"""Business logic for What's Next view, separated from presentation layer."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..cache.models import CachedEvent
from ..utils.helpers import get_timezone_aware_now
from .whats_next_data_model import EventData, StatusInfo, WeatherData, WhatsNextViewModel

logger = logging.getLogger(__name__)


class WhatsNextLogic:
    """Business logic for What's Next view that can be shared across renderers."""

    def __init__(self, settings: Any) -> None:
        """Initialize What's Next logic.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self._debug_time: Optional[datetime] = None
        logger.info("WhatsNextLogic initialized")

    def set_debug_time(self, debug_time: Optional[datetime]) -> None:
        """Set debug time override for testing.

        Args:
            debug_time: Debug time override or None to use real time
        """
        self._debug_time = debug_time
        if debug_time:
            logger.debug(f"WhatsNextLogic: Using debug time override: {debug_time.isoformat()}")

    def get_current_time(self) -> datetime:
        """Get current time, respecting debug time override if set.

        Returns:
            Current time or debug time if set
        """
        if self._debug_time:
            logger.debug(f"DIAGNOSTIC WHATS_NEXT: Using DEBUG TIME override: {self._debug_time}")
            return self._debug_time

        now = get_timezone_aware_now()
        logger.debug(f"DIAGNOSTIC WHATS_NEXT: Using REAL TIME: {now}")
        return now

    def create_view_model(
        self, events: List[CachedEvent], status_info: Optional[Dict[str, Any]] = None
    ) -> WhatsNextViewModel:
        """Create view model from events and status info.

        Args:
            events: List of cached events
            status_info: Additional status information

        Returns:
            WhatsNextViewModel instance
        """
        current_time = self.get_current_time()

        # Group events by type
        current_events, upcoming_events, later_events = self._group_events(events, current_time)

        # Convert to EventData objects
        current_event_data = [EventData.from_cached_event(e, current_time) for e in current_events]
        next_event_data = [
            EventData.from_cached_event(e, current_time) for e in upcoming_events[:3]
        ]
        later_event_data = [
            EventData.from_cached_event(e, current_time) for e in upcoming_events[3:8]
        ]

        # Format display date
        display_date = self._format_display_date(status_info, current_time)

        # Create status info
        status = self._create_status_info(status_info, current_time)

        # Create view model
        view_model = WhatsNextViewModel(
            current_time=current_time,
            display_date=display_date,
            next_events=next_event_data,
            current_events=current_event_data,
            later_events=later_event_data,
            status_info=status,
        )

        return view_model

    def _group_events(
        self, events: List[CachedEvent], current_time: datetime
    ) -> Tuple[List[CachedEvent], List[CachedEvent], List[CachedEvent]]:
        """Group events into current, upcoming, and later categories.

        Args:
            events: List of cached events
            current_time: Current time reference

        Returns:
            Tuple of (current_events, upcoming_events, later_events)
        """
        if not events:
            return [], [], []

        # Find current events (happening now)
        current_events = [e for e in events if e.is_current()]

        # Find upcoming events (not started yet)
        upcoming_events = [e for e in events if e.start_dt > current_time]
        upcoming_events.sort(key=lambda e: e.start_dt)  # Sort by start time

        # First 3 upcoming events are "next up"
        next_up_events = upcoming_events[:3] if upcoming_events else []

        # Remaining upcoming events are "later today"
        later_events = upcoming_events[3:] if len(upcoming_events) > 3 else []

        logger.debug(
            f"DIAGNOSTIC WHATS_NEXT: Grouped events - "
            f"Current: {len(current_events)}, Next: {len(next_up_events)}, Later: {len(later_events)}"
        )

        return current_events[:1], upcoming_events, later_events

    def _format_display_date(
        self, status_info: Optional[Dict[str, Any]], current_time: datetime
    ) -> str:
        """Format display date string.

        Args:
            status_info: Status information
            current_time: Current time reference

        Returns:
            Formatted date string
        """
        if status_info and status_info.get("selected_date"):
            # Add type assertion to ensure return value is str
            selected_date: str = str(status_info["selected_date"])
            return selected_date

        return current_time.strftime("%A, %B %d")

    def _create_status_info(
        self, status_info: Optional[Dict[str, Any]], current_time: datetime
    ) -> StatusInfo:
        """Create StatusInfo from raw status info.

        Args:
            status_info: Raw status information
            current_time: Current time reference

        Returns:
            StatusInfo instance
        """
        return StatusInfo(
            last_update=current_time,
            is_cached=status_info.get("is_cached", False) if status_info else False,
            connection_status=status_info.get("connection_status") if status_info else None,
            relative_description=status_info.get("relative_description") if status_info else None,
            interactive_mode=status_info.get("interactive_mode", False) if status_info else False,
            selected_date=status_info.get("selected_date") if status_info else None,
        )

    def find_next_upcoming_event(self, events: List[CachedEvent]) -> Optional[CachedEvent]:
        """Find the next single upcoming event after current time.

        Args:
            events: List of events to search

        Returns:
            Next upcoming event or None if no upcoming events found
        """
        try:
            now = self.get_current_time()
            logger.debug(f"DIAGNOSTIC WHATS_NEXT: Current time for filtering: {now}")
            logger.debug(f"DIAGNOSTIC WHATS_NEXT: Total events to filter: {len(events)}")

            # Log all events with their times for debugging
            for i, event in enumerate(events):
                logger.debug(
                    f"DIAGNOSTIC WHATS_NEXT: Event {i}: {event.subject} | "
                    f"Start: {event.start_dt} | Current: {event.is_current()}"
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
                f"DIAGNOSTIC WHATS_NEXT: Found next upcoming event: "
                f"{next_event.subject} at {next_event.start_dt}"
            )
            return next_event

        except Exception as e:
            logger.error(f"Error finding next upcoming event: {e}")
            return None
