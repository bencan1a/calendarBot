"""Enhanced unit tests for calendarbot/display/manager.py - Display management system."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDisplayManager:
    """Test suite for DisplayManager core functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for display testing."""
        settings = MagicMock()
        settings.display_type = "console"
        settings.display_enabled = True
        settings.web_host = "localhost"
        settings.web_port = 8080
        settings.web_theme = "standard"
        settings.log_level = "INFO"
        settings.data_dir = Path("/tmp/test")
        return settings

    @pytest.fixture
    def sample_cached_events(self):
        """Sample cached events for display testing."""
        from calendarbot.cache.models import CachedEvent

        now = datetime.now()
        start_time = now + timedelta(hours=1)
        end_time = now + timedelta(hours=2)
        return [
            CachedEvent(
                id="event_1",
                graph_id="outlook_graph_1",
                subject="Test Meeting",
                body_preview="Important meeting",
                start_datetime=start_time.isoformat(),
                end_datetime=end_time.isoformat(),
                start_timezone="UTC",
                end_timezone="UTC",
                is_all_day=False,
                location_display_name="Conference Room A",
                cached_at=now.isoformat(),
            ),
            CachedEvent(
                id="event_2",
                graph_id="outlook_graph_2",
                subject="All Day Event",
                body_preview="Conference day",
                start_datetime=now.replace(hour=0).isoformat(),
                end_datetime=now.replace(hour=23).isoformat(),
                start_timezone="UTC",
                end_timezone="UTC",
                is_all_day=True,
                location_display_name="",
                cached_at=now.isoformat(),
            ),
        ]

    def test_display_manager_initialization_console(self, mock_settings):
        """Test DisplayManager initialization with console renderer."""
        mock_settings.display_type = "console"

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer:
            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)

            assert manager.settings == mock_settings
            assert manager.renderer is not None
            mock_renderer.assert_called_once_with(mock_settings)

    def test_display_manager_initialization_html(self, mock_settings):
        """Test DisplayManager initialization with HTML renderer."""
        mock_settings.display_type = "html"

        with patch("calendarbot.display.manager.HTMLRenderer") as mock_renderer:
            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)

            assert manager.settings == mock_settings
            assert manager.renderer is not None
            mock_renderer.assert_called_once_with(mock_settings)

    def test_display_manager_initialization_rpi(self, mock_settings):
        """Test DisplayManager initialization with RPI renderer."""
        mock_settings.display_type = "rpi"

        with patch("calendarbot.display.manager.RaspberryPiHTMLRenderer") as mock_renderer:
            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)

            assert manager.settings == mock_settings
            assert manager.renderer is not None
            mock_renderer.assert_called_once_with(mock_settings)

    def test_display_manager_initialization_rpi_html(self, mock_settings):
        """Test DisplayManager initialization with rpi-html renderer."""
        mock_settings.display_type = "rpi-html"

        with patch("calendarbot.display.manager.RaspberryPiHTMLRenderer") as mock_renderer:
            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)

            assert manager.settings == mock_settings
            assert manager.renderer is not None
            mock_renderer.assert_called_once_with(mock_settings)

    def test_display_manager_initialization_unknown_type(self, mock_settings):
        """Test DisplayManager initialization with unknown display type defaults to console."""
        mock_settings.display_type = "unknown"

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer:
            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)

            assert manager.settings == mock_settings
            assert manager.renderer is not None
            mock_renderer.assert_called_once_with(mock_settings)

    @pytest.mark.asyncio
    async def test_display_events_success(self, mock_settings, sample_cached_events):
        """Test successful event display."""
        mock_settings.display_enabled = True

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.render_events.return_value = "Event content"
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            result = await manager.display_events(sample_cached_events)

            assert result is True
            mock_renderer.render_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_display_events_disabled(self, mock_settings, sample_cached_events):
        """Test event display when display is disabled."""
        mock_settings.display_enabled = False

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            result = await manager.display_events(sample_cached_events)

            assert result is True

    @pytest.mark.asyncio
    async def test_display_events_with_clear_screen(self, mock_settings, sample_cached_events):
        """Test event display with clear screen capability."""
        mock_settings.display_enabled = True

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.render_events.return_value = "Event content"
            mock_renderer.display_with_clear = MagicMock()
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            result = await manager.display_events(sample_cached_events, clear_screen=True)

            assert result is True
            mock_renderer.display_with_clear.assert_called_once_with("Event content")

    @pytest.mark.asyncio
    async def test_display_events_with_status_info(self, mock_settings, sample_cached_events):
        """Test event display with status information."""
        mock_settings.display_enabled = True
        status_info = {"last_sync": "2023-01-01", "source_count": 2}

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class, patch(
            "builtins.print"
        ) as mock_print:
            mock_renderer = MagicMock()
            mock_renderer.render_events.return_value = "Event content"
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            result = await manager.display_events(sample_cached_events, status_info=status_info)

            assert result is True
            # Verify status_info was passed and modified
            call_args = mock_renderer.render_events.call_args[0]
            assert call_args[0] == sample_cached_events
            assert "last_update" in call_args[1]  # Should add last_update timestamp

    @pytest.mark.asyncio
    async def test_display_events_renderer_exception(self, mock_settings, sample_cached_events):
        """Test event display with renderer exception."""
        mock_settings.display_enabled = True

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.render_events.side_effect = Exception("Render error")
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            result = await manager.display_events(sample_cached_events)

            assert result is False

    @pytest.mark.asyncio
    async def test_display_error_success(self, mock_settings):
        """Test successful error display."""
        mock_settings.display_enabled = True
        error_message = "Test error message"

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.render_error.return_value = "Error content"
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            result = await manager.display_error(error_message)

            assert result is True
            mock_renderer.render_error.assert_called_once_with(error_message, None)

    @pytest.mark.asyncio
    async def test_display_error_with_cached_events(self, mock_settings, sample_cached_events):
        """Test error display with cached events."""
        mock_settings.display_enabled = True
        error_message = "Test error message"

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class, patch(
            "builtins.print"
        ) as mock_print:
            mock_renderer = MagicMock()
            mock_renderer.render_error.return_value = "Error content with cached events"
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            result = await manager.display_error(error_message, cached_events=sample_cached_events)

            assert result is True
            mock_renderer.render_error.assert_called_once_with(error_message, sample_cached_events)

    @pytest.mark.asyncio
    async def test_display_error_disabled(self, mock_settings):
        """Test error display when display is disabled."""
        mock_settings.display_enabled = False

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            result = await manager.display_error("Test error")

            assert result is True

    @pytest.mark.asyncio
    async def test_display_authentication_prompt_success(self, mock_settings):
        """Test successful authentication prompt display."""
        mock_settings.display_enabled = True
        verification_uri = "https://microsoft.com/devicelogin"
        user_code = "ABC123"

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.render_authentication_prompt.return_value = "Auth prompt content"
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            result = await manager.display_authentication_prompt(verification_uri, user_code)

            assert result is True
            mock_renderer.render_authentication_prompt.assert_called_once_with(
                verification_uri, user_code
            )

    @pytest.mark.asyncio
    async def test_display_authentication_prompt_disabled(self, mock_settings):
        """Test authentication prompt when display is disabled."""
        mock_settings.display_enabled = False

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            result = await manager.display_authentication_prompt("https://test.com", "ABC123")

            assert result is True

    @pytest.mark.asyncio
    async def test_display_status_success(self, mock_settings):
        """Test successful status display."""
        mock_settings.display_enabled = True
        status_info = {"cache_status": "healthy", "last_sync": "2023-01-01"}

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class, patch(
            "builtins.print"
        ) as mock_print:
            mock_renderer_class.return_value = MagicMock()

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            result = await manager.display_status(status_info)

            assert result is True
            # display_status method should complete successfully
            # The actual printing is handled internally by the status display logic

    @pytest.mark.asyncio
    async def test_display_status_with_renderer_clear(self, mock_settings):
        """Test status display with renderer clear capability."""
        mock_settings.display_enabled = True
        status_info = {"test": "value"}

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.display_with_clear = MagicMock()
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            result = await manager.display_status(status_info, clear_screen=True)

            assert result is True
            mock_renderer.display_with_clear.assert_called_once()

    def test_clear_display_with_renderer_support(self, mock_settings):
        """Test clear display when renderer supports it."""
        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.clear_screen = MagicMock()
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            manager.clear_display()

            mock_renderer.clear_screen.assert_called_once()

    def test_clear_display_fallback(self, mock_settings):
        """Test clear display fallback to OS command."""
        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class, patch(
            "os.system"
        ) as mock_system:
            mock_renderer = MagicMock()
            # Remove clear_screen method to test fallback
            del mock_renderer.clear_screen
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            manager.clear_display()

            mock_system.assert_called_once_with("clear")

    def test_clear_display_exception_handling(self, mock_settings):
        """Test clear display exception handling."""
        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.clear_screen.side_effect = Exception("Clear error")
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            # Should not raise exception
            manager.clear_display()

    def test_get_renderer_info(self, mock_settings):
        """Test getting renderer information."""
        mock_settings.display_type = "console"
        mock_settings.display_enabled = True

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.__class__.__name__ = "ConsoleRenderer"
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            info = manager.get_renderer_info()

            assert info["type"] == "console"
            assert info["enabled"] is True
            assert info["renderer_class"] == "ConsoleRenderer"

    def test_get_renderer_info_no_renderer(self, mock_settings):
        """Test getting renderer info when no renderer is available."""
        mock_settings.display_type = "console"
        mock_settings.display_enabled = True

        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            mock_renderer_class.return_value = None

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(mock_settings)
            manager.renderer = None  # Simulate no renderer
            info = manager.get_renderer_info()

            assert info["type"] == "console"
            assert info["enabled"] is True
            assert info["renderer_class"] is None


@pytest.mark.unit
class TestDisplayManagerEdgeCases:
    """Test edge cases and error conditions for DisplayManager."""

    @pytest.fixture
    def minimal_settings(self):
        """Minimal settings for edge case testing."""
        settings = MagicMock()
        settings.display_type = "console"
        settings.display_enabled = True
        return settings

    def test_initialization_with_none_settings(self):
        """Test initialization with None settings."""
        from calendarbot.display.manager import DisplayManager

        with pytest.raises((AttributeError, TypeError)):
            DisplayManager(None)

    def test_initialization_missing_display_type(self):
        """Test initialization with missing display_type setting."""
        from calendarbot.display.manager import DisplayManager

        settings = MagicMock()
        del settings.display_type  # Remove display_type attribute

        with pytest.raises(AttributeError):
            DisplayManager(settings)

    @pytest.mark.asyncio
    async def test_display_events_none_events(self, minimal_settings):
        """Test displaying None events list."""
        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.render_events.return_value = "Empty content"
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(minimal_settings)
            result = await manager.display_events(None)

            # Should return False due to error handling of None events
            assert result is False

    @pytest.mark.asyncio
    async def test_display_error_none_message(self, minimal_settings):
        """Test displaying None error message."""
        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class, patch(
            "builtins.print"
        ) as mock_print:
            mock_renderer = MagicMock()
            mock_renderer.render_error.return_value = "Error content"
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(minimal_settings)
            result = await manager.display_error(None)

            assert result is True
            mock_renderer.render_error.assert_called_once_with(None, None)

    @pytest.mark.asyncio
    async def test_no_renderer_available(self, minimal_settings):
        """Test behavior when renderer is None."""
        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            mock_renderer_class.return_value = None

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(minimal_settings)
            manager.renderer = None  # Simulate no renderer

            result = await manager.display_events([])
            assert result is False

            result = await manager.display_error("Error")
            assert result is False

            result = await manager.display_authentication_prompt("url", "code")
            assert result is False

    @pytest.mark.asyncio
    async def test_concurrent_display_operations(self, minimal_settings):
        """Test concurrent display operations."""
        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class, patch(
            "builtins.print"
        ) as mock_print:
            mock_renderer = MagicMock()
            mock_renderer.render_events.return_value = "Events"
            mock_renderer.render_error.return_value = "Error"
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(minimal_settings)

            # Run multiple operations concurrently
            tasks = [
                manager.display_events([]),
                manager.display_error("Error 1"),
                manager.display_error("Error 2"),
            ]

            results = await asyncio.gather(*tasks)

            # All operations should succeed
            assert all(results)

    def test_settings_modification_after_init(self, minimal_settings):
        """Test behavior when settings are modified after initialization."""
        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            mock_renderer_class.return_value = MagicMock()

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(minimal_settings)
            original_renderer = manager.renderer

            # Modify settings after initialization
            minimal_settings.display_type = "html"

            # Renderer should remain the same (no automatic reinitialization)
            assert manager.renderer == original_renderer

    @pytest.mark.asyncio
    async def test_exception_during_async_operation(self, minimal_settings):
        """Test exception handling during async operations."""
        with patch("calendarbot.display.manager.ConsoleRenderer") as mock_renderer_class:
            mock_renderer = MagicMock()
            mock_renderer.render_events.side_effect = asyncio.CancelledError("Operation cancelled")
            mock_renderer_class.return_value = mock_renderer

            from calendarbot.display.manager import DisplayManager

            manager = DisplayManager(minimal_settings)

            # Should handle CancelledError gracefully
            with pytest.raises(asyncio.CancelledError):
                await manager.display_events([])
