"""Alexa-specific API routes using consolidated handlers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any, Optional

from aiohttp import web

from calendarbot_lite.alexa.alexa_handlers import (
    AlexaEndpointBase,
    DoneForDayHandler,
    LaunchSummaryHandler,
    MorningSummaryHandler,
    NextMeetingHandler,
    TimeUntilHandler,
)
from calendarbot_lite.alexa.alexa_presentation import SSMLPresenter
from calendarbot_lite.calendar.lite_models import LiteCalendarEvent

logger = logging.getLogger(__name__)


def register_alexa_routes(
    app: web.Application,
    bearer_token: Optional[str],
    event_window_ref: list[tuple[LiteCalendarEvent, ...]],
    window_lock: asyncio.Lock,
    skipped_store: Any,
    time_provider: Callable[[], Any],
    duration_formatter: Callable[[int], str],
    iso_serializer: Callable[[Any], str],
    ssml_renderers: dict[str, object],
    get_server_timezone: Optional[Callable[[], str]] = None,
    response_cache: Any = None,
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
        response_cache: Optional ResponseCache for caching handler responses
    """
    # Create presenters for different handlers
    # NextMeetingHandler uses meeting SSML renderer
    next_meeting_presenter = SSMLPresenter({"meeting": ssml_renderers.get("meeting")})

    # TimeUntilHandler uses time_until SSML renderer
    time_until_presenter = SSMLPresenter({"time_until": ssml_renderers.get("time_until")})

    # DoneForDayHandler uses done_for_day SSML renderer
    done_for_day_presenter = SSMLPresenter({"done_for_day": ssml_renderers.get("done_for_day")})

    # LaunchSummaryHandler uses both meeting and done_for_day SSML renderers
    launch_summary_presenter = SSMLPresenter(ssml_renderers)

    # MorningSummaryHandler uses morning_summary SSML renderer
    morning_summary_presenter = SSMLPresenter(
        {"morning_summary": ssml_renderers.get("morning_summary")}
    )

    # Create handler instances with presenters
    next_meeting_handler = NextMeetingHandler(
        bearer_token=bearer_token,
        time_provider=time_provider,
        skipped_store=skipped_store,
        response_cache=response_cache,
        presenter=next_meeting_presenter,
        duration_formatter=duration_formatter,
        iso_serializer=iso_serializer,
    )

    time_until_handler = TimeUntilHandler(
        bearer_token=bearer_token,
        time_provider=time_provider,
        skipped_store=skipped_store,
        response_cache=response_cache,
        presenter=time_until_presenter,
        duration_formatter=duration_formatter,
    )

    done_for_day_handler = DoneForDayHandler(
        bearer_token=bearer_token,
        time_provider=time_provider,
        skipped_store=skipped_store,
        response_cache=response_cache,
        presenter=done_for_day_presenter,
        iso_serializer=iso_serializer,
        get_server_timezone=get_server_timezone,
    )

    launch_summary_handler = LaunchSummaryHandler(
        bearer_token=bearer_token,
        time_provider=time_provider,
        skipped_store=skipped_store,
        response_cache=response_cache,
        presenter=launch_summary_presenter,
        duration_formatter=duration_formatter,
        iso_serializer=iso_serializer,
        get_server_timezone=get_server_timezone,
    )

    morning_summary_handler = MorningSummaryHandler(
        bearer_token=bearer_token,
        time_provider=time_provider,
        skipped_store=skipped_store,
        response_cache=response_cache,
        presenter=morning_summary_presenter,
        get_server_timezone=get_server_timezone,
    )

    # Map handler instances to their registered routes using the registry
    from collections.abc import Awaitable

    handler_map: dict[str, AlexaEndpointBase] = {
        "/api/alexa/next-meeting": next_meeting_handler,
        "/api/alexa/time-until-next": time_until_handler,
        "/api/alexa/done-for-day": done_for_day_handler,
        "/api/alexa/launch-summary": launch_summary_handler,
        "/api/alexa/morning-summary": morning_summary_handler,
    }

    # Register routes using the handler map
    registered_routes = []
    for route, handler in handler_map.items():

        def create_route_handler(
            handler_instance: AlexaEndpointBase,
        ) -> Callable[[web.Request], Awaitable[web.Response]]:
            """Create route handler closure with proper handler binding."""

            async def route_handler(request: web.Request) -> web.Response:
                return await handler_instance.handle(request, event_window_ref, window_lock)

            return route_handler

        route_handler_func = create_route_handler(handler)
        app.router.add_get(route, route_handler_func)
        registered_routes.append(route)

    logger.debug(
        "Registered %d Alexa routes: %s",
        len(registered_routes),
        ", ".join(registered_routes),
    )
