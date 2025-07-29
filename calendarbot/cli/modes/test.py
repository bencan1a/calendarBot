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

        from ..config import apply_cli_overrides
        from ..runtime_integration import (
            create_runtime_tracker,
            start_runtime_tracking,
            stop_runtime_tracking,
        )

        # Apply command-line logging overrides
        updated_settings = apply_command_line_overrides(settings, args)

        # Apply CLI-specific overrides
        updated_settings = apply_cli_overrides(updated_settings, args)

        # Set up enhanced logging for test mode
        logger = setup_enhanced_logging(updated_settings, interactive_mode=False)
        logger.info("Enhanced logging initialized for test mode")

        # Initialize runtime tracking if enabled
        runtime_tracker = create_runtime_tracker(updated_settings)
        session_name = "test_mode"
        if hasattr(updated_settings, "runtime_tracking") and updated_settings.runtime_tracking:
            session_name = getattr(updated_settings.runtime_tracking, "session_name", "test_mode")

        # Start runtime tracking if enabled
        if runtime_tracker:
            start_runtime_tracking(runtime_tracker, "test_mode", session_name)

        try:
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

        finally:
            # Stop runtime tracking if it was started
            if runtime_tracker:
                stop_runtime_tracking(runtime_tracker, "test_mode")

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
