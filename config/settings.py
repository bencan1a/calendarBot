"""Settings management using Pydantic for type validation and configuration."""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Pattern, Type, Union

import yaml
from pydantic import BaseModel, Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    PYDANTIC_V2 = True
    SettingsConfigDictType = SettingsConfigDict
except ImportError:
    from pydantic import BaseSettings  # type: ignore

    PYDANTIC_V2 = False
    SettingsConfigDictType = None  # type: ignore


def _get_safe_web_host() -> str:
    """Get a safe default web host, preferring local network interface over 0.0.0.0."""
    try:
        from calendarbot.utils.network import get_local_network_interface

        return get_local_network_interface()
    except ImportError:
        # Fallback to localhost if network utils not available
        return "127.0.0.1"


# Security logging fallbacks - avoid name conflicts with imports
def _mask_credentials_fallback(
    text: str, custom_patterns: Optional[Dict[str, Pattern[Any]]] = None
) -> str:
    """Fallback credential masking function."""
    if not text:
        return text
    return text[:2] + "*" * (len(text) - 4) + text[-2:] if len(text) > 4 else "***"


class _SecurityEventLoggerFallback:
    """Fallback security event logger."""

    def log_event(self, event: Any) -> None:
        pass


class _SecurityEventFallback:
    """Fallback security event."""

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


class _SecurityEventTypeFallback:
    """Fallback security event type."""

    SYSTEM_CREDENTIAL_ACCESS = "credential_access"


class _SecuritySeverityFallback:
    """Fallback security severity."""

    LOW = "low"


# Import security logging for credential masking with fallbacks
try:
    from calendarbot.security.logging import (
        SecurityEvent,
        SecurityEventLogger,
        SecurityEventType,
        SecuritySeverity,
        mask_credentials,
    )
except ImportError:
    # Use fallback implementations
    mask_credentials = _mask_credentials_fallback
    SecurityEventLogger = _SecurityEventLoggerFallback  # type: ignore
    SecurityEvent = _SecurityEventFallback  # type: ignore
    SecurityEventType = _SecurityEventTypeFallback()  # type: ignore
    SecuritySeverity = _SecuritySeverityFallback()  # type: ignore


class LoggingSettings(BaseModel):
    """Comprehensive logging configuration settings."""

    # Console Logging
    console_enabled: bool = Field(default=True, description="Enable console logging")
    console_level: str = Field(
        default="INFO",
        description="Console log level: DEBUG, VERBOSE, INFO, WARNING, ERROR, CRITICAL",
    )
    console_colors: bool = Field(
        default=True, description="Enable colored console output (auto-detected)"
    )

    # File Logging
    file_enabled: bool = Field(default=True, description="Enable file logging")
    file_level: str = Field(
        default="DEBUG",
        description="File log level: DEBUG, VERBOSE, INFO, WARNING, ERROR, CRITICAL",
    )
    file_directory: Optional[str] = Field(
        default=None, description="Custom log directory (defaults to data_dir/logs)"
    )
    file_prefix: str = Field(default="calendarbot", description="Log file prefix")
    max_log_files: int = Field(default=5, description="Maximum number of log files to keep")
    include_function_names: bool = Field(
        default=True, description="Include function names and line numbers in file logs"
    )

    # Interactive Mode
    interactive_split_display: bool = Field(
        default=True, description="Use split display in interactive mode"
    )
    interactive_log_lines: int = Field(
        default=5, description="Number of log lines to show in interactive mode"
    )

    # Third-party Libraries
    third_party_level: str = Field(
        default="WARNING", description="Log level for third-party libraries"
    )

    # Security Logging
    security_enabled: bool = Field(default=True, description="Enable security event logging")
    security_level: str = Field(default="INFO", description="Security event log level")
    security_mask_credentials: bool = Field(
        default=True, description="Mask credentials in security logs"
    )
    security_track_auth: bool = Field(default=True, description="Track authentication events")
    security_track_input_validation: bool = Field(
        default=True, description="Track input validation failures"
    )

    # Performance Monitoring
    performance_enabled: bool = Field(default=True, description="Enable performance monitoring")
    performance_level: str = Field(default="INFO", description="Performance monitoring log level")
    performance_timing_threshold: float = Field(
        default=1.0, description="Log operations slower than this (seconds)"
    )
    performance_memory_threshold: int = Field(
        default=50, description="Log memory usage over this (MB)"
    )
    performance_cache_monitoring: bool = Field(
        default=True, description="Enable cache performance monitoring"
    )

    # Structured Logging
    structured_enabled: bool = Field(default=True, description="Enable structured logging")
    structured_format: bool = Field(default=False, description="Use JSON format for file logs")
    structured_correlation_ids: bool = Field(
        default=True, description="Enable correlation ID tracking"
    )
    structured_context_tracking: bool = Field(default=True, description="Enable context tracking")

    # Production Optimization
    production_mode: bool = Field(default=False, description="Enable production optimization mode")
    production_filter_debug: bool = Field(
        default=True, description="Filter debug statements in production"
    )
    production_rate_limit: int = Field(
        default=100, description="Rate limit for log messages per minute"
    )
    production_max_message_length: int = Field(
        default=1000, description="Maximum log message length"
    )
    production_remove_obsolete: bool = Field(
        default=True, description="Remove obsolete debug statements"
    )

    # Advanced Options
    buffer_size: int = Field(default=100, description="Log message buffer size")
    flush_interval: float = Field(default=1.0, description="Log flush interval in seconds")


class CalendarBotSettings(BaseSettings):
    """Application settings with environment variable support."""

    # ICS Calendar Configuration
    ics_url: Optional[str] = Field(default=None, description="ICS calendar URL")
    ics_refresh_interval: int = Field(
        default=300, description="ICS fetch interval in seconds (5 minutes)"
    )
    ics_timeout: int = Field(default=30, description="HTTP timeout for ICS requests")

    # ICS Authentication (optional)
    ics_auth_type: Optional[str] = Field(
        default=None, description="Auth type: basic, bearer, or null"
    )
    ics_username: Optional[str] = Field(default=None, description="Basic auth username")
    ics_password: Optional[str] = Field(default=None, description="Basic auth password")
    ics_bearer_token: Optional[str] = Field(default=None, description="Bearer token")
    ics_custom_headers: Optional[str] = Field(
        default=None, description="Custom HTTP headers as JSON string"
    )

    # ICS Advanced Settings
    ics_validate_ssl: bool = Field(default=True, description="Validate SSL certificates")
    ics_enable_caching: bool = Field(default=True, description="Enable HTTP caching")
    ics_filter_busy_only: bool = Field(default=True, description="Only show busy/tentative events")

    # Application Configuration
    app_name: str = Field(default="CalendarBot", description="Application name")
    refresh_interval: int = Field(
        default=300, description="Refresh interval in seconds (5 minutes)"
    )
    cache_ttl: int = Field(default=3600, description="Cache time-to-live in seconds (1 hour)")
    auto_kill_existing: bool = Field(
        default=True, description="Automatically kill existing calendarbot processes on startup"
    )

    # File Paths
    config_dir: Path = Field(default_factory=lambda: Path.home() / ".config" / "calendarbot")
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".local" / "share" / "calendarbot")
    cache_dir: Path = Field(default_factory=lambda: Path.home() / ".cache" / "calendarbot")

    # Logging Configuration
    logging: LoggingSettings = Field(
        default_factory=LoggingSettings, description="Comprehensive logging settings"
    )

    # Legacy logging fields (maintained for backward compatibility)
    log_level: Optional[str] = Field(
        default=None, description="Legacy: Use logging.console_level instead"
    )
    log_file: Optional[str] = Field(
        default=None, description="Legacy: Use logging.file_enabled instead"
    )

    # Display Settings
    display_enabled: bool = Field(default=True, description="Enable display output")
    display_type: str = Field(
        default="console", description="Renderer type: console, html, rpi, compact"
    )

    # Raspberry Pi E-ink Display Settings
    rpi_enabled: bool = Field(default=False, description="Enable Raspberry Pi e-ink mode")
    rpi_display_width: int = Field(default=480, description="RPI display width in pixels")
    rpi_display_height: int = Field(default=800, description="RPI display height in pixels")
    rpi_refresh_mode: str = Field(
        default="partial", description="E-ink refresh mode: partial, full"
    )
    rpi_auto_layout: bool = Field(
        default=True, description="Auto-optimize layout for e-ink display"
    )

    # Compact E-ink Display Settings (300x400)
    compact_eink_enabled: bool = Field(default=False, description="Enable compact e-ink mode")
    compact_eink_display_width: int = Field(
        default=300, description="Compact e-ink display width in pixels"
    )
    compact_eink_display_height: int = Field(
        default=400, description="Compact e-ink display height in pixels"
    )
    compact_eink_refresh_mode: str = Field(
        default="partial", description="Compact e-ink refresh mode: partial, full"
    )
    compact_eink_auto_layout: bool = Field(
        default=True, description="Auto-optimize layout for compact e-ink display"
    )
    compact_eink_content_truncation: bool = Field(
        default=True, description="Enable content truncation for compact display"
    )

    # Web/HTML Display Settings
    web_enabled: bool = Field(default=False, description="Enable web server for HTML display")
    web_port: int = Field(default=8080, description="Port for web server")
    web_host: str = Field(
        default_factory=lambda: _get_safe_web_host(), description="Host address for web server"
    )
    web_layout: str = Field(default="4x8", description="Web layout: 4x8, 3x4")
    layout_name: str = Field(
        default="4x8", description="Current layout name (alias for web_layout)"
    )
    web_auto_refresh: int = Field(default=60, description="Auto-refresh interval in seconds")

    # Network and Retry Settings
    request_timeout: int = Field(default=30, description="HTTP request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_backoff_factor: float = Field(default=1.5, description="Exponential backoff factor")

    if PYDANTIC_V2 and SettingsConfigDictType is not None:
        model_config = SettingsConfigDictType(
            env_prefix="CALENDARBOT_",
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
        )
    else:
        # For older pydantic versions, use Config class
        class Config:
            env_prefix = "CALENDARBOT_"
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load YAML configuration
        self._load_yaml_config()

        # Sync layout_name with web_layout
        self.layout_name = self.web_layout

        # Validate required configuration
        self._validate_required_config()

    def _validate_required_config(self) -> None:
        """Validate that required configuration is present."""
        if not self.ics_url:
            raise ValueError(
                "ICS URL is required but not configured. "
                "Please set CALENDARBOT_ICS_URL environment variable or configure 'ics.url' in config.yaml"
            )

    def _find_config_file(self) -> Optional[Path]:
        """Find config file, checking project directory first, then user home."""
        # Check project directory first (relative to this file)
        project_config = Path(__file__).parent / "config.yaml"
        if project_config.exists():
            return project_config

        # Fall back to user home directory
        user_config = self.config_dir / "config.yaml"
        if user_config.exists():
            return user_config

        return None

    def _load_yaml_config(self) -> None:
        """Load configuration from YAML file if it exists."""
        config_file = self._find_config_file()
        if not config_file:
            return

        try:
            with open(config_file, "r") as f:
                config_data = yaml.safe_load(f)

            if not config_data:
                return

            # Map YAML structure to settings fields
            if "ics" in config_data:
                ics_config = config_data["ics"]
                if "url" in ics_config and not self.ics_url:
                    self.ics_url = ics_config["url"]
                if "auth_type" in ics_config and not self.ics_auth_type:
                    self.ics_auth_type = ics_config["auth_type"]
                if "username" in ics_config and not self.ics_username:
                    username = ics_config["username"]
                    self.ics_username = username
                    # Log credential loading with masking
                    security_logger = SecurityEventLogger()
                    event = SecurityEvent(
                        event_type=SecurityEventType.SYSTEM_CREDENTIAL_ACCESS,
                        severity=SecuritySeverity.LOW,
                        action="credential_load",
                        result="success",
                        details={
                            "credential_type": "username",
                            "description": f"ICS username loaded from config: {mask_credentials(username)}",
                            "source_ip": "internal",
                        },
                    )
                    security_logger.log_event(event)
                if "password" in ics_config and not self.ics_password:
                    password = ics_config["password"]
                    self.ics_password = password
                    # Log credential loading with masking
                    security_logger = SecurityEventLogger()
                    event = SecurityEvent(
                        event_type=SecurityEventType.SYSTEM_CREDENTIAL_ACCESS,
                        severity=SecuritySeverity.LOW,
                        action="credential_load",
                        result="success",
                        details={
                            "credential_type": "password",
                            "description": f"ICS password loaded from config: {mask_credentials(password)}",
                            "source_ip": "internal",
                        },
                    )
                    security_logger.log_event(event)
                if "token" in ics_config and not self.ics_bearer_token:
                    token = ics_config["token"]
                    self.ics_bearer_token = token
                    # Log credential loading with masking
                    security_logger = SecurityEventLogger()
                    event = SecurityEvent(
                        event_type=SecurityEventType.SYSTEM_CREDENTIAL_ACCESS,
                        severity=SecuritySeverity.LOW,
                        action="credential_load",
                        result="success",
                        details={
                            "credential_type": "bearer_token",
                            "description": f"ICS bearer token loaded from config: {mask_credentials(token)}",
                            "source_ip": "internal",
                        },
                    )
                    security_logger.log_event(event)
                if "custom_headers" in ics_config and not self.ics_custom_headers:
                    import json

                    try:
                        # Convert dict to JSON string if needed
                        headers = ics_config["custom_headers"]
                        if isinstance(headers, dict):
                            self.ics_custom_headers = json.dumps(headers)
                        else:
                            self.ics_custom_headers = str(headers)
                    except Exception:
                        # If conversion fails, skip custom headers
                        pass
                if "verify_ssl" in ics_config:
                    self.ics_validate_ssl = ics_config["verify_ssl"]

            # Map other top-level settings
            if "refresh_interval" in config_data:
                self.refresh_interval = config_data["refresh_interval"]
            if "cache_ttl" in config_data:
                self.cache_ttl = config_data["cache_ttl"]
            if "auto_kill_existing" in config_data:
                self.auto_kill_existing = config_data["auto_kill_existing"]

            # Legacy logging settings (backward compatibility)
            if "log_level" in config_data:
                self.log_level = config_data["log_level"]
                self.logging.console_level = config_data["log_level"]
                self.logging.file_level = config_data["log_level"]
            if "log_file" in config_data:
                self.log_file = config_data["log_file"]
                if config_data["log_file"]:
                    self.logging.file_enabled = True

            # New comprehensive logging settings
            if "logging" in config_data:
                logging_config = config_data["logging"]

                # Console settings
                if "console_enabled" in logging_config:
                    self.logging.console_enabled = logging_config["console_enabled"]
                if "console_level" in logging_config:
                    self.logging.console_level = logging_config["console_level"]
                if "console_colors" in logging_config:
                    self.logging.console_colors = logging_config["console_colors"]

                # File settings
                if "file_enabled" in logging_config:
                    self.logging.file_enabled = logging_config["file_enabled"]
                if "file_level" in logging_config:
                    self.logging.file_level = logging_config["file_level"]
                if "file_directory" in logging_config:
                    self.logging.file_directory = logging_config["file_directory"]
                if "file_prefix" in logging_config:
                    self.logging.file_prefix = logging_config["file_prefix"]
                if "max_log_files" in logging_config:
                    self.logging.max_log_files = logging_config["max_log_files"]
                if "include_function_names" in logging_config:
                    self.logging.include_function_names = logging_config["include_function_names"]

                # Interactive mode settings
                if "interactive_split_display" in logging_config:
                    self.logging.interactive_split_display = logging_config[
                        "interactive_split_display"
                    ]
                if "interactive_log_lines" in logging_config:
                    self.logging.interactive_log_lines = logging_config["interactive_log_lines"]

                # Third-party and advanced settings
                if "third_party_level" in logging_config:
                    self.logging.third_party_level = logging_config["third_party_level"]
                if "buffer_size" in logging_config:
                    self.logging.buffer_size = logging_config["buffer_size"]
                if "flush_interval" in logging_config:
                    self.logging.flush_interval = logging_config["flush_interval"]

            if "display_enabled" in config_data:
                self.display_enabled = config_data["display_enabled"]
            if "display_type" in config_data:
                self.display_type = config_data["display_type"]

            # RPI Display settings
            if "rpi" in config_data:
                rpi_config = config_data["rpi"]
                if "enabled" in rpi_config:
                    self.rpi_enabled = rpi_config["enabled"]
                if "display_width" in rpi_config:
                    self.rpi_display_width = rpi_config["display_width"]
                if "display_height" in rpi_config:
                    self.rpi_display_height = rpi_config["display_height"]
                if "refresh_mode" in rpi_config:
                    self.rpi_refresh_mode = rpi_config["refresh_mode"]
                if "auto_layout" in rpi_config:
                    self.rpi_auto_layout = rpi_config["auto_layout"]
                elif "auto_theme" in rpi_config:
                    # Backward compatibility: map old "auto_theme" to new "auto_layout"
                    self.rpi_auto_layout = rpi_config["auto_theme"]

            # Web settings
            if "web" in config_data:
                web_config = config_data["web"]
                if "enabled" in web_config:
                    self.web_enabled = web_config["enabled"]
                if "port" in web_config:
                    self.web_port = web_config["port"]
                if "host" in web_config:
                    self.web_host = web_config["host"]
                if "layout" in web_config:
                    self.web_layout = web_config["layout"]
                elif "theme" in web_config:
                    # Backward compatibility: map old "theme" to new "layout"
                    self.web_layout = web_config["theme"]
                if "auto_refresh" in web_config:
                    self.web_auto_refresh = web_config["auto_refresh"]
            if "request_timeout" in config_data:
                self.request_timeout = config_data["request_timeout"]
            if "max_retries" in config_data:
                self.max_retries = config_data["max_retries"]
            if "retry_backoff_factor" in config_data:
                self.retry_backoff_factor = config_data["retry_backoff_factor"]

        except Exception as e:
            # Don't fail if YAML loading fails, just continue with defaults/env vars
            print(f"Warning: Could not load YAML config from {config_file}: {e}")

    @property
    def database_file(self) -> Path:
        """Path to SQLite database file."""
        return self.data_dir / "calendar_cache.db"

    @property
    def config_file(self) -> Path:
        """Path to YAML configuration file."""
        return self.config_dir / "config.yaml"

    @property
    def ics_cache_file(self) -> Path:
        """Path to ICS cache metadata file."""
        return self.cache_dir / "ics_cache.json"


# Global settings instance
settings = CalendarBotSettings()
