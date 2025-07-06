"""Web interface module for HTML display and navigation."""

from .server import WebServer
from .navigation import WebNavigationHandler

__all__ = ['WebServer', 'WebNavigationHandler']