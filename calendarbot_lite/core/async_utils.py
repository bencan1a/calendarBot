"""Centralized async orchestration utilities for CalendarBot Lite.

This module provides consistent patterns for async operations including:
- ThreadPoolExecutor management with proper lifecycle
- Event loop detection and safe execution
- Timeout management with cancellation
- Concurrent async operations with gather

Design Goals:
1. Eliminate scattered ThreadPoolExecutor usage across codebase
2. Provide safe event loop handling for mixed sync/async contexts
3. Centralize timeout configuration
4. Enable consistent error handling and logging patterns

Usage Example:
    ```python
    from calendarbot_lite.core.async_utils import get_global_orchestrator

    # Run async from sync context
    orchestrator = get_global_orchestrator()
    result = orchestrator.run_coroutine_from_sync(my_async_func)

    # Gather with timeout (in async context)
    results = await orchestrator.gather_with_timeout(
        coro1(), coro2(), coro3(),
        timeout=60.0
    )
    ```
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AsyncOrchestratorError(Exception):
    """Base exception for AsyncOrchestrator errors."""


class AsyncTimeoutError(AsyncOrchestratorError):
    """Raised when async operation exceeds timeout."""


class AsyncOrchestrator:
    """Centralized async operation orchestration with consistent patterns.

    Provides unified interface for:
    - Safe event loop detection and execution
    - Timeout management with cancellation
    - Concurrent async operations with gather

    This class consolidates scattered async patterns across the codebase,
    particularly the ThreadPoolExecutor usage in lite_rrule_expander.py
    and lite_parser.py.
    """

    def __init__(
        self,
        max_workers: int = 4,
        default_timeout: float = 30.0,
    ):
        """Initialize async orchestrator.

        Args:
            max_workers: Maximum number of thread pool workers
            default_timeout: Default timeout for operations in seconds
        """
        self.max_workers = max_workers
        self.default_timeout = default_timeout

        logger.debug(
            "AsyncOrchestrator initialized: max_workers=%d, default_timeout=%.1fs",
            max_workers,
            default_timeout,
        )

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
        effective_timeout = timeout if timeout is not None else self.default_timeout
        gather_coro = asyncio.gather(*coroutines, return_exceptions=return_exceptions)

        try:
            return await asyncio.wait_for(gather_coro, timeout=effective_timeout)
        except TimeoutError as e:
            # Cancel all pending coroutines
            gather_coro.cancel()
            logger.warning("gather_with_timeout exceeded %.1fs", effective_timeout)
            raise AsyncTimeoutError(
                f"Operation exceeded timeout of {effective_timeout}s"
            ) from e

    def run_coroutine_from_sync(
        self,
        coro_func: Any,
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
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_in_new_loop)
                return future.result()

        except RuntimeError:
            # No running loop - use asyncio.run() directly
            logger.debug("No running event loop - using asyncio.run()")
            coro = coro_func()
            if timeout:
                coro = asyncio.wait_for(coro, timeout=timeout)
            return asyncio.run(coro)

    async def shutdown(self) -> None:
        """Shutdown orchestrator and clean up resources.

        Should be called during application shutdown to properly
        clean up any resources.
        """
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
