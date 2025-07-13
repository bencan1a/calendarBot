"""Unit tests for layout switching functionality with layout-renderer separation."""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from calendarbot.display.manager import DisplayManager
from calendarbot.layout.registry import LayoutRegistry
from calendarbot.web.server import WebServer


class TestLayoutSwitching:
    """Test layout switching functionality with new layout-renderer separation."""

    @pytest.fixture
    def mock_layout_registry(self) -> Mock:
        """Create mock layout registry."""
        registry = Mock(spec=LayoutRegistry)
        registry.get_available_layouts.return_value = ["4x8", "3x4"]
        registry.validate_layout.side_effect = lambda layout: layout in ["4x8", "3x4"]
        # Mock the actual LayoutInfo object that get_layout_info returns
        from calendarbot.layout.registry import LayoutInfo

        mock_layout_info = LayoutInfo(
            name="test",
            display_name="Test Layout",
            version="1.0.0",
            description="Test layout",
            capabilities={"renderer_type": "html"},
            renderer_type="html",
            fallback_chain=[],
            resources={"css": [], "js": []},
            requirements={},
        )
        registry.get_layout_info.return_value = mock_layout_info
        return registry

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Create mock settings with layout-renderer separation."""
        settings = Mock()
        settings.display_type = "html"  # This is the renderer type
        settings.display_enabled = True
        settings.layout_name = "3x4"  # This is the layout name
        settings.web_layout = "3x4"  # For web server compatibility
        settings.web_host = "localhost"
        settings.web_port = 8080
        return settings

    @pytest.fixture
    def display_manager(self, mock_settings: Mock, mock_layout_registry: Mock) -> DisplayManager:
        """Create display manager with mock settings and layout registry."""
        with patch("calendarbot.display.manager.LayoutRegistry", return_value=mock_layout_registry):
            with patch(
                "calendarbot.display.manager.RendererFactory.create_renderer"
            ) as mock_create:
                mock_renderer = Mock()
                mock_create.return_value = mock_renderer
                return DisplayManager(mock_settings)

    @pytest.fixture
    def web_server(self, mock_settings: Mock, mock_layout_registry: Mock) -> WebServer:
        """Create web server with mock components and layout registry."""
        mock_display_manager = Mock()
        mock_display_manager.get_display_type.return_value = "3x4"
        mock_cache_manager = Mock()
        return WebServer(
            mock_settings,
            mock_display_manager,
            mock_cache_manager,
            layout_registry=mock_layout_registry,
        )

    def test_set_layout_4x8(self, display_manager: DisplayManager) -> None:
        """Test setting layout to 4x8."""
        result = display_manager.set_layout("4x8")
        assert result is True
        assert display_manager.get_current_layout() == "4x8"

    def test_set_layout_3x4(self, display_manager: DisplayManager) -> None:
        """Test setting layout to 3x4."""
        result = display_manager.set_layout("3x4")
        assert result is True
        assert display_manager.get_current_layout() == "3x4"

    def test_set_layout_invalid(self, display_manager: DisplayManager) -> None:
        """Test setting invalid layout returns False."""
        # Patch the layout registry to return None for invalid layouts
        with patch.object(display_manager.layout_registry, "get_layout_info") as mock_get:
            mock_get.return_value = None

            result = display_manager.set_layout("invalid-layout")
            assert result is False

    def test_set_layout_same_layout(self, display_manager: DisplayManager) -> None:
        """Test setting layout to the same layout."""
        # First set to 3x4
        display_manager.set_layout("3x4")

        # Try to set to same layout - should still work
        result = display_manager.set_layout("3x4")
        assert result is True
        assert display_manager.get_current_layout() == "3x4"

    def test_get_available_layouts(self, display_manager: DisplayManager) -> None:
        """Test getting available layouts from registry."""
        layouts = display_manager.get_available_layouts()
        assert layouts == ["4x8", "3x4"]

    def test_set_display_type_changes_renderer(self, display_manager: DisplayManager) -> None:
        """Test setting display type (renderer) separately from layout."""
        with patch("calendarbot.display.manager.RendererFactory.create_renderer") as mock_create:
            mock_renderer = Mock()
            mock_create.return_value = mock_renderer

            result = display_manager.set_display_type("console")
            assert result is True
            assert display_manager.get_current_renderer_type() == "console"

    def test_web_server_set_layout(self, web_server: WebServer) -> None:
        """Test web server layout setting with new architecture."""
        # Mock the display manager's set_layout method (not set_display_type)
        web_server.display_manager.set_layout = Mock(return_value=True)

        result = web_server.set_layout("3x4")
        assert result is True
        # Web server calls set_layout with layout name
        web_server.display_manager.set_layout.assert_called_once_with("3x4")

    def test_web_server_set_layout_invalid(self, web_server: WebServer) -> None:
        """Test web server layout setting with invalid layout."""
        # Mock layout registry validation
        web_server.layout_registry.validate_layout.return_value = False
        web_server.layout_registry.get_available_layouts.return_value = ["4x8", "3x4"]

        result = web_server.set_layout("invalid-layout")
        assert result is False

    def test_web_server_cycle_layout(self, web_server: WebServer) -> None:
        """Test web server layout cycling from 3x4 to 4x8."""
        # Set initial state - web server layout property is the source of truth for layout names
        web_server.layout = "3x4"
        web_server.display_manager.set_layout = Mock(return_value=True)

        result = web_server.cycle_layout()
        assert result == "4x8"

    def test_web_server_cycle_layout_from_4x8(self, web_server: WebServer) -> None:
        """Test web server layout cycling from 4x8 to 3x4."""
        # Set initial state - web server layout property is the source of truth for layout names
        web_server.layout = "4x8"
        web_server.display_manager.set_layout = Mock(return_value=True)

        result = web_server.cycle_layout()
        assert result == "3x4"

    def test_web_server_get_current_layout(self, web_server: WebServer) -> None:
        """Test web server getting current layout."""
        web_server.layout = "3x4"

        result = web_server.get_current_layout()
        assert result == "3x4"

    def test_display_manager_renderer_factory_creation(
        self, mock_settings: Mock, mock_layout_registry: Mock
    ) -> None:
        """Test renderer creation using factory pattern."""
        mock_settings.display_type = "html"

        with patch("calendarbot.display.manager.LayoutRegistry", return_value=mock_layout_registry):
            with patch(
                "calendarbot.display.manager.RendererFactory.create_renderer"
            ) as mock_create:
                mock_renderer = Mock()
                mock_create.return_value = mock_renderer

                display_manager = DisplayManager(mock_settings)

                # Verify factory was used with old positional signature first
                mock_create.assert_called_once_with("html", mock_settings)

    def test_display_manager_layout_renderer_separation(
        self, display_manager: DisplayManager
    ) -> None:
        """Test that layout and renderer can be set independently."""
        # Set layout independently of renderer
        result = display_manager.set_layout("4x8")
        assert result is True
        assert display_manager.get_current_layout() == "4x8"

        # Set renderer independently of layout using set_display_type
        with patch("calendarbot.display.manager.RendererFactory.create_renderer") as mock_create:
            mock_renderer = Mock()
            mock_create.return_value = mock_renderer

            result = display_manager.set_display_type("console", "4x8")
            assert result is True
            assert display_manager.get_current_renderer_type() == "console"

    def test_layout_works_with_any_renderer(self, display_manager: DisplayManager) -> None:
        """Test that any layout can work with any compatible renderer."""
        with patch("calendarbot.display.manager.RendererFactory.create_renderer") as mock_create:
            mock_renderer = Mock()
            mock_create.return_value = mock_renderer

            # Test 4x8 layout with HTML renderer
            display_manager.set_display_type("html", "4x8")
            assert display_manager.get_current_layout() == "4x8"
            assert display_manager.get_current_renderer_type() == "html"

            # Test 3x4 layout with console renderer
            display_manager.set_display_type("console", "3x4")
            assert display_manager.get_current_layout() == "3x4"
            assert display_manager.get_current_renderer_type() == "console"

    def test_web_server_get_status_includes_layout_info(self, web_server: WebServer) -> None:
        """Test that get_status includes current layout information."""
        # Set up the web server with specific properties
        web_server.running = True
        web_server.host = "localhost"
        web_server.port = 8080
        web_server.display_manager.get_display_type.return_value = "3x4"

        # Get status
        status = web_server.get_status()

        # Verify layout info is included
        assert "layout" in status
        assert status["layout"] == "3x4"

        # Verify other expected fields are present
        assert status["running"] is True
        assert status["host"] == "localhost"
        assert status["port"] == 8080
        assert "interactive_mode" in status
        assert "current_date" in status

    def test_layout_registry_integration(self, web_server: WebServer) -> None:
        """Test that web server properly integrates with layout registry."""
        # Test that layout registry is used for validation
        web_server.layout_registry.validate_layout.return_value = True
        web_server.display_manager.set_layout = Mock(return_value=True)

        result = web_server.set_layout("4x8")
        assert result is True

        # Verify registry was called for validation
        web_server.layout_registry.validate_layout.assert_called_with("4x8")

    def test_renderer_factory_integration(self, display_manager: DisplayManager) -> None:
        """Test that display manager properly integrates with renderer factory."""
        with patch("calendarbot.display.manager.RendererFactory.create_renderer") as mock_create:
            mock_renderer = Mock()
            mock_create.return_value = mock_renderer

            # Test renderer creation through factory
            result = display_manager.set_display_type("console")
            assert result is True

            # Verify factory was used with new keyword signature
            mock_create.assert_called_with(
                settings=display_manager.settings, renderer_type="console", layout_name=None
            )

    def test_fallback_to_emergency_layouts(self, mock_settings: Mock) -> None:
        """Test fallback behavior when layout registry fails."""
        # Mock LayoutRegistry to throw exception during initialization
        with patch("calendarbot.display.manager.LayoutRegistry") as mock_registry_class:
            mock_registry_class.side_effect = Exception("Registry initialization failed")

            with patch(
                "calendarbot.display.manager.RendererFactory.create_renderer"
            ) as mock_create:
                mock_renderer = Mock()
                mock_create.return_value = mock_renderer

                # Should still create display manager with None registry
                display_manager = DisplayManager(mock_settings)
                assert display_manager.layout_registry is None

                # Should still have emergency fallback layouts available
                layouts = display_manager.get_available_display_types()
                assert "4x8" in layouts
                assert "3x4" in layouts

    def test_error_handling_renderer_factory_failure(self, display_manager: DisplayManager) -> None:
        """Test error handling when renderer factory fails."""
        with patch("calendarbot.display.manager.RendererFactory.create_renderer") as mock_create:
            mock_create.side_effect = Exception("Factory error")

            # Should handle factory errors gracefully
            result = display_manager.set_display_type("console")
            assert result is False

    def test_get_renderer_info_returns_complete_info(self, display_manager: DisplayManager) -> None:
        """Test that get_renderer_info returns complete renderer and layout information."""
        info = display_manager.get_renderer_info()

        # Verify all expected fields are present (matching actual implementation)
        assert "type" in info
        assert "enabled" in info
        assert "renderer_class" in info

        # Verify types
        assert isinstance(info["enabled"], bool)
        assert isinstance(info["type"], str)
        # renderer_class can be None if no renderer is available
        assert info["renderer_class"] is None or isinstance(info["renderer_class"], str)
