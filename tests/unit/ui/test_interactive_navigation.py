"""
Unit tests for InteractiveController navigation handlers.

This module tests the navigation event handlers in the InteractiveController class, focusing on:
- Previous/next day navigation
- Jump to today functionality
- Start/end of week navigation
- Exit handling
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from calendarbot.ui.interactive import InteractiveController
from calendarbot.ui.keyboard import KeyCode


class TestNavigationEventHandlers:
    """Test navigation event handlers in InteractiveController."""

    @pytest.mark.asyncio
    async def test_handle_previous_day_when_called_then_navigates_backward(self) -> None:
        """Test _handle_previous_day calls navigate_backward on navigation."""
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
    async def test_handle_next_day_when_called_then_navigates_forward(self) -> None:
        """Test _handle_next_day calls navigate_forward on navigation."""
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
    async def test_handle_jump_to_today_when_called_then_jumps_to_today(self) -> None:
        """Test _handle_jump_to_today calls jump_to_today on navigation."""
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
    async def test_handle_start_of_week_when_called_then_jumps_to_start_of_week(self) -> None:
        """Test _handle_start_of_week calls jump_to_start_of_week on navigation."""
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
    async def test_handle_end_of_week_when_called_then_jumps_to_end_of_week(self) -> None:
        """Test _handle_end_of_week calls jump_to_end_of_week on navigation."""
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
    async def test_handle_exit_when_called_then_stops_controller(self) -> None:
        """Test _handle_exit calls stop on controller."""
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

    @pytest.mark.asyncio
    async def test_start_with_initial_date_when_provided_then_jumps_to_date(self) -> None:
        """Test start with initial date calls jump_to_date on navigation."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock methods to avoid actual execution
        controller.navigation.jump_to_date = Mock()
        controller._setup_split_display_logging = Mock()
        controller._update_display = AsyncMock()
        controller.keyboard.start_listening = AsyncMock()
        controller._background_update_loop = AsyncMock()
        
        # Mock asyncio.wait to return immediately
        with patch('calendarbot.ui.interactive.asyncio.wait') as mock_wait:
            mock_wait.return_value = (set(), set())
            
            # Call start with initial date
            from datetime import date
            test_date = date(2024, 1, 15)
            await controller.start(test_date)
            
            # Verify jump_to_date was called with the initial date
            controller.navigation.jump_to_date.assert_called_once_with(test_date)

    @pytest.mark.asyncio
    async def test_start_when_already_running_then_returns_early(self) -> None:
        """Test start when already running returns early."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Set running to True
        controller._running = True
        
        # Mock methods to verify they're not called
        controller.navigation.jump_to_date = Mock()
        controller._setup_split_display_logging = Mock()
        controller._update_display = AsyncMock()
        
        # Call start
        await controller.start()
        
        # Verify methods were not called
        controller.navigation.jump_to_date.assert_not_called()
        controller._setup_split_display_logging.assert_not_called()
        controller._update_display.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_when_called_then_stops_keyboard_and_cancels_tasks(self) -> None:
        """Test stop stops keyboard and cancels background task."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Set running to True
        controller._running = True
        
        # Mock keyboard.stop_listening
        controller.keyboard.stop_listening = Mock()
        
        # Create mock background task
        mock_task = Mock()
        mock_task.cancel = Mock()
        controller._background_update_task = mock_task
        
        # Call stop
        await controller.stop()
        
        # Verify running was set to False
        assert controller._running is False
        
        # Verify keyboard.stop_listening was called
        controller.keyboard.stop_listening.assert_called_once()
        
        # Verify background task was cancelled
        mock_task.cancel.assert_called_once()

    def test_is_running_property_returns_running_state(self) -> None:
        """Test is_running property returns _running state."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Default should be False
        assert controller.is_running is False
        
        # Set to True and check
        controller._running = True
        assert controller.is_running is True

    def test_current_date_property_returns_navigation_selected_date(self) -> None:
        """Test current_date property returns navigation.selected_date."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Mock navigation.selected_date property
        from datetime import date
        test_date = date(2024, 1, 15)
        
        # Create a mock for the navigation object with a selected_date property
        mock_navigation = Mock()
        mock_navigation.selected_date = test_date
        controller.navigation = mock_navigation
        
        # Check current_date property
        assert controller.current_date == test_date

    def test_get_navigation_state_returns_complete_state_dict(self) -> None:
        """Test get_navigation_state returns complete state dictionary."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        
        # Create a mock for the navigation object
        from datetime import date
        test_date = date(2024, 1, 15)
        
        mock_navigation = Mock()
        mock_navigation.selected_date = test_date
        mock_navigation.get_display_date.return_value = "Monday, January 15"
        mock_navigation.is_today.return_value = False
        mock_navigation.is_past.return_value = False
        mock_navigation.is_future.return_value = True
        mock_navigation.days_from_today.return_value = 5
        mock_navigation.get_week_context.return_value = {"week": "context"}
        
        controller.navigation = mock_navigation
        
        # Call get_navigation_state
        result = controller.get_navigation_state()
        
        # Verify result contains expected keys
        assert "selected_date" in result
        assert "display_date" in result
        assert "is_today" in result
        assert "is_past" in result
        assert "is_future" in result
        assert "days_from_today" in result
        assert "week_context" in result
        
        # Verify values
        assert result["selected_date"] == test_date.isoformat()
        assert result["display_date"] == "Monday, January 15"
        assert result["is_today"] is False
        assert result["is_past"] is False
        assert result["is_future"] is True
        assert result["days_from_today"] == 5
        assert result["week_context"] == {"week": "context"}


if __name__ == "__main__":
    pytest.main([__file__])