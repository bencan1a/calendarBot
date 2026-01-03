"""CalendarBot Framebuffer UI - Lightweight pygame-based display.

This package provides a minimal-memory framebuffer UI for CalendarBot,
replacing the heavy X11 + Chromium stack (~260MB) with a lightweight
pygame renderer (~15MB).

Target Platform: Raspberry Pi Zero 2W (512MB RAM)
Memory Target: <25MB RSS
Startup Target: <5s to first frame

Architecture:
- renderer.py: Pygame framebuffer rendering (3-zone layout)
- api_client.py: Async HTTP client for backend API
- layout_engine.py: Data transformation and formatting
- config.py: Configuration loading from .env
- main.py: Main event loop and coordinator

Usage:
    SDL_VIDEODRIVER=kmsdrm python -m framebuffer_ui.main

Environment Variables:
    CALENDARBOT_BACKEND_URL - Backend API URL (default: http://localhost:8080)
    SDL_VIDEODRIVER - SDL video driver (kmsdrm or fbcon)
    SDL_NOMOUSE - Disable mouse cursor (default: 1)
"""

__version__ = "0.1.0"
__author__ = "CalendarBot Team"

from framebuffer_ui.config import Config

__all__ = ["Config"]
