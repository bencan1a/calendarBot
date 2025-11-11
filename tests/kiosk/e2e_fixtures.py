"""Pytest fixtures for CalendarBot Kiosk E2E testing.

Provides fixtures for managing Docker containers with systemd support.
"""

import pytest
import docker
import time
from pathlib import Path
from typing import Generator, Any
import logging

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def docker_client() -> Generator[docker.DockerClient, None, None]:
    """Docker client for managing containers.

    Yields:
        docker.DockerClient: Configured Docker client

    Raises:
        docker.errors.DockerException: If Docker daemon is not available
    """
    client = docker.from_env()
    try:
        # Verify Docker is accessible
        client.ping()
        yield client
    finally:
        client.close()


@pytest.fixture(scope="module")
def e2e_image(docker_client: docker.DockerClient) -> str:
    """Build E2E image once per test module.

    Builds the CalendarBot E2E test image if it doesn't exist or needs updating.

    Args:
        docker_client: Docker client fixture

    Returns:
        str: Image name "calendarbot-e2e:latest"

    Raises:
        docker.errors.BuildError: If image build fails
    """
    image_name = "calendarbot-e2e:latest"
    context_path = Path(__file__).parent.parent.parent  # Repository root
    dockerfile_path = "tests/kiosk/Dockerfile.e2e"

    logger.info(f"Building E2E image: {image_name}")
    logger.info(f"Build context: {context_path}")
    logger.info(f"Dockerfile: {dockerfile_path}")

    try:
        # Build image
        image, build_logs = docker_client.images.build(
            path=str(context_path),
            dockerfile=dockerfile_path,
            tag=image_name,
            rm=True,  # Remove intermediate containers
            forcerm=True,  # Always remove intermediate containers
        )

        # Log build output
        for log in build_logs:
            if 'stream' in log:
                logger.debug(log['stream'].strip())

        logger.info(f"Successfully built image: {image_name}")
        return image_name

    except docker.errors.BuildError as e:
        logger.error(f"Failed to build image: {e}")
        raise


@pytest.fixture(scope="function")
def e2e_container(docker_client: docker.DockerClient, e2e_image: str) -> Generator[Any, None, None]:
    """Create fresh E2E container for each test.

    Creates a new container with systemd support, waits for systemd to be ready,
    and cleans up after the test completes.

    Args:
        docker_client: Docker client fixture
        e2e_image: E2E image name fixture

    Yields:
        docker.models.containers.Container: Running container with systemd ready

    Raises:
        docker.errors.ContainerError: If container fails to start
        TimeoutError: If systemd does not become ready in time
    """
    container = None

    try:
        # Create container with workspace volume mount
        # Mount workspace so container can access installer and code
        workspace_path = Path(__file__).parent.parent.parent
        logger.info(f"Mounting workspace: {workspace_path} -> /workspace")

        container = docker_client.containers.create(
            image=e2e_image,
            name=f"calendarbot-e2e-test-{int(time.time())}",
            privileged=True,
            environment={
                "CALENDARBOT_E2E_TEST": "true",
            },
            volumes={
                str(workspace_path): {
                    "bind": "/workspace",
                    "mode": "rw"
                }
            },
            tmpfs={
                "/run": "",
                "/run/lock": "",
                "/tmp": "",
            },
            detach=True,
        )

        logger.info(f"Created container: {container.name}")

        # Start container
        container.start()
        logger.info(f"Started container: {container.name}")

        # Wait for systemd to be ready
        _wait_for_systemd(container, timeout=30)

        logger.info(f"Container ready: {container.name}")
        yield container

    finally:
        # Cleanup
        if container:
            try:
                logger.info(f"Stopping container: {container.name}")
                container.stop(timeout=10)
            except Exception as e:
                logger.warning(f"Error stopping container: {e}")

            try:
                logger.info(f"Removing container: {container.name}")
                container.remove(force=True)
            except Exception as e:
                logger.warning(f"Error removing container: {e}")


@pytest.fixture
def clean_container(e2e_container: Any) -> Any:
    """Ensure container is clean before test.

    Removes any CalendarBot installation from previous tests to ensure
    a clean state for the current test.

    Args:
        e2e_container: E2E container fixture

    Returns:
        docker.models.containers.Container: Clean container
    """
    logger.info("Cleaning container state")

    # Clean CalendarBot installation (but don't recreate testuser - it's in Dockerfile)
    cleanup_commands = [
        "systemctl stop 'calendarbot-*.service' 2>/dev/null || true",
        "systemctl disable 'calendarbot-*.service' 2>/dev/null || true",
        "rm -f /etc/systemd/system/calendarbot-*.service",
        "rm -f /etc/systemd/system/multi-user.target.wants/calendarbot-*.service",
        "systemctl daemon-reload",
        # Clean testuser home directory (but don't delete user)
        "rm -rf /home/testuser/calendarbot",
        "rm -f /home/testuser/.xinitrc",
        "rm -f /home/testuser/.bash_history",
        # Remove installation artifacts
        "rm -rf /opt/calendarbot",
        "rm -rf /etc/calendarbot-monitor",
        "rm -f /usr/local/bin/calendarbot-*",
        "rm -f /usr/local/bin/log-*.sh",
        "rm -f /usr/local/bin/monitoring-*.sh",
        "rm -f /usr/local/bin/critical-*.sh",
        # Remove nginx config
        "rm -f /etc/nginx/sites-enabled/calendarbot*",
        "rm -f /etc/nginx/sites-available/calendarbot*",
        "systemctl reload nginx 2>/dev/null || true",
        # Remove SSL certificates
        "rm -f /etc/ssl/certs/calendarbot*",
        "rm -f /etc/ssl/private/calendarbot*",
        # Remove sudoers files
        "rm -f /etc/sudoers.d/calendarbot-watchdog",
        "rm -f /etc/sudoers.d/calendarbot-alexa",
    ]

    for cmd in cleanup_commands:
        try:
            exit_code, output = e2e_container.exec_run(
                cmd,
                privileged=True,
            )
            if exit_code != 0 and "|| true" not in cmd:
                logger.warning(f"Cleanup command failed (exit {exit_code}): {cmd}")
                logger.warning(f"Output: {output.decode('utf-8', errors='replace')}")
        except Exception as e:
            logger.warning(f"Error running cleanup command '{cmd}': {e}")

    logger.info("Container cleanup complete")
    return e2e_container


@pytest.fixture(scope="class")
def progressive_container(docker_client: docker.DockerClient, e2e_image: str) -> Generator[Any, None, None]:
    """Create persistent E2E container for progressive testing.

    This fixture creates a container that persists across all tests in a class,
    allowing progressive installation testing (section 1 → 2 → 3 → 4).

    Args:
        docker_client: Docker client fixture
        e2e_image: E2E image name fixture

    Yields:
        docker.models.containers.Container: Running container with systemd ready

    Raises:
        docker.errors.ContainerError: If container fails to start
        TimeoutError: If systemd does not become ready in time
    """
    container = None

    try:
        # Create container with workspace volume mount
        workspace_path = Path(__file__).parent.parent.parent
        logger.info(f"Creating progressive test container")
        logger.info(f"Mounting workspace: {workspace_path} -> /workspace")

        container = docker_client.containers.create(
            image=e2e_image,
            name=f"calendarbot-e2e-progressive-{int(time.time())}",
            privileged=True,
            environment={
                "CALENDARBOT_E2E_TEST": "true",
            },
            volumes={
                str(workspace_path): {
                    "bind": "/workspace",
                    "mode": "rw"
                }
            },
            tmpfs={
                "/run": "",
                "/run/lock": "",
                "/tmp": "",
            },
            detach=True,
        )

        logger.info(f"Created progressive container: {container.name}")

        # Start container
        container.start()
        logger.info(f"Started progressive container: {container.name}")

        # Wait for systemd to be ready
        _wait_for_systemd(container, timeout=30)

        logger.info(f"Progressive container ready: {container.name}")
        yield container

    finally:
        # Cleanup
        if container:
            try:
                logger.info(f"Stopping progressive container: {container.name}")
                container.stop(timeout=10)
            except Exception as e:
                logger.warning(f"Error stopping container: {e}")

            try:
                logger.info(f"Removing progressive container: {container.name}")
                container.remove(force=True)
            except Exception as e:
                logger.warning(f"Error removing container: {e}")


def _wait_for_systemd(container: Any, timeout: int = 30) -> None:
    """Wait for systemd to be ready in container.

    Args:
        container: Docker container
        timeout: Maximum time to wait in seconds

    Raises:
        TimeoutError: If systemd does not become ready in time
    """
    start_time = time.time()
    last_error = None

    while time.time() - start_time < timeout:
        try:
            exit_code, output = container.exec_run(
                "systemctl is-system-running --wait",
                privileged=True,
            )

            output_str = output.decode('utf-8', errors='replace').strip()

            # systemd states: initializing, starting, running, degraded, maintenance, stopping
            # We accept: running, degraded (some services failed but system is up)
            if exit_code == 0 or "running" in output_str or "degraded" in output_str:
                logger.info(f"systemd is ready (state: {output_str})")
                return

            last_error = output_str

        except Exception as e:
            last_error = str(e)

        time.sleep(1)

    raise TimeoutError(
        f"systemd did not become ready within {timeout}s. "
        f"Last status: {last_error}"
    )
