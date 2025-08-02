"""
Unit tests for the display integration functionality of EInkWhatsNextRenderer.

These tests focus on the display integration aspects:
- Update display method with different images
- Display initialization handling
- Error handling during display updates
- Image processing for display format
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Any, Dict, List, Optional, Tuple, cast

from PIL import Image, ImageDraw

from calendarbot.display.epaper.integration.eink_whats_next_renderer import EInkWhatsNextRenderer
from calendarbot.display.epaper.abstraction import DisplayAbstractionLayer
from calendarbot.display.epaper.capabilities import DisplayCapabilities
from calendarbot.display.epaper.utils.image_processor import ImageProcessor
from calendarbot.display.whats_next_data_model import WhatsNextViewModel


class MockDisplayCapabilities:
    """Mock display capabilities for testing."""
    
    def __init__(
        self,
        width: int = 300,
        height: int = 400,
        colors: int = 2,
        supports_partial_update: bool = True,
        supports_grayscale: bool = True,
        supports_red: bool = False
    ) -> None:
        """Initialize mock display capabilities.
        
        Args:
            width: Display width in pixels
            height: Display height in pixels
            colors: Number of colors supported
            supports_partial_update: Whether partial updates are supported
            supports_grayscale: Whether grayscale is supported
            supports_red: Whether red color is supported
        """
        self.width = width
        self.height = height
        self.colors = colors
        self.supports_partial_update = supports_partial_update
        self.supports_grayscale = supports_grayscale
        self.supports_red = supports_red


class MockDisplay(DisplayAbstractionLayer):
    """Mock display for testing."""
    
    def __init__(
        self, 
        capabilities: Optional[MockDisplayCapabilities] = None,
        initialize_success: bool = True,
        render_success: bool = True
    ) -> None:
        """Initialize mock display.
        
        Args:
            capabilities: Optional display capabilities
            initialize_success: Whether initialize() should return success
            render_success: Whether render() should return success
        """
        self.capabilities = capabilities or MockDisplayCapabilities()
        self.initialize_called = False
        self.render_called = False
        self.render_buffer = None
        self.initialize_success = initialize_success
        self.render_success = render_success
    
    def initialize(self) -> bool:
        """Mock initialize method.
        
        Returns:
            True if initialization was successful based on initialize_success
        """
        self.initialize_called = True
        return self.initialize_success
    
    def render(self, buffer: Any) -> bool:
        """Mock render method.
        
        Args:
            buffer: Display buffer to render
            
        Returns:
            True if render was successful based on render_success
        """
        self.render_called = True
        self.render_buffer = buffer
        return self.render_success
    
    def get_capabilities(self) -> MockDisplayCapabilities:
        """Get display capabilities.
        
        Returns:
            Display capabilities
        """
        return self.capabilities
    
    def clear(self) -> bool:
        """Clear the display.
        
        Returns:
            True if clearing was successful
        """
        return True
    
    def shutdown(self) -> bool:
        """Shutdown the display.
        
        Returns:
            True if shutdown was successful
        """
        return True


class MockImageProcessor:
    """Mock image processor for testing."""
    
    def __init__(self, conversion_success: bool = True) -> None:
        """Initialize mock image processor.
        
        Args:
            conversion_success: Whether conversion should succeed
        """
        self.conversion_success = conversion_success
        self.convert_called = False
        self.resize_called = False
        self.optimize_called = False
    
    def convert_to_display_format(
        self, image: Image.Image, capabilities: DisplayCapabilities
    ) -> bytes:
        """Mock convert to display format.
        
        Args:
            image: PIL Image to convert
            capabilities: Display capabilities
            
        Returns:
            Mock display buffer
            
        Raises:
            ValueError: If conversion_success is False
        """
        self.convert_called = True
        
        if not self.conversion_success:
            raise ValueError("Mock conversion error")
        
        return b"mock_display_buffer"
    
    def resize_for_display(
        self, 
        image: Image.Image, 
        capabilities: DisplayCapabilities,
        maintain_aspect_ratio: bool = True
    ) -> Image.Image:
        """Mock resize for display.
        
        Args:
            image: PIL Image to resize
            capabilities: Display capabilities
            maintain_aspect_ratio: Whether to maintain aspect ratio
            
        Returns:
            Resized PIL Image
        """
        self.resize_called = True
        return image
    
    def optimize_for_eink(self, image: Image.Image) -> Image.Image:
        """Mock optimize for e-Ink.
        
        Args:
            image: PIL Image to optimize
            
        Returns:
            Optimized PIL Image
        """
        self.optimize_called = True
        return image


@pytest.fixture
def mock_display() -> MockDisplay:
    """Fixture for mock display.
    
    Returns:
        Mock display instance
    """
    return MockDisplay()


@pytest.fixture
def mock_display_init_fail() -> MockDisplay:
    """Fixture for mock display with initialization failure.
    
    Returns:
        Mock display instance with initialization failure
    """
    return MockDisplay(initialize_success=False)


@pytest.fixture
def mock_display_render_fail() -> MockDisplay:
    """Fixture for mock display with render failure.
    
    Returns:
        Mock display instance with render failure
    """
    return MockDisplay(render_success=False)


@pytest.fixture
def mock_image_processor() -> MockImageProcessor:
    """Fixture for mock image processor.
    
    Returns:
        Mock image processor instance
    """
    return MockImageProcessor()


@pytest.fixture
def mock_image_processor_fail() -> MockImageProcessor:
    """Fixture for mock image processor with conversion failure.
    
    Returns:
        Mock image processor instance with conversion failure
    """
    return MockImageProcessor(conversion_success=False)


@pytest.fixture
def mock_settings() -> Dict[str, Any]:
    """Fixture for mock settings.
    
    Returns:
        Mock settings dictionary
    """
    return {"display": {"type": "epaper"}}


@pytest.fixture
def test_image() -> Image.Image:
    """Fixture for test image.
    
    Returns:
        Test PIL Image
    """
    image = Image.new("RGB", (100, 100), color="white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([(10, 10), (90, 90)], outline="black")
    draw.text((20, 40), "Test", fill="black")
    return image


class TestEInkWhatsNextRendererDisplay:
    """Test display integration functionality of EInkWhatsNextRenderer."""
    
    def test_update_display_when_valid_image_then_initializes_and_renders(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay, test_image: Image.Image
    ) -> None:
        """Test update_display method with valid image.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            test_image: Test image
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        # Mock the image processor
        renderer.image_processor = cast(ImageProcessor, MockImageProcessor())
        
        result = renderer.update_display(test_image)
        
        assert result is True
        assert mock_display.initialize_called is True
        assert mock_display.render_called is True
        assert mock_display.render_buffer == b"mock_display_buffer"
        assert cast(MockImageProcessor, renderer.image_processor).convert_called is True
    
    def test_update_display_when_initialize_fails_then_returns_false(
        self, mock_settings: Dict[str, Any], mock_display_init_fail: MockDisplay, test_image: Image.Image
    ) -> None:
        """Test update_display method when initialize fails.
        
        Args:
            mock_settings: Mock settings
            mock_display_init_fail: Mock display with initialization failure
            test_image: Test image
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display_init_fail)
        
        result = renderer.update_display(test_image)
        
        assert result is False
        assert mock_display_init_fail.initialize_called is True
        assert mock_display_init_fail.render_called is False
    
    def test_update_display_when_render_fails_then_returns_false(
        self, mock_settings: Dict[str, Any], mock_display_render_fail: MockDisplay, test_image: Image.Image
    ) -> None:
        """Test update_display method when render fails.
        
        Args:
            mock_settings: Mock settings
            mock_display_render_fail: Mock display with render failure
            test_image: Test image
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display_render_fail)
        
        # Mock the image processor
        renderer.image_processor = cast(ImageProcessor, MockImageProcessor())
        
        result = renderer.update_display(test_image)
        
        assert result is False
        assert mock_display_render_fail.initialize_called is True
        assert mock_display_render_fail.render_called is True
        assert cast(MockImageProcessor, renderer.image_processor).convert_called is True
    
    def test_update_display_when_image_processing_fails_then_returns_false(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay, test_image: Image.Image
    ) -> None:
        """Test update_display method when image processing fails.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            test_image: Test image
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        # Mock the image processor to fail
        renderer.image_processor = cast(ImageProcessor, MockImageProcessor(conversion_success=False))
        
        result = renderer.update_display(test_image)
        
        assert result is False
        assert mock_display.initialize_called is True
        assert mock_display.render_called is False
        assert cast(MockImageProcessor, renderer.image_processor).convert_called is True
    
    def test_update_display_when_exception_occurs_then_returns_false_and_logs_error(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay, test_image: Image.Image
    ) -> None:
        """Test update_display method with exception.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            test_image: Test image
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        # Mock the image processor to raise an exception
        mock_processor = MagicMock()
        mock_processor.convert_to_display_format.side_effect = Exception("Test error")
        renderer.image_processor = mock_processor
        
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.logger") as mock_logger:
            result = renderer.update_display(test_image)
            
            assert result is False
            assert mock_display.initialize_called is True
            assert mock_display.render_called is False
            mock_logger.exception.assert_called_once_with("Error updating e-Paper display")
    
    def test_update_display_when_invalid_image_then_returns_false(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay
    ) -> None:
        """Test update_display method with invalid image.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        # Mock the image processor
        mock_processor = MagicMock()
        mock_processor.convert_to_display_format.side_effect = TypeError("Invalid image")
        renderer.image_processor = mock_processor
        
        # Use a non-image object
        invalid_image = "not an image"
        
        with patch("calendarbot.display.epaper.integration.eink_whats_next_renderer.logger") as mock_logger:
            result = renderer.update_display(cast(Image.Image, invalid_image))
            
            assert result is False
            assert mock_display.initialize_called is True
            assert mock_display.render_called is False
            mock_logger.exception.assert_called_once_with("Error updating e-Paper display")
    
    def test_display_capabilities_when_different_display_types_then_handles_correctly(
        self, mock_settings: Dict[str, Any], test_image: Image.Image
    ) -> None:
        """Test handling of different display capabilities.
        
        Args:
            mock_settings: Mock settings
            test_image: Test image
        """
        # Test with grayscale display
        grayscale_display = MockDisplay(
            MockDisplayCapabilities(
                supports_grayscale=True,
                supports_red=False
            )
        )
        grayscale_renderer = EInkWhatsNextRenderer(mock_settings, display=grayscale_display)
        grayscale_renderer.image_processor = cast(ImageProcessor, MockImageProcessor())
        
        grayscale_result = grayscale_renderer.update_display(test_image)
        assert grayscale_result is True
        
        # Test with red support display
        red_display = MockDisplay(
            MockDisplayCapabilities(
                supports_grayscale=True,
                supports_red=True
            )
        )
        red_renderer = EInkWhatsNextRenderer(mock_settings, display=red_display)
        red_renderer.image_processor = cast(ImageProcessor, MockImageProcessor())
        
        red_result = red_renderer.update_display(test_image)
        assert red_result is True
        
        # Test with monochrome display
        mono_display = MockDisplay(
            MockDisplayCapabilities(
                supports_grayscale=False,
                supports_red=False
            )
        )
        mono_renderer = EInkWhatsNextRenderer(mock_settings, display=mono_display)
        mono_renderer.image_processor = cast(ImageProcessor, MockImageProcessor())
        
        mono_result = mono_renderer.update_display(test_image)
        assert mono_result is True
    
    def test_image_processor_integration_when_converting_image_then_uses_correct_parameters(
        self, mock_settings: Dict[str, Any], mock_display: MockDisplay, test_image: Image.Image
    ) -> None:
        """Test integration with image processor for converting images.
        
        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            test_image: Test image
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)
        
        with patch("calendarbot.display.epaper.utils.image_processor.ImageProcessor.convert_to_display_format") as mock_convert:
            mock_convert.return_value = b"test_buffer"
            
            result = renderer.update_display(test_image)
            
            assert result is True
            mock_convert.assert_called_once_with(test_image, mock_display.capabilities)
            assert mock_display.render_buffer == b"test_buffer"
    
    def test_display_abstraction_layer_integration_when_updating_display_then_follows_protocol(
        self, mock_settings: Dict[str, Any], test_image: Image.Image
    ) -> None:
        """Test integration with display abstraction layer.
        
        Args:
            mock_settings: Mock settings
            test_image: Test image
        """
        # Create a mock that strictly follows the DisplayAbstractionLayer protocol
        strict_mock_display = MagicMock(spec=DisplayAbstractionLayer)
        strict_mock_display.initialize.return_value = True
        strict_mock_display.render.return_value = True
        strict_mock_display.get_capabilities.return_value = MockDisplayCapabilities()
        
        renderer = EInkWhatsNextRenderer(mock_settings, display=strict_mock_display)
        
        # Mock the image processor
        renderer.image_processor = cast(ImageProcessor, MockImageProcessor())
        
        result = renderer.update_display(test_image)
        
        assert result is True
        strict_mock_display.initialize.assert_called_once()
        strict_mock_display.render.assert_called_once_with(b"mock_display_buffer")