"""Tests for CLI argument parser functionality.

Tests cover argument parser creation, validation functions,
and edge cases for command-line argument processing.
"""

import argparse
from datetime import datetime

import pytest

from calendarbot.cli.parser import create_parser, parse_date


class TestCreateParser:
    """Test suite for create_parser function."""

    def test_create_parser_returns_argument_parser(self):
        """Test that create_parser returns a properly configured ArgumentParser."""
        parser = create_parser()

        assert isinstance(parser, argparse.ArgumentParser)
        assert parser.description is not None
        assert "Calendar Bot" in parser.description
        assert parser.epilog is not None

    def test_parser_has_setup_arguments(self):
        """Test that parser includes setup and configuration arguments."""
        parser = create_parser()

        # Test parsing setup arguments
        args = parser.parse_args(["--setup"])
        assert args.setup is True

        args = parser.parse_args(["--backup"])
        assert args.backup is True

        args = parser.parse_args(["--list-backups"])
        assert args.list_backups is True

        args = parser.parse_args(["--restore", "backup.yaml"])
        assert args.restore == "backup.yaml"

    def test_parser_has_verbose_argument(self):
        """Test that parser includes verbose logging argument."""
        parser = create_parser()

        args = parser.parse_args(["--verbose"])
        assert args.verbose is True

        args = parser.parse_args(["-v"])
        assert args.verbose is True

    def test_parser_interactive_mode_argument(self):
        """Test that parser includes interactive mode argument."""
        parser = create_parser()

        args = parser.parse_args(["--interactive"])
        assert args.interactive is True

        args = parser.parse_args(["-i"])
        assert args.interactive is True

    def test_parser_web_mode_arguments(self):
        """Test that parser includes web mode arguments."""
        parser = create_parser()

        args = parser.parse_args(["--web"])
        assert args.web is True

        args = parser.parse_args(["-w"])
        assert args.web is True

        args = parser.parse_args(["--port", "3000"])
        assert args.port == 3000

        args = parser.parse_args(["--host", "localhost"])
        assert args.host == "localhost"

        args = parser.parse_args(["--auto-open"])
        assert args.auto_open is True

    def test_parser_display_arguments(self):
        """Test that parser includes layout arguments."""
        parser = create_parser()

        args = parser.parse_args(["--layout", "4x8"])
        assert args.display_type == "4x8"  # --layout sets display_type

    def test_parser_rpi_arguments(self):
        """Test that parser includes Raspberry Pi arguments."""
        parser = create_parser()

        args = parser.parse_args(["--rpi"])
        assert args.rpi is True

        args = parser.parse_args(["--rpi-mode"])
        assert args.rpi is True

        args = parser.parse_args(["--rpi-width", "480"])
        assert args.rpi_width == 480

        args = parser.parse_args(["--rpi-height", "800"])
        assert args.rpi_height == 800

        args = parser.parse_args(["--rpi-refresh-mode", "full"])
        assert args.rpi_refresh_mode == "full"

    def test_parser_logging_arguments(self):
        """Test that parser includes comprehensive logging arguments."""
        parser = create_parser()

        args = parser.parse_args(["--log-level", "DEBUG"])
        assert args.log_level == "DEBUG"

        args = parser.parse_args(["--console-level", "INFO"])
        assert args.console_level == "INFO"

        args = parser.parse_args(["--file-level", "WARNING"])
        assert args.file_level == "WARNING"

        args = parser.parse_args(["--quiet"])
        assert args.quiet is True

        args = parser.parse_args(["-q"])
        assert args.quiet is True

    def test_parser_logging_file_arguments(self, tmp_path):
        """Test that parser includes file logging arguments."""
        parser = create_parser()

        log_dir = tmp_path / "logs"
        args = parser.parse_args(["--log-dir", str(log_dir)])
        assert args.log_dir == log_dir

        args = parser.parse_args(["--no-file-logging"])
        assert args.no_file_logging is True

        args = parser.parse_args(["--max-log-files", "10"])
        assert args.max_log_files == 10

    def test_parser_logging_console_arguments(self):
        """Test that parser includes console logging arguments."""
        parser = create_parser()

        args = parser.parse_args(["--no-console-logging"])
        assert args.no_console_logging is True

        args = parser.parse_args(["--no-log-colors"])
        assert args.no_log_colors is True

    def test_parser_interactive_logging_arguments(self):
        """Test that parser includes interactive mode logging arguments."""
        parser = create_parser()

        args = parser.parse_args(["--no-split-display"])
        assert args.no_split_display is True

        args = parser.parse_args(["--log-lines", "10"])
        assert args.log_lines == 10

    def test_parser_version_argument(self):
        """Test that parser includes version argument."""
        parser = create_parser()

        # Version argument should trigger SystemExit
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    def test_parser_defaults(self):
        """Test that parser has correct default values."""
        parser = create_parser()
        args = parser.parse_args([])

        # Check some key defaults
        assert args.port == 8080
        assert args.rpi_width == 480
        assert args.rpi_height == 800
        assert args.rpi_refresh_mode == "partial"

    def test_parser_invalid_choice_raises_error(self):
        """Test that parser raises error for invalid choices."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--output-format", "invalid"])

        with pytest.raises(SystemExit):
            parser.parse_args(["--log-level", "INVALID"])

        with pytest.raises(SystemExit):
            parser.parse_args(["--rpi-refresh-mode", "invalid"])

    def test_parser_complex_argument_combinations(self):
        """Test that parser handles complex argument combinations."""
        parser = create_parser()

        args = parser.parse_args(
            [
                "--web",
                "--port",
                "3000",
                "--host",
                "localhost",
                "--verbose",
                "--log-level",
                "DEBUG",
                "--rpi",
                "--rpi-width",
                "480",
                "--auto-open",
            ]
        )

        assert args.web is True
        assert args.port == 3000
        assert args.host == "localhost"
        assert args.verbose is True
        assert args.log_level == "DEBUG"
        assert args.rpi is True
        assert args.rpi_width == 480
        assert args.auto_open is True


class TestParseDateFunction:
    """Test suite for parse_date function."""

    def test_parse_date_valid_format(self):
        """Test that parse_date correctly parses valid date strings."""
        result = parse_date("2024-01-15")

        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_parse_date_edge_cases(self):
        """Test parse_date with edge case dates."""
        # Leap year
        result = parse_date("2024-02-29")
        assert result.year == 2024
        assert result.month == 2
        assert result.day == 29

        # New Year's Day
        result = parse_date("2024-01-01")
        assert result.month == 1
        assert result.day == 1

        # New Year's Eve
        result = parse_date("2024-12-31")
        assert result.month == 12
        assert result.day == 31

    def test_parse_date_invalid_format_raises_error(self):
        """Test that parse_date raises ArgumentTypeError for invalid formats."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_date("15-01-2024")

        assert "Invalid date format" in str(exc_info.value)
        assert "15-01-2024" in str(exc_info.value)
        assert "YYYY-MM-DD" in str(exc_info.value)

    @pytest.mark.parametrize(
        "invalid_date",
        [
            "2024/01/15",  # Wrong separators
            "01-15-2024",  # Wrong order
            "24-01-15",  # Two-digit year
            "2024-13-01",  # Invalid month
            "2024-02-30",  # Invalid day for February
            "2024-04-31",  # Invalid day for April
            "invalid",  # Non-date string
            "2024-01",  # Missing day
            "2024",  # Missing month and day
            "",  # Empty string
        ],
    )
    def test_parse_date_various_invalid_formats(self, invalid_date):
        """Test parse_date with various invalid date formats."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_date(invalid_date)

    @pytest.mark.parametrize(
        ("flexible_date", "expected"),
        [
            ("2024-1-15", datetime(2024, 1, 15)),  # Single digit month works
            ("2024-01-1", datetime(2024, 1, 1)),  # Single digit day works
        ],
    )
    def test_parse_date_flexible_formats(self, flexible_date, expected):
        """Test that parse_date accepts flexible single-digit formats."""
        result = parse_date(flexible_date)
        assert result == expected


class TestParserIntegration:
    """Integration tests for parser functionality."""

    def test_parser_integration_web_mode_with_logging(self):
        """Test integration of web mode with logging configuration."""
        parser = create_parser()

        args = parser.parse_args(
            [
                "--web",
                "--port",
                "3000",
                "--host",
                "localhost",
                "--log-level",
                "DEBUG",
                "--no-file-logging",
                "--auto-open",
            ]
        )

        assert args.web is True
        assert args.port == 3000
        assert args.host == "localhost"
        assert args.log_level == "DEBUG"
        assert args.no_file_logging is True
        assert args.auto_open is True

    def test_parser_integration_rpi_mode_complete(self):
        """Test integration of RPI mode with all related arguments."""
        parser = create_parser()

        args = parser.parse_args(
            [
                "--rpi",
                "--rpi-width",
                "600",
                "--rpi-height",
                "900",
                "--rpi-refresh-mode",
                "full",
                "--web",
                "--quiet",
            ]
        )

        assert args.rpi is True
        assert args.rpi_width == 600
        assert args.rpi_height == 900
        assert args.rpi_refresh_mode == "full"
        assert args.web is True
        assert args.quiet is True

    def test_parser_help_message_generation(self):
        """Test that parser can generate help messages without errors."""
        parser = create_parser()

        # This should not raise an exception
        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])
