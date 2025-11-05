"""Route modules for calendarbot_lite server."""

from .alexa_routes import register_alexa_routes
from .api_routes import register_api_routes
from .static_routes import register_static_routes

__all__ = [
    "register_alexa_routes",
    "register_api_routes",
    "register_static_routes",
]
