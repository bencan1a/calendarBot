"""Consolidated Alexa endpoint handlers with shared logic."""

from __future__ import annotations

import asyncio
import datetime
import logging
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

from aiohttp import web
from pydantic import BaseModel, ValidationError

from calendarbot_lite.alexa.alexa_exceptions import (
    AlexaAuthenticationError,
    AlexaHandlerError,
    AlexaValidationError,
)
from calendarbot_lite.alexa.alexa_models import (
    AlexaRequestParams,
    MorningSummaryRequestParams,
)
from calendarbot_lite.alexa.alexa_types import (
    AlexaDoneForDayInfo,
    AlexaDoneForDayResponse,
    AlexaLaunchSummaryResponse,
    AlexaMeetingInfo,
    AlexaMorningSummaryMetadata,
    AlexaMorningSummaryResponse,
    AlexaNextMeetingResponse,
    AlexaTimeUntilResponse,
)
from calendarbot_lite.calendar.lite_datetime_utils import (
    format_time_cross_platform,
    serialize_datetime_utc,
)
from calendarbot_lite.calendar.lite_models import LiteCalendarEvent
from calendarbot_lite.core.monitoring_logging import get_logger
from calendarbot_lite.core.timezone_utils import parse_request_timezone

logger = logging.getLogger(__name__)
monitoring_logger = get_logger("alexa_handlers")


class AlexaEndpointBase(ABC):
    """Base class for Alexa endpoints with common authentication and meeting search logic."""

    # Subclasses can override this to specify their parameter model
    param_model: type[BaseModel] = AlexaRequestParams

    def __init__(
        self,
        bearer_token: Optional[str],
        time_provider: TimeProvider,
        skipped_store: SkippedStore | None,
        response_cache: Optional[ResponseCache] = None,
    ):
        """Initialize Alexa endpoint handler.

        Args:
            bearer_token: Required bearer token for authentication
            time_provider: Callable that returns current UTC time
            skipped_store: Optional store for skipped events
            response_cache: Optional ResponseCache for caching responses
        """
        self.bearer_token = bearer_token
        self.time_provider = time_provider
        self.skipped_store = skipped_store
        self.response_cache = response_cache

    def validate_params(self, request: web.Request) -> BaseModel:
        """Validate request query parameters using the handler's param model.

        Args:
            request: aiohttp request object

        Returns:
            Validated parameters as a Pydantic model

        Raises:
            AlexaValidationError: If validation fails
        """
        try:
            params = dict(request.query)
            return self.param_model(**params)
        except ValidationError as e:
            raise AlexaValidationError(f"Invalid request parameters: {e}") from e

    def check_auth(self, request: web.Request) -> None:
        """Check if request has valid bearer token.

        Args:
            request: aiohttp request object

        Raises:
            AlexaAuthenticationError: If authentication fails
        """
        if not self.bearer_token:
            return  # No token configured, allow all requests

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise AlexaAuthenticationError("Missing or malformed Authorization header")

        token = auth_header[7:]  # Remove "Bearer " prefix
        if token != self.bearer_token:
            raise AlexaAuthenticationError("Invalid bearer token")

    async def handle(
        self,
        request: web.Request,
        event_window_ref: list[tuple[LiteCalendarEvent, ...]],
        window_lock: asyncio.Lock,
    ) -> web.Response:
        """Main handler with auth check, validation, telemetry, and common setup.

        Args:
            request: aiohttp request object
            event_window_ref: Reference to event window
            window_lock: Lock for thread-safe window access

        Returns:
            aiohttp json response
        """

        # Start timing for telemetry
        start_time = time.time()
        handler_name = self.__class__.__name__

        try:
            # Check authentication - raises AlexaAuthenticationError if invalid
            try:
                self.check_auth(request)
            except AlexaAuthenticationError as e:
                logger.warning("Authentication failed for %s: %s", handler_name, e)
                monitoring_logger.warning(  # noqa: PLE1205
                    "alexa.auth.failed",
                    f"Authentication failed for {handler_name}",
                    details={"handler": handler_name, "error": str(e)},
                )
                return web.json_response({"error": "Unauthorized"}, status=401)

            # Validate request parameters - raises AlexaValidationError if invalid
            try:
                self.validate_params(request)
            except AlexaValidationError as e:
                logger.warning("Validation failed for %s: %s", handler_name, e)
                monitoring_logger.warning(  # noqa: PLE1205
                    "alexa.validation.failed",
                    f"Validation failed for {handler_name}",
                    details={
                        "handler": handler_name,
                        "error": str(e),
                        "params": dict(request.query),
                    },
                )
                return web.json_response({"error": "Bad request", "message": str(e)}, status=400)

            # Check cache before processing (if cache is enabled)
            cache_key = None
            if self.response_cache:
                # Generate cache key from handler name and query params
                params = dict(request.query)
                cache_key = self.response_cache.generate_key(handler_name, params)
                cached = self.response_cache.get(cache_key)
                if cached:
                    logger.debug("Cache hit for %s", handler_name)
                    latency_ms = (time.time() - start_time) * 1000
                    monitoring_logger.info(  # noqa: PLE1205
                        "alexa.request.completed",
                        f"Request completed for {handler_name}",
                        details={
                            "handler": handler_name,
                            "latency_ms": round(latency_ms, 2),
                            "cache_hit": True,
                            "timezone": params.get("tz", "UTC"),
                            "status": 200,
                        },
                    )
                    return web.json_response(cached)

            # Get current time
            now = self.time_provider()

            # Read event window with lock
            async with window_lock:
                window = tuple(event_window_ref[0])

            # Delegate to subclass-specific logic with exception handling
            response = await self.handle_request(request, window, now)

            # Cache the response data (if cache is enabled and response is json)
            if self.response_cache and cache_key and hasattr(response, "body"):
                # Extract response data from aiohttp response
                # The response should already be a web.json_response
                import json as json_lib

                try:
                    response_data = json_lib.loads(response.body)  # type: ignore[arg-type]
                    self.response_cache.set(cache_key, response_data)
                except Exception as e:
                    logger.debug("Could not cache response: %s", e)

            # Log successful completion with telemetry
            latency_ms = (time.time() - start_time) * 1000
            monitoring_logger.info(  # noqa: PLE1205
                "alexa.request.completed",
                f"Request completed for {handler_name}",
                details={
                    "handler": handler_name,
                    "latency_ms": round(latency_ms, 2),
                    "cache_hit": False,
                    "timezone": request.query.get("tz", "UTC"),
                    "status": 200,
                },
            )

            return response
        except AlexaValidationError as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning("Validation error in %s: %s", handler_name, e)
            monitoring_logger.error(  # noqa: PLE1205, TRY400
                "alexa.request.failed",
                f"Validation error in {handler_name}",
                details={
                    "handler": handler_name,
                    "latency_ms": round(latency_ms, 2),
                    "error_type": "ValidationError",
                    "error": str(e),
                    "status": 400,
                },
            )
            return web.json_response({"error": "Bad request", "message": str(e)}, status=400)
        except AlexaAuthenticationError as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.warning("Auth error in %s: %s", handler_name, e)
            monitoring_logger.error(  # noqa: PLE1205, TRY400
                "alexa.request.failed",
                f"Authentication error in {handler_name}",
                details={
                    "handler": handler_name,
                    "latency_ms": round(latency_ms, 2),
                    "error_type": "AuthenticationError",
                    "error": str(e),
                    "status": 401,
                },
            )
            return web.json_response({"error": "Unauthorized"}, status=401)
        except AlexaHandlerError as e:
            # Catch any other custom exceptions
            latency_ms = (time.time() - start_time) * 1000
            logger.exception("Handler exception in %s", handler_name)
            monitoring_logger.error(  # noqa: PLE1205, TRY400
                "alexa.request.failed",
                f"Handler exception in {handler_name}",
                details={
                    "handler": handler_name,
                    "latency_ms": round(latency_ms, 2),
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "status": 500,
                },
            )
            return web.json_response(
                {"error": "Internal server error", "message": str(e)}, status=500
            )
        except Exception as e:
            # Catch unexpected exceptions
            latency_ms = (time.time() - start_time) * 1000
            logger.exception("Unexpected error in %s", handler_name)
            monitoring_logger.error(  # noqa: PLE1205, TRY400
                "alexa.request.failed",
                f"Unexpected error in {handler_name}",
                details={
                    "handler": handler_name,
                    "latency_ms": round(latency_ms, 2),
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "status": 500,
                },
            )
            return web.json_response(
                {"error": "Internal server error", "message": "An unexpected error occurred"},
                status=500,
            )

    @abstractmethod
    async def handle_request(
        self,
        request: web.Request,
        window: tuple[LiteCalendarEvent, ...],
        now: datetime.datetime,
    ) -> web.Response:
        """Handle the specific endpoint request (implemented by subclasses).

        Args:
            request: aiohttp request object
            window: Tuple of LiteCalendarEvent objects
            now: Current UTC time

        Returns:
            aiohttp json response
        """

    def find_next_meeting(
        self,
        window: tuple[LiteCalendarEvent, ...],
        now: datetime.datetime,
        skip_focus_time: bool = False,
    ) -> tuple[LiteCalendarEvent, int] | None:
        """Find the next upcoming non-skipped meeting.

        Args:
            window: Tuple of LiteCalendarEvent objects
            now: Current UTC time
            skip_focus_time: Whether to skip focus time events

        Returns:
            Tuple of (event, seconds_until) or None if no meetings found
        """
        for ev in window:
            start = ev.start.date_time
            if not isinstance(start, datetime.datetime):
                continue

            seconds_until = int((start - now).total_seconds())

            # For all-day events: active for the entire day, always include
            # For timed events: skip if already ended OR currently in progress
            # (in-progress meetings are handled by _find_current_meeting)
            if not ev.is_all_day:
                end = ev.end.date_time
                # Skip if meeting has ended or is in progress
                if isinstance(end, datetime.datetime) and (end <= now or (start <= now < end)):
                    continue

            # Skip focus time events if requested
            if skip_focus_time and self._is_focus_time(ev):
                continue

            # Check if event is skipped
            if self._is_skipped(ev):
                continue

            return ev, seconds_until

        return None

    def _is_skipped(self, event: LiteCalendarEvent) -> bool:
        """Check if event is skipped by user.

        Args:
            event: LiteCalendarEvent object

        Returns:
            True if skipped, False otherwise (also returns False on store access errors)
        """
        if self.skipped_store is None:
            return False

        is_skipped_fn = getattr(self.skipped_store, "is_skipped", None)
        if not callable(is_skipped_fn):
            return False

        try:
            result = is_skipped_fn(event.id)
            return bool(result)
        except Exception as e:
            # Log warning but don't fail - treat as not skipped
            logger.warning("Skipped store access failed for event %s: %s", event.id, e)
            return False

    def _is_focus_time(self, event: LiteCalendarEvent) -> bool:
        """Check if event is a focus time event.

        Args:
            event: LiteCalendarEvent object

        Returns:
            True if focus time, False otherwise
        """
        subject = event.subject.lower()
        focus_keywords = ["focus time", "focus block", "do not schedule"]
        return any(keyword in subject for keyword in focus_keywords)

    async def _filter_events_with_pipeline(
        self,
        events: list[LiteCalendarEvent] | tuple[LiteCalendarEvent, ...],
        window_start: Optional[datetime.datetime] = None,
        window_end: Optional[datetime.datetime] = None,
        apply_skipped_filter: bool = True,
        apply_time_window_filter: bool = True,
    ) -> list[LiteCalendarEvent]:
        """Filter events using pipeline stages.

        This method uses the existing pipeline infrastructure (SkippedEventsFilterStage
        and TimeWindowStage) to filter events consistently across all handlers.

        Args:
            events: Events to filter
            window_start: Optional start time for time window filtering
            window_end: Optional end time for time window filtering
            apply_skipped_filter: Whether to filter out skipped events
            apply_time_window_filter: Whether to apply time window filtering

        Returns:
            Filtered list of LiteCalendarEvent objects
        """
        from calendarbot_lite.domain.pipeline import ProcessingContext
        from calendarbot_lite.domain.pipeline_stages import (
            SkippedEventsFilterStage,
            TimeWindowStage,
        )

        # Create processing context
        context = ProcessingContext(
            events=list(events),
            window_start=window_start,
            window_end=window_end,
        )

        # Add skipped event IDs to context if available
        if apply_skipped_filter and self.skipped_store:
            try:
                active_list_fn = getattr(self.skipped_store, "active_list", None)
                if callable(active_list_fn):
                    active_list_result = active_list_fn()
                    # active_list() returns dict[str, str] per skipped_store.py
                    if isinstance(active_list_result, dict):
                        context.skipped_event_ids = set(active_list_result.keys())
            except Exception as e:
                logger.warning("Failed to get skipped events list: %s", e)

        # Apply skipped events filter
        if apply_skipped_filter and context.skipped_event_ids:
            skipped_stage = SkippedEventsFilterStage()
            await skipped_stage.process(context)

        # Apply time window filter
        if apply_time_window_filter and (window_start or window_end):
            time_stage = TimeWindowStage()
            await time_stage.process(context)

        return context.events

    def _build_response_with_ssml(
        self,
        data: dict[str, Any],
        ssml: Optional[str],
        card_title: Optional[str] = None,
        card_content: Optional[str] = None,
    ) -> dict[str, Any]:
        """Build response with optional SSML and card data.

        Args:
            data: Base response data
            ssml: Optional SSML string
            card_title: Optional Alexa card title
            card_content: Optional Alexa card content

        Returns:
            Response dictionary with SSML and card if provided
        """
        response = {**data}

        if ssml:
            response["ssml"] = ssml

        if card_title and card_content:
            response["card"] = {
                "title": card_title,
                "content": card_content,
            }

        return response


class NextMeetingHandler(AlexaEndpointBase):
    """Handler for /api/alexa/next-meeting endpoint."""

    def __init__(
        self,
        bearer_token: Optional[str],
        time_provider: TimeProvider,
        skipped_store: SkippedStore | None,
        response_cache: Optional[ResponseCache] = None,
        presenter: Optional[AlexaPresenter] = None,
        duration_formatter: Optional[DurationFormatter] = None,
        iso_serializer: Optional[ISOSerializer] = None,
    ):
        """Initialize next meeting handler with presenter support.

        Args:
            bearer_token: Bearer token for auth
            time_provider: Time provider callable
            skipped_store: Skipped events store
            response_cache: Optional ResponseCache for caching responses
            presenter: Optional presenter for formatting responses (AlexaPresenter)
            duration_formatter: Function to format duration in speech
            iso_serializer: Function to serialize datetime to ISO string
        """
        super().__init__(
            bearer_token, time_provider, skipped_store, response_cache
        )
        from calendarbot_lite.alexa.alexa_presentation import PlainTextPresenter

        self.presenter = presenter or PlainTextPresenter()
        self.duration_formatter = duration_formatter
        self.iso_serializer = iso_serializer

    async def handle_request(
        self,
        request: web.Request,
        window: tuple[LiteCalendarEvent, ...],
        now: datetime.datetime,
    ) -> web.Response:
        """Handle next meeting request with presenter-based formatting."""

        logger.debug("Alexa /api/alexa/next-meeting called - window has %d events", len(window))

        # Find next meeting
        result = self.find_next_meeting(window, now)

        response_data: AlexaNextMeetingResponse

        if result is None:
            # No upcoming meetings - use presenter for formatting
            speech_text, ssml_output = self.presenter.format_next_meeting(None)

            response_data = {
                "meeting": None,
                "speech_text": speech_text,
            }
            if ssml_output:
                response_data["ssml"] = ssml_output

            return web.json_response(response_data, status=200)

        # Found a meeting - prepare data for presenter
        event, seconds_until = result
        subject = event.subject
        start = event.start.date_time
        duration_spoken = self.duration_formatter(seconds_until) if self.duration_formatter else ""

        meeting_data: dict[str, Any] = {
            "subject": subject,
            "seconds_until_start": seconds_until,
            "duration_spoken": duration_spoken,
            "location": event.location.display_name if event.location else "",
            "is_online_meeting": event.is_online_meeting,
        }

        # Use presenter to format response
        speech_text, ssml_output = self.presenter.format_next_meeting(meeting_data)

        # Build response with typed meeting info
        meeting_info: AlexaMeetingInfo = {
            "subject": subject,
            "start_iso": self.iso_serializer(start) if self.iso_serializer else start.isoformat(),
            "seconds_until_start": seconds_until,
            "speech_text": speech_text,
            "duration_spoken": duration_spoken,
        }

        if ssml_output:
            meeting_info["ssml"] = ssml_output

        response_data = {"meeting": meeting_info}

        return web.json_response(response_data, status=200)


class TimeUntilHandler(AlexaEndpointBase):
    """Handler for /api/alexa/time-until-next endpoint."""

    def __init__(
        self,
        bearer_token: Optional[str],
        time_provider: TimeProvider,
        skipped_store: SkippedStore | None,
        response_cache: Optional[ResponseCache] = None,
        presenter: Optional[AlexaPresenter] = None,
        duration_formatter: Optional[DurationFormatter] = None,
    ):
        """Initialize time until handler with presenter support.

        Args:
            bearer_token: Bearer token for auth
            time_provider: Time provider callable
            skipped_store: Skipped events store
            response_cache: Optional ResponseCache for caching responses
            presenter: Optional presenter for formatting responses (AlexaPresenter)
            duration_formatter: Function to format duration in speech
        """
        super().__init__(
            bearer_token, time_provider, skipped_store, response_cache
        )
        from calendarbot_lite.alexa.alexa_presentation import PlainTextPresenter

        self.presenter = presenter or PlainTextPresenter()
        self.duration_formatter = duration_formatter

    async def handle_request(
        self,
        request: web.Request,
        window: tuple[LiteCalendarEvent, ...],
        now: datetime.datetime,
    ) -> web.Response:
        """Handle time until next meeting request with presenter-based formatting."""

        logger.debug("Alexa /api/alexa/time-until-next called - window has %d events", len(window))

        # Find next meeting
        result = self.find_next_meeting(window, now)

        response_data: AlexaTimeUntilResponse

        if result is None:
            # No upcoming meetings - use presenter for formatting
            speech_text, ssml_output = self.presenter.format_time_until(0, None)

            response_data = {
                "seconds_until_start": None,
                "speech_text": speech_text,
                "duration_spoken": "",
            }
            if ssml_output:
                response_data["ssml"] = ssml_output

            return web.json_response(response_data, status=200)

        # Found a meeting - prepare data for presenter
        event, seconds_until = result
        duration_spoken = self.duration_formatter(seconds_until) if self.duration_formatter else ""

        meeting_data: dict[str, Any] = {
            "subject": event.subject,
            "duration_spoken": duration_spoken,
        }

        # Use presenter to format response
        speech_text, ssml_output = self.presenter.format_time_until(seconds_until, meeting_data)

        # Build response
        response_data = {
            "seconds_until_start": seconds_until,
            "duration_spoken": duration_spoken,
            "speech_text": speech_text,
        }

        if ssml_output:
            response_data["ssml"] = ssml_output

        return web.json_response(response_data, status=200)


class DoneForDayHandler(AlexaEndpointBase):
    """Handler for /api/alexa/done-for-day endpoint."""

    def __init__(
        self,
        bearer_token: Optional[str],
        time_provider: TimeProvider,
        skipped_store: SkippedStore | None,
        response_cache: Optional[ResponseCache] = None,
        presenter: Optional[AlexaPresenter] = None,
        iso_serializer: Optional[ISOSerializer] = None,
        get_server_timezone: Optional[TimezoneGetter] = None,
    ):
        """Initialize done-for-day handler with presenter support.

        Args:
            bearer_token: Bearer token for auth
            time_provider: Time provider callable
            skipped_store: Skipped events store
            response_cache: Optional ResponseCache for caching responses
            presenter: Optional presenter for formatting responses (AlexaPresenter)
            iso_serializer: Function to serialize datetime to ISO string
            get_server_timezone: Function to get server timezone
        """
        super().__init__(
            bearer_token, time_provider, skipped_store, response_cache
        )
        from calendarbot_lite.alexa.alexa_presentation import PlainTextPresenter

        self.presenter = presenter or PlainTextPresenter()
        self.iso_serializer = iso_serializer
        self.get_server_timezone = get_server_timezone

    async def handle_request(
        self,
        request: web.Request,
        window: tuple[LiteCalendarEvent, ...],
        now: datetime.datetime,
    ) -> web.Response:
        """Handle done-for-day request."""

        # Get timezone parameter from query string
        request_tz = request.query.get("tz")

        logger.debug(
            "Alexa /api/alexa/done-for-day called - window has %d events, tz=%s",
            len(window),
            request_tz,
        )

        # Compute last meeting end for today
        result = await self._compute_last_meeting_end_for_today(request_tz, window)

        # Generate speech text based on results
        speech_text = self._generate_speech_text(result, request_tz, now)

        # Use presenter to format response (returns speech_text and optional SSML)
        speech_text, ssml_output = self.presenter.format_done_for_day(
            result["has_meetings_today"], speech_text
        )

        # Build response
        response_data: AlexaDoneForDayResponse = {
            "now_iso": self.iso_serializer(now)
            if self.iso_serializer
            else serialize_datetime_utc(now),
            "tz": request_tz,
            "has_meetings_today": result["has_meetings_today"],
            "last_meeting_start_iso": result["last_meeting_start_iso"],
            "last_meeting_end_iso": result["last_meeting_end_iso"],
            "last_meeting_end_local_iso": result["last_meeting_end_local_iso"],
            "speech_text": speech_text,
            "note": result.get("note"),
        }

        # Add SSML and card data for Alexa if available
        if ssml_output:
            response_data["ssml"] = ssml_output
            response_data["card"] = {
                "title": "Done for the Day",
                "content": speech_text,
            }

        return web.json_response(response_data, status=200)

    async def _compute_last_meeting_end_for_today(
        self,
        request_tz: str | None,
        event_window: tuple[LiteCalendarEvent, ...],
    ) -> AlexaDoneForDayInfo:
        """Compute the last meeting end time for today from the event window.

        Uses shared utility function with pipeline stages for consistent event filtering.

        Args:
            request_tz: Optional timezone string for date comparison
            event_window: Tuple of LiteCalendarEvent objects from the in-memory window

        Returns:
            Dictionary with has_meetings_today, last_meeting_start_iso, last_meeting_end_iso, etc.
        """
        from calendarbot_lite.alexa import alexa_utils

        now_utc = self.time_provider()

        # Use shared utility to compute done-for-day info
        computation_result = await alexa_utils.compute_done_for_day_info(
            events=event_window,
            request_tz=request_tz,
            now=now_utc,
            filter_events_fn=self._filter_events_with_pipeline,
        )

        # Format result for Alexa response
        result = alexa_utils.format_done_for_day_result(
            computation_result,
            iso_serializer=self.iso_serializer,
        )

        logger.debug(
            "Done-for-day result: has_meetings=%s, meetings_found=%d (shared-utility)",
            result["has_meetings_today"],
            computation_result["meetings_count"],
        )

        return result

    def _generate_speech_text(
        self,
        result: AlexaDoneForDayInfo,
        request_tz: str | None,
        now: datetime.datetime,
    ) -> str:
        """Generate speech text based on done-for-day result."""
        if result["has_meetings_today"]:
            if result["last_meeting_end_iso"]:
                # Parse the end time for speech formatting
                try:
                    end_utc = datetime.datetime.fromisoformat(
                        result["last_meeting_end_iso"].replace("Z", "+00:00")
                    )

                    # Convert to local time for speech
                    tz = parse_request_timezone(request_tz)
                    end_local = end_utc.astimezone(tz)

                    # Format time string (show UTC if no timezone provided)
                    if request_tz:
                        time_str = format_time_cross_platform(end_local)
                    else:
                        time_str = format_time_cross_platform(end_local, " UTC")

                    # Compare current time with last meeting end time
                    if now >= end_utc:
                        # All meetings for today have ended
                        return "You're all done for today!"
                    # Still have meetings, will be done at end time
                    return f"You'll be done at {time_str}."

                except (ValueError, AttributeError) as e:
                    logger.warning("Error formatting end time for speech: %s", e)
                    return (
                        "You have meetings today, but I couldn't determine when your last one ends."
                    )
                except Exception:
                    logger.exception("Unexpected error formatting end time")
                    return (
                        "You have meetings today, but I couldn't determine when your last one ends."
                    )
            else:
                return "You have meetings today, but I couldn't determine when your last one ends."
        else:
            return "You have no meetings today. Enjoy your free day!"


class LaunchSummaryHandler(AlexaEndpointBase):
    """Handler for /api/alexa/launch-summary endpoint."""

    def __init__(
        self,
        bearer_token: Optional[str],
        time_provider: TimeProvider,
        skipped_store: SkippedStore | None,
        response_cache: Optional[ResponseCache] = None,
        presenter: Optional[AlexaPresenter] = None,
        duration_formatter: Optional[DurationFormatter] = None,
        iso_serializer: Optional[ISOSerializer] = None,
        get_server_timezone: Optional[TimezoneGetter] = None,
    ):
        """Initialize launch summary handler with presenter support.

        Args:
            bearer_token: Bearer token for auth
            time_provider: Time provider callable
            skipped_store: Skipped events store
            response_cache: Optional ResponseCache for caching responses
            presenter: Optional presenter for formatting responses (AlexaPresenter)
            duration_formatter: Function to format duration for speech
            iso_serializer: Function to serialize datetime to ISO string
            get_server_timezone: Function to get server timezone
        """
        super().__init__(
            bearer_token, time_provider, skipped_store, response_cache
        )
        from calendarbot_lite.alexa.alexa_presentation import PlainTextPresenter

        self.presenter = presenter or PlainTextPresenter()
        self.duration_formatter = duration_formatter
        self.iso_serializer = iso_serializer
        self.get_server_timezone = get_server_timezone

    def _get_timezone(self, request_tz: Optional[str]) -> datetime.tzinfo:
        """Parse timezone from request.

        Args:
            request_tz: Optional timezone string from request

        Returns:
            Timezone object (from parse_request_timezone)
        """
        return parse_request_timezone(request_tz)

    async def _get_done_for_day_info(
        self,
        window: tuple[LiteCalendarEvent, ...],
        request_tz: Optional[str],
    ) -> AlexaDoneForDayInfo:
        """Get done-for-day information using shared utility.

        Uses the shared alexa_utils module instead of creating a DoneForDayHandler
        instance, eliminating cross-handler coupling.

        Args:
            window: Event window
            request_tz: Optional timezone string

        Returns:
            Done-for-day information dictionary
        """
        from calendarbot_lite.alexa import alexa_utils

        now_utc = self.time_provider()

        # Use shared utility to compute done-for-day info
        computation_result = await alexa_utils.compute_done_for_day_info(
            events=window,
            request_tz=request_tz,
            now=now_utc,
            filter_events_fn=self._filter_events_with_pipeline,
        )

        # Format result for Alexa response
        return alexa_utils.format_done_for_day_result(
            computation_result,
            iso_serializer=self.iso_serializer,
        )

    def _build_launch_summary_response(
        self,
        speech_text: str,
        has_meetings_today: bool,
        primary_meeting: Optional[dict[str, Any]],
        done_info: AlexaDoneForDayInfo,
        ssml_output: Optional[str],
    ) -> AlexaLaunchSummaryResponse:
        """Build the final launch summary response.

        Args:
            speech_text: Generated speech text
            has_meetings_today: Whether user has meetings today
            primary_meeting: Primary meeting to include (or None)
            done_info: Done-for-day calculation results
            ssml_output: Optional SSML markup

        Returns:
            Formatted Alexa launch summary response
        """
        # Build next meeting info if available
        next_meeting_info: Optional[AlexaMeetingInfo] = None
        if primary_meeting:
            next_meeting_info = {
                "subject": primary_meeting["subject"],
                "start_iso": (
                    self.iso_serializer(primary_meeting["event"].start.date_time)
                    if self.iso_serializer
                    else primary_meeting["event"].start.date_time.isoformat()
                ),
                "seconds_until_start": primary_meeting["seconds_until"],
                "duration_spoken": primary_meeting["duration_spoken"],
                "speech_text": speech_text,
            }

        # Build response
        response_data: AlexaLaunchSummaryResponse = {
            "speech_text": speech_text,
            "has_meetings_today": has_meetings_today,
            "next_meeting": next_meeting_info,
            "done_for_day": done_info,
        }

        if ssml_output:
            response_data["ssml"] = ssml_output

        return response_data

    def _find_current_meeting(
        self,
        window: tuple[LiteCalendarEvent, ...],
        now: datetime.datetime,
        tz: datetime.tzinfo,
        today_date: datetime.date,
    ) -> Optional[dict[str, Any]]:
        """Find a meeting that is currently in progress.

        Args:
            window: Event window to search
            now: Current time
            tz: Timezone for date comparison
            today_date: Today's date in the target timezone

        Returns:
            Dictionary with current meeting details or None if no meeting is in progress
        """
        for ev in window:
            start = ev.start.date_time
            end = ev.end.date_time

            # Skip if not datetime events
            if not isinstance(start, datetime.datetime) or not isinstance(end, datetime.datetime):
                continue

            # For all-day events, extract date from UTC time (which represents the calendar date)
            # For timed events, convert to local timezone for date comparison
            if ev.is_all_day:
                event_date = (
                    start.date()
                )  # All-day events stored at midnight UTC represent this date
            else:
                start_local = start.astimezone(tz)
                event_date = start_local.date()

            # Only check today's meetings
            if event_date != today_date:
                continue

            # Check if meeting is currently in progress (start <= now < end)
            if start <= now < end:
                # Check if skipped
                if self._is_skipped(ev):
                    continue

                # Calculate seconds until end (for duration display)
                seconds_until_end = int((end - now).total_seconds())

                # Found a meeting in progress
                return {
                    "event": ev,
                    "seconds_until_end": seconds_until_end,
                    "subject": ev.subject,
                    "is_current": True,
                }

        return None

    def _find_next_meeting(
        self,
        window: tuple[LiteCalendarEvent, ...],
        now: datetime.datetime,
        tz: datetime.tzinfo,
        today_date: datetime.date,
        include_today: bool = True,
    ) -> Optional[dict[str, Any]]:
        """Find the next upcoming meeting.

        Args:
            window: Event window to search
            now: Current time
            tz: Timezone for date comparison
            today_date: Today's date in the target timezone
            include_today: If True, include today's meetings; if False, only future days

        Returns:
            Dictionary with meeting details or None if no meeting found
        """
        for ev in window:
            start = ev.start.date_time
            if not isinstance(start, datetime.datetime):
                continue

            # For all-day events, extract date from UTC time (which represents the calendar date)
            # For timed events, convert to local timezone for date comparison
            if ev.is_all_day:
                event_date = (
                    start.date()
                )  # All-day events stored at midnight UTC represent this date
            else:
                start_local = start.astimezone(tz)
                event_date = start_local.date()

            # Filter by date based on include_today parameter
            if include_today:
                if event_date != today_date:
                    continue  # Skip non-today meetings
            elif event_date <= today_date:
                continue  # Skip today's and past meetings

            # For all-day events: active for the entire day, always include
            # For timed events: skip if already ended OR currently in progress
            # (in-progress meetings are handled by _find_current_meeting)
            seconds_until = int((start - now).total_seconds())
            if not ev.is_all_day:
                end = ev.end.date_time
                # Skip if meeting has ended or is in progress
                if isinstance(end, datetime.datetime) and (end <= now or (start <= now < end)):
                    continue

            # Check if skipped
            if self._is_skipped(ev):
                continue

            # Found a meeting
            return {
                "event": ev,
                "seconds_until": seconds_until,
                "subject": ev.subject,
                "duration_spoken": (
                    self.duration_formatter(seconds_until) if self.duration_formatter else ""
                ),
            }

        return None

    async def handle_request(
        self,
        request: web.Request,
        window: tuple[LiteCalendarEvent, ...],
        now: datetime.datetime,
    ) -> web.Response:
        """Handle launch summary request - orchestrates helper methods.

        This method has been refactored to delegate to focused helper methods,
        reducing complexity from 181 lines to <50 lines.
        """

        # 1. Parse timezone
        request_tz = request.query.get("tz")
        tz = self._get_timezone(request_tz)
        today_date = now.astimezone(tz).date()

        logger.debug(
            "Alexa /api/alexa/launch-summary called - window has %d events, tz=%s",
            len(window),
            request_tz,
        )

        # 2. Get done-for-day info
        done_info = await self._get_done_for_day_info(window, request_tz)

        # 3. Check for current meeting in progress
        current_meeting = self._find_current_meeting(window, now, tz, today_date)

        # 4. Find next meeting based on whether there are meetings today
        if done_info["has_meetings_today"]:
            primary_meeting = self._find_next_meeting(
                window, now, tz, today_date, include_today=True
            )
        else:
            primary_meeting = self._find_next_meeting(
                window, now, tz, today_date, include_today=False
            )

        # 5. Use presenter to generate speech text AND SSML
        # Presenter now handles all speech generation logic, including current meeting
        speech_text, ssml_output = self.presenter.format_launch_summary(
            done_info, primary_meeting, tz, request_tz, now, current_meeting
        )

        # 5. Build and return response
        response_data = self._build_launch_summary_response(
            speech_text=speech_text,
            has_meetings_today=done_info["has_meetings_today"],
            primary_meeting=primary_meeting,
            done_info=done_info,
            ssml_output=ssml_output,
        )

        return web.json_response(response_data, status=200)


class MorningSummaryHandler(AlexaEndpointBase):
    """Handler for /api/alexa/morning-summary endpoint."""

    # Use specialized validation model for morning summary
    param_model = MorningSummaryRequestParams

    @staticmethod
    def _empty_summary_metadata() -> AlexaMorningSummaryMetadata:
        """Return empty summary metadata for error responses."""
        return {
            "preview_for": "",
            "total_meetings_equivalent": 0.0,
            "early_start_flag": False,
            "density": "",
            "back_to_back_count": 0,
            "timeframe_start": "",
            "timeframe_end": "",
            "wake_up_recommendation": None,
        }

    def _build_error_response(
        self, error_type: str, speech_text: str, status: int
    ) -> web.Response:
        """Build a standardized error response for morning summary.

        Args:
            error_type: Error description (e.g., "Bad request", "Internal server error")
            speech_text: User-friendly speech text for Alexa
            status: HTTP status code

        Returns:
            JSON response with error, speech_text, and empty summary
        """
        error_response: AlexaMorningSummaryResponse = {
            "error": error_type,
            "speech_text": speech_text,
            "summary": self._empty_summary_metadata(),
        }
        return web.json_response(error_response, status=status)

    def __init__(
        self,
        bearer_token: Optional[str],
        time_provider: TimeProvider,
        skipped_store: SkippedStore | None,
        response_cache: Optional[ResponseCache] = None,
        presenter: Optional[AlexaPresenter] = None,
        get_server_timezone: Optional[TimezoneGetter] = None,
    ):
        """Initialize morning summary handler with presenter support.

        Args:
            bearer_token: Bearer token for auth
            time_provider: Time provider callable
            skipped_store: Skipped events store
            response_cache: Optional ResponseCache for caching responses
            presenter: Optional presenter for formatting responses (AlexaPresenter)
            get_server_timezone: Function to get server timezone
        """
        super().__init__(
            bearer_token, time_provider, skipped_store, response_cache
        )
        from calendarbot_lite.alexa.alexa_presentation import PlainTextPresenter

        self.presenter = presenter or PlainTextPresenter()
        self.get_server_timezone = get_server_timezone

    async def handle_request(
        self,
        request: web.Request,
        window: tuple[LiteCalendarEvent, ...],
        now: datetime.datetime,
    ) -> web.Response:
        """Handle morning summary request."""

        try:
            # Parse request parameters
            target_date = request.query.get("date")  # ISO date for summary (defaults to tomorrow)
            timezone_str = request.query.get(
                "timezone",
                self.get_server_timezone() if self.get_server_timezone else "UTC",
            )
            detail_level = request.query.get("detail_level", "normal")
            prefer_ssml = request.query.get("prefer_ssml", "false").lower() == "true"
            max_events = int(request.query.get("max_events", "50"))

            logger.debug(
                "Alexa morning summary called with tz=%s, prefer_ssml=%s", timezone_str, prefer_ssml
            )

            # Events are already LiteCalendarEvent objects - use directly!
            from calendarbot_lite.domain.morning_summary import (
                MorningSummaryRequest,
                MorningSummaryService,
            )

            # Create morning summary request
            summary_request = MorningSummaryRequest(
                date=target_date,
                timezone=timezone_str,
                detail_level=detail_level,
                prefer_ssml=prefer_ssml,
                max_events=max_events,
            )

            # Generate morning summary (window is already LiteCalendarEvent objects)
            service = MorningSummaryService()
            summary_result = await service.generate_summary(list(window), summary_request)

            # Use presenter to format response (returns speech_text and optional SSML)
            # Note: We use the speech_text from summary_result, presenter just adds SSML if requested
            _, ssml_output = self.presenter.format_morning_summary(summary_result)

            # Build response following existing Alexa endpoint patterns
            summary_metadata: AlexaMorningSummaryMetadata = {
                "preview_for": summary_result.metadata.get("preview_for", "tomorrow_morning"),
                "total_meetings_equivalent": summary_result.total_meetings_equivalent,
                "early_start_flag": summary_result.early_start_flag,
                "density": summary_result.density,
                "back_to_back_count": summary_result.back_to_back_count,
                "timeframe_start": summary_result.timeframe_start.isoformat(),
                "timeframe_end": summary_result.timeframe_end.isoformat(),
                "wake_up_recommendation": summary_result.wake_up_recommendation_time.isoformat()
                if summary_result.wake_up_recommendation_time
                else None,
            }

            response_data: AlexaMorningSummaryResponse = {
                "speech_text": summary_result.speech_text,
                "summary": summary_metadata,
            }

            # Add SSML to response if generated
            if ssml_output:
                response_data["ssml"] = ssml_output

            return web.json_response(response_data, status=200)

        except AlexaValidationError as e:
            logger.warning("Morning summary validation error: %s", e)
            return self._build_error_response(
                "Bad request",
                "Sorry, I couldn't understand your request. Please try again.",
                400,
            )
        except AlexaHandlerError:
            logger.exception("Morning summary handler error")
            return self._build_error_response(
                "Internal server error",
                "Sorry, I couldn't generate your morning summary right now. Please try again later.",
                500,
            )
        except Exception:
            logger.exception("Unexpected error in morning summary")
            return self._build_error_response(
                "Internal server error",
                "Sorry, I couldn't generate your morning summary right now. Please try again later.",
                500,
            )
