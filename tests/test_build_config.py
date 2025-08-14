"""
Unit tests for calendarbot/config/build.py

Tests production asset filtering, environment detection, and debug asset exclusion
functionality for the static asset optimization system.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from calendarbot.config.build import (
    DEVELOPMENT_ARTIFACTS,
    PRODUCTION_EXCLUDES,
    TEST_PATTERNS,
    ProductionAssetFilter,
    filter_asset_paths,
    get_asset_exclusion_info,
    get_excluded_patterns,
    get_production_filter,
    is_debug_asset,
    is_production_mode,
    should_exclude_asset,
    validate_asset_path,
)


class TestEnvironmentDetection:
    """Test environment detection and production mode logic."""

    def test_is_production_mode_when_env_is_production(self):
        """Test production mode detection with CALENDARBOT_ENV=production."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            assert is_production_mode() is True

    def test_is_production_mode_when_env_is_prod(self):
        """Test production mode detection with CALENDARBOT_ENV=prod."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "prod"}):
            assert is_production_mode() is True

    def test_is_production_mode_when_env_is_development(self):
        """Test development mode detection with CALENDARBOT_ENV=development."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "development"}):
            assert is_production_mode() is False

    def test_is_production_mode_when_env_is_dev(self):
        """Test development mode detection with CALENDARBOT_ENV=dev."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "dev"}):
            assert is_production_mode() is False

    def test_is_production_mode_when_env_is_debug(self):
        """Test development mode detection with CALENDARBOT_ENV=debug."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "debug"}):
            assert is_production_mode() is False

    def test_is_production_mode_when_debug_is_true(self):
        """Test development mode detection with CALENDARBOT_DEBUG=true."""
        with patch.dict(os.environ, {"CALENDARBOT_DEBUG": "true"}, clear=True):
            assert is_production_mode() is False

    def test_is_production_mode_when_debug_is_1(self):
        """Test development mode detection with CALENDARBOT_DEBUG=1."""
        with patch.dict(os.environ, {"CALENDARBOT_DEBUG": "1"}, clear=True):
            assert is_production_mode() is False

    def test_is_production_mode_when_debug_is_false(self):
        """Test production mode detection with CALENDARBOT_DEBUG=false."""
        with patch.dict(os.environ, {"CALENDARBOT_DEBUG": "false"}, clear=True):
            assert is_production_mode() is True

    def test_is_production_mode_when_debug_is_0(self):
        """Test production mode detection with CALENDARBOT_DEBUG=0."""
        with patch.dict(os.environ, {"CALENDARBOT_DEBUG": "0"}, clear=True):
            assert is_production_mode() is True

    def test_is_production_mode_when_no_env_vars(self):
        """Test default production mode when no environment variables are set."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_production_mode() is True

    def test_is_production_mode_when_env_precedence(self):
        """Test CALENDARBOT_ENV takes precedence over CALENDARBOT_DEBUG."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production", "CALENDARBOT_DEBUG": "true"}):
            assert is_production_mode() is True


class TestDebugAssetDetection:
    """Test debug asset pattern matching and identification."""

    def test_is_debug_asset_when_debug_prefix(self):
        """Test debug asset detection for debug-* pattern."""
        assert is_debug_asset("debug-console.js") is True
        assert is_debug_asset("debug-utils.js") is True
        assert is_debug_asset("debug-handler.js") is True

    def test_is_debug_asset_when_development_prefix(self):
        """Test debug asset detection for development-* pattern."""
        assert is_debug_asset("development-tools.js") is True
        assert is_debug_asset("development-logger.js") is True

    def test_is_debug_asset_when_test_prefix(self):
        """Test debug asset detection for test-* pattern."""
        assert is_debug_asset("test-helpers.js") is True
        assert is_debug_asset("test-mock.js") is True

    def test_is_debug_asset_when_mock_prefix(self):
        """Test debug asset detection for mock-* pattern."""
        assert is_debug_asset("mock-api.js") is True
        assert is_debug_asset("mock-data.js") is True

    def test_is_debug_asset_when_specific_debug_files(self):
        """Test debug asset detection for specific identified debug files."""
        assert is_debug_asset("settings-panel.js") is True
        assert is_debug_asset("settings-api.js") is True
        assert is_debug_asset("gesture-handler.js") is True

    def test_is_debug_asset_when_debug_suffix(self):
        """Test debug asset detection for *-debug.js pattern."""
        assert is_debug_asset("utils-debug.js") is True
        assert is_debug_asset("api-debug.js") is True

    def test_is_debug_asset_when_dev_suffix(self):
        """Test debug asset detection for *-dev.js pattern."""
        assert is_debug_asset("utils-dev.js") is True
        assert is_debug_asset("api-dev.js") is True

    def test_is_debug_asset_when_dot_debug(self):
        """Test debug asset detection for *.debug.js pattern."""
        assert is_debug_asset("utils.debug.js") is True
        assert is_debug_asset("api.debug.js") is True

    def test_is_debug_asset_when_dot_dev(self):
        """Test debug asset detection for *.dev.js pattern."""
        assert is_debug_asset("utils.dev.js") is True
        assert is_debug_asset("api.dev.js") is True

    def test_is_debug_asset_when_source_maps(self):
        """Test debug asset detection for source maps."""
        assert is_debug_asset("app.js.map") is True
        assert is_debug_asset("utils.map") is True
        assert is_debug_asset("api-sourcemap.js") is True

    def test_is_debug_asset_when_test_files(self):
        """Test debug asset detection for test files."""
        assert is_debug_asset("utils.test.js") is True
        assert is_debug_asset("api.spec.js") is True
        assert is_debug_asset("component.mock.js") is True

    def test_is_debug_asset_when_production_files(self):
        """Test production files are not detected as debug assets."""
        assert is_debug_asset("app.js") is False
        assert is_debug_asset("utils.js") is False
        assert is_debug_asset("main.css") is False
        assert is_debug_asset("styles.css") is False
        assert is_debug_asset("layout.html") is False

    def test_is_debug_asset_when_case_insensitive(self):
        """Test debug asset detection is case insensitive."""
        assert is_debug_asset("DEBUG-utils.js") is True
        assert is_debug_asset("DEVELOPMENT-tools.js") is True
        assert is_debug_asset("TEST-helpers.js") is True

    def test_is_debug_asset_when_path_object(self):
        """Test debug asset detection with Path objects."""
        assert is_debug_asset(Path("debug-console.js")) is True
        assert is_debug_asset(Path("app.js")) is False

    def test_is_debug_asset_when_nested_path(self):
        """Test debug asset detection with nested paths."""
        assert is_debug_asset("shared/js/debug-console.js") is True
        assert is_debug_asset("assets/debug/utils.js") is False  # Pattern matches filename only


class TestAssetExclusion:
    """Test asset exclusion logic combining environment and debug detection."""

    def test_should_exclude_asset_when_production_and_debug(self):
        """Test asset exclusion in production mode for debug assets."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            assert should_exclude_asset("debug-console.js") is True
            assert should_exclude_asset("settings-panel.js") is True

    def test_should_exclude_asset_when_production_and_production_file(self):
        """Test asset inclusion in production mode for production assets."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            assert should_exclude_asset("app.js") is False
            assert should_exclude_asset("utils.js") is False

    def test_should_exclude_asset_when_development_and_debug(self):
        """Test asset inclusion in development mode for debug assets."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "development"}):
            assert should_exclude_asset("debug-console.js") is False
            assert should_exclude_asset("settings-panel.js") is False

    def test_should_exclude_asset_when_development_and_production_file(self):
        """Test asset inclusion in development mode for production assets."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "development"}):
            assert should_exclude_asset("app.js") is False
            assert should_exclude_asset("utils.js") is False


class TestAssetPathFiltering:
    """Test asset path list filtering functionality."""

    def test_filter_asset_paths_when_production_mode(self):
        """Test asset path filtering removes debug assets in production."""
        from typing import List, Union

        asset_paths: List[Union[str, Path]] = [
            "app.js",
            "debug-console.js",
            "utils.js",
            "settings-panel.js",
            "styles.css",
        ]

        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            filtered = filter_asset_paths(asset_paths)

        expected = ["app.js", "utils.js", "styles.css"]
        assert filtered == expected

    def test_filter_asset_paths_when_development_mode(self):
        """Test asset path filtering includes all assets in development."""
        from typing import List, Union

        asset_paths: List[Union[str, Path]] = [
            "app.js",
            "debug-console.js",
            "utils.js",
            "settings-panel.js",
            "styles.css",
        ]

        with patch.dict(os.environ, {"CALENDARBOT_ENV": "development"}):
            filtered = filter_asset_paths(asset_paths)

        assert filtered == asset_paths

    def test_filter_asset_paths_when_empty_list(self):
        """Test asset path filtering with empty input."""
        from typing import List, Union

        empty_list: List[Union[str, Path]] = []
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            filtered = filter_asset_paths(empty_list)

        assert filtered == []

    def test_filter_asset_paths_when_no_debug_assets(self):
        """Test asset path filtering with no debug assets."""
        from typing import List, Union

        asset_paths: List[Union[str, Path]] = ["app.js", "utils.js", "styles.css"]

        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            filtered = filter_asset_paths(asset_paths)

        assert filtered == asset_paths

    def test_filter_asset_paths_when_only_debug_assets(self):
        """Test asset path filtering with only debug assets."""
        from typing import List, Union

        asset_paths: List[Union[str, Path]] = [
            "debug-console.js",
            "settings-panel.js",
            "test-helper.js",
        ]

        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            filtered = filter_asset_paths(asset_paths)

        assert filtered == []


class TestAssetPathValidation:
    """Test asset path validation and security checks."""

    def test_validate_asset_path_when_valid_relative_path(self):
        """Test validation accepts valid relative paths."""
        assert validate_asset_path("js/app.js") is True
        assert validate_asset_path("css/styles.css") is True
        assert validate_asset_path("images/logo.png") is True

    def test_validate_asset_path_when_empty_path(self):
        """Test validation rejects empty paths."""
        assert validate_asset_path("") is False
        # Test None case with type ignore for intentional invalid input testing
        assert validate_asset_path(None) is False  # type: ignore[arg-type]

    def test_validate_asset_path_when_path_traversal(self):
        """Test validation rejects path traversal attempts."""
        assert validate_asset_path("../../../etc/passwd") is False
        assert validate_asset_path("js/../../../config.js") is False
        assert validate_asset_path("..\\windows\\system32") is False

    def test_validate_asset_path_when_absolute_path(self):
        """Test validation rejects absolute paths."""
        assert validate_asset_path("/etc/passwd") is False
        assert validate_asset_path("C:\\Windows\\System32") is False
        assert validate_asset_path("/home/user/file.js") is False

    def test_validate_asset_path_when_path_object(self):
        """Test validation works with Path objects."""
        assert validate_asset_path(Path("js/app.js")) is True
        assert validate_asset_path(Path("../config.js")) is False


class TestProductionAssetFilter:
    """Test the ProductionAssetFilter class functionality."""

    def test_production_asset_filter_init_production_mode(self):
        """Test ProductionAssetFilter initialization in production mode."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            filter_instance = ProductionAssetFilter()

        assert filter_instance.production_mode is True
        assert len(filter_instance.exclusion_patterns) > 0

    def test_production_asset_filter_init_development_mode(self):
        """Test ProductionAssetFilter initialization in development mode."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "development"}):
            filter_instance = ProductionAssetFilter()

        assert filter_instance.production_mode is False
        assert len(filter_instance.exclusion_patterns) == 0

    def test_production_asset_filter_should_serve_asset_production(self):
        """Test asset serving decision in production mode."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            filter_instance = ProductionAssetFilter()

        assert filter_instance.should_serve_asset("app.js") is True
        assert filter_instance.should_serve_asset("debug-console.js") is False
        assert filter_instance.should_serve_asset("settings-panel.js") is False

    def test_production_asset_filter_should_serve_asset_development(self):
        """Test asset serving decision in development mode."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "development"}):
            filter_instance = ProductionAssetFilter()

        assert filter_instance.should_serve_asset("app.js") is True
        assert filter_instance.should_serve_asset("debug-console.js") is True
        assert filter_instance.should_serve_asset("settings-panel.js") is True

    def test_production_asset_filter_caching(self):
        """Test exclusion caching functionality."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            filter_instance = ProductionAssetFilter()

        # First call should compute and cache
        result1 = filter_instance.should_serve_asset("debug-console.js")
        # Second call should use cache
        result2 = filter_instance.should_serve_asset("debug-console.js")

        assert result1 is False
        assert result2 is False
        assert "debug-console.js" in filter_instance._excluded_cache

    def test_production_asset_filter_get_serving_decision(self):
        """Test detailed serving decision information."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            filter_instance = ProductionAssetFilter()

        decision = filter_instance.get_serving_decision("debug-console.js")

        assert decision["file_path"] == "debug-console.js"
        assert decision["should_serve"] is False
        assert decision["is_debug_asset"] is True
        assert decision["production_mode"] is True
        assert decision["excluded_reason"] == "debug_asset_in_production"

    def test_production_asset_filter_clear_cache(self):
        """Test cache clearing functionality."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            filter_instance = ProductionAssetFilter()

        # Populate cache
        filter_instance.should_serve_asset("debug-console.js")
        assert len(filter_instance._excluded_cache) > 0

        # Clear cache
        filter_instance.clear_cache()
        assert len(filter_instance._excluded_cache) == 0


class TestGlobalFilterInstance:
    """Test global filter instance management."""

    def test_get_production_filter_singleton(self):
        """Test global filter instance is singleton."""
        filter1 = get_production_filter()
        filter2 = get_production_filter()

        assert filter1 is filter2


class TestUtilityFunctions:
    """Test utility functions and information retrieval."""

    def test_get_excluded_patterns_production_mode(self):
        """Test pattern retrieval in production mode."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            patterns = get_excluded_patterns()

        expected_count = len(PRODUCTION_EXCLUDES) + len(DEVELOPMENT_ARTIFACTS) + len(TEST_PATTERNS)
        assert len(patterns) == expected_count

    def test_get_excluded_patterns_development_mode(self):
        """Test pattern retrieval in development mode."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "development"}):
            patterns = get_excluded_patterns()

        assert patterns == []

    def test_get_asset_exclusion_info(self):
        """Test asset exclusion information retrieval."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            info = get_asset_exclusion_info()

        assert "production_mode" in info
        assert "environment" in info
        assert "exclusion_patterns" in info
        assert "target_files" in info
        assert "estimated_savings" in info

        assert info["production_mode"] is True
        assert info["estimated_savings"]["javascript_heap_mb"] == 45
        assert len(info["target_files"]) == 3


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_is_debug_asset_when_invalid_path(self):
        """Test debug asset detection with invalid paths."""
        # Should not raise exceptions
        assert is_debug_asset("") is False
        assert is_debug_asset(" ") is False

    def test_should_exclude_asset_when_invalid_path(self):
        """Test asset exclusion with invalid paths."""
        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            # Should not exclude invalid paths
            assert should_exclude_asset("") is False
            assert should_exclude_asset(" ") is False

    def test_filter_asset_paths_when_mixed_types(self):
        """Test asset path filtering with mixed Path and string types."""
        asset_paths = ["app.js", Path("debug-console.js"), "utils.js", Path("settings-panel.js")]

        with patch.dict(os.environ, {"CALENDARBOT_ENV": "production"}):
            filtered = filter_asset_paths(asset_paths)

        # Should preserve original types but filter out debug assets
        assert "app.js" in filtered
        assert "utils.js" in filtered
        assert len(filtered) == 2


if __name__ == "__main__":
    pytest.main([__file__])
