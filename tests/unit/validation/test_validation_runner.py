"""Minimal tests for ValidationRunner - module not actively used."""

from unittest.mock import AsyncMock, patch

import pytest

from calendarbot.validation.results import ValidationResults
from calendarbot.validation.runner import ValidationRunner


class TestValidationRunnerMinimal:
    """Minimal test coverage for ValidationRunner since module is unused."""

    def test_init_basic(self, test_settings) -> None:
        """Test basic ValidationRunner initialization."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                runner = ValidationRunner()
                assert isinstance(runner.results, ValidationResults)
                assert runner.components == ["sources", "cache", "display"]

    @pytest.mark.asyncio
    async def test_run_validation_basic(self, test_settings) -> None:
        """Test basic run_validation workflow."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                runner = ValidationRunner()

                # Mock all async methods
                with (
                    patch.object(runner, "_initialize_components", new_callable=AsyncMock),
                    patch.object(runner, "_validate_source_connectivity", new_callable=AsyncMock),
                    patch.object(runner, "_validate_cache_operations", new_callable=AsyncMock),
                    patch.object(runner, "_validate_display_functionality", new_callable=AsyncMock),
                    patch.object(runner, "_cleanup_components", new_callable=AsyncMock),
                ):
                    result = await runner.run_validation()
                    assert isinstance(result, ValidationResults)
