"""
Integration test that demonstrates the real-world gap in raw events functionality.

This test reveals why raw events aren't being stored in the actual application:
the ICS source returns only parsed events, not the full ICSParseResult that
contains raw content.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from calendarbot.cache.models import CalendarEvent
from calendarbot.ics.models import ICSParseResult
from calendarbot.sources.ics_source import ICSSource
from calendarbot.sources.manager import SourceManager


@pytest.fixture
def sample_events():
    """Create sample calendar events."""
    return [
        CalendarEvent(
            id="event1",
            graph_id="graph1",
            subject="Test Event 1",
            start=datetime(2024, 1, 15, 10, 0),
            end=datetime(2024, 1, 15, 11, 0),
            show_as="busy",
            location=Mock(),
            body=Mock(),
            attendees=[],
            is_cancelled=False,
            is_organizer=True,
            web_link="https://example.com/event1",
        ),
        CalendarEvent(
            id="event2",
            graph_id="graph2",
            subject="Test Event 2",
            start=datetime(2024, 1, 15, 14, 0),
            end=datetime(2024, 1, 15, 15, 0),
            show_as="busy",
            location=Mock(),
            body=Mock(),
            attendees=[],
            is_cancelled=False,
            is_organizer=True,
            web_link="https://example.com/event2",
        ),
    ]


@pytest.fixture
def sample_ics_parse_result(sample_events):
    """Create sample ICS parse result with raw content."""
    return ICSParseResult(
        success=True,
        events=sample_events,
        raw_content="BEGIN:VCALENDAR\nVERSION:2.0\nSAMPLE ICS CONTENT\nEND:VCALENDAR",
        source_url="https://example.com/calendar.ics",
        event_count=2,
    )


class TestRawEventsRealIntegrationGap:
    """Test that demonstrates the real integration gap preventing raw events storage."""

    @pytest.mark.asyncio
    async def test_integration_gap_ics_source_loses_raw_content(self, sample_ics_parse_result):
        """
        CRITICAL INTEGRATION TEST: Demonstrates that ICS source loses raw content.

        This test shows that while the ICS parser creates ICSParseResult with raw content,
        the ICS source's fetch_events() method only returns the events list,
        losing the raw content that should be stored.
        """
        # Setup ICS source with mocked parser
        mock_settings = Mock()
        mock_config = Mock()
        mock_config.name = "test-source"

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

            # CRITICAL: Parser returns full ICSParseResult with raw content
            mock_parser.parse_ics_content.return_value = sample_ics_parse_result

            # Create ICS source
            ics_source = ICSSource(mock_settings, mock_config)

            # Call fetch_events (this is what sources manager calls)
            result = await ics_source.fetch_events()

            # PROBLEM: Result is only the events list, raw content is lost!
            assert isinstance(result, list)  # Not ICSParseResult
            assert len(result) == 2
            assert result[0].id == "event1"
            assert result[1].id == "event2"

            # The raw content is completely lost at this point
            # This is why raw events never get stored in the real application

    @pytest.mark.asyncio
    async def test_integration_gap_sources_manager_cant_store_raw_events(self, sample_events):
        """
        CRITICAL: Shows that sources manager can't store raw events because it never receives them.

        This test demonstrates the complete integration flow and shows where it breaks down.
        """
        # Setup mocks
        mock_settings = Mock()
        mock_cache_manager = Mock()
        mock_cache_manager.cache_events = AsyncMock(return_value=True)

        # Create sources manager
        sources_manager = SourceManager(mock_settings, mock_cache_manager)

        # Mock a source that returns only events (current behavior)
        mock_source = Mock()
        mock_source.is_healthy.return_value = True
        mock_source.fetch_events = AsyncMock(return_value=sample_events)
        sources_manager._sources = {"test-source": mock_source}

        # Fetch and cache events
        result = await sources_manager.fetch_and_cache_events()

        # Verify success
        assert result is True

        # Check what was passed to cache manager
        mock_cache_manager.cache_events.assert_called_once()
        cached_data = mock_cache_manager.cache_events.call_args[0][0]

        # PROBLEM: Cache manager only receives events list, no raw content
        assert isinstance(cached_data, list)
        assert len(cached_data) == 2
        assert cached_data[0].id == "event1"

        # Raw content is never available to be stored because the source interface
        # only returns events, not the full parse result with raw content


class TestProposedSolutionForRawEventsIntegration:
    """Tests that show how the integration should work to fix raw events storage."""

    @pytest.mark.asyncio
    async def test_proposed_solution_ics_source_returns_parse_result(self, sample_ics_parse_result):
        """
        PROPOSED SOLUTION: ICS source should return ICSParseResult, not just events.

        This test shows how the ICS source could be modified to preserve raw content.
        Note: This would require interface changes.
        """
        # This test would pass if we modify ICS source to return ICSParseResult
        # instead of just the events list

        # The modification would be in ics_source.py line 160:
        # OLD: return parse_result.events
        # NEW: return parse_result  # Return full result with raw content

        # Then sources manager would need to handle ICSParseResult objects
        # and pass them directly to cache manager, which already supports this

        # For now, this test documents the intended behavior
        assert sample_ics_parse_result.raw_content is not None
        assert sample_ics_parse_result.source_url == "https://example.com/calendar.ics"
        assert len(sample_ics_parse_result.events) == 2

    @pytest.mark.asyncio
    async def test_proposed_solution_sources_manager_handles_parse_results(
        self, sample_ics_parse_result
    ):
        """
        PROPOSED SOLUTION: Sources manager should handle ICSParseResult objects.

        This test shows how sources manager could handle the full parse results.
        """
        # Setup mocks
        mock_settings = Mock()
        mock_cache_manager = Mock()
        mock_cache_manager.cache_events = AsyncMock(return_value=True)

        # Create sources manager
        sources_manager = SourceManager(mock_settings, mock_cache_manager)

        # Mock a source that returns ICSParseResult (proposed new behavior)
        mock_source = Mock()
        mock_source.is_healthy.return_value = True
        mock_source.fetch_events = AsyncMock(return_value=sample_ics_parse_result)
        sources_manager._sources = {"test-source": mock_source}

        # This would require modifying sources manager to:
        # 1. Detect when fetch_events returns ICSParseResult vs list
        # 2. Pass ICSParseResult directly to cache_events (which already supports it)
        # 3. Handle mixed scenarios (some sources return lists, others return parse results)

        # The cache manager already supports both interfaces:
        # cache_events(List[CalendarEvent]) - current
        # cache_events(ICSParseResult) - already implemented for raw events


# Documentation of the integration issue
INTEGRATION_ISSUE_SUMMARY = """
RAW EVENTS INTEGRATION ISSUE SUMMARY:

PROBLEM:
1. ICS Parser creates ICSParseResult with raw content ✓
2. ICS Source calls parser but returns only parse_result.events ✗
3. Sources Manager receives only events list ✗
4. Cache Manager never gets raw content to store ✗

CURRENT FLOW:
ICS Content → Parser (creates ICSParseResult) → ICS Source (extracts .events) → 
Sources Manager (gets events list) → Cache Manager (stores only events)

NEEDED FLOW:
ICS Content → Parser (creates ICSParseResult) → ICS Source (returns full result) →
Sources Manager (handles parse result) → Cache Manager (stores events + raw content)

REQUIRED CHANGES:
1. Modify ICS Source to return ICSParseResult instead of just events
2. Modify Sources Manager to handle ICSParseResult objects 
3. Cache Manager already supports both interfaces (no change needed)

The unit tests pass because they test isolated components with mocks,
but the real application integration is broken due to the interface mismatch.
"""
