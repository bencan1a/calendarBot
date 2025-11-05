"""Integration test for launch summary with meeting in progress."""

import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from calendarbot_lite.alexa_handlers import LaunchSummaryHandler
from calendarbot_lite.alexa_presentation import PlainTextPresenter
from calendarbot_lite.lite_parser import LiteICSParser


@pytest.fixture
def test_settings() -> SimpleNamespace:
    """Minimal settings for integration tests."""
    return SimpleNamespace(
        rrule_worker_concurrency=2,
        max_occurrences_per_rule=500,
        expansion_days_window=365,
        expansion_time_budget_ms_per_rule=200,
        expansion_yield_frequency=50,
        rrule_expansion_days=30,
        enable_rrule_expansion=True,
        request_timeout=10,
        max_retries=2,
        retry_backoff_factor=1.5,
    )


@pytest.mark.integration
async def test_launch_summary_end_to_end_with_meeting_in_progress(
    test_settings: SimpleNamespace,
) -> None:
    """Test launch summary end-to-end with a meeting currently in progress."""
    # Load the meeting-in-progress fixture
    fixture_path = (
        Path(__file__).parent.parent.parent / "fixtures" / "ics" / "meeting-in-progress.ics"
    )

    with open(fixture_path, "r") as f:
        ics_content = f.read()

    # Parse the ICS content
    parser = LiteICSParser(test_settings)
    parse_result = parser.parse_ics_content(ics_content)
    events = parse_result.events

    # Verify we have both events
    assert len(events) == 2
    event_subjects = {e.subject for e in events}
    assert "Morning Standup" in event_subjects
    assert "Afternoon Meeting" in event_subjects
    
    # Set test time to be during the morning meeting (10:15 AM UTC)
    # Morning meeting: 10:00-11:00 AM UTC
    # Afternoon meeting: 1:00-2:00 PM UTC
    test_time = datetime.datetime(2025, 11, 5, 10, 15, 0, tzinfo=datetime.timezone.utc)
    mock_time_provider = Mock(return_value=test_time)
    
    # Create handler with PlainTextPresenter
    mock_skipped_store = Mock()
    mock_skipped_store.is_skipped = Mock(return_value=False)
    
    presenter = PlainTextPresenter()
    
    handler = LaunchSummaryHandler(
        bearer_token=None,
        time_provider=mock_time_provider,
        skipped_store=mock_skipped_store,
        response_cache=None,
        precompute_getter=None,
        presenter=presenter,  # pyright: ignore[reportCallIssue]
        duration_formatter=lambda s: f"in {s // 60} minutes" if s > 0 else "now",  # pyright: ignore[reportCallIssue]
        iso_serializer=lambda dt: dt.isoformat(),  # pyright: ignore[reportCallIssue]
    )
    
    # Create mock request
    mock_request = Mock()
    mock_request.query = {"tz": "UTC"}
    
    # Call the handler
    now = mock_time_provider()
    response = await handler.handle_request(mock_request, tuple(events), now)
    
    # Verify response
    assert response.status == 200
    
    import json
    data = json.loads(response.body)
    
    # Verify structure
    assert "speech_text" in data
    assert "has_meetings_today" in data
    assert "next_meeting" in data
    
    # Verify content
    assert data["has_meetings_today"] is True
    
    # Speech should acknowledge current meeting
    speech_text = data["speech_text"]
    assert "currently" in speech_text.lower()
    assert "Morning Standup" in speech_text
    
    # Speech should also mention next meeting
    assert "Afternoon Meeting" in speech_text
    
    # Next meeting should be the afternoon meeting
    next_meeting = data["next_meeting"]
    assert next_meeting is not None
    assert next_meeting["subject"] == "Afternoon Meeting"
    
    print(f"Speech: {speech_text}")
