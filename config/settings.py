"""Settings management using Pydantic for type validation and configuration."""

from pathlib import Path
from typing import Optional, Any, Dict
from pydantic import Field
from pydantic_settings import BaseSettings
import os
import yaml


class CalendarBotSettings(BaseSettings):
    """Application settings with environment variable support."""
    
    # ICS Calendar Configuration
    ics_url: Optional[str] = Field(default=None, description="ICS calendar URL")
    ics_refresh_interval: int = Field(default=300, description="ICS fetch interval in seconds (5 minutes)")
    ics_timeout: int = Field(default=30, description="HTTP timeout for ICS requests")
    
    # ICS Authentication (optional)
    ics_auth_type: Optional[str] = Field(default=None, description="Auth type: basic, bearer, or null")
    ics_username: Optional[str] = Field(default=None, description="Basic auth username")
    ics_password: Optional[str] = Field(default=None, description="Basic auth password")
    ics_bearer_token: Optional[str] = Field(default=None, description="Bearer token")
    
    # ICS Advanced Settings
    ics_validate_ssl: bool = Field(default=True, description="Validate SSL certificates")
    ics_enable_caching: bool = Field(default=True, description="Enable HTTP caching")
    ics_filter_busy_only: bool = Field(default=True, description="Only show busy/tentative events")
    
    # Application Configuration
    app_name: str = Field(default="CalendarBot", description="Application name")
    refresh_interval: int = Field(default=300, description="Refresh interval in seconds (5 minutes)")
    cache_ttl: int = Field(default=3600, description="Cache time-to-live in seconds (1 hour)")
    
    # File Paths
    config_dir: Path = Field(default_factory=lambda: Path.home() / ".config" / "calendarbot")
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".local" / "share" / "calendarbot")
    cache_dir: Path = Field(default_factory=lambda: Path.home() / ".cache" / "calendarbot")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    
    # Display Settings
    display_enabled: bool = Field(default=True, description="Enable display output")
    display_type: str = Field(default="console", description="Display type: console, eink")
    
    # Network and Retry Settings
    request_timeout: int = Field(default=30, description="HTTP request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_backoff_factor: float = Field(default=1.5, description="Exponential backoff factor")
    
    class Config:
        env_prefix = "CALENDARBOT_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load YAML configuration
        self._load_yaml_config()
    
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
    
    def _load_yaml_config(self):
        """Load configuration from YAML file if it exists."""
        config_file = self._find_config_file()
        if not config_file:
            return
        
        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                return
            
            # Map YAML structure to settings fields
            if 'ics' in config_data:
                ics_config = config_data['ics']
                if 'url' in ics_config and not self.ics_url:
                    self.ics_url = ics_config['url']
                if 'auth_type' in ics_config and not self.ics_auth_type:
                    self.ics_auth_type = ics_config['auth_type']
                if 'username' in ics_config and not self.ics_username:
                    self.ics_username = ics_config['username']
                if 'password' in ics_config and not self.ics_password:
                    self.ics_password = ics_config['password']
                if 'token' in ics_config and not self.ics_bearer_token:
                    self.ics_bearer_token = ics_config['token']
                if 'verify_ssl' in ics_config:
                    self.ics_validate_ssl = ics_config['verify_ssl']
            
            # Map other top-level settings
            if 'refresh_interval' in config_data:
                self.refresh_interval = config_data['refresh_interval']
            if 'cache_ttl' in config_data:
                self.cache_ttl = config_data['cache_ttl']
            if 'log_level' in config_data:
                self.log_level = config_data['log_level']
            if 'log_file' in config_data:
                self.log_file = config_data['log_file']
            if 'display_enabled' in config_data:
                self.display_enabled = config_data['display_enabled']
            if 'display_type' in config_data:
                self.display_type = config_data['display_type']
            if 'request_timeout' in config_data:
                self.request_timeout = config_data['request_timeout']
            if 'max_retries' in config_data:
                self.max_retries = config_data['max_retries']
            if 'retry_backoff_factor' in config_data:
                self.retry_backoff_factor = config_data['retry_backoff_factor']
                
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