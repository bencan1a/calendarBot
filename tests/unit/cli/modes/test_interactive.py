"""Unit tests for CLI interactive mode functionality.

Tests cover:
- Interactive mode execution with success and failure scenarios
- Logging setup and component initialization
- Exception handling and cleanup
- Argument processing edge cases
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.cli.modes import interactive


class TestRunInteractiveMode:
    """Test the run_interactive_mode function."""

    @pytest.mark.asyncio
    async def test_run_interactive_mode_initialization_failure(self, test_settings):
        """Test interactive mode when CalendarBot initialization fails."""
        mock_args = MagicMock()
        mock_args.rpi = False

        mock_calendar_bot = MagicMock()
        mock_calendar_bot.initialize = AsyncMock(return_value=False)

        with patch("calendarbot.main.CalendarBot", return_value=mock_calendar_bot), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch("calendarbot.cli.config.apply_cli_overrides", return_value=test_settings), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "calendarbot.config.settings.settings", test_settings
        ), patch(
            "builtins.print"
        ) as mock_print:
            result = await interactive.run_interactive_mode(mock_args)

            assert result == 1
            mock_print.assert_called_with("Failed to initialize Calendar Bot")

    @pytest.mark.asyncio
    async def test_run_interactive_mode_exception_handling(self, test_settings):
        """Test interactive mode handles exceptions properly."""
        mock_args = MagicMock()
        mock_args.rpi = False

        with patch("calendarbot.main.CalendarBot", side_effect=Exception("Test exception")), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch("calendarbot.cli.config.apply_cli_overrides", return_value=test_settings), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "calendarbot.config.settings.settings", test_settings
        ), patch(
            "builtins.print"
        ) as mock_print:
            result = await interactive.run_interactive_mode(mock_args)

            assert result == 1
            mock_print.assert_called_with("Interactive mode error: Test exception")

    @pytest.mark.asyncio
    async def test_run_interactive_mode_keyboard_interrupt(self, test_settings):
        """Test interactive mode handles KeyboardInterrupt gracefully."""
        mock_args = MagicMock()
        mock_args.rpi = False

        mock_calendar_bot = MagicMock()
        mock_calendar_bot.initialize = AsyncMock(return_value=True)
        mock_calendar_bot.cache_manager = MagicMock()
        mock_calendar_bot.display_manager = MagicMock()

        with patch("calendarbot.main.CalendarBot", return_value=mock_calendar_bot), patch(
            "calendarbot.ui.InteractiveController", side_effect=KeyboardInterrupt()
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_cli_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "calendarbot.config.settings.settings", test_settings
        ), patch(
            "builtins.print"
        ) as mock_print:
            result = await interactive.run_interactive_mode(mock_args)

            assert result == 0
            mock_print.assert_called_with("\nInteractive mode interrupted")

    @pytest.mark.asyncio
    async def test_run_interactive_mode_import_error(self, test_settings):
        """Test interactive mode when imports fail."""
        mock_args = MagicMock()
        mock_args.rpi = False

        with patch(
            "calendarbot.main.CalendarBot", side_effect=ImportError("Module not found")
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_cli_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "calendarbot.config.settings.settings", test_settings
        ), patch(
            "builtins.print"
        ) as mock_print:
            result = await interactive.run_interactive_mode(mock_args)

            assert result == 1
            mock_print.assert_called_with("Interactive mode error: Module not found")

    @pytest.mark.asyncio
    async def test_run_interactive_mode_rpi_overrides(self, test_settings):
        """Test that RPI overrides are called correctly."""
        mock_args = MagicMock()
        mock_args.rpi = True

        # Make CalendarBot initialization fail to avoid complex async issues
        mock_calendar_bot = MagicMock()
        mock_calendar_bot.initialize = AsyncMock(return_value=False)

        with patch("calendarbot.main.CalendarBot", return_value=mock_calendar_bot), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_cli_overrides", return_value=test_settings
        ) as mock_rpi_overrides, patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "calendarbot.config.settings.settings", test_settings
        ), patch(
            "builtins.print"
        ):
            result = await interactive.run_interactive_mode(mock_args)

            assert result == 1  # Fails due to initialization
            mock_rpi_overrides.assert_called_once_with(test_settings, mock_args)

    @pytest.mark.asyncio
    async def test_run_interactive_mode_component_creation(self, test_settings):
        """Test that components are created properly when initialization succeeds."""
        mock_args = MagicMock()
        mock_args.rpi = False

        mock_calendar_bot = MagicMock()
        mock_calendar_bot.initialize = AsyncMock(return_value=True)
        mock_calendar_bot.cache_manager = MagicMock()
        mock_calendar_bot.display_manager = MagicMock()

        # Make InteractiveController creation fail to test component creation
        with patch("calendarbot.main.CalendarBot", return_value=mock_calendar_bot), patch(
            "calendarbot.ui.InteractiveController",
            side_effect=Exception("Controller creation failed"),
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_cli_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ) as mock_setup_logging, patch(
            "calendarbot.config.settings.settings", test_settings
        ), patch(
            "builtins.print"
        ) as mock_print:
            result = await interactive.run_interactive_mode(mock_args)

            assert result == 1
            # Verify initialization was called
            mock_calendar_bot.initialize.assert_called_once()
            # Verify enhanced logging was set up
            mock_setup_logging.assert_called_once()
            mock_print.assert_called_with("Interactive mode error: Controller creation failed")



class TestInteractiveModeModuleExports:
    """Test interactive module's __all__ exports."""

    def test_module_exports(self):
        """Test that all expected functions are exported."""
        expected_exports = [
            "run_interactive_mode"
        ]

        assert hasattr(interactive, "__all__")
        assert interactive.__all__ == expected_exports

        # Verify all exported functions exist
        for export in expected_exports:
            assert hasattr(interactive, export)
            assert callable(getattr(interactive, export))


class TestInteractiveModeArgumentProcessing:
    """Test argument processing and edge cases for interactive mode."""

    @pytest.mark.parametrize("rpi_setting", [True, False])
    @pytest.mark.asyncio
    async def test_run_interactive_mode_rpi_configurations(self, rpi_setting, test_settings):
        """Test different RPI configuration scenarios."""
        mock_args = MagicMock()
        mock_args.rpi = rpi_setting

        # Use initialization failure to avoid complex async flow
        mock_calendar_bot = MagicMock()
        mock_calendar_bot.initialize = AsyncMock(return_value=False)

        with patch("calendarbot.main.CalendarBot", return_value=mock_calendar_bot), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_cli_overrides", return_value=test_settings
        ) as mock_rpi_overrides, patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "calendarbot.config.settings.settings", test_settings
        ), patch(
            "builtins.print"
        ):
            result = await interactive.run_interactive_mode(mock_args)

            assert result == 1  # Fails due to initialization
            mock_rpi_overrides.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_interactive_mode_minimal_args(self, test_settings):
        """Test interactive mode with minimal argument attributes."""
        minimal_args = MagicMock()
        minimal_args.rpi = False

        # Use initialization failure to test args processing
        mock_calendar_bot = MagicMock()
        mock_calendar_bot.initialize = AsyncMock(return_value=False)

        with patch("calendarbot.main.CalendarBot", return_value=mock_calendar_bot), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch("calendarbot.cli.config.apply_cli_overrides", return_value=test_settings), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "calendarbot.config.settings.settings", test_settings
        ), patch(
            "builtins.print"
        ):
            result = await interactive.run_interactive_mode(minimal_args)

            assert result == 1  # Should handle minimal args gracefully


class TestInteractiveModeIntegration:
    """Integration tests for interactive mode functionality."""

    @pytest.mark.asyncio
    async def test_interactive_mode_edge_case_error_handling(self, test_settings):
        """Test edge cases in error handling."""
        mock_args = MagicMock()
        mock_args.rpi = False

        # Test with various exception types
        exception_types = [
            RuntimeError("Runtime error"),
            ValueError("Value error"),
            TypeError("Type error"),
            Exception("Generic exception"),
        ]

        for exception in exception_types:
            with patch("calendarbot.main.CalendarBot", side_effect=exception), patch(
                "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
            ), patch(
                "calendarbot.cli.config.apply_cli_overrides", return_value=test_settings
            ), patch(
                "calendarbot.utils.logging.setup_enhanced_logging"
            ), patch(
                "calendarbot.config.settings.settings", test_settings
            ), patch(
                "builtins.print"
            ) as mock_print:
                result = await interactive.run_interactive_mode(mock_args)

                assert result == 1
                mock_print.assert_called_with(f"Interactive mode error: {exception}")

    @pytest.mark.asyncio
    async def test_interactive_mode_logging_setup_calls(self, test_settings):
        """Test that logging setup functions are called correctly."""
        mock_args = MagicMock()
        mock_args.rpi = False

        # Use successful initialization to reach the logging setup
        mock_calendar_bot = MagicMock()
        mock_calendar_bot.initialize = AsyncMock(return_value=True)
        mock_calendar_bot.cache_manager = MagicMock()
        mock_calendar_bot.display_manager = MagicMock()

        # Make InteractiveController creation fail after logging setup
        with patch("calendarbot.main.CalendarBot", return_value=mock_calendar_bot), patch(
            "calendarbot.ui.InteractiveController", side_effect=Exception("Controller failed")
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ) as mock_cmd_overrides, patch(
            "calendarbot.cli.config.apply_cli_overrides", return_value=test_settings
        ) as mock_rpi_overrides, patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ) as mock_setup_logging, patch(
            "calendarbot.config.settings.settings", test_settings
        ), patch(
            "builtins.print"
        ):
            result = await interactive.run_interactive_mode(mock_args)

            assert result == 1
            # Verify all setup functions were called
            mock_cmd_overrides.assert_called_once_with(test_settings, mock_args)
            mock_rpi_overrides.assert_called_once_with(test_settings, mock_args)
            mock_setup_logging.assert_called_once()
