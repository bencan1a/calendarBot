"""Tests for HTML-based display renderer."""

from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest
import pytz

from calendarbot.cache.models import CachedEvent
from calendarbot.display.html_renderer import HTMLRenderer


class TestHTMLRendererInitialization:
    """Test HTML renderer initialization and configuration."""

    def test_init_default_theme(self) -> None:
        """Test HTML renderer initialization with default theme."""
        settings = Mock()
        del settings.web_theme  # No web_theme attribute

        renderer = HTMLRenderer(settings)

        # DEBUG: Log actual theme for diagnosis
        print(f"DEBUG: Actual default theme is: {renderer.theme}")
        print(f"DEBUG: Expected theme should be: 4x8 (based on HTMLRenderer line 24)")

        assert renderer.settings == settings
        assert renderer.theme == "4x8"  # Fixed: Default is 4x8, not 3x4

    def test_init_with_3x4_theme(self) -> None:
        """Test HTML renderer initialization with 3x4 theme."""
        settings = Mock()
        settings.web_theme = "3x4"

        renderer = HTMLRenderer(settings)

        assert renderer.settings == settings
        assert renderer.theme == "3x4"

    def test_init_with_4x8_theme(self) -> None:
        """Test HTML renderer initialization with 4x8 theme."""
        settings = Mock()
        settings.web_theme = "4x8"

        renderer = HTMLRenderer(settings)

        assert renderer.settings == settings
        assert renderer.theme == "4x8"


class TestHTMLRendererRenderEvents:
    """Test main render_events method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.settings.web_theme = "3x4"
        self.renderer = HTMLRenderer(self.settings)

    @patch("calendarbot.display.html_renderer.datetime")
    def test_render_events_empty_list(self, mock_datetime: Any) -> None:
        """Test rendering with empty events list."""
        mock_now = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now

        result = self.renderer.render_events([])

        assert "<!DOCTYPE html>" in result
        assert "No meetings scheduled!" in result
        assert "Enjoy your free time" in result
        assert "Friday, December 15" in result

    @patch("calendarbot.display.html_renderer.datetime")
    def test_render_events_with_status_info(self, mock_datetime: Any) -> None:
        """Test rendering with status information."""
        mock_now = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now

        status_info = {
            "interactive_mode": True,
            "selected_date": "Monday, December 18",
            "last_update": "2023-12-15T10:00:00Z",
            "is_cached": True,
            "connection_status": "Good",
        }

        result = self.renderer.render_events([], status_info)

        assert "Monday, December 18" in result
        assert "📱 Cached Data" in result
        assert "📶 Good" in result
        assert "Updated:" in result

    @patch("calendarbot.display.html_renderer.datetime")
    def test_render_events_interactive_mode(self, mock_datetime: Any) -> None:
        """Test rendering in interactive mode."""
        mock_now = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now

        status_info = {
            "interactive_mode": True,
            "selected_date": "Today",
            "relative_description": "Tomorrow",
        }

        result = self.renderer.render_events([], status_info)

        assert 'onclick="navigate(' in result
        assert "Navigate" in result
        # Relative date highlighting was removed, just check for basic structure
        assert "Today" in result  # selected_date is "Today"

    def test_render_events_error_handling(self) -> None:
        """Test error handling in render_events."""
        # Mock an exception during rendering
        with patch.object(self.renderer, "_build_status_line", side_effect=Exception("Test error")):
            result = self.renderer.render_events([])

            assert "Error rendering calendar: Test error" in result
            assert "<!DOCTYPE html>" in result

    @patch("calendarbot.display.html_renderer.datetime")
    def test_render_events_with_current_and_upcoming_events(self, mock_datetime: Any) -> None:
        """Test rendering with current and upcoming events."""
        mock_now = datetime(2023, 12, 15, 10, 30, 0, tzinfo=pytz.UTC)
        mock_datetime.now.return_value = mock_now

        # Create mock events with proper datetime attributes
        current_event = Mock(spec=CachedEvent)
        current_event.is_current.return_value = True
        current_event.is_upcoming.return_value = False
        current_event.subject = "Current Meeting"
        current_event.start_dt = datetime(2023, 12, 15, 10, 0, 0, tzinfo=pytz.UTC)
        current_event.end_dt = datetime(2023, 12, 15, 11, 0, 0, tzinfo=pytz.UTC)
        current_event.location_display_name = None
        current_event.is_online_meeting = False
        current_event.format_time_range.return_value = "10:00 AM - 11:00 AM"

        upcoming_event = Mock(spec=CachedEvent)
        upcoming_event.is_current.return_value = False
        upcoming_event.is_upcoming.return_value = True
        upcoming_event.subject = "Next Meeting"
        upcoming_event.location_display_name = None
        upcoming_event.is_online_meeting = False
        upcoming_event.format_time_range.return_value = "11:00 AM - 12:00 PM"
        upcoming_event.time_until_start.return_value = 30

        events = [current_event, upcoming_event]

        # Mock the HTML formatting methods to avoid complex setup
        with patch.object(
            self.renderer,
            "_format_current_event_html",
            return_value="<div>Current Event HTML</div>",
        ):
            with patch.object(
                self.renderer,
                "_format_upcoming_event_html",
                return_value="<div>Upcoming Event HTML</div>",
            ):
                result = self.renderer.render_events(events)  # type: ignore

                assert "▶ Current Event" in result
                assert "📋 Next Up" in result
                assert "Current Event HTML" in result
                assert "Upcoming Event HTML" in result


class TestHTMLRendererGetTimestampHTML:
    """Test timestamp HTML generation for navigation area."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.renderer = HTMLRenderer(self.settings)

    def test_get_timestamp_html_no_info(self) -> None:
        """Test timestamp generation with no status info."""
        result = self.renderer._get_timestamp_html(None)
        assert result == ""

    def test_get_timestamp_html_no_last_update(self) -> None:
        """Test timestamp generation with no last_update."""
        status_info = {"is_cached": True}
        result = self.renderer._get_timestamp_html(status_info)
        assert result == ""

    @patch("pytz.timezone")
    @patch("calendarbot.display.html_renderer.datetime")
    def test_get_timestamp_html_with_string_datetime(
        self, mock_datetime_module: Any, mock_timezone: Any
    ) -> None:
        """Test timestamp generation with string datetime."""
        # Mock Pacific timezone
        mock_pacific_tz = Mock()
        mock_timezone.return_value = mock_pacific_tz

        # Create a simple mock datetime that properly handles chaining
        mock_update_time = Mock()
        mock_update_time.tzinfo = Mock()  # Has timezone info
        mock_update_time.astimezone.return_value.astimezone.return_value.strftime.return_value = (
            "10:00 AM"
        )

        # Mock datetime.fromisoformat
        mock_datetime_module.fromisoformat.return_value = mock_update_time

        status_info = {"last_update": "2023-12-15T18:00:00Z"}
        result = self.renderer._get_timestamp_html(status_info)

        assert result == "Updated: 10:00 AM"

    def test_get_timestamp_html_with_datetime_object(self) -> None:
        """Test timestamp generation with datetime object."""
        mock_update_time = Mock()
        mock_update_time.tzinfo = None  # Simulate no timezone info

        with patch("pytz.timezone") as mock_timezone, patch("pytz.utc.localize") as mock_localize:

            mock_pacific_tz = Mock()
            mock_timezone.return_value = mock_pacific_tz

            mock_utc_time = Mock()
            mock_pacific_time = Mock()
            mock_pacific_time.strftime.return_value = "10:00 AM"

            mock_localize.return_value = mock_utc_time
            mock_utc_time.astimezone.return_value = mock_pacific_time

            status_info = {"last_update": mock_update_time}
            result = self.renderer._get_timestamp_html(status_info)

            assert result == "Updated: 10:00 AM"

    def test_get_timestamp_html_parsing_error(self) -> None:
        """Test handling of timestamp parsing errors."""
        status_info = {"last_update": "invalid-date-format"}
        result = self.renderer._get_timestamp_html(status_info)

        # Should return empty string on parsing error
        assert result == ""


class TestHTMLRendererBuildStatusLine:
    """Test status line building."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.renderer = HTMLRenderer(self.settings)

    def test_build_status_line_no_info(self) -> None:
        """Test building status line with no status info."""
        result = self.renderer._build_status_line(None)
        assert result == ""

    def test_build_status_line_empty_dict(self) -> None:
        """Test building status line with empty status dict."""
        result = self.renderer._build_status_line({})
        assert result == ""

    @patch("pytz.timezone")
    @patch("pytz.utc")
    @patch("calendarbot.display.html_renderer.datetime")
    def test_build_status_line_with_last_update_string(
        self, mock_datetime_module: Any, mock_utc: Any, mock_timezone: Any
    ) -> None:
        """Test building status line with last update as string."""
        # Mock Pacific timezone
        mock_pacific_tz = Mock()
        mock_timezone.return_value = mock_pacific_tz

        # Create a simple mock datetime that properly handles chaining
        mock_update_time = Mock()
        mock_update_time.tzinfo = Mock()  # Has timezone info
        mock_update_time.astimezone.return_value.astimezone.return_value.strftime.return_value = (
            "10:00 AM"
        )

        # Mock datetime.fromisoformat
        mock_datetime_module.fromisoformat.return_value = mock_update_time

        status_info = {"last_update": "2023-12-15T18:00:00Z"}
        result = self.renderer._build_status_line(status_info)

        # Timestamp was moved to navigation, status line should only show cached data indicator
        assert result == ""

    def test_build_status_line_with_last_update_datetime(self) -> None:
        """Test building status line with last update as datetime object."""
        mock_update_time = Mock()
        mock_update_time.tzinfo = None  # Simulate no timezone info

        with patch("pytz.timezone") as mock_timezone, patch("pytz.utc.localize") as mock_localize:

            mock_pacific_tz = Mock()
            mock_timezone.return_value = mock_pacific_tz

            mock_utc_time = Mock()
            mock_pacific_time = Mock()
            mock_pacific_time.strftime.return_value = "10:00 AM"

            mock_localize.return_value = mock_utc_time
            mock_utc_time.astimezone.return_value = mock_pacific_time

            status_info = {"last_update": mock_update_time}
            result = self.renderer._build_status_line(status_info)

            # Timestamp was moved to navigation, status line should only show cached data indicator
            assert result == ""

    def test_build_status_line_cached_data(self) -> None:
        """Test building status line with cached data indicator."""
        status_info = {"is_cached": True}
        result = self.renderer._build_status_line(status_info)

        assert "📱 Cached Data" in result

    def test_build_status_line_live_data(self) -> None:
        """Test building status line with live data indicator."""
        status_info = {"is_cached": False}
        result = self.renderer._build_status_line(status_info)

        # Live Data indicator was removed, should return empty string for non-cached
        assert result == ""

    def test_build_status_line_with_connection_status(self) -> None:
        """Test building status line with connection status."""
        status_info = {"connection_status": "Excellent"}
        result = self.renderer._build_status_line(status_info)

        assert "📶 Excellent" in result

    def test_build_status_line_combined_info(self) -> None:
        """Test building status line with multiple status elements."""
        status_info = {"is_cached": True, "connection_status": "Good"}
        result = self.renderer._build_status_line(status_info)

        assert "📱 Cached Data" in result
        assert "📶 Good" in result
        assert " | " in result

    def test_build_status_line_update_parsing_error(self) -> None:
        """Test handling of last_update parsing errors."""
        status_info = {"last_update": "invalid-date-format", "is_cached": True}
        result = self.renderer._build_status_line(status_info)

        # Should still include other status info despite update parsing error
        assert "📱 Cached Data" in result
        assert "Updated:" not in result


class TestHTMLRendererRenderEventsContent:
    """Test events content rendering."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.renderer = HTMLRenderer(self.settings)

    def test_render_events_content_empty(self) -> None:
        """Test rendering events content with empty list."""
        result = self.renderer._render_events_content([], False)

        assert "No meetings scheduled!" in result
        assert "Enjoy your free time" in result
        assert "🎉" in result

    def test_render_events_content_current_events(self) -> None:
        """Test rendering events content with current events."""
        current_event = Mock(spec=CachedEvent)
        current_event.is_current.return_value = True
        current_event.is_upcoming.return_value = False
        current_event.subject = "Current Meeting"

        with patch.object(
            self.renderer,
            "_format_current_event_html",
            return_value="<div>Current Event HTML</div>",
        ):
            result = self.renderer._render_events_content([current_event], False)

            assert "▶ Current Event" in result
            assert "Current Event HTML" in result

    def test_render_events_content_upcoming_events(self) -> None:
        """Test rendering events content with upcoming events."""
        upcoming_event = Mock(spec=CachedEvent)
        upcoming_event.is_current.return_value = False
        upcoming_event.is_upcoming.return_value = True
        upcoming_event.subject = "Next Meeting"

        with patch.object(
            self.renderer,
            "_format_upcoming_event_html",
            return_value="<div>Upcoming Event HTML</div>",
        ):
            result = self.renderer._render_events_content([upcoming_event], False)

            assert "📋 Next Up" in result
            assert "Upcoming Event HTML" in result

    def test_render_events_content_later_events(self) -> None:
        """Test rendering events content with later events (4+ upcoming)."""
        # Create 5 upcoming events to trigger "Later Today" section
        upcoming_events = []
        for i in range(5):
            event = Mock(spec=CachedEvent)
            event.is_current.return_value = False
            event.is_upcoming.return_value = True
            event.subject = f"Meeting {i+1}"
            event.location_display_name = None
            event.is_online_meeting = False
            event.format_time_range.return_value = f"10:{i+1}0 AM - 11:{i+1}0 AM"
            upcoming_events.append(event)

        with patch.object(
            self.renderer,
            "_format_upcoming_event_html",
            return_value="<div>Upcoming Event HTML</div>",
        ):
            result = self.renderer._render_events_content(upcoming_events, False)  # type: ignore

            assert "📋 Next Up" in result
            assert "⏰ Later Today" in result
            assert "Meeting 4" in result  # 4th event (index 3) should be in later section
            assert "Meeting 5" in result  # 5th event should be in later section

    def test_render_events_content_later_events_with_location(self) -> None:
        """Test rendering later events with location information."""
        # Create 5 upcoming events to trigger later section
        upcoming_events = []
        for i in range(5):
            event = Mock(spec=CachedEvent)
            event.is_current.return_value = False
            event.is_upcoming.return_value = True
            event.subject = f"Meeting {i+1}"
            # 4th event has location, 5th event is online meeting
            event.location_display_name = f"Room {i+1}" if i == 3 else None
            event.is_online_meeting = i == 4  # Fifth event is online
            event.format_time_range.return_value = f"10:{i+1}0 AM - 11:{i+1}0 AM"
            upcoming_events.append(event)

        with patch.object(
            self.renderer,
            "_format_upcoming_event_html",
            return_value="<div>Upcoming Event HTML</div>",
        ):
            result = self.renderer._render_events_content(upcoming_events, False)  # type: ignore

            assert "⏰ Later Today" in result
            assert "📍 Room 4" in result  # 4th event has location
            # Online meeting indicators were removed
            assert "Meeting 5" in result  # 5th event should still be shown

    def test_render_events_content_filter_teams_location(self) -> None:
        """Test filtering out Microsoft Teams Meeting location text."""
        upcoming_events = []
        for i in range(4):
            event = Mock(spec=CachedEvent)
            event.is_current.return_value = False
            event.is_upcoming.return_value = True
            event.subject = f"Meeting {i+1}"
            event.location_display_name = "Microsoft Teams Meeting" if i == 3 else None
            event.is_online_meeting = False
            event.format_time_range.return_value = f"10:{i+1}0 AM - 11:{i+1}0 AM"
            upcoming_events.append(event)

        with patch.object(
            self.renderer,
            "_format_upcoming_event_html",
            return_value="<div>Upcoming Event HTML</div>",
        ):
            result = self.renderer._render_events_content(upcoming_events, False)  # type: ignore

            # Microsoft Teams Meeting location should be filtered out
            assert "📍 Microsoft Teams Meeting" not in result


class TestHTMLRendererFormatCurrentEvent:
    """Test current event HTML formatting."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.renderer = HTMLRenderer(self.settings)

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_current_event_html_basic(self, mock_get_now: Any) -> None:
        """Test basic current event HTML formatting."""
        now = datetime(2023, 12, 15, 10, 30, 0, tzinfo=pytz.UTC)
        mock_get_now.return_value = now

        event = Mock(spec=CachedEvent)
        event.subject = "Team Meeting"
        event.start_dt = datetime(2023, 12, 15, 10, 0, 0, tzinfo=pytz.UTC)
        event.end_dt = datetime(2023, 12, 15, 11, 0, 0, tzinfo=pytz.UTC)
        event.location_display_name = None
        event.is_online_meeting = False
        event.format_time_range.return_value = "10:00 AM - 11:00 AM"

        result = self.renderer._format_current_event_html(event)

        assert "Team Meeting" in result
        assert "10:00 AM - 11:00 AM" in result
        assert "(60min)" in result  # Duration
        assert "30 minutes remaining" in result  # Time remaining

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_current_event_html_with_location(self, mock_get_now: Any) -> None:
        """Test current event HTML formatting with location."""
        now = datetime(2023, 12, 15, 10, 30, 0, tzinfo=pytz.UTC)
        mock_get_now.return_value = now

        event = Mock(spec=CachedEvent)
        event.subject = "Team Meeting"
        event.start_dt = datetime(2023, 12, 15, 10, 0, 0, tzinfo=pytz.UTC)
        event.end_dt = datetime(2023, 12, 15, 11, 0, 0, tzinfo=pytz.UTC)
        event.location_display_name = "Conference Room A"
        event.is_online_meeting = False
        event.format_time_range.return_value = "10:00 AM - 11:00 AM"

        result = self.renderer._format_current_event_html(event)

        assert "📍 Conference Room A" in result

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_current_event_html_online_meeting(self, mock_get_now: Any) -> None:
        """Test current event HTML formatting for online meeting."""
        now = datetime(2023, 12, 15, 10, 30, 0, tzinfo=pytz.UTC)
        mock_get_now.return_value = now

        event = Mock(spec=CachedEvent)
        event.subject = "Virtual Standup"
        event.start_dt = datetime(2023, 12, 15, 10, 0, 0, tzinfo=pytz.UTC)
        event.end_dt = datetime(2023, 12, 15, 10, 30, 0, tzinfo=pytz.UTC)
        event.location_display_name = None
        event.is_online_meeting = True
        event.format_time_range.return_value = "10:00 AM - 10:30 AM"

        result = self.renderer._format_current_event_html(event)

        # Online meeting indicators were removed
        assert "Virtual Standup" in result

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_current_event_html_filter_teams_location(self, mock_get_now: Any) -> None:
        """Test filtering Microsoft Teams Meeting location text."""
        now = datetime(2023, 12, 15, 10, 30, 0, tzinfo=pytz.UTC)
        mock_get_now.return_value = now

        event = Mock(spec=CachedEvent)
        event.subject = "Teams Call"
        event.start_dt = datetime(2023, 12, 15, 10, 0, 0, tzinfo=pytz.UTC)
        event.end_dt = datetime(2023, 12, 15, 11, 0, 0, tzinfo=pytz.UTC)
        event.location_display_name = "Microsoft Teams Meeting"
        event.is_online_meeting = False
        event.format_time_range.return_value = "10:00 AM - 11:00 AM"

        result = self.renderer._format_current_event_html(event)

        # Should not include the Microsoft Teams Meeting location
        assert "📍 Microsoft Teams Meeting" not in result

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_current_event_html_time_remaining_error(self, mock_get_now: Any) -> None:
        """Test handling of time remaining calculation errors."""
        mock_get_now.side_effect = Exception("Time calculation error")

        event = Mock(spec=CachedEvent)
        event.subject = "Test Meeting"
        event.start_dt = datetime(2023, 12, 15, 10, 0, 0, tzinfo=pytz.UTC)
        event.end_dt = datetime(2023, 12, 15, 11, 0, 0, tzinfo=pytz.UTC)
        event.location_display_name = None
        event.is_online_meeting = False
        event.format_time_range.return_value = "10:00 AM - 11:00 AM"

        result = self.renderer._format_current_event_html(event)

        # Should still render event without time remaining
        assert "Test Meeting" in result
        assert "minutes remaining" not in result

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_current_event_html_zero_duration(self, mock_get_now: Any) -> None:
        """Test current event formatting with zero duration."""
        now = datetime(2023, 12, 15, 10, 30, 0, tzinfo=pytz.UTC)
        mock_get_now.return_value = now

        event = Mock(spec=CachedEvent)
        event.subject = "Instant Event"
        event.start_dt = datetime(2023, 12, 15, 10, 0, 0, tzinfo=pytz.UTC)
        event.end_dt = datetime(2023, 12, 15, 10, 0, 0, tzinfo=pytz.UTC)  # Same time
        event.location_display_name = None
        event.is_online_meeting = False
        event.format_time_range.return_value = "10:00 AM - 10:00 AM"

        result = self.renderer._format_current_event_html(event)

        # Should not include duration text for zero-duration events
        assert "(0min)" not in result
        assert "10:00 AM - 10:00 AM" in result


class TestHTMLRendererFormatUpcomingEvent:
    """Test upcoming event HTML formatting."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.renderer = HTMLRenderer(self.settings)

    def test_format_upcoming_event_html_basic(self) -> None:
        """Test basic upcoming event HTML formatting."""
        event = Mock(spec=CachedEvent)
        event.subject = "Next Meeting"
        event.location_display_name = None
        event.is_online_meeting = False
        event.format_time_range.return_value = "2:00 PM - 3:00 PM"
        event.time_until_start.return_value = (
            45  # 45 minutes until start (within 60 minute threshold)
        )

        result = self.renderer._format_upcoming_event_html(event)

        assert "Next Meeting" in result
        assert "2:00 PM - 3:00 PM" in result
        assert "⏰ In 45 minutes" in result

    def test_format_upcoming_event_html_with_location(self) -> None:
        """Test upcoming event HTML formatting with location."""
        event = Mock(spec=CachedEvent)
        event.subject = "Client Meeting"
        event.location_display_name = "Meeting Room B"
        event.is_online_meeting = False
        event.format_time_range.return_value = "2:00 PM - 3:00 PM"
        event.time_until_start.return_value = 45

        result = self.renderer._format_upcoming_event_html(event)

        assert "📍 Meeting Room B" in result

    def test_format_upcoming_event_html_online_meeting(self) -> None:
        """Test upcoming event HTML formatting for online meeting."""
        event = Mock(spec=CachedEvent)
        event.subject = "Video Conference"
        event.location_display_name = None
        event.is_online_meeting = True
        event.format_time_range.return_value = "3:00 PM - 4:00 PM"
        event.time_until_start.return_value = 30

        result = self.renderer._format_upcoming_event_html(event)

        # Online meeting indicators were removed
        assert "Video Conference" in result

    def test_format_upcoming_event_html_filter_teams_location(self) -> None:
        """Test filtering Microsoft Teams Meeting location text."""
        event = Mock(spec=CachedEvent)
        event.subject = "Teams Meeting"
        event.location_display_name = "Microsoft Teams Meeting"
        event.is_online_meeting = False
        event.format_time_range.return_value = "3:00 PM - 4:00 PM"
        event.time_until_start.return_value = 45

        result = self.renderer._format_upcoming_event_html(event)

        assert "📍 Microsoft Teams Meeting" not in result

    def test_format_upcoming_event_html_urgent_timing(self) -> None:
        """Test upcoming event with urgent timing (≤5 minutes)."""
        event = Mock(spec=CachedEvent)
        event.subject = "Urgent Meeting"
        event.location_display_name = None
        event.is_online_meeting = False
        event.format_time_range.return_value = "10:35 AM - 11:35 AM"
        event.time_until_start.return_value = 3  # 3 minutes until start

        result = self.renderer._format_upcoming_event_html(event)

        assert "🔔 Starting in 3 minutes!" in result
        assert "urgent" in result.lower()

    def test_format_upcoming_event_html_no_time_until(self) -> None:
        """Test upcoming event when time_until_start returns None."""
        event = Mock(spec=CachedEvent)
        event.subject = "Future Meeting"
        event.location_display_name = "Room C"
        event.is_online_meeting = False
        event.format_time_range.return_value = "5:00 PM - 6:00 PM"
        event.time_until_start.return_value = None

        result = self.renderer._format_upcoming_event_html(event)

        assert "Future Meeting" in result
        assert "📍 Room C" in result
        assert "In " not in result  # No time until display

    def test_format_upcoming_event_html_far_future(self) -> None:
        """Test upcoming event far in the future (>60 minutes)."""
        event = Mock(spec=CachedEvent)
        event.subject = "Later Meeting"
        event.location_display_name = None
        event.is_online_meeting = False
        event.format_time_range.return_value = "4:00 PM - 5:00 PM"
        event.time_until_start.return_value = 120  # 2 hours

        result = self.renderer._format_upcoming_event_html(event)

        assert "Later Meeting" in result
        # Should not show time until for events >60 minutes away
        assert "In 120 minutes" not in result


class TestHTMLRendererNavigationHelp:
    """Test navigation help rendering."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.renderer = HTMLRenderer(self.settings)

    def test_render_navigation_help_basic(self) -> None:
        """Test basic navigation help rendering."""
        status_info: Dict[str, Any] = {}

        result = self.renderer._render_navigation_help(status_info)

        assert "← →" in result
        assert "Navigate" in result
        assert "Space" in result
        assert "Today" in result
        assert "Home/End" in result
        assert "Week" in result
        assert "R" in result
        assert "Refresh" in result

    def test_render_navigation_help_with_relative_date(self) -> None:
        """Test navigation help with relative date information."""
        status_info = {"relative_description": "Tomorrow"}

        result = self.renderer._render_navigation_help(status_info)

        # Relative date highlighting was removed from navigation help
        assert "Tomorrow" in result or "Navigate" in result
        assert "Navigate" in result

    def test_render_navigation_help_today_no_relative(self) -> None:
        """Test navigation help when relative description is 'Today'."""
        status_info = {"relative_description": "Today"}

        result = self.renderer._render_navigation_help(status_info)

        # Should not show relative date info for "Today"
        assert "📍 Today" not in result
        assert "Navigate" in result


class TestHTMLRendererHTMLTemplate:
    """Test HTML template building."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.renderer = HTMLRenderer(self.settings)

    @patch.object(HTMLRenderer, "_get_theme_css_file")
    @patch.object(HTMLRenderer, "_get_theme_js_file")
    def test_build_html_template_interactive_mode(
        self, mock_js_file: Any, mock_css_file: Any
    ) -> None:
        """Test HTML template building in interactive mode."""
        mock_css_file.return_value = "style.css"
        mock_js_file.return_value = "app.js"

        result = self.renderer._build_html_template(
            display_date="Friday, December 15",
            status_line="Updated: 10:00 AM",
            events_content="<div>Events</div>",
            nav_help="<div>Navigation</div>",
            interactive_mode=True,
        )

        assert "<!DOCTYPE html>" in result
        assert "Friday, December 15" in result
        assert "Updated: 10:00 AM" in result
        assert "<div>Events</div>" in result
        assert "<div>Navigation</div>" in result
        assert 'onclick="navigate(' in result
        assert "style.css" in result
        assert "app.js" in result

    @patch.object(HTMLRenderer, "_get_theme_css_file")
    @patch.object(HTMLRenderer, "_get_theme_js_file")
    def test_build_html_template_static_mode(self, mock_js_file: Any, mock_css_file: Any) -> None:
        """Test HTML template building in static mode."""
        mock_css_file.return_value = "3x4.css"
        mock_js_file.return_value = "3x4.js"

        result = self.renderer._build_html_template(
            display_date="Monday, December 18",
            status_line="Live Data",
            events_content="<div>Static Events</div>",
            nav_help="",
            interactive_mode=False,
        )

        assert "Monday, December 18" in result
        assert "Live Data" in result
        assert "<div>Static Events</div>" in result
        assert 'onclick="navigate(' not in result  # No interactive navigation
        assert "<footer" not in result  # No footer in static mode
        assert "3x4.css" in result
        assert "3x4.js" in result


class TestHTMLRendererThemeFiles:
    """Test theme file selection."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()

    def test_get_theme_css_file_3x4(self) -> None:
        """Test CSS file selection for 3x4 theme."""
        self.settings.web_theme = "3x4"
        renderer = HTMLRenderer(self.settings)

        result = renderer._get_theme_css_file()
        assert result == "3x4.css"

    def test_get_theme_css_file_4x8(self) -> None:
        """Test CSS file selection for 4x8 theme."""
        self.settings.web_theme = "4x8"
        renderer = HTMLRenderer(self.settings)

        result = renderer._get_theme_css_file()
        assert result == "4x8.css"

    def test_get_theme_css_file_unknown(self) -> None:
        """Test CSS file selection for unknown theme (defaults to 4x8)."""
        self.settings.web_theme = "unknown"
        renderer = HTMLRenderer(self.settings)

        result = renderer._get_theme_css_file()
        assert result == "4x8.css"

    def test_get_theme_js_file_3x4(self) -> None:
        """Test JS file selection for 3x4 theme."""
        self.settings.web_theme = "3x4"
        renderer = HTMLRenderer(self.settings)

        result = renderer._get_theme_js_file()
        assert result == "3x4.js"

    def test_get_theme_js_file_4x8(self) -> None:
        """Test JS file selection for 4x8 theme."""
        self.settings.web_theme = "4x8"
        renderer = HTMLRenderer(self.settings)

        result = renderer._get_theme_js_file()
        assert result == "4x8.js"

    def test_get_theme_js_file_unknown(self) -> None:
        """Test JS file selection for unknown theme (defaults to 4x8)."""
        self.settings.web_theme = "unknown"
        renderer = HTMLRenderer(self.settings)

        result = renderer._get_theme_js_file()
        assert result == "4x8.js"

    def test_get_theme_icon_3x4(self) -> None:
        """Test theme icon for 3x4 theme."""
        self.settings.web_theme = "3x4"
        renderer = HTMLRenderer(self.settings)

        result = renderer._get_theme_icon()
        assert result == "⚙️"

    def test_get_theme_icon_other(self) -> None:
        """Test theme icon for non-3x4 themes."""
        self.settings.web_theme = "4x8"
        renderer = HTMLRenderer(self.settings)

        result = renderer._get_theme_icon()
        assert result == "⚫"


class TestHTMLRendererEscapeHTML:
    """Test HTML escaping utility."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.renderer = HTMLRenderer(self.settings)

    def test_escape_html_basic_characters(self) -> None:
        """Test escaping basic HTML characters."""
        text = "<script>alert('xss')</script>"
        result = self.renderer._escape_html(text)

        assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" == result

    def test_escape_html_all_special_characters(self) -> None:
        """Test escaping all special HTML characters."""
        text = "&<>\"'test"
        result = self.renderer._escape_html(text)

        assert "&amp;&lt;&gt;&quot;&#x27;test" == result

    def test_escape_html_empty_string(self) -> None:
        """Test escaping empty string."""
        result = self.renderer._escape_html("")
        assert result == ""

    def test_escape_html_none(self) -> None:
        """Test escaping None value."""
        result = self.renderer._escape_html(None)  # type: ignore
        assert result == ""

    def test_escape_html_no_special_characters(self) -> None:
        """Test escaping text with no special characters."""
        text = "Normal text without special characters"
        result = self.renderer._escape_html(text)

        assert result == text


class TestHTMLRendererRenderError:
    """Test error rendering functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.settings.web_theme = "3x4"
        self.renderer = HTMLRenderer(self.settings)

    @patch("calendarbot.display.html_renderer.datetime")
    def test_render_error_basic(self, mock_datetime: Any) -> None:
        """Test basic error rendering."""
        mock_now = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now

        result = self.renderer.render_error("Connection failed")

        assert "<!DOCTYPE html>" in result
        assert "Connection Issue" in result
        assert "Connection failed" in result
        assert "Friday, December 15" in result
        assert "⚠️" in result

    @patch("calendarbot.display.html_renderer.datetime")
    def test_render_error_with_cached_events(self, mock_datetime: Any) -> None:
        """Test error rendering with cached events."""
        mock_now = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now

        cached_event = Mock(spec=CachedEvent)
        cached_event.subject = "Cached Meeting"
        cached_event.location_display_name = "Room A"
        cached_event.format_time_range.return_value = "10:00 AM - 11:00 AM"

        result = self.renderer.render_error("Network error", [cached_event])

        assert "Network error" in result
        assert "📱 Showing Cached Data" in result
        assert "Cached Meeting" in result
        assert "📍 Room A" in result

    @patch("calendarbot.display.html_renderer.datetime")
    def test_render_error_no_cached_data(self, mock_datetime: Any) -> None:
        """Test error rendering with no cached data."""
        mock_now = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now

        result = self.renderer.render_error("Service unavailable", [])

        assert "Service unavailable" in result
        assert "❌ No cached data available" in result

    def test_render_error_exception_handling(self) -> None:
        """Test error rendering when _render_error_html fails."""
        with patch.object(
            self.renderer, "_render_error_html", side_effect=Exception("Render error")
        ):
            result = self.renderer.render_error("Original error")

            assert "Critical Error" in result
            assert "Render error" in result

    @patch("calendarbot.display.html_renderer.datetime")
    def test_render_error_html_many_cached_events(self, mock_datetime: Any) -> None:
        """Test error rendering with many cached events (should limit to 5)."""
        mock_now = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now

        cached_events = []
        for i in range(10):  # Create 10 events
            event = Mock(spec=CachedEvent)
            event.subject = f"Meeting {i+1}"
            event.location_display_name = None
            event.format_time_range.return_value = f"1{i}:00 AM - 1{i}:30 AM"
            cached_events.append(event)

        result = self.renderer.render_error("Too many meetings", cached_events)  # type: ignore

        assert "Meeting 1" in result
        assert "Meeting 5" in result
        assert "Meeting 6" not in result  # Should be limited to 5


class TestHTMLRendererRenderAuthenticationPrompt:
    """Test authentication prompt rendering."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.settings.web_theme = "3x4"
        self.renderer = HTMLRenderer(self.settings)

    def test_render_authentication_prompt_basic(self) -> None:
        """Test basic authentication prompt rendering."""
        verification_uri = "https://microsoft.com/devicelogin"
        user_code = "ABC123DEF"

        result = self.renderer.render_authentication_prompt(verification_uri, user_code)

        assert "<!DOCTYPE html>" in result
        assert "🔐 Authentication Required" in result
        assert "Microsoft 365 Authentication" in result
        assert verification_uri in result
        assert user_code in result
        assert "Visit:" in result
        assert "Enter code:" in result

    def test_render_authentication_prompt_elements(self) -> None:
        """Test authentication prompt contains required elements."""
        verification_uri = "https://login.microsoftonline.com/device"
        user_code = "XYZ789"

        result = self.renderer.render_authentication_prompt(verification_uri, user_code)

        assert "step-number" in result
        assert "step-text" in result
        assert "user-code" in result
        assert "auth-steps" in result
        assert "loading-spinner" in result
        assert "Waiting for authentication" in result

    def test_render_authentication_prompt_theme_integration(self) -> None:
        """Test authentication prompt integrates with theme system."""
        self.renderer.theme = "3x4"

        result = self.renderer.render_authentication_prompt("https://example.com", "CODE123")

        assert f'class="theme-{self.renderer.theme}"' in result


class TestHTMLRendererIntegration:
    """Test HTML renderer integration scenarios."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.settings.web_theme = "3x4"
        self.renderer = HTMLRenderer(self.settings)

    @patch("calendarbot.display.html_renderer.datetime")
    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_full_rendering_workflow_with_events(
        self, mock_get_now: Any, mock_datetime: Any
    ) -> None:
        """Test complete rendering workflow with realistic events."""
        # Set up time mocks
        mock_now = datetime(2023, 12, 15, 10, 30, 0, tzinfo=pytz.UTC)
        mock_datetime.now.return_value = mock_now
        mock_get_now.return_value = mock_now

        # Create realistic events
        current_event = Mock(spec=CachedEvent)
        current_event.is_current.return_value = True
        current_event.is_upcoming.return_value = False
        current_event.subject = "Daily Standup"
        current_event.start_dt = datetime(2023, 12, 15, 10, 0, 0, tzinfo=pytz.UTC)
        current_event.end_dt = datetime(2023, 12, 15, 10, 30, 0, tzinfo=pytz.UTC)
        current_event.location_display_name = None
        current_event.is_online_meeting = True
        current_event.format_time_range.return_value = "10:00 AM - 10:30 AM"

        upcoming_events = []
        for i in range(3):
            event = Mock(spec=CachedEvent)
            event.is_current.return_value = False
            event.is_upcoming.return_value = True
            event.subject = f"Meeting {i+1}"
            event.location_display_name = f"Room {i+1}"
            event.is_online_meeting = False
            event.format_time_range.return_value = f"1{i+1}:00 AM - 1{i+1}:30 AM"
            event.time_until_start.return_value = (i + 1) * 30  # 30, 60, 90 minutes
            upcoming_events.append(event)

        events = [current_event] + upcoming_events

        status_info = {
            "interactive_mode": True,
            "selected_date": "Friday, December 15",
            "last_update": "2023-12-15T10:00:00Z",
            "is_cached": False,
            "connection_status": "Excellent",
            "relative_description": "Today",
        }

        result = self.renderer.render_events(events, status_info)  # type: ignore

        # Verify complete HTML structure
        assert "<!DOCTYPE html>" in result
        assert "Friday, December 15" in result

        # Verify current event section
        assert "▶ Current Event" in result
        assert "Daily Standup" in result
        # Online meeting indicators were removed

        # Verify upcoming events section
        assert "📋 Next Up" in result
        assert "Meeting 1" in result
        assert "📍 Room 1" in result

        # Verify status information - Live Data indicator was removed
        assert "📶 Excellent" in result
        # Timestamp was moved to navigation area

        # Verify interactive navigation
        assert 'onclick="navigate(' in result
        assert "Navigate" in result

    @patch("calendarbot.display.html_renderer.datetime")
    def test_error_recovery_workflow(self, mock_datetime: Any) -> None:
        """Test error recovery with cached data fallback."""
        mock_now = datetime(2023, 12, 15, 10, 30, 0)
        mock_datetime.now.return_value = mock_now

        cached_event = Mock(spec=CachedEvent)
        cached_event.subject = "Important Meeting"
        cached_event.location_display_name = "Executive Boardroom"
        cached_event.format_time_range.return_value = "2:00 PM - 3:00 PM"

        result = self.renderer.render_error("Microsoft Graph API unavailable", [cached_event])

        assert "Connection Issue" in result
        assert "Microsoft Graph API unavailable" in result
        assert "📱 Showing Cached Data" in result
        assert "Important Meeting" in result
        assert "📍 Executive Boardroom" in result

    def test_theme_consistency_across_methods(self) -> None:
        """Test theme consistency across different rendering methods."""
        self.renderer.theme = "3x4"

        # Test main rendering
        events_result = self.renderer.render_events([])
        assert f'class="theme-{self.renderer.theme}"' in events_result

        # Test error rendering
        error_result = self.renderer.render_error("Test error")
        assert f'class="theme-{self.renderer.theme}"' in error_result

        # Test authentication rendering
        auth_result = self.renderer.render_authentication_prompt("https://example.com", "CODE")
        assert f'class="theme-{self.renderer.theme}"' in auth_result
