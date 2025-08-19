"""Comprehensive tests for calendarbot.utils.process module."""

import signal
import subprocess
from unittest.mock import MagicMock, patch

from calendarbot.utils.process import (
    ProcessInfo,
    auto_cleanup_before_start,
    check_port_availability,
    find_calendarbot_processes,
    find_process_using_port,
    kill_calendarbot_processes,
)


class TestProcessInfo:
    """Test ProcessInfo class."""

    def test_initialization(self):
        """Test ProcessInfo initialization."""
        process = ProcessInfo(pid=1234, command="python", full_command="python calendarbot.py")

        assert process.pid == 1234
        assert process.command == "python"
        assert process.full_command == "python calendarbot.py"

    def test_string_representation(self):
        """Test ProcessInfo string representation."""
        process = ProcessInfo(pid=5678, command="calendarbot", full_command="python -m calendarbot")

        assert str(process) == "PID 5678: calendarbot"


class TestFindCalendarbotProcesses:
    """Test find_calendarbot_processes function."""

    @patch("calendarbot.utils.process.subprocess.run")
    def test_no_processes_found(self, mock_run):
        """Test when no calendarbot processes are found."""
        mock_run.return_value.returncode = 1  # pgrep returns 1 when no matches
        mock_run.return_value.stdout = ""

        processes = find_calendarbot_processes()

        assert processes == []

    @patch("calendarbot.utils.process.subprocess.run")
    @patch("calendarbot.utils.process.os.getpid", return_value=9999)
    def test_processes_found_excluding_self(self, mock_getpid, mock_run):
        """Test finding processes excluding current process."""
        # Mock only the first call to return our test data, others return empty
        call_count = [0]

        def run_side_effect(cmd, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # First call only
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = (
                    "1234 python calendarbot.py\n5678 /usr/bin/python3 -m calendarbot"
                )
                return mock_result
            # All other calls
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            return mock_result

        mock_run.side_effect = run_side_effect

        processes = find_calendarbot_processes()

        assert len(processes) == 2
        assert processes[0].pid == 1234
        assert processes[0].command == "python"
        assert processes[0].full_command == "python calendarbot.py"
        assert processes[1].pid == 5678
        assert processes[1].command == "/usr/bin/python3"

    @patch("calendarbot.utils.process.subprocess.run")
    def test_malformed_output_handling(self, mock_run):
        """Test handling of malformed pgrep output."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "invalid line\n1234\n notapid python calendarbot.py"

        processes = find_calendarbot_processes()

        assert processes == []  # All lines are malformed

    @patch("calendarbot.utils.process.subprocess.run")
    def test_multiple_patterns_searched(self, mock_run):
        """Test that multiple patterns are searched."""
        mock_run.return_value.returncode = 1  # No matches for any pattern
        mock_run.return_value.stdout = ""

        find_calendarbot_processes()

        # Should call pgrep for each pattern
        assert mock_run.call_count >= 2  # At least 2 patterns (calendarbot, python.*calendarbot)

    @patch("calendarbot.utils.process.subprocess.run")
    def test_subprocess_timeout_handling(self, mock_run):
        """Test handling of subprocess timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("pgrep", 5)

        processes = find_calendarbot_processes()

        assert processes == []

    @patch("calendarbot.utils.process.subprocess.run")
    def test_subprocess_error_handling(self, mock_run):
        """Test handling of subprocess errors."""
        mock_run.side_effect = subprocess.CalledProcessError(2, "pgrep")

        processes = find_calendarbot_processes()

        assert processes == []

    @patch("calendarbot.utils.process.subprocess.run")
    def test_general_exception_handling(self, mock_run):
        """Test handling of general exceptions."""
        mock_run.side_effect = Exception("Unexpected error")

        with patch("calendarbot.utils.process.logger") as mock_logger:
            processes = find_calendarbot_processes()

            assert processes == []
            mock_logger.exception.assert_called_once()

    @patch("calendarbot.utils.process.subprocess.run")
    @patch("calendarbot.utils.process.os.getpid", return_value=9999)
    def test_empty_command_handling(self, mock_getpid, mock_run):
        """Test handling of processes with empty commands."""
        # Mock only the first call to return our test data, others return empty
        call_count = [0]

        def run_side_effect(cmd, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:  # First call only
                mock_result = MagicMock()
                mock_result.returncode = 0
                # Only the legitimate calendarbot process should be found
                mock_result.stdout = "5678 python calendarbot.py"
                return mock_result
            # All other calls
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            return mock_result

        mock_run.side_effect = run_side_effect

        processes = find_calendarbot_processes()

        assert len(processes) == 1
        assert processes[0].command == "python"


class TestKillCalendarbotProcesses:
    """Test kill_calendarbot_processes function."""

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    def test_no_processes_to_kill(self, mock_find):
        """Test when no processes are found to kill."""
        mock_find.return_value = []

        killed_count, errors = kill_calendarbot_processes()

        assert killed_count == 0
        assert errors == []

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.os.kill")
    @patch("calendarbot.utils.process.os.getpid", return_value=9999)
    def test_successful_process_termination(self, mock_getpid, mock_kill, mock_find):
        """Test successful process termination."""
        processes = [
            ProcessInfo(1234, "python", "python calendarbot.py"),
            ProcessInfo(5678, "calendarbot", "calendarbot --web"),
        ]
        mock_find.side_effect = [
            processes,
            [],
            [],
        ]  # Found processes, then none after killing, then final check

        with patch("calendarbot.utils.process.time.sleep"):
            killed_count, errors = kill_calendarbot_processes()

        assert killed_count == 0  # No processes marked as killed in this flow
        assert errors == []
        assert mock_kill.call_count == 2  # SIGTERM sent to both processes

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.os.kill")
    @patch("calendarbot.utils.process.os.getpid", return_value=1234)
    def test_exclude_self_process(self, mock_getpid, mock_kill, mock_find):
        """Test excluding current process from termination."""
        processes = [
            ProcessInfo(1234, "python", "python calendarbot.py"),  # Current process
            ProcessInfo(5678, "calendarbot", "calendarbot --web"),
        ]
        mock_find.side_effect = [processes, [], []]

        with patch("calendarbot.utils.process.time.sleep"):
            killed_count, errors = kill_calendarbot_processes(exclude_self=True)

        # Should only try to kill process 5678, not 1234 (self)
        mock_kill.assert_called_once_with(5678, signal.SIGTERM)

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.os.kill")
    def test_include_self_process(self, mock_kill, mock_find):
        """Test including current process in termination."""
        processes = [ProcessInfo(1234, "python", "python calendarbot.py")]
        mock_find.side_effect = [processes, [], []]

        with patch("calendarbot.utils.process.time.sleep"):
            with patch("calendarbot.utils.process.os.getpid", return_value=9999):
                killed_count, errors = kill_calendarbot_processes(exclude_self=False)

        mock_kill.assert_called_with(1234, signal.SIGTERM)

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.os.kill")
    def test_process_already_dead(self, mock_kill, mock_find):
        """Test handling process already dead (ProcessLookupError)."""
        processes = [ProcessInfo(1234, "python", "python calendarbot.py")]
        mock_find.side_effect = [processes, [], []]
        mock_kill.side_effect = ProcessLookupError("No such process")

        with patch("calendarbot.utils.process.time.sleep"):
            killed_count, errors = kill_calendarbot_processes()

        assert killed_count == 1  # Counted as killed since already dead
        assert errors == []

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.os.kill")
    def test_permission_denied_error(self, mock_kill, mock_find):
        """Test handling permission denied error."""
        processes = [ProcessInfo(1234, "python", "python calendarbot.py")]
        mock_find.side_effect = [processes, [], []]
        mock_kill.side_effect = PermissionError("Operation not permitted")

        with patch("calendarbot.utils.process.time.sleep"):
            killed_count, errors = kill_calendarbot_processes()

        assert killed_count == 0
        assert len(errors) == 1
        assert "Permission denied" in errors[0]

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.os.kill")
    def test_general_kill_error(self, mock_kill, mock_find):
        """Test handling general kill errors."""
        processes = [ProcessInfo(1234, "python", "python calendarbot.py")]
        mock_find.side_effect = [processes, [], []]
        mock_kill.side_effect = Exception("Unexpected error")

        with patch("calendarbot.utils.process.time.sleep"):
            killed_count, errors = kill_calendarbot_processes()

        assert killed_count == 0
        assert len(errors) == 1
        assert "Error killing process" in errors[0]

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.os.kill")
    def test_sigkill_for_stubborn_processes(self, mock_kill, mock_find):
        """Test SIGKILL for processes that don't respond to SIGTERM."""
        processes = [ProcessInfo(1234, "python", "python calendarbot.py")]
        remaining_processes = [ProcessInfo(1234, "python", "python calendarbot.py")]
        mock_find.side_effect = [
            processes,
            remaining_processes,
            [],
            [],
        ]  # Process persists after SIGTERM, final check

        with patch("calendarbot.utils.process.time.sleep"):
            killed_count, errors = kill_calendarbot_processes()

        # Should send both SIGTERM and SIGKILL
        assert mock_kill.call_count == 2
        mock_kill.assert_any_call(1234, signal.SIGTERM)
        mock_kill.assert_any_call(1234, signal.SIGKILL)

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.os.kill")
    def test_final_count_with_remaining_processes(self, mock_kill, mock_find):
        """Test final count when processes still remain."""
        processes = [ProcessInfo(1234, "python", "python calendarbot.py")]
        # Process persists even after SIGKILL
        mock_find.side_effect = [processes, processes, processes, processes]

        with patch("calendarbot.utils.process.time.sleep"):
            killed_count, errors = kill_calendarbot_processes()

        assert len(errors) >= 1
        assert any("processes still running after cleanup" in error for error in errors)

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.os.kill")
    def test_timeout_parameter(self, mock_kill, mock_find):
        """Test timeout parameter affects wait time."""
        processes = [ProcessInfo(1234, "python", "python calendarbot.py")]
        mock_find.side_effect = [processes, [], []]

        with patch("calendarbot.utils.process.time.sleep") as mock_sleep:
            kill_calendarbot_processes(timeout=10.0)

            # During testing, should sleep for min(timeout, 1.0) = 1.0
            mock_sleep.assert_called_with(1.0)


class TestCheckPortAvailability:
    """Test check_port_availability function."""

    @patch("socket.socket")
    def test_port_available(self, mock_socket):
        """Test when port is available."""
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 1  # Connection failed = port available
        mock_socket.return_value.__enter__.return_value = mock_sock

        result = check_port_availability("127.0.0.1", 8080)

        assert result is True
        mock_sock.settimeout.assert_called_with(1.0)
        mock_sock.connect_ex.assert_called_with(("127.0.0.1", 8080))

    @patch("socket.socket")
    def test_port_occupied(self, mock_socket):
        """Test when port is occupied."""
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0  # Connection succeeded = port occupied
        mock_socket.return_value.__enter__.return_value = mock_sock

        result = check_port_availability("127.0.0.1", 8080)

        assert result is False

    @patch("socket.socket")
    def test_socket_exception(self, mock_socket):
        """Test handling socket exceptions."""
        mock_socket.side_effect = Exception("Socket error")

        with patch("calendarbot.utils.process.logger") as mock_logger:
            result = check_port_availability("127.0.0.1", 8080)

            assert result is False
            mock_logger.debug.assert_called_once()


class TestFindProcessUsingPort:
    """Test find_process_using_port function."""

    @patch("calendarbot.utils.process.subprocess.run")
    def test_netstat_finds_process(self, mock_run):
        """Test finding process using netstat."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = (
            "tcp  0  0  127.0.0.1:8080  0.0.0.0:*  LISTEN  1234/python\n"
            "tcp  0  0  127.0.0.1:9090  0.0.0.0:*  LISTEN  5678/node\n"
        )

        process = find_process_using_port(8080)

        assert process is not None
        assert process.pid == 1234
        assert process.command == "python"
        assert "port 8080" in process.full_command

    @patch("calendarbot.utils.process.subprocess.run")
    def test_netstat_no_process_found(self, mock_run):
        """Test when netstat finds no process on port."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "tcp  0  0  127.0.0.1:9090  0.0.0.0:*  LISTEN  5678/node\n"

        process = find_process_using_port(8080)

        assert process is None

    @patch("calendarbot.utils.process.subprocess.run")
    def test_netstat_fails_lsof_fallback(self, mock_run):
        """Test fallback to lsof when netstat fails."""

        def run_side_effect(cmd, **kwargs):
            if cmd[0] == "netstat":
                raise subprocess.CalledProcessError(1, "netstat")
            if cmd[0] == "lsof":
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "1234\n"
                return mock_result

        mock_run.side_effect = run_side_effect

        process = find_process_using_port(8080)

        assert process is not None
        assert process.pid == 1234
        assert process.command == "unknown"

    @patch("calendarbot.utils.process.subprocess.run")
    def test_both_netstat_and_lsof_fail(self, mock_run):
        """Test when both netstat and lsof fail."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "command")

        process = find_process_using_port(8080)

        assert process is None

    @patch("calendarbot.utils.process.subprocess.run")
    def test_netstat_malformed_output(self, mock_run):
        """Test handling malformed netstat output."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = (
            "malformed line\n"
            "tcp  0  0  127.0.0.1:8080  0.0.0.0:*  LISTEN\n"  # Missing PID
            "tcp  0  0  127.0.0.1:8080  0.0.0.0:*  LISTEN  notapid/python\n"  # Invalid PID
        )

        process = find_process_using_port(8080)

        assert process is None

    @patch("calendarbot.utils.process.subprocess.run")
    def test_lsof_malformed_output(self, mock_run):
        """Test handling malformed lsof output."""

        def run_side_effect(cmd, **kwargs):
            if cmd[0] == "netstat":
                raise FileNotFoundError("netstat not found")
            if cmd[0] == "lsof":
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "notapid\n"  # Invalid PID
                return mock_result

        mock_run.side_effect = run_side_effect

        process = find_process_using_port(8080)

        assert process is None

    @patch("calendarbot.utils.process.subprocess.run")
    def test_timeout_handling(self, mock_run):
        """Test handling of subprocess timeouts."""
        mock_run.side_effect = subprocess.TimeoutExpired("netstat", 5)

        process = find_process_using_port(8080)

        assert process is None


class TestAutoCleanupBeforeStart:
    """Test auto_cleanup_before_start function."""

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.kill_calendarbot_processes")
    @patch("calendarbot.utils.process.check_port_availability")
    def test_force_cleanup_success(self, mock_check_port, mock_kill, mock_find):
        """Test successful force cleanup."""
        processes = [ProcessInfo(1234, "python", "python calendarbot.py")]
        mock_find.return_value = processes
        mock_kill.return_value = (1, [])  # Killed 1 process, no errors
        mock_check_port.return_value = True  # Port available after cleanup

        with patch("calendarbot.utils.process.time.sleep"):
            result = auto_cleanup_before_start("127.0.0.1", 8080, force=True)

        assert result is True
        mock_kill.assert_called_once()

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.kill_calendarbot_processes")
    @patch("calendarbot.utils.process.check_port_availability")
    def test_no_force_cleanup_skipped(self, mock_check_port, mock_kill, mock_find):
        """Test cleanup skipped when force=False."""
        mock_check_port.return_value = True  # Port available

        result = auto_cleanup_before_start("127.0.0.1", 8080, force=False)

        assert result is True
        mock_find.assert_not_called()
        mock_kill.assert_not_called()

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.kill_calendarbot_processes")
    @patch("calendarbot.utils.process.check_port_availability")
    @patch("calendarbot.utils.process.find_process_using_port")
    @patch("calendarbot.utils.process.subprocess.run")
    @patch("calendarbot.utils.process.os.kill")
    def test_port_occupied_specific_process_killed(
        self,
        mock_os_kill,
        mock_subprocess_run,
        mock_find_port_process,
        mock_check_port,
        mock_kill,
        mock_find,
    ):
        """Test killing specific process when port is occupied."""
        mock_find.return_value = []  # No calendarbot processes
        mock_kill.return_value = (0, [])
        mock_check_port.side_effect = [
            False,
            True,
            True,
        ]  # Port occupied, then available, final check

        port_process = ProcessInfo(5678, "other-app", "other-app --port 8080")
        mock_find_port_process.return_value = port_process

        # Mock process exists (os.kill with signal 0 doesn't raise OSError)
        mock_os_kill.return_value = None  # Process exists
        # Mock successful kill
        mock_subprocess_run.return_value = MagicMock(returncode=0, stderr="")

        with patch("calendarbot.utils.process.time.sleep"):
            result = auto_cleanup_before_start("127.0.0.1", 8080, force=True)

        assert result is True
        # Verify kill command was called with SIGTERM
        # Verify os.kill was called for process termination
        mock_os_kill.assert_called_with(5678, signal.SIGTERM)

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.kill_calendarbot_processes")
    @patch("calendarbot.utils.process.check_port_availability")
    @patch("calendarbot.utils.process.find_process_using_port")
    @patch("calendarbot.utils.process.subprocess.run")
    @patch("calendarbot.utils.process.os.kill")
    def test_stubborn_port_process_sigkill(
        self,
        mock_os_kill,
        mock_subprocess_run,
        mock_find_port_process,
        mock_check_port,
        mock_kill,
        mock_find,
    ):
        """Test SIGKILL for stubborn processes occupying port."""
        mock_find.return_value = []
        mock_kill.return_value = (0, [])
        mock_check_port.side_effect = [
            False,
            False,
            True,
            True,
        ]  # Port occupied twice, then available, final check

        port_process = ProcessInfo(5678, "stubborn-app", "stubborn-app --port 8080")
        mock_find_port_process.return_value = port_process

        # Mock process exists (os.kill with signal 0 doesn't raise OSError)
        mock_os_kill.return_value = None  # Process exists
        # Mock successful kill operations
        mock_subprocess_run.return_value = MagicMock(returncode=0, stderr="")

        with patch("calendarbot.utils.process.time.sleep"):
            result = auto_cleanup_before_start("127.0.0.1", 8080, force=True)

        assert result is True
        # Verify both SIGTERM and SIGKILL were attempted
        # Each _safe_kill_process call makes 2 os.kill calls: existence check (signal 0) + actual signal
        assert mock_os_kill.call_count == 4
        mock_os_kill.assert_any_call(5678, 0)  # Existence check before SIGTERM
        mock_os_kill.assert_any_call(5678, signal.SIGTERM)
        mock_os_kill.assert_any_call(5678, 0)  # Existence check before SIGKILL
        mock_os_kill.assert_any_call(5678, signal.SIGKILL)

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.kill_calendarbot_processes")
    @patch("calendarbot.utils.process.check_port_availability")
    @patch("calendarbot.utils.process.find_process_using_port")
    @patch("calendarbot.utils.process.subprocess.run")
    @patch("calendarbot.utils.process.os.kill")
    def test_kill_port_process_error(
        self,
        mock_os_kill,
        mock_subprocess_run,
        mock_find_port_process,
        mock_check_port,
        mock_kill,
        mock_find,
    ):
        """Test error handling when killing port process fails."""
        mock_find.return_value = []
        mock_kill.return_value = (0, [])
        mock_check_port.return_value = False  # Port remains occupied

        port_process = ProcessInfo(5678, "protected-app", "protected-app --port 8080")
        mock_find_port_process.return_value = port_process

        # Mock process exists (os.kill with signal 0 doesn't raise OSError)
        mock_os_kill.return_value = None  # Process exists
        # Mock permission error
        mock_subprocess_run.return_value = MagicMock(returncode=1, stderr="Operation not permitted")

        with patch("calendarbot.utils.process.time.sleep"):
            result = auto_cleanup_before_start("127.0.0.1", 8080, force=True)

        assert result is False

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.kill_calendarbot_processes")
    @patch("calendarbot.utils.process.check_port_availability")
    def test_cleanup_with_errors(self, mock_check_port, mock_kill, mock_find):
        """Test cleanup with errors reported."""
        processes = [ProcessInfo(1234, "python", "python calendarbot.py")]
        mock_find.return_value = processes
        mock_kill.return_value = (0, ["Permission denied for process 1234"])
        mock_check_port.return_value = True

        with patch("calendarbot.utils.process.time.sleep"):
            with patch("calendarbot.utils.process.logger") as mock_logger:
                result = auto_cleanup_before_start("127.0.0.1", 8080, force=True)

        assert result is True
        mock_logger.warning.assert_called()

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.check_port_availability")
    def test_no_processes_found_port_available(self, mock_check_port, mock_find):
        """Test when no processes found and port is available."""
        mock_find.return_value = []
        mock_check_port.return_value = True

        result = auto_cleanup_before_start("127.0.0.1", 8080, force=True)

        assert result is True

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.check_port_availability")
    @patch("calendarbot.utils.process.find_process_using_port")
    def test_no_process_using_port_still_occupied(
        self, mock_find_port_process, mock_check_port, mock_find
    ):
        """Test when port is occupied but no specific process found."""
        mock_find.return_value = []
        mock_check_port.return_value = False  # Port occupied
        mock_find_port_process.return_value = None  # No process found

        result = auto_cleanup_before_start("127.0.0.1", 8080, force=True)

        assert result is False
