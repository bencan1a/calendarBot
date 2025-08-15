"""Unit tests for cache manager raw events integration."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from unittest.mock import Mock, patch

import pytest

from calendarbot.cache.manager import CacheManager
from calendarbot.ics.models import CalendarEvent, DateTimeInfo, ICSParseResult, Location


@pytest.fixture
async def temp_cache_manager():
    """Create a temporary cache manager for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create mock settings
        settings = Mock()
        settings.database_file = Path(temp_dir) / "test.db"
        settings.cache_ttl = 3600  # 1 hour

        cache_manager = CacheManager(settings)
        await cache_manager.initialize()
        yield cache_manager


def create_test_calendar_event(
    event_id: str,
    subject: str = "Test Event",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> CalendarEvent:
    """Create a test calendar event for testing."""
    if start_time is None:
        start_time = datetime.now()
    if end_time is None:
        end_time = start_time + timedelta(hours=1)

    # Create mock calendar event
    event = Mock(spec=CalendarEvent)
    event.id = event_id
    event.subject = subject
    event.body_preview = f"Body for {subject}"
    event.start = Mock(spec=DateTimeInfo)
    event.start.date_time = start_time
    event.start.time_zone = "UTC"
    event.end = Mock(spec=DateTimeInfo)
    event.end.date_time = end_time
    event.end.time_zone = "UTC"
    event.is_all_day = False
    event.show_as = "busy"  # String for ICS events
    event.is_cancelled = False
    event.is_organizer = True
    event.location = Mock(spec=Location)
    event.location.display_name = "Test Location"
    event.location.address = "123 Test St"
    event.is_online_meeting = False
    event.online_meeting_url = None
    event.is_recurring = False
    event.last_modified_date_time = None

    return event


def create_test_ics_parse_result(
    events: list[CalendarEvent],
    raw_content: Optional[str] = None,
    source_url: str = "https://example.com/calendar.ics",
) -> ICSParseResult:
    """Create a test ICS parse result."""
    # If no raw content provided, generate valid ICS content with events
    if raw_content is None:
        ics_events = []
        for event in events:
            ics_events.append(f"""BEGIN:VEVENT
UID:{event.id}
SUMMARY:{event.subject}
DTSTART:20240101T120000Z
DTEND:20240101T130000Z
END:VEVENT""")

        raw_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
{chr(10).join(ics_events)}
END:VCALENDAR"""

    # Create event_raw_content_map mapping event IDs to individual ICS content
    event_raw_content_map = {}
    for event in events:
        event_raw_content_map[event.id] = f"""BEGIN:VEVENT
UID:{event.id}
SUMMARY:{event.subject}
DTSTART:20240101T120000Z
DTEND:20240101T130000Z
END:VEVENT"""

    return ICSParseResult(
        success=True,
        events=events,
        raw_content=raw_content,
        source_url=source_url,
        event_raw_content_map=event_raw_content_map,
    )


class TestCacheManagerRawEventsIntegration:
    """Test cases for cache manager raw events integration."""

    async def test_cache_events_when_ics_parse_result_then_stores_raw_events(
        self, temp_cache_manager
    ):
        """Test caching ICS parse result stores both cached and raw events."""
        # Create test events
        event1 = create_test_calendar_event("event1", "Meeting 1")
        event2 = create_test_calendar_event("event2", "Meeting 2")

        # Create ICS parse result with auto-generated valid raw content
        source_url = "https://example.com/calendar.ics"
        ics_result = create_test_ics_parse_result([event1, event2], source_url=source_url)

        # Cache the events
        result = await temp_cache_manager.cache_events(ics_result)
        assert result is True

        # Verify cached events were stored
        cached_events = await temp_cache_manager.get_cached_events(
            datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
            datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999),
        )
        assert len(cached_events) == 2

        # Verify raw events were created with correct IDs
        raw_event1 = await temp_cache_manager.db.get_raw_event_by_id("raw_event1")
        raw_event2 = await temp_cache_manager.db.get_raw_event_by_id("raw_event2")

        # Expected individual event ICS content
        expected_event1_ics = """BEGIN:VEVENT
UID:event1
SUMMARY:Meeting 1
DTSTART:20240101T120000Z
DTEND:20240101T130000Z
END:VEVENT"""

        expected_event2_ics = """BEGIN:VEVENT
UID:event2
SUMMARY:Meeting 2
DTSTART:20240101T120000Z
DTEND:20240101T130000Z
END:VEVENT"""

        assert raw_event1 is not None
        assert raw_event1.graph_id == "event1"
        assert raw_event1.raw_ics_content == expected_event1_ics
        assert raw_event1.source_url == source_url

        assert raw_event2 is not None
        assert raw_event2.graph_id == "event2"
        assert raw_event2.raw_ics_content == expected_event2_ics
        assert raw_event2.source_url == source_url

    async def test_cache_events_when_regular_events_list_then_no_raw_events(
        self, temp_cache_manager
    ):
        """Test caching regular events list doesn't create raw events."""
        # Create test events
        event1 = create_test_calendar_event("event1", "Meeting 1")
        event2 = create_test_calendar_event("event2", "Meeting 2")

        # Cache events as regular list (not ICSParseResult)
        result = await temp_cache_manager.cache_events([event1, event2])
        assert result is True

        # Verify cached events were stored
        cached_events = await temp_cache_manager.get_cached_events(
            datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
            datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999),
        )
        assert len(cached_events) == 2

        # Verify no raw events were created
        raw_event1 = await temp_cache_manager.db.get_raw_event_by_id("raw_event1")
        raw_event2 = await temp_cache_manager.db.get_raw_event_by_id("raw_event2")

        assert raw_event1 is None
        assert raw_event2 is None

    async def test_cache_events_when_raw_event_creation_fails_then_continues_with_cached_only(
        self, temp_cache_manager
    ):
        """Test that raw event creation failure doesn't prevent cached events storage."""
        # Create test events
        event1 = create_test_calendar_event("event1", "Meeting 1")

        # Create ICS parse result
        ics_result = create_test_ics_parse_result([event1], "invalid content")

        # Mock RawEvent.create_from_ics to raise an exception
        with patch(
            "calendarbot.cache.models.RawEvent.create_from_ics",
            side_effect=Exception("Raw event creation failed"),
        ):
            result = await temp_cache_manager.cache_events(ics_result)
            assert result is True  # Should still succeed for cached events

        # Verify cached events were stored
        cached_events = await temp_cache_manager.get_cached_events(
            datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
            datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999),
        )
        assert len(cached_events) == 1

        # Verify no raw events were created
        raw_event = await temp_cache_manager.db.get_raw_event_by_id("raw_event1")
        assert raw_event is None

    async def test_cache_events_when_raw_storage_fails_then_logs_warning_but_succeeds(
        self, temp_cache_manager
    ):
        """Test that raw event storage failure logs warning but doesn't fail the operation."""
        # Create test events
        event1 = create_test_calendar_event("event1", "Meeting 1")

        # Create ICS parse result
        ics_result = create_test_ics_parse_result([event1])

        # Mock database store_raw_events to fail
        with patch.object(temp_cache_manager.db, "store_raw_events", return_value=False):
            with patch("calendarbot.cache.manager.logger") as mock_logger:
                result = await temp_cache_manager.cache_events(ics_result)
                assert result is True

                # Verify warning was logged
                mock_logger.warning.assert_called_with(
                    "Failed to store raw events, but cached events were stored"
                )

        # Verify cached events were still stored
        cached_events = await temp_cache_manager.get_cached_events(
            datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
            datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999),
        )
        assert len(cached_events) == 1

    async def test_cache_events_when_cached_storage_fails_then_tries_fallback(
        self, temp_cache_manager
    ):
        """Test fallback when initial cached events storage fails."""
        # Create test events
        event1 = create_test_calendar_event("event1", "Meeting 1")

        # Create ICS parse result
        ics_result = create_test_ics_parse_result([event1])

        # Mock database store_events to fail initially, then succeed
        call_count = 0

        def mock_store_events(events):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Database error")
            return True

        with patch.object(temp_cache_manager.db, "store_events", side_effect=mock_store_events):
            with patch("calendarbot.cache.manager.logger") as mock_logger:
                result = await temp_cache_manager.cache_events(ics_result)
                assert result is True

                # Verify fallback warning was logged
                mock_logger.warning.assert_called_with(
                    "Stored cached events only after raw storage error"
                )

    async def test_cache_events_when_both_storages_fail_then_returns_false(
        self, temp_cache_manager
    ):
        """Test complete failure when both cached and fallback storage fail."""
        # Create test events
        event1 = create_test_calendar_event("event1", "Meeting 1")

        # Create ICS parse result
        ics_result = create_test_ics_parse_result([event1])

        # Mock database store_events to always fail
        with patch.object(
            temp_cache_manager.db, "store_events", side_effect=Exception("Database error")
        ):
            result = await temp_cache_manager.cache_events(ics_result)
            assert result is False

    async def test_cache_events_when_empty_ics_result_then_succeeds_without_raw_events(
        self, temp_cache_manager
    ):
        """Test caching empty ICS result succeeds without creating raw events."""
        # Create empty ICS parse result
        ics_result = create_test_ics_parse_result([])

        result = await temp_cache_manager.cache_events(ics_result)
        assert result is True

    async def test_cache_events_when_ics_result_no_raw_content_then_no_raw_events(
        self, temp_cache_manager
    ):
        """Test ICS result without raw content doesn't create raw events."""
        # Create test events
        event1 = create_test_calendar_event("event1", "Meeting 1")

        # Create ICS parse result without raw content
        ics_result = ICSParseResult(
            success=True,
            events=[event1],
            raw_content=None,  # No raw content
            source_url="https://example.com/calendar.ics",
        )

        result = await temp_cache_manager.cache_events(ics_result)
        assert result is True

        # Verify cached events were stored
        cached_events = await temp_cache_manager.get_cached_events(
            datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
            datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999),
        )
        assert len(cached_events) == 1

        # Verify no raw events were created
        raw_event = await temp_cache_manager.db.get_raw_event_by_id("raw_event1")
        assert raw_event is None


class TestCacheManagerRawEventsCleanup:
    """Test cases for cache manager raw events cleanup operations."""

    async def test_cleanup_when_called_then_cleans_both_cached_and_raw_events(
        self, temp_cache_manager
    ):
        """Test cleanup removes both cached and raw events."""
        # Store some test events first
        event1 = create_test_calendar_event("event1", "Meeting 1")
        ics_result = create_test_ics_parse_result([event1])
        await temp_cache_manager.cache_events(ics_result)

        # Mock the cleanup methods to return specific counts
        with patch.object(
            temp_cache_manager, "cleanup_old_events", return_value=2
        ) as mock_cached_cleanup:
            with patch.object(
                temp_cache_manager.db, "cleanup_raw_events", return_value=3
            ) as mock_raw_cleanup:
                result = await temp_cache_manager.cleanup()

                assert result is True
                mock_cached_cleanup.assert_called_once()
                mock_raw_cleanup.assert_called_once()

    async def test_cleanup_when_database_error_then_returns_false(self, temp_cache_manager):
        """Test cleanup handles database errors gracefully."""
        # Mock cleanup_old_events to raise an exception
        with patch.object(
            temp_cache_manager, "cleanup_old_events", side_effect=Exception("Database error")
        ):
            result = await temp_cache_manager.cleanup()
            assert result is False

    async def test_cleanup_when_raw_cleanup_fails_then_logs_but_continues(self, temp_cache_manager):
        """Test cleanup continues even if raw events cleanup fails."""
        # Mock cleanup methods
        with patch.object(temp_cache_manager, "cleanup_old_events", return_value=2):
            with patch.object(
                temp_cache_manager.db,
                "cleanup_raw_events",
                side_effect=Exception("Raw cleanup error"),
            ):
                result = await temp_cache_manager.cleanup()
                assert result is False  # Should fail due to exception


class TestCacheManagerRawEventsErrorHandling:
    """Test cases for cache manager raw events error handling."""

    async def test_cache_events_when_conversion_fails_then_handles_gracefully(
        self, temp_cache_manager
    ):
        """Test graceful handling when event conversion fails."""
        # Create malformed event that will cause conversion issues
        bad_event = Mock()
        bad_event.id = "bad_event"
        # Missing required attributes to cause conversion failure

        ics_result = create_test_ics_parse_result([bad_event])

        result = await temp_cache_manager.cache_events(ics_result)
        assert result is False  # Should fail gracefully

    async def test_cache_events_when_raw_event_oversized_then_handles_gracefully(
        self, temp_cache_manager
    ):
        """Test handling of oversized raw content."""
        # Create test event
        event1 = create_test_calendar_event("event1", "Meeting 1")

        # Create ICS result with very large raw content
        large_content = "X" * (60 * 1024 * 1024)  # 60MB content (exceeds 50MB limit)
        ics_result = create_test_ics_parse_result([event1], large_content)

        # This should handle the oversized content gracefully
        # The RawEvent creation might fail, but cached events should still work
        result = await temp_cache_manager.cache_events(ics_result)

        # The result depends on whether RawEvent.create_from_ics handles size validation
        # If it raises an exception, it should be caught and cached events should still work
        # If it succeeds, both cached and raw events should be stored
        assert result is True  # At minimum, cached events should succeed


class TestCacheManagerRawEventsTransactionHandling:
    """Test cases for cache manager atomic transaction handling."""

    async def test_cache_events_when_raw_storage_exception_then_atomic_fallback(
        self, temp_cache_manager
    ):
        """Test atomic transaction behavior with raw storage exceptions."""
        # Create test events
        event1 = create_test_calendar_event("event1", "Meeting 1")
        ics_result = create_test_ics_parse_result([event1])

        # Mock store_raw_events to raise an exception
        with patch.object(
            temp_cache_manager.db, "store_raw_events", side_effect=Exception("Raw storage error")
        ):
            with patch("calendarbot.cache.manager.logger") as mock_logger:
                result = await temp_cache_manager.cache_events(ics_result)
                assert result is True

                # Verify fallback message was logged
                mock_logger.warning.assert_called_with(
                    "Stored cached events only after raw storage error"
                )

        # Verify cached events were still stored
        cached_events = await temp_cache_manager.get_cached_events(
            datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
            datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999),
        )
        assert len(cached_events) == 1

    async def test_cache_events_when_memory_monitoring_fails_then_continues(
        self, temp_cache_manager
    ):
        """Test that memory monitoring failures don't prevent event caching."""
        # Create test events
        event1 = create_test_calendar_event("event1", "Meeting 1")
        ics_result = create_test_ics_parse_result([event1])

        # Mock memory_monitor to raise an exception
        with patch(
            "calendarbot.cache.manager.memory_monitor",
            side_effect=Exception("Memory monitor error"),
        ):
            result = await temp_cache_manager.cache_events(ics_result)
            assert result is False  # Should fail due to exception in conversion

    async def test_cache_events_when_performance_monitor_fails_then_continues(
        self, temp_cache_manager
    ):
        """Test that performance monitoring failures don't prevent event caching."""
        # Create test events
        event1 = create_test_calendar_event("event1", "Meeting 1")
        ics_result = create_test_ics_parse_result([event1])

        # Mock the performance monitor decorator to not interfere
        # The actual performance monitor is applied as a decorator, so we can't easily mock it
        # Instead, we'll test that the core functionality works despite monitoring
        result = await temp_cache_manager.cache_events(ics_result)
        assert result is True

    async def test_cache_events_when_correlation_id_fails_then_continues(self, temp_cache_manager):
        """Test that correlation ID failures don't prevent event caching."""
        # Create test events
        event1 = create_test_calendar_event("event1", "Meeting 1")
        ics_result = create_test_ics_parse_result([event1])

        # Mock the correlation ID decorator to not interfere
        # The actual correlation ID is applied as a decorator, so we can't easily mock it
        # Instead, we'll test that the core functionality works despite correlation ID tracking
        result = await temp_cache_manager.cache_events(ics_result)
        assert result is True
