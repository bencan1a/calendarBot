"""Unit tests for calendarbot.validation.logging_setup module."""

import logging
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

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
    """Test ValidationFormatter class functionality."""

    def test_formatter_initialization(self):
        """Test ValidationFormatter initialization."""
        formatter = ValidationFormatter()
        assert isinstance(formatter, logging.Formatter)

    def test_format_with_normal_record(self):
        """Test format method with normal log record."""
        formatter = ValidationFormatter("%(component)s - %(message)s")

        record = logging.LogRecord(
            name="calendarbot.sources",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.msecs = 123.456

        result = formatter.format(record)

        assert "sources" in result
        assert "Test message" in result
        assert hasattr(record, "msecs_formatted")
        assert getattr(record, "msecs_formatted") == "123"
        assert hasattr(record, "component")
        assert getattr(record, "component") == "sources"

    def test_format_with_none_msecs(self):
        """Test format method when msecs is None."""
        formatter = ValidationFormatter("%(msecs_formatted)s")

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.msecs = None

        result = formatter.format(record)

        assert hasattr(record, "msecs_formatted")
        assert getattr(record, "msecs_formatted") == "000"

    def test_format_with_invalid_msecs(self):
        """Test format method when msecs causes ValueError."""
        formatter = ValidationFormatter("%(msecs_formatted)s")

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.msecs = "invalid"

        result = formatter.format(record)

        assert hasattr(record, "msecs_formatted")
        assert getattr(record, "msecs_formatted") == "000"

    def test_format_with_calendarbot_logger(self):
        """Test format method with calendarbot logger names."""
        formatter = ValidationFormatter("%(component)s")

        record = logging.LogRecord(
            name="calendarbot.cache",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        assert hasattr(record, "component")
        assert getattr(record, "component") == "cache"

    def test_format_with_non_calendarbot_logger(self):
        """Test format method with non-calendarbot logger names."""
        formatter = ValidationFormatter("%(component)s")

        record = logging.LogRecord(
            name="external.library",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        assert hasattr(record, "component")
        assert getattr(record, "component") == "system"

    def test_format_with_none_name(self):
        """Test format method when logger name is None."""
        formatter = ValidationFormatter("%(component)s")

        record = logging.LogRecord(
            name="",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        assert hasattr(record, "component")
        assert getattr(record, "component") == "system"

    def test_format_with_short_logger_name(self):
        """Test format method with single-part logger name."""
        formatter = ValidationFormatter("%(component)s")

        record = logging.LogRecord(
            name="root",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        assert hasattr(record, "component")
        assert getattr(record, "component") == "system"

    def test_format_handles_attribute_error(self):
        """Test format method handles AttributeError gracefully."""
        formatter = ValidationFormatter("%(component)s")

        # Create a mock record that raises AttributeError
        record = Mock()

        # DIAGNOSTIC: Properly configure Mock to simulate LogRecord with AttributeError
        # Set all required string attributes that logging formatter expects
        record.exc_text = ""
        record.exc_info = None
        record.stack_info = None
        record.getMessage.return_value = "Test message"

        # Configure the mock to raise AttributeError when name is accessed
        def raise_attribute_error():
            raise AttributeError("No name")

        type(record).name = property(raise_attribute_error)

        # Should not raise exception and set component to system
        result = formatter.format(record)

        assert hasattr(record, "component")
        assert record.component == "system"


class TestComponentFilter:
    """Test ComponentFilter class functionality."""

    def test_component_filter_initialization_with_components(self):
        """Test ComponentFilter initialization with allowed components."""
        allowed = ["sources", "cache"]
        filter_instance = ComponentFilter(allowed)

        assert filter_instance.allowed_components == {"sources", "cache"}

    def test_component_filter_initialization_none(self):
        """Test ComponentFilter initialization with None (allow all)."""
        filter_instance = ComponentFilter(None)

        assert filter_instance.allowed_components is None

    def test_filter_allows_all_when_none(self):
        """Test filter allows all records when allowed_components is None."""
        filter_instance = ComponentFilter(None)

        record = Mock()
        record.name = "any.logger"

        assert filter_instance.filter(record) is True

    def test_filter_allows_calendarbot_component(self):
        """Test filter allows calendarbot component when in allowed list."""
        filter_instance = ComponentFilter(["sources"])

        record = Mock()
        record.name = "calendarbot.sources"

        assert filter_instance.filter(record) is True

    def test_filter_blocks_calendarbot_component(self):
        """Test filter blocks calendarbot component when not in allowed list."""
        filter_instance = ComponentFilter(["sources"])

        record = Mock()
        record.name = "calendarbot.cache"

        assert filter_instance.filter(record) is False

    def test_filter_allows_system_logs(self):
        """Test filter allows system logs when system is in allowed list."""
        filter_instance = ComponentFilter(["system"])

        record = Mock()
        record.name = "external.library"

        assert filter_instance.filter(record) is True

    def test_filter_blocks_system_logs(self):
        """Test filter blocks system logs when system not in allowed list."""
        filter_instance = ComponentFilter(["sources"])

        record = Mock()
        record.name = "external.library"

        assert filter_instance.filter(record) is False

    def test_filter_with_short_logger_name(self):
        """Test filter with single-part logger name."""
        filter_instance = ComponentFilter(["system"])

        record = Mock()
        record.name = "root"

        assert filter_instance.filter(record) is True


class TestSetupValidationLogging:
    """Test setup_validation_logging function."""

    def setUp(self):
        """Clear logging handlers before each test."""
        # Clear root logger handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def test_setup_validation_logging_defaults(self):
        """Test setup_validation_logging with default parameters."""
        self.setUp()

        result = setup_validation_logging()

        assert isinstance(result, dict)
        assert "sources" in result
        assert "cache" in result
        assert "display" in result
        assert "validation" in result
        assert "system" in result

        # Check that loggers are properly configured
        assert result["sources"].name == "calendarbot.sources"
        assert result["sources"].level == logging.DEBUG

    def test_setup_validation_logging_verbose(self):
        """Test setup_validation_logging with verbose mode."""
        self.setUp()

        result = setup_validation_logging(verbose=True)

        # Should configure for DEBUG level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_setup_validation_logging_with_components(self):
        """Test setup_validation_logging with specific components."""
        self.setUp()

        result = setup_validation_logging(components=["sources", "cache"])

        # Should still return all component loggers
        assert "sources" in result
        assert "cache" in result
        assert "display" in result
        assert "validation" in result

    def test_setup_validation_logging_with_log_file(self):
        """Test setup_validation_logging with log file."""
        self.setUp()

        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"

            result = setup_validation_logging(log_file=str(log_file))

            # Should have created log file directory
            assert log_file.parent.exists()

            # Should have added file handler
            root_logger = logging.getLogger()
            file_handlers = [
                h
                for h in root_logger.handlers
                if isinstance(h, logging.handlers.RotatingFileHandler)
            ]
            assert len(file_handlers) > 0

    def test_setup_validation_logging_clears_existing_handlers(self):
        """Test that setup_validation_logging clears existing handlers."""
        # Add a handler first
        root_logger = logging.getLogger()
        old_handler = logging.StreamHandler()
        root_logger.addHandler(old_handler)

        initial_count = len(root_logger.handlers)
        assert initial_count > 0

        setup_validation_logging()

        # Should have cleared old handlers and added new ones
        assert old_handler not in root_logger.handlers

    def test_setup_validation_logging_configures_third_party_loggers(self):
        """Test that third-party loggers are configured to reduce noise."""
        self.setUp()

        setup_validation_logging()

        # Check that third-party loggers are set to WARNING level
        assert logging.getLogger("aiohttp").level == logging.WARNING
        assert logging.getLogger("urllib3").level == logging.WARNING
        assert logging.getLogger("msal").level == logging.WARNING
        assert logging.getLogger("asyncio").level == logging.WARNING


class TestUtilityFunctions:
    """Test utility functions."""

    def test_get_validation_logger(self):
        """Test get_validation_logger function."""
        logger = get_validation_logger("sources")

        assert logger.name == "calendarbot.sources"
        assert isinstance(logger, logging.Logger)

    def test_get_validation_logger_different_components(self):
        """Test get_validation_logger with different components."""
        components = ["sources", "cache", "display", "validation"]

        for component in components:
            logger = get_validation_logger(component)
            assert logger.name == f"calendarbot.{component}"

    def test_log_validation_start_basic(self):
        """Test log_validation_start with basic parameters."""
        mock_logger = Mock()

        log_validation_start(mock_logger, "test_validation")

        mock_logger.info.assert_called_once_with("Starting validation: test_validation")

    def test_log_validation_start_with_details(self):
        """Test log_validation_start with details."""
        mock_logger = Mock()
        details = {"param1": "value1", "param2": "value2"}

        log_validation_start(mock_logger, "test_validation", details)

        mock_logger.info.assert_called_once_with("Starting validation: test_validation")
        assert mock_logger.debug.call_count == 2
        mock_logger.debug.assert_any_call("  param1: value1")
        mock_logger.debug.assert_any_call("  param2: value2")

    def test_log_validation_result_success(self):
        """Test log_validation_result with successful result."""
        mock_logger = Mock()

        log_validation_result(mock_logger, "test_validation", True, "Success message")

        mock_logger.log.assert_called_once_with(
            logging.INFO, "Validation PASSED: test_validation - Success message"
        )

    def test_log_validation_result_failure(self):
        """Test log_validation_result with failed result."""
        mock_logger = Mock()

        log_validation_result(mock_logger, "test_validation", False, "Failure message")

        mock_logger.log.assert_called_once_with(
            logging.ERROR, "Validation FAILED: test_validation - Failure message"
        )

    def test_log_validation_result_with_duration(self):
        """Test log_validation_result with duration."""
        mock_logger = Mock()

        log_validation_result(
            mock_logger, "test_validation", True, "Success message", duration_ms=150
        )

        mock_logger.log.assert_called_once_with(
            logging.INFO, "Validation PASSED: test_validation - Success message (150ms)"
        )

    def test_log_validation_result_without_duration(self):
        """Test log_validation_result without duration."""
        mock_logger = Mock()

        log_validation_result(mock_logger, "test_validation", True, "Success message", None)

        mock_logger.log.assert_called_once_with(
            logging.INFO, "Validation PASSED: test_validation - Success message"
        )


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    def test_complete_logging_setup_flow(self):
        """Test complete logging setup and usage flow."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Setup logging
        loggers = setup_validation_logging(verbose=True, components=["sources"])

        # Get logger and use it
        sources_logger = loggers["sources"]

        # Capture output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(ValidationFormatter("%(component)s: %(message)s"))
        sources_logger.addHandler(handler)

        # Log some messages
        log_validation_start(sources_logger, "test", {"detail": "value"})
        log_validation_result(sources_logger, "test", True, "success", 100)

        # Check output
        output = stream.getvalue()
        assert "sources:" in output

    def test_formatter_and_filter_integration(self):
        """Test ValidationFormatter and ComponentFilter working together."""
        formatter = ValidationFormatter("%(component)s - %(levelname)s - %(message)s")
        component_filter = ComponentFilter(["sources"])

        # Create a handler with both formatter and filter
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(formatter)
        handler.addFilter(component_filter)

        logger = logging.getLogger("calendarbot.sources")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        # Log a message that should pass the filter
        logger.info("Test message")

        output = stream.getvalue()
        assert "sources - INFO - Test message" in output

        # Clear the stream for next test
        stream.truncate(0)
        stream.seek(0)

        # Log from a filtered-out logger
        blocked_logger = logging.getLogger("calendarbot.cache")
        blocked_logger.addHandler(handler)
        blocked_logger.info("Blocked message")

        # Should be empty since cache is not in allowed components
        output = stream.getvalue()
        assert "Blocked message" not in output

    def test_error_handling_in_formatter(self):
        """Test error handling in ValidationFormatter."""
        formatter = ValidationFormatter("%(component)s - %(message)s")

        # Create a properly configured mock record that simulates missing attributes
        record = Mock()
        record.name = "calendarbot.test"
        record.getMessage.return_value = "Test message"

        # DIAGNOSTIC: Properly configure Mock to behave like a LogRecord
        # Set required attributes that logging formatter expects as strings
        record.exc_text = ""  # Must be string, not Mock
        record.exc_info = None
        record.stack_info = None

        # Remove msecs attribute to test missing attribute handling
        if hasattr(record, "msecs"):
            del record.msecs

        # Should not raise exception
        try:
            result = formatter.format(record)
            assert hasattr(record, "component")
            assert hasattr(record, "msecs_formatted")
        except Exception as e:
            pytest.fail(f"Formatter should handle missing attributes gracefully: {e}")
