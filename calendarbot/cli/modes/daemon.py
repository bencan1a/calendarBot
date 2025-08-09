"""Daemon mode handler for Calendar Bot CLI.

This module provides daemon (background service) mode functionality for Calendar Bot,
including daemon start, status checking, and graceful shutdown operations.
The daemon mode reuses existing web server infrastructure but runs detached
from the terminal with file-only logging.
"""

from pathlib import Path
from typing import Any

from calendarbot.config.settings import settings
from calendarbot.utils.daemon import (
    DaemonAlreadyRunningError,
    DaemonController,
    DaemonError,
    DaemonNotRunningError,
    detach_process,
)
from calendarbot.utils.logging import apply_command_line_overrides, setup_enhanced_logging

from ..config import apply_cli_overrides
from .web import run_web_mode


def _configure_daemon_settings(args: Any, base_settings: Any) -> Any:
    """Configure daemon mode settings from command line arguments.

    Args:
        args: Parsed command line arguments
        base_settings: Base settings object to configure

    Returns:
        Updated settings object with daemon mode configuration
    """
    # Apply command-line logging overrides with priority system
    updated_settings = apply_command_line_overrides(base_settings, args)

    # Apply CLI-specific overrides
    updated_settings = apply_cli_overrides(updated_settings, args)

    # Configure daemon-specific logging settings
    # Force file-only logging for daemon mode
    if hasattr(updated_settings, "logging"):
        # Disable console logging for daemon mode
        updated_settings.logging.console_enabled = False
        # Ensure file logging is enabled
        updated_settings.logging.file_enabled = True
        # Set appropriate log directory for daemon
        if not updated_settings.logging.file_directory:
            log_dir = Path.home() / ".calendarbot" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            updated_settings.logging.file_directory = str(log_dir)
            # Set daemon-specific prefix to distinguish from regular logs
            updated_settings.logging.file_prefix = "daemon"

    return updated_settings


def _setup_daemon_logging(updated_settings: Any) -> Any:
    """Set up file-only logging for daemon mode.

    Args:
        updated_settings: Configured settings object

    Returns:
        Logger instance configured for daemon mode
    """
    # Set up enhanced logging for daemon mode (file-only)
    logger = setup_enhanced_logging(updated_settings, interactive_mode=False)
    logger.info("Daemon mode logging initialized")
    return logger


async def _start_daemon_process(args: Any) -> int:
    """Start CalendarBot as a daemon process (called after fork).

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)

    Note:
        This function assumes detach_process() has already been called
        before entering the async context to avoid event loop conflicts.
    """
    try:
        # Configure daemon settings
        updated_settings = _configure_daemon_settings(args, settings)

        # Create daemon controller
        daemon_controller = DaemonController()

        # Check if daemon is already running (this might be redundant after fork)
        if daemon_controller.daemon_manager.is_daemon_running():
            existing_pid = daemon_controller.daemon_manager.get_daemon_pid()
            print(f"CalendarBot daemon is already running with PID {existing_pid}")
            print("Use 'calendarbot --daemon-status' to check status")
            print("Use 'calendarbot --daemon-stop' to stop the daemon")
            return 1

        # Create PID file and set up daemon infrastructure
        pid = daemon_controller.daemon_manager.create_pid_file()

        # Set up signal handlers for graceful shutdown
        daemon_controller._setup_signal_handlers()  # noqa: SLF001

        # Set up daemon logging
        logger = _setup_daemon_logging(updated_settings)
        logger.info(f"CalendarBot daemon started with PID {pid}")
        logger.info(f"Web server will start on port {args.port}")

        # Run web mode in daemon context
        exit_code = await run_web_mode(args)

        # Clean up PID file on exit
        daemon_controller.daemon_manager.cleanup_pid_file()
        logger.info("CalendarBot daemon stopped")

        return exit_code

    except DaemonAlreadyRunningError as e:
        print(f"Error: {e}")
        return 1
    except DaemonError as e:
        print(f"Daemon startup error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error starting daemon: {e}")
        return 1


def _check_daemon_status() -> int:
    """Check and display daemon status.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        daemon_controller = DaemonController()
        status = daemon_controller.get_daemon_status()

        if status is None:
            print("CalendarBot daemon is not running")
            return 1

        print(status.format_status())
        return 0

    except Exception as e:
        print(f"Error checking daemon status: {e}")
        return 1


def _stop_daemon_process(timeout: int = 30) -> int:
    """Stop running daemon process.

    Args:
        timeout: Maximum seconds to wait for shutdown

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        daemon_controller = DaemonController()

        # Check if daemon is running
        if not daemon_controller.daemon_manager.is_daemon_running():
            print("CalendarBot daemon is not running")
            return 1

        pid = daemon_controller.daemon_manager.get_daemon_pid()
        print(f"Stopping CalendarBot daemon (PID {pid})...")

        # Stop the daemon
        success = daemon_controller.stop_daemon(timeout=timeout)

        if success:
            print("CalendarBot daemon stopped successfully")
            return 0
        print("Failed to stop CalendarBot daemon")
        return 1

    except DaemonNotRunningError:
        print("CalendarBot daemon is not running")
        return 1
    except Exception as e:
        print(f"Error stopping daemon: {e}")
        return 1


async def run_daemon_mode(args: Any) -> int:
    """Run Calendar Bot in daemon mode based on CLI arguments.

    This function handles the three daemon operations:
    - args.daemon: Start daemon in background
    - args.daemon_status: Check daemon status
    - args.daemon_stop: Stop running daemon

    Args:
        args: Parsed command line arguments with daemon flags

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Validate arguments
    if (
        not hasattr(args, "daemon")
        and not hasattr(args, "daemon_status")
        and not hasattr(args, "daemon_stop")
    ):
        print("Error: No valid daemon operation specified")
        return 1

    # Handle daemon operations
    if getattr(args, "daemon", False):
        # Start daemon operation
        return await _start_daemon_process(args)

    if getattr(args, "daemon_status", False):
        # Status check operation (synchronous)
        return _check_daemon_status()

    if getattr(args, "daemon_stop", False):
        # Stop daemon operation (synchronous)
        timeout = getattr(args, "daemon_timeout", 30)
        return _stop_daemon_process(timeout)

    print("Error: No valid daemon operation specified")
    return 1


__all__ = ["detach_process", "run_daemon_mode"]
