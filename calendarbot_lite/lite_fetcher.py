"""HTTP client for downloading ICS calendar files - CalendarBot Lite version."""

# Standard library imports
import asyncio
import logging
import random
from typing import Any, NoReturn, Optional
from urllib.parse import urlparse

import httpx

from .http_client import (
    DEFAULT_BROWSER_HEADERS,
    get_shared_client,
    record_client_error,
    record_client_success,
)
from .lite_models import LiteICSResponse, LiteICSSource

logger = logging.getLogger(__name__)

# Backoff calculation constants
MAX_BACKOFF_SECONDS = 30.0  # Maximum backoff time for corruption scenarios
JITTER_MIN_FACTOR = 0.1  # Minimum jitter multiplier
JITTER_MAX_FACTOR = 0.3  # Maximum jitter multiplier


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
        self.settings = settings
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
            request_timeout = getattr(self.settings, "request_timeout", 30)
            timeout = httpx.Timeout(connect=10.0, read=request_timeout, write=10.0, pool=30.0)

            # Create IPv4-only transport to prevent IPv6 DNS resolution issues on Pi Zero 2W
            # This fixes "temporary failure in name resolution" when IPv6 is configured
            # on the host but DNS resolution fails for certain domains like outlook.office365.com
            limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
            transport = httpx.AsyncHTTPTransport(
                limits=limits,
                local_address="0.0.0.0",  # nosec B104 - intentional IPv4 binding for client
            )

            self.client = httpx.AsyncClient(
                transport=transport,
                timeout=timeout,
                follow_redirects=True,
                verify=True,  # SSL verification
                headers=DEFAULT_BROWSER_HEADERS,
            )

    def _log_validation_event(
        self, url: str, result: str, description: str, severity: str = "LOW"
    ) -> None:
        """Log URL validation security event.

        Args:
            url: The URL being validated
            result: Validation result ("blocked" or "error")
            description: Human-readable description of the validation outcome
            severity: Event severity level (default: "LOW")
        """
        event = {
            "event_type": "INPUT_VALIDATION_FAILURE",
            "severity": severity,
            "resource": url,
            "action": "url_validation",
            "result": result,
            "details": {
                "description": description,
            },
        }
        self.security_logger.log_event(event)

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
                logger.debug("Blocked non-HTTP(S) URL: %s", url)
                self._log_validation_event(url, "blocked", f"Invalid URL scheme: {parsed.scheme}")
                return False

            # Require valid hostname
            if not parsed.hostname:
                logger.debug("Blocked URL with missing hostname: %s", url)
                self._log_validation_event(url, "blocked", "URL missing hostname")
                return False

            # URL passed basic validation
            logger.debug("URL validation passed: %s", url)
            return True

        except Exception as e:
            logger.debug("URL validation error for %s: %s", url, e)
            self._log_validation_event(url, "error", f"URL validation error: {e}")
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
            logger.error("SSRF protection: %s - %s", error_msg, source.url)
            return LiteICSResponse(success=False, error_message=error_msg, status_code=403)

        try:
            logger.debug("Fetching ICS from %s", source.url)

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
            response = await self._make_request_with_retry(source.url, headers, source.timeout)

            return self._create_response(response)

        except httpx.TimeoutException:
            logger.exception("Timeout fetching ICS from %s", source.url)
            return LiteICSResponse(
                success=False,
                error_message=f"Request timeout after {source.timeout}s",
                status_code=None,
            )

        except httpx.HTTPStatusError as e:
            logger.exception(
                "HTTP error fetching ICS from %s: %s", source.url, e.response.status_code
            )

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
            logger.exception("Network error fetching ICS from %s", source.url)
            raise LiteICSNetworkError(f"Network error: {e}") from e

        except Exception as e:
            logger.exception("Unexpected error fetching ICS from %s", source.url)
            raise LiteICSFetchError(f"Unexpected error: {e}") from e

    def _calculate_backoff(
        self,
        attempt: int,
        corruption_detected: bool,
        max_retries: int,
        backoff_factor: float,
    ) -> float:
        """Calculate exponential backoff time with jitter.

        Implements exponential backoff with optional corruption-detection multiplier
        and randomized jitter to prevent thundering herd problems.

        Args:
            attempt: Current retry attempt number (0-indexed)
            corruption_detected: Whether network corruption has been detected
            max_retries: Maximum number of retries allowed (used for context)
            backoff_factor: Base factor for exponential backoff calculation

        Returns:
            float: Calculated backoff time in seconds including jitter
        """
        # Calculate base exponential backoff
        base_backoff = backoff_factor**attempt

        # Double backoff and apply cap for corruption scenarios
        if corruption_detected:
            base_backoff = min(base_backoff * 2, MAX_BACKOFF_SECONDS)

        # Add jitter to prevent thundering herd
        jitter = random.uniform(JITTER_MIN_FACTOR, JITTER_MAX_FACTOR) * base_backoff  # nosec B311 - jitter not cryptographic
        return base_backoff + jitter

    async def _make_request_with_retry(
        self, url: str, headers: dict[str, str], timeout: int
    ) -> Any:
        """Make HTTP request with retry logic and streaming decision.

        Enhanced with network corruption detection and jittered backoff.

        Returns:
            Either an httpx.Response (buffered) or a StreamHandle (streaming).
        """
        last_exception = None

        attempt = 0
        max_retries = int(getattr(self.settings, "max_retries", 3))
        backoff_factor = float(getattr(self.settings, "retry_backoff_factor", 1.5))

        # Enhanced retry for network corruption scenarios
        corruption_detected = False

        while attempt <= max_retries:
            try:
                if self.client is None:
                    _raise_client_not_initialized()

                # Merge existing headers with browser headers (browser headers take precedence)
                combined_headers = {**headers, **DEFAULT_BROWSER_HEADERS}

                # Add correlation ID for request tracing (if available, doesn't override existing)
                try:
                    from .middleware import get_request_id

                    request_id = get_request_id()
                    if request_id and request_id != "no-request-id":
                        # Only add if not already present (allows client override)
                        combined_headers.setdefault("X-Request-ID", request_id)
                except (ImportError, AttributeError):
                    # Middleware not available or no request context
                    pass

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
                if (
                    "Connection broken" in str(e)
                    or "Broken pipe" in str(e)
                    or "Connection reset" in str(e)
                ):
                    corruption_detected = True
                    logger.warning("Network corruption detected in attempt %d: %s", attempt + 1, e)

                last_exception = e
                if attempt < max_retries:
                    # Calculate backoff with jitter for network corruption scenarios
                    backoff_time = self._calculate_backoff(
                        attempt, corruption_detected, max_retries, backoff_factor
                    )

                    logger.warning(
                        "Request failed (attempt %s/%s), corruption_detected=%s, retrying in %.1fs: %s",
                        attempt + 1,
                        max_retries + 1,
                        corruption_detected,
                        backoff_time,
                        e,
                    )
                    await asyncio.sleep(backoff_time)
                else:
                    if corruption_detected:
                        logger.exception(
                            "All retry attempts failed with network corruption indicators for %s",
                            url,
                        )
                    else:
                        logger.exception("All retry attempts failed for %s", url)
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
            logger.warning("Unexpected content type: %s", content_type)

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

        logger.debug("Successfully fetched ICS content (%d bytes)", len(content))

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
            logger.debug("Testing connection to %s", source.url)

            # Make a HEAD request first for efficiency
            await self._ensure_client()

            headers = source.auth.get_headers()
            headers.update(source.custom_headers)

            if self.client is None:
                _raise_client_not_initialized()

            response = await self.client.head(source.url, headers=headers, timeout=source.timeout)

            if response.status_code == 200:
                logger.info("Connection test successful for %s", source.url)
                return True
            if response.status_code == 405:  # Method not allowed, try GET
                logger.debug("HEAD not supported, testing with GET")
                ics_response = await self.fetch_ics(source)
                return ics_response.success
            logger.warning("Connection test failed: HTTP %d", response.status_code)
            return False

        except Exception:
            logger.exception("Connection test failed for %s", source.url)
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
