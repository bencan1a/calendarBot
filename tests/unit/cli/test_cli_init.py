"""Tests for calendarbot/cli/__init__.py module.

This module tests CLI initialization and main entry point functionality including:
- Main entry point execution with various arguments
- Configuration checking integration
- Mode selection and validation
- Error handling and exit codes
- Import validation
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.cli import main_entry


class TestMainEntry:
    """Test the main_entry function."""

    @pytest.fixture
    def mock_parser_args(self):
        """Create mock parser arguments with minimal required attributes."""
        # Use spec to limit available attributes and improve performance
        args = MagicMock(
            spec=[
                "setup",
                "backup",
                "restore",
                "list_backups",
                "verbose",
                "test_mode",
                "interactive",
                "web",
                "epaper",
                "daemon",
                "daemon_status",
                "daemon_stop",
                "kiosk",
                "kiosk_status",
                "kiosk_stop",
                "kiosk_restart",
                "kiosk_setup",
                "rpi",
                "port",
                "host",
            ]
        )

        # Only set the most commonly used attributes
        args.setup = False
        args.backup = False
        args.restore = None
        args.list_backups = False
        args.test_mode = False
        args.interactive = False
        args.web = False
        args.epaper = False
        args.rpi = False
        args.port = 8080
        args.host = None

        return args

    @pytest.mark.asyncio
    async def test_main_entry_setup_wizard_simple_mode_works(self, mock_parser_args):
        """Test main_entry setup wizard simple mode (choice 2) should work."""
        mock_parser_args.setup = True

        with (
            patch("calendarbot.cli.create_parser") as mock_create_parser,
            patch("builtins.input", return_value="2"),
            patch("builtins.print"),
            patch("calendarbot.setup_wizard.run_simple_wizard", return_value=True) as mock_simple,
        ):
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = mock_parser_args
            mock_create_parser.return_value = mock_parser

            result = await main_entry()

            assert result == 0
            mock_simple.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_entry_backup_configuration(self, mock_parser_args):
        """Test main_entry with backup configuration argument."""
        mock_parser_args.backup = True

        with (
            patch("calendarbot.cli.create_parser") as mock_create_parser,
            patch("calendarbot.cli.backup_configuration") as mock_backup,
        ):
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = mock_parser_args
            mock_create_parser.return_value = mock_parser
            mock_backup.return_value = 0

            result = await main_entry()

            assert result == 0
            mock_backup.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_entry_restore_configuration(self, mock_parser_args):
        """Test main_entry with restore configuration argument."""
        mock_parser_args.restore = "backup_file.yaml"

        with (
            patch("calendarbot.cli.create_parser") as mock_create_parser,
            patch("calendarbot.cli.restore_configuration") as mock_restore,
        ):
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = mock_parser_args
            mock_create_parser.return_value = mock_parser
            mock_restore.return_value = 0

            result = await main_entry()

            assert result == 0
            mock_restore.assert_called_once_with("backup_file.yaml")

    @pytest.mark.asyncio
    async def test_main_entry_list_backups(self, mock_parser_args):
        """Test main_entry with list backups argument."""
        mock_parser_args.list_backups = True

        with (
            patch("calendarbot.cli.create_parser") as mock_create_parser,
            patch("calendarbot.cli.list_backups") as mock_list,
        ):
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = mock_parser_args
            mock_create_parser.return_value = mock_parser
            mock_list.return_value = 0

            result = await main_entry()

            assert result == 0
            mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_entry_test_mode(self, mock_parser_args):
        """Test main_entry with test mode argument."""
        mock_parser_args.test_mode = True

        with (
            patch("calendarbot.cli.create_parser") as mock_create_parser,
            patch("calendarbot.cli.run_test_mode", new_callable=AsyncMock) as mock_test_mode,
        ):
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = mock_parser_args
            mock_create_parser.return_value = mock_parser
            mock_test_mode.return_value = 0

            result = await main_entry()

            assert result == 0
            mock_test_mode.assert_called_once_with(mock_parser_args)

    @pytest.mark.asyncio
    async def test_main_entry_not_configured(self, mock_parser_args, capsys):
        """Test main_entry when not configured."""
        with (
            patch("calendarbot.cli.create_parser") as mock_create_parser,
            patch("calendarbot.cli.check_configuration") as mock_check_config,
            patch("calendarbot.cli.show_setup_guidance") as mock_guidance,
            patch("calendarbot.cli.run_web_mode", new_callable=AsyncMock) as mock_web_mode,
        ):
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = mock_parser_args
            mock_create_parser.return_value = mock_parser
            mock_check_config.return_value = (False, None)
            mock_web_mode.return_value = 0

            result = await main_entry()

            assert result == 0  # Should succeed as web mode runs even when not configured
            mock_check_config.assert_called_once()
            mock_guidance.assert_called_once()
            mock_web_mode.assert_called_once_with(mock_parser_args)

            captured = capsys.readouterr()
            assert "Tip: Run 'calendarbot --setup'" in captured.out

    @pytest.mark.asyncio
    async def test_main_entry_configured_interactive_mode(self, mock_parser_args):
        """Test main_entry in interactive mode when configured."""
        mock_parser_args.interactive = True

        with (
            patch("calendarbot.cli.create_parser") as mock_create_parser,
            patch("calendarbot.cli.check_configuration") as mock_check_config,
            patch(
                "calendarbot.cli.run_interactive_mode", new_callable=AsyncMock
            ) as mock_interactive,
        ):
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = mock_parser_args
            mock_create_parser.return_value = mock_parser
            mock_check_config.return_value = (True, "/path/to/config.yaml")
            mock_interactive.return_value = 0

            result = await main_entry()

            assert result == 0
            mock_interactive.assert_called_once_with(mock_parser_args)

    @pytest.mark.asyncio
    async def test_main_entry_configured_web_mode_default(self, mock_parser_args):
        """Test main_entry defaults to web mode when configured."""
        with (
            patch("calendarbot.cli.create_parser") as mock_create_parser,
            patch("calendarbot.cli.check_configuration") as mock_check_config,
            patch("calendarbot.cli.run_web_mode", new_callable=AsyncMock) as mock_web,
        ):
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = mock_parser_args
            mock_create_parser.return_value = mock_parser
            mock_check_config.return_value = (True, "/path/to/config.yaml")
            mock_web.return_value = 0

            result = await main_entry()

            assert result == 0
            mock_web.assert_called_once_with(mock_parser_args)

    @pytest.mark.asyncio
    async def test_main_entry_configured_web_mode_explicit(self, mock_parser_args):
        """Test main_entry with explicit web mode argument."""
        mock_parser_args.web = True

        with (
            patch("calendarbot.cli.create_parser") as mock_create_parser,
            patch("calendarbot.cli.check_configuration") as mock_check_config,
            patch("calendarbot.cli.run_web_mode", new_callable=AsyncMock) as mock_web,
        ):
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = mock_parser_args
            mock_create_parser.return_value = mock_parser
            mock_check_config.return_value = (True, "/path/to/config.yaml")
            mock_web.return_value = 0

            result = await main_entry()

            assert result == 0
            mock_web.assert_called_once_with(mock_parser_args)

    @pytest.mark.asyncio
    async def test_main_entry_mutually_exclusive_modes_error(self, mock_parser_args):
        """Test main_entry with mutually exclusive mode arguments."""
        mock_parser_args.test_mode = True
        mock_parser_args.interactive = True
        mock_parser_args.web = True

        with (
            patch("calendarbot.cli.create_parser") as mock_create_parser,
            patch("calendarbot.cli.check_configuration") as mock_check_config,
        ):
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = mock_parser_args
            mock_parser.error.side_effect = (
                SystemExit  # Configure mock to raise SystemExit like real argparse
            )
            mock_create_parser.return_value = mock_parser
            mock_check_config.return_value = (True, "/path/to/config.yaml")

            # Should call parser.error for mutually exclusive modes
            with pytest.raises(SystemExit):
                await main_entry()

            mock_parser.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_entry_test_mode_without_configuration(self, mock_parser_args):
        """Test that test mode can run even without configuration."""
        mock_parser_args.test_mode = True

        with (
            patch("calendarbot.cli.create_parser") as mock_create_parser,
            patch("calendarbot.cli.run_test_mode", new_callable=AsyncMock) as mock_test_mode,
        ):
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = mock_parser_args
            mock_create_parser.return_value = mock_parser
            mock_test_mode.return_value = 0

            result = await main_entry()

            assert result == 0
            mock_test_mode.assert_called_once_with(mock_parser_args)

    @pytest.mark.asyncio
    async def test_main_entry_hasattr_safety(self, mock_parser_args):
        """Test main_entry handles missing attributes gracefully."""
        # Remove some attributes to test hasattr checks
        delattr(mock_parser_args, "setup")
        delattr(mock_parser_args, "backup")

        with (
            patch("calendarbot.cli.create_parser") as mock_create_parser,
            patch("calendarbot.cli.check_configuration") as mock_check_config,
            patch("calendarbot.cli.run_web_mode", new_callable=AsyncMock) as mock_web,
        ):
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = mock_parser_args
            mock_create_parser.return_value = mock_parser
            mock_check_config.return_value = (True, "/path/to/config.yaml")
            mock_web.return_value = 0

            result = await main_entry()

            assert result == 0
            mock_web.assert_called_once_with(mock_parser_args)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("mode_args", "expected_count"),
        [
            ({"test_mode": False, "interactive": False, "web": False}, 0),
            ({"test_mode": True, "interactive": False, "web": False}, 1),
            ({"test_mode": False, "interactive": True, "web": False}, 1),
            ({"test_mode": False, "interactive": False, "web": True}, 1),
            ({"test_mode": True, "interactive": True, "web": False}, 2),
            ({"test_mode": True, "interactive": True, "web": True}, 3),
        ],
    )
    async def test_main_entry_mode_count_calculation(
        self, mock_parser_args, mode_args, expected_count
    ):
        """Test mode count calculation for mutual exclusion."""
        for attr, value in mode_args.items():
            setattr(mock_parser_args, attr, value)

        with (
            patch("calendarbot.cli.create_parser") as mock_create_parser,
            patch("calendarbot.cli.check_configuration") as mock_check_config,
        ):
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = mock_parser_args
            mock_create_parser.return_value = mock_parser
            mock_check_config.return_value = (True, "/path/to/config.yaml")

            if expected_count > 1:
                # Configure mock to raise SystemExit only for cases that should error
                mock_parser.error.side_effect = SystemExit
                # Should error on multiple modes
                with pytest.raises(SystemExit):
                    await main_entry()
                mock_parser.error.assert_called_once()
            # Should not error - mock the appropriate mode function
            elif mode_args.get("test_mode", False):
                with patch("calendarbot.cli.run_test_mode", new_callable=AsyncMock) as mock_mode:
                    mock_mode.return_value = 0
                    result = await main_entry()
                    assert result == 0
            elif mode_args.get("interactive", False):
                with patch(
                    "calendarbot.cli.run_interactive_mode", new_callable=AsyncMock
                ) as mock_mode:
                    mock_mode.return_value = 0
                    result = await main_entry()
                    assert result == 0
            else:
                # Default to web mode or explicit web mode
                with patch("calendarbot.cli.run_web_mode", new_callable=AsyncMock) as mock_mode:
                    mock_mode.return_value = 0
                    result = await main_entry()
                    assert result == 0

    @pytest.mark.asyncio
    async def test_main_entry_return_codes(self, mock_parser_args):
        """Test main_entry propagates return codes correctly."""
        test_cases = [
            ("run_setup_wizard", {"setup": True}, 0),
            ("run_setup_wizard", {"setup": True}, 1),
            ("backup_configuration", {"backup": True}, 0),
            ("backup_configuration", {"backup": True}, 1),
        ]

        for mock_func_name, args_dict, expected_code in test_cases:
            # Reset args
            for attr in ["setup", "backup", "restore", "list_backups", "test_mode"]:
                setattr(mock_parser_args, attr, False if attr != "restore" else None)

            # Set specific args
            for attr, value in args_dict.items():
                setattr(mock_parser_args, attr, value)

            with (
                patch("calendarbot.cli.create_parser") as mock_create_parser,
                patch(f"calendarbot.cli.{mock_func_name}") as mock_func,
            ):
                mock_parser = MagicMock()
                mock_parser.parse_args.return_value = mock_parser_args
                mock_create_parser.return_value = mock_parser
                mock_func.return_value = expected_code

                result = await main_entry()

                assert result == expected_code
                mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_entry_async_mode_functions(self, mock_parser_args):
        """Test main_entry calls async mode functions correctly."""
        async_test_cases = [
            ("run_test_mode", {"test_mode": True}),
            ("run_interactive_mode", {"interactive": True}),
            ("run_web_mode", {"web": True}),
        ]

        for mock_func_name, args_dict in async_test_cases:
            # Reset args
            for attr in ["test_mode", "interactive", "web"]:
                setattr(mock_parser_args, attr, False)

            # Set specific args
            for attr, value in args_dict.items():
                setattr(mock_parser_args, attr, value)

            with (
                patch("calendarbot.cli.create_parser") as mock_create_parser,
                patch("calendarbot.cli.check_configuration") as mock_check_config,
                patch(f"calendarbot.cli.{mock_func_name}", new_callable=AsyncMock) as mock_func,
            ):
                mock_parser = MagicMock()
                mock_parser.parse_args.return_value = mock_parser_args
                mock_create_parser.return_value = mock_parser
                mock_check_config.return_value = (True, "/path/to/config.yaml")
                mock_func.return_value = 0

                result = await main_entry()

                assert result == 0
                mock_func.assert_called_once_with(mock_parser_args)


class TestCliImports:
    """Test CLI module imports and exports."""

    def test_cli_module_imports(self):
        """Test that CLI module imports work correctly."""
        from calendarbot.cli import (
            apply_cli_overrides,
            backup_configuration,
            check_configuration,
            create_parser,
            list_backups,
            main_entry,
            parse_components,
            parse_date,
            restore_configuration,
            run_interactive_mode,
            run_setup_wizard,
            run_test_mode,
            run_web_mode,
            show_setup_guidance,
        )

        # Verify all imports are callable
        callable_functions = [
            main_entry,
            create_parser,
            parse_date,
            parse_components,
            check_configuration,
            show_setup_guidance,
            apply_cli_overrides,
            run_setup_wizard,
            backup_configuration,
            restore_configuration,
            list_backups,
            run_interactive_mode,
            run_web_mode,
            run_test_mode,
        ]

        for func in callable_functions:
            assert callable(func)

    def test_cli_module_exports(self):
        """Test that CLI module exports expected items."""
        import calendarbot.cli as cli_module

        expected_exports = [
            "main_entry",
            "create_parser",
            "parse_date",
            "parse_components",
            "check_configuration",
            "show_setup_guidance",
            "apply_cli_overrides",
            "run_setup_wizard",
            "backup_configuration",
            "restore_configuration",
            "list_backups",
            "run_interactive_mode",
            "run_web_mode",
            "run_test_mode",
        ]

        for export in expected_exports:
            assert hasattr(cli_module, export)
            assert callable(getattr(cli_module, export))

    def test_cli_module_has_all_attribute(self):
        """Test that CLI module defines __all__ correctly."""
        import calendarbot.cli as cli_module

        assert hasattr(cli_module, "__all__")
        assert isinstance(cli_module.__all__, list)
        assert len(cli_module.__all__) > 0

    def test_cli_module_docstring(self):
        """Test that CLI module has proper documentation."""
        import calendarbot.cli as cli_module

        assert cli_module.__doc__ is not None
        assert "CLI module for Calendar Bot application" in cli_module.__doc__


class TestCliIntegration:
    """Test CLI integration scenarios."""

    @pytest.mark.asyncio
    async def test_main_entry_integration_flow(self):
        """Test main_entry integration with typical argument flow."""
        with (
            patch("calendarbot.cli.create_parser") as mock_create_parser,
            patch("calendarbot.cli.check_configuration") as mock_check_config,
            patch("calendarbot.cli.run_web_mode", new_callable=AsyncMock) as mock_web_mode,
        ):
            # Create realistic args
            args = MagicMock()
            args.setup = False
            args.backup = False
            args.restore = None
            args.list_backups = False
            args.test_mode = False
            args.interactive = False
            args.web = False
            args.epaper = False

            # Add missing daemon arguments
            args.daemon = False
            args.daemon_status = False
            args.daemon_stop = False

            # Add missing kiosk arguments
            args.kiosk = False
            args.kiosk_status = False
            args.kiosk_stop = False
            args.kiosk_restart = False
            args.kiosk_setup = False

            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = args
            mock_create_parser.return_value = mock_parser
            mock_check_config.return_value = (True, "/path/to/config.yaml")
            mock_web_mode.return_value = 0

            result = await main_entry()

            assert result == 0
            mock_create_parser.assert_called_once()
            mock_parser.parse_args.assert_called_once()
            mock_check_config.assert_called_once()
            mock_web_mode.assert_called_once_with(args)

    @pytest.mark.asyncio
    async def test_main_entry_error_propagation(self):
        """Test that main_entry propagates errors appropriately."""
        with patch("calendarbot.cli.create_parser") as mock_create_parser:
            mock_create_parser.side_effect = Exception("Parser creation failed")

            with pytest.raises(Exception, match="Parser creation failed"):
                await main_entry()

    def test_module_level_functionality(self):
        """Test module-level functionality and structure."""
        import calendarbot.cli

        # Module should be importable
        assert calendarbot.cli is not None

        # Key functions should be accessible
        assert hasattr(calendarbot.cli, "main_entry")
        assert asyncio.iscoroutinefunction(calendarbot.cli.main_entry)
