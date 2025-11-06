"""Performance tests for deduplication functionality.

These tests verify that deduplication maintains O(n) complexity and meets
performance targets across different scenarios.
"""

import time
from datetime import UTC, datetime, timedelta

import pytest

from calendarbot_lite.calendar.lite_event_merger import LiteEventMerger
from calendarbot_lite.calendar.lite_models import LiteCalendarEvent, LiteDateTimeInfo
from calendarbot_lite.domain.pipeline import ProcessingContext
from calendarbot_lite.domain.pipeline_stages import DeduplicationStage


@pytest.fixture
def event_merger():
    """Create event merger instance."""
    return LiteEventMerger()


@pytest.fixture
def dedupe_stage():
    """Create deduplication stage instance."""
    return DeduplicationStage()


def create_test_event(
    uid: str, subject: str, start: datetime, end: datetime
) -> LiteCalendarEvent:
    """Create a test calendar event."""
    return LiteCalendarEvent(
        id=uid,
        subject=subject,
        start=LiteDateTimeInfo(date_time=start, time_zone="UTC"),
        end=LiteDateTimeInfo(date_time=end, time_zone="UTC"),
        is_recurring=False,
        recurrence_id=None,
    )


def generate_events(count: int, duplicate_rate: float = 0.1) -> list[LiteCalendarEvent]:
    """Generate test events with some duplicates.

    Args:
        count: Number of events to generate
        duplicate_rate: Fraction of events that should be duplicates (0.0-1.0)

    Returns:
        List of calendar events with specified duplicate rate
    """
    events = []
    base_time = datetime(2025, 1, 1, 10, 0, tzinfo=UTC)

    for i in range(count):
        # Create some duplicates based on rate
        # Guard against division by zero and ensure we have previous events
        should_duplicate = (
            duplicate_rate > 0
            and i > 0
            and i % max(1, int(1 / duplicate_rate)) == 0
        )
        if should_duplicate:
            # Duplicate the previous event
            prev = events[-1]
            events.append(
                create_test_event(
                    prev.id, prev.subject, prev.start.date_time, prev.end.date_time
                )
            )
        else:
            # Create unique event
            start = base_time + timedelta(hours=i)
            end = start + timedelta(hours=1)
            events.append(create_test_event(f"event-{i}", f"Event {i}", start, end))

    return events


@pytest.mark.performance
class TestDeduplicationPerformance:
    """Performance tests for event deduplication."""

    def test_deduplicate_events_small_calendar(self, event_merger):
        """Test deduplication performance with small calendar (100 events)."""
        events = generate_events(100, duplicate_rate=0.1)

        start = time.perf_counter()
        result = event_merger.deduplicate_events(events)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should complete very quickly for small calendars
        assert elapsed_ms < 5, f"Deduplication took {elapsed_ms:.2f}ms, expected <5ms"
        assert len(result) < len(events)  # Some duplicates removed

    def test_deduplicate_events_medium_calendar(self, event_merger):
        """Test deduplication performance with medium calendar (500 events)."""
        events = generate_events(500, duplicate_rate=0.1)

        start = time.perf_counter()
        result = event_merger.deduplicate_events(events)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should scale linearly - allow reasonable overhead
        assert elapsed_ms < 15, f"Deduplication took {elapsed_ms:.2f}ms, expected <15ms"
        assert len(result) < len(events)

    def test_deduplicate_events_large_calendar_target(self, event_merger):
        """Test deduplication meets target: <50ms for 1000 events."""
        events = generate_events(1000, duplicate_rate=0.1)

        start = time.perf_counter()
        result = event_merger.deduplicate_events(events)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Primary success metric from issue #XX
        assert (
            elapsed_ms < 50
        ), f"Deduplication took {elapsed_ms:.2f}ms, target is <50ms for 1000 events"

        # Verify correctness
        expected_removed = int(1000 * 0.1)
        actual_removed = len(events) - len(result)
        # Allow some variance due to rounding
        assert (
            abs(actual_removed - expected_removed) <= 10
        ), f"Expected ~{expected_removed} duplicates, got {actual_removed}"

    def test_deduplicate_events_very_large_calendar(self, event_merger):
        """Test deduplication scales to very large calendars (5000 events)."""
        events = generate_events(5000, duplicate_rate=0.1)

        start = time.perf_counter()
        result = event_merger.deduplicate_events(events)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should scale linearly - 5x events should be <5x time
        # If 1000 events takes <50ms, 5000 should take <250ms
        assert (
            elapsed_ms < 250
        ), f"Deduplication took {elapsed_ms:.2f}ms, expected <250ms for 5000 events"
        assert len(result) < len(events)

    def test_deduplicate_linear_complexity(self, event_merger):
        """Verify O(n) complexity by testing scaling behavior.

        This test verifies that doubling the input size roughly doubles the time,
        confirming O(n) rather than O(n²) complexity.
        """
        # Test with two sizes: 1000 and 2000 events
        size_1 = 1000
        size_2 = 2000

        # Measure time for size_1
        events_1 = generate_events(size_1, duplicate_rate=0.1)
        start = time.perf_counter()
        event_merger.deduplicate_events(events_1)
        time_1 = time.perf_counter() - start

        # Measure time for size_2
        events_2 = generate_events(size_2, duplicate_rate=0.1)
        start = time.perf_counter()
        event_merger.deduplicate_events(events_2)
        time_2 = time.perf_counter() - start

        # For O(n) complexity: time_2 / time_1 should be ~2.0
        # For O(n²) complexity: time_2 / time_1 would be ~4.0
        ratio = time_2 / time_1 if time_1 > 0 else 0

        # Allow significant variance (1.5-3.0x) due to system noise, but should not be 4x
        assert (
            1.5 <= ratio <= 3.0
        ), f"Complexity appears worse than O(n): ratio={ratio:.2f} (expected ~2.0)"

    def test_deduplicate_no_duplicates_overhead(self, event_merger):
        """Test performance when there are no duplicates (best case)."""
        events = generate_events(1000, duplicate_rate=0.0)

        start = time.perf_counter()
        result = event_merger.deduplicate_events(events)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # No duplicates - should be fastest case
        assert elapsed_ms < 50, f"Deduplication took {elapsed_ms:.2f}ms"
        assert len(result) == len(events)  # No duplicates removed

    def test_deduplicate_many_duplicates(self, event_merger):
        """Test performance with high duplicate rate (50%)."""
        events = generate_events(1000, duplicate_rate=0.5)

        start = time.perf_counter()
        result = event_merger.deduplicate_events(events)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Even with many duplicates, should meet target
        assert elapsed_ms < 50, f"Deduplication took {elapsed_ms:.2f}ms"
        # Should remove roughly 50% of events
        assert len(result) < len(events) * 0.6


@pytest.mark.performance
@pytest.mark.asyncio
class TestPipelineDeduplicationPerformance:
    """Performance tests for pipeline deduplication stage."""

    async def test_pipeline_dedupe_target(self, dedupe_stage):
        """Test pipeline deduplication meets performance target."""
        events = generate_events(1000, duplicate_rate=0.1)
        context = ProcessingContext()
        context.events = events

        start = time.perf_counter()
        result = await dedupe_stage.process(context)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Pipeline version should also be fast
        assert elapsed_ms < 50, f"Pipeline deduplication took {elapsed_ms:.2f}ms"
        assert result.success
        assert result.events_filtered > 0  # Some duplicates removed

    async def test_pipeline_dedupe_linear_complexity(self, dedupe_stage):
        """Verify pipeline deduplication maintains O(n) complexity."""
        # Test with two sizes
        size_1 = 1000
        size_2 = 2000

        # Measure time for size_1
        events_1 = generate_events(size_1, duplicate_rate=0.1)
        context_1 = ProcessingContext()
        context_1.events = events_1
        start = time.perf_counter()
        await dedupe_stage.process(context_1)
        time_1 = time.perf_counter() - start

        # Measure time for size_2
        events_2 = generate_events(size_2, duplicate_rate=0.1)
        context_2 = ProcessingContext()
        context_2.events = events_2
        start = time.perf_counter()
        await dedupe_stage.process(context_2)
        time_2 = time.perf_counter() - start

        # Verify O(n) scaling
        ratio = time_2 / time_1 if time_1 > 0 else 0
        assert (
            1.5 <= ratio <= 3.0
        ), f"Pipeline complexity appears worse than O(n): ratio={ratio:.2f}"
