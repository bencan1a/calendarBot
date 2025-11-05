"""Unit tests for calendarbot_lite.server port conflict handling."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from calendarbot_lite.api.server import _handle_port_conflict, _import_process_utilities

pytestmark = pytest.mark.unit


class TestImportProcessUtilities:
    """Test the _import_process_utilities function."""

    @patch("calendarbot_lite.server.logger")
    def test_import_process_utilities_when_success_then_returns_functions(self, mock_logger):
        """Test successful import of process utilities."""
        # Mock the successful import by mocking the module directly
        mock_check_port = Mock()
        mock_find_process = Mock()
        mock_auto_cleanup = Mock()

        with patch.dict(
            "sys.modules",
            {
                "calendarbot.utils.process": MagicMock(
                    check_port_availability=mock_check_port,
                    find_process_using_port=mock_find_process,
                    auto_cleanup_before_start=mock_auto_cleanup,
                )
            },
        ):
            result = _import_process_utilities()

            assert len(result) == 3
            assert result[0] is not None
            assert result[1] is not None
            assert result[2] is not None

    @patch("calendarbot_lite.server.logger")
    def test_import_process_utilities_when_import_error_then_returns_none(self, mock_logger):
        """Test import failure returns None values."""
        with patch("builtins.__import__", side_effect=ImportError("Module not found")):
            result = _import_process_utilities()

            assert result == (None, None, None)
            mock_logger.warning.assert_called_once()
            assert "Process utilities not available" in mock_logger.warning.call_args[0][0]


class TestHandlePortConflict:
    """Test the _handle_port_conflict function."""

    @patch("calendarbot_lite.server._import_process_utilities")
    @patch("calendarbot_lite.server.logger")
    def test_handle_port_conflict_when_utilities_missing_then_returns_false(
        self, mock_logger, mock_import
    ):
        """Test when process utilities are not available."""
        mock_import.return_value = (None, None, None)

        result = _handle_port_conflict("localhost", 8080)

        assert result is False
        mock_logger.warning.assert_called_once()
        assert "Port conflict resolution not available" in mock_logger.warning.call_args[0][0]

    @patch("calendarbot_lite.server._import_process_utilities")
    @patch("calendarbot_lite.server.logger")
    def test_handle_port_conflict_when_port_available_then_returns_true(
        self, mock_logger, mock_import
    ):
        """Test when port is already available."""
        mock_check_port = Mock(return_value=True)
        mock_import.return_value = (mock_check_port, Mock(), Mock())

        result = _handle_port_conflict("localhost", 8080)

        assert result is True
        mock_check_port.assert_called_once_with("localhost", 8080)
        mock_logger.debug.assert_called_once_with("Port %d is available", 8080)

    @patch("calendarbot_lite.server._import_process_utilities")
    @patch("calendarbot_lite.server.logger")
    @patch("builtins.print")
    @patch("builtins.input", return_value="n")
    def test_handle_port_conflict_when_user_declines_then_returns_false(
        self, mock_input, mock_print, mock_logger, mock_import
    ):
        """Test when user declines to terminate conflicting process."""
        mock_check_port = Mock(return_value=False)
        mock_find_process = Mock(return_value=None)
        mock_import.return_value = (mock_check_port, mock_find_process, Mock())

        result = _handle_port_conflict("localhost", 8080)

        assert result is False
        mock_logger.error.assert_called_once_with("Port %d is already in use", 8080)
        mock_logger.info.assert_called_once_with(
            "User declined to terminate process using port %d", 8080
        )
        mock_print.assert_any_call("Port conflict not resolved - server cannot start")

    @patch("calendarbot_lite.server._import_process_utilities")
    @patch("calendarbot_lite.server.logger")
    @patch("builtins.print")
    @patch("builtins.input", return_value="y")
    def test_handle_port_conflict_when_user_accepts_and_cleanup_succeeds_then_returns_true(
        self, mock_input, mock_print, mock_logger, mock_import
    ):
        """Test when user accepts and cleanup succeeds."""
        mock_check_port = Mock(return_value=False)

        # Create a mock process info
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.command = "test-server"

        mock_find_process = Mock(return_value=mock_process)
        mock_auto_cleanup = Mock(return_value=True)
        mock_import.return_value = (mock_check_port, mock_find_process, mock_auto_cleanup)

        result = _handle_port_conflict("localhost", 8080)

        assert result is True
        mock_auto_cleanup.assert_called_once_with("localhost", 8080, force=True)
        mock_logger.info.assert_any_call(
            "Successfully terminated conflicting process and freed port %d", 8080
        )
        mock_print.assert_any_call("✓ Port 8080 is now available")

    @patch("calendarbot_lite.server._import_process_utilities")
    @patch("calendarbot_lite.server.logger")
    @patch("builtins.print")
    @patch("builtins.input", return_value="y")
    def test_handle_port_conflict_when_user_accepts_and_cleanup_fails_then_returns_false(
        self, mock_input, mock_print, mock_logger, mock_import
    ):
        """Test when user accepts but cleanup fails."""
        mock_check_port = Mock(return_value=False)

        # Create a mock process info
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.command = "stubborn-server"

        mock_find_process = Mock(return_value=mock_process)
        mock_auto_cleanup = Mock(return_value=False)
        mock_import.return_value = (mock_check_port, mock_find_process, mock_auto_cleanup)

        result = _handle_port_conflict("localhost", 8080)

        assert result is False
        mock_auto_cleanup.assert_called_once_with("localhost", 8080, force=True)
        mock_logger.error.assert_any_call(
            "Failed to terminate conflicting process on port %d", 8080
        )
        mock_print.assert_any_call("✗ Failed to free port 8080")

    @patch("calendarbot_lite.server._import_process_utilities")
    @patch("calendarbot_lite.server.logger")
    @patch("builtins.print")
    @patch("builtins.input", return_value="yes")
    def test_handle_port_conflict_when_auto_cleanup_missing_then_returns_false(
        self, mock_input, mock_print, mock_logger, mock_import
    ):
        """Test when auto cleanup function is not available."""
        mock_check_port = Mock(return_value=False)
        mock_find_process = Mock(return_value=Mock(pid=12345, command="test-server"))
        mock_import.return_value = (mock_check_port, mock_find_process, None)

        result = _handle_port_conflict("localhost", 8080)

        assert result is False
        mock_logger.error.assert_any_call("Auto cleanup function not available")
        mock_print.assert_any_call("✗ Port cleanup functionality not available")

    @patch("calendarbot_lite.server._import_process_utilities")
    @patch("calendarbot_lite.server.logger")
    @patch("builtins.print")
    @patch("builtins.input", return_value="Y")  # Test case insensitive
    def test_handle_port_conflict_when_input_case_insensitive_then_accepts(
        self, mock_input, mock_print, mock_logger, mock_import
    ):
        """Test that input is case insensitive."""
        mock_check_port = Mock(return_value=False)
        mock_find_process = Mock(return_value=Mock(pid=12345, command="test-server"))
        mock_auto_cleanup = Mock(return_value=True)
        mock_import.return_value = (mock_check_port, mock_find_process, mock_auto_cleanup)

        result = _handle_port_conflict("localhost", 8080)

        assert result is True
        mock_logger.info.assert_any_call(
            "User confirmed termination of process using port %d", 8080
        )

    @patch("calendarbot_lite.server._import_process_utilities")
    @patch("calendarbot_lite.server.logger")
    @patch("builtins.print")
    @patch("builtins.input", return_value="y")
    def test_handle_port_conflict_when_no_process_found_then_warns_and_attempts_cleanup(
        self, mock_input, mock_print, mock_logger, mock_import
    ):
        """Test when port is occupied but no specific process is found."""
        mock_check_port = Mock(return_value=False)
        mock_find_process = Mock(return_value=None)
        mock_auto_cleanup = Mock(return_value=True)
        mock_import.return_value = (mock_check_port, mock_find_process, mock_auto_cleanup)

        result = _handle_port_conflict("localhost", 8080)

        assert result is True
        mock_logger.warning.assert_called_once_with(
            "Port %d is occupied but could not identify the process", 8080
        )
        mock_auto_cleanup.assert_called_once_with("localhost", 8080, force=True)
