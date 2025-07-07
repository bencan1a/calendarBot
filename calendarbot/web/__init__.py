"""Web interface module for HTML display and navigation."""

from .navigation import WebNavigationHandler
from .server import WebServer

__all__ = ["WebServer", "WebNavigationHandler"]
