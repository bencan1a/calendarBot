"""Tests for ConsoleRenderer display functionality."""

from datetime import datetime, timedelta
from typing import Any, Optional
from unittest.mock import Mock, patch

import pytz

from calendarbot.cache.models import CachedEvent
from calendarbot.display.console_renderer import ConsoleRenderer


class TestConsoleRendererInitialization:
    """Test ConsoleRenderer initialization."""

    def test_init_creates_renderer_with_defaults(self) -> None:
        """Test basic initialization with default values."""
        mock_settings = Mock()

        renderer = ConsoleRenderer(mock_settings)

        assert renderer.settings == mock_settings
        assert renderer.width == 60
        assert renderer.log_area_lines == []
        assert renderer.log_area_enabled is False

    def test_init_sets_console_width(self) -> None:
        """Test console width is set correctly."""
        mock_settings = Mock()

        renderer = ConsoleRenderer(mock_settings)

        assert renderer.width == 60  # Default console width

    @patch("calendarbot.display.console_renderer.logger")
    def test_init_logs_debug_message(self, mock_logger: Any) -> None:
        """Test initialization logs debug message."""
        mock_settings = Mock()

        ConsoleRenderer(mock_settings)

        mock_logger.debug.assert_called_once_with("Console renderer initialized")


class TestConsoleRendererRenderEvents:
    """Test console renderer event rendering."""

    def create_mock_event(
        self,
        subject: str = "Test Event",
        is_current: bool = False,
        is_upcoming: bool = False,
        location: Optional[str] = None,
        is_online: bool = False,
    ) -> Any:
        """Create a mock CachedEvent for testing."""
        event = Mock(spec=CachedEvent)
        event.subject = subject
        event.location_display_name = location
        event.is_online_meeting = is_online
        event.start_dt = datetime.now(pytz.UTC)
        event.end_dt = event.start_dt + timedelta(hours=1)
        event.is_current.return_value = is_current
        event.is_upcoming.return_value = is_upcoming
        event.format_time_range.return_value = "10:00 AM - 11:00 AM"
        event.time_until_start.return_value = 30 if is_upcoming else None
        return event

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_empty_list(self, mock_datetime: Any) -> None:
        """Test rendering with empty events list."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_events([])

        assert "🎉 No meetings scheduled for today!" in result
        assert "📅 MICROSOFT 365 CALENDAR" in result
        assert "=" * 60 in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_with_current_events(self, mock_datetime: Any) -> None:
        """Test rendering with current events."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        current_event = self.create_mock_event("Current Meeting", is_current=True)

        renderer = ConsoleRenderer(Mock())
        with patch.object(
            renderer, "_format_current_event", return_value=["Formatted current event"]
        ):
            result = renderer.render_events([current_event])

        assert "▶ CURRENT EVENT" in result
        assert "Formatted current event" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_with_upcoming_events(self, mock_datetime: Any) -> None:
        """Test rendering with upcoming events."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        upcoming_events = [
            self.create_mock_event(f"Meeting {i}", is_upcoming=True) for i in range(1, 6)
        ]

        renderer = ConsoleRenderer(Mock())
        with patch.object(
            renderer, "_format_upcoming_event", return_value=["Upcoming event formatted"]
        ):
            result = renderer.render_events(upcoming_events)

        assert "📋 NEXT UP" in result
        assert "⏰ LATER TODAY" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_interactive_mode(self, mock_datetime: Any) -> None:
        """Test rendering in interactive mode."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        status_info: dict[str, Any] = {
            "interactive_mode": True,
            "selected_date": "Tuesday, January 02",
        }

        renderer = ConsoleRenderer(Mock())
        with patch.object(renderer, "_render_navigation_help", return_value="Navigation help"):
            result = renderer.render_events([], status_info)

        assert "Tuesday, January 02" in result
        assert "Navigation help" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_with_status_info(self, mock_datetime: Any) -> None:
        """Test rendering with comprehensive status info."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        # Mock datetime.fromisoformat to return a proper datetime mock
        mock_dt = Mock()
        mock_dt.strftime.return_value = "15:30"
        mock_datetime.fromisoformat.return_value = mock_dt

        status_info = {
            "last_update": "2024-01-01T15:30:00Z",
            "is_cached": True,
            "connection_status": "Connected",
        }

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_events([], status_info)

        assert "Updated: 15:30" in result
        assert "📱 Cached Data" in result
        assert "📶 Connected" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_status_update_time_datetime(self, mock_datetime: Any) -> None:
        """Test rendering with datetime update time."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        update_time = datetime(2024, 1, 1, 15, 30, 0, tzinfo=pytz.UTC)
        status_info: dict[str, Any] = {"last_update": update_time}

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_events([], status_info)

        assert "Updated:" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_status_invalid_update_time(self, mock_datetime: Any) -> None:
        """Test rendering with invalid update time."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        status_info: dict[str, Any] = {"last_update": "invalid-date"}

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_events([], status_info)

        # Should not crash, should handle gracefully
        assert "📅 MICROSOFT 365 CALENDAR" in result

    @patch("calendarbot.display.console_renderer.logger")
    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_exception_handling(self, mock_datetime: Any, mock_logger: Any) -> None:
        """Test exception handling in render_events."""
        mock_datetime.now.side_effect = Exception("Test exception")

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_events([])

        assert "Error rendering calendar: Test exception" in result
        mock_logger.exception.assert_called_once()

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_non_interactive_mode(self, mock_datetime: Any) -> None:
        """Test rendering in non-interactive mode."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        status_info: dict[str, Any] = {"interactive_mode": False}

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_events([], status_info)

        assert "Monday, January 01" in result
        # Should not contain navigation help
        assert "← → Navigate" not in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_live_data_status(self, mock_datetime: Any) -> None:
        """Test rendering with live data status."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        status_info: dict[str, Any] = {"is_cached": False}

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_events([], status_info)

        assert "🌐 Live Data" in result


class TestConsoleRendererFormatCurrentEvent:
    """Test current event formatting."""

    def create_mock_event(
        self,
        subject: str = "Test Event",
        location: Optional[str] = None,
        is_online: bool = False,
        duration_mins: int = 60,
    ) -> Any:
        """Create a mock event for testing."""
        event = Mock(spec=CachedEvent)
        event.subject = subject
        event.location_display_name = location
        event.is_online_meeting = is_online
        event.start_dt = datetime.now(pytz.UTC)
        event.end_dt = event.start_dt + timedelta(minutes=duration_mins)
        event.format_time_range.return_value = "10:00 AM - 11:00 AM"
        return event

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_current_event_basic(self, mock_now: Any) -> None:
        """Test basic current event formatting."""
        mock_now.return_value = datetime.now(pytz.UTC)

        event = self.create_mock_event("Team Meeting")

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_current_event(event)

        assert any("Team Meeting" in line for line in lines)
        assert any("10:00 AM - 11:00 AM" in line for line in lines)
        assert any("60min" in line for line in lines)

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_current_event_with_location(self, mock_now: Any) -> None:
        """Test current event formatting with location."""
        mock_now.return_value = datetime.now(pytz.UTC)

        event = self.create_mock_event("Meeting", location="Conference Room A")

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_current_event(event)

        assert any("📍 Conference Room A" in line for line in lines)

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_current_event_online_meeting(self, mock_now: Any) -> None:
        """Test current event formatting for online meeting."""
        mock_now.return_value = datetime.now(pytz.UTC)

        event = self.create_mock_event("Online Meeting", is_online=True)

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_current_event(event)

        # Online meeting indicators were removed per user requirements
        assert any("Online Meeting" in line for line in lines)

    @patch("calendarbot.display.console_renderer.get_timezone_aware_now")
    def test_format_current_event_time_remaining(self, mock_now: Any) -> None:
        """Test current event shows time remaining."""
        # Create specific times for the test
        event_start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=pytz.UTC)
        event_end = datetime(2024, 1, 1, 11, 0, 0, tzinfo=pytz.UTC)  # 1 hour duration
        current_time = datetime(
            2024, 1, 1, 10, 30, 0, tzinfo=pytz.UTC
        )  # 30 minutes after start = 30 minutes remaining

        mock_now.return_value = current_time

        event = self.create_mock_event("Meeting")
        event.start_dt = event_start
        event.end_dt = event_end

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_current_event(event)

        assert any("⏱️  30 minutes remaining" in line for line in lines)

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_current_event_truncated_title(self, mock_now: Any) -> None:
        """Test current event with long title gets truncated."""
        # Set up proper datetime mock
        now = datetime(2024, 1, 1, 9, 15, 0, tzinfo=pytz.UTC)
        mock_now.return_value = now

        long_title = "Very Long Meeting Title That Should Be Truncated Because It Exceeds Limit"
        event = self.create_mock_event(long_title)
        # Ensure event is currently running
        event.start_dt = datetime(2024, 1, 1, 9, 0, 0, tzinfo=pytz.UTC)
        event.end_dt = datetime(2024, 1, 1, 9, 30, 0, tzinfo=pytz.UTC)

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_current_event(event)

        # Should be truncated to 50 characters max
        title_line = next(line for line in lines if long_title[:20] in line)
        assert len(title_line.strip()) <= 55  # Account for padding


class TestConsoleRendererFormatUpcomingEvent:
    """Test upcoming event formatting."""

    def create_mock_event(
        self,
        subject: str = "Test Event",
        location: Optional[str] = None,
        is_online: bool = False,
        time_until: int = 30,
    ) -> Any:
        """Create a mock upcoming event."""
        event = Mock(spec=CachedEvent)
        event.subject = subject
        event.location_display_name = location
        event.is_online_meeting = is_online
        event.format_time_range.return_value = "2:00 PM - 3:00 PM"
        event.time_until_start.return_value = time_until
        return event

    def test_format_upcoming_event_basic(self) -> None:
        """Test basic upcoming event formatting."""
        event = self.create_mock_event("Team Standup")

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_upcoming_event(event)

        assert any("• Team Standup" in line for line in lines)
        assert any("2:00 PM - 3:00 PM" in line for line in lines)

    def test_format_upcoming_event_with_location(self) -> None:
        """Test upcoming event with location."""
        event = self.create_mock_event("Meeting", location="Room 101")

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_upcoming_event(event)

        assert any("📍 Room 101" in line for line in lines)

    def test_format_upcoming_event_online_meeting(self) -> None:
        """Test upcoming online meeting."""
        event = self.create_mock_event("Video Call", is_online=True)

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_upcoming_event(event)

        # Online meeting indicators were removed per user requirements
        assert any("Video Call" in line for line in lines)

    def test_format_upcoming_event_time_until_urgent(self) -> None:
        """Test upcoming event starting soon (≤5 minutes)."""
        event = self.create_mock_event("Urgent Meeting", time_until=3)

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_upcoming_event(event)

        assert any("🔔 Starting in 3 minutes!" in line for line in lines)

    def test_format_upcoming_event_time_until_normal(self) -> None:
        """Test upcoming event starting within hour."""
        event = self.create_mock_event("Meeting", time_until=45)

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_upcoming_event(event)

        assert any("⏰ In 45 minutes" in line for line in lines)

    def test_format_upcoming_event_time_until_far(self) -> None:
        """Test upcoming event starting far in future."""
        event = self.create_mock_event("Meeting", time_until=120)  # 2 hours

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_upcoming_event(event)

        # Should not show time until for events > 1 hour away
        assert not any("⏰" in line for line in lines)
        assert not any("🔔" in line for line in lines)

    def test_format_upcoming_event_empty_line_separator(self) -> None:
        """Test upcoming events have empty line separators."""
        event = self.create_mock_event("Meeting")

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_upcoming_event(event)

        assert lines[-1] == ""  # Should end with empty line


class TestConsoleRendererNavigationHelp:
    """Test navigation help rendering."""

    def test_render_navigation_help_basic(self) -> None:
        """Test basic navigation help."""
        status_info: dict[str, Any] = {}

        renderer = ConsoleRenderer(Mock())
        result = renderer._render_navigation_help(status_info)

        assert "← → Navigate" in result
        assert "Space: Today" in result
        assert "ESC: Exit" in result

    def test_render_navigation_help_with_custom_controls(self) -> None:
        """Test navigation help with custom controls."""
        status_info: dict[str, Any] = {"navigation_help": "Home: Week Start | End: Week End"}

        renderer = ConsoleRenderer(Mock())
        result = renderer._render_navigation_help(status_info)

        assert "Home: Week Start" in result
        assert "End: Week End" in result

    def test_render_navigation_help_with_relative_description(self) -> None:
        """Test navigation help no longer shows relative date descriptions."""
        status_info: dict[str, Any] = {"relative_description": "Tomorrow"}

        renderer = ConsoleRenderer(Mock())
        result = renderer._render_navigation_help(status_info)

        # Relative descriptions were removed per user requirements
        assert "📍 Tomorrow" not in result
        # Should still show basic navigation controls
        assert "← → Navigate" in result

    def test_render_navigation_help_today_no_relative(self) -> None:
        """Test navigation help doesn't show 'Today' as relative."""
        status_info: dict[str, Any] = {"relative_description": "Today"}

        renderer = ConsoleRenderer(Mock())
        result = renderer._render_navigation_help(status_info)

        assert "📍 Today" not in result  # Should skip showing "Today"


class TestConsoleRendererTruncateText:
    """Test text truncation functionality."""

    def test_truncate_text_no_truncation_needed(self) -> None:
        """Test text shorter than max length."""
        renderer = ConsoleRenderer(Mock())
        result = renderer._truncate_text("Short text", 20)

        assert result == "Short text"

    def test_truncate_text_exact_length(self) -> None:
        """Test text exactly at max length."""
        renderer = ConsoleRenderer(Mock())
        result = renderer._truncate_text("Exactly20Characters", 20)

        assert result == "Exactly20Characters"

    def test_truncate_text_needs_truncation(self) -> None:
        """Test text longer than max length gets truncated."""
        renderer = ConsoleRenderer(Mock())
        result = renderer._truncate_text("This is a very long text that needs truncation", 20)

        assert result == "This is a very lo..."
        assert len(result) == 20

    def test_truncate_text_empty_string(self) -> None:
        """Test truncating empty string."""
        renderer = ConsoleRenderer(Mock())
        result = renderer._truncate_text("", 10)

        assert result == ""

    def test_truncate_text_very_short_limit(self) -> None:
        """Test truncation with very short limit."""
        renderer = ConsoleRenderer(Mock())
        result = renderer._truncate_text("Hello", 4)

        assert result == "H..."
        assert len(result) == 4


class TestConsoleRendererRenderError:
    """Test error rendering functionality."""

    def create_mock_event(self, subject: str = "Test Event", location: Optional[str] = None) -> Any:
        """Create a mock cached event."""
        event = Mock(spec=CachedEvent)
        event.subject = subject
        event.location_display_name = location
        event.format_time_range.return_value = "10:00 AM - 11:00 AM"
        return event

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_error_basic(self, mock_datetime: Any) -> None:
        """Test basic error rendering."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_error("Connection failed")

        assert "⚠️  CONNECTION ISSUE" in result
        assert "Connection failed" in result
        assert "❌ No cached data available" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_error_with_cached_events(self, mock_datetime: Any) -> None:
        """Test error rendering with cached events."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        cached_events = [
            self.create_mock_event("Meeting 1"),
            self.create_mock_event("Meeting 2", location="Room A"),
        ]

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_error("Network timeout", cached_events)

        assert "📱 SHOWING CACHED DATA" in result
        assert "Meeting 1" in result
        assert "Meeting 2" in result
        assert "📍 Room A" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_error_with_many_cached_events(self, mock_datetime: Any) -> None:
        """Test error rendering limits cached events to 5."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        cached_events = [self.create_mock_event(f"Meeting {i}") for i in range(1, 10)]

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_error("Error", cached_events)

        # Should only show first 5 events
        assert "Meeting 1" in result
        assert "Meeting 5" in result
        assert "Meeting 6" not in result

    @patch("calendarbot.display.console_renderer.logger")
    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_error_exception_handling(self, mock_datetime: Any, mock_logger: Any) -> None:
        """Test error rendering handles exceptions."""
        mock_datetime.now.side_effect = Exception("Test exception")

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_error("Original error")

        assert "Critical error: Test exception" in result
        mock_logger.exception.assert_called_once()


class TestConsoleRendererAuthenticationPrompt:
    """Test authentication prompt rendering."""

    def test_render_authentication_prompt_basic(self) -> None:
        """Test basic authentication prompt rendering."""
        renderer = ConsoleRenderer(Mock())
        result = renderer.render_authentication_prompt(
            "https://microsoft.com/devicelogin", "A1B2C3D4"
        )

        assert "🔐 MICROSOFT 365 AUTHENTICATION REQUIRED" in result
        assert "Visit: https://microsoft.com/devicelogin" in result
        assert "Enter code: A1B2C3D4" in result
        assert "Waiting for authentication..." in result

    def test_render_authentication_prompt_formatting(self) -> None:
        """Test authentication prompt has proper formatting."""
        renderer = ConsoleRenderer(Mock())
        result = renderer.render_authentication_prompt("https://example.com", "CODE123")

        lines = result.split("\n")

        # Should have proper header with equals signs
        assert any("=" * 60 in line for line in lines)
        # Should have numbered steps
        assert any("1. Visit:" in line for line in lines)
        assert any("2. Enter code:" in line for line in lines)


class TestConsoleRendererScreenControl:
    """Test screen clearing and display functionality."""

    @patch("calendarbot.display.console_renderer.secure_clear_screen")
    def test_clear_screen_success(self, mock_clear: Any) -> None:
        """Test successful screen clearing."""
        mock_clear.return_value = True

        renderer = ConsoleRenderer(Mock())
        result = renderer.clear_screen()

        assert result is True
        mock_clear.assert_called_once()

    @patch("calendarbot.display.console_renderer.secure_clear_screen")
    def test_clear_screen_failure(self, mock_clear: Any) -> None:
        """Test failed screen clearing."""
        mock_clear.return_value = False

        renderer = ConsoleRenderer(Mock())
        result = renderer.clear_screen()

        assert result is False
        mock_clear.assert_called_once()

    @patch("builtins.print")
    def test_display_with_clear_normal_mode(self, mock_print: Any) -> None:
        """Test display with clear in normal mode."""
        renderer = ConsoleRenderer(Mock())
        renderer.log_area_enabled = False

        with patch.object(renderer, "clear_screen") as mock_clear:
            renderer.display_with_clear("Test content")

        mock_clear.assert_called_once()
        mock_print.assert_called()

    def test_display_with_clear_split_mode(self) -> None:
        """Test display with clear in split mode."""
        renderer = ConsoleRenderer(Mock())
        renderer.log_area_enabled = True

        with patch.object(renderer, "_display_with_split_logging") as mock_split:
            renderer.display_with_clear("Test content")

        mock_split.assert_called_once_with("Test content")


class TestConsoleRendererSplitDisplay:
    """Test split display functionality."""

    def test_enable_split_display(self) -> None:
        """Test enabling split display mode."""
        renderer = ConsoleRenderer(Mock())

        renderer.enable_split_display(max_log_lines=10)

        assert renderer.log_area_enabled is True
        assert renderer.max_log_lines == 10
        assert renderer.log_area_lines == []

    def test_enable_split_display_default_lines(self) -> None:
        """Test enabling split display with default max lines."""
        renderer = ConsoleRenderer(Mock())

        renderer.enable_split_display()

        assert renderer.max_log_lines == 5  # Default value

    @patch("calendarbot.display.console_renderer.logger")
    def test_enable_split_display_logs_debug(self, mock_logger: Any) -> None:
        """Test enabling split display logs debug message."""
        renderer = ConsoleRenderer(Mock())

        renderer.enable_split_display()

        mock_logger.debug.assert_called_with("Split display mode enabled")

    def test_disable_split_display(self) -> None:
        """Test disabling split display mode."""
        renderer = ConsoleRenderer(Mock())
        renderer.log_area_enabled = True
        renderer.log_area_lines = ["test"]

        renderer.disable_split_display()

        assert renderer.log_area_enabled is False
        assert renderer.log_area_lines == []

    @patch("calendarbot.display.console_renderer.logger")
    def test_disable_split_display_logs_debug(self, mock_logger: Any) -> None:
        """Test disabling split display logs debug message."""
        renderer = ConsoleRenderer(Mock())

        renderer.disable_split_display()

        mock_logger.debug.assert_called_with("Split display mode disabled")

    def test_update_log_area_disabled(self) -> None:
        """Test updating log area when disabled does nothing."""
        renderer = ConsoleRenderer(Mock())
        renderer.log_area_enabled = False

        renderer.update_log_area(["log line 1", "log line 2"])

        assert renderer.log_area_lines == []

    def test_update_log_area_enabled(self) -> None:
        """Test updating log area when enabled."""
        renderer = ConsoleRenderer(Mock())
        renderer.enable_split_display(max_log_lines=3)

        renderer.update_log_area(["line 1", "line 2", "line 3", "line 4", "line 5"])

        # Should only keep last 3 lines
        assert renderer.log_area_lines == ["line 3", "line 4", "line 5"]

    @patch("calendarbot.display.console_renderer.logger")
    def test_update_log_area_logs_debug(self, mock_logger: Any) -> None:
        """Test updating log area logs debug message."""
        renderer = ConsoleRenderer(Mock())
        renderer.enable_split_display()

        renderer.update_log_area(["line 1", "line 2"])

        mock_logger.debug.assert_called_with("Log area updated with 2 lines")

    def test_update_log_area_empty_list(self) -> None:
        """Test updating log area with empty list."""
        renderer = ConsoleRenderer(Mock())
        renderer.enable_split_display()

        renderer.update_log_area([])

        assert renderer.log_area_lines == []

    def test_get_log_area_status_disabled(self) -> None:
        """Test getting log area status when disabled."""
        renderer = ConsoleRenderer(Mock())

        status = renderer.get_log_area_status()

        assert status["enabled"] is False
        assert status["max_lines"] == 0
        assert status["current_lines"] == 0
        assert status["log_content"] == []

    def test_get_log_area_status_enabled(self) -> None:
        """Test getting log area status when enabled."""
        renderer = ConsoleRenderer(Mock())
        renderer.enable_split_display(max_log_lines=5)
        renderer.log_area_lines = ["line 1", "line 2"]

        status = renderer.get_log_area_status()

        assert status["enabled"] is True
        assert status["max_lines"] == 5
        assert status["current_lines"] == 2
        assert status["log_content"] == ["line 1", "line 2"]

    @patch("builtins.print")
    @patch("os.get_terminal_size")
    def test_display_with_split_logging(self, mock_terminal_size: Any, mock_print: Any) -> None:
        """Test split logging display functionality."""
        mock_terminal_size.return_value = Mock(lines=30)

        renderer = ConsoleRenderer(Mock())
        renderer.enable_split_display()
        renderer.log_area_lines = ["Log line 1", "Log line 2"]

        with patch.object(renderer, "clear_screen"):
            renderer._display_with_split_logging("Main content\nLine 2")

        # Should have printed main content and log area
        mock_print.assert_called()

    @patch("builtins.print")
    @patch("os.get_terminal_size")
    def test_display_with_split_logging_terminal_size_error(
        self, mock_terminal_size: Any, mock_print: Any
    ) -> None:
        """Test split logging handles terminal size error."""
        mock_terminal_size.side_effect = OSError("No terminal")

        renderer = ConsoleRenderer(Mock())
        renderer.enable_split_display()

        with patch.object(renderer, "clear_screen"):
            renderer._display_with_split_logging("Test content")

        # Should fallback to default height and still work
        mock_print.assert_called()

    @patch("builtins.print")
    @patch("os.get_terminal_size")
    def test_display_with_split_logging_no_log_content(
        self, mock_terminal_size: Any, mock_print: Any
    ) -> None:
        """Test split logging with no log area content."""
        mock_terminal_size.return_value = Mock(lines=30)

        renderer = ConsoleRenderer(Mock())
        renderer.enable_split_display()
        renderer.log_area_lines = []

        with patch.object(renderer, "clear_screen"):
            renderer._display_with_split_logging("Main content")

        # Should not display separator or log area
        calls = [call.args[0] if call.args else "" for call in mock_print.call_args_list]
        assert not any("─" in str(call) for call in calls)


class TestConsoleRendererIntegration:
    """Integration tests for console renderer."""

    def create_realistic_events(self) -> list[Any]:
        """Create realistic test events."""
        events = []

        # Current event
        current = Mock(spec=CachedEvent)
        current.subject = "Daily Standup"
        current.location_display_name = "Conference Room A"
        current.is_online_meeting = False
        current.is_current.return_value = True
        current.is_upcoming.return_value = False
        current.start_dt = datetime.now(pytz.UTC) - timedelta(minutes=15)
        current.end_dt = datetime.now(pytz.UTC) + timedelta(minutes=15)
        current.format_time_range.return_value = "9:00 AM - 9:30 AM"
        events.append(current)

        # Upcoming events - need more than 3 to trigger "LATER TODAY" section
        time_until_values = [30, 90, 150, 240, 300]  # 5 events to ensure "LATER TODAY" appears
        for i in range(5):
            event = Mock(spec=CachedEvent)
            event.subject = f"Meeting {i + 1}"
            event.location_display_name = None
            event.is_online_meeting = True
            event.is_current.return_value = False
            event.is_upcoming.return_value = True
            event.format_time_range.return_value = f"{10 + i}:00 AM - {11 + i}:00 AM"
            event.time_until_start.return_value = time_until_values[i]
            events.append(event)

        return events

    @patch("calendarbot.display.console_renderer.datetime")
    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_full_rendering_workflow(self, mock_now: Any, mock_datetime: Any) -> None:
        """Test complete rendering workflow with realistic data."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"
        mock_now.return_value = datetime.now(pytz.UTC)

        # Mock datetime.fromisoformat for status update time
        mock_dt = Mock()
        mock_dt.strftime.return_value = "10:30"
        mock_datetime.fromisoformat.return_value = mock_dt

        events = self.create_realistic_events()
        status_info: dict[str, Any] = {
            "last_update": "2024-01-01T10:30:00Z",
            "is_cached": False,
            "connection_status": "Connected",
            "interactive_mode": True,
            "selected_date": "Monday, January 01",
            "relative_description": "Today",
        }

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_events(events, status_info)

        # Verify all major sections are present
        assert "📅 MICROSOFT 365 CALENDAR" in result
        assert "▶ CURRENT EVENT" in result
        assert "Daily Standup" in result
        assert "📋 NEXT UP" in result
        assert "Meeting 1" in result
        assert "⏰ LATER TODAY" in result
        assert "🌐 Live Data" in result
        assert "Updated: 10:30" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_error_recovery_workflow(self, mock_datetime: Any) -> None:
        """Test error recovery with cached data."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        cached_events = self.create_realistic_events()[:2]  # Only first 2 events

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_error("Network connection failed", cached_events)

        assert "⚠️  CONNECTION ISSUE" in result
        assert "📱 SHOWING CACHED DATA" in result
        assert "Daily Standup" in result
        assert "Meeting 1" in result

    def test_split_display_complete_workflow(self) -> None:
        """Test complete split display workflow."""
        renderer = ConsoleRenderer(Mock())

        # Enable split display
        renderer.enable_split_display(max_log_lines=3)
        assert renderer.get_log_area_status()["enabled"] is True

        # Add log lines
        renderer.update_log_area(["Error 1", "Warning 2", "Info 3", "Debug 4"])
        status = renderer.get_log_area_status()
        assert status["current_lines"] == 3
        assert "Debug 4" in status["log_content"]

        # Disable and verify cleanup
        renderer.disable_split_display()
        assert renderer.get_log_area_status()["enabled"] is False
