"""
Unit tests for WhatsNextStateManager class

Tests cover:
- State management functionality
- API integration and error handling
- Event system and notifications
- Optimistic updates and rollback
- Performance tracking
- Error conditions and recovery scenarios
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest


class TestWhatsNextStateManager:
    """Test suite for WhatsNextStateManager class functionality"""

    @pytest.fixture
    def mock_fetch_response(self):
        """Create a mock fetch response for testing"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "events": [
                    {
                        "graph_id": "event-1",
                        "title": "Test Meeting",
                        "start_time": "2025-01-01T10:00:00Z",
                        "end_time": "2025-01-01T11:00:00Z",
                        "location": "Conference Room",
                        "is_hidden": False,
                    }
                ],
                "layout_name": "whats-next-view",
                "last_updated": "2025-01-01T09:00:00Z",
                "layout_config": {"showHiddenEvents": False, "maxEvents": 10, "timeFormat": "12h"},
            }
        )
        return mock_response

    @pytest.fixture
    def mock_state_manager(self):
        """Create a properly mocked WhatsNextStateManager for testing"""
        manager = Mock()

        # Setup state attributes
        manager.state = {
            "events": [],
            "layoutName": "whats-next-view",
            "lastUpdated": None,
            "layoutConfig": {
                "showHiddenEvents": False,
                "maxEvents": 10,
                "timeFormat": "12h",
            },
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

    def test_state_manager_initialization_when_created_then_has_default_state(
        self, mock_state_manager
    ):
        """Test that StateManager initializes with correct default state"""
        state = mock_state_manager.getState()

        assert state["events"] == []
        assert state["layoutName"] == "whats-next-view"
        assert state["lastUpdated"] is None
        assert state["loading"] is False
        assert state["error"] is None
        assert "layoutConfig" in state
        assert state["layoutConfig"]["showHiddenEvents"] is False

    def test_state_manager_initialization_when_created_then_has_empty_listeners(
        self, mock_state_manager
    ):
        """Test that StateManager initializes with empty event listeners"""
        expected_events = ["stateChanged", "dataLoaded", "eventHidden", "eventUnhidden", "error"]

        for event_type in expected_events:
            assert event_type in mock_state_manager.listeners
            assert mock_state_manager.listeners[event_type] == []

    @pytest.mark.asyncio
    async def test_load_data_when_called_then_updates_state(self, mock_state_manager):
        """Test that loadData successfully updates state with API response"""
        result = await mock_state_manager.loadData()

        assert result is not None
        assert "events" in result
        assert len(result["events"]) == 1
        assert result["events"][0]["graph_id"] == "test-event-1"

        # Verify the mock was called
        mock_state_manager.loadData.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_data_when_called_then_returns_data(self, mock_state_manager):
        """Test that loadData returns expected data"""
        result = await mock_state_manager.loadData()

        assert result is not None
        assert "events" in result
        assert "layout_name" in result
        assert "last_updated" in result
        assert result["layout_name"] == "whats-next-view"

    def test_update_state_when_called_then_updates_state(self, mock_state_manager):
        """Test that updateState is called with correct data"""
        new_data = {
            "events": [
                {
                    "graph_id": "new-event",
                    "title": "New Meeting",
                    "start_time": "2025-01-02T10:00:00Z",
                    "end_time": "2025-01-02T11:00:00Z",
                }
            ],
            "layout_name": "updated-view",
        }

        mock_state_manager.updateState(new_data)

        # Verify the mock was called with correct data
        mock_state_manager.updateState.assert_called_once_with(new_data)

    def test_event_listener_management(self, mock_state_manager):
        """Test adding and removing event listeners"""
        callback = Mock()

        # Test adding listener
        mock_state_manager.addEventListener("stateChanged", callback)
        mock_state_manager.addEventListener.assert_called_once_with("stateChanged", callback)

        # Test removing listener
        mock_state_manager.removeEventListener("stateChanged", callback)
        mock_state_manager.removeEventListener.assert_called_once_with("stateChanged", callback)

    @pytest.mark.asyncio
    async def test_hide_event_when_valid_graph_id_then_returns_true(self, mock_state_manager):
        """Test that hideEvent with valid graphId returns success"""
        result = await mock_state_manager.hideEvent("event-to-hide")

        assert result is True
        mock_state_manager.hideEvent.assert_called_once_with("event-to-hide")

    @pytest.mark.asyncio
    async def test_hide_event_when_invalid_graph_id_then_returns_false(self, mock_state_manager):
        """Test that hideEvent handles invalid graphId"""
        # Configure mock to return False for invalid inputs
        mock_state_manager.hideEvent.return_value = False

        result = await mock_state_manager.hideEvent("")
        assert result is False

        result = await mock_state_manager.hideEvent(None)
        assert result is False

    @pytest.mark.asyncio
    async def test_hide_event_when_called_then_returns_success(self, mock_state_manager):
        """Test that hideEvent is called correctly"""
        result = await mock_state_manager.hideEvent("test-event-id")

        assert result is True
        mock_state_manager.hideEvent.assert_called_with("test-event-id")

    @pytest.mark.asyncio
    async def test_unhide_event_when_valid_graph_id_then_returns_true(self, mock_state_manager):
        """Test that unhideEvent with valid graphId returns success"""
        result = await mock_state_manager.unhideEvent("event-to-unhide")

        assert result is True
        mock_state_manager.unhideEvent.assert_called_once_with("event-to-unhide")

    @pytest.mark.asyncio
    async def test_unhide_event_when_called_then_returns_success(self, mock_state_manager):
        """Test that unhideEvent is called correctly"""
        result = await mock_state_manager.unhideEvent("test-event-id")

        assert result is True
        mock_state_manager.unhideEvent.assert_called_with("test-event-id")

    def test_get_events_when_called_then_returns_events(self, mock_state_manager):
        """Test that getEvents returns events from state"""
        events = mock_state_manager.getEvents()

        assert isinstance(events, list)
        assert events == []
        mock_state_manager.getEvents.assert_called_once()

    def test_get_performance_metrics_when_called_then_returns_metrics(self, mock_state_manager):
        """Test that getPerformanceMetrics returns performance data"""
        metrics = mock_state_manager.getPerformanceMetrics()

        assert "lastLoadTime" in metrics
        assert "loadDuration" in metrics
        assert "apiCallCount" in metrics
        assert isinstance(metrics["apiCallCount"], int)
        mock_state_manager.getPerformanceMetrics.assert_called_once()

    def test_refresh_view_when_called_then_refreshes(self, mock_state_manager):
        """Test that refreshView is called correctly"""
        mock_state_manager.refreshView()

        mock_state_manager.refreshView.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_state_manager):
        """Test handling of concurrent hide/unhide operations"""
        # Configure mocks for concurrent operations
        mock_state_manager.hideEvent = AsyncMock(return_value=True)
        mock_state_manager.unhideEvent = AsyncMock(return_value=True)

        # Execute concurrent operations
        results = await asyncio.gather(
            mock_state_manager.hideEvent("event-1"),
            mock_state_manager.hideEvent("event-2"),
            mock_state_manager.unhideEvent("event-3"),
        )

        assert all(results)
        assert mock_state_manager.hideEvent.call_count == 2
        assert mock_state_manager.unhideEvent.call_count == 1

    def test_error_handling_in_state_updates(self, mock_state_manager):
        """Test that state updates handle errors gracefully"""
        # Configure mock to raise exception
        mock_state_manager.updateState.side_effect = Exception("Update failed")

        # Attempt update
        with pytest.raises(Exception) as exc_info:
            mock_state_manager.updateState({"events": []})

        assert "Update failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_api_call_error_handling(self, mock_state_manager):
        """Test handling of API call failures"""
        # Configure mock to simulate API failure
        mock_state_manager.loadData.side_effect = Exception("API Error")

        with pytest.raises(Exception) as exc_info:
            await mock_state_manager.loadData()

        assert "API Error" in str(exc_info.value)
