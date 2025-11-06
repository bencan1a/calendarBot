"""Pytest configuration for kiosk E2E tests.

This file makes fixtures available to all tests in the kiosk directory.
"""

# Import all fixtures from e2e_fixtures
from tests.kiosk.e2e_fixtures import (
    docker_client,
    e2e_image,
    e2e_container,
    clean_container,
)

# Make fixtures available (they're already defined as fixtures in e2e_fixtures.py)
__all__ = [
    "docker_client",
    "e2e_image",
    "e2e_container",
    "clean_container",
]
