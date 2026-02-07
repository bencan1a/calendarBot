"""Main entry point for CalendarBot framebuffer UI.

This module coordinates the API client, layout engine, and renderer
in an async event loop to provide a lightweight calendar display.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
import sys
import time
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

        # Shared state for dual-loop pattern
        self.cached_api_data: dict[str, Any] | None = None
        self.last_fetch_time: float | None = None
        self.data_lock = asyncio.Lock()

        # Initialize components
        self.api_client = CalendarAPIClient(config)
        self.layout_engine = LayoutEngine()
        self.renderer = FramebufferRenderer(config)

        logger.info("CalendarBot Framebuffer UI initialized")
        logger.info("Backend URL: %s", config.backend_url)
        logger.info("Data refresh interval: %ds", config.refresh_interval)
        logger.info("Display refresh interval: %ds", config.display_refresh_interval)

    async def run(self) -> None:
        """Main event loop with dual-loop architecture.

        Runs two concurrent tasks:
        - Data refresh task: Fetches API data every 60s
        - Display refresh task: Renders display every 5s using cached data
        """
        self.running = True
        logger.info("Starting main event loop (dual-loop mode)")

        # Initial render (loading screen)
        await self._render_loading_screen()

        # Create concurrent tasks
        data_task = asyncio.create_task(self._data_refresh_loop())
        display_task = asyncio.create_task(self._display_refresh_loop())

        try:
            # Wait for both tasks to complete (or shutdown signal)
            await asyncio.gather(data_task, display_task)
        except Exception:
            logger.exception("Error in main event loop")
        finally:
            # Cancel tasks if still running
            for task in [data_task, display_task]:
                if not task.done():
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task

        logger.info("Main event loop stopped")

    async def _data_refresh_loop(self) -> None:
        """Data refresh task - fetches API data every 60s.

        Updates shared cache with fresh data from backend.
        Uses existing error handling from APIClient (15min threshold).
        """
        while self.running:
            try:
                # Fetch fresh data from API
                data = await self.api_client.fetch_whats_next()

                # Update shared cache
                async with self.data_lock:
                    self.cached_api_data = data
                    self.last_fetch_time = time.time()

                logger.debug("Data refresh successful")

            except Exception:
                logger.exception("Error in data refresh loop")
                # Continue running - APIClient handles error display logic

            # Sleep with interruptible chunks (for responsive shutdown)
            await self._interruptible_sleep(self.config.refresh_interval)

    async def _display_refresh_loop(self) -> None:
        """Display refresh task - renders display every 5s.

        Uses cached API data with local countdown adjustment based on elapsed time.
        Handles pygame events and shutdown signals.
        """
        # Wait for initial data fetch
        while self.running and self.cached_api_data is None:
            await asyncio.sleep(0.1)

        while self.running:
            try:
                # Check data availability (quick check with lock)
                async with self.data_lock:
                    has_data = self.cached_api_data is not None

                # Sleep outside lock if no data
                if not has_data:
                    await asyncio.sleep(0.5)
                    continue

                # Get data with lock
                async with self.data_lock:
                    if self.cached_api_data is None:
                        # Data became None between checks (rare race condition)
                        continue

                    # Create adjusted data copy
                    adjusted_data = self._adjust_countdown_data(
                        self.cached_api_data,
                        self.last_fetch_time,
                    )

                # Process through layout engine
                layout = self.layout_engine.process(adjusted_data)

                # Render to display
                self.renderer.render(layout)

                logger.debug("Display updated (from cache)")

            except Exception as error:
                logger.exception("Error in display loop")
                await self._render_error_screen(str(error))

            # Handle pygame events (for clean exit)
            pygame.event.pump()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    logger.info("Received QUIT event")
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        logger.info("Received quit key")
                        self.running = False

            # Sleep before next display refresh (5s, interruptible)
            await self._interruptible_sleep(self.config.display_refresh_interval)

    def _adjust_countdown_data(
        self,
        cached_data: dict[str, Any],
        fetch_time: float | None,
    ) -> dict[str, Any]:
        """Adjust seconds_until_start based on elapsed time since fetch.

        Args:
            cached_data: Original API response
            fetch_time: Timestamp of when data was fetched

        Returns:
            Copy of data with adjusted seconds_until_start
        """
        if fetch_time is None or "meeting" not in cached_data:
            return cached_data

        # Calculate elapsed time since fetch
        elapsed_seconds = int(time.time() - fetch_time)

        # Create deep copy to avoid mutating cache
        adjusted_data = {**cached_data}

        if adjusted_data.get("meeting"):
            meeting_copy = {**adjusted_data["meeting"]}
            original_seconds = meeting_copy.get("seconds_until_start", 0)

            # Adjust countdown by subtracting elapsed time
            adjusted_seconds = max(0, original_seconds - elapsed_seconds)
            meeting_copy["seconds_until_start"] = adjusted_seconds

            adjusted_data["meeting"] = meeting_copy

        return adjusted_data

    async def _interruptible_sleep(self, duration: float) -> None:
        """Sleep in 0.5s chunks to allow responsive shutdown.

        Args:
            duration: Total sleep duration in seconds
        """
        remaining = duration
        while remaining > 0 and self.running:
            chunk = min(0.5, remaining)
            await asyncio.sleep(chunk)
            remaining -= chunk

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

        except Exception:
            logger.exception("Failed to render loading screen")

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

        except Exception:
            logger.exception("Failed to render error screen")

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
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))  # type: ignore[misc]

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
    except Exception:
        logger.exception("Fatal error")
        sys.exit(1)
