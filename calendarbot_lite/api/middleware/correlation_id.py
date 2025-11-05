"""Request correlation ID middleware for distributed tracing.

This module provides middleware to extract or generate correlation IDs
for request tracking across distributed system components (Alexa -> API
Gateway -> Lambda -> CalendarBot -> Calendar Service).

Correlation IDs enable:
- End-to-end request tracing across services
- Faster debugging by correlating logs
- Performance analysis tracking request latency
- Error investigation across service boundaries
"""

import uuid
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

from aiohttp import web

# Context variable for storing request correlation ID
# Uses contextvars for thread-safe async context propagation
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


@web.middleware
async def correlation_id_middleware(
    request: web.Request, handler: Callable[[web.Request], Any]
) -> web.Response:
    """Extract or generate correlation ID for request tracking.

    Priority for correlation ID extraction:
    1. X-Amzn-Trace-Id from AWS ALB/API Gateway
    2. X-Request-ID from client
    3. X-Correlation-ID from client
    4. Generate new UUID

    The correlation ID is:
    - Stored in context variable for access throughout request
    - Added to request object for handler access
    - Added to response headers for client visibility

    Args:
        request: aiohttp request object
        handler: Next handler in middleware chain

    Returns:
        Response with correlation ID added to headers
    """
    # Try to get correlation ID from headers (priority order)
    correlation_id = (
        request.headers.get("X-Amzn-Trace-Id")
        or request.headers.get("X-Request-ID")
        or request.headers.get("X-Correlation-ID")
        or str(uuid.uuid4())
    )

    # Store in context variable for access throughout request
    request_id_var.set(correlation_id)

    # Add to request for handler access
    request["correlation_id"] = correlation_id

    # Process request
    response = await handler(request)

    # Add correlation ID to response headers
    response.headers["X-Request-ID"] = correlation_id

    return response


def get_request_id() -> str:
    """Get current request correlation ID from context.

    Returns:
        Current request correlation ID, or "no-request-id" if not set

    Example:
        >>> from calendarbot_lite.middleware import get_request_id
        >>> request_id = get_request_id()
        >>> logger.info("Processing request %s", request_id)
    """
    request_id = request_id_var.get()
    return request_id if request_id else "no-request-id"
