"""Business logic for What's Next view, separated from presentation layer."""

import logging
from datetime import datetime
from typing import Any, Optional

from ..cache.models import CachedEvent
from ..utils.helpers import get_timezone_aware_now
from .whats_next_data_model import EventData, StatusInfo, WhatsNextViewModel

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
            return self._debug_time

        return get_timezone_aware_now()

    def create_view_model(
        self, events: list[CachedEvent], status_info: Optional[dict[str, Any]] = None
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
        # 4x8 view enhancement: consolidate all upcoming events into next_events, eliminate later_events
        next_event_data = [EventData.from_cached_event(e, current_time) for e in upcoming_events]
        later_event_data = []  # No longer used in 4x8 view - all events consolidated into next_events

        # Format display date
        display_date = self._format_display_date(status_info, current_time)

        # Create status info
        status = self._create_status_info(status_info, current_time)

        # Create and return view model
        return WhatsNextViewModel(
            current_time=current_time,
            display_date=display_date,
            next_events=next_event_data,
            current_events=current_event_data,
            later_events=later_event_data,
            status_info=status,
        )

    def _group_events(
        self, events: list[CachedEvent], current_time: datetime
    ) -> tuple[list[CachedEvent], list[CachedEvent], list[CachedEvent]]:
        """Group events into current, upcoming, and later categories.

        Prioritizes upcoming meetings over current meetings - when both exist,
        upcoming meetings are selected for display. Falls back to current
        meetings only when no upcoming meetings are available.

        Args:
            events: List of cached events
            current_time: Current time reference

        Returns:
            Tuple of (current_events, upcoming_events, later_events)
        """
        if not events:
            return [], [], []

        # Filter out hidden events
        visible_events = []
        if hasattr(self.settings, "event_filters") and hasattr(
            self.settings.event_filters, "hidden_events"
        ):
            hidden_events = self.settings.event_filters.hidden_events

            # Get matching events to log their titles
            matching_hidden = [e for e in events if e.graph_id in hidden_events]
            hidden_titles = [e.subject[:50] if e.subject else "No title" for e in matching_hidden]
            logger.debug(f"WhatsNext filtering - hidden event titles: {hidden_titles}")

            logger.debug(f"WhatsNext filtering - total events before filter: {len(events)}")
            visible_events = [e for e in events if e.graph_id not in hidden_events]
            filtered_count = len(events) - len(visible_events)
            logger.debug(
                f"WhatsNext filtering - events filtered out: {filtered_count}, visible events: {len(visible_events)}"
            )
            if filtered_count > 0:
                # Log titles instead of IDs for better readability
                filtered_titles = [
                    e.subject[:50] if e.subject else "No title" for e in matching_hidden
                ]
                logger.info(
                    f"WhatsNext filtered out {filtered_count} hidden events: {filtered_titles}"
                )
        else:
            logger.debug("WhatsNext filtering - no hidden_events found in settings")
            visible_events = events

        # Find current events (happening now)
        current_events = [e for e in visible_events if e.is_current()]

        # Find upcoming events (not started yet)
        upcoming_events = [e for e in visible_events if e.start_dt > current_time]
        upcoming_events.sort(key=lambda e: e.start_dt)  # Sort by start time

        # Remaining upcoming events are "later today"
        later_events = upcoming_events[3:] if len(upcoming_events) > 3 else []

        # CORE BUSINESS RULE: Prioritize upcoming meetings over current meetings
        # When both current and upcoming meetings exist, select upcoming for display
        if upcoming_events:
            logger.debug(
                f"Meeting selection: Prioritizing upcoming meetings - found {len(upcoming_events)} upcoming, "
                f"{len(current_events)} current. Selecting upcoming."
            )
            # Return empty current_events to prioritize upcoming meetings
            selected_current_events = []
        else:
            logger.debug(
                f"Meeting selection: No upcoming meetings found ({len(upcoming_events)}), "
                f"falling back to current meetings ({len(current_events)})."
            )
            # Fallback to current meetings when no upcoming meetings exist
            selected_current_events = current_events[:1]

        return selected_current_events, upcoming_events, later_events

    def _format_display_date(
        self, status_info: Optional[dict[str, Any]], current_time: datetime
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
        self, status_info: Optional[dict[str, Any]], current_time: datetime
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

    def find_next_upcoming_event(self, events: list[CachedEvent]) -> Optional[CachedEvent]:
        """Find the next single upcoming event after current time.

        Args:
            events: List of events to search

        Returns:
            Next upcoming event or None if no upcoming events found
        """
        try:
            now = self.get_current_time()

            # Apply hidden events filter first - get fresh settings to avoid staleness
            try:
                from ..settings.service import SettingsService  # noqa: PLC0415

                settings_service = SettingsService()
                fresh_settings = settings_service.get_filter_settings()

                if hasattr(fresh_settings, "hidden_events") and fresh_settings.hidden_events:
                    hidden_events = fresh_settings.hidden_events
                    logger.debug(
                        f"find_next_upcoming_event filtering - fresh hidden_events: {list(hidden_events)}"
                    )

                    # Check for matches using the same ID system as frontend
                    matching_events = [e for e in events if e.graph_id in hidden_events]

                    # Log the first 50 characters of titles of hidden events
                    hidden_titles = [
                        e.subject[:50] if e.subject else "No title" for e in matching_events
                    ]
                    logger.debug(
                        f"find_next_upcoming_event filtering - hidden event titles: {hidden_titles}"
                    )

                    # Debug: show actual event IDs that we're using for filtering
                    event_ids = [e.graph_id for e in events[:5]]  # Show first 5 for debugging
                    logger.debug(
                        f"find_next_upcoming_event - sample event IDs being used for filtering: {event_ids}"
                    )

                    logger.debug(
                        f"find_next_upcoming_event - found {len(matching_events)} events to hide: {[e.graph_id for e in matching_events]}"
                    )

                    visible_events = [e for e in events if e.graph_id not in hidden_events]
                    filtered_count = len(events) - len(visible_events)
                    logger.debug(
                        f"find_next_upcoming_event filtered out {filtered_count} hidden events, {len(visible_events)} visible"
                    )
                else:
                    logger.debug(
                        "find_next_upcoming_event - no hidden_events found in fresh settings"
                    )
                    visible_events = events
            except Exception as e:
                logger.warning(f"Failed to get fresh settings for hidden events filtering: {e}")
                # Fallback to original settings
                if hasattr(self.settings, "event_filters") and hasattr(
                    self.settings.event_filters, "hidden_events"
                ):
                    hidden_events = self.settings.event_filters.hidden_events

                    # Get matching events to log their titles for fallback
                    matching_events_fallback = [e for e in events if e.graph_id in hidden_events]
                    hidden_titles_fallback = [
                        e.subject[:50] if e.subject else "No title"
                        for e in matching_events_fallback
                    ]
                    logger.debug(
                        f"find_next_upcoming_event filtering - fallback hidden event titles: {hidden_titles_fallback}"
                    )

                    visible_events = [e for e in events if e.graph_id not in hidden_events]
                    filtered_count = len(events) - len(visible_events)
                    logger.debug(
                        f"find_next_upcoming_event filtered out {filtered_count} hidden events (fallback), {len(visible_events)} visible"
                    )
                else:
                    logger.debug(
                        "find_next_upcoming_event - no hidden_events found in fallback settings"
                    )
                    visible_events = events

            # DEBUG: Log recurring event properties for duplicate investigation
            for event in visible_events:
                if "Product Strategy" in event.subject:
                    logger.debug(
                        f"DUPLICATE DEBUG - Event: {event.subject}, ID: {event.id}, "
                        f"graph_id: {event.graph_id}, is_recurring: {event.is_recurring}, "
                        f"series_master_id: {event.series_master_id}, start: {event.start_dt}"
                    )

            # Filter to only upcoming events (not current)
            upcoming_events = [e for e in visible_events if e.start_dt > now]

            if not upcoming_events:
                return None

            # Sort by start time and return the first (earliest)
            upcoming_events.sort(key=lambda e: e.start_dt)
            next_event = upcoming_events[0]

            logger.debug(
                f"Found next upcoming event: {next_event.subject} at {next_event.start_dt}"
            )
            return next_event

        except Exception:
            logger.exception("Error finding next upcoming event")
            return None
