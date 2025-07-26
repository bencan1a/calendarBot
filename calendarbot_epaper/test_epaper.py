#!/usr/bin/env python3
"""Test script for calendarbot_epaper package."""

import argparse
import logging
import sys
import time
from typing import Any, Dict, Optional

from PIL import Image

from calendarbot_epaper.display.capabilities import DisplayCapabilities
from calendarbot_epaper.display.region import Region
from calendarbot_epaper.drivers.waveshare.epd4in2b_v2 import EPD4in2bV2
from calendarbot_epaper.utils.image_processing import create_test_pattern, render_text_to_image
from calendarbot_epaper.utils.logging import setup_logger


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Test calendarbot_epaper package")
    parser.add_argument("--test-pattern", action="store_true", help="Display test pattern")
    parser.add_argument("--text", type=str, help="Display text")
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )

    return parser.parse_args()


def initialize_display() -> Optional[EPD4in2bV2]:
    """Initialize e-Paper display.

    Returns:
        Initialized display driver or None if initialization failed
    """
    logger.info("Initializing e-Paper display...")

    try:
        # Create display driver
        display = EPD4in2bV2()

        # Initialize display
        if not display.initialize():
            logger.error("Failed to initialize display")
            return None

        # Get display capabilities
        capabilities = display.get_capabilities()
        logger.info(f"Display capabilities: {capabilities}")

        return display

    except Exception as e:
        logger.error(f"Failed to initialize display: {e}")
        return None


def display_test_pattern(display: EPD4in2bV2) -> bool:
    """Display test pattern.

    Args:
        display: Display driver

    Returns:
        True if successful, False otherwise
    """
    logger.info("Displaying test pattern...")

    try:
        # Get display capabilities
        capabilities = display.get_capabilities()

        # Create test pattern
        buffer = create_test_pattern(
            capabilities.width, capabilities.height, capabilities.supports_red
        )

        # Display test pattern
        if not display.render(buffer):
            logger.error("Failed to render test pattern")
            return False

        logger.info("Test pattern displayed successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to display test pattern: {e}")
        return False


def display_text(display: EPD4in2bV2, text: str) -> bool:
    """Display text.

    Args:
        display: Display driver
        text: Text to display

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Displaying text: {text}")

    try:
        # Get display capabilities
        capabilities = display.get_capabilities()

        # Create text image
        image = render_text_to_image(
            text,
            capabilities.width,
            capabilities.height,
            font_size=36,
            text_color=(0, 0, 0),  # black as RGB tuple
            bg_color=(255, 255, 255),  # white as RGB tuple
            align="center",
        )

        # Convert image to e-Paper format
        from calendarbot_epaper.utils.image_processing import convert_image_to_epaper_format

        buffer = convert_image_to_epaper_format(image)

        # Display text
        if not display.render(buffer):
            logger.error("Failed to render text")
            return False

        logger.info("Text displayed successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to display text: {e}")
        return False


def main() -> int:
    """Main function.

    Returns:
        Exit code
    """
    args = parse_args()

    # Initialize display
    display = initialize_display()
    if display is None:
        return 1

    try:
        # Display test pattern or text
        if args.test_pattern:
            if not display_test_pattern(display):
                return 1
        elif args.text:
            if not display_text(display, args.text):
                return 1
        else:
            logger.error("No test specified")
            return 1

        # Wait for user to see the display
        logger.info("Press Ctrl+C to exit...")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Exiting...")

    finally:
        # Shutdown display
        logger.info("Shutting down display...")
        display.shutdown()

    return 0


if __name__ == "__main__":
    # Setup logger
    logger = setup_logger("calendarbot_epaper", "INFO")

    # Run main function
    sys.exit(main())
