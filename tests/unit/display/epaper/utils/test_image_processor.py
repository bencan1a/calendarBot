"""Tests for e-Paper display image processor."""

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from calendarbot.display.epaper.capabilities import DisplayCapabilities
from calendarbot.display.epaper.utils.image_processor import ImageProcessor


class TestImageProcessor:
    """Test cases for ImageProcessor class."""

    @pytest.fixture
    def processor(self) -> ImageProcessor:
        """Create ImageProcessor instance for testing."""
        return ImageProcessor()

    @pytest.fixture
    def mock_capabilities(self) -> MagicMock:
        """Create mock DisplayCapabilities for testing."""
        capabilities = MagicMock(spec=DisplayCapabilities)
        capabilities.width = 200
        capabilities.height = 100
        capabilities.supports_red = False
        return capabilities

    @pytest.fixture
    def mock_image(self) -> MagicMock:
        """Create mock PIL Image for testing."""
        image = MagicMock(spec=Image.Image)
        image.size = (100, 50)
        image.mode = "RGB"
        return image

    @pytest.fixture
    def real_image(self) -> Image.Image:
        """Create a real PIL Image for testing."""
        return Image.new("RGB", (100, 50), color="white")

    def test_init_when_called_then_initializes_successfully(self) -> None:
        """Test ImageProcessor initialization."""
        processor = ImageProcessor()

        assert processor is not None
        assert isinstance(processor, ImageProcessor)

    @patch("calendarbot.display.epaper.utils.image_processor.resize_image_for_epaper")
    @patch("calendarbot.display.epaper.utils.image_processor.convert_image_to_epaper_format")
    def test_convert_to_display_format_when_bw_display_then_converts_correctly(
        self,
        mock_convert: MagicMock,
        mock_resize: MagicMock,
        processor: ImageProcessor,
        mock_image: MagicMock,
        mock_capabilities: MagicMock,
    ) -> None:
        """Test convert_to_display_format for black and white display."""
        # Configure mocks
        mock_capabilities.supports_red = False
        mock_resize.return_value = mock_image
        mock_convert.return_value = b"test_buffer"

        # Call method
        result = processor.convert_to_display_format(mock_image, mock_capabilities)

        # Verify results
        assert result == b"test_buffer"
        mock_resize.assert_called_once_with(
            mock_image,
            mock_capabilities.width,
            mock_capabilities.height,
            maintain_aspect_ratio=True,
        )
        mock_convert.assert_called_once_with(mock_image, threshold=128, red_threshold=None)

    @patch("calendarbot.display.epaper.utils.image_processor.resize_image_for_epaper")
    @patch("calendarbot.display.epaper.utils.image_processor.convert_image_to_epaper_format")
    def test_convert_to_display_format_when_red_display_then_converts_correctly(
        self,
        mock_convert: MagicMock,
        mock_resize: MagicMock,
        processor: ImageProcessor,
        mock_image: MagicMock,
        mock_capabilities: MagicMock,
    ) -> None:
        """Test convert_to_display_format for display with red support."""
        # Configure mocks
        mock_capabilities.supports_red = True
        mock_resize.return_value = mock_image
        mock_convert.return_value = b"test_buffer_with_red"

        # Call method
        result = processor.convert_to_display_format(mock_image, mock_capabilities)

        # Verify results
        assert result == b"test_buffer_with_red"
        mock_resize.assert_called_once_with(
            mock_image,
            mock_capabilities.width,
            mock_capabilities.height,
            maintain_aspect_ratio=True,
        )
        mock_convert.assert_called_once_with(mock_image, threshold=128, red_threshold=200)

    def test_convert_to_display_format_when_invalid_image_then_raises_type_error(
        self, processor: ImageProcessor, mock_capabilities: MagicMock
    ) -> None:
        """Test convert_to_display_format raises TypeError for invalid image."""
        with pytest.raises(TypeError) as excinfo:
            processor.convert_to_display_format("not_an_image", mock_capabilities)

        assert "Input must be a PIL Image" in str(excinfo.value)

    def test_convert_to_display_format_when_invalid_capabilities_then_raises_type_error(
        self, processor: ImageProcessor, mock_image: MagicMock
    ) -> None:
        """Test convert_to_display_format raises TypeError for invalid capabilities."""
        with pytest.raises(TypeError) as excinfo:
            processor.convert_to_display_format(mock_image, "not_capabilities")

        assert "Capabilities must be a DisplayCapabilities instance" in str(excinfo.value)

    @patch("calendarbot.display.epaper.utils.image_processor.resize_image_for_epaper")
    def test_convert_to_display_format_when_error_occurs_then_raises_exception(
        self,
        mock_resize: MagicMock,
        processor: ImageProcessor,
        mock_image: MagicMock,
        mock_capabilities: MagicMock,
    ) -> None:
        """Test convert_to_display_format propagates exceptions."""
        # Configure mock to raise exception
        mock_resize.side_effect = ValueError("Test error")

        # Call method and verify exception is raised
        with pytest.raises(ValueError) as excinfo:
            processor.convert_to_display_format(mock_image, mock_capabilities)

        assert "Test error" in str(excinfo.value)

    @patch("calendarbot.display.epaper.utils.image_processor.resize_image_for_epaper")
    def test_resize_for_display_when_maintain_aspect_ratio_then_resizes_correctly(
        self,
        mock_resize: MagicMock,
        processor: ImageProcessor,
        mock_image: MagicMock,
        mock_capabilities: MagicMock,
    ) -> None:
        """Test resize_for_display with maintain_aspect_ratio=True."""
        # Configure mock
        mock_resize.return_value = MagicMock(spec=Image.Image)
        mock_resize.return_value.size = (200, 100)

        # Call method
        result = processor.resize_for_display(
            mock_image, mock_capabilities, maintain_aspect_ratio=True
        )

        # Verify results
        assert result is mock_resize.return_value
        mock_resize.assert_called_once_with(
            mock_image,
            mock_capabilities.width,
            mock_capabilities.height,
            maintain_aspect_ratio=True,
        )

    @patch("calendarbot.display.epaper.utils.image_processor.resize_image_for_epaper")
    def test_resize_for_display_when_not_maintain_aspect_ratio_then_resizes_correctly(
        self,
        mock_resize: MagicMock,
        processor: ImageProcessor,
        mock_image: MagicMock,
        mock_capabilities: MagicMock,
    ) -> None:
        """Test resize_for_display with maintain_aspect_ratio=False."""
        # Configure mock
        mock_resize.return_value = MagicMock(spec=Image.Image)
        mock_resize.return_value.size = (200, 100)

        # Call method
        result = processor.resize_for_display(
            mock_image, mock_capabilities, maintain_aspect_ratio=False
        )

        # Verify results
        assert result is mock_resize.return_value
        mock_resize.assert_called_once_with(
            mock_image,
            mock_capabilities.width,
            mock_capabilities.height,
            maintain_aspect_ratio=False,
        )

    def test_resize_for_display_when_invalid_image_then_raises_type_error(
        self, processor: ImageProcessor, mock_capabilities: MagicMock
    ) -> None:
        """Test resize_for_display raises TypeError for invalid image."""
        with pytest.raises(TypeError) as excinfo:
            processor.resize_for_display("not_an_image", mock_capabilities)

        assert "Input must be a PIL Image" in str(excinfo.value)

    def test_resize_for_display_when_invalid_capabilities_then_raises_type_error(
        self, processor: ImageProcessor, mock_image: MagicMock
    ) -> None:
        """Test resize_for_display raises TypeError for invalid capabilities."""
        with pytest.raises(TypeError) as excinfo:
            processor.resize_for_display(mock_image, "not_capabilities")

        assert "Capabilities must be a DisplayCapabilities instance" in str(excinfo.value)

    @patch("calendarbot.display.epaper.utils.image_processor.resize_image_for_epaper")
    def test_resize_for_display_when_error_occurs_then_raises_exception(
        self,
        mock_resize: MagicMock,
        processor: ImageProcessor,
        mock_image: MagicMock,
        mock_capabilities: MagicMock,
    ) -> None:
        """Test resize_for_display propagates exceptions."""
        # Configure mock to raise exception
        mock_resize.side_effect = ValueError("Test error")

        # Call method and verify exception is raised
        with pytest.raises(ValueError) as excinfo:
            processor.resize_for_display(mock_image, mock_capabilities)

        assert "Test error" in str(excinfo.value)

    def test_optimize_for_eink_when_rgb_image_then_enhances_correctly(
        self, processor: ImageProcessor, real_image: Image.Image
    ) -> None:
        """Test optimize_for_eink enhances RGB image correctly."""
        # Call method
        result = processor.optimize_for_eink(real_image)

        # Verify results
        assert result is not None
        assert isinstance(result, Image.Image)
        assert result.mode == "RGB"
        # Size should remain the same
        assert result.size == real_image.size

    def test_optimize_for_eink_when_non_rgb_image_then_converts_to_rgb(
        self, processor: ImageProcessor
    ) -> None:
        """Test optimize_for_eink converts non-RGB image to RGB."""
        # Create grayscale image
        grayscale_image = Image.new("L", (100, 50), color=128)

        # Call method
        result = processor.optimize_for_eink(grayscale_image)

        # Verify results
        assert result is not None
        assert isinstance(result, Image.Image)
        assert result.mode == "RGB"
        assert result.size == grayscale_image.size

    def test_optimize_for_eink_when_invalid_image_then_raises_type_error(
        self, processor: ImageProcessor
    ) -> None:
        """Test optimize_for_eink raises TypeError for invalid image."""
        with pytest.raises(TypeError) as excinfo:
            processor.optimize_for_eink("not_an_image")

        assert "Input must be a PIL Image" in str(excinfo.value)

    @patch("calendarbot.display.epaper.utils.image_processor.ImageEnhance")
    def test_optimize_for_eink_when_error_occurs_then_raises_exception(
        self, mock_enhance: MagicMock, processor: ImageProcessor, real_image: Image.Image
    ) -> None:
        """Test optimize_for_eink propagates exceptions."""
        # Configure mock to raise exception
        mock_enhance.Contrast.side_effect = ValueError("Test error")

        # Call method and verify exception is raised
        with pytest.raises(ValueError) as excinfo:
            processor.optimize_for_eink(real_image)

        assert "Test error" in str(excinfo.value)

    @patch("calendarbot.display.epaper.utils.image_processor.create_test_pattern")
    def test_create_test_image_when_bw_display_then_creates_correctly(
        self,
        mock_create_pattern: MagicMock,
        processor: ImageProcessor,
        mock_capabilities: MagicMock,
    ) -> None:
        """Test create_test_image for black and white display."""
        # Configure mocks
        mock_capabilities.supports_red = False
        mock_create_pattern.return_value = b"test_pattern"

        # Call method
        result = processor.create_test_image(mock_capabilities)

        # Verify results
        assert result == b"test_pattern"
        mock_create_pattern.assert_called_once_with(
            mock_capabilities.width, mock_capabilities.height, has_red=False
        )

    @patch("calendarbot.display.epaper.utils.image_processor.create_test_pattern")
    def test_create_test_image_when_red_display_then_creates_correctly(
        self,
        mock_create_pattern: MagicMock,
        processor: ImageProcessor,
        mock_capabilities: MagicMock,
    ) -> None:
        """Test create_test_image for display with red support."""
        # Configure mocks
        mock_capabilities.supports_red = True
        mock_create_pattern.return_value = b"test_pattern_with_red"

        # Call method
        result = processor.create_test_image(mock_capabilities)

        # Verify results
        assert result == b"test_pattern_with_red"
        mock_create_pattern.assert_called_once_with(
            mock_capabilities.width, mock_capabilities.height, has_red=True
        )

    @patch("calendarbot.display.epaper.utils.image_processor.create_test_pattern")
    def test_create_test_image_when_error_occurs_then_raises_exception(
        self,
        mock_create_pattern: MagicMock,
        processor: ImageProcessor,
        mock_capabilities: MagicMock,
    ) -> None:
        """Test create_test_image propagates exceptions."""
        # Configure mock to raise exception
        mock_create_pattern.side_effect = ValueError("Test error")

        # Call method and verify exception is raised
        with pytest.raises(ValueError) as excinfo:
            processor.create_test_image(mock_capabilities)

        assert "Test error" in str(excinfo.value)
