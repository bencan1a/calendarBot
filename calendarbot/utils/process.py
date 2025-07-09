"""Process management utilities for Calendar Bot."""

import logging
import os
import signal
import subprocess  # nosec B404
import time
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class ProcessInfo:
    """Information about a running process."""

    def __init__(self, pid: int, command: str, full_command: str):
        self.pid = pid
        self.command = command
        self.full_command = full_command

    def __str__(self) -> str:
        return f"PID {self.pid}: {self.command}"


def find_calendarbot_processes() -> List[ProcessInfo]:
    """Find all running calendarbot processes.

    Returns:
        List of ProcessInfo objects for running calendarbot processes
    """
    processes = []

    try:
        # Use pgrep to find processes matching calendarbot patterns
        patterns = ["calendarbot", "python.*calendarbot", "python.*main\\.py"]

        for pattern in patterns:
            try:
                # Get PIDs and command lines for matching processes
                result = subprocess.run(  # nosec B607
                    ["pgrep", "-af", pattern], capture_output=True, text=True, timeout=5
                )

                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        if line:
                            parts = line.split(None, 1)
                            # Check if line has space after PID (indicating command part, even if empty)
                            has_command_part = len(parts) >= 2 or (len(parts) == 1 and " " in line)

                            if has_command_part:
                                try:
                                    pid = int(parts[0])
                                    full_command = parts[1] if len(parts) > 1 else ""

                                    # Extract just the command name
                                    command_parts = full_command.split()
                                    command = command_parts[0] if command_parts else ""

                                    # Skip our own process
                                    if pid != os.getpid():
                                        processes.append(ProcessInfo(pid, command, full_command))
                                except ValueError:
                                    continue

            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                # Pattern didn't match any processes, continue
                continue

    except Exception as e:
        logger.error(f"Error finding calendarbot processes: {e}")

    return processes


def kill_calendarbot_processes(
    exclude_self: bool = True, timeout: float = 5.0
) -> Tuple[int, List[str]]:
    """Kill all running calendarbot processes.

    Args:
        exclude_self: Whether to exclude the current process from termination
        timeout: Maximum time to wait for processes to terminate

    Returns:
        Tuple of (killed_count, error_messages)
    """
    processes = find_calendarbot_processes()
    killed_count = 0
    errors = []

    if not processes:
        logger.debug("No calendarbot processes found to kill")
        return 0, []

    current_pid = os.getpid()
    logger.info(f"Found {len(processes)} calendarbot processes to terminate")

    # First pass: Send SIGTERM to all processes
    for process in processes:
        if exclude_self and process.pid == current_pid:
            logger.debug(f"Skipping current process {current_pid}")
            continue

        try:
            logger.debug(f"Sending SIGTERM to process {process.pid}: {process.command}")
            os.kill(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            # Process already dead
            logger.debug(f"Process {process.pid} already terminated")
            killed_count += 1
        except PermissionError:
            error_msg = f"Permission denied killing process {process.pid}"
            logger.warning(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Error killing process {process.pid}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    # Wait for processes to terminate gracefully
    logger.debug(f"Waiting up to {timeout}s for processes to terminate gracefully")
    time.sleep(min(timeout, 2.0))

    # Second pass: Check for remaining processes and use SIGKILL if needed
    remaining_processes = find_calendarbot_processes()
    for process in remaining_processes:
        if exclude_self and process.pid == current_pid:
            continue

        try:
            logger.warning(f"Process {process.pid} still running, sending SIGKILL")
            os.kill(process.pid, signal.SIGKILL)
            killed_count += 1
        except ProcessLookupError:
            # Process finally died
            killed_count += 1
        except Exception as e:
            error_msg = f"Error force-killing process {process.pid}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    # Final verification
    final_check = find_calendarbot_processes()
    final_count = len([p for p in final_check if not exclude_self or p.pid != current_pid])

    if final_count > 0:
        error_msg = f"{final_count} processes still running after cleanup"
        logger.warning(error_msg)
        errors.append(error_msg)
    else:
        logger.info(f"Successfully terminated {killed_count} calendarbot processes")

    return killed_count, errors


def check_port_availability(host: str, port: int) -> bool:
    """Check if a port is available for binding.

    Args:
        host: Host address to check
        port: Port number to check

    Returns:
        True if port is available, False if occupied
    """
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            result = sock.connect_ex((host, port))
            return result != 0  # Port is available if connection failed
    except Exception as e:
        logger.debug(f"Error checking port {host}:{port}: {e}")
        return False


def find_process_using_port(port: int) -> Optional[ProcessInfo]:
    """Find the process using a specific port.

    Args:
        port: Port number to check

    Returns:
        ProcessInfo if a process is found using the port, None otherwise
    """
    try:
        # Use netstat to find process using the port
        result = subprocess.run(  # nosec B607
            ["netstat", "-tlnp"], capture_output=True, text=True, timeout=5
        )

        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if f":{port} " in line and "LISTEN" in line:
                    # Extract PID from the line (format: proto recv-q send-q local-addr foreign-addr state pid/name)
                    parts = line.split()
                    if len(parts) >= 7:
                        pid_info = parts[6]
                        if "/" in pid_info:
                            try:
                                pid = int(pid_info.split("/")[0])
                                name = pid_info.split("/")[1]
                                return ProcessInfo(pid, name, f"{name} (port {port})")
                            except ValueError:
                                continue

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        # netstat might not be available, try lsof
        try:
            result = subprocess.run(  # nosec B607
                ["lsof", "-ti", f":{port}"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                pid = int(result.stdout.strip())
                return ProcessInfo(pid, "unknown", f"unknown process (port {port})")

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
            ValueError,
        ):
            pass

    return None


def auto_cleanup_before_start(host: str, port: int, force: bool = True) -> bool:
    """Automatically clean up conflicting processes before starting.

    Args:
        host: Host address to bind to
        port: Port number to bind to
        force: Whether to force cleanup even if port is available

    Returns:
        True if cleanup was successful and port is now available
    """
    logger.info(f"Checking for conflicting processes before binding to {host}:{port}")

    # Always check for calendarbot processes if force is True
    if force:
        processes = find_calendarbot_processes()
        if processes:
            logger.info(f"Found {len(processes)} existing calendarbot processes")
            for process in processes:
                logger.debug(f"  - {process}")

            killed_count, errors = kill_calendarbot_processes()

            if errors:
                logger.warning(f"Process cleanup completed with {len(errors)} errors:")
                for error in errors:
                    logger.warning(f"  - {error}")

            if killed_count > 0:
                logger.info(f"Terminated {killed_count} existing calendarbot processes")
                # Give a moment for ports to be released
                time.sleep(1.0)

    # Check if port is available
    if not check_port_availability(host, port):
        logger.warning(f"Port {port} is still occupied after cleanup")

        # Try to find and kill the specific process using the port
        port_process = find_process_using_port(port)
        if port_process:
            logger.warning(f"Process using port {port}: {port_process}")
            try:
                logger.info(f"Attempting to terminate process {port_process.pid} using port {port}")
                os.kill(port_process.pid, signal.SIGTERM)
                time.sleep(2.0)

                # Check again
                if not check_port_availability(host, port):
                    logger.warning(f"Port {port} still occupied, trying SIGKILL")
                    os.kill(port_process.pid, signal.SIGKILL)
                    time.sleep(1.0)

            except Exception as e:
                logger.error(f"Failed to kill process using port {port}: {e}")
                return False

    # Final check
    is_available = check_port_availability(host, port)
    if is_available:
        logger.debug(f"Port {port} is now available")
    else:
        logger.error(f"Port {port} is still not available after cleanup")

    return is_available
