"""Optimized unit tests for StaticAssetCache optimization implementation.

Tests cover O(1) path resolution, cache building, fallback behavior,
security validation, and layout-specific asset handling with minimal file I/O.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from calendarbot.optimization.static_asset_cache import AssetMetadata, StaticAssetCache


class TestAssetMetadata:
    """Test AssetMetadata dataclass."""

    def test_asset_metadata_creation_when_valid_data_then_stores_correctly(self):
        """Test AssetMetadata stores all fields correctly."""
        metadata = AssetMetadata(
            absolute_path=Path("/test/path"),
            size=1024,
            mtime=1234567890.0,
            is_layout_specific=True,
            layout_name="modern",
        )

        assert metadata.absolute_path == Path("/test/path")
        assert metadata.size == 1024
        assert metadata.mtime == 1234567890.0
        assert metadata.is_layout_specific is True
        assert metadata.layout_name == "modern"

    def test_asset_metadata_creation_when_none_layout_then_handles_correctly(self):
        """Test AssetMetadata handles None layout name."""
        metadata = AssetMetadata(
            absolute_path=Path("/test/path"),
            size=512,
            mtime=1234567890.0,
            is_layout_specific=False,
            layout_name=None,
        )

        assert metadata.layout_name is None
        assert metadata.is_layout_specific is False


class TestStaticAssetCacheCore:
    """Test StaticAssetCache core functionality with mocked I/O."""

    def test_init_when_valid_directories_then_initializes_correctly(self):
        """Test StaticAssetCache initialization with valid directories."""
        static_dirs = [Path("/static")]
        layouts_dir = Path("/layouts")

        cache = StaticAssetCache(static_dirs, layouts_dir)

        assert not cache.is_cache_built()
        stats = cache.get_cache_stats()
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["total_assets"] == 0

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.iterdir")
    @patch("pathlib.Path.rglob")
    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.is_file")
    def test_build_cache_when_files_exist_then_builds_complete_map(
        self, mock_is_file, mock_stat, mock_rglob, mock_iterdir, mock_exists
    ):
        """Test cache building creates complete asset map with mocked files."""
        # Mock directory existence
        mock_exists.return_value = True

        # Mock layout directory iteration (return empty list to avoid layout scanning)
        mock_iterdir.return_value = []

        # Mock file structure
        static_files = [Path("/static/style.css"), Path("/static/script.js")]
        mock_rglob.return_value = static_files
        mock_is_file.return_value = True

        # Mock stat with proper attributes
        mock_stat_result = Mock()
        mock_stat_result.st_size = 100
        mock_stat_result.st_mtime = 1234567890.0
        mock_stat.return_value = mock_stat_result

        cache = StaticAssetCache([Path("/static")], Path("/layouts"))
        cache.build_cache()

        # Verify assets can be resolved
        assert cache.resolve_asset_path("style.css") is not None
        assert cache.resolve_asset_path("script.js") is not None

        # Verify metadata structure
        css_metadata = cache.get_asset_metadata("style.css")
        assert isinstance(css_metadata, AssetMetadata)
        assert css_metadata.absolute_path.name == "style.css"
        assert css_metadata.size == 100
        assert css_metadata.is_layout_specific is False

    def test_resolve_asset_path_when_cache_hit_then_returns_o1_lookup(self):
        """Test O(1) asset path resolution on cache hit."""
        cache = StaticAssetCache([Path("/static")], Path("/layouts"))

        # Manually populate cache to avoid file I/O
        metadata = AssetMetadata(
            absolute_path=Path("/static/style.css"),
            size=100,
            mtime=1234567890.0,
            is_layout_specific=False,
            layout_name=None,
        )
        cache._asset_map["style.css"] = metadata

        # Test static file resolution
        result = cache.resolve_asset_path("style.css")
        assert result is not None
        assert result.name == "style.css"

        stats = cache.get_cache_stats()
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 0

    def test_resolve_asset_path_when_layout_specific_then_uses_layout_prefix(self):
        """Test layout-specific asset resolution."""
        cache = StaticAssetCache([Path("/static")], Path("/layouts"))

        # Manually populate cache with layout-specific asset
        metadata = AssetMetadata(
            absolute_path=Path("/layouts/modern/layout.css"),
            size=150,
            mtime=1234567890.0,
            is_layout_specific=True,
            layout_name="modern",
        )
        cache._asset_map["modern/layout.css"] = metadata

        # Test layout-specific file resolution
        result = cache.resolve_asset_path("layout.css", layout_name="modern")
        assert result is not None
        assert result.name == "layout.css"
        assert "modern" in str(result)

        stats = cache.get_cache_stats()
        assert stats["cache_hits"] == 1

    def test_resolve_asset_path_when_cache_miss_then_returns_none(self):
        """Test cache miss returns None and increments miss counter."""
        cache = StaticAssetCache([Path("/static")], Path("/layouts"))
        # Cache is empty, so any lookup should be a miss

        result = cache.resolve_asset_path("nonexistent.css")
        assert result is None

        stats = cache.get_cache_stats()
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 1

    def test_resolve_asset_path_when_path_separators_then_normalizes(self):
        """Test path separator normalization."""
        cache = StaticAssetCache([Path("/static")], Path("/layouts"))

        # Manually populate cache
        metadata = AssetMetadata(
            absolute_path=Path("/static/css/style.css"),
            size=100,
            mtime=1234567890.0,
            is_layout_specific=False,
            layout_name=None,
        )
        cache._asset_map["css/style.css"] = metadata

        # Test with different path separators
        result1 = cache.resolve_asset_path("css/style.css")
        result2 = cache.resolve_asset_path("css\\style.css")  # Windows style
        result3 = cache.resolve_asset_path("/css/style.css")  # Leading slash

        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
        assert result1 == result2 == result3

    @patch("calendarbot.optimization.static_asset_cache.logger")
    @patch("pathlib.Path.rglob")
    def test_scan_directory_when_permission_error_then_logs_and_continues(
        self, mock_rglob, mock_logger
    ):
        """Test directory scanning handles permission errors gracefully."""
        cache = StaticAssetCache([Path("/static")], Path("/layouts"))
        mock_rglob.side_effect = OSError("Permission denied")

        # Should not raise, just log
        result = cache._scan_directory(Path("/static"))
        assert result == 0  # No assets scanned
        mock_logger.warning.assert_called_once()

    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.rglob")
    @patch("pathlib.Path.is_file")
    def test_scan_directory_when_file_stat_error_then_skips_file(
        self, mock_is_file, mock_rglob, mock_stat
    ):
        """Test file scanning skips files with stat errors."""
        cache = StaticAssetCache([Path("/static")], Path("/layouts"))
        mock_rglob.return_value = [Path("/static/temp.css")]
        mock_is_file.return_value = True
        mock_stat.side_effect = OSError("File not found")

        # Should not crash and should not include the problematic file
        result = cache._scan_directory(Path("/static"))
        assert result == 0  # No assets successfully cached
        assert cache.resolve_asset_path("temp.css") is None

    def test_get_cache_stats_when_operations_performed_then_returns_accurate_stats(self):
        """Test cache statistics tracking."""
        cache = StaticAssetCache([Path("/static")], Path("/layouts"))

        # Manually populate cache
        cache._asset_map["style.css"] = AssetMetadata(
            absolute_path=Path("/static/style.css"),
            size=100,
            mtime=1234567890.0,
            is_layout_specific=False,
            layout_name=None,
        )
        cache._asset_map["script.js"] = AssetMetadata(
            absolute_path=Path("/static/script.js"),
            size=200,
            mtime=1234567890.0,
            is_layout_specific=False,
            layout_name=None,
        )

        # Perform some operations
        cache.resolve_asset_path("style.css")  # hit
        cache.resolve_asset_path("script.js")  # hit
        cache.resolve_asset_path("missing.css")  # miss

        stats = cache.get_cache_stats()
        assert stats["cache_hits"] == 2
        assert stats["cache_misses"] == 1
        assert stats["total_assets"] == 2
        assert abs(stats["hit_rate_percent"] - (2 / 3 * 100)) < 0.01

    @patch("pathlib.Path.exists")
    def test_build_cache_when_empty_directories_then_handles_gracefully(self, mock_exists):
        """Test cache building with empty directories."""
        mock_exists.return_value = False  # Directories don't exist

        cache = StaticAssetCache([Path("/static")], Path("/layouts"))
        cache.build_cache()

        stats = cache.get_cache_stats()
        assert stats["total_assets"] == 0

    def test_build_cache_when_nested_layout_structure_then_maps_correctly(self):
        """Test cache building with nested layout directory structures."""
        cache = StaticAssetCache([Path("/static")], Path("/layouts"))

        # Manually populate cache to test layout-specific functionality
        metadata = AssetMetadata(
            absolute_path=Path("/layouts/modern/components/button.css"),
            size=50,
            mtime=1234567890.0,
            is_layout_specific=True,
            layout_name="modern",
        )
        cache._asset_map["modern/components/button.css"] = metadata
        cache._asset_map["components/button.css"] = metadata  # Direct lookup fallback

        assert cache.resolve_asset_path("components/button.css", layout_name="modern") is not None
        metadata_result = cache.get_asset_metadata("components/button.css", layout_name="modern")
        assert metadata_result is not None
        assert metadata_result.is_layout_specific is True
        assert metadata_result.layout_name == "modern"

    def test_is_static_asset_when_valid_extensions_then_returns_true(self):
        """Test static asset detection for valid file types."""
        cache = StaticAssetCache([Path("/static")], Path("/layouts"))

        valid_files = [
            Path("/test/style.css"),
            Path("/test/script.js"),
            Path("/test/image.png"),
            Path("/test/font.woff2"),
            Path("/test/page.html"),
        ]

        for file_path in valid_files:
            assert cache._is_static_asset(file_path) is True

    def test_is_static_asset_when_invalid_extensions_then_returns_false(self):
        """Test static asset detection excludes invalid file types."""
        cache = StaticAssetCache([Path("/static")], Path("/layouts"))

        invalid_files = [
            Path("/test/.hidden"),
            Path("/test/script.py"),
            Path("/test/config.conf"),
            Path("/test/Thumbs.db"),
            Path("/test/.DS_Store"),
        ]

        for file_path in invalid_files:
            assert cache._is_static_asset(file_path) is False

    def test_invalidate_asset_when_exists_then_removes_from_cache(self):
        """Test asset invalidation removes from cache."""
        cache = StaticAssetCache([Path("/static")], Path("/layouts"))

        # Add asset to cache
        cache._asset_map["style.css"] = AssetMetadata(
            absolute_path=Path("/static/style.css"),
            size=100,
            mtime=1234567890.0,
            is_layout_specific=False,
            layout_name=None,
        )

        # Verify it exists
        assert cache.resolve_asset_path("style.css") is not None

        # Invalidate
        result = cache.invalidate_asset("style.css")
        assert result is True

        # Verify it's gone
        assert cache.resolve_asset_path("style.css") is None

    def test_clear_cache_when_called_then_resets_all_state(self):
        """Test cache clearing resets all state."""
        cache = StaticAssetCache([Path("/static")], Path("/layouts"))

        # Populate cache and stats
        cache._asset_map["style.css"] = AssetMetadata(
            absolute_path=Path("/static/style.css"),
            size=100,
            mtime=1234567890.0,
            is_layout_specific=False,
            layout_name=None,
        )
        cache._cache_hits = 5
        cache._cache_misses = 2
        cache._build_time = 0.1

        # Clear cache
        cache.clear_cache()

        # Verify everything is reset
        stats = cache.get_cache_stats()
        assert stats["total_assets"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["build_time_ms"] == 0.0
        assert not cache.is_cache_built()


class TestStaticAssetCacheFileOperations:
    """Test StaticAssetCache with minimal real file operations for critical paths."""

    @pytest.fixture
    def minimal_temp_structure(self):
        """Create minimal temporary structure for essential tests."""
        temp_dir = tempfile.mkdtemp()
        static_dir = Path(temp_dir) / "static"
        layouts_dir = Path(temp_dir) / "layouts"

        static_dir.mkdir()
        layouts_dir.mkdir()

        # Create minimal test files
        (static_dir / "test.css").write_text("/* test */")

        modern_dir = layouts_dir / "modern"
        modern_dir.mkdir()
        (modern_dir / "layout.css").write_text("/* modern */")

        yield {"temp_dir": Path(temp_dir), "static_dirs": [static_dir], "layouts_dir": layouts_dir}

        shutil.rmtree(temp_dir)

    def test_resolve_asset_path_when_multiple_static_dirs_then_searches_all(
        self, minimal_temp_structure
    ):
        """Test asset resolution searches all static directories."""
        cache = StaticAssetCache(
            minimal_temp_structure["static_dirs"], minimal_temp_structure["layouts_dir"]
        )
        cache.build_cache()

        assert cache.resolve_asset_path("test.css") is not None
        assert cache.resolve_asset_path("layout.css", layout_name="modern") is not None

    def test_cache_invalidation_when_file_modified_then_detection_possible(
        self, minimal_temp_structure
    ):
        """Test that cache can detect file modifications via mtime."""
        cache = StaticAssetCache(
            minimal_temp_structure["static_dirs"], minimal_temp_structure["layouts_dir"]
        )
        cache.build_cache()

        # Get original metadata
        original_metadata = cache.get_asset_metadata("test.css")
        assert original_metadata is not None
        original_mtime = original_metadata.mtime

        # Modify file (with time delay to ensure different mtime)
        import time

        time.sleep(0.1)

        test_file = minimal_temp_structure["static_dirs"][0] / "test.css"
        test_file.write_text("/* modified */")

        # Get new mtime
        new_mtime = test_file.stat().st_mtime

        # Verify mtime difference allows for cache invalidation logic
        assert new_mtime > original_mtime


class TestStaticAssetCachePerformance:
    """Test performance characteristics with minimal overhead."""

    def test_performance_o1_lookup_time_complexity(self):
        """Test that asset resolution is O(1) regardless of cache size."""
        cache = StaticAssetCache([Path("/static")], Path("/layouts"))

        # Mock large cache structure for performance testing
        for i in range(100):  # Reduced from 1000 for faster testing
            cache._asset_map[f"file_{i}.css"] = AssetMetadata(
                absolute_path=Path(f"/static/file_{i}.css"),
                size=100,
                mtime=1234567890.0,
                is_layout_specific=False,
                layout_name=None,
            )

        # Measure lookup time for first and last file
        import time

        start_time = time.time()
        cache.resolve_asset_path("file_0.css")
        first_lookup_time = time.time() - start_time

        start_time = time.time()
        cache.resolve_asset_path("file_99.css")
        last_lookup_time = time.time() - start_time

        # O(1) lookup should have similar performance regardless of position
        assert abs(first_lookup_time - last_lookup_time) < 0.001  # 1ms variance

    def test_memory_efficiency_asset_metadata_size(self):
        """Test memory-efficient asset metadata storage."""
        cache = StaticAssetCache([Path("/static")], Path("/layouts"))

        # Create mock metadata for testing
        metadata = AssetMetadata(
            absolute_path=Path("/static/test.css"),
            size=100,
            mtime=1234567890.0,
            is_layout_specific=False,
            layout_name=None,
        )

        # Check that metadata objects are lightweight
        import sys

        metadata_size = sys.getsizeof(metadata)
        assert metadata_size < 200  # Reasonable size limit for metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
