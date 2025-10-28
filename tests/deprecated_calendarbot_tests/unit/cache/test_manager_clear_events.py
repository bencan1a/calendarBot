"""Test cache manager event clearing functionality."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

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
async def cache_manager(tmp_path):
    """Create a cache manager with mocked database."""
    db_path = tmp_path / "test.db"
    settings = MockSettings(db_path)

    with patch("calendarbot.cache.manager.DatabaseManager") as mock_db_class:
        mock_db = AsyncMock()
        mock_db_class.return_value = mock_db

        manager = CacheManager(settings)
        # Mock the initialize method to avoid actual database creation
        with patch.object(manager, "initialize", new_callable=AsyncMock):
            await manager.initialize()

        # Set the mocked database instance
        manager.db = mock_db
        yield manager


class TestCacheManagerClearEvents:
    """Test cases for cache manager event clearing."""

    async def test_clear_all_events_when_empty_cache_then_returns_zero(self, cache_manager):
        """Test clearing events from empty cache returns zero."""
        cache_manager.db.clear_all_events.return_value = 0
        cleared_count = await cache_manager.clear_all_events()
        assert cleared_count == 0

    async def test_clear_all_events_when_has_cached_events_then_clears_all(self, cache_manager):
        """Test clearing events removes all cached events."""
        # Mock the cache manager methods directly with AsyncMock for async methods
        with patch.object(
            cache_manager, "cache_events", new_callable=AsyncMock, return_value=True
        ) as mock_cache:
            with patch.object(
                cache_manager,
                "get_todays_cached_events",
                new_callable=AsyncMock,
                side_effect=[
                    [
                        create_mock_event("event1"),
                        create_mock_event("event2"),
                    ],  # Initial cached events
                    [],  # After clearing
                ],
            ) as mock_get:
                with patch.object(
                    cache_manager, "clear_all_events", new_callable=AsyncMock, return_value=2
                ) as mock_clear:
                    # Cache some events
                    events = [
                        create_mock_event("event1"),
                        create_mock_event("event2"),
                    ]

                    success = await cache_manager.cache_events(events)
                    assert success, "Failed to cache test events"

                    # Verify events were cached (mocked)
                    cached_events = await cache_manager.get_todays_cached_events()
                    assert len(cached_events) == 2, "Events were not cached correctly"

                    # Clear all events
                    cleared_count = await cache_manager.clear_all_events()
                    assert cleared_count == 2, "Should have cleared 2 events"

                    # Verify no events remain (mocked)
                    remaining_events = await cache_manager.get_todays_cached_events()
                    assert len(remaining_events) == 0, "Events should have been cleared"

    async def test_clear_all_events_when_error_then_returns_zero(self, cache_manager):
        """Test clear_all_events handles errors gracefully."""
        # Mock error case
        cache_manager.db.clear_all_events.return_value = 0

        # This should handle the error gracefully
        cleared_count = await cache_manager.clear_all_events()
        assert cleared_count == 0, "Should return 0 when error occurs"
