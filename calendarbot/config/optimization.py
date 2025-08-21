"""Optimization configuration for CalendarBot performance improvements."""

import contextlib
import os
from typing import Any, Optional

from pydantic import BaseModel, Field


class OptimizationConfig(BaseModel):
    """Configuration for connection pooling and request pipeline optimization."""

    # =============================
    # Connection Pool Configuration
    # =============================

    # aiohttp ClientSession Pool Settings
    max_connections: int = Field(
        default=20,
        ge=1,
        le=1000,
        description="Maximum total connections in aiohttp connection pool",
    )

    max_connections_per_host: int = Field(
        default=30, ge=1, le=100, description="Maximum connections per host in aiohttp pool"
    )

    connection_ttl: int = Field(
        default=300, ge=1, le=3600, description="Connection TTL in seconds for pooled connections"
    )

    # =============================
    # Request Pipeline Configuration
    # =============================

    # TTL Cache Settings
    cache_ttl: int = Field(
        default=300,
        ge=30,
        le=3600,
        description="Time-to-live for cached requests in seconds (5 minutes default)",
    )

    cache_maxsize: int = Field(
        default=500, ge=100, le=10000, description="Maximum number of cached request responses"
    )

    # =============================
    # Performance Monitoring
    # =============================

    # Performance Thresholds
    memory_warning_threshold_mb: int = Field(
        default=150, ge=50, le=1000, description="Memory usage warning threshold in MB"
    )

    latency_warning_threshold_ms: float = Field(
        default=200.0,
        ge=50.0,
        le=5000.0,
        description="Request latency warning threshold in milliseconds",
    )

    cache_hit_rate_warning: float = Field(
        default=0.5, ge=0.1, le=1.0, description="Cache hit rate warning threshold (0.0-1.0)"
    )

    def __init__(self, **kwargs: Any) -> None:
        """Initialize optimization configuration with environment variable support."""
        # Load from environment variables with CALENDARBOT_OPT_ prefix
        env_overrides = {}

        for field_name, field_info in self.model_fields.items():
            env_key = f"CALENDARBOT_OPT_{field_name.upper()}"
            env_value = os.getenv(env_key)

            if env_value is not None:
                field_type = field_info.annotation

                # Convert string environment variables to appropriate types
                if field_type is bool:
                    env_overrides[field_name] = env_value.lower() in ("true", "1", "yes", "on")
                elif field_type is int:
                    with contextlib.suppress(ValueError):
                        env_overrides[field_name] = int(env_value)
                elif field_type is float:
                    with contextlib.suppress(ValueError):
                        env_overrides[field_name] = float(env_value)
                else:
                    env_overrides[field_name] = env_value

        # Merge environment overrides with provided kwargs
        final_kwargs = {**env_overrides, **kwargs}

        super().__init__(**final_kwargs)

    def _get_env_int(self, key: str, default: int) -> int:
        """Get integer value from environment variable.

        Args:
            key: Environment variable key
            default: Default value if not found or invalid

        Returns:
            int: Environment variable value or default
        """
        try:
            value = os.getenv(key)
            if value is not None:
                return int(value)
        except ValueError:
            pass
        return default

    def _get_env_float(self, key: str, default: float) -> float:
        """Get float value from environment variable.

        Args:
            key: Environment variable key
            default: Default value if not found or invalid

        Returns:
            float: Environment variable value or default
        """
        try:
            value = os.getenv(key)
            if value is not None:
                return float(value)
        except ValueError:
            pass
        return default

    def get_connection_pool_config(self) -> dict:
        """Get configuration dict for aiohttp connection pool.

        Returns:
            dict: Configuration for aiohttp ClientConnector
        """
        return {
            "limit": self.max_connections,
            "limit_per_host": self.max_connections_per_host,
            "ttl_dns_cache": self.connection_ttl,
        }

    def get_cache_config(self) -> dict:
        """Get configuration dict for TTL cache.

        Returns:
            dict: Configuration for cachetools.TTLCache
        """
        return {
            "maxsize": self.cache_maxsize,
            "ttl": self.cache_ttl,
        }


# Global optimization configuration instance
_optimization_config: Optional[OptimizationConfig] = None


def get_optimization_config(config: Optional[OptimizationConfig] = None) -> OptimizationConfig:
    """Get the global optimization configuration instance.

    Args:
        config: Optional custom configuration to set as global

    Returns:
        OptimizationConfig: Global optimization configuration
    """
    global _optimization_config  # noqa: PLW0603
    if config is not None:
        _optimization_config = config
        return config
    if _optimization_config is None:
        _optimization_config = OptimizationConfig()
    return _optimization_config


def reset_optimization_config() -> None:
    """Reset the global optimization configuration (for testing)."""
    global _optimization_config  # noqa: PLW0603
    _optimization_config = None
