"""Browser-specific test configuration for pytest integration."""

import pytest

try:
    from pyppeteer import launch

    PYPPETEER_AVAILABLE = True
except ImportError:
    PYPPETEER_AVAILABLE = False


# Skip all browser tests if pyppeteer is not available
pytestmark = pytest.mark.skipif(
    not PYPPETEER_AVAILABLE, reason="pyppeteer not available for browser tests"
)


def pytest_configure(config):
    """Configure pytest for browser tests."""
    config.addinivalue_line("markers", "browser: mark test as a browser automation test")
    config.addinivalue_line("markers", "smoke: mark test as a smoke test for basic functionality")
