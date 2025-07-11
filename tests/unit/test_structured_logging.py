"""Comprehensive tests for structured logging module."""

import json
import logging
import sys
import threading
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from calendarbot.structured.logging import (
    ContextualLoggerMixin,
    CorrelationID,
    LogContext,
    LogLevel,
    StructuredFormatter,
    StructuredLogger,
    _context_storage,
    correlation_context,
    current_correlation_id,
    get_structured_logger,
    init_structured_logging,
    operation_context,
    request_context,
    with_correlation_id,
)


class TestLogLevel:
    """Test LogLevel enum functionality."""

    def test_log_level_values(self):
        """Test all log level values are correct."""
        assert LogLevel.TRACE.value == 5
        assert LogLevel.DEBUG.value == logging.DEBUG
        assert LogLevel.INFO.value == logging.INFO
        assert LogLevel.WARNING.value == logging.WARNING
        assert LogLevel.ERROR.value == logging.ERROR
        assert LogLevel.CRITICAL.value == logging.CRITICAL
        assert LogLevel.AUDIT.value == 35

    def test_log_level_enum_members(self):
        """Test enum has all expected members."""
        expected_levels = ["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "AUDIT"]
        actual_levels = [level.name for level in LogLevel]
        assert actual_levels == expected_levels


class TestCorrelationID:
    """Test CorrelationID functionality."""

    def test_correlation_id_generation(self):
        """Test correlation ID is generated properly."""
        correlation_id = CorrelationID()
        assert correlation_id.id is not None
        assert len(correlation_id.id) == 36  # UUID4 string length
        assert isinstance(correlation_id.id, str)

    def test_correlation_id_custom_value(self):
        """Test correlation ID with custom value."""
        custom_id = "custom-correlation-123"
        correlation_id = CorrelationID(custom_id)
        assert correlation_id.id == custom_id

    def test_correlation_id_string_representation(self):
        """Test string representation methods."""
        custom_id = "test-id-456"
        correlation_id = CorrelationID(custom_id)

        assert str(correlation_id) == custom_id
        assert repr(correlation_id) == f"CorrelationID('{custom_id}')"

    def test_correlation_id_generate_static_method(self):
        """Test static generate method."""
        generated_id = CorrelationID.generate()
        assert isinstance(generated_id, str)
        assert len(generated_id) == 36

    def test_correlation_id_unique_generation(self):
        """Test that generated IDs are unique."""
        ids = [CorrelationID().id for _ in range(10)]
        assert len(set(ids)) == 10  # All should be unique


class TestLogContext:
    """Test LogContext functionality."""

    def test_log_context_default_initialization(self):
        """Test default LogContext initialization."""
        context = LogContext()

        assert context.correlation_id is None
        assert context.user_id is None
        assert context.session_id is None
        assert context.request_id is None
        assert context.operation is None
        assert context.component is None
        assert context.source_file is None
        assert context.source_line is None
        assert context.function_name is None
        assert context.thread_id is None
        assert context.process_id is None
        assert context.custom_fields == {}
        assert isinstance(context.timestamp, datetime)

    def test_log_context_full_initialization(self):
        """Test LogContext with all fields."""
        correlation_id = CorrelationID("test-correlation")
        timestamp = datetime.now(timezone.utc)
        custom_fields = {"key1": "value1", "key2": "value2"}

        context = LogContext(
            correlation_id=correlation_id,
            user_id="user-123",
            session_id="session-456",
            request_id="req-789",
            operation="test_operation",
            component="test_component",
            source_file="/path/to/file.py",
            source_line=42,
            function_name="test_function",
            thread_id="thread-1",
            process_id=1234,
            custom_fields=custom_fields,
            timestamp=timestamp,
        )

        assert context.correlation_id == correlation_id
        assert context.user_id == "user-123"
        assert context.session_id == "session-456"
        assert context.request_id == "req-789"
        assert context.operation == "test_operation"
        assert context.component == "test_component"
        assert context.source_file == "/path/to/file.py"
        assert context.source_line == 42
        assert context.function_name == "test_function"
        assert context.thread_id == "thread-1"
        assert context.process_id == 1234
        assert context.custom_fields == custom_fields
        assert context.timestamp == timestamp

    def test_log_context_to_dict_empty(self):
        """Test to_dict with minimal context."""
        context = LogContext()
        result = context.to_dict()

        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)
        assert len(result) == 1  # Only timestamp

    def test_log_context_to_dict_full(self):
        """Test to_dict with full context."""
        correlation_id = CorrelationID("test-correlation")
        timestamp = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        custom_fields = {"key1": "value1", "key2": "value2"}

        context = LogContext(
            correlation_id=correlation_id,
            user_id="user-123",
            session_id="session-456",
            request_id="req-789",
            operation="test_operation",
            component="test_component",
            source_file="/path/to/file.py",
            source_line=42,
            function_name="test_function",
            thread_id="thread-1",
            process_id=1234,
            custom_fields=custom_fields,
            timestamp=timestamp,
        )

        result = context.to_dict()

        assert result["correlation_id"] == "test-correlation"
        assert result["user_id"] == "user-123"
        assert result["session_id"] == "session-456"
        assert result["request_id"] == "req-789"
        assert result["operation"] == "test_operation"
        assert result["component"] == "test_component"
        assert result["source_file"] == "/path/to/file.py"
        assert result["source_line"] == 42
        assert result["function_name"] == "test_function"
        assert result["thread_id"] == "thread-1"
        assert result["process_id"] == 1234
        assert result["timestamp"] == "2023-01-01T12:00:00+00:00"
        assert result["key1"] == "value1"
        assert result["key2"] == "value2"

    @patch("inspect.currentframe")
    @patch("threading.get_ident")
    @patch("os.getpid")
    def test_log_context_from_frame(self, mock_getpid, mock_get_ident, mock_currentframe):
        """Test LogContext.from_frame method."""
        # Mock frame data
        mock_frame = Mock()
        mock_frame.f_code.co_filename = "/test/file.py"
        mock_frame.f_code.co_name = "test_function"
        mock_frame.f_lineno = 123
        mock_frame.f_back = mock_frame

        mock_currentframe.return_value = mock_frame
        mock_get_ident.return_value = 12345
        mock_getpid.return_value = 9876

        context = LogContext.from_frame()

        assert context.source_file == "/test/file.py"
        assert context.function_name == "test_function"
        assert context.source_line == 123
        assert context.thread_id == "12345"
        assert context.process_id == 9876

    @patch("inspect.currentframe")
    def test_log_context_from_frame_with_custom_frame(self, mock_currentframe):
        """Test LogContext.from_frame with custom frame."""
        mock_frame = Mock()
        mock_frame.f_code.co_filename = "/custom/file.py"
        mock_frame.f_code.co_name = "custom_function"
        mock_frame.f_lineno = 456

        with patch("threading.get_ident", return_value=54321), patch(
            "os.getpid", return_value=6543
        ):
            context = LogContext.from_frame(mock_frame)

        assert context.source_file == "/custom/file.py"
        assert context.function_name == "custom_function"
        assert context.source_line == 456

    @patch("inspect.currentframe")
    def test_log_context_from_frame_no_frame(self, mock_currentframe):
        """Test LogContext.from_frame when no frame available."""
        mock_currentframe.return_value = None

        context = LogContext.from_frame()

        # Should still create context, but without frame-specific data
        assert context.source_file is None
        assert context.function_name is None
        assert context.source_line is None

    def test_log_context_get_current_none(self):
        """Test get_current when no context is set."""
        # Clear any existing context
        if hasattr(_context_storage, "context"):
            delattr(_context_storage, "context")

        context = LogContext.get_current()
        assert context is None

    def test_log_context_set_and_get_current(self):
        """Test setting and getting current context."""
        context = LogContext(user_id="test-user")
        context.set_current()

        retrieved_context = LogContext.get_current()
        assert retrieved_context == context
        assert retrieved_context.user_id == "test-user"

    def test_log_context_update_existing_fields(self):
        """Test updating existing context fields."""
        context = LogContext(user_id="original-user", operation="original-op")

        context.update(user_id="updated-user", operation="updated-op")

        assert context.user_id == "updated-user"
        assert context.operation == "updated-op"

    def test_log_context_update_custom_fields(self):
        """Test updating with custom fields."""
        context = LogContext()

        context.update(custom_field1="value1", custom_field2="value2")

        assert context.custom_fields["custom_field1"] == "value1"
        assert context.custom_fields["custom_field2"] == "value2"

    def test_log_context_update_mixed_fields(self):
        """Test updating both existing and custom fields."""
        context = LogContext(user_id="original-user")

        context.update(user_id="updated-user", custom_field="custom_value")

        assert context.user_id == "updated-user"
        assert context.custom_fields["custom_field"] == "custom_value"


class TestStructuredFormatter:
    """Test StructuredFormatter functionality."""

    def test_structured_formatter_initialization(self):
        """Test StructuredFormatter initialization."""
        formatter = StructuredFormatter()

        assert formatter.format_type == "json"
        assert formatter.include_context is True
        assert formatter.include_source is True
        assert formatter.timestamp_format == "%Y-%m-%d %H:%M:%S.%f"

    def test_structured_formatter_custom_initialization(self):
        """Test StructuredFormatter with custom settings."""
        formatter = StructuredFormatter(
            format_type="KEY_VALUE",
            include_context=False,
            include_source=False,
            timestamp_format="%Y-%m-%d %H:%M:%S",
        )

        assert formatter.format_type == "key_value"  # Should be lowercase
        assert formatter.include_context is False
        assert formatter.include_source is False
        assert formatter.timestamp_format == "%Y-%m-%d %H:%M:%S"

    def test_structured_formatter_json_format(self):
        """Test JSON formatting."""
        formatter = StructuredFormatter(
            format_type="json", include_context=False, include_source=False
        )

        # Create a mock log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"
        record.module = "test_module"

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.logger"
        assert parsed["message"] == "Test message"
        assert parsed["module"] == "test_module"
        assert parsed["function"] == "test_function"
        assert parsed["line"] == 123
        assert "timestamp" in parsed

    def test_structured_formatter_with_exception(self):
        """Test formatting with exception information."""
        formatter = StructuredFormatter(
            format_type="json", include_context=False, include_source=False
        )

        # Create exception info
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/path/to/file.py",
            lineno=123,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        record.funcName = "test_function"
        record.module = "test_module"

        result = formatter.format(record)
        parsed = json.loads(result)

        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"
        assert parsed["exception"]["message"] == "Test exception"
        assert "traceback" in parsed["exception"]

    def test_structured_formatter_with_context(self):
        """Test formatting with log context."""
        formatter = StructuredFormatter(
            format_type="json", include_context=True, include_source=False
        )

        # Set up context
        context = LogContext(user_id="test-user", operation="test-op")
        context.set_current()

        try:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="/path/to/file.py",
                lineno=123,
                msg="Test message",
                args=(),
                exc_info=None,
            )
            record.funcName = "test_function"
            record.module = "test_module"

            result = formatter.format(record)
            parsed = json.loads(result)

            assert "context" in parsed
            assert parsed["context"]["user_id"] == "test-user"
            assert parsed["context"]["operation"] == "test-op"
        finally:
            # Clean up context
            if hasattr(_context_storage, "context"):
                delattr(_context_storage, "context")

    def test_structured_formatter_with_source(self):
        """Test formatting with source information."""
        formatter = StructuredFormatter(
            format_type="json", include_context=False, include_source=True
        )

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"
        record.module = "test_module"

        result = formatter.format(record)
        parsed = json.loads(result)

        assert "source" in parsed
        assert parsed["source"]["file"] == "/path/to/file.py"
        assert parsed["source"]["line"] == 123
        assert parsed["source"]["function"] == "test_function"

    def test_structured_formatter_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = StructuredFormatter(
            format_type="json", include_context=False, include_source=False
        )

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"
        record.module = "test_module"

        # Add extra fields
        record.custom_field1 = "value1"
        record.custom_field2 = "value2"

        result = formatter.format(record)
        parsed = json.loads(result)

        assert "extra" in parsed
        assert parsed["extra"]["custom_field1"] == "value1"
        assert parsed["extra"]["custom_field2"] == "value2"

    def test_structured_formatter_key_value_format(self):
        """Test key-value formatting."""
        formatter = StructuredFormatter(
            format_type="key_value", include_context=False, include_source=False
        )

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"
        record.module = "test_module"

        result = formatter.format(record)

        assert "level=INFO" in result
        assert "logger=test.logger" in result
        assert "message=Test message" in result
        assert "function=test_function" in result

    def test_structured_formatter_human_readable_format(self):
        """Test human-readable formatting."""
        formatter = StructuredFormatter(
            format_type="human", include_context=False, include_source=False
        )

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"
        record.module = "test_module"

        result = formatter.format(record)

        assert "INFO" in result
        assert "test.logger" in result
        assert "Test message" in result

    def test_structured_formatter_human_readable_with_correlation(self):
        """Test human-readable formatting with correlation ID."""
        formatter = StructuredFormatter(
            format_type="human", include_context=True, include_source=False
        )

        # Set up context with correlation ID
        context = LogContext(correlation_id=CorrelationID("test-correlation"))
        context.set_current()

        try:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="/path/to/file.py",
                lineno=123,
                msg="Test message",
                args=(),
                exc_info=None,
            )
            record.funcName = "test_function"
            record.module = "test_module"

            result = formatter.format(record)

            assert "[correlation_id=test-correlation]" in result
        finally:
            # Clean up context
            if hasattr(_context_storage, "context"):
                delattr(_context_storage, "context")


class TestStructuredLogger:
    """Test StructuredLogger functionality."""

    @patch("logging.getLogger")
    def test_structured_logger_initialization(self, mock_get_logger):
        """Test StructuredLogger initialization."""
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_get_logger.return_value = mock_logger

        structured_logger = StructuredLogger("test.logger")

        assert structured_logger.name == "test.logger"
        assert structured_logger.logger == mock_logger
        assert structured_logger._context_stack == []
        mock_get_logger.assert_called_once_with("test.logger")

    @patch("logging.getLogger")
    def test_structured_logger_setup_handler(self, mock_get_logger):
        """Test structured handler setup."""
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_get_logger.return_value = mock_logger

        structured_logger = StructuredLogger("test.logger")

        # Verify handler was added
        mock_logger.addHandler.assert_called_once()
        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)

    @patch("logging.getLogger")
    def test_structured_logger_skip_existing_handler(self, mock_get_logger):
        """Test skipping handler setup when structured handler exists."""
        mock_logger = Mock()
        mock_handler = Mock()
        mock_handler.formatter = StructuredFormatter()
        mock_logger.handlers = [mock_handler]
        mock_get_logger.return_value = mock_logger

        structured_logger = StructuredLogger("test.logger")

        # Should not add another handler
        mock_logger.addHandler.assert_not_called()

    @patch("logging.getLogger")
    @patch("inspect.currentframe")
    def test_structured_logger_log_levels(self, mock_currentframe, mock_get_logger):
        """Test all log level methods."""
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_get_logger.return_value = mock_logger

        # Mock frame for context creation
        mock_frame = Mock()
        mock_frame.f_back = None
        mock_currentframe.return_value = mock_frame

        structured_logger = StructuredLogger("test.logger")

        # Test all log levels
        structured_logger.trace("Trace message")
        structured_logger.debug("Debug message")
        structured_logger.info("Info message")
        structured_logger.warning("Warning message")
        structured_logger.error("Error message")
        structured_logger.critical("Critical message")
        structured_logger.audit("Audit message")

        # Verify logger.log was called for each level
        assert mock_logger.log.call_count == 7

    @patch("logging.getLogger")
    def test_structured_logger_with_context(self, mock_get_logger):
        """Test logging with explicit context."""
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_get_logger.return_value = mock_logger

        structured_logger = StructuredLogger("test.logger")

        context = LogContext(user_id="test-user")
        structured_logger.info("Test message", context=context)

        # Verify log was called with extra context
        mock_logger.log.assert_called_once()
        args, kwargs = mock_logger.log.call_args
        assert "extra" in kwargs
        assert kwargs["extra"]["user_id"] == "test-user"

    @patch("logging.getLogger")
    def test_structured_logger_with_context_method(self, mock_get_logger):
        """Test with_context method."""
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_get_logger.return_value = mock_logger

        structured_logger = StructuredLogger("test.logger")

        contextual_logger = structured_logger.with_context(user_id="test-user", operation="test-op")

        assert isinstance(contextual_logger, StructuredLogger)
        assert contextual_logger.name == "test.logger"
        assert len(contextual_logger._context_stack) == 1

    @patch("logging.getLogger")
    def test_structured_logger_error_with_exc_info(self, mock_get_logger):
        """Test error logging with exception info."""
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_get_logger.return_value = mock_logger

        structured_logger = StructuredLogger("test.logger")

        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()

        structured_logger.error("Error occurred", exc_info=exc_info)

        # Verify log was called with exc_info
        mock_logger.log.assert_called_once()
        args, kwargs = mock_logger.log.call_args
        assert kwargs["exc_info"] == exc_info


class TestContextualLoggerMixin:
    """Test ContextualLoggerMixin functionality."""

    def test_contextual_logger_mixin_initialization(self):
        """Test ContextualLoggerMixin initialization."""

        class TestClass(ContextualLoggerMixin):
            pass

        with patch("calendarbot.structured.logging.get_structured_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            instance = TestClass()

            assert instance._structured_logger == mock_logger
            mock_get_logger.assert_called_once_with("TestClass")

    def test_contextual_logger_get_base_context(self):
        """Test get_base_context method."""

        class TestClass(ContextualLoggerMixin):
            pass

        with patch("calendarbot.structured.logging.get_structured_logger"):
            instance = TestClass()

            with patch.object(
                instance, "get_correlation_id", return_value=CorrelationID("test-id")
            ):
                context = instance.get_base_context()

                assert context.component == "TestClass"
                assert str(context.correlation_id) == "test-id"

    def test_contextual_logger_get_correlation_id_with_context(self):
        """Test get_correlation_id when context exists."""

        class TestClass(ContextualLoggerMixin):
            pass

        with patch("calendarbot.structured.logging.get_structured_logger"):
            instance = TestClass()

            correlation_id = CorrelationID("existing-id")
            context = LogContext(correlation_id=correlation_id)
            context.set_current()

            try:
                result = instance.get_correlation_id()
                assert result == correlation_id
            finally:
                if hasattr(_context_storage, "context"):
                    delattr(_context_storage, "context")

    def test_contextual_logger_get_correlation_id_no_context(self):
        """Test get_correlation_id when no context exists."""

        class TestClass(ContextualLoggerMixin):
            pass

        with patch("calendarbot.structured.logging.get_structured_logger"):
            # Clear any existing context
            if hasattr(_context_storage, "context"):
                delattr(_context_storage, "context")

            instance = TestClass()
            result = instance.get_correlation_id()
            assert result is None

    def test_contextual_logger_log_methods(self):
        """Test all log level methods."""

        class TestClass(ContextualLoggerMixin):
            pass

        mock_logger = Mock()
        with patch(
            "calendarbot.structured.logging.get_structured_logger", return_value=mock_logger
        ):
            instance = TestClass()

            # Test all log methods
            instance.log_trace("Trace message", extra_field="value")
            instance.log_debug("Debug message", extra_field="value")
            instance.log_info("Info message", extra_field="value")
            instance.log_warning("Warning message", extra_field="value")
            instance.log_error("Error message", extra_field="value")
            instance.log_critical("Critical message", extra_field="value")
            instance.log_audit("Audit message", extra_field="value")

            # Verify all methods were called
            assert mock_logger.trace.call_count == 1
            assert mock_logger.debug.call_count == 1
            assert mock_logger.info.call_count == 1
            assert mock_logger.warning.call_count == 1
            assert mock_logger.error.call_count == 1
            assert mock_logger.critical.call_count == 1
            assert mock_logger.audit.call_count == 1

    def test_contextual_logger_error_with_exc_info(self):
        """Test error logging with exception info."""

        class TestClass(ContextualLoggerMixin):
            pass

        mock_logger = Mock()
        with patch(
            "calendarbot.structured.logging.get_structured_logger", return_value=mock_logger
        ):
            instance = TestClass()

            try:
                raise ValueError("Test exception")
            except ValueError:
                exc_info = sys.exc_info()

            instance.log_error("Error occurred", exc_info=exc_info, extra_field="value")

            mock_logger.error.assert_called_once()
            args, kwargs = mock_logger.error.call_args
            assert kwargs["exc_info"] == exc_info


class TestContextManagers:
    """Test context manager functionality."""

    def test_correlation_context_auto_generated(self):
        """Test correlation_context with auto-generated ID."""
        with correlation_context() as correlation_id:
            assert isinstance(correlation_id, CorrelationID)

            current_context = LogContext.get_current()
            assert current_context is not None
            assert current_context.correlation_id == correlation_id

        # Context should be cleared after exiting
        assert LogContext.get_current() is None

    def test_correlation_context_with_string_id(self):
        """Test correlation_context with string ID."""
        test_id = "test-correlation-id"

        with correlation_context(test_id) as correlation_id:
            assert isinstance(correlation_id, CorrelationID)
            assert str(correlation_id) == test_id

            current_context = LogContext.get_current()
            assert current_context.correlation_id == correlation_id

    def test_correlation_context_with_correlation_id_object(self):
        """Test correlation_context with CorrelationID object."""
        existing_id = CorrelationID("existing-id")

        with correlation_context(existing_id) as correlation_id:
            assert correlation_id == existing_id

            current_context = LogContext.get_current()
            assert current_context.correlation_id == correlation_id

    def test_correlation_context_preserves_existing_context(self):
        """Test that correlation_context preserves existing context."""
        # Set up existing context
        existing_context = LogContext(user_id="existing-user")
        existing_context.set_current()

        try:
            with correlation_context("new-correlation") as correlation_id:
                current_context = LogContext.get_current()
                assert current_context.correlation_id.id == "new-correlation"
                assert current_context.user_id == "existing-user"  # Should be preserved

            # Original context should be restored
            restored_context = LogContext.get_current()
            assert restored_context == existing_context
            assert restored_context.user_id == "existing-user"
        finally:
            # Clean up
            if hasattr(_context_storage, "context"):
                delattr(_context_storage, "context")

    def test_request_context_full_parameters(self):
        """Test request_context with all parameters."""
        with request_context(
            request_id="req-123",
            user_id="user-456",
            session_id="session-789",
            correlation_id="corr-abc",
        ) as context:
            assert isinstance(context, LogContext)
            assert context.request_id == "req-123"
            assert context.user_id == "user-456"
            assert context.session_id == "session-789"
            assert str(context.correlation_id) == "corr-abc"

            current_context = LogContext.get_current()
            assert current_context == context

    def test_request_context_minimal_parameters(self):
        """Test request_context with minimal parameters."""
        with request_context() as context:
            assert isinstance(context, LogContext)
            assert context.correlation_id is not None
            assert context.request_id is None
            assert context.user_id is None
            assert context.session_id is None

    def test_operation_context_with_component(self):
        """Test operation_context with component."""
        with operation_context("test_operation", component="test_component") as context:
            assert isinstance(context, LogContext)
            assert context.operation == "test_operation"
            assert context.component == "test_component"
            assert context.correlation_id is not None

            current_context = LogContext.get_current()
            assert current_context == context

    def test_operation_context_with_existing_correlation(self):
        """Test operation_context preserving existing correlation ID."""
        # Set up existing context with correlation ID
        existing_correlation = CorrelationID("existing-correlation")
        existing_context = LogContext(correlation_id=existing_correlation)
        existing_context.set_current()

        try:
            with operation_context("new_operation") as context:
                assert context.operation == "new_operation"
                assert context.correlation_id == existing_correlation
        finally:
            # Clean up
            if hasattr(_context_storage, "context"):
                delattr(_context_storage, "context")

    def test_operation_context_with_kwargs(self):
        """Test operation_context with additional keyword arguments."""
        with operation_context(
            "test_op", component="test_comp", custom_field="custom_value"
        ) as context:
            assert context.operation == "test_op"
            assert context.component == "test_comp"
            assert context.custom_fields["custom_field"] == "custom_value"


class TestDecorators:
    """Test decorator functionality."""

    def test_with_correlation_id_decorator_no_id(self):
        """Test @with_correlation_id decorator without ID."""

        @with_correlation_id()
        def test_function():
            context = LogContext.get_current()
            assert context is not None
            assert context.correlation_id is not None
            return str(context.correlation_id)

        result = test_function()
        assert isinstance(result, str)
        assert len(result) == 36  # UUID length

        # Context should be cleared after function
        assert LogContext.get_current() is None

    def test_with_correlation_id_decorator_with_string_id(self):
        """Test @with_correlation_id decorator with string ID."""

        @with_correlation_id("decorator-test-id")
        def test_function():
            context = LogContext.get_current()
            return str(context.correlation_id)

        result = test_function()
        assert result == "decorator-test-id"

    def test_with_correlation_id_decorator_with_correlation_id_object(self):
        """Test @with_correlation_id decorator with CorrelationID object."""
        test_correlation = CorrelationID("object-test-id")

        @with_correlation_id(test_correlation)
        def test_function():
            context = LogContext.get_current()
            return context.correlation_id

        result = test_function()
        assert result == test_correlation

    def test_with_correlation_id_decorator_preserves_return_value(self):
        """Test decorator preserves function return value."""

        @with_correlation_id()
        def test_function(x, y):
            return x + y

        result = test_function(5, 10)
        assert result == 15

    def test_with_correlation_id_decorator_preserves_exceptions(self):
        """Test decorator preserves exceptions."""

        @with_correlation_id()
        def test_function():
            raise ValueError("Test exception")

        with pytest.raises(ValueError, match="Test exception"):
            test_function()


class TestGlobalFunctions:
    """Test global utility functions."""

    def test_current_correlation_id_with_context(self):
        """Test current_correlation_id when context exists."""
        correlation_id = CorrelationID("test-current-id")
        context = LogContext(correlation_id=correlation_id)
        context.set_current()

        try:
            result = current_correlation_id()
            assert result == correlation_id
        finally:
            if hasattr(_context_storage, "context"):
                delattr(_context_storage, "context")

    def test_current_correlation_id_no_context(self):
        """Test current_correlation_id when no context exists."""
        # Clear any existing context
        if hasattr(_context_storage, "context"):
            delattr(_context_storage, "context")

        result = current_correlation_id()
        assert result is None

    @patch("logging.getLogger")
    def test_get_structured_logger_new(self, mock_get_logger):
        """Test get_structured_logger creates new logger."""
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_get_logger.return_value = mock_logger

        # Reset global logger
        import calendarbot.structured.logging as logging_module

        logging_module._structured_logger = None

        result = get_structured_logger("test.logger")

        assert isinstance(result, StructuredLogger)
        assert result.name == "test.logger"

    @patch("logging.getLogger")
    def test_get_structured_logger_reuse_existing(self, mock_get_logger):
        """Test get_structured_logger reuses existing logger with same name."""
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_get_logger.return_value = mock_logger

        # Create initial logger
        logger1 = get_structured_logger("same.logger")
        logger2 = get_structured_logger("same.logger")

        assert logger1 == logger2

    @patch("logging.getLogger")
    def test_get_structured_logger_different_name(self, mock_get_logger):
        """Test get_structured_logger creates new logger for different name."""
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_get_logger.return_value = mock_logger

        logger1 = get_structured_logger("logger1")
        logger2 = get_structured_logger("logger2")

        assert logger1.name != logger2.name

    @patch("logging.addLevelName")
    @patch("logging.getLogger")
    def test_init_structured_logging(self, mock_get_logger, mock_add_level_name):
        """Test init_structured_logging function."""
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_get_logger.return_value = mock_logger

        mock_settings = Mock()
        result = init_structured_logging(mock_settings)

        assert isinstance(result, StructuredLogger)
        assert result.name == "calendarbot.structured"

        # Verify custom log levels were added
        mock_add_level_name.assert_any_call(LogLevel.TRACE.value, "TRACE")
        mock_add_level_name.assert_any_call(LogLevel.AUDIT.value, "AUDIT")


class TestThreadSafety:
    """Test thread safety of context management."""

    def test_context_isolation_between_threads(self):
        """Test that contexts are isolated between threads."""
        results = {}

        def thread_function(thread_id):
            correlation_id = CorrelationID(f"thread-{thread_id}")
            context = LogContext(correlation_id=correlation_id, user_id=f"user-{thread_id}")
            context.set_current()

            # Simulate some work
            import time

            time.sleep(0.1)

            # Get current context
            current_context = LogContext.get_current()
            results[thread_id] = {
                "correlation_id": str(current_context.correlation_id) if current_context else None,
                "user_id": current_context.user_id if current_context else None,
            }

        # Create and start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=thread_function, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify each thread had its own context
        for i in range(3):
            assert results[i]["correlation_id"] == f"thread-{i}"
            assert results[i]["user_id"] == f"user-{i}"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_log_context_to_dict_with_none_values(self):
        """Test to_dict handles None values correctly."""
        context = LogContext(correlation_id=None, user_id=None, source_line=None, process_id=None)

        result = context.to_dict()

        # Should only contain timestamp
        assert len(result) == 1
        assert "timestamp" in result

    def test_structured_formatter_with_corrupted_extra(self):
        """Test formatter handles corrupted extra data."""
        formatter = StructuredFormatter(format_type="json")

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"
        record.module = "test_module"

        # Add non-dict extra data
        record.custom_field = "value"

        # Should handle gracefully and not crash
        result = formatter.format(record)
        parsed = json.loads(result)

        assert "extra" in parsed
        assert parsed["extra"]["custom_field"] == "value"

    def test_context_manager_exception_handling(self):
        """Test context managers handle exceptions properly."""
        original_context = LogContext(user_id="original")
        original_context.set_current()

        try:
            with correlation_context("test-id"):
                # Verify context is set
                current = LogContext.get_current()
                assert str(current.correlation_id) == "test-id"

                # Raise exception
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Original context should be restored even after exception
        restored = LogContext.get_current()
        assert restored.user_id == "original"

        # Clean up
        if hasattr(_context_storage, "context"):
            delattr(_context_storage, "context")

    @patch("inspect.currentframe")
    def test_log_context_from_frame_exception_handling(self, mock_currentframe):
        """Test LogContext.from_frame with threading exception propagation."""
        # Mock frame that raises exception when accessed
        mock_frame = Mock()
        mock_frame.f_back = None
        mock_frame.f_code.co_filename = "/test/file.py"
        mock_frame.f_code.co_name = "test_function"
        mock_frame.f_lineno = 123

        # Test that threading.get_ident exception propagates (realistic behavior)
        with patch("threading.get_ident", side_effect=RuntimeError("Thread error")):
            # Should raise the exception since there's no handling in the actual implementation
            with pytest.raises(RuntimeError, match="Thread error"):
                LogContext.from_frame(mock_frame)
