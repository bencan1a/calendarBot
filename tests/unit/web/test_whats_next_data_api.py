"""Unit tests for the What's Next data API endpoint."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from calendarbot.display.whats_next_data_model import EventData, StatusInfo, WhatsNextViewModel
from calendarbot.web.server import WebRequestHandler, WebServer


class TestWhatsNextDataAPI:
    """Test cases for the What's Next data API endpoint."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        return MagicMock()

    @pytest.fixture
    def mock_display_manager(self):
        """Create mock display manager."""
        return MagicMock()

    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager."""
        return MagicMock()

    @pytest.fixture
    def mock_navigation_state(self):
        """Create mock navigation state."""
        return MagicMock()

    @pytest.fixture
    def mock_layout_registry(self):
        """Create mock layout registry."""
        return MagicMock()

    @pytest.fixture
    def mock_resource_manager(self):
        """Create mock resource manager."""
        return MagicMock()

    @pytest.fixture
    def web_server(
        self,
        mock_settings,
        mock_display_manager,
        mock_cache_manager,
        mock_navigation_state,
        mock_layout_registry,
        mock_resource_manager,
    ):
        """Create web server instance with mocked dependencies."""
        return WebServer(
            mock_settings,
            mock_display_manager,
            mock_cache_manager,
            mock_navigation_state,
            mock_layout_registry,
            mock_resource_manager,
        )

    @pytest.fixture
    def handler(self, web_server):
        """Create request handler with mocked web server."""
        handler = WebRequestHandler(web_server=web_server)
        # Mock the _send_json_response method
        handler._send_json_response = MagicMock()
        return handler

    @pytest.fixture
    def mock_events(self):
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

    def test_handle_whats_next_data_api_when_normal_request_then_returns_json_data(
        self, handler, web_server, mock_events, mock_navigation_state, mock_cache_manager
    ) -> None:
        """Test that the API returns JSON data for a normal request."""
        mock_cache_manager.get_events_by_date_range = MagicMock()

        # Mock asyncio.run to return mock events
        with patch("asyncio.run", return_value=mock_events):
            # Mock the navigation state
            mock_navigation_state.selected_date = datetime.now().date()
            mock_navigation_state.get_display_date.return_value = "Monday, August 7"
            mock_navigation_state.is_today.return_value = True

            # Mock the current layout
            web_server.get_current_layout = MagicMock(return_value="whats-next-view")

            # Call the API handler
            handler._handle_whats_next_data_api({})

            # Verify that _send_json_response was called with status 200
            handler._send_json_response.assert_called_once()
            args = handler._send_json_response.call_args[0]
            assert args[0] == 200

            # Verify that the response contains the expected keys
            response = args[1]
            assert "layout_name" in response
            assert "current_time" in response
            assert "display_date" in response
            assert "current_events" in response
            assert "next_events" in response
            assert "later_events" in response
            assert "status_info" in response
            assert "layout_config" in response

    def test_handle_whats_next_data_api_when_debug_time_provided_then_uses_debug_time(
        self, handler, web_server, mock_events, mock_navigation_state, mock_cache_manager
    ) -> None:
        """Test that the API uses the provided debug_time parameter."""
        mock_cache_manager.get_events_by_date_range = MagicMock()

        # Mock asyncio.run to return mock events
        with patch("asyncio.run", return_value=mock_events):
            # Mock the navigation state
            mock_navigation_state.selected_date = datetime.now().date()
            mock_navigation_state.get_display_date.return_value = "Monday, August 7"
            mock_navigation_state.is_today.return_value = True

            # Mock the current layout
            web_server.get_current_layout = MagicMock(return_value="whats-next-view")

            # Create a debug_time parameter (timezone-aware)
            debug_time = datetime.now(timezone.utc) + timedelta(hours=2)
            debug_time_str = debug_time.isoformat()

            # Call the API handler with debug_time
            handler._handle_whats_next_data_api({"debug_time": debug_time_str})

            # Verify that _send_json_response was called with status 200
            handler._send_json_response.assert_called_once()
            args = handler._send_json_response.call_args[0]
            assert args[0] == 200

    def test_handle_whats_next_data_api_when_invalid_debug_time_then_ignores_debug_time(
        self, handler, web_server, mock_events, mock_navigation_state, mock_cache_manager
    ) -> None:
        """Test that the API ignores an invalid debug_time parameter."""
        mock_cache_manager.get_events_by_date_range = MagicMock()

        # Mock asyncio.run to return mock events
        with patch("asyncio.run", return_value=mock_events):
            # Mock the navigation state
            mock_navigation_state.selected_date = datetime.now().date()
            mock_navigation_state.get_display_date.return_value = "Monday, August 7"
            mock_navigation_state.is_today.return_value = True

            # Mock the current layout
            web_server.get_current_layout = MagicMock(return_value="whats-next-view")

            # Call the API handler with invalid debug_time
            handler._handle_whats_next_data_api({"debug_time": "invalid-time"})

            # Verify that _send_json_response was called with status 200
            handler._send_json_response.assert_called_once()
            args = handler._send_json_response.call_args[0]
            assert args[0] == 200

    def test_handle_whats_next_data_api_when_web_server_not_available_then_returns_error(
        self, handler
    ) -> None:
        """Test that the API returns an error when the web server is not available."""
        # Set web_server to None
        handler.web_server = None

        # Call the API handler
        handler._handle_whats_next_data_api({})

        # Verify that _send_json_response was called with status 500
        handler._send_json_response.assert_called_once()
        args = handler._send_json_response.call_args[0]
        assert args[0] == 500
        assert "error" in args[1]
        assert args[1]["error"] == "Web server not available"

    def test_handle_whats_next_data_api_when_exception_occurs_then_returns_error(
        self, handler, mock_cache_manager, mock_navigation_state
    ) -> None:
        """Test that the API returns an error when an exception occurs."""
        # Mock the cache manager to raise an exception
        mock_cache_manager.get_events_by_date_range = MagicMock(
            side_effect=Exception("Test exception")
        )

        # Mock asyncio.run to propagate the exception
        with patch("asyncio.run", side_effect=Exception("Test exception")):
            # Mock the navigation state
            mock_navigation_state.selected_date = datetime.now().date()

            # Mock the current layout
            handler.web_server.get_current_layout = MagicMock(return_value="whats-next-view")

            # Call the API handler
            handler._handle_whats_next_data_api({})

            # Verify that _send_json_response was called with status 500
            handler._send_json_response.assert_called_once()
            args = handler._send_json_response.call_args[0]
            assert args[0] == 500
            assert "error" in args[1]

    def test_view_model_to_dict_when_valid_view_model_then_returns_correct_dict(
        self, handler, web_server
    ) -> None:
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
        web_server.get_current_layout = MagicMock(return_value="whats-next-view")

        # Convert view model to dictionary
        result = handler._view_model_to_dict(view_model)

        # Verify the result
        assert result["layout_name"] == "whats-next-view"
        assert result["display_date"] == "Monday, August 7"
        assert len(result["next_events"]) == 1
        assert len(result["current_events"]) == 1
        assert len(result["later_events"]) == 0

        # Verify event data
        next_event = result["next_events"][0]
        assert next_event["title"] == "Test Event 1"  # Implementation uses 'title' not 'subject'
        assert next_event["graph_id"] == "test-graph-id-1"

        current_event = result["current_events"][0]
        assert current_event["title"] == "Test Event 2"  # Implementation uses 'title' not 'subject'
        assert current_event["graph_id"] == "test-graph-id-2"

        # Verify status info
        status = result["status_info"]
        assert status["connection_status"] == "connected"
        assert status["selected_date"] == "Monday, August 7"
