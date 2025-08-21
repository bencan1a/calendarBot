"""Unit tests for the build configuration module."""

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


class TestProductionModeDetection:
    """Tests for production mode detection."""

    @pytest.mark.parametrize(
        ("env_value", "expected"),
        [
            ("production", True),
            ("prod", True),
            ("PRODUCTION", True),
            ("development", False),
            ("dev", False),
            ("debug", False),
            ("", True),  # Default to production
            ("invalid", True),  # Default to production
        ],
    )
    def test_is_production_mode_with_environment_variables(self, env_value, expected) -> None:
        """Test production mode detection with various environment values."""
        with patch.dict("os.environ", {"CALENDARBOT_ENV": env_value}, clear=False):
            assert is_production_mode() == expected

    def test_is_production_mode_without_environment_variable(self) -> None:
        """Test production mode detection without environment variable."""
        with patch.dict("os.environ", {}, clear=True):
            # Should default to production mode for safety
            assert is_production_mode() is True


class TestDebugAssetDetection:
    """Tests for debug asset detection."""

    @pytest.mark.parametrize(
        ("file_path", "expected"),
        [
            # Debug JavaScript patterns
            ("debug-settings.js", True),
            ("development-api.js", True),
            ("test-utils.js", True),
            ("mock-data.js", True),
            ("console-logger.js", True),
            ("debugger-panel.js", True),
            # Extension patterns
            ("app.debug.js", True),
            ("utils.dev.js", True),
            ("main-debug.js", True),
            ("api-dev.js", True),
            # Development artifacts
            ("app.js.map", True),
            ("bundle.map.js", True),
            ("main-sourcemap.js", True),
            # Test files
            ("component.test.js", True),
            ("service.spec.js", True),
            ("data.mock.js", True),
            ("test-helper.js", True),  # Must match TEST_PATTERNS
            ("test-setup.js", True),  # Must match TEST_PATTERNS
            # Production files (should not match)
            ("app.js", False),
            ("bundle.js", False),
            ("main.css", False),
            ("settings-panel.js", False),  # Explicitly not excluded
            ("settings-api.js", False),  # Explicitly not excluded
            ("gesture-handler.js", False),  # Explicitly not excluded
        ],
    )
    def test_is_debug_asset_with_various_files(self, file_path, expected) -> None:
        """Test debug asset detection with various file paths."""
        assert is_debug_asset(file_path) == expected

    def test_is_debug_asset_with_path_objects(self) -> None:
        """Test debug asset detection with Path objects."""
        debug_path = Path("static/js/debug-console.js")
        production_path = Path("static/js/app.js")

        assert is_debug_asset(debug_path) is True
        assert is_debug_asset(production_path) is False

    def test_is_debug_asset_with_complex_paths(self) -> None:
        """Test debug asset detection with complex file paths."""
        # Should only check filename, not full path
        assert is_debug_asset("/path/to/debug/app.js") is False
        assert is_debug_asset("/path/to/debug/debug-app.js") is True

    @patch("calendarbot.config.build.logger")
    def test_is_debug_asset_with_invalid_regex(self, mock_logger) -> None:
        """Test debug asset detection handles invalid regex gracefully."""
        # This should not happen in practice, but test error handling
        with patch("calendarbot.config.build.PRODUCTION_EXCLUDES", ["[invalid"]):
            result = is_debug_asset("test.js")
            # Should return False and log warning for invalid regex
            assert result is False
            mock_logger.warning.assert_called()


class TestAssetExclusion:
    """Tests for asset exclusion logic."""

    @patch("calendarbot.config.build.is_production_mode")
    def test_should_exclude_asset_in_development_mode(self, mock_prod_mode) -> None:
        """Test asset exclusion in development mode."""
        mock_prod_mode.return_value = False

        # In development, no assets should be excluded
        assert should_exclude_asset("debug-console.js") is False
        assert should_exclude_asset("app.js") is False

    @patch("calendarbot.config.build.is_production_mode")
    def test_should_exclude_asset_in_production_mode(self, mock_prod_mode) -> None:
        """Test asset exclusion in production mode."""
        mock_prod_mode.return_value = True

        # In production, debug assets should be excluded
        assert should_exclude_asset("debug-console.js") is True
        assert should_exclude_asset("app.js") is False


class TestExclusionPatterns:
    """Tests for exclusion pattern management."""

    @patch("calendarbot.config.build.is_production_mode")
    def test_get_excluded_patterns_in_development(self, mock_prod_mode) -> None:
        """Test getting exclusion patterns in development mode."""
        mock_prod_mode.return_value = False
        patterns = get_excluded_patterns()
        assert patterns == []

    @patch("calendarbot.config.build.is_production_mode")
    def test_get_excluded_patterns_in_production(self, mock_prod_mode) -> None:
        """Test getting exclusion patterns in production mode."""
        mock_prod_mode.return_value = True
        patterns = get_excluded_patterns()

        expected_length = len(PRODUCTION_EXCLUDES) + len(DEVELOPMENT_ARTIFACTS) + len(TEST_PATTERNS)
        assert len(patterns) == expected_length
        assert all(isinstance(pattern, str) for pattern in patterns)


class TestAssetPathFiltering:
    """Tests for asset path filtering."""

    @patch("calendarbot.config.build.is_production_mode")
    def test_filter_asset_paths_in_development(self, mock_prod_mode) -> None:
        """Test asset path filtering in development mode."""
        mock_prod_mode.return_value = False

        asset_paths = ["app.js", "debug-console.js", "test-utils.js", "bundle.js"]
        filtered = filter_asset_paths(asset_paths)

        # In development, all assets should be preserved
        assert filtered == asset_paths

    @patch("calendarbot.config.build.is_production_mode")
    @patch("calendarbot.config.build.logger")
    def test_filter_asset_paths_in_production(self, mock_logger, mock_prod_mode) -> None:
        """Test asset path filtering in production mode."""
        mock_prod_mode.return_value = True

        asset_paths = ["app.js", "debug-console.js", "test-utils.js", "bundle.js"]
        filtered = filter_asset_paths(asset_paths)

        # Debug assets should be excluded
        expected = ["app.js", "bundle.js"]
        assert filtered == expected

        # Should log exclusion info
        mock_logger.info.assert_called_with("Production mode: excluded 2 debug assets")


class TestAssetExclusionInfo:
    """Tests for asset exclusion information."""

    @patch("calendarbot.config.build.is_production_mode")
    @patch.dict("os.environ", {"CALENDARBOT_ENV": "production"})
    def test_get_asset_exclusion_info_structure(self, mock_prod_mode) -> None:
        """Test asset exclusion info returns proper structure."""
        mock_prod_mode.return_value = True

        info = get_asset_exclusion_info()

        # Check required keys
        assert "production_mode" in info
        assert "environment" in info
        assert "exclusion_patterns" in info
        assert "target_files" in info
        assert "estimated_savings" in info

        # Check specific values
        assert info["production_mode"] is True
        assert info["environment"]["CALENDARBOT_ENV"] == "production"
        assert isinstance(info["exclusion_patterns"]["total_patterns"], int)
        assert isinstance(info["target_files"], list)
        assert "javascript_heap_mb" in info["estimated_savings"]


class TestAssetPathValidation:
    """Tests for asset path validation."""

    @pytest.mark.parametrize(
        "valid_path",
        [
            "static/js/app.js",
            "css/styles.css",
            "images/logo.png",
            "js/components/button.js",
            "relative/path/file.js",
        ],
    )
    def test_validate_asset_path_with_valid_paths(self, valid_path) -> None:
        """Test asset path validation with valid paths."""
        assert validate_asset_path(valid_path) is True

    @pytest.mark.parametrize(
        "invalid_path",
        [
            "../../../etc/passwd",  # Path traversal
            "/absolute/path/file.js",  # Absolute path
            "C:\\Windows\\system32\\file.js",  # Windows absolute path
            "",  # Empty path
            None,  # None path
        ],
    )
    def test_validate_asset_path_with_invalid_paths(self, invalid_path) -> None:
        """Test asset path validation with invalid paths."""
        assert validate_asset_path(invalid_path) is False

    @patch("calendarbot.config.build.logger")
    def test_validate_asset_path_logs_warnings(self, mock_logger) -> None:
        """Test asset path validation logs appropriate warnings."""
        validate_asset_path("../malicious.js")
        mock_logger.warning.assert_called_with(
            "Path traversal detected in asset path: ../malicious.js"
        )

        validate_asset_path("/absolute/path.js")
        mock_logger.warning.assert_called_with(
            "Absolute path not allowed for assets: /absolute/path.js"
        )


class TestProductionAssetFilter:
    """Tests for the ProductionAssetFilter class."""

    @patch("calendarbot.config.build.is_production_mode")
    def test_filter_initialization_development_mode(self, mock_prod_mode) -> None:
        """Test filter initialization in development mode."""
        mock_prod_mode.return_value = False

        filter_instance = ProductionAssetFilter()

        assert filter_instance.production_mode is False
        assert filter_instance.exclusion_patterns == []

    @patch("calendarbot.config.build.is_production_mode")
    def test_filter_initialization_production_mode(self, mock_prod_mode) -> None:
        """Test filter initialization in production mode."""
        mock_prod_mode.return_value = True

        filter_instance = ProductionAssetFilter()

        assert filter_instance.production_mode is True
        assert len(filter_instance.exclusion_patterns) > 0

    @patch("calendarbot.config.build.is_production_mode")
    def test_should_serve_asset_in_development(self, mock_prod_mode) -> None:
        """Test should_serve_asset in development mode."""
        mock_prod_mode.return_value = False
        filter_instance = ProductionAssetFilter()

        # All valid assets should be served in development
        assert filter_instance.should_serve_asset("debug-console.js") is True
        assert filter_instance.should_serve_asset("app.js") is True

    @patch("calendarbot.config.build.is_production_mode")
    def test_should_serve_asset_in_production(self, mock_prod_mode) -> None:
        """Test should_serve_asset in production mode."""
        mock_prod_mode.return_value = True
        filter_instance = ProductionAssetFilter()

        # Debug assets should not be served in production
        assert filter_instance.should_serve_asset("debug-console.js") is False
        assert filter_instance.should_serve_asset("app.js") is True

    @patch("calendarbot.config.build.is_production_mode")
    def test_should_serve_asset_with_invalid_paths(self, mock_prod_mode) -> None:
        """Test should_serve_asset with invalid paths."""
        mock_prod_mode.return_value = True
        filter_instance = ProductionAssetFilter()

        # Invalid paths should not be served
        assert filter_instance.should_serve_asset("../malicious.js") is False
        assert filter_instance.should_serve_asset("/absolute/path.js") is False

    @patch("calendarbot.config.build.is_production_mode")
    def test_exclusion_cache_behavior(self, mock_prod_mode) -> None:
        """Test exclusion cache behavior."""
        mock_prod_mode.return_value = True
        filter_instance = ProductionAssetFilter()

        # First call should cache result
        result1 = filter_instance.should_serve_asset("debug-console.js")
        assert result1 is False
        assert "debug-console.js" in filter_instance._excluded_cache

        # Second call should use cache
        result2 = filter_instance.should_serve_asset("debug-console.js")
        assert result2 is False

    @patch("calendarbot.config.build.is_production_mode")
    def test_get_serving_decision(self, mock_prod_mode) -> None:
        """Test get_serving_decision method."""
        mock_prod_mode.return_value = True
        filter_instance = ProductionAssetFilter()

        decision = filter_instance.get_serving_decision("debug-console.js")

        assert decision["file_path"] == "debug-console.js"
        assert decision["should_serve"] is False
        assert decision["is_debug_asset"] is True
        assert decision["production_mode"] is True
        assert decision["excluded_reason"] == "debug_asset_in_production"

    @patch("calendarbot.config.build.is_production_mode")
    def test_clear_cache(self, mock_prod_mode) -> None:
        """Test cache clearing functionality."""
        mock_prod_mode.return_value = True
        filter_instance = ProductionAssetFilter()

        # Add something to cache
        filter_instance.should_serve_asset("debug-console.js")
        assert len(filter_instance._excluded_cache) > 0

        # Clear cache
        filter_instance.clear_cache()
        assert len(filter_instance._excluded_cache) == 0


class TestGlobalFilter:
    """Tests for global filter management."""

    def test_get_production_filter_singleton(self) -> None:
        """Test that get_production_filter returns singleton instance."""
        # Clear global state first
        import calendarbot.config.build

        calendarbot.config.build._global_filter = None

        filter1 = get_production_filter()
        filter2 = get_production_filter()

        assert filter1 is filter2
        assert isinstance(filter1, ProductionAssetFilter)
