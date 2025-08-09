"""
Unit tests for the display integration functionality of EInkWhatsNextRenderer.

These tests focus on the display integration aspects:
- Update display method with different images
- Display initialization handling
- Error handling during display updates
- Image processing for display format
"""

from typing import Any, Dict, Optional, cast
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image, ImageDraw

from calendarbot.display.epaper.abstraction import DisplayAbstractionLayer
from calendarbot.display.epaper.integration.eink_whats_next_renderer import EInkWhatsNextRenderer
from calendarbot.display.epaper.utils.image_processor import ImageProcessor


def create_mock_display_capabilities(
    width: int = 300,
    height: int = 400,
    colors: int = 2,
    supports_partial_update: bool = True,
    supports_grayscale: bool = True,
    supports_red: bool = False,
) -> MagicMock:
    """Create mock display capabilities for testing.

    Args:
        width: Display width in pixels
        height: Display height in pixels
        colors: Number of colors supported
        supports_partial_update: Whether partial updates are supported
        supports_grayscale: Whether grayscale is supported
        supports_red: Whether red color is supported

    Returns:
        Mock display capabilities
    """
    capabilities = MagicMock()
    capabilities.width = width
    capabilities.height = height
    capabilities.colors = colors
    capabilities.supports_partial_update = supports_partial_update
    capabilities.supports_grayscale = supports_grayscale
    capabilities.supports_red = supports_red
    return capabilities


def create_mock_display(
    capabilities: Optional[MagicMock] = None,
    initialize_success: bool = True,
    render_success: bool = True,
) -> MagicMock:
    """Create mock display for testing.

    Args:
        capabilities: Optional display capabilities
        initialize_success: Whether initialize() should return success
        render_success: Whether render() should return success

    Returns:
        Mock display instance
    """
    display = MagicMock(spec=DisplayAbstractionLayer)
    display.capabilities = capabilities or create_mock_display_capabilities()
    display.initialize_called = False
    display.render_called = False
    display.render_buffer = None
    display.initialize_success = initialize_success
    display.render_success = render_success

    def mock_initialize():
        display.initialize_called = True
        return display.initialize_success

    def mock_render(buffer):
        display.render_called = True
        display.render_buffer = buffer
        return display.render_success

    def mock_get_capabilities():
        return display.capabilities

    display.initialize.side_effect = mock_initialize
    display.render.side_effect = mock_render
    display.get_capabilities.side_effect = mock_get_capabilities
    display.clear.return_value = True
    display.shutdown.return_value = True

    return display


def create_mock_image_processor(conversion_success: bool = True) -> MagicMock:
    """Create mock image processor for testing.

    Args:
        conversion_success: Whether conversion should succeed

    Returns:
        Mock image processor instance
    """
    processor = MagicMock()
    processor.conversion_success = conversion_success
    processor.convert_called = False
    processor.resize_called = False
    processor.optimize_called = False

    def mock_convert_to_display_format(image, capabilities):
        processor.convert_called = True
        if not processor.conversion_success:
            raise ValueError("Mock conversion error")
        return b"mock_display_buffer"

    def mock_resize_for_display(image, capabilities, maintain_aspect_ratio=True):
        processor.resize_called = True
        return image

    def mock_optimize_for_eink(image):
        processor.optimize_called = True
        return image

    processor.convert_to_display_format.side_effect = mock_convert_to_display_format
    processor.resize_for_display.side_effect = mock_resize_for_display
    processor.optimize_for_eink.side_effect = mock_optimize_for_eink

    return processor


@pytest.fixture
def mock_display() -> MagicMock:
    """Fixture for mock display.

    Returns:
        Mock display instance
    """
    return create_mock_display()


@pytest.fixture
def mock_display_init_fail() -> MagicMock:
    """Fixture for mock display with initialization failure.

    Returns:
        Mock display instance with initialization failure
    """
    return create_mock_display(initialize_success=False)


@pytest.fixture
def mock_display_render_fail() -> MagicMock:
    """Fixture for mock display with render failure.

    Returns:
        Mock display instance with render failure
    """
    return create_mock_display(render_success=False)


@pytest.fixture
def mock_image_processor() -> MagicMock:
    """Fixture for mock image processor.

    Returns:
        Mock image processor instance
    """
    return create_mock_image_processor()


@pytest.fixture
def mock_image_processor_fail() -> MagicMock:
    """Fixture for mock image processor with conversion failure.

    Returns:
        Mock image processor instance with conversion failure
    """
    return create_mock_image_processor(conversion_success=False)


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
        self, mock_settings: Dict[str, Any], mock_display: MagicMock, test_image: Image.Image
    ) -> None:
        """Test update_display method with valid image.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            test_image: Test image
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

        # Mock the image processor
        renderer.image_processor = cast(ImageProcessor, create_mock_image_processor())

        result = renderer.update_display(test_image)

        assert result is True
        assert mock_display.initialize_called is True
        assert mock_display.render_called is True
        assert mock_display.render_buffer == b"mock_display_buffer"
        assert renderer.image_processor.convert_called is True

    def test_update_display_when_initialize_fails_then_returns_false(
        self,
        mock_settings: Dict[str, Any],
        mock_display_init_fail: MagicMock,
        test_image: Image.Image,
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
        self,
        mock_settings: Dict[str, Any],
        mock_display_render_fail: MagicMock,
        test_image: Image.Image,
    ) -> None:
        """Test update_display method when render fails.

        Args:
            mock_settings: Mock settings
            mock_display_render_fail: Mock display with render failure
            test_image: Test image
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display_render_fail)

        # Mock the image processor
        renderer.image_processor = cast(ImageProcessor, create_mock_image_processor())

        result = renderer.update_display(test_image)

        assert result is False
        assert mock_display_render_fail.initialize_called is True
        assert mock_display_render_fail.render_called is True
        assert renderer.image_processor.convert_called is True

    def test_update_display_when_image_processing_fails_then_returns_false(
        self, mock_settings: Dict[str, Any], mock_display: MagicMock, test_image: Image.Image
    ) -> None:
        """Test update_display method when image processing fails.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            test_image: Test image
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

        # Mock the image processor to fail
        renderer.image_processor = cast(
            ImageProcessor, create_mock_image_processor(conversion_success=False)
        )

        result = renderer.update_display(test_image)

        assert result is False
        assert mock_display.initialize_called is True
        assert mock_display.render_called is False
        assert renderer.image_processor.convert_called is True

    def test_update_display_when_exception_occurs_then_returns_false_and_logs_error(
        self, mock_settings: Dict[str, Any], mock_display: MagicMock, test_image: Image.Image
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

        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.logger"
        ) as mock_logger:
            result = renderer.update_display(test_image)

            assert result is False
            assert mock_display.initialize_called is True
            assert mock_display.render_called is False
            mock_logger.exception.assert_called_once_with("Error updating e-Paper display")

    def test_update_display_when_invalid_image_then_returns_false(
        self, mock_settings: Dict[str, Any], mock_display: MagicMock
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

        with patch(
            "calendarbot.display.epaper.integration.eink_whats_next_renderer.logger"
        ) as mock_logger:
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
        grayscale_display = create_mock_display(
            create_mock_display_capabilities(supports_grayscale=True, supports_red=False)
        )
        grayscale_renderer = EInkWhatsNextRenderer(mock_settings, display=grayscale_display)
        grayscale_renderer.image_processor = cast(ImageProcessor, create_mock_image_processor())

        grayscale_result = grayscale_renderer.update_display(test_image)
        assert grayscale_result is True

        # Test with red support display
        red_display = create_mock_display(
            create_mock_display_capabilities(supports_grayscale=True, supports_red=True)
        )
        red_renderer = EInkWhatsNextRenderer(mock_settings, display=red_display)
        red_renderer.image_processor = cast(ImageProcessor, create_mock_image_processor())

        red_result = red_renderer.update_display(test_image)
        assert red_result is True

        # Test with monochrome display
        mono_display = create_mock_display(
            create_mock_display_capabilities(supports_grayscale=False, supports_red=False)
        )
        mono_renderer = EInkWhatsNextRenderer(mock_settings, display=mono_display)
        mono_renderer.image_processor = cast(ImageProcessor, create_mock_image_processor())

        mono_result = mono_renderer.update_display(test_image)
        assert mono_result is True

    def test_image_processor_integration_when_converting_image_then_uses_correct_parameters(
        self, mock_settings: Dict[str, Any], mock_display: MagicMock, test_image: Image.Image
    ) -> None:
        """Test integration with image processor for converting images.

        Args:
            mock_settings: Mock settings
            mock_display: Mock display
            test_image: Test image
        """
        renderer = EInkWhatsNextRenderer(mock_settings, display=mock_display)

        with patch(
            "calendarbot.display.epaper.utils.image_processor.ImageProcessor.convert_to_display_format"
        ) as mock_convert:
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
        strict_mock_display.get_capabilities.return_value = create_mock_display_capabilities()

        renderer = EInkWhatsNextRenderer(mock_settings, display=strict_mock_display)

        # Mock the image processor
        renderer.image_processor = cast(ImageProcessor, create_mock_image_processor())

        result = renderer.update_display(test_image)

        assert result is True
        strict_mock_display.initialize.assert_called_once()
        strict_mock_display.render.assert_called_once_with(b"mock_display_buffer")
