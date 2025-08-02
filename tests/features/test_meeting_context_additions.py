"""Additional unit tests for meeting context analysis features."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from calendarbot.features.meeting_context import (
    MeetingContextAnalyzer,
    calculate_preparation_time_needed,
    get_meeting_context_for_timeframe,
)
from calendarbot.ics.models import Attendee, CalendarEvent, DateTimeInfo, EventStatus, Location


class TestMeetingContextAnalyzerAdditional:
    """Additional test cases for MeetingContextAnalyzer class."""

    def test_generate_meeting_insight_when_exception_occurs_then_returns_none(self) -> None:
        """Test that exceptions in _generate_meeting_insight are caught and None is returned."""
        analyzer = MeetingContextAnalyzer()
        current_time = datetime.now(timezone.utc)
        
        # Create a meeting with problematic data that will cause an exception
        meeting = MagicMock(spec=CalendarEvent)
        meeting.id = "test-meeting"
        meeting.subject = "Test Meeting"
        meeting.start = MagicMock()
        # This will cause an AttributeError when accessing date_time
        meeting.start.date_time.side_effect = AttributeError("No date_time attribute")
        
        # The method should catch the exception and return None
        result = analyzer._generate_meeting_insight(meeting, current_time)
        assert result is None

    def test_analyze_upcoming_meetings_when_all_insights_none_then_returns_empty_list(self) -> None:
        """Test that analyze_upcoming_meetings returns empty list when all insights are None."""
        analyzer = MeetingContextAnalyzer()
        current_time = datetime.now(timezone.utc)
        
        # Create a meeting that will result in None insight
        far_meeting = CalendarEvent(
            id="far-meeting",
            subject="Future Meeting",
            start=DateTimeInfo(date_time=current_time + timedelta(hours=6), time_zone="UTC"),
            end=DateTimeInfo(date_time=current_time + timedelta(hours=7), time_zone="UTC"),
            show_as=EventStatus.BUSY,
        )
        
        # Mock _generate_meeting_insight to always return None
        with patch.object(analyzer, '_generate_meeting_insight', return_value=None):
            insights = analyzer.analyze_upcoming_meetings([far_meeting], current_time)
            
            # Should return an empty list since all insights are None
            assert isinstance(insights, list)
            assert len(insights) == 0

    def test_classify_meeting_type_when_virtual_meeting_then_returns_virtual(self) -> None:
        """Test classification of virtual meetings."""
        analyzer = MeetingContextAnalyzer()
        base_time = datetime.now(timezone.utc)
        
        # Create a meeting that is online but doesn't match other types
        meeting = CalendarEvent(
            id="virtual",
            subject="General Discussion",  # Generic name that doesn't match other types
            start=DateTimeInfo(date_time=base_time, time_zone="UTC"),
            end=DateTimeInfo(date_time=base_time + timedelta(hours=1), time_zone="UTC"),
            show_as=EventStatus.BUSY,
            is_online_meeting=True,
            attendees=[Attendee(name="Person", email="person@example.com")],
        )
        
        meeting_type = analyzer._classify_meeting_type(meeting)
        assert meeting_type == "virtual"

    def test_analyze_upcoming_meetings_when_exception_in_filter_then_logs_and_raises(self) -> None:
        """Test error handling during meeting filtering."""
        analyzer = MeetingContextAnalyzer()
        current_time = datetime.now(timezone.utc)
        
        # Create a valid event
        event = CalendarEvent(
            id="test-event",
            subject="Test Meeting",
            start=DateTimeInfo(date_time=current_time + timedelta(hours=1), time_zone="UTC"),
            end=DateTimeInfo(date_time=current_time + timedelta(hours=2), time_zone="UTC"),
            show_as=EventStatus.BUSY,
        )
        
        # Mock _filter_upcoming_meetings to raise an exception
        with patch.object(analyzer, '_filter_upcoming_meetings') as mock_filter:
            mock_filter.side_effect = Exception("Filter error")
            
            # Should raise the exception
            with pytest.raises(Exception, match="Filter error"):
                analyzer.analyze_upcoming_meetings([event], current_time)