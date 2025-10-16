"""Multi-level cache manager for optimized cache strategy implementation.

Implements L1 memory (TTLCache) and L2 disk caching with automatic cleanup.
Targets: +10MB cache overhead, -30MB from reduced recomputation (net -20MB savings)
Performance: -70% cached request response time, 70%+ cache hit rate
"""

import hashlib
import logging
import pickle
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

try:
    from cachetools import TTLCache  # type: ignore[import, attr-defined]
except ImportError:
    # Fallback implementation if cachetools not available
    import threading
    from collections import OrderedDict

    class TTLCache:  # type: ignore[no-redef]
        def __init__(self, maxsize: int, ttl: int):
            self.maxsize = maxsize
            self.ttl = ttl
            self._cache: OrderedDict[Any, Any] = OrderedDict()
            self._times: dict[Any, float] = {}
            self._lock = threading.RLock()

        def __contains__(self, key: Any) -> bool:
            with self._lock:
                if key not in self._cache:
                    return False
                if time.time() - self._times[key] > self.ttl:
                    del self._cache[key]
                    del self._times[key]
                    return False
                return True

        def __getitem__(self, key: Any) -> Any:
            with self._lock:
                if key not in self:
                    raise KeyError(key)
                value = self._cache[key]
                # Move to end (LRU)
                self._cache.move_to_end(key)
                return value

        def __setitem__(self, key: Any, value: Any) -> None:
            with self._lock:
                current_time = time.time()
                if key in self._cache:
                    self._cache[key] = value
                    self._times[key] = current_time
                    self._cache.move_to_end(key)
                else:
                    if len(self._cache) >= self.maxsize:
                        # Remove oldest
                        oldest_key = next(iter(self._cache))
                        del self._cache[oldest_key]
                        del self._times[oldest_key]
                    self._cache[key] = value
                    self._times[key] = current_time

        def get(self, key: Any, default: Any = None) -> Any:
            try:
                return self[key]
            except KeyError:
                return default

        def pop(self, key: Any, default: Any = None) -> Any:
            with self._lock:
                if key in self._cache:
                    value = self._cache.pop(key)
                    self._times.pop(key, None)
                    return value
                return default

        def clear(self) -> None:
            with self._lock:
                self._cache.clear()
                self._times.clear()


try:
    from diskcache import Cache as DiskCache  # type: ignore[import, import-untyped]
except ImportError:
    # Fallback disk cache implementation

    class DiskCache:  # type: ignore[no-redef]
        def __init__(self, directory: str, size_limit: int = 50 * 1024 * 1024):
            self.directory = Path(directory)
            self.size_limit = size_limit
            self.directory.mkdir(parents=True, exist_ok=True)

        def __contains__(self, key: Any) -> bool:
            return self._get_path(key).exists()

        def __getitem__(self, key: Any) -> Any:
            path = self._get_path(key)
            if not path.exists():
                raise KeyError(key)
            try:
                with path.open("rb") as f:
                    return pickle.load(f)  # nosec B301 - Used for cache data, not untrusted input
            except Exception:
                # Remove corrupted file
                path.unlink(missing_ok=True)
                raise KeyError(key) from None

        def __setitem__(self, key: Any, value: Any) -> None:
            self._cleanup_if_needed()
            path = self._get_path(key)
            try:
                with path.open("wb") as f:
                    pickle.dump(value, f)  # nosec B301 - Used for cache data, not untrusted input
            except Exception:
                path.unlink(missing_ok=True)
                raise

        def get(self, key: Any, default: Any = None) -> Any:
            try:
                return self[key]
            except KeyError:
                return default

        def pop(self, key: Any, default: Any = None) -> Any:
            try:
                value = self[key]
                self._get_path(key).unlink(missing_ok=True)
                return value
            except KeyError:
                return default

        def clear(self) -> None:
            for file_path in self.directory.glob("cache_*"):
                file_path.unlink(missing_ok=True)

        def _get_path(self, key: str) -> Path:
            safe_key = hashlib.md5(
                str(key).encode(), usedforsecurity=False
            ).hexdigest()  # Used for cache keys, not security
            return self.directory / f"cache_{safe_key}.pkl"

        def _cleanup_if_needed(self) -> None:
            total_size = sum(f.stat().st_size for f in self.directory.glob("cache_*"))
            if total_size > self.size_limit:
                # Remove oldest files
                files = [(f.stat().st_mtime, f) for f in self.directory.glob("cache_*")]
                files.sort()
                for _, file_path in files[: len(files) // 4]:  # Remove 25% oldest
                    file_path.unlink(missing_ok=True)


from ..config.optimization import OptimizationConfig, get_optimization_config
from ..monitoring.connection_pool_monitor import (
    ConnectionPoolMonitor,
    get_connection_pool_monitor,
)

logger = logging.getLogger(__name__)


class CacheError(Exception):
    """Base exception for cache operations."""


class CacheManager:
    """Multi-level caching manager with L1 memory and L2 disk caching.

    Implements hierarchical caching strategy:
    - L1: TTLCache for fast memory access (5-minute TTL, 500 items)
    - L2: DiskCache for persistent storage (50MB limit with cleanup)

    Performance targets:
    - Memory: +10MB cache overhead, -30MB from reduced recomputation
    - Response time: -70% for cached requests
    - Cache hit rate: 70%+ for event data and computation results
    """

    def __init__(
        self,
        config: Optional[OptimizationConfig] = None,
        monitor: Optional[ConnectionPoolMonitor] = None,
        cache_dir: Optional[Path] = None,
    ):
        """Initialize multi-level cache manager.

        Args:
            config: Optional optimization configuration
            monitor: Optional connection pool performance monitor
            cache_dir: Optional custom cache directory (defaults to /tmp/calendarbot_cache)
        """
        self.config = config or get_optimization_config()
        self.monitor = monitor or get_connection_pool_monitor(self.config)
        self.logger = logger

        # Detect small-device optimization flag from global application settings if available.
        # This allows a reversible, config-gated change without altering behavior for defaults.
        small_device = False
        try:
            # Import here to avoid circular imports at module import time
            from ..config.settings import settings as app_settings  # noqa: PLC0415

            small_device = bool(
                getattr(getattr(app_settings, "optimization", None), "small_device", False)
            )
        except Exception:
            # If settings are not available or import fails, default to non-small-device behavior
            small_device = False

        # Determine conservative defaults for constrained devices
        if small_device:
            self._l1_maxsize = 50
            self._l1_ttl = 120  # seconds
            self._l2_size_limit = 15 * 1024 * 1024  # 15MB
        else:
            # Use configured defaults
            self._l1_maxsize = self.config.cache_maxsize
            self._l1_ttl = self.config.cache_ttl
            self._l2_size_limit = 50 * 1024 * 1024  # 50MB

        # L1 Memory Cache - TTLCache with config-driven parameters
        self.memory_cache = TTLCache(
            maxsize=self._l1_maxsize,
            ttl=self._l1_ttl,
        )

        # L2 Disk Cache - Persistent storage with size limit
        if cache_dir is None:
            cache_dir = Path(tempfile.gettempdir()) / "calendarbot_cache"

        self.cache_dir = cache_dir
        self.disk_cache = DiskCache(
            directory=str(cache_dir),
            size_limit=self._l2_size_limit,
        )

        # Performance tracking
        self._stats = {
            "l1_hits": 0,
            "l1_misses": 0,
            "l2_hits": 0,
            "l2_misses": 0,
            "sets": 0,
            "evictions": 0,
            "startup_time": time.time(),
        }

        # Report actual active cache parameters (reflects small_device overrides when enabled)
        self.logger.info(
            f"CacheManager initialized: L1={self._l1_maxsize} items, "
            f"TTL={self._l1_ttl}s, L2={cache_dir}"
        )

    def _generate_cache_key(self, key: str, prefix: str = "") -> str:
        """Generate standardized cache key with optional prefix.

        Args:
            key: Base key string
            prefix: Optional prefix for categorization

        Returns:
            Standardized cache key
        """
        if prefix:
            key = f"{prefix}:{key}"

        # Normalize key for consistent hashing
        normalized = str(key).lower().strip()

        # Hash long keys to prevent filesystem issues
        if len(normalized) > 100:
            normalized = hashlib.sha256(normalized.encode()).hexdigest()

        return normalized

    async def get(self, key: str, prefix: str = "") -> Optional[Any]:
        """Get value from multi-level cache hierarchy (L1 -> L2).

        Args:
            key: Cache key
            prefix: Optional key prefix for categorization

        Returns:
            Cached value or None if not found
        """
        cache_key = self._generate_cache_key(key, prefix)
        start_time = time.time()

        # Lower-volume logging for frequent operations on small devices; use DEBUG for details
        self.logger.debug(f"[CACHE_DEBUG] Starting get operation for key: {cache_key}")

        # Try L1 memory cache first
        try:
            l1_start = time.time()
            self.logger.debug(f"[CACHE_DEBUG] Accessing L1 cache for: {cache_key}")
            value = self.memory_cache.get(cache_key)
            l1_duration = time.time() - l1_start

            if value is not None:
                self._stats["l1_hits"] += 1
                self.logger.debug(
                    f"[CACHE_DEBUG] L1 cache hit: {cache_key} (duration: {l1_duration:.4f}s)"
                )
                return value
            self._stats["l1_misses"] += 1
            self.logger.debug(
                f"[CACHE_DEBUG] L1 cache miss: {cache_key} (duration: {l1_duration:.4f}s)"
            )
        except Exception as e:
            # Keep errors visible
            self.logger.error(f"[CACHE_DEBUG] L1 cache error for {cache_key}: {e}", exc_info=True)
            self._stats["l1_misses"] += 1

        # Try L2 disk cache (disk I/O may block; run in thread to avoid blocking the event loop)
        try:
            l2_start = time.time()
            self.logger.debug(f"[CACHE_DEBUG] Accessing L2 cache for: {cache_key}")
            import asyncio  # local import to avoid top-level import cycles  # noqa: PLC0415

            value = await asyncio.to_thread(self.disk_cache.get, cache_key)
            l2_duration = time.time() - l2_start

            if value is not None:
                self._stats["l2_hits"] += 1
                self.logger.debug(
                    f"[CACHE_DEBUG] L2 cache hit: {cache_key} (duration: {l2_duration:.4f}s)"
                )

                # Promote to L1 cache (fast, in-process)
                try:
                    promote_start = time.time()
                    self.logger.debug(f"[CACHE_DEBUG] Promoting to L1: {cache_key}")
                    self.memory_cache[cache_key] = value
                    promote_duration = time.time() - promote_start
                    self.logger.debug(
                        f"[CACHE_DEBUG] L1 promotion complete: {cache_key} (duration: {promote_duration:.4f}s)"
                    )
                except Exception as e:
                    self.logger.error(f"[CACHE_DEBUG] Failed to promote to L1: {e}", exc_info=True)

                total_duration = time.time() - start_time
                self.logger.debug(
                    f"[CACHE_DEBUG] Get operation complete: {cache_key} (total: {total_duration:.4f}s)"
                )
                return value
            self._stats["l2_misses"] += 1
            self.logger.debug(
                f"[CACHE_DEBUG] L2 cache miss: {cache_key} (duration: {l2_duration:.4f}s)"
            )
        except Exception as e:
            # Keep errors visible
            self.logger.error(f"[CACHE_DEBUG] L2 cache error for {cache_key}: {e}", exc_info=True)
            self._stats["l2_misses"] += 1

        total_duration = time.time() - start_time
        self.logger.debug(
            f"[CACHE_DEBUG] Cache miss complete: {cache_key} (total: {total_duration:.4f}s)"
        )
        return None

    async def set(self, key: str, value: Any, prefix: str = "", ttl: Optional[int] = None) -> bool:
        """Set value in both L1 and L2 caches.

        Args:
            key: Cache key
            value: Value to cache
            prefix: Optional key prefix for categorization
            ttl: Optional TTL override (not used in current implementation)

        Returns:
            True if successfully cached
        """
        # TTL parameter reserved for future use
        _ = ttl

        cache_key = self._generate_cache_key(key, prefix)
        success = False

        # Store in L1 memory cache
        try:
            self.memory_cache[cache_key] = value
            success = True
            self.logger.debug(f"Stored in L1 cache: {cache_key}")
        except Exception as e:
            self.logger.warning(f"Failed to store in L1 cache {cache_key}: {e}")

        # Store in L2 disk cache (disk I/O may block; run in thread)
        try:
            import asyncio  # noqa: PLC0415

            await asyncio.to_thread(self.disk_cache.__setitem__, cache_key, value)
            success = True
            self.logger.debug(f"Stored in L2 cache: {cache_key}")
        except Exception as e:
            self.logger.warning(f"Failed to store in L2 cache {cache_key}: {e}")

        if success:
            self._stats["sets"] += 1

        return success

    async def delete(self, key: str, prefix: str = "") -> bool:
        """Delete value from both cache levels.

        Args:
            key: Cache key to delete
            prefix: Optional key prefix for categorization

        Returns:
            True if key was found and deleted
        """
        cache_key = self._generate_cache_key(key, prefix)
        deleted = False

        # Remove from L1
        try:
            value = self.memory_cache.pop(cache_key, None)
            if value is not None:
                deleted = True
                self.logger.debug(f"Deleted from L1 cache: {cache_key}")
        except Exception as e:
            self.logger.warning(f"Error deleting from L1 cache {cache_key}: {e}")

        # Remove from L2
        try:
            value = self.disk_cache.pop(cache_key, None)
            if value is not None:
                deleted = True
                self.logger.debug(f"Deleted from L2 cache: {cache_key}")
        except Exception as e:
            self.logger.warning(f"Error deleting from L2 cache {cache_key}: {e}")

        return deleted

    def get_cache_stats(self) -> dict[str, Any]:
        """Get comprehensive cache performance statistics.

        Returns:
            Dictionary with cache performance metrics
        """
        total_requests = (
            self._stats["l1_hits"]
            + self._stats["l1_misses"]
            + self._stats["l2_hits"]
            + self._stats["l2_misses"]
        )

        l1_hit_rate = (self._stats["l1_hits"] / total_requests * 100) if total_requests > 0 else 0

        overall_hit_rate = (
            ((self._stats["l1_hits"] + self._stats["l2_hits"]) / total_requests * 100)
            if total_requests > 0
            else 0
        )

        return {
            "l1_memory_cache": {
                "hits": self._stats["l1_hits"],
                "misses": self._stats["l1_misses"],
                "hit_rate_percent": l1_hit_rate,
                "maxsize": self._l1_maxsize,
                "ttl_seconds": self._l1_ttl,
            },
            "l2_disk_cache": {
                "hits": self._stats["l2_hits"],
                "misses": self._stats["l2_misses"],
                "cache_dir": str(self.cache_dir),
                "size_limit_bytes": self._l2_size_limit,
            },
            "overall": {
                "total_requests": total_requests,
                "hit_rate_percent": overall_hit_rate,
                "sets": self._stats["sets"],
                "evictions": self._stats["evictions"],
                "uptime_seconds": time.time() - self._stats["startup_time"],
            },
        }

    async def clear_cache(self, level: str = "both") -> None:
        """Clear cache at specified level(s).

        Args:
            level: Cache level to clear ("l1", "l2", or "both")
        """
        if level in ("l1", "both"):
            try:
                self.memory_cache.clear()
                self.logger.info("L1 memory cache cleared")
            except Exception:
                self.logger.exception("Error clearing L1 cache")

        if level in ("l2", "both"):
            try:
                self.disk_cache.clear()
                self.logger.info("L2 disk cache cleared")
            except Exception:
                self.logger.exception("Error clearing L2 cache")

        # Reset stats if clearing both
        if level == "both":
            self._stats.update(
                {
                    "l1_hits": 0,
                    "l1_misses": 0,
                    "l2_hits": 0,
                    "l2_misses": 0,
                    "sets": 0,
                    "evictions": 0,
                    "startup_time": time.time(),
                }
            )

    async def cleanup(self) -> None:
        """Perform cache cleanup and maintenance."""
        try:
            # Disk cache cleanup is handled automatically by DiskCache
            self.logger.debug("Cache cleanup completed")
        except Exception:
            self.logger.exception("Error during cache cleanup")


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(
    config: Optional[OptimizationConfig] = None,
    monitor: Optional[ConnectionPoolMonitor] = None,
    cache_dir: Optional[Path] = None,
) -> CacheManager:
    """Get or create global cache manager instance.

    Args:
        config: Optional optimization configuration
        monitor: Optional connection pool monitor
        cache_dir: Optional custom cache directory

    Returns:
        CacheManager: Global cache manager instance
    """
    global _cache_manager  # noqa: PLW0603
    if _cache_manager is None:
        _cache_manager = CacheManager(config, monitor, cache_dir)
    return _cache_manager


def reset_cache_manager() -> None:
    """Reset the global cache manager (for testing)."""
    global _cache_manager  # noqa: PLW0603
    _cache_manager = None
