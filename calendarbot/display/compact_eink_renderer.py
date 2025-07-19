"""Compact e-ink HTML renderer for 300x400px displays."""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from ..cache.models import CachedEvent
from .rpi_html_renderer import RaspberryPiHTMLRenderer

logger = logging.getLogger(__name__)


class CompactEInkRenderer(RaspberryPiHTMLRenderer):
    """HTML renderer optimized for compact e-ink displays (300x400px).

    Extends the RaspberryPiHTMLRenderer with compact-specific layout and components:
    - CSS Grid layout optimized for 300x400 viewport
    - Compact typography scale (16px-11px)
    - Fixed section heights: 50px header, 310px content, 40px status
    - Content truncation for small screen space
    - Touch-friendly 35px minimum targets with 6px spacing
    - Optimized for resource-constrained devices
    """

    def __init__(self, settings: Any) -> None:
        """Initialize Compact E-ink renderer.

        Args:
            settings: Application settings
        """
        logger.debug("DIAGNOSTIC: CompactEInkRenderer.__init__ called")
        try:
            super().__init__(settings)
            # Override layout for compact e-ink display
            self.layout = "3x4"
            logger.debug(
                "DIAGNOSTIC: CompactEInkRenderer initialized successfully for 300x400px display"
            )
        except Exception as e:
            logger.error(f"DIAGNOSTIC: CompactEInkRenderer.__init__ failed: {e}")
            raise

    def _build_html_template(
        self,
        display_date: str,
        status_line: str,
        events_content: str,
        nav_help: str,
        interactive_mode: bool,
        status_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the complete HTML template optimized for compact e-ink display.

        Args:
            display_date: Formatted date string
            status_line: Status information HTML
            events_content: Main events content HTML
            nav_help: Navigation help HTML (unused in compact layout)
            interactive_mode: Whether in interactive mode
            status_info: Additional status information (unused in compact layout)

        Returns:
            Complete HTML document with compact e-ink layout
        """
        # DEBUG: Log critical parameters for compact UX debugging
        logger.debug(f"Compact HTML Template - interactive_mode: {interactive_mode}")
        logger.debug(f"Compact HTML Template - display_date: {display_date}")
        logger.debug(
            f"Compact HTML Template - viewport will be: width=300, height=400 (compact portrait)"
        )

        # Generate compact header navigation
        compact_header_navigation = self._generate_compact_header_navigation(
            display_date, interactive_mode
        )

        # Generate compact status bar
        compact_status_bar = self._generate_compact_status_bar(status_line)

        # Dynamic resource loading using inherited ResourceManager
        css_files, js_files = self._get_dynamic_resources()

        # Generate link and script tags for multiple files
        css_links = "\n    ".join(
            [f'<link rel="stylesheet" href="/static/{css}">' for css in css_files]
        )
        js_scripts = "\n    ".join([f'<script src="/static/{js}"></script>' for js in js_files])

        return f"""<!DOCTYPE html>
<html lang="en" class="layout-{self.layout}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=300, height=400, initial-scale=1.0, user-scalable=no">
    <title>📅 Calendar Bot - {display_date}</title>
    {css_links}
</head>
<body>
    <div class="calendar-container">
        <header class="calendar-header" role="banner">
            {compact_header_navigation}
        </header>

        <main id="main-content" class="calendar-content" role="main" aria-label="Calendar Events">
            {events_content}
        </main>

        {compact_status_bar}
    </div>

    {js_scripts}
</body>
</html>"""

    def _generate_compact_header_navigation(self, display_date: str, interactive_mode: bool) -> str:
        """Generate compact header navigation with minimal elements.

        Args:
            display_date: Formatted date string to display in center
            interactive_mode: Whether in interactive mode

        Returns:
            HTML for compact header navigation
        """
        if not interactive_mode:
            return f"""
            <div class="header-navigation">
                <div class="nav-controls"></div>
                <div class="header-main">
                    <h1 class="calendar-title">{display_date}</h1>
                </div>
                <div class="layout-controls"></div>
            </div>
            """

        return f"""
        <div class="nav-controls" role="toolbar" aria-label="Navigation Controls">
        </div>
        <div class="header-main">
            <h1 class="calendar-title">{display_date}</h1>
        </div>
        <div class="theme-controls" role="toolbar" aria-label="Theme Controls">
        </div>
        """

    def _generate_compact_status_bar(self, status_line: str) -> str:
        """Generate compact status bar for compact layout.

        Args:
            status_line: Status information HTML from the base renderer

        Returns:
            HTML for compact status bar
        """
        return f"""
        <div id="status" class="calendar-status" role="status" aria-label="Calendar Status">
            {self._render_compact_status_line_html(status_line)}
        </div>
        """

    def _render_compact_status_line_html(self, status_line: str) -> str:
        """Render status line with compact styling.

        Args:
            status_line: Status information HTML

        Returns:
            Formatted compact status line HTML
        """
        if not status_line:
            return ""

        # Truncate status line for compact display
        truncated_status = self._truncate_text(status_line, 35)
        return f'<div class="status-line">{truncated_status}</div>'

    def _render_events_content(self, events: List[CachedEvent], interactive_mode: bool) -> str:
        """Render events content optimized for compact e-ink display with strict space constraints.

        Args:
            events: List of events to render
            interactive_mode: Whether in interactive mode

        Returns:
            HTML content for events using compact structured layout
        """
        if not events:
            return self._render_no_events_compact()

        content_parts = []

        # Compact Event Grouping with Fixed Heights
        current_events = [e for e in events if e.is_current()]
        upcoming_events = [e for e in events if e.is_upcoming()]

        # Current event section (120px height - above fold)
        if current_events:
            content_parts.append(self._render_current_events_section_compact(current_events[:1]))

        # Next Up section (80px height - single event only)
        if upcoming_events:
            next_up_events = upcoming_events[:1]  # Only 1 event for compact
            content_parts.append(self._render_next_up_events_section_compact(next_up_events))

        # Later Today section (60px height - summary list, max 3 events)
        later_events = upcoming_events[1:4] if len(upcoming_events) > 1 else []
        if later_events:
            content_parts.append(self._render_later_today_section_compact(later_events))

        return "\n".join(content_parts)

    def _render_no_events_compact(self) -> str:
        """Render no events state for compact display.

        Returns:
            HTML for compact no events state
        """
        return """
        <div class="no-events" role="region" aria-label="No Events Today">
            <div class="no-events-icon" aria-hidden="true">🎉</div>
            <h2>No meetings!</h2>
            <p>Free time.</p>
        </div>
        """

    def _render_current_events_section_compact(self, current_events: List[CachedEvent]) -> str:
        """Render current events section with compact structure.

        Args:
            current_events: List of current events (max 1 for compact)

        Returns:
            HTML for compact current events section
        """
        section_parts = [
            '<section class="section-current" role="region" aria-labelledby="current-heading">',
            '<h2 id="current-heading" class="section-title">▶ Now</h2>',
        ]

        # Show only the first current event for compact layout
        event = current_events[0]
        section_parts.append(self._format_current_event_compact(event))

        section_parts.append("</section>")
        return "\n".join(section_parts)

    def _render_next_up_events_section_compact(self, next_up_events: List[CachedEvent]) -> str:
        """Render Next Up events section with compact structure.

        Args:
            next_up_events: List of next up events (max 1 for compact)

        Returns:
            HTML for compact Next Up events section
        """
        section_parts = [
            '<section class="section-upcoming" role="region" aria-labelledby="upcoming-heading">',
            '<h2 id="upcoming-heading" class="section-title">📋 Next</h2>',
        ]

        # Show only 1 event for compact layout
        event = next_up_events[0]
        section_parts.append(self._format_upcoming_event_compact(event))

        section_parts.append("</section>")
        return "\n".join(section_parts)

    def _render_later_today_section_compact(self, later_events: List[CachedEvent]) -> str:
        """Render Later Today section with compact list format.

        Args:
            later_events: List of later events (max 3 for compact)

        Returns:
            HTML for compact Later Today section
        """
        section_parts = [
            '<section class="section-later" role="region" aria-labelledby="later-heading">',
            '<h2 id="later-heading" class="section-title">⏰ Later</h2>',
            '<ul class="later-events-list" role="list">',
        ]

        # Show up to 3 later events in compact format
        for event in later_events[:3]:
            section_parts.append(self._format_later_event_compact(event))

        section_parts.extend(["</ul>", "</section>"])
        return "\n".join(section_parts)

    def _format_current_event_compact(self, event: CachedEvent) -> str:
        """Format current event with compact structure and truncation for 300x400px displays.

        Creates a compact event card optimized for small screen real estate with
        aggressive text truncation and essential information only. Calculates duration,
        formats location data, and includes time remaining indicators with urgency styling.

        Args:
            event: Current event to format. Must be a CachedEvent instance with valid
                  start_dt, end_dt, subject, and optional location_display_name and
                  is_online_meeting attributes. Event should have is_current() == True.

        Returns:
            str: HTML string containing a complete event card with:
                - Truncated event title (max 25 chars)
                - Time range with duration in minutes
                - Location information (if available, max 18 chars)
                - Time remaining with urgency styling (red if ≤5 min)

        Raises:
            AttributeError: If event lacks required datetime or subject attributes
            TypeError: If event is not a CachedEvent instance

        Example:
            >>> event = CachedEvent(subject="Team Meeting", start_dt=..., end_dt=...)
            >>> html = renderer._format_current_event_compact(event)
            >>> "▶ Team Meeting" in html
            True
        """
        # Calculate duration
        duration_mins = (event.end_dt - event.start_dt).total_seconds() / 60
        duration_text = f" ({int(duration_mins)}min)" if duration_mins > 0 else ""

        # Truncate title for compact display
        truncated_title = self._truncate_text(event.subject, 25)

        # Compact location information
        location_html = self._format_event_location_compact(event)

        # Compact time remaining
        time_remaining_html = self._format_time_remaining_compact(event)

        return f"""
        <div class="current-event" data-event-id="{event.id}"
             role="article" aria-label="Current Event">
            <h3 class="event-title">▶ {self._escape_html(truncated_title)}</h3>
            <div class="event-time">{self._truncate_text(event.format_time_range(), 20)}{duration_text}</div>
            {location_html}
            {time_remaining_html}
        </div>
        """

    def _format_upcoming_event_compact(self, event: CachedEvent) -> str:
        """Format upcoming event with compact structure and truncation.

        Args:
            event: Upcoming event to format

        Returns:
            HTML string for the compact upcoming event card
        """
        # Truncate title for compact display
        truncated_title = self._truncate_text(event.subject, 20)

        # Compact location information
        location_text = ""
        if (
            event.location_display_name
            and "Microsoft Teams Meeting" not in event.location_display_name
        ):
            location_text = f" | 📍 {self._truncate_text(event.location_display_name, 12)}"

        # Compact time until start
        time_until_html = self._format_time_until_compact(event)

        return f"""
        <div class="upcoming-event" data-event-id="{event.id}"
             role="article" aria-label="Upcoming Event">
            <h4 class="event-title">📋 {self._escape_html(truncated_title)}</h4>
            <div class="event-details">{self._truncate_text(event.format_time_range(), 15)}{location_text}</div>
            {time_until_html}
        </div>
        """

    def _format_later_event_compact(self, event: CachedEvent) -> str:
        """Format later event with compact list format.

        Args:
            event: Later event to format

        Returns:
            HTML string for the compact later event list item
        """
        # Truncate title for compact display
        truncated_title = self._truncate_text(event.subject, 15)

        # Compact time display
        compact_time = self._truncate_text(event.format_time_range(), 10)

        return f"""
        <li class="later-event" data-event-id="{event.id}" role="listitem"
            aria-label="Later Event: {self._escape_html(truncated_title)}">
            <span class="event-title">{self._escape_html(truncated_title)}</span>
            <span class="event-time">{compact_time}</span>
        </li>
        """

    def _format_event_location_compact(self, event: CachedEvent) -> str:
        """Format event location for compact display.

        Args:
            event: Event with location information

        Returns:
            HTML for compact event location
        """
        if event.location_display_name:
            # Filter out "Microsoft Teams Meeting" text and truncate
            location_name = event.location_display_name
            if "Microsoft Teams Meeting" not in location_name:
                truncated_location = self._truncate_text(location_name, 18)
                return (
                    f'<div class="event-location">📍 {self._escape_html(truncated_location)}</div>'
                )
        return ""

    def _format_time_remaining_compact(self, event: CachedEvent) -> str:
        """Format time remaining for current event with compact styling and exception handling.

        Calculates and formats the time remaining until the current event ends,
        with urgency-based styling for visual alerts. Handles timezone-aware
        calculations and gracefully manages calculation errors.

        Args:
            event: Current event instance. Must have valid end_dt attribute
                  with timezone-aware datetime for accurate time calculations.

        Returns:
            str: HTML string with time remaining display, or empty string if:
                - Time calculation fails due to timezone issues
                - Event has already ended (time_left <= 0)
                - Required helper functions are unavailable

                Format: '<div class="time-remaining [urgent]">⏱️ {minutes}min left</div>'
                The 'urgent' class is applied when ≤5 minutes remain.

        Raises:
            No exceptions raised - all errors are caught and logged internally.
            Method returns empty string on any calculation failure.

        Exception Handling:
            - ImportError: If get_timezone_aware_now() helper is unavailable
            - AttributeError: If event.end_dt is missing or invalid
            - TypeError: If datetime calculations fail due to type mismatches
            - Any other unexpected exceptions during time calculations

        Note:
            Uses try/except to ensure UI stability even with malformed event data.
            Timezone awareness is critical for accurate time remaining calculations.
        """
        logger.debug("DIAGNOSTIC: _format_time_remaining_compact called")
        try:
            from ..utils.helpers import get_timezone_aware_now

            logger.debug("DIAGNOSTIC: get_timezone_aware_now imported successfully")

            now = get_timezone_aware_now()
            logger.debug(f"DIAGNOSTIC: current time: {now}")
            logger.debug(f"DIAGNOSTIC: event.end_dt: {event.end_dt}")

            time_left = (event.end_dt - now).total_seconds() / 60
            logger.debug(f"DIAGNOSTIC: time_left calculated: {time_left}")

            if time_left > 0:
                urgency_class = "urgent" if time_left <= 5 else ""
                result = (
                    f'<div class="time-remaining {urgency_class}">⏱️ {int(time_left)}min left</div>'
                )
                logger.debug(f"DIAGNOSTIC: time remaining HTML generated: {result}")
                return result
        except Exception as e:
            logger.error(f"DIAGNOSTIC: _format_time_remaining_compact failed: {e}")
            logger.error(f"DIAGNOSTIC: Exception type: {type(e)}")
            import traceback

            logger.error(f"DIAGNOSTIC: Traceback: {traceback.format_exc()}")
        return ""

    def _format_time_until_compact(self, event: CachedEvent) -> str:
        """Format time until start for upcoming event with compact styling.

        Args:
            event: Upcoming event

        Returns:
            HTML for compact time until start
        """
        time_until = event.time_until_start()
        if time_until is not None and time_until <= 60:  # Show if within 1 hour
            if time_until <= 5:
                return f'<div class="time-until urgent">🔔 {time_until}min!</div>'
            elif time_until <= 30:
                return f'<div class="time-until soon">⏰ {time_until}min</div>'
            else:
                return f'<div class="time-until">⏰ {time_until}min</div>'
        return ""

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text for compact display.

        Args:
            text: Text to truncate
            max_length: Maximum character length

        Returns:
            Truncated text with ellipsis if needed
        """
        if not text or len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def _render_error_html(
        self, error_message: str, cached_events: Optional[List[CachedEvent]] = None
    ) -> str:
        """Render error HTML content for compact display.

        Args:
            error_message: Error message to display
            cached_events: Optional cached events to show

        Returns:
            HTML error content with compact layout
        """
        cached_content = ""
        if cached_events:
            cached_items = []
            for event in cached_events[:2]:  # Limit to 2 for compact display
                location = ""
                if event.location_display_name:
                    location = f" | 📍 {self._truncate_text(event.location_display_name, 10)}"

                cached_items.append(
                    f"""
                <li class="cached-event">
                    <span class="event-title">{self._escape_html(self._truncate_text(event.subject, 15))}</span>
                    <span class="event-details">{self._truncate_text(event.format_time_range(), 10)}{location}</span>
                </li>
                """
                )

            cached_content = f"""
            <section class="cached-data">
                <h2>📱 Cached Data</h2>
                <ul class="cached-events-list">
                    {''.join(cached_items)}
                </ul>
            </section>
            """
        else:
            cached_content = '<div class="no-cache">❌ No cached data</div>'

        # Dynamic resource loading using inherited ResourceManager
        css_files, js_files = self._get_dynamic_resources()

        # Generate link and script tags for multiple files
        css_links = "\n    ".join(
            [f'<link rel="stylesheet" href="/static/{css}">' for css in css_files]
        )
        js_scripts = "\n    ".join([f'<script src="/static/{js}"></script>' for js in js_files])

        return f"""<!DOCTYPE html>
<html lang="en" class="layout-{self.layout}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=300, height=400, initial-scale=1.0, user-scalable=no">
    <title>📅 Calendar Bot - Error</title>
    {css_links}
</head>
<body>
    <div class="calendar-container">
        <header class="calendar-header">
            <div class="nav-controls"></div>
            <div class="header-main">
                <h1 class="calendar-title">📅 {datetime.now().strftime('%m/%d')}</h1>
            </div>
            <div class="theme-controls"></div>
        </header>

        <main class="calendar-content">
            <section class="error-section">
                <div class="error-icon">⚠️</div>
                <h2 class="error-title">Error</h2>
                <p class="error-message">{self._escape_html(self._truncate_text(error_message, 40))}</p>
            </section>

            {cached_content}
        </main>

        <div class="calendar-status">
            <div class="status-line">Error</div>
        </div>
    </div>

    {js_scripts}
</body>
</html>"""

    def render_authentication_prompt(self, verification_uri: str, user_code: str) -> str:
        """Render authentication prompt optimized for compact e-ink display.

        Args:
            verification_uri: URL for user to visit
            user_code: Code for user to enter

        Returns:
            Formatted HTML authentication prompt with compact layout
        """
        # Dynamic resource loading using inherited ResourceManager
        css_files, js_files = self._get_dynamic_resources()

        # Generate link and script tags for multiple files
        css_links = "\n    ".join(
            [f'<link rel="stylesheet" href="/static/{css}">' for css in css_files]
        )

        return f"""<!DOCTYPE html>
<html lang="en" class="layout-{self.layout}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=300, height=400, initial-scale=1.0, user-scalable=no">
    <title>📅 Calendar Bot - Auth</title>
    {css_links}
</head>
<body>
    <div class="calendar-container">
        <header class="calendar-header">
            <div class="nav-controls"></div>
            <div class="header-main">
                <h1 class="calendar-title">🔐 Auth Required</h1>
            </div>
            <div class="theme-controls"></div>
        </header>

        <main class="calendar-content">
            <section class="auth-section">
                <h2>MS 365 Auth</h2>
                <p>To access calendar:</p>

                <div class="auth-steps">
                    <div class="auth-step">
                        <span class="step-number">1.</span>
                        <span class="step-text">Visit: {self._truncate_text(verification_uri, 25)}</span>
                    </div>
                    <div class="auth-step">
                        <span class="step-number">2.</span>
                        <span class="step-text">Code: <code class="user-code">{user_code}</code></span>
                    </div>
                </div>

                <div class="auth-status">
                    <p>Waiting...</p>
                    <div class="loading-spinner">⏳</div>
                </div>
            </section>
        </main>

        <div class="calendar-status">
            <div class="status-line">Auth</div>
        </div>
    </div>
</body>
</html>"""
