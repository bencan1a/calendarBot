"""Unit tests for morning summary service functionality."""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from calendarbot_lite.lite_models import (
    LiteCalendarEvent,
    LiteDateTimeInfo,
    LiteEventStatus,
    LiteLocation,
)
from calendarbot_lite.morning_summary import (
    FOCUS_TIME_KEYWORDS,
    MAX_EVENTS_LIMIT,
    MORNING_END_HOUR,
    MORNING_START_HOUR,
    PERFORMANCE_TARGET_SECONDS,
    SIGNIFICANT_FREE_BLOCK_MINUTES,
    DensityLevel,
    FreeBlock,
    MeetingInsight,
    MorningSummaryRequest,
    MorningSummaryResult,
    MorningSummaryService,
    get_morning_summary_service,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def mock_server_timezone():
    """Mock _get_server_timezone to return UTC for all tests."""
    # Patch in both server module and morning_summary module (which imports it)
    with patch("calendarbot_lite.server._get_server_timezone", return_value="UTC"), \
         patch("calendarbot_lite.morning_summary._get_server_timezone", return_value="UTC"):
        yield


class TestMorningSummaryRequest:
    """Tests for MorningSummaryRequest data model."""

    def test_request_when_default_values_then_valid(self):
        """Test request creation with default values."""
        request = MorningSummaryRequest()
        
        assert request.date is None
        assert request.timezone == "UTC"
        assert request.detail_level == "normal"
        assert request.prefer_ssml is False
        assert request.max_events == 50

    def test_request_when_max_events_exceeds_limit_then_clamped(self):
        """Test max_events validation clamps to performance limit."""
        request = MorningSummaryRequest(max_events=100)
        
        assert request.max_events == MAX_EVENTS_LIMIT

    def test_request_when_custom_values_then_preserved(self):
        """Test request creation with custom values."""
        request = MorningSummaryRequest(
            date="2023-12-01",
            timezone="America/Los_Angeles",
            detail_level="detailed",
            prefer_ssml=True,
            max_events=25,
        )
        
        assert request.date == "2023-12-01"
        assert request.timezone == "America/Los_Angeles"
        assert request.detail_level == "detailed"
        assert request.prefer_ssml is True
        assert request.max_events == 25


class TestFreeBlock:
    """Tests for FreeBlock data model."""

    def test_free_block_when_45_minutes_then_significant(self):
        """Test significant free block detection."""
        start_time = datetime(2023, 12, 1, 9, 0, tzinfo=timezone.utc)
        end_time = datetime(2023, 12, 1, 9, 45, tzinfo=timezone.utc)
        
        block = FreeBlock(
            start_time=start_time,
            end_time=end_time,
            duration_minutes=45,
        )
        
        assert block.is_significant is True

    def test_free_block_when_30_minutes_then_not_significant(self):
        """Test non-significant free block detection."""
        start_time = datetime(2023, 12, 1, 9, 0, tzinfo=timezone.utc)
        end_time = datetime(2023, 12, 1, 9, 30, tzinfo=timezone.utc)
        
        block = FreeBlock(
            start_time=start_time,
            end_time=end_time,
            duration_minutes=30,
        )
        
        assert block.is_significant is False

    def test_get_spoken_duration_when_30_minutes_then_formatted(self):
        """Test spoken duration formatting for minutes."""
        block = FreeBlock(
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_minutes=30,
        )
        
        assert block.get_spoken_duration() == "30-minute"

    def test_get_spoken_duration_when_60_minutes_then_one_hour(self):
        """Test spoken duration formatting for one hour."""
        block = FreeBlock(
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_minutes=60,
        )
        
        assert block.get_spoken_duration() == "one-hour"

    def test_get_spoken_duration_when_90_minutes_then_hour_and_minutes(self):
        """Test spoken duration formatting for hour and minutes."""
        block = FreeBlock(
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_minutes=90,
        )
        
        assert block.get_spoken_duration() == "1-hour 30-minute"

    def test_get_spoken_start_time_when_9_am_then_formatted(self):
        """Test spoken start time formatting for 9 AM."""
        start_time = datetime(2023, 12, 1, 9, 0, tzinfo=timezone.utc)
        
        block = FreeBlock(
            start_time=start_time,
            end_time=datetime.now(timezone.utc),
            duration_minutes=60,
        )
        
        assert block.get_spoken_start_time() == "9 AM"

    def test_get_spoken_start_time_when_930_am_then_formatted(self):
        """Test spoken start time formatting for 9:30 AM."""
        start_time = datetime(2023, 12, 1, 9, 30, tzinfo=timezone.utc)
        
        block = FreeBlock(
            start_time=start_time,
            end_time=datetime.now(timezone.utc),
            duration_minutes=60,
        )
        
        assert block.get_spoken_start_time() == "9 thirty AM"

    def test_get_spoken_start_time_when_noon_then_formatted(self):
        """Test spoken start time formatting for noon."""
        start_time = datetime(2023, 12, 1, 12, 0, tzinfo=timezone.utc)
        
        block = FreeBlock(
            start_time=start_time,
            end_time=datetime.now(timezone.utc),
            duration_minutes=60,
        )
        
        assert block.get_spoken_start_time() == "noon"


class TestMeetingInsight:
    """Tests for MeetingInsight data model."""

    def test_get_short_subject_when_long_title_then_truncated(self):
        """Test subject truncation for long titles."""
        insight = MeetingInsight(
            meeting_id="test-1",
            subject="This is a very long meeting subject that needs to be shortened",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )
        
        short_subject = insight.get_short_subject()
        words = short_subject.split()
        assert len(words) <= 6
        assert short_subject == "This is a very long meeting"

    def test_get_short_subject_when_short_title_then_preserved(self):
        """Test subject preservation for short titles."""
        insight = MeetingInsight(
            meeting_id="test-1",
            subject="Quick sync",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )
        
        assert insight.get_short_subject() == "Quick sync"

    def test_get_spoken_start_time_when_various_times_then_formatted(self):
        """Test spoken start time formatting for various times."""
        # Test 9:00 AM
        insight_9am = MeetingInsight(
            meeting_id="test-1",
            subject="Test Meeting",
            start_time=datetime(2023, 12, 1, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2023, 12, 1, 10, 0, tzinfo=timezone.utc),
        )
        assert insight_9am.get_spoken_start_time() == "9 AM"

        # Test 12:30 PM
        insight_1230pm = MeetingInsight(
            meeting_id="test-2",
            subject="Test Meeting",
            start_time=datetime(2023, 12, 1, 12, 30, tzinfo=timezone.utc),
            end_time=datetime(2023, 12, 1, 13, 30, tzinfo=timezone.utc),
        )
        assert insight_1230pm.get_spoken_start_time() == "twelve thirty PM"


@pytest.fixture
def sample_events():
    """Create sample calendar events for testing."""
    # Create events for December 1, 2023 (tomorrow in tests)
    base_date = datetime(2023, 12, 1, tzinfo=timezone.utc)
    
    events = [
        # Early meeting at 7:00 AM
        LiteCalendarEvent(
            id="early-meeting",
            subject="Early Team Standup",
            start=LiteDateTimeInfo(
                date_time=base_date.replace(hour=7, minute=0),
                time_zone="UTC",
            ),
            end=LiteDateTimeInfo(
                date_time=base_date.replace(hour=7, minute=30),
                time_zone="UTC",
            ),
            show_as=LiteEventStatus.BUSY,
        ),
        
        # Normal meeting at 9:00 AM
        LiteCalendarEvent(
            id="morning-meeting",
            subject="Project Sync Meeting with Development Team and Stakeholders",
            start=LiteDateTimeInfo(
                date_time=base_date.replace(hour=9, minute=0),
                time_zone="UTC",
            ),
            end=LiteDateTimeInfo(
                date_time=base_date.replace(hour=10, minute=0),
                time_zone="UTC",
            ),
            show_as=LiteEventStatus.BUSY,
            location=LiteLocation(display_name="Conference Room A"),
        ),
        
        # Back-to-back meeting at 10:00 AM (no gap)
        LiteCalendarEvent(
            id="back-to-back-meeting",
            subject="Client Review",
            start=LiteDateTimeInfo(
                date_time=base_date.replace(hour=10, minute=0),
                time_zone="UTC",
            ),
            end=LiteDateTimeInfo(
                date_time=base_date.replace(hour=11, minute=0),
                time_zone="UTC",
            ),
            show_as=LiteEventStatus.BUSY,
            is_online_meeting=True,
            online_meeting_url="https://teams.microsoft.com/example",
        ),
        
        # Focus Time block at 11:30 AM (should not count as meeting)
        LiteCalendarEvent(
            id="focus-time",
            subject="Focus Time - Deep Work",
            start=LiteDateTimeInfo(
                date_time=base_date.replace(hour=11, minute=30),
                time_zone="UTC",
            ),
            end=LiteDateTimeInfo(
                date_time=base_date.replace(hour=12, minute=0),
                time_zone="UTC",
            ),
            show_as=LiteEventStatus.BUSY,
        ),
        
        # All-day actionable event
        LiteCalendarEvent(
            id="all-day-actionable",
            subject="Company Conference",
            start=LiteDateTimeInfo(
                date_time=base_date.replace(hour=0, minute=0),
                time_zone="UTC",
            ),
            end=LiteDateTimeInfo(
                date_time=base_date.replace(hour=23, minute=59),
                time_zone="UTC",
            ),
            is_all_day=True,
            show_as=LiteEventStatus.BUSY,
        ),
        
        # All-day non-actionable event (birthday)
        LiteCalendarEvent(
            id="birthday",
            subject="John's Birthday",
            start=LiteDateTimeInfo(
                date_time=base_date.replace(hour=0, minute=0),
                time_zone="UTC",
            ),
            end=LiteDateTimeInfo(
                date_time=base_date.replace(hour=23, minute=59),
                time_zone="UTC",
            ),
            is_all_day=True,
            show_as=LiteEventStatus.FREE,
        ),
        
        # Cancelled meeting (should be filtered out)
        LiteCalendarEvent(
            id="cancelled-meeting",
            subject="Cancelled Meeting",
            start=LiteDateTimeInfo(
                date_time=base_date.replace(hour=8, minute=0),
                time_zone="UTC",
            ),
            end=LiteDateTimeInfo(
                date_time=base_date.replace(hour=9, minute=0),
                time_zone="UTC",
            ),
            show_as=LiteEventStatus.BUSY,
            is_cancelled=True,
        ),
    ]
    
    return events


@pytest.fixture
def mock_tomorrow_date():
    """Mock tomorrow's date for consistent testing."""
    return datetime(2023, 12, 1, 0, 0, 0, tzinfo=timezone.utc)


class TestMorningSummaryService:
    """Tests for MorningSummaryService core functionality."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance for testing."""
        return MorningSummaryService()

    @pytest.mark.asyncio
    async def test_generate_summary_when_normal_schedule_then_analysis_correct(
        self, service, sample_events, mock_tomorrow_date
    ):
        """Test normal morning schedule analysis (Story 1)."""
        with patch.object(service, "_get_tomorrow_date", return_value=mock_tomorrow_date):
            request = MorningSummaryRequest(timezone="UTC")
            result = await service.generate_summary(sample_events, request)
            
            # Basic analysis verification (Story 1)
            assert isinstance(result, MorningSummaryResult)
            assert result.timeframe_start.hour == MORNING_START_HOUR
            assert result.timeframe_end.hour == MORNING_END_HOUR
            
            # Meeting equivalents calculation (Story 4)
            # 3 timed meetings (early, morning, back-to-back) + 0.5 for all-day actionable
            # Focus time doesn't count, cancelled meeting filtered out, birthday not actionable
            expected_equivalents = 3.5
            assert result.total_meetings_equivalent == expected_equivalents
            
            # Density classification (Story 4)
            assert result.density == DensityLevel.MODERATE  # 3.5 equivalents = moderate
            
            # Early start detection (Story 2)
            assert result.early_start_flag is True  # 7:00 AM meeting
            
            # Back-to-back meetings (Story 3)
            assert result.back_to_back_count == 1  # 9-10 AM and 10-11 AM meetings
            
            # Meeting insights - Focus Time should be excluded from insights
            assert len(result.meeting_insights) == 3  # Excluding cancelled and focus time
            
            # Speech text contains evening delivery context (Story 5)
            assert "Good evening" in result.speech_text
            assert "tomorrow" in result.speech_text.lower()

    @pytest.mark.asyncio
    async def test_generate_summary_when_early_start_then_detection_correct(
        self, service, mock_tomorrow_date
    ):
        """Test early start detection and wake-up recommendations (Story 2)."""
        # Create event at 7:15 AM (very early)
        early_event = LiteCalendarEvent(
            id="very-early",
            subject="Very Early Meeting",
            start=LiteDateTimeInfo(
                date_time=datetime(2023, 12, 1, 7, 15, tzinfo=timezone.utc),
                time_zone="UTC",
            ),
            end=LiteDateTimeInfo(
                date_time=datetime(2023, 12, 1, 8, 0, tzinfo=timezone.utc),
                time_zone="UTC",
            ),
            show_as=LiteEventStatus.BUSY,
        )
        
        with patch.object(service, "_get_tomorrow_date", return_value=mock_tomorrow_date):
            request = MorningSummaryRequest(timezone="UTC")
            result = await service.generate_summary([early_event], request)
            
            # Early start flag should be True
            assert result.early_start_flag is True
            
            # Wake-up recommendation calculation
            wake_up_time = result.wake_up_recommendation_time
            assert wake_up_time is not None
            
            # Should be 90 minutes before meeting, but minimum 6:00 AM
            expected_wake_up = datetime(2023, 12, 1, 6, 0, tzinfo=timezone.utc)
            assert wake_up_time == expected_wake_up
            
            # Speech should mention very early start
            assert "very early" in result.speech_text.lower()

    @pytest.mark.asyncio
    async def test_generate_summary_when_free_blocks_then_analysis_correct(
        self, service, mock_tomorrow_date
    ):
        """Test free time block analysis (Story 3)."""
        # Create events with gaps for free time analysis
        events = [
            LiteCalendarEvent(
                id="meeting1",
                subject="Meeting 1",
                start=LiteDateTimeInfo(
                    date_time=datetime(2023, 12, 1, 8, 0, tzinfo=timezone.utc),
                    time_zone="UTC",
                ),
                end=LiteDateTimeInfo(
                    date_time=datetime(2023, 12, 1, 9, 0, tzinfo=timezone.utc),
                    time_zone="UTC",
                ),
            ),
            LiteCalendarEvent(
                id="meeting2",
                subject="Meeting 2",
                start=LiteDateTimeInfo(
                    date_time=datetime(2023, 12, 1, 10, 30, tzinfo=timezone.utc),
                    time_zone="UTC",
                ),
                end=LiteDateTimeInfo(
                    date_time=datetime(2023, 12, 1, 11, 30, tzinfo=timezone.utc),
                    time_zone="UTC",
                ),
            ),
        ]
        
        with patch.object(service, "_get_tomorrow_date", return_value=mock_tomorrow_date):
            request = MorningSummaryRequest(timezone="UTC")
            result = await service.generate_summary(events, request)
            
            # Should have free blocks
            assert len(result.free_blocks) >= 1
            
            # Check for significant free block between meetings (9:00 - 10:30 = 90 minutes)
            significant_blocks = [fb for fb in result.free_blocks if fb.is_significant]
            assert len(significant_blocks) >= 1
            
            longest_block = result.longest_free_block
            assert longest_block is not None
            assert longest_block.duration_minutes >= SIGNIFICANT_FREE_BLOCK_MINUTES

    @pytest.mark.asyncio
    async def test_generate_summary_when_density_levels_then_classification_correct(
        self, service, mock_tomorrow_date
    ):
        """Test morning schedule density classification (Story 4)."""
        
        # Test light schedule (1 meeting)
        light_events = [
            LiteCalendarEvent(
                id="single-meeting",
                subject="Only Meeting",
                start=LiteDateTimeInfo(
                    date_time=datetime(2023, 12, 1, 9, 0, tzinfo=timezone.utc),
                    time_zone="UTC",
                ),
                end=LiteDateTimeInfo(
                    date_time=datetime(2023, 12, 1, 10, 0, tzinfo=timezone.utc),
                    time_zone="UTC",
                ),
            )
        ]
        
        with patch.object(service, "_get_tomorrow_date", return_value=mock_tomorrow_date):
            request = MorningSummaryRequest(timezone="UTC")
            result = await service.generate_summary(light_events, request)
            
            assert result.density == DensityLevel.LIGHT
            assert "light morning schedule" in result.speech_text.lower()

    @pytest.mark.asyncio
    async def test_generate_summary_when_focus_time_then_excluded_from_density(
        self, service, mock_tomorrow_date
    ):
        """Test Focus Time exclusion from density calculation (Stories 3&4)."""
        focus_events = [
            LiteCalendarEvent(
                id="focus-1",
                subject="Focus Time",
                start=LiteDateTimeInfo(
                    date_time=datetime(2023, 12, 1, 9, 0, tzinfo=timezone.utc),
                    time_zone="UTC",
                ),
                end=LiteDateTimeInfo(
                    date_time=datetime(2023, 12, 1, 10, 0, tzinfo=timezone.utc),
                    time_zone="UTC",
                ),
            ),
            LiteCalendarEvent(
                id="focus-2",
                subject="Deep Work Session",
                start=LiteDateTimeInfo(
                    date_time=datetime(2023, 12, 1, 10, 30, tzinfo=timezone.utc),
                    time_zone="UTC",
                ),
                end=LiteDateTimeInfo(
                    date_time=datetime(2023, 12, 1, 11, 30, tzinfo=timezone.utc),
                    time_zone="UTC",
                ),
            ),
        ]
        
        with patch.object(service, "_get_tomorrow_date", return_value=mock_tomorrow_date):
            request = MorningSummaryRequest(timezone="UTC")
            result = await service.generate_summary(focus_events, request)
            
            # Focus Time should not count toward meeting equivalents
            assert result.total_meetings_equivalent == 0.0
            
            # Should mention 0 meeting equivalents but not "completely free morning"
            # since there are still Focus Time events scheduled
            assert "0 meeting equivalents" in result.speech_text
            assert "light morning schedule" in result.speech_text.lower()

    @pytest.mark.asyncio
    async def test_generate_summary_when_all_day_events_then_handled_correctly(
        self, service, mock_tomorrow_date
    ):
        """Test all-day event handling (Story 6)."""
        all_day_events = [
            # Actionable all-day event
            LiteCalendarEvent(
                id="conference",
                subject="Annual Conference",
                start=LiteDateTimeInfo(
                    date_time=datetime(2023, 12, 1, 0, 0, tzinfo=timezone.utc),
                    time_zone="UTC",
                ),
                end=LiteDateTimeInfo(
                    date_time=datetime(2023, 12, 1, 23, 59, tzinfo=timezone.utc),
                    time_zone="UTC",
                ),
                is_all_day=True,
            ),
            # Non-actionable all-day event (birthday)
            LiteCalendarEvent(
                id="birthday",
                subject="Birthday - John Smith",
                start=LiteDateTimeInfo(
                    date_time=datetime(2023, 12, 1, 0, 0, tzinfo=timezone.utc),
                    time_zone="UTC",
                ),
                end=LiteDateTimeInfo(
                    date_time=datetime(2023, 12, 1, 23, 59, tzinfo=timezone.utc),
                    time_zone="UTC",
                ),
                is_all_day=True,
            ),
        ]
        
        with patch.object(service, "_get_tomorrow_date", return_value=mock_tomorrow_date):
            request = MorningSummaryRequest(timezone="UTC")
            result = await service.generate_summary(all_day_events, request)
            
            # Only actionable all-day events should count (0.5 equivalents)
            assert result.total_meetings_equivalent == 0.5
            
            # Should mention actionable all-day event in speech
            assert "Annual Conference" in result.speech_text

    @pytest.mark.asyncio
    async def test_generate_summary_when_no_meetings_then_encouraging_message(
        self, service, mock_tomorrow_date
    ):
        """Test no meetings scenario (Story 7)."""
        with patch.object(service, "_get_tomorrow_date", return_value=mock_tomorrow_date):
            request = MorningSummaryRequest(timezone="UTC")
            result = await service.generate_summary([], request)
            
            # Should have encouraging message for free morning
            assert "completely free morning" in result.speech_text
            assert "great opportunity" in result.speech_text.lower()
            assert "deep work or personal time" in result.speech_text

    @pytest.mark.asyncio
    async def test_generate_summary_when_performance_requirements_then_met(
        self, service, mock_tomorrow_date
    ):
        """Test performance and reliability requirements (Story 8)."""
        # Create maximum number of events to test performance
        max_events = []
        base_time = datetime(2023, 12, 1, 6, 0, tzinfo=timezone.utc)
        
        for i in range(MAX_EVENTS_LIMIT):
            event = LiteCalendarEvent(
                id=f"event-{i}",
                subject=f"Meeting {i}",
                start=LiteDateTimeInfo(
                    date_time=base_time + timedelta(minutes=i * 5),
                    time_zone="UTC",
                ),
                end=LiteDateTimeInfo(
                    date_time=base_time + timedelta(minutes=i * 5 + 30),
                    time_zone="UTC",
                ),
            )
            max_events.append(event)
        
        with patch.object(service, "_get_tomorrow_date", return_value=mock_tomorrow_date):
            request = MorningSummaryRequest(timezone="UTC")
            
            start_time = time.time()
            result = await service.generate_summary(max_events, request)
            elapsed_time = time.time() - start_time
            
            # Should complete within performance target
            assert elapsed_time < PERFORMANCE_TARGET_SECONDS
            
            # Should return valid result
            assert isinstance(result, MorningSummaryResult)
            assert result.speech_text is not None

    @pytest.mark.asyncio
    async def test_generate_summary_when_invalid_input_then_error_handling(self, service):
        """Test error handling for invalid inputs."""
        request = MorningSummaryRequest()
        
        # Test with non-list events
        with pytest.raises(ValueError, match="Events must be a list"):
            await service.generate_summary("not-a-list", request)

    def test_service_when_focus_time_detection_then_accurate(self, service):
        """Test Focus Time detection accuracy."""
        for keyword in FOCUS_TIME_KEYWORDS:
            event = LiteCalendarEvent(
                id="test",
                subject=f"Morning {keyword.title()} Block",
                start=LiteDateTimeInfo(
                    date_time=datetime.now(timezone.utc),
                    time_zone="UTC",
                ),
                end=LiteDateTimeInfo(
                    date_time=datetime.now(timezone.utc),
                    time_zone="UTC",
                ),
            )
            
            assert service._is_focus_time(event) is True

    def test_service_when_caching_then_performance_improved(self, service):
        """Test caching functionality improves performance."""
        events = []
        request = MorningSummaryRequest()
        
        # Generate cache key
        cache_key = service._get_cache_key(events, request)
        assert isinstance(cache_key, str)
        
        # Test cache miss
        cached_result = service._get_cached_result(cache_key)
        assert cached_result is None
        
        # Test cache storage and retrieval
        mock_result = MorningSummaryResult(
            timeframe_start=datetime.now(timezone.utc),
            timeframe_end=datetime.now(timezone.utc),
            total_meetings_equivalent=0.0,
            early_start_flag=False,
            density=DensityLevel.LIGHT,
            speech_text="Test speech",
            metadata={
                "preview_for": "tomorrow_morning",
                "generation_context": {
                    "delivery_time": "evening",
                    "reference_day": "tomorrow",
                },
            },
        )
        
        service._cache_result(cache_key, mock_result)
        
        cached_result = service._get_cached_result(cache_key)
        assert cached_result is not None
        assert cached_result.speech_text == "Test speech"


class TestMorningSummaryResult:
    """Tests for MorningSummaryResult properties and methods."""

    def test_result_when_early_start_then_wake_up_recommendation(self):
        """Test wake-up recommendation calculation."""
        early_meeting = MeetingInsight(
            meeting_id="early",
            subject="Early Meeting",
            start_time=datetime(2023, 12, 1, 7, 0, tzinfo=timezone.utc),
            end_time=datetime(2023, 12, 1, 8, 0, tzinfo=timezone.utc),
        )
        
        result = MorningSummaryResult(
            timeframe_start=datetime(2023, 12, 1, 6, 0, tzinfo=timezone.utc),
            timeframe_end=datetime(2023, 12, 1, 12, 0, tzinfo=timezone.utc),
            total_meetings_equivalent=1.0,
            early_start_flag=True,
            density=DensityLevel.LIGHT,
            meeting_insights=[early_meeting],
            speech_text="Test speech",
            metadata={
                "preview_for": "tomorrow_morning",
                "generation_context": {
                    "delivery_time": "evening",
                    "reference_day": "tomorrow",
                },
            },
        )
        
        wake_up_time = result.wake_up_recommendation_time
        assert wake_up_time is not None
        
        # Should be 90 minutes before meeting, but minimum 6:00 AM
        expected_wake_up = datetime(2023, 12, 1, 6, 0, tzinfo=timezone.utc)
        assert wake_up_time == expected_wake_up

    def test_result_when_no_early_start_then_no_wake_up_recommendation(self):
        """Test no wake-up recommendation when no early start."""
        result = MorningSummaryResult(
            timeframe_start=datetime(2023, 12, 1, 6, 0, tzinfo=timezone.utc),
            timeframe_end=datetime(2023, 12, 1, 12, 0, tzinfo=timezone.utc),
            total_meetings_equivalent=1.0,
            early_start_flag=False,
            density=DensityLevel.LIGHT,
            speech_text="Test speech",
            metadata={
                "preview_for": "tomorrow_morning",
                "generation_context": {
                    "delivery_time": "evening",
                    "reference_day": "tomorrow",
                },
            },
        )

        assert result.wake_up_recommendation_time is None

    def test_result_when_free_blocks_then_longest_identified(self):
        """Test longest free block identification."""
        short_block = FreeBlock(
            start_time=datetime(2023, 12, 1, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2023, 12, 1, 9, 30, tzinfo=timezone.utc),
            duration_minutes=30,
        )
        
        long_block = FreeBlock(
            start_time=datetime(2023, 12, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2023, 12, 1, 11, 30, tzinfo=timezone.utc),
            duration_minutes=90,
        )
        
        result = MorningSummaryResult(
            timeframe_start=datetime(2023, 12, 1, 6, 0, tzinfo=timezone.utc),
            timeframe_end=datetime(2023, 12, 1, 12, 0, tzinfo=timezone.utc),
            total_meetings_equivalent=0.0,
            early_start_flag=False,
            density=DensityLevel.LIGHT,
            free_blocks=[short_block, long_block],
            speech_text="Test speech",
            metadata={
                "preview_for": "tomorrow_morning",
                "generation_context": {
                    "delivery_time": "evening",
                    "reference_day": "tomorrow",
                },
            },
        )
        
        longest_block = result.longest_free_block
        assert longest_block is not None
        assert longest_block.duration_minutes == 90

    def test_result_when_metadata_then_contains_required_fields(self):
        """Test metadata contains required fields."""
        result = MorningSummaryResult(
            timeframe_start=datetime(2023, 12, 1, 6, 0, tzinfo=timezone.utc),
            timeframe_end=datetime(2023, 12, 1, 12, 0, tzinfo=timezone.utc),
            total_meetings_equivalent=0.0,
            early_start_flag=False,
            density=DensityLevel.LIGHT,
            speech_text="Test speech",
            metadata={
                "preview_for": "tomorrow_morning",
                "generation_context": {
                    "delivery_time": "evening",
                    "reference_day": "tomorrow",
                },
            },
        )

        # Check required metadata fields
        assert result.metadata["preview_for"] == "tomorrow_morning"
        assert result.metadata["generation_context"]["delivery_time"] == "evening"
        assert result.metadata["generation_context"]["reference_day"] == "tomorrow"


class TestServiceFactory:
    """Tests for service factory function."""

    def test_get_morning_summary_service_when_called_then_singleton(self):
        """Test service factory returns singleton instance."""
        service1 = get_morning_summary_service()
        service2 = get_morning_summary_service()
        
        assert service1 is service2
        assert isinstance(service1, MorningSummaryService)


class TestSpeechGeneration:
    """Tests for natural language speech generation (Story 5)."""

    @pytest.mark.asyncio
    async def test_speech_when_various_scenarios_then_evening_delivery_context(
        self, sample_events, mock_tomorrow_date
    ):
        """Test speech generation contains proper evening delivery context."""
        service = MorningSummaryService()
        
        with patch.object(service, "_get_tomorrow_date", return_value=mock_tomorrow_date):
            request = MorningSummaryRequest(timezone="UTC")
            result = await service.generate_summary(sample_events, request)
            
            speech = result.speech_text
            
            # Must start with evening greeting
            assert speech.startswith("Good evening.")
            
            # Must reference tomorrow throughout
            assert "tomorrow" in speech.lower()
            
            # Should not use first person (avoiding "your")
            # Should use second person appropriately
            assert "you" in speech.lower()

    @pytest.mark.asyncio
    async def test_speech_when_early_start_then_urgency_appropriate(self):
        """Test speech urgency for early start scenarios."""
        service = MorningSummaryService()
        
        # Very early meeting (7:00 AM)
        very_early_event = LiteCalendarEvent(
            id="very-early",
            subject="Very Early Meeting",
            start=LiteDateTimeInfo(
                date_time=datetime(2023, 12, 1, 7, 0, tzinfo=timezone.utc),
                time_zone="UTC",
            ),
            end=LiteDateTimeInfo(
                date_time=datetime(2023, 12, 1, 8, 0, tzinfo=timezone.utc),
                time_zone="UTC",
            ),
        )
        
        # Slightly early meeting (7:45 AM)
        early_event = LiteCalendarEvent(
            id="early",
            subject="Early Meeting",
            start=LiteDateTimeInfo(
                date_time=datetime(2023, 12, 1, 7, 45, tzinfo=timezone.utc),
                time_zone="UTC",
            ),
            end=LiteDateTimeInfo(
                date_time=datetime(2023, 12, 1, 8, 45, tzinfo=timezone.utc),
                time_zone="UTC",
            ),
        )
        
        mock_tomorrow = datetime(2023, 12, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        with patch.object(service, "_get_tomorrow_date", return_value=mock_tomorrow):
            request = MorningSummaryRequest(timezone="UTC")
            
            # Test very early
            result_very_early = await service.generate_summary([very_early_event], request)
            assert "very early" in result_very_early.speech_text.lower()
            
            # Test early but not very early
            result_early = await service.generate_summary([early_event], request)
            assert "early" in result_early.speech_text.lower()
            assert "very early" not in result_early.speech_text.lower()
