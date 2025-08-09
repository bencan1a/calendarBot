"""Unit tests for event hiding API endpoints."""

from unittest.mock import MagicMock, patch

import pytest

from calendarbot.settings.models import EventFilterSettings
from calendarbot.web.server import WebRequestHandler


@pytest.fixture
def mock_settings_service():
    """Create a mock settings service for testing."""
    mock_service = MagicMock()

    # Set up filter settings with some hidden events
    filter_settings = EventFilterSettings()
    filter_settings.hidden_events = {"existing-id-1", "existing-id-2"}

    # Configure the mock to return our filter settings
    mock_service.get_filter_settings.return_value = filter_settings

    # Configure update_filter_settings to return the updated settings
    mock_service.update_filter_settings.side_effect = lambda x: x

    return mock_service


@pytest.fixture
def mock_web_server():
    """Create a mock web server for testing."""
    mock_server = MagicMock()
    return mock_server


@pytest.fixture
def request_handler(mock_web_server, mock_settings_service):
    """Create a request handler for testing."""
    handler = WebRequestHandler(web_server=mock_web_server)
    handler._send_json_response = MagicMock()

    # Set up the mock web server to return our mock settings service
    mock_web_server.settings_service = mock_settings_service

    return handler


def test_handle_hide_event_success(request_handler, mock_settings_service):
    """Test successful event hiding - verify actual state changes."""
    # Set up test data
    params = {"graph_id": "test-graph-id"}

    # Get initial state
    initial_settings = mock_settings_service.get_filter_settings()
    initial_hidden_count = len(initial_settings.hidden_events)

    # Mock _get_updated_whats_next_data to return sample data
    request_handler._get_updated_whats_next_data = MagicMock(
        return_value={
            "layout_name": "whats-next-view",
            "current_events": [],
            "next_events": [],
            "status_info": {"last_update": "2023-01-01T00:00:00"},
        }
    )

    # Call the handler
    request_handler._handle_hide_event(mock_settings_service, params)

    # Verify the event was actually added to hidden events
    updated_settings_call = mock_settings_service.update_filter_settings.call_args[0][0]
    assert "test-graph-id" in updated_settings_call.hidden_events
    assert len(updated_settings_call.hidden_events) == initial_hidden_count + 1

    # Verify the response reflects the actual state
    request_handler._send_json_response.assert_called_once()
    args = request_handler._send_json_response.call_args[0]
    assert args[0] == 200
    assert args[1]["success"] is True
    assert args[1]["count"] == initial_hidden_count + 1  # Verify actual count
    assert "data" in args[1]
    assert args[1]["data"]["layout_name"] == "whats-next-view"


def test_handle_hide_event_missing_graph_id(request_handler, mock_settings_service):
    """Test event hiding with missing graph_id."""
    # Set up test data with missing graph_id
    params = {}

    # Call the handler
    request_handler._handle_hide_event(mock_settings_service, params)

    # Verify error response
    request_handler._send_json_response.assert_called_once()
    args = request_handler._send_json_response.call_args[0]
    assert args[0] == 400
    assert "error" in args[1]
    assert "Missing graph_id" in args[1]["error"]

    # Verify settings service was not called
    mock_settings_service.update_filter_settings.assert_not_called()


def test_handle_unhide_event_success(request_handler, mock_settings_service):
    """Test successful event unhiding - verify actual state changes."""
    # Set up test data for an existing hidden event
    params = {"graph_id": "existing-id-1"}

    # Get initial state
    initial_settings = mock_settings_service.get_filter_settings()
    initial_hidden_count = len(initial_settings.hidden_events)
    assert "existing-id-1" in initial_settings.hidden_events  # Verify it's initially hidden

    # Mock _get_updated_whats_next_data to return sample data
    request_handler._get_updated_whats_next_data = MagicMock(
        return_value={
            "layout_name": "whats-next-view",
            "current_events": [],
            "next_events": [],
            "status_info": {"last_update": "2023-01-01T00:00:00"},
        }
    )

    # Call the handler
    request_handler._handle_unhide_event(mock_settings_service, params)

    # Verify the event was actually removed from hidden events
    updated_settings_call = mock_settings_service.update_filter_settings.call_args[0][0]
    assert "existing-id-1" not in updated_settings_call.hidden_events
    assert len(updated_settings_call.hidden_events) == initial_hidden_count - 1

    # Verify the response reflects the actual state
    request_handler._send_json_response.assert_called_once()
    args = request_handler._send_json_response.call_args[0]
    assert args[0] == 200
    assert args[1]["success"] is True
    assert args[1]["count"] == initial_hidden_count - 1  # Verify actual count
    assert "data" in args[1]
    assert args[1]["data"]["layout_name"] == "whats-next-view"


def test_handle_unhide_event_not_hidden(request_handler, mock_settings_service):
    """Test unhiding an event that wasn't hidden."""
    # Set up test data for a non-hidden event
    params = {"graph_id": "non-hidden-id"}

    # Call the handler
    request_handler._handle_unhide_event(mock_settings_service, params)

    # Verify the settings were still updated
    mock_settings_service.get_filter_settings.assert_called_once()
    mock_settings_service.update_filter_settings.assert_called_once()

    # Verify the response
    request_handler._send_json_response.assert_called_once()
    args = request_handler._send_json_response.call_args[0]
    assert args[0] == 200
    assert args[1]["success"] is True
    assert "message" in args[1]
    assert "not hidden" in args[1]["message"]
    assert args[1]["count"] == 2  # No change to count


def test_handle_unhide_event_missing_graph_id(request_handler, mock_settings_service):
    """Test event unhiding with missing graph_id."""
    # Set up test data with missing graph_id
    params = {}

    # Call the handler
    request_handler._handle_unhide_event(mock_settings_service, params)

    # Verify error response
    request_handler._send_json_response.assert_called_once()
    args = request_handler._send_json_response.call_args[0]
    assert args[0] == 400
    assert "error" in args[1]
    assert "Missing graph_id" in args[1]["error"]

    # Verify settings service was not called
    mock_settings_service.update_filter_settings.assert_not_called()


def test_handle_get_hidden_events(request_handler, mock_settings_service):
    """Test getting hidden events."""
    # Call the handler
    request_handler._handle_get_hidden_events(mock_settings_service)

    # Verify the settings service was called
    mock_settings_service.get_filter_settings.assert_called_once()

    # Verify the response
    request_handler._send_json_response.assert_called_once()
    args = request_handler._send_json_response.call_args[0]
    assert args[0] == 200
    assert args[1]["success"] is True
    assert "hidden_events" in args[1]
    assert "count" in args[1]
    assert args[1]["count"] == 2
    assert set(args[1]["hidden_events"]) == {"existing-id-1", "existing-id-2"}


def test_handle_settings_api_routing(request_handler):
    """Test API routing for event hiding endpoints."""
    # Mock the handler methods


def test_handle_hide_event_data_fallback(request_handler, mock_settings_service):
    """Test event hiding with data retrieval fallback."""
    # Set up test data
    params = {"graph_id": "test-graph-id"}

    # Mock _get_updated_whats_next_data to raise an exception
    request_handler._get_updated_whats_next_data = MagicMock(
        side_effect=Exception("Data retrieval failed")
    )

    # Call the handler
    request_handler._handle_hide_event(mock_settings_service, params)

    # Verify the event was still hidden
    mock_settings_service.get_filter_settings.assert_called_once()
    mock_settings_service.update_filter_settings.assert_called_once()

    # Verify the fallback response
    request_handler._send_json_response.assert_called_once()
    args = request_handler._send_json_response.call_args[0]
    assert args[0] == 200
    assert args[1]["success"] is True
    assert "count" in args[1]
    assert "data" in args[1]
    assert args[1]["data"]["graph_id"] == "test-graph-id"
    assert args[1]["data"]["hidden"] is True


def test_handle_unhide_event_data_fallback(request_handler, mock_settings_service):
    """Test event unhiding with data retrieval fallback."""
    # Set up test data for an existing hidden event
    params = {"graph_id": "existing-id-1"}

    # Mock _get_updated_whats_next_data to raise an exception
    request_handler._get_updated_whats_next_data = MagicMock(
        side_effect=Exception("Data retrieval failed")
    )

    # Call the handler
    request_handler._handle_unhide_event(mock_settings_service, params)

    # Verify the event was still unhidden
    mock_settings_service.get_filter_settings.assert_called_once()
    mock_settings_service.update_filter_settings.assert_called_once()

    # Verify the fallback response
    request_handler._send_json_response.assert_called_once()
    args = request_handler._send_json_response.call_args[0]
    assert args[0] == 200
    assert args[1]["success"] is True
    assert "count" in args[1]
    assert "data" in args[1]
    assert args[1]["data"]["graph_id"] == "existing-id-1"
    assert args[1]["data"]["hidden"] is False


def test_handle_hide_event_settings_error_json_response(request_handler, mock_settings_service):
    """Test event hiding with settings error returns proper JSON."""
    from calendarbot.settings.exceptions import SettingsError

    # Set up test data
    params = {"graph_id": "test-graph-id"}

    # Mock settings service to raise an error
    mock_settings_service.get_filter_settings.side_effect = SettingsError("Settings unavailable")

    # Call the handler
    request_handler._handle_hide_event(mock_settings_service, params)

    # Verify error response is JSON
    request_handler._send_json_response.assert_called_once()
    args = request_handler._send_json_response.call_args[0]
    assert args[0] == 500
    assert "error" in args[1]
    assert "Failed to hide event" in args[1]["error"]
    assert "message" in args[1]
    assert "Settings unavailable" in args[1]["message"]


def test_handle_unhide_event_settings_error_json_response(request_handler, mock_settings_service):
    """Test event unhiding with settings error returns proper JSON."""
    from calendarbot.settings.exceptions import SettingsError

    # Set up test data
    params = {"graph_id": "test-graph-id"}

    # Mock settings service to raise an error
    mock_settings_service.get_filter_settings.side_effect = SettingsError("Settings unavailable")

    # Call the handler
    request_handler._handle_unhide_event(mock_settings_service, params)

    # Verify error response is JSON
    request_handler._send_json_response.assert_called_once()
    args = request_handler._send_json_response.call_args[0]
    assert args[0] == 500
    assert "error" in args[1]
    assert "Failed to unhide event" in args[1]["error"]
    assert "message" in args[1]
    assert "Settings unavailable" in args[1]["message"]
    request_handler._handle_hide_event = MagicMock()
    request_handler._handle_unhide_event = MagicMock()
    request_handler._handle_get_hidden_events = MagicMock()

    # Create a mock settings service
    mock_settings_service = MagicMock()

    # Test hide event endpoint
    with patch.object(request_handler, "command", "POST"):
        request_handler._handle_settings_api("/api/events/hide", {"graph_id": "test-id"})
        request_handler._handle_hide_event.assert_called_once()

    # Test unhide event endpoint
    with patch.object(request_handler, "command", "POST"):
        request_handler._handle_settings_api("/api/events/unhide", {"graph_id": "test-id"})
        request_handler._handle_unhide_event.assert_called_once()

    # Test get hidden events endpoint
    with patch.object(request_handler, "command", "GET"):
        request_handler._handle_settings_api("/api/events/hidden", {})
        request_handler._handle_get_hidden_events.assert_called_once()
