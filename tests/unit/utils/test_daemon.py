"""Optimized daemon tests - 73 tests reduced to 12 tests.

Eliminates over-testing while preserving essential coverage of:
- Exception hierarchy
- Core daemon lifecycle operations
- Critical error conditions
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from calendarbot.utils.daemon import (
    DaemonAlreadyRunningError,
    DaemonController,
    DaemonError,
    DaemonManager,
    DaemonNotRunningError,
    DaemonStatus,
    PIDFileError,
)


class TestDaemonCore:
    """Essential daemon functionality only."""

    @pytest.mark.parametrize(
        "exception_class,base_class",
        [
            (DaemonError, Exception),
            (DaemonAlreadyRunningError, DaemonError),
            (DaemonNotRunningError, DaemonError),
            (PIDFileError, DaemonError),
        ],
    )
    def test_exception_inheritance(self, exception_class, base_class):
        """Test exception classes inherit correctly."""
        error = exception_class("test message")
        assert isinstance(error, base_class)
        assert str(error) == "test message"

    def test_daemon_status(self):
        """Test daemon status creation and formatting."""
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        status = DaemonStatus(pid=1234, port=8080, start_time=start_time)

        assert status.pid == 1234
        assert status.port == 8080
        assert "1234" in status.format_status()
        assert "8080" in status.format_status()

    @patch("os.getpid", return_value=1234)
    def test_pid_file_creation(self, mock_getpid, tmp_path):
        """Test PID file creation when daemon not running."""
        # Mock Path.open directly to avoid file system issues
        with patch.object(Path, "open", mock_open()) as mock_file, patch.object(Path, "mkdir"):
            manager = DaemonManager(pid_file_path=tmp_path / "test" / "daemon.pid")

            with patch.object(manager, "is_daemon_running", return_value=False):
                pid = manager.create_pid_file()
                assert pid == 1234
                mock_file.assert_called_once_with("w", encoding="utf-8")

    @patch.object(Path, "mkdir")
    def test_pid_file_already_running_error(self, mock_mkdir, tmp_path):
        """Test error when trying to create PID file for running daemon."""
        manager = DaemonManager(pid_file_path=tmp_path / "test" / "daemon.pid")

        with patch.object(manager, "is_daemon_running", return_value=True):
            with pytest.raises(DaemonAlreadyRunningError):
                manager.create_pid_file()

    @patch.object(Path, "mkdir")
    def test_daemon_running_detection(self, mock_mkdir, tmp_path):
        """Test daemon running detection with stale PID cleanup."""
        manager = DaemonManager(pid_file_path=tmp_path / "test" / "daemon.pid")

        # No PID file
        with patch.object(manager, "read_pid_file", return_value=None):
            assert manager.is_daemon_running() is False

        # Running daemon
        with (
            patch.object(manager, "read_pid_file", return_value=1234),
            patch.object(manager, "is_process_running", return_value=True),
        ):
            assert manager.is_daemon_running() is True

        # Stale PID file (cleaned up)
        with (
            patch.object(manager, "read_pid_file", return_value=1234),
            patch.object(manager, "is_process_running", return_value=False),
            patch.object(manager, "cleanup_pid_file"),
        ):
            assert manager.is_daemon_running() is False

    def test_controller_start_already_running(self):
        """Test controller prevents starting when daemon already running."""
        controller = DaemonController()

        with patch.object(controller.daemon_manager, "is_daemon_running", return_value=True):
            with pytest.raises(DaemonAlreadyRunningError):
                controller.start_daemon(command_args=["--web"], port=8080)

    def test_controller_stop_not_running(self):
        """Test controller error when stopping non-running daemon."""
        controller = DaemonController()

        with patch.object(controller.daemon_manager, "get_daemon_pid", return_value=None):
            with pytest.raises(DaemonNotRunningError):
                controller.stop_daemon()

    def test_controller_start_success(self):
        """Test successful daemon start."""
        controller = DaemonController()

        with (
            patch.object(controller.daemon_manager, "is_daemon_running", return_value=False),
            patch.object(controller.daemon_manager, "create_pid_file", return_value=1234),
            patch.object(controller, "_setup_signal_handlers"),
            patch("calendarbot.utils.daemon.detach_process"),
        ):
            pid = controller.start_daemon(command_args=["--web"], port=8080)
            assert pid == 1234

    def test_controller_stop_success(self):
        """Test successful daemon stop."""
        controller = DaemonController()

        with (
            patch.object(controller.daemon_manager, "get_daemon_pid", return_value=1234),
            patch("calendarbot.utils.daemon.os.kill") as mock_kill,
            patch.object(controller.daemon_manager, "cleanup_pid_file"),
            patch("time.sleep"),
        ):
            # Mock process stopping gracefully
            mock_kill.side_effect = [
                None,
                ProcessLookupError(),
            ]  # SIGTERM succeeds, then process gone

            result = controller.stop_daemon()
            assert result is True

    def test_controller_status_not_running(self):
        """Test status retrieval when daemon not running."""
        controller = DaemonController()

        with patch.object(controller.daemon_manager, "is_daemon_running", return_value=False):
            assert controller.get_daemon_status() is None

    def test_controller_status_running(self):
        """Test status retrieval when daemon running."""
        controller = DaemonController()

        mock_process_info = {"cmdline": ["--web", "--port", "8080"], "running": True}

        with (
            patch.object(controller.daemon_manager, "get_daemon_pid", return_value=1234),
            patch.object(
                controller.daemon_manager, "get_process_info", return_value=mock_process_info
            ),
            patch.object(controller, "_parse_port_from_cmdline", return_value=8080),
        ):
            status = controller.get_daemon_status()
            assert status.pid == 1234
            assert status.port == 8080

    def test_convenience_functions(self):
        """Test module-level convenience functions delegate correctly."""
        from calendarbot.utils.daemon import is_daemon_running, stop_daemon

        with (
            patch("calendarbot.utils.daemon.DaemonManager") as mock_manager_class,
            patch("calendarbot.utils.daemon.DaemonController") as mock_controller_class,
        ):
            mock_manager = MagicMock()
            mock_controller = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_controller_class.return_value = mock_controller

            # Test is_daemon_running delegates to DaemonManager
            is_daemon_running()
            mock_manager.is_daemon_running.assert_called_once()

            # Test stop_daemon delegates to DaemonController
            stop_daemon()
            mock_controller.stop_daemon.assert_called_once()
