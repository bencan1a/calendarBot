"""
CalendarBot Kiosk Mode Module.

This module provides kiosk mode functionality for unattended calendar displays,
optimized for Raspberry Pi Zero 2W deployment with memory constraints and
robust crash recovery mechanisms.

Components:
    BrowserManager: Chromium browser process lifecycle management
    BrowserState: Browser process state enumeration
    BrowserStatus: Browser health and status tracking
    BrowserConfig: Browser configuration for Pi Zero 2W
    BrowserError: Browser-related exception handling
"""

from .browser_manager import (
    BrowserConfig,
    BrowserError,
    BrowserManager,
    BrowserState,
    BrowserStatus,
)

__all__ = [
    "BrowserConfig",
    "BrowserError",
    "BrowserManager",
    "BrowserState",
    "BrowserStatus",
]

__version__ = "1.0.0"
