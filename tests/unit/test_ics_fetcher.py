"""Consolidated ICS fetcher tests combining comprehensive coverage with optimized critical paths."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from calendarbot.ics.exceptions import ICSAuthError, ICSFetchError, ICSNetworkError
from calendarbot.ics.fetcher import ICSFetcher
from calendarbot.ics.models import AuthType, ICSAuth, ICSSource
from tests.fixtures.mock_ics_data import ICSDataFactory, MockHTTPResponses, SSRFTestCases
from tests.fixtures.mock_servers import MockICSServer


@pytest.fixture
def mock_ics_source():
    """Create mock ICS source for testing."""
    return ICSSource(
        name="test_source",
        url="https://example.com/calendar.ics",
        auth=ICSAuth(),
        timeout=10,
        validate_ssl=True,
        custom_headers={},
    )


@pytest.mark.unit
@pytest.mark.critical_path
class TestICSFetcherCore:
    """Core ICS fetcher functionality tests with critical path coverage."""

    @pytest_asyncio.fixture
    async def ics_fetcher(self, test_settings):
        """Create an ICS fetcher for testing."""
        fetcher = ICSFetcher(test_settings)
        yield fetcher
        await fetcher._close_client()

    @pytest.fixture
    def fetcher(self, test_settings):
        """Create ICS fetcher instance (optimized fixture)."""
        return ICSFetcher(test_settings)

    @pytest_asyncio.fixture
    async def basic_ics_source(self):
        """Create a basic ICS source for testing."""
        return ICSSource(
            name="basic_test_source",
            url="https://example.com/calendar.ics",
            auth=ICSAuth(),
            timeout=10,
            validate_ssl=True,
            custom_headers={},
        )

    @pytest.mark.asyncio
    async def test_fetcher_initialization(self, test_settings):
        """Test ICS fetcher initialization."""
        fetcher = ICSFetcher(test_settings)

        assert fetcher.settings == test_settings
        assert fetcher.client is None
        assert fetcher.security_logger is not None

    def test_fetcher_initialization_optimized(self, fetcher, test_settings):
        """Test fetcher initializes correctly (optimized version)."""
        assert fetcher.settings == test_settings
        assert fetcher.client is None
        assert fetcher.security_logger is not None

    @pytest.mark.asyncio
    async def test_client_creation(self, ics_fetcher):
        """Test HTTP client creation and configuration."""
        await ics_fetcher._ensure_client()

        assert ics_fetcher.client is not None
        assert not ics_fetcher.client.is_closed

        # Check client configuration
        assert ics_fetcher.client.timeout.connect == 10.0
        assert ics_fetcher.client.timeout.read == ics_fetcher.settings.request_timeout
        assert ics_fetcher.client.follow_redirects is True
        # Note: httpx.AsyncClient doesn't have a verify attribute directly accessible
        # SSL verification is handled internally through the client configuration

    @pytest.mark.asyncio
    async def test_ensure_client_creates_client(self, fetcher):
        """Test client creation (optimized version)."""
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
    async def test_client_headers(self, ics_fetcher):
        """Test that proper headers are set on HTTP client."""
        await ics_fetcher._ensure_client()

        headers = ics_fetcher.client.headers
        assert "User-Agent" in headers
        assert headers["User-Agent"].startswith(ics_fetcher.settings.app_name)
        assert headers["Accept"] == "text/calendar, text/plain, */*"
        assert headers["Accept-Charset"] == "utf-8"
        assert headers["Cache-Control"] == "no-cache"

    @pytest.mark.asyncio
    async def test_client_cleanup(self, ics_fetcher):
        """Test HTTP client cleanup."""
        await ics_fetcher._ensure_client()
        assert ics_fetcher.client is not None

        await ics_fetcher._close_client()
        assert ics_fetcher.client.is_closed

    @pytest.mark.asyncio
    async def test_close_client_when_exists(self, fetcher):
        """Test closing existing client (optimized version)."""
        await fetcher._ensure_client()
        assert not fetcher.client.is_closed

        await fetcher._close_client()

        assert fetcher.client.is_closed

    @pytest.mark.asyncio
    async def test_close_client_when_none(self, fetcher):
        """Test closing client when none exists."""
        # Should not raise exception
        await fetcher._close_client()

    @pytest.mark.asyncio
    async def test_context_manager(self, test_settings):
        """Test ICS fetcher as async context manager."""
        async with ICSFetcher(test_settings) as fetcher:
            assert fetcher.client is not None
            assert not fetcher.client.is_closed

        # Client should be closed after exiting context
        assert fetcher.client.is_closed

    @pytest.mark.asyncio
    async def test_context_manager_entry_exit(self, fetcher):
        """Test async context manager functionality (optimized version)."""
        async with fetcher as f:
            assert f is fetcher
            assert fetcher.client is not None

        # Client should be closed after exit
        assert fetcher.client.is_closed


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.critical_path
class TestSSRFProtection:
    """Test suite for SSRF protection in ICS fetcher."""

    @pytest_asyncio.fixture
    async def ics_fetcher(self, test_settings):
        """Create an ICS fetcher for testing."""
        fetcher = ICSFetcher(test_settings)
        yield fetcher
        await fetcher._close_client()

    @pytest.fixture
    def fetcher(self, test_settings):
        """Create ICS fetcher instance (optimized fixture)."""
        return ICSFetcher(test_settings)

    @pytest.mark.parametrize("malicious_url", SSRFTestCases.MALICIOUS_URLS)
    @pytest.mark.asyncio
    async def test_ssrf_protection_blocks_malicious_urls(self, ics_fetcher, malicious_url):
        """Test that SSRF protection blocks malicious URLs."""
        is_safe = ics_fetcher._validate_url_for_ssrf(malicious_url)
        assert is_safe is False, f"URL should be blocked: {malicious_url}"

    @pytest.mark.parametrize("safe_url", SSRFTestCases.SAFE_URLS)
    @pytest.mark.asyncio
    async def test_ssrf_protection_allows_safe_urls(self, ics_fetcher, safe_url):
        """Test that SSRF protection allows safe URLs."""
        is_safe = ics_fetcher._validate_url_for_ssrf(safe_url)
        assert is_safe is True, f"URL should be allowed: {safe_url}"

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
    def test_validate_url_for_ssrf_optimized(self, fetcher, url, expected):
        """Test SSRF validation for various URLs (optimized version)."""
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
    def test_ssrf_protection_blocks_malicious_urls_optimized(self, fetcher, malicious_url):
        """Test SSRF protection blocks various malicious URLs (optimized version)."""
        result = fetcher._validate_url_for_ssrf(malicious_url)

        assert result is False

    def test_ssrf_protection_allows_safe_urls_optimized(self, fetcher):
        """Test SSRF protection allows safe external URLs (optimized version)."""
        safe_urls = [
            "https://calendar.google.com/calendar.ics",
            "http://example.com/public/calendar.ics",
            "https://outlook.office365.com/owa/calendar.ics",
        ]

        for url in safe_urls:
            result = fetcher._validate_url_for_ssrf(url)
            assert result is True, f"URL should be allowed: {url}"

    @pytest.mark.asyncio
    async def test_ssrf_protection_blocks_fetch(self, ics_fetcher):
        """Test that fetch_ics blocks requests to malicious URLs."""
        malicious_source = ICSSource(
            name="Malicious Source",  # Add required name field
            url="http://localhost/internal",
            auth=ICSAuth(),
            timeout=10,
        )

        response = await ics_fetcher.fetch_ics(malicious_source)

        assert response.success is False
        assert response.status_code == 403
        assert "security reasons" in response.error_message

    @pytest.mark.asyncio
    async def test_ssrf_protection_logs_security_events(self, ics_fetcher):
        """Test that SSRF protection logs security events."""
        with patch.object(ics_fetcher.security_logger, "log_event") as mock_log:
            ics_fetcher._validate_url_for_ssrf("http://127.0.0.1/")

            # Should log a security violation
            mock_log.assert_called_once()
            event = mock_log.call_args[0][0]
            assert "ssrf_attempt" in event.details["violation_type"]

    @pytest.mark.asyncio
    async def test_invalid_url_handling(self, ics_fetcher):
        """Test handling of invalid URLs."""
        invalid_urls = ["not-a-url", "ftp://invalid.scheme/", "javascript:alert('xss')", "", None]

        for invalid_url in invalid_urls:
            if invalid_url is not None:
                is_safe = ics_fetcher._validate_url_for_ssrf(invalid_url)
                assert is_safe is False, f"Invalid URL should be blocked: {invalid_url}"


@pytest.mark.unit
class TestICSFetching:
    """Test suite for ICS content fetching."""

    @pytest_asyncio.fixture
    async def ics_fetcher(self, test_settings):
        """Create an ICS fetcher for testing."""
        fetcher = ICSFetcher(test_settings)
        yield fetcher
        await fetcher._close_client()

    @pytest.fixture
    def fetcher(self, test_settings):
        """Create ICS fetcher instance (optimized fixture)."""
        return ICSFetcher(test_settings)

    @pytest_asyncio.fixture
    async def mock_ics_server(self):
        """Create a mock ICS server."""
        server = MockICSServer()
        ics_content = ICSDataFactory.create_basic_ics(2)
        server.set_response("/test.ics", ics_content)
        server.start()
        yield server
        server.stop()

    @pytest.mark.asyncio
    async def test_successful_ics_fetch(self, ics_fetcher, mock_ics_server):
        """Test successful ICS content fetching."""
        source = ICSSource(
            name="Test Calendar", url=f"{mock_ics_server.url}/test.ics", auth=ICSAuth(), timeout=10
        )

        # Mock SSRF validation to allow test server
        with patch.object(ics_fetcher, "_validate_url_for_ssrf", return_value=True):
            response = await ics_fetcher.fetch_ics(source)

        assert response.success is True
        assert response.status_code == 200
        assert "BEGIN:VCALENDAR" in response.content
        # Check Content-Type exists and is correct (case insensitive)
        content_type = response.headers.get("Content-Type") or response.headers.get("content-type")
        assert content_type == "text/calendar"
        assert mock_ics_server.get_request_count() == 1

    @pytest.mark.asyncio
    async def test_fetch_ics_success_optimized(self, fetcher, mock_ics_source, mock_http_response):
        """Test successful ICS fetch (optimized version)."""
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
    async def test_fetch_with_conditional_headers(self, ics_fetcher, mock_ics_server):
        """Test ICS fetching with conditional headers."""
        # Set up server to return 304 Not Modified
        mock_ics_server.set_not_modified_response("/conditional.ics")

        source = ICSSource(
            name="Test Calendar",
            url=f"{mock_ics_server.url}/conditional.ics",
            auth=ICSAuth(),
            timeout=10,
        )

        conditional_headers = {
            "If-None-Match": '"12345"',
            "If-Modified-Since": "Wed, 01 Jan 2025 12:00:00 GMT",
        }

        # Mock SSRF validation to allow test server
        with patch.object(ics_fetcher, "_validate_url_for_ssrf", return_value=True):
            response = await ics_fetcher.fetch_ics(source, conditional_headers)

        assert response.success is True
        assert response.status_code == 304
        # 304 responses typically have no content
        assert response.content is None or response.content == ""

    @pytest.mark.asyncio
    async def test_authentication_required(self, ics_fetcher, mock_ics_server):
        """Test handling of authentication required responses."""
        mock_ics_server.set_auth_required_response("/auth.ics")

        source = ICSSource(
            name="Test Calendar",
            url=f"{mock_ics_server.url}/auth.ics",
            auth=ICSAuth(),  # No credentials
            timeout=10,
        )

        # Mock SSRF validation to allow test server
        with patch.object(ics_fetcher, "_validate_url_for_ssrf", return_value=True):
            with pytest.raises(ICSAuthError) as exc_info:
                await ics_fetcher.fetch_ics(source)

        assert exc_info.value.status_code == 401
        assert "Authentication failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_ics_auth_error_optimized(self, fetcher, mock_ics_source):
        """Test ICS fetch with authentication error (optimized version)."""
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
    async def test_basic_authentication(self, ics_fetcher):
        """Test basic authentication handling."""
        auth = ICSAuth(type=AuthType.BASIC, username="test", password="pass")
        headers = auth.get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

        # Decode and verify credentials
        import base64

        encoded_creds = headers["Authorization"].split(" ")[1]
        decoded_creds = base64.b64decode(encoded_creds).decode()
        assert decoded_creds == "test:pass"

    @pytest.mark.asyncio
    async def test_bearer_authentication(self, ics_fetcher):
        """Test bearer token authentication."""
        auth = ICSAuth(type=AuthType.BEARER, bearer_token="test-token-123")
        headers = auth.get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-token-123"

    @pytest.mark.asyncio
    async def test_timeout_handling(self, ics_fetcher, mock_ics_server):
        """Test timeout handling during fetch."""
        # Set up server with long delay
        mock_ics_server.set_timeout_response("/timeout.ics", timeout_duration=1)

        source = ICSSource(
            name="Test Calendar",
            url=f"{mock_ics_server.url}/timeout.ics",
            auth=ICSAuth(),
            timeout=1,  # Use integer timeout - short timeout
        )

        # Mock SSRF validation to allow test server
        with patch.object(ics_fetcher, "_validate_url_for_ssrf", return_value=True):
            # The mock server disconnection causes an ICSFetchError instead of timeout
            with pytest.raises(ICSFetchError) as exc_info:
                await ics_fetcher.fetch_ics(source)

            # Check that it's related to server disconnection/timeout behavior
            assert (
                "Server disconnected" in str(exc_info.value)
                or "timeout" in str(exc_info.value).lower()
            )

    @pytest.mark.asyncio
    async def test_fetch_ics_timeout_optimized(self, fetcher, mock_ics_source):
        """Test ICS fetch with timeout (optimized version)."""
        import httpx

        with patch.object(fetcher, "_validate_url_for_ssrf", return_value=True), patch.object(
            fetcher, "_make_request_with_retry", side_effect=httpx.TimeoutException("Timeout")
        ):

            result = await fetcher.fetch_ics(mock_ics_source)

            assert result.success is False
            assert "timeout" in result.error_message.lower()

    @patch("httpx.AsyncClient.get")
    @pytest.mark.asyncio
    async def test_network_error_handling(self, mock_get, ics_fetcher):
        """Test network error handling."""
        # Simulate network error
        mock_get.side_effect = httpx.NetworkError("Connection failed")

        source = ICSSource(
            name="Test Calendar", url="https://example.com/test.ics", auth=ICSAuth(), timeout=10
        )

        with pytest.raises(ICSNetworkError):
            await ics_fetcher.fetch_ics(source)

    @pytest.mark.asyncio
    async def test_fetch_ics_network_error_optimized(self, fetcher, mock_ics_source):
        """Test ICS fetch with network error (optimized version)."""
        import httpx

        with patch.object(fetcher, "_validate_url_for_ssrf", return_value=True), patch.object(
            fetcher, "_make_request_with_retry", side_effect=httpx.NetworkError("Network error")
        ), pytest.raises(ICSNetworkError):

            await fetcher.fetch_ics(mock_ics_source)

    @pytest.mark.asyncio
    async def test_retry_logic(self, ics_fetcher):
        """Test retry logic for failed requests."""
        # Ensure client is initialized first
        await ics_fetcher._ensure_client()

        with patch.object(ics_fetcher.client, "get") as mock_get:
            # First two calls fail, third succeeds
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = ICSDataFactory.create_basic_ics(1)
            mock_response.headers = {"Content-Type": "text/calendar"}
            mock_response.raise_for_status = AsyncMock()

            mock_get.side_effect = [
                httpx.NetworkError("Network error"),
                httpx.NetworkError("Network error"),
                mock_response,
            ]

            source = ICSSource(
                name="Test Calendar", url="https://example.com/test.ics", auth=ICSAuth(), timeout=10
            )

            response = await ics_fetcher._make_request_with_retry(
                source.url, {}, source.timeout, source.validate_ssl
            )

            assert response.status_code == 200
            assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_make_request_with_retry_success_first_attempt(self, fetcher, mock_http_response):
        """Test successful request on first attempt (optimized version)."""
        fetcher.client = AsyncMock()
        fetcher.client.get.return_value = mock_http_response

        result = await fetcher._make_request_with_retry("https://example.com", {}, 10, True)

        assert result == mock_http_response
        fetcher.client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_with_retry_success_after_retry(
        self, fetcher, mock_http_response, test_settings
    ):
        """Test successful request after retry (optimized version)."""
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
        """Test request fails after max retries (optimized version)."""
        import httpx

        test_settings.max_retries = 1
        fetcher.client = AsyncMock()
        fetcher.client.get.side_effect = httpx.TimeoutException("Timeout")

        with patch("asyncio.sleep"), pytest.raises(httpx.TimeoutException):

            await fetcher._make_request_with_retry("https://example.com", {}, 10, True)

    @pytest.mark.asyncio
    async def test_make_request_with_retry_http_error_no_retry(self, fetcher):
        """Test HTTP errors are not retried (optimized version)."""
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

    @pytest.mark.asyncio
    async def test_connection_test_head_request(self, ics_fetcher, mock_ics_server):
        """Test connection testing with HEAD request."""
        source = ICSSource(
            name="Test Calendar", url=f"{mock_ics_server.url}/test.ics", auth=ICSAuth(), timeout=10
        )

        # Mock SSRF validation to allow test server
        with patch.object(ics_fetcher, "_validate_url_for_ssrf", return_value=True):
            success = await ics_fetcher.test_connection(source)
        assert success is True

    @pytest.mark.asyncio
    async def test_test_connection_success_head(self, fetcher, mock_ics_source):
        """Test successful connection test with HEAD request (optimized version)."""
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
    async def test_connection_test_fallback_to_get(self, ics_fetcher):
        """Test connection testing falls back to GET when HEAD fails."""
        with patch("httpx.AsyncClient.head") as mock_head, patch.object(
            ics_fetcher, "fetch_ics"
        ) as mock_fetch:

            # HEAD returns 405 Method Not Allowed
            mock_head.return_value.status_code = 405

            # fetch_ics returns success
            mock_response = MagicMock()
            mock_response.success = True
            mock_fetch.return_value = mock_response

            source = ICSSource(
                name="Test Calendar", url="https://example.com/test.ics", auth=ICSAuth(), timeout=10
            )

            success = await ics_fetcher.test_connection(source)

            assert success is True
            mock_head.assert_called_once()
            mock_fetch.assert_called_once_with(source)

    @pytest.mark.asyncio
    async def test_test_connection_head_not_allowed_fallback_get(self, fetcher, mock_ics_source):
        """Test connection test falls back to GET when HEAD not allowed (optimized version)."""
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
        """Test connection test failure (optimized version)."""
        fetcher.client = AsyncMock()
        fetcher.client.head.side_effect = Exception("Connection failed")

        result = await fetcher.test_connection(mock_ics_source)

        assert result is False

    @pytest.mark.asyncio
    async def test_conditional_headers_generation(self, ics_fetcher):
        """Test generation of conditional request headers."""
        etag = "12345"
        last_modified = "Wed, 01 Jan 2025 12:00:00 GMT"

        headers = ics_fetcher.get_conditional_headers(etag, last_modified)

        assert headers["If-None-Match"] == etag
        assert headers["If-Modified-Since"] == last_modified

    def test_get_conditional_headers_with_etag(self, fetcher):
        """Test getting conditional headers with ETag (optimized version)."""
        headers = fetcher.get_conditional_headers(etag='"123"', last_modified=None)

        assert headers["If-None-Match"] == '"123"'
        assert "If-Modified-Since" not in headers

    def test_get_conditional_headers_with_last_modified(self, fetcher):
        """Test getting conditional headers with Last-Modified (optimized version)."""
        headers = fetcher.get_conditional_headers(
            etag=None, last_modified="Wed, 21 Oct 2015 07:28:00 GMT"
        )

        assert headers["If-Modified-Since"] == "Wed, 21 Oct 2015 07:28:00 GMT"
        assert "If-None-Match" not in headers

    def test_get_conditional_headers_with_both(self, fetcher):
        """Test getting conditional headers with both ETag and Last-Modified (optimized version)."""
        headers = fetcher.get_conditional_headers(
            etag='"123"', last_modified="Wed, 21 Oct 2015 07:28:00 GMT"
        )

        assert headers["If-None-Match"] == '"123"'
        assert headers["If-Modified-Since"] == "Wed, 21 Oct 2015 07:28:00 GMT"

    @pytest.mark.asyncio
    async def test_empty_conditional_headers(self, ics_fetcher):
        """Test conditional headers with empty values."""
        headers = ics_fetcher.get_conditional_headers(None, None)
        assert headers == {}

        headers = ics_fetcher.get_conditional_headers("", "")
        assert headers == {}

    def test_get_conditional_headers_empty(self, fetcher):
        """Test getting conditional headers when no values provided (optimized version)."""
        headers = fetcher.get_conditional_headers()

        assert headers == {}

    def test_create_response_success(self, fetcher, mock_http_response):
        """Test creating response from successful HTTP response (optimized version)."""
        mock_http_response.text = "Mock ICS content"
        mock_http_response.headers = {"content-type": "text/calendar", "etag": "123"}

        result = fetcher._create_response(mock_http_response)

        assert result.success is True
        assert result.content == "Mock ICS content"
        assert result.etag == "123"

    def test_create_response_304_not_modified(self, fetcher):
        """Test creating response for 304 Not Modified (optimized version)."""
        mock_response = MagicMock()
        mock_response.status_code = 304
        mock_response.headers = {"etag": "123"}

        result = fetcher._create_response(mock_response)

        assert result.success is True
        assert result.status_code == 304
        assert result.content is None

    def test_create_response_empty_content(self, fetcher):
        """Test creating response with empty content (optimized version)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.headers = {}

        result = fetcher._create_response(mock_response)

        assert result.success is False
        assert "Empty content" in result.error_message

    def test_create_response_invalid_content_type(self, fetcher):
        """Test creating response with unexpected content type (optimized version)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Some content"
        mock_response.headers = {"content-type": "text/html"}

        result = fetcher._create_response(mock_response)

        # Should still create response but log warning
        assert result.success is True
        assert result.content == "Some content"

    def test_create_response_missing_ics_markers(self, fetcher):
        """Test creating response without ICS markers (optimized version)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Not ICS content"
        mock_response.headers = {"content-type": "text/calendar"}

        result = fetcher._create_response(mock_response)

        # Should still create response but log warning
        assert result.success is True
        assert result.content == "Not ICS content"

    @pytest.mark.asyncio
    async def test_content_validation(self, ics_fetcher):
        """Test ICS content validation."""
        with patch("httpx.AsyncClient.get") as mock_get:
            # Test empty content
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = ""
            mock_response.headers = {"Content-Type": "text/calendar"}
            mock_response.raise_for_status = AsyncMock()
            mock_get.return_value = mock_response

            source = ICSSource(
                name="Test Calendar",
                url="https://example.com/empty.ics",
                auth=ICSAuth(),
                timeout=10,
            )

            response = await ics_fetcher.fetch_ics(source)

            assert response.success is False
            assert "empty content" in response.error_message.lower()

    @pytest.mark.asyncio
    async def test_invalid_content_type_warning(self, ics_fetcher):
        """Test warning for unexpected content types."""
        with patch("httpx.AsyncClient.get") as mock_get:

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = ICSDataFactory.create_basic_ics(1)
            # Create a dict-like headers object that behaves like httpx headers (case-insensitive access)
            mock_headers = {"Content-Type": "text/html", "content-type": "text/html"}
            mock_response.headers = mock_headers
            mock_response.raise_for_status = AsyncMock()
            mock_get.return_value = mock_response

            source = ICSSource(
                name="Test Calendar", url="https://example.com/test.ics", auth=ICSAuth(), timeout=10
            )

            # Patch logger at the module level
            with patch("calendarbot.ics.fetcher.logger") as mock_logger:
                response = await ics_fetcher.fetch_ics(source)

                assert response.success is True  # Still succeeds
                # Check that warning was called with content type message
                mock_logger.warning.assert_called_once()
                call_args = mock_logger.warning.call_args[0][0]
                assert "content type" in call_args.lower() or "html" in call_args.lower()

    @pytest.mark.asyncio
    async def test_non_ics_content_warning(self, ics_fetcher):
        """Test warning for content that doesn't look like ICS."""
        with patch("httpx.AsyncClient.get") as mock_get, patch(
            "calendarbot.ics.fetcher.logger"
        ) as mock_logger:

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = "<html><body>Not ICS content</body></html>"
            mock_response.headers = {"Content-Type": "text/calendar"}
            mock_response.raise_for_status = AsyncMock()
            mock_get.return_value = mock_response

            source = ICSSource(
                name="Test Calendar", url="https://example.com/test.ics", auth=ICSAuth(), timeout=10
            )

            response = await ics_fetcher.fetch_ics(source)

            assert response.success is True  # Still succeeds
            mock_logger.warning.assert_called()  # But logs warning about format


@pytest.mark.unit
@pytest.mark.performance
class TestPerformance:
    """Performance-related tests for ICS fetcher."""

    @pytest_asyncio.fixture
    async def ics_fetcher(self, test_settings):
        """Create an ICS fetcher for testing."""
        fetcher = ICSFetcher(test_settings)
        yield fetcher
        await fetcher._close_client()

    @pytest.mark.asyncio
    async def test_large_ics_handling(self, ics_fetcher, performance_tracker):
        """Test handling of large ICS files."""
        large_ics = ICSDataFactory.create_large_ics(100)

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = large_ics
            mock_response.headers = {"Content-Type": "text/calendar"}
            mock_response.raise_for_status = AsyncMock()
            mock_get.return_value = mock_response

            source = ICSSource(
                name="Large Calendar",
                url="https://example.com/large.ics",
                auth=ICSAuth(),
                timeout=30,
            )

            performance_tracker.start_timer("large_fetch")
            response = await ics_fetcher.fetch_ics(source)
            performance_tracker.end_timer("large_fetch")

            assert response.success is True
            assert len(response.content) > 10000  # Ensure it's actually large

            # Should complete within reasonable time (5 seconds)
            performance_tracker.assert_performance("large_fetch", 5.0)

    @pytest.mark.asyncio
    async def test_concurrent_fetches(self, ics_fetcher):
        """Test concurrent ICS fetches don't interfere."""
        import asyncio

        sources = [
            ICSSource(
                name=f"Calendar {i}",
                url=f"https://example.com/test{i}.ics",
                auth=ICSAuth(),
                timeout=10,
            )
            for i in range(5)
        ]

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = ICSDataFactory.create_basic_ics(1)
            mock_response.headers = {"Content-Type": "text/calendar"}
            mock_response.raise_for_status = AsyncMock()
            mock_get.return_value = mock_response

            # Fetch all sources concurrently
            tasks = [ics_fetcher.fetch_ics(source) for source in sources]
            responses = await asyncio.gather(*tasks)

            # All should succeed
            assert all(response.success for response in responses)
            assert mock_get.call_count == len(sources)
