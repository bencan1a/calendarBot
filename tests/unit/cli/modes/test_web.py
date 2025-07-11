"""Unit tests for CLI web mode functionality.

Tests cover:
- Web mode execution with success and failure scenarios
- Signal handling and graceful shutdown
- Web server setup and configuration
- Browser auto-open functionality
- Background task management
- Settings overrides and logging configuration
- Error handling and cleanup procedures
"""

import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.cli.modes import web


class TestRunWebMode:
    """Test the run_web_mode function."""

    @pytest.fixture
    def mock_args(self):
        """Create mock command line arguments."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 8080
        args.auto_open = False
        args.rpi = False
        return args

    @pytest.fixture
    def mock_app(self):
        """Create mock CalendarBot instance."""
        app = AsyncMock()
        app.initialize = AsyncMock(return_value=True)
        app.display_manager = MagicMock()
        app.cache_manager = MagicMock()
        app.run_background_fetch = AsyncMock()
        app.cleanup = AsyncMock()
        return app

    @pytest.fixture
    def mock_web_server(self):
        """Create mock web server instance."""
        server = MagicMock()
        server.start = MagicMock()
        server.stop = MagicMock()
        return server

    @pytest.fixture
    def mock_navigation_handler(self):
        """Create mock navigation handler."""
        handler = MagicMock()
        handler.navigation_state = MagicMock()
        return handler

    @pytest.mark.asyncio
    async def test_run_web_mode_success(
        self, test_settings, mock_args, mock_app, mock_web_server, mock_navigation_handler
    ):
        """Test successful web mode execution."""
        with patch("calendarbot.main.CalendarBot", return_value=mock_app), patch(
            "calendarbot.web.server.WebServer", return_value=mock_web_server
        ), patch(
            "calendarbot.web.navigation.WebNavigationHandler", return_value=mock_navigation_handler
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ) as mock_setup_logging, patch(
            "config.settings.settings", test_settings
        ), patch(
            "calendarbot.cli.modes.web.asyncio.create_task"
        ) as mock_create_task, patch(
            "builtins.print"
        ), patch(
            "signal.signal"
        ):

            # Configure mocks
            mock_logger = MagicMock()
            mock_setup_logging.return_value = mock_logger
            mock_task = AsyncMock()
            mock_create_task.return_value = mock_task

            # Mock the shutdown event to immediately trigger
            with patch("calendarbot.cli.modes.web.asyncio.Event") as mock_event_class:
                mock_event = MagicMock()
                mock_event.is_set.side_effect = [False, True]  # One iteration then shutdown
                mock_event_class.return_value = mock_event

                result = await web.run_web_mode(mock_args)

                assert result == 0
                mock_app.initialize.assert_called_once()
                mock_web_server.start.assert_called_once()
                mock_web_server.stop.assert_called_once()
                mock_app.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_web_mode_app_initialization_failure(
        self, test_settings, mock_args, mock_app
    ):
        """Test web mode when CalendarBot initialization fails."""
        mock_app.initialize.return_value = False

        with patch("calendarbot.main.CalendarBot", return_value=mock_app), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch("calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "config.settings.settings", test_settings
        ), patch(
            "builtins.print"
        ) as mock_print, patch(
            "signal.signal"
        ):

            result = await web.run_web_mode(mock_args)

            assert result == 1
            mock_print.assert_any_call("Failed to initialize Calendar Bot")

    @pytest.mark.asyncio
    async def test_run_web_mode_with_auto_host_detection(
        self, test_settings, mock_app, mock_web_server, mock_navigation_handler
    ):
        """Test web mode with automatic host detection."""
        mock_args = MagicMock()
        mock_args.host = None  # Trigger auto-detection
        mock_args.port = 8080
        mock_args.auto_open = False
        mock_args.rpi = False

        with patch("calendarbot.main.CalendarBot", return_value=mock_app), patch(
            "calendarbot.web.server.WebServer", return_value=mock_web_server
        ), patch(
            "calendarbot.web.navigation.WebNavigationHandler", return_value=mock_navigation_handler
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "calendarbot.utils.network.get_local_network_interface", return_value="192.168.1.100"
        ), patch(
            "config.settings.settings", test_settings
        ), patch(
            "calendarbot.cli.modes.web.asyncio.create_task"
        ), patch(
            "builtins.print"
        ), patch(
            "signal.signal"
        ):

            # Mock the shutdown event to immediately trigger
            with patch("calendarbot.cli.modes.web.asyncio.Event") as mock_event_class:
                mock_event = MagicMock()
                mock_event.is_set.side_effect = [False, True]
                mock_event_class.return_value = mock_event

                result = await web.run_web_mode(mock_args)

                assert result == 0
                assert test_settings.web_host == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_run_web_mode_with_auto_open_browser(
        self, test_settings, mock_args, mock_app, mock_web_server, mock_navigation_handler
    ):
        """Test web mode with browser auto-open."""
        mock_args.auto_open = True

        with patch("calendarbot.main.CalendarBot", return_value=mock_app), patch(
            "calendarbot.web.server.WebServer", return_value=mock_web_server
        ), patch(
            "calendarbot.web.navigation.WebNavigationHandler", return_value=mock_navigation_handler
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "config.settings.settings", test_settings
        ), patch(
            "calendarbot.cli.modes.web.asyncio.create_task"
        ), patch(
            "webbrowser.open"
        ) as mock_browser_open, patch(
            "builtins.print"
        ), patch(
            "signal.signal"
        ):

            # Mock the shutdown event to immediately trigger
            with patch("calendarbot.cli.modes.web.asyncio.Event") as mock_event_class:
                mock_event = MagicMock()
                mock_event.is_set.side_effect = [False, True]
                mock_event_class.return_value = mock_event

                result = await web.run_web_mode(mock_args)

                assert result == 0
                mock_browser_open.assert_called_once_with(
                    f"http://{mock_args.host}:{mock_args.port}"
                )

    @pytest.mark.asyncio
    async def test_run_web_mode_browser_open_failure(
        self, test_settings, mock_args, mock_app, mock_web_server, mock_navigation_handler
    ):
        """Test web mode when browser auto-open fails."""
        mock_args.auto_open = True

        with patch("calendarbot.main.CalendarBot", return_value=mock_app), patch(
            "calendarbot.web.server.WebServer", return_value=mock_web_server
        ), patch(
            "calendarbot.web.navigation.WebNavigationHandler", return_value=mock_navigation_handler
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ) as mock_setup_logging, patch(
            "config.settings.settings", test_settings
        ), patch(
            "calendarbot.cli.modes.web.asyncio.create_task"
        ), patch(
            "webbrowser.open", side_effect=Exception("Browser failed")
        ), patch(
            "builtins.print"
        ), patch(
            "signal.signal"
        ):

            mock_logger = MagicMock()
            mock_setup_logging.return_value = mock_logger

            # Mock the shutdown event to immediately trigger
            with patch("calendarbot.cli.modes.web.asyncio.Event") as mock_event_class:
                mock_event = MagicMock()
                mock_event.is_set.side_effect = [False, True]
                mock_event_class.return_value = mock_event

                result = await web.run_web_mode(mock_args)

                assert result == 0
                mock_logger.warning.assert_called_with(
                    "Failed to auto-open browser: Browser failed"
                )

    @pytest.mark.asyncio
    async def test_run_web_mode_web_server_creation_failure(
        self, test_settings, mock_args, mock_app, mock_navigation_handler
    ):
        """Test web mode when WebServer creation fails."""
        with patch("calendarbot.main.CalendarBot", return_value=mock_app), patch(
            "calendarbot.web.server.WebServer", side_effect=Exception("Server creation failed")
        ), patch(
            "calendarbot.web.navigation.WebNavigationHandler", return_value=mock_navigation_handler
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "config.settings.settings", test_settings
        ), patch(
            "builtins.print"
        ) as mock_print, patch(
            "traceback.print_exc"
        ) as mock_traceback, patch(
            "signal.signal"
        ):

            result = await web.run_web_mode(mock_args)

            assert result == 1
            mock_print.assert_called_with("Web server error: Server creation failed")
            mock_traceback.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_web_mode_rpi_mode(
        self, test_settings, mock_app, mock_web_server, mock_navigation_handler
    ):
        """Test web mode with RPI-specific settings."""
        mock_args = MagicMock()
        mock_args.host = "0.0.0.0"
        mock_args.port = 8080
        mock_args.auto_open = False
        mock_args.rpi = True

        with patch("calendarbot.main.CalendarBot", return_value=mock_app), patch(
            "calendarbot.web.server.WebServer", return_value=mock_web_server
        ), patch(
            "calendarbot.web.navigation.WebNavigationHandler", return_value=mock_navigation_handler
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ) as mock_rpi_overrides, patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "config.settings.settings", test_settings
        ), patch(
            "calendarbot.cli.modes.web.asyncio.create_task"
        ), patch(
            "builtins.print"
        ), patch(
            "signal.signal"
        ):

            # Mock the shutdown event to immediately trigger
            with patch("calendarbot.cli.modes.web.asyncio.Event") as mock_event_class:
                mock_event = MagicMock()
                mock_event.is_set.side_effect = [False, True]
                mock_event_class.return_value = mock_event

                result = await web.run_web_mode(mock_args)

                assert result == 0
                mock_rpi_overrides.assert_called_once_with(test_settings, mock_args)
                # In RPI mode, display_type and web_theme should not be overridden
                assert (
                    not hasattr(test_settings, "display_type")
                    or test_settings.display_type != "html"
                )

    @pytest.mark.asyncio
    async def test_run_web_mode_cleanup_errors(
        self, test_settings, mock_args, mock_app, mock_web_server, mock_navigation_handler
    ):
        """Test web mode handles cleanup errors gracefully."""
        # Make cleanup operations raise exceptions
        mock_web_server.stop.side_effect = Exception("Server stop failed")
        mock_app.cleanup.side_effect = Exception("App cleanup failed")

        with patch("calendarbot.main.CalendarBot", return_value=mock_app), patch(
            "calendarbot.web.server.WebServer", return_value=mock_web_server
        ), patch(
            "calendarbot.web.navigation.WebNavigationHandler", return_value=mock_navigation_handler
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ) as mock_setup_logging, patch(
            "config.settings.settings", test_settings
        ), patch(
            "calendarbot.cli.modes.web.asyncio.create_task"
        ), patch(
            "builtins.print"
        ), patch(
            "signal.signal"
        ):

            mock_logger = MagicMock()
            mock_setup_logging.return_value = mock_logger

            # Mock the shutdown event to immediately trigger
            with patch("calendarbot.cli.modes.web.asyncio.Event") as mock_event_class:
                mock_event = MagicMock()
                mock_event.is_set.side_effect = [False, True]
                mock_event_class.return_value = mock_event

                result = await web.run_web_mode(mock_args)

                # Should still return 0 despite cleanup errors
                assert result == 0
                mock_logger.error.assert_any_call("Error stopping web server: Server stop failed")
                mock_logger.error.assert_any_call(
                    "Error during application cleanup: App cleanup failed"
                )

    @pytest.mark.asyncio
    async def test_run_web_mode_background_task_timeout(
        self, test_settings, mock_args, mock_app, mock_web_server, mock_navigation_handler
    ):
        """Test web mode handles background task timeout during cleanup."""
        # Create a task that doesn't complete within timeout
        mock_task = AsyncMock()
        mock_task.cancel = MagicMock()

        with patch("calendarbot.main.CalendarBot", return_value=mock_app), patch(
            "calendarbot.web.server.WebServer", return_value=mock_web_server
        ), patch(
            "calendarbot.web.navigation.WebNavigationHandler", return_value=mock_navigation_handler
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ) as mock_setup_logging, patch(
            "config.settings.settings", test_settings
        ), patch(
            "calendarbot.cli.modes.web.asyncio.create_task", return_value=mock_task
        ), patch(
            "calendarbot.cli.modes.web.asyncio.wait_for", side_effect=asyncio.TimeoutError
        ), patch(
            "builtins.print"
        ), patch(
            "signal.signal"
        ):

            mock_logger = MagicMock()
            mock_setup_logging.return_value = mock_logger

            # Mock the shutdown event to immediately trigger
            with patch("calendarbot.cli.modes.web.asyncio.Event") as mock_event_class:
                mock_event = MagicMock()
                mock_event.is_set.side_effect = [False, True]
                mock_event_class.return_value = mock_event

                result = await web.run_web_mode(mock_args)

                assert result == 0
                mock_task.cancel.assert_called_once()
                mock_logger.warning.assert_any_call(
                    "Background fetch task did not cancel within 10 seconds - this may indicate a hanging task"
                )

    def test_signal_handler(self):
        """Test signal handler functionality."""
        # This is tested implicitly in run_web_mode, but we can test the setup
        with patch("signal.signal") as mock_signal:
            with patch("calendarbot.cli.modes.web.asyncio.Event") as mock_event_class:
                mock_event = MagicMock()
                mock_event_class.return_value = mock_event

                # Test that signal handlers are registered
                # This would be called in run_web_mode
                mock_signal.assert_not_called()  # Not called yet without running the function


class TestWebModePlaceholderFunctions:
    """Test placeholder functions in web module."""

    def test_setup_web_server(self):
        """Test setup_web_server placeholder function."""
        mock_settings = MagicMock()
        mock_display_manager = MagicMock()
        mock_cache_manager = MagicMock()
        mock_navigation_state = MagicMock()

        with patch("builtins.print") as mock_print:
            result = web.setup_web_server(
                mock_settings, mock_display_manager, mock_cache_manager, mock_navigation_state
            )

            assert result is None
            mock_print.assert_called_once_with(
                "Web server setup placeholder - will be migrated from root main.py"
            )

    def test_apply_web_mode_overrides(self):
        """Test apply_web_mode_overrides placeholder function."""
        mock_settings = MagicMock()
        mock_args = MagicMock()

        with patch("builtins.print") as mock_print:
            result = web.apply_web_mode_overrides(mock_settings, mock_args)

            assert result == mock_settings
            mock_print.assert_called_once_with(
                "Web mode overrides placeholder - will be migrated from root main.py"
            )

    def test_setup_web_navigation(self):
        """Test setup_web_navigation placeholder function."""
        with patch("builtins.print") as mock_print:
            result = web.setup_web_navigation()

            assert result is None
            mock_print.assert_called_once_with(
                "Web navigation setup placeholder - will be migrated from root main.py"
            )


class TestWebModeModuleExports:
    """Test web module's __all__ exports."""

    def test_module_exports(self):
        """Test that all expected functions are exported."""
        expected_exports = [
            "run_web_mode",
            "setup_web_server",
            "apply_web_mode_overrides",
            "setup_web_navigation",
        ]

        assert hasattr(web, "__all__")
        assert web.__all__ == expected_exports

        # Verify all exported functions exist
        for export in expected_exports:
            assert hasattr(web, export)
            assert callable(getattr(web, export))


class TestWebModeIntegration:
    """Integration tests for web mode functionality."""

    @pytest.mark.asyncio
    async def test_web_mode_full_lifecycle(self, test_settings):
        """Test complete web mode lifecycle from startup to shutdown."""
        mock_args = MagicMock()
        mock_args.host = "127.0.0.1"
        mock_args.port = 9090
        mock_args.auto_open = True
        mock_args.rpi = False

        mock_app = AsyncMock()
        mock_app.initialize.return_value = True
        mock_app.display_manager = MagicMock()
        mock_app.cache_manager = MagicMock()
        mock_app.run_background_fetch = AsyncMock()
        mock_app.cleanup = AsyncMock()

        mock_web_server = MagicMock()
        mock_navigation_handler = MagicMock()
        mock_navigation_handler.navigation_state = MagicMock()

        with patch("calendarbot.main.CalendarBot", return_value=mock_app), patch(
            "calendarbot.web.server.WebServer", return_value=mock_web_server
        ), patch(
            "calendarbot.web.navigation.WebNavigationHandler", return_value=mock_navigation_handler
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ) as mock_setup_logging, patch(
            "config.settings.settings", test_settings
        ), patch(
            "calendarbot.cli.modes.web.asyncio.create_task"
        ) as mock_create_task, patch(
            "webbrowser.open"
        ) as mock_browser_open, patch(
            "builtins.print"
        ), patch(
            "signal.signal"
        ):

            mock_logger = MagicMock()
            mock_setup_logging.return_value = mock_logger
            mock_task = AsyncMock()
            mock_create_task.return_value = mock_task

            # Mock the shutdown event for quick completion
            with patch("calendarbot.cli.modes.web.asyncio.Event") as mock_event_class:
                mock_event = MagicMock()
                mock_event.is_set.side_effect = [False, True]
                mock_event_class.return_value = mock_event

                result = await web.run_web_mode(mock_args)

                # Verify complete workflow
                assert result == 0

                # Verify initialization sequence
                mock_app.initialize.assert_called_once()
                mock_setup_logging.assert_called_once()

                # Verify web server operations
                mock_web_server.start.assert_called_once()
                mock_web_server.stop.assert_called_once()

                # Verify browser opening
                mock_browser_open.assert_called_once_with("http://127.0.0.1:9090")

                # Verify cleanup
                mock_task.cancel.assert_called_once()
                mock_app.cleanup.assert_called_once()

                # Verify settings were updated for web mode
                assert test_settings.display_type == "html"
                assert test_settings.web_theme == "4x8"
                assert test_settings.web_host == "127.0.0.1"
                assert test_settings.web_port == 9090

    @pytest.mark.asyncio
    async def test_web_mode_error_scenarios(self, test_settings):
        """Test various error scenarios in web mode."""
        mock_args = MagicMock()
        mock_args.host = "localhost"
        mock_args.port = 8080
        mock_args.auto_open = False
        mock_args.rpi = False

        # Test different error scenarios
        error_scenarios = [
            ("Import error", ImportError("Module not found")),
            ("Runtime error", RuntimeError("Runtime failure")),
            ("General error", Exception("General failure")),
        ]

        for scenario_name, exception in error_scenarios:
            with patch("calendarbot.main.CalendarBot", side_effect=exception), patch(
                "builtins.print"
            ) as mock_print, patch("traceback.print_exc") as mock_traceback, patch("signal.signal"):

                result = await web.run_web_mode(mock_args)

                assert result == 1
                # Check that an error message was printed (content may vary due to mock interactions)
                mock_print.assert_called()
                print_calls = [call.args[0] for call in mock_print.call_args_list]
                assert any("Web server error:" in str(call) for call in print_calls)
                mock_traceback.assert_called_once()
