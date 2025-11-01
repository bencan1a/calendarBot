"""Main API routes for calendarbot_lite."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_api_routes(
    app: Any,
    config: Any,
    skipped_store: object | None,
    event_window_ref: list[tuple[dict[str, Any], ...]],
    window_lock: Any,
    shared_http_client: Any,
    health_tracker: Any,
    time_provider: Any,
    event_to_api_model: Any,
    is_focus_time_event: Any,
    serialize_iso: Any,
    get_system_diagnostics: Any,
) -> None:
    """Register main API routes.

    Args:
        app: aiohttp web application
        config: Application configuration
        skipped_store: Optional skipped events store
        event_window_ref: Reference to event window
        window_lock: Lock for thread-safe window access
        shared_http_client: Shared HTTP client
        health_tracker: Health tracking instance
        time_provider: Time provider callable
        event_to_api_model: Function to convert event to API model
        is_focus_time_event: Function to check if event is focus time
        serialize_iso: Function to serialize datetime to ISO string
        get_system_diagnostics: Function to get system diagnostics
    """
    from aiohttp import web

    async def health_check(_request: Any) -> Any:
        """Health check endpoint for monitoring system status."""
        now = time_provider()
        now_iso = now.isoformat() + "Z"

        # Get health status from tracker
        health_status = health_tracker.get_health_status(now_iso)

        # Get system diagnostics
        diag = get_system_diagnostics()

        # Build comprehensive health response
        health_data = {
            "status": health_status.status,
            "server_time_iso": health_status.server_time_iso,
            "server_status": {
                "uptime_s": health_status.uptime_seconds,
                "pid": health_status.pid,
            },
            "data_status": {
                "event_count": health_status.event_count,
                "last_refresh_success_age_s": health_status.last_refresh_success_age_seconds,
            },
            "background_tasks": health_status.background_tasks,
            "system_diagnostics": {
                "platform": diag.platform,
                "python_version": diag.python_version,
                "event_loop_running": diag.event_loop_running,
            },
        }

        # Return appropriate HTTP status based on health
        http_status = 200 if health_status.status == "ok" else 503
        return web.json_response(health_data, status=http_status)

    async def whats_next(_request: Any) -> Any:
        """Find the next upcoming event with smart prioritization logic."""
        from ..event_prioritizer import EventPrioritizer

        now = time_provider()

        # Read window with lock to be consistent
        async with window_lock:
            window = tuple(event_window_ref[0])

        logger.debug(" /api/whats-next called - window has %d events", len(window))

        # Use event prioritizer to find next event with business logic
        prioritizer = EventPrioritizer(is_focus_time_event)
        result = prioritizer.find_next_event(window, now, skipped_store)

        if result is None:
            # No upcoming events found
            return web.json_response({"meeting": None}, status=200)

        # Unpack result and build response
        event, seconds_until = result
        model = event_to_api_model(event)
        model["seconds_until_start"] = seconds_until

        return web.json_response({"meeting": model}, status=200)

    async def post_skip(request: Any) -> Any:
        """Skip a meeting by ID."""
        if skipped_store is None:
            return web.json_response({"error": "skip-store not available"}, status=501)
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid json"}, status=400)

        meeting_id = data.get("meeting_id") if isinstance(data, dict) else None
        if not meeting_id or not isinstance(meeting_id, str):
            return web.json_response({"error": "missing or invalid meeting_id"}, status=400)

        add_skip = getattr(skipped_store, "add_skip", None)
        if not callable(add_skip):
            return web.json_response({"error": "skip-store missing add_skip"}, status=501)

        try:
            result = add_skip(meeting_id)
            if asyncio.iscoroutine(result):
                result = await result
        except Exception:
            logger.exception("skipped_store.add_skip failed")
            return web.json_response({"error": "failed to add skip"}, status=500)

        # Normalize result into ISO timestamp if possible
        skipped_until_iso = None
        if isinstance(result, type(time_provider())):  # datetime
            skipped_until_iso = serialize_iso(result)
        elif isinstance(result, str):
            skipped_until_iso = result

        return web.json_response({"skipped_until": skipped_until_iso}, status=200)

    async def delete_skip(_request: Any) -> Any:
        """Clear all skipped meetings."""
        if skipped_store is None:
            return web.json_response({"error": "skip-store not available"}, status=501)

        clear_all = getattr(skipped_store, "clear_all", None)
        if not callable(clear_all):
            return web.json_response({"error": "skip-store missing clear_all"}, status=501)

        try:
            res = clear_all()
            if asyncio.iscoroutine(res):
                res = await res
        except Exception:
            logger.exception("skipped_store.clear_all failed")
            return web.json_response({"error": "failed to clear skips"}, status=500)

        count = int(res) if isinstance(res, int) else 0
        return web.json_response({"cleared": True, "count": count}, status=200)

    async def clear_skips(_request: Any) -> Any:
        """Convenient GET endpoint to clear all skipped meetings."""
        if skipped_store is None:
            return web.json_response({"error": "skip-store not available"}, status=501)

        clear_all = getattr(skipped_store, "clear_all", None)
        if not callable(clear_all):
            return web.json_response({"error": "skip-store missing clear_all"}, status=501)

        try:
            res = clear_all()
            if asyncio.iscoroutine(res):
                res = await res
        except Exception:
            logger.exception("skipped_store.clear_all failed")
            return web.json_response({"error": "failed to clear skips"}, status=500)

        count = int(res) if isinstance(res, int) else 0

        # Force immediate cache refresh to restore previously skipped meetings
        # Import refresh function dynamically to avoid circular imports
        from .. import server as server_module
        try:
            await server_module._refresh_once(  # noqa: SLF001
                config, skipped_store, event_window_ref, window_lock, shared_http_client
            )
            logger.debug("Refreshed event cache after clearing %d skipped meetings", count)
        except Exception:
            logger.exception("Failed to refresh cache after clearing skips")
            return web.json_response(
                {"error": "cleared skips but failed to refresh cache"}, status=500
            )

        return web.json_response(
            {"cleared": True, "count": count, "message": f"Cleared {count} skipped meetings"},
            status=200,
        )

    # Register API routes
    app.router.add_get("/api/health", health_check)
    app.router.add_get("/api/whats-next", whats_next)
    app.router.add_post("/api/skip", post_skip)
    app.router.add_delete("/api/skip", delete_skip)
    app.router.add_get("/api/clear_skips", clear_skips)

    logger.debug("API routes registered")
