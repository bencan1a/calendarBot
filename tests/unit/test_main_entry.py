"""Unit tests for calendarbot/__main__.py entry point and CLI functionality."""

import argparse
import asyncio
import sys
import tempfile
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
import pytest_asyncio


class TestConfigurationChecking:
    """Test suite for configuration detection functionality."""

    def test_check_configuration_project_config_exists(self):
        """Test configuration check when project config file exists."""
        from calendarbot.__main__ import check_configuration

        with patch("calendarbot.__main__.Path") as mock_path:
            # Mock project config exists
            mock_project_config = MagicMock()
            mock_project_config.exists.return_value = True
            mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value = (
                mock_project_config
            )

            is_configured, config_path = check_configuration()

            assert is_configured is True
            assert config_path == mock_project_config

    def test_check_configuration_user_config_exists(self):
        """Test configuration check when user config file exists."""
        from calendarbot.__main__ import check_configuration

        with patch("calendarbot.__main__.Path") as mock_path:
            # Mock project config doesn't exist but user config does
            mock_project_config = MagicMock()
            mock_project_config.exists.return_value = False

            mock_user_config = MagicMock()
            mock_user_config.exists.return_value = True

            # Setup path chain
            mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value = (
                mock_project_config
            )
            mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = (
                mock_user_config
            )

            is_configured, config_path = check_configuration()

            assert is_configured is True
            assert config_path == mock_user_config

    def test_check_configuration_environment_variables(self):
        """Test configuration check using environment variables."""
        from calendarbot.__main__ import check_configuration

        with patch("calendarbot.__main__.Path") as mock_path, patch(
            "config.settings.CalendarBotSettings"
        ) as mock_settings_class:

            # Mock both config files don't exist
            mock_project_config = MagicMock()
            mock_project_config.exists.return_value = False
            mock_user_config = MagicMock()
            mock_user_config.exists.return_value = False

            mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value = (
                mock_project_config
            )
            mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = (
                mock_user_config
            )

            # Mock settings with ICS URL configured
            mock_settings = MagicMock()
            mock_settings.ics_url = "http://example.com/calendar.ics"
            mock_settings_class.return_value = mock_settings

            is_configured, config_path = check_configuration()

            assert is_configured is True
            assert config_path is None

    def test_check_configuration_not_configured(self):
        """Test configuration check when not configured."""
        from calendarbot.__main__ import check_configuration

        with patch("calendarbot.__main__.Path") as mock_path, patch(
            "config.settings.CalendarBotSettings"
        ) as mock_settings_class:

            # Mock no config files exist
            mock_project_config = MagicMock()
            mock_project_config.exists.return_value = False
            mock_user_config = MagicMock()
            mock_user_config.exists.return_value = False

            mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value = (
                mock_project_config
            )
            mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = (
                mock_user_config
            )

            # Mock settings without ICS URL
            mock_settings = MagicMock()
            mock_settings.ics_url = None
            mock_settings_class.return_value = mock_settings

            is_configured, config_path = check_configuration()

            assert is_configured is False
            assert config_path is None

    def test_check_configuration_import_exception(self):
        """Test configuration check when import fails."""
        from calendarbot.__main__ import check_configuration

        with patch("calendarbot.__main__.Path") as mock_path:
            # Mock config files don't exist
            mock_project_config = MagicMock()
            mock_project_config.exists.return_value = False
            mock_user_config = MagicMock()
            mock_user_config.exists.return_value = False

            mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value = (
                mock_project_config
            )
            mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = (
                mock_user_config
            )

            # Mock import error for settings
            with patch(
                "config.settings.CalendarBotSettings", side_effect=ImportError("Settings not found")
            ):
                is_configured, config_path = check_configuration()

                assert is_configured is False
                assert config_path is None

    def test_check_configuration_general_exception(self):
        """Test configuration check with general exception."""
        from calendarbot.__main__ import check_configuration

        with patch("calendarbot.__main__.Path", side_effect=Exception("Unexpected error")):
            is_configured, config_path = check_configuration()

            assert is_configured is False
            assert config_path is None


class TestSetupGuidance:
    """Test suite for setup guidance display."""

    def test_show_setup_guidance_output(self):
        """Test that setup guidance displays expected content."""
        from calendarbot.__main__ import show_setup_guidance

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            show_setup_guidance()
            output = mock_stdout.getvalue()

            # Check for key elements in output
            assert "Welcome to Calendar Bot!" in output
            assert "Quick Setup Options:" in output
            assert "calendarbot --setup" in output
            assert "Interactive Wizard Features:" in output
            assert "Documentation:" in output
            assert "Required Configuration:" in output


class TestSetupWizard:
    """Test suite for setup wizard functionality."""

    def test_run_setup_wizard_full_wizard_success(self):
        """Test setup wizard with full wizard option and success."""
        from calendarbot.__main__ import run_setup_wizard

        with patch("builtins.input", return_value="1"), patch(
            "calendarbot.setup_wizard.run_setup_wizard", return_value=True
        ) as mock_async_wizard, patch("asyncio.run") as mock_asyncio_run:

            mock_asyncio_run.return_value = True

            result = run_setup_wizard()

            assert result == 0

    def test_run_setup_wizard_quick_setup_success(self):
        """Test setup wizard with quick setup option and success."""
        from calendarbot.__main__ import run_setup_wizard

        with patch("builtins.input", return_value="2"), patch(
            "calendarbot.setup_wizard.run_simple_wizard", return_value=True
        ) as mock_simple_wizard:

            result = run_setup_wizard()

            assert result == 0
            mock_simple_wizard.assert_called_once()

    def test_run_setup_wizard_quick_setup_failure(self):
        """Test setup wizard with quick setup option and failure."""
        from calendarbot.__main__ import run_setup_wizard

        with patch("builtins.input", return_value="2"), patch(
            "calendarbot.setup_wizard.run_simple_wizard", return_value=False
        ):

            result = run_setup_wizard()

            assert result == 1

    def test_run_setup_wizard_full_wizard_failure(self):
        """Test setup wizard with full wizard option and failure."""
        from calendarbot.__main__ import run_setup_wizard

        with patch("builtins.input", return_value="1"), patch("asyncio.run", return_value=False):

            result = run_setup_wizard()

            assert result == 1

    def test_run_setup_wizard_keyboard_interrupt(self):
        """Test setup wizard with keyboard interrupt."""
        from calendarbot.__main__ import run_setup_wizard

        with patch("builtins.input", side_effect=KeyboardInterrupt()):
            result = run_setup_wizard()

            assert result == 1

    def test_run_setup_wizard_exception(self):
        """Test setup wizard with general exception."""
        from calendarbot.__main__ import run_setup_wizard

        with patch("builtins.input", side_effect=Exception("Setup error")):
            result = run_setup_wizard()

            assert result == 1

    def test_run_setup_wizard_import_error(self):
        """Test setup wizard with import error."""
        from calendarbot.__main__ import run_setup_wizard

        with patch("builtins.input", return_value="1"), patch(
            "calendarbot.setup_wizard.run_setup_wizard", side_effect=ImportError("Module not found")
        ):
            result = run_setup_wizard()

            assert result == 1


class TestDateParsing:
    """Test suite for date parsing functionality."""

    def test_parse_date_valid_format(self):
        """Test parsing valid date format."""
        from calendarbot.__main__ import parse_date

        result = parse_date("2024-01-15")
        expected = datetime(2024, 1, 15)

        assert result == expected

    def test_parse_date_invalid_format(self):
        """Test parsing invalid date format."""
        from calendarbot.__main__ import parse_date

        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_date("invalid-date")

        assert "Invalid date format" in str(exc_info.value)

    def test_parse_date_wrong_separator(self):
        """Test parsing date with wrong separator."""
        from calendarbot.__main__ import parse_date

        with pytest.raises(argparse.ArgumentTypeError):
            parse_date("2024/01/15")

    def test_parse_date_missing_components(self):
        """Test parsing date with missing components."""
        from calendarbot.__main__ import parse_date

        with pytest.raises(argparse.ArgumentTypeError):
            parse_date("2024-01")


class TestComponentsParsing:
    """Test suite for components parsing functionality."""

    def test_parse_components_valid_single(self):
        """Test parsing single valid component."""
        from calendarbot.__main__ import parse_components

        result = parse_components("sources")

        assert result == ["sources"]

    def test_parse_components_valid_multiple(self):
        """Test parsing multiple valid components."""
        from calendarbot.__main__ import parse_components

        result = parse_components("sources,cache,display")

        assert result == ["sources", "cache", "display"]

    def test_parse_components_with_spaces(self):
        """Test parsing components with spaces."""
        from calendarbot.__main__ import parse_components

        result = parse_components("sources, cache , display")

        assert result == ["sources", "cache", "display"]

    def test_parse_components_case_insensitive(self):
        """Test parsing components with mixed case."""
        from calendarbot.__main__ import parse_components

        result = parse_components("SOURCES,Cache,DISPLAY")

        assert result == ["sources", "cache", "display"]

    def test_parse_components_invalid_component(self):
        """Test parsing with invalid component."""
        from calendarbot.__main__ import parse_components

        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_components("sources,invalid,cache")

        assert "Invalid components: invalid" in str(exc_info.value)

    def test_parse_components_multiple_invalid(self):
        """Test parsing with multiple invalid components."""
        from calendarbot.__main__ import parse_components

        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_components("sources,invalid1,invalid2,cache")

        error_msg = str(exc_info.value)
        assert "Invalid components:" in error_msg
        assert "invalid1" in error_msg
        assert "invalid2" in error_msg


class TestRPIOverrides:
    """Test suite for RPI-specific overrides functionality."""

    def test_apply_rpi_overrides_enabled(self):
        """Test applying RPI overrides when enabled."""
        from calendarbot.__main__ import apply_rpi_overrides

        # Create mock settings
        mock_settings = MagicMock()
        mock_settings.rpi_auto_theme = True
        mock_settings.web_theme = "standard"

        # Create mock args with RPI enabled
        mock_args = MagicMock()
        mock_args.rpi = True
        mock_args.rpi_width = 800
        mock_args.rpi_height = 480
        mock_args.rpi_refresh_mode = "partial"

        with patch("logging.getLogger") as mock_logger:
            result = apply_rpi_overrides(mock_settings, mock_args)

        assert result.rpi_enabled is True
        assert result.display_type == "rpi"
        assert result.rpi_display_width == 800
        assert result.rpi_display_height == 480
        assert result.rpi_refresh_mode == "partial"
        assert result.web_theme == "eink-rpi"

    def test_apply_rpi_overrides_disabled(self):
        """Test applying RPI overrides when disabled."""
        from calendarbot.__main__ import apply_rpi_overrides

        mock_settings = MagicMock()
        mock_settings.rpi_auto_theme = True
        mock_settings.web_theme = "standard"

        mock_args = MagicMock()
        mock_args.rpi = False

        with patch("logging.getLogger"):
            result = apply_rpi_overrides(mock_settings, mock_args)

        # Settings should be unchanged when RPI not enabled
        assert result == mock_settings

    def test_apply_rpi_overrides_auto_theme_disabled(self):
        """Test applying RPI overrides with auto theme disabled."""
        from calendarbot.__main__ import apply_rpi_overrides

        mock_settings = MagicMock()
        mock_settings.rpi_auto_theme = False
        mock_settings.web_theme = "custom"

        mock_args = MagicMock()
        mock_args.rpi = True

        with patch("logging.getLogger"):
            result = apply_rpi_overrides(mock_settings, mock_args)

        assert result.rpi_enabled is True
        assert result.display_type == "rpi"
        # Theme should remain unchanged when auto theme is disabled
        assert result.web_theme == "custom"

    def test_apply_rpi_overrides_no_rpi_attribute(self):
        """Test applying RPI overrides when args has no rpi attribute."""
        from calendarbot.__main__ import apply_rpi_overrides

        mock_settings = MagicMock()
        mock_args = MagicMock(spec=[])  # No rpi attribute

        with patch("logging.getLogger"):
            result = apply_rpi_overrides(mock_settings, mock_args)

        assert result == mock_settings


class TestArgumentParser:
    """Test suite for command line argument parser."""

    def test_create_parser_basic(self):
        """Test creating basic argument parser."""
        from calendarbot.__main__ import create_parser

        parser = create_parser()

        assert isinstance(parser, argparse.ArgumentParser)
        assert "Calendar Bot" in parser.description

    def test_create_parser_setup_argument(self):
        """Test parser includes setup argument."""
        from calendarbot.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args(["--setup"])

        assert args.setup is True

    def test_create_parser_version_argument(self):
        """Test parser includes version argument."""
        from calendarbot.__main__ import create_parser

        parser = create_parser()

        # Version should exit, so we catch SystemExit
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    def test_create_parser_test_mode_arguments(self):
        """Test parser includes test mode arguments."""
        from calendarbot.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args(
            [
                "--test-mode",
                "--date",
                "2024-01-15",
                "--end-date",
                "2024-01-20",
                "--verbose",
                "--no-cache",
                "--components",
                "sources,cache",
                "--output-format",
                "json",
            ]
        )

        assert args.test_mode is True
        assert args.date.year == 2024
        assert args.date.month == 1
        assert args.date.day == 15
        assert args.end_date.year == 2024
        assert args.verbose is True
        assert args.no_cache is True
        assert args.components == ["sources", "cache"]
        assert args.output_format == "json"

    def test_create_parser_web_mode_arguments(self):
        """Test parser includes web mode arguments."""
        from calendarbot.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args(["--web", "--port", "9000", "--host", "0.0.0.0", "--auto-open"])

        assert args.web is True
        assert args.port == 9000
        assert args.host == "0.0.0.0"
        assert args.auto_open is True

    def test_create_parser_rpi_arguments(self):
        """Test parser includes RPI arguments."""
        from calendarbot.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["--rpi", "--rpi-width", "800", "--rpi-height", "480", "--rpi-refresh-mode", "full"]
        )

        assert args.rpi is True
        assert args.rpi_width == 800
        assert args.rpi_height == 480
        assert args.rpi_refresh_mode == "full"

    def test_create_parser_logging_arguments(self):
        """Test parser includes logging arguments."""
        from calendarbot.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args(
            [
                "--log-level",
                "DEBUG",
                "--console-level",
                "INFO",
                "--file-level",
                "WARNING",
                "--quiet",
                "--log-dir",
                "/tmp/logs",
                "--no-file-logging",
                "--max-log-files",
                "10",
                "--no-console-logging",
                "--no-log-colors",
                "--no-split-display",
                "--log-lines",
                "15",
            ]
        )

        assert args.log_level == "DEBUG"
        assert args.console_level == "INFO"
        assert args.file_level == "WARNING"
        assert args.quiet is True
        assert str(args.log_dir) == "/tmp/logs"
        assert args.no_file_logging is True
        assert args.max_log_files == 10
        assert args.no_console_logging is True
        assert args.no_log_colors is True
        assert args.no_split_display is True
        assert args.log_lines == 15

    def test_create_parser_default_values(self):
        """Test parser default values."""
        from calendarbot.__main__ import create_parser

        parser = create_parser()
        args = parser.parse_args([])

        assert args.setup is False
        assert args.test_mode is False
        assert args.interactive is False
        assert args.web is False
        assert args.port == 8080
        assert args.host is None
        assert args.auto_open is False
        assert args.rpi is False
        assert args.verbose is False
        assert args.no_cache is False
        assert args.components == ["sources", "cache", "display"]
        assert args.output_format == "console"


class TestTestMode:
    """Test suite for test mode functionality."""

    @pytest.mark.asyncio
    async def test_run_test_mode_success(self):
        """Test successful test mode execution."""
        from calendarbot.__main__ import run_test_mode

        mock_args = MagicMock()
        mock_args.date = datetime(2024, 1, 15)
        mock_args.end_date = datetime(2024, 1, 20)
        mock_args.components = ["sources", "cache"]
        mock_args.no_cache = False
        mock_args.output_format = "console"
        mock_args.verbose = True

        with patch(
            "calendarbot.utils.logging.apply_command_line_overrides"
        ) as mock_overrides, patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ) as mock_logging, patch(
            "calendarbot.validation.ValidationRunner"
        ) as mock_runner_class, patch(
            "config.settings.settings"
        ) as mock_settings, patch(
            "calendarbot.__main__.apply_rpi_overrides"
        ) as mock_rpi:

            mock_overrides.return_value = mock_settings
            mock_rpi.return_value = mock_settings
            mock_logger = MagicMock()
            mock_logging.return_value = mock_logger

            mock_runner = AsyncMock()
            mock_results = MagicMock()
            mock_results.has_failures.return_value = False
            mock_results.has_warnings.return_value = False
            mock_runner.run_validation.return_value = mock_results
            mock_runner.print_results = MagicMock()
            mock_runner_class.return_value = mock_runner

            result = await run_test_mode(mock_args)

            assert result == 0
            mock_runner.run_validation.assert_called_once()
            mock_runner.print_results.assert_called_once_with(verbose=True)

    @pytest.mark.asyncio
    async def test_run_test_mode_with_failures(self):
        """Test test mode with validation failures."""
        from calendarbot.__main__ import run_test_mode

        mock_args = MagicMock()
        mock_args.date = datetime(2024, 1, 15)
        mock_args.end_date = None
        mock_args.components = ["sources"]
        mock_args.no_cache = True
        mock_args.output_format = "json"
        mock_args.verbose = False

        with patch("calendarbot.utils.logging.apply_command_line_overrides"), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch("calendarbot.validation.ValidationRunner") as mock_runner_class, patch(
            "config.settings.settings"
        ), patch(
            "calendarbot.__main__.apply_rpi_overrides"
        ):

            mock_runner = AsyncMock()
            mock_results = MagicMock()
            mock_results.has_failures.return_value = True
            mock_runner.run_validation.return_value = mock_results
            mock_runner_class.return_value = mock_runner

            result = await run_test_mode(mock_args)

            assert result == 1

    @pytest.mark.asyncio
    async def test_run_test_mode_with_warnings_only(self):
        """Test test mode with warnings but no failures."""
        from calendarbot.__main__ import run_test_mode

        mock_args = MagicMock()

        with patch("calendarbot.utils.logging.apply_command_line_overrides"), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch("calendarbot.validation.ValidationRunner") as mock_runner_class, patch(
            "config.settings.settings"
        ), patch(
            "calendarbot.__main__.apply_rpi_overrides"
        ):

            mock_runner = AsyncMock()
            mock_results = MagicMock()
            mock_results.has_failures.return_value = False
            mock_results.has_warnings.return_value = True
            mock_runner.run_validation.return_value = mock_results
            mock_runner_class.return_value = mock_runner

            result = await run_test_mode(mock_args)

            assert result == 0  # Warnings don't cause failure

    @pytest.mark.asyncio
    async def test_run_test_mode_keyboard_interrupt(self):
        """Test test mode with keyboard interrupt."""
        from calendarbot.__main__ import run_test_mode

        mock_args = MagicMock()

        with patch("calendarbot.validation.ValidationRunner", side_effect=KeyboardInterrupt()):
            result = await run_test_mode(mock_args)

            assert result == 1

    @pytest.mark.asyncio
    async def test_run_test_mode_exception(self):
        """Test test mode with general exception."""
        from calendarbot.__main__ import run_test_mode

        mock_args = MagicMock()

        with patch("calendarbot.validation.ValidationRunner", side_effect=Exception("Test error")):
            result = await run_test_mode(mock_args)

            assert result == 1


class TestInteractiveMode:
    """Test suite for interactive mode functionality."""

    @pytest.mark.asyncio
    async def test_run_interactive_mode_success(self):
        """Test successful interactive mode execution."""
        from calendarbot.__main__ import run_interactive_mode

        mock_args = MagicMock()

        with patch("calendarbot.main.CalendarBot") as mock_bot_class, patch(
            "calendarbot.ui.InteractiveController"
        ) as mock_controller_class, patch(
            "calendarbot.utils.logging.apply_command_line_overrides"
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "config.settings.settings"
        ), patch(
            "calendarbot.__main__.apply_rpi_overrides"
        ):

            mock_bot = AsyncMock()
            mock_bot.initialize.return_value = True
            mock_bot.cleanup = AsyncMock()
            mock_bot_class.return_value = mock_bot

            mock_controller = AsyncMock()
            mock_controller.start.side_effect = KeyboardInterrupt()  # Simulate user exit
            mock_controller_class.return_value = mock_controller

            result = await run_interactive_mode(mock_args)

            assert result == 0  # KeyboardInterrupt should be handled gracefully
            mock_bot.initialize.assert_called_once()
            mock_controller.start.assert_called_once()
            mock_bot.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_interactive_mode_initialization_failure(self):
        """Test interactive mode with initialization failure."""
        from calendarbot.__main__ import run_interactive_mode

        mock_args = MagicMock()

        with patch("calendarbot.main.CalendarBot") as mock_bot_class, patch(
            "calendarbot.utils.logging.apply_command_line_overrides"
        ), patch("calendarbot.utils.logging.setup_enhanced_logging"), patch(
            "config.settings.settings"
        ), patch(
            "calendarbot.__main__.apply_rpi_overrides"
        ):

            mock_bot = AsyncMock()
            mock_bot.initialize.return_value = False
            mock_bot_class.return_value = mock_bot

            result = await run_interactive_mode(mock_args)

            assert result == 1

    @pytest.mark.asyncio
    async def test_run_interactive_mode_keyboard_interrupt(self):
        """Test interactive mode with keyboard interrupt."""
        from calendarbot.__main__ import run_interactive_mode

        mock_args = MagicMock()

        with patch("calendarbot.main.CalendarBot", side_effect=KeyboardInterrupt()):
            result = await run_interactive_mode(mock_args)

            assert result == 0  # Keyboard interrupt is handled gracefully

    @pytest.mark.asyncio
    async def test_run_interactive_mode_exception(self):
        """Test interactive mode with general exception."""
        from calendarbot.__main__ import run_interactive_mode

        mock_args = MagicMock()

        with patch("calendarbot.main.CalendarBot", side_effect=Exception("Interactive error")):
            result = await run_interactive_mode(mock_args)

            assert result == 1


class TestWebMode:
    """Test suite for web mode functionality."""

    @pytest.mark.asyncio
    async def test_run_web_mode_success(self):
        """Test successful web mode execution."""
        from calendarbot.__main__ import run_web_mode

        mock_args = MagicMock()
        mock_args.host = "127.0.0.1"
        mock_args.port = 8080
        mock_args.auto_open = False
        mock_args.rpi = False

        with patch("signal.signal"), patch("calendarbot.main.CalendarBot") as mock_bot_class, patch(
            "calendarbot.web.server.WebServer"
        ) as mock_server_class, patch(
            "calendarbot.web.navigation.WebNavigationHandler"
        ) as mock_nav_class, patch(
            "calendarbot.utils.logging.apply_command_line_overrides"
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "calendarbot.utils.network.validate_host_binding"
        ) as mock_validate, patch(
            "config.settings.settings"
        ), patch(
            "calendarbot.__main__.apply_rpi_overrides"
        ), patch(
            "asyncio.create_task"
        ) as mock_create_task, patch(
            "asyncio.sleep"
        ) as mock_sleep:

            mock_bot = AsyncMock()
            mock_bot.initialize.return_value = True
            mock_bot.cleanup = AsyncMock()
            mock_bot_class.return_value = mock_bot

            mock_server = MagicMock()
            mock_server.start = MagicMock()
            mock_server.stop = MagicMock()
            mock_server_class.return_value = mock_server

            mock_nav_class.return_value = MagicMock()
            mock_validate.return_value = "127.0.0.1"

            mock_task = AsyncMock()
            mock_task.cancel = MagicMock()
            mock_create_task.return_value = mock_task

            # Simulate KeyboardInterrupt to trigger shutdown
            mock_sleep.side_effect = KeyboardInterrupt()

            result = await run_web_mode(mock_args)
            assert result == 0  # KeyboardInterrupt handled gracefully

    @pytest.mark.asyncio
    async def test_run_web_mode_with_auto_open(self):
        """Test web mode with auto-open browser."""
        from calendarbot.__main__ import run_web_mode

        mock_args = MagicMock()
        mock_args.host = "localhost"
        mock_args.port = 3000
        mock_args.auto_open = True
        mock_args.rpi = False

        with patch("signal.signal"), patch("webbrowser.open") as mock_browser, patch(
            "calendarbot.main.CalendarBot"
        ) as mock_bot_class, patch("calendarbot.web.server.WebServer"), patch(
            "calendarbot.web.navigation.WebNavigationHandler"
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides"
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "calendarbot.utils.network.validate_host_binding", return_value="localhost"
        ), patch(
            "config.settings.settings"
        ), patch(
            "calendarbot.__main__.apply_rpi_overrides"
        ), patch(
            "asyncio.create_task"
        ), patch(
            "asyncio.sleep", side_effect=KeyboardInterrupt()
        ):

            mock_bot = AsyncMock()
            mock_bot.initialize.return_value = True
            mock_bot.cleanup = AsyncMock()
            mock_bot_class.return_value = mock_bot

            result = await run_web_mode(mock_args)
            assert result == 0  # KeyboardInterrupt handled gracefully
            mock_browser.assert_called_once_with("http://localhost:3000")

    @pytest.mark.asyncio
    async def test_run_web_mode_auto_detect_host(self):
        """Test web mode with auto-detected host."""
        from calendarbot.__main__ import run_web_mode

        mock_args = MagicMock()
        mock_args.host = None  # Auto-detect
        mock_args.port = 8080
        mock_args.auto_open = False
        mock_args.rpi = False

        with patch("signal.signal"), patch("calendarbot.main.CalendarBot") as mock_bot_class, patch(
            "calendarbot.web.server.WebServer"
        ), patch("calendarbot.web.navigation.WebNavigationHandler"), patch(
            "calendarbot.utils.logging.apply_command_line_overrides"
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "calendarbot.utils.network.get_local_network_interface", return_value="192.168.1.100"
        ), patch(
            "config.settings.settings"
        ), patch(
            "calendarbot.__main__.apply_rpi_overrides"
        ), patch(
            "asyncio.create_task"
        ), patch(
            "asyncio.sleep", side_effect=Exception("Shutdown")
        ):

            mock_bot = AsyncMock()
            mock_bot.initialize.return_value = True
            mock_bot_class.return_value = mock_bot

            with pytest.raises(Exception):
                await run_web_mode(mock_args)

    @pytest.mark.asyncio
    async def test_run_web_mode_initialization_failure(self):
        """Test web mode with bot initialization failure."""
        from calendarbot.__main__ import run_web_mode

        mock_args = MagicMock()
        mock_args.rpi = False

        with patch("signal.signal"), patch("calendarbot.main.CalendarBot") as mock_bot_class, patch(
            "calendarbot.utils.logging.apply_command_line_overrides"
        ), patch("calendarbot.utils.logging.setup_enhanced_logging"), patch(
            "config.settings.settings"
        ), patch(
            "calendarbot.__main__.apply_rpi_overrides"
        ):

            mock_bot = AsyncMock()
            mock_bot.initialize.return_value = False
            mock_bot_class.return_value = mock_bot

            result = await run_web_mode(mock_args)

            assert result == 1

    @pytest.mark.asyncio
    async def test_run_web_mode_exception(self):
        """Test web mode with general exception."""
        from calendarbot.__main__ import run_web_mode

        mock_args = MagicMock()

        with patch("signal.signal"), patch(
            "calendarbot.main.CalendarBot", side_effect=Exception("Web mode error")
        ):

            result = await run_web_mode(mock_args)

            assert result == 1


class TestMainEntry:
    """Test suite for main entry point functionality."""

    @pytest.mark.asyncio
    async def test_main_entry_setup_mode(self):
        """Test main entry with setup mode."""
        from calendarbot.__main__ import main_entry

        with patch("calendarbot.__main__.create_parser") as mock_parser, patch(
            "calendarbot.__main__.run_setup_wizard", return_value=0
        ) as mock_setup:

            mock_args = MagicMock()
            mock_args.setup = True
            mock_parser.return_value.parse_args.return_value = mock_args

            result = await main_entry()

            assert result == 0
            mock_setup.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_entry_not_configured(self):
        """Test main entry when not configured."""
        from calendarbot.__main__ import main_entry

        with patch("calendarbot.__main__.create_parser") as mock_parser, patch(
            "calendarbot.__main__.check_configuration", return_value=(False, None)
        ), patch("calendarbot.__main__.show_setup_guidance") as mock_guidance:

            mock_args = MagicMock()
            mock_args.setup = False
            mock_args.test_mode = False
            mock_parser.return_value.parse_args.return_value = mock_args

            result = await main_entry()

            assert result == 1
            mock_guidance.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_entry_test_mode_when_not_configured(self):
        """Test main entry with test mode when not configured (should still run)."""
        from calendarbot.__main__ import main_entry

        with patch("calendarbot.__main__.create_parser") as mock_parser, patch(
            "calendarbot.__main__.check_configuration", return_value=(False, None)
        ), patch("calendarbot.__main__.run_test_mode", return_value=0) as mock_test:

            mock_args = MagicMock()
            mock_args.setup = False
            mock_args.test_mode = True
            mock_args.interactive = False
            mock_args.web = False
            mock_parser.return_value.parse_args.return_value = mock_args

            result = await main_entry()

            assert result == 0
            mock_test.assert_called_once_with(mock_args)

    @pytest.mark.asyncio
    async def test_main_entry_mutually_exclusive_modes_error(self):
        """Test main entry with multiple modes specified."""
        from calendarbot.__main__ import main_entry

        with patch("calendarbot.__main__.create_parser") as mock_parser, patch(
            "calendarbot.__main__.check_configuration", return_value=(True, None)
        ):

            mock_args = MagicMock()
            mock_args.setup = False
            mock_args.test_mode = True
            mock_args.interactive = True
            mock_args.web = False

            mock_parser_instance = MagicMock()
            mock_parser_instance.parse_args.return_value = mock_args
            mock_parser_instance.error.side_effect = SystemExit(2)
            mock_parser.return_value = mock_parser_instance

            with pytest.raises(SystemExit):
                await main_entry()

    @pytest.mark.asyncio
    async def test_main_entry_web_mode(self):
        """Test main entry with web mode."""
        from calendarbot.__main__ import main_entry

        with patch("calendarbot.__main__.create_parser") as mock_parser, patch(
            "calendarbot.__main__.check_configuration", return_value=(True, None)
        ), patch("calendarbot.__main__.run_web_mode", return_value=0) as mock_web:

            mock_args = MagicMock()
            mock_args.setup = False
            mock_args.test_mode = False
            mock_args.interactive = False
            mock_args.web = True
            mock_parser.return_value.parse_args.return_value = mock_args

            result = await main_entry()

            assert result == 0
            mock_web.assert_called_once_with(mock_args)

    @pytest.mark.asyncio
    async def test_main_entry_default_interactive_mode(self):
        """Test main entry defaults to interactive mode."""
        from calendarbot.__main__ import main_entry

        with patch("calendarbot.__main__.create_parser") as mock_parser, patch(
            "calendarbot.__main__.check_configuration", return_value=(True, None)
        ), patch("calendarbot.__main__.run_interactive_mode", return_value=0) as mock_interactive:

            mock_args = MagicMock()
            mock_args.setup = False
            mock_args.test_mode = False
            mock_args.interactive = False
            mock_args.web = False
            mock_parser.return_value.parse_args.return_value = mock_args

            result = await main_entry()

            assert result == 0
            mock_interactive.assert_called_once_with(mock_args)


class TestSynchronousWrapper:
    """Test suite for synchronous wrapper functions."""

    def test_main_function_success(self):
        """Test main function with successful execution."""
        from calendarbot.__main__ import main

        with patch("asyncio.run", return_value=0), patch("sys.exit") as mock_exit:

            main()

            mock_exit.assert_called_once_with(0)

    def test_main_function_keyboard_interrupt(self):
        """Test main function with keyboard interrupt."""
        from calendarbot.__main__ import main

        with patch("asyncio.run", side_effect=KeyboardInterrupt()), patch("sys.exit") as mock_exit:

            main()

            mock_exit.assert_called_once_with(1)

    def test_main_function_exception(self):
        """Test main function with general exception."""
        from calendarbot.__main__ import main

        with patch("asyncio.run", side_effect=Exception("Fatal error")), patch(
            "sys.exit"
        ) as mock_exit:

            main()

            mock_exit.assert_called_once_with(1)

    def test_main_module_execution(self):
        """Test __main__ module execution."""
        with patch("calendarbot.__main__.main_entry") as mock_main_entry, patch(
            "asyncio.run", return_value=0
        ), patch("sys.exit") as mock_exit:

            mock_main_entry.return_value = 0

            # Simulate module execution
            exec(
                """
if __name__ == "__main__":
    import asyncio
    import sys
    from calendarbot.__main__ import main_entry
    exit_code = asyncio.run(main_entry())
    sys.exit(exit_code)
"""
            )

            # The exec above should handle the exit


class TestErrorHandling:
    """Test suite for error handling throughout main entry point."""

    @pytest.mark.asyncio
    async def test_import_errors_handled_gracefully(self):
        """Test that import errors are handled gracefully."""
        from calendarbot.__main__ import run_test_mode

        mock_args = MagicMock()

        with patch(
            "calendarbot.validation.ValidationRunner", side_effect=ImportError("Module not found")
        ):
            result = await run_test_mode(mock_args)

            assert result == 1

    def test_argument_parser_error_handling(self):
        """Test argument parser error handling."""
        from calendarbot.__main__ import create_parser

        parser = create_parser()

        # Test invalid argument
        with pytest.raises(SystemExit):
            parser.parse_args(["--invalid-argument"])

    def test_date_parsing_error_messages(self):
        """Test date parsing provides helpful error messages."""
        from calendarbot.__main__ import parse_date

        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_date("2024-13-01")  # Invalid month

        assert "Invalid date format" in str(exc_info.value)
        assert "Use YYYY-MM-DD" in str(exc_info.value)


@pytest.mark.unit
class TestIntegrationScenarios:
    """Integration test scenarios for main entry point."""

    @pytest.mark.asyncio
    async def test_full_test_mode_workflow(self):
        """Test complete test mode workflow."""
        from calendarbot.__main__ import main_entry

        with patch("sys.argv", ["calendarbot", "--test-mode", "--verbose"]), patch(
            "calendarbot.__main__.check_configuration", return_value=(True, Path("/config.yaml"))
        ), patch("calendarbot.utils.logging.apply_command_line_overrides") as mock_overrides, patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "calendarbot.validation.ValidationRunner"
        ) as mock_runner_class, patch(
            "config.settings.settings"
        ), patch(
            "calendarbot.__main__.apply_rpi_overrides"
        ):

            # Setup mocks
            mock_overrides.return_value = MagicMock()
            mock_runner = AsyncMock()
            mock_results = MagicMock()
            mock_results.has_failures.return_value = False
            mock_results.has_warnings.return_value = False
            mock_runner.run_validation.return_value = mock_results
            mock_runner_class.return_value = mock_runner

            result = await main_entry()

            assert result == 0

    def test_configuration_precedence(self):
        """Test configuration file precedence logic."""
        from calendarbot.__main__ import check_configuration

        with patch("calendarbot.__main__.Path") as mock_path, patch(
            "config.settings.CalendarBotSettings"
        ) as mock_settings_class:

            # Mock project config exists (should be preferred)
            mock_project_config = MagicMock()
            mock_project_config.exists.return_value = True

            mock_user_config = MagicMock()
            mock_user_config.exists.return_value = True

            mock_path.return_value.parent.parent.__truediv__.return_value.__truediv__.return_value = (
                mock_project_config
            )
            mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = (
                mock_user_config
            )

            is_configured, config_path = check_configuration()

            assert is_configured is True
            assert config_path == mock_project_config  # Project config should be preferred

    def test_rpi_mode_configuration_chain(self):
        """Test RPI mode configuration application chain."""
        from calendarbot.__main__ import apply_rpi_overrides

        mock_settings = MagicMock()
        mock_settings.rpi_auto_theme = True
        mock_settings.web_theme = "standard"

        mock_args = MagicMock()
        mock_args.rpi = True
        mock_args.rpi_width = 1024
        mock_args.rpi_height = 768
        mock_args.rpi_refresh_mode = "full"

        with patch("logging.getLogger"):
            result = apply_rpi_overrides(mock_settings, mock_args)

        # Verify all RPI settings applied correctly
        assert result.rpi_enabled is True
        assert result.display_type == "rpi"
        assert result.rpi_display_width == 1024
        assert result.rpi_display_height == 768
        assert result.rpi_refresh_mode == "full"
        assert result.web_theme == "eink-rpi"
