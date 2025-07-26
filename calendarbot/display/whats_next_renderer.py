"""What's Next renderer for displaying only the next single upcoming event."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..cache.models import CachedEvent
from .html_renderer import HTMLRenderer
from .renderer_interface import InteractionEvent, RendererInterface
from .whats_next_data_model import EventData, WhatsNextViewModel
from .whats_next_logic import WhatsNextLogic

logger = logging.getLogger(__name__)


class WhatsNextRenderer(HTMLRenderer, RendererInterface):
    """Renders calendar events using the What's Next layout showing only the next upcoming event.

    Extends HTMLRenderer to provide specialized filtering that shows:
    - Only the next single upcoming event after current time
    - Maintains existing HTML structure for frontend compatibility
    - Optimized for whats-next-view layout
    - Implements RendererInterface for compatibility with e-Paper renderer
    """

    def __init__(self, settings: Any) -> None:
        """Initialize What's Next renderer.

        Args:
            settings: Application settings
        """
        super().__init__(settings)
        # Initialize business logic
        self.logic = WhatsNextLogic(settings)
        logger.info("WhatsNextRenderer initialized with shared logic")

    # RendererInterface implementation
    def render(self, view_model: WhatsNextViewModel) -> str:
        """Render the view model to HTML format.

        Args:
            view_model: Data model containing all information needed for rendering

        Returns:
            Rendered HTML output
        """
        logger.debug("WhatsNextRenderer.render called with view model")

        # Extract status info for parent class compatibility
        status_info = {
            "last_update": view_model.status_info.last_update.isoformat(),
            "is_cached": view_model.status_info.is_cached,
            "connection_status": view_model.status_info.connection_status,
            "relative_description": view_model.status_info.relative_description,
            "interactive_mode": view_model.status_info.interactive_mode,
            "selected_date": view_model.status_info.selected_date,
        }

        # Render events content from view model
        events_html = self._render_events_from_view_model(view_model)

        # Use the parent HTML renderer to build full page structure
        # This maintains compatibility with existing HTML structure and CSS
        return self._render_full_page_html(
            events_content=events_html,
            status_info=status_info,
            current_time=view_model.current_time,
            display_date=view_model.display_date,
        )

    def _render_full_page_html(
        self,
        events_content: str,
        status_info: Dict[str, Any],
        current_time: datetime,
        display_date: str,
    ) -> str:
        """Render full page HTML using parent class structure.

        Args:
            events_content: Pre-rendered events HTML content
            status_info: Status information dictionary
            current_time: Current time
            display_date: Display date string

        Returns:
            Complete HTML page
        """
        try:
            # Build main content
            main_content = f"""
            <div class="calendar-container whats-next-theme">
                <div class="header">
                    <h1>📅 {self._escape_html(display_date)}</h1>
                    <div class="time-display">{current_time.strftime('%I:%M %p')}</div>
                </div>
                {events_content}
            </div>
            """

            # Build status footer
            status_html = f"""
            <div class="status-footer">
                <p>Last updated: {status_info.get('relative_description', 'now')}</p>
                {f'<p>Status: {status_info["connection_status"]}</p>' if status_info.get('connection_status') else ''}
            </div>
            """

            # Combine and wrap in full HTML document
            body_content = main_content + status_html
            return self._wrap_html_document(body_content, f"Calendar - {display_date}")

        except Exception as e:
            logger.error(f"Error building full page HTML: {e}")
            return self._render_error_html(f"Error rendering page: {e}")

    def _wrap_html_document(self, body_content: str, title: str) -> str:
        """Wrap content in full HTML document.

        Args:
            body_content: HTML content for body
            title: Page title

        Returns:
            Complete HTML document
        """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._escape_html(title)}</title>
    <style>
    {self._get_css_styles()}
    </style>
</head>
<body>
    {body_content}
</body>
</html>"""

    def _get_css_styles(self) -> str:
        """Get CSS styles for the page.

        Returns:
            CSS styles string
        """
        return """
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .calendar-container { background: white; border-radius: 8px; padding: 20px; max-width: 800px; margin: 0 auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; border-bottom: 2px solid #ddd; padding-bottom: 15px; margin-bottom: 20px; }
        .header h1 { margin: 0; color: #333; }
        .time-display { font-size: 1.2em; color: #666; margin-top: 10px; }
        .current-events, .upcoming-events, .later-events { margin: 20px 0; }
        .section-title { color: #444; border-bottom: 1px solid #eee; padding-bottom: 5px; }
        .current-event, .upcoming-event { background: #f9f9f9; border: 1px solid #ddd; border-radius: 6px; padding: 15px; margin: 10px 0; }
        .current-event { background: #e8f5e8; border-color: #4CAF50; }
        .event-title { margin: 0 0 8px 0; font-weight: bold; color: #333; }
        .event-time { margin: 5px 0; color: #666; font-size: 0.9em; }
        .event-location { margin: 5px 0; color: #888; font-size: 0.9em; }
        .event-duration { margin: 5px 0; color: #888; font-size: 0.9em; }
        .no-events { text-align: center; padding: 40px; color: #666; }
        .no-events-icon { font-size: 3em; margin-bottom: 15px; }
        .status-footer { margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee; font-size: 0.9em; color: #666; text-align: center; }
        .error { background: #ffebee; border: 1px solid #f44336; color: #c62828; padding: 15px; border-radius: 6px; margin: 10px 0; }
        """

    def _render_events_from_view_model(self, view_model: WhatsNextViewModel) -> str:
        """Render events section from view model EventData objects.

        Args:
            view_model: View model containing EventData objects

        Returns:
            HTML content for events
        """
        if not view_model.has_events():
            return """
            <div class="no-events">
                <div class="no-events-icon">🎉</div>
                <h2>No meetings scheduled!</h2>
                <p>Enjoy your free time.</p>
            </div>
            """

        content_parts = []

        # Current events
        if view_model.current_events:
            content_parts.append('<section class="current-events">')
            content_parts.append('<h2 class="section-title">▶ Current Event</h2>')
            for event in view_model.current_events:
                content_parts.append(self._format_event_data_html(event, is_current=True))
            content_parts.append("</section>")

        # Next events (upcoming)
        if view_model.next_events:
            content_parts.append('<section class="upcoming-events">')
            content_parts.append('<h2 class="section-title">📋 What\'s Next</h2>')
            for event in view_model.next_events:
                content_parts.append(self._format_event_data_html(event, is_current=False))
            content_parts.append("</section>")

        # Later events
        if view_model.later_events:
            content_parts.append('<section class="later-events">')
            content_parts.append('<h2 class="section-title">📅 Later Today</h2>')
            for event in view_model.later_events:
                content_parts.append(self._format_event_data_html(event, is_current=False))
            content_parts.append("</section>")

        return "\n".join(content_parts)

    def _format_event_data_html(self, event: EventData, is_current: bool) -> str:
        """Format an EventData object as HTML.

        Args:
            event: EventData object to format
            is_current: Whether this is a current event

        Returns:
            HTML string for the event
        """
        try:
            # Build event HTML similar to existing format
            event_class = "current-event" if is_current else "upcoming-event"

            html_parts = [f'<div class="{event_class}">']

            # Event title
            html_parts.append(f'<h3 class="event-title">{self._escape_html(event.subject)}</h3>')

            # Time information
            time_info = event.formatted_time_range
            if event.time_until_minutes and not is_current:
                time_info += f" (in {event.time_until_minutes} min)"
            html_parts.append(f'<p class="event-time">{self._escape_html(time_info)}</p>')

            # Location if available
            if event.location:
                html_parts.append(
                    f'<p class="event-location">📍 {self._escape_html(event.location)}</p>'
                )

            # Duration
            if event.duration_minutes:
                duration_text = f"{event.duration_minutes} min"
                html_parts.append(f'<p class="event-duration">⏱️ {duration_text}</p>')

            html_parts.append("</div>")

            return "\n".join(html_parts)

        except Exception as e:
            logger.error(f"Error formatting EventData: {e}")
            return f'<div class="error">Error formatting event: {self._escape_html(str(e))}</div>'

    def handle_interaction(self, interaction: InteractionEvent) -> None:
        """Handle user interactions.

        Args:
            interaction: Interaction event to handle
        """
        logger.debug(f"WhatsNextRenderer.handle_interaction called with {interaction.event_type}")
        # Web renderer doesn't need to handle interactions directly
        # as they are handled by JavaScript in the browser
        pass

    def update_display(self, content: str) -> bool:
        """Update the display with rendered content.

        Args:
            content: Rendered HTML content

        Returns:
            True if update was successful, False otherwise
        """
        # Web renderer doesn't need to update display directly
        # as the content is returned to the web server
        return True

    def _render_events_content(self, events: List[CachedEvent], interactive_mode: bool) -> str:
        """Render events content filtered to show only the next upcoming event.

        Args:
            events: List of events to render
            interactive_mode: Whether in interactive mode

        Returns:
            HTML content for events showing only next upcoming event
        """
        logger.debug(f"WhatsNextRenderer filtering {len(events)} events to next single event")

        if not events:
            return """
            <div class="no-events">
                <div class="no-events-icon">🎉</div>
                <h2>No meetings scheduled!</h2>
                <p>Enjoy your free time.</p>
            </div>
            """

        try:
            # Use shared logic to find the next upcoming event
            next_event = self.logic.find_next_upcoming_event(events)

            if not next_event:
                # Check if there's a current event
                current_events = [e for e in events if e.is_current()]
                if current_events:
                    # Show current event as the "what's next"
                    logger.debug("No upcoming events found, showing current event")
                    return self._render_single_event_content(current_events[0], is_current=True)
                else:
                    # No current or upcoming events
                    return """
                    <div class="no-events">
                        <div class="no-events-icon">📅</div>
                        <h2>No upcoming meetings!</h2>
                        <p>Your schedule is clear.</p>
                    </div>
                    """

            logger.debug(f"Rendering next event: {next_event.subject}")
            return self._render_single_event_content(next_event, is_current=False)

        except Exception as e:
            logger.error(f"Error filtering events in WhatsNextRenderer: {e}")
            # Fallback to parent implementation
            return super()._render_events_content(events, interactive_mode)

    # This method is removed as it's now part of WhatsNextLogic
    # _find_next_upcoming_event is replaced by logic.find_next_upcoming_event

    def _render_single_event_content(self, event: CachedEvent, is_current: bool) -> str:
        """Render content for a single event.

        Args:
            event: Event to render
            is_current: True if this is a current event, False if upcoming

        Returns:
            HTML content for the single event
        """
        try:
            if is_current:
                # Use existing current event formatting
                content_parts = ['<section class="current-events">']
                content_parts.append('<h2 class="section-title">▶ Current Event</h2>')
                content_parts.append(self._format_current_event_html(event))
                content_parts.append("</section>")
            else:
                # Format as upcoming event but as the main focus
                content_parts = ['<section class="upcoming-events">']
                content_parts.append('<h2 class="section-title">📋 What\'s Next</h2>')
                content_parts.append(self._format_upcoming_event_html(event))
                content_parts.append("</section>")

            return "\n".join(content_parts)

        except Exception as e:
            logger.error(f"Error rendering single event content: {e}")
            return f'<div class="error">Error rendering event: {self._escape_html(str(e))}</div>'

    def render_events(
        self,
        events: List[CachedEvent],
        status_info: Optional[Dict[str, Any]] = None,
        debug_time: Optional[datetime] = None,
    ) -> str:
        """Render events to formatted HTML output for What's Next view.

        Args:
            events: List of cached events to display
            status_info: Additional status information
            debug_time: Optional time override for debug mode

        Returns:
            Formatted HTML string for What's Next display
        """
        logger.debug(f"WhatsNextRenderer.render_events called with {len(events)} events")
        if debug_time:
            logger.debug(f"WhatsNextRenderer: Using debug time override: {debug_time.isoformat()}")

        # Pass debug_time to the logic component
        self.logic.set_debug_time(debug_time)

        # Use the parent implementation but with our overridden _render_events_content
        try:
            return super().render_events(events, status_info)
        except Exception as e:
            logger.error(f"Error in WhatsNextRenderer.render_events: {e}")
            return self._render_error_html(f"Error rendering What's Next view: {e}")
        finally:
            # Clean up debug_time after rendering
            self.logic.set_debug_time(None)
