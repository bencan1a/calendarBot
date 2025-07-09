"""Command-line argument parsing for Calendar Bot.

This module handles all command-line argument parsing functionality,
including setup of argument groups, validation, and parsing logic.
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser.

    Returns:
        Configured ArgumentParser instance
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
        "--test-mode", "-t", action="store_true", help="Run Calendar Bot in test/validation mode"
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

    # Raspberry Pi e-ink display arguments
    rpi_group = parser.add_argument_group("rpi", "Raspberry Pi e-ink display options")

    rpi_group.add_argument(
        "--rpi",
        "--rpi-mode",
        action="store_true",
        help="Enable Raspberry Pi e-ink display mode (800x480px optimized)",
    )

    rpi_group.add_argument(
        "--rpi-width", type=int, default=800, help="RPI display width in pixels (default: 800)"
    )

    rpi_group.add_argument(
        "--rpi-height", type=int, default=480, help="RPI display height in pixels (default: 480)"
    )

    rpi_group.add_argument(
        "--rpi-refresh-mode",
        choices=["partial", "full"],
        default="partial",
        help="E-ink refresh mode (default: partial)",
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
    """Parse date string in YYYY-MM-DD format.

    Args:
        date_str: Date string to parse

    Returns:
        Parsed datetime object

    Raises:
        argparse.ArgumentTypeError: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def parse_components(components_str: str) -> List[str]:
    """Parse components string into a list of valid component names.

    Args:
        components_str: Comma-separated string of component names

    Returns:
        List of valid component names

    Raises:
        argparse.ArgumentTypeError: If any component is invalid
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
]
