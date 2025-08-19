"""Additional unit tests for calendarbot.layout.registry module to improve coverage."""

import json
import logging
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from calendarbot.layout.exceptions import LayoutValidationError
from calendarbot.layout.registry import LayoutInfo, LayoutRegistry, _raise_missing_field_error

# Disable logging for performance
logging.getLogger("calendarbot").setLevel(logging.CRITICAL)


class TestLayoutRegistryAdditionalCoverage:
    """Additional tests to improve coverage for LayoutRegistry."""

    def test_raise_missing_field_error_when_called_then_raises_validation_error(self) -> None:
        """Test _raise_missing_field_error raises LayoutValidationError with correct message."""
        field_name = "test_field"
        with pytest.raises(LayoutValidationError) as excinfo:
            _raise_missing_field_error(field_name)
        assert f"Missing required field: {field_name}" in str(excinfo.value)

    def test_discover_layouts_creates_emergency_layouts_when_directory_missing(self) -> None:
        """Test discover_layouts creates emergency layouts when directory doesn't exist."""
        with patch.object(LayoutRegistry, "_create_emergency_layouts") as mock_create_emergency:
            registry = LayoutRegistry()
            registry.layouts_dir = Mock()
            registry.layouts_dir.exists.return_value = False

            # Call the real discover_layouts method which should detect missing directory
            LayoutRegistry.discover_layouts(registry)

            mock_create_emergency.assert_called_once()

    def test_discover_layouts_creates_emergency_layouts_on_iterdir_error(self) -> None:
        """Test discover_layouts creates emergency layouts when iterdir fails."""
        with patch.object(LayoutRegistry, "_create_emergency_layouts") as mock_create_emergency:
            registry = LayoutRegistry()
            registry.layouts_dir = Mock()
            registry.layouts_dir.exists.return_value = True
            registry.layouts_dir.iterdir.side_effect = Exception("Test exception")

            # Call the real discover_layouts method which should handle the exception
            LayoutRegistry.discover_layouts(registry)

            mock_create_emergency.assert_called_once()

    @pytest.mark.parametrize(
        "error_type,expected_message",
        [
            (json.JSONDecodeError("Test error", "", 0), "Invalid JSON"),
            (Exception("Test error"), "Error loading"),
        ],
    )
    def test_load_layout_config_error_handling(self, error_type, expected_message) -> None:
        """Test _load_layout_config error handling for various exceptions."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()
            config_file = Mock(spec=Path)

            m = mock_open()
            with (
                patch("builtins.open", m),
                patch("json.load", side_effect=error_type),
            ):
                config_file.open.return_value = m()
                with pytest.raises(LayoutValidationError) as excinfo:
                    registry._load_layout_config(config_file)
                assert expected_message in str(excinfo.value)

    def test_load_layout_config_valid_json(self) -> None:
        """Test _load_layout_config returns LayoutInfo for valid JSON."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()
            config_file = Mock(spec=Path)
            config_data = {
                "name": "test_layout",
                "display_name": "Test Layout",
                "version": "1.0.0",
                "capabilities": {"test": True},
                "renderer_mapping": {"internal_type": "test_renderer"},
                "fallback_chain": ["fallback1"],
                "resources": {"css": ["test.css"], "js": ["test.js"]},
                "requirements": {"test_req": True},
                "description": "Test description",
            }

            m = mock_open()
            with (
                patch("builtins.open", m),
                patch("json.load", return_value=config_data),
            ):
                config_file.open.return_value = m()
                layout_info = registry._load_layout_config(config_file)

            assert layout_info.name == "test_layout"
            assert layout_info.display_name == "Test Layout"
            assert layout_info.renderer_type == "test_renderer"

    def test_create_emergency_layouts(self) -> None:
        """Test _create_emergency_layouts creates expected emergency layouts."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()
            registry._layouts = {}
            registry._create_emergency_layouts()

            assert "4x8" in registry._layouts
            assert "console" in registry._layouts
            assert "Emergency" in registry._layouts["4x8"].display_name

    @pytest.mark.parametrize(
        "layout_exists,fallback_available,expected_result",
        [
            (True, False, "test_layout"),
            (False, True, "4x8"),
        ],
    )
    def test_get_layout_with_fallback_scenarios(
        self, layout_exists, fallback_available, expected_result
    ) -> None:
        """Test get_layout_with_fallback under various scenarios."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()

            if layout_exists:
                test_layout = LayoutInfo(
                    name="test_layout",
                    display_name="Test Layout",
                    version="1.0.0",
                    description="Test",
                    capabilities={},
                    renderer_type="test",
                    fallback_chain=[],
                    resources={},
                    requirements={},
                )
                registry._layouts = {"test_layout": test_layout}
                result = registry.get_layout_with_fallback("test_layout")
                assert result.name == expected_result
            elif fallback_available:
                emergency_layout = LayoutInfo(
                    name="4x8",
                    display_name="Emergency",
                    version="1.0.0",
                    description="Emergency",
                    capabilities={},
                    renderer_type="test",
                    fallback_chain=[],
                    resources={},
                    requirements={},
                )
                registry._layouts = {"4x8": emergency_layout}
                registry._fallback_layouts = ["4x8"]
                result = registry.get_layout_with_fallback("nonexistent")
                assert result.name == expected_result

    @pytest.mark.parametrize(
        "resource_type,expected_count",
        [
            ("css", 2),
            ("js", 2),
        ],
    )
    def test_get_layout_resource_paths(self, resource_type, expected_count) -> None:
        """Test get_layout_css_paths and get_layout_js_paths return correct paths."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()
            test_layout = LayoutInfo(
                name="test_layout",
                display_name="Test Layout",
                version="1.0.0",
                description="Test",
                capabilities={},
                renderer_type="test",
                fallback_chain=[],
                resources={resource_type: [f"file1.{resource_type}", f"file2.{resource_type}"]},
                requirements={},
            )
            registry._layouts = {"test_layout": test_layout}
            registry.layouts_dir = Path("/test/layouts")

            if resource_type == "css":
                paths = registry.get_layout_css_paths("test_layout")
            else:
                paths = registry.get_layout_js_paths("test_layout")

            assert len(paths) == expected_count
            assert all(isinstance(p, Path) for p in paths)

    def test_discover_layouts_alias(self) -> None:
        """Test _discover_layouts calls discover_layouts (backward compatibility)."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()
            with patch.object(LayoutRegistry, "discover_layouts") as mock_discover:
                registry._discover_layouts()
                assert mock_discover.call_count == 1
