"""
Layout Asset Bundler for CalendarBot Layout Optimization.

Provides smart asset grouping and bundling for layout system optimization,
targeting Pi Zero 2W deployment with 512MB RAM constraints.

Performance targets:
- Transfer Size: -40% for layout assets through bundling
- Load Time: -60% for layout switching via optimized assets
- Memory: Efficient asset caching and reuse
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from calendarbot.optimization.static_asset_cache import StaticAssetCache

logger = logging.getLogger(__name__)


@dataclass
class AssetBundle:
    """Represents a bundled group of assets for optimized delivery."""

    name: str
    bundle_type: str  # 'css' or 'js'
    assets: list[Path]
    bundle_path: Optional[Path] = None
    content_hash: Optional[str] = None
    size_bytes: int = 0
    original_size_bytes: int = 0
    compression_ratio: float = 0.0
    created_at: float = field(default_factory=time.time)


@dataclass
class BundleMetrics:
    """Performance metrics for asset bundling operations."""

    total_bundles: int = 0
    total_assets: int = 0
    total_size_reduction: int = 0
    bundle_creation_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    last_bundle_time: float = 0.0


class LayoutAssetBundler:
    """
    Smart asset bundler for layout optimization.

    Creates optimized asset bundles grouped by layout type and usage patterns
    to minimize transfer sizes and improve loading performance.
    """

    def __init__(
        self,
        layouts_root: Path,
        bundle_cache_dir: Optional[Path] = None,
        static_cache: Optional[StaticAssetCache] = None,
    ):
        """
        Initialize layout asset bundler.

        Args:
            layouts_root: Root directory containing layout definitions
            bundle_cache_dir: Directory for storing bundled assets
            static_cache: StaticAssetCache instance for integration
        """
        self.layouts_root = Path(layouts_root)
        self.bundle_cache_dir = bundle_cache_dir or (layouts_root / ".bundle_cache")
        self.static_cache = static_cache

        # Ensure bundle cache directory exists
        self.bundle_cache_dir.mkdir(parents=True, exist_ok=True)

        # Bundle tracking
        self._bundles: dict[str, AssetBundle] = {}
        self._bundle_index: dict[str, str] = {}  # asset_path -> bundle_name
        self._layout_bundles: dict[str, list[str]] = {}  # layout_name -> bundle_names

        # Performance metrics
        self.metrics = BundleMetrics()

        # Bundle configurations
        self._bundle_configs = {
            "whats-next-view": {
                "css_patterns": ["whats-next*.css", "calendar-*.css"],
                "js_patterns": ["whats-next*.js", "calendar-*.js"],
                "priority": "high",
            },
            "layout-4x8": {
                "css_patterns": ["4x8*.css", "grid-*.css"],
                "js_patterns": ["4x8*.js", "grid-*.js"],
                "priority": "high",
            },
            "shared": {
                "css_patterns": ["shared/*.css", "common/*.css"],
                "js_patterns": ["shared/*.js", "common/*.js"],
                "priority": "critical",
            },
        }

        logger.info("Initialized LayoutAssetBundler with cache at %s", self.bundle_cache_dir)

    def discover_layout_assets(self, layout_name: str) -> tuple[list[Path], list[Path]]:
        """
        Discover CSS and JS assets for a specific layout.

        Args:
            layout_name: Name of the layout to discover assets for

        Returns:
            Tuple of (css_files, js_files)
        """
        layout_dir = self.layouts_root / layout_name

        if not layout_dir.exists():
            logger.warning("Layout directory not found: %s", layout_dir)
            return [], []

        # Find CSS files
        css_files = []
        css_patterns = ["*.css", "css/*.css", "static/*.css"]
        for pattern in css_patterns:
            css_files.extend(layout_dir.glob(pattern))

        # Find JS files
        js_files = []
        js_patterns = ["*.js", "js/*.js", "static/*.js"]
        for pattern in js_patterns:
            js_files.extend(layout_dir.glob(pattern))

        # Filter out minified files to avoid double-processing
        css_files = [f for f in css_files if not f.name.endswith(".min.css")]
        js_files = [f for f in js_files if not f.name.endswith(".min.js")]

        logger.debug(
            "Discovered %d CSS and %d JS assets for layout '%s'",
            len(css_files),
            len(js_files),
            layout_name,
        )

        return css_files, js_files

    def create_bundle(
        self, bundle_name: str, assets: list[Path], bundle_type: str
    ) -> Optional[AssetBundle]:
        """
        Create an optimized asset bundle from multiple files.

        Args:
            bundle_name: Name for the bundle
            assets: List of asset file paths to bundle
            bundle_type: Type of bundle ('css' or 'js')

        Returns:
            AssetBundle instance or None if creation failed
        """
        if not assets:
            logger.debug("No assets provided for bundle '%s'", bundle_name)
            return None

        start_time = time.time()

        try:
            # Calculate content hash for cache validation
            content_hash = self._calculate_assets_hash(assets)

            # Check if bundle already exists and is current
            bundle_filename = f"{bundle_name}.{bundle_type}"
            bundle_path = self.bundle_cache_dir / bundle_filename

            if self._is_bundle_current(bundle_path, content_hash):
                self.metrics.cache_hits += 1
                return self._load_existing_bundle(bundle_name, bundle_path, content_hash)

            # Create new bundle
            bundled_content = self._combine_assets(assets)
            original_size = sum(asset.stat().st_size for asset in assets if asset.exists())

            # Write bundle to cache
            with bundle_path.open("w", encoding="utf-8") as f:
                f.write(bundled_content)

            bundle_size = bundle_path.stat().st_size
            compression_ratio = (
                (original_size - bundle_size) / original_size if original_size > 0 else 0.0
            )

            bundle = AssetBundle(
                name=bundle_name,
                bundle_type=bundle_type,
                assets=assets,
                bundle_path=bundle_path,
                content_hash=content_hash,
                size_bytes=bundle_size,
                original_size_bytes=original_size,
                compression_ratio=compression_ratio,
            )

            # Store bundle and update tracking
            self._bundles[bundle_name] = bundle
            for asset in assets:
                self._bundle_index[str(asset)] = bundle_name

            # Update metrics
            self.metrics.cache_misses += 1
            self.metrics.total_bundles += 1
            self.metrics.total_assets += len(assets)
            self.metrics.total_size_reduction += original_size - bundle_size

            bundle_time = time.time() - start_time
            self.metrics.bundle_creation_time += bundle_time
            self.metrics.last_bundle_time = bundle_time

            logger.info(
                "Created bundle '%s': %d assets, %.1f%% compression, %.2fms",
                bundle_name,
                len(assets),
                compression_ratio * 100,
                bundle_time * 1000,
            )

            return bundle

        except Exception:
            logger.exception("Failed to create bundle '%s'", bundle_name)
            return None

    def create_layout_bundles(self, layout_name: str) -> dict[str, AssetBundle]:
        """
        Create all bundles for a specific layout.

        Args:
            layout_name: Name of the layout to create bundles for

        Returns:
            Dictionary mapping bundle names to AssetBundle instances
        """
        css_files, js_files = self.discover_layout_assets(layout_name)
        bundles = {}

        # Create CSS bundle if assets exist
        if css_files:
            css_bundle_name = f"{layout_name}-styles"
            css_bundle = self.create_bundle(css_bundle_name, css_files, "css")
            if css_bundle:
                bundles[css_bundle_name] = css_bundle

        # Create JS bundle if assets exist
        if js_files:
            js_bundle_name = f"{layout_name}-scripts"
            js_bundle = self.create_bundle(js_bundle_name, js_files, "js")
            if js_bundle:
                bundles[js_bundle_name] = js_bundle

        # Update layout bundle tracking
        self._layout_bundles[layout_name] = list(bundles.keys())

        logger.info("Created %d bundles for layout '%s'", len(bundles), layout_name)
        return bundles

    def get_bundle_url(self, bundle_name: str) -> Optional[str]:
        """
        Get the URL for accessing a bundle.

        Args:
            bundle_name: Name of the bundle

        Returns:
            URL string or None if bundle not found
        """
        bundle = self._bundles.get(bundle_name)
        if not bundle or not bundle.bundle_path:
            return None

        # Integration with StaticAssetCache if available
        if self.static_cache:
            try:
                relative_path = bundle.bundle_path.relative_to(self.layouts_root)
                resolved_path = self.static_cache.resolve_asset_path(str(relative_path))
                if resolved_path:
                    # Convert absolute path back to web-accessible URL
                    return f"/bundles/{bundle.bundle_path.name}"
            except ValueError:
                # Bundle path not relative to layouts_root, use direct path
                pass

        # Fallback to relative path from bundle cache
        return f"/bundles/{bundle.bundle_path.name}"

    def get_layout_bundle_urls(self, layout_name: str) -> dict[str, str]:
        """
        Get URLs for all bundles associated with a layout.

        Args:
            layout_name: Name of the layout

        Returns:
            Dictionary mapping bundle names to URLs
        """
        bundle_names = self._layout_bundles.get(layout_name, [])
        urls = {}

        for bundle_name in bundle_names:
            url = self.get_bundle_url(bundle_name)
            if url:
                urls[bundle_name] = url

        return urls

    def invalidate_layout_bundles(self, layout_name: str) -> None:
        """
        Invalidate and remove bundles for a specific layout.

        Args:
            layout_name: Name of the layout to invalidate bundles for
        """
        bundle_names = self._layout_bundles.get(layout_name, [])

        for bundle_name in bundle_names:
            bundle = self._bundles.get(bundle_name)
            if bundle and bundle.bundle_path and bundle.bundle_path.exists():
                try:
                    bundle.bundle_path.unlink()
                    logger.debug("Removed bundle file: %s", bundle.bundle_path)
                except OSError as e:
                    logger.warning("Failed to remove bundle file %s: %s", bundle.bundle_path, e)

            # Remove from tracking
            if bundle_name in self._bundles:
                bundle = self._bundles[bundle_name]
                for asset in bundle.assets:
                    self._bundle_index.pop(str(asset), None)
                del self._bundles[bundle_name]

        # Clear layout bundle tracking
        self._layout_bundles.pop(layout_name, None)

        logger.info("Invalidated %d bundles for layout '%s'", len(bundle_names), layout_name)

    def get_performance_metrics(self) -> BundleMetrics:
        """
        Get current bundling performance metrics.

        Returns:
            BundleMetrics instance with current statistics
        """
        return self.metrics

    def _calculate_assets_hash(self, assets: list[Path]) -> str:
        """Calculate MD5 hash of asset file contents and modification times."""
        hasher = hashlib.md5(usedforsecurity=False)  # Used for cache keys, not security

        for asset in sorted(assets):  # Sort for consistent hashing
            if asset.exists():
                # Include file path and modification time
                hasher.update(str(asset).encode("utf-8"))
                hasher.update(str(asset.stat().st_mtime).encode("utf-8"))

                # Include file content
                try:
                    with asset.open("rb") as f:
                        hasher.update(f.read())
                except OSError as e:
                    logger.warning("Failed to read asset %s for hashing: %s", asset, e)

        return hasher.hexdigest()

    def _is_bundle_current(self, bundle_path: Path, content_hash: str) -> bool:
        """Check if existing bundle is current based on content hash."""
        if not bundle_path.exists():
            return False

        # Check for hash file
        hash_file = bundle_path.with_suffix(bundle_path.suffix + ".hash")
        if not hash_file.exists():
            return False

        try:
            with hash_file.open("r") as f:
                stored_hash = f.read().strip()
            return stored_hash == content_hash
        except OSError:
            return False

    def _load_existing_bundle(
        self, bundle_name: str, bundle_path: Path, content_hash: str
    ) -> AssetBundle:
        """Load existing bundle metadata."""
        size_bytes = bundle_path.stat().st_size

        return AssetBundle(
            name=bundle_name,
            bundle_type=bundle_path.suffix[1:],  # Remove leading dot
            assets=[],  # Assets not needed for existing bundle
            bundle_path=bundle_path,
            content_hash=content_hash,
            size_bytes=size_bytes,
            original_size_bytes=size_bytes,  # Unknown for existing bundles
            compression_ratio=0.0,
        )

    def _combine_assets(self, assets: list[Path]) -> str:
        """Combine multiple asset files into a single bundled string."""
        combined_content = []

        for asset in assets:
            if not asset.exists():
                logger.warning("Asset file not found: %s", asset)
                continue

            try:
                with asset.open("r", encoding="utf-8") as f:
                    content = f.read()

                # Add source comment for debugging
                combined_content.append(f"/* Source: {asset.name} */")
                combined_content.append(content)
                combined_content.append("")  # Add spacing between files

            except OSError as e:
                logger.warning("Failed to read asset %s: %s", asset, e)

        return "\n".join(combined_content)
