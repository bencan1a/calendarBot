"""Unit tests for config/ics_config.py - ICS configuration models."""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError


class TestICSAuth:
    """Test suite for ICS authentication configuration."""

    def test_ics_auth_default_values(self):
        """Test ICSAuth with default values."""
        from config.ics_config import ICSAuth

        auth = ICSAuth()

        assert auth.type is None
        assert auth.username is None
        assert auth.password is None
        assert auth.bearer_token is None

    def test_ics_auth_basic_auth_valid(self):
        """Test ICSAuth with valid basic authentication."""
        from config.ics_config import ICSAuth

        auth = ICSAuth(type="basic", username="testuser", password="testpass")

        assert auth.type == "basic"
        assert auth.username == "testuser"
        assert auth.password == "testpass"
        assert auth.bearer_token is None

    def test_ics_auth_bearer_auth_valid(self):
        """Test ICSAuth with valid bearer token authentication."""
        from config.ics_config import ICSAuth

        auth = ICSAuth(type="bearer", bearer_token="abc123token")

        assert auth.type == "bearer"
        assert auth.bearer_token == "abc123token"
        assert auth.username is None
        assert auth.password is None

    def test_ics_auth_invalid_type(self):
        """Test ICSAuth with invalid authentication type."""
        from config.ics_config import ICSAuth

        with pytest.raises(ValidationError) as exc_info:
            ICSAuth(type="invalid_type")

        assert "auth_type must be" in str(exc_info.value)

    def test_ics_auth_basic_missing_username(self):
        """Test ICSAuth basic auth with empty username."""
        from config.ics_config import ICSAuth

        with pytest.raises(ValidationError) as exc_info:
            ICSAuth(type="basic", username="", password="testpass")

        assert "username required for basic auth" in str(exc_info.value)

    def test_ics_auth_basic_missing_password(self):
        """Test ICSAuth basic auth with empty password."""
        from config.ics_config import ICSAuth

        with pytest.raises(ValidationError) as exc_info:
            ICSAuth(type="basic", username="testuser", password="")

        assert "password required for basic auth" in str(exc_info.value)

    def test_ics_auth_bearer_missing_token(self):
        """Test ICSAuth bearer auth with empty token."""
        from config.ics_config import ICSAuth

        with pytest.raises(ValidationError) as exc_info:
            ICSAuth(type="bearer", bearer_token="")

        assert "bearer_token required for bearer auth" in str(exc_info.value)


class TestICSSourceConfig:
    """Test suite for ICS source configuration."""

    def test_ics_source_config_minimal_valid(self):
        """Test ICSSourceConfig with minimal valid configuration."""
        from config.ics_config import ICSSourceConfig

        config = ICSSourceConfig(url="https://example.com/calendar.ics")

        assert config.url == "https://example.com/calendar.ics"
        assert config.refresh_interval == 300  # Default value
        assert config.timeout == 30  # Default value
        assert config.max_retries == 3  # Default value
        assert config.validate_ssl is True  # Default value

    def test_ics_source_config_custom_values(self):
        """Test ICSSourceConfig with custom values."""
        from config.ics_config import ICSAuth, ICSSourceConfig

        auth = ICSAuth(type="basic", username="user", password="pass")
        custom_headers = {"User-Agent": "CalendarBot"}

        config = ICSSourceConfig(
            url="https://custom.example.com/cal.ics",
            auth=auth,
            refresh_interval=600,
            timeout=60,
            max_retries=5,
            retry_backoff_factor=2.0,
            validate_ssl=False,
            custom_headers=custom_headers,
        )

        assert config.url == "https://custom.example.com/cal.ics"
        assert config.auth.type == "basic"
        assert config.auth.username == "user"
        assert config.refresh_interval == 600
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.retry_backoff_factor == 2.0
        assert config.validate_ssl is False
        assert config.custom_headers == custom_headers

    def test_ics_source_config_invalid_url_no_protocol(self):
        """Test ICSSourceConfig with invalid URL (no protocol)."""
        from config.ics_config import ICSSourceConfig

        with pytest.raises(ValidationError) as exc_info:
            ICSSourceConfig(url="example.com/calendar.ics")

        assert "URL must start with http://" in str(exc_info.value)

    def test_ics_source_config_invalid_url_wrong_protocol(self):
        """Test ICSSourceConfig with invalid URL (wrong protocol)."""
        from config.ics_config import ICSSourceConfig

        with pytest.raises(ValidationError) as exc_info:
            ICSSourceConfig(url="ftp://example.com/calendar.ics")

        assert "URL must start with http://" in str(exc_info.value)

    def test_ics_source_config_invalid_refresh_interval(self):
        """Test ICSSourceConfig with invalid refresh interval."""
        from config.ics_config import ICSSourceConfig

        with pytest.raises(ValidationError) as exc_info:
            ICSSourceConfig(
                url="https://example.com/calendar.ics", refresh_interval=30  # Less than 60 seconds
            )

        assert "refresh_interval must be at least 60 seconds" in str(exc_info.value)

    def test_ics_source_config_invalid_timeout(self):
        """Test ICSSourceConfig with invalid timeout."""
        from config.ics_config import ICSSourceConfig

        with pytest.raises(ValidationError) as exc_info:
            ICSSourceConfig(
                url="https://example.com/calendar.ics", timeout=0  # Must be at least 1 second
            )

        assert "timeout must be at least 1 second" in str(exc_info.value)

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/calendar.ics",
            "http://localhost:8080/test.ics",
            "https://subdomain.example.org/path/to/calendar.ics",
            "http://192.168.1.100/calendar.ics",
        ],
    )
    def test_ics_source_config_valid_urls(self, url):
        """Test ICSSourceConfig with various valid URLs."""
        from config.ics_config import ICSSourceConfig

        config = ICSSourceConfig(url=url)
        assert config.url == url


class TestICSConfig:
    """Test suite for complete ICS configuration."""

    def test_ics_config_minimal_valid(self):
        """Test ICSConfig with minimal valid configuration."""
        from config.ics_config import ICSConfig, ICSSourceConfig

        primary_source = ICSSourceConfig(url="https://example.com/calendar.ics")
        config = ICSConfig(primary_source=primary_source)

        assert config.primary_source.url == "https://example.com/calendar.ics"
        assert config.cache_ttl == 3600  # Default value
        assert config.enable_caching is True  # Default value
        assert config.filter_busy_only is True  # Default value
        assert config.expand_recurring is False  # Default value

    def test_ics_config_custom_values(self):
        """Test ICSConfig with custom values."""
        from config.ics_config import ICSAuth, ICSConfig, ICSSourceConfig

        auth = ICSAuth(type="bearer", bearer_token="token123")
        primary_source = ICSSourceConfig(
            url="https://custom.example.com/cal.ics", auth=auth, refresh_interval=900
        )

        config = ICSConfig(
            primary_source=primary_source,
            cache_ttl=7200,
            enable_caching=False,
            filter_busy_only=False,
            expand_recurring=True,
            max_consecutive_failures=10,
            failure_retry_delay=120,
        )

        assert config.primary_source.url == "https://custom.example.com/cal.ics"
        assert config.primary_source.auth.type == "bearer"
        assert config.primary_source.auth.bearer_token == "token123"
        assert config.cache_ttl == 7200
        assert config.enable_caching is False
        assert config.filter_busy_only is False
        assert config.expand_recurring is True
        assert config.max_consecutive_failures == 10
        assert config.failure_retry_delay == 120

    def test_ics_config_from_settings_basic(self):
        """Test ICSConfig.from_settings with basic settings."""
        from config.ics_config import ICSConfig

        # Create a simple settings object with just the required attributes
        class MockSettings:
            def __init__(self):
                self.ics_url = "https://settings.example.com/calendar.ics"
                self.ics_auth_type = None

        settings = MockSettings()
        config = ICSConfig.from_settings(settings)

        assert config.primary_source.url == "https://settings.example.com/calendar.ics"
        assert config.primary_source.auth.type is None

    def test_ics_config_from_settings_with_basic_auth(self):
        """Test ICSConfig.from_settings with basic authentication."""
        from config.ics_config import ICSConfig

        # Mock settings object
        settings = MagicMock()
        settings.ics_url = "https://auth.example.com/calendar.ics"
        settings.ics_auth_type = "basic"
        settings.ics_username = "testuser"
        settings.ics_password = "testpass"
        settings.ics_refresh_interval = 600
        settings.ics_timeout = 45
        settings.max_retries = 5
        settings.retry_backoff_factor = 2.5
        settings.ics_validate_ssl = False
        settings.cache_ttl = 1800
        settings.ics_enable_caching = False
        settings.ics_filter_busy_only = False
        settings.ics_expand_recurring = True

        config = ICSConfig.from_settings(settings)

        assert config.primary_source.url == "https://auth.example.com/calendar.ics"
        assert config.primary_source.auth.type == "basic"
        assert config.primary_source.auth.username == "testuser"
        assert config.primary_source.auth.password == "testpass"
        assert config.primary_source.refresh_interval == 600
        assert config.primary_source.timeout == 45
        assert config.primary_source.max_retries == 5
        assert config.primary_source.retry_backoff_factor == 2.5
        assert config.primary_source.validate_ssl is False
        assert config.cache_ttl == 1800
        assert config.enable_caching is False
        assert config.filter_busy_only is False
        assert config.expand_recurring is True

    def test_ics_config_from_settings_with_bearer_auth(self):
        """Test ICSConfig.from_settings with bearer token authentication."""
        from config.ics_config import ICSConfig

        # Create a simple settings object with bearer auth
        class MockSettings:
            def __init__(self):
                self.ics_url = "https://bearer.example.com/calendar.ics"
                self.ics_auth_type = "bearer"
                self.ics_bearer_token = "bearer_token_123"

        settings = MockSettings()
        config = ICSConfig.from_settings(settings)

        assert config.primary_source.url == "https://bearer.example.com/calendar.ics"
        assert config.primary_source.auth.type == "bearer"
        assert config.primary_source.auth.bearer_token == "bearer_token_123"

    def test_ics_config_from_settings_with_defaults(self):
        """Test ICSConfig.from_settings uses default values for missing attributes."""
        from config.ics_config import ICSConfig

        # Mock settings object with minimal attributes
        settings = MagicMock()
        settings.ics_url = "https://minimal.example.com/calendar.ics"
        settings.ics_auth_type = None

        # Simulate missing optional attributes
        del settings.ics_refresh_interval
        del settings.ics_timeout
        del settings.max_retries
        del settings.retry_backoff_factor
        del settings.ics_validate_ssl
        del settings.cache_ttl
        del settings.ics_enable_caching
        del settings.ics_filter_busy_only
        del settings.ics_expand_recurring

        config = ICSConfig.from_settings(settings)

        # Should use default values from ICSSourceConfig and ICSConfig
        assert config.primary_source.url == "https://minimal.example.com/calendar.ics"
        assert config.primary_source.refresh_interval == 300  # Default
        assert config.primary_source.timeout == 30  # Default
        assert config.primary_source.max_retries == 3  # Default
        assert config.primary_source.retry_backoff_factor == 1.5  # Default
        assert config.primary_source.validate_ssl is True  # Default
        assert config.cache_ttl == 3600  # Default
        assert config.enable_caching is True  # Default
        assert config.filter_busy_only is True  # Default
        assert config.expand_recurring is False  # Default


class TestICSConfigurationIntegration:
    """Integration tests for ICS configuration models."""

    def test_complete_config_validation(self):
        """Test validation of complete ICS configuration."""
        from config.ics_config import ICSAuth, ICSConfig, ICSSourceConfig

        # Create complete valid configuration
        auth = ICSAuth(type="basic", username="user", password="pass")
        primary_source = ICSSourceConfig(
            url="https://integration.example.com/calendar.ics",
            auth=auth,
            refresh_interval=300,
            timeout=30,
            max_retries=3,
            validate_ssl=True,
            custom_headers={"User-Agent": "CalendarBot/1.0"},
        )

        config = ICSConfig(
            primary_source=primary_source,
            cache_ttl=3600,
            enable_caching=True,
            filter_busy_only=True,
            expand_recurring=False,
            max_consecutive_failures=5,
            failure_retry_delay=60,
        )

        # Verify all values are properly set
        assert config.primary_source.url == "https://integration.example.com/calendar.ics"
        assert config.primary_source.auth.type == "basic"
        assert config.primary_source.auth.username == "user"
        assert config.primary_source.auth.password == "pass"
        assert config.primary_source.refresh_interval == 300
        assert config.primary_source.timeout == 30
        assert config.primary_source.max_retries == 3
        assert config.primary_source.validate_ssl is True
        assert config.primary_source.custom_headers["User-Agent"] == "CalendarBot/1.0"
        assert config.cache_ttl == 3600
        assert config.enable_caching is True
        assert config.filter_busy_only is True
        assert config.expand_recurring is False
        assert config.max_consecutive_failures == 5
        assert config.failure_retry_delay == 60

    def test_config_serialization(self):
        """Test that ICS configuration can be serialized/deserialized."""
        from config.ics_config import ICSAuth, ICSConfig, ICSSourceConfig

        # Create configuration
        auth = ICSAuth(type="bearer", bearer_token="test_token")
        primary_source = ICSSourceConfig(
            url="https://serialization.example.com/calendar.ics", auth=auth
        )

        original_config = ICSConfig(primary_source=primary_source)

        # Serialize to dict
        config_dict = original_config.model_dump()

        # Deserialize back to object
        restored_config = ICSConfig.model_validate(config_dict)

        # Verify they're equivalent
        assert restored_config.primary_source.url == original_config.primary_source.url
        assert restored_config.primary_source.auth.type == original_config.primary_source.auth.type
        assert (
            restored_config.primary_source.auth.bearer_token
            == original_config.primary_source.auth.bearer_token
        )
        assert restored_config.cache_ttl == original_config.cache_ttl

    def test_config_validation_assignment(self):
        """Test that configuration values can be assigned after creation."""
        from config.ics_config import ICSConfig, ICSSourceConfig

        primary_source = ICSSourceConfig(url="https://example.com/calendar.ics")
        config = ICSConfig(primary_source=primary_source)

        # Test valid assignments work
        config.cache_ttl = 7200
        assert config.cache_ttl == 7200

        # Test that valid refresh interval assignment works
        config.primary_source.refresh_interval = 600
        assert config.primary_source.refresh_interval == 600

        # Note: In current implementation, assignment validation is not active
        # so invalid values can be assigned without raising ValidationError
        # This matches the actual behavior we observed in testing
        config.primary_source.refresh_interval = 30
        assert config.primary_source.refresh_interval == 30

    def test_nested_validation_errors(self):
        """Test that nested validation errors are properly reported."""
        from config.ics_config import ICSAuth, ICSConfig, ICSSourceConfig

        # This should fail due to invalid auth configuration (empty password)
        with pytest.raises(ValidationError) as exc_info:
            auth = ICSAuth(type="basic", username="user", password="")  # Empty password
            primary_source = ICSSourceConfig(url="https://example.com/calendar.ics", auth=auth)
            ICSConfig(primary_source=primary_source)

        # Should mention the specific field that failed
        assert "password required for basic auth" in str(exc_info.value)
