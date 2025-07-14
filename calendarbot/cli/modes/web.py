"""Web server mode handler for Calendar Bot CLI.

This module provides the web server mode functionality for Calendar Bot,
including web interface setup, server management, and browser integration.
This functionality will be migrated from root main.py during Phase 2.
"""

import asyncio
import logging
import signal
from typing import Any, Optional


async def run_web_mode(args: Any) -> int:
    """Run Calendar Bot in web server mode.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    shutdown_event = asyncio.Event()

    def signal_handler(signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully."""
        print(f"\nReceived signal {signum}, initiating graceful shutdown...")
        shutdown_event.set()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        import webbrowser

        from calendarbot.config.settings import settings
        from calendarbot.main import CalendarBot
        from calendarbot.utils.logging import apply_command_line_overrides, setup_enhanced_logging
        from calendarbot.web.navigation import WebNavigationHandler
        from calendarbot.web.server import WebServer

        from ..config import apply_rpi_overrides

        # Apply command-line logging overrides with priority system
        updated_settings = apply_command_line_overrides(settings, args)

        # Apply RPI-specific overrides
        updated_settings = apply_rpi_overrides(updated_settings, args)

        # Apply web mode overrides - ensure HTML renderer and 4x8 layout for web mode
        if not hasattr(args, "rpi") or not args.rpi:
            # Use HTML renderer for proper layout structure in web mode
            updated_settings.display_type = "html"
            updated_settings.web_layout = "4x8"  # Default to 4x8 layout for web mode

        # Set up enhanced logging for web mode
        logger = setup_enhanced_logging(updated_settings, interactive_mode=False)
        # Enhanced logging initialized - removed verbose message

        logger.info("Starting Calendar Bot web mode initialization...")

        # Create Calendar Bot instance
        app = CalendarBot()
        logger.debug("Created CalendarBot instance")

        # Initialize components
        logger.info("Initializing Calendar Bot components...")
        if not await app.initialize():
            logger.error("Failed to initialize Calendar Bot")
            print("Failed to initialize Calendar Bot")
            return 1
        logger.info("Calendar Bot components initialized successfully")

        # Override web settings from command line
        logger.debug(
            f"Original settings - host: {updated_settings.web_host}, port: {updated_settings.web_port}"
        )

        # Use auto-detected host if not specified
        if args.host is None:
            from calendarbot.utils.network import get_local_network_interface

            updated_settings.web_host = get_local_network_interface()
        else:
            updated_settings.web_host = args.host

        updated_settings.web_port = args.port
        logger.debug(
            f"Updated web settings - host: {updated_settings.web_host}, port: {updated_settings.web_port}"
        )

        # Settings validation completed

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
        except Exception as e:
            logger.error(f"Failed to create WebServer: {e}")
            logger.debug(
                f"WebServer parameters attempted: settings={settings}, display_manager={app.display_manager}, cache_manager={app.cache_manager}, navigation_state={navigation_handler.navigation_state}"
            )
            raise

        # Start background data fetching
        logger.debug("Starting background data fetching task...")
        fetch_task = asyncio.create_task(app.run_background_fetch())
        logger.debug("Background data fetching task started")

        try:
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

            # Wait for shutdown signal using polling to keep event loop responsive
            logger.debug("Web server started, waiting for shutdown signal...")

            # Poll the shutdown event instead of blocking on await
            while not shutdown_event.is_set():
                await asyncio.sleep(0.1)  # Check every 100ms

            logger.info("Shutdown signal received, beginning graceful shutdown...")

        finally:
            logger.debug("Entering cleanup phase...")

            # Stop web server
            try:
                logger.debug("Stopping web server...")
                web_server.stop()
                logger.info("Web server stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping web server: {e}")

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
            except Exception as e:
                logger.error(f"Unexpected error during background fetch task cancellation: {e}")

            # Cleanup
            try:
                logger.debug("Running application cleanup...")
                await asyncio.wait_for(app.cleanup(), timeout=10.0)
                logger.info("Application cleanup completed")
            except asyncio.TimeoutError:
                logger.warning("Application cleanup timed out after 10 seconds")
            except Exception as e:
                logger.error(f"Error during application cleanup: {e}")
                import traceback

                logger.error(f"Cleanup traceback: {traceback.format_exc()}")

        logger.info("Web mode completed successfully")
        return 0

    except Exception as e:
        # Use print instead of logger since logger might not be initialized yet
        print(f"Web server error: {e}")
        import traceback

        traceback.print_exc()
        return 1


def setup_web_server(
    settings: Any, display_manager: Any, cache_manager: Any, navigation_state: Any
) -> Optional[Any]:
    """Setup web server with navigation state.

    This function will be migrated from root main.py in Phase 2 to handle
    web server creation and configuration.

    Args:
        settings: Application settings object
        display_manager: Display manager instance
        cache_manager: Cache manager instance
        navigation_state: Navigation state handler

    Returns:
        Configured web server instance
    """
    # Placeholder implementation - will be migrated in Phase 2
    print("Web server setup placeholder - will be migrated from root main.py")
    return None


def apply_web_mode_overrides(settings: Any, args: Any) -> Any:
    """Apply web mode specific setting overrides.

    This function will be migrated from root main.py in Phase 2 to handle
    web mode specific configuration like layout and display type.

    Args:
        settings: Application settings object
        args: Parsed command line arguments

    Returns:
        Updated settings object
    """
    # Placeholder implementation - will be migrated in Phase 2
    print("Web mode overrides placeholder - will be migrated from root main.py")
    return settings


def setup_web_navigation() -> Optional[Any]:
    """Setup web navigation handler.

    This function will be migrated from root main.py in Phase 2 to handle
    web navigation state management.

    Returns:
        Web navigation handler instance
    """
    # Placeholder implementation - will be migrated in Phase 2
    print("Web navigation setup placeholder - will be migrated from root main.py")
    return None


__all__ = [
    "run_web_mode",
    "setup_web_server",
    "apply_web_mode_overrides",
    "setup_web_navigation",
]
