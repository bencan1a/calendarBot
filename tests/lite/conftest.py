from types import SimpleNamespace
from typing import Any, AsyncIterator
import pytest

from calendarbot_lite.http_client import close_all_clients

@pytest.fixture
def simple_settings() -> SimpleNamespace:
    """Lightweight settings object used across lite tests.

    Provides a minimal, deterministic configuration used by multiple
    tests in tests/lite/. Keep this fixture small and fast.
    Fields:
      - request_timeout: HTTP read timeout in seconds
      - max_retries: retry attempts for HTTP fetches
      - retry_backoff_factor: multiplier for retry backoff delays
      - user_agent: default User-Agent header used in tests
    """
    return SimpleNamespace(
        request_timeout=30,
        max_retries=3,
        retry_backoff_factor=1.5,
        user_agent="calendarbot-lite-test/1.0",
    )

@pytest.fixture
def test_timezone() -> str:
    """Return a deterministic timezone identifier for tests.

    Using a fixed timezone string avoids host-local timezone differences
    which can make datetime-sensitive tests flaky.
    """
    return "America/Los_Angeles"

@pytest.fixture(autouse=True)
async def cleanup_shared_http_clients() -> AsyncIterator[None]:
    """Autouse async fixture to clean up shared HTTP clients.

    Ensures calendarbot_lite.http_client.close_all_clients() is invoked
    after every test to prevent resource leaks from httpx clients.
    This fixture is intentionally lightweight (no setup) and only runs
    teardown logic after the test completes.
    """
    yield
    await close_all_clients()