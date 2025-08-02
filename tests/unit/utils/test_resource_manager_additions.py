"""Additional tests for calendarbot.layout.resource_manager module to improve coverage."""

from pathlib import Path
from unittest.mock import Mock, patch, call

import pytest

from calendarbot.layout.exceptions import LayoutNotFoundError, ResourceLoadingError
from calendarbot.layout.resource_manager import ResourceManager


class TestResourceManagerURLMethods:
    """Test URL generation methods with various edge cases."""

    @pytest.fixture
    def mock_layout_info(self):
        """Create mock layout info with various resource formats."""
        layout_info = Mock()
        layout_info.name = "test-layout"
        layout_info.resources = {
            "css": [
                "style.css",                                # String format
                {"file": "theme.css"},                      # Object format
                {"file": ""},                               # Empty file name
                {"wrong_key": "wrong.css"},                 # Missing file key
                None,                                       # None entry
                {"file": None},                             # None file name
                {"file": 123},                              # Non-string file name
                "https://cdn.example.com/external.css",     # External URL
            ],
            "js": [
                "script.js",                                # String format
                {"file": "utils.js"},                       # Object format
                {"file": ""},                               # Empty file name
                {"wrong_key": "wrong.js"},                  # Missing file key
                None,                                       # None entry
                {"file": None},                             # None file name
                {"file": 123},                              # Non-string file name
                "https://cdn.example.com/external.js",      # External URL
            ]
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

    def test_get_css_urls_handles_various_formats(self, resource_manager, mock_registry, mock_layout_info):
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

    def test_get_js_urls_handles_various_formats(self, resource_manager, mock_registry, mock_layout_info):
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
        layout_info.resources = {
            "css": ["style.css", "theme.css"],
            "js": ["script.js", "utils.js"]
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
        with patch.object(resource_manager, 'get_css_urls') as mock_get_css_urls:
            with patch.object(resource_manager, 'get_js_urls') as mock_get_js_urls:
                mock_get_css_urls.return_value = ["/static/layouts/test-layout/style.css"]
                mock_get_js_urls.return_value = ["/static/layouts/test-layout/script.js"]
                
                result = resource_manager.inject_layout_resources(template, "test-layout")
                
                # Should call URL methods with correct layout name
                mock_get_css_urls.assert_called_with("test-layout")
                mock_get_js_urls.assert_called_with("test-layout")
                
                # Should inject CSS links before </head>
                assert '<link rel="stylesheet" type="text/css" href="/static/shared/css/settings-panel.css">' in result
                assert '<link rel="stylesheet" type="text/css" href="/static/layouts/test-layout/style.css">' in result
                
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
        with patch.object(resource_manager, 'get_css_urls') as mock_get_css_urls:
            with patch.object(resource_manager, 'get_js_urls') as mock_get_js_urls:
                mock_get_css_urls.return_value = ["/static/layouts/test-layout/style.css"]
                mock_get_js_urls.return_value = ["/static/layouts/test-layout/script.js"]
                
                result = resource_manager.inject_layout_resources(template, "test-layout")
                
                # Should return template unchanged
                assert result == template

    def test_inject_layout_resources_when_exception_then_raises_resource_loading_error(self, resource_manager):
        """Test inject_layout_resources raises ResourceLoadingError on exception."""
        template = "<html><head></head><body></body></html>"
        
        # Patch get_css_urls to raise an exception
        with patch.object(resource_manager, 'get_css_urls', side_effect=Exception("Test error")):
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
        with patch.object(resource_manager, 'get_css_urls') as mock_get_css_urls:
            with patch.object(resource_manager, 'get_js_urls') as mock_get_js_urls:
                mock_get_css_urls.side_effect = lambda layout: [f"/static/layouts/{layout}/style.css"]
                mock_get_js_urls.side_effect = lambda layout: [f"/static/layouts/{layout}/script.js"]
                
                # Preload multiple layouts
                resource_manager.preload_resources(["layout1", "layout2", "layout3"])
                
                # Should call URL methods for each layout
                assert mock_get_css_urls.call_count == 3
                assert mock_get_js_urls.call_count == 3
                
                # Should cache resources for each layout
                assert len(resource_manager._resource_cache) == 3
                assert resource_manager._resource_cache["layout1"] == {
                    "css": ["/static/layouts/layout1/style.css"],
                    "js": ["/static/layouts/layout1/script.js"]
                }
                assert resource_manager._resource_cache["layout2"] == {
                    "css": ["/static/layouts/layout2/style.css"],
                    "js": ["/static/layouts/layout2/script.js"]
                }
                assert resource_manager._resource_cache["layout3"] == {
                    "css": ["/static/layouts/layout3/style.css"],
                    "js": ["/static/layouts/layout3/script.js"]
                }

    def test_preload_resources_handles_exceptions_gracefully(self, resource_manager):
        """Test preload_resources handles exceptions for individual layouts gracefully."""
        # Patch get_css_urls to raise exception for specific layout
        with patch.object(resource_manager, 'get_css_urls') as mock_get_css_urls:
            with patch.object(resource_manager, 'get_js_urls') as mock_get_js_urls:
                mock_get_css_urls.side_effect = lambda layout: (
                    [f"/static/layouts/{layout}/style.css"] if layout != "layout2" 
                    else (_ for _ in ()).throw(Exception("Test error"))  # Raise exception for layout2
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