"""Interactive mode handler for Calendar Bot CLI.

This module provides the interactive console navigation mode with arrow key
controls for Calendar Bot. This functionality will be migrated from root main.py
during Phase 2 of the architectural refactoring.
"""

import asyncio
from typing import Any, Optional

from ..runtime_integration import (
    create_runtime_tracker,
    start_runtime_tracking,
    stop_runtime_tracking,
)


def setup_interactive_logging(settings: Any, display_manager: Optional[Any] = None) -> None:
    """Set up interactive logging configuration.

    This is a placeholder function that will be migrated from root main.py
    during Phase 2 of the architectural refactoring.

    Args:
        settings: Settings configuration object
        display_manager: Optional display manager for split display logging
    """
    print("Interactive logging setup placeholder - will be migrated from root main.py")


def create_interactive_controller(
    cache_manager: Optional[Any], display_manager: Optional[Any]
) -> None:
    """Create interactive controller for navigation.

    This is a placeholder function that will be migrated from root main.py
    during Phase 2 of the architectural refactoring.

    Args:
        cache_manager: Cache manager instance for data access
        display_manager: Display manager instance for rendering
    """
    print("Interactive controller creation placeholder - will be migrated from root main.py")


async def run_interactive_mode(args: Any) -> int:
    """Run Calendar Bot in interactive navigation mode.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        from calendarbot.config.settings import settings
        from calendarbot.main import CalendarBot
        from calendarbot.ui import InteractiveController
        from calendarbot.utils.logging import apply_command_line_overrides, setup_enhanced_logging

        from ..config import apply_cli_overrides

        # Apply command-line logging overrides with priority system
        updated_settings = apply_command_line_overrides(settings, args)

        # Apply CLI-specific overrides
        updated_settings = apply_cli_overrides(updated_settings, args)

        # Create runtime tracker if enabled
        runtime_tracker = create_runtime_tracker(updated_settings)

        # Start runtime tracking for interactive mode
        session_name = (
            getattr(updated_settings.runtime_tracking, "session_name", None)
            if hasattr(updated_settings, "runtime_tracking")
            else None
        )
        start_runtime_tracking(runtime_tracker, "interactive_mode", session_name)

        # Create Calendar Bot instance
        app = CalendarBot()

        # Initialize components
        if not await app.initialize():
            print("Failed to initialize Calendar Bot")
            return 1

        # Set up enhanced logging for interactive mode with split display
        logger = setup_enhanced_logging(
            updated_settings, interactive_mode=True, display_manager=app.display_manager
        )
        logger.info("Enhanced logging initialized for interactive mode")

        # Create interactive controller
        interactive = InteractiveController(app.cache_manager, app.display_manager)

        # Start background data fetching
        fetch_task = asyncio.create_task(app.run_background_fetch())

        try:
            print("Starting interactive calendar navigation...")
            print("Use arrow keys to navigate, Space for today, ESC to exit")

            # Start interactive mode
            await interactive.start()

        finally:
            # Stop runtime tracking
            stop_runtime_tracking(runtime_tracker, "interactive_mode")

            # Stop background fetching
            fetch_task.cancel()
            try:
                await fetch_task
            except asyncio.CancelledError:
                pass

            # Cleanup
            await app.cleanup()

        return 0

    except KeyboardInterrupt:
        print("\nInteractive mode interrupted")
        return 0
    except Exception as e:
        print(f"Interactive mode error: {e}")
        return 1


__all__ = [
    "run_interactive_mode",
    "setup_interactive_logging",
    "create_interactive_controller",
]
