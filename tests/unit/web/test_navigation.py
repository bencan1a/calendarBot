"""Tests for WebNavigationHandler class."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from calendarbot.ui.navigation import NavigationState
from calendarbot.web.navigation import WebNavigationHandler


class TestWebNavigationHandler:
    """Test suite for WebNavigationHandler class."""

    def test_init_when_no_navigation_state_then_creates_new_state(self) -> None:
        """Test initialization with no navigation state creates a new one."""
        # Act
        handler = WebNavigationHandler()

        # Assert
        assert isinstance(handler.navigation_state, NavigationState)
        assert len(handler._navigation_callbacks) == 0

    def test_init_when_navigation_state_provided_then_uses_provided_state(self) -> None:
        """Test initialization with provided navigation state uses it."""
        # Arrange
        nav_state = NavigationState()

        # Act
        handler = WebNavigationHandler(navigation_state=nav_state)

        # Assert
        assert handler.navigation_state is nav_state
        assert len(handler._navigation_callbacks) == 0

    def test_handle_navigation_action_when_prev_then_navigates_backward(self) -> None:
        """Test handle_navigation_action with 'prev' action navigates backward."""
        # Arrange
        handler = WebNavigationHandler()

        with patch.object(handler.navigation_state, "navigate_backward") as mock_navigate:
            # Act
            result = handler.handle_navigation_action("prev")

            # Assert
            assert result is True
            mock_navigate.assert_called_once()

    def test_handle_navigation_action_when_next_then_navigates_forward(self) -> None:
        """Test handle_navigation_action with 'next' action navigates forward."""
        # Arrange
        handler = WebNavigationHandler()

        with patch.object(handler.navigation_state, "navigate_forward") as mock_navigate:
            # Act
            result = handler.handle_navigation_action("next")

            # Assert
            assert result is True
            mock_navigate.assert_called_once()

    def test_handle_navigation_action_when_today_then_jumps_to_today(self) -> None:
        """Test handle_navigation_action with 'today' action jumps to today."""
        # Arrange
        handler = WebNavigationHandler()

        with patch.object(handler.navigation_state, "jump_to_today") as mock_navigate:
            # Act
            result = handler.handle_navigation_action("today")

            # Assert
            assert result is True
            mock_navigate.assert_called_once()

    def test_handle_navigation_action_when_week_start_then_jumps_to_start_of_week(self) -> None:
        """Test handle_navigation_action with 'week-start' action jumps to start of week."""
        # Arrange
        handler = WebNavigationHandler()

        with patch.object(handler.navigation_state, "jump_to_start_of_week") as mock_navigate:
            # Act
            result = handler.handle_navigation_action("week-start")

            # Assert
            assert result is True
            mock_navigate.assert_called_once()

    def test_handle_navigation_action_when_week_end_then_jumps_to_end_of_week(self) -> None:
        """Test handle_navigation_action with 'week-end' action jumps to end of week."""
        # Arrange
        handler = WebNavigationHandler()

        with patch.object(handler.navigation_state, "jump_to_end_of_week") as mock_navigate:
            # Act
            result = handler.handle_navigation_action("week-end")

            # Assert
            assert result is True
            mock_navigate.assert_called_once()

    def test_handle_navigation_action_when_unknown_action_then_returns_false(self) -> None:
        """Test handle_navigation_action with unknown action returns False."""
        # Arrange
        handler = WebNavigationHandler()

        # Act
        result = handler.handle_navigation_action("unknown_action")

        # Assert
        assert result is False

    def test_handle_navigation_action_when_exception_occurs_then_returns_false(self) -> None:
        """Test handle_navigation_action returns False when exception occurs."""
        # Arrange
        handler = WebNavigationHandler()

        with patch.object(
            handler.navigation_state, "navigate_forward", side_effect=Exception("Test exception")
        ):
            # Act
            result = handler.handle_navigation_action("next")

            # Assert
            assert result is False

    def test_jump_to_date_when_valid_date_then_jumps_to_date(self) -> None:
        """Test jump_to_date with valid date jumps to that date."""
        # Arrange
        handler = WebNavigationHandler()
        target_date = date.today() + timedelta(days=7)

        with patch.object(handler.navigation_state, "jump_to_date") as mock_jump:
            # Act
            result = handler.jump_to_date(target_date)

            # Assert
            assert result is True
            mock_jump.assert_called_once_with(target_date)

    def test_jump_to_date_when_exception_occurs_then_returns_false(self) -> None:
        """Test jump_to_date returns False when exception occurs."""
        # Arrange
        handler = WebNavigationHandler()
        target_date = date.today() + timedelta(days=7)

        with patch.object(
            handler.navigation_state, "jump_to_date", side_effect=Exception("Test exception")
        ):
            # Act
            result = handler.jump_to_date(target_date)

            # Assert
            assert result is False

    def test_get_navigation_info_when_called_then_returns_navigation_info(self) -> None:
        """Test get_navigation_info returns navigation information dictionary."""
        # Arrange
        handler = WebNavigationHandler()

        # Mock navigation state methods
        with patch.multiple(
            handler.navigation_state,
            get_display_date=MagicMock(return_value="August 2, 2025"),
            is_today=MagicMock(return_value=False),
            is_past=MagicMock(return_value=False),
            is_future=MagicMock(return_value=True),
            days_from_today=MagicMock(return_value=7),
            get_week_context=MagicMock(
                return_value=["Jul 27", "Jul 28", "Jul 29", "Jul 30", "Jul 31", "Aug 1", "Aug 2"]
            ),
            get_formatted_date=MagicMock(return_value="Saturday, August 2, 2025"),
        ):
            # Act
            result = handler.get_navigation_info()

            # Assert
            assert isinstance(result, dict)
            assert result["selected_date"] == "August 2, 2025"
            assert result["is_today"] is False
            assert result["is_past"] is False
            assert result["is_future"] is True
            assert result["days_from_today"] == 7
            assert len(result["week_context"]) == 7
            assert result["formatted_date"] == "Saturday, August 2, 2025"
            assert "navigation_help" in result

    def test_get_navigation_info_when_exception_occurs_then_returns_error_info(self) -> None:
        """Test get_navigation_info returns error info when exception occurs."""
        # Arrange
        handler = WebNavigationHandler()

        with patch.object(
            handler.navigation_state, "get_display_date", side_effect=Exception("Test exception")
        ):
            # Act
            result = handler.get_navigation_info()

            # Assert
            assert isinstance(result, dict)
            assert result["selected_date"] == "Error"
            assert result["is_today"] is True
            assert "error" in result

    def test_get_web_navigation_help_when_called_then_returns_help_text(self) -> None:
        """Test _get_web_navigation_help returns help text."""
        # Arrange
        handler = WebNavigationHandler()

        # Act
        result = handler._get_web_navigation_help()

        # Assert
        assert isinstance(result, str)
        assert "Navigate" in result
        assert "Today" in result

    def test_add_navigation_callback_when_called_then_adds_callback(self) -> None:
        """Test add_navigation_callback adds callback to list."""
        # Arrange
        handler = WebNavigationHandler()
        callback = MagicMock()

        # Act
        handler.add_navigation_callback(callback)

        # Assert
        assert callback in handler._navigation_callbacks
        assert len(handler._navigation_callbacks) == 1

    def test_remove_navigation_callback_when_callback_exists_then_removes_callback(self) -> None:
        """Test remove_navigation_callback removes existing callback."""
        # Arrange
        handler = WebNavigationHandler()
        callback = MagicMock()
        handler.add_navigation_callback(callback)
        assert callback in handler._navigation_callbacks

        # Act
        handler.remove_navigation_callback(callback)

        # Assert
        assert callback not in handler._navigation_callbacks
        assert len(handler._navigation_callbacks) == 0

    def test_remove_navigation_callback_when_callback_not_exists_then_does_nothing(self) -> None:
        """Test remove_navigation_callback does nothing for non-existent callback."""
        # Arrange
        handler = WebNavigationHandler()
        callback1 = MagicMock()
        callback2 = MagicMock()
        handler.add_navigation_callback(callback1)
        assert len(handler._navigation_callbacks) == 1

        # Act
        handler.remove_navigation_callback(callback2)

        # Assert
        assert callback1 in handler._navigation_callbacks
        assert len(handler._navigation_callbacks) == 1

    def test_on_navigation_changed_when_called_then_notifies_callbacks(self) -> None:
        """Test _on_navigation_changed notifies all callbacks."""
        # Arrange
        handler = WebNavigationHandler()
        callback1 = MagicMock()
        callback2 = MagicMock()
        handler.add_navigation_callback(callback1)
        handler.add_navigation_callback(callback2)

        new_date = date.today()

        with patch.object(handler, "get_navigation_info", return_value={"test": "info"}):
            # Act
            handler._on_navigation_changed(new_date)

            # Assert
            callback1.assert_called_once_with(new_date, {"test": "info"})
            callback2.assert_called_once_with(new_date, {"test": "info"})

    def test_safe_callback_execution_when_callback_raises_exception_then_handles_gracefully(
        self,
    ) -> None:
        """Test _safe_callback_execution handles exceptions gracefully."""
        # Arrange
        handler = WebNavigationHandler()
        callback = MagicMock(side_effect=Exception("Test exception"))
        new_date = date.today()
        nav_info = {"test": "info"}

        # Act & Assert - Should not raise exception
        handler._safe_callback_execution(callback, new_date, nav_info)
        callback.assert_called_once_with(new_date, nav_info)

    def test_selected_date_property_when_accessed_then_returns_navigation_state_selected_date(
        self,
    ) -> None:
        """Test selected_date property returns navigation_state.selected_date."""
        # Arrange
        handler = WebNavigationHandler()
        test_date = date(2025, 8, 2)

        # Mock the selected_date property
        handler.navigation_state = MagicMock()
        handler.navigation_state.selected_date = test_date

        # Act
        result = handler.selected_date

        # Assert
        assert result == test_date

    def test_today_property_when_accessed_then_returns_navigation_state_today(self) -> None:
        """Test today property returns navigation_state.today."""
        # Arrange
        handler = WebNavigationHandler()
        test_date = date(2025, 8, 2)

        # Mock the today property
        handler.navigation_state = MagicMock()
        handler.navigation_state.today = test_date

        # Act
        result = handler.today

        # Assert
        assert result == test_date

    def test_is_today_when_called_then_delegates_to_navigation_state(self) -> None:
        """Test is_today delegates to navigation_state.is_today."""
        # Arrange
        handler = WebNavigationHandler()

        with patch.object(handler.navigation_state, "is_today", return_value=True) as mock_is_today:
            # Act
            result = handler.is_today()

            # Assert
            assert result is True
            mock_is_today.assert_called_once()

    def test_is_past_when_called_then_delegates_to_navigation_state(self) -> None:
        """Test is_past delegates to navigation_state.is_past."""
        # Arrange
        handler = WebNavigationHandler()

        with patch.object(handler.navigation_state, "is_past", return_value=True) as mock_is_past:
            # Act
            result = handler.is_past()

            # Assert
            assert result is True
            mock_is_past.assert_called_once()

    def test_is_future_when_called_then_delegates_to_navigation_state(self) -> None:
        """Test is_future delegates to navigation_state.is_future."""
        # Arrange
        handler = WebNavigationHandler()

        with patch.object(
            handler.navigation_state, "is_future", return_value=True
        ) as mock_is_future:
            # Act
            result = handler.is_future()

            # Assert
            assert result is True
            mock_is_future.assert_called_once()

    def test_get_display_date_when_called_then_delegates_to_navigation_state(self) -> None:
        """Test get_display_date delegates to navigation_state.get_display_date."""
        # Arrange
        handler = WebNavigationHandler()

        with patch.object(
            handler.navigation_state, "get_display_date", return_value="August 2, 2025"
        ) as mock_get_display_date:
            # Act
            result = handler.get_display_date()

            # Assert
            assert result == "August 2, 2025"
            mock_get_display_date.assert_called_once()

    def test_update_today_when_called_then_delegates_to_navigation_state(self) -> None:
        """Test update_today delegates to navigation_state.update_today."""
        # Arrange
        handler = WebNavigationHandler()

        with patch.object(handler.navigation_state, "update_today") as mock_update_today:
            # Act
            handler.update_today()

            # Assert
            mock_update_today.assert_called_once()
