"""Test cache manager event clearing functionality."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from calendarbot.cache.manager import CacheManager
from calendarbot.ics.models import CalendarEvent, DateTimeInfo


class MockSettings:
    """Mock settings for testing."""

    def __init__(self, db_path: Path):
        self.database_file = db_path
        self.cache_ttl = 3600


def create_mock_event(event_id: str) -> CalendarEvent:
    """Create a mock calendar event."""
    now = datetime.now()
    return CalendarEvent(
        id=event_id,
        subject=f"Test Event {event_id}",
        body_preview=f"Body for event {event_id}",
        start=DateTimeInfo(date_time=now, time_zone="UTC"),
        end=DateTimeInfo(date_time=now, time_zone="UTC"),
        is_all_day=False,
        show_as="busy",
        is_cancelled=False,
        is_organizer=True,
        location=None,
        is_online_meeting=False,
        online_meeting_url=None,
        is_recurring=False,
        last_modified_date_time=None,
    )


@pytest.fixture
async def cache_manager():
    """Create a cache manager with temporary database."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        settings = MockSettings(db_path)
        manager = CacheManager(settings)
        await manager.initialize()
        yield manager


class TestCacheManagerClearEvents:
    """Test cases for cache manager event clearing."""

    async def test_clear_all_events_when_empty_cache_then_returns_zero(self, cache_manager):
        """Test clearing events from empty cache returns zero."""
        cleared_count = await cache_manager.clear_all_events()
        assert cleared_count == 0

    async def test_clear_all_events_when_has_cached_events_then_clears_all(self, cache_manager):
        """Test clearing events removes all cached events."""
        # Cache some events
        events = [
            create_mock_event("event1"),
            create_mock_event("event2"),
        ]

        success = await cache_manager.cache_events(events)
        assert success, "Failed to cache test events"

        # Verify events were cached
        cached_events = await cache_manager.get_todays_cached_events()
        assert len(cached_events) == 2, "Events were not cached correctly"

        # Clear all events
        cleared_count = await cache_manager.clear_all_events()
        assert cleared_count == 2, "Should have cleared 2 events"

        # Verify no events remain
        remaining_events = await cache_manager.get_todays_cached_events()
        assert len(remaining_events) == 0, "Events should have been cleared"

    async def test_clear_all_events_when_error_then_returns_zero(self, cache_manager):
        """Test clear_all_events handles errors gracefully."""
        # Cache an event first
        event = create_mock_event("test_event")
        await cache_manager.cache_events([event])

        # Mock database to cause an error by setting an invalid path
        original_db = cache_manager.db
        cache_manager.db = None

        # This should handle the error gracefully
        cleared_count = await cache_manager.clear_all_events()
        assert cleared_count == 0, "Should return 0 when error occurs"

        # Restore original database
        cache_manager.db = original_db
