"""Static Asset Cache for eliminating filesystem lookups during request serving.

Phase 1A of CalendarBot Performance Optimization Project.
Targets 80% response time improvement (-8ms per static request) with net -13MB memory savings.
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class AssetMetadata:
    """Metadata for cached static assets.

    Memory-efficient storage of asset information to eliminate filesystem lookups.
    """

    absolute_path: Path
    size: int
    mtime: float
    is_layout_specific: bool = False
    layout_name: Optional[str] = None


class StaticAssetCache:
    """High-performance static asset path cache eliminating triple filesystem lookups.

    Replaces runtime filesystem traversal with O(1) dictionary access.
    Built at startup with one-time scan cost, eliminating per-request overhead.

    Performance targets:
    - Memory: +2MB cache, -15MB from eliminated lookups (net -13MB)
    - Response time: -8ms per static request (80% improvement)
    """

    def __init__(self, static_dirs: list[Path], layouts_dir: Path):
        """Initialize cache with static asset directories.

        Args:
            static_dirs: List of static asset directories to scan
            layouts_dir: Directory containing layout-specific assets
        """
        self._asset_map: dict[str, AssetMetadata] = {}
        self._layout_assets: dict[str, set[str]] = {}
        self._static_dirs = static_dirs
        self._layouts_dir = layouts_dir
        self._cache_hits = 0
        self._cache_misses = 0
        self._build_time = 0.0

        logger.info("Initializing StaticAssetCache for %d directories", len(static_dirs))

    def build_cache(self) -> None:
        """Build complete asset map at startup.

        One-time filesystem scan to eliminate runtime lookups.
        Scans all static directories and layout-specific assets.
        """
        start_time = time.time()
        asset_count = 0

        try:
            # Scan standard static directories
            for static_dir in self._static_dirs:
                if static_dir.exists():
                    asset_count += self._scan_directory(static_dir, is_layout_specific=False)

            # Scan layout-specific directories
            if self._layouts_dir.exists():
                for layout_dir in self._layouts_dir.iterdir():
                    if layout_dir.is_dir():
                        layout_name = layout_dir.name
                        layout_assets: set[str] = set()

                        # Scan layout directory directly for assets
                        count = self._scan_directory(
                            layout_dir, is_layout_specific=True, layout_name=layout_name
                        )
                        asset_count += count

                        # Also scan layout's static subdirectory if it exists
                        static_path = layout_dir / "static"
                        if static_path.exists():
                            count = self._scan_directory(
                                static_path, is_layout_specific=True, layout_name=layout_name
                            )
                            asset_count += count

                        # Collect all layout assets
                        layout_assets.update(
                            path
                            for path, meta in self._asset_map.items()
                            if meta.layout_name == layout_name
                        )

                        if layout_assets:
                            self._layout_assets[layout_name] = layout_assets

            self._build_time = time.time() - start_time
            logger.info(
                "StaticAssetCache built: %d assets cached in %.2fms",
                asset_count,
                self._build_time * 1000,
            )

        except Exception:
            logger.exception("Failed to build static asset cache")
            # Clear partial cache on error to prevent inconsistent state
            self._asset_map.clear()
            self._layout_assets.clear()
            raise

    def _scan_directory(
        self, directory: Path, is_layout_specific: bool = False, layout_name: Optional[str] = None
    ) -> int:
        """Scan directory for static assets and cache metadata.

        Args:
            directory: Directory to scan recursively
            is_layout_specific: Whether assets belong to specific layout
            layout_name: Name of layout if layout-specific

        Returns:
            Number of assets cached from this directory
        """
        asset_count = 0

        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file() and self._is_static_asset(file_path):
                    # Calculate relative path for cache key
                    try:
                        relative_path = file_path.relative_to(directory)
                        cache_key = str(relative_path).replace(
                            "\\", "/"
                        )  # Normalize path separators

                        # Get file metadata
                        stat_info = file_path.stat()
                        metadata = AssetMetadata(
                            absolute_path=file_path,
                            size=stat_info.st_size,
                            mtime=stat_info.st_mtime,
                            is_layout_specific=is_layout_specific,
                            layout_name=layout_name,
                        )

                        # Store in cache with potential layout prefix
                        if is_layout_specific and layout_name:
                            # Layout-specific assets get prefixed keys for disambiguation
                            prefixed_key = f"{layout_name}/{cache_key}"
                            self._asset_map[prefixed_key] = metadata

                        # Always store direct key for fallback lookup
                        self._asset_map[cache_key] = metadata
                        asset_count += 1

                    except ValueError:
                        # Skip if relative_to fails (shouldn't happen with rglob)
                        logger.warning("Could not determine relative path for %s", file_path)
                        continue

        except OSError as e:
            logger.warning("Error scanning directory %s: %s", directory, e)

        return asset_count

    def _is_static_asset(self, file_path: Path) -> bool:
        """Check if file is a static asset worth caching.

        Args:
            file_path: Path to check

        Returns:
            True if file should be cached as static asset
        """
        # Cache common web assets and exclude system files
        static_extensions = {
            ".css",
            ".js",
            ".html",
            ".htm",
            ".json",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".ico",
            ".webp",
            ".woff",
            ".woff2",
            ".ttf",
            ".eot",
            ".txt",
            ".xml",
            ".pdf",
        }

        # Skip hidden files and system files
        if file_path.name.startswith("."):
            return False

        # Skip common non-asset files
        if file_path.name.lower() in {"thumbs.db", "desktop.ini", ".ds_store"}:
            return False

        return file_path.suffix.lower() in static_extensions

    def resolve_asset_path(
        self, requested_path: str, layout_name: Optional[str] = None
    ) -> Optional[Path]:
        """Resolve static asset path with O(1) cache lookup.

        Replaces triple filesystem lookup pattern with dictionary access.

        Args:
            requested_path: Requested asset path (e.g., "css/styles.css")
            layout_name: Layout context for layout-specific assets

        Returns:
            Absolute path to asset file, or None if not found
        """
        # Normalize path separators
        requested_path = requested_path.replace("\\", "/").lstrip("/")

        # Try layout-specific lookup first if layout provided
        if layout_name:
            layout_key = f"{layout_name}/{requested_path}"
            if layout_key in self._asset_map:
                self._cache_hits += 1
                return self._asset_map[layout_key].absolute_path

        # Try direct lookup
        if requested_path in self._asset_map:
            self._cache_hits += 1
            return self._asset_map[requested_path].absolute_path

        # Cache miss - asset not found
        self._cache_misses += 1
        logger.debug("Cache miss for asset: %s (layout: %s)", requested_path, layout_name)
        return None

    def get_asset_metadata(
        self, requested_path: str, layout_name: Optional[str] = None
    ) -> Optional[AssetMetadata]:
        """Get cached metadata for asset without filesystem access.

        Args:
            requested_path: Requested asset path
            layout_name: Layout context for layout-specific assets

        Returns:
            Asset metadata or None if not found
        """
        requested_path = requested_path.replace("\\", "/").lstrip("/")

        # Try layout-specific lookup first
        if layout_name:
            layout_key = f"{layout_name}/{requested_path}"
            if layout_key in self._asset_map:
                return self._asset_map[layout_key]

        # Try direct lookup
        return self._asset_map.get(requested_path)

    def is_cache_built(self) -> bool:
        """Check if cache has been built and is ready for use.

        Returns:
            True if cache is built and ready
        """
        return bool(self._asset_map)

    def get_cache_stats(self) -> dict[str, Union[int, float]]:
        """Get cache performance statistics.

        Returns:
            Dictionary with cache performance metrics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "total_assets": len(self._asset_map),
            "layout_count": len(self._layout_assets),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": hit_rate,
            "build_time_ms": self._build_time * 1000,
        }

    def invalidate_asset(self, requested_path: str) -> bool:
        """Invalidate cached asset (for dynamic updates).

        Args:
            requested_path: Asset path to invalidate

        Returns:
            True if asset was found and invalidated
        """
        requested_path = requested_path.replace("\\", "/").lstrip("/")

        # Remove from main cache
        removed = requested_path in self._asset_map
        self._asset_map.pop(requested_path, None)

        # Remove from layout-specific caches
        for layout_name, layout_assets in self._layout_assets.items():
            layout_key = f"{layout_name}/{requested_path}"
            self._asset_map.pop(layout_key, None)
            layout_assets.discard(requested_path)

        if removed:
            logger.debug("Invalidated cached asset: %s", requested_path)

        return removed

    def clear_cache(self) -> None:
        """Clear all cached assets (for testing or reset)."""
        asset_count = len(self._asset_map)
        self._asset_map.clear()
        self._layout_assets.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self._build_time = 0.0

        logger.info("StaticAssetCache cleared: %d assets removed", asset_count)
