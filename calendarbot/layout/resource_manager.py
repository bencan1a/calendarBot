"""Resource manager for dynamic layout CSS/JS loading and injection."""

import logging
from pathlib import Path
from typing import Any, Optional

from .exceptions import LayoutNotFoundError, ResourceLoadingError
from .registry import LayoutRegistry

logger = logging.getLogger(__name__)


class ResourceManager:
    """Manages dynamic loading of layout resources."""

    def __init__(
        self,
        layout_registry: LayoutRegistry,
        base_url: str = "/static",
        settings: Optional[Any] = None,
    ) -> None:
        """Initialize resource manager.

        Args:
            layout_registry: Registry instance for layout discovery.
            base_url: Base URL path for serving static resources.
            settings: Application settings for conditional resource loading.
        """
        self.layout_registry = layout_registry
        self.base_url = base_url.rstrip("/")
        self.settings = settings
        self._resource_cache: dict[str, dict[str, list[str]]] = {}
        self._css_cache: dict[str, str] = {}
        self._js_cache: dict[str, str] = {}

    def get_css_urls(self, layout_name: str) -> list[str]:
        """Get CSS file URLs for a layout.

        Args:
            layout_name: Name of layout to get CSS for.

        Returns:
            List of CSS file URLs.

        Raises:
            ResourceLoadingError: If layout resources cannot be loaded.
        """
        try:
            layout_info = self.layout_registry.get_layout_with_fallback(layout_name)
            css_files = layout_info.resources.get("css", [])

            # Convert to URLs
            css_urls = []
            for css_file in css_files:
                # Handle both string and object formats
                if isinstance(css_file, dict):
                    file_name = css_file.get("file", "")

                    # Check for conditional loading
                    condition = css_file.get("condition", None)
                    if condition and condition == "epaper":
                        # Skip this CSS file if the condition is not met
                        # Only include e-paper CSS in e-paper mode
                        if (
                            not self.settings
                            or not hasattr(self.settings, "epaper")
                            or not getattr(self.settings.epaper, "enabled", False)
                        ):
                            logger.debug(
                                f"Skipping e-paper CSS file {file_name} - epaper mode not enabled"
                            )
                            continue
                        logger.debug(
                            f"Including e-paper CSS file {file_name} - epaper mode enabled"
                        )
                else:
                    file_name = css_file

                if not file_name or not isinstance(file_name, str):
                    continue

                if file_name.startswith("http"):
                    # External URL
                    css_urls.append(file_name)
                else:
                    # Local file - construct URL
                    css_urls.append(f"{self.base_url}/layouts/{layout_info.name}/{file_name}")

            return css_urls

        except Exception:
            logger.exception(f"Failed to get CSS URLs for layout '{layout_name}'")
            return []

    def get_js_urls(self, layout_name: str) -> list[str]:
        """Get JavaScript file URLs for a layout.

        Args:
            layout_name: Name of layout to get JavaScript for.

        Returns:
            List of JavaScript file URLs.

        Raises:
            ResourceLoadingError: If layout resources cannot be loaded.
        """
        try:
            layout_info = self.layout_registry.get_layout_with_fallback(layout_name)
            js_files = layout_info.resources.get("js", [])

            # Convert to URLs
            js_urls = []
            for js_file in js_files:
                # Handle both string and object formats
                file_name = js_file.get("file", "") if isinstance(js_file, dict) else js_file

                if not file_name or not isinstance(file_name, str):
                    continue

                if file_name.startswith("http"):
                    # External URL
                    js_urls.append(file_name)
                else:
                    # Local file - construct URL
                    js_urls.append(f"{self.base_url}/layouts/{layout_info.name}/{file_name}")

            return js_urls

        except Exception:
            logger.exception(f"Failed to get JS URLs for layout '{layout_name}'")
            return []

    def inject_layout_resources(self, template: str, layout_name: str) -> str:
        """Inject layout resources into HTML template.

        Args:
            template: HTML template string.
            layout_name: Name of layout to inject resources for.

        Returns:
            Updated HTML template with injected resources.

        Raises:
            ResourceLoadingError: If resource injection fails.
        """
        try:
            css_urls = self.get_css_urls(layout_name)
            js_urls = self.get_js_urls(layout_name)

            # Add shared settings panel resources
            shared_css_urls = [f"{self.base_url}/shared/css/settings-panel.css"]
            shared_js_urls = [
                f"{self.base_url}/shared/js/settings-api.js",
                f"{self.base_url}/shared/js/gesture-handler.js",
                f"{self.base_url}/shared/js/settings-panel.js",
            ]

            # Combine layout-specific and shared resources
            all_css_urls = shared_css_urls + css_urls
            all_js_urls = shared_js_urls + js_urls

            # Build CSS link tags
            css_links = [
                f'<link rel="stylesheet" type="text/css" href="{css_url}">'
                for css_url in all_css_urls
            ]
            css_html = "\n    ".join(css_links)

            # Build JS script tags
            js_scripts = [f'<script src="{js_url}"></script>' for js_url in all_js_urls]
            js_html = "\n    ".join(js_scripts)

            # Inject resources into template
            updated_template = template

            # Inject CSS before closing </head> tag
            if css_html and "</head>" in updated_template:
                updated_template = updated_template.replace("</head>", f"    {css_html}\n</head>")

            # Inject JS before closing </body> tag
            if js_html and "</body>" in updated_template:
                updated_template = updated_template.replace("</body>", f"    {js_html}\n</body>")

            return updated_template

        except Exception as e:
            logger.exception(f"Failed to inject resources for layout '{layout_name}'")
            raise ResourceLoadingError(f"Resource injection failed: {e}") from e

    def preload_resources(self, layout_names: list[str]) -> None:
        """Preload resources for multiple layouts.

        Args:
            layout_names: List of layout names to preload.
        """

        def _preload_single_layout(layout_name: str) -> None:
            """Helper to preload a single layout with error handling."""
            try:
                # Cache URLs for later use
                css_urls = self.get_css_urls(layout_name)
                js_urls = self.get_js_urls(layout_name)

                self._resource_cache[layout_name] = {"css": css_urls, "js": js_urls}

                logger.debug(f"Preloaded resources for layout: {layout_name}")

            except Exception as e:
                logger.warning(f"Failed to preload resources for layout '{layout_name}': {e}")

        for layout_name in layout_names:
            _preload_single_layout(layout_name)

    def get_css_content(self, layout_name: str) -> str:
        """Get CSS file content for a layout.

        Args:
            layout_name: Name of layout to get CSS content for.

        Returns:
            Combined CSS content from all layout CSS files.

        Raises:
            LayoutNotFoundError: If layout is not valid.
        """
        # Check cache first
        if layout_name in self._css_cache:
            return self._css_cache[layout_name]

        # Validate layout
        if not self.layout_registry.validate_layout(layout_name):
            raise LayoutNotFoundError(f"Layout '{layout_name}' not found")

        def _read_file_content(file_path: Path) -> str:
            """Helper to read file content with error handling."""
            try:
                with file_path.open(encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Failed to read CSS file '{file_path}': {e}")
                return ""

        try:
            css_paths = self.layout_registry.get_layout_css_paths(layout_name)

            css_content_parts = []
            for css_path in css_paths:
                content = _read_file_content(css_path)
                if content:
                    css_content_parts.append(content)

            combined_content = "\n".join(css_content_parts)

            # Cache the result
            self._css_cache[layout_name] = combined_content

            return combined_content

        except Exception:
            logger.exception(f"Failed to get CSS content for layout '{layout_name}'")
            return ""

    def get_js_content(self, layout_name: str) -> str:
        """Get JavaScript file content for a layout.

        Args:
            layout_name: Name of layout to get JS content for.

        Returns:
            Combined JavaScript content from all layout JS files.

        Raises:
            LayoutNotFoundError: If layout is not valid.
        """
        # Check cache first
        if layout_name in self._js_cache:
            return self._js_cache[layout_name]

        # Validate layout
        if not self.layout_registry.validate_layout(layout_name):
            raise LayoutNotFoundError(f"Layout '{layout_name}' not found")

        def _read_file_content(file_path: Path) -> str:
            """Helper to read file content with error handling."""
            try:
                with file_path.open(encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Failed to read JS file '{file_path}': {e}")
                return ""

        try:
            js_paths = self.layout_registry.get_layout_js_paths(layout_name)

            js_content_parts = []
            for js_path in js_paths:
                content = _read_file_content(js_path)
                if content:
                    js_content_parts.append(content)

            combined_content = "\n".join(js_content_parts)

            # Cache the result
            self._js_cache[layout_name] = combined_content

            return combined_content

        except Exception:
            logger.exception(f"Failed to get JS content for layout '{layout_name}'")
            return ""

    def get_css_paths_for_layout(self, layout_name: str) -> list[Path]:
        """Get CSS file paths for a layout.

        Args:
            layout_name: Name of layout to get CSS paths for.

        Returns:
            List of Path objects for CSS files.
        """
        css_paths: list[Path] = self.layout_registry.get_layout_css_paths(layout_name)
        return css_paths

    def get_js_paths_for_layout(self, layout_name: str) -> list[Path]:
        """Get JavaScript file paths for a layout.

        Args:
            layout_name: Name of layout to get JS paths for.

        Returns:
            List of Path objects for JavaScript files.
        """
        js_paths: list[Path] = self.layout_registry.get_layout_js_paths(layout_name)
        return js_paths

    def get_css_path(self, layout_name: str) -> Optional[Path]:
        """Get single CSS path for a layout.

        Args:
            layout_name: Name of layout to get CSS path for.

        Returns:
            Path to first CSS file for the layout, or None if no CSS files
            or if the first file is an external URL.
        """
        try:
            layout_info = self.layout_registry.get_layout_with_fallback(layout_name)
            css_files = layout_info.resources.get("css", [])

            if not css_files:
                return None

            first_css = css_files[0]

            # Handle both string and object formats
            file_name = first_css.get("file", "") if isinstance(first_css, dict) else first_css

            # Skip external URLs or invalid entries
            if not file_name or not isinstance(file_name, str) or file_name.startswith("http"):
                return None

            # Return path to first CSS file
            return Path(self.layout_registry.layouts_dir / layout_info.name / file_name)

        except Exception as e:
            logger.debug(f"Failed to get CSS path for layout '{layout_name}': {e}")
            return None

    def get_js_path(self, layout_name: str) -> Optional[Path]:
        """Get single JavaScript path for a layout.

        Args:
            layout_name: Name of layout to get JS path for.

        Returns:
            Path to first JavaScript file for the layout, or None if no JS files
            or if the first file is an external URL.
        """
        try:
            layout_info = self.layout_registry.get_layout_with_fallback(layout_name)
            js_files = layout_info.resources.get("js", [])

            if not js_files:
                return None

            first_js = js_files[0]

            # Handle both string and object formats
            file_name = first_js.get("file", "") if isinstance(first_js, dict) else first_js

            # Skip external URLs or invalid entries
            if not file_name or not isinstance(file_name, str) or file_name.startswith("http"):
                return None

            # Return path to first JS file
            return Path(self.layout_registry.layouts_dir / layout_info.name / file_name)

        except Exception as e:
            logger.debug(f"Failed to get JS path for layout '{layout_name}': {e}")
            return None

    def clear_cache(self) -> None:
        """Clear resource cache."""
        self._resource_cache.clear()
        self._css_cache.clear()
        self._js_cache.clear()
        logger.debug("Resource cache cleared")

    def get_layout_base_path(self, layout_name: str) -> str:
        """Get base path for layout resources.

        Args:
            layout_name: Name of layout.

        Returns:
            Base path for layout resources.
        """
        return f"{self.base_url}/layouts/{layout_name}"

    def validate_layout_resources(self, layout_name: str) -> dict[str, bool]:
        """Validate that layout resources exist.

        Args:
            layout_name: Name of layout to validate.

        Returns:
            Dictionary with validation results for each resource type.
        """
        validation_results = {"css_valid": True, "js_valid": True, "layout_exists": False}

        try:
            layout_info = self.layout_registry.get_layout_info(layout_name)
            if layout_info is None:
                return validation_results

            validation_results["layout_exists"] = True

            # Check if resource files exist (simplified validation)
            layouts_dir = self.layout_registry.layouts_dir
            layout_dir = layouts_dir / layout_name

            if layout_dir.exists():
                # Validate CSS files
                css_files = layout_info.resources.get("css", [])
                for css_file in css_files:
                    # Handle both string and object formats
                    file_name = css_file.get("file", "") if isinstance(css_file, dict) else css_file

                    if (
                        file_name
                        and isinstance(file_name, str)
                        and not file_name.startswith("http")
                    ):
                        css_path = layout_dir / file_name
                        if not css_path.exists():
                            validation_results["css_valid"] = False
                            break

                # Validate JS files
                js_files = layout_info.resources.get("js", [])
                for js_file in js_files:
                    # Handle both string and object formats
                    file_name = js_file.get("file", "") if isinstance(js_file, dict) else js_file

                    if (
                        file_name
                        and isinstance(file_name, str)
                        and not file_name.startswith("http")
                    ):
                        js_path = layout_dir / file_name
                        if not js_path.exists():
                            validation_results["js_valid"] = False
                            break
            else:
                validation_results["css_valid"] = False
                validation_results["js_valid"] = False

        except Exception:
            logger.exception(f"Error validating resources for layout '{layout_name}'")
            validation_results["css_valid"] = False
            validation_results["js_valid"] = False

        return validation_results
