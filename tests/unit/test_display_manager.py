"""Test suite for calendarbot.display.manager module."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from calendarbot.cache.models import CachedEvent
from calendarbot.display.manager import DisplayManager


class TestDisplayManagerInitialization:
    """Test DisplayManager initialization and renderer selection."""

    def test_init_console_renderer(self) -> None:
        """Test initialization with console display type."""
        settings = Mock()
        settings.display_type = "console"

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_console:
            mock_renderer = Mock()
            mock_console.return_value = mock_renderer

            manager = DisplayManager(settings)

            assert manager.settings == settings
            assert manager.renderer == mock_renderer
            mock_console.assert_called_once_with(settings)

    def test_init_html_renderer(self) -> None:
        """Test initialization with HTML display type."""
        settings = Mock()
        settings.display_type = "html"

        with patch("calendarbot.display.manager.HTMLRenderer") as mock_html:
            mock_renderer = Mock()
            mock_html.return_value = mock_renderer

            manager = DisplayManager(settings)

            assert manager.settings == settings
            assert manager.renderer == mock_renderer
            mock_html.assert_called_once_with(settings)

    def test_init_rpi_renderer(self) -> None:
        """Test initialization with Raspberry Pi display type."""
        settings = Mock()
        settings.display_type = "rpi"

        with patch("calendarbot.display.manager.RaspberryPiHTMLRenderer") as mock_rpi:
            mock_renderer = Mock()
            mock_rpi.return_value = mock_renderer

            manager = DisplayManager(settings)

            assert manager.settings == settings
            assert manager.renderer == mock_renderer
            mock_rpi.assert_called_once_with(settings)

    def test_init_rpi_html_renderer(self) -> None:
        """Test initialization with rpi-html display type."""
        settings = Mock()
        settings.display_type = "rpi-html"

        with patch("calendarbot.display.manager.RaspberryPiHTMLRenderer") as mock_rpi:
            mock_renderer = Mock()
            mock_rpi.return_value = mock_renderer

            manager = DisplayManager(settings)

            assert manager.settings == settings
            assert manager.renderer == mock_renderer
            mock_rpi.assert_called_once_with(settings)

    def test_init_unknown_display_type_defaults_to_console(self) -> None:
        """Test initialization with unknown display type defaults to console."""
        settings = Mock()
        settings.display_type = "unknown_type"

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_console:
            mock_renderer = Mock()
            mock_console.return_value = mock_renderer

            manager = DisplayManager(settings)

            assert manager.settings == settings
            assert manager.renderer == mock_renderer
            mock_console.assert_called_once_with(settings)


class TestDisplayManagerDisplayEvents:
    """Test display_events method."""

    def create_test_manager(self, display_enabled: bool = True) -> Any:
        """Create test manager with mocked settings and renderer."""
        settings = Mock()
        settings.display_enabled = display_enabled
        settings.display_type = "console"

        with patch("calendarbot.display.manager.ConsoleRenderer"):
            manager = DisplayManager(settings)
            manager.renderer = Mock()
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

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_console:
            mock_renderer = Mock()
            mock_renderer.__class__.__name__ = "ConsoleRenderer"
            mock_console.return_value = mock_renderer

            manager = DisplayManager(settings)
            info = manager.get_renderer_info()

            expected = {"type": "console", "enabled": True, "renderer_class": "ConsoleRenderer"}
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

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_console:
            mock_renderer = Mock()
            mock_renderer.render_events.return_value = "Formatted events"
            mock_renderer.render_error.return_value = "Error content"
            mock_renderer.display_with_clear = Mock()
            mock_renderer.clear_screen.return_value = True  # Ensure clear_screen returns True
            mock_console.return_value = mock_renderer

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
