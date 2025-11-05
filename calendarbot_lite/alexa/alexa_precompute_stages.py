"""Precomputation stages for Alexa responses.

This module provides pipeline stages that precompute Alexa responses during
event window refresh, allowing handlers to serve precomputed responses
for common queries without reprocessing events.

The precomputed responses are stored in context.extra["precomputed_responses"]
and can be accessed by handlers to provide <10ms response times.
"""

from __future__ import annotations

import datetime
import logging
from typing import Optional

from calendarbot_lite.alexa.alexa_protocols import (
    DurationFormatter,
    ISOSerializer,
    SkippedStore,
    TimeProvider,
    TimezoneGetter,
)
from calendarbot_lite.calendar.lite_models import LiteCalendarEvent
from calendarbot_lite.core.timezone_utils import parse_request_timezone
from calendarbot_lite.domain.pipeline import (
    EventProcessingPipeline,
    ProcessingContext,
    ProcessingResult,
)

logger = logging.getLogger(__name__)


class NextMeetingPrecomputeStage:
    """Precompute next meeting response for default timezone.

    This stage finds the next upcoming meeting and generates a response
    compatible with the NextMeetingHandler, caching it for quick retrieval.
    """

    def __init__(
        self,
        default_tz: str,
        time_provider: TimeProvider,
        skipped_store: Optional[SkippedStore] = None,
        duration_formatter: Optional[DurationFormatter] = None,
        iso_serializer: Optional[ISOSerializer] = None,
    ):
        """Initialize next meeting precompute stage.

        Args:
            default_tz: Default timezone for precomputation (e.g., "America/Los_Angeles")
            time_provider: Callable that returns current UTC time
            skipped_store: Optional store for skipped events
            duration_formatter: Function to format duration for speech
            iso_serializer: Function to serialize datetime to ISO string
        """
        self.default_tz = default_tz
        self.time_provider = time_provider
        self.skipped_store = skipped_store
        self.duration_formatter = duration_formatter
        self.iso_serializer = iso_serializer
        self._name = "NextMeetingPrecompute"

    @property
    def name(self) -> str:
        """Name of this processing stage."""
        return self._name

    def _is_skipped(self, event: LiteCalendarEvent) -> bool:
        """Check if event is marked as skipped."""
        if not self.skipped_store:
            return False
        try:
            return self.skipped_store.is_skipped(event.id)
        except Exception as e:
            logger.warning("Failed to check if event %s is skipped: %s", event.id, e)
            return False

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Precompute next meeting response.

        Args:
            context: Processing context with events

        Returns:
            Processing result (events unchanged, response in extra)
        """
        result = ProcessingResult(
            stage_name=self.name,
            events_in=len(context.events),
            events_out=len(context.events),
        )

        try:
            now = self.time_provider()
            next_meeting = None
            seconds_until = 0

            # Find next non-skipped meeting
            for event in context.events:
                if not isinstance(event.start.date_time, datetime.datetime):
                    continue

                event_seconds_until = int((event.start.date_time - now).total_seconds())

                # Skip past events
                if event_seconds_until < 0:
                    continue

                # Skip if marked as skipped
                if self._is_skipped(event):
                    continue

                # Found next meeting
                next_meeting = event
                seconds_until = event_seconds_until
                break

            # Build precomputed response
            if next_meeting:
                # Format duration if formatter available
                if self.duration_formatter and isinstance(
                    next_meeting.end.date_time, datetime.datetime
                ):
                    duration_seconds = int(
                        (next_meeting.end.date_time - next_meeting.start.date_time).total_seconds()
                    )
                    duration_spoken = self.duration_formatter(duration_seconds)
                else:
                    duration_spoken = ""

                # Serialize ISO if serializer available
                start_iso = (
                    self.iso_serializer(next_meeting.start.date_time)
                    if self.iso_serializer
                    else next_meeting.start.date_time.isoformat()
                )

                response = {
                    "meeting": {
                        "subject": next_meeting.subject or "Untitled",
                        "start_iso": start_iso,
                        "seconds_until_start": seconds_until,
                        "duration_spoken": duration_spoken,
                    },
                    "speech_text": f"Your next meeting is {next_meeting.subject}",
                }
            else:
                response = {
                    "meeting": None,  # type: ignore[dict-item]
                    "speech_text": "No upcoming meetings",
                }

            # Store in context
            if "precomputed_responses" not in context.extra:
                context.extra["precomputed_responses"] = {}

            cache_key = f"NextMeetingHandler:{self.default_tz}"
            context.extra["precomputed_responses"][cache_key] = response

            logger.debug(
                "Precomputed next meeting for tz=%s: %s",
                self.default_tz,
                "found" if next_meeting else "none",
            )
            result.success = True
            result.metadata["precomputed_key"] = cache_key
            result.metadata["has_meeting"] = next_meeting is not None

        except Exception as e:
            result.add_error(f"Precomputation failed: {e}")
            logger.exception("Error precomputing next meeting")

        return result


class TimeUntilPrecomputeStage:
    """Precompute time until next meeting for default timezone.

    This stage computes when the next meeting starts, optimized
    for the TimeUntilHandler endpoint.
    """

    def __init__(
        self,
        default_tz: str,
        time_provider: TimeProvider,
        skipped_store: Optional[SkippedStore] = None,
        duration_formatter: Optional[DurationFormatter] = None,
    ):
        """Initialize time until precompute stage.

        Args:
            default_tz: Default timezone for precomputation
            time_provider: Callable that returns current UTC time
            skipped_store: Optional store for skipped events
            duration_formatter: Function to format duration for speech
        """
        self.default_tz = default_tz
        self.time_provider = time_provider
        self.skipped_store = skipped_store
        self.duration_formatter = duration_formatter
        self._name = "TimeUntilPrecompute"

    @property
    def name(self) -> str:
        """Name of this processing stage."""
        return self._name

    def _is_skipped(self, event: LiteCalendarEvent) -> bool:
        """Check if event is marked as skipped."""
        if not self.skipped_store:
            return False
        try:
            return self.skipped_store.is_skipped(event.id)
        except Exception as e:
            logger.warning("Failed to check if event %s is skipped: %s", event.id, e)
            return False

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Precompute time until next meeting.

        Args:
            context: Processing context with events

        Returns:
            Processing result (events unchanged, response in extra)
        """
        result = ProcessingResult(
            stage_name=self.name,
            events_in=len(context.events),
            events_out=len(context.events),
        )

        try:
            now = self.time_provider()
            seconds_until = None
            duration_spoken = ""

            # Find next non-skipped meeting
            for event in context.events:
                if not isinstance(event.start.date_time, datetime.datetime):
                    continue

                event_seconds_until = int((event.start.date_time - now).total_seconds())

                # Skip past events
                if event_seconds_until < 0:
                    continue

                # Skip if marked as skipped
                if self._is_skipped(event):
                    continue

                # Found next meeting
                seconds_until = event_seconds_until
                if self.duration_formatter:
                    duration_spoken = self.duration_formatter(seconds_until)
                break

            # Build precomputed response
            if seconds_until is not None:
                response = {
                    "seconds_until_start": seconds_until,
                    "duration_spoken": duration_spoken,
                    "speech_text": f"Your next meeting is {duration_spoken}",
                }
            else:
                response = {
                    "seconds_until_start": None,
                    "duration_spoken": "",
                    "speech_text": "No upcoming meetings",
                }

            # Store in context
            if "precomputed_responses" not in context.extra:
                context.extra["precomputed_responses"] = {}

            cache_key = f"TimeUntilHandler:{self.default_tz}"
            context.extra["precomputed_responses"][cache_key] = response

            logger.debug(
                "Precomputed time until for tz=%s: %s",
                self.default_tz,
                "found" if seconds_until is not None else "none",
            )
            result.success = True
            result.metadata["precomputed_key"] = cache_key
            result.metadata["has_meeting"] = seconds_until is not None

        except Exception as e:
            result.add_error(f"Precomputation failed: {e}")
            logger.exception("Error precomputing time until")

        return result


class DoneForDayPrecomputeStage:
    """Precompute done-for-day response for default timezone.

    This stage determines when the user will be done with meetings today
    and generates a response compatible with the DoneForDayHandler.
    """

    def __init__(
        self,
        default_tz: str,
        time_provider: TimeProvider,
        skipped_store: Optional[SkippedStore] = None,
        iso_serializer: Optional[ISOSerializer] = None,
        get_server_timezone: Optional[TimezoneGetter] = None,
    ):
        """Initialize done-for-day precompute stage.

        Args:
            default_tz: Default timezone for precomputation
            time_provider: Callable that returns current UTC time
            skipped_store: Optional store for skipped events
            iso_serializer: Function to serialize datetime to ISO string
            get_server_timezone: Function to get server timezone
        """
        self.default_tz = default_tz
        self.time_provider = time_provider
        self.skipped_store = skipped_store
        self.iso_serializer = iso_serializer
        self.get_server_timezone = get_server_timezone
        self._name = "DoneForDayPrecompute"

    @property
    def name(self) -> str:
        """Name of this processing stage."""
        return self._name

    def _is_skipped(self, event: LiteCalendarEvent) -> bool:
        """Check if event is marked as skipped."""
        if not self.skipped_store:
            return False
        try:
            return self.skipped_store.is_skipped(event.id)
        except Exception as e:
            logger.warning("Failed to check if event %s is skipped: %s", event.id, e)
            return False

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Precompute done-for-day response.

        Args:
            context: Processing context with events

        Returns:
            Processing result (events unchanged, response in extra)
        """
        result = ProcessingResult(
            stage_name=self.name,
            events_in=len(context.events),
            events_out=len(context.events),
        )

        try:
            now = self.time_provider()
            tz = parse_request_timezone(self.default_tz)
            today_start = now.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + datetime.timedelta(days=1)

            # Find last meeting ending today
            last_meeting_end = None
            last_meeting_start = None
            has_meetings_today = False

            for event in context.events:
                if not isinstance(event.end.date_time, datetime.datetime):
                    continue

                # Skip if marked as skipped
                if self._is_skipped(event):
                    continue

                event_end = event.end.date_time
                event_start = event.start.date_time

                # Check if meeting ends today
                if today_start <= event_end < today_end:
                    has_meetings_today = True
                    if last_meeting_end is None or event_end > last_meeting_end:
                        last_meeting_end = event_end
                        last_meeting_start = event_start

            # Build precomputed response
            if has_meetings_today and last_meeting_end:
                # Serialize times
                last_end_iso = (
                    self.iso_serializer(last_meeting_end)
                    if self.iso_serializer
                    else last_meeting_end.isoformat()
                )
                last_start_iso = (
                    self.iso_serializer(last_meeting_start)
                    if self.iso_serializer and last_meeting_start
                    else last_meeting_start.isoformat()
                    if last_meeting_start
                    else None
                )

                # Get local time
                last_end_local = last_meeting_end.astimezone(tz)

                response = {
                    "has_meetings_today": True,
                    "last_meeting_end_iso": last_end_iso,
                    "last_meeting_start_iso": last_start_iso,
                    "last_meeting_end_local_iso": last_end_local.isoformat(),
                    "speech_text": f"You'll be done at {last_end_local.strftime('%I:%M %p')}",
                }
            else:
                response = {
                    "has_meetings_today": False,
                    "last_meeting_end_iso": None,
                    "last_meeting_start_iso": None,
                    "last_meeting_end_local_iso": None,
                    "speech_text": "You have no meetings today",
                }

            # Store in context
            if "precomputed_responses" not in context.extra:
                context.extra["precomputed_responses"] = {}

            cache_key = f"DoneForDayHandler:{self.default_tz}"
            context.extra["precomputed_responses"][cache_key] = response

            logger.debug(
                "Precomputed done-for-day for tz=%s: %s",
                self.default_tz,
                "meetings today" if has_meetings_today else "no meetings",
            )
            result.success = True
            result.metadata["precomputed_key"] = cache_key
            result.metadata["has_meetings_today"] = has_meetings_today

        except Exception as e:
            result.add_error(f"Precomputation failed: {e}")
            logger.exception("Error precomputing done-for-day")

        return result


def create_alexa_precompute_pipeline(
    skipped_store: Optional[SkippedStore],
    default_tz: str,
    time_provider: TimeProvider,
    duration_formatter: Optional[DurationFormatter] = None,
    iso_serializer: Optional[ISOSerializer] = None,
    get_server_timezone: Optional[TimezoneGetter] = None,
) -> EventProcessingPipeline:
    """Create pipeline for precomputing Alexa responses.

    Args:
        skipped_store: Optional store for skipped events
        default_tz: Default timezone for precomputation (e.g., "America/Los_Angeles")
        time_provider: Callable that returns current UTC time
        duration_formatter: Function to format duration for speech
        iso_serializer: Function to serialize datetime to ISO string
        get_server_timezone: Function to get server timezone

    Returns:
        EventProcessingPipeline configured with precomputation stages

    Example:
        pipeline = create_alexa_precompute_pipeline(
            skipped_store=store,
            default_tz="America/Los_Angeles",
            time_provider=lambda: datetime.datetime.now(datetime.timezone.utc)
        )

        context = ProcessingContext(events=event_list)
        result = await pipeline.process(context)

        # Access precomputed responses
        responses = context.extra.get("precomputed_responses", {})
        next_meeting = responses.get("NextMeetingHandler:America/Los_Angeles")
    """
    from calendarbot_lite.domain.pipeline import EventProcessingPipeline

    pipeline = EventProcessingPipeline()

    # Add precomputation stages for common queries
    pipeline.add_stage(
        NextMeetingPrecomputeStage(
            default_tz=default_tz,
            time_provider=time_provider,
            skipped_store=skipped_store,
            duration_formatter=duration_formatter,
            iso_serializer=iso_serializer,
        )
    )

    pipeline.add_stage(
        TimeUntilPrecomputeStage(
            default_tz=default_tz,
            time_provider=time_provider,
            skipped_store=skipped_store,
            duration_formatter=duration_formatter,
        )
    )

    pipeline.add_stage(
        DoneForDayPrecomputeStage(
            default_tz=default_tz,
            time_provider=time_provider,
            skipped_store=skipped_store,
            iso_serializer=iso_serializer,
            get_server_timezone=get_server_timezone,
        )
    )

    logger.debug("Created Alexa precompute pipeline with %d stages", len(pipeline.stages))
    return pipeline
