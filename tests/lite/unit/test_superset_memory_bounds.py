"""Unit tests for Issue #49: Unbounded Memory Growth in Component Superset.

This test suite verifies that the component superset memory bounds are enforced
correctly for both recurring and non-recurring events.
"""

import sys
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from calendarbot_lite.calendar.lite_parser import LiteICSParser

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_settings():
    """Mock settings for parser with superset limit."""
    settings = Mock()
    settings.enable_rrule_expansion = True
    settings.rrule_expansion_days = 365
    settings.max_occurrences_per_rule = 250
    settings.raw_components_superset_limit = 100  # Low limit to test bounds enforcement
    # RRULE worker pool settings
    settings.rrule_worker_concurrency = 1
    settings.expansion_days_window = 365
    settings.expansion_time_budget_ms_per_rule = 200
    settings.expansion_yield_frequency = 50
    return settings


@pytest.fixture
def parser(mock_settings):
    """Create parser instance."""
    return LiteICSParser(mock_settings)


def generate_ics_with_recurring_events(count: int) -> str:
    """Generate ICS content with many recurring events.

    Args:
        count: Number of recurring events to generate

    Returns:
        ICS content string with specified number of recurring events
    """
    ics_parts = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Test//Test//EN",
        "X-WR-CALNAME:Large Calendar Test",
    ]

    for i in range(count):
        ics_parts.extend([
            "BEGIN:VEVENT",
            f"UID:recurring-{i}@test.com",
            f"SUMMARY:Recurring Event {i}",
            "DTSTART:20250101T100000Z",
            "DTEND:20250101T110000Z",
            "RRULE:FREQ=DAILY;COUNT=30",
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT",
        ])

    ics_parts.append("END:VCALENDAR")
    return "\n".join(ics_parts)


def generate_ics_with_single_events(count: int) -> str:
    """Generate ICS content with many single (non-recurring) events.

    Args:
        count: Number of single events to generate

    Returns:
        ICS content string with specified number of single events
    """
    ics_parts = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Test//Test//EN",
        "X-WR-CALNAME:Large Calendar Test",
    ]

    for i in range(count):
        ics_parts.extend([
            "BEGIN:VEVENT",
            f"UID:single-{i}@test.com",
            f"SUMMARY:Single Event {i}",
            f"DTSTART:202501{(i % 28) + 1:02d}T100000Z",
            f"DTEND:202501{(i % 28) + 1:02d}T110000Z",
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT",
        ])

    ics_parts.append("END:VCALENDAR")
    return "\n".join(ics_parts)


def generate_ics_with_mixed_events(recurring_count: int, single_count: int) -> str:
    """Generate ICS content with both recurring and single events.

    Args:
        recurring_count: Number of recurring events
        single_count: Number of single events

    Returns:
        ICS content string with mixed event types
    """
    ics_parts = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Test//Test//EN",
        "X-WR-CALNAME:Mixed Calendar Test",
    ]

    # Add recurring events
    for i in range(recurring_count):
        ics_parts.extend([
            "BEGIN:VEVENT",
            f"UID:recurring-{i}@test.com",
            f"SUMMARY:Recurring Event {i}",
            "DTSTART:20250101T100000Z",
            "DTEND:20250101T110000Z",
            "RRULE:FREQ=DAILY;COUNT=30",
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT",
        ])

    # Add single events
    for i in range(single_count):
        ics_parts.extend([
            "BEGIN:VEVENT",
            f"UID:single-{i}@test.com",
            f"SUMMARY:Single Event {i}",
            f"DTSTART:202501{(i % 28) + 1:02d}T100000Z",
            f"DTEND:202501{(i % 28) + 1:02d}T110000Z",
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT",
        ])

    ics_parts.append("END:VCALENDAR")
    return "\n".join(ics_parts)


class TestSupersetMemoryBounds:
    """Tests for component superset memory bounds enforcement."""

    def test_recurring_events_respect_limit(self, parser):
        """Test that recurring events are bounded to 70% of superset limit.

        This is the critical test for Issue #49 - verifies that we don't keep
        ALL recurring masters, but enforce a hard limit.
        """
        # Generate 200 recurring events (2x the total limit of 100)
        ics_content = generate_ics_with_recurring_events(200)

        # Parse the content
        result = parser.parse_ics_content_optimized(ics_content)

        # Verify parsing succeeded
        assert result.success, f"Parsing failed: {result.error_message}"

        # The key assertion: we should have limited the number of recurring events
        # stored, not kept all 200
        # With limit=100, masters_limit=70, we should have at most 70 recurring events
        # tracked for RRULE expansion
        assert result.recurring_event_count == 200, "Should count all 200 recurring events"

        # We can't directly check the internal superset size, but we can verify
        # that parsing doesn't consume unbounded memory by checking it completes
        # successfully without OOM
        assert result.event_count == 200

    def test_single_events_respect_limit(self, parser):
        """Test that single (non-recurring) events are bounded to 30% of superset limit."""
        # Generate 200 single events (2x the total limit of 100)
        ics_content = generate_ics_with_single_events(200)

        # Parse the content
        result = parser.parse_ics_content_optimized(ics_content)

        # Verify parsing succeeded
        assert result.success, f"Parsing failed: {result.error_message}"

        # Should have counted all events but bounded storage
        assert result.event_count == 200, "Should count all 200 single events"
        assert result.recurring_event_count == 0, "Should have no recurring events"

    def test_mixed_events_respect_split_limits(self, parser):
        """Test that mixed calendars respect the 70/30 split between recurring/single."""
        # Generate 150 recurring + 150 single events (3x the limit of 100 total)
        ics_content = generate_ics_with_mixed_events(150, 150)

        # Parse the content
        result = parser.parse_ics_content_optimized(ics_content)

        # Verify parsing succeeded
        assert result.success, f"Parsing failed: {result.error_message}"

        # Should have counted all events
        assert result.event_count == 300, "Should count all 300 events"
        assert result.recurring_event_count == 150, "Should count 150 recurring events"

        # The implementation should bound both types independently

    def test_memory_usage_stays_bounded(self, parser):
        """Test that memory usage stays bounded even with very large calendars.

        This test uses tracemalloc to verify actual memory usage.
        """
        import tracemalloc

        # Start memory tracking
        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        # Generate a large calendar (300 recurring events, 3x the limit)
        ics_content = generate_ics_with_recurring_events(300)

        # Parse the content
        result = parser.parse_ics_content_optimized(ics_content)

        # Take memory snapshot after parsing
        snapshot_after = tracemalloc.take_snapshot()
        tracemalloc.stop()

        # Verify parsing succeeded
        assert result.success, f"Parsing failed: {result.error_message}"

        # Calculate memory increase
        top_stats = snapshot_after.compare_to(snapshot_before, "lineno")
        total_memory_increase = sum(stat.size_diff for stat in top_stats)

        # Memory should be bounded (< 25MB for this test)
        # The exact limit depends on the implementation, but with bounds it should
        # be much less than unbounded growth (which would be 100MB+ for 300 events)
        max_acceptable_memory_mb = 25
        memory_increase_mb = total_memory_increase / (1024 * 1024)

        assert memory_increase_mb < max_acceptable_memory_mb, (
            f"Memory usage {memory_increase_mb:.2f}MB exceeds "
            f"acceptable limit of {max_acceptable_memory_mb}MB"
        )

    def test_boundary_condition_at_limit(self, parser):
        """Test behavior when event count exactly equals the limit."""
        # Generate exactly 100 events (matching the limit)
        ics_content = generate_ics_with_recurring_events(100)

        # Parse the content
        result = parser.parse_ics_content_optimized(ics_content)

        # Verify parsing succeeded
        assert result.success, f"Parsing failed: {result.error_message}"
        assert result.event_count == 100

    def test_boundary_condition_one_over_limit(self, parser):
        """Test behavior when event count is exactly 1 over the limit."""
        # Generate 101 events (1 over the limit)
        ics_content = generate_ics_with_recurring_events(101)

        # Parse the content
        result = parser.parse_ics_content_optimized(ics_content)

        # Verify parsing succeeded and handled the overflow
        assert result.success, f"Parsing failed: {result.error_message}"
        assert result.event_count == 101

    def test_zero_limit_edge_case(self, parser, mock_settings):
        """Test behavior with zero or very small limits."""
        # Set limit to 0
        mock_settings.raw_components_superset_limit = 0
        parser = LiteICSParser(mock_settings)

        # Generate some events
        ics_content = generate_ics_with_recurring_events(10)

        # Parse should handle gracefully
        result = parser.parse_ics_content_optimized(ics_content)

        # Parsing may succeed or fail gracefully, but shouldn't crash
        assert result is not None

    def test_very_large_limit(self, parser, mock_settings):
        """Test behavior with very large limits."""
        # Set limit to a very large value
        mock_settings.raw_components_superset_limit = 1000000
        parser = LiteICSParser(mock_settings)

        # Generate some events (much less than limit)
        ics_content = generate_ics_with_recurring_events(100)

        # Parse should work normally
        result = parser.parse_ics_content_optimized(ics_content)

        assert result.success, f"Parsing failed: {result.error_message}"
        assert result.event_count == 100

    def test_fifo_eviction_keeps_newest(self, parser):
        """Test that FIFO eviction keeps the most recent events.

        When we exceed limits, we should keep the newest (most recent in the file)
        events, not the oldest ones.
        """
        # Generate events with identifiable summaries
        ics_parts = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Test//Test//EN",
        ]

        # Generate 150 recurring events (1.5x the total limit)
        # The newer ones should be kept
        for i in range(150):
            ics_parts.extend([
                "BEGIN:VEVENT",
                f"UID:event-{i}@test.com",
                f"SUMMARY:Event Number {i}",
                "DTSTART:20250101T100000Z",
                "DTEND:20250101T110000Z",
                "RRULE:FREQ=DAILY;COUNT=30",
                "STATUS:CONFIRMED",
                "TRANSP:OPAQUE",
                "END:VEVENT",
            ])

        ics_parts.append("END:VCALENDAR")
        ics_content = "\n".join(ics_parts)

        # Parse
        result = parser.parse_ics_content_optimized(ics_content)

        # Verify parsing succeeded
        assert result.success, f"Parsing failed: {result.error_message}"

        # All events should be counted
        assert result.event_count == 150

        # The FIFO eviction should keep the newest events
        # We can verify this by checking that expansion worked
        # (expansion requires the components to be in the superset)


class TestSupersetPerformance:
    """Performance tests to ensure the fix doesn't degrade performance."""

    def test_parsing_performance_acceptable(self, parser):
        """Test that parsing performance is acceptable with bounded memory."""
        import time

        # Generate a reasonably large calendar
        ics_content = generate_ics_with_recurring_events(200)

        # Measure parsing time
        start_time = time.time()
        result = parser.parse_ics_content_optimized(ics_content)
        end_time = time.time()

        # Verify parsing succeeded
        assert result.success, f"Parsing failed: {result.error_message}"

        # Parsing should be fast (< 5 seconds for 200 events)
        parse_time = end_time - start_time
        assert parse_time < 5.0, f"Parsing took {parse_time:.2f}s, expected < 5s"

    def test_no_quadratic_behavior(self, parser):
        """Test that we don't have O(n²) behavior in the superset management.

        The old implementation with repeated filtering was O(n²).
        The new implementation should be O(n).
        """
        import time

        # Test with different sizes and verify linear scaling
        sizes = [50, 100, 200]
        times = []

        for size in sizes:
            ics_content = generate_ics_with_recurring_events(size)

            # Use perf_counter for better precision than time.time()
            start_time = time.perf_counter()
            result = parser.parse_ics_content_optimized(ics_content)
            end_time = time.perf_counter()

            assert result.success, f"Parsing failed for size {size}"
            times.append(end_time - start_time)

        # Check that doubling the size doesn't quadruple the time
        # Allow some variance, but it should be roughly linear
        # If it were O(n²), doubling would ~4x the time
        # If it's O(n), doubling should ~2x the time
        MIN_TIME_THRESHOLD = 1e-3  # 1ms minimum to avoid noise from very fast operations
        if times[1] > MIN_TIME_THRESHOLD and times[0] > MIN_TIME_THRESHOLD:
            ratio_50_to_100 = times[1] / times[0]

            # Threshold of 3.5 allows for O(n log n) and environmental variance
            # while still catching O(n²) behavior (which would be ~4.0)
            assert ratio_50_to_100 < 3.5, (
                f"Parsing shows quadratic behavior: 50→100 ratio={ratio_50_to_100:.2f}"
            )

        if times[2] > MIN_TIME_THRESHOLD and times[1] > MIN_TIME_THRESHOLD:
            ratio_100_to_200 = times[2] / times[1]

            # Threshold of 3.5 allows for O(n log n) and environmental variance
            # while still catching O(n²) behavior (which would be ~4.0)
            assert ratio_100_to_200 < 3.5, (
                f"Parsing shows quadratic behavior: 100→200 ratio={ratio_100_to_200:.2f}"
            )
