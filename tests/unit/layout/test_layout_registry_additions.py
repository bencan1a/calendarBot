"""Additional unit tests for calendarbot.layout.registry module to improve coverage."""

import json
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from calendarbot.layout.exceptions import LayoutNotFoundError, LayoutValidationError
from calendarbot.layout.registry import LayoutInfo, LayoutRegistry, _raise_missing_field_error


class TestLayoutRegistryAdditionalCoverage:
    """Additional tests to improve coverage for LayoutRegistry."""

    def test_raise_missing_field_error_when_called_then_raises_validation_error(self) -> None:
        """Test _raise_missing_field_error raises LayoutValidationError with correct message."""
        field_name = "test_field"

        with pytest.raises(LayoutValidationError) as excinfo:
            _raise_missing_field_error(field_name)

        assert f"Missing required field: {field_name}" in str(excinfo.value)

    def test_discover_layouts_when_directory_not_exists_then_creates_emergency_layouts(
        self,
    ) -> None:
        """Test discover_layouts creates emergency layouts when directory doesn't exist."""
        with patch.object(LayoutRegistry, "_create_emergency_layouts") as mock_create_emergency:
            registry = LayoutRegistry()

            # Mock directory not existing
            registry.layouts_dir = Mock()
            registry.layouts_dir.exists.return_value = False

            # Call discover_layouts
            registry.discover_layouts()

            # Verify _create_emergency_layouts was called
            mock_create_emergency.assert_called_once()

    def test_discover_layouts_when_iterdir_raises_exception_then_creates_emergency_layouts(
        self,
    ) -> None:
        """Test discover_layouts creates emergency layouts when iterdir raises exception."""
        with patch.object(LayoutRegistry, "_create_emergency_layouts") as mock_create_emergency:
            registry = LayoutRegistry()

            # Mock directory existing but iterdir raising exception
            registry.layouts_dir = Mock()
            registry.layouts_dir.exists.return_value = True
            registry.layouts_dir.iterdir.side_effect = Exception("Test exception")

            # Call discover_layouts
            registry.discover_layouts()

            # Verify _create_emergency_layouts was called
            mock_create_emergency.assert_called_once()

    def test_load_layout_config_when_valid_json_then_returns_layout_info(self) -> None:
        """Test _load_layout_config returns LayoutInfo for valid JSON."""
        registry = LayoutRegistry()

        # Mock config file and JSON data
        config_file = Mock(spec=Path)
        config_data = {
            "name": "test_layout",
            "display_name": "Test Layout",
            "version": "1.0.0",
            "capabilities": {"test": True},
            "renderer_mapping": {"internal_type": "test_renderer"},
            "fallback_chain": ["fallback1", "fallback2"],
            "resources": {"css": ["test.css"], "js": ["test.js"]},
            "requirements": {"test_req": True},
            "description": "Test description",
        }

        # Mock the file opening
        m = mock_open()
        with (
            patch("builtins.open", m),
            patch("json.load", return_value=config_data),
        ):
            # Mock Path.open to return our mock file
            config_file.open.return_value = m()

            layout_info = registry._load_layout_config(config_file)

        # Verify LayoutInfo was created correctly
        assert layout_info.name == "test_layout"
        assert layout_info.display_name == "Test Layout"
        assert layout_info.version == "1.0.0"
        assert layout_info.description == "Test description"
        assert layout_info.capabilities == {"test": True}
        assert layout_info.renderer_type == "test_renderer"
        assert layout_info.fallback_chain == ["fallback1", "fallback2"]
        assert layout_info.resources == {"css": ["test.css"], "js": ["test.js"]}
        assert layout_info.requirements == {"test_req": True}

    def test_load_layout_config_when_missing_required_field_then_raises_validation_error(
        self,
    ) -> None:
        """Test _load_layout_config raises LayoutValidationError for missing required field."""
        registry = LayoutRegistry()

        # Mock config file and JSON data with missing required field
        config_file = Mock(spec=Path)
        config_data = {
            # Missing "name" field
            "display_name": "Test Layout",
            "version": "1.0.0",
            "capabilities": {"test": True},
        }

        # Mock the file opening
        m = mock_open()
        with (
            patch("builtins.open", m),
            patch("json.load", return_value=config_data),
        ):
            # Mock Path.open to return our mock file
            config_file.open.return_value = m()

            with pytest.raises(LayoutValidationError) as excinfo:
                registry._load_layout_config(config_file)

        assert "Missing required field: name" in str(excinfo.value)

    def test_load_layout_config_when_json_decode_error_then_raises_validation_error(self) -> None:
        """Test _load_layout_config raises LayoutValidationError for JSON decode error."""
        registry = LayoutRegistry()

        # Mock config file
        config_file = Mock(spec=Path)

        # Mock the file opening
        m = mock_open()
        with (
            patch("builtins.open", m),
            patch("json.load", side_effect=json.JSONDecodeError("Test error", "", 0)),
        ):
            # Mock Path.open to return our mock file
            config_file.open.return_value = m()

            with pytest.raises(LayoutValidationError) as excinfo:
                registry._load_layout_config(config_file)

        assert "Invalid JSON" in str(excinfo.value)

    def test_load_layout_config_when_general_exception_then_raises_validation_error(self) -> None:
        """Test _load_layout_config raises LayoutValidationError for general exceptions."""
        registry = LayoutRegistry()

        # Mock config file
        config_file = Mock(spec=Path)

        # Mock open and json.load raising general exception
        m = mock_open()
        with (
            patch("builtins.open", m),
            patch("json.load", side_effect=Exception("Test error")),
        ):
            # Mock Path.open to return our mock file
            config_file.open.return_value = m()

            with pytest.raises(LayoutValidationError) as excinfo:
                registry._load_layout_config(config_file)

        assert "Error loading" in str(excinfo.value)

    def test_create_emergency_layouts_when_called_then_creates_expected_layouts(self) -> None:
        """Test _create_emergency_layouts creates expected emergency layouts."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()
            registry._layouts = {}  # Clear any existing layouts

            # Call _create_emergency_layouts
            registry._create_emergency_layouts()

            # Verify emergency layouts were created (no longer includes 3x4)
            assert "4x8" in registry._layouts
            assert "console" in registry._layouts
            # 3x4 is no longer created as emergency layout
            assert "3x4" not in registry._layouts

            # Verify 4x8 layout properties
            assert registry._layouts["4x8"].name == "4x8"
            assert "Emergency" in registry._layouts["4x8"].display_name
            assert registry._layouts["4x8"].fallback_chain == ["console"]

            # Verify console layout properties
            assert registry._layouts["console"].name == "console"
            assert "Emergency" in registry._layouts["console"].display_name
            assert registry._layouts["console"].fallback_chain == []

    def test_get_layout_with_fallback_when_layout_exists_then_returns_layout(self) -> None:
        """Test get_layout_with_fallback returns layout when it exists."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()

            # Create test layout
            test_layout = LayoutInfo(
                name="test_layout",
                display_name="Test Layout",
                version="1.0.0",
                description="Test description",
                capabilities={},
                renderer_type="test",
                fallback_chain=[],
                resources={},
                requirements={},
            )

            # Add test layout to registry
            registry._layouts = {"test_layout": test_layout}

            # Call get_layout_with_fallback
            result = registry.get_layout_with_fallback("test_layout")

            # Verify result
            assert result is test_layout

    def test_get_layout_with_fallback_when_layout_not_exists_but_in_registry_then_uses_fallback_chain(
        self,
    ) -> None:
        """Test get_layout_with_fallback uses fallback chain when layout doesn't exist but is in registry."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()

            # Create fallback layout
            fallback_layout = LayoutInfo(
                name="fallback1",
                display_name="Fallback Layout",
                version="1.0.0",
                description="Fallback layout",
                capabilities={},
                renderer_type="test",
                fallback_chain=[],
                resources={},
                requirements={},
            )

            # Add layouts to registry
            registry._layouts = {
                "primary": LayoutInfo(
                    name="primary",
                    display_name="Primary Layout",
                    version="1.0.0",
                    description="Primary layout",
                    capabilities={},
                    renderer_type="test",
                    fallback_chain=["fallback1"],
                    resources={},
                    requirements={},
                ),
                "fallback1": fallback_layout,
            }

            # Create a custom implementation of get_layout_info
            def mock_get_layout_info(layout_name):
                if layout_name == "primary":
                    return None
                if layout_name == "fallback1":
                    return fallback_layout
                return None

            # Patch get_layout_info with our custom implementation
            with (
                patch.object(registry, "get_layout_info", side_effect=mock_get_layout_info),
                patch.object(registry, "get_fallback_chain", return_value=["fallback1"]),
            ):
                # Call get_layout_with_fallback
                result = registry.get_layout_with_fallback("primary")

                # Verify result is fallback layout
                assert result.name == "fallback1"

    def test_get_layout_with_fallback_when_layout_not_in_registry_then_uses_emergency_fallback(
        self,
    ) -> None:
        """Test get_layout_with_fallback uses emergency fallback when layout not in registry."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()

            # Create emergency fallback layout
            emergency_layout = LayoutInfo(
                name="4x8",
                display_name="Emergency Layout",
                version="1.0.0",
                description="Emergency layout",
                capabilities={},
                renderer_type="test",
                fallback_chain=[],
                resources={},
                requirements={},
            )

            # Add emergency layout to registry
            registry._layouts = {"4x8": emergency_layout}

            # Set fallback layouts
            registry._fallback_layouts = ["4x8"]

            # Call get_layout_with_fallback with non-existent layout
            result = registry.get_layout_with_fallback("nonexistent")

            # Verify result is emergency layout
            assert result is emergency_layout

    def test_get_layout_with_fallback_when_no_layouts_available_then_raises_error(self) -> None:
        """Test get_layout_with_fallback raises LayoutNotFoundError when no layouts available."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()

            # Empty layouts and fallbacks
            registry._layouts = {}
            registry._fallback_layouts = ["nonexistent"]

            # Call get_layout_with_fallback with non-existent layout
            with pytest.raises(LayoutNotFoundError) as excinfo:
                registry.get_layout_with_fallback("nonexistent")

            assert "No valid layouts found" in str(excinfo.value)

    def test_get_layout_css_paths_when_valid_layout_then_returns_paths(self) -> None:
        """Test get_layout_css_paths returns correct paths for valid layout."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()

            # Create test layout with CSS resources
            test_layout = LayoutInfo(
                name="test_layout",
                display_name="Test Layout",
                version="1.0.0",
                description="Test description",
                capabilities={},
                renderer_type="test",
                fallback_chain=[],
                resources={"css": ["style1.css", "style2.css"]},
                requirements={},
            )

            # Add test layout to registry
            registry._layouts = {"test_layout": test_layout}

            # Set layouts_dir
            registry.layouts_dir = Path("/test/layouts")

            # Call get_layout_css_paths
            css_paths = registry.get_layout_css_paths("test_layout")

            # Verify paths
            assert len(css_paths) == 2
            assert css_paths[0] == Path("/test/layouts/test_layout/style1.css")
            assert css_paths[1] == Path("/test/layouts/test_layout/style2.css")

    def test_get_layout_css_paths_when_layout_not_found_then_raises_error(self) -> None:
        """Test get_layout_css_paths raises LayoutNotFoundError when layout not found."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()
            registry._layouts = {}

            with pytest.raises(LayoutNotFoundError) as excinfo:
                registry.get_layout_css_paths("nonexistent")

            assert "not found" in str(excinfo.value)

    def test_get_layout_css_paths_with_object_format_resources(self) -> None:
        """Test get_layout_css_paths handles object format resources correctly."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()

            # Create test layout with CSS resources in object format
            test_layout = LayoutInfo(
                name="test_layout",
                display_name="Test Layout",
                version="1.0.0",
                description="Test description",
                capabilities={},
                renderer_type="test",
                fallback_chain=[],
                resources={"css": [{"file": "style1.css"}, {"file": "style2.css"}]},
                requirements={},
            )

            # Add test layout to registry
            registry._layouts = {"test_layout": test_layout}

            # Set layouts_dir
            registry.layouts_dir = Path("/test/layouts")

            # Call get_layout_css_paths
            css_paths = registry.get_layout_css_paths("test_layout")

            # Verify paths
            assert len(css_paths) == 2
            assert css_paths[0] == Path("/test/layouts/test_layout/style1.css")
            assert css_paths[1] == Path("/test/layouts/test_layout/style2.css")

    def test_get_layout_css_paths_skips_external_urls(self) -> None:
        """Test get_layout_css_paths skips external URLs."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()

            # Create test layout with CSS resources including external URL
            test_layout = LayoutInfo(
                name="test_layout",
                display_name="Test Layout",
                version="1.0.0",
                description="Test description",
                capabilities={},
                renderer_type="test",
                fallback_chain=[],
                resources={"css": ["style1.css", "http://example.com/style.css"]},
                requirements={},
            )

            # Add test layout to registry
            registry._layouts = {"test_layout": test_layout}

            # Set layouts_dir
            registry.layouts_dir = Path("/test/layouts")

            # Call get_layout_css_paths
            css_paths = registry.get_layout_css_paths("test_layout")

            # Verify only local path is included
            assert len(css_paths) == 1
            assert css_paths[0] == Path("/test/layouts/test_layout/style1.css")

    def test_get_layout_js_paths_when_valid_layout_then_returns_paths(self) -> None:
        """Test get_layout_js_paths returns correct paths for valid layout."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()

            # Create test layout with JS resources
            test_layout = LayoutInfo(
                name="test_layout",
                display_name="Test Layout",
                version="1.0.0",
                description="Test description",
                capabilities={},
                renderer_type="test",
                fallback_chain=[],
                resources={"js": ["script1.js", "script2.js"]},
                requirements={},
            )

            # Add test layout to registry
            registry._layouts = {"test_layout": test_layout}

            # Set layouts_dir
            registry.layouts_dir = Path("/test/layouts")

            # Call get_layout_js_paths
            js_paths = registry.get_layout_js_paths("test_layout")

            # Verify paths
            assert len(js_paths) == 2
            assert js_paths[0] == Path("/test/layouts/test_layout/script1.js")
            assert js_paths[1] == Path("/test/layouts/test_layout/script2.js")

    def test_get_layout_js_paths_when_layout_not_found_then_raises_error(self) -> None:
        """Test get_layout_js_paths raises LayoutNotFoundError when layout not found."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()
            registry._layouts = {}

            with pytest.raises(LayoutNotFoundError) as excinfo:
                registry.get_layout_js_paths("nonexistent")

            assert "not found" in str(excinfo.value)

    def test_get_layout_js_paths_with_object_format_resources(self) -> None:
        """Test get_layout_js_paths handles object format resources correctly."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()

            # Create test layout with JS resources in object format
            test_layout = LayoutInfo(
                name="test_layout",
                display_name="Test Layout",
                version="1.0.0",
                description="Test description",
                capabilities={},
                renderer_type="test",
                fallback_chain=[],
                resources={"js": [{"file": "script1.js"}, {"file": "script2.js"}]},
                requirements={},
            )

            # Add test layout to registry
            registry._layouts = {"test_layout": test_layout}

            # Set layouts_dir
            registry.layouts_dir = Path("/test/layouts")

            # Call get_layout_js_paths
            js_paths = registry.get_layout_js_paths("test_layout")

            # Verify paths
            assert len(js_paths) == 2
            assert js_paths[0] == Path("/test/layouts/test_layout/script1.js")
            assert js_paths[1] == Path("/test/layouts/test_layout/script2.js")

    def test_get_layout_js_paths_skips_external_urls(self) -> None:
        """Test get_layout_js_paths skips external URLs."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()

            # Create test layout with JS resources including external URL
            test_layout = LayoutInfo(
                name="test_layout",
                display_name="Test Layout",
                version="1.0.0",
                description="Test description",
                capabilities={},
                renderer_type="test",
                fallback_chain=[],
                resources={"js": ["script1.js", "http://example.com/script.js"]},
                requirements={},
            )

            # Add test layout to registry
            registry._layouts = {"test_layout": test_layout}

            # Set layouts_dir
            registry.layouts_dir = Path("/test/layouts")

            # Call get_layout_js_paths
            js_paths = registry.get_layout_js_paths("test_layout")

            # Verify only local path is included
            assert len(js_paths) == 1
            assert js_paths[0] == Path("/test/layouts/test_layout/script1.js")

    def test_discover_layouts_alias_when_called_then_calls_discover_layouts(self) -> None:
        """Test _discover_layouts calls discover_layouts (backward compatibility)."""
        registry = LayoutRegistry()

        # Reset mock_calls to clear the call from initialization
        with patch.object(LayoutRegistry, "discover_layouts") as mock_discover:
            # Call _discover_layouts
            registry._discover_layouts()

            # Verify discover_layouts was called
            assert mock_discover.call_count == 1
