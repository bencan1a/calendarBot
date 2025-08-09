"""Unit tests for the shared webserver utility."""

import socket
from unittest.mock import MagicMock, patch

import pytest

from calendarbot.cli.modes.shared_webserver import SharedWebServer, find_available_port


class TestSharedWebServer:
    """Test cases for the SharedWebServer class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings fixture."""
        mock_settings = MagicMock()
        mock_settings.web_host = "127.0.0.1"
        mock_settings.web_port = 8081
        mock_settings.web_layout = "whats-next-view"
        mock_settings.auto_kill_existing = False
        return mock_settings

    @pytest.fixture
    def mock_display_manager(self):
        """Create mock display manager fixture."""
        return MagicMock()

    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager fixture."""
        return MagicMock()

    @pytest.fixture
    def mock_navigation_state(self):
        """Create mock navigation state fixture."""
        return MagicMock()

    @patch("calendarbot.cli.modes.shared_webserver.WebServer")
    def test_init(
        self,
        mock_web_server_class,
        mock_settings,
        mock_display_manager,
        mock_cache_manager,
        mock_navigation_state,
    ):
        """Test SharedWebServer initialization."""
        # Create SharedWebServer instance
        server = SharedWebServer(
            settings=mock_settings,
            display_manager=mock_display_manager,
            cache_manager=mock_cache_manager,
            navigation_state=mock_navigation_state,
        )

        # Verify attributes
        assert server.host == "127.0.0.1"
        assert server.port == 8081
        assert server.layout == "whats-next-view"
        assert server.running is False
        assert server.server is None
        assert server.server_thread is None
        assert server.web_server is None

    @patch("calendarbot.cli.modes.shared_webserver.WebServer")
    def test_start_success(
        self, mock_web_server_class, mock_settings, mock_display_manager, mock_cache_manager
    ):
        """Test successful server start."""
        # Configure mock
        mock_web_server_instance = MagicMock()
        mock_web_server_class.return_value = mock_web_server_instance

        # Create SharedWebServer instance
        server = SharedWebServer(
            settings=mock_settings,
            display_manager=mock_display_manager,
            cache_manager=mock_cache_manager,
        )

        # Call start method
        result = server.start(auto_find_port=False)

        # Verify WebServer was created and started
        mock_web_server_class.assert_called_once()
        mock_web_server_instance.start.assert_called_once()

        # Verify result and state
        assert result is True
        assert server.running is True
        assert server.web_server == mock_web_server_instance

    @patch("calendarbot.cli.modes.shared_webserver.WebServer")
    def test_start_failure(
        self, mock_web_server_class, mock_settings, mock_display_manager, mock_cache_manager
    ):
        """Test server start failure."""
        # Configure mock to raise an exception
        mock_web_server_instance = MagicMock()
        mock_web_server_instance.start.side_effect = Exception("Failed to start")
        mock_web_server_class.return_value = mock_web_server_instance

        # Create SharedWebServer instance
        server = SharedWebServer(
            settings=mock_settings,
            display_manager=mock_display_manager,
            cache_manager=mock_cache_manager,
        )

        # Call start method
        result = server.start(auto_find_port=False)

        # Verify WebServer was created and start was attempted
        mock_web_server_class.assert_called_once()
        mock_web_server_instance.start.assert_called_once()

        # Verify result and state
        assert result is False
        assert server.running is False

    @patch("calendarbot.cli.modes.shared_webserver.WebServer")
    def test_stop_success(
        self, mock_web_server_class, mock_settings, mock_display_manager, mock_cache_manager
    ):
        """Test successful server stop."""
        # Configure mock
        mock_web_server_instance = MagicMock()
        mock_web_server_class.return_value = mock_web_server_instance

        # Create SharedWebServer instance
        server = SharedWebServer(
            settings=mock_settings,
            display_manager=mock_display_manager,
            cache_manager=mock_cache_manager,
        )

        # Start server
        server.start(auto_find_port=False)

        # Call stop method
        result = server.stop()

        # Verify WebServer was stopped
        mock_web_server_instance.stop.assert_called_once()

        # Verify result and state
        assert result is True
        assert server.running is False

    @patch("calendarbot.cli.modes.shared_webserver.WebServer")
    def test_stop_failure(
        self, mock_web_server_class, mock_settings, mock_display_manager, mock_cache_manager
    ):
        """Test server stop failure."""
        # Configure mock to raise an exception
        mock_web_server_instance = MagicMock()
        mock_web_server_instance.stop.side_effect = Exception("Failed to stop")
        mock_web_server_class.return_value = mock_web_server_instance

        # Create SharedWebServer instance
        server = SharedWebServer(
            settings=mock_settings,
            display_manager=mock_display_manager,
            cache_manager=mock_cache_manager,
        )

        # Start server
        server.start(auto_find_port=False)

        # Call stop method
        result = server.stop()

        # Verify WebServer stop was attempted
        mock_web_server_instance.stop.assert_called_once()

        # Verify result and state
        assert result is False
        assert server.running is False

    @patch("calendarbot.cli.modes.shared_webserver.WebServer")
    def test_get_calendar_html(
        self, mock_web_server_class, mock_settings, mock_display_manager, mock_cache_manager
    ):
        """Test get_calendar_html method."""
        # Configure mock
        mock_web_server_instance = MagicMock()
        mock_web_server_instance.get_calendar_html.return_value = "<html>Test</html>"
        mock_web_server_class.return_value = mock_web_server_instance

        # Create SharedWebServer instance
        server = SharedWebServer(
            settings=mock_settings,
            display_manager=mock_display_manager,
            cache_manager=mock_cache_manager,
        )

        # Start server
        server.start(auto_find_port=False)

        # Call get_calendar_html method
        html = server.get_calendar_html(days=7)

        # Verify WebServer.get_calendar_html was called
        mock_web_server_instance.get_calendar_html.assert_called_once_with(7, None)

        # Verify result
        assert html == "<html>Test</html>"

    @patch("calendarbot.cli.modes.shared_webserver.WebServer")
    def test_get_calendar_html_not_running(
        self, mock_web_server_class, mock_settings, mock_display_manager, mock_cache_manager
    ):
        """Test get_calendar_html when server is not running."""
        # Create SharedWebServer instance
        server = SharedWebServer(
            settings=mock_settings,
            display_manager=mock_display_manager,
            cache_manager=mock_cache_manager,
        )

        # Call get_calendar_html method without starting server
        with pytest.raises(RuntimeError):
            server.get_calendar_html()

    @patch("calendarbot.cli.modes.shared_webserver.WebServer")
    def test_get_status(
        self, mock_web_server_class, mock_settings, mock_display_manager, mock_cache_manager
    ):
        """Test get_status method."""
        # Configure mock
        mock_web_server_instance = MagicMock()
        mock_web_server_instance.get_status.return_value = {
            "running": True,
            "host": "127.0.0.1",
            "port": 8081,
            "layout": "whats-next-view",
        }
        mock_web_server_class.return_value = mock_web_server_instance

        # Create SharedWebServer instance
        server = SharedWebServer(
            settings=mock_settings,
            display_manager=mock_display_manager,
            cache_manager=mock_cache_manager,
        )

        # Start server
        server.start(auto_find_port=False)

        # Call get_status method
        status = server.get_status()

        # Verify WebServer.get_status was called
        mock_web_server_instance.get_status.assert_called_once()

        # Verify result
        assert status["running"] is True
        assert status["port"] == 8081

    @patch("calendarbot.cli.modes.shared_webserver.socket.socket")
    def test_find_available_port(self, mock_socket):
        """Test find_available_port function."""
        # Configure mock to succeed on first attempt
        mock_socket_instance = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_socket_instance

        # Call find_available_port
        port = find_available_port(start_port=8080, max_attempts=5)

        # Verify socket was created and bind was called
        mock_socket.assert_called_once()
        mock_socket_instance.bind.assert_called_once_with(("127.0.0.1", 8080))

        # Verify result
        assert port == 8080

    @patch("calendarbot.cli.modes.shared_webserver.socket.socket")
    def test_find_available_port_retry(self, mock_socket):
        """Test find_available_port with retry."""
        # Configure mock to fail on first attempt, succeed on second
        mock_socket_instance = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        mock_socket_instance.bind.side_effect = [
            OSError("Address in use"),
            None,  # Success on second attempt
        ]

        # Call find_available_port
        port = find_available_port(start_port=8080, max_attempts=5)

        # Verify socket was created twice and bind was called twice
        assert mock_socket.call_count == 2

        # Verify bind was called with different ports
        mock_socket_instance.bind.assert_any_call(("127.0.0.1", 8080))
        mock_socket_instance.bind.assert_any_call(("127.0.0.1", 8081))

        # Verify result
        assert port == 8081

    @patch("calendarbot.cli.modes.shared_webserver.socket.socket")
    def test_find_available_port_exhausted(self, mock_socket):
        """Test find_available_port with all attempts exhausted."""
        # Configure mock to fail on all attempts
        mock_socket_instance = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        mock_socket_instance.bind.side_effect = OSError("Address in use")

        # Call find_available_port
        with pytest.raises(RuntimeError):
            find_available_port(start_port=8080, max_attempts=3)

        # Verify socket was created three times and bind was called three times
        assert mock_socket.call_count == 3

        # Verify bind was called with different ports
        mock_socket_instance.bind.assert_any_call(("127.0.0.1", 8080))
        mock_socket_instance.bind.assert_any_call(("127.0.0.1", 8081))
        mock_socket_instance.bind.assert_any_call(("127.0.0.1", 8082))


@pytest.mark.asyncio
async def test_auto_port_conflict_resolution():
    """Test automatic port conflict resolution."""
    # Create a socket to occupy a port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Bind to a port
        sock.bind(("127.0.0.1", 8081))
        sock.listen(1)

        # Create mock objects
        mock_settings = MagicMock()
        mock_settings.web_host = "127.0.0.1"
        mock_settings.web_port = 8081  # Same port as the one we're occupying
        mock_settings.web_layout = "whats-next-view"
        mock_settings.auto_kill_existing = False

        mock_display_manager = MagicMock()
        mock_cache_manager = MagicMock()

        # Patch WebServer to avoid actually starting it
        with patch("calendarbot.cli.modes.shared_webserver.WebServer") as mock_web_server_class:
            mock_web_server_instance = MagicMock()
            # Configure the mock to raise OSError on first start() call, then succeed on second call
            mock_web_server_instance.start.side_effect = [OSError("Port already in use"), None]
            mock_web_server_class.return_value = mock_web_server_instance

            # Create SharedWebServer instance
            server = SharedWebServer(
                settings=mock_settings,
                display_manager=mock_display_manager,
                cache_manager=mock_cache_manager,
            )

            # Start server with auto_find_port=True
            result = server.start(auto_find_port=True, max_port_attempts=5)

            # Verify server started successfully
            assert result is True

            # Verify port was incremented
            assert server.port == 8082  # Should be 8081 + 1

    finally:
        # Clean up
        sock.close()
