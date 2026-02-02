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

# Browser-like headers to avoid automated client detection (e.g., Office365)
# Centralized here to ensure consistency across shared and individual clients
DEFAULT_BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
}


def _get_headers_with_correlation_id() -> dict[str, str]:
    """Get default headers with correlation ID for request tracing.

    Returns:
        Headers dictionary with correlation ID if available
    """
    headers = DEFAULT_BROWSER_HEADERS.copy()

    # Add correlation ID if available from context
    try:
        from calendarbot_lite.api.middleware.correlation_id import get_request_id

        request_id = get_request_id()
        if request_id and request_id != "no-request-id":
            headers["X-Request-ID"] = request_id
    except (ImportError, AttributeError):
        # Middleware not available or no request context
        pass

    return headers


# Health check thresholds
HEALTH_ERROR_THRESHOLD = 3  # Recreate client after 3 consecutive errors
HEALTH_TIMEOUT_SECONDS = 300  # Consider client unhealthy after 5 minutes of errors


def _create_ipv4_transport(limits: httpx.Limits) -> httpx.AsyncHTTPTransport:
    """Create HTTP transport configured for IPv4-only connections.

    This prevents IPv6 resolution issues on Pi Zero 2W where IPv6 may be
    configured on the host but DNS resolution fails for certain domains.

    Args:
        limits: Connection limits

    Returns:
        HTTP transport configured to use IPv4 only
    """
    # Create a connection pool with IPv4-only socket family
    # By specifying socket_options, we can control the socket creation
    # The key is to use local_address="0.0.0.0" which forces IPv4 binding
    return httpx.AsyncHTTPTransport(
        limits=limits,
        # Force IPv4 resolution by binding to IPv4 address
        local_address="0.0.0.0",  # nosec B104 - intentional IPv4 binding for client
    )


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
                    "max_keepalive=%d (IPv4-only)",
                    client_id,
                    effective_limits.max_connections,
                    effective_limits.max_keepalive_connections,
                )

                # Create IPv4-only transport to prevent IPv6 DNS resolution issues
                transport = _create_ipv4_transport(effective_limits)

                _shared_clients[client_id] = httpx.AsyncClient(
                    transport=transport,
                    timeout=effective_timeout,
                    follow_redirects=True,
                    verify=True,  # SSL verification
                    headers=DEFAULT_BROWSER_HEADERS,
                )

                # Initialize health tracking
                _client_health[client_id] = {
                    "error_count": 0,
                    "last_error_time": 0,
                    "created_time": time.time(),
                }

                logger.debug("Created shared HTTP client '%s'", client_id)

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
            except Exception as e:
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

    logger.debug("Creating fallback HTTP client for single request (IPv4-only)")

    # Create IPv4-only transport to prevent IPv6 DNS resolution issues
    transport = _create_ipv4_transport(_PI_ZERO_LIMITS)

    return httpx.AsyncClient(
        transport=transport,
        timeout=effective_timeout,
        follow_redirects=True,
        verify=True,
        headers=DEFAULT_BROWSER_HEADERS,
    )
