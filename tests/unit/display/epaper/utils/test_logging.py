"""Tests for e-Paper display logging utilities."""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from calendarbot.display.epaper.utils.logging import (
    DEFAULT_FORMAT,
    DEFAULT_LEVEL,
    configure_package_logging,
    get_logger,
    set_log_level,
    setup_logger,
)


class TestSetupLogger:
    """Test cases for setup_logger function."""

    def test_setup_logger_when_default_params_then_creates_correctly(self) -> None:
        """Test setup_logger with default parameters."""
        # Get a unique logger name to avoid conflicts
        logger_name = f"test_logger_{id(self)}"
        
        # Setup logger
        logger = setup_logger(logger_name)
        
        # Verify logger
        assert isinstance(logger, logging.Logger)
        assert logger.name == logger_name
        assert logger.level == DEFAULT_LEVEL
        
        # Should have at least one handler (console)
        assert len(logger.handlers) >= 1
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
        
        # Clean up
        logging.getLogger(logger_name).handlers = []

    def test_setup_logger_when_custom_level_then_sets_correct_level(self) -> None:
        """Test setup_logger with custom level."""
        # Get a unique logger name to avoid conflicts
        logger_name = f"test_logger_{id(self)}"
        
        # Setup logger with custom level
        custom_level = logging.DEBUG
        logger = setup_logger(logger_name, level=custom_level)
        
        # Verify logger
        assert logger.level == custom_level
        
        # Clean up
        logging.getLogger(logger_name).handlers = []

    def test_setup_logger_when_string_level_then_converts_correctly(self) -> None:
        """Test setup_logger with string level."""
        # Get a unique logger name to avoid conflicts
        logger_name = f"test_logger_{id(self)}"
        
        # Setup logger with string level
        logger = setup_logger(logger_name, level="DEBUG")
        
        # Verify logger
        assert logger.level == logging.DEBUG
        
        # Clean up
        logging.getLogger(logger_name).handlers = []

    def test_setup_logger_when_invalid_string_level_then_defaults_to_info(self) -> None:
        """Test setup_logger with invalid string level defaults to INFO."""
        # Get a unique logger name to avoid conflicts
        logger_name = f"test_logger_{id(self)}"
        
        # Setup logger with invalid string level
        logger = setup_logger(logger_name, level="INVALID")
        
        # Verify logger
        assert logger.level == logging.INFO
        
        # Clean up
        logging.getLogger(logger_name).handlers = []

    def test_setup_logger_when_custom_format_then_uses_correct_format(self) -> None:
        """Test setup_logger with custom format."""
        # Get a unique logger name to avoid conflicts
        logger_name = f"test_logger_{id(self)}"
        
        # Setup logger with custom format
        custom_format = "%(levelname)s - %(message)s"
        logger = setup_logger(logger_name, log_format=custom_format)
        
        # Verify logger
        assert isinstance(logger, logging.Logger)
        
        # Verify formatter
        for handler in logger.handlers:
            assert handler.formatter is not None
            assert handler.formatter._fmt == custom_format
        
        # Clean up
        logging.getLogger(logger_name).handlers = []

    @pytest.fixture
    def temp_log_file(self, tmp_path: Path) -> Path:
        """Create a temporary log file path."""
        return tmp_path / "test.log"

    def test_setup_logger_when_log_file_then_adds_file_handler(self, temp_log_file: Path) -> None:
        """Test setup_logger with log file adds file handler."""
        # Get a unique logger name to avoid conflicts
        logger_name = f"test_logger_{id(self)}"
        
        # Setup logger with log file
        logger = setup_logger(logger_name, log_file=str(temp_log_file))
        
        # Verify logger
        assert isinstance(logger, logging.Logger)
        
        # Should have at least two handlers (console + file)
        assert len(logger.handlers) >= 2
        assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)
        
        # Verify log file was created
        assert temp_log_file.exists()
        
        # Clean up
        logging.getLogger(logger_name).handlers = []

    def test_setup_logger_when_no_console_then_no_console_handler(self) -> None:
        """Test setup_logger with console=False doesn't add console handler."""
        # Get a unique logger name to avoid conflicts
        logger_name = f"test_logger_{id(self)}"
        
        # Setup logger without console handler
        logger = setup_logger(logger_name, console=False)
        
        # Verify logger
        assert isinstance(logger, logging.Logger)
        
        # Should have no handlers
        assert not any(isinstance(h, logging.StreamHandler) and h.stream == sys.stdout for h in logger.handlers)
        
        # Clean up
        logging.getLogger(logger_name).handlers = []

    def test_setup_logger_when_log_file_directory_not_exist_then_creates_directory(
        self, tmp_path: Path
    ) -> None:
        """Test setup_logger creates log file directory if it doesn't exist."""
        # Get a unique logger name to avoid conflicts
        logger_name = f"test_logger_{id(self)}"
        
        # Create nested directory path that doesn't exist
        nested_dir = tmp_path / "nested" / "logs"
        log_file = nested_dir / "test.log"
        
        # Setup logger with log file in non-existent directory
        logger = setup_logger(logger_name, log_file=str(log_file))
        
        # Verify logger
        assert isinstance(logger, logging.Logger)
        
        # Verify directory was created
        assert nested_dir.exists()
        
        # Verify log file was created
        assert log_file.exists()
        
        # Clean up
        logging.getLogger(logger_name).handlers = []


class TestGetLogger:
    """Test cases for get_logger function."""

    def test_get_logger_when_called_then_returns_namespaced_logger(self) -> None:
        """Test get_logger returns logger with correct namespace."""
        # Get logger
        logger_name = "test_module"
        logger = get_logger(logger_name)
        
        # Verify logger
        assert isinstance(logger, logging.Logger)
        assert logger.name == logger_name

    def test_get_logger_when_called_multiple_times_then_returns_same_logger(self) -> None:
        """Test get_logger returns same logger when called multiple times with same name."""
        # Get logger twice
        logger_name = "test_module"
        logger1 = get_logger(logger_name)
        logger2 = get_logger(logger_name)
        
        # Verify loggers are the same
        assert logger1 is logger2

    def test_get_logger_when_different_names_then_returns_different_loggers(self) -> None:
        """Test get_logger returns different loggers for different names."""
        # Get loggers with different names
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        
        # Verify loggers are different
        assert logger1 is not logger2
        assert logger1.name != logger2.name


class TestSetLogLevel:
    """Test cases for set_log_level function."""

    def test_set_log_level_when_int_level_then_sets_correct_level(self) -> None:
        """Test set_log_level with integer level."""
        # Create logger
        logger = logging.getLogger(f"test_logger_{id(self)}")
        logger.setLevel(logging.INFO)
        
        # Set log level
        set_log_level(logger, logging.DEBUG)
        
        # Verify level
        assert logger.level == logging.DEBUG

    def test_set_log_level_when_string_level_then_converts_correctly(self) -> None:
        """Test set_log_level with string level."""
        # Create logger
        logger = logging.getLogger(f"test_logger_{id(self)}")
        logger.setLevel(logging.INFO)
        
        # Set log level
        set_log_level(logger, "DEBUG")
        
        # Verify level
        assert logger.level == logging.DEBUG

    def test_set_log_level_when_invalid_string_level_then_defaults_to_info(self) -> None:
        """Test set_log_level with invalid string level defaults to INFO."""
        # Create logger
        logger = logging.getLogger(f"test_logger_{id(self)}")
        logger.setLevel(logging.WARNING)
        
        # Set log level
        set_log_level(logger, "INVALID")
        
        # Verify level
        assert logger.level == logging.INFO


class TestConfigurePackageLogging:
    """Test cases for configure_package_logging function."""

    def test_configure_package_logging_when_default_params_then_configures_correctly(self) -> None:
        """Test configure_package_logging with default parameters."""
        # Configure package logging
        loggers = configure_package_logging()
        
        # Verify loggers
        assert isinstance(loggers, dict)
        assert "root" in loggers
        assert "display" in loggers
        assert "drivers" in loggers
        assert "drivers.waveshare" in loggers
        assert "rendering" in loggers
        assert "utils" in loggers
        
        # Verify root logger
        root_logger = loggers["root"]
        assert isinstance(root_logger, logging.Logger)
        assert root_logger.name == "calendarbot.display.epaper"
        assert root_logger.level == DEFAULT_LEVEL
        
        # Clean up
        for logger in loggers.values():
            logger.handlers = []

    def test_configure_package_logging_when_custom_level_then_sets_correct_level(self) -> None:
        """Test configure_package_logging with custom level."""
        # Configure package logging with custom level
        custom_level = logging.DEBUG
        loggers = configure_package_logging(level=custom_level)
        
        # Verify loggers
        for logger in loggers.values():
            assert logger.level == custom_level
        
        # Clean up
        for logger in loggers.values():
            logger.handlers = []

    @pytest.fixture
    def temp_log_file(self, tmp_path: Path) -> Path:
        """Create a temporary log file path."""
        return tmp_path / "test.log"

    def test_configure_package_logging_when_log_file_then_adds_file_handler(
        self, temp_log_file: Path
    ) -> None:
        """Test configure_package_logging with log file adds file handler."""
        # Configure package logging with log file
        loggers = configure_package_logging(log_file=str(temp_log_file))
        
        # Verify root logger has file handler
        root_logger = loggers["root"]
        assert any(isinstance(h, logging.FileHandler) for h in root_logger.handlers)
        
        # Verify log file was created
        assert temp_log_file.exists()
        
        # Clean up
        for logger in loggers.values():
            logger.handlers = []

    def test_configure_package_logging_when_no_console_then_no_console_handler(self) -> None:
        """Test configure_package_logging with console=False doesn't add console handler."""
        # Configure package logging without console handler
        loggers = configure_package_logging(console=False)
        
        # Verify root logger has no console handler
        root_logger = loggers["root"]
        assert not any(
            isinstance(h, logging.StreamHandler) and h.stream == sys.stdout for h in root_logger.handlers
        )
        
        # Clean up
        for logger in loggers.values():
            logger.handlers = []

    def test_configure_package_logging_when_called_then_returns_all_loggers(self) -> None:
        """Test configure_package_logging returns all package loggers."""
        # Configure package logging
        loggers = configure_package_logging()
        
        # Verify all loggers are returned
        expected_loggers = [
            "calendarbot.display.epaper",
            "calendarbot.display.epaper.display",
            "calendarbot.display.epaper.drivers",
            "calendarbot.display.epaper.drivers.waveshare",
            "calendarbot.display.epaper.rendering",
            "calendarbot.display.epaper.utils",
        ]
        
        for name in expected_loggers:
            assert any(logger.name == name for logger in loggers.values())
        
        # Clean up
        for logger in loggers.values():
            logger.handlers = []