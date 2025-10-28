"""Unit tests for calendarbot.setup_wizard module.

Tests interactive configuration wizard including user input handling,
configuration generation, validation, and file operations.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
import yaml

from calendarbot.ics.exceptions import ICSError
from calendarbot.ics.models import AuthType
from calendarbot.setup_wizard import (
    CalendarServiceTemplate,
    SetupWizard,
    run_setup_wizard,
    run_simple_wizard,
)


class TestCalendarServiceTemplate:
    """Test CalendarServiceTemplate data class."""

    def test_calendar_service_template_creation(self):
        """Test CalendarServiceTemplate creation with all parameters."""
        template = CalendarServiceTemplate(
            name="Test Service",
            description="Test description",
            url_pattern=r"https://test\.com/.*",
            auth_type="basic",
            instructions="Test instructions",
        )

        assert template.name == "Test Service"
        assert template.description == "Test description"
        assert template.url_pattern == r"https://test\.com/.*"
        assert template.auth_type == "basic"
        assert template.instructions == "Test instructions"

    def test_calendar_service_template_defaults(self):
        """Test CalendarServiceTemplate creation with default values."""
        template = CalendarServiceTemplate(
            name="Simple Service",
            description="Simple description",
            url_pattern=r"https://simple\.com/.*",
        )

        assert template.name == "Simple Service"
        assert template.description == "Simple description"
        assert template.url_pattern == r"https://simple\.com/.*"
        assert template.auth_type == "none"
        assert template.instructions == ""


class TestSetupWizardInitialization:
    """Test SetupWizard initialization and basic functionality."""

    def test_setup_wizard_initialization(self):
        """Test SetupWizard initialization."""
        wizard = SetupWizard()

        assert wizard.config_data == {}
        assert wizard.settings is None
        assert isinstance(wizard.SERVICE_TEMPLATES, dict)
        assert "outlook" in wizard.SERVICE_TEMPLATES
        assert "google" in wizard.SERVICE_TEMPLATES
        assert "icloud" in wizard.SERVICE_TEMPLATES
        assert "caldav" in wizard.SERVICE_TEMPLATES
        assert "custom" in wizard.SERVICE_TEMPLATES

    def test_service_templates_structure(self):
        """Test SERVICE_TEMPLATES contains expected services."""
        wizard = SetupWizard()

        # Check Outlook template - Note: url_pattern is a regex with escaped dots
        outlook = wizard.SERVICE_TEMPLATES["outlook"]
        assert outlook.name == "Microsoft Outlook"
        assert "outlook" in outlook.url_pattern and "live" in outlook.url_pattern
        assert outlook.auth_type == "none"

        # Check Google template
        google = wizard.SERVICE_TEMPLATES["google"]
        assert google.name == "Google Calendar"
        assert "calendar" in google.url_pattern and "google" in google.url_pattern
        assert google.auth_type == "none"

        # Check CalDAV template
        caldav = wizard.SERVICE_TEMPLATES["caldav"]
        assert caldav.name == "CalDAV Server"
        assert caldav.auth_type == "basic"


class TestSetupWizardUIHelpers:
    """Test SetupWizard UI helper methods."""

    @patch("builtins.print")
    def test_print_header(self, mock_print):
        """Test print_header formatting."""
        wizard = SetupWizard()
        wizard.print_header("Test Title")

        # Should print multiple lines including header with emoji
        assert mock_print.call_count >= 3
        calls = [call.args[0] for call in mock_print.call_args_list]
        assert any("📅 Test Title" in call for call in calls)
        assert any("=" * 60 in call for call in calls)

    @patch("builtins.print")
    def test_print_section(self, mock_print):
        """Test print_section formatting."""
        wizard = SetupWizard()
        wizard.print_section("Test Section")

        # Should print section with emoji and separator
        assert mock_print.call_count >= 2
        calls = [call.args[0] for call in mock_print.call_args_list]
        assert any("🔧 Test Section" in call for call in calls)
        assert any("-" * 40 in call for call in calls)

    @patch("builtins.input", return_value="test input")
    def test_get_input_basic(self, mock_input):
        """Test get_input with basic functionality."""
        wizard = SetupWizard()
        result = wizard.get_input("Enter value")

        assert result == "test input"
        mock_input.assert_called_once_with("Enter value: ")

    @patch("builtins.input", return_value="")
    def test_get_input_with_default(self, mock_input):
        """Test get_input with default value."""
        wizard = SetupWizard()
        result = wizard.get_input("Enter value", default="default_value")

        assert result == "default_value"
        mock_input.assert_called_once_with("Enter value [default_value]: ")

    @patch("builtins.input", side_effect=["", "valid input"])
    @patch("builtins.print")
    def test_get_input_required_validation(self, mock_print, mock_input):
        """Test get_input requires input when required=True."""
        wizard = SetupWizard()
        result = wizard.get_input("Enter value", required=True)

        assert result == "valid input"
        assert mock_input.call_count == 2
        # Should print error message for empty input
        error_calls = [
            call for call in mock_print.call_args_list if "This field is required" in str(call)
        ]
        assert len(error_calls) > 0

    @patch("builtins.input", side_effect=["invalid", "valid"])
    @patch("builtins.print")
    def test_get_input_with_validation(self, mock_print, mock_input):
        """Test get_input with validation function."""

        def validate_func(value):
            return value == "valid"

        wizard = SetupWizard()
        result = wizard.get_input("Enter value", validate_func=validate_func)

        assert result == "valid"
        assert mock_input.call_count == 2
        # Should print error message for invalid input
        error_calls = [call for call in mock_print.call_args_list if "Invalid input" in str(call)]
        assert len(error_calls) > 0

    @patch("builtins.input", return_value="2")
    @patch("builtins.print")
    def test_get_choice_basic(self, mock_print, mock_input):
        """Test get_choice with basic functionality."""
        wizard = SetupWizard()
        choices = ["Option 1", "Option 2", "Option 3"]
        result = wizard.get_choice("Choose option", choices)

        assert result == "Option 2"
        mock_input.assert_called_once_with("\nEnter choice (1-3): ")

    @patch("builtins.input", return_value="1")
    @patch("builtins.print")
    def test_get_choice_with_descriptions(self, mock_print, mock_input):
        """Test get_choice with descriptions."""
        wizard = SetupWizard()
        choices = ["Option 1", "Option 2"]
        descriptions = ["First option", "Second option"]
        result = wizard.get_choice("Choose option", choices, descriptions)

        assert result == "Option 1"
        # Should print options with descriptions
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Option 1 - First option" in call for call in print_calls)

    @patch("builtins.input", side_effect=["0", "4", "2"])
    @patch("builtins.print")
    def test_get_choice_validation(self, mock_print, mock_input):
        """Test get_choice validates input range."""
        wizard = SetupWizard()
        choices = ["Option 1", "Option 2", "Option 3"]
        result = wizard.get_choice("Choose option", choices)

        assert result == "Option 2"
        assert mock_input.call_count == 3
        # Should print error messages for invalid choices
        error_calls = [
            call
            for call in mock_print.call_args_list
            if "Please enter a number between" in str(call)
        ]
        assert len(error_calls) >= 2

    @pytest.mark.parametrize(
        ("input_value", "expected"),
        [
            ("y", True),
            ("yes", True),
            ("Y", True),
            ("YES", True),
            ("n", False),
            ("no", False),
            ("N", False),
            ("", False),  # Default False
        ],
    )
    @patch("builtins.input")
    def test_get_yes_no(self, mock_input, input_value, expected):
        """Test get_yes_no with various inputs."""
        mock_input.return_value = input_value
        wizard = SetupWizard()
        result = wizard.get_yes_no("Continue?", default=False)

        assert result == expected

    @patch("builtins.input", return_value="")
    def test_get_yes_no_default_true(self, mock_input):
        """Test get_yes_no with default=True."""
        wizard = SetupWizard()
        result = wizard.get_yes_no("Continue?", default=True)

        assert result is True
        mock_input.assert_called_once_with("Continue? [Y/n]: ")


class TestSetupWizardValidation:
    """Test SetupWizard validation methods."""

    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://example.com", True),
            ("http://example.com", True),
            ("https://example.com:8080/path", True),
            ("http://localhost:3000", True),
            ("https://192.168.1.1", True),
            ("ftp://example.com", False),
            ("not-a-url", False),
            ("example.com", False),
            ("", False),
        ],
    )
    @patch("builtins.print")
    def test_validate_url(self, mock_print, url, expected):
        """Test URL validation with various inputs."""
        wizard = SetupWizard()
        result = wizard.validate_url(url)

        assert result == expected
        if not expected and url:
            # Should print error message for invalid URLs
            error_calls = [
                call
                for call in mock_print.call_args_list
                if "Please enter a valid HTTP or HTTPS URL" in str(call)
            ]
            assert len(error_calls) > 0


class TestSetupWizardServiceSelection:
    """Test calendar service selection functionality."""

    @patch.object(SetupWizard, "get_choice", return_value="Google Calendar")
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    def test_select_calendar_service(self, mock_print, mock_print_section, mock_get_choice):
        """Test calendar service selection."""
        wizard = SetupWizard()
        result = wizard.select_calendar_service()

        assert result == "google"
        mock_print_section.assert_called_once_with("Calendar Service Selection")
        mock_get_choice.assert_called_once()

    @patch.object(SetupWizard, "get_choice", return_value="Unknown Service")
    @patch.object(SetupWizard, "print_section")
    def test_select_calendar_service_fallback(self, mock_print_section, mock_get_choice):
        """Test calendar service selection with unknown service."""
        wizard = SetupWizard()
        result = wizard.select_calendar_service()

        assert result == "custom"  # Should fallback to custom


class TestSetupWizardICSConfiguration:
    """Test ICS URL configuration functionality."""

    @patch.object(SetupWizard, "get_input", return_value="https://example.com/calendar.ics")
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    def test_configure_ics_url_basic(self, mock_print, mock_print_section, mock_get_input):
        """Test basic ICS URL configuration."""
        wizard = SetupWizard()
        result = wizard.configure_ics_url("custom")

        assert result == {"url": "https://example.com/calendar.ics", "recommended_auth": "none"}
        mock_print_section.assert_called_once()
        mock_get_input.assert_called_once()

    @patch.object(
        SetupWizard,
        "get_input",
        return_value="https://calendar.google.com/calendar/ical/test/basic.ics",
    )
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    def test_configure_ics_url_google_pattern_match(
        self, mock_print, mock_print_section, mock_get_input
    ):
        """Test ICS URL configuration with Google service pattern matching."""
        wizard = SetupWizard()
        result = wizard.configure_ics_url("google")

        assert result == {
            "url": "https://calendar.google.com/calendar/ical/test/basic.ics",
            "recommended_auth": "none",
        }

    @patch.object(SetupWizard, "get_input", return_value="https://wrong-pattern.com/calendar.ics")
    @patch.object(SetupWizard, "get_yes_no", return_value=True)
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    def test_configure_ics_url_pattern_mismatch_continue(
        self, mock_print, mock_print_section, mock_get_yes_no, mock_get_input
    ):
        """Test ICS URL configuration with pattern mismatch but user continues."""
        wizard = SetupWizard()
        result = wizard.configure_ics_url("google")

        assert result == {
            "url": "https://wrong-pattern.com/calendar.ics",
            "recommended_auth": "none",
        }
        mock_get_yes_no.assert_called_once()
        # Should print warning about pattern mismatch
        warning_calls = [
            call
            for call in mock_print.call_args_list
            if "Warning: URL doesn't match expected pattern" in str(call)
        ]
        assert len(warning_calls) > 0

    @patch.object(
        SetupWizard,
        "get_input",
        side_effect=[
            "https://wrong-pattern.com/calendar.ics",
            "https://calendar.google.com/calendar/ical/test/basic.ics",
        ],
    )
    @patch.object(SetupWizard, "get_yes_no", return_value=False)
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    def test_configure_ics_url_pattern_mismatch_retry(
        self, mock_print, mock_print_section, mock_get_yes_no, mock_get_input
    ):
        """Test ICS URL configuration with pattern mismatch and retry."""
        wizard = SetupWizard()
        result = wizard.configure_ics_url("google")

        assert result == {
            "url": "https://calendar.google.com/calendar/ical/test/basic.ics",
            "recommended_auth": "none",
        }
        assert mock_get_input.call_count == 2


class TestSetupWizardAuthentication:
    """Test authentication configuration functionality."""

    @patch.object(SetupWizard, "get_choice", return_value="none")
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    def test_configure_authentication_none(self, mock_print, mock_print_section, mock_get_choice):
        """Test authentication configuration with no auth."""
        wizard = SetupWizard()
        result = wizard.configure_authentication()

        assert result == {"auth_type": "none"}
        mock_print_section.assert_called_once()

    @patch.object(SetupWizard, "get_input", side_effect=["testuser", "testpass"])
    @patch.object(SetupWizard, "get_choice", return_value="basic")
    @patch.object(SetupWizard, "print_section")
    @patch("calendarbot.setup_wizard.SecurityEventLogger")
    @patch("builtins.print")
    def test_configure_authentication_basic(
        self, mock_print, mock_security_logger, mock_print_section, mock_get_choice, mock_get_input
    ):
        """Test authentication configuration with basic auth."""
        mock_logger_instance = MagicMock()
        mock_security_logger.return_value = mock_logger_instance

        wizard = SetupWizard()
        result = wizard.configure_authentication()

        assert result == {"auth_type": "basic", "username": "testuser", "password": "testpass"}
        mock_security_logger.assert_called_once()
        mock_logger_instance.log_authentication_success.assert_called_once()

    @patch.object(SetupWizard, "get_input", return_value="bearer123token")
    @patch.object(SetupWizard, "get_choice", return_value="bearer")
    @patch.object(SetupWizard, "print_section")
    @patch("calendarbot.setup_wizard.SecurityEventLogger")
    @patch("builtins.print")
    def test_configure_authentication_bearer(
        self, mock_print, mock_security_logger, mock_print_section, mock_get_choice, mock_get_input
    ):
        """Test authentication configuration with bearer token."""
        mock_logger_instance = MagicMock()
        mock_security_logger.return_value = mock_logger_instance

        wizard = SetupWizard()
        result = wizard.configure_authentication()

        assert result == {"auth_type": "bearer", "token": "bearer123token"}
        mock_security_logger.assert_called_once()
        mock_logger_instance.log_authentication_success.assert_called_once()

    @patch.object(SetupWizard, "get_input", side_effect=["testuser", "testpass"])
    @patch.object(SetupWizard, "get_choice", return_value="basic")
    @patch.object(SetupWizard, "print_section")
    @patch("calendarbot.setup_wizard.SecurityEventLogger")
    @patch("builtins.print")
    def test_configure_authentication_with_recommendation(
        self, mock_print, mock_security_logger, mock_print_section, mock_get_choice, mock_get_input
    ):
        """Test authentication configuration shows recommendation."""
        mock_logger_instance = MagicMock()
        mock_security_logger.return_value = mock_logger_instance

        wizard = SetupWizard()
        result = wizard.configure_authentication(recommended_auth="basic")

        # Should return authentication config
        assert result == {"auth_type": "basic", "username": "testuser", "password": "testpass"}

        # Should print recommendation
        recommendation_calls = [
            call
            for call in mock_print.call_args_list
            if "Recommended for your service: basic" in str(call)
        ]
        assert len(recommendation_calls) > 0


class TestSetupWizardAdvancedSettings:
    """Test advanced settings configuration."""

    @patch.object(SetupWizard, "get_input", side_effect=["600", "7200", ""])
    @patch.object(SetupWizard, "get_choice", return_value="INFO")
    @patch.object(SetupWizard, "get_yes_no", return_value=False)
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    def test_configure_advanced_settings(
        self, mock_print, mock_print_section, mock_get_yes_no, mock_get_choice, mock_get_input
    ):
        """Test advanced settings configuration."""
        wizard = SetupWizard()
        result = wizard.configure_advanced_settings()

        expected = {
            "refresh_interval": 600,
            "cache_ttl": 7200,
            "verify_ssl": False,
            "log_level": "INFO",
        }
        assert result == expected

    @patch.object(SetupWizard, "get_input", side_effect=["invalid", ""])
    @patch.object(SetupWizard, "get_choice", return_value="DEBUG")
    @patch.object(SetupWizard, "get_yes_no", return_value=True)
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    def test_configure_advanced_settings_invalid_numbers(
        self, mock_print, mock_print_section, mock_get_yes_no, mock_get_choice, mock_get_input
    ):
        """Test advanced settings with invalid number inputs."""
        wizard = SetupWizard()
        result = wizard.configure_advanced_settings()

        # Should use defaults for invalid numbers
        assert result["refresh_interval"] == 300  # Default
        assert result["verify_ssl"] is True
        assert result["log_level"] == "DEBUG"

        # Should print warning about invalid number
        warning_calls = [
            call
            for call in mock_print.call_args_list
            if "Invalid number, using default" in str(call)
        ]
        assert len(warning_calls) > 0


class TestSetupWizardConfigurationTesting:
    """Test configuration testing functionality."""

    @pytest.mark.asyncio
    @patch("calendarbot.setup_wizard.ICSFetcher")
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    async def test_test_configuration_success(
        self, mock_print, mock_print_section, mock_fetcher_class
    ):
        """Test successful configuration testing."""
        # Mock successful fetch response
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR"

        mock_fetcher_instance = AsyncMock()
        mock_fetcher_instance.test_connection = AsyncMock(return_value=True)
        mock_fetcher_instance.fetch_ics = AsyncMock(return_value=mock_response)

        mock_fetcher_class.return_value.__aenter__ = AsyncMock(return_value=mock_fetcher_instance)
        mock_fetcher_class.return_value.__aexit__ = AsyncMock(return_value=None)

        wizard = SetupWizard()
        ics_config = {"url": "https://example.com/calendar.ics", "auth_type": "none"}

        result = await wizard.test_configuration(ics_config)

        assert result is True
        mock_fetcher_instance.test_connection.assert_called_once()
        mock_fetcher_instance.fetch_ics.assert_called_once()

    @pytest.mark.asyncio
    @patch("calendarbot.setup_wizard.ICSFetcher")
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    async def test_test_configuration_connection_failure(
        self, mock_print, mock_print_section, mock_fetcher_class
    ):
        """Test configuration testing with connection failure."""
        mock_fetcher_instance = AsyncMock()
        mock_fetcher_instance.test_connection = AsyncMock(return_value=False)

        mock_fetcher_class.return_value.__aenter__ = AsyncMock(return_value=mock_fetcher_instance)
        mock_fetcher_class.return_value.__aexit__ = AsyncMock(return_value=None)

        wizard = SetupWizard()
        ics_config = {"url": "https://example.com/calendar.ics", "auth_type": "none"}

        result = await wizard.test_configuration(ics_config)

        assert result is False
        mock_fetcher_instance.test_connection.assert_called_once()

    @pytest.mark.asyncio
    @patch("calendarbot.setup_wizard.ICSFetcher")
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    async def test_test_configuration_fetch_failure(
        self, mock_print, mock_print_section, mock_fetcher_class
    ):
        """Test configuration testing with fetch failure."""
        mock_response = MagicMock()
        mock_response.success = False
        mock_response.error_message = "HTTP 404 Not Found"

        mock_fetcher_instance = AsyncMock()
        mock_fetcher_instance.test_connection = AsyncMock(return_value=True)
        mock_fetcher_instance.fetch_ics = AsyncMock(return_value=mock_response)

        mock_fetcher_class.return_value.__aenter__ = AsyncMock(return_value=mock_fetcher_instance)
        mock_fetcher_class.return_value.__aexit__ = AsyncMock(return_value=None)

        wizard = SetupWizard()
        ics_config = {"url": "https://example.com/calendar.ics", "auth_type": "none"}

        result = await wizard.test_configuration(ics_config)

        assert result is False

    @pytest.mark.asyncio
    @patch("calendarbot.setup_wizard.ICSFetcher")
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    async def test_test_configuration_ics_error(
        self, mock_print, mock_print_section, mock_fetcher_class
    ):
        """Test configuration testing with ICS error."""
        mock_fetcher_instance = AsyncMock()
        mock_fetcher_instance.test_connection = AsyncMock(side_effect=ICSError("Invalid format"))

        mock_fetcher_class.return_value.__aenter__ = AsyncMock(return_value=mock_fetcher_instance)
        mock_fetcher_class.return_value.__aexit__ = AsyncMock(return_value=None)

        wizard = SetupWizard()
        ics_config = {"url": "https://example.com/calendar.ics", "auth_type": "none"}

        result = await wizard.test_configuration(ics_config)

        assert result is False

    @pytest.mark.asyncio
    @patch("calendarbot.setup_wizard.ICSFetcher")
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    async def test_test_configuration_with_authentication(
        self, mock_print, mock_print_section, mock_fetcher_class
    ):
        """Test configuration testing with authentication."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = "BEGIN:VCALENDAR\nEND:VCALENDAR"

        mock_fetcher_instance = AsyncMock()
        mock_fetcher_instance.test_connection = AsyncMock(return_value=True)
        mock_fetcher_instance.fetch_ics = AsyncMock(return_value=mock_response)

        mock_fetcher_class.return_value.__aenter__ = AsyncMock(return_value=mock_fetcher_instance)
        mock_fetcher_class.return_value.__aexit__ = AsyncMock(return_value=None)

        wizard = SetupWizard()
        ics_config = {
            "url": "https://example.com/calendar.ics",
            "auth_type": "basic",
            "username": "testuser",
            "password": "testpass",
        }

        result = await wizard.test_configuration(ics_config)

        assert result is True
        # Verify ICSSource was created with correct auth
        call_args = mock_fetcher_instance.test_connection.call_args[0][0]
        assert call_args.auth.type == AuthType.BASIC
        assert call_args.auth.username == "testuser"
        assert call_args.auth.password == "testpass"


class TestSetupWizardConfigGeneration:
    """Test configuration file generation."""

    def test_generate_config_content_basic(self):
        """Test basic configuration content generation."""
        wizard = SetupWizard()
        ics_config = {"url": "https://example.com/calendar.ics", "auth_type": "none"}
        advanced_settings = {
            "refresh_interval": 300,
            "cache_ttl": 3600,
            "verify_ssl": True,
            "log_level": "INFO",
        }

        result = wizard.generate_config_content(ics_config, advanced_settings)

        # Verify it's valid YAML
        config = yaml.safe_load(result)
        assert config["ics"]["url"] == "https://example.com/calendar.ics"
        assert config["ics"]["auth_type"] == "none"
        assert config["refresh_interval"] == 300
        assert config["cache_ttl"] == 3600
        assert config["log_level"] == "INFO"

    def test_generate_config_content_with_basic_auth(self):
        """Test configuration generation with basic authentication."""
        wizard = SetupWizard()
        ics_config = {
            "url": "https://example.com/calendar.ics",
            "auth_type": "basic",
            "username": "testuser",
            "password": "testpass",
        }
        advanced_settings = {}

        result = wizard.generate_config_content(ics_config, advanced_settings)

        config = yaml.safe_load(result)
        assert config["ics"]["auth_type"] == "basic"
        assert config["ics"]["username"] == "testuser"
        assert config["ics"]["password"] == "testpass"

    def test_generate_config_content_with_bearer_token(self):
        """Test configuration generation with bearer token."""
        wizard = SetupWizard()
        ics_config = {
            "url": "https://example.com/calendar.ics",
            "auth_type": "bearer",
            "token": "bearer123token",
        }
        advanced_settings = {}

        result = wizard.generate_config_content(ics_config, advanced_settings)

        config = yaml.safe_load(result)
        assert config["ics"]["auth_type"] == "bearer"
        assert config["ics"]["token"] == "bearer123token"

    def test_generate_config_content_includes_timestamp(self):
        """Test configuration includes generation timestamp."""
        wizard = SetupWizard()
        ics_config = {"url": "https://example.com/cal.ics", "auth_type": "none"}
        advanced_settings = {}

        result = wizard.generate_config_content(ics_config, advanced_settings)

        # Should include timestamp in header comment
        current_year = datetime.now().year
        assert f"Generated by setup wizard on {current_year}" in result


class TestSetupWizardConfigSaving:
    """Test configuration file saving functionality."""

    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists", return_value=False)
    @patch("pathlib.Path.open", new_callable=mock_open)
    @patch.object(SetupWizard, "get_choice", return_value="Project directory")
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    def test_save_configuration_success(
        self, mock_print, mock_print_section, mock_get_choice, mock_file, mock_exists, mock_mkdir
    ):
        """Test successful configuration saving."""
        wizard = SetupWizard()
        config_content = "test: configuration"

        result = wizard.save_configuration(config_content)

        assert result is not None
        assert result.name == "config.yaml"
        mock_file.assert_called_once()
        mock_file().write.assert_called_once_with(config_content)

    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.open", new_callable=mock_open)
    @patch.object(SetupWizard, "get_choice", return_value="Project directory")
    @patch.object(SetupWizard, "get_yes_no", return_value=True)
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    def test_save_configuration_overwrite_existing(
        self,
        mock_print,
        mock_print_section,
        mock_get_yes_no,
        mock_get_choice,
        mock_file,
        mock_exists,
        mock_mkdir,
    ):
        """Test configuration saving with existing file overwrite."""
        wizard = SetupWizard()
        config_content = "test: configuration"

        result = wizard.save_configuration(config_content)

        assert result is not None
        mock_get_yes_no.assert_called_once()
        mock_file().write.assert_called_once_with(config_content)

    @patch("pathlib.Path.exists", return_value=True)
    @patch.object(SetupWizard, "get_choice", return_value="Project directory")
    @patch.object(SetupWizard, "get_yes_no", return_value=False)
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    def test_save_configuration_cancel_overwrite(
        self, mock_print, mock_print_section, mock_get_yes_no, mock_get_choice, mock_exists
    ):
        """Test configuration saving cancelled when user rejects overwrite."""
        wizard = SetupWizard()
        config_content = "test: configuration"

        result = wizard.save_configuration(config_content)

        assert result is None
        mock_get_yes_no.assert_called_once()

    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists", return_value=False)
    @patch("pathlib.Path.open", side_effect=OSError("Permission denied"))
    @patch.object(SetupWizard, "get_choice", return_value="Project directory")
    @patch.object(SetupWizard, "print_section")
    @patch("builtins.print")
    def test_save_configuration_write_error(
        self, mock_print, mock_print_section, mock_get_choice, mock_file, mock_exists, mock_mkdir
    ):
        """Test configuration saving with write error."""
        wizard = SetupWizard()
        config_content = "test: configuration"

        result = wizard.save_configuration(config_content)

        assert result is None
        # Should print error message
        error_calls = [
            call
            for call in mock_print.call_args_list
            if "Failed to save configuration" in str(call)
        ]
        assert len(error_calls) > 0


class TestSetupWizardCompletionMessage:
    """Test setup completion message display."""

    @patch.object(SetupWizard, "print_header")
    @patch("builtins.print")
    def test_show_completion_message_with_config_path(self, mock_print, mock_print_header):
        """Test completion message with valid config path."""
        wizard = SetupWizard()
        config_path = Path("/test/config.yaml")

        wizard.show_completion_message(config_path)

        mock_print_header.assert_called_once_with("Setup Complete! 🎉")
        # Should print next steps and documentation
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Next Steps:" in call for call in print_calls)
        assert any("calendarbot --test-mode" in call for call in print_calls)

    @patch.object(SetupWizard, "print_header")
    @patch("builtins.print")
    def test_show_completion_message_without_config_path(self, mock_print, mock_print_header):
        """Test completion message without config path."""
        wizard = SetupWizard()

        wizard.show_completion_message(None)

        mock_print_header.assert_called_once_with("Setup Complete! 🎉")
        # Should print warning about config not saved
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("Configuration file could not be saved" in call for call in print_calls)


class TestSetupWizardMainFlow:
    """Test main setup wizard flow."""

    @pytest.mark.asyncio
    @patch.object(SetupWizard, "get_yes_no", side_effect=[True, True, False, True])
    @patch.object(SetupWizard, "select_calendar_service", return_value="google")
    @patch.object(
        SetupWizard,
        "configure_ics_url",
        return_value={"url": "https://example.com/cal.ics", "recommended_auth": "none"},
    )
    @patch.object(SetupWizard, "configure_authentication", return_value={"auth_type": "none"})
    @patch.object(SetupWizard, "test_configuration", return_value=True)
    @patch.object(SetupWizard, "generate_config_content", return_value="config: content")
    @patch.object(SetupWizard, "save_configuration", return_value=Path("/test/config.yaml"))
    @patch.object(SetupWizard, "show_completion_message")
    @patch.object(SetupWizard, "print_header")
    @patch("builtins.print")
    async def test_run_success_minimal_flow(
        self,
        mock_print,
        mock_print_header,
        mock_show_completion,
        mock_save_config,
        mock_generate_config,
        mock_test_config,
        mock_configure_auth,
        mock_configure_ics,
        mock_select_service,
        mock_get_yes_no,
    ):
        """Test successful minimal wizard flow."""
        wizard = SetupWizard()
        result = await wizard.run()

        assert result is True
        mock_select_service.assert_called_once()
        mock_configure_ics.assert_called_once()
        mock_configure_auth.assert_called_once()
        mock_test_config.assert_called_once()
        mock_save_config.assert_called_once()
        mock_show_completion.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(SetupWizard, "get_yes_no", return_value=False)
    @patch.object(SetupWizard, "print_header")
    @patch("builtins.print")
    async def test_run_cancelled_at_start(self, mock_print, mock_print_header, mock_get_yes_no):
        """Test wizard cancelled at start."""
        wizard = SetupWizard()
        result = await wizard.run()

        assert result is False
        mock_get_yes_no.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(SetupWizard, "get_yes_no", side_effect=[True, True, False])
    @patch.object(SetupWizard, "select_calendar_service", return_value="google")
    @patch.object(
        SetupWizard,
        "configure_ics_url",
        return_value={"url": "https://example.com/cal.ics", "recommended_auth": "none"},
    )
    @patch.object(SetupWizard, "configure_authentication", return_value={"auth_type": "none"})
    @patch.object(SetupWizard, "test_configuration", return_value=False)
    @patch.object(SetupWizard, "print_header")
    @patch("builtins.print")
    async def test_run_test_failure_cancelled(
        self,
        mock_print,
        mock_print_header,
        mock_test_config,
        mock_configure_auth,
        mock_configure_ics,
        mock_select_service,
        mock_get_yes_no,
    ):
        """Test wizard cancelled after test failure."""
        wizard = SetupWizard()
        result = await wizard.run()

        assert result is False
        mock_test_config.assert_called_once()

    @pytest.mark.asyncio
    @patch.object(SetupWizard, "print_header")
    @patch("builtins.print")
    async def test_run_keyboard_interrupt(self, mock_print, mock_print_header):
        """Test wizard handles keyboard interrupt."""
        wizard = SetupWizard()

        with patch.object(wizard, "get_yes_no", side_effect=KeyboardInterrupt()):
            result = await wizard.run()

        assert result is False
        # Should print cancellation message
        cancel_calls = [
            call for call in mock_print.call_args_list if "Setup cancelled by user" in str(call)
        ]
        assert len(cancel_calls) > 0


class TestStandaloneFunctions:
    """Test standalone setup wizard functions."""

    @pytest.mark.asyncio
    @patch("calendarbot.setup_wizard.SetupWizard")
    async def test_run_setup_wizard(self, mock_wizard_class):
        """Test run_setup_wizard function."""
        mock_wizard_instance = AsyncMock()
        mock_wizard_instance.run = AsyncMock(return_value=True)
        mock_wizard_class.return_value = mock_wizard_instance

        result = await run_setup_wizard()

        assert result is True
        mock_wizard_class.assert_called_once()
        mock_wizard_instance.run.assert_called_once()

    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists", return_value=False)
    @patch("pathlib.Path.open", new_callable=mock_open)
    @patch("builtins.input", return_value="https://example.com/calendar.ics")
    @patch("builtins.print")
    def test_run_simple_wizard_success(
        self, mock_print, mock_input, mock_file, mock_exists, mock_mkdir
    ):
        """Test successful simple wizard run."""
        result = run_simple_wizard()

        assert result is True
        mock_input.assert_called_once()
        mock_file.assert_called_once()
        mock_file().write.assert_called_once()

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.input", side_effect=["n", "https://example.com/calendar.ics"])
    @patch("builtins.print")
    def test_run_simple_wizard_existing_config_cancel(self, mock_print, mock_input, mock_exists):
        """Test simple wizard cancelled when config exists."""
        result = run_simple_wizard()

        assert result is False
        assert mock_input.call_count == 1  # Only asked about overwrite

    @patch("pathlib.Path.exists", return_value=False)
    @patch("builtins.input", return_value="")
    @patch("builtins.print")
    def test_run_simple_wizard_empty_url(self, mock_print, mock_input, mock_exists):
        """Test simple wizard with empty URL."""
        result = run_simple_wizard()

        assert result is False
        # Should print error about required URL - check for exact message from implementation
        error_calls = [
            call for call in mock_print.call_args_list if "ICS URL is required" in str(call)
        ]
        assert len(error_calls) > 0

    @patch("builtins.input", side_effect=KeyboardInterrupt())
    @patch("builtins.print")
    def test_run_simple_wizard_keyboard_interrupt(self, mock_print, mock_input):
        """Test simple wizard handles keyboard interrupt."""
        result = run_simple_wizard()

        assert result is False
        # Should print cancellation message
        cancel_calls = [
            call for call in mock_print.call_args_list if "Setup cancelled by user" in str(call)
        ]
        assert len(cancel_calls) > 0
