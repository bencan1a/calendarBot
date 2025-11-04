"""Configuration management for calendarbot_lite server."""

from __future__ import annotations

import contextlib
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Input validation limits for event fields
# These limits prevent resource exhaustion from oversized calendar data
MAX_EVENT_SUBJECT_LENGTH = 200  # ~20 words - reasonable meeting title
MAX_EVENT_LOCATION_LENGTH = 100  # ~10 words - reasonable location name
MAX_EVENT_DESCRIPTION_LENGTH = 500  # ~50 words - reasonable description
MAX_EVENTS_PER_REQUEST = 100  # Pagination limit for API requests


class ConfigManager:
    """Manages application configuration from environment variables and .env files."""

    def __init__(self, env_file_path: Path | None = None):
        """Initialize configuration manager.

        Args:
            env_file_path: Optional path to .env file (defaults to .env in current directory)
        """
        self.env_file_path = env_file_path or Path.cwd() / ".env"

    def load_env_file(self) -> list[str]:
        """Load .env file and set environment variables.

        Only sets variables that are not already in the environment to avoid
        surprising overrides of user's environment.

        Returns:
            List of environment variable keys that were loaded from .env file
        """
        if not self.env_file_path.exists():
            logger.debug("No .env file found at %s", self.env_file_path)
            return []

        set_keys = []

        try:
            content = self.env_file_path.read_text(encoding="utf-8")

            for raw_line in content.splitlines():
                line = raw_line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse KEY=VALUE format
                if "=" not in line:
                    continue

                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")

                # Only set if not already in environment
                if key and key not in os.environ:
                    os.environ[key] = val
                    set_keys.append(key)

            if set_keys:
                logger.debug("Loaded .env defaults for keys: %s", ", ".join(set_keys))

        except Exception:
            logger.debug(
                "Failed to read .env file for defaults (continuing): %s",
                str(self.env_file_path),
                exc_info=True,
            )

        return set_keys

    def build_config_from_env(self) -> dict[str, Any]:
        """Build configuration dictionary from environment variables.

        Recognizes:
        - CALENDARBOT_ICS_URL -> 'ics_sources' (list with single URL)
        - CALENDARBOT_REFRESH_INTERVAL -> 'refresh_interval_seconds' (int)
        - CALENDARBOT_WEB_HOST or CALENDARBOT_SERVER_BIND -> 'server_bind'
        - CALENDARBOT_WEB_PORT or CALENDARBOT_SERVER_PORT -> 'server_port' (int)
        - CALENDARBOT_ALEXA_BEARER_TOKEN -> 'alexa_bearer_token'
        - CALENDARBOT_DEFAULT_TIMEZONE -> 'default_timezone'

        Returns:
            Configuration dictionary compatible with start_server
        """
        cfg: dict[str, Any] = {}

        # ICS URL configuration
        ics_url = os.environ.get("CALENDARBOT_ICS_URL")
        if ics_url:
            # Accept a single URL string; server uses ics_sources list
            cfg["ics_sources"] = [ics_url]
            with contextlib.suppress(Exception):
                cfg["sources"] = [ics_url]  # For diagnostic purposes

        # Refresh interval configuration
        refresh = os.environ.get("CALENDARBOT_REFRESH_INTERVAL") or os.environ.get(
            "CALENDARBOT_REFRESH_INTERVAL_SECONDS"
        )
        if refresh:
            try:
                cfg["refresh_interval_seconds"] = int(refresh)
            except Exception:
                logger.warning("Invalid CALENDARBOT_REFRESH_INTERVAL=%r; ignoring", refresh)

        # Server host configuration
        host = os.environ.get("CALENDARBOT_WEB_HOST") or os.environ.get("CALENDARBOT_SERVER_BIND")
        if host:
            cfg["server_bind"] = host

        # Server port configuration
        port = os.environ.get("CALENDARBOT_WEB_PORT") or os.environ.get("CALENDARBOT_SERVER_PORT")
        if port:
            try:
                cfg["server_port"] = int(port)
            except Exception:
                logger.warning("Invalid CALENDARBOT_WEB_PORT=%r; ignoring", port)

        # Alexa bearer token for API authentication
        alexa_token = os.environ.get("CALENDARBOT_ALEXA_BEARER_TOKEN")
        if alexa_token:
            cfg["alexa_bearer_token"] = alexa_token

        # Default timezone configuration
        default_tz = os.environ.get("CALENDARBOT_DEFAULT_TIMEZONE")
        if default_tz:
            cfg["default_timezone"] = default_tz

        return cfg

    def load_full_config(self) -> dict[str, Any]:
        """Load .env file and build configuration from environment.

        This is the main entry point for loading configuration.

        Returns:
            Configuration dictionary
        """
        # Load .env file first (only sets if not already in environment)
        self.load_env_file()

        # Build configuration from environment variables
        return self.build_config_from_env()


def get_default_timezone(fallback: str = "America/Los_Angeles") -> str:
    """Get default timezone from environment with validation.

    Args:
        fallback: Fallback timezone if not configured or invalid (default: America/Los_Angeles)

    Returns:
        Valid IANA timezone string

    Note:
        This function validates the timezone using zoneinfo.ZoneInfo and falls back
        to the provided fallback timezone if the configured timezone is invalid.
    """
    import zoneinfo

    # Get timezone from environment
    timezone = os.environ.get("CALENDARBOT_DEFAULT_TIMEZONE", fallback)

    # Validate timezone
    try:
        zoneinfo.ZoneInfo(timezone)
        return timezone
    except Exception:
        logger.warning(
            "Invalid timezone %r, falling back to %r", timezone, fallback, exc_info=True
        )
        return fallback


def get_config_value(config: Any, key: str, default: Any = None) -> Any:
    """Get configuration value supporting both dict and dataclass-like objects.

    Args:
        config: Configuration object (dict or object with attributes)
        key: Configuration key to retrieve
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    if isinstance(config, dict):
        return config.get(key, default)
    return getattr(config, key, default)
