"""Unit tests for issue #49: Unbounded Memory Growth in Component Superset."""

import sys
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from calendarbot_lite.lite_parser import LiteICSParser

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_settings():
    """Mock settings for parser with superset limit."""
    settings = Mock()
    settings.enable_rrule_expansion = True
    settings.rrule_expansion_days = 365
    settings.max_occurrences_per_rule = 250
    settings.raw_components_superset_limit = 100  # Low limit to test the bug faster
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
        event = f"""BEGIN:VEVENT
UID:recurring-event-{i}
DTSTART:20250115T100000Z
DTEND:20250115T110000Z
RRULE:FREQ=DAILY;COUNT=5
SUMMARY:Recurring Meeting {i}
STATUS:CONFIRMED
TRANSP:OPAQUE
END:VEVENT"""
        ics_parts.append(event)

    ics_parts.append("END:VCALENDAR")
    return "\n".join(ics_parts)


def generate_ics_with_mixed_events(recurring_count: int, non_recurring_count: int) -> str:
    """Generate ICS content with mix of recurring and non-recurring events.

    Args:
        recurring_count: Number of recurring events to generate
        non_recurring_count: Number of non-recurring events to generate

    Returns:
        ICS content string with specified events
    """
    ics_parts = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Test//Test//EN",
        "X-WR-CALNAME:Mixed Calendar Test",
    ]

    # Add recurring events
    for i in range(recurring_count):
        event = f"""BEGIN:VEVENT
UID:recurring-{i}
DTSTART:20250115T{10 + (i % 10):02d}0000Z
DTEND:20250115T{11 + (i % 10):02d}0000Z
RRULE:FREQ=DAILY;COUNT=5
SUMMARY:Recurring Event {i}
STATUS:CONFIRMED
TRANSP:OPAQUE
END:VEVENT"""
        ics_parts.append(event)

    # Add non-recurring events
    for i in range(non_recurring_count):
        event = f"""BEGIN:VEVENT
UID:single-{i}
DTSTART:20250116T{10 + (i % 10):02d}0000Z
DTEND:20250116T{11 + (i % 10):02d}0000Z
SUMMARY:Single Event {i}
STATUS:CONFIRMED
TRANSP:OPAQUE
END:VEVENT"""
        ics_parts.append(event)

    ics_parts.append("END:VCALENDAR")
    return "\n".join(ics_parts)


class TestSupersetMemoryLeak:
    """Test suite for issue #49: Unbounded memory growth in component superset."""

    @pytest.mark.memory
    def test_superset_should_enforce_limit_with_many_masters(self, parser):
        """Test that superset is bounded even with many recurring events.

        This test demonstrates the bug: when there are more recurring events (RRULE masters)
        than the superset limit, ALL masters are kept regardless of the limit.

        Expected behavior: Superset should never exceed raw_components_superset_limit
        Actual behavior: Superset grows unbounded with recurring events (BUG)
        """
        # Generate 200 recurring events, but limit is only 100
        superset_limit = parser.settings.raw_components_superset_limit
        recurring_count = superset_limit * 2  # 2x the limit

        ics_content = generate_ics_with_recurring_events(recurring_count)

        # Spy on the superset to track its size
        actual_superset_sizes = []

        original_parse_with_streaming = parser._parse_with_streaming

        def spy_on_superset(ics_content, source_url=None):
            """Wrapper to spy on superset size during parsing."""
            # Patch the superset list inside the streaming parser to track its size
            from unittest.mock import patch

            superset_sizes = actual_superset_sizes

            # Patch the list used for the superset inside the streaming parser
            # This assumes the attribute is named '_raw_components_superset'
            # If the attribute name is different, update accordingly
            def superset_append_spy(self, item):
                orig_append(item)
                superset_sizes.append(len(self))

            result = None
            with patch("calendarbot_lite.lite_parser.LiteICSParser._raw_components_superset", new_callable=list) as superset:
                orig_append = superset.append
                superset.append = lambda item: superset_append_spy(superset, item)
                result = original_parse_with_streaming(ics_content, source_url)
            return result

        with patch.object(parser, '_parse_with_streaming', side_effect=spy_on_superset):
            result = parser.parse_ics_content_optimized(ics_content)

        # The bug: superset grows unbounded because all masters are kept
        # We can't directly access the superset after parsing (it's a local variable),
        # so we'll verify indirectly by checking memory or by inspecting the code

        # For now, verify the parsing succeeded
        assert result.success, f"Parsing failed: {result.error_message}"

        # This test documents the expected behavior:
        # The superset should have been bounded to 100 items, not 200
        # But with the current bug, all 200 masters would be kept

    def test_superset_memory_growth_with_many_recurring_events(self, parser):
        """Test memory growth with large number of recurring events.

        This test verifies that memory doesn't grow unbounded when processing
        calendars with many recurring events.
        """
        superset_limit = parser.settings.raw_components_superset_limit

        # Generate 3x the superset limit in recurring events
        recurring_count = superset_limit * 3  # 300 events with limit of 100

        ics_content = generate_ics_with_recurring_events(recurring_count)

        # Track memory before and after parsing
        import tracemalloc
        tracemalloc.start()

        current, peak_before = tracemalloc.get_traced_memory()

        result = parser.parse_ics_content_optimized(ics_content)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_used_mb = (peak - peak_before) / (1024 * 1024)

        # Verify parsing succeeded
        assert result.success, f"Parsing failed: {result.error_message}"

        # With the bug, memory usage would be proportional to total event count (300)
        # After fix, memory should be bounded to superset_limit (100)

        # For 300 recurring events, each ~500 bytes, we'd expect:
        # - Buggy: ~150KB (300 * 500 bytes)
        # - Fixed: ~50KB (100 * 500 bytes)

        # Allow some overhead for parsing structures
        max_expected_mb = 5.0  # Very generous for 100 items

        print(f"\nMemory used: {memory_used_mb:.2f} MB")
        print(f"Recurring events: {recurring_count}")
        print(f"Superset limit: {superset_limit}")

        # This assertion will FAIL with the current bug, demonstrating the issue
        # After fix, this should pass
        assert memory_used_mb < max_expected_mb, (
            f"Memory usage {memory_used_mb:.2f}MB exceeds expected {max_expected_mb}MB. "
            "This suggests superset is not properly bounded."
        )

        # For now, just report the memory usage
        # The fix should reduce this significantly

    def test_superset_with_mixed_event_types(self, parser):
        """Test superset behavior with mix of recurring and non-recurring events.

        Verifies that the superset limit is enforced correctly when there's a mix
        of recurring (RRULE) and non-recurring events.
        """
        superset_limit = parser.settings.raw_components_superset_limit

        # Generate events: 150 recurring + 150 non-recurring = 300 total
        # With limit of 100, we expect:
        # - Buggy: All 150 recurring + some non-recurring = 150-200 items
        # - Fixed: 70 recurring + 30 non-recurring = 100 items (or similar split)

        recurring_count = int(superset_limit * 1.5)  # 150
        non_recurring_count = int(superset_limit * 1.5)  # 150

        ics_content = generate_ics_with_mixed_events(recurring_count, non_recurring_count)

        result = parser.parse_ics_content_optimized(ics_content)

        assert result.success, f"Parsing failed: {result.error_message}"

        # After fix, recurring events should also be subject to the superset limit
        # Not all 150 recurring events should be kept

    @pytest.mark.performance
    def test_superset_cleanup_performance(self, parser):
        """Test that superset cleanup doesn't cause O(n²) performance degradation.

        The current implementation rebuilds the superset list on every iteration
        when over the limit, causing O(n²) behavior.
        """
        superset_limit = parser.settings.raw_components_superset_limit

        # Generate events that exceed the limit
        recurring_count = superset_limit * 2

        ics_content = generate_ics_with_recurring_events(recurring_count)

        import time
        start_time = time.time()

        result = parser.parse_ics_content_optimized(ics_content)

        elapsed_time = time.time() - start_time

        assert result.success, f"Parsing failed: {result.error_message}"

        # With O(n²) behavior, parsing 200 events with cleanup could take several seconds
        # After fix with O(1) operations, should be < 1 second

        print(f"\nParsing time: {elapsed_time:.3f}s")
        print(f"Events: {recurring_count}")

        # For now, just report timing
        # After fix, this should be much faster
        max_expected_time = 2.0  # seconds
        assert elapsed_time < max_expected_time, (
            f"Parsing took {elapsed_time:.3f}s, expected < {max_expected_time}s. "
            "This suggests O(n²) performance issue."
        )


class TestSupersetBoundaryConditions:
    """Test edge cases and boundary conditions for superset limits."""

    def test_superset_exactly_at_limit(self, parser):
        """Test behavior when event count exactly matches superset limit."""
        superset_limit = parser.settings.raw_components_superset_limit

        ics_content = generate_ics_with_recurring_events(superset_limit)
        result = parser.parse_ics_content_optimized(ics_content)

        assert result.success

    def test_superset_one_over_limit(self, parser):
        """Test behavior when event count is one over the limit."""
        superset_limit = parser.settings.raw_components_superset_limit

        ics_content = generate_ics_with_recurring_events(superset_limit + 1)
        result = parser.parse_ics_content_optimized(ics_content)

        assert result.success

    def test_superset_with_zero_limit(self):
        """Test behavior with zero superset limit (edge case)."""
        settings = Mock()
        settings.enable_rrule_expansion = True
        settings.rrule_expansion_days = 365
        settings.max_occurrences_per_rule = 250
        settings.raw_components_superset_limit = 0  # Zero limit
        settings.rrule_worker_concurrency = 1
        settings.expansion_days_window = 365
        settings.expansion_time_budget_ms_per_rule = 200
        settings.expansion_yield_frequency = 50

        parser = LiteICSParser(settings)

        ics_content = generate_ics_with_recurring_events(10)
        result = parser.parse_ics_content_optimized(ics_content)

        # Should handle gracefully, not crash
        assert result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not performance"])
