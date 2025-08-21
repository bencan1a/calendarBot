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
from pathlib import Path
from typing import Any, Optional

# Import html2image conditionally to handle environments where it's not installed
try:
    from html2image import Html2Image  # type: ignore[import]

    HTML2IMAGE_AVAILABLE = True
except ImportError:
    HTML2IMAGE_AVAILABLE = False
    Html2Image = None  # type: ignore

# Import PIL for image cropping
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None  # type: ignore

# For type checking only
from typing import TypeVar

# Define HTI type for type checking
HTI = TypeVar("HTI")

logger = logging.getLogger(__name__)

size_override: tuple[int, int] = (300, 500)


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
    _instance: Optional["HtmlToPngConverter"] = None

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "HtmlToPngConverter":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False  # type: ignore[attr-defined] # noqa: SLF001
        return cls._instance

    def __init__(
        self,
        size: tuple[int, int] = (300, 400),
        output_path: Optional[str] = None,
        custom_flags: Optional[list[str]] = None,
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
        if getattr(self, "_initialized", False):
            return

        if not HTML2IMAGE_AVAILABLE:
            logger.error("html2image is not installed. Install with: pip install html2image")
            raise ImportError("html2image is not installed")

        self.size = size

        # Use system temp directory if output_path is not specified
        self.output_path = output_path or tempfile.gettempdir()

        # Default flags optimized for minimal resource usage
        default_flags = [
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-dev-shm-usage",
            "--disable-setuid-sandbox",
            "--no-sandbox",
            "--headless",
            "--disable-extensions",
            "--disable-component-extensions-with-background-pages",
            "--disable-default-apps",
            "--mute-audio",
            "--hide-scrollbars",
            "--disable-background-networking",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-breakpad",
            "--disable-client-side-phishing-detection",
            "--disable-features=TranslateUI,BlinkGenPropertyTrees",
            "--disable-hang-monitor",
            "--disable-ipc-flooding-protection",
            "--disable-prompt-on-repost",
            "--disable-renderer-backgrounding",
            "--force-color-profile=srgb",
            "--metrics-recording-only",
            "--no-first-run",
            "--password-store=basic",
            "--use-mock-keychain",
            f"--ash-host-window-bounds={size_override[0]}x{size_override[1]}",
            f"--window-size={size_override[0]},{size_override[1]}",
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
                raise ImportError("html2image is not installed")  # noqa: TRY301
        except Exception:
            logger.exception("Failed to initialize HtmlToPngConverter")
            raise

    def crop_image_to_target_size(
        self, image_path: str, target_size: tuple[int, int] = (300, 400), crop_from_top: bool = True
    ) -> Optional[str]:
        """
        Crop an image to the target size, taking pixels from the top.

        Args:
            image_path: Path to the source image file
            target_size: Tuple of (width, height) for the cropped image
            crop_from_top: If True, crop from top; if False, crop from center

        Returns:
            Path to the cropped image file or None if cropping failed

        Raises:
            RuntimeError: If PIL is not available or cropping fails
        """
        if not PIL_AVAILABLE or Image is None:
            logger.error("PIL/Pillow is not installed. Install with: pip install Pillow")
            raise RuntimeError("PIL/Pillow is not installed")

        try:
            # Open the source image
            with Image.open(image_path) as img:
                logger.info(f"Original image size: {img.size}")

                # Calculate crop box
                img_width, img_height = img.size
                target_width, target_height = target_size

                if img_width < target_width or img_height < target_height:
                    logger.warning(f"Source image {img.size} is smaller than target {target_size}")
                    return image_path  # Return original if too small

                if crop_from_top:
                    # Crop from top-left corner
                    left = 0
                    top = 0
                    right = min(target_width, img_width)
                    bottom = min(target_height, img_height)
                else:
                    # Crop from center
                    left = max(0, (img_width - target_width) // 2)
                    top = max(0, (img_height - target_height) // 2)
                    right = left + target_width
                    bottom = top + target_height

                # Perform the crop
                cropped_img = img.crop((left, top, right, bottom))
                logger.info(f"Cropped image size: {cropped_img.size}")

                # Create output filename for cropped image
                path_obj = Path(image_path)
                cropped_path = path_obj.parent / f"{path_obj.stem}_cropped{path_obj.suffix}"

                # Save the cropped image
                cropped_img.save(str(cropped_path), format="PNG")
                logger.info(f"Cropped image saved to: {cropped_path}")

                return str(cropped_path)

        except Exception:
            logger.exception("Error cropping image {image_path}")
            return None

    def convert_url_to_png(
        self,
        url: str,
        output_filename: Optional[str] = None,
    ) -> Optional[str]:
        """
        Convert a URL to a PNG image by navigating to it directly.

        This method uses the browser to navigate to a URL and capture a screenshot,
        following the html2image documentation's recommended approach.

        Args:
            url: URL to navigate to and capture
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
            if not output_filename.lower().endswith(".png"):
                output_filename += ".png"

            logger.info(f"Converting URL to PNG: {url} -> {output_filename}")

            # Ensure the output directory exists
            Path(self.output_path).mkdir(parents=True, exist_ok=True)

            # Use html2image direct URL approach (recommended by documentation)
            logger.info(f"Capturing URL: {url}")

            try:
                # Direct URL capture - pass size parameter explicitly per html2image docs
                if self.hti is None:
                    logger.error("Html2Image instance (self.hti) is None")
                    return None
                output_files = self.hti.screenshot(
                    url=url, save_as=output_filename, size=(size_override[0], size_override[1])
                )
                logger.debug(f"html2image returned output_files: {output_files}")

                if output_files and len(output_files) > 0:
                    original_path = output_files[0]
                    logger.info(f"Original image captured: {original_path}")

                    # Crop the image to 300x400 pixels from the top
                    cropped_path = self.crop_image_to_target_size(
                        original_path, target_size=(300, 400), crop_from_top=True
                    )

                    if cropped_path:
                        logger.info(f"Image successfully cropped to 300x400: {cropped_path}")
                        return cropped_path
                    logger.warning("Failed to crop image, returning original")
                    return original_path  # type: ignore[no-any-return]

                return None

            except Exception:
                logger.exception("Direct URL screenshot failed")
                return None

        except Exception as exc:
            logger.exception("Error converting URL to PNG")
            raise RuntimeError("Error converting URL to PNG") from exc

    def cleanup(self) -> None:
        """
        Clean up resources used by the converter.

        This method should be called when the converter is no longer needed
        to free up resources.
        """
        if hasattr(self, "hti") and self.hti is not None:
            # Close the browser if possible
            if hasattr(self.hti, "browser"):
                try:
                    # Use getattr to avoid type checking issues
                    browser = getattr(self.hti, "browser", None)
                    if browser is not None:
                        close_method = getattr(browser, "close", None)
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
    size: tuple[int, int] = (300, 400),
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
    except Exception:
        logger.exception("Failed to create HtmlToPngConverter")
        return None
