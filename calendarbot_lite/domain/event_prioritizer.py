"""Event prioritization logic for whats-next endpoint."""

from __future__ import annotations

import datetime
import logging
from enum import Enum
from typing import Any

from calendarbot_lite.calendar.lite_models import LiteCalendarEvent
from calendarbot_lite.domain.skipped_store import is_event_skipped

logger = logging.getLogger(__name__)

# Type alias for backwards compatibility (deprecated - use LiteCalendarEvent)
EventDict = dict[str, Any]


class EventCategory(Enum):
    """Categories for event prioritization."""

    BUSINESS = "business"
    LUNCH = "lunch"
    FOCUS_TIME = "focus_time"


class EventPrioritizer:
    """Prioritizes events for the whats-next endpoint with business logic."""

    def __init__(self, focus_time_checker: Any):
        """Initialize event prioritizer.

        Args:
            focus_time_checker: Callable that checks if event is focus time
        """
        self.is_focus_time_event = focus_time_checker
        self.time_grouping_threshold_seconds = 1800  # 30 minutes

    def find_next_event(
        self,
        events: tuple[LiteCalendarEvent, ...],
        now: datetime.datetime,
        skipped_store: object | None,
    ) -> tuple[LiteCalendarEvent, int] | None:
        """Find the next event to show, applying prioritization logic.

        Business rules:
        1. Skip events in the past
        2. Skip focus time events
        3. Skip user-skipped events
        4. If multiple events occur at similar time (within 30 min), prioritize business over lunch

        Args:
            events: Tuple of LiteCalendarEvent objects
            now: Current time
            skipped_store: Optional skipped store

        Returns:
            Tuple of (event, seconds_until) or None if no events found
        """
        candidate_events: list[tuple[LiteCalendarEvent, int]] = []

        for i, ev in enumerate(events):
            logger.debug(" Checking event %d - ID: %r, Start: %r", i, ev.id, ev.start.date_time)

            start = ev.start.date_time
            if not isinstance(start, datetime.datetime):
                continue

            seconds_until = int((start - now).total_seconds())

            # Skip past events
            if seconds_until < 0:
                continue

            # Skip focus time events
            if self.is_focus_time_event(ev):
                logger.debug("Skipping focus time event: %r", ev.subject)
                continue

            # Skip user-skipped events
            if is_event_skipped(ev.id, skipped_store):
                continue

            candidate_events.append((ev, seconds_until))

        # If no candidates found, return None
        if not candidate_events:
            return None

        # Sort candidates by time (earliest first)
        candidate_events.sort(key=lambda x: x[1])

        # Apply priority logic to events that start at similar time to the earliest event
        earliest_time = candidate_events[0][1]
        early_group = [
            (ev, secs)
            for ev, secs in candidate_events
            if abs(secs - earliest_time) <= self.time_grouping_threshold_seconds
        ]

        # If there are multiple events at similar time, apply prioritization
        if len(early_group) > 1:
            logger.debug(
                "PRIORITY: Multiple events at similar time to earliest, applying prioritization"
            )
            priority_result = self._apply_priority_early_group(early_group)
            if priority_result:
                return priority_result

        # Return earliest event
        return candidate_events[0]

    def _apply_priority_early_group(
        self,
        early_group: list[tuple[LiteCalendarEvent, int]],
    ) -> tuple[LiteCalendarEvent, int] | None:
        """Apply prioritization logic to a group of events at similar times.

        Args:
            early_group: List of (event, seconds_until) tuples at similar times

        Returns:
            Selected (event, seconds_until) or None if no prioritization needed
        """
        # Categorize events
        business_events = []
        lunch_events = []

        for cand_ev, cand_seconds in early_group:
            category = self._categorize_event(cand_ev)

            if category == EventCategory.LUNCH:
                lunch_events.append((cand_ev, cand_seconds))
                logger.debug("PRIORITY: Categorized as lunch event: %s", cand_ev.subject or "")
            else:
                business_events.append((cand_ev, cand_seconds))
                logger.debug("PRIORITY: Categorized as business event: %s", cand_ev.subject or "")

        # Prioritize business events over lunch
        if business_events:
            # Sort business events by time and take the earliest
            business_events.sort(key=lambda x: x[1])
            selected_ev, selected_seconds = business_events[0]
            logger.debug("PRIORITY: Selected earliest business event over lunch")
            return selected_ev, selected_seconds

        # No business events, use first available
        selected_ev, selected_seconds = early_group[0]
        logger.debug("PRIORITY: No business events found, using first available")
        return selected_ev, selected_seconds

    def _categorize_event(self, event: LiteCalendarEvent) -> EventCategory:
        """Categorize event as business or lunch.

        Args:
            event: LiteCalendarEvent object

        Returns:
            EventCategory enum value
        """
        subject = (event.subject or "").lower()

        # Check for generic lunch events (short subject containing "lunch")
        if "lunch" in subject and len(subject) <= 10:
            return EventCategory.LUNCH

        return EventCategory.BUSINESS
