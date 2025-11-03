"""
Unit tests for calendarbot_lite.lite_rrule_expander.RRuleWorkerPool

Covers:
- basic RRULE expansion for DAILY/COUNT
- EXDATE exclusion handling
- honoring expansion limits (COUNT)
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from calendarbot_lite.lite_models import LiteEventStatus
from calendarbot_lite.lite_rrule_expander import RRuleWorkerPool

pytestmark = [pytest.mark.unit, pytest.mark.fast]


class DummySettings:
    rrule_worker_concurrency = 1
    max_occurrences_per_rule = 100
    expansion_days_window = 10
    expansion_time_budget_ms_per_rule = 1000
    expansion_yield_frequency = 10


UTC = timezone.utc


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
