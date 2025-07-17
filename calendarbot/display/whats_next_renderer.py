"""What's Next renderer for displaying only the next single upcoming event."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..cache.models import CachedEvent
from .html_renderer import HTMLRenderer

logger = logging.getLogger(__name__)


class WhatsNextRenderer(HTMLRenderer):
    """Renders calendar events using the What's Next layout showing only the next upcoming event.

    Extends HTMLRenderer to provide specialized filtering that shows:
    - Only the next single upcoming event after current time
    - Maintains existing HTML structure for frontend compatibility
    - Optimized for whats-next-view layout
    """

    def __init__(self, settings: Any) -> None:
        """Initialize What's Next renderer.

        Args:
            settings: Application settings
        """
        super().__init__(settings)
        logger.info("WhatsNextRenderer initialized")

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
            # Filter to find the next single upcoming event
            next_event = self._find_next_upcoming_event(events)

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

    def _find_next_upcoming_event(self, events: List[CachedEvent]) -> Optional[CachedEvent]:
        """Find the next single upcoming event after current time.

        Args:
            events: List of events to search

        Returns:
            Next upcoming event or None if no upcoming events found
        """
        try:
            from ..utils.helpers import get_timezone_aware_now

            # Use debug time override if available, otherwise use real time
            if hasattr(self, "_debug_time") and self._debug_time:
                now = self._debug_time
                logger.debug(
                    f"DIAGNOSTIC WHATS_NEXT: Using DEBUG TIME override for filtering: {now}"
                )
            else:
                now = get_timezone_aware_now()
                logger.debug(f"DIAGNOSTIC WHATS_NEXT: Using REAL TIME for filtering: {now}")

            logger.debug(f"DIAGNOSTIC WHATS_NEXT: Current time for filtering: {now}")
            logger.debug(f"DIAGNOSTIC WHATS_NEXT: Total events to filter: {len(events)}")

            # Log all events with their times for debugging
            for i, event in enumerate(events):
                logger.debug(
                    f"DIAGNOSTIC WHATS_NEXT: Event {i}: {event.subject} | Start: {event.start_dt} | Current: {event.is_current()}"
                )
                logger.debug(
                    f"DIAGNOSTIC WHATS_NEXT: Event {i} start > now? {event.start_dt > now}"
                )

            # Filter to only upcoming events (not current)
            upcoming_events = [e for e in events if e.start_dt > now]

            logger.debug(
                f"DIAGNOSTIC WHATS_NEXT: Upcoming events after filtering: {len(upcoming_events)}"
            )

            if not upcoming_events:
                logger.debug(
                    "DIAGNOSTIC WHATS_NEXT: No upcoming events found - checking current events"
                )
                current_events = [e for e in events if e.is_current()]
                logger.debug(f"DIAGNOSTIC WHATS_NEXT: Current events found: {len(current_events)}")
                return None

            # Sort by start time and return the first (earliest)
            upcoming_events.sort(key=lambda e: e.start_dt)
            next_event = upcoming_events[0]

            logger.debug(
                f"DIAGNOSTIC WHATS_NEXT: Found next upcoming event: {next_event.subject} at {next_event.start_dt}"
            )
            return next_event

        except Exception as e:
            logger.error(f"Error finding next upcoming event: {e}")
            return None

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

        # Store debug_time for use in _find_next_upcoming_event
        self._debug_time = debug_time

        # Use the parent implementation but with our overridden _render_events_content
        try:
            return super().render_events(events, status_info)
        except Exception as e:
            logger.error(f"Error in WhatsNextRenderer.render_events: {e}")
            return self._render_error_html(f"Error rendering What's Next view: {e}")
        finally:
            # Clean up debug_time after rendering
            self._debug_time = None
