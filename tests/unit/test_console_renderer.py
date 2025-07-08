"""Comprehensive unit tests for ConsoleRenderer."""

import os
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest
import pytz

from calendarbot.cache.models import CachedEvent
from calendarbot.display.console_renderer import ConsoleRenderer


class TestConsoleRendererInitialization:
    """Test ConsoleRenderer initialization."""

    def test_init_with_settings(self):
        """Test initialization with settings."""
        mock_settings = Mock()
        with patch("calendarbot.display.console_renderer.logger") as mock_logger:
            renderer = ConsoleRenderer(mock_settings)

            assert renderer.settings == mock_settings
            assert renderer.width == 60
            assert renderer.log_area_lines == []
            assert renderer.log_area_enabled is False
            mock_logger.debug.assert_called_once_with("Console renderer initialized")

    def test_init_default_properties(self):
        """Test initialization sets correct default properties."""
        mock_settings = Mock()
        renderer = ConsoleRenderer(mock_settings)

        assert renderer.width == 60
        assert isinstance(renderer.log_area_lines, list)
        assert len(renderer.log_area_lines) == 0
        assert renderer.log_area_enabled is False


class TestConsoleRendererTextTruncation:
    """Test text truncation functionality."""

    def test_truncate_text_short_text(self):
        """Test truncation with text shorter than max length."""
        renderer = ConsoleRenderer(Mock())
        result = renderer._truncate_text("Short text", 20)
        assert result == "Short text"

    def test_truncate_text_exact_length(self):
        """Test truncation with text exactly at max length."""
        renderer = ConsoleRenderer(Mock())
        text = "Exactly twenty chars"
        result = renderer._truncate_text(text, 20)
        assert result == text

    def test_truncate_text_too_long(self):
        """Test truncation with text longer than max length."""
        renderer = ConsoleRenderer(Mock())
        long_text = "This is a very long text that exceeds the maximum length"
        result = renderer._truncate_text(long_text, 20)
        assert result == "This is a very lo..."
        assert len(result) == 20

    def test_truncate_text_very_short_max_length(self):
        """Test truncation with very short max length."""
        renderer = ConsoleRenderer(Mock())
        result = renderer._truncate_text("Long text", 5)
        assert result == "Lo..."
        assert len(result) == 5

    def test_truncate_text_empty_string(self):
        """Test truncation with empty string."""
        renderer = ConsoleRenderer(Mock())
        result = renderer._truncate_text("", 10)
        assert result == ""


class TestConsoleRendererEventFormatting:
    """Test event formatting methods."""

    @pytest.fixture
    def mock_current_event(self):
        """Create a mock current event."""
        event = Mock(spec=CachedEvent)
        event.subject = "Team Meeting"
        event.start_dt = datetime.now(pytz.UTC) - timedelta(minutes=30)
        event.end_dt = datetime.now(pytz.UTC) + timedelta(minutes=30)
        event.location_display_name = "Conference Room A"
        event.is_online_meeting = False
        event.format_time_range.return_value = "2:00 PM - 3:00 PM"
        return event

    @pytest.fixture
    def mock_upcoming_event(self):
        """Create a mock upcoming event."""
        event = Mock(spec=CachedEvent)
        event.subject = "Client Call"
        event.start_dt = datetime.now(pytz.UTC) + timedelta(hours=1)
        event.end_dt = datetime.now(pytz.UTC) + timedelta(hours=2)
        event.location_display_name = None
        event.is_online_meeting = True
        event.format_time_range.return_value = "4:00 PM - 5:00 PM"
        event.time_until_start.return_value = 60
        return event

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_current_event_with_location(self, mock_now, mock_current_event):
        """Test formatting current event with location."""
        mock_now.return_value = datetime.now(pytz.UTC)
        renderer = ConsoleRenderer(Mock())

        lines = renderer._format_current_event(mock_current_event)

        assert any("Team Meeting" in line for line in lines)
        assert any("2:00 PM - 3:00 PM" in line for line in lines)
        assert any("📍 Conference Room A" in line for line in lines)
        assert any("minutes remaining" in line for line in lines)

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_current_event_online_meeting(self, mock_now):
        """Test formatting current event that's online."""
        mock_now.return_value = datetime.now(pytz.UTC)

        event = Mock(spec=CachedEvent)
        event.subject = "Online Meeting"
        event.start_dt = datetime.now(pytz.UTC) - timedelta(minutes=15)
        event.end_dt = datetime.now(pytz.UTC) + timedelta(minutes=45)
        event.location_display_name = None
        event.is_online_meeting = True
        event.format_time_range.return_value = "2:00 PM - 3:00 PM"

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_current_event(event)

        assert any("💻 Online Meeting" in line for line in lines)

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_current_event_no_time_remaining(self, mock_now):
        """Test formatting current event with no time remaining."""
        mock_now.return_value = datetime.now(pytz.UTC)

        event = Mock(spec=CachedEvent)
        event.subject = "Ending Soon"
        event.start_dt = datetime.now(pytz.UTC) - timedelta(hours=1)
        event.end_dt = datetime.now(pytz.UTC) - timedelta(minutes=5)  # Already ended
        event.location_display_name = None
        event.is_online_meeting = False
        event.format_time_range.return_value = "1:00 PM - 2:00 PM"

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_current_event(event)

        # Should not include time remaining when event is over
        assert not any("minutes remaining" in line for line in lines)

    def test_format_upcoming_event_with_location(self, mock_upcoming_event):
        """Test formatting upcoming event with location."""
        mock_upcoming_event.location_display_name = "Building B"
        mock_upcoming_event.is_online_meeting = False

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_upcoming_event(mock_upcoming_event)

        assert any("• Client Call" in line for line in lines)
        assert any("4:00 PM - 5:00 PM" in line for line in lines)
        assert any("📍 Building B" in line for line in lines)

    def test_format_upcoming_event_online(self, mock_upcoming_event):
        """Test formatting upcoming online event."""
        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_upcoming_event(mock_upcoming_event)

        assert any("💻 Online" in line for line in lines)

    def test_format_upcoming_event_urgent(self):
        """Test formatting upcoming event that's starting soon."""
        event = Mock(spec=CachedEvent)
        event.subject = "Urgent Meeting"
        event.location_display_name = None
        event.is_online_meeting = False
        event.format_time_range.return_value = "3:00 PM - 4:00 PM"
        event.time_until_start.return_value = 3  # 3 minutes

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_upcoming_event(event)

        assert any("🔔 Starting in 3 minutes!" in line for line in lines)

    def test_format_upcoming_event_normal_timing(self):
        """Test formatting upcoming event with normal timing."""
        event = Mock(spec=CachedEvent)
        event.subject = "Normal Meeting"
        event.location_display_name = None
        event.is_online_meeting = False
        event.format_time_range.return_value = "3:00 PM - 4:00 PM"
        event.time_until_start.return_value = 30  # 30 minutes

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_upcoming_event(event)

        assert any("⏰ In 30 minutes" in line for line in lines)

    def test_format_upcoming_event_far_future(self):
        """Test formatting upcoming event that's far in the future."""
        event = Mock(spec=CachedEvent)
        event.subject = "Future Meeting"
        event.location_display_name = None
        event.is_online_meeting = False
        event.format_time_range.return_value = "3:00 PM - 4:00 PM"
        event.time_until_start.return_value = 120  # 2 hours

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_upcoming_event(event)

        # Should not show timing info for events > 1 hour away
        assert not any("In 120 minutes" in line for line in lines)
        assert not any("Starting in" in line for line in lines)


class TestConsoleRendererNavigationHelp:
    """Test navigation help rendering."""

    def test_render_navigation_help_basic(self):
        """Test basic navigation help rendering."""
        renderer = ConsoleRenderer(Mock())
        status_info: Dict[str, Any] = {}

        result = renderer._render_navigation_help(status_info)

        assert "← → Navigate" in result
        assert "Space: Today" in result
        assert "ESC: Exit" in result

    def test_render_navigation_help_with_custom_controls(self):
        """Test navigation help with custom controls."""
        renderer = ConsoleRenderer(Mock())
        status_info = {"navigation_help": "Home: Week Start | End: Week End"}

        result = renderer._render_navigation_help(status_info)

        assert "Home: Week Start" in result
        assert "End: Week End" in result

    def test_render_navigation_help_with_relative_description(self):
        """Test navigation help with relative description."""
        renderer = ConsoleRenderer(Mock())
        status_info = {"relative_description": "Tomorrow"}

        result = renderer._render_navigation_help(status_info)

        assert "📍 Tomorrow" in result

    def test_render_navigation_help_today_relative(self):
        """Test navigation help when relative description is Today."""
        renderer = ConsoleRenderer(Mock())
        status_info = {"relative_description": "Today"}

        result = renderer._render_navigation_help(status_info)

        # Should not show relative description for "Today"
        assert "📍 Today" not in result


class TestConsoleRendererMainRender:
    """Test main render_events method."""

    def create_mock_event(self, subject="Test Event", is_current=False, is_upcoming=True):
        """Helper to create mock events."""
        event = Mock(spec=CachedEvent)
        event.subject = subject
        event.is_current.return_value = is_current
        event.is_upcoming.return_value = is_upcoming
        event.format_time_range.return_value = "2:00 PM - 3:00 PM"
        event.location_display_name = None
        event.is_online_meeting = False
        return event

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_empty_list(self, mock_datetime):
        """Test rendering with empty events list."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_events([])

        assert "🎉 No meetings scheduled for today!" in result
        assert "📅 MICROSOFT 365 CALENDAR" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_with_current_events(self, mock_datetime):
        """Test rendering with current events."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        current_event = self.create_mock_event(
            "Current Meeting", is_current=True, is_upcoming=False
        )

        renderer = ConsoleRenderer(Mock())
        with patch.object(
            renderer, "_format_current_event", return_value=["Current event formatted"]
        ):
            result = renderer.render_events([current_event])

        assert "▶ CURRENT EVENT" in result
        assert "Current event formatted" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_with_upcoming_events(self, mock_datetime):
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
    def test_render_events_interactive_mode(self, mock_datetime):
        """Test rendering in interactive mode."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        status_info = {"interactive_mode": True, "selected_date": "Tuesday, January 02"}

        renderer = ConsoleRenderer(Mock())
        with patch.object(renderer, "_render_navigation_help", return_value="Navigation help"):
            result = renderer.render_events([], status_info)

        assert "Tuesday, January 02" in result
        assert "Navigation help" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_with_status_info(self, mock_datetime):
        """Test rendering with status information."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        status_info = {
            "last_update": "2024-01-01T12:00:00Z",
            "is_cached": True,
            "connection_status": "Connected",
        }

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_events([], status_info)

        assert "📱 Cached Data" in result
        assert "📶 Connected" in result
        assert "Updated:" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_live_data_status(self, mock_datetime):
        """Test rendering with live data status."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        status_info = {"is_cached": False}

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_events([], status_info)

        assert "🌐 Live Data" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_status_update_time_string(self, mock_datetime):
        """Test rendering with string update time."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        status_info = {"last_update": "2024-01-01T15:30:00Z"}

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_events([], status_info)

        assert "Updated:" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_status_update_time_datetime(self, mock_datetime):
        """Test rendering with datetime update time."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        update_time = datetime(2024, 1, 1, 15, 30, 0, tzinfo=pytz.UTC)
        status_info = {"last_update": update_time}

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_events([], status_info)

        assert "Updated:" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_status_invalid_update_time(self, mock_datetime):
        """Test rendering with invalid update time."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        status_info = {"last_update": "invalid-date"}

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_events([], status_info)

        # Should not crash, should handle gracefully
        assert "📅 MICROSOFT 365 CALENDAR" in result

    @patch("calendarbot.display.console_renderer.logger")
    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_exception_handling(self, mock_datetime, mock_logger):
        """Test exception handling in render_events."""
        mock_datetime.now.side_effect = Exception("Test exception")

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_events([])

        assert "Error rendering calendar: Test exception" in result
        mock_logger.error.assert_called_once()

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_events_later_today_section(self, mock_datetime):
        """Test rendering with later today events."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        # Create 6 upcoming events to trigger "later today" section
        upcoming_events = [
            self.create_mock_event(f"Meeting {i}", is_upcoming=True) for i in range(1, 7)
        ]

        renderer = ConsoleRenderer(Mock())
        with patch.object(renderer, "_format_upcoming_event", return_value=["Event line"]):
            result = renderer.render_events(upcoming_events)

        assert "⏰ LATER TODAY" in result


class TestConsoleRendererErrorHandling:
    """Test error rendering functionality."""

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_error_without_cached_events(self, mock_datetime):
        """Test error rendering without cached events."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_error("Connection failed")

        assert "⚠️  CONNECTION ISSUE" in result
        assert "Connection failed" in result
        assert "❌ No cached data available" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_error_with_cached_events(self, mock_datetime):
        """Test error rendering with cached events."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        cached_event = Mock(spec=CachedEvent)
        cached_event.subject = "Cached Meeting"
        cached_event.format_time_range.return_value = "2:00 PM - 3:00 PM"
        cached_event.location_display_name = "Room A"

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_error("Network error", [cached_event])

        assert "📱 SHOWING CACHED DATA" in result
        assert "Cached Meeting" in result
        assert "📍 Room A" in result

    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_error_with_many_cached_events(self, mock_datetime):
        """Test error rendering limits cached events to 5."""
        mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"

        cached_events = []
        for i in range(10):
            event = Mock(spec=CachedEvent)
            event.subject = f"Meeting {i}"
            event.format_time_range.return_value = "2:00 PM - 3:00 PM"
            event.location_display_name = None
            cached_events.append(event)

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_error("Error", cached_events)  # type: ignore

        # Should only show first 5 events
        assert "Meeting 0" in result
        assert "Meeting 4" in result
        assert "Meeting 9" not in result

    @patch("calendarbot.display.console_renderer.logger")
    @patch("calendarbot.display.console_renderer.datetime")
    def test_render_error_exception_handling(self, mock_datetime, mock_logger):
        """Test exception handling in render_error."""
        mock_datetime.now.side_effect = Exception("Test exception")

        renderer = ConsoleRenderer(Mock())
        result = renderer.render_error("Original error")

        assert "Critical error: Test exception" in result
        mock_logger.error.assert_called_once()


class TestConsoleRendererAuthenticationPrompt:
    """Test authentication prompt rendering."""

    def test_render_authentication_prompt(self):
        """Test authentication prompt rendering."""
        renderer = ConsoleRenderer(Mock())
        result = renderer.render_authentication_prompt(
            "https://microsoft.com/devicelogin", "ABCD1234"
        )

        assert "🔐 MICROSOFT 365 AUTHENTICATION REQUIRED" in result
        assert "https://microsoft.com/devicelogin" in result
        assert "ABCD1234" in result
        assert "Waiting for authentication..." in result


class TestConsoleRendererScreenControl:
    """Test screen control functionality."""

    @patch("os.system")
    @patch("os.name", "posix")
    def test_clear_screen_posix(self, mock_system):
        """Test screen clearing on POSIX systems."""
        renderer = ConsoleRenderer(Mock())
        renderer.clear_screen()

        mock_system.assert_called_once_with("clear")

    @patch("os.system")
    @patch("os.name", "nt")
    def test_clear_screen_windows(self, mock_system):
        """Test screen clearing on Windows."""
        renderer = ConsoleRenderer(Mock())
        renderer.clear_screen()

        mock_system.assert_called_once_with("cls")

    @patch("builtins.print")
    def test_display_with_clear_normal_mode(self, mock_print):
        """Test display with clear in normal mode."""
        renderer = ConsoleRenderer(Mock())
        renderer.log_area_enabled = False

        with patch.object(renderer, "clear_screen") as mock_clear:
            renderer.display_with_clear("Test content")

        mock_clear.assert_called_once()
        mock_print.assert_called()

    def test_display_with_clear_split_mode(self):
        """Test display with clear in split mode."""
        renderer = ConsoleRenderer(Mock())
        renderer.log_area_enabled = True

        with patch.object(renderer, "_display_with_split_logging") as mock_split:
            renderer.display_with_clear("Test content")

        mock_split.assert_called_once_with("Test content")


class TestConsoleRendererSplitDisplay:
    """Test split display functionality."""

    @patch("calendarbot.display.console_renderer.logger")
    def test_enable_split_display(self, mock_logger):
        """Test enabling split display mode."""
        renderer = ConsoleRenderer(Mock())
        renderer.enable_split_display(max_log_lines=3)

        assert renderer.log_area_enabled is True
        assert renderer.max_log_lines == 3
        assert renderer.log_area_lines == []
        mock_logger.debug.assert_called_with("Split display mode enabled")

    @patch("calendarbot.display.console_renderer.logger")
    def test_disable_split_display(self, mock_logger):
        """Test disabling split display mode."""
        renderer = ConsoleRenderer(Mock())
        renderer.log_area_enabled = True
        renderer.log_area_lines = ["test"]

        renderer.disable_split_display()

        assert renderer.log_area_enabled is False
        assert renderer.log_area_lines == []
        mock_logger.debug.assert_called_with("Split display mode disabled")

    @patch("calendarbot.display.console_renderer.logger")
    def test_update_log_area_enabled(self, mock_logger):
        """Test updating log area when enabled."""
        renderer = ConsoleRenderer(Mock())
        renderer.enable_split_display(max_log_lines=3)

        log_lines = ["Line 1", "Line 2", "Line 3", "Line 4", "Line 5"]
        renderer.update_log_area(log_lines)

        # Should keep only last 3 lines
        assert len(renderer.log_area_lines) == 3
        assert renderer.log_area_lines == ["Line 3", "Line 4", "Line 5"]
        mock_logger.debug.assert_called_with("Log area updated with 3 lines")

    def test_update_log_area_disabled(self):
        """Test updating log area when disabled."""
        renderer = ConsoleRenderer(Mock())
        renderer.log_area_enabled = False

        log_lines = ["Line 1", "Line 2"]
        renderer.update_log_area(log_lines)

        # Should not update when disabled
        assert renderer.log_area_lines == []

    @patch("calendarbot.display.console_renderer.logger")
    def test_update_log_area_empty_lines(self, mock_logger):
        """Test updating log area with empty lines."""
        renderer = ConsoleRenderer(Mock())
        renderer.enable_split_display(max_log_lines=3)

        renderer.update_log_area([])

        assert renderer.log_area_lines == []
        mock_logger.debug.assert_called_with("Log area updated with 0 lines")

    def test_get_log_area_status_enabled(self):
        """Test getting log area status when enabled."""
        renderer = ConsoleRenderer(Mock())
        renderer.enable_split_display(max_log_lines=5)
        renderer.log_area_lines = ["Line 1", "Line 2"]

        status = renderer.get_log_area_status()

        assert status["enabled"] is True
        assert status["max_lines"] == 5
        assert status["current_lines"] == 2
        assert status["log_content"] == ["Line 1", "Line 2"]

    def test_get_log_area_status_disabled(self):
        """Test getting log area status when disabled."""
        renderer = ConsoleRenderer(Mock())

        status = renderer.get_log_area_status()

        assert status["enabled"] is False
        assert status["max_lines"] == 0
        assert status["current_lines"] == 0
        assert status["log_content"] == []


class TestConsoleRendererSplitLogging:
    """Test split logging display functionality."""

    @patch("os.get_terminal_size")
    @patch("builtins.print")
    def test_display_with_split_logging_normal_terminal(self, mock_print, mock_terminal_size):
        """Test split logging with normal terminal size."""
        mock_terminal_size.return_value.lines = 30

        renderer = ConsoleRenderer(Mock())
        renderer.log_area_enabled = True
        renderer.log_area_lines = ["Log line 1", "Log line 2"]

        with patch.object(renderer, "clear_screen"):
            renderer._display_with_split_logging("Main content\nLine 2\nLine 3")

        # Should print main content and log area
        mock_print.assert_called()

    @patch("os.get_terminal_size")
    @patch("builtins.print")
    def test_display_with_split_logging_small_terminal(self, mock_print, mock_terminal_size):
        """Test split logging with small terminal."""
        mock_terminal_size.return_value.lines = 10

        renderer = ConsoleRenderer(Mock())
        renderer.log_area_enabled = True
        renderer.log_area_lines = ["Log line 1"]

        with patch.object(renderer, "clear_screen"):
            renderer._display_with_split_logging("Main content")

        mock_print.assert_called()

    @patch("os.get_terminal_size")
    @patch("builtins.print")
    def test_display_with_split_logging_os_error(self, mock_print, mock_terminal_size):
        """Test split logging when terminal size unavailable."""
        mock_terminal_size.side_effect = OSError("No terminal")

        renderer = ConsoleRenderer(Mock())
        renderer.log_area_enabled = True
        renderer.log_area_lines = ["Log line"]

        with patch.object(renderer, "clear_screen"):
            renderer._display_with_split_logging("Main content")

        # Should use default height of 24
        mock_print.assert_called()

    @patch("os.get_terminal_size")
    @patch("builtins.print")
    def test_display_with_split_logging_no_log_area(self, mock_print, mock_terminal_size):
        """Test split logging with no log area content."""
        mock_terminal_size.return_value.lines = 30

        renderer = ConsoleRenderer(Mock())
        renderer.log_area_enabled = True
        renderer.log_area_lines = []

        with patch.object(renderer, "clear_screen"):
            renderer._display_with_split_logging("Main content")

        mock_print.assert_called()

    @patch("os.get_terminal_size")
    @patch("builtins.print")
    def test_display_with_split_logging_long_content(self, mock_print, mock_terminal_size):
        """Test split logging with long content that gets truncated."""
        mock_terminal_size.return_value.lines = 5  # Very small terminal

        renderer = ConsoleRenderer(Mock())
        renderer.log_area_enabled = True
        renderer.log_area_lines = ["Log 1", "Log 2"]

        long_content = "\n".join([f"Line {i}" for i in range(20)])

        with patch.object(renderer, "clear_screen"):
            renderer._display_with_split_logging(long_content)

        # Should handle truncation gracefully
        mock_print.assert_called()


class TestConsoleRendererEdgeCases:
    """Test edge cases and error conditions."""

    def test_render_events_none_events(self):
        """Test rendering with None events."""
        renderer = ConsoleRenderer(Mock())

        # Should handle None gracefully by treating it as empty list
        with patch("calendarbot.display.console_renderer.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "Monday, January 01"
            result = renderer.render_events(None)

        assert "🎉 No meetings scheduled for today!" in result

    def test_format_current_event_duration_calculation(self):
        """Test current event duration calculation edge cases."""
        renderer = ConsoleRenderer(Mock())

        # Event with zero duration
        now = datetime.now(pytz.UTC)
        event = Mock(spec=CachedEvent)
        event.subject = "Zero Duration"
        event.start_dt = now
        event.end_dt = now  # Same time
        event.location_display_name = None
        event.is_online_meeting = False
        event.format_time_range.return_value = "2:00 PM - 2:00 PM"

        with patch("calendarbot.utils.helpers.get_timezone_aware_now", return_value=now):
            lines = renderer._format_current_event(event)

        # Should handle zero duration - no duration shown for 0-minute events
        assert not any("(0min)" in line for line in lines)
        assert any("2:00 PM - 2:00 PM" in line for line in lines)

    def test_format_upcoming_event_time_until_none(self):
        """Test upcoming event when time_until_start returns None."""
        event = Mock(spec=CachedEvent)
        event.subject = "Past Event"
        event.location_display_name = None
        event.is_online_meeting = False
        event.format_time_range.return_value = "1:00 PM - 2:00 PM"
        event.time_until_start.return_value = None  # Event already started

        renderer = ConsoleRenderer(Mock())
        lines = renderer._format_upcoming_event(event)

        # Should not show timing info for past events
        assert not any("Starting in" in line for line in lines)
        assert not any("In " in line for line in lines)

    def test_render_navigation_help_edge_cases(self):
        """Test navigation help with edge case inputs."""
        renderer = ConsoleRenderer(Mock())

        # Empty navigation help
        status_info = {"navigation_help": ""}
        result = renderer._render_navigation_help(status_info)
        assert "← → Navigate" in result

        # Partial navigation help
        status_info = {"navigation_help": "Home: Something"}
        result = renderer._render_navigation_help(status_info)
        assert "Home: Week Start" in result

    def test_truncate_text_boundary_conditions(self):
        """Test text truncation boundary conditions."""
        renderer = ConsoleRenderer(Mock())

        # Test with max_length of 3 (minimum for ellipsis)
        result = renderer._truncate_text("Test", 3)
        assert result == "..."

        # Test with max_length of 5 (longer than text)
        result = renderer._truncate_text("Test", 5)
        assert result == "Test"

        # Test with max_length of 3 for longer text
        result = renderer._truncate_text("Testing", 3)
        assert result == "..."
