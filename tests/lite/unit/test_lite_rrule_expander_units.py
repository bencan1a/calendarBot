"""
Unit tests for calendarbot_lite.lite_rrule_expander.LiteRRuleExpander.

Covers:
- parse_rrule_string()
- apply_exdates()
- generate_event_instances()

Tests are deterministic and fast. Use fixtures from tests/lite/conftest.py.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import List

import pytest

from calendarbot_lite.calendar.lite_models import LiteCalendarEvent, LiteDateTimeInfo, LiteEventStatus
from calendarbot_lite.calendar.lite_rrule_expander import (
    LiteRRuleExpander,
    LiteRRuleParseError,
)

pytestmark = pytest.mark.unit


def _build_master_event(start_dt: datetime, end_dt: datetime) -> LiteCalendarEvent:
    """Helper to construct a minimal LiteCalendarEvent for tests."""
    return LiteCalendarEvent(
        id="master-1",
        subject="Test event",
        body_preview="preview",
        start=LiteDateTimeInfo(date_time=start_dt, time_zone="UTC"),
        end=LiteDateTimeInfo(date_time=end_dt, time_zone="UTC"),
        is_all_day=False,
        show_as=LiteEventStatus.BUSY,
        is_cancelled=False,
        is_organizer=False,
        location=None,
        is_online_meeting=False,
        online_meeting_url=None,
        is_recurring=True,
        is_expanded_instance=False,
        last_modified_date_time=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
    )


@pytest.mark.parametrize(
    "rrule_str,expected_freq,expected_interval",
    [
        ("FREQ=DAILY;INTERVAL=1", "DAILY", 1),
        ("FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,WE", "WEEKLY", 2),
        ("FREQ=MONTHLY;COUNT=3", "MONTHLY", 1),
        ("FREQ=YEARLY;INTERVAL=5", "YEARLY", 5),
    ],
)
def test_parse_rrule_string_valid_various(rrule_str: str, expected_freq: str, expected_interval: int, simple_settings: SimpleNamespace) -> None:
    """parse_rrule_string should correctly parse common RRULE variants."""
    expander = LiteRRuleExpander(simple_settings)
    parsed = expander.parse_rrule_string(rrule_str)
    assert parsed["freq"] == expected_freq
    # interval defaults to 1 when not provided
    assert parsed.get("interval", 1) == expected_interval or parsed.get("interval") == expected_interval


def test_parse_rrule_string_with_until_and_count(simple_settings: SimpleNamespace) -> None:
    """UNTIL should be parsed into a datetime with UTC tz when suffixed with Z."""
    expander = LiteRRuleExpander(simple_settings)
    rrule = "FREQ=DAILY;UNTIL=20251028T120000Z;COUNT=10"
    parsed = expander.parse_rrule_string(rrule)
    assert parsed["freq"] == "DAILY"
    assert parsed["count"] == 10
    until_dt = parsed["until"]
    assert isinstance(until_dt, datetime)
    assert until_dt.tzinfo is not None
    assert until_dt == datetime(2025, 10, 28, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("bad_rrule", ["", "   ", "INTERVAL=2", "FREQ=;COUNT=2", "FREQ=DAILY;INTERVAL=bad"])
def test_parse_rrule_string_invalid_raises(bad_rrule: str, simple_settings: SimpleNamespace) -> None:
    """Malformed or missing RRULE components should raise LiteRRuleParseError."""
    expander = LiteRRuleExpander(simple_settings)
    with pytest.raises(LiteRRuleParseError):
        expander.parse_rrule_string(bad_rrule)


def test_apply_exdates_single_and_multiple(simple_settings: SimpleNamespace) -> None:
    """apply_exdates should remove matching occurrence datetimes within tolerance."""
    expander = LiteRRuleExpander(simple_settings)
    # Build occurrences: daily 2025-01-01..2025-01-05 UTC
    base = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)
    occurrences: List[datetime] = [base + timedelta(days=i) for i in range(5)]
    # Exclude 2025-01-03 (middle day)
    exdates = ["20250103T090000Z"]
    filtered = expander.apply_exdates(occurrences, exdates)
    assert len(filtered) == 4
    assert all(dt.day != 3 for dt in [d.astimezone(timezone.utc) for d in filtered])


def test_apply_exdates_with_timezone_tzid_format(simple_settings: SimpleNamespace, test_timezone: str) -> None:
    """EXDATEs with TZID=Pacific Standard Time should be parsed and matched."""
    expander = LiteRRuleExpander(simple_settings)
    # Occurrences in UTC corresponding to 2025-06-23 15:30 UTC (which is 08:30 PDT)
    occ = datetime(2025, 6, 23, 15, 30, tzinfo=timezone.utc)
    occurrences = [occ]
    # EXDATE in TZID format pointing to America/Los_Angeles 2025-06-23T08:30:00
    ex_tz_str = "TZID=Pacific Standard Time:20250623T083000"
    filtered = expander.apply_exdates(occurrences, [ex_tz_str])
    # The single occurrence should be excluded after timezone normalization
    assert filtered == []


def test_apply_exdates_no_op_on_empty_exdates(simple_settings: SimpleNamespace) -> None:
    """apply_exdates with no exdates should return original occurrences unchanged."""
    expander = LiteRRuleExpander(simple_settings)
    occ = datetime(2025, 2, 1, 10, 0, tzinfo=timezone.utc)
    occurrences = [occ]
    filtered = expander.apply_exdates(occurrences, None)
    assert filtered == occurrences


def test_generate_event_instances_creates_instances_with_duration_preserved(simple_settings: SimpleNamespace) -> None:
    """generate_event_instances should create instances preserving duration and master id link."""
    expander = LiteRRuleExpander(simple_settings)
    start = datetime(2025, 3, 1, 9, 0, tzinfo=timezone.utc)
    end = datetime(2025, 3, 1, 10, 0, tzinfo=timezone.utc)
    master = _build_master_event(start, end)
    # Two occurrences
    occ1 = datetime(2025, 3, 2, 9, 0, tzinfo=timezone.utc)
    occ2 = datetime(2025, 3, 3, 9, 0, tzinfo=timezone.utc)
    events = expander.generate_event_instances(master, [occ1, occ2])
    assert len(events) == 2
    for ev, occ in zip(events, [occ1, occ2]):
        # Duration preserved
        assert ev.end.date_time - ev.start.date_time == timedelta(hours=1)
        # rrule_master_uid preserved
        assert ev.rrule_master_uid == master.id
        # Instance id contains master id prefix
        assert ev.id.startswith(master.id)


def test_generate_event_instances_with_malformed_occurrence_raises(simple_settings: SimpleNamespace) -> None:
    """Passing a non-datetime in occurrences should raise an AttributeError/TypeError."""
    expander = LiteRRuleExpander(simple_settings)
    start = datetime(2025, 4, 1, 9, 0, tzinfo=timezone.utc)
    end = datetime(2025, 4, 1, 10, 0, tzinfo=timezone.utc)
    master = _build_master_event(start, end)
    # Intentionally provide a bad occurrence value
    with pytest.raises(Exception):
        expander.generate_event_instances(master, ["not-a-datetime"])  # type: ignore[arg-type,list-item]


@pytest.mark.smoke  # Critical path: RRULE expansion validation
def test_integration_parse_apply_generate(simple_settings: SimpleNamespace) -> None:
    """Integration flow: parse RRULE, remove EXDATEs, and generate instances deterministically."""
    expander = LiteRRuleExpander(simple_settings)
    # Use a simple weekly RRULE on Mondays for three occurrences
    rrule_str = "FREQ=WEEKLY;INTERVAL=1;BYDAY=MO;COUNT=3"
    parsed = expander.parse_rrule_string(rrule_str)
    assert parsed["freq"] == "WEEKLY"
    assert parsed["byday"] == ["MO"]
    # Create occurrences manually matching Mondays (avoid calling the internal generator)
    start = datetime(2025, 5, 5, 8, 0, tzinfo=timezone.utc)  # a Monday
    master = _build_master_event(start, start + timedelta(hours=1))
    occs = [start + timedelta(days=7 * i) for i in range(3)]
    # Exclude the second occurrence
    exdates = [occs[1].strftime("%Y%m%dT%H%M%SZ")]
    filtered = expander.apply_exdates(occs, exdates)
    assert len(filtered) == 2
    events = expander.generate_event_instances(master, filtered)
    assert len(events) == 2
    # Ensure generated instances match filtered datetimes
    generated_starts = [e.start.date_time for e in events]
    assert generated_starts == filtered
