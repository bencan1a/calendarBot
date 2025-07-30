"""Structured logging enhancement with correlation IDs and standardized formats for CalendarBot."""

from typing import Optional

from .logging import (
    ContextualLoggerMixin,
    CorrelationID,
    LogContext,
    StructuredFormatter,
    StructuredLogger,
    correlation_context,
    current_correlation_id,
    get_structured_logger,
    init_structured_logging,
    operation_context,
    request_context,
    with_correlation_id,
)

__all__ = [
    "ContextualLoggerMixin",
    "CorrelationID",
    "LogContext",
    "StructuredFormatter",
    "StructuredLogger",
    "correlation_context",
    "current_correlation_id",
    "get_structured_logger",
    "init_structured_logging",
    "operation_context",
    "request_context",
    "with_correlation_id",
]


# Convenience functions for quick access
def get_logger() -> StructuredLogger:
    """Get the global structured logger instance."""
    return get_structured_logger()


def new_correlation_id() -> str:
    """Generate a new correlation ID."""
    return CorrelationID.generate()


def get_current_context() -> Optional[LogContext]:
    """Get current log context."""
    return LogContext.get_current()
