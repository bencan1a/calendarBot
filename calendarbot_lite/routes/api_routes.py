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
    event_window_ref: list[tuple[Any, ...]],
    window_lock: Any,
    shared_http_client: Any,
    health_tracker: Any,
    time_provider: Any,
    event_to_api_model: Any,
    is_focus_time_event: Any,
    serialize_iso: Any,
    get_system_diagnostics: Any,
    compute_last_meeting_end_for_today: Any,
    get_server_timezone: Any,
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
        compute_last_meeting_end_for_today: Function to compute last meeting end time
        get_server_timezone: Function to get server timezone
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

        # Get display probe data
        last_probe_ts = health_tracker.get_last_render_probe_timestamp()
        last_probe_iso = None if last_probe_ts is None else serialize_iso(time_provider().replace(microsecond=0).fromtimestamp(last_probe_ts))

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
            "display_probe": {
                "last_render_probe_iso": last_probe_iso,
                "last_probe_ok": health_tracker.get_last_render_probe_ok(),
                "last_probe_notes": health_tracker.get_last_render_probe_notes(),
            },
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

    async def browser_heartbeat(_request: Any) -> Any:
        """Browser heartbeat endpoint to detect stuck/frozen browsers.

        Called periodically by JavaScript in the browser to prove the page is
        alive and rendering. Watchdog can check this to detect blank pages."""
        now = time_provider()
        now_iso = now.isoformat() + "Z"

        # Record that browser sent a heartbeat
        health_tracker.record_render_probe(ok=True, notes="browser-heartbeat")
        logger.debug("Browser heartbeat received at %s", now_iso)

        return web.json_response({"status": "ok", "timestamp": now_iso}, status=200)

    async def done_for_day(request: Any) -> Any:
        """API endpoint for getting last meeting end time for today."""
        now = time_provider()

        # Get timezone parameter from query string
        request_tz = request.query.get("tz")

        # Read window with lock to be consistent
        async with window_lock:
            window = tuple(event_window_ref[0])

        logger.debug(
            "/api/done-for-day called - window has %d events, tz=%s", len(window), request_tz
        )

        # Compute last meeting end for today
        result = compute_last_meeting_end_for_today(request_tz, window, skipped_store)

        # Build full response with current time and timezone info
        response = {
            "now_iso": serialize_iso(now),
            "tz": request_tz,
            **result,
        }

        return web.json_response(response, status=200)

    async def morning_summary(request: Any) -> Any:
        """General API endpoint for morning summary with full structured data.

        Returns comprehensive morning summary data for programmatic consumption,
        excluding Alexa-specific fields like speech_text and ssml.

        Query Parameters:
            date (str, optional): ISO date for summary (defaults to tomorrow)
            timezone (str, optional): IANA timezone identifier (default: UTC)
            detail_level (str, optional): Detail level: brief|normal|detailed (default: normal)
            max_events (int, optional): Maximum events to process (default: 50)

        Returns:
            JSON response with complete summary structure including timeframe,
            meeting analysis, free blocks, density metrics, and metadata.
        """

        try:
            # Parse request parameters
            target_date = request.query.get("date")  # ISO date for summary (defaults to tomorrow)
            timezone_str = request.query.get("timezone", get_server_timezone())
            detail_level = request.query.get("detail_level", "normal")
            max_events = int(request.query.get("max_events", "50"))

            logger.debug(
                "Morning summary called with tz=%s, detail_level=%s", timezone_str, detail_level
            )

            # Read window with lock to be consistent
            async with window_lock:
                window = tuple(event_window_ref[0])

            # Window now contains LiteCalendarEvent objects directly (no conversion needed)
            from ..morning_summary import MorningSummaryRequest, MorningSummaryService

            # Events are already LiteCalendarEvent objects from the event window
            lite_events = list(window)

            # Create morning summary request (no prefer_ssml for general API)
            summary_request = MorningSummaryRequest(
                date=target_date,
                timezone=timezone_str,
                detail_level=detail_level,
                prefer_ssml=False,  # General API doesn't need SSML
                max_events=max_events,
            )

            # Generate morning summary
            service = MorningSummaryService()
            summary_result = await service.generate_summary(lite_events, summary_request)

            # Build response with full structured data (exclude Alexa-specific fields)
            summary_data = {
                "timeframe_start": summary_result.timeframe_start.isoformat(),
                "timeframe_end": summary_result.timeframe_end.isoformat(),
                "analysis_time": summary_result.analysis_time.isoformat(),
                "total_meetings_equivalent": summary_result.total_meetings_equivalent,
                "early_start_flag": summary_result.early_start_flag,
                "density": summary_result.density,
                "back_to_back_count": summary_result.back_to_back_count,
                "meeting_insights": [
                    {
                        "meeting_id": insight.meeting_id,
                        "subject": insight.subject,
                        "start_time": insight.start_time.isoformat(),
                        "end_time": insight.end_time.isoformat(),
                        "time_until_minutes": insight.time_until_minutes,
                        "preparation_needed": insight.preparation_needed,
                        "is_online": insight.is_online,
                        "attendees_count": insight.attendees_count,
                        "short_note": insight.short_note,
                    }
                    for insight in summary_result.meeting_insights
                ],
                "free_blocks": [
                    {
                        "start_time": block.start_time.isoformat(),
                        "end_time": block.end_time.isoformat(),
                        "duration_minutes": block.duration_minutes,
                        "recommended_action": block.recommended_action,
                        "is_significant": block.is_significant,
                    }
                    for block in summary_result.free_blocks
                ],
                "metadata": summary_result.metadata,
            }

            # Add wake-up recommendation if available
            if summary_result.wake_up_recommendation_time:
                summary_data["wake_up_recommendation_time"] = (
                    summary_result.wake_up_recommendation_time.isoformat()
                )

            response_data = {"summary": summary_data}

            return web.json_response(response_data, status=200)

        except Exception:
            logger.exception("Morning summary endpoint failed")
            return web.json_response(
                {
                    "error": "Internal server error",
                    "message": "Failed to generate morning summary. Please try again later.",
                },
                status=500,
            )

    # Register API routes
    app.router.add_get("/api/health", health_check)
    app.router.add_post("/api/browser-heartbeat", browser_heartbeat)
    app.router.add_get("/api/whats-next", whats_next)
    app.router.add_post("/api/skip", post_skip)
    app.router.add_delete("/api/skip", delete_skip)
    app.router.add_get("/api/clear_skips", clear_skips)
    app.router.add_get("/api/done-for-day", done_for_day)
    app.router.add_post("/api/morning-summary", morning_summary)

    logger.debug("API routes registered")
