"""Unit tests for async_utils module."""

import asyncio

import pytest

from calendarbot_lite.core.async_utils import (
    AsyncOrchestrator,
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
async def test_gather_with_timeout_uses_default_timeout():
    """Test gather_with_timeout uses default_timeout when no timeout specified."""
    orch = AsyncOrchestrator(default_timeout=0.3)

    async def slow_operation():
        await asyncio.sleep(2.0)
        return "slow"

    with pytest.raises(AsyncTimeoutError):
        await orch.gather_with_timeout(slow_operation())

    await orch.shutdown()


def test_run_coroutine_from_sync_no_running_loop():
    """Test run_coroutine_from_sync when no event loop is running."""
    orchestrator = AsyncOrchestrator()

    async def operation():
        await asyncio.sleep(0.1)
        return "sync result"

    result = orchestrator.run_coroutine_from_sync(lambda: operation())
    assert result == "sync result"


def test_run_coroutine_from_sync_with_timeout():
    """Test run_coroutine_from_sync with timeout."""
    orchestrator = AsyncOrchestrator()

    async def operation():
        await asyncio.sleep(0.1)
        return "with timeout"

    result = orchestrator.run_coroutine_from_sync(
        lambda: operation(),
        timeout=2.0
    )
    assert result == "with timeout"


@pytest.mark.asyncio
async def test_run_coroutine_from_sync_with_running_loop(orchestrator):
    """Test run_coroutine_from_sync when there's a running event loop.

    This tests the code path where we're in an async context and need
    to run async code via a thread pool with a new event loop.
    """
    async def inner_operation():
        await asyncio.sleep(0.1)
        return "from thread pool"

    # This runs inside an async test, so there's already a running loop
    result = orchestrator.run_coroutine_from_sync(lambda: inner_operation())
    assert result == "from thread pool"


@pytest.mark.asyncio
async def test_shutdown(orchestrator):
    """Test orchestrator shutdown."""
    # Shutdown
    await orchestrator.shutdown()
    # Should complete without error


@pytest.mark.asyncio
async def test_context_manager():
    """Test AsyncOrchestrator as async context manager."""
    async with AsyncOrchestrator(max_workers=2) as orch:
        async def operation():
            return 42

        results = await orch.gather_with_timeout(operation(), timeout=1.0)
        assert results == [42]


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
async def test_orchestrator_initialization_defaults():
    """Test default values for AsyncOrchestrator."""
    orch = AsyncOrchestrator()
    assert orch.max_workers == 4
    assert orch.default_timeout == 30.0
    await orch.shutdown()


@pytest.mark.asyncio
async def test_orchestrator_initialization_custom():
    """Test custom values for AsyncOrchestrator."""
    orch = AsyncOrchestrator(max_workers=8, default_timeout=60.0)
    assert orch.max_workers == 8
    assert orch.default_timeout == 60.0
    await orch.shutdown()
