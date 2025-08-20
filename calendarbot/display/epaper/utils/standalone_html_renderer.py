"""
Standalone HTML renderer for html2image conversion.

This renderer generates HTML with inline CSS and JS instead of external
resource references, making it suitable for html2image conversion without
requiring a web server.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from ...shared_styling import get_colors_for_renderer

logger = logging.getLogger(__name__)


class StandaloneHtmlRenderer:
    """HTML renderer that generates standalone HTML with inline resources."""

    def __init__(self) -> None:
        """Initialize the standalone HTML renderer."""
        # Get colors for CSS generation
        self._colors = get_colors_for_renderer("html")
        logger.info("StandaloneHtmlRenderer initialized")

    def render_whats_next_view(
        self, display_date: str = "", next_event: Optional[Any] = None, status_message: str = ""
    ) -> str:
        """Render What's Next view as standalone HTML.

        Args:
            display_date: Date to display in header
            next_event: Next upcoming event data
            status_message: Status message to display

        Returns:
            Complete standalone HTML document
        """
        # Generate CSS content
        css_content = self._generate_inline_css()

        # Generate main content
        main_content = self._generate_main_content(next_event, status_message)

        # Build complete HTML
        html = f"""<!DOCTYPE html>
<html lang="en" class="layout-whats-next-view">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Calendar Bot - {display_date or datetime.now().strftime("%A, %B %d")}</title>
    <style>
{css_content}
    </style>
</head>
<body>
    <main class="calendar-content">
{main_content}
    </main>
</body>
</html>"""

        logger.debug(f"Generated standalone HTML: {len(html)} characters")
        return html

    def _generate_inline_css(self) -> str:
        """Generate inline CSS for the What's Next view.

        Returns:
            CSS content as string
        """
        # Colors from SharedStylingConstants
        background = self._colors.get("background", "#ffffff")
        background_secondary = self._colors.get("background_secondary", "#f5f5f5")
        text_primary = self._colors.get("text_primary", "#000000")
        text_secondary = self._colors.get("text_secondary", "#666666")
        text_supporting = self._colors.get("text_supporting", "#999999")
        accent = self._colors.get("accent", "#007bff")

        css = f"""
/* Reset and base styles */
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background-color: {background};
    color: {text_primary};
    line-height: 1.4;
    padding: 20px;
    width: 400px;
    height: 300px;
    overflow: hidden;
}}

.calendar-content {{
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}}

/* No events styling */
.no-events {{
    text-align: center;
    padding: 40px 20px;
}}

.no-events-icon {{
    font-size: 48px;
    margin-bottom: 16px;
}}

.no-events h2 {{
    font-size: 24px;
    font-weight: 600;
    color: {text_primary};
    margin-bottom: 8px;
}}

.no-events p {{
    font-size: 16px;
    color: {text_secondary};
}}

/* Next event styling */
.next-event {{
    background: {background};
    border: 2px solid {text_primary};
    border-radius: 12px;
    padding: 20px;
    margin: 10px;
    width: calc(100% - 40px);
    max-width: 320px;
}}

.event-title {{
    font-size: 18px;
    font-weight: 600;
    color: {text_primary};
    margin-bottom: 8px;
    line-height: 1.3;
}}

.event-time {{
    font-size: 14px;
    color: {text_secondary};
    margin-bottom: 6px;
}}

.event-location {{
    font-size: 12px;
    color: {text_supporting};
    margin-bottom: 8px;
}}

.time-until {{
    background: {background_secondary};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    font-weight: 500;
    color: {text_primary};
    text-align: center;
    margin-top: 8px;
}}

.time-until.urgent {{
    background: {accent};
    color: {background};
}}

/* Countdown styling */
.countdown-section {{
    text-align: center;
    background: {background_secondary};
    border-radius: 12px;
    padding: 20px;
    margin: 10px;
    width: calc(100% - 40px);
    max-width: 320px;
}}

.countdown-text {{
    font-size: 20px;
    font-weight: 700;
    color: {text_primary};
    margin-bottom: 4px;
}}

.countdown-subtitle {{
    font-size: 14px;
    color: {text_secondary};
}}

/* Status message */
.status-message {{
    text-align: center;
    font-size: 12px;
    color: {text_supporting};
    margin-top: 10px;
    padding: 4px 8px;
    background: {background_secondary};
    border-radius: 6px;
}}
"""

        return css  # noqa: RET504

    def _generate_main_content(self, next_event: Optional[Any], status_message: str) -> str:
        """Generate main content HTML.

        Args:
            next_event: Next event data
            status_message: Status message to display

        Returns:
            Main content HTML
        """
        if not next_event:
            # No events case
            content = """
        <div class="no-events">
            <div class="no-events-icon">🎉</div>
            <h2>No meetings scheduled!</h2>
            <p>Enjoy your free time.</p>
        </div>"""
        else:
            # Format event information
            event_title = self._escape_html(getattr(next_event, "subject", "Untitled Event"))
            if len(event_title) > 30:
                event_title = event_title[:30] + "..."

            # Time information
            time_range = ""
            if hasattr(next_event, "formatted_time_range"):
                time_range = next_event.formatted_time_range
            elif hasattr(next_event, "format_time_range"):
                time_range = next_event.format_time_range()

            # Location information
            location_html = ""
            if hasattr(next_event, "location") and next_event.location:
                location = self._escape_html(next_event.location)
                if len(location) > 25:
                    location = location[:25] + "..."
                location_html = f'<div class="event-location">📍 {location}</div>'

            # Time until start
            time_until_html = ""
            if hasattr(next_event, "time_until_minutes"):
                minutes = next_event.time_until_minutes
                if minutes is not None:
                    if minutes <= 5:
                        urgency_class = " urgent"
                        time_text = f"🔔 Starting in {minutes} minutes!"
                    elif minutes <= 60:
                        urgency_class = ""
                        time_text = f"⏰ Starts in {minutes} minutes"
                    else:
                        hours = minutes // 60
                        remaining_mins = minutes % 60
                        if remaining_mins == 0:
                            time_text = f"📅 Starts in {hours} hours"
                        else:
                            time_text = f"📅 Starts in {hours}h {remaining_mins}m"
                        urgency_class = ""

                    time_until_html = f'<div class="time-until{urgency_class}">{time_text}</div>'

            content = f"""
        <div class="next-event">
            <div class="event-title">{event_title}</div>
            <div class="event-time">{time_range}</div>
            {location_html}
            {time_until_html}
        </div>"""

        # Add status message if provided
        if status_message:
            status_html = f'<div class="status-message">{self._escape_html(status_message)}</div>'
            content += status_html

        return content

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters.

        Args:
            text: Text to escape

        Returns:
            HTML-escaped text
        """
        if not text:
            return ""

        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )


def create_standalone_html_renderer() -> StandaloneHtmlRenderer:
    """Create a standalone HTML renderer instance.

    Returns:
        StandaloneHtmlRenderer instance
    """
    return StandaloneHtmlRenderer()
