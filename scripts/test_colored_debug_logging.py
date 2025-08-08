#!/usr/bin/env python3
"""Test script to verify DEBUG logs include colored filename."""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from calendarbot.utils.logging import get_logger, setup_logging


def test_colored_debug_logging() -> None:
    """Test that DEBUG logs include colored filename."""
    print("Testing DEBUG logging with colored filename...")

    # Set up logging with DEBUG level
    logger = setup_logging(log_level="DEBUG")

    # Get a test logger
    test_logger = get_logger("test_module")

    print("\nTesting different log levels with colors:")
    test_logger.info("This is an INFO message - should not include filename")
    test_logger.warning("This is a WARNING message - should not include filename")
    test_logger.debug("This is a DEBUG message - should include COLORED filename")
    test_logger.error("This is an ERROR message - should not include filename")

    print("\nTesting with main logger:")
    logger.debug("Main logger DEBUG message - should include COLORED filename")
    logger.info("Main logger INFO message - should not include filename")

    print("\nNote: The filename in DEBUG logs should appear in bright cyan/bold color!")


if __name__ == "__main__":
    test_colored_debug_logging()
