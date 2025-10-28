"""Test utilities for handling async operations and timing without sleep statements."""

import asyncio
import threading
from contextlib import contextmanager
from typing import Any, Callable
from unittest.mock import MagicMock, patch


@contextmanager
def mock_sleep():
    """Mock time.sleep to prevent actual sleeping in tests."""
    with patch("time.sleep") as mock:
        mock.return_value = None
        yield mock


@contextmanager
def mock_async_sleep():
    """Mock asyncio.sleep to prevent actual sleeping in async tests."""
    with patch("asyncio.sleep") as mock:
        mock.return_value = asyncio.Future()
        mock.return_value.set_result(None)
        yield mock


async def wait_for_condition(
    condition: Callable[[], bool], timeout: float = 1.0, interval: float = 0.01
) -> bool:
    """
    Wait for a condition to become true without using sleep.

    Args:
        condition: Callable that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Check interval in seconds (uses asyncio.sleep)

    Returns:
        True if condition was met, False if timeout
    """
    start = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start < timeout:
        if condition():
            return True
        await asyncio.sleep(interval)
    return False


def wait_for_thread_completion(threads: list[threading.Thread], timeout: float = 1.0) -> bool:
    """
    Wait for threads to complete without blocking.

    Args:
        threads: List of threads to wait for
        timeout: Maximum time to wait

    Returns:
        True if all threads completed, False if timeout
    """
    for thread in threads:
        thread.join(timeout=timeout / len(threads))
        if thread.is_alive():
            return False
    return True


class AsyncEventWaiter:
    """Helper for waiting on events in async tests."""

    def __init__(self):
        self.event = asyncio.Event()

    async def wait(self, timeout: float = 1.0) -> bool:
        """Wait for event with timeout."""
        try:
            await asyncio.wait_for(self.event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    def set(self):
        """Set the event."""
        self.event.set()

    def clear(self):
        """Clear the event."""
        self.event.clear()


class MockTimer:
    """Mock timer for testing time-based operations."""

    def __init__(self, auto_advance: bool = True):
        self.current_time = 0.0
        self.auto_advance = auto_advance
        self.advance_amount = 0.1

    def time(self) -> float:
        """Get current mock time."""
        if self.auto_advance:
            self.current_time += self.advance_amount
        return self.current_time

    def advance(self, seconds: float):
        """Manually advance the mock time."""
        self.current_time += seconds

    @contextmanager
    def patch_time(self):
        """Context manager to patch time.time with mock."""
        with patch("time.time", side_effect=self.time):
            yield self


def create_async_mock(return_value: Any = None) -> MagicMock:
    """Create an async mock function."""
    mock = MagicMock()

    async def async_func(*args, **kwargs):
        return return_value

    mock.side_effect = async_func
    return mock


class ThreadSafeCounter:
    """Thread-safe counter for testing concurrent operations."""

    def __init__(self):
        self.value = 0
        self.lock = threading.Lock()

    def increment(self):
        """Increment counter thread-safely."""
        with self.lock:
            self.value += 1

    def get(self) -> int:
        """Get current value thread-safely."""
        with self.lock:
            return self.value


def run_async_test(coro, timeout: float = 5.0):
    """
    Run an async test with timeout.

    Args:
        coro: Coroutine to run
        timeout: Maximum execution time

    Returns:
        Result of the coroutine
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
    finally:
        loop.close()
