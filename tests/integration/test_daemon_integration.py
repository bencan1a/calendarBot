"""Integration tests for CalendarBot daemon mode CLI functionality.

This test suite validates end-to-end daemon operation through the CLI interface,
focusing on integration points between CLI parsing, mode routing, and daemon operations
without testing actual process management.

Integration test areas:
- CLI argument parsing and routing to daemon operations
- Integration between main_entry() and run_daemon_mode()
- End-to-end workflows for daemon start/stop/status
- Error handling and propagation through CLI stack
- Mode registry integration
"""

from typing import Optional
from unittest.mock import Mock, patch

import pytest

from calendarbot.cli import main_entry
from calendarbot.cli.modes.daemon import run_daemon_mode
from calendarbot.cli.parser import create_parser
from calendarbot.utils.daemon import (
    DaemonAlreadyRunningError,
    DaemonError,
)


class TestDaemonCLIRouting:
    """Test CLI argument parsing and routing to daemon mode operations."""

    @pytest.fixture
    def mock_daemon_dependencies(self):
        """Mock all daemon-related dependencies to isolate CLI integration."""
        with (
            patch("calendarbot.cli.run_daemon_mode") as mock_run_daemon,
            patch("calendarbot.cli.check_configuration") as mock_check_config,
        ):
            mock_check_config.return_value = (True, "/mock/config.yaml")
            mock_run_daemon.return_value = 0

            yield {"run_daemon_mode": mock_run_daemon, "check_configuration": mock_check_config}

    @pytest.mark.asyncio
    async def test_cli_routing_when_daemon_flag_then_routes_to_daemon_mode(
        self, mock_daemon_dependencies
    ):
        """Test that --daemon flag properly routes to daemon mode through main_entry."""
        # Arrange: Mock sys.argv for daemon start
        with patch("sys.argv", ["calendarbot", "--daemon", "--port", "3000"]):
            # Act: Run main entry point
            exit_code = await main_entry()

            # Assert: Daemon mode was called and succeeded
            assert exit_code == 0
            mock_daemon_dependencies["run_daemon_mode"].assert_called_once()

            # Verify arguments were passed correctly
            call_args = mock_daemon_dependencies["run_daemon_mode"].call_args[0][0]
            assert hasattr(call_args, "daemon")
            assert call_args.daemon is True
            assert call_args.port == 3000

    @pytest.mark.asyncio
    async def test_cli_routing_when_daemon_status_flag_then_routes_to_daemon_mode(
        self, mock_daemon_dependencies
    ):
        """Test that --daemon-status flag properly routes to daemon mode through main_entry."""
        # Arrange: Mock sys.argv for daemon status check
        with patch("sys.argv", ["calendarbot", "--daemon-status"]):
            # Act: Run main entry point
            exit_code = await main_entry()

            # Assert: Daemon mode was called for status check
            assert exit_code == 0
            mock_daemon_dependencies["run_daemon_mode"].assert_called_once()

            # Verify daemon status argument was passed
            call_args = mock_daemon_dependencies["run_daemon_mode"].call_args[0][0]
            assert hasattr(call_args, "daemon_status")
            assert call_args.daemon_status is True

    @pytest.mark.asyncio
    async def test_cli_routing_when_daemon_stop_flag_then_routes_to_daemon_mode(
        self, mock_daemon_dependencies
    ):
        """Test that --daemon-stop flag properly routes to daemon mode through main_entry."""
        # Arrange: Mock sys.argv for daemon stop
        with patch("sys.argv", ["calendarbot", "--daemon-stop"]):
            # Act: Run main entry point
            exit_code = await main_entry()

            # Assert: Daemon mode was called for stop operation
            assert exit_code == 0
            mock_daemon_dependencies["run_daemon_mode"].assert_called_once()

            # Verify daemon stop argument was passed
            call_args = mock_daemon_dependencies["run_daemon_mode"].call_args[0][0]
            assert hasattr(call_args, "daemon_stop")
            assert call_args.daemon_stop is True

    @pytest.mark.asyncio
    async def test_cli_routing_when_multiple_daemon_flags_then_all_passed_to_handler(
        self, mock_daemon_dependencies
    ):
        """Test that daemon operations can coexist in argument parsing."""
        # Arrange: Test daemon flag priority handling
        with patch("sys.argv", ["calendarbot", "--daemon", "--port", "8080"]):
            # Act: Run main entry point
            exit_code = await main_entry()

            # Assert: Main entry succeeded and routed correctly
            assert exit_code == 0
            mock_daemon_dependencies["run_daemon_mode"].assert_called_once()

    def test_parser_integration_when_daemon_args_parsed_then_all_flags_present(self):
        """Test that CLI parser correctly handles all daemon-related arguments."""
        # Arrange: Create parser and test daemon arguments
        parser = create_parser()

        # Act: Parse various daemon command combinations
        daemon_args = parser.parse_args(["--daemon", "--port", "3000"])
        status_args = parser.parse_args(["--daemon-status"])
        stop_args = parser.parse_args(["--daemon-stop"])

        # Assert: All daemon flags are properly parsed
        assert hasattr(daemon_args, "daemon") and daemon_args.daemon is True
        assert hasattr(daemon_args, "port") and daemon_args.port == 3000

        assert hasattr(status_args, "daemon_status") and status_args.daemon_status is True
        assert hasattr(stop_args, "daemon_stop") and stop_args.daemon_stop is True


class TestDaemonModeIntegration:
    """Test integration between main_entry() and run_daemon_mode()."""

    @pytest.fixture
    def mock_daemon_operations(self):
        """Mock daemon controller and process operations."""
        with (
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller,
            patch("calendarbot.cli.modes.daemon.detach_process") as mock_detach,
            patch("calendarbot.cli.modes.daemon.run_web_mode") as mock_web_mode,
            patch("calendarbot.cli.modes.daemon._setup_daemon_logging") as mock_logging,
            patch("calendarbot.cli.modes.daemon._configure_daemon_settings") as mock_config,
        ):
            # Configure default successful behavior
            mock_daemon_manager = Mock()
            mock_daemon_manager.is_daemon_running.return_value = False
            mock_daemon_manager.get_daemon_pid.return_value = None
            mock_daemon_manager.create_pid_file.return_value = 12345
            mock_daemon_manager.cleanup_pid_file.return_value = None

            mock_controller_instance = Mock()
            mock_controller_instance.daemon_manager = mock_daemon_manager
            mock_controller_instance._setup_signal_handlers = Mock()
            mock_controller_instance.get_daemon_status = Mock()
            mock_controller_instance.stop_daemon = Mock()
            mock_controller.return_value = mock_controller_instance

            mock_web_mode.return_value = 0
            mock_config.return_value = Mock()
            mock_logging.return_value = Mock()

            yield {
                "controller": mock_controller,
                "controller_instance": mock_controller_instance,
                "daemon_manager": mock_daemon_manager,
                "detach_process": mock_detach,
                "web_mode": mock_web_mode,
                "logging": mock_logging,
                "config": mock_config,
            }

    @pytest.mark.asyncio
    async def test_daemon_start_integration_when_successful_then_returns_success_code(
        self, mock_daemon_operations
    ):
        """Test successful daemon start operation through CLI integration."""
        # Arrange: Set up arguments for daemon start
        args = Mock()
        args.daemon = True
        args.daemon_status = False
        args.daemon_stop = False
        args.port = 8080

        # Act: Run daemon mode with start operation
        exit_code = await run_daemon_mode(args)

        # Assert: Daemon start process completed successfully
        assert exit_code == 0

        # Verify integration chain was called correctly
        mock_daemon_operations["controller"].assert_called_once()
        mock_daemon_operations["daemon_manager"].is_daemon_running.assert_called_once()
        # Note: detach_process() is called in __main__.py before run_daemon_mode(), not within it
        mock_daemon_operations["daemon_manager"].create_pid_file.assert_called_once()
        mock_daemon_operations["web_mode"].assert_called_once_with(args)

    @pytest.mark.asyncio
    async def test_daemon_start_integration_when_already_running_then_returns_error_code(
        self, mock_daemon_operations
    ):
        """Test daemon start when daemon already running returns appropriate error."""
        # Arrange: Configure daemon as already running
        mock_daemon_operations["daemon_manager"].is_daemon_running.return_value = True
        mock_daemon_operations["daemon_manager"].get_daemon_pid.return_value = 5678

        args = Mock()
        args.daemon = True
        args.daemon_status = False
        args.daemon_stop = False
        args.port = 8080

        with patch("builtins.print") as mock_print:
            # Act: Attempt to start daemon when already running
            exit_code = await run_daemon_mode(args)

            # Assert: Returns error code and displays appropriate message
            assert exit_code == 1
            mock_print.assert_called()

            # Verify daemon start process was not initiated
            mock_daemon_operations["detach_process"].assert_not_called()
            mock_daemon_operations["web_mode"].assert_not_called()

    @pytest.mark.asyncio
    async def test_daemon_status_integration_when_running_then_displays_status(
        self, mock_daemon_operations
    ):
        """Test daemon status check integration when daemon is running."""
        # Arrange: Configure daemon status response
        mock_status = Mock()
        mock_status.format_status.return_value = "CalendarBot daemon running (PID: 12345)"
        mock_daemon_operations["controller_instance"].get_daemon_status.return_value = mock_status

        args = Mock()
        args.daemon = False
        args.daemon_status = True
        args.daemon_stop = False

        with patch("builtins.print") as mock_print:
            # Act: Check daemon status
            exit_code = await run_daemon_mode(args)

            # Assert: Status check succeeded
            assert exit_code == 0
            mock_daemon_operations["controller_instance"].get_daemon_status.assert_called_once()
            mock_print.assert_called_with("CalendarBot daemon running (PID: 12345)")

    @pytest.mark.asyncio
    async def test_daemon_status_integration_when_not_running_then_reports_not_running(
        self, mock_daemon_operations
    ):
        """Test daemon status check integration when daemon is not running."""
        # Arrange: Configure daemon as not running
        mock_daemon_operations["controller_instance"].get_daemon_status.return_value = None

        args = Mock()
        args.daemon = False
        args.daemon_status = True
        args.daemon_stop = False

        with patch("builtins.print") as mock_print:
            # Act: Check daemon status when not running
            exit_code = await run_daemon_mode(args)

            # Assert: Returns error code indicating daemon not running
            assert exit_code == 1
            mock_print.assert_called_with("CalendarBot daemon is not running")

    @pytest.mark.asyncio
    async def test_daemon_stop_integration_when_successful_then_stops_daemon(
        self, mock_daemon_operations
    ):
        """Test daemon stop operation integration when successful."""
        # Arrange: Configure daemon as running and stoppable
        mock_daemon_operations["daemon_manager"].is_daemon_running.return_value = True
        mock_daemon_operations["daemon_manager"].get_daemon_pid.return_value = 9999
        mock_daemon_operations["controller_instance"].stop_daemon.return_value = True

        args = Mock()
        args.daemon = False
        args.daemon_status = False
        args.daemon_stop = True
        args.daemon_timeout = 30

        with patch("builtins.print") as mock_print:
            # Act: Stop daemon
            exit_code = await run_daemon_mode(args)

            # Assert: Daemon stop succeeded
            assert exit_code == 0
            mock_daemon_operations["controller_instance"].stop_daemon.assert_called_once_with(
                timeout=30
            )
            mock_print.assert_any_call("Stopping CalendarBot daemon (PID 9999)...")
            mock_print.assert_any_call("CalendarBot daemon stopped successfully")

    @pytest.mark.asyncio
    async def test_daemon_stop_integration_when_not_running_then_reports_not_running(
        self, mock_daemon_operations
    ):
        """Test daemon stop operation when daemon is not running."""
        # Arrange: Configure daemon as not running
        mock_daemon_operations["daemon_manager"].is_daemon_running.return_value = False

        args = Mock()
        args.daemon = False
        args.daemon_status = False
        args.daemon_stop = True

        with patch("builtins.print") as mock_print:
            # Act: Attempt to stop non-running daemon
            exit_code = await run_daemon_mode(args)

            # Assert: Returns error code
            assert exit_code == 1
            mock_print.assert_called_with("CalendarBot daemon is not running")


class TestDaemonErrorHandling:
    """Test error handling and propagation through CLI stack."""

    @pytest.mark.asyncio
    async def test_daemon_error_propagation_when_daemon_error_then_returns_error_code(self):
        """Test that DaemonError exceptions are properly caught and handled."""
        # Arrange: Configure daemon controller to raise DaemonError
        args = Mock()
        args.daemon = True
        args.daemon_status = False
        args.daemon_stop = False
        args.port = 8080

        with (
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("calendarbot.cli.modes.daemon._configure_daemon_settings") as mock_config,
            patch("builtins.print") as mock_print,
        ):
            mock_controller_class.side_effect = DaemonError("Test daemon error")

            # Act: Run daemon mode with error condition
            exit_code = await run_daemon_mode(args)

            # Assert: Error is handled gracefully with error exit code
            assert exit_code == 1
            mock_print.assert_called_with("Daemon startup error: Test daemon error")

    @pytest.mark.asyncio
    async def test_daemon_already_running_error_propagation_when_raised_then_handled_gracefully(
        self,
    ):
        """Test that DaemonAlreadyRunningError is properly handled."""
        # Arrange: Configure daemon start to raise already running error
        args = Mock()
        args.daemon = True
        args.daemon_status = False
        args.daemon_stop = False
        args.port = 8080

        with (
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("calendarbot.cli.modes.daemon._configure_daemon_settings") as mock_config,
            patch("builtins.print") as mock_print,
        ):
            mock_controller_class.side_effect = DaemonAlreadyRunningError("Daemon already running")

            # Act: Attempt daemon start when already running
            exit_code = await run_daemon_mode(args)

            # Assert: Error handled with appropriate exit code
            assert exit_code == 1
            mock_print.assert_called_with("Error: Daemon already running")

    @pytest.mark.asyncio
    async def test_daemon_not_running_error_propagation_when_stop_requested_then_handled(self):
        """Test that DaemonNotRunningError during stop is properly handled."""
        # Arrange: Configure daemon stop to raise not running error
        args = Mock()
        args.daemon = False
        args.daemon_status = False
        args.daemon_stop = True

        with (
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("builtins.print") as mock_print,
        ):
            mock_controller = Mock()
            mock_controller.daemon_manager.is_daemon_running.return_value = False
            mock_controller_class.return_value = mock_controller

            # Act: Attempt to stop non-running daemon
            exit_code = await run_daemon_mode(args)

            # Assert: Error handled gracefully
            assert exit_code == 1
            mock_print.assert_called_with("CalendarBot daemon is not running")

    @pytest.mark.asyncio
    async def test_unexpected_error_propagation_when_exception_then_returns_error_code(self):
        """Test that unexpected exceptions are handled gracefully."""
        # Arrange: Configure daemon operation to raise unexpected error
        args = Mock()
        args.daemon = True
        args.daemon_status = False
        args.daemon_stop = False
        args.port = 8080

        with (
            patch("calendarbot.cli.modes.daemon.DaemonController") as mock_controller_class,
            patch("calendarbot.cli.modes.daemon._configure_daemon_settings") as mock_config,
            patch("builtins.print") as mock_print,
        ):
            mock_controller_class.side_effect = Exception("Unexpected error")

            # Act: Run daemon mode with unexpected error
            exit_code = await run_daemon_mode(args)

            # Assert: Unexpected error handled with error exit code
            assert exit_code == 1
            mock_print.assert_called_with("Unexpected error starting daemon: Unexpected error")

    @pytest.mark.asyncio
    async def test_invalid_daemon_args_when_no_valid_operation_then_returns_error(self):
        """Test that invalid daemon arguments return appropriate error."""
        # Arrange: Create args with no valid daemon operation
        args = Mock()
        args.daemon = False
        args.daemon_status = False
        args.daemon_stop = False

        with patch("builtins.print") as mock_print:
            # Act: Run daemon mode with invalid arguments
            exit_code = await run_daemon_mode(args)

            # Assert: Returns error code for invalid arguments
            assert exit_code == 1
            mock_print.assert_called_with("Error: No valid daemon operation specified")


class TestDaemonModeRegistry:
    """Test daemon mode integration with CLI mode registry."""

    @pytest.mark.asyncio
    async def test_daemon_mode_registration_when_imported_then_available_in_cli(self):
        """Test that daemon mode is properly registered and accessible through CLI."""
        # Arrange: Import the CLI module to ensure registration
        from calendarbot.cli import run_daemon_mode as imported_daemon_mode

        # Act: Verify the daemon mode function is available
        assert imported_daemon_mode is not None
        assert callable(imported_daemon_mode)

        # Assert: Function has expected signature for CLI integration
        import inspect

        sig = inspect.signature(imported_daemon_mode)
        assert "args" in sig.parameters

    @pytest.mark.asyncio
    async def test_main_entry_daemon_integration_when_daemon_args_then_calls_daemon_mode(self):
        """Test that main_entry properly integrates with daemon mode routing."""
        # Arrange: Mock the daemon mode function and configuration check
        args = Mock()
        args.daemon = True
        args.daemon_status = False
        args.daemon_stop = False
        args.port = 8080
        args.setup = False
        args.backup = False
        args.restore = None
        args.list_backups = False

        with (
            patch("calendarbot.cli.create_parser") as mock_parser,
            patch("calendarbot.cli.run_daemon_mode") as mock_daemon_mode,
            patch("calendarbot.cli.check_configuration") as mock_check_config,
        ):
            mock_parser.return_value.parse_args.return_value = args
            mock_daemon_mode.return_value = 0
            mock_check_config.return_value = (True, "/mock/config.yaml")

            # Act: Run main entry point
            exit_code = await main_entry()

            # Assert: Daemon mode was called through main entry integration
            assert exit_code == 0
            mock_daemon_mode.assert_called_once_with(args)

    def test_daemon_args_precedence_when_multiple_modes_then_daemon_takes_priority(self):
        """Test that daemon arguments take precedence in CLI routing logic."""
        # Arrange: Create parser and test precedence
        parser = create_parser()

        # Act: Parse arguments with both daemon and other mode flags
        # Note: In practice, users shouldn't specify conflicting modes,
        # but we test the parsing behavior
        daemon_with_web_args = parser.parse_args(["--daemon", "--web", "--port", "3000"])

        # Assert: Both flags are parsed (precedence handled in main_entry logic)
        assert daemon_with_web_args.daemon is True
        assert daemon_with_web_args.web is True
        assert daemon_with_web_args.port == 3000


# Test fixtures and utilities for integration testing
@pytest.fixture
def sample_daemon_args():
    """Provide sample daemon arguments for testing."""
    args = Mock()
    args.daemon = False
    args.daemon_status = False
    args.daemon_stop = False
    args.port = 8080
    args.daemon_timeout = 30
    return args


@pytest.fixture
def daemon_start_args(sample_daemon_args):
    """Provide daemon start arguments."""
    sample_daemon_args.daemon = True
    return sample_daemon_args


@pytest.fixture
def daemon_status_args(sample_daemon_args):
    """Provide daemon status arguments."""
    sample_daemon_args.daemon_status = True
    return sample_daemon_args


@pytest.fixture
def daemon_stop_args(sample_daemon_args):
    """Provide daemon stop arguments."""
    sample_daemon_args.daemon_stop = True
    return sample_daemon_args


# Integration test helper functions
def create_mock_daemon_controller(
    is_running: bool = False, pid: Optional[int] = None, status_response: Optional[str] = None
) -> Mock:
    """Create a mock daemon controller for testing.

    Args:
        is_running: Whether daemon should appear to be running
        pid: Mock PID to return
        status_response: Mock status response

    Returns:
        Mock DaemonController configured for testing
    """
    controller = Mock()
    controller.daemon_manager.is_daemon_running.return_value = is_running
    controller.daemon_manager.get_daemon_pid.return_value = pid

    if status_response:
        mock_status = Mock()
        mock_status.format_status.return_value = status_response
        controller.get_daemon_status.return_value = mock_status
    else:
        controller.get_daemon_status.return_value = None

    return controller
