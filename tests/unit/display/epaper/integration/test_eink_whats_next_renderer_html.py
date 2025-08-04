"""
Unit tests for the HTML-to-PNG conversion functionality in EInkWhatsNextRenderer.

These tests verify that the HTML-to-PNG conversion features in EInkWhatsNextRenderer
work correctly, including:
- HTML rendering using WhatsNextRenderer
- HTML-to-PNG conversion using html2image
- Caching of rendered HTML
- Fallback to PIL rendering when HTML-to-PNG is not available
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from PIL import Image

from calendarbot.display.epaper.integration.eink_whats_next_renderer import (
    EInkWhatsNextRenderer,
    HTML2IMAGE_AVAILABLE
)
from calendarbot.display.epaper.utils.html_to_png import HtmlToPngConverter
from tests.unit.display.epaper.integration.test_eink_whats_next_renderer_core import (
    MockDisplay,
    MockEvent,
    MockViewModel,
    MockStatusInfo
)


@pytest.fixture
def mock_settings():
    """Fixture for mock settings."""
    return {"display": {"type": "epaper"}}


@pytest.fixture
def mock_display():
    """Fixture for mock display."""
    return MockDisplay()


@pytest.fixture
def mock_view_model():
    """Fixture for mock view model with events."""
    current_event = MockEvent(
        subject="Current Meeting",
        time_until_minutes=0,
        location="Conference Room A",
        is_current=True,
        is_upcoming=False
    )
    next_event = MockEvent(
        subject="Next Meeting",
        time_until_minutes=30,
        location="Conference Room B",
        is_current=False,
        is_upcoming=True
    )
    later_event = MockEvent(
        subject="Later Meeting",
        time_until_minutes=120,
        location="Conference Room C",
        is_current=False,
        is_upcoming=True
    )
    
    # Create a proper status info object
    status_info = MockStatusInfo(
        is_cached=False,
        connection_status="connected",
        relative_description="now",
        interactive_mode=False,
        selected_date=None
    )
    
    return MockViewModel(
        current_events=[current_event],
        next_events=[next_event],
        later_events=[later_event],
        current_time=datetime.now(),
        status_info=status_info
    )


@pytest.fixture
def mock_html_converter():
    """Fixture for mock HTML-to-PNG converter."""
    mock_converter = MagicMock(spec=HtmlToPngConverter)
    
    # Configure the mock to return a valid PNG path
    temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    temp_file.close()
    
    # Create a small test image
    test_image = Image.new("RGB", (100, 100), color="white")
    test_image.save(temp_file.name)
    
    mock_converter.convert_html_to_png.return_value = temp_file.name
    
    yield mock_converter
    
    # Clean up the temporary file
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


class TestEInkWhatsNextRendererHtml:
    """Test suite for HTML-to-PNG conversion in EInkWhatsNextRenderer."""
    
    def test_init_when_html2image_available_then_initializes_converter(
        self, mock_settings, mock_display
    ):
        """Test initialization creates HTML converter when html2image is available."""
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.HTML2IMAGE_AVAILABLE", True):
            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.create_converter") as mock_create:
                # Configure the mock to return a valid converter
                mock_converter = MagicMock()
                mock_create.return_value = mock_converter
                
                # Initialize the renderer
                renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
                
                # Verify converter was created
                mock_create.assert_called_once()
                assert renderer.html_converter is mock_converter
    
    def test_init_when_html2image_not_available_then_converter_is_none(
        self, mock_settings, mock_display
    ):
        """Test initialization sets converter to None when html2image is not available."""
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.HTML2IMAGE_AVAILABLE", False):
            # Initialize the renderer
            renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
            
            # Verify converter is None
            assert renderer.html_converter is None
    
    def test_render_when_html_converter_available_then_uses_html_conversion(
        self, mock_settings, mock_display, mock_view_model, mock_html_converter
    ):
        """Test render method uses HTML conversion when converter is available."""
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.HTML2IMAGE_AVAILABLE", True):
            # Initialize the renderer with mock converter
            renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
            renderer.html_converter = mock_html_converter
            
            # Mock the HTML renderer
            renderer.html_renderer = MagicMock()
            renderer.html_renderer.render.return_value = "<html><body>Test</body></html>"
            
            # Call render
            result = renderer.render(mock_view_model)
            
            # Verify HTML renderer was used
            renderer.html_renderer.render.assert_called_once_with(mock_view_model)
            
            # Verify HTML-to-PNG conversion was used
            mock_html_converter.convert_html_to_png.assert_called_once()
            
            # Verify result is a PIL Image
            assert isinstance(result, Image.Image)
    
    def test_render_when_html_converter_not_available_then_falls_back_to_pil(
        self, mock_settings, mock_display, mock_view_model
    ):
        """Test render method falls back to PIL rendering when converter is not available."""
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.HTML2IMAGE_AVAILABLE", False):
            # Initialize the renderer
            renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
            
            # Mock the _render_full_image method
            renderer._render_full_image = MagicMock()
            mock_image = Image.new("L", (100, 100))
            renderer._render_full_image.return_value = mock_image
            
            # Call render
            result = renderer.render(mock_view_model)
            
            # Verify _render_full_image was called
            renderer._render_full_image.assert_called_once_with(mock_view_model)
            
            # Verify result is the mock image
            assert result is mock_image
    
    def test_render_using_html_conversion_when_converter_none_then_falls_back_to_pil(
        self, mock_settings, mock_display, mock_view_model
    ):
        """Test _render_using_html_conversion falls back to PIL when converter is None."""
        # Initialize the renderer
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        renderer.html_converter = None
        
        # Mock the _render_full_image method
        renderer._render_full_image = MagicMock()
        mock_image = Image.new("L", (100, 100))
        renderer._render_full_image.return_value = mock_image
        
        # Call _render_using_html_conversion
        result = renderer._render_using_html_conversion(mock_view_model)
        
        # Verify _render_full_image was called
        renderer._render_full_image.assert_called_once_with(mock_view_model)
        
        # Verify result is the mock image
        assert result is mock_image
    
    def test_render_using_html_conversion_when_cached_then_uses_cache(
        self, mock_settings, mock_display, mock_view_model
    ):
        """Test _render_using_html_conversion uses cached render when available."""
        # Initialize the renderer
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        # Create a mock cache entry
        cache_key = "test_cache_key"
        
        # Create a temporary file for the cached image
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_file.close()
        
        # Create a small test image
        test_image = Image.new("RGB", (100, 100), color="white")
        test_image.save(temp_file.name)
        
        # Add to cache
        renderer._html_render_cache[cache_key] = (temp_file.name, datetime.now())
        
        # Mock the _generate_cache_key method
        renderer._generate_cache_key = MagicMock(return_value=cache_key)
        
        # Call _render_using_html_conversion
        with patch("PIL.Image.open", return_value=test_image) as mock_open:
            result = renderer._render_using_html_conversion(mock_view_model)
            
            # Verify Image.open was called with the cached path
            mock_open.assert_called_once_with(temp_file.name)
            
            # Verify result is an Image
            assert isinstance(result, Image.Image)
        
        # Clean up
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
    
    def test_render_using_html_conversion_when_conversion_fails_then_falls_back_to_pil(
        self, mock_settings, mock_display, mock_view_model, mock_html_converter
    ):
        """Test _render_using_html_conversion falls back to PIL when conversion fails."""
        # Initialize the renderer
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        renderer.html_converter = mock_html_converter
        
        # Configure the mock to simulate failure
        mock_html_converter.convert_html_to_png.return_value = None
        
        # Mock the HTML renderer
        renderer.html_renderer = MagicMock()
        renderer.html_renderer.render.return_value = "<html><body>Test</body></html>"
        
        # Mock the _render_full_image method
        renderer._render_full_image = MagicMock()
        mock_image = Image.new("L", (100, 100))
        renderer._render_full_image.return_value = mock_image
        
        # Call _render_using_html_conversion
        result = renderer._render_using_html_conversion(mock_view_model)
        
        # Verify _render_full_image was called
        renderer._render_full_image.assert_called_once_with(mock_view_model)
        
        # Verify result is the mock image
        assert result is mock_image
    
    def test_cleanup_when_called_then_cleans_up_resources(
        self, mock_settings, mock_display, mock_html_converter
    ):
        """Test cleanup method cleans up resources."""
        # Initialize the renderer
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        renderer.html_converter = mock_html_converter
        
        # Create a mock temp directory
        temp_dir = tempfile.mkdtemp()
        renderer.temp_dir = Path(temp_dir)
        
        # Call cleanup
        renderer.cleanup()
        
        # Verify converter cleanup was called
        mock_html_converter.cleanup.assert_called_once()
        
        # Clean up the temporary directory
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)