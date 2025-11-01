"""Alexa-specific API routes using consolidated handlers."""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def register_alexa_routes(
    app: Any,
    bearer_token: Optional[str],
    event_window_ref: list[tuple[dict[str, Any], ...]],
    window_lock: Any,
    skipped_store: object | None,
    time_provider: Any,
    duration_formatter: Any,
    iso_serializer: Any,
    ssml_renderers: dict[str, Any],
    get_server_timezone: Any = None,
) -> None:
    """Register Alexa-specific API routes using consolidated handlers.

    Args:
        app: aiohttp web application
        bearer_token: Bearer token for Alexa endpoint authentication
        event_window_ref: Reference to event window
        window_lock: Lock for thread-safe window access
        skipped_store: Optional skipped events store
        time_provider: Function to get current UTC time
        duration_formatter: Function to format duration for speech
        iso_serializer: Function to serialize datetime to ISO string
        ssml_renderers: Dictionary of SSML rendering functions
        get_server_timezone: Optional function to get server timezone
    """
    from ..alexa_handlers import (
        DoneForDayHandler,
        LaunchSummaryHandler,
        MorningSummaryHandler,
        NextMeetingHandler,
        TimeUntilHandler,
    )

    # Create handler instances with dependencies
    next_meeting_handler = NextMeetingHandler(
        bearer_token=bearer_token,
        time_provider=time_provider,
        skipped_store=skipped_store,
        ssml_renderer=ssml_renderers.get("meeting"),
        duration_formatter=duration_formatter,
        iso_serializer=iso_serializer,
    )

    time_until_handler = TimeUntilHandler(
        bearer_token=bearer_token,
        time_provider=time_provider,
        skipped_store=skipped_store,
        ssml_renderer=ssml_renderers.get("time_until"),
        duration_formatter=duration_formatter,
    )

    done_for_day_handler = DoneForDayHandler(
        bearer_token=bearer_token,
        time_provider=time_provider,
        skipped_store=skipped_store,
        ssml_renderer=ssml_renderers.get("done_for_day"),
        iso_serializer=iso_serializer,
        get_server_timezone=get_server_timezone,
    )

    launch_summary_handler = LaunchSummaryHandler(
        bearer_token=bearer_token,
        time_provider=time_provider,
        skipped_store=skipped_store,
        ssml_renderers=ssml_renderers,
        duration_formatter=duration_formatter,
        iso_serializer=iso_serializer,
        get_server_timezone=get_server_timezone,
    )

    morning_summary_handler = MorningSummaryHandler(
        bearer_token=bearer_token,
        time_provider=time_provider,
        skipped_store=skipped_store,
        ssml_renderer=ssml_renderers.get("morning_summary"),
        get_server_timezone=get_server_timezone,
    )

    # Register Alexa routes with handlers
    async def alexa_next_meeting(request: Any) -> Any:
        """Alexa endpoint for getting next meeting with speech formatting."""
        return await next_meeting_handler.handle(request, event_window_ref, window_lock)

    async def alexa_time_until_next(request: Any) -> Any:
        """Alexa endpoint for getting time until next meeting."""
        return await time_until_handler.handle(request, event_window_ref, window_lock)

    async def alexa_done_for_day(request: Any) -> Any:
        """Alexa endpoint for getting done-for-day status with SSML."""
        return await done_for_day_handler.handle(request, event_window_ref, window_lock)

    async def alexa_launch_summary(request: Any) -> Any:
        """Alexa endpoint for launch intent - comprehensive summary with SSML."""
        return await launch_summary_handler.handle(request, event_window_ref, window_lock)

    async def alexa_morning_summary(request: Any) -> Any:
        """Alexa endpoint for morning summary with intelligent context switching."""
        return await morning_summary_handler.handle(request, event_window_ref, window_lock)

    # Register all Alexa endpoints
    app.router.add_get("/api/alexa/next-meeting", alexa_next_meeting)
    app.router.add_get("/api/alexa/time-until-next", alexa_time_until_next)
    app.router.add_get("/api/alexa/done-for-day", alexa_done_for_day)
    app.router.add_get("/api/alexa/launch-summary", alexa_launch_summary)
    app.router.add_get("/api/alexa/morning-summary", alexa_morning_summary)

    logger.debug(
        "Alexa routes registered (next-meeting, time-until-next, done-for-day, "
        "launch-summary, morning-summary)"
    )
