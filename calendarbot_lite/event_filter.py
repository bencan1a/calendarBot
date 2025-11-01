"""Event filtering and window management for calendarbot_lite server."""

from __future__ import annotations

import datetime
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Type alias for event dictionaries
EventDict = dict[str, Any]


class SmartFallbackHandler:
    """Handles smart fallback logic when source fetching fails or returns suspicious results."""

    def should_preserve_existing_window(
        self,
        parsed_events: list[EventDict],
        existing_count: int,
        sources_count: int,
    ) -> tuple[bool, str]:
        """Determine if existing window should be preserved based on fetch results.

        Args:
            parsed_events: Events parsed from sources
            existing_count: Number of events in existing window
            sources_count: Number of configured sources

        Returns:
            Tuple of (should_preserve, reason_message)
        """
        # Case 1: All sources failed - preserve existing window
        if not parsed_events:
            if existing_count > 0:
                reason = (
                    f"All {sources_count} ICS sources failed - preserving {existing_count} "
                    f"existing events to avoid clearing display"
                )
                return True, reason
            reason = "All sources failed and no cached events available"
            return False, reason

        # Case 2: Sources returned 0 events but we had events before (suspicious)
        if len(parsed_events) == 0 and existing_count > 0:
            reason = (
                f"Suspicious 0 events from 'successful' parsing when we had {existing_count} "
                f"events before. This likely indicates network corruption that bypassed "
                f"failure detection. Preserving existing window."
            )
            return True, reason

        # No fallback needed
        return False, "Processing new events normally"


class EventFilter:
    """Filters events based on time, timezone, and skip status."""

    def __init__(self, server_timezone_getter: Any, fallback_timezone_getter: Any):
        """Initialize event filter.

        Args:
            server_timezone_getter: Callable that returns server timezone name
            fallback_timezone_getter: Callable that returns fallback timezone name
        """
        self.get_server_timezone = server_timezone_getter
        self.get_fallback_timezone = fallback_timezone_getter

    def filter_upcoming_events(
        self,
        events: list[EventDict],
        now: datetime.datetime,
    ) -> list[EventDict]:
        """Filter events to include only those in the future.

        Handles both timezone-aware and timezone-naive datetime objects safely.

        Args:
            events: List of event dictionaries
            now: Current time (timezone-aware)

        Returns:
            List of events that start in the future
        """
        upcoming = []
        server_tz_name = self.get_server_timezone()

        for e in events:
            start_dt = e.get("start")
            if not isinstance(start_dt, datetime.datetime):
                continue

            # Make timezone-aware if needed
            try:
                start_dt_aware = self._make_timezone_aware(start_dt, server_tz_name)

                # Compare timezone-aware datetimes
                if start_dt_aware >= now:
                    upcoming.append(e)

            except Exception as ex:
                logger.warning("Failed to process event start time %s: %s", start_dt, ex)
                continue

        return upcoming

    def _make_timezone_aware(
        self,
        dt: datetime.datetime,
        server_tz_name: str,
    ) -> datetime.datetime:
        """Convert datetime to timezone-aware if needed.

        Args:
            dt: Datetime to process
            server_tz_name: Server timezone name

        Returns:
            Timezone-aware datetime
        """
        if dt.tzinfo is not None:
            # Already timezone-aware
            return dt

        # Event is timezone-naive - assume it's in server timezone
        try:
            import zoneinfo
            server_tz = zoneinfo.ZoneInfo(server_tz_name)
            return dt.replace(tzinfo=server_tz)
        except Exception:
            # Fallback to fallback timezone
            fallback_tz_name = self.get_fallback_timezone()
            try:
                import zoneinfo
                fallback_tz = zoneinfo.ZoneInfo(fallback_tz_name)
                return dt.replace(tzinfo=fallback_tz)
            except Exception:
                # Last resort: treat as UTC
                return dt.replace(tzinfo=datetime.timezone.utc)

    def filter_skipped_events(
        self,
        events: list[EventDict],
        skipped_store: object | None,
    ) -> list[EventDict]:
        """Filter out events that have been skipped by the user.

        Args:
            events: List of event dictionaries
            skipped_store: Optional skipped store object with is_skipped method

        Returns:
            List of events excluding skipped ones
        """
        if skipped_store is None:
            return events

        is_skipped_fn = getattr(skipped_store, "is_skipped", None)
        if not callable(is_skipped_fn):
            return events

        try:
            return [e for e in events if not is_skipped_fn(e["meeting_id"])]
        except Exception as e:
            logger.warning("skipped_store.is_skipped raised: %s", e)
            return events

    def sort_and_limit_events(
        self,
        events: list[EventDict],
        window_size: int,
    ) -> list[EventDict]:
        """Sort events by start time and limit to window size.

        Args:
            events: List of event dictionaries
            window_size: Maximum number of events to keep

        Returns:
            Sorted and limited list of events
        """
        sorted_events = sorted(events, key=lambda e: e["start"])
        return sorted_events[:window_size]


class EventWindowManager:
    """Manages the in-memory event window with atomic updates."""

    def __init__(
        self,
        event_filter: EventFilter,
        fallback_handler: SmartFallbackHandler,
    ):
        """Initialize event window manager.

        Args:
            event_filter: EventFilter instance for filtering events
            fallback_handler: SmartFallbackHandler for smart fallback logic
        """
        self.event_filter = event_filter
        self.fallback_handler = fallback_handler

    async def update_window(
        self,
        event_window_ref: list[tuple[EventDict, ...]],
        window_lock: Any,
        parsed_events: list[EventDict],
        now: datetime.datetime,
        skipped_store: object | None,
        window_size: int,
        sources_count: int,
    ) -> tuple[bool, int, str]:
        """Update event window with new events, applying smart fallback logic.

        Args:
            event_window_ref: Reference to event window (single-element list)
            window_lock: Asyncio lock for thread-safe updates
            parsed_events: Events parsed from sources
            now: Current time
            skipped_store: Optional skipped store
            window_size: Maximum window size
            sources_count: Number of configured sources

        Returns:
            Tuple of (updated, final_count, message)
            - updated: True if window was updated, False if preserved
            - final_count: Number of events in window after operation
            - message: Descriptive message about the operation
        """
        # Get current window state
        async with window_lock:
            existing_window = event_window_ref[0]
            existing_count = len(existing_window)

        # Check if we should preserve existing window
        should_preserve, reason = self.fallback_handler.should_preserve_existing_window(
            parsed_events, existing_count, sources_count
        )

        if should_preserve:
            logger.info("Smart fallback: %s", reason)
            return False, existing_count, reason

        # Process new events: filter, sort, and limit
        upcoming = self.event_filter.filter_upcoming_events(parsed_events, now)
        filtered = self.event_filter.filter_skipped_events(upcoming, skipped_store)
        final_events = self.event_filter.sort_and_limit_events(filtered, window_size)

        # Update window atomically
        async with window_lock:
            event_window_ref[0] = tuple(final_events)

        message = f"Updated window with {len(final_events)} events (from {len(parsed_events)} parsed)"
        return True, len(final_events), message
