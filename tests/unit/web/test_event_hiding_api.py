"""Unit tests for event hiding API endpoints."""

from unittest.mock import MagicMock, patch

import pytest

from calendarbot.settings.models import EventFilterSettings
from calendarbot.web.server import WebRequestHandler


@pytest.fixture
def mock_settings_service():
    """Create a mock settings service for testing."""
    mock_service = MagicMock()
    filter_settings = EventFilterSettings()
    filter_settings.hidden_events = {"existing-id-1", "existing-id-2"}
    mock_service.get_filter_settings.return_value = filter_settings
    mock_service.update_filter_settings.side_effect = lambda x: x
    return mock_service


@pytest.fixture
def request_handler(mock_settings_service):
    """Create a request handler for testing."""
    mock_web_server = MagicMock()
    mock_web_server.settings_service = mock_settings_service
    handler = WebRequestHandler(web_server=mock_web_server)
    handler._send_json_response = MagicMock()
    handler._get_updated_whats_next_data = MagicMock(
        return_value={
            "layout_name": "whats-next-view",
            "current_events": [],
            "next_events": [],
            "status_info": {"last_update": "2023-01-01T00:00:00"},
        }
    )
    return handler


@pytest.fixture
def mock_whats_next_data():
    """Mock data for whats next updates."""
    return {
        "layout_name": "whats-next-view",
        "current_events": [],
        "next_events": [],
        "status_info": {"last_update": "2023-01-01T00:00:00"},
    }


class TestEventHidingAPI:
    """Test event hiding API endpoints."""

    def test_hide_event_success(self, request_handler, mock_settings_service):
        """Test successful event hiding with state verification."""
        params = {"graph_id": "test-graph-id"}
        initial_settings = mock_settings_service.get_filter_settings()
        initial_count = len(initial_settings.hidden_events)

        request_handler._handle_hide_event(mock_settings_service, params)

        # Verify state changes
        updated_settings = mock_settings_service.update_filter_settings.call_args[0][0]
        assert "test-graph-id" in updated_settings.hidden_events
        assert len(updated_settings.hidden_events) == initial_count + 1

        # Verify response
        args = request_handler._send_json_response.call_args[0]
        assert args[0] == 200
        assert args[1]["success"] is True
        assert args[1]["count"] == initial_count + 1

    def test_unhide_event_success(self, request_handler, mock_settings_service):
        """Test successful event unhiding with state verification."""
        params = {"graph_id": "existing-id-1"}
        initial_settings = mock_settings_service.get_filter_settings()
        initial_count = len(initial_settings.hidden_events)

        request_handler._handle_unhide_event(mock_settings_service, params)

        # Verify state changes
        updated_settings = mock_settings_service.update_filter_settings.call_args[0][0]
        assert "existing-id-1" not in updated_settings.hidden_events
        assert len(updated_settings.hidden_events) == initial_count - 1

        # Verify response
        args = request_handler._send_json_response.call_args[0]
        assert args[0] == 200
        assert args[1]["success"] is True
        assert args[1]["count"] == initial_count - 1

    @pytest.mark.parametrize(
        ("handler_method", "params", "expected_error"),
        [
            ("_handle_hide_event", {}, "Missing graph_id"),
            ("_handle_unhide_event", {}, "Missing graph_id"),
        ],
    )
    def test_missing_graph_id_error(
        self, request_handler, mock_settings_service, handler_method, params, expected_error
    ):
        """Test error handling for missing graph_id parameter."""
        getattr(request_handler, handler_method)(mock_settings_service, params)

        args = request_handler._send_json_response.call_args[0]
        assert args[0] == 400
        assert expected_error in args[1]["error"]
        mock_settings_service.update_filter_settings.assert_not_called()

    def test_get_hidden_events(self, request_handler, mock_settings_service):
        """Test getting hidden events list."""
        request_handler._handle_get_hidden_events(mock_settings_service)

        mock_settings_service.get_filter_settings.assert_called_once()
        args = request_handler._send_json_response.call_args[0]
        assert args[0] == 200
        assert args[1]["success"] is True
        assert args[1]["count"] == 2
        assert set(args[1]["hidden_events"]) == {"existing-id-1", "existing-id-2"}

    @pytest.mark.parametrize(
        ("handler_method", "graph_id", "expected_hidden"),
        [
            ("_handle_hide_event", "test-graph-id", True),
            ("_handle_unhide_event", "existing-id-1", False),
        ],
    )
    def test_data_fallback_handling(
        self, request_handler, mock_settings_service, handler_method, graph_id, expected_hidden
    ):
        """Test fallback response when data retrieval fails."""
        request_handler._get_updated_whats_next_data = MagicMock(
            side_effect=Exception("Data retrieval failed")
        )
        params = {"graph_id": graph_id}

        getattr(request_handler, handler_method)(mock_settings_service, params)

        args = request_handler._send_json_response.call_args[0]
        assert args[0] == 200
        assert args[1]["success"] is True
        assert args[1]["data"]["graph_id"] == graph_id
        assert args[1]["data"]["hidden"] is expected_hidden

    @pytest.mark.parametrize(
        ("handler_method", "expected_error_prefix"),
        [
            ("_handle_hide_event", "Failed to hide event"),
            ("_handle_unhide_event", "Failed to unhide event"),
        ],
    )
    def test_settings_error_handling(
        self, request_handler, mock_settings_service, handler_method, expected_error_prefix
    ):
        """Test error handling when settings service fails."""
        from calendarbot.settings.exceptions import SettingsError

        mock_settings_service.get_filter_settings.side_effect = SettingsError(
            "Settings unavailable"
        )
        params = {"graph_id": "test-graph-id"}

        getattr(request_handler, handler_method)(mock_settings_service, params)

        args = request_handler._send_json_response.call_args[0]
        assert args[0] == 500
        assert expected_error_prefix in args[1]["error"]
        assert "Settings unavailable" in args[1]["message"]

    def test_unhide_non_hidden_event(self, request_handler, mock_settings_service):
        """Test unhiding an event that wasn't hidden."""
        params = {"graph_id": "non-hidden-id"}
        request_handler._handle_unhide_event(mock_settings_service, params)

        args = request_handler._send_json_response.call_args[0]
        assert args[0] == 200
        assert args[1]["success"] is True
        assert "not hidden" in args[1]["message"]
        assert args[1]["count"] == 2  # No change to count

    def test_api_routing(self, request_handler):
        """Test API routing for event hiding endpoints."""
        request_handler._handle_hide_event = MagicMock()
        request_handler._handle_unhide_event = MagicMock()
        request_handler._handle_get_hidden_events = MagicMock()

        test_cases = [
            ("POST", "/api/events/hide", {"graph_id": "test-id"}, "_handle_hide_event"),
            ("POST", "/api/events/unhide", {"graph_id": "test-id"}, "_handle_unhide_event"),
            ("GET", "/api/events/hidden", {}, "_handle_get_hidden_events"),
        ]

        for method, path, params, expected_handler in test_cases:
            with patch.object(request_handler, "command", method):
                request_handler._handle_settings_api(path, params)
                getattr(request_handler, expected_handler).assert_called()
