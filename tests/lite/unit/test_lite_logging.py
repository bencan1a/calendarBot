"""Tests for calendarbot_lite.lite_logging module."""

import logging
import os
from unittest.mock import patch

import pytest

from calendarbot_lite.calendar.lite_logging import (
    configure_lite_logging,
    get_logging_status,
    reset_logging_to_debug,
)

pytestmark = pytest.mark.unit


class TestConfigureLiteLogging:
    """Tests for configure_lite_logging function."""

    def test_configure_lite_logging_default_production_mode(self):
        """Test default production mode configuration."""
        configure_lite_logging()

        # Check root logger is at INFO level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

        # Check that noisy loggers are suppressed
        aiohttp_access = logging.getLogger("aiohttp.access")
        assert aiohttp_access.level == logging.WARNING

        httpx_logger = logging.getLogger("httpx")
        assert httpx_logger.level == logging.WARNING

        # Check calendarbot_lite loggers are at INFO
        lite_logger = logging.getLogger("calendarbot_lite")
        assert lite_logger.level == logging.INFO

    def test_configure_lite_logging_debug_mode(self):
        """Test debug mode configuration."""
        configure_lite_logging(debug_mode=True)

        # Check root logger is at DEBUG level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

        # Check calendarbot_lite loggers are at DEBUG
        lite_logger = logging.getLogger("calendarbot_lite")
        assert lite_logger.level == logging.DEBUG

        # Third-party loggers should still be suppressed
        aiohttp_access = logging.getLogger("aiohttp.access")
        assert aiohttp_access.level == logging.WARNING

    def test_configure_lite_logging_force_debug_override(self):
        """Test force_debug parameter overrides debug_mode."""
        configure_lite_logging(debug_mode=False, force_debug=True)

        # Should be in debug mode despite debug_mode=False
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

        lite_logger = logging.getLogger("calendarbot_lite")
        assert lite_logger.level == logging.DEBUG

    @patch.dict(os.environ, {"CALENDARBOT_DEBUG": "1"})
    def test_configure_lite_logging_env_debug_override(self):
        """Test CALENDARBOT_DEBUG environment variable enables debug."""
        configure_lite_logging(debug_mode=False)

        # Should be in debug mode due to environment variable
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    @patch.dict(os.environ, {"CALENDARBOT_LOG_LEVEL": "WARNING"})
    def test_configure_lite_logging_env_log_level_override(self):
        """Test CALENDARBOT_LOG_LEVEL environment variable sets root level."""
        configure_lite_logging()

        # Root should be at WARNING level due to environment variable
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_configure_lite_logging_suppresses_noisy_libraries(self):
        """Test that noisy third-party libraries are properly suppressed."""
        configure_lite_logging()

        # Test key noisy loggers are suppressed
        noisy_loggers = [
            "aiohttp.access",
            "aiohttp.server",
            "httpx",
            "asyncio",
            "urllib3.connectionpool",
            "charset_normalizer",
        ]

        for logger_name in noisy_loggers:
            logger = logging.getLogger(logger_name)
            assert logger.level >= logging.WARNING, f"{logger_name} should be suppressed"


class TestResetLoggingToDebug:
    """Tests for reset_logging_to_debug function."""

    def test_reset_logging_to_debug_enables_all_loggers(self):
        """Test reset_logging_to_debug enables debug for all loggers."""
        # First configure with suppressed logging
        configure_lite_logging(debug_mode=False)

        # Verify some loggers are suppressed
        aiohttp_logger = logging.getLogger("aiohttp.access")
        assert aiohttp_logger.level == logging.WARNING

        # Reset to debug
        reset_logging_to_debug()

        # All loggers should now be at DEBUG
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

        aiohttp_logger = logging.getLogger("aiohttp.access")
        assert aiohttp_logger.level == logging.DEBUG


class TestGetLoggingStatus:
    """Tests for get_logging_status function."""

    def test_get_logging_status_returns_current_levels(self):
        """Test get_logging_status returns current logger levels."""
        configure_lite_logging(debug_mode=False)

        status = get_logging_status()

        assert isinstance(status, dict)
        assert "root" in status
        assert "calendarbot_lite" in status
        assert "aiohttp.access" in status

        # Check values are string level names
        assert status["root"] == "INFO"
        assert status["aiohttp.access"] == "WARNING"

    def test_get_logging_status_debug_mode(self):
        """Test get_logging_status in debug mode."""
        configure_lite_logging(debug_mode=True)

        status = get_logging_status()

        assert status["root"] == "DEBUG"
        assert status["calendarbot_lite"] == "DEBUG"
        # Third-party loggers should still be suppressed
        assert status["aiohttp.access"] == "WARNING"


class TestEnvironmentVariableHandling:
    """Tests for environment variable handling."""

    @patch.dict(os.environ, {"CALENDARBOT_DEBUG": "true"})
    def test_env_debug_true_string(self):
        """Test CALENDARBOT_DEBUG='true' enables debug."""
        configure_lite_logging()
        assert logging.getLogger().level == logging.DEBUG

    @patch.dict(os.environ, {"CALENDARBOT_DEBUG": "yes"})
    def test_env_debug_yes_string(self):
        """Test CALENDARBOT_DEBUG='yes' enables debug."""
        configure_lite_logging()
        assert logging.getLogger().level == logging.DEBUG

    @patch.dict(os.environ, {"CALENDARBOT_DEBUG": "false"})
    def test_env_debug_false_string_ignored(self):
        """Test CALENDARBOT_DEBUG='false' does not enable debug."""
        configure_lite_logging()
        assert logging.getLogger().level == logging.INFO

    @patch.dict(os.environ, {"CALENDARBOT_LOG_LEVEL": "ERROR"})
    def test_env_log_level_error(self):
        """Test CALENDARBOT_LOG_LEVEL='ERROR' sets root to ERROR."""
        configure_lite_logging()
        assert logging.getLogger().level == logging.ERROR

    @patch.dict(os.environ, {"CALENDARBOT_LOG_LEVEL": "INVALID"})
    def test_env_log_level_invalid_ignored(self):
        """Test invalid CALENDARBOT_LOG_LEVEL is ignored."""
        configure_lite_logging()
        # Should fallback to default INFO level
        assert logging.getLogger().level == logging.INFO
