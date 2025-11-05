"""
Integration tests for RRULE orchestration and full ICS parsing pipeline.

These tests exercise the real LiteICSParser + RRuleOrchestrator integration
to ensure RRULE expansion produces expanded instances and the parser
returns the expected combined events list.

Marked as integration because they exercise multiple components end-to-end.
"""

from textwrap import dedent
from types import SimpleNamespace

import pytest

from calendarbot_lite.calendar.lite_parser import LiteICSParser


@pytest.mark.integration
def test_rrule_orchestrator_expands_recurring_events(tmp_path):
    """End-to-end: parsing an ICS with an RRULE should produce expanded instances.

    The test constructs a small ICS with a daily RRULE (COUNT=3) and verifies
    that the parser returns at least one expanded instance (is_expanded_instance).
    """
    ics_content = dedent(
        """
        BEGIN:VCALENDAR
        VERSION:2.0
        BEGIN:VEVENT
        UID:test-rrule-1
        SUMMARY:Daily Meeting
        DTSTART:20251101T090000Z
        DTEND:20251101T100000Z
        RRULE:FREQ=DAILY;COUNT=3
        END:VEVENT
        END:VCALENDAR
        """
    )

    # Minimal settings required by the RRULE expander and parser
    settings = SimpleNamespace(
        rrule_worker_concurrency=1,
        max_occurrences_per_rule=1000,
        expansion_days_window=365,
        expansion_time_budget_ms_per_rule=200,
        expansion_yield_frequency=50,
        rrule_expansion_days=30,
        enable_rrule_expansion=True,
    )

    parser = LiteICSParser(settings)

    # Run the full optimized parse path (small content will use traditional parser)
    result = parser.parse_ics_content_optimized(ics_content, source_url=str(tmp_path / "test.ics"))

    assert result.success is True, f"Parser failed: {result.error_message}"
    events = result.events
    assert isinstance(events, list)

    # The parser should have expanded the daily RRULE (COUNT=3) into 3 event instances
    assert len(events) == 3, f"Expected 3 expanded instances from FREQ=DAILY;COUNT=3, got {len(events)}"
    
    # All events should be based on the same base UID (test-rrule-1)
    # The parser appends occurrence time + hash for uniqueness: test-rrule-1_20251101T090000_<hash>
    base_uid = "test-rrule-1"
    for event in events:
        assert event.id.startswith(base_uid), f"Expected ID to start with '{base_uid}', got {event.id}"
    
    # All events should have unique IDs (each instance gets unique ID)
    uids = {e.id for e in events}
    assert len(uids) == 3, f"Expected 3 unique IDs for 3 instances, got {len(uids)}"
    
    # All events should have the same summary
    summaries = {e.subject for e in events}
    assert summaries == {"Daily Meeting"}, f"Expected 'Daily Meeting', got {summaries}"
    
    # Verify the events are on consecutive days (daily recurrence)
    start_dates = sorted([e.start.date_time.date() for e in events])
    for i in range(1, len(start_dates)):
        delta = (start_dates[i] - start_dates[i-1]).days
        assert delta == 1, f"Expected consecutive daily occurrences, got {delta} days between events"
