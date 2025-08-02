"""Tests for Raspberry Pi HTML-based display renderer."""

from datetime import datetime
from typing import Any
from unittest.mock import Mock, patch

import pytz

from calendarbot.cache.models import CachedEvent
from calendarbot.display.rpi_html_renderer import RaspberryPiHTMLRenderer


class TestRPIHTMLRendererInitialization:
    """Test RPI HTML renderer initialization and configuration."""

    def test_init_default_layout(self) -> None:
        """Test RPI HTML renderer initialization with default layout."""
        settings = Mock()
        del settings.web_layout  # No web_layout attribute

        renderer = RaspberryPiHTMLRenderer(settings)

        assert renderer.settings == settings
        assert renderer.layout == "3x4"  # Default for RPI is 3x4, not 4x8 like base HTMLRenderer

    def test_init_with_explicit_layout(self) -> None:
        """Test RPI HTML renderer initialization with explicit layout."""
        settings = Mock()
        settings.web_layout = "4x8"

        renderer = RaspberryPiHTMLRenderer(settings)

        assert renderer.settings == settings
        assert renderer.layout == "4x8"


class TestRPIHTMLRendererTemplateBuilding:
    """Test RPI HTML template building methods."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.settings.web_layout = "3x4"
        self.renderer = RaspberryPiHTMLRenderer(self.settings)

    @patch.object(RaspberryPiHTMLRenderer, "_get_dynamic_resources")
    def test_build_html_template_interactive_mode(self, mock_dynamic_resources: Any) -> None:
        """Test HTML template building in interactive mode."""
        mock_dynamic_resources.return_value = (["style.css"], ["app.js"])

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
        assert "style.css" in result
        assert "app.js" in result
        assert 'width=480, height=800' in result  # RPI-specific viewport

    @patch.object(RaspberryPiHTMLRenderer, "_get_dynamic_resources")
    def test_build_html_template_static_mode(self, mock_dynamic_resources: Any) -> None:
        """Test HTML template building in static mode."""
        mock_dynamic_resources.return_value = (["3x4.css"], ["3x4.js"])

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
        assert 'width=480, height=800' in result  # RPI-specific viewport
        assert "3x4.css" in result
        assert "3x4.js" in result

    def test_generate_header_navigation_with_date_interactive(self) -> None:
        """Test header navigation generation in interactive mode."""
        result = self.renderer._generate_header_navigation_with_date(
            display_date="Friday, December 15", interactive_mode=True
        )

        assert "Friday, December 15" in result
        assert "nav-arrow-left" in result
        assert "nav-arrow-right" in result
        assert 'data-action="prev"' in result
        assert 'data-action="next"' in result
        assert "role=" in result  # Accessibility attributes

    def test_generate_header_navigation_with_date_static(self) -> None:
        """Test header navigation generation in static mode."""
        result = self.renderer._generate_header_navigation_with_date(
            display_date="Friday, December 15", interactive_mode=False
        )

        assert "Friday, December 15" in result
        assert "nav-arrow-left" in result
        assert "nav-arrow-right" in result
        assert 'data-action="prev"' not in result  # No interactive elements
        assert 'data-action="next"' not in result  # No interactive elements

    def test_generate_bottom_status_bar(self) -> None:
        """Test bottom status bar generation."""
        result = self.renderer._generate_bottom_status_bar("Updated: 10:00 AM")

        assert "Updated: 10:00 AM" in result
        assert "calendar-status" in result
        assert "role=" in result  # Accessibility attributes

    def test_render_status_line_html_with_content(self) -> None:
        """Test status line rendering with content."""
        result = self.renderer._render_status_line_html("Updated: 10:00 AM")

        assert "Updated: 10:00 AM" in result
        assert "status-line" in result

    def test_render_status_line_html_empty(self) -> None:
        """Test status line rendering with empty content."""
        result = self.renderer._render_status_line_html("")

        assert result == ""


class TestRPIHTMLRendererEventRendering:
    """Test RPI HTML event rendering methods."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.settings.web_layout = "3x4"
        self.renderer = RaspberryPiHTMLRenderer(self.settings)

    def test_render_events_content_empty(self) -> None:
        """Test rendering events content with empty list."""
        result = self.renderer._render_events_content([], False)

        assert "No meetings scheduled!" in result
        assert "Enjoy your free time" in result
        assert "🎉" in result

    def test_render_no_events_rpi(self) -> None:
        """Test rendering no events state."""
        result = self.renderer._render_no_events_rpi()

        assert "No meetings scheduled!" in result
        assert "Enjoy your free time" in result
        assert "🎉" in result
        assert "no-events" in result
        assert "role=" in result  # Accessibility attributes

    @patch.object(RaspberryPiHTMLRenderer, "_format_current_event_rpi")
    def test_render_current_events_section_rpi(self, mock_format_current: Any) -> None:
        """Test rendering current events section."""
        mock_format_current.return_value = "<div>Current Event HTML</div>"
        
        current_event = Mock(spec=CachedEvent)
        current_event.id = "event123"
        
        result = self.renderer._render_current_events_section_rpi([current_event])

        assert "▶ Current Event" in result
        assert "Current Event HTML" in result
        assert "section-current" in result
        assert "role=" in result  # Accessibility attributes
        mock_format_current.assert_called_once_with(current_event)

    @patch.object(RaspberryPiHTMLRenderer, "_format_upcoming_event_rpi")
    def test_render_next_up_events_section_rpi(self, mock_format_upcoming: Any) -> None:
        """Test rendering Next Up events section."""
        mock_format_upcoming.return_value = "<div>Upcoming Event HTML</div>"
        
        upcoming_events = [Mock(spec=CachedEvent), Mock(spec=CachedEvent)]
        
        result = self.renderer._render_next_up_events_section_rpi(upcoming_events)

        assert "📋 Next Up" in result
        assert "Upcoming Event HTML" in result
        assert "section-upcoming" in result
        assert "role=" in result  # Accessibility attributes
        assert mock_format_upcoming.call_count == 2

    @patch.object(RaspberryPiHTMLRenderer, "_format_later_event_rpi")
    def test_render_later_today_section_rpi(self, mock_format_later: Any) -> None:
        """Test rendering Later Today section."""
        mock_format_later.return_value = "<li>Later Event HTML</li>"
        
        later_events = [Mock(spec=CachedEvent), Mock(spec=CachedEvent), Mock(spec=CachedEvent)]
        
        result = self.renderer._render_later_today_section_rpi(later_events)

        assert "⏰ Later Today" in result
        assert "Later Event HTML" in result
        assert "section-later" in result
        assert "later-events-list" in result
        assert "role=" in result  # Accessibility attributes
        assert mock_format_later.call_count == 3

    @patch.object(RaspberryPiHTMLRenderer, "_render_current_events_section_rpi")
    @patch.object(RaspberryPiHTMLRenderer, "_render_next_up_events_section_rpi")
    @patch.object(RaspberryPiHTMLRenderer, "_render_later_today_section_rpi")
    def test_render_events_content_with_all_event_types(
        self, mock_later: Any, mock_next_up: Any, mock_current: Any
    ) -> None:
        """Test rendering events content with all event types."""
        mock_current.return_value = "<div>Current Section</div>"
        mock_next_up.return_value = "<div>Next Up Section</div>"
        mock_later.return_value = "<div>Later Section</div>"
        
        # Create mock events
        current_event = Mock(spec=CachedEvent)
        current_event.is_current.return_value = True
        current_event.is_upcoming.return_value = False
        
        upcoming_events = []
        for i in range(8):  # Create 8 upcoming events to trigger all sections
            event = Mock(spec=CachedEvent)
            event.is_current.return_value = False
            event.is_upcoming.return_value = True
            upcoming_events.append(event)
        
        events = [current_event] + upcoming_events
        
        result = self.renderer._render_events_content(events, False)

        assert "Current Section" in result
        assert "Next Up Section" in result
        assert "Later Section" in result
        
        # Verify the correct events were passed to each section renderer
        mock_current.assert_called_once()
        mock_next_up.assert_called_once()
        mock_later.assert_called_once()
        
        # Verify the first 3 upcoming events go to Next Up section
        assert len(mock_next_up.call_args[0][0]) == 3
        
        # Verify the next 5 upcoming events go to Later section
        assert len(mock_later.call_args[0][0]) == 5


class TestRPIHTMLRendererFormatting:
    """Test RPI HTML event formatting methods."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.settings.web_layout = "3x4"
        self.renderer = RaspberryPiHTMLRenderer(self.settings)

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_current_event_rpi(self, mock_get_now: Any) -> None:
        """Test formatting current event."""
        now = datetime(2023, 12, 15, 10, 30, 0, tzinfo=pytz.UTC)
        mock_get_now.return_value = now
        
        event = Mock(spec=CachedEvent)
        event.id = "event123"
        event.subject = "Team Meeting"
        event.start_dt = datetime(2023, 12, 15, 10, 0, 0, tzinfo=pytz.UTC)
        event.end_dt = datetime(2023, 12, 15, 11, 0, 0, tzinfo=pytz.UTC)
        event.location_display_name = None
        event.is_online_meeting = False
        event.format_time_range.return_value = "10:00 AM - 11:00 AM"
        
        # Mock the escape_html method
        with patch.object(self.renderer, "_escape_html", side_effect=lambda x: x):
            # Mock the format methods
            with patch.object(
                self.renderer, "_format_event_location_rpi", return_value=""
            ):
                with patch.object(
                    self.renderer, "_format_time_remaining_rpi", 
                    return_value='<div class="time-remaining">⏱️ 30 minutes remaining</div>'
                ):
                    result = self.renderer._format_current_event_rpi(event)
        
        assert "Team Meeting" in result
        assert "10:00 AM - 11:00 AM" in result
        assert "(60min)" in result  # Duration
        assert "30 minutes remaining" in result  # Time remaining
        assert "current-event" in result
        assert 'data-event-id="event123"' in result
        assert "role=" in result  # Accessibility attributes

    def test_format_upcoming_event_rpi(self) -> None:
        """Test formatting upcoming event."""
        event = Mock(spec=CachedEvent)
        event.id = "event456"
        event.subject = "Planning Meeting"
        event.location_display_name = "Conference Room A"
        event.is_online_meeting = False
        event.format_time_range.return_value = "2:00 PM - 3:00 PM"
        event.time_until_start.return_value = 30  # 30 minutes until start
        
        # Mock the escape_html method
        with patch.object(self.renderer, "_escape_html", side_effect=lambda x: x):
            # Mock the format_time_until_rpi method
            with patch.object(
                self.renderer, "_format_time_until_rpi", 
                return_value='<div class="time-until soon">⏰ In 30 minutes</div>'
            ):
                result = self.renderer._format_upcoming_event_rpi(event)
        
        assert "Planning Meeting" in result
        assert "2:00 PM - 3:00 PM" in result
        assert "📍 Conference Room A" in result
        assert "In 30 minutes" in result
        assert "upcoming-event" in result
        assert "event-soon" in result  # Urgency class for 30 minutes
        assert 'data-event-id="event456"' in result
        assert "role=" in result  # Accessibility attributes

    def test_format_event_location_rpi_with_location(self) -> None:
        """Test formatting event location with physical location."""
        event = Mock(spec=CachedEvent)
        event.location_display_name = "Conference Room A"
        
        # Mock the escape_html method
        with patch.object(self.renderer, "_escape_html", side_effect=lambda x: x):
            result = self.renderer._format_event_location_rpi(event)
        
        assert "📍 Conference Room A" in result
        assert "event-location" in result
        assert "location-physical" in result

    def test_format_event_location_rpi_with_teams_meeting(self) -> None:
        """Test formatting event location with Microsoft Teams Meeting."""
        event = Mock(spec=CachedEvent)
        event.location_display_name = "Microsoft Teams Meeting"
        
        result = self.renderer._format_event_location_rpi(event)
        
        # Should filter out Microsoft Teams Meeting
        assert result == ""

    def test_format_event_location_rpi_no_location(self) -> None:
        """Test formatting event location with no location."""
        event = Mock(spec=CachedEvent)
        event.location_display_name = None
        
        result = self.renderer._format_event_location_rpi(event)
        
        assert result == ""

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_time_remaining_rpi(self, mock_get_now: Any) -> None:
        """Test formatting time remaining for current event."""
        now = datetime(2023, 12, 15, 10, 30, 0, tzinfo=pytz.UTC)
        mock_get_now.return_value = now
        
        event = Mock(spec=CachedEvent)
        event.end_dt = datetime(2023, 12, 15, 11, 0, 0, tzinfo=pytz.UTC)
        
        result = self.renderer._format_time_remaining_rpi(event)
        
        assert "30 minutes remaining" in result
        assert "time-remaining" in result
        assert "⏱️" in result

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_time_remaining_rpi_urgent(self, mock_get_now: Any) -> None:
        """Test formatting time remaining with urgent styling (≤5 minutes)."""
        now = datetime(2023, 12, 15, 10, 55, 0, tzinfo=pytz.UTC)
        mock_get_now.return_value = now
        
        event = Mock(spec=CachedEvent)
        event.end_dt = datetime(2023, 12, 15, 11, 0, 0, tzinfo=pytz.UTC)
        
        result = self.renderer._format_time_remaining_rpi(event)
        
        assert "5 minutes remaining" in result
        assert "time-remaining" in result
        assert "urgent" in result  # Urgent class for ≤5 minutes
        assert "⏱️" in result

    @patch("calendarbot.utils.helpers.get_timezone_aware_now")
    def test_format_time_remaining_rpi_error(self, mock_get_now: Any) -> None:
        """Test handling of time remaining calculation errors."""
        mock_get_now.side_effect = Exception("Time calculation error")
        
        event = Mock(spec=CachedEvent)
        event.end_dt = datetime(2023, 12, 15, 11, 0, 0, tzinfo=pytz.UTC)
        
        result = self.renderer._format_time_remaining_rpi(event)
        
        # Should return empty string on error
        assert result == ""

    def test_format_time_until_rpi_soon(self) -> None:
        """Test formatting time until start with soon styling (≤30 minutes)."""
        event = Mock(spec=CachedEvent)
        event.time_until_start.return_value = 25
        
        result = self.renderer._format_time_until_rpi(event)
        
        assert "In 25 minutes" in result
        assert "time-until" in result
        assert "soon" in result  # Soon class for ≤30 minutes
        assert "⏰" in result

    def test_format_time_until_rpi_urgent(self) -> None:
        """Test formatting time until start with urgent styling (≤5 minutes)."""
        event = Mock(spec=CachedEvent)
        event.time_until_start.return_value = 5
        
        result = self.renderer._format_time_until_rpi(event)
        
        assert "Starting in 5 minutes!" in result
        assert "time-until" in result
        assert "urgent" in result  # Urgent class for ≤5 minutes
        assert "🔔" in result  # Different icon for urgent

    def test_format_time_until_rpi_normal(self) -> None:
        """Test formatting time until start with normal styling (>30 minutes)."""
        event = Mock(spec=CachedEvent)
        event.time_until_start.return_value = 45
        
        result = self.renderer._format_time_until_rpi(event)
        
        assert "In 45 minutes" in result
        assert "time-until" in result
        assert "soon" not in result  # No soon class for >30 minutes
        assert "urgent" not in result  # No urgent class for >30 minutes
        assert "⏰" in result

    def test_format_time_until_rpi_far_future(self) -> None:
        """Test formatting time until start for far future events (>60 minutes)."""
        event = Mock(spec=CachedEvent)
        event.time_until_start.return_value = 120
        
        result = self.renderer._format_time_until_rpi(event)
        
        # Should return empty string for events >60 minutes away
        assert result == ""

    def test_format_time_until_rpi_none(self) -> None:
        """Test formatting time until start when time_until_start returns None."""
        event = Mock(spec=CachedEvent)
        event.time_until_start.return_value = None
        
        result = self.renderer._format_time_until_rpi(event)
        
        # Should return empty string when time_until_start is None
        assert result == ""

    def test_format_later_event_rpi(self) -> None:
        """Test formatting later event."""
        event = Mock(spec=CachedEvent)
        event.id = "event789"
        event.subject = "Weekly Review"
        event.location_display_name = "Room B"
        event.is_online_meeting = False
        event.format_time_range.return_value = "4:00 PM - 5:00 PM"
        
        # Mock the escape_html method
        with patch.object(self.renderer, "_escape_html", side_effect=lambda x: x):
            result = self.renderer._format_later_event_rpi(event)
        
        assert "Weekly Review" in result
        assert "4:00 PM - 5:00 PM" in result
        assert "📍 Room B" in result
        assert "later-event" in result
        assert 'data-event-id="event789"' in result
        assert "role=" in result  # Accessibility attributes
        assert "aria-label=" in result  # Accessibility label


class TestRPIHTMLRendererErrorHandling:
    """Test RPI HTML error handling methods."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.settings = Mock()
        self.settings.web_layout = "3x4"
        self.renderer = RaspberryPiHTMLRenderer(self.settings)

    @patch("calendarbot.display.rpi_html_renderer.datetime")
    def test_render_error_html_basic(self, mock_datetime: Any) -> None:
        """Test basic error rendering."""
        mock_now = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        result = self.renderer._render_error_html("Connection failed")
        
        assert "<!DOCTYPE html>" in result
        assert "Connection Issue" in result
        assert "Connection failed" in result
        assert "Friday, December 15" in result
        assert "⚠️" in result

    @patch("calendarbot.display.rpi_html_renderer.datetime")
    def test_render_error_html_with_cached_events(self, mock_datetime: Any) -> None:
        """Test error rendering with cached events."""
        mock_now = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        cached_event = Mock(spec=CachedEvent)
        cached_event.subject = "Cached Meeting"
        cached_event.location_display_name = "Room A"
        cached_event.format_time_range.return_value = "10:00 AM - 11:00 AM"
        
        # Mock the escape_html method
        with patch.object(self.renderer, "_escape_html", side_effect=lambda x: x):
            result = self.renderer._render_error_html("Network error", [cached_event])
        
        assert "Network error" in result
        assert "📱 Showing Cached Data" in result
        assert "Cached Meeting" in result
        assert "📍 Room A" in result

    @patch("calendarbot.display.rpi_html_renderer.datetime")
    def test_render_error_html_no_cached_data(self, mock_datetime: Any) -> None:
        """Test error rendering with no cached data."""
        mock_now = datetime(2023, 12, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        result = self.renderer._render_error_html("Service unavailable", None)
        
        assert "Service unavailable" in result
        assert "❌ No cached data available" in result

    def test_render_authentication_prompt(self) -> None:
        """Test authentication prompt rendering."""
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