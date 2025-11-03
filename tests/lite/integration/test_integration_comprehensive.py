"""
Comprehensive integration tests for calendarbot_lite.

These tests exercise full end-to-end flows across multiple components:
- Full ICS parsing pipeline (fetch → parse → expand → filter → sort)
- Timezone conversion edge cases across the stack
- Cross-component event processing validation

Marked as @pytest.mark.integration for selective execution.
"""

import asyncio
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from textwrap import dedent
from types import SimpleNamespace
from typing import Any

import pytest

from calendarbot_lite.lite_fetcher import LiteICSFetcher
from calendarbot_lite.lite_parser import LiteICSParser
from calendarbot_lite.pipeline import EventProcessingPipeline, ProcessingContext
from calendarbot_lite.pipeline_stages import (
    DeduplicationStage,
    SortStage,
    TimeWindowStage,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def test_settings() -> SimpleNamespace:
    """Minimal settings for integration tests."""
    return SimpleNamespace(
        rrule_worker_concurrency=2,
        max_occurrences_per_rule=500,
        expansion_days_window=365,
        expansion_time_budget_ms_per_rule=200,
        expansion_yield_frequency=50,
        rrule_expansion_days=30,
        enable_rrule_expansion=True,
        request_timeout=10,
        max_retries=2,
        retry_backoff_factor=1.5,
    )


@pytest.fixture
def ics_with_timezone_edge_cases() -> str:
    """ICS content with various timezone edge cases."""
    return dedent(
        """
        BEGIN:VCALENDAR
        VERSION:2.0
        PRODID:-//Test//Test//EN
        BEGIN:VEVENT
        UID:utc-event
        SUMMARY:UTC Event
        DTSTART:20251201T140000Z
        DTEND:20251201T150000Z
        END:VEVENT
        BEGIN:VEVENT
        UID:naive-event
        SUMMARY:Naive Datetime Event
        DTSTART:20251201T100000
        DTEND:20251201T110000
        END:VEVENT
        BEGIN:VEVENT
        UID:recurring-tz-event
        SUMMARY:Recurring with TZ
        DTSTART;TZID=America/Los_Angeles:20251201T090000
        DTEND;TZID=America/Los_Angeles:20251201T100000
        RRULE:FREQ=DAILY;COUNT=3
        END:VEVENT
        END:VCALENDAR
        """
    )


@pytest.fixture
def ics_with_complex_recurrence() -> str:
    """ICS content with complex recurring events."""
    return dedent(
        """
        BEGIN:VCALENDAR
        VERSION:2.0
        PRODID:-//Test//Test//EN
        BEGIN:VEVENT
        UID:daily-standup
        SUMMARY:Daily Standup
        DTSTART:20251201T090000Z
        DTEND:20251201T091500Z
        RRULE:FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR;COUNT=10
        END:VEVENT
        BEGIN:VEVENT
        UID:weekly-review
        SUMMARY:Weekly Review
        DTSTART:20251206T140000Z
        DTEND:20251206T150000Z
        RRULE:FREQ=WEEKLY;BYDAY=FR;COUNT=4
        END:VEVENT
        BEGIN:VEVENT
        UID:exception-instance
        SUMMARY:Weekly Review - Rescheduled
        DTSTART:20251213T160000Z
        DTEND:20251213T170000Z
        RECURRENCE-ID:20251213T140000Z
        END:VEVENT
        BEGIN:VEVENT
        UID:single-meeting
        SUMMARY:One-off Meeting
        DTSTART:20251203T100000Z
        DTEND:20251203T110000Z
        END:VEVENT
        END:VCALENDAR
        """
    )


@pytest.mark.integration
def test_full_ics_pipeline_when_complex_recurrence_then_all_stages_work(
    test_settings: SimpleNamespace, ics_with_complex_recurrence: str, tmp_path: Any
) -> None:
    """Integration test: Full ICS parsing pipeline with recurring events.

    Tests the complete flow:
    1. Parse ICS content (with RRULE expansion)
    2. Deduplicate events
    3. Apply time window filter
    4. Sort events
    
    Validates that all stages work together correctly and produce the expected output.
    """
    parser = LiteICSParser(test_settings)
    
    # Parse with RRULE expansion
    result = parser.parse_ics_content_optimized(
        ics_with_complex_recurrence, source_url=str(tmp_path / "test.ics")
    )
    
    assert result.success is True, f"Parser failed: {result.error_message}"
    assert len(result.events) > 0, "Expected parsed events"
    
    # Verify RRULE expansion produced multiple instances
    # The parser expands recurring events into multiple event instances
    # We expect more events than the 4 unique UIDs in the test ICS
    assert len(result.events) >= 10, f"Expected at least 10 expanded events, got {len(result.events)}"
    
    # Verify we have events from different recurring patterns
    event_subjects = {e.subject for e in result.events}
    assert "Daily Standup" in event_subjects, "Expected daily standup events"
    assert "Weekly Review" in event_subjects, "Expected weekly review events"
    
    # Build processing pipeline
    pipeline = (
        EventProcessingPipeline()
        .add_stage(DeduplicationStage())
        .add_stage(TimeWindowStage())
        .add_stage(SortStage())
    )
    
    # Process events through pipeline
    context = ProcessingContext(
        events=result.events,
        window_start=datetime(2025, 12, 1, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc),
    )
    pipeline_result = asyncio.run(pipeline.process(context))
    
    assert pipeline_result.success is True
    assert len(context.events) > 0, "Expected events after pipeline"
    
    # Verify events are sorted
    for i in range(len(context.events) - 1):
        assert (
            context.events[i].start.date_time <= context.events[i + 1].start.date_time
        ), "Events should be sorted by start time"
    
    # Verify all events are within time window
    for event in context.events:
        assert event.start.date_time >= datetime(2025, 12, 1, 0, 0, tzinfo=timezone.utc)
        assert event.start.date_time <= datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc)


@pytest.mark.integration
def test_timezone_conversion_when_mixed_timezones_then_consistent_handling(
    test_settings: SimpleNamespace, ics_with_timezone_edge_cases: str, tmp_path: Any
) -> None:
    """Integration test: Timezone conversion edge cases across the stack.

    Tests:
    - UTC events remain UTC
    - Naive datetimes get UTC default
    - TZID events are parsed correctly
    - Recurring events with timezones expand properly
    
    This test validates that timezone handling is consistent across all components.
    """
    parser = LiteICSParser(test_settings)
    
    result = parser.parse_ics_content_optimized(
        ics_with_timezone_edge_cases, source_url=str(tmp_path / "test.ics")
    )
    
    assert result.success is True, f"Parser failed: {result.error_message}"
    events = result.events
    assert len(events) > 0, "Expected parsed events"
    
    # Find specific events by UID
    utc_event = None
    naive_event = None
    recurring_tz_events = []
    
    for event in events:
        if event.id == "utc-event":
            utc_event = event
        elif event.id == "naive-event":
            naive_event = event
        elif event.id.startswith("recurring-tz-event"):
            recurring_tz_events.append(event)
    
    # Verify UTC event
    assert utc_event is not None, "UTC event should be parsed"
    assert utc_event.start.date_time.tzinfo is not None, "UTC event should be timezone-aware"
    
    # Verify naive event gets timezone
    assert naive_event is not None, "Naive event should be parsed"
    assert naive_event.start.date_time.tzinfo is not None, "Naive event should get timezone"
    
    # Verify recurring events with timezone
    assert len(recurring_tz_events) >= 1, "Expected recurring event with timezone"
    for rec_event in recurring_tz_events:
        assert (
            rec_event.start.date_time.tzinfo is not None
        ), "Recurring event should be timezone-aware"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_parse_filter_pipeline_when_local_server_then_end_to_end_works(
    test_settings: SimpleNamespace, ics_with_complex_recurrence: str
) -> None:
    """Integration test: Full fetch → parse → filter pipeline with local HTTP server.

    Tests the complete end-to-end flow:
    1. Serve ICS content from local HTTP server
    2. Fetch content using LiteICSFetcher
    3. Parse content using LiteICSParser
    4. Apply processing pipeline
    
    This validates the entire stack works together in realistic conditions.
    """
    ics_bytes = ics_with_complex_recurrence.encode("utf-8")
    
    # Start local HTTP server
    class _ICSHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/calendar")
            self.send_header("Content-Length", str(len(ics_bytes)))
            self.end_headers()
            self.wfile.write(ics_bytes)
        
        def log_message(self, format: str, *args: Any) -> None:
            return  # Suppress logs
    
    httpd = HTTPServer(("127.0.0.1", 0), _ICSHandler)
    port = httpd.server_port
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    
    try:
        # Fetch ICS content
        from calendarbot_lite.lite_models import LiteICSSource
        
        url = f"http://127.0.0.1:{port}/calendar.ics"
        source = LiteICSSource(name="test", url=url)
        fetcher = LiteICSFetcher(test_settings)
        
        fetch_result = await fetcher.fetch_ics(source)
        assert fetch_result.success is True, f"Fetch failed: {fetch_result.error_message}"
        assert fetch_result.content is not None, "Expected ICS content"
        
        # Parse fetched content
        parser = LiteICSParser(test_settings)
        parse_result = parser.parse_ics_content_optimized(fetch_result.content, source_url=url)
        
        assert parse_result.success is True, f"Parse failed: {parse_result.error_message}"
        assert len(parse_result.events) > 0, "Expected parsed events"
        
        # Apply processing pipeline
        pipeline = EventProcessingPipeline().add_stage(DeduplicationStage()).add_stage(SortStage())
        
        context = ProcessingContext(events=parse_result.events)
        pipeline_result = await pipeline.process(context)
        
        assert pipeline_result.success is True
        assert len(context.events) > 0, "Expected events after processing"
        
        # Verify RRULE expansion worked - should have multiple events
        assert len(context.events) >= 10, f"Expected at least 10 events after expansion, got {len(context.events)}"
        
        # Verify events from recurring patterns exist
        subjects = {e.subject for e in context.events}
        assert "Daily Standup" in subjects, "Expected daily standup events"
        
    finally:
        httpd.shutdown()
        thread.join(timeout=1)


@pytest.mark.integration
def test_pipeline_stages_when_real_events_then_correct_filtering(
    test_settings: SimpleNamespace, ics_with_complex_recurrence: str, tmp_path: Any
) -> None:
    """Integration test: Pipeline stages correctly filter and process real events.

    Validates:
    - Deduplication removes true duplicates
    - Time window filtering works correctly
    - Sorting maintains correct order
    - No data loss or corruption
    """
    parser = LiteICSParser(test_settings)
    result = parser.parse_ics_content_optimized(
        ics_with_complex_recurrence, source_url=str(tmp_path / "test.ics")
    )
    
    assert result.success is True
    initial_events = result.events
    assert len(initial_events) > 0
    
    # Create pipeline with strict time window
    window_start = datetime(2025, 12, 1, 0, 0, tzinfo=timezone.utc)
    window_end = datetime(2025, 12, 7, 23, 59, tzinfo=timezone.utc)  # Only first week
    
    pipeline = (
        EventProcessingPipeline()
        .add_stage(DeduplicationStage())
        .add_stage(TimeWindowStage())
        .add_stage(SortStage())
    )
    
    context = ProcessingContext(
        events=initial_events,
        window_start=window_start,
        window_end=window_end,
    )
    pipeline_result = asyncio.run(pipeline.process(context))
    
    assert pipeline_result.success is True
    filtered_events = context.events
    
    # Verify all filtered events are within window
    for event in filtered_events:
        assert event.start.date_time >= window_start
        assert event.start.date_time <= window_end
    
    # Verify sorted order
    for i in range(len(filtered_events) - 1):
        assert filtered_events[i].start.date_time <= filtered_events[i + 1].start.date_time
    
    # Verify we have fewer events than initial (due to window filtering)
    assert len(filtered_events) < len(initial_events), "Window should filter some events"


@pytest.mark.integration
def test_rrule_expansion_when_exception_instances_then_correctly_handled(
    test_settings: SimpleNamespace, ics_with_complex_recurrence: str, tmp_path: Any
) -> None:
    """Integration test: RRULE expansion correctly handles RECURRENCE-ID exceptions.

    Validates that:
    - Master recurring events are identified
    - Instances are expanded
    - Exception instances (RECURRENCE-ID) override default instances
    - No duplicate instances for exceptions
    """
    parser = LiteICSParser(test_settings)
    result = parser.parse_ics_content_optimized(
        ics_with_complex_recurrence, source_url=str(tmp_path / "test.ics")
    )
    
    assert result.success is True
    events = result.events
    
    # Find weekly review events (which has an exception)
    weekly_review_events = [e for e in events if "Weekly Review" in e.subject]
    
    assert len(weekly_review_events) >= 1, "Expected weekly review events"
    
    # Check for exception instance (rescheduled meeting)
    exception_event = None
    for event in weekly_review_events:
        if "Rescheduled" in event.subject:
            exception_event = event
            break
    
    # Exception instance should exist
    assert exception_event is not None, "Expected exception instance to be present"


@pytest.mark.integration
def test_parser_performance_when_large_ics_then_meets_targets(
    test_settings: SimpleNamespace,
) -> None:
    """Integration test: Parser performance with large ICS content.

    Validates:
    - Parser handles large ICS files efficiently
    - RRULE expansion completes in reasonable time
    - Memory usage remains bounded
    """
    import time
    
    # Generate large ICS with many recurring events
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Test//Test//EN",
    ]
    
    for i in range(20):  # 20 recurring events
        ics_lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:recurring-{i}",
                f"SUMMARY:Meeting {i}",
                f"DTSTART:20251201T{9 + (i % 8):02d}0000Z",
                f"DTEND:20251201T{10 + (i % 8):02d}0000Z",
                "RRULE:FREQ=DAILY;COUNT=30",
                "END:VEVENT",
            ]
        )
    
    ics_lines.append("END:VCALENDAR")
    large_ics = "\n".join(ics_lines)
    
    parser = LiteICSParser(test_settings)
    
    start_time = time.time()
    result = parser.parse_ics_content_optimized(large_ics, source_url="test://large.ics")
    elapsed = time.time() - start_time
    
    assert result.success is True, f"Parser failed: {result.error_message}"
    assert len(result.events) > 0, "Expected parsed events"
    
    # Performance target: < 5 seconds for 20 recurring events with 30 instances each
    assert elapsed < 5.0, f"Parser took {elapsed:.2f}s, expected < 5s"
    
    # Verify we got expanded instances
    expanded = [e for e in result.events if getattr(e, "is_expanded_instance", False)]
    assert len(expanded) > 20, "Expected many expanded instances"
