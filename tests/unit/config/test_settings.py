"""Unit tests for the settings configuration module."""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from calendarbot.config.settings import (
    CalendarBotSettings,
    EpaperConfiguration,
    LoggingSettings,
    RuntimeTrackingSettings,
    _get_safe_web_host,
    _mask_credentials_fallback,
    _SettingsProxy,
    get_settings,
    reset_settings,
)


@pytest.fixture
def mock_yaml_config():
    """Mock YAML configuration data."""
    return {
        "ics": {
            "url": "https://example.com/calendar.ics",
            "auth_type": "basic",
            "username": "test_user",
            "password": "test_pass",
        },
        "logging": {
            "console_level": "DEBUG",
            "file_enabled": True,
        },
        "web": {
            "enabled": True,
            "port": 8080,
            "layout": "whats-next-view",
        },
        "epaper": {
            "enabled": True,
            "width": 400,
            "height": 300,
        },
    }


@pytest.fixture
def clean_settings():
    """Clean up global settings state before and after tests."""
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def mock_file_operations():
    """Mock file system operations for settings."""
    with (
        patch("pathlib.Path.exists", return_value=False),
        patch("pathlib.Path.open", mock_open()),
        patch("calendarbot.config.settings.yaml.safe_load", return_value={}),
        patch(
            "calendarbot.config.settings.CalendarBotSettings._find_config_file", return_value=None
        ),
        patch("calendarbot.config.settings.CalendarBotSettings._load_yaml_config"),
        patch.dict("os.environ", {}, clear=True),
    ):
        yield


class TestLoggingSettings:
    """Tests for the LoggingSettings class."""

    def test_logging_settings_defaults(self) -> None:
        """Test LoggingSettings initialization with defaults."""
        settings = LoggingSettings()

        # Console logging
        assert settings.console_enabled is True
        assert settings.console_level == "INFO"
        assert settings.console_colors is True

        # File logging
        assert settings.file_enabled is True
        assert settings.file_level == "DEBUG"
        assert settings.file_directory is None
        assert settings.file_prefix == "calendarbot"
        assert settings.max_log_files == 5

        # Security logging
        assert settings.security_enabled is True
        assert settings.security_mask_credentials is True

        # Performance monitoring
        assert settings.performance_enabled is True
        assert settings.performance_timing_threshold == 1.0

    def test_logging_settings_custom_values(self) -> None:
        """Test LoggingSettings with custom values."""
        settings = LoggingSettings(
            console_level="ERROR",
            file_enabled=False,
            security_enabled=False,
            performance_timing_threshold=2.0,
        )

        assert settings.console_level == "ERROR"
        assert settings.file_enabled is False
        assert settings.security_enabled is False
        assert settings.performance_timing_threshold == 2.0


class TestRuntimeTrackingSettings:
    """Tests for the RuntimeTrackingSettings class."""

    def test_runtime_tracking_defaults(self) -> None:
        """Test RuntimeTrackingSettings initialization with defaults."""
        settings = RuntimeTrackingSettings()

        assert settings.enabled is False
        assert settings.sampling_interval == 1.0
        assert settings.save_samples is True
        assert settings.session_name is None
        assert settings.memory_threshold_mb == 100
        assert settings.cpu_threshold_percent == 80.0
        assert settings.max_samples == 10000


class TestEpaperConfiguration:
    """Tests for the EpaperConfiguration class."""

    def test_epaper_configuration_defaults(self) -> None:
        """Test EpaperConfiguration initialization with defaults."""
        config = EpaperConfiguration()

        assert config.enabled is True
        assert config.force_epaper is False
        assert config.display_model is None
        assert config.webserver_enabled is True
        assert config.webserver_port == 8081
        assert config.width == 300
        assert config.height == 400
        assert config.rotation == 0
        assert config.partial_refresh is True
        assert config.refresh_interval == 300
        assert config.contrast_level == 100
        assert config.dither_mode == "floyd_steinberg"
        assert config.error_fallback is True
        assert config.png_fallback_enabled is True


class TestCalendarBotSettings:
    """Tests for the CalendarBotSettings class."""

    @patch.dict(
        "os.environ",
        {
            "CALENDARBOT_ICS_URL": "https://test.com/cal.ics",
            "CALENDARBOT_WEB_ENABLED": "true",
            "CALENDARBOT_WEB_PORT": "9000",
            "CALENDARBOT_CACHE_TTL": "1200",
        },
        clear=True,
    )
    def test_settings_initialization_with_environment_variables(self, mock_file_operations) -> None:
        """Test CalendarBotSettings initialization with environment variables."""
        settings = CalendarBotSettings()

        assert settings.ics_url == "https://test.com/cal.ics"
        assert settings.web_enabled is True
        assert settings.web_port == 9000
        assert settings.cache_ttl == 1200

    def test_settings_config_file_path_resolution(self, mock_file_operations) -> None:
        """Test configuration file path resolution."""
        settings = CalendarBotSettings()

        # Test property access
        assert isinstance(settings.database_file, Path)
        assert isinstance(settings.config_file, Path)
        assert isinstance(settings.ics_cache_file, Path)

        # Check path construction
        assert settings.database_file.name == "calendar_cache.db"
        assert settings.config_file.name == "config.yaml"
        assert settings.ics_cache_file.name == "ics_cache.json"

    @patch.dict("os.environ", {"CALENDARBOT_ICS_URL": "https://test.com/cal.ics"}, clear=True)
    def test_ics_config_validation_with_url(self, mock_file_operations) -> None:
        """Test ICS configuration validation when URL is present."""
        settings = CalendarBotSettings()

        # Should not raise when URL is configured
        settings._validate_ics_config()  # Should pass without exception

    @patch.dict("os.environ", {}, clear=True)
    def test_settings_environment_ignore_empty(self, mock_file_operations) -> None:
        """Test settings with empty environment variable handling."""
        with patch.dict("os.environ", {"CALENDARBOT_WEB_PORT": ""}, clear=False):
            settings = CalendarBotSettings(_env_ignore_empty=True)

            # Empty env vars should be ignored, using defaults
            assert settings.web_port == 8080

    @patch("calendarbot.config.settings._get_safe_web_host")
    def test_settings_web_host_default(self, mock_safe_host, mock_file_operations) -> None:
        """Test settings web host default resolution."""
        mock_safe_host.return_value = "192.168.1.100"

        settings = CalendarBotSettings()

        assert settings.web_host == "192.168.1.100"
        mock_safe_host.assert_called_once()


class TestGlobalSettingsManagement:
    """Tests for global settings management functions."""

    def test_get_settings_creates_instance(self, clean_settings, mock_file_operations) -> None:
        """Test get_settings creates new instance when none exists."""
        settings = get_settings()

        assert isinstance(settings, CalendarBotSettings)
        assert settings.app_name == "CalendarBot"

    def test_get_settings_returns_same_instance(self, clean_settings, mock_file_operations) -> None:
        """Test get_settings returns same instance on subsequent calls."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_reset_settings(self, clean_settings, mock_file_operations) -> None:
        """Test reset_settings clears global instance."""
        # Create instance
        settings1 = get_settings()
        assert settings1 is not None

        # Reset and create new instance
        reset_settings()
        settings2 = get_settings()

        # Should be different instances
        assert settings1 is not settings2


class TestSettingsProxy:
    """Tests for the settings proxy class."""

    def test_settings_proxy_attribute_access(self, clean_settings, mock_file_operations) -> None:
        """Test settings proxy delegates attribute access."""
        proxy = _SettingsProxy()

        # Should delegate to underlying settings instance
        assert proxy.app_name == "CalendarBot"
        assert proxy.web_port == 8080

    def test_settings_proxy_attribute_setting(self, clean_settings, mock_file_operations) -> None:
        """Test settings proxy delegates attribute setting."""
        proxy = _SettingsProxy()

        # Should delegate to underlying settings instance
        proxy.web_port = 9000
        assert proxy.web_port == 9000

    def test_settings_proxy_repr(self, clean_settings, mock_file_operations) -> None:
        """Test settings proxy repr method."""
        proxy = _SettingsProxy()

        # Should delegate to underlying settings instance
        repr_str = repr(proxy)
        assert "CalendarBotSettings" in repr_str


class TestUtilityFunctions:
    """Tests for utility functions."""

    @patch("calendarbot.utils.network.get_local_network_interface")
    def test_get_safe_web_host_with_network_utils(self, mock_network_func) -> None:
        """Test _get_safe_web_host with network utils available."""
        mock_network_func.return_value = "192.168.1.100"

        result = _get_safe_web_host()

        assert result == "192.168.1.100"
        mock_network_func.assert_called_once()

    @patch("calendarbot.utils.network.get_local_network_interface", side_effect=ImportError())
    def test_get_safe_web_host_fallback(self, mock_network_func) -> None:
        """Test _get_safe_web_host fallback when network utils unavailable."""
        result = _get_safe_web_host()

        assert result == "127.0.0.1"

    @pytest.mark.parametrize(
        ("input_text", "expected"),
        [
            ("password123", "pa*******23"),
            ("", ""),
            ("ab", "***"),
            ("abcd", "***"),
            ("12345", "12*45"),
        ],
    )
    def test_mask_credentials_fallback(self, input_text, expected) -> None:
        """Test credential masking fallback function."""
        result = _mask_credentials_fallback(input_text)
        assert result == expected


class TestSettingsComplexScenarios:
    """Tests for complex settings scenarios."""

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.open", mock_open())
    @patch("calendarbot.config.settings.yaml.safe_load")
    def test_settings_yaml_config_loading(self, mock_yaml_load, mock_file_operations) -> None:
        """Test settings with YAML configuration loading."""
        yaml_config = {
            "web": {
                "enabled": True,
                "port": 9090,
                "layout": "test-layout",
            },
            "logging": {
                "console_level": "ERROR",
                "file_enabled": False,
            },
        }
        mock_yaml_load.return_value = yaml_config

        settings = CalendarBotSettings()

        # Should have loaded YAML configuration
        assert settings.web_enabled is True
        assert settings.web_port == 9090
        assert settings.web_layout == "test-layout"

    def test_settings_explicit_args_tracking(self, mock_file_operations) -> None:
        """Test that explicitly provided arguments are tracked."""
        settings = CalendarBotSettings(web_port=9000, cache_ttl=1800)

        # Should track explicitly provided arguments
        assert "web_port" in settings._explicit_args
        assert "cache_ttl" in settings._explicit_args
        assert "display_type" not in settings._explicit_args  # Not explicitly provided
