"""Unit tests for calendarbot_lite.lite_fetcher module (simplified for non-streaming implementation)."""

import logging
from types import SimpleNamespace
from typing import Any
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

pytestmark = pytest.mark.integration


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

    def test_log_validation_event_when_invalid_scheme_then_logs_blocked(
        self, test_fetcher: LiteICSFetcher
    ) -> None:
        """Test _log_validation_event logs blocked event for invalid URL scheme."""
        # Create a simple test double to record log_event calls
        logged_events = []

        class RecordingSecurityLogger:
            def log_event(self, event_data: dict[str, Any]) -> None:
                logged_events.append(event_data)

        # Replace security logger with test double
        test_fetcher.security_logger = RecordingSecurityLogger()  # type: ignore[assignment]

        # Call _validate_url_for_ssrf with FTP URL (non-HTTP scheme)
        result = test_fetcher._validate_url_for_ssrf("ftp://example.com/file.ics")

        # Verify validation failed
        assert result is False

        # Verify log_event was called once
        assert len(logged_events) == 1

        # Verify event structure and content
        event = logged_events[0]
        assert event["result"] == "blocked"
        assert event["event_type"] == "INPUT_VALIDATION_FAILURE"
        assert event["severity"] == "LOW"
        assert event["resource"] == "ftp://example.com/file.ics"
        assert event["action"] == "url_validation"
        assert "Invalid URL scheme" in event["details"]["description"]
        assert "ftp" in event["details"]["description"]

    def test_log_validation_event_when_missing_hostname_then_logs_blocked(
        self, test_fetcher: LiteICSFetcher
    ) -> None:
        """Test _log_validation_event logs blocked event for missing hostname."""
        logged_events = []

        class RecordingSecurityLogger:
            def log_event(self, event_data: dict[str, Any]) -> None:
                logged_events.append(event_data)

        test_fetcher.security_logger = RecordingSecurityLogger()  # type: ignore[assignment]

        # Call with URL missing hostname
        result = test_fetcher._validate_url_for_ssrf("http:///path")

        assert result is False
        assert len(logged_events) == 1

        event = logged_events[0]
        assert event["result"] == "blocked"
        assert event["event_type"] == "INPUT_VALIDATION_FAILURE"
        assert event["severity"] == "LOW"
        assert event["resource"] == "http:///path"
        assert event["action"] == "url_validation"
        assert "URL missing hostname" in event["details"]["description"]

    def test_log_validation_event_when_malformed_url_then_logs_error(
        self, test_fetcher: LiteICSFetcher, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test _log_validation_event logs error event when urlparse raises exception."""
        logged_events = []

        class RecordingSecurityLogger:
            def log_event(self, event_data: dict[str, Any]) -> None:
                logged_events.append(event_data)

        test_fetcher.security_logger = RecordingSecurityLogger()  # type: ignore[assignment]

        # Patch urlparse to simulate exception during URL parsing
        from unittest.mock import Mock

        mock_urlparse = Mock(side_effect=ValueError("Invalid URL format"))
        monkeypatch.setattr("calendarbot_lite.lite_fetcher.urlparse", mock_urlparse)

        # Call with any URL - urlparse will raise ValueError
        result = test_fetcher._validate_url_for_ssrf("http://example.com")

        assert result is False
        assert len(logged_events) == 1

        event = logged_events[0]
        assert event["result"] == "error"
        assert event["event_type"] == "INPUT_VALIDATION_FAILURE"
        assert event["severity"] == "LOW"
        assert event["resource"] == "http://example.com"
        assert event["action"] == "url_validation"
        assert "URL validation error" in event["details"]["description"]
        assert "Invalid URL format" in event["details"]["description"]

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
                "https://example.com/test.ics", {}, 30
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
            await fetcher._make_request_with_retry("https://example.com/test.ics", {}, 30)

        # Should only attempt once (no retries for HTTP errors)
        assert mock_client_with_retries.get.call_count == 1


class TestCalculateBackoff:
    """Tests for _calculate_backoff method."""

    @pytest.fixture
    def test_fetcher(self) -> LiteICSFetcher:
        """Create test fetcher with basic settings."""
        settings = SimpleNamespace(
            request_timeout=30,
            max_retries=3,
            retry_backoff_factor=1.5,
        )
        return LiteICSFetcher(settings)

    def test_calculate_backoff_when_normal_scenario_then_exponential_with_jitter(
        self, test_fetcher: LiteICSFetcher
    ) -> None:
        """Test _calculate_backoff calculates exponential backoff with jitter for normal scenarios."""
        backoff_factor = 1.5
        max_retries = 3

        # Test attempt 0
        result = test_fetcher._calculate_backoff(0, False, max_retries, backoff_factor)
        base = backoff_factor**0  # 1.0
        assert base * 1.1 <= result <= base * 1.3

        # Test attempt 1
        result = test_fetcher._calculate_backoff(1, False, max_retries, backoff_factor)
        base = backoff_factor**1  # 1.5
        assert base * 1.1 <= result <= base * 1.3

        # Test attempt 2
        result = test_fetcher._calculate_backoff(2, False, max_retries, backoff_factor)
        base = backoff_factor**2  # 2.25
        assert base * 1.1 <= result <= base * 1.3

    def test_calculate_backoff_when_corruption_detected_then_doubled_and_capped(
        self, test_fetcher: LiteICSFetcher
    ) -> None:
        """Test _calculate_backoff doubles backoff and applies 30s cap when corruption detected."""
        backoff_factor = 2.0
        max_retries = 3

        # Test with corruption detected - should double backoff
        result = test_fetcher._calculate_backoff(2, True, max_retries, backoff_factor)
        base = (backoff_factor**2) * 2  # 4.0 * 2 = 8.0
        expected_base = min(base, 30.0)
        assert expected_base * 1.1 <= result <= expected_base * 1.3

        # Test high attempt that would exceed cap
        result = test_fetcher._calculate_backoff(5, True, max_retries, backoff_factor)
        # backoff_factor^5 * 2 = 32 * 2 = 64, should be capped at 30
        assert 30.0 * 1.1 <= result <= 30.0 * 1.3

    def test_calculate_backoff_when_jitter_distribution_then_varies_within_bounds(
        self, test_fetcher: LiteICSFetcher
    ) -> None:
        """Test _calculate_backoff produces varied results within jitter bounds."""
        backoff_factor = 2.0
        max_retries = 3
        attempt = 1
        corruption_detected = False

        results = []
        for _ in range(100):
            result = test_fetcher._calculate_backoff(
                attempt, corruption_detected, max_retries, backoff_factor
            )
            results.append(result)

        # All results should be within jitter bounds
        base = backoff_factor**attempt  # 2.0
        min_expected = base * 1.1
        max_expected = base * 1.3

        for result in results:
            assert min_expected <= result <= max_expected

        # Results should vary (not all identical)
        unique_results = set(results)
        assert len(unique_results) > 1, "Backoff results should vary due to randomness"

    def test_calculate_backoff_when_zero_attempt_then_minimal_backoff(
        self, test_fetcher: LiteICSFetcher
    ) -> None:
        """Test _calculate_backoff produces minimal backoff for attempt 0."""
        backoff_factor = 1.5
        max_retries = 3

        result = test_fetcher._calculate_backoff(0, False, max_retries, backoff_factor)

        # Base backoff is backoff_factor^0 = 1.0
        # With jitter: 1.0 + (0.1 to 0.3) * 1.0 = 1.1 to 1.3
        assert 1.1 <= result <= 1.3


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

        http_error = httpx.HTTPStatusError("Unauthorized", request=Mock(), response=mock_response)

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
        with (
            patch.object(basic_fetcher, "_ensure_client"),
            patch.object(basic_fetcher, "fetch_ics") as mock_fetch,
        ):
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


@pytest.mark.asyncio
async def test_fetcher_uses_default_browser_headers() -> None:
    """
    Verify LiteICSFetcher.fetch_ics uses DEFAULT_BROWSER_HEADERS and that
    browser headers take precedence over per-request custom_headers on collisions.
    """
    from calendarbot_lite.lite_models import LiteICSSource

    settings = SimpleNamespace(request_timeout=30, max_retries=1, retry_backoff_factor=1.0)
    fetcher = LiteICSFetcher(settings)

    captured: dict = {}

    async def fake_get(*args, **kwargs):
        # Capture headers passed to HTTP client's get()
        captured["url"] = args[0] if args else kwargs.get("url")
        captured["headers"] = dict(kwargs.get("headers") or {})
        # Minimal response object compatible with fetcher expectations
        return SimpleNamespace(
            status_code=200,
            headers={"content-type": "text/calendar"},
            text="BEGIN:VCALENDAR\nEND:VCALENDAR",
            content=b"BEGIN:VCALENDAR\nEND:VCALENDAR",
            raise_for_status=lambda: None,
        )

    mock_client = Mock()
    mock_client.is_closed = False
    mock_client.get = AsyncMock(side_effect=fake_get)

    # Inject fake client
    fetcher.client = mock_client

    # Provide custom headers that collide with browser headers
    source = LiteICSSource(
        name="test",
        url="https://example.com/cal.ics",
        custom_headers={"Cache-Control": "client-cache", "User-Agent": "CustomAgent/1.0"},
    )

    response = await fetcher.fetch_ics(source)

    # Ensure fetch executed successfully and content returned
    assert response.success is True
    assert response.content is not None
    assert "BEGIN:VCALENDAR" in response.content

    captured_headers = captured["headers"]

    # All DEFAULT_BROWSER_HEADERS keys must be present
    from calendarbot_lite.http_client import DEFAULT_BROWSER_HEADERS as _DEFAULT

    for key in _DEFAULT:
        assert key in captured_headers, f"Missing browser header: {key}"

    # Colliding keys should be overridden by browser headers (browser precedence)
    assert captured_headers["Cache-Control"] == _DEFAULT["Cache-Control"]
    assert captured_headers["User-Agent"] == _DEFAULT["User-Agent"]


@pytest.mark.asyncio
async def test_fetcher_with_immutable_settings() -> None:
    """
    Verify LiteICSFetcher works with immutable settings objects that don't allow
    attribute assignment, confirming that the fetcher does not attempt to mutate settings.
    """
    from types import MappingProxyType

    # Create an immutable settings object without the expected attributes
    # Using MappingProxyType to ensure immutability
    base_settings = {}
    immutable_settings = MappingProxyType(base_settings)

    # Create fetcher with immutable settings - should not raise
    fetcher = LiteICSFetcher(immutable_settings)

    # Mock client to avoid real network calls
    mock_client = Mock()
    mock_client.is_closed = False
    mock_client.get = AsyncMock()
    mock_client.get.return_value = SimpleNamespace(
        status_code=200,
        headers={"content-type": "text/calendar"},
        text="BEGIN:VCALENDAR\nEND:VCALENDAR",
        content=b"BEGIN:VCALENDAR\nEND:VCALENDAR",
        raise_for_status=lambda: None,
    )

    fetcher.client = mock_client
    source = LiteICSSource(name="test", url="https://example.com/cal.ics")

    # Should use defaults (30s timeout, 3 retries, 1.5 backoff) without mutating settings
    response = await fetcher.fetch_ics(source)

    assert response.success is True
    assert response.content is not None
    assert "BEGIN:VCALENDAR" in response.content
    # Verify settings object was not mutated
    assert "request_timeout" not in base_settings
    assert "max_retries" not in base_settings
    assert "retry_backoff_factor" not in base_settings


@pytest.mark.asyncio
async def test_fetcher_with_partial_settings() -> None:
    """
    Verify LiteICSFetcher uses provided custom values and defaults for missing attributes.
    """
    # Create settings with only request_timeout, missing max_retries and retry_backoff_factor
    settings = SimpleNamespace(request_timeout=60)

    fetcher = LiteICSFetcher(settings)

    # Mock client
    mock_client = Mock()
    mock_client.is_closed = False

    # Track retry attempts
    call_count = 0

    async def failing_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.NetworkError("Connection failed")
        # Third attempt succeeds
        return SimpleNamespace(
            status_code=200,
            headers={"content-type": "text/calendar"},
            text="BEGIN:VCALENDAR\nEND:VCALENDAR",
            content=b"BEGIN:VCALENDAR\nEND:VCALENDAR",
            raise_for_status=lambda: None,
        )

    mock_client.get = AsyncMock(side_effect=failing_get)
    fetcher.client = mock_client

    source = LiteICSSource(name="test", url="https://example.com/cal.ics")

    with patch("asyncio.sleep"):
        response = await fetcher.fetch_ics(source)

    # Should use custom timeout (60) and defaults for retries (3) and backoff (1.5)
    assert response.success is True
    assert (
        call_count == 3
    )  # Default max_retries=3 means 1 initial + 3 retries = 4 total attempts, but we succeed on 3rd


@pytest.mark.asyncio
async def test_fetcher_with_all_custom_settings() -> None:
    """
    Verify LiteICSFetcher uses all custom settings values when provided.
    """
    # Create settings with all custom values
    settings = SimpleNamespace(
        request_timeout=120,
        max_retries=5,
        retry_backoff_factor=2.0,
    )

    fetcher = LiteICSFetcher(settings)

    # Mock client
    mock_client = Mock()
    mock_client.is_closed = False

    # Track retry attempts
    call_count = 0

    async def failing_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 4:
            raise httpx.NetworkError("Connection failed")
        # Fourth attempt succeeds
        return SimpleNamespace(
            status_code=200,
            headers={"content-type": "text/calendar"},
            text="BEGIN:VCALENDAR\nEND:VCALENDAR",
            content=b"BEGIN:VCALENDAR\nEND:VCALENDAR",
            raise_for_status=lambda: None,
        )

    mock_client.get = AsyncMock(side_effect=failing_get)
    fetcher.client = mock_client

    source = LiteICSSource(name="test", url="https://example.com/cal.ics")

    with patch("asyncio.sleep") as mock_sleep:
        response = await fetcher.fetch_ics(source)

    # Should use custom values: max_retries=5, retry_backoff_factor=2.0
    assert response.success is True
    assert call_count == 4  # 1 initial + 3 retries needed to succeed
    assert mock_sleep.call_count == 3  # 3 retries means 3 sleeps


@pytest.mark.asyncio
async def test_fetcher_merges_conditional_and_auth_headers() -> None:
    """
    Verify that conditional headers and authentication headers are merged with
    DEFAULT_BROWSER_HEADERS and preserved in the outgoing request.
    """
    from calendarbot_lite.http_client import DEFAULT_BROWSER_HEADERS
    from calendarbot_lite.lite_models import LiteAuthType, LiteICSAuth, LiteICSSource

    settings = SimpleNamespace(request_timeout=30, max_retries=1, retry_backoff_factor=1.0)
    fetcher = LiteICSFetcher(settings)

    captured: dict = {}

    async def fake_get(*args, **kwargs):
        captured["url"] = args[0] if args else kwargs.get("url")
        captured["headers"] = dict(kwargs.get("headers") or {})
        return SimpleNamespace(
            status_code=200,
            headers={"content-type": "text/calendar"},
            text="BEGIN:VCALENDAR\nEND:VCALENDAR",
            content=b"BEGIN:VCALENDAR\nEND:VCALENDAR",
            raise_for_status=lambda: None,
        )

    mock_client = Mock()
    mock_client.is_closed = False
    mock_client.get = AsyncMock(side_effect=fake_get)

    fetcher.client = mock_client

    auth = LiteICSAuth(type=LiteAuthType.BEARER, bearer_token="token123")
    source = LiteICSSource(name="auth-test", url="https://example.com/cal.ics", auth=auth)

    conditional_headers = {"If-None-Match": "etag123"}

    response = await fetcher.fetch_ics(source, conditional_headers=conditional_headers)

    assert response.success is True
    assert response.content is not None
    assert "BEGIN:VCALENDAR" in response.content

    headers = captured["headers"]

    # Auth header should be present and correct
    assert headers.get("Authorization") == "Bearer token123"

    # Conditional header should be preserved
    assert headers.get("If-None-Match") == "etag123"

    # Browser headers must be present
    for key in DEFAULT_BROWSER_HEADERS:
        assert key in headers, f"Missing browser header: {key}"


class TestSmokeTests:
    """Smoke tests to verify functionality is unchanged after removing dead code."""

    @pytest.mark.asyncio
    async def test_fetch_ics_smoke_test_successful_fetch(self) -> None:
        """Verify fetch_ics successfully fetches and returns ICS content."""
        settings = SimpleNamespace(request_timeout=30, max_retries=3, retry_backoff_factor=1.5)
        fetcher = LiteICSFetcher(settings)

        # Create fake successful response
        fake_response = SimpleNamespace(
            status_code=200,
            headers={"content-type": "text/calendar"},
            text="BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR",
            content=b"BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR",
            raise_for_status=lambda: None,
        )

        mock_client = Mock()
        mock_client.is_closed = False
        mock_client.get = AsyncMock(return_value=fake_response)

        fetcher.client = mock_client
        source = LiteICSSource(name="test", url="https://example.com/calendar.ics")

        response = await fetcher.fetch_ics(source)

        assert response.success is True
        assert response.content is not None
        assert "BEGIN:VCALENDAR" in response.content
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_fetch_ics_smoke_test_retry_behavior(self) -> None:
        """Verify fetch_ics retries on failure and eventually succeeds."""
        settings = SimpleNamespace(request_timeout=30, max_retries=3, retry_backoff_factor=1.5)
        fetcher = LiteICSFetcher(settings)

        # Create fake client that fails twice then succeeds on third attempt
        call_count = 0

        async def fake_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.NetworkError("Connection failed")
            # Third attempt succeeds
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "text/calendar"},
                text="BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR",
                content=b"BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR",
                raise_for_status=lambda: None,
            )

        mock_client = Mock()
        mock_client.is_closed = False
        mock_client.get = AsyncMock(side_effect=fake_get)

        fetcher.client = mock_client
        source = LiteICSSource(name="test", url="https://example.com/calendar.ics")

        with patch("asyncio.sleep"):
            response = await fetcher.fetch_ics(source)

        assert response.success is True
        assert call_count == 3
        assert response.content is not None
        assert "BEGIN:VCALENDAR" in response.content

    @pytest.mark.asyncio
    async def test_fetch_ics_smoke_test_timeout_handling(self) -> None:
        """Verify fetch_ics handles timeout gracefully."""
        settings = SimpleNamespace(request_timeout=5, max_retries=1, retry_backoff_factor=1.5)
        fetcher = LiteICSFetcher(settings)

        # Create fake client that raises timeout exception
        mock_client = Mock()
        mock_client.is_closed = False
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))

        fetcher.client = mock_client
        source = LiteICSSource(name="test", url="https://example.com/calendar.ics")

        with patch("asyncio.sleep"):
            response = await fetcher.fetch_ics(source)

        assert response.success is False
        assert response.error_message is not None
        assert "timeout" in response.error_message.lower()
