"""Shared fixtures for UI tests."""

from datetime import date
from unittest.mock import Mock

import pytest


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
def test_date():
    """Standard test date for consistency."""
    return date(2024, 1, 15)
