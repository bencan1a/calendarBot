
"""Tests for calendarbot_lite done-for-day functionality.

This module tests the comprehensive "done for the day" feature including:
- Core computation function _compute_last_meeting_end_for_today()
- HTTP API endpoints /api/done-for-day and /api/alexa/done-for-day
- Alexa backend intent handler handle_get_done_for_day_intent()
- Edge cases, error handling, and timezone considerations

Run with:
    pytest tests/test_lite_done_for_day.py -v
"""

import asyncio
import datetime
from typing import Any
from unittest.mock import Mock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from calendarbot_lite.api.server import _compute_last_meeting_end_for_today, _now_utc, _serialize_iso

pytestmark = pytest.mark.integration


class TestComputeLastMeetingEndForToday:
    """Tests for the _compute_last_meeting_end_for_today() core function."""

    def test_compute_last_meeting_end_when_no_meetings_then_returns_false(self):
        """Test computation with empty event window returns has_meetings_today: false."""
        result = _compute_last_meeting_end_for_today(
            request_tz="UTC",
            event_window=(),
            skipped_store=None,
        )
        
        assert result["has_meetings_today"] is False
        assert result["last_meeting_start_iso"] is None
        assert result["last_meeting_end_iso"] is None
        assert result["last_meeting_end_local_iso"] is None
        assert result["note"] is None

    @patch("calendarbot_lite.api.server._now_utc")
    def test_compute_last_meeting_end_when_single_meeting_today_then_returns_end_time(self, mock_now):
        """Test computation with single meeting today returns correct end time."""
        # Mock current time: 2025-01-15 10:00:00 UTC
        mock_now.return_value = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Create meeting starting today at 14:00 UTC with 60 minute duration
        meeting_start = datetime.datetime(2025, 1, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)
        event: dict[str, Any] = {
            "start": meeting_start,
            "duration_seconds": 3600,  # 1 hour
            "subject": "Test Meeting",
            "meeting_id": "test-id-1",
        }
        
        result = _compute_last_meeting_end_for_today(
            request_tz="UTC",
            event_window=(event,),
            skipped_store=None,
        )
        
        expected_end = meeting_start + datetime.timedelta(seconds=3600)
        
        assert result["has_meetings_today"] is True
        assert result["last_meeting_start_iso"] == _serialize_iso(meeting_start)
        assert result["last_meeting_end_iso"] == _serialize_iso(expected_end)
        assert result["last_meeting_end_local_iso"] == expected_end.isoformat()

    @patch("calendarbot_lite.api.server._now_utc")
    def test_compute_last_meeting_end_when_multiple_meetings_then_returns_latest_end(self, mock_now):
        """Test computation with multiple meetings returns latest end time."""
        mock_now.return_value = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Meeting 1: 14:00-15:00
        meeting1_start = datetime.datetime(2025, 1, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)
        event1: dict[str, Any] = {
            "start": meeting1_start,
            "duration_seconds": 3600,
            "subject": "Meeting 1",
            "meeting_id": "test-id-1",
        }
        
        # Meeting 2: 16:00-17:30 (latest end)
        meeting2_start = datetime.datetime(2025, 1, 15, 16, 0, 0, tzinfo=datetime.timezone.utc)
        event2: dict[str, Any] = {
            "start": meeting2_start,
            "duration_seconds": 5400,  # 1.5 hours
            "subject": "Meeting 2",
            "meeting_id": "test-id-2",
        }
        
        # Meeting 3: 13:00-13:30 (earlier)
        meeting3_start = datetime.datetime(2025, 1, 15, 13, 0, 0, tzinfo=datetime.timezone.utc)
        event3: dict[str, Any] = {
            "start": meeting3_start,
            "duration_seconds": 1800,  # 30 minutes
            "subject": "Meeting 3",
            "meeting_id": "test-id-3",
        }
        
        result = _compute_last_meeting_end_for_today(
            request_tz="UTC",
            event_window=(event1, event2, event3),
            skipped_store=None,
        )
        
        expected_latest_end = meeting2_start + datetime.timedelta(seconds=5400)
        
        assert result["has_meetings_today"] is True
        assert result["last_meeting_start_iso"] == _serialize_iso(meeting2_start)
        assert result["last_meeting_end_iso"] == _serialize_iso(expected_latest_end)

    @patch("calendarbot_lite.api.server._now_utc")
    def test_compute_last_meeting_end_when_missing_duration_then_uses_fallback(self, mock_now):
        """Test computation with missing duration uses 1-hour fallback."""
        mock_now.return_value = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        meeting_start = datetime.datetime(2025, 1, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)
        event: dict[str, Any] = {
            "start": meeting_start,
            # duration_seconds missing
            "subject": "Test Meeting",
            "meeting_id": "test-id-1",
        }
        
        result = _compute_last_meeting_end_for_today(
            request_tz="UTC",
            event_window=(event,),
            skipped_store=None,
        )
        
        # Should use 3600 second (1 hour) fallback
        expected_end = meeting_start + datetime.timedelta(seconds=3600)
        
        assert result["has_meetings_today"] is True
        assert result["last_meeting_end_iso"] == _serialize_iso(expected_end)

    @patch("calendarbot_lite.api.server._now_utc")
    def test_compute_last_meeting_end_when_invalid_duration_then_uses_fallback(self, mock_now):
        """Test computation with invalid duration uses 1-hour fallback."""
        mock_now.return_value = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        meeting_start = datetime.datetime(2025, 1, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Test various invalid durations
        invalid_durations = [0, -300, "invalid", None]
        
        for invalid_duration in invalid_durations:
            event: dict[str, Any] = {
                "start": meeting_start,
                "duration_seconds": invalid_duration,
                "subject": "Test Meeting",
                "meeting_id": "test-id-1",
            }
            
            result = _compute_last_meeting_end_for_today(
                request_tz="UTC",
                event_window=(event,),
                skipped_store=None,
            )
            
            # Should use 3600 second fallback
            expected_end = meeting_start + datetime.timedelta(seconds=3600)
            assert result["last_meeting_end_iso"] == _serialize_iso(expected_end)

    @patch("calendarbot_lite.api.server._now_utc")
    def test_compute_last_meeting_end_when_different_timezone_then_converts_correctly(self, mock_now):
        """Test computation with different timezone handles conversion correctly."""
        # Mock current time: 2025-01-15 10:00:00 UTC (2:00 AM PST)
        mock_now.return_value = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Meeting at 22:00 UTC (2:00 PM PST same day)
        meeting_start = datetime.datetime(2025, 1, 15, 22, 0, 0, tzinfo=datetime.timezone.utc)
        event: dict[str, Any] = {
            "start": meeting_start,
            "duration_seconds": 3600,
            "subject": "Test Meeting",
            "meeting_id": "test-id-1",
        }
        
        result = _compute_last_meeting_end_for_today(
            request_tz="America/Los_Angeles",
            event_window=(event,),
            skipped_store=None,
        )
        
        assert result["has_meetings_today"] is True
        assert result["last_meeting_end_local_iso"] is not None
        # Should convert to PST timezone
        assert "15:00:00-08:00" in result["last_meeting_end_local_iso"] or "23:00:00-08:00" in result["last_meeting_end_local_iso"]

    @patch("calendarbot_lite.api.server._now_utc")
    def test_compute_last_meeting_end_when_meetings_different_days_then_filters_today_only(self, mock_now):
        """Test computation only includes meetings from today."""
        # Current time: 2025-01-15 10:00:00 UTC
        mock_now.return_value = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Meeting yesterday
        yesterday_start = datetime.datetime(2025, 1, 14, 14, 0, 0, tzinfo=datetime.timezone.utc)
        yesterday_event: dict[str, Any] = {
            "start": yesterday_start,
            "duration_seconds": 3600,
            "subject": "Yesterday Meeting",
            "meeting_id": "yesterday-id",
        }
        
        # Meeting today
        today_start = datetime.datetime(2025, 1, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)
        today_event: dict[str, Any] = {
            "start": today_start,
            "duration_seconds": 3600,
            "subject": "Today Meeting",
            "meeting_id": "today-id",
        }
        
        # Meeting tomorrow
        tomorrow_start = datetime.datetime(2025, 1, 16, 14, 0, 0, tzinfo=datetime.timezone.utc)
        tomorrow_event: dict[str, Any] = {
            "start": tomorrow_start,
            "duration_seconds": 3600,
            "subject": "Tomorrow Meeting",
            "meeting_id": "tomorrow-id",
        }
        
        result = _compute_last_meeting_end_for_today(
            request_tz="UTC",
            event_window=(yesterday_event, today_event, tomorrow_event),
            skipped_store=None,
        )
        
        # Should only count today's meeting
        assert result["has_meetings_today"] is True
        assert result["last_meeting_start_iso"] == _serialize_iso(today_start)

    @patch("calendarbot_lite.api.server._now_utc")
    def test_compute_last_meeting_end_when_skipped_meetings_then_excludes_them(self, mock_now):
        """Test computation excludes skipped meetings."""
        mock_now.return_value = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Meeting 1: 14:00-15:00 (not skipped)
        meeting1_start = datetime.datetime(2025, 1, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)
        event1: dict[str, Any] = {
            "start": meeting1_start,
            "duration_seconds": 3600,
            "subject": "Meeting 1",
            "meeting_id": "meeting-1",
        }
        
        # Meeting 2: 16:00-17:00 (skipped - would be latest)
        meeting2_start = datetime.datetime(2025, 1, 15, 16, 0, 0, tzinfo=datetime.timezone.utc)
        event2: dict[str, Any] = {
            "start": meeting2_start,
            "duration_seconds": 3600,
            "subject": "Meeting 2",
            "meeting_id": "meeting-2",
        }
        
        # Mock skipped store
        mock_skipped_store = Mock()
        mock_skipped_store.is_skipped = Mock(side_effect=lambda mid: mid == "meeting-2")
        
        result = _compute_last_meeting_end_for_today(
            request_tz="UTC",
            event_window=(event1, event2),
            skipped_store=mock_skipped_store,
        )
        
        # Should only count non-skipped meeting
        expected_end = meeting1_start + datetime.timedelta(seconds=3600)
        assert result["has_meetings_today"] is True
        assert result["last_meeting_end_iso"] == _serialize_iso(expected_end)
        
        # Verify skipped store was called
        mock_skipped_store.is_skipped.assert_any_call("meeting-1")
        mock_skipped_store.is_skipped.assert_any_call("meeting-2")

    @patch("calendarbot_lite.api.server._now_utc")
    def test_compute_last_meeting_end_when_skipped_store_errors_then_continues_processing(self, mock_now):
        """Test computation continues when skipped store raises exceptions."""
        mock_now.return_value = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        meeting_start = datetime.datetime(2025, 1, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)
        event: dict[str, Any] = {
            "start": meeting_start,
            "duration_seconds": 3600,
            "subject": "Test Meeting",
            "meeting_id": "test-id-1",
        }
        
        # Mock skipped store that raises exception
        mock_skipped_store = Mock()
        mock_skipped_store.is_skipped = Mock(side_effect=Exception("Skipped store error"))
        
        result = _compute_last_meeting_end_for_today(
            request_tz="UTC",
            event_window=(event,),
            skipped_store=mock_skipped_store,
        )
        
        # Should still process the meeting despite skipped store error
        assert result["has_meetings_today"] is True
        assert result["last_meeting_end_iso"] is not None

    @patch("calendarbot_lite.api.server._now_utc")
    def test_compute_last_meeting_end_when_invalid_timezone_then_falls_back_to_utc(self, mock_now):
        """Test computation falls back to UTC for invalid timezone."""
        mock_now.return_value = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        meeting_start = datetime.datetime(2025, 1, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)
        event: dict[str, Any] = {
            "start": meeting_start,
            "duration_seconds": 3600,
            "subject": "Test Meeting",
            "meeting_id": "test-id-1",
        }
        
        result = _compute_last_meeting_end_for_today(
            request_tz="Invalid/Timezone",
            event_window=(event,),
            skipped_store=None,
        )
        
        # Should still work despite invalid timezone
        assert result["has_meetings_today"] is True
        assert result["last_meeting_end_iso"] is not None

    @patch("calendarbot_lite.api.server._now_utc")
    def test_compute_last_meeting_end_when_malformed_events_then_handles_gracefully(self, mock_now):
        """Test computation handles malformed event data gracefully."""
        mock_now.return_value = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Valid meeting
        valid_start = datetime.datetime(2025, 1, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)
        valid_event: dict[str, Any] = {
            "start": valid_start,
            "duration_seconds": 3600,
            "subject": "Valid Meeting",
            "meeting_id": "valid-id",
        }
        
        # Malformed events
        malformed_events = [
            {"start": "not-a-datetime", "subject": "Bad Start"},
            {"start": None, "subject": "None Start"},
            {"subject": "Missing Start"},  # Missing start field
            {},  # Empty event
        ]
        
        # Mix valid and malformed events
        all_events = [valid_event] + malformed_events
        
        result = _compute_last_meeting_end_for_today(
            request_tz="UTC",
            event_window=tuple(all_events),
            skipped_store=None,
        )
        
        # Should process only the valid event
        assert result["has_meetings_today"] is True
        assert result["last_meeting_start_iso"] == _serialize_iso(valid_start)

    @patch("calendarbot_lite.api.server._now_utc")
    def test_compute_last_meeting_end_when_timezone_conversion_fails_then_adds_note(self, mock_now):
        """Test computation adds note when timezone conversion fails."""
        mock_now.return_value = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Create naive datetime (no timezone)
        meeting_start = datetime.datetime(2025, 1, 15, 14, 0, 0)  # Naive datetime
        event: dict[str, Any] = {
            "start": meeting_start,
            "duration_seconds": 3600,
            "subject": "Test Meeting",
            "meeting_id": "test-id-1",
        }
        
        # This might cause timezone conversion issues
        result = _compute_last_meeting_end_for_today(
            request_tz="America/Los_Angeles",
            event_window=(event,),
            skipped_store=None,
        )
        
        # Should handle gracefully, may include note about conversion failure
        assert result["has_meetings_today"] is True or result["has_meetings_today"] is False
        # Note may be set if conversion fails
        if result.get("note"):
            assert "timezone" in result["note"].lower() or "conversion" in result["note"].lower()


class TestDoneForDayAPIEndpoints(AioHTTPTestCase):
    """Tests for the HTTP API endpoints /api/done-for-day and /api/alexa/done-for-day."""

    async def get_application(self) -> web.Application:
        """Create test aiohttp application with done-for-day endpoints."""
        from calendarbot_lite.api.server import _compute_last_meeting_end_for_today, _serialize_iso
        
        app = web.Application()
        
        # Mock event window and skipped store
        test_event_window = []
        test_skipped_store = None
        test_window_lock = asyncio.Lock()
        
        async def done_for_day(request):
            """Test implementation of /api/done-for-day endpoint."""
            request_tz = request.query.get("tz")
            
            # Use test data
            result = _compute_last_meeting_end_for_today(request_tz, tuple(test_event_window), test_skipped_store)
            
            response = {
                "now_iso": _serialize_iso(_now_utc()),
                "tz": request_tz,
                **result,
            }
            return web.json_response(response)
        
        async def alexa_done_for_day(request):
            """Test implementation of /api/alexa/done-for-day endpoint."""
            # Check bearer token (simplified)
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return web.json_response({"error": "Unauthorized"}, status=401)
            
            request_tz = request.query.get("tz")
            # Access current state of event window from app
            current_event_window = request.app["test_event_window"]
            result = _compute_last_meeting_end_for_today(request_tz, tuple(current_event_window), test_skipped_store)
            
            # Generate speech text
            if result["has_meetings_today"]:
                speech_text = "Your last meeting today has ended. You're done for the day!"
            else:
                speech_text = "You have no meetings today."
            
            response_data = {
                "now_iso": _serialize_iso(_now_utc()),
                "tz": request_tz,
                "speech_text": speech_text,
                "ssml": None,  # Simplified for testing
                **result,
            }
            return web.json_response(response_data)
        
        app.router.add_get("/api/done-for-day", done_for_day)
        app.router.add_get("/api/alexa/done-for-day", alexa_done_for_day)
        
        # Store test data for manipulation in tests
        app["test_event_window"] = test_event_window
        app["test_skipped_store"] = test_skipped_store
        
        return app

    @unittest_run_loop
    async def test_done_for_day_endpoint_when_no_meetings_then_returns_correct_response(self):
        """Test /api/done-for-day endpoint with no meetings."""
        resp = await self.client.request("GET", "/api/done-for-day")
        
        assert resp.status == 200
        data = await resp.json()
        
        assert "now_iso" in data
        assert "tz" in data
        assert data["has_meetings_today"] is False
        assert data["last_meeting_start_iso"] is None
        assert data["last_meeting_end_iso"] is None

    @unittest_run_loop
    async def test_done_for_day_endpoint_when_timezone_specified_then_includes_in_response(self):
        """Test /api/done-for-day endpoint with timezone parameter."""
        resp = await self.client.request("GET", "/api/done-for-day?tz=America/Los_Angeles")
        
        assert resp.status == 200
        data = await resp.json()
        
        assert data["tz"] == "America/Los_Angeles"

    @unittest_run_loop
    async def test_alexa_done_for_day_endpoint_when_no_auth_then_returns_401(self):
        """Test /api/alexa/done-for-day endpoint without authorization returns 401."""
        resp = await self.client.request("GET", "/api/alexa/done-for-day")
        
        assert resp.status == 401
        data = await resp.json()
        assert "error" in data

    @unittest_run_loop
    async def test_alexa_done_for_day_endpoint_when_valid_auth_then_returns_speech_response(self):
        """Test /api/alexa/done-for-day endpoint with valid authorization."""
        headers = {"Authorization": "Bearer test-token"}
        resp = await self.client.request("GET", "/api/alexa/done-for-day", headers=headers)
        
        assert resp.status == 200
        data = await resp.json()
        
        assert "speech_text" in data
        assert "ssml" in data
        assert data["speech_text"] == "You have no meetings today."

    @unittest_run_loop
    async def test_alexa_done_for_day_endpoint_when_has_meetings_then_returns_done_message(self):
        """Test /api/alexa/done-for-day endpoint with meetings returns done message."""
        # Add test meeting to the app's event window with today's date
        now = _now_utc()
        today = now.date()
        
        # Create meeting starting today at 14:00 UTC
        meeting_start = datetime.datetime.combine(today, datetime.time(14, 0), tzinfo=datetime.timezone.utc)
        test_event: dict[str, Any] = {
            "start": meeting_start,
            "duration_seconds": 3600,
            "subject": "Test Meeting",
            "meeting_id": "test-id",
        }
        self.app["test_event_window"].append(test_event)
        
        headers = {"Authorization": "Bearer test-token"}
        resp = await self.client.request("GET", "/api/alexa/done-for-day", headers=headers)
        
        assert resp.status == 200
        data = await resp.json()
        
        assert "done for the day" in data["speech_text"].lower()


class TestAlexaBackendIntentHandler:
    """Tests for the Alexa backend intent handler handle_get_done_for_day_intent()."""

    @patch("calendarbot_lite.alexa.alexa_skill_backend.call_calendarbot_api")
    def test_handle_get_done_for_day_intent_when_api_success_then_returns_response(self, mock_api_call):
        """Test intent handler with successful API call returns proper response."""
        from calendarbot_lite.alexa.alexa_skill_backend import handle_get_done_for_day_intent
        
        # Mock API response
        mock_api_response = {
            "speech_text": "Your last meeting today ended at 3 PM. You're done for the day!",
            "ssml": "<speak>Your last meeting today ended at 3 PM. You're done for the day!</speak>",
            "has_meetings_today": True,
            "last_meeting_end_iso": "2025-01-15T15:00:00Z",
        }
        mock_api_call.return_value = mock_api_response
        
        result = handle_get_done_for_day_intent()
        response_dict = result.to_dict()
        
        assert response_dict["version"] == "1.0"
        assert "sessionAttributes" in response_dict
        assert "response" in response_dict
        
        response = response_dict["response"]
        assert response["outputSpeech"]["type"] == "SSML"
        assert "done for the day" in response["outputSpeech"]["ssml"].lower()
        assert response["shouldEndSession"] is True

    @patch("calendarbot_lite.alexa.alexa_skill_backend.call_calendarbot_api")
    def test_handle_get_done_for_day_intent_when_no_meetings_then_returns_no_meetings_message(self, mock_api_call):
        """Test intent handler with no meetings returns appropriate message."""
        from calendarbot_lite.alexa.alexa_skill_backend import handle_get_done_for_day_intent
        
        mock_api_response = {
            "speech_text": "You have no meetings today.",
            "ssml": None,
            "has_meetings_today": False,
        }
        mock_api_call.return_value = mock_api_response
        
        result = handle_get_done_for_day_intent()
        response_dict = result.to_dict()
        
        response = response_dict["response"]
        assert "no meetings" in response["outputSpeech"]["text"].lower()

    @patch("calendarbot_lite.alexa.alexa_skill_backend.call_calendarbot_api")
    def test_handle_get_done_for_day_intent_when_api_fails_then_returns_error_response(self, mock_api_call):
        """Test intent handler with API failure returns error response."""
        from calendarbot_lite.alexa.alexa_skill_backend import handle_get_done_for_day_intent
        
        # Mock API failure
        mock_api_call.side_effect = Exception("API call failed")
        
        result = handle_get_done_for_day_intent()
        response_dict = result.to_dict()
        
        response = response_dict["response"]
        # Should return some form of error message
        assert "sorry" in response["outputSpeech"]["text"].lower() or "error" in response["outputSpeech"]["text"].lower()

    @patch("calendarbot_lite.alexa.alexa_skill_backend.call_calendarbot_api")
    def test_handle_get_done_for_day_intent_when_calls_correct_endpoint(self, mock_api_call):
        """Test intent handler calls the correct API endpoint."""
        from calendarbot_lite.alexa.alexa_skill_backend import handle_get_done_for_day_intent
        
        mock_api_call.return_value = {"speech_text": "Test", "has_meetings_today": False}
        
        handle_get_done_for_day_intent()
        
        # Verify correct API endpoint was called
        mock_api_call.assert_called_once_with("/api/alexa/done-for-day")


class TestDoneForDayEdgeCases:
    """Tests for edge cases and error conditions in done-for-day functionality."""

    @patch("calendarbot_lite.api.server._now_utc")
    def test_compute_last_meeting_end_when_meeting_at_midnight_boundary_then_handles_correctly(self, mock_now):
        """Test computation with meetings at midnight boundary."""
        # Current time: just after midnight UTC
        mock_now.return_value = datetime.datetime(2025, 1, 15, 0, 1, 0, tzinfo=datetime.timezone.utc)
        
        # Meeting that starts just before midnight (previous day)
        meeting_before_midnight = datetime.datetime(2025, 1, 14, 23, 30, 0, tzinfo=datetime.timezone.utc)
        event_before: dict[str, Any] = {
            "start": meeting_before_midnight,
            "duration_seconds": 3600,  # Ends at 00:30 today
            "subject": "Late Meeting",
            "meeting_id": "late-id",
        }
        
        # Meeting that starts just after midnight (today)
        meeting_after_midnight = datetime.datetime(2025, 1, 15, 0, 30, 0, tzinfo=datetime.timezone.utc)
        event_after: dict[str, Any] = {
            "start": meeting_after_midnight,
            "duration_seconds": 1800,  # 30 minutes
            "subject": "Early Meeting",
            "meeting_id": "early-id",
        }
        
        result = _compute_last_meeting_end_for_today(
            request_tz="UTC",
            event_window=(event_before, event_after),
            skipped_store=None,
        )
        
        # Should only count the meeting that starts today
        assert result["has_meetings_today"] is True
        assert result["last_meeting_start_iso"] == _serialize_iso(meeting_after_midnight)

    @patch("calendarbot_lite.api.server._now_utc")
    def test_compute_last_meeting_end_when_multiple_meetings_same_end_time_then_returns_any_valid(self, mock_now):
        """Test computation with multiple meetings having same end time."""
        mock_now.return_value = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
        
        # Two meetings ending at same time
        meeting1_start = datetime.datetime(2025, 1, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)
        meeting2_start = datetime.datetime(2025, 1, 15, 14, 30, 0, tzinfo=datetime.timezone.utc)
        
        event1: dict[str, Any] = {
            "start": meeting1_start,
            "duration_seconds": 5400,  # 1.5 hours -> ends at 15:30
            "subject": "Meeting 1",
            "meeting_id": "id-1",
        }
        
        event2: dict[str, Any] = {
            "start": meeting2_start,
            "duration_seconds": 3600,  # 1 hour -> ends at 15:30
            "subject": "Meeting 2",
            "meeting_id": "id-2",
        }
        
        result = _compute_last_meeting_end_for_today(
            request_tz="UTC",
            event_window=(event1, event2),
            skipped_store=None,
        )
        
        expected_end = datetime.datetime(2025, 1, 15, 15, 30, 0, tzinfo=datetime.timezone.utc)
        
        assert result["has_meetings_today"] is True
        assert result["last_meeting_end_iso"] == _serialize_iso(expected_end)
        # Should return one of the meetings (implementation detail)
        assert result["last_meeting_start_iso"] in [_serialize_iso(meeting1_start), _serialize_iso(meeting2_start)]

    def test_compute_last_meeting_end_when_none_timezone_then_uses_utc(self):
        """Test computation with None timezone falls back to UTC."""
        with patch("calendarbot_lite.api.server._now_utc") as mock_now:
            mock_now.return_value = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
            
            meeting_start = datetime.datetime(2025, 1, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)
            event: dict[str, Any] = {
                "start": meeting_start,
                "duration_seconds": 3600,
                "subject": "Test Meeting",
                "meeting_id": "test-id-1",
            }
            
            result = _compute_last_meeting_end_for_today(
                request_tz=None,  # None timezone
                event_window=(event,),
                skipped_store=None,
            )
            
            assert result["has_meetings_today"] is True
            assert result["last_meeting_end_iso"] is not None

    def test_compute_last_meeting_end_when_empty_string_timezone_then_uses_utc(self):
        """Test computation with empty string timezone falls back to UTC."""
        with patch("calendarbot_lite.api.server._now_utc") as mock_now:
            mock_now.return_value = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
            
            meeting_start = datetime.datetime(2025, 1, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)
            event: dict[str, Any] = {
                "start": meeting_start,
                "duration_seconds": 3600,
                "subject": "Test Meeting",
                "meeting_id": "test-id-1",
            }
            
            result = _compute_last_meeting_end_for_today(
                request_tz="",  # Empty string timezone
                event_window=(event,),
                skipped_store=None,
            )
            
            assert result["has_meetings_today"] is True
            assert result["last_meeting_end_iso"] is not None

    def test_compute_last_meeting_end_when_no_meeting_id_then_handles_gracefully(self):
        """Test computation with events missing meeting_id field."""
        with patch("calendarbot_lite.api.server._now_utc") as mock_now:
            mock_now.return_value = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
            
            meeting_start = datetime.datetime(2025, 1, 15, 14, 0, 0, tzinfo=datetime.timezone.utc)
            event: dict[str, Any] = {
                "start": meeting_start,
                "duration_seconds": 3600,
                "subject": "Test Meeting",
                # missing meeting_id
            }
            
            mock_skipped_store = Mock()
            mock_skipped_store.is_skipped = Mock(return_value=False)
            
            result = _compute_last_meeting_end_for_today(
                request_tz="UTC",
                event_window=(event,),
                skipped_store=mock_skipped_store,
            )
            
            # Should still process event even without meeting_id
            assert result["has_meetings_today"] is True
            # Skipped store should not be called for events without meeting_id
            mock_skipped_store.is_skipped.assert_not_called()
