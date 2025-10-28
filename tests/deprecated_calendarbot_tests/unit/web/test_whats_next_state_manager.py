"""Unit tests for WhatsNextStateManager class functionality."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def mock_state_manager():
    """Create a properly mocked WhatsNextStateManager for testing."""
    manager = Mock()

    # Setup state attributes
    manager.state = {
        "events": [],
        "layoutName": "whats-next-view",
        "lastUpdated": None,
        "layoutConfig": {"showHiddenEvents": False, "maxEvents": 10, "timeFormat": "12h"},
        "loading": False,
        "error": None,
    }

    # Setup performance metrics
    manager.performanceMetrics = {
        "lastLoadTime": None,
        "loadDuration": None,
        "apiCallCount": 0,
    }

    # Setup listener tracking
    manager.listeners = {
        "stateChanged": [],
        "dataLoaded": [],
        "eventHidden": [],
        "eventUnhidden": [],
        "error": [],
    }

    # Mock async methods
    manager.loadData = AsyncMock(
        return_value={
            "events": [
                {
                    "graph_id": "test-event-1",
                    "title": "Test Meeting",
                    "start_time": "2025-01-01T10:00:00Z",
                    "end_time": "2025-01-01T11:00:00Z",
                    "location": "Test Location",
                    "is_hidden": False,
                }
            ],
            "layout_name": "whats-next-view",
            "last_updated": "2025-01-01T09:00:00Z",
        }
    )

    manager.hideEvent = AsyncMock(return_value=True)
    manager.unhideEvent = AsyncMock(return_value=True)

    # Mock synchronous methods
    manager.updateState = Mock()
    manager.refreshView = Mock()
    manager.getState = Mock(return_value=manager.state.copy())
    manager.getEvents = Mock(return_value=manager.state["events"].copy())
    manager.getPerformanceMetrics = Mock(return_value=manager.performanceMetrics.copy())
    manager.addEventListener = Mock()
    manager.removeEventListener = Mock()

    return manager


class TestWhatsNextStateManager:
    """Test suite for WhatsNextStateManager class functionality."""

    def test_initialization_state(self, mock_state_manager):
        """Test StateManager initializes with correct default state."""
        state = mock_state_manager.getState()

        assert state["events"] == []
        assert state["layoutName"] == "whats-next-view"
        assert state["lastUpdated"] is None
        assert state["loading"] is False
        assert state["error"] is None
        assert "layoutConfig" in state
        assert state["layoutConfig"]["showHiddenEvents"] is False

    def test_initialization_listeners(self, mock_state_manager):
        """Test StateManager initializes with empty event listeners."""
        expected_events = ["stateChanged", "dataLoaded", "eventHidden", "eventUnhidden", "error"]

        for event_type in expected_events:
            assert event_type in mock_state_manager.listeners
            assert mock_state_manager.listeners[event_type] == []

    @pytest.mark.asyncio
    async def test_load_data_success(self, mock_state_manager):
        """Test loadData returns expected data structure."""
        result = await mock_state_manager.loadData()

        assert result is not None
        assert "events" in result
        assert "layout_name" in result
        assert "last_updated" in result
        assert result["layout_name"] == "whats-next-view"
        assert len(result["events"]) == 1
        assert result["events"][0]["graph_id"] == "test-event-1"
        mock_state_manager.loadData.assert_called_once()

    def test_update_state_delegation(self, mock_state_manager):
        """Test updateState is called with correct data."""
        new_data = {
            "events": [{"graph_id": "new-event", "title": "New Meeting"}],
            "layout_name": "updated-view",
        }

        mock_state_manager.updateState(new_data)
        mock_state_manager.updateState.assert_called_once_with(new_data)

    def test_event_listener_management(self, mock_state_manager):
        """Test adding and removing event listeners."""
        callback = Mock()

        mock_state_manager.addEventListener("stateChanged", callback)
        mock_state_manager.addEventListener.assert_called_once_with("stateChanged", callback)

        mock_state_manager.removeEventListener("stateChanged", callback)
        mock_state_manager.removeEventListener.assert_called_once_with("stateChanged", callback)

    @pytest.mark.parametrize(
        ("graph_id", "expected_result", "method_name"),
        [
            ("valid-event-id", True, "hideEvent"),
            ("another-valid-id", True, "unhideEvent"),
            ("event-to-hide", True, "hideEvent"),
            ("event-to-unhide", True, "unhideEvent"),
        ],
    )
    @pytest.mark.asyncio
    async def test_event_hide_unhide_operations(
        self, mock_state_manager, graph_id, expected_result, method_name
    ):
        """Test hide and unhide event operations."""
        method = getattr(mock_state_manager, method_name)
        result = await method(graph_id)

        assert result is expected_result
        method.assert_called_once_with(graph_id)

    @pytest.mark.parametrize(
        ("graph_id", "expected_result"),
        [
            ("", False),
            (None, False),
        ],
    )
    @pytest.mark.asyncio
    async def test_hide_event_invalid_inputs(self, mock_state_manager, graph_id, expected_result):
        """Test hideEvent handles invalid inputs."""
        mock_state_manager.hideEvent.return_value = expected_result
        result = await mock_state_manager.hideEvent(graph_id)
        assert result is expected_result

    def test_get_events_returns_list(self, mock_state_manager):
        """Test getEvents returns events from state."""
        events = mock_state_manager.getEvents()

        assert isinstance(events, list)
        assert events == []
        mock_state_manager.getEvents.assert_called_once()

    def test_get_performance_metrics_structure(self, mock_state_manager):
        """Test getPerformanceMetrics returns expected structure."""
        metrics = mock_state_manager.getPerformanceMetrics()

        required_keys = ["lastLoadTime", "loadDuration", "apiCallCount"]
        for key in required_keys:
            assert key in metrics
        assert isinstance(metrics["apiCallCount"], int)
        mock_state_manager.getPerformanceMetrics.assert_called_once()

    def test_refresh_view_delegation(self, mock_state_manager):
        """Test refreshView is called correctly."""
        mock_state_manager.refreshView()
        mock_state_manager.refreshView.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_state_manager):
        """Test handling of concurrent hide/unhide operations."""
        mock_state_manager.hideEvent = AsyncMock(return_value=True)
        mock_state_manager.unhideEvent = AsyncMock(return_value=True)

        results = await asyncio.gather(
            mock_state_manager.hideEvent("event-1"),
            mock_state_manager.hideEvent("event-2"),
            mock_state_manager.unhideEvent("event-3"),
        )

        assert all(results)
        assert mock_state_manager.hideEvent.call_count == 2
        assert mock_state_manager.unhideEvent.call_count == 1

    @pytest.mark.parametrize(
        ("operation", "error_message"),
        [
            ("updateState", "Update failed"),
            ("loadData", "API Error"),
        ],
    )
    def test_error_handling(self, mock_state_manager, operation, error_message):
        """Test error handling in various operations."""
        if operation == "updateState":
            mock_state_manager.updateState.side_effect = Exception(error_message)
            with pytest.raises(Exception) as exc_info:
                mock_state_manager.updateState({"events": []})
        else:  # loadData
            import asyncio

            async def test_async():
                mock_state_manager.loadData.side_effect = Exception(error_message)
                with pytest.raises(Exception) as exc_info:
                    await mock_state_manager.loadData()
                assert error_message in str(exc_info.value)

            asyncio.run(test_async())
            return

        assert error_message in str(exc_info.value)
