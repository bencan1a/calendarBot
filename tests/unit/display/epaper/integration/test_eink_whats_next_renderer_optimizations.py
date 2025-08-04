"""
Unit tests for EInkWhatsNextRenderer optimizations.

These tests verify that the optimization features in EInkWhatsNextRenderer
work correctly, including:
- Font caching with LRU eviction
- Text measurement caching
- Image buffer pooling
- Performance monitoring integration
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Any, Dict, Generator, List, Optional, Tuple, Union, cast
from collections import OrderedDict

from PIL import Image, ImageDraw, ImageFont

from calendarbot.display.epaper.integration.eink_whats_next_renderer import (
    EInkWhatsNextRenderer,
    MAX_FONT_CACHE_SIZE,
    MAX_TEXT_MEASURE_CACHE_SIZE,
    BUFFER_POOL_SIZE
)
from calendarbot.display.epaper.abstraction import DisplayAbstractionLayer
from calendarbot.display.epaper.capabilities import DisplayCapabilities
from calendarbot.display.epaper.utils.performance import PerformanceMetrics


class MockDisplayCapabilities(DisplayCapabilities):
    """Mock display capabilities for testing."""
    
    def __init__(
        self,
        width: int = 400,
        height: int = 300,
        supports_partial_update: bool = True,
        supports_grayscale: bool = True,
        supports_red: bool = False
    ) -> None:
        """Initialize mock display capabilities."""
        super().__init__(
            width=width,
            height=height,
            colors=2 if supports_grayscale else 1,
            supports_partial_update=supports_partial_update,
            supports_grayscale=supports_grayscale,
            supports_red=supports_red
        )


class MockDisplay(DisplayAbstractionLayer):
    """Mock display for testing."""
    
    def __init__(self, capabilities: Optional[MockDisplayCapabilities] = None) -> None:
        """Initialize mock display."""
        self.capabilities = capabilities or MockDisplayCapabilities()
        self.initialize_called = False
        self.render_called = False
        self.render_buffer = None
    
    def initialize(self) -> bool:
        """Mock initialize method."""
        self.initialize_called = True
        return True
    
    def render(self, content: Any) -> bool:
        """Mock render method."""
        self.render_called = True
        self.render_buffer = content
        return True
    
    def get_capabilities(self) -> DisplayCapabilities:
        """Get display capabilities."""
        return self.capabilities
        
    def clear(self) -> bool:
        """Mock clear method."""
        return True
        
    def shutdown(self) -> bool:
        """Mock shutdown method."""
        return True


@pytest.fixture
def mock_display() -> MockDisplay:
    """Fixture for mock display."""
    return MockDisplay()


@pytest.fixture
def mock_settings() -> Dict[str, Any]:
    """Fixture for mock settings."""
    return {"display": {"type": "epaper"}}


@pytest.fixture
def mock_image_font() -> MagicMock:
    """Fixture for mock ImageFont."""
    mock_font = MagicMock(spec=ImageFont.FreeTypeFont)
    return mock_font


@pytest.fixture
def mock_renderer(mock_settings: Dict[str, Any], mock_display: MockDisplay) -> Generator[EInkWhatsNextRenderer, None, None]:
    """Fixture for EInkWhatsNextRenderer with mocked dependencies."""
    with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.get_colors_for_renderer") as mock_get_colors:
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.get_typography_for_renderer") as mock_get_typography:
            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.get_layout_for_renderer") as mock_get_layout:
                # Mock the color, typography, and layout functions
                mock_get_colors.return_value = {
                    "background": 255,
                    "background_secondary": 245,
                    "text_primary": 0,
                    "text_secondary": 100,
                    "text_supporting": 173,
                    "accent": 50,
                    "urgent": 76
                }
                mock_get_typography.return_value = {
                    "countdown": 30,
                    "title": 24,
                    "subtitle": 18,
                    "body": 14,
                    "small": 12
                }
                mock_get_layout.return_value = {
                    "width": 400,
                    "height": 300
                }
                
                # Initialize the renderer
                renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
                
                # Replace the actual font loading with mocks
                with patch.object(renderer, "_load_fonts", return_value={}):
                    yield renderer


class TestEInkWhatsNextRendererOptimizations:
    """Test suite for EInkWhatsNextRenderer optimizations."""

    def test_init_when_created_then_initializes_optimization_structures(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test initialization creates optimization structures."""
        # Check font cache
        assert hasattr(mock_renderer, "_font_cache")
        assert isinstance(mock_renderer._font_cache, OrderedDict)
        assert len(mock_renderer._font_cache) == 0
        
        # Check text measurement cache
        assert hasattr(mock_renderer, "_text_measure_cache")
        assert isinstance(mock_renderer._text_measure_cache, OrderedDict)
        assert len(mock_renderer._text_measure_cache) == 0
        
        # Check image buffer pool
        assert hasattr(mock_renderer, "_image_buffer_pool")
        assert isinstance(mock_renderer._image_buffer_pool, dict)
        assert len(mock_renderer._image_buffer_pool) == 0
        
        # Check performance metrics
        assert hasattr(mock_renderer, "performance")
        assert isinstance(mock_renderer.performance, PerformanceMetrics)

    def test_get_font_when_font_not_in_cache_then_loads_font(
        self, mock_renderer: EInkWhatsNextRenderer, mock_image_font: MagicMock
    ) -> None:
        """Test _get_font loads font when not in cache."""
        with patch("PIL.ImageFont.truetype", return_value=mock_image_font):
            font = mock_renderer._get_font("title")
            
            # Check that the font was loaded and cached
            assert font is mock_image_font
            assert "title" in mock_renderer._font_cache
            assert mock_renderer._font_cache["title"] is mock_image_font

    def test_get_font_when_font_in_cache_then_returns_cached_font(
        self, mock_renderer: EInkWhatsNextRenderer, mock_image_font: MagicMock
    ) -> None:
        """Test _get_font returns cached font when available."""
        # Add font to cache
        mock_renderer._font_cache["title"] = mock_image_font
        
        # Get font from cache
        font = mock_renderer._get_font("title")
        
        # Check that the cached font was returned
        assert font is mock_image_font
        
        # Verify no font loading occurred
        with patch("PIL.ImageFont.truetype") as mock_truetype:
            font = mock_renderer._get_font("title")
            mock_truetype.assert_not_called()

    def test_get_font_when_cache_full_then_evicts_least_recently_used(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _get_font evicts least recently used font when cache is full."""
        # Fill the cache to capacity
        mock_fonts = {}
        for i in range(MAX_FONT_CACHE_SIZE):
            font_key = f"font{i}"
            mock_font = MagicMock(spec=ImageFont.FreeTypeFont)
            mock_renderer._font_cache[font_key] = mock_font
            mock_fonts[font_key] = mock_font
        
        # Verify cache is at capacity
        assert len(mock_renderer._font_cache) == MAX_FONT_CACHE_SIZE
        
        # Add one more font, which should evict the least recently used
        with patch("PIL.ImageFont.truetype") as mock_truetype:
            new_mock_font = MagicMock(spec=ImageFont.FreeTypeFont)
            mock_truetype.return_value = new_mock_font
            
            # Mock the typography dictionary to include the new font
            with patch.object(mock_renderer, "_typography",
                             {"countdown": 30, "title": 24, "subtitle": 18, "body": 14, "small": 12, "new_font": 16}):
                mock_renderer._get_font("new_font")
                
                # Verify cache size hasn't changed
                assert len(mock_renderer._font_cache) == MAX_FONT_CACHE_SIZE
                
                # Verify the new font is in the cache
                assert "new_font" in mock_renderer._font_cache
                
                # Verify the least recently used font (font0) is no longer in the cache
                assert "font0" not in mock_renderer._font_cache

    def test_get_text_bbox_when_not_in_cache_then_calculates_bbox(
        self, mock_renderer: EInkWhatsNextRenderer, mock_image_font: MagicMock
    ) -> None:
        """Test _get_text_bbox calculates bbox when not in cache."""
        # Mock the font retrieval
        with patch.object(mock_renderer, "_get_font", return_value=mock_image_font):
            # Mock the draw.textbbox method
            mock_draw = MagicMock(spec=ImageDraw.ImageDraw)
            mock_draw.textbbox.return_value = (0, 0, 100, 20)
            
            # Get text bbox
            bbox = mock_renderer._get_text_bbox(mock_draw, "test text", "title")
            
            # Verify bbox was calculated and cached
            assert bbox == (0, 0, 100, 20)
            assert len(mock_renderer._text_measure_cache) == 1
            mock_draw.textbbox.assert_called_once()

    def test_get_text_bbox_when_in_cache_then_returns_cached_bbox(
        self, mock_renderer: EInkWhatsNextRenderer, mock_image_font: MagicMock
    ) -> None:
        """Test _get_text_bbox returns cached bbox when available."""
        # Mock the font retrieval
        with patch.object(mock_renderer, "_get_font", return_value=mock_image_font):
            # Create a cache key
            cache_key = ("test text", "title", id(mock_image_font))
            
            # Add bbox to cache
            mock_renderer._text_measure_cache[cache_key] = (0, 0, 100, 20)
            
            # Mock the draw.textbbox method
            mock_draw = MagicMock(spec=ImageDraw.ImageDraw)
            
            # Get text bbox
            bbox = mock_renderer._get_text_bbox(mock_draw, "test text", "title")
            
            # Verify cached bbox was returned
            assert bbox == (0, 0, 100, 20)
            
            # Verify textbbox was not called
            mock_draw.textbbox.assert_not_called()

    def test_get_text_bbox_when_cache_full_then_evicts_least_recently_used(
        self, mock_renderer: EInkWhatsNextRenderer, mock_image_font: MagicMock
    ) -> None:
        """Test _get_text_bbox evicts least recently used bbox when cache is full."""
        # Mock the font retrieval
        with patch.object(mock_renderer, "_get_font", return_value=mock_image_font):
            # Fill the cache to capacity
            for i in range(MAX_TEXT_MEASURE_CACHE_SIZE):
                cache_key = (f"text{i}", "title", id(mock_image_font))
                mock_renderer._text_measure_cache[cache_key] = (0, 0, 100, 20)
            
            # Verify cache is at capacity
            assert len(mock_renderer._text_measure_cache) == MAX_TEXT_MEASURE_CACHE_SIZE
            
            # Mock the draw.textbbox method
            mock_draw = MagicMock(spec=ImageDraw.ImageDraw)
            mock_draw.textbbox.return_value = (0, 0, 200, 40)
            
            # Get text bbox for new text
            bbox = mock_renderer._get_text_bbox(mock_draw, "new text", "title")
            
            # Verify bbox was calculated and cached
            assert bbox == (0, 0, 200, 40)
            
            # Verify cache size hasn't changed
            assert len(mock_renderer._text_measure_cache) == MAX_TEXT_MEASURE_CACHE_SIZE
            
            # Verify the least recently used bbox is no longer in the cache
            first_key = ("text0", "title", id(mock_image_font))
            assert first_key not in mock_renderer._text_measure_cache

    def test_get_image_buffer_when_not_in_pool_then_creates_new_buffer(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _get_image_buffer creates new buffer when not in pool."""
        # Get a new image buffer
        image = mock_renderer._get_image_buffer("L", 400, 300)
        
        # Verify a new image was created
        assert isinstance(image, Image.Image)
        assert image.mode == "L"
        assert image.width == 400
        assert image.height == 300

    def test_get_image_buffer_when_in_pool_then_returns_from_pool(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _get_image_buffer returns buffer from pool when available."""
        # Create a mock image
        mock_image = MagicMock(spec=Image.Image)
        mock_image.mode = "L"
        mock_image.width = 400
        mock_image.height = 300
        
        # Add image to pool
        buffer_key = ("L", 400, 300)
        mock_renderer._image_buffer_pool[buffer_key] = [mock_image]
        
        # Get image buffer
        with patch("PIL.Image.new") as mock_new:
            image = mock_renderer._get_image_buffer("L", 400, 300)
            
            # Verify image was returned from pool
            assert image is mock_image
            
            # Verify new image was not created
            mock_new.assert_not_called()
            
            # Verify pool is now empty
            assert len(mock_renderer._image_buffer_pool[buffer_key]) == 0

    def test_recycle_image_buffer_when_pool_not_full_then_adds_to_pool(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _recycle_image_buffer adds buffer to pool when not full."""
        # Create a mock image
        mock_image = MagicMock(spec=Image.Image)
        mock_image.mode = "L"
        mock_image.width = 400
        mock_image.height = 300
        
        # Recycle image buffer
        mock_renderer._recycle_image_buffer(mock_image)
        
        # Verify image was added to pool
        buffer_key = ("L", 400, 300)
        assert buffer_key in mock_renderer._image_buffer_pool
        assert len(mock_renderer._image_buffer_pool[buffer_key]) == 1
        assert mock_renderer._image_buffer_pool[buffer_key][0] is mock_image

    def test_recycle_image_buffer_when_pool_full_then_discards_buffer(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test _recycle_image_buffer discards buffer when pool is full."""
        # Create mock images
        mock_images = []
        for i in range(BUFFER_POOL_SIZE):
            mock_image = MagicMock(spec=Image.Image)
            mock_image.mode = "L"
            mock_image.width = 400
            mock_image.height = 300
            mock_images.append(mock_image)
        
        # Fill the pool to capacity
        buffer_key = ("L", 400, 300)
        mock_renderer._image_buffer_pool[buffer_key] = mock_images.copy()
        
        # Create one more image
        new_mock_image = MagicMock(spec=Image.Image)
        new_mock_image.mode = "L"
        new_mock_image.width = 400
        new_mock_image.height = 300
        
        # Recycle the new image
        mock_renderer._recycle_image_buffer(new_mock_image)
        
        # Verify pool size hasn't changed
        assert len(mock_renderer._image_buffer_pool[buffer_key]) == BUFFER_POOL_SIZE
        
        # Verify the new image was not added to the pool
        assert new_mock_image not in mock_renderer._image_buffer_pool[buffer_key]

    def test_render_when_called_then_uses_performance_monitoring(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test render method uses performance monitoring."""
        # Mock the view model
        mock_view_model = MagicMock()
        mock_view_model.get_next_event.return_value = None
        
        # Mock the performance monitoring
        with patch.object(mock_renderer.performance, "start_operation") as mock_start:
            with patch.object(mock_renderer.performance, "end_operation") as mock_end:
                # Mock the render methods
                with patch.object(mock_renderer, "_can_do_partial_update", return_value=False):
                    with patch.object(mock_renderer, "_render_full_image") as mock_render_full:
                        mock_render_full.return_value = Image.new("L", (100, 100))
                        
                        # Mock the logger to avoid f-string formatting issues
                        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.logger") as mock_logger:
                            # Mock the end_operation to return a float instead of a MagicMock
                            mock_end.return_value = 10.5  # Return a float value for render_time
                            
                            # Call render
                            mock_renderer.render(mock_view_model)
                            
                            # Verify performance monitoring was used
                            # In the unified rendering pipeline, the operation name might be different
                            # depending on whether HTML-to-PNG conversion is used
                            assert mock_start.called, "Performance monitoring start_operation should be called"
                            assert mock_end.called, "Performance monitoring end_operation should be called"
                            
                            # Check that one of the expected operation names was used
                            expected_operations = ["render", "html_to_png_conversion"]
                            start_calls = [call for call in mock_start.call_args_list
                                          if call[0][0] in expected_operations]
                            assert len(start_calls) > 0, "Should call start_operation with a valid operation name"
                            
                            end_calls = [call for call in mock_end.call_args_list
                                        if call[0][0] in expected_operations]
                            assert len(end_calls) > 0, "Should call end_operation with a valid operation name"

    def test_render_error_when_called_then_uses_optimized_features(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test render_error method uses optimized features."""
        # Mock the font retrieval
        with patch.object(mock_renderer, "_get_font") as mock_get_font:
            # Mock the image buffer retrieval
            with patch.object(mock_renderer, "_get_image_buffer") as mock_get_buffer:
                # Mock the performance monitoring
                with patch.object(mock_renderer.performance, "start_operation") as mock_start:
                    with patch.object(mock_renderer.performance, "end_operation") as mock_end:
                        # Set up mock returns
                        mock_get_font.return_value = MagicMock(spec=ImageFont.FreeTypeFont)
                        mock_get_buffer.return_value = Image.new("L", (400, 300))
                        mock_end.return_value = 42.0  # Mock timing result
                        
                        # Call render_error
                        mock_renderer.render_error("Test error")
                        
                        # Verify optimized features were used
                        mock_get_font.assert_called()
                        mock_get_buffer.assert_called_with("L", 400, 300)
                        mock_start.assert_called_with("render_error")
                        mock_end.assert_called_with("render_error")

    def test_render_authentication_prompt_when_called_then_uses_optimized_features(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test render_authentication_prompt method uses optimized features."""
        # Mock the font retrieval
        with patch.object(mock_renderer, "_get_font") as mock_get_font:
            # Mock the image buffer retrieval
            with patch.object(mock_renderer, "_get_image_buffer") as mock_get_buffer:
                # Mock the performance monitoring
                with patch.object(mock_renderer.performance, "start_operation") as mock_start:
                    with patch.object(mock_renderer.performance, "end_operation") as mock_end:
                        # Set up mock returns
                        mock_get_font.return_value = MagicMock(spec=ImageFont.FreeTypeFont)
                        mock_get_buffer.return_value = Image.new("L", (400, 300))
                        mock_end.return_value = 42.0  # Mock timing result
                        
                        # Call render_authentication_prompt
                        mock_renderer.render_authentication_prompt("https://example.com", "ABC123")
                        
                        # Verify optimized features were used
                        mock_get_font.assert_called()
                        mock_get_buffer.assert_called_with("L", 400, 300)
                        mock_start.assert_called_with("render_auth_prompt")
                        mock_end.assert_called_with("render_auth_prompt")

    def test_error_handling_when_exception_occurs_then_cleans_up_resources(
        self, mock_renderer: EInkWhatsNextRenderer
    ) -> None:
        """Test error handling cleans up resources when exception occurs."""
        # Mock the image buffer retrieval
        mock_image = Image.new("L", (400, 300))
        with patch.object(mock_renderer, "_get_image_buffer", return_value=mock_image):
            # Mock the recycle method
            with patch.object(mock_renderer, "_recycle_image_buffer") as mock_recycle:
                # Mock the performance monitoring
                with patch.object(mock_renderer.performance, "start_operation"):
                    with patch.object(mock_renderer.performance, "end_operation"):
                        # Mock ImageDraw.Draw to get a mock draw object
                        mock_draw = MagicMock()
                        mock_draw.text.side_effect = Exception("Test error")
                        
                        with patch("PIL.ImageDraw.Draw", return_value=mock_draw):
                            # Mock logger to avoid issues with f-strings
                            with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.logger"):
                                # Call render_error which should catch the exception
                                mock_renderer.render_error("Test error")
                                
                                # Verify resources were cleaned up
                                mock_recycle.assert_called_with(mock_image)