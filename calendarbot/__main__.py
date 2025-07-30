"""Entry point for `python -m calendarbot` command.

This module provides the standard Python module execution interface that
delegates to the comprehensive CLI module, following Python packaging
best practices with proper internal imports.
"""

import asyncio
import logging
import sys

logger = logging.getLogger(__name__)

try:
    from calendarbot.cli import main_entry
except ImportError:
    logger.exception("Error importing main entry point")
    logger.info("Make sure you're running from the Calendar Bot project directory.")
    sys.exit(1)


def main() -> None:
    """Entry point for python -m calendarbot.

    This function maintains compatibility with setuptools entry points
    while delegating all functionality to the comprehensive CLI module.
    """
    try:
        exit_code = asyncio.run(main_entry())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
