"""Alexa-specific API routes using consolidated handlers."""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..alexa_presentation import SSMLPresenter
from ..alexa_registry import AlexaHandlerRegistry

logger = logging.getLogger(__name__)


def register_alexa_routes(
    app: Any,
    bearer_token: Optional[str],
    event_window_ref: list[tuple[Any, ...]],
    window_lock: Any,
    skipped_store: object | None,
    time_provider: Any,
    duration_formatter: Any,
    iso_serializer: Any,
    ssml_renderers: dict[str, Any],
    get_server_timezone: Any = None,
    response_cache: Optional[Any] = None,
    precompute_getter: Optional[Any] = None,
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
        precompute_getter: Optional function to get precomputed responses
    """
    from ..alexa_handlers import (
        DoneForDayHandler,
        LaunchSummaryHandler,
        MorningSummaryHandler,
        NextMeetingHandler,
        TimeUntilHandler,
    )

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
    # Note: pyright false positives for presenter params due to function-scoped imports
    next_meeting_handler = NextMeetingHandler(
        bearer_token=bearer_token,
        time_provider=time_provider,
        skipped_store=skipped_store,
        response_cache=response_cache,
        precompute_getter=precompute_getter,
        presenter=next_meeting_presenter,  # pyright: ignore[reportCallIssue]
        duration_formatter=duration_formatter,  # pyright: ignore[reportCallIssue]
        iso_serializer=iso_serializer,  # pyright: ignore[reportCallIssue]
    )

    time_until_handler = TimeUntilHandler(
        bearer_token=bearer_token,
        time_provider=time_provider,
        skipped_store=skipped_store,
        response_cache=response_cache,
        precompute_getter=precompute_getter,
        presenter=time_until_presenter,  # pyright: ignore[reportCallIssue]
        duration_formatter=duration_formatter,  # pyright: ignore[reportCallIssue]
    )

    done_for_day_handler = DoneForDayHandler(
        bearer_token=bearer_token,
        time_provider=time_provider,
        skipped_store=skipped_store,
        response_cache=response_cache,
        precompute_getter=precompute_getter,
        presenter=done_for_day_presenter,  # pyright: ignore[reportCallIssue]
        iso_serializer=iso_serializer,  # pyright: ignore[reportCallIssue]
        get_server_timezone=get_server_timezone,  # pyright: ignore[reportCallIssue]
    )

    launch_summary_handler = LaunchSummaryHandler(
        bearer_token=bearer_token,
        time_provider=time_provider,
        skipped_store=skipped_store,
        response_cache=response_cache,
        precompute_getter=precompute_getter,
        presenter=launch_summary_presenter,  # pyright: ignore[reportCallIssue]
        duration_formatter=duration_formatter,  # pyright: ignore[reportCallIssue]
        iso_serializer=iso_serializer,  # pyright: ignore[reportCallIssue]
        get_server_timezone=get_server_timezone,  # pyright: ignore[reportCallIssue]
    )

    morning_summary_handler = MorningSummaryHandler(
        bearer_token=bearer_token,
        time_provider=time_provider,
        skipped_store=skipped_store,
        response_cache=response_cache,
        precompute_getter=precompute_getter,
        presenter=morning_summary_presenter,  # pyright: ignore[reportCallIssue]
        get_server_timezone=get_server_timezone,  # pyright: ignore[reportCallIssue]
    )

    # Map handler instances to their registered routes using the registry
    handler_map: dict[str, Any] = {
        "/api/alexa/next-meeting": next_meeting_handler,
        "/api/alexa/time-until-next": time_until_handler,
        "/api/alexa/done-for-day": done_for_day_handler,
        "/api/alexa/launch-summary": launch_summary_handler,
        "/api/alexa/morning-summary": morning_summary_handler,
    }

    # Validate all registered handlers have been instantiated
    registry_routes = AlexaHandlerRegistry.get_routes()
    for route, info in registry_routes.items():
        if route not in handler_map:
            logger.warning(
                "Handler registered in registry but not instantiated: %s (%s)",
                info.intent,
                route,
            )

    # Register routes using the handler map
    registered_routes = []
    for route, handler in handler_map.items():

        def create_route_handler(handler_instance: Any) -> Any:
            """Create route handler closure with proper handler binding."""

            async def route_handler(request: Any) -> Any:
                return await handler_instance.handle(request, event_window_ref, window_lock)

            return route_handler

        route_handler_func = create_route_handler(handler)
        app.router.add_get(route, route_handler_func)
        registered_routes.append(route)

    logger.info(
        "Registered %d Alexa routes: %s", len(registered_routes), ", ".join(registered_routes)
    )
