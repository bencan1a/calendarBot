"""Tests for WhatsNextRenderer."""

from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from calendarbot.cache.models import CachedEvent
from calendarbot.display.whats_next_logic import WhatsNextLogic
from calendarbot.display.whats_next_renderer import WhatsNextRenderer


class TestWhatsNextRenderer:
    """Test cases for WhatsNextRenderer class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings object."""
        settings = MagicMock()
        settings.web_layout = "whats-next-view"
        return settings

    @pytest.fixture
    def renderer(self, mock_settings):
        """Create WhatsNextRenderer instance for testing."""
        with patch("calendarbot.display.html_renderer.LayoutRegistry"), patch(
            "calendarbot.display.html_renderer.ResourceManager"
        ):
            return WhatsNextRenderer(mock_settings)

    @pytest.fixture
    def mock_now(self):
        """Mock current time."""
        return datetime(2025, 7, 14, 12, 0, 0)

    def create_mock_event(
        self, subject: str, start_hours_offset: int, end_hours_offset: Optional[int] = None
    ) -> CachedEvent:
        """Create a mock CachedEvent for testing.

        Args:
            subject: Event subject
            start_hours_offset: Hours from now for start time
            end_hours_offset: Hours from now for end time (defaults to start + 1 hour)

        Returns:
            Mock CachedEvent instance
        """
        from datetime import timezone

        base_time = datetime(2025, 7, 14, 12, 0, 0, tzinfo=timezone.utc)  # noon UTC
        start_dt = base_time + timedelta(hours=start_hours_offset)
        end_dt = base_time + timedelta(hours=end_hours_offset or (start_hours_offset + 1))

        event = MagicMock(spec=CachedEvent)
        event.subject = subject
        event.start_dt = start_dt
        event.end_dt = end_dt
        event.location_display_name = None
        event.format_time_range.return_value = (
            f"{start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}"
        )
        event.is_current.return_value = start_dt <= base_time < end_dt
        event.is_upcoming.return_value = start_dt > base_time

        # Mock time_until_start() method
        if start_dt > base_time:
            minutes_until = int((start_dt - base_time).total_seconds() / 60)
            event.time_until_start.return_value = minutes_until
        else:
            event.time_until_start.return_value = None

        return event

    def test_init_when_called_then_initializes_successfully(self, mock_settings):
        """Test WhatsNextRenderer initialization."""
        with patch("calendarbot.display.html_renderer.LayoutRegistry"), patch(
            "calendarbot.display.html_renderer.ResourceManager"
        ):
            renderer = WhatsNextRenderer(mock_settings)
            assert renderer is not None
            assert isinstance(renderer, WhatsNextRenderer)

    def test_find_next_upcoming_event_when_upcoming_events_exist_then_returns_earliest(
        self, renderer
    ):
        """Test finding next upcoming event with multiple upcoming events."""
        from datetime import timezone

        # Use built-in debug time mechanism instead of mocking
        debug_time = datetime(2025, 7, 14, 12, 0, 0, tzinfo=timezone.utc)
        renderer.logic.set_debug_time(debug_time)

        # Create events: past, current, future1, future2
        events = [
            self.create_mock_event("Past Event", -2, -1),  # 10am-11am (past)
            self.create_mock_event("Current Event", -1, 1),  # 11am-1pm (current)
            self.create_mock_event("Future Event 2", 4, 5),  # 4pm-5pm (later)
            self.create_mock_event("Future Event 1", 2, 3),  # 2pm-3pm (next)
        ]

        result = renderer.logic.find_next_upcoming_event(events)

        assert result is not None
        assert result.subject == "Future Event 1"

    def test_find_next_upcoming_event_when_no_upcoming_events_then_returns_none(self, renderer):
        """Test finding next upcoming event when no upcoming events exist."""
        from datetime import timezone

        # Use built-in debug time mechanism instead of mocking
        debug_time = datetime(2025, 7, 14, 12, 0, 0, tzinfo=timezone.utc)
        renderer.logic.set_debug_time(debug_time)

        # Create only past and current events
        events = [
            self.create_mock_event("Past Event", -2, -1),  # 10am-11am
            self.create_mock_event("Current Event", -1, 1),  # 11am-1pm
        ]

        result = renderer.logic.find_next_upcoming_event(events)

        assert result is None

    def test_find_next_upcoming_event_when_empty_list_then_returns_none(self, renderer):
        """Test finding next upcoming event with empty event list."""
        from datetime import timezone

        # Use built-in debug time mechanism instead of mocking
        debug_time = datetime(2025, 7, 14, 12, 0, 0, tzinfo=timezone.utc)
        renderer.logic.set_debug_time(debug_time)

        result = renderer.logic.find_next_upcoming_event([])

        assert result is None

    def test_find_next_upcoming_event_when_error_occurs_then_returns_none(self, renderer):
        """Test error handling in find_next_upcoming_event."""
        # Pass None to trigger an error path
        result = renderer.logic.find_next_upcoming_event(None)

        assert result is None

    def test_render_single_event_content_when_upcoming_event_then_renders_correctly(self, renderer):
        """Test rendering single upcoming event content."""
        event = self.create_mock_event("Test Meeting", 2, 3)

        result = renderer._render_single_event_content(event, is_current=False)

        assert result is not None
        assert isinstance(result, str)
        assert "What's Next" in result
        assert "Test Meeting" in result
        assert "upcoming-events" in result

    def test_render_single_event_content_when_current_event_then_renders_correctly(self, renderer):
        """Test rendering single current event content."""
        event = self.create_mock_event("Current Meeting", -1, 1)

        result = renderer._render_single_event_content(event, is_current=True)

        assert result is not None
        assert isinstance(result, str)
        assert "Current Event" in result
        assert "Current Meeting" in result
        assert "current-events" in result

    def test_render_single_event_content_when_error_occurs_then_returns_error_html(self, renderer):
        """Test error handling in render_single_event_content."""
        event = MagicMock()
        event.subject = None  # This should cause an error

        result = renderer._render_single_event_content(event, is_current=False)

        assert result is not None
        assert "error" in result.lower()

    @patch.object(WhatsNextLogic, "find_next_upcoming_event")
    def test_render_events_content_when_next_event_exists_then_renders_single_event(
        self, mock_find_next, renderer
    ):
        """Test rendering events content when next event exists."""
        next_event = self.create_mock_event("Next Meeting", 2, 3)
        mock_find_next.return_value = next_event

        events = [
            self.create_mock_event("Past Event", -2, -1),
            next_event,
            self.create_mock_event("Later Event", 4, 5),
        ]

        result = renderer._render_events_content(events, interactive_mode=False)

        assert result is not None
        assert isinstance(result, str)
        assert "Next Meeting" in result
        mock_find_next.assert_called_once_with(events)

    @patch.object(WhatsNextLogic, "find_next_upcoming_event")
    def test_render_events_content_when_no_next_event_but_current_exists_then_renders_current(
        self, mock_find_next, renderer
    ):
        """Test rendering events content when no next event but current event exists."""
        current_event = self.create_mock_event("Current Meeting", -1, 1)
        # Mock method properly
        current_event.is_current = MagicMock(return_value=True)

        mock_find_next.return_value = None
        events = [current_event]

        result = renderer._render_events_content(events, interactive_mode=False)

        assert result is not None
        assert isinstance(result, str)
        assert "Current Meeting" in result

    @patch.object(WhatsNextLogic, "find_next_upcoming_event")
    def test_render_events_content_when_no_events_then_renders_no_events_message(
        self, mock_find_next, renderer
    ):
        """Test rendering events content when no events exist."""
        mock_find_next.return_value = None

        result = renderer._render_events_content([], interactive_mode=False)

        assert result is not None
        assert isinstance(result, str)
        assert "No meetings scheduled" in result

    @patch.object(WhatsNextLogic, "find_next_upcoming_event")
    def test_render_events_content_when_no_upcoming_or_current_then_renders_no_upcoming_message(
        self, mock_find_next, renderer
    ):
        """Test rendering events content when no upcoming or current events."""
        mock_find_next.return_value = None

        # Only past events
        events = [self.create_mock_event("Past Event", -2, -1)]
        events[0].is_current = MagicMock(return_value=False)

        result = renderer._render_events_content(events, interactive_mode=False)

        assert result is not None
        assert isinstance(result, str)
        assert "No upcoming meetings" in result

    @patch.object(WhatsNextRenderer, "_render_events_content")
    def test_render_events_when_called_then_uses_parent_implementation_with_override(
        self, mock_render_content, renderer
    ):
        """Test main render_events method uses parent implementation with content override."""
        mock_render_content.return_value = "<div>Test Content</div>"

        events = [self.create_mock_event("Test Event", 1, 2)]
        status_info = {"test": "data"}

        result = renderer.render_events(events, status_info)

        assert result is not None
        assert isinstance(result, str)
        mock_render_content.assert_called_once_with(
            events, False
        )  # interactive_mode defaults to False

    @patch.object(WhatsNextRenderer, "_render_events_content")
    def test_render_events_when_error_occurs_then_returns_error_html(
        self, mock_render_content, renderer
    ):
        """Test error handling in main render_events method."""
        mock_render_content.side_effect = Exception("Rendering error")

        events = [self.create_mock_event("Test Event", 1, 2)]

        result = renderer.render_events(events)

        assert result is not None
        assert isinstance(result, str)
        assert "Error rendering calendar" in result

    def test_render_events_content_when_error_in_filtering_then_falls_back_to_parent(
        self, renderer
    ):
        """Test fallback to parent implementation when filtering fails."""
        events = [self.create_mock_event("Test Event", 1, 2)]

        # Mock an error in the filtering process
        with patch.object(
            renderer.logic, "find_next_upcoming_event", side_effect=Exception("Filter error")
        ):
            # This should fall back to parent implementation (HTMLRenderer._render_events_content)
            result = renderer._render_events_content(events, interactive_mode=False)

            # Should not crash and should return some content
            assert result is not None
            assert isinstance(result, str)
