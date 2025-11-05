"""Rate limiting middleware for aiohttp route handlers.

This module provides decorator and middleware functions to apply rate limiting
to Alexa endpoint handlers with minimal code changes.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any, Optional

from aiohttp import web

from .rate_limiter import RateLimiter, get_bearer_token, get_client_ip

logger = logging.getLogger(__name__)


def create_rate_limited_handler(
    handler: Callable[..., Any],
    rate_limiter: RateLimiter,
) -> Callable[..., Any]:
    """Wrap a handler function with rate limiting.

    Args:
        handler: Async handler function to wrap
        rate_limiter: RateLimiter instance

    Returns:
        Wrapped handler function with rate limiting
    """

    @functools.wraps(handler)
    async def wrapped_handler(request: web.Request) -> web.Response:
        """Rate-limited handler wrapper."""
        # Extract client info
        client_ip = get_client_ip(request)
        bearer_token = get_bearer_token(request)

        # Check rate limit
        allowed, limit_info = await rate_limiter.check_rate_limit(client_ip, bearer_token)

        # Add rate limit headers to response
        def add_rate_limit_headers(response: web.Response) -> web.Response:
            """Add X-RateLimit-* headers to response."""
            response.headers["X-RateLimit-Limit-IP"] = str(rate_limiter.config.per_ip_limit)
            response.headers["X-RateLimit-Remaining-IP"] = str(limit_info["remaining_ip"])
            response.headers["X-RateLimit-Reset"] = str(limit_info["reset_seconds"])

            if bearer_token and limit_info["remaining_token"] is not None:
                response.headers["X-RateLimit-Limit-Token"] = str(
                    rate_limiter.config.per_token_limit
                )
                response.headers["X-RateLimit-Remaining-Token"] = str(
                    limit_info["remaining_token"]
                )

            return response

        # If rate limit exceeded, return 429 Too Many Requests
        if not allowed:
            retry_after = limit_info.get("retry_after", 60)

            response = web.json_response(
                {
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after": retry_after,
                },
                status=429,
            )

            response.headers["Retry-After"] = str(retry_after)
            response = add_rate_limit_headers(response)

            logger.info(
                "Rate limit exceeded for IP=%s, retry_after=%d seconds",
                client_ip[:15] + "..." if len(client_ip) > 15 else client_ip,
                retry_after,
            )

            return response

        # Call original handler
        response = await handler(request)

        # Add rate limit headers to successful response
        if isinstance(response, web.Response):
            response = add_rate_limit_headers(response)

        return response

    return wrapped_handler


def rate_limit(rate_limiter: RateLimiter) -> Callable[[Any], Any]:
    """Decorator to apply rate limiting to a handler function.

    Usage:
        @rate_limit(my_rate_limiter)
        async def my_handler(request):
            return web.json_response({"status": "ok"})

    Args:
        rate_limiter: RateLimiter instance

    Returns:
        Decorator function
    """

    def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
        return create_rate_limited_handler(handler, rate_limiter)

    return decorator


async def rate_limit_middleware(
    app: web.Application, handler: Callable[..., Any]
) -> Callable[..., Any]:
    """aiohttp middleware to apply rate limiting to all routes.

    This middleware checks for a rate_limiter instance stored in app['rate_limiter']
    and applies rate limiting if present.

    Usage:
        app.middlewares.append(rate_limit_middleware)
        app['rate_limiter'] = RateLimiter(config)

    Args:
        app: aiohttp Application instance
        handler: Request handler

    Returns:
        Wrapped handler with rate limiting
    """
    rate_limiter: Optional[RateLimiter] = app.get("rate_limiter")

    if rate_limiter is None:
        logger.warning("Rate limiter not configured in app['rate_limiter'], skipping rate limiting")
        return handler

    return create_rate_limited_handler(handler, rate_limiter)
