"""Central layout registry for dynamic layout discovery and validation."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn, Optional, Union

from .exceptions import LayoutNotFoundError, LayoutValidationError

logger = logging.getLogger(__name__)


def _raise_missing_field_error(field: str) -> NoReturn:
    """Raise LayoutValidationError for missing required field."""
    raise LayoutValidationError(f"Missing required field: {field}")


@dataclass
class LayoutInfo:
    """Information about a layout configuration."""

    name: str
    display_name: str
    version: str
    description: str
    capabilities: dict[str, Any]
    renderer_type: str
    fallback_chain: list[str]
    resources: dict[str, list[Union[str, dict[str, Any]]]]
    requirements: dict[str, Any]


class LayoutRegistry:
    """Central registry for dynamic layout discovery and management."""

    layouts_dir: Path  # Always a Path after initialization
    _layouts: dict[str, LayoutInfo]
    _fallback_layouts: list[str]

    def __init__(
        self, layouts_dir: Optional[Path] = None, layouts_directory: Optional[Path] = None
    ) -> None:
        """Initialize layout registry.

        Args:
            layouts_dir: Directory containing layout configurations.
                        Defaults to 'layouts' in project root.
            layouts_directory: Alias for layouts_dir for backward compatibility.
        """
        # Support both parameter names for backward compatibility
        if layouts_directory is not None:
            layouts_dir = layouts_directory
        if layouts_dir is None:
            # Default to layouts directory in web/static/layouts
            calendarbot_module = Path(__file__).parent.parent
            layouts_dir = calendarbot_module / "web" / "static" / "layouts"

        self.layouts_dir = layouts_dir
        logger.debug(f"LayoutRegistry initialized with layouts_dir: {self.layouts_dir}")
        self._layouts: dict[str, LayoutInfo] = {}
        self._fallback_layouts = ["4x8", "3x4", "console"]  # Emergency fallback

        # Discover layouts on initialization
        self.discover_layouts()

    def discover_layouts(self) -> None:
        """Scan filesystem and rebuild layout registry.

        Raises:
            LayoutValidationError: If layout configuration is invalid.
        """
        self._layouts.clear()

        if not self.layouts_dir.exists():
            logger.warning(f"Layouts directory not found: {self.layouts_dir}")
            # Use emergency fallback
            self._create_emergency_layouts()
            return

        try:
            for layout_dir in self.layouts_dir.iterdir():
                if not layout_dir.is_dir():
                    continue

                config_file = layout_dir / "layout.json"
                if not config_file.exists():
                    logger.debug(f"Skipping {layout_dir.name} - no layout.json found")
                    continue

                try:
                    layout_info = self._load_layout_config(config_file)
                    self._layouts[layout_info.name] = layout_info
                    logger.debug(f"Loaded layout: {layout_info.name}")
                except Exception:
                    logger.exception(f"Failed to load layout from {config_file}")

        except Exception:
            logger.exception("Error discovering layouts")
            # Use emergency fallback
            self._create_emergency_layouts()

    def _load_layout_config(self, config_file: Path) -> LayoutInfo:
        """Load layout configuration from JSON file.

        Args:
            config_file: Path to layout.json file.

        Returns:
            LayoutInfo object with configuration data.

        Raises:
            LayoutValidationError: If configuration is invalid.
        """
        try:
            with config_file.open(encoding="utf-8") as f:
                config_data = json.load(f)

            # Validate required fields (renderer_mapping is now optional in new architecture)
            required_fields = ["name", "display_name", "version", "capabilities"]
            for field in required_fields:
                if field not in config_data:
                    _raise_missing_field_error(field)

            # Extract renderer type from mapping
            renderer_mapping = config_data.get("renderer_mapping", {})
            renderer_type = renderer_mapping.get("internal_type", "console")

            return LayoutInfo(
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

        except json.JSONDecodeError as e:
            raise LayoutValidationError(f"Invalid JSON in {config_file}: {e}") from e
        except Exception as e:
            raise LayoutValidationError(f"Error loading {config_file}: {e}") from e

    def _create_emergency_layouts(self) -> None:
        """Create emergency fallback layouts when filesystem discovery fails."""
        logger.warning("Creating emergency fallback layouts")

        # 4x8 emergency layout
        self._layouts["4x8"] = LayoutInfo(
            name="4x8",
            display_name="4x8 Grid Layout (Emergency)",
            version="1.0.0",
            description="Emergency fallback 4x8 layout",
            capabilities={"grid_dimensions": {"columns": 4, "rows": 8}, "renderer_type": "html"},
            renderer_type="html",
            fallback_chain=["3x4", "console"],
            resources={"css": ["4x8.css"], "js": ["4x8.js"]},
            requirements={},
        )

        # 3x4 emergency layout
        self._layouts["3x4"] = LayoutInfo(
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

        # Console emergency layout
        self._layouts["console"] = LayoutInfo(
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

    def get_available_layouts(self) -> list[str]:
        """Get list of all available layout names.

        Returns:
            List of layout names.
        """
        return list(self._layouts.keys())

    def validate_layout(self, layout_name: str) -> bool:
        """Validate if a layout exists and is properly configured.

        Args:
            layout_name: Name of layout to validate.

        Returns:
            True if layout is valid, False otherwise.
        """
        return layout_name in self._layouts

    def get_layout_info(self, layout_name: str) -> Optional[LayoutInfo]:
        """Get detailed information about a specific layout.

        Args:
            layout_name: Name of layout to get info for.

        Returns:
            LayoutInfo object or None if layout not found.
        """
        return self._layouts.get(layout_name)

    def get_renderer_type(self, layout_name: str) -> str:
        """Get the renderer type required for a layout.

        Args:
            layout_name: Name of layout.

        Returns:
            Renderer type string.

        Raises:
            LayoutNotFoundError: If layout doesn't exist.
        """
        layout_info = self.get_layout_info(layout_name)
        if layout_info is None:
            raise LayoutNotFoundError(f"Layout '{layout_name}' not found")
        return layout_info.renderer_type

    def get_fallback_chain(self, layout_name: str) -> list[str]:
        """Get the fallback chain for a layout.

        Args:
            layout_name: Name of layout.

        Returns:
            List of fallback layout names.

        Raises:
            LayoutNotFoundError: If layout doesn't exist.
        """
        layout_info = self.get_layout_info(layout_name)
        if layout_info is None:
            raise LayoutNotFoundError(f"Layout '{layout_name}' not found")
        return layout_info.fallback_chain

    def get_layout_with_fallback(self, layout_name: str) -> LayoutInfo:
        """Get layout with automatic fallback chain.

        Args:
            layout_name: Primary layout name to try.

        Returns:
            LayoutInfo for successfully loaded layout.

        Raises:
            LayoutNotFoundError: If no layouts in fallback chain exist.
        """
        # Try primary layout first
        layout_info = self.get_layout_info(layout_name)
        if layout_info is not None:
            return layout_info

        # Try fallback chain from requested layout
        if layout_name in self._layouts:
            fallback_chain = self.get_fallback_chain(layout_name)
        else:
            fallback_chain = self._fallback_layouts

        for fallback_name in fallback_chain:
            layout_info = self.get_layout_info(fallback_name)
            if layout_info is not None:
                logger.warning(
                    f"Using fallback layout '{fallback_name}' instead of '{layout_name}'"
                )
                return layout_info

        # Emergency fallback
        for emergency_layout in self._fallback_layouts:
            layout_info = self.get_layout_info(emergency_layout)
            if layout_info is not None:
                logger.error(f"Using emergency layout '{emergency_layout}'")
                return layout_info

        raise LayoutNotFoundError(
            f"No valid layouts found, including fallbacks for '{layout_name}'"
        )

    def get_default_layout(self) -> str:
        """Get the default layout name.

        Returns:
            Default layout name.
        """
        if self._layouts:
            # Return first available layout, preferring whats-next-view
            if "whats-next-view" in self._layouts:
                return "whats-next-view"
            if "4x8" in self._layouts:
                return "4x8"
            if "3x4" in self._layouts:
                return "3x4"
            return next(iter(self._layouts.keys()))
        return "whats-next-view"  # Emergency fallback

    def get_layout_metadata(self, layout_name: str) -> Optional[dict[str, Any]]:
        """Get metadata for a specific layout.

        Args:
            layout_name: Name of layout to get metadata for.

        Returns:
            Layout metadata dictionary or None if layout not found.
        """
        layout_info = self.get_layout_info(layout_name)
        if layout_info is None:
            return None

        return {
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

    def get_layout_css_paths(self, layout_name: str) -> list[Path]:
        """Get CSS file paths for a layout.

        Args:
            layout_name: Name of layout to get CSS paths for.

        Returns:
            List of Path objects for CSS files.

        Raises:
            LayoutNotFoundError: If layout doesn't exist.
        """
        layout_info = self.get_layout_info(layout_name)
        if layout_info is None:
            raise LayoutNotFoundError(f"Layout '{layout_name}' not found")

        css_paths = []
        css_files = layout_info.resources.get("css", [])

        for css_file in css_files:
            # Handle both string and object formats
            file_name = css_file.get("file", "") if isinstance(css_file, dict) else css_file

            if not file_name or not isinstance(file_name, str) or file_name.startswith("http"):
                continue  # Skip external URLs or invalid entries

            css_path = self.layouts_dir / layout_info.name / file_name
            css_paths.append(css_path)

        return css_paths

    def get_layout_js_paths(self, layout_name: str) -> list[Path]:
        """Get JavaScript file paths for a layout.

        Args:
            layout_name: Name of layout to get JS paths for.

        Returns:
            List of Path objects for JavaScript files.

        Raises:
            LayoutNotFoundError: If layout doesn't exist.
        """
        layout_info = self.get_layout_info(layout_name)
        if layout_info is None:
            raise LayoutNotFoundError(f"Layout '{layout_name}' not found")

        js_paths = []
        js_files = layout_info.resources.get("js", [])

        for js_file in js_files:
            # Handle both string and object formats
            file_name = js_file.get("file", "") if isinstance(js_file, dict) else js_file

            if not file_name or not isinstance(file_name, str) or file_name.startswith("http"):
                continue  # Skip external URLs or invalid entries

            js_path = self.layouts_dir / layout_info.name / file_name
            js_paths.append(js_path)

        return js_paths

    def _discover_layouts(self) -> None:
        """Internal method for layout discovery (for backward compatibility with tests)."""
        self.discover_layouts()
