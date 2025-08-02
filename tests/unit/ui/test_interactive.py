"""
Unit tests for interactive calendar navigation UI.

This module tests the InteractiveController class, focusing on:
- Controller initialization
- Keyboard handler setup
- Navigation event handling
- Display update functionality
- Background update loop
- Event retrieval methods
"""

import asyncio
import contextlib
from datetime import date, datetime as dt, timedelta
from typing import Any, Dict, List, Optional, cast
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from calendarbot.cache.models import CachedEvent
from calendarbot.ui.interactive import InteractiveController
from calendarbot.ui.keyboard import KeyCode, KeyboardHandler
from calendarbot.ui.navigation import NavigationState


class TestInteractiveControllerInitialization:
    """Test InteractiveController initialization."""

    def test_init_with_dependencies(self) -> None:
        """Test initialization with required dependencies."""
        # Create mocks for dependencies
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Verify dependencies are set
        assert controller.cache_manager == mock_cache_manager
        assert controller.display_manager == mock_display_manager
        
        # Verify UI components are created
        assert isinstance(controller.navigation, NavigationState)
        assert isinstance(controller.keyboard, KeyboardHandler)
        
        # Verify initial state
        assert controller._running is False
        assert controller._last_data_update is None
        assert controller._background_update_task is None

    def test_init_sets_up_keyboard_handlers(self) -> None:
        """Test that initialization sets up keyboard handlers."""
        # Create mocks for dependencies
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        
        # Patch the _setup_keyboard_handlers method
        with patch.object(InteractiveController, '_setup_keyboard_handlers') as mock_setup:
            controller = InteractiveController(mock_cache_manager, mock_display_manager)
            
            # Verify _setup_keyboard_handlers was called
            mock_setup.assert_called_once()

    def test_init_adds_navigation_callback(self) -> None:
        """Test that initialization adds navigation change callback."""
        # Create mocks for dependencies
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        
        # Create a mock for NavigationState
        with patch('calendarbot.ui.interactive.NavigationState') as MockNavState:
            mock_nav = Mock()
            MockNavState.return_value = mock_nav
            
            controller = InteractiveController(mock_cache_manager, mock_display_manager)
            
            # Verify add_change_callback was called with _on_date_changed
            mock_nav.add_change_callback.assert_called_once_with(controller._on_date_changed)


class TestKeyboardHandlerSetup:
    """Test keyboard handler setup in InteractiveController."""

    def test_setup_keyboard_handlers(self) -> None:
        """Test that _setup_keyboard_handlers registers all required handlers."""
        # Create mocks for dependencies
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        
        # Create a mock for KeyboardHandler
        with patch('calendarbot.ui.interactive.KeyboardHandler') as MockKeyboardHandler:
            mock_keyboard = Mock()
            MockKeyboardHandler.return_value = mock_keyboard
            
            controller = InteractiveController(mock_cache_manager, mock_display_manager)
            
            # Verify register_key_handler was called for all navigation keys
            assert mock_keyboard.register_key_handler.call_count >= 6
            
            # Check specific key registrations
            mock_keyboard.register_key_handler.assert_any_call(KeyCode.LEFT_ARROW, controller._handle_previous_day)
            mock_keyboard.register_key_handler.assert_any_call(KeyCode.RIGHT_ARROW, controller._handle_next_day)
            mock_keyboard.register_key_handler.assert_any_call(KeyCode.SPACE, controller._handle_jump_to_today)
            mock_keyboard.register_key_handler.assert_any_call(KeyCode.HOME, controller._handle_start_of_week)
            mock_keyboard.register_key_handler.assert_any_call(KeyCode.END, controller._handle_end_of_week)
            mock_keyboard.register_key_handler.assert_any_call(KeyCode.ESCAPE, controller._handle_exit)


class TestNavigationEventHandlers:
    """Test navigation event handlers in InteractiveController."""

    @pytest.mark.asyncio
    async def test_handle_previous_day(self) -> None:
        """Test _handle_previous_day method."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock navigation.navigate_backward
        controller.navigation.navigate_backward = Mock()
        
        # Call the handler
        await controller._handle_previous_day()
        
        # Verify navigate_backward was called
        controller.navigation.navigate_backward.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_next_day(self) -> None:
        """Test _handle_next_day method."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock navigation.navigate_forward
        controller.navigation.navigate_forward = Mock()
        
        # Call the handler
        await controller._handle_next_day()
        
        # Verify navigate_forward was called
        controller.navigation.navigate_forward.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_jump_to_today(self) -> None:
        """Test _handle_jump_to_today method."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock navigation.jump_to_today
        controller.navigation.jump_to_today = Mock()
        
        # Call the handler
        await controller._handle_jump_to_today()
        
        # Verify jump_to_today was called
        controller.navigation.jump_to_today.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_start_of_week(self) -> None:
        """Test _handle_start_of_week method."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock navigation.jump_to_start_of_week
        controller.navigation.jump_to_start_of_week = Mock()
        
        # Call the handler
        await controller._handle_start_of_week()
        
        # Verify jump_to_start_of_week was called
        controller.navigation.jump_to_start_of_week.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_end_of_week(self) -> None:
        """Test _handle_end_of_week method."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock navigation.jump_to_end_of_week
        controller.navigation.jump_to_end_of_week = Mock()
        
        # Call the handler
        await controller._handle_end_of_week()
        
        # Verify jump_to_end_of_week was called
        controller.navigation.jump_to_end_of_week.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_exit(self) -> None:
        """Test _handle_exit method."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock controller.stop
        controller.stop = AsyncMock()
        
        # Call the handler
        await controller._handle_exit()
        
        # Verify stop was called
        controller.stop.assert_called_once()

    def test_on_date_changed(self) -> None:
        """Test _on_date_changed method."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock asyncio.create_task
        with patch('calendarbot.ui.interactive.asyncio.create_task') as mock_create_task:
            # Mock controller._update_display
            controller._update_display = AsyncMock()
            
            # Call the callback
            test_date = date(2024, 1, 15)
            controller._on_date_changed(test_date)
            
            # Verify create_task was called with _update_display
            mock_create_task.assert_called_once()


class TestDisplayUpdateFunctionality:
    """Test display update functionality in InteractiveController."""

    @pytest.mark.asyncio
    async def test_update_display_normal_flow(self) -> None:
        """Test _update_display normal flow."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Set navigation selected date
        test_date = date(2024, 1, 15)
        controller.navigation.jump_to_date(test_date)
        
        # Mock cache_manager.get_events_by_date_range with properly configured mock events
        mock_event1 = Mock(spec=CachedEvent)
        mock_event1.subject = "Test Event 1"
        mock_event1.start_datetime = "2024-01-15T10:00:00Z"
        
        mock_event2 = Mock(spec=CachedEvent)
        mock_event2.subject = "Test Event 2"
        mock_event2.start_datetime = "2024-01-15T14:00:00Z"
        
        mock_events = [mock_event1, mock_event2]
        controller.cache_manager.get_events_by_date_range = AsyncMock(return_value=mock_events)
        
        # Mock _get_status_info
        mock_status = {"status": "test"}
        controller._get_status_info = AsyncMock(return_value=mock_status)
        
        # Mock display_manager.display_events
        controller.display_manager.display_events = AsyncMock(return_value=True)
        
        # Call the method
        await controller._update_display()
        
        # Verify get_events_by_date_range was called with correct date range
        start_datetime = dt.combine(test_date, dt.min.time())
        end_datetime = start_datetime + timedelta(days=1)
        controller.cache_manager.get_events_by_date_range.assert_called_once_with(
            start_datetime, end_datetime
        )
        
        # Verify _get_status_info was called
        controller._get_status_info.assert_called_once()
        
        # Verify display_events was called with events and status
        controller.display_manager.display_events.assert_called_once_with(
            mock_events, mock_status, clear_screen=True
        )

    @pytest.mark.asyncio
    async def test_update_display_with_exception(self) -> None:
        """Test _update_display with exception in get_events_by_date_range."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Set navigation selected date
        test_date = date(2024, 1, 15)
        controller.navigation.jump_to_date(test_date)
        
        # Mock cache_manager.get_events_by_date_range to raise exception
        controller.cache_manager.get_events_by_date_range = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        # Call the method - should not raise exception
        await controller._update_display()
        
        # Verify get_events_by_date_range was called
        controller.cache_manager.get_events_by_date_range.assert_called_once()
        
        # Verify display_events was not called
        controller.display_manager.display_events.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_status_info_normal_flow(self) -> None:
        """Test _get_status_info normal flow."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock cache_manager.get_cache_status
        mock_cache_status = Mock()
        mock_cache_status.last_update = "2024-01-15T12:00:00Z"
        mock_cache_status.is_stale = False
        controller.cache_manager.get_cache_status = AsyncMock(return_value=mock_cache_status)
        
        # Mock navigation methods
        controller.navigation.get_display_date = Mock(return_value="Monday, January 15")
        controller.navigation.is_today = Mock(return_value=False)
        controller.keyboard.get_help_text = Mock(return_value="Help text")
        
        # Call the method
        result = await controller._get_status_info()
        
        # Verify get_cache_status was called
        controller.cache_manager.get_cache_status.assert_called_once()
        
        # Verify navigation methods were called
        controller.navigation.get_display_date.assert_called_once()
        controller.navigation.is_today.assert_called_once()
        controller.keyboard.get_help_text.assert_called_once()
        
        # Verify result contains expected keys
        assert "last_update" in result
        assert "is_cached" in result
        assert "connection_status" in result
        assert "interactive_mode" in result
        assert "selected_date" in result
        assert "is_today" in result
        assert "navigation_help" in result

    @pytest.mark.asyncio
    async def test_get_status_info_with_exception(self) -> None:
        """Test _get_status_info with exception in get_cache_status."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock cache_manager.get_cache_status to raise exception
        controller.cache_manager.get_cache_status = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        # Mock navigation.get_display_date
        controller.navigation.get_display_date = Mock(return_value="Monday, January 15")
        
        # Call the method
        result = await controller._get_status_info()
        
        # Verify get_cache_status was called
        controller.cache_manager.get_cache_status.assert_called_once()
        
        # Verify result contains fallback keys
        assert "selected_date" in result
        assert "interactive_mode" in result
        assert "error" in result


class TestBackgroundUpdateLoop:
    """Test background update loop in InteractiveController."""

    @pytest.mark.asyncio
    async def test_background_update_loop_normal_flow(self) -> None:
        """Test _background_update_loop normal flow."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Set up to run once then stop
        controller._running = True
        
        # Mock _background_update_iteration
        controller._background_update_iteration = AsyncMock(
            side_effect=lambda: setattr(controller, "_running", False)
        )
        
        # Mock asyncio.sleep
        with patch('calendarbot.ui.interactive.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Call the method
            await controller._background_update_loop()
            
            # Verify _background_update_iteration was called
            controller._background_update_iteration.assert_called_once()
            
            # Verify sleep was not called (because we stopped after first iteration)
            mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_background_update_loop_cancelled(self) -> None:
        """Test _background_update_loop with CancelledError."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Set running to True
        controller._running = True
        
        # Mock _background_update_iteration to raise CancelledError
        controller._background_update_iteration = AsyncMock(
            side_effect=asyncio.CancelledError()
        )
        
        # Call the method - should not raise exception
        await controller._background_update_loop()
        
        # Verify _background_update_iteration was called
        controller._background_update_iteration.assert_called_once()

    @pytest.mark.asyncio
    async def test_background_update_iteration_with_update(self) -> None:
        """Test _background_update_iteration with cache update."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock cache_manager.get_cache_status
        mock_cache_status = Mock()
        mock_cache_status.last_update = "2024-01-15T12:00:00Z"
        controller.cache_manager.get_cache_status = AsyncMock(return_value=mock_cache_status)
        
        # Set _last_data_update to None (first run)
        controller._last_data_update = None
        
        # Mock _update_display
        controller._update_display = AsyncMock()
        
        # Mock navigation.update_today
        controller.navigation.update_today = Mock()
        
        # Call the method
        await controller._background_update_iteration()
        
        # Verify get_cache_status was called
        controller.cache_manager.get_cache_status.assert_called_once()
        
        # Verify _update_display was called
        controller._update_display.assert_called_once()
        
        # Verify update_today was called
        controller.navigation.update_today.assert_called_once()
        
        # Verify _last_data_update was updated
        assert controller._last_data_update is not None

    @pytest.mark.asyncio
    async def test_background_update_iteration_no_update(self) -> None:
        """Test _background_update_iteration with no cache update."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock cache_manager.get_cache_status
        mock_cache_status = Mock()
        mock_cache_status.last_update = "2024-01-15T12:00:00Z"
        controller.cache_manager.get_cache_status = AsyncMock(return_value=mock_cache_status)
        
        # Set _last_data_update to same value
        controller._last_data_update = dt.fromisoformat("2024-01-15T12:00:00+00:00")
        
        # Mock _update_display
        controller._update_display = AsyncMock()
        
        # Mock navigation.update_today
        controller.navigation.update_today = Mock()
        
        # Call the method
        await controller._background_update_iteration()
        
        # Verify get_cache_status was called
        controller.cache_manager.get_cache_status.assert_called_once()
        
        # Verify _update_display was not called
        controller._update_display.assert_not_called()
        
        # Verify update_today was called
        controller.navigation.update_today.assert_called_once()


class TestEventRetrievalMethods:
    """Test event retrieval methods in InteractiveController."""

    @pytest.mark.asyncio
    async def test_get_events_for_date_normal_flow(self) -> None:
        """Test get_events_for_date normal flow."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock cache_manager.get_events_by_date_range
        mock_events = [Mock(spec=CachedEvent), Mock(spec=CachedEvent)]
        controller.cache_manager.get_events_by_date_range = AsyncMock(return_value=mock_events)
        
        # Call the method
        test_date = date(2024, 1, 15)
        result = await controller.get_events_for_date(test_date)
        
        # Verify get_events_by_date_range was called with correct date range
        start_datetime = dt.combine(test_date, dt.min.time())
        end_datetime = start_datetime + timedelta(days=1)
        controller.cache_manager.get_events_by_date_range.assert_called_once_with(
            start_datetime, end_datetime
        )
        
        # Verify result is the mock events
        assert result == mock_events

    @pytest.mark.asyncio
    async def test_get_events_for_date_with_exception(self) -> None:
        """Test get_events_for_date with exception in get_events_by_date_range."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock cache_manager.get_events_by_date_range to raise exception
        controller.cache_manager.get_events_by_date_range = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        # Call the method
        test_date = date(2024, 1, 15)
        result = await controller.get_events_for_date(test_date)
        
        # Verify get_events_by_date_range was called
        controller.cache_manager.get_events_by_date_range.assert_called_once()
        
        # Verify result is empty list
        assert result == []

    @pytest.mark.asyncio
    async def test_get_events_for_week_normal_flow(self) -> None:
        """Test get_events_for_week normal flow."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock cache_manager.get_events_by_date_range
        mock_event1 = Mock(spec=CachedEvent)
        mock_event1.subject = "Event 1"
        mock_event1.start_datetime = "2024-01-15T10:00:00Z"
        mock_event1.start_dt = dt(2024, 1, 15, 10, 0, 0)
        
        mock_event2 = Mock(spec=CachedEvent)
        mock_event2.subject = "Event 2"
        mock_event2.start_datetime = "2024-01-16T14:00:00Z"
        mock_event2.start_dt = dt(2024, 1, 16, 14, 0, 0)
        
        mock_events = [mock_event1, mock_event2]
        controller.cache_manager.get_events_by_date_range = AsyncMock(return_value=mock_events)
        
        # Mock _process_event_for_date_grouping
        original_process = controller._process_event_for_date_grouping
        controller._process_event_for_date_grouping = Mock(
            side_effect=lambda event, events_by_date: events_by_date[event.start_dt.date()].append(event)
        )
        
        # Call the method
        test_date = date(2024, 1, 15)  # Monday
        result = await controller.get_events_for_week(test_date)
        
        # Verify get_events_by_date_range was called with correct date range
        start_of_week = date(2024, 1, 15)  # Monday
        end_of_week = date(2024, 1, 21)    # Sunday
        start_datetime = dt.combine(start_of_week, dt.min.time())
        end_datetime = dt.combine(end_of_week, dt.max.time())
        controller.cache_manager.get_events_by_date_range.assert_called_once_with(
            start_datetime, end_datetime
        )
        
        # Verify _process_event_for_date_grouping was called for each event
        assert controller._process_event_for_date_grouping.call_count == len(mock_events)
        
        # Verify result contains all days of the week
        assert len(result) == 7
        for day in range(7):
            current_date = start_of_week + timedelta(days=day)
            assert current_date in result
        
        # Verify events are in the correct days
        assert mock_event1 in result[date(2024, 1, 15)]
        assert mock_event2 in result[date(2024, 1, 16)]
        
        # Restore original method
        controller._process_event_for_date_grouping = original_process

    @pytest.mark.asyncio
    async def test_get_events_for_week_with_exception(self) -> None:
        """Test get_events_for_week with exception in get_events_by_date_range."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock cache_manager.get_events_by_date_range to raise exception
        controller.cache_manager.get_events_by_date_range = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        # Call the method
        test_date = date(2024, 1, 15)
        result = await controller.get_events_for_week(test_date)
        
        # Verify get_events_by_date_range was called
        controller.cache_manager.get_events_by_date_range.assert_called_once()
        
        # Verify result is empty dict
        assert result == {}

    def test_process_event_for_date_grouping_with_start_dt(self) -> None:
        """Test _process_event_for_date_grouping with start_dt attribute."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Create mock event with start_dt
        mock_event = Mock(spec=CachedEvent)
        mock_event.subject = "Test Event"
        mock_event.start_dt = dt(2024, 1, 15, 10, 0, 0)
        
        # Create events_by_date dict
        events_by_date = {
            date(2024, 1, 15): [],
            date(2024, 1, 16): [],
        }
        
        # Call the method
        controller._process_event_for_date_grouping(mock_event, events_by_date)
        
        # Verify event was added to correct date
        assert mock_event in events_by_date[date(2024, 1, 15)]
        assert len(events_by_date[date(2024, 1, 16)]) == 0

    def test_process_event_for_date_grouping_with_start_datetime(self) -> None:
        """Test _process_event_for_date_grouping with start_datetime string."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Create mock event with start_datetime
        mock_event = Mock(spec=CachedEvent)
        mock_event.subject = "Test Event"
        mock_event.start_datetime = "2024-01-16T14:00:00Z"
        # Ensure start_dt is None to force using start_datetime
        mock_event.start_dt = None
        
        # Create events_by_date dict
        events_by_date = {
            date(2024, 1, 15): [],
            date(2024, 1, 16): [],
        }
        
        # Call the method
        controller._process_event_for_date_grouping(mock_event, events_by_date)
        
        # Verify event was added to correct date
        assert len(events_by_date[date(2024, 1, 15)]) == 0
        assert mock_event in events_by_date[date(2024, 1, 16)]

    def test_process_event_for_date_grouping_with_exception(self) -> None:
        """Test _process_event_for_date_grouping with exception."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Create mock event with invalid start_datetime
        mock_event = Mock(spec=CachedEvent)
        mock_event.subject = "Test Event"
        mock_event.start_datetime = "invalid-date"
        
        # Create events_by_date dict
        events_by_date = {
            date(2024, 1, 15): [],
            date(2024, 1, 16): [],
        }
        
        # Call the method - should not raise exception
        controller._process_event_for_date_grouping(mock_event, events_by_date)
        
        # Verify no events were added
        assert len(events_by_date[date(2024, 1, 15)]) == 0
        assert len(events_by_date[date(2024, 1, 16)]) == 0


class TestInteractiveControllerLifecycle:
    """Test InteractiveController lifecycle methods."""

    @pytest.mark.asyncio
    async def test_start_already_running(self) -> None:
        """Test start when already running."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Set running to True
        controller._running = True
        
        # Call the method
        await controller.start()
        
        # Verify no further actions were taken
        assert controller._running is True

    @pytest.mark.asyncio
    async def test_start_with_initial_date(self) -> None:
        """Test start with initial date."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock navigation.jump_to_date
        controller.navigation.jump_to_date = Mock()
        
        # Mock _setup_split_display_logging
        controller._setup_split_display_logging = Mock()
        
        # Mock _