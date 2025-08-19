"""Unit tests for the optimization configuration module."""

from unittest.mock import patch

import pytest

from calendarbot.config.optimization import (
    OptimizationConfig,
    get_optimization_config,
    reset_optimization_config,
)


@pytest.fixture
def clean_optimization_config():
    """Clean up global config state before and after tests."""
    reset_optimization_config()
    yield
    reset_optimization_config()


@pytest.fixture
def sample_env_vars():
    """Standard environment variables for testing."""
    return {
        "CALENDARBOT_OPT_MAX_CONNECTIONS": "50",
        "CALENDARBOT_OPT_MAX_CONNECTIONS_PER_HOST": "15",
        "CALENDARBOT_OPT_CONNECTION_TTL": "600",
        "CALENDARBOT_OPT_CACHE_TTL": "900",
        "CALENDARBOT_OPT_CACHE_MAXSIZE": "2000",
        "CALENDARBOT_OPT_MEMORY_WARNING_THRESHOLD_MB": "512",
        "CALENDARBOT_OPT_LATENCY_WARNING_THRESHOLD_MS": "150",
        "CALENDARBOT_OPT_CACHE_HIT_RATE_WARNING": "0.7",
    }


class TestOptimizationConfig:
    """Tests for the OptimizationConfig class."""

    def test_initialization_with_defaults(self) -> None:
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

    def test_initialization_with_environment_variables(self, sample_env_vars) -> None:
        """Test OptimizationConfig initialization with environment variables."""
        with patch.dict("os.environ", sample_env_vars, clear=False):
            config = OptimizationConfig()

            assert config.max_connections == 50
            assert config.max_connections_per_host == 15
            assert config.connection_ttl == 600
            assert config.cache_ttl == 900
            assert config.cache_maxsize == 2000
            assert config.memory_warning_threshold_mb == 512
            assert config.latency_warning_threshold_ms == 150
            assert config.cache_hit_rate_warning == 0.7

    @pytest.mark.parametrize(
        "invalid_env,field,expected_default",
        [
            ({"CALENDARBOT_OPT_MAX_CONNECTIONS": "invalid"}, "max_connections", 20),
            (
                {"CALENDARBOT_OPT_CACHE_HIT_RATE_WARNING": "not_a_float"},
                "cache_hit_rate_warning",
                0.5,
            ),
            ({"CALENDARBOT_OPT_CACHE_TTL": ""}, "cache_ttl", 300),
            (
                {"CALENDARBOT_OPT_MEMORY_WARNING_THRESHOLD_MB": "invalid"},
                "memory_warning_threshold_mb",
                150,
            ),  # Another invalid case
        ],
    )
    def test_invalid_environment_variables_fallback(
        self, invalid_env, field, expected_default
    ) -> None:
        """Test OptimizationConfig with invalid environment variables falls back to defaults."""
        with patch.dict("os.environ", invalid_env, clear=False):
            config = OptimizationConfig()
            assert getattr(config, field) == expected_default

    def test_partial_environment_override(self) -> None:
        """Test that environment variables partially override defaults."""
        partial_env = {
            "CALENDARBOT_OPT_MAX_CONNECTIONS": "50",
            "CALENDARBOT_OPT_CACHE_MAXSIZE": "1500",
        }

        with patch.dict("os.environ", partial_env, clear=False):
            config = OptimizationConfig()

            # Environment variables should override defaults
            assert config.max_connections == 50
            assert config.cache_maxsize == 1500
            # Other values should remain at defaults
            assert config.memory_warning_threshold_mb == 150
            assert config.connection_ttl == 300

    def test_get_connection_pool_config(self) -> None:
        """Test connection pool configuration dict generation."""
        config = OptimizationConfig(
            max_connections=25, max_connections_per_host=35, connection_ttl=400
        )
        pool_config = config.get_connection_pool_config()

        expected = {
            "limit": 25,
            "limit_per_host": 35,
            "ttl_dns_cache": 400,
        }
        assert pool_config == expected

    def test_get_cache_config(self) -> None:
        """Test cache configuration dict generation."""
        config = OptimizationConfig(cache_maxsize=1000, cache_ttl=600)
        cache_config = config.get_cache_config()

        expected = {
            "maxsize": 1000,
            "ttl": 600,
        }
        assert cache_config == expected


class TestGlobalFunctions:
    """Tests for global functions in the optimization module."""

    def test_get_optimization_config_creates_new_instance(self, clean_optimization_config) -> None:
        """Test get_optimization_config creates a new instance if none exists."""
        config = get_optimization_config()

        assert isinstance(config, OptimizationConfig)
        assert config.max_connections == 20  # Default value

    def test_get_optimization_config_returns_existing_instance(
        self, clean_optimization_config
    ) -> None:
        """Test get_optimization_config returns existing instance if one exists."""
        # Get first instance
        config1 = get_optimization_config()
        # Get second instance
        config2 = get_optimization_config()

        # Should be the same instance
        assert config1 is config2

    def test_reset_optimization_config(self, clean_optimization_config) -> None:
        """Test reset_optimization_config clears the global instance."""
        # Create an instance
        config1 = get_optimization_config()
        assert config1 is not None

        # Reset and create new instance
        reset_optimization_config()
        config2 = get_optimization_config()

        # Should be different instances
        assert config1 is not config2

    def test_get_optimization_config_with_custom_config(self, clean_optimization_config) -> None:
        """Test get_optimization_config with custom config parameter."""
        custom_config = OptimizationConfig()
        custom_config.max_connections = 42

        # Should return the custom config
        config = get_optimization_config(custom_config)
        assert config is custom_config
        assert config.max_connections == 42
