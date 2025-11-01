"""Event prioritization logic for whats-next endpoint."""

from __future__ import annotations

import datetime
import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# Type alias for event dictionaries
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
        events: tuple[EventDict, ...],
        now: datetime.datetime,
        skipped_store: object | None,
    ) -> tuple[EventDict, int] | None:
        """Find the next event to show, applying prioritization logic.

        Business rules:
        1. Skip events in the past
        2. Skip focus time events
        3. Skip user-skipped events
        4. If multiple events occur at similar time (within 30 min), prioritize business over lunch

        Args:
            events: Tuple of event dictionaries
            now: Current time
            skipped_store: Optional skipped store

        Returns:
            Tuple of (event, seconds_until) or None if no events found
        """
        candidate_events: list[tuple[EventDict, int]] = []

        for i, ev in enumerate(events):
            logger.debug(" Checking event %d - ID: %r, Start: %r", i, ev.get("meeting_id"), ev.get("start"))

            start = ev.get("start")
            if not isinstance(start, datetime.datetime):
                continue

            seconds_until = int((start - now).total_seconds())

            # Skip past events
            if seconds_until < 0:
                continue

            # Skip focus time events
            if self.is_focus_time_event(ev):
                logger.debug("Skipping focus time event: %r", ev.get("subject"))
                continue

            # Skip user-skipped events
            if self._is_skipped(ev, skipped_store):
                continue

            candidate_events.append((ev, seconds_until))

            # Check for time-based grouping and prioritization
            if len(candidate_events) >= 2:
                priority_result = self._apply_priority_logic(candidate_events, seconds_until)
                if priority_result:
                    return priority_result

        # Return first qualifying event if no prioritization was applied
        if candidate_events:
            return candidate_events[0]

        return None

    def _is_skipped(self, event: EventDict, skipped_store: object | None) -> bool:
        """Check if event is skipped by user.

        Args:
            event: Event dictionary
            skipped_store: Optional skipped store

        Returns:
            True if event is skipped, False otherwise
        """
        if skipped_store is None:
            return False

        is_skipped_fn = getattr(skipped_store, "is_skipped", None)
        if not callable(is_skipped_fn):
            return False

        try:
            return is_skipped_fn(event["meeting_id"])
        except Exception as e:
            logger.warning("skipped_store.is_skipped raised: %s", e)
            return False

    def _apply_priority_logic(
        self,
        candidate_events: list[tuple[EventDict, int]],
        current_seconds_until: int,
    ) -> tuple[EventDict, int] | None:
        """Apply prioritization logic when multiple events occur at similar time.

        Args:
            candidate_events: List of (event, seconds_until) tuples
            current_seconds_until: Seconds until current event

        Returns:
            Selected (event, seconds_until) or None if no prioritization needed
        """
        # Group events by time (within threshold)
        current_time_group = [candidate_events[-1]]  # Latest event

        for prev_ev, prev_seconds in candidate_events[:-1]:
            if abs(current_seconds_until - prev_seconds) <= self.time_grouping_threshold_seconds:
                current_time_group.append((prev_ev, prev_seconds))

        # Only apply prioritization if we have multiple events at similar time
        if len(current_time_group) <= 1:
            return None

        logger.debug("PRIORITY: Multiple events at similar time, applying prioritization")

        # Categorize events
        business_events = []
        lunch_events = []

        for cand_ev, cand_seconds in current_time_group:
            category = self._categorize_event(cand_ev)

            if category == EventCategory.LUNCH:
                lunch_events.append((cand_ev, cand_seconds))
                logger.debug(f"PRIORITY: Categorized as lunch event: {cand_ev.get('subject', '')}")
            else:
                business_events.append((cand_ev, cand_seconds))
                logger.debug(f"PRIORITY: Categorized as business event: {cand_ev.get('subject', '')}")

        # Prioritize business events over lunch
        if business_events:
            # Sort business events by time and take the earliest
            business_events.sort(key=lambda x: x[1])
            selected_ev, selected_seconds = business_events[0]
            logger.debug("PRIORITY: Selected earliest business event over lunch")
            return selected_ev, selected_seconds

        # No business events, use first available
        selected_ev, selected_seconds = current_time_group[0]
        logger.debug("PRIORITY: No business events found, using first available")
        return selected_ev, selected_seconds

    def _categorize_event(self, event: EventDict) -> EventCategory:
        """Categorize event as business or lunch.

        Args:
            event: Event dictionary

        Returns:
            EventCategory enum value
        """
        subject = event.get("subject", "").lower()

        # Check for generic lunch events (short subject containing "lunch")
        if "lunch" in subject and len(subject) <= 10:
            return EventCategory.LUNCH

        return EventCategory.BUSINESS
