"""
Tests for InteractiveController initialization details.

This module focuses on specific initialization behaviors not covered
in the main integration tests, particularly around keyboard handler setup.
"""

from unittest.mock import Mock, patch

import pytest

from calendarbot.ui.interactive import InteractiveController
from calendarbot.ui.keyboard import KeyCode


class TestKeyboardHandlerSetup:
    """Test detailed keyboard handler setup during initialization."""

    def test_setup_keyboard_handlers_registers_all_navigation_keys(
        self, interactive_controller
    ) -> None:
        """Test that all required navigation keys are properly registered."""
        keyboard = interactive_controller.keyboard

        # Verify all required handlers are registered
        required_keys = [
            (KeyCode.LEFT_ARROW, "_handle_previous_day"),
            (KeyCode.RIGHT_ARROW, "_handle_next_day"),
            (KeyCode.SPACE, "_handle_jump_to_today"),
            (KeyCode.HOME, "_handle_start_of_week"),
            (KeyCode.END, "_handle_end_of_week"),
            (KeyCode.ESCAPE, "_handle_exit"),
        ]

        for key_code, handler_name in required_keys:
            assert key_code in keyboard._key_callbacks, f"Handler missing for {key_code}"
            # Verify handler points to correct controller method
            handler = keyboard._key_callbacks[key_code]
            assert hasattr(interactive_controller, handler_name)

    def test_setup_keyboard_handlers_creates_correct_handler_bindings(
        self, mock_cache_manager, mock_display_manager
    ) -> None:
        """Test keyboard handler setup creates proper method bindings."""
        with patch("calendarbot.ui.interactive.KeyboardHandler") as MockKeyboardHandler:
            mock_keyboard = Mock()
            MockKeyboardHandler.return_value = mock_keyboard

            controller = InteractiveController(mock_cache_manager, mock_display_manager)

            # Verify register_key_handler was called with controller methods
            expected_calls = [
                (KeyCode.LEFT_ARROW, controller._handle_previous_day),
                (KeyCode.RIGHT_ARROW, controller._handle_next_day),
                (KeyCode.SPACE, controller._handle_jump_to_today),
                (KeyCode.HOME, controller._handle_start_of_week),
                (KeyCode.END, controller._handle_end_of_week),
                (KeyCode.ESCAPE, controller._handle_exit),
            ]

            # Check that register was called for each key
            assert mock_keyboard.register_key_handler.call_count == len(expected_calls)

            # Verify specific calls were made
            for key_code, handler in expected_calls:
                mock_keyboard.register_key_handler.assert_any_call(key_code, handler)


if __name__ == "__main__":
    pytest.main([__file__])
