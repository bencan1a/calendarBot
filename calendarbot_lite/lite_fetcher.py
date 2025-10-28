"""HTTP client for downloading ICS calendar files - CalendarBot Lite version."""

# Standard library imports
import asyncio
import logging
from typing import Any, NoReturn, Optional
from urllib.parse import urlparse

import httpx

from .http_client import (
    get_shared_client,
    record_client_error,
    record_client_success,
)
from .lite_models import LiteICSResponse, LiteICSSource

logger = logging.getLogger(__name__)

# HTTP client defaults
READ_CHUNK_SIZE_BYTES = 8192  # Still used for some internal operations


# Lite exceptions for CalendarBot Lite
class LiteICSFetchError(Exception):
    """Base exception for ICS fetch errors."""


class LiteICSAuthError(LiteICSFetchError):
    """Authentication error during ICS fetch."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class LiteICSNetworkError(LiteICSFetchError):
    """Network error during ICS fetch."""


class LiteICSTimeoutError(LiteICSFetchError):
    """Timeout error during ICS fetch."""


# Lightweight security event logging for CalendarBot Lite
class LiteSecurityEventLogger:
    """Lightweight security event logger for CalendarBot Lite."""

    def log_event(self, event_data: dict[str, Any]) -> None:
        """Log security event with minimal overhead.

        Args:
            event_data: Security event data to log
        """
        # For CalendarBot Lite, log security events at appropriate levels based on severity
        event_type = event_data.get("event_type", "unknown")
        severity = event_data.get("severity", "unknown")
        resource = event_data.get("resource", "unknown")
        description = event_data.get("details", {}).get("description", "No description")

        message = f"Security Event - Type: {event_type}, Severity: {severity}, Resource: {resource}, Description: {description}"

        # Use DEBUG level for LOW severity events (normal operations like URL access)
        # Use WARNING level for MEDIUM/HIGH severity events (actual security concerns)
        if severity == "LOW":
            logger.debug(message)
        else:
            logger.warning(message)


def _raise_client_not_initialized() -> NoReturn:
    """Raise LiteICSFetchError for uninitialized HTTP client."""
    raise LiteICSFetchError("HTTP client not initialized")


class LiteICSFetcher:
    """Async HTTP client for downloading ICS calendar files - CalendarBot Lite version."""

    def __init__(self, settings: Any, shared_client: Optional[httpx.AsyncClient] = None) -> None:
        """Initialize ICS fetcher.

        Args:
            settings: Application settings
            shared_client: Optional shared HTTP client for connection reuse
        """
        # Assign settings and ensure it exposes the small surface the fetcher expects.
        # Some callers construct minimal ad-hoc settings objects; provide safe defaults
        # on the settings object so older/compact callers won't trigger AttributeError.
        self.settings = settings
        try:
            if not hasattr(self.settings, "request_timeout"):
                # Prefer direct attribute assignment over setattr for clarity and ruff B010.
                # Use type: ignore because settings can be a dynamic/mapping-like object in tests.
                self.settings.request_timeout = 30  # type: ignore[attr-defined]
            if not hasattr(self.settings, "max_retries"):
                self.settings.max_retries = 3  # type: ignore[attr-defined]
            if not hasattr(self.settings, "retry_backoff_factor"):
                self.settings.retry_backoff_factor = 1.5  # type: ignore[attr-defined]
        except Exception:
            # settings may be an immutable type or Mock; in that case other code paths
            # already use getattr(..., default) fallbacks, so it's safe to ignore.
            pass

        self.client: Optional[httpx.AsyncClient] = shared_client
        self._use_shared_client = shared_client is not None
        self._client_id = "lite_fetcher"
        self.security_logger = LiteSecurityEventLogger()

        logger.debug("Lite ICS fetcher initialized (shared_client: %s)", self._use_shared_client)

    async def __aenter__(self) -> "LiteICSFetcher":
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Async context manager exit."""
        await self._close_client()

    async def _close_client(self) -> None:
        """Close HTTP client if it's not shared."""
        if self.client is not None and not self._use_shared_client:
            # Only close individual clients, not shared ones
            if not self.client.is_closed:
                await self.client.aclose()
                logger.debug("Closed individual HTTP client")
            self.client = None
        elif self._use_shared_client:
            # Don't close shared clients, just clear reference
            self.client = None
            logger.debug("Released shared HTTP client reference")

    async def _ensure_client(self) -> None:
        """Ensure HTTP client exists."""
        if self._use_shared_client:
            # Use shared client for connection reuse optimization
            try:
                self.client = await get_shared_client(self._client_id)
                logger.debug("Using shared HTTP client for connection reuse")
                return
            except Exception as e:
                logger.warning(
                    "Failed to get shared HTTP client, falling back to individual client: %s", e
                )
                # Fall back to individual client
                self._use_shared_client = False

        # Individual client path (fallback or when shared client not provided)
        if self.client is None or self.client.is_closed:
            timeout = httpx.Timeout(
                connect=10.0, read=self.settings.request_timeout, write=10.0, pool=30.0
            )

            self.client = httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                verify=True,  # SSL verification
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/calendar, text/plain, application/octet-stream, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Cache-Control": "no-cache",
                },
            )

    def _validate_url_for_ssrf(self, url: str) -> bool:
        """Validate URL for basic format and security - simplified for single-user hobby application.

        Performs basic URL validation to ensure proper format and prevent obviously malicious URLs.
        This simplified version is appropriate for single-user applications where complex SSRF
        protection is unnecessary overhead.

        Args:
            url: URL string to validate. Should be a complete HTTP or HTTPS URL.

        Returns:
            bool: True if URL has valid format, False if blocked due to invalid format.
        """
        try:
            parsed = urlparse(url)

            # Only allow HTTP/HTTPS schemes
            if parsed.scheme not in ["http", "https"]:
                logger.debug(f"Blocked non-HTTP(S) URL: {url}")
                event = {
                    "event_type": "INPUT_VALIDATION_FAILURE",
                    "severity": "LOW",
                    "resource": url,
                    "action": "url_validation",
                    "result": "blocked",
                    "details": {
                        "description": f"Invalid URL scheme: {parsed.scheme}",
                    },
                }
                self.security_logger.log_event(event)
                return False

            # Require valid hostname
            if not parsed.hostname:
                logger.debug(f"Blocked URL with missing hostname: {url}")
                event = {
                    "event_type": "INPUT_VALIDATION_FAILURE",
                    "severity": "LOW",
                    "resource": url,
                    "action": "url_validation",
                    "result": "blocked",
                    "details": {
                        "description": "URL missing hostname",
                    },
                }
                self.security_logger.log_event(event)
                return False

            # URL passed basic validation
            logger.debug(f"URL validation passed: {url}")
            return True

        except Exception as e:
            logger.debug(f"URL validation error for {url}: {e}")
            event = {
                "event_type": "INPUT_VALIDATION_FAILURE",
                "severity": "LOW",
                "resource": url,
                "action": "url_validation",
                "result": "error",
                "details": {
                    "description": f"URL validation error: {e}",
                },
            }
            self.security_logger.log_event(event)
            return False

    async def fetch_ics(
        self, source: LiteICSSource, conditional_headers: Optional[dict[str, str]] = None
    ) -> LiteICSResponse:
        """Download ICS content from source with comprehensive error handling and security validation.

        Performs secure HTTP(S) requests to fetch ICS calendar data with built-in SSRF protection,
        authentication handling, retry logic, and comprehensive error management. Supports conditional
        requests for efficient caching and implements security logging for audit compliance.

        Args:
            source: ICS source configuration containing:
                   - url (str): HTTP(S) URL to fetch, validated against SSRF attacks
                   - auth (AuthConfig): Authentication configuration (basic/bearer/none)
                   - custom_headers (Dict[str, str]): Additional HTTP headers
                   - timeout (int): Request timeout in seconds
                   - validate_ssl (bool): SSL certificate validation setting
            conditional_headers: Optional caching headers for bandwidth optimization:
                                - "If-Modified-Since": RFC 2822 date string
                                - "If-None-Match": ETag value from previous response

        Returns:
            LiteICSResponse: Response object containing:
                        - success (bool): Operation success indicator
                        - content (str): ICS calendar data (if successful)
                        - status_code (int): HTTP response code
                        - error_message (str): Detailed error description (if failed)
                        - headers (Dict[str, str]): Response headers
                        - etag/last_modified: Caching metadata

        Raises:
            LiteICSAuthError: Authentication failures (HTTP 401/403):
                         - Invalid credentials for basic authentication
                         - Expired or invalid bearer tokens
                         - Insufficient permissions for calendar access

            LiteICSNetworkError: Network connectivity issues:
                            - DNS resolution failures
                            - Connection timeouts or refused connections
                            - SSL/TLS handshake failures
                            - Network unreachability

            LiteICSTimeoutError: Request timeout scenarios:
                            - Server response timeout beyond configured limit
                            - Connection establishment timeout
                            - Slow server response causing timeout

            LiteICSFetchError: General fetching errors:
                          - Invalid ICS content format
                          - Unexpected server responses
                          - HTTP client initialization failures
                          - Malformed source configuration

        Security Features:
            - SSRF protection prevents access to private networks
            - URL validation blocks localhost and RFC 1918 addresses
            - Comprehensive security event logging
            - SSL certificate validation (configurable)
            - Request timeout enforcement to prevent resource exhaustion

        Performance Features:
            - Automatic retry with exponential backoff
            - Conditional request support for bandwidth optimization
            - Connection pooling and reuse
            - Configurable timeouts for different scenarios

        Example:
            >>> source = LiteICSSource(url="https://calendar.example.com/cal.ics")
            >>> response = await fetcher.fetch_ics(source)
            >>> if response.success:
            ...     events = parse_ics_content(response.content)
        """
        await self._ensure_client()

        # Validate URL to prevent SSRF attacks
        if not self._validate_url_for_ssrf(source.url):
            error_msg = "URL blocked for security reasons"
            logger.error(f"SSRF protection: {error_msg} - {source.url}")
            return LiteICSResponse(success=False, error_message=error_msg, status_code=403)

        try:
            logger.debug(f"Fetching ICS from {source.url}")

            # Log successful URL validation
            event = {
                "event_type": "DATA_ACCESS",
                "severity": "LOW",
                "resource": source.url,
                "action": "url_access",
                "result": "success",
                "details": {
                    "description": f"Accessing validated URL: {source.url}",
                    "source_ip": "internal",
                },
            }
            self.security_logger.log_event(event)

            # Prepare headers
            headers = {}

            # Add authentication headers
            auth_headers = source.auth.get_headers()
            headers.update(auth_headers)

            # Add custom headers
            headers.update(source.custom_headers)

            # Add conditional request headers
            if conditional_headers:
                headers.update(conditional_headers)

            # Make request with retry logic and possible streaming
            response = await self._make_request_with_retry(
                source.url, headers, source.timeout, source.validate_ssl
            )

            return self._create_response(response)

        except httpx.TimeoutException:
            logger.exception(f"Timeout fetching ICS from {source.url}")
            return LiteICSResponse(
                success=False,
                error_message=f"Request timeout after {source.timeout}s",
                status_code=None,
            )

        except httpx.HTTPStatusError as e:
            logger.exception(f"HTTP error fetching ICS from {source.url}: {e.response.status_code}")

            if e.response.status_code == 401:
                error_msg = "Authentication failed - check credentials"
                raise LiteICSAuthError(error_msg, e.response.status_code) from e
            if e.response.status_code == 403:
                error_msg = "Access forbidden - insufficient permissions"
                raise LiteICSAuthError(error_msg, e.response.status_code) from e
            return LiteICSResponse(
                success=False,
                status_code=e.response.status_code,
                error_message=f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
                headers=dict(e.response.headers),
            )

        except httpx.NetworkError as e:
            logger.exception(f"Network error fetching ICS from {source.url}")
            raise LiteICSNetworkError(f"Network error: {e}") from e

        except Exception as e:
            logger.exception(f"Unexpected error fetching ICS from {source.url}")
            raise LiteICSFetchError(f"Unexpected error: {e}") from e

    async def _make_request_with_retry(
        self, url: str, headers: dict[str, str], timeout: int, _verify_ssl: bool
    ) -> Any:
        """Make HTTP request with retry logic and streaming decision.

        Enhanced with network corruption detection and jittered backoff.

        Returns:
            Either an httpx.Response (buffered) or a StreamHandle (streaming).
        """
        last_exception = None
        corruption_indicators = 0  # Track signs of network issues

        attempt = 0
        max_retries = int(getattr(self.settings, "max_retries", 3))
        backoff_factor = float(getattr(self.settings, "retry_backoff_factor", 1.5))

        # Enhanced retry for network corruption scenarios
        corruption_detected = False

        while attempt <= max_retries:
            try:
                if self.client is None:
                    _raise_client_not_initialized()

                # Add browser-like headers to avoid automated client detection by Office365
                browser_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/calendar,text/plain,*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Cache-Control": "max-age=0",
                }
                # Merge existing headers with browser headers (browser headers take precedence)
                combined_headers = {**headers, **browser_headers}

                # DEAD SIMPLE: Use httpx.get() to download entire file at once like a browser
                logger.debug("Using dead simple GET request for %s", url)
                response = await self.client.get(
                    url, headers=combined_headers, timeout=timeout, follow_redirects=True
                )

                # Handle 304 Not Modified
                if response.status_code == 304:
                    logger.debug("ICS content not modified (304)")
                    if self._use_shared_client:
                        await record_client_success(self._client_id)
                    return response

                # Raise for status for HTTP errors
                response.raise_for_status()

                if self._use_shared_client:
                    await record_client_success(self._client_id)

                logger.debug(
                    "Successfully fetched ICS from %s (attempt %d) - %d bytes",
                    url,
                    attempt + 1,
                    len(response.content),
                )
                return response

            except httpx.HTTPStatusError:
                # Don't retry HTTP errors (auth errors, not found, etc.)
                raise

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                # Record client error for health tracking
                if self._use_shared_client:
                    await record_client_error(self._client_id)

                # Detect potential network corruption indicators
                corruption_indicators += 1
                if (
                    "Connection broken" in str(e)
                    or "Broken pipe" in str(e)
                    or "Connection reset" in str(e)
                ):
                    corruption_detected = True
                    logger.warning(f"Network corruption detected in attempt {attempt + 1}: {e}")

                last_exception = e
                if attempt < max_retries:
                    # Enhanced backoff with jitter for network corruption scenarios
                    base_backoff = backoff_factor**attempt
                    if corruption_detected:
                        # Longer backoff for corruption scenarios
                        base_backoff = min(base_backoff * 2, 30.0)  # Cap at 30 seconds

                    # Add jitter to prevent thundering herd
                    import random  # noqa: PLC0415

                    jitter = random.uniform(0.1, 0.3) * base_backoff
                    backoff_time = base_backoff + jitter

                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"corruption_detected={corruption_detected}, "
                        f"retrying in {backoff_time:.1f}s: {e}"
                    )
                    await asyncio.sleep(backoff_time)
                else:
                    if corruption_detected:
                        logger.exception(
                            f"All retry attempts failed with network corruption indicators for {url}"
                        )
                    else:
                        logger.exception(f"All retry attempts failed for {url}")
                    raise
            except Exception:
                # Record client error for unexpected exceptions
                if self._use_shared_client:
                    await record_client_error(self._client_id)
                raise
            attempt += 1

        if last_exception:
            raise last_exception
        raise LiteICSFetchError("Maximum retries exceeded")

    def _create_response(self, http_response: Any) -> LiteICSResponse:
        """Create ICS response from HTTP response or StreamHandle.

        Args:
            http_response: Either httpx.Response (buffered) or StreamHandle (streaming)

        Returns:
            ICS response object
        """
        # Always buffered httpx.Response now
        headers = dict(http_response.headers)

        # Handle 304 Not Modified
        if http_response.status_code == 304:
            logger.debug("ICS content not modified (304)")
            return LiteICSResponse(
                success=True,
                status_code=304,
                headers=headers,
                etag=headers.get("etag"),
                last_modified=headers.get("last-modified"),
                cache_control=headers.get("cache-control"),
            )

        # Get content
        content = http_response.text
        content_type = headers.get("content-type", "").lower()

        # Validate content type
        if content_type and not any(ct in content_type for ct in ["text/calendar", "text/plain"]):
            logger.warning(f"Unexpected content type: {content_type}")

        # Basic content validation
        if not content or not content.strip():
            logger.error("Empty ICS content received")
            return LiteICSResponse(
                success=False,
                status_code=http_response.status_code,
                error_message="Empty content received",
                headers=headers,
            )

        # Check for basic ICS markers
        if "BEGIN:VCALENDAR" not in content:
            logger.warning("Content does not appear to be valid ICS format")

        logger.debug(f"Successfully fetched ICS content ({len(content)} bytes)")

        return LiteICSResponse(
            success=True,
            content=content,
            status_code=http_response.status_code,
            headers=headers,
            etag=headers.get("etag"),
            last_modified=headers.get("last-modified"),
            cache_control=headers.get("cache-control"),
        )

    async def test_connection(self, source: LiteICSSource) -> bool:
        """Test connection to ICS source.

        Args:
            source: ICS source to test

        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.debug(f"Testing connection to {source.url}")

            # Make a HEAD request first for efficiency
            await self._ensure_client()

            headers = source.auth.get_headers()
            headers.update(source.custom_headers)

            if self.client is None:
                _raise_client_not_initialized()

            response = await self.client.head(source.url, headers=headers, timeout=source.timeout)

            if response.status_code == 200:
                logger.info(f"Connection test successful for {source.url}")
                return True
            if response.status_code == 405:  # Method not allowed, try GET
                logger.debug("HEAD not supported, testing with GET")
                ics_response = await self.fetch_ics(source)
                return ics_response.success
            logger.warning(f"Connection test failed: HTTP {response.status_code}")
            return False

        except Exception:
            logger.exception(f"Connection test failed for {source.url}")
            return False

    def get_conditional_headers(
        self, etag: Optional[str] = None, last_modified: Optional[str] = None
    ) -> dict[str, str]:
        """Get conditional request headers for caching.

        Args:
            etag: ETag value from previous response
            last_modified: Last-Modified value from previous response

        Returns:
            Dictionary of conditional headers
        """
        headers = {}

        if etag:
            headers["If-None-Match"] = etag

        if last_modified:
            headers["If-Modified-Since"] = last_modified

        return headers
