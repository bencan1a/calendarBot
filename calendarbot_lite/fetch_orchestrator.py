"""Fetch orchestration and refresh loop management for calendarbot_lite."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class FetchOrchestrator:
    """Orchestrates fetching from multiple sources with bounded concurrency."""

    def __init__(
        self,
        fetch_and_parse_source: Any,
        window_manager: Any,
        health_tracker: Any,
        monitoring_logger: Any,
    ):
        """Initialize fetch orchestrator.

        Args:
            fetch_and_parse_source: Function to fetch and parse a single source
            window_manager: EventWindowManager instance
            health_tracker: HealthTracker instance
            monitoring_logger: Function to log monitoring events
        """
        self.fetch_and_parse_source = fetch_and_parse_source
        self.window_manager = window_manager
        self.health_tracker = health_tracker
        self.log_monitoring_event = monitoring_logger

    async def fetch_all_sources(
        self,
        sources_cfg: list[Any],
        fetch_concurrency: int,
        rrule_days: int,
        shared_http_client: Any = None,
    ) -> list[dict[str, Any]]:
        """Fetch and parse all sources with bounded concurrency.

        Now uses AsyncOrchestrator for consistent async patterns and timeout management.

        Args:
            sources_cfg: List of source configurations
            fetch_concurrency: Maximum number of concurrent fetches
            rrule_days: Days to expand RRULE patterns
            shared_http_client: Optional shared HTTP client

        Returns:
            List of all parsed events from all sources
        """
        if not sources_cfg:
            logger.error("No sources configured, skipping fetch")
            return []

        # Import AsyncOrchestrator for centralized async patterns
        from .async_utils import get_global_orchestrator

        orchestrator = get_global_orchestrator()

        # Use bounded concurrency for fetching sources
        semaphore = asyncio.Semaphore(fetch_concurrency)
        fetch_tasks = [
            asyncio.create_task(
                self.fetch_and_parse_source(semaphore, src_cfg, rrule_days, shared_http_client)
            )
            for src_cfg in sources_cfg
        ]

        # Execute all fetch tasks concurrently with timeout management
        # Use 120s timeout for fetching all sources (reasonable for multiple ICS fetches)
        fetch_results = await orchestrator.gather_with_timeout(
            *fetch_tasks, timeout=120.0, return_exceptions=True
        )

        # Process results and collect parsed events
        parsed_events = []
        for i, result in enumerate(fetch_results):
            if isinstance(result, Exception):
                logger.error("Source %r failed: %s", sources_cfg[i], result)
                continue
            if isinstance(result, list):
                logger.debug("Source %r returned %d events", sources_cfg[i], len(result))
                parsed_events.extend(result)

        logger.debug("Total parsed events from all sources: %d", len(parsed_events))
        return parsed_events

    async def refresh_once(
        self,
        config: Any,
        skipped_store: object | None,
        event_window_ref: list[tuple[dict[str, Any], ...]],
        window_lock: Any,
        shared_http_client: Any,
        time_provider: Any,
        get_config_value: Any,
    ) -> None:
        """Perform a single refresh: fetch sources, parse/expand events and update window.

        Args:
            config: Application configuration
            skipped_store: Optional store for skipped events
            event_window_ref: Reference to event window for atomic updates
            window_lock: Lock for thread-safe event window updates
            shared_http_client: Optional shared HTTP client for connection reuse
            time_provider: Function to get current time
            get_config_value: Function to get config values
        """
        logger.debug("=== Starting refresh_once ===")

        # Track refresh attempt and log monitoring event
        self.health_tracker.record_refresh_attempt()
        self.health_tracker.record_background_heartbeat()

        sources_cfg = get_config_value(config, "ics_sources", []) or []

        self.log_monitoring_event(
            "refresh.cycle.start",
            "Starting refresh cycle",
            "DEBUG",
            details={"sources_count": len(sources_cfg)},
        )

        if not sources_cfg:
            logger.error("No sources configured, skipping refresh")
            self.log_monitoring_event(
                "refresh.config.error",
                "No ICS sources configured - refresh skipped",
                "ERROR",
                details={"config_keys": list(config.keys()) if isinstance(config, dict) else []},
            )
            return

        # Get configuration
        fetch_concurrency = int(get_config_value(config, "fetch_concurrency", 2))
        fetch_concurrency = max(1, min(fetch_concurrency, 3))  # Bound between 1-3
        rrule_days = int(get_config_value(config, "rrule_expansion_days", 14))
        window_size = int(get_config_value(config, "event_window_size", 50))

        logger.debug(
            "Refresh configuration: rrule_expansion_days=%d, sources_count=%d, fetch_concurrency=%d",
            rrule_days,
            len(sources_cfg),
            fetch_concurrency,
        )

        # Fetch all sources
        parsed_events = await self.fetch_all_sources(
            sources_cfg,
            fetch_concurrency,
            rrule_days,
            shared_http_client,
        )

        # Use event filter and window manager for smart filtering and fallback
        now = time_provider()

        # Update window with smart fallback logic
        updated, final_count, message = await self.window_manager.update_window(
            event_window_ref,
            window_lock,
            parsed_events,
            now,
            skipped_store,
            window_size,
            len(sources_cfg),
        )

        # Log appropriate monitoring events based on outcome
        if not updated:
            # Window was preserved due to fallback logic
            if final_count > 0:
                self.log_monitoring_event(
                    "refresh.sources.fallback",
                    message,
                    "WARNING",
                    details={"existing_events": final_count, "sources_count": len(sources_cfg)},
                    include_system_state=True,
                )
            else:
                self.log_monitoring_event(
                    "refresh.sources.critical_failure",
                    message,
                    "CRITICAL",
                    include_system_state=True,
                )
            return  # Exit early when using fallback

        # Track successful refresh
        self.health_tracker.record_refresh_success(final_count)

        logger.debug("Refresh complete; stored %d events in window", final_count)

        # Log structured monitoring event for refresh success
        self.log_monitoring_event(
            "refresh.cycle.complete",
            f"Refresh cycle completed successfully - {final_count} events in window",
            "INFO",
            details={
                "events_parsed": len(parsed_events),
                "events_in_window": final_count,
                "sources_processed": len(sources_cfg),
            },
            include_system_state=True,
        )

        # INFO level log to confirm server is operational
        if parsed_events:
            logger.info(
                "ICS data successfully parsed and refreshed - %d upcoming events available",
                final_count,
            )
        else:
            logger.info(
                "No events from sources - using fallback behavior (%d events in window)",
                final_count,
            )

        # Log event details for debugging (read window for logging)
        async with window_lock:
            window_for_logging = event_window_ref[0]

        for i, event in enumerate(window_for_logging[:3]):  # Log first 3 events
            logger.debug(
                "Event %d - ID: %r, Subject: %r, Start: %r",
                i,
                event.get("meeting_id"),
                event.get("subject"),
                event.get("start"),
            )

    async def start_refresh_loop(
        self,
        config: Any,
        skipped_store: object | None,
        event_window_ref: list[tuple[dict[str, Any], ...]],
        window_lock: Any,
        stop_event: Any,
        shared_http_client: Any,
        time_provider: Any,
        get_config_value: Any,
    ) -> None:
        """Background refresher: immediate refresh then periodic refreshes.

        Args:
            config: Application configuration
            skipped_store: Optional skipped events store
            event_window_ref: Reference to event window
            window_lock: Lock for thread-safe updates
            stop_event: Event to signal shutdown
            shared_http_client: Optional shared HTTP client
            time_provider: Function to get current time
            get_config_value: Function to get config values
        """
        interval = int(get_config_value(config, "refresh_interval_seconds", 60))
        logger.debug("Refresh loop starting with interval %d seconds", interval)

        # Perform an initial refresh immediately
        logger.debug("Starting initial refresh")
        try:
            await self.refresh_once(
                config,
                skipped_store,
                event_window_ref,
                window_lock,
                shared_http_client,
                time_provider,
                get_config_value,
            )
            logger.debug("Initial refresh completed")
        except Exception:
            logger.exception("Initial refresh failed")

        logger.debug("Starting refresh loop")
        while not stop_event.is_set():
            try:
                logger.debug("Sleeping for %d seconds until next refresh", interval)
                await asyncio.sleep(interval)
                if stop_event.is_set():
                    break
                logger.debug("Starting periodic refresh")
                await self.refresh_once(
                    config,
                    skipped_store,
                    event_window_ref,
                    window_lock,
                    shared_http_client,
                    time_provider,
                    get_config_value,
                )
                logger.debug("Periodic refresh completed")
            except Exception:
                logger.exception("Refresh loop unexpected error")
