"""Unit tests for calendarbot_lite.lite_fetcher module (simplified for non-streaming implementation)."""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from calendarbot_lite.lite_fetcher import (
    LiteICSAuthError,
    LiteICSFetcher,
    LiteICSNetworkError,
    LiteSecurityEventLogger,
)
from calendarbot_lite.lite_models import LiteICSResponse, LiteICSSource


class TestSSRFProtection:
    """Tests for SSRF protection and URL validation."""

    @pytest.fixture
    def test_fetcher(self) -> LiteICSFetcher:
        """Create test fetcher with basic settings."""
        settings = SimpleNamespace(
            request_timeout=30,
            max_retries=3,
            retry_backoff_factor=1.5,
        )
        return LiteICSFetcher(settings)

    def test_validate_url_when_http_scheme_then_allows(self, test_fetcher: LiteICSFetcher) -> None:
        """Test _validate_url_for_ssrf allows HTTP URLs."""
        assert test_fetcher._validate_url_for_ssrf("http://example.com/calendar.ics") is True

    def test_validate_url_when_https_scheme_then_allows(self, test_fetcher: LiteICSFetcher) -> None:
        """Test _validate_url_for_ssrf allows HTTPS URLs."""
        assert test_fetcher._validate_url_for_ssrf("https://example.com/calendar.ics") is True

    def test_validate_url_when_ftp_scheme_then_blocks(self, test_fetcher: LiteICSFetcher) -> None:
        """Test _validate_url_for_ssrf blocks FTP URLs."""
        assert test_fetcher._validate_url_for_ssrf("ftp://example.com/file.ics") is False

    def test_validate_url_when_file_scheme_then_blocks(self, test_fetcher: LiteICSFetcher) -> None:
        """Test _validate_url_for_ssrf blocks file:// URLs."""
        assert test_fetcher._validate_url_for_ssrf("file:///etc/passwd") is False

    def test_validate_url_when_empty_hostname_then_blocks(
        self, test_fetcher: LiteICSFetcher
    ) -> None:
        """Test _validate_url_for_ssrf blocks URLs with empty hostnames."""
        assert test_fetcher._validate_url_for_ssrf("http:///calendar.ics") is False

    def test_validate_url_when_public_ip_then_allows(self, test_fetcher: LiteICSFetcher) -> None:
        """Test _validate_url_for_ssrf allows public IP addresses."""
        assert test_fetcher._validate_url_for_ssrf("http://8.8.8.8/calendar.ics") is True
        assert test_fetcher._validate_url_for_ssrf("http://1.1.1.1/calendar.ics") is True

    def test_validate_url_when_public_domain_then_allows(
        self, test_fetcher: LiteICSFetcher
    ) -> None:
        """Test _validate_url_for_ssrf allows public domain names."""
        assert test_fetcher._validate_url_for_ssrf("https://calendar.google.com/ics") is True
        assert test_fetcher._validate_url_for_ssrf("https://outlook.office365.com/calendar") is True

    def test_validate_url_when_malformed_url_then_blocks(
        self, test_fetcher: LiteICSFetcher
    ) -> None:
        """Test _validate_url_for_ssrf blocks malformed URLs."""
        assert test_fetcher._validate_url_for_ssrf("not-a-url") is False
        assert test_fetcher._validate_url_for_ssrf("") is False


class TestSecurityEventLogger:
    """Tests for LiteSecurityEventLogger."""

    @pytest.fixture
    def security_logger(self) -> LiteSecurityEventLogger:
        """Create test security logger."""
        return LiteSecurityEventLogger()

    def test_log_event_when_low_severity_then_logs_debug(
        self, security_logger: LiteSecurityEventLogger, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test log_event logs LOW severity events at DEBUG level."""
        # Set the module logger to DEBUG level to capture debug messages
        import logging
        logger = logging.getLogger("calendarbot_lite.lite_fetcher")
        logger.setLevel(logging.DEBUG)
        
        with caplog.at_level(logging.DEBUG, logger="calendarbot_lite.lite_fetcher"):
            event_data = {
                "event_type": "DATA_ACCESS",
                "severity": "LOW",
                "resource": "https://example.com",
                "details": {"description": "Test access"},
            }
            security_logger.log_event(event_data)

        assert "Security Event - Type: DATA_ACCESS" in caplog.text
        assert "Severity: LOW" in caplog.text

    def test_log_event_when_high_severity_then_logs_warning(
        self, security_logger: LiteSecurityEventLogger, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test log_event logs HIGH severity events at WARNING level."""
        with caplog.at_level(logging.WARNING):
            event_data = {
                "event_type": "SYSTEM_SECURITY_VIOLATION",
                "severity": "HIGH",
                "resource": "http://localhost",
                "details": {"description": "SSRF attempt blocked"},
            }
            security_logger.log_event(event_data)

        assert "Security Event - Type: SYSTEM_SECURITY_VIOLATION" in caplog.text
        assert "Severity: HIGH" in caplog.text

    def test_log_event_when_missing_fields_then_uses_defaults(
        self, security_logger: LiteSecurityEventLogger, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test log_event handles missing fields gracefully."""
        with caplog.at_level(logging.DEBUG):
            event_data = {}  # Empty event data
            security_logger.log_event(event_data)

        assert "Type: unknown" in caplog.text
        assert "Severity: unknown" in caplog.text
        assert "Resource: unknown" in caplog.text
        assert "Description: No description" in caplog.text


class TestHTTPRetryLogic:
    """Tests for HTTP retry logic and error handling."""

    @pytest.fixture
    def retry_settings(self) -> SimpleNamespace:
        """Create settings with retry configuration."""
        return SimpleNamespace(
            request_timeout=5,
            max_retries=2,
            retry_backoff_factor=2.0,
        )

    @pytest.fixture
    def mock_client_with_retries(self) -> Mock:
        """Create mock client for retry testing."""
        client = Mock()
        client.is_closed = False
        client.get = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_retry_logic_when_network_error_then_retries_with_backoff(
        self, retry_settings: SimpleNamespace, mock_client_with_retries: Mock
    ) -> None:
        """Test retry logic retries on network errors with exponential backoff."""
        # Setup mock to fail twice, then succeed
        network_error = httpx.NetworkError("Connection failed")
        success_response = Mock()
        success_response.status_code = 200
        success_response.headers = {"content-type": "text/calendar"}
        success_response.text = "BEGIN:VCALENDAR\nEND:VCALENDAR"
        success_response.raise_for_status = Mock()
        success_response.content = b"BEGIN:VCALENDAR\nEND:VCALENDAR"

        mock_client_with_retries.get.side_effect = [
            network_error,
            network_error,
            success_response,
        ]

        fetcher = LiteICSFetcher(retry_settings)
        fetcher.client = mock_client_with_retries

        with patch("asyncio.sleep") as mock_sleep:
            response = await fetcher._make_request_with_retry(
                "https://example.com/test.ics", {}, 30, True
            )

        # Should have made 3 attempts total
        assert mock_client_with_retries.get.call_count == 3

        # Should have slept twice (between retries)
        assert mock_sleep.call_count == 2

        # Should return successful response
        assert hasattr(response, "status_code")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_retry_logic_when_http_error_then_does_not_retry(
        self, retry_settings: SimpleNamespace, mock_client_with_retries: Mock
    ) -> None:
        """Test retry logic does not retry on HTTP status errors."""
        http_error = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=Mock(status_code=404)
        )
        mock_client_with_retries.get.side_effect = http_error

        fetcher = LiteICSFetcher(retry_settings)
        fetcher.client = mock_client_with_retries

        with pytest.raises(httpx.HTTPStatusError):
            await fetcher._make_request_with_retry(
                "https://example.com/test.ics", {}, 30, True
            )

        # Should only attempt once (no retries for HTTP errors)
        assert mock_client_with_retries.get.call_count == 1


class TestErrorHandling:
    """Tests for comprehensive error handling scenarios."""

    @pytest.fixture
    def error_test_settings(self) -> SimpleNamespace:
        """Create settings for error testing."""
        return SimpleNamespace(
            request_timeout=5,
            max_retries=1,
            retry_backoff_factor=1.0,
        )

    @pytest.mark.asyncio
    async def test_fetch_ics_when_ssrf_blocked_then_returns_error_response(
        self, error_test_settings: SimpleNamespace
    ) -> None:
        """Test fetch_ics returns error response when SSRF validation fails."""
        fetcher = LiteICSFetcher(error_test_settings)
        # Use file:// scheme which is blocked
        source = LiteICSSource(name="malicious", url="file:///etc/passwd")

        response = await fetcher.fetch_ics(source)

        assert response.success is False
        assert response.status_code == 403
        assert response.error_message is not None
        assert "URL blocked for security reasons" in response.error_message

    @pytest.mark.asyncio
    async def test_fetch_ics_when_401_error_then_raises_auth_error(
        self, error_test_settings: SimpleNamespace
    ) -> None:
        """Test fetch_ics raises LiteICSAuthError for 401 status."""
        fetcher = LiteICSFetcher(error_test_settings)

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.reason_phrase = "Unauthorized"

        http_error = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response
        )

        mock_client = Mock()
        mock_client.is_closed = False
        mock_client.get = AsyncMock(side_effect=http_error)

        fetcher.client = mock_client
        source = LiteICSSource(name="auth", url="https://protected.example.com/calendar.ics")

        with pytest.raises(LiteICSAuthError, match="Authentication failed"):
            await fetcher.fetch_ics(source)

    @pytest.mark.asyncio
    async def test_fetch_ics_when_network_error_then_raises_network_error(
        self, error_test_settings: SimpleNamespace
    ) -> None:
        """Test fetch_ics raises LiteICSNetworkError for network failures."""
        fetcher = LiteICSFetcher(error_test_settings)

        network_error = httpx.NetworkError("Connection refused")

        mock_client = Mock()
        mock_client.is_closed = False
        mock_client.get = AsyncMock(side_effect=network_error)

        fetcher.client = mock_client
        source = LiteICSSource(name="network", url="https://unreachable.example.com/calendar.ics")

        with pytest.raises(LiteICSNetworkError, match="Network error"):
            await fetcher.fetch_ics(source)

    def test_create_response_when_empty_content_then_returns_error(
        self, error_test_settings: SimpleNamespace
    ) -> None:
        """Test _create_response handles empty content gracefully."""
        fetcher = LiteICSFetcher(error_test_settings)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/calendar"}
        mock_response.text = ""  # Empty content

        response = fetcher._create_response(mock_response)

        assert response.success is False
        assert response.error_message is not None
        assert "Empty content received" in response.error_message

    def test_create_response_when_invalid_content_type_then_logs_warning(
        self, error_test_settings: SimpleNamespace, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test _create_response logs warning for unexpected content types."""
        fetcher = LiteICSFetcher(error_test_settings)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = "BEGIN:VCALENDAR\nEND:VCALENDAR"

        with caplog.at_level(logging.WARNING):
            response = fetcher._create_response(mock_response)

        assert "Unexpected content type: text/html" in caplog.text
        assert response.success is True  # Still processes if it contains ICS markers


class TestLiteICSFetcherMiscellaneous:
    """Tests for miscellaneous LiteICSFetcher functionality."""

    @pytest.fixture
    def basic_fetcher(self) -> LiteICSFetcher:
        """Create basic fetcher for testing."""
        settings = SimpleNamespace(
            request_timeout=30,
            max_retries=3,
            retry_backoff_factor=1.5,
        )
        return LiteICSFetcher(settings)

    def test_get_conditional_headers_when_etag_provided_then_includes_if_none_match(
        self, basic_fetcher: LiteICSFetcher
    ) -> None:
        """Test get_conditional_headers includes If-None-Match for ETag."""
        etag = '"abc123"'
        headers = basic_fetcher.get_conditional_headers(etag=etag)

        assert headers["If-None-Match"] == etag

    def test_get_conditional_headers_when_last_modified_provided_then_includes_if_modified_since(
        self, basic_fetcher: LiteICSFetcher
    ) -> None:
        """Test get_conditional_headers includes If-Modified-Since for Last-Modified."""
        last_modified = "Wed, 21 Oct 2015 07:28:00 GMT"
        headers = basic_fetcher.get_conditional_headers(last_modified=last_modified)

        assert headers["If-Modified-Since"] == last_modified

    def test_get_conditional_headers_when_both_provided_then_includes_both(
        self, basic_fetcher: LiteICSFetcher
    ) -> None:
        """Test get_conditional_headers includes both headers when provided."""
        etag = '"abc123"'
        last_modified = "Wed, 21 Oct 2015 07:28:00 GMT"
        headers = basic_fetcher.get_conditional_headers(etag=etag, last_modified=last_modified)

        assert headers["If-None-Match"] == etag
        assert headers["If-Modified-Since"] == last_modified

    def test_get_conditional_headers_when_none_provided_then_returns_empty(
        self, basic_fetcher: LiteICSFetcher
    ) -> None:
        """Test get_conditional_headers returns empty dict when no values provided."""
        headers = basic_fetcher.get_conditional_headers()

        assert headers == {}

    @pytest.mark.asyncio
    async def test_test_connection_when_head_successful_then_returns_true(
        self, basic_fetcher: LiteICSFetcher
    ) -> None:
        """Test test_connection returns True for successful HEAD request."""
        mock_client = AsyncMock()
        mock_client.head = AsyncMock()
        mock_client.head.return_value = Mock(status_code=200)

        # Patch _ensure_client to prevent real client creation
        with patch.object(basic_fetcher, "_ensure_client"):
            basic_fetcher.client = mock_client
            source = LiteICSSource(name="test", url="https://example.com/calendar.ics")

            result = await basic_fetcher.test_connection(source)

            assert result is True
            mock_client.head.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_when_head_405_then_tries_get(
        self, basic_fetcher: LiteICSFetcher
    ) -> None:
        """Test test_connection falls back to GET when HEAD returns 405."""
        mock_client = AsyncMock()
        mock_client.head = AsyncMock()
        mock_client.head.return_value = Mock(status_code=405)

        source = LiteICSSource(name="test", url="https://example.com/calendar.ics")

        # Mock both _ensure_client and fetch_ics
        with patch.object(basic_fetcher, "_ensure_client"), \
             patch.object(basic_fetcher, "fetch_ics") as mock_fetch:
            basic_fetcher.client = mock_client
            mock_fetch.return_value = LiteICSResponse(success=True)

            result = await basic_fetcher.test_connection(source)

            assert result is True
            mock_fetch.assert_called_once_with(source)

    def test_create_response_when_304_not_modified_then_handles_correctly(
        self, basic_fetcher: LiteICSFetcher
    ) -> None:
        """Test _create_response handles 304 Not Modified correctly."""
        mock_response = Mock()
        mock_response.status_code = 304
        mock_response.headers = {
            "etag": '"cached123"',
            "last-modified": "Wed, 21 Oct 2015 07:28:00 GMT",
        }

        response = basic_fetcher._create_response(mock_response)

        assert response.success is True
        assert response.status_code == 304
        assert response.etag == '"cached123"'
        assert response.last_modified == "Wed, 21 Oct 2015 07:28:00 GMT"
        assert response.content is None
