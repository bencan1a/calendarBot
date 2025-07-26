"""Tests for calendarbot/cli/config.py module.

This module tests configuration management functionality including:
- Configuration checking and file discovery
- Backup and restore operations
- Setup guidance display
- RPI override application
- Error handling for file operations
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from calendarbot.cli.config import (
    apply_cli_overrides,
    backup_configuration,
    check_configuration,
    list_backups,
    restore_configuration,
    show_setup_guidance,
)


class TestCheckConfiguration:
    """Test the check_configuration function."""

    def test_check_configuration_project_config_exists(self):
        """Test configuration check when project config file exists."""
        with patch("calendarbot.cli.config.Path") as mock_path:
            # Mock project config file exists
            mock_project_config = MagicMock()
            mock_project_config.exists.return_value = True
            # Handle two __truediv__ calls: / "config" / "config.yaml"
            mock_intermediate = MagicMock()
            mock_intermediate.__truediv__.return_value = mock_project_config
            mock_path.return_value.parent.parent.__truediv__.return_value = mock_intermediate

            is_configured, config_path = check_configuration()

            assert is_configured is True
            assert config_path == mock_project_config

    def test_check_configuration_user_config_exists(self):
        """Test configuration check when user config file exists."""
        with patch("calendarbot.cli.config.Path") as mock_path:
            # Mock project config doesn't exist, user config does
            mock_project_config = MagicMock()
            mock_project_config.exists.return_value = False

            mock_user_config = MagicMock()
            mock_user_config.exists.return_value = True

            # Handle two __truediv__ calls for project config: / "config" / "config.yaml"
            mock_intermediate = MagicMock()
            mock_intermediate.__truediv__.return_value = mock_project_config
            mock_path.return_value.parent.parent.__truediv__.return_value = mock_intermediate
            mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = (
                mock_user_config
            )

            is_configured, config_path = check_configuration()

            assert is_configured is True
            assert config_path == mock_user_config

    def test_check_configuration_environment_variables(self):
        """Test configuration check with environment variables."""
        with patch("calendarbot.cli.config.Path") as mock_path:
            # Mock no config files exist
            mock_config = MagicMock()
            mock_config.exists.return_value = False
            # Handle two __truediv__ calls for project config: / "config" / "config.yaml"
            mock_intermediate = MagicMock()
            mock_intermediate.__truediv__.return_value = mock_config
            mock_path.return_value.parent.parent.__truediv__.return_value = mock_intermediate
            mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = (
                mock_config
            )

            # Mock settings with ICS URL
            mock_settings = MagicMock()
            mock_settings.ics_url = "http://example.com/calendar.ics"

            with patch(
                "calendarbot.config.settings.CalendarBotSettings", return_value=mock_settings
            ):
                is_configured, config_path = check_configuration()

                assert is_configured is True
                assert config_path is None  # Configured via env vars

    def test_check_configuration_not_configured(self):
        """Test configuration check when not configured."""
        with patch("calendarbot.cli.config.Path") as mock_path:
            # Mock no config files exist
            mock_config = MagicMock()
            mock_config.exists.return_value = False
            # Handle two __truediv__ calls for project config: / "config" / "config.yaml"
            mock_intermediate = MagicMock()
            mock_intermediate.__truediv__.return_value = mock_config
            mock_path.return_value.parent.parent.__truediv__.return_value = mock_intermediate
            mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = (
                mock_config
            )

            # Mock settings import failure
            with patch(
                "calendarbot.config.settings.CalendarBotSettings", side_effect=ImportError()
            ):
                is_configured, config_path = check_configuration()

                assert is_configured is False
                assert config_path is None

    def test_check_configuration_settings_no_ics_url(self):
        """Test configuration check when settings exist but no ICS URL."""
        with patch("calendarbot.cli.config.Path") as mock_path:
            # Mock project config file doesn't exist
            mock_project_config = MagicMock()
            mock_project_config.exists.return_value = False

            # Mock user config file doesn't exist
            mock_user_config = MagicMock()
            mock_user_config.exists.return_value = False

            # Handle project config path: parent.parent / "config" / "config.yaml"
            mock_intermediate = MagicMock()
            mock_intermediate.__truediv__.return_value = mock_project_config
            mock_path.return_value.parent.parent.__truediv__.return_value = mock_intermediate

            # Handle user config path: home() / ".config" / "calendarbot" / "config.yaml"
            mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = (
                mock_user_config
            )

            # Mock settings without ICS URL
            mock_settings = MagicMock()
            mock_settings.ics_url = None

            with patch(
                "calendarbot.config.settings.CalendarBotSettings", return_value=mock_settings
            ):
                is_configured, config_path = check_configuration()

                assert is_configured is False
                assert config_path is None

    def test_check_configuration_general_exception(self):
        """Test configuration check with general exception."""
        with patch("calendarbot.cli.config.Path", side_effect=Exception("Test error")):
            is_configured, config_path = check_configuration()

            assert is_configured is False
            assert config_path is None


class TestShowSetupGuidance:
    """Test the show_setup_guidance function."""

    def test_show_setup_guidance_output(self, capsys):
        """Test that setup guidance displays correct content."""
        show_setup_guidance()

        captured = capsys.readouterr()
        output = captured.out

        # Check for key content elements
        assert "Welcome to Calendar Bot!" in output
        assert "Quick Setup Options:" in output
        assert "calendarbot --setup" in output
        assert "Interactive Wizard Features:" in output
        assert "config.yaml.example" in output
        assert "CALENDARBOT_ICS_URL" in output
        assert "Documentation:" in output

    def test_show_setup_guidance_formatting(self, capsys):
        """Test that setup guidance has proper formatting."""
        show_setup_guidance()

        captured = capsys.readouterr()
        output = captured.out

        # Check for formatting elements
        assert "=" * 70 in output  # Header separator
        assert "🚀" in output  # Rocket emoji (Welcome message)
        assert "📋" in output  # Clipboard emoji (Quick Setup)
        assert "🔧" in output  # Wrench emoji (Interactive Wizard)
        assert "📖" in output  # Book emoji (Documentation)


class TestBackupConfiguration:
    """Test the backup_configuration function."""

    def test_backup_configuration_success(self, capsys):
        """Test successful configuration backup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock config file
            config_file = Path(temp_dir) / "config.yaml"
            config_file.write_text("test: content")

            # Mock check_configuration to return our test file
            with patch(
                "calendarbot.cli.config.check_configuration", return_value=(True, config_file)
            ):
                with patch("calendarbot.cli.config.Path.home") as mock_home:
                    backup_dir = Path(temp_dir) / "backups"
                    mock_home.return_value = Path(temp_dir)

                    result = backup_configuration()

                    assert result == 0
                    captured = capsys.readouterr()
                    assert "Configuration backed up to:" in captured.out

    def test_backup_configuration_no_config(self, capsys):
        """Test backup when no configuration exists."""
        with patch("calendarbot.cli.config.check_configuration", return_value=(False, None)):
            result = backup_configuration()

            assert result == 1
            captured = capsys.readouterr()
            assert "No configuration file found to backup" in captured.out

    def test_backup_configuration_exception(self, capsys):
        """Test backup with exception during operation."""
        with patch(
            "calendarbot.cli.config.check_configuration", side_effect=Exception("Test error")
        ):
            result = backup_configuration()

            assert result == 1
            captured = capsys.readouterr()
            assert "Backup failed: Test error" in captured.out

    def test_backup_configuration_creates_timestamped_file(self):
        """Test that backup creates properly timestamped file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.yaml"
            config_file.write_text("test: content")

            with patch(
                "calendarbot.cli.config.check_configuration", return_value=(True, config_file)
            ):
                with patch("calendarbot.cli.config.Path.home") as mock_home:
                    mock_home.return_value = Path(temp_dir)

                    result = backup_configuration()

                    assert result == 0
                    backup_dir = Path(temp_dir) / ".config" / "calendarbot" / "backups"
                    backup_files = list(backup_dir.glob("config_backup_*.yaml"))
                    assert len(backup_files) == 1
                    assert "config_backup_" in backup_files[0].name


class TestRestoreConfiguration:
    """Test the restore_configuration function."""

    def test_restore_configuration_success(self, capsys):
        """Test successful configuration restore."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create backup file
            backup_file = Path(temp_dir) / "backup.yaml"
            backup_file.write_text("restored: content")

            with patch("calendarbot.cli.config.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                result = restore_configuration(str(backup_file))

                assert result == 0
                captured = capsys.readouterr()
                assert "Configuration restored from:" in captured.out

    def test_restore_configuration_backup_not_found(self, capsys):
        """Test restore when backup file doesn't exist."""
        result = restore_configuration("/nonexistent/backup.yaml")

        assert result == 1
        captured = capsys.readouterr()
        assert "Backup file not found:" in captured.out

    def test_restore_configuration_backs_up_current(self, capsys):
        """Test that restore backs up current config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create backup file
            backup_file = Path(temp_dir) / "backup.yaml"
            backup_file.write_text("restored: content")

            # Create existing config
            target_config = Path(temp_dir) / ".config" / "calendarbot" / "config.yaml"
            target_config.parent.mkdir(parents=True, exist_ok=True)
            target_config.write_text("existing: content")

            with patch("calendarbot.cli.config.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                result = restore_configuration(str(backup_file))

                assert result == 0
                captured = capsys.readouterr()
                assert "Current config backed up to:" in captured.out

    def test_restore_configuration_exception(self, capsys):
        """Test restore with exception during operation."""
        with patch("calendarbot.cli.config.Path", side_effect=Exception("Test error")):
            result = restore_configuration("backup.yaml")

            assert result == 1
            captured = capsys.readouterr()
            assert "Restore failed: Test error" in captured.out


class TestListBackups:
    """Test the list_backups function."""

    def test_list_backups_no_directory(self, capsys):
        """Test list backups when no backup directory exists."""
        with patch("calendarbot.cli.config.Path.home") as mock_home:
            mock_home.return_value = Path("/nonexistent")

            result = list_backups()

            assert result == 0
            captured = capsys.readouterr()
            assert "No backup directory found" in captured.out

    def test_list_backups_no_files(self, capsys):
        """Test list backups when directory exists but no backup files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / ".config" / "calendarbot" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)

            with patch("calendarbot.cli.config.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                result = list_backups()

                assert result == 0
                captured = capsys.readouterr()
                assert "No configuration backups found" in captured.out

    def test_list_backups_with_files(self, capsys):
        """Test list backups with existing backup files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / ".config" / "calendarbot" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Create test backup files
            backup1 = backup_dir / "config_backup_20240101_120000.yaml"
            backup2 = backup_dir / "config_backup_20240102_130000.yaml"
            backup1.write_text("backup1")
            backup2.write_text("backup2")

            with patch("calendarbot.cli.config.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                result = list_backups()

                assert result == 0
                captured = capsys.readouterr()
                assert "Configuration backups in" in captured.out
                assert "config_backup_20240101_120000.yaml" in captured.out
                assert "config_backup_20240102_130000.yaml" in captured.out
                assert "To restore:" in captured.out

    def test_list_backups_exception(self, capsys):
        """Test list backups with exception during operation."""
        with patch("calendarbot.cli.config.Path.home", side_effect=Exception("Test error")):
            result = list_backups()

            assert result == 1
            captured = capsys.readouterr()
            assert "Failed to list backups: Test error" in captured.out


class TestModuleLevel:
    """Test module-level functionality."""

    def test_module_exports(self):
        """Test that module exports expected functions."""
        from calendarbot.cli import config

        expected_exports = [
            "check_configuration",
            "show_setup_guidance",
            "backup_configuration",
            "restore_configuration",
            "list_backups",
            "apply_cli_overrides",
        ]

        for export in expected_exports:
            assert hasattr(config, export)
            assert callable(getattr(config, export))

    def test_module_docstring(self):
        """Test that module has proper documentation."""
        from calendarbot.cli import config

        assert config.__doc__ is not None
        assert "Configuration management for Calendar Bot CLI" in config.__doc__
