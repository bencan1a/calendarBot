"""Command-line argument parsing for Calendar Bot.

This module handles all command-line argument parsing functionality,
including setup of argument groups, validation, and parsing logic.
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from calendarbot.layout.exceptions import LayoutError
from calendarbot.layout.registry import LayoutRegistry

logger = logging.getLogger(__name__)


class LayoutAction(argparse.Action):
    """Custom argparse action for layout validation using Layout Registry.

    This action validates layout names against available layouts discovered
    by the Layout Registry, providing dynamic validation instead of hardcoded choices.
    """

    def __init__(self, option_strings: List[str], dest: str, **kwargs: Any) -> None:
        """Initialize the layout action.

        Args:
            option_strings: Command line option strings (e.g., ['--layout'])
            dest: Destination attribute name for parsed value
            **kwargs: Additional argparse action arguments
        """
        # Remove choices if provided since we handle validation dynamically
        kwargs.pop("choices", None)
        super().__init__(option_strings, dest, **kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: Optional[str] = None,
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
            # Initialize layout registry for validation
            registry = LayoutRegistry()

            # Validate layout exists
            if not registry.validate_layout(layout_name):
                available_layouts = registry.get_available_layouts()
                if available_layouts:
                    raise argparse.ArgumentTypeError(
                        f"Invalid layout '{layout_name}'. "
                        f"Available layouts: {', '.join(available_layouts)}"
                    )
                else:
                    raise argparse.ArgumentTypeError(
                        f"Invalid layout '{layout_name}'. No layouts available."
                    )

            # Set the validated layout name
            setattr(namespace, self.dest, layout_name)

        except argparse.ArgumentTypeError:
            # Re-raise argparse errors to let argparse handle them
            raise

        except LayoutError as e:
            logger.warning(f"Layout registry error during CLI validation: {e}")
            # Fallback to legacy validation for backward compatibility
            legacy_layouts = ["4x8", "3x4"]
            if layout_name not in legacy_layouts:
                raise argparse.ArgumentTypeError(
                    f"Invalid layout '{layout_name}'. "
                    f"Available layouts: {', '.join(legacy_layouts)} "
                    f"(using fallback validation due to registry error)"
                )
            setattr(namespace, self.dest, layout_name)

        except Exception as e:
            logger.error(f"Unexpected error during layout validation: {e}")
            # Fallback to legacy validation for robustness
            legacy_layouts = ["4x8", "3x4"]
            if layout_name not in legacy_layouts:
                raise argparse.ArgumentTypeError(
                    f"Invalid layout '{layout_name}'. "
                    f"Available layouts: {', '.join(legacy_layouts)} "
                    f"(using fallback validation due to error)"
                )
            setattr(namespace, self.dest, layout_name)


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser with comprehensive configuration options.

    Builds a comprehensive ArgumentParser with all supported command-line options
    organized into logical groups for setup, testing, display modes, logging,
    and operational modes (interactive, web, RPI).

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
  %(prog)s --interactive             # Run interactive console mode with arrow key controls
  %(prog)s --web                     # Run web server mode on localhost:8080 (explicit)
  %(prog)s --web --port 3000 --auto-open  # Run web server on port 3000 and open browser
  %(prog)s --epaper                  # Run in e-paper display mode with hardware auto-detection
  %(prog)s --rpi --web               # Run in RPI e-ink mode with web interface
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
        "--version", action="version", version=f"%(prog)s 1.0.0", help="Show version information"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging and detailed output"
    )

    # Test mode arguments
    test_group = parser.add_argument_group("test", "Test and validation mode options")

    test_group.add_argument(
        "--test-mode",
        "-t",
        action="store_true",
        help="Run comprehensive validation and testing of Calendar Bot components",
    )

    test_group.add_argument(
        "--date", type=parse_date, help="Start date for test mode (YYYY-MM-DD format)"
    )

    test_group.add_argument(
        "--end-date", type=parse_date, help="End date for test mode (YYYY-MM-DD format)"
    )

    test_group.add_argument("--no-cache", action="store_true", help="Disable cache for test mode")

    test_group.add_argument(
        "--components",
        type=parse_components,
        default=["sources", "cache", "display"],
        help="Components to test (comma-separated): sources,cache,display,validation,logging,network",
    )

    test_group.add_argument(
        "--output-format",
        choices=["console", "json", "yaml"],
        default="console",
        help="Output format for test results",
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

    # Interactive mode arguments
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive navigation mode with arrow key controls",
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
        choices=["html", "rpi", "compact"],
        default=None,
        help="Renderer type: html (web browser), rpi (Raspberry Pi e-ink), compact (compact e-ink)",
    )

    # Raspberry Pi e-ink display arguments
    rpi_group = parser.add_argument_group("rpi", "Raspberry Pi e-ink display options")

    rpi_group.add_argument(
        "--rpi",
        "--rpi-mode",
        action="store_true",
        help="Enable Raspberry Pi e-ink display configuration (480x800px optimized layout, compact renderer)",
    )

    rpi_group.add_argument(
        "--rpi-width", type=int, default=480, help="RPI display width in pixels (default: 480)"
    )

    rpi_group.add_argument(
        "--rpi-height", type=int, default=800, help="RPI display height in pixels (default: 800)"
    )

    rpi_group.add_argument(
        "--rpi-refresh-mode",
        choices=["partial", "full"],
        default="partial",
        help="E-ink refresh mode (default: partial)",
    )

    # Compact e-ink display arguments
    compact_group = parser.add_argument_group("compact", "Compact e-ink display options")

    compact_group.add_argument(
        "--compact",
        "--compact-mode",
        action="store_true",
        help="Enable compact e-ink display mode (300x400px optimized) - sets renderer to 'compact'",
    )

    compact_group.add_argument(
        "--compact-width",
        type=int,
        default=300,
        help="Compact display width in pixels (default: 300)",
    )

    compact_group.add_argument(
        "--compact-height",
        type=int,
        default=400,
        help="Compact display height in pixels (default: 400)",
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

    # Interactive mode options
    logging_group.add_argument(
        "--no-split-display", action="store_true", help="Disable split display in interactive mode"
    )

    logging_group.add_argument(
        "--log-lines", type=int, help="Number of log lines to show in interactive mode (default: 5)"
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
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def parse_components(components_str: str) -> List[str]:
    """Parse components string into a list of valid component names.

    Validates and processes a comma-separated string of component names
    for test mode component selection, ensuring all components are valid.

    Args:
        components_str (str): Comma-separated string of component names

    Returns:
        List[str]: List of valid, normalized component names

    Raises:
        argparse.ArgumentTypeError: If any component is invalid or unrecognized

    Example:
        >>> components = parse_components("sources,cache,display")
        >>> print(components)  # ['sources', 'cache', 'display']
        >>>
        >>> # Handles whitespace and case normalization
        >>> components = parse_components(" SOURCES, Cache , display ")
        >>> print(components)  # ['sources', 'cache', 'display']
        >>>
        >>> # Invalid component raises error
        >>> parse_components("invalid,sources")  # Raises ArgumentTypeError
    """
    valid_components = ["sources", "cache", "display", "validation", "logging", "network"]

    # Split by comma and clean up whitespace
    components = [comp.strip().lower() for comp in components_str.split(",")]

    # Validate components
    invalid_components = [comp for comp in components if comp not in valid_components]

    if invalid_components:
        raise argparse.ArgumentTypeError(
            f"Invalid components: {', '.join(invalid_components)}. "
            f"Valid options: {', '.join(valid_components)}"
        )

    return components


__all__ = [
    "create_parser",
    "parse_date",
    "parse_components",
    "LayoutAction",
]
