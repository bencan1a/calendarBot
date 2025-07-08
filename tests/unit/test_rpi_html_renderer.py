"""Comprehensive unit tests for calendarbot.display.rpi_html_renderer module."""

import logging
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from calendarbot.cache.models import CachedEvent
from calendarbot.display.rpi_html_renderer import RaspberryPiHTMLRenderer


class TestRPiHTMLRenderer:
    """Test Raspberry Pi E-ink HTML renderer functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings object for RPI renderer."""
        settings = Mock()
        settings.web_theme = "eink-rpi"  # Should be overridden to "eink"
        settings.display_type = "rpi"
        settings.display_enabled = True
        return settings

    @pytest.fixture
    def rpi_renderer(self, mock_settings):
        """Create RaspberryPiHTMLRenderer instance with mock settings."""
        return RaspberryPiHTMLRenderer(mock_settings)

    @pytest.fixture
    def mock_cached_event(self):
        """Create a mock CachedEvent for testing."""
        event = Mock(spec=CachedEvent)
        event.id = "rpi-test-event-1"
        event.subject = "RPI Test Meeting"
        event.start_datetime = "2025-01-15T10:00:00Z"
        event.end_datetime = "2025-01-15T11:00:00Z"
        event.location_display_name = "Conference Room Alpha"
        event.is_online_meeting = False
        event.is_current.return_value = False
        event.is_upcoming.return_value = True
        event.format_time_range.return_value = "10:00 AM - 11:00 AM"
        event.time_until_start.return_value = 45

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

    @pytest.fixture
    def mock_online_event(self, mock_cached_event):
        """Create a mock online meeting event."""
        event = mock_cached_event
        event.location_display_name = None
        event.is_online_meeting = True
        return event

    def test_init_sets_eink_theme(self, mock_settings):
        """Test RPI renderer initialization sets 'eink' theme regardless of settings."""
        mock_settings.web_theme = "standard"  # Different theme in settings

        with patch("calendarbot.display.rpi_html_renderer.logger") as mock_logger:
            renderer = RaspberryPiHTMLRenderer(mock_settings)

            assert renderer.settings == mock_settings
            assert renderer.theme == "eink"  # Should be overridden
            mock_logger.debug.assert_called_with(
                "RPI HTML renderer initialized for 800x480px e-ink display with 'eink' theme"
            )

    def test_init_inherits_from_base_renderer(self, mock_settings):
        """Test RPI renderer properly inherits from HTMLRenderer."""
        renderer = RaspberryPiHTMLRenderer(mock_settings)

        # Should have HTMLRenderer methods
        assert hasattr(renderer, "_escape_html")
        assert hasattr(renderer, "render_events")
        assert hasattr(renderer, "render_error")

    def test_build_html_template_interactive_mode(self, rpi_renderer):
        """Test HTML template generation in interactive mode."""
        result = rpi_renderer._build_html_template(
            display_date="Monday, January 15",
            status_line="Test status",
            events_content="<div>Test events</div>",
            nav_help="<div>Navigation help</div>",  # Unused in RPI layout
            interactive_mode=True,
        )

        # Check RPI-specific structure
        assert "<!DOCTYPE html>" in result
        assert 'class="theme-eink"' in result
        assert "width=800, height=480" in result
        assert "📅 Calendar Bot - Monday, January 15" in result
        assert "/static/eink-rpi.css" in result
        assert "/static/eink-rpi.js" in result

        # Check interactive navigation
        assert 'data-action="prev"' in result
        assert 'data-action="next"' in result
        assert "←" in result and "→" in result

        # Check grid layout structure
        assert 'class="calendar-container"' in result
        assert 'class="calendar-header"' in result
        assert 'class="calendar-content"' in result
        assert 'class="calendar-status"' in result

    def test_build_html_template_non_interactive_mode(self, rpi_renderer):
        """Test HTML template generation in non-interactive mode."""
        result = rpi_renderer._build_html_template(
            display_date="Monday, January 15",
            status_line="Test status",
            events_content="<div>Test events</div>",
            nav_help="",
            interactive_mode=False,
        )

        # Should not have interactive navigation
        assert 'data-action="prev"' not in result
        assert 'data-action="next"' not in result
        assert "<button" not in result

        # But should still have arrow placeholders
        assert "nav-arrow-left" in result
        assert "nav-arrow-right" in result

    def test_build_html_template_debug_logging(self, rpi_renderer):
        """Test HTML template logs debug information."""
        with patch("calendarbot.display.rpi_html_renderer.logger") as mock_logger:
            rpi_renderer._build_html_template(
                display_date="Test Date",
                status_line="",
                events_content="",
                nav_help="",
                interactive_mode=True,
            )

            # Check debug logging calls
            mock_logger.debug.assert_any_call("RPI HTML Template - interactive_mode: True")
            mock_logger.debug.assert_any_call("RPI HTML Template - display_date: Test Date")
            mock_logger.debug.assert_any_call(
                "RPI HTML Template - viewport will be: width=800, height=480 (ISSUE: should be 480x800 for portrait)"
            )

    def test_generate_header_navigation_interactive(self, rpi_renderer):
        """Test header navigation generation in interactive mode."""
        result = rpi_renderer._generate_header_navigation_with_date(
            "Tuesday, January 16", interactive_mode=True
        )

        assert 'role="toolbar"' in result
        assert 'aria-label="Date Navigation"' in result
        assert "Navigate to previous day" in result
        assert "Navigate to next day" in result
        assert "Tuesday, January 16" in result
        assert "nav-arrow-left" in result
        assert "nav-arrow-right" in result

    def test_generate_header_navigation_non_interactive(self, rpi_renderer):
        """Test header navigation generation in non-interactive mode."""
        result = rpi_renderer._generate_header_navigation_with_date(
            "Tuesday, January 16", interactive_mode=False
        )

        assert 'role="toolbar"' not in result
        assert "<button" not in result
        assert "Tuesday, January 16" in result
        assert "nav-arrow-left" in result
        assert "nav-arrow-right" in result

    def test_generate_bottom_status_bar(self, rpi_renderer):
        """Test bottom status bar generation."""
        with patch.object(
            rpi_renderer, "_render_status_line_html", return_value="<span>Status</span>"
        ):
            result = rpi_renderer._generate_bottom_status_bar("Test status")

            assert 'id="status"' in result
            assert 'class="calendar-status"' in result
            assert 'role="status"' in result
            assert 'aria-label="Calendar Status"' in result
            assert "<span>Status</span>" in result

    def test_generate_theme_toggle(self, rpi_renderer):
        """Test theme toggle button generation."""
        result = rpi_renderer._generate_theme_toggle()

        assert 'class="theme-controls"' in result
        assert 'role="toolbar"' in result
        assert 'aria-label="Theme Controls"' in result
        assert 'class="theme-toggle"' in result
        assert 'data-action="theme"' in result
        assert "🎨" in result

    def test_render_status_line_html_with_content(self, rpi_renderer):
        """Test status line rendering with content."""
        result = rpi_renderer._render_status_line_html("Test status content")

        assert 'class="status-line"' in result
        assert "Test status content" in result

    def test_render_status_line_html_empty(self, rpi_renderer):
        """Test status line rendering with empty content."""
        result = rpi_renderer._render_status_line_html("")
        assert result == ""

        result = rpi_renderer._render_status_line_html(None)
        assert result == ""

    def test_render_events_content_no_events(self, rpi_renderer):
        """Test events content rendering with no events."""
        result = rpi_renderer._render_events_content([], interactive_mode=False)

        assert "no-events" in result
        assert 'role="region"' in result
        assert 'aria-label="No Events Today"' in result
        assert "🎉" in result
        assert "No meetings scheduled!" in result
        assert "Enjoy your free time." in result

    def test_render_events_content_current_events(self, rpi_renderer, mock_current_event):
        """Test events content rendering with current events."""
        result = rpi_renderer._render_events_content([mock_current_event], interactive_mode=False)

        assert "section-current" in result
        assert 'aria-labelledby="current-heading"' in result
        assert "▶ Current Event" in result
        assert mock_current_event.subject in result

    def test_render_events_content_upcoming_events(self, rpi_renderer, mock_cached_event):
        """Test events content rendering with upcoming events."""
        # Create multiple upcoming events
        events = [mock_cached_event]
        for i in range(2):
            event = Mock(spec=CachedEvent)
            event.id = f"upcoming-test-{i+2}"
            event.subject = f"Meeting {i+2}"
            event.location_display_name = None
            event.is_online_meeting = False
            event.is_current.return_value = False
            event.is_upcoming.return_value = True
            event.format_time_range.return_value = f"{11+i}:00 AM - {12+i}:00 PM"
            event.time_until_start.return_value = 60 + (i * 30)
            events.append(event)

        result = rpi_renderer._render_events_content(events, interactive_mode=False)

        assert "section-upcoming" in result
        assert 'aria-labelledby="upcoming-heading"' in result
        assert "📋 Next Up" in result

    def test_render_events_content_later_events(self, rpi_renderer):
        """Test events content rendering with later events section."""
        # Create enough events to trigger "later today" section
        events = []
        for i in range(7):
            event = Mock(spec=CachedEvent)
            event.id = f"later-test-{i+1}"
            event.subject = f"Meeting {i+1}"
            event.location_display_name = None if i % 2 else f"Room {i}"
            event.is_online_meeting = i % 2 == 0
            event.is_current.return_value = False
            event.is_upcoming.return_value = True
            event.format_time_range.return_value = f"{11+i}:00 AM - {12+i}:00 PM"
            event.time_until_start.return_value = 60 + (i * 30)
            events.append(event)

        result = rpi_renderer._render_events_content(events, interactive_mode=False)

        assert "section-later" in result
        assert 'aria-labelledby="later-heading"' in result
        assert "⏰ Later Today" in result
        assert "later-events-list" in result

    def test_render_no_events_rpi(self, rpi_renderer):
        """Test no events state rendering for RPI."""
        result = rpi_renderer._render_no_events_rpi()

        assert "no-events" in result
        assert 'role="region"' in result
        assert 'aria-label="No Events Today"' in result
        assert "🎉" in result
        assert "No meetings scheduled!" in result

    def test_render_current_events_section_rpi(self, rpi_renderer, mock_current_event):
        """Test current events section rendering."""
        result = rpi_renderer._render_current_events_section_rpi([mock_current_event])

        assert 'class="section-current"' in result
        assert 'role="region"' in result
        assert 'id="current-heading"' in result
        assert "▶ Current Event" in result

    def test_render_next_up_events_section_rpi(self, rpi_renderer, mock_cached_event):
        """Test Next Up events section rendering."""
        events = [mock_cached_event]
        result = rpi_renderer._render_next_up_events_section_rpi(events)

        assert 'class="section-upcoming"' in result
        assert 'role="region"' in result
        assert 'id="upcoming-heading"' in result
        assert "📋 Next Up" in result

    def test_render_later_today_section_rpi(self, rpi_renderer, mock_cached_event):
        """Test Later Today section rendering."""
        events = [mock_cached_event]
        result = rpi_renderer._render_later_today_section_rpi(events)

        assert 'class="section-later"' in result
        assert 'role="region"' in result
        assert 'id="later-heading"' in result
        assert "⏰ Later Today" in result
        assert 'role="list"' in result

    def test_format_current_event_rpi(self, rpi_renderer, mock_current_event):
        """Test current event formatting with Phase 3 architecture."""
        with patch("calendarbot.utils.helpers.get_timezone_aware_now") as mock_now:
            now = datetime(2025, 1, 15, 10, 30, 0)  # 30 minutes into event
            mock_now.return_value = now

            result = rpi_renderer._format_current_event_rpi(mock_current_event)

            assert 'class="current-event card-current event-current"' in result
            assert f'data-event-id="{mock_current_event.id}"' in result
            assert 'role="article"' in result
            assert f"▶ {mock_current_event.subject}" in result
            assert "(60min)" in result  # Duration calculation
            assert "⏱️ 30 minutes remaining" in result

    def test_format_current_event_rpi_with_location(self, rpi_renderer, mock_current_event):
        """Test current event formatting with location."""
        result = rpi_renderer._format_current_event_rpi(mock_current_event)

        assert "📍 Conference Room Alpha" in result
        assert "location-physical" in result

    def test_format_current_event_rpi_online_meeting(self, rpi_renderer, mock_online_event):
        """Test current event formatting for online meetings."""
        mock_online_event.is_current.return_value = True
        mock_online_event.is_upcoming.return_value = False

        result = rpi_renderer._format_current_event_rpi(mock_online_event)

        assert "💻 Online Meeting" in result
        assert "location-online" in result

    def test_format_upcoming_event_rpi(self, rpi_renderer, mock_cached_event):
        """Test upcoming event formatting with Phase 3 architecture."""
        result = rpi_renderer._format_upcoming_event_rpi(mock_cached_event)

        assert 'class="upcoming-event card-upcoming event-upcoming' in result
        assert f'data-event-id="{mock_cached_event.id}"' in result
        assert 'role="article"' in result
        assert f"📋 {mock_cached_event.subject}" in result
        assert "⏰ In 45 minutes" in result

    def test_format_upcoming_event_rpi_urgent_timing(self, rpi_renderer, mock_cached_event):
        """Test upcoming event formatting with urgent timing."""
        mock_cached_event.time_until_start.return_value = 3  # 3 minutes

        result = rpi_renderer._format_upcoming_event_rpi(mock_cached_event)

        assert "event-urgent" in result
        assert "🔔 Starting in 3 minutes!" in result
        assert "time-until urgent" in result

    def test_format_upcoming_event_rpi_soon_timing(self, rpi_renderer, mock_cached_event):
        """Test upcoming event formatting with soon timing."""
        mock_cached_event.time_until_start.return_value = 20  # 20 minutes

        result = rpi_renderer._format_upcoming_event_rpi(mock_cached_event)

        assert "event-soon" in result
        assert "⏰ In 20 minutes" in result
        assert "time-until soon" in result

    def test_format_upcoming_event_rpi_teams_filtering(self, rpi_renderer, mock_cached_event):
        """Test filtering out Microsoft Teams Meeting text from upcoming events."""
        mock_cached_event.location_display_name = "Microsoft Teams Meeting"
        mock_cached_event.is_online_meeting = True

        result = rpi_renderer._format_upcoming_event_rpi(mock_cached_event)

        assert "💻 Online" in result
        assert "Microsoft Teams Meeting" not in result

    def test_format_event_location_rpi_physical(self, rpi_renderer, mock_cached_event):
        """Test event location formatting for physical locations."""
        result = rpi_renderer._format_event_location_rpi(mock_cached_event)

        assert "location-physical" in result
        assert "📍 Conference Room Alpha" in result

    def test_format_event_location_rpi_online(self, rpi_renderer, mock_online_event):
        """Test event location formatting for online meetings."""
        result = rpi_renderer._format_event_location_rpi(mock_online_event)

        assert "location-online" in result
        assert "💻 Online Meeting" in result

    def test_format_event_location_rpi_teams_filtering(self, rpi_renderer, mock_cached_event):
        """Test filtering Microsoft Teams Meeting text from location."""
        mock_cached_event.location_display_name = "Microsoft Teams Meeting"
        mock_cached_event.is_online_meeting = True

        result = rpi_renderer._format_event_location_rpi(mock_cached_event)

        assert result == ""  # Should return empty for Teams meeting text

    def test_format_time_remaining_rpi(self, rpi_renderer, mock_current_event):
        """Test time remaining formatting for current events."""
        with patch("calendarbot.utils.helpers.get_timezone_aware_now") as mock_now:
            now = datetime(2025, 1, 15, 10, 45, 0)  # 15 minutes left
            mock_now.return_value = now

            result = rpi_renderer._format_time_remaining_rpi(mock_current_event)

            assert "⏱️ 15 minutes remaining" in result
            assert "time-remaining" in result

    def test_format_time_remaining_rpi_urgent(self, rpi_renderer, mock_current_event):
        """Test time remaining formatting with urgent styling."""
        with patch("calendarbot.utils.helpers.get_timezone_aware_now") as mock_now:
            now = datetime(2025, 1, 15, 10, 57, 0)  # 3 minutes left
            mock_now.return_value = now

            result = rpi_renderer._format_time_remaining_rpi(mock_current_event)

            assert "⏱️ 3 minutes remaining" in result
            assert "time-remaining urgent" in result

    def test_format_time_remaining_rpi_error_handling(self, rpi_renderer, mock_current_event):
        """Test time remaining handles import errors gracefully."""
        with patch(
            "calendarbot.utils.helpers.get_timezone_aware_now", side_effect=ImportError("No module")
        ):
            result = rpi_renderer._format_time_remaining_rpi(mock_current_event)
            assert result == ""

    def test_format_time_until_rpi(self, rpi_renderer, mock_cached_event):
        """Test time until start formatting for upcoming events."""
        result = rpi_renderer._format_time_until_rpi(mock_cached_event)

        assert "⏰ In 45 minutes" in result
        assert "time-until" in result

    @pytest.mark.parametrize(
        "minutes,expected_class,expected_icon",
        [
            (3, "urgent", "🔔"),
            (20, "soon", "⏰"),
            (45, "", "⏰"),
            (70, "", ""),  # Over 60 minutes, no display
        ],
    )
    def test_format_time_until_rpi_priority_indicators(
        self, rpi_renderer, mock_cached_event, minutes, expected_class, expected_icon
    ):
        """Test time until formatting with different priority indicators."""
        mock_cached_event.time_until_start.return_value = minutes

        result = rpi_renderer._format_time_until_rpi(mock_cached_event)

        if minutes > 60:
            assert result == ""
        else:
            if expected_class:
                assert f"time-until {expected_class}" in result
            assert expected_icon in result

    def test_format_later_event_rpi(self, rpi_renderer, mock_cached_event):
        """Test later event formatting with Phase 3 compact list format."""
        result = rpi_renderer._format_later_event_rpi(mock_cached_event)

        assert 'class="later-event"' in result
        assert f'data-event-id="{mock_cached_event.id}"' in result
        assert 'role="listitem"' in result
        assert f'aria-label="Later Event: {mock_cached_event.subject}"' in result
        assert "📍 Conference Room Alpha" in result

    def test_format_later_event_rpi_online(self, rpi_renderer, mock_online_event):
        """Test later event formatting for online meetings."""
        result = rpi_renderer._format_later_event_rpi(mock_online_event)

        assert "💻 Online" in result
        assert "Microsoft Teams Meeting" not in result

    def test_render_error_html_no_cached_events(self, rpi_renderer):
        """Test error HTML rendering without cached events."""
        result = rpi_renderer._render_error_html("Connection failed")

        assert "<!DOCTYPE html>" in result
        assert 'class="theme-eink"' in result
        assert "Connection Issue" in result
        assert "Connection failed" in result
        assert "⚠️" in result
        assert "❌ No cached data available" in result

    def test_render_error_html_with_cached_events(self, rpi_renderer, mock_cached_event):
        """Test error HTML rendering with cached events."""
        cached_events = [mock_cached_event]

        result = rpi_renderer._render_error_html("Network error", cached_events)

        assert "Network error" in result
        assert "📱 Showing Cached Data" in result
        assert mock_cached_event.subject in result
        assert "📍 Conference Room Alpha" in result

    def test_render_error_html_rpi_viewport(self, rpi_renderer):
        """Test error HTML uses correct RPI viewport dimensions."""
        result = rpi_renderer._render_error_html("Test error")

        # Note: Error template uses portrait mode (480x800)
        assert "width=480, height=800" in result

    def test_render_authentication_prompt_complete_structure(self, rpi_renderer):
        """Test authentication prompt renders complete RPI structure."""
        verification_uri = "https://microsoft.com/devicelogin"
        user_code = "ABC123DEF"

        result = rpi_renderer.render_authentication_prompt(verification_uri, user_code)

        # Check HTML structure
        assert "<!DOCTYPE html>" in result
        assert 'class="theme-eink"' in result
        assert "width=800, height=480" in result

        # Check content
        assert "🔐 Authentication Required" in result
        assert "Microsoft 365 Authentication" in result
        assert verification_uri in result
        assert user_code in result
        assert 'target="_blank"' in result
        assert "Waiting for authentication..." in result
        assert "⏳" in result

    def test_comprehensive_html_structure_validation(self, rpi_renderer):
        """Test complete HTML structure includes all RPI-specific elements."""
        # Create separate mock objects to avoid fixture conflicts
        current_event = Mock(spec=CachedEvent)
        current_event.id = "current-test-event"
        current_event.subject = "Current Meeting"
        current_event.location_display_name = "Conference Room A"
        current_event.is_online_meeting = False
        current_event.is_current.return_value = True
        current_event.is_upcoming.return_value = False
        current_event.format_time_range.return_value = "10:00 AM - 11:00 AM"
        current_event.start_dt = datetime(2025, 1, 15, 10, 0, 0)
        current_event.end_dt = datetime(2025, 1, 15, 11, 0, 0)

        upcoming_event = Mock(spec=CachedEvent)
        upcoming_event.id = "upcoming-test-event"
        upcoming_event.subject = "Upcoming Meeting"
        upcoming_event.location_display_name = "Conference Room B"
        upcoming_event.is_online_meeting = False
        upcoming_event.is_current.return_value = False
        upcoming_event.is_upcoming.return_value = True
        upcoming_event.format_time_range.return_value = "11:00 AM - 12:00 PM"
        upcoming_event.time_until_start.return_value = 60

        events = [current_event, upcoming_event]

        with patch("calendarbot.display.rpi_html_renderer.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "Monday, January 15"

            result = rpi_renderer.render_events(events)

            # Check RPI-specific structure
            assert "<!DOCTYPE html>" in result
            assert 'class="theme-eink"' in result
            assert "width=800, height=480" in result
            assert "/static/eink-rpi.css" in result
            assert "/static/eink-rpi.js" in result

            # Check grid layout
            assert 'class="calendar-container"' in result
            assert 'class="calendar-header"' in result
            assert 'class="calendar-content"' in result
            assert 'class="calendar-status"' in result

            # Check Phase 3 content sections
            assert "▶ Current Event" in result
            assert "📋 Next Up" in result

    def test_html_escaping_security(self, rpi_renderer):
        """Test HTML escaping in RPI renderer for security."""
        malicious_event = Mock(spec=CachedEvent)
        malicious_event.id = "evil-event"
        malicious_event.subject = "<script>alert('xss')</script>"
        malicious_event.location_display_name = "Room<img src=x onerror=alert(1)>"
        malicious_event.is_current.return_value = True
        malicious_event.is_upcoming.return_value = False
        malicious_event.is_online_meeting = False
        malicious_event.format_time_range.return_value = "10:00 AM - 11:00 AM"
        malicious_event.start_dt = datetime(2025, 1, 15, 10, 0, 0)
        malicious_event.end_dt = datetime(2025, 1, 15, 11, 0, 0)

        result = rpi_renderer._format_current_event_rpi(malicious_event)

        # Check that HTML is properly escaped
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        # Note: HTML escaping may result in onerror= still being visible but safely escaped
        assert "&lt;img" in result  # Image tag should be escaped
        assert "&gt;" in result

    @pytest.mark.parametrize("interactive_mode", [True, False])
    def test_render_events_interactive_mode_handling(
        self, rpi_renderer, mock_cached_event, interactive_mode
    ):
        """Test render_events handles both interactive modes correctly."""
        status_info = {
            "interactive_mode": interactive_mode,
            "selected_date": "Tuesday, January 16",
            "relative_description": "Tomorrow",
        }

        result = rpi_renderer.render_events([mock_cached_event], status_info)

        if interactive_mode:
            assert 'data-action="prev"' in result
            assert 'data-action="next"' in result
        else:
            assert 'data-action="prev"' not in result
            assert 'data-action="next"' not in result

    def test_error_handling_in_render_events(self, rpi_renderer):
        """Test error handling in render_events method."""
        with patch.object(
            rpi_renderer, "_build_html_template", side_effect=Exception("Template error")
        ):
            with patch("calendarbot.display.html_renderer.logger") as mock_logger:
                result = rpi_renderer.render_events([])

                assert "Error rendering calendar: Template error" in result
                mock_logger.error.assert_called_with(
                    "Failed to render events to HTML: Template error"
                )

    def test_logger_usage(self, mock_settings):
        """Test proper logger usage throughout RPI renderer."""
        with patch("calendarbot.display.rpi_html_renderer.logger") as mock_logger:
            # Test initialization logging
            RaspberryPiHTMLRenderer(mock_settings)
            mock_logger.debug.assert_called_with(
                "RPI HTML renderer initialized for 800x480px e-ink display with 'eink' theme"
            )

    def test_inheritance_from_html_renderer(self, rpi_renderer):
        """Test that RPI renderer properly inherits HTMLRenderer functionality."""
        # Should inherit _escape_html method
        result = rpi_renderer._escape_html("<test>")
        assert result == "&lt;test&gt;"

        # Should inherit render_error method
        error_result = rpi_renderer.render_error("Test error")
        assert "Test error" in error_result

    def test_phase_3_information_architecture(self, rpi_renderer, mock_current_event):
        """Test Phase 3 information architecture implementation."""
        # Test that current events get proper Phase 3 styling
        result = rpi_renderer._format_current_event_rpi(mock_current_event)

        # Check Phase 3 specific classes and structure
        assert "card-current" in result
        assert "event-current" in result
        assert "▶" in result  # Phase 3 icon

        # Test upcoming event Phase 3 structure
        mock_current_event.is_current.return_value = False
        mock_current_event.is_upcoming.return_value = True
        result = rpi_renderer._format_upcoming_event_rpi(mock_current_event)

        assert "card-upcoming" in result
        assert "event-upcoming" in result
        assert "📋" in result  # Phase 3 icon

    def test_touch_friendly_navigation_elements(self, rpi_renderer):
        """Test touch-friendly navigation elements for RPI."""
        result = rpi_renderer._generate_header_navigation_with_date(
            "Test Date", interactive_mode=True
        )

        # Check for proper ARIA labels and accessibility
        assert 'aria-label="Date Navigation"' in result
        assert 'aria-label="Navigate to previous day"' in result
        assert 'aria-label="Navigate to next day"' in result
        assert 'title="Previous Day"' in result
        assert 'title="Next Day"' in result


class TestRPiHTMLRendererIntegration:
    """Integration tests for RPI HTML Renderer with realistic scenarios."""

    @pytest.fixture
    def rpi_settings(self):
        """Create RPI-specific settings."""
        settings = Mock()
        settings.web_theme = "eink-rpi"
        settings.display_type = "rpi"
        settings.display_enabled = True
        return settings

    @pytest.fixture
    def realistic_rpi_events(self):
        """Create realistic events for RPI testing."""
        events = []
        now = datetime(2025, 1, 15, 10, 0, 0)

        # Current meeting
        current = Mock(spec=CachedEvent)
        current.id = "current-standup"
        current.subject = "Daily Team Standup"
        current.location_display_name = "Conference Room Alpha"
        current.is_online_meeting = False
        current.is_current.return_value = True
        current.is_upcoming.return_value = False
        current.format_time_range.return_value = "10:00 AM - 10:30 AM"
        current.start_dt = now
        current.end_dt = now + timedelta(minutes=30)
        events.append(current)

        # Next 3 upcoming meetings
        for i in range(3):
            upcoming = Mock(spec=CachedEvent)
            upcoming.id = f"upcoming-{i+1}"
            upcoming.subject = f"Meeting {i+1}"
            upcoming.location_display_name = "Microsoft Teams Meeting" if i == 1 else f"Room {i+1}"
            upcoming.is_online_meeting = i == 1
            upcoming.is_current.return_value = False
            upcoming.is_upcoming.return_value = True
            upcoming.format_time_range.return_value = f"{11+i}:00 AM - {12+i}:00 PM"
            upcoming.time_until_start.return_value = 60 + (i * 60)
            events.append(upcoming)

        # Later events (5 more)
        for i in range(5):
            later = Mock(spec=CachedEvent)
            later.id = f"later-{i+1}"
            later.subject = f"Later Meeting {i+1}"
            later.location_display_name = None if i % 2 else f"Conference Room {i+1}"
            later.is_online_meeting = i % 2 == 0
            later.is_current.return_value = False
            later.is_upcoming.return_value = True
            later.format_time_range.return_value = f"{14+i}:00 PM - {15+i}:00 PM"
            later.time_until_start.return_value = 240 + (i * 60)
            events.append(later)

        return events

    def test_full_rpi_page_rendering_interactive(self, rpi_settings, realistic_rpi_events):
        """Test complete RPI page rendering in interactive mode."""
        renderer = RaspberryPiHTMLRenderer(rpi_settings)

        status_info = {
            "interactive_mode": True,
            "selected_date": "Monday, January 15, 2025",
            "last_update": "2025-01-15T14:30:00Z",
            "is_cached": False,
            "connection_status": "Connected",
            "relative_description": "Today",
        }

        result = renderer.render_events(realistic_rpi_events, status_info)

        # Verify RPI-specific structure
        assert 'class="theme-eink"' in result
        assert "width=800, height=480" in result
        assert "/static/eink-rpi.css" in result
        assert "/static/eink-rpi.js" in result

        # Verify all sections are present
        assert "▶ Current Event" in result
        assert "Daily Team Standup" in result
        assert "📋 Next Up" in result
        assert "⏰ Later Today" in result

        # Verify interactive elements
        assert 'data-action="prev"' in result
        assert 'data-action="next"' in result

        # Verify proper Teams meeting filtering
        assert "💻 Online" in result
        assert "Microsoft Teams Meeting" not in result

    def test_rpi_error_page_with_cached_data(self, rpi_settings, realistic_rpi_events):
        """Test RPI error page rendering with cached events."""
        renderer = RaspberryPiHTMLRenderer(rpi_settings)

        result = renderer.render_error("Microsoft Graph API unavailable", realistic_rpi_events)

        assert "Connection Issue" in result
        assert "Microsoft Graph API unavailable" in result
        assert "📱 Showing Cached Data" in result
        assert "Daily Team Standup" in result
        # Should limit to 3 events in error display
        assert "Later Meeting" not in result

    def test_rpi_authentication_flow(self, rpi_settings):
        """Test RPI authentication prompt rendering."""
        renderer = RaspberryPiHTMLRenderer(rpi_settings)

        result = renderer.render_authentication_prompt(
            "https://microsoft.com/devicelogin", "RPI12345"
        )

        # Check RPI-specific dimensions and styling
        assert "width=800, height=480" in result
        assert 'class="theme-eink"' in result
        assert "🔐 Authentication Required" in result
        assert "RPI12345" in result
        assert "microsoft.com/devicelogin" in result

    def test_responsive_layout_for_eink_display(self, rpi_settings, realistic_rpi_events):
        """Test responsive layout generation for e-ink displays."""
        renderer = RaspberryPiHTMLRenderer(rpi_settings)

        result = renderer.render_events(realistic_rpi_events)

        # Check CSS Grid layout structure for RPI
        assert 'class="calendar-container"' in result
        assert 'class="calendar-header"' in result
        assert 'class="calendar-content"' in result
        assert 'class="calendar-status"' in result

        # Check Phase 3 information architecture
        assert "section-current" in result
        assert "section-upcoming" in result
        assert "section-later" in result

    def test_eink_color_optimization(self, rpi_settings):
        """Test e-ink color optimization through theme selection."""
        renderer = RaspberryPiHTMLRenderer(rpi_settings)

        # Verify eink theme is forced regardless of settings
        assert renderer.theme == "eink"

        result = renderer._build_html_template("Test", "", "", "", False)

        # Check that eink theme CSS is loaded
        assert "/static/eink-rpi.css" in result
        assert 'class="theme-eink"' in result
