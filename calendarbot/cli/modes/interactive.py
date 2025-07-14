"""Interactive mode handler for Calendar Bot CLI.

This module provides the interactive console navigation mode with arrow key
controls for Calendar Bot. This functionality will be migrated from root main.py
during Phase 2 of the architectural refactoring.
"""

import asyncio
from typing import Any


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

        from ..config import apply_rpi_overrides

        # Apply command-line logging overrides with priority system
        updated_settings = apply_command_line_overrides(settings, args)

        # Apply RPI-specific overrides
        updated_settings = apply_rpi_overrides(updated_settings, args)

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


def setup_interactive_logging(settings: Any, display_manager: Any = None) -> Any:
    """Setup enhanced logging for interactive mode.

    This function will be migrated from root main.py in Phase 2 to handle
    the specialized logging requirements for interactive mode with split display.

    Args:
        settings: Application settings object
        display_manager: Display manager for split logging display

    Returns:
        Configured logger instance
    """
    # Placeholder implementation - will be migrated in Phase 2
    print("Interactive logging setup placeholder - will be migrated from root main.py")
    return None


def create_interactive_controller(cache_manager: Any, display_manager: Any) -> Any:
    """Create interactive controller instance.

    This function will be migrated from root main.py in Phase 2 to handle
    creation and configuration of the interactive navigation controller.

    Args:
        cache_manager: Cache manager instance
        display_manager: Display manager instance

    Returns:
        Interactive controller instance
    """
    # Placeholder implementation - will be migrated in Phase 2
    print("Interactive controller creation placeholder - will be migrated from root main.py")
    return None


__all__ = [
    "run_interactive_mode",
    "setup_interactive_logging",
    "create_interactive_controller",
]
