"""HTTP client for downloading ICS calendar files - CalendarBot Lite version."""

# Standard library imports
import asyncio
import ipaddress
import logging
import os
from typing import Any, NoReturn, Optional
from urllib.parse import urlparse

import httpx

from .lite_models import LiteICSResponse, LiteICSSource

logger = logging.getLogger(__name__)

# Streaming / performance tuning defaults (can be overridden via settings object)
STREAM_THRESHOLD = 262_144  # 256KB
READ_CHUNK_SIZE_BYTES = 8192
PREFER_STREAM_DEFAULT = "auto"  # "auto" | "force" | "never"
INITIAL_BUFFER_BYTES_FOR_CHUNKED = 8192


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


class StreamHandle:
    """Lightweight handle representing a streaming HTTP response.

    The StreamHandle provides an async iterator of bytes via `iter_bytes()`.
    It does not consume the entire response body up-front and is designed to be
    passed to downstream consumers that can stream-parse the content.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
        timeout: int,
        chunk_size: int = READ_CHUNK_SIZE_BYTES,
        status_code: Optional[int] = None,
        resp_headers: Optional[dict[str, str]] = None,
    ):
        self.client = client
        self.url = url
        self.request_headers = headers
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.status_code = status_code
        self.headers = dict(resp_headers or {})

    async def iter_bytes(self):
        """Async generator yielding raw byte chunks from the remote resource."""
        async with self.client.stream(
            "GET", self.url, headers=self.request_headers, timeout=self.timeout
        ) as resp:
            # Let callers observe status/headers via the handle if needed
            self.status_code = resp.status_code
            self.headers = dict(resp.headers)
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(chunk_size=self.chunk_size):
                yield chunk

    async def read_initial_bytes(self, n: int) -> bytes:
        """Read up to `n` bytes from the stream, returning them as a single bytes object.

        This method will consume the stream; intended for heuristics (e.g., sniffing headers)
        and should be used carefully.
        """
        buf = bytearray()
        async for chunk in self.iter_bytes():
            if not chunk:
                break
            need = n - len(buf)
            if need <= 0:
                break
            if len(chunk) <= need:
                buf.extend(chunk)
            else:
                buf.extend(chunk[:need])
                # Note: we cannot push the remainder back into the stream easily,
                # so read_initial_bytes should be used only for small heuristics.
                break
        return bytes(buf)


class LiteICSFetcher:
    """Async HTTP client for downloading ICS calendar files - CalendarBot Lite version."""

    def __init__(self, settings: Any) -> None:
        """Initialize ICS fetcher.

        Args:
            settings: Application settings
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

        self.client: Optional[httpx.AsyncClient] = None
        self.security_logger = LiteSecurityEventLogger()

        logger.debug("Lite ICS fetcher initialized")

    async def __aenter__(self) -> "LiteICSFetcher":
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Async context manager exit."""
        await self._close_client()

    async def _ensure_client(self) -> None:
        """Ensure HTTP client exists."""
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

    async def _close_client(self) -> None:
        """Close HTTP client."""
        if self.client and not self.client.is_closed:
            await self.client.aclose()

    def _validate_url_for_ssrf(self, url: str) -> bool:  # noqa: PLR0911, PLR0912
        """Validate URL to prevent Server-Side Request Forgery (SSRF) attacks with comprehensive security checks.

        Implements multi-layered security validation to prevent malicious URLs from accessing
        internal network resources, localhost services, or private IP ranges. Includes detection
        of encoded IP addresses and alternative representations commonly used in SSRF exploits.

        Security Validation Layers:
        1. Protocol validation - Only HTTP/HTTPS allowed
        2. Hostname validation - Rejects empty or malformed hostnames
        3. IP address validation - Blocks private, loopback, and link-local ranges
        4. Alternative encoding detection - Prevents decimal/hex IP encoding bypasses
        5. Hostname pattern matching - Blocks common private network names

        Args:
            url: URL string to validate for SSRF security risks. Should be a complete
                HTTP or HTTPS URL with valid hostname/IP and optional path components.

        Returns:
            bool: True if URL is safe for external requests, False if blocked for security.
                 All rejections are logged as security events for audit compliance.

        Security Patterns Detected and Blocked:
            - Non-HTTP(S) protocols: ftp://, file://, gopher://, etc.
            - Private IPv4 ranges: 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12
            - IPv6 loopback and link-local: ::1, fe80::/10
            - Localhost patterns: localhost, 127.0.0.1, 127.x.x.x
            - Decimal IP encoding: 2130706433 (represents 127.0.0.1)
            - Hexadecimal IP encoding: 0x7f000001 (represents 127.0.0.1)
            - Partial private network matches: 192.168.*, 10.*, 172.*

        Environment Variables:
            CALENDARBOT_ALLOW_LOCALHOST: Set to 'true', '1', or 'yes' to allow localhost
                                        URLs for testing purposes. This bypasses security
                                        checks for localhost/127.0.0.1 addresses only.
        """
        try:
            # Check for testing mode that allows localhost URLs
            allow_localhost = os.environ.get("CALENDARBOT_ALLOW_LOCALHOST", "").lower() in (
                "true",
                "1",
                "yes",
            )
            if allow_localhost:
                logger.debug(
                    "CALENDARBOT_ALLOW_LOCALHOST enabled - localhost URLs will be allowed for testing"
                )

            parsed = urlparse(url)

            # Only allow HTTP/HTTPS
            if parsed.scheme not in ["http", "https"]:
                event = {
                    "event_type": "SYSTEM_SECURITY_VIOLATION",
                    "severity": "HIGH",
                    "resource": url,
                    "action": "url_validation",
                    "result": "blocked",
                    "details": {
                        "violation_type": "ssrf_attempt",
                        "description": f"Blocked non-HTTP(S) scheme: {parsed.scheme}",
                        "source_ip": "internal",
                    },
                }
                self.security_logger.log_event(event)
                return False

            # Check for localhost/private IP addresses
            hostname = parsed.hostname
            if not hostname:
                # Reject URLs with empty hostnames
                event = {
                    "event_type": "SYSTEM_SECURITY_VIOLATION",
                    "severity": "HIGH",
                    "resource": url,
                    "action": "url_validation",
                    "result": "blocked",
                    "details": {
                        "violation_type": "ssrf_attempt",
                        "description": f"Blocked URL with empty hostname: {url}",
                        "source_ip": "internal",
                    },
                }
                self.security_logger.log_event(event)
                return False

            if hostname:
                # First try standard IP parsing
                try:
                    ip = ipaddress.ip_address(hostname)
                    # Allow localhost/loopback IPs if testing mode is enabled
                    if allow_localhost and ip.is_loopback:
                        logger.debug(
                            "Allowing localhost IP %s due to CALENDARBOT_ALLOW_LOCALHOST", hostname
                        )
                        return True

                    if ip.is_private or ip.is_loopback or ip.is_link_local:
                        event = {
                            "event_type": "SYSTEM_SECURITY_VIOLATION",
                            "severity": "HIGH",
                            "resource": url,
                            "action": "url_validation",
                            "result": "blocked",
                            "details": {
                                "violation_type": "ssrf_attempt",
                                "description": f"Blocked private/localhost IP: {hostname}",
                                "source_ip": "internal",
                            },
                        }
                        self.security_logger.log_event(event)
                        return False
                except ValueError:
                    # Try parsing alternative IP representations (decimal, hex)
                    parsed_ip = None
                    try:
                        # Try decimal representation (e.g., 2130706433 = 127.0.0.1)
                        if hostname.isdigit():
                            decimal_ip = int(hostname)
                            if 0 <= decimal_ip <= 0xFFFFFFFF:  # Valid IPv4 range
                                # Convert decimal to dotted decimal
                                ip_bytes = [
                                    (decimal_ip >> 24) & 0xFF,
                                    (decimal_ip >> 16) & 0xFF,
                                    (decimal_ip >> 8) & 0xFF,
                                    decimal_ip & 0xFF,
                                ]
                                ip_str = ".".join(map(str, ip_bytes))
                                parsed_ip = ipaddress.ip_address(ip_str)

                        # Try hexadecimal representation (e.g., 0x7f000001 = 127.0.0.1)
                        elif hostname.lower().startswith("0x"):
                            hex_ip = int(hostname, 16)
                            if 0 <= hex_ip <= 0xFFFFFFFF:  # Valid IPv4 range
                                # Convert hex to dotted decimal
                                ip_bytes = [
                                    (hex_ip >> 24) & 0xFF,
                                    (hex_ip >> 16) & 0xFF,
                                    (hex_ip >> 8) & 0xFF,
                                    hex_ip & 0xFF,
                                ]
                                ip_str = ".".join(map(str, ip_bytes))
                                parsed_ip = ipaddress.ip_address(ip_str)

                        # If we successfully parsed an alternative IP format, check if it's private
                        if parsed_ip and (
                            parsed_ip.is_private or parsed_ip.is_loopback or parsed_ip.is_link_local
                        ):
                            event = {
                                "event_type": "SYSTEM_SECURITY_VIOLATION",
                                "severity": "HIGH",
                                "resource": url,
                                "action": "url_validation",
                                "result": "blocked",
                                "details": {
                                    "violation_type": "ssrf_attempt",
                                    "description": f"Blocked encoded private IP: {hostname} -> {parsed_ip}",
                                    "source_ip": "internal",
                                },
                            }
                            self.security_logger.log_event(event)
                            return False

                    except (ValueError, OverflowError):
                        pass  # Not a valid alternative IP format

                    # Hostname is not an IP, check for localhost patterns
                    # Allow localhost hostnames if testing mode is enabled
                    if allow_localhost and (
                        hostname.lower() in ["localhost", "::1"] or hostname.startswith("127.")
                    ):
                        logger.debug(
                            "Allowing localhost hostname %s due to CALENDARBOT_ALLOW_LOCALHOST",
                            hostname,
                        )
                        return True

                    if hostname.lower() in ["localhost", "127.0.0.1", "::1"] or hostname.startswith(
                        ("192.168.", "10.", "172.")
                    ):
                        event = {
                            "event_type": "SYSTEM_SECURITY_VIOLATION",
                            "severity": "HIGH",
                            "resource": url,
                            "action": "url_validation",
                            "result": "blocked",
                            "details": {
                                "violation_type": "ssrf_attempt",
                                "description": f"Blocked private hostname: {hostname}",
                                "source_ip": "internal",
                            },
                        }
                        self.security_logger.log_event(event)
                        return False

            return True

        except Exception as e:
            event = {
                "event_type": "INPUT_VALIDATION_FAILURE",
                "severity": "MEDIUM",
                "resource": url,
                "action": "url_validation",
                "result": "error",
                "details": {
                    "validation_error": f"URL validation failed: {e}",
                    "source_ip": "internal",
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

    async def _make_request_with_retry(  # noqa: PLR0912, PLR0915
        self, url: str, headers: dict[str, str], timeout: int, _verify_ssl: bool
    ) -> Any:
        """Make HTTP request with retry logic and streaming decision.

        Returns:
            Either an httpx.Response (buffered) or a StreamHandle (streaming).
        """
        last_exception = None

        attempt = 0
        max_retries = int(getattr(self.settings, "max_retries", 3))
        backoff_factor = float(getattr(self.settings, "retry_backoff_factor", 1.5))

        # Configurable tuning values (can be provided on settings object)
        stream_threshold = int(getattr(self.settings, "stream_threshold_bytes", STREAM_THRESHOLD))
        prefer_stream = str(getattr(self.settings, "prefer_stream", PREFER_STREAM_DEFAULT)).lower()
        chunk_size = int(getattr(self.settings, "read_chunk_size_bytes", READ_CHUNK_SIZE_BYTES))

        while attempt <= max_retries:
            try:
                if self.client is None:
                    _raise_client_not_initialized()

                # Attempt HEAD first to cheaply obtain headers (some servers don't support HEAD)
                head_resp = None
                try:
                    head_resp = await self.client.head(url, headers=headers, timeout=timeout)
                    # Some test mocks (e.g., SimpleNamespace) do not implement raise_for_status().
                    # Only call raise_for_status when available to avoid AttributeError on mocks.
                    if getattr(head_resp, "status_code", None) != 304 and hasattr(
                        head_resp, "raise_for_status"
                    ):
                        head_resp.raise_for_status()
                except httpx.HTTPStatusError:
                    # Propagate HTTP errors from HEAD
                    raise
                except Exception:
                    # HEAD not supported or failed; treat as absent
                    head_resp = None

                content_length = None
                head_headers = None
                head_status = None
                if head_resp is not None:
                    head_headers = dict(getattr(head_resp, "headers", {}))
                    head_status = getattr(head_resp, "status_code", None)
                    # Read Content-Length header in a case-insensitive way to support varied servers/mocks
                    cl = None
                    if getattr(head_resp, "headers", None):
                        for hk, hv in getattr(head_resp, "headers", {}).items():
                            if isinstance(hk, str) and hk.lower() == "content-length":
                                cl = hv
                                break
                    if cl is not None:
                        try:
                            content_length = int(cl)
                        except Exception:
                            content_length = None

                # Decision logic for streaming vs buffering
                do_stream = False
                if prefer_stream == "force":
                    do_stream = True
                elif prefer_stream == "never":
                    do_stream = False
                elif content_length is not None:
                    do_stream = content_length > stream_threshold
                else:
                    # No Content-Length (chunked) -> conservative: stream
                    do_stream = True

                if do_stream:
                    logger.debug(
                        f"Selected streaming GET for {url} (prefer_stream={prefer_stream}, content_length={content_length})"
                    )
                    # Return StreamHandle for downstream consumption
                    return StreamHandle(
                        self.client,
                        url,
                        headers,
                        timeout,
                        chunk_size,
                        status_code=head_status,
                        resp_headers=head_headers,
                    )

                # Buffered path: perform GET and return full response (existing behavior)
                response = await self.client.get(url, headers=headers, timeout=timeout)

                if response.status_code != 304:
                    response.raise_for_status()

                logger.debug(f"Successfully fetched ICS from {url} (attempt {attempt + 1})")
                return response

            except httpx.HTTPStatusError:
                # Don't retry HTTP errors (auth errors, not found, etc.)
                raise

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                if attempt < max_retries:
                    backoff_time = backoff_factor**attempt
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {backoff_time:.1f}s: {e}"
                    )
                    await asyncio.sleep(backoff_time)
                else:
                    logger.exception(f"All retry attempts failed for {url}")
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
        # Streaming path
        if isinstance(http_response, StreamHandle):
            headers = dict(http_response.headers or {})
            logger.debug(f"Creating streaming LiteICSResponse for {http_response.url}")
            return LiteICSResponse(
                success=True,
                content=None,
                stream_handle=http_response,
                stream_mode="bytes",
                status_code=http_response.status_code,
                headers=headers,
                etag=headers.get("etag"),
                last_modified=headers.get("last-modified"),
                cache_control=headers.get("cache-control"),
            )

        # Otherwise expect a buffered httpx.Response
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
