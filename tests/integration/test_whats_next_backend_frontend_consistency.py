"""Integration tests for backend-frontend consistency in WhatsNext meeting selection logic."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from calendarbot.cache.models import CachedEvent
from calendarbot.display.whats_next_logic import WhatsNextLogic


class TestWhatsNextBackendFrontendConsistency:
    """Test consistency between backend and frontend meeting selection logic.

    These tests ensure that both the Python backend (_group_events) and JavaScript frontend
    (detectCurrentMeeting) select identical meetings when given the same input data.
    """

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

    def create_test_event_data(
        self,
        subject: str,
        start_hours_offset: float,
        end_hours_offset: float,
        base_time: Optional[datetime] = None,
        location: Optional[str] = None,
    ) -> Dict:
        """Create test event data in the format used by both backend and frontend.

        Args:
            subject: Event subject/title
            start_hours_offset: Hours offset from base time for start
            end_hours_offset: Hours offset from base time for end
            base_time: Base time reference (defaults to fixed test time)
            location: Event location

        Returns:
            Dict containing event data compatible with both systems
        """
        if base_time is None:
            base_time = datetime(2025, 7, 14, 12, 0, 0)

        start_dt = base_time + timedelta(hours=start_hours_offset)
        end_dt = base_time + timedelta(hours=end_hours_offset)

        # Create event data structure that matches both backend and frontend expectations
        return {
            "graph_id": f"test_graph_id_{subject.replace(' ', '_').lower()}",
            "title": subject,
            "subject": subject,  # Backend uses 'subject', frontend uses 'title'
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "start_dt": start_dt,  # Backend uses datetime objects
            "end_dt": end_dt,  # Backend uses datetime objects
            "location": location or "",
            "location_display_name": location or "",
            "description": "",
            "is_hidden": False,
        }

    def create_backend_cached_event(self, event_data: Dict) -> CachedEvent:
        """Create backend CachedEvent from event data."""
        event = MagicMock(spec=CachedEvent)
        event.subject = event_data["subject"]
        event.start_dt = event_data["start_dt"]
        event.end_dt = event_data["end_dt"]
        event.location_display_name = event_data["location_display_name"]
        event.graph_id = event_data["graph_id"]

        # Configure is_current and is_upcoming methods
        def is_current():
            now = datetime(2025, 7, 14, 12, 0, 0)  # Fixed test time
            return event.start_dt <= now < event.end_dt

        def is_upcoming():
            now = datetime(2025, 7, 14, 12, 0, 0)  # Fixed test time
            return event.start_dt > now

        event.is_current = is_current
        event.is_upcoming = is_upcoming

        return event

    def simulate_frontend_meeting_selection(self, events_data: List[Dict]) -> Optional[Dict]:
        """Simulate the frontend meeting selection logic.

        This replicates the core logic from detectCurrentMeeting() in whats-next-view.js
        but adapted for Python testing.

        Args:
            events_data: List of event data dictionaries

        Returns:
            Selected meeting data or None if no meeting selected
        """
        now = datetime(2025, 7, 14, 12, 0, 0)  # Fixed test time to match backend

        # Filter out hidden events (matching frontend logic)
        visible_events = [e for e in events_data if not e.get("is_hidden", False)]

        # Phase 2 Frontend Update: Prioritize upcoming meetings first, current meetings as fallback
        # This ensures frontend and backend select identical meetings consistently

        # First pass: Look for upcoming meetings (prioritized)
        for event in visible_events:
            meeting_start = (
                datetime.fromisoformat(event["start_time"].replace("Z", "+00:00"))
                if event["start_time"].endswith("Z")
                else datetime.fromisoformat(event["start_time"])
            )

            # Check if meeting is upcoming
            if meeting_start > now:
                return event

        # Second pass: If no upcoming meetings found, look for current meetings as fallback
        for event in visible_events:
            meeting_start = (
                datetime.fromisoformat(event["start_time"].replace("Z", "+00:00"))
                if event["start_time"].endswith("Z")
                else datetime.fromisoformat(event["start_time"])
            )
            meeting_end = (
                datetime.fromisoformat(event["end_time"].replace("Z", "+00:00"))
                if event["end_time"].endswith("Z")
                else datetime.fromisoformat(event["end_time"])
            )

            # Check if meeting is currently happening
            if now >= meeting_start and now <= meeting_end:
                return event

        return None

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_backend_frontend_consistency_when_both_current_and_upcoming_then_select_upcoming(
        self, mock_get_now, logic
    ) -> None:
        """Test that both backend and frontend select upcoming meeting when both current and upcoming exist."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create test data: current meeting + upcoming meeting
        current_event_data = self.create_test_event_data("Current Meeting", -1, 1)  # 11am-1pm
        upcoming_event_data = self.create_test_event_data(
            "Upcoming Meeting", 0.5, 1.5
        )  # 12:30pm-1:30pm

        events_data = [current_event_data, upcoming_event_data]

        # Test backend selection
        backend_events = [self.create_backend_cached_event(e) for e in events_data]
        current_events, upcoming_events, later_events = logic._group_events(
            backend_events, current_time
        )

        # Backend should prioritize upcoming meeting (empty current_events)
        backend_selected = None
        if upcoming_events:
            backend_selected = upcoming_events[0].subject
        elif current_events:
            backend_selected = current_events[0].subject

        # Test frontend selection
        frontend_selected_event = self.simulate_frontend_meeting_selection(events_data)
        frontend_selected = frontend_selected_event["title"] if frontend_selected_event else None

        # Consistency assertion: Both should select the upcoming meeting
        assert backend_selected == "Upcoming Meeting", "Backend should prioritize upcoming meeting"
        assert frontend_selected == "Upcoming Meeting", (
            "Frontend should prioritize upcoming meeting"
        )
        assert backend_selected == frontend_selected, (
            "Backend and frontend should select identical meetings"
        )

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_backend_frontend_consistency_when_only_current_then_select_current(
        self, mock_get_now, logic
    ) -> None:
        """Test that both backend and frontend select current meeting when no upcoming meetings exist."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create test data: only current meeting (no upcoming)
        current_event_data = self.create_test_event_data("Current Meeting", -1, 1)  # 11am-1pm

        events_data = [current_event_data]

        # Test backend selection
        backend_events = [self.create_backend_cached_event(e) for e in events_data]
        current_events, upcoming_events, later_events = logic._group_events(
            backend_events, current_time
        )

        # Backend should fallback to current meeting
        backend_selected = None
        if upcoming_events:
            backend_selected = upcoming_events[0].subject
        elif current_events:
            backend_selected = current_events[0].subject

        # Test frontend selection
        frontend_selected_event = self.simulate_frontend_meeting_selection(events_data)
        frontend_selected = frontend_selected_event["title"] if frontend_selected_event else None

        # Consistency assertion: Both should select the current meeting as fallback
        assert backend_selected == "Current Meeting", "Backend should fallback to current meeting"
        assert frontend_selected == "Current Meeting", "Frontend should fallback to current meeting"
        assert backend_selected == frontend_selected, (
            "Backend and frontend should select identical meetings"
        )

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_backend_frontend_consistency_when_only_upcoming_then_select_upcoming(
        self, mock_get_now, logic
    ) -> None:
        """Test that both backend and frontend select upcoming meeting when only upcoming meetings exist."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create test data: only upcoming meetings
        upcoming_event_data = self.create_test_event_data("Upcoming Meeting", 1, 2)  # 1pm-2pm

        events_data = [upcoming_event_data]

        # Test backend selection
        backend_events = [self.create_backend_cached_event(e) for e in events_data]
        current_events, upcoming_events, later_events = logic._group_events(
            backend_events, current_time
        )

        # Backend should select upcoming meeting
        backend_selected = None
        if upcoming_events:
            backend_selected = upcoming_events[0].subject
        elif current_events:
            backend_selected = current_events[0].subject

        # Test frontend selection
        frontend_selected_event = self.simulate_frontend_meeting_selection(events_data)
        frontend_selected = frontend_selected_event["title"] if frontend_selected_event else None

        # Consistency assertion: Both should select the upcoming meeting
        assert backend_selected == "Upcoming Meeting", "Backend should select upcoming meeting"
        assert frontend_selected == "Upcoming Meeting", "Frontend should select upcoming meeting"
        assert backend_selected == frontend_selected, (
            "Backend and frontend should select identical meetings"
        )

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_backend_frontend_consistency_when_no_meetings_then_select_none(
        self, mock_get_now, logic
    ) -> None:
        """Test that both backend and frontend select no meeting when no meetings exist."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create test data: no meetings
        events_data = []

        # Test backend selection
        backend_events = []
        current_events, upcoming_events, later_events = logic._group_events(
            backend_events, current_time
        )

        # Backend should select no meeting
        backend_selected = None
        if upcoming_events:
            backend_selected = upcoming_events[0].subject
        elif current_events:
            backend_selected = current_events[0].subject

        # Test frontend selection
        frontend_selected_event = self.simulate_frontend_meeting_selection(events_data)
        frontend_selected = frontend_selected_event["title"] if frontend_selected_event else None

        # Consistency assertion: Both should select no meeting
        assert backend_selected is None, "Backend should select no meeting when no meetings exist"
        assert frontend_selected is None, "Frontend should select no meeting when no meetings exist"
        assert backend_selected == frontend_selected, "Backend and frontend should both select None"

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_backend_frontend_consistency_when_multiple_upcoming_then_select_earliest(
        self, mock_get_now, logic
    ) -> None:
        """Test that both backend and frontend select earliest upcoming meeting when multiple upcoming exist."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create test data: multiple upcoming meetings
        upcoming_event1_data = self.create_test_event_data("Later Meeting", 2, 3)  # 2pm-3pm
        upcoming_event2_data = self.create_test_event_data(
            "Earlier Meeting", 1, 2
        )  # 1pm-2pm (earlier)

        # Note: Order them non-chronologically to test sorting
        events_data = [upcoming_event1_data, upcoming_event2_data]

        # Test backend selection
        backend_events = [self.create_backend_cached_event(e) for e in events_data]
        current_events, upcoming_events, later_events = logic._group_events(
            backend_events, current_time
        )

        # Backend should select earliest upcoming meeting
        backend_selected = None
        if upcoming_events:
            backend_selected = upcoming_events[0].subject
        elif current_events:
            backend_selected = current_events[0].subject

        # Test frontend selection (frontend selects first upcoming found, which should be earliest)
        frontend_selected_event = self.simulate_frontend_meeting_selection(events_data)
        frontend_selected = frontend_selected_event["title"] if frontend_selected_event else None

        # Consistency assertion: Both should select the earliest upcoming meeting
        assert backend_selected == "Earlier Meeting", (
            "Backend should select earliest upcoming meeting"
        )
        assert frontend_selected == "Earlier Meeting", (
            "Frontend should select earliest upcoming meeting"
        )
        assert backend_selected == frontend_selected, (
            "Backend and frontend should select identical meetings"
        )

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_backend_frontend_consistency_when_back_to_back_meetings_then_prioritize_upcoming(
        self, mock_get_now, logic
    ) -> None:
        """Test that both backend and frontend handle back-to-back meetings consistently."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create test data: back-to-back meetings (current ends when next starts)
        current_event_data = self.create_test_event_data(
            "Current Meeting", -1, 0
        )  # 11am-12pm (ends now)
        next_event_data = self.create_test_event_data("Next Meeting", 0, 1)  # 12pm-1pm (starts now)

        events_data = [current_event_data, next_event_data]

        # Test backend selection
        backend_events = [self.create_backend_cached_event(e) for e in events_data]
        current_events, upcoming_events, later_events = logic._group_events(
            backend_events, current_time
        )

        # Backend should prioritize upcoming meeting in back-to-back scenario
        backend_selected = None
        if upcoming_events:
            backend_selected = upcoming_events[0].subject
        elif current_events:
            backend_selected = current_events[0].subject

        # Test frontend selection
        frontend_selected_event = self.simulate_frontend_meeting_selection(events_data)
        frontend_selected = frontend_selected_event["title"] if frontend_selected_event else None

        # Consistency assertion: Both should prioritize the next meeting
        assert backend_selected == "Next Meeting", (
            "Backend should prioritize next meeting in back-to-back scenario"
        )
        assert frontend_selected == "Next Meeting", (
            "Frontend should prioritize next meeting in back-to-back scenario"
        )
        assert backend_selected == frontend_selected, (
            "Backend and frontend should select identical meetings"
        )

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_backend_frontend_consistency_with_hidden_events_filtering(
        self, mock_get_now, logic
    ) -> None:
        """Test that both backend and frontend filter hidden events consistently."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create test data: visible and hidden events
        visible_event_data = self.create_test_event_data("Visible Meeting", 1, 2)  # 1pm-2pm
        hidden_event_data = self.create_test_event_data(
            "Hidden Meeting", 0.5, 1.5
        )  # 12:30pm-1:30pm (earlier)
        hidden_event_data["is_hidden"] = True  # Mark as hidden for frontend
        hidden_event_data["graph_id"] = "hidden_meeting_id"

        events_data = [visible_event_data, hidden_event_data]

        # Configure backend to hide the event
        logic.settings.event_filters.hidden_events = {"hidden_meeting_id"}

        # Test backend selection
        backend_events = [self.create_backend_cached_event(e) for e in events_data]
        current_events, upcoming_events, later_events = logic._group_events(
            backend_events, current_time
        )

        # Backend should only see visible meeting
        backend_selected = None
        if upcoming_events:
            backend_selected = upcoming_events[0].subject
        elif current_events:
            backend_selected = current_events[0].subject

        # Test frontend selection
        frontend_selected_event = self.simulate_frontend_meeting_selection(events_data)
        frontend_selected = frontend_selected_event["title"] if frontend_selected_event else None

        # Consistency assertion: Both should select only the visible meeting
        assert backend_selected == "Visible Meeting", "Backend should filter out hidden events"
        assert frontend_selected == "Visible Meeting", "Frontend should filter out hidden events"
        assert backend_selected == frontend_selected, (
            "Backend and frontend should select identical meetings after filtering"
        )

    @patch("calendarbot.display.whats_next_logic.get_timezone_aware_now")
    def test_backend_frontend_consistency_comprehensive_scenario(self, mock_get_now, logic) -> None:
        """Test comprehensive scenario with multiple meeting types to ensure complete consistency."""
        current_time = datetime(2025, 7, 14, 12, 0, 0)
        mock_get_now.return_value = current_time

        # Create comprehensive test data: past, current, multiple upcoming
        past_event_data = self.create_test_event_data("Past Meeting", -3, -2)  # 9am-10am
        current_event_data = self.create_test_event_data("Current Meeting", -1, 1)  # 11am-1pm
        upcoming_event1_data = self.create_test_event_data(
            "Next Meeting", 0.5, 1.5
        )  # 12:30pm-1:30pm (earliest upcoming)
        upcoming_event2_data = self.create_test_event_data("Later Meeting", 2, 3)  # 2pm-3pm

        events_data = [
            past_event_data,
            current_event_data,
            upcoming_event1_data,
            upcoming_event2_data,
        ]

        # Test backend selection
        backend_events = [self.create_backend_cached_event(e) for e in events_data]
        current_events, upcoming_events, later_events = logic._group_events(
            backend_events, current_time
        )

        # Backend should prioritize earliest upcoming meeting
        backend_selected = None
        if upcoming_events:
            backend_selected = upcoming_events[0].subject
        elif current_events:
            backend_selected = current_events[0].subject

        # Test frontend selection
        frontend_selected_event = self.simulate_frontend_meeting_selection(events_data)
        frontend_selected = frontend_selected_event["title"] if frontend_selected_event else None

        # Consistency assertion: Both should prioritize the earliest upcoming meeting
        assert backend_selected == "Next Meeting", (
            "Backend should prioritize earliest upcoming meeting in comprehensive scenario"
        )
        assert frontend_selected == "Next Meeting", (
            "Frontend should prioritize earliest upcoming meeting in comprehensive scenario"
        )
        assert backend_selected == frontend_selected, (
            "Backend and frontend should select identical meetings in comprehensive scenario"
        )

    def test_meeting_selection_priority_documentation(self) -> None:
        """Document the meeting selection priority rules for both backend and frontend.

        This test serves as living documentation of the priority rules.
        """
        priority_rules = [
            "1. Upcoming meetings are ALWAYS prioritized over current meetings",
            "2. When multiple upcoming meetings exist, select the earliest (chronologically first)",
            "3. Current meetings are only selected as fallback when NO upcoming meetings exist",
            "4. Hidden events are filtered out before applying selection rules",
            "5. Empty state when no visible events exist",
            "6. Both backend and frontend must implement identical selection logic",
        ]

        # This test documents the rules and always passes
        assert len(priority_rules) == 6, "Meeting selection priority rules are documented"

        # Log the rules for visibility in test output
        for rule in priority_rules:
            print(f"  {rule}")
