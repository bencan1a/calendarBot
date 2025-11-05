"""Unit tests for event_filter module."""

import asyncio
import datetime
from typing import Any
from unittest.mock import Mock

import pytest

from calendarbot_lite.domain.event_filter import (
    EventFilter,
    EventWindowManager,
    SmartFallbackHandler,
)

pytestmark = pytest.mark.unit


class TestSmartFallbackHandler:
    """Tests for SmartFallbackHandler class."""

    def test_preserve_on_zero_events_with_existing(self):
        """Should preserve window when zero events returned but we have existing events."""
        handler = SmartFallbackHandler()

        should_preserve, message = handler.should_preserve_existing_window(
            parsed_events=[],
            existing_count=10,
            sources_count=2
        )

        assert should_preserve is True
        assert "all" in message.lower()
        assert "sources failed" in message.lower()
        assert "10 existing events" in message.lower()

    def test_do_not_preserve_when_new_events_available(self):
        """Should not preserve when new events are available."""
        handler = SmartFallbackHandler()

        should_preserve, message = handler.should_preserve_existing_window(
            parsed_events=[{"subject": "Meeting"}],
            existing_count=50,
            sources_count=1
        )

        assert should_preserve is False
        assert "processing new events normally" in message.lower()

    def test_do_not_preserve_on_reasonable_new_data(self):
        """Should not preserve when new data looks reasonable."""
        handler = SmartFallbackHandler()

        # 15 events from 2 sources is reasonable
        parsed_events = [{"subject": f"Meeting {i}"} for i in range(15)]

        should_preserve, message = handler.should_preserve_existing_window(
            parsed_events=parsed_events,
            existing_count=20,
            sources_count=2
        )

        assert should_preserve is False
        assert "processing new events normally" in message.lower()

    def test_do_not_preserve_when_no_existing_events(self):
        """Should not preserve when there are no existing events."""
        handler = SmartFallbackHandler()

        should_preserve, message = handler.should_preserve_existing_window(
            parsed_events=[],
            existing_count=0,
            sources_count=2
        )

        assert should_preserve is False
        assert "all sources failed" in message.lower()
        assert "no cached events" in message.lower()


class TestEventFilter:
    """Tests for EventFilter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.get_server_tz = Mock(return_value="America/Los_Angeles")
        self.get_fallback_tz = Mock(return_value="UTC")
        self.filter = EventFilter(self.get_server_tz, self.get_fallback_tz)

    @pytest.mark.smoke  # Critical path: Event filtering validation
    def test_filter_upcoming_events_removes_past_events(self):
        """Should filter out past events."""
        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        events = [
            {"subject": "Past Event", "start": datetime.datetime(2025, 11, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)},
            {"subject": "Future Event", "start": datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)},
        ]

        filtered = self.filter.filter_upcoming_events(events, now)

        assert len(filtered) == 1
        assert filtered[0]["subject"] == "Future Event"

    def test_filter_upcoming_events_handles_invalid_start(self):
        """Should skip events with invalid start times."""
        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        events = [
            {"subject": "No Start"},
            {"subject": "Invalid Start", "start": "not a datetime"},
            {"subject": "Valid Event", "start": datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)},
        ]

        filtered = self.filter.filter_upcoming_events(events, now)

        assert len(filtered) == 1
        assert filtered[0]["subject"] == "Valid Event"

    def test_filter_skipped_events_with_no_store(self):
        """Should return all events when no skip store."""
        events = [{"subject": "Event 1"}, {"subject": "Event 2"}]

        filtered = self.filter.filter_skipped_events(events, None)

        assert len(filtered) == 2

    def test_filter_skipped_events_removes_skipped(self):
        """Should filter out skipped events."""
        mock_store = Mock()
        mock_store.is_skipped = Mock(side_effect=lambda id: id == "skip-me")

        events = [
            {"subject": "Keep", "meeting_id": "keep-1"},
            {"subject": "Skip", "meeting_id": "skip-me"},
            {"subject": "Keep 2", "meeting_id": "keep-2"},
        ]

        filtered = self.filter.filter_skipped_events(events, mock_store)

        assert len(filtered) == 2
        assert filtered[0]["meeting_id"] == "keep-1"
        assert filtered[1]["meeting_id"] == "keep-2"

    def test_filter_skipped_events_handles_errors(self):
        """Should handle errors from skip store gracefully."""
        mock_store = Mock()
        mock_store.is_skipped = Mock(side_effect=Exception("Store error"))

        events = [{"subject": "Event", "meeting_id": "123"}]

        # Should not raise, just log warning and keep event
        filtered = self.filter.filter_skipped_events(events, mock_store)

        assert len(filtered) == 1


@pytest.mark.asyncio
class TestEventWindowManager:
    """Tests for EventWindowManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.get_server_tz = Mock(return_value="America/Los_Angeles")
        self.get_fallback_tz = Mock(return_value="UTC")
        self.event_filter = EventFilter(self.get_server_tz, self.get_fallback_tz)
        self.fallback_handler = SmartFallbackHandler()
        self.manager = EventWindowManager(self.event_filter, self.fallback_handler)

    async def test_update_window_with_valid_events(self):
        """Should update window with valid upcoming events."""
        event_window_ref: list[tuple[Any, ...]] = [()]
        window_lock = asyncio.Lock()

        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        parsed_events = [
            {"subject": "Past Event", "start": datetime.datetime(2025, 11, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)},
            {"subject": "Event 1", "start": datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)},
            {"subject": "Event 2", "start": datetime.datetime(2025, 11, 1, 16, 0, 0, tzinfo=datetime.timezone.utc)},
        ]

        updated, count, message = await self.manager.update_window(
            event_window_ref, window_lock, parsed_events, now, None, 50, 1
        )

        assert updated is True
        assert count == 2
        assert len(event_window_ref[0]) == 2
        assert event_window_ref[0][0]["subject"] == "Event 1"
        assert event_window_ref[0][1]["subject"] == "Event 2"

    async def test_update_window_with_fallback(self):
        """Should preserve existing window when all sources fail (empty parsed_events)."""
        # Set up existing window with 50 events
        base_time = datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)
        existing_events = tuple(
            {"subject": f"Event {i}", "start": base_time + datetime.timedelta(hours=i)}
            for i in range(50)
        )
        event_window_ref = [existing_events]
        window_lock = asyncio.Lock()

        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        # All sources failed - empty parsed events
        parsed_events = []

        updated, count, message = await self.manager.update_window(
            event_window_ref, window_lock, parsed_events, now, None, 50, 2
        )

        assert updated is False  # Fallback triggered
        assert count == 50  # Kept existing events
        assert "all" in message.lower()
        assert "sources failed" in message.lower()

    async def test_update_window_with_window_size_limit(self):
        """Should limit window to specified size."""
        event_window_ref: list[tuple[Any, ...]] = [()]
        window_lock = asyncio.Lock()

        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        # Create 100 future events
        base_time = datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)
        parsed_events = [
            {"subject": f"Event {i}", "start": base_time + datetime.timedelta(hours=i)}
            for i in range(100)
        ]

        updated, count, message = await self.manager.update_window(
            event_window_ref, window_lock, parsed_events, now, None, 50, 1
        )

        assert updated is True
        assert count == 50
        assert len(event_window_ref[0]) == 50

    async def test_update_window_sorts_by_start_time(self):
        """Should sort events by start time."""
        event_window_ref: list[tuple[Any, ...]] = [()]
        window_lock = asyncio.Lock()

        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        # Events in random order
        parsed_events = [
            {"subject": "Event 3", "start": datetime.datetime(2025, 11, 1, 18, 0, 0, tzinfo=datetime.timezone.utc)},
            {"subject": "Event 1", "start": datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)},
            {"subject": "Event 2", "start": datetime.datetime(2025, 11, 1, 16, 0, 0, tzinfo=datetime.timezone.utc)},
        ]

        updated, count, message = await self.manager.update_window(
            event_window_ref, window_lock, parsed_events, now, None, 50, 1
        )

        assert updated is True
        assert event_window_ref[0][0]["subject"] == "Event 1"
        assert event_window_ref[0][1]["subject"] == "Event 2"
        assert event_window_ref[0][2]["subject"] == "Event 3"
