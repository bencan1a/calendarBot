"""Consolidated Alexa endpoint handlers with shared logic."""

from __future__ import annotations

import datetime
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AlexaEndpointBase(ABC):
    """Base class for Alexa endpoints with common authentication and meeting search logic."""

    def __init__(
        self,
        bearer_token: Optional[str],
        time_provider: Any,
        skipped_store: object | None,
    ):
        """Initialize Alexa endpoint handler.

        Args:
            bearer_token: Required bearer token for authentication
            time_provider: Callable that returns current UTC time
            skipped_store: Optional store for skipped events
        """
        self.bearer_token = bearer_token
        self.time_provider = time_provider
        self.skipped_store = skipped_store

    def check_auth(self, request: Any) -> bool:
        """Check if request has valid bearer token.

        Args:
            request: aiohttp request object

        Returns:
            True if authorized, False otherwise
        """
        if not self.bearer_token:
            return True  # No token configured, allow all requests

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return False

        token = auth_header[7:]  # Remove "Bearer " prefix
        return token == self.bearer_token

    async def handle(self, request: Any, event_window_ref: Any, window_lock: Any) -> Any:
        """Main handler with auth check and common setup.

        Args:
            request: aiohttp request object
            event_window_ref: Reference to event window
            window_lock: Lock for thread-safe window access

        Returns:
            aiohttp json response
        """
        # Import web here to avoid circular imports
        from aiohttp import web

        # Check authentication
        if not self.check_auth(request):
            return web.json_response({"error": "Unauthorized"}, status=401)

        # Get current time
        now = self.time_provider()

        # Read event window with lock
        async with window_lock:
            window = tuple(event_window_ref[0])

        # Delegate to subclass-specific logic
        try:
            return await self.handle_request(request, window, now)
        except Exception as e:
            logger.exception("Alexa endpoint %s failed", self.__class__.__name__)
            return web.json_response(
                {
                    "error": "Internal server error",
                    "message": str(e),
                },
                status=500,
            )

    @abstractmethod
    async def handle_request(
        self,
        request: Any,
        window: tuple[dict[str, Any], ...],
        now: datetime.datetime,
    ) -> Any:
        """Handle the specific endpoint request (implemented by subclasses).

        Args:
            request: aiohttp request object
            window: Tuple of event dictionaries
            now: Current UTC time

        Returns:
            aiohttp json response
        """

    def find_next_meeting(
        self,
        window: tuple[dict[str, Any], ...],
        now: datetime.datetime,
        skip_focus_time: bool = False,
    ) -> tuple[dict[str, Any], int] | None:
        """Find the next upcoming non-skipped meeting.

        Args:
            window: Tuple of event dictionaries
            now: Current UTC time
            skip_focus_time: Whether to skip focus time events

        Returns:
            Tuple of (event, seconds_until) or None if no meetings found
        """
        for ev in window:
            start = ev.get("start")
            if not isinstance(start, datetime.datetime):
                continue

            seconds_until = int((start - now).total_seconds())

            # Skip past events
            if seconds_until < 0:
                continue

            # Skip focus time events if requested
            if skip_focus_time and self._is_focus_time(ev):
                continue

            # Check if event is skipped
            if self._is_skipped(ev):
                continue

            return ev, seconds_until

        return None

    def _is_skipped(self, event: dict[str, Any]) -> bool:
        """Check if event is skipped by user.

        Args:
            event: Event dictionary

        Returns:
            True if skipped, False otherwise
        """
        if self.skipped_store is None:
            return False

        is_skipped_fn = getattr(self.skipped_store, "is_skipped", None)
        if not callable(is_skipped_fn):
            return False

        try:
            return is_skipped_fn(event["meeting_id"])
        except Exception as e:
            logger.warning("skipped_store.is_skipped raised: %s", e)
            return False

    def _is_focus_time(self, event: dict[str, Any]) -> bool:
        """Check if event is a focus time event.

        Args:
            event: Event dictionary

        Returns:
            True if focus time, False otherwise
        """
        subject = event.get("subject", "").lower()
        focus_keywords = ["focus time", "focus block", "do not schedule"]
        return any(keyword in subject for keyword in focus_keywords)

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
        time_provider: Any,
        skipped_store: object | None,
        ssml_renderer: Any = None,
        duration_formatter: Any = None,
        iso_serializer: Any = None,
    ):
        """Initialize next meeting handler with SSML support.

        Args:
            bearer_token: Bearer token for auth
            time_provider: Time provider callable
            skipped_store: Skipped events store
            ssml_renderer: Optional SSML rendering function
            duration_formatter: Function to format duration in speech
            iso_serializer: Function to serialize datetime to ISO string
        """
        super().__init__(bearer_token, time_provider, skipped_store)
        self.ssml_renderer = ssml_renderer
        self.duration_formatter = duration_formatter
        self.iso_serializer = iso_serializer

    async def handle_request(
        self,
        request: Any,
        window: tuple[dict[str, Any], ...],
        now: datetime.datetime,
    ) -> Any:
        """Handle next meeting request with SSML generation."""
        from aiohttp import web

        logger.debug("Alexa /api/alexa/next-meeting called - window has %d events", len(window))

        # Find next meeting
        result = self.find_next_meeting(window, now)

        if result is None:
            # No upcoming meetings
            speech_text = "You have no upcoming meetings."
            ssml_output = self._generate_no_meeting_ssml()

            response_data = {"meeting": None, "speech_text": speech_text}
            if ssml_output:
                response_data["ssml"] = ssml_output

            return web.json_response(response_data, status=200)

        # Found a meeting
        event, seconds_until = result
        subject = event.get("subject", "Untitled meeting")
        start = event.get("start")
        duration_spoken = self.duration_formatter(seconds_until) if self.duration_formatter else ""

        # Simple speech text
        speech_text = f"Your next meeting is {subject} {duration_spoken}."

        # Generate SSML
        meeting_data = {
            "subject": subject,
            "seconds_until_start": seconds_until,
            "duration_spoken": duration_spoken,
            "location": event.get("location", ""),
            "is_online_meeting": event.get("is_online_meeting", False),
        }
        ssml_output = self._generate_meeting_ssml(meeting_data)

        # Build response
        response_data = {
            "meeting": {  # type: ignore[dict-item]
                "subject": subject,
                "start_iso": self.iso_serializer(start) if self.iso_serializer else str(start),
                "seconds_until_start": seconds_until,
                "speech_text": speech_text,
                "duration_spoken": duration_spoken,
            }
        }

        if ssml_output:
            response_data["meeting"]["ssml"] = ssml_output  # type: ignore[index]

        return web.json_response(response_data, status=200)

    def _generate_meeting_ssml(self, meeting_data: dict[str, Any]) -> Optional[str]:
        """Generate SSML for meeting data."""
        if not self.ssml_renderer:
            return None

        try:
            ssml = self.ssml_renderer(meeting_data)
            if ssml:
                logger.info("SSML generated successfully: %d characters", len(ssml))
            return ssml
        except Exception as e:
            logger.error("SSML generation failed: %s", e, exc_info=True)
            return None

    def _generate_no_meeting_ssml(self) -> Optional[str]:
        """Generate SSML for no meetings case."""
        if not self.ssml_renderer:
            return None

        try:
            empty_meeting = {"subject": "", "seconds_until_start": 0, "duration_spoken": ""}
            ssml = self.ssml_renderer(empty_meeting)
            if ssml:
                logger.info("No-meetings SSML generated: %d characters", len(ssml))
            return ssml
        except Exception as e:
            logger.error("No-meetings SSML generation failed: %s", e, exc_info=True)
            return None


class TimeUntilHandler(AlexaEndpointBase):
    """Handler for /api/alexa/time-until-next endpoint."""

    def __init__(
        self,
        bearer_token: Optional[str],
        time_provider: Any,
        skipped_store: object | None,
        ssml_renderer: Any = None,
        duration_formatter: Any = None,
    ):
        """Initialize time until handler.

        Args:
            bearer_token: Bearer token for auth
            time_provider: Time provider callable
            skipped_store: Skipped events store
            ssml_renderer: Optional SSML rendering function
            duration_formatter: Function to format duration in speech
        """
        super().__init__(bearer_token, time_provider, skipped_store)
        self.ssml_renderer = ssml_renderer
        self.duration_formatter = duration_formatter

    async def handle_request(
        self,
        request: Any,
        window: tuple[dict[str, Any], ...],
        now: datetime.datetime,
    ) -> Any:
        """Handle time until next meeting request."""
        from aiohttp import web

        logger.debug("Alexa /api/alexa/time-until-next called - window has %d events", len(window))

        # Find next meeting
        result = self.find_next_meeting(window, now)

        if result is None:
            # No upcoming meetings
            speech_text = "You have no upcoming meetings."
            ssml_output = self._generate_ssml(0, None)

            response_data = {"seconds_until_start": None, "speech_text": speech_text}
            if ssml_output:
                response_data["ssml"] = ssml_output

            return web.json_response(response_data, status=200)

        # Found a meeting
        event, seconds_until = result
        duration_spoken = self.duration_formatter(seconds_until) if self.duration_formatter else ""
        speech_text = f"Your next meeting is {duration_spoken}."

        # Generate SSML
        meeting_data = {
            "subject": event.get("subject", ""),
            "duration_spoken": duration_spoken,
        }
        ssml_output = self._generate_ssml(seconds_until, meeting_data)

        # Build response
        response_data = {
            "seconds_until_start": seconds_until,  # type: ignore[dict-item]
            "duration_spoken": duration_spoken,
            "speech_text": speech_text,
        }

        if ssml_output:
            response_data["ssml"] = ssml_output

        return web.json_response(response_data, status=200)

    def _generate_ssml(
        self,
        seconds_until: int,
        meeting_data: Optional[dict[str, Any]],
    ) -> Optional[str]:
        """Generate SSML for time until response."""
        if not self.ssml_renderer:
            return None

        try:
            ssml = self.ssml_renderer(seconds_until, meeting_data)
            if ssml:
                logger.info("Time-until SSML generated: %d characters", len(ssml))
            return ssml
        except Exception as e:
            logger.error("Time-until SSML generation failed: %s", e, exc_info=True)
            return None


class DoneForDayHandler(AlexaEndpointBase):
    """Handler for /api/alexa/done-for-day endpoint."""

    def __init__(
        self,
        bearer_token: Optional[str],
        time_provider: Any,
        skipped_store: object | None,
        ssml_renderer: Any = None,
        iso_serializer: Any = None,
        get_server_timezone: Any = None,
    ):
        """Initialize done-for-day handler.

        Args:
            bearer_token: Bearer token for auth
            time_provider: Time provider callable
            skipped_store: Skipped events store
            ssml_renderer: Optional SSML rendering function
            iso_serializer: Function to serialize datetime to ISO string
            get_server_timezone: Function to get server timezone
        """
        super().__init__(bearer_token, time_provider, skipped_store)
        self.ssml_renderer = ssml_renderer
        self.iso_serializer = iso_serializer
        self.get_server_timezone = get_server_timezone

    async def handle_request(
        self,
        request: Any,
        window: tuple[dict[str, Any], ...],
        now: datetime.datetime,
    ) -> Any:
        """Handle done-for-day request."""
        from aiohttp import web

        # Get timezone parameter from query string
        request_tz = request.query.get("tz")

        logger.debug(
            "Alexa /api/alexa/done-for-day called - window has %d events, tz=%s",
            len(window),
            request_tz,
        )

        # Compute last meeting end for today
        result = self._compute_last_meeting_end_for_today(request_tz, window)

        # Generate speech text based on results
        speech_text = self._generate_speech_text(result, request_tz, now)

        # Generate SSML if available
        ssml_output = None
        if self.ssml_renderer:
            logger.debug("Attempting SSML generation for done-for-day")
            try:
                ssml_output = self.ssml_renderer(result["has_meetings_today"], speech_text)
                if ssml_output:
                    logger.info("Done-for-day SSML generated: %d characters", len(ssml_output))
                else:
                    logger.warning("Done-for-day SSML generation returned None")
            except Exception as e:
                logger.error("Done-for-day SSML generation failed: %s", e, exc_info=True)

        # Build response
        response_data = {
            "now_iso": self.iso_serializer(now) if self.iso_serializer else now.isoformat() + "Z",
            "tz": request_tz,
            **result,
            "speech_text": speech_text,
        }

        # Add SSML and card data for Alexa if available
        if ssml_output:
            response_data["ssml"] = ssml_output
            response_data["card"] = {
                "title": "Done for the Day",
                "content": speech_text,
            }

        return web.json_response(response_data, status=200)

    def _compute_last_meeting_end_for_today(
        self,
        request_tz: str | None,
        event_window: tuple[dict[str, Any], ...],
    ) -> dict[str, Any]:
        """Compute the last meeting end time for today from the event window.

        Args:
            request_tz: Optional timezone string for date comparison
            event_window: Tuple of event dictionaries from the in-memory window

        Returns:
            Dictionary with has_meetings_today, last_meeting_start_iso, last_meeting_end_iso, etc.
        """
        now_utc = self.time_provider()

        # Parse timezone or fallback to UTC
        try:
            if request_tz:
                import zoneinfo

                tz = zoneinfo.ZoneInfo(request_tz)
            else:
                tz = datetime.timezone.utc  # type: ignore[assignment]
        except Exception:
            logger.warning("Invalid timezone %r, falling back to UTC", request_tz)
            tz = datetime.timezone.utc  # type: ignore[assignment]

        # Get today's date in the target timezone
        today_date = now_utc.astimezone(tz).date()

        latest_end_utc = None
        latest_start_utc = None
        meetings_found = 0

        # Process events in the window
        for ev in event_window:
            try:
                # Get event start time
                start = ev.get("start")
                if not isinstance(start, datetime.datetime):
                    continue

                # Convert to target timezone for date comparison
                start_local = start.astimezone(tz)
                if start_local.date() != today_date:
                    continue  # Not today

                # Check if meeting is skipped
                if self._is_skipped(ev):
                    continue

                meetings_found += 1

                # Calculate event end time with 1-hour fallback
                duration_seconds = ev.get("duration_seconds")
                if not isinstance(duration_seconds, int) or duration_seconds <= 0:
                    duration_seconds = 3600  # 1-hour fallback

                end_utc = start + datetime.timedelta(seconds=duration_seconds)

                # Track latest end time
                if latest_end_utc is None or end_utc > latest_end_utc:
                    latest_end_utc = end_utc
                    latest_start_utc = start

            except Exception as e:
                logger.warning("Error processing event for done-for-day: %s", e)
                continue

        # Build result
        has_meetings = meetings_found > 0

        result = {
            "has_meetings_today": has_meetings,
            "last_meeting_start_iso": (
                self.iso_serializer(latest_start_utc)
                if self.iso_serializer and latest_start_utc
                else (latest_start_utc.isoformat() + "Z" if latest_start_utc else None)
            ),
            "last_meeting_end_iso": (
                self.iso_serializer(latest_end_utc)
                if self.iso_serializer and latest_end_utc
                else (latest_end_utc.isoformat() + "Z" if latest_end_utc else None)
            ),
            "last_meeting_end_local_iso": (
                latest_end_utc.astimezone(tz).isoformat() if latest_end_utc else None
            ),
            "note": None,
        }

        logger.debug(
            "Done-for-day result: has_meetings=%s, meetings_found=%d",
            has_meetings,
            meetings_found,
        )

        return result

    def _generate_speech_text(
        self,
        result: dict[str, Any],
        request_tz: str | None,
        now: datetime.datetime,
    ) -> str:
        """Generate speech text based on done-for-day result."""
        if result["has_meetings_today"]:
            if result["last_meeting_end_iso"]:
                # Parse the end time for speech formatting
                try:
                    import zoneinfo

                    end_utc = datetime.datetime.fromisoformat(
                        result["last_meeting_end_iso"].replace("Z", "+00:00")
                    )

                    # Convert to local time for speech
                    if request_tz:
                        try:
                            tz = zoneinfo.ZoneInfo(request_tz)
                            end_local = end_utc.astimezone(tz)
                            time_str = end_local.strftime("%-I:%M %p").lower()
                        except Exception:
                            time_str = end_utc.strftime("%-I:%M %p UTC").lower()
                    else:
                        time_str = end_utc.strftime("%-I:%M %p UTC").lower()

                    # Compare current time with last meeting end time
                    if now >= end_utc:
                        # All meetings for today have ended
                        return "You're all done for today!"
                    # Still have meetings, will be done at end time
                    return f"You'll be done at {time_str}."

                except Exception as e:
                    logger.warning("Error formatting end time for speech: %s", e)
                    return "You have meetings today, but I couldn't determine when your last one ends."
            else:
                return "You have meetings today, but I couldn't determine when your last one ends."
        else:
            return "You have no meetings today. Enjoy your free day!"


class LaunchSummaryHandler(AlexaEndpointBase):
    """Handler for /api/alexa/launch-summary endpoint."""

    def __init__(
        self,
        bearer_token: Optional[str],
        time_provider: Any,
        skipped_store: object | None,
        ssml_renderers: dict[str, Any] | None = None,
        duration_formatter: Any = None,
        iso_serializer: Any = None,
        get_server_timezone: Any = None,
    ):
        """Initialize launch summary handler.

        Args:
            bearer_token: Bearer token for auth
            time_provider: Time provider callable
            skipped_store: Skipped events store
            ssml_renderers: Dictionary of SSML rendering functions
            duration_formatter: Function to format duration for speech
            iso_serializer: Function to serialize datetime to ISO string
            get_server_timezone: Function to get server timezone
        """
        super().__init__(bearer_token, time_provider, skipped_store)
        self.ssml_renderers = ssml_renderers or {}
        self.duration_formatter = duration_formatter
        self.iso_serializer = iso_serializer
        self.get_server_timezone = get_server_timezone

    async def handle_request(
        self,
        request: Any,
        window: tuple[dict[str, Any], ...],
        now: datetime.datetime,
    ) -> Any:
        """Handle launch summary request."""
        from aiohttp import web

        # Get timezone parameter from query string
        request_tz = request.query.get("tz")

        logger.debug(
            "Alexa /api/alexa/launch-summary called - window has %d events, tz=%s",
            len(window),
            request_tz,
        )

        # Create a temporary DoneForDayHandler instance to reuse the computation logic
        done_handler = DoneForDayHandler(
            self.bearer_token,
            self.time_provider,
            self.skipped_store,
            None,
            self.iso_serializer,
            self.get_server_timezone,
        )
        done_for_day_result = done_handler._compute_last_meeting_end_for_today(request_tz, window)  # noqa: SLF001

        # Parse timezone for date comparison
        try:
            if request_tz:
                import zoneinfo

                tz = zoneinfo.ZoneInfo(request_tz)
            else:
                tz = datetime.timezone.utc  # type: ignore[assignment]
        except Exception:
            tz = datetime.timezone.utc  # type: ignore[assignment]

        today_date = now.astimezone(tz).date()

        # Initialize meeting variables
        next_meeting_today = None
        future_meeting = None

        # Build speech response based on whether there are meetings today
        if not done_for_day_result["has_meetings_today"]:
            # No meetings today case - find next future meeting beyond today
            for ev in window:
                start = ev.get("start")
                if not isinstance(start, datetime.datetime):
                    continue

                start_local = start.astimezone(tz)
                if start_local.date() <= today_date:
                    continue  # Skip today's meetings and past meetings

                # Check if skipped
                if self._is_skipped(ev):
                    continue

                seconds_until = int((start - now).total_seconds())
                future_meeting = {
                    "event": ev,
                    "seconds_until": seconds_until,
                    "subject": ev.get("subject", "Untitled meeting"),
                    "duration_spoken": (
                        self.duration_formatter(seconds_until) if self.duration_formatter else ""
                    ),
                }
                break

            if future_meeting:
                speech_text = f"No meetings today, you're free until {future_meeting['subject']} {future_meeting['duration_spoken']}."
            else:
                speech_text = "No meetings today. You have no upcoming meetings scheduled."

        else:
            # Have meetings today case - find next meeting today
            for ev in window:
                start = ev.get("start")
                if not isinstance(start, datetime.datetime):
                    continue

                start_local = start.astimezone(tz)
                if start_local.date() != today_date:
                    continue  # Skip non-today meetings

                seconds_until = int((start - now).total_seconds())
                if seconds_until < 0:
                    continue  # Skip past meetings

                if self._is_skipped(ev):
                    continue

                next_meeting_today = {
                    "event": ev,
                    "seconds_until": seconds_until,
                    "subject": ev.get("subject", "Untitled meeting"),
                    "duration_spoken": (
                        self.duration_formatter(seconds_until) if self.duration_formatter else ""
                    ),
                }
                break

            if next_meeting_today:
                speech_text = f"Your next meeting is {next_meeting_today['subject']} {next_meeting_today['duration_spoken']}."
            else:
                speech_text = "You have no more meetings today."

            # Add done-for-day information if we have meetings today
            if done_for_day_result["last_meeting_end_iso"]:
                try:
                    import zoneinfo

                    end_utc = datetime.datetime.fromisoformat(
                        done_for_day_result["last_meeting_end_iso"].replace("Z", "+00:00")
                    )

                    # Convert to local time for speech
                    if request_tz:
                        try:
                            tz = zoneinfo.ZoneInfo(request_tz)
                            end_local = end_utc.astimezone(tz)
                            time_str = end_local.strftime("%-I:%M %p").lower()
                        except Exception:
                            time_str = end_utc.strftime("%-I:%M %p UTC").lower()
                    else:
                        time_str = end_utc.strftime("%-I:%M %p UTC").lower()

                    if now >= end_utc:
                        speech_text += " You're all done for today!"
                    else:
                        speech_text += f" You'll be done for the day at {time_str}."

                except Exception as e:
                    logger.warning("Error formatting end time for launch summary: %s", e)
                    speech_text += " I couldn't determine when your last meeting ends today."

        # Determine which meeting to use for SSML and response building
        primary_meeting = None
        if done_for_day_result["has_meetings_today"] and next_meeting_today is not None:
            primary_meeting = next_meeting_today
        elif not done_for_day_result["has_meetings_today"] and future_meeting is not None:
            primary_meeting = future_meeting

        # Generate SSML if available - reuse existing SSML functions
        ssml_output = None
        if (
            done_for_day_result["has_meetings_today"]
            and primary_meeting
            and "meeting" in self.ssml_renderers
        ):
            # Meetings today case - use meeting SSML
            logger.debug("Attempting SSML generation for launch summary with meetings today")
            try:
                meeting_data = {
                    "subject": primary_meeting["subject"],
                    "seconds_until_start": primary_meeting["seconds_until"],
                    "duration_spoken": primary_meeting["duration_spoken"],
                    "location": primary_meeting["event"].get("location", ""),
                    "is_online_meeting": primary_meeting["event"].get("is_online_meeting", False),
                }
                # Use the meeting SSML renderer for meetings today
                base_ssml = self.ssml_renderers["meeting"](meeting_data)
                if base_ssml:
                    ssml_output = base_ssml
                    logger.info(
                        "Launch summary (meetings today) SSML generated: %d characters",
                        len(ssml_output),
                    )
            except Exception as e:
                logger.error(
                    "Launch summary (meetings today) SSML generation failed: %s", e, exc_info=True
                )
        elif "done_for_day" in self.ssml_renderers:
            # No meetings today case - use done-for-day SSML
            logger.debug("Attempting SSML generation for launch summary (no meetings today)")
            try:
                ssml_output = self.ssml_renderers["done_for_day"](
                    done_for_day_result["has_meetings_today"], speech_text
                )
                if ssml_output:
                    logger.info(
                        "Launch summary (no meetings today) SSML generated: %d characters",
                        len(ssml_output),
                    )
            except Exception as e:
                logger.error(
                    "Launch summary (no meetings today) SSML generation failed: %s",
                    e,
                    exc_info=True,
                )

        # Build response
        response_data = {
            "speech_text": speech_text,
            "has_meetings_today": done_for_day_result["has_meetings_today"],
            "next_meeting": {
                "subject": primary_meeting["subject"],
                "start_iso": (
                    self.iso_serializer(primary_meeting["event"].get("start"))
                    if self.iso_serializer
                    else primary_meeting["event"].get("start").isoformat() + "Z"
                ),
                "seconds_until_start": primary_meeting["seconds_until"],
                "duration_spoken": primary_meeting["duration_spoken"],
            }
            if primary_meeting
            else None,
            "done_for_day": done_for_day_result,
        }

        # Add SSML to response if generated
        if ssml_output:
            response_data["ssml"] = ssml_output

        return web.json_response(response_data, status=200)


class MorningSummaryHandler(AlexaEndpointBase):
    """Handler for /api/alexa/morning-summary endpoint."""

    def __init__(
        self,
        bearer_token: Optional[str],
        time_provider: Any,
        skipped_store: object | None,
        ssml_renderer: Any = None,
        get_server_timezone: Any = None,
    ):
        """Initialize morning summary handler.

        Args:
            bearer_token: Bearer token for auth
            time_provider: Time provider callable
            skipped_store: Skipped events store
            ssml_renderer: Optional SSML rendering function for morning summary
            get_server_timezone: Function to get server timezone
        """
        super().__init__(bearer_token, time_provider, skipped_store)
        self.ssml_renderer = ssml_renderer
        self.get_server_timezone = get_server_timezone

    async def handle_request(
        self,
        request: Any,
        window: tuple[dict[str, Any], ...],
        now: datetime.datetime,
    ) -> Any:
        """Handle morning summary request."""
        from aiohttp import web

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

            # Convert raw events to LiteCalendarEvent objects for morning summary service
            from .lite_models import (
                LiteCalendarEvent,
                LiteDateTimeInfo,
                LiteEventStatus,
                LiteLocation,
            )
            from .morning_summary import MorningSummaryRequest, MorningSummaryService

            lite_events = []
            for ev in window:
                try:
                    # Convert raw event dict to LiteCalendarEvent
                    start_dt = ev.get("start")
                    duration_seconds = ev.get("duration_seconds", 3600)  # Default 1 hour

                    if not isinstance(start_dt, datetime.datetime):
                        continue

                    end_dt = start_dt + datetime.timedelta(seconds=duration_seconds)

                    # Create location object if location exists
                    location_obj = None
                    if ev.get("location"):
                        location_obj = LiteLocation(display_name=ev.get("location", ""))

                    lite_event = LiteCalendarEvent(
                        id=ev.get("meeting_id", f"event_{id(ev)}"),  # Use meeting_id or fallback
                        subject=ev.get("subject", "Untitled meeting"),
                        start=LiteDateTimeInfo(date_time=start_dt),
                        end=LiteDateTimeInfo(date_time=end_dt),
                        location=location_obj,
                        is_online_meeting=ev.get("is_online_meeting", False),
                        is_cancelled=False,  # Assume not cancelled if in window
                        show_as=LiteEventStatus.BUSY,  # Default to busy
                    )
                    lite_events.append(lite_event)
                except Exception as e:
                    logger.warning("Failed to convert event to LiteCalendarEvent: %s", e)
                    continue

            # Create morning summary request
            summary_request = MorningSummaryRequest(
                date=target_date,
                timezone=timezone_str,
                detail_level=detail_level,
                prefer_ssml=prefer_ssml,
                max_events=max_events,
            )

            # Generate morning summary
            service = MorningSummaryService()
            summary_result = await service.generate_summary(lite_events, summary_request)

            # Generate SSML if requested and available
            ssml_output = None
            if prefer_ssml and summary_result.speech_text and self.ssml_renderer:
                try:
                    ssml_output = self.ssml_renderer(summary_result)
                    if ssml_output:
                        logger.info(
                            "Morning summary SSML generated: %d characters", len(ssml_output)
                        )
                except Exception as e:
                    logger.error("Morning summary SSML generation failed: %s", e, exc_info=True)

            # Build response following existing Alexa endpoint patterns
            response_data = {
                "speech_text": summary_result.speech_text,
                "summary": {
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
                },
            }

            # Add SSML to response if generated
            if ssml_output:
                response_data["ssml"] = ssml_output

            return web.json_response(response_data, status=200)

        except Exception as e:
            logger.error("Morning summary endpoint failed: %s", e, exc_info=True)
            return web.json_response(
                {
                    "error": "Internal server error",
                    "speech_text": "Sorry, I couldn't generate your morning summary right now. Please try again later.",
                },
                status=500,
            )
