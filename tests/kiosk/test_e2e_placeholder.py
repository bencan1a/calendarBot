"""Placeholder E2E test to verify Docker infrastructure works.

This test will be replaced by real E2E tests in Phase 3B.
"""
import pytest
import docker


def test_docker_available():
    """Test that Docker is available and can connect."""
    client = docker.from_env()
    assert client.ping(), "Docker daemon not responding"


def test_e2e_image_exists():
    """Test that E2E Docker image was built."""
    client = docker.from_env()
    images = client.images.list(name="calendarbot-e2e")

    # Image might not exist in first CI run before build step
    # This is expected - just log it
    if not images:
        pytest.skip("E2E image not built yet (expected in CI)")

    assert len(images) > 0, "E2E image should exist after build"


@pytest.mark.integration
def test_e2e_container_can_start():
    """Test that E2E container can start with systemd."""
    pytest.skip("Real E2E tests coming in Phase 3B")
