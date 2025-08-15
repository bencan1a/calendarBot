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
        # Configure event filtering structure
        settings.event_filters = MagicMock()
        settings.event_filters.hidden_events = set()
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
        # Add required graph_id attribute for filtering logic
        event.graph_id = f"test_graph_id_{subject.replace(' ', '_').lower()}"
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
        # With new priority logic, upcoming meetings are prioritized over current meetings
        assert len(result.current_events) == 0
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

        # With new priority logic, upcoming meetings are prioritized over current meetings
        assert len(result.current_events) == 0, (
            "Should prioritize upcoming meetings over current meetings"
        )

        # Should have first 3 upcoming events as next_events
        assert len(result.next_events) == 3
        assert result.next_events[0].subject == "Upcoming 1"
        assert result.next_events[1].subject == "Upcoming 2"
        assert result.next_events[2].subject == "Upcoming 3"

        # Should have next 2 upcoming events as later_events
        assert len(result.later_events) == 2
        assert result.later_events[0].subject == "Upcoming 4"
        assert result.later_events[1].subject == "Upcoming 5"

    # ===========================================
    # NEXT MEETING PRIORITY TESTS
    # (Testing the core business rule: upcoming meetings prioritized over current meetings)
    # ===========================================

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_group_events_when_both_current_and_upcoming_exist_then_prioritize_upcoming(
        self, mock_get_now, logic
    ) -> None:
        """Test that upcoming meetings are prioritized when both current and upcoming exist.

        This tests the core business rule: US001 - Prioritize Next Meeting Over Current Meeting.
        """
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create current meeting (happening now) and upcoming meeting (in 30 minutes)
        current_meeting = self.create_mock_cached_event("Current Meeting", -1, 1)  # 11am-1pm
        current_meeting.is_current = MagicMock(return_value=True)
        current_meeting.is_upcoming = MagicMock(return_value=False)

        upcoming_meeting = self.create_mock_cached_event(
            "Upcoming Meeting", 0.5, 1.5
        )  # 12:30pm-1:30pm
        upcoming_meeting.is_current = MagicMock(return_value=False)
        upcoming_meeting.is_upcoming = MagicMock(return_value=True)

        events = [current_meeting, upcoming_meeting]

        current_events, upcoming_events, later_events = logic._group_events(events, current_time)

        # Core assertion: When both exist, current_events should be empty (prioritizing upcoming)
        assert len(current_events) == 0, (
            "Current events should be empty when upcoming meetings exist"
        )
        assert len(upcoming_events) == 1, "Should have one upcoming meeting"
        assert upcoming_events[0].subject == "Upcoming Meeting", (
            "Should select the upcoming meeting"
        )

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_group_events_when_only_current_meetings_exist_then_select_current(
        self, mock_get_now, logic
    ) -> None:
        """Test fallback to current meetings when no upcoming meetings exist.

        This tests the fallback behavior for US005 - Handle No Upcoming Meetings State.
        """
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create only current meetings (no upcoming meetings)
        current_meeting1 = self.create_mock_cached_event("Current Meeting 1", -1, 1)  # 11am-1pm
        current_meeting1.is_current = MagicMock(return_value=True)
        current_meeting1.is_upcoming = MagicMock(return_value=False)

        current_meeting2 = self.create_mock_cached_event(
            "Current Meeting 2", -0.5, 0.5
        )  # 11:30am-12:30pm
        current_meeting2.is_current = MagicMock(return_value=True)
        current_meeting2.is_upcoming = MagicMock(return_value=False)

        events = [current_meeting1, current_meeting2]

        current_events, upcoming_events, later_events = logic._group_events(events, current_time)

        # Fallback assertion: Should select current meetings when no upcoming meetings exist
        assert len(current_events) == 1, (
            "Should fallback to current meetings when no upcoming meetings"
        )
        assert len(upcoming_events) == 0, "Should have no upcoming meetings"
        assert current_events[0].subject == "Current Meeting 1", (
            "Should select first current meeting"
        )

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_group_events_when_only_upcoming_meetings_exist_then_select_upcoming(
        self, mock_get_now, logic
    ) -> None:
        """Test that upcoming meetings are selected when only upcoming meetings exist.

        This tests US002 - Calculate Countdown to Next Meeting Start Time.
        """
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create only upcoming meetings
        upcoming_meeting1 = self.create_mock_cached_event("Upcoming Meeting 1", 1, 2)  # 1pm-2pm
        upcoming_meeting1.is_current = MagicMock(return_value=False)
        upcoming_meeting1.is_upcoming = MagicMock(return_value=True)

        upcoming_meeting2 = self.create_mock_cached_event("Upcoming Meeting 2", 2, 3)  # 2pm-3pm
        upcoming_meeting2.is_current = MagicMock(return_value=False)
        upcoming_meeting2.is_upcoming = MagicMock(return_value=True)

        events = [upcoming_meeting1, upcoming_meeting2]

        current_events, upcoming_events, later_events = logic._group_events(events, current_time)

        # Upcoming-only assertion: Should select upcoming meetings in chronological order
        assert len(current_events) == 0, "Should have no current events"
        assert len(upcoming_events) == 2, "Should have all upcoming meetings"
        assert upcoming_events[0].subject == "Upcoming Meeting 1", (
            "Should select earliest upcoming meeting first"
        )
        assert upcoming_events[1].subject == "Upcoming Meeting 2", (
            "Should maintain chronological order"
        )

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_group_events_when_no_meetings_exist_then_return_empty(
        self, mock_get_now, logic
    ) -> None:
        """Test graceful handling when no meetings exist.

        This tests edge case for US005 - Handle No Upcoming Meetings State.
        """
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        events = []

        current_events, upcoming_events, later_events = logic._group_events(events, current_time)

        # Empty state assertion: All arrays should be empty
        assert len(current_events) == 0, "Should have no current events when no meetings exist"
        assert len(upcoming_events) == 0, "Should have no upcoming events when no meetings exist"
        assert len(later_events) == 0, "Should have no later events when no meetings exist"

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_group_events_when_back_to_back_meetings_then_select_next_deterministically(
        self, mock_get_now, logic
    ) -> None:
        """Test handling of consecutive meetings (back-to-back scenarios).

        This tests US004 - Handle Consecutive Meetings.
        """
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create back-to-back meetings: current meeting ends when next meeting starts
        current_meeting = self.create_mock_cached_event(
            "Current Meeting", -1, 0
        )  # 11am-12pm (ends now)
        current_meeting.is_current = MagicMock(
            return_value=True
        )  # Still considered current at end time
        current_meeting.is_upcoming = MagicMock(return_value=False)

        next_meeting = self.create_mock_cached_event("Next Meeting", 0, 1)  # 12pm-1pm (starts now)
        next_meeting.is_current = MagicMock(return_value=False)  # Not yet current at start time
        next_meeting.is_upcoming = MagicMock(return_value=True)
        # Set start_dt to be in the future so it's considered upcoming by _group_events
        next_meeting.start_dt = current_time + timedelta(minutes=1)

        events = [current_meeting, next_meeting]

        current_events, upcoming_events, later_events = logic._group_events(events, current_time)

        # Back-to-back assertion: Should prioritize the upcoming meeting
        assert len(current_events) == 0, (
            "Should prioritize upcoming meeting in back-to-back scenario"
        )
        assert len(upcoming_events) == 1, "Should have one upcoming meeting"
        assert upcoming_events[0].subject == "Next Meeting", (
            "Should select the next meeting deterministically"
        )

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_group_events_when_all_meetings_hidden_then_handle_gracefully(
        self, mock_get_now, logic
    ) -> None:
        """Test graceful handling when all meetings are hidden by event filters.

        This tests edge case handling with hidden events.
        """
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create meetings but mark them as hidden
        meeting1 = self.create_mock_cached_event("Hidden Meeting 1", 1, 2)
        meeting1.graph_id = "hidden_meeting_1"
        meeting2 = self.create_mock_cached_event("Hidden Meeting 2", 2, 3)
        meeting2.graph_id = "hidden_meeting_2"

        # Configure settings to hide these meetings
        logic.settings.event_filters.hidden_events = {"hidden_meeting_1", "hidden_meeting_2"}

        events = [meeting1, meeting2]

        current_events, upcoming_events, later_events = logic._group_events(events, current_time)

        # Hidden events assertion: Should return empty when all meetings are hidden
        assert len(current_events) == 0, (
            "Should have no current events when all meetings are hidden"
        )
        assert len(upcoming_events) == 0, (
            "Should have no upcoming events when all meetings are hidden"
        )
        assert len(later_events) == 0, "Should have no later events when all meetings are hidden"

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_group_events_when_mixed_visibility_then_filter_correctly(
        self, mock_get_now, logic
    ) -> None:
        """Test filtering behavior with mixed visible and hidden meetings.

        This tests proper filtering logic with hidden events.
        """
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create mix of visible and hidden meetings
        visible_meeting = self.create_mock_cached_event("Visible Meeting", 1, 2)
        visible_meeting.graph_id = "visible_meeting"

        hidden_meeting = self.create_mock_cached_event("Hidden Meeting", 0.5, 1.5)
        hidden_meeting.graph_id = "hidden_meeting"

        # Configure settings to hide only one meeting
        logic.settings.event_filters.hidden_events = {"hidden_meeting"}

        events = [visible_meeting, hidden_meeting]

        current_events, upcoming_events, later_events = logic._group_events(events, current_time)

        # Filtering assertion: Should only show visible meetings
        assert len(upcoming_events) == 1, "Should have one upcoming meeting after filtering"
        assert upcoming_events[0].subject == "Visible Meeting", "Should only show visible meetings"

    # ===========================================
    # DEBUG LOGGING VALIDATION TESTS
    # ===========================================

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    @patch("calendarbot.display.whats_next_logic.logger")
    def test_group_events_logs_meeting_selection_decisions(
        self, mock_logger, mock_get_now, logic
    ) -> None:
        """Test that debug logging captures meeting selection decisions.

        This validates that the debug logging added for meeting selection is working.
        """
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create both current and upcoming meetings to trigger priority logging
        current_meeting = self.create_mock_cached_event("Current Meeting", -1, 1)
        current_meeting.is_current = MagicMock(return_value=True)

        upcoming_meeting = self.create_mock_cached_event("Upcoming Meeting", 1, 2)

        events = [current_meeting, upcoming_meeting]

        logic._group_events(events, current_time)

        # Debug logging assertion: Should log the priority decision
        debug_calls = [
            call for call in mock_logger.debug.call_args_list if "Meeting selection" in str(call)
        ]
        assert len(debug_calls) > 0, "Should log meeting selection decisions"

        # Check that the log message indicates prioritizing upcoming meetings
        priority_log_found = any(
            "Prioritizing upcoming meetings" in str(call) for call in debug_calls
        )
        assert priority_log_found, "Should log that upcoming meetings are being prioritized"

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    @patch("calendarbot.display.whats_next_logic.logger")
    def test_group_events_logs_fallback_to_current_meetings(
        self, mock_logger, mock_get_now, logic
    ) -> None:
        """Test that debug logging captures fallback to current meetings.

        This validates fallback logging when no upcoming meetings exist.
        """
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create only current meetings (no upcoming)
        current_meeting = self.create_mock_cached_event("Current Meeting", -1, 1)
        current_meeting.is_current = MagicMock(return_value=True)

        events = [current_meeting]

        logic._group_events(events, current_time)

        # Fallback logging assertion: Should log the fallback decision
        debug_calls = [
            call for call in mock_logger.debug.call_args_list if "Meeting selection" in str(call)
        ]
        assert len(debug_calls) > 0, "Should log meeting selection decisions"

        # Check that the log message indicates falling back to current meetings
        fallback_log_found = any(
            "falling back to current meetings" in str(call) for call in debug_calls
        )
        assert fallback_log_found, (
            "Should log fallback to current meetings when no upcoming meetings"
        )

    # ===========================================
    # USER STORY VALIDATION TESTS
    # ===========================================

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_us001_prioritize_next_meeting_over_current_meeting_in_business_logic(
        self, mock_get_now, logic
    ) -> None:
        """US001: Prioritize Next Meeting Over Current Meeting in Business Logic.

        Validates that the business logic correctly prioritizes upcoming meetings
        over current meetings when both are present.
        """
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Business scenario: User is in a current meeting, next meeting starts in 30 minutes
        current_meeting = self.create_mock_cached_event(
            "Current Team Standup", -0.5, 0.5
        )  # 11:30am-12:30pm
        current_meeting.is_current = MagicMock(return_value=True)

        next_meeting = self.create_mock_cached_event("Next Client Call", 0.5, 1.5)  # 12:30pm-1:30pm

        events = [current_meeting, next_meeting]

        result = logic.create_view_model(events, {})

        # US001 assertion: Should display next meeting, not current meeting
        assert len(result.current_events) == 0, (
            "US001: Should not display current meeting when next meeting exists"
        )
        assert len(result.next_events) == 1, "US001: Should display next meeting"
        assert result.next_events[0].subject == "Next Client Call", (
            "US001: Should prioritize the upcoming meeting"
        )

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_us002_calculate_countdown_to_next_meeting_start_time(
        self, mock_get_now, logic
    ) -> None:
        """US002: Calculate Countdown to Next Meeting Start Time.

        Validates that countdown calculations work correctly for next meeting start times.
        """
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Business scenario: Next meeting starts in 2 hours
        next_meeting = self.create_mock_cached_event("Next Meeting", 2, 3)  # 2pm-3pm

        events = [next_meeting]

        result = logic.create_view_model(events, {})

        # US002 assertion: Should calculate time to next meeting start
        assert len(result.next_events) == 1, "US002: Should have next meeting for countdown"
        next_event = result.next_events[0]
        assert next_event.subject == "Next Meeting", "US002: Should identify correct next meeting"

        # Validate countdown calculation (time until meeting start)
        time_until_start = next_event.start_time - result.current_time
        hours_until = time_until_start.total_seconds() / 3600
        assert abs(hours_until - 2.0) < 0.01, (
            "US002: Should correctly calculate 2 hours until start"
        )

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_us003_populate_display_with_next_meeting_information(
        self, mock_get_now, logic
    ) -> None:
        """US003: Populate Display with Next Meeting Information.

        Validates that the display is populated with correct next meeting information.
        """
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Business scenario: Next meeting with full details
        next_meeting = self.create_mock_cached_event("Project Review Meeting", 1, 2)
        next_meeting.location_display_name = "Conference Room A"

        events = [next_meeting]

        result = logic.create_view_model(events, {})

        # US003 assertion: Should populate display with next meeting details
        assert len(result.next_events) == 1, "US003: Should have next meeting data"
        next_event = result.next_events[0]
        assert next_event.subject == "Project Review Meeting", "US003: Should display meeting title"
        assert next_event.location == "Conference Room A", "US003: Should display meeting location"
        assert next_event.formatted_time_range is not None, "US003: Should display formatted time"

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_us004_handle_consecutive_meetings_back_to_back_scenarios(
        self, mock_get_now, logic
    ) -> None:
        """US004: Handle Consecutive Meetings (back-to-back scenarios).

        Validates deterministic handling of back-to-back meetings.
        """
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Business scenario: Current meeting ends exactly when next meeting starts
        current_meeting = self.create_mock_cached_event("Current Meeting", -1, 0)  # 11am-12pm
        current_meeting.is_current = MagicMock(return_value=True)
        current_meeting.is_upcoming = MagicMock(return_value=False)

        consecutive_meeting = self.create_mock_cached_event("Consecutive Meeting", 0, 1)  # 12pm-1pm
        consecutive_meeting.is_current = MagicMock(return_value=False)
        consecutive_meeting.is_upcoming = MagicMock(return_value=True)
        # Set start_dt to be in the future so it's considered upcoming by _group_events
        consecutive_meeting.start_dt = current_time + timedelta(minutes=1)

        events = [current_meeting, consecutive_meeting]

        result = logic.create_view_model(events, {})

        # US004 assertion: With new priority logic, upcoming meetings are prioritized
        assert len(result.current_events) == 0, (
            "US004: Should prioritize consecutive meeting over ending meeting"
        )
        assert len(result.next_events) == 1, "US004: Should display consecutive meeting"
        assert result.next_events[0].subject == "Consecutive Meeting", (
            "US004: Should select the consecutive meeting"
        )

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_us005_handle_no_upcoming_meetings_state(self, mock_get_now, logic) -> None:
        """US005: Handle No Upcoming Meetings State.

        Validates graceful handling when no upcoming meetings exist.
        """
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Business scenario: Only past meetings and current meeting, no upcoming
        past_meeting = self.create_mock_cached_event("Past Meeting", -3, -2)  # 9am-10am
        current_meeting = self.create_mock_cached_event("Current Meeting", -1, 1)  # 11am-1pm
        current_meeting.is_current = MagicMock(return_value=True)

        events = [past_meeting, current_meeting]

        result = logic.create_view_model(events, {})

        # US005 assertion: Should gracefully handle no upcoming meetings
        assert len(result.next_events) == 0, "US005: Should have no upcoming meetings"
        assert len(result.current_events) == 1, "US005: Should fallback to showing current meeting"
        assert result.current_events[0].subject == "Current Meeting", (
            "US005: Should display current meeting as fallback"
        )

    # ===========================================
    # TIMEZONE AND BOUNDARY TESTS
    # ===========================================

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_group_events_when_timezone_boundary_then_maintain_consistency(
        self, mock_get_now, logic
    ) -> None:
        """Test timezone handling consistency for meeting selection.

        This tests edge case handling across timezone boundaries.
        """
        # Test with timezone-aware datetime (simulating timezone boundary conditions)
        current_time = datetime(2025, 7, 14, 23, 59, 59)  # Just before midnight
        mock_get_now.return_value = current_time

        # Create meeting that crosses midnight boundary
        late_meeting = self.create_mock_cached_event(
            "Late Meeting", 0.5, 1.5
        )  # 30 minutes after midnight
        late_meeting.is_current = MagicMock(return_value=False)
        late_meeting.is_upcoming = MagicMock(return_value=True)
        # Set start_dt to be in the future so it's considered upcoming by _group_events
        late_meeting.start_dt = current_time + timedelta(minutes=30)

        events = [late_meeting]

        current_events, upcoming_events, later_events = logic._group_events(events, current_time)

        # Timezone boundary assertion: Should handle timezone boundaries correctly
        assert len(upcoming_events) == 1, "Should handle timezone boundaries correctly"
        assert upcoming_events[0].subject == "Late Meeting", (
            "Should select meeting across timezone boundary"
        )

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_group_events_when_meeting_transitions_then_update_correctly(
        self, mock_get_now, logic
    ) -> None:
        """Test behavior at exact meeting start/end times.

        This tests boundary conditions at exact meeting transition times.
        """
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create meeting that starts exactly at current time
        meeting_starting_now = self.create_mock_cached_event(
            "Meeting Starting Now", 0, 1
        )  # 12pm-1pm
        meeting_starting_now.is_current = MagicMock(return_value=False)  # Not yet current
        meeting_starting_now.is_upcoming = MagicMock(return_value=True)  # Still upcoming
        # Set start_dt to be in the future so it's considered upcoming by _group_events
        meeting_starting_now.start_dt = current_time + timedelta(minutes=1)

        events = [meeting_starting_now]

        current_events, upcoming_events, later_events = logic._group_events(events, current_time)

        # Meeting transition assertion: Should handle exact transition times
        assert len(upcoming_events) == 1, "Should handle meeting starting at exact current time"
        assert upcoming_events[0].subject == "Meeting Starting Now", (
            "Should select meeting at transition boundary"
        )
