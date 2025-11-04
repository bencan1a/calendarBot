"""Test launch summary with meeting in progress scenario."""

import datetime
import pytest

from calendarbot_lite.alexa_presentation import PlainTextPresenter
from calendarbot_lite.alexa_types import AlexaDoneForDayInfo


@pytest.mark.unit
def test_plain_text_presenter_when_current_meeting_then_acknowledges_it() -> None:
    """Test that PlainTextPresenter acknowledges current meeting."""
    presenter = PlainTextPresenter()
    
    # Mock done_info
    done_info: AlexaDoneForDayInfo = {
        "has_meetings_today": True,
        "last_meeting_end_iso": "2024-01-15T14:00:00Z",
        "last_meeting_subject": "Afternoon Meeting",
    }
    
    # Mock current meeting (in progress)
    current_meeting = {
        "subject": "Morning Standup",
        "is_current": True,
    }
    
    # Mock next meeting
    next_meeting = {
        "subject": "Afternoon Meeting",
        "duration_spoken": "in 2 hours and 45 minutes",
        "seconds_until": 9900,
    }
    
    # Generate speech
    speech_text, ssml = presenter.format_launch_summary(
        done_info=done_info,
        primary_meeting=next_meeting,
        tz=None,
        request_tz=None,
        now=None,
        current_meeting=current_meeting,
    )
    
    # Verify speech acknowledges current meeting
    assert "currently" in speech_text.lower()
    assert "Morning Standup" in speech_text
    assert "Afternoon Meeting" in speech_text
    assert ssml is None  # PlainTextPresenter doesn't generate SSML


@pytest.mark.unit
def test_plain_text_presenter_when_no_current_meeting_then_shows_next() -> None:
    """Test that PlainTextPresenter shows next meeting when no current meeting."""
    presenter = PlainTextPresenter()
    
    # Mock done_info
    done_info: AlexaDoneForDayInfo = {
        "has_meetings_today": True,
        "last_meeting_end_iso": "2024-01-15T14:00:00Z",
        "last_meeting_subject": "Afternoon Meeting",
    }
    
    # Mock next meeting (no current meeting)
    next_meeting = {
        "subject": "Afternoon Meeting",
        "duration_spoken": "in 2 hours and 45 minutes",
        "seconds_until": 9900,
    }
    
    # Generate speech
    speech_text, ssml = presenter.format_launch_summary(
        done_info=done_info,
        primary_meeting=next_meeting,
        tz=None,
        request_tz=None,
        now=None,
        current_meeting=None,  # No current meeting
    )
    
    # Verify speech shows next meeting only
    assert "currently" not in speech_text.lower()
    assert "next meeting is Afternoon Meeting" in speech_text
    assert ssml is None


@pytest.mark.unit
def test_plain_text_presenter_when_current_meeting_no_next_then_shows_current_only() -> None:
    """Test that PlainTextPresenter shows current meeting when no next meeting."""
    presenter = PlainTextPresenter()
    
    # Mock done_info
    done_info: AlexaDoneForDayInfo = {
        "has_meetings_today": True,
        "last_meeting_end_iso": "2024-01-15T11:00:00Z",
        "last_meeting_subject": "Morning Standup",
    }
    
    # Mock current meeting (in progress, last meeting of the day)
    current_meeting = {
        "subject": "Morning Standup",
        "is_current": True,
    }
    
    # Generate speech (no next meeting)
    speech_text, ssml = presenter.format_launch_summary(
        done_info=done_info,
        primary_meeting=None,  # No next meeting
        tz=None,
        request_tz=None,
        now=None,
        current_meeting=current_meeting,
    )
    
    # Verify speech acknowledges current meeting
    assert "currently" in speech_text.lower()
    assert "Morning Standup" in speech_text
    assert ssml is None
