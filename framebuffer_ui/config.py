"""Configuration management for framebuffer UI.

Loads configuration from environment variables, matching the pattern
used by calendarbot_lite.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Framebuffer UI configuration.

    All settings loaded from environment variables to maintain consistency
    with the existing calendarbot_lite configuration approach.
    """

    # Display settings
    display_width: int = 480
    display_height: int = 800
    display_rotation: int = 0  # 0, 90, 180, 270

    # Backend API settings
    backend_url: str = "http://localhost:8080"
    api_timeout: int = 10  # seconds
    api_retry_attempts: int = 3

    # Refresh settings
    refresh_interval: int = 60  # seconds - API data refresh
    display_refresh_interval: int = 5  # seconds - Display render refresh

    # Error display settings
    error_threshold: int = 900  # 15 minutes - only show errors after this long

    # Font settings
    font_dir: Path | None = None  # If None, use bundled fonts

    # Logging
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Config:
        """Load configuration from environment variables.

        Environment Variables:
            CALENDARBOT_BACKEND_URL - Backend API URL
            CALENDARBOT_DISPLAY_WIDTH - Display width in pixels
            CALENDARBOT_DISPLAY_HEIGHT - Display height in pixels
            CALENDARBOT_DISPLAY_ROTATION - Display rotation (0, 90, 180, 270)
            CALENDARBOT_API_TIMEOUT - API request timeout in seconds
            CALENDARBOT_REFRESH_INTERVAL - Refresh interval in seconds
            CALENDARBOT_LOG_LEVEL - Logging level (DEBUG, INFO, WARNING, ERROR)
            CALENDARBOT_FONT_DIR - Custom font directory path

        Returns:
            Config instance with values from environment
        """
        backend_url = os.getenv("CALENDARBOT_BACKEND_URL", "http://localhost:8080")

        # Strip trailing slash from backend URL
        if backend_url.endswith("/"):
            backend_url = backend_url[:-1]

        display_width = int(os.getenv("CALENDARBOT_DISPLAY_WIDTH", "480"))
        display_height = int(os.getenv("CALENDARBOT_DISPLAY_HEIGHT", "800"))
        display_rotation = int(os.getenv("CALENDARBOT_DISPLAY_ROTATION", "0"))

        api_timeout = int(os.getenv("CALENDARBOT_API_TIMEOUT", "10"))
        api_retry_attempts = int(os.getenv("CALENDARBOT_API_RETRY_ATTEMPTS", "3"))

        refresh_interval = int(os.getenv("CALENDARBOT_REFRESH_INTERVAL", "60"))
        display_refresh_interval = int(os.getenv("CALENDARBOT_DISPLAY_REFRESH_INTERVAL", "5"))

        error_threshold = int(os.getenv("CALENDARBOT_ERROR_THRESHOLD", "900"))

        log_level = os.getenv("CALENDARBOT_LOG_LEVEL", "INFO").upper()

        font_dir_str = os.getenv("CALENDARBOT_FONT_DIR")
        font_dir = Path(font_dir_str) if font_dir_str else None

        return cls(
            display_width=display_width,
            display_height=display_height,
            display_rotation=display_rotation,
            backend_url=backend_url,
            api_timeout=api_timeout,
            api_retry_attempts=api_retry_attempts,
            refresh_interval=refresh_interval,
            display_refresh_interval=display_refresh_interval,
            error_threshold=error_threshold,
            font_dir=font_dir,
            log_level=log_level,
        )

    def get_api_endpoint(self, path: str) -> str:
        """Get full API endpoint URL.

        Args:
            path: API path (e.g., "/api/whats-next")

        Returns:
            Full URL (e.g., "http://localhost:8080/api/whats-next")
        """
        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path

        return f"{self.backend_url}{path}"
