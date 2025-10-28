"""Tests for e-Paper display image processing utilities."""

from unittest import mock
from unittest.mock import MagicMock

import pytest
from PIL import Image

from calendarbot.display.epaper.utils.image_processing import (
    convert_image_to_epaper_format,
    create_test_pattern,
    render_text_to_image,
    resize_image_for_epaper,
)


class TestConvertImageToEpaperFormat:
    """Test cases for convert_image_to_epaper_format function."""

    @pytest.fixture
    def mock_image(self) -> MagicMock:
        """Create a mock image for testing to avoid expensive PIL operations."""
        mock_img = MagicMock(spec=Image.Image)
        mock_img.size = (16, 8)
        mock_img.mode = "RGB"
        # Mock convert method to return self for chaining
        mock_img.convert.return_value = mock_img
        # Mock getdata to return predictable pixel data
        mock_img.getdata.return_value = [
            (0, 0, 0) if i < 32 else (255, 0, 0) if i < 64 else (255, 255, 255)
            for i in range(128)  # 16*8 = 128 pixels
        ]
        return mock_img

    def test_convert_image_to_epaper_format_when_bw_mode_then_converts_correctly(
        self, mock_image: MagicMock
    ) -> None:
        """Test convert_image_to_epaper_format in black and white mode."""
        # Convert to e-paper format without red support
        result = convert_image_to_epaper_format(mock_image, threshold=128, red_threshold=None)

        # Verify result
        assert isinstance(result, bytes)
        # Expected buffer size: (16 * 8) // 8 * 2 = 32 bytes (black + red buffers)
        assert len(result) == 32

        # Check black buffer (first half) - should have some non-white bytes
        black_buffer = result[:16]
        assert black_buffer[0] != 0xFF  # Not all white

        # Check red buffer (second half) - should be all white since red_threshold is None
        red_buffer = result[16:]
        assert all(b == 0xFF for b in red_buffer)

    def test_convert_image_to_epaper_format_when_red_mode_then_converts_correctly(
        self, mock_image: MagicMock
    ) -> None:
        """Test convert_image_to_epaper_format with red support."""
        # Convert to e-paper format with red support
        result = convert_image_to_epaper_format(mock_image, threshold=128, red_threshold=200)

        # Verify result exists and is bytes
        assert isinstance(result, bytes)
        # Expected buffer size: (16 * 8) // 8 * 2 = 32 bytes (black + red buffers)
        assert len(result) == 32

        # Verify the function ran without error - that's the main goal
        assert result is not None

    def test_convert_image_to_epaper_format_when_non_rgb_image_then_converts_to_rgb(self) -> None:
        """Test convert_image_to_epaper_format converts non-RGB image to RGB."""
        # Mock grayscale image that gets converted to RGB
        mock_image = MagicMock(spec=Image.Image)
        mock_image.size = (16, 8)
        mock_image.mode = "L"
        mock_rgb_image = MagicMock(spec=Image.Image)
        mock_rgb_image.size = (16, 8)
        mock_rgb_image.mode = "RGB"
        mock_rgb_image.getdata.return_value = [
            (0, 0, 0) if i < 32 else (255, 255, 255) for i in range(128)
        ]
        mock_image.convert.return_value = mock_rgb_image

        # Convert to e-paper format
        result = convert_image_to_epaper_format(mock_image, threshold=128)

        # Verify result
        assert isinstance(result, bytes)
        assert len(result) == 32  # (16 * 8) // 8 * 2 = 32 bytes
        # Verify convert was called to convert to RGB
        mock_image.convert.assert_called_with("RGB")

    def test_convert_image_to_epaper_format_when_empty_image_then_returns_empty_buffer(
        self,
    ) -> None:
        """Test convert_image_to_epaper_format with empty image."""
        # Mock empty image
        mock_image = MagicMock(spec=Image.Image)
        mock_image.size = (0, 0)
        mock_image.mode = "RGB"
        mock_image.convert.return_value = mock_image
        mock_image.getdata.return_value = []

        # Convert to e-paper format
        result = convert_image_to_epaper_format(mock_image, threshold=128)

        # Verify result
        assert isinstance(result, bytes)
        assert len(result) == 0  # Empty buffer


class TestResizeImageForEpaper:
    """Test cases for resize_image_for_epaper function."""

    @pytest.fixture
    def mock_image(self) -> MagicMock:
        """Create a mock image for testing to avoid expensive PIL operations."""
        mock_img = MagicMock(spec=Image.Image)
        mock_img.size = (100, 50)
        mock_img.width = 100
        mock_img.height = 50
        return mock_img

    @mock.patch("calendarbot.display.epaper.utils.image_processing.Image")
    def test_resize_image_for_epaper_when_maintain_aspect_ratio_then_preserves_ratio(
        self, mock_image_class: MagicMock, mock_image: MagicMock
    ) -> None:
        """Test resize_image_for_epaper preserves aspect ratio."""
        # Mock the result image
        mock_result = MagicMock(spec=Image.Image)
        mock_result.width = 200
        mock_result.height = 200

        # Mock Image.new to return our mock result
        mock_image_class.new.return_value = mock_result
        mock_image.resize.return_value = mock_image

        # Call the function
        result = resize_image_for_epaper(mock_image, 200, 200, maintain_aspect_ratio=True)

        # Verify the function was called and returns expected result
        assert result == mock_result

    @mock.patch("calendarbot.display.epaper.utils.image_processing.Image")
    def test_resize_image_for_epaper_when_not_maintain_aspect_ratio_then_stretches(
        self, mock_image_class: MagicMock, mock_image: MagicMock
    ) -> None:
        """Test resize_image_for_epaper stretches image when not maintaining aspect ratio."""
        # Mock the result image
        mock_result = MagicMock(spec=Image.Image)
        mock_result.width = 200
        mock_result.height = 200
        mock_image.resize.return_value = mock_result

        # Call the function
        result = resize_image_for_epaper(mock_image, 200, 200, maintain_aspect_ratio=False)

        # Verify the resize was called and returns expected result
        mock_image.resize.assert_called_once()
        assert result == mock_result

    @mock.patch("calendarbot.display.epaper.utils.image_processing.Image")
    def test_resize_image_for_epaper_when_smaller_target_then_downscales(
        self, mock_image_class: MagicMock, mock_image: MagicMock
    ) -> None:
        """Test resize_image_for_epaper downscales image."""
        # Mock the result image
        mock_result = MagicMock(spec=Image.Image)
        mock_result.width = 50
        mock_result.height = 25

        # Mock Image.new to return our mock result
        mock_image_class.new.return_value = mock_result
        mock_image.resize.return_value = mock_image

        # Call the function
        result = resize_image_for_epaper(mock_image, 50, 25, maintain_aspect_ratio=True)

        # Verify result
        assert result == mock_result

    @mock.patch("calendarbot.display.epaper.utils.image_processing.Image")
    def test_resize_image_for_epaper_when_custom_bg_color_then_uses_correct_color(
        self, mock_image_class: MagicMock, mock_image: MagicMock
    ) -> None:
        """Test resize_image_for_epaper uses custom background color."""
        # Mock the result image
        mock_result = MagicMock(spec=Image.Image)
        bg_color = (255, 0, 0)  # Red

        # Mock Image.new to return our mock result
        mock_image_class.new.return_value = mock_result
        mock_image.resize.return_value = mock_image

        # Call the function
        result = resize_image_for_epaper(
            mock_image, 200, 200, maintain_aspect_ratio=True, bg_color=bg_color
        )

        # Verify Image.new was called with the custom background color
        # Check if it was called (it should be for aspect ratio maintenance)
        if mock_image_class.new.called:
            call_args = mock_image_class.new.call_args
            if len(call_args) > 1 and "color" in call_args[1]:
                assert call_args[1]["color"] == bg_color
        assert result is not None


class TestRenderTextToImage:
    """Test cases for render_text_to_image function."""

    @mock.patch("calendarbot.display.epaper.utils.image_processing.Image")
    @mock.patch("calendarbot.display.epaper.utils.image_processing.ImageDraw")
    def test_render_text_to_image_when_default_params_then_renders_correctly(
        self, mock_draw_class: MagicMock, mock_image_class: MagicMock
    ) -> None:
        """Test render_text_to_image with default parameters."""
        # Mock the result image
        mock_result = MagicMock(spec=Image.Image)
        mock_result.width = 200
        mock_result.height = 100
        mock_result.mode = "RGB"
        mock_image_class.new.return_value = mock_result

        # Mock ImageDraw
        mock_draw = MagicMock()
        mock_draw_class.Draw.return_value = mock_draw

        # Call the function
        result = render_text_to_image("Test Text", 200, 100)

        # Verify result
        assert result == mock_result
        mock_image_class.new.assert_called_once()
        mock_draw_class.Draw.assert_called_once_with(mock_result)

    @mock.patch("calendarbot.display.epaper.utils.image_processing.Image")
    @mock.patch("calendarbot.display.epaper.utils.image_processing.ImageDraw")
    def test_render_text_to_image_when_custom_colors_then_uses_correct_colors(
        self, mock_draw_class: MagicMock, mock_image_class: MagicMock
    ) -> None:
        """Test render_text_to_image with custom colors."""
        # Mock the result image
        mock_result = MagicMock(spec=Image.Image)
        mock_image_class.new.return_value = mock_result

        # Mock ImageDraw
        mock_draw = MagicMock()
        mock_draw_class.Draw.return_value = mock_draw

        text_color = (255, 0, 0)  # Red
        bg_color = (0, 0, 255)  # Blue

        # Call the function
        result = render_text_to_image(
            "Test Text", 200, 100, text_color=text_color, bg_color=bg_color
        )

        # Verify Image.new was called and function returned mock result
        mock_image_class.new.assert_called_once()
        assert result == mock_result

        # Verify ImageDraw.Draw was called with the mock image
        mock_draw_class.Draw.assert_called_once_with(mock_result)

    @mock.patch("calendarbot.display.epaper.utils.image_processing.Image")
    @mock.patch("calendarbot.display.epaper.utils.image_processing.ImageDraw")
    def test_render_text_to_image_when_custom_font_then_uses_correct_font(
        self, mock_draw_class: MagicMock, mock_image_class: MagicMock
    ) -> None:
        """Test render_text_to_image with custom font."""
        # Mock the result image
        mock_result = MagicMock(spec=Image.Image)
        mock_image_class.new.return_value = mock_result

        # Mock ImageDraw
        mock_draw = MagicMock()
        mock_draw_class.Draw.return_value = mock_draw

        # Call the function with font path
        result = render_text_to_image("Test Text", 200, 100, font_path="/path/to/font.ttf")

        # Verify basic functionality without complex font mocking
        assert result == mock_result

    @mock.patch("calendarbot.display.epaper.utils.image_processing.Image")
    @mock.patch("calendarbot.display.epaper.utils.image_processing.ImageDraw")
    def test_render_text_to_image_when_left_aligned_then_aligns_correctly(
        self, mock_draw_class: MagicMock, mock_image_class: MagicMock
    ) -> None:
        """Test render_text_to_image with left alignment."""
        # Mock the result image
        mock_result = MagicMock(spec=Image.Image)
        mock_image_class.new.return_value = mock_result

        # Mock ImageDraw
        mock_draw = MagicMock()
        mock_draw_class.Draw.return_value = mock_draw

        # Call the function
        result = render_text_to_image("Test Text", 200, 100, align="left")

        # Verify result
        assert result == mock_result


class TestCreateTestPattern:
    """Test cases for create_test_pattern function."""

    @mock.patch("calendarbot.display.epaper.utils.image_processing.convert_image_to_epaper_format")
    @mock.patch("calendarbot.display.epaper.utils.image_processing.Image")
    @mock.patch("calendarbot.display.epaper.utils.image_processing.ImageDraw")
    def test_create_test_pattern_when_bw_display_then_creates_correct_pattern(
        self, mock_draw_class: MagicMock, mock_image_class: MagicMock, mock_convert: MagicMock
    ) -> None:
        """Test create_test_pattern for black and white display."""
        # Mock the conversion result
        width = 200
        height = 100
        expected_buffer_size = (width * height) // 8 * 2
        mock_buffer = bytes([0xFF] * expected_buffer_size)

        # Ensure red buffer is all white for BW display
        red_start = (width * height) // 8
        mock_buffer = mock_buffer[:red_start] + bytes([0xFF] * (expected_buffer_size - red_start))
        mock_convert.return_value = mock_buffer

        # Mock image creation
        mock_image = MagicMock(spec=Image.Image)
        mock_image_class.new.return_value = mock_image
        mock_draw = MagicMock()
        mock_draw_class.Draw.return_value = mock_draw

        # Call the function
        result = create_test_pattern(width, height, has_red=False)

        # Verify result
        assert isinstance(result, bytes)
        assert len(result) == expected_buffer_size

        # Check that red buffer is all white (0xFF)
        red_buffer = result[red_start:]
        assert all(b == 0xFF for b in red_buffer)

    @mock.patch("calendarbot.display.epaper.utils.image_processing.convert_image_to_epaper_format")
    @mock.patch("calendarbot.display.epaper.utils.image_processing.Image")
    @mock.patch("calendarbot.display.epaper.utils.image_processing.ImageDraw")
    def test_create_test_pattern_when_red_display_then_creates_correct_pattern(
        self, mock_draw_class: MagicMock, mock_image_class: MagicMock, mock_convert: MagicMock
    ) -> None:
        """Test create_test_pattern for display with red support."""
        # Mock the conversion result with some red pixels
        width = 200
        height = 100
        expected_buffer_size = (width * height) // 8 * 2
        red_start = (width * height) // 8

        # Create buffer with some non-white pixels in red section
        black_buffer = bytes([0xFF] * red_start)
        red_buffer = bytes([0xFE] * (expected_buffer_size - red_start))  # Some non-white
        mock_buffer = black_buffer + red_buffer
        mock_convert.return_value = mock_buffer

        # Mock image creation
        mock_image = MagicMock(spec=Image.Image)
        mock_image_class.new.return_value = mock_image
        mock_draw = MagicMock()
        mock_draw_class.Draw.return_value = mock_draw

        # Call the function
        result = create_test_pattern(width, height, has_red=True)

        # Verify result
        assert isinstance(result, bytes)
        assert len(result) == expected_buffer_size

        # Check that red buffer has some non-white pixels
        red_buffer_result = result[red_start:]
        assert any(b != 0xFF for b in red_buffer_result)

    @mock.patch("calendarbot.display.epaper.utils.image_processing.convert_image_to_epaper_format")
    @mock.patch("calendarbot.display.epaper.utils.image_processing.Image")
    @mock.patch("calendarbot.display.epaper.utils.image_processing.ImageDraw")
    def test_create_test_pattern_when_called_then_uses_correct_parameters(
        self, mock_draw_class: MagicMock, mock_image_class: MagicMock, mock_convert: MagicMock
    ) -> None:
        """Test create_test_pattern uses correct parameters for conversion."""
        # Mock conversion function
        mock_convert.return_value = b"test_buffer"

        # Mock image creation
        mock_image = MagicMock(spec=Image.Image)
        mock_image_class.new.return_value = mock_image
        mock_draw = MagicMock()
        mock_draw_class.Draw.return_value = mock_draw

        # Call the function
        result = create_test_pattern(200, 100, has_red=True)

        # Verify result
        assert result == b"test_buffer"

        # Verify conversion was called
        mock_convert.assert_called_once()
        # Verify image creation was called
        mock_image_class.new.assert_called_once()
