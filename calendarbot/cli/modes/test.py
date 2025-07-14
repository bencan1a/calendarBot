"""Test mode handler for Calendar Bot CLI.

This module provides the test mode functionality for validating
Calendar Bot components and configuration.
"""

import asyncio
from typing import Any


async def run_test_mode(args: Any) -> int:
    """Run Calendar Bot in test/validation mode.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        from calendarbot.config.settings import settings
        from calendarbot.utils.logging import apply_command_line_overrides, setup_enhanced_logging
        from calendarbot.validation import ValidationRunner

        from ..config import apply_rpi_overrides

        # Apply command-line logging overrides
        updated_settings = apply_command_line_overrides(settings, args)

        # Apply RPI-specific overrides
        updated_settings = apply_rpi_overrides(updated_settings, args)

        # Set up enhanced logging for test mode
        logger = setup_enhanced_logging(updated_settings, interactive_mode=False)
        logger.info("Enhanced logging initialized for test mode")

        # Create validation runner
        validation_runner = ValidationRunner(
            test_date=getattr(args, "date", None),
            end_date=getattr(args, "end_date", None),
            components=getattr(args, "components", ["sources", "cache", "display"]),
            use_cache=not getattr(args, "no_cache", False),
            output_format=getattr(args, "output_format", "console"),
        )

        # Run validation
        logger.info("Starting Calendar Bot validation...")
        results = await validation_runner.run_validation()

        # Print results
        validation_runner.print_results(verbose=getattr(args, "verbose", False))

        # Return appropriate exit code
        if results.has_failures():
            logger.error("Validation completed with failures")
            return 1
        elif results.has_warnings():
            logger.warning("Validation completed with warnings")
            return 0  # Warnings don't cause failure
        else:
            logger.info("Validation completed successfully")
            return 0

    except KeyboardInterrupt:
        print("\nTest mode interrupted")
        return 1
    except ImportError as e:
        print(f"Import error in test mode: {e}")
        return 1
    except Exception as e:
        print(f"Test mode error: {e}")
        return 1


__all__ = [
    "run_test_mode",
]
