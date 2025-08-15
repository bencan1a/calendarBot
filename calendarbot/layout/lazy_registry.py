"""Lazy loading layout registry for dynamic layout optimization.

Replaces eager layout loading with on-demand pattern to achieve:
- Memory: -20MB from unused layout elimination
- Startup Time: -2-3 seconds through lazy loading
- Layout Switching: -60% load time through optimized caching
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn, Optional

from ..optimization.cache_keys import CacheKeyGenerator

# Required cache manager integration for cache strategy
from ..optimization.cache_manager import CacheManager, get_cache_manager
from .exceptions import LayoutValidationError
from .registry import LayoutInfo  # Reuse existing LayoutInfo

logger = logging.getLogger(__name__)


def _raise_missing_field_error(field: str) -> NoReturn:
    """Raise LayoutValidationError for missing required field."""
    raise LayoutValidationError(f"Missing required field: {field}")


@dataclass
class LayoutMetadata:
    """Lightweight metadata for layout discovery without full loading."""

    name: str
    config_path: Path
    last_modified: float
    is_loaded: bool = False


class LazyLayoutRegistry:
    """Lazy loading layout registry - loads layouts on demand for layout optimization.

    Performance targets:
    - Memory: -20MB from unused layout elimination
    - Startup time: -2-3 seconds through lazy loading
    - Layout switching: -60% load time through on-demand loading
    """

    def __init__(
        self,
        layouts_dir: Optional[Path] = None,
        layouts_directory: Optional[Path] = None,
        cache_manager: Optional["CacheManager"] = None,
    ) -> None:
        """Initialize lazy layout registry with metadata-only discovery.

        Args:
            layouts_dir: Directory containing layout configurations
            layouts_directory: Alias for layouts_dir for backward compatibility
            cache_manager: Optional cache manager for layout computation caching
        """
        # Support both parameter names for backward compatibility
        if layouts_directory is not None:
            layouts_dir = layouts_directory
        if layouts_dir is None:
            # Default to layouts directory in web/static/layouts
            calendarbot_module = Path(__file__).parent.parent
            layouts_dir = calendarbot_module / "web" / "static" / "layouts"

        self.layouts_dir = layouts_dir
        self._metadata_cache: dict[str, LayoutMetadata] = {}
        self._loaded_layouts: dict[str, LayoutInfo] = {}
        self._fallback_layouts = ["4x8", "3x4", "console"]

        # Phase 2C Cache Integration - Always enabled for maximum efficiency
        self._cache_manager = cache_manager or get_cache_manager()
        self._key_generator = CacheKeyGenerator()
        logger.debug("LazyLayoutRegistry cache integration enabled")

        # Performance tracking
        self._cache_hits = 0
        self._cache_misses = 0
        self._discovery_time = 0.0
        self._load_times: dict[str, float] = {}
        self._layout_cache_hits = 0
        self._layout_cache_misses = 0

        logger.debug(f"LazyLayoutRegistry initialized with layouts_dir: {self.layouts_dir}")

        # Build lightweight metadata cache only
        self._build_metadata_cache()

    def _build_metadata_cache(self) -> None:
        """Build lightweight metadata cache without loading layout configurations."""
        start_time = time.time()

        try:
            if not self.layouts_dir.exists():
                logger.warning(f"Layouts directory not found: {self.layouts_dir}")
                self._create_emergency_metadata()
                return

            layout_count = 0
            for layout_dir in self.layouts_dir.iterdir():
                if not layout_dir.is_dir():
                    continue

                config_file = layout_dir / "layout.json"
                if not config_file.exists():
                    logger.debug(f"Skipping {layout_dir.name} - no layout.json found")
                    continue

                try:
                    stat_info = config_file.stat()
                    metadata = LayoutMetadata(
                        name=layout_dir.name,
                        config_path=config_file,
                        last_modified=stat_info.st_mtime,
                    )
                    self._metadata_cache[layout_dir.name] = metadata
                    layout_count += 1

                except OSError as e:
                    logger.warning(f"Failed to read metadata for {config_file}: {e}")

            self._discovery_time = time.time() - start_time
            logger.info(
                "LazyLayoutRegistry metadata cache built: %d layouts discovered in %.2fms",
                layout_count,
                self._discovery_time * 1000,
            )

        except Exception:
            logger.exception("Failed to build layout metadata cache")
            self._create_emergency_metadata()

    def _create_emergency_metadata(self) -> None:
        """Create emergency fallback metadata when filesystem discovery fails."""
        logger.warning("Creating emergency fallback layout metadata")

        # Create basic metadata for emergency layouts
        for layout_name in self._fallback_layouts:
            emergency_path = self.layouts_dir / layout_name / "layout.json"
            metadata = LayoutMetadata(
                name=layout_name, config_path=emergency_path, last_modified=time.time()
            )
            self._metadata_cache[layout_name] = metadata

    def get_layout(self, layout_name: str) -> Optional[LayoutInfo]:
        """Get layout with lazy loading - loads on first access.

        Args:
            layout_name: Name of layout to retrieve

        Returns:
            LayoutInfo object or None if not found
        """
        # Check if already loaded
        if layout_name in self._loaded_layouts:
            self._cache_hits += 1
            return self._loaded_layouts[layout_name]

        # Check metadata cache
        if layout_name not in self._metadata_cache:
            self._cache_misses += 1
            return None

        # Load layout on demand
        return self._load_layout_on_demand(layout_name)

    def _load_layout_on_demand(self, layout_name: str) -> Optional[LayoutInfo]:
        """Load layout configuration on first access with caching.

        Args:
            layout_name: Name of layout to load

        Returns:
            LayoutInfo object or None if loading failed
        """
        start_time = time.time()

        # Try cache first - always enabled for efficiency
        cached_layout = self._get_cached_layout(layout_name)
        if cached_layout:
            self._layout_cache_hits += 1
            logger.debug("Layout '%s' loaded from cache", layout_name)
            return cached_layout

        metadata = self._metadata_cache[layout_name]
        config_file = metadata.config_path

        try:
            # Handle emergency layouts that may not exist on filesystem
            if not config_file.exists():
                layout_info = self._create_emergency_layout(layout_name)
                # Cache emergency layout if available
                if layout_info and self._cache_manager:
                    self._cache_layout(layout_name, layout_info)
                return layout_info

            # Try cached configuration first
            config_data = self._get_cached_config(config_file)

            # Load from filesystem if not cached
            if config_data is None:
                with config_file.open(encoding="utf-8") as f:
                    config_data = json.load(f)

                # Cache configuration data
                self._cache_config(config_file, config_data)

            # Validate required fields
            required_fields = ["name", "display_name", "version", "capabilities"]
            for field in required_fields:
                if field not in config_data:
                    _raise_missing_field_error(field)

            # Extract renderer type from mapping
            renderer_mapping = config_data.get("renderer_mapping", {})
            renderer_type = renderer_mapping.get("internal_type", "console")

            layout_info = LayoutInfo(
                name=config_data["name"],
                display_name=config_data["display_name"],
                version=config_data["version"],
                description=config_data.get("description", ""),
                capabilities=config_data["capabilities"],
                renderer_type=renderer_type,
                fallback_chain=config_data.get("fallback_chain", []),
                resources=config_data.get("resources", {}),
                requirements=config_data.get("requirements", {}),
            )

            # Cache loaded layout
            self._loaded_layouts[layout_name] = layout_info
            metadata.is_loaded = True

            # Cache layout object for future efficiency
            self._cache_layout(layout_name, layout_info)

            load_time = time.time() - start_time
            self._load_times[layout_name] = load_time

            logger.debug("Loaded layout '%s' in %.2fms", layout_name, load_time * 1000)
            self._layout_cache_misses += 1  # First load counts as cache miss

            return layout_info

        except json.JSONDecodeError:
            logger.exception(f"Invalid JSON in {config_file}")
            return None
        except Exception:
            logger.exception(f"Failed to load layout '{layout_name}'")
            return None

    def _create_emergency_layout(self, layout_name: str) -> Optional[LayoutInfo]:
        """Create emergency layout info when config file missing.

        Args:
            layout_name: Name of emergency layout to create

        Returns:
            Emergency LayoutInfo or None if unsupported layout
        """
        if layout_name == "4x8":
            layout_info = LayoutInfo(
                name="4x8",
                display_name="4x8 Grid Layout (Emergency)",
                version="1.0.0",
                description="Emergency fallback 4x8 layout",
                capabilities={
                    "grid_dimensions": {"columns": 4, "rows": 8},
                    "renderer_type": "html",
                },
                renderer_type="html",
                fallback_chain=["3x4", "console"],
                resources={"css": ["4x8.css"], "js": ["4x8.js"]},
                requirements={},
            )
        elif layout_name == "3x4":
            layout_info = LayoutInfo(
                name="3x4",
                display_name="3x4 Compact Layout (Emergency)",
                version="1.0.0",
                description="Emergency fallback 3x4 layout",
                capabilities={"grid_dimensions": {"columns": 3, "rows": 4}, "renderer_type": "3x4"},
                renderer_type="3x4",
                fallback_chain=["console"],
                resources={"css": ["3x4.css"], "js": []},
                requirements={},
            )
        elif layout_name == "console":
            layout_info = LayoutInfo(
                name="console",
                display_name="Console Layout (Emergency)",
                version="1.0.0",
                description="Emergency fallback console layout",
                capabilities={"renderer_type": "console"},
                renderer_type="console",
                fallback_chain=[],
                resources={},
                requirements={},
            )
        else:
            logger.warning(f"No emergency layout available for '{layout_name}'")
            return None

        # Cache emergency layout
        self._loaded_layouts[layout_name] = layout_info
        if layout_name in self._metadata_cache:
            self._metadata_cache[layout_name].is_loaded = True

        logger.warning(f"Created emergency layout: {layout_name}")
        return layout_info

    def preload_layout(self, layout_name: str) -> bool:
        """Preload specific layout for performance optimization.

        Args:
            layout_name: Name of layout to preload

        Returns:
            True if layout was successfully preloaded
        """
        if layout_name in self._loaded_layouts:
            return True  # Already loaded

        layout_info = self.get_layout(layout_name)
        return layout_info is not None

    def get_available_layouts(self) -> list[str]:
        """Get list of all available layout names from metadata cache.

        Returns:
            List of layout names discovered during metadata scanning
        """
        return list(self._metadata_cache.keys())

    def validate_layout(self, layout_name: str) -> bool:
        """Validate if a layout exists in metadata cache.

        Args:
            layout_name: Name of layout to validate

        Returns:
            True if layout exists in metadata cache
        """
        return layout_name in self._metadata_cache

    def get_layout_info(self, layout_name: str) -> Optional[LayoutInfo]:
        """Get layout info with lazy loading (alias for get_layout).

        Args:
            layout_name: Name of layout to get info for

        Returns:
            LayoutInfo object or None if not found
        """
        return self.get_layout(layout_name)

    def _get_cached_layout(self, layout_name: str) -> Optional[LayoutInfo]:
        """Retrieve cached layout object.

        Args:
            layout_name: Name of layout to retrieve from cache

        Returns:
            Cached LayoutInfo object or None if not found
        """
        if not self._cache_manager or not self._key_generator:
            return None

        try:
            # Use SIMPLE strategy for layout caching
            cache_key = self._key_generator.generate_simple_key("layout", layout_name)

            # Handle async cache operation synchronously
            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If event loop is running, we can't use asyncio.run()
                    # Skip cache operation to avoid blocking
                    return None
                cached_data = asyncio.run(self._cache_manager.get(cache_key))
            except RuntimeError:
                # Event loop may not be available in sync context
                return None

            if cached_data and isinstance(cached_data, dict):
                # Reconstruct LayoutInfo from cached dictionary
                return LayoutInfo(**cached_data)

        except Exception as e:
            logger.debug(f"Failed to retrieve cached layout '{layout_name}': {e}")

        return None

    def _cache_layout(self, layout_name: str, layout_info: LayoutInfo) -> None:
        """Cache layout object for future retrieval.

        Args:
            layout_name: Name of layout to cache
            layout_info: LayoutInfo object to cache
        """
        if not self._cache_manager or not self._key_generator:
            return

        try:
            cache_key = self._key_generator.generate_simple_key("layout", layout_name)
            # Convert LayoutInfo to dictionary for serialization
            layout_dict = {
                "name": layout_info.name,
                "display_name": layout_info.display_name,
                "version": layout_info.version,
                "description": layout_info.description,
                "capabilities": layout_info.capabilities,
                "renderer_type": layout_info.renderer_type,
                "fallback_chain": layout_info.fallback_chain,
                "resources": layout_info.resources,
                "requirements": layout_info.requirements,
            }

            # Handle async cache operation synchronously
            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If event loop is running, we can't use asyncio.run()
                    # Skip cache operation to avoid blocking
                    return
                asyncio.run(self._cache_manager.set(cache_key, layout_dict, ttl=1800))
            except RuntimeError:
                # Event loop may not be available in sync context
                pass

        except Exception as e:
            logger.debug(f"Failed to cache layout '{layout_name}': {e}")

    def _get_cached_config(self, config_file: Path) -> Optional[dict[str, Any]]:
        """Retrieve cached configuration data.

        Args:
            config_file: Path to configuration file

        Returns:
            Cached configuration dictionary or None if not found
        """
        if not self._cache_manager or not self._key_generator:
            return None

        try:
            # Use file path and modification time for cache key
            stat_info = config_file.stat()
            cache_key = self._key_generator.generate_simple_key(
                "config", f"{config_file}_{stat_info.st_mtime}"
            )

            # Handle async cache operation synchronously
            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If event loop is running, we can't use asyncio.run()
                    # Skip cache operation to avoid blocking
                    return None
                cached_data = asyncio.run(self._cache_manager.get(cache_key))
                if cached_data and isinstance(cached_data, dict):
                    return cached_data
            except RuntimeError:
                # Event loop may not be available in sync context
                pass

        except Exception as e:
            logger.debug(f"Failed to retrieve cached config '{config_file}': {e}")

        return None

    def _cache_config(self, config_file: Path, config_data: dict[str, Any]) -> None:
        """Cache configuration data for future retrieval.

        Args:
            config_file: Path to configuration file
            config_data: Configuration dictionary to cache
        """
        if not self._cache_manager or not self._key_generator:
            return

        try:
            # Use file path and modification time for cache key
            stat_info = config_file.stat()
            cache_key = self._key_generator.generate_simple_key(
                "config", f"{config_file}_{stat_info.st_mtime}"
            )

            # Handle async cache operation synchronously
            import asyncio  # noqa: PLC0415

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If event loop is running, we can't use asyncio.run()
                    # Skip cache operation to avoid blocking
                    return
                asyncio.run(self._cache_manager.set(cache_key, config_data, ttl=3600))
            except RuntimeError:
                # Event loop may not be available in sync context
                pass

        except Exception as e:
            logger.debug(f"Failed to cache config '{config_file}': {e}")

    def get_performance_stats(self) -> dict[str, Any]:
        """Get lazy loading performance statistics.

        Returns:
            Dictionary with performance metrics and cache statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0

        total_layout_requests = self._layout_cache_hits + self._layout_cache_misses
        layout_hit_rate = (
            (self._layout_cache_hits / total_layout_requests * 100)
            if total_layout_requests > 0
            else 0
        )

        stats = {
            "total_layouts_discovered": len(self._metadata_cache),
            "loaded_layouts": len(self._loaded_layouts),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": hit_rate,
            "discovery_time_ms": self._discovery_time * 1000,
            "average_load_time_ms": (
                sum(self._load_times.values()) / len(self._load_times) * 1000
                if self._load_times
                else 0
            ),
            "memory_efficiency_percent": (
                (len(self._metadata_cache) - len(self._loaded_layouts))
                / len(self._metadata_cache)
                * 100
                if self._metadata_cache
                else 0
            ),
            # Phase 2C Cache Statistics
            "layout_cache_enabled": self._cache_manager is not None,
            "layout_cache_hits": self._layout_cache_hits,
            "layout_cache_misses": self._layout_cache_misses,
            "layout_cache_hit_rate_percent": layout_hit_rate,
        }

        # Add cache manager statistics if available
        if self._cache_manager:
            try:
                cache_stats = self._cache_manager.get_cache_stats()
                stats["cache_manager_stats"] = cache_stats
            except Exception as e:
                logger.debug(f"Failed to get cache manager statistics: {e}")

        return stats

    def clear_cache(self) -> None:
        """Clear loaded layout cache for testing or reset."""
        cleared_count = len(self._loaded_layouts)
        self._loaded_layouts.clear()

        # Reset metadata loaded flags
        for metadata in self._metadata_cache.values():
            metadata.is_loaded = False

        # Reset performance counters
        self._cache_hits = 0
        self._cache_misses = 0
        self._load_times.clear()

        logger.info("LazyLayoutRegistry cache cleared: %d layouts unloaded", cleared_count)
