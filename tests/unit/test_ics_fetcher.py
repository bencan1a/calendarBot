"""Unit tests for ICS Fetcher HTTP client functionality."""

from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from calendarbot.ics.exceptions import ICSAuthError, ICSFetchError, ICSNetworkError, ICSTimeoutError
from calendarbot.ics.fetcher import ICSFetcher
from calendarbot.ics.models import AuthType, ICSAuth, ICSResponse, ICSSource


class TestICSFetcherInitialization:
    """Test ICSFetcher initialization and setup."""

    def test_init_creates_fetcher(self, test_settings):
        """Test that ICSFetcher.__init__ creates fetcher correctly."""
        with patch("calendarbot.ics.fetcher.SecurityEventLogger"):
            fetcher = ICSFetcher(test_settings)

            assert fetcher.settings == test_settings
            assert fetcher.client is None
            assert fetcher.security_logger is not None

    @pytest.mark.asyncio
    async def test_ensure_client_creates_http_client(self, test_settings):
        """Test that _ensure_client creates httpx.AsyncClient with correct config."""
        with patch("calendarbot.ics.fetcher.SecurityEventLogger"), patch(
            "httpx.AsyncClient"
        ) as mock_client:

            fetcher = ICSFetcher(test_settings)
            await fetcher._ensure_client()

            # Verify client was created with correct settings
            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args.kwargs

            assert call_kwargs["follow_redirects"] is True
            assert call_kwargs["verify"] is True
            assert "timeout" in call_kwargs
            assert "headers" in call_kwargs

            # Verify headers
            headers = call_kwargs["headers"]
            assert headers["User-Agent"].startswith(test_settings.app_name)
            assert "text/calendar" in headers["Accept"]

    @pytest.mark.asyncio
    async def test_ensure_client_reuses_existing_client(self, test_settings):
        """Test that _ensure_client reuses existing client if not closed."""
        with patch("calendarbot.ics.fetcher.SecurityEventLogger"), patch(
            "httpx.AsyncClient"
        ) as mock_client:

            fetcher = ICSFetcher(test_settings)

            # Create mock client instance
            mock_client_instance = MagicMock()
            mock_client_instance.is_closed = False
            mock_client.return_value = mock_client_instance

            # First call should create client
            await fetcher._ensure_client()
            fetcher.client = mock_client_instance

            # Second call should reuse
            await fetcher._ensure_client()

            # Should only be called once
            mock_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_client_closes_http_client(self, test_settings):
        """Test that _close_client properly closes httpx client."""
        with patch("calendarbot.ics.fetcher.SecurityEventLogger"):
            fetcher = ICSFetcher(test_settings)

            # Mock client
            mock_client = AsyncMock()
            mock_client.is_closed = False
            fetcher.client = mock_client

            await fetcher._close_client()

            mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self, test_settings):
        """Test async context manager properly manages client lifecycle."""
        with patch("calendarbot.ics.fetcher.SecurityEventLogger"), patch(
            "httpx.AsyncClient"
        ) as mock_client:

            mock_client_instance = AsyncMock()
            mock_client_instance.is_closed = False  # Ensure close method gets called
            mock_client.return_value = mock_client_instance

            async with ICSFetcher(test_settings) as fetcher:
                # Client should be created
                assert fetcher.client is not None

            # Client should be closed after exiting context
            mock_client_instance.aclose.assert_called_once()


class TestICSFetcherSSRFProtection:
    """Test ICS Fetcher SSRF protection validation."""

    @pytest.fixture
    def fetcher(self, test_settings):
        """Create ICSFetcher instance for testing."""
        with patch("calendarbot.ics.fetcher.SecurityEventLogger"):
            return ICSFetcher(test_settings)

    @pytest.mark.parametrize(
        "malicious_url",
        [
            "http://localhost:80/",
            "http://127.0.0.1:80/",
            "http://[::1]:80/",
            "http://192.168.1.1/",
            "http://10.0.0.1/",
            "http://172.16.0.1/",
            "file:///etc/passwd",
            "ftp://internal.server/",
            "http://2130706433/",  # 127.0.0.1 in decimal
            "http://0x7f000001/",  # 127.0.0.1 in hex
        ],
    )
    def test_validate_url_blocks_malicious_urls(self, fetcher, malicious_url):
        """Test that SSRF protection blocks malicious URLs."""
        result = fetcher._validate_url_for_ssrf(malicious_url)
        assert result is False

    @pytest.mark.parametrize(
        "safe_url",
        [
            "https://calendar.google.com/calendar/ical/example.ics",
            "https://outlook.live.com/owa/calendar/example.ics",
            "https://example.com/calendar.ics",
            "http://public-server.com/calendar.ics",
            "https://calendars.office365.com/test.ics",
        ],
    )
    def test_validate_url_allows_safe_urls(self, fetcher, safe_url):
        """Test that SSRF protection allows safe public URLs."""
        result = fetcher._validate_url_for_ssrf(safe_url)
        assert result is True

    def test_validate_url_handles_invalid_urls(self, fetcher):
        """Test SSRF validation handles malformed URLs gracefully."""
        invalid_urls = ["not-a-url", "http://", "https://", "", None]

        for invalid_url in invalid_urls:
            result = fetcher._validate_url_for_ssrf(str(invalid_url) if invalid_url else "")
            assert result is False

    def test_validate_url_logs_security_events(self, fetcher):
        """Test that SSRF validation logs security events."""
        with patch.object(fetcher.security_logger, "log_event") as mock_log:
            # Test blocked URL
            fetcher._validate_url_for_ssrf("http://localhost/")

            # Should log security violation
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0][0]
            assert hasattr(call_args, "event_type")
            assert hasattr(call_args, "severity")


class TestICSFetcherHTTPOperations:
    """Test ICS Fetcher HTTP request operations."""

    @pytest.fixture
    def fetcher_with_mocks(self, test_settings):
        """Create ICSFetcher with mocked dependencies."""
        with patch("calendarbot.ics.fetcher.SecurityEventLogger"):
            fetcher = ICSFetcher(test_settings)
            mock_client = AsyncMock()
            mock_client.is_closed = False  # Prevent _ensure_client from creating new client
            fetcher.client = mock_client
            return fetcher

    @pytest.fixture
    def sample_ics_source(self):
        """Create sample ICS source for testing."""
        auth = ICSAuth(type=AuthType.NONE)
        return ICSSource(
            name="Test Source",
            url="https://example.com/calendar.ics",
            auth=auth,
            timeout=30,
            validate_ssl=True,
        )

    @pytest.mark.asyncio
    async def test_fetch_ics_success(
        self, fetcher_with_mocks, sample_ics_source, sample_ics_content
    ):
        """Test successful ICS content fetching."""
        fetcher = fetcher_with_mocks

        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_ics_content
        mock_response.headers = {
            "content-type": "text/calendar",
            "etag": '"12345"',
            "last-modified": "Wed, 01 Jan 2024 12:00:00 GMT",
        }

        fetcher._make_request_with_retry = AsyncMock(return_value=mock_response)

        result = await fetcher.fetch_ics(sample_ics_source)

        assert result.success is True
        assert result.content == sample_ics_content
        assert result.status_code == 200
        assert result.etag == '"12345"'
        assert "content-type" in result.headers

    @pytest.mark.asyncio
    async def test_fetch_ics_ssrf_blocked(self, fetcher_with_mocks):
        """Test that SSRF protection blocks malicious URLs."""
        fetcher = fetcher_with_mocks

        # Create source with malicious URL
        auth = ICSAuth(type=AuthType.NONE)
        malicious_source = ICSSource(
            name="Malicious Source", url="http://localhost/calendar.ics", auth=auth
        )

        result = await fetcher.fetch_ics(malicious_source)

        assert result.success is False
        assert result.status_code == 403
        assert "security reasons" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_ics_timeout_error(self, fetcher_with_mocks, sample_ics_source):
        """Test handling of timeout errors."""
        fetcher = fetcher_with_mocks

        # Mock timeout exception
        fetcher._make_request_with_retry = AsyncMock(
            side_effect=httpx.TimeoutException("Request timeout")
        )

        result = await fetcher.fetch_ics(sample_ics_source)

        assert result.success is False
        assert result.status_code is None
        assert "timeout" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_ics_auth_error(self, fetcher_with_mocks, sample_ics_source):
        """Test handling of authentication errors."""
        fetcher = fetcher_with_mocks

        # Mock 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.reason_phrase = "Unauthorized"

        http_error = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=mock_response
        )

        fetcher._make_request_with_retry = AsyncMock(side_effect=http_error)

        with pytest.raises(ICSAuthError):
            await fetcher.fetch_ics(sample_ics_source)

    @pytest.mark.asyncio
    async def test_fetch_ics_network_error(self, fetcher_with_mocks, sample_ics_source):
        """Test handling of network errors."""
        fetcher = fetcher_with_mocks

        # Mock network error
        fetcher._make_request_with_retry = AsyncMock(
            side_effect=httpx.NetworkError("Connection failed")
        )

        with pytest.raises(ICSNetworkError):
            await fetcher.fetch_ics(sample_ics_source)

    @pytest.mark.asyncio
    async def test_fetch_ics_not_modified(self, fetcher_with_mocks, sample_ics_source):
        """Test handling of 304 Not Modified responses."""
        fetcher = fetcher_with_mocks

        # Mock 304 response
        mock_response = MagicMock()
        mock_response.status_code = 304
        mock_response.headers = {
            "etag": '"12345"',
            "last-modified": "Wed, 01 Jan 2024 12:00:00 GMT",
        }

        fetcher._make_request_with_retry = AsyncMock(return_value=mock_response)

        result = await fetcher.fetch_ics(sample_ics_source)

        assert result.success is True
        assert result.status_code == 304
        assert result.content is None
        assert result.etag == '"12345"'

    @pytest.mark.asyncio
    async def test_fetch_ics_with_conditional_headers(self, fetcher_with_mocks, sample_ics_source):
        """Test fetching with conditional request headers."""
        fetcher = fetcher_with_mocks

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ICS content"
        mock_response.headers = {"content-type": "text/calendar"}

        fetcher._make_request_with_retry = AsyncMock(return_value=mock_response)

        conditional_headers = {
            "If-None-Match": '"12345"',
            "If-Modified-Since": "Wed, 01 Jan 2024 12:00:00 GMT",
        }

        result = await fetcher.fetch_ics(sample_ics_source, conditional_headers)

        assert result.success is True

        # Verify conditional headers were passed
        call_args = fetcher._make_request_with_retry.call_args
        headers_arg = call_args[0][1]  # Second argument is headers
        assert "If-None-Match" in headers_arg
        assert "If-Modified-Since" in headers_arg


class TestICSFetcherRequestRetry:
    """Test ICS Fetcher retry logic."""

    @pytest.fixture
    def fetcher_with_client(self, test_settings):
        """Create ICSFetcher with real client for retry testing."""
        with patch("calendarbot.ics.fetcher.SecurityEventLogger"):
            fetcher = ICSFetcher(test_settings)
            fetcher.client = AsyncMock()
            return fetcher

    @pytest.mark.asyncio
    async def test_make_request_with_retry_success_first_attempt(self, fetcher_with_client):
        """Test successful request on first attempt."""
        fetcher = fetcher_with_client

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        fetcher.client.get.return_value = mock_response

        result = await fetcher._make_request_with_retry(
            "https://example.com/calendar.ics", {}, 30, True
        )

        assert result == mock_response
        fetcher.client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_with_retry_success_after_retries(
        self, fetcher_with_client, test_settings
    ):
        """Test successful request after retries."""
        fetcher = fetcher_with_client
        test_settings.max_retries = 2

        # Mock responses: first two fail, third succeeds
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        fetcher.client.get.side_effect = [
            httpx.TimeoutException("First timeout"),
            httpx.NetworkError("Second network error"),
            mock_response,
        ]

        with patch("asyncio.sleep"):  # Speed up test
            result = await fetcher._make_request_with_retry(
                "https://example.com/calendar.ics", {}, 30, True
            )

        assert result == mock_response
        assert fetcher.client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_make_request_with_retry_max_retries_exceeded(
        self, fetcher_with_client, test_settings
    ):
        """Test that max retries are respected."""
        fetcher = fetcher_with_client
        test_settings.max_retries = 1

        # Mock all attempts to fail
        fetcher.client.get.side_effect = httpx.TimeoutException("Persistent timeout")

        with patch("asyncio.sleep"):  # Speed up test
            with pytest.raises(httpx.TimeoutException):
                await fetcher._make_request_with_retry(
                    "https://example.com/calendar.ics", {}, 30, True
                )

        # Should try max_retries + 1 times
        assert fetcher.client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_make_request_with_retry_no_retry_on_http_errors(self, fetcher_with_client):
        """Test that HTTP errors don't trigger retries."""
        fetcher = fetcher_with_client

        # Mock HTTP error (should not retry)
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=mock_response
        )

        fetcher.client.get.side_effect = http_error

        with pytest.raises(httpx.HTTPStatusError):
            await fetcher._make_request_with_retry("https://example.com/calendar.ics", {}, 30, True)

        # Should only try once (no retries for HTTP errors)
        fetcher.client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_handles_304_not_modified(self, fetcher_with_client):
        """Test that 304 Not Modified is handled correctly."""
        fetcher = fetcher_with_client

        # Mock 304 response
        mock_response = MagicMock()
        mock_response.status_code = 304

        fetcher.client.get.return_value = mock_response

        result = await fetcher._make_request_with_retry(
            "https://example.com/calendar.ics", {}, 30, True
        )

        assert result == mock_response
        # Should not call raise_for_status for 304
        mock_response.raise_for_status.assert_not_called()


class TestICSFetcherResponseCreation:
    """Test ICS Fetcher response creation and validation."""

    @pytest.fixture
    def fetcher(self, test_settings):
        """Create ICSFetcher instance for testing."""
        with patch("calendarbot.ics.fetcher.SecurityEventLogger"):
            return ICSFetcher(test_settings)

    def test_create_response_success(self, fetcher, sample_ics_content):
        """Test creating successful ICS response."""
        # Mock HTTP response
        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        mock_http_response.text = sample_ics_content
        mock_http_response.headers = {
            "content-type": "text/calendar; charset=utf-8",
            "etag": '"abcd1234"',
            "last-modified": "Thu, 02 Jan 2024 10:30:00 GMT",
            "cache-control": "max-age=3600",
        }

        result = fetcher._create_response(mock_http_response)

        assert result.success is True
        assert result.content == sample_ics_content
        assert result.status_code == 200
        assert result.etag == '"abcd1234"'
        assert result.last_modified == "Thu, 02 Jan 2024 10:30:00 GMT"
        assert result.cache_control == "max-age=3600"
        assert "content-type" in result.headers

    def test_create_response_304_not_modified(self, fetcher):
        """Test creating response for 304 Not Modified."""
        mock_http_response = MagicMock()
        mock_http_response.status_code = 304
        mock_http_response.headers = {
            "etag": '"abcd1234"',
            "last-modified": "Thu, 02 Jan 2024 10:30:00 GMT",
        }

        result = fetcher._create_response(mock_http_response)

        assert result.success is True
        assert result.content is None
        assert result.status_code == 304
        assert result.etag == '"abcd1234"'

    def test_create_response_empty_content(self, fetcher):
        """Test handling of empty ICS content."""
        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        mock_http_response.text = ""
        mock_http_response.headers = {"content-type": "text/calendar"}

        result = fetcher._create_response(mock_http_response)

        assert result.success is False
        assert "Empty content received" in result.error_message

    def test_create_response_invalid_ics_format(self, fetcher):
        """Test handling of content that doesn't look like ICS."""
        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        mock_http_response.text = "<html><body>Not ICS content</body></html>"
        mock_http_response.headers = {"content-type": "text/html"}

        result = fetcher._create_response(mock_http_response)

        # Should still succeed but with warning logged
        assert result.success is True
        assert result.content == "<html><body>Not ICS content</body></html>"

    def test_create_response_unexpected_content_type(self, fetcher):
        """Test handling of unexpected content types."""
        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        mock_http_response.text = "BEGIN:VCALENDAR\nEND:VCALENDAR"
        mock_http_response.headers = {"content-type": "application/json"}

        result = fetcher._create_response(mock_http_response)

        # Should succeed despite unexpected content type
        assert result.success is True
        assert "BEGIN:VCALENDAR" in result.content


class TestICSFetcherConnectionTesting:
    """Test ICS Fetcher connection testing functionality."""

    @pytest.fixture
    def fetcher_with_mocks(self, test_settings):
        """Create ICSFetcher with mocked client."""
        with patch("calendarbot.ics.fetcher.SecurityEventLogger"):
            fetcher = ICSFetcher(test_settings)
            fetcher.client = AsyncMock()
            return fetcher

    @pytest.fixture
    def sample_ics_source(self):
        """Create sample ICS source for testing."""
        auth = ICSAuth(type=AuthType.BASIC, username="user", password="pass")
        return ICSSource(
            name="Test Source", url="https://example.com/calendar.ics", auth=auth, timeout=30
        )

    @pytest.mark.asyncio
    async def test_test_connection_success_with_head(self, fetcher_with_mocks, sample_ics_source):
        """Test successful connection test using HEAD request."""
        fetcher = fetcher_with_mocks

        # Mock successful HEAD response
        mock_response = MagicMock()
        mock_response.status_code = 200
        fetcher.client.head = AsyncMock(return_value=mock_response)

        # Mock _ensure_client to prevent client recreation
        fetcher._ensure_client = AsyncMock()

        result = await fetcher.test_connection(sample_ics_source)

        assert result is True
        fetcher.client.head.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_fallback_to_get(self, fetcher_with_mocks, sample_ics_source):
        """Test connection test falls back to GET when HEAD not supported."""
        fetcher = fetcher_with_mocks

        # Mock HEAD returning 405 Method Not Allowed
        mock_head_response = MagicMock()
        mock_head_response.status_code = 405
        fetcher.client.head = AsyncMock(return_value=mock_head_response)

        # Mock _ensure_client to prevent client recreation
        fetcher._ensure_client = AsyncMock()

        # Mock successful fetch_ics
        fetcher.fetch_ics = AsyncMock()
        mock_ics_response = MagicMock()
        mock_ics_response.success = True
        fetcher.fetch_ics.return_value = mock_ics_response

        result = await fetcher.test_connection(sample_ics_source)

        assert result is True
        fetcher.client.head.assert_called_once()
        fetcher.fetch_ics.assert_called_once_with(sample_ics_source)

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, fetcher_with_mocks, sample_ics_source):
        """Test connection test failure."""
        fetcher = fetcher_with_mocks

        # Mock _ensure_client to prevent client recreation
        fetcher._ensure_client = AsyncMock()

        # Mock failed HEAD response
        mock_response = MagicMock()
        mock_response.status_code = 404
        fetcher.client.head.return_value = mock_response

        result = await fetcher.test_connection(sample_ics_source)

        assert result is False

    @pytest.mark.asyncio
    async def test_test_connection_exception(self, fetcher_with_mocks, sample_ics_source):
        """Test connection test with exception."""
        fetcher = fetcher_with_mocks

        # Mock _ensure_client to prevent client recreation
        fetcher._ensure_client = AsyncMock()

        # Mock exception during HEAD request
        fetcher.client.head.side_effect = Exception("Network error")

        result = await fetcher.test_connection(sample_ics_source)

        assert result is False


class TestICSFetcherConditionalHeaders:
    """Test ICS Fetcher conditional request headers."""

    @pytest.fixture
    def fetcher(self, test_settings):
        """Create ICSFetcher instance for testing."""
        with patch("calendarbot.ics.fetcher.SecurityEventLogger"):
            return ICSFetcher(test_settings)

    def test_get_conditional_headers_with_etag(self, fetcher):
        """Test creating conditional headers with ETag."""
        headers = fetcher.get_conditional_headers(etag='"12345"')

        assert headers["If-None-Match"] == '"12345"'
        assert "If-Modified-Since" not in headers

    def test_get_conditional_headers_with_last_modified(self, fetcher):
        """Test creating conditional headers with Last-Modified."""
        last_modified = "Wed, 01 Jan 2024 12:00:00 GMT"
        headers = fetcher.get_conditional_headers(last_modified=last_modified)

        assert headers["If-Modified-Since"] == last_modified
        assert "If-None-Match" not in headers

    def test_get_conditional_headers_with_both(self, fetcher):
        """Test creating conditional headers with both ETag and Last-Modified."""
        etag = '"12345"'
        last_modified = "Wed, 01 Jan 2024 12:00:00 GMT"

        headers = fetcher.get_conditional_headers(etag=etag, last_modified=last_modified)

        assert headers["If-None-Match"] == etag
        assert headers["If-Modified-Since"] == last_modified

    def test_get_conditional_headers_empty(self, fetcher):
        """Test creating conditional headers with no values."""
        headers = fetcher.get_conditional_headers()

        assert headers == {}


@pytest.mark.asyncio
async def test_ics_fetcher_integration_flow(test_settings, sample_ics_content):
    """Integration test of ICSFetcher complete workflow."""
    with patch("calendarbot.ics.fetcher.SecurityEventLogger"), patch(
        "httpx.AsyncClient"
    ) as mock_client_class:

        # Mock HTTP client
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.is_closed = False

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_ics_content
        mock_response.headers = {"content-type": "text/calendar", "etag": '"test123"'}
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        # Create source
        auth = ICSAuth(type=AuthType.NONE)
        source = ICSSource(
            name="Integration Test", url="https://example.com/calendar.ics", auth=auth
        )

        # Test complete flow
        async with ICSFetcher(test_settings) as fetcher:
            # Test connection
            mock_client.head.return_value = mock_response
            connection_ok = await fetcher.test_connection(source)
            assert connection_ok is True

            # Fetch ICS content
            ics_response = await fetcher.fetch_ics(source)
            assert ics_response.success is True
            assert ics_response.content == sample_ics_content

            # Test conditional headers
            conditional_headers = fetcher.get_conditional_headers(etag=ics_response.etag)
            assert "If-None-Match" in conditional_headers

        # Verify client was closed
        mock_client.aclose.assert_called_once()
