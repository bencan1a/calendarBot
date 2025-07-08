"""Tests for secure helper functions."""

import os
import subprocess
from unittest.mock import Mock, patch

import pytest

from calendarbot.utils.helpers import secure_clear_screen


class TestSecureClearScreen:
    """Test secure screen clearing functionality."""

    @patch("subprocess.run")
    @patch("os.name", "posix")
    def test_secure_clear_screen_posix_success(self, mock_run):
        """Test successful screen clearing on POSIX systems."""
        mock_run.return_value = Mock()

        result = secure_clear_screen()

        assert result is True
        mock_run.assert_called_once_with(["clear"], check=True, timeout=5)

    @patch("subprocess.run")
    @patch("os.name", "nt")
    def test_secure_clear_screen_windows_success(self, mock_run):
        """Test successful screen clearing on Windows systems."""
        mock_run.return_value = Mock()

        result = secure_clear_screen()

        assert result is True
        mock_run.assert_called_once_with(["cmd.exe", "/c", "cls"], check=True, timeout=5)

    @patch("subprocess.run")
    @patch("os.name", "posix")
    def test_secure_clear_screen_command_fails(self, mock_run):
        """Test handling of command execution failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, ["clear"])

        with patch("builtins.print") as mock_print:
            result = secure_clear_screen()

        assert result is False
        mock_run.assert_called_once_with(["clear"], check=True, timeout=5)
        mock_print.assert_called_once_with("\n" * 50)

    @patch("subprocess.run")
    @patch("os.name", "posix")
    def test_secure_clear_screen_timeout(self, mock_run):
        """Test handling of command timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(["clear"], 5)

        with patch("builtins.print") as mock_print:
            result = secure_clear_screen()

        assert result is False
        mock_run.assert_called_once_with(["clear"], check=True, timeout=5)
        mock_print.assert_called_once_with("\n" * 50)

    @patch("subprocess.run")
    @patch("os.name", "posix")
    def test_secure_clear_screen_file_not_found(self, mock_run):
        """Test handling when clear command is not found."""
        mock_run.side_effect = FileNotFoundError("clear command not found")

        with patch("builtins.print") as mock_print:
            result = secure_clear_screen()

        assert result is False
        mock_run.assert_called_once_with(["clear"], check=True, timeout=5)
        mock_print.assert_called_once_with("\n" * 50)

    @patch("subprocess.run")
    @patch("os.name", "posix")
    def test_secure_clear_screen_unexpected_error(self, mock_run):
        """Test handling of unexpected errors."""
        mock_run.side_effect = RuntimeError("Unexpected error")

        with patch("builtins.print") as mock_print:
            result = secure_clear_screen()

        assert result is False
        mock_run.assert_called_once_with(["clear"], check=True, timeout=5)
        mock_print.assert_called_once_with("\n" * 50)

    @patch("subprocess.run")
    @patch("os.name", "unknown")
    def test_secure_clear_screen_unknown_os(self, mock_run):
        """Test screen clearing on unknown OS (defaults to Windows behavior)."""
        mock_run.return_value = Mock()

        result = secure_clear_screen()

        assert result is True
        mock_run.assert_called_once_with(["cmd.exe", "/c", "cls"], check=True, timeout=5)
