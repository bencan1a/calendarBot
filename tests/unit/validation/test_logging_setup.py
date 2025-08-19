"""Minimal tests for validation logging setup - module not actively used."""

import logging
from unittest.mock import Mock, patch

import pytest

from calendarbot.validation.logging_setup import (
    ValidationFormatter,
    get_validation_logger,
    log_validation_result,
    log_validation_start,
    setup_validation_logging,
)


class TestValidationFormatterMinimal:
    """Minimal test coverage for ValidationFormatter."""

    @pytest.fixture
    def formatter(self) -> ValidationFormatter:
        """Create a ValidationFormatter for testing."""
        return ValidationFormatter(
            "%(asctime)s.%(msecs_formatted)s [%(component)8s] %(levelname)7s: %(message)s"
        )

    def test_format_basic_functionality(self, formatter: ValidationFormatter) -> None:
        """Test basic formatting functionality."""
        record = logging.LogRecord(
            name="calendarbot.sources",
            level=logging.INFO,
            pathname="sources.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        formatter.formatTime = lambda record, datefmt: "2021-01-01 00:00:00"
        record.msecs = 123.456

        result = formatter.format(record)
        assert "sources" in result
        assert "INFO" in result
        assert "Test message" in result


class TestSetupValidationLoggingMinimal:
    """Minimal test coverage for setup_validation_logging."""

    def test_setup_validation_logging_basic(self) -> None:
        """Test basic logging setup functionality."""
        with (
            patch("calendarbot.validation.logging_setup.logging.getLogger") as mock_get_logger,
            patch("calendarbot.validation.logging_setup.logging.StreamHandler"),
            patch("calendarbot.validation.logging_setup.ValidationFormatter"),
        ):
            mock_logger = Mock()
            mock_logger.handlers = []
            mock_get_logger.return_value = mock_logger

            result = setup_validation_logging()
            assert isinstance(result, dict)
            assert len(result) > 0


class TestUtilityFunctionsMinimal:
    """Minimal test coverage for utility functions."""

    def test_get_validation_logger_basic(self) -> None:
        """Test basic logger retrieval."""
        with patch("calendarbot.validation.logging_setup.logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            result = get_validation_logger("sources")
            assert result is mock_logger
            mock_get_logger.assert_called_once_with("calendarbot.sources")

    def test_log_validation_start_basic(self) -> None:
        """Test basic validation start logging."""
        mock_logger = Mock()
        log_validation_start(mock_logger, "Test Validation")
        mock_logger.info.assert_called_once()

    def test_log_validation_result_basic(self) -> None:
        """Test basic validation result logging."""
        mock_logger = Mock()
        log_validation_result(mock_logger, "Test Validation", True, "Success message")
        mock_logger.log.assert_called_once()
        assert mock_logger.log.call_args[0][0] == logging.INFO
