"""
HTML to PNG conversion utility for e-paper display.

This module provides a lightweight HTML-to-PNG conversion utility optimized for
resource-constrained environments like Raspberry Pi Zero 2W. It uses html2image
with minimal configuration to efficiently convert HTML content to PNG images
suitable for e-paper displays.
"""

import logging
import os
import tempfile
from typing import Optional

# Import html2image conditionally to handle environments where it's not installed
try:
    from html2image import Html2Image
    HTML2IMAGE_AVAILABLE = True
except ImportError:
    HTML2IMAGE_AVAILABLE = False
    Html2Image = None  # type: ignore

# For type checking only
from typing import List, Tuple, TypeVar

# Define HTI type for type checking
HTI = TypeVar('HTI')

logger = logging.getLogger(__name__)


class HtmlToPngConverter:
    """
    Lightweight HTML to PNG converter optimized for e-paper displays.

    This class provides an efficient way to convert HTML content to PNG images
    with minimal resource usage, making it suitable for resource-constrained
    environments like Raspberry Pi Zero 2W.

    It uses html2image with custom browser flags to minimize memory usage
    and implements caching to avoid repeated initialization.
    """

    # Singleton instance for reuse
    _instance: Optional['HtmlToPngConverter'] = None

    def __new__(cls, *args, **kwargs):
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        size: Tuple[int, int] = (400, 300),
        output_path: Optional[str] = None,
        custom_flags: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize the HTML to PNG converter.

        Args:
            size: Tuple of (width, height) for the output image
            output_path: Directory to save output images (uses temp dir if None)
            custom_flags: Custom browser flags to minimize resource usage

        Raises:
            ImportError: If html2image is not installed
        """
        # Skip initialization if already initialized
        if getattr(self, '_initialized', False):
            return

        if not HTML2IMAGE_AVAILABLE:
            logger.error("html2image is not installed. Install with: pip install html2image")
            raise ImportError("html2image is not installed")

        self.size = size

        # Use system temp directory if output_path is not specified
        self.output_path = output_path or tempfile.gettempdir()

        # Default flags optimized for minimal resource usage
        default_flags = [
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-dev-shm-usage',
            '--disable-setuid-sandbox',
            '--no-sandbox',
            '--headless',
            '--disable-extensions',
            '--disable-component-extensions-with-background-pages',
            '--disable-default-apps',
            '--mute-audio',
            '--hide-scrollbars',
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-breakpad',
            '--disable-client-side-phishing-detection',
            '--disable-features=TranslateUI,BlinkGenPropertyTrees',
            '--disable-hang-monitor',
            '--disable-ipc-flooding-protection',
            '--disable-prompt-on-repost',
            '--disable-renderer-backgrounding',
            '--force-color-profile=srgb',
            '--metrics-recording-only',
            '--no-first-run',
            '--password-store=basic',
            '--use-mock-keychain',
            f'--window-size={size[0]},{size[1]}',
        ]

        # Use custom flags if provided, otherwise use default flags
        browser_flags = custom_flags if custom_flags is not None else default_flags

        try:
            if HTML2IMAGE_AVAILABLE and Html2Image is not None:
                # Initialize html2image with optimized settings
                self.hti = Html2Image(  # type: ignore
                    size=size,
                    output_path=self.output_path,
                    custom_flags=browser_flags,
                )
                logger.info(f"HtmlToPngConverter initialized with size {size}")
                self._initialized = True
            else:
                logger.error("html2image is not available")
                raise ImportError("html2image is not installed")
        except Exception as e:
            logger.exception(f"Failed to initialize HtmlToPngConverter: {e}")
            raise

    def convert_html_to_png(
        self,
        html_content: str,
        css_content: Optional[str] = None,
        output_filename: Optional[str] = None,
    ) -> Optional[str]:
        """
        Convert HTML content to a PNG image.

        Args:
            html_content: HTML content to convert
            css_content: Optional CSS content to apply
            output_filename: Optional filename for the output image

        Returns:
            Path to the generated PNG file or None if conversion failed

        Raises:
            RuntimeError: If conversion fails
        """
        if not self._initialized:
            logger.error("HtmlToPngConverter not initialized")
            raise RuntimeError("HtmlToPngConverter not initialized")

        try:
            # Generate a unique filename if not provided
            if output_filename is None:
                output_filename = f"epaper_render_{os.urandom(4).hex()}.png"

            # Ensure the filename has .png extension
            if not output_filename.lower().endswith('.png'):
                output_filename += '.png'

            # Convert HTML to PNG
            logger.debug(f"Converting HTML to PNG: {output_filename}")

            # Prepare CSS content - html2image expects css_str to be a list (not None)
            css_str_param = [css_content] if css_content is not None else []

            # Use html2image to convert HTML to PNG
            # Ensure the output directory exists
            os.makedirs(self.output_path, exist_ok=True)
            logger.debug(f"Ensured output directory exists: {self.output_path}")

            # Check if the output path is accessible
            if not os.path.exists(self.output_path):
                logger.error(f"Output directory does not exist: {self.output_path}")
                try:
                    os.makedirs(self.output_path, exist_ok=True)
                    logger.info(f"Created output directory: {self.output_path}")
                except Exception as e:
                    logger.error(f"Failed to create output directory: {e}")
                    # Fall back to a more reliable directory
                    new_output_path = os.path.join(os.getcwd(), "epaper_output")
                    os.makedirs(new_output_path, exist_ok=True)
                    logger.info(f"Created fallback output directory: {new_output_path}")
                    self.output_path = new_output_path

                    # Update the output path if hti is available
                    if hasattr(self, 'hti') and self.hti is not None:
                        # Use getattr/setattr to avoid type checking issues
                        if hasattr(self.hti, 'output_path'):
                            self.hti.output_path = new_output_path
                            logger.info(f"Updated HTML converter output path to: {getattr(self.hti, 'output_path', 'Unknown')}")

            # Double-check write permissions
            if not os.access(self.output_path, os.W_OK):
                logger.error(f"Output directory is not writable: {self.output_path}")
                # Try to create a new directory in a different location
                new_output_path = os.path.join(tempfile.gettempdir(), f"calendarbot_html2png_{os.urandom(4).hex()}")
                os.makedirs(new_output_path, exist_ok=True)
                logger.info(f"Created new output directory: {new_output_path}")
                self.output_path = new_output_path

                # Update the output path if hti is available
                if hasattr(self, 'hti') and self.hti is not None:
                    if hasattr(self.hti, 'output_path'):
                        self.hti.output_path = new_output_path  # type: ignore
                        logger.info(f"Updated HTML converter output path to: {self.hti.output_path}")  # type: ignore

            # Use the filename as provided
            if not hasattr(self, 'hti') or self.hti is None:
                logger.error("HTML converter not initialized")
                return None

            # Use getattr to avoid type checking issues
            screenshot_method = getattr(self.hti, 'screenshot', None)
            if screenshot_method and callable(screenshot_method):
                logger.debug(f"Calling html2image screenshot with output_path: {self.output_path}")
                output_files = screenshot_method(
                    html_str=html_content,
                    css_str=css_str_param,
                    save_as=output_filename,
                )
                logger.debug(f"html2image returned output_files: {output_files}")
            else:
                logger.error("Screenshot method not available")
                return None

            # Enhanced file finding logic
            possible_paths = []
            
            # Check returned paths from html2image
            if output_files and len(output_files) > 0:  # type: ignore
                for path in output_files:  # type: ignore
                    if isinstance(path, str):
                        possible_paths.append(path)
                        logger.debug(f"html2image reported file at: {path}")
            
            # Add additional search locations
            possible_paths.extend([
                # Expected path in configured output directory
                os.path.join(self.output_path, output_filename),
                # Path in html2image's internal output directory
                os.path.join(getattr(self.hti, 'output_path', self.output_path), output_filename) if hasattr(self.hti, 'output_path') else None,
                # Current working directory
                os.path.join(os.getcwd(), output_filename),
                # Temp directory
                os.path.join(tempfile.gettempdir(), output_filename),
                # html2image's default output directory
                os.path.join(tempfile.gettempdir(), "html2image", output_filename),
                # Common html2image output locations
                os.path.join(os.getcwd(), "screenshots", output_filename),
                os.path.join(self.output_path, "screenshots", output_filename),
            ])
            
            # Remove None values and duplicates
            possible_paths = list(set([p for p in possible_paths if p is not None]))
            
            # Search for the actual file
            found_file = None
            for path in possible_paths:
                logger.debug(f"Checking for file at: {path}")
                if os.path.exists(path) and os.path.isfile(path):
                    found_file = path
                    logger.info(f"Found output file at: {path}")
                    break
            
            if not found_file:
                logger.error(f"Failed to find PNG file: {output_filename}")
                logger.error(f"Searched locations: {possible_paths}")
                
                # List files in output directory for debugging
                try:
                    files_in_output = os.listdir(self.output_path)
                    logger.debug(f"Files in output directory {self.output_path}: {files_in_output}")
                except Exception as e:
                    logger.debug(f"Could not list files in output directory: {e}")
                
                return None

            logger.info(f"Successfully generated PNG: {found_file}")
            return found_file

        except Exception as e:
            logger.exception(f"Error converting HTML to PNG: {e}")
            raise RuntimeError(f"Error converting HTML to PNG: {e}")

    def cleanup(self) -> None:
        """
        Clean up resources used by the converter.

        This method should be called when the converter is no longer needed
        to free up resources.
        """
        if hasattr(self, 'hti') and self.hti is not None:
            # Close the browser if possible
            if hasattr(self.hti, 'browser'):
                try:
                    # Use getattr to avoid type checking issues
                    browser = getattr(self.hti, 'browser', None)
                    if browser is not None:
                        close_method = getattr(browser, 'close', None)
                        if close_method and callable(close_method):
                            close_method()
                            logger.debug("Browser closed successfully")
                except Exception as e:
                    logger.warning(f"Failed to close browser: {e}")

            # Set to None to allow garbage collection
            self.hti = None
            logger.info("HtmlToPngConverter resources cleaned up")


def is_html2image_available() -> bool:
    """
    Check if html2image is available.

    Returns:
        True if html2image is available, False otherwise
    """
    return HTML2IMAGE_AVAILABLE


def create_converter(
    size: tuple[int, int] = (400, 300),
    output_path: Optional[str] = None,
    custom_flags: Optional[list] = None,
) -> Optional[HtmlToPngConverter]:
    """
    Create an HTML to PNG converter instance.

    This is a convenience function to create a converter instance
    with error handling.

    Args:
        size: Tuple of (width, height) for the output image
        output_path: Directory to save output images (uses temp dir if None)
        custom_flags: Custom browser flags to minimize resource usage

    Returns:
        HtmlToPngConverter instance or None if creation failed
    """
    if not HTML2IMAGE_AVAILABLE:
        logger.error("html2image is not installed. Install with: pip install html2image")
        return None

    try:
        return HtmlToPngConverter(size=size, output_path=output_path, custom_flags=custom_flags)
    except Exception as e:
        logger.exception(f"Failed to create HtmlToPngConverter: {e}")
        return None
