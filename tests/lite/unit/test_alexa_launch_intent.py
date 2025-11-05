"""Unit tests for the new Alexa launch intent functionality."""

import datetime
from unittest.mock import Mock, patch

import pytest

from calendarbot_lite.alexa.alexa_skill_backend import handle_launch_intent, lambda_handler
from calendarbot_lite.api.server import (
    _check_bearer_token,
    _compute_last_meeting_end_for_today,
    _format_duration_spoken,
)

pytestmark = pytest.mark.unit


class TestAlexaLaunchIntent:
    """Test the new launch intent functionality."""

    @patch("calendarbot_lite.alexa.alexa_skill_backend.call_calendarbot_api")
    def test_handle_launch_intent_with_next_meeting(self, mock_api):
        """Test launch intent when there's a next meeting."""
        # Mock API response with next meeting and done-for-day info
        mock_api.return_value = {
            "speech_text": "Your next meeting is Team Standup in 15 minutes. You'll be done for the day at 6:00 pm.",
            "ssml": "<speak>Your next meeting is <emphasis level=\"moderate\">Team Standup</emphasis> in 15 minutes.</speak>",
            "has_meetings_today": True,
            "next_meeting": {
                "subject": "Team Standup",
                "start_iso": "2024-01-15T14:00:00Z",
                "seconds_until_start": 900,
                "duration_spoken": "in 15 minutes"
            },
            "done_for_day": {
                "has_meetings_today": True,
                "last_meeting_end_iso": "2024-01-15T18:00:00Z"
            }
        }

        response = handle_launch_intent()

        assert response.speech_text == "Your next meeting is Team Standup in 15 minutes. You'll be done for the day at 6:00 pm."
        assert response.ssml == "<speak>Your next meeting is <emphasis level=\"moderate\">Team Standup</emphasis> in 15 minutes.</speak>"
        assert response.card_title == "Calendar Summary"
        mock_api.assert_called_once_with("/api/alexa/launch-summary")

    @patch("calendarbot_lite.alexa.alexa_skill_backend.call_calendarbot_api")
    def test_handle_launch_intent_no_meetings_today(self, mock_api):
        """Test launch intent when there are no meetings today - should switch to morning summary mode."""
        # Mock the launch summary call (first call to check status)
        launch_response = {
            "speech_text": "No meetings today, you're free until Project Review in 2 days.",
            "has_meetings_today": False,
            "next_meeting": None,
            "done_for_day": {
                "has_meetings_today": False,
                "last_meeting_end_iso": None
            }
        }
        
        # Mock the morning summary call (second call when switching to morning summary mode)
        morning_response = {
            "speech_text": "Good evening. You have a completely free morning. Great opportunity for deep work.",
            "ssml": "<speak>Good evening. <emphasis level='moderate'>You have a completely free morning.</emphasis> Great opportunity for deep work.</speak>",
            "summary": {
                "preview_for": "tomorrow_morning",
                "total_meetings_equivalent": 0,
                "early_start_flag": False,
                "density": "light"
            }
        }
        
        # Configure mock to return different values for different calls
        mock_api.side_effect = [launch_response, morning_response]

        response = handle_launch_intent()

        # Should switch to morning summary mode and return morning summary content
        assert "completely free morning" in response.speech_text
        assert response.card_title == "Tomorrow Morning Summary"
        assert response.ssml is not None
        
        # Verify both API calls were made
        assert mock_api.call_count == 2
        mock_api.assert_any_call("/api/alexa/launch-summary")
        # Check that the second call is to morning summary with query parameters
        second_call_args = mock_api.call_args_list[1][0][0]
        assert "/api/alexa/morning-summary" in second_call_args
        assert "prefer_ssml=true" in second_call_args

    @patch("calendarbot_lite.alexa.alexa_skill_backend.call_calendarbot_api")
    def test_handle_launch_intent_api_error(self, mock_api):
        """Test launch intent when API call fails."""
        mock_api.side_effect = Exception("Connection failed")

        response = handle_launch_intent()

        assert response.speech_text == "Sorry, I'm having trouble accessing your calendar right now. Please try again later."
        assert response.ssml is None
        mock_api.assert_called_once_with("/api/alexa/launch-summary")

    @patch("calendarbot_lite.alexa.alexa_skill_backend.handle_launch_intent")
    def test_lambda_handler_launch_request(self, mock_handle_launch):
        """Test lambda_handler with LaunchRequest calls the new handler."""
        mock_response = Mock()
        mock_response.to_dict.return_value = {
            "version": "1.0",
            "response": {
                "outputSpeech": {"type": "PlainText", "text": "Test response"},
                "shouldEndSession": True
            }
        }
        mock_handle_launch.return_value = mock_response

        event = {"request": {"type": "LaunchRequest"}}
        result = lambda_handler(event, None)

        mock_handle_launch.assert_called_once()
        mock_response.to_dict.assert_called_once()
        assert result == mock_response.to_dict.return_value

    def test_lambda_handler_other_request_types_unchanged(self):
        """Test that other request types still work as before."""
        # Test help intent
        event = {"request": {"type": "IntentRequest", "intent": {"name": "AMAZON.HelpIntent"}}}
        result = lambda_handler(event, None)
        
        assert "I can help you with your calendar" in result["response"]["outputSpeech"]["text"]
        
        # Test invalid request
        event = {"invalid": "request"}
        result = lambda_handler(event, None)
        
        assert "invalid request" in result["response"]["outputSpeech"]["text"]


@pytest.mark.asyncio
class TestLaunchSummaryEndpoint:
    """Test the server-side launch summary endpoint logic."""

    def test_format_duration_spoken_function(self):
        """Test the _format_duration_spoken helper function."""
        # Test various durations
        assert _format_duration_spoken(30) == "in 30 seconds"
        assert _format_duration_spoken(60) == "in 1 minute"
        assert _format_duration_spoken(120) == "in 2 minutes"
        assert _format_duration_spoken(3600) == "in 1 hour"
        assert _format_duration_spoken(3660) == "in 1 hour and 1 minute"
        assert _format_duration_spoken(7200) == "in 2 hours"
        assert _format_duration_spoken(7320) == "in 2 hours and 2 minutes"
        assert _format_duration_spoken(-30) == "in the past"

    def test_compute_last_meeting_end_for_today_no_meetings(self):
        """Test done-for-day computation with no meetings."""
        result = _compute_last_meeting_end_for_today("America/Los_Angeles", (), None)
        
        assert result["has_meetings_today"] is False
        assert result["last_meeting_start_iso"] is None
        assert result["last_meeting_end_iso"] is None

    def test_compute_last_meeting_end_for_today_with_meetings(self):
        """Test done-for-day computation with meetings."""
        now = datetime.datetime.now(datetime.timezone.utc)
        today_meeting = {
            "meeting_id": "test-1",
            "start": now.replace(hour=14, minute=0, second=0, microsecond=0),
            "duration_seconds": 3600,
        }
        
        result = _compute_last_meeting_end_for_today("UTC", (today_meeting,), None)
        
        assert result["has_meetings_today"] is True
        assert result["last_meeting_start_iso"] is not None
        assert result["last_meeting_end_iso"] is not None

    def test_bearer_token_check_function(self):
        """Test the bearer token checking function."""
        # Mock request with valid token
        request = Mock()
        request.headers = {"Authorization": "Bearer test-token"}
        assert _check_bearer_token(request, "test-token") is True
        
        # Mock request with invalid token
        request.headers = {"Authorization": "Bearer wrong-token"}
        assert _check_bearer_token(request, "test-token") is False
        
        # Mock request without token
        request.headers = {}
        assert _check_bearer_token(request, "test-token") is False
        
        # Mock request with no required token
        assert _check_bearer_token(request, None) is True
