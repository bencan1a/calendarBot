"""Unit tests for event_prioritizer module."""

import datetime
from unittest.mock import Mock

import pytest

from calendarbot_lite.event_prioritizer import EventCategory, EventPrioritizer
from calendarbot_lite.lite_models import LiteCalendarEvent, LiteDateTimeInfo

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
            LiteCalendarEvent(
                id="past-1",
                subject="Past Event",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)),
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 11, 0, 0, tzinfo=datetime.timezone.utc)),
            ),
            LiteCalendarEvent(
                id="future-1",
                subject="Future Event",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)),
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)),
            ),
        )

        result = self.prioritizer.find_next_event(events, now, None)

        assert result is not None
        event, seconds_until = result
        assert event.subject == "Future Event"
        assert seconds_until > 0

    def test_find_next_event_skips_focus_time(self):
        """Should skip focus time events."""
        # Mock is_focus_time to return True for focus time events
        def check_focus(event):
            return "focus time" in (event.subject or "").lower()

        self.is_focus_time = check_focus
        self.prioritizer = EventPrioritizer(self.is_focus_time)

        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        events = (
            LiteCalendarEvent(
                id="focus-1",
                subject="Focus Time",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)),
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 14, 30, 0, tzinfo=datetime.timezone.utc)),
            ),
            LiteCalendarEvent(
                id="meeting-1",
                subject="Real Meeting",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)),
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 16, 0, 0, tzinfo=datetime.timezone.utc)),
            ),
        )

        result = self.prioritizer.find_next_event(events, now, None)

        assert result is not None
        event, seconds_until = result
        assert event.subject == "Real Meeting"

    def test_find_next_event_skips_skipped_events(self):
        """Should skip events that are marked as skipped."""
        mock_store = Mock()
        mock_store.is_skipped = Mock(side_effect=lambda id: id == "skip-me")

        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        events = (
            LiteCalendarEvent(
                id="skip-me",
                subject="Skipped Event",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)),
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)),
            ),
            LiteCalendarEvent(
                id="keep-1",
                subject="Next Event",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)),
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 16, 0, 0, tzinfo=datetime.timezone.utc)),
            ),
        )

        result = self.prioritizer.find_next_event(events, now, mock_store)

        assert result is not None
        event, seconds_until = result
        assert event.subject == "Next Event"

    def test_find_next_event_calculates_seconds_until(self):
        """Should correctly calculate seconds until event start."""
        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        events = (
            LiteCalendarEvent(
                id="event-1",
                subject="Event in 2 hours",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)),
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)),
            ),
        )

        result = self.prioritizer.find_next_event(events, now, None)

        assert result is not None
        event, seconds_until = result
        assert seconds_until == 7200  # 2 hours = 7200 seconds

    def test_categorize_event_as_lunch(self):
        """Should categorize lunch meetings correctly."""
        # Implementation only categorizes as LUNCH if subject contains "lunch" and is <= 10 chars
        lunch_events = [
            LiteCalendarEvent(
                id="lunch-1",
                subject="Lunch",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)),
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 13, 0, 0, tzinfo=datetime.timezone.utc)),
            ),
            LiteCalendarEvent(
                id="lunch-2",
                subject="LUNCH",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)),
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 13, 0, 0, tzinfo=datetime.timezone.utc)),
            ),
            LiteCalendarEvent(
                id="lunch-3",
                subject="lunch",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)),
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 13, 0, 0, tzinfo=datetime.timezone.utc)),
            ),
        ]

        for event in lunch_events:
            category = self.prioritizer._categorize_event(event)
            assert category == EventCategory.LUNCH

    def test_categorize_event_as_business(self):
        """Should categorize business meetings correctly."""
        business_events = [
            LiteCalendarEvent(
                id="biz-1",
                subject="Team Standup",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 9, 0, 0, tzinfo=datetime.timezone.utc)),
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 9, 30, 0, tzinfo=datetime.timezone.utc)),
            ),
            LiteCalendarEvent(
                id="biz-2",
                subject="Project Review",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)),
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 11, 0, 0, tzinfo=datetime.timezone.utc)),
            ),
            LiteCalendarEvent(
                id="biz-3",
                subject="1:1 with Manager",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)),
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 14, 30, 0, tzinfo=datetime.timezone.utc)),
            ),
        ]

        for event in business_events:
            category = self.prioritizer._categorize_event(event)
            assert category == EventCategory.BUSINESS

    def test_prioritize_business_over_lunch_when_similar_time(self):
        """Should prefer business meetings over lunch when they occur at similar times."""
        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        # Events within 30 minutes - business should be prioritized
        events = (
            LiteCalendarEvent(
                id="lunch-event",
                subject="Lunch",  # Short lunch event
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)),
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)),
            ),
            LiteCalendarEvent(
                id="meeting-1",
                subject="Important Meeting",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 14, 15, 0, tzinfo=datetime.timezone.utc)),  # 15 min later
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)),
            ),
        )

        result = self.prioritizer.find_next_event(events, now, None)

        assert result is not None
        event, seconds_until = result
        # Should pick the business meeting even though lunch is earlier
        assert event.subject == "Important Meeting"

    def test_no_prioritization_when_events_far_apart(self):
        """Should not apply prioritization when events are far apart in time."""
        now = datetime.datetime(2025, 11, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

        # Events more than 30 minutes apart - no prioritization
        events = (
            LiteCalendarEvent(
                id="lunch-far",
                subject="Lunch",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)),
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)),
            ),
            LiteCalendarEvent(
                id="meeting-far",
                subject="Meeting",
                start=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)),  # 1 hour later
                end=LiteDateTimeInfo(date_time=datetime.datetime(2025, 11, 1, 16, 0, 0, tzinfo=datetime.timezone.utc)),
            ),
        )

        result = self.prioritizer.find_next_event(events, now, None)

        assert result is not None
        event, seconds_until = result
        # Should pick the first event (lunch) since they're far apart
        assert event.subject == "Lunch"
