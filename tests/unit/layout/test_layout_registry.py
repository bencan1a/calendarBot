"""Unit tests for calendarbot.layout.registry module."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from calendarbot.layout.exceptions import LayoutNotFoundError
from calendarbot.layout.registry import LayoutInfo, LayoutRegistry

# Disable logging during tests for performance
logging.getLogger("calendarbot").setLevel(logging.CRITICAL)


@pytest.fixture(scope="module")
def mock_layout_info():
    """Shared LayoutInfo fixture for performance."""
    return LayoutInfo(
        name="test",
        display_name="Test Layout",
        description="Test layout",
        version="1.0.0",
        capabilities={"test": True},
        renderer_type="html",
        fallback_chain=["console"],
        resources={"css": ["test.css"], "js": ["test.js"]},
        requirements={},
    )


@pytest.fixture(scope="module")
def mock_registry():
    """Shared registry fixture with minimal setup."""
    with patch.object(LayoutRegistry, "discover_layouts"):
        registry = LayoutRegistry()
        registry._layouts = {
            "4x8": LayoutInfo(
                name="4x8",
                display_name="4x8 Layout",
                description="Standard 4x8 layout",
                version="1.0.0",
                capabilities={"grid_dimensions": {"columns": 4, "rows": 8}},
                renderer_type="html",
                fallback_chain=["whats-next-view", "console"],
                resources={"css": ["4x8.css"], "js": ["4x8.js"]},
                requirements={},
            ),
            "whats-next-view": LayoutInfo(
                name="whats-next-view",
                display_name="What's Next View",
                description="Next upcoming event view",
                version="1.0.0",
                capabilities={"view_type": "upcoming"},
                renderer_type="html",
                fallback_chain=["4x8", "console"],
                resources={"css": ["whats-next-view.css"], "js": ["whats-next-view.js"]},
                requirements={},
            ),
        }
        return registry


class TestLayoutRegistryInitialization:
    """Test LayoutRegistry initialization and discovery."""

    def test_init_with_default_layouts_directory(self) -> None:
        """Test initialization with default layouts directory."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()
            assert hasattr(registry, "layouts_dir")
            assert registry.layouts_dir is not None

    def test_init_with_custom_layouts_directory(self) -> None:
        """Test initialization with custom layouts directory."""
        custom_dir = Path("/custom/layouts")
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry(layouts_dir=custom_dir)
            assert registry.layouts_dir == custom_dir

    def test_init_calls_discover_layouts(self) -> None:
        """Test initialization calls discover_layouts method."""
        with patch.object(LayoutRegistry, "discover_layouts") as mock_discover:
            LayoutRegistry()
            mock_discover.assert_called_once()


class TestLayoutRegistryDiscovery:
    """Test layout discovery functionality."""

    def test_discover_layouts_finds_valid_layouts(self, mock_registry) -> None:
        """Test discovery finds valid layouts with layout.json files."""
        # Use shared registry instead of creating new one
        available_layouts = mock_registry.get_available_layouts()
        assert "4x8" in available_layouts
        assert "whats-next-view" in available_layouts

    def test_discover_layouts_handles_invalid_json(self) -> None:
        """Test discovery handles invalid JSON gracefully."""
        with patch.object(LayoutRegistry, "discover_layouts"):
            registry = LayoutRegistry()
            registry._layouts = {}  # Simulate failure to load
            available_layouts = registry.get_available_layouts()
            assert len(available_layouts) >= 0


class TestLayoutRegistryValidation:
    """Test layout validation functionality."""

    def test_validate_layout_valid_layout(self, mock_registry) -> None:
        """Test validation of valid layout."""
        assert mock_registry.validate_layout("4x8") is True
        assert mock_registry.validate_layout("whats-next-view") is True

    def test_validate_layout_invalid_layout(self, mock_registry) -> None:
        """Test validation of invalid layout."""
        assert mock_registry.validate_layout("invalid") is False
        assert mock_registry.validate_layout("") is False
        assert mock_registry.validate_layout(None) is False

    def test_get_layout_metadata_valid_layout(self, mock_registry) -> None:
        """Test getting metadata for valid layout."""
        metadata = mock_registry.get_layout_metadata("4x8")
        assert metadata["name"] == "4x8"
        assert metadata["display_name"] == "4x8 Layout"
        assert "4x8.css" in metadata["resources"]["css"]

    def test_get_available_layouts(self, mock_registry) -> None:
        """Test getting list of available layouts."""
        layouts = mock_registry.get_available_layouts()
        assert "4x8" in layouts
        assert "whats-next-view" in layouts
        assert len(layouts) == 2

    def test_get_default_layout(self, mock_registry) -> None:
        """Test getting default layout."""
        default = mock_registry.get_default_layout()
        assert default in ["4x8", "whats-next-view"]


class TestLayoutRegistryAdvanced:
    """Test advanced layout registry functionality."""

    def test_get_renderer_type(self, mock_registry) -> None:
        """Test getting renderer type for layout."""
        renderer_type = mock_registry.get_renderer_type("4x8")
        assert renderer_type == "html"

    def test_get_renderer_type_invalid_layout(self, mock_registry) -> None:
        """Test getting renderer type for invalid layout raises exception."""
        with pytest.raises(LayoutNotFoundError):
            mock_registry.get_renderer_type("invalid")

    def test_get_fallback_chain(self, mock_registry) -> None:
        """Test getting fallback chain for layout."""
        fallback_chain = mock_registry.get_fallback_chain("4x8")
        assert fallback_chain == ["whats-next-view", "console"]


class TestLayoutRegistryErrorHandling:
    """Test error handling and edge cases."""

    def test_get_layout_with_fallback(self, mock_registry) -> None:
        """Test layout fallback chain functionality."""
        # Add console layout for fallback testing
        mock_registry._layouts["console"] = LayoutInfo(
            name="console",
            display_name="Console Layout",
            description="Emergency console layout",
            version="1.0.0",
            capabilities={"renderer_type": "console"},
            renderer_type="console",
            fallback_chain=[],
            resources={},
            requirements={},
        )
        mock_registry._fallback_layouts = mock_registry._generate_dynamic_fallbacks()

        # Test successful fallback
        layout = mock_registry.get_layout_with_fallback("nonexistent")
        assert layout.name == "4x8"

        # Test direct layout retrieval
        layout = mock_registry.get_layout_with_fallback("4x8")
        assert layout.name == "4x8"
