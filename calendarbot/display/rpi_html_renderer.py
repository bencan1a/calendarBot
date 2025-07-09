"""Raspberry Pi e-ink HTML renderer for 800x480px displays."""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from ..cache.models import CachedEvent
from .html_renderer import HTMLRenderer

logger = logging.getLogger(__name__)


class RaspberryPiHTMLRenderer(HTMLRenderer):
    """HTML renderer optimized for Raspberry Pi e-ink displays (480x800px).

    Extends the base HTMLRenderer with RPI-specific layout and components:
    - CSS Grid layout with header, content, and navigation areas
    - Bottom navigation bar with previous/next day buttons and centered date display
    - Component-based event cards optimized for e-ink contrast
    - Touch-friendly navigation elements
    - Fixed 800x480 viewport dimensions
    """

    def __init__(self, settings: Any) -> None:
        """Initialize RPI HTML renderer.

        Args:
            settings: Application settings
        """
        super().__init__(settings)
        # Override theme for RPI e-ink display - use the more visually appealing 'eink' theme
        self.theme = "eink"

        logger.debug("RPI HTML renderer initialized for 800x480px e-ink display with 'eink' theme")

    def _build_html_template(
        self,
        display_date: str,
        status_line: str,
        events_content: str,
        nav_help: str,
        interactive_mode: bool,
    ) -> str:
        """Build the complete HTML template optimized for RPI e-ink display.

        Args:
            display_date: Formatted date string
            status_line: Status information HTML
            events_content: Main events content HTML
            nav_help: Navigation help HTML (unused in RPI layout)
            interactive_mode: Whether in interactive mode

        Returns:
            Complete HTML document with RPI e-ink layout
        """
        # DEBUG: Log critical parameters for UX debugging
        logger.debug(f"RPI HTML Template - interactive_mode: {interactive_mode}")
        logger.debug(f"RPI HTML Template - display_date: {display_date}")
        logger.debug(
            f"RPI HTML Template - viewport will be: width=480, height=800 (portrait layout)"
        )

        # Generate header navigation with arrow buttons and date
        header_navigation = self._generate_header_navigation_with_date(
            display_date, interactive_mode
        )

        # Generate bottom status bar (replaces navigation)
        bottom_status_bar = self._generate_bottom_status_bar(status_line)

        return f"""<!DOCTYPE html>
<html lang="en" class="theme-{self.theme}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=480, height=800, initial-scale=1.0, user-scalable=no">
    <title>📅 Calendar Bot - {display_date}</title>
    <link rel="stylesheet" href="/static/style.css">
    <link rel="stylesheet" href="/static/eink-rpi.css">
</head>
<body>
    <div class="calendar-container">
        <header class="calendar-header" role="banner">
            {header_navigation}
        </header>

        <main id="main-content" class="calendar-content" role="main" aria-label="Calendar Events">
            {events_content}
        </main>

        {bottom_status_bar}
    </div>

    <script src="/static/app.js"></script>
    <script src="/static/eink-rpi.js"></script>
</body>
</html>"""

    def _generate_header_navigation_with_date(
        self, display_date: str, interactive_mode: bool
    ) -> str:
        """Generate header navigation with arrow buttons and centered date display.

        Args:
            display_date: Formatted date string to display in center
            interactive_mode: Whether in interactive mode

        Returns:
            HTML for header navigation with arrow buttons and date
        """
        if not interactive_mode:
            return f"""
            <div class="header-navigation">
                <div class="nav-arrow-left"></div>
                <div class="header-date">{display_date}</div>
                <div class="nav-arrow-right"></div>
            </div>
            """

        return f"""
        <div class="header-navigation" role="toolbar" aria-label="Date Navigation">
            <button class="nav-arrow-left"
                    title="Previous Day"
                    aria-label="Navigate to previous day"
                    data-action="prev">
                ←
            </button>
            <div class="header-date">{display_date}</div>
            <button class="nav-arrow-right"
                    title="Next Day"
                    aria-label="Navigate to next day"
                    data-action="next">
                →
            </button>
        </div>
        """

    def _generate_bottom_status_bar(self, status_line: str) -> str:
        """Generate bottom status bar for RPI layout.

        Args:
            status_line: Status information HTML from the base renderer

        Returns:
            HTML for bottom status bar
        """
        return f"""
        <div id="status" class="calendar-status" role="status" aria-label="Calendar Status">
            {self._render_status_line_html(status_line)}
        </div>
        """

    def _generate_theme_toggle(self) -> str:
        """Generate theme toggle button for header.

        Returns:
            HTML for theme toggle button
        """
        return """
        <div class="theme-controls" role="toolbar" aria-label="Theme Controls">
            <button class="theme-toggle"
                    title="Toggle Theme"
                    aria-label="Toggle Theme - Switch between light and dark modes"
                    data-action="theme">
                🎨
            </button>
        </div>
        """

    def _render_status_line_html(self, status_line: str) -> str:
        """Render status line with appropriate styling for RPI layout.

        Args:
            status_line: Status information HTML

        Returns:
            Formatted status line HTML
        """
        if not status_line:
            return ""

        return f'<div class="status-line">{status_line}</div>'

    def _render_events_content(self, events: List[CachedEvent], interactive_mode: bool) -> str:
        """Render events content optimized for RPI e-ink display with Phase 3 information architecture.

        Args:
            events: List of events to render
            interactive_mode: Whether in interactive mode

        Returns:
            HTML content for events using Phase 3 structured layout
        """
        if not events:
            return self._render_no_events_rpi()

        content_parts = []

        # Phase 3: Enhanced Event Grouping with Information Density Optimization
        current_events = [e for e in events if e.is_current()]
        upcoming_events = [e for e in events if e.is_upcoming()]

        # Current event section (above fold - most prominent)
        if current_events:
            content_parts.append(self._render_current_events_section_rpi(current_events))

        # Next Up section (next 3 events - above fold)
        if upcoming_events:
            next_up_events = upcoming_events[:3]
            content_parts.append(self._render_next_up_events_section_rpi(next_up_events))

        # Later Today section (compact list - scrollable area, max 5 events)
        later_events = upcoming_events[3:8] if len(upcoming_events) > 3 else []
        if later_events:
            content_parts.append(self._render_later_today_section_rpi(later_events))

        return "\n".join(content_parts)

    def _render_no_events_rpi(self) -> str:
        """Render no events state for RPI display.

        Returns:
            HTML for no events state
        """
        return """
        <div class="no-events" role="region" aria-label="No Events Today">
            <div class="no-events-icon" aria-hidden="true">🎉</div>
            <h2>No meetings scheduled!</h2>
            <p>Enjoy your free time.</p>
        </div>
        """

    def _render_current_events_section_rpi(self, current_events: List[CachedEvent]) -> str:
        """Render current events section with Phase 3 information architecture.

        Args:
            current_events: List of current events

        Returns:
            HTML for current events section with enhanced structure
        """
        section_parts = [
            '<section class="section-current" role="region" aria-labelledby="current-heading">',
            '<h2 id="current-heading" class="section-title">▶ Current Event</h2>',
        ]

        # Show only the first current event for RPI layout with Phase 3 structure
        event = current_events[0]
        section_parts.append(self._format_current_event_rpi(event))

        section_parts.append("</section>")
        return "\n".join(section_parts)

    def _render_next_up_events_section_rpi(self, next_up_events: List[CachedEvent]) -> str:
        """Render Next Up events section with Phase 3 information architecture.

        Args:
            next_up_events: List of next up events (max 3)

        Returns:
            HTML for Next Up events section with enhanced structure
        """
        section_parts = [
            '<section class="section-upcoming" role="region" aria-labelledby="upcoming-heading">',
            '<h2 id="upcoming-heading" class="section-title">📋 Next Up</h2>',
        ]

        # Show next 3 events for RPI layout with Phase 3 structure
        for event in next_up_events:
            section_parts.append(self._format_upcoming_event_rpi(event))

        section_parts.append("</section>")
        return "\n".join(section_parts)

    def _render_later_today_section_rpi(self, later_events: List[CachedEvent]) -> str:
        """Render Later Today section with Phase 3 compact list format.

        Args:
            later_events: List of later events (max 5 for information density)

        Returns:
            HTML for Later Today section with Phase 3 structure
        """
        section_parts = [
            '<section class="section-later" role="region" aria-labelledby="later-heading">',
            '<h2 id="later-heading" class="section-title">⏰ Later Today</h2>',
            '<ul class="later-events-list" role="list">',
        ]

        # Show up to 5 later events in compact format with Phase 3 structure
        for event in later_events[:5]:
            section_parts.append(self._format_later_event_rpi(event))

        section_parts.extend(["</ul>", "</section>"])
        return "\n".join(section_parts)

    def _format_current_event_rpi(self, event: CachedEvent) -> str:
        """Format current event with Phase 3 information architecture structure.

        Phase 3 Current Event Card Structure:
        [3px Black Border - 16px Padding]
        ▶ MEETING TITLE (18px bold)
        10:00 AM - 11:00 AM (60min) (16px medium)
        📍 Conference Room A (14px normal)
        ⏱️ 25 minutes remaining (14px, urgent styling)

        Args:
            event: Current event to format

        Returns:
            HTML string for the Phase 3 current event card
        """
        # Calculate duration
        duration_mins = (event.end_dt - event.start_dt).total_seconds() / 60
        duration_text = f" ({int(duration_mins)}min)" if duration_mins > 0 else ""

        # Location information with enhanced visual indicators
        location_html = self._format_event_location_rpi(event)

        # Time remaining with urgency styling
        time_remaining_html = self._format_time_remaining_rpi(event)

        return f"""
        <div class="current-event card-current event-current" data-event-id="{event.id}"
             role="article" aria-label="Current Event">
            <h3 class="event-title">▶ {self._escape_html(event.subject)}</h3>
            <div class="event-time">{event.format_time_range()}{duration_text}</div>
            {location_html}
            {time_remaining_html}
        </div>
        """

    def _format_upcoming_event_rpi(self, event: CachedEvent) -> str:
        """Format upcoming event with Phase 3 information architecture structure.

        Phase 3 Upcoming Event Card Structure:
        [2px Border - 12px Padding]
        📋 MEETING TITLE (16px bold)
        2:00 PM - 3:00 PM | 💻 Online (14px)
        ⏰ In 45 minutes (14px)

        Args:
            event: Upcoming event to format

        Returns:
            HTML string for the Phase 3 upcoming event card
        """
        # Location information with enhanced visual indicators - filter out Microsoft Teams Meeting text
        location_text = ""
        if (
            event.location_display_name
            and "Microsoft Teams Meeting" not in event.location_display_name
        ):
            location_text = f" | 📍 {self._escape_html(event.location_display_name)}"
        elif event.is_online_meeting:
            location_text = " | 💻 Online"

        # Time until start with priority visual indicators
        time_until_html = self._format_time_until_rpi(event)

        # Determine urgency class for visual coding
        time_until = event.time_until_start()
        urgency_class = (
            "event-urgent"
            if time_until is not None and time_until <= 5
            else "event-soon" if time_until is not None and time_until <= 30 else ""
        )

        return f"""
        <div class="upcoming-event card-upcoming event-upcoming {urgency_class}" data-event-id="{event.id}"
             role="article" aria-label="Upcoming Event">
            <h4 class="event-title">📋 {self._escape_html(event.subject)}</h4>
            <div class="event-details">{event.format_time_range()}{location_text}</div>
            {time_until_html}
        </div>
        """

    def _format_event_location_rpi(self, event: CachedEvent) -> str:
        """Format event location for RPI display with Phase 3 visual indicators.

        Args:
            event: Event with location information

        Returns:
            HTML for event location with enhanced styling
        """
        if event.location_display_name:
            # Filter out "Microsoft Teams Meeting" text
            location_name = event.location_display_name
            if "Microsoft Teams Meeting" not in location_name:
                return f'<div class="event-location location-physical">📍 {self._escape_html(location_name)}</div>'
        elif event.is_online_meeting:
            return '<div class="event-location location-online">💻 Online Meeting</div>'
        return ""

    def _format_time_remaining_rpi(self, event: CachedEvent) -> str:
        """Format time remaining for current event with Phase 3 urgent styling.

        Args:
            event: Current event

        Returns:
            HTML for time remaining with Phase 3 enhanced styling
        """
        try:
            from ..utils.helpers import get_timezone_aware_now

            now = get_timezone_aware_now()
            time_left = (event.end_dt - now).total_seconds() / 60
            if time_left > 0:
                urgency_class = "urgent" if time_left <= 5 else ""
                return f'<div class="time-remaining {urgency_class}">⏱️ {int(time_left)} minutes remaining</div>'
        except Exception:
            pass
        return ""

    def _format_time_until_rpi(self, event: CachedEvent) -> str:
        """Format time until start for upcoming event with Phase 3 priority indicators.

        Args:
            event: Upcoming event

        Returns:
            HTML for time until start with Phase 3 enhanced priority styling
        """
        time_until = event.time_until_start()
        if time_until is not None and time_until <= 60:  # Show if within 1 hour
            if time_until <= 5:
                return f'<div class="time-until urgent">🔔 Starting in {time_until} minutes!</div>'
            elif time_until <= 30:
                return f'<div class="time-until soon">⏰ In {time_until} minutes</div>'
            else:
                return f'<div class="time-until">⏰ In {time_until} minutes</div>'
        return ""

    def _format_later_event_rpi(self, event: CachedEvent) -> str:
        """Format later event with Phase 3 compact list format and Phase 5 accessibility.

        Args:
            event: Later event to format

        Returns:
            HTML string for the Phase 3 later event list item with Phase 5 accessibility
        """
        # Location information with visual indicators - filter out Microsoft Teams Meeting text
        location_text = ""
        if (
            event.location_display_name
            and "Microsoft Teams Meeting" not in event.location_display_name
        ):
            location_text = f" | 📍 {self._escape_html(event.location_display_name)}"
        elif event.is_online_meeting:
            location_text = " | 💻 Online"

        return f"""
        <li class="later-event" data-event-id="{event.id}" role="listitem"
            aria-label="Later Event: {self._escape_html(event.subject)}">
            <span class="event-title">{self._escape_html(event.subject)}</span>
            <span class="event-details">{event.format_time_range()}{location_text}</span>
        </li>
        """

    def _render_error_html(
        self, error_message: str, cached_events: Optional[List[CachedEvent]] = None
    ) -> str:
        """Render error HTML content for RPI display.

        Args:
            error_message: Error message to display
            cached_events: Optional cached events to show

        Returns:
            HTML error content with RPI layout
        """
        cached_content = ""
        if cached_events:
            cached_items = []
            for event in cached_events[:3]:  # Limit for RPI display
                location = ""
                if event.location_display_name:
                    location = f" | 📍 {self._escape_html(event.location_display_name)}"

                cached_items.append(
                    f"""
                <li class="cached-event">
                    <span class="event-title">{self._escape_html(event.subject)}</span>
                    <span class="event-details">{event.format_time_range()}{location}</span>
                </li>
                """
                )

            cached_content = f"""
            <section class="cached-data">
                <h2>📱 Showing Cached Data</h2>
                <ul class="cached-events-list">
                    {''.join(cached_items)}
                </ul>
            </section>
            """
        else:
            cached_content = '<div class="no-cache">❌ No cached data available</div>'

        return f"""<!DOCTYPE html>
<html lang="en" class="theme-{self.theme}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=480, height=800, initial-scale=1.0, user-scalable=no">
    <title>📅 Calendar Bot - Connection Issue</title>
    <link rel="stylesheet" href="/static/style.css">
    <link rel="stylesheet" href="/static/eink-rpi.css">
</head>
<body>
    <div class="calendar-container">
        <header class="calendar-header">
            <div class="nav-controls"></div>
            <div class="header-main">
                <h1 class="calendar-title">📅 Calendar - {datetime.now().strftime('%A, %B %d')}</h1>
            </div>
            <div class="theme-controls"></div>
        </header>

        <main class="calendar-content">
            <section class="error-section">
                <div class="error-icon">⚠️</div>
                <h2 class="error-title">Connection Issue</h2>
                <p class="error-message">{self._escape_html(error_message)}</p>
            </section>

            {cached_content}
        </main>

        <nav class="calendar-navigation">
            <div class="nav-prev"></div>
            <div class="nav-date-display">Error</div>
            <div class="nav-next"></div>
        </nav>
    </div>

    <script src="/static/app.js"></script>
</body>
</html>"""

    def render_authentication_prompt(self, verification_uri: str, user_code: str) -> str:
        """Render authentication prompt optimized for RPI e-ink display.

        Args:
            verification_uri: URL for user to visit
            user_code: Code for user to enter

        Returns:
            Formatted HTML authentication prompt with RPI layout
        """
        return f"""<!DOCTYPE html>
<html lang="en" class="theme-{self.theme}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=480, height=800, initial-scale=1.0, user-scalable=no">
    <title>📅 Calendar Bot - Authentication Required</title>
    <link rel="stylesheet" href="/static/style.css">
    <link rel="stylesheet" href="/static/eink-rpi.css">
</head>
<body>
    <div class="calendar-container">
        <header class="calendar-header">
            <div class="nav-controls"></div>
            <div class="header-main">
                <h1 class="calendar-title">🔐 Authentication Required</h1>
            </div>
            <div class="theme-controls"></div>
        </header>

        <main class="calendar-content">
            <section class="auth-section">
                <h2>Microsoft 365 Authentication</h2>
                <p>To access your calendar, please complete authentication:</p>

                <div class="auth-steps">
                    <div class="auth-step">
                        <span class="step-number">1.</span>
                        <span class="step-text">Visit: <a href="{verification_uri}" target="_blank">{verification_uri}</a></span>
                    </div>
                    <div class="auth-step">
                        <span class="step-number">2.</span>
                        <span class="step-text">Enter code: <code class="user-code">{user_code}</code></span>
                    </div>
                </div>

                <div class="auth-status">
                    <p>Waiting for authentication...</p>
                    <div class="loading-spinner">⏳</div>
                </div>
            </section>
        </main>

        <nav class="calendar-navigation">
            <div class="nav-prev"></div>
            <div class="nav-date-display">Auth</div>
            <div class="nav-next"></div>
        </nav>
    </div>
</body>
</html>"""
