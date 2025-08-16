"""Main application entry point for the Calendar Bot."""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Any, Optional

from calendarbot.config.settings import settings

from .cache import CacheManager
from .display import DisplayManager
from .sources import SourceManager
from .utils import retry_with_backoff, safe_async_call, setup_logging
from .utils.process import kill_calendarbot_processes

# Set up logging
logger = setup_logging(
    log_level=str(settings.log_level),
    log_file=settings.log_file,
    log_dir=settings.config_dir if settings.log_file else None,
)


class CalendarBot:
    """Main Calendar Bot application coordinating all components."""

    def __init__(self) -> None:
        """Initialize Calendar Bot application."""
        self.settings = settings
        self.running = False
        self.shutdown_event = asyncio.Event()

        # Initialize component references (lazy initialization)
        self.cache_manager: Optional[CacheManager] = None
        self.source_manager: Optional[SourceManager] = None
        self.display_manager: Optional[DisplayManager] = None

        # Track last successful update
        self.last_successful_update: Optional[datetime] = None
        self.consecutive_failures = 0

        logger.info("Calendar Bot initialized (lazy components)")

    async def initialize(self) -> bool:
        """Initialize all components and ensure readiness with parallel async loading.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing Calendar Bot components in parallel...")

            # Create components (fast, no I/O)
            self.cache_manager = CacheManager(self.settings)
            self.source_manager = SourceManager(self.settings, self.cache_manager)
            self.display_manager = DisplayManager(self.settings)

            # Initialize components in parallel (async I/O operations)
            cache_task = asyncio.create_task(self.cache_manager.initialize())
            source_task = asyncio.create_task(self.source_manager.initialize())
            # Display manager doesn't have async initialization, so we skip it

            # Wait for both to complete
            cache_result, source_result = await asyncio.gather(
                cache_task, source_task, return_exceptions=True
            )

            # Check results
            if isinstance(cache_result, Exception):
                logger.error(f"Failed to initialize cache manager: {cache_result}")
                return False
            if not cache_result:
                logger.error("Cache manager initialization returned False")
                return False

            if isinstance(source_result, Exception):
                logger.error(f"Failed to initialize source manager: {source_result}")
                return False
            if not source_result:
                logger.error("Source manager initialization returned False")
                return False

            logger.info("Calendar Bot initialization completed successfully")
            return True

        except Exception:
            logger.exception("Failed to initialize Calendar Bot")
            return False

    def _ensure_components_initialized(self) -> bool:
        """Ensure all components are initialized.

        Returns:
            True if components are available, False otherwise
        """
        if (
            self.cache_manager is None
            or self.source_manager is None
            or self.display_manager is None
        ):
            logger.error("Components not initialized. Call initialize() first.")
            return False
        return True

    async def fetch_and_cache_events(self) -> bool:
        """Fetch events from ICS calendar feeds and cache them.

        Returns:
            True if fetch was successful, False otherwise
        """
        try:
            if not self._ensure_components_initialized():
                return False

            assert self.source_manager is not None

            logger.info("Fetching calendar events...")

            # Test source health first
            health_check = await self.source_manager.health_check()
            if not health_check.is_healthy:
                logger.warning(f"Source health check failed: {health_check.status_message}")
                return False

            # Fetch events from all sources and cache them
            if await self.source_manager.fetch_and_cache_events():
                self.last_successful_update = datetime.now()
                self.consecutive_failures = 0
                logger.info("Successfully fetched and cached events from all sources")
                return True
            logger.error("Failed to fetch and cache events")
            return False

        except Exception:
            logger.exception("Failed to fetch and cache events")
            self.consecutive_failures += 1
            return False

    async def update_display(self, force_cached: bool = False) -> bool:
        """Update the display with current calendar events.

        Args:
            force_cached: Force using cached data even if fresh data available

        Returns:
            True if display update successful, False otherwise
        """
        try:
            if not self._ensure_components_initialized():
                return False

            # Type assertions for components after guard check
            assert self.cache_manager is not None
            assert self.source_manager is not None
            assert self.display_manager is not None

            # Get cached events for today
            cached_events = await self.cache_manager.get_todays_cached_events()

            # Prepare status information
            cache_status = await self.cache_manager.get_cache_status()
            source_info = await self.source_manager.get_source_info()
            status_info = {
                "last_update": cache_status.last_update,
                "is_cached": force_cached or cache_status.is_stale,
                "connection_status": (
                    "Online" if not force_cached and not cache_status.is_stale else "Offline"
                ),
                "total_events": len(cached_events),
                "consecutive_failures": self.consecutive_failures,
                "source_status": source_info.status,
                "source_url": source_info.url,
            }

            # Update display
            success = await self.display_manager.display_events(cached_events, status_info)

            if not success:
                logger.warning("Display update failed")

            return success

        except Exception:
            logger.exception("Failed to update display")
            return False

    async def handle_error_display(self, error_message: str) -> None:
        """Display error message with cached events if available.

        Args:
            error_message: Error message to display
        """
        try:
            if not self._ensure_components_initialized():
                logger.error(f"Cannot display error: {error_message}")
                return

            assert self.cache_manager is not None
            assert self.display_manager is not None

            # Try to get cached events to show alongside error
            cached_events: list[Any] = (
                await safe_async_call(
                    self.cache_manager.get_todays_cached_events, default=[], log_errors=False
                )
                or []
            )

            await self.display_manager.display_error(error_message, cached_events)

        except Exception:
            logger.exception("Failed to display error")

    async def refresh_cycle(self) -> None:
        """Perform one refresh cycle - fetch data and update display."""
        try:
            if not self._ensure_components_initialized():
                return

            assert self.cache_manager is not None

            # Check if cache is fresh
            is_cache_fresh = await self.cache_manager.is_cache_fresh()

            if not is_cache_fresh:
                logger.info("Cache is stale, fetching fresh data")

                # Try to fetch fresh data
                fetch_success = await retry_with_backoff(
                    self.fetch_and_cache_events,
                    max_retries=2,
                    backoff_factor=2.0,
                    initial_delay=1.0,
                    exceptions=(Exception,),
                )

                if not fetch_success:
                    logger.warning("Failed to fetch fresh data, using cached data")
                    await self.handle_error_display("Network Issue - Using Cached Data")
                    return

            # Update display with current data
            await self.update_display(force_cached=not is_cache_fresh)

        except Exception as e:
            logger.exception("Error during refresh cycle")
            await self.handle_error_display(f"System Error: {str(e)[:50]}...")

    async def run_background_fetch(self) -> None:
        """Run background data fetching without display updates."""
        logger.info(
            f"Starting background data fetching (interval: {self.settings.refresh_interval}s)"
        )

        try:
            # Initial fetch
            await self.fetch_and_cache_events()

            while self.running and not self.shutdown_event.is_set():
                try:
                    # Wait for next refresh interval or shutdown signal
                    await asyncio.wait_for(
                        self.shutdown_event.wait(), timeout=self.settings.refresh_interval
                    )

                    # If we get here, shutdown was signaled
                    break

                except TimeoutError:
                    # Timeout means it's time for next fetch
                    if self.running:
                        await self.fetch_and_cache_events()

        except Exception:
            logger.exception("Background fetch error")

        logger.info("Background data fetching stopped")

    async def run_scheduler(self) -> None:
        """Run the main refresh scheduler."""
        logger.info(f"Starting refresh scheduler (interval: {self.settings.refresh_interval}s)")

        try:
            # Initial refresh
            await self.refresh_cycle()

            while self.running and not self.shutdown_event.is_set():
                try:
                    # Wait for next refresh interval or shutdown signal
                    await asyncio.wait_for(
                        self.shutdown_event.wait(), timeout=self.settings.refresh_interval
                    )

                    # If we get here, shutdown was signaled
                    break

                except TimeoutError:
                    # Timeout means it's time for next refresh
                    if self.running:
                        await self.refresh_cycle()

        except Exception:
            logger.exception("Scheduler error")

        logger.info("Refresh scheduler stopped")

    async def start(self) -> bool:
        """Start the Calendar Bot application."""
        try:
            logger.info("Starting Calendar Bot...")

            # Automatically clean up any existing calendarbot processes if configured
            if self.settings.auto_kill_existing:
                logger.info("Checking for existing Calendar Bot processes...")
                killed_count, errors = kill_calendarbot_processes(exclude_self=True)

                if killed_count > 0:
                    logger.info(f"Terminated {killed_count} existing Calendar Bot processes")

                if errors:
                    logger.warning(f"Process cleanup completed with {len(errors)} warnings:")
                    for error in errors:
                        logger.warning(f"  - {error}")
            else:
                logger.debug("Auto-cleanup of existing processes disabled in configuration")

            # Initialize components
            if not await self.initialize():
                logger.error("Initialization failed, exiting")
                return False

            self.running = True

            # Start the scheduler
            await self.run_scheduler()

            return True

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            return True
        except Exception:
            logger.exception("Error running Calendar Bot")
            return False
        finally:
            await self.cleanup()

    async def stop(self) -> None:
        """Stop the Calendar Bot application."""
        logger.info("Stopping Calendar Bot...")
        self.running = False
        self.shutdown_event.set()

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            logger.info("Cleaning up resources...")

            # Close any open connections
            # (SourceManager handles its own cleanup internally)

            # Clear all events from database on app exit (only if components are initialized)
            if self.cache_manager is not None:
                await safe_async_call(
                    self.cache_manager.clear_all_events, default=0, log_errors=False
                )

            logger.info("Cleanup completed")

        except Exception:
            logger.exception("Error during cleanup")

    async def status(self) -> dict[str, Any]:
        """Get current application status.

        Returns:
            Dictionary with status information
        """
        try:
            if not self._ensure_components_initialized():
                return {
                    "running": self.running,
                    "error": "Components not initialized",
                    "last_successful_update": (
                        self.last_successful_update.isoformat()
                        if self.last_successful_update
                        else None
                    ),
                    "consecutive_failures": self.consecutive_failures,
                }

            assert self.source_manager is not None
            assert self.cache_manager is not None

            source_info = await self.source_manager.get_source_info()
            cache_summary = await self.cache_manager.get_cache_summary()
        except Exception as e:
            logger.exception("Failed to get status")
            return {"error": str(e)}
        else:
            return {
                "running": self.running,
                "last_successful_update": (
                    self.last_successful_update.isoformat() if self.last_successful_update else None
                ),
                "consecutive_failures": self.consecutive_failures,
                "source_configured": source_info.is_configured,
                "source_status": source_info.status,
                "source_url": source_info.url,
                "cache_events": cache_summary.get("total_events", 0),
                "cache_fresh": cache_summary.get("is_fresh", False),
                "settings": {
                    "refresh_interval": self.settings.refresh_interval,
                    "cache_ttl_hours": self.settings.cache_ttl / 3600,
                    "display_type": self.settings.display_type,
                },
            }


def setup_signal_handlers(app: CalendarBot) -> None:
    """Set up signal handlers for graceful shutdown."""

    background_tasks = set()

    def signal_handler(signum: int, frame: Any) -> None:  # noqa: ARG001
        logger.info(f"Received signal {signum}")
        task = asyncio.create_task(app.stop())
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def check_first_run_configuration() -> bool:
    """Check if this is a first run and provide setup guidance."""
    from pathlib import Path  # noqa: PLC0415

    # Check for config file in project directory first
    project_config = Path(__file__).parent / "config" / "config.yaml"
    if project_config.exists():
        return True

    # Check user config directory
    user_config_dir = Path.home() / ".config" / "calendarbot"
    user_config = user_config_dir / "config.yaml"
    if user_config.exists():
        return True

    # Check if essential settings are available via environment variables
    return bool(settings.ics_url)


async def main() -> int:
    """Main entry point for the application with first-run detection."""
    try:
        # Check if configuration exists
        if not check_first_run_configuration():
            logger.error("Configuration missing. Please run 'calendarbot --setup' to configure.")
            print("\n" + "=" * 60)
            print("⚙️  Configuration Required")
            print("=" * 60)
            print("Calendar Bot needs to be configured before it can run.")
            print("\n🔧 Quick Setup:")
            print("   calendarbot --setup    # Interactive configuration wizard")
            print("\n📖 Manual Setup:")
            print(
                "   1. Copy calendarbot/config/config.yaml.example to calendarbot/config/config.yaml"
            )
            print("   2. Edit config.yaml with your calendar URL")
            print("   3. Or set environment variable: CALENDARBOT_ICS_URL=your-url")
            print("=" * 60)
            return 1

        # Validate required settings
        if not settings.ics_url:
            logger.error("ICS URL configuration is required")
            logger.info(
                "Please configure ICS URL in config.yaml or via CALENDARBOT_ICS_URL environment variable"
            )
            return 1

        # Create and start the application
        app = CalendarBot()

        # Set up signal handlers for graceful shutdown
        setup_signal_handlers(app)

        # Start the application
        success = await app.start()

        return 0 if success else 1

    except Exception:
        logger.exception("Fatal error")
        return 1


if __name__ == "__main__":
    # Run the application
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
