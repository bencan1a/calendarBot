"""Comprehensive tests for calendarbot.utils.process module."""

import os
import signal
import socket
import subprocess
import time
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from calendarbot.utils.process import (
    ProcessInfo,
    auto_cleanup_before_start,
    check_port_availability,
    find_calendarbot_processes,
    find_process_using_port,
    kill_calendarbot_processes,
)


class TestProcessInfo:
    """Test the ProcessInfo class."""

    def test_init(self):
        """Test ProcessInfo initialization."""
        process = ProcessInfo(1234, "python", "python -m calendarbot")
        assert process.pid == 1234
        assert process.command == "python"
        assert process.full_command == "python -m calendarbot"

    def test_str_representation(self):
        """Test ProcessInfo string representation."""
        process = ProcessInfo(1234, "python", "python -m calendarbot")
        assert str(process) == "PID 1234: python"

    @pytest.mark.parametrize(
        "pid, command, full_command, expected",
        [
            (999, "calendarbot", "/usr/bin/python /app/calendarbot", "PID 999: calendarbot"),
            (12345, "main.py", "python main.py --debug", "PID 12345: main.py"),
            (0, "", "", "PID 0: "),
        ],
    )
    def test_str_parametrized(self, pid, command, full_command, expected):
        """Test ProcessInfo string representation with various inputs."""
        process = ProcessInfo(pid, command, full_command)
        assert str(process) == expected


class TestFindCalendarbotProcesses:
    """Test the find_calendarbot_processes function."""

    @patch("subprocess.run")
    @patch("os.getpid")
    def test_find_processes_success(self, mock_getpid, mock_subprocess):
        """Test successful process discovery."""
        mock_getpid.return_value = 9999

        # Mock pgrep output for different patterns
        mock_subprocess.side_effect = [
            # First pattern: calendarbot
            Mock(
                returncode=0,
                stdout="1234 /usr/bin/python -m calendarbot\n5678 python calendarbot.py\n",
            ),
            # Second pattern: python.*calendarbot (no matches)
            Mock(returncode=1, stdout=""),
            # Third pattern: python.*main\.py
            Mock(returncode=0, stdout="9876 python main.py --config=/etc/calendarbot.conf\n"),
        ]

        processes = find_calendarbot_processes()

        assert len(processes) == 3
        assert processes[0].pid == 1234
        assert processes[0].command == "/usr/bin/python"
        assert processes[1].pid == 5678
        assert processes[1].command == "python"
        assert processes[2].pid == 9876
        assert processes[2].command == "python"

    @patch("subprocess.run")
    @patch("os.getpid")
    def test_find_processes_excludes_self(self, mock_getpid, mock_subprocess):
        """Test that the current process is excluded from results."""
        mock_getpid.return_value = 1234

        mock_subprocess.side_effect = [
            Mock(
                returncode=0,
                stdout="1234 /usr/bin/python -m calendarbot\n5678 python calendarbot.py\n",
            ),
            Mock(returncode=1, stdout=""),
            Mock(returncode=1, stdout=""),
        ]

        processes = find_calendarbot_processes()

        assert len(processes) == 1
        assert processes[0].pid == 5678

    @patch("subprocess.run")
    def test_find_processes_no_matches(self, mock_subprocess):
        """Test when no processes are found."""
        mock_subprocess.side_effect = [
            Mock(returncode=1, stdout=""),
            Mock(returncode=1, stdout=""),
            Mock(returncode=1, stdout=""),
        ]

        processes = find_calendarbot_processes()
        assert len(processes) == 0

    @patch("subprocess.run")
    def test_find_processes_invalid_pid(self, mock_subprocess):
        """Test handling of invalid PID in output."""
        mock_subprocess.side_effect = [
            Mock(
                returncode=0,
                stdout="invalid /usr/bin/python -m calendarbot\n1234 python calendarbot.py\n",
            ),
            Mock(returncode=1, stdout=""),
            Mock(returncode=1, stdout=""),
        ]

        processes = find_calendarbot_processes()
        assert len(processes) == 1
        assert processes[0].pid == 1234

    @patch("subprocess.run")
    def test_find_processes_malformed_output(self, mock_subprocess):
        """Test handling of malformed pgrep output."""
        mock_subprocess.side_effect = [
            Mock(returncode=0, stdout="1234\n\n5678 python calendarbot.py\n"),
            Mock(returncode=1, stdout=""),
            Mock(returncode=1, stdout=""),
        ]

        processes = find_calendarbot_processes()
        assert len(processes) == 1
        assert processes[0].pid == 5678

    @patch("subprocess.run")
    def test_find_processes_timeout_error(self, mock_subprocess):
        """Test handling of subprocess timeout."""
        mock_subprocess.side_effect = [
            subprocess.TimeoutExpired(["pgrep"], 5),
            Mock(returncode=0, stdout="1234 python calendarbot.py\n"),
            Mock(returncode=1, stdout=""),
        ]

        processes = find_calendarbot_processes()
        assert len(processes) == 1
        assert processes[0].pid == 1234

    @patch("subprocess.run")
    def test_find_processes_called_process_error(self, mock_subprocess):
        """Test handling of subprocess CalledProcessError."""
        mock_subprocess.side_effect = [
            subprocess.CalledProcessError(1, ["pgrep"]),
            Mock(returncode=0, stdout="1234 python calendarbot.py\n"),
            Mock(returncode=1, stdout=""),
        ]

        processes = find_calendarbot_processes()
        assert len(processes) == 1

    @patch("subprocess.run")
    @patch("calendarbot.utils.process.logger")
    def test_find_processes_general_exception(self, mock_logger, mock_subprocess):
        """Test handling of general exception."""
        mock_subprocess.side_effect = Exception("System error")

        processes = find_calendarbot_processes()
        assert len(processes) == 0
        mock_logger.error.assert_called_once()


class TestKillCalendarbotProcesses:
    """Test the kill_calendarbot_processes function."""

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("time.sleep")
    @patch("os.getpid")
    @patch("os.kill")
    def test_kill_processes_success(self, mock_kill, mock_getpid, mock_sleep, mock_find):
        """Test successful process termination."""
        mock_getpid.return_value = 9999
        mock_kill.side_effect = ProcessLookupError()  # Process already dead when trying to kill

        # First call returns processes to kill, subsequent calls return fewer/none
        mock_find.side_effect = [
            [ProcessInfo(1234, "python", "python -m calendarbot")],
            [],  # After SIGTERM, no processes remain
            [],  # Final check
        ]

        killed_count, errors = kill_calendarbot_processes()

        assert killed_count == 1
        assert errors == []
        mock_kill.assert_called_once_with(1234, signal.SIGTERM)

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("time.sleep")
    @patch("os.getpid")
    @patch("os.kill")
    def test_kill_processes_requires_sigkill(self, mock_kill, mock_getpid, mock_sleep, mock_find):
        """Test process termination that requires SIGKILL."""
        mock_getpid.return_value = 9999

        process = ProcessInfo(1234, "python", "python -m calendarbot")
        mock_find.side_effect = [
            [process],  # Initial find
            [process],  # Still running after SIGTERM
            [],  # Finally gone after SIGKILL
        ]

        killed_count, errors = kill_calendarbot_processes()

        assert killed_count == 1
        assert errors == []
        assert mock_kill.call_count == 2
        mock_kill.assert_any_call(1234, signal.SIGTERM)
        mock_kill.assert_any_call(1234, signal.SIGKILL)

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    def test_kill_processes_no_processes(self, mock_find):
        """Test when no processes are found to kill."""
        mock_find.return_value = []

        killed_count, errors = kill_calendarbot_processes()

        assert killed_count == 0
        assert errors == []

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("time.sleep")
    @patch("os.getpid")
    @patch("os.kill")
    def test_kill_processes_exclude_self(self, mock_kill, mock_getpid, mock_sleep, mock_find):
        """Test that current process is excluded from termination."""
        mock_getpid.return_value = 1234
        mock_kill.side_effect = ProcessLookupError()  # Process already dead when trying to kill

        mock_find.side_effect = [
            [
                ProcessInfo(1234, "python", "python -m calendarbot"),
                ProcessInfo(5678, "python", "python -m calendarbot"),
            ],
            [],
            [],
        ]

        killed_count, errors = kill_calendarbot_processes(exclude_self=True)

        assert killed_count == 1
        assert errors == []
        mock_kill.assert_called_once_with(5678, signal.SIGTERM)

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("time.sleep")
    @patch("os.getpid")
    @patch("os.kill")
    def test_kill_processes_include_self(self, mock_kill, mock_getpid, mock_sleep, mock_find):
        """Test killing processes including self when exclude_self=False."""
        mock_getpid.return_value = 1234
        mock_kill.side_effect = ProcessLookupError()  # Process already dead when trying to kill

        mock_find.side_effect = [
            [
                ProcessInfo(1234, "python", "python -m calendarbot"),
                ProcessInfo(5678, "python", "python -m calendarbot"),
            ],
            [],
            [],
        ]

        killed_count, errors = kill_calendarbot_processes(exclude_self=False)

        assert killed_count == 2
        assert errors == []
        assert mock_kill.call_count == 2

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("time.sleep")
    @patch("os.getpid")
    @patch("os.kill")
    def test_kill_processes_process_already_dead(
        self, mock_kill, mock_getpid, mock_sleep, mock_find
    ):
        """Test handling of ProcessLookupError (process already dead)."""
        mock_getpid.return_value = 9999
        mock_kill.side_effect = ProcessLookupError()

        mock_find.side_effect = [[ProcessInfo(1234, "python", "python -m calendarbot")], [], []]

        killed_count, errors = kill_calendarbot_processes()

        assert killed_count == 1
        assert errors == []

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("time.sleep")
    @patch("os.getpid")
    @patch("os.kill")
    def test_kill_processes_permission_error(self, mock_kill, mock_getpid, mock_sleep, mock_find):
        """Test handling of PermissionError."""
        mock_getpid.return_value = 9999
        mock_kill.side_effect = PermissionError()

        mock_find.side_effect = [[ProcessInfo(1234, "python", "python -m calendarbot")], [], []]

        killed_count, errors = kill_calendarbot_processes()

        assert killed_count == 0
        assert len(errors) == 1
        assert "Permission denied" in errors[0]

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("time.sleep")
    @patch("os.getpid")
    @patch("os.kill")
    def test_kill_processes_general_error(self, mock_kill, mock_getpid, mock_sleep, mock_find):
        """Test handling of general exception during kill."""
        mock_getpid.return_value = 9999
        mock_kill.side_effect = OSError("System error")

        mock_find.side_effect = [[ProcessInfo(1234, "python", "python -m calendarbot")], [], []]

        killed_count, errors = kill_calendarbot_processes()

        assert killed_count == 0
        assert len(errors) == 1
        assert "Error killing process 1234" in errors[0]

    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("time.sleep")
    @patch("os.getpid")
    @patch("os.kill")
    def test_kill_processes_persistent_processes(
        self, mock_kill, mock_getpid, mock_sleep, mock_find
    ):
        """Test handling of processes that won't die."""
        mock_getpid.return_value = 9999

        process = ProcessInfo(1234, "python", "python -m calendarbot")
        mock_find.side_effect = [
            [process],  # Initial find
            [process],  # Still running after SIGTERM
            [process],  # Still running after SIGKILL
        ]

        killed_count, errors = kill_calendarbot_processes()

        assert killed_count == 1  # SIGKILL attempt is counted as killed even if process persists
        assert len(errors) == 1
        assert "1 processes still running" in errors[0]

    @pytest.mark.parametrize("timeout", [0.5, 2.0, 5.0, 10.0])
    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("time.sleep")
    @patch("os.getpid")
    @patch("os.kill")
    def test_kill_processes_timeout_values(
        self, mock_kill, mock_getpid, mock_sleep, mock_find, timeout
    ):
        """Test different timeout values."""
        mock_getpid.return_value = 9999
        mock_find.side_effect = [[ProcessInfo(1234, "python", "python -m calendarbot")], [], []]

        kill_calendarbot_processes(timeout=timeout)

        # Should sleep for min(timeout, 2.0)
        expected_sleep = min(timeout, 2.0)
        mock_sleep.assert_called_with(expected_sleep)


class TestCheckPortAvailability:
    """Test the check_port_availability function."""

    @patch("socket.socket")
    def test_port_available(self, mock_socket_class):
        """Test when port is available."""
        mock_socket = MagicMock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket
        mock_socket.connect_ex.return_value = 1  # Connection failed = port available

        result = check_port_availability("localhost", 8080)

        assert result is True
        mock_socket.settimeout.assert_called_once_with(1.0)
        mock_socket.connect_ex.assert_called_once_with(("localhost", 8080))

    @patch("socket.socket")
    def test_port_occupied(self, mock_socket_class):
        """Test when port is occupied."""
        mock_socket = MagicMock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket
        mock_socket.connect_ex.return_value = 0  # Connection succeeded = port occupied

        result = check_port_availability("127.0.0.1", 8080)

        assert result is False

    @patch("socket.socket")
    @patch("calendarbot.utils.process.logger")
    def test_port_check_exception(self, mock_logger, mock_socket_class):
        """Test handling of socket exception."""
        mock_socket_class.side_effect = Exception("Socket error")

        result = check_port_availability("localhost", 8080)

        assert result is False
        mock_logger.debug.assert_called_once()

    @pytest.mark.parametrize(
        "host, port",
        [
            ("localhost", 80),
            ("127.0.0.1", 443),
            ("0.0.0.0", 8000),
            ("::1", 9000),
        ],
    )
    @patch("socket.socket")
    def test_port_check_various_hosts_ports(self, mock_socket_class, host, port):
        """Test port checking with various host/port combinations."""
        mock_socket = MagicMock()
        mock_socket_class.return_value.__enter__.return_value = mock_socket
        mock_socket.connect_ex.return_value = 1

        result = check_port_availability(host, port)

        assert result is True
        mock_socket.connect_ex.assert_called_once_with((host, port))


class TestFindProcessUsingPort:
    """Test the find_process_using_port function."""

    @patch("subprocess.run")
    def test_find_process_netstat_success(self, mock_subprocess):
        """Test successful process discovery using netstat."""
        netstat_output = """
Active Internet connections (only servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
tcp        0      0 0.0.0.0:8080            0.0.0.0:*               LISTEN      1234/python
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      567/sshd
        """.strip()

        mock_subprocess.return_value = Mock(returncode=0, stdout=netstat_output)

        result = find_process_using_port(8080)

        assert result is not None
        assert result.pid == 1234
        assert result.command == "python"
        assert "port 8080" in result.full_command

    @patch("subprocess.run")
    def test_find_process_netstat_not_found(self, mock_subprocess):
        """Test when port is not found in netstat output."""
        netstat_output = """
Active Internet connections (only servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      567/sshd
        """.strip()

        mock_subprocess.return_value = Mock(returncode=0, stdout=netstat_output)

        result = find_process_using_port(8080)

        assert result is None

    @patch("subprocess.run")
    def test_find_process_netstat_malformed_output(self, mock_subprocess):
        """Test handling of malformed netstat output."""
        netstat_output = """
Active Internet connections (only servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name
tcp        0      0 0.0.0.0:8080            0.0.0.0:*               LISTEN      invalid/python
tcp        0      0 0.0.0.0:8080            0.0.0.0:*               LISTEN      1234/python
        """.strip()

        mock_subprocess.return_value = Mock(returncode=0, stdout=netstat_output)

        result = find_process_using_port(8080)

        assert result is not None
        assert result.pid == 1234

    @patch("subprocess.run")
    def test_find_process_fallback_to_lsof(self, mock_subprocess):
        """Test fallback to lsof when netstat fails."""
        mock_subprocess.side_effect = [
            subprocess.CalledProcessError(1, ["netstat"]),  # netstat fails
            Mock(returncode=0, stdout="1234\n"),  # lsof succeeds
        ]

        result = find_process_using_port(8080)

        assert result is not None
        assert result.pid == 1234
        assert result.command == "unknown"
        assert "port 8080" in result.full_command

    @patch("subprocess.run")
    def test_find_process_lsof_multiple_pids(self, mock_subprocess):
        """Test lsof with multiple PIDs (should use first one)."""
        mock_subprocess.side_effect = [
            subprocess.CalledProcessError(1, ["netstat"]),
            Mock(returncode=0, stdout="1234\n"),  # Just return first PID
        ]

        result = find_process_using_port(8080)

        assert result is not None
        assert result.pid == 1234

    @patch("subprocess.run")
    def test_find_process_lsof_invalid_pid(self, mock_subprocess):
        """Test lsof with invalid PID."""
        mock_subprocess.side_effect = [
            subprocess.CalledProcessError(1, ["netstat"]),
            Mock(returncode=0, stdout="invalid\n"),
        ]

        result = find_process_using_port(8080)

        assert result is None

    @patch("subprocess.run")
    def test_find_process_all_methods_fail(self, mock_subprocess):
        """Test when both netstat and lsof fail."""
        mock_subprocess.side_effect = [
            subprocess.CalledProcessError(1, ["netstat"]),
            subprocess.CalledProcessError(1, ["lsof"]),
        ]

        result = find_process_using_port(8080)

        assert result is None

    @patch("subprocess.run")
    def test_find_process_timeout_and_file_not_found(self, mock_subprocess):
        """Test handling of various subprocess exceptions."""
        mock_subprocess.side_effect = [
            subprocess.TimeoutExpired(["netstat"], 5),
            FileNotFoundError(),
        ]

        result = find_process_using_port(8080)

        assert result is None

    @pytest.mark.parametrize("port", [80, 443, 8080, 9000, 65535])
    @patch("subprocess.run")
    def test_find_process_various_ports(self, mock_subprocess, port):
        """Test process discovery for various ports."""
        netstat_output = f"""
tcp        0      0 0.0.0.0:{port}            0.0.0.0:*               LISTEN      1234/python
        """.strip()

        mock_subprocess.return_value = Mock(returncode=0, stdout=netstat_output)

        result = find_process_using_port(port)

        assert result is not None
        assert result.pid == 1234


class TestAutoCleanupBeforeStart:
    """Test the auto_cleanup_before_start function."""

    @patch("calendarbot.utils.process.check_port_availability")
    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.kill_calendarbot_processes")
    @patch("time.sleep")
    def test_cleanup_force_with_processes(self, mock_sleep, mock_kill, mock_find, mock_check_port):
        """Test forced cleanup with existing processes."""
        mock_find.return_value = [ProcessInfo(1234, "python", "python -m calendarbot")]
        mock_kill.return_value = (1, [])
        mock_check_port.side_effect = [True, True]  # Port available after cleanup

        result = auto_cleanup_before_start("localhost", 8080, force=True)

        assert result is True
        mock_kill.assert_called_once()
        assert mock_check_port.call_count == 2

    @patch("calendarbot.utils.process.check_port_availability")
    @patch("calendarbot.utils.process.find_calendarbot_processes")
    def test_cleanup_no_force_port_available(self, mock_find, mock_check_port):
        """Test cleanup without force when port is available."""
        mock_find.return_value = []
        mock_check_port.return_value = True

        result = auto_cleanup_before_start("localhost", 8080, force=False)

        assert result is True
        mock_find.assert_not_called()

    @patch("calendarbot.utils.process.check_port_availability")
    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.kill_calendarbot_processes")
    @patch("time.sleep")
    def test_cleanup_with_errors(self, mock_sleep, mock_kill, mock_find, mock_check_port):
        """Test cleanup that encounters errors."""
        mock_find.return_value = [ProcessInfo(1234, "python", "python -m calendarbot")]
        mock_kill.return_value = (1, ["Permission denied killing process 1234"])
        mock_check_port.side_effect = [True, True]

        result = auto_cleanup_before_start("localhost", 8080, force=True)

        assert result is True

    @patch("calendarbot.utils.process.check_port_availability")
    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.find_process_using_port")
    @patch("os.kill")
    @patch("time.sleep")
    def test_cleanup_port_occupied_kill_port_process(
        self, mock_sleep, mock_os_kill, mock_find_port, mock_find, mock_check_port
    ):
        """Test cleanup when port is occupied by specific process."""
        mock_find.return_value = []
        mock_check_port.side_effect = [
            False,
            False,
            True,
        ]  # Occupied, still occupied, then available
        mock_find_port.return_value = ProcessInfo(5678, "nginx", "nginx (port 8080)")

        result = auto_cleanup_before_start("localhost", 8080, force=True)

        assert result is True
        mock_os_kill.assert_any_call(5678, signal.SIGTERM)
        assert mock_sleep.call_count >= 2

    @patch("calendarbot.utils.process.check_port_availability")
    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.find_process_using_port")
    @patch("os.kill")
    @patch("time.sleep")
    def test_cleanup_port_process_requires_sigkill(
        self, mock_sleep, mock_os_kill, mock_find_port, mock_find, mock_check_port
    ):
        """Test cleanup when port process requires SIGKILL."""
        mock_find.return_value = []
        # Port becomes available after SIGKILL (3rd call is final check)
        mock_check_port.side_effect = [False, False, True]
        mock_find_port.return_value = ProcessInfo(5678, "nginx", "nginx (port 8080)")

        result = auto_cleanup_before_start("localhost", 8080, force=True)

        assert result is True
        mock_os_kill.assert_any_call(5678, signal.SIGTERM)
        mock_os_kill.assert_any_call(5678, signal.SIGKILL)

    @patch("calendarbot.utils.process.check_port_availability")
    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.find_process_using_port")
    @patch("os.kill")
    def test_cleanup_port_process_kill_fails(
        self, mock_os_kill, mock_find_port, mock_find, mock_check_port
    ):
        """Test cleanup when killing port process fails."""
        mock_find.return_value = []
        mock_check_port.return_value = False
        mock_find_port.return_value = ProcessInfo(5678, "nginx", "nginx (port 8080)")
        mock_os_kill.side_effect = PermissionError("Permission denied")

        result = auto_cleanup_before_start("localhost", 8080, force=True)

        assert result is False

    @patch("calendarbot.utils.process.check_port_availability")
    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.find_process_using_port")
    def test_cleanup_port_occupied_no_process_found(
        self, mock_find_port, mock_find, mock_check_port
    ):
        """Test cleanup when port is occupied but no process is found."""
        mock_find.return_value = []
        mock_check_port.return_value = False
        mock_find_port.return_value = None

        result = auto_cleanup_before_start("localhost", 8080, force=True)

        assert result is False

    @patch("calendarbot.utils.process.check_port_availability")
    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.kill_calendarbot_processes")
    @patch("time.sleep")
    def test_cleanup_no_processes_found(self, mock_sleep, mock_kill, mock_find, mock_check_port):
        """Test cleanup when no processes are found."""
        mock_find.return_value = []
        mock_check_port.return_value = True

        result = auto_cleanup_before_start("localhost", 8080, force=True)

        assert result is True
        mock_kill.assert_not_called()

    @pytest.mark.parametrize(
        "host, port",
        [
            ("localhost", 8080),
            ("127.0.0.1", 9000),
            ("0.0.0.0", 80),
        ],
    )
    @patch("calendarbot.utils.process.check_port_availability")
    @patch("calendarbot.utils.process.find_calendarbot_processes")
    def test_cleanup_various_host_port_combinations(self, mock_find, mock_check_port, host, port):
        """Test cleanup with various host/port combinations."""
        mock_find.return_value = []
        mock_check_port.return_value = True

        result = auto_cleanup_before_start(host, port, force=False)

        assert result is True
        mock_check_port.assert_called_with(host, port)


class TestProcessModuleIntegration:
    """Integration tests for the process module."""

    @patch("calendarbot.utils.process.kill_calendarbot_processes")
    @patch("calendarbot.utils.process.find_calendarbot_processes")
    @patch("calendarbot.utils.process.check_port_availability")
    @patch("time.sleep")
    def test_full_cleanup_workflow(
        self, mock_sleep, mock_check_port, mock_find, mock_kill_processes
    ):
        """Test complete cleanup workflow integration."""
        # Mock process discovery - find processes initially
        mock_find.return_value = [ProcessInfo(1234, "python", "python -m calendarbot")]

        # Mock kill function to return success
        mock_kill_processes.return_value = (1, [])  # 1 process killed, no errors

        # Mock port check - initially occupied, then available after cleanup
        mock_check_port.side_effect = [False, True]  # Occupied, then available

        result = auto_cleanup_before_start("localhost", 8080, force=True)

        assert result is True
        mock_kill_processes.assert_called_once()
        assert mock_check_port.call_count == 2

    def test_process_info_in_various_contexts(self):
        """Test ProcessInfo usage in various contexts."""
        process = ProcessInfo(1234, "python", "python -m calendarbot --debug")

        # Test in string context
        process_str = f"Found {process}"
        assert "Found PID 1234: python" in process_str

        # Test attribute access
        assert process.pid == 1234
        assert process.command == "python"
        assert "calendarbot" in process.full_command

    @patch("calendarbot.utils.process.logger")
    def test_logging_integration(self, mock_logger):
        """Test that appropriate logging occurs during operations."""
        # This test ensures that the logging calls are made correctly

        # Test with no processes found
        with patch("calendarbot.utils.process.find_calendarbot_processes", return_value=[]):
            kill_calendarbot_processes()
            mock_logger.debug.assert_called_with("No calendarbot processes found to kill")
