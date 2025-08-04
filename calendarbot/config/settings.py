"""Settings management using Pydantic for type validation and configuration."""

import logging
import os
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING, Any, Optional, cast

import yaml
from pydantic import BaseModel, Field, PrivateAttr

if TYPE_CHECKING:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    PYDANTIC_V2 = True
    SettingsConfigDictType = SettingsConfigDict
else:
    try:
        from pydantic_settings import BaseSettings, SettingsConfigDict

        PYDANTIC_V2 = True
        SettingsConfigDictType = SettingsConfigDict
    except ImportError:
        from pydantic import BaseSettings  # type: ignore

        PYDANTIC_V2 = False
        SettingsConfigDictType = None  # type: ignore

# Type alias for proper typing
SettingsBase = BaseSettings


def _get_safe_web_host() -> str:
    """Get a safe default web host, preferring local network interface over 0.0.0.0."""
    try:
        from calendarbot.utils.network import get_local_network_interface  # noqa: PLC0415

        return get_local_network_interface()
    except ImportError:
        # Fallback to localhost if network utils not available
        return "127.0.0.1"


# Security logging fallbacks - avoid name conflicts with imports
def _mask_credentials_fallback(
    text: str, custom_patterns: Optional[dict[str, Pattern[Any]]] = None
) -> str:
    """Fallback credential masking function."""
    # custom_patterns parameter is kept for API compatibility but not used in fallback
    _ = custom_patterns  # Suppress unused argument warning
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

    SECURITY_LOGGING_AVAILABLE = True
except ImportError:
    # Use fallback implementations
    mask_credentials = _mask_credentials_fallback
    SecurityEventLogger = _SecurityEventLoggerFallback  # type: ignore
    SecurityEvent = _SecurityEventFallback  # type: ignore
    SecurityEventType = _SecurityEventTypeFallback()  # type: ignore
    SecuritySeverity = _SecuritySeverityFallback()  # type: ignore
    SECURITY_LOGGING_AVAILABLE = False


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


class RuntimeTrackingSettings(BaseModel):
    """Runtime resource tracking configuration settings."""

    # Core Settings
    enabled: bool = Field(default=False, description="Enable runtime resource tracking")
    sampling_interval: float = Field(
        default=1.0, description="Resource sampling interval in seconds"
    )
    save_samples: bool = Field(
        default=True, description="Save resource samples to performance tracking system"
    )
    session_name: Optional[str] = Field(default=None, description="Session name for tracking data")

    # Advanced Settings
    memory_threshold_mb: int = Field(
        default=100, description="Memory usage threshold for logging warnings (MB)"
    )
    cpu_threshold_percent: float = Field(
        default=80.0, description="CPU usage threshold for logging warnings (%)"
    )
    max_samples: int = Field(
        default=10000, description="Maximum number of samples to collect per session"
    )


class EpaperConfiguration(BaseModel):
    """Core e-Paper display configuration within CalendarBot settings."""

    # Core Settings
    enabled: bool = Field(default=True, description="Enable e-Paper functionality")
    force_epaper: bool = Field(
        default=False, description="Force use of e-Paper renderer regardless of device detection"
    )
    display_model: Optional[str] = Field(
        default=None, description="E-Paper display model (e.g., 'waveshare_4_2', 'waveshare_7_5')"
    )

    # Display Properties
    width: int = Field(default=400, description="Display width in pixels")
    height: int = Field(default=300, description="Display height in pixels")
    rotation: int = Field(default=0, description="Display rotation in degrees (0, 90, 180, 270)")

    # Refresh Settings
    partial_refresh: bool = Field(
        default=True, description="Enable partial refresh for e-Paper displays"
    )
    refresh_interval: int = Field(
        default=300, description="Full refresh interval for e-Paper displays in seconds"
    )

    # Rendering Options
    contrast_level: int = Field(
        default=100, description="Contrast level for e-Paper displays (0-100)"
    )
    dither_mode: str = Field(
        default="floyd_steinberg", description="Dithering mode: none, floyd_steinberg, ordered"
    )

    # Fallback and Error Handling
    error_fallback: bool = Field(
        default=True, description="Fallback to console renderer on e-Paper errors"
    )
    png_fallback_enabled: bool = Field(default=True, description="Enable PNG fallback output")
    png_output_path: str = Field(
        default="epaper_output.png", description="PNG fallback output path"
    )

    # Hardware Detection
    hardware_detection_enabled: bool = Field(
        default=True, description="Enable hardware auto-detection"
    )

    # Advanced Settings
    update_strategy: str = Field(
        default="adaptive", description="Update strategy: full, partial, adaptive"
    )


class CalendarBotSettings(BaseSettings):
    """Application settings with environment variable support."""

    # Private attributes
    _explicit_args: set = PrivateAttr(default_factory=set)

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

    # Runtime Tracking Configuration
    runtime_tracking: RuntimeTrackingSettings = Field(
        default_factory=RuntimeTrackingSettings, description="Runtime resource tracking settings"
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
        default="console", description="Renderer type: console, html, whats-next, epaper, rpi, compact, eink-whats-next"
    )

    # Generic Display Dimensions (used by tests and some renderers)
    display_width: int = Field(default=800, description="Generic display width in pixels")
    display_height: int = Field(default=600, description="Generic display height in pixels")
    compact_display_width: int = Field(default=400, description="Compact display width in pixels")
    compact_display_height: int = Field(default=300, description="Compact display height in pixels")

    # Core E-Paper Configuration
    epaper: EpaperConfiguration = Field(
        default_factory=EpaperConfiguration, description="Core e-Paper display configuration"
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
    web_layout: str = Field(
        default="whats-next-view", description="Web layout: 4x8, 3x4, whats-next-view"
    )
    layout_name: str = Field(
        default="whats-next-view", description="Current layout name (alias for web_layout)"
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
        # Check if we should ignore empty environment variables for testing
        env_ignore_empty = kwargs.pop("_env_ignore_empty", False)

        # Handle empty environment variables before Pydantic sees them
        original_env = None
        if env_ignore_empty:
            # Save original environment and create a clean copy
            original_env = {}
            for key, value in os.environ.items():
                if key.startswith("CALENDARBOT_") and not value.strip():
                    # Save the original value and remove from environment
                    original_env[key] = value
                    del os.environ[key]

        try:
            # Track which environment variables are set before calling parent
            env_vars_set = set()
            for key in os.environ:
                if key.startswith("CALENDARBOT_"):
                    env_vars_set.add(key.replace("CALENDARBOT_", "").lower())

            # Call parent constructor first to initialize Pydantic machinery
            super().__init__(**kwargs)

            # Track which arguments were explicitly provided
            self._explicit_args = set(kwargs.keys())
            self._env_vars_set = env_vars_set

            # Load YAML configuration after basic initialization
            self._load_yaml_config()

            # Note: ICS validation is now deferred until actually needed
            # This allows the app to start for help/version/setup commands

        finally:
            # Restore original environment variables if we modified them
            if original_env:
                for key, value in original_env.items():
                    os.environ[key] = value

    def _validate_ics_config(self) -> None:
        """Validate that ICS configuration is present when needed for calendar operations.

        Raises:
            ValueError: If ICS URL is not configured when calendar functionality is accessed.
        """
        if not self.ics_url:
            raise ValueError(
                "ICS URL is required for calendar operations but not configured. "
                "Please set CALENDARBOT_ICS_URL environment variable or configure 'ics.url' in config.yaml"
            )

    def _validate_required_config(self) -> None:
        """Validate that required configuration is present.

        This method is kept for backward compatibility but no longer validates ICS
        during initialization. ICS validation is now deferred until needed.
        """
        # ICS validation is now deferred - see _validate_ics_config()

    def _find_config_file(self) -> Optional[Path]:
        """Find config file, checking project directory first, then user home."""
        # Check project root directory first (go up from calendarbot/config to project root)
        project_root = Path(__file__).parent.parent.parent
        project_config = project_root / "config" / "config.yaml"
        if project_config.exists():
            return project_config

        # Fall back to user home directory
        user_config = self.config_dir / "config.yaml"
        if user_config.exists():
            return user_config

        return None

    def _log_credential_loading(self, credential_type: str, credential_value: str) -> None:
        """Log credential loading with security masking."""
        if SECURITY_LOGGING_AVAILABLE:
            from calendarbot.security.logging import (  # noqa: PLC0415
                SecurityEvent,
                SecurityEventLogger,
                SecurityEventType,
                SecuritySeverity,
            )

            security_logger = SecurityEventLogger()
            event = SecurityEvent(
                event_type=SecurityEventType.SYSTEM_CREDENTIAL_ACCESS,
                severity=SecuritySeverity.LOW,
                action="credential_load",
                result="success",
                details={
                    "credential_type": credential_type,
                    "description": f"ICS {credential_type} loaded from config: {mask_credentials(credential_value)}",
                    "source_ip": "internal",
                },
            )
            security_logger.log_event(event)

    def _load_ics_config(self, config_data: dict) -> None:
        """Load ICS configuration from YAML data."""
        if "ics" not in config_data:
            return

        ics_config = config_data["ics"]

        # Basic ICS settings
        if ("url" in ics_config and not self.ics_url and "ics_url" not in self._explicit_args):
            self.ics_url = ics_config["url"]
        if ("auth_type" in ics_config and not self.ics_auth_type and "ics_auth_type" not in self._explicit_args):
            self.ics_auth_type = ics_config["auth_type"]

        # Credentials with security logging
        if ("username" in ics_config and not self.ics_username and "ics_username" not in self._explicit_args):
            username = ics_config["username"]
            self.ics_username = username
            self._log_credential_loading("username", username)

        if ("password" in ics_config and not self.ics_password and "ics_password" not in self._explicit_args):
            password = ics_config["password"]
            self.ics_password = password
            self._log_credential_loading("password", password)

        if "token" in ics_config and not self.ics_bearer_token:
            token = ics_config["token"]
            self.ics_bearer_token = token
            self._log_credential_loading("bearer_token", token)

        # Custom headers handling
        if "custom_headers" in ics_config and not self.ics_custom_headers:
            import json  # noqa: PLC0415
            try:
                headers = ics_config["custom_headers"]
                if isinstance(headers, dict):
                    self.ics_custom_headers = json.dumps(headers)
                else:
                    self.ics_custom_headers = str(headers)
            except Exception as e:
                logging.warning(f"Failed to convert custom headers: {e}")

        if "verify_ssl" in ics_config:
            self.ics_validate_ssl = ics_config["verify_ssl"]

    def _load_basic_settings(self, config_data: dict) -> None:
        """Load basic application settings from YAML data."""
        basic_settings = ["refresh_interval", "cache_ttl", "auto_kill_existing"]

        for setting in basic_settings:
            if (setting in config_data and
                setting not in self._explicit_args and
                setting not in self._env_vars_set):
                setattr(self, setting, config_data[setting])

    def _load_legacy_logging_config(self, config_data: dict) -> None:
        """Load legacy logging settings for backward compatibility."""
        if "log_level" in config_data:
            self.log_level = config_data["log_level"]
            self.logging.console_level = config_data["log_level"]
            self.logging.file_level = config_data["log_level"]
        if "log_file" in config_data:
            self.log_file = config_data["log_file"]
            if config_data["log_file"]:
                self.logging.file_enabled = True

    def _load_logging_config(self, config_data: dict) -> None:
        """Load comprehensive logging configuration from YAML data."""
        if "logging" not in config_data:
            return

        logging_config = config_data["logging"]

        # Console settings
        console_settings = ["console_enabled", "console_level", "console_colors"]
        for setting in console_settings:
            if setting in logging_config:
                setattr(self.logging, setting, logging_config[setting])

        # File settings
        file_settings = ["file_enabled", "file_level", "file_directory",
                        "file_prefix", "max_log_files", "include_function_names"]
        for setting in file_settings:
            if setting in logging_config:
                setattr(self.logging, setting, logging_config[setting])

        # Interactive mode settings
        interactive_settings = ["interactive_split_display", "interactive_log_lines"]
        for setting in interactive_settings:
            if setting in logging_config:
                setattr(self.logging, setting, logging_config[setting])

        # Advanced settings
        advanced_settings = ["third_party_level", "buffer_size", "flush_interval"]
        for setting in advanced_settings:
            if setting in logging_config:
                setattr(self.logging, setting, logging_config[setting])

    def _load_display_settings(self, config_data: dict) -> None:
        """Load display configuration from YAML data."""
        display_settings = ["display_enabled", "display_type"]

        for setting in display_settings:
            if (setting in config_data and
                setting not in self._explicit_args and
                setting not in self._env_vars_set):
                setattr(self, setting, config_data[setting])

    def _load_rpi_config(self, config_data: dict) -> None:
        """Load RPI display configuration from YAML data."""
        if "rpi" not in config_data:
            return

        rpi_config = config_data["rpi"]
        rpi_settings = ["enabled", "display_width", "display_height", "refresh_mode", "auto_layout"]

        for setting in rpi_settings:
            if setting in rpi_config:
                setattr(self, f"rpi_{setting}", rpi_config[setting])

        # Backward compatibility for auto_theme
        if "auto_theme" in rpi_config:
            self.rpi_auto_layout = rpi_config["auto_theme"]

    def _load_web_config(self, config_data: dict) -> None:
        """Load web configuration from YAML data."""
        if "web" not in config_data:
            return

        web_config = config_data["web"]
        web_settings = ["enabled", "port", "host", "layout", "auto_refresh"]

        for setting in web_settings:
            web_field = f"web_{setting}"
            if setting in web_config and web_field not in self._explicit_args:
                setattr(self, web_field, web_config[setting])

        # Backward compatibility for theme -> layout
        if "theme" in web_config and "web_layout" not in self._explicit_args:
            self.web_layout = web_config["theme"]

    def _load_epaper_config(self, config_data: dict) -> None:
        """Load e-paper configuration from YAML data."""
        if "epaper" not in config_data:
            return

        epaper_config = config_data["epaper"]

        # Core settings
        core_settings = ["enabled", "force_epaper", "display_model"]
        for setting in core_settings:
            if setting in epaper_config:
                setattr(self.epaper, setting, epaper_config[setting])

        # Display properties
        display_props = ["width", "height", "rotation"]
        for prop in display_props:
            if prop in epaper_config:
                setattr(self.epaper, prop, epaper_config[prop])

        # Refresh and rendering settings
        refresh_settings = ["partial_refresh", "refresh_interval", "contrast_level", "dither_mode"]
        for setting in refresh_settings:
            if setting in epaper_config:
                setattr(self.epaper, setting, epaper_config[setting])

        # Fallback and advanced settings
        advanced_settings = ["error_fallback", "png_fallback_enabled", "png_output_path",
                           "hardware_detection_enabled", "update_strategy"]
        for setting in advanced_settings:
            if setting in epaper_config:
                setattr(self.epaper, setting, epaper_config[setting])


    def _load_network_settings(self, config_data: dict) -> None:
        """Load network and retry settings from YAML data."""
        network_settings = ["request_timeout", "max_retries", "retry_backoff_factor"]

        for setting in network_settings:
            if setting in config_data:
                setattr(self, setting, config_data[setting])

    def _load_yaml_config(self) -> None:
        """Load configuration from YAML file if it exists."""
        config_file = self._find_config_file()
        if not config_file:
            return

        try:
            with config_file.open() as f:
                config_data = yaml.safe_load(f)

            if not config_data:
                return

            # Load configuration in logical sections
            self._load_ics_config(config_data)
            self._load_basic_settings(config_data)
            self._load_legacy_logging_config(config_data)
            self._load_logging_config(config_data)
            self._load_display_settings(config_data)
            self._load_rpi_config(config_data)
            self._load_web_config(config_data)
            self._load_epaper_config(config_data)
            self._load_network_settings(config_data)

        except Exception as e:
            # Don't fail if YAML loading fails, just continue with defaults/env vars
            logging.warning(f"Could not load YAML config from {config_file}: {e}")


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


# Global settings management
_settings_instance: Optional[CalendarBotSettings] = None


def get_settings() -> CalendarBotSettings:
    """Get the global settings instance, creating it lazily if needed.

    Returns:
        CalendarBotSettings: The global settings instance

    Raises:
        ValueError: If settings cannot be initialized due to missing configuration
    """
    # Access module-level variable without using 'global'
    # This pattern allows reading the variable without the global keyword
    # and modifies it through direct module reference
    if globals()["_settings_instance"] is None:
        globals()["_settings_instance"] = CalendarBotSettings()
    return globals()["_settings_instance"]


def reset_settings() -> None:
    """Reset the global settings instance (primarily for testing)."""
    # Access module-level variable without using 'global'
    globals()["_settings_instance"] = None


# Backward compatibility: Provide settings attribute that initializes lazily
class _SettingsProxy:
    """
    Proxy object that provides lazy access to settings for backward compatibility.

    This proxy delegates all attribute access to the global settings instance,
    allowing for lazy initialization while maintaining full API compatibility.
    """

    def __getattr__(self, name: str) -> Any:
        return getattr(get_settings(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(get_settings(), name, value)

    def __repr__(self) -> str:
        return repr(get_settings())

    def __str__(self) -> str:
        return str(get_settings())


# Global settings instance (backward compatible)
# Type cast to CalendarBotSettings for type checking compatibility
settings = cast(CalendarBotSettings, _SettingsProxy())
