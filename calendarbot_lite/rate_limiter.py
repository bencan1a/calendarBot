"""Lightweight rate limiting middleware for Alexa endpoints.

This module provides simple, memory-efficient rate limiting suitable for
single-instance personal deployments on resource-constrained hardware like
Raspberry Pi Zero 2W.

Design Philosophy:
- In-memory storage (no Redis/database dependency)
- Sliding window algorithm for accurate tracking
- Minimal memory footprint (~1KB per tracked IP/token)
- Automatic cleanup of expired entries
- Thread-safe for asyncio event loop
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # Requests per minute per IP address
    per_ip_limit: int = 100

    # Requests per minute per bearer token
    per_token_limit: int = 500

    # Burst limit: max requests in 10 seconds
    burst_limit: int = 20
    burst_window_seconds: int = 10

    # Cleanup interval for expired entries (seconds)
    cleanup_interval: int = 300


@dataclass
class RateLimitEntry:
    """Tracking entry for rate limiting with sliding window."""

    # List of request timestamps (Unix epoch seconds)
    requests: list[float] = field(default_factory=list)

    # Last cleanup timestamp
    last_cleanup: float = field(default_factory=time.time)


class RateLimiter:
    """Lightweight in-memory rate limiter with sliding window algorithm.

    This implementation uses a sliding window to track requests, providing
    accurate rate limiting without the overhead of external storage systems.

    Memory usage: ~1KB per tracked IP/token (with 500 requests tracked).
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize rate limiter.

        Args:
            config: Rate limit configuration (uses defaults if None)
        """
        self.config = config or RateLimitConfig()

        # Separate tracking for IP and token limits
        self._ip_entries: dict[str, RateLimitEntry] = {}
        self._token_entries: dict[str, RateLimitEntry] = {}

        # Lock for thread-safe access in asyncio
        self._lock = asyncio.Lock()

        # Statistics tracking
        self._stats = {
            "total_requests": 0,
            "rejected_requests": 0,
            "tracked_ips": 0,
            "tracked_tokens": 0,
        }

        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task[None]] = None

        logger.info(
            "RateLimiter initialized: per_ip=%d/min, per_token=%d/min, burst=%d/%ds",
            self.config.per_ip_limit,
            self.config.per_token_limit,
            self.config.burst_limit,
            self.config.burst_window_seconds,
        )

    async def start(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.debug("Rate limiter cleanup task started")

    async def stop(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.debug("Rate limiter cleanup task stopped")

    async def check_rate_limit(
        self, client_ip: str, bearer_token: Optional[str] = None
    ) -> tuple[bool, dict[str, Any]]:
        """Check if request should be allowed based on rate limits.

        Uses sliding window algorithm to track requests accurately.

        Args:
            client_ip: Client IP address
            bearer_token: Optional bearer token for token-based limiting

        Returns:
            Tuple of (allowed: bool, limit_info: dict) where limit_info contains:
            - remaining_ip: Remaining requests for IP
            - remaining_token: Remaining requests for token (if provided)
            - reset_seconds: Seconds until rate limit resets
            - retry_after: Seconds to wait before retrying (if rejected)
        """
        async with self._lock:
            self._stats["total_requests"] += 1
            now = time.time()

            # Check IP-based rate limit
            ip_allowed, ip_info = self._check_limit(
                client_ip,
                self._ip_entries,
                self.config.per_ip_limit,
                60,  # 1 minute window
                now,
            )

            # Check burst limit for IP
            burst_allowed, burst_info = self._check_limit(
                client_ip,
                self._ip_entries,
                self.config.burst_limit,
                self.config.burst_window_seconds,
                now,
            )

            # Check token-based rate limit if token provided
            token_allowed = True
            token_info = {"remaining": self.config.per_token_limit, "reset_seconds": 60}

            if bearer_token:
                token_allowed, token_info = self._check_limit(
                    bearer_token,
                    self._token_entries,
                    self.config.per_token_limit,
                    60,  # 1 minute window
                    now,
                )

            # Request is allowed only if all checks pass
            allowed = ip_allowed and burst_allowed and token_allowed

            if not allowed:
                self._stats["rejected_requests"] += 1
                logger.warning(
                    "Rate limit exceeded: ip=%s, token=%s, ip_allowed=%s, burst_allowed=%s, token_allowed=%s",
                    client_ip[:15] + "..." if len(client_ip) > 15 else client_ip,
                    "***" if bearer_token else None,
                    ip_allowed,
                    burst_allowed,
                    token_allowed,
                )
            else:
                # Record this request
                self._record_request(client_ip, self._ip_entries, now)
                if bearer_token:
                    self._record_request(bearer_token, self._token_entries, now)

            # Update stats
            self._stats["tracked_ips"] = len(self._ip_entries)
            self._stats["tracked_tokens"] = len(self._token_entries)

            # Build response info
            limit_info = {
                "remaining_ip": ip_info["remaining"],
                "remaining_token": token_info["remaining"] if bearer_token else None,
                "reset_seconds": min(ip_info["reset_seconds"], token_info["reset_seconds"]),
                "retry_after": self._calculate_retry_after(
                    ip_info, burst_info, token_info
                ) if not allowed else 0,
            }

            return allowed, limit_info

    def _check_limit(
        self,
        key: str,
        entries: dict[str, RateLimitEntry],
        limit: int,
        window_seconds: int,
        now: float,
    ) -> tuple[bool, dict[str, Any]]:
        """Check rate limit for a specific key using sliding window.

        Args:
            key: Identifier (IP or token)
            entries: Entry storage dict
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            now: Current timestamp

        Returns:
            Tuple of (allowed: bool, info: dict)
        """
        entry = entries.get(key)
        if entry is None:
            # First request from this key
            return True, {"remaining": limit - 1, "reset_seconds": window_seconds}

        # Remove requests outside the sliding window
        cutoff = now - window_seconds
        entry.requests = [ts for ts in entry.requests if ts > cutoff]

        # Check if limit exceeded
        current_count = len(entry.requests)
        allowed = current_count < limit

        # Calculate remaining and reset time
        remaining = max(0, limit - current_count)
        reset_seconds = window_seconds

        if entry.requests:
            # Time until oldest request expires from window
            oldest_request = min(entry.requests)
            reset_seconds = int(window_seconds - (now - oldest_request)) + 1

        return allowed, {"remaining": remaining, "reset_seconds": reset_seconds}

    def _record_request(
        self, key: str, entries: dict[str, RateLimitEntry], now: float
    ) -> None:
        """Record a request for tracking.

        Args:
            key: Identifier (IP or token)
            entries: Entry storage dict
            now: Current timestamp
        """
        if key not in entries:
            entries[key] = RateLimitEntry()

        entries[key].requests.append(now)

    def _calculate_retry_after(
        self, ip_info: dict[str, Any], burst_info: dict[str, Any], token_info: dict[str, Any]
    ) -> int:
        """Calculate Retry-After header value in seconds.

        Returns the minimum time to wait until any limit resets.

        Args:
            ip_info: IP rate limit info
            burst_info: Burst limit info
            token_info: Token rate limit info

        Returns:
            Seconds to wait before retrying
        """
        retry_times = [
            ip_info.get("reset_seconds", 60),
            burst_info.get("reset_seconds", 10),
            token_info.get("reset_seconds", 60),
        ]
        return max(1, min(retry_times))  # At least 1 second, max of shortest reset

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup expired entries.

        Runs periodically to remove entries with no recent requests,
        keeping memory usage minimal.
        """
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._cleanup_expired_entries()
            except asyncio.CancelledError:
                logger.debug("Rate limiter cleanup loop cancelled")
                break
            except Exception as e:
                logger.error("Error in rate limiter cleanup loop: %s", e, exc_info=True)

    async def _cleanup_expired_entries(self) -> None:
        """Remove entries with no requests in the last window period."""
        async with self._lock:
            now = time.time()
            cleanup_cutoff = now - 300  # Keep entries active for 5 minutes

            # Cleanup IP entries
            expired_ips = [
                key
                for key, entry in self._ip_entries.items()
                if not entry.requests or max(entry.requests) < cleanup_cutoff
            ]
            for key in expired_ips:
                del self._ip_entries[key]

            # Cleanup token entries
            expired_tokens = [
                key
                for key, entry in self._token_entries.items()
                if not entry.requests or max(entry.requests) < cleanup_cutoff
            ]
            for key in expired_tokens:
                del self._token_entries[key]

            if expired_ips or expired_tokens:
                logger.debug(
                    "Cleaned up %d expired IP entries and %d expired token entries",
                    len(expired_ips),
                    len(expired_tokens),
                )

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiter statistics.

        Returns:
            Dictionary with rate limiter stats
        """
        return {
            "total_requests": self._stats["total_requests"],
            "rejected_requests": self._stats["rejected_requests"],
            "rejection_rate": (
                self._stats["rejected_requests"] / self._stats["total_requests"]
                if self._stats["total_requests"] > 0
                else 0.0
            ),
            "tracked_ips": self._stats["tracked_ips"],
            "tracked_tokens": self._stats["tracked_tokens"],
            "config": {
                "per_ip_limit": self.config.per_ip_limit,
                "per_token_limit": self.config.per_token_limit,
                "burst_limit": self.config.burst_limit,
                "burst_window_seconds": self.config.burst_window_seconds,
            },
        }


def get_client_ip(request: Any) -> str:
    """Extract client IP address from request.

    Handles X-Forwarded-For header for proxy scenarios.

    Args:
        request: aiohttp request object

    Returns:
        Client IP address as string
    """
    # Check X-Forwarded-For header (for proxies/load balancers)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        return forwarded_for.split(",")[0].strip()

    # Fall back to direct connection IP
    peername = request.transport.get_extra_info("peername")
    if peername:
        return peername[0]

    return "unknown"


def get_bearer_token(request: Any) -> Optional[str]:
    """Extract bearer token from Authorization header.

    Args:
        request: aiohttp request object

    Returns:
        Bearer token string or None if not present
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None
