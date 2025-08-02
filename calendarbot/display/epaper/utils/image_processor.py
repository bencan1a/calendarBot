"""Image processor class for e-Paper display image handling."""

import logging

from PIL import Image, ImageEnhance

from ..capabilities import DisplayCapabilities
from .image_processing import (
    convert_image_to_epaper_format,
    create_test_pattern,
    resize_image_for_epaper,
)

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Image processor for converting PIL Images to e-Paper display format.

    This class handles the conversion of PIL Images to formats suitable for
    e-Paper displays, including resizing, color conversion, and format optimization.
    """

    def __init__(self) -> None:
        """Initialize the image processor."""
        logger.debug("ImageProcessor initialized")

    def convert_to_display_format(
        self, image: Image.Image, capabilities: DisplayCapabilities
    ) -> bytes:
        """Convert PIL Image to e-Paper display format.

        Args:
            image: PIL Image to convert
            capabilities: Display capabilities defining format requirements

        Returns:
            Bytes in e-Paper display format

        Raises:
            ValueError: If image or capabilities are invalid
        """
        if not isinstance(image, Image.Image):
            raise TypeError("Input must be a PIL Image")

        if not isinstance(capabilities, DisplayCapabilities):
            raise TypeError("Capabilities must be a DisplayCapabilities instance")

        try:
            # Resize image to match display dimensions
            resized_image = resize_image_for_epaper(
                image, capabilities.width, capabilities.height, maintain_aspect_ratio=True
            )

            # Convert to e-Paper format based on capabilities
            if capabilities.supports_red:
                # Convert with red support
                display_buffer = convert_image_to_epaper_format(
                    resized_image, threshold=128, red_threshold=200
                )
            else:
                # Convert to black/white only
                display_buffer = convert_image_to_epaper_format(
                    resized_image, threshold=128, red_threshold=None
                )

            logger.debug(
                f"Converted image to e-Paper format: {len(display_buffer)} bytes, "
                f"red_support={capabilities.supports_red}"
            )

            return display_buffer

        except Exception:
            logger.exception("Failed to convert image to display format")
            raise

    def resize_for_display(
        self,
        image: Image.Image,
        capabilities: DisplayCapabilities,
        maintain_aspect_ratio: bool = True,
    ) -> Image.Image:
        """Resize image for e-Paper display.

        Args:
            image: PIL Image to resize
            capabilities: Display capabilities defining target dimensions
            maintain_aspect_ratio: Whether to maintain aspect ratio

        Returns:
            Resized PIL Image

        Raises:
            ValueError: If image or capabilities are invalid
        """
        if not isinstance(image, Image.Image):
            raise TypeError("Input must be a PIL Image")

        if not isinstance(capabilities, DisplayCapabilities):
            raise TypeError("Capabilities must be a DisplayCapabilities instance")

        try:
            resized_image = resize_image_for_epaper(
                image,
                capabilities.width,
                capabilities.height,
                maintain_aspect_ratio=maintain_aspect_ratio,
            )

            logger.debug(
                f"Resized image from {image.size} to {resized_image.size}, "
                f"aspect_ratio_maintained={maintain_aspect_ratio}"
            )

            return resized_image

        except Exception:
            logger.exception("Failed to resize image")
            raise

    def optimize_for_eink(self, image: Image.Image) -> Image.Image:
        """Optimize image for e-Ink display characteristics.

        Args:
            image: PIL Image to optimize

        Returns:
            Optimized PIL Image

        Raises:
            ValueError: If image is invalid
        """
        if not isinstance(image, Image.Image):
            raise TypeError("Input must be a PIL Image")

        try:
            # Convert to RGB if not already
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Apply e-Ink optimizations
            # 1. Increase contrast for better e-Ink visibility

            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            enhanced_image = enhancer.enhance(1.2)  # 20% contrast boost

            # Enhance sharpness for crisp text
            sharpness_enhancer = ImageEnhance.Sharpness(enhanced_image)
            optimized_image = sharpness_enhancer.enhance(1.1)  # 10% sharpness boost

            logger.debug("Applied e-Ink optimizations (contrast, sharpness)")

            return optimized_image

        except Exception:
            logger.exception("Failed to optimize image for e-Ink")
            raise

    def create_test_image(self, capabilities: DisplayCapabilities) -> bytes:
        """Create a test image for e-Paper display validation.

        Args:
            capabilities: Display capabilities defining format requirements

        Returns:
            Test image in e-Paper display format
        """
        try:

            test_buffer = create_test_pattern(
                capabilities.width, capabilities.height, has_red=capabilities.supports_red
            )

            logger.info(
                f"Created test pattern: {capabilities.width}x{capabilities.height}, "
                f"red_support={capabilities.supports_red}"
            )

            return test_buffer

        except Exception:
            logger.exception("Failed to create test image")
            raise
