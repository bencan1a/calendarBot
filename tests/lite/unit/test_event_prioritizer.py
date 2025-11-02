"""Unit tests for event_prioritizer module."""

import datetime
from unittest.mock import Mock
import pytest

from calendarbot_lite.event_prioritizer import EventCategory, EventPrioritizer

pytestmark = pytest.mark.unit


class TestEventPrioritizer:
    """Tests for EventPrioritizer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.is_focus_time = Mock(return_value=False)
        self.prioritizer = EventPrioritizer(self.is_focus_time)

    def test_find_next_event_returns_none_for_empty_window(self):
        """Should return None when no events in window."""
        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        result = self.prioritizer.find_next_event((), now, None)

        assert result is None

    def test_find_next_event_skips_past_events(self):
        """Should skip events that have already started."""
        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        events = (
            {"subject": "Past Event", "start": datetime.datetime(2025, 11, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)},
            {"subject": "Future Event", "start": datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)},
        )

        result = self.prioritizer.find_next_event(events, now, None)

        assert result is not None
        event, seconds_until = result
        assert event["subject"] == "Future Event"
        assert seconds_until > 0

    def test_find_next_event_skips_focus_time(self):
        """Should skip focus time events."""
        # Mock is_focus_time to return True for focus time events
        def check_focus(event):
            return "focus time" in event.get("subject", "").lower()

        self.is_focus_time = check_focus
        self.prioritizer = EventPrioritizer(self.is_focus_time)

        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        events = (
            {"subject": "Focus Time", "start": datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)},
            {"subject": "Real Meeting", "start": datetime.datetime(2025, 11, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)},
        )

        result = self.prioritizer.find_next_event(events, now, None)

        assert result is not None
        event, seconds_until = result
        assert event["subject"] == "Real Meeting"

    def test_find_next_event_skips_skipped_events(self):
        """Should skip events that are marked as skipped."""
        mock_store = Mock()
        mock_store.is_skipped = Mock(side_effect=lambda id: id == "skip-me")

        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        events = (
            {
                "subject": "Skipped Event",
                "meeting_id": "skip-me",
                "start": datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc),
            },
            {
                "subject": "Next Event",
                "meeting_id": "keep-1",
                "start": datetime.datetime(2025, 11, 1, 15, 0, 0, tzinfo=datetime.timezone.utc),
            },
        )

        result = self.prioritizer.find_next_event(events, now, mock_store)

        assert result is not None
        event, seconds_until = result
        assert event["subject"] == "Next Event"

    def test_find_next_event_calculates_seconds_until(self):
        """Should correctly calculate seconds until event start."""
        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        events = (
            {
                "subject": "Event in 2 hours",
                "start": datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc),
            },
        )

        result = self.prioritizer.find_next_event(events, now, None)

        assert result is not None
        event, seconds_until = result
        assert seconds_until == 7200  # 2 hours = 7200 seconds

    def test_categorize_event_as_lunch(self):
        """Should categorize lunch meetings correctly."""
        # Implementation only categorizes as LUNCH if subject contains "lunch" and is <= 10 chars
        lunch_events = [
            {"subject": "Lunch"},
            {"subject": "LUNCH"},
            {"subject": "lunch"},
        ]

        for event in lunch_events:
            category = self.prioritizer._categorize_event(event)
            assert category == EventCategory.LUNCH

    def test_categorize_event_as_business(self):
        """Should categorize business meetings correctly."""
        business_events = [
            {"subject": "Team Standup"},
            {"subject": "Project Review"},
            {"subject": "1:1 with Manager"},
        ]

        for event in business_events:
            category = self.prioritizer._categorize_event(event)
            assert category == EventCategory.BUSINESS

    def test_prioritize_business_over_lunch_when_similar_time(self):
        """Should prefer business meetings over lunch when they occur at similar times."""
        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        # Events within 30 minutes - business should be prioritized
        events = (
            {
                "subject": "Lunch",  # Short lunch event
                "start": datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc),
            },
            {
                "subject": "Important Meeting",
                "start": datetime.datetime(2025, 11, 1, 14, 15, 0, tzinfo=datetime.timezone.utc),  # 15 min later
            },
        )

        result = self.prioritizer.find_next_event(events, now, None)

        assert result is not None
        event, seconds_until = result
        # Should pick the business meeting even though lunch is earlier
        assert event["subject"] == "Important Meeting"

    def test_no_prioritization_when_events_far_apart(self):
        """Should not apply prioritization when events are far apart in time."""
        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        # Events more than 30 minutes apart - no prioritization
        events = (
            {
                "subject": "Lunch",
                "start": datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc),
            },
            {
                "subject": "Meeting",
                "start": datetime.datetime(2025, 11, 1, 15, 0, 0, tzinfo=datetime.timezone.utc),  # 1 hour later
            },
        )

        result = self.prioritizer.find_next_event(events, now, None)

        assert result is not None
        event, seconds_until = result
        # Should pick the first event (lunch) since they're far apart
        assert event["subject"] == "Lunch"
