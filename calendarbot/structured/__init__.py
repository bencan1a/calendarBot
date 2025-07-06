"""Structured logging enhancement with correlation IDs and standardized formats for CalendarBot."""

from .logging import (
    StructuredLogger,
    CorrelationID,
    LogContext,
    StructuredFormatter,
    ContextualLoggerMixin,
    correlation_context,
    request_context,
    operation_context,
    get_structured_logger,
    init_structured_logging,
    with_correlation_id,
    current_correlation_id
)

__all__ = [
    'StructuredLogger',
    'CorrelationID',
    'LogContext',
    'StructuredFormatter',
    'ContextualLoggerMixin',
    'correlation_context',
    'request_context',
    'operation_context',
    'get_structured_logger',
    'init_structured_logging',
    'with_correlation_id',
    'current_correlation_id'
]


# Convenience functions for quick access
def get_logger():
    """Get the global structured logger instance."""
    return get_structured_logger()

def new_correlation_id():
    """Generate a new correlation ID."""
    return CorrelationID.generate()

def get_current_context():
    """Get current log context."""
    return LogContext.get_current()