"""Tests for validation logging setup."""

import logging
import os
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from calendarbot.validation.logging_setup import (
    ComponentFilter,
    ValidationFormatter,
    get_validation_logger,
    log_validation_result,
    log_validation_start,
    setup_validation_logging,
)


class TestValidationFormatter:
    """Test suite for ValidationFormatter."""

    @pytest.fixture
    def formatter(self) -> ValidationFormatter:
        """Create a ValidationFormatter for testing."""
        return ValidationFormatter("%(asctime)s.%(msecs_formatted)s [%(component)8s] %(levelname)7s: %(message)s")

    def test_format_when_valid_record_then_adds_custom_fields(self, formatter: ValidationFormatter) -> None:
        """Test format adds custom fields to the log record."""
        # Arrange
        record = logging.LogRecord(
            name="calendarbot.sources",
            level=logging.INFO,
            pathname="sources.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        # Override the asctime to avoid timezone issues in testing
        formatter.formatTime = lambda record, datefmt: "2021-01-01 00:00:00"
        record.msecs = 123.456

        # Act
        result = formatter.format(record)

        # Assert
        assert "sources" in result
        assert "INFO" in result
        assert "Test message" in result
        assert "123" in result  # Just check for the milliseconds

    def test_format_when_non_calendarbot_logger_then_uses_system_component(self, formatter: ValidationFormatter) -> None:
        """Test format uses 'system' component for non-calendarbot loggers."""
        # Arrange
        record = logging.LogRecord(
            name="requests",
            level=logging.INFO,
            pathname="requests.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Act
        result = formatter.format(record)

        # Assert
        assert "system" in result

    def test_format_when_msecs_none_then_handles_gracefully(self, formatter: ValidationFormatter) -> None:
        """Test format handles None msecs gracefully."""
        # Arrange
        record = logging.LogRecord(
            name="calendarbot.sources",
            level=logging.INFO,
            pathname="sources.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        
        # Override the asctime to avoid timezone issues in testing
        formatter.formatTime = lambda record, datefmt: "2021-01-01 00:00:00"
        
        # We need to delete msecs attribute rather than setting to None
        # to properly test the exception handling
        if hasattr(record, 'msecs'):
            delattr(record, 'msecs')

        # Act
        result = formatter.format(record)

        # Assert
        assert "000" in result  # Check for zero milliseconds

    def test_format_when_name_none_then_handles_gracefully(self, formatter: ValidationFormatter) -> None:
        """Test format handles None name gracefully."""
        # Arrange
        record = logging.LogRecord(
            name=None,  # type: ignore
            level=logging.INFO,
            pathname="sources.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Act
        result = formatter.format(record)

        # Assert
        assert "system" in result


class TestComponentFilter:
    """Test suite for ComponentFilter."""

    @pytest.fixture
    def filter_all(self) -> ComponentFilter:
        """Create a ComponentFilter that allows all components."""
        return ComponentFilter([])

    @pytest.fixture
    def filter_sources(self) -> ComponentFilter:
        """Create a ComponentFilter that allows only sources component."""
        return ComponentFilter(["sources"])

    def test_filter_when_no_allowed_components_then_allows_all(self, filter_all: ComponentFilter) -> None:
        """Test filter allows all records when no components are specified."""
        # Arrange
        record = logging.LogRecord(
            name="calendarbot.sources",
            level=logging.INFO,
            pathname="sources.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Act
        result = filter_all.filter(record)

        # Assert
        assert result is True

    def test_filter_when_component_allowed_then_allows_record(self, filter_sources: ComponentFilter) -> None:
        """Test filter allows records from allowed components."""
        # Arrange
        record = logging.LogRecord(
            name="calendarbot.sources",
            level=logging.INFO,
            pathname="sources.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Act
        result = filter_sources.filter(record)

        # Assert
        assert result is True

    def test_filter_when_component_not_allowed_then_blocks_record(self, filter_sources: ComponentFilter) -> None:
        """Test filter blocks records from non-allowed components."""
        # Arrange
        record = logging.LogRecord(
            name="calendarbot.cache",
            level=logging.INFO,
            pathname="cache.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Act
        result = filter_sources.filter(record)

        # Assert
        assert result is False

    def test_filter_when_system_allowed_then_allows_external_loggers(self) -> None:
        """Test filter allows external loggers when system is allowed."""
        # Arrange
        filter_with_system = ComponentFilter(["sources", "system"])
        record = logging.LogRecord(
            name="requests",
            level=logging.INFO,
            pathname="requests.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Act
        result = filter_with_system.filter(record)

        # Assert
        assert result is True

    def test_filter_when_system_not_allowed_then_blocks_external_loggers(self, filter_sources: ComponentFilter) -> None:
        """Test filter blocks external loggers when system is not allowed."""
        # Arrange
        record = logging.LogRecord(
            name="requests",
            level=logging.INFO,
            pathname="requests.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Act
        result = filter_sources.filter(record)

        # Assert
        assert result is False


class TestSetupValidationLogging:
    """Test suite for setup_validation_logging function."""

    def test_setup_validation_logging_when_default_params_then_configures_correctly(self) -> None:
        """Test setup_validation_logging configures logging with default parameters."""
        # Arrange
        mock_root_logger = Mock()
        mock_root_logger.handlers = []
        mock_component_loggers = {}
        
        # Act
        with patch("calendarbot.validation.logging_setup.logging.getLogger") as mock_get_logger:
            # Setup mock to return different loggers for different calls
            def get_logger_side_effect(name=None):
                if name is None:
                    return mock_root_logger
                mock_logger = Mock()
                mock_component_loggers[name] = mock_logger
                return mock_logger
                
            mock_get_logger.side_effect = get_logger_side_effect
            
            with patch("calendarbot.validation.logging_setup.logging.StreamHandler") as mock_stream_handler, \
                 patch("calendarbot.validation.logging_setup.ValidationFormatter") as mock_formatter:
                
                result = setup_validation_logging()
                
                # Assert
                assert isinstance(result, dict)
                assert set(result.keys()) >= {"sources", "cache", "display", "validation", "system"}
                mock_stream_handler.assert_called_once()
                assert mock_formatter.call_count >= 1
                assert mock_root_logger.addHandler.call_count >= 1

    def test_setup_validation_logging_when_verbose_then_uses_debug_level(self) -> None:
        """Test setup_validation_logging uses DEBUG level when verbose is True."""
        # Arrange
        mock_handler = Mock()
        
        # Act
        with patch("calendarbot.validation.logging_setup.logging.getLogger"), \
             patch("calendarbot.validation.logging_setup.logging.StreamHandler", return_value=mock_handler), \
             patch("calendarbot.validation.logging_setup.ValidationFormatter"):
            
            setup_validation_logging(verbose=True)
            
            # Assert
            mock_handler.setLevel.assert_called_with(logging.DEBUG)

    def test_setup_validation_logging_when_components_specified_then_adds_filter(self) -> None:
        """Test setup_validation_logging adds ComponentFilter when components are specified."""
        # Arrange
        mock_handler = Mock()
        
        # Act
        with patch("calendarbot.validation.logging_setup.logging.getLogger"), \
             patch("calendarbot.validation.logging_setup.logging.StreamHandler", return_value=mock_handler), \
             patch("calendarbot.validation.logging_setup.ValidationFormatter"), \
             patch("calendarbot.validation.logging_setup.ComponentFilter") as mock_filter_cls:
            
            setup_validation_logging(components=["sources", "cache"])
            
            # Assert
            mock_filter_cls.assert_called_with(["sources", "cache", "system"])
            assert mock_handler.addFilter.call_count == 1

    def test_setup_validation_logging_when_log_file_then_adds_file_handler(self) -> None:
        """Test setup_validation_logging adds FileHandler when log_file is specified."""
        # Arrange
        mock_logger = Mock()
        mock_logger.handlers = []
        
        # Act
        with patch("calendarbot.validation.logging_setup.logging.getLogger", return_value=mock_logger), \
             patch("calendarbot.validation.logging_setup.logging.StreamHandler"), \
             patch("calendarbot.validation.logging_setup.logging.handlers.RotatingFileHandler") as mock_file_handler, \
             patch("calendarbot.validation.logging_setup.ValidationFormatter"):
            
            # Skip the Path mock and just verify the handler is called with the right arguments
            setup_validation_logging(log_file="test.log")
            
            # Assert
            mock_file_handler.assert_called_once()
            # Just check that the first argument contains test.log
            assert mock_file_handler.call_args.args[0] == "test.log" or "test.log" in str(mock_file_handler.call_args)


class TestGetValidationLogger:
    """Test suite for get_validation_logger function."""

    def test_get_validation_logger_when_valid_component_then_returns_logger(self) -> None:
        """Test get_validation_logger returns a logger for a valid component."""
        # Arrange
        mock_logger = Mock()
        
        # Act
        with patch("calendarbot.validation.logging_setup.logging.getLogger", return_value=mock_logger) as mock_get_logger:
            result = get_validation_logger("sources")
            
            # Assert
            assert result is mock_logger
            mock_get_logger.assert_called_once_with("calendarbot.sources")

    def test_get_validation_logger_when_custom_component_then_returns_logger(self) -> None:
        """Test get_validation_logger returns a logger for a custom component."""
        # Arrange
        mock_logger = Mock()
        
        # Act
        with patch("calendarbot.validation.logging_setup.logging.getLogger", return_value=mock_logger) as mock_get_logger:
            result = get_validation_logger("custom_component")
            
            # Assert
            assert result is mock_logger
            mock_get_logger.assert_called_once_with("calendarbot.custom_component")


class TestLogValidationStart:
    """Test suite for log_validation_start function."""

    def test_log_validation_start_when_basic_info_then_logs_correctly(self) -> None:
        """Test log_validation_start logs basic validation start information."""
        # Arrange
        mock_logger = Mock()
        
        # Act
        log_validation_start(mock_logger, "Test Validation")
            
        # Assert
        mock_logger.info.assert_called_once()
        assert "Starting validation" in mock_logger.info.call_args[0][0]
        assert "Test Validation" in mock_logger.info.call_args[0][0]

    def test_log_validation_start_when_details_provided_then_logs_details(self) -> None:
        """Test log_validation_start logs validation details when provided."""
        # Arrange
        mock_logger = Mock()
        details = {"source": "test_source", "count": 42}
        
        # Act
        log_validation_start(mock_logger, "Test Validation", details)
            
        # Assert
        mock_logger.info.assert_called_once()
        assert "Starting validation" in mock_logger.info.call_args[0][0]
        assert "Test Validation" in mock_logger.info.call_args[0][0]
        
        # Check that debug was called for each detail
        assert mock_logger.debug.call_count == len(details)
        for key, value in details.items():
            debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
            assert any(f"  {key}: {value}" in call for call in debug_calls)


class TestLogValidationResult:
    """Test suite for log_validation_result function."""

    def test_log_validation_result_when_success_then_logs_at_info_level(self) -> None:
        """Test log_validation_result logs success at INFO level."""
        # Arrange
        mock_logger = Mock()
        
        # Act
        log_validation_result(mock_logger, "Test Validation", True, "Success message")
            
        # Assert
        assert mock_logger.log.call_count == 1
        # First arg is level, should be INFO
        assert mock_logger.log.call_args[0][0] == logging.INFO
        # Second arg is message
        message = mock_logger.log.call_args[0][1]
        assert "PASSED" in message
        assert "Test Validation" in message
        assert "Success message" in message

    def test_log_validation_result_when_failure_then_logs_at_error_level(self) -> None:
        """Test log_validation_result logs failure at ERROR level."""
        # Arrange
        mock_logger = Mock()
        
        # Act
        log_validation_result(mock_logger, "Test Validation", False, "Validation failed")
            
        # Assert
        assert mock_logger.log.call_count == 1
        # First arg is level, should be ERROR
        assert mock_logger.log.call_args[0][0] == logging.ERROR
        # Second arg is message
        message = mock_logger.log.call_args[0][1]
        assert "FAILED" in message
        assert "Test Validation" in message
        assert "Validation failed" in message

    def test_log_validation_result_when_duration_provided_then_includes_duration(self) -> None:
        """Test log_validation_result includes duration when provided."""
        # Arrange
        mock_logger = Mock()
        
        # Act
        log_validation_result(mock_logger, "Test Validation", True, "Success message", duration_ms=123.45)
            
        # Assert
        assert mock_logger.log.call_count == 1
        # Check message includes duration
        message = mock_logger.log.call_args[0][1]
        assert "123.45ms" in message