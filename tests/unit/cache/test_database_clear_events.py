"""Test database event clearing functionality."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from calendarbot.cache.database import DatabaseManager
from calendarbot.cache.models import CachedEvent


@pytest.fixture
async def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        db = DatabaseManager(db_path)
        await db.initialize()
        yield db


def create_test_event(event_id: str) -> CachedEvent:
    """Create a test event with the given ID."""
    now = datetime.now()
    return CachedEvent(
        id=f"cached_{event_id}",
        graph_id=event_id,
        subject=f"Test Event {event_id}",
        body_preview=f"Body for event {event_id}",
        start_datetime=now.isoformat(),
        end_datetime=now.isoformat(),
        start_timezone="UTC",
        end_timezone="UTC",
        is_all_day=False,
        show_as="busy",
        is_cancelled=False,
        is_organizer=True,
        location_display_name=None,
        location_address=None,
        is_online_meeting=False,
        online_meeting_url=None,
        web_link=None,
        is_recurring=False,
        series_master_id=None,
        cached_at=now.isoformat(),
        last_modified=None,
    )


class TestDatabaseClearEvents:
    """Test cases for database event clearing functionality."""

    async def test_clear_all_events_when_empty_database_then_returns_zero(self, temp_db):
        """Test clearing events from empty database returns zero."""
        cleared_count = await temp_db.clear_all_events()
        assert cleared_count == 0

    async def test_clear_all_events_when_has_events_then_clears_all(self, temp_db):
        """Test clearing events removes all events from database."""
        # Create and store test events
        events = [
            create_test_event("event1"),
            create_test_event("event2"),
            create_test_event("event3"),
        ]

        success = await temp_db.store_events(events)
        assert success, "Failed to store test events"

        # Verify events were stored
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date.replace(hour=23, minute=59, second=59)
        stored_events = await temp_db.get_events_by_date_range(start_date, end_date)
        assert len(stored_events) == 3, "Events were not stored correctly"

        # Clear all events
        cleared_count = await temp_db.clear_all_events()
        assert cleared_count == 3, "Should have cleared 3 events"

        # Verify no events remain
        remaining_events = await temp_db.get_events_by_date_range(start_date, end_date)
        assert len(remaining_events) == 0, "Events should have been cleared"

    async def test_clear_all_events_when_multiple_calls_then_subsequent_calls_return_zero(
        self, temp_db
    ):
        """Test multiple calls to clear_all_events."""
        # Store an event
        event = create_test_event("test_event")
        await temp_db.store_events([event])

        # First clear should remove the event
        first_clear = await temp_db.clear_all_events()
        assert first_clear == 1, "First clear should remove 1 event"

        # Second clear should remove nothing
        second_clear = await temp_db.clear_all_events()
        assert second_clear == 0, "Second clear should remove 0 events"

    async def test_clear_all_events_when_database_error_then_returns_zero(self, temp_db):
        """Test clear_all_events handles database errors gracefully."""
        # Close the database connection to simulate an error
        await temp_db.db.close() if hasattr(temp_db, "db") else None

        # This should handle the error gracefully and return 0
        cleared_count = await temp_db.clear_all_events()
        assert cleared_count == 0, "Should return 0 when database error occurs"
