"""Command-line argument parsing for Calendar Bot.

This module handles all command-line argument parsing functionality,
including setup of argument groups, validation, and parsing logic.
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from calendarbot.layout.exceptions import LayoutError
from calendarbot.layout.registry import LayoutRegistry

logger = logging.getLogger(__name__)


class LayoutAction(argparse.Action):
    """Custom argparse action for layout validation using Layout Registry.

    This action validates layout names against available layouts discovered
    by the Layout Registry, providing dynamic validation instead of hardcoded choices.
    """

    def __init__(
        self,
        option_strings: list[str],
        dest: str,
        layout_registry: Optional[LayoutRegistry] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the layout action.

        Args:
            option_strings: Command line option strings (e.g., ['--layout'])
            dest: Destination attribute name for parsed value
            layout_registry: Optional LayoutRegistry instance to use for validation
            **kwargs: Additional argparse action arguments
        """
        # Remove choices if provided since we handle validation dynamically
        kwargs.pop("choices", None)
        self.layout_registry = layout_registry
        super().__init__(option_strings, dest, **kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        _option_string: Optional[str] = None,
    ) -> None:
        """Validate and set layout value using Layout Registry.

        Args:
            parser: The ArgumentParser instance
            namespace: The Namespace object to store parsed values
            values: The layout name to validate
            option_string: The option string used to invoke this action

        Raises:
            argparse.ArgumentTypeError: If layout is invalid or registry fails
        """
        layout_name = str(values)

        try:
            # Use provided registry or create new one for validation
            if self.layout_registry is not None:
                registry = self.layout_registry
            else:
                registry = LayoutRegistry()

            # Validate layout exists
            if not registry.validate_layout(layout_name):
                available_layouts = registry.get_available_layouts()
                if available_layouts:
                    self._raise_invalid_layout_error(layout_name, available_layouts)
                self._raise_no_layouts_error(layout_name)

            # Set the validated layout name
            setattr(namespace, self.dest, layout_name)

        except argparse.ArgumentTypeError:
            # Re-raise argparse errors to let argparse handle them
            raise

        except LayoutError as e:
            logger.warning(f"Layout registry error during CLI validation: {e}")
            # Fallback to filesystem-based validation for backward compatibility
            fallback_layouts = self._get_fallback_layouts()
            if layout_name not in fallback_layouts:
                self._raise_fallback_error(layout_name, fallback_layouts, "registry error")
            setattr(namespace, self.dest, layout_name)

        except Exception:
            logger.exception("Unexpected error during layout validation")
            # Fallback to filesystem-based validation for robustness
            fallback_layouts = self._get_fallback_layouts()
            if layout_name not in fallback_layouts:
                self._raise_fallback_error(layout_name, fallback_layouts, "error")
            setattr(namespace, self.dest, layout_name)

    def _raise_invalid_layout_error(self, layout_name: str, available_layouts: list[str]) -> None:
        """Raise an error for invalid layout when layouts are available.

        Args:
            layout_name: The invalid layout name
            available_layouts: List of available layout names

        Raises:
            argparse.ArgumentTypeError: With formatted error message
        """
        raise argparse.ArgumentTypeError(
            f"Invalid layout '{layout_name}'. Available layouts: {', '.join(available_layouts)}"
        )

    def _raise_no_layouts_error(self, layout_name: str) -> None:
        """Raise an error for invalid layout when no layouts are available.

        Args:
            layout_name: The invalid layout name

        Raises:
            argparse.ArgumentTypeError: With formatted error message
        """
        raise argparse.ArgumentTypeError(f"Invalid layout '{layout_name}'. No layouts available.")

    def _get_fallback_layouts(self) -> list[str]:
        """Get fallback layouts using filesystem discovery.

        Returns:
            List of layout names available in the filesystem.
        """
        try:
            layouts_dir = Path(__file__).parent.parent / "layouts"
            if layouts_dir.exists():
                available_layouts = [
                    layout_dir.name
                    for layout_dir in layouts_dir.iterdir()
                    if layout_dir.is_dir() and (layout_dir / "layout.json").exists()
                ]
                if available_layouts:
                    return available_layouts
        except Exception:
            logger.exception("Filesystem layout discovery failed")

        # Ultimate fallback - only layouts known to exist
        return ["4x8", "whats-next-view"]

    def _raise_fallback_error(
        self, layout_name: str, legacy_layouts: list[str], reason: str
    ) -> None:
        """Raise an error for invalid layout when using fallback validation.

        Args:
            layout_name: The invalid layout name
            legacy_layouts: List of legacy layout names
            reason: The reason for fallback validation

        Raises:
            argparse.ArgumentTypeError: With formatted error message
        """
        raise argparse.ArgumentTypeError(
            f"Invalid layout '{layout_name}'. "
            f"Available layouts: {', '.join(legacy_layouts)} "
            f"(using fallback validation due to {reason})"
        )


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser with comprehensive configuration options.

    Builds a comprehensive ArgumentParser with all supported command-line options
    organized into logical groups for setup, testing, display modes, logging,
    and operational modes (web, epaper).

    Returns:
        argparse.ArgumentParser: Fully configured ArgumentParser instance with all
            command-line options, help text, and validation rules

    Example:
        >>> parser = create_parser()
        >>> args = parser.parse_args(['--web', '--port', '3000', '--verbose'])
        >>> print(f"Running web server on port {args.port}")
    """
    parser = argparse.ArgumentParser(
        description="Calendar Bot - ICS calendar display with interactive navigation and web interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run in web server mode (default)
  %(prog)s --setup                   # Run first-time configuration wizard
  %(prog)s --backup                  # Backup current configuration
  %(prog)s --list-backups            # List available configuration backups
  %(prog)s --restore backup_file.yaml # Restore configuration from backup
  %(prog)s --web                     # Run web server mode on localhost:8080 (explicit)
  %(prog)s --web --port 3000 --auto-open  # Run web server on port 3000 and open browser
  %(prog)s --epaper                  # Run in e-paper display mode with hardware auto-detection
        """,
    )

    # Setup and configuration arguments
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run first-time configuration wizard (creates config.yaml)",
    )

    parser.add_argument(
        "--backup", action="store_true", help="Backup current configuration to timestamped file"
    )

    parser.add_argument(
        "--restore", metavar="BACKUP_FILE", help="Restore configuration from backup file"
    )

    parser.add_argument(
        "--list-backups", action="store_true", help="List available configuration backups"
    )

    parser.add_argument(
        "--version", action="version", version="%(prog)s 1.0.0", help="Show version information"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging and detailed output"
    )

    parser.add_argument(
        "--kill-duplicates",
        action="store_true",
        help="Kill existing calendarbot processes on startup (disabled by default)",
    )

    # Performance tracking arguments
    performance_group = parser.add_argument_group(
        "performance", "Runtime resource consumption tracking options"
    )

    performance_group.add_argument(
        "--track-runtime",
        action="store_true",
        help="Enable runtime resource tracking with automatic storage (CPU and memory usage, 1.0s sampling)",
    )

    performance_group.add_argument(
        "--pi-optimized",
        dest="pi_optimized",
        action="store_true",
        help="Enable consolidated Pi-optimized mode (equivalent to setting CALENDARBOT_PI_OPTIMIZED=1)",
    )

    # Web mode arguments
    parser.add_argument(
        "--web",
        "-w",
        action="store_true",
        help="Run in web server mode for browser-based calendar viewing",
    )

    parser.add_argument(
        "--port", type=int, default=8080, help="Port for web server (default: 8080, web mode only)"
    )

    parser.add_argument(
        "--host",
        default=None,
        help="Host for web server (default: auto-detect local network interface, web mode only)",
    )

    parser.add_argument(
        "--auto-open", action="store_true", help="Automatically open browser when starting web mode"
    )

    # E-Paper mode arguments
    parser.add_argument(
        "--epaper",
        "-e",
        action="store_true",
        help="Run in e-paper display mode with hardware detection and PNG fallback",
    )

    # Display and layout arguments
    display_group = parser.add_argument_group("display", "Display type and layout options")

    display_group.add_argument(
        "--layout",
        action=LayoutAction,
        dest="display_type",
        default=None,
        help="Layout to use for calendar display (dynamically validated against available layouts)",
    )

    display_group.add_argument(
        "--renderer",
        choices=["html"],
        default=None,
        help="Renderer type: html (web browser)",
    )

    # Comprehensive logging arguments
    logging_group = parser.add_argument_group(
        "logging", "Comprehensive logging configuration options"
    )

    # Log level options
    logging_group.add_argument(
        "--log-level",
        choices=["DEBUG", "VERBOSE", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set both console and file log levels",
    )

    logging_group.add_argument(
        "--console-level",
        choices=["DEBUG", "VERBOSE", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set console log level specifically",
    )

    logging_group.add_argument(
        "--file-level",
        choices=["DEBUG", "VERBOSE", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set file log level specifically",
    )

    # Quick options
    logging_group.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only show errors on console (sets console level to ERROR)",
    )

    # File logging options
    logging_group.add_argument("--log-dir", type=Path, help="Custom directory for log files")

    logging_group.add_argument(
        "--no-file-logging", action="store_true", help="Disable file logging completely"
    )

    logging_group.add_argument(
        "--max-log-files", type=int, help="Maximum number of log files to keep (default: 5)"
    )

    # Console options
    logging_group.add_argument(
        "--no-console-logging", action="store_true", help="Disable console logging completely"
    )

    logging_group.add_argument(
        "--no-log-colors", action="store_true", help="Disable colored console output"
    )

    return parser


def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format for command-line arguments.

    Validates and converts a date string into a datetime object for use
    in test mode and date range operations.

    Args:
        date_str (str): Date string to parse in YYYY-MM-DD format

    Returns:
        datetime: Parsed datetime object set to midnight (00:00:00)

    Raises:
        argparse.ArgumentTypeError: If date format is invalid or date is not parseable

    Example:
        >>> date_obj = parse_date("2024-01-15")
        >>> print(date_obj)  # 2024-01-15 00:00:00
        >>>
        >>> # Invalid format raises error
        >>> parse_date("15-01-2024")  # Raises ArgumentTypeError
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as err:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: {date_str}. Use YYYY-MM-DD"
        ) from err


__all__ = [
    "LayoutAction",
    "create_parser",
    "parse_date",
]
