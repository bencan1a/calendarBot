"""Tests for event processing pipeline architecture."""

import pytest
from datetime import datetime, timezone
from types import SimpleNamespace

from calendarbot_lite.lite_models import LiteCalendarEvent, LiteDateTimeInfo
from calendarbot_lite.pipeline import ProcessingContext, ProcessingResult, EventProcessingPipeline
from calendarbot_lite.pipeline_stages import (
    DeduplicationStage,
    SkippedEventsFilterStage,
    TimeWindowStage,
    EventLimitStage,
)


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
        attendees=[{"name": "Test User", "email": "test@example.com"}] if has_attendees else None,
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
        """Test that events are limited to maximum count."""
        events = [
            create_test_event(
                f"event-{i}", f"Meeting {i}",
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
        """Test pipeline with multiple stages."""
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

        # Build pipeline
        pipeline = EventProcessingPipeline()
        pipeline.add_stage(DeduplicationStage())
        pipeline.add_stage(SkippedEventsFilterStage())
        pipeline.add_stage(EventLimitStage(max_events=2))

        # Process
        context = ProcessingContext(
            events=events,
            skipped_event_ids={"event-2"}
        )
        result = await pipeline.process(context)

        # Verify pipeline succeeded
        assert result.success is True
        assert len(result.warnings) >= 1  # Should have warnings from dedup and limit

        # Verify final state
        assert len(context.events) == 2  # Limited to 2
        assert all(e.id != "event-2" for e in context.events)  # Skipped filtered
        # Duplicates should be removed

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
        from calendarbot_lite.pipeline_stages import SortStage

        # Create events out of order
        event3 = create_test_event(
            "event-3", "Last", datetime(2025, 11, 1, 14, 0, tzinfo=timezone.utc)
        )
        event1 = create_test_event(
            "event-1", "First", datetime(2025, 11, 1, 10, 0, tzinfo=timezone.utc)
        )
        event2 = create_test_event(
            "event-2", "Second", datetime(2025, 11, 1, 12, 0, tzinfo=timezone.utc)
        )

        context = ProcessingContext(events=[event3, event1, event2])
        stage = SortStage()
        result = await stage.process(context)

        assert result.success is True
        assert result.events_out == 3
        assert len(context.events) == 3

        # Verify events are sorted
        assert context.events[0].subject == "First"
        assert context.events[1].subject == "Second"
        assert context.events[2].subject == "Last"

    @pytest.mark.asyncio
    async def test_sort_empty_list(self) -> None:
        """Test sorting empty event list."""
        from calendarbot_lite.pipeline_stages import SortStage

        context = ProcessingContext(events=[])
        stage = SortStage()
        result = await stage.process(context)

        assert result.success is True
        assert result.events_out == 0
        assert len(context.events) == 0
