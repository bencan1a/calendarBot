"""Unit tests for the HTTP client utility."""

import socket
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from calendarbot.utils.http_client import HTTPClient, is_webserver_running, wait_for_webserver


class TestHTTPClient(unittest.TestCase):
    """Test cases for the HTTPClient class."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = HTTPClient(
            base_url="http://127.0.0.1:8080",
            timeout=0.5,
            max_retries=2,
            retry_delay=0.1,
        )

    def test_init(self):
        """Test HTTPClient initialization."""
        self.assertEqual(self.client.base_url, "http://127.0.0.1:8080")
        self.assertEqual(self.client.timeout, 0.5)
        self.assertEqual(self.client.max_retries, 2)
        self.assertEqual(self.client.retry_delay, 0.1)

    @patch("urllib.request.build_opener")
    def test_fetch_html_success(self, mock_build_opener):
        """Test successful HTML fetch."""
        # Configure mock
        mock_opener = MagicMock()
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html>Test</html>"
        mock_opener.open.return_value.__enter__.return_value = mock_response
        mock_build_opener.return_value = mock_opener

        # Call fetch_html
        html = self.client.fetch_html()

        # Verify build_opener was called
        mock_build_opener.assert_called_once()

        # Verify opener.open was called with correct URL and timeout
        mock_opener.open.assert_called_once()
        args, kwargs = mock_opener.open.call_args
        self.assertEqual(args[0].full_url, "http://127.0.0.1:8080/")
        self.assertEqual(kwargs["timeout"], 0.5)

        # Verify result
        self.assertEqual(html, "<html>Test</html>")

    @patch("urllib.request.build_opener")
    def test_fetch_html_with_path_and_params(self, mock_build_opener):
        """Test HTML fetch with path and query parameters."""
        # Configure mock
        mock_opener = MagicMock()
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html>Test</html>"
        mock_opener.open.return_value.__enter__.return_value = mock_response
        mock_build_opener.return_value = mock_opener

        # Call fetch_html with path and params
        html = self.client.fetch_html(
            path="/calendar",
            params={"days": "7", "debug_time": "2023-01-01T12:00:00"},
        )

        # Verify opener.open was called with correct URL
        mock_opener.open.assert_called_once()
        args, kwargs = mock_opener.open.call_args
        self.assertEqual(
            args[0].full_url,
            "http://127.0.0.1:8080/calendar?days=7&debug_time=2023-01-01T12%3A00%3A00",
        )

        # Verify result
        self.assertEqual(html, "<html>Test</html>")

    @patch("urllib.request.build_opener")
    def test_fetch_html_with_headers(self, mock_build_opener):
        """Test HTML fetch with custom headers."""
        # Configure mock
        mock_opener = MagicMock()
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html>Test</html>"
        mock_opener.open.return_value.__enter__.return_value = mock_response
        mock_build_opener.return_value = mock_opener

        # Call fetch_html with headers
        html = self.client.fetch_html(
            headers={"X-Custom-Header": "Value"},
        )

        # Verify opener.open was called with correct headers
        mock_opener.open.assert_called_once()
        args, kwargs = mock_opener.open.call_args

        # Get the Request object
        request = args[0]

        # Check if headers were set correctly in the _prepare_headers method
        # This is an indirect test since we can't easily access the headers directly in the mock
        with patch.object(self.client, "_prepare_headers") as mock_prepare_headers:
            mock_prepare_headers.return_value = {
                "X-Custom-Header": "Value",
                "User-Agent": "CalendarBot/1.0",
            }
            self.client.fetch_html(headers={"X-Custom-Header": "Value"})
            mock_prepare_headers.assert_called_once_with({"X-Custom-Header": "Value"})

        # Verify result
        self.assertEqual(html, "<html>Test</html>")

    @patch("urllib.request.build_opener")
    @patch("time.sleep")
    def test_fetch_html_retry_on_timeout(self, mock_time_sleep, mock_build_opener):
        """Test HTML fetch with retry on timeout."""
        # Configure mocks
        mock_opener = MagicMock()
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html>Test</html>"

        # First call raises timeout, second succeeds
        mock_opener.open.side_effect = [
            socket.timeout("Connection timed out"),
            MagicMock(__enter__=MagicMock(return_value=mock_response)),
        ]
        mock_build_opener.return_value = mock_opener

        # Call fetch_html
        html = self.client.fetch_html()

        # Verify opener.open was called twice
        self.assertEqual(mock_opener.open.call_count, 2)

        # Verify time.sleep was called for delay
        mock_time_sleep.assert_called_once_with(self.client.retry_delay)

        # Verify result
        self.assertEqual(html, "<html>Test</html>")

    @patch("urllib.request.build_opener")
    def test_fetch_html_max_retries_exceeded(self, mock_build_opener):
        """Test HTML fetch with max retries exceeded."""
        # Configure mock to always raise timeout
        mock_opener = MagicMock()
        mock_opener.open.side_effect = socket.timeout("Connection timed out")
        mock_build_opener.return_value = mock_opener

        # Call fetch_html and expect TimeoutError
        with self.assertRaises(TimeoutError):
            self.client.fetch_html()

        # Verify opener.open was called max_retries times
        self.assertEqual(mock_opener.open.call_count, 2)

    @patch("urllib.request.build_opener")
    def test_fetch_html_connection_refused(self, mock_build_opener):
        """Test HTML fetch with connection refused."""
        # Configure mock to raise ConnectionRefusedError
        mock_opener = MagicMock()
        mock_opener.open.side_effect = urllib.error.URLError(ConnectionRefusedError())
        mock_build_opener.return_value = mock_opener

        # Call fetch_html and expect ConnectionError
        with self.assertRaises(ConnectionError):
            self.client.fetch_html()

    @patch("urllib.request.build_opener")
    def test_fetch_calendar_html(self, mock_build_opener):
        """Test fetch_calendar_html convenience method."""
        # Configure mock
        mock_opener = MagicMock()
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html>Calendar</html>"
        mock_opener.open.return_value.__enter__.return_value = mock_response
        mock_build_opener.return_value = mock_opener

        # Call fetch_calendar_html
        html = self.client.fetch_calendar_html(days=7, debug_time="2023-01-01T12:00:00")

        # Verify opener.open was called with correct URL
        mock_opener.open.assert_called_once()
        args, kwargs = mock_opener.open.call_args
        self.assertEqual(
            args[0].full_url,
            "http://127.0.0.1:8080/calendar?days=7&debug_time=2023-01-01T12%3A00%3A00",
        )

        # Verify result
        self.assertEqual(html, "<html>Calendar</html>")

    def test_build_url(self):
        """Test _build_url method."""
        # Test with path only
        url = self.client._build_url("/test")
        self.assertEqual(url, "http://127.0.0.1:8080/test")

        # Test with path without leading slash
        url = self.client._build_url("test")
        self.assertEqual(url, "http://127.0.0.1:8080/test")

        # Test with path and params
        url = self.client._build_url("/test", {"param1": "value1", "param2": "value2"})
        self.assertEqual(url, "http://127.0.0.1:8080/test?param1=value1&param2=value2")

    def test_prepare_headers(self):
        """Test _prepare_headers method."""
        # Test default headers
        headers = self.client._prepare_headers()
        self.assertEqual(headers["User-Agent"], "CalendarBot/1.0")
        self.assertEqual(headers["Accept"], "text/html,application/xhtml+xml")

        # Test with custom headers
        headers = self.client._prepare_headers({"X-Custom": "Value", "User-Agent": "Custom/1.0"})
        self.assertEqual(headers["User-Agent"], "Custom/1.0")
        self.assertEqual(headers["X-Custom"], "Value")
        self.assertEqual(headers["Accept"], "text/html,application/xhtml+xml")


@pytest.mark.asyncio
class TestAsyncHTTPClient:
    """Test cases for the async methods of HTTPClient."""

    @pytest.fixture
    async def client(self):
        """Create HTTPClient fixture."""
        return HTTPClient(
            base_url="http://127.0.0.1:8080",
            timeout=0.5,
            max_retries=2,
            retry_delay=0.1,
        )

    @pytest.mark.asyncio
    async def test_fetch_html_async(self, client):
        """Test fetch_html_async method."""
        with patch("asyncio.to_thread") as mock_to_thread:
            # Configure mock
            mock_to_thread.return_value = "<html>Async Test</html>"

            # Call fetch_html_async
            html = await client.fetch_html_async(
                path="/test",
                params={"param": "value"},
                headers={"X-Custom": "Value"},
            )

            # Verify to_thread was called with correct arguments
            mock_to_thread.assert_called_once_with(
                client.fetch_html,
                path="/test",
                params={"param": "value"},
                headers={"X-Custom": "Value"},
            )

            # Verify result
            assert html == "<html>Async Test</html>"

    @pytest.mark.asyncio
    async def test_fetch_calendar_html_async(self, client):
        """Test fetch_calendar_html_async method."""
        with patch("asyncio.to_thread") as mock_to_thread:
            # Configure mock
            mock_to_thread.return_value = "<html>Async Calendar</html>"

            # Call fetch_calendar_html_async
            html = await client.fetch_calendar_html_async(
                days=7,
                debug_time="2023-01-01T12:00:00",
            )

            # Verify to_thread was called with correct arguments
            mock_to_thread.assert_called_once_with(
                client.fetch_html,
                path="/calendar",
                params={"days": "7", "debug_time": "2023-01-01T12:00:00"},
                headers=None,
            )

            # Verify result
            assert html == "<html>Async Calendar</html>"


class TestWebserverUtils(unittest.TestCase):
    """Test cases for webserver utility functions."""

    @patch("socket.create_connection")
    def test_is_webserver_running_true(self, mock_create_connection):
        """Test is_webserver_running when server is running."""
        # Configure mock
        mock_create_connection.return_value = MagicMock()

        # Call is_webserver_running
        result = is_webserver_running(host="127.0.0.1", port=8080, timeout=0.5)

        # Verify create_connection was called with correct arguments
        mock_create_connection.assert_called_once_with(("127.0.0.1", 8080), timeout=0.5)

        # Verify result
        self.assertTrue(result)

    @patch("socket.create_connection")
    def test_is_webserver_running_false(self, mock_create_connection):
        """Test is_webserver_running when server is not running."""
        # Configure mock to raise ConnectionRefusedError
        mock_create_connection.side_effect = ConnectionRefusedError()

        # Call is_webserver_running
        result = is_webserver_running(host="127.0.0.1", port=8080, timeout=0.5)

        # Verify create_connection was called with correct arguments
        mock_create_connection.assert_called_once_with(("127.0.0.1", 8080), timeout=0.5)

        # Verify result
        self.assertFalse(result)

    @patch("calendarbot.utils.http_client.is_webserver_running")
    @patch("time.time")
    @patch("time.sleep")
    def test_wait_for_webserver_success(
        self, mock_time_sleep, mock_time, mock_is_webserver_running
    ):
        """Test wait_for_webserver with successful connection."""
        # Configure mocks
        # Use a function to generate incrementing time values to avoid StopIteration
        time_counter = [0.0]

        def mock_time_func():
            time_counter[0] += 0.1
            return time_counter[0]

        mock_time.side_effect = mock_time_func
        mock_is_webserver_running.return_value = True

        # Call wait_for_webserver
        result = wait_for_webserver(host="127.0.0.1", port=8080, timeout=5.0, check_interval=0.1)

        # Verify is_webserver_running was called with correct arguments
        mock_is_webserver_running.assert_called_once_with("127.0.0.1", 8080, timeout=0.1)

        # Verify result
        self.assertTrue(result)

    @patch("calendarbot.utils.http_client.is_webserver_running")
    @patch("time.time")
    @patch("time.sleep")
    def test_wait_for_webserver_timeout(
        self, mock_time_sleep, mock_time, mock_is_webserver_running
    ):
        """Test wait_for_webserver with timeout."""
        # Configure mocks
        # Use a function to generate incrementing time values that exceed timeout
        time_counter = [0.0]

        def mock_time_func():
            current_time = time_counter[0]
            time_counter[0] += 2.6  # Increment by more than timeout to trigger timeout
            return current_time

        mock_time.side_effect = mock_time_func
        mock_is_webserver_running.return_value = False

        # Call wait_for_webserver
        result = wait_for_webserver(host="127.0.0.1", port=8080, timeout=5.0, check_interval=0.1)

        # Verify is_webserver_running was called
        self.assertEqual(mock_is_webserver_running.call_count, 1)

        # Verify result
        self.assertFalse(result)


@pytest.mark.asyncio
async def test_wait_for_webserver_async():
    """Test wait_for_webserver_async function."""
    with (
        patch("asyncio.to_thread") as mock_to_thread,
        patch("asyncio.get_event_loop") as mock_get_event_loop,
        patch("asyncio.sleep") as mock_sleep,
    ):
        # Configure mocks
        mock_loop = MagicMock()
        mock_loop.time.side_effect = [0, 0.1, 0.2]  # Start time, check time, final check
        mock_get_event_loop.return_value = mock_loop
        mock_to_thread.return_value = True

        # Call wait_for_webserver_async
        from calendarbot.utils.http_client import wait_for_webserver_async

        result = await wait_for_webserver_async(
            host="127.0.0.1",
            port=8080,
            timeout=5.0,
            check_interval=0.1,
        )

        # Verify to_thread was called with is_webserver_running
        mock_to_thread.assert_called_once_with(
            is_webserver_running,
            "127.0.0.1",
            8080,
            0.1,
        )

        # Verify result
        assert result is True
