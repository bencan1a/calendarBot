"""Tests for CLI argument parser functionality.

Tests cover argument parser creation, validation functions,
and edge cases for command-line argument processing.
"""

import argparse
from datetime import datetime
from pathlib import Path

import pytest

from calendarbot.cli.parser import create_parser, parse_components, parse_date


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

    def test_parser_has_test_mode_arguments(self):
        """Test that parser includes test mode arguments."""
        parser = create_parser()

        args = parser.parse_args(["--test-mode"])
        assert args.test_mode is True

        args = parser.parse_args(["-t"])
        assert args.test_mode is True

        args = parser.parse_args(["--no-cache"])
        assert args.no_cache is True

    def test_parser_date_arguments(self):
        """Test that parser handles date arguments correctly."""
        parser = create_parser()

        args = parser.parse_args(["--date", "2024-01-15"])
        assert isinstance(args.date, datetime)
        assert args.date.year == 2024
        assert args.date.month == 1
        assert args.date.day == 15

        args = parser.parse_args(["--end-date", "2024-12-31"])
        assert isinstance(args.end_date, datetime)

    def test_parser_components_argument(self):
        """Test that parser handles components argument correctly."""
        parser = create_parser()

        args = parser.parse_args(["--components", "sources,cache"])
        assert args.components == ["sources", "cache"]

        # Test default components
        args = parser.parse_args([])
        assert args.components == ["sources", "cache", "display"]

    def test_parser_output_format_argument(self):
        """Test that parser handles output format choices."""
        parser = create_parser()

        args = parser.parse_args(["--output-format", "json"])
        assert args.output_format == "json"

        args = parser.parse_args(["--output-format", "yaml"])
        assert args.output_format == "yaml"

        # Test default
        args = parser.parse_args([])
        assert args.output_format == "console"

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

    def test_parser_compact_arguments(self):
        """Test that parser includes compact display arguments."""
        parser = create_parser()

        args = parser.parse_args(["--compact"])
        assert args.compact is True

        args = parser.parse_args(["--compact-mode"])
        assert args.compact is True

        args = parser.parse_args(["--compact-width", "300"])
        assert args.compact_width == 300

        args = parser.parse_args(["--compact-height", "400"])
        assert args.compact_height == 400

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

    def test_parser_logging_file_arguments(self):
        """Test that parser includes file logging arguments."""
        parser = create_parser()

        args = parser.parse_args(["--log-dir", "/tmp/logs"])
        assert args.log_dir == Path("/tmp/logs")

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
        assert args.compact_width == 300
        assert args.compact_height == 400
        assert args.output_format == "console"
        assert args.components == ["sources", "cache", "display"]

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
                "--components",
                "sources,cache,display",
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
        assert args.components == ["sources", "cache", "display"]
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


class TestParseComponentsFunction:
    """Test suite for parse_components function."""

    def test_parse_components_valid_input(self):
        """Test that parse_components correctly parses valid component strings."""
        result = parse_components("sources,cache,display")
        assert result == ["sources", "cache", "display"]

    def test_parse_components_handles_whitespace(self):
        """Test that parse_components handles whitespace correctly."""
        result = parse_components(" sources , cache , display ")
        assert result == ["sources", "cache", "display"]

        result = parse_components("sources,  cache,   display")
        assert result == ["sources", "cache", "display"]

    def test_parse_components_handles_case_normalization(self):
        """Test that parse_components normalizes case correctly."""
        result = parse_components("SOURCES,Cache,DISPLAY")
        assert result == ["sources", "cache", "display"]

        result = parse_components("Sources,CACHE,Display")
        assert result == ["sources", "cache", "display"]

    def test_parse_components_all_valid_components(self):
        """Test parse_components with all valid component names."""
        all_components = "sources,cache,display,validation,logging,network"
        result = parse_components(all_components)

        expected = ["sources", "cache", "display", "validation", "logging", "network"]
        assert result == expected

    def test_parse_components_single_component(self):
        """Test parse_components with a single component."""
        result = parse_components("sources")
        assert result == ["sources"]

        result = parse_components("  CACHE  ")
        assert result == ["cache"]

    def test_parse_components_empty_string_raises_error(self):
        """Test parse_components with empty string raises error."""
        # Empty string produces [''] after split, which is invalid
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_components("")

        assert "Invalid components:" in str(exc_info.value)

        # Whitespace-only strings also produce invalid results
        with pytest.raises(argparse.ArgumentTypeError):
            parse_components("   ")

    def test_parse_components_invalid_component_raises_error(self):
        """Test that parse_components raises error for invalid components."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_components("invalid,sources")

        assert "Invalid components: invalid" in str(exc_info.value)
        assert "Valid options:" in str(exc_info.value)

    def test_parse_components_multiple_invalid_components(self):
        """Test parse_components with multiple invalid components."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_components("invalid1,sources,invalid2,cache")

        error_msg = str(exc_info.value)
        assert "Invalid components:" in error_msg
        assert "invalid1" in error_msg
        assert "invalid2" in error_msg

    @pytest.mark.parametrize(
        ("component_string", "expected"),
        [
            ("sources", ["sources"]),
            ("sources,cache", ["sources", "cache"]),
            ("validation,logging,network", ["validation", "logging", "network"]),
            ("SOURCES,cache,DISPLAY", ["sources", "cache", "display"]),
            (" sources , cache ", ["sources", "cache"]),
        ],
    )
    def test_parse_components_parametrized_valid_inputs(self, component_string, expected):
        """Test parse_components with various valid input combinations."""
        result = parse_components(component_string)
        assert result == expected

    def test_parse_components_duplicate_components(self):
        """Test parse_components with duplicate component names."""
        result = parse_components("sources,cache,sources,display")
        # Should preserve duplicates as returned by split logic
        assert result == ["sources", "cache", "sources", "display"]

    def test_parse_components_partial_invalid_mixed_with_valid(self):
        """Test parse_components error message contains only invalid components."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_components("sources,invalid,cache,another_invalid")

        error_msg = str(exc_info.value)
        assert "invalid, another_invalid" in error_msg
        # Valid components should not be in error message
        assert "sources" not in error_msg.split("Valid options:")[0]
        assert "cache" not in error_msg.split("Valid options:")[0]


class TestParserIntegration:
    """Integration tests for parser functionality."""

    def test_parser_integration_test_mode_with_components(self):
        """Test integration of test mode with components parsing."""
        parser = create_parser()

        args = parser.parse_args(
            [
                "--test-mode",
                "--components",
                "sources,validation",
                "--date",
                "2024-01-15",
                "--output-format",
                "json",
            ]
        )

        assert args.test_mode is True
        assert args.components == ["sources", "validation"]
        assert args.date.year == 2024
        assert args.output_format == "json"

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
