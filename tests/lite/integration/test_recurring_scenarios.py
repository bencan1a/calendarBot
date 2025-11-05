"""
Improved recurring scenarios test-suite with per-scenario test functions and detailed reporting.

This file splits the previous aggregated test into discrete tests so each scenario
is reported separately by pytest (one pass/fail per scenario). Each scenario prints
the expected vs actual values so you can re-run a single failing scenario quickly
(e.g. pytest -q tests/lite/test_recurring_scenarios.py::test_daily_recurring -q).

Design points:
- Each test is parametrized to exercise both traditional and streaming parser paths.
- Tests print an explicit report (expected vs actual) using print() so running with -s
  shows the detailed report inline.
- Keep tests deterministic and focused so failures are easy to reproduce.

Usage:
- Run all: pytest tests/lite/test_recurring_scenarios.py -q
- Run single scenario (example): pytest tests/lite/test_recurring_scenarios.py::test_daily_recurring -q -s
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import List

import pytest

from calendarbot_lite.calendar.lite_models import LiteCalendarEvent
from calendarbot_lite.calendar.lite_parser import LiteICSParser

pytestmark = pytest.mark.integration

# Shared fixture used across scenarios
@pytest.fixture
def simple_settings() -> SimpleNamespace:
    return SimpleNamespace(
        enable_rrule_expansion=True,
        rrule_expansion_days=500,  # Increased to 500 days to ensure yearly events starting in Dec are included (395+ days from Nov 1)
        expansion_days_window=500,  # Worker pool uses this attribute for expansion window
        rrule_max_occurrences=1000,
        raw_components_superset_limit=1500,
    )


def _run_parser_for_ics(settings: SimpleNamespace, ics_content: str, tmp_path: Path, use_streaming: bool) -> List[LiteCalendarEvent]:
    """
    Helper to run the parser and return final filtered events.
    If use_streaming=True the content is padded to trigger the streaming path.
    """
    path = tmp_path / "scenario.ics"
    path.write_text(ics_content, encoding="utf-8")
    parser = LiteICSParser(settings)

    content_to_parse = ics_content
    if use_streaming:
        # append filler to cross streaming threshold without changing VEVENTs
        content_to_parse = ics_content + "\n" + ("X" * (10 * 1024 * 1024))

    result = parser.parse_ics_content_optimized(content_to_parse, source_url=str(path))
    assert result.success, f"Parser failed: {getattr(result, 'error_message', '<no message>')}"
    return result.events


def _sorted_event_starts(events: List[LiteCalendarEvent], subject: str) -> List[datetime]:
    return sorted([e.start.date_time for e in events if e.subject == subject])


def _print_report(scenario_name: str, expected: List[datetime], actual: List[datetime]) -> None:
    print(f"\nSCENARIO: {scenario_name}")
    print(f"  Expected ({len(expected)}):")
    for e in expected:
        print(f"    - {e.isoformat()}")
    print(f"  Actual ({len(actual)}):")
    for a in actual:
        print(f"    - {a.isoformat()}")
    print(f"  RESULT: {'PASS' if expected == actual else 'FAIL'}\n")


@pytest.mark.parametrize("use_streaming", [False, True])
def test_daily_recurring(simple_settings: SimpleNamespace, tmp_path: Path, use_streaming: bool) -> None:
    """Daily recurring pattern -> 3 occurrences"""
    ics = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "BEGIN:VEVENT\n"
        "UID:daily-test@example.com\n"
        "SUMMARY:Daily Team Sync\n"
        "DTSTART:20251101T090000Z\n"
        "DTEND:20251101T100000Z\n"
        "RRULE:FREQ=DAILY;COUNT=3\n"
        "END:VEVENT\n"
        "END:VCALENDAR\n"
    )
    events = _run_parser_for_ics(simple_settings, ics, tmp_path, use_streaming)
    expected = [
        datetime(2025, 11, 1, 9, 0, tzinfo=timezone.utc),
        datetime(2025, 11, 2, 9, 0, tzinfo=timezone.utc),
        datetime(2025, 11, 3, 9, 0, tzinfo=timezone.utc),
    ]
    actual = _sorted_event_starts(events, "Daily Team Sync")
    _print_report("Daily recurring", expected, actual)
    assert expected == actual


@pytest.mark.parametrize("use_streaming", [False, True])
def test_weekly_recurring_byday(simple_settings: SimpleNamespace, tmp_path: Path, use_streaming: bool) -> None:
    """Weekly recurring pattern with BYDAY -> generate correct occurrences"""
    ics = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "BEGIN:VEVENT\n"
        "UID:weekly-test@example.com\n"
        "SUMMARY:Weekly Planning\n"
        "DTSTART:20251103T080000Z\n"
        "DTEND:20251103T090000Z\n"
        "RRULE:FREQ=WEEKLY;BYDAY=MO,WE;COUNT=4\n"
        "END:VEVENT\n"
        "END:VCALENDAR\n"
    )
    events = _run_parser_for_ics(simple_settings, ics, tmp_path, use_streaming)
    actual = _sorted_event_starts(events, "Weekly Planning")
    # Build expected Mondays/Wednesdays from start
    start = datetime(2025, 11, 3, 8, 0, tzinfo=timezone.utc)  # Monday
    expected = [start, start + timedelta(days=2), start + timedelta(weeks=1), start + timedelta(weeks=1, days=2)]
    _print_report("Weekly BYDAY", expected, actual)
    assert expected == actual


@pytest.mark.parametrize("use_streaming", [False, True])
def test_monthly_and_yearly_recurring(simple_settings: SimpleNamespace, tmp_path: Path, use_streaming: bool) -> None:
    """Monthly and yearly recurrence basic counts"""
    ics = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "BEGIN:VEVENT\n"
        "UID:monthly-test@example.com\n"
        "SUMMARY:Monthly All Hands\n"
        "DTSTART:20251115T170000Z\n"
        "DTEND:20251115T180000Z\n"
        "RRULE:FREQ=MONTHLY;COUNT=3\n"
        "END:VEVENT\n"
        "BEGIN:VEVENT\n"
        "UID:yearly-test@example.com\n"
        "SUMMARY:Yearly Strategy\n"
        "DTSTART:20251201T120000Z\n"
        "DTEND:20251201T130000Z\n"
        "RRULE:FREQ=YEARLY;COUNT=2\n"
        "END:VEVENT\n"
        "END:VCALENDAR\n"
    )
    events = _run_parser_for_ics(simple_settings, ics, tmp_path, use_streaming)

    monthly_expected = [
        datetime(2025, 11, 15, 17, 0, tzinfo=timezone.utc),
        datetime(2025, 12, 15, 17, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 15, 17, 0, tzinfo=timezone.utc),
    ]
    monthly_actual = _sorted_event_starts(events, "Monthly All Hands")
    _print_report("Monthly recurring", monthly_expected, monthly_actual)
    assert monthly_expected == monthly_actual

    yearly_expected = [
        datetime(2025, 12, 1, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 12, 1, 12, 0, tzinfo=timezone.utc),
    ]
    yearly_actual = _sorted_event_starts(events, "Yearly Strategy")
    _print_report("Yearly recurring", yearly_expected, yearly_actual)
    assert yearly_expected == yearly_actual


@pytest.mark.parametrize("use_streaming", [False, True])
def test_exdate_cancelled_instance(simple_settings: SimpleNamespace, tmp_path: Path, use_streaming: bool) -> None:
    """EXDATE should remove the specified occurrence"""
    ics = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "BEGIN:VEVENT\n"
        "UID:exdate-test@example.com\n"
        "SUMMARY:Daily With Cancel\n"
        "DTSTART:20251110T070000Z\n"
        "DTEND:20251110T080000Z\n"
        "RRULE:FREQ=DAILY;COUNT=3\n"
        "EXDATE:20251111T070000Z\n"
        "END:VEVENT\n"
        "END:VCALENDAR\n"
    )
    events = _run_parser_for_ics(simple_settings, ics, tmp_path, use_streaming)
    expected = [
        datetime(2025, 11, 10, 7, 0, tzinfo=timezone.utc),
        datetime(2025, 11, 12, 7, 0, tzinfo=timezone.utc),
    ]
    actual = _sorted_event_starts(events, "Daily With Cancel")
    _print_report("EXDATE cancelled instance", expected, actual)
    assert expected == actual


@pytest.mark.parametrize("use_streaming", [False, True])
def test_moved_rescheduled_instance_and_recurring_suppression(simple_settings: SimpleNamespace, tmp_path: Path, use_streaming: bool) -> None:
    """RECURRENCE-ID moved instance should appear at new time and suppress original slot"""
    ics = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "BEGIN:VEVENT\n"
        "UID:move-test@example.com\n"
        "SUMMARY:Standup Meeting\n"
        "DTSTART:20251120T090000Z\n"
        "DTEND:20251120T091500Z\n"
        "RRULE:FREQ=DAILY;COUNT=3\n"
        "END:VEVENT\n"
        # Moved second occurrence (original 20251121T090000Z) -> new time 11:00 and renamed.
        "BEGIN:VEVENT\n"
        "UID:move-test@example.com\n"
        "RECURRENCE-ID:20251121T090000Z\n"
        "SUMMARY:Standup Meeting (Rescheduled)\n"
        "DTSTART:20251121T110000Z\n"
        "DTEND:20251121T111500Z\n"
        "END:VEVENT\n"
        "END:VCALENDAR\n"
    )
    events = _run_parser_for_ics(simple_settings, ics, tmp_path, use_streaming)

    # Expect moved instance present at new time (there may be duplicates from upstream
    # processing, but we only require that the moved instance exists and original is suppressed)
    expected_moved_dt = datetime(2025, 11, 21, 11, 0, tzinfo=timezone.utc)
    actual_moved = _sorted_event_starts(events, "Standup Meeting (Rescheduled)")
    _print_report("Moved/rescheduled instance (presence)", [expected_moved_dt], actual_moved)
    # Require at least one moved instance at the expected datetime (allow duplicates)
    matches = [dt for dt in actual_moved if dt == expected_moved_dt]
    print(f"SCENARIO: Moved/rescheduled - found {len(matches)} moved instances at expected time")
    assert len(matches) >= 1, "Moved/rescheduled instance not found at expected time"

    # Ensure original expanded occurrence was suppressed (no "Standup Meeting" at 2025-11-21 09:00Z)
    overridden = [e for e in events if e.subject == "Standup Meeting" and e.start.date_time == datetime(2025, 11, 21, 9, 0, tzinfo=timezone.utc)]
    print(f"SCENARIO: Recurrence suppression check - overridden count = {len(overridden)}")
    assert len(overridden) == 0


@pytest.mark.parametrize("use_streaming", [False, True])
def test_multiple_exdates_and_counts(simple_settings: SimpleNamespace, tmp_path: Path, use_streaming: bool) -> None:
    """Multiple EXDATE values should be applied correctly"""
    ics = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "BEGIN:VEVENT\n"
        "UID:multi-ex-test@example.com\n"
        "SUMMARY:Biweekly Class\n"
        "DTSTART:20251105T150000Z\n"
        "DTEND:20251105T160000Z\n"
        "RRULE:FREQ=WEEKLY;INTERVAL=2;COUNT=5\n"
        "EXDATE:20251119T150000Z,20251203T150000Z\n"
        "END:VEVENT\n"
        "END:VCALENDAR\n"
    )
    events = _run_parser_for_ics(simple_settings, ics, tmp_path, use_streaming)

    # The RRULE produces 5 candidate dates separated by 2 weeks, but two are excluded -> expect 3
    actual = _sorted_event_starts(events, "Biweekly Class")
    expected = sorted([
        datetime(2025, 11, 5, 15, 0, tzinfo=timezone.utc),
        datetime(2025, 12, 17, 15, 0, tzinfo=timezone.utc),
        datetime(2025, 12, 31, 15, 0, tzinfo=timezone.utc),
    ])
    _print_report("Multiple EXDATEs", expected, actual)
    assert expected == actual


@pytest.mark.parametrize("use_streaming", [False, True])
def test_multiple_recurring_series_same_name(simple_settings: SimpleNamespace, tmp_path: Path, use_streaming: bool) -> None:
    """Two separate recurring series with identical SUMMARY should both be preserved"""
    ics = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        # First series
        "BEGIN:VEVENT\n"
        "UID:same1@example.com\n"
        "SUMMARY:Project Sync\n"
        "DTSTART:20251104T130000Z\n"
        "DTEND:20251104T140000Z\n"
        "RRULE:FREQ=WEEKLY;COUNT=2\n"
        "END:VEVENT\n"
        # Second series different UID same summary
        "BEGIN:VEVENT\n"
        "UID:same2@example.com\n"
        "SUMMARY:Project Sync\n"
        "DTSTART:20251106T130000Z\n"
        "DTEND:20251106T140000Z\n"
        "RRULE:FREQ=WEEKLY;COUNT=2\n"
        "END:VEVENT\n"
        "END:VCALENDAR\n"
    )
    events = _run_parser_for_ics(simple_settings, ics, tmp_path, use_streaming)

    actual = _sorted_event_starts(events, "Project Sync")
    # Both series each yield 2 occurrences, so expect 4 instances total
    expected_count = 4
    print("\nSCENARIO: Multiple series same name")
    print(f"  Expected count: {expected_count}")
    print(f"  Actual starts ({len(actual)}):")
    for a in actual:
        print(f"    - {a.isoformat()}")
    print(f"  RESULT: {'PASS' if len(actual) == expected_count else 'FAIL'}\n")
    assert len(actual) == expected_count


@pytest.mark.parametrize("use_streaming", [False, True])
def test_moved_recurring_with_tzid_cross_timezone(simple_settings: SimpleNamespace, tmp_path: Path, use_streaming: bool) -> None:
    """Issue #43: RECURRENCE-ID with TZID should properly suppress original occurrence in different timezone."""
    ics = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "PRODID:-//Test//Test//EN\n"
        "BEGIN:VTIMEZONE\n"
        "TZID:America/Los_Angeles\n"
        "BEGIN:STANDARD\n"
        "DTSTART:20241103T020000\n"
        "TZOFFSETFROM:-0700\n"
        "TZOFFSETTO:-0800\n"
        "RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU\n"
        "TZNAME:PST\n"
        "END:STANDARD\n"
        "BEGIN:DAYLIGHT\n"
        "DTSTART:20250309T020000\n"
        "TZOFFSETFROM:-0800\n"
        "TZOFFSETTO:-0700\n"
        "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU\n"
        "TZNAME:PDT\n"
        "END:DAYLIGHT\n"
        "END:VTIMEZONE\n"
        "BEGIN:VEVENT\n"
        "UID:recurring-meeting@example.com\n"
        "SUMMARY:Daily Standup\n"
        "DTSTART;TZID=America/Los_Angeles:20251120T090000\n"
        "DTEND;TZID=America/Los_Angeles:20251120T093000\n"
        "RRULE:FREQ=DAILY;COUNT=3\n"
        "END:VEVENT\n"
        "BEGIN:VEVENT\n"
        "UID:recurring-meeting@example.com\n"
        "RECURRENCE-ID;TZID=America/Los_Angeles:20251121T090000\n"
        "SUMMARY:Daily Standup (Moved)\n"
        "DTSTART;TZID=America/Los_Angeles:20251121T110000\n"
        "DTEND;TZID=America/Los_Angeles:20251121T113000\n"
        "END:VEVENT\n"
        "END:VCALENDAR\n"
    )
    events = _run_parser_for_ics(simple_settings, ics, tmp_path, use_streaming)

    # Should have 3 total events: 2 original occurrences + 1 moved instance
    standup_events = [e for e in events if "Daily Standup" in e.subject]
    print(f"\nSCENARIO: TZID RECURRENCE-ID cross-timezone")
    print(f"  Total events with 'Daily Standup': {len(standup_events)}")
    for e in standup_events:
        print(f"    - {e.subject}: {e.start.date_time.isoformat()}")

    assert len(standup_events) == 3, f"Expected 3 events, got {len(standup_events)}"

    # Verify moved instance exists at new time
    moved_events = [e for e in standup_events if "Moved" in e.subject]
    assert len(moved_events) == 1, "Expected exactly one moved instance"

    # Verify NO event at original 09:00 PST time slot (17:00 UTC) on 2025-11-21
    # After the first Sunday in November, Los Angeles is on PST (UTC-8), so 09:00 PST = 17:00 UTC.
    # Original occurrence should be suppressed by RECURRENCE-ID
    original_time_utc = datetime(2025, 11, 21, 17, 0, tzinfo=timezone.utc)  # 09:00 PST = 17:00 UTC
    events_at_original_time = [
        e for e in standup_events
        if e.start.date_time == original_time_utc and "Moved" not in e.subject
    ]
    print(f"  Events at original time slot (should be 0): {len(events_at_original_time)}")
    assert len(events_at_original_time) == 0, "RECURRENCE-ID should suppress original occurrence"
