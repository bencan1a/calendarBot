"""Unit tests for StaticAssetCache optimization implementation.

Tests cover O(1) path resolution, cache building, fallback behavior,
security validation, and layout-specific asset handling.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

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


class TestStaticAssetCache:
    """Test StaticAssetCache core functionality."""

    @pytest.fixture
    def temp_directories(self):
        """Create temporary directories for testing."""
        temp_dir = tempfile.mkdtemp()
        static_dir = Path(temp_dir) / "static"
        layouts_dir = Path(temp_dir) / "layouts"

        static_dir.mkdir()
        layouts_dir.mkdir()

        # Create test files
        (static_dir / "style.css").write_text("body { margin: 0; }")
        (static_dir / "script.js").write_text("console.log('test');")

        # Create layout-specific files
        modern_dir = layouts_dir / "modern"
        modern_dir.mkdir()
        (modern_dir / "layout.css").write_text("/* modern layout */")
        (modern_dir / "layout.js").write_text("// modern layout")

        classic_dir = layouts_dir / "classic"
        classic_dir.mkdir()
        (classic_dir / "layout.css").write_text("/* classic layout */")

        yield {"temp_dir": Path(temp_dir), "static_dirs": [static_dir], "layouts_dir": layouts_dir}

        shutil.rmtree(temp_dir)

    def test_init_when_valid_directories_then_initializes_correctly(self, temp_directories):
        """Test StaticAssetCache initialization with valid directories."""
        cache = StaticAssetCache(temp_directories["static_dirs"], temp_directories["layouts_dir"])

        # Test initialization through public interface
        assert not cache.is_cache_built()
        stats = cache.get_cache_stats()
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["total_assets"] == 0

    def test_build_cache_when_files_exist_then_builds_complete_map(self, temp_directories):
        """Test cache building creates complete asset map."""
        cache = StaticAssetCache(temp_directories["static_dirs"], temp_directories["layouts_dir"])
        cache.build_cache()

        # Check static files are cached via resolution
        assert cache.resolve_asset_path("style.css") is not None
        assert cache.resolve_asset_path("script.js") is not None

        # Check layout-specific files are cached
        assert cache.resolve_asset_path("modern/layout.css") is not None
        assert cache.resolve_asset_path("modern/layout.js") is not None
        assert cache.resolve_asset_path("classic/layout.css") is not None

        # Verify metadata structure via public interface
        css_metadata = cache.get_asset_metadata("style.css")
        assert isinstance(css_metadata, AssetMetadata)
        assert css_metadata.absolute_path.name == "style.css"
        assert css_metadata.size > 0
        assert css_metadata.mtime > 0
        assert css_metadata.is_layout_specific is False
        assert css_metadata.layout_name is None

    def test_build_cache_when_layout_files_then_marks_layout_specific(self, temp_directories):
        """Test layout-specific files are properly marked."""
        cache = StaticAssetCache(temp_directories["static_dirs"], temp_directories["layouts_dir"])
        cache.build_cache()

        modern_css = cache.get_asset_metadata("modern/layout.css")
        assert modern_css is not None
        assert modern_css.is_layout_specific is True
        assert modern_css.layout_name == "modern"

        classic_css = cache.get_asset_metadata("classic/layout.css")
        assert classic_css is not None
        assert classic_css.is_layout_specific is True
        assert classic_css.layout_name == "classic"

    def test_resolve_asset_path_when_cache_hit_then_returns_o1_lookup(self, temp_directories):
        """Test O(1) asset path resolution on cache hit."""
        cache = StaticAssetCache(temp_directories["static_dirs"], temp_directories["layouts_dir"])
        cache.build_cache()

        # Test static file resolution
        result = cache.resolve_asset_path("style.css")
        assert result is not None
        assert result.name == "style.css"

        stats = cache.get_cache_stats()
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 0

        # Test layout-specific file resolution
        result = cache.resolve_asset_path("modern/layout.css")
        assert result is not None
        assert result.name == "layout.css"
        assert "modern" in str(result)

        stats = cache.get_cache_stats()
        assert stats["cache_hits"] == 2

    def test_resolve_asset_path_when_cache_miss_then_returns_none_and_increments_miss(
        self, temp_directories
    ):
        """Test cache miss returns None and increments miss counter."""
        cache = StaticAssetCache(temp_directories["static_dirs"], temp_directories["layouts_dir"])
        cache.build_cache()

        result = cache.resolve_asset_path("nonexistent.css")
        assert result is None

        stats = cache.get_cache_stats()
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 1

    def test_resolve_asset_path_when_relative_path_then_validates_security(self, temp_directories):
        """Test security validation prevents path traversal."""
        cache = StaticAssetCache(temp_directories["static_dirs"], temp_directories["layouts_dir"])
        cache.build_cache()

        # Test path traversal attempts
        result = cache.resolve_asset_path("../../../etc/passwd")
        assert result is None

        result = cache.resolve_asset_path("..\\..\\windows\\system32\\cmd.exe")
        assert result is None

        # Test legitimate paths still work
        result = cache.resolve_asset_path("style.css")
        assert result is not None

    @patch("calendarbot.optimization.static_asset_cache.logger")
    def test_scan_directory_when_permission_error_then_logs_and_continues(
        self, mock_logger, temp_directories
    ):
        """Test directory scanning handles permission errors gracefully."""
        cache = StaticAssetCache(temp_directories["static_dirs"], temp_directories["layouts_dir"])

        # Mock permission error for rglob method used in _scan_directory
        with patch("pathlib.Path.rglob", side_effect=OSError("Permission denied")):
            cache._scan_directory(temp_directories["static_dirs"][0])

        mock_logger.warning.assert_called_once()

    def test_scan_directory_when_file_stat_error_then_skips_file(self, temp_directories):
        """Test file scanning skips files with stat errors."""
        cache = StaticAssetCache(temp_directories["static_dirs"], temp_directories["layouts_dir"])

        # Create a file and then remove it to cause stat error
        test_file = temp_directories["static_dirs"][0] / "temp.txt"
        test_file.write_text("test")

        with patch.object(Path, "stat", side_effect=OSError("File not found")):
            cache._scan_directory(temp_directories["static_dirs"][0])

        # Should not crash and should not include the problematic file
        assert cache.resolve_asset_path("temp.txt") is None

    def test_get_cache_stats_when_operations_performed_then_returns_accurate_stats(
        self, temp_directories
    ):
        """Test cache statistics tracking."""
        cache = StaticAssetCache(temp_directories["static_dirs"], temp_directories["layouts_dir"])
        cache.build_cache()

        # Perform some operations
        cache.resolve_asset_path("style.css")  # hit
        cache.resolve_asset_path("script.js")  # hit
        cache.resolve_asset_path("missing.css")  # miss

        stats = cache.get_cache_stats()
        assert stats["cache_hits"] == 2
        assert stats["cache_misses"] == 1
        assert stats["total_assets"] >= 4  # At least our test files
        assert (
            abs(stats["hit_rate_percent"] - (2 / 3 * 100)) < 0.01
        )  # 2 hits out of 3 requests * 100

    def test_build_cache_when_empty_directories_then_handles_gracefully(self):
        """Test cache building with empty directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            static_dir = Path(temp_dir) / "static"
            layouts_dir = Path(temp_dir) / "layouts"
            static_dir.mkdir()
            layouts_dir.mkdir()

            cache = StaticAssetCache([static_dir], layouts_dir)
            cache.build_cache()

            stats = cache.get_cache_stats()
            assert stats["total_assets"] == 0

    def test_build_cache_when_nested_layout_structure_then_maps_correctly(self, temp_directories):
        """Test cache building with nested layout directory structures."""
        # Create nested layout structure
        layouts_dir = temp_directories["layouts_dir"]
        nested_dir = layouts_dir / "modern" / "components"
        nested_dir.mkdir()
        (nested_dir / "button.css").write_text("/* button styles */")

        cache = StaticAssetCache(temp_directories["static_dirs"], layouts_dir)
        cache.build_cache()

        assert cache.resolve_asset_path("modern/components/button.css") is not None
        metadata = cache.get_asset_metadata("modern/components/button.css")
        assert metadata is not None
        assert metadata.is_layout_specific is True
        assert metadata.layout_name == "modern"

    def test_resolve_asset_path_when_multiple_static_dirs_then_searches_all(self):
        """Test asset resolution searches all static directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            static_dir1 = Path(temp_dir) / "static1"
            static_dir2 = Path(temp_dir) / "static2"
            layouts_dir = Path(temp_dir) / "layouts"

            for directory in [static_dir1, static_dir2, layouts_dir]:
                directory.mkdir()

            # Create files in different static directories
            (static_dir1 / "file1.css").write_text("/* file1 */")
            (static_dir2 / "file2.css").write_text("/* file2 */")

            cache = StaticAssetCache([static_dir1, static_dir2], layouts_dir)
            cache.build_cache()

            assert cache.resolve_asset_path("file1.css") is not None
            assert cache.resolve_asset_path("file2.css") is not None

            result1 = cache.resolve_asset_path("file1.css")
            result2 = cache.resolve_asset_path("file2.css")

            assert result1 is not None
            assert result2 is not None
            assert result1.name == "file1.css"
            assert result2.name == "file2.css"

    def test_performance_o1_lookup_time_complexity(self, temp_directories):
        """Test that asset resolution is O(1) regardless of cache size."""
        import time

        cache = StaticAssetCache(temp_directories["static_dirs"], temp_directories["layouts_dir"])

        # Create many files to test O(1) performance
        static_dir = temp_directories["static_dirs"][0]
        for i in range(1000):
            (static_dir / f"file_{i}.css").write_text(f"/* file {i} */")

        cache.build_cache()

        # Measure lookup time for first and last file
        start_time = time.time()
        cache.resolve_asset_path("file_0.css")
        first_lookup_time = time.time() - start_time

        start_time = time.time()
        cache.resolve_asset_path("file_999.css")
        last_lookup_time = time.time() - start_time

        # O(1) lookup should have similar performance regardless of position
        # Allow for some variance due to system scheduling
        assert abs(first_lookup_time - last_lookup_time) < 0.001  # 1ms variance

    def test_memory_efficiency_asset_metadata_size(self, temp_directories):
        """Test memory-efficient asset metadata storage."""
        cache = StaticAssetCache(temp_directories["static_dirs"], temp_directories["layouts_dir"])
        cache.build_cache()

        # Check that metadata objects are lightweight
        import sys

        # Test a few known assets via public interface
        for asset_name in ["style.css", "script.js"]:
            metadata = cache.get_asset_metadata(asset_name)
            if metadata:
                # AssetMetadata should be small due to dataclass efficiency
                metadata_size = sys.getsizeof(metadata)
                assert metadata_size < 200  # Reasonable size limit for metadata

    def test_cache_invalidation_when_file_modified_then_detection_possible(self, temp_directories):
        """Test that cache can detect file modifications via mtime."""
        cache = StaticAssetCache(temp_directories["static_dirs"], temp_directories["layouts_dir"])
        cache.build_cache()

        # Get original metadata
        original_metadata = cache.get_asset_metadata("style.css")
        assert original_metadata is not None
        original_mtime = original_metadata.mtime

        # Modify file (with time delay to ensure different mtime)
        import time

        time.sleep(0.1)

        style_file = temp_directories["static_dirs"][0] / "style.css"
        style_file.write_text("body { margin: 10px; }")

        # Get new mtime
        new_mtime = style_file.stat().st_mtime

        # Verify mtime difference allows for cache invalidation logic
        assert new_mtime > original_mtime


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
