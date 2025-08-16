"""
Global Thread Pool Singleton for CalendarBot

This module provides a singleton ThreadPoolExecutor to consolidate thread pool usage
across the CalendarBot application, reducing memory overhead and thread count from
20-30 concurrent threads to 4-6 for Pi Zero 2W deployment optimization.

Key Features:
- Singleton pattern ensuring single global thread pool instance
- Configured with max_workers=4 for resource-constrained environments
- Thread safety with proper locking mechanisms
- Graceful shutdown with cleanup handling
- Timeout support for async-sync bridging operations
"""

import concurrent.futures
import logging
import threading
from collections.abc import Callable
from typing import Any, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class GlobalThreadPool:
    """
    Singleton ThreadPoolExecutor for CalendarBot application.

    Provides centralized thread pool management to reduce memory overhead
    and consolidate thread usage across web server operations.
    """

    _instance: Optional["GlobalThreadPool"] = None
    _lock = threading.Lock()
    _executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
    _is_shutdown = False

    def __new__(cls) -> "GlobalThreadPool":
        """Create or return existing singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the singleton thread pool if not already initialized."""
        if not hasattr(self, "_initialized"):
            with self._lock:
                if not hasattr(self, "_initialized"):
                    self._initialize_executor()
                    self._initialized = True

    def _initialize_executor(self) -> None:
        """Initialize ThreadPoolExecutor with optimization settings."""
        if self._executor is None and not self._is_shutdown:
            self._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=4, thread_name_prefix="calendarbot"
            )
            logger.info("Initialized global thread pool with max_workers=4")

    def submit(
        self, fn: Callable[..., T], *args: Any, **kwargs: Any
    ) -> concurrent.futures.Future[T]:
        """
        Submit a callable to the thread pool.

        Args:
            fn: Callable to execute in thread pool
            *args: Positional arguments for callable
            **kwargs: Keyword arguments for callable

        Returns:
            Future object representing the execution

        Raises:
            RuntimeError: If thread pool is shutdown or unavailable
        """
        if self._is_shutdown or self._executor is None:
            raise RuntimeError("Global thread pool is shutdown or unavailable")

        try:
            return self._executor.submit(fn, *args, **kwargs)
        except Exception:
            logger.exception("Failed to submit task to thread pool")
            raise

    def submit_with_timeout(
        self, fn: Callable[..., T], timeout: float = 5.0, *args: Any, **kwargs: Any
    ) -> T:
        """
        Submit a callable with timeout handling.

        Args:
            fn: Callable to execute in thread pool
            timeout: Maximum time to wait for result (default: 5.0 seconds)
            *args: Positional arguments for callable
            **kwargs: Keyword arguments for callable

        Returns:
            Result of the callable execution

        Raises:
            TimeoutError: If execution exceeds timeout
            RuntimeError: If thread pool is shutdown or unavailable
        """
        future = self.submit(fn, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as e:
            logger.warning(f"Thread pool task timed out after {timeout}s")
            raise TimeoutError(f"Task execution timed out after {timeout} seconds") from e

    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the thread pool gracefully.

        Args:
            wait: Whether to wait for pending tasks to complete
        """
        with self._lock:
            if self._executor is not None and not self._is_shutdown:
                logger.info("Shutting down global thread pool")
                self._executor.shutdown(wait=wait)
                self._is_shutdown = True
                self._executor = None

    @property
    def is_shutdown(self) -> bool:
        """Check if thread pool is shutdown."""
        return self._is_shutdown

    @property
    def max_workers(self) -> int:
        """Get maximum number of worker threads."""
        return 4

    @classmethod
    def reset_singleton(cls) -> None:
        """
        Reset singleton for testing purposes.

        Warning: This method should only be used in testing environments.
        """
        with cls._lock:
            if cls._instance is not None:
                if cls._instance._executor is not None:  # noqa: SLF001
                    cls._instance._executor.shutdown(wait=False)  # noqa: SLF001
                cls._instance = None
            # Reset class-level state for testing
            cls._is_shutdown = False
            cls._executor = None

        # Reinitialize global instance for testing
        global global_thread_pool  # noqa: PLW0603
        global_thread_pool = GlobalThreadPool()


# Global singleton instance
global_thread_pool = GlobalThreadPool()


def run_in_thread_pool(fn: Callable[..., T], *args: Any, timeout: float = 5.0, **kwargs: Any) -> T:
    """
    Convenience function to run a callable in the global thread pool.

    Args:
        fn: Callable to execute in thread pool
        *args: Positional arguments for callable
        timeout: Maximum time to wait for result (default: 5.0 seconds)
        **kwargs: Keyword arguments for callable

    Returns:
        Result of the callable execution

    Raises:
        TimeoutError: If execution exceeds timeout
        RuntimeError: If thread pool is shutdown or unavailable
    """
    return global_thread_pool.submit_with_timeout(fn, timeout, *args, **kwargs)


def shutdown_global_thread_pool(wait: bool = True) -> None:
    """
    Shutdown the global thread pool.

    Args:
        wait: Whether to wait for pending tasks to complete
    """
    global_thread_pool.shutdown(wait=wait)
