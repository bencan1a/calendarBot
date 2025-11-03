"""Concrete implementations of pipeline stages for event processing.

This module provides stage implementations that wrap existing calendarbot_lite
functionality into the EventProcessor protocol. These stages can be composed
into an EventProcessingPipeline for flexible event processing.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from .lite_models import LiteCalendarEvent
from .pipeline import ProcessingContext, ProcessingResult

if TYPE_CHECKING:
    from .pipeline import EventProcessingPipeline

logger = logging.getLogger(__name__)


class DeduplicationStage:
    """Remove duplicate events based on UID.

    Wraps the existing deduplication logic from lite_parser.
    """

    def __init__(self) -> None:
        """Initialize deduplication stage."""
        self._name = "Deduplication"

    @property
    def name(self) -> str:
        """Stage name for logging."""
        return self._name

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Remove duplicate events from context.events.

        Args:
            context: Processing context with events

        Returns:
            Result with deduplicated events
        """
        result = ProcessingResult(
            stage_name=self.name,
            events_in=len(context.events),
        )

        try:
            # Track events by UID
            unique_events: dict[str, LiteCalendarEvent] = {}

            for event in context.events:
                if event.id not in unique_events:
                    unique_events[event.id] = event
                else:
                    # Keep the event with more information (attendees, body, etc.)
                    existing = unique_events[event.id]
                    if self._has_more_info(event, existing):
                        unique_events[event.id] = event

            # Update context with deduplicated events
            deduplicated = list(unique_events.values())
            context.events = sorted(deduplicated, key=lambda e: e.start.date_time)

            result.events = context.events
            result.events_out = len(context.events)
            result.events_filtered = result.events_in - result.events_out
            result.success = True

            if result.events_filtered > 0:
                logger.debug(
                    f"Deduplication: {result.events_in} → {result.events_out} events "
                    f"({result.events_filtered} duplicates removed)"
                )
            else:
                logger.debug(
                    f"Deduplication: {result.events_in} events (no duplicates found)"
                )

            return result

        except Exception as e:
            result.add_error(f"Deduplication failed: {e}")
            logger.exception("Deduplication stage failed")
            return result

    def _has_more_info(
        self, event1: LiteCalendarEvent, event2: LiteCalendarEvent
    ) -> bool:
        """Determine which event has more information."""
        score1 = self._calculate_info_score(event1)
        score2 = self._calculate_info_score(event2)
        return score1 > score2

    def _calculate_info_score(self, event: LiteCalendarEvent) -> int:
        """Calculate information completeness score for an event."""
        score = 0
        if event.body_preview:
            score += 1
        if event.attendees and len(event.attendees) > 0:
            score += 2
        if event.location:
            score += 1
        if event.online_meeting_url:
            score += 1
        return score


class SkippedEventsFilterStage:
    """Filter out events that the user has marked as skipped.

    Wraps the existing event filtering logic.
    """

    def __init__(self, skipped_event_ids: Optional[set[str]] = None) -> None:
        """Initialize filter stage.

        Args:
            skipped_event_ids: Set of event IDs to skip
        """
        self._name = "SkippedEventsFilter"
        self.skipped_event_ids = skipped_event_ids or set()

    @property
    def name(self) -> str:
        """Stage name for logging."""
        return self._name

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Filter out skipped events from context.events.

        Args:
            context: Processing context with events

        Returns:
            Result with filtered events
        """
        result = ProcessingResult(
            stage_name=self.name,
            events_in=len(context.events),
        )

        try:
            # Use skipped IDs from context if available, otherwise use instance default
            skipped_ids = context.skipped_event_ids or self.skipped_event_ids

            if not skipped_ids:
                # No filtering needed
                result.events = context.events
                result.events_out = len(context.events)
                result.success = True
                return result

            # Filter out skipped events
            filtered = [
                event
                for event in context.events
                if event.id not in skipped_ids
            ]

            context.events = filtered
            result.events = filtered
            result.events_out = len(filtered)
            result.events_filtered = result.events_in - result.events_out
            result.success = True

            if result.events_filtered > 0:
                logger.info(
                    f"Filtered out {result.events_filtered} skipped events"
                )

            return result

        except Exception as e:
            result.add_error(f"Event filtering failed: {e}")
            logger.exception("Skipped events filter stage failed")
            return result


class TimeWindowStage:
    """Filter events to a specific time window.

    Keeps only events within the specified time range.
    """

    def __init__(self) -> None:
        """Initialize time window stage."""
        self._name = "TimeWindow"

    @property
    def name(self) -> str:
        """Stage name for logging."""
        return self._name

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Filter events to time window from context.

        Args:
            context: Processing context with window_start and window_end

        Returns:
            Result with windowed events
        """
        result = ProcessingResult(
            stage_name=self.name,
            events_in=len(context.events),
        )

        try:
            # If no window specified, keep all events
            if not context.window_start and not context.window_end:
                result.events = context.events
                result.events_out = len(context.events)
                result.success = True
                return result

            # Filter events to time window
            windowed = []
            for event in context.events:
                event_time = event.start.date_time

                # Check if event is within window
                if context.window_start and event_time < context.window_start:
                    continue
                if context.window_end and event_time > context.window_end:
                    continue

                windowed.append(event)

            context.events = windowed
            result.events = windowed
            result.events_out = len(windowed)
            result.events_filtered = result.events_in - result.events_out
            result.success = True

            logger.debug(
                f"Time window: {result.events_in} → {result.events_out} events "
                f"(window: {context.window_start} to {context.window_end})"
            )

            return result

        except Exception as e:
            result.add_error(f"Time window filtering failed: {e}")
            logger.exception("Time window stage failed")
            return result


class EventLimitStage:
    """Limit the number of events to a maximum count.

    Keeps the earliest N events (useful for UI display limits).
    """

    def __init__(self, max_events: Optional[int] = None) -> None:
        """Initialize event limit stage.

        Args:
            max_events: Maximum number of events to keep (None = unlimited)
        """
        self._name = "EventLimit"
        self.max_events = max_events

    @property
    def name(self) -> str:
        """Stage name for logging."""
        return self._name

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Limit events to maximum count.

        Args:
            context: Processing context with events

        Returns:
            Result with limited events
        """
        result = ProcessingResult(
            stage_name=self.name,
            events_in=len(context.events),
        )

        try:
            # Use max_events from context if available, otherwise use instance default
            limit = context.event_window_size if context.event_window_size else self.max_events

            if not limit or len(context.events) <= limit:
                # No limiting needed
                result.events = context.events
                result.events_out = len(context.events)
                result.success = True
                return result

            # Keep first N events (already sorted by time in earlier stages)
            limited = context.events[:limit]
            context.events = limited

            result.events = limited
            result.events_out = len(limited)
            result.events_filtered = result.events_in - result.events_out
            result.success = True

            if result.events_filtered > 0:
                logger.debug(
                    f"Event limit: {result.events_in} → {result.events_out} events (limit={limit})"
                )
            else:
                logger.debug(
                    f"Event limit: {result.events_in} events (under limit={limit})"
                )

            return result

        except Exception as e:
            result.add_error(f"Event limiting failed: {e}")
            logger.exception("Event limit stage failed")
            return result


class ParseStage:
    """Parse ICS content into LiteCalendarEvent objects.

    Wraps LiteICSParser to parse raw ICS content and populate context.events.
    """

    def __init__(self, parser: Any) -> None:
        """Initialize parse stage.

        Args:
            parser: LiteICSParser instance
        """
        self._name = "Parse"
        self.parser = parser

    @property
    def name(self) -> str:
        """Stage name for logging."""
        return self._name

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Parse ICS content from context.raw_content.

        Args:
            context: Processing context with raw_content

        Returns:
            Result with parsed events
        """
        result = ProcessingResult(
            stage_name=self.name,
            events_in=0,
        )

        try:
            if not context.raw_content:
                result.add_error("No raw ICS content to parse")
                return result

            # Parse ICS content using existing parser
            parse_result = self.parser.parse_ics_content_optimized(
                context.raw_content,
                source_url=context.source_url
            )

            if not parse_result.success:
                result.add_error(
                    f"ICS parsing failed: {parse_result.error_message or 'Unknown error'}"
                )
                return result

            # Update context with parsed events
            context.events = parse_result.events or []

            # Build calendar metadata from parse result fields
            context.calendar_metadata = {
                "calendar_name": parse_result.calendar_name,
                "calendar_description": parse_result.calendar_description,
                "timezone": parse_result.timezone,
            }

            result.events = context.events
            result.events_out = len(context.events)
            result.success = True

            # Add parser warnings to result
            if parse_result.warnings:
                for warning in parse_result.warnings:
                    result.add_warning(warning)

            logger.info(
                f"Parsed {result.events_out} events from ICS content "
                f"({len(context.raw_content)} bytes)"
            )

            return result

        except Exception as e:
            result.add_error(f"ICS parsing failed: {e}")
            logger.exception("Parse stage failed")
            return result


class ExpansionStage:
    """Expand recurring events using RRULE patterns.

    Wraps the _expand_recurring_events logic from LiteICSParser.
    """

    def __init__(self, parser: Any) -> None:
        """Initialize expansion stage.

        Args:
            parser: LiteICSParser instance with _expand_recurring_events method
        """
        self._name = "RRULEExpansion"
        self.parser = parser

    @property
    def name(self) -> str:
        """Stage name for logging."""
        return self._name

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Expand recurring events in context.events.

        Args:
            context: Processing context with events and raw_components

        Returns:
            Result with expanded events
        """
        result = ProcessingResult(
            stage_name=self.name,
            events_in=len(context.events),
        )

        try:
            # Check if we have any events to expand
            if not context.events:
                result.events = []
                result.events_out = 0
                result.success = True
                return result

            # Use existing RRULE expansion logic from parser
            # The parser's _expand_recurring_events needs both events and raw components
            if hasattr(self.parser, '_expand_recurring_events'):
                expanded = self.parser._expand_recurring_events(  # noqa: SLF001
                    context.events,
                    context.raw_components
                )
                context.events = expanded
            else:
                # If parser doesn't have expansion method, skip this stage
                result.add_warning("Parser does not support RRULE expansion, skipping")

            result.events = context.events
            result.events_out = len(context.events)
            result.success = True

            expansion_count = result.events_out - result.events_in
            if expansion_count > 0:
                logger.info(
                    f"RRULE expansion: {result.events_in} → {result.events_out} events "
                    f"({expansion_count} instances generated)"
                )

            return result

        except Exception as e:
            result.add_error(f"RRULE expansion failed: {e}")
            logger.exception("Expansion stage failed")
            return result


class SortStage:
    """Sort events by start time.

    Wraps the sorting logic from _finalize_parsing.
    """

    def __init__(self) -> None:
        """Initialize sort stage."""
        self._name = "Sort"

    @property
    def name(self) -> str:
        """Stage name for logging."""
        return self._name

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Sort events by start time.

        Args:
            context: Processing context with events

        Returns:
            Result with sorted events
        """
        result = ProcessingResult(
            stage_name=self.name,
            events_in=len(context.events),
        )

        try:
            # Sort events by start time
            context.events = sorted(
                context.events,
                key=lambda e: e.start.date_time
            )

            result.events = context.events
            result.events_out = len(context.events)
            result.success = True

            logger.debug(f"Sorted {result.events_out} events by start time")

            return result

        except Exception as e:
            result.add_error(f"Event sorting failed: {e}")
            logger.exception("Sort stage failed")
            return result


# Example pipeline factory functions:

def create_basic_pipeline() -> EventProcessingPipeline:
    """Create a basic post-processing pipeline for already-parsed events.

    This pipeline handles deduplication, filtering, windowing, and limiting
    for events that have already been parsed and expanded.

    Use this when you have LiteCalendarEvent objects that need cleanup.

    Returns:
        Configured pipeline ready for processing
    """
    from .pipeline import EventProcessingPipeline

    pipeline = EventProcessingPipeline()

    # Add stages in order
    pipeline.add_stage(DeduplicationStage())
    pipeline.add_stage(SkippedEventsFilterStage())
    pipeline.add_stage(TimeWindowStage())
    pipeline.add_stage(EventLimitStage())

    return pipeline


def create_complete_pipeline(parser: Any) -> EventProcessingPipeline:
    """Create a complete event processing pipeline.

    This pipeline handles the full event processing flow:
    1. Parse ICS content → LiteCalendarEvent objects
    2. Expand recurring events (RRULE)
    3. Deduplicate by event ID
    4. Sort by start time
    5. Filter skipped events
    6. Apply time window
    7. Limit to max events

    Use this for complete ICS-to-events processing.

    Args:
        parser: LiteICSParser instance for parsing and expansion

    Returns:
        Configured pipeline ready for complete processing

    Example:
        >>> from calendarbot_lite.lite_parser import LiteICSParser
        >>> from calendarbot_lite.pipeline import ProcessingContext
        >>>
        >>> parser = LiteICSParser(settings)
        >>> pipeline = create_complete_pipeline(parser)
        >>>
        >>> context = ProcessingContext(
        ...     raw_content=ics_content,
        ...     source_url="https://example.com/calendar.ics",
        ...     skipped_event_ids={"event-123"},
        ...     event_window_size=50
        ... )
        >>> result = await pipeline.process(context)
        >>> events = context.events  # Fully processed events
    """
    from .pipeline import EventProcessingPipeline

    return (
        EventProcessingPipeline()
        .add_stage(ParseStage(parser))
        .add_stage(ExpansionStage(parser))
        .add_stage(DeduplicationStage())
        .add_stage(SortStage())
        .add_stage(SkippedEventsFilterStage())
        .add_stage(TimeWindowStage())
        .add_stage(EventLimitStage())
    )
