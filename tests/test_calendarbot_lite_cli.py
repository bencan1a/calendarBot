"""Unit tests for calendarbot_lite CLI functionality."""

from unittest.mock import Mock, patch

import pytest

from calendarbot_lite import run_server
from calendarbot_lite.__main__ import _create_parser


class TestCalendarbotLiteCLI:
    """Test cases for calendarbot_lite command line interface."""

    def test_create_parser_when_no_args_then_defaults(self) -> None:
        """Test parser creation with default configuration."""
        parser = _create_parser()
        args = parser.parse_args([])
        
        assert args.port is None

    def test_create_parser_when_port_specified_then_parsed_correctly(self) -> None:
        """Test parser correctly handles --port argument."""
        parser = _create_parser()
        args = parser.parse_args(["--port", "3000"])
        
        assert args.port == 3000

    def test_create_parser_when_invalid_port_then_raises_error(self) -> None:
        """Test parser raises error for invalid port values."""
        parser = _create_parser()
        
        with pytest.raises(SystemExit):
            parser.parse_args(["--port", "invalid"])

    def test_create_parser_when_negative_port_then_parsed_as_negative(self) -> None:
        """Test parser handles negative port numbers (validation happens later)."""
        parser = _create_parser()
        args = parser.parse_args(["--port", "-1"])
        
        assert args.port == -1

    def test_create_parser_when_help_requested_then_shows_usage(self) -> None:
        """Test parser shows help message with correct usage information."""
        parser = _create_parser()
        
        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])

    def test_run_server_when_no_args_then_uses_env_config(self) -> None:
        """Test run_server works without command line arguments."""
        with patch('importlib.import_module') as mock_import:
            mock_server = Mock()
            mock_server._build_default_config_from_env.return_value = {"server_port": 8080}
            mock_server._create_skipped_store_if_available.return_value = None
            mock_server.start_server = Mock()
            mock_import.return_value = mock_server
            
            run_server(None)
            
            mock_server.start_server.assert_called_once()
            config_arg = mock_server.start_server.call_args[0][0]
            assert config_arg.get("server_port") == 8080

    def test_run_server_when_port_arg_then_overrides_config(self) -> None:
        """Test run_server applies command line port override."""
        with patch('importlib.import_module') as mock_import:
            mock_server = Mock()
            mock_server._build_default_config_from_env.return_value = {"server_port": 8080}
            mock_server._create_skipped_store_if_available.return_value = None
            mock_server.start_server = Mock()
            mock_import.return_value = mock_server
            
            args = Mock()
            args.port = 9999
            
            run_server(args)
            
            mock_server.start_server.assert_called_once()
            config_arg = mock_server.start_server.call_args[0][0]
            assert config_arg.get("server_port") == 9999

    def test_run_server_when_invalid_port_arg_then_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test run_server logs warning for invalid port values."""
        with patch('importlib.import_module') as mock_import:
            mock_server = Mock()
            mock_server._build_default_config_from_env.return_value = {}
            mock_server._create_skipped_store_if_available.return_value = None
            mock_server.start_server = Mock()
            mock_import.return_value = mock_server
            
            args = Mock()
            args.port = "invalid"
            
            run_server(args)
            
            # Check that warning was logged about invalid port
            assert any("Invalid port value" in record.message for record in caplog.records)

    def test_run_server_when_no_env_config_then_uses_empty_config(self) -> None:
        """Test run_server handles missing environment configuration gracefully."""
        with patch('importlib.import_module') as mock_import:
            mock_server = Mock()
            mock_server._build_default_config_from_env.return_value = None
            mock_server._create_skipped_store_if_available.return_value = None
            mock_server.start_server = Mock()
            mock_import.return_value = mock_server
            
            args = Mock()
            args.port = 3000
            
            run_server(args)
            
            mock_server.start_server.assert_called_once()
            config_arg = mock_server.start_server.call_args[0][0]
            assert config_arg.get("server_port") == 3000

    def test_run_server_when_zero_port_then_applies_override(self) -> None:
        """Test run_server correctly handles port 0 (system-assigned port)."""
        with patch('importlib.import_module') as mock_import:
            mock_server = Mock()
            mock_server._build_default_config_from_env.return_value = {"server_port": 8080}
            mock_server._create_skipped_store_if_available.return_value = None
            mock_server.start_server = Mock()
            mock_import.return_value = mock_server
            
            args = Mock()
            args.port = 0
            
            run_server(args)
            
            mock_server.start_server.assert_called_once()
            config_arg = mock_server.start_server.call_args[0][0]
            assert config_arg.get("server_port") == 0

    def test_run_server_when_server_import_fails_then_raises_not_implemented(self) -> None:
        """Test run_server raises NotImplementedError when server module import fails."""
        with patch('importlib.import_module') as mock_import:
            mock_import.side_effect = ImportError("Module not found")
            
            with pytest.raises(NotImplementedError) as exc_info:
                run_server(None)
            
            assert "calendarbot_lite server not available" in str(exc_info.value)
            assert "Module not found" in str(exc_info.value)
