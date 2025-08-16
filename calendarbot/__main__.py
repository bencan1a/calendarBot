"""Entry point for `python -m calendarbot` command.

This module provides the standard Python module execution interface that
delegates to the comprehensive CLI module, following Python packaging
best practices with proper internal imports.
"""

import asyncio
import logging
import sys

logger = logging.getLogger(__name__)

try:
    from calendarbot.cli import main_entry
    from calendarbot.cli.parser import create_parser
except ImportError:
    logger.exception("Error importing main entry point")
    logger.info("Make sure you're running from the Calendar Bot project directory.")
    sys.exit(1)


def _handle_daemon_mode_early() -> bool:
    """Handle daemon mode detection before async context.

    Returns:
        True if daemon mode was handled, False if normal processing should continue
    """
    # Parse args early to detect daemon mode
    parser = create_parser()
    args = parser.parse_args()

    # Only handle daemon start mode early (status/stop can run normally)
    if hasattr(args, "daemon") and args.daemon:
        # Import here to avoid circular imports
        from calendarbot.cli.modes.daemon import _start_daemon_process  # noqa: PLC0415
        from calendarbot.utils.daemon import (  # noqa: PLC0415
            DaemonError,
            detach_process,
        )

        print("Starting CalendarBot daemon...")

        try:
            # Fork BEFORE any async context to avoid event loop corruption
            detach_process()

            # After fork, start fresh async context for daemon process
            exit_code = asyncio.run(_start_daemon_process(args))
            sys.exit(exit_code)

        except DaemonError as e:
            print(f"Daemon startup error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error starting daemon: {e}")
            sys.exit(1)

    return False


def main() -> None:
    """Entry point for python -m calendarbot.

    This function maintains compatibility with setuptools entry points
    while delegating all functionality to the comprehensive CLI module.
    """
    try:
        # Handle daemon mode early to avoid async event loop conflicts
        if _handle_daemon_mode_early():
            return  # Daemon mode was handled, exit

        # Normal async processing for all other modes
        exit_code = asyncio.run(main_entry())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
