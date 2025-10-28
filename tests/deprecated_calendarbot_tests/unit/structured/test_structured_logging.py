"""Comprehensive tests for structured logging module."""

import json
import logging
import sys
import threading
from datetime import datetime, timezone
from unittest.mock import Mock, patch

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


@pytest.fixture(autouse=True)
def clean_context():
    """Automatically clean up context storage after each test."""
    yield
    if hasattr(_context_storage, "context"):
        delattr(_context_storage, "context")


@pytest.fixture
def mock_frame():
    """Reusable mock frame for testing."""
    frame = Mock()
    frame.f_code.co_filename = "/test/file.py"
    frame.f_code.co_name = "test_function"
    frame.f_lineno = 123
    frame.f_back = frame
    return frame


@pytest.fixture
def mock_logger():
    """Reusable mock logger."""
    logger = Mock()
    logger.handlers = []
    return logger


@pytest.fixture
def sample_log_record():
    """Sample log record for formatter testing."""
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
    return record


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

    @patch("threading.get_ident", return_value=12345)
    @patch("os.getpid", return_value=9876)
    @patch("inspect.currentframe")
    def test_log_context_from_frame(
        self, mock_currentframe, mock_getpid, mock_get_ident, mock_frame
    ):
        """Test LogContext.from_frame method."""
        mock_currentframe.return_value = mock_frame
        context = LogContext.from_frame()

        assert context.source_file == "/test/file.py"
        assert context.function_name == "test_function"
        assert context.source_line == 123
        assert context.thread_id == "12345"
        assert context.process_id == 9876

    @patch("threading.get_ident", return_value=54321)
    @patch("os.getpid", return_value=6543)
    def test_log_context_from_frame_with_custom_frame(self, mock_getpid, mock_get_ident):
        """Test LogContext.from_frame with custom frame."""
        custom_frame = Mock()
        custom_frame.f_code.co_filename = "/custom/file.py"
        custom_frame.f_code.co_name = "custom_function"
        custom_frame.f_lineno = 456

        context = LogContext.from_frame(custom_frame)
        assert context.source_file == "/custom/file.py"
        assert context.function_name == "custom_function"
        assert context.source_line == 456

    @patch("inspect.currentframe", return_value=None)
    def test_log_context_from_frame_no_frame(self, mock_currentframe):
        """Test LogContext.from_frame when no frame available."""
        context = LogContext.from_frame()
        assert context.source_file is None
        assert context.function_name is None
        assert context.source_line is None

    def test_log_context_get_current_none(self):
        """Test get_current when no context is set."""
        context = LogContext.get_current()
        assert context is None

    def test_log_context_set_and_get_current(self):
        """Test setting and getting current context."""
        context = LogContext(user_id="test-user")
        context.set_current()

        retrieved_context = LogContext.get_current()
        assert retrieved_context == context
        assert retrieved_context.user_id == "test-user"

    @pytest.mark.parametrize(
        "original,updates,expected",
        [
            (
                {"user_id": "original", "operation": "orig-op"},
                {"user_id": "updated", "operation": "new-op"},
                {"user_id": "updated", "operation": "new-op"},
            ),
            (
                {},
                {"custom_field1": "value1", "custom_field2": "value2"},
                {"custom_fields": {"custom_field1": "value1", "custom_field2": "value2"}},
            ),
            (
                {"user_id": "original"},
                {"user_id": "updated", "custom_field": "custom_value"},
                {"user_id": "updated", "custom_fields": {"custom_field": "custom_value"}},
            ),
        ],
    )
    def test_log_context_update(self, original, updates, expected):
        """Test updating context fields."""
        context = LogContext(**original)
        context.update(**updates)

        for key, value in expected.items():
            if key == "custom_fields":
                assert context.custom_fields == value
            else:
                assert getattr(context, key) == value


class TestStructuredFormatter:
    """Test StructuredFormatter functionality."""

    @pytest.mark.parametrize(
        "format_type,include_context,include_source,expected",
        [
            (
                "json",
                True,
                True,
                {"format_type": "json", "include_context": True, "include_source": True},
            ),
            (
                "KEY_VALUE",
                False,
                False,
                {"format_type": "key_value", "include_context": False, "include_source": False},
            ),
        ],
    )
    def test_structured_formatter_initialization(
        self, format_type, include_context, include_source, expected
    ):
        """Test StructuredFormatter initialization."""
        formatter = StructuredFormatter(
            format_type=format_type,
            include_context=include_context,
            include_source=include_source,
        )

        assert formatter.format_type == expected["format_type"]
        assert formatter.include_context == expected["include_context"]
        assert formatter.include_source == expected["include_source"]

    def test_structured_formatter_json_format(self, sample_log_record):
        """Test JSON formatting."""
        formatter = StructuredFormatter(
            format_type="json", include_context=False, include_source=False
        )
        result = formatter.format(sample_log_record)
        parsed = json.loads(result)

        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.logger"
        assert parsed["message"] == "Test message"
        assert parsed["module"] == "test_module"
        assert parsed["function"] == "test_function"
        assert parsed["line"] == 123
        assert "timestamp" in parsed

    def test_structured_formatter_with_exception(self, sample_log_record):
        """Test formatting with exception information."""
        formatter = StructuredFormatter(
            format_type="json", include_context=False, include_source=False
        )

        # Create exception info
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()

        sample_log_record.exc_info = exc_info
        sample_log_record.level = logging.ERROR
        result = formatter.format(sample_log_record)
        parsed = json.loads(result)

        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"
        assert parsed["exception"]["message"] == "Test exception"
        assert "traceback" in parsed["exception"]

    def test_structured_formatter_with_context(self, sample_log_record):
        """Test formatting with log context."""
        formatter = StructuredFormatter(
            format_type="json", include_context=True, include_source=False
        )
        context = LogContext(user_id="test-user", operation="test-op")
        context.set_current()

        result = formatter.format(sample_log_record)
        parsed = json.loads(result)

        assert "context" in parsed
        assert parsed["context"]["user_id"] == "test-user"
        assert parsed["context"]["operation"] == "test-op"

    @pytest.mark.parametrize(
        "format_type,expected_checks",
        [
            (
                "json",
                lambda result: (
                    "source" in json.loads(result)
                    and json.loads(result)["source"]["file"] == "/path/to/file.py"
                ),
            ),
            ("key_value", lambda result: "level=INFO" in result and "logger=test.logger" in result),
            ("human", lambda result: "INFO" in result and "test.logger" in result),
        ],
    )
    def test_structured_formatter_formats(self, sample_log_record, format_type, expected_checks):
        """Test different formatting types."""
        include_source = format_type == "json"
        formatter = StructuredFormatter(
            format_type=format_type, include_context=False, include_source=include_source
        )

        result = formatter.format(sample_log_record)
        assert expected_checks(result)

    def test_structured_formatter_with_extra_fields(self, sample_log_record):
        """Test formatting with extra fields."""
        formatter = StructuredFormatter(
            format_type="json", include_context=False, include_source=False
        )

        # Add extra fields
        sample_log_record.custom_field1 = "value1"
        sample_log_record.custom_field2 = "value2"

        result = formatter.format(sample_log_record)
        parsed = json.loads(result)

        assert "extra" in parsed
        assert parsed["extra"]["custom_field1"] == "value1"
        assert parsed["extra"]["custom_field2"] == "value2"

    def test_structured_formatter_human_readable_with_correlation(self, sample_log_record):
        """Test human-readable formatting with correlation ID."""
        formatter = StructuredFormatter(
            format_type="human", include_context=True, include_source=False
        )
        context = LogContext(correlation_id=CorrelationID("test-correlation"))
        context.set_current()

        result = formatter.format(sample_log_record)
        assert "[correlation_id=test-correlation]" in result


class TestStructuredLogger:
    """Test StructuredLogger functionality."""

    @patch("logging.getLogger")
    def test_structured_logger_initialization(self, mock_get_logger, mock_logger):
        """Test StructuredLogger initialization."""
        mock_get_logger.return_value = mock_logger
        structured_logger = StructuredLogger("test.logger")

        assert structured_logger.name == "test.logger"
        assert structured_logger.logger == mock_logger
        assert structured_logger._context_stack == []
        mock_get_logger.assert_called_once_with("test.logger")

    @patch("logging.getLogger")
    def test_structured_logger_setup_handler(self, mock_get_logger, mock_logger):
        """Test structured handler setup."""
        mock_get_logger.return_value = mock_logger
        StructuredLogger("test.logger")

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

        StructuredLogger("test.logger")
        mock_logger.addHandler.assert_not_called()

    @patch("inspect.currentframe")
    @patch("logging.getLogger")
    def test_structured_logger_log_levels(self, mock_get_logger, mock_currentframe, mock_logger):
        """Test all log level methods."""
        mock_get_logger.return_value = mock_logger
        mock_currentframe.return_value = Mock(f_back=None)

        structured_logger = StructuredLogger("test.logger")

        # Test all log levels with single calls
        for method, message in [
            ("trace", "Trace message"),
            ("debug", "Debug message"),
            ("info", "Info message"),
            ("warning", "Warning message"),
            ("error", "Error message"),
            ("critical", "Critical message"),
            ("audit", "Audit message"),
        ]:
            getattr(structured_logger, method)(message)

        assert mock_logger.log.call_count == 7

    @patch("logging.getLogger")
    def test_structured_logger_with_context_and_exc_info(self, mock_get_logger, mock_logger):
        """Test logging with explicit context and exception info."""
        mock_get_logger.return_value = mock_logger
        structured_logger = StructuredLogger("test.logger")

        # Test with context
        context = LogContext(user_id="test-user")
        structured_logger.info("Test message", context=context)

        args, kwargs = mock_logger.log.call_args
        assert "extra" in kwargs
        assert kwargs["extra"]["user_id"] == "test-user"

        # Test exception info
        mock_logger.reset_mock()
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()

        structured_logger.error("Error occurred", exc_info=exc_info)
        args, kwargs = mock_logger.log.call_args
        assert kwargs["exc_info"] == exc_info

    @patch("logging.getLogger")
    def test_structured_logger_with_context_method(self, mock_get_logger, mock_logger):
        """Test with_context method."""
        mock_get_logger.return_value = mock_logger
        structured_logger = StructuredLogger("test.logger")
        contextual_logger = structured_logger.with_context(user_id="test-user", operation="test-op")

        assert isinstance(contextual_logger, StructuredLogger)
        assert contextual_logger.name == "test.logger"
        assert len(contextual_logger._context_stack) == 1


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

    @pytest.mark.parametrize(
        "has_context,expected",
        [
            (True, "existing-id"),
            (False, None),
        ],
    )
    def test_contextual_logger_get_correlation_id(self, has_context, expected):
        """Test get_correlation_id with and without context."""

        class TestClass(ContextualLoggerMixin):
            pass

        with patch("calendarbot.structured.logging.get_structured_logger"):
            instance = TestClass()

            if has_context:
                correlation_id = CorrelationID(expected)
                context = LogContext(correlation_id=correlation_id)
                context.set_current()

            result = instance.get_correlation_id()
            if expected:
                assert str(result) == expected
            else:
                assert result is None

    def test_contextual_logger_all_methods(self):
        """Test all log level methods and error with exc_info."""

        class TestClass(ContextualLoggerMixin):
            pass

        mock_logger = Mock()
        with patch(
            "calendarbot.structured.logging.get_structured_logger", return_value=mock_logger
        ):
            instance = TestClass()

            # Test all log methods
            log_methods = [
                ("log_trace", "trace"),
                ("log_debug", "debug"),
                ("log_info", "info"),
                ("log_warning", "warning"),
                ("log_error", "error"),
                ("log_critical", "critical"),
                ("log_audit", "audit"),
            ]

            for method_name, mock_method in log_methods:
                getattr(instance, method_name)("Test message", extra_field="value")

            # Verify all methods were called
            for _, mock_method in log_methods:
                assert getattr(mock_logger, mock_method).call_count == 1

            # Test exception info
            try:
                raise ValueError("Test exception")
            except ValueError:
                exc_info = sys.exc_info()

            instance.log_error("Error occurred", exc_info=exc_info, extra_field="value")
            # Should be called twice now (once above + once here)
            assert mock_logger.error.call_count == 2
            args, kwargs = mock_logger.error.call_args
            assert kwargs["exc_info"] == exc_info


class TestContextManagers:
    """Test context manager functionality."""

    @pytest.mark.parametrize(
        "correlation_input,expected_type",
        [
            (None, CorrelationID),
            ("test-correlation-id", CorrelationID),
            (CorrelationID("existing-id"), CorrelationID),
        ],
    )
    def test_correlation_context_variants(self, correlation_input, expected_type):
        """Test correlation_context with different input types."""
        with correlation_context(correlation_input) as correlation_id:
            assert isinstance(correlation_id, expected_type)
            current_context = LogContext.get_current()
            assert current_context is not None
            assert current_context.correlation_id == correlation_id

            if isinstance(correlation_input, str):
                assert str(correlation_id) == correlation_input
            elif isinstance(correlation_input, CorrelationID):
                assert correlation_id == correlation_input

        # Context should be cleared after exiting
        assert LogContext.get_current() is None

    def test_correlation_context_preserves_existing_context(self):
        """Test that correlation_context preserves existing context."""
        existing_context = LogContext(user_id="existing-user")
        existing_context.set_current()

        with correlation_context("new-correlation"):
            current_context = LogContext.get_current()
            assert current_context.correlation_id.id == "new-correlation"
            assert current_context.user_id == "existing-user"  # Should be preserved

        # Original context should be restored
        restored_context = LogContext.get_current()
        assert restored_context == existing_context
        assert restored_context.user_id == "existing-user"

    @pytest.mark.parametrize(
        "params,expected",
        [
            ({}, {"request_id": None, "user_id": None, "session_id": None}),
            (
                {
                    "request_id": "req-123",
                    "user_id": "user-456",
                    "session_id": "session-789",
                    "correlation_id": "corr-abc",
                },
                {
                    "request_id": "req-123",
                    "user_id": "user-456",
                    "session_id": "session-789",
                    "correlation_id": "corr-abc",
                },
            ),
        ],
    )
    def test_request_context_parameters(self, params, expected):
        """Test request_context with various parameters."""
        with request_context(**params) as context:
            assert isinstance(context, LogContext)
            for key, value in expected.items():
                if key == "correlation_id" and value:
                    assert str(getattr(context, key)) == value
                else:
                    assert getattr(context, key) == value

            assert LogContext.get_current() == context

    def test_operation_context_scenarios(self):
        """Test operation_context with different scenarios."""
        # Test with component and kwargs
        with operation_context(
            "test_op", component="test_comp", custom_field="custom_value"
        ) as context:
            assert context.operation == "test_op"
            assert context.component == "test_comp"
            assert context.custom_fields["custom_field"] == "custom_value"

        # Test preserving existing correlation
        existing_correlation = CorrelationID("existing-correlation")
        existing_context = LogContext(correlation_id=existing_correlation)
        existing_context.set_current()

        with operation_context("new_operation") as context:
            assert context.operation == "new_operation"
            assert context.correlation_id == existing_correlation


class TestDecorators:
    """Test decorator functionality."""

    @pytest.mark.parametrize(
        "correlation_id_input,expected_check",
        [
            (None, lambda result: len(result) == 36),  # UUID length
            ("decorator-test-id", lambda result: result == "decorator-test-id"),
            (
                CorrelationID("object-test-id"),
                lambda result: isinstance(result, CorrelationID)
                and str(result) == "object-test-id",
            ),
        ],
    )
    def test_with_correlation_id_decorator(self, correlation_id_input, expected_check):
        """Test @with_correlation_id decorator with different inputs."""

        @with_correlation_id(correlation_id_input)
        def test_function():
            context = LogContext.get_current()
            assert context is not None
            assert context.correlation_id is not None
            return (
                context.correlation_id
                if isinstance(correlation_id_input, CorrelationID)
                else str(context.correlation_id)
            )

        result = test_function()
        assert expected_check(result)
        # Context should be cleared after function
        assert LogContext.get_current() is None

    def test_with_correlation_id_decorator_preserves_functionality(self):
        """Test decorator preserves function return values and exceptions."""

        # Test return value preservation
        @with_correlation_id()
        def test_add(x, y):
            return x + y

        assert test_add(5, 10) == 15

        # Test exception preservation
        @with_correlation_id()
        def test_exception():
            raise ValueError("Test exception")

        with pytest.raises(ValueError, match="Test exception"):
            test_exception()


class TestGlobalFunctions:
    """Test global utility functions."""

    @pytest.mark.parametrize(
        "has_context,expected_id",
        [
            (True, "test-current-id"),
            (False, None),
        ],
    )
    def test_current_correlation_id(self, has_context, expected_id):
        """Test current_correlation_id with and without context."""
        if has_context:
            correlation_id = CorrelationID(expected_id)
            context = LogContext(correlation_id=correlation_id)
            context.set_current()

        result = current_correlation_id()
        if expected_id:
            assert str(result) == expected_id
        else:
            assert result is None

    @patch("logging.getLogger")
    def test_get_structured_logger_scenarios(self, mock_get_logger, mock_logger):
        """Test get_structured_logger creation and reuse scenarios."""
        mock_get_logger.return_value = mock_logger

        # Reset global logger
        import calendarbot.structured.logging as logging_module

        logging_module._structured_logger = None

        # Test new logger creation
        result = get_structured_logger("test.logger")
        assert isinstance(result, StructuredLogger)
        assert result.name == "test.logger"

        # Test logger reuse with same name
        logger1 = get_structured_logger("same.logger")
        logger2 = get_structured_logger("same.logger")
        assert logger1 == logger2

        # Test different logger names
        logger3 = get_structured_logger("different.logger")
        assert logger1.name != logger3.name

    @patch("logging.addLevelName")
    @patch("logging.getLogger")
    def test_init_structured_logging(self, mock_get_logger, mock_add_level_name, mock_logger):
        """Test init_structured_logging function."""
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
        threads = [threading.Thread(target=thread_function, args=(i,)) for i in range(3)]
        for thread in threads:
            thread.start()
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

    def test_structured_formatter_with_extra_data(self, sample_log_record):
        """Test formatter handles extra data gracefully."""
        formatter = StructuredFormatter(format_type="json")
        sample_log_record.custom_field = "value"

        result = formatter.format(sample_log_record)
        parsed = json.loads(result)
        assert "extra" in parsed
        assert parsed["extra"]["custom_field"] == "value"

    def test_context_manager_exception_handling(self):
        """Test context managers handle exceptions properly."""
        original_context = LogContext(user_id="original")
        original_context.set_current()

        try:
            with correlation_context("test-id"):
                current = LogContext.get_current()
                assert str(current.correlation_id) == "test-id"
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Original context should be restored even after exception
        restored = LogContext.get_current()
        assert restored.user_id == "original"

    @patch("threading.get_ident", side_effect=RuntimeError("Thread error"))
    @patch("inspect.currentframe")
    def test_log_context_from_frame_exception_handling(
        self, mock_currentframe, mock_get_ident, mock_frame
    ):
        """Test LogContext.from_frame with threading exception propagation."""
        # Should raise the exception since there's no handling in the actual implementation
        with pytest.raises(RuntimeError, match="Thread error"):
            LogContext.from_frame(mock_frame)
