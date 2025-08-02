"""Tests for WhatsNextLogic business logic class."""

from datetime import datetime, timedelta
from typing import Optional, Union
from unittest.mock import MagicMock, patch

import pytest

from calendarbot.cache.models import CachedEvent
from calendarbot.display.whats_next_data_model import WhatsNextViewModel
from calendarbot.display.whats_next_logic import WhatsNextLogic


class TestWhatsNextLogic:
    """Test WhatsNextLogic class functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings object."""
        settings = MagicMock()
        settings.web_layout = "whats-next-view"
        settings.debug_time = None
        return settings

    @pytest.fixture
    def logic(self, mock_settings):
        """Create WhatsNextLogic instance for testing."""
        return WhatsNextLogic(mock_settings)

    def create_mock_cached_event(
        self,
        subject: str = "Test Event",
        start_hours_offset: Union[int, float] = 1,
        end_hours_offset: Union[int, float] = 2,
        location: Optional[str] = None,
    ) -> CachedEvent:
        """Create a mock CachedEvent for testing."""
        base_time = datetime(2025, 7, 14, 12, 0, 0)
        start_dt = base_time + timedelta(hours=start_hours_offset)
        end_dt = base_time + timedelta(hours=end_hours_offset)

        event = MagicMock(spec=CachedEvent)
        event.subject = subject
        event.start_dt = start_dt
        event.end_dt = end_dt
        event.location_display_name = location
        event.format_time_range.return_value = (
            f"{start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}"
        )
        event.is_current.return_value = start_dt <= base_time < end_dt
        event.is_upcoming.return_value = start_dt > base_time

        return event

    def test_init_when_called_then_initializes_successfully(self, mock_settings) -> None:
        """Test WhatsNextLogic initialization."""
        logic = WhatsNextLogic(mock_settings)

        assert logic is not None
        assert isinstance(logic, WhatsNextLogic)

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_get_current_time_when_no_debug_time_then_returns_now(
        self, mock_get_now, logic
    ) -> None:
        """Test get_current_time returns current time when no debug time."""
        mock_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = mock_time

        result = logic.get_current_time()

        assert result == mock_time
        mock_get_now.assert_called_once()

    def test_get_current_time_when_debug_time_set_then_returns_debug_time(self, logic) -> None:
        """Test get_current_time returns debug time when set."""
        debug_time = datetime(2025, 7, 14, 15, 30, 0)
        logic.set_debug_time(debug_time)

        result = logic.get_current_time()

        assert result == debug_time

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_find_next_upcoming_event_when_upcoming_events_exist_then_returns_earliest(
        self, mock_get_now, logic
    ) -> None:
        """Test finding next upcoming event with multiple upcoming events."""
        mock_get_now.return_value = datetime(2025, 7, 14, 12, 0, 0)

        # Create events: past, current, future1, future2
        events = [
            self.create_mock_cached_event("Past Event", -2, -1),  # 10am-11am (past)
            self.create_mock_cached_event("Current Event", -1, 1),  # 11am-1pm (current)
            self.create_mock_cached_event("Future Event 2", 4, 5),  # 4pm-5pm (later)
            self.create_mock_cached_event("Future Event 1", 2, 3),  # 2pm-3pm (next)
        ]

        result = logic.find_next_upcoming_event(events)

        assert result is not None
        assert result.subject == "Future Event 1"

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_find_next_upcoming_event_when_no_upcoming_events_then_returns_none(
        self, mock_get_now, logic
    ) -> None:
        """Test finding next upcoming event when no upcoming events exist."""
        mock_get_now.return_value = datetime(2025, 7, 14, 12, 0, 0)

        # Create only past and current events
        events = [
            self.create_mock_cached_event("Past Event", -2, -1),  # 10am-11am
            self.create_mock_cached_event("Current Event", -1, 1),  # 11am-1pm
        ]

        # Set is_upcoming to False for all events
        for event in events:
            event.is_upcoming = MagicMock(return_value=False)

        result = logic.find_next_upcoming_event(events)

        assert result is None

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_find_next_upcoming_event_when_empty_list_then_returns_none(
        self, mock_get_now, logic
    ) -> None:
        """Test finding next upcoming event with empty event list."""
        mock_get_now.return_value = datetime(2025, 7, 14, 12, 0, 0)

        result = logic.find_next_upcoming_event([])

        assert result is None

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_find_next_upcoming_event_when_error_occurs_then_returns_none(
        self, mock_get_now, logic
    ) -> None:
        """Test error handling in find_next_upcoming_event."""
        mock_get_now.side_effect = Exception("Time error")

        events = [self.create_mock_cached_event("Test Event", 1, 2)]

        result = logic.find_next_upcoming_event(events)

        assert result is None

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_create_view_model_when_valid_events_then_returns_view_model(
        self, mock_get_now, logic
    ) -> None:
        """Test creating WhatsNextViewModel from events and status info."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create mock events
        current_event = self.create_mock_cached_event("Current Meeting", -1, 1)
        current_event.is_current = MagicMock(return_value=True)
        current_event.is_upcoming = MagicMock(return_value=False)

        upcoming_event = self.create_mock_cached_event("Next Meeting", 2, 3)
        upcoming_event.is_current = MagicMock(return_value=False)
        upcoming_event.is_upcoming = MagicMock(return_value=True)

        events = [current_event, upcoming_event]
        status_info = {"is_cached": True, "connection_status": "Connected"}

        result = logic.create_view_model(events, status_info)

        assert isinstance(result, WhatsNextViewModel)
        assert result.current_time == current_time
        assert len(result.current_events) == 1
        assert len(result.next_events) == 1
        assert result.status_info.is_cached is True

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_create_view_model_when_no_events_then_returns_empty_view_model(
        self, mock_get_now, logic
    ) -> None:
        """Test creating WhatsNextViewModel with no events."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        events: list[CachedEvent] = []
        status_info = {"is_cached": False}

        result = logic.create_view_model(events, status_info)

        assert isinstance(result, WhatsNextViewModel)
        assert result.current_time == current_time
        assert len(result.current_events) == 0
        assert len(result.next_events) == 0
        assert len(result.later_events) == 0
        assert result.status_info.is_cached is False

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_create_view_model_when_none_status_info_then_handles_gracefully(
        self, mock_get_now, logic
    ) -> None:
        """Test creating WhatsNextViewModel with None status info."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        events: list[CachedEvent] = []

        result = logic.create_view_model(events, None)

        assert isinstance(result, WhatsNextViewModel)
        assert result.current_time == current_time
        assert result.status_info is not None

    def test_create_view_model_when_error_occurs_then_handles_gracefully(self, logic) -> None:
        """Test error handling in create_view_model."""
        # Force an error by passing None events
        result = logic.create_view_model(None, {"test": "data"})

        # Should handle gracefully and return something
        assert result is not None

    def test_type_compliance_for_methods(self, logic) -> None:
        """Test that all methods have proper type compliance."""
        # get_current_time should return datetime
        with patch("calendarbot.display.whats_next_logic.get_timezone_aware_now") as mock_now:
            mock_now.return_value = datetime(2025, 7, 14, 12, 0, 0)
            result = logic.get_current_time()
            assert isinstance(result, datetime)

        # find_next_upcoming_event should return CachedEvent or None
        with patch("calendarbot.display.whats_next_logic.get_timezone_aware_now") as mock_now:
            mock_now.return_value = datetime(2025, 7, 14, 12, 0, 0)
            result = logic.find_next_upcoming_event([])
            assert result is None

        # create_view_model should return WhatsNextViewModel
        with patch("calendarbot.display.whats_next_logic.get_timezone_aware_now") as mock_now:
            mock_now.return_value = datetime(2025, 7, 14, 12, 0, 0)
            result = logic.create_view_model([], {})
            assert isinstance(result, WhatsNextViewModel)

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_event_grouping_logic_when_multiple_event_types_then_groups_correctly(
        self, mock_get_now, logic
    ) -> None:
        """Test that events are correctly grouped by type (current, next, later)."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create multiple events of different types
        current1 = self.create_mock_cached_event("Current 1", -1, 1)
        current1.is_current = MagicMock(return_value=True)
        current1.is_upcoming = MagicMock(return_value=False)

        current2 = self.create_mock_cached_event(
            "Current 2", -0.5, 0.5
        )  # Use float for more realistic offset
        current2.is_current = MagicMock(return_value=True)
        current2.is_upcoming = MagicMock(return_value=False)

        upcoming1 = self.create_mock_cached_event("Upcoming 1", 1, 2)
        upcoming1.is_current = MagicMock(return_value=False)
        upcoming1.is_upcoming = MagicMock(return_value=True)

        upcoming2 = self.create_mock_cached_event("Upcoming 2", 2, 3)
        upcoming2.is_current = MagicMock(return_value=False)
        upcoming2.is_upcoming = MagicMock(return_value=True)

        upcoming3 = self.create_mock_cached_event("Upcoming 3", 3, 4)
        upcoming3.is_current = MagicMock(return_value=False)
        upcoming3.is_upcoming = MagicMock(return_value=True)

        upcoming4 = self.create_mock_cached_event("Upcoming 4", 4, 5)
        upcoming4.is_current = MagicMock(return_value=False)
        upcoming4.is_upcoming = MagicMock(return_value=True)

        upcoming5 = self.create_mock_cached_event("Upcoming 5", 5, 6)
        upcoming5.is_current = MagicMock(return_value=False)
        upcoming5.is_upcoming = MagicMock(return_value=True)

        events = [current1, current2, upcoming1, upcoming2, upcoming3, upcoming4, upcoming5]

        result = logic.create_view_model(events, {})

        # Should have only one current event (first one found)
        assert len(result.current_events) == 1
        assert result.current_events[0].subject == "Current 1"

        # Should have first 3 upcoming events as next_events
        assert len(result.next_events) == 3
        assert result.next_events[0].subject == "Upcoming 1"
        assert result.next_events[1].subject == "Upcoming 2"
        assert result.next_events[2].subject == "Upcoming 3"

        # Should have next 2 upcoming events as later_events
        assert len(result.later_events) == 2
        assert result.later_events[0].subject == "Upcoming 4"
        assert result.later_events[1].subject == "Upcoming 5"
