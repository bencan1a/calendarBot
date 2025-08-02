"""Unit tests for the test CLI mode.

Tests cover validation runner integration, return codes, and error handling.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pytest

from calendarbot.cli.modes.test import run_test_mode


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create a mock settings object for testing.
    
    Returns:
        MagicMock: A mock settings object with required attributes.
    """
    settings = MagicMock()
    settings.runtime_tracking = MagicMock()
    settings.runtime_tracking.session_name = "test_session"
    return settings


@pytest.fixture
def mock_args() -> MagicMock:
    """Create a mock args object for testing.
    
    Returns:
        MagicMock: A mock args object with required attributes.
    """
    args = MagicMock()
    args.date = None
    args.end_date = None
    args.components = ["sources", "cache", "display"]
    args.no_cache = False
    args.output_format = "console"
    args.verbose = False
    return args


@pytest.fixture
def mock_validation_results() -> MagicMock:
    """Create a mock validation results object for testing.
    
    Returns:
        MagicMock: A mock validation results object.
    """
    results = MagicMock()
    results.has_failures.return_value = False
    results.has_warnings.return_value = False
    return results


class TestRunTestMode:
    """Tests for the run_test_mode function."""

    @pytest.mark.asyncio
    async def test_run_test_mode_when_successful_then_returns_zero(
        self, mock_args: MagicMock, mock_settings: MagicMock, mock_validation_results: MagicMock
    ) -> None:
        """Test successful test mode execution."""
        # Setup
        with patch("calendarbot.cli.modes.test.apply_command_line_overrides") as mock_apply_cmd_overrides, \
             patch("calendarbot.cli.modes.test.apply_cli_overrides") as mock_apply_cli_overrides, \
             patch("calendarbot.cli.modes.test.setup_enhanced_logging") as mock_setup_logging, \
             patch("calendarbot.cli.modes.test.create_runtime_tracker") as mock_create_tracker, \
             patch("calendarbot.cli.modes.test.start_runtime_tracking") as mock_start_tracking, \
             patch("calendarbot.cli.modes.test.stop_runtime_tracking") as mock_stop_tracking, \
             patch("calendarbot.cli.modes.test.ValidationRunner") as mock_validation_runner, \
             patch("calendarbot.cli.modes.test.settings", mock_settings):
            
            # Mock the chain of settings updates
            mock_apply_cmd_overrides.return_value = mock_settings
            mock_apply_cli_overrides.return_value = mock_settings
            
            # Mock runtime tracker
            mock_tracker = MagicMock()
            mock_create_tracker.return_value = mock_tracker
            
            # Mock validation runner
            mock_runner_instance = MagicMock()
            mock_runner_instance.run_validation.return_value = asyncio.Future()
            mock_runner_instance.run_validation.return_value.set_result(mock_validation_results)
            mock_validation_runner.return_value = mock_runner_instance
            
            # Execute
            result = await run_test_mode(mock_args)
            
            # Verify
            assert result == 0
            mock_apply_cmd_overrides.assert_called_once_with(mock_settings, mock_args)
            mock_apply_cli_overrides.assert_called_once_with(mock_settings, mock_args)
            mock_setup_logging.assert_called_once()
            mock_create_tracker.assert_called_once_with(mock_settings)
            mock_start_tracking.assert_called_once_with(mock_tracker, "test_mode", "test_session")
            mock_validation_runner.assert_called_once()
            mock_runner_instance.run_validation.assert_called_once()
            mock_runner_instance.print_results.assert_called_once_with(verbose=False)
            mock_stop_tracking.assert_called_once_with(mock_tracker, "test_mode")

    @pytest.mark.asyncio
    async def test_run_test_mode_when_validation_has_failures_then_returns_one(
        self, mock_args: MagicMock, mock_settings: MagicMock, mock_validation_results: MagicMock
    ) -> None:
        """Test test mode with validation failures."""
        # Setup
        mock_validation_results.has_failures.return_value = True
        
        with patch("calendarbot.cli.modes.test.apply_command_line_overrides") as mock_apply_cmd_overrides, \
             patch("calendarbot.cli.modes.test.apply_cli_overrides") as mock_apply_cli_overrides, \
             patch("calendarbot.cli.modes.test.setup_enhanced_logging") as mock_setup_logging, \
             patch("calendarbot.cli.modes.test.create_runtime_tracker") as mock_create_tracker, \
             patch("calendarbot.cli.modes.test.start_runtime_tracking") as mock_start_tracking, \
             patch("calendarbot.cli.modes.test.stop_runtime_tracking") as mock_stop_tracking, \
             patch("calendarbot.cli.modes.test.ValidationRunner") as mock_validation_runner, \
             patch("calendarbot.cli.modes.test.settings", mock_settings):
            
            # Mock the chain of settings updates
            mock_apply_cmd_overrides.return_value = mock_settings
            mock_apply_cli_overrides.return_value = mock_settings
            
            # Mock runtime tracker
            mock_tracker = MagicMock()
            mock_create_tracker.return_value = mock_tracker
            
            # Mock validation runner
            mock_runner_instance = MagicMock()
            mock_runner_instance.run_validation.return_value = asyncio.Future()
            mock_runner_instance.run_validation.return_value.set_result(mock_validation_results)
            mock_validation_runner.return_value = mock_runner_instance
            
            # Execute
            result = await run_test_mode(mock_args)
            
            # Verify
            assert result == 1
            mock_runner_instance.run_validation.assert_called_once()
            mock_runner_instance.print_results.assert_called_once_with(verbose=False)

    @pytest.mark.asyncio
    async def test_run_test_mode_when_validation_has_warnings_then_returns_zero(
        self, mock_args: MagicMock, mock_settings: MagicMock, mock_validation_results: MagicMock
    ) -> None:
        """Test test mode with validation warnings."""
        # Setup
        mock_validation_results.has_failures.return_value = False
        mock_validation_results.has_warnings.return_value = True
        
        with patch("calendarbot.cli.modes.test.apply_command_line_overrides") as mock_apply_cmd_overrides, \
             patch("calendarbot.cli.modes.test.apply_cli_overrides") as mock_apply_cli_overrides, \
             patch("calendarbot.cli.modes.test.setup_enhanced_logging") as mock_setup_logging, \
             patch("calendarbot.cli.modes.test.create_runtime_tracker") as mock_create_tracker, \
             patch("calendarbot.cli.modes.test.start_runtime_tracking") as mock_start_tracking, \
             patch("calendarbot.cli.modes.test.stop_runtime_tracking") as mock_stop_tracking, \
             patch("calendarbot.cli.modes.test.ValidationRunner") as mock_validation_runner, \
             patch("calendarbot.cli.modes.test.settings", mock_settings):
            
            # Mock the chain of settings updates
            mock_apply_cmd_overrides.return_value = mock_settings
            mock_apply_cli_overrides.return_value = mock_settings
            
            # Mock runtime tracker
            mock_tracker = MagicMock()
            mock_create_tracker.return_value = mock_tracker
            
            # Mock validation runner
            mock_runner_instance = MagicMock()
            mock_runner_instance.run_validation.return_value = asyncio.Future()
            mock_runner_instance.run_validation.return_value.set_result(mock_validation_results)
            mock_validation_runner.return_value = mock_runner_instance
            
            # Execute
            result = await run_test_mode(mock_args)
            
            # Verify
            assert result == 0  # Warnings don't cause failure
            mock_runner_instance.run_validation.assert_called_once()
            mock_runner_instance.print_results.assert_called_once_with(verbose=False)

    @pytest.mark.asyncio
    async def test_run_test_mode_when_runtime_tracking_disabled_then_skips_tracking(
        self, mock_args: MagicMock
    ) -> None:
        """Test test mode with runtime tracking disabled."""
        # Setup
        mock_settings = MagicMock()
        mock_settings.runtime_tracking = None  # Disabled
        
        with patch("calendarbot.cli.modes.test.apply_command_line_overrides") as mock_apply_cmd_overrides, \
             patch("calendarbot.cli.modes.test.apply_cli_overrides") as mock_apply_cli_overrides, \
             patch("calendarbot.cli.modes.test.setup_enhanced_logging") as mock_setup_logging, \
             patch("calendarbot.cli.modes.test.create_runtime_tracker") as mock_create_tracker, \
             patch("calendarbot.cli.modes.test.start_runtime_tracking") as mock_start_tracking, \
             patch("calendarbot.cli.modes.test.stop_runtime_tracking") as mock_stop_tracking, \
             patch("calendarbot.cli.modes.test.ValidationRunner") as mock_validation_runner, \
             patch("calendarbot.cli.modes.test.settings", MagicMock()):
            
            # Mock the chain of settings updates
            mock_apply_cmd_overrides.return_value = mock_settings
            mock_apply_cli_overrides.return_value = mock_settings
            
            # Mock runtime tracker
            mock_create_tracker.return_value = None  # No tracker
            
            # Mock validation runner
            mock_runner_instance = MagicMock()
            mock_validation_results = MagicMock()
            mock_validation_results.has_failures.return_value = False
            mock_validation_results.has_warnings.return_value = False
            mock_runner_instance.run_validation.return_value = asyncio.Future()
            mock_runner_instance.run_validation.return_value.set_result(mock_validation_results)
            mock_validation_runner.return_value = mock_runner_instance
            
            # Execute
            result = await run_test_mode(mock_args)
            
            # Verify
            assert result == 0
            mock_start_tracking.assert_not_called()
            mock_stop_tracking.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_test_mode_when_keyboard_interrupt_then_returns_one(
        self, mock_args: MagicMock
    ) -> None:
        """Test test mode with keyboard interrupt."""
        # Setup
        with patch("calendarbot.cli.modes.test.apply_command_line_overrides") as mock_apply_cmd_overrides:
            mock_apply_cmd_overrides.side_effect = KeyboardInterrupt()
            
            # Execute
            result = await run_test_mode(mock_args)
            
            # Verify
            assert result == 1

    @pytest.mark.asyncio
    async def test_run_test_mode_when_import_error_then_returns_one(
        self, mock_args: MagicMock
    ) -> None:
        """Test test mode with import error."""
        # Setup
        with patch("calendarbot.cli.modes.test.apply_command_line_overrides") as mock_apply_cmd_overrides:
            mock_apply_cmd_overrides.side_effect = ImportError("Missing module")
            
            # Execute
            result = await run_test_mode(mock_args)
            
            # Verify
            assert result == 1

    @pytest.mark.asyncio
    async def test_run_test_mode_when_general_exception_then_returns_one(
        self, mock_args: MagicMock
    ) -> None:
        """Test test mode with general exception."""
        # Setup
        with patch("calendarbot.cli.modes.test.apply_command_line_overrides") as mock_apply_cmd_overrides:
            mock_apply_cmd_overrides.side_effect = Exception("Test error")
            
            # Execute
            result = await run_test_mode(mock_args)
            
            # Verify
            assert result == 1

    @pytest.mark.asyncio
    async def test_run_test_mode_when_custom_args_then_passes_to_validation_runner(
        self, mock_settings: MagicMock
    ) -> None:
        """Test test mode with custom arguments."""
        # Setup
        args = MagicMock()
        args.date = "2025-08-01"
        args.end_date = "2025-08-02"
        args.components = ["sources"]
        args.no_cache = True
        args.output_format = "json"
        args.verbose = True
        
        with patch("calendarbot.cli.modes.test.apply_command_line_overrides") as mock_apply_cmd_overrides, \
             patch("calendarbot.cli.modes.test.apply_cli_overrides") as mock_apply_cli_overrides, \
             patch("calendarbot.cli.modes.test.setup_enhanced_logging"), \
             patch("calendarbot.cli.modes.test.create_runtime_tracker") as mock_create_tracker, \
             patch("calendarbot.cli.modes.test.start_runtime_tracking"), \
             patch("calendarbot.cli.modes.test.stop_runtime_tracking"), \
             patch("calendarbot.cli.modes.test.ValidationRunner") as mock_validation_runner, \
             patch("calendarbot.cli.modes.test.settings", mock_settings):
            
            # Mock the chain of settings updates
            mock_apply_cmd_overrides.return_value = mock_settings
            mock_apply_cli_overrides.return_value = mock_settings
            
            # Mock runtime tracker
            mock_tracker = MagicMock()
            mock_create_tracker.return_value = mock_tracker
            
            # Mock validation runner
            mock_runner_instance = MagicMock()
            mock_validation_results = MagicMock()
            mock_validation_results.has_failures.return_value = False
            mock_validation_results.has_warnings.return_value = False
            mock_runner_instance.run_validation.return_value = asyncio.Future()
            mock_runner_instance.run_validation.return_value.set_result(mock_validation_results)
            mock_validation_runner.return_value = mock_runner_instance
            
            # Execute
            await run_test_mode(args)
            
            # Verify
            mock_validation_runner.assert_called_once_with(
                test_date="2025-08-01",
                end_date="2025-08-02",
                components=["sources"],
                use_cache=False,  # no_cache=True
                output_format="json"
            )
            mock_runner_instance.print_results.assert_called_once_with(verbose=True)