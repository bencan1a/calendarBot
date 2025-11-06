"""
Unit tests for calendarbot_lite.lite_rrule_expander.RRuleWorkerPool

Covers:
- basic RRULE expansion for DAILY/COUNT
- EXDATE exclusion handling
- honoring expansion limits (COUNT)
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from calendarbot_lite.calendar.lite_models import LiteEventStatus
from calendarbot_lite.calendar.lite_rrule_expander import RRuleWorkerPool

pytestmark = [pytest.mark.unit, pytest.mark.fast]


class DummySettings:
    rrule_worker_concurrency = 1
    max_occurrences_per_rule = 100
    expansion_days_window = 10
    expansion_time_budget_ms_per_rule = 1000
    expansion_yield_frequency = 10


@pytest.mark.asyncio
async def test_expand_event_to_list_daily_count_three() -> None:
    """test_expand_event_to_list_daily_count_three"""
    settings = DummySettings()
    pool = RRuleWorkerPool(settings)

    # Create a simple master_event as SimpleNamespace with required attributes
    start_dt = datetime(2025, 1, 1, 9, 0, tzinfo=UTC)
    end_dt = start_dt + timedelta(hours=1)
    master = SimpleNamespace()
    master.start = SimpleNamespace(date_time=start_dt, time_zone="UTC")
    master.end = SimpleNamespace(date_time=end_dt, time_zone="UTC")
    master.id = "master-1"
    master.subject = "Daily Standup"
    master.body_preview = ""
    master.is_all_day = False
    master.show_as = LiteEventStatus.BUSY
    master.is_cancelled = False
    master.is_organizer = True
    master.location = None
    master.is_online_meeting = False
    master.online_meeting_url = None
    master.last_modified_date_time = None

    rrule = "FREQ=DAILY;COUNT=3"
    instances = await pool.expand_event_to_list(master, rrule, exdates=None)  # type: ignore[arg-type]
    assert isinstance(instances, list)
    assert len(instances) == 3
    # Verify successive starts are 1 day apart
    starts = [inst.start.date_time for inst in instances]
    assert starts[0] == start_dt.replace(tzinfo=UTC)
    assert starts[1] == (start_dt + timedelta(days=1)).replace(tzinfo=UTC)


@pytest.mark.asyncio
async def test_expand_event_respects_exdate_exclusion() -> None:
    """test_expand_event_respects_exdate_exclusion"""
    settings = DummySettings()
    pool = RRuleWorkerPool(settings)

    start_dt = datetime(2025, 2, 1, 9, 0, tzinfo=UTC)
    end_dt = start_dt + timedelta(hours=1)
    master = SimpleNamespace()
    master.start = SimpleNamespace(date_time=start_dt, time_zone="UTC")
    master.end = SimpleNamespace(date_time=end_dt, time_zone="UTC")
    master.id = "master-2"
    master.subject = "Weekly Sync"
    master.body_preview = ""
    master.is_all_day = False
    master.show_as = LiteEventStatus.BUSY
    master.is_cancelled = False
    master.is_organizer = True
    master.location = None
    master.is_online_meeting = False
    master.online_meeting_url = None
    master.last_modified_date_time = None

    # RRULE daily count 5 but exclude the 3rd day
    rrule = "FREQ=DAILY;COUNT=5"
    exdate = [(start_dt + timedelta(days=2)).strftime("%Y%m%dT%H%M%SZ")]
    instances = await pool.expand_event_to_list(master, rrule, exdates=exdate)  # type: ignore[arg-type]
    # Expect 4 instances because one was excluded
    assert len(instances) == 4
    # Ensure excluded date not present
    excluded_dt = (start_dt + timedelta(days=2)).replace(tzinfo=UTC)
    starts = {inst.start.date_time for inst in instances}
    assert excluded_dt not in starts


@pytest.mark.asyncio
async def test_old_weekly_recurring_event_shows_future_occurrences(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that a weekly recurring event created 6 months ago still shows future occurrences.

    This tests the fix for the RRULE expansion window bug where old recurring events
    would hit max_occurrences limit before reaching current dates.
    """
    settings = DummySettings()
    # Use reasonable limits to simulate real-world conditions
    settings.max_occurrences_per_rule = 250
    settings.expansion_days_window = 365
    pool = RRuleWorkerPool(settings)

    # Mock current time to be 2025-11-05 (as per test environment)
    mock_now = datetime(2025, 11, 5, 10, 0, 0, tzinfo=UTC)
    monkeypatch.setenv("CALENDARBOT_TEST_TIME", mock_now.isoformat())

    # Create a weekly standup that started 6 months ago (2025-05-05)
    start_dt = datetime(2025, 5, 5, 9, 0, tzinfo=UTC)
    end_dt = start_dt + timedelta(hours=1)
    master = SimpleNamespace()
    master.start = SimpleNamespace(date_time=start_dt, time_zone="UTC")
    master.end = SimpleNamespace(date_time=end_dt, time_zone="UTC")
    master.id = "master-old-weekly"
    master.subject = "Weekly Standup"
    master.body_preview = ""
    master.is_all_day = False
    master.show_as = LiteEventStatus.BUSY
    master.is_cancelled = False
    master.is_organizer = True
    master.location = None
    master.is_online_meeting = False
    master.online_meeting_url = None
    master.last_modified_date_time = None

    # Weekly recurring event (no end date - infinite series)
    rrule = "FREQ=WEEKLY;BYDAY=MO"
    instances = await pool.expand_event_to_list(master, rrule, exdates=None)  # type: ignore[arg-type]

    # Should get instances - verify we have recent/future occurrences
    assert len(instances) > 0, "Should have expanded instances"

    # Find instances in the near future (next 7 days from mock_now)
    future_start = mock_now - timedelta(days=7)  # Include this week
    future_end = mock_now + timedelta(days=14)  # Next 2 weeks

    future_instances = [
        inst for inst in instances
        if future_start <= inst.start.date_time <= future_end
    ]

    # Should have at least 2 upcoming Monday occurrences
    assert len(future_instances) >= 2, (
        f"Expected at least 2 future instances but got {len(future_instances)}. "
        f"Total instances: {len(instances)}, "
        f"Instance dates: {[inst.start.date_time for inst in instances[:5]]}"
    )

    # Verify instances are on Mondays
    for inst in future_instances:
        assert inst.start.date_time.weekday() == 0, f"Expected Monday but got {inst.start.date_time.strftime('%A')}"


@pytest.mark.asyncio
async def test_very_old_daily_recurring_event_with_max_occurrences(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that a daily recurring event from over 1 year ago still shows current occurrences.

    With max_occurrences=250, a daily event from 1+ year ago would generate 365+ occurrences
    and hit the limit before reaching today. The fix should start expansion from a recent date.
    """
    settings = DummySettings()
    settings.max_occurrences_per_rule = 250
    settings.expansion_days_window = 365
    pool = RRuleWorkerPool(settings)

    # Mock current time to be 2025-11-05
    mock_now = datetime(2025, 11, 5, 10, 0, 0, tzinfo=UTC)
    monkeypatch.setenv("CALENDARBOT_TEST_TIME", mock_now.isoformat())

    # Create a daily standup that started over 1 year ago (2024-01-01)
    start_dt = datetime(2024, 1, 1, 9, 0, tzinfo=UTC)
    end_dt = start_dt + timedelta(hours=1)
    master = SimpleNamespace()
    master.start = SimpleNamespace(date_time=start_dt, time_zone="UTC")
    master.end = SimpleNamespace(date_time=end_dt, time_zone="UTC")
    master.id = "master-very-old-daily"
    master.subject = "Daily Standup"
    master.body_preview = ""
    master.is_all_day = False
    master.show_as = LiteEventStatus.BUSY
    master.is_cancelled = False
    master.is_organizer = True
    master.location = None
    master.is_online_meeting = False
    master.online_meeting_url = None
    master.last_modified_date_time = None

    # Daily recurring event (infinite series)
    rrule = "FREQ=DAILY"
    instances = await pool.expand_event_to_list(master, rrule, exdates=None)  # type: ignore[arg-type]

    # Should hit max_occurrences limit
    assert len(instances) <= 250, f"Should not exceed max_occurrences: {len(instances)}"

    # CRITICAL: Should have instances from today and near future
    # With the fix, we start from (now - 7 days), so we should get instances for the next ~243 days
    today_start = mock_now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today_start + timedelta(days=1)

    recent_instances = [
        inst for inst in instances
        if today_start <= inst.start.date_time < tomorrow
    ]

    assert len(recent_instances) >= 1, (
        f"Expected at least 1 instance for today but got {len(recent_instances)}. "
        f"Total instances: {len(instances)}, "
        f"First instance: {instances[0].start.date_time if instances else 'None'}, "
        f"Last instance: {instances[-1].start.date_time if instances else 'None'}"
    )

    # Verify all instances are in a reasonable time range (not all ancient history)
    oldest_allowed = mock_now - timedelta(days=30)  # Allow up to 30 days in past
    newest_allowed = mock_now + timedelta(days=365)  # Up to 1 year in future

    out_of_range = [
        inst for inst in instances
        if inst.start.date_time < oldest_allowed or inst.start.date_time > newest_allowed
    ]

    assert len(out_of_range) == 0, (
        f"Found {len(out_of_range)} instances outside reasonable range. "
        f"Oldest allowed: {oldest_allowed}, Newest allowed: {newest_allowed}. "
        f"Out of range dates: {[inst.start.date_time for inst in out_of_range[:5]]}"
    )
