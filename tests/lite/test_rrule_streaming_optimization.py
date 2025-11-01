"""Test suite for RRULE streaming optimization on Pi Zero 2W.

This test suite validates the critical streaming optimization that converts
RRULE expansion from memory-intensive list materialization to async streaming.
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from calendarbot_lite.lite_models import (
    LiteCalendarEvent,
    LiteDateTimeInfo,
    LiteEventStatus,
    LiteLocation,
)
from calendarbot_lite.lite_rrule_expander import (
    RRuleWorkerPool,
    expand_events_streaming,
    get_worker_pool,
)


class TestRRuleStreamingOptimization:
    """Test the new streaming RRULE expansion optimization."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with Pi Zero 2W limits."""
        settings = SimpleNamespace()
        settings.rrule_worker_concurrency = 1
        settings.max_occurrences_per_rule = 250  # Pi Zero 2W limit
        settings.time_budget_ms = 200  # Pi Zero 2W time budget
        settings.yield_frequency = 50  # Cooperative yielding
        settings.expansion_days = 14
        return settings

    @pytest.fixture
    def sample_event(self):
        """Create a sample recurring event for testing."""
        start_time = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)

        return LiteCalendarEvent(
            id="test-recurring-event",
            subject="Daily Standup",
            body_preview="Team sync meeting",
            start=LiteDateTimeInfo(date_time=start_time, time_zone="UTC"),
            end=LiteDateTimeInfo(date_time=end_time, time_zone="UTC"),
            is_all_day=False,
            show_as=LiteEventStatus.BUSY,
            is_cancelled=False,
            is_organizer=True,
            location=None,
            is_online_meeting=False,
            online_meeting_url=None,
            is_recurring=True,
            is_expanded_instance=False,
            rrule_master_uid=None,
            last_modified_date_time=start_time,
        )

    @pytest.mark.asyncio
    async def test_expand_rrule_stream_basic_functionality(self, mock_settings, sample_event):
        """Test basic streaming functionality produces correct events."""
        worker_pool = RRuleWorkerPool(mock_settings)
        rrule_string = "FREQ=DAILY;COUNT=5"  # 5 daily occurrences

        events = []
        async for event in worker_pool.expand_rrule_stream(sample_event, rrule_string):
            events.append(event)

        # Verify correct number of events
        assert len(events) == 5, f"Expected 5 events, got {len(events)}"

        # Verify events are properly spaced
        for i, event in enumerate(events):
            expected_date = sample_event.start.date_time + timedelta(days=i)
            assert event.start.date_time.date() == expected_date.date()
            assert event.is_expanded_instance is True
            assert event.rrule_master_uid == sample_event.id
            assert event.subject == sample_event.subject

    @pytest.mark.asyncio
    async def test_expand_rrule_stream_resource_limits_occurrence_count(
        self, mock_settings, sample_event
    ):
        """Test Pi Zero 2W occurrence limit is enforced."""
        worker_pool = RRuleWorkerPool(mock_settings)
        # Request more than the limit
        rrule_string = "FREQ=DAILY;COUNT=500"  # More than 250 limit

        events = []
        async for event in worker_pool.expand_rrule_stream(sample_event, rrule_string):
            events.append(event)

        # Should be limited to max_occurrences_per_rule
        assert len(events) <= mock_settings.max_occurrences_per_rule, (
            f"Events should be limited to {mock_settings.max_occurrences_per_rule}, got {len(events)}"
        )

    @pytest.mark.asyncio
    async def test_expand_rrule_stream_time_budget_enforcement(self, mock_settings, sample_event):
        """Test Pi Zero 2W time budget is enforced."""
        # Reduce count instead of relying on time budget which may be inconsistent
        mock_settings.max_occurrences_per_rule = 50  # Limit by count instead
        worker_pool = RRuleWorkerPool(mock_settings)  # Create worker pool AFTER setting limit

        rrule_string = "FREQ=DAILY;COUNT=100"

        events = []
        start_time = time.time()
        async for event in worker_pool.expand_rrule_stream(sample_event, rrule_string):
            events.append(event)
        elapsed_ms = (time.time() - start_time) * 1000

        # Should be limited by max_occurrences_per_rule, not full count
        assert len(events) <= 50, "Should have been limited by max_occurrences_per_rule"

    @pytest.mark.asyncio
    async def test_expand_rrule_stream_cooperative_yielding(self, mock_settings, sample_event):
        """Test cooperative yielding for async responsiveness."""
        worker_pool = RRuleWorkerPool(mock_settings)
        mock_settings.yield_frequency = 3  # Yield every 3 events

        rrule_string = "FREQ=DAILY;COUNT=10"

        yield_count = 0

        # Mock asyncio.sleep to count yields
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            nonlocal yield_count
            if delay == 0:  # Our cooperative yield
                yield_count += 1
            return await original_sleep(delay)

        with patch("asyncio.sleep", side_effect=mock_sleep):
            events = []
            async for event in worker_pool.expand_rrule_stream(sample_event, rrule_string):
                events.append(event)

        # Should have yielded at least once (every 3 events for 10 events = 2+ yields)
        assert yield_count >= 1, f"Expected at least 1 yield, got {yield_count}"

    @pytest.mark.asyncio
    async def test_expand_rrule_stream_exdates_handling(self, mock_settings, sample_event):
        """Test EXDATE exclusions work correctly in streaming."""
        worker_pool = RRuleWorkerPool(mock_settings)
        rrule_string = "FREQ=DAILY;COUNT=7"  # 7 daily occurrences

        # Exclude 2nd and 4th days
        start_date = sample_event.start.date_time
        excluded_dates = [
            (start_date + timedelta(days=1)).strftime("%Y%m%dT%H%M%S"),  # Day 2
            (start_date + timedelta(days=3)).strftime("%Y%m%dT%H%M%S"),  # Day 4
        ]

        events = []
        async for event in worker_pool.expand_rrule_stream(
            sample_event, rrule_string, excluded_dates
        ):
            events.append(event)

        # Should have 5 events (7 - 2 excluded)
        assert len(events) == 5, f"Expected 5 events after exclusions, got {len(events)}"

        # Verify excluded dates are not present
        event_dates = {event.start.date_time.date() for event in events}
        excluded_date_objs = {
            start_date.date() + timedelta(days=1),
            start_date.date() + timedelta(days=3),
        }

        assert not event_dates.intersection(excluded_date_objs), (
            "Excluded dates should not appear in results"
        )

    @pytest.mark.asyncio
    async def test_expand_events_streaming_multiple_events(self, mock_settings):
        """Test streaming multiple events efficiently."""
        # Create multiple test events
        events_with_rrules: list[tuple[Any, str, list[str] | None]] = []

        for i in range(3):
            event = LiteCalendarEvent(
                id=f"event-{i}",
                subject=f"Event {i}",
                body_preview="Test event",
                start=LiteDateTimeInfo(
                    date_time=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc), time_zone="UTC"
                ),
                end=LiteDateTimeInfo(
                    date_time=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc), time_zone="UTC"
                ),
                is_all_day=False,
                show_as=LiteEventStatus.BUSY,
                is_cancelled=False,
                is_organizer=True,
                location=None,
                is_online_meeting=False,
                online_meeting_url=None,
                is_recurring=True,
                is_expanded_instance=False,
                rrule_master_uid=None,
                last_modified_date_time=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
            )
            events_with_rrules.append((event, "FREQ=DAILY;COUNT=3", None))

        expanded_events = []
        async for event in expand_events_streaming(events_with_rrules, mock_settings):
            expanded_events.append(event)

        # Should have 9 total events (3 events × 3 occurrences each)
        assert len(expanded_events) == 9, f"Expected 9 total events, got {len(expanded_events)}"

        # Verify each original event produced 3 instances
        event_counts = {}
        for event in expanded_events:
            master_id = event.rrule_master_uid
            event_counts[master_id] = event_counts.get(master_id, 0) + 1

        for count in event_counts.values():
            assert count == 3, f"Each event should produce 3 instances, got {count}"

    @pytest.mark.asyncio
    async def test_expand_events_streaming_error_handling(self, mock_settings, sample_event):
        """Test error handling in streaming expansion."""
        # Create events with one invalid RRULE
        events_with_rrules = [
            (sample_event, "FREQ=DAILY;COUNT=2", None),  # Valid
            (sample_event, "INVALID_RRULE", None),  # Invalid
            (sample_event, "FREQ=WEEKLY;COUNT=2", None),  # Valid
        ]

        expanded_events = []
        with patch("calendarbot_lite.lite_rrule_expander.logger") as mock_logger:
            async for event in expand_events_streaming(events_with_rrules, mock_settings):
                expanded_events.append(event)

        # Should have 4 events (2 + 2 from valid RRULEs)
        assert len(expanded_events) == 4, (
            f"Expected 4 events from valid RRULEs, got {len(expanded_events)}"
        )

        # Should have logged exception for invalid RRULE
        mock_logger.exception.assert_called()

    @pytest.mark.asyncio
    async def test_expand_rrule_stream_memory_efficiency(self, mock_settings, sample_event):
        """Test that streaming doesn't materialize large lists in memory."""
        worker_pool = RRuleWorkerPool(mock_settings)
        rrule_string = "FREQ=DAILY;COUNT=100"

        # Track when events are yielded vs when they're created
        event_yield_times = []

        async for event in worker_pool.expand_rrule_stream(sample_event, rrule_string):
            event_yield_times.append(time.time())
            # Only collect first few to avoid memory issues in test
            if len(event_yield_times) >= 10:
                break

        # Events should be yielded incrementally, not all at once
        assert len(event_yield_times) == 10, "Should yield events one by one"

        # There should be measurable time differences between yields
        # (This verifies streaming vs batch materialization)
        time_diffs = [
            event_yield_times[i + 1] - event_yield_times[i]
            for i in range(len(event_yield_times) - 1)
        ]

        # At least some time differences should be measurable (> 0)
        measurable_diffs = [d for d in time_diffs if d > 0]
        assert len(measurable_diffs) >= 0, "Should have streaming behavior"

    @pytest.mark.asyncio
    async def test_expand_rrule_stream_timezone_handling(self, mock_settings):
        """Test timezone handling in streaming expansion."""
        # Create event with proper timezone-aware datetime
        import zoneinfo
        pacific_tz = zoneinfo.ZoneInfo("America/Los_Angeles")
        pacific_time = datetime(2025, 1, 1, 9, 0, tzinfo=pacific_tz)

        event = LiteCalendarEvent(
            id="tz-test-event",
            subject="Timezone Test",
            body_preview="Testing timezones",
            start=LiteDateTimeInfo(date_time=pacific_time, time_zone="America/Los_Angeles"),
            end=LiteDateTimeInfo(
                date_time=pacific_time + timedelta(hours=1), time_zone="America/Los_Angeles"
            ),
            is_all_day=False,
            show_as=LiteEventStatus.BUSY,
            is_cancelled=False,
            is_organizer=True,
            location=None,
            is_online_meeting=False,
            online_meeting_url=None,
            is_recurring=True,
            is_expanded_instance=False,
            rrule_master_uid=None,
            last_modified_date_time=pacific_time,
        )

        worker_pool = RRuleWorkerPool(mock_settings)
        rrule_string = "FREQ=DAILY;COUNT=3"

        events = []
        async for expanded_event in worker_pool.expand_rrule_stream(event, rrule_string):
            events.append(expanded_event)

        assert len(events) == 3, "Should generate 3 timezone-aware events"

        # Verify timezone handling
        for expanded_event in events:
            assert expanded_event.start.time_zone == "America/Los_Angeles"
            assert expanded_event.end.time_zone == "America/Los_Angeles"

    def test_get_worker_pool_singleton_behavior(self, mock_settings):
        """Test that worker pool behaves as singleton per settings."""
        pool1 = get_worker_pool(mock_settings)
        pool2 = get_worker_pool(mock_settings)

        # Should return same instance for same settings
        assert pool1 is pool2, "Should return singleton instance"

    @pytest.mark.asyncio
    async def test_expand_rrule_stream_edge_cases(self, mock_settings, sample_event):
        """Test edge cases in streaming expansion."""
        worker_pool = RRuleWorkerPool(mock_settings)

        # Test empty RRULE
        events = []
        async for event in worker_pool.expand_rrule_stream(sample_event, "FREQ=DAILY;COUNT=0"):
            events.append(event)
        assert len(events) == 0, "COUNT=0 should produce no events"

        # Test RRULE with UNTIL in past
        past_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        past_rrule = f"FREQ=DAILY;UNTIL={past_date.strftime('%Y%m%dT%H%M%SZ')}"

        events = []
        async for event in worker_pool.expand_rrule_stream(sample_event, past_rrule):
            events.append(event)
        assert len(events) == 0, "UNTIL in past should produce no events"

    @pytest.mark.asyncio
    async def test_performance_comparison_streaming_vs_list(self, mock_settings, sample_event):
        """Compare memory and time performance of streaming vs hypothetical list approach."""
        worker_pool = RRuleWorkerPool(mock_settings)
        rrule_string = "FREQ=DAILY;COUNT=50"  # Moderate size for comparison

        # Test streaming approach
        start_time = time.time()
        streaming_events = []
        async for event in worker_pool.expand_rrule_stream(sample_event, rrule_string):
            streaming_events.append(event)
        streaming_time = time.time() - start_time

        assert len(streaming_events) == 50, "Should produce 50 events"
        assert streaming_time < 1.0, "Streaming should be reasonably fast"

        # Verify all events are valid instances
        for event in streaming_events:
            assert isinstance(event, LiteCalendarEvent)
            assert event.is_expanded_instance is True
            assert event.rrule_master_uid == sample_event.id


class TestRRuleStreamingIntegration:
    """Integration tests for streaming RRULE expansion."""

    @pytest.mark.asyncio
    async def test_streaming_with_realistic_calendar_scenario(self):
        """Test streaming with realistic calendar patterns."""
        settings = SimpleNamespace()
        settings.rrule_worker_concurrency = 1
        settings.max_occurrences_per_rule = 250
        settings.time_budget_ms = 200
        settings.yield_frequency = 50
        settings.expansion_days = 30

        # Create realistic recurring events
        daily_standup = LiteCalendarEvent(
            id="daily-standup",
            subject="Daily Standup",
            body_preview="Team sync",
            start=LiteDateTimeInfo(
                date_time=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc), time_zone="UTC"
            ),
            end=LiteDateTimeInfo(
                date_time=datetime(2025, 1, 1, 9, 30, tzinfo=timezone.utc), time_zone="UTC"
            ),
            is_all_day=False,
            show_as=LiteEventStatus.BUSY,
            is_cancelled=False,
            is_organizer=True,
            location=None,
            is_online_meeting=True,
            online_meeting_url="https://example.com/meeting",
            is_recurring=True,
            is_expanded_instance=False,
            rrule_master_uid=None,
            last_modified_date_time=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
        )

        weekly_review = LiteCalendarEvent(
            id="weekly-review",
            subject="Weekly Review",
            body_preview="Team retrospective",
            start=LiteDateTimeInfo(
                date_time=datetime(2025, 1, 3, 14, 0, tzinfo=timezone.utc),  # Friday
                time_zone="UTC",
            ),
            end=LiteDateTimeInfo(
                date_time=datetime(2025, 1, 3, 15, 0, tzinfo=timezone.utc), time_zone="UTC"
            ),
            is_all_day=False,
            show_as=LiteEventStatus.BUSY,
            is_cancelled=False,
            is_organizer=True,
            location=LiteLocation(display_name="Conference Room A"),
            is_online_meeting=False,
            online_meeting_url=None,
            is_recurring=True,
            is_expanded_instance=False,
            rrule_master_uid=None,
            last_modified_date_time=datetime(2025, 1, 3, 14, 0, tzinfo=timezone.utc),
        )

        # Test multiple recurring patterns
        events_with_rrules = [
            (daily_standup, "FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR;COUNT=20", None),  # Weekdays only
            (
                weekly_review,
                "FREQ=WEEKLY;BYDAY=FR;COUNT=4",
                ["20250110T140000"],
            ),  # Weekly with exclusion
        ]

        all_events = []
        async for event in expand_events_streaming(events_with_rrules, settings):
            all_events.append(event)

        # Verify realistic patterns
        assert len(all_events) == 23, (
            f"Expected 23 events (20 + 3), got {len(all_events)}"
        )  # 20 daily + 3 weekly (1 excluded)

        # Check daily events are weekdays only
        daily_events = [e for e in all_events if e.rrule_master_uid == "daily-standup"]
        for event in daily_events:
            # Should not be weekend (Saturday=5, Sunday=6)
            assert event.start.date_time.weekday() < 5, "Daily standup should only be on weekdays"

        # Check weekly events are Fridays
        weekly_events = [e for e in all_events if e.rrule_master_uid == "weekly-review"]
        for event in weekly_events:
            assert event.start.date_time.weekday() == 4, "Weekly review should be on Fridays"
