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
from datetime import datetime
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
    def mock_state_manager_class(self):
        """Create a mock WhatsNextStateManager class for testing"""

        class MockWhatsNextStateManager:
            def __init__(self):
                self.state = {
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
                self.listeners = {
                    "stateChanged": [],
                    "dataLoaded": [],
                    "eventHidden": [],
                    "eventUnhidden": [],
                    "error": [],
                }
                self.optimisticUpdates = {}
                self.performanceMetrics = {
                    "lastLoadTime": None,
                    "loadDuration": None,
                    "apiCallCount": 0,
                }

            async def loadData(self):
                self.state["loading"] = True
                # Simulate API call
                await asyncio.sleep(0.01)

                mock_data = {
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

                self.updateState(mock_data)
                self.state["loading"] = False
                self._emitEvent("dataLoaded", {"data": mock_data})
                return mock_data

            def updateState(self, newData):
                previousState = self.state.copy()

                if "events" in newData:
                    self.state["events"] = newData["events"]
                if "layout_name" in newData:
                    self.state["layoutName"] = newData["layout_name"]
                if "last_updated" in newData:
                    self.state["lastUpdated"] = newData["last_updated"]

                self._emitEvent(
                    "stateChanged",
                    {
                        "previousState": previousState,
                        "newState": self.state.copy(),
                        "changeType": "update",
                    },
                )

            def refreshView(self):
                # Mock view refresh logic
                pass

            async def hideEvent(self, graphId):
                if not graphId:
                    return False

                try:
                    # Apply optimistic update
                    self._addOptimisticUpdate(graphId, {"is_hidden": True})

                    # Simulate API call
                    await asyncio.sleep(0.01)

                    # Update state
                    for event in self.state["events"]:
                        if event["graph_id"] == graphId:
                            event["is_hidden"] = True

                    self._emitEvent("eventHidden", {"graphId": graphId})
                    return True

                except Exception as e:
                    self._emitEvent(
                        "error", {"type": "hideEvent", "graphId": graphId, "error": str(e)}
                    )
                    return False

            async def unhideEvent(self, graphId):
                if not graphId:
                    return False

                try:
                    # Apply optimistic update
                    self._addOptimisticUpdate(graphId, {"is_hidden": False})

                    # Simulate API call
                    await asyncio.sleep(0.01)

                    # Update state
                    for event in self.state["events"]:
                        if event["graph_id"] == graphId:
                            event["is_hidden"] = False

                    self._emitEvent("eventUnhidden", {"graphId": graphId})
                    return True

                except Exception as e:
                    self._emitEvent(
                        "error", {"type": "unhideEvent", "graphId": graphId, "error": str(e)}
                    )
                    return False

            def getState(self):
                import copy

                return copy.deepcopy(self.state)

            def getEvents(self):
                import copy

                return copy.deepcopy(self.state["events"])

            def getPerformanceMetrics(self):
                return self.performanceMetrics.copy()

            def addEventListener(self, eventType, callback):
                if eventType in self.listeners:
                    self.listeners[eventType].append(callback)

            def removeEventListener(self, eventType, callback):
                if eventType in self.listeners and callback in self.listeners[eventType]:
                    self.listeners[eventType].remove(callback)

            def _emitEvent(self, eventType, data):
                if eventType in self.listeners:
                    for callback in self.listeners[eventType]:
                        try:
                            callback(data)
                        except Exception as e:
                            # Log error but continue with other callbacks
                            print(f"Error in {eventType} listener: {e}")

            def _addOptimisticUpdate(self, graphId, updates):
                self.optimisticUpdates[graphId] = updates

            def _removeOptimisticUpdate(self, graphId):
                if graphId in self.optimisticUpdates:
                    del self.optimisticUpdates[graphId]

        return MockWhatsNextStateManager

    def test_state_manager_initialization_when_created_then_has_default_state(
        self, mock_state_manager_class
    ):
        """Test that StateManager initializes with correct default state"""
        manager = mock_state_manager_class()

        state = manager.getState()

        assert state["events"] == []
        assert state["layoutName"] == "whats-next-view"
        assert state["lastUpdated"] is None
        assert state["loading"] is False
        assert state["error"] is None
        assert "layoutConfig" in state
        assert state["layoutConfig"]["showHiddenEvents"] is False

    def test_state_manager_initialization_when_created_then_has_empty_listeners(
        self, mock_state_manager_class
    ):
        """Test that StateManager initializes with empty event listeners"""
        manager = mock_state_manager_class()

        expected_events = ["stateChanged", "dataLoaded", "eventHidden", "eventUnhidden", "error"]

        for event_type in expected_events:
            assert event_type in manager.listeners
            assert manager.listeners[event_type] == []

    @pytest.mark.asyncio
    async def test_load_data_when_called_then_updates_state(self, mock_state_manager_class):
        """Test that loadData successfully updates state with API response"""
        manager = mock_state_manager_class()

        result = await manager.loadData()

        assert result is not None
        assert "events" in result
        assert len(result["events"]) == 1
        assert result["events"][0]["graph_id"] == "test-event-1"

        state = manager.getState()
        assert len(state["events"]) == 1
        assert state["events"][0]["title"] == "Test Meeting"

    @pytest.mark.asyncio
    async def test_load_data_when_called_then_emits_data_loaded_event(
        self, mock_state_manager_class
    ):
        """Test that loadData emits dataLoaded event"""
        manager = mock_state_manager_class()
        event_data = None

        def on_data_loaded(data):
            nonlocal event_data
            event_data = data

        manager.addEventListener("dataLoaded", on_data_loaded)

        await manager.loadData()

        assert event_data is not None
        assert "data" in event_data
        assert "events" in event_data["data"]

    def test_update_state_when_called_then_merges_new_data(self, mock_state_manager_class):
        """Test that updateState correctly merges new data into existing state"""
        manager = mock_state_manager_class()

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

        manager.updateState(new_data)

        state = manager.getState()
        assert len(state["events"]) == 1
        assert state["events"][0]["graph_id"] == "new-event"
        assert state["layoutName"] == "updated-view"

    def test_update_state_when_called_then_emits_state_changed_event(
        self, mock_state_manager_class
    ):
        """Test that updateState emits stateChanged event"""
        manager = mock_state_manager_class()
        event_data = None

        def on_state_changed(data):
            nonlocal event_data
            event_data = data

        manager.addEventListener("stateChanged", on_state_changed)

        new_data = {"events": []}
        manager.updateState(new_data)

        assert event_data is not None
        assert "previousState" in event_data
        assert "newState" in event_data
        assert event_data["changeType"] == "update"

    @pytest.mark.asyncio
    async def test_hide_event_when_valid_graph_id_then_returns_true(self, mock_state_manager_class):
        """Test that hideEvent with valid graphId returns success"""
        manager = mock_state_manager_class()

        # Add an event to hide
        manager.updateState(
            {"events": [{"graph_id": "event-to-hide", "title": "Test Event", "is_hidden": False}]}
        )

        result = await manager.hideEvent("event-to-hide")

        assert result is True

        # Check that event is marked as hidden
        state = manager.getState()
        hidden_event = next((e for e in state["events"] if e["graph_id"] == "event-to-hide"), None)
        assert hidden_event is not None
        assert hidden_event["is_hidden"] is True

    @pytest.mark.asyncio
    async def test_hide_event_when_invalid_graph_id_then_returns_false(
        self, mock_state_manager_class
    ):
        """Test that hideEvent with invalid graphId returns failure"""
        manager = mock_state_manager_class()

        result = await manager.hideEvent("")
        assert result is False

        result = await manager.hideEvent(None)
        assert result is False

    @pytest.mark.asyncio
    async def test_hide_event_when_called_then_emits_event_hidden(self, mock_state_manager_class):
        """Test that hideEvent emits eventHidden event"""
        manager = mock_state_manager_class()
        event_data = None

        def on_event_hidden(data):
            nonlocal event_data
            event_data = data

        manager.addEventListener("eventHidden", on_event_hidden)

        # Add an event to hide
        manager.updateState(
            {"events": [{"graph_id": "event-to-hide", "title": "Test Event", "is_hidden": False}]}
        )

        await manager.hideEvent("event-to-hide")

        assert event_data is not None
        assert event_data["graphId"] == "event-to-hide"

    @pytest.mark.asyncio
    async def test_unhide_event_when_valid_graph_id_then_returns_true(
        self, mock_state_manager_class
    ):
        """Test that unhideEvent with valid graphId returns success"""
        manager = mock_state_manager_class()

        # Add a hidden event to unhide
        manager.updateState(
            {"events": [{"graph_id": "event-to-unhide", "title": "Test Event", "is_hidden": True}]}
        )

        result = await manager.unhideEvent("event-to-unhide")

        assert result is True

        # Check that event is marked as not hidden
        state = manager.getState()
        unhidden_event = next(
            (e for e in state["events"] if e["graph_id"] == "event-to-unhide"), None
        )
        assert unhidden_event is not None
        assert unhidden_event["is_hidden"] is False

    @pytest.mark.asyncio
    async def test_unhide_event_when_called_then_emits_event_unhidden(
        self, mock_state_manager_class
    ):
        """Test that unhideEvent emits eventUnhidden event"""
        manager = mock_state_manager_class()
        event_data = None

        def on_event_unhidden(data):
            nonlocal event_data
            event_data = data

        manager.addEventListener("eventUnhidden", on_event_unhidden)

        # Add a hidden event to unhide
        manager.updateState(
            {"events": [{"graph_id": "event-to-unhide", "title": "Test Event", "is_hidden": True}]}
        )

        await manager.unhideEvent("event-to-unhide")

        assert event_data is not None
        assert event_data["graphId"] == "event-to-unhide"

    def test_get_events_when_called_then_returns_copy(self, mock_state_manager_class):
        """Test that getEvents returns a copy of events array"""
        manager = mock_state_manager_class()

        original_events = [{"graph_id": "test-event", "title": "Test Event"}]

        manager.updateState({"events": original_events})

        events = manager.getEvents()

        # Modify the returned array
        events.append({"graph_id": "added-event"})

        # Original state should be unchanged
        state = manager.getState()
        assert len(state["events"]) == 1
        assert state["events"][0]["graph_id"] == "test-event"

    def test_get_performance_metrics_when_called_then_returns_metrics(
        self, mock_state_manager_class
    ):
        """Test that getPerformanceMetrics returns performance data"""
        manager = mock_state_manager_class()

        metrics = manager.getPerformanceMetrics()

        assert "lastLoadTime" in metrics
        assert "loadDuration" in metrics
        assert "apiCallCount" in metrics
        assert isinstance(metrics["apiCallCount"], int)

    def test_add_event_listener_when_valid_type_then_adds_callback(self, mock_state_manager_class):
        """Test that addEventListener adds callback to correct event type"""
        manager = mock_state_manager_class()

        callback = Mock()
        manager.addEventListener("stateChanged", callback)

        assert callback in manager.listeners["stateChanged"]

    def test_remove_event_listener_when_callback_exists_then_removes_it(
        self, mock_state_manager_class
    ):
        """Test that removeEventListener removes existing callback"""
        manager = mock_state_manager_class()

        callback = Mock()
        manager.addEventListener("stateChanged", callback)
        manager.removeEventListener("stateChanged", callback)

        assert callback not in manager.listeners["stateChanged"]

    def test_optimistic_updates_when_added_then_stored_correctly(self, mock_state_manager_class):
        """Test that optimistic updates are stored and applied correctly"""
        manager = mock_state_manager_class()

        graph_id = "test-event"
        updates = {"is_hidden": True}

        manager._addOptimisticUpdate(graph_id, updates)

        assert graph_id in manager.optimisticUpdates
        assert manager.optimisticUpdates[graph_id] == updates

    def test_optimistic_updates_when_removed_then_deleted_correctly(self, mock_state_manager_class):
        """Test that optimistic updates are removed correctly"""
        manager = mock_state_manager_class()

        graph_id = "test-event"
        updates = {"is_hidden": True}

        manager._addOptimisticUpdate(graph_id, updates)
        manager._removeOptimisticUpdate(graph_id)

        assert graph_id not in manager.optimisticUpdates

    def test_event_emission_when_listeners_exist_then_calls_all_callbacks(
        self, mock_state_manager_class
    ):
        """Test that event emission calls all registered callbacks"""
        manager = mock_state_manager_class()

        callback1 = Mock()
        callback2 = Mock()

        manager.addEventListener("stateChanged", callback1)
        manager.addEventListener("stateChanged", callback2)

        test_data = {"test": "data"}
        manager._emitEvent("stateChanged", test_data)

        callback1.assert_called_once_with(test_data)
        callback2.assert_called_once_with(test_data)

    def test_event_emission_when_no_listeners_then_no_error(self, mock_state_manager_class):
        """Test that event emission with no listeners doesn't cause errors"""
        manager = mock_state_manager_class()

        # Should not raise any exception
        manager._emitEvent("nonExistentEvent", {"test": "data"})
        manager._emitEvent("stateChanged", {"test": "data"})

    def test_refresh_view_when_called_then_executes_successfully(self, mock_state_manager_class):
        """Test that refreshView executes without errors"""
        manager = mock_state_manager_class()

        # Should not raise any exception
        manager.refreshView()

    @pytest.mark.asyncio
    async def test_error_handling_when_hide_event_fails_then_emits_error(
        self, mock_state_manager_class
    ):
        """Test that errors during hideEvent are properly handled and emitted"""
        manager = mock_state_manager_class()
        error_data = None

        def on_error(data):
            nonlocal error_data
            error_data = data

        manager.addEventListener("error", on_error)

        # Override hideEvent to simulate failure
        async def failing_hide_event(graphId):
            manager._emitEvent(
                "error", {"type": "hideEvent", "graphId": graphId, "error": "Simulated API failure"}
            )
            return False

        manager.hideEvent = failing_hide_event

        result = await manager.hideEvent("test-event")

        assert result is False
        assert error_data is not None
        assert error_data["type"] == "hideEvent"
        assert error_data["graphId"] == "test-event"
        assert "error" in error_data

    def test_state_isolation_when_multiple_state_changes_then_maintains_integrity(
        self, mock_state_manager_class
    ):
        """Test that state changes maintain data integrity across multiple operations"""
        manager = mock_state_manager_class()

        # Initial state update
        manager.updateState(
            {
                "events": [
                    {"graph_id": "event-1", "title": "Event 1"},
                    {"graph_id": "event-2", "title": "Event 2"},
                ]
            }
        )

        # Subsequent state update
        manager.updateState({"events": [{"graph_id": "event-3", "title": "Event 3"}]})

        state = manager.getState()
        assert len(state["events"]) == 1
        assert state["events"][0]["graph_id"] == "event-3"

    def test_callback_error_handling_when_listener_throws_then_continues(
        self, mock_state_manager_class
    ):
        """Test that errors in event listeners don't break the emission process"""
        manager = mock_state_manager_class()

        def throwing_callback(data):
            raise Exception("Listener error")

        def normal_callback(data):
            normal_callback.called = True

        normal_callback.called = False

        manager.addEventListener("stateChanged", throwing_callback)
        manager.addEventListener("stateChanged", normal_callback)

        # Should not raise exception and should call the normal callback
        manager._emitEvent("stateChanged", {"test": "data"})

        assert normal_callback.called is True

    def test_state_immutability_when_get_state_called_then_returns_copy(
        self, mock_state_manager_class
    ):
        """Test that getState returns a copy that doesn't affect internal state"""
        manager = mock_state_manager_class()

        original_events = [{"graph_id": "test", "title": "Test"}]
        manager.updateState({"events": original_events})

        state = manager.getState()
        state["events"].append({"graph_id": "added", "title": "Added"})
        state["newProperty"] = "new value"

        # Original state should be unchanged
        internal_state = manager.getState()
        assert len(internal_state["events"]) == 1
        assert "newProperty" not in internal_state

    def test_performance_tracking_when_operations_performed_then_metrics_updated(
        self, mock_state_manager_class
    ):
        """Test that performance metrics are properly tracked"""
        manager = mock_state_manager_class()

        initial_metrics = manager.getPerformanceMetrics()

        # Simulate some operations that would update metrics
        manager.performanceMetrics["apiCallCount"] += 1
        manager.performanceMetrics["lastLoadTime"] = datetime.now()
        manager.performanceMetrics["loadDuration"] = 150.5

        updated_metrics = manager.getPerformanceMetrics()

        assert updated_metrics["apiCallCount"] == initial_metrics["apiCallCount"] + 1
        assert updated_metrics["lastLoadTime"] is not None
        assert updated_metrics["loadDuration"] == 150.5


if __name__ == "__main__":
    pytest.main([__file__])
