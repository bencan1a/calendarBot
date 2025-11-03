"""Response caching for Alexa handlers tied to event window version.

This module provides a cache for Alexa responses that automatically invalidates
when the event window is refreshed. Cache keys are based on handler name and
request parameters, ensuring consistent responses within a window version.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ResponseCache:
    """Cache for Alexa responses tied to event window version.

    The cache automatically invalidates all entries when the event window
    is refreshed, ensuring responses stay synchronized with current events.
    Each cache entry is associated with a window version number.

    Example:
        cache = ResponseCache(max_size=100)

        # Generate cache key
        key = cache.generate_key("NextMeetingHandler", {"tz": "America/Los_Angeles"})

        # Check cache
        cached = cache.get(key)
        if cached:
            return cached

        # Process and cache
        response = process_request()
        cache.set(key, response)

        # On window refresh
        cache.invalidate_all()
    """

    def __init__(self, max_size: int = 100):
        """Initialize response cache.

        Args:
            max_size: Maximum number of cached responses (FIFO eviction when full)
        """
        self.cache: dict[str, tuple[dict[str, Any], int]] = {}  # key -> (response, window_version)
        self.max_size = max_size
        self.current_window_version = 0
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "invalidations": 0,
        }

    def generate_key(self, handler_name: str, params: dict[str, Any]) -> str:
        """Generate cache key from handler and params.

        The key incorporates:
        - Handler name (ensures different handlers don't collide)
        - Window version (auto-invalidates on refresh)
        - Request parameters (handles different queries)

        Args:
            handler_name: Name of the handler (e.g., "NextMeetingHandler")
            params: Request parameters to include in key

        Returns:
            Cache key string

        Example:
            >>> cache = ResponseCache()
            >>> key = cache.generate_key("NextMeetingHandler", {"tz": "UTC"})
            >>> key
            'NextMeetingHandler:0:5d41402abc4b2a76b9719d911017c592'
        """
        # Sort params for consistent hashing
        param_str = json.dumps(params, sort_keys=True)
        # MD5 is used here for speed, not security - cache keys don't need
        # cryptographic properties, just collision resistance for deduplication
        param_hash = hashlib.md5(param_str.encode()).hexdigest()
        return f"{handler_name}:{self.current_window_version}:{param_hash}"

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Get cached response if valid.

        Args:
            key: Cache key from generate_key()

        Returns:
            Cached response dict or None if not found/invalid
        """
        if key in self.cache:
            response, window_version = self.cache[key]
            if window_version == self.current_window_version:
                self.stats["hits"] += 1
                logger.debug("Cache hit for key: %s", key)
                return response
            # Stale entry from previous window version
            logger.debug("Cache entry stale (version %d != %d): %s",
                       window_version, self.current_window_version, key)

        self.stats["misses"] += 1
        logger.debug("Cache miss for key: %s", key)
        return None

    def set(self, key: str, response: dict[str, Any]) -> None:
        """Cache response for current window version.

        Args:
            key: Cache key from generate_key()
            response: Response dict to cache
        """
        self.cache[key] = (response, self.current_window_version)
        logger.debug("Cached response for key: %s (version %d)",
                    key, self.current_window_version)

        # FIFO eviction if needed (removes oldest inserted entry)
        # Note: This is not true LRU (which would track access patterns).
        # FIFO is simpler and sufficient for this use case where most
        # queries are unique per user within a window.
        if len(self.cache) > self.max_size:
            # Remove oldest entry (first in dict for Python 3.7+ ordered dicts)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            self.stats["evictions"] += 1
            logger.debug("Evicted oldest cache entry: %s (cache size: %d/%d)",
                        oldest_key, len(self.cache), self.max_size)

    def invalidate_all(self) -> None:
        """Invalidate all cached responses (call on window refresh).

        This increments the window version, which causes all existing
        cache entries to be considered stale on the next get().
        The cache dict is also cleared to free memory.
        """
        old_version = self.current_window_version
        old_size = len(self.cache)

        self.current_window_version += 1
        self.cache.clear()
        self.stats["invalidations"] += 1

        logger.info(
            "Invalidated all cache entries (version %d → %d, cleared %d entries)",
            old_version, self.current_window_version, old_size
        )

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache statistics including:
            - hits: Number of cache hits
            - misses: Number of cache misses
            - hit_rate: Percentage of hits (0-100)
            - evictions: Number of LRU evictions
            - invalidations: Number of full invalidations
            - current_size: Current number of cached entries
            - max_size: Maximum cache size
            - window_version: Current window version
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": round(hit_rate, 2),
            "evictions": self.stats["evictions"],
            "invalidations": self.stats["invalidations"],
            "current_size": len(self.cache),
            "max_size": self.max_size,
            "window_version": self.current_window_version,
        }

    def clear_stats(self) -> None:
        """Clear cache statistics (useful for testing)."""
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "invalidations": 0,
        }
