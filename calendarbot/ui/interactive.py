"""Interactive UI controller for calendar navigation."""

import asyncio
import contextlib
import logging
from datetime import date, datetime as dt, timedelta
from typing import Any, Optional, cast

from ..cache import CacheManager
from ..cache.models import CachedEvent
from ..display import DisplayManager
from .keyboard import KeyboardHandler, KeyCode
from .navigation import NavigationState

logger = logging.getLogger(__name__)


class InteractiveController:
    """Controls interactive calendar navigation UI."""

    def __init__(self, cache_manager: CacheManager, display_manager: DisplayManager):
        """Initialize interactive controller.

        Args:
            cache_manager: Cache manager for retrieving events
            display_manager: Display manager for rendering
        """
        self.cache_manager = cache_manager
        self.display_manager = display_manager

        # UI components
        self.navigation = NavigationState()
        self.keyboard = KeyboardHandler()

        # State
        self._running = False
        self._last_data_update: Optional[dt] = None
        self._background_update_task: Optional[asyncio.Task[Any]] = None
        self._last_display_update_task: Optional[asyncio.Task[Any]] = None

        # Setup keyboard handlers
        self._setup_keyboard_handlers()

        # Setup navigation callbacks
        self.navigation.add_change_callback(self._on_date_changed)

        logger.info("Interactive controller initialized")

    def _setup_keyboard_handlers(self) -> None:
        """Set up keyboard event handlers."""
        # Navigation keys
        self.keyboard.register_key_handler(KeyCode.LEFT_ARROW, self._handle_previous_day)
        self.keyboard.register_key_handler(KeyCode.RIGHT_ARROW, self._handle_next_day)

        # Jump keys
        self.keyboard.register_key_handler(KeyCode.SPACE, self._handle_jump_to_today)
        self.keyboard.register_key_handler(KeyCode.HOME, self._handle_start_of_week)
        self.keyboard.register_key_handler(KeyCode.END, self._handle_end_of_week)

        # Control keys
        self.keyboard.register_key_handler(KeyCode.ESCAPE, self._handle_exit)

        logger.debug("Keyboard handlers configured")

    async def _handle_previous_day(self) -> None:
        """Handle left arrow key - go to previous day."""
        self.navigation.navigate_backward()
        logger.debug("User navigated to previous day")

    async def _handle_next_day(self) -> None:
        """Handle right arrow key - go to next day."""
        self.navigation.navigate_forward()
        logger.debug("User navigated to next day")

    async def _handle_jump_to_today(self) -> None:
        """Handle space key - jump to today."""
        self.navigation.jump_to_today()
        logger.debug("User jumped to today")

    async def _handle_start_of_week(self) -> None:
        """Handle home key - jump to start of week."""
        self.navigation.jump_to_start_of_week()
        logger.debug("User jumped to start of week")

    async def _handle_end_of_week(self) -> None:
        """Handle end key - jump to end of week."""
        self.navigation.jump_to_end_of_week()
        logger.debug("User jumped to end of week")

    async def _handle_exit(self) -> None:
        """Handle escape key - exit interactive mode."""
        logger.info("User requested exit from interactive mode")
        await self.stop()

    def _on_date_changed(self, new_date: date) -> None:
        """Handle date change events from navigation.

        Args:
            new_date: New selected date
        """
        logger.debug(f"Date changed to: {new_date}")
        # Trigger display update
        self._last_display_update_task = asyncio.create_task(self._update_display())

    async def start(self, initial_date: Optional[date] = None) -> None:
        """Start interactive mode.

        Args:
            initial_date: Optional initial date to display
        """
        if self._running:
            logger.warning("Interactive controller already running")
            return

        self._running = True

        # Set initial date if provided
        if initial_date:
            self.navigation.jump_to_date(initial_date)

        # Enable split display logging if console renderer supports it
        self._setup_split_display_logging()

        logger.info("Starting interactive calendar navigation")

        try:
            # Initial display update
            await self._update_display()

            # Start keyboard listening
            keyboard_task = asyncio.create_task(self.keyboard.start_listening())

            # Start background update checking
            update_task = asyncio.create_task(self._background_update_loop())

            # Wait for either task to complete (keyboard stops on ESC)
            done, pending = await asyncio.wait(
                {keyboard_task, update_task}, return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel remaining tasks
            for task in pending:
                with contextlib.suppress(asyncio.CancelledError):
                    task.cancel()
                    await task

        except Exception:
            logger.exception("Error in interactive mode")
        finally:
            self._running = False
            self._cleanup_split_display_logging()
            logger.info("Interactive mode stopped")

    async def stop(self) -> None:
        """Stop interactive mode."""
        self._running = False
        self.keyboard.stop_listening()

        if self._background_update_task:
            self._background_update_task.cancel()

        logger.debug("Interactive controller stop requested")

    async def _update_display(self) -> None:
        """Update the display with current date's events."""
        try:
            # Get events for selected date
            selected_date = self.navigation.selected_date
            start_datetime = dt.combine(selected_date, dt.min.time())
            end_datetime = start_datetime + timedelta(days=1)

            logger.debug(
                f"Querying events for {selected_date} between {start_datetime} and {end_datetime}"
            )

            # Retrieve events from cache
            events = await self.cache_manager.get_events_by_date_range(start_datetime, end_datetime)

            logger.debug(f"Found {len(events)} events for {selected_date}")
            if events:
                for event in events[:3]:  # Log first 3 events
                    try:
                        logger.debug(f"Event - {event.subject} at {event.start_datetime}")
                    except AttributeError:
                        logger.debug("Event details not available for logging")

            # Prepare status information
            status_info = await self._get_status_info()

            # Display events
            success = await self.display_manager.display_events(
                events, status_info, clear_screen=True
            )

            if success:
                logger.debug(f"Display updated for {selected_date} with {len(events)} events")
            else:
                logger.warning("Display update failed")

        except Exception:
            logger.exception("Failed to update display")

    async def _get_status_info(self) -> dict[str, Any]:
        """Get status information for display.

        Returns:
            Status information dictionary
        """
        try:
            # Get cache status
            cache_status = await self.cache_manager.get_cache_status()

            # Get navigation info
            nav_info = {
                "selected_date": self.navigation.get_display_date(),
                "is_today": self.navigation.is_today(),
                "navigation_help": self.keyboard.get_help_text(),
            }

            # Combine status information
            return {
                "last_update": cache_status.last_update,
                "is_cached": cache_status.is_stale,
                "connection_status": "Online" if not cache_status.is_stale else "Cached Data",
                "interactive_mode": True,
                **nav_info,
            }
        except Exception as e:
            logger.exception("Failed to get status info")
            return {
                "selected_date": self.navigation.get_display_date(),
                "interactive_mode": True,
                "error": str(e),
            }

    async def _background_update_loop(self) -> None:
        """Background loop to check for data updates."""
        try:
            while self._running:
                await self._background_update_iteration()
                if self._running:  # Check again before sleeping
                    await asyncio.sleep(30)  # Check every 30 seconds
        except asyncio.CancelledError:
            pass  # Expected when stopping
        except Exception:
            logger.exception("Error in background update loop")
            # Don't re-raise to avoid crashing the loop

    async def _background_update_iteration(self) -> None:
        """Single iteration of background update check, extracted to avoid try/except overhead in loop."""
        # Check if cache has been updated
        cache_status = await self.cache_manager.get_cache_status()

        # Normalize cache status timestamp for comparison
        last_update_normalized: Optional[dt] = None
        if cache_status.last_update:
            # Convert string timestamp to datetime for comparison
            last_update_normalized = dt.fromisoformat(
                cache_status.last_update.replace("Z", "+00:00")
            )

        if self._last_data_update is None or (
            last_update_normalized and last_update_normalized != self._last_data_update
        ):
            # Data has been updated, refresh display
            self._last_data_update = last_update_normalized
            await self._update_display()
            logger.debug("Display refreshed due to data update")

        # Update today reference (in case we've crossed midnight)
        self.navigation.update_today()

    async def get_events_for_date(self, target_date: date) -> list[CachedEvent]:
        """Get events for a specific date.

        Args:
            target_date: Date to get events for

        Returns:
            List of events for the date
        """
        try:
            start_datetime = dt.combine(target_date, dt.min.time())
            end_datetime = start_datetime + timedelta(days=1)

            events = await self.cache_manager.get_events_by_date_range(start_datetime, end_datetime)
        except Exception:
            logger.exception(f"Failed to get events for {target_date}")
            return []
        else:
            return events

    async def get_events_for_week(self, target_date: date) -> dict[date, list[CachedEvent]]:
        """Get events for the week containing the target date.

        Args:
            target_date: Date within the target week

        Returns:
            Dictionary mapping dates to event lists
        """
        try:
            # Get start and end of week
            start_of_week = target_date - timedelta(days=target_date.weekday())
            end_of_week = start_of_week + timedelta(days=6)

            # Get all events for the week
            start_datetime = dt.combine(start_of_week, dt.min.time())
            end_datetime = dt.combine(end_of_week, dt.max.time())

            all_events = await self.cache_manager.get_events_by_date_range(
                start_datetime, end_datetime
            )

            # Group events by date
            events_by_date: dict[date, list[CachedEvent]] = {}
            current_date = start_of_week

            while current_date <= end_of_week:
                events_by_date[current_date] = []
                current_date += timedelta(days=1)

            # Process events with extracted function to avoid try/except overhead in loop
            for event in all_events:
                self._process_event_for_date_grouping(event, events_by_date)

            return events_by_date

        except Exception:
            logger.exception(f"Failed to get events for week containing {target_date}")
            return {}

    def _process_event_for_date_grouping(self, event: CachedEvent, events_by_date: dict[date, list[CachedEvent]]) -> None:
        """Process a single event for date grouping, avoiding try/except overhead in loops.

        Args:
            event: Event to process
            events_by_date: Dictionary to group events by date
        """
        try:
            logger.debug(f"Processing event '{event.subject}' for date grouping")
            # Use the start_dt property which provides parsed datetime
            if hasattr(event, "start_dt") and event.start_dt is not None:
                event_date = event.start_dt.date()
            elif hasattr(event, "start_datetime") and event.start_datetime:
                # Fallback to parsing start_datetime string
                from datetime import datetime  # noqa: PLC0415

                # Handle different datetime formats
                dt_str = event.start_datetime
                if "Z" in dt_str:
                    dt_str = dt_str.replace("Z", "+00:00")
                elif "+" not in dt_str and "-" not in dt_str[10:]:  # No timezone info
                    dt_str = f"{dt_str}+00:00"

                start_datetime = datetime.fromisoformat(dt_str)
                event_date = start_datetime.date()
            else:
                logger.debug(f"Event '{event.subject}' has no valid date information")
                return

            logger.debug(f"Event date parsed as: {event_date}")
            if event_date in events_by_date:
                events_by_date[event_date].append(event)
                logger.debug(f"Added event to date {event_date}")
        except Exception as e:
            logger.debug(f"Failed to process event '{event.subject}': {e}")
            logger.debug(f"Event start_datetime raw: '{event.start_datetime}'")

    @property
    def is_running(self) -> bool:
        """Check if interactive controller is running."""
        return self._running

    @property
    def current_date(self) -> date:
        """Get the currently selected date."""
        return self.navigation.selected_date

    def get_navigation_state(self) -> dict[str, Any]:
        """Get current navigation state information.

        Returns:
            Navigation state dictionary
        """
        return {
            "selected_date": self.navigation.selected_date.isoformat(),
            "display_date": self.navigation.get_display_date(),
            "is_today": self.navigation.is_today(),
            "is_past": self.navigation.is_past(),
            "is_future": self.navigation.is_future(),
            "days_from_today": self.navigation.days_from_today(),
            "week_context": self.navigation.get_week_context(),
        }

    def _setup_split_display_logging(self) -> None:
        """Set up split display logging for interactive mode."""
        try:
            # Check if we have a console renderer that supports split display
            if hasattr(self.display_manager, "renderer") and hasattr(
                self.display_manager.renderer, "enable_split_display"
            ):
                # Enable split display with default settings
                if self.display_manager.renderer is not None:
                    cast(Any, self.display_manager.renderer).enable_split_display(max_log_lines=5)
                logger.debug("Split display logging enabled for interactive mode")
            else:
                logger.debug("Split display logging not available for current renderer")
        except Exception as e:
            logger.warning(f"Failed to enable split display logging: {e}")

    def _cleanup_split_display_logging(self) -> None:
        """Clean up split display logging when exiting interactive mode."""
        try:
            # Disable split display if supported
            if hasattr(self.display_manager, "renderer") and hasattr(
                self.display_manager.renderer, "disable_split_display"
            ):
                if self.display_manager.renderer is not None:
                    cast(Any, self.display_manager.renderer).disable_split_display()
                logger.debug("Split display logging disabled")
        except Exception as e:
            logger.warning(f"Failed to disable split display logging: {e}")
