"""Unit tests for web server and API endpoints."""

import json
import threading
import time
from datetime import date, datetime
from http.server import HTTPServer
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from calendarbot.ui.navigation import NavigationState
from calendarbot.web.server import WebRequestHandler, WebServer
from tests.fixtures.mock_ics_data import WebAPITestData


@pytest_asyncio.fixture
async def mock_request_handler(test_settings, cache_manager):
    """Create mock request handler for API testing."""
    display_manager = MagicMock()
    navigation_state = NavigationState()
    web_server = WebServer(test_settings, display_manager, cache_manager, navigation_state)

    # Mock the base class initialization
    with patch("calendarbot.web.server.BaseHTTPRequestHandler.__init__"):
        handler = WebRequestHandler(None, None, None, web_server=web_server)

        # Mock HTTP response methods
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = MagicMock()
        handler.client_address = ("127.0.0.1", 12345)

        yield handler


@pytest_asyncio.fixture
async def web_server_with_mock_renderer(test_settings, cache_manager):
    """Create web server with mock renderer."""
    display_manager = MagicMock()
    display_manager.renderer = MagicMock()
    display_manager.renderer.render_events.return_value = "<html><body>Test Calendar</body></html>"
    server = WebServer(test_settings, display_manager, cache_manager)
    yield server


@pytest.mark.unit
class TestWebServerInitialization:
    """Test suite for web server initialization."""

    def test_web_server_creation(self, test_settings, cache_manager):
        """Test web server creation with required dependencies."""
        display_manager = MagicMock()

        web_server = WebServer(test_settings, display_manager, cache_manager)

        assert web_server.settings == test_settings
        assert web_server.display_manager == display_manager
        assert web_server.cache_manager == cache_manager
        assert web_server.navigation_state is None
        assert web_server.host == test_settings.web_host
        assert web_server.port == test_settings.web_port
        assert web_server.theme == test_settings.web_theme
        assert web_server.running is False

    def test_web_server_creation_with_navigation_state(self, test_settings, cache_manager):
        """Test web server creation with navigation state for interactive mode."""
        display_manager = MagicMock()
        navigation_state = NavigationState()

        web_server = WebServer(test_settings, display_manager, cache_manager, navigation_state)

        assert web_server.navigation_state == navigation_state

    def test_web_server_configuration_from_settings(self, test_settings, cache_manager):
        """Test that web server uses settings for configuration."""
        test_settings.web_host = "0.0.0.0"
        test_settings.web_port = 9000
        test_settings.web_theme = "eink"

        display_manager = MagicMock()
        web_server = WebServer(test_settings, display_manager, cache_manager)

        assert web_server.host == "0.0.0.0"
        assert web_server.port == 9000
        assert web_server.theme == "eink"


@pytest.mark.unit
class TestWebServerLifecycle:
    """Test suite for web server start/stop lifecycle."""

    @pytest_asyncio.fixture
    async def web_server(self, test_settings, cache_manager):
        """Create a web server for testing."""
        display_manager = MagicMock()
        server = WebServer(test_settings, display_manager, cache_manager)
        yield server
        if server.running:
            server.stop()

    def test_web_server_start(self, web_server):
        """Test web server start process."""
        with patch("calendarbot.web.server.HTTPServer") as mock_http_server, patch(
            "calendarbot.web.server.Thread"
        ) as mock_thread:

            mock_server_instance = MagicMock()
            mock_http_server.return_value = mock_server_instance
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            web_server.start()

            assert web_server.running is True
            mock_http_server.assert_called_once()
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()

    def test_web_server_start_already_running(self, web_server):
        """Test starting web server when already running."""
        web_server.running = True

        with patch("calendarbot.web.server.logger") as mock_logger:
            web_server.start()
            mock_logger.warning.assert_called_with("Web server already running")

    def test_web_server_start_with_auto_cleanup(self, web_server):
        """Test web server start with auto cleanup enabled."""
        web_server.settings.auto_kill_existing = True

        with patch("calendarbot.web.server.auto_cleanup_before_start") as mock_cleanup, patch(
            "calendarbot.web.server.HTTPServer"
        ), patch("threading.Thread"):

            mock_cleanup.return_value = True

            web_server.start()

            mock_cleanup.assert_called_once_with(web_server.host, web_server.port, force=True)

    def test_web_server_start_cleanup_failure(self, web_server):
        """Test web server start when cleanup fails."""
        web_server.settings.auto_kill_existing = True

        with patch("calendarbot.web.server.auto_cleanup_before_start") as mock_cleanup, patch(
            "calendarbot.web.server.HTTPServer"
        ), patch("threading.Thread"), patch("calendarbot.web.server.logger") as mock_logger:

            mock_cleanup.return_value = False

            web_server.start()

            mock_logger.warning.assert_called()

    def test_web_server_stop(self, web_server):
        """Test web server stop process."""
        # Set up running state
        mock_server = MagicMock()
        mock_thread = MagicMock()
        web_server.server = mock_server
        web_server.server_thread = mock_thread
        web_server.running = True

        web_server.stop()

        assert web_server.running is False
        mock_server.shutdown.assert_called_once()
        mock_server.server_close.assert_called_once()
        mock_thread.join.assert_called_once_with(timeout=5)

    def test_web_server_stop_not_running(self, web_server):
        """Test stopping web server when not running."""
        web_server.stop()  # Should not raise exception

    def test_web_server_stop_with_error(self, web_server):
        """Test web server stop with error during shutdown."""
        mock_server = MagicMock()
        mock_server.shutdown.side_effect = Exception("Shutdown error")
        web_server.server = mock_server
        web_server.running = True

        with patch("calendarbot.web.server.logger") as mock_logger:
            web_server.stop()
            mock_logger.error.assert_called()

    def test_web_server_url_property(self, web_server):
        """Test web server URL property."""
        assert web_server.url == f"http://{web_server.host}:{web_server.port}"


@pytest.mark.unit
class TestNavigationAPI:
    """Test suite for navigation API endpoint."""

    @pytest_asyncio.fixture
    async def web_server_with_navigation(self, test_settings, cache_manager):
        """Create web server with navigation state."""
        display_manager = MagicMock()
        navigation_state = NavigationState()
        server = WebServer(test_settings, display_manager, cache_manager, navigation_state)
        yield server

    def test_handle_navigation_prev(self, web_server_with_navigation):
        """Test navigation previous day action."""
        with patch.object(
            web_server_with_navigation.navigation_state, "navigate_backward"
        ) as mock_nav:
            success = web_server_with_navigation.handle_navigation("prev")

            assert success is True
            mock_nav.assert_called_once()

    def test_handle_navigation_next(self, web_server_with_navigation):
        """Test navigation next day action."""
        with patch.object(
            web_server_with_navigation.navigation_state, "navigate_forward"
        ) as mock_nav:
            success = web_server_with_navigation.handle_navigation("next")

            assert success is True
            mock_nav.assert_called_once()

    def test_handle_navigation_today(self, web_server_with_navigation):
        """Test navigation to today action."""
        with patch.object(web_server_with_navigation.navigation_state, "jump_to_today") as mock_nav:
            success = web_server_with_navigation.handle_navigation("today")

            assert success is True
            mock_nav.assert_called_once()

    def test_handle_navigation_week_start(self, web_server_with_navigation):
        """Test navigation to week start action."""
        with patch.object(
            web_server_with_navigation.navigation_state, "jump_to_start_of_week"
        ) as mock_nav:
            success = web_server_with_navigation.handle_navigation("week-start")

            assert success is True
            mock_nav.assert_called_once()

    def test_handle_navigation_week_end(self, web_server_with_navigation):
        """Test navigation to week end action."""
        with patch.object(
            web_server_with_navigation.navigation_state, "jump_to_end_of_week"
        ) as mock_nav:
            success = web_server_with_navigation.handle_navigation("week-end")

            assert success is True
            mock_nav.assert_called_once()

    def test_handle_navigation_invalid_action(self, web_server_with_navigation):
        """Test navigation with invalid action."""
        with patch("calendarbot.web.server.logger") as mock_logger:
            success = web_server_with_navigation.handle_navigation("invalid")

            assert success is False
            mock_logger.warning.assert_called()

    def test_handle_navigation_without_navigation_state(self, test_settings, cache_manager):
        """Test navigation when no navigation state is available."""
        display_manager = MagicMock()
        server = WebServer(test_settings, display_manager, cache_manager)

        with patch("calendarbot.web.server.logger") as mock_logger:
            success = server.handle_navigation("next")

            assert success is False
            mock_logger.warning.assert_called()

    def test_handle_navigation_with_exception(self, web_server_with_navigation):
        """Test navigation with exception during action."""
        with patch.object(
            web_server_with_navigation.navigation_state,
            "navigate_forward",
            side_effect=Exception("Navigation error"),
        ), patch("calendarbot.web.server.logger") as mock_logger:

            success = web_server_with_navigation.handle_navigation("next")

            assert success is False
            mock_logger.error.assert_called()


@pytest.mark.unit
class TestThemeAPI:
    """Test suite for theme API endpoint."""

    @pytest_asyncio.fixture
    async def web_server_with_display(self, test_settings, cache_manager):
        """Create web server with mock display manager."""
        display_manager = MagicMock()
        display_manager.renderer = MagicMock()
        server = WebServer(test_settings, display_manager, cache_manager)
        yield server

    def test_set_theme_valid(self, web_server_with_display):
        """Test setting valid theme."""
        success = web_server_with_display.set_theme("eink")

        assert success is True
        assert web_server_with_display.theme == "eink"
        assert web_server_with_display.display_manager.renderer.theme == "eink"

    def test_set_theme_standard(self, web_server_with_display):
        """Test setting standard theme."""
        success = web_server_with_display.set_theme("standard")

        assert success is True
        assert web_server_with_display.theme == "standard"

    def test_set_theme_eink_rpi(self, web_server_with_display):
        """Test setting eink-rpi theme."""
        success = web_server_with_display.set_theme("eink-rpi")

        assert success is True
        assert web_server_with_display.theme == "eink-rpi"

    def test_set_theme_invalid(self, web_server_with_display):
        """Test setting invalid theme."""
        with patch("calendarbot.web.server.logger") as mock_logger:
            success = web_server_with_display.set_theme("invalid-theme")

            assert success is False
            mock_logger.warning.assert_called()

    def test_set_theme_without_renderer_theme_attribute(self, test_settings, cache_manager):
        """Test setting theme when renderer doesn't have theme attribute."""
        display_manager = MagicMock()
        display_manager.renderer = MagicMock(spec=[])  # No theme attribute
        server = WebServer(test_settings, display_manager, cache_manager)

        success = server.set_theme("eink")

        assert success is True
        assert server.theme == "eink"

    def test_toggle_theme_eink_to_standard(self, web_server_with_display):
        """Test toggling theme from eink to standard."""
        web_server_with_display.theme = "eink"

        new_theme = web_server_with_display.toggle_theme()

        assert new_theme == "standard"
        assert web_server_with_display.theme == "standard"

    def test_toggle_theme_standard_to_eink_rpi(self, web_server_with_display):
        """Test toggling theme from standard to eink-rpi."""
        web_server_with_display.theme = "standard"

        new_theme = web_server_with_display.toggle_theme()

        assert new_theme == "eink-rpi"
        assert web_server_with_display.theme == "eink-rpi"

    def test_toggle_theme_eink_rpi_to_eink(self, web_server_with_display):
        """Test toggling theme from eink-rpi to eink."""
        web_server_with_display.theme = "eink-rpi"

        new_theme = web_server_with_display.toggle_theme()

        assert new_theme == "eink"
        assert web_server_with_display.theme == "eink"

    def test_toggle_theme_unknown_to_eink(self, web_server_with_display):
        """Test toggling from unknown theme defaults to eink."""
        web_server_with_display.theme = "unknown"

        new_theme = web_server_with_display.toggle_theme()

        assert new_theme == "eink"
        assert web_server_with_display.theme == "eink"


@pytest.mark.unit
class TestRefreshAPI:
    """Test suite for refresh API endpoint."""

    @pytest_asyncio.fixture
    async def web_server_for_refresh(self, test_settings, cache_manager):
        """Create web server for refresh testing."""
        display_manager = MagicMock()
        server = WebServer(test_settings, display_manager, cache_manager)
        yield server

    def test_refresh_data_success(self, web_server_for_refresh):
        """Test successful data refresh."""
        success = web_server_for_refresh.refresh_data()

        assert success is True

    def test_refresh_data_with_exception(self, web_server_for_refresh):
        """Test data refresh with exception."""
        with patch("calendarbot.web.server.logger") as mock_logger:
            # Mock an exception during refresh
            with patch.object(
                web_server_for_refresh, "refresh_data", side_effect=Exception("Refresh error")
            ):
                try:
                    web_server_for_refresh.refresh_data()
                except Exception:
                    pass  # Expected


@pytest.mark.unit
class TestStatusAPI:
    """Test suite for status API endpoint."""

    def test_get_status_without_navigation(self, test_settings, cache_manager):
        """Test getting status without navigation state."""
        display_manager = MagicMock()
        server = WebServer(test_settings, display_manager, cache_manager)

        status = server.get_status()

        expected_status = {
            "running": False,
            "host": test_settings.web_host,
            "port": test_settings.web_port,
            "theme": test_settings.web_theme,
            "interactive_mode": False,
            "current_date": date.today().isoformat(),
        }

        assert status == expected_status

    def test_get_status_with_navigation(self, test_settings, cache_manager):
        """Test getting status with navigation state."""
        display_manager = MagicMock()
        navigation_state = NavigationState()
        server = WebServer(test_settings, display_manager, cache_manager, navigation_state)
        server.running = True

        status = server.get_status()

        assert status["running"] is True
        assert status["interactive_mode"] is True
        assert status["current_date"] == navigation_state.selected_date.isoformat()


@pytest.mark.unit
class TestCalendarHTML:
    """Test suite for calendar HTML generation."""

    def test_get_calendar_html_without_navigation(self, web_server_with_mock_renderer):
        """Test getting calendar HTML without navigation state."""
        with patch("asyncio.run") as mock_run:
            mock_run.return_value = []  # Empty events

            html = web_server_with_mock_renderer.get_calendar_html()

            assert html == "<html><body>Test Calendar</body></html>"
            web_server_with_mock_renderer.display_manager.renderer.render_events.assert_called_once()

    def test_get_calendar_html_with_navigation(self, test_settings, cache_manager):
        """Test getting calendar HTML with navigation state."""
        display_manager = MagicMock()
        display_manager.renderer = MagicMock()
        display_manager.renderer.render_events.return_value = (
            "<html><body>Interactive Calendar</body></html>"
        )

        navigation_state = NavigationState()
        server = WebServer(test_settings, display_manager, cache_manager, navigation_state)

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = []  # Empty events

            html = server.get_calendar_html()

            assert html == "<html><body>Interactive Calendar</body></html>"

    def test_get_calendar_html_with_events(self, web_server_with_mock_renderer):
        """Test getting calendar HTML with events."""
        mock_events = [MagicMock(), MagicMock()]

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = mock_events

            html = web_server_with_mock_renderer.get_calendar_html()

            # Verify render_events was called with events and status info
            call_args = (
                web_server_with_mock_renderer.display_manager.renderer.render_events.call_args
            )
            events_arg = call_args[0][0]
            status_arg = call_args[0][1]

            assert events_arg == mock_events
            assert isinstance(status_arg, dict)
            assert "last_update" in status_arg
            assert "is_cached" in status_arg

    def test_get_calendar_html_without_render_method(self, test_settings, cache_manager):
        """Test getting calendar HTML when renderer doesn't have render_events method."""
        display_manager = MagicMock()
        display_manager.renderer = MagicMock(spec=[])  # No render_events method
        server = WebServer(test_settings, display_manager, cache_manager)

        with patch("calendarbot.web.server.logger") as mock_logger:
            html = server.get_calendar_html()

            assert "Error: HTML renderer not available" in html
            mock_logger.error.assert_called()

    def test_get_calendar_html_with_exception(self, web_server_with_mock_renderer):
        """Test getting calendar HTML with exception during generation."""
        with patch("asyncio.run", side_effect=Exception("HTML generation error")), patch(
            "calendarbot.web.server.logger"
        ) as mock_logger:

            html = web_server_with_mock_renderer.get_calendar_html()

            assert "Error" in html
            assert "HTML generation error" in html
            mock_logger.error.assert_called()


@pytest.mark.unit
class TestWebRequestHandler:
    """Test suite for web request handler."""

    def test_request_handler_initialization(self, test_settings, cache_manager):
        """Test web request handler initialization."""
        display_manager = MagicMock()
        web_server = WebServer(test_settings, display_manager, cache_manager)

        # Mock the request handler initialization
        with patch("calendarbot.web.server.BaseHTTPRequestHandler.__init__"):
            handler = WebRequestHandler(None, None, None, web_server=web_server)

            assert handler.web_server == web_server
            assert handler.security_logger is not None

    def test_request_handler_logging_disabled(self):
        """Test that request handler logging is disabled."""
        with patch("calendarbot.web.server.BaseHTTPRequestHandler.__init__"):
            handler = WebRequestHandler(None, None, None)

            # log_message should be overridden to suppress output
            with patch("calendarbot.web.server.logger") as mock_logger:
                handler.log_message("Test message %s", "arg")
                mock_logger.debug.assert_called_with("HTTP Test message arg")


@pytest.mark.unit
class TestAPIEndpointIntegration:
    """Integration tests for API endpoints with request handler."""

    def test_handle_navigation_api_valid_action(self, mock_request_handler):
        """Test handling valid navigation API request."""
        params = {"action": ["next"]}

        with patch.object(
            mock_request_handler.web_server, "handle_navigation", return_value=True
        ), patch.object(
            mock_request_handler.web_server, "get_calendar_html", return_value="<html>Test</html>"
        ):

            mock_request_handler._handle_navigation_api(params)

            mock_request_handler.send_response.assert_called_with(200)

    def test_handle_navigation_api_invalid_action(self, mock_request_handler):
        """Test handling invalid navigation API request."""
        params = {"action": ["invalid"]}

        with patch.object(
            mock_request_handler.security_logger, "log_input_validation_failure"
        ) as mock_log:
            mock_request_handler._handle_navigation_api(params)

            mock_request_handler.send_response.assert_called_with(400)
            mock_log.assert_called_once()

    def test_handle_navigation_api_missing_action(self, mock_request_handler):
        """Test handling navigation API request with missing action."""
        params = {}

        with patch.object(
            mock_request_handler.security_logger, "log_input_validation_failure"
        ) as mock_log:
            mock_request_handler._handle_navigation_api(params)

            mock_request_handler.send_response.assert_called_with(400)
            mock_log.assert_called_once()

    def test_handle_theme_api_with_theme(self, mock_request_handler):
        """Test handling theme API request with specific theme."""
        params = {"theme": ["eink"]}

        with patch.object(mock_request_handler.web_server, "set_theme", return_value=True):
            mock_request_handler._handle_theme_api(params)

            mock_request_handler.send_response.assert_called_with(200)

    def test_handle_theme_api_toggle(self, mock_request_handler):
        """Test handling theme API request for toggle."""
        params = {}

        with patch.object(mock_request_handler.web_server, "toggle_theme", return_value="standard"):
            mock_request_handler._handle_theme_api(params)

            mock_request_handler.send_response.assert_called_with(200)

    def test_handle_refresh_api(self, mock_request_handler):
        """Test handling refresh API request."""
        with patch.object(
            mock_request_handler.web_server, "refresh_data", return_value=True
        ), patch.object(
            mock_request_handler.web_server,
            "get_calendar_html",
            return_value="<html>Refreshed</html>",
        ):

            mock_request_handler._handle_refresh_api()

            mock_request_handler.send_response.assert_called_with(200)

    def test_handle_status_api(self, mock_request_handler):
        """Test handling status API request."""
        expected_status = {"running": True, "host": "127.0.0.1", "port": 8998}

        with patch.object(
            mock_request_handler.web_server, "get_status", return_value=expected_status
        ):
            mock_request_handler._handle_status_api()

            mock_request_handler.send_response.assert_called_with(200)


@pytest.mark.unit
class TestSecurityValidation:
    """Test suite for security validation in web endpoints."""

    @pytest_asyncio.fixture
    async def handler_for_security_test(self, test_settings, cache_manager):
        """Create request handler for security testing."""
        display_manager = MagicMock()
        web_server = WebServer(test_settings, display_manager, cache_manager)

        with patch("calendarbot.web.server.BaseHTTPRequestHandler.__init__"):
            handler = WebRequestHandler(None, None, None, web_server=web_server)
            handler.client_address = ("192.168.1.100", 12345)
            handler.send_response = MagicMock()
            handler.send_header = MagicMock()
            handler.end_headers = MagicMock()
            handler.wfile = MagicMock()

            yield handler

    def test_navigation_action_validation_valid_actions(self, handler_for_security_test):
        """Test that valid navigation actions are accepted."""
        valid_actions = ["prev", "next", "today", "week-start", "week-end"]

        for action in valid_actions:
            params = {"action": [action]}

            with patch.object(
                handler_for_security_test.web_server, "handle_navigation", return_value=True
            ), patch.object(
                handler_for_security_test.web_server,
                "get_calendar_html",
                return_value="<html>Test</html>",
            ):

                handler_for_security_test._handle_navigation_api(params)

                # Should not return 400 for valid actions
                assert handler_for_security_test.send_response.call_args[0][0] == 200

    def test_navigation_action_validation_logs_security_events(self, handler_for_security_test):
        """Test that invalid actions log security events."""
        malicious_actions = [
            "../../../etc/passwd",
            "<script>alert('xss')</script>",
            "'; DROP TABLE events; --",
            "eval(malicious_code)",
            "../../admin/delete_all",
        ]

        for malicious_action in malicious_actions:
            params = {"action": [malicious_action]}

            with patch.object(
                handler_for_security_test.security_logger, "log_input_validation_failure"
            ) as mock_log:
                handler_for_security_test._handle_navigation_api(params)

                # Should log security event
                mock_log.assert_called_once()

                # Should include details about the invalid input
                call_args = mock_log.call_args[1]
                assert call_args["input_type"] == "navigation_action"
                assert malicious_action in call_args["validation_error"]
                assert call_args["details"]["input_value"] == malicious_action

                mock_log.reset_mock()

    def test_input_validation_logs_source_ip(self, handler_for_security_test):
        """Test that input validation failures log source IP."""
        params = {"action": ["malicious_action"]}

        with patch.object(
            handler_for_security_test.security_logger, "log_input_validation_failure"
        ) as mock_log:
            handler_for_security_test._handle_navigation_api(params)

            call_args = mock_log.call_args[1]
            assert call_args["details"]["source_ip"] == "192.168.1.100"

    def test_json_format_parameter_handling(self, handler_for_security_test):
        """Test handling of JSON format parameters vs query format."""
        # Test JSON format: {"action": "next"}
        json_params = {"action": "next"}

        with patch.object(
            handler_for_security_test.web_server, "handle_navigation", return_value=True
        ), patch.object(
            handler_for_security_test.web_server,
            "get_calendar_html",
            return_value="<html>Test</html>",
        ):

            handler_for_security_test._handle_navigation_api(json_params)

            # Should handle JSON format correctly
            handler_for_security_test.send_response.assert_called_with(200)

        # Test query format: {"action": ["next"]}
        query_params = {"action": ["next"]}

        with patch.object(
            handler_for_security_test.web_server, "handle_navigation", return_value=True
        ), patch.object(
            handler_for_security_test.web_server,
            "get_calendar_html",
            return_value="<html>Test</html>",
        ):

            handler_for_security_test._handle_navigation_api(query_params)

            # Should handle query format correctly
            handler_for_security_test.send_response.assert_called_with(200)


@pytest.mark.unit
class TestErrorHandling:
    """Test suite for error handling in web server."""

    def test_web_server_start_with_exception(self, test_settings, cache_manager):
        """Test web server start with exception."""
        display_manager = MagicMock()
        server = WebServer(test_settings, display_manager, cache_manager)

        with patch(
            "calendarbot.web.server.HTTPServer", side_effect=Exception("Server start error")
        ):
            with pytest.raises(Exception):
                server.start()

    def test_api_request_handler_with_no_web_server(self, test_settings):
        """Test API request handling without web server reference."""
        with patch("calendarbot.web.server.BaseHTTPRequestHandler.__init__"):
            handler = WebRequestHandler(None, None, None, web_server=None)
            handler.send_response = MagicMock()
            handler.send_header = MagicMock()
            handler.end_headers = MagicMock()
            handler.wfile = MagicMock()
            handler.client_address = ("127.0.0.1", 12345)

            # Test through the proper API flow, not directly calling _handle_navigation_api
            handler._handle_api_request("/api/navigate", {"action": ["next"]})

            # Should return 500 error due to null web_server
            handler.send_response.assert_called_with(500)

    def test_navigation_api_with_web_server_exception(self, mock_request_handler):
        """Test navigation API with exception in web server."""
        params = {"action": ["next"]}

        with patch.object(
            mock_request_handler.web_server, "handle_navigation", side_effect=Exception("Nav error")
        ):
            # Test through the full API request flow which has exception handling
            mock_request_handler._handle_api_request("/api/navigate", params)

            # Should handle exception gracefully with 500 error
            mock_request_handler.send_response.assert_called_with(500)


@pytest.mark.unit
class TestPerformance:
    """Performance tests for web server operations."""

    def test_get_calendar_html_performance(
        self, web_server_with_mock_renderer, performance_tracker
    ):
        """Test calendar HTML generation performance."""
        with patch("asyncio.run") as mock_run:
            mock_run.return_value = []

            performance_tracker.start_timer("html_generation")
            html = web_server_with_mock_renderer.get_calendar_html()
            performance_tracker.end_timer("html_generation")

            assert html is not None
            # Should complete quickly
            performance_tracker.assert_performance("html_generation", 1.0)

    def test_concurrent_api_requests_performance(self, mock_request_handler, performance_tracker):
        """Test performance of concurrent API requests."""
        import threading

        def make_request():
            params = {"action": ["next"]}
            with patch.object(
                mock_request_handler.web_server, "handle_navigation", return_value=True
            ), patch.object(
                mock_request_handler.web_server,
                "get_calendar_html",
                return_value="<html>Test</html>",
            ):
                mock_request_handler._handle_navigation_api(params)

        performance_tracker.start_timer("concurrent_requests")

        # Simulate 10 concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        performance_tracker.end_timer("concurrent_requests")

        # Should handle concurrent requests efficiently
        performance_tracker.assert_performance("concurrent_requests", 2.0)
