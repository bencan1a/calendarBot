"""Daemon process management utilities for CalendarBot.

This module provides comprehensive daemon process management capabilities including
PID file management, process detachment, status monitoring, and graceful shutdown
handling. It follows Unix daemon conventions and integrates with CalendarBot's
existing logging and configuration systems.

Architecture:
    - DaemonManager: Core PID file and process management
    - DaemonStatus: Status information and health monitoring
    - DaemonController: High-level daemon operations
    - Process detachment utilities for background operation
    - Signal handling for graceful shutdown
"""

import os
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None  # type: ignore[assignment]
    PSUTIL_AVAILABLE = False

from .logging import get_logger

logger = get_logger(__name__)


class DaemonError(Exception):
    """Base exception for daemon-related errors."""


class DaemonAlreadyRunningError(DaemonError):
    """Raised when attempting to start a daemon that is already running."""


class DaemonNotRunningError(DaemonError):
    """Raised when attempting to operate on a daemon that is not running."""


class PIDFileError(DaemonError):
    """Raised when PID file operations fail."""


class DaemonStatus:
    """Container for daemon status information and health monitoring.

    Provides comprehensive status information about a running daemon process
    including PID, uptime, port, health status, and log file locations.
    """

    def __init__(
        self,
        pid: int,
        port: int,
        start_time: Optional[datetime] = None,
        log_file: Optional[Path] = None,
        is_healthy: bool = True,
    ) -> None:
        """Initialize daemon status information.

        Args:
            pid: Process ID of the daemon
            port: Port the web server is running on
            start_time: When the daemon was started (defaults to now)
            log_file: Path to the daemon's log file
            is_healthy: Whether the daemon is responding properly
        """
        self.pid = pid
        self.port = port
        self.start_time = start_time or datetime.now()
        self.log_file = log_file
        self.is_healthy = is_healthy

    @property
    def uptime(self) -> timedelta:
        """Calculate daemon uptime since start."""
        return datetime.now() - self.start_time

    def format_status(self) -> str:
        """Format status information for display.

        Returns:
            Formatted status string with key daemon information
        """
        uptime_str = str(self.uptime).split(".")[0]  # Remove microseconds
        health_str = "healthy" if self.is_healthy else "unhealthy"

        status_lines = [
            "CalendarBot Daemon Status:",
            f"  PID: {self.pid}",
            f"  Port: {self.port}",
            f"  Uptime: {uptime_str}",
            f"  Health: {health_str}",
        ]

        if self.log_file:
            status_lines.append(f"  Log file: {self.log_file}")

        return "\n".join(status_lines)


class DaemonManager:
    """Core daemon process management with PID file operations.

    Handles PID file creation, validation, cleanup, and process health checking.
    Follows Unix daemon conventions for reliable background service operation.
    """

    def __init__(self, pid_file_path: Optional[Path] = None) -> None:
        """Initialize daemon manager with PID file location.

        Args:
            pid_file_path: Custom PID file path (defaults to ~/.calendarbot/daemon.pid)
        """
        if pid_file_path:
            self.pid_file_path = Path(pid_file_path)
        else:
            self.pid_file_path = self.get_default_pid_file_path()

        # Create directory if it doesn't exist
        self.pid_file_path.parent.mkdir(parents=True, exist_ok=True)

        logger.debug(f"DaemonManager initialized with PID file: {self.pid_file_path}")

    @staticmethod
    def get_default_pid_file_path() -> Path:
        """Get the default PID file path.

        Returns:
            Path to ~/.calendarbot/daemon.pid
        """
        home_dir = Path.home()
        return home_dir / ".calendarbot" / "daemon.pid"

    def create_pid_file(self, pid: Optional[int] = None) -> int:
        """Create PID file with current or specified process ID.

        Args:
            pid: Process ID to write (defaults to current process)

        Returns:
            The PID that was written to the file

        Raises:
            DaemonAlreadyRunningError: If daemon is already running
            PIDFileError: If PID file cannot be created
        """
        if pid is None:
            pid = os.getpid()

        # Check if daemon is already running
        if self.is_daemon_running():
            existing_pid = self.read_pid_file()
            raise DaemonAlreadyRunningError(f"Daemon already running with PID {existing_pid}")

        try:
            with self.pid_file_path.open("w", encoding="utf-8") as f:
                f.write(str(pid))

            logger.info(f"Created PID file: {self.pid_file_path} with PID {pid}")
            return pid

        except OSError as e:
            raise PIDFileError(f"Failed to create PID file {self.pid_file_path}: {e}") from e

    def read_pid_file(self) -> Optional[int]:
        """Read PID from file if it exists and is valid.

        Returns:
            PID from file, or None if file doesn't exist or is invalid
        """
        if not self.pid_file_path.exists():
            return None

        try:
            with self.pid_file_path.open(encoding="utf-8") as f:
                pid_str = f.read().strip()

            if not pid_str:
                logger.warning(f"Empty PID file: {self.pid_file_path}")
                return None

            pid = int(pid_str)

            # Validate PID is reasonable
            if pid <= 0:
                logger.warning(f"Invalid PID in file: {pid}")
                return None

            return pid

        except (OSError, ValueError) as e:
            logger.warning(f"Failed to read PID file {self.pid_file_path}: {e}")
            return None

    def cleanup_pid_file(self) -> bool:
        """Remove PID file if it exists.

        Returns:
            True if file was removed or didn't exist, False if removal failed
        """
        if not self.pid_file_path.exists():
            return True

        try:
            self.pid_file_path.unlink()
            logger.info(f"Removed PID file: {self.pid_file_path}")
            return True

        except OSError:
            logger.exception("Failed to remove PID file {self.pid_file_path}")
            return False

    def is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running.

        Args:
            pid: Process ID to check

        Returns:
            True if process is running, False otherwise
        """
        if PSUTIL_AVAILABLE and psutil is not None:
            return psutil.pid_exists(pid)
        # Fallback to kill signal 0 (doesn't actually kill)
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def is_daemon_running(self) -> bool:
        """Check if daemon is currently running.

        Returns:
            True if daemon is running, False otherwise
        """
        pid = self.read_pid_file()
        if pid is None:
            return False

        is_running = self.is_process_running(pid)

        # Clean up stale PID file
        if not is_running:
            logger.info(f"Cleaning up stale PID file for non-existent process {pid}")
            self.cleanup_pid_file()

        return is_running

    def get_daemon_pid(self) -> Optional[int]:
        """Get PID of running daemon, if any.

        Returns:
            PID of running daemon, or None if not running
        """
        if self.is_daemon_running():
            return self.read_pid_file()
        return None

    def get_process_info(self, pid: int) -> dict[str, Any]:
        """Get detailed process information.

        Args:
            pid: Process ID to examine

        Returns:
            Dictionary with process information
        """
        info = {"pid": pid, "running": False}

        if not self.is_process_running(pid):
            return info

        info["running"] = True

        if PSUTIL_AVAILABLE and psutil is not None:
            try:
                process = psutil.Process(pid)
                info.update(
                    {
                        "name": process.name(),
                        "create_time": datetime.fromtimestamp(
                            process.create_time(), tz=timezone.utc
                        ),
                        "memory_info": process.memory_info()._asdict(),
                        "cpu_percent": process.cpu_percent(),
                        "status": process.status(),
                        "cmdline": process.cmdline(),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning(f"Failed to get process info for PID {pid}: {e}")
            except Exception as e:
                logger.warning(f"Failed to get process info for PID {pid}: {e}")

        return info


def detach_process() -> None:
    """Detach current process from terminal using double fork.

    Implements Unix daemon conventions for proper process detachment:
    1. First fork to background
    2. Become session leader
    3. Second fork to prevent TTY reacquisition
    4. Redirect standard file descriptors
    5. Reset asyncio event loop to prevent conflicts

    Raises:
        DaemonError: If process detachment fails
    """
    logger.info("Starting process detachment for daemon mode")

    try:
        # First fork
        pid = os.fork()
        if pid > 0:
            # Parent process exits
            sys.exit(0)
    except OSError as e:
        raise DaemonError(f"First fork failed: {e}") from e

    # Become session leader
    try:
        os.setsid()
    except OSError as e:
        raise DaemonError(f"Failed to become session leader: {e}") from e

    try:
        # Second fork
        pid = os.fork()
        if pid > 0:
            # Parent process exits
            sys.exit(0)
    except OSError as e:
        raise DaemonError(f"Second fork failed: {e}") from e

    # Change working directory to root to avoid keeping filesystem busy
    os.chdir("/")

    # Set file mode creation mask
    os.umask(0)

    # Reset asyncio event loop to prevent conflicts after fork
    try:
        import asyncio  # noqa: PLC0415

        logger.info("DEBUG: Starting asyncio event loop reset")

        # Close any existing event loop from parent process
        try:
            loop = asyncio.get_running_loop()
            logger.info("DEBUG: Found existing event loop, closing it")
            loop.close()
        except RuntimeError:
            # No running loop, which is fine
            logger.info("DEBUG: No existing event loop found")

        # Set a fresh event loop policy for the daemon process
        logger.info("DEBUG: Setting new event loop policy")
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

        logger.info("Reset asyncio event loop for daemon process")
        logger.info("DEBUG: Asyncio reset completed successfully")
    except Exception:
        logger.exception("CRITICAL: Failed to reset asyncio event loop")

    logger.info("DEBUG: Starting file descriptor redirection")

    # Redirect standard file descriptors to /dev/null
    try:
        logger.info("DEBUG: Opening /dev/null for reading")
        with Path("/dev/null").open(encoding="utf-8") as devnull_r:
            logger.info("DEBUG: Redirecting stdin to /dev/null")
            os.dup2(devnull_r.fileno(), sys.stdin.fileno())

        logger.info("DEBUG: Opening /dev/null for writing")
        with Path("/dev/null").open("w", encoding="utf-8") as devnull_w:
            logger.info("DEBUG: Redirecting stdout to /dev/null")
            os.dup2(devnull_w.fileno(), sys.stdout.fileno())
            logger.info("DEBUG: Redirecting stderr to /dev/null")
            os.dup2(devnull_w.fileno(), sys.stderr.fileno())

        logger.info("DEBUG: File descriptor redirection completed")
    except Exception:
        logger.exception("CRITICAL: Failed to redirect file descriptors")

    logger.info(f"Process detached successfully, PID: {os.getpid()}")


class DaemonController:
    """High-level daemon operations controller.

    Provides user-facing daemon management operations including start, stop,
    status checking, and signal handling. Coordinates between DaemonManager
    and the actual CalendarBot web server process.
    """

    def __init__(self, daemon_manager: Optional[DaemonManager] = None) -> None:
        """Initialize daemon controller.

        Args:
            daemon_manager: Custom daemon manager (defaults to new instance)
        """
        self.daemon_manager = daemon_manager or DaemonManager()
        self.logger = get_logger(f"{__name__}.controller")

    def start_daemon(self, command_args: list[str], port: int = 8000, detach: bool = True) -> int:
        """Start CalendarBot as a daemon process.

        Args:
            command_args: Command line arguments for CalendarBot
            port: Port for web server (default: 8000)
            detach: Whether to detach from terminal (default: True)

        Returns:
            PID of the started daemon process

        Raises:
            DaemonAlreadyRunningError: If daemon is already running
            DaemonError: If daemon startup fails
        """
        self.logger.info(f"Starting daemon on port {port}")

        # Check if already running
        if self.daemon_manager.is_daemon_running():
            existing_pid = self.daemon_manager.get_daemon_pid()
            raise DaemonAlreadyRunningError(f"Daemon already running with PID {existing_pid}")

        if detach:
            # Detach from terminal
            detach_process()

        # Create PID file
        pid = self.daemon_manager.create_pid_file()

        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()

        self.logger.info(f"Daemon started successfully with PID {pid}")
        return pid

    def stop_daemon(self, timeout: int = 30) -> bool:
        """Stop running daemon gracefully.

        Args:
            timeout: Maximum seconds to wait for shutdown (default: 30)

        Returns:
            True if daemon was stopped successfully, False otherwise

        Raises:
            DaemonNotRunningError: If daemon is not running
        """
        self.logger.info("Stopping daemon")

        pid = self.daemon_manager.get_daemon_pid()
        if pid is None:
            raise DaemonNotRunningError("No daemon is currently running")

        self.logger.info(f"Sending SIGTERM to PID {pid}")

        try:
            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)
        except (OSError, ProcessLookupError) as e:
            self.logger.warning(f"Failed to send SIGTERM to PID {pid}: {e}")
            # Process might already be dead, clean up PID file
            self.daemon_manager.cleanup_pid_file()
            return True

        # Wait for process to exit
        for _ in range(timeout):
            if not self.daemon_manager.is_process_running(pid):
                self.logger.info(f"Daemon PID {pid} stopped gracefully")
                self.daemon_manager.cleanup_pid_file()
                return True
            time.sleep(1)

        # Force kill if still running
        self.logger.warning(f"Daemon PID {pid} did not stop gracefully, sending SIGKILL")
        try:
            os.kill(pid, signal.SIGKILL)
            time.sleep(2)  # Give it a moment

            if not self.daemon_manager.is_process_running(pid):
                self.logger.info(f"Daemon PID {pid} force killed")
                self.daemon_manager.cleanup_pid_file()
                return True
            self.logger.error(f"Failed to kill daemon PID {pid}")
            return False

        except (OSError, ProcessLookupError):
            # Process is gone
            self.daemon_manager.cleanup_pid_file()
            return True

    def _parse_port_from_cmdline(self, cmdline: list[str]) -> Optional[int]:
        """Parse port number from command line arguments.

        Args:
            cmdline: List of command line arguments

        Returns:
            Port number if found, None otherwise
        """
        try:
            for i, arg in enumerate(cmdline):
                if arg == "--port" and i + 1 < len(cmdline):
                    return int(cmdline[i + 1])
                if arg.startswith("--port="):
                    return int(arg.split("=", 1)[1])
        except (ValueError, IndexError):
            logger.warning(f"Failed to parse port from command line: {cmdline}")
        return None

    def get_daemon_status(self) -> Optional[DaemonStatus]:
        """Get current daemon status information.

        Returns:
            DaemonStatus object if daemon is running, None otherwise
        """
        pid = self.daemon_manager.get_daemon_pid()
        if pid is None:
            return None

        # Get process info
        process_info = self.daemon_manager.get_process_info(pid)

        # Determine start time
        start_time = None
        if PSUTIL_AVAILABLE and "create_time" in process_info:
            start_time = process_info["create_time"]

        # Basic health check - process is running
        is_healthy = process_info.get("running", False)

        # Try to determine actual port from command line arguments
        port = 8080  # Default fallback (matches system default)
        if process_info.get("cmdline"):
            detected_port = self._parse_port_from_cmdline(process_info["cmdline"])
            if detected_port:
                port = detected_port
                logger.debug(f"Detected daemon port from command line: {port}")
            else:
                logger.debug("Could not detect port from command line, using default 8080")

        # Find log file (could be enhanced to read from daemon's actual log location)
        log_file = None

        return DaemonStatus(
            pid=pid, port=port, start_time=start_time, log_file=log_file, is_healthy=is_healthy
        )

    def send_signal(self, sig: int) -> bool:
        """Send signal to running daemon.

        Args:
            sig: Signal number to send

        Returns:
            True if signal was sent successfully, False otherwise

        Raises:
            DaemonNotRunningError: If daemon is not running
        """
        pid = self.daemon_manager.get_daemon_pid()
        if pid is None:
            raise DaemonNotRunningError("No daemon is currently running")

        try:
            os.kill(pid, sig)
            self.logger.info(f"Sent signal {sig} to daemon PID {pid}")
            return True
        except (OSError, ProcessLookupError):
            self.logger.exception(f"Failed to send signal {sig} to PID {pid}")
            return False

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""

        def signal_handler(signum: int, _frame: Any) -> None:
            """Handle shutdown signals gracefully."""
            self.logger.info(f"Received signal {signum}, shutting down daemon")

            # Clean up PID file
            self.daemon_manager.cleanup_pid_file()

            # Exit gracefully
            sys.exit(0)

        # Register signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        self.logger.debug("Signal handlers configured for graceful shutdown")


# Convenience functions for common operations


def get_pid_file_path() -> Path:
    """Get the default PID file path.

    Returns:
        Path to the default daemon PID file
    """
    return DaemonManager.get_default_pid_file_path()


def is_daemon_running() -> bool:
    """Check if CalendarBot daemon is currently running.

    Returns:
        True if daemon is running, False otherwise
    """
    manager = DaemonManager()
    return manager.is_daemon_running()


def get_daemon_status() -> Optional[DaemonStatus]:
    """Get status of running daemon.

    Returns:
        DaemonStatus object if daemon is running, None otherwise
    """
    controller = DaemonController()
    return controller.get_daemon_status()


def start_daemon(command_args: list[str], port: int = 8000) -> int:
    """Start CalendarBot daemon.

    Args:
        command_args: Command line arguments for CalendarBot
        port: Port for web server (default: 8000)

    Returns:
        PID of started daemon process

    Raises:
        DaemonAlreadyRunningError: If daemon is already running
        DaemonError: If daemon startup fails
    """
    controller = DaemonController()
    return controller.start_daemon(command_args, port)


def stop_daemon(timeout: int = 30) -> bool:
    """Stop running CalendarBot daemon.

    Args:
        timeout: Maximum seconds to wait for shutdown (default: 30)

    Returns:
        True if daemon was stopped successfully, False otherwise

    Raises:
        DaemonNotRunningError: If daemon is not running
    """
    controller = DaemonController()
    return controller.stop_daemon(timeout)


def cleanup_daemon() -> bool:
    """Clean up daemon resources (PID file, etc.).

    Returns:
        True if cleanup was successful, False otherwise
    """
    manager = DaemonManager()
    return manager.cleanup_pid_file()
