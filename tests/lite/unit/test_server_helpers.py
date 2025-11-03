"""Unit tests for calendarbot_lite.server helper functions.

These tests cover _format_duration_spoken, _serialize_iso and
_compute_last_meeting_end_for_today. They are deterministic and fast.
"""

from __future__ import annotations

import datetime
import zoneinfo
from typing import Any

import pytest

from calendarbot_lite import server
from calendarbot_lite.lite_models import LiteCalendarEvent, LiteDateTimeInfo

pytestmark = pytest.mark.unit


def make_lite_event(subject: str) -> LiteCalendarEvent:
    """Helper to create LiteCalendarEvent for focus time tests."""
    now = datetime.datetime.now(datetime.timezone.utc)
    return LiteCalendarEvent(
        id="test-id",
        subject=subject,
        start=LiteDateTimeInfo(date_time=now, time_zone="UTC"),
        end=LiteDateTimeInfo(date_time=now + datetime.timedelta(hours=1), time_zone="UTC"),
    )


def test_is_focus_time_event_when_exact_keyword_match_then_true():
    """Focus time keywords should be detected exactly."""
    focus_subjects = [
        "focus time",
        "Focus Time",
        "FOCUS TIME",
        "focus",
        "deep work",
        "thinking time",
        "planning time",
    ]

    for subject in focus_subjects:
        event = make_lite_event(subject)
        assert server._is_focus_time_event(event), f"Event with subject '{subject}' should be focus time"


def test_is_focus_time_event_when_keyword_in_longer_subject_then_true():
    """Focus time keywords within longer subjects should be detected."""
    focus_subjects = [
        "Morning focus time block",
        "focus time - project planning",
        "Team deep work session",
        "Personal thinking time",
        "Planning time for Q4",
        "focus session",
    ]

    for subject in focus_subjects:
        event = make_lite_event(subject)
        assert server._is_focus_time_event(event), f"Event with subject '{subject}' should be focus time"


def test_is_focus_time_event_when_non_focus_subject_then_false():
    """Non-focus time events should not be detected as focus time."""
    non_focus_subjects = [
        "Team standup",
        "Client meeting",
        "1:1 with manager",
        "Project review",
        "Lunch",
        "All hands meeting",
        "discussion meeting",  # does not contain focus keywords
        "work session",  # partial but not complete keyword
        "development sync",
        "code review",
    ]

    for subject in non_focus_subjects:
        event = make_lite_event(subject)
        assert not server._is_focus_time_event(event), f"Event with subject '{subject}' should not be focus time"


def test_is_focus_time_event_when_missing_subject_then_false():
    """Events with empty subject should not be considered focus time."""
    event = make_lite_event("")
    assert not server._is_focus_time_event(event)


def test_is_focus_time_event_when_case_insensitive_then_detected():
    """Focus time detection should be case insensitive."""
    mixed_case_subjects = [
        "Focus Time",
        "DEEP WORK",
        "Thinking Time",
        "PLANNING TIME",
        "Morning FOCUS session",
    ]

    for subject in mixed_case_subjects:
        event = make_lite_event(subject)
        assert server._is_focus_time_event(event), f"Event with subject '{subject}' should be focus time"


def test_format_duration_spoken_seconds_under_minute_then_seconds():
    """seconds < 60 should be spoken in seconds."""
    assert server._format_duration_spoken(0) == "in 0 seconds"
    assert server._format_duration_spoken(30) == "in 30 seconds"
    assert server._format_duration_spoken(59) == "in 59 seconds"


def test_format_duration_spoken_exact_minute_then_1_minute():
    """60 seconds should be spoken as 1 minute."""
    assert server._format_duration_spoken(60) == "in 1 minute"


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (61, "in 1 minute"),
        (90, "in 1 minute"),
        (119, "in 1 minute"),
        (3599, "in 59 minutes"),
    ],
)
def test_format_duration_spoken_minutes_range_then_expected(seconds, expected):
    assert server._format_duration_spoken(seconds) == expected


def test_format_duration_spoken_exact_hour_then_1_hour():
    assert server._format_duration_spoken(3600) == "in 1 hour"


def test_format_duration_spoken_hours_with_minutes_then_expected():
    """Hours and minutes combinations are formatted correctly."""
    assert server._format_duration_spoken(3661) == "in 1 hour and 1 minute"
    # 2 hours and 30 minutes -> 9000 seconds
    assert server._format_duration_spoken(9000) == "in 2 hours and 30 minutes"


def test_format_duration_spoken_negative_then_in_the_past():
    assert server._format_duration_spoken(-10) == "in the past"


def test_serialize_iso_none_then_none():
    assert server._serialize_iso(None) is None


def test_serialize_iso_naive_datetime_then_assume_utc():
    dt = datetime.datetime(2025, 10, 28, 12, 0, 0)
    assert server._serialize_iso(dt) == "2025-10-28T12:00:00Z"


def test_serialize_iso_utc_datetime_then_z_suffix():
    dt = datetime.datetime(2025, 10, 28, 12, 0, tzinfo=datetime.timezone.utc)
    assert server._serialize_iso(dt) == "2025-10-28T12:00:00Z"


def test_serialize_iso_non_utc_timezone_then_converted_to_z():
    tokyo = zoneinfo.ZoneInfo("Asia/Tokyo")
    dt = datetime.datetime(2025, 10, 28, 21, 0, tzinfo=tokyo)
    # 21:00 JST is 12:00Z
    assert server._serialize_iso(dt) == "2025-10-28T12:00:00Z"


def test_serialize_iso_pacific_timezone_then_converted_to_z():
    pacific = zoneinfo.ZoneInfo("America/Los_Angeles")
    dt = datetime.datetime(2025, 10, 28, 5, 0, tzinfo=pacific)
    # 05:00 PDT (-7) is 12:00Z
    assert server._serialize_iso(dt) == "2025-10-28T12:00:00Z"


def make_event(start_utc: datetime.datetime, duration_seconds: int | None, meeting_id: str | None = None) -> dict[str, Any]:
    """Helper to create event dicts expected by _compute_last_meeting_end_for_today."""
    ev: dict[str, Any] = {"start": start_utc}
    if duration_seconds is not None:
        ev["duration_seconds"] = duration_seconds
    if meeting_id is not None:
        ev["meeting_id"] = meeting_id
    return ev


def test_compute_last_meeting_end_for_today_empty_window_then_no_meetings(test_timezone, monkeypatch):
    """Empty window returns has_meetings_today False and no ISO times."""
    # Freeze "now" to 2025-10-28T12:00:00-07:00 (Pacific)
    monkeypatch.setenv("CALENDARBOT_TEST_TIME", "2025-10-28T12:00:00-07:00")
    result = server._compute_last_meeting_end_for_today(test_timezone, (), None)
    assert result["has_meetings_today"] is False
    assert result["last_meeting_end_iso"] is None
    assert result["last_meeting_end_local_iso"] is None


def test_compute_last_meeting_end_for_today_events_today_and_other_days_then_latest_selected(test_timezone, monkeypatch):
    """Only today's events are considered and the latest end is returned."""
    monkeypatch.setenv("CALENDARBOT_TEST_TIME", "2025-10-28T12:00:00-07:00")
    tz = zoneinfo.ZoneInfo(test_timezone)
    # Event earlier today at 09:00 local -> 16:00Z
    start1_local = datetime.datetime(2025, 10, 28, 9, 0, tzinfo=tz)
    start1_utc = start1_local.astimezone(datetime.timezone.utc)
    ev1 = make_event(start1_utc, 1800, "a")
    # Event later today at 13:00 local -> 20:00Z
    start2_local = datetime.datetime(2025, 10, 28, 13, 0, tzinfo=tz)
    start2_utc = start2_local.astimezone(datetime.timezone.utc)
    ev2 = make_event(start2_utc, 3600, "b")
    # Event tomorrow should be ignored
    start_tom_local = datetime.datetime(2025, 10, 29, 10, 0, tzinfo=tz)
    start_tom_utc = start_tom_local.astimezone(datetime.timezone.utc)
    ev3 = make_event(start_tom_utc, 1800, "c")

    window = (ev1, ev2, ev3)
    result = server._compute_last_meeting_end_for_today(test_timezone, window, None)
    assert result["has_meetings_today"] is True
    # Last meeting end is ev2 start + 3600 = start2_utc + 3600
    expected_end_iso = server._serialize_iso(start2_utc + datetime.timedelta(seconds=3600))
    assert result["last_meeting_end_iso"] == expected_end_iso
    # Local iso should be in the requested timezone
    assert result["last_meeting_end_local_iso"].startswith("2025-10-28")


def test_compute_last_meeting_end_for_today_with_skipped_store_honors_skip(test_timezone, monkeypatch):
    """Events flagged as skipped by skipped_store are ignored."""
    monkeypatch.setenv("CALENDARBOT_TEST_TIME", "2025-10-28T12:00:00-07:00")
    tz = zoneinfo.ZoneInfo(test_timezone)
    start_local = datetime.datetime(2025, 10, 28, 14, 0, tzinfo=tz)
    start_utc = start_local.astimezone(datetime.timezone.utc)
    ev_skip = make_event(start_utc, 1800, "skip-me")
    ev_keep = make_event(start_utc + datetime.timedelta(hours=1), 1800, "keep-me")

    class SkippedStoreMock:
        def is_skipped(self, meeting_id: str) -> bool:
            return meeting_id == "skip-me"

    window = (ev_skip, ev_keep)
    skipped = SkippedStoreMock()
    result = server._compute_last_meeting_end_for_today(test_timezone, window, skipped)
    assert result["has_meetings_today"] is True
    # The latest end should come from ev_keep only
    expected = server._serialize_iso(
        ev_keep["start"] + datetime.timedelta(seconds=ev_keep["duration_seconds"])
    )
    assert result["last_meeting_end_iso"] == expected


def test_compute_last_meeting_end_for_today_skipped_store_raises_then_continue(test_timezone, monkeypatch):
    """If skipped_store.is_skipped raises, processing continues and meeting is kept."""
    monkeypatch.setenv("CALENDARBOT_TEST_TIME", "2025-10-28T12:00:00-07:00")
    tz = zoneinfo.ZoneInfo(test_timezone)
    start_local = datetime.datetime(2025, 10, 28, 15, 0, tzinfo=tz)
    start_utc = start_local.astimezone(datetime.timezone.utc)
    ev = make_event(start_utc, 1800, "err-me")

    class BrokenSkippedStore:
        def is_skipped(self, meeting_id: str) -> bool:
            raise RuntimeError("boom")

    result = server._compute_last_meeting_end_for_today(
        test_timezone, (ev,), BrokenSkippedStore()
    )
    assert result["has_meetings_today"] is True
    assert result["last_meeting_end_iso"] == server._serialize_iso(
        ev["start"] + datetime.timedelta(seconds=ev["duration_seconds"])
    )


def test_compute_last_meeting_end_for_today_missing_duration_uses_fallback(test_timezone, monkeypatch):
    """Events without duration_seconds use 1-hour fallback."""
    monkeypatch.setenv("CALENDARBOT_TEST_TIME", "2025-10-28T12:00:00-07:00")
    tz = zoneinfo.ZoneInfo(test_timezone)
    start_local = datetime.datetime(2025, 10, 28, 16, 0, tzinfo=tz)
    start_utc = start_local.astimezone(datetime.timezone.utc)
    ev = make_event(start_utc, None, "no-duration")
    result = server._compute_last_meeting_end_for_today(test_timezone, (ev,), None)
    assert result["has_meetings_today"] is True
    # fallback end = start + 3600
    assert result["last_meeting_end_iso"] == server._serialize_iso(start_utc + datetime.timedelta(hours=1))
