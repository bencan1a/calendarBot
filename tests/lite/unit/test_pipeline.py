"""Tests for event processing pipeline architecture."""

from datetime import datetime, timezone

import pytest

from calendarbot_lite.calendar.lite_models import LiteAttendee, LiteCalendarEvent, LiteDateTimeInfo
from calendarbot_lite.domain.pipeline import EventProcessingPipeline, ProcessingContext, ProcessingResult
from calendarbot_lite.domain.pipeline_stages import (
    DeduplicationStage,
    EventLimitStage,
    SkippedEventsFilterStage,
    TimeWindowStage,
)

pytestmark = pytest.mark.unit


def create_test_event(
    event_id: str,
    subject: str,
    start_time: datetime,
    has_attendees: bool = False,
) -> LiteCalendarEvent:
    """Create a test event for pipeline testing."""
    return LiteCalendarEvent(
        id=event_id,  # Required field
        subject=subject,
        start=LiteDateTimeInfo(
            date_time=start_time,
            time_zone="UTC",
        ),
        end=LiteDateTimeInfo(
            date_time=start_time,
            time_zone="UTC",
        ),
        attendees=[LiteAttendee(name="Test User", email="test@example.com")] if has_attendees else None,
    )


class TestProcessingContext:
    """Test ProcessingContext dataclass."""

    def test_create_empty_context(self) -> None:
        """Test creating an empty processing context."""
        context = ProcessingContext()
        assert context.events == []
        assert context.rrule_expansion_days == 14
        assert context.event_window_size == 50

    def test_create_context_with_config(self) -> None:
        """Test creating context with custom configuration."""
        context = ProcessingContext(
            rrule_expansion_days=30,
            event_window_size=100,
            source_url="https://example.com/calendar.ics",
        )
        assert context.rrule_expansion_days == 30
        assert context.event_window_size == 100
        assert context.source_url == "https://example.com/calendar.ics"


class TestProcessingResult:
    """Test ProcessingResult dataclass."""

    def test_create_successful_result(self) -> None:
        """Test creating a successful result."""
        result = ProcessingResult(success=True, stage_name="TestStage")
        assert result.success is True
        assert result.warnings == []
        assert result.errors == []

    def test_add_warning(self) -> None:
        """Test adding a warning to result."""
        result = ProcessingResult(stage_name="TestStage")
        result.add_warning("Test warning")
        assert len(result.warnings) == 1
        assert "Test warning" in result.warnings

    def test_add_error_marks_as_failed(self) -> None:
        """Test that adding an error marks result as failed."""
        result = ProcessingResult(success=True, stage_name="TestStage")
        result.add_error("Test error")
        assert result.success is False
        assert len(result.errors) == 1
        assert "Test error" in result.errors


class TestDeduplicationStage:
    """Test deduplication stage."""

    @pytest.mark.asyncio
    async def test_deduplicate_events_with_same_id(self) -> None:
        """Test that duplicate events are removed."""
        event1 = create_test_event(
            "event-1", "Meeting", datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc)
        )
        event2 = create_test_event(
            "event-1", "Meeting", datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc),
            has_attendees=True
        )

        context = ProcessingContext(events=[event1, event2])
        stage = DeduplicationStage()
        result = await stage.process(context)

        assert result.success is True
        assert result.events_in == 2
        assert result.events_out == 1
        assert result.events_filtered == 1
        assert len(context.events) == 1
        # Should keep event with more info (attendees)
        assert context.events[0].attendees is not None

    @pytest.mark.asyncio
    async def test_no_duplicates(self) -> None:
        """Test that unique events are preserved."""
        event1 = create_test_event(
            "event-1", "Meeting 1", datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc)
        )
        event2 = create_test_event(
            "event-2", "Meeting 2", datetime(2025, 11, 1, 11, 0, tzinfo=timezone.utc)
        )

        context = ProcessingContext(events=[event1, event2])
        stage = DeduplicationStage()
        result = await stage.process(context)

        assert result.success is True
        assert result.events_in == 2
        assert result.events_out == 2
        assert result.events_filtered == 0
        assert len(context.events) == 2


class TestSkippedEventsFilterStage:
    """Test skipped events filter stage."""

    @pytest.mark.asyncio
    async def test_filter_skipped_events(self) -> None:
        """Test that skipped events are removed."""
        event1 = create_test_event(
            "event-1", "Meeting 1", datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc)
        )
        event2 = create_test_event(
            "event-2", "Meeting 2", datetime(2025, 11, 1, 11, 0, tzinfo=timezone.utc)
        )
        event3 = create_test_event(
            "event-3", "Meeting 3", datetime(2025, 11, 1, 12, 0, tzinfo=timezone.utc)
        )

        context = ProcessingContext(
            events=[event1, event2, event3],
            skipped_event_ids={"event-2"}
        )
        stage = SkippedEventsFilterStage()
        result = await stage.process(context)

        assert result.success is True
        assert result.events_in == 3
        assert result.events_out == 2
        assert result.events_filtered == 1
        assert len(context.events) == 2
        assert all(e.id != "event-2" for e in context.events)

    @pytest.mark.asyncio
    async def test_no_skipped_events(self) -> None:
        """Test behavior when no events are skipped."""
        event1 = create_test_event(
            "event-1", "Meeting 1", datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc)
        )
        event2 = create_test_event(
            "event-2", "Meeting 2", datetime(2025, 11, 1, 11, 0, tzinfo=timezone.utc)
        )

        context = ProcessingContext(events=[event1, event2])
        stage = SkippedEventsFilterStage()
        result = await stage.process(context)

        assert result.success is True
        assert result.events_in == 2
        assert result.events_out == 2
        assert result.events_filtered == 0  # No events filtered
        assert len(context.events) == 2


class TestTimeWindowStage:
    """Test time window filtering stage."""

    @pytest.mark.asyncio
    async def test_filter_events_by_time_window(self) -> None:
        """Test that events outside time window are filtered."""
        event1 = create_test_event(
            "event-1", "Past", datetime(2025, 11, 1, 8, 0, tzinfo=timezone.utc)
        )
        event2 = create_test_event(
            "event-2", "Present", datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc)
        )
        event3 = create_test_event(
            "event-3", "Future", datetime(2025, 11, 1, 14, 0, tzinfo=timezone.utc)
        )

        context = ProcessingContext(
            events=[event1, event2, event3],
            window_start=datetime(2025, 11, 1, 9, 0, tzinfo=timezone.utc),
            window_end=datetime(2025, 11, 1, 12, 0, tzinfo=timezone.utc),
        )
        stage = TimeWindowStage()
        result = await stage.process(context)

        assert result.success is True
        assert result.events_in == 3
        assert result.events_out == 1
        assert result.events_filtered == 2
        assert len(context.events) == 1
        assert context.events[0].subject == "Present"

    @pytest.mark.asyncio
    async def test_no_window_keeps_all_events(self) -> None:
        """Test that without a window, all events are kept."""
        event1 = create_test_event(
            "event-1", "Meeting 1", datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc)
        )
        event2 = create_test_event(
            "event-2", "Meeting 2", datetime(2025, 11, 1, 11, 0, tzinfo=timezone.utc)
        )

        context = ProcessingContext(events=[event1, event2])
        stage = TimeWindowStage()
        result = await stage.process(context)

        assert result.success is True
        assert result.events_out == 2


class TestEventLimitStage:
    """Test event limit stage."""

    @pytest.mark.asyncio
    async def test_limit_events_to_max(self) -> None:
        """Test that events are limited to maximum count and earliest events are kept."""
        # Create events with scrambled subject names to ensure we're testing time-based limiting
        events = [
            create_test_event(
                f"event-{i}", f"Meeting-{chr(90 - i)}",  # Z, Y, X, ... to avoid alphabetical matching
                datetime(2025, 11, 1, 10 + i, 0, tzinfo=timezone.utc)
            )
            for i in range(10)
        ]

        context = ProcessingContext(events=events, event_window_size=5)
        stage = EventLimitStage()
        result = await stage.process(context)

        assert result.success is True
        assert result.events_in == 10
        assert result.events_out == 5
        assert result.events_filtered == 5
        assert len(context.events) == 5

        # Verify the first 5 events (earliest by time) are kept
        assert context.events[0].id == "event-0"
        assert context.events[1].id == "event-1"
        assert context.events[2].id == "event-2"
        assert context.events[3].id == "event-3"
        assert context.events[4].id == "event-4"

        # Verify times are the earliest 5
        assert context.events[0].start.date_time == datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc)
        assert context.events[4].start.date_time == datetime(2025, 11, 1, 14, 0, tzinfo=timezone.utc)

        # Verify all events are in chronological order (like sort test does)
        for i in range(len(context.events) - 1):
            current_time = context.events[i].start.date_time
            next_time = context.events[i + 1].start.date_time
            assert current_time <= next_time, \
                f"Event {i} (ID: {context.events[i].id}) at {current_time} should be before " \
                f"event {i+1} (ID: {context.events[i+1].id}) at {next_time}"

        # Also verify the specific times for all 5 events (not just first and last)
        expected_times = [
            datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc),
            datetime(2025, 11, 1, 11, 0, tzinfo=timezone.utc),
            datetime(2025, 11, 1, 12, 0, tzinfo=timezone.utc),
            datetime(2025, 11, 1, 13, 0, tzinfo=timezone.utc),
            datetime(2025, 11, 1, 14, 0, tzinfo=timezone.utc),
        ]
        for i, expected_time in enumerate(expected_times):
            assert context.events[i].start.date_time == expected_time, \
                f"Event {i} should have time {expected_time}, got {context.events[i].start.date_time}"

    @pytest.mark.asyncio
    async def test_no_limit_if_under_max(self) -> None:
        """Test that events under limit are preserved."""
        events = [
            create_test_event(
                f"event-{i}", f"Meeting {i}",
                datetime(2025, 11, 1, 10 + i, 0, tzinfo=timezone.utc)
            )
            for i in range(3)
        ]

        context = ProcessingContext(events=events, event_window_size=10)
        stage = EventLimitStage()
        result = await stage.process(context)

        assert result.success is True
        assert result.events_out == 3
        assert result.events_filtered == 0


class TestEventProcessingPipeline:
    """Test complete pipeline orchestration."""

    @pytest.mark.asyncio
    async def test_empty_pipeline(self) -> None:
        """Test that empty pipeline succeeds."""
        pipeline = EventProcessingPipeline()
        context = ProcessingContext()
        result = await pipeline.process(context)

        assert result.success is True
        assert result.events == []

    @pytest.mark.asyncio
    async def test_pipeline_with_multiple_stages(self) -> None:
        """Test pipeline with multiple stages and verify each stage contributes.

        This test verifies that:
        1. Deduplication stage removes duplicates (4 -> 3 events)
        2. Skipped filter stage removes skipped events (3 -> 2 events)
        3. Event limit stage has no effect if already at/below limit (2 -> 2 events)
        4. Final result contains only the expected events
        """
        # Create test data with duplicates, skipped events, and extra events
        events = [
            create_test_event(
                "event-1", "Meeting 1", datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc)
            ),
            create_test_event(
                "event-1", "Meeting 1", datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc),
                has_attendees=True
            ),  # Duplicate
            create_test_event(
                "event-2", "Skipped", datetime(2025, 11, 1, 11, 0, tzinfo=timezone.utc)
            ),  # Will be skipped
            create_test_event(
                "event-3", "Meeting 3", datetime(2025, 11, 1, 12, 0, tzinfo=timezone.utc)
            ),
        ]

        # Verify initial state
        assert len(events) == 4, "Should start with 4 events"

        # To verify each stage's contribution, we need to run stages individually
        # then compare with full pipeline run

        # Step 1: Run deduplication stage only
        context_dedupe = ProcessingContext(events=events.copy(), skipped_event_ids={"event-2"})
        dedupe_stage = DeduplicationStage()
        dedupe_result = await dedupe_stage.process(context_dedupe)

        assert dedupe_result.success is True
        assert dedupe_result.events_in == 4
        assert dedupe_result.events_out == 3, "Deduplication should remove 1 duplicate (4 -> 3)"
        assert dedupe_result.events_filtered == 1
        assert len(context_dedupe.events) == 3

        # Step 2: Run skipped filter stage after deduplication
        filter_stage = SkippedEventsFilterStage()
        filter_result = await filter_stage.process(context_dedupe)

        assert filter_result.success is True
        assert filter_result.events_in == 3
        assert filter_result.events_out == 2, "Filter should remove 1 skipped event (3 -> 2)"
        assert filter_result.events_filtered == 1
        assert len(context_dedupe.events) == 2
        assert all(e.id != "event-2" for e in context_dedupe.events), "Skipped event should be removed"

        # Step 3: Run event limit stage (should have no effect since already at 2)
        limit_stage = EventLimitStage(max_events=2)
        limit_result = await limit_stage.process(context_dedupe)

        assert limit_result.success is True
        assert limit_result.events_in == 2
        assert limit_result.events_out == 2, "Limit stage should not remove events (already at limit)"
        assert limit_result.events_filtered == 0
        assert len(context_dedupe.events) == 2

        # Now run the full pipeline and verify same result
        pipeline = EventProcessingPipeline()
        pipeline.add_stage(DeduplicationStage())
        pipeline.add_stage(SkippedEventsFilterStage())
        pipeline.add_stage(EventLimitStage(max_events=2))

        context_full = ProcessingContext(events=events.copy(), skipped_event_ids={"event-2"})
        result_full = await pipeline.process(context_full)

        # Verify pipeline succeeded
        assert result_full.success is True
        assert result_full.events_out == 2

        # Verify final state matches stage-by-stage result
        assert len(context_full.events) == 2  # Limited to 2
        assert all(e.id != "event-2" for e in context_full.events)  # Skipped filtered

        # Verify duplicate was removed (event-1 should appear only once)
        event_ids = [e.id for e in context_full.events]
        assert event_ids.count("event-1") == 1, "Duplicate event-1 should be removed"
        assert "event-3" in event_ids, "Non-duplicate, non-skipped event should remain"

    @pytest.mark.asyncio
    async def test_pipeline_builder_pattern(self) -> None:
        """Test that add_stage returns self for chaining."""
        pipeline = (
            EventProcessingPipeline()
            .add_stage(DeduplicationStage())
            .add_stage(SkippedEventsFilterStage())
            .add_stage(EventLimitStage())
        )

        assert len(pipeline.stages) == 3

    @pytest.mark.asyncio
    async def test_pipeline_repr(self) -> None:
        """Test pipeline string representation."""
        pipeline = EventProcessingPipeline()
        pipeline.add_stage(DeduplicationStage())
        pipeline.add_stage(SkippedEventsFilterStage())

        repr_str = repr(pipeline)
        assert "Deduplication" in repr_str
        assert "SkippedEventsFilter" in repr_str


class TestSortStage:
    """Test sort stage."""

    @pytest.mark.asyncio
    async def test_sort_events_by_start_time(self) -> None:
        """Test that events are sorted by start time."""
        from calendarbot_lite.domain.pipeline_stages import SortStage

        # Create events with scrambled subject names that DON'T match chronological order
        # This ensures we're testing actual datetime sorting, not accidental subject ordering
        event_zebra = create_test_event(
            "event-3", "Zebra Meeting", datetime(2025, 11, 1, 14, 0, tzinfo=timezone.utc)
        )
        event_apple = create_test_event(
            "event-1", "Apple Meeting", datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc)
        )
        event_monkey = create_test_event(
            "event-2", "Monkey Meeting", datetime(2025, 11, 1, 12, 0, tzinfo=timezone.utc)
        )

        # Add events in random order (not time order, not alphabetical order)
        context = ProcessingContext(events=[event_zebra, event_apple, event_monkey])
        stage = SortStage()
        result = await stage.process(context)

        assert result.success is True
        assert result.events_out == 3
        assert len(context.events) == 3

        # Verify events are sorted by actual start time (not subject)
        assert context.events[0].subject == "Apple Meeting"
        assert context.events[1].subject == "Monkey Meeting"
        assert context.events[2].subject == "Zebra Meeting"

        # Verify datetime values are in ascending order
        assert context.events[0].start.date_time == datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc)
        assert context.events[1].start.date_time == datetime(2025, 11, 1, 12, 0, tzinfo=timezone.utc)
        assert context.events[2].start.date_time == datetime(2025, 11, 1, 14, 0, tzinfo=timezone.utc)

        # Verify times are strictly ascending
        for i in range(len(context.events) - 1):
            assert context.events[i].start.date_time <= context.events[i + 1].start.date_time

    @pytest.mark.asyncio
    async def test_sort_empty_list(self) -> None:
        """Test sorting empty event list."""
        from calendarbot_lite.domain.pipeline_stages import SortStage

        context = ProcessingContext(events=[])
        stage = SortStage()
        result = await stage.process(context)

        assert result.success is True
        assert result.events_out == 0
        assert len(context.events) == 0
