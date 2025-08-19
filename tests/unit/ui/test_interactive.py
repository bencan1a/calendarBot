"""
Consolidated tests for InteractiveController core functionality.

This module tests the primary InteractiveController class integration,
focusing on lifecycle management and overall coordination between components.
Specialized functionality is tested in dedicated modules.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from calendarbot.ui.interactive import InteractiveController
from calendarbot.ui.keyboard import KeyCode
from calendarbot.ui.navigation import NavigationState


class TestInteractiveControllerLifecycle:
    """Test InteractiveController lifecycle methods."""

    @pytest.mark.asyncio
    async def test_start_when_already_running_then_returns_early(
        self, interactive_controller
    ) -> None:
        """Test start when already running returns early."""
        interactive_controller._running = True

        # Mock methods to verify they're not called
        interactive_controller._setup_split_display_logging = Mock()
        interactive_controller._update_display = AsyncMock()

        await interactive_controller.start()

        # Verify methods were not called
        interactive_controller._setup_split_display_logging.assert_not_called()
        interactive_controller._update_display.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_with_initial_date_then_sets_date_and_runs(
        self, interactive_controller, test_date
    ) -> None:
        """Test start with initial date sets navigation date."""
        # Mock all the methods to avoid actual execution
        interactive_controller.navigation.jump_to_date = Mock()
        interactive_controller._setup_split_display_logging = Mock()
        interactive_controller._update_display = AsyncMock()
        interactive_controller.keyboard.start_listening = AsyncMock()
        interactive_controller._background_update_loop = AsyncMock()

        # Mock asyncio.wait to return immediately
        with patch("calendarbot.ui.interactive.asyncio.wait") as mock_wait:
            mock_wait.return_value = (set(), set())

            await interactive_controller.start(test_date)

            # Verify jump_to_date was called with the initial date
            interactive_controller.navigation.jump_to_date.assert_called_once_with(test_date)

    @pytest.mark.asyncio
    async def test_stop_when_running_then_stops_keyboard_and_cancels_tasks(
        self, interactive_controller
    ) -> None:
        """Test stop method properly cleans up resources."""
        # Set up running state
        interactive_controller._running = True
        interactive_controller.keyboard.stop_listening = Mock()

        # Create mock background task
        mock_task = Mock()
        mock_task.cancel = Mock()
        interactive_controller._background_update_task = mock_task

        await interactive_controller.stop()

        # Verify cleanup
        assert interactive_controller._running is False
        interactive_controller.keyboard.stop_listening.assert_called_once()
        mock_task.cancel.assert_called_once()

    def test_is_running_property_reflects_internal_state(self, interactive_controller) -> None:
        """Test is_running property returns _running state."""
        assert interactive_controller.is_running is False

        interactive_controller._running = True
        assert interactive_controller.is_running is True

    def test_current_date_property_returns_navigation_selected_date(
        self, interactive_controller, test_date
    ) -> None:
        """Test current_date property returns navigation.selected_date."""
        # Mock navigation.selected_date
        mock_navigation = Mock()
        mock_navigation.selected_date = test_date
        interactive_controller.navigation = mock_navigation

        assert interactive_controller.current_date == test_date

    def test_get_navigation_state_returns_complete_state_dict(
        self, interactive_controller, test_date
    ) -> None:
        """Test get_navigation_state returns complete navigation state."""
        # Mock navigation methods
        mock_navigation = Mock()
        mock_navigation.selected_date = test_date
        mock_navigation.get_display_date.return_value = "Monday, January 15"
        mock_navigation.is_today.return_value = False
        mock_navigation.is_past.return_value = False
        mock_navigation.is_future.return_value = True
        mock_navigation.days_from_today.return_value = 5
        mock_navigation.get_week_context.return_value = {"week": "context"}

        interactive_controller.navigation = mock_navigation

        result = interactive_controller.get_navigation_state()

        # Verify result structure
        expected_keys = [
            "selected_date",
            "display_date",
            "is_today",
            "is_past",
            "is_future",
            "days_from_today",
            "week_context",
        ]
        for key in expected_keys:
            assert key in result

        assert result["selected_date"] == test_date.isoformat()
        assert result["display_date"] == "Monday, January 15"


class TestInteractiveControllerIntegration:
    """Test integration between InteractiveController components."""

    def test_initialization_creates_required_components(
        self, mock_cache_manager, mock_display_manager
    ) -> None:
        """Test initialization creates all required UI components."""
        controller = InteractiveController(mock_cache_manager, mock_display_manager)

        # Verify dependencies are set
        assert controller.cache_manager == mock_cache_manager
        assert controller.display_manager == mock_display_manager

        # Verify UI components are created
        assert isinstance(controller.navigation, NavigationState)
        assert hasattr(controller, "keyboard")

        # Verify initial state
        assert controller._running is False
        assert controller._last_data_update is None
        assert controller._background_update_task is None

    def test_keyboard_handlers_registered_for_all_navigation_keys(
        self, interactive_controller
    ) -> None:
        """Test that all required keyboard handlers are registered."""
        # Access the keyboard's internal callbacks to verify registration
        keyboard = interactive_controller.keyboard

        # Check that handlers exist for required keys
        expected_keys = [
            KeyCode.LEFT_ARROW,
            KeyCode.RIGHT_ARROW,
            KeyCode.SPACE,
            KeyCode.HOME,
            KeyCode.END,
            KeyCode.ESCAPE,
        ]

        for key_code in expected_keys:
            assert key_code in keyboard._key_callbacks, f"Handler missing for {key_code}"

    def test_navigation_callback_registered_on_initialization(
        self, mock_cache_manager, mock_display_manager
    ) -> None:
        """Test that navigation change callback is registered during init."""
        with patch("calendarbot.ui.interactive.NavigationState") as MockNavState:
            mock_nav = Mock()
            MockNavState.return_value = mock_nav

            controller = InteractiveController(mock_cache_manager, mock_display_manager)

            # Verify add_change_callback was called with _on_date_changed
            mock_nav.add_change_callback.assert_called_once_with(controller._on_date_changed)

    def test_date_change_triggers_display_update_task(
        self, interactive_controller, test_date
    ) -> None:
        """Test that date changes trigger display update via async task."""
        with patch("calendarbot.ui.interactive.asyncio.create_task") as mock_create_task:
            interactive_controller._update_display = AsyncMock()

            # Simulate date change callback
            interactive_controller._on_date_changed(test_date)

            # Verify async task was created
            mock_create_task.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
