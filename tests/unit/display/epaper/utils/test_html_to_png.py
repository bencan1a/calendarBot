"""Unit tests for the HTML to PNG conversion utility."""

import os
import tempfile
from unittest import mock
from pathlib import Path

import pytest

from calendarbot.display.epaper.utils.html_to_png import (
    HtmlToPngConverter,
    is_html2image_available,
    create_converter,
    HTML2IMAGE_AVAILABLE,
)


@pytest.fixture
def mock_html2image():
    """Mock the Html2Image class."""
    with mock.patch('calendarbot.display.epaper.utils.html_to_png.Html2Image') as mock_hti:
        # Configure the mock to return a mock instance
        mock_instance = mock.MagicMock()
        mock_instance.screenshot.return_value = [os.path.join(tempfile.gettempdir(), 'test.png')]
        mock_hti.return_value = mock_instance
        yield mock_hti


@pytest.fixture
def mock_html2image_available():
    """Mock the HTML2IMAGE_AVAILABLE flag."""
    with mock.patch('calendarbot.display.epaper.utils.html_to_png.HTML2IMAGE_AVAILABLE', True):
        yield


@pytest.fixture
def mock_html2image_unavailable():
    """Mock the HTML2IMAGE_AVAILABLE flag as False."""
    with mock.patch('calendarbot.display.epaper.utils.html_to_png.HTML2IMAGE_AVAILABLE', False):
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
        assert kwargs['size'] == (400, 300)
        assert kwargs['output_path'] == tempfile.gettempdir()
        assert '--disable-gpu' in kwargs['custom_flags']
        assert '--headless' in kwargs['custom_flags']

    def test_initialization_with_custom_params(self, mock_html2image, mock_html2image_available):
        """Test initialization with custom parameters."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None
        
        custom_size = (800, 600)
        custom_output_path = '/tmp/custom'
        custom_flags = ['--flag1', '--flag2']
        
        converter = HtmlToPngConverter(
            size=custom_size,
            output_path=custom_output_path,
            custom_flags=custom_flags,
        )
        
        # Check that Html2Image was called with custom parameters
        mock_html2image.assert_called_once()
        args, kwargs = mock_html2image.call_args
        assert kwargs['size'] == custom_size
        assert kwargs['output_path'] == custom_output_path
        assert kwargs['custom_flags'] == custom_flags

    def test_convert_html_to_png(self, mock_html2image, mock_html2image_available):
        """Test converting HTML to PNG."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None
        
        converter = HtmlToPngConverter()
        
        html_content = "<html><body><h1>Test</h1></body></html>"
        css_content = "h1 { color: red; }"
        output_filename = "test_output.png"
        
        # Configure the mock to return a specific file path
        expected_output = os.path.join(tempfile.gettempdir(), output_filename)
        converter.hti.screenshot.return_value = [expected_output]
        
        # Create a mock file to simulate successful file creation
        with mock.patch('os.path.exists', return_value=True):
            result = converter.convert_html_to_png(
                html_content=html_content,
                css_content=css_content,
                output_filename=output_filename,
            )
        
        # Check that screenshot was called with expected parameters
        converter.hti.screenshot.assert_called_once_with(
            html_str=html_content,
            css_str=[css_content],
            save_as=output_filename,
        )
        
        # Check that the result is the expected output path
        assert result == expected_output

    def test_convert_html_to_png_failure(self, mock_html2image, mock_html2image_available):
        """Test handling of conversion failure."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None
        
        converter = HtmlToPngConverter()
        
        # Configure the mock to simulate failure (file doesn't exist)
        converter.hti.screenshot.return_value = ['/nonexistent/path.png']
        
        with mock.patch('os.path.exists', return_value=False):
            result = converter.convert_html_to_png(
                html_content="<html><body>Test</body></html>",
            )
        
        # Result should be None on failure
        assert result is None

    def test_cleanup(self, mock_html2image, mock_html2image_available):
        """Test cleanup method."""
        # Reset the singleton instance for testing
        HtmlToPngConverter._instance = None
        
        converter = HtmlToPngConverter()
        
        # Add a mock browser attribute to the hti instance
        converter.hti = mock.MagicMock()
        browser_mock = mock.MagicMock()
        converter.hti.browser = browser_mock
        
        # Call cleanup
        converter.cleanup()
        
        # Check that browser.close was called
        browser_mock.close.assert_called_once()
        
        # Check that hti was set to None
        assert converter.hti is None

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