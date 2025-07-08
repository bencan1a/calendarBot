"""Unit tests for Phase 2 CLI migration functionality.

Tests the migrated entry point logic from root main.py into the CLI module structure.
"""

import argparse
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from calendarbot.cli import main_entry
from calendarbot.cli.config import (
    apply_rpi_overrides,
    backup_configuration,
    check_configuration,
    list_backups,
    restore_configuration,
    show_setup_guidance,
)
from calendarbot.cli.parser import create_parser, parse_date
from calendarbot.cli.setup import run_setup_wizard


class TestMainEntry:
    """Test the main CLI entry point function."""

    @pytest.mark.asyncio
    async def test_main_entry_setup_wizard(self):
        """Test main_entry calls setup wizard when --setup flag is provided."""
        with patch("calendarbot.cli.create_parser") as mock_parser, patch(
            "calendarbot.cli.run_setup_wizard"
        ) as mock_setup:

            mock_args = Mock()
            mock_args.setup = True
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_setup.return_value = 0

            result = await main_entry()

            assert result == 0
            mock_setup.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_entry_backup_configuration(self):
        """Test main_entry calls backup when --backup flag is provided."""
        with patch("calendarbot.cli.create_parser") as mock_parser, patch(
            "calendarbot.cli.backup_configuration"
        ) as mock_backup:

            mock_args = Mock()
            mock_args.setup = False
            mock_args.backup = True
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_backup.return_value = 0

            result = await main_entry()

            assert result == 0
            mock_backup.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_entry_unconfigured_shows_guidance(self):
        """Test main_entry shows setup guidance when not configured."""
        with patch("calendarbot.cli.create_parser") as mock_parser, patch(
            "calendarbot.cli.check_configuration"
        ) as mock_check, patch("calendarbot.cli.show_setup_guidance") as mock_guidance:

            mock_args = Mock()
            mock_args.setup = False
            mock_args.backup = False
            mock_args.restore = None
            mock_args.list_backups = False
            mock_args.test_mode = False
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_check.return_value = (False, None)  # Not configured

            result = await main_entry()

            assert result == 1
            mock_guidance.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_entry_web_mode_default(self):
        """Test main_entry defaults to web mode when configured."""
        with patch("calendarbot.cli.create_parser") as mock_parser, patch(
            "calendarbot.cli.check_configuration"
        ) as mock_check, patch("calendarbot.cli.run_web_mode") as mock_web:

            mock_args = Mock()
            mock_args.setup = False
            mock_args.backup = False
            mock_args.restore = None
            mock_args.list_backups = False
            mock_args.test_mode = False
            mock_args.interactive = False
            mock_args.web = False  # Not explicitly set, should default to web
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_check.return_value = (True, Path("/fake/config.yaml"))
            mock_web.return_value = 0

            result = await main_entry()

            assert result == 0
            mock_web.assert_called_once_with(mock_args)


class TestParser:
    """Test the argument parser functionality."""

    def test_create_parser_returns_parser(self):
        """Test create_parser returns an ArgumentParser instance."""
        parser = create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_create_parser_has_required_arguments(self):
        """Test create_parser includes all required CLI arguments."""
        parser = create_parser()

        # Get all argument destinations
        arg_dests = [action.dest for action in parser._actions if action.dest != "help"]

        required_args = [
            "setup",
            "backup",
            "restore",
            "list_backups",
            "version",
            "verbose",
            "interactive",
            "web",
            "port",
            "host",
            "auto_open",
            "rpi",
            "rpi_width",
            "rpi_height",
            "rpi_refresh_mode",
        ]

        for arg in required_args:
            assert arg in arg_dests, f"Missing required argument: {arg}"

    def test_parse_date_valid_format(self):
        """Test parse_date correctly parses valid date strings."""
        from datetime import datetime

        result = parse_date("2023-12-25")
        expected = datetime(2023, 12, 25)

        assert result == expected

    def test_parse_date_invalid_format_raises_error(self):
        """Test parse_date raises ArgumentTypeError for invalid formats."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_date("25-12-2023")  # Wrong format

        with pytest.raises(argparse.ArgumentTypeError):
            parse_date("invalid-date")


class TestConfigurationManagement:
    """Test configuration management functions."""

    def test_check_configuration_finds_project_config(self):
        """Test check_configuration finds project config file."""
        project_config = Path(__file__).parent.parent.parent / "config" / "config.yaml"

        if project_config.exists():
            is_configured, config_path = check_configuration()
            assert is_configured is True
            assert config_path == project_config

    @patch("calendarbot.cli.config.Path.home")
    def test_check_configuration_finds_user_config(self, mock_home):
        """Test check_configuration finds user config file."""
        mock_home.return_value = Path("/fake/home")

        def mock_exists(self):
            # Mock project config doesn't exist, user config does
            if "config/config.yaml" in str(self) and "/fake/home" not in str(self):
                return False
            elif ".config/calendarbot/config.yaml" in str(self):
                return True
            return False

        with patch("pathlib.Path.exists", mock_exists), patch(
            "config.settings.CalendarBotSettings"
        ) as mock_settings:
            mock_settings_instance = Mock()
            mock_settings_instance.ics_url = None
            mock_settings.return_value = mock_settings_instance

            is_configured, config_path = check_configuration()

            assert is_configured is True
            assert config_path == Path("/fake/home/.config/calendarbot/config.yaml")

    def test_apply_rpi_overrides_enables_rpi_mode(self):
        """Test apply_rpi_overrides correctly enables RPI mode."""
        mock_settings = Mock()
        mock_settings.rpi_auto_theme = True
        mock_settings.web_theme = "default"

        mock_args = Mock()
        mock_args.rpi = True
        mock_args.rpi_width = 800
        mock_args.rpi_height = 480
        mock_args.rpi_refresh_mode = "partial"

        result = apply_rpi_overrides(mock_settings, mock_args)

        assert result.rpi_enabled is True
        assert result.display_type == "rpi"
        assert result.rpi_display_width == 800
        assert result.rpi_display_height == 480
        assert result.rpi_refresh_mode == "partial"
        assert result.web_theme == "eink-rpi"

    def test_apply_rpi_overrides_no_rpi_mode(self):
        """Test apply_rpi_overrides when RPI mode is not enabled."""
        mock_settings = Mock()
        mock_args = Mock()
        mock_args.rpi = False

        result = apply_rpi_overrides(mock_settings, mock_args)

        # Settings should remain unchanged when RPI mode is disabled
        assert result == mock_settings


class TestSetupWizard:
    """Test setup wizard integration."""

    @patch("calendarbot.cli.setup.input")
    @patch("calendarbot.cli.setup.asyncio.run")
    def test_run_setup_wizard_full_mode(self, mock_asyncio_run, mock_input):
        """Test run_setup_wizard runs full wizard when choice is 1."""
        mock_input.return_value = "1"
        mock_asyncio_run.return_value = True

        with patch("calendarbot.setup_wizard.run_setup_wizard") as mock_full_wizard:
            result = run_setup_wizard()

            assert result == 0
            mock_asyncio_run.assert_called_once()

    @patch("calendarbot.cli.setup.input")
    def test_run_setup_wizard_quick_mode(self, mock_input):
        """Test run_setup_wizard runs simple wizard when choice is 2."""
        mock_input.return_value = "2"

        with patch("calendarbot.setup_wizard.run_simple_wizard") as mock_simple_wizard:
            mock_simple_wizard.return_value = True

            result = run_setup_wizard()

            assert result == 0
            mock_simple_wizard.assert_called_once()

    @patch("calendarbot.cli.setup.input")
    def test_run_setup_wizard_keyboard_interrupt(self, mock_input):
        """Test run_setup_wizard handles keyboard interrupt gracefully."""
        mock_input.side_effect = KeyboardInterrupt()

        result = run_setup_wizard()

        assert result == 1


class TestBackupRestore:
    """Test backup and restore functionality."""

    @patch("calendarbot.cli.config.check_configuration")
    def test_backup_configuration_no_config_found(self, mock_check):
        """Test backup_configuration when no config file is found."""
        mock_check.return_value = (False, None)

        result = backup_configuration()

        assert result == 1

    def test_show_setup_guidance_runs_without_error(self):
        """Test show_setup_guidance runs without error."""
        # Simply verify the function can be called without raising an exception
        try:
            show_setup_guidance()
            success = True
        except Exception:
            success = False

        assert success, "show_setup_guidance should run without error"


if __name__ == "__main__":
    pytest.main([__file__])
