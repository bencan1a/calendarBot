"""Web server mode handler for Calendar Bot CLI.

This module provides the web server mode functionality for Calendar Bot,
including web interface setup, server management, and browser integration.
"""

import asyncio
import logging
import signal
import webbrowser
from typing import Any, Optional

from calendarbot.config.settings import settings
from calendarbot.layout.registry import LayoutRegistry
from calendarbot.main import CalendarBot
from calendarbot.utils.logging import apply_command_line_overrides, setup_enhanced_logging
from calendarbot.utils.network import get_local_network_interface, validate_host_binding
from calendarbot.web.navigation import WebNavigationHandler
from calendarbot.web.server import WebServer

from ..config import apply_cli_overrides
from ..runtime_integration import (
    create_runtime_tracker,
    start_runtime_tracking,
    stop_runtime_tracking,
)


def _configure_web_settings(args: Any, base_settings: Any) -> Any:
    """Configure web mode settings from command line arguments.

    Args:
        args: Parsed command line arguments
        base_settings: Base settings object to configure

    Returns:
        Updated settings object with web mode configuration
    """
    # Apply command-line logging overrides with priority system
    updated_settings = apply_command_line_overrides(base_settings, args)

    # Apply CLI-specific overrides
    updated_settings = apply_cli_overrides(updated_settings, args)

    # Apply web mode overrides - ensure HTML renderer and appropriate layout for web mode
    if not hasattr(args, "rpi") or not args.rpi:
        # Check if layout was explicitly set to whats-next-view
        layout_from_args = getattr(args, "layout", None) or getattr(args, "display_type", None)
        if layout_from_args == "whats-next-view":
            # Use WhatsNextRenderer for whats-next-view layout
            updated_settings.display_type = "whats-next"
            updated_settings.web_layout = "whats-next-view"
        else:
            # Use HTML renderer for proper layout structure in web mode
            updated_settings.display_type = "html"
            # Use centralized default layout from LayoutRegistry
            layout_registry = LayoutRegistry()
            updated_settings.web_layout = layout_registry.get_default_layout()

    # Configure host settings
    if args.host is None:
        # Use detected network interface for binding
        detected_host = get_local_network_interface()
        updated_settings.web_host = detected_host

        # Validate the binding choice and show appropriate warnings
        validate_host_binding(updated_settings.web_host, warn_on_all_interfaces=False)
    else:
        updated_settings.web_host = args.host

    updated_settings.web_port = args.port

    return updated_settings


async def _initialize_web_components(updated_settings: Any) -> tuple[CalendarBot, WebServer, WebNavigationHandler, Any]:
    """Initialize Calendar Bot and web server components.

    Args:
        updated_settings: Configured settings object

    Returns:
        Tuple of (app, web_server, navigation_handler, logger)

    Raises:
        Exception: If component initialization fails
    """
    # Set up enhanced logging for web mode
    logger = setup_enhanced_logging(updated_settings, interactive_mode=False)
    logger.info("Starting Calendar Bot web mode initialization...")

    # Create Calendar Bot instance
    app = CalendarBot()
    logger.debug("Created CalendarBot instance")

    # Initialize components
    logger.info("Initializing Calendar Bot components...")
    if not await app.initialize():
        logger.error("Failed to initialize Calendar Bot")
        raise RuntimeError("Failed to initialize Calendar Bot")
    logger.info("Calendar Bot components initialized successfully")

    # Create web navigation handler
    logger.debug("Creating web navigation handler...")
    navigation_handler = WebNavigationHandler()
    logger.debug("Web navigation handler created successfully")

    # Create web server with navigation state enabled
    logger.debug("Creating WebServer with navigation state enabled...")
    try:
        web_server = WebServer(
            settings=updated_settings,
            display_manager=app.display_manager,
            cache_manager=app.cache_manager,
            navigation_state=navigation_handler.navigation_state,  # Navigation enabled
        )
        logger.debug("WebServer created successfully with navigation enabled")
    except Exception:
        logger.exception("Failed to create WebServer")
        logger.debug(
            f"WebServer parameters attempted: settings={updated_settings}, display_manager={app.display_manager}, cache_manager={app.cache_manager}, navigation_state={navigation_handler.navigation_state}"
        )
        raise

    return app, web_server, navigation_handler, logger


def _start_web_server(web_server: WebServer, updated_settings: Any, args: Any, logger: logging.Logger) -> None:
    """Start the web server and optionally open browser.

    Args:
        web_server: WebServer instance to start
        updated_settings: Configured settings object
        args: Command line arguments
        logger: Logger instance for output
    """
    print(
        f"Starting Calendar Bot web server on http://{updated_settings.web_host}:{updated_settings.web_port}"
    )
    print("Press Ctrl+C to stop the server")
    logger.debug(
        f"Web server configured for http://{updated_settings.web_host}:{updated_settings.web_port}"
    )

    # Optionally open browser
    if args.auto_open:
        url = f"http://{updated_settings.web_host}:{updated_settings.web_port}"
        print(f"Opening browser to {url}")
        logger.info(f"Auto-opening browser to {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            logger.warning(f"Failed to auto-open browser: {e}")

    # Start web server (NOT async - fixed sync/async mismatch)
    logger.debug("Starting web server...")
    web_server.start()
    logger.debug("Web server started successfully")

    # Keep the server running
    print("Web server is running. Press Ctrl+C to stop.")
    logger.debug("Entering main server loop with graceful shutdown")


async def _cleanup_web_resources(
    runtime_tracker: Optional[Any],
    web_server: WebServer,
    fetch_task: asyncio.Task,
    app: CalendarBot,
    logger: logging.Logger
) -> None:
    """Clean up web server resources.

    Args:
        runtime_tracker: Runtime tracker instance (optional)
        web_server: WebServer instance to stop
        fetch_task: Background fetch task to cancel
        app: CalendarBot instance to cleanup
        logger: Logger instance for output
    """
    logger.debug("Entering cleanup phase...")

    # Stop runtime tracking
    if runtime_tracker:
        stop_runtime_tracking(runtime_tracker, "web_mode")

    # Stop web server
    try:
        logger.debug("Stopping web server...")
        web_server.stop()
        logger.info("Web server stopped successfully")
    except Exception:
        logger.exception("Error stopping web server")

    # Stop background fetching
    logger.debug("Cancelling background fetch task...")
    fetch_task.cancel()

    logger.debug("Waiting for background fetch task to complete...")
    try:
        await asyncio.wait_for(fetch_task, timeout=10.0)
        logger.debug("Background fetch task completed normally")
    except asyncio.CancelledError:
        logger.debug("Background fetch task cancelled successfully")
    except asyncio.TimeoutError:
        logger.warning(
            "Background fetch task did not cancel within 10 seconds - this may indicate a hanging task"
        )
    except Exception:
        logger.exception("Unexpected error during background fetch task cancellation")

    # Cleanup
    try:
        logger.debug("Running application cleanup...")
        await asyncio.wait_for(app.cleanup(), timeout=10.0)
        logger.info("Application cleanup completed")
    except asyncio.TimeoutError:
        logger.warning("Application cleanup timed out after 10 seconds")
    except Exception:
        logger.exception("Error during application cleanup")
        import traceback  # noqa: PLC0415

        logger.exception(f"Cleanup traceback: {traceback.format_exc()}")


async def run_web_mode(args: Any) -> int:
    """Run Calendar Bot in web server mode.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    shutdown_event = asyncio.Event()

    def signal_handler(signum: int, _frame: Any) -> None:
        """Handle shutdown signals gracefully."""
        print(f"\nReceived signal {signum}, initiating graceful shutdown...")
        shutdown_event.set()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Configure web mode settings
        updated_settings = _configure_web_settings(args, settings)

        # Initialize components
        app, web_server, navigation_handler, logger = await _initialize_web_components(updated_settings)

        # Create runtime tracker if enabled
        runtime_tracker = create_runtime_tracker(updated_settings)

        # Start runtime tracking for web mode
        session_name = (
            getattr(updated_settings.runtime_tracking, "session_name", None)
            if hasattr(updated_settings, "runtime_tracking")
            else None
        )
        start_runtime_tracking(runtime_tracker, "web_mode", session_name)

        # Start background data fetching
        logger.debug("Starting background data fetching task...")
        fetch_task = asyncio.create_task(app.run_background_fetch())
        logger.debug("Background data fetching task started")

        try:
            # Start web server
            _start_web_server(web_server, updated_settings, args, logger)

            # Wait for shutdown signal using polling to keep event loop responsive
            logger.debug("Web server started, waiting for shutdown signal...")

            # Poll the shutdown event instead of blocking on await
            while not shutdown_event.is_set():
                await asyncio.sleep(0.1)  # Check every 100ms

            logger.info("Shutdown signal received, beginning graceful shutdown...")

        finally:
            # Clean up resources
            await _cleanup_web_resources(runtime_tracker, web_server, fetch_task, app, logger)

        logger.info("Web mode completed successfully")
        return 0

    except Exception as e:
        # Use print instead of logger since logger might not be initialized yet
        print(f"Web server error: {e}")
        import traceback  # noqa: PLC0415

        traceback.print_exc()
        return 1


__all__ = ["run_web_mode"]
