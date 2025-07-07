"""Main application entry point for the Calendar Bot."""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional

from config.settings import settings

from .cache import CacheManager
from .display import DisplayManager
from .sources import SourceManager
from .utils import retry_with_backoff, safe_async_call, setup_logging
from .utils.process import kill_calendarbot_processes

# Set up logging
logger = setup_logging(
    log_level=settings.log_level,
    log_file=settings.log_file,
    log_dir=settings.config_dir if settings.log_file else None,
)


class CalendarBot:
    """Main Calendar Bot application coordinating all components."""

    def __init__(self):
        """Initialize Calendar Bot application."""
        self.settings = settings
        self.running = False
        self.shutdown_event = asyncio.Event()

        # Initialize components
        self.cache_manager = CacheManager(settings)
        self.source_manager = SourceManager(settings, self.cache_manager)
        self.display_manager = DisplayManager(settings)

        # Track last successful update
        self.last_successful_update: Optional[datetime] = None
        self.consecutive_failures = 0

        logger.info("Calendar Bot initialized")

    async def initialize(self) -> bool:
        """Initialize all components and ensure readiness.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing Calendar Bot components...")

            # Initialize cache manager and database
            if not await self.cache_manager.initialize():
                logger.error("Failed to initialize cache manager")
                return False

            # Initialize and validate source configuration
            if not await self.source_manager.initialize():
                logger.error("Failed to initialize source manager")
                return False

            logger.info("Calendar Bot initialization completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Calendar Bot: {e}")
            return False

    async def fetch_and_cache_events(self) -> bool:
        """Fetch events from ICS calendar feeds and cache them.

        Returns:
            True if fetch was successful, False otherwise
        """
        try:
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
            else:
                logger.error("Failed to fetch and cache events")
                return False

        except Exception as e:
            logger.error(f"Failed to fetch and cache events: {e}")
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

            if success:
                logger.debug("Display updated successfully")
            else:
                logger.warning("Display update failed")

            return success

        except Exception as e:
            logger.error(f"Failed to update display: {e}")
            return False

    async def handle_error_display(self, error_message: str):
        """Display error message with cached events if available.

        Args:
            error_message: Error message to display
        """
        try:
            # Try to get cached events to show alongside error
            cached_events = await safe_async_call(
                self.cache_manager.get_todays_cached_events, default=[], log_errors=False
            )

            await self.display_manager.display_error(error_message, cached_events)

        except Exception as e:
            logger.error(f"Failed to display error: {e}")

    async def refresh_cycle(self):
        """Perform one refresh cycle - fetch data and update display."""
        try:
            logger.debug("Starting refresh cycle")

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
            logger.error(f"Error during refresh cycle: {e}")
            await self.handle_error_display(f"System Error: {str(e)[:50]}...")

    async def run_background_fetch(self):
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

                except asyncio.TimeoutError:
                    # Timeout means it's time for next fetch
                    if self.running:
                        await self.fetch_and_cache_events()

        except Exception as e:
            logger.error(f"Background fetch error: {e}")

        logger.info("Background data fetching stopped")

    async def run_scheduler(self):
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

                except asyncio.TimeoutError:
                    # Timeout means it's time for next refresh
                    if self.running:
                        await self.refresh_cycle()

        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        logger.info("Refresh scheduler stopped")

    async def start(self):
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
        except Exception as e:
            logger.error(f"Error running Calendar Bot: {e}")
            return False
        finally:
            await self.cleanup()

    async def stop(self):
        """Stop the Calendar Bot application."""
        logger.info("Stopping Calendar Bot...")
        self.running = False
        self.shutdown_event.set()

    async def cleanup(self):
        """Clean up resources."""
        try:
            logger.info("Cleaning up resources...")

            # Close any open connections
            # (SourceManager handles its own cleanup internally)

            # Final cache cleanup
            await safe_async_call(
                self.cache_manager.cleanup_old_events, default=0, log_errors=False
            )

            logger.info("Cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def status(self) -> dict:
        """Get current application status.

        Returns:
            Dictionary with status information
        """
        try:
            source_info = await self.source_manager.get_source_info()
            cache_summary = await self.cache_manager.get_cache_summary()

            status = {
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

            return status

        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {"error": str(e)}


def setup_signal_handlers(app: CalendarBot):
    """Set up signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(app.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def check_first_run_configuration():
    """Check if this is a first run and provide setup guidance."""
    from pathlib import Path

    # Check for config file in project directory first
    project_config = Path(__file__).parent.parent / "config" / "config.yaml"
    if project_config.exists():
        return True

    # Check user config directory
    user_config_dir = Path.home() / ".config" / "calendarbot"
    user_config = user_config_dir / "config.yaml"
    if user_config.exists():
        return True

    # Check if essential settings are available via environment variables
    if settings.ics_url:
        return True

    return False


async def main():
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
            print("   1. Copy config/config.yaml.example to config/config.yaml")
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

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    # Run the application
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
