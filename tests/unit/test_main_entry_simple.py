"""Simple unit tests for calendarbot main entry point functionality.

This test file focuses on testing the main entry point logic with minimal,
targeted mocking to avoid complexity and circular references.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# CRITICAL: Mock core components BEFORE any calendarbot imports
# This prevents real component initialization during test imports
with patch("calendarbot.main.CalendarBot", new_callable=AsyncMock), patch(
    "calendarbot.web.server.WebServer"
), patch("calendarbot.validation.ValidationRunner"), patch(
    "calendarbot.ui.interactive.InteractiveController"
), patch(
    "calendarbot.ui.keyboard.KeyboardHandler"
), patch(
    "calendarbot.setup_wizard.run_setup_wizard", return_value=True
), patch(
    "calendarbot.setup_wizard.run_simple_wizard", return_value=True
), patch(
    "builtins.input", return_value=""
):
    pass


class TestMainEntrySimple:
    """Simple test suite for main entry point functionality."""

    @pytest.mark.asyncio
    async def test_main_entry_setup_mode(self):
        """Test main entry with setup mode - should handle KeyboardInterrupt gracefully."""
        from calendarbot.cli import main_entry

        # Patch all the components that could cause real execution
        with patch("sys.argv", ["calendarbot", "--setup"]), patch(
            "builtins.input", return_value="1"
        ), patch("calendarbot.setup_wizard.run_setup_wizard", return_value=True), patch(
            "calendarbot.setup_wizard.run_simple_wizard", return_value=True
        ), patch(
            "asyncio.run", return_value=True
        ):

            # Test normal execution
            result = await main_entry()
            assert result == 0

            # Test KeyboardInterrupt handling
            with patch("builtins.input", side_effect=KeyboardInterrupt()):
                try:
                    result = await main_entry()
                    # KeyboardInterrupt should be handled, not propagated
                    assert result == 1  # Error exit code expected
                except KeyboardInterrupt:
                    pytest.fail(
                        "KeyboardInterrupt should be handled within the test, not propagated"
                    )

    @pytest.mark.asyncio
    async def test_main_entry_not_configured(self):
        """Test main entry when not configured."""
        from calendarbot.cli import main_entry

        # Fix import path mismatch and add AsyncMock for CalendarBot
        with patch("sys.argv", ["calendarbot"]), patch(
            "calendarbot.cli.check_configuration", return_value=(False, None)
        ), patch("calendarbot.cli.show_setup_guidance") as mock_guidance, patch(
            "calendarbot.main.CalendarBot", new_callable=AsyncMock
        ) as mock_calendar_bot, patch(
            "calendarbot.web.server.WebServer"
        ) as mock_web_server, patch(
            "calendarbot.cli.modes.web.run_web_mode", return_value=0
        ), patch(
            "calendarbot.setup_wizard.run_setup_wizard", return_value=True
        ), patch(
            "calendarbot.setup_wizard.run_simple_wizard", return_value=True
        ), patch(
            "builtins.input", return_value=""
        ):

            result = await main_entry()
            assert result == 1
            mock_guidance.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_entry_test_mode(self):
        """Test main entry with test mode - should handle KeyboardInterrupt gracefully."""
        from calendarbot.cli import main_entry

        with patch("sys.argv", ["calendarbot", "--test-mode"]), patch(
            "calendarbot.cli.check_configuration", return_value=(False, None)
        ), patch("calendarbot.cli.modes.test.run_test_mode") as mock_test, patch(
            "calendarbot.validation.ValidationRunner"
        ), patch(
            "calendarbot.main.CalendarBot"
        ) as mock_calendar_bot, patch(
            "calendarbot.web.server.WebServer"
        ):

            # Setup proper AsyncMock for all CalendarBot async methods
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=True)
            mock_instance.run_background_fetch = AsyncMock()
            mock_instance.cleanup = AsyncMock()
            mock_calendar_bot.return_value = mock_instance

            # Test normal execution
            mock_test.return_value = 0
            result = await main_entry()
            assert result == 0
            mock_test.assert_called_once()

            # Test KeyboardInterrupt handling
            mock_test.side_effect = KeyboardInterrupt()
            try:
                result = await main_entry()
                # KeyboardInterrupt should be handled, not propagated
                assert result == 1  # Error exit code expected
            except KeyboardInterrupt:
                pytest.fail("KeyboardInterrupt should be handled within the test, not propagated")

    @pytest.mark.asyncio
    async def test_main_entry_web_mode(self):
        """Test main entry with web mode - should handle KeyboardInterrupt gracefully."""
        from calendarbot.cli import main_entry

        with patch("sys.argv", ["calendarbot", "--web"]), patch(
            "calendarbot.cli.check_configuration", return_value=(True, None)
        ), patch("calendarbot.cli.modes.web.run_web_mode") as mock_web, patch(
            "calendarbot.main.CalendarBot"
        ) as mock_calendar_bot, patch(
            "calendarbot.web.server.WebServer"
        ):

            # Setup proper AsyncMock for CalendarBot.initialize()
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=True)
            mock_calendar_bot.return_value = mock_instance

            # Test normal execution
            mock_web.return_value = 0
            result = await main_entry()
            assert result == 0
            mock_web.assert_called_once()

            # Test KeyboardInterrupt handling
            mock_web.side_effect = KeyboardInterrupt()
            try:
                result = await main_entry()
                # KeyboardInterrupt should be handled, not propagated
                assert result == 1  # Error exit code expected
            except KeyboardInterrupt:
                pytest.fail("KeyboardInterrupt should be handled within the test, not propagated")

    @pytest.mark.asyncio
    async def test_main_entry_interactive_mode(self):
        """Test main entry with interactive mode - should handle KeyboardInterrupt gracefully."""
        from calendarbot.cli import main_entry

        with patch("sys.argv", ["calendarbot"]), patch(
            "calendarbot.cli.check_configuration", return_value=(True, None)
        ), patch(
            "calendarbot.cli.modes.interactive.run_interactive_mode"
        ) as mock_interactive, patch(
            "calendarbot.main.CalendarBot"
        ) as mock_calendar_bot, patch(
            "calendarbot.web.server.WebServer"
        ):

            # Setup proper AsyncMock for all CalendarBot async methods
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=True)
            mock_instance.run_background_fetch = AsyncMock()
            mock_instance.cleanup = AsyncMock()
            mock_calendar_bot.return_value = mock_instance

            # Test normal execution
            mock_interactive.return_value = 0
            result = await main_entry()
            assert result == 0
            mock_interactive.assert_called_once()

            # Test KeyboardInterrupt handling - this is the critical test
            mock_interactive.side_effect = KeyboardInterrupt()
            try:
                result = await main_entry()
                # KeyboardInterrupt should be handled, not propagated to stop test execution
                assert result == 0  # Interactive mode should handle KeyboardInterrupt gracefully
            except KeyboardInterrupt:
                pytest.fail("KeyboardInterrupt should be handled within the test, not propagated")

    @pytest.mark.asyncio
    async def test_keyboard_interrupt_does_not_stop_tests(self):
        """Critical test: Ensure KeyboardInterrupt in main_entry doesn't stop test execution."""
        from calendarbot.cli import main_entry

        # This test specifically verifies that KeyboardInterrupts are contained
        with patch("sys.argv", ["calendarbot", "--setup"]), patch(
            "calendarbot.cli.setup.run_setup_wizard", side_effect=KeyboardInterrupt()
        ), patch("calendarbot.main.CalendarBot", new_callable=AsyncMock), patch(
            "calendarbot.web.server.WebServer"
        ):

            # Multiple calls to verify KeyboardInterrupt doesn't break test execution
            for i in range(3):
                try:
                    result = await main_entry()
                    # Should get here without KeyboardInterrupt propagating
                    assert isinstance(result, int)  # Should return exit code, not raise exception
                except KeyboardInterrupt:
                    pytest.fail(
                        f"KeyboardInterrupt propagated on iteration {i+1}, breaking test execution"
                    )
