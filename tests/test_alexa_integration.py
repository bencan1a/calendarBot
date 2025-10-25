"""Tests for Alexa integration in calendarbot_lite."""

import datetime
from unittest.mock import Mock

import pytest

from calendarbot_lite.server import (
    _check_bearer_token,
    _format_duration_spoken,
    _serialize_iso,
)


class TestBearerTokenAuth:
    """Test bearer token authentication."""

    def test_check_bearer_token_with_valid_token(self):
        """Test valid bearer token authentication."""
        request = Mock()
        request.headers = {"Authorization": "Bearer test-token-123"}

        result = _check_bearer_token(request, "test-token-123")
        assert result is True

    def test_check_bearer_token_with_invalid_token(self):
        """Test invalid bearer token authentication."""
        request = Mock()
        request.headers = {"Authorization": "Bearer wrong-token"}

        result = _check_bearer_token(request, "test-token-123")
        assert result is False

    def test_check_bearer_token_with_missing_header(self):
        """Test missing authorization header."""
        request = Mock()
        request.headers = {}

        result = _check_bearer_token(request, "test-token-123")
        assert result is False

    def test_check_bearer_token_with_malformed_header(self):
        """Test malformed authorization header."""
        request = Mock()
        request.headers = {"Authorization": "Basic dGVzdA=="}

        result = _check_bearer_token(request, "test-token-123")
        assert result is False

    def test_check_bearer_token_with_no_required_token(self):
        """Test when no token is required (auth disabled)."""
        request = Mock()
        request.headers = {}

        result = _check_bearer_token(request, None)
        assert result is True


class TestDurationFormatting:
    """Test duration formatting for speech."""

    def test_format_duration_spoken_seconds(self):
        """Test formatting seconds."""
        assert _format_duration_spoken(30) == "in 30 seconds"
        assert _format_duration_spoken(1) == "in 1 seconds"

    def test_format_duration_spoken_minutes(self):
        """Test formatting minutes."""
        assert _format_duration_spoken(60) == "in 1 minute"
        assert _format_duration_spoken(120) == "in 2 minutes"
        assert _format_duration_spoken(90) == "in 1 minute"

    def test_format_duration_spoken_hours(self):
        """Test formatting hours."""
        assert _format_duration_spoken(3600) == "in 1 hour"
        assert _format_duration_spoken(7200) == "in 2 hours"
        assert _format_duration_spoken(3660) == "in 1 hour and 1 minute"
        assert _format_duration_spoken(3720) == "in 1 hour and 2 minutes"
        assert _format_duration_spoken(7260) == "in 2 hours and 1 minute"
        assert _format_duration_spoken(7320) == "in 2 hours and 2 minutes"

    def test_format_duration_spoken_past(self):
        """Test formatting negative durations."""
        assert _format_duration_spoken(-30) == "in the past"


class TestAlexaEndpointsIntegration:
    """Test Alexa-specific API endpoints integration."""

    @pytest.mark.asyncio
    async def test_bearer_token_environment_variable_loading(self):
        """Test that bearer token can be loaded from environment."""
        import os

        from calendarbot_lite.server import _build_default_config_from_env

        # Mock environment variable
        original_value = os.environ.get("CALENDARBOT_ALEXA_BEARER_TOKEN")
        os.environ["CALENDARBOT_ALEXA_BEARER_TOKEN"] = "test-env-token"

        try:
            # Note: Current implementation doesn't read CALENDARBOT_ALEXA_BEARER_TOKEN
            # This test documents expected behavior for future enhancement
            config = _build_default_config_from_env()
            # For now, this will be empty since not implemented
            assert "alexa_bearer_token" not in config
        finally:
            if original_value is not None:
                os.environ["CALENDARBOT_ALEXA_BEARER_TOKEN"] = original_value
            else:
                os.environ.pop("CALENDARBOT_ALEXA_BEARER_TOKEN", None)

    def test_auth_flow_documentation(self):
        """Document the authentication flow for Alexa integration."""
        # This test serves as documentation of the auth flow

        # 1. User configures alexa_bearer_token in config
        # 2. CalendarBot lite server starts with this token
        # 3. Alexa skill backend makes requests with Authorization: Bearer <token>
        # 4. Server validates token before serving calendar data

        assert True  # Documentation test


class TestConfigurationIntegration:
    """Test configuration integration for Alexa features."""

    def test_config_from_dict_with_alexa_token(self):
        """Test config loading with Alexa bearer token."""
        from calendarbot_lite.config_loader import Config

        data = {
            "sources": ["https://example.com/calendar.ics"],
            "alexa_bearer_token": "my-secret-token",
        }

        config = Config.from_dict(data)
        assert config.alexa_bearer_token == "my-secret-token"

    def test_config_from_dict_without_alexa_token(self):
        """Test config loading without Alexa bearer token."""
        from calendarbot_lite.config_loader import Config

        data = {"sources": ["https://example.com/calendar.ics"]}

        config = Config.from_dict(data)
        assert config.alexa_bearer_token is None

    def test_config_from_dict_with_empty_alexa_token(self):
        """Test config loading with empty Alexa bearer token."""
        from calendarbot_lite.config_loader import Config

        data = {"sources": ["https://example.com/calendar.ics"], "alexa_bearer_token": ""}

        config = Config.from_dict(data)
        assert config.alexa_bearer_token == ""


class TestSerializationHelpers:
    """Test serialization helper functions."""

    def test_serialize_iso_with_timezone(self):
        """Test ISO serialization with timezone."""
        dt = datetime.datetime(2023, 10, 25, 14, 30, 0, tzinfo=datetime.timezone.utc)
        result = _serialize_iso(dt)
        assert result == "2023-10-25T14:30:00Z"

    def test_serialize_iso_without_timezone(self):
        """Test ISO serialization without timezone (assumes UTC)."""
        dt = datetime.datetime(2023, 10, 25, 14, 30, 0)
        result = _serialize_iso(dt)
        assert result == "2023-10-25T14:30:00Z"

    def test_serialize_iso_with_none(self):
        """Test ISO serialization with None."""
        result = _serialize_iso(None)
        assert result is None
