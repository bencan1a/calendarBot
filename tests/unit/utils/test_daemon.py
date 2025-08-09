"""Unit tests for calendarbot/utils/daemon.py

This test suite provides comprehensive coverage of daemon process management utilities
including PID file management, process detachment, status monitoring, and graceful
shutdown handling. All external dependencies are mocked for isolated testing.
"""

import signal
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest

import calendarbot.utils.daemon as daemon_module
from calendarbot.utils.daemon import (
    DaemonAlreadyRunningError,
    DaemonController,
    # Exception classes
    DaemonError,
    DaemonManager,
    DaemonNotRunningError,
    # Core classes
    DaemonStatus,
    PIDFileError,
    cleanup_daemon,
    # Functions
    detach_process,
    get_daemon_status,
    get_pid_file_path,
    is_daemon_running,
    start_daemon,
    stop_daemon,
)


class TestDaemonExceptions:
    """Test custom daemon exception classes."""

    def test_daemon_error_when_instantiated_then_inherits_from_exception(self):
        """Test that DaemonError inherits from Exception."""
        # Arrange & Act
        error = DaemonError("Test message")

        # Assert
        assert isinstance(error, Exception)
        assert str(error) == "Test message"

    def test_daemon_already_running_error_when_instantiated_then_inherits_from_daemon_error(self):
        """Test that DaemonAlreadyRunningError inherits from DaemonError."""
        # Arrange & Act
        error = DaemonAlreadyRunningError("Already running")

        # Assert
        assert isinstance(error, DaemonError)
        assert isinstance(error, Exception)
        assert str(error) == "Already running"

    def test_daemon_not_running_error_when_instantiated_then_inherits_from_daemon_error(self):
        """Test that DaemonNotRunningError inherits from DaemonError."""
        # Arrange & Act
        error = DaemonNotRunningError("Not running")

        # Assert
        assert isinstance(error, DaemonError)
        assert str(error) == "Not running"

    def test_pid_file_error_when_instantiated_then_inherits_from_daemon_error(self):
        """Test that PIDFileError inherits from DaemonError."""
        # Arrange & Act
        error = PIDFileError("PID file error")

        # Assert
        assert isinstance(error, DaemonError)
        assert str(error) == "PID file error"


class TestDaemonStatus:
    """Test DaemonStatus class for daemon status information and monitoring."""

    def test_daemon_status_when_initialized_with_required_params_then_sets_attributes(self):
        """Test DaemonStatus initialization with required parameters."""
        # Arrange & Act
        status = DaemonStatus(pid=1234, port=8080)

        # Assert
        assert status.pid == 1234
        assert status.port == 8080
        assert isinstance(status.start_time, datetime)
        assert status.log_file is None
        assert status.is_healthy is True

    def test_daemon_status_when_initialized_with_all_params_then_sets_all_attributes(self):
        """Test DaemonStatus initialization with all parameters."""
        # Arrange
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        log_file = Path("/var/log/daemon.log")

        # Act
        status = DaemonStatus(
            pid=5678, port=9000, start_time=start_time, log_file=log_file, is_healthy=False
        )

        # Assert
        assert status.pid == 5678
        assert status.port == 9000
        assert status.start_time == start_time
        assert status.log_file == log_file
        assert status.is_healthy is False

    @patch("calendarbot.utils.daemon.datetime")
    def test_daemon_status_uptime_when_called_then_calculates_difference(self, mock_datetime):
        """Test uptime property calculates time difference correctly."""
        # Arrange
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        current_time = datetime(2024, 1, 1, 12, 30, 0)
        mock_datetime.now.return_value = current_time

        status = DaemonStatus(pid=1234, port=8080, start_time=start_time)

        # Act
        uptime = status.uptime

        # Assert
        assert uptime == timedelta(minutes=30)

    @patch("calendarbot.utils.daemon.datetime")
    def test_daemon_status_format_status_when_called_then_returns_formatted_string(
        self, mock_datetime
    ):
        """Test format_status method returns properly formatted status."""
        # Arrange
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        current_time = datetime(2024, 1, 1, 12, 15, 30)
        mock_datetime.now.return_value = current_time

        status = DaemonStatus(
            pid=1234,
            port=8080,
            start_time=start_time,
            log_file=Path("/var/log/daemon.log"),
            is_healthy=True,
        )

        # Act
        formatted = status.format_status()

        # Assert
        expected_lines = [
            "CalendarBot Daemon Status:",
            "  PID: 1234",
            "  Port: 8080",
            "  Uptime: 0:15:30",
            "  Health: healthy",
            "  Log file: /var/log/daemon.log",
        ]
        assert formatted == "\n".join(expected_lines)

    @patch("calendarbot.utils.daemon.datetime")
    def test_daemon_status_format_status_when_unhealthy_then_shows_unhealthy(self, mock_datetime):
        """Test format_status shows unhealthy status correctly."""
        # Arrange
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        current_time = datetime(2024, 1, 1, 12, 1, 0)
        mock_datetime.now.return_value = current_time

        status = DaemonStatus(pid=9999, port=3000, start_time=start_time, is_healthy=False)

        # Act
        formatted = status.format_status()

        # Assert
        assert "Health: unhealthy" in formatted

    @patch("calendarbot.utils.daemon.datetime")
    def test_daemon_status_format_status_when_no_log_file_then_excludes_log_line(
        self, mock_datetime
    ):
        """Test format_status excludes log file line when log_file is None."""
        # Arrange
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        current_time = datetime(2024, 1, 1, 12, 1, 0)
        mock_datetime.now.return_value = current_time

        status = DaemonStatus(pid=1234, port=8080, start_time=start_time)

        # Act
        formatted = status.format_status()

        # Assert
        assert "Log file:" not in formatted


class TestDaemonManager:
    """Test DaemonManager class for PID file operations and process management."""

    @patch("calendarbot.utils.daemon.Path.home")
    def test_daemon_manager_when_no_pid_file_specified_then_uses_default_path(self, mock_home):
        """Test DaemonManager uses default PID file path when none specified."""
        # Arrange
        mock_home.return_value = Path("/mock/home")

        with patch.object(Path, "mkdir") as mock_mkdir:
            # Act
            manager = DaemonManager()

            # Assert
            expected_path = Path("/mock/home/.calendarbot/daemon.pid")
            assert manager.pid_file_path == expected_path
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_daemon_manager_when_custom_pid_file_specified_then_uses_custom_path(self):
        """Test DaemonManager uses custom PID file path when specified."""
        # Arrange
        custom_path = Path("/custom/path/daemon.pid")

        with patch.object(Path, "mkdir") as mock_mkdir:
            # Act
            manager = DaemonManager(pid_file_path=custom_path)

            # Assert
            assert manager.pid_file_path == custom_path
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("calendarbot.utils.daemon.Path.home")
    def test_get_default_pid_file_path_when_called_then_returns_correct_path(self, mock_home):
        """Test get_default_pid_file_path returns correct default path."""
        # Arrange
        mock_home.return_value = Path("/mock/home")

        # Act
        path = DaemonManager.get_default_pid_file_path()

        # Assert
        expected = Path("/mock/home/.calendarbot/daemon.pid")
        assert path == expected

    @patch("calendarbot.utils.daemon.os.getpid")
    @patch("calendarbot.utils.daemon.logger")
    def test_create_pid_file_when_no_existing_daemon_then_creates_file(
        self, mock_logger, mock_getpid
    ):
        """Test create_pid_file creates PID file when no daemon running."""
        # Arrange
        mock_getpid.return_value = 1234

        with (
            patch.object(Path, "mkdir") as mock_mkdir,
            patch.object(Path, "open", mock_open()) as mock_file,
        ):
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            with patch.object(manager, "is_daemon_running", return_value=False):
                # Act
                pid = manager.create_pid_file()

                # Assert
                assert pid == 1234
                mock_file.assert_called_once_with("w", encoding="utf-8")
                mock_file().write.assert_called_once_with("1234")

    def test_create_pid_file_when_daemon_already_running_then_raises_error(self):
        """Test create_pid_file raises DaemonAlreadyRunningError when daemon running."""
        # Arrange
        with patch.object(Path, "mkdir") as mock_mkdir:
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            with (
                patch.object(manager, "is_daemon_running", return_value=True),
                patch.object(manager, "read_pid_file", return_value=5678),
            ):
                # Act & Assert
                with pytest.raises(DaemonAlreadyRunningError) as exc_info:
                    manager.create_pid_file()

                assert "Daemon already running with PID 5678" in str(exc_info.value)

    def test_create_pid_file_when_custom_pid_specified_then_uses_custom_pid(self):
        """Test create_pid_file uses custom PID when specified."""
        # Arrange
        with (
            patch.object(Path, "mkdir") as mock_mkdir,
            patch.object(Path, "open", mock_open()) as mock_file,
        ):
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            with patch.object(manager, "is_daemon_running", return_value=False):
                # Act
                pid = manager.create_pid_file(pid=9999)

                # Assert
                assert pid == 9999
                mock_file().write.assert_called_once_with("9999")

    def test_create_pid_file_when_file_write_fails_then_raises_pid_file_error(self):
        """Test create_pid_file raises PIDFileError when file write fails."""
        # Arrange
        with (
            patch.object(Path, "mkdir") as mock_mkdir,
            patch.object(Path, "open", side_effect=OSError("Permission denied")),
        ):
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            with patch.object(manager, "is_daemon_running", return_value=False):
                # Act & Assert
                with pytest.raises(PIDFileError) as exc_info:
                    manager.create_pid_file()

                assert "Failed to create PID file" in str(exc_info.value)

    def test_read_pid_file_when_file_exists_and_valid_then_returns_pid(self):
        """Test read_pid_file returns PID when file exists and contains valid PID."""
        # Arrange
        with (
            patch.object(Path, "mkdir") as mock_mkdir,
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data="1234")),
        ):
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            # Act
            pid = manager.read_pid_file()

            # Assert
            assert pid == 1234

    def test_read_pid_file_when_file_does_not_exist_then_returns_none(self):
        """Test read_pid_file returns None when PID file doesn't exist."""
        # Arrange
        with (
            patch.object(Path, "mkdir") as mock_mkdir,
            patch.object(Path, "exists", return_value=False),
        ):
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            # Act
            pid = manager.read_pid_file()

            # Assert
            assert pid is None

    @patch("calendarbot.utils.daemon.logger")
    def test_read_pid_file_when_file_empty_then_returns_none(self, mock_logger):
        """Test read_pid_file returns None when PID file is empty."""
        # Arrange
        with (
            patch.object(Path, "mkdir") as mock_mkdir,
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data="")),
        ):
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            # Act
            pid = manager.read_pid_file()

            # Assert
            assert pid is None
            mock_logger.warning.assert_called_once()

    @patch("calendarbot.utils.daemon.logger")
    def test_read_pid_file_when_invalid_pid_then_returns_none(self, mock_logger):
        """Test read_pid_file returns None when PID is invalid."""
        # Arrange
        with (
            patch.object(Path, "mkdir") as mock_mkdir,
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data="0")),
        ):
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            # Act
            pid = manager.read_pid_file()

            # Assert
            assert pid is None
            mock_logger.warning.assert_called_once()

    @patch("calendarbot.utils.daemon.logger")
    def test_read_pid_file_when_non_numeric_content_then_returns_none(self, mock_logger):
        """Test read_pid_file returns None when PID file contains non-numeric content."""
        # Arrange
        with (
            patch.object(Path, "mkdir") as mock_mkdir,
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", mock_open(read_data="not_a_number")),
        ):
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            # Act
            pid = manager.read_pid_file()

            # Assert
            assert pid is None
            mock_logger.warning.assert_called_once()

    @patch("calendarbot.utils.daemon.logger")
    def test_read_pid_file_when_read_fails_then_returns_none(self, mock_logger):
        """Test read_pid_file returns None when file read fails."""
        # Arrange
        with (
            patch.object(Path, "mkdir") as mock_mkdir,
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "open", side_effect=OSError("Read error")),
        ):
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            # Act
            pid = manager.read_pid_file()

            # Assert
            assert pid is None
            mock_logger.warning.assert_called_once()

    def test_cleanup_pid_file_when_file_exists_then_removes_file(self):
        """Test cleanup_pid_file removes PID file when it exists."""
        # Arrange
        with (
            patch.object(Path, "mkdir") as mock_mkdir,
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "unlink") as mock_unlink,
        ):
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            # Act
            result = manager.cleanup_pid_file()

            # Assert
            assert result is True
            mock_unlink.assert_called_once()

    def test_cleanup_pid_file_when_file_does_not_exist_then_returns_true(self):
        """Test cleanup_pid_file returns True when file doesn't exist."""
        # Arrange
        with (
            patch.object(Path, "mkdir") as mock_mkdir,
            patch.object(Path, "exists", return_value=False),
        ):
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            # Act
            result = manager.cleanup_pid_file()

            # Assert
            assert result is True

    @patch("calendarbot.utils.daemon.logger")
    def test_cleanup_pid_file_when_removal_fails_then_returns_false(self, mock_logger):
        """Test cleanup_pid_file returns False when file removal fails."""
        # Arrange
        with (
            patch.object(Path, "mkdir") as mock_mkdir,
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "unlink", side_effect=OSError("Permission denied")),
        ):
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            # Act
            result = manager.cleanup_pid_file()

            # Assert
            assert result is False
            mock_logger.exception.assert_called_once()

    @pytest.mark.parametrize(
        "psutil_available,psutil_result,expected",
        [
            (True, True, True),
            (True, False, False),
            (False, True, True),  # psutil not available, os.kill succeeds
            (False, False, False),  # psutil not available, os.kill fails
        ],
    )
    def test_is_process_running_when_different_scenarios_then_returns_correct_result(
        self, psutil_available: bool, psutil_result: bool, expected: bool
    ):
        """Test is_process_running with various psutil availability and results."""
        # Arrange
        with patch.object(Path, "mkdir") as mock_mkdir:
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            if psutil_available:
                # Mock psutil as available
                mock_psutil = MagicMock()
                mock_psutil.pid_exists.return_value = psutil_result
                with (
                    patch.object(daemon_module, "PSUTIL_AVAILABLE", True),
                    patch.object(daemon_module, "psutil", mock_psutil),
                ):
                    result = manager.is_process_running(1234)
            else:
                # Mock psutil as not available - use os.kill fallback
                with (
                    patch.object(daemon_module, "PSUTIL_AVAILABLE", False),
                    patch.object(daemon_module, "psutil", None),
                ):
                    if psutil_result:  # os.kill succeeds
                        with patch("os.kill", return_value=None):
                            result = manager.is_process_running(1234)
                    else:  # os.kill fails
                        with patch("os.kill", side_effect=ProcessLookupError("Process not found")):
                            result = manager.is_process_running(1234)

            # Assert
            assert result == expected

    def test_is_daemon_running_when_no_pid_file_then_returns_false(self):
        """Test is_daemon_running returns False when no PID file exists."""
        # Arrange
        with patch.object(Path, "mkdir") as mock_mkdir:
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            with patch.object(manager, "read_pid_file", return_value=None):
                # Act
                result = manager.is_daemon_running()

                # Assert
                assert result is False

    def test_is_daemon_running_when_process_running_then_returns_true(self):
        """Test is_daemon_running returns True when process is running."""
        # Arrange
        with patch.object(Path, "mkdir") as mock_mkdir:
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            with (
                patch.object(manager, "read_pid_file", return_value=1234),
                patch.object(manager, "is_process_running", return_value=True),
            ):
                # Act
                result = manager.is_daemon_running()

                # Assert
                assert result is True

    @patch("calendarbot.utils.daemon.logger")
    def test_is_daemon_running_when_process_not_running_then_cleans_up_and_returns_false(
        self, mock_logger
    ):
        """Test is_daemon_running cleans up stale PID file when process not running."""
        # Arrange
        with patch.object(Path, "mkdir") as mock_mkdir:
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            with (
                patch.object(manager, "read_pid_file", return_value=1234),
                patch.object(manager, "is_process_running", return_value=False),
                patch.object(manager, "cleanup_pid_file") as mock_cleanup,
            ):
                # Act
                result = manager.is_daemon_running()

                # Assert
                assert result is False
                mock_cleanup.assert_called_once()
                mock_logger.info.assert_called_once()

    def test_get_daemon_pid_when_daemon_running_then_returns_pid(self):
        """Test get_daemon_pid returns PID when daemon is running."""
        # Arrange
        with patch.object(Path, "mkdir") as mock_mkdir:
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            with (
                patch.object(manager, "is_daemon_running", return_value=True),
                patch.object(manager, "read_pid_file", return_value=1234),
            ):
                # Act
                pid = manager.get_daemon_pid()

                # Assert
                assert pid == 1234

    def test_get_daemon_pid_when_daemon_not_running_then_returns_none(self):
        """Test get_daemon_pid returns None when daemon is not running."""
        # Arrange
        with patch.object(Path, "mkdir") as mock_mkdir:
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            with patch.object(manager, "is_daemon_running", return_value=False):
                # Act
                pid = manager.get_daemon_pid()

                # Assert
                assert pid is None

    def test_get_process_info_when_process_not_running_then_returns_basic_info(self):
        """Test get_process_info returns basic info when process not running."""
        # Arrange
        with patch.object(Path, "mkdir") as mock_mkdir:
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            with patch.object(manager, "is_process_running", return_value=False):
                # Act
                info = manager.get_process_info(1234)

                # Assert
                assert info == {"pid": 1234, "running": False}

    @patch("calendarbot.utils.daemon.PSUTIL_AVAILABLE", True)
    @patch("calendarbot.utils.daemon.psutil")
    def test_get_process_info_when_psutil_available_and_process_running_then_returns_detailed_info(
        self, mock_psutil
    ):
        """Test get_process_info returns detailed info when psutil available and process running."""
        # Arrange
        with patch.object(Path, "mkdir") as mock_mkdir:
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            mock_process = Mock()
            mock_process.name.return_value = "test_process"
            mock_process.create_time.return_value = 1640995200.0  # timestamp
            mock_process.memory_info.return_value._asdict.return_value = {"rss": 1024, "vms": 2048}
            mock_process.cpu_percent.return_value = 15.5
            mock_process.status.return_value = "running"

            mock_psutil.Process.return_value = mock_process

            with patch.object(manager, "is_process_running", return_value=True):
                # Act
                info = manager.get_process_info(1234)

                # Assert
                assert info["pid"] == 1234
                assert info["running"] is True
                assert info["name"] == "test_process"
                assert info["memory_info"] == {"rss": 1024, "vms": 2048}
                assert info["cpu_percent"] == 15.5
                assert info["status"] == "running"

    def test_get_process_info_when_psutil_error_then_logs_warning(self):
        """Test get_process_info logs warning when psutil raises exception."""
        # Arrange
        with patch.object(Path, "mkdir") as mock_mkdir:
            manager = DaemonManager(pid_file_path=Path("/test/daemon.pid"))

            # Create proper exception classes that inherit from BaseException
            class MockNoSuchProcess(Exception):
                def __init__(self, pid):
                    self.pid = pid
                    super().__init__(f"No process with PID {pid}")

            # Create a mock psutil with proper exception classes
            mock_psutil = MagicMock()
            mock_psutil.NoSuchProcess = MockNoSuchProcess
            mock_psutil.AccessDenied = MockNoSuchProcess  # Use same for simplicity

            def raise_exception(*args, **kwargs):
                raise MockNoSuchProcess(1234)

            mock_psutil.Process.side_effect = raise_exception

            with (
                patch.object(daemon_module, "PSUTIL_AVAILABLE", True),
                patch.object(daemon_module, "psutil", mock_psutil),
                patch.object(manager, "is_process_running", return_value=True),
                patch("calendarbot.utils.daemon.logger") as mock_logger,
            ):
                # Act
                info = manager.get_process_info(1234)

                # Assert
                assert info == {"pid": 1234, "running": True}
                mock_logger.warning.assert_called_once()


class TestDaemonController:
    """Test DaemonController class for high-level daemon operations."""

    def test_daemon_controller_when_no_daemon_manager_specified_then_creates_default(self):
        """Test DaemonController creates default DaemonManager when none specified."""
        # Arrange & Act
        with (
            patch("calendarbot.utils.daemon.DaemonManager") as mock_manager_class,
            patch("calendarbot.utils.daemon.get_logger") as mock_get_logger,
        ):
            controller = DaemonController()

            # Assert
            mock_manager_class.assert_called_once()
            assert controller.daemon_manager is not None

    def test_daemon_controller_when_custom_daemon_manager_specified_then_uses_custom(self):
        """Test DaemonController uses custom DaemonManager when specified."""
        # Arrange
        custom_manager = Mock()

        with patch("calendarbot.utils.daemon.get_logger"):
            # Act
            controller = DaemonController(daemon_manager=custom_manager)

            # Assert
            assert controller.daemon_manager == custom_manager

    @patch("calendarbot.utils.daemon.detach_process")
    def test_start_daemon_when_daemon_not_running_then_starts_successfully(self, mock_detach):
        """Test start_daemon starts daemon successfully when not already running."""
        # Arrange
        mock_manager = Mock()
        mock_manager.is_daemon_running.return_value = False
        mock_manager.create_pid_file.return_value = 1234

        with patch("calendarbot.utils.daemon.get_logger"):
            controller = DaemonController(daemon_manager=mock_manager)

            with patch.object(controller, "_setup_signal_handlers") as mock_signals:
                # Act
                pid = controller.start_daemon(["--web"], port=8080, detach=True)

                # Assert
                assert pid == 1234
                mock_detach.assert_called_once()
                mock_manager.create_pid_file.assert_called_once()
                mock_signals.assert_called_once()

    def test_start_daemon_when_daemon_already_running_then_raises_error(self):
        """Test start_daemon raises DaemonAlreadyRunningError when daemon already running."""
        # Arrange
        mock_manager = Mock()
        mock_manager.is_daemon_running.return_value = True
        mock_manager.get_daemon_pid.return_value = 5678

        with patch("calendarbot.utils.daemon.get_logger"):
            controller = DaemonController(daemon_manager=mock_manager)

            # Act & Assert
            with pytest.raises(DaemonAlreadyRunningError) as exc_info:
                controller.start_daemon(["--web"], port=8080)

            assert "Daemon already running with PID 5678" in str(exc_info.value)

    @patch("calendarbot.utils.daemon.detach_process")
    def test_start_daemon_when_detach_false_then_skips_detachment(self, mock_detach):
        """Test start_daemon skips process detachment when detach=False."""
        # Arrange
        mock_manager = Mock()
        mock_manager.is_daemon_running.return_value = False
        mock_manager.create_pid_file.return_value = 9999

        with patch("calendarbot.utils.daemon.get_logger"):
            controller = DaemonController(daemon_manager=mock_manager)

            with patch.object(controller, "_setup_signal_handlers"):
                # Act
                pid = controller.start_daemon(["--web"], detach=False)

                # Assert
                assert pid == 9999
                mock_detach.assert_not_called()

    @patch("calendarbot.utils.daemon.os.kill")
    @patch("calendarbot.utils.daemon.time.sleep")
    def test_stop_daemon_when_graceful_shutdown_successful_then_returns_true(
        self, mock_sleep, mock_kill
    ):
        """Test stop_daemon returns True when graceful shutdown successful."""
        # Arrange
        mock_manager = Mock()
        mock_manager.get_daemon_pid.return_value = 1234
        mock_manager.is_process_running.side_effect = [True, False]  # Running, then stopped
        mock_manager.cleanup_pid_file.return_value = True

        with patch("calendarbot.utils.daemon.get_logger"):
            controller = DaemonController(daemon_manager=mock_manager)

            # Act
            result = controller.stop_daemon(timeout=30)

            # Assert
            assert result is True
            mock_kill.assert_called_once_with(1234, signal.SIGTERM)
            mock_manager.cleanup_pid_file.assert_called_once()

    def test_stop_daemon_when_no_daemon_running_then_raises_error(self):
        """Test stop_daemon raises DaemonNotRunningError when no daemon running."""
        # Arrange
        mock_manager = Mock()
        mock_manager.get_daemon_pid.return_value = None

        with patch("calendarbot.utils.daemon.get_logger"):
            controller = DaemonController(daemon_manager=mock_manager)

            # Act & Assert
            with pytest.raises(DaemonNotRunningError) as exc_info:
                controller.stop_daemon()

            assert "No daemon is currently running" in str(exc_info.value)

    def test_stop_daemon_when_graceful_timeout_then_force_kills(self):
        """Test stop_daemon force kills process when graceful shutdown times out."""
        controller = DaemonController()

        with (
            patch.object(controller.daemon_manager, "get_daemon_pid", return_value=1234),
            patch("os.kill") as mock_kill,
            patch("time.sleep"),
            patch.object(controller.daemon_manager, "cleanup_pid_file", return_value=True),
        ):
            # Mock process that doesn't die gracefully for timeout period, then dies after force kill
            call_count = [0]

            def mock_is_running(*args):
                call_count[0] += 1
                # Process stays alive during timeout period (2 calls), then dies after force kill
                if call_count[0] <= 2:  # Stay alive for timeout period
                    return True
                # Die after force kill
                return False

            with patch.object(
                controller.daemon_manager, "is_process_running", side_effect=mock_is_running
            ):
                result = controller.stop_daemon(timeout=2)  # 2 second timeout

                # Assert
                assert result is True
                # Should call both SIGTERM and SIGKILL
                expected_calls = [call(1234, signal.SIGTERM), call(1234, signal.SIGKILL)]
                mock_kill.assert_has_calls(expected_calls)

    @patch("calendarbot.utils.daemon.os.kill")
    def test_stop_daemon_when_process_already_dead_then_cleans_up_gracefully(self, mock_kill):
        """Test stop_daemon handles already dead process gracefully."""
        # Arrange
        mock_manager = Mock()
        mock_manager.get_daemon_pid.return_value = 1234
        mock_manager.cleanup_pid_file.return_value = True
        mock_kill.side_effect = ProcessLookupError("Process not found")

        with patch("calendarbot.utils.daemon.get_logger"):
            controller = DaemonController(daemon_manager=mock_manager)

            # Act
            result = controller.stop_daemon()

            # Assert
            assert result is True
            mock_manager.cleanup_pid_file.assert_called_once()

    def test_get_daemon_status_when_daemon_not_running_then_returns_none(self):
        """Test get_daemon_status returns None when daemon not running."""
        # Arrange
        mock_manager = Mock()
        mock_manager.get_daemon_pid.return_value = None

        with patch("calendarbot.utils.daemon.get_logger"):
            controller = DaemonController(daemon_manager=mock_manager)

            # Act
            status = controller.get_daemon_status()

            # Assert
            assert status is None

    @patch("calendarbot.utils.daemon.PSUTIL_AVAILABLE", True)
    def test_get_daemon_status_when_daemon_running_then_returns_status_object(self):
        """Test get_daemon_status returns DaemonStatus object when daemon running."""
        # Arrange
        mock_manager = Mock()
        mock_manager.get_daemon_pid.return_value = 1234
        mock_manager.get_process_info.return_value = {
            "running": True,
            "create_time": datetime(2024, 1, 1, 12, 0, 0),
        }

        with patch("calendarbot.utils.daemon.get_logger"):
            controller = DaemonController(daemon_manager=mock_manager)

            # Act
            status = controller.get_daemon_status()

            # Assert
            assert isinstance(status, DaemonStatus)
            assert status.pid == 1234
            assert status.port == 8000  # Default port
            assert status.is_healthy is True

    @patch("calendarbot.utils.daemon.os.kill")
    def test_send_signal_when_daemon_running_then_sends_signal(self, mock_kill):
        """Test send_signal sends signal to running daemon."""
        # Arrange
        mock_manager = Mock()
        mock_manager.get_daemon_pid.return_value = 1234

        with patch("calendarbot.utils.daemon.get_logger"):
            controller = DaemonController(daemon_manager=mock_manager)

            # Act
            result = controller.send_signal(signal.SIGUSR1)

            # Assert
            assert result is True
            mock_kill.assert_called_once_with(1234, signal.SIGUSR1)

    def test_send_signal_when_no_daemon_running_then_raises_error(self):
        """Test send_signal raises DaemonNotRunningError when no daemon running."""
        # Arrange
        mock_manager = Mock()
        mock_manager.get_daemon_pid.return_value = None

        with patch("calendarbot.utils.daemon.get_logger"):
            controller = DaemonController(daemon_manager=mock_manager)

            # Act & Assert
            with pytest.raises(DaemonNotRunningError):
                controller.send_signal(signal.SIGUSR1)

    @patch("calendarbot.utils.daemon.os.kill")
    @patch("calendarbot.utils.daemon.logger")
    def test_send_signal_when_signal_fails_then_returns_false(self, mock_logger, mock_kill):
        """Test send_signal returns False when signal sending fails."""
        # Arrange
        mock_manager = Mock()
        mock_manager.get_daemon_pid.return_value = 1234
        mock_kill.side_effect = OSError("Permission denied")

        with patch("calendarbot.utils.daemon.get_logger"):
            controller = DaemonController(daemon_manager=mock_manager)

            # Act
            result = controller.send_signal(signal.SIGUSR1)

            # Assert
            assert result is False

    @patch("calendarbot.utils.daemon.signal.signal")
    @patch("calendarbot.utils.daemon.sys.exit")
    def test_setup_signal_handlers_when_called_then_registers_handlers(
        self, mock_exit, mock_signal_func
    ):
        """Test _setup_signal_handlers registers signal handlers."""
        # Arrange
        mock_manager = Mock()

        with patch("calendarbot.utils.daemon.get_logger"):
            controller = DaemonController(daemon_manager=mock_manager)

            # Act
            controller._setup_signal_handlers()

            # Assert
            # Should register handlers for SIGTERM and SIGINT
            assert mock_signal_func.call_count == 2

            # Test signal handler functionality
            signal_handler = mock_signal_func.call_args_list[0][0][1]
            signal_handler(signal.SIGTERM, None)

            mock_manager.cleanup_pid_file.assert_called_once()
            mock_exit.assert_called_once_with(0)


class TestDetachProcess:
    """Test detach_process function for Unix daemon detachment."""

    @patch("calendarbot.utils.daemon.os.fork")
    @patch("calendarbot.utils.daemon.os.setsid")
    @patch("calendarbot.utils.daemon.os.chdir")
    @patch("calendarbot.utils.daemon.os.umask")
    @patch("calendarbot.utils.daemon.os.dup2")
    @patch("calendarbot.utils.daemon.os.getpid")
    @patch("calendarbot.utils.daemon.sys.exit")
    @patch("calendarbot.utils.daemon.sys.stdin")
    @patch("calendarbot.utils.daemon.sys.stdout")
    @patch("calendarbot.utils.daemon.sys.stderr")
    @patch("calendarbot.utils.daemon.logger")
    def test_detach_process_when_successful_then_completes_double_fork(
        self,
        mock_logger,
        mock_stderr,
        mock_stdout,
        mock_stdin,
        mock_exit,
        mock_getpid,
        mock_dup2,
        mock_umask,
        mock_chdir,
        mock_setsid,
        mock_fork,
    ):
        """Test detach_process completes double fork process successfully."""
        # Arrange
        mock_fork.side_effect = [0, 0]  # Child process in both forks
        mock_getpid.return_value = 9999

        # Mock sys file descriptors
        mock_stdin.fileno.return_value = 0
        mock_stdout.fileno.return_value = 1
        mock_stderr.fileno.return_value = 2

        # Create mock file objects that support context manager protocol
        mock_devnull_r = MagicMock()
        mock_devnull_r.__enter__.return_value = mock_devnull_r
        mock_devnull_r.__exit__.return_value = None
        mock_devnull_r.fileno.return_value = 10

        mock_devnull_w = MagicMock()
        mock_devnull_w.__enter__.return_value = mock_devnull_w
        mock_devnull_w.__exit__.return_value = None
        mock_devnull_w.fileno.return_value = 11

        with patch("calendarbot.utils.daemon.Path") as mock_path:
            mock_path.return_value.open.side_effect = [mock_devnull_r, mock_devnull_w]

            # Act
            detach_process()

            # Assert
            assert mock_fork.call_count == 2
            mock_setsid.assert_called_once()
            mock_chdir.assert_called_once_with("/")
            mock_umask.assert_called_once_with(0)
            assert mock_dup2.call_count == 3  # stdin, stdout, stderr

    @patch("calendarbot.utils.daemon.os.fork")
    @patch("calendarbot.utils.daemon.os.dup2")
    @patch("calendarbot.utils.daemon.sys.exit")
    @patch("calendarbot.utils.daemon.sys.stdin")
    @patch("calendarbot.utils.daemon.sys.stdout")
    @patch("calendarbot.utils.daemon.sys.stderr")
    @patch("calendarbot.utils.daemon.Path")
    def test_detach_process_when_parent_in_first_fork_then_exits(
        self, mock_path, mock_stderr, mock_stdout, mock_stdin, mock_exit, mock_dup2, mock_fork
    ):
        """Test detach_process exits parent process in first fork."""
        # Arrange
        mock_fork.return_value = 1234  # Parent process in first fork
        mock_stdin.fileno.return_value = 0
        mock_stdout.fileno.return_value = 1
        mock_stderr.fileno.return_value = 2
        # Make sys.exit() raise SystemExit to stop execution like real sys.exit()
        mock_exit.side_effect = SystemExit(0)

        # Act & Assert
        with pytest.raises(SystemExit):
            detach_process()

        mock_exit.assert_called_once_with(0)
        assert mock_fork.call_count == 1  # Should only call fork once before exiting

    @patch("calendarbot.utils.daemon.os.fork")
    @patch("calendarbot.utils.daemon.os.setsid")
    @patch("calendarbot.utils.daemon.os.dup2")
    @patch("calendarbot.utils.daemon.sys.exit")
    @patch("calendarbot.utils.daemon.sys.stdin")
    @patch("calendarbot.utils.daemon.sys.stdout")
    @patch("calendarbot.utils.daemon.sys.stderr")
    @patch("calendarbot.utils.daemon.Path")
    def test_detach_process_when_parent_in_second_fork_then_exits(
        self,
        mock_path,
        mock_stderr,
        mock_stdout,
        mock_stdin,
        mock_exit,
        mock_dup2,
        mock_setsid,
        mock_fork,
    ):
        """Test detach_process exits parent process in second fork."""
        # Arrange
        mock_fork.side_effect = [0, 5678]  # Child in first, parent in second fork
        mock_stdin.fileno.return_value = 0
        mock_stdout.fileno.return_value = 1
        mock_stderr.fileno.return_value = 2

        # Act
        detach_process()

        # Assert
        assert mock_exit.call_count == 1
        mock_exit.assert_called_with(0)

    @patch("calendarbot.utils.daemon.os.fork")
    def test_detach_process_when_first_fork_fails_then_raises_daemon_error(self, mock_fork):
        """Test detach_process raises DaemonError when first fork fails."""
        # Arrange
        mock_fork.side_effect = OSError("Fork failed")

        # Act & Assert
        with pytest.raises(DaemonError) as exc_info:
            detach_process()

        assert "First fork failed" in str(exc_info.value)

    @patch("calendarbot.utils.daemon.os.fork")
    @patch("calendarbot.utils.daemon.os.setsid")
    def test_detach_process_when_setsid_fails_then_raises_daemon_error(
        self, mock_setsid, mock_fork
    ):
        """Test detach_process raises DaemonError when setsid fails."""
        # Arrange
        mock_fork.return_value = 0  # Child process
        mock_setsid.side_effect = OSError("Setsid failed")

        # Act & Assert
        with pytest.raises(DaemonError) as exc_info:
            detach_process()

        assert "Failed to become session leader" in str(exc_info.value)

    @patch("calendarbot.utils.daemon.os.fork")
    @patch("calendarbot.utils.daemon.os.setsid")
    def test_detach_process_when_second_fork_fails_then_raises_daemon_error(
        self, mock_setsid, mock_fork
    ):
        """Test detach_process raises DaemonError when second fork fails."""
        # Arrange
        mock_fork.side_effect = [0, OSError("Second fork failed")]

        # Act & Assert
        with pytest.raises(DaemonError) as exc_info:
            detach_process()

        assert "Second fork failed" in str(exc_info.value)


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    @patch("calendarbot.utils.daemon.DaemonManager.get_default_pid_file_path")
    def test_get_pid_file_path_when_called_then_returns_default_path(self, mock_get_default):
        """Test get_pid_file_path returns default PID file path."""
        # Arrange
        expected_path = Path("/mock/home/.calendarbot/daemon.pid")
        mock_get_default.return_value = expected_path

        # Act
        path = get_pid_file_path()

        # Assert
        assert path == expected_path
        mock_get_default.assert_called_once()

    @patch("calendarbot.utils.daemon.DaemonManager")
    def test_is_daemon_running_when_called_then_uses_daemon_manager(self, mock_manager_class):
        """Test is_daemon_running creates DaemonManager and checks if running."""
        # Arrange
        mock_manager = Mock()
        mock_manager.is_daemon_running.return_value = True
        mock_manager_class.return_value = mock_manager

        # Act
        result = is_daemon_running()

        # Assert
        assert result is True
        mock_manager_class.assert_called_once()
        mock_manager.is_daemon_running.assert_called_once()

    @patch("calendarbot.utils.daemon.DaemonController")
    def test_get_daemon_status_when_called_then_uses_daemon_controller(self, mock_controller_class):
        """Test get_daemon_status creates DaemonController and gets status."""
        # Arrange
        mock_status = Mock()
        mock_controller = Mock()
        mock_controller.get_daemon_status.return_value = mock_status
        mock_controller_class.return_value = mock_controller

        # Act
        result = get_daemon_status()

        # Assert
        assert result == mock_status
        mock_controller_class.assert_called_once()
        mock_controller.get_daemon_status.assert_called_once()

    @patch("calendarbot.utils.daemon.DaemonController")
    def test_start_daemon_when_called_then_uses_daemon_controller(self, mock_controller_class):
        """Test start_daemon creates DaemonController and starts daemon."""
        # Arrange
        mock_controller = Mock()
        mock_controller.start_daemon.return_value = 1234
        mock_controller_class.return_value = mock_controller

        command_args = ["--web", "--config", "/path/to/config"]

        # Act
        pid = start_daemon(command_args, port=9000)

        # Assert
        assert pid == 1234
        mock_controller_class.assert_called_once()
        mock_controller.start_daemon.assert_called_once_with(command_args, 9000)

    @patch("calendarbot.utils.daemon.DaemonController")
    def test_stop_daemon_when_called_then_uses_daemon_controller(self, mock_controller_class):
        """Test stop_daemon creates DaemonController and stops daemon."""
        # Arrange
        mock_controller = Mock()
        mock_controller.stop_daemon.return_value = True
        mock_controller_class.return_value = mock_controller

        # Act
        result = stop_daemon(timeout=60)

        # Assert
        assert result is True
        mock_controller_class.assert_called_once()
        mock_controller.stop_daemon.assert_called_once_with(60)  # Called with positional arg

    @patch("calendarbot.utils.daemon.DaemonManager")
    def test_cleanup_daemon_when_called_then_uses_daemon_manager(self, mock_manager_class):
        """Test cleanup_daemon creates DaemonManager and cleans up PID file."""
        # Arrange
        mock_manager = Mock()
        mock_manager.cleanup_pid_file.return_value = True
        mock_manager_class.return_value = mock_manager

        # Act
        result = cleanup_daemon()

        # Assert
        assert result is True
        mock_manager_class.assert_called_once()
        mock_manager.cleanup_pid_file.assert_called_once()
