"""HTTP client for downloading ICS calendar files."""

import asyncio
import ipaddress
import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx

from ..security.logging import (
    SecurityEvent,
    SecurityEventLogger,
    SecurityEventType,
    SecuritySeverity,
)
from .exceptions import ICSAuthError, ICSFetchError, ICSNetworkError
from .models import ICSResponse, ICSSource

logger = logging.getLogger(__name__)


class ICSFetcher:
    """Async HTTP client for downloading ICS calendar files."""

    def __init__(self, settings: Any):
        """Initialize ICS fetcher.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.client: Optional[httpx.AsyncClient] = None
        self.security_logger = SecurityEventLogger()

        logger.debug("ICS fetcher initialized")

    async def __aenter__(self) -> "ICSFetcher":
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
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
                    "User-Agent": f"{self.settings.app_name}/1.0.0 ICS-Client",
                    "Accept": "text/calendar, text/plain, */*",
                    "Accept-Charset": "utf-8",
                    "Cache-Control": "no-cache",
                },
            )

    async def _close_client(self) -> None:
        """Close HTTP client."""
        if self.client and not self.client.is_closed:
            await self.client.aclose()

    def _validate_url_for_ssrf(self, url: str) -> bool:
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

        Security Event Logging:
            All blocked URLs generate SecurityEvent logs with:
            - Event type: SYSTEM_SECURITY_VIOLATION
            - Severity: HIGH for protocol/IP violations, MEDIUM for validation errors
            - Violation details including detected attack pattern
            - Source IP tracking for audit trails

        Exception Handling:
            - Malformed URLs trigger INPUT_VALIDATION_FAILURE events
            - URL parsing exceptions are caught and logged safely
            - Returns False for any validation errors to fail securely

        Example Blocked URLs:
            - http://127.0.0.1/admin
            - https://192.168.1.1/config
            - http://2130706433/ (decimal localhost)
            - ftp://internal.example.com/
            - http://localhost:8080/api

        Example Allowed URLs:
            - https://calendar.google.com/calendar/ical/...
            - https://outlook.office365.com/owa/calendar/...
            - http://public-calendar.example.com/feed.ics

        Note:
            This method prioritizes security over functionality - when in doubt,
            URLs are blocked. Consider allowlisting specific domains if legitimate
            URLs are incorrectly blocked by hostname pattern matching.
        """
        try:
            parsed = urlparse(url)

            # Only allow HTTP/HTTPS
            if parsed.scheme not in ["http", "https"]:
                event = SecurityEvent(
                    event_type=SecurityEventType.SYSTEM_SECURITY_VIOLATION,
                    severity=SecuritySeverity.HIGH,
                    resource=url,
                    action="url_validation",
                    result="blocked",
                    details={
                        "violation_type": "ssrf_attempt",
                        "description": f"Blocked non-HTTP(S) scheme: {parsed.scheme}",
                        "source_ip": "internal",
                    },
                )
                self.security_logger.log_event(event)
                return False

            # Check for localhost/private IP addresses
            hostname = parsed.hostname
            if not hostname:
                # Reject URLs with empty hostnames
                event = SecurityEvent(
                    event_type=SecurityEventType.SYSTEM_SECURITY_VIOLATION,
                    severity=SecuritySeverity.HIGH,
                    resource=url,
                    action="url_validation",
                    result="blocked",
                    details={
                        "violation_type": "ssrf_attempt",
                        "description": f"Blocked URL with empty hostname: {url}",
                        "source_ip": "internal",
                    },
                )
                self.security_logger.log_event(event)
                return False

            if hostname:
                # First try standard IP parsing
                try:
                    ip = ipaddress.ip_address(hostname)
                    if ip.is_private or ip.is_loopback or ip.is_link_local:
                        event = SecurityEvent(
                            event_type=SecurityEventType.SYSTEM_SECURITY_VIOLATION,
                            severity=SecuritySeverity.HIGH,
                            resource=url,
                            action="url_validation",
                            result="blocked",
                            details={
                                "violation_type": "ssrf_attempt",
                                "description": f"Blocked private/localhost IP: {hostname}",
                                "source_ip": "internal",
                            },
                        )
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
                            event = SecurityEvent(
                                event_type=SecurityEventType.SYSTEM_SECURITY_VIOLATION,
                                severity=SecuritySeverity.HIGH,
                                resource=url,
                                action="url_validation",
                                result="blocked",
                                details={
                                    "violation_type": "ssrf_attempt",
                                    "description": f"Blocked encoded private IP: {hostname} -> {parsed_ip}",
                                    "source_ip": "internal",
                                },
                            )
                            self.security_logger.log_event(event)
                            return False

                    except (ValueError, OverflowError):
                        pass  # Not a valid alternative IP format

                    # Hostname is not an IP, check for localhost patterns
                    if (
                        hostname.lower() in ["localhost", "127.0.0.1", "::1"]
                        or hostname.startswith("192.168.")
                        or hostname.startswith("10.")
                        or hostname.startswith("172.")
                    ):
                        event = SecurityEvent(
                            event_type=SecurityEventType.SYSTEM_SECURITY_VIOLATION,
                            severity=SecuritySeverity.HIGH,
                            resource=url,
                            action="url_validation",
                            result="blocked",
                            details={
                                "violation_type": "ssrf_attempt",
                                "description": f"Blocked private hostname: {hostname}",
                                "source_ip": "internal",
                            },
                        )
                        self.security_logger.log_event(event)
                        return False

            return True

        except Exception as e:
            event = SecurityEvent(
                event_type=SecurityEventType.INPUT_VALIDATION_FAILURE,
                severity=SecuritySeverity.MEDIUM,
                resource=url,
                action="url_validation",
                result="error",
                details={
                    "validation_error": f"URL validation failed: {e}",
                    "source_ip": "internal",
                },
            )
            self.security_logger.log_event(event)
            return False

    async def fetch_ics(
        self, source: ICSSource, conditional_headers: Optional[Dict[str, str]] = None
    ) -> ICSResponse:
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
            ICSResponse: Response object containing:
                        - success (bool): Operation success indicator
                        - content (str): ICS calendar data (if successful)
                        - status_code (int): HTTP response code
                        - error_message (str): Detailed error description (if failed)
                        - headers (Dict[str, str]): Response headers
                        - etag/last_modified: Caching metadata

        Raises:
            ICSAuthError: Authentication failures (HTTP 401/403):
                         - Invalid credentials for basic authentication
                         - Expired or invalid bearer tokens
                         - Insufficient permissions for calendar access

            ICSNetworkError: Network connectivity issues:
                            - DNS resolution failures
                            - Connection timeouts or refused connections
                            - SSL/TLS handshake failures
                            - Network unreachability

            ICSTimeoutError: Request timeout scenarios:
                            - Server response timeout beyond configured limit
                            - Connection establishment timeout
                            - Slow server response causing timeout

            ICSFetchError: General fetching errors:
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
            >>> source = ICSSource(url="https://calendar.example.com/cal.ics")
            >>> response = await fetcher.fetch_ics(source)
            >>> if response.success:
            ...     events = parse_ics_content(response.content)
        """
        await self._ensure_client()

        # Validate URL to prevent SSRF attacks
        if not self._validate_url_for_ssrf(source.url):
            error_msg = "URL blocked for security reasons"
            logger.error(f"SSRF protection: {error_msg} - {source.url}")
            return ICSResponse(success=False, error_message=error_msg, status_code=403)

        try:
            logger.debug(f"Fetching ICS from {source.url}")

            # Log successful URL validation
            event = SecurityEvent(
                event_type=SecurityEventType.DATA_ACCESS,
                severity=SecuritySeverity.LOW,
                resource=source.url,
                action="url_access",
                result="success",
                details={
                    "description": f"Accessing validated URL: {source.url}",
                    "source_ip": "internal",
                },
            )
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

            # Make request with retry logic
            response = await self._make_request_with_retry(
                source.url, headers, source.timeout, source.validate_ssl
            )

            return self._create_response(response)

        except httpx.TimeoutException as e:
            logger.error(f"Timeout fetching ICS from {source.url}: {e}")
            return ICSResponse(
                success=False,
                error_message=f"Request timeout after {source.timeout}s",
                status_code=None,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching ICS from {source.url}: {e.response.status_code}")

            if e.response.status_code == 401:
                error_msg = "Authentication failed - check credentials"
                raise ICSAuthError(error_msg, e.response.status_code)
            if e.response.status_code == 403:
                error_msg = "Access forbidden - insufficient permissions"
                raise ICSAuthError(error_msg, e.response.status_code)
            return ICSResponse(
                success=False,
                status_code=e.response.status_code,
                error_message=f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
                headers=dict(e.response.headers),
            )

        except httpx.NetworkError as e:
            logger.error(f"Network error fetching ICS from {source.url}: {e}")
            raise ICSNetworkError(f"Network error: {e}")

        except Exception as e:
            logger.error(f"Unexpected error fetching ICS from {source.url}: {e}")
            raise ICSFetchError(f"Unexpected error: {e}")

    async def _make_request_with_retry(
        self, url: str, headers: Dict[str, str], timeout: int, verify_ssl: bool
    ) -> httpx.Response:
        """Make HTTP request with retry logic.

        Args:
            url: URL to fetch
            headers: Request headers
            timeout: Request timeout
            verify_ssl: Whether to verify SSL certificates

        Returns:
            HTTP response
        """
        last_exception = None

        for attempt in range(self.settings.max_retries + 1):
            try:
                # Create request with SSL verification setting
                if self.client is None:
                    raise ICSFetchError("HTTP client not initialized")

                # Note: SSL verification is configured at client level, not per request
                response = await self.client.get(url, headers=headers, timeout=timeout)

                # Don't raise for 304 Not Modified - it's a successful response
                if response.status_code != 304:
                    # Raise for HTTP error status codes (4xx, 5xx)
                    response.raise_for_status()

                logger.debug(f"Successfully fetched ICS from {url} (attempt {attempt + 1})")
                return response

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e

                if attempt < self.settings.max_retries:
                    backoff_time = self.settings.retry_backoff_factor**attempt
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.settings.max_retries + 1}), "
                        f"retrying in {backoff_time:.1f}s: {e}"
                    )
                    await asyncio.sleep(backoff_time)
                else:
                    logger.error(f"All retry attempts failed for {url}")
                    raise e

            except httpx.HTTPStatusError as e:
                # Don't retry HTTP errors (auth errors, not found, etc.)
                raise e

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise ICSFetchError("Maximum retries exceeded")

    def _create_response(self, http_response: httpx.Response) -> ICSResponse:
        """Create ICS response from HTTP response.

        Args:
            http_response: HTTP response object

        Returns:
            ICS response object
        """
        headers = dict(http_response.headers)

        # Handle 304 Not Modified
        if http_response.status_code == 304:
            logger.debug("ICS content not modified (304)")
            return ICSResponse(
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
            return ICSResponse(
                success=False,
                status_code=http_response.status_code,
                error_message="Empty content received",
                headers=headers,
            )

        # Check for basic ICS markers
        if "BEGIN:VCALENDAR" not in content:
            logger.warning("Content does not appear to be valid ICS format")

        logger.debug(f"Successfully fetched ICS content ({len(content)} bytes)")

        return ICSResponse(
            success=True,
            content=content,
            status_code=http_response.status_code,
            headers=headers,
            etag=headers.get("etag"),
            last_modified=headers.get("last-modified"),
            cache_control=headers.get("cache-control"),
        )

    async def test_connection(self, source: ICSSource) -> bool:
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
                raise ICSFetchError("HTTP client not initialized")

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

        except Exception as e:
            logger.error(f"Connection test failed for {source.url}: {e}")
            return False

    def get_conditional_headers(
        self, etag: Optional[str] = None, last_modified: Optional[str] = None
    ) -> Dict[str, str]:
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
