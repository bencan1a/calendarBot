"""Connection pool management for HTTP client sessions and database connections."""

import time
from typing import Any, Optional

import aiohttp

from ..config.optimization import OptimizationConfig, get_optimization_config
from ..monitoring.connection_pool_monitor import ConnectionPoolMonitor, get_connection_pool_monitor
from ..utils.logging import get_logger
from .cache_keys import generate_http_cache_key
from .cache_manager import CacheManager, get_cache_manager


class ConnectionManagerError(Exception):
    """Base exception for ConnectionManager errors."""


class ConnectionPoolExhaustedError(ConnectionManagerError):
    """Raised when connection pool is exhausted."""


class ConnectionManager:
    """Manages HTTP connection pools and lifecycle for optimal resource utilization.

    This class provides centralized management of aiohttp.ClientSession instances
    with connection pooling to eliminate per-request event loop creation and
    reduce memory overhead.
    """

    def __init__(
        self,
        config: Optional[OptimizationConfig] = None,
        monitor: Optional[ConnectionPoolMonitor] = None,
        cache_manager: Optional[CacheManager] = None,
    ):
        """Initialize connection manager.

        Args:
            config: Optional optimization configuration
            monitor: Optional connection pool performance monitor
            cache_manager: Optional cache manager for HTTP response caching
        """
        self.config = config or get_optimization_config()
        self.monitor = monitor or get_connection_pool_monitor(self.config)
        self.cache_manager = cache_manager or get_cache_manager()
        self.logger = get_logger("connection_manager")

        # Connection pool state
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._startup_complete = False
        self._shutdown_initiated = False

        # Connection statistics (including cache stats)
        self._connection_stats = {
            "sessions_created": 0,
            "connections_acquired": 0,
            "connections_released": 0,
            "failed_acquisitions": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cached_requests": 0,
            "last_health_check": None,
            "startup_time": None,
        }

        # Apply conservative universal limits while respecting config
        self._max_connections = min(self.config.max_connections, 20)
        self._max_connections_per_host = min(self.config.max_connections_per_host, 15)

        self.logger.info(
            f"ConnectionManager initialized with limits: "
            f"max_connections={self._max_connections}, "
            f"max_connections_per_host={self._max_connections_per_host}, "
            f"caching_enabled={self.cache_manager is not None}"
        )

    async def startup(self) -> None:
        """Initialize connection pools and HTTP session.

        Raises:
            ConnectionManagerError: If startup fails
        """
        if self._startup_complete:
            self.logger.warning("ConnectionManager already started")
            return

        try:
            start_time = time.time()

            # Create TCP connector with conservative limits
            connector_config = {
                "limit": self._max_connections,
                "limit_per_host": self._max_connections_per_host,
                "ttl_dns_cache": self.config.connection_ttl,
                "use_dns_cache": True,
                "enable_cleanup_closed": True,
                "keepalive_timeout": 30.0,
                "ssl": False,  # Will be determined per request
            }

            self._connector = aiohttp.TCPConnector(**connector_config)

            # Create HTTP session with pooled connector
            timeout = aiohttp.ClientTimeout(total=30.0, connect=10.0)
            self._http_session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout,
                connector_owner=True,
            )

            self._startup_complete = True
            self._connection_stats["startup_time"] = time.time()
            self._connection_stats["sessions_created"] += 1

            startup_duration = time.time() - start_time

            self.logger.info(f"ConnectionManager startup completed in {startup_duration:.3f}s")

            # Log initial connection pool status
            self.monitor.log_connection_pool_status(
                active=0,
                idle=0,
                max_connections=self._max_connections,
                component="connection_manager",
            )

        except Exception as e:
            self.logger.exception("ConnectionManager startup failed")
            await self._cleanup_on_error()
            raise ConnectionManagerError(f"Startup failed: {e}") from e

    async def shutdown(self) -> None:
        """Gracefully shutdown all connections and cleanup resources."""
        if self._shutdown_initiated:
            return

        self._shutdown_initiated = True
        self.logger.info("ConnectionManager shutdown initiated")

        try:
            if self._http_session:
                await self._http_session.close()
                self._http_session = None

            if self._connector:
                await self._connector.close()
                self._connector = None

            self._startup_complete = False
            self.logger.info("ConnectionManager shutdown completed")

        except Exception:
            self.logger.exception("Error during ConnectionManager shutdown")

    async def get_http_session(self) -> aiohttp.ClientSession:
        """Get shared HTTP session with connection pooling.

        Returns:
            aiohttp.ClientSession: Pooled HTTP session

        Raises:
            ConnectionManagerError: If session not available
        """
        if not self._startup_complete or self._shutdown_initiated:
            raise ConnectionManagerError("ConnectionManager not ready. Call startup() first.")

        if not self._http_session:
            raise ConnectionManagerError("HTTP session not available")

        # Track connection acquisition
        acquisition_start = time.time()
        try:
            # Session is already created and pooled, so this is just a reference
            self._connection_stats["connections_acquired"] += 1

            acquisition_time = time.time() - acquisition_start

            # Log successful acquisition
            self.monitor.log_connection_acquisition(
                wait_time=acquisition_time,
                success=True,
                component="connection_manager",
            )

            return self._http_session

        except Exception:
            acquisition_time = time.time() - acquisition_start
            self._connection_stats["failed_acquisitions"] += 1

            # Log failed acquisition
            self.monitor.log_connection_acquisition(
                wait_time=acquisition_time,
                success=False,
                component="connection_manager",
            )

            self.logger.exception("Failed to acquire HTTP session")
            raise ConnectionManagerError("Session acquisition failed") from None

    async def release_connection(self) -> None:
        """Release connection back to pool.

        Note: With aiohttp.ClientSession, connections are automatically
        returned to the pool after use. This method exists for compatibility
        and monitoring purposes.
        """
        self._connection_stats["connections_released"] += 1

        # Log connection release
        self.monitor.log_connection_release(
            component="connection_manager",
        )

    def get_connection_stats(self) -> dict[str, Any]:
        """Get current connection pool statistics.

        Returns:
            Dictionary containing connection pool statistics
        """
        if not self._startup_complete:
            return {"status": "not_started", "error": "ConnectionManager not started"}

        # Get connector statistics if available
        connector_stats = {}
        if self._connector:
            connector_stats = {
                "limit": getattr(self._connector, "_limit", self._max_connections),
                "limit_per_host": getattr(
                    self._connector, "_limit_per_host", self._max_connections_per_host
                ),
            }

        return {
            "status": "active" if not self._shutdown_initiated else "shutdown",
            "startup_complete": self._startup_complete,
            "max_connections": self._max_connections,
            "max_connections_per_host": self._max_connections_per_host,
            "connection_ttl": self.config.connection_ttl,
            "statistics": self._connection_stats.copy(),
            "connector": connector_stats,
            "session_available": self._http_session is not None,
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform health check on connection pools.

        Returns:
            Dictionary containing health check results
        """
        health_check_time = time.time()
        self._connection_stats["last_health_check"] = health_check_time

        health_status = {
            "timestamp": health_check_time,
            "overall_healthy": True,
            "startup_complete": self._startup_complete,
            "session_available": self._http_session is not None,
            "connector_available": self._connector is not None,
            "shutdown_initiated": self._shutdown_initiated,
            "issues": [],
        }

        # Check session availability
        if not self._http_session:
            health_status["overall_healthy"] = False
            health_status["issues"].append("HTTP session not available")

        # Check connector availability
        if not self._connector:
            health_status["overall_healthy"] = False
            health_status["issues"].append("TCP connector not available")

        # Check if session is closed
        if self._http_session and self._http_session.closed:
            health_status["overall_healthy"] = False
            health_status["issues"].append("HTTP session is closed")

        # Check failure rates
        total_acquisitions = self._connection_stats["connections_acquired"]
        failed_acquisitions = self._connection_stats["failed_acquisitions"]

        if total_acquisitions > 0:
            failure_rate = failed_acquisitions / total_acquisitions
            if failure_rate > 0.1:  # 10% failure rate threshold
                health_status["overall_healthy"] = False
                health_status["issues"].append(f"High failure rate: {failure_rate:.1%}")

        # Log health check to monitor
        if self._connector:
            self.monitor.log_connection_pool_status(
                active=0,  # aiohttp doesn't expose active connection count easily
                idle=0,  # aiohttp doesn't expose idle connection count easily
                max_connections=self._max_connections,
                component="connection_manager",
            )

        self.logger.debug(f"Health check completed: healthy={health_status['overall_healthy']}")

        return health_status

    async def cached_request(
        self, method: str, url: str, cache_ttl: int = 300, **kwargs
    ) -> dict[str, Any]:
        """Make HTTP request with response caching.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            cache_ttl: Cache TTL in seconds (default: 5 minutes)
            **kwargs: Additional arguments for aiohttp request

        Returns:
            dict[str, Any]: HTTP response data (cached or fresh)

        Raises:
            ConnectionManagerError: If request fails
        """
        if not self._startup_complete or self._shutdown_initiated:
            raise ConnectionManagerError("ConnectionManager not ready. Call startup() first.")

        # Only cache GET requests for safety
        cacheable = method.upper() == "GET" and self.cache_manager is not None

        cache_key: Optional[str] = None
        if cacheable:
            # Generate cache key for the request
            params = kwargs.get("params", {})
            headers = kwargs.get("headers", {})
            cache_key = generate_http_cache_key(url, params, headers)

            # Try to get from cache first
            cached_response = await self.cache_manager.get(cache_key, "http_response")
            if cached_response is not None:
                self._connection_stats["cache_hits"] += 1
                self.logger.debug(f"HTTP cache hit: {cache_key}")

                # Return cached response data
                return cached_response

        # Cache miss or non-cacheable request - make actual HTTP request
        if cacheable and cache_key:
            self._connection_stats["cache_misses"] += 1
            self.logger.debug(f"HTTP cache miss: {cache_key}")

        try:
            session = await self.get_http_session()

            # Make the actual HTTP request
            async with session.request(method, url, **kwargs) as response:
                # Read response data
                response_data = {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "url": str(response.url),
                    "method": method,
                    "content": await response.read(),
                    "content_type": response.content_type,
                    "charset": response.charset,
                }

                # Cache successful GET responses (only if we have a valid cache key)
                if cacheable and cache_key and 200 <= response.status < 300:
                    await self.cache_manager.set(
                        cache_key, response_data, "http_response", cache_ttl
                    )
                    self._connection_stats["cached_requests"] += 1
                    self.logger.debug(f"HTTP response cached: {cache_key}")

                return response_data

        except Exception as e:
            self.logger.exception(f"HTTP request failed: {method} {url}")
            raise ConnectionManagerError(f"HTTP request failed: {e}") from e

    async def cached_get(self, url: str, cache_ttl: int = 300, **kwargs) -> dict[str, Any]:
        """Make cached GET request.

        Args:
            url: Request URL
            cache_ttl: Cache TTL in seconds (default: 5 minutes)
            **kwargs: Additional arguments for aiohttp request

        Returns:
            Dict containing response data
        """
        return await self.cached_request("GET", url, cache_ttl, **kwargs)

    async def invalidate_cache_for_url(self, url: str, params: Optional[dict] = None) -> bool:
        """Invalidate cached response for specific URL.

        Args:
            url: URL to invalidate
            params: Optional parameters that were used in the request

        Returns:
            True if cache entry was invalidated
        """
        if not self.cache_manager:
            return False

        try:
            cache_key = generate_http_cache_key(url, params)
            success = await self.cache_manager.delete(cache_key, "http_response")

            if success:
                self.logger.debug(f"HTTP cache invalidated: {cache_key}")

            return success

        except Exception as e:
            self.logger.warning(f"Error invalidating HTTP cache for {url}: {e}")
            return False

    async def close_all_connections(self) -> None:
        """Close all connections immediately (for shutdown/cleanup).

        This is an alias for shutdown() for interface compatibility.
        """
        await self.shutdown()

    async def _cleanup_on_error(self) -> None:
        """Cleanup resources on error during startup."""
        try:
            if self._http_session:
                await self._http_session.close()
                self._http_session = None

            if self._connector:
                await self._connector.close()
                self._connector = None

        except Exception:
            self.logger.exception("Error during cleanup")


# Global connection manager instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager(
    config: Optional[OptimizationConfig] = None,
    monitor: Optional[ConnectionPoolMonitor] = None,
    cache_manager: Optional[CacheManager] = None,
) -> ConnectionManager:
    """Get or create global connection manager instance.

    Args:
        config: Optional optimization configuration
        monitor: Optional connection pool monitor
        cache_manager: Optional cache manager for HTTP response caching

    Returns:
        ConnectionManager: Global connection manager instance
    """
    global _connection_manager  # noqa: PLW0603
    if _connection_manager is None:
        _connection_manager = ConnectionManager(config, monitor, cache_manager)
    return _connection_manager


def reset_connection_manager() -> None:
    """Reset the global connection manager (for testing)."""
    global _connection_manager  # noqa: PLW0603
    if _connection_manager is not None:
        # Note: shutdown() should be called before reset in production
        pass
    _connection_manager = None
