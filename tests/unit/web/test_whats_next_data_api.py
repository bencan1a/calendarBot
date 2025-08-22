"""Unit tests for the What's Next data API endpoint."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from calendarbot.display.whats_next_data_model import EventData, StatusInfo, WhatsNextViewModel
from calendarbot.web.server import WebRequestHandler, WebServer


@pytest.fixture
def mock_events():
    """Create mock events for testing."""
    current_time = datetime.now(timezone.utc)
    events = []
    for i in range(5):
        mock_event = MagicMock()
        mock_event.start_dt = current_time + timedelta(hours=i + 1)
        mock_event.end_dt = current_time + timedelta(hours=i + 2)
        mock_event.subject = f"Test Event {i + 1}"
        mock_event.graph_id = f"test-graph-id-{i + 1}"
        mock_event.location_display_name = f"Location {i + 1}"
        mock_event.is_current.return_value = False
        mock_event.is_upcoming.return_value = True
        mock_event.format_time_range.return_value = f"{10 + i}:00 AM - {11 + i}:00 AM"
        events.append(mock_event)
    return events


@pytest.fixture
def web_server():
    """Create web server instance with mocked dependencies."""
    return WebServer(
        MagicMock(),  # settings
        MagicMock(),  # display_manager
        MagicMock(),  # cache_manager
        MagicMock(),  # navigation_state
        MagicMock(),  # layout_registry
        MagicMock(),  # resource_manager
    )


@pytest.fixture
def handler(web_server):
    """Create request handler with mocked web server."""
    handler = WebRequestHandler(web_server=web_server)
    handler._send_json_response = MagicMock()
    return handler


class TestWhatsNextDataAPI:
    """Test cases for the What's Next data API endpoint."""

    def setup_method(self):
        """Set up common test data."""
        self.current_time = datetime.now(timezone.utc)
        self.debug_time = self.current_time + timedelta(hours=2)

    def _setup_successful_api_mocks(self, handler, web_server, mock_events):
        """Set up mocks for successful API calls."""
        web_server.cache_manager.get_events_by_date_range = MagicMock()
        web_server.navigation_state.selected_date = datetime.now().date()
        web_server.navigation_state.get_display_date.return_value = "Monday, August 7"
        web_server.navigation_state.is_today.return_value = True
        web_server.get_current_layout = MagicMock(return_value="whats-next-view")
        return patch("asyncio.run", return_value=mock_events)

    @pytest.mark.parametrize(
        ("params", "expected_status"),
        [
            ({}, 200),  # Normal request
            ({"debug_time": None}, 200),  # Debug time with valid format
            ({"debug_time": "invalid-time"}, 200),  # Invalid debug time - should be ignored
        ],
    )
    def test_whats_next_data_api_success_scenarios(
        self, handler, web_server, mock_events, params, expected_status
    ):
        """Test successful API scenarios with different parameters."""
        if params.get("debug_time") is None and "debug_time" in params:
            params["debug_time"] = self.debug_time.isoformat()

        with self._setup_successful_api_mocks(handler, web_server, mock_events):
            handler._handle_whats_next_data_api(params)

            args = handler._send_json_response.call_args[0]
            assert args[0] == expected_status

            if expected_status == 200:
                response = args[1]
                expected_keys = [
                    "layout_name",
                    "current_time",
                    "display_date",
                    "current_events",
                    "next_events",
                    "later_events",
                    "status_info",
                    "layout_config",
                ]
                for key in expected_keys:
                    assert key in response

    @pytest.mark.parametrize(
        ("error_scenario", "expected_status", "expected_error"),
        [
            ("no_web_server", 500, "Web server not available"),
            ("api_exception", 500, None),  # Error message varies
        ],
    )
    def test_whats_next_data_api_error_scenarios(
        self, handler, web_server, error_scenario, expected_status, expected_error
    ):
        """Test API error scenarios."""
        if error_scenario == "no_web_server":
            handler.web_server = None
        elif error_scenario == "api_exception":
            with patch("asyncio.run", side_effect=Exception("Test exception")):
                web_server.navigation_state.selected_date = datetime.now().date()
                web_server.get_current_layout = MagicMock(return_value="whats-next-view")
                handler._handle_whats_next_data_api({})

        if error_scenario == "no_web_server":
            handler._handle_whats_next_data_api({})

        args = handler._send_json_response.call_args[0]
        assert args[0] == expected_status
        assert "error" in args[1]
        if expected_error:
            assert args[1]["error"] == expected_error

    def test_view_model_to_dict_conversion(self, handler, web_server):
        """Test view model to dictionary conversion."""
        # Create test event data
        event1 = EventData(
            subject="Test Event 1",
            start_time=self.current_time + timedelta(minutes=30),
            end_time=self.current_time + timedelta(minutes=60),
            location="Test Location",
            is_current=False,
            is_upcoming=True,
            time_until_minutes=30,
            duration_minutes=30,
            formatted_time_range="10:30 AM - 11:00 AM",
            graph_id="test-graph-id-1",
        )

        event2 = EventData(
            subject="Test Event 2",
            start_time=self.current_time - timedelta(minutes=30),
            end_time=self.current_time + timedelta(minutes=30),
            location="Test Location 2",
            is_current=True,
            is_upcoming=False,
            time_until_minutes=None,
            duration_minutes=60,
            formatted_time_range="10:00 AM - 11:00 AM",
            graph_id="test-graph-id-2",
        )

        # Create status info
        status_info = StatusInfo(
            last_update=self.current_time,
            is_cached=False,
            connection_status="connected",
            selected_date="Monday, August 7",
        )

        # Create view model
        view_model = WhatsNextViewModel(
            current_time=self.current_time,
            display_date="Monday, August 7",
            next_events=[event1],
            current_events=[event2],
            later_events=[],
            status_info=status_info,
        )

        web_server.get_current_layout = MagicMock(return_value="whats-next-view")
        result = handler._view_model_to_dict(view_model)

        # Verify structure
        assert result["layout_name"] == "whats-next-view"
        assert result["display_date"] == "Monday, August 7"
        assert len(result["next_events"]) == 1
        assert len(result["current_events"]) == 1
        assert len(result["later_events"]) == 0

        # Verify event data
        next_event = result["next_events"][0]
        assert next_event["title"] == "Test Event 1"
        assert next_event["graph_id"] == "test-graph-id-1"

        current_event = result["current_events"][0]
        assert current_event["title"] == "Test Event 2"
        assert current_event["graph_id"] == "test-graph-id-2"

        # Verify status info
        status = result["status_info"]
        assert status["connection_status"] == "connected"
        assert status["selected_date"] == "Monday, August 7"
