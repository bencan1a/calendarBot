"""Unit tests for kiosk mode CLI functionality.

This module tests the CLI integration for kiosk mode operations,
including argument parsing, configuration, status reporting, and
command execution with proper mocking of kiosk components.
"""

from argparse import Namespace
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from calendarbot.cli.modes.kiosk import (
    KioskCLIError,
    _check_kiosk_status,
    _configure_kiosk_settings,
    _format_kiosk_status,
    _restart_kiosk_process,
    _run_kiosk_setup_wizard,
    _setup_kiosk_logging,
    _start_kiosk_process,
    _stop_kiosk_process,
    run_kiosk_mode,
)
from calendarbot.kiosk.browser_manager import BrowserState, BrowserStatus
from calendarbot.kiosk.manager import KioskStatus
from calendarbot.settings.kiosk_models import KioskSettings


@pytest.fixture
def mock_args():
    """Create mock command line arguments for testing."""
    args = Namespace()
    args.port = 8080
    args.display_type = "whats-next-view"
    args.kiosk_memory_limit = 80
    args.kiosk_startup_timeout = 30
    args.kiosk_health_interval = 60
    args.kiosk_max_restarts = 3
    args.kiosk_enable_gpu = False
    args.kiosk_disable_extensions = True
    args.kiosk_disable_plugins = True
    args.kiosk_width = 480
    args.kiosk_height = 800
    args.kiosk_orientation = "portrait"
    args.kiosk_scale = 1.0
    args.kiosk_fullscreen = True
    args.kiosk_hide_cursor = True
    args.kiosk_prevent_zoom = True
    args.kiosk_auto_start = False
    args.kiosk_startup_delay = 5.0
    args.no_log_colors = False
    return args


@pytest.fixture
def mock_settings():
    """Create mock settings object for testing."""
    settings = MagicMock()
    settings.web_port = 8080
    return settings


@pytest.fixture
def mock_kiosk_status():
    """Create mock kiosk status for testing."""
    browser_status = BrowserStatus(
        state=BrowserState.RUNNING,
        pid=1234,
        start_time=datetime.now() - timedelta(minutes=30),
        uptime=timedelta(minutes=30),
        memory_usage_mb=64,
        cpu_usage_percent=5.2,
        crash_count=0,
        restart_count=0,
        last_restart_time=None,
        is_responsive=True,
        last_health_check=datetime.now(),
        last_error=None,
        error_time=None,
    )

    return KioskStatus(
        is_running=True,
        start_time=datetime.now() - timedelta(minutes=30),
        uptime=timedelta(minutes=30),
        daemon_status=MagicMock(),
        browser_status=browser_status,
        memory_usage_mb=256,
        cpu_usage_percent=15.5,
        restart_count=0,
        last_error=None,
        error_time=None,
    )


class TestKioskCLIError:
    """Test KioskCLIError exception class."""

    def test_kiosk_cli_error_creation(self):
        """Test KioskCLIError can be created and raised properly."""
        error_msg = "Test error message"

        with pytest.raises(KioskCLIError) as exc_info:
            raise KioskCLIError(error_msg)

        assert str(exc_info.value) == error_msg

    def test_kiosk_cli_error_inheritance(self):
        """Test KioskCLIError inherits from Exception."""
        error = KioskCLIError("test")
        assert isinstance(error, Exception)


class TestConfigureKioskSettings:
    """Test _configure_kiosk_settings function."""

    @patch("calendarbot.cli.modes.kiosk.apply_command_line_overrides")
    @patch("calendarbot.cli.modes.kiosk.apply_cli_overrides")
    def test_configure_kiosk_settings_success(
        self, mock_cli_overrides, mock_cmd_overrides, mock_args, mock_settings
    ):
        """Test successful kiosk settings configuration."""
        mock_cmd_overrides.return_value = mock_settings
        mock_cli_overrides.return_value = mock_settings

        updated_settings, kiosk_settings = _configure_kiosk_settings(mock_args, mock_settings)

        assert updated_settings == mock_settings
        assert isinstance(kiosk_settings, KioskSettings)
        assert kiosk_settings.enabled is True
        assert kiosk_settings.target_layout == "whats-next-view"
        assert kiosk_settings.browser.memory_limit_mb == 80
        assert kiosk_settings.display.width == 480
        assert kiosk_settings.display.height == 800

        mock_cmd_overrides.assert_called_once_with(mock_settings, mock_args)
        mock_cli_overrides.assert_called_once()

    @patch("calendarbot.cli.modes.kiosk.apply_command_line_overrides")
    def test_configure_kiosk_settings_error(self, mock_cmd_overrides, mock_args, mock_settings):
        """Test error handling in kiosk settings configuration."""
        mock_cmd_overrides.side_effect = Exception("Configuration error")

        with pytest.raises(KioskCLIError) as exc_info:
            _configure_kiosk_settings(mock_args, mock_settings)

        assert "Failed to configure kiosk settings" in str(exc_info.value)


class TestSetupKioskLogging:
    """Test _setup_kiosk_logging function."""

    @patch("calendarbot.cli.modes.kiosk.setup_enhanced_logging")
    def test_setup_kiosk_logging_kiosk_mode(self, mock_setup_logging, mock_settings):
        """Test logging setup for kiosk mode."""
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_settings.logging = MagicMock()
        mock_settings.logging.console_level = None
        mock_settings.logging.file_enabled = False
        mock_settings.logging.file_directory = None

        result = _setup_kiosk_logging(mock_settings, kiosk_mode=True)

        assert result == mock_logger
        assert mock_settings.logging.console_level == "WARNING"
        assert mock_settings.logging.file_enabled is True
        assert mock_settings.logging.file_prefix == "kiosk"
        mock_logger.info.assert_called_once_with("Kiosk mode logging initialized")

    @patch("calendarbot.cli.modes.kiosk.setup_enhanced_logging")
    def test_setup_kiosk_logging_non_kiosk_mode(self, mock_setup_logging, mock_settings):
        """Test logging setup for non-kiosk mode."""
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger

        result = _setup_kiosk_logging(mock_settings, kiosk_mode=False)

        assert result == mock_logger
        mock_logger.info.assert_not_called()


class TestFormatKioskStatus:
    """Test _format_kiosk_status function."""

    def test_format_kiosk_status_plain_text(self, mock_kiosk_status):
        """Test status formatting with plain text output."""
        result = _format_kiosk_status(mock_kiosk_status, color_output=False)

        assert "Kiosk Status: Running" in result
        assert "Browser State: running" in result  # BrowserState enum values are lowercase
        assert "System Memory: 256MB" in result
        assert "System CPU: 15.5%" in result
        assert "Browser PID: 1234" in result
        assert "Browser Memory: 64MB" in result
        assert "Browser CPU: 5.2%" in result
        assert "Restart Count: 0" in result

    def test_format_kiosk_status_with_color(self, mock_kiosk_status):
        """Test status formatting with color output."""
        result = _format_kiosk_status(mock_kiosk_status, color_output=True)

        assert "CalendarBot Kiosk Status" in result
        assert "●" in result  # Status indicator
        assert "\033[" in result  # ANSI color codes
        assert "Running" in result
        assert "running" in result  # BrowserState enum values are lowercase

    def test_format_kiosk_status_with_error(self, mock_kiosk_status):
        """Test status formatting when there's an error."""
        mock_kiosk_status.last_error = "Test error message"
        mock_kiosk_status.error_time = datetime.now()

        result = _format_kiosk_status(mock_kiosk_status, color_output=False)

        assert "Last Error: Test error message" in result
        assert "Error Time:" in result

    def test_format_kiosk_status_stopped(self, mock_kiosk_status):
        """Test status formatting when kiosk is stopped."""
        mock_kiosk_status.is_running = False
        mock_kiosk_status.browser_status = None
        mock_kiosk_status.daemon_status = None

        result = _format_kiosk_status(mock_kiosk_status, color_output=False)

        assert "Kiosk Status: Stopped" in result
        assert "Browser State: N/A" in result


class TestStartKioskProcess:
    """Test _start_kiosk_process function."""

    @patch("calendarbot.cli.modes.kiosk._configure_kiosk_settings")
    @patch("calendarbot.cli.modes.kiosk._setup_kiosk_logging")
    @patch("calendarbot.cli.modes.kiosk.KioskManager")
    @patch("calendarbot.cli.modes.kiosk._format_kiosk_status")
    async def test_start_kiosk_process_success(
        self,
        mock_format_status,
        mock_kiosk_manager_class,
        mock_setup_logging,
        mock_configure_settings,
        mock_args,
        mock_settings,
        mock_kiosk_status,
    ):
        """Test successful kiosk process start."""
        mock_kiosk_settings = MagicMock()
        mock_configure_settings.return_value = (mock_settings, mock_kiosk_settings)
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_kiosk_manager = MagicMock()
        mock_kiosk_manager_class.return_value = mock_kiosk_manager
        mock_kiosk_manager.get_kiosk_status.return_value = mock_kiosk_status
        mock_kiosk_status.is_running = False  # Not already running
        mock_kiosk_manager.start_kiosk = AsyncMock(return_value=True)
        mock_format_status.return_value = "Status output"

        result = await _start_kiosk_process(mock_args)

        assert result == 0
        mock_configure_settings.assert_called_once()
        mock_setup_logging.assert_called_once()
        mock_kiosk_manager.start_kiosk.assert_called_once()
        mock_logger.info.assert_called()

    @patch("calendarbot.cli.modes.kiosk._configure_kiosk_settings")
    @patch("calendarbot.cli.modes.kiosk._setup_kiosk_logging")
    @patch("calendarbot.cli.modes.kiosk.KioskManager")
    async def test_start_kiosk_process_already_running(
        self,
        mock_kiosk_manager_class,
        mock_setup_logging,
        mock_configure_settings,
        mock_args,
        mock_settings,
        mock_kiosk_status,
    ):
        """Test kiosk process start when already running."""
        mock_kiosk_settings = MagicMock()
        mock_configure_settings.return_value = (mock_settings, mock_kiosk_settings)
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_kiosk_manager = MagicMock()
        mock_kiosk_manager_class.return_value = mock_kiosk_manager
        mock_kiosk_manager.get_kiosk_status.return_value = mock_kiosk_status
        mock_kiosk_status.is_running = True  # Already running

        result = await _start_kiosk_process(mock_args)

        assert result == 1
        mock_kiosk_manager.start_kiosk.assert_not_called()

    @patch("calendarbot.cli.modes.kiosk._configure_kiosk_settings")
    async def test_start_kiosk_process_configuration_error(
        self, mock_configure_settings, mock_args
    ):
        """Test kiosk process start with configuration error."""
        mock_configure_settings.side_effect = KioskCLIError("Config error")

        result = await _start_kiosk_process(mock_args)

        assert result == 1


class TestCheckKioskStatus:
    """Test _check_kiosk_status function."""

    @patch("calendarbot.cli.modes.kiosk._configure_kiosk_settings")
    @patch("calendarbot.cli.modes.kiosk.KioskManager")
    @patch("calendarbot.cli.modes.kiosk._format_kiosk_status")
    def test_check_kiosk_status_running(
        self,
        mock_format_status,
        mock_kiosk_manager_class,
        mock_configure_settings,
        mock_args,
        mock_settings,
        mock_kiosk_status,
    ):
        """Test checking kiosk status when running."""
        mock_kiosk_settings = MagicMock()
        mock_configure_settings.return_value = (mock_settings, mock_kiosk_settings)
        mock_kiosk_manager = MagicMock()
        mock_kiosk_manager_class.return_value = mock_kiosk_manager
        mock_kiosk_manager.get_kiosk_status.return_value = mock_kiosk_status
        mock_kiosk_status.is_running = True
        mock_format_status.return_value = "Status output"

        result = _check_kiosk_status(mock_args)

        assert result == 0
        mock_format_status.assert_called_once_with(mock_kiosk_status, color_output=True)

    @patch("calendarbot.cli.modes.kiosk._configure_kiosk_settings")
    @patch("calendarbot.cli.modes.kiosk.KioskManager")
    def test_check_kiosk_status_not_running(
        self,
        mock_kiosk_manager_class,
        mock_configure_settings,
        mock_args,
        mock_settings,
        mock_kiosk_status,
    ):
        """Test checking kiosk status when not running."""
        mock_kiosk_settings = MagicMock()
        mock_configure_settings.return_value = (mock_settings, mock_kiosk_settings)
        mock_kiosk_manager = MagicMock()
        mock_kiosk_manager_class.return_value = mock_kiosk_manager
        mock_kiosk_manager.get_kiosk_status.return_value = mock_kiosk_status
        mock_kiosk_status.is_running = False

        result = _check_kiosk_status(mock_args)

        assert result == 1


class TestStopKioskProcess:
    """Test _stop_kiosk_process function."""

    @patch("calendarbot.cli.modes.kiosk._configure_kiosk_settings")
    @patch("calendarbot.cli.modes.kiosk._setup_kiosk_logging")
    @patch("calendarbot.cli.modes.kiosk.KioskManager")
    async def test_stop_kiosk_process_success(
        self,
        mock_kiosk_manager_class,
        mock_setup_logging,
        mock_configure_settings,
        mock_args,
        mock_settings,
        mock_kiosk_status,
    ):
        """Test successful kiosk process stop."""
        mock_kiosk_settings = MagicMock()
        mock_configure_settings.return_value = (mock_settings, mock_kiosk_settings)
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_kiosk_manager = MagicMock()
        mock_kiosk_manager_class.return_value = mock_kiosk_manager
        mock_kiosk_manager.get_kiosk_status.return_value = mock_kiosk_status
        mock_kiosk_status.is_running = True
        mock_kiosk_manager.stop_kiosk = AsyncMock(return_value=True)

        result = await _stop_kiosk_process(mock_args)

        assert result == 0
        mock_kiosk_manager.stop_kiosk.assert_called_once()
        mock_logger.info.assert_called()

    @patch("calendarbot.cli.modes.kiosk._configure_kiosk_settings")
    @patch("calendarbot.cli.modes.kiosk._setup_kiosk_logging")
    @patch("calendarbot.cli.modes.kiosk.KioskManager")
    async def test_stop_kiosk_process_not_running(
        self,
        mock_kiosk_manager_class,
        mock_setup_logging,
        mock_configure_settings,
        mock_args,
        mock_settings,
        mock_kiosk_status,
    ):
        """Test kiosk process stop when not running."""
        mock_kiosk_settings = MagicMock()
        mock_configure_settings.return_value = (mock_settings, mock_kiosk_settings)
        mock_logger = MagicMock()
        mock_setup_logging.return_value = mock_logger
        mock_kiosk_manager = MagicMock()
        mock_kiosk_manager_class.return_value = mock_kiosk_manager
        mock_kiosk_manager.get_kiosk_status.return_value = mock_kiosk_status
        mock_kiosk_status.is_running = False

        result = await _stop_kiosk_process(mock_args)

        assert result == 1
        mock_kiosk_manager.stop_kiosk.assert_not_called()


class TestRestartKioskProcess:
    """Test _restart_kiosk_process function."""

    @patch("calendarbot.cli.modes.kiosk._stop_kiosk_process")
    @patch("calendarbot.cli.modes.kiosk._start_kiosk_process")
    @patch("calendarbot.cli.modes.kiosk.asyncio.sleep")
    async def test_restart_kiosk_process_success(
        self, mock_sleep, mock_start, mock_stop, mock_args
    ):
        """Test successful kiosk process restart."""
        mock_stop.return_value = 0
        mock_start.return_value = 0
        mock_sleep.return_value = None

        result = await _restart_kiosk_process(mock_args)

        assert result == 0
        mock_stop.assert_called_once_with(mock_args)
        mock_sleep.assert_called_once_with(2)
        mock_start.assert_called_once_with(mock_args)

    @patch("calendarbot.cli.modes.kiosk._stop_kiosk_process")
    @patch("calendarbot.cli.modes.kiosk._start_kiosk_process")
    @patch("calendarbot.cli.modes.kiosk.asyncio.sleep")
    async def test_restart_kiosk_process_start_failure(
        self, mock_sleep, mock_start, mock_stop, mock_args
    ):
        """Test kiosk process restart with start failure."""
        mock_stop.return_value = 0
        mock_start.return_value = 1  # Start failure
        mock_sleep.return_value = None

        result = await _restart_kiosk_process(mock_args)

        assert result == 1


class TestRunKioskSetupWizard:
    """Test _run_kiosk_setup_wizard function."""

    @patch("calendarbot.cli.modes.kiosk._start_kiosk_process")
    @patch("builtins.input")
    @patch("pathlib.Path.open", new_callable=mock_open)
    async def test_run_kiosk_setup_wizard_success(
        self, mock_file, mock_input, mock_start, mock_args
    ):
        """Test successful kiosk setup wizard."""
        # Mock user inputs
        mock_input.side_effect = [
            "480",  # width
            "800",  # height
            "portrait",  # orientation
            "80",  # memory limit
            "n",  # GPU acceleration
            "whats-next-view",  # layout
            "8080",  # port
            "y",  # auto-start
            "y",  # confirm
        ]
        mock_start.return_value = 0

        result = await _run_kiosk_setup_wizard(mock_args)

        assert result == 0
        mock_start.assert_called_once()
        # Verify file was written
        mock_file.assert_called()

    @patch("builtins.input")
    async def test_run_kiosk_setup_wizard_cancelled(self, mock_input, mock_args):
        """Test kiosk setup wizard cancellation."""
        # Mock user inputs ending with cancellation
        mock_input.side_effect = [
            "480",
            "800",
            "portrait",
            "80",
            "n",
            "whats-next-view",
            "8080",
            "y",
            "n",  # Confirm = no
        ]

        result = await _run_kiosk_setup_wizard(mock_args)

        assert result == 1

    @patch("builtins.input")
    async def test_run_kiosk_setup_wizard_keyboard_interrupt(self, mock_input, mock_args):
        """Test kiosk setup wizard with keyboard interrupt."""
        mock_input.side_effect = KeyboardInterrupt()

        result = await _run_kiosk_setup_wizard(mock_args)

        assert result == 1


class TestRunKioskMode:
    """Test run_kiosk_mode main entry point function."""

    @patch("calendarbot.cli.modes.kiosk._run_kiosk_setup_wizard")
    async def test_run_kiosk_mode_setup(self, mock_setup_wizard, mock_args):
        """Test run_kiosk_mode with setup operation."""
        mock_args.kiosk_setup = True
        mock_args.kiosk = False
        mock_args.kiosk_status = False
        mock_args.kiosk_stop = False
        mock_args.kiosk_restart = False
        mock_setup_wizard.return_value = 0

        result = await run_kiosk_mode(mock_args)

        assert result == 0
        mock_setup_wizard.assert_called_once_with(mock_args)

    @patch("calendarbot.cli.modes.kiosk._start_kiosk_process")
    async def test_run_kiosk_mode_start(self, mock_start, mock_args):
        """Test run_kiosk_mode with start operation."""
        mock_args.kiosk_setup = False
        mock_args.kiosk = True
        mock_args.kiosk_status = False
        mock_args.kiosk_stop = False
        mock_args.kiosk_restart = False
        mock_start.return_value = 0

        result = await run_kiosk_mode(mock_args)

        assert result == 0
        mock_start.assert_called_once_with(mock_args)

    @patch("calendarbot.cli.modes.kiosk._check_kiosk_status")
    async def test_run_kiosk_mode_status(self, mock_status, mock_args):
        """Test run_kiosk_mode with status operation."""
        mock_args.kiosk_setup = False
        mock_args.kiosk = False
        mock_args.kiosk_status = True
        mock_args.kiosk_stop = False
        mock_args.kiosk_restart = False
        mock_status.return_value = 0

        result = await run_kiosk_mode(mock_args)

        assert result == 0
        mock_status.assert_called_once_with(mock_args)

    @patch("calendarbot.cli.modes.kiosk._stop_kiosk_process")
    async def test_run_kiosk_mode_stop(self, mock_stop, mock_args):
        """Test run_kiosk_mode with stop operation."""
        mock_args.kiosk_setup = False
        mock_args.kiosk = False
        mock_args.kiosk_status = False
        mock_args.kiosk_stop = True
        mock_args.kiosk_restart = False
        mock_stop.return_value = 0

        result = await run_kiosk_mode(mock_args)

        assert result == 0
        mock_stop.assert_called_once_with(mock_args)

    @patch("calendarbot.cli.modes.kiosk._restart_kiosk_process")
    async def test_run_kiosk_mode_restart(self, mock_restart, mock_args):
        """Test run_kiosk_mode with restart operation."""
        mock_args.kiosk_setup = False
        mock_args.kiosk = False
        mock_args.kiosk_status = False
        mock_args.kiosk_stop = False
        mock_args.kiosk_restart = True
        mock_restart.return_value = 0

        result = await run_kiosk_mode(mock_args)

        assert result == 0
        mock_restart.assert_called_once_with(mock_args)

    async def test_run_kiosk_mode_no_operation(self, mock_args):
        """Test run_kiosk_mode with no valid operation specified."""
        mock_args.kiosk_setup = False
        mock_args.kiosk = False
        mock_args.kiosk_status = False
        mock_args.kiosk_stop = False
        mock_args.kiosk_restart = False

        result = await run_kiosk_mode(mock_args)

        assert result == 1

    async def test_run_kiosk_mode_missing_attributes(self):
        """Test run_kiosk_mode with missing attributes in args."""
        args = Namespace()  # Empty namespace

        result = await run_kiosk_mode(args)

        assert result == 1


class TestIntegration:
    """Integration tests for kiosk CLI functionality."""

    @patch("calendarbot.cli.modes.kiosk.settings")
    @patch("calendarbot.cli.modes.kiosk.KioskManager")
    async def test_full_kiosk_lifecycle(
        self, mock_kiosk_manager_class, mock_settings, mock_args, mock_kiosk_status
    ):
        """Test complete kiosk lifecycle: start -> status -> stop."""
        # Setup mocks
        mock_kiosk_manager = MagicMock()
        mock_kiosk_manager_class.return_value = mock_kiosk_manager

        # Create proper status mocks with real values
        not_running_status = KioskStatus(
            is_running=False,
            start_time=None,
            uptime=None,
            daemon_status=None,
            browser_status=None,
            memory_usage_mb=128,
            cpu_usage_percent=5.0,
            restart_count=0,
            last_error=None,
            error_time=None,
        )

        running_status = KioskStatus(
            is_running=True,
            start_time=datetime.now(),
            uptime=timedelta(minutes=5),
            daemon_status=MagicMock(),
            browser_status=BrowserStatus(
                state=BrowserState.RUNNING,
                pid=1234,
                start_time=datetime.now(),
                uptime=timedelta(minutes=5),
                memory_usage_mb=64,
                cpu_usage_percent=3.2,
                crash_count=0,
                restart_count=0,
                last_restart_time=None,
                is_responsive=True,
                last_health_check=datetime.now(),
                last_error=None,
                error_time=None,
            ),
            memory_usage_mb=256,
            cpu_usage_percent=8.5,
            restart_count=0,
            last_error=None,
            error_time=None,
        )

        mock_kiosk_manager.get_kiosk_status.return_value = not_running_status
        mock_kiosk_manager.start_kiosk = AsyncMock(return_value=True)
        mock_kiosk_manager.stop_kiosk = AsyncMock(return_value=True)

        with patch("calendarbot.cli.modes.kiosk._setup_kiosk_logging") as mock_logging:
            mock_logging.return_value = MagicMock()

            # Test start
            mock_args.kiosk = True
            mock_args.kiosk_status = False
            mock_args.kiosk_stop = False
            mock_args.kiosk_restart = False
            mock_args.kiosk_setup = False

            start_result = await run_kiosk_mode(mock_args)
            assert start_result == 0

            # Simulate kiosk now running
            mock_kiosk_manager.get_kiosk_status.return_value = running_status

            # Test status
            mock_args.kiosk = False
            mock_args.kiosk_status = True

            with patch("calendarbot.cli.modes.kiosk._format_kiosk_status") as mock_format:
                mock_format.return_value = "Status output"
                status_result = await run_kiosk_mode(mock_args)
                assert status_result == 0

            # Test stop
            mock_args.kiosk_status = False
            mock_args.kiosk_stop = True

            stop_result = await run_kiosk_mode(mock_args)
            assert stop_result == 0
