"""Helper functions for CalendarBot Kiosk E2E testing.

Provides utilities for interacting with Docker containers during E2E tests.
"""

import logging
import time
from typing import Tuple, Optional, List, Any

logger = logging.getLogger(__name__)


def container_file_exists(container: Any, path: str) -> bool:
    """Check if file exists in container.

    Args:
        container: Docker container
        path: Absolute path to file

    Returns:
        bool: True if file exists, False otherwise
    """
    exit_code, _ = container.exec_run(f"test -f {path}")
    return exit_code == 0


def container_dir_exists(container: Any, path: str) -> bool:
    """Check if directory exists in container.

    Args:
        container: Docker container
        path: Absolute path to directory

    Returns:
        bool: True if directory exists, False otherwise
    """
    exit_code, _ = container.exec_run(f"test -d {path}")
    return exit_code == 0


def container_read_file(container: Any, path: str) -> str:
    """Read file contents from container.

    Args:
        container: Docker container
        path: Absolute path to file

    Returns:
        str: File contents

    Raises:
        FileNotFoundError: If file doesn't exist in container
        RuntimeError: If file read fails for other reasons
    """
    # First check if file exists
    if not container_file_exists(container, path):
        raise FileNotFoundError(f"File not found in container: {path}")

    # Read file contents
    exit_code, output = container.exec_run(f"cat {path}")

    if exit_code != 0:
        error_msg = output.decode('utf-8', errors='replace').strip()
        raise RuntimeError(f"Failed to read file {path}: {error_msg}")

    return output.decode('utf-8', errors='replace')


def container_service_enabled(container: Any, service: str) -> bool:
    """Check if systemd service is enabled.

    Args:
        container: Docker container
        service: Service name (e.g., "calendarbot-lite@testuser.service")

    Returns:
        bool: True if service is enabled, False otherwise
    """
    exit_code, output = container.exec_run(
        f"systemctl is-enabled {service}",
        privileged=True,
    )

    # is-enabled returns 0 if enabled, non-zero otherwise
    # Output is typically "enabled", "disabled", "static", etc.
    return exit_code == 0


def container_service_active(container: Any, service: str) -> bool:
    """Check if systemd service is active (running).

    Args:
        container: Docker container
        service: Service name (e.g., "calendarbot-lite@testuser.service")

    Returns:
        bool: True if service is active/running, False otherwise
    """
    exit_code, output = container.exec_run(
        f"systemctl is-active {service}",
        privileged=True,
    )

    # is-active returns 0 if active, non-zero otherwise
    # Output is typically "active", "inactive", "failed", etc.
    return exit_code == 0


def container_service_status(container: Any, service: str) -> dict[str, Any]:
    """Get detailed systemd service status.

    Args:
        container: Docker container
        service: Service name (e.g., "calendarbot-lite@testuser.service")

    Returns:
        dict: Service status information with keys:
            - enabled: bool
            - active: bool
            - status_output: str (full status output)
    """
    enabled = container_service_enabled(container, service)
    active = container_service_active(container, service)

    # Get full status output
    exit_code, output = container.exec_run(
        f"systemctl status {service}",
        privileged=True,
    )
    status_output = output.decode('utf-8', errors='replace')

    return {
        "enabled": enabled,
        "active": active,
        "status_output": status_output,
    }


def prepare_repository_in_container(
    container: Any,
    target_user: str = "testuser",
    target_path: str = "/home/testuser/calendarbot",
) -> None:
    """Copy workspace to target location to simulate existing repo.

    This avoids git clone issues in E2E tests by copying the mounted
    workspace to the expected installation location.

    Args:
        container: Docker container
        target_user: User who should own the repo
        target_path: Where to copy the repository

    Raises:
        RuntimeError: If copy fails
    """
    # Create parent directory
    parent_dir = "/".join(target_path.split("/")[:-1])

    exit_code, output = container.exec_run(
        f"mkdir -p {parent_dir}",
        privileged=True,
    )

    if exit_code != 0:
        raise RuntimeError(f"Failed to create parent directory: {output.decode()}")

    # Copy workspace to target path
    exit_code, output = container.exec_run(
        f"cp -r /workspace {target_path}",
        privileged=True,
    )

    if exit_code != 0:
        raise RuntimeError(f"Failed to copy workspace: {output.decode()}")

    # Set ownership
    exit_code, output = container.exec_run(
        f"chown -R {target_user}:{target_user} {target_path}",
        privileged=True,
    )

    if exit_code != 0:
        raise RuntimeError(f"Failed to set ownership: {output.decode()}")

    # Remove venv if it exists (host venv is not compatible with container)
    venv_path = f"{target_path}/venv"
    exit_code, output = container.exec_run(
        f"rm -rf {venv_path}",
        privileged=True,
    )

    if exit_code != 0:
        raise RuntimeError(f"Failed to remove venv: {output.decode()}")

    # Remove .env file to ensure installer creates fresh one with test config
    env_path = f"{target_path}/.env"
    exit_code, output = container.exec_run(
        f"rm -f {env_path}",
        privileged=True,
    )

    if exit_code != 0:
        raise RuntimeError(f"Failed to remove .env: {output.decode()}")

    logger.info(f"Prepared repository at {target_path} for user {target_user}")


def run_installer_in_container(
    container: Any,
    config_yaml: str,
    extra_args: Optional[List[str]] = None,
    prep_repo: bool = True,
) -> Tuple[int, str, str]:
    """Run install-kiosk.sh in container.

    Args:
        container: Docker container
        config_yaml: YAML config string to write to /tmp/install-config.yaml
        extra_args: Additional args (e.g., ["--update", "--dry-run"])
        prep_repo: If True, copy workspace to target location before install

    Returns:
        tuple: (exit_code, stdout, stderr)

    Raises:
        RuntimeError: If config file cannot be written
    """
    # Prepare repository if requested (simulate existing installation)
    if prep_repo:
        prepare_repository_in_container(container)

    # Write config file to container using heredoc (simple and reliable)
    config_path = "/tmp/install-config.yaml"

    exit_code, output = container.exec_run(
        ["bash", "-c", f"cat > {config_path} <<'EOFCONFIG'\n{config_yaml}\nEOFCONFIG"],
        privileged=True,
    )

    if exit_code != 0:
        error_msg = output.decode('utf-8', errors='replace')
        raise RuntimeError(f"Failed to write config file: {error_msg}")

    # Verify file was written
    if not container_file_exists(container, config_path):
        raise RuntimeError(f"Config file was not created at {config_path}")

    # Build installer command
    installer_path = "/workspace/kiosk/install-kiosk.sh"
    cmd_args = [installer_path, "--config", config_path]

    if extra_args:
        cmd_args.extend(extra_args)

    cmd = " ".join(cmd_args)

    logger.info(f"Running installer: {cmd}")

    # Run installer
    exit_code, output = container.exec_run(
        cmd,
        privileged=True,
        workdir="/workspace/kiosk",
    )

    # Split output into stdout/stderr (best effort - exec_run combines them)
    output_str = output.decode('utf-8', errors='replace')

    # For now, return combined output as stdout, empty stderr
    # (exec_run doesn't separate stdout/stderr)
    return exit_code, output_str, ""


def container_exec(
    container: Any,
    command: str,
    privileged: bool = False,
    user: Optional[str] = None,
    workdir: Optional[str] = None,
) -> Tuple[int, str]:
    """Execute command in container.

    Args:
        container: Docker container
        command: Command to execute
        privileged: Run with elevated privileges
        user: User to run command as (e.g., "testuser")
        workdir: Working directory for command

    Returns:
        tuple: (exit_code, output)
    """
    exec_kwargs: dict[str, Any] = {
        "privileged": privileged,
    }

    if user:
        exec_kwargs["user"] = user

    if workdir:
        exec_kwargs["workdir"] = workdir

    exit_code, output = container.exec_run(command, **exec_kwargs)

    output_str = output.decode('utf-8', errors='replace')

    return exit_code, output_str


def container_get_file_permissions(container: Any, path: str) -> Optional[str]:
    """Get file permissions in symbolic format (e.g., 'rwxr-xr-x').

    Args:
        container: Docker container
        path: Absolute path to file or directory

    Returns:
        str: Permissions in symbolic format, or None if file doesn't exist
    """
    if not container_file_exists(container, path) and not container_dir_exists(container, path):
        return None

    exit_code, output = container.exec_run(f"stat -c %A {path}")

    if exit_code != 0:
        return None

    return output.decode('utf-8', errors='replace').strip()


def container_get_file_owner(container: Any, path: str) -> Optional[Tuple[str, str]]:
    """Get file owner and group.

    Args:
        container: Docker container
        path: Absolute path to file or directory

    Returns:
        tuple: (owner, group) or None if file doesn't exist
    """
    if not container_file_exists(container, path) and not container_dir_exists(container, path):
        return None

    exit_code, output = container.exec_run(f"stat -c '%U %G' {path}")

    if exit_code != 0:
        return None

    parts = output.decode('utf-8', errors='replace').strip().split()
    if len(parts) != 2:
        return None

    return parts[0], parts[1]


def container_wait_for_service(
    container: Any,
    service: str,
    timeout: int = 30,
    check_interval: int = 1,
) -> bool:
    """Wait for systemd service to become active.

    Args:
        container: Docker container
        service: Service name (e.g., "calendarbot-lite@testuser.service")
        timeout: Maximum time to wait in seconds
        check_interval: Time between checks in seconds

    Returns:
        bool: True if service became active, False if timeout
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        if container_service_active(container, service):
            logger.info(f"Service {service} is active")
            return True

        time.sleep(check_interval)

    logger.warning(f"Service {service} did not become active within {timeout}s")
    return False
