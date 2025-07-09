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
        settings.web_theme = "eink"
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

    def test_set_display_type_standard(self, display_manager):
        """Test setting display type to standard."""
        result = display_manager.set_display_type("standard")
        assert result is True
        assert display_manager.get_display_type() == "standard"

    def test_set_display_type_eink_rpi(self, display_manager):
        """Test setting display type to eink-rpi."""
        result = display_manager.set_display_type("eink-rpi")
        assert result is True
        assert display_manager.get_display_type() == "eink-rpi"

    def test_set_display_type_compact(self, display_manager):
        """Test setting display type to eink-compact-300x400."""
        result = display_manager.set_display_type("eink-compact-300x400")
        assert result is True
        assert display_manager.get_display_type() == "eink-compact-300x400"

    def test_set_display_type_invalid(self, display_manager):
        """Test setting invalid display type."""
        result = display_manager.set_display_type("invalid-type")
        assert result is False
        # Should remain unchanged
        assert display_manager.get_display_type() == "standard"

    def test_set_display_type_same_type(self, display_manager):
        """Test setting display type to the same type."""
        # First set to compact
        display_manager.set_display_type("eink-compact-300x400")

        # Try to set to same type
        result = display_manager.set_display_type("eink-compact-300x400")
        assert result is True
        assert display_manager.get_display_type() == "eink-compact-300x400"

    def test_get_available_display_types(self, display_manager):
        """Test getting available display types."""
        types = display_manager.get_available_display_types()
        expected_types = ["standard", "eink-rpi", "eink-compact-300x400"]
        assert types == expected_types

    def test_current_display_type_property(self, display_manager):
        """Test current_display_type property."""
        display_manager.set_display_type("eink-rpi")
        assert display_manager.current_display_type == "eink-rpi"

    def test_web_server_set_layout(self, web_server):
        """Test web server layout setting."""
        # Mock the display manager's set_display_type method
        web_server.display_manager.set_display_type = Mock(return_value=True)

        result = web_server.set_layout("eink-compact-300x400")
        assert result is True
        web_server.display_manager.set_display_type.assert_called_once_with("eink-compact-300x400")

    def test_web_server_set_layout_invalid(self, web_server):
        """Test web server layout setting with invalid layout."""
        result = web_server.set_layout("invalid-layout")
        assert result is False

    def test_web_server_cycle_layout(self, web_server):
        """Test web server layout cycling."""
        # Mock the display manager's set_display_type method
        web_server.display_manager.set_display_type = Mock(return_value=True)
        web_server.display_manager.current_display_type = "standard"

        result = web_server.cycle_layout()
        assert result == "eink-rpi"
        web_server.display_manager.set_display_type.assert_called_once_with("eink-rpi")

    def test_web_server_cycle_layout_from_rpi(self, web_server):
        """Test web server layout cycling from eink-rpi."""
        # Mock the display manager's set_display_type method
        web_server.display_manager.set_display_type = Mock(return_value=True)
        web_server.display_manager.current_display_type = "eink-rpi"

        result = web_server.cycle_layout()
        assert result == "eink-compact-300x400"
        web_server.display_manager.set_display_type.assert_called_once_with("eink-compact-300x400")

    def test_web_server_cycle_layout_from_compact(self, web_server):
        """Test web server layout cycling from compact."""
        # Mock the display manager's set_display_type method
        web_server.display_manager.set_display_type = Mock(return_value=True)
        web_server.display_manager.current_display_type = "eink-compact-300x400"

        result = web_server.cycle_layout()
        assert result == "standard"
        web_server.display_manager.set_display_type.assert_called_once_with("standard")

    def test_web_server_get_current_layout(self, web_server):
        """Test web server getting current layout."""
        web_server.display_manager.current_display_type = "eink-compact-300x400"

        result = web_server.get_current_layout()
        assert result == "eink-compact-300x400"

    def test_display_manager_renderer_creation_standard(self, mock_settings):
        """Test renderer creation for standard layout."""
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
        mock_settings.display_type = "eink-compact-300x400"
        with patch("calendarbot.display.manager.CompactEInkRenderer") as mock_renderer:
            display_manager = DisplayManager(mock_settings)
            mock_renderer.assert_called_once_with(mock_settings)

    def test_display_manager_type_mapping(self, display_manager):
        """Test internal type mapping works correctly."""
        # Set to standard (maps to html internally)
        display_manager.set_display_type("standard")
        assert display_manager.settings.display_type == "html"
        assert display_manager.get_display_type() == "standard"

        # Set to eink-rpi (maps to rpi internally)
        display_manager.set_display_type("eink-rpi")
        assert display_manager.settings.display_type == "rpi"
        assert display_manager.get_display_type() == "eink-rpi"

        # Set to compact (maps to itself)
        display_manager.set_display_type("eink-compact-300x400")
        assert display_manager.settings.display_type == "eink-compact-300x400"
        assert display_manager.get_display_type() == "eink-compact-300x400"

    def test_web_server_get_status_includes_layout(self, web_server):
        """Test that get_status includes current layout information."""
        # Set up the web server with specific properties
        web_server.running = True
        web_server.host = "localhost"
        web_server.port = 8080
        web_server.theme = "standard"
        web_server.display_manager.current_display_type = "eink-compact-300x400"

        # Get status
        status = web_server.get_status()

        # Verify layout is included in status
        assert "layout" in status
        assert status["layout"] == "eink-compact-300x400"

        # Verify other expected fields are present
        assert status["running"] is True
        assert status["host"] == "localhost"
        assert status["port"] == 8080
        assert status["theme"] == "standard"
        assert "interactive_mode" in status
        assert "current_date" in status
