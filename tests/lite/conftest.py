from types import SimpleNamespace
from typing import Any, AsyncIterator, Generator
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
def reset_worker_pool() -> Generator[None, Any, None]:
    """Reset global worker pool between tests to prevent state pollution.

    The global _worker_pool singleton in lite_rrule_expander can carry state
    from one test to another. This fixture ensures each test gets a fresh
    worker pool by resetting it to None after each test.
    """
    yield
    # Reset global worker pool after each test
    import calendarbot_lite.lite_rrule_expander
    calendarbot_lite.lite_rrule_expander._worker_pool = None


@pytest.fixture(autouse=True)
def clean_test_environment(monkeypatch: Any) -> Generator[None, Any, None]:
    """Ensure test environment variables are cleaned between tests.

    Some tests set CALENDARBOT_TEST_TIME to freeze time for recurring event
    expansion. This fixture ensures the environment variable is cleared before
    and after each test to prevent pollution between tests.
    """
    # Clear any lingering test time before the test
    monkeypatch.delenv("CALENDARBOT_TEST_TIME", raising=False)
    yield
    # Clear again after the test
    monkeypatch.delenv("CALENDARBOT_TEST_TIME", raising=False)


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