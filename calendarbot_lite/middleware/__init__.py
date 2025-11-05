"""Middleware components for request processing.

This module provides middleware for cross-cutting concerns like request
correlation ID tracking for distributed tracing.
"""

from .correlation_id import correlation_id_middleware, get_request_id

__all__ = ["correlation_id_middleware", "get_request_id"]
