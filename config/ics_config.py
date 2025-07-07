"""ICS-specific configuration models."""

from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ICSAuth(BaseModel):
    """ICS authentication configuration."""

    type: Optional[str] = Field(default=None, description="Auth type: basic, bearer, or null")
    username: Optional[str] = Field(default=None, description="Username for basic auth")
    password: Optional[str] = Field(default=None, description="Password for basic auth")
    bearer_token: Optional[str] = Field(default=None, description="Bearer token for auth")

    @field_validator("type")
    @classmethod
    def validate_auth_type(cls, v):
        if v is not None and v not in ["basic", "bearer"]:
            raise ValueError('auth_type must be "basic", "bearer", or null')
        return v

    @field_validator("username", "password")
    @classmethod
    def validate_basic_auth(cls, v, info):
        if info.data.get("type") == "basic":
            if info.field_name == "username" and not v:
                raise ValueError("username required for basic auth")
            if info.field_name == "password" and not v:
                raise ValueError("password required for basic auth")
        return v

    @field_validator("bearer_token")
    @classmethod
    def validate_bearer_auth(cls, v, info):
        auth_type = info.data.get("type")
        if auth_type == "bearer" and not v:
            raise ValueError("bearer_token required for bearer auth")
        return v


class ICSSourceConfig(BaseModel):
    """Configuration for an ICS calendar source."""

    # Required settings
    url: str = Field(..., description="ICS calendar URL")

    # Authentication
    auth: ICSAuth = Field(default_factory=ICSAuth, description="Authentication configuration")

    # Timing settings
    refresh_interval: int = Field(
        default=300, description="Refresh interval in seconds (5 minutes)"
    )
    timeout: int = Field(default=30, description="HTTP timeout in seconds")

    # Retry settings
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_backoff_factor: float = Field(default=1.5, description="Exponential backoff factor")

    # Advanced settings
    validate_ssl: bool = Field(default=True, description="Validate SSL certificates")
    custom_headers: Dict[str, str] = Field(default_factory=dict, description="Custom HTTP headers")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("refresh_interval")
    @classmethod
    def validate_refresh_interval(cls, v):
        if v < 60:
            raise ValueError("refresh_interval must be at least 60 seconds")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v):
        if v < 1:
            raise ValueError("timeout must be at least 1 second")
        return v


class ICSConfig(BaseModel):
    """Complete ICS configuration."""

    # Primary source
    primary_source: ICSSourceConfig = Field(..., description="Primary ICS calendar source")

    # Global settings
    cache_ttl: int = Field(default=3600, description="Cache time-to-live in seconds (1 hour)")
    enable_caching: bool = Field(
        default=True, description="Enable HTTP caching with ETag/Last-Modified"
    )

    # Parsing settings
    filter_busy_only: bool = Field(default=True, description="Only show busy/tentative events")
    expand_recurring: bool = Field(
        default=False, description="Expand recurring events (experimental)"
    )

    # Error handling
    max_consecutive_failures: int = Field(
        default=5, description="Max failures before marking unhealthy"
    )
    failure_retry_delay: int = Field(default=60, description="Delay after failure in seconds")

    model_config = ConfigDict(validate_assignment=True)

    @classmethod
    def from_settings(cls, settings) -> "ICSConfig":
        """Create ICS config from application settings.

        Args:
            settings: Application settings object

        Returns:
            ICS configuration
        """
        # Create authentication config
        auth_config = ICSAuth()

        if hasattr(settings, "ics_auth_type") and settings.ics_auth_type:
            auth_config.type = settings.ics_auth_type

            if settings.ics_auth_type == "basic":
                auth_config.username = getattr(settings, "ics_username", None)
                auth_config.password = getattr(settings, "ics_password", None)
            elif settings.ics_auth_type == "bearer":
                auth_config.bearer_token = getattr(settings, "ics_bearer_token", None)

        # Create primary source config
        primary_source = ICSSourceConfig(
            url=settings.ics_url,
            auth=auth_config,
            refresh_interval=getattr(settings, "ics_refresh_interval", 300),
            timeout=getattr(settings, "ics_timeout", 30),
            max_retries=getattr(settings, "max_retries", 3),
            retry_backoff_factor=getattr(settings, "retry_backoff_factor", 1.5),
            validate_ssl=getattr(settings, "ics_validate_ssl", True),
        )

        return cls(
            primary_source=primary_source,
            cache_ttl=getattr(settings, "cache_ttl", 3600),
            enable_caching=getattr(settings, "ics_enable_caching", True),
            filter_busy_only=getattr(settings, "ics_filter_busy_only", True),
            expand_recurring=getattr(settings, "ics_expand_recurring", False),
        )
