"""Centralized async orchestration utilities for CalendarBot Lite.

This module provides consistent patterns for async operations including:
- ThreadPoolExecutor management with proper lifecycle
- Event loop detection and safe execution
- Timeout management with backoff strategies
- Error handling with retry logic
- Semaphore-based concurrency control
- Async context manager utilities

Design Goals:
1. Eliminate scattered ThreadPoolExecutor usage across codebase
2. Provide safe event loop handling for mixed sync/async contexts
3. Centralize timeout and retry configuration
4. Enable consistent error handling and logging patterns
5. Simplify async code with reusable utilities

Usage Example:
    ```python
    from calendarbot_lite.core.async_utils import AsyncOrchestrator

    orchestrator = AsyncOrchestrator(max_workers=4)

    # Run async function with timeout
    result = await orchestrator.run_with_timeout(
        some_async_func(),
        timeout=30.0
    )

    # Run sync function in executor
    result = await orchestrator.run_in_executor(
        some_blocking_func,
        arg1,
        arg2
    )

    # Gather multiple coroutines with timeout
    results = await orchestrator.gather_with_timeout(
        coro1(), coro2(), coro3(),
        timeout=60.0
    )

    # Retry with exponential backoff
    result = await orchestrator.retry_async(
        flaky_async_func,
        max_retries=3,
        backoff=1.0
    )
    ```

Async Patterns Audit (conducted 2025-11-01):

## ThreadPoolExecutor Usage:
1. lite_rrule_expander.py (lines 1018-1031): Creates ThreadPoolExecutor to run
   async code in new event loop when existing loop detected
2. lite_parser.py (lines 390-403): Similar pattern for RRULE expansion

## Async/Await Patterns:
- asyncio.gather() for concurrent operations (fetch_orchestrator.py:67)
- Semaphores for bounded concurrency (RRuleWorkerPool, FetchOrchestrator)
- AsyncIterator for streaming (lite_rrule_expander.py:101)
- Async context managers for locks and semaphores

## Timeout Strategies:
- http_client.py: httpx.Timeout with separate connect/read/write/pool timeouts
  - connect=10.0s, read=30.0s, write=10.0s, pool=30.0s
- RRuleWorkerPool: time budget per RRULE (200ms default)
- No centralized timeout management - handled ad-hoc per operation

## Error Handling:
- http_client.py: Health tracking with error counts and client recreation
- Try/except with logging throughout
- No centralized retry logic - implemented per operation
- Error recording: record_client_error(), record_client_success()

## Concurrency Control:
- asyncio.Semaphore for bounded concurrency
- RRuleWorkerPool: max_concurrency=1 (Pi Zero 2W optimization)
- FetchOrchestrator: fetch_concurrency=2-3 (bounded 1-3)
- No centralized semaphore management

## Common Patterns to Consolidate:
1. Event loop detection with fallback to ThreadPoolExecutor
2. Semaphore-based concurrency limiting
3. Health tracking with error thresholds
4. Timeout management with configurable durations
5. Async streaming with cooperative yields
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AsyncOrchestratorError(Exception):
    """Base exception for AsyncOrchestrator errors."""


class AsyncTimeoutError(AsyncOrchestratorError):
    """Raised when async operation exceeds timeout."""


class AsyncRetryExhaustedError(AsyncOrchestratorError):
    """Raised when retry attempts are exhausted."""


class AsyncOrchestrator:
    """Centralized async operation orchestration with consistent patterns.

    Provides unified interface for:
    - ThreadPoolExecutor lifecycle management
    - Safe event loop detection and execution
    - Timeout management with cancellation
    - Retry logic with exponential backoff
    - Semaphore-based concurrency control
    - Async context manager utilities

    This class consolidates scattered async patterns across the codebase,
    particularly the ThreadPoolExecutor usage in lite_rrule_expander.py
    and lite_parser.py.
    """

    def __init__(
        self,
        max_workers: int = 4,
        default_timeout: float = 30.0,
        enable_health_tracking: bool = True,
    ):
        """Initialize async orchestrator.

        Args:
            max_workers: Maximum number of thread pool workers
            default_timeout: Default timeout for operations in seconds
            enable_health_tracking: Enable health tracking for operations
        """
        self.max_workers = max_workers
        self.default_timeout = default_timeout
        self.enable_health_tracking = enable_health_tracking

        # Lazy initialization of ThreadPoolExecutor (created on first use)
        self._executor: Optional[ThreadPoolExecutor] = None
        self._executor_lock = asyncio.Lock()

        # Health tracking
        self._operation_count = 0
        self._error_count = 0
        self._timeout_count = 0
        self._last_error_time: Optional[float] = None

        logger.debug(
            "AsyncOrchestrator initialized: max_workers=%d, default_timeout=%.1fs, "
            "health_tracking=%s",
            max_workers,
            default_timeout,
            enable_health_tracking,
        )

    async def _get_executor(self) -> ThreadPoolExecutor:
        """Get or create the thread pool executor.

        Returns:
            ThreadPoolExecutor instance
        """
        async with self._executor_lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(
                    max_workers=self.max_workers, thread_name_prefix="AsyncOrch"
                )
                logger.debug("Created ThreadPoolExecutor with %d workers", self.max_workers)
        return self._executor

    def _record_operation(self, success: bool = True, timeout: bool = False) -> None:
        """Record operation metrics for health tracking.

        Args:
            success: Whether operation succeeded
            timeout: Whether operation timed out
        """
        if not self.enable_health_tracking:
            return

        self._operation_count += 1

        if not success:
            self._error_count += 1
            self._last_error_time = time.time()

        if timeout:
            self._timeout_count += 1

    async def run_with_timeout(
        self,
        coro: Any,
        timeout: Optional[float] = None,
        raise_on_timeout: bool = True,
    ) -> Any:
        """Run async coroutine with timeout.

        Args:
            coro: Coroutine to execute
            timeout: Timeout in seconds (uses default if None)
            raise_on_timeout: Whether to raise exception on timeout

        Returns:
            Coroutine result

        Raises:
            AsyncTimeoutError: If timeout occurs and raise_on_timeout=True
        """
        effective_timeout = timeout if timeout is not None else self.default_timeout

        try:
            result = await asyncio.wait_for(coro, timeout=effective_timeout)
            self._record_operation(success=True)
            return result
        except TimeoutError as e:
            self._record_operation(success=False, timeout=True)
            logger.warning("Operation timed out after %.1fs", effective_timeout)
            if raise_on_timeout:
                raise AsyncTimeoutError(
                    f"Operation exceeded timeout of {effective_timeout}s"
                ) from e
            return None

    async def run_in_executor(
        self,
        func: Callable[..., T],
        *args: Any,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> T:
        """Run synchronous function in thread pool executor.

        Args:
            func: Synchronous function to execute
            *args: Positional arguments for function
            timeout: Optional timeout in seconds
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            AsyncTimeoutError: If operation times out
        """
        executor = await self._get_executor()

        try:
            # Wrap function with kwargs if needed
            wrapped_func = (lambda: func(*args, **kwargs)) if kwargs else lambda: func(*args)

            loop = asyncio.get_event_loop()
            coro = loop.run_in_executor(executor, wrapped_func)

            result = await self.run_with_timeout(coro, timeout=timeout)
            self._record_operation(success=True)
            return result
        except Exception:
            self._record_operation(success=False)
            logger.exception("Error running function in executor")
            raise

    async def run_in_new_event_loop(
        self,
        coro_func: Callable[[], Any],
        timeout: Optional[float] = None,
    ) -> Any:
        """Run coroutine in new event loop within separate thread.

        This consolidates the pattern from lite_rrule_expander.py and lite_parser.py
        where async code needs to run when there's already a running event loop.

        Args:
            coro_func: Function that returns a coroutine
            timeout: Optional timeout in seconds

        Returns:
            Coroutine result

        Raises:
            AsyncTimeoutError: If operation times out
        """

        def run_in_new_loop() -> Any:
            """Run coroutine in a new event loop in separate thread."""
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro_func())
            finally:
                new_loop.close()

        return await self.run_in_executor(run_in_new_loop, timeout=timeout)

    async def gather_with_timeout(
        self,
        *coroutines: Any,
        timeout: Optional[float] = None,
        return_exceptions: bool = False,
    ) -> list[Any]:
        """Gather multiple coroutines with timeout.

        Args:
            *coroutines: Coroutines to gather
            timeout: Timeout in seconds
            return_exceptions: Whether to return exceptions instead of raising

        Returns:
            List of results from all coroutines

        Raises:
            AsyncTimeoutError: If timeout occurs
        """
        gather_coro = asyncio.gather(*coroutines, return_exceptions=return_exceptions)

        try:
            results = await self.run_with_timeout(
                gather_coro, timeout=timeout, raise_on_timeout=True
            )
            self._record_operation(success=True)
            return results
        except AsyncTimeoutError:
            # Cancel all pending coroutines
            gather_coro.cancel()
            self._record_operation(success=False, timeout=True)
            raise

    async def retry_async(
        self,
        coro_func: Callable[[], Any],
        max_retries: int = 3,
        backoff: float = 1.0,
        backoff_multiplier: float = 2.0,
        max_backoff: float = 60.0,
        retry_on: Optional[tuple[type[Exception], ...]] = None,
    ) -> Any:
        """Retry async function with exponential backoff.

        Args:
            coro_func: Function that returns a coroutine
            max_retries: Maximum number of retry attempts
            backoff: Initial backoff delay in seconds
            backoff_multiplier: Multiplier for exponential backoff
            max_backoff: Maximum backoff delay in seconds
            retry_on: Tuple of exception types to retry on (None = retry all)

        Returns:
            Function result

        Raises:
            AsyncRetryExhaustedError: If all retries are exhausted
        """
        last_exception = None
        current_backoff = backoff

        for attempt in range(max_retries + 1):
            try:
                result = await coro_func()
                if attempt > 0:
                    logger.info(
                        "Operation succeeded on attempt %d/%d", attempt + 1, max_retries + 1
                    )
                self._record_operation(success=True)
                return result
            except Exception as e:
                last_exception = e

                # Check if we should retry this exception type
                if retry_on is not None and not isinstance(e, retry_on):
                    logger.debug("Not retrying exception type %s", type(e).__name__)
                    raise

                # Check if we have retries left
                if attempt >= max_retries:
                    self._record_operation(success=False)
                    logger.exception("Retry exhausted after %d attempts", max_retries + 1)
                    break

                # Log and wait before retry
                logger.warning(
                    "Attempt %d/%d failed: %s. Retrying in %.1fs...",
                    attempt + 1,
                    max_retries + 1,
                    e,
                    current_backoff,
                )

                await asyncio.sleep(current_backoff)

                # Exponential backoff with max cap
                current_backoff = min(current_backoff * backoff_multiplier, max_backoff)

        # All retries exhausted
        raise AsyncRetryExhaustedError(
            f"Operation failed after {max_retries + 1} attempts"
        ) from last_exception

    @asynccontextmanager
    async def bounded_concurrency(self, max_concurrent: int) -> AsyncIterator[asyncio.Semaphore]:
        """Create async context manager with semaphore for bounded concurrency.

        Args:
            max_concurrent: Maximum number of concurrent operations

        Yields:
            Semaphore for concurrency control

        Example:
            ```python
            async with orchestrator.bounded_concurrency(3) as sem:
                async with sem:
                    await some_operation()
            ```
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        logger.debug("Created semaphore with max_concurrent=%d", max_concurrent)
        try:
            yield semaphore
        finally:
            logger.debug("Released semaphore")

    def run_coroutine_from_sync(
        self,
        coro_func: Callable[[], Any],
        timeout: Optional[float] = None,
    ) -> Any:
        """Run async coroutine from synchronous context.

        This is a SYNCHRONOUS method that safely executes async code whether
        or not there's already a running event loop.

        Automatically detects if there's a running event loop and chooses
        the appropriate execution strategy:
        - If no loop: Use asyncio.run()
        - If loop exists: Run in new loop within thread pool

        This consolidates the pattern from lite_rrule_expander.py:1018-1038
        and lite_parser.py:390-410.

        Args:
            coro_func: Function that returns a coroutine
            timeout: Optional timeout in seconds

        Returns:
            Coroutine result

        Example:
            ```python
            def sync_function():
                orchestrator = get_global_orchestrator()

                async def my_async_work():
                    return await some_async_operation()

                result = orchestrator.run_coroutine_from_sync(my_async_work)
                return result
            ```
        """
        try:
            # Check if there's a running event loop
            asyncio.get_running_loop()
            # There's a running loop - need to run in separate thread with new loop
            logger.debug("Detected running event loop - using thread pool")

            def run_in_new_loop() -> Any:
                """Run coroutine in a new event loop in separate thread."""
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    coro = coro_func()
                    if timeout:
                        coro = asyncio.wait_for(coro, timeout=timeout)
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()

            # Use blocking version - this is a sync method
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_in_new_loop)
                return future.result()

        except RuntimeError:
            # No running loop - use asyncio.run() directly
            logger.debug("No running event loop - using asyncio.run()")
            coro = coro_func()
            if timeout:
                coro = asyncio.wait_for(coro, timeout=timeout)
            return asyncio.run(coro)

    async def execute_safe_from_sync_context(
        self,
        coro_func: Callable[[], Any],
        timeout: Optional[float] = None,
    ) -> Any:
        """Safely execute async code from async context (deprecated - use run_coroutine_from_sync for sync contexts).

        This async method is kept for backwards compatibility but note:
        - For SYNC contexts: use run_coroutine_from_sync() instead
        - For ASYNC contexts: just await the coroutine directly

        Args:
            coro_func: Function that returns a coroutine
            timeout: Optional timeout in seconds

        Returns:
            Coroutine result
        """
        try:
            # Check if there's a running event loop
            asyncio.get_running_loop()
            # There's a running loop - use thread pool with new loop
            logger.debug("Detected running event loop - using thread pool")
            return await self.run_in_new_event_loop(coro_func, timeout=timeout)
        except RuntimeError:
            # No running loop - use asyncio.run() directly
            logger.debug("No running event loop - using asyncio.run()")
            coro = coro_func()
            if timeout:
                coro = asyncio.wait_for(coro, timeout=timeout)
            return asyncio.run(coro)

    def get_health_stats(self) -> dict[str, Any]:
        """Get health statistics for monitoring.

        Returns:
            Dictionary with health metrics
        """
        if not self.enable_health_tracking:
            return {"health_tracking": "disabled"}

        error_rate = self._error_count / self._operation_count if self._operation_count > 0 else 0.0

        timeout_rate = (
            self._timeout_count / self._operation_count if self._operation_count > 0 else 0.0
        )

        return {
            "operation_count": self._operation_count,
            "error_count": self._error_count,
            "timeout_count": self._timeout_count,
            "error_rate": error_rate,
            "timeout_rate": timeout_rate,
            "last_error_time": self._last_error_time,
        }

    async def shutdown(self) -> None:
        """Shutdown orchestrator and clean up resources.

        Should be called during application shutdown to properly
        clean up thread pool executor.
        """
        async with self._executor_lock:
            if self._executor is not None:
                logger.debug("Shutting down ThreadPoolExecutor")
                self._executor.shutdown(wait=True)
                self._executor = None
                logger.info("AsyncOrchestrator shutdown complete")

    async def __aenter__(self) -> "AsyncOrchestrator":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.shutdown()


# Global orchestrator instance for application-wide use
_global_orchestrator: Optional[AsyncOrchestrator] = None


def get_global_orchestrator(
    max_workers: int = 4,
    default_timeout: float = 30.0,
) -> AsyncOrchestrator:
    """Get or create the global AsyncOrchestrator instance.

    Args:
        max_workers: Maximum thread pool workers
        default_timeout: Default timeout for operations

    Returns:
        Global AsyncOrchestrator instance
    """
    global _global_orchestrator
    if _global_orchestrator is None:
        _global_orchestrator = AsyncOrchestrator(
            max_workers=max_workers,
            default_timeout=default_timeout,
        )
        logger.debug("Created global AsyncOrchestrator")
    return _global_orchestrator


async def shutdown_global_orchestrator() -> None:
    """Shutdown the global orchestrator instance."""
    global _global_orchestrator
    if _global_orchestrator is not None:
        await _global_orchestrator.shutdown()
        _global_orchestrator = None
        logger.debug("Shutdown global AsyncOrchestrator")
