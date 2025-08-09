"""Unit tests for the What's Next data API endpoint."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from calendarbot.display.whats_next_data_model import EventData, StatusInfo, WhatsNextViewModel
from calendarbot.web.server import WebRequestHandler, WebServer


class TestWhatsNextDataAPI(unittest.TestCase):
    """Test cases for the What's Next data API endpoint."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Create mock objects
        self.settings = MagicMock()
        self.display_manager = MagicMock()
        self.cache_manager = MagicMock()
        self.navigation_state = MagicMock()
        self.layout_registry = MagicMock()
        self.resource_manager = MagicMock()

        # Create web server instance
        self.web_server = WebServer(
            self.settings,
            self.display_manager,
            self.cache_manager,
            self.navigation_state,
            self.layout_registry,
            self.resource_manager,
        )

        # Create request handler
        self.handler = WebRequestHandler(web_server=self.web_server)

        # Mock the _send_json_response method
        self.mock_send_json_response = MagicMock()
        self.handler._send_json_response = self.mock_send_json_response

    def test_handle_whats_next_data_api_when_normal_request_then_returns_json_data(self) -> None:
        """Test that the API returns JSON data for a normal request."""
        # Create properly mocked events with timezone-aware datetime attributes
        current_time = datetime.now(timezone.utc)
        mock_events = []

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
            mock_events.append(mock_event)

        self.cache_manager.get_events_by_date_range = MagicMock()

        # Mock asyncio.run to return mock events
        with patch("asyncio.run", return_value=mock_events):
            # Mock the navigation state
            self.navigation_state.selected_date = datetime.now().date()
            self.navigation_state.get_display_date.return_value = "Monday, August 7"
            self.navigation_state.is_today.return_value = True

            # Mock the current layout
            self.web_server.get_current_layout = MagicMock(return_value="whats-next-view")

            # Call the API handler
            self.handler._handle_whats_next_data_api({})

            # Verify that _send_json_response was called with status 200
            self.mock_send_json_response.assert_called_once()
            args = self.mock_send_json_response.call_args[0]
            self.assertEqual(args[0], 200)

            # Verify that the response contains the expected keys
            response = args[1]
            self.assertIn("layout_name", response)
            self.assertIn("current_time", response)
            self.assertIn("display_date", response)
            self.assertIn("current_events", response)
            self.assertIn("next_events", response)
            self.assertIn("later_events", response)
            self.assertIn("status_info", response)
            self.assertIn("layout_config", response)

    def test_handle_whats_next_data_api_when_debug_time_provided_then_uses_debug_time(self) -> None:
        """Test that the API uses the provided debug_time parameter."""
        # Create properly mocked events with timezone-aware datetime attributes
        current_time = datetime.now(timezone.utc)
        mock_events = []

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
            mock_events.append(mock_event)

        self.cache_manager.get_events_by_date_range = MagicMock()

        # Mock asyncio.run to return mock events
        with patch("asyncio.run", return_value=mock_events):
            # Mock the navigation state
            self.navigation_state.selected_date = datetime.now().date()
            self.navigation_state.get_display_date.return_value = "Monday, August 7"
            self.navigation_state.is_today.return_value = True

            # Mock the current layout
            self.web_server.get_current_layout = MagicMock(return_value="whats-next-view")

            # Create a debug_time parameter (timezone-aware)
            debug_time = datetime.now(timezone.utc) + timedelta(hours=2)
            debug_time_str = debug_time.isoformat()

            # Call the API handler with debug_time
            self.handler._handle_whats_next_data_api({"debug_time": debug_time_str})

            # Verify that _send_json_response was called with status 200
            self.mock_send_json_response.assert_called_once()
            args = self.mock_send_json_response.call_args[0]
            self.assertEqual(args[0], 200)

    def test_handle_whats_next_data_api_when_invalid_debug_time_then_ignores_debug_time(
        self,
    ) -> None:
        """Test that the API ignores an invalid debug_time parameter."""
        # Create properly mocked events with timezone-aware datetime attributes
        current_time = datetime.now(timezone.utc)
        mock_events = []

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
            mock_events.append(mock_event)

        self.cache_manager.get_events_by_date_range = MagicMock()

        # Mock asyncio.run to return mock events
        with patch("asyncio.run", return_value=mock_events):
            # Mock the navigation state
            self.navigation_state.selected_date = datetime.now().date()
            self.navigation_state.get_display_date.return_value = "Monday, August 7"
            self.navigation_state.is_today.return_value = True

            # Mock the current layout
            self.web_server.get_current_layout = MagicMock(return_value="whats-next-view")

            # Call the API handler with invalid debug_time
            self.handler._handle_whats_next_data_api({"debug_time": "invalid-time"})

            # Verify that _send_json_response was called with status 200
            self.mock_send_json_response.assert_called_once()
            args = self.mock_send_json_response.call_args[0]
            self.assertEqual(args[0], 200)

    def test_handle_whats_next_data_api_when_web_server_not_available_then_returns_error(
        self,
    ) -> None:
        """Test that the API returns an error when the web server is not available."""
        # Set web_server to None
        self.handler.web_server = None

        # Call the API handler
        self.handler._handle_whats_next_data_api({})

        # Verify that _send_json_response was called with status 500
        self.mock_send_json_response.assert_called_once()
        args = self.mock_send_json_response.call_args[0]
        self.assertEqual(args[0], 500)
        self.assertIn("error", args[1])
        self.assertEqual(args[1]["error"], "Web server not available")

    def test_handle_whats_next_data_api_when_exception_occurs_then_returns_error(self) -> None:
        """Test that the API returns an error when an exception occurs."""
        # Mock the cache manager to raise an exception
        self.cache_manager.get_events_by_date_range = MagicMock(
            side_effect=Exception("Test exception")
        )

        # Mock asyncio.run to propagate the exception
        with patch("asyncio.run", side_effect=Exception("Test exception")):
            # Mock the navigation state
            self.navigation_state.selected_date = datetime.now().date()

            # Mock the current layout
            self.web_server.get_current_layout = MagicMock(return_value="whats-next-view")

            # Call the API handler
            self.handler._handle_whats_next_data_api({})

            # Verify that _send_json_response was called with status 500
            self.mock_send_json_response.assert_called_once()
            args = self.mock_send_json_response.call_args[0]
            self.assertEqual(args[0], 500)
            self.assertIn("error", args[1])

    def test_view_model_to_dict_when_valid_view_model_then_returns_correct_dict(self) -> None:
        """Test that _view_model_to_dict correctly converts a WhatsNextViewModel to a dictionary."""
        # Create a test view model
        current_time = datetime.now(timezone.utc)

        # Create event data
        event1 = EventData(
            subject="Test Event 1",
            start_time=current_time + timedelta(minutes=30),
            end_time=current_time + timedelta(minutes=60),
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
            start_time=current_time - timedelta(minutes=30),
            end_time=current_time + timedelta(minutes=30),
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
            last_update=current_time,
            is_cached=False,
            connection_status="connected",
            interactive_mode=True,
            selected_date="Monday, August 7",
        )

        # Create view model
        view_model = WhatsNextViewModel(
            current_time=current_time,
            display_date="Monday, August 7",
            next_events=[event1],
            current_events=[event2],
            later_events=[],
            status_info=status_info,
        )

        # Mock the current layout
        self.web_server.get_current_layout = MagicMock(return_value="whats-next-view")

        # Convert view model to dictionary
        result = self.handler._view_model_to_dict(view_model)

        # Verify the result
        self.assertEqual(result["layout_name"], "whats-next-view")
        self.assertEqual(result["display_date"], "Monday, August 7")
        self.assertEqual(len(result["next_events"]), 1)
        self.assertEqual(len(result["current_events"]), 1)
        self.assertEqual(len(result["later_events"]), 0)

        # Verify event data
        next_event = result["next_events"][0]
        self.assertEqual(
            next_event["title"], "Test Event 1"
        )  # Implementation uses 'title' not 'subject'
        self.assertEqual(next_event["graph_id"], "test-graph-id-1")

        current_event = result["current_events"][0]
        self.assertEqual(
            current_event["title"], "Test Event 2"
        )  # Implementation uses 'title' not 'subject'
        self.assertEqual(current_event["graph_id"], "test-graph-id-2")

        # Verify status info
        status = result["status_info"]
        self.assertEqual(status["connection_status"], "connected")
        self.assertEqual(status["selected_date"], "Monday, August 7")


if __name__ == "__main__":
    unittest.main()
