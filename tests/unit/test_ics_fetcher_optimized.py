"""Optimized ICS fetcher tests for core HTTP functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.ics.exceptions import ICSAuthError, ICSFetchError, ICSNetworkError
from calendarbot.ics.fetcher import ICSFetcher
from calendarbot.ics.models import ICSAuth, ICSSource


@pytest.mark.unit
@pytest.mark.critical_path
class TestICSFetcherCore:
    """Core ICS fetcher functionality tests."""

    @pytest.fixture
    def fetcher(self, test_settings):
        """Create ICS fetcher instance."""
        return ICSFetcher(test_settings)

    @pytest.fixture
    def mock_ics_source(self):
        """Create mock ICS source."""
        return ICSSource(
            name="test_source",
            url="https://example.com/calendar.ics",
            auth=ICSAuth(),
            timeout=10,
            validate_ssl=True,
            custom_headers={},
        )

    def test_fetcher_initialization(self, fetcher, test_settings):
        """Test fetcher initializes correctly."""
        assert fetcher.settings == test_settings
        assert fetcher.client is None
        assert fetcher.security_logger is not None

    @pytest.mark.asyncio
    async def test_context_manager_entry_exit(self, fetcher):
        """Test async context manager functionality."""
        async with fetcher as f:
            assert f is fetcher
            assert fetcher.client is not None

        # Client should be closed after exit
        assert fetcher.client.is_closed

    @pytest.mark.asyncio
    async def test_ensure_client_creates_client(self, fetcher):
        """Test client creation."""
        await fetcher._ensure_client()

        assert fetcher.client is not None
        assert not fetcher.client.is_closed

        await fetcher._close_client()

    @pytest.mark.asyncio
    async def test_ensure_client_reuses_existing(self, fetcher):
        """Test client reuse when already exists."""
        await fetcher._ensure_client()
        first_client = fetcher.client

        await fetcher._ensure_client()

        assert fetcher.client is first_client
        await fetcher._close_client()

    @pytest.mark.asyncio
    async def test_close_client_when_exists(self, fetcher):
        """Test closing existing client."""
        await fetcher._ensure_client()
        assert not fetcher.client.is_closed

        await fetcher._close_client()

        assert fetcher.client.is_closed

    @pytest.mark.asyncio
    async def test_close_client_when_none(self, fetcher):
        """Test closing client when none exists."""
        # Should not raise exception
        await fetcher._close_client()

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://example.com/calendar.ics", True),
            ("http://example.com/calendar.ics", True),
            ("ftp://example.com/calendar.ics", False),
            ("https://localhost/calendar.ics", False),
            ("https://127.0.0.1/calendar.ics", False),
            ("https://192.168.1.1/calendar.ics", False),
            ("https://10.0.0.1/calendar.ics", False),
        ],
    )
    def test_validate_url_for_ssrf(self, fetcher, url, expected):
        """Test SSRF validation for various URLs."""
        result = fetcher._validate_url_for_ssrf(url)

        assert result == expected

    def test_validate_url_malformed(self, fetcher):
        """Test validation of malformed URL."""
        result = fetcher._validate_url_for_ssrf("not-a-url")

        assert result is False

    def test_validate_url_encoded_localhost(self, fetcher):
        """Test validation catches encoded localhost attempts."""
        # 127.0.0.1 as decimal: 2130706433
        result = fetcher._validate_url_for_ssrf("http://2130706433/test")

        assert result is False

    def test_validate_url_hex_localhost(self, fetcher):
        """Test validation catches hex-encoded localhost."""
        # 127.0.0.1 as hex: 0x7f000001
        result = fetcher._validate_url_for_ssrf("http://0x7f000001/test")

        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_ics_success(self, fetcher, mock_ics_source, mock_http_response):
        """Test successful ICS fetch."""
        mock_http_response.text = "Mock ICS content"

        with patch.object(fetcher, "_validate_url_for_ssrf", return_value=True), patch.object(
            fetcher, "_make_request_with_retry", return_value=mock_http_response
        ):

            result = await fetcher.fetch_ics(mock_ics_source)

            assert result.success is True
            assert result.content == "Mock ICS content"
            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_fetch_ics_ssrf_blocked(self, fetcher, mock_ics_source):
        """Test ICS fetch blocked by SSRF protection."""
        with patch.object(fetcher, "_validate_url_for_ssrf", return_value=False):

            result = await fetcher.fetch_ics(mock_ics_source)

            assert result.success is False
            assert result.status_code == 403
            assert "security reasons" in result.error_message

    @pytest.mark.asyncio
    async def test_fetch_ics_timeout(self, fetcher, mock_ics_source):
        """Test ICS fetch with timeout."""
        import httpx

        with patch.object(fetcher, "_validate_url_for_ssrf", return_value=True), patch.object(
            fetcher, "_make_request_with_retry", side_effect=httpx.TimeoutException("Timeout")
        ):

            result = await fetcher.fetch_ics(mock_ics_source)

            assert result.success is False
            assert "timeout" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_fetch_ics_auth_error(self, fetcher, mock_ics_source):
        """Test ICS fetch with authentication error."""
        import httpx

        auth_error_response = MagicMock()
        auth_error_response.status_code = 401
        auth_error_response.reason_phrase = "Unauthorized"

        with patch.object(fetcher, "_validate_url_for_ssrf", return_value=True), patch.object(
            fetcher,
            "_make_request_with_retry",
            side_effect=httpx.HTTPStatusError(
                "Auth failed", request=MagicMock(), response=auth_error_response
            ),
        ), pytest.raises(ICSAuthError):

            await fetcher.fetch_ics(mock_ics_source)

    @pytest.mark.asyncio
    async def test_fetch_ics_network_error(self, fetcher, mock_ics_source):
        """Test ICS fetch with network error."""
        import httpx

        with patch.object(fetcher, "_validate_url_for_ssrf", return_value=True), patch.object(
            fetcher, "_make_request_with_retry", side_effect=httpx.NetworkError("Network error")
        ), pytest.raises(ICSNetworkError):

            await fetcher.fetch_ics(mock_ics_source)

    @pytest.mark.asyncio
    async def test_make_request_with_retry_success_first_attempt(self, fetcher, mock_http_response):
        """Test successful request on first attempt."""
        fetcher.client = AsyncMock()
        fetcher.client.get.return_value = mock_http_response

        result = await fetcher._make_request_with_retry("https://example.com", {}, 10, True)

        assert result == mock_http_response
        fetcher.client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_with_retry_success_after_retry(
        self, fetcher, mock_http_response, test_settings
    ):
        """Test successful request after retry."""
        import httpx

        test_settings.max_retries = 1
        fetcher.client = AsyncMock()

        # First call fails, second succeeds
        fetcher.client.get.side_effect = [httpx.TimeoutException("Timeout"), mock_http_response]

        with patch("asyncio.sleep"):  # Speed up test
            result = await fetcher._make_request_with_retry("https://example.com", {}, 10, True)

        assert result == mock_http_response
        assert fetcher.client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_make_request_with_retry_max_retries_exceeded(self, fetcher, test_settings):
        """Test request fails after max retries."""
        import httpx

        test_settings.max_retries = 1
        fetcher.client = AsyncMock()
        fetcher.client.get.side_effect = httpx.TimeoutException("Timeout")

        with patch("asyncio.sleep"), pytest.raises(httpx.TimeoutException):

            await fetcher._make_request_with_retry("https://example.com", {}, 10, True)

    @pytest.mark.asyncio
    async def test_make_request_with_retry_http_error_no_retry(self, fetcher):
        """Test HTTP errors are not retried."""
        import httpx

        fetcher.client = AsyncMock()

        error_response = MagicMock()
        error_response.status_code = 404

        fetcher.client.get.side_effect = httpx.HTTPStatusError(
            "Not found", request=MagicMock(), response=error_response
        )

        with pytest.raises(httpx.HTTPStatusError):
            await fetcher._make_request_with_retry("https://example.com", {}, 10, True)

        # Should only try once for HTTP errors
        fetcher.client.get.assert_called_once()

    def test_create_response_success(self, fetcher, mock_http_response):
        """Test creating response from successful HTTP response."""
        mock_http_response.text = "Mock ICS content"
        mock_http_response.headers = {"content-type": "text/calendar", "etag": "123"}

        result = fetcher._create_response(mock_http_response)

        assert result.success is True
        assert result.content == "Mock ICS content"
        assert result.etag == "123"

    def test_create_response_304_not_modified(self, fetcher):
        """Test creating response for 304 Not Modified."""
        mock_response = MagicMock()
        mock_response.status_code = 304
        mock_response.headers = {"etag": "123"}

        result = fetcher._create_response(mock_response)

        assert result.success is True
        assert result.status_code == 304
        assert result.content is None

    def test_create_response_empty_content(self, fetcher):
        """Test creating response with empty content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.headers = {}

        result = fetcher._create_response(mock_response)

        assert result.success is False
        assert "Empty content" in result.error_message

    def test_create_response_invalid_content_type(self, fetcher):
        """Test creating response with unexpected content type."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Some content"
        mock_response.headers = {"content-type": "text/html"}

        result = fetcher._create_response(mock_response)

        # Should still create response but log warning
        assert result.success is True
        assert result.content == "Some content"

    def test_create_response_missing_ics_markers(self, fetcher):
        """Test creating response without ICS markers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Not ICS content"
        mock_response.headers = {"content-type": "text/calendar"}

        result = fetcher._create_response(mock_response)

        # Should still create response but log warning
        assert result.success is True
        assert result.content == "Not ICS content"

    @pytest.mark.asyncio
    async def test_test_connection_success_head(self, fetcher, mock_ics_source):
        """Test successful connection test with HEAD request."""
        # Mock the client and prevent _ensure_client from replacing it
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.head = AsyncMock(return_value=mock_response)

        # Patch _ensure_client to prevent real client creation
        with patch.object(fetcher, "_ensure_client", new_callable=AsyncMock):
            fetcher.client = mock_client

            result = await fetcher.test_connection(mock_ics_source)

            assert result is True
            mock_client.head.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_head_not_allowed_fallback_get(self, fetcher, mock_ics_source):
        """Test connection test falls back to GET when HEAD not allowed."""
        # Mock the client and prevent _ensure_client from replacing it
        mock_client = AsyncMock()
        head_response = MagicMock()
        head_response.status_code = 405
        mock_client.head = AsyncMock(return_value=head_response)

        # Patch _ensure_client to prevent real client creation
        with patch.object(fetcher, "_ensure_client", new_callable=AsyncMock), patch.object(
            fetcher, "fetch_ics"
        ) as mock_fetch:

            fetcher.client = mock_client
            mock_fetch.return_value = MagicMock(success=True)

            result = await fetcher.test_connection(mock_ics_source)

            assert result is True
            mock_client.head.assert_called_once()
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, fetcher, mock_ics_source):
        """Test connection test failure."""
        fetcher.client = AsyncMock()
        fetcher.client.head.side_effect = Exception("Connection failed")

        result = await fetcher.test_connection(mock_ics_source)

        assert result is False

    def test_get_conditional_headers_with_etag(self, fetcher):
        """Test getting conditional headers with ETag."""
        headers = fetcher.get_conditional_headers(etag='"123"', last_modified=None)

        assert headers["If-None-Match"] == '"123"'
        assert "If-Modified-Since" not in headers

    def test_get_conditional_headers_with_last_modified(self, fetcher):
        """Test getting conditional headers with Last-Modified."""
        headers = fetcher.get_conditional_headers(
            etag=None, last_modified="Wed, 21 Oct 2015 07:28:00 GMT"
        )

        assert headers["If-Modified-Since"] == "Wed, 21 Oct 2015 07:28:00 GMT"
        assert "If-None-Match" not in headers

    def test_get_conditional_headers_with_both(self, fetcher):
        """Test getting conditional headers with both ETag and Last-Modified."""
        headers = fetcher.get_conditional_headers(
            etag='"123"', last_modified="Wed, 21 Oct 2015 07:28:00 GMT"
        )

        assert headers["If-None-Match"] == '"123"'
        assert headers["If-Modified-Since"] == "Wed, 21 Oct 2015 07:28:00 GMT"

    def test_get_conditional_headers_empty(self, fetcher):
        """Test getting conditional headers when no values provided."""
        headers = fetcher.get_conditional_headers()

        assert headers == {}


@pytest.mark.unit
class TestICSFetcherSecurity:
    """Security-focused ICS fetcher tests."""

    @pytest.fixture
    def fetcher(self, test_settings):
        """Create ICS fetcher instance."""
        return ICSFetcher(test_settings)

    @pytest.mark.parametrize(
        "malicious_url",
        [
            "http://localhost:8080/internal",
            "https://127.0.0.1/admin",
            "http://192.168.1.1/config",
            "https://10.0.0.1/secret",
            "http://169.254.169.254/metadata",  # AWS metadata
            "ftp://example.com/file",
            "file:///etc/passwd",
            "ldap://internal.server/",
        ],
    )
    def test_ssrf_protection_blocks_malicious_urls(self, fetcher, malicious_url):
        """Test SSRF protection blocks various malicious URLs."""
        result = fetcher._validate_url_for_ssrf(malicious_url)

        assert result is False

    def test_ssrf_protection_allows_safe_urls(self, fetcher):
        """Test SSRF protection allows safe external URLs."""
        safe_urls = [
            "https://calendar.google.com/calendar.ics",
            "http://example.com/public/calendar.ics",
            "https://outlook.office365.com/owa/calendar.ics",
        ]

        for url in safe_urls:
            result = fetcher._validate_url_for_ssrf(url)
            assert result is True, f"URL should be allowed: {url}"
