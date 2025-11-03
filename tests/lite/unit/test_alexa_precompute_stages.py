"""Tests for Alexa precomputation pipeline stages."""

import datetime
from typing import Optional

import pytest

from calendarbot_lite.alexa_precompute_stages import (
    DoneForDayPrecomputeStage,
    NextMeetingPrecomputeStage,
    TimeUntilPrecomputeStage,
    create_alexa_precompute_pipeline,
)
from calendarbot_lite.lite_models import (
    LiteCalendarEvent,
    LiteDateTimeInfo,
    LiteLocation,
)
from calendarbot_lite.pipeline import ProcessingContext


# Helper to create test events
def create_test_event(
    subject: str,
    start: datetime.datetime,
    end: datetime.datetime,
    event_id: Optional[str] = None,
) -> LiteCalendarEvent:
    """Create a test calendar event."""
    if event_id is None:
        event_id = subject.replace(" ", "_")

    return LiteCalendarEvent(
        id=event_id,
        subject=subject,
        start=LiteDateTimeInfo(date_time=start, time_zone="UTC"),
        end=LiteDateTimeInfo(date_time=end, time_zone="UTC"),
        body_preview="",
        location=LiteLocation(display_name=""),
        attendees=[],
        is_online_meeting=False,
        online_meeting_url=None,
    )


@pytest.mark.asyncio
async def test_next_meeting_precompute_with_meeting():
    """Test precomputing next meeting when events exist."""
    now = datetime.datetime.now(datetime.timezone.utc)
    future_time = now + datetime.timedelta(hours=1)
    end_time = future_time + datetime.timedelta(minutes=30)

    # Create test event
    event = create_test_event("Team Standup", future_time, end_time)

    # Create stage
    stage = NextMeetingPrecomputeStage(
        default_tz="UTC",
        time_provider=lambda: now,
        skipped_store=None,
        duration_formatter=None,
        iso_serializer=None,
    )

    # Create context with event
    context = ProcessingContext(events=[event])

    # Run precomputation
    result = await stage.process(context)

    # Verify success
    assert result.success is True
    assert "precomputed_responses" in context.extra

    # Verify response content
    responses = context.extra["precomputed_responses"]
    assert "NextMeetingHandler:UTC" in responses

    response = responses["NextMeetingHandler:UTC"]
    assert response["meeting"] is not None
    assert response["meeting"]["subject"] == "Team Standup"
    assert "speech_text" in response


@pytest.mark.asyncio
async def test_next_meeting_precompute_no_meetings():
    """Test precomputing next meeting when no events exist."""
    now = datetime.datetime.now(datetime.timezone.utc)

    # Create stage
    stage = NextMeetingPrecomputeStage(
        default_tz="UTC",
        time_provider=lambda: now,
        skipped_store=None,
        duration_formatter=None,
        iso_serializer=None,
    )

    # Create context with no events
    context = ProcessingContext(events=[])

    # Run precomputation
    result = await stage.process(context)

    # Verify success
    assert result.success is True

    # Verify response content
    responses = context.extra["precomputed_responses"]
    response = responses["NextMeetingHandler:UTC"]
    assert response["meeting"] is None
    assert response["speech_text"] == "No upcoming meetings"


@pytest.mark.asyncio
async def test_next_meeting_precompute_past_events_ignored():
    """Test that past events are ignored in precomputation."""
    now = datetime.datetime.now(datetime.timezone.utc)
    past_time = now - datetime.timedelta(hours=1)
    past_end = past_time + datetime.timedelta(minutes=30)
    future_time = now + datetime.timedelta(hours=2)
    future_end = future_time + datetime.timedelta(minutes=30)

    # Create past and future events
    past_event = create_test_event("Past Meeting", past_time, past_end, "past")
    future_event = create_test_event("Future Meeting", future_time, future_end, "future")

    # Create stage
    stage = NextMeetingPrecomputeStage(
        default_tz="UTC",
        time_provider=lambda: now,
        skipped_store=None,
        duration_formatter=None,
        iso_serializer=None,
    )

    # Create context with both events
    context = ProcessingContext(events=[past_event, future_event])

    # Run precomputation
    result = await stage.process(context)

    # Verify success
    assert result.success is True

    # Verify only future event is returned
    responses = context.extra["precomputed_responses"]
    response = responses["NextMeetingHandler:UTC"]
    assert response["meeting"]["subject"] == "Future Meeting"


@pytest.mark.asyncio
async def test_time_until_precompute_with_meeting():
    """Test precomputing time until next meeting when events exist."""
    now = datetime.datetime.now(datetime.timezone.utc)
    future_time = now + datetime.timedelta(hours=2)
    end_time = future_time + datetime.timedelta(minutes=45)

    # Create test event
    event = create_test_event("Design Review", future_time, end_time)

    # Create stage with duration formatter
    def format_duration(seconds):
        hours = seconds // 3600
        return f"in {hours} hours"

    stage = TimeUntilPrecomputeStage(
        default_tz="UTC",
        time_provider=lambda: now,
        skipped_store=None,
        duration_formatter=format_duration,
    )

    # Create context with event
    context = ProcessingContext(events=[event])

    # Run precomputation
    result = await stage.process(context)

    # Verify success
    assert result.success is True
    assert "precomputed_responses" in context.extra

    # Verify response content
    responses = context.extra["precomputed_responses"]
    assert "TimeUntilHandler:UTC" in responses

    response = responses["TimeUntilHandler:UTC"]
    assert response["seconds_until_start"] is not None
    assert response["seconds_until_start"] > 0
    assert "in 2 hours" in response["duration_spoken"]


@pytest.mark.asyncio
async def test_time_until_precompute_no_meetings():
    """Test precomputing time until when no meetings exist."""
    now = datetime.datetime.now(datetime.timezone.utc)

    # Create stage
    stage = TimeUntilPrecomputeStage(
        default_tz="UTC",
        time_provider=lambda: now,
        skipped_store=None,
        duration_formatter=None,
    )

    # Create context with no events
    context = ProcessingContext(events=[])

    # Run precomputation
    result = await stage.process(context)

    # Verify success
    assert result.success is True

    # Verify response content
    responses = context.extra["precomputed_responses"]
    response = responses["TimeUntilHandler:UTC"]
    assert response["seconds_until_start"] is None
    assert response["speech_text"] == "No upcoming meetings"


@pytest.mark.asyncio
async def test_done_for_day_precompute_with_meetings():
    """Test precomputing done-for-day when meetings exist today."""
    now = datetime.datetime.now(datetime.timezone.utc)

    # Create meetings throughout the day
    morning_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    morning_end = morning_start + datetime.timedelta(hours=1)

    afternoon_start = now.replace(hour=15, minute=0, second=0, microsecond=0)
    afternoon_end = afternoon_start + datetime.timedelta(hours=1)

    morning_event = create_test_event("Morning Meeting", morning_start, morning_end, "morning")
    afternoon_event = create_test_event("Afternoon Meeting", afternoon_start, afternoon_end, "afternoon")

    # Create stage
    stage = DoneForDayPrecomputeStage(
        default_tz="UTC",
        time_provider=lambda: now,
        skipped_store=None,
        iso_serializer=None,
        get_server_timezone=None,
    )

    # Create context with events
    context = ProcessingContext(events=[morning_event, afternoon_event])

    # Run precomputation
    result = await stage.process(context)

    # Verify success
    assert result.success is True
    assert "precomputed_responses" in context.extra

    # Verify response content
    responses = context.extra["precomputed_responses"]
    assert "DoneForDayHandler:UTC" in responses

    response = responses["DoneForDayHandler:UTC"]
    assert response["has_meetings_today"] is True
    assert response["last_meeting_end_iso"] is not None


@pytest.mark.asyncio
async def test_done_for_day_precompute_no_meetings():
    """Test precomputing done-for-day when no meetings exist today."""
    now = datetime.datetime.now(datetime.timezone.utc)

    # Create stage
    stage = DoneForDayPrecomputeStage(
        default_tz="UTC",
        time_provider=lambda: now,
        skipped_store=None,
        iso_serializer=None,
        get_server_timezone=None,
    )

    # Create context with no events
    context = ProcessingContext(events=[])

    # Run precomputation
    result = await stage.process(context)

    # Verify success
    assert result.success is True

    # Verify response content
    responses = context.extra["precomputed_responses"]
    response = responses["DoneForDayHandler:UTC"]
    assert response["has_meetings_today"] is False
    assert response["last_meeting_end_iso"] is None


@pytest.mark.asyncio
async def test_precompute_pipeline_integration():
    """Test the full precomputation pipeline."""
    now = datetime.datetime.now(datetime.timezone.utc)
    future_time = now + datetime.timedelta(hours=1)
    end_time = future_time + datetime.timedelta(minutes=30)

    # Create test event
    event = create_test_event("Important Meeting", future_time, end_time)

    # Create pipeline
    pipeline = create_alexa_precompute_pipeline(
        skipped_store=None,
        default_tz="UTC",
        time_provider=lambda: now,
        duration_formatter=None,
        iso_serializer=None,
        get_server_timezone=None,
    )

    # Create context
    context = ProcessingContext(events=[event])

    # Run pipeline
    result = await pipeline.process(context)

    # Verify success
    assert result.success is True

    # Verify all three responses were precomputed
    responses = context.extra.get("precomputed_responses", {})
    assert "NextMeetingHandler:UTC" in responses
    assert "TimeUntilHandler:UTC" in responses
    assert "DoneForDayHandler:UTC" in responses

    # Verify next meeting response
    next_meeting_response = responses["NextMeetingHandler:UTC"]
    assert next_meeting_response["meeting"]["subject"] == "Important Meeting"

    # Verify time until response
    time_until_response = responses["TimeUntilHandler:UTC"]
    assert time_until_response["seconds_until_start"] is not None

    # Verify done for day response
    done_for_day_response = responses["DoneForDayHandler:UTC"]
    assert done_for_day_response["has_meetings_today"] is True
