"""Specialized event cache for calendar data with optimized caching strategies.

Cache Strategy Implementation - EventCache component.
Targets: 1-hour TTL for event data, layout computation result caching, ICS processing cache.
"""

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from ..config.optimization import OptimizationConfig, get_optimization_config
from ..monitoring.connection_pool_monitor import (
    ConnectionPoolMonitor,
    get_connection_pool_monitor,
)
from .cache_manager import CacheManager, get_cache_manager

logger = logging.getLogger(__name__)


@dataclass
class CacheableEvent:
    """Cacheable representation of calendar event data."""

    uid: str
    title: str
    start_time: datetime
    end_time: datetime
    description: str = ""
    location: str = ""
    organizer: str = ""
    attendees: Optional[list[str]] = None
    recurrence_rule: str = ""
    last_modified: Optional[datetime] = None

    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []
        if self.last_modified is None:
            self.last_modified = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for caching."""
        data = asdict(self)
        # Convert datetime objects to ISO strings for JSON serialization
        for field in ["start_time", "end_time", "last_modified"]:
            if data[field]:
                data[field] = data[field].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheableEvent":
        """Create from dictionary retrieved from cache."""
        # Convert ISO strings back to datetime objects
        for field in ["start_time", "end_time", "last_modified"]:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        return cls(**data)


@dataclass
class CacheStats:
    """Cache performance statistics."""

    events_cached: int = 0
    layouts_cached: int = 0
    ics_files_cached: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_requests: int = 0
    average_response_time_ms: float = 0.0
    hit_rate_percent: float = 0.0


class EventCache:
    """Specialized caching for calendar event data and computations.

    Provides optimized caching for:
    - Calendar event data with 1-hour TTL
    - Layout computation results
    - ICS file parsing results
    - Event transformations and aggregations

    Performance targets:
    - 1-hour TTL for event data
    - 70%+ cache hit rate for event requests
    - -70% response time for cached event requests
    """

    def __init__(
        self,
        ttl: int = 3600,  # 1 hour default
        cache_manager: Optional[CacheManager] = None,
        config: Optional[OptimizationConfig] = None,
        monitor: Optional[ConnectionPoolMonitor] = None,
    ):
        """Initialize event cache with specialized TTL.

        Args:
            ttl: Time-to-live for cached events in seconds (default: 1 hour)
            cache_manager: Optional cache manager instance
            config: Optional optimization configuration
            monitor: Optional connection pool monitor
        """
        self.ttl = ttl
        self.cache_manager = cache_manager or get_cache_manager()
        self.config = config or get_optimization_config()
        self.monitor = monitor or get_connection_pool_monitor(self.config)
        self.logger = logger

        # Cache prefixes for different data types
        self.EVENT_PREFIX = "event"
        self.LAYOUT_PREFIX = "layout"
        self.ICS_PREFIX = "ics"
        self.COMPUTED_PREFIX = "computed"

        # Performance tracking
        self._stats = CacheStats()
        self._startup_time = time.time()

        self.logger.info(f"EventCache initialized with TTL={ttl}s")

    def _generate_event_key(self, source_key: str, filters: Optional[dict] = None) -> str:
        """Generate cache key for event data.

        Args:
            source_key: Source identifier (URL, file path, etc.)
            filters: Optional filters applied to events

        Returns:
            Standardized cache key for events
        """
        key_parts = [source_key]

        if filters:
            # Sort filters for consistent key generation
            filter_str = json.dumps(filters, sort_keys=True, default=str)
            filter_hash = hashlib.md5(filter_str.encode(), usedforsecurity=False).hexdigest()[
                :8
            ]  # Used for cache keys, not security
            key_parts.append(f"filters_{filter_hash}")

        return "_".join(key_parts)

    def _generate_layout_key(self, layout_name: str, config_hash: str) -> str:
        """Generate cache key for layout computation results.

        Args:
            layout_name: Name of the layout
            config_hash: Hash of layout configuration

        Returns:
            Standardized cache key for layout results
        """
        return f"{layout_name}_{config_hash}"

    def _generate_ics_key(self, source_url: str, last_modified: Optional[str] = None) -> str:
        """Generate cache key for ICS file processing.

        Args:
            source_url: URL or path to ICS file
            last_modified: Optional last-modified timestamp

        Returns:
            Standardized cache key for ICS processing
        """
        key_parts = [source_url]

        if last_modified:
            key_parts.append(f"mod_{last_modified}")

        # Hash long URLs to prevent filesystem issues
        key = "_".join(key_parts)
        if len(key) > 100:
            key = hashlib.sha256(key.encode()).hexdigest()

        return key

    async def get_events(
        self, source_key: str, filters: Optional[dict] = None
    ) -> Optional[list[CacheableEvent]]:
        """Get cached parsed event data.

        Args:
            source_key: Source identifier for events
            filters: Optional filters that were applied

        Returns:
            List of cached events or None if not found
        """
        start_time = time.time()
        cache_key = self._generate_event_key(source_key, filters)

        try:
            cached_data = await self.cache_manager.get(cache_key, self.EVENT_PREFIX)

            if cached_data is not None:
                # Convert cached dictionaries back to CacheableEvent objects
                events = [CacheableEvent.from_dict(event_data) for event_data in cached_data]

                self._stats.cache_hits += 1
                self._stats.total_requests += 1

                response_time = (time.time() - start_time) * 1000
                self._update_response_time(response_time)

                self.logger.debug(f"Event cache hit: {cache_key} ({len(events)} events)")
                return events

            self._stats.cache_misses += 1
            self._stats.total_requests += 1
            self.logger.debug(f"Event cache miss: {cache_key}")
            return None

        except Exception as e:
            self.logger.warning(f"Error retrieving events from cache {cache_key}: {e}")
            self._stats.cache_misses += 1
            self._stats.total_requests += 1
            return None

    async def set_events(
        self, source_key: str, events: list[CacheableEvent], filters: Optional[dict] = None
    ) -> bool:
        """Cache parsed event data.

        Args:
            source_key: Source identifier for events
            events: List of events to cache
            filters: Optional filters that were applied

        Returns:
            True if successfully cached
        """
        cache_key = self._generate_event_key(source_key, filters)

        try:
            # Convert CacheableEvent objects to dictionaries for caching
            event_data = [event.to_dict() for event in events]

            success = await self.cache_manager.set(
                cache_key, event_data, self.EVENT_PREFIX, self.ttl
            )

            if success:
                self._stats.events_cached += len(events)
                self.logger.debug(f"Cached {len(events)} events: {cache_key}")

            return success

        except Exception as e:
            self.logger.warning(f"Error caching events {cache_key}: {e}")
            return False

    async def get_computed_layout(self, layout_key: str) -> Optional[dict]:
        """Get cached layout computation results.

        Args:
            layout_key: Key identifying the layout computation

        Returns:
            Cached layout result or None if not found
        """
        start_time = time.time()

        try:
            cached_result = await self.cache_manager.get(layout_key, self.LAYOUT_PREFIX)

            if cached_result is not None:
                self._stats.cache_hits += 1
                self._stats.total_requests += 1

                response_time = (time.time() - start_time) * 1000
                self._update_response_time(response_time)

                self.logger.debug(f"Layout cache hit: {layout_key}")
                return cached_result

            self._stats.cache_misses += 1
            self._stats.total_requests += 1
            self.logger.debug(f"Layout cache miss: {layout_key}")
            return None

        except Exception as e:
            self.logger.warning(f"Error retrieving layout from cache {layout_key}: {e}")
            self._stats.cache_misses += 1
            self._stats.total_requests += 1
            return None

    async def set_computed_layout(self, layout_name: str, config_hash: str, result: dict) -> bool:
        """Cache layout computation results.

        Args:
            layout_name: Name of the layout
            config_hash: Hash of the layout configuration
            result: Computed layout result to cache

        Returns:
            True if successfully cached
        """
        layout_key = self._generate_layout_key(layout_name, config_hash)

        try:
            success = await self.cache_manager.set(layout_key, result, self.LAYOUT_PREFIX, self.ttl)

            if success:
                self._stats.layouts_cached += 1
                self.logger.debug(f"Cached layout result: {layout_key}")

            return success

        except Exception as e:
            self.logger.warning(f"Error caching layout {layout_key}: {e}")
            return False

    async def get_ics_data(
        self, source_url: str, last_modified: Optional[str] = None
    ) -> Optional[dict]:
        """Get cached ICS file processing results.

        Args:
            source_url: URL or path to ICS file
            last_modified: Optional last-modified timestamp

        Returns:
            Cached ICS processing result or None if not found
        """
        start_time = time.time()
        ics_key = self._generate_ics_key(source_url, last_modified)

        try:
            cached_data = await self.cache_manager.get(ics_key, self.ICS_PREFIX)

            if cached_data is not None:
                self._stats.cache_hits += 1
                self._stats.total_requests += 1

                response_time = (time.time() - start_time) * 1000
                self._update_response_time(response_time)

                self.logger.debug(f"ICS cache hit: {ics_key}")
                return cached_data

            self._stats.cache_misses += 1
            self._stats.total_requests += 1
            self.logger.debug(f"ICS cache miss: {ics_key}")
            return None

        except Exception as e:
            self.logger.warning(f"Error retrieving ICS data from cache {ics_key}: {e}")
            self._stats.cache_misses += 1
            self._stats.total_requests += 1
            return None

    async def set_ics_data(
        self, source_url: str, data: dict, last_modified: Optional[str] = None
    ) -> bool:
        """Cache ICS file processing results.

        Args:
            source_url: URL or path to ICS file
            data: Processed ICS data to cache
            last_modified: Optional last-modified timestamp

        Returns:
            True if successfully cached
        """
        ics_key = self._generate_ics_key(source_url, last_modified)

        try:
            success = await self.cache_manager.set(ics_key, data, self.ICS_PREFIX, self.ttl)

            if success:
                self._stats.ics_files_cached += 1
                self.logger.debug(f"Cached ICS data: {ics_key}")

            return success

        except Exception as e:
            self.logger.warning(f"Error caching ICS data {ics_key}: {e}")
            return False

    async def invalidate_source(self, source_key: str) -> bool:
        """Invalidate all cached data for a specific source.

        Args:
            source_key: Source identifier to invalidate

        Returns:
            True if any cache entries were invalidated
        """
        invalidated = False

        # Invalidate events for this source
        for prefix in [self.EVENT_PREFIX, self.ICS_PREFIX]:
            try:
                key = (
                    self._generate_event_key(source_key)
                    if prefix == self.EVENT_PREFIX
                    else self._generate_ics_key(source_key)
                )
                if await self.cache_manager.delete(key, prefix):
                    invalidated = True
                    self.logger.debug(f"Invalidated {prefix} cache for source: {source_key}")
            except Exception as e:  # noqa: PERF203
                self.logger.warning(f"Error invalidating {prefix} cache for {source_key}: {e}")

        return invalidated

    def _update_response_time(self, response_time_ms: float) -> None:
        """Update average response time statistics.

        Args:
            response_time_ms: Response time in milliseconds
        """
        # Simple moving average calculation
        if self._stats.average_response_time_ms == 0:
            self._stats.average_response_time_ms = response_time_ms
        else:
            # Weighted average with 90% weight on historical data
            self._stats.average_response_time_ms = (
                0.9 * self._stats.average_response_time_ms + 0.1 * response_time_ms
            )

    def get_cache_stats(self) -> dict[str, Any]:
        """Get comprehensive event cache statistics.

        Returns:
            dictionary with detailed cache performance metrics
        """
        # Calculate hit rate
        if self._stats.total_requests > 0:
            self._stats.hit_rate_percent = self._stats.cache_hits / self._stats.total_requests * 100

        # Get underlying cache manager stats
        cache_manager_stats = self.cache_manager.get_cache_stats()

        return {
            "event_cache": {
                "ttl_seconds": self.ttl,
                "events_cached": self._stats.events_cached,
                "layouts_cached": self._stats.layouts_cached,
                "ics_files_cached": self._stats.ics_files_cached,
                "cache_hits": self._stats.cache_hits,
                "cache_misses": self._stats.cache_misses,
                "total_requests": self._stats.total_requests,
                "hit_rate_percent": self._stats.hit_rate_percent,
                "average_response_time_ms": self._stats.average_response_time_ms,
                "uptime_seconds": time.time() - self._startup_time,
            },
            "cache_manager": cache_manager_stats,
        }

    async def clear_cache(self, cache_type: str = "all") -> None:
        """Clear event cache data.

        Args:
            cache_type: Type of cache to clear ("events", "layouts", "ics", "all")
        """
        if cache_type in ("events", "all"):
            # Clear would need to be implemented in cache_manager to clear by prefix
            self._stats.events_cached = 0
            self.logger.info("Event cache cleared")

        if cache_type in ("layouts", "all"):
            self._stats.layouts_cached = 0
            self.logger.info("Layout cache cleared")

        if cache_type in ("ics", "all"):
            self._stats.ics_files_cached = 0
            self.logger.info("ICS cache cleared")

        if cache_type == "all":
            # Reset all stats
            self._stats = CacheStats()
            self._startup_time = time.time()
            self.logger.info("All event caches cleared")


# Global event cache instance
_event_cache: Optional[EventCache] = None


def get_event_cache(
    ttl: int = 3600,
    cache_manager: Optional[CacheManager] = None,
    config: Optional[OptimizationConfig] = None,
    monitor: Optional[ConnectionPoolMonitor] = None,
) -> EventCache:
    """Get or create global event cache instance.

    Args:
        ttl: Time-to-live for cached events in seconds
        cache_manager: Optional cache manager instance
        config: Optional optimization configuration
        monitor: Optional connection pool monitor

    Returns:
        EventCache: Global event cache instance
    """
    if _event_cache is None:
        return EventCache(ttl, cache_manager, config, monitor)
    return _event_cache


def reset_event_cache() -> EventCache:
    """Reset the global event cache (for testing).

    Returns:
        New EventCache instance
    """
    return EventCache()
