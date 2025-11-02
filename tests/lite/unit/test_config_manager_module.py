"""Unit tests for config_manager module."""

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock
import pytest

from calendarbot_lite.config_manager import ConfigManager, get_config_value

pytestmark = pytest.mark.unit


@contextmanager
def clean_env(**env_vars):
    """Context manager to set environment variables while clearing config-related ones."""
    # List of all config env vars to clear
    config_keys = [
        "CALENDARBOT_ICS_URL",
        "CALENDARBOT_WEB_HOST",
        "CALENDARBOT_WEB_PORT",
        "CALENDARBOT_SERVER_BIND",
        "CALENDARBOT_SERVER_PORT",
        "CALENDARBOT_REFRESH_INTERVAL",
        "CALENDARBOT_REFRESH_INTERVAL_SECONDS",
        "CALENDARBOT_ALEXA_BEARER_TOKEN",
    ]

    # Save original values
    original = {key: os.environ.get(key) for key in config_keys}

    try:
        # Clear all config vars
        for key in config_keys:
            os.environ.pop(key, None)
        # Set the ones we want
        os.environ.update(env_vars)
        yield
    finally:
        # Restore original values
        for key in config_keys:
            orig_value = original[key]
            if orig_value is not None:
                os.environ[key] = orig_value
            else:
                os.environ.pop(key, None)


class TestConfigManager:
    """Tests for ConfigManager class."""

    def test_load_env_file_with_valid_file(self):
        """Should load environment variables from .env file."""
        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_VAR1=value1\n")
            f.write("TEST_VAR2=value2\n")
            f.write("# Comment line\n")
            f.write("TEST_VAR3=value3\n")
            env_file = f.name

        try:
            manager = ConfigManager(env_file_path=Path(env_file))
            loaded_vars = manager.load_env_file()

            assert "TEST_VAR1" in loaded_vars
            assert "TEST_VAR2" in loaded_vars
            assert "TEST_VAR3" in loaded_vars
        finally:
            os.unlink(env_file)

    def test_load_env_file_with_nonexistent_file(self):
        """Should handle non-existent .env file gracefully."""
        manager = ConfigManager(env_file_path=Path("/nonexistent/.env"))
        loaded_vars = manager.load_env_file()

        assert loaded_vars == []

    def test_build_config_from_env_ics_url(self):
        """Should build config from CALENDARBOT_ICS_URL environment variable."""
        with clean_env(CALENDARBOT_ICS_URL="https://example.com/calendar.ics"):
            manager = ConfigManager()
            config = manager.build_config_from_env()

            assert "ics_sources" in config
            assert len(config["ics_sources"]) == 1
            assert config["ics_sources"][0] == "https://example.com/calendar.ics"

    def test_build_config_from_env_server_settings(self):
        """Should build server config from environment variables."""
        with clean_env(
            CALENDARBOT_SERVER_BIND="127.0.0.1",
            CALENDARBOT_SERVER_PORT="9090",
        ):
            manager = ConfigManager()
            config = manager.build_config_from_env()

            assert config["server_bind"] == "127.0.0.1"
            assert config["server_port"] == 9090

    def test_build_config_from_env_refresh_interval(self):
        """Should build refresh interval from environment variable."""
        with clean_env(CALENDARBOT_REFRESH_INTERVAL_SECONDS="120"):
            manager = ConfigManager()
            config = manager.build_config_from_env()

            assert config["refresh_interval_seconds"] == 120

    def test_build_config_from_env_bearer_token(self):
        """Should build bearer token from environment variable."""
        with clean_env(CALENDARBOT_ALEXA_BEARER_TOKEN="secret-token-123"):
            manager = ConfigManager()
            config = manager.build_config_from_env()

            assert config["alexa_bearer_token"] == "secret-token-123"

    def test_load_full_config_with_env_only(self):
        """Should load full config from environment variables."""
        with clean_env(
            CALENDARBOT_ICS_URL="https://example.com/calendar.ics",
            CALENDARBOT_SERVER_PORT="8080",
        ):
            manager = ConfigManager()
            config = manager.load_full_config()

            assert "ics_sources" in config
            assert config["server_port"] == 8080

    def test_load_full_config_with_env_file(self):
        """Should load config from .env file and environment."""
        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("CALENDARBOT_ICS_URL=https://fromfile.com/calendar.ics\n")
            f.write("CALENDARBOT_SERVER_PORT=9090\n")
            env_file = f.name

        try:
            # Override with environment variable (should take precedence)
            with clean_env(CALENDARBOT_SERVER_PORT="8080"):
                manager = ConfigManager(env_file_path=Path(env_file))
                config = manager.load_full_config()

                # Environment variable should take precedence
                assert config["server_port"] == 8080
                # But ICS URL from file should be there
                assert "ics_sources" in config
        finally:
            os.unlink(env_file)


class TestGetConfigValue:
    """Tests for get_config_value helper function."""

    def test_get_config_value_from_dict(self):
        """Should get value from dictionary config."""
        config = {"key1": "value1", "key2": 42}

        assert get_config_value(config, "key1") == "value1"
        assert get_config_value(config, "key2") == 42

    def test_get_config_value_from_dataclass(self):
        """Should get value from dataclass-like object."""
        mock_config = Mock()
        mock_config.key1 = "value1"
        mock_config.key2 = 42

        assert get_config_value(mock_config, "key1") == "value1"
        assert get_config_value(mock_config, "key2") == 42

    def test_get_config_value_with_default(self):
        """Should return default when key not found."""
        config = {"key1": "value1"}

        assert get_config_value(config, "missing_key", "default") == "default"

    def test_get_config_value_none_config(self):
        """Should return default for None config."""
        assert get_config_value(None, "key", "default") == "default"

    def test_get_config_value_with_none_value(self):
        """Should return None value if key exists with None."""
        config = {"key1": None}

        # Should return None, not the default
        assert get_config_value(config, "key1", "default") is None

    def test_get_config_value_attribute_error(self):
        """Should return default on attribute error."""
        mock_config = Mock(spec=['key1'])
        mock_config.key1 = "value1"
        # Don't set key2, so getattr will fail with AttributeError

        assert get_config_value(mock_config, "key2", "default") == "default"
