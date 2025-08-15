"""Interactive mode handler for Calendar Bot CLI.

This module provides the interactive console navigation mode with arrow key
controls for Calendar Bot. This functionality will be migrated from root main.py
during Phase 2 of the architectural refactoring.
"""

import asyncio
import contextlib
from typing import Any

from ..runtime_integration import (
    create_runtime_tracker,
    start_runtime_tracking,
    stop_runtime_tracking,
)


async def run_interactive_mode(args: Any) -> int:
    """Run Calendar Bot in interactive navigation mode.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        from calendarbot.config.settings import settings  # noqa: PLC0415
        from calendarbot.main import CalendarBot  # noqa: PLC0415
        from calendarbot.ui import InteractiveController  # noqa: PLC0415
        from calendarbot.utils.logging import (  # noqa: PLC0415
            apply_command_line_overrides,
            setup_enhanced_logging,
        )

        from ..config import apply_cli_overrides  # noqa: PLC0415

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
        if app.cache_manager is None or app.display_manager is None:
            logger.error("App components not properly initialized")
            return 1

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
            with contextlib.suppress(asyncio.CancelledError):
                await fetch_task

            # Cleanup
            await app.cleanup()

        return 0

    except KeyboardInterrupt:
        print("\nInteractive mode interrupted")
        return 0
    except Exception as e:
        print(f"Interactive mode error: {e}")
        return 1


__all__ = ["run_interactive_mode"]
