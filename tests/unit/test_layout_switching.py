"""Unit tests for layout switching functionality."""

from unittest.mock import Mock, patch

import pytest

from calendarbot.display.manager import DisplayManager
from calendarbot.web.server import WebServer


class TestLayoutSwitching:
    """Test layout switching functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.display_type = "html"
        settings.display_enabled = True
        settings.web_theme = "3x4"
        settings.web_host = "localhost"
        settings.web_port = 8080
        return settings

    @pytest.fixture
    def display_manager(self, mock_settings):
        """Create display manager with mock settings."""
        return DisplayManager(mock_settings)

    @pytest.fixture
    def web_server(self, mock_settings):
        """Create web server with mock components."""
        mock_display_manager = Mock()
        mock_cache_manager = Mock()
        return WebServer(mock_settings, mock_display_manager, mock_cache_manager)

    def test_set_display_type_4x8(self, display_manager):
        """Test setting display type to 4x8 (maps to html internally)."""
        result = display_manager.set_display_type("4x8")
        assert result is True
        assert display_manager.get_display_type() == "4x8"

    def test_set_display_type_3x4(self, display_manager):
        """Test setting display type to 3x4."""
        result = display_manager.set_display_type("3x4")
        assert result is True
        assert display_manager.get_display_type() == "3x4"

    def test_set_display_type_compact(self, display_manager):
        """Test setting display type to 3x4 (compact layout)."""
        result = display_manager.set_display_type("3x4")
        assert result is True
        assert display_manager.get_display_type() == "3x4"

    def test_set_display_type_invalid(self, display_manager):
        """Test setting invalid display type."""
        result = display_manager.set_display_type("invalid-type")
        assert result is False
        # Should remain unchanged
        assert display_manager.get_display_type() == "4x8"

    def test_set_display_type_same_type(self, display_manager):
        """Test setting display type to the same type."""
        # First set to compact
        display_manager.set_display_type("3x4")

        # Try to set to same type
        result = display_manager.set_display_type("3x4")
        assert result is True
        assert display_manager.get_display_type() == "3x4"

    def test_get_available_display_types(self, display_manager):
        """Test getting available display types."""
        types = display_manager.get_available_display_types()
        expected_types = ["4x8", "3x4"]
        assert types == expected_types

    def test_current_display_type_property(self, display_manager):
        """Test current_display_type property."""
        display_manager.set_display_type("3x4")
        assert display_manager.current_display_type == "3x4"

    def test_web_server_set_layout(self, web_server):
        """Test web server layout setting."""
        # Mock the display manager's set_display_type method
        web_server.display_manager.set_display_type = Mock(return_value=True)

        result = web_server.set_layout("3x4")
        assert result is True
        web_server.display_manager.set_display_type.assert_called_once_with("3x4")

    def test_web_server_set_layout_invalid(self, web_server):
        """Test web server layout setting with invalid layout."""
        result = web_server.set_layout("invalid-layout")
        assert result is False

    def test_web_server_cycle_layout(self, web_server):
        """Test web server layout cycling from 4x8."""
        # Mock the display manager's methods
        web_server.display_manager.set_display_type = Mock(return_value=True)
        web_server.display_manager.get_display_type = Mock(return_value="4x8")

        result = web_server.cycle_layout()
        assert result == "3x4"
        web_server.display_manager.set_display_type.assert_called_once_with("3x4")

    def test_web_server_cycle_layout_from_compact(self, web_server):
        """Test web server layout cycling from 3x4."""
        # Mock the display manager's methods
        web_server.display_manager.set_display_type = Mock(return_value=True)
        web_server.display_manager.get_display_type = Mock(return_value="3x4")

        result = web_server.cycle_layout()
        assert result == "4x8"
        web_server.display_manager.set_display_type.assert_called_once_with("4x8")

    def test_web_server_cycle_layout_from_compact_duplicate(self, web_server):
        """Test web server layout cycling from compact (duplicate test)."""
        # Mock the display manager's methods
        web_server.display_manager.set_display_type = Mock(return_value=True)
        web_server.display_manager.get_display_type = Mock(return_value="3x4")

        result = web_server.cycle_layout()
        assert result == "4x8"
        web_server.display_manager.set_display_type.assert_called_once_with("4x8")

    def test_web_server_get_current_layout(self, web_server):
        """Test web server getting current layout."""
        web_server.display_manager.get_display_type = Mock(return_value="3x4")

        result = web_server.get_current_layout()
        assert result == "3x4"

    def test_display_manager_renderer_creation_standard(self, mock_settings):
        """Test renderer creation for 4x8 layout."""
        mock_settings.display_type = "html"
        with patch("calendarbot.display.manager.HTMLRenderer") as mock_renderer:
            display_manager = DisplayManager(mock_settings)
            mock_renderer.assert_called_once_with(mock_settings)

    def test_display_manager_renderer_creation_rpi(self, mock_settings):
        """Test renderer creation for RPI layout."""
        mock_settings.display_type = "rpi"
        with patch("calendarbot.display.manager.RaspberryPiHTMLRenderer") as mock_renderer:
            display_manager = DisplayManager(mock_settings)
            mock_renderer.assert_called_once_with(mock_settings)

    def test_display_manager_renderer_creation_compact(self, mock_settings):
        """Test renderer creation for compact layout."""
        mock_settings.display_type = "3x4"
        with patch("calendarbot.display.manager.CompactEInkRenderer") as mock_renderer:
            display_manager = DisplayManager(mock_settings)
            mock_renderer.assert_called_once_with(mock_settings)

    def test_display_manager_type_mapping(self, display_manager):
        """Test internal type mapping works correctly."""
        # Set to 4x8 (maps to html internally)
        display_manager.set_display_type("4x8")
        assert display_manager.settings.display_type == "html"
        assert display_manager.get_display_type() == "4x8"

        # Set to compact
        display_manager.set_display_type("3x4")
        assert display_manager.settings.display_type == "3x4"
        assert display_manager.get_display_type() == "3x4"

        # Set to compact
        display_manager.set_display_type("3x4")
        assert display_manager.settings.display_type == "3x4"
        assert display_manager.get_display_type() == "3x4"

    def test_web_server_get_status_includes_layout(self, web_server):
        """Test that get_status includes current layout information."""
        # Set up the web server with specific properties
        web_server.running = True
        web_server.host = "localhost"
        web_server.port = 8080
        web_server.theme = "4x8"
        web_server.display_manager.get_display_type = Mock(return_value="3x4")

        # Get status
        status = web_server.get_status()

        # Verify layout is included in status
        assert "layout" in status
        assert status["layout"] == "3x4"

        # Verify other expected fields are present
        assert status["running"] is True
        assert status["host"] == "localhost"
        assert status["port"] == 8080
        assert status["theme"] == "4x8"
        assert "interactive_mode" in status
        assert "current_date" in status
