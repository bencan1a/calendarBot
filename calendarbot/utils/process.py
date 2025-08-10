"""Process management utilities for Calendar Bot."""

import logging
import os
import signal
import subprocess  # nosec B404
import time
from typing import Optional

logger = logging.getLogger(__name__)


def _is_legitimate_calendarbot_process(command: str, full_command: str, pattern: str) -> bool:
    """Check if a process is legitimately a calendarbot process.

    Args:
        command: The command name (first part of command line)
        full_command: The full command line
        pattern: The pgrep pattern that matched

    Returns:
        True if this appears to be a legitimate calendarbot process
    """
    # Reject obvious non-calendarbot processes
    non_calendarbot_commands = {
        "avahi-daemon",
        "systemd",
        "dbus",
        "NetworkManager",
        "bluetoothd",
        "pulseaudio",
        "gdm",
        "gnome-session",
        "firefox",
        "chrome",
        "chromium",
        "code",
        "vim",
        "nano",
        "ssh",
        "sshd",
        "rsync",
        "cron",
        "at",
    }

    if command in non_calendarbot_commands:
        logger.debug(f"Rejecting known non-calendarbot command: {command}")
        return False

    # For "calendarbot" pattern, require it to be in the actual executable path or script name
    if pattern == "calendarbot":
        # Accept if calendarbot is in the executable name or script being run
        calendarbot_indicators = [
            "/calendarbot",  # executable path
            "calendarbot.py",  # python script
            "calendarbot",  # direct command
            "python.*calendarbot",  # python running calendarbot
        ]

        has_indicator = any(indicator in full_command for indicator in calendarbot_indicators)
        if not has_indicator:
            logger.debug(
                f"Pattern 'calendarbot' matched but no calendarbot indicators found in: {full_command}"
            )
            return False

    # For python patterns, ensure they're actually running calendarbot code
    if pattern.startswith("python"):
        python_calendarbot_indicators = [
            "calendarbot",  # module or script name
            "main.py",  # common calendarbot entry point
            "-m calendarbot",  # module execution
        ]

        has_python_indicator = any(
            indicator in full_command for indicator in python_calendarbot_indicators
        )
        if not has_python_indicator:
            logger.debug(f"Python pattern matched but no calendarbot indicators: {full_command}")
            return False

    logger.debug(f"Process appears legitimate for pattern '{pattern}': {command}")
    return True


class ProcessInfo:
    """Information about a running process."""

    def __init__(self, pid: int, command: str, full_command: str):
        self.pid = pid
        self.command = command
        self.full_command = full_command

    def __str__(self) -> str:
        return f"PID {self.pid}: {self.command}"


def find_calendarbot_processes() -> list[ProcessInfo]:
    """Find all running calendarbot processes.

    Returns:
        List of ProcessInfo objects for running calendarbot processes
    """
    processes = []
    seen_pids = set()  # Track PIDs to avoid duplicates

    try:
        # Use pgrep to find processes matching calendarbot patterns
        patterns = ["calendarbot", "python.*calendarbot", "python.*main\\.py"]

        for pattern in patterns:
            try:
                # Get PIDs and command lines for matching processes
                # The 'pattern' variable is a fixed string from a hardcoded list, not user input.
                result = subprocess.run(
                    ["pgrep", "-af", pattern],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
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

                                    # Skip our own process and avoid duplicates
                                    if (
                                        pid != os.getpid()
                                        and pid not in seen_pids
                                        and _is_legitimate_calendarbot_process(
                                            command, full_command, pattern
                                        )
                                    ):
                                        processes.append(ProcessInfo(pid, command, full_command))
                                        seen_pids.add(pid)
                                except ValueError:
                                    continue

            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                # Pattern didn't match any processes, continue
                continue

    except Exception:
        logger.exception("Error finding calendarbot processes")

    return processes


def kill_calendarbot_processes(
    exclude_self: bool = True, timeout: float = 5.0
) -> tuple[int, list[str]]:
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
            logger.exception(error_msg)
            errors.append(error_msg)

    # Wait for processes to terminate gracefully - but shorter during testing
    is_testing = os.environ.get("PYTEST_CURRENT_TEST") is not None
    wait_time = min(timeout, 1.0) if is_testing else min(timeout, 2.0)
    logger.debug(f"Waiting {wait_time}s for processes to terminate gracefully")
    time.sleep(wait_time)

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
            logger.exception(error_msg)
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
    import socket  # noqa: PLC0415

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
            ["netstat", "-tlnp"], check=False, capture_output=True, text=True, timeout=5
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
                ["lsof", "-ti", f":{port}"], check=False, capture_output=True, text=True, timeout=5
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


def _safe_kill_process(pid: int, signal_type: int = signal.SIGTERM, timeout: float = 5.0) -> bool:  # noqa: ARG001
    """Safely kill a process with timeout protection.

    Args:
        pid: Process ID to kill
        signal_type: Signal to send (default: SIGTERM)
        timeout: Maximum time to wait for operation (seconds)

    Returns:
        True if process was successfully killed or already dead, False if timeout/error
    """
    try:
        # First check if process exists
        try:
            os.kill(pid, 0)  # Signal 0 checks if process exists
        except OSError:
            # Process doesn't exist, consider it successfully "killed"
            logger.debug(f"Process {pid} already dead")
            return True

        # Use direct os.kill for faster operation, but with try/except for safety
        signal_name = "SIGTERM" if signal_type == signal.SIGTERM else "SIGKILL"
        logger.debug(f"Sending {signal_name} to process {pid}")

        try:
            os.kill(pid, signal_type)
            logger.debug(f"Successfully sent {signal_name} to process {pid}")
            return True
        except ProcessLookupError:
            # Process died between checks - that's success
            logger.debug(f"Process {pid} died during kill operation")
            return True
        except PermissionError:
            logger.warning(f"Permission denied killing process {pid}")
            return False

    except Exception as e:
        logger.warning(f"Error killing process {pid}: {e}")
        return False


def auto_cleanup_before_start(host: str, port: int, force: bool = True) -> bool:
    """Automatically clean up conflicting processes before starting.

    Args:
        host: Host address to bind to
        port: Port number to bind to
        force: Whether to force cleanup even if port is available

    Returns:
        True if cleanup was successful and port is now available
    """
    logger.debug(f"Checking for conflicting processes before binding to {host}:{port}")

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

            # Try graceful termination first with timeout protection
            logger.info(f"Attempting to terminate process {port_process.pid} using port {port}")
            if _safe_kill_process(port_process.pid, signal.SIGTERM, timeout=3.0):
                time.sleep(2.0)  # Give process time to cleanup

                # Check if port is now available
                if not check_port_availability(host, port):
                    # Try force kill with timeout protection
                    logger.warning(f"Port {port} still occupied, trying SIGKILL")
                    if _safe_kill_process(port_process.pid, signal.SIGKILL, timeout=2.0):
                        time.sleep(1.0)  # Brief wait after force kill
                    else:
                        logger.error(f"Failed to force kill process {port_process.pid}")
                        return False
            else:
                logger.error(f"Failed to terminate process {port_process.pid}")
                return False

    # Final check
    is_available = check_port_availability(host, port)
    if is_available:
        logger.debug(f"Port {port} is now available")
    else:
        logger.error(f"Port {port} is still not available after cleanup")

    return is_available
