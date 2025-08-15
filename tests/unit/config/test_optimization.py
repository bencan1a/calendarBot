"""Unit tests for the optimization configuration module."""

import os
from unittest.mock import patch

from calendarbot.config.optimization import (
    OptimizationConfig,
    get_optimization_config,
    reset_optimization_config,
)


class TestOptimizationConfig:
    """Tests for the OptimizationConfig class."""

    def test_optimization_config_initialization_with_defaults(self) -> None:
        """Test OptimizationConfig initialization with default values."""
        config = OptimizationConfig()

        # Connection pool settings
        assert config.max_connections == 20
        assert config.max_connections_per_host == 30
        assert config.connection_ttl == 300

        # Cache settings
        assert config.cache_ttl == 300
        assert config.cache_maxsize == 500

        # Performance thresholds
        assert config.memory_warning_threshold_mb == 150
        assert config.latency_warning_threshold_ms == 200
        assert config.cache_hit_rate_warning == 0.5

    def test_optimization_config_initialization_with_environment_variables(self) -> None:
        """Test OptimizationConfig initialization with environment variables."""
        env_vars = {
            "CALENDARBOT_OPT_MAX_CONNECTIONS": "50",
            "CALENDARBOT_OPT_MAX_CONNECTIONS_PER_HOST": "15",
            "CALENDARBOT_OPT_CONNECTION_TTL": "600",
            "CALENDARBOT_OPT_CACHE_TTL": "900",
            "CALENDARBOT_OPT_CACHE_MAXSIZE": "2000",
            "CALENDARBOT_OPT_MEMORY_WARNING_THRESHOLD_MB": "512",
            "CALENDARBOT_OPT_LATENCY_WARNING_THRESHOLD_MS": "150",
            "CALENDARBOT_OPT_CACHE_HIT_RATE_WARNING": "0.7",
        }

        with patch.dict(os.environ, env_vars):
            config = OptimizationConfig()

            assert config.max_connections == 50
            assert config.max_connections_per_host == 15
            assert config.connection_ttl == 600
            assert config.cache_ttl == 900
            assert config.cache_maxsize == 2000
            assert config.memory_warning_threshold_mb == 512
            assert config.latency_warning_threshold_ms == 150
            assert config.cache_hit_rate_warning == 0.7

    def test_optimization_config_invalid_environment_variables(self) -> None:
        """Test OptimizationConfig with invalid environment variables falls back to defaults."""
        env_vars = {
            "CALENDARBOT_OPT_MAX_CONNECTIONS": "invalid",
            "CALENDARBOT_OPT_CACHE_HIT_RATE_WARNING": "not_a_float",
        }

        with patch.dict(os.environ, env_vars):
            config = OptimizationConfig()

            # Should use defaults for invalid values
            assert config.max_connections == 20
            assert config.cache_hit_rate_warning == 0.5

    def test_environment_variables_override_defaults(self) -> None:
        """Test that environment variables override default values."""
        env_vars = {
            "CALENDARBOT_OPT_MAX_CONNECTIONS": "50",
            "CALENDARBOT_OPT_CACHE_MAXSIZE": "1500",
        }

        with patch.dict(os.environ, env_vars):
            config = OptimizationConfig()

            # Environment variables should override defaults
            assert config.max_connections == 50
            assert config.cache_maxsize == 1500
            # Other values should remain at defaults
            assert config.memory_warning_threshold_mb == 150

    def test_get_env_int_with_valid_value(self) -> None:
        """Test _get_env_int with valid integer value."""
        with patch.dict(os.environ, {"TEST_VAR": "42"}):
            config = OptimizationConfig()
            result = config._get_env_int("TEST_VAR", 10)
            assert result == 42

    def test_get_env_int_with_invalid_value(self) -> None:
        """Test _get_env_int with invalid integer value."""
        with patch.dict(os.environ, {"TEST_VAR": "not_an_int"}):
            config = OptimizationConfig()
            result = config._get_env_int("TEST_VAR", 10)
            assert result == 10

    def test_get_env_int_with_missing_value(self) -> None:
        """Test _get_env_int with missing environment variable."""
        config = OptimizationConfig()
        result = config._get_env_int("MISSING_VAR", 10)
        assert result == 10

    def test_get_env_float_with_valid_value(self) -> None:
        """Test _get_env_float with valid float value."""
        with patch.dict(os.environ, {"TEST_VAR": "3.14"}):
            config = OptimizationConfig()
            result = config._get_env_float("TEST_VAR", 1.0)
            assert result == 3.14

    def test_get_env_float_with_invalid_value(self) -> None:
        """Test _get_env_float with invalid float value."""
        with patch.dict(os.environ, {"TEST_VAR": "not_a_float"}):
            config = OptimizationConfig()
            result = config._get_env_float("TEST_VAR", 1.0)
            assert result == 1.0

    def test_get_env_float_with_missing_value(self) -> None:
        """Test _get_env_float with missing environment variable."""
        config = OptimizationConfig()
        result = config._get_env_float("MISSING_VAR", 1.0)
        assert result == 1.0


class TestGlobalFunctions:
    """Tests for global functions in the optimization module."""

    def test_get_optimization_config_creates_new_instance(self) -> None:
        """Test get_optimization_config creates a new instance if none exists."""
        # Reset global config to None
        reset_optimization_config()

        config = get_optimization_config()

        assert isinstance(config, OptimizationConfig)
        assert config.max_connections == 20  # Default value

    def test_get_optimization_config_returns_existing_instance(self) -> None:
        """Test get_optimization_config returns existing instance if one exists."""
        # Get first instance
        config1 = get_optimization_config()
        # Get second instance
        config2 = get_optimization_config()

        # Should be the same instance
        assert config1 is config2

    def test_reset_optimization_config(self) -> None:
        """Test reset_optimization_config clears the global instance."""
        # Create an instance
        config1 = get_optimization_config()
        assert config1 is not None

        # Reset and create new instance
        reset_optimization_config()
        config2 = get_optimization_config()

        # Should be different instances
        assert config1 is not config2

    def test_get_optimization_config_with_custom_config(self) -> None:
        """Test get_optimization_config with custom config parameter."""
        custom_config = OptimizationConfig()
        custom_config.max_connections = 42

        # Should return the custom config
        config = get_optimization_config(custom_config)
        assert config is custom_config
        assert config.max_connections == 42
