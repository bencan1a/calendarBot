"""Dependency injection container for calendarbot_lite server."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AppDependencies:
    """Container for all application dependencies.

    This dataclass holds all the shared dependencies needed by various
    parts of the application, making it easier to test and maintain.
    """

    # Configuration
    config: Any

    # State management
    event_window_ref: list[tuple[dict[str, Any], ...]]
    window_lock: Any
    stop_event: Any
    skipped_store: object | None

    # Infrastructure
    shared_http_client: Any
    health_tracker: Any

    # Business logic components
    config_manager: Any
    event_filter: Any
    window_manager: Any
    fetch_orchestrator: Any

    # Utility functions
    time_provider: Any
    get_config_value: Any
    get_server_timezone: Any
    get_fallback_timezone: Any
    serialize_iso: Any
    event_to_api_model: Any
    is_focus_time_event: Any
    format_duration_spoken: Any
    get_system_diagnostics: Any
    log_monitoring_event: Any

    # SSML renderers (optional)
    ssml_renderers: dict[str, Any]


class DependencyContainer:
    """Factory for building application dependencies."""

    @staticmethod
    def build_dependencies(
        config: Any,
        skipped_store: object | None,
        shared_http_client: Any,
    ) -> AppDependencies:
        """Build all application dependencies.

        Args:
            config: Application configuration
            skipped_store: Optional skipped events store
            shared_http_client: Shared HTTP client session

        Returns:
            AppDependencies container with all dependencies initialized
        """
        import asyncio

        # Import required modules
        from calendarbot_lite.core.config_manager import get_config_value
        from calendarbot_lite.core.health_tracker import HealthTracker, get_system_diagnostics
        from calendarbot_lite.core.timezone_utils import (
            get_fallback_timezone,
            get_server_timezone,
            now_utc,
        )
        from calendarbot_lite.domain.event_filter import (
            EventFilter,
            EventWindowManager,
            SmartFallbackHandler,
        )
        from calendarbot_lite.domain.fetch_orchestrator import FetchOrchestrator

        # Initialize health tracker
        health_tracker = HealthTracker()

        # Create event window state
        event_window_ref: list[tuple[dict[str, Any], ...]] = [()]
        window_lock = asyncio.Lock()
        stop_event = asyncio.Event()

        # Initialize event filtering components
        fallback_handler = SmartFallbackHandler()
        event_filter = EventFilter(get_server_timezone, get_fallback_timezone)
        window_manager = EventWindowManager(event_filter, fallback_handler)

        # Import utility functions from server module
        # Note: These need to be imported dynamically to avoid circular imports
        from calendarbot_lite.api import server as server_module

        # Create fetch orchestrator
        fetch_orchestrator = FetchOrchestrator(
            fetch_and_parse_source=server_module._fetch_and_parse_source,  # noqa: SLF001
            window_manager=window_manager,
            health_tracker=health_tracker,
            monitoring_logger=server_module.log_monitoring_event,
        )

        # Load SSML renderers if available
        ssml_renderers = {}
        try:
            from calendarbot_lite.alexa.alexa_ssml import (
                render_done_for_day_ssml,
                render_meeting_ssml,
                render_time_until_ssml,
            )

            ssml_renderers = {
                "meeting": render_meeting_ssml,
                "time_until": render_time_until_ssml,
                "done_for_day": render_done_for_day_ssml,
            }
        except ImportError:
            pass

        # Build and return dependencies container
        return AppDependencies(
            config=config,
            event_window_ref=event_window_ref,
            window_lock=window_lock,
            stop_event=stop_event,
            skipped_store=skipped_store,
            shared_http_client=shared_http_client,
            health_tracker=health_tracker,
            config_manager=None,  # Can be added if needed
            event_filter=event_filter,
            window_manager=window_manager,
            fetch_orchestrator=fetch_orchestrator,
            time_provider=now_utc,
            get_config_value=get_config_value,
            get_server_timezone=get_server_timezone,
            get_fallback_timezone=get_fallback_timezone,
            serialize_iso=server_module._serialize_iso,  # noqa: SLF001
            event_to_api_model=server_module._event_to_api_model,  # noqa: SLF001
            is_focus_time_event=server_module._is_focus_time_event,  # noqa: SLF001
            format_duration_spoken=server_module._format_duration_spoken,  # noqa: SLF001
            get_system_diagnostics=get_system_diagnostics,
            log_monitoring_event=server_module.log_monitoring_event,
            ssml_renderers=ssml_renderers,
        )
