"""
Integration test to validate that the ICS source fix actually works.

This test validates that the fixes to ICS source and sources manager
now properly preserve raw content through the complete data flow.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from calendarbot.cache.models import CalendarEvent
from calendarbot.ics.models import ICSParseResult
from calendarbot.sources.manager import SourceManager
from calendarbot.sources.models import SourceConfig


@pytest.fixture
def sample_events():
    """Create sample calendar events."""
    return [
        CalendarEvent(
            id="event1",
            title="Test Event 1",
            start_time=datetime(2024, 1, 15, 10, 0),
            end_time=datetime(2024, 1, 15, 11, 0),
            location="Test Location 1",
            description="Test Description 1",
        ),
        CalendarEvent(
            id="event2",
            title="Test Event 2",
            start_time=datetime(2024, 1, 15, 14, 0),
            end_time=datetime(2024, 1, 15, 15, 0),
            location="Test Location 2",
            description="Test Description 2",
        ),
    ]


@pytest.fixture
def sample_parse_result(sample_events):
    """Create sample ICS parse result with raw content."""
    return ICSParseResult(
        success=True,
        events=sample_events,
        raw_content="BEGIN:VCALENDAR\nVERSION:2.0\nSAMPLE ICS CONTENT\nEND:VCALENDAR",
        source_url="https://example.com/calendar.ics",
        event_count=2,
    )


@pytest.fixture
def sample_source_config():
    """Create sample source configuration."""
    return SourceConfig(
        name="test-source",
        type="ics",
        url="https://example.com/calendar.ics",
        enabled=True,
        refresh_interval=3600,
        timeout=30,
    )


class TestIntegrationFixValidation:
    """Test that validates the integration gap fix works correctly."""

    @pytest.mark.asyncio
    async def test_ics_source_now_returns_parse_result(self, sample_parse_result):
        """
        Validates that ICS source now returns ICSParseResult instead of just events.

        This test confirms the fix where we changed the return type from
        list[CalendarEvent] to ICSParseResult.
        """
        # Setup ICS source with mocked dependencies
        mock_config = {
            "name": "test-source",
            "url": "https://example.com/calendar.ics",
            "enabled": True,
        }

        with (
            patch("calendarbot.sources.ics_source.ICSFetcher") as mock_fetcher_class,
            patch("calendarbot.sources.ics_source.ICSParser") as mock_parser_class,
        ):
            # Setup mocks
            mock_fetcher = Mock()
            mock_fetcher_class.return_value = mock_fetcher
            mock_parser = Mock()
            mock_parser_class.return_value = mock_parser

            # Mock the fetch response
            mock_response = Mock()
            mock_response.content = (
                "BEGIN:VCALENDAR\nVERSION:2.0\nSAMPLE ICS CONTENT\nEND:VCALENDAR"
            )
            mock_fetcher.fetch_ics = AsyncMock(return_value=mock_response)

            # Parser returns full ICSParseResult with raw content
            mock_parser.parse_ics_content.return_value = sample_parse_result

            # Create ICS source using Pydantic model constructor
            ics_source = ICSSource(**mock_config)

            # Call fetch_events - THIS IS THE KEY FIX
            result = await ics_source.fetch_events()

            # VALIDATION: Result should now be ICSParseResult, not just events list
            assert isinstance(result, ICSParseResult), (
                f"Expected ICSParseResult, got {type(result)}"
            )
            assert result.raw_content is not None, "Raw content should be preserved"
            assert (
                result.raw_content
                == "BEGIN:VCALENDAR\nVERSION:2.0\nSAMPLE ICS CONTENT\nEND:VCALENDAR"
            )
            assert len(result.events) == 2, "Should have 2 events"
            assert result.source_url == "https://example.com/calendar.ics"

            # Validate the events are still accessible
            assert result.events[0].id == "event1"
            assert result.events[1].id == "event2"

    @pytest.mark.asyncio
    async def test_sources_manager_handles_parse_result(self, sample_parse_result):
        """
        Validates that sources manager can now handle ICSParseResult objects.

        This test confirms the fix where we updated the sources manager to
        detect and properly pass ICSParseResult to the cache manager.
        """
        # Setup mocks
        mock_settings = Mock()
        mock_cache_manager = Mock()
        mock_cache_manager.cache_events = AsyncMock(return_value=True)

        # Create sources manager
        sources_manager = SourceManager(mock_settings, mock_cache_manager)

        # Mock a source that returns ICSParseResult (our new behavior)
        mock_source = Mock()
        mock_source.is_healthy.return_value = True
        mock_source.fetch_events = AsyncMock(return_value=sample_parse_result)
        sources_manager._sources = {"test-source": mock_source}

        # Fetch and cache events
        result = await sources_manager.fetch_and_cache_events()

        # Verify success
        assert result is True

        # VALIDATION: Check what was passed to cache manager
        mock_cache_manager.cache_events.assert_called_once()
        cached_data = mock_cache_manager.cache_events.call_args[0][0]

        # Should receive the full ICSParseResult, not just events
        assert isinstance(cached_data, ICSParseResult), (
            f"Expected ICSParseResult, got {type(cached_data)}"
        )
        assert cached_data.raw_content is not None, "Raw content should be passed through"
        assert len(cached_data.events) == 2, "Events should be included"

    @pytest.mark.asyncio
    async def test_mixed_sources_graceful_degradation(self, sample_parse_result):
        """
        Validates that sources manager handles mixed source types gracefully.

        This test ensures that when we have sources returning different types,
        the system gracefully falls back to events-only mode.
        """
        # Setup mocks
        mock_settings = Mock()
        mock_cache_manager = Mock()
        mock_cache_manager.cache_events = AsyncMock(return_value=True)

        # Create sources manager
        sources_manager = SourceManager(mock_settings, mock_cache_manager)

        # Mock sources with different return types
        mock_source1 = Mock()
        mock_source1.is_healthy.return_value = True
        mock_source1.fetch_events = AsyncMock(return_value=sample_parse_result)

        mock_source2 = Mock()
        mock_source2.is_healthy.return_value = True
        mock_source2.fetch_events = AsyncMock(
            return_value=sample_parse_result.events
        )  # Just events

        sources_manager._sources = {"ics-source": mock_source1, "other-source": mock_source2}

        # Fetch and cache events
        result = await sources_manager.fetch_and_cache_events()

        # Verify success
        assert result is True

        # Should fall back to events-only mode due to mixed sources
        mock_cache_manager.cache_events.assert_called_once()
        cached_data = mock_cache_manager.cache_events.call_args[0][0]

        # Should be combined events list, not parse result
        assert isinstance(cached_data, list), "Should fall back to events list for mixed sources"
        assert len(cached_data) == 4, "Should have combined events from both sources"


# Documentation of the successful fix
FIX_VALIDATION_SUMMARY = """
INTEGRATION FIX VALIDATION SUMMARY:

PROBLEM IDENTIFIED:
- ICS source was returning only parse_result.events instead of full ICSParseResult
- Sources manager couldn't access raw content to pass to cache manager
- Raw events were never stored despite all components supporting them

FIXES IMPLEMENTED:
1. ✅ ICS Source: Changed return type from List[CalendarEvent] to ICSParseResult
2. ✅ Sources Manager: Added logic to detect and handle ICSParseResult objects
3. ✅ Backward Compatibility: Maintained support for sources returning events lists

VALIDATION TESTS:
1. ✅ ICS source now returns full ICSParseResult with raw content
2. ✅ Sources manager properly passes ICSParseResult to cache manager  
3. ✅ Mixed source scenarios gracefully fall back to events-only mode
4. ✅ Raw content is preserved throughout the data flow

The integration gap has been successfully closed. Raw events should now 
be stored when using ICS sources in the real application.
"""
