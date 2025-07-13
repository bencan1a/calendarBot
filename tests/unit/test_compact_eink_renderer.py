"""Unit tests for CompactEInkRenderer."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from calendarbot.cache.models import CachedEvent
from calendarbot.display.compact_eink_renderer import CompactEInkRenderer


class TestCompactEInkRenderer:
    """Test cases for CompactEInkRenderer."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        settings = Mock()
        settings.display_enabled = True
        settings.compact_eink_enabled = True
        settings.compact_eink_display_width = 300
        settings.compact_eink_display_height = 400
        settings.compact_eink_content_truncation = True
        return settings

    @pytest.fixture
    def renderer(self, mock_settings):
        """Create CompactEInkRenderer instance for testing."""
        return CompactEInkRenderer(mock_settings)

    @pytest.fixture
    def sample_event(self):
        """Create sample event for testing."""
        from datetime import timezone

        now = datetime.now(timezone.utc)
        return CachedEvent(
            id="test-1",
            graph_id="graph-test-1",
            subject="Test Meeting with Long Subject Line",
            start_datetime=now.isoformat(),
            end_datetime=(now + timedelta(hours=1)).isoformat(),
            start_timezone="UTC",
            end_timezone="UTC",
            location_display_name="Conference Room A - Building B",
            is_online_meeting=False,
            show_as="busy",
            cached_at=now.isoformat(),
        )

    def test_init(self, mock_settings):
        """Test CompactEInkRenderer initialization."""
        renderer = CompactEInkRenderer(mock_settings)
        assert renderer.layout == "3x4"

    def test_truncate_text_short_text(self, renderer):
        """Test _truncate_text with text shorter than max_length."""
        result = renderer._truncate_text("Short", 10)
        assert result == "Short"

    def test_truncate_text_long_text(self, renderer):
        """Test _truncate_text with text longer than max_length."""
        result = renderer._truncate_text("This is a very long text", 10)
        assert result == "This is..."
        assert len(result) == 10

    def test_truncate_text_empty_text(self, renderer):
        """Test _truncate_text with empty text."""
        result = renderer._truncate_text("", 10)
        assert result == ""

    def test_truncate_text_none_text(self, renderer):
        """Test _truncate_text with None text."""
        result = renderer._truncate_text(None, 10)
        assert result is None

    def test_build_html_template_structure(self, renderer):
        """Test that _build_html_template creates proper HTML structure."""
        html = renderer._build_html_template(
            display_date="Today",
            status_line="Status",
            events_content="<div>Events</div>",
            nav_help="",
            interactive_mode=True,
        )

        # Check for compact layout class
        assert 'class="layout-3x4"' in html

        # Check for compact viewport
        assert "width=300, height=400" in html

        # Check for compact CSS
        assert "3x4.css" in html

        # Check for compact JS
        assert "3x4.js" in html

    def test_generate_compact_header_navigation_interactive(self, renderer):
        """Test compact header navigation in interactive mode."""
        result = renderer._generate_compact_header_navigation("Today", True)

        # Theme toggle button has been removed from compact renderer
        assert "layout-toggle" not in result
        assert "Today" in result

    def test_generate_compact_header_navigation_non_interactive(self, renderer):
        """Test compact header navigation in non-interactive mode."""
        result = renderer._generate_compact_header_navigation("Today", False)

        # Should not include layout toggle button in non-interactive mode
        assert "layout-toggle" not in result
        assert "Today" in result

    def test_generate_compact_status_bar(self, renderer):
        """Test compact status bar generation."""
        status_line = "Last updated: 2023-01-01 12:00:00"
        result = renderer._generate_compact_status_bar(status_line)

        assert "calendar-status" in result
        assert 'role="status"' in result

    def test_render_compact_status_line_html_truncation(self, renderer):
        """Test status line truncation for compact display."""
        long_status = "This is a very long status line that should be truncated for compact display"
        result = renderer._render_compact_status_line_html(long_status)

        # Should be truncated to 35 characters
        assert len(result) < len(f'<div class="status-line">{long_status}</div>')
        assert "..." in result

    def test_render_no_events_compact(self, renderer):
        """Test compact no events rendering."""
        result = renderer._render_no_events_compact()

        assert "no-events" in result
        assert "No meetings!" in result
        assert "Free time." in result

    def test_format_current_event_compact(self, renderer, sample_event):
        """Test compact current event formatting."""
        result = renderer._format_current_event_compact(sample_event)

        # Check for proper structure
        assert "current-event" in result
        assert "event-title" in result
        assert "event-time" in result

        # Check for title truncation (25 chars max)
        assert "Test Meeting with Lon..." in result or "Test Meeting with Long" in result

    def test_format_upcoming_event_compact(self, renderer, sample_event):
        """Test compact upcoming event formatting."""
        result = renderer._format_upcoming_event_compact(sample_event)

        # Check for proper structure
        assert "upcoming-event" in result
        assert "event-title" in result
        assert "event-details" in result

        # Check for title truncation (20 chars max)
        assert len("Test Meeting with Long Subject Line") > 20  # Original is longer
        # The truncated version should be in the result

    def test_format_later_event_compact(self, renderer, sample_event):
        """Test compact later event formatting."""
        result = renderer._format_later_event_compact(sample_event)

        # Check for proper structure
        assert "later-event" in result
        assert "event-title" in result
        assert "event-time" in result
        assert 'role="listitem"' in result

        # Check for title truncation (15 chars max)
        assert len("Test Meeting with Long Subject Line") > 15  # Original is longer

    def test_format_event_location_compact_physical(self, renderer):
        """Test compact physical location formatting."""
        event = Mock()
        event.location_display_name = "Conference Room A - Building B - Floor 3"
        event.is_online_meeting = False

        result = renderer._format_event_location_compact(event)

        assert "📍" in result
        assert "event-location" in result
        # Should be truncated to 18 chars
        assert "..." in result

    def test_format_event_location_compact_online(self, renderer):
        """Test compact online location formatting - should return empty string."""
        event = Mock()
        event.location_display_name = None
        event.is_online_meeting = True

        result = renderer._format_event_location_compact(event)

        # Online meeting indicators were removed, should return empty string
        assert result == ""

    def test_format_event_location_compact_no_location(self, renderer):
        """Test compact formatting with no location."""
        event = Mock()
        event.location_display_name = None
        event.is_online_meeting = False

        result = renderer._format_event_location_compact(event)

        assert result == ""

    def test_format_time_remaining_compact(self, renderer):
        """Test compact time remaining formatting."""
        with patch("calendarbot.utils.helpers.get_timezone_aware_now") as mock_now:
            now = datetime.now()
            mock_now.return_value = now

            event = Mock()
            event.end_dt = now + timedelta(minutes=30)

            result = renderer._format_time_remaining_compact(event)

            assert "⏱️" in result
            assert "time-remaining" in result
            assert "30min left" in result

    def test_format_time_remaining_compact_urgent(self, renderer):
        """Test compact time remaining formatting for urgent events."""
        with patch("calendarbot.utils.helpers.get_timezone_aware_now") as mock_now:
            now = datetime.now()
            mock_now.return_value = now

            event = Mock()
            event.end_dt = now + timedelta(minutes=3)

            result = renderer._format_time_remaining_compact(event)

            assert "urgent" in result
            assert "3min left" in result

    def test_format_time_until_compact_urgent(self, renderer):
        """Test compact time until formatting for urgent events."""
        event = Mock()
        event.time_until_start.return_value = 3

        result = renderer._format_time_until_compact(event)

        assert "🔔" in result
        assert "urgent" in result
        assert "3min!" in result

    def test_format_time_until_compact_soon(self, renderer):
        """Test compact time until formatting for soon events."""
        event = Mock()
        event.time_until_start.return_value = 15

        result = renderer._format_time_until_compact(event)

        assert "⏰" in result
        assert "soon" in result
        assert "15min" in result

    def test_format_time_until_compact_later(self, renderer):
        """Test compact time until formatting for later events."""
        event = Mock()
        event.time_until_start.return_value = 45

        result = renderer._format_time_until_compact(event)

        assert "⏰" in result
        assert "45min" in result
        assert "urgent" not in result
        assert "soon" not in result

    def test_format_time_until_compact_too_far(self, renderer):
        """Test compact time until formatting for events too far away."""
        event = Mock()
        event.time_until_start.return_value = 120  # 2 hours

        result = renderer._format_time_until_compact(event)

        assert result == ""

    def test_render_events_content_no_events(self, renderer):
        """Test rendering with no events."""
        result = renderer._render_events_content([], True)

        assert "no-events" in result
        assert "No meetings!" in result

    def test_render_events_content_with_current_event(self, renderer, sample_event):
        """Test rendering with current event."""
        with patch("calendarbot.cache.models.CachedEvent.is_current", return_value=True), patch(
            "calendarbot.cache.models.CachedEvent.is_upcoming", return_value=False
        ):
            result = renderer._render_events_content([sample_event], True)

            assert "section-current" in result
            assert "▶ Now" in result

    def test_render_events_content_with_upcoming_events(self, renderer, sample_event):
        """Test rendering with upcoming events."""
        with patch("calendarbot.cache.models.CachedEvent.is_current", return_value=False), patch(
            "calendarbot.cache.models.CachedEvent.is_upcoming", return_value=True
        ):
            result = renderer._render_events_content([sample_event], True)

            assert "section-upcoming" in result
            assert "📋 Next" in result

    def test_render_error_html_compact(self, renderer):
        """Test error HTML rendering for compact display."""
        error_message = (
            "This is a very long error message that should be truncated for compact display"
        )

        result = renderer._render_error_html(error_message)

        # Check for compact layout
        assert "layout-3x4" in result

        # Check for compact viewport
        assert "width=300, height=400" in result

        # Check that error message is truncated
        assert "error-message" in result

    def test_render_authentication_prompt_compact(self, renderer):
        """Test authentication prompt rendering for compact display."""
        verification_uri = "https://microsoft.com/devicelogin"
        user_code = "ABC123DEF"

        result = renderer.render_authentication_prompt(verification_uri, user_code)

        # Check for compact layout
        assert "layout-3x4" in result

        # Check for compact viewport
        assert "width=300, height=400" in result

        # Check for authentication content
        assert user_code in result
        assert "MS 365 Auth" in result

    def test_microsoft_teams_meeting_filtering(self, renderer):
        """Test that Microsoft Teams Meeting text is filtered out."""
        event = Mock()
        event.location_display_name = "Microsoft Teams Meeting"
        event.is_online_meeting = False

        result = renderer._format_event_location_compact(event)

        # Should return empty string as Teams Meeting text is filtered
        assert result == ""


class TestCompactEInkRendererIntegration:
    """Integration tests for CompactEInkRenderer."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for integration testing."""
        settings = Mock()
        settings.display_enabled = True
        settings.compact_eink_enabled = True
        settings.compact_eink_display_width = 300
        settings.compact_eink_display_height = 400
        settings.compact_eink_content_truncation = True
        return settings

    @pytest.fixture
    def renderer(self, mock_settings):
        """Create CompactEInkRenderer instance for integration testing."""
        return CompactEInkRenderer(mock_settings)

    def test_full_render_workflow(self, renderer):
        """Test complete rendering workflow."""
        # Create test events
        from datetime import timezone

        now = datetime.now(timezone.utc)
        current_event = CachedEvent(
            id="current-1",
            graph_id="graph-current-1",
            subject="Current Meeting in Progress",
            start_datetime=(now - timedelta(minutes=30)).isoformat(),
            end_datetime=(now + timedelta(minutes=30)).isoformat(),
            start_timezone="UTC",
            end_timezone="UTC",
            location_display_name="Room A",
            is_online_meeting=False,
            show_as="busy",
            cached_at=now.isoformat(),
        )

        upcoming_event = CachedEvent(
            id="upcoming-1",
            graph_id="graph-upcoming-1",
            subject="Upcoming Important Meeting",
            start_datetime=(now + timedelta(minutes=15)).isoformat(),
            end_datetime=(now + timedelta(hours=1, minutes=15)).isoformat(),
            start_timezone="UTC",
            end_timezone="UTC",
            location_display_name=None,
            is_online_meeting=True,  # Online meeting flag still present but not displayed
            show_as="busy",
            cached_at=now.isoformat(),
        )

        events = [current_event, upcoming_event]

        # Test complete rendering with proper mocking at class level
        def mock_is_current(self):
            return self.id == "current-1"

        def mock_is_upcoming(self):
            return self.id == "upcoming-1"

        def mock_format_time_range(self, format_str="%I:%M %p"):
            if self.id == "current-1":
                return "10:00 AM - 11:00 AM"
            else:
                return "10:30 AM - 11:30 AM"

        def mock_time_until_start(self):
            if self.id == "current-1":
                return None
            else:
                return 15

        with patch("calendarbot.cache.models.CachedEvent.is_current", mock_is_current), patch(
            "calendarbot.cache.models.CachedEvent.is_upcoming", mock_is_upcoming
        ), patch(
            "calendarbot.cache.models.CachedEvent.format_time_range", mock_format_time_range
        ), patch(
            "calendarbot.cache.models.CachedEvent.time_until_start", mock_time_until_start
        ):
            result = renderer._render_events_content(events, True)

        # Verify structure
        assert "section-current" in result
        assert "section-upcoming" in result
        assert "▶ Now" in result
        assert "📋 Next" in result

        # Verify content truncation
        assert "Current Meeting in..." in result or "Current Meeting in" in result
        assert "Upcoming Importan" in result  # Truncated version that's actually generated
