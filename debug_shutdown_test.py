#!/usr/bin/env python3
"""Test script to debug web server shutdown issues."""

import asyncio
import logging
import signal
import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


async def test_shutdown():
    """Test the shutdown process with detailed logging."""
    logger.info("Starting shutdown test...")

    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Signal {signum} received, setting shutdown event...")
        shutdown_event.set()
        logger.info(f"Shutdown event set for signal {signum}")

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        from calendarbot.main import CalendarBot
        from calendarbot.web.navigation import WebNavigationHandler
        from calendarbot.web.server import WebServer
        from config.settings import settings

        logger.info("Creating CalendarBot instance...")
        app = CalendarBot()

        logger.info("Initializing CalendarBot...")
        if not await app.initialize():
            logger.error("Failed to initialize Calendar Bot")
            return 1
        logger.info("CalendarBot initialized successfully")

        # Create web navigation handler
        logger.info("Creating web navigation handler...")
        navigation_handler = WebNavigationHandler()

        # Create web server
        logger.info("Creating WebServer...")
        web_server = WebServer(
            settings=settings,
            display_manager=app.display_manager,
            cache_manager=app.cache_manager,
            navigation_state=navigation_handler.navigation_state,
        )
        logger.info("WebServer created successfully")

        # Start background data fetching
        logger.info("Starting background data fetching task...")
        fetch_task = asyncio.create_task(app.run_background_fetch())
        logger.info("Background fetch task started")

        try:
            logger.info("Starting web server...")
            web_server.start()
            logger.info("Web server started - waiting for shutdown signal...")

            print("Web server is running. Press Ctrl+C to test shutdown...")

            # Wait for shutdown signal with timeout for testing
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=60)
                logger.info("Shutdown signal received!")
            except asyncio.TimeoutError:
                logger.info("Timeout reached - initiating shutdown anyway for testing")
                shutdown_event.set()

        finally:
            logger.info("=== STARTING SHUTDOWN SEQUENCE ===")
            start_time = time.time()

            # Stop web server
            logger.info("Step 1: Stopping web server...")
            try:
                web_server.stop()
                logger.info("Web server stop completed")
            except Exception as e:
                logger.error(f"Error stopping web server: {e}")

            # Stop background fetching
            logger.info("Step 2: Cancelling background fetch task...")
            fetch_task.cancel()

            try:
                await asyncio.wait_for(fetch_task, timeout=10.0)
                logger.info("Background fetch task completed")
            except asyncio.CancelledError:
                logger.info("Background fetch task cancelled successfully")
            except asyncio.TimeoutError:
                logger.warning("Background fetch task timeout!")
            except Exception as e:
                logger.error(f"Error with background fetch task: {e}")

            # Cleanup
            logger.info("Step 3: Running application cleanup...")
            try:
                await asyncio.wait_for(app.cleanup(), timeout=10.0)
                logger.info("Application cleanup completed")
            except asyncio.TimeoutError:
                logger.warning("Application cleanup timeout!")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

            end_time = time.time()
            shutdown_duration = end_time - start_time
            logger.info(f"=== SHUTDOWN COMPLETED IN {shutdown_duration:.2f} SECONDS ===")

        return 0

    except Exception as e:
        logger.error(f"Test error: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1


def main():
    """Run the shutdown test."""
    try:
        exit_code = asyncio.run(test_shutdown())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
