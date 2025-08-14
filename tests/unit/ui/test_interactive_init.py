"""
Unit tests for InteractiveController initialization.

This module tests the initialization of the InteractiveController class, focusing on:
- Dependency injection
- UI component creation
- Keyboard handler setup
- Navigation callback registration
"""

from unittest.mock import Mock, patch

import pytest

from calendarbot.ui.interactive import InteractiveController
from calendarbot.ui.keyboard import KeyboardHandler
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
        with patch.object(InteractiveController, "_setup_keyboard_handlers") as mock_setup:
            InteractiveController(mock_cache_manager, mock_display_manager)

            # Verify _setup_keyboard_handlers was called
            mock_setup.assert_called_once()

    def test_init_adds_navigation_callback(self) -> None:
        """Test that initialization adds navigation change callback."""
        # Create mocks for dependencies
        mock_cache_manager = Mock()
        mock_display_manager = Mock()

        # Create a mock for NavigationState
        with patch("calendarbot.ui.interactive.NavigationState") as MockNavState:
            mock_nav = Mock()
            MockNavState.return_value = mock_nav

            controller = InteractiveController(mock_cache_manager, mock_display_manager)

            # Verify add_change_callback was called with _on_date_changed
            mock_nav.add_change_callback.assert_called_once_with(controller._on_date_changed)

    def test_setup_keyboard_handlers(self) -> None:
        """Test that _setup_keyboard_handlers registers all required handlers."""
        # Create mocks for dependencies
        mock_cache_manager = Mock()
        mock_display_manager = Mock()

        # Create a mock for KeyboardHandler
        with patch("calendarbot.ui.interactive.KeyboardHandler") as MockKeyboardHandler:
            mock_keyboard = Mock()
            MockKeyboardHandler.return_value = mock_keyboard

            controller = InteractiveController(mock_cache_manager, mock_display_manager)

            # Verify register_key_handler was called for all navigation keys
            assert mock_keyboard.register_key_handler.call_count >= 6

            # Check specific key registrations
            from calendarbot.ui.keyboard import KeyCode

            mock_keyboard.register_key_handler.assert_any_call(
                KeyCode.LEFT_ARROW, controller._handle_previous_day
            )
            mock_keyboard.register_key_handler.assert_any_call(
                KeyCode.RIGHT_ARROW, controller._handle_next_day
            )
            mock_keyboard.register_key_handler.assert_any_call(
                KeyCode.SPACE, controller._handle_jump_to_today
            )
            mock_keyboard.register_key_handler.assert_any_call(
                KeyCode.HOME, controller._handle_start_of_week
            )
            mock_keyboard.register_key_handler.assert_any_call(
                KeyCode.END, controller._handle_end_of_week
            )
            mock_keyboard.register_key_handler.assert_any_call(
                KeyCode.ESCAPE, controller._handle_exit
            )

    def test_on_date_changed_creates_update_task(self) -> None:
        """Test that _on_date_changed creates a display update task."""
        # Create controller with mocks
        mock_cache_manager = Mock()
        mock_display_manager = Mock()
        controller = InteractiveController(mock_cache_manager, mock_display_manager)

        # Mock asyncio.create_task
        with patch("calendarbot.ui.interactive.asyncio.create_task") as mock_create_task:
            # Mock controller._update_display
            controller._update_display = Mock()

            # Call the callback
            from datetime import date

            test_date = date(2024, 1, 15)
            controller._on_date_changed(test_date)

            # Verify create_task was called with _update_display
            mock_create_task.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
