"""Test suite for calendarbot.display.manager module with new layout-renderer architecture."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from calendarbot.cache.models import CachedEvent
from calendarbot.display.manager import DisplayManager


class TestDisplayManagerInitialization:
    """Test DisplayManager initialization with renderer factory and layout registry."""

    @pytest.fixture
    def mock_layout_registry(self):
        """Create mock layout registry."""
        registry = Mock()
        registry.get_available_layouts.return_value = ["4x8", "3x4"]
        registry.validate_layout.return_value = True
        registry.get_default_layout.return_value = "4x8"
        return registry

    @pytest.fixture
    def mock_renderer_factory(self):
        """Create mock renderer factory."""
        factory = Mock()
        mock_renderer = Mock()
        factory.create_renderer.return_value = mock_renderer
        return factory

    def test_init_with_renderer_factory(self, mock_layout_registry, mock_renderer_factory) -> None:
        """Test initialization uses renderer factory instead of direct instantiation."""
        settings = Mock()
        settings.display_type = "html"
        settings.web_layout = "4x8"

        with patch("calendarbot.display.manager.LayoutRegistry", return_value=mock_layout_registry):
            with patch(
                "calendarbot.display.manager.RendererFactory", return_value=mock_renderer_factory
            ):
                manager = DisplayManager(settings)

                assert manager.settings == settings
                assert manager.layout_registry == mock_layout_registry
                assert manager.renderer_factory == mock_renderer_factory
                mock_renderer_factory.create_renderer.assert_called_once_with("html", settings)

    def test_init_with_layout_registry(self, mock_layout_registry, mock_renderer_factory) -> None:
        """Test initialization properly sets up layout registry."""
        settings = Mock()
        settings.display_type = "console"
        settings.web_layout = "3x4"

        with patch("calendarbot.display.manager.LayoutRegistry", return_value=mock_layout_registry):
            with patch(
                "calendarbot.display.manager.RendererFactory", return_value=mock_renderer_factory
            ):
                manager = DisplayManager(settings)

                assert manager.layout_registry == mock_layout_registry
                # Verify layout registry is initialized correctly
                mock_layout_registry.get_available_layouts.assert_called()

    def test_init_fallback_to_default_layout(
        self, mock_layout_registry, mock_renderer_factory
    ) -> None:
        """Test initialization falls back to default layout for invalid layout."""
        settings = Mock()
        settings.display_type = "html"
        settings.web_layout = "invalid-layout"

        mock_layout_registry.validate_layout.side_effect = lambda layout: layout in ["4x8", "3x4"]
        mock_layout_registry.get_default_layout.return_value = "4x8"

        with patch("calendarbot.display.manager.LayoutRegistry", return_value=mock_layout_registry):
            with patch(
                "calendarbot.display.manager.RendererFactory", return_value=mock_renderer_factory
            ):
                manager = DisplayManager(settings)

                # Should fall back to default layout
                assert manager.get_layout() == "4x8"

    def test_init_handles_renderer_factory_failure(self, mock_layout_registry) -> None:
        """Test initialization handles renderer factory failures gracefully."""
        settings = Mock()
        settings.display_type = "html"

        mock_factory = Mock()
        mock_factory.create_renderer.side_effect = Exception("Factory error")

        with patch("calendarbot.display.manager.LayoutRegistry", return_value=mock_layout_registry):
            with patch("calendarbot.display.manager.RendererFactory", return_value=mock_factory):
                # Should not raise exception, should handle gracefully
                manager = DisplayManager(settings)
                assert manager.renderer is None


class TestDisplayManagerLayoutRendererSeparation:
    """Test layout and renderer separation functionality."""

    @pytest.fixture
    def mock_setup(self):
        """Create common mock setup for layout-renderer tests."""
        settings = Mock()
        settings.display_type = "html"
        settings.web_layout = "4x8"
        settings.display_enabled = True

        layout_registry = Mock()
        layout_registry.get_available_layouts.return_value = ["4x8", "3x4"]
        layout_registry.validate_layout.return_value = True
        layout_registry.get_default_layout.return_value = "4x8"

        renderer_factory = Mock()
        mock_renderer = Mock()
        renderer_factory.create_renderer.return_value = mock_renderer

        return settings, layout_registry, renderer_factory, mock_renderer

    def test_set_layout_independent_of_renderer(self, mock_setup) -> None:
        """Test that layout can be set independently of renderer."""
        settings, layout_registry, renderer_factory, mock_renderer = mock_setup

        with patch("calendarbot.display.manager.LayoutRegistry", return_value=layout_registry):
            with patch(
                "calendarbot.display.manager.RendererFactory", return_value=renderer_factory
            ):
                manager = DisplayManager(settings)

                # Set layout to 3x4
                result = manager.set_layout("3x4")
                assert result is True
                assert manager.get_layout() == "3x4"

                # Renderer should remain unchanged
                assert manager.renderer == mock_renderer

    def test_set_renderer_type_independent_of_layout(self, mock_setup) -> None:
        """Test that renderer type can be set independently of layout."""
        settings, layout_registry, renderer_factory, mock_renderer = mock_setup

        with patch("calendarbot.display.manager.LayoutRegistry", return_value=layout_registry):
            with patch(
                "calendarbot.display.manager.RendererFactory", return_value=renderer_factory
            ) as mock_factory_class:
                # Set up the static method on the mocked class
                mock_factory_class.get_available_renderers.return_value = [
                    "html",
                    "rpi",
                    "compact",
                    "console",
                ]
                mock_factory_class.create_renderer.return_value = mock_renderer

                manager = DisplayManager(settings)
                original_layout = manager.get_layout()

                # Create new renderer for RPI
                rpi_renderer = Mock()
                mock_factory_class.create_renderer.return_value = rpi_renderer

                # Set renderer type to RPI
                result = manager.set_renderer_type("rpi")
                assert result is True
                assert manager.get_renderer_type() == "rpi"

                # Layout should remain unchanged
                assert manager.get_layout() == original_layout

    def test_get_available_layouts_from_registry(self, mock_setup) -> None:
        """Test getting available layouts from registry."""
        settings, layout_registry, renderer_factory, mock_renderer = mock_setup

        with patch("calendarbot.display.manager.LayoutRegistry", return_value=layout_registry):
            with patch(
                "calendarbot.display.manager.RendererFactory", return_value=renderer_factory
            ):
                manager = DisplayManager(settings)

                layouts = manager.get_available_layouts()
                assert layouts == ["4x8", "3x4"]
                layout_registry.get_available_layouts.assert_called()

    def test_validate_layout_through_registry(self, mock_setup) -> None:
        """Test layout validation through registry."""
        settings, layout_registry, renderer_factory, mock_renderer = mock_setup

        # Set up validation to fail for invalid layout
        layout_registry.validate_layout.side_effect = lambda layout: layout in ["4x8", "3x4"]

        with patch("calendarbot.display.manager.LayoutRegistry", return_value=layout_registry):
            with patch(
                "calendarbot.display.manager.RendererFactory", return_value=renderer_factory
            ):
                manager = DisplayManager(settings)

                # Valid layout should succeed
                result = manager.set_layout("4x8")
                assert result is True

                # Invalid layout should fail
                result = manager.set_layout("invalid-layout")
                assert result is False


class TestDisplayManagerDisplayEvents:
    """Test display_events method."""

    def create_test_manager(self, display_enabled: bool = True) -> Any:
        """Create test manager with mocked settings and renderer."""
        settings = Mock()
        settings.display_enabled = display_enabled
        settings.display_type = "console"
        settings.web_layout = "4x8"

        layout_registry = Mock()
        renderer_factory = Mock()
        mock_renderer = Mock()
        renderer_factory.create_renderer.return_value = mock_renderer

        with patch("calendarbot.display.manager.LayoutRegistry", return_value=layout_registry):
            with patch(
                "calendarbot.display.manager.RendererFactory", return_value=renderer_factory
            ):
                manager = DisplayManager(settings)
                manager.renderer = mock_renderer
                return manager, settings

    def create_sample_events(self) -> List[CachedEvent]:
        """Create sample cached events for testing."""
        return [
            CachedEvent(
                id="1",
                graph_id="graph-1",
                subject="Test Event 1",
                start_datetime="2024-01-01T10:00:00Z",
                end_datetime="2024-01-01T11:00:00Z",
                start_timezone="UTC",
                end_timezone="UTC",
                cached_at="2024-01-01T09:00:00Z",
            ),
            CachedEvent(
                id="2",
                graph_id="graph-2",
                subject="Test Event 2",
                start_datetime="2024-01-01T14:00:00Z",
                end_datetime="2024-01-01T15:00:00Z",
                start_timezone="UTC",
                end_timezone="UTC",
                cached_at="2024-01-01T09:00:00Z",
            ),
        ]

    @pytest.mark.asyncio
    async def test_display_events_success(self) -> None:
        """Test successful event display."""
        manager, settings = self.create_test_manager()
        events = self.create_sample_events()
        status_info: Dict[str, Any] = {"source": "test"}

        manager.renderer.render_events.return_value = "rendered content"
        manager.renderer.display_with_clear = Mock()

        with patch("builtins.print") as mock_print, patch(
            "calendarbot.display.manager.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"

            result = await manager.display_events(events, status_info, clear_screen=True)

            assert result is True
            manager.renderer.render_events.assert_called_once()

            # Check status info was enhanced with last_update
            call_args = manager.renderer.render_events.call_args
            assert call_args[0][0] == events  # First arg: events
            enhanced_status = call_args[0][1]  # Second arg: status_info
            assert enhanced_status["source"] == "test"
            assert enhanced_status["last_update"] == "2024-01-01T12:00:00"

            manager.renderer.display_with_clear.assert_called_once_with("rendered content")
            mock_print.assert_not_called()  # Should use display_with_clear, not print

    @pytest.mark.asyncio
    async def test_display_events_no_clear_screen(self) -> None:
        """Test event display without clearing screen."""
        manager, settings = self.create_test_manager()
        events = self.create_sample_events()

        manager.renderer.render_events.return_value = "rendered content"

        with patch("builtins.print") as mock_print, patch(
            "calendarbot.display.manager.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"

            result = await manager.display_events(events, clear_screen=False)

            assert result is True
            mock_print.assert_called_once_with("rendered content")

    @pytest.mark.asyncio
    async def test_display_events_no_display_with_clear_method(self) -> None:
        """Test event display when renderer lacks display_with_clear method."""
        manager, settings = self.create_test_manager()
        events = self.create_sample_events()

        manager.renderer.render_events.return_value = "rendered content"
        # Remove display_with_clear method to simulate basic renderer
        delattr(manager.renderer, "display_with_clear")

        with patch("builtins.print") as mock_print, patch(
            "calendarbot.display.manager.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"

            result = await manager.display_events(events, clear_screen=True)

            assert result is True
            mock_print.assert_called_once_with("rendered content")

    @pytest.mark.asyncio
    async def test_display_events_display_disabled(self) -> None:
        """Test event display when display is disabled."""
        manager, settings = self.create_test_manager(display_enabled=False)
        events = self.create_sample_events()

        result = await manager.display_events(events)

        assert result is True
        manager.renderer.render_events.assert_not_called()

    @pytest.mark.asyncio
    async def test_display_events_no_renderer(self) -> None:
        """Test event display when no renderer is available."""
        manager, settings = self.create_test_manager()
        manager.renderer = None
        events = self.create_sample_events()

        result = await manager.display_events(events)

        assert result is False

    @pytest.mark.asyncio
    async def test_display_events_none_status_info(self) -> None:
        """Test event display with None status info."""
        manager, settings = self.create_test_manager()
        events = self.create_sample_events()

        manager.renderer.render_events.return_value = "content"

        with patch("builtins.print"), patch(
            "calendarbot.display.manager.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"

            result = await manager.display_events(events, status_info=None)

            assert result is True
            call_args = manager.renderer.render_events.call_args[0][1]
            assert call_args["last_update"] == "2024-01-01T12:00:00"

    @pytest.mark.asyncio
    async def test_display_events_exception_handling(self) -> None:
        """Test event display exception handling."""
        manager, settings = self.create_test_manager()
        events = self.create_sample_events()

        manager.renderer.render_events.side_effect = Exception("Render error")

        result = await manager.display_events(events)

        assert result is False


class TestDisplayManagerDisplayError:
    """Test display_error method."""

    def create_test_manager(self, display_enabled: bool = True) -> Any:
        """Create test manager with mocked settings and renderer."""
        settings = Mock()
        settings.display_enabled = display_enabled
        settings.display_type = "console"

        with patch("calendarbot.display.manager.ConsoleRenderer"):
            manager = DisplayManager(settings)
            manager.renderer = Mock()
            return manager, settings

    @pytest.mark.asyncio
    async def test_display_error_success(self) -> None:
        """Test successful error display."""
        manager, settings = self.create_test_manager()
        error_message = "Test error message"
        cached_events: List[Any] = []

        manager.renderer.render_error.return_value = "error content"
        manager.renderer.display_with_clear = Mock()

        with patch("builtins.print") as mock_print:
            result = await manager.display_error(error_message, cached_events, clear_screen=True)

            assert result is True
            manager.renderer.render_error.assert_called_once_with(error_message, cached_events)
            manager.renderer.display_with_clear.assert_called_once_with("error content")
            mock_print.assert_not_called()

    @pytest.mark.asyncio
    async def test_display_error_no_clear_screen(self) -> None:
        """Test error display without clearing screen."""
        manager, settings = self.create_test_manager()
        error_message = "Test error"

        manager.renderer.render_error.return_value = "error content"

        with patch("builtins.print") as mock_print:
            result = await manager.display_error(error_message, clear_screen=False)

            assert result is True
            mock_print.assert_called_once_with("error content")

    @pytest.mark.asyncio
    async def test_display_error_display_disabled(self) -> None:
        """Test error display when display is disabled."""
        manager, settings = self.create_test_manager(display_enabled=False)

        result = await manager.display_error("Test error")

        assert result is True
        manager.renderer.render_error.assert_not_called()

    @pytest.mark.asyncio
    async def test_display_error_no_renderer(self) -> None:
        """Test error display when no renderer is available."""
        manager, settings = self.create_test_manager()
        manager.renderer = None

        result = await manager.display_error("Test error")

        assert result is False

    @pytest.mark.asyncio
    async def test_display_error_exception_handling(self) -> None:
        """Test error display exception handling."""
        manager, settings = self.create_test_manager()

        manager.renderer.render_error.side_effect = Exception("Render error")

        result = await manager.display_error("Test error")

        assert result is False


class TestDisplayManagerDisplayAuthenticationPrompt:
    """Test display_authentication_prompt method."""

    def create_test_manager(self, display_enabled: bool = True) -> Any:
        """Create test manager with mocked settings and renderer."""
        settings = Mock()
        settings.display_enabled = display_enabled
        settings.display_type = "console"

        with patch("calendarbot.display.manager.ConsoleRenderer"):
            manager = DisplayManager(settings)
            manager.renderer = Mock()
            return manager, settings

    @pytest.mark.asyncio
    async def test_display_authentication_prompt_success(self) -> None:
        """Test successful authentication prompt display."""
        manager, settings = self.create_test_manager()
        verification_uri = "https://example.com/auth"
        user_code = "ABC123"

        manager.renderer.render_authentication_prompt.return_value = "auth content"
        manager.renderer.display_with_clear = Mock()

        with patch("builtins.print") as mock_print:
            result = await manager.display_authentication_prompt(
                verification_uri, user_code, clear_screen=True
            )

            assert result is True
            manager.renderer.render_authentication_prompt.assert_called_once_with(
                verification_uri, user_code
            )
            manager.renderer.display_with_clear.assert_called_once_with("auth content")
            mock_print.assert_not_called()

    @pytest.mark.asyncio
    async def test_display_authentication_prompt_no_clear_screen(self) -> None:
        """Test authentication prompt display without clearing screen."""
        manager, settings = self.create_test_manager()
        verification_uri = "https://example.com/auth"
        user_code = "ABC123"

        manager.renderer.render_authentication_prompt.return_value = "auth content"

        with patch("builtins.print") as mock_print:
            result = await manager.display_authentication_prompt(
                verification_uri, user_code, clear_screen=False
            )

            assert result is True
            mock_print.assert_called_once_with("auth content")

    @pytest.mark.asyncio
    async def test_display_authentication_prompt_display_disabled(self) -> None:
        """Test authentication prompt when display is disabled."""
        manager, settings = self.create_test_manager(display_enabled=False)

        result = await manager.display_authentication_prompt("uri", "code")

        assert result is True
        manager.renderer.render_authentication_prompt.assert_not_called()

    @pytest.mark.asyncio
    async def test_display_authentication_prompt_no_renderer(self) -> None:
        """Test authentication prompt when no renderer is available."""
        manager, settings = self.create_test_manager()
        manager.renderer = None

        result = await manager.display_authentication_prompt("uri", "code")

        assert result is False

    @pytest.mark.asyncio
    async def test_display_authentication_prompt_exception_handling(self) -> None:
        """Test authentication prompt exception handling."""
        manager, settings = self.create_test_manager()

        manager.renderer.render_authentication_prompt.side_effect = Exception("Render error")

        result = await manager.display_authentication_prompt("uri", "code")

        assert result is False


class TestDisplayManagerDisplayStatus:
    """Test display_status method."""

    def create_test_manager(self, display_enabled: bool = True) -> Any:
        """Create test manager with mocked settings and renderer."""
        settings = Mock()
        settings.display_enabled = display_enabled
        settings.display_type = "console"

        with patch("calendarbot.display.manager.ConsoleRenderer"):
            manager = DisplayManager(settings)
            manager.renderer = Mock()
            return manager, settings

    @pytest.mark.asyncio
    async def test_display_status_success(self) -> None:
        """Test successful status display."""
        manager, settings = self.create_test_manager()
        status_info: Dict[str, Any] = {
            "events_count": 5,
            "last_update": "2024-01-01T12:00:00",
            "cache_size": "1.2MB",
        }

        manager.renderer.display_with_clear = Mock()

        with patch("builtins.print") as mock_print:
            result = await manager.display_status(status_info, clear_screen=True)

            assert result is True
            manager.renderer.display_with_clear.assert_called_once()

            # Check the content passed to display_with_clear
            call_args = manager.renderer.display_with_clear.call_args[0][0]
            assert "📊 CALENDAR BOT STATUS" in call_args
            assert "Events Count: 5" in call_args
            assert "Last Update: 2024-01-01T12:00:00" in call_args
            assert "Cache Size: 1.2MB" in call_args
            assert "=" * 60 in call_args

            mock_print.assert_not_called()

    @pytest.mark.asyncio
    async def test_display_status_no_clear_screen(self) -> None:
        """Test status display without clearing screen."""
        manager, settings = self.create_test_manager()
        status_info: Dict[str, Any] = {"test_key": "test_value"}

        with patch("builtins.print") as mock_print:
            result = await manager.display_status(status_info, clear_screen=False)

            assert result is True
            mock_print.assert_called_once()

            # Check the content passed to print
            call_args = mock_print.call_args[0][0]
            assert "📊 CALENDAR BOT STATUS" in call_args
            assert "Test Key: test_value" in call_args

    @pytest.mark.asyncio
    async def test_display_status_no_renderer(self) -> None:
        """Test status display when renderer is None but still works."""
        manager, settings = self.create_test_manager()
        manager.renderer = None
        status_info: Dict[str, Any] = {"test": "value"}

        with patch("builtins.print") as mock_print:
            result = await manager.display_status(status_info, clear_screen=True)

            assert result is True
            mock_print.assert_called_once()

    @pytest.mark.asyncio
    async def test_display_status_renderer_without_display_with_clear(self) -> None:
        """Test status display when renderer lacks display_with_clear method."""
        manager, settings = self.create_test_manager()
        # Remove display_with_clear method
        delattr(manager.renderer, "display_with_clear")
        status_info: Dict[str, Any] = {"test": "value"}

        with patch("builtins.print") as mock_print:
            result = await manager.display_status(status_info, clear_screen=True)

            assert result is True
            mock_print.assert_called_once()

    @pytest.mark.asyncio
    async def test_display_status_display_disabled(self) -> None:
        """Test status display when display is disabled."""
        manager, settings = self.create_test_manager(display_enabled=False)

        result = await manager.display_status({"test": "value"})

        assert result is True

    @pytest.mark.asyncio
    async def test_display_status_key_formatting(self) -> None:
        """Test status display key formatting."""
        manager, settings = self.create_test_manager()
        status_info: Dict[str, Any] = {
            "snake_case_key": "value1",
            "another_test_key": "value2",
            "simple": "value3",
        }

        with patch("builtins.print") as mock_print:
            result = await manager.display_status(status_info, clear_screen=False)

            assert result is True
            content = mock_print.call_args[0][0]
            assert "Snake Case Key: value1" in content
            assert "Another Test Key: value2" in content
            assert "Simple: value3" in content

    @pytest.mark.asyncio
    async def test_display_status_exception_handling(self) -> None:
        """Test status display exception handling."""
        manager, settings = self.create_test_manager()

        # Create a status_info that will cause an exception when iterating
        class BadDict:
            def items(self) -> None:
                raise Exception("Status error")

        result = await manager.display_status(BadDict())

        assert result is False


class TestDisplayManagerClearDisplay:
    """Test clear_display method."""

    def create_test_manager(self) -> Any:
        """Create test manager with mocked settings and renderer."""
        settings = Mock()
        settings.display_type = "console"

        with patch("calendarbot.display.manager.ConsoleRenderer"):
            manager = DisplayManager(settings)
            manager.renderer = Mock()
            return manager, settings

    def test_clear_display_with_renderer_clear_screen(self) -> None:
        """Test clearing display when renderer has clear_screen method."""
        manager, settings = self.create_test_manager()
        manager.renderer.clear_screen.return_value = True

        result = manager.clear_display()

        assert result is True
        manager.renderer.clear_screen.assert_called_once()

    def test_clear_display_renderer_without_clear_screen(self) -> None:
        """Test clearing display when renderer lacks clear_screen method."""
        manager, settings = self.create_test_manager()
        # Remove clear_screen method
        delattr(manager.renderer, "clear_screen")

        with patch("calendarbot.display.manager.secure_clear_screen") as mock_secure_clear:
            mock_secure_clear.return_value = True

            result = manager.clear_display()

            assert result is True
            mock_secure_clear.assert_called_once()

    def test_clear_display_no_renderer(self) -> None:
        """Test clearing display when no renderer is available."""
        manager, settings = self.create_test_manager()
        manager.renderer = None

        with patch("calendarbot.display.manager.secure_clear_screen") as mock_secure_clear:
            mock_secure_clear.return_value = True

            result = manager.clear_display()

            assert result is True
            mock_secure_clear.assert_called_once()

    def test_clear_display_exception_handling(self) -> None:
        """Test clear display exception handling."""
        manager, settings = self.create_test_manager()
        manager.renderer.clear_screen.side_effect = Exception("Clear error")

        result = manager.clear_display()

        assert result is False


class TestDisplayManagerGetRendererInfo:
    """Test get_renderer_info method."""

    def test_get_renderer_info_with_renderer(self) -> None:
        """Test getting renderer info when renderer is available."""
        settings = Mock()
        settings.display_type = "console"
        settings.display_enabled = True
        settings.web_layout = None  # Will get default layout (whats-next-view)

        with patch("calendarbot.display.manager.LayoutRegistry") as mock_registry_class:
            mock_registry = Mock()
            mock_registry.get_available_layouts.return_value = ["whats-next-view", "4x8", "3x4"]
            mock_registry.validate_layout.return_value = True
            mock_registry.get_default_layout.return_value = "whats-next-view"
            mock_registry_class.return_value = mock_registry

            with patch("calendarbot.display.manager.RendererFactory") as mock_factory_class:
                mock_factory = Mock()
                mock_renderer = Mock()
                mock_renderer.__class__.__name__ = "WhatsNextRenderer"
                mock_factory.create_renderer.return_value = mock_renderer
                mock_factory_class.return_value = mock_factory

                manager = DisplayManager(settings)
                info = manager.get_renderer_info()

                expected = {
                    "type": "console",
                    "enabled": True,
                    "renderer_class": "WhatsNextRenderer",
                }
                assert info == expected

    def test_get_renderer_info_no_renderer(self) -> None:
        """Test getting renderer info when no renderer is available."""
        settings = Mock()
        settings.display_type = "unknown"
        settings.display_enabled = False

        with patch("calendarbot.display.manager.ConsoleRenderer"):
            manager = DisplayManager(settings)
            manager.renderer = None

            info = manager.get_renderer_info()

            expected = {"type": "unknown", "enabled": False, "renderer_class": None}
            assert info == expected


class TestDisplayManagerIntegration:
    """Integration tests for DisplayManager."""

    @pytest.mark.asyncio
    async def test_full_display_workflow(self) -> None:
        """Test complete display workflow with events."""
        settings = Mock()
        settings.display_type = "console"
        settings.display_enabled = True
        settings.web_layout = None  # Will get default layout (whats-next-view)

        events: List[CachedEvent] = [
            CachedEvent(
                id="1",
                graph_id="graph-1",
                subject="Meeting",
                start_datetime="2024-01-01T10:00:00Z",
                end_datetime="2024-01-01T11:00:00Z",
                start_timezone="UTC",
                end_timezone="UTC",
                cached_at="2024-01-01T09:00:00Z",
            )
        ]

        with patch("calendarbot.display.manager.LayoutRegistry") as mock_registry_class:
            mock_registry = Mock()
            mock_registry.get_available_layouts.return_value = ["whats-next-view", "4x8", "3x4"]
            mock_registry.validate_layout.return_value = True
            mock_registry.get_default_layout.return_value = "whats-next-view"
            mock_registry_class.return_value = mock_registry

            with patch("calendarbot.display.manager.RendererFactory") as mock_factory_class:
                mock_factory = Mock()
                mock_renderer = Mock()
                mock_renderer.render_events.return_value = "Formatted events"
                mock_renderer.render_error.return_value = "Error content"
                mock_renderer.display_with_clear = Mock()
                mock_renderer.clear_screen.return_value = True
                mock_factory.create_renderer.return_value = mock_renderer
                mock_factory_class.return_value = mock_factory

                manager = DisplayManager(settings)

                with patch("calendarbot.display.manager.datetime") as mock_datetime:
                    mock_datetime.now.return_value.isoformat.return_value = "2024-01-01T12:00:00"

                    # Test successful display
                    result = await manager.display_events(events)
                    assert result is True

                    # Test error display
                    result = await manager.display_error("Connection failed", events)
                    assert result is True

                    # Test status display
                    result = await manager.display_status({"events": len(events)})
                    assert result is True

                    # Test clear display
                    result = manager.clear_display()
                    assert result is True

                    # Test renderer info
                    info = manager.get_renderer_info()
                    assert info["type"] == "console"
                    assert info["enabled"] is True
