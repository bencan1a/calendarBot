"""Shared fixtures for UI tests."""

from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from calendarbot.ui.interactive import InteractiveController


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager with common async methods."""
    cache_manager = Mock()
    cache_manager.get_events_by_date_range = AsyncMock(return_value=[])
    cache_manager.get_cache_status = AsyncMock()
    return cache_manager


@pytest.fixture
def mock_display_manager():
    """Mock display manager with common async methods."""
    display_manager = Mock()
    display_manager.display_events = AsyncMock(return_value=True)
    display_manager.renderer = Mock()
    return display_manager


@pytest.fixture
def mock_navigation_state():
    """Mock navigation state with all needed methods."""
    navigation = Mock()
    navigation.selected_date = date(2024, 1, 15)
    navigation.is_today.return_value = False
    navigation.get_display_date.return_value = "Monday, January 15"
    navigation.add_change_callback = Mock()
    return navigation


@pytest.fixture
def mock_keyboard_handler():
    """Mock keyboard handler with needed methods."""
    from calendarbot.ui.keyboard import KeyCode

    keyboard = Mock()
    keyboard.get_help_text.return_value = "Help text"
    keyboard.register_handler = Mock()
    keyboard.start = AsyncMock()
    keyboard.stop = AsyncMock()
    # Populate with expected keys for testing
    keyboard._key_callbacks = {
        KeyCode.LEFT_ARROW: Mock(),
        KeyCode.RIGHT_ARROW: Mock(),
        KeyCode.SPACE: Mock(),
        KeyCode.HOME: Mock(),
        KeyCode.END: Mock(),
        KeyCode.ESCAPE: Mock(),
    }
    return keyboard


@pytest.fixture
def interactive_controller(
    mock_cache_manager, mock_display_manager, mock_navigation_state, mock_keyboard_handler
):
    """Pre-configured InteractiveController for testing."""
    with (
        patch("calendarbot.ui.interactive.NavigationState", return_value=mock_navigation_state),
        patch("calendarbot.ui.interactive.KeyboardHandler", return_value=mock_keyboard_handler),
    ):
        controller = InteractiveController(mock_cache_manager, mock_display_manager)
        # Ensure the mocks are properly attached
        controller.navigation = mock_navigation_state
        controller.keyboard = mock_keyboard_handler
        return controller


@pytest.fixture
def mock_cache_status():
    """Mock cache status object."""
    status = Mock()
    status.last_update = "2024-01-15T12:00:00Z"
    status.is_stale = False
    return status


@pytest.fixture
def test_date():
    """Standard test date for consistency."""
    return date(2024, 1, 15)


@pytest.fixture
def mock_cached_event():
    """Mock CachedEvent with all needed attributes."""
    event = Mock()
    event.subject = "Test Event"
    event.start_dt = datetime(2024, 1, 15, 10, 0, 0)
    event.end_dt = datetime(2024, 1, 15, 11, 0, 0)
    return event
