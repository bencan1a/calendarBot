"""HTTP client utility for Calendar Bot.

This module provides a lightweight HTTP client for fetching HTML content
from a local webserver. It is primarily used by the e-paper renderer to
fetch HTML content from the shared webserver instead of generating it directly.
"""

import asyncio
import logging
import socket
import time
import urllib.error
import urllib.request
from typing import Optional
from urllib.parse import urlencode, urlparse

logger = logging.getLogger(__name__)


class HTTPClient:
    """Lightweight HTTP client for fetching HTML content.

    This class provides methods for fetching HTML content from a local
    webserver with proper error handling and timeout management.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        timeout: float = 5.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize HTTP client.

        Args:
            base_url: Base URL of the webserver to fetch from
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retry attempts in seconds

        Raises:
            ValueError: If base_url uses an unsafe scheme
        """
        # Validate base URL scheme
        parsed_base = urlparse(base_url)
        if parsed_base.scheme not in ("http", "https"):
            raise ValueError(f"Base URL must use HTTP or HTTPS scheme, got: {parsed_base.scheme}")

        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        logger.debug(f"HTTPClient initialized with base_url={base_url}, timeout={timeout}s")

    def fetch_html(
        self,
        path: str = "/",
        params: Optional[dict[str, str]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> str:
        """Fetch HTML content from the webserver.

        Args:
            path: URL path to fetch
            params: Optional query parameters
            headers: Optional HTTP headers

        Returns:
            HTML content as string

        Raises:
            ConnectionError: If connection to webserver fails
            TimeoutError: If request times out
            RuntimeError: If request fails for other reasons
        """
        url = self._build_url(path, params)
        request_headers = self._prepare_headers(headers)

        # Log URL scheme for security validation
        parsed_url = urlparse(url)
        logger.debug(
            f"Fetching HTML from {url} (base_url: {self.base_url}, scheme: {parsed_url.scheme})"
        )

        # Security check: only allow HTTP/HTTPS schemes
        if parsed_url.scheme not in ("http", "https"):
            logger.error(f"Unsafe URL scheme detected: {parsed_url.scheme} in URL: {url}")
            raise ValueError(f"Only HTTP and HTTPS schemes are allowed, got: {parsed_url.scheme}")

        for attempt in range(1, self.max_retries + 1):
            try:
                request = urllib.request.Request(url, headers=request_headers)

                # Use explicit HTTP/HTTPS handlers for security (resolves B310)
                handler: urllib.request.BaseHandler
                if parsed_url.scheme == "https":
                    handler = urllib.request.HTTPSHandler()
                elif parsed_url.scheme == "http":
                    handler = urllib.request.HTTPHandler()
                else:
                    # This should never happen due to our earlier validation, but add as failsafe
                    self._raise_scheme_error(parsed_url.scheme)
                    return ""  # This line will never execute, but satisfies type checker

                opener = urllib.request.build_opener(handler)
                with opener.open(request, timeout=self.timeout) as response:
                    html_content = response.read().decode("utf-8")
                    logger.debug(
                        f"Successfully fetched HTML from {url} ({len(html_content)} bytes)"
                    )
                    return html_content

            except urllib.error.URLError as e:
                self._handle_url_error(e, attempt)
            except socket.timeout as e:
                self._handle_socket_timeout(e, attempt)
            except Exception as e:
                self._handle_unexpected_error(e, attempt)

            # Wait before retrying
            if attempt < self.max_retries:
                logger.debug(f"Retrying in {self.retry_delay}s...")
                # Use time.sleep instead of asyncio.run(asyncio.sleep())
                time.sleep(self.retry_delay)

        # This should never be reached due to the exception handling above
        raise RuntimeError("Unexpected error in fetch_html")

    async def fetch_html_async(
        self,
        path: str = "/",
        params: Optional[dict[str, str]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> str:
        """Fetch HTML content from the webserver asynchronously.

        Args:
            path: URL path to fetch
            params: Optional query parameters
            headers: Optional HTTP headers

        Returns:
            HTML content as string

        Raises:
            ConnectionError: If connection to webserver fails
            TimeoutError: If request times out
            RuntimeError: If request fails for other reasons
        """
        # Use asyncio.to_thread to run the synchronous fetch_html in a separate thread
        # This avoids blocking the event loop while waiting for the HTTP response
        return await asyncio.to_thread(
            self.fetch_html,
            path=path,
            params=params,
            headers=headers,
        )

    def fetch_calendar_html(
        self,
        days: int = 1,
        debug_time: Optional[str] = None,
    ) -> str:
        """Fetch calendar HTML content from the webserver.

        This is a convenience method for fetching calendar HTML with
        appropriate query parameters.

        Args:
            days: Number of days to fetch events for
            debug_time: Optional debug time override (ISO format)

        Returns:
            Calendar HTML content as string

        Raises:
            ConnectionError: If connection to webserver fails
            TimeoutError: If request times out
            RuntimeError: If request fails for other reasons
        """
        params = {"days": str(days)}
        if debug_time:
            params["debug_time"] = debug_time

        return self.fetch_html(path="/calendar", params=params)

    async def fetch_calendar_html_async(
        self,
        days: int = 1,
        debug_time: Optional[str] = None,
    ) -> str:
        """Fetch calendar HTML content from the webserver asynchronously.

        This is a convenience method for fetching calendar HTML with
        appropriate query parameters.

        Args:
            days: Number of days to fetch events for
            debug_time: Optional debug time override (ISO format)

        Returns:
            Calendar HTML content as string

        Raises:
            ConnectionError: If connection to webserver fails
            TimeoutError: If request times out
            RuntimeError: If request fails for other reasons
        """
        params = {"days": str(days)}
        if debug_time:
            params["debug_time"] = debug_time

        return await self.fetch_html_async(path="/calendar", params=params)

    def _build_url(self, path: str, params: Optional[dict[str, str]] = None) -> str:
        """Build a complete URL from path and parameters.

        Args:
            path: URL path
            params: Optional query parameters

        Returns:
            Complete URL as string
        """
        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path

        # Build base URL
        url = self.base_url + path

        # Add query parameters if provided
        if params:
            query_string = urlencode(params)
            url = f"{url}?{query_string}"
            logger.debug(f"Built URL with encoded parameters: {url}")

        return url

    def _raise_scheme_error(self, scheme: str) -> None:
        """Raise a ValueError for unsupported URL schemes.

        Args:
            scheme: The unsupported URL scheme

        Raises:
            ValueError: Always raises for unsupported schemes
        """
        raise ValueError(f"Unsupported URL scheme: {scheme}")

    def _handle_url_error(self, error: urllib.error.URLError, attempt: int) -> None:
        """Handle URLError exceptions during HTTP requests."""
        if isinstance(error.reason, socket.timeout):
            logger.warning(f"Request timed out (attempt {attempt}/{self.max_retries}): {error}")
            if attempt == self.max_retries:
                raise TimeoutError(
                    f"Request timed out after {self.max_retries} attempts: {error}"
                ) from error
        elif isinstance(error.reason, ConnectionRefusedError):
            logger.warning(f"Connection refused (attempt {attempt}/{self.max_retries}): {error}")
            if attempt == self.max_retries:
                raise ConnectionError(
                    f"Connection refused after {self.max_retries} attempts: {error}"
                ) from error
        else:
            logger.warning(f"URL error (attempt {attempt}/{self.max_retries}): {error}")
            if attempt == self.max_retries:
                raise RuntimeError(
                    f"URL error after {self.max_retries} attempts: {error}"
                ) from error

    def _handle_socket_timeout(self, error: socket.timeout, attempt: int) -> None:
        """Handle socket timeout exceptions during HTTP requests."""
        logger.warning(f"Socket timeout (attempt {attempt}/{self.max_retries}): {error}")
        if attempt == self.max_retries:
            raise TimeoutError(
                f"Socket timeout after {self.max_retries} attempts: {error}"
            ) from error

    def _handle_unexpected_error(self, error: Exception, attempt: int) -> None:
        """Handle unexpected exceptions during HTTP requests."""
        logger.warning(f"Unexpected error (attempt {attempt}/{self.max_retries}): {error}")
        if attempt == self.max_retries:
            raise RuntimeError(
                f"Failed to fetch HTML after {self.max_retries} attempts: {error}"
            ) from error

    def _prepare_headers(self, headers: Optional[dict[str, str]] = None) -> dict[str, str]:
        """Prepare HTTP headers for the request.

        Args:
            headers: Optional user-provided headers

        Returns:
            Complete headers dictionary
        """
        # Default headers
        default_headers = {
            "User-Agent": "CalendarBot/1.0",
            "Accept": "text/html,application/xhtml+xml",
        }

        # Merge with user-provided headers
        if headers:
            default_headers.update(headers)

        return default_headers


def is_webserver_running(host: str = "127.0.0.1", port: int = 8080, timeout: float = 1.0) -> bool:
    """Check if a webserver is running at the specified host and port.

    Args:
        host: Webserver host
        port: Webserver port
        timeout: Connection timeout in seconds

    Returns:
        True if webserver is running, False otherwise
    """
    try:
        # Try to connect to the webserver
        with socket.create_connection((host, port), timeout=timeout):
            logger.debug(f"Webserver is running at {host}:{port}")
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        logger.debug(f"Webserver is not running at {host}:{port}")
        return False


def wait_for_webserver(
    host: str = "127.0.0.1",
    port: int = 8080,
    timeout: float = 30.0,
    check_interval: float = 0.5,
) -> bool:
    """Wait for a webserver to become available.

    Args:
        host: Webserver host
        port: Webserver port
        timeout: Maximum time to wait in seconds
        check_interval: Interval between checks in seconds

    Returns:
        True if webserver became available within timeout, False otherwise
    """
    logger.debug(f"Waiting for webserver at {host}:{port} (timeout: {timeout}s)")

    start_time = time.time()
    while (time.time() - start_time) < timeout:
        if is_webserver_running(host, port, timeout=check_interval):
            elapsed = time.time() - start_time
            logger.info(f"Webserver at {host}:{port} is available (waited {elapsed:.2f}s)")
            return True

        # Wait before checking again
        time.sleep(check_interval)

    logger.warning(f"Timed out waiting for webserver at {host}:{port} after {timeout}s")
    return False


async def wait_for_webserver_async(
    host: str = "127.0.0.1",
    port: int = 8080,
    timeout: float = 30.0,
    check_interval: float = 0.5,
) -> bool:
    """Wait for a webserver to become available asynchronously.

    Args:
        host: Webserver host
        port: Webserver port
        timeout: Maximum time to wait in seconds
        check_interval: Interval between checks in seconds

    Returns:
        True if webserver became available within timeout, False otherwise
    """
    logger.debug(f"Waiting for webserver at {host}:{port} (timeout: {timeout}s)")

    start_time = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        # Use asyncio.to_thread to run the synchronous is_webserver_running in a separate thread
        if await asyncio.to_thread(is_webserver_running, host, port, check_interval):
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(f"Webserver at {host}:{port} is available (waited {elapsed:.2f}s)")
            return True

        # Wait before checking again
        await asyncio.sleep(check_interval)

    logger.warning(f"Timed out waiting for webserver at {host}:{port} after {timeout}s")
    return False
