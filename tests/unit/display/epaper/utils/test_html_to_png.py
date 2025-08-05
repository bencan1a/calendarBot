"""Unit tests for the HTML to PNG conversion utility."""

import os
import tempfile
from unittest import mock

import pytest

from calendarbot.display.epaper.utils.html_to_png import (
    HtmlToPngConverter,
    create_converter,
    is_html2image_available,
)


@pytest.fixture
def mock_html2image():
    """Mock the Html2Image class."""
    with mock.patch("calendarbot.display.epaper.utils.html_to_png.Html2Image") as mock_hti:
        # Configure the mock to return a mock instance
        mock_instance = mock.MagicMock()
        mock_instance.screenshot.return_value = [os.path.join(tempfile.gettempdir(), "test.png")]
        mock_hti.return_value = mock_instance
        yield mock_hti


@pytest.fixture
def mock_html2image_available():
    """Mock the HTML2IMAGE_AVAILABLE flag."""
    with mock.patch("calendarbot.display.epaper.utils.html_to_png.HTML2IMAGE_AVAILABLE", True):
        yield


@pytest.fixture
def mock_html2image_unavailable():
    """Mock the HTML2IMAGE_AVAILABLE flag as False."""
    with mock.patch("calendarbot.display.epaper.utils.html_to_png.HTML2IMAGE_AVAILABLE", False):
        yield


class TestHtmlToPngConverter:
    """Tests for the HtmlToPngConverter class."""

    def test_singleton_pattern(self, mock_html2image, mock_html2image_available):
        """Test that the converter uses the singleton pattern."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None

        # Create two instances
        converter1 = HtmlToPngConverter()
        converter2 = HtmlToPngConverter()

        # They should be the same instance
        assert converter1 is converter2

    def test_initialization_with_defaults(self, mock_html2image, mock_html2image_available):
        """Test initialization with default parameters."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None

        converter = HtmlToPngConverter()

        # Check that Html2Image was called with expected defaults
        mock_html2image.assert_called_once()
        args, kwargs = mock_html2image.call_args
        assert kwargs["size"] == (300, 400)
        assert kwargs["output_path"] == tempfile.gettempdir()
        assert "--disable-gpu" in kwargs["custom_flags"]
        assert "--headless" in kwargs["custom_flags"]

    def test_initialization_with_custom_params(self, mock_html2image, mock_html2image_available):
        """Test initialization with custom parameters."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None

        custom_size = (800, 600)
        custom_output_path = "/tmp/custom"
        custom_flags = ["--flag1", "--flag2"]

        converter = HtmlToPngConverter(
            size=custom_size,
            output_path=custom_output_path,
            custom_flags=custom_flags,
        )

        # Check that Html2Image was called with custom parameters
        mock_html2image.assert_called_once()
        args, kwargs = mock_html2image.call_args
        assert kwargs["size"] == custom_size
        assert kwargs["output_path"] == custom_output_path
        assert kwargs["custom_flags"] == custom_flags

    def test_convert_url_to_png_with_html_like_content(
        self, mock_html2image, mock_html2image_available
    ):
        """Test converting URL to PNG (replacement for convert_html_to_png test)."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None

        # Create a mock for the Html2Image instance
        mock_hti_instance = mock.MagicMock()
        test_url = "http://example.com/test.html"
        output_filename = "test_output.png"

        # Configure the mock to return a specific file path
        expected_output = os.path.join(tempfile.gettempdir(), output_filename)
        mock_hti_instance.screenshot.return_value = [expected_output]

        # Create the converter with the mock
        with mock.patch(
            "calendarbot.display.epaper.utils.html_to_png.Html2Image",
            return_value=mock_hti_instance,
        ):
            converter = HtmlToPngConverter()

            # Mock the cropping method to return the same path
            with mock.patch.object(
                converter, "crop_image_to_target_size", return_value=expected_output
            ):
                result = converter.convert_url_to_png(
                    url=test_url,
                    output_filename=output_filename,
                )

            # Check that screenshot was called with expected parameters
            mock_hti_instance.screenshot.assert_called_once()
            screenshot_args = mock_hti_instance.screenshot.call_args[1]
            assert screenshot_args["url"] == test_url
            assert screenshot_args["save_as"] == output_filename

            # Check that the result is the expected output path
            assert result == expected_output

    def test_convert_url_to_png_failure(self, mock_html2image, mock_html2image_available):
        """Test handling of URL conversion failure."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None

        # Create a mock for the Html2Image instance
        mock_hti_instance = mock.MagicMock()

        # Configure the mock to simulate failure (no files returned)
        mock_hti_instance.screenshot.return_value = []

        # Create the converter with the mock
        with mock.patch(
            "calendarbot.display.epaper.utils.html_to_png.Html2Image",
            return_value=mock_hti_instance,
        ):
            converter = HtmlToPngConverter()

            result = converter.convert_url_to_png(
                url="http://example.com/test.html", output_filename="test_output.png"
            )

            # Result should be None on failure
            assert result is None

    def test_cleanup(self, mock_html2image, mock_html2image_available):
        """Test cleanup method."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None

        # Create a mock for the Html2Image instance
        mock_hti_instance = mock.MagicMock()
        browser_mock = mock.MagicMock()
        mock_hti_instance.browser = browser_mock

        # Create the converter with the mock
        with mock.patch(
            "calendarbot.display.epaper.utils.html_to_png.Html2Image",
            return_value=mock_hti_instance,
        ):
            converter = HtmlToPngConverter()

            # Call cleanup
            converter.cleanup()

            # Check that browser.close was called
            browser_mock.close.assert_called_once()

            # Check that hti was set to None
            assert converter.hti is None

    def test_convert_url_to_png_success(self, mock_html2image, mock_html2image_available):
        """Test successful URL to PNG conversion."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None

        # Create a mock for the Html2Image instance
        mock_hti_instance = mock.MagicMock()
        test_url = "http://example.com"
        output_filename = "test_url.png"
        expected_output = os.path.join(tempfile.gettempdir(), "test_url_cropped.png")

        # Configure the mock to return a file path
        mock_hti_instance.screenshot.return_value = [
            os.path.join(tempfile.gettempdir(), output_filename)
        ]

        # Create the converter with the mock
        with mock.patch(
            "calendarbot.display.epaper.utils.html_to_png.Html2Image",
            return_value=mock_hti_instance,
        ):
            converter = HtmlToPngConverter()

            # Mock the cropping method to return cropped path
            with mock.patch.object(
                converter, "crop_image_to_target_size", return_value=expected_output
            ):
                result = converter.convert_url_to_png(url=test_url, output_filename=output_filename)

                # Check that screenshot was called
                mock_hti_instance.screenshot.assert_called_once()
                screenshot_args = mock_hti_instance.screenshot.call_args[1]
                assert screenshot_args["url"] == test_url
                assert screenshot_args["save_as"] == output_filename

                # Check that the result is the cropped output path
                assert result == expected_output

    def test_convert_url_to_png_screenshot_failure(
        self, mock_html2image, mock_html2image_available
    ):
        """Test handling of URL conversion when screenshot fails."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None

        # Create a mock for the Html2Image instance
        mock_hti_instance = mock.MagicMock()

        # Configure the mock to simulate screenshot failure (empty list)
        mock_hti_instance.screenshot.return_value = []

        # Create the converter with the mock
        with mock.patch(
            "calendarbot.display.epaper.utils.html_to_png.Html2Image",
            return_value=mock_hti_instance,
        ):
            converter = HtmlToPngConverter()

            result = converter.convert_url_to_png(
                url="http://example.com", output_filename="test_url.png"
            )

            # Result should be None on failure
            assert result is None

    def test_crop_image_to_target_size(self, mock_html2image, mock_html2image_available):
        """Test the crop_image_to_target_size method."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None

        # Create a temporary test image
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_file.close()

        # Create a test image larger than target size
        from PIL import Image

        test_image = Image.new("RGB", (500, 600), color="white")
        test_image.save(temp_file.name)

        try:
            # Create the converter
            converter = HtmlToPngConverter()

            # Test cropping
            result = converter.crop_image_to_target_size(
                image_path=temp_file.name, target_size=(300, 400), crop_from_top=True
            )

            # Check that a cropped file was created
            assert result is not None
            assert result != temp_file.name  # Should be a different path
            assert result.endswith("_cropped.png")

            # Verify the cropped image has the correct size
            with Image.open(result) as cropped_img:
                assert cropped_img.size == (300, 400)

            # Clean up cropped file
            if os.path.exists(result):
                os.unlink(result)

        finally:
            # Clean up original file
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

    def test_initialization_failure(self, mock_html2image, mock_html2image_available):
        """Test handling of initialization failure."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None

        # Configure the mock to raise an exception
        mock_html2image.side_effect = Exception("Initialization failed")

        # Initialization should raise an exception
        with pytest.raises(Exception, match="Initialization failed"):
            HtmlToPngConverter()

    def test_html2image_unavailable(self, mock_html2image_unavailable):
        """Test behavior when html2image is not available."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None

        # Initialization should raise ImportError
        with pytest.raises(ImportError, match="html2image is not installed"):
            HtmlToPngConverter()


class TestHelperFunctions:
    """Tests for the helper functions."""

    def test_is_html2image_available_true(self, mock_html2image_available):
        """Test is_html2image_available when html2image is available."""
        assert is_html2image_available() is True

    def test_is_html2image_available_false(self, mock_html2image_unavailable):
        """Test is_html2image_available when html2image is not available."""
        assert is_html2image_available() is False

    def test_create_converter_success(self, mock_html2image, mock_html2image_available):
        """Test create_converter when successful."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None

        converter = create_converter(size=(800, 600))

        # Should return a converter instance
        assert isinstance(converter, HtmlToPngConverter)
        assert converter.size == (800, 600)

    def test_create_converter_failure(self, mock_html2image, mock_html2image_available):
        """Test create_converter when initialization fails."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None

        # Configure the mock to raise an exception
        mock_html2image.side_effect = Exception("Initialization failed")

        # Should return None on failure
        assert create_converter() is None

    def test_create_converter_html2image_unavailable(self, mock_html2image_unavailable):
        """Test create_converter when html2image is not available."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None

        # Should return None when html2image is not available
        assert create_converter() is None
