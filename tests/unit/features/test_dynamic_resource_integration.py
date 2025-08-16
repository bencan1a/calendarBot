"""Tests for dynamic resource loading integration with the layout-renderer architecture."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from calendarbot.display.html_renderer import HTMLRenderer
from calendarbot.layout.registry import LayoutRegistry
from calendarbot.layout.resource_manager import ResourceManager


class TestDynamicResourceIntegration:
    """Test integration between ResourceManager and HTMLRenderer."""

    @pytest.fixture
    def mock_layout_registry(self) -> Mock:
        """Create a mock layout registry with realistic data."""
        registry = Mock(spec=LayoutRegistry)

        # Mock layout info for 4x8
        layout_4x8 = Mock()
        layout_4x8.name = "4x8"
        layout_4x8.resources = {"css": ["4x8.css", "common.css"], "js": ["4x8.js", "navigation.js"]}

        # Mock layout info for whats-next-view
        layout_whats_next = Mock()
        layout_whats_next.name = "whats-next-view"
        layout_whats_next.resources = {"css": ["whats-next-view.css"], "js": ["whats-next-view.js"]}

        registry.get_layout_with_fallback.side_effect = lambda name: {
            "4x8": layout_4x8,
            "whats-next-view": layout_whats_next,
        }.get(name, layout_4x8)  # Default to 4x8

        registry.layouts_dir = Path("/test/layouts")

        return registry

    @pytest.fixture
    def resource_manager(self, mock_layout_registry: Mock) -> ResourceManager:
        """Create ResourceManager with mock registry."""
        return ResourceManager(mock_layout_registry)

    def test_html_renderer_with_working_resource_manager(self, mock_layout_registry: Mock) -> None:
        """Test HTMLRenderer when ResourceManager works correctly."""
        settings = Mock()
        settings.web_layout = "4x8"

        with patch(
            "calendarbot.display.html_renderer.LayoutRegistry", return_value=mock_layout_registry
        ):
            renderer = HTMLRenderer(settings)

            # Mock _get_dynamic_resources to return the expected values
            with patch.object(
                renderer, "_get_dynamic_resources", return_value=(["4x8.css"], ["4x8.js"])
            ):
                result = renderer._build_html_template(
                    display_date="Test Date",
                    status_line="Test Status",
                    events_content="<div>Test Events</div>",
                    nav_help="<div>Test Nav</div>",
                    interactive_mode=True,
                )

                assert "4x8.css" in result
                assert "4x8.js" in result
                assert "Test Date" in result

    def test_html_renderer_with_failing_resource_manager(self) -> None:
        """Test HTMLRenderer gracefully handles ResourceManager failure."""
        settings = Mock()
        settings.web_layout = "4x8"

        # Mock ResourceManager to fail during initialization
        with patch(
            "calendarbot.display.html_renderer.ResourceManager",
            side_effect=Exception("Resource manager failed"),
        ):
            renderer = HTMLRenderer(settings)

            # Should still work with fallback
            result = renderer._build_html_template(
                display_date="Test Date",
                status_line="Test Status",
                events_content="<div>Test Events</div>",
                nav_help="<div>Test Nav</div>",
                interactive_mode=True,
            )

            # Should fall back to theme-based CSS/JS
            assert "4x8.css" in result
            assert "4x8.js" in result

    def test_resource_manager_url_methods_integration(
        self, resource_manager: ResourceManager
    ) -> None:
        """Test ResourceManager get_css_urls and get_js_urls methods."""
        css_urls = resource_manager.get_css_urls("4x8")
        js_urls = resource_manager.get_js_urls("4x8")

        expected_css_urls = ["/static/layouts/4x8/4x8.css", "/static/layouts/4x8/common.css"]
        expected_js_urls = ["/static/layouts/4x8/4x8.js", "/static/layouts/4x8/navigation.js"]

        assert css_urls == expected_css_urls
        assert js_urls == expected_js_urls

    @pytest.mark.parametrize(
        "layout_name,expected_css,expected_js",
        [
            ("4x8", "4x8.css", "4x8.js"),
            ("whats-next-view", "whats-next-view.css", "whats-next-view.js"),
            ("unknown", "4x8.css", "4x8.js"),  # Should fallback to 4x8
        ],
    )
    def test_renderer_layout_fallback(
        self, mock_layout_registry: Mock, layout_name: str, expected_css: str, expected_js: str
    ) -> None:
        """Test that HTMLRenderer properly handles different layouts and fallbacks."""
        settings = Mock()
        settings.web_layout = layout_name

        with patch(
            "calendarbot.display.html_renderer.LayoutRegistry", return_value=mock_layout_registry
        ):
            renderer = HTMLRenderer(settings)

            # Get resources using the actual method
            css_files, js_files = renderer._get_dynamic_resources()

            # Check if expected file is in the returned list
            assert any(expected_css in css_file for css_file in css_files)
            assert any(expected_js in js_file for js_file in js_files)


class TestLayoutRendererSeparation:
    """Test that layouts work independently of renderers."""

    @pytest.fixture
    def mock_settings_4x8(self) -> Mock:
        """Mock settings with 4x8 layout."""
        settings = Mock()
        settings.web_layout = "4x8"
        return settings

    @pytest.fixture
    def mock_settings_whats_next(self) -> Mock:
        """Mock settings with whats-next-view layout."""
        settings = Mock()
        settings.web_layout = "whats-next-view"
        return settings

    def test_html_renderer_works_with_any_layout(
        self, mock_settings_4x8: Mock, mock_settings_whats_next: Mock
    ) -> None:
        """Test that HTMLRenderer works with different layout configurations."""
        # Test with 4x8 layout
        renderer_4x8 = HTMLRenderer(mock_settings_4x8)
        assert renderer_4x8.layout == "4x8"

        # Test with whats-next-view layout
        renderer_whats_next = HTMLRenderer(mock_settings_whats_next)
        assert renderer_whats_next.layout == "whats-next-view"

    def test_layout_specific_resources_are_loaded(
        self, mock_settings_4x8: Mock, mock_settings_whats_next: Mock
    ) -> None:
        """Test that layout-specific resources are correctly loaded."""
        renderer_4x8 = HTMLRenderer(mock_settings_4x8)
        renderer_whats_next = HTMLRenderer(mock_settings_whats_next)

        # Test fallback CSS file selection
        css_4x8 = renderer_4x8._get_fallback_css_file()
        css_whats_next = renderer_whats_next._get_fallback_css_file()

        assert css_4x8 == "4x8.css"
        assert css_whats_next == "4x8.css"  # whats-next-view falls back to 4x8.css

        # Test fallback JS file selection
        js_4x8 = renderer_4x8._get_fallback_js_file()
        js_whats_next = renderer_whats_next._get_fallback_js_file()

        assert js_4x8 == "4x8.js"
        assert js_whats_next == "whats-next-view.js"

    def test_html_output_includes_layout_class(
        self, mock_settings_4x8: Mock, mock_settings_whats_next: Mock
    ) -> None:
        """Test that HTML output includes correct layout CSS class."""
        renderer_4x8 = HTMLRenderer(mock_settings_4x8)
        renderer_whats_next = HTMLRenderer(mock_settings_whats_next)

        html_4x8 = renderer_4x8._build_html_template(
            display_date="Test",
            status_line="",
            events_content="<div>Content</div>",
            nav_help="",
            interactive_mode=False,
        )

        html_whats_next = renderer_whats_next._build_html_template(
            display_date="Test",
            status_line="",
            events_content="<div>Content</div>",
            nav_help="",
            interactive_mode=False,
        )

        assert 'class="layout-4x8"' in html_4x8
        assert 'class="layout-whats-next-view"' in html_whats_next


class TestResourceManagerErrorHandling:
    """Test ResourceManager error handling and fallback mechanisms."""

    def test_resource_manager_handles_missing_layout_gracefully(self) -> None:
        """Test ResourceManager handles missing layouts gracefully."""
        mock_registry = Mock()
        mock_registry.get_layout_with_fallback.side_effect = Exception("Layout not found")

        resource_manager = ResourceManager(mock_registry)

        # Should return empty lists instead of raising exception
        css_urls = resource_manager.get_css_urls("nonexistent")
        js_urls = resource_manager.get_js_urls("nonexistent")

        assert css_urls == []
        assert js_urls == []

    def test_resource_manager_handles_malformed_layout_data(self) -> None:
        """Test ResourceManager handles malformed layout data gracefully."""
        mock_registry = Mock()

        # Mock layout with malformed resources
        malformed_layout = Mock()
        malformed_layout.name = "malformed"
        malformed_layout.resources = "not a dict"  # Should be a dict

        mock_registry.get_layout_with_fallback.return_value = malformed_layout

        resource_manager = ResourceManager(mock_registry)

        # Should handle gracefully by falling back to legacy URLs
        css_urls = resource_manager.get_css_urls("malformed")
        js_urls = resource_manager.get_js_urls("malformed")

        # Should fall back to empty lists for unknown layout
        assert css_urls == []
        assert js_urls == []

    def test_html_renderer_resilience_to_resource_manager_failures(self) -> None:
        """Test HTMLRenderer remains functional when ResourceManager fails."""
        settings = Mock()
        settings.web_layout = "4x8"

        # Force ResourceManager initialization to fail
        with patch(
            "calendarbot.display.html_renderer.ResourceManager",
            side_effect=Exception("Init failed"),
        ):
            renderer = HTMLRenderer(settings)

            # Renderer should still be functional
            assert renderer.layout == "4x8"
            assert renderer.resource_manager is None

            # Should still be able to render
            result = renderer.render_events([])
            assert "<!DOCTYPE html>" in result
            assert "4x8.css" in result  # Should use fallback
