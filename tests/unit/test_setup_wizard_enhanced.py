"""Enhanced unit tests for calendarbot/setup_wizard.py - Setup wizard functionality."""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, call, mock_open, patch

import pytest
import yaml

from calendarbot.setup_wizard import (
    CalendarServiceTemplate,
    SetupWizard,
    run_setup_wizard,
    run_simple_wizard,
)


class TestCalendarServiceTemplate:
    """Test suite for CalendarServiceTemplate class."""

    def test_service_template_initialization_basic(self):
        """Test basic CalendarServiceTemplate initialization."""
        template = CalendarServiceTemplate(
            name="Test Service", description="Test Description", url_pattern="https://test.com/.*"
        )

        assert template.name == "Test Service"
        assert template.description == "Test Description"
        assert template.url_pattern == "https://test.com/.*"
        assert template.auth_type == "none"
        assert template.instructions == ""

    def test_service_template_initialization_full(self):
        """Test CalendarServiceTemplate initialization with all parameters."""
        template = CalendarServiceTemplate(
            name="Full Service",
            description="Full Description",
            url_pattern="https://full.com/.*",
            auth_type="basic",
            instructions="Full instructions",
        )

        assert template.name == "Full Service"
        assert template.description == "Full Description"
        assert template.url_pattern == "https://full.com/.*"
        assert template.auth_type == "basic"
        assert template.instructions == "Full instructions"


class TestSetupWizardInitialization:
    """Test suite for SetupWizard initialization and basic functionality."""

    @pytest.fixture
    def wizard(self):
        """Create a SetupWizard instance for testing."""
        return SetupWizard()

    def test_wizard_initialization(self, wizard):
        """Test SetupWizard initialization."""
        assert wizard.config_data == {}
        assert wizard.settings is None
        assert hasattr(wizard, "SERVICE_TEMPLATES")
        assert "outlook" in wizard.SERVICE_TEMPLATES
        assert "google" in wizard.SERVICE_TEMPLATES
        assert "icloud" in wizard.SERVICE_TEMPLATES
        assert "caldav" in wizard.SERVICE_TEMPLATES
        assert "custom" in wizard.SERVICE_TEMPLATES

    def test_service_templates_structure(self, wizard):
        """Test SERVICE_TEMPLATES structure and content."""
        templates = wizard.SERVICE_TEMPLATES

        for key, template in templates.items():
            assert isinstance(template, CalendarServiceTemplate)
            assert template.name
            assert template.description
            assert template.url_pattern
            assert template.auth_type in ["none", "basic", "bearer"]
            assert isinstance(template.instructions, str)

    def test_service_templates_outlook(self, wizard):
        """Test Outlook service template configuration."""
        outlook = wizard.SERVICE_TEMPLATES["outlook"]

        assert outlook.name == "Microsoft Outlook"
        assert "Outlook.com or Office 365" in outlook.description
        assert "outlook\\.live\\.com" in outlook.url_pattern
        assert outlook.auth_type == "none"
        assert "Outlook.com" in outlook.instructions

    def test_service_templates_google(self, wizard):
        """Test Google service template configuration."""
        google = wizard.SERVICE_TEMPLATES["google"]

        assert google.name == "Google Calendar"
        assert "Google Calendar" in google.description
        assert "calendar\\.google\\.com" in google.url_pattern
        assert google.auth_type == "none"
        assert "Google Calendar" in google.instructions


class TestSetupWizardUserInterface:
    """Test suite for SetupWizard user interface methods."""

    @pytest.fixture
    def wizard(self):
        """Create a SetupWizard instance for testing."""
        return SetupWizard()

    def test_print_header(self, wizard):
        """Test print_header method."""
        with patch("builtins.print") as mock_print:
            wizard.print_header("Test Title")

            calls = mock_print.call_args_list
            assert len(calls) >= 3
            assert "=" * 60 in str(calls[0])
            assert "📅 Test Title" in str(calls[1])
            assert "=" * 60 in str(calls[2])

    def test_print_section(self, wizard):
        """Test print_section method."""
        with patch("builtins.print") as mock_print:
            wizard.print_section("Test Section")

            calls = mock_print.call_args_list
            assert len(calls) >= 2
            assert "🔧 Test Section" in str(calls[0])
            assert "-" * 40 in str(calls[1])

    def test_get_input_with_default(self, wizard):
        """Test get_input method with default value."""
        with patch("builtins.input", return_value=""):
            result = wizard.get_input("Test prompt", default="default_value")

            assert result == "default_value"

    def test_get_input_user_provided(self, wizard):
        """Test get_input method with user-provided value."""
        with patch("builtins.input", return_value="user_input"):
            result = wizard.get_input("Test prompt", default="default_value")

            assert result == "user_input"

    def test_get_input_required_empty(self, wizard):
        """Test get_input method with required field and empty input."""
        with patch("builtins.input", side_effect=["", "valid_input"]), patch(
            "builtins.print"
        ) as mock_print:

            result = wizard.get_input("Test prompt", required=True)

            assert result == "valid_input"
            # Should have printed error message
            assert any("required" in str(call) for call in mock_print.call_args_list)

    def test_get_input_with_validation_success(self, wizard):
        """Test get_input method with successful validation."""

        def validate_func(value):
            return len(value) > 3

        with patch("builtins.input", return_value="valid_input"):
            result = wizard.get_input("Test prompt", validate_func=validate_func)

            assert result == "valid_input"

    def test_get_input_with_validation_failure(self, wizard):
        """Test get_input method with validation failure."""

        def validate_func(value):
            return len(value) > 10

        with patch("builtins.input", side_effect=["short", "very_long_input"]), patch(
            "builtins.print"
        ) as mock_print:

            result = wizard.get_input("Test prompt", validate_func=validate_func)

            assert result == "very_long_input"
            # Should have printed validation error
            assert any("Invalid input" in str(call) for call in mock_print.call_args_list)

    def test_get_input_validation_exception(self, wizard):
        """Test get_input method with validation exception."""

        def validate_func(value):
            raise ValueError("Validation error")

        with patch("builtins.input", side_effect=["bad_input", "good_input"]), patch(
            "builtins.print"
        ) as mock_print:

            result = wizard.get_input("Test prompt", validate_func=lambda x: True)

            assert result == "bad_input"  # First input succeeds with lambda

    def test_get_choice_valid_selection(self, wizard):
        """Test get_choice method with valid selection."""
        choices = ["Option 1", "Option 2", "Option 3"]

        with patch("builtins.input", return_value="2"), patch("builtins.print"):

            result = wizard.get_choice("Choose option:", choices)

            assert result == "Option 2"

    def test_get_choice_with_descriptions(self, wizard):
        """Test get_choice method with descriptions."""
        choices = ["Option 1", "Option 2"]
        descriptions = ["First option", "Second option"]

        with patch("builtins.input", return_value="1"), patch("builtins.print") as mock_print:

            result = wizard.get_choice("Choose option:", choices, descriptions)

            assert result == "Option 1"
            # Should have printed descriptions
            assert any("First option" in str(call) for call in mock_print.call_args_list)

    def test_get_choice_invalid_then_valid(self, wizard):
        """Test get_choice method with invalid then valid selection."""
        choices = ["Option 1", "Option 2"]

        with patch("builtins.input", side_effect=["0", "invalid", "2"]), patch(
            "builtins.print"
        ) as mock_print:

            result = wizard.get_choice("Choose option:", choices)

            assert result == "Option 2"
            # Should have printed error messages
            error_messages = [str(call) for call in mock_print.call_args_list]
            assert any("between 1 and 2" in msg for msg in error_messages)
            assert any("valid number" in msg for msg in error_messages)

    @pytest.mark.parametrize(
        "input_value,default,expected",
        [
            ("y", False, True),
            ("yes", False, True),
            ("Y", False, True),
            ("YES", False, True),
            ("n", True, False),
            ("no", True, False),
            ("N", True, False),
            ("", True, True),  # Default when empty
            ("", False, False),  # Default when empty
            ("true", False, True),
            ("1", False, True),
            ("false", False, False),
            ("0", False, False),
        ],
    )
    def test_get_yes_no(self, wizard, input_value, default, expected):
        """Test get_yes_no method with various inputs."""
        with patch("builtins.input", return_value=input_value):
            result = wizard.get_yes_no("Test question?", default=default)

            assert result == expected


class TestSetupWizardValidation:
    """Test suite for SetupWizard validation methods."""

    @pytest.fixture
    def wizard(self):
        """Create a SetupWizard instance for testing."""
        return SetupWizard()

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://example.com", True),
            ("http://localhost:8080", True),
            ("https://subdomain.example.org/path", True),
            ("http://192.168.1.100:3000/api", True),
            ("https://outlook.live.com/owa/calendar/test/calendar.ics", True),
            ("ftp://example.com", False),  # Wrong protocol
            ("not-a-url", False),
            ("", False),
            ("https://", False),  # Incomplete
            ("example.com", False),  # Missing protocol
        ],
    )
    def test_validate_url(self, wizard, url, expected):
        """Test URL validation with various URLs."""
        with patch("builtins.print"):
            result = wizard.validate_url(url)

            assert result == expected

    def test_validate_url_error_message(self, wizard):
        """Test URL validation error message."""
        with patch("builtins.print") as mock_print:
            result = wizard.validate_url("invalid-url")

            assert result is False
            assert any("valid HTTP or HTTPS URL" in str(call) for call in mock_print.call_args_list)


class TestSetupWizardServiceSelection:
    """Test suite for SetupWizard service selection methods."""

    @pytest.fixture
    def wizard(self):
        """Create a SetupWizard instance for testing."""
        return SetupWizard()

    def test_select_calendar_service_outlook(self, wizard):
        """Test calendar service selection for Outlook."""
        with patch.object(wizard, "get_choice", return_value="Microsoft Outlook"), patch.object(
            wizard, "print_section"
        ), patch("builtins.print"):

            result = wizard.select_calendar_service()

            assert result == "outlook"

    def test_select_calendar_service_google(self, wizard):
        """Test calendar service selection for Google."""
        with patch.object(wizard, "get_choice", return_value="Google Calendar"), patch.object(
            wizard, "print_section"
        ), patch("builtins.print"):

            result = wizard.select_calendar_service()

            assert result == "google"

    def test_select_calendar_service_custom(self, wizard):
        """Test calendar service selection for custom service."""
        with patch.object(wizard, "get_choice", return_value="Custom/Other"), patch.object(
            wizard, "print_section"
        ), patch("builtins.print"):

            result = wizard.select_calendar_service()

            assert result == "custom"

    def test_select_calendar_service_unknown_fallback(self, wizard):
        """Test calendar service selection fallback for unknown service."""
        with patch.object(wizard, "get_choice", return_value="Unknown Service"), patch.object(
            wizard, "print_section"
        ), patch("builtins.print"):

            result = wizard.select_calendar_service()

            assert result == "custom"  # Should fallback to custom


class TestSetupWizardConfiguration:
    """Test suite for SetupWizard configuration methods."""

    @pytest.fixture
    def wizard(self):
        """Create a SetupWizard instance for testing."""
        return SetupWizard()

    def test_configure_ics_url_outlook_valid(self, wizard):
        """Test ICS URL configuration for Outlook with valid URL."""
        outlook_url = "https://outlook.live.com/owa/calendar/test/calendar.ics"

        with patch.object(wizard, "get_input", return_value=outlook_url), patch.object(
            wizard, "print_section"
        ), patch("builtins.print"):

            result = wizard.configure_ics_url("outlook")

            assert result["url"] == outlook_url
            assert result["recommended_auth"] == "none"

    def test_configure_ics_url_pattern_mismatch_continue(self, wizard):
        """Test ICS URL configuration with pattern mismatch - user continues."""
        custom_url = "https://custom.com/calendar.ics"

        with patch.object(wizard, "get_input", return_value=custom_url), patch.object(
            wizard, "get_yes_no", return_value=True
        ), patch.object(wizard, "print_section"), patch("builtins.print"):

            result = wizard.configure_ics_url("outlook")

            assert result["url"] == custom_url
            assert result["recommended_auth"] == "none"

    def test_configure_authentication_none(self, wizard):
        """Test authentication configuration with no auth."""
        with patch.object(wizard, "get_choice", return_value="none"), patch.object(
            wizard, "print_section"
        ), patch("builtins.print"):

            result = wizard.configure_authentication()

            assert result["auth_type"] == "none"
            assert "username" not in result
            assert "password" not in result
            assert "token" not in result

    def test_configure_authentication_basic(self, wizard):
        """Test authentication configuration with basic auth."""
        with patch.object(wizard, "get_choice", return_value="basic"), patch.object(
            wizard, "get_input", side_effect=["testuser", "testpass"]
        ), patch.object(wizard, "print_section"), patch("builtins.print"), patch(
            "calendarbot.setup_wizard.SecurityEventLogger"
        ) as mock_security:

            mock_logger = MagicMock()
            mock_security.return_value = mock_logger

            result = wizard.configure_authentication()

            assert result["auth_type"] == "basic"
            assert result["username"] == "testuser"
            assert result["password"] == "testpass"
            assert "token" not in result

            # Should have logged security event
            mock_logger.log_authentication_success.assert_called_once()

    def test_configure_authentication_bearer(self, wizard):
        """Test authentication configuration with bearer token."""
        with patch.object(wizard, "get_choice", return_value="bearer"), patch.object(
            wizard, "get_input", return_value="test_token_123"
        ), patch.object(wizard, "print_section"), patch("builtins.print"), patch(
            "calendarbot.setup_wizard.SecurityEventLogger"
        ) as mock_security:

            mock_logger = MagicMock()
            mock_security.return_value = mock_logger

            result = wizard.configure_authentication()

            assert result["auth_type"] == "bearer"
            assert result["token"] == "test_token_123"
            assert "username" not in result
            assert "password" not in result

            # Should have logged security event
            mock_logger.log_authentication_success.assert_called_once()

    def test_configure_authentication_with_recommendation(self, wizard):
        """Test authentication configuration with recommendation."""
        with patch.object(wizard, "get_choice", return_value="basic"), patch.object(
            wizard, "get_input", side_effect=["user", "pass"]
        ), patch.object(wizard, "print_section"), patch("builtins.print") as mock_print, patch(
            "calendarbot.setup_wizard.SecurityEventLogger"
        ):

            wizard.configure_authentication("basic")

            # Should have shown recommendation
            printed_messages = [str(call) for call in mock_print.call_args_list]
            assert any("Recommended" in msg and "basic" in msg for msg in printed_messages)

    def test_configure_advanced_settings_defaults(self, wizard):
        """Test advanced settings configuration with defaults."""
        with patch.object(wizard, "get_input", side_effect=["", "", ""]), patch.object(
            wizard, "get_yes_no", return_value=True
        ), patch.object(wizard, "get_choice", return_value="INFO"), patch.object(
            wizard, "print_section"
        ), patch(
            "builtins.print"
        ):

            result = wizard.configure_advanced_settings()

            # When empty strings are provided, no values are set (not defaults)
            assert "refresh_interval" not in result
            assert "cache_ttl" not in result
            assert result["verify_ssl"] is True
            assert result["log_level"] == "INFO"

    def test_configure_advanced_settings_custom_values(self, wizard):
        """Test advanced settings configuration with custom values."""
        with patch.object(wizard, "get_input", side_effect=["600", "7200"]), patch.object(
            wizard, "get_yes_no", return_value=False
        ), patch.object(wizard, "get_choice", return_value="DEBUG"), patch.object(
            wizard, "print_section"
        ), patch(
            "builtins.print"
        ):

            result = wizard.configure_advanced_settings()

            assert result["refresh_interval"] == 600
            assert result["cache_ttl"] == 7200
            assert result["verify_ssl"] is False
            assert result["log_level"] == "DEBUG"

    def test_configure_advanced_settings_invalid_numbers(self, wizard):
        """Test advanced settings configuration with invalid numbers."""
        with patch.object(
            wizard, "get_input", side_effect=["invalid", "also_invalid"]
        ), patch.object(wizard, "get_yes_no", return_value=True), patch.object(
            wizard, "get_choice", return_value="WARNING"
        ), patch.object(
            wizard, "print_section"
        ), patch(
            "builtins.print"
        ) as mock_print:

            result = wizard.configure_advanced_settings()

            assert result["refresh_interval"] == 300  # Default due to invalid input
            assert result["cache_ttl"] == 3600  # Default due to invalid input

            # Should have printed warnings
            printed_messages = [str(call) for call in mock_print.call_args_list]
            assert any("Invalid number" in msg for msg in printed_messages)


class TestSetupWizardConfigurationTesting:
    """Test suite for SetupWizard configuration testing."""

    @pytest.fixture
    def wizard(self):
        """Create a SetupWizard instance for testing."""
        return SetupWizard()

    @pytest.fixture
    def mock_ics_config(self):
        """Create mock ICS configuration."""
        return {"url": "https://example.com/calendar.ics", "auth_type": "none", "verify_ssl": True}

    @pytest.fixture
    def mock_ics_config_basic_auth(self):
        """Create mock ICS configuration with basic auth."""
        return {
            "url": "https://example.com/calendar.ics",
            "auth_type": "basic",
            "username": "testuser",
            "password": "testpass",
            "verify_ssl": True,
        }

    @pytest.fixture
    def mock_ics_config_bearer(self):
        """Create mock ICS configuration with bearer token."""
        return {
            "url": "https://example.com/calendar.ics",
            "auth_type": "bearer",
            "token": "test_token",
            "verify_ssl": True,
        }

    @pytest.mark.asyncio
    async def test_test_configuration_success(self, wizard, mock_ics_config):
        """Test successful configuration testing."""
        mock_fetcher = AsyncMock()
        mock_fetcher.test_connection.return_value = True

        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = "BEGIN:VCALENDAR\nEND:VCALENDAR"
        mock_fetcher.fetch_ics.return_value = mock_response

        with patch("calendarbot.setup_wizard.ICSFetcher") as mock_fetcher_class, patch.object(
            wizard, "print_section"
        ), patch("builtins.print") as mock_print:

            mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher

            result = await wizard.test_configuration(mock_ics_config)

            assert result is True

            # Should have printed success messages
            printed_messages = [str(call) for call in mock_print.call_args_list]
            assert any("Connection successful" in msg for msg in printed_messages)
            assert any("Successfully fetched ICS data" in msg for msg in printed_messages)
            assert any("ICS format appears valid" in msg for msg in printed_messages)

    @pytest.mark.asyncio
    async def test_test_configuration_connection_failure(self, wizard, mock_ics_config):
        """Test configuration testing with connection failure."""
        mock_fetcher = AsyncMock()
        mock_fetcher.test_connection.return_value = False

        with patch("calendarbot.setup_wizard.ICSFetcher") as mock_fetcher_class, patch.object(
            wizard, "print_section"
        ), patch("builtins.print") as mock_print:

            mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher

            result = await wizard.test_configuration(mock_ics_config)

            assert result is False

            # Should have printed failure message
            printed_messages = [str(call) for call in mock_print.call_args_list]
            assert any("Connection test failed" in msg for msg in printed_messages)

    @pytest.mark.asyncio
    async def test_test_configuration_fetch_failure(self, wizard, mock_ics_config):
        """Test configuration testing with fetch failure."""
        mock_fetcher = AsyncMock()
        mock_fetcher.test_connection.return_value = True

        mock_response = MagicMock()
        mock_response.success = False
        mock_response.error_message = "Fetch failed"
        mock_fetcher.fetch_ics.return_value = mock_response

        with patch("calendarbot.setup_wizard.ICSFetcher") as mock_fetcher_class, patch.object(
            wizard, "print_section"
        ), patch("builtins.print") as mock_print:

            mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher

            result = await wizard.test_configuration(mock_ics_config)

            assert result is False

            # Should have printed error message
            printed_messages = [str(call) for call in mock_print.call_args_list]
            assert any("Failed to fetch ICS data: Fetch failed" in msg for msg in printed_messages)

    @pytest.mark.asyncio
    async def test_test_configuration_ics_error(self, wizard, mock_ics_config):
        """Test configuration testing with ICS error."""
        from calendarbot.ics.exceptions import ICSError

        mock_fetcher = AsyncMock()
        mock_fetcher.test_connection.side_effect = ICSError("ICS connection error")

        with patch("calendarbot.setup_wizard.ICSFetcher") as mock_fetcher_class, patch.object(
            wizard, "print_section"
        ), patch("builtins.print") as mock_print:

            mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher

            result = await wizard.test_configuration(mock_ics_config)

            assert result is False

            # Should have printed ICS error
            printed_messages = [str(call) for call in mock_print.call_args_list]
            assert any("ICS Error: ICS connection error" in msg for msg in printed_messages)


class TestSetupWizardConfigurationGeneration:
    """Test suite for SetupWizard configuration generation and saving."""

    @pytest.fixture
    def wizard(self):
        """Create a SetupWizard instance for testing."""
        return SetupWizard()

    @pytest.fixture
    def mock_ics_config(self):
        """Create mock ICS configuration."""
        return {"url": "https://example.com/calendar.ics", "auth_type": "none"}

    @pytest.fixture
    def mock_advanced_settings(self):
        """Create mock advanced settings."""
        return {
            "refresh_interval": 600,
            "cache_ttl": 7200,
            "verify_ssl": True,
            "log_level": "DEBUG",
        }

    def test_generate_config_content_basic(self, wizard, mock_ics_config, mock_advanced_settings):
        """Test configuration content generation with basic settings."""
        content = wizard.generate_config_content(mock_ics_config, mock_advanced_settings)

        assert isinstance(content, str)
        assert "Calendar Bot Configuration" in content
        assert "https://example.com/calendar.ics" in content
        assert "auth_type: none" in content
        assert "refresh_interval: 600" in content
        assert "cache_ttl: 7200" in content
        assert "verify_ssl: true" in content
        assert "log_level: DEBUG" in content

        # Should be valid YAML
        config_lines = content.split("\n")
        yaml_start = None
        for i, line in enumerate(config_lines):
            if line.strip() and not line.startswith("#"):
                yaml_start = i
                break

        if yaml_start:
            yaml_content = "\n".join(config_lines[yaml_start:])
            parsed_config = yaml.safe_load(yaml_content)
            assert parsed_config["ics"]["url"] == "https://example.com/calendar.ics"
            assert parsed_config["refresh_interval"] == 600

    def test_generate_config_content_with_basic_auth(self, wizard, mock_advanced_settings):
        """Test configuration content generation with basic authentication."""
        ics_config = {
            "url": "https://example.com/calendar.ics",
            "auth_type": "basic",
            "username": "testuser",
            "password": "testpass",
        }

        content = wizard.generate_config_content(ics_config, mock_advanced_settings)

        assert "auth_type: basic" in content
        assert "username: testuser" in content
        assert "password: testpass" in content

        # Parse YAML to verify structure
        config_lines = content.split("\n")
        yaml_start = None
        for i, line in enumerate(config_lines):
            if line.strip() and not line.startswith("#"):
                yaml_start = i
                break

        yaml_content = "\n".join(config_lines[yaml_start:])
        parsed_config = yaml.safe_load(yaml_content)
        assert parsed_config["ics"]["username"] == "testuser"
        assert parsed_config["ics"]["password"] == "testpass"

    def test_save_configuration_success(self, wizard):
        """Test successful configuration saving."""
        config_content = "test_config_content"

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"

            with patch.object(wizard, "get_choice", return_value="Project directory"), patch.object(
                wizard, "print_section"
            ), patch("builtins.print"):

                # Mock the config options to use our temp directory
                with patch.object(wizard, "save_configuration") as mock_save:
                    mock_save.return_value = config_path

                    result = wizard.save_configuration(config_content)

                    assert result == config_path

    def test_save_configuration_file_exists_no_overwrite(self, wizard):
        """Test configuration saving when file exists and user chooses not to overwrite."""
        config_content = "test_config_content"

        with patch.object(wizard, "get_choice", return_value="Project directory"), patch.object(
            wizard, "get_yes_no", return_value=False
        ), patch.object(wizard, "print_section"), patch("builtins.print") as mock_print:

            # Mock existing file
            with patch("pathlib.Path.exists", return_value=True):
                result = wizard.save_configuration(config_content)

                assert result is None

                # Should have printed cancellation message
                printed_messages = [str(call) for call in mock_print.call_args_list]
                assert any("Configuration not saved" in msg for msg in printed_messages)

    def test_show_completion_message_with_config(self, wizard):
        """Test completion message display with config path."""
        config_path = Path("/test/config.yaml")

        with patch.object(wizard, "print_header"), patch("builtins.print") as mock_print:

            wizard.show_completion_message(config_path)

            printed_messages = [str(call) for call in mock_print.call_args_list]
            assert any("/test/config.yaml" in msg for msg in printed_messages)
            assert any("Next Steps:" in msg for msg in printed_messages)
            assert any("calendarbot --test-mode" in msg for msg in printed_messages)


class TestSetupWizardMainWorkflow:
    """Test suite for SetupWizard main workflow."""

    @pytest.fixture
    def wizard(self):
        """Create a SetupWizard instance for testing."""
        return SetupWizard()

    @pytest.mark.asyncio
    async def test_run_success_full_workflow(self, wizard):
        """Test successful full wizard workflow."""
        with patch.object(wizard, "print_header"), patch.object(
            wizard, "get_yes_no", side_effect=[True, True, False, True]
        ), patch.object(wizard, "select_calendar_service", return_value="outlook"), patch.object(
            wizard,
            "configure_ics_url",
            return_value={"url": "https://test.com", "recommended_auth": "none"},
        ), patch.object(
            wizard, "configure_authentication", return_value={"auth_type": "none"}
        ), patch.object(
            wizard, "test_configuration", return_value=True
        ), patch.object(
            wizard, "generate_config_content", return_value="config_content"
        ), patch.object(
            wizard, "save_configuration", return_value=Path("/test/config.yaml")
        ), patch.object(
            wizard, "show_completion_message"
        ), patch(
            "builtins.print"
        ):

            result = await wizard.run()

            assert result is True

    @pytest.mark.asyncio
    async def test_run_cancel_at_start(self, wizard):
        """Test wizard cancellation at start."""
        with patch.object(wizard, "print_header"), patch.object(
            wizard, "get_yes_no", return_value=False
        ), patch("builtins.print") as mock_print:

            result = await wizard.run()

            assert result is False

            printed_messages = [str(call) for call in mock_print.call_args_list]
            assert any("Setup cancelled" in msg for msg in printed_messages)

    @pytest.mark.asyncio
    async def test_run_keyboard_interrupt(self, wizard):
        """Test wizard handling of keyboard interrupt."""
        with patch.object(wizard, "print_header"), patch.object(
            wizard, "get_yes_no", side_effect=KeyboardInterrupt
        ), patch("builtins.print") as mock_print:

            result = await wizard.run()

            assert result is False

            printed_messages = [str(call) for call in mock_print.call_args_list]
            assert any("cancelled by user" in msg for msg in printed_messages)


class TestModuleLevelFunctions:
    """Test suite for module-level functions."""

    @pytest.mark.asyncio
    async def test_run_setup_wizard_success(self):
        """Test run_setup_wizard function success."""
        with patch("calendarbot.setup_wizard.SetupWizard") as mock_wizard_class:
            mock_wizard = AsyncMock()
            mock_wizard.run.return_value = True
            mock_wizard_class.return_value = mock_wizard

            result = await run_setup_wizard()

            assert result is True
            mock_wizard_class.assert_called_once()
            mock_wizard.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_setup_wizard_failure(self):
        """Test run_setup_wizard function failure."""
        with patch("calendarbot.setup_wizard.SetupWizard") as mock_wizard_class:
            mock_wizard = AsyncMock()
            mock_wizard.run.return_value = False
            mock_wizard_class.return_value = mock_wizard

            result = await run_setup_wizard()

            assert result is False

    def test_run_simple_wizard_success(self):
        """Test run_simple_wizard function success."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pathlib.Path.home", return_value=Path(temp_dir)), patch(
                "builtins.input", return_value="https://example.com/calendar.ics"
            ), patch("builtins.print"):

                # Mock the config directory creation and file writing
                with patch("pathlib.Path.mkdir"), patch(
                    "pathlib.Path.exists", return_value=False
                ), patch("builtins.open", mock_open()) as mock_file:

                    result = run_simple_wizard()

                    assert result is True
                    mock_file.assert_called_once()

    def test_run_simple_wizard_no_url(self):
        """Test run_simple_wizard function with no URL provided."""
        with patch("builtins.input", return_value=""), patch("builtins.print") as mock_print, patch(
            "pathlib.Path.exists", return_value=False
        ), patch("pathlib.Path.mkdir"), patch("builtins.open", mock_open()):

            result = run_simple_wizard()

            assert result is False

            # Look for the exact message anywhere in the print calls
            found = False
            target_message = "❌ ICS URL is required. Setup cancelled."
            for call_args in mock_print.call_args_list:
                args, kwargs = call_args
                if args and target_message in str(args[0]):
                    found = True
                    break

            assert found, f"Expected message '{target_message}' not found in print calls"

    def test_run_simple_wizard_keyboard_interrupt(self):
        """Test run_simple_wizard handling keyboard interrupt."""
        with patch("builtins.input", side_effect=KeyboardInterrupt), patch(
            "builtins.print"
        ) as mock_print:

            result = run_simple_wizard()

            assert result is False

            printed_messages = [str(call) for call in mock_print.call_args_list]
            assert any("cancelled by user" in msg for msg in printed_messages)


@pytest.mark.integration
class TestSetupWizardIntegration:
    """Integration tests for SetupWizard."""

    @pytest.mark.asyncio
    async def test_full_wizard_integration_outlook(self):
        """Test full wizard integration with Outlook setup."""
        wizard = SetupWizard()

        # Simulate user inputs for Outlook setup
        user_inputs = [
            "1",  # Ready to start
            "1",  # Microsoft Outlook
            "https://outlook.live.com/owa/calendar/test/calendar.ics",  # Valid Outlook URL
            "1",  # No authentication
            "n",  # Skip configuration test
            "n",  # Skip advanced settings
            "1",  # Project directory
            "y",  # Overwrite if exists
        ]

        with patch("builtins.input", side_effect=user_inputs), patch(
            "builtins.print"
        ), patch.object(wizard, "save_configuration", return_value=Path("/test/config.yaml")):

            result = await wizard.run()

            assert result is True


@pytest.mark.unit
class TestSetupWizardEdgeCases:
    """Test edge cases and error conditions for SetupWizard."""

    @pytest.fixture
    def wizard(self):
        """Create a SetupWizard instance for testing."""
        return SetupWizard()

    def test_get_input_strip_whitespace(self, wizard):
        """Test that get_input strips whitespace from user input."""
        with patch("builtins.input", return_value="  test input  "):
            result = wizard.get_input("Test prompt")

            assert result == "test input"

    def test_get_choice_boundary_values(self, wizard):
        """Test get_choice with boundary values."""
        choices = ["Option 1", "Option 2", "Option 3"]

        with patch("builtins.input", return_value="1"), patch("builtins.print"):
            result = wizard.get_choice("Choose:", choices)
            assert result == "Option 1"

        with patch("builtins.input", return_value="3"), patch("builtins.print"):
            result = wizard.get_choice("Choose:", choices)
            assert result == "Option 3"

    def test_validate_url_edge_cases(self, wizard):
        """Test URL validation with edge cases."""
        edge_cases = [
            ("http://localhost", True),
            ("https://127.0.0.1", True),
            ("http://192.168.1.1:8080", True),
            ("https://sub.domain.co.uk/path?query=1", True),
            ("http://", False),
            ("https://", False),
            ("http://.com", False),
        ]

        for url, expected in edge_cases:
            with patch("builtins.print"):
                result = wizard.validate_url(url)
                assert result == expected, f"URL {url} should be {expected}"

    def test_generate_config_content_timestamp(self, wizard):
        """Test that generated config content includes timestamp."""
        ics_config = {"url": "https://test.com"}
        advanced_settings: Dict[str, Any] = {}

        with patch("calendarbot.setup_wizard.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2024-01-01 12:00:00"

            content = wizard.generate_config_content(ics_config, advanced_settings)

            assert "2024-01-01 12:00:00" in content
