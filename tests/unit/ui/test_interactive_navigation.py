"""
Tests for InteractiveController navigation handlers.

This module focuses on navigation event handlers and their specific
interactions with the NavigationState component.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestNavigationEventHandlers:
    """Test navigation event handler behavior."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "handler_method,navigation_method",
        [
            ("_handle_previous_day", "navigate_backward"),
            ("_handle_next_day", "navigate_forward"),
            ("_handle_jump_to_today", "jump_to_today"),
            ("_handle_start_of_week", "jump_to_start_of_week"),
            ("_handle_end_of_week", "jump_to_end_of_week"),
        ],
    )
    async def test_navigation_handlers_call_correct_navigation_methods(
        self, interactive_controller, handler_method, navigation_method
    ) -> None:
        """Test that navigation handlers call the correct navigation methods."""
        # Mock the navigation method
        setattr(interactive_controller.navigation, navigation_method, Mock())

        # Get and call the handler
        handler = getattr(interactive_controller, handler_method)
        await handler()

        # Verify the navigation method was called
        getattr(interactive_controller.navigation, navigation_method).assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_exit_when_called_then_stops_controller(
        self, interactive_controller
    ) -> None:
        """Test exit handler properly stops the controller."""
        interactive_controller.stop = AsyncMock()

        await interactive_controller._handle_exit()

        interactive_controller.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_with_initial_date_when_provided_then_sets_navigation_date(
        self, interactive_controller, test_date
    ) -> None:
        """Test that start() with initial date sets navigation properly."""
        # Mock all methods to prevent actual execution
        interactive_controller.navigation.jump_to_date = Mock()
        interactive_controller._setup_split_display_logging = Mock()
        interactive_controller._update_display = AsyncMock()
        interactive_controller.keyboard.start_listening = AsyncMock()
        interactive_controller._background_update_loop = AsyncMock()

        # Mock asyncio.wait to prevent hanging
        with patch("calendarbot.ui.interactive.asyncio.wait") as mock_wait:
            mock_wait.return_value = (set(), set())

            await interactive_controller.start(test_date)

            # Verify navigation was set to the specified date
            interactive_controller.navigation.jump_to_date.assert_called_once_with(test_date)


class TestNavigationStateIntegration:
    """Test integration between controller and navigation state."""

    def test_current_date_property_delegates_to_navigation_selected_date(
        self, interactive_controller, test_date
    ) -> None:
        """Test current_date property correctly delegates to navigation."""
        # Mock navigation's selected_date property
        mock_navigation = Mock()
        mock_navigation.selected_date = test_date
        interactive_controller.navigation = mock_navigation

        assert interactive_controller.current_date == test_date

    def test_get_navigation_state_returns_comprehensive_navigation_info(
        self, interactive_controller, test_date
    ) -> None:
        """Test get_navigation_state returns complete navigation state information."""
        # Set up mock navigation with all expected methods
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

        # Verify all navigation methods were called
        mock_navigation.get_display_date.assert_called_once()
        mock_navigation.is_today.assert_called_once()
        mock_navigation.is_past.assert_called_once()
        mock_navigation.is_future.assert_called_once()
        mock_navigation.days_from_today.assert_called_once()
        mock_navigation.get_week_context.assert_called_once()

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

        # Verify specific values
        assert result["selected_date"] == test_date.isoformat()
        assert result["display_date"] == "Monday, January 15"
        assert result["is_today"] is False
        assert result["is_past"] is False
        assert result["is_future"] is True
        assert result["days_from_today"] == 5
        assert result["week_context"] == {"week": "context"}


if __name__ == "__main__":
    pytest.main([__file__])
