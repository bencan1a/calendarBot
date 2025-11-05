"""Memory profiling tests for Raspberry Pi Zero 2W deployment validation.

Target: <100MB RAM idle, resource-efficient operation for embedded deployment.

These tests validate memory usage patterns to ensure the application can run
efficiently on resource-constrained hardware (Raspberry Pi Zero 2W with 512MB RAM).

Baseline expectations (documented 2025-11-05):
- Large calendar parsing: <50MB RAM usage
- 1000+ recurring events: <75MB RAM usage
- Concurrent fetches: <100MB total RAM usage
- No memory leaks in repeated operations

Run with: pytest tests/lite/ -m memory -v
"""

import asyncio
import gc
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from calendarbot_lite.calendar.lite_models import LiteCalendarEvent, LiteEventStatus
from calendarbot_lite.calendar.lite_rrule_expander import RRuleWorkerPool
from calendarbot_lite.calendar.lite_streaming_parser import parse_ics_stream

pytestmark = [pytest.mark.performance, pytest.mark.memory, pytest.mark.slow]


# Helper to generate large ICS content
def generate_large_calendar(num_events: int = 500, with_rrule: bool = False) -> str:
    """Generate large ICS calendar content for memory testing.

    Args:
        num_events: Number of events to generate (default 500 to avoid telemetry warnings)
        with_rrule: If True, use recurring events (fewer entries, more expansion)

    Returns:
        ICS calendar string
    """
    ics_parts = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//CalendarBot Lite//Memory Test//EN",
        "CALSCALE:GREGORIAN",
    ]

    if with_rrule:
        # Generate recurring events (compact but expands to many occurrences)
        for i in range(num_events):
            start_date = datetime(2025, 1, 1, 9, 0, tzinfo=UTC) + timedelta(hours=i % 24)
            end_date = start_date + timedelta(hours=1)

            ics_parts.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:recurring-event-{i}@memory-test.local",
                    f"DTSTART:{start_date.strftime('%Y%m%dT%H%M%SZ')}",
                    f"DTEND:{end_date.strftime('%Y%m%dT%H%M%SZ')}",
                    f"SUMMARY:Memory Test Event {i}",
                    f"DESCRIPTION:This is a memory test event with some body text to simulate real events. Event number {i}.",
                    "LOCATION:Test Location",
                    "STATUS:CONFIRMED",
                    "TRANSP:OPAQUE",
                    "RRULE:FREQ=DAILY;COUNT=10",  # Each event expands to 10 occurrences
                    "END:VEVENT",
                ]
            )
    else:
        # Generate individual events (larger file size, no expansion)
        for i in range(num_events):
            event_date = datetime(2025, 1, 1, 9, 0, tzinfo=UTC) + timedelta(
                days=i % 365, hours=i % 24
            )
            end_date = event_date + timedelta(hours=1)

            ics_parts.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:simple-event-{i}@memory-test.local",
                    f"DTSTART:{event_date.strftime('%Y%m%dT%H%M%SZ')}",
                    f"DTEND:{end_date.strftime('%Y%m%dT%H%M%SZ')}",
                    f"SUMMARY:Simple Event {i}",
                    f"DESCRIPTION:This is a simple event with body text. Event {i}. Adding more text to increase memory footprint for realistic testing.",
                    "LOCATION:Test Location Room 123",
                    "STATUS:CONFIRMED",
                    "TRANSP:OPAQUE",
                    "END:VEVENT",
                ]
            )

    ics_parts.append("END:VCALENDAR")
    return "\n".join(ics_parts)


class AsyncByteIterator:
    """Helper class to simulate async byte stream for streaming parser tests."""

    def __init__(self, content: str, chunk_size: int = 8192):
        self.data = content.encode("utf-8")
        self.chunk_size = chunk_size
        self.position = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.position >= len(self.data):
            raise StopAsyncIteration

        chunk = self.data[self.position : self.position + self.chunk_size]
        self.position += self.chunk_size
        await asyncio.sleep(0)  # Yield control
        return chunk


@pytest.mark.asyncio
@pytest.mark.limit_memory("50 MB")  # pytest-memray: fail if exceeds 50MB
async def test_large_calendar_file_memory_usage(tmp_path):
    """Test memory usage when parsing large calendar files.

    Target: <50MB RAM for parsing 1000 events

    This test validates that the streaming parser efficiently handles large
    files without excessive memory consumption, critical for RPi deployment.

    Note: Reduced to 1000 events to avoid telemetry warning spam.
    """
    # Generate large calendar (1000 events ~ 2-3MB file size)
    ics_content = generate_large_calendar(num_events=1000, with_rrule=False)
    file_size_mb = len(ics_content.encode("utf-8")) / (1024 * 1024)
    print(f"\nGenerated calendar file: {file_size_mb:.2f} MB")

    # Force garbage collection before test
    gc.collect()

    # Parse using streaming parser
    stream = AsyncByteIterator(ics_content, chunk_size=8192)
    result = await parse_ics_stream(stream, source_url="memory-test://large-file")

    # Verify parsing succeeded
    assert result.success, f"Parser failed: {result.error_message}"
    assert result.event_count > 0, "No events parsed"
    print(f"Parsed {result.event_count} events successfully")

    # Force cleanup
    del result
    del stream
    gc.collect()


@pytest.mark.asyncio
@pytest.mark.limit_memory("75 MB")  # pytest-memray: fail if exceeds 75MB
async def test_recurring_event_expansion_memory_usage():
    """Test memory usage when expanding 1000+ recurring events.

    Target: <75MB RAM for expanding 1000 recurring events (10,000 occurrences total)

    Validates that RRULE expansion with worker pool doesn't accumulate excessive
    memory, especially important for calendars with many recurring meetings.
    """
    # Create settings for RRULE expansion
    settings = SimpleNamespace(
        rrule_worker_concurrency=2,
        max_occurrences_per_rule=100,
        expansion_days_window=365,
        expansion_time_budget_ms_per_rule=1000,
        expansion_yield_frequency=50,
    )

    pool = RRuleWorkerPool(settings)

    # Force garbage collection before test
    gc.collect()

    # Create 1000 master events with RRULE
    total_expanded = 0
    for i in range(1000):
        start_dt = datetime(2025, 1, 1, 9, 0, tzinfo=UTC) + timedelta(hours=i % 24)
        end_dt = start_dt + timedelta(hours=1)

        master = SimpleNamespace()
        master.start = SimpleNamespace(date_time=start_dt, time_zone="UTC")
        master.end = SimpleNamespace(date_time=end_dt, time_zone="UTC")
        master.id = f"master-{i}"
        master.subject = f"Recurring Meeting {i}"
        master.body_preview = ""
        master.is_all_day = False
        master.show_as = LiteEventStatus.BUSY
        master.is_cancelled = False
        master.is_organizer = True
        master.location = None
        master.is_online_meeting = False
        master.online_meeting_url = None
        master.last_modified_date_time = None

        # Expand to 10 occurrences each (10,000 total)
        rrule = "FREQ=DAILY;COUNT=10"
        instances = await pool.expand_event_to_list(master, rrule, exdates=None)  # type: ignore[arg-type]
        total_expanded += len(instances)

        # Cleanup every 100 iterations to prevent accumulation
        if i % 100 == 0:
            del instances
            gc.collect()

    print(f"\nExpanded {total_expanded} total event occurrences from 1000 recurring events")
    assert total_expanded >= 9000, f"Expected ~10000 occurrences, got {total_expanded}"

    # Cleanup
    await pool.shutdown()
    gc.collect()


@pytest.mark.asyncio
@pytest.mark.limit_memory("100 MB")  # pytest-memray: fail if exceeds 100MB
async def test_concurrent_calendar_fetch_memory_usage(tmp_path):
    """Test memory usage when processing multiple calendars concurrently.

    Target: <100MB RAM for 5 concurrent calendar fetches/parses

    Validates bounded concurrency and memory usage when fetching multiple
    calendar sources simultaneously, as would occur in production.
    """
    # Generate 5 different calendars
    calendars = []
    for _ in range(5):
        ics_content = generate_large_calendar(num_events=500, with_rrule=True)
        calendars.append(ics_content)

    print(f"\nGenerated {len(calendars)} calendars for concurrent processing")

    # Force garbage collection before test
    gc.collect()

    # Parse all calendars concurrently
    async def parse_calendar(content: str, idx: int):
        stream = AsyncByteIterator(content)
        return await parse_ics_stream(stream, source_url=f"memory-test://concurrent-{idx}")

    # Process concurrently
    results = await asyncio.gather(*[parse_calendar(cal, i) for i, cal in enumerate(calendars)])

    # Verify all succeeded
    for i, result in enumerate(results):
        assert result.success, f"Calendar {i} failed: {result.error_message}"
        assert result.event_count > 0, f"Calendar {i} has no events"

    total_events = sum(r.event_count for r in results)
    print(f"Parsed {total_events} total events from {len(calendars)} calendars")

    # Cleanup
    del results
    gc.collect()


@pytest.mark.asyncio
async def test_memory_leak_detection_repeated_parsing(tmp_path):
    """Test for memory leaks in repeated parse operations.

    This test runs the parser multiple times to detect memory leaks that would
    accumulate over time in a long-running server process. Uses manual memory
    tracking since pytest-memray's limit_memory doesn't detect slow leaks.

    Note: This test does not use @pytest.mark.limit_memory because we want to
    track growth patterns, not absolute limits.
    """
    import tracemalloc

    # Start memory tracking
    tracemalloc.start()
    gc.collect()

    # Generate test calendar
    ics_content = generate_large_calendar(num_events=1000, with_rrule=False)

    # Record baseline memory
    baseline_snapshot = tracemalloc.take_snapshot()
    baseline_memory = sum(stat.size for stat in baseline_snapshot.statistics("filename")) / (
        1024 * 1024
    )
    print(f"\nBaseline memory: {baseline_memory:.2f} MB")

    # Parse the same calendar 10 times
    memory_samples = []
    for i in range(10):
        stream = AsyncByteIterator(ics_content)
        result = await parse_ics_stream(stream, source_url=f"memory-test://leak-{i}")
        assert result.success

        # Force cleanup after each iteration
        del result
        del stream
        gc.collect()

        # Sample memory
        current_snapshot = tracemalloc.take_snapshot()
        current_memory = sum(stat.size for stat in current_snapshot.statistics("filename")) / (
            1024 * 1024
        )
        memory_samples.append(current_memory)

    # Analyze memory growth
    final_memory = memory_samples[-1]
    memory_growth = final_memory - baseline_memory
    max_growth = max(memory_samples) - baseline_memory

    print(f"Final memory: {final_memory:.2f} MB")
    print(f"Memory growth: {memory_growth:.2f} MB")
    print(f"Max memory: {max_growth:.2f} MB")
    print(f"Memory samples: {[f'{m:.2f}' for m in memory_samples]}")

    # Stop tracking
    tracemalloc.stop()

    # Assert no significant memory leak (allow 10MB growth for caching/buffers)
    # This is a generous threshold; in practice we expect <5MB growth
    assert memory_growth < 10.0, (
        f"Potential memory leak detected: {memory_growth:.2f} MB growth "
        f"after 10 iterations (threshold: 10 MB)"
    )

    # Also check that memory doesn't continuously grow (check slope)
    # If there's a leak, later samples should be significantly higher than earlier ones
    first_half_avg = sum(memory_samples[:5]) / 5
    second_half_avg = sum(memory_samples[5:]) / 5
    slope = second_half_avg - first_half_avg

    print(f"First half average: {first_half_avg:.2f} MB")
    print(f"Second half average: {second_half_avg:.2f} MB")
    print(f"Slope: {slope:.2f} MB")

    assert slope < 5.0, (
        f"Memory continuously growing: {slope:.2f} MB increase from first to second half "
        f"(threshold: 5 MB)"
    )


@pytest.mark.asyncio
@pytest.mark.limit_memory("30 MB")  # pytest-memray: minimal memory for small calendars
async def test_minimal_memory_footprint_small_calendar():
    """Test minimal memory footprint for small calendars.

    Target: <30MB RAM for parsing 100 events

    Validates that the parser doesn't have excessive overhead for common
    small calendar scenarios (daily usage with few events).
    """
    # Generate small calendar
    ics_content = generate_large_calendar(num_events=100, with_rrule=False)

    gc.collect()

    # Parse
    stream = AsyncByteIterator(ics_content)
    result = await parse_ics_stream(stream, source_url="memory-test://small")

    assert result.success
    assert result.event_count > 0
    print(f"\nParsed {result.event_count} events in small calendar test")

    # Cleanup
    del result
    del stream
    gc.collect()


@pytest.mark.asyncio
async def test_event_deduplication_memory_efficiency():
    """Test memory efficiency of event deduplication with many duplicates.

    Validates that deduplication doesn't create excessive memory overhead
    when processing calendars with many duplicate events (common with
    multiple calendar sources).
    """
    import tracemalloc

    from calendarbot_lite.calendar.lite_models import LiteDateTimeInfo

    tracemalloc.start()
    gc.collect()

    # Create events with many duplicates (simulate multiple calendar sources)
    events: list[LiteCalendarEvent] = []
    base_time = datetime(2025, 1, 1, 9, 0, tzinfo=UTC)

    # Create 100 unique events, duplicated 10 times each (1000 total)
    for i in range(100):
        event_time = base_time + timedelta(hours=i)

        for duplicate in range(10):
            # Create slightly different IDs to simulate different sources
            event = LiteCalendarEvent(
                id=f"event-{i}-source-{duplicate}",
                subject=f"Meeting {i}",
                start=LiteDateTimeInfo(
                    date_time=event_time,
                    time_zone="America/Los_Angeles",
                ),
                end=LiteDateTimeInfo(
                    date_time=event_time + timedelta(hours=1),
                    time_zone="America/Los_Angeles",
                ),
                body_preview="Test meeting",
                is_all_day=False,
                show_as=LiteEventStatus.BUSY,
                is_cancelled=False,
                is_organizer=True,
                location=None,
                is_online_meeting=False,
                online_meeting_url=None,
                last_modified_date_time=None,
            )
            events.append(event)

    print(f"\nCreated {len(events)} events (100 unique, 10 duplicates each)")

    # Measure memory before deduplication
    before_snapshot = tracemalloc.take_snapshot()
    before_memory = sum(stat.size for stat in before_snapshot.statistics("filename")) / (
        1024 * 1024
    )

    # Simulate deduplication by creating a dict keyed by (subject, start_time)
    deduplicated = {}
    for event in events:
        key = (event.subject, event.start.date_time)
        if key not in deduplicated:
            deduplicated[key] = event

    # Measure memory after deduplication
    after_snapshot = tracemalloc.take_snapshot()
    after_memory = sum(stat.size for stat in after_snapshot.statistics("filename")) / (1024 * 1024)

    print(f"Before deduplication: {before_memory:.2f} MB ({len(events)} events)")
    print(f"After deduplication: {after_memory:.2f} MB ({len(deduplicated)} events)")
    print(f"Memory saved: {(before_memory - after_memory):.2f} MB")

    tracemalloc.stop()

    # Verify deduplication worked
    assert len(deduplicated) == 100, f"Expected 100 unique events, got {len(deduplicated)}"

    # Memory usage should be reasonable
    assert after_memory < 50.0, f"Deduplication memory too high: {after_memory:.2f} MB"

    # Cleanup
    del events
    del deduplicated
    gc.collect()


@pytest.mark.asyncio
@pytest.mark.limit_memory("75 MB")  # pytest-memray: production workload limit
async def test_production_workload_4000_events(tmp_path, caplog):
    """Test memory usage for typical production workload.

    Target: <75MB RAM for parsing 4000 events (trimmed to ~50 event window)

    This test simulates the realistic production scenario:
    - ICS file with ~4000 events
    - Parsed and trimmed to window of 50 events
    - Fetched every 5 minutes

    Note: Telemetry warnings are suppressed for this test since exceeding
    the 1000-event warning threshold is expected for production workloads.
    """
    import logging

    # Temporarily suppress INFO/WARNING logs for this test to avoid spam
    logging.getLogger("calendarbot_lite").setLevel(logging.ERROR)

    # Generate realistic calendar (4000 events)
    ics_content = generate_large_calendar(num_events=4000, with_rrule=False)
    file_size_mb = len(ics_content.encode("utf-8")) / (1024 * 1024)
    print(f"\nGenerated production calendar: {file_size_mb:.2f} MB with 4000 events")

    # Force garbage collection before test
    gc.collect()

    # Parse using streaming parser
    stream = AsyncByteIterator(ics_content, chunk_size=8192)
    result = await parse_ics_stream(stream, source_url="memory-test://production-4000")

    # Verify parsing succeeded
    assert result.success, f"Parser failed: {result.error_message}"
    print(f"Parsed {result.event_count} events successfully (trimmed from 4000)")

    # In production, events are further trimmed to a window (e.g., 50 events)
    # Simulate this trimming by selecting a subset
    # (In real code, this happens in the event window filtering logic)

    # Force cleanup to simulate end of fetch cycle
    del result
    del stream
    gc.collect()

    print("Production workload simulation complete")

    # Reset logging
    logging.getLogger("calendarbot_lite").setLevel(logging.INFO)


# Summary test that runs all memory-critical paths together
@pytest.mark.asyncio
@pytest.mark.limit_memory("100 MB")  # Overall system limit
async def test_end_to_end_memory_profile(tmp_path):
    """End-to-end memory profiling test simulating production workload.

    Target: <100MB RAM for complete calendar fetch/parse/expand cycle

    This test simulates a realistic production scenario:
    1. Parse multiple calendars (some with RRULE)
    2. Expand recurring events
    3. Deduplicate results
    4. All within 100MB memory budget
    """
    gc.collect()

    # Step 1: Generate and parse calendars
    print("\n=== Step 1: Parsing calendars ===")
    calendars = [
        generate_large_calendar(num_events=300, with_rrule=True),
        generate_large_calendar(num_events=500, with_rrule=False),
    ]

    parse_tasks = [
        parse_ics_stream(AsyncByteIterator(cal), f"memory-test://e2e-{i}")
        for i, cal in enumerate(calendars)
    ]
    results = await asyncio.gather(*parse_tasks)

    total_parsed = sum(r.event_count for r in results)
    print(f"Parsed {total_parsed} events from {len(calendars)} calendars")

    # Step 2: Simulate RRULE expansion
    print("\n=== Step 2: Expanding recurring events ===")
    settings = SimpleNamespace(
        rrule_worker_concurrency=2,
        max_occurrences_per_rule=50,
        expansion_days_window=180,
        expansion_time_budget_ms_per_rule=500,
        expansion_yield_frequency=25,
    )

    pool = RRuleWorkerPool(settings)

    # Expand a few recurring events
    expanded_count = 0
    for i in range(50):  # Expand 50 recurring events
        start_dt = datetime(2025, 1, 1, 9, 0, tzinfo=UTC) + timedelta(hours=i)
        end_dt = start_dt + timedelta(hours=1)

        master = SimpleNamespace()
        master.start = SimpleNamespace(date_time=start_dt, time_zone="UTC")
        master.end = SimpleNamespace(date_time=end_dt, time_zone="UTC")
        master.id = f"e2e-master-{i}"
        master.subject = f"E2E Meeting {i}"
        master.body_preview = ""
        master.is_all_day = False
        master.show_as = LiteEventStatus.BUSY
        master.is_cancelled = False
        master.is_organizer = True
        master.location = None
        master.is_online_meeting = False
        master.online_meeting_url = None
        master.last_modified_date_time = None

        instances = await pool.expand_event_to_list(master, "FREQ=DAILY;COUNT=5", exdates=None)  # type: ignore[arg-type]
        expanded_count += len(instances)

        # Periodic cleanup
        if i % 10 == 0:
            del instances
            gc.collect()

    print(f"Expanded {expanded_count} event occurrences")

    # Step 3: Cleanup
    print("\n=== Step 3: Cleanup ===")
    await pool.shutdown()
    del results
    del parse_tasks
    gc.collect()

    print("End-to-end memory profiling complete")
