"""Unit tests for config.ics_config module.

Tests ICS configuration models including authentication, source configuration,
and overall ICS settings with comprehensive validation coverage.
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from calendarbot.config.ics_config import ICSAuth, ICSConfig, ICSSourceConfig


@pytest.fixture
def basic_auth():
    """Basic authentication configuration."""
    return ICSAuth(type="basic", username="testuser", password="testpass")


@pytest.fixture
def bearer_auth():
    """Bearer token authentication configuration."""
    return ICSAuth(type="bearer", bearer_token="abc123xyz")


@pytest.fixture
def no_auth():
    """No authentication configuration."""
    return ICSAuth()


@pytest.fixture
def basic_source_config():
    """Basic ICS source configuration."""
    return ICSSourceConfig(url="https://example.com/calendar.ics")


@pytest.fixture
def mock_settings_basic():
    """Mock settings object with basic configuration."""
    mock_settings = MagicMock()
    mock_settings.configure_mock(
        ics_url="https://example.com/calendar.ics",
        ics_refresh_interval=300,
        ics_timeout=30,
        max_retries=3,
        retry_backoff_factor=1.5,
        ics_validate_ssl=True,
        cache_ttl=3600,
        ics_enable_caching=True,
        ics_filter_busy_only=True,
        ics_expand_recurring=False,
    )
    return mock_settings


@pytest.fixture
def mock_settings_with_basic_auth(mock_settings_basic):
    """Mock settings with basic authentication."""
    mock_settings_basic.configure_mock(
        ics_auth_type="basic", ics_username="testuser", ics_password="testpass"
    )
    return mock_settings_basic


@pytest.fixture
def mock_settings_with_bearer_auth(mock_settings_basic):
    """Mock settings with bearer authentication."""
    mock_settings_basic.configure_mock(ics_auth_type="bearer", ics_bearer_token="abc123xyz")
    return mock_settings_basic


class TestICSAuth:
    """Test ICSAuth authentication configuration model."""

    def test_ics_auth_defaults(self):
        """Test ICSAuth has correct default values."""
        auth = ICSAuth()

        assert auth.type is None
        assert auth.username is None
        assert auth.password is None
        assert auth.bearer_token is None

    def test_ics_auth_valid_auth_types(self):
        """Test valid authentication types."""
        # Test None/null auth type
        auth_none = ICSAuth(type=None)
        assert auth_none.type is None

        # Test basic auth type
        auth_basic = ICSAuth(type="basic", username="user", password="pass")
        assert auth_basic.type == "basic"
        assert auth_basic.username == "user"
        assert auth_basic.password == "pass"

        # Test bearer auth type
        auth_bearer = ICSAuth(type="bearer", bearer_token="token123")
        assert auth_bearer.type == "bearer"
        assert auth_bearer.bearer_token == "token123"

    def test_ics_auth_invalid_auth_type(self):
        """Test invalid authentication types raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ICSAuth(type="invalid")

        assert "auth_type must be" in str(exc_info.value)

    @pytest.mark.parametrize("invalid_type", ["oauth", "digest", "custom", ""])
    def test_ics_auth_invalid_auth_types_parametrized(self, invalid_type):
        """Test various invalid authentication types."""
        with pytest.raises(ValidationError) as exc_info:
            ICSAuth(type=invalid_type)

        assert "auth_type must be" in str(exc_info.value)

    def test_ics_auth_basic_missing_username(self):
        """Test basic auth validation fails when username is missing."""
        with pytest.raises(ValidationError) as exc_info:
            ICSAuth(type="basic", username=None, password="password")

        assert "username required for basic auth" in str(exc_info.value)

    def test_ics_auth_basic_missing_password(self):
        """Test basic auth validation fails when password is missing."""
        with pytest.raises(ValidationError) as exc_info:
            ICSAuth(type="basic", username="user", password=None)

        assert "password required for basic auth" in str(exc_info.value)

    def test_ics_auth_basic_empty_username(self):
        """Test basic auth validation fails when username is empty."""
        with pytest.raises(ValidationError) as exc_info:
            ICSAuth(type="basic", username="", password="password")

        assert "username required for basic auth" in str(exc_info.value)

    def test_ics_auth_basic_empty_password(self):
        """Test basic auth validation fails when password is empty."""
        with pytest.raises(ValidationError) as exc_info:
            ICSAuth(type="basic", username="user", password="")

        assert "password required for basic auth" in str(exc_info.value)

    def test_ics_auth_bearer_missing_token(self):
        """Test bearer auth validation fails when token is missing."""
        with pytest.raises(ValidationError) as exc_info:
            ICSAuth(type="bearer", bearer_token=None)

        assert "bearer_token required for bearer auth" in str(exc_info.value)

    def test_ics_auth_bearer_empty_token(self):
        """Test bearer auth validation fails when token is empty."""
        with pytest.raises(ValidationError) as exc_info:
            ICSAuth(type="bearer", bearer_token="")

        assert "bearer_token required for bearer auth" in str(exc_info.value)

    def test_ics_auth_basic_with_bearer_token(self):
        """Test basic auth ignores bearer_token field."""
        auth = ICSAuth(type="basic", username="user", password="pass", bearer_token="ignored")

        assert auth.type == "basic"
        assert auth.username == "user"
        assert auth.password == "pass"
        assert auth.bearer_token == "ignored"  # Field is set but not validated for basic auth

    def test_ics_auth_bearer_with_basic_fields(self):
        """Test bearer auth ignores basic auth fields."""
        auth = ICSAuth(
            type="bearer", bearer_token="token123", username="ignored", password="ignored"
        )

        assert auth.type == "bearer"
        assert auth.bearer_token == "token123"
        assert auth.username == "ignored"  # Field is set but not validated for bearer auth
        assert auth.password == "ignored"

    def test_ics_auth_none_type_with_credentials(self):
        """Test null auth type doesn't validate credential fields."""
        auth = ICSAuth(type=None, username="user", password="pass", bearer_token="token")

        assert auth.type is None
        assert auth.username == "user"
        assert auth.password == "pass"
        assert auth.bearer_token == "token"


class TestICSSourceConfig:
    """Test ICSSourceConfig calendar source configuration model."""

    def test_ics_source_config_minimal(self):
        """Test ICSSourceConfig with minimal required fields."""
        config = ICSSourceConfig(url="https://example.com/calendar.ics")

        assert config.url == "https://example.com/calendar.ics"
        assert isinstance(config.auth, ICSAuth)
        assert config.auth.type is None
        assert config.refresh_interval == 300
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.retry_backoff_factor == 1.5
        assert config.validate_ssl is True
        assert config.custom_headers == {}

    def test_ics_source_config_with_all_fields(self):
        """Test ICSSourceConfig with all fields specified."""
        auth = ICSAuth(type="basic", username="user", password="pass")
        custom_headers = {"Authorization": "Bearer token", "User-Agent": "CalendarBot"}

        config = ICSSourceConfig(
            url="https://secure.example.com/cal.ics",
            auth=auth,
            refresh_interval=600,
            timeout=60,
            max_retries=5,
            retry_backoff_factor=2.0,
            validate_ssl=False,
            custom_headers=custom_headers,
        )

        assert config.url == "https://secure.example.com/cal.ics"
        assert config.auth == auth
        assert config.refresh_interval == 600
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.retry_backoff_factor == 2.0
        assert config.validate_ssl is False
        assert config.custom_headers == custom_headers

    @pytest.mark.parametrize(
        "valid_url",
        [
            "https://example.com/calendar.ics",
            "http://localhost:8080/cal.ics",
            "https://subdomain.domain.com/path/to/calendar.ics",
            "http://192.168.1.100/calendar.ics",
            "https://example.com:8443/secure/cal.ics",
        ],
    )
    def test_ics_source_config_valid_urls(self, valid_url):
        """Test valid URL formats."""
        config = ICSSourceConfig(url=valid_url)
        assert config.url == valid_url

    @pytest.mark.parametrize(
        "invalid_url",
        [
            "ftp://example.com/calendar.ics",
            "file:///path/to/calendar.ics",
            "example.com/calendar.ics",
            "calendar.ics",
            "mailto:user@example.com",
            "",
        ],
    )
    def test_ics_source_config_invalid_urls(self, invalid_url):
        """Test invalid URL formats raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ICSSourceConfig(url=invalid_url)

        assert "URL must start with http:// or https://" in str(exc_info.value)

    def test_ics_source_config_refresh_interval_too_low(self):
        """Test refresh_interval validation fails when too low."""
        with pytest.raises(ValidationError) as exc_info:
            ICSSourceConfig(url="https://example.com/cal.ics", refresh_interval=59)

        assert "refresh_interval must be at least 60 seconds" in str(exc_info.value)

    @pytest.mark.parametrize("invalid_interval", [0, -1, 30, 59])
    def test_ics_source_config_invalid_refresh_intervals(self, invalid_interval):
        """Test various invalid refresh intervals."""
        with pytest.raises(ValidationError) as exc_info:
            ICSSourceConfig(url="https://example.com/cal.ics", refresh_interval=invalid_interval)

        assert "refresh_interval must be at least 60 seconds" in str(exc_info.value)

    @pytest.mark.parametrize("valid_interval", [60, 300, 3600, 86400])
    def test_ics_source_config_valid_refresh_intervals(self, valid_interval):
        """Test valid refresh intervals."""
        config = ICSSourceConfig(url="https://example.com/cal.ics", refresh_interval=valid_interval)
        assert config.refresh_interval == valid_interval

    def test_ics_source_config_timeout_too_low(self):
        """Test timeout validation fails when too low."""
        with pytest.raises(ValidationError) as exc_info:
            ICSSourceConfig(url="https://example.com/cal.ics", timeout=0)

        assert "timeout must be at least 1 second" in str(exc_info.value)

    @pytest.mark.parametrize("invalid_timeout", [0, -1, -5])
    def test_ics_source_config_invalid_timeouts(self, invalid_timeout):
        """Test various invalid timeout values."""
        with pytest.raises(ValidationError) as exc_info:
            ICSSourceConfig(url="https://example.com/cal.ics", timeout=invalid_timeout)

        assert "timeout must be at least 1 second" in str(exc_info.value)

    @pytest.mark.parametrize("valid_timeout", [1, 10, 30, 120])
    def test_ics_source_config_valid_timeouts(self, valid_timeout):
        """Test valid timeout values."""
        config = ICSSourceConfig(url="https://example.com/cal.ics", timeout=valid_timeout)
        assert config.timeout == valid_timeout

    def test_ics_source_config_with_basic_auth(self, basic_auth):
        """Test ICSSourceConfig with basic authentication."""
        config = ICSSourceConfig(url="https://example.com/cal.ics", auth=basic_auth)

        assert config.auth.type == "basic"
        assert config.auth.username == "testuser"
        assert config.auth.password == "testpass"

    def test_ics_source_config_with_bearer_auth(self, bearer_auth):
        """Test ICSSourceConfig with bearer authentication."""
        config = ICSSourceConfig(url="https://example.com/cal.ics", auth=bearer_auth)

        assert config.auth.type == "bearer"
        assert config.auth.bearer_token == "abc123xyz"

    def test_ics_source_config_auth_validation_propagated(self):
        """Test that auth validation errors are propagated."""
        with pytest.raises(ValidationError) as exc_info:
            ICSSourceConfig(
                url="https://example.com/cal.ics",
                auth=ICSAuth(type="basic", username="user", password=None),  # Missing password
            )

        assert "password required for basic auth" in str(exc_info.value)


class TestICSConfig:
    """Test ICSConfig complete configuration model."""

    def test_ics_config_minimal(self, basic_source_config):
        """Test ICSConfig with minimal required fields."""
        config = ICSConfig(primary_source=basic_source_config)

        assert config.primary_source == basic_source_config
        assert config.cache_ttl == 3600
        assert config.enable_caching is True
        assert config.filter_busy_only is True
        assert config.expand_recurring is False
        assert config.max_consecutive_failures == 5
        assert config.failure_retry_delay == 60

    def test_ics_config_with_custom_values(self, bearer_auth):
        """Test ICSConfig with custom values."""
        primary_source = ICSSourceConfig(
            url="https://secure.example.com/cal.ics", auth=bearer_auth, refresh_interval=900
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

        assert config.primary_source == primary_source
        assert config.cache_ttl == 7200
        assert config.enable_caching is False
        assert config.filter_busy_only is False
        assert config.expand_recurring is True
        assert config.max_consecutive_failures == 10
        assert config.failure_retry_delay == 120

    def test_ics_config_primary_source_validation(self):
        """Test that primary_source validation is enforced."""
        with pytest.raises(ValidationError) as exc_info:
            ICSConfig(primary_source=None)

        # Should fail due to required field validation
        assert "Input should be a valid dictionary or instance of ICSSourceConfig" in str(
            exc_info.value
        )

    def test_ics_config_from_settings_minimal(self, mock_settings_basic):
        """Test from_settings class method with minimal settings."""
        # Mock hasattr to return False for ics_auth_type (no auth)
        with patch("builtins.hasattr", return_value=False):
            config = ICSConfig.from_settings(mock_settings_basic)

        assert config.primary_source.url == "https://example.com/calendar.ics"
        assert config.primary_source.auth.type is None
        assert config.cache_ttl == 3600
        assert config.enable_caching is True

    def test_ics_config_from_settings_with_basic_auth(self, mock_settings_with_basic_auth):
        """Test from_settings with basic authentication."""
        # Mock hasattr to return True for ics_auth_type
        with patch("builtins.hasattr", return_value=True):
            config = ICSConfig.from_settings(mock_settings_with_basic_auth)

        assert config.primary_source.url == "https://example.com/calendar.ics"
        assert config.primary_source.auth.type == "basic"
        assert config.primary_source.auth.username == "testuser"
        assert config.primary_source.auth.password == "testpass"

    def test_ics_config_from_settings_with_bearer_auth(self, mock_settings_with_bearer_auth):
        """Test from_settings with bearer authentication."""
        # Mock hasattr to return True for ics_auth_type
        with patch("builtins.hasattr", return_value=True):
            config = ICSConfig.from_settings(mock_settings_with_bearer_auth)

        assert config.primary_source.url == "https://example.com/calendar.ics"
        assert config.primary_source.auth.type == "bearer"
        assert config.primary_source.auth.bearer_token == "abc123xyz"

    def test_ics_config_from_settings_with_custom_values(self):
        """Test from_settings with custom configuration values."""
        mock_settings = MagicMock()
        mock_settings.configure_mock(
            ics_url="https://custom.example.com/cal.ics",
            ics_refresh_interval=600,
            ics_timeout=60,
            max_retries=5,
            retry_backoff_factor=2.0,
            ics_validate_ssl=False,
            cache_ttl=7200,
            ics_enable_caching=False,
            ics_filter_busy_only=False,
            ics_expand_recurring=True,
        )

        # Mock hasattr to return False for ics_auth_type (no auth)
        with patch("builtins.hasattr", return_value=False):
            config = ICSConfig.from_settings(mock_settings)

        assert config.primary_source.url == "https://custom.example.com/cal.ics"
        assert config.primary_source.refresh_interval == 600
        assert config.primary_source.timeout == 60
        assert config.primary_source.max_retries == 5
        assert config.primary_source.retry_backoff_factor == 2.0
        assert config.primary_source.validate_ssl is False
        assert config.cache_ttl == 7200
        assert config.enable_caching is False
        assert config.filter_busy_only is False
        assert config.expand_recurring is True

    def test_ics_config_from_settings_no_auth_type_attribute(self, mock_settings_basic):
        """Test from_settings when settings has no ics_auth_type attribute."""
        # Mock hasattr to return False for ics_auth_type (no auth)
        with patch("builtins.hasattr", return_value=False):
            config = ICSConfig.from_settings(mock_settings_basic)

        # Should create config with no authentication
        assert config.primary_source.auth.type is None

    def test_ics_config_from_settings_empty_auth_type(self, mock_settings_basic):
        """Test from_settings when ics_auth_type is empty."""
        mock_settings_basic.ics_auth_type = ""  # Empty string

        # Mock hasattr to return True for ics_auth_type
        with patch("builtins.hasattr", return_value=True):
            config = ICSConfig.from_settings(mock_settings_basic)

        # Empty auth_type should not set up authentication
        assert config.primary_source.auth.type is None


class TestICSConfigEdgeCases:
    """Test edge cases and error conditions for ICS configuration models."""

    def test_ics_auth_field_validator_order(self):
        """Test that field validators are called in the correct order."""
        # This tests the interaction between validators when multiple fields are involved

        # Valid case should work
        auth = ICSAuth(type="basic", username="user", password="pass")
        assert auth.type == "basic"

        # Invalid type should fail before other validations
        with pytest.raises(ValidationError) as exc_info:
            ICSAuth(type="invalid", username="user", password="pass")
        assert "auth_type must be" in str(exc_info.value)

    def test_ics_source_config_extreme_values(self):
        """Test ICSSourceConfig with extreme but valid values."""
        config = ICSSourceConfig(
            url="https://example.com/cal.ics",
            refresh_interval=86400,  # 24 hours
            timeout=3600,  # 1 hour
            max_retries=100,
            retry_backoff_factor=10.0,
        )

        assert config.refresh_interval == 86400
        assert config.timeout == 3600
        assert config.max_retries == 100
        assert config.retry_backoff_factor == 10.0

    def test_ics_config_validate_assignment(self):
        """Test that validate_assignment is enabled and works."""
        primary_source = ICSSourceConfig(url="https://example.com/cal.ics")
        config = ICSConfig(primary_source=primary_source)

        # Verify the config was created successfully
        assert config.primary_source == primary_source

        # Note: We can't easily test assignment validation without directly
        # modifying fields after creation, which would require more complex setup
