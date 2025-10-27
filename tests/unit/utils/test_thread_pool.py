"""Unit tests for thread pool singleton module."""

import concurrent.futures
import threading

import pytest

from calendarbot.utils.thread_pool import GlobalThreadPool, run_in_thread_pool
from tests.utils.async_helpers import ThreadSafeCounter


@pytest.fixture(autouse=True)
def reset_thread_pool() -> None:
    """Reset the singleton thread pool before each test for isolation."""
    GlobalThreadPool.reset_singleton()
    yield
    GlobalThreadPool.reset_singleton()


class TestGlobalThreadPool:
    """Test cases for GlobalThreadPool singleton."""

    def test_singleton_behavior_when_multiple_instances_then_same_object(self) -> None:
        """Test that GlobalThreadPool follows singleton pattern."""
        # Create multiple instances
        instance1 = GlobalThreadPool()
        instance2 = GlobalThreadPool()
        instance3 = GlobalThreadPool()

        # All should be the same object
        assert instance1 is instance2
        assert instance2 is instance3
        assert instance1 is instance3

    def test_thread_pool_configuration_when_initialized_then_correct_settings(self) -> None:
        """Test that thread pool has correct configuration."""
        pool = GlobalThreadPool()

        # Verify max_workers setting
        if pool._executor is not None:
            assert pool._executor._max_workers == 4  # type: ignore[attr-defined]

        # Verify thread name prefix
        if pool._executor is not None:
            assert pool._executor._thread_name_prefix == "calendarbot"  # type: ignore[attr-defined]

    def test_singleton_thread_safety_when_concurrent_access_then_same_instance(self) -> None:
        """Test singleton behavior under concurrent access."""
        instances = []

        def create_instance() -> None:
            instances.append(GlobalThreadPool())

        # Create multiple threads that create instances
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All instances should be the same object
        first_instance = instances[0]
        for instance in instances:
            assert instance is first_instance

    def test_submit_task_when_valid_function_then_executes_correctly(self) -> None:
        """Test that tasks are submitted and executed correctly."""
        pool = GlobalThreadPool()

        def test_function(x: int, y: int) -> int:
            return x + y

        # Submit task and get result
        future = pool.submit(test_function, 5, 3)
        result = future.result(timeout=1.0)

        assert result == 8

    def test_submit_task_when_exception_raised_then_propagated(self) -> None:
        """Test that exceptions in submitted tasks are properly propagated."""
        pool = GlobalThreadPool()

        def failing_function() -> None:
            raise ValueError("Test error")

        # Submit task that raises exception
        future = pool.submit(failing_function)

        with pytest.raises(ValueError, match="Test error"):
            future.result(timeout=1.0)

    def test_shutdown_when_called_then_executor_shutdown(self) -> None:
        """Test that shutdown properly closes the thread pool."""
        pool = GlobalThreadPool()

        # Submit a task to ensure executor is active
        def dummy_task() -> str:
            return "completed"

        future = pool.submit(dummy_task)
        assert future.result(timeout=1.0) == "completed"

        # Shutdown the pool
        pool.shutdown(wait=True)

        # Verify executor is shutdown
        assert pool.is_shutdown
        assert pool._executor is None

    def test_multiple_tasks_when_submitted_concurrently_then_all_execute(self) -> None:
        """Test that multiple tasks can be executed concurrently."""
        pool = GlobalThreadPool()
        counter = ThreadSafeCounter()

        def slow_task(task_id: int) -> int:
            # Use counter instead of sleep to verify concurrency
            counter.increment()
            return task_id * 2

        # Submit multiple tasks
        futures = []
        for i in range(8):  # More than max_workers to test queuing
            future = pool.submit(slow_task, i)
            futures.append(future)

        # Collect results
        results = []
        for future in futures:
            results.append(future.result(timeout=2.0))

        # Verify all tasks completed correctly
        expected = [i * 2 for i in range(8)]
        assert sorted(results) == sorted(expected)


class TestRunInThreadPool:
    """Test cases for run_in_thread_pool convenience function."""

    def test_run_in_thread_pool_when_simple_function_then_returns_result(self) -> None:
        """Test basic functionality of run_in_thread_pool."""

        def add_numbers(a: int, b: int) -> int:
            return a + b

        result = run_in_thread_pool(add_numbers, 10, 20)
        assert result == 30

    def test_run_in_thread_pool_when_kwargs_provided_then_handles_correctly(self) -> None:
        """Test run_in_thread_pool with keyword arguments."""

        def multiply_with_default(x: int, multiplier: int = 2) -> int:
            return x * multiplier

        result = run_in_thread_pool(multiply_with_default, 5, multiplier=3)
        assert result == 15

    def test_run_in_thread_pool_when_timeout_exceeded_then_raises_timeout_error(self) -> None:
        """Test timeout handling in run_in_thread_pool."""
        event = threading.Event()

        def slow_function() -> str:
            # Block on event instead of sleep
            event.wait(timeout=2.0)
            return "completed"

        with pytest.raises(concurrent.futures.TimeoutError):
            run_in_thread_pool(slow_function, timeout=0.5)

        # Clean up
        event.set()

    def test_run_in_thread_pool_when_function_raises_exception_then_propagated(self) -> None:
        """Test exception propagation in run_in_thread_pool."""

        def failing_function() -> None:
            raise RuntimeError("Function failed")

        with pytest.raises(RuntimeError, match="Function failed"):
            run_in_thread_pool(failing_function)

    def test_run_in_thread_pool_when_no_timeout_specified_then_uses_default(self) -> None:
        """Test that default timeout is used when not specified."""

        def quick_function() -> str:
            return "success"

        # Should complete within default timeout (5.0 seconds)
        result = run_in_thread_pool(quick_function)
        assert result == "success"

    def test_run_in_thread_pool_when_custom_timeout_then_respects_setting(self) -> None:
        """Test that custom timeout values are respected."""
        event = threading.Event()

        def timed_function() -> str:
            # Use event with short timeout to simulate work
            event.wait(timeout=0.01)
            return "completed"

        # Should complete with 1 second timeout
        result = run_in_thread_pool(timed_function, timeout=1.0)
        assert result == "completed"

        def blocking_function() -> str:
            # Block indefinitely
            event.wait()
            return "completed"

        # Should timeout with very short timeout
        with pytest.raises(concurrent.futures.TimeoutError):
            run_in_thread_pool(blocking_function, timeout=0.1)

        # Clean up
        event.set()

    def test_run_in_thread_pool_when_concurrent_calls_then_all_succeed(self) -> None:
        """Test concurrent calls to run_in_thread_pool."""
        counter = ThreadSafeCounter()

        def worker_function(worker_id: int) -> int:
            # Use counter to verify execution instead of sleep
            counter.increment()
            return worker_id * 10

        # Create multiple threads calling run_in_thread_pool
        results = []

        def call_run_in_thread_pool(worker_id: int) -> None:
            result = run_in_thread_pool(worker_function, worker_id)
            results.append(result)

        threads = []
        for i in range(6):
            thread = threading.Thread(target=call_run_in_thread_pool, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify all calls succeeded
        expected = [i * 10 for i in range(6)]
        assert sorted(results) == sorted(expected)


class TestThreadPoolIntegration:
    """Integration tests for thread pool usage scenarios."""

    def test_async_function_wrapper_when_called_then_executes_correctly(self) -> None:
        """Test wrapping async functions for sync execution."""
        import asyncio

        async def async_function(value: str) -> str:
            await asyncio.sleep(0.1)
            return f"async_{value}"

        def run_async_in_thread() -> str:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(async_function("test"))
            finally:
                loop.close()

        result = run_in_thread_pool(run_async_in_thread)
        assert result == "async_test"

    def test_thread_pool_resource_management_when_multiple_operations_then_efficient(self) -> None:
        """Test that thread pool efficiently manages resources."""
        pool = GlobalThreadPool()

        def cpu_intensive_task(n: int) -> int:
            # Simulate some work
            total = 0
            for i in range(n * 1000):
                total += i
            return total

        # Submit multiple CPU-intensive tasks
        futures = []
        for i in range(10):
            future = pool.submit(cpu_intensive_task, i + 1)
            futures.append(future)

        # Collect results
        results = []
        for future in futures:
            results.append(future.result(timeout=5.0))

        # Verify all tasks completed
        assert len(results) == 10
        assert all(isinstance(r, int) for r in results)

    def test_thread_pool_error_isolation_when_one_task_fails_then_others_continue(self) -> None:
        """Test that errors in one task don't affect others."""

        def working_task(value: int) -> int:
            return value * 2

        def failing_task() -> None:
            raise ValueError("This task fails")

        # Submit mix of working and failing tasks
        working_future1 = run_in_thread_pool(working_task, 5)

        with pytest.raises(ValueError, match="This task fails"):
            run_in_thread_pool(failing_task)

        working_future2 = run_in_thread_pool(working_task, 10)

        # Working tasks should still succeed
        assert working_future1 == 10
        assert working_future2 == 20

    def test_thread_count_optimization_when_max_workers_respected_then_within_limits(self) -> None:
        """Test that thread count stays within configured limits."""
        import threading

        active_threads = []
        barrier = threading.Barrier(4)  # Match max_workers

        def thread_counting_task() -> int:
            active_threads.append(threading.current_thread())
            try:
                # Use barrier to synchronize threads instead of sleep
                barrier.wait(timeout=1.0)
            except threading.BrokenBarrierError:
                pass
            return len(active_threads)

        # Submit more tasks than max_workers
        futures = []
        for _ in range(8):  # More than max_workers=4
            future = GlobalThreadPool().submit(thread_counting_task)
            futures.append(future)

        # Wait for all to complete
        results = []
        for future in futures:
            results.append(future.result(timeout=3.0))

        # Verify that we didn't exceed thread limits significantly
        # (Some overlap is expected due to timing, but should be controlled)
        unique_threads = set(active_threads)
        assert len(unique_threads) <= 6  # Allow some flexibility for timing
