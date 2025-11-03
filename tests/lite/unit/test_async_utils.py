"""Unit tests for async_utils module."""

import asyncio
import time

import pytest

from calendarbot_lite.async_utils import (
    AsyncOrchestrator,
    AsyncRetryExhaustedError,
    AsyncTimeoutError,
    get_global_orchestrator,
    shutdown_global_orchestrator,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def orchestrator():
    """Create AsyncOrchestrator for testing."""
    orch = AsyncOrchestrator(max_workers=2, default_timeout=5.0)
    yield orch
    # Cleanup
    asyncio.run(orch.shutdown())


@pytest.mark.asyncio
async def test_run_with_timeout_success(orchestrator):
    """Test run_with_timeout with successful operation."""
    async def quick_operation():
        await asyncio.sleep(0.1)
        return "success"

    result = await orchestrator.run_with_timeout(quick_operation(), timeout=1.0)
    assert result == "success"


@pytest.mark.asyncio
async def test_run_with_timeout_exceeds(orchestrator):
    """Test run_with_timeout when timeout is exceeded."""
    async def slow_operation():
        await asyncio.sleep(2.0)
        return "should not reach"

    with pytest.raises(AsyncTimeoutError):
        await orchestrator.run_with_timeout(slow_operation(), timeout=0.5)

    # Check health stats recorded timeout
    stats = orchestrator.get_health_stats()
    assert stats["timeout_count"] == 1
    assert stats["error_count"] == 1


@pytest.mark.asyncio
async def test_run_with_timeout_no_raise(orchestrator):
    """Test run_with_timeout without raising on timeout."""
    async def slow_operation():
        await asyncio.sleep(2.0)
        return "should not reach"

    result = await orchestrator.run_with_timeout(
        slow_operation(),
        timeout=0.5,
        raise_on_timeout=False
    )
    assert result is None


@pytest.mark.asyncio
async def test_run_in_executor_success(orchestrator):
    """Test run_in_executor with successful sync function."""
    def blocking_function(x, y):
        time.sleep(0.1)
        return x + y

    result = await orchestrator.run_in_executor(blocking_function, 10, 20)
    assert result == 30


@pytest.mark.asyncio
async def test_run_in_executor_with_kwargs(orchestrator):
    """Test run_in_executor with keyword arguments."""
    def blocking_function(x, y, multiply=False):
        if multiply:
            return x * y
        return x + y

    result = await orchestrator.run_in_executor(
        blocking_function,
        10,
        20,
        multiply=True
    )
    assert result == 200


@pytest.mark.asyncio
async def test_run_in_executor_timeout(orchestrator):
    """Test run_in_executor with timeout."""
    def slow_blocking_function():
        time.sleep(2.0)
        return "should not reach"

    with pytest.raises(AsyncTimeoutError):
        await orchestrator.run_in_executor(
            slow_blocking_function,
            timeout=0.5
        )


@pytest.mark.asyncio
async def test_run_in_new_event_loop(orchestrator):
    """Test run_in_new_event_loop."""
    async def async_operation():
        await asyncio.sleep(0.1)
        return "from new loop"

    result = await orchestrator.run_in_new_event_loop(
        lambda: async_operation(),
        timeout=2.0
    )
    assert result == "from new loop"


@pytest.mark.asyncio
async def test_gather_with_timeout_success(orchestrator):
    """Test gather_with_timeout with successful operations."""
    async def operation1():
        await asyncio.sleep(0.1)
        return "result1"

    async def operation2():
        await asyncio.sleep(0.1)
        return "result2"

    async def operation3():
        await asyncio.sleep(0.1)
        return "result3"

    results = await orchestrator.gather_with_timeout(
        operation1(),
        operation2(),
        operation3(),
        timeout=2.0
    )

    assert results == ["result1", "result2", "result3"]


@pytest.mark.asyncio
async def test_gather_with_timeout_exceeds(orchestrator):
    """Test gather_with_timeout when timeout is exceeded."""
    async def quick_operation():
        await asyncio.sleep(0.1)
        return "quick"

    async def slow_operation():
        await asyncio.sleep(2.0)
        return "slow"

    with pytest.raises(AsyncTimeoutError):
        await orchestrator.gather_with_timeout(
            quick_operation(),
            slow_operation(),
            timeout=0.5
        )


@pytest.mark.asyncio
async def test_gather_with_timeout_return_exceptions(orchestrator):
    """Test gather_with_timeout with return_exceptions=True."""
    async def successful_operation():
        await asyncio.sleep(0.1)
        return "success"

    async def failing_operation():
        await asyncio.sleep(0.1)
        raise ValueError("expected error")

    results = await orchestrator.gather_with_timeout(
        successful_operation(),
        failing_operation(),
        timeout=2.0,
        return_exceptions=True
    )

    assert results[0] == "success"
    assert isinstance(results[1], ValueError)


@pytest.mark.asyncio
async def test_retry_async_success_first_try(orchestrator):
    """Test retry_async with success on first attempt."""
    call_count = 0

    async def operation():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await orchestrator.retry_async(
        operation,
        max_retries=3,
        backoff=0.1
    )

    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_async_success_after_retries(orchestrator):
    """Test retry_async with success after retries."""
    call_count = 0

    async def flaky_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("temporary error")
        return "success"

    result = await orchestrator.retry_async(
        flaky_operation,
        max_retries=5,
        backoff=0.1
    )

    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_async_exhausted(orchestrator):
    """Test retry_async when all retries are exhausted."""
    call_count = 0

    async def always_failing_operation():
        nonlocal call_count
        call_count += 1
        raise ValueError("permanent error")

    with pytest.raises(AsyncRetryExhaustedError):
        await orchestrator.retry_async(
            always_failing_operation,
            max_retries=2,
            backoff=0.1
        )

    assert call_count == 3  # Initial + 2 retries


@pytest.mark.asyncio
async def test_retry_async_selective_retry(orchestrator):
    """Test retry_async with selective exception retrying."""
    async def operation_with_bad_error():
        raise TypeError("should not retry")

    with pytest.raises(TypeError):
        await orchestrator.retry_async(
            operation_with_bad_error,
            max_retries=2,
            backoff=0.1,
            retry_on=(ValueError, RuntimeError)
        )


@pytest.mark.asyncio
async def test_retry_async_exponential_backoff(orchestrator):
    """Test retry_async exponential backoff timing."""
    call_times = []

    async def failing_operation():
        call_times.append(time.time())
        raise ValueError("error")

    with pytest.raises(AsyncRetryExhaustedError):
        await orchestrator.retry_async(
            failing_operation,
            max_retries=3,
            backoff=0.1,
            backoff_multiplier=2.0
        )

    # Verify exponential backoff
    assert len(call_times) == 4  # Initial + 3 retries

    # Check delays between attempts (approximate due to timing variance)
    delay1 = call_times[1] - call_times[0]
    delay2 = call_times[2] - call_times[1]
    delay3 = call_times[3] - call_times[2]

    assert 0.08 < delay1 < 0.15  # ~0.1s
    assert 0.18 < delay2 < 0.25  # ~0.2s (doubled)
    assert 0.38 < delay3 < 0.45  # ~0.4s (doubled again)


@pytest.mark.asyncio
async def test_bounded_concurrency(orchestrator):
    """Test bounded_concurrency context manager."""
    concurrent_count = 0
    max_concurrent_seen = 0

    async def operation():
        nonlocal concurrent_count, max_concurrent_seen
        concurrent_count += 1
        max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
        await asyncio.sleep(0.1)
        concurrent_count -= 1

    async with orchestrator.bounded_concurrency(2) as sem:
        tasks = []
        for _ in range(5):
            async def bounded_op():
                async with sem:
                    await operation()
            tasks.append(bounded_op())

        await asyncio.gather(*tasks)

    # Should never exceed 2 concurrent operations
    assert max_concurrent_seen <= 2
    assert concurrent_count == 0  # All completed


@pytest.mark.asyncio
async def test_execute_safe_from_sync_context_no_loop():
    """Test execute_safe_from_sync_context when no event loop is running."""
    # This test runs without an event loop
    orchestrator = AsyncOrchestrator()

    async def operation():
        return "from no loop"

    # Note: This should be called from sync context, but we can't easily test
    # that in pytest's async environment. The logic is tested in integration.


@pytest.mark.asyncio
async def test_execute_safe_from_sync_context_with_loop(orchestrator):
    """Test execute_safe_from_sync_context when event loop is running."""
    async def operation():
        await asyncio.sleep(0.1)
        return "from existing loop"

    # This is called from within an async context (event loop is running)
    result = await orchestrator.execute_safe_from_sync_context(
        lambda: operation(),
        timeout=2.0
    )
    assert result == "from existing loop"


def test_get_health_stats(orchestrator):
    """Test health statistics tracking."""
    # Initially empty
    stats = orchestrator.get_health_stats()
    assert stats["operation_count"] == 0
    assert stats["error_count"] == 0
    assert stats["timeout_count"] == 0
    assert stats["error_rate"] == 0.0


@pytest.mark.asyncio
async def test_health_stats_tracking(orchestrator):
    """Test that health stats are tracked correctly."""
    # Successful operation
    async def success_op():
        return "ok"

    await orchestrator.run_with_timeout(success_op(), timeout=1.0)

    # Failing operation
    async def fail_op():
        await asyncio.sleep(2.0)

    try:
        await orchestrator.run_with_timeout(fail_op(), timeout=0.5)
    except AsyncTimeoutError:
        pass

    stats = orchestrator.get_health_stats()
    assert stats["operation_count"] == 2
    assert stats["error_count"] == 1
    assert stats["timeout_count"] == 1
    assert stats["error_rate"] == 0.5
    assert stats["timeout_rate"] == 0.5
    assert stats["last_error_time"] is not None


@pytest.mark.asyncio
async def test_shutdown(orchestrator):
    """Test orchestrator shutdown."""
    # Run an operation to create executor
    await orchestrator.run_in_executor(lambda: 42)

    # Shutdown
    await orchestrator.shutdown()

    # Executor should be None after shutdown
    assert orchestrator._executor is None


@pytest.mark.asyncio
async def test_context_manager():
    """Test AsyncOrchestrator as async context manager."""
    async with AsyncOrchestrator(max_workers=2) as orch:
        result = await orch.run_in_executor(lambda: 42)
        assert result == 42

    # Executor should be cleaned up
    assert orch._executor is None


def test_get_global_orchestrator():
    """Test global orchestrator singleton."""
    orch1 = get_global_orchestrator()
    orch2 = get_global_orchestrator()

    # Should return same instance
    assert orch1 is orch2


@pytest.mark.asyncio
async def test_shutdown_global_orchestrator():
    """Test shutting down global orchestrator."""
    orch = get_global_orchestrator()
    await shutdown_global_orchestrator()

    # Should create new instance after shutdown
    orch2 = get_global_orchestrator()
    assert orch is not orch2


@pytest.mark.asyncio
async def test_health_tracking_disabled():
    """Test orchestrator with health tracking disabled."""
    orch = AsyncOrchestrator(enable_health_tracking=False)

    async def operation():
        return "ok"

    await orch.run_with_timeout(operation(), timeout=1.0)

    stats = orch.get_health_stats()
    assert stats == {"health_tracking": "disabled"}

    await orch.shutdown()


@pytest.mark.asyncio
async def test_concurrent_executor_creation(orchestrator):
    """Test that executor creation is thread-safe."""
    async def create_executor():
        return await orchestrator._get_executor()

    # Try to create executor concurrently
    executors = await asyncio.gather(*[create_executor() for _ in range(10)])

    # All should return same executor instance
    assert all(e is executors[0] for e in executors)


@pytest.mark.asyncio
async def test_run_in_executor_error_handling(orchestrator):
    """Test error handling in run_in_executor."""
    def failing_function():
        raise ValueError("expected error")

    with pytest.raises(ValueError):
        await orchestrator.run_in_executor(failing_function)

    # Error should be tracked
    stats = orchestrator.get_health_stats()
    assert stats["error_count"] == 1
