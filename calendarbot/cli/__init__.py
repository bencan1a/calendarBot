"""CLI module for Calendar Bot application.

This module provides the command-line interface functionality for Calendar Bot,
including argument parsing, configuration management, and mode execution.

This module is part of the architectural refactoring to eliminate the root-level
import anti-pattern and establish proper internal package structure.
"""

from .config import (
    apply_cli_overrides,
    backup_configuration,
    check_configuration,
    list_backups,
    restore_configuration,
    show_setup_guidance,
)
from .modes.epaper import run_epaper_mode
from .modes.interactive import run_interactive_mode
from .modes.test import run_test_mode
from .modes.web import run_web_mode
from .parser import create_parser, parse_components, parse_date
from .setup import run_setup_wizard


async def main_entry() -> int:
    """Main entry point with argument parsing and first-run detection.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = create_parser()
    args = parser.parse_args()

    # Handle setup wizard
    if hasattr(args, "setup") and args.setup:
        return await run_setup_wizard()

    # Handle backup operations
    if hasattr(args, "backup") and args.backup:
        return backup_configuration()

    if hasattr(args, "restore") and args.restore:
        return restore_configuration(args.restore)

    if hasattr(args, "list_backups") and args.list_backups:
        return list_backups()

    # Validate mutually exclusive modes BEFORE executing any mode
    mode_count = sum(
        [
            getattr(args, "test_mode", False),
            getattr(args, "interactive", False),
            getattr(args, "web", False),
            getattr(args, "epaper", False),
        ]
    )
    if mode_count > 1:
        parser.error(
            "Only one mode can be specified: --test-mode, --interactive, --web, or --epaper"
        )

    # Handle test mode - can run even without configuration
    if hasattr(args, "test_mode") and args.test_mode:
        return await run_test_mode(args)

    # Check if configuration exists
    is_configured, config_path = check_configuration()

    # If not configured and not running setup or test, show guidance
    if not is_configured:
        show_setup_guidance()
        print(f"\n💡 Tip: Run 'calendarbot --setup' to get started quickly!\n")
        return 1

    # Run in specified mode
    if hasattr(args, "interactive") and args.interactive:
        return await run_interactive_mode(args)
    elif hasattr(args, "epaper") and args.epaper:
        return await run_epaper_mode(args)
    else:
        # Default to web mode when no other mode is specified
        return await run_web_mode(args)


__all__ = [
    "main_entry",
    "create_parser",
    "parse_date",
    "parse_components",
    "check_configuration",
    "show_setup_guidance",
    "apply_cli_overrides",
    "run_setup_wizard",
    "backup_configuration",
    "restore_configuration",
    "list_backups",
    "run_interactive_mode",
    "run_web_mode",
    "run_test_mode",
    "run_epaper_mode",
]
