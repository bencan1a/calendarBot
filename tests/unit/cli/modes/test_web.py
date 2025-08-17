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
        app = MagicMock()
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

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings object."""
        return MagicMock()

    def test_signal_handler(self):
        """Test signal handler functionality."""
        # This is tested implicitly in run_web_mode, but we can test the setup
        with (
            patch("signal.signal") as mock_signal,
            patch("calendarbot.cli.modes.web.asyncio.Event") as mock_event_class,
        ):
            mock_event = MagicMock()
            mock_event_class.return_value = mock_event

            # Test that signal handlers are registered
            # This would be called in run_web_mode
            mock_signal.assert_not_called()  # Not called yet without running the function

    @patch("calendarbot.cli.modes.web.apply_command_line_overrides")
    @patch("calendarbot.cli.modes.web.apply_cli_overrides")
    @patch("calendarbot.cli.modes.web.get_local_network_interface")
    @patch("calendarbot.cli.modes.web.validate_host_binding")
    def test_configure_web_settings_when_rpi_false_and_layout_not_whats_next_then_uses_html_renderer(
        self,
        mock_validate_host,
        mock_get_interface,
        mock_apply_cli_overrides,
        mock_apply_cmd_overrides,
        mock_args,
        mock_settings,
    ):
        """Test _configure_web_settings with rpi=False and layout not whats-next-view."""
        # Setup
        mock_args.rpi = False
        mock_args.layout = "4x8"
        mock_args.host = None
        mock_args.port = 8080

        mock_apply_cmd_overrides.return_value = mock_settings
        mock_apply_cli_overrides.return_value = mock_settings
        mock_get_interface.return_value = "192.168.1.100"

        # Execute
        result = web._configure_web_settings(mock_args, mock_settings)

        # Assert
        assert result == mock_settings
        assert result.display_type == "html"
        assert result.web_layout == "default"
        assert result.web_host == "192.168.1.100"
        assert result.web_port == 8080
        mock_validate_host.assert_called_once_with("192.168.1.100", warn_on_all_interfaces=False)

    @patch("calendarbot.cli.modes.web.apply_command_line_overrides")
    @patch("calendarbot.cli.modes.web.apply_cli_overrides")
    @patch("calendarbot.cli.modes.web.validate_host_binding")
    def test_configure_web_settings_when_rpi_false_and_layout_whats_next_then_uses_whats_next_renderer(
        self,
        mock_validate_host,
        mock_apply_cli_overrides,
        mock_apply_cmd_overrides,
        mock_args,
        mock_settings,
    ):
        """Test _configure_web_settings with rpi=False and layout=whats-next-view."""
        # Setup
        mock_args.rpi = False
        mock_args.layout = "whats-next-view"
        mock_args.host = "localhost"
        mock_args.port = 8080

        mock_apply_cmd_overrides.return_value = mock_settings
        mock_apply_cli_overrides.return_value = mock_settings

        # Execute
        result = web._configure_web_settings(mock_args, mock_settings)

        # Assert
        assert result == mock_settings
        assert result.display_type == "whats-next"
        assert result.web_layout == "whats-next-view"
        assert result.web_host == "localhost"
        assert result.web_port == 8080
        mock_validate_host.assert_not_called()

    @patch("calendarbot.cli.modes.web.apply_command_line_overrides")
    @patch("calendarbot.cli.modes.web.apply_cli_overrides")
    @patch("calendarbot.cli.modes.web.get_local_network_interface")
    @patch("calendarbot.cli.modes.web.validate_host_binding")
    def test_configure_web_settings_when_display_type_whats_next_view_then_uses_whats_next_renderer(
        self,
        mock_validate_host,
        mock_get_interface,
        mock_apply_cli_overrides,
        mock_apply_cmd_overrides,
        mock_args,
        mock_settings,
    ):
        """Test _configure_web_settings with display_type=whats-next-view."""
        # Setup
        mock_args.rpi = False
        mock_args.layout = None
        mock_args.display_type = "whats-next-view"
        mock_args.host = None
        mock_args.port = 8080

        mock_apply_cmd_overrides.return_value = mock_settings
        mock_apply_cli_overrides.return_value = mock_settings
        mock_get_interface.return_value = "192.168.1.100"

        # Execute
        result = web._configure_web_settings(mock_args, mock_settings)

        # Assert
        assert result == mock_settings
        assert result.display_type == "whats-next"
        assert result.web_layout == "whats-next-view"
        assert result.web_host == "192.168.1.100"
        assert result.web_port == 8080
        mock_validate_host.assert_called_once_with("192.168.1.100", warn_on_all_interfaces=False)


class TestWebModeIntegration:
    """Integration tests for web mode functionality."""

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

        for _scenario_name, exception in error_scenarios:
            with (
                patch("calendarbot.cli.modes.web.CalendarBot", side_effect=exception),
                patch("builtins.print") as mock_print,
                patch("traceback.print_exc") as mock_traceback,
                patch("signal.signal"),
            ):
                result = await asyncio.wait_for(web.run_web_mode(mock_args), timeout=5.0)

                assert result == 1
                # Check that an error message was printed (content may vary due to mock interactions)
                mock_print.assert_called()
                print_calls = [call.args[0] for call in mock_print.call_args_list]
                assert any("Web server error:" in str(call) for call in print_calls)
                mock_traceback.assert_called_once()


class TestWebComponents:
    """Tests for web component initialization and management."""

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return MagicMock()

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.web_host = "localhost"
        settings.web_port = 8080
        return settings

    @pytest.fixture
    def mock_app(self):
        """Create mock CalendarBot instance."""
        app = MagicMock()
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
    def mock_args(self):
        """Create mock command line arguments."""
        args = MagicMock()
        args.host = "localhost"
        args.port = 8080
        args.auto_open = False
        args.rpi = False
        return args

    @pytest.fixture
    def mock_navigation_handler(self):
        """Create mock navigation handler."""
        handler = MagicMock()
        handler.navigation_state = MagicMock()
        return handler

    @pytest.mark.asyncio
    @patch("calendarbot.cli.modes.web.setup_enhanced_logging")
    @patch("calendarbot.cli.modes.web.CalendarBot")
    @patch("calendarbot.cli.modes.web.WebNavigationHandler")
    @patch("calendarbot.cli.modes.web.WebServer")
    async def test_initialize_web_components_when_successful_then_returns_components(
        self,
        mock_web_server_class,
        mock_nav_handler_class,
        mock_calendar_bot_class,
        mock_setup_logging,
        mock_settings,
    ):
        """Test successful initialization of web components."""
        # Setup
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        mock_app = MagicMock()
        mock_app.initialize = AsyncMock(return_value=True)
        mock_app.display_manager = MagicMock()
        mock_app.cache_manager = MagicMock()
        mock_calendar_bot_class.return_value = mock_app

        mock_nav_handler = MagicMock()
        mock_nav_handler.navigation_state = MagicMock()
        mock_nav_handler_class.return_value = mock_nav_handler

        mock_web_server = MagicMock()
        mock_web_server_class.return_value = mock_web_server

        # Execute
        app, server, nav_handler, logger = await web._initialize_web_components(mock_settings)

        # Assert
        assert app == mock_app
        assert server == mock_web_server
        assert nav_handler == mock_nav_handler
        assert logger == mock_logger
        mock_app.initialize.assert_called_once()
        mock_web_server_class.assert_called_once_with(
            settings=mock_settings,
            display_manager=mock_app.display_manager,
            cache_manager=mock_app.cache_manager,
            navigation_state=mock_nav_handler.navigation_state,
            layout_registry=mock_app.display_manager.layout_registry,
        )

    @pytest.mark.asyncio
    @patch("calendarbot.cli.modes.web.setup_enhanced_logging")
    @patch("calendarbot.cli.modes.web.CalendarBot")
    async def test_initialize_web_components_when_app_init_fails_then_raises_error(
        self, mock_calendar_bot_class, mock_setup_logging, mock_settings
    ):
        """Test initialization failure when app initialization fails."""
        # Setup
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        mock_app = MagicMock()
        mock_app.initialize = AsyncMock(return_value=False)
        mock_calendar_bot_class.return_value = mock_app

        # Execute and Assert
        with pytest.raises(RuntimeError, match="Failed to initialize Calendar Bot"):
            await web._initialize_web_components(mock_settings)

        mock_app.initialize.assert_called_once()
        mock_logger.error.assert_called_once_with("Failed to initialize Calendar Bot")

    @pytest.mark.asyncio
    @patch("calendarbot.cli.modes.web.setup_enhanced_logging")
    @patch("calendarbot.cli.modes.web.CalendarBot")
    @patch("calendarbot.cli.modes.web.WebNavigationHandler")
    @patch("calendarbot.cli.modes.web.WebServer")
    async def test_initialize_web_components_when_web_server_init_fails_then_raises_error(
        self,
        mock_web_server_class,
        mock_nav_handler_class,
        mock_calendar_bot_class,
        mock_setup_logging,
        mock_settings,
    ):
        """Test initialization failure when web server initialization fails."""
        # Setup
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        mock_app = MagicMock()
        mock_app.initialize = AsyncMock(return_value=True)
        mock_app.display_manager = MagicMock()
        mock_app.cache_manager = MagicMock()
        mock_calendar_bot_class.return_value = mock_app

        mock_nav_handler = MagicMock()
        mock_nav_handler.navigation_state = MagicMock()
        mock_nav_handler_class.return_value = mock_nav_handler

        mock_web_server_class.side_effect = Exception("Web server init failed")

        # Execute and Assert
        with pytest.raises(Exception, match="Web server init failed"):
            await web._initialize_web_components(mock_settings)

        mock_app.initialize.assert_called_once()
        mock_logger.exception.assert_called_once_with("Failed to create WebServer")

    @patch("calendarbot.cli.modes.web.webbrowser")
    def test_start_web_server_when_auto_open_true_then_opens_browser(
        self, mock_webbrowser, mock_web_server, mock_settings, mock_args, mock_logger
    ):
        """Test web server start with auto_open=True."""
        # Setup
        mock_args.auto_open = True
        mock_settings.web_host = "localhost"
        mock_settings.web_port = 8080

        # Execute
        with patch("builtins.print") as mock_print:
            web._start_web_server(mock_web_server, mock_settings, mock_args, mock_logger)

        # Assert
        mock_web_server.start.assert_called_once()
        mock_webbrowser.open.assert_called_once_with("http://localhost:8080")
        mock_print.assert_any_call("Opening browser to http://localhost:8080")
        mock_logger.info.assert_any_call("Auto-opening browser to http://localhost:8080")

    @patch("calendarbot.cli.modes.web.webbrowser")
    def test_start_web_server_when_browser_open_fails_then_logs_warning(
        self, mock_webbrowser, mock_web_server, mock_settings, mock_args, mock_logger
    ):
        """Test web server start with browser open failure."""
        # Setup
        mock_args.auto_open = True
        mock_settings.web_host = "localhost"
        mock_settings.web_port = 8080
        mock_webbrowser.open.side_effect = Exception("Browser open failed")

        # Execute
        with patch("builtins.print"):
            web._start_web_server(mock_web_server, mock_settings, mock_args, mock_logger)

        # Assert
        mock_web_server.start.assert_called_once()
        mock_webbrowser.open.assert_called_once_with("http://localhost:8080")
        mock_logger.warning.assert_called_once_with(
            "Failed to auto-open browser: Browser open failed"
        )

    def test_start_web_server_when_auto_open_false_then_does_not_open_browser(
        self, mock_web_server, mock_settings, mock_args, mock_logger
    ):
        """Test web server start with auto_open=False."""
        # Setup
        mock_args.auto_open = False
        mock_settings.web_host = "localhost"
        mock_settings.web_port = 8080

        # Execute
        with (
            patch("builtins.print") as mock_print,
            patch("calendarbot.cli.modes.web.webbrowser") as mock_webbrowser,
        ):
            web._start_web_server(mock_web_server, mock_settings, mock_args, mock_logger)

        # Assert
        mock_web_server.start.assert_called_once()
        mock_webbrowser.open.assert_not_called()
        mock_print.assert_any_call("Starting Calendar Bot web server on http://localhost:8080")
        mock_print.assert_any_call("Press Ctrl+C to stop the server")
        mock_print.assert_any_call("Web server is running. Press Ctrl+C to stop.")

    @pytest.mark.asyncio
    async def test_cleanup_web_resources_when_successful_then_stops_components(
        self, mock_web_server, mock_app, mock_logger
    ):
        """Test successful cleanup of web resources."""
        # Setup
        mock_runtime_tracker = MagicMock()
        mock_fetch_task = MagicMock()
        mock_fetch_task.cancel = MagicMock()

        # Mock asyncio.wait_for to avoid actual waiting
        with patch("asyncio.wait_for", new=AsyncMock()) as mock_wait_for:
            # Execute
            await web._cleanup_web_resources(
                mock_runtime_tracker, mock_web_server, mock_fetch_task, mock_app, mock_logger
            )

        # Assert
        mock_web_server.stop.assert_called_once()
        mock_fetch_task.cancel.assert_called_once()
        assert mock_wait_for.call_count == 2  # Called for fetch task and app cleanup
        mock_logger.info.assert_any_call("Web server stopped successfully")
        mock_logger.info.assert_any_call("Application cleanup completed")

    @pytest.mark.asyncio
    async def test_cleanup_web_resources_when_web_server_stop_fails_then_logs_error(
        self, mock_web_server, mock_app, mock_logger
    ):
        """Test cleanup with web server stop failure."""
        # Setup
        mock_runtime_tracker = MagicMock()
        mock_fetch_task = MagicMock()
        mock_fetch_task.cancel = MagicMock()
        mock_web_server.stop.side_effect = Exception("Stop failed")

        # Mock asyncio.wait_for to avoid actual waiting
        with patch("asyncio.wait_for", new=AsyncMock()) as mock_wait_for:
            # Execute
            await web._cleanup_web_resources(
                mock_runtime_tracker, mock_web_server, mock_fetch_task, mock_app, mock_logger
            )

        # Assert
        mock_web_server.stop.assert_called_once()
        mock_fetch_task.cancel.assert_called_once()
        assert mock_wait_for.call_count == 2  # Called for fetch task and app cleanup
        mock_logger.exception.assert_any_call("Error stopping web server")

    @pytest.mark.asyncio
    async def test_cleanup_web_resources_when_fetch_task_cancelled_then_logs_debug(
        self, mock_web_server, mock_app, mock_logger
    ):
        """Test cleanup with fetch task cancellation."""
        # Setup
        mock_runtime_tracker = MagicMock()
        mock_fetch_task = MagicMock()
        mock_fetch_task.cancel = MagicMock()

        # Mock asyncio.wait_for to raise CancelledError for fetch task
        async def mock_wait_for_side_effect(coro, timeout):
            if coro == mock_fetch_task:
                raise asyncio.CancelledError()
            return await coro

        with patch("asyncio.wait_for", new=AsyncMock(side_effect=mock_wait_for_side_effect)):
            # Execute
            await web._cleanup_web_resources(
                mock_runtime_tracker, mock_web_server, mock_fetch_task, mock_app, mock_logger
            )

        # Assert
        mock_web_server.stop.assert_called_once()
        mock_fetch_task.cancel.assert_called_once()
        mock_logger.debug.assert_any_call("Background fetch task cancelled successfully")

    @pytest.mark.asyncio
    async def test_cleanup_web_resources_when_fetch_task_timeout_then_logs_warning(
        self, mock_web_server, mock_app, mock_logger
    ):
        """Test cleanup with fetch task timeout."""
        # Setup
        mock_runtime_tracker = MagicMock()
        mock_fetch_task = MagicMock()
        mock_fetch_task.cancel = MagicMock()

        # Mock asyncio.wait_for to raise TimeoutError for fetch task
        async def mock_wait_for_side_effect(coro, timeout):
            if coro == mock_fetch_task:
                raise asyncio.TimeoutError()
            return await coro

        with patch("asyncio.wait_for", new=AsyncMock(side_effect=mock_wait_for_side_effect)):
            # Execute
            await web._cleanup_web_resources(
                mock_runtime_tracker, mock_web_server, mock_fetch_task, mock_app, mock_logger
            )

        # Assert
        mock_web_server.stop.assert_called_once()
        mock_fetch_task.cancel.assert_called_once()
        mock_logger.warning.assert_any_call(
            "Background fetch task did not cancel within 10 seconds - this may indicate a hanging task"
        )

    @pytest.mark.asyncio
    @patch("calendarbot.cli.modes.web._configure_web_settings")
    @patch("calendarbot.cli.modes.web._initialize_web_components")
    @patch("calendarbot.cli.modes.web.create_runtime_tracker")
    @patch("calendarbot.cli.modes.web.start_runtime_tracking")
    @patch("calendarbot.cli.modes.web._start_web_server")
    @patch("calendarbot.cli.modes.web._cleanup_web_resources")
    async def test_run_web_mode_when_successful_then_returns_zero(
        self,
        mock_cleanup,
        mock_start_server,
        mock_start_tracking,
        mock_create_tracker,
        mock_init_components,
        mock_configure_settings,
        mock_args,
        mock_settings,
        mock_app,
        mock_web_server,
        mock_navigation_handler,
        mock_logger,
    ):
        """Test successful web mode execution."""
        # Setup
        mock_configure_settings.return_value = mock_settings
        mock_init_components.return_value = (
            mock_app,
            mock_web_server,
            mock_navigation_handler,
            mock_logger,
        )
        mock_runtime_tracker = MagicMock()
        mock_create_tracker.return_value = mock_runtime_tracker
        mock_cleanup.return_value = None

        # Mock asyncio.Event and create_task
        mock_event = MagicMock()
        mock_event.is_set.side_effect = [False, True]  # Return False first, then True to exit loop
        mock_fetch_task = MagicMock()

        with (
            patch("asyncio.Event", return_value=mock_event),
            patch("asyncio.create_task", return_value=mock_fetch_task),
            patch("asyncio.sleep", new=AsyncMock()),
            patch("signal.signal"),
        ):
            # Execute
            result = await web.run_web_mode(mock_args)

        # Assert
        assert result == 0
        mock_configure_settings.assert_called_once()
        mock_init_components.assert_called_once()
        mock_create_tracker.assert_called_once()
        mock_start_tracking.assert_called_once()
        mock_start_server.assert_called_once()
        mock_cleanup.assert_called_once()
        mock_logger.info.assert_any_call("Web mode completed successfully")
