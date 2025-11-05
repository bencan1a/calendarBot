"""Event merging and deduplication for ICS calendar processing - CalendarBot Lite.

This module handles merging expanded recurring events with original events,
RECURRENCE-ID override processing, and event deduplication.
Extracted from lite_parser.py to improve modularity and testability.
"""

import logging
from typing import Optional

from .lite_models import LiteCalendarEvent

logger = logging.getLogger(__name__)


class LiteEventMerger:
    """Handles merging, deduplication, and RECURRENCE-ID override logic for calendar events."""

    def merge_expanded_events(
        self,
        original_events: list[LiteCalendarEvent],
        expanded_events: list[LiteCalendarEvent],
    ) -> list[LiteCalendarEvent]:
        """Merge expanded events with original events.

        This method handles the complex logic of:
        1. Identifying RECURRENCE-ID overrides (moved/modified recurring instances)
        2. Suppressing expanded occurrences that have been overridden
        3. Merging original and expanded events intelligently

        Args:
            original_events: Original parsed events (including RECURRENCE-ID instances)
            expanded_events: Expanded recurring event instances from RRULE

        Returns:
            Combined list of events with overrides properly handled
        """
        # First, collect RECURRENCE-ID events and their original times for suppression
        recurrence_overrides = self._collect_recurrence_overrides(original_events)

        # Filter expanded events to exclude those overridden by RECURRENCE-ID
        filtered_expanded, suppressed_count = self._filter_overridden_occurrences(
            expanded_events, recurrence_overrides
        )

        if suppressed_count > 0:
            logger.info(
                f"RECURRENCE-ID processing: Suppressed {suppressed_count} expanded occurrences "
                f"that were overridden by moved meetings"
            )

        # Start with filtered expanded events (suppressed overrides removed)
        merged_events = filtered_expanded.copy()

        # Create a set of master UIDs that were successfully expanded
        expanded_master_uids = {
            getattr(event, "rrule_master_uid", None)
            for event in filtered_expanded
            if getattr(event, "rrule_master_uid", None)
        }

        # Add original events, but skip recurring masters that were successfully expanded
        for event in original_events:
            if event.is_recurring:
                # Keep recurring masters that weren't expanded (e.g., due to unsupported RRULE)
                if event.id not in expanded_master_uids:
                    merged_events.append(event)
            else:
                # Always keep non-recurring events (including moved instances with RECURRENCE-ID)
                # Modified instances have recurrence_id set and should be included
                merged_events.append(event)

        logger.debug(
            f"Merged {len(original_events)} original + {len(filtered_expanded)} expanded = {len(merged_events)} total events"
        )
        return merged_events

    def _collect_recurrence_overrides(
        self, events: list[LiteCalendarEvent]
    ) -> dict[tuple[str, str], LiteCalendarEvent]:
        """Collect RECURRENCE-ID events and their original times for override processing.

        RECURRENCE-ID indicates that a specific instance of a recurring event has been
        moved or modified. We need to suppress the original expanded occurrence and
        use the modified one instead.

        Args:
            events: List of events to scan for RECURRENCE-ID markers

        Returns:
            Dictionary mapping (master_uid, original_time) -> moved_event
        """
        recurrence_overrides: dict[tuple[str, str], LiteCalendarEvent] = {}

        for event in events:
            if hasattr(event, "recurrence_id") and event.recurrence_id:
                # Extract master UID from the event
                master_uid = self._extract_master_uid(event.id)

                # Parse the RECURRENCE-ID to get the original time being overridden
                original_time = self._parse_recurrence_id_time(event.recurrence_id)

                if original_time:
                    # Create a key for the original time slot being overridden
                    override_key = (master_uid, original_time)
                    recurrence_overrides[override_key] = event

                    logger.debug(
                        f"RECURRENCE-ID override detected: {event.subject} "
                        f"moves {original_time} to {event.start.date_time.strftime('%Y%m%dT%H%M%S')}"
                    )

        return recurrence_overrides

    def _extract_master_uid(self, event_id: str) -> str:
        """Extract master UID from event ID.

        Event IDs may contain delimiters (:: or _) separating the master UID
        from instance-specific information.

        Args:
            event_id: Event ID to extract master UID from

        Returns:
            Master UID (first part before delimiter)
        """
        if "::" in event_id:
            return event_id.split("::")[0]
        if "_" in event_id:
            return event_id.split("_")[0]
        return event_id

    def _parse_recurrence_id_time(self, recurrence_id: str) -> Optional[str]:
        """Parse RECURRENCE-ID to extract the original time being overridden.

        RECURRENCE-ID format can be:
        - "TZID=Pacific Standard Time:20251028T143000"
        - "20251028T143000Z"
        - "20251028T143000"

        Args:
            recurrence_id: RECURRENCE-ID string

        Returns:
            Datetime part as string (e.g., "20251028T143000") or None if parsing fails
        """
        try:
            recurrence_id_str = str(recurrence_id)

            if ":" in recurrence_id_str and "T" in recurrence_id_str:
                # Extract the datetime part after the colon (handles TZID format)
                datetime_part = recurrence_id_str.split(":")[-1]  # "20251028T143000"
                # Remove trailing 'Z' if present
                return datetime_part.rstrip("Z")
            if "T" in recurrence_id_str:
                # No TZID, just datetime
                return recurrence_id_str.rstrip("Z")
            logger.warning(f"Unexpected RECURRENCE-ID format: {recurrence_id}")
            return None

        except Exception as e:
            logger.warning(f"Failed to parse RECURRENCE-ID {recurrence_id}: {e}")
            return None

    def _filter_overridden_occurrences(
        self,
        expanded_events: list[LiteCalendarEvent],
        recurrence_overrides: dict[tuple[str, str], LiteCalendarEvent],
    ) -> tuple[list[LiteCalendarEvent], int]:
        """Filter expanded events to exclude those overridden by RECURRENCE-ID.

        Args:
            expanded_events: List of expanded recurring event instances
            recurrence_overrides: Dictionary of RECURRENCE-ID overrides

        Returns:
            Tuple of (filtered_events, suppressed_count)
        """
        filtered_expanded = []
        suppressed_count = 0

        for event in expanded_events:
            master_uid = getattr(event, "rrule_master_uid", None)
            if master_uid and hasattr(event, "start") and event.start:
                # Create key for this expanded occurrence
                event_time_key = event.start.date_time.strftime("%Y%m%dT%H%M%S")
                override_key = (master_uid, event_time_key)

                if override_key in recurrence_overrides:
                    # This expanded occurrence is overridden by a RECURRENCE-ID event
                    override_event = recurrence_overrides[override_key]
                    logger.debug(
                        f"Suppressing expanded occurrence: {event.subject} at {event_time_key} "
                        f"(overridden by RECURRENCE-ID event at {override_event.start.date_time})"
                    )
                    suppressed_count += 1
                    continue

            filtered_expanded.append(event)

        return filtered_expanded, suppressed_count

    def deduplicate_events(
        self, events: list[LiteCalendarEvent]
    ) -> list[LiteCalendarEvent]:
        """Remove duplicate events based on UID and start time.

        Events are considered duplicates if they have the same:
        - UID (event.id)
        - Subject
        - Start time (as ISO string)
        - End time (as ISO string)
        - All-day flag
        - RECURRENCE-ID (if present)

        Modified recurring instances with different RECURRENCE-IDs are NOT
        considered duplicates, even if they have the same UID and times.

        Args:
            events: List of calendar events to deduplicate

        Returns:
            Deduplicated list of events
        """
        seen = set()
        deduplicated = []

        for event in events:
            # Create a unique key based on UID, start time, and basic properties
            # Two events with different UIDs are by definition different events,
            # even if they have the same subject and time (e.g., two separate recurring series)
            # Use start time as string to avoid timezone comparison issues
            # Include recurrence_id to prevent deduplicating modified recurring instances (issue #45)
            recurrence_id = getattr(event, "recurrence_id", None)
            key = (
                event.id,  # Include UID to avoid incorrectly deduplicating separate events
                event.subject,
                event.start.date_time.isoformat(),
                event.end.date_time.isoformat(),
                event.is_all_day,
                recurrence_id,  # Include RECURRENCE-ID to distinguish modified instances
            )

            if key not in seen:
                seen.add(key)
                deduplicated.append(event)

        if len(events) != len(deduplicated):
            logger.debug(f"Removed {len(events) - len(deduplicated)} duplicate events")

        return deduplicated
