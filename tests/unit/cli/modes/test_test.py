"""Unit tests for CLI test mode functionality.

Tests cover:
- Test mode execution with success and failure scenarios
- ValidationRunner configuration and execution
- Results processing and exit code handling
- Settings overrides and logging configuration
- Error handling for various exception types
- Argument processing and edge cases
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.cli.modes import test


class TestRunTestMode:
    """Test the run_test_mode function."""

    @pytest.fixture
    def mock_args(self):
        """Create mock command line arguments."""
        args = MagicMock()
        args.date = "2023-12-01"
        args.end_date = "2023-12-07"
        args.components = ["sources", "cache", "display"]
        args.no_cache = False
        args.output_format = "console"
        args.verbose = False
        return args

    @pytest.fixture
    def mock_validation_runner(self):
        """Create mock validation runner."""
        runner = AsyncMock()
        runner.run_validation = AsyncMock()
        runner.print_results = MagicMock()
        return runner

    @pytest.fixture
    def mock_validation_results(self):
        """Create mock validation results."""
        results = MagicMock()
        results.has_failures = MagicMock(return_value=False)
        results.has_warnings = MagicMock(return_value=False)
        return results

    @pytest.mark.asyncio
    async def test_run_test_mode_success_no_issues(
        self, test_settings, mock_args, mock_validation_runner, mock_validation_results
    ):
        """Test successful test mode execution with no failures or warnings."""
        mock_validation_runner.run_validation.return_value = mock_validation_results

        with patch(
            "calendarbot.validation.ValidationRunner", return_value=mock_validation_runner
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ) as mock_setup_logging, patch(
            "config.settings.settings", test_settings
        ):

            mock_logger = MagicMock()
            mock_setup_logging.return_value = mock_logger

            result = await test.run_test_mode(mock_args)

            assert result == 0
            mock_validation_runner.run_validation.assert_called_once()
            mock_validation_runner.print_results.assert_called_once_with(verbose=False)
            mock_logger.info.assert_any_call("Enhanced logging initialized for test mode")
            mock_logger.info.assert_any_call("Starting Calendar Bot validation...")
            mock_logger.info.assert_any_call("Validation completed successfully")

    @pytest.mark.asyncio
    async def test_run_test_mode_with_failures(
        self, test_settings, mock_args, mock_validation_runner, mock_validation_results
    ):
        """Test test mode execution with validation failures."""
        mock_validation_results.has_failures.return_value = True
        mock_validation_runner.run_validation.return_value = mock_validation_results

        with patch(
            "calendarbot.validation.ValidationRunner", return_value=mock_validation_runner
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ) as mock_setup_logging, patch(
            "config.settings.settings", test_settings
        ):

            mock_logger = MagicMock()
            mock_setup_logging.return_value = mock_logger

            result = await test.run_test_mode(mock_args)

            assert result == 1
            mock_logger.error.assert_called_with("Validation completed with failures")

    @pytest.mark.asyncio
    async def test_run_test_mode_with_warnings_only(
        self, test_settings, mock_args, mock_validation_runner, mock_validation_results
    ):
        """Test test mode execution with warnings but no failures."""
        mock_validation_results.has_failures.return_value = False
        mock_validation_results.has_warnings.return_value = True
        mock_validation_runner.run_validation.return_value = mock_validation_results

        with patch(
            "calendarbot.validation.ValidationRunner", return_value=mock_validation_runner
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ) as mock_setup_logging, patch(
            "config.settings.settings", test_settings
        ):

            mock_logger = MagicMock()
            mock_setup_logging.return_value = mock_logger

            result = await test.run_test_mode(mock_args)

            assert result == 0  # Warnings don't cause failure
            mock_logger.warning.assert_called_with("Validation completed with warnings")

    @pytest.mark.asyncio
    async def test_run_test_mode_verbose_output(
        self, test_settings, mock_validation_runner, mock_validation_results
    ):
        """Test test mode with verbose output enabled."""
        mock_args = MagicMock()
        mock_args.date = None
        mock_args.end_date = None
        mock_args.components = ["sources"]
        mock_args.no_cache = False
        mock_args.output_format = "json"
        mock_args.verbose = True

        mock_validation_runner.run_validation.return_value = mock_validation_results

        with patch(
            "calendarbot.validation.ValidationRunner", return_value=mock_validation_runner
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "config.settings.settings", test_settings
        ):

            result = await test.run_test_mode(mock_args)

            assert result == 0
            mock_validation_runner.print_results.assert_called_once_with(verbose=True)

    @pytest.mark.asyncio
    async def test_run_test_mode_with_cache_disabled(
        self, test_settings, mock_validation_runner, mock_validation_results
    ):
        """Test test mode with cache disabled."""
        mock_args = MagicMock()
        mock_args.date = "2023-12-01"
        mock_args.end_date = None
        mock_args.components = ["cache", "display"]
        mock_args.no_cache = True
        mock_args.output_format = "console"
        mock_args.verbose = False

        mock_validation_runner.run_validation.return_value = mock_validation_results

        with patch("calendarbot.validation.ValidationRunner") as mock_runner_class, patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch("calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "config.settings.settings", test_settings
        ):

            mock_runner_class.return_value = mock_validation_runner

            result = await test.run_test_mode(mock_args)

            assert result == 0
            # Verify ValidationRunner was created with correct parameters
            mock_runner_class.assert_called_once_with(
                test_date="2023-12-01",
                end_date=None,
                components=["cache", "display"],
                use_cache=False,  # no_cache=True means use_cache=False
                output_format="console",
            )

    @pytest.mark.asyncio
    async def test_run_test_mode_keyboard_interrupt(self, test_settings):
        """Test test mode handles KeyboardInterrupt gracefully."""
        mock_args = MagicMock()
        mock_args.date = None
        mock_args.end_date = None
        mock_args.components = ["sources"]
        mock_args.no_cache = False
        mock_args.output_format = "console"
        mock_args.verbose = False

        with patch("calendarbot.validation.ValidationRunner", side_effect=KeyboardInterrupt), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch("calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "config.settings.settings", test_settings
        ), patch(
            "builtins.print"
        ) as mock_print:

            result = await test.run_test_mode(mock_args)

            assert result == 1
            mock_print.assert_called_with("\nTest mode interrupted")

    @pytest.mark.asyncio
    async def test_run_test_mode_import_error(self, test_settings):
        """Test test mode handles ImportError gracefully."""
        mock_args = MagicMock()
        mock_args.date = None
        mock_args.end_date = None
        mock_args.components = ["sources"]
        mock_args.no_cache = False
        mock_args.output_format = "console"
        mock_args.verbose = False

        with patch(
            "calendarbot.validation.ValidationRunner", side_effect=ImportError("Module not found")
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "config.settings.settings", test_settings
        ), patch(
            "builtins.print"
        ) as mock_print:

            result = await test.run_test_mode(mock_args)

            assert result == 1
            mock_print.assert_called_with("Import error in test mode: Module not found")

    @pytest.mark.asyncio
    async def test_run_test_mode_general_exception(self, test_settings):
        """Test test mode handles general exceptions gracefully."""
        mock_args = MagicMock()
        mock_args.date = None
        mock_args.end_date = None
        mock_args.components = ["sources"]
        mock_args.no_cache = False
        mock_args.output_format = "console"
        mock_args.verbose = False

        with patch(
            "calendarbot.validation.ValidationRunner", side_effect=RuntimeError("Validation failed")
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "config.settings.settings", test_settings
        ), patch(
            "builtins.print"
        ) as mock_print:

            result = await test.run_test_mode(mock_args)

            assert result == 1
            mock_print.assert_called_with("Test mode error: Validation failed")

    @pytest.mark.asyncio
    async def test_run_test_mode_validation_runner_exception(
        self, test_settings, mock_validation_runner
    ):
        """Test test mode when ValidationRunner.run_validation raises exception."""
        mock_args = MagicMock()
        mock_args.date = None
        mock_args.end_date = None
        mock_args.components = ["sources"]
        mock_args.no_cache = False
        mock_args.output_format = "console"
        mock_args.verbose = False

        mock_validation_runner.run_validation.side_effect = Exception("Runner failed")

        with patch(
            "calendarbot.validation.ValidationRunner", return_value=mock_validation_runner
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "config.settings.settings", test_settings
        ), patch(
            "builtins.print"
        ) as mock_print:

            result = await test.run_test_mode(mock_args)

            assert result == 1
            mock_print.assert_called_with("Test mode error: Runner failed")

    @pytest.mark.asyncio
    async def test_run_test_mode_with_rpi_overrides(
        self, test_settings, mock_validation_runner, mock_validation_results
    ):
        """Test test mode with RPI-specific overrides."""
        mock_args = MagicMock()
        mock_args.date = None
        mock_args.end_date = None
        mock_args.components = ["sources"]
        mock_args.no_cache = False
        mock_args.output_format = "console"
        mock_args.verbose = False
        mock_args.rpi = True

        mock_validation_runner.run_validation.return_value = mock_validation_results

        with patch(
            "calendarbot.validation.ValidationRunner", return_value=mock_validation_runner
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ) as mock_rpi_overrides, patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "config.settings.settings", test_settings
        ):

            result = await test.run_test_mode(mock_args)

            assert result == 0
            mock_rpi_overrides.assert_called_once_with(test_settings, mock_args)


class TestTestModeArgumentProcessing:
    """Test argument processing and getattr usage in test mode."""

    @pytest.fixture
    def mock_validation_runner(self):
        """Create mock validation runner."""
        runner = AsyncMock()
        runner.run_validation = AsyncMock()
        runner.print_results = MagicMock()
        return runner

    @pytest.fixture
    def mock_validation_results(self):
        """Create mock validation results."""
        results = MagicMock()
        results.has_failures = MagicMock(return_value=False)
        results.has_warnings = MagicMock(return_value=False)
        return results

    @pytest.mark.asyncio
    async def test_run_test_mode_missing_attributes(
        self, test_settings, mock_validation_runner, mock_validation_results
    ):
        """Test test mode with missing argument attributes (using getattr defaults)."""
        # Create args without some optional attributes
        minimal_args = MagicMock()
        # Remove some attributes to test getattr defaults
        for attr in ["date", "end_date", "components", "no_cache", "output_format", "verbose"]:
            if hasattr(minimal_args, attr):
                delattr(minimal_args, attr)

        mock_validation_runner.run_validation.return_value = mock_validation_results

        with patch("calendarbot.validation.ValidationRunner") as mock_runner_class, patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch("calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "config.settings.settings", test_settings
        ):

            mock_runner_class.return_value = mock_validation_runner

            result = await test.run_test_mode(minimal_args)

            assert result == 0
            # Verify ValidationRunner was called with default values
            mock_runner_class.assert_called_once_with(
                test_date=None,  # default from getattr
                end_date=None,  # default from getattr
                components=["sources", "cache", "display"],  # default from getattr
                use_cache=True,  # default from getattr (not no_cache)
                output_format="console",  # default from getattr
            )
            # Should use default for verbose
            mock_validation_runner.print_results.assert_called_once_with(verbose=False)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("output_format", ["console", "json", "xml"])
    async def test_run_test_mode_different_output_formats(
        self, output_format, test_settings, mock_validation_runner, mock_validation_results
    ):
        """Test test mode with different output formats."""
        mock_args = MagicMock()
        mock_args.date = None
        mock_args.end_date = None
        mock_args.components = ["sources"]
        mock_args.no_cache = False
        mock_args.output_format = output_format
        mock_args.verbose = False

        mock_validation_runner.run_validation.return_value = mock_validation_results

        with patch("calendarbot.validation.ValidationRunner") as mock_runner_class, patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch("calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "config.settings.settings", test_settings
        ):

            mock_runner_class.return_value = mock_validation_runner

            result = await test.run_test_mode(mock_args)

            assert result == 0
            mock_runner_class.assert_called_once_with(
                test_date=None,
                end_date=None,
                components=["sources"],
                use_cache=True,
                output_format=output_format,
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "components",
        [
            ["sources"],
            ["cache"],
            ["display"],
            ["sources", "cache"],
            ["cache", "display"],
            ["sources", "cache", "display"],
            [],
        ],
    )
    async def test_run_test_mode_different_component_combinations(
        self, components, test_settings, mock_validation_runner, mock_validation_results
    ):
        """Test test mode with different component combinations."""
        mock_args = MagicMock()
        mock_args.date = None
        mock_args.end_date = None
        mock_args.components = components
        mock_args.no_cache = False
        mock_args.output_format = "console"
        mock_args.verbose = False

        mock_validation_runner.run_validation.return_value = mock_validation_results

        with patch("calendarbot.validation.ValidationRunner") as mock_runner_class, patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch("calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ), patch(
            "config.settings.settings", test_settings
        ):

            mock_runner_class.return_value = mock_validation_runner

            result = await test.run_test_mode(mock_args)

            assert result == 0
            mock_runner_class.assert_called_once_with(
                test_date=None,
                end_date=None,
                components=components,
                use_cache=True,
                output_format="console",
            )


class TestTestModeModuleExports:
    """Test test module's __all__ exports."""

    def test_module_exports(self):
        """Test that all expected functions are exported."""
        expected_exports = [
            "run_test_mode",
        ]

        assert hasattr(test, "__all__")
        assert test.__all__ == expected_exports

        # Verify all exported functions exist
        for export in expected_exports:
            assert hasattr(test, export)
            assert callable(getattr(test, export))


class TestTestModeIntegration:
    """Integration tests for test mode functionality."""

    @pytest.mark.asyncio
    async def test_test_mode_full_workflow_success(self, test_settings):
        """Test complete test mode workflow with successful validation."""
        mock_args = MagicMock()
        mock_args.date = "2023-12-01"
        mock_args.end_date = "2023-12-07"
        mock_args.components = ["sources", "cache", "display"]
        mock_args.no_cache = False
        mock_args.output_format = "json"
        mock_args.verbose = True

        mock_validation_runner = AsyncMock()
        mock_validation_results = MagicMock()
        mock_validation_results.has_failures.return_value = False
        mock_validation_results.has_warnings.return_value = False
        mock_validation_runner.run_validation.return_value = mock_validation_results
        mock_validation_runner.print_results = MagicMock()

        with patch("calendarbot.validation.ValidationRunner") as mock_runner_class, patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ) as mock_rpi_overrides, patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ) as mock_setup_logging, patch(
            "config.settings.settings", test_settings
        ):

            mock_runner_class.return_value = mock_validation_runner
            mock_logger = MagicMock()
            mock_setup_logging.return_value = mock_logger

            result = await test.run_test_mode(mock_args)

            # Verify successful completion
            assert result == 0

            # Verify complete workflow
            mock_runner_class.assert_called_once_with(
                test_date="2023-12-01",
                end_date="2023-12-07",
                components=["sources", "cache", "display"],
                use_cache=True,
                output_format="json",
            )
            mock_validation_runner.run_validation.assert_called_once()
            mock_validation_runner.print_results.assert_called_once_with(verbose=True)
            mock_rpi_overrides.assert_called_once_with(test_settings, mock_args)
            mock_setup_logging.assert_called_once_with(test_settings, interactive_mode=False)

            # Verify logging calls
            mock_logger.info.assert_any_call("Enhanced logging initialized for test mode")
            mock_logger.info.assert_any_call("Starting Calendar Bot validation...")
            mock_logger.info.assert_any_call("Validation completed successfully")

    @pytest.mark.asyncio
    async def test_test_mode_workflow_with_mixed_results(self, test_settings):
        """Test test mode workflow with different result scenarios."""
        mock_args = MagicMock()
        mock_args.date = None
        mock_args.end_date = None
        mock_args.components = ["sources"]
        mock_args.no_cache = True
        mock_args.output_format = "console"
        mock_args.verbose = False

        # Test scenario with failures and warnings
        mock_validation_runner = AsyncMock()
        mock_validation_results = MagicMock()
        mock_validation_results.has_failures.return_value = True
        mock_validation_results.has_warnings.return_value = True
        mock_validation_runner.run_validation.return_value = mock_validation_results

        with patch(
            "calendarbot.validation.ValidationRunner", return_value=mock_validation_runner
        ), patch(
            "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
        ), patch(
            "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
        ), patch(
            "calendarbot.utils.logging.setup_enhanced_logging"
        ) as mock_setup_logging, patch(
            "config.settings.settings", test_settings
        ):

            mock_logger = MagicMock()
            mock_setup_logging.return_value = mock_logger

            result = await test.run_test_mode(mock_args)

            # Should return 1 for failures (even with warnings)
            assert result == 1
            mock_logger.error.assert_called_with("Validation completed with failures")

    @pytest.mark.asyncio
    async def test_test_mode_edge_cases_and_error_handling(self, test_settings):
        """Test edge cases and comprehensive error handling."""
        mock_args = MagicMock()
        mock_args.date = None
        mock_args.end_date = None
        mock_args.components = []
        mock_args.no_cache = False
        mock_args.output_format = "console"
        mock_args.verbose = False

        # Test different exception scenarios
        exception_scenarios = [
            (KeyboardInterrupt(), "\nTest mode interrupted"),
            (ImportError("Missing module"), "Import error in test mode: Missing module"),
            (ValueError("Invalid value"), "Test mode error: Invalid value"),
            (RuntimeError("Runtime issue"), "Test mode error: Runtime issue"),
            (Exception("Generic error"), "Test mode error: Generic error"),
        ]

        for exception, expected_message in exception_scenarios:
            with patch("calendarbot.validation.ValidationRunner", side_effect=exception), patch(
                "calendarbot.utils.logging.apply_command_line_overrides", return_value=test_settings
            ), patch(
                "calendarbot.cli.config.apply_rpi_overrides", return_value=test_settings
            ), patch(
                "calendarbot.utils.logging.setup_enhanced_logging"
            ), patch(
                "config.settings.settings", test_settings
            ), patch(
                "builtins.print"
            ) as mock_print:

                result = await test.run_test_mode(mock_args)

                assert result == 1
                mock_print.assert_called_with(expected_message)
