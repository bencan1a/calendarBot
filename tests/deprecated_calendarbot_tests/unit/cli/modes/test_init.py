"""Unit tests for the CLI modes initialization module.

Tests cover mode registration, retrieval, execution, and error handling.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.cli.modes import (
    MODE_REGISTRY,
    execute_mode,
    get_available_modes,
    get_mode_handler,
    register_mode,
)


@pytest.fixture
def mock_mode_registry() -> dict[str, dict[str, Any]]:
    """Create a mock mode registry for testing.

    Returns:
        Dict[str, Dict[str, Any]]: A mock mode registry with test modes.
    """
    return {
        "test_mode": {
            "name": "Test Mode",
            "description": "Test mode description",
            "handler": MagicMock(),
            "requires_display": False,
            "async_mode": True,
        },
        "sync_mode": {
            "name": "Sync Mode",
            "description": "Sync mode description",
            "handler": MagicMock(),
            "requires_display": True,
            "async_mode": False,
        },
    }


@pytest.fixture
def mock_args() -> MagicMock:
    """Create a mock args object for testing.

    Returns:
        MagicMock: A mock args object.
    """
    return MagicMock()


class TestGetAvailableModes:
    """Tests for the get_available_modes function."""

    def test_get_available_modes_when_called_then_returns_copy_of_registry(self) -> None:
        """Test that get_available_modes returns a copy of the mode registry."""
        # Setup
        original_registry = {"mode1": {"name": "Mode 1"}}

        with patch("calendarbot.cli.modes.MODE_REGISTRY", original_registry):
            # Execute
            result = get_available_modes()

            # Verify
            assert result == original_registry
            assert result is not original_registry  # Should be a copy


class TestRegisterMode:
    """Tests for the register_mode function."""

    def test_register_mode_when_basic_params_then_registers_with_defaults(self) -> None:
        """Test mode registration with basic parameters."""
        # Setup
        test_registry = {}
        mock_handler = MagicMock()

        with patch("calendarbot.cli.modes.MODE_REGISTRY", test_registry):
            # Execute
            register_mode("test_mode", mock_handler)

            # Verify
            assert "test_mode" in test_registry
            # Fix for capitalization issue - match actual implementation
            assert test_registry["test_mode"]["name"] == "Test_Mode"
            assert test_registry["test_mode"]["description"] == "test_mode mode"
            assert test_registry["test_mode"]["handler"] == mock_handler
            assert test_registry["test_mode"]["requires_display"] is False
            assert test_registry["test_mode"]["async_mode"] is True

    def test_register_mode_when_custom_params_then_registers_with_custom_values(self) -> None:
        """Test mode registration with custom parameters."""
        # Setup
        test_registry = {}
        mock_handler = MagicMock()

        with patch("calendarbot.cli.modes.MODE_REGISTRY", test_registry):
            # Execute
            register_mode(
                "custom_mode",
                mock_handler,
                display_name="Custom Display Name",
                description="Custom description",
                requires_display=True,
                async_mode=False,
                custom_param="custom_value",
            )

            # Verify
            assert "custom_mode" in test_registry
            assert test_registry["custom_mode"]["name"] == "Custom Display Name"
            assert test_registry["custom_mode"]["description"] == "Custom description"
            assert test_registry["custom_mode"]["handler"] == mock_handler
            assert test_registry["custom_mode"]["requires_display"] is True
            assert test_registry["custom_mode"]["async_mode"] is False
            assert test_registry["custom_mode"]["custom_param"] == "custom_value"


class TestGetModeHandler:
    """Tests for the get_mode_handler function."""

    def test_get_mode_handler_when_mode_exists_then_returns_handler(
        self, mock_mode_registry: dict[str, dict[str, Any]]
    ) -> None:
        """Test handler retrieval for existing mode."""
        # Setup
        with patch("calendarbot.cli.modes.MODE_REGISTRY", mock_mode_registry):
            # Execute
            handler = get_mode_handler("test_mode")

            # Verify
            assert handler == mock_mode_registry["test_mode"]["handler"]

    def test_get_mode_handler_when_mode_does_not_exist_then_raises_key_error(
        self, mock_mode_registry: dict[str, dict[str, Any]]
    ) -> None:
        """Test handler retrieval for non-existent mode."""
        # Setup
        with patch("calendarbot.cli.modes.MODE_REGISTRY", mock_mode_registry):
            # Execute and verify
            with pytest.raises(KeyError, match="Unknown mode: unknown_mode"):
                get_mode_handler("unknown_mode")

    def test_get_mode_handler_when_handler_is_none_then_raises_runtime_error(
        self, mock_mode_registry: dict[str, dict[str, Any]]
    ) -> None:
        """Test handler retrieval when handler is None."""
        # Setup
        mock_mode_registry["none_handler_mode"] = {
            "name": "None Handler Mode",
            "description": "Mode with None handler",
            "handler": None,
            "requires_display": False,
            "async_mode": True,
        }

        with patch("calendarbot.cli.modes.MODE_REGISTRY", mock_mode_registry):
            # Execute and verify
            with pytest.raises(
                RuntimeError, match="Handler not yet migrated for mode: none_handler_mode"
            ):
                get_mode_handler("none_handler_mode")


class TestExecuteMode:
    """Tests for the execute_mode function."""

    @pytest.mark.asyncio
    async def test_execute_mode_when_async_mode_then_executes_async_handler(
        self, mock_mode_registry: dict[str, dict[str, Any]], mock_args: MagicMock
    ) -> None:
        """Test execution of async mode."""
        # Setup
        async_handler = AsyncMock()
        async_handler.return_value = 0
        mock_mode_registry["test_mode"]["handler"] = async_handler

        with (
            patch("calendarbot.cli.modes.MODE_REGISTRY", mock_mode_registry),
            patch("calendarbot.cli.modes.get_mode_handler", return_value=async_handler),
        ):
            # Execute
            result = await execute_mode("test_mode", mock_args)

            # Verify
            assert result == 0
            async_handler.assert_called_once_with(mock_args)

    @pytest.mark.asyncio
    async def test_execute_mode_when_sync_mode_then_executes_sync_handler(
        self, mock_mode_registry: dict[str, dict[str, Any]], mock_args: MagicMock
    ) -> None:
        """Test execution of sync mode."""
        # Setup
        sync_handler = MagicMock()
        sync_handler.return_value = 0
        mock_mode_registry["sync_mode"]["handler"] = sync_handler

        with (
            patch("calendarbot.cli.modes.MODE_REGISTRY", mock_mode_registry),
            patch("calendarbot.cli.modes.get_mode_handler", return_value=sync_handler),
        ):
            # Execute
            result = await execute_mode("sync_mode", mock_args)

            # Verify
            assert result == 0
            sync_handler.assert_called_once_with(mock_args)

    @pytest.mark.asyncio
    async def test_execute_mode_when_handler_returns_none_then_returns_zero(
        self, mock_mode_registry: dict[str, dict[str, Any]], mock_args: MagicMock
    ) -> None:
        """Test execution when handler returns None."""
        # Setup
        async_handler = AsyncMock()
        async_handler.return_value = None
        mock_mode_registry["test_mode"]["handler"] = async_handler

        with (
            patch("calendarbot.cli.modes.MODE_REGISTRY", mock_mode_registry),
            patch("calendarbot.cli.modes.get_mode_handler", return_value=async_handler),
        ):
            # Execute
            result = await execute_mode("test_mode", mock_args)

            # Verify
            assert result == 0
            async_handler.assert_called_once_with(mock_args)

    @pytest.mark.asyncio
    async def test_execute_mode_when_unknown_mode_then_returns_one(
        self, mock_mode_registry: dict[str, dict[str, Any]], mock_args: MagicMock
    ) -> None:
        """Test execution with unknown mode."""
        # Setup
        with (
            patch("calendarbot.cli.modes.MODE_REGISTRY", mock_mode_registry),
            patch(
                "calendarbot.cli.modes.get_mode_handler",
                side_effect=KeyError("Unknown mode: unknown_mode"),
            ),
        ):
            # Execute
            result = await execute_mode("unknown_mode", mock_args)

            # Verify
            assert result == 1

    @pytest.mark.asyncio
    async def test_execute_mode_when_handler_not_migrated_then_returns_one(
        self, mock_mode_registry: dict[str, dict[str, Any]], mock_args: MagicMock
    ) -> None:
        """Test execution when handler is not migrated."""
        # Setup
        with (
            patch("calendarbot.cli.modes.MODE_REGISTRY", mock_mode_registry),
            patch(
                "calendarbot.cli.modes.get_mode_handler",
                side_effect=RuntimeError("Handler not yet migrated for mode: test_mode"),
            ),
        ):
            # Execute
            result = await execute_mode("test_mode", mock_args)

            # Verify
            assert result == 1

    @pytest.mark.asyncio
    async def test_execute_mode_when_general_exception_then_returns_one(
        self, mock_mode_registry: dict[str, dict[str, Any]], mock_args: MagicMock
    ) -> None:
        """Test execution with general exception."""
        # Setup
        async_handler = AsyncMock()
        async_handler.side_effect = Exception("Test error")
        mock_mode_registry["test_mode"]["handler"] = async_handler

        with (
            patch("calendarbot.cli.modes.MODE_REGISTRY", mock_mode_registry),
            patch("calendarbot.cli.modes.get_mode_handler", return_value=async_handler),
        ):
            # Execute
            result = await execute_mode("test_mode", mock_args)

            # Verify
            assert result == 1
            async_handler.assert_called_once_with(mock_args)


class TestModeRegistry:
    """Tests for the MODE_REGISTRY constant."""

    def test_mode_registry_when_initialized_then_contains_expected_modes(self) -> None:
        """Test that MODE_REGISTRY contains expected modes."""
        # Verify
        assert "web" in MODE_REGISTRY
        assert "epaper" in MODE_REGISTRY
        # Verify only expected modes exist
        assert len(MODE_REGISTRY) == 2

        # Check structure of a mode entry
        for mode_name, mode_info in MODE_REGISTRY.items():
            assert "name" in mode_info
            assert "description" in mode_info
            assert "handler" in mode_info
            assert "requires_display" in mode_info
            assert "async_mode" in mode_info
