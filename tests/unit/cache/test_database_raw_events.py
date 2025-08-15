"""Unit tests for database raw events operations."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest

from calendarbot.cache.database import DatabaseManager
from calendarbot.cache.models import RawEvent


@pytest.fixture
async def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        db = DatabaseManager(db_path)
        await db.initialize()
        yield db


def create_test_raw_event(
    event_id: str, content: str = "BEGIN:VCALENDAR\nEND:VCALENDAR", source_url: Optional[str] = None
) -> RawEvent:
    """Create a test raw event with the given parameters."""
    from datetime import datetime

    # Provide default values for the new required fields
    now = datetime.now()
    return RawEvent.create_from_ics(
        graph_id=event_id,
        ics_content=content,
        source_url=source_url,
        subject=f"Test Event {event_id}",
        start_datetime=now.isoformat(),
        end_datetime=(now.replace(hour=now.hour + 1)).isoformat(),
        start_timezone="UTC",
        end_timezone="UTC",
    )


class TestDatabaseRawEventsStorage:
    """Test cases for raw events storage operations."""

    async def test_store_raw_events_when_empty_list_then_returns_true(self, temp_db):
        """Test storing empty list of raw events returns True."""
        result = await temp_db.store_raw_events([])
        assert result is True

    async def test_store_raw_events_when_valid_events_then_stores_successfully(self, temp_db):
        """Test storing valid raw events stores them in database."""
        raw_events = [
            create_test_raw_event("event1", "content1"),
            create_test_raw_event("event2", "content2"),
        ]

        result = await temp_db.store_raw_events(raw_events)
        assert result is True

        # Verify events were stored
        stored_event1 = await temp_db.get_raw_event_by_id("raw_event1")
        stored_event2 = await temp_db.get_raw_event_by_id("raw_event2")

        assert stored_event1 is not None
        assert stored_event1.graph_id == "event1"
        assert stored_event1.raw_ics_content == "content1"

        assert stored_event2 is not None
        assert stored_event2.graph_id == "event2"
        assert stored_event2.raw_ics_content == "content2"

    async def test_store_raw_events_when_duplicate_id_then_replaces_event(self, temp_db):
        """Test storing raw event with duplicate ID replaces existing event."""
        # Store initial event
        initial_event = create_test_raw_event("event1", "initial_content")
        await temp_db.store_raw_events([initial_event])

        # Store updated event with same ID
        updated_event = create_test_raw_event("event1", "updated_content")
        result = await temp_db.store_raw_events([updated_event])
        assert result is True

        # Verify the event was replaced
        stored_event = await temp_db.get_raw_event_by_id("raw_event1")
        assert stored_event.raw_ics_content == "updated_content"

    async def test_store_raw_events_when_large_content_then_stores_successfully(self, temp_db):
        """Test storing raw event with large content."""
        large_content = "X" * (1024 * 1024)  # 1MB content
        raw_event = create_test_raw_event("large_event", large_content)

        result = await temp_db.store_raw_events([raw_event])
        assert result is True

        stored_event = await temp_db.get_raw_event_by_id("raw_large_event")
        assert stored_event.raw_ics_content == large_content
        assert stored_event.content_size_bytes == len(large_content.encode("utf-8"))

    async def test_store_raw_events_when_with_source_url_then_stores_url(self, temp_db):
        """Test storing raw event with source URL stores the URL."""
        source_url = "https://example.com/calendar.ics"
        raw_event = create_test_raw_event("event1", "content", source_url)

        result = await temp_db.store_raw_events([raw_event])
        assert result is True

        stored_event = await temp_db.get_raw_event_by_id("raw_event1")
        assert stored_event.source_url == source_url

    async def test_store_raw_events_when_database_error_then_returns_false(self, temp_db):
        """Test storing raw events handles database errors gracefully."""
        raw_event = create_test_raw_event("event1", "content")

        # Mock aiosqlite.connect to raise an exception
        with patch(
            "calendarbot.cache.database.aiosqlite.connect", side_effect=Exception("Database error")
        ):
            result = await temp_db.store_raw_events([raw_event])
            assert result is False


class TestDatabaseRawEventsRetrieval:
    """Test cases for raw events retrieval operations."""

    async def test_get_raw_event_by_id_when_exists_then_returns_event(self, temp_db):
        """Test getting raw event by ID returns the event when it exists."""
        raw_event = create_test_raw_event("event1", "test_content")
        await temp_db.store_raw_events([raw_event])

        retrieved_event = await temp_db.get_raw_event_by_id("raw_event1")

        assert retrieved_event is not None
        assert retrieved_event.id == "raw_event1"
        assert retrieved_event.graph_id == "event1"
        assert retrieved_event.raw_ics_content == "test_content"

    async def test_get_raw_event_by_id_when_not_exists_then_returns_none(self, temp_db):
        """Test getting raw event by ID returns None when it doesn't exist."""
        retrieved_event = await temp_db.get_raw_event_by_id("nonexistent_event")
        assert retrieved_event is None

    async def test_get_raw_event_by_id_when_database_error_then_returns_none(self, temp_db):
        """Test getting raw event by ID handles database errors gracefully."""
        # Mock aiosqlite.connect to raise an exception
        with patch(
            "calendarbot.cache.database.aiosqlite.connect", side_effect=Exception("Database error")
        ):
            retrieved_event = await temp_db.get_raw_event_by_id("event1")
            assert retrieved_event is None


class TestDatabaseRawEventsCleanup:
    """Test cases for raw events cleanup operations."""

    async def test_cleanup_raw_events_when_no_old_events_then_returns_zero(self, temp_db):
        """Test cleanup returns zero when no old events exist."""
        # Store a recent event
        raw_event = create_test_raw_event("recent_event", "content")
        await temp_db.store_raw_events([raw_event])

        removed_count = await temp_db.cleanup_raw_events(days_old=7)
        assert removed_count == 0

    async def test_cleanup_raw_events_when_has_old_events_then_removes_them(self, temp_db):
        """Test cleanup removes events older than specified days."""
        # Store an old event by manipulating the cached_at timestamp
        old_event = create_test_raw_event("old_event", "old_content")

        # Manually insert with old timestamp
        old_timestamp = (datetime.now() - timedelta(days=10)).isoformat()

        # Store the event first, then update its timestamp
        await temp_db.store_raw_events([old_event])

        # Update the cached_at timestamp to be old
        import aiosqlite

        async with aiosqlite.connect(str(temp_db.database_path)) as db:
            await db.execute(
                "UPDATE raw_events SET cached_at = ? WHERE id = ?", (old_timestamp, "raw_old_event")
            )
            await db.commit()

        # Store a recent event
        recent_event = create_test_raw_event("recent_event", "recent_content")
        await temp_db.store_raw_events([recent_event])

        # Cleanup events older than 7 days
        removed_count = await temp_db.cleanup_raw_events(days_old=7)
        assert removed_count == 1

        # Verify old event was removed and recent event remains
        old_retrieved = await temp_db.get_raw_event_by_id("raw_old_event")
        recent_retrieved = await temp_db.get_raw_event_by_id("raw_recent_event")

        assert old_retrieved is None
        assert recent_retrieved is not None

    async def test_cleanup_raw_events_when_database_error_then_returns_zero(self, temp_db):
        """Test cleanup handles database errors gracefully."""
        # Mock aiosqlite.connect to raise an exception
        with patch(
            "calendarbot.cache.database.aiosqlite.connect", side_effect=Exception("Database error")
        ):
            removed_count = await temp_db.cleanup_raw_events(days_old=7)
            assert removed_count == 0

    async def test_clear_raw_events_when_empty_database_then_returns_true(self, temp_db):
        """Test clearing raw events from empty database returns True."""
        result = await temp_db.clear_raw_events()
        assert result is True

    async def test_clear_raw_events_when_has_events_then_clears_all(self, temp_db):
        """Test clearing raw events removes all events."""
        # Store multiple events
        raw_events = [
            create_test_raw_event("event1", "content1"),
            create_test_raw_event("event2", "content2"),
            create_test_raw_event("event3", "content3"),
        ]
        await temp_db.store_raw_events(raw_events)

        # Verify events were stored
        stored_event1 = await temp_db.get_raw_event_by_id("raw_event1")
        assert stored_event1 is not None

        # Clear all events
        result = await temp_db.clear_raw_events()
        assert result is True

        # Verify all events were removed
        stored_event1 = await temp_db.get_raw_event_by_id("raw_event1")
        stored_event2 = await temp_db.get_raw_event_by_id("raw_event2")
        stored_event3 = await temp_db.get_raw_event_by_id("raw_event3")

        assert stored_event1 is None
        assert stored_event2 is None
        assert stored_event3 is None

    async def test_clear_raw_events_when_database_error_then_returns_false(self, temp_db):
        """Test clearing raw events handles database errors gracefully."""
        # Mock aiosqlite.connect to raise an exception
        with patch(
            "calendarbot.cache.database.aiosqlite.connect", side_effect=Exception("Database error")
        ):
            result = await temp_db.clear_raw_events()
            assert result is False


class TestDatabaseRawEventsIntegration:
    """Test cases for integration scenarios with raw events."""

    async def test_foreign_key_constraint_when_raw_event_references_cached_event(self, temp_db):
        """Test that raw events properly reference cached events via foreign key."""
        # First store a cached event
        from calendarbot.cache.models import CachedEvent

        now = datetime.now()
        cached_event = CachedEvent(
            id="cached_test_event",
            graph_id="test_event",
            subject="Test Event",
            body_preview="Test body",
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

        await temp_db.store_events([cached_event])

        # Now store a raw event that references the cached event
        raw_event = create_test_raw_event("test_event", "raw_content")
        result = await temp_db.store_raw_events([raw_event])
        assert result is True

        # Verify the raw event was stored and references the cached event
        stored_raw_event = await temp_db.get_raw_event_by_id("raw_test_event")
        assert stored_raw_event is not None
        assert stored_raw_event.graph_id == "test_event"

    async def test_content_hash_uniqueness_when_different_content_then_different_hashes(
        self, temp_db
    ):
        """Test that different content produces different content hashes."""
        raw_event1 = create_test_raw_event("event1", "content1")
        raw_event2 = create_test_raw_event("event2", "content2")

        await temp_db.store_raw_events([raw_event1, raw_event2])

        stored_event1 = await temp_db.get_raw_event_by_id("raw_event1")
        stored_event2 = await temp_db.get_raw_event_by_id("raw_event2")

        assert stored_event1.content_hash != stored_event2.content_hash

    async def test_content_hash_consistency_when_same_content_then_same_hash(self, temp_db):
        """Test that identical content produces the same content hash."""
        content = "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR"

        raw_event1 = create_test_raw_event("event1", content)
        raw_event2 = create_test_raw_event("event2", content)

        await temp_db.store_raw_events([raw_event1, raw_event2])

        stored_event1 = await temp_db.get_raw_event_by_id("raw_event1")
        stored_event2 = await temp_db.get_raw_event_by_id("raw_event2")

        assert stored_event1.content_hash == stored_event2.content_hash
