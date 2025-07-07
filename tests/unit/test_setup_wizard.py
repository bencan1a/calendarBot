"""Unit tests for calendarbot.setup_wizard module."""

import asyncio
import tempfile
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, mock_open, patch

import pytest
import yaml

from calendarbot.ics.exceptions import ICSError
from calendarbot.ics.models import ICSAuth, ICSSource
from calendarbot.setup_wizard import (
    CalendarServiceTemplate,
    SetupWizard,
    run_setup_wizard,
    run_simple_wizard,
)


class TestCalendarServiceTemplate:
    """Test CalendarServiceTemplate class functionality."""

    def test_calendar_service_template_initialization(self):
        """Test CalendarServiceTemplate initialization with all parameters."""
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

    def test_calendar_service_template_default_values(self):
        """Test CalendarServiceTemplate with default values."""
        template = CalendarServiceTemplate(
            name="Test Service", description="Test description", url_pattern=r"https://test\.com/.*"
        )

        assert template.auth_type == "none"
        assert template.instructions == ""


class TestSetupWizard:
    """Test SetupWizard class functionality."""

    @pytest.fixture
    def wizard(self):
        """Create a SetupWizard instance for testing."""
        return SetupWizard()

    @pytest.fixture
    def mock_input(self):
        """Mock input function for testing user interactions."""
        with patch("builtins.input") as mock:
            yield mock

    @pytest.fixture
    def mock_print(self):
        """Mock print function for testing output."""
        with patch("builtins.print") as mock:
            yield mock

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

    def test_print_header(self, wizard, mock_print):
        """Test print_header method."""
        wizard.print_header("Test Title")

        assert mock_print.call_count == 3
        calls = [call.args[0] for call in mock_print.call_args_list]
        assert "=" in calls[0]
        assert "📅 Test Title" in calls[1]
        assert "=" in calls[2]

    def test_print_section(self, wizard, mock_print):
        """Test print_section method."""
        wizard.print_section("Test Section")

        assert mock_print.call_count == 2
        calls = [call.args[0] for call in mock_print.call_args_list]
        assert "🔧 Test Section" in calls[0]
        assert "-" in calls[1]

    def test_get_input_with_default(self, wizard, mock_input):
        """Test get_input method with default value."""
        mock_input.return_value = ""
        result = wizard.get_input("Test prompt", default="default_value")

        assert result == "default_value"
        mock_input.assert_called_once_with("Test prompt [default_value]: ")

    def test_get_input_with_user_response(self, wizard, mock_input):
        """Test get_input method with user response."""
        mock_input.return_value = "user_input"
        result = wizard.get_input("Test prompt")

        assert result == "user_input"

    def test_get_input_required_validation(self, wizard, mock_input, mock_print):
        """Test get_input method with required field validation."""
        # Ensure we don't fall back to empty strings after side_effect is exhausted
        mock_input.side_effect = ["", "valid_input", StopIteration()]

        result = wizard.get_input("Test prompt", required=True)

        assert result == "valid_input"
        assert mock_input.call_count == 2
        mock_print.assert_called_with("❌ This field is required. Please enter a value.")

    def test_get_input_with_validation_function(self, wizard, mock_input, mock_print):
        """Test get_input method with validation function."""

        def validate_func(value):
            return value == "valid"

        # Prevent infinite loop by adding StopIteration after exhausting side_effect
        mock_input.side_effect = ["invalid", "valid", StopIteration()]

        result = wizard.get_input("Test prompt", validate_func=validate_func)

        assert result == "valid"
        assert mock_input.call_count == 2

    def test_get_input_validation_function_exception(self, wizard, mock_input, mock_print):
        """Test get_input method when validation function raises exception."""

        def validate_func(value):
            if value == "error":
                raise ValueError("Test validation error")
            return value == "valid"

        # Prevent infinite loop by adding StopIteration after exhausting side_effect
        mock_input.side_effect = ["error", "valid", StopIteration()]

        result = wizard.get_input("Test prompt", validate_func=validate_func)

        assert result == "valid"
        assert mock_input.call_count == 2
        mock_print.assert_called_with("❌ Validation error: Test validation error")

    def test_get_input_not_required_empty_response(self, wizard, mock_input):
        """Test get_input method with non-required field and empty response."""
        mock_input.return_value = ""

        result = wizard.get_input("Test prompt", required=False)

        assert result == ""

    def test_get_choice_valid_selection(self, wizard, mock_input, mock_print):
        """Test get_choice method with valid selection."""
        mock_input.return_value = "2"
        choices = ["Option 1", "Option 2", "Option 3"]
        descriptions = ["Desc 1", "Desc 2", "Desc 3"]

        result = wizard.get_choice("Choose option", choices, descriptions)

        assert result == "Option 2"

    def test_get_choice_invalid_then_valid(self, wizard, mock_input, mock_print):
        """Test get_choice method with invalid then valid selection."""
        # Prevent infinite loop by adding StopIteration after exhausting side_effect
        mock_input.side_effect = ["invalid", "0", "4", "2", StopIteration()]
        choices = ["Option 1", "Option 2", "Option 3"]

        result = wizard.get_choice("Choose option", choices)

        assert result == "Option 2"
        assert mock_input.call_count == 4

    @pytest.mark.parametrize(
        "input_value,default,expected",
        [
            ("y", False, True),
            ("yes", False, True),
            ("n", True, False),
            ("no", True, False),
            ("", True, True),
            ("", False, False),
        ],
    )
    def test_get_yes_no(self, wizard, mock_input, input_value, default, expected):
        """Test get_yes_no method with various inputs."""
        mock_input.return_value = input_value

        result = wizard.get_yes_no("Test prompt", default=default)

        assert result == expected

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://example.com", True),
            ("http://localhost:8080", True),
            ("https://test.com/path?query=1", True),
            ("ftp://invalid.com", False),
            ("not-a-url", False),
            ("", False),
        ],
    )
    def test_validate_url(self, wizard, mock_print, url, expected):
        """Test validate_url method with various URL formats."""
        result = wizard.validate_url(url)
        assert result == expected

    def test_select_calendar_service(self, wizard, mock_input, mock_print):
        """Test select_calendar_service method."""
        mock_input.return_value = "1"  # Select first option (Outlook)

        result = wizard.select_calendar_service()

        assert result == "outlook"

    def test_select_calendar_service_fallback(self, wizard, mock_input, mock_print):
        """Test select_calendar_service method fallback to custom."""
        mock_input.return_value = "1"  # Select first option

        # Mock get_choice to return a service name that doesn't exist in templates
        with patch.object(wizard, "get_choice", return_value="Non-existent Service"):
            result = wizard.select_calendar_service()
            assert result == "custom"

    def test_configure_ics_url_valid(self, wizard, mock_input, mock_print):
        """Test configure_ics_url method with valid URL."""
        mock_input.return_value = "https://outlook.live.com/owa/calendar/test/calendar.ics"

        result = wizard.configure_ics_url("outlook")

        assert result["url"] == "https://outlook.live.com/owa/calendar/test/calendar.ics"
        assert result["recommended_auth"] == "none"

    def test_configure_ics_url_pattern_mismatch(self, wizard, mock_input, mock_print):
        """Test configure_ics_url method with URL pattern mismatch."""
        mock_input.side_effect = [
            "https://wrong-pattern.com/test.ics",  # URL that doesn't match pattern
            "n",  # Don't continue with this URL
            "https://outlook.live.com/owa/calendar/test/calendar.ics",  # Correct URL
            StopIteration(),  # Prevent infinite loop
        ]

        result = wizard.configure_ics_url("outlook")

        assert "outlook.live.com" in result["url"]

    def test_configure_authentication_none(self, wizard, mock_input):
        """Test configure_authentication method with no auth."""
        mock_input.return_value = "1"  # Select "none"

        result = wizard.configure_authentication()

        assert result["auth_type"] == "none"

    @patch("calendarbot.setup_wizard.SecurityEventLogger")
    def test_configure_authentication_basic(
        self, mock_security_logger, wizard, mock_input, mock_print
    ):
        """Test configure_authentication method with basic auth."""
        mock_input.side_effect = [
            "2",
            "testuser",
            "testpass",
            StopIteration(),
        ]  # Select basic, username, password
        mock_logger_instance = Mock()
        mock_security_logger.return_value = mock_logger_instance

        result = wizard.configure_authentication()

        assert result["auth_type"] == "basic"
        assert result["username"] == "testuser"
        assert result["password"] == "testpass"
        mock_logger_instance.log_authentication_success.assert_called_once()

    @patch("calendarbot.setup_wizard.SecurityEventLogger")
    def test_configure_authentication_bearer(
        self, mock_security_logger, wizard, mock_input, mock_print
    ):
        """Test configure_authentication method with bearer token."""
        mock_input.side_effect = ["3", "test_token", StopIteration()]  # Select bearer, token
        mock_logger_instance = Mock()
        mock_security_logger.return_value = mock_logger_instance

        result = wizard.configure_authentication()

        assert result["auth_type"] == "bearer"
        assert result["token"] == "test_token"
        mock_logger_instance.log_authentication_success.assert_called_once()

    def test_configure_authentication_with_recommendation(self, wizard, mock_input, mock_print):
        """Test configure_authentication method with recommended auth type."""
        mock_input.return_value = "2"  # Select basic auth

        wizard.configure_authentication(recommended_auth="basic")

        # Check that recommendation was displayed
        print_calls = [call.args[0] for call in mock_print.call_args_list]
        assert any("Recommended for your service: basic" in call for call in print_calls)

    def test_configure_advanced_settings_defaults(self, wizard, mock_input):
        """Test configure_advanced_settings method with default values."""
        mock_input.side_effect = [
            "",
            "",
            "y",
            "2",
            StopIteration(),
        ]  # Use defaults for intervals, yes for SSL, INFO level

        result = wizard.configure_advanced_settings()

        assert "refresh_interval" not in result or result["refresh_interval"] == 300
        assert "cache_ttl" not in result or result["cache_ttl"] == 3600
        assert result["verify_ssl"] == True
        assert result["log_level"] == "INFO"

    def test_configure_advanced_settings_custom(self, wizard, mock_input, mock_print):
        """Test configure_advanced_settings method with custom values."""
        mock_input.side_effect = ["600", "7200", "n", "1", StopIteration()]  # Custom values

        result = wizard.configure_advanced_settings()

        assert result["refresh_interval"] == 600
        assert result["cache_ttl"] == 7200
        assert result["verify_ssl"] == False
        assert result["log_level"] == "DEBUG"

    def test_configure_advanced_settings_invalid_numbers(self, wizard, mock_input, mock_print):
        """Test configure_advanced_settings method with invalid number inputs."""
        mock_input.side_effect = ["invalid", "also_invalid", "y", "1", StopIteration()]

        result = wizard.configure_advanced_settings()

        assert result["refresh_interval"] == 300  # Default fallback
        assert result["cache_ttl"] == 3600  # Default fallback

    @pytest.mark.asyncio
    async def test_test_configuration_success(self, wizard, mock_print):
        """Test test_configuration method with successful connection."""
        ics_config = {
            "url": "https://test.com/calendar.ics",
            "auth_type": "none",
            "verify_ssl": True,
        }

        mock_fetcher = AsyncMock()
        mock_fetcher.test_connection.return_value = True

        mock_response = Mock()
        mock_response.success = True
        mock_response.content = "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR"
        mock_fetcher.fetch_ics.return_value = mock_response

        # Mock all dependencies to avoid import and instantiation issues
        with patch("calendarbot.setup_wizard.CalendarBotSettings") as mock_settings_class:
            mock_settings_class.return_value = Mock()

            with patch("calendarbot.setup_wizard.ICSAuth") as mock_auth_class:
                mock_auth_class.return_value = Mock()

                with patch("calendarbot.setup_wizard.ICSSource") as mock_source_class:
                    mock_source_class.return_value = Mock()

                    with patch("calendarbot.setup_wizard.ICSFetcher") as mock_fetcher_class:
                        mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher

                        result = await wizard.test_configuration(ics_config)

                        assert result == True

    @pytest.mark.asyncio
    async def test_test_configuration_connection_failure(self, wizard, mock_print):
        """Test test_configuration method with connection failure."""
        ics_config = {"url": "https://test.com/calendar.ics", "auth_type": "none"}

        mock_fetcher = AsyncMock()
        mock_fetcher.test_connection.return_value = False

        with patch("calendarbot.setup_wizard.ICSFetcher") as mock_fetcher_class:
            mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher

            result = await wizard.test_configuration(ics_config)

            assert result == False

    @pytest.mark.asyncio
    async def test_test_configuration_ics_error(self, wizard, mock_print):
        """Test test_configuration method with ICS error."""
        ics_config = {"url": "https://test.com/calendar.ics", "auth_type": "none"}

        with patch("calendarbot.setup_wizard.ICSFetcher") as mock_fetcher_class:
            mock_fetcher_class.side_effect = ICSError("Test ICS error")

            result = await wizard.test_configuration(ics_config)

            assert result == False

    @pytest.mark.asyncio
    async def test_test_configuration_basic_auth(self, wizard, mock_print):
        """Test test_configuration method with basic authentication."""
        ics_config = {
            "url": "https://test.com/calendar.ics",
            "auth_type": "basic",
            "username": "testuser",
            "password": "testpass",
            "verify_ssl": True,
        }

        mock_fetcher = AsyncMock()
        mock_fetcher.test_connection.return_value = True

        mock_response = Mock()
        mock_response.success = True
        mock_response.content = "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR"
        mock_fetcher.fetch_ics.return_value = mock_response

        with patch("calendarbot.setup_wizard.CalendarBotSettings") as mock_settings_class:
            mock_settings_class.return_value = Mock()
            with patch("calendarbot.setup_wizard.ICSAuth") as mock_auth_class:
                mock_auth_class.return_value = Mock()
                with patch("calendarbot.setup_wizard.ICSSource") as mock_source_class:
                    mock_source_class.return_value = Mock()
                    with patch("calendarbot.setup_wizard.ICSFetcher") as mock_fetcher_class:
                        mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher

                        result = await wizard.test_configuration(ics_config)

                        assert result == True

    @pytest.mark.asyncio
    async def test_test_configuration_bearer_auth(self, wizard, mock_print):
        """Test test_configuration method with bearer token authentication."""
        ics_config = {
            "url": "https://test.com/calendar.ics",
            "auth_type": "bearer",
            "token": "test_token",
        }

        mock_fetcher = AsyncMock()
        mock_fetcher.test_connection.return_value = True

        mock_response = Mock()
        mock_response.success = True
        mock_response.content = "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR"
        mock_fetcher.fetch_ics.return_value = mock_response

        with patch("calendarbot.setup_wizard.CalendarBotSettings") as mock_settings_class:
            mock_settings_class.return_value = Mock()
            with patch("calendarbot.setup_wizard.ICSAuth") as mock_auth_class:
                mock_auth_class.return_value = Mock()
                with patch("calendarbot.setup_wizard.ICSSource") as mock_source_class:
                    mock_source_class.return_value = Mock()
                    with patch("calendarbot.setup_wizard.ICSFetcher") as mock_fetcher_class:
                        mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher

                        result = await wizard.test_configuration(ics_config)

                        assert result == True

    @pytest.mark.asyncio
    async def test_test_configuration_invalid_content(self, wizard, mock_print):
        """Test test_configuration method with invalid ICS content."""
        ics_config = {"url": "https://test.com/calendar.ics", "auth_type": "none"}

        mock_fetcher = AsyncMock()
        mock_fetcher.test_connection.return_value = True

        mock_response = Mock()
        mock_response.success = True
        mock_response.content = "INVALID CONTENT"  # Not valid ICS format
        mock_fetcher.fetch_ics.return_value = mock_response

        with patch("calendarbot.setup_wizard.CalendarBotSettings") as mock_settings_class:
            mock_settings_class.return_value = Mock()
            with patch("calendarbot.setup_wizard.ICSAuth") as mock_auth_class:
                mock_auth_class.return_value = Mock()
                with patch("calendarbot.setup_wizard.ICSSource") as mock_source_class:
                    mock_source_class.return_value = Mock()
                    with patch("calendarbot.setup_wizard.ICSFetcher") as mock_fetcher_class:
                        mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher

                        result = await wizard.test_configuration(ics_config)

                        assert result == True  # Should still succeed, just warn about content

    @pytest.mark.asyncio
    async def test_test_configuration_fetch_failure(self, wizard, mock_print):
        """Test test_configuration method with fetch failure."""
        ics_config = {"url": "https://test.com/calendar.ics", "auth_type": "none"}

        mock_fetcher = AsyncMock()
        mock_fetcher.test_connection.return_value = True

        mock_response = Mock()
        mock_response.success = False
        mock_response.error_message = "Network error"
        mock_fetcher.fetch_ics.return_value = mock_response

        with patch("calendarbot.setup_wizard.CalendarBotSettings") as mock_settings_class:
            mock_settings_class.return_value = Mock()
            with patch("calendarbot.setup_wizard.ICSAuth") as mock_auth_class:
                mock_auth_class.return_value = Mock()
                with patch("calendarbot.setup_wizard.ICSSource") as mock_source_class:
                    mock_source_class.return_value = Mock()
                    with patch("calendarbot.setup_wizard.ICSFetcher") as mock_fetcher_class:
                        mock_fetcher_class.return_value.__aenter__.return_value = mock_fetcher

                        result = await wizard.test_configuration(ics_config)

                        assert result == False

    @pytest.mark.asyncio
    async def test_test_configuration_unexpected_exception(self, wizard, mock_print):
        """Test test_configuration method with unexpected exception."""
        ics_config = {"url": "https://test.com/calendar.ics", "auth_type": "none"}

        with patch("calendarbot.setup_wizard.ICSFetcher") as mock_fetcher_class:
            mock_fetcher_class.side_effect = Exception("Unexpected error")

            result = await wizard.test_configuration(ics_config)

            assert result == False

    def test_generate_config_content_basic(self, wizard):
        """Test generate_config_content method with basic configuration."""
        ics_config = {"url": "https://test.com/calendar.ics", "auth_type": "none"}
        advanced_settings = {"refresh_interval": 300, "verify_ssl": True, "log_level": "INFO"}

        result = wizard.generate_config_content(ics_config, advanced_settings)

        assert isinstance(result, str)
        # YAML may not quote simple URLs, so check for the URL without quotes
        assert "url: https://test.com/calendar.ics" in result
        assert "auth_type: none" in result
        assert "refresh_interval: 300" in result

    def test_generate_config_content_with_auth(self, wizard):
        """Test generate_config_content method with authentication."""
        ics_config = {
            "url": "https://test.com/calendar.ics",
            "auth_type": "basic",
            "username": "testuser",
            "password": "testpass",
        }
        advanced_settings = {}

        result = wizard.generate_config_content(ics_config, advanced_settings)

        assert "username: testuser" in result
        assert "password: testpass" in result

    def test_generate_config_content_with_bearer_token(self, wizard):
        """Test generate_config_content method with bearer token authentication."""
        ics_config = {
            "url": "https://test.com/calendar.ics",
            "auth_type": "bearer",
            "token": "bearer_test_token",
        }
        advanced_settings = {}

        result = wizard.generate_config_content(ics_config, advanced_settings)

        assert "token: bearer_test_token" in result
        assert "auth_type: bearer" in result

    @patch("builtins.open", new_callable=mock_open)
    def test_save_configuration_success(self, mock_file, wizard, mock_input, mock_print):
        """Test save_configuration method with successful save."""
        mock_input.return_value = "1"  # Select first option
        config_content = "test: config"

        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir"):
                result = wizard.save_configuration(config_content)

                assert result is not None
                mock_file.assert_called_once()

    def test_save_configuration_file_exists_overwrite(self, wizard, mock_input, mock_print):
        """Test save_configuration method when file exists and user chooses to overwrite."""
        mock_input.side_effect = ["1", "y", StopIteration()]  # Select location, yes to overwrite
        config_content = "test: config"

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", mock_open()) as mock_file:
                    result = wizard.save_configuration(config_content)

                    assert result is not None

    def test_save_configuration_file_exists_no_overwrite(self, wizard, mock_input, mock_print):
        """Test save_configuration method when file exists and user declines overwrite."""
        mock_input.side_effect = ["1", "n", StopIteration()]  # Select location, no to overwrite
        config_content = "test: config"

        with patch("pathlib.Path.exists", return_value=True):
            result = wizard.save_configuration(config_content)

            assert result is None

    def test_save_configuration_write_error(self, wizard, mock_input, mock_print):
        """Test save_configuration method with file write error."""
        mock_input.return_value = "1"  # Select first option
        config_content = "test: config"

        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", side_effect=IOError("Permission denied")):
                    result = wizard.save_configuration(config_content)

                    assert result is None
                    # Verify error message was printed
                    print_calls = [call.args[0] for call in mock_print.call_args_list]
                    assert any("Failed to save configuration" in call for call in print_calls)

    def test_save_configuration_fallback_path(self, wizard, mock_input, mock_print):
        """Test save_configuration method with fallback to default path."""
        mock_input.return_value = "1"  # Select first option
        config_content = "test: config"

        # Mock to simulate not finding the selected choice (edge case)
        with patch.object(wizard, "get_choice", return_value="Non-existent choice"):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("pathlib.Path.mkdir"):
                    with patch("builtins.open", mock_open()) as mock_file:
                        result = wizard.save_configuration(config_content)

                        assert result is not None  # Should use fallback path

    def test_show_completion_message(self, wizard, mock_print):
        """Test show_completion_message method."""
        config_path = Path("/test/config.yaml")

        wizard.show_completion_message(config_path)

        # Verify that print was called multiple times with completion information
        assert mock_print.call_count > 5
        calls = [call.args[0] for call in mock_print.call_args_list]
        assert any("Setup Complete" in call for call in calls)
        assert any("Next Steps" in call for call in calls)

    def test_show_completion_message_no_config_path(self, wizard, mock_print):
        """Test show_completion_message method when config path is None."""
        wizard.show_completion_message(None)

        # Verify that warning message is displayed
        calls = [call.args[0] for call in mock_print.call_args_list]
        assert any("Configuration file could not be saved" in call for call in calls)

    @pytest.mark.asyncio
    async def test_run_full_wizard_success(self, wizard, mock_input, mock_print):
        """Test complete wizard run with successful configuration."""
        # Mock all user inputs for a complete run
        mock_input.side_effect = [
            "y",  # Ready to start
            "1",  # Select Outlook
            "https://outlook.live.com/owa/calendar/test/calendar.ics",  # ICS URL
            "1",  # No auth
            "n",  # Skip configuration test
            "n",  # Skip advanced settings
            "1",  # Save to project directory
            StopIteration(),  # Prevent infinite loop
        ]

        # Mock successful file operations
        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", mock_open()):
                    result = await wizard.run()

                    assert result == True

    @pytest.mark.asyncio
    async def test_run_wizard_cancelled_at_start(self, wizard, mock_input, mock_print):
        """Test wizard run when user cancels at the beginning."""
        mock_input.return_value = "n"  # Not ready to start

        result = await wizard.run()

        assert result == False

    @pytest.mark.asyncio
    async def test_run_wizard_keyboard_interrupt(self, wizard, mock_input, mock_print):
        """Test wizard run with keyboard interrupt."""
        mock_input.side_effect = KeyboardInterrupt()

        result = await wizard.run()

        assert result == False

    @pytest.mark.asyncio
    async def test_run_wizard_exception(self, wizard, mock_input, mock_print):
        """Test wizard run with unexpected exception."""
        mock_input.side_effect = Exception("Test error")

        result = await wizard.run()

        assert result == False

    @pytest.mark.asyncio
    async def test_run_wizard_test_failure_continue(self, wizard, mock_input, mock_print):
        """Test wizard run when test fails but user continues anyway."""
        mock_input.side_effect = [
            "y",  # Ready to start
            "1",  # Select Outlook
            "https://outlook.live.com/owa/calendar/test/calendar.ics",  # ICS URL
            "1",  # No auth
            "y",  # Test configuration
            "y",  # Continue anyway after test failure
            "n",  # Skip advanced settings
            "1",  # Save to project directory
            StopIteration(),  # Prevent infinite loop
        ]

        # Mock test failure
        with patch.object(wizard, "test_configuration", return_value=False):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("pathlib.Path.mkdir"):
                    with patch("builtins.open", mock_open()):
                        result = await wizard.run()

                        assert result == True

    @pytest.mark.asyncio
    async def test_run_wizard_test_failure_no_continue(self, wizard, mock_input, mock_print):
        """Test wizard run when test fails and user doesn't continue."""
        mock_input.side_effect = [
            "y",  # Ready to start
            "1",  # Select Outlook
            "https://outlook.live.com/owa/calendar/test/calendar.ics",  # ICS URL
            "1",  # No auth
            "y",  # Test configuration
            "n",  # Don't continue after test failure
            StopIteration(),  # Prevent infinite loop
        ]

        # Mock test failure
        with patch.object(wizard, "test_configuration", return_value=False):
            result = await wizard.run()

            assert result == False

    @pytest.mark.asyncio
    async def test_run_wizard_with_advanced_settings(self, wizard, mock_input, mock_print):
        """Test wizard run with advanced settings configuration."""
        mock_input.side_effect = [
            "y",  # Ready to start
            "1",  # Select Outlook
            "https://outlook.live.com/owa/calendar/test/calendar.ics",  # ICS URL
            "1",  # No auth
            "n",  # Skip configuration test
            "y",  # Configure advanced settings
            "600",  # Custom refresh interval
            "7200",  # Custom cache TTL
            "n",  # Don't verify SSL
            "1",  # DEBUG log level
            "1",  # Save to project directory
            StopIteration(),  # Prevent infinite loop
        ]

        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", mock_open()):
                    result = await wizard.run()

                    assert result == True

    @pytest.mark.asyncio
    async def test_run_wizard_config_save_failure(self, wizard, mock_input, mock_print):
        """Test wizard run when configuration save fails."""
        mock_input.side_effect = [
            "y",  # Ready to start
            "1",  # Select Outlook
            "https://outlook.live.com/owa/calendar/test/calendar.ics",  # ICS URL
            "1",  # No auth
            "n",  # Skip configuration test
            "n",  # Skip advanced settings
            "1",  # Save to project directory
            StopIteration(),  # Prevent infinite loop
        ]

        # Mock save failure
        with patch.object(wizard, "save_configuration", return_value=None):
            result = await wizard.run()

            assert result == False


class TestSetupWizardFunctions:
    """Test module-level functions."""

    @pytest.mark.asyncio
    @patch("calendarbot.setup_wizard.SetupWizard")
    async def test_run_setup_wizard(self, mock_wizard_class):
        """Test run_setup_wizard function."""
        mock_wizard = Mock()
        mock_wizard.run = AsyncMock(return_value=True)
        mock_wizard_class.return_value = mock_wizard

        result = await run_setup_wizard()

        assert result == True
        mock_wizard_class.assert_called_once()
        mock_wizard.run.assert_called_once()

    @patch("builtins.input")
    @patch("builtins.print")
    def test_run_simple_wizard_success(self, mock_print, mock_input):
        """Test run_simple_wizard function with successful execution."""
        mock_input.return_value = "https://test.com/calendar.ics"

        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", mock_open()) as mock_file:
                    result = run_simple_wizard()

                    assert result == True
                    mock_file.assert_called_once()

    @patch("builtins.input")
    @patch("builtins.print")
    def test_run_simple_wizard_existing_config_overwrite(self, mock_print, mock_input):
        """Test run_simple_wizard with existing config file and overwrite."""
        mock_input.side_effect = ["y", "https://test.com/calendar.ics", StopIteration()]

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", mock_open()) as mock_file:
                    result = run_simple_wizard()

                    assert result == True

    @patch("builtins.input")
    @patch("builtins.print")
    def test_run_simple_wizard_existing_config_no_overwrite(self, mock_print, mock_input):
        """Test run_simple_wizard with existing config file and no overwrite."""
        mock_input.side_effect = ["n"]  # Don't overwrite

        with patch("pathlib.Path.exists", return_value=True):
            result = run_simple_wizard()

            assert result == False

    @patch("builtins.input")
    @patch("builtins.print")
    def test_run_simple_wizard_no_url(self, mock_print, mock_input):
        """Test run_simple_wizard with no URL provided."""
        mock_input.return_value = ""  # Empty URL

        result = run_simple_wizard()

        assert result == False

    @patch("builtins.input")
    @patch("builtins.print")
    def test_run_simple_wizard_keyboard_interrupt(self, mock_print, mock_input):
        """Test run_simple_wizard with keyboard interrupt."""
        mock_input.side_effect = KeyboardInterrupt()

        result = run_simple_wizard()

        assert result == False

    @patch("builtins.input")
    @patch("builtins.print")
    def test_run_simple_wizard_exception(self, mock_print, mock_input):
        """Test run_simple_wizard with unexpected exception."""
        mock_input.side_effect = Exception("Test error")

        result = run_simple_wizard()

        assert result == False

    @patch("builtins.input")
    @patch("builtins.print")
    def test_run_simple_wizard_url_warning(self, mock_print, mock_input):
        """Test run_simple_wizard with URL that doesn't start with http/https."""
        mock_input.return_value = "ftp://test.com/calendar.ics"  # Non-HTTP URL

        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", mock_open()) as mock_file:
                    result = run_simple_wizard()

                    assert result == True
                    # Verify warning was displayed
                    print_calls = [
                        call.args[0] if call.args else "" for call in mock_print.call_args_list
                    ]
                    assert any(
                        "Warning: URL should start with http://" in call for call in print_calls
                    )

    @patch("builtins.input")
    @patch("builtins.print")
    def test_run_simple_wizard_empty_url_validation(self, mock_print, mock_input):
        """Test run_simple_wizard empty URL validation."""
        mock_input.return_value = ""  # Empty URL

        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir"):
                result = run_simple_wizard()

                assert result == False
                # Verify error message was displayed
                print_calls = [
                    call.args[0] if call.args else "" for call in mock_print.call_args_list
                ]
                assert any(
                    "❌ ICS URL is required. Setup cancelled." in call for call in print_calls
                )
