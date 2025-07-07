"""Unit tests for ICS fetcher and HTTP client functionality."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from calendarbot.ics.exceptions import ICSAuthError, ICSFetchError, ICSNetworkError
from calendarbot.ics.fetcher import ICSFetcher
from calendarbot.ics.models import ICSAuth, ICSSource
from tests.fixtures.mock_ics_data import ICSDataFactory, MockHTTPResponses, SSRFTestCases
from tests.fixtures.mock_servers import MockICSServer


@pytest.mark.unit
@pytest.mark.critical_path
class TestICSFetcher:
    """Test suite for ICS fetcher functionality."""

    @pytest_asyncio.fixture
    async def ics_fetcher(self, test_settings):
        """Create an ICS fetcher for testing."""
        fetcher = ICSFetcher(test_settings)
        yield fetcher
        await fetcher._close_client()

    @pytest_asyncio.fixture
    async def basic_ics_source(self):
        """Create a basic ICS source for testing."""
        return ICSSource(
            url="https://example.com/calendar.ics",
            auth=ICSAuth(),
            timeout=10,
            validate_ssl=True,
            custom_headers={},
            max_retries=2,
            retry_backoff=1.0,
        )

    @pytest.mark.asyncio
    async def test_fetcher_initialization(self, test_settings):
        """Test ICS fetcher initialization."""
        fetcher = ICSFetcher(test_settings)

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
    async def test_context_manager(self, test_settings):
        """Test ICS fetcher as async context manager."""
        async with ICSFetcher(test_settings) as fetcher:
            assert fetcher.client is not None
            assert not fetcher.client.is_closed

        # Client should be closed after exiting context
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
    async def test_basic_authentication(self, ics_fetcher):
        """Test basic authentication handling."""
        auth = ICSAuth(type="basic", username="test", password="pass")
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
        auth = ICSAuth(type="bearer", bearer_token="test-token-123")
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
    async def test_conditional_headers_generation(self, ics_fetcher):
        """Test generation of conditional request headers."""
        etag = "12345"
        last_modified = "Wed, 01 Jan 2025 12:00:00 GMT"

        headers = ics_fetcher.get_conditional_headers(etag, last_modified)

        assert headers["If-None-Match"] == etag
        assert headers["If-Modified-Since"] == last_modified

    @pytest.mark.asyncio
    async def test_empty_conditional_headers(self, ics_fetcher):
        """Test conditional headers with empty values."""
        headers = ics_fetcher.get_conditional_headers(None, None)
        assert headers == {}

        headers = ics_fetcher.get_conditional_headers("", "")
        assert headers == {}

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
