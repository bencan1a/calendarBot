"""Test RRuleWorkerPool thread safety with concurrent event loops.

Tests for issue #48: Worker Pool Thread Safety Issues
"""

import asyncio
import concurrent.futures
import pytest
from datetime import datetime, timedelta, UTC

from calendarbot_lite.lite_rrule_expander import (
    RRuleWorkerPool,
    get_worker_pool,
    RRuleExpanderConfig,
)
from calendarbot_lite.lite_models import LiteCalendarEvent, LiteDateTimeInfo, LiteEventStatus


class MockSettings:
    """Mock settings for testing."""

    def __init__(self):
        self.rrule_worker_concurrency = 1
        self.max_occurrences_per_rule = 10
        self.expansion_days_window = 30
        self.expansion_time_budget_ms_per_rule = 1000
        self.expansion_yield_frequency = 5


def create_test_event(event_id: str = "test-event") -> LiteCalendarEvent:
    """Create a test recurring event that starts yesterday to ensure it's in the expansion window."""
    now = datetime.now(UTC)
    # Start yesterday to ensure first occurrence is clearly in expansion window
    start_time = now - timedelta(days=1)
    return LiteCalendarEvent(
        id=event_id,
        subject="Test Weekly Meeting",
        body_preview="Test event",
        start=LiteDateTimeInfo(
            date_time=start_time,
            time_zone="UTC",
        ),
        end=LiteDateTimeInfo(
            date_time=start_time + timedelta(hours=1),
            time_zone="UTC",
        ),
        is_all_day=False,
        show_as=LiteEventStatus.BUSY,
        is_cancelled=False,
        is_organizer=True,
        location=None,
        is_online_meeting=False,
        online_meeting_url=None,
        is_recurring=True,
        is_expanded_instance=False,
        rrule_master_uid=None,
        last_modified_date_time=now,
    )


@pytest.mark.asyncio
async def test_worker_pool_creates_per_loop_semaphores():
    """Test that worker pool creates separate semaphores for each event loop."""
    settings = MockSettings()
    pool = RRuleWorkerPool(settings)

    # Get semaphore from current loop
    sem1 = pool._get_semaphore()
    loop1_id = id(asyncio.get_running_loop())

    # Verify semaphore was created for this loop
    assert loop1_id in pool._semaphores
    assert pool._semaphores[loop1_id] is sem1

    # Getting it again should return the same semaphore
    sem1_again = pool._get_semaphore()
    assert sem1_again is sem1


@pytest.mark.asyncio
async def test_concurrent_expansions_same_loop():
    """Test concurrent RRULE expansions within the same event loop."""
    settings = MockSettings()
    pool = RRuleWorkerPool(settings)

    event1 = create_test_event("event-1")
    event2 = create_test_event("event-2")
    rrule = "FREQ=DAILY;COUNT=5"

    # Run two expansions concurrently in same loop
    async def expand_and_collect(event):
        results = []
        async for instance in pool.expand_rrule_stream(event, rrule):
            results.append(instance)
        return results

    results = await asyncio.gather(
        expand_and_collect(event1),
        expand_and_collect(event2),
    )

    # Both should succeed and return instances
    # Note: COUNT=5 but expansion window may filter past occurrences
    assert len(results) == 2
    assert len(results[0]) >= 3  # At least 3 future occurrences
    assert len(results[1]) >= 3  # At least 3 future occurrences
    assert len(results[0]) <= 5  # No more than COUNT
    assert len(results[1]) <= 5  # No more than COUNT


@pytest.mark.asyncio
async def test_concurrent_expansions_different_loops():
    """Test concurrent RRULE expansions from different event loops (thread pool).

    This is the critical test for issue #48 - ensures that semaphores
    don't interfere across different event loops.
    """
    settings = MockSettings()
    # Use global pool to test real-world scenario
    pool = get_worker_pool(settings)

    event1 = create_test_event("event-1")
    event2 = create_test_event("event-2")
    event3 = create_test_event("event-3")
    rrule = "FREQ=DAILY;COUNT=5"

    async def expand_in_new_loop(event, pool_obj):
        """Expand event in a new event loop (simulates concurrent requests)."""
        results = []
        async for instance in pool_obj.expand_rrule_stream(event, rrule):
            results.append(instance)
        return results

    def run_in_thread(event):
        """Run async expansion in a new thread with new event loop."""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(expand_in_new_loop(event, pool))
        finally:
            new_loop.close()

    # Run expansions in parallel threads (different event loops)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(run_in_thread, event1),
            executor.submit(run_in_thread, event2),
            executor.submit(run_in_thread, event3),
        ]

        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All should succeed without race conditions
    assert len(results) == 3
    for result in results:
        # COUNT=5 but expansion window may filter past occurrences
        assert len(result) >= 3  # At least 3 future occurrences
        assert len(result) <= 5  # No more than COUNT

    # Verify multiple semaphores were created (one per loop)
    # We should have at least 3 loops (one for each thread)
    # Note: might have 4 if pytest's event loop is also counted
    assert len(pool._semaphores) >= 3


@pytest.mark.asyncio
async def test_worker_pool_thread_safe_semaphore_creation():
    """Test that concurrent semaphore creation is thread-safe."""
    settings = MockSettings()
    pool = RRuleWorkerPool(settings)

    created_semaphores = []

    def create_semaphore_in_thread():
        """Create semaphore in new event loop."""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            async def get_sem():
                return pool._get_semaphore()

            sem = new_loop.run_until_complete(get_sem())
            return id(new_loop), sem
        finally:
            new_loop.close()

    # Create semaphores concurrently from multiple threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(create_semaphore_in_thread) for _ in range(5)]
        results = [f.result() for f in futures]

    # Verify we got 5 different event loops and semaphores
    loop_ids = {loop_id for loop_id, _ in results}
    assert len(loop_ids) == 5

    # Verify all semaphores were stored (thread-safe access)
    assert len(pool._semaphores) == 5


@pytest.mark.asyncio
async def test_worker_pool_shutdown_clears_semaphores():
    """Test that shutdown properly clears all semaphores."""
    settings = MockSettings()
    pool = RRuleWorkerPool(settings)

    # Create some semaphores
    _ = pool._get_semaphore()

    # Create semaphores in other loops
    def create_in_thread():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            async def get_sem():
                return pool._get_semaphore()

            return new_loop.run_until_complete(get_sem())
        finally:
            new_loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(create_in_thread) for _ in range(2)]
        [f.result() for f in futures]

    # Should have multiple semaphores
    assert len(pool._semaphores) >= 3

    # Shutdown should clear them all
    await pool.shutdown()
    assert len(pool._semaphores) == 0


@pytest.mark.asyncio
async def test_stress_concurrent_requests():
    """Stress test with many concurrent calendar fetch simulations.

    Simulates the real-world scenario from issue #48 where multiple
    concurrent calendar fetches could interfere with each other.
    """
    settings = MockSettings()
    pool = get_worker_pool(settings)

    # Create multiple test events
    events = [create_test_event(f"event-{i}") for i in range(10)]
    rrule = "FREQ=WEEKLY;COUNT=4"

    def fetch_calendar_simulation(event_list):
        """Simulate a calendar fetch with RRULE expansion in new event loop."""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            async def expand_all():
                all_instances = []
                for event in event_list:
                    async for instance in pool.expand_rrule_stream(event, rrule):
                        all_instances.append(instance)
                return all_instances

            return new_loop.run_until_complete(expand_all())
        finally:
            new_loop.close()

    # Simulate 5 concurrent calendar fetches
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_calendar_simulation, events) for _ in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All fetches should succeed with instances
    assert len(results) == 5
    for result in results:
        # 10 events * ~4 instances each (expansion window may filter some)
        # At minimum we should get 30 instances (10 events * 3 future occurrences)
        assert len(result) >= 30
        assert len(result) <= 40  # No more than 10 events * 4 occurrences

    # Each instance should be properly formed
    for instance in results[0]:
        assert instance.id.startswith("event-")
        assert instance.subject == "Test Weekly Meeting"
        assert instance.is_expanded_instance is True


@pytest.mark.asyncio
async def test_global_pool_reuse():
    """Test that global pool is reused across calls."""
    settings = MockSettings()

    pool1 = get_worker_pool(settings)
    pool2 = get_worker_pool(settings)

    # Should be the same instance
    assert pool1 is pool2


@pytest.mark.asyncio
async def test_semaphore_concurrency_limit():
    """Test that semaphore properly limits concurrency within an event loop."""
    settings = MockSettings()
    settings.rrule_worker_concurrency = 2  # Limit to 2 concurrent
    pool = RRuleWorkerPool(settings)

    event = create_test_event()
    rrule = "FREQ=DAILY;COUNT=3"

    concurrent_count = 0
    max_concurrent = 0
    lock = asyncio.Lock()

    async def track_concurrent_expansion():
        nonlocal concurrent_count, max_concurrent
        semaphore = pool._get_semaphore()

        async with semaphore:
            async with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)

            # Simulate some work
            await asyncio.sleep(0.01)

            async with lock:
                concurrent_count -= 1

    # Try to run 5 concurrent expansions
    await asyncio.gather(*[track_concurrent_expansion() for _ in range(5)])

    # Max concurrent should be limited by semaphore
    assert max_concurrent <= settings.rrule_worker_concurrency
