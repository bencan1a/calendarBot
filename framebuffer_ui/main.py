"""Main entry point for CalendarBot framebuffer UI.

This module coordinates the API client, layout engine, and renderer
in an async event loop to provide a lightweight calendar display.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from typing import Any

import pygame

from framebuffer_ui.api_client import CalendarAPIClient
from framebuffer_ui.config import Config
from framebuffer_ui.layout_engine import LayoutEngine
from framebuffer_ui.renderer import FramebufferRenderer

logger = logging.getLogger(__name__)


class CalendarKioskApp:
    """Main application coordinator.

    Coordinates the API client, layout engine, and renderer in an
    async event loop. Handles graceful shutdown and error recovery.
    """

    def __init__(self, config: Config):
        """Initialize the application.

        Args:
            config: Configuration instance
        """
        self.config = config
        self.running = False

        # Initialize components
        self.api_client = CalendarAPIClient(config)
        self.layout_engine = LayoutEngine()
        self.renderer = FramebufferRenderer(config)

        logger.info("CalendarBot Framebuffer UI initialized")
        logger.info("Backend URL: %s", config.backend_url)
        logger.info("Refresh interval: %ds", config.refresh_interval)

    async def run(self) -> None:
        """Main event loop.

        Polls the API at regular intervals, processes the data through
        the layout engine, and renders to the display.
        """
        self.running = True

        logger.info("Starting main event loop")

        # Initial render (with loading message)
        await self._render_loading_screen()

        while self.running:
            try:
                # Fetch data from API
                data = await self.api_client.fetch_whats_next()

                # Process through layout engine
                layout = self.layout_engine.process(data)

                # Render to display
                self.renderer.render(layout)

                logger.debug("Display updated successfully")

            except Exception as error:
                # Render error screen
                logger.error("Error in main loop: %s", error)
                await self._render_error_screen(str(error))

            # Handle pygame events (for clean exit)
            pygame.event.pump()  # Force event queue update
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    logger.info("Received QUIT event")
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                        logger.info("Received quit key")
                        self.running = False

            # Wait before next update (interruptible sleep for responsive shutdown)
            if self.running:
                # Sleep in 0.5-second increments to allow quick shutdown response
                sleep_remaining = self.config.refresh_interval
                while sleep_remaining > 0 and self.running:
                    sleep_chunk = min(0.5, sleep_remaining)
                    await asyncio.sleep(sleep_chunk)
                    sleep_remaining -= sleep_chunk

        logger.info("Main event loop stopped")

    async def _render_loading_screen(self) -> None:
        """Render loading screen during initial startup."""
        try:
            # Create a simple loading layout
            from framebuffer_ui.layout_engine import (
                CountdownDisplay,
                LayoutData,
                MeetingDisplay,
                StatusDisplay,
            )

            loading_layout = LayoutData(
                countdown=CountdownDisplay(
                    label="LOADING",
                    value=0,
                    primary_unit="...",
                    secondary="",
                    state="normal",
                ),
                meeting=MeetingDisplay(
                    title="CalendarBot Framebuffer UI",
                    time="Connecting to backend...",
                    location="",
                ),
                status=StatusDisplay(
                    message="Initializing display",
                    is_urgent=False,
                    is_critical=False,
                ),
                has_data=False,
            )

            self.renderer.render(loading_layout)
            logger.debug("Loading screen rendered")

        except Exception as error:
            logger.error("Failed to render loading screen: %s", error)

    async def _render_error_screen(self, error_message: str) -> None:
        """Render error screen.

        Args:
            error_message: Error message to display
        """
        try:
            from framebuffer_ui.layout_engine import (
                CountdownDisplay,
                LayoutData,
                MeetingDisplay,
                StatusDisplay,
            )

            error_layout = LayoutData(
                countdown=CountdownDisplay(
                    label="ERROR",
                    value=0,
                    primary_unit="",
                    secondary="",
                    state="critical",
                ),
                meeting=MeetingDisplay(
                    title="Connection Error",
                    time="Unable to connect to backend",
                    location="",
                ),
                status=StatusDisplay(
                    message=f"Error: {error_message[:40]}...",
                    is_urgent=True,
                    is_critical=True,
                ),
                has_data=False,
            )

            self.renderer.render(error_layout)
            logger.debug("Error screen rendered")

        except Exception as render_error:
            logger.error("Failed to render error screen: %s", render_error)

    async def shutdown(self) -> None:
        """Graceful shutdown.

        Stops the main loop and closes resources.
        Note: Renderer cleanup (pygame.quit) must happen AFTER the main loop
        exits, since the loop uses pygame event handling.

        Cleanup order:
        1. Stop main loop (set running = False)
        2. Close API client
        3. Renderer cleanup is done externally after run() completes
        """
        logger.info("Shutting down...")

        self.running = False

        # Close API client
        await self.api_client.close()

        logger.info("Shutdown complete")


def setup_logging(config: Config) -> None:
    """Set up logging configuration.

    Args:
        config: Configuration instance
    """
    log_level = getattr(logging, config.log_level, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger.info("Logging configured: level=%s", config.log_level)


async def main() -> None:
    """Main entry point."""
    # Load configuration
    config = Config.from_env()

    # Set up logging
    setup_logging(config)

    # Create application
    app = CalendarKioskApp(config)

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler(sig: Any) -> None:
        logger.info("Received signal: %s", sig)
        app.running = False  # Immediately stop the loop

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    try:
        # Run the application
        await app.run()

    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt")

    finally:
        # Ensure clean shutdown
        await app.shutdown()

        # Clean up pygame (must be done AFTER run() exits)
        app.renderer.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        logger.exception("Fatal error: %s", error)
        sys.exit(1)
