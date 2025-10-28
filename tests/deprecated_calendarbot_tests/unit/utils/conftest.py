"""Shared fixtures for utils tests to optimize setup/teardown performance."""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_daemon_process_operations():
    """Fixture for common daemon process operations mocking."""
    with ExitStack() as stack:
        mocks = {
            "fork": stack.enter_context(patch("calendarbot.utils.daemon.os.fork")),
            "setsid": stack.enter_context(patch("calendarbot.utils.daemon.os.setsid")),
            "chdir": stack.enter_context(patch("calendarbot.utils.daemon.os.chdir")),
            "umask": stack.enter_context(patch("calendarbot.utils.daemon.os.umask")),
            "dup2": stack.enter_context(patch("calendarbot.utils.daemon.os.dup2")),
            "getpid": stack.enter_context(patch("calendarbot.utils.daemon.os.getpid")),
            "exit": stack.enter_context(patch("calendarbot.utils.daemon.sys.exit")),
            "stdin": stack.enter_context(patch("calendarbot.utils.daemon.sys.stdin")),
            "stdout": stack.enter_context(patch("calendarbot.utils.daemon.sys.stdout")),
            "stderr": stack.enter_context(patch("calendarbot.utils.daemon.sys.stderr")),
            "logger": stack.enter_context(patch("calendarbot.utils.daemon.logger")),
        }

        # Configure common return values
        mocks["fork"].side_effect = [0, 0]  # Child process for both forks
        mocks["getpid"].return_value = 1234

        yield mocks


@pytest.fixture
def mock_subprocess_operations():
    """Fixture for common subprocess operation mocking."""
    with patch("calendarbot.utils.process.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def mock_socket_operations():
    """Fixture for common socket operation mocking."""
    with ExitStack() as stack:
        socket_mock = stack.enter_context(patch("socket.socket"))
        create_connection_mock = stack.enter_context(patch("socket.create_connection"))

        # Configure common socket behavior
        socket_instance = MagicMock()
        socket_mock.return_value = socket_instance

        yield {
            "socket": socket_mock,
            "socket_instance": socket_instance,
            "create_connection": create_connection_mock,
        }


@pytest.fixture
def mock_file_operations():
    """Fixture for common file operation mocking."""
    with ExitStack() as stack:
        open_mock = stack.enter_context(patch("builtins.open"))
        path_mock = stack.enter_context(patch("calendarbot.utils.daemon.Path"))

        # Configure typical file behavior
        file_handle = MagicMock()
        open_mock.return_value.__enter__.return_value = file_handle

        path_instance = MagicMock()
        path_mock.return_value = path_instance
        path_instance.exists.return_value = True

        yield {
            "open": open_mock,
            "file_handle": file_handle,
            "path": path_mock,
            "path_instance": path_instance,
        }


@pytest.fixture
def mock_http_client_operations():
    """Fixture for common HTTP client operation mocking."""
    with patch("urllib.request.build_opener") as mock_opener:
        opener_instance = MagicMock()
        mock_opener.return_value = opener_instance

        # Configure typical HTTP response
        response_mock = MagicMock()
        response_mock.read.return_value = b"<html>Test content</html>"
        opener_instance.open.return_value = response_mock

        yield {
            "build_opener": mock_opener,
            "opener_instance": opener_instance,
            "response": response_mock,
        }
