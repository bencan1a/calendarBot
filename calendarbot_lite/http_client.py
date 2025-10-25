"""Shared HTTP client manager optimized for Pi Zero 2W performance.

This module provides a connection pool manager that eliminates per-fetch
httpx.AsyncClient creation and reduces network overhead through connection reuse.
Configured with Pi Zero 2W-specific limits to balance performance and resource usage.
"""

import asyncio
import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Global state for shared HTTP clients
_shared_clients: dict[str, httpx.AsyncClient] = {}
_client_health: dict[str, dict[str, float]] = {}
_client_lock = asyncio.Lock()

# Pi Zero 2W optimized configuration
_PI_ZERO_LIMITS = httpx.Limits(
    max_connections=4,  # Conservative limit for low-memory device
    max_keepalive_connections=2,  # Minimal keepalive to preserve memory
)

_PI_ZERO_TIMEOUT = httpx.Timeout(
    connect=10.0,  # Conservative connection timeout
    read=30.0,  # Adequate for moderate ICS files
    write=10.0,  # Standard write timeout
    pool=30.0,  # Pool timeout to prevent hanging connections
)

# Buffer threshold for streaming vs buffering decision (50 KiB)
BUFFER_THRESHOLD_BYTES = 50 * 1024

# Initial peek size for content analysis (1 KiB)
INITIAL_PEEK_SIZE = 1024

# Health check thresholds
HEALTH_ERROR_THRESHOLD = 3  # Recreate client after 3 consecutive errors
HEALTH_TIMEOUT_SECONDS = 300  # Consider client unhealthy after 5 minutes of errors


async def get_shared_client(
    client_id: str = "default",
    limits: Optional[httpx.Limits] = None,
    timeout: Optional[httpx.Timeout] = None,
) -> httpx.AsyncClient:
    """Get or create a shared HTTP client with connection pooling.

    Args:
        client_id: Identifier for the client (allows multiple clients if needed)
        limits: Custom connection limits (defaults to Pi Zero 2W optimized)
        timeout: Custom timeout configuration (defaults to Pi Zero 2W optimized)

    Returns:
        Shared httpx.AsyncClient configured for Pi Zero 2W performance

    Raises:
        RuntimeError: If client creation fails
    """
    async with _client_lock:
        # Check if we need to recreate an unhealthy client
        await _recreate_client_if_unhealthy(client_id)

        if client_id not in _shared_clients or _shared_clients[client_id].is_closed:
            try:
                # Use Pi Zero 2W optimized defaults
                effective_limits = limits or _PI_ZERO_LIMITS
                effective_timeout = timeout or _PI_ZERO_TIMEOUT

                logger.debug(
                    "Creating shared HTTP client '%s' with limits: max_connections=%d, "
                    "max_keepalive=%d",
                    client_id,
                    effective_limits.max_connections,
                    effective_limits.max_keepalive_connections,
                )

                _shared_clients[client_id] = httpx.AsyncClient(
                    limits=effective_limits,
                    timeout=effective_timeout,
                    follow_redirects=True,
                    verify=True,  # SSL verification
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    },
                )

                # Initialize health tracking
                _client_health[client_id] = {
                    "error_count": 0,
                    "last_error_time": 0,
                    "created_time": time.time(),
                }

                logger.info("Created shared HTTP client '%s'", client_id)

            except Exception as e:
                logger.exception("Failed to create shared HTTP client '%s'", client_id)
                raise RuntimeError(f"Failed to create shared HTTP client: {e}") from e

        return _shared_clients[client_id]


async def close_all_clients() -> None:
    """Close all shared HTTP clients and clean up resources.

    This should be called during application shutdown to ensure
    proper cleanup of HTTP connections and resources.
    """
    async with _client_lock:
        for client_id, client in _shared_clients.items():
            try:
                if not client.is_closed:
                    await client.aclose()
                    logger.debug("Closed shared HTTP client '%s'", client_id)
            except Exception as e:  # noqa: PERF203
                logger.warning("Error closing shared HTTP client '%s': %s", client_id, e)

        _shared_clients.clear()
        _client_health.clear()
        logger.info("All shared HTTP clients closed")


async def record_client_error(client_id: str = "default") -> None:
    """Record an error for health tracking.

    Args:
        client_id: Identifier of the client that encountered an error
    """
    async with _client_lock:
        if client_id not in _client_health:
            _client_health[client_id] = {
                "error_count": 0,
                "last_error_time": 0,
                "created_time": time.time(),
            }

        health = _client_health[client_id]
        health["error_count"] += 1
        health["last_error_time"] = time.time()

        logger.debug(
            "Recorded error for client '%s', total errors: %d",
            client_id,
            health["error_count"],
        )


async def record_client_success(client_id: str = "default") -> None:
    """Record a successful operation for health tracking.

    Args:
        client_id: Identifier of the client that had a successful operation
    """
    async with _client_lock:
        if client_id in _client_health:
            _client_health[client_id]["error_count"] = 0
            logger.debug("Reset error count for healthy client '%s'", client_id)


async def _recreate_client_if_unhealthy(client_id: str) -> None:
    """Recreate client if it's determined to be unhealthy.

    Args:
        client_id: Identifier of the client to check
    """
    if client_id not in _client_health:
        return

    health = _client_health[client_id]
    current_time = time.time()

    # Check if client should be considered unhealthy
    should_recreate = (
        health["error_count"] >= HEALTH_ERROR_THRESHOLD
        and (current_time - health["last_error_time"]) < HEALTH_TIMEOUT_SECONDS
    )

    if should_recreate and client_id in _shared_clients:
        logger.warning(
            "Recreating unhealthy client '%s' due to %d errors in last %d seconds",
            client_id,
            health["error_count"],
            HEALTH_TIMEOUT_SECONDS,
        )

        try:
            old_client = _shared_clients[client_id]
            if not old_client.is_closed:
                await old_client.aclose()
        except Exception as e:
            logger.warning("Error closing unhealthy client '%s': %s", client_id, e)

        # Remove from tracking so it gets recreated
        del _shared_clients[client_id]
        del _client_health[client_id]


async def get_fallback_client(
    timeout: Optional[httpx.Timeout] = None,
) -> httpx.AsyncClient:
    """Create a temporary client for single-request fallback scenarios.

    This is used when the shared client fails and we need to make
    an isolated request without affecting the shared client pool.

    Args:
        timeout: Custom timeout configuration

    Returns:
        Temporary httpx.AsyncClient for single use
    """
    effective_timeout = timeout or _PI_ZERO_TIMEOUT

    logger.debug("Creating fallback HTTP client for single request")

    return httpx.AsyncClient(
        timeout=effective_timeout,
        follow_redirects=True,
        verify=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
    )


class StreamingHTTPResponse:
    """Wrapper for streaming HTTP response with peek capability.

    This class provides a way to peek at the initial bytes of an HTTP response
    to make buffering vs streaming decisions, while preserving the ability to
    read the full response content.
    """

    def __init__(self, response: httpx.Response):
        """Initialize streaming response wrapper.

        Args:
            response: The httpx.Response to wrap
        """
        self.response = response
        self._initial_bytes: Optional[bytes] = None
        self._peek_consumed = False

    async def peek_initial_bytes(self, size: int = INITIAL_PEEK_SIZE) -> bytes:
        """Peek at initial bytes without consuming the stream.

        Args:
            size: Number of bytes to peek at

        Returns:
            Initial bytes from the response

        Raises:
            RuntimeError: If peek has already been consumed
        """
        if self._peek_consumed:
            raise RuntimeError("Peek has already been consumed")

        if self._initial_bytes is None:
            # Read initial chunk
            async for chunk in self.response.aiter_bytes(chunk_size=size):
                self._initial_bytes = chunk
                break
            else:
                self._initial_bytes = b""

        return self._initial_bytes

    async def iter_bytes_with_peek(self, chunk_size: int = 8192):
        """Iterate over response bytes including the peeked bytes.

        Args:
            chunk_size: Size of chunks to read

        Yields:
            Chunks of response bytes
        """
        # First yield the peeked bytes if any
        if self._initial_bytes:
            yield self._initial_bytes
            self._peek_consumed = True

        # Then yield the rest
        async for chunk in self.response.aiter_bytes(chunk_size=chunk_size):
            yield chunk

    async def read_full_content(self) -> bytes:
        """Read the full response content including peeked bytes.

        Returns:
            Complete response content as bytes
        """
        chunks = [chunk async for chunk in self.iter_bytes_with_peek()]
        return b"".join(chunks)

    @property
    def headers(self) -> httpx.Headers:
        """Get response headers."""
        return self.response.headers

    @property
    def status_code(self) -> int:
        """Get response status code."""
        return self.response.status_code

    def raise_for_status(self) -> None:
        """Raise an exception if response indicates an error."""
        self.response.raise_for_status()


async def stream_request_with_peek(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs,
) -> StreamingHTTPResponse:
    """Make a streaming HTTP request with peek capability.

    Args:
        client: HTTP client to use
        method: HTTP method (GET, POST, etc.)
        url: URL to request
        **kwargs: Additional arguments for the request

    Returns:
        StreamingHTTPResponse wrapper with peek capability

    Raises:
        httpx.HTTPError: If the request fails
    """
    async with client.stream(method, url, **kwargs) as response:
        # Create a copy of the response for our wrapper
        # Note: We need to be careful here to not double-consume the stream
        return StreamingHTTPResponse(response)
