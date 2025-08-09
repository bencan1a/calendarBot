"""Unit tests for daemon mode handler."""

from unittest.mock import Mock, patch

import pytest

from calendarbot.cli.modes.daemon import (
    _check_daemon_status,
    _configure_daemon_settings,
    _setup_daemon_logging,
    _start_daemon_process,
    _stop_daemon_process,
    run_daemon_mode,
)
from calendarbot.utils.daemon import (
    DaemonAlreadyRunningError,
    DaemonError,
    DaemonNotRunningError,
)


class TestConfigureDaemonSettings:
    """Test daemon settings configuration."""

    def test_configure_daemon_settings_when_called_then_applies_overrides(self):
        """Test that daemon settings configuration applies all necessary overrides."""
        # Arrange
        mock_args = Mock(port=8080)
        mock_settings = Mock()
        mock_settings.logging = Mock()

        with (
            patch(
                "calendarbot.cli.modes.daemon.apply_command_line_overrides"
            ) as mock_cmd_overrides,
            patch("calendarbot.cli.modes.daemon.apply_cli_overrides") as mock_cli_overrides,
        ):
            mock_cmd_overrides.return_value = mock_settings
            mock_cli_overrides.return_value = mock_settings

            # Act
            result = _configure_daemon_settings(mock_args, mock_settings)

            # Assert
            mock_cmd_overrides.assert_called_once_with(mock_settings, mock_args)
            mock_cli_overrides.assert_called_once_with(mock_settings, mock_args)
            assert result.logging.console_enabled is False
            assert result.logging.file_enabled is True

    def test_configure_daemon_settings_when_no_log_file_then_creates_default_path(self):
        """Test that daemon settings creates default log file path when none exists."""
        # Arrange
        mock_args = Mock(port=8080)
        mock_settings = Mock()
        mock_settings.logging = Mock()
        mock_settings.logging.log_file = None

        with (
            patch(
                "calendarbot.cli.modes.daemon.apply_command_line_overrides"
            ) as mock_cmd_overrides,
            patch("calendarbot.cli.modes.daemon.apply_cli_overrides") as mock_cli_overrides,
        ):
            mock_cmd_overrides.return_value = mock_settings
            mock_cli_overrides.return_value = mock_settings

            # Act
            result = _configure_daemon_settings(mock_args, mock_settings)

            # Assert - just verify that logging configuration was applied
            assert result.logging.console_enabled is False
            assert result.logging.file_enabled is True
            # Log file path will be set (actual path testing not critical for unit test)
            assert result.logging.log_file is not None

    def test_configure_daemon_settings_when_no_logging_attr_then_handles_gracefully(self):
        """Test that daemon settings handles missing logging attribute gracefully."""
        # Arrange
        mock_args = Mock(port=8080)
        mock_settings = Mock(spec=[])  # No logging attribute

        with (
            patch(
                "calendarbot.cli.modes.daemon.apply_command_line_overrides"
            ) as mock_cmd_overrides,
            patch("calendarbot.cli.modes.daemon.apply_cli_overrides") as mock_cli_overrides,
        ):
            mock_cmd_overrides.return_value = mock_settings
            mock_cli_overrides.return_value = mock_settings

            # Act & Assert - Should not raise exception
            result = _configure_daemon_settings(mock_args, mock_settings)
            assert result is not None


class TestSetupDaemonLogging:
    """Test daemon logging setup."""

    def test_setup_daemon_logging_when_called_then_returns_logger(self):
        """Test that daemon logging setup returns configured logger."""
        # Arrange
        mock_settings = Mock()
        mock_logger = Mock()

        with patch("calendarbot.cli.modes.daemon.setup_enhanced_logging") as mock_setup:
            mock_setup.return_value = mock_logger

            # Act
            result = _setup_daemon_logging(mock_settings)

            # Assert
            mock_setup.assert_called_once_with(mock_settings, interactive_mode=False)
            mock_logger.info.assert_called_once_with("Daemon mode logging initialized")
            assert result == mock_logger


class TestStartDaemonProcess:
    """Test daemon process startup."""

    @pytest.mark.asyncio
    async def test_start_daemon_process_when_daemon_already_running_then_returns_error(self):
        """Test that starting daemon when already running returns error code."""
        # Arrange
        mock_args = Mock(port=8080)

        with (
            patch("calendarbot.cli.modes.daemon._configure_daemon_settings") as mock_config,
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("builtins.print") as mock_print,
        ):
            mock_controller = Mock()
            mock_controller.daemon_manager.is_daemon_running.return_value = True
            mock_controller.daemon_manager.get_daemon_pid.return_value = 1234
            mock_controller_class.return_value = mock_controller

            # Act
            result = await _start_daemon_process(mock_args)

            # Assert
            assert result == 1
            mock_print.assert_called()

    @pytest.mark.asyncio
    async def test_start_daemon_process_when_successful_then_runs_web_mode(self):
        """Test that successful daemon start runs web mode and returns exit code."""
        # Arrange
        mock_args = Mock(port=8080)

        with (
            patch("calendarbot.cli.modes.daemon._configure_daemon_settings") as mock_config,
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("calendarbot.cli.modes.daemon.detach_process") as mock_detach,
            patch("calendarbot.cli.modes.daemon._setup_daemon_logging") as mock_logging,
            patch("calendarbot.cli.modes.daemon.run_web_mode") as mock_web_mode,
            patch("builtins.print") as mock_print,
        ):
            mock_controller = Mock()
            mock_controller.daemon_manager.is_daemon_running.return_value = False
            mock_controller.daemon_manager.create_pid_file.return_value = 5678
            mock_controller_class.return_value = mock_controller

            mock_logger = Mock()
            mock_logging.return_value = mock_logger
            mock_web_mode.return_value = 0

            # Act
            result = await _start_daemon_process(mock_args)

            # Assert
            assert result == 0
            mock_detach.assert_called_once()
            mock_controller.daemon_manager.create_pid_file.assert_called_once()
            mock_controller._setup_signal_handlers.assert_called_once()
            mock_web_mode.assert_called_once_with(mock_args)
            mock_controller.daemon_manager.cleanup_pid_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_daemon_process_when_daemon_already_running_error_then_returns_error(self):
        """Test that DaemonAlreadyRunningError returns error code."""
        # Arrange
        mock_args = Mock(port=8080)

        with (
            patch("calendarbot.cli.modes.daemon._configure_daemon_settings") as mock_config,
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("builtins.print") as mock_print,
        ):
            mock_controller_class.side_effect = DaemonAlreadyRunningError("Already running")

            # Act
            result = await _start_daemon_process(mock_args)

            # Assert
            assert result == 1
            mock_print.assert_called()

    @pytest.mark.asyncio
    async def test_start_daemon_process_when_daemon_error_then_returns_error(self):
        """Test that DaemonError returns error code."""
        # Arrange
        mock_args = Mock(port=8080)

        with (
            patch("calendarbot.cli.modes.daemon._configure_daemon_settings") as mock_config,
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("builtins.print") as mock_print,
        ):
            mock_controller_class.side_effect = DaemonError("Startup failed")

            # Act
            result = await _start_daemon_process(mock_args)

            # Assert
            assert result == 1
            mock_print.assert_called()

    @pytest.mark.asyncio
    async def test_start_daemon_process_when_unexpected_error_then_returns_error(self):
        """Test that unexpected errors return error code."""
        # Arrange
        mock_args = Mock(port=8080)

        with (
            patch("calendarbot.cli.modes.daemon._configure_daemon_settings") as mock_config,
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("builtins.print") as mock_print,
        ):
            mock_controller_class.side_effect = Exception("Unexpected error")

            # Act
            result = await _start_daemon_process(mock_args)

            # Assert
            assert result == 1
            mock_print.assert_called()


class TestCheckDaemonStatus:
    """Test daemon status checking."""

    def test_check_daemon_status_when_daemon_running_then_displays_status(self):
        """Test that status check displays status when daemon is running."""
        # Arrange
        mock_status = Mock()
        mock_status.format_status.return_value = "Status info"

        with (
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("builtins.print") as mock_print,
        ):
            mock_controller = Mock()
            mock_controller.get_daemon_status.return_value = mock_status
            mock_controller_class.return_value = mock_controller

            # Act
            result = _check_daemon_status()

            # Assert
            assert result == 0
            mock_print.assert_called_with("Status info")

    def test_check_daemon_status_when_daemon_not_running_then_shows_not_running(self):
        """Test that status check shows not running when daemon is not running."""
        # Arrange
        with (
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("builtins.print") as mock_print,
        ):
            mock_controller = Mock()
            mock_controller.get_daemon_status.return_value = None
            mock_controller_class.return_value = mock_controller

            # Act
            result = _check_daemon_status()

            # Assert
            assert result == 1
            mock_print.assert_called_with("CalendarBot daemon is not running")

    def test_check_daemon_status_when_error_then_returns_error(self):
        """Test that status check returns error code on exception."""
        # Arrange
        with (
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("builtins.print") as mock_print,
        ):
            mock_controller_class.side_effect = Exception("Status error")

            # Act
            result = _check_daemon_status()

            # Assert
            assert result == 1
            mock_print.assert_called()


class TestStopDaemonProcess:
    """Test daemon process stopping."""

    def test_stop_daemon_process_when_daemon_not_running_then_shows_not_running(self):
        """Test that stopping daemon when not running shows appropriate message."""
        # Arrange
        with (
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("builtins.print") as mock_print,
        ):
            mock_controller = Mock()
            mock_controller.daemon_manager.is_daemon_running.return_value = False
            mock_controller_class.return_value = mock_controller

            # Act
            result = _stop_daemon_process()

            # Assert
            assert result == 1
            mock_print.assert_called_with("CalendarBot daemon is not running")

    def test_stop_daemon_process_when_successful_then_shows_success(self):
        """Test that successful daemon stop shows success message."""
        # Arrange
        with (
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("builtins.print") as mock_print,
        ):
            mock_controller = Mock()
            mock_controller.daemon_manager.is_daemon_running.return_value = True
            mock_controller.daemon_manager.get_daemon_pid.return_value = 1234
            mock_controller.stop_daemon.return_value = True
            mock_controller_class.return_value = mock_controller

            # Act
            result = _stop_daemon_process(timeout=30)

            # Assert
            assert result == 0
            mock_controller.stop_daemon.assert_called_once_with(timeout=30)
            mock_print.assert_any_call("Stopping CalendarBot daemon (PID 1234)...")
            mock_print.assert_any_call("CalendarBot daemon stopped successfully")

    def test_stop_daemon_process_when_stop_fails_then_shows_failure(self):
        """Test that failed daemon stop shows failure message."""
        # Arrange
        with (
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("builtins.print") as mock_print,
        ):
            mock_controller = Mock()
            mock_controller.daemon_manager.is_daemon_running.return_value = True
            mock_controller.daemon_manager.get_daemon_pid.return_value = 1234
            mock_controller.stop_daemon.return_value = False
            mock_controller_class.return_value = mock_controller

            # Act
            result = _stop_daemon_process()

            # Assert
            assert result == 1
            mock_print.assert_any_call("Failed to stop CalendarBot daemon")

    def test_stop_daemon_process_when_daemon_not_running_error_then_shows_not_running(self):
        """Test that DaemonNotRunningError shows not running message."""
        # Arrange
        with (
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("builtins.print") as mock_print,
        ):
            mock_controller = Mock()
            mock_controller.daemon_manager.is_daemon_running.side_effect = DaemonNotRunningError(
                "Not running"
            )
            mock_controller_class.return_value = mock_controller

            # Act
            result = _stop_daemon_process()

            # Assert
            assert result == 1
            mock_print.assert_called_with("CalendarBot daemon is not running")

    def test_stop_daemon_process_when_unexpected_error_then_returns_error(self):
        """Test that unexpected errors return error code."""
        # Arrange
        with (
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("builtins.print") as mock_print,
        ):
            mock_controller_class.side_effect = Exception("Stop error")

            # Act
            result = _stop_daemon_process()

            # Assert
            assert result == 1
            mock_print.assert_called()


class TestRunDaemonMode:
    """Test main daemon mode entry point."""

    @pytest.mark.asyncio
    async def test_run_daemon_mode_when_daemon_flag_then_starts_daemon(self):
        """Test that daemon flag triggers daemon start."""
        # Arrange
        mock_args = Mock()
        mock_args.daemon = True
        mock_args.daemon_status = False
        mock_args.daemon_stop = False

        with patch("calendarbot.cli.modes.daemon._start_daemon_process") as mock_start:
            mock_start.return_value = 0

            # Act
            result = await run_daemon_mode(mock_args)

            # Assert
            assert result == 0
            mock_start.assert_called_once_with(mock_args)

    @pytest.mark.asyncio
    async def test_run_daemon_mode_when_status_flag_then_checks_status(self):
        """Test that status flag triggers status check."""
        # Arrange
        mock_args = Mock()
        mock_args.daemon = False
        mock_args.daemon_status = True
        mock_args.daemon_stop = False

        with patch("calendarbot.cli.modes.daemon._check_daemon_status") as mock_status:
            mock_status.return_value = 0

            # Act
            result = await run_daemon_mode(mock_args)

            # Assert
            assert result == 0
            mock_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_daemon_mode_when_stop_flag_then_stops_daemon(self):
        """Test that stop flag triggers daemon stop."""
        # Arrange
        mock_args = Mock()
        mock_args.daemon = False
        mock_args.daemon_status = False
        mock_args.daemon_stop = True
        mock_args.daemon_timeout = 30

        with patch("calendarbot.cli.modes.daemon._stop_daemon_process") as mock_stop:
            mock_stop.return_value = 0

            # Act
            result = await run_daemon_mode(mock_args)

            # Assert
            assert result == 0
            mock_stop.assert_called_once_with(30)

    @pytest.mark.asyncio
    async def test_run_daemon_mode_when_stop_flag_no_timeout_then_uses_default(self):
        """Test that stop flag without timeout uses default."""
        # Arrange
        mock_args = Mock(spec=["daemon", "daemon_status", "daemon_stop"])
        mock_args.daemon = False
        mock_args.daemon_status = False
        mock_args.daemon_stop = True
        # No daemon_timeout attribute - using spec to prevent auto-creation

        with patch("calendarbot.cli.modes.daemon._stop_daemon_process") as mock_stop:
            mock_stop.return_value = 0

            # Act
            result = await run_daemon_mode(mock_args)

            # Assert
            assert result == 0
            mock_stop.assert_called_once_with(30)  # Default timeout

    @pytest.mark.asyncio
    async def test_run_daemon_mode_when_no_daemon_attrs_then_returns_error(self):
        """Test that missing daemon attributes returns error."""
        # Arrange
        mock_args = Mock(spec=[])  # No daemon attributes

        with patch("builtins.print") as mock_print:
            # Act
            result = await run_daemon_mode(mock_args)

            # Assert
            assert result == 1
            mock_print.assert_called_with("Error: No valid daemon operation specified")

    @pytest.mark.asyncio
    async def test_run_daemon_mode_when_no_flags_set_then_returns_error(self):
        """Test that no flags set returns error."""
        # Arrange
        mock_args = Mock()
        mock_args.daemon = False
        mock_args.daemon_status = False
        mock_args.daemon_stop = False

        with patch("builtins.print") as mock_print:
            # Act
            result = await run_daemon_mode(mock_args)

            # Assert
            assert result == 1
            mock_print.assert_called_with("Error: No valid daemon operation specified")
