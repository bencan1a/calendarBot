"""Structured logging enhancement with correlation IDs and standardized formats."""

import inspect
import json
import logging
import sys
import threading
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from ..utils.logging import get_logger


class LogLevel(Enum):
    """Enhanced log levels with structured context."""

    TRACE = 5
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    AUDIT = 35


class CorrelationID:
    """Manages correlation IDs for request tracing."""

    def __init__(self, correlation_id: Optional[str] = None):
        self.id = correlation_id or self.generate()

    @staticmethod
    def generate() -> str:
        """Generate a new correlation ID."""
        return str(uuid.uuid4())

    def __str__(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return f"CorrelationID('{self.id}')"


@dataclass
class LogContext:
    """Structured context for enhanced logging."""

    correlation_id: Optional[CorrelationID] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    function_name: Optional[str] = None
    thread_id: Optional[str] = None
    process_id: Optional[int] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for logging."""
        context_dict = {}

        if self.correlation_id:
            context_dict["correlation_id"] = str(self.correlation_id)
        if self.user_id:
            context_dict["user_id"] = self.user_id
        if self.session_id:
            context_dict["session_id"] = self.session_id
        if self.request_id:
            context_dict["request_id"] = self.request_id
        if self.operation:
            context_dict["operation"] = self.operation
        if self.component:
            context_dict["component"] = self.component
        if self.source_file:
            context_dict["source_file"] = self.source_file
        if self.source_line:
            context_dict["source_line"] = self.source_line
        if self.function_name:
            context_dict["function_name"] = self.function_name
        if self.thread_id:
            context_dict["thread_id"] = self.thread_id
        if self.process_id:
            context_dict["process_id"] = self.process_id

        context_dict["timestamp"] = self.timestamp.isoformat()
        context_dict.update(self.custom_fields)

        return context_dict

    @classmethod
    def from_frame(cls, frame: Optional[Any] = None) -> "LogContext":
        """Create context from current execution frame."""
        if frame is None:
            frame = inspect.currentframe().f_back

        context = cls()

        if frame:
            context.source_file = frame.f_code.co_filename
            context.source_line = frame.f_lineno
            context.function_name = frame.f_code.co_name
            context.thread_id = str(threading.get_ident())
            context.process_id = os.getpid() if "os" in sys.modules else None

        return context

    @classmethod
    def get_current(cls) -> Optional["LogContext"]:
        """Get current context from thread-local storage."""
        return getattr(_context_storage, "context", None)

    def set_current(self):
        """Set this context as current in thread-local storage."""
        _context_storage.context = self

    def update(self, **kwargs):
        """Update context fields."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.custom_fields[key] = value


# Thread-local storage for context
_context_storage = threading.local()


class StructuredFormatter(logging.Formatter):
    """Advanced formatter for structured log output."""

    def __init__(
        self,
        format_type: str = "json",
        include_context: bool = True,
        include_source: bool = True,
        timestamp_format: str = "%Y-%m-%d %H:%M:%S.%f",
    ):
        super().__init__()
        self.format_type = format_type.lower()
        self.include_context = include_context
        self.include_source = include_source
        self.timestamp_format = timestamp_format

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured output."""
        # Build structured log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).strftime(self.timestamp_format)[
                :-3
            ],
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None,
            }

        # Add context information
        if self.include_context:
            current_context = LogContext.get_current()
            if current_context:
                log_entry["context"] = current_context.to_dict()

        # Add source information
        if self.include_source:
            log_entry["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Add any extra fields from the record
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
            ):
                log_entry["extra"] = log_entry.get("extra", {})
                log_entry["extra"][key] = value

        # Format according to specified type
        if self.format_type == "json":
            return json.dumps(log_entry, separators=(",", ":"), default=str)
        elif self.format_type == "key_value":
            return self._format_key_value(log_entry)
        else:  # human-readable
            return self._format_human_readable(log_entry)

    def _format_key_value(self, log_entry: Dict[str, Any]) -> str:
        """Format as key=value pairs."""
        pairs = []
        for key, value in log_entry.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    pairs.append(f"{key}_{sub_key}={sub_value}")
            else:
                pairs.append(f"{key}={value}")
        return " ".join(pairs)

    def _format_human_readable(self, log_entry: Dict[str, Any]) -> str:
        """Format as human-readable text."""
        timestamp = log_entry["timestamp"]
        level = log_entry["level"]
        logger = log_entry["logger"]
        message = log_entry["message"]

        formatted = f"{timestamp} - {level} - {logger} - {message}"

        # Add context if available
        if "context" in log_entry and "correlation_id" in log_entry["context"]:
            formatted += f" [correlation_id={log_entry['context']['correlation_id']}]"

        return formatted


class StructuredLogger:
    """Enhanced logger with structured logging capabilities."""

    def __init__(self, name: str, settings: Optional[Any] = None):
        self.name = name
        self.settings = settings
        self.logger = logging.getLogger(name)
        self._context_stack: List[LogContext] = []

        # Set up structured formatter if not already configured
        self._setup_structured_handler()

    def _setup_structured_handler(self):
        """Set up structured logging handler."""
        # Check if structured handler already exists
        for handler in self.logger.handlers:
            if isinstance(handler.formatter, StructuredFormatter):
                return

        # Create structured handler
        structured_handler = logging.StreamHandler()
        structured_formatter = StructuredFormatter(
            format_type="json", include_context=True, include_source=True
        )
        structured_handler.setFormatter(structured_formatter)
        structured_handler.setLevel(logging.DEBUG)

        # Add to logger
        self.logger.addHandler(structured_handler)
        self.logger.setLevel(logging.DEBUG)

    def _log_with_context(
        self,
        level: int,
        message: str,
        context: Optional[LogContext] = None,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Any] = None,
    ):
        """Log message with structured context."""
        # Get or create context
        if context is None:
            context = LogContext.get_current()
            if context is None:
                context = LogContext.from_frame(inspect.currentframe().f_back)

        # Set context as current
        old_context = LogContext.get_current()
        context.set_current()

        try:
            # Prepare extra fields
            log_extra = extra or {}
            log_extra.update(context.to_dict())

            # Log the message
            self.logger.log(level, message, extra=log_extra, exc_info=exc_info)

        finally:
            # Restore previous context
            if old_context:
                old_context.set_current()
            elif hasattr(_context_storage, "context"):
                delattr(_context_storage, "context")

    def trace(
        self,
        message: str,
        context: Optional[LogContext] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """Log trace message."""
        self._log_with_context(LogLevel.TRACE.value, message, context, extra)

    def debug(
        self,
        message: str,
        context: Optional[LogContext] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, context, extra)

    def info(
        self,
        message: str,
        context: Optional[LogContext] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """Log info message."""
        self._log_with_context(logging.INFO, message, context, extra)

    def warning(
        self,
        message: str,
        context: Optional[LogContext] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, context, extra)

    def error(
        self,
        message: str,
        context: Optional[LogContext] = None,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Any] = None,
    ):
        """Log error message."""
        self._log_with_context(logging.ERROR, message, context, extra, exc_info)

    def critical(
        self,
        message: str,
        context: Optional[LogContext] = None,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Any] = None,
    ):
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, context, extra, exc_info)

    def audit(
        self,
        message: str,
        context: Optional[LogContext] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """Log audit message."""
        self._log_with_context(LogLevel.AUDIT.value, message, context, extra)

    def with_context(self, **kwargs) -> "StructuredLogger":
        """Create logger with additional context."""
        context = LogContext.get_current() or LogContext()
        context.update(**kwargs)

        # Create new logger instance with context
        new_logger = StructuredLogger(self.name, self.settings)
        new_logger._context_stack = self._context_stack.copy()
        new_logger._context_stack.append(context)

        return new_logger


class ContextualLoggerMixin:
    """Mixin to add structured logging capabilities to any class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._structured_logger = get_structured_logger(self.__class__.__name__)

    def get_base_context(self) -> LogContext:
        """Get base context for this component."""
        context = LogContext()
        context.component = self.__class__.__name__
        context.correlation_id = self.get_correlation_id()
        return context

    def get_correlation_id(self) -> Optional[CorrelationID]:
        """Get correlation ID for this component."""
        current_context = LogContext.get_current()
        return current_context.correlation_id if current_context else None

    def log_trace(self, message: str, **kwargs):
        """Log trace message with component context."""
        context = self.get_base_context()
        context.update(**kwargs)
        self._structured_logger.trace(message, context)

    def log_debug(self, message: str, **kwargs):
        """Log debug message with component context."""
        context = self.get_base_context()
        context.update(**kwargs)
        self._structured_logger.debug(message, context)

    def log_info(self, message: str, **kwargs):
        """Log info message with component context."""
        context = self.get_base_context()
        context.update(**kwargs)
        self._structured_logger.info(message, context)

    def log_warning(self, message: str, **kwargs):
        """Log warning message with component context."""
        context = self.get_base_context()
        context.update(**kwargs)
        self._structured_logger.warning(message, context)

    def log_error(self, message: str, exc_info: Optional[Any] = None, **kwargs):
        """Log error message with component context."""
        context = self.get_base_context()
        context.update(**kwargs)
        self._structured_logger.error(message, context, exc_info=exc_info)

    def log_critical(self, message: str, exc_info: Optional[Any] = None, **kwargs):
        """Log critical message with component context."""
        context = self.get_base_context()
        context.update(**kwargs)
        self._structured_logger.critical(message, context, exc_info=exc_info)

    def log_audit(self, message: str, **kwargs):
        """Log audit message with component context."""
        context = self.get_base_context()
        context.update(**kwargs)
        self._structured_logger.audit(message, context)


@contextmanager
def correlation_context(correlation_id: Optional[Union[str, CorrelationID]] = None):
    """
    Context manager for correlation ID tracking.

    Usage:
        with correlation_context() as correlation_id:
            # All logging within this context will include the correlation ID
            logger.info("Processing request")
    """
    if isinstance(correlation_id, str):
        correlation_id = CorrelationID(correlation_id)
    elif correlation_id is None:
        correlation_id = CorrelationID()

    # Create new context with correlation ID
    context = LogContext.get_current() or LogContext()
    context.correlation_id = correlation_id

    # Store previous context
    old_context = LogContext.get_current()
    context.set_current()

    try:
        yield correlation_id
    finally:
        # Restore previous context
        if old_context:
            old_context.set_current()
        elif hasattr(_context_storage, "context"):
            delattr(_context_storage, "context")


@contextmanager
def request_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    correlation_id: Optional[Union[str, CorrelationID]] = None,
):
    """
    Context manager for HTTP request tracking.

    Usage:
        with request_context(request_id="req-123", user_id="user-456"):
            # All logging within this context will include request context
            logger.info("Processing user request")
    """
    if isinstance(correlation_id, str):
        correlation_id = CorrelationID(correlation_id)
    elif correlation_id is None:
        correlation_id = CorrelationID()

    # Create request context
    context = LogContext(
        correlation_id=correlation_id, request_id=request_id, user_id=user_id, session_id=session_id
    )

    # Store previous context
    old_context = LogContext.get_current()
    context.set_current()

    try:
        yield context
    finally:
        # Restore previous context
        if old_context:
            old_context.set_current()
        elif hasattr(_context_storage, "context"):
            delattr(_context_storage, "context")


@contextmanager
def operation_context(
    operation: str,
    component: Optional[str] = None,
    correlation_id: Optional[Union[str, CorrelationID]] = None,
    **kwargs,
):
    """
    Context manager for operation tracking.

    Usage:
        with operation_context("fetch_events", component="source_manager"):
            # All logging within this context will include operation context
            logger.info("Fetching calendar events")
    """
    # Get or create correlation ID
    if isinstance(correlation_id, str):
        correlation_id = CorrelationID(correlation_id)
    elif correlation_id is None:
        current_context = LogContext.get_current()
        correlation_id = current_context.correlation_id if current_context else CorrelationID()

    # Create operation context
    context = LogContext.get_current() or LogContext()
    context.correlation_id = correlation_id
    context.operation = operation
    if component:
        context.component = component
    context.update(**kwargs)

    # Store previous context
    old_context = LogContext.get_current()
    context.set_current()

    try:
        yield context
    finally:
        # Restore previous context
        if old_context:
            old_context.set_current()
        elif hasattr(_context_storage, "context"):
            delattr(_context_storage, "context")


def with_correlation_id(correlation_id: Optional[Union[str, CorrelationID]] = None):
    """
    Decorator to automatically add correlation ID to function context.

    Usage:
        @with_correlation_id()
        def process_request():
            logger.info("Processing")  # Will include correlation ID
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with correlation_context(correlation_id):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def current_correlation_id() -> Optional[CorrelationID]:
    """Get the current correlation ID from context."""
    context = LogContext.get_current()
    return context.correlation_id if context else None


# Global structured logger instance
_structured_logger: Optional[StructuredLogger] = None


def get_structured_logger(
    name: str = "calendarbot.structured", settings: Optional[Any] = None
) -> StructuredLogger:
    """Get or create structured logger instance."""
    global _structured_logger
    if _structured_logger is None or _structured_logger.name != name:
        _structured_logger = StructuredLogger(name, settings)
    return _structured_logger


def init_structured_logging(settings: Any) -> StructuredLogger:
    """Initialize structured logging system with settings."""
    global _structured_logger
    _structured_logger = StructuredLogger("calendarbot.structured", settings)

    # Add TRACE and AUDIT levels
    logging.addLevelName(LogLevel.TRACE.value, "TRACE")
    logging.addLevelName(LogLevel.AUDIT.value, "AUDIT")

    return _structured_logger


# Make os available for process ID
import os
