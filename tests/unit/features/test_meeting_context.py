"""Tests for meeting context analysis features."""

from datetime import datetime, timedelta
from typing import List, cast
from unittest.mock import Mock, patch

import pytest

from calendarbot.features.meeting_context import (
    MeetingContextAnalyzer,
    calculate_preparation_time_needed,
    get_meeting_context_for_timeframe,
)
from calendarbot.ics.models import CalendarEvent


class TestMeetingContextAnalyzer:
    """Test MeetingContextAnalyzer class."""

    @pytest.fixture
    def analyzer(self) -> MeetingContextAnalyzer:
        """Create analyzer with default 15min buffer."""
        return MeetingContextAnalyzer()

    @pytest.fixture
    def custom_analyzer(self) -> MeetingContextAnalyzer:
        """Create analyzer with custom 30min buffer."""
        return MeetingContextAnalyzer(preparation_buffer_minutes=30)

    @pytest.fixture
    def mock_event(self) -> Mock:
        """Create a mock calendar event with realistic properties."""
        event = Mock(spec=CalendarEvent)
        event.id = "test-meeting-123"
        event.subject = "Team Standup"
        event.location = "Conference Room A"
        event.attendees = ["user1@test.com", "user2@test.com"]
        event.is_busy_status = True
        event.is_cancelled = False
        event.is_online_meeting = False

        # Configure nested start attribute with date_time
        event.start = Mock()
        event.start.date_time = None  # Will be set in individual tests

        return event

    @pytest.fixture
    def current_time(self) -> datetime:
        """Standard current time for testing."""
        return datetime(2024, 1, 15, 10, 0, 0)

    def test_analyzer_initialization_with_default_buffer(self) -> None:
        """Test analyzer initializes with correct default buffer."""
        analyzer = MeetingContextAnalyzer()
        expected_buffer = timedelta(minutes=15)
        assert analyzer.preparation_buffer == expected_buffer
        assert analyzer.context_cache == {}

    def test_analyzer_initialization_with_custom_buffer(
        self, custom_analyzer: MeetingContextAnalyzer
    ) -> None:
        """Test analyzer initializes with custom buffer."""
        expected_buffer = timedelta(minutes=30)
        assert custom_analyzer.preparation_buffer == expected_buffer

    def test_analyze_upcoming_meetings_with_empty_events_raises_error(
        self, analyzer: MeetingContextAnalyzer
    ) -> None:
        """Test that empty events list raises ValueError."""
        with pytest.raises(ValueError, match="Events list cannot be empty"):
            analyzer.analyze_upcoming_meetings([])

    def test_analyze_upcoming_meetings_with_valid_events(
        self, analyzer: MeetingContextAnalyzer, mock_event: Mock, current_time: datetime
    ) -> None:
        """Test analysis with valid upcoming events."""
        # Set event to be 10 minutes from now (within preparation buffer)
        mock_event.start.date_time = current_time + timedelta(minutes=10)

        with patch(
            "calendarbot.features.meeting_context.get_timezone_aware_now", return_value=current_time
        ):
            insights = analyzer.analyze_upcoming_meetings([mock_event])

        assert len(insights) == 1
        insight = insights[0]
        assert insight["meeting_id"] == "test-meeting-123"
        assert insight["subject"] == "Team Standup"
        assert insight["time_until_meeting_minutes"] == 10
        assert insight["preparation_needed"] is True
        assert insight["meeting_type"] == "standup"

    def test_filter_upcoming_meetings_excludes_past_events(
        self, analyzer: MeetingContextAnalyzer, mock_event: Mock, current_time: datetime
    ) -> None:
        """Test filtering excludes events in the past."""
        # Set event to be in the past
        mock_event.start.date_time = current_time - timedelta(hours=1)

        filtered = analyzer._filter_upcoming_meetings([mock_event], current_time)
        assert len(filtered) == 0

    def test_filter_upcoming_meetings_excludes_far_future_events(
        self, analyzer: MeetingContextAnalyzer, mock_event: Mock, current_time: datetime
    ) -> None:
        """Test filtering excludes events more than 24 hours away."""
        # Set event to be 25 hours in the future
        mock_event.start.date_time = current_time + timedelta(hours=25)

        filtered = analyzer._filter_upcoming_meetings([mock_event], current_time)
        assert len(filtered) == 0

    def test_filter_upcoming_meetings_excludes_cancelled_events(
        self, analyzer: MeetingContextAnalyzer, mock_event: Mock, current_time: datetime
    ) -> None:
        """Test filtering excludes cancelled events."""
        mock_event.start.date_time = current_time + timedelta(hours=2)
        mock_event.is_cancelled = True

        filtered = analyzer._filter_upcoming_meetings([mock_event], current_time)
        assert len(filtered) == 0

    def test_filter_upcoming_meetings_excludes_non_busy_events(
        self, analyzer: MeetingContextAnalyzer, mock_event: Mock, current_time: datetime
    ) -> None:
        """Test filtering excludes non-busy status events."""
        mock_event.start.date_time = current_time + timedelta(hours=2)
        mock_event.is_busy_status = False

        filtered = analyzer._filter_upcoming_meetings([mock_event], current_time)
        assert len(filtered) == 0

    @pytest.mark.parametrize(
        ("subject", "expected_type"),
        [
            ("1:1 with John", "one_on_one"),
            ("One-on-one discussion", "one_on_one"),
            ("Weekly sync meeting", "one_on_one"),
            ("Daily standup", "standup"),
            ("Scrum meeting", "standup"),
            ("Sprint review", "review"),
            ("Retrospective session", "review"),
            ("Demo presentation", "review"),
            ("Interview with candidate", "interview"),
            ("Candidate screening", "interview"),
            ("Regular meeting", "standard"),
        ],
    )
    def test_classify_meeting_type_by_subject(
        self, analyzer: MeetingContextAnalyzer, mock_event: Mock, subject: str, expected_type: str
    ) -> None:
        """Test meeting type classification based on subject."""
        mock_event.subject = subject
        mock_event.attendees = ["user1@test.com", "user2@test.com"]  # Small group
        mock_event.is_online_meeting = False

        result = analyzer._classify_meeting_type(mock_event)
        assert result == expected_type

    def test_classify_meeting_type_large_group(
        self, analyzer: MeetingContextAnalyzer, mock_event: Mock
    ) -> None:
        """Test classification for large group meetings."""
        mock_event.subject = "All hands meeting"
        mock_event.attendees = [f"user{i}@test.com" for i in range(7)]  # 7 attendees
        mock_event.is_online_meeting = False

        result = analyzer._classify_meeting_type(mock_event)
        assert result == "large_group"

    def test_classify_meeting_type_virtual(
        self, analyzer: MeetingContextAnalyzer, mock_event: Mock
    ) -> None:
        """Test classification for virtual meetings."""
        mock_event.subject = "Regular meeting"
        mock_event.attendees = ["user1@test.com", "user2@test.com"]
        mock_event.is_online_meeting = True

        result = analyzer._classify_meeting_type(mock_event)
        assert result == "virtual"

    @pytest.mark.parametrize(
        ("meeting_type", "expected_recommendations"),
        [
            (
                "interview",
                [
                    "Review candidate resume and background",
                    "Prepare interview questions",
                    "Test video conference setup",
                ],
            ),
            (
                "review",
                [
                    "Gather status updates and metrics",
                    "Prepare presentation materials",
                    "Review previous action items",
                ],
            ),
            (
                "one_on_one",
                [
                    "Review recent team updates",
                    "Prepare discussion topics",
                    "Check for any blockers to discuss",
                ],
            ),
            (
                "standup",
                ["Prepare status update", "Identify any blockers", "Review sprint progress"],
            ),
        ],
    )
    def test_generate_preparation_recommendations_by_type(
        self,
        analyzer: MeetingContextAnalyzer,
        mock_event: Mock,
        meeting_type: str,
        expected_recommendations: list[str],
    ) -> None:
        """Test preparation recommendations based on meeting type."""
        # Configure mock based on meeting type
        if meeting_type == "interview":
            mock_event.subject = "Interview with candidate"
        elif meeting_type == "review":
            mock_event.subject = "Sprint review"
        elif meeting_type == "one_on_one":
            mock_event.subject = "1:1 with manager"
        elif meeting_type == "standup":
            mock_event.subject = "Daily standup"

        mock_event.is_online_meeting = False
        mock_event.location = None
        mock_event.attendees = ["user1@test.com", "user2@test.com"]

        recommendations = analyzer._generate_preparation_recommendations(mock_event)

        for expected in expected_recommendations:
            assert expected in recommendations

    def test_generate_preparation_recommendations_online_meeting(
        self, analyzer: MeetingContextAnalyzer, mock_event: Mock
    ) -> None:
        """Test preparation recommendations include tech setup for online meetings."""
        mock_event.subject = "Regular meeting"
        mock_event.is_online_meeting = True
        mock_event.location = None
        mock_event.attendees = ["user1@test.com"]

        recommendations = analyzer._generate_preparation_recommendations(mock_event)
        assert "Test audio/video setup" in recommendations

    def test_generate_preparation_recommendations_physical_location(
        self, analyzer: MeetingContextAnalyzer, mock_event: Mock
    ) -> None:
        """Test preparation recommendations include travel time for physical meetings."""
        mock_event.subject = "Regular meeting"
        mock_event.is_online_meeting = False
        mock_event.location = "Conference Room A"
        mock_event.attendees = ["user1@test.com"]

        recommendations = analyzer._generate_preparation_recommendations(mock_event)
        assert "Check travel time to location" in recommendations

    def test_generate_preparation_recommendations_large_group(
        self, analyzer: MeetingContextAnalyzer, mock_event: Mock
    ) -> None:
        """Test preparation recommendations include attendee review for large groups."""
        mock_event.subject = "Regular meeting"
        mock_event.is_online_meeting = False
        mock_event.location = None
        mock_event.attendees = [f"user{i}@test.com" for i in range(5)]  # 5 attendees

        recommendations = analyzer._generate_preparation_recommendations(mock_event)
        assert "Review attendee list and roles" in recommendations

    def test_generate_meeting_insight_skips_far_future_meetings(
        self, analyzer: MeetingContextAnalyzer, mock_event: Mock, current_time: datetime
    ) -> None:
        """Test that meetings more than 4 hours away return None insight."""
        mock_event.start.date_time = current_time + timedelta(hours=5)

        insight = analyzer._generate_meeting_insight(mock_event, current_time)
        assert insight is None

    def test_generate_meeting_insight_handles_exceptions(
        self, analyzer: MeetingContextAnalyzer, current_time: datetime
    ) -> None:
        """Test that insight generation handles exceptions gracefully."""
        # Create a broken mock that will raise an exception
        broken_event = Mock()
        broken_event.id = "broken"
        broken_event.start.date_time = "not a datetime"  # This will cause an error

        insight = analyzer._generate_meeting_insight(broken_event, current_time)
        assert insight is None

    def test_analyze_upcoming_meetings_handles_exceptions(
        self, analyzer: MeetingContextAnalyzer, mock_event: Mock
    ) -> None:
        """Test that analysis handles exceptions and re-raises them."""
        # Create a scenario that will cause an exception in the main logic
        mock_event.start.date_time = "not a datetime"

        with pytest.raises(Exception):
            analyzer.analyze_upcoming_meetings([mock_event])


class TestGetMeetingContextForTimeframe:
    """Test get_meeting_context_for_timeframe function."""

    @pytest.fixture
    def mock_events(self) -> list[Mock]:
        """Create list of mock events for testing."""
        events = []
        for i in range(3):
            event = Mock(spec=CalendarEvent)
            event.id = f"event-{i}"
            event.subject = f"Meeting {i}"
            event.is_cancelled = False

            # Configure nested start attribute
            event.start = Mock()
            event.start.date_time = None  # Will be set in individual tests

            events.append(event)
        return events

    @pytest.fixture
    def current_time(self) -> datetime:
        """Standard current time for testing."""
        return datetime(2024, 1, 15, 10, 0, 0)

    @pytest.mark.asyncio
    async def test_get_context_with_negative_hours_raises_error(self) -> None:
        """Test that negative hours_ahead raises ValueError."""
        with pytest.raises(ValueError, match="hours_ahead must be non-negative"):
            await get_meeting_context_for_timeframe([], hours_ahead=-1)

    @pytest.mark.asyncio
    async def test_get_context_with_empty_events_raises_error(self) -> None:
        """Test that empty events list raises ValueError."""
        with pytest.raises(ValueError, match="Events list cannot be empty"):
            await get_meeting_context_for_timeframe([])

    @pytest.mark.asyncio
    async def test_get_context_with_valid_events(
        self, mock_events: list[Mock], current_time: datetime
    ) -> None:
        """Test context generation with valid events."""
        # Set up events within timeframe
        for i, event in enumerate(mock_events):
            event.start.date_time = current_time + timedelta(hours=i + 1)

        with patch(
            "calendarbot.features.meeting_context.get_timezone_aware_now", return_value=current_time
        ):
            with patch(
                "calendarbot.features.meeting_context.MeetingContextAnalyzer"
            ) as mock_analyzer_class:
                mock_analyzer = Mock()
                mock_analyzer.analyze_upcoming_meetings.return_value = [
                    {"meeting_id": "event-0", "preparation_needed": True, "is_online": False},
                    {"meeting_id": "event-1", "preparation_needed": False, "is_online": True},
                ]
                mock_analyzer_class.return_value = mock_analyzer

                result = await get_meeting_context_for_timeframe(
                    cast(List[CalendarEvent], mock_events), hours_ahead=4
                )

        assert result["timeframe_hours"] == 4
        assert result["total_meetings"] == 2
        assert result["meetings_needing_preparation"] == 1
        assert result["online_meetings"] == 1
        assert len(result["meeting_insights"]) == 2
        assert result["next_meeting"]["meeting_id"] == "event-0"

    @pytest.mark.asyncio
    async def test_get_context_filters_events_by_timeframe(
        self, mock_events: list[Mock], current_time: datetime
    ) -> None:
        """Test that events outside timeframe are filtered out."""
        # Set first event within timeframe, others outside
        mock_events[0].start.date_time = current_time + timedelta(hours=1)
        mock_events[1].start.date_time = current_time + timedelta(hours=5)  # Outside 4h window
        mock_events[2].start.date_time = current_time - timedelta(hours=1)  # In past

        with patch(
            "calendarbot.features.meeting_context.get_timezone_aware_now", return_value=current_time
        ):
            with patch(
                "calendarbot.features.meeting_context.MeetingContextAnalyzer"
            ) as mock_analyzer_class:
                mock_analyzer = Mock()
                mock_analyzer.analyze_upcoming_meetings.return_value = []
                mock_analyzer_class.return_value = mock_analyzer

                await get_meeting_context_for_timeframe(
                    cast(List[CalendarEvent], mock_events), hours_ahead=4
                )

                # Check that only events within timeframe were passed to analyzer
                passed_events = mock_analyzer.analyze_upcoming_meetings.call_args[0][0]
                assert len(passed_events) == 1
                assert passed_events[0] == mock_events[0]

    @pytest.mark.asyncio
    async def test_get_context_handles_exceptions(self, mock_events: list[Mock]) -> None:
        """Test that context generation handles exceptions and re-raises them."""
        mock_events[0].start.date_time = "not a datetime"

        with pytest.raises(Exception):
            await get_meeting_context_for_timeframe(cast(List[CalendarEvent], mock_events))


class TestCalculatePreparationTimeNeeded:
    """Test calculate_preparation_time_needed function."""

    def test_calculate_with_negative_attendee_count_raises_error(self) -> None:
        """Test that negative attendee count raises ValueError."""
        with pytest.raises(ValueError, match="Attendee count cannot be negative"):
            calculate_preparation_time_needed("standard", -1)

    @pytest.mark.parametrize(
        ("meeting_type", "attendee_count", "expected_time"),
        [
            ("interview", 2, 30),
            ("review", 3, 20),
            ("one_on_one", 2, 5),
            ("standup", 5, 2),
            ("large_group", 3, 15),
            ("virtual", 4, 10),
            ("standard", 3, 10),
            ("unknown_type", 2, 10),  # Should default to 10
        ],
    )
    def test_calculate_base_time_by_meeting_type(
        self, meeting_type: str, attendee_count: int, expected_time: int
    ) -> None:
        """Test base preparation time calculation by meeting type."""
        result = calculate_preparation_time_needed(meeting_type, attendee_count)
        assert result == expected_time

    def test_calculate_with_large_attendee_count_adds_extra_time(self) -> None:
        """Test that large attendee counts add extra preparation time."""
        # Base time for standard meeting is 10, with 8 attendees should add 3 extra (8-5=3)
        result = calculate_preparation_time_needed("standard", 8)
        assert result == 13

    def test_calculate_with_very_large_attendee_count_caps_extra_time(self) -> None:
        """Test that extra time is capped at 10 minutes regardless of attendee count."""
        # Base time for standard meeting is 10, with 20 attendees should add max 10 extra
        result = calculate_preparation_time_needed("standard", 20)
        assert result == 20

    def test_calculate_with_zero_attendees(self) -> None:
        """Test calculation with zero attendees."""
        result = calculate_preparation_time_needed("standard", 0)
        assert result == 10  # Just base time

    def test_calculate_with_exactly_five_attendees(self) -> None:
        """Test calculation with exactly 5 attendees (boundary case)."""
        result = calculate_preparation_time_needed("standard", 5)
        assert result == 10  # No extra time added for 5 or fewer
