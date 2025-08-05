#!/usr/bin/env python3
"""
Test script for e-paper emulation mode with processed image visualization.

This script creates a simple test image and runs it through the e-paper
emulation pipeline to verify that both the original PNG and the processed
visualization are generated correctly.
"""

import logging
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image, ImageDraw, ImageFont

from calendarbot.cli.modes.epaper import save_png_emulation

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def create_test_image(width: int = 400, height: int = 300) -> Image.Image:
    """Create a test image with black, white, and red elements.

    Args:
        width: Image width
        height: Image height

    Returns:
        PIL Image with test pattern
    """
    # Create a white background
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Draw black border
    draw.rectangle(((0, 0), (width - 1, height - 1)), outline=(0, 0, 0))

    # Draw black text
    try:
        font = ImageFont.truetype("Arial", 24)
    except OSError:
        font = ImageFont.load_default()

    draw.text((width // 2 - 100, 20), "E-Paper Test", fill=(0, 0, 0), font=font)

    # Draw black shapes
    draw.rectangle(((50, 50), (150, 150)), outline=(0, 0, 0), fill=(0, 0, 0))
    draw.ellipse(((200, 50), (300, 150)), outline=(0, 0, 0))

    # Draw red elements
    draw.rectangle(((50, 200), (150, 250)), outline=(255, 0, 0), fill=(255, 0, 0))
    draw.text((200, 200), "RED TEXT", fill=(255, 0, 0), font=font)

    # Draw some grayscale elements
    for i in range(10):
        gray_value = i * 25
        draw.rectangle(
            ((350, 50 + i * 20), (380, 70 + i * 20)),
            outline=(0, 0, 0),
            fill=(gray_value, gray_value, gray_value),
        )

    return image


def main():
    """Run the e-paper emulation test."""
    logger.info("Creating test image...")
    test_image = create_test_image()

    logger.info("Saving test image through e-paper emulation pipeline...")
    png_path, processed_path = save_png_emulation(test_image, "test")

    logger.info(f"Original PNG saved to: {png_path}")
    if processed_path:
        logger.info(f"Processed visualization saved to: {processed_path}")
    else:
        logger.error("Failed to generate processed visualization!")
        return 1

    logger.info("Test completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
