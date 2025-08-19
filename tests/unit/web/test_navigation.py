"""Tests for WebNavigationHandler class."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from calendarbot.ui.navigation import NavigationState
from calendarbot.web.navigation import WebNavigationHandler


@pytest.fixture
def handler():
    """Create WebNavigationHandler instance for testing."""
    return WebNavigationHandler()


@pytest.fixture
def handler_with_nav_state():
    """Create WebNavigationHandler with provided navigation state."""
    nav_state = NavigationState()
    return WebNavigationHandler(navigation_state=nav_state), nav_state


class TestWebNavigationHandlerInitialization:
    """Test WebNavigationHandler initialization."""

    def test_init_with_no_navigation_state(self, handler):
        """Test initialization creates new navigation state."""
        assert isinstance(handler.navigation_state, NavigationState)
        assert len(handler._navigation_callbacks) == 0

    def test_init_with_provided_navigation_state(self, handler_with_nav_state):
        """Test initialization uses provided navigation state."""
        handler, nav_state = handler_with_nav_state
        assert handler.navigation_state is nav_state
        assert len(handler._navigation_callbacks) == 0


class TestNavigationActions:
    """Test navigation action handling."""

    @pytest.mark.parametrize(
        ("action", "method_name"),
        [
            ("prev", "navigate_backward"),
            ("next", "navigate_forward"),
            ("today", "jump_to_today"),
            ("week-start", "jump_to_start_of_week"),
            ("week-end", "jump_to_end_of_week"),
        ],
    )
    def test_handle_navigation_action_valid_actions(self, handler, action, method_name):
        """Test handle_navigation_action with valid actions."""
        with patch.object(handler.navigation_state, method_name) as mock_method:
            result = handler.handle_navigation_action(action)
            assert result is True
            mock_method.assert_called_once()

    def test_handle_navigation_action_unknown_action(self, handler):
        """Test handle_navigation_action with unknown action returns False."""
        result = handler.handle_navigation_action("unknown_action")
        assert result is False

    def test_handle_navigation_action_exception_handling(self, handler):
        """Test handle_navigation_action handles exceptions gracefully."""
        with patch.object(
            handler.navigation_state, "navigate_forward", side_effect=Exception("Test exception")
        ):
            result = handler.handle_navigation_action("next")
            assert result is False

    def test_jump_to_date_success(self, handler):
        """Test jump_to_date with valid date."""
        target_date = date.today() + timedelta(days=7)
        with patch.object(handler.navigation_state, "jump_to_date") as mock_jump:
            result = handler.jump_to_date(target_date)
            assert result is True
            mock_jump.assert_called_once_with(target_date)

    def test_jump_to_date_exception_handling(self, handler):
        """Test jump_to_date handles exceptions gracefully."""
        target_date = date.today() + timedelta(days=7)
        with patch.object(
            handler.navigation_state, "jump_to_date", side_effect=Exception("Test exception")
        ):
            result = handler.jump_to_date(target_date)
            assert result is False


class TestNavigationInfo:
    """Test navigation information retrieval."""

    def test_get_navigation_info_success(self, handler):
        """Test get_navigation_info returns complete information."""
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
            result = handler.get_navigation_info()

            assert isinstance(result, dict)
            assert result["selected_date"] == "August 2, 2025"
            assert result["is_today"] is False
            assert result["is_past"] is False
            assert result["is_future"] is True
            assert result["days_from_today"] == 7
            assert len(result["week_context"]) == 7
            assert result["formatted_date"] == "Saturday, August 2, 2025"
            assert "navigation_help" in result

    def test_get_navigation_info_exception_handling(self, handler):
        """Test get_navigation_info handles exceptions gracefully."""
        with patch.object(
            handler.navigation_state, "get_display_date", side_effect=Exception("Test exception")
        ):
            result = handler.get_navigation_info()
            assert isinstance(result, dict)
            assert result["selected_date"] == "Error"
            assert result["is_today"] is True
            assert "error" in result

    def test_get_web_navigation_help(self, handler):
        """Test _get_web_navigation_help returns help text."""
        result = handler._get_web_navigation_help()
        assert isinstance(result, str)
        assert "Navigate" in result
        assert "Today" in result


class TestCallbackManagement:
    """Test navigation callback management."""

    def test_add_navigation_callback(self, handler):
        """Test adding navigation callback."""
        callback = MagicMock()
        handler.add_navigation_callback(callback)
        assert callback in handler._navigation_callbacks
        assert len(handler._navigation_callbacks) == 1

    def test_remove_navigation_callback_exists(self, handler):
        """Test removing existing navigation callback."""
        callback = MagicMock()
        handler.add_navigation_callback(callback)
        handler.remove_navigation_callback(callback)
        assert callback not in handler._navigation_callbacks
        assert len(handler._navigation_callbacks) == 0

    def test_remove_navigation_callback_not_exists(self, handler):
        """Test removing non-existent callback does nothing."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        handler.add_navigation_callback(callback1)
        handler.remove_navigation_callback(callback2)
        assert callback1 in handler._navigation_callbacks
        assert len(handler._navigation_callbacks) == 1

    def test_on_navigation_changed_notifies_callbacks(self, handler):
        """Test _on_navigation_changed notifies all callbacks."""
        callback1 = MagicMock()
        callback2 = MagicMock()
        handler.add_navigation_callback(callback1)
        handler.add_navigation_callback(callback2)

        new_date = date.today()
        with patch.object(handler, "get_navigation_info", return_value={"test": "info"}):
            handler._on_navigation_changed(new_date)
            callback1.assert_called_once_with(new_date, {"test": "info"})
            callback2.assert_called_once_with(new_date, {"test": "info"})

    def test_safe_callback_execution_handles_exceptions(self, handler):
        """Test _safe_callback_execution handles exceptions gracefully."""
        callback = MagicMock(side_effect=Exception("Test exception"))
        new_date = date.today()
        nav_info = {"test": "info"}

        # Should not raise exception
        handler._safe_callback_execution(callback, new_date, nav_info)
        callback.assert_called_once_with(new_date, nav_info)


class TestPropertyDelegation:
    """Test property delegation to navigation state."""

    @pytest.mark.parametrize(
        ("property_name", "expected_value"),
        [
            ("selected_date", date(2025, 8, 2)),
            ("today", date(2025, 8, 2)),
        ],
    )
    def test_property_delegation(self, handler, property_name, expected_value):
        """Test property delegation to navigation_state."""
        handler.navigation_state = MagicMock()
        setattr(handler.navigation_state, property_name, expected_value)
        result = getattr(handler, property_name)
        assert result == expected_value

    @pytest.mark.parametrize(
        ("method_name", "return_value"),
        [
            ("is_today", True),
            ("is_past", True),
            ("is_future", True),
            ("get_display_date", "August 2, 2025"),
        ],
    )
    def test_method_delegation(self, handler, method_name, return_value):
        """Test method delegation to navigation_state."""
        with patch.object(
            handler.navigation_state, method_name, return_value=return_value
        ) as mock_method:
            result = getattr(handler, method_name)()
            assert result == return_value
            mock_method.assert_called_once()

    def test_update_today_delegation(self, handler):
        """Test update_today delegates to navigation_state."""
        with patch.object(handler.navigation_state, "update_today") as mock_update:
            handler.update_today()
            mock_update.assert_called_once()
