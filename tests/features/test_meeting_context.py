"""Comprehensive unit tests for meeting context analysis features."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

from calendarbot.features.meeting_context import (
    MeetingContextAnalyzer,
    calculate_preparation_time_needed,
    get_meeting_context_for_timeframe,
)
from calendarbot.ics.models import Attendee, CalendarEvent, DateTimeInfo, EventStatus, Location


@pytest.fixture
def sample_meeting() -> CalendarEvent:
    """Create a sample calendar event for testing."""
    base_time = datetime.now(timezone.utc)
    return CalendarEvent(
        id="test-meeting-1",
        subject="Team Standup",
        start=DateTimeInfo(date_time=base_time + timedelta(minutes=30), time_zone="UTC"),
        end=DateTimeInfo(date_time=base_time + timedelta(minutes=60), time_zone="UTC"),
        show_as=EventStatus.BUSY,
        is_cancelled=False,
        attendees=[
            Attendee(name="Alice", email="alice@example.com"),
            Attendee(name="Bob", email="bob@example.com"),
        ],
    )


@pytest.fixture
def sample_events_list() -> List[CalendarEvent]:
    """Create a list of sample calendar events for testing."""
    base_time = datetime.now(timezone.utc)

    return [
        CalendarEvent(
            id="meeting-1",
            subject="1:1 with Manager",
            start=DateTimeInfo(date_time=base_time + timedelta(minutes=15), time_zone="UTC"),
            end=DateTimeInfo(date_time=base_time + timedelta(minutes=45), time_zone="UTC"),
            show_as=EventStatus.BUSY,
            attendees=[Attendee(name="Manager", email="manager@example.com")],
        ),
        CalendarEvent(
            id="meeting-2",
            subject="Interview - Senior Developer",
            start=DateTimeInfo(date_time=base_time + timedelta(hours=2), time_zone="UTC"),
            end=DateTimeInfo(date_time=base_time + timedelta(hours=3), time_zone="UTC"),
            show_as=EventStatus.BUSY,
            is_online_meeting=True,
            attendees=[
                Attendee(name="Candidate", email="candidate@example.com"),
                Attendee(name="HR", email="hr@example.com"),
            ],
        ),
        CalendarEvent(
            id="meeting-3",
            subject="Sprint Review",
            start=DateTimeInfo(date_time=base_time + timedelta(hours=4), time_zone="UTC"),
            end=DateTimeInfo(date_time=base_time + timedelta(hours=5), time_zone="UTC"),
            show_as=EventStatus.BUSY,
            location=Location(display_name="Conference Room A"),
            attendees=[
                Attendee(name=f"Team Member {i}", email=f"member{i}@example.com") for i in range(6)
            ],
        ),
        CalendarEvent(
            id="meeting-4",
            subject="Free Time Block",
            start=DateTimeInfo(date_time=base_time + timedelta(hours=6), time_zone="UTC"),
            end=DateTimeInfo(date_time=base_time + timedelta(hours=7), time_zone="UTC"),
            show_as=EventStatus.FREE,  # This should be filtered out
        ),
        CalendarEvent(
            id="meeting-5",
            subject="Cancelled Meeting",
            start=DateTimeInfo(date_time=base_time + timedelta(hours=8), time_zone="UTC"),
            end=DateTimeInfo(date_time=base_time + timedelta(hours=9), time_zone="UTC"),
            show_as=EventStatus.BUSY,
            is_cancelled=True,  # This should be filtered out
        ),
    ]


class TestMeetingContextAnalyzer:
    """Test cases for MeetingContextAnalyzer class."""

    def test_init_when_default_buffer_then_sets_15_minutes(self) -> None:
        """Test analyzer initialization with default buffer time."""
        analyzer = MeetingContextAnalyzer()
        expected_buffer = timedelta(minutes=15)
        assert analyzer.preparation_buffer == expected_buffer
        assert analyzer.context_cache == {}

    def test_init_when_custom_buffer_then_sets_correct_time(self) -> None:
        """Test analyzer initialization with custom buffer time."""
        analyzer = MeetingContextAnalyzer(preparation_buffer_minutes=30)
        expected_buffer = timedelta(minutes=30)
        assert analyzer.preparation_buffer == expected_buffer

    def test_analyze_upcoming_meetings_when_empty_events_then_raises_value_error(self) -> None:
        """Test that empty events list raises ValueError."""
        analyzer = MeetingContextAnalyzer()

        with pytest.raises(ValueError, match="Events list cannot be empty"):
            analyzer.analyze_upcoming_meetings([])

    def test_analyze_upcoming_meetings_when_valid_events_then_returns_insights(
        self, sample_events_list: List[CalendarEvent]
    ) -> None:
        """Test successful analysis of upcoming meetings."""
        analyzer = MeetingContextAnalyzer()
        current_time = datetime.now(timezone.utc)

        insights = analyzer.analyze_upcoming_meetings(sample_events_list, current_time)

        assert isinstance(insights, list)
        # Should filter out free time and cancelled meetings
        assert len(insights) <= len(sample_events_list)

        # Check insight structure
        if insights:
            insight = insights[0]
            required_keys = {
                "meeting_id",
                "subject",
                "start_time",
                "time_until_meeting_minutes",
                "preparation_needed",
                "meeting_type",
                "attendee_count",
                "has_location",
                "is_online",
                "preparation_recommendations",
            }
            assert all(key in insight for key in required_keys)

    def test_analyze_upcoming_meetings_when_exception_occurs_then_logs_and_raises(
        self, sample_events_list: List[CalendarEvent]
    ) -> None:
        """Test error handling during meeting analysis."""
        analyzer = MeetingContextAnalyzer()

        # Mock get_timezone_aware_now to cause an exception
        with patch("calendarbot.features.meeting_context.get_timezone_aware_now") as mock_get_now:
            mock_get_now.side_effect = Exception("Time error")

            with pytest.raises(Exception):
                analyzer.analyze_upcoming_meetings(sample_events_list)

    def test_filter_upcoming_meetings_when_mixed_events_then_filters_correctly(
        self, sample_events_list: List[CalendarEvent]
    ) -> None:
        """Test filtering of upcoming meetings."""
        analyzer = MeetingContextAnalyzer()
        current_time = datetime.now(timezone.utc)

        upcoming = analyzer._filter_upcoming_meetings(sample_events_list, current_time)

        # Should exclude free time and cancelled meetings
        for meeting in upcoming:
            assert meeting.is_busy_status
            assert not meeting.is_cancelled
            assert meeting.start.date_time > current_time

    def test_generate_meeting_insight_when_valid_meeting_then_returns_insight(
        self, sample_meeting: CalendarEvent
    ) -> None:
        """Test generation of meeting insight for valid meeting."""
        analyzer = MeetingContextAnalyzer()
        current_time = datetime.now(timezone.utc)

        insight = analyzer._generate_meeting_insight(sample_meeting, current_time)

        assert insight is not None
        assert insight["meeting_id"] == sample_meeting.id
        assert insight["subject"] == sample_meeting.subject
        assert isinstance(insight["time_until_meeting_minutes"], int)
        assert isinstance(insight["preparation_needed"], bool)
        assert isinstance(insight["preparation_recommendations"], list)

    def test_generate_meeting_insight_when_meeting_too_far_then_returns_none(self) -> None:
        """Test that meetings too far in future return None."""
        analyzer = MeetingContextAnalyzer()
        current_time = datetime.now(timezone.utc)

        # Create meeting 6 hours in future (beyond 4 hour limit)
        far_meeting = CalendarEvent(
            id="far-meeting",
            subject="Future Meeting",
            start=DateTimeInfo(date_time=current_time + timedelta(hours=6), time_zone="UTC"),
            end=DateTimeInfo(date_time=current_time + timedelta(hours=7), time_zone="UTC"),
            show_as=EventStatus.BUSY,
        )

        insight = analyzer._generate_meeting_insight(far_meeting, current_time)
        assert insight is None

    def test_classify_meeting_type_when_one_on_one_then_returns_correct_type(self) -> None:
        """Test classification of one-on-one meetings."""
        analyzer = MeetingContextAnalyzer()
        base_time = datetime.now(timezone.utc)

        meeting = CalendarEvent(
            id="1on1",
            subject="1:1 sync with Bob",
            start=DateTimeInfo(date_time=base_time, time_zone="UTC"),
            end=DateTimeInfo(date_time=base_time + timedelta(hours=1), time_zone="UTC"),
            show_as=EventStatus.BUSY,
        )

        meeting_type = analyzer._classify_meeting_type(meeting)
        assert meeting_type == "one_on_one"

    def test_classify_meeting_type_when_standup_then_returns_correct_type(self) -> None:
        """Test classification of standup meetings."""
        analyzer = MeetingContextAnalyzer()
        base_time = datetime.now(timezone.utc)

        meeting = CalendarEvent(
            id="standup",
            subject="Daily Standup",
            start=DateTimeInfo(date_time=base_time, time_zone="UTC"),
            end=DateTimeInfo(date_time=base_time + timedelta(hours=1), time_zone="UTC"),
            show_as=EventStatus.BUSY,
        )

        meeting_type = analyzer._classify_meeting_type(meeting)
        assert meeting_type == "standup"

    def test_classify_meeting_type_when_interview_then_returns_correct_type(self) -> None:
        """Test classification of interview meetings."""
        analyzer = MeetingContextAnalyzer()
        base_time = datetime.now(timezone.utc)

        meeting = CalendarEvent(
            id="interview",
            subject="Interview - Software Engineer",
            start=DateTimeInfo(date_time=base_time, time_zone="UTC"),
            end=DateTimeInfo(date_time=base_time + timedelta(hours=1), time_zone="UTC"),
            show_as=EventStatus.BUSY,
        )

        meeting_type = analyzer._classify_meeting_type(meeting)
        assert meeting_type == "interview"

    def test_classify_meeting_type_when_large_group_then_returns_correct_type(self) -> None:
        """Test classification of large group meetings."""
        analyzer = MeetingContextAnalyzer()
        base_time = datetime.now(timezone.utc)

        meeting = CalendarEvent(
            id="large",
            subject="All Hands Meeting",
            start=DateTimeInfo(date_time=base_time, time_zone="UTC"),
            end=DateTimeInfo(date_time=base_time + timedelta(hours=1), time_zone="UTC"),
            show_as=EventStatus.BUSY,
            attendees=[
                Attendee(name=f"Person {i}", email=f"person{i}@example.com") for i in range(7)
            ],
        )

        meeting_type = analyzer._classify_meeting_type(meeting)
        assert meeting_type == "large_group"

    def test_generate_preparation_recommendations_when_interview_then_returns_appropriate_recs(
        self,
    ) -> None:
        """Test preparation recommendations for interview meetings."""
        analyzer = MeetingContextAnalyzer()
        base_time = datetime.now(timezone.utc)

        meeting = CalendarEvent(
            id="interview",
            subject="Interview - Senior Developer",
            start=DateTimeInfo(date_time=base_time, time_zone="UTC"),
            end=DateTimeInfo(date_time=base_time + timedelta(hours=1), time_zone="UTC"),
            show_as=EventStatus.BUSY,
            is_online_meeting=True,
        )

        recommendations = analyzer._generate_preparation_recommendations(meeting)

        assert isinstance(recommendations, list)
        assert any("resume" in rec.lower() for rec in recommendations)
        assert any("questions" in rec.lower() for rec in recommendations)
        assert any("audio/video" in rec.lower() for rec in recommendations)


@pytest.mark.asyncio
async def test_get_meeting_context_for_timeframe_when_valid_input_then_returns_context(
    sample_events_list: List[CalendarEvent],
) -> None:
    """Test async function for getting meeting context within timeframe."""
    result = await get_meeting_context_for_timeframe(sample_events_list, hours_ahead=4)

    assert isinstance(result, dict)

    required_keys = {
        "timeframe_hours",
        "analysis_time",
        "total_meetings",
        "meetings_needing_preparation",
        "online_meetings",
        "meeting_insights",
        "next_meeting",
    }
    assert all(key in result for key in required_keys)

    assert result["timeframe_hours"] == 4
    assert isinstance(result["total_meetings"], int)
    assert isinstance(result["meeting_insights"], list)


@pytest.mark.asyncio
async def test_get_meeting_context_for_timeframe_when_negative_hours_then_raises_value_error() -> (
    None
):
    """Test that negative hours_ahead raises ValueError."""
    sample_events = [
        CalendarEvent(
            id="test",
            subject="Test Meeting",
            start=DateTimeInfo(date_time=datetime.now(), time_zone="UTC"),
            end=DateTimeInfo(date_time=datetime.now() + timedelta(hours=1), time_zone="UTC"),
            show_as=EventStatus.BUSY,
        )
    ]

    with pytest.raises(ValueError, match="hours_ahead must be non-negative"):
        await get_meeting_context_for_timeframe(sample_events, hours_ahead=-1)


@pytest.mark.asyncio
async def test_get_meeting_context_for_timeframe_when_empty_events_then_raises_value_error() -> (
    None
):
    """Test that empty events list raises ValueError."""
    with pytest.raises(ValueError, match="Events list cannot be empty"):
        await get_meeting_context_for_timeframe([], hours_ahead=4)


@pytest.mark.asyncio
async def test_get_meeting_context_for_timeframe_when_exception_occurs_then_logs_and_raises(
    sample_events_list: List[CalendarEvent],
) -> None:
    """Test error handling in async meeting context function."""
    with patch("calendarbot.features.meeting_context.MeetingContextAnalyzer") as mock_analyzer:
        mock_analyzer.return_value.analyze_upcoming_meetings.side_effect = Exception(
            "Analysis error"
        )

        with pytest.raises(Exception):
            await get_meeting_context_for_timeframe(sample_events_list, hours_ahead=4)


class TestCalculatePreparationTimeNeeded:
    """Test cases for calculate_preparation_time_needed function."""

    def test_calculate_preparation_time_when_negative_attendees_then_raises_value_error(
        self,
    ) -> None:
        """Test that negative attendee count raises ValueError."""
        with pytest.raises(ValueError, match="Attendee count cannot be negative"):
            calculate_preparation_time_needed("standard", -1)

    def test_calculate_preparation_time_when_interview_type_then_returns_30_minutes(self) -> None:
        """Test preparation time calculation for interview meetings."""
        result = calculate_preparation_time_needed("interview", 2)
        assert result == 30
        assert isinstance(result, int)

    def test_calculate_preparation_time_when_standup_type_then_returns_2_minutes(self) -> None:
        """Test preparation time calculation for standup meetings."""
        result = calculate_preparation_time_needed("standup", 5)
        assert result == 2
        assert isinstance(result, int)

    def test_calculate_preparation_time_when_large_attendee_count_then_adds_extra_time(
        self,
    ) -> None:
        """Test that large attendee count adds extra preparation time."""
        result_small = calculate_preparation_time_needed("standard", 3)
        result_large = calculate_preparation_time_needed("standard", 8)

        assert result_large > result_small
        assert isinstance(result_large, int)

    def test_calculate_preparation_time_when_unknown_type_then_uses_default(self) -> None:
        """Test that unknown meeting type uses default time."""
        result = calculate_preparation_time_needed("unknown_type", 2)
        assert result == 10  # Default base time
        assert isinstance(result, int)

    def test_calculate_preparation_time_when_very_large_group_then_caps_extra_time(self) -> None:
        """Test that very large groups don't add unlimited extra time."""
        result = calculate_preparation_time_needed("standard", 20)  # 15 extra people

        # Should cap at 10 extra minutes (base 10 + max 10 = 20)
        assert result == 20
        assert isinstance(result, int)


# Integration test combining multiple components
@pytest.mark.asyncio
async def test_meeting_context_integration_when_full_workflow_then_completes_successfully() -> None:
    """Integration test for complete meeting context analysis workflow."""
    # Create realistic test data
    current_time = datetime.now(timezone.utc)
    events = [
        CalendarEvent(
            id="urgent-1on1",
            subject="Urgent 1:1 with CEO",
            start=DateTimeInfo(date_time=current_time + timedelta(minutes=10), time_zone="UTC"),
            end=DateTimeInfo(date_time=current_time + timedelta(minutes=40), time_zone="UTC"),
            show_as=EventStatus.BUSY,
            attendees=[Attendee(name="CEO", email="ceo@company.com")],
        ),
        CalendarEvent(
            id="candidate-interview",
            subject="Interview - Principal Engineer Candidate",
            start=DateTimeInfo(date_time=current_time + timedelta(hours=1), time_zone="UTC"),
            end=DateTimeInfo(date_time=current_time + timedelta(hours=2), time_zone="UTC"),
            show_as=EventStatus.BUSY,
            is_online_meeting=True,
            attendees=[
                Attendee(name="Candidate", email="candidate@example.com"),
                Attendee(name="Tech Lead", email="lead@company.com"),
                Attendee(name="HR Partner", email="hr@company.com"),
            ],
        ),
    ]

    # Run complete analysis
    context = await get_meeting_context_for_timeframe(events, hours_ahead=3)

    # Verify comprehensive results
    assert context["total_meetings"] == 2
    assert context["meetings_needing_preparation"] >= 1  # At least the urgent one
    assert len(context["meeting_insights"]) == 2

    # Check specific meeting insights
    insights = context["meeting_insights"]
    urgent_insight = next(i for i in insights if "CEO" in i["subject"])
    interview_insight = next(i for i in insights if "Interview" in i["subject"])

    assert urgent_insight["meeting_type"] == "one_on_one"
    assert urgent_insight["preparation_needed"] is True

    assert interview_insight["meeting_type"] == "interview"
    assert interview_insight["is_online"] is True
    assert len(interview_insight["preparation_recommendations"]) > 0
