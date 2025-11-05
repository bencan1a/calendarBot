"""Unit tests for calendarbot_lite.__main__ module.

Tests cover CLI argument parsing, main entry point, error handling,
and integration with the run_server function.
"""

from __future__ import annotations

from argparse import Namespace
from unittest.mock import Mock

import pytest

from calendarbot_lite.__main__ import _create_parser, main


@pytest.mark.unit
@pytest.mark.fast
class TestCreateParser:
    """Tests for argument parser creation."""

    def test_create_parser_when_called_then_returns_parser(self) -> None:
        """Test parser creation returns ArgumentParser instance."""
        parser = _create_parser()
        
        assert parser is not None
        assert parser.prog == "calendarbot_lite"
        assert parser.description is not None
        assert "CalendarBot Lite" in parser.description

    def test_create_parser_when_called_then_has_port_argument(self) -> None:
        """Test parser includes --port argument."""
        parser = _create_parser()
        
        # Parse with port argument
        args = parser.parse_args(["--port", "3000"])
        assert args.port == 3000

    def test_create_parser_when_no_args_then_port_is_none(self) -> None:
        """Test parser when no arguments provided."""
        parser = _create_parser()
        
        args = parser.parse_args([])
        assert args.port is None

    def test_create_parser_when_invalid_port_then_raises_error(self) -> None:
        """Test parser rejects non-integer port values."""
        parser = _create_parser()
        
        with pytest.raises(SystemExit):
            parser.parse_args(["--port", "invalid"])


@pytest.mark.unit
@pytest.mark.fast
class TestMain:
    """Tests for main entry point."""

    def test_main_when_run_server_succeeds_then_exits_zero(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test main exits with 0 when run_server succeeds."""
        mock_run_server = Mock()
        monkeypatch.setattr("calendarbot_lite.__main__.run_server", mock_run_server)
        monkeypatch.setattr("sys.argv", ["calendarbot_lite"])
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0
        mock_run_server.assert_called_once()

    def test_main_when_port_specified_then_passes_to_run_server(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test main passes port argument to run_server."""
        mock_run_server = Mock()
        monkeypatch.setattr("calendarbot_lite.__main__.run_server", mock_run_server)
        monkeypatch.setattr("sys.argv", ["calendarbot_lite", "--port", "5000"])
        
        with pytest.raises(SystemExit):
            main()
        
        call_args = mock_run_server.call_args[0][0]
        assert isinstance(call_args, Namespace)
        assert call_args.port == 5000

    def test_main_when_not_implemented_error_then_prints_message(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """Test main handles NotImplementedError gracefully."""
        mock_run_server = Mock(side_effect=NotImplementedError("Server not ready"))
        monkeypatch.setattr("calendarbot_lite.__main__.run_server", mock_run_server)
        monkeypatch.setattr("sys.argv", ["calendarbot_lite"])
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "calendarbot_lite server is not implemented yet" in captured.out
        assert "Details: Server not ready" in captured.out

    def test_main_when_not_implemented_error_then_suggests_next_steps(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """Test main provides helpful development guidance."""
        mock_run_server = Mock(side_effect=NotImplementedError("Test error"))
        monkeypatch.setattr("calendarbot_lite.__main__.run_server", mock_run_server)
        monkeypatch.setattr("sys.argv", ["calendarbot_lite"])
        
        with pytest.raises(SystemExit):
            main()
        
        captured = capsys.readouterr()
        assert "To continue development:" in captured.out
        assert "calendarbot_lite.api.server" in captured.out

    def test_main_when_no_args_then_uses_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test main with no command line arguments."""
        mock_run_server = Mock()
        monkeypatch.setattr("calendarbot_lite.__main__.run_server", mock_run_server)
        monkeypatch.setattr("sys.argv", ["calendarbot_lite"])
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0
        call_args = mock_run_server.call_args[0][0]
        assert call_args.port is None  # Default behavior


@pytest.mark.unit
@pytest.mark.fast
class TestMainIntegration:
    """Integration tests for main function behavior."""

    def test_main_when_parser_fails_then_exits_nonzero(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test main exits with non-zero on parser error."""
        monkeypatch.setattr("sys.argv", ["calendarbot_lite", "--port", "invalid"])
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code != 0

    def test_main_when_called_creates_parser_and_calls_run_server(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test main creates parser and invokes run_server."""
        mock_run_server = Mock()
        mock_parser = Mock()
        mock_parser.parse_args.return_value = Namespace(port=8080)
        
        monkeypatch.setattr("calendarbot_lite.__main__.run_server", mock_run_server)
        monkeypatch.setattr("calendarbot_lite.__main__._create_parser", lambda: mock_parser)
        monkeypatch.setattr("sys.argv", ["calendarbot_lite", "--port", "8080"])
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0
        mock_parser.parse_args.assert_called_once()
        mock_run_server.assert_called_once()


@pytest.mark.unit
@pytest.mark.fast
class TestMainEdgeCases:
    """Edge case tests for main function."""

    def test_main_when_other_exception_then_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test main propagates non-NotImplementedError exceptions."""
        mock_run_server = Mock(side_effect=ValueError("Unexpected error"))
        monkeypatch.setattr("calendarbot_lite.__main__.run_server", mock_run_server)
        monkeypatch.setattr("sys.argv", ["calendarbot_lite"])
        
        with pytest.raises(ValueError, match="Unexpected error"):
            main()

    def test_main_when_keyboard_interrupt_then_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test main propagates KeyboardInterrupt."""
        mock_run_server = Mock(side_effect=KeyboardInterrupt())
        monkeypatch.setattr("calendarbot_lite.__main__.run_server", mock_run_server)
        monkeypatch.setattr("sys.argv", ["calendarbot_lite"])
        
        with pytest.raises(KeyboardInterrupt):
            main()
