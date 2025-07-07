"""Comprehensive unit tests for calendarbot.display.html_renderer module."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from calendarbot.cache.models import CachedEvent
from calendarbot.display.html_renderer import HTMLRenderer


class TestHTMLRenderer:
    """Test cases for HTMLRenderer class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings object."""
        settings = Mock()
        settings.web_theme = "eink"
        settings.display_type = "html"
        settings.display_enabled = True
        return settings

    @pytest.fixture
    def renderer(self, mock_settings):
        """Create HTMLRenderer instance with mock settings."""
        return HTMLRenderer(mock_settings)

    @pytest.fixture
    def mock_cached_event(self):
        """Create a mock CachedEvent for testing."""
        event = Mock(spec=CachedEvent)
        event.id = "test-event-1"
        event.subject = "Test Meeting"
        event.start_datetime = "2025-01-15T10:00:00Z"
        event.end_datetime = "2025-01-15T11:00:00Z"
        event.location_display_name = "Conference Room A"
        event.is_online_meeting = False
        event.is_current.return_value = False
        event.is_upcoming.return_value = True
        event.format_time_range.return_value = "10:00 AM - 11:00 AM"
        event.time_until_start.return_value = 30

        # Mock datetime properties
        start_dt = datetime(2025, 1, 15, 10, 0, 0)
        end_dt = datetime(2025, 1, 15, 11, 0, 0)
        event.start_dt = start_dt
        event.end_dt = end_dt

        return event

    @pytest.fixture
    def mock_current_event(self, mock_cached_event):
        """Create a mock current event."""
        event = mock_cached_event
        event.is_current.return_value = True
        event.is_upcoming.return_value = False
        event.time_until_start.return_value = None
        return event

    def test_init_default_theme(self, mock_settings):
        """Test HTMLRenderer initialization with default theme."""
        mock_settings.web_theme = "eink"

        with patch("calendarbot.display.html_renderer.logger") as mock_logger:
            renderer = HTMLRenderer(mock_settings)

            assert renderer.settings == mock_settings
            assert renderer.theme == "eink"
            mock_logger.info.assert_called_with("HTML renderer initialized with theme: eink")

    def test_init_no_theme_attribute(self, mock_settings):
        """Test HTMLRenderer initialization when settings has no web_theme attribute."""
        delattr(mock_settings, "web_theme")

        renderer = HTMLRenderer(mock_settings)

        assert renderer.theme == "eink"  # Default theme

    @pytest.mark.parametrize("theme", ["eink", "eink-rpi", "standard", "custom"])
    def test_init_various_themes(self, mock_settings, theme):
        """Test HTMLRenderer initialization with various themes."""
        mock_settings.web_theme = theme

        renderer = HTMLRenderer(mock_settings)

        assert renderer.theme == theme

    def test_render_events_empty_list(self, renderer):
        """Test rendering with empty events list."""
        with patch("calendarbot.display.html_renderer.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "Monday, January 15"

            result = renderer.render_events([])

            assert "No meetings scheduled!" in result
            assert "Enjoy your free time" in result
            assert "🎉" in result
            assert "no-events" in result

    def test_render_events_with_status_info(self, renderer, mock_cached_event):
        """Test rendering events with status information."""
        status_info = {
            "interactive_mode": False,
            "last_update": "2025-01-15T10:00:00Z",
            "is_cached": True,
            "connection_status": "Connected",
        }

        with patch("calendarbot.display.html_renderer.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "Monday, January 15"

            result = renderer.render_events([mock_cached_event], status_info)

            assert "Monday, January 15" in result
            assert "📱 Cached Data" in result
            assert "📶 Connected" in result

    def test_render_events_interactive_mode(self, renderer, mock_cached_event):
        """Test rendering events in interactive mode."""
        status_info = {
            "interactive_mode": True,
            "selected_date": "Tuesday, January 16",
            "relative_description": "Tomorrow",
        }

        result = renderer.render_events([mock_cached_event], status_info)

        assert "Tuesday, January 16" in result
        assert "navigate('prev')" in result
        assert "navigate('next')" in result
        assert "📍 Tomorrow" in result

    def test_render_events_exception_handling(self, renderer):
        """Test error handling in render_events method."""
        with patch.object(renderer, "_build_status_line", side_effect=Exception("Test error")):
            with patch("calendarbot.display.html_renderer.logger") as mock_logger:

                result = renderer.render_events([])

                assert "Error rendering calendar: Test error" in result
                mock_logger.error.assert_called_with("Failed to render events to HTML: Test error")

    def test_build_status_line_no_info(self, renderer):
        """Test building status line with no status info."""
        result = renderer._build_status_line(None)

        assert result == ""

    def test_build_status_line_empty_info(self, renderer):
        """Test building status line with empty status info."""
        result = renderer._build_status_line({})

        assert result == ""

    @patch("calendarbot.display.html_renderer.datetime")
    @patch("calendarbot.display.html_renderer.pytz")
    def test_build_status_line_with_update_time_string(self, mock_pytz, mock_datetime, renderer):
        """Test building status line with last update time as string."""
        # Mock datetime.fromisoformat to return a controlled datetime object
        mock_parsed_time = Mock()
        mock_parsed_time.tzinfo = None
        mock_datetime.fromisoformat.return_value = mock_parsed_time

        # Mock the timezone conversion chain
        mock_pacific_tz = Mock()
        mock_utc_time = Mock()
        mock_pacific_time = Mock()

        mock_pytz.timezone.return_value = mock_pacific_tz
        mock_pytz.utc.localize.return_value = mock_utc_time
        mock_utc_time.astimezone.return_value = mock_pacific_time
        mock_pacific_time.strftime.return_value = "02:00 PM"

        status_info = {
            "last_update": "2025-01-15T22:00:00Z",
            "is_cached": False,
            "connection_status": "Online",
        }

        result = renderer._build_status_line(status_info)

        assert "Updated: 02:00 PM" in result
        assert "🌐 Live Data" in result
        assert "📶 Online" in result

    @patch("calendarbot.display.html_renderer.pytz")
    def test_build_status_line_with_update_time_datetime(self, mock_pytz, renderer):
        """Test building status line with last update time as datetime object."""
        # Mock the timezone conversion chain properly
        mock_pacific_tz = Mock()
        mock_update_time = Mock()
        mock_utc_time = Mock()
        mock_pacific_time = Mock()

        mock_pytz.timezone.return_value = mock_pacific_tz
        mock_update_time.tzinfo = None
        mock_pytz.utc.localize.return_value = mock_utc_time
        mock_utc_time.astimezone.return_value = mock_pacific_time
        mock_pacific_time.strftime.return_value = "03:30 PM"

        status_info = {"last_update": mock_update_time, "is_cached": True}

        result = renderer._build_status_line(status_info)

        assert "Updated: 03:30 PM" in result
        assert "📱 Cached Data" in result

    def test_build_status_line_timezone_error(self, renderer):
        """Test building status line handles timezone conversion errors gracefully."""
        status_info = {"last_update": "invalid-datetime", "is_cached": False}

        result = renderer._build_status_line(status_info)

        # Should still include other status info despite timezone error
        assert "🌐 Live Data" in result
        assert "Updated:" not in result  # Update time should be skipped

    def test_render_events_content_no_events(self, renderer):
        """Test rendering events content with no events."""
        result = renderer._render_events_content([], False)

        assert "No meetings scheduled!" in result
        assert "no-events" in result
        assert "🎉" in result

    def test_render_events_content_current_events(self, renderer, mock_current_event):
        """Test rendering events content with current events."""
        result = renderer._render_events_content([mock_current_event], False)

        assert "▶ Current Event" in result
        assert "current-events" in result
        assert mock_current_event.subject in result

    def test_render_events_content_upcoming_events(self, renderer, mock_cached_event):
        """Test rendering events content with upcoming events."""
        result = renderer._render_events_content([mock_cached_event], False)

        assert "📋 Next Up" in result
        assert "upcoming-events" in result
        assert mock_cached_event.subject in result

    def test_render_events_content_later_events(self, renderer):
        """Test rendering events content with many upcoming events showing 'later' section."""
        # Create 6 upcoming events to trigger "later today" section
        upcoming_events = []
        for i in range(6):
            event = Mock(spec=CachedEvent)
            event.subject = f"Meeting {i+1}"
            event.location_display_name = None
            event.is_online_meeting = False
            event.is_current.return_value = False
            event.is_upcoming.return_value = True
            event.format_time_range.return_value = f"{10+i}:00 AM - {11+i}:00 AM"
            event.time_until_start.return_value = 30 + i * 10  # Return proper integer values
            upcoming_events.append(event)

        result = renderer._render_events_content(upcoming_events, False)

        assert "⏰ Later Today" in result
        assert "later-events" in result
        assert "Meeting 4" in result  # 4th event should be in later section

    def test_format_current_event_html(self, renderer, mock_current_event):
        """Test formatting current event HTML."""
        with patch("calendarbot.utils.helpers.get_timezone_aware_now") as mock_now:
            now = datetime(2025, 1, 15, 10, 30, 0)  # 30 minutes into the event
            mock_now.return_value = now

            result = renderer._format_current_event_html(mock_current_event)

            assert mock_current_event.subject in result
            assert "current-event" in result
            assert "⏱️ 30 minutes remaining" in result

    def test_format_current_event_with_location(self, renderer, mock_current_event):
        """Test formatting current event with location."""
        mock_current_event.location_display_name = "Conference Room B"

        result = renderer._format_current_event_html(mock_current_event)

        assert "📍 Conference Room B" in result
        assert "event-location" in result

    def test_format_current_event_online_meeting(self, renderer, mock_current_event):
        """Test formatting current event that's an online meeting."""
        mock_current_event.location_display_name = None
        mock_current_event.is_online_meeting = True

        result = renderer._format_current_event_html(mock_current_event)

        assert "💻 Online Meeting" in result
        assert "event-location online" in result

    def test_format_current_event_teams_filtering(self, renderer, mock_current_event):
        """Test filtering out Microsoft Teams Meeting text from location."""
        mock_current_event.location_display_name = "Microsoft Teams Meeting"
        mock_current_event.is_online_meeting = True

        result = renderer._format_current_event_html(mock_current_event)

        assert "💻 Online Meeting" in result
        assert "Microsoft Teams Meeting" not in result

    def test_format_upcoming_event_html(self, renderer, mock_cached_event):
        """Test formatting upcoming event HTML."""
        result = renderer._format_upcoming_event_html(mock_cached_event)

        assert mock_cached_event.subject in result
        assert "upcoming-event" in result
        assert "⏰ In 30 minutes" in result

    def test_format_upcoming_event_urgent_timing(self, renderer, mock_cached_event):
        """Test formatting upcoming event with urgent timing."""
        mock_cached_event.time_until_start.return_value = 3  # 3 minutes

        result = renderer._format_upcoming_event_html(mock_cached_event)

        assert "🔔 Starting in 3 minutes!" in result
        assert "time-until urgent" in result

    def test_format_upcoming_event_far_future(self, renderer, mock_cached_event):
        """Test formatting upcoming event far in the future."""
        mock_cached_event.time_until_start.return_value = 120  # 2 hours

        result = renderer._format_upcoming_event_html(mock_cached_event)

        # Should not show time until when > 60 minutes
        assert "time-until" not in result

    def test_render_navigation_help(self, renderer):
        """Test rendering navigation help."""
        status_info = {"relative_description": "Tomorrow"}

        result = renderer._render_navigation_help(status_info)

        assert "← →" in result
        assert "Navigate" in result
        assert "Space" in result
        assert "Today" in result
        assert "📍 Tomorrow" in result

    def test_render_navigation_help_today(self, renderer):
        """Test rendering navigation help for today."""
        status_info = {"relative_description": "Today"}

        result = renderer._render_navigation_help(status_info)

        # Should not show relative date for "Today"
        assert "📍 Today" not in result
        assert "Navigate" in result

    @pytest.mark.parametrize(
        "theme,expected_css",
        [
            ("eink", "style.css"),
            ("eink-rpi", "eink-rpi.css"),
            ("standard", "standard.css"),
            ("unknown", "style.css"),
        ],
    )
    def test_get_theme_css_file(self, mock_settings, theme, expected_css):
        """Test getting CSS file for different themes."""
        mock_settings.web_theme = theme
        renderer = HTMLRenderer(mock_settings)

        result = renderer._get_theme_css_file()

        assert result == expected_css

    @pytest.mark.parametrize(
        "theme,expected_js",
        [
            ("eink", "app.js"),
            ("eink-rpi", "eink-rpi.js"),
            ("standard", "standard.js"),
            ("unknown", "app.js"),
        ],
    )
    def test_get_theme_js_file(self, mock_settings, theme, expected_js):
        """Test getting JavaScript file for different themes."""
        mock_settings.web_theme = theme
        renderer = HTMLRenderer(mock_settings)

        result = renderer._get_theme_js_file()

        assert result == expected_js

    @pytest.mark.parametrize(
        "theme,expected_icon",
        [("eink", "🎨"), ("eink-rpi", "⚫"), ("standard", "⚫"), ("other", "⚫")],
    )
    def test_get_theme_icon(self, mock_settings, theme, expected_icon):
        """Test getting theme icon for different themes."""
        mock_settings.web_theme = theme
        renderer = HTMLRenderer(mock_settings)

        result = renderer._get_theme_icon()

        assert result == expected_icon

    def test_build_html_template_interactive(self, renderer):
        """Test building HTML template in interactive mode."""
        result = renderer._build_html_template(
            display_date="Monday, January 15",
            status_line="Status info",
            events_content="<div>Events</div>",
            nav_help="<div>Navigation</div>",
            interactive_mode=True,
        )

        assert "navigate('prev')" in result
        assert "navigate('next')" in result
        assert "Monday, January 15" in result
        assert "Status info" in result
        assert "<div>Events</div>" in result
        assert "<div>Navigation</div>" in result
        assert "theme-eink" in result

    def test_build_html_template_non_interactive(self, renderer):
        """Test building HTML template in non-interactive mode."""
        result = renderer._build_html_template(
            display_date="Monday, January 15",
            status_line="Status info",
            events_content="<div>Events</div>",
            nav_help="",
            interactive_mode=False,
        )

        assert "navigate('prev')" not in result
        assert "navigate('next')" not in result
        assert "Monday, January 15" in result
        assert "nav-arrow-left" in result  # Static arrows present
        assert "nav-arrow-right" in result

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Hello World", "Hello World"),
            ("", ""),
            (None, ""),
            ("Hello & World", "Hello &amp; World"),
            (
                "<script>alert('xss')</script>",
                "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;",
            ),
            ('Hello "quoted" text', "Hello &quot;quoted&quot; text"),
            ("Hello > World < Test", "Hello &gt; World &lt; Test"),
        ],
    )
    def test_escape_html(self, renderer, text, expected):
        """Test HTML escaping functionality."""
        result = renderer._escape_html(text)

        assert result == expected

    def test_render_error_success(self, renderer):
        """Test successful error rendering."""
        result = renderer.render_error("Connection failed")

        assert "Connection Issue" in result
        assert "Connection failed" in result
        assert "⚠️" in result

    def test_render_error_with_cached_events(self, renderer, mock_cached_event):
        """Test error rendering with cached events."""
        result = renderer.render_error("Network error", [mock_cached_event])

        assert "Network error" in result
        assert "📱 Showing Cached Data" in result
        assert mock_cached_event.subject in result

    def test_render_error_exception_handling(self, renderer):
        """Test error rendering handles exceptions gracefully."""
        with patch.object(renderer, "_render_error_html", side_effect=Exception("Render error")):
            with patch("calendarbot.display.html_renderer.logger") as mock_logger:

                result = renderer.render_error("Original error")

                assert "Critical Error" in result
                assert "Render error" in result
                mock_logger.error.assert_called_with("Failed to render error HTML: Render error")

    def test_render_error_html_no_cached(self, renderer):
        """Test rendering error HTML without cached events."""
        result = renderer._render_error_html("Test error")

        assert "Test error" in result
        assert "❌ No cached data available" in result
        assert "Connection Issue" in result

    def test_render_error_html_with_cached(self, renderer, mock_cached_event):
        """Test rendering error HTML with cached events."""
        mock_cached_event.location_display_name = "Meeting Room"

        result = renderer._render_error_html("Test error", [mock_cached_event])

        assert "Test error" in result
        assert "📱 Showing Cached Data" in result
        assert mock_cached_event.subject in result
        assert "📍 Meeting Room" in result

    def test_render_authentication_prompt(self, renderer):
        """Test rendering authentication prompt."""
        verification_uri = "https://microsoft.com/devicelogin"
        user_code = "ABC123DEF"

        result = renderer.render_authentication_prompt(verification_uri, user_code)

        assert verification_uri in result
        assert user_code in result
        assert "🔐 Authentication Required" in result
        assert "Microsoft 365 Authentication" in result
        assert "Visit:" in result
        assert "Enter code:" in result
        assert "Waiting for authentication..." in result

    def test_location_filtering_in_events(self, renderer):
        """Test that Microsoft Teams Meeting location text is filtered out consistently."""
        # Test current event
        current_event = Mock(spec=CachedEvent)
        current_event.subject = "Teams Meeting"
        current_event.location_display_name = "Microsoft Teams Meeting"
        current_event.is_online_meeting = True
        current_event.is_current.return_value = True
        current_event.is_upcoming.return_value = False
        current_event.format_time_range.return_value = "10:00 AM - 11:00 AM"
        current_event.start_dt = datetime(2025, 1, 15, 10, 0, 0)
        current_event.end_dt = datetime(2025, 1, 15, 11, 0, 0)

        # Test upcoming event
        upcoming_event = Mock(spec=CachedEvent)
        upcoming_event.subject = "Another Teams Meeting"
        upcoming_event.location_display_name = "Microsoft Teams Meeting"
        upcoming_event.is_online_meeting = True
        upcoming_event.is_current.return_value = False
        upcoming_event.is_upcoming.return_value = True
        upcoming_event.format_time_range.return_value = "11:00 AM - 12:00 PM"
        upcoming_event.time_until_start.return_value = 30

        result = renderer._render_events_content([current_event, upcoming_event], False)

        # Should show "Online Meeting" instead of "Microsoft Teams Meeting"
        assert "💻 Online Meeting" in result or "💻 Online" in result
        assert "Microsoft Teams Meeting" not in result

    def test_event_duration_calculation(self, renderer, mock_current_event):
        """Test event duration calculation in current event formatting."""
        # Set up a 90-minute meeting
        mock_current_event.start_dt = datetime(2025, 1, 15, 10, 0, 0)
        mock_current_event.end_dt = datetime(2025, 1, 15, 11, 30, 0)

        result = renderer._format_current_event_html(mock_current_event)

        assert "(90min)" in result

    def test_time_remaining_calculation_error_handling(self, renderer, mock_current_event):
        """Test time remaining calculation handles import errors gracefully."""
        with patch(
            "calendarbot.utils.helpers.get_timezone_aware_now",
            side_effect=ImportError("Module not found"),
        ):

            result = renderer._format_current_event_html(mock_current_event)

            # Should still render without time remaining section
            assert mock_current_event.subject in result
            assert "minutes remaining" not in result

    @patch("calendarbot.display.html_renderer.datetime")
    def test_render_events_date_formatting(self, mock_datetime, renderer, mock_cached_event):
        """Test that render_events properly formats the display date."""
        mock_datetime.now.return_value.strftime.return_value = "Wednesday, January 17"

        result = renderer.render_events([mock_cached_event])

        assert "Wednesday, January 17" in result
        mock_datetime.now.return_value.strftime.assert_called_with("%A, %B %d")

    def test_comprehensive_html_structure(self, renderer, mock_cached_event, mock_current_event):
        """Test that rendered HTML has proper structure and includes all necessary elements."""
        events = [mock_current_event, mock_cached_event]
        status_info = {
            "interactive_mode": True,
            "selected_date": "Monday, January 15",
            "last_update": "2025-01-15T10:00:00Z",
            "is_cached": False,
            "relative_description": "Today",
        }

        result = renderer.render_events(events, status_info)

        # Check HTML structure
        assert "<!DOCTYPE html>" in result
        assert '<html lang="en"' in result
        assert "<head>" in result and "</head>" in result
        assert "<body>" in result and "</body>" in result
        assert "<header" in result and "</header>" in result
        assert "<main" in result and "</main>" in result
        assert "<footer" in result and "</footer>" in result

        # Check CSS and JS includes
        assert "/static/style.css" in result
        assert "/static/app.js" in result

        # Check interactive elements
        assert "navigate('prev')" in result
        assert "navigate('next')" in result


class TestHTMLRendererIntegration:
    """Integration tests for HTMLRenderer with real-like data."""

    @pytest.fixture
    def realistic_settings(self):
        """Create realistic settings object."""
        settings = Mock()
        settings.web_theme = "eink-rpi"
        settings.display_type = "html"
        settings.display_enabled = True
        return settings

    @pytest.fixture
    def realistic_events(self):
        """Create realistic event data for integration testing."""
        events = []

        # Current meeting
        current = Mock(spec=CachedEvent)
        current.subject = "Weekly Team Standup"
        current.location_display_name = "Conference Room Alpha"
        current.is_online_meeting = False
        current.is_current.return_value = True
        current.is_upcoming.return_value = False
        current.format_time_range.return_value = "9:00 AM - 9:30 AM"
        current.start_dt = datetime(2025, 1, 15, 9, 0, 0)
        current.end_dt = datetime(2025, 1, 15, 9, 30, 0)
        events.append(current)

        # Upcoming meetings
        upcoming1 = Mock(spec=CachedEvent)
        upcoming1.subject = "Product Planning Meeting"
        upcoming1.location_display_name = None
        upcoming1.is_online_meeting = True
        upcoming1.is_current.return_value = False
        upcoming1.is_upcoming.return_value = True
        upcoming1.format_time_range.return_value = "10:00 AM - 11:00 AM"
        upcoming1.time_until_start.return_value = 45
        events.append(upcoming1)

        upcoming2 = Mock(spec=CachedEvent)
        upcoming2.subject = "Client Demo"
        upcoming2.location_display_name = "Microsoft Teams Meeting"
        upcoming2.is_online_meeting = True
        upcoming2.is_current.return_value = False
        upcoming2.is_upcoming.return_value = True
        upcoming2.format_time_range.return_value = "2:00 PM - 3:00 PM"
        upcoming2.time_until_start.return_value = 240
        events.append(upcoming2)

        return events

    def test_full_page_rendering_interactive(self, realistic_settings, realistic_events):
        """Test full page rendering in interactive mode with realistic data."""
        renderer = HTMLRenderer(realistic_settings)

        status_info = {
            "interactive_mode": True,
            "selected_date": "Monday, January 15, 2025",
            "last_update": "2025-01-15T14:30:00Z",
            "is_cached": False,
            "connection_status": "Connected",
            "relative_description": "Today",
        }

        result = renderer.render_events(realistic_events, status_info)

        # Verify all major sections are present
        assert "Weekly Team Standup" in result
        assert "Product Planning Meeting" in result
        assert "Client Demo" in result
        assert "▶ Current Event" in result
        assert "📋 Next Up" in result
        assert "🌐 Live Data" in result
        assert "📶 Connected" in result
        assert "theme-eink-rpi" in result

        # Verify interactive elements
        assert "navigate('prev')" in result
        assert "navigate('next')" in result
        assert "← →" in result
        assert "Navigate" in result

    def test_error_page_with_cached_data(self, realistic_settings, realistic_events):
        """Test error page rendering with cached events."""
        renderer = HTMLRenderer(realistic_settings)

        result = renderer.render_error("Unable to connect to Microsoft Graph API", realistic_events)

        assert "Connection Issue" in result
        assert "Unable to connect to Microsoft Graph API" in result
        assert "📱 Showing Cached Data" in result
        assert "Weekly Team Standup" in result
        assert "Product Planning Meeting" in result

    def test_authentication_flow_page(self, realistic_settings):
        """Test authentication prompt page rendering."""
        renderer = HTMLRenderer(realistic_settings)

        result = renderer.render_authentication_prompt(
            "https://microsoft.com/devicelogin", "ABCD1234"
        )

        assert "🔐 Authentication Required" in result
        assert "Microsoft 365 Authentication" in result
        assert "https://microsoft.com/devicelogin" in result
        assert "ABCD1234" in result
        assert 'target="_blank"' in result  # Opens in new tab
        assert "Waiting for authentication..." in result
        assert "⏳" in result
