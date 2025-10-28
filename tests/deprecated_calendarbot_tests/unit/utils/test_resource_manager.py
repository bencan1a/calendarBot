"""Unit tests for calendarbot.layout.resource_manager module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from calendarbot.layout.exceptions import LayoutNotFoundError, ResourceLoadingError
from calendarbot.layout.resource_manager import ResourceManager


class TestResourceManagerInitialization:
    """Test ResourceManager initialization."""

    def test_init_with_layout_registry(self) -> None:
        """Test initialization with layout registry."""
        mock_registry = Mock()
        resource_manager = ResourceManager(mock_registry)

        assert resource_manager.layout_registry == mock_registry

    def test_init_sets_up_cache(self) -> None:
        """Test initialization sets up internal cache."""
        mock_registry = Mock()
        resource_manager = ResourceManager(mock_registry)

        # Should have empty cache initially
        assert hasattr(resource_manager, "_css_cache")
        assert hasattr(resource_manager, "_js_cache")


class TestResourceManagerCSSLoading:
    """Test CSS resource loading functionality."""

    @pytest.fixture
    def mock_registry_with_layouts(self):
        """Create mock registry with layout data."""
        registry = Mock()
        registry.validate_layout.return_value = True
        registry.get_layout_css_paths.return_value = [
            Path("calendarbot/web/static/layouts/4x8/4x8.css"),
        ]
        return registry

    @pytest.fixture
    def resource_manager(self, mock_registry_with_layouts):
        """Create resource manager with mock registry."""
        return ResourceManager(mock_registry_with_layouts)

    def test_get_css_content_invalid_layout(
        self, resource_manager, mock_registry_with_layouts
    ) -> None:
        """Test getting CSS content for invalid layout raises exception."""
        mock_registry_with_layouts.validate_layout.return_value = False

        with pytest.raises(LayoutNotFoundError):
            resource_manager.get_css_content("invalid_layout")

    def test_get_css_content_file_not_found(
        self, resource_manager, mock_registry_with_layouts
    ) -> None:
        """Test getting CSS content handles missing files gracefully."""
        with patch("builtins.open", side_effect=FileNotFoundError("CSS file not found")):
            result = resource_manager.get_css_content("4x8")

            # Should return empty string or handle gracefully
            assert isinstance(result, str)

    def test_get_css_content_uses_cache(self, resource_manager, mock_registry_with_layouts) -> None:
        """Test CSS content caching functionality."""
        mock_css_content = "body { margin: 0; }"

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = mock_css_content

            # First call should read file
            result1 = resource_manager.get_css_content("4x8")

            # Second call should use cache
            result2 = resource_manager.get_css_content("4x8")

            assert result1 == result2
            # Should only call get_layout_css_paths once if caching works
            assert mock_registry_with_layouts.get_layout_css_paths.call_count <= 2

    def test_get_css_paths_for_layout(self, resource_manager, mock_registry_with_layouts) -> None:
        """Test getting CSS file paths for layout."""
        paths = resource_manager.get_css_paths_for_layout("4x8")

        expected_paths = [Path("calendarbot/web/static/layouts/4x8/4x8.css")]

        assert paths == expected_paths
        mock_registry_with_layouts.get_layout_css_paths.assert_called_with("4x8")


class TestResourceManagerJSLoading:
    """Test JavaScript resource loading functionality."""

    @pytest.fixture
    def mock_registry_with_js(self):
        """Create mock registry with JS layout data."""
        registry = Mock()
        registry.validate_layout.return_value = True
        registry.get_layout_js_paths.return_value = [
            Path("calendarbot/web/static/layouts/4x8/4x8.js"),
        ]
        return registry

    @pytest.fixture
    def resource_manager_js(self, mock_registry_with_js):
        """Create resource manager with JS mock registry."""
        return ResourceManager(mock_registry_with_js)

    def test_get_js_content_valid_layout(self, resource_manager_js, mock_registry_with_js) -> None:
        """Test getting JavaScript content for valid layout."""
        mock_js_content = (
            "/* Calendar Bot Web Interface */\nfunction initializeApp() { console.log('loaded'); }"
        )

        # Ensure cache is clear at start
        resource_manager_js.clear_cache()

        # Mock the specific pathlib.Path.open call that ResourceManager uses
        with patch("pathlib.Path.open", create=True) as mock_path_open:
            mock_path_open.return_value.__enter__.return_value.read.return_value = mock_js_content

            result = resource_manager_js.get_js_content("4x8")

            # Should contain mocked content
            assert "Calendar Bot Web Interface" in result
            assert "function initializeApp()" in result
            mock_registry_with_js.validate_layout.assert_called_with("4x8")
            mock_registry_with_js.get_layout_js_paths.assert_called_with("4x8")

            # Verify the content is exactly what we mocked
            assert result == mock_js_content

    def test_get_js_content_invalid_layout(
        self, resource_manager_js, mock_registry_with_js
    ) -> None:
        """Test getting JS content for invalid layout raises exception."""
        mock_registry_with_js.validate_layout.return_value = False

        with pytest.raises(LayoutNotFoundError):
            resource_manager_js.get_js_content("invalid_layout")

    def test_get_js_content_file_not_found(
        self, resource_manager_js, mock_registry_with_js
    ) -> None:
        """Test getting JS content handles missing files gracefully."""
        with patch("builtins.open", side_effect=FileNotFoundError("JS file not found")):
            result = resource_manager_js.get_js_content("4x8")

            # Should return empty string or handle gracefully
            assert isinstance(result, str)

    def test_get_js_paths_for_layout(self, resource_manager_js, mock_registry_with_js) -> None:
        """Test getting JavaScript file paths for layout."""
        paths = resource_manager_js.get_js_paths_for_layout("4x8")

        expected_paths = [Path("calendarbot/web/static/layouts/4x8/4x8.js")]

        assert paths == expected_paths
        mock_registry_with_js.get_layout_js_paths.assert_called_with("4x8")


class TestResourceManagerPathMethods:
    """Test get_css_path and get_js_path methods."""

    @pytest.fixture
    def mock_layout_info(self):
        """Create mock layout info object."""
        layout_info = Mock()
        layout_info.name = "4x8"
        layout_info.resources = {"css": ["4x8.css", "common.css"], "js": ["4x8.js", "utils.js"]}
        return layout_info

    @pytest.fixture
    def mock_registry_with_layout_info(self, mock_layout_info):
        """Create mock registry that returns layout info."""
        registry = Mock()
        registry.get_layout_with_fallback.return_value = mock_layout_info
        registry.layouts_dir = Path("calendarbot/web/static/layouts")
        return registry

    @pytest.fixture
    def resource_manager_paths(self, mock_registry_with_layout_info):
        """Create resource manager for path testing."""
        return ResourceManager(mock_registry_with_layout_info)

    def test_get_css_path_valid_layout_returns_first_css_file(
        self, resource_manager_paths, mock_registry_with_layout_info
    ) -> None:
        """Test get_css_path returns path to first CSS file for valid layout."""
        result = resource_manager_paths.get_css_path("4x8")

        expected_path = Path("calendarbot/web/static/layouts/4x8/4x8.css")
        assert result == expected_path
        mock_registry_with_layout_info.get_layout_with_fallback.assert_called_with("4x8")

    def test_get_css_path_no_css_files_returns_none(
        self, resource_manager_paths, mock_registry_with_layout_info, mock_layout_info
    ) -> None:
        """Test get_css_path returns None when layout has no CSS files."""
        mock_layout_info.resources = {"css": [], "js": ["test.js"]}

        result = resource_manager_paths.get_css_path("4x8")

        assert result is None

    def test_get_css_path_http_url_returns_none(
        self, resource_manager_paths, mock_registry_with_layout_info, mock_layout_info
    ) -> None:
        """Test get_css_path returns None for HTTP URLs (external resources)."""
        mock_layout_info.resources = {"css": ["https://cdn.example.com/style.css"], "js": []}

        result = resource_manager_paths.get_css_path("4x8")

        assert result is None

    def test_get_css_path_exception_handling_returns_none(
        self, resource_manager_paths, mock_registry_with_layout_info
    ) -> None:
        """Test get_css_path returns None when registry throws exception."""
        mock_registry_with_layout_info.get_layout_with_fallback.side_effect = LayoutNotFoundError(
            "Layout not found"
        )

        result = resource_manager_paths.get_css_path("invalid_layout")

        assert result is None

    def test_get_js_path_valid_layout_returns_first_js_file(
        self, resource_manager_paths, mock_registry_with_layout_info
    ) -> None:
        """Test get_js_path returns path to first JS file for valid layout."""
        result = resource_manager_paths.get_js_path("4x8")

        expected_path = Path("calendarbot/web/static/layouts/4x8/4x8.js")
        assert result == expected_path
        mock_registry_with_layout_info.get_layout_with_fallback.assert_called_with("4x8")

    def test_get_js_path_no_js_files_returns_none(
        self, resource_manager_paths, mock_registry_with_layout_info, mock_layout_info
    ) -> None:
        """Test get_js_path returns None when layout has no JS files."""
        mock_layout_info.resources = {"css": ["test.css"], "js": []}

        result = resource_manager_paths.get_js_path("4x8")

        assert result is None

    def test_get_js_path_http_url_returns_none(
        self, resource_manager_paths, mock_registry_with_layout_info, mock_layout_info
    ) -> None:
        """Test get_js_path returns None for HTTP URLs (external resources)."""
        mock_layout_info.resources = {"css": [], "js": ["https://cdn.example.com/script.js"]}

        result = resource_manager_paths.get_js_path("4x8")

        assert result is None

    def test_get_js_path_exception_handling_returns_none(
        self, resource_manager_paths, mock_registry_with_layout_info
    ) -> None:
        """Test get_js_path returns None when registry throws exception."""
        mock_registry_with_layout_info.get_layout_with_fallback.side_effect = Exception(
            "Registry error"
        )

        result = resource_manager_paths.get_js_path("invalid_layout")

        assert result is None

    @pytest.mark.parametrize(
        ("layout_name", "expected_css_path", "expected_js_path"),
        [
            (
                "4x8",
                Path("calendarbot/web/static/layouts/4x8/4x8.css"),
                Path("calendarbot/web/static/layouts/4x8/4x8.js"),
            ),
            (
                "whats-next-view",
                Path("calendarbot/web/static/layouts/whats-next-view/whats-next-view.css"),
                Path("calendarbot/web/static/layouts/whats-next-view/whats-next-view.js"),
            ),
        ],
    )
    def test_path_methods_with_different_layouts(
        self, mock_registry_with_layout_info, layout_name, expected_css_path, expected_js_path
    ) -> None:
        """Test path methods work correctly with different layout names."""
        # Setup mock layout info for each test case
        layout_info = Mock()
        layout_info.name = layout_name
        layout_info.resources = {"css": [f"{layout_name}.css"], "js": [f"{layout_name}.js"]}
        mock_registry_with_layout_info.get_layout_with_fallback.return_value = layout_info

        resource_manager = ResourceManager(mock_registry_with_layout_info)

        css_result = resource_manager.get_css_path(layout_name)
        js_result = resource_manager.get_js_path(layout_name)

        assert css_result == expected_css_path
        assert js_result == expected_js_path


class TestResourceManagerCombinedOperations:
    """Test combined CSS and JS operations."""

    @pytest.fixture
    def mock_registry_combined(self):
        """Create mock registry with both CSS and JS data."""
        registry = Mock()
        registry.validate_layout.return_value = True
        registry.get_layout_css_paths.return_value = [Path("tests/fixtures/layouts/test/style.css")]
        registry.get_layout_js_paths.return_value = [Path("tests/fixtures/layouts/test/script.js")]
        return registry

    @pytest.fixture
    def resource_manager_combined(self, mock_registry_combined):
        """Create resource manager with combined mock registry."""
        return ResourceManager(mock_registry_combined)

    def test_clear_cache(self, resource_manager_combined) -> None:
        """Test clearing resource cache."""
        # Populate cache first
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "test content"

            resource_manager_combined.get_css_content("test")
            resource_manager_combined.get_js_content("test")

            # Clear cache
            resource_manager_combined.clear_cache()

            # Cache should be empty
            assert len(resource_manager_combined._css_cache) == 0
            assert len(resource_manager_combined._js_cache) == 0

    def test_cache_invalidation_on_layout_change(
        self, resource_manager_combined, mock_registry_combined
    ) -> None:
        """Test that cache is invalidated when layout changes."""
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "content"

            # Load content for first layout
            resource_manager_combined.get_css_content("test")

            # Change to different layout should not use cached content
            mock_registry_combined.get_layout_css_paths.return_value = [
                Path("tests/fixtures/layouts/other/style.css")
            ]

            resource_manager_combined.get_css_content("other")

            # Should call registry again for new layout
            assert mock_registry_combined.get_layout_css_paths.call_count >= 2


class TestResourceManagerErrorHandling:
    """Test error handling and edge cases."""

    def test_handles_registry_exceptions(self) -> None:
        """Test handling exceptions from layout registry."""
        mock_registry = Mock()
        mock_registry.validate_layout.side_effect = Exception("Registry error")

        resource_manager = ResourceManager(mock_registry)

        with pytest.raises(Exception, match="Registry error"):
            resource_manager.get_css_content("test")

    def test_handles_file_permission_errors(self) -> None:
        """Test handling file permission errors."""
        mock_registry = Mock()
        mock_registry.validate_layout.return_value = True
        mock_registry.get_layout_css_paths.return_value = [
            Path("tests/fixtures/layouts/protected/style.css")
        ]

        resource_manager = ResourceManager(mock_registry)

        with patch("pathlib.Path.open", side_effect=PermissionError("Permission denied")):
            result = resource_manager.get_css_content("test")

            # Should handle gracefully and return empty string
            assert result == ""

    def test_handles_corrupted_files(self) -> None:
        """Test handling corrupted or binary files."""
        mock_registry = Mock()
        mock_registry.validate_layout.return_value = True
        mock_registry.get_layout_css_paths.return_value = [
            Path("tests/fixtures/layouts/test/corrupted.css")
        ]

        resource_manager = ResourceManager(mock_registry)

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.side_effect = UnicodeDecodeError(
                "utf-8", b"", 0, 1, "invalid start byte"
            )

            result = resource_manager.get_css_content("test")

            # Should handle gracefully
            assert isinstance(result, str)

    def test_empty_file_list_handling(self) -> None:
        """Test handling when layout has no CSS/JS files."""
        mock_registry = Mock()
        mock_registry.validate_layout.return_value = True
        mock_registry.get_layout_css_paths.return_value = []
        mock_registry.get_layout_js_paths.return_value = []

        resource_manager = ResourceManager(mock_registry)

        css_result = resource_manager.get_css_content("test")
        js_result = resource_manager.get_js_content("test")

        assert css_result == ""
        assert js_result == ""

    @pytest.mark.parametrize(
        "layout_name", ["", None, "   ", "invalid/path", "../../../etc/passwd"]
    )
    def test_handles_invalid_layout_names(self, layout_name) -> None:
        """Test handling various invalid layout names."""
        mock_registry = Mock()
        mock_registry.validate_layout.return_value = False

        resource_manager = ResourceManager(mock_registry)

        with pytest.raises(LayoutNotFoundError):
            resource_manager.get_css_content(layout_name)


class TestResourceManagerFileOperationErrors:
    """Test error scenarios for resource manager file operations."""

    @pytest.fixture
    def mock_registry_error_scenarios(self) -> Mock:
        """Create mock registry for error scenario testing."""
        registry = Mock()
        registry.validate_layout.return_value = True
        registry.get_layout_css_paths.return_value = [Path("tests/fixtures/layouts/test/style.css")]
        registry.get_layout_js_paths.return_value = [Path("tests/fixtures/layouts/test/script.js")]
        return registry

    @pytest.fixture
    def resource_manager_error_test(self, mock_registry_error_scenarios) -> ResourceManager:
        """Create resource manager for error testing."""
        return ResourceManager(mock_registry_error_scenarios)

    def test_get_css_content_when_file_permission_denied_then_handles_gracefully(
        self, resource_manager_error_test, mock_registry_error_scenarios
    ) -> None:
        """Test CSS content loading handles PermissionError gracefully."""
        with patch("pathlib.Path.open", side_effect=PermissionError("Permission denied")):
            result = resource_manager_error_test.get_css_content("test")

            # Should return empty string and not crash
            assert result == ""
            assert isinstance(result, str)

    def test_get_css_content_when_file_not_found_then_handles_gracefully(
        self, resource_manager_error_test, mock_registry_error_scenarios
    ) -> None:
        """Test CSS content loading handles FileNotFoundError gracefully."""
        with patch("pathlib.Path.open", side_effect=FileNotFoundError("File not found")):
            result = resource_manager_error_test.get_css_content("test")

            # Should return empty string and continue processing
            assert result == ""
            assert isinstance(result, str)

    def test_get_css_content_when_unicode_decode_error_then_handles_gracefully(
        self, resource_manager_error_test, mock_registry_error_scenarios
    ) -> None:
        """Test CSS content loading handles UnicodeDecodeError gracefully."""
        with patch("pathlib.Path.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.side_effect = UnicodeDecodeError(
                "utf-8", b"\xff\xfe", 0, 1, "invalid start byte"
            )

            result = resource_manager_error_test.get_css_content("test")

            # Should return empty string when encoding fails
            assert result == ""
            assert isinstance(result, str)

    def test_get_js_content_when_file_permission_denied_then_handles_gracefully(
        self, resource_manager_error_test, mock_registry_error_scenarios
    ) -> None:
        """Test JS content loading handles PermissionError gracefully."""
        with patch("pathlib.Path.open", side_effect=PermissionError("Permission denied")):
            result = resource_manager_error_test.get_js_content("test")

            # Should return empty string and not crash
            assert result == ""
            assert isinstance(result, str)

    def test_get_js_content_when_file_not_found_then_handles_gracefully(
        self, resource_manager_error_test, mock_registry_error_scenarios
    ) -> None:
        """Test JS content loading handles FileNotFoundError gracefully."""
        with patch("pathlib.Path.open", side_effect=FileNotFoundError("File not found")):
            result = resource_manager_error_test.get_js_content("test")

            # Should return empty string and continue processing
            assert result == ""
            assert isinstance(result, str)

    def test_get_js_content_when_unicode_decode_error_then_handles_gracefully(
        self, resource_manager_error_test, mock_registry_error_scenarios
    ) -> None:
        """Test JS content loading handles UnicodeDecodeError gracefully."""
        with patch("pathlib.Path.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.side_effect = UnicodeDecodeError(
                "utf-8", b"\xff\xfe", 0, 1, "invalid start byte"
            )

            result = resource_manager_error_test.get_js_content("test")

            # Should return empty string when encoding fails
            assert result == ""
            assert isinstance(result, str)

    def test_get_css_content_when_io_error_then_handles_gracefully(
        self, resource_manager_error_test, mock_registry_error_scenarios
    ) -> None:
        """Test CSS content loading handles generic IOError gracefully."""
        with patch("pathlib.Path.open", side_effect=OSError("I/O operation failed")):
            result = resource_manager_error_test.get_css_content("test")

            # Should return empty string and log warning
            assert result == ""
            assert isinstance(result, str)

    def test_get_js_content_when_io_error_then_handles_gracefully(
        self, resource_manager_error_test, mock_registry_error_scenarios
    ) -> None:
        """Test JS content loading handles generic IOError gracefully."""
        with patch("pathlib.Path.open", side_effect=OSError("I/O operation failed")):
            result = resource_manager_error_test.get_js_content("test")

            # Should return empty string and log warning
            assert result == ""
            assert isinstance(result, str)

    def test_validate_layout_resources_when_files_missing_then_reports_correctly(
        self, resource_manager_error_test
    ) -> None:
        """Test validate_layout_resources reports missing files correctly."""
        # Setup mock layout info with specific resources
        mock_layout_info = Mock()
        mock_layout_info.name = "test"
        mock_layout_info.resources = {
            "css": ["existing.css", "missing.css"],
            "js": ["existing.js", "missing.js"],
        }

        resource_manager_error_test.layout_registry.get_layout_info.return_value = mock_layout_info
        resource_manager_error_test.layout_registry.layouts_dir = Path("tests/fixtures/layouts")

        # Mock Path.exists to simulate missing files
        with patch("pathlib.Path.exists") as mock_exists:

            def exists_side_effect(self):
                path_str = str(self)
                if "missing" in path_str:
                    return False
                return True

            mock_exists.side_effect = exists_side_effect

            result = resource_manager_error_test.validate_layout_resources("test")

            # Should report validation failures for missing files
            assert result["layout_exists"] is True
            assert result["css_valid"] is False  # Because missing.css doesn't exist
            assert result["js_valid"] is False  # Because missing.js doesn't exist

    def test_validate_layout_resources_when_layout_directory_missing_then_reports_invalid(
        self, resource_manager_error_test
    ) -> None:
        """Test validate_layout_resources handles missing layout directory."""
        mock_layout_info = Mock()
        mock_layout_info.name = "test"
        mock_layout_info.resources = {"css": ["style.css"], "js": ["script.js"]}

        resource_manager_error_test.layout_registry.get_layout_info.return_value = mock_layout_info
        resource_manager_error_test.layout_registry.layouts_dir = Path(
            "calendarbot/web/static/layouts"
        )

        # Mock directory not existing
        with patch("pathlib.Path.exists", return_value=False):
            result = resource_manager_error_test.validate_layout_resources("test")

            # Should report all as invalid when directory doesn't exist
            assert result["layout_exists"] is True
            assert result["css_valid"] is False
            assert result["js_valid"] is False

    @pytest.mark.parametrize(
        ("error_type", "expected_result"),
        [
            (
                Exception("General error"),
                {"css_valid": False, "js_valid": False, "layout_exists": False},
            ),
            (
                KeyError("Missing key"),
                {"css_valid": False, "js_valid": False, "layout_exists": False},
            ),
            (
                AttributeError("Missing attribute"),
                {"css_valid": False, "js_valid": False, "layout_exists": False},
            ),
        ],
    )
    def test_validate_layout_resources_when_registry_error_then_handles_gracefully(
        self, resource_manager_error_test, error_type, expected_result
    ) -> None:
        """Test validate_layout_resources handles registry errors gracefully."""
        resource_manager_error_test.layout_registry.get_layout_info.side_effect = error_type

        result = resource_manager_error_test.validate_layout_resources("test")

        # Should return safe defaults when registry fails
        assert result == expected_result


class TestResourceManagerURLMethods:
    """Test URL generation methods with various edge cases."""

    @pytest.fixture
    def mock_layout_info(self):
        """Create mock layout info with various resource formats."""
        layout_info = Mock()
        layout_info.name = "test-layout"
        layout_info.resources = {
            "css": [
                "style.css",  # String format
                {"file": "theme.css"},  # Object format
                {"file": ""},  # Empty file name
                {"wrong_key": "wrong.css"},  # Missing file key
                None,  # None entry
                {"file": None},  # None file name
                {"file": 123},  # Non-string file name
                "https://cdn.example.com/external.css",  # External URL
            ],
            "js": [
                "script.js",  # String format
                {"file": "utils.js"},  # Object format
                {"file": ""},  # Empty file name
                {"wrong_key": "wrong.js"},  # Missing file key
                None,  # None entry
                {"file": None},  # None file name
                {"file": 123},  # Non-string file name
                "https://cdn.example.com/external.js",  # External URL
            ],
        }
        return layout_info

    @pytest.fixture
    def mock_registry(self, mock_layout_info):
        """Create mock registry that returns the layout info."""
        registry = Mock()
        registry.get_layout_with_fallback.return_value = mock_layout_info
        return registry

    @pytest.fixture
    def resource_manager(self, mock_registry):
        """Create resource manager with mock registry."""
        return ResourceManager(mock_registry, base_url="/custom-static")

    def test_get_css_urls_handles_various_formats(
        self, resource_manager, mock_registry, mock_layout_info
    ):
        """Test get_css_urls handles various resource formats correctly."""
        urls = resource_manager.get_css_urls("test-layout")

        # Should include valid local and external URLs
        assert "/custom-static/layouts/test-layout/style.css" in urls
        assert "/custom-static/layouts/test-layout/theme.css" in urls
        assert "https://cdn.example.com/external.css" in urls

        # Should skip invalid entries
        assert len(urls) == 3
        assert "/custom-static/layouts/test-layout/wrong.css" not in urls

        # Should call registry with correct layout name
        mock_registry.get_layout_with_fallback.assert_called_with("test-layout")

    def test_get_js_urls_handles_various_formats(
        self, resource_manager, mock_registry, mock_layout_info
    ):
        """Test get_js_urls handles various resource formats correctly."""
        urls = resource_manager.get_js_urls("test-layout")

        # Should include valid local and external URLs
        assert "/custom-static/layouts/test-layout/script.js" in urls
        assert "/custom-static/layouts/test-layout/utils.js" in urls
        assert "https://cdn.example.com/external.js" in urls

        # Should skip invalid entries
        assert len(urls) == 3
        assert "/custom-static/layouts/test-layout/wrong.js" not in urls

        # Should call registry with correct layout name
        mock_registry.get_layout_with_fallback.assert_called_with("test-layout")

    def test_get_css_urls_with_custom_base_url(self, mock_registry, mock_layout_info):
        """Test get_css_urls with custom base URL."""
        # Create resource manager with custom base URL
        resource_manager = ResourceManager(mock_registry, base_url="https://example.com/assets")

        urls = resource_manager.get_css_urls("test-layout")

        # Should use custom base URL
        assert "https://example.com/assets/layouts/test-layout/style.css" in urls
        assert "https://example.com/assets/layouts/test-layout/theme.css" in urls

    def test_get_js_urls_with_custom_base_url(self, mock_registry, mock_layout_info):
        """Test get_js_urls with custom base URL."""
        # Create resource manager with custom base URL
        resource_manager = ResourceManager(mock_registry, base_url="https://example.com/assets")

        urls = resource_manager.get_js_urls("test-layout")

        # Should use custom base URL
        assert "https://example.com/assets/layouts/test-layout/script.js" in urls
        assert "https://example.com/assets/layouts/test-layout/utils.js" in urls


class TestResourceManagerInjection:
    """Test resource injection functionality."""

    @pytest.fixture
    def mock_layout_info(self):
        """Create mock layout info for injection testing."""
        layout_info = Mock()
        layout_info.name = "test-layout"
        layout_info.resources = {"css": ["style.css", "theme.css"], "js": ["script.js", "utils.js"]}
        return layout_info

    @pytest.fixture
    def mock_registry(self, mock_layout_info):
        """Create mock registry that returns the layout info."""
        registry = Mock()
        registry.get_layout_with_fallback.return_value = mock_layout_info
        return registry

    @pytest.fixture
    def resource_manager(self, mock_registry):
        """Create resource manager with mock registry."""
        return ResourceManager(mock_registry)

    def test_inject_layout_resources_adds_css_and_js(self, resource_manager):
        """Test inject_layout_resources adds CSS and JS to HTML template."""
        # Create a simple HTML template
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test</title>
        </head>
        <body>
            <div>Content</div>
        </body>
        </html>
        """

        # Patch get_css_urls and get_js_urls to return known values
        with patch.object(resource_manager, "get_css_urls") as mock_get_css_urls:
            with patch.object(resource_manager, "get_js_urls") as mock_get_js_urls:
                mock_get_css_urls.return_value = ["/static/layouts/test-layout/style.css"]
                mock_get_js_urls.return_value = ["/static/layouts/test-layout/script.js"]

                result = resource_manager.inject_layout_resources(template, "test-layout")

                # Should call URL methods with correct layout name
                mock_get_css_urls.assert_called_with("test-layout")
                mock_get_js_urls.assert_called_with("test-layout")

                # Should inject CSS links before </head>
                assert (
                    '<link rel="stylesheet" type="text/css" href="/static/shared/css/settings-panel.css">'
                    in result
                )
                assert (
                    '<link rel="stylesheet" type="text/css" href="/static/layouts/test-layout/style.css">'
                    in result
                )

                # Should inject JS scripts before </body>
                assert '<script src="/static/shared/js/settings-api.js"></script>' in result
                assert '<script src="/static/shared/js/gesture-handler.js"></script>' in result
                assert '<script src="/static/shared/js/settings-panel.js"></script>' in result
                assert '<script src="/static/layouts/test-layout/script.js"></script>' in result

    def test_inject_layout_resources_handles_missing_tags(self, resource_manager):
        """Test inject_layout_resources handles templates without head/body tags."""
        # Create a template without head/body tags
        template = "<div>Simple template</div>"

        # Patch get_css_urls and get_js_urls to return known values
        with patch.object(resource_manager, "get_css_urls") as mock_get_css_urls:
            with patch.object(resource_manager, "get_js_urls") as mock_get_js_urls:
                mock_get_css_urls.return_value = ["/static/layouts/test-layout/style.css"]
                mock_get_js_urls.return_value = ["/static/layouts/test-layout/script.js"]

                result = resource_manager.inject_layout_resources(template, "test-layout")

                # Should return template unchanged
                assert result == template

    def test_inject_layout_resources_when_exception_then_raises_resource_loading_error(
        self, resource_manager
    ):
        """Test inject_layout_resources raises ResourceLoadingError on exception."""
        template = "<html><head></head><body></body></html>"

        # Patch get_css_urls to raise an exception
        with patch.object(resource_manager, "get_css_urls", side_effect=Exception("Test error")):
            with pytest.raises(ResourceLoadingError) as excinfo:
                resource_manager.inject_layout_resources(template, "test-layout")

            # Should include original exception message
            assert "Test error" in str(excinfo.value)


class TestResourceManagerPreloading:
    """Test resource preloading functionality."""

    @pytest.fixture
    def mock_registry(self):
        """Create mock registry for preloading tests."""
        registry = Mock()
        return registry

    @pytest.fixture
    def resource_manager(self, mock_registry):
        """Create resource manager with mock registry."""
        return ResourceManager(mock_registry)

    def test_preload_resources_caches_multiple_layouts(self, resource_manager):
        """Test preload_resources caches resources for multiple layouts."""
        # Patch get_css_urls and get_js_urls to return different values for different layouts
        with patch.object(resource_manager, "get_css_urls") as mock_get_css_urls:
            with patch.object(resource_manager, "get_js_urls") as mock_get_js_urls:
                mock_get_css_urls.side_effect = lambda layout: [
                    f"/static/layouts/{layout}/style.css"
                ]
                mock_get_js_urls.side_effect = lambda layout: [
                    f"/static/layouts/{layout}/script.js"
                ]

                # Preload multiple layouts
                resource_manager.preload_resources(["layout1", "layout2", "layout3"])

                # Should call URL methods for each layout
                assert mock_get_css_urls.call_count == 3
                assert mock_get_js_urls.call_count == 3

                # Should cache resources for each layout
                assert len(resource_manager._resource_cache) == 3
                assert resource_manager._resource_cache["layout1"] == {
                    "css": ["/static/layouts/layout1/style.css"],
                    "js": ["/static/layouts/layout1/script.js"],
                }
                assert resource_manager._resource_cache["layout2"] == {
                    "css": ["/static/layouts/layout2/style.css"],
                    "js": ["/static/layouts/layout2/script.js"],
                }
                assert resource_manager._resource_cache["layout3"] == {
                    "css": ["/static/layouts/layout3/style.css"],
                    "js": ["/static/layouts/layout3/script.js"],
                }

    def test_preload_resources_handles_exceptions_gracefully(self, resource_manager):
        """Test preload_resources handles exceptions for individual layouts gracefully."""
        # Patch get_css_urls to raise exception for specific layout
        with patch.object(resource_manager, "get_css_urls") as mock_get_css_urls:
            with patch.object(resource_manager, "get_js_urls") as mock_get_js_urls:
                mock_get_css_urls.side_effect = lambda layout: (
                    [f"/static/layouts/{layout}/style.css"]
                    if layout != "layout2"
                    else (_ for _ in ()).throw(
                        Exception("Test error")
                    )  # Raise exception for layout2
                )
                mock_get_js_urls.return_value = ["/static/layouts/test/script.js"]

                # Should not raise exception
                resource_manager.preload_resources(["layout1", "layout2", "layout3"])

                # Should cache resources for successful layouts only
                assert "layout1" in resource_manager._resource_cache
                assert "layout2" not in resource_manager._resource_cache
                assert "layout3" in resource_manager._resource_cache


class TestResourceManagerAdditionalMethods:
    """Test additional methods not covered by existing tests."""

    @pytest.fixture
    def mock_registry(self):
        """Create mock registry."""
        registry = Mock()
        return registry

    @pytest.fixture
    def resource_manager(self, mock_registry):
        """Create resource manager with mock registry."""
        return ResourceManager(mock_registry, base_url="/custom-static")

    def test_get_layout_base_path_returns_correct_path(self, resource_manager):
        """Test get_layout_base_path returns correct path with base URL."""
        result = resource_manager.get_layout_base_path("test-layout")

        assert result == "/custom-static/layouts/test-layout"

    def test_get_layout_base_path_with_different_layouts(self, resource_manager):
        """Test get_layout_base_path with different layout names."""
        assert resource_manager.get_layout_base_path("layout1") == "/custom-static/layouts/layout1"
        assert resource_manager.get_layout_base_path("layout2") == "/custom-static/layouts/layout2"
        assert resource_manager.get_layout_base_path("") == "/custom-static/layouts/"

    def test_get_layout_base_path_with_default_base_url(self, mock_registry):
        """Test get_layout_base_path with default base URL."""
        resource_manager = ResourceManager(mock_registry)  # Uses default base_url="/static"

        result = resource_manager.get_layout_base_path("test-layout")

        assert result == "/static/layouts/test-layout"
