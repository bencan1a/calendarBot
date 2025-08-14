"""Unit tests for ValidationRunner core initialization and basic workflow components."""

import asyncio
import time
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.validation.results import ValidationResults, ValidationStatus
from calendarbot.validation.runner import ValidationRunner


class TestValidationRunnerInitialization:
    """Test ValidationRunner.__init__() and basic setup."""

    def test_init_with_defaults(self, test_settings: Any) -> None:
        """Test ValidationRunner initialization with default parameters."""
        with patch("calendarbot.validation.runner.get_validation_logger") as mock_logger:
            with patch("calendarbot.validation.runner.settings", test_settings):
                runner = ValidationRunner()

                # Verify default parameter assignments
                assert runner.test_date.hour == 0
                assert runner.test_date.minute == 0
                assert runner.test_date.second == 0
                assert runner.test_date.microsecond == 0
                assert runner.end_date == runner.test_date
                assert runner.components == ["sources", "cache", "display"]
                assert runner.use_cache is True
                assert runner.output_format == "console"
                assert runner.settings == test_settings

                # Verify ValidationResults instantiation
                assert isinstance(runner.results, ValidationResults)

                # Verify component instances initialized to None
                assert runner.source_manager is None
                assert runner.cache_manager is None
                assert runner.display_manager is None

                # Verify logger setup
                mock_logger.assert_called_once_with("validation")
                assert runner.logger == mock_logger.return_value

    def test_init_with_custom_parameters(self, test_settings: Any) -> None:
        """Test ValidationRunner initialization with custom parameters."""
        test_date = datetime(2024, 1, 15, 14, 30, 0)
        end_date = datetime(2024, 1, 16, 14, 30, 0)
        components = ["sources", "cache"]

        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                runner = ValidationRunner(
                    test_date=test_date,
                    end_date=end_date,
                    components=components,
                    use_cache=False,
                    output_format="json",
                )

                # Verify custom parameter assignments
                assert runner.test_date == test_date
                assert runner.end_date == end_date
                assert runner.components == components
                assert runner.use_cache is False
                assert runner.output_format == "json"

    def test_init_with_none_parameters(self, test_settings: Any) -> None:
        """Test ValidationRunner initialization with None parameters to verify defaults."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                runner = ValidationRunner(test_date=None, end_date=None, components=None)

                # Verify None parameters are handled with defaults
                assert runner.test_date is not None
                assert runner.end_date == runner.test_date
                assert runner.components == ["sources", "cache", "display"]

    def test_init_date_normalization(self, test_settings: Any) -> None:
        """Test that test_date is normalized to start of day."""
        test_date = datetime(2024, 1, 15, 14, 30, 45, 123456)

        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                runner = ValidationRunner(test_date=test_date)

                # Verify date normalization (only when test_date is None, actual dates are preserved)
                assert runner.test_date == test_date

                # Test with None to see normalization
                runner2 = ValidationRunner(test_date=None)
                assert runner2.test_date.hour == 0
                assert runner2.test_date.minute == 0
                assert runner2.test_date.second == 0
                assert runner2.test_date.microsecond == 0

    @pytest.mark.parametrize(
        "components,expected",
        [
            (["sources"], ["sources"]),
            (["cache", "display"], ["cache", "display"]),
            (["sources", "cache", "display"], ["sources", "cache", "display"]),
            ([], ["sources", "cache", "display"]),  # Empty list defaults to all components
        ],
    )
    def test_init_component_combinations(
        self, test_settings: Any, components: Any, expected: Any
    ) -> None:
        """Test ValidationRunner initialization with various component combinations."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                runner = ValidationRunner(components=components)

                assert runner.components == expected

    @pytest.mark.parametrize("output_format", ["console", "json", "xml", "custom"])
    def test_init_output_formats(self, test_settings: Any, output_format: Any) -> None:
        """Test ValidationRunner initialization with various output formats."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                runner = ValidationRunner(output_format=output_format)

                assert runner.output_format == output_format

    def test_init_logging_calls(self, test_settings: Any) -> None:
        """Test that initialization performs expected logging calls."""
        with patch("calendarbot.validation.runner.get_validation_logger") as mock_get_logger:
            mock_logger = mock_get_logger.return_value
            with patch("calendarbot.validation.runner.settings", test_settings):
                test_date = datetime(2024, 1, 15)
                end_date = datetime(2024, 1, 16)
                components = ["sources", "cache"]

                ValidationRunner(test_date=test_date, end_date=end_date, components=components)

                # Verify logger calls
                expected_calls = [
                    f"ValidationRunner initialized for {test_date.date()}",
                    f"Date range: {test_date.date()} to {end_date.date()}",
                    f"Components to test: {', '.join(components)}",
                ]

                assert mock_logger.info.call_count == 3
                actual_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                assert actual_calls == expected_calls

    def test_init_single_date_no_range_logging(self, test_settings: Any) -> None:
        """Test logging when end_date equals test_date (no range)."""
        with patch("calendarbot.validation.runner.get_validation_logger") as mock_get_logger:
            mock_logger = mock_get_logger.return_value
            with patch("calendarbot.validation.runner.settings", test_settings):
                test_date = datetime(2024, 1, 15)

                ValidationRunner(test_date=test_date, end_date=test_date)

                # Should not log date range when end_date == test_date
                assert mock_logger.info.call_count == 2  # Only init and components, not range
                calls = [call[0][0] for call in mock_logger.info.call_args_list]
                assert any("Date range:" in call for call in calls) == False


class TestValidationRunnerBasicMethods:
    """Test basic ValidationRunner methods that don't require async operations."""

    @pytest.fixture
    def runner_with_mocks(self, test_settings: Any) -> Any:
        """Create ValidationRunner with mocked dependencies."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                return ValidationRunner()

    def test_get_results_returns_validation_results(self, runner_with_mocks: Any) -> None:
        """Test that get_results() returns the ValidationResults instance."""
        runner = runner_with_mocks

        results = runner.get_results()

        assert isinstance(results, ValidationResults)
        assert results is runner.results

    def test_print_results_console_format(self, runner_with_mocks: Any) -> None:
        """Test print_results() with console format."""
        runner = runner_with_mocks
        runner.output_format = "console"

        # Mock the results object
        mock_results = MagicMock()
        runner.results = mock_results

        runner.print_results(verbose=False)

        mock_results.print_console_report.assert_called_once_with(False)
        mock_results.print_json_report.assert_not_called()

    def test_print_results_console_format_verbose(self, runner_with_mocks: Any) -> None:
        """Test print_results() with console format and verbose flag."""
        runner = runner_with_mocks
        runner.output_format = "console"

        # Mock the results object
        mock_results = MagicMock()
        runner.results = mock_results

        runner.print_results(verbose=True)

        mock_results.print_console_report.assert_called_once_with(True)
        mock_results.print_json_report.assert_not_called()

    def test_print_results_json_format(self, runner_with_mocks: Any) -> None:
        """Test print_results() with JSON format."""
        runner = runner_with_mocks
        runner.output_format = "json"

        # Mock the results object
        mock_results = MagicMock()
        runner.results = mock_results

        runner.print_results(verbose=False)

        mock_results.print_json_report.assert_called_once()
        mock_results.print_console_report.assert_not_called()

    def test_print_results_json_format_ignores_verbose(self, runner_with_mocks: Any) -> None:
        """Test print_results() with JSON format ignores verbose flag."""
        runner = runner_with_mocks
        runner.output_format = "json"

        # Mock the results object
        mock_results = MagicMock()
        runner.results = mock_results

        runner.print_results(verbose=True)

        mock_results.print_json_report.assert_called_once()
        mock_results.print_console_report.assert_not_called()


class TestValidationRunnerResultsIntegration:
    """Test ValidationRunner integration with ValidationResults."""

    @pytest.fixture
    def runner_with_real_results(self, test_settings: Any) -> Any:
        """Create ValidationRunner with real ValidationResults for testing."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                return ValidationRunner()

    def test_results_initialization(self, runner_with_real_results: Any) -> None:
        """Test that ValidationResults is properly initialized."""
        runner = runner_with_real_results

        assert isinstance(runner.results, ValidationResults)
        assert len(runner.results.items) == 0
        assert runner.results.start_time is not None
        assert runner.results.end_time is None
        assert len(runner.results.components_tested) == 0

    def test_results_add_success_integration(self, runner_with_real_results: Any) -> None:
        """Test adding success results through ValidationResults."""
        runner = runner_with_real_results

        runner.results.add_success(
            "sources",
            "test_component_init",
            "Component initialized successfully",
            {"test_detail": "value"},
            150,
        )

        assert len(runner.results.items) == 1
        item = runner.results.items[0]
        assert item.component == "sources"
        assert item.test_name == "test_component_init"
        assert item.status == ValidationStatus.SUCCESS
        assert item.message == "Component initialized successfully"
        assert item.details == {"test_detail": "value"}
        assert item.duration_ms == 150
        assert "sources" in runner.results.components_tested

    def test_results_add_failure_integration(self, runner_with_real_results: Any) -> None:
        """Test adding failure results through ValidationResults."""
        runner = runner_with_real_results

        runner.results.add_failure(
            "cache",
            "test_cache_init",
            "Cache initialization failed",
            {"error": "Connection timeout"},
            300,
        )

        assert len(runner.results.items) == 1
        item = runner.results.items[0]
        assert item.component == "cache"
        assert item.test_name == "test_cache_init"
        assert item.status == ValidationStatus.FAILURE
        assert item.message == "Cache initialization failed"
        assert item.details == {"error": "Connection timeout"}
        assert item.duration_ms == 300
        assert "cache" in runner.results.components_tested

    def test_results_add_warning_integration(self, runner_with_real_results: Any) -> None:
        """Test adding warning results through ValidationResults."""
        runner = runner_with_real_results

        runner.results.add_warning(
            "display",
            "test_display_config",
            "Display type not optimal",
            {"display_type": "console"},
            75,
        )

        assert len(runner.results.items) == 1
        item = runner.results.items[0]
        assert item.component == "display"
        assert item.test_name == "test_display_config"
        assert item.status == ValidationStatus.WARNING
        assert item.message == "Display type not optimal"
        assert item.details == {"display_type": "console"}
        assert item.duration_ms == 75
        assert "display" in runner.results.components_tested

    def test_results_multiple_components(self, runner_with_real_results: Any) -> None:
        """Test results tracking across multiple components."""
        runner = runner_with_real_results

        # Add results for different components
        runner.results.add_success("sources", "source_test", "Source OK")
        runner.results.add_failure("cache", "cache_test", "Cache failed")
        runner.results.add_warning("display", "display_test", "Display warning")
        runner.results.add_success("sources", "source_test2", "Source OK again")

        assert len(runner.results.items) == 4
        assert len(runner.results.components_tested) == 3
        assert "sources" in runner.results.components_tested
        assert "cache" in runner.results.components_tested
        assert "display" in runner.results.components_tested

    def test_results_finalize_integration(self, runner_with_real_results: Any) -> None:
        """Test results finalization."""
        runner = runner_with_real_results

        # Add some results
        runner.results.add_success("sources", "test", "Test passed")

        # Initially end_time should be None
        assert runner.results.end_time is None

        # Finalize results
        runner.results.finalize()

        # After finalization, end_time should be set
        assert runner.results.end_time is not None
        assert runner.results.end_time >= runner.results.start_time  # type: ignore

    def test_results_summary_integration(self, runner_with_real_results: Any) -> None:
        """Test results summary generation."""
        runner = runner_with_real_results

        # Add various results
        runner.results.add_success("sources", "test1", "Test 1 passed")
        runner.results.add_failure("cache", "test2", "Test 2 failed")
        runner.results.add_warning("display", "test3", "Test 3 warning")
        runner.results.add_success("sources", "test4", "Test 4 passed")

        summary = runner.results.get_summary()

        assert summary["total_tests"] == 4
        assert summary["status_counts"]["success"] == 2
        assert summary["status_counts"]["failure"] == 1
        assert summary["status_counts"]["warning"] == 1
        assert summary["status_counts"]["skipped"] == 0
        assert summary["success_rate"] == 0.5  # 2 out of 4 successful
        assert len(summary["components_tested"]) == 3


class TestValidationRunnerComponentValidation:
    """Test ValidationRunner component validation logic (without async operations)."""

    @pytest.fixture
    def runner_with_mocks(self, test_settings: Any) -> Any:
        """Create ValidationRunner with mocked dependencies."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                return ValidationRunner()

    def test_component_instances_initially_none(self, runner_with_mocks: Any) -> None:
        """Test that component instances are initially None."""
        runner = runner_with_mocks

        assert runner.source_manager is None
        assert runner.cache_manager is None
        assert runner.display_manager is None

    def test_component_assignment(self, runner_with_mocks: Any) -> None:
        """Test manual component assignment for validation."""
        runner = runner_with_mocks

        # Manually assign mock components
        mock_source = MagicMock()
        mock_cache = MagicMock()
        mock_display = MagicMock()

        runner.source_manager = mock_source
        runner.cache_manager = mock_cache
        runner.display_manager = mock_display

        assert runner.source_manager is mock_source
        assert runner.cache_manager is mock_cache
        assert runner.display_manager is mock_display

    def test_component_boolean_evaluation(self, runner_with_mocks: Any) -> None:
        """Test component boolean evaluation for validation checks."""
        runner = runner_with_mocks

        # Test None components evaluate to False
        assert not bool(runner.source_manager)
        assert not bool(runner.cache_manager)
        assert not bool(runner.display_manager)

        # Test assigned components evaluate to True
        runner.source_manager = MagicMock()
        runner.cache_manager = MagicMock()
        runner.display_manager = MagicMock()

        assert bool(runner.source_manager)
        assert bool(runner.cache_manager)
        assert bool(runner.display_manager)

    @pytest.mark.parametrize(
        "component_name,components_list",
        [
            ("sources", ["sources"]),
            ("cache", ["cache"]),
            ("display", ["display"]),
            ("sources", ["sources", "cache"]),
            ("cache", ["sources", "cache", "display"]),
        ],
    )
    def test_component_inclusion_check(
        self, test_settings: Any, component_name: Any, components_list: Any
    ) -> None:
        """Test component inclusion logic for validation flow."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                runner = ValidationRunner(components=components_list)

                # Test that component is correctly identified as included
                assert component_name in runner.components

    @pytest.mark.parametrize(
        "component_name,components_list",
        [
            ("sources", ["cache", "display"]),
            ("cache", ["sources", "display"]),
            ("display", ["sources", "cache"]),
        ],
    )
    def test_component_exclusion_check(
        self, test_settings: Any, component_name: Any, components_list: Any
    ) -> None:
        """Test component exclusion logic for validation flow."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                runner = ValidationRunner(components=components_list)

                # Test that component is correctly identified as excluded
                assert component_name not in runner.components

    def test_empty_components_defaults_to_all(self, test_settings: Any) -> None:
        """Test that empty components list defaults to all components."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                runner = ValidationRunner(components=[])

                # Empty list should default to all components
                assert runner.components == ["sources", "cache", "display"]


class TestValidationRunnerErrorHandling:
    """Test ValidationRunner error handling in initialization and basic operations."""

    def test_init_with_invalid_settings(self) -> None:
        """Test initialization with invalid settings object."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", None):
                # Should not raise exception, but settings should be None
                runner = ValidationRunner()
                assert runner.settings is None

    def test_init_logger_exception_handling(self, test_settings: Any) -> None:
        """Test initialization when logger setup fails."""
        with patch("calendarbot.validation.runner.get_validation_logger") as mock_get_logger:
            mock_get_logger.side_effect = Exception("Logger setup failed")
            with patch("calendarbot.validation.runner.settings", test_settings):
                # Should raise the exception since logger setup is critical
                with pytest.raises(Exception, match="Logger setup failed"):
                    ValidationRunner()

    def test_results_operations_with_edge_cases(self, test_settings: Any) -> None:
        """Test ValidationResults operations with edge case data."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                runner = ValidationRunner()

                # Test with None details
                runner.results.add_success("test", "test_name", "message", None, None)
                assert len(runner.results.items) == 1
                assert runner.results.items[0].details == {}
                assert runner.results.items[0].duration_ms is None

                # Test with empty details
                runner.results.add_failure("test", "test_name2", "message", {}, 0)
                assert len(runner.results.items) == 2
                assert runner.results.items[1].details == {}
                assert runner.results.items[1].duration_ms == 0

    def test_print_results_with_mocked_results_exception(self, test_settings: Any) -> None:
        """Test print_results() error handling when results methods fail."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                runner = ValidationRunner()

                # Mock results to raise exception
                mock_results = MagicMock()
                mock_results.print_console_report.side_effect = Exception("Print failed")
                runner.results = mock_results

                # Should raise the exception since no error handling is implemented
                with pytest.raises(Exception, match="Print failed"):
                    runner.print_results()


class TestValidationRunnerBasicAsyncSupport:
    """Test ValidationRunner basic async method signatures and structure."""

    @pytest.fixture
    def runner_with_mocks(self, test_settings: Any) -> Any:
        """Create ValidationRunner with mocked dependencies."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                return ValidationRunner()

    @pytest.mark.asyncio
    async def test_run_validation_method_exists(self, runner_with_mocks: Any) -> None:
        """Test that run_validation() method exists and is async."""
        runner = runner_with_mocks

        # Mock the internal async methods to avoid actual component initialization
        with patch.object(runner, "_initialize_components", new_callable=AsyncMock):
            with patch.object(runner, "_validate_source_connectivity", new_callable=AsyncMock):
                with patch.object(runner, "_validate_cache_operations", new_callable=AsyncMock):
                    with patch.object(
                        runner, "_validate_display_functionality", new_callable=AsyncMock
                    ):
                        with patch.object(runner, "_cleanup_components", new_callable=AsyncMock):
                            result = await runner.run_validation()

                            # Should return ValidationResults
                            assert isinstance(result, ValidationResults)
                            assert result is runner.results

    @pytest.mark.asyncio
    async def test_run_validation_exception_handling(self, runner_with_mocks: Any) -> None:
        """Test run_validation() basic exception handling structure."""
        runner = runner_with_mocks

        # Mock _initialize_components to raise exception
        with patch.object(runner, "_initialize_components", new_callable=AsyncMock) as mock_init:
            mock_init.side_effect = Exception("Initialization failed")
            with patch.object(runner, "_cleanup_components", new_callable=AsyncMock):
                result = await runner.run_validation()

                # Should handle exception and return results
                assert isinstance(result, ValidationResults)
                assert result is runner.results

                # Should have recorded the failure
                failures = result.get_failures()
                assert len(failures) > 0
                assert any("Runner error" in failure.message for failure in failures)

    @pytest.mark.asyncio
    async def test_cleanup_components_method_exists(self, runner_with_mocks: Any) -> None:
        """Test that _cleanup_components() method exists and is async."""
        runner = runner_with_mocks

        # Should be able to call without exception when components are None
        await runner._cleanup_components()

    @pytest.mark.asyncio
    async def test_cleanup_components_with_cache_manager(self, runner_with_mocks: Any) -> None:
        """Test _cleanup_components() with mocked cache manager."""
        runner = runner_with_mocks

        # Assign mock cache manager
        mock_cache = AsyncMock()
        runner.cache_manager = mock_cache

        await runner._cleanup_components()

        # Should call cleanup_old_events on cache manager
        mock_cache.cleanup_old_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_components_exception_handling(self, runner_with_mocks: Any) -> None:
        """Test _cleanup_components() exception handling."""
        runner = runner_with_mocks

        # Assign mock cache manager that raises exception
        mock_cache = AsyncMock()
        mock_cache.cleanup_old_events.side_effect = Exception("Cleanup failed")
        runner.cache_manager = mock_cache

        # Should not raise exception, just log warning
        await runner._cleanup_components()


class TestValidationRunnerAsyncWorkflows:
    """Test ValidationRunner main async validation workflows and component coordination."""

    @pytest.fixture
    def runner_with_mocks(self, test_settings: Any) -> Any:
        """Create ValidationRunner with mocked dependencies for async testing."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                return ValidationRunner()

    @pytest.fixture
    def mock_components(self) -> Any:
        """Create mock component managers for async testing."""
        mock_source = AsyncMock()
        mock_cache = AsyncMock()
        mock_display = AsyncMock()

        # Configure default successful responses
        mock_source.sources = ["test_source"]
        mock_source.get_health_status.return_value = {"test_source": AsyncMock(is_healthy=True)}
        mock_source.fetch_events.return_value = []

        mock_cache.initialize.return_value = True
        mock_cache.get_todays_cached_events.return_value = []
        mock_cache.get_cache_summary.return_value = {"total_events": 0}
        mock_cache.get_cache_status.return_value = AsyncMock()
        mock_cache.is_cache_fresh.return_value = True
        mock_cache.cleanup_old_events = AsyncMock()

        mock_display.display_events.return_value = True
        mock_display.settings = AsyncMock(display_type="console", display_enabled=True)

        return mock_source, mock_cache, mock_display

    @pytest.mark.asyncio
    async def test_run_validation_complete_workflow_success(
        self, runner_with_mocks: Any, mock_components: Any
    ) -> None:
        """Test complete run_validation() workflow with all components successful."""
        runner = runner_with_mocks
        mock_source, mock_cache, mock_display = mock_components

        # Mock component initialization
        with patch.object(runner, "_initialize_components", new_callable=AsyncMock) as mock_init:
            with patch.object(
                runner, "_validate_source_connectivity", new_callable=AsyncMock
            ) as mock_source_val:
                with patch.object(
                    runner, "_validate_cache_operations", new_callable=AsyncMock
                ) as mock_cache_val:
                    with patch.object(
                        runner, "_validate_display_functionality", new_callable=AsyncMock
                    ) as mock_display_val:
                        with patch.object(
                            runner, "_cleanup_components", new_callable=AsyncMock
                        ) as mock_cleanup:
                            result = await runner.run_validation()

                            # Verify workflow execution order
                            mock_init.assert_called_once()
                            mock_source_val.assert_called_once()
                            mock_cache_val.assert_called_once()
                            mock_display_val.assert_called_once()
                            mock_cleanup.assert_called_once()

                            # Verify results
                            assert isinstance(result, ValidationResults)
                            assert result is runner.results
                            assert result.end_time is not None

    @pytest.mark.asyncio
    async def test_run_validation_partial_components(self, test_settings: Any) -> None:
        """Test run_validation() with subset of components."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                runner = ValidationRunner(components=["sources", "cache"])

                with patch.object(runner, "_initialize_components", new_callable=AsyncMock):
                    with patch.object(
                        runner, "_validate_source_connectivity", new_callable=AsyncMock
                    ) as mock_source_val:
                        with patch.object(
                            runner, "_validate_cache_operations", new_callable=AsyncMock
                        ) as mock_cache_val:
                            with patch.object(
                                runner, "_validate_display_functionality", new_callable=AsyncMock
                            ) as mock_display_val:
                                with patch.object(
                                    runner, "_cleanup_components", new_callable=AsyncMock
                                ):
                                    result = await runner.run_validation()

                                    # Only sources and cache should be validated
                                    mock_source_val.assert_called_once()
                                    mock_cache_val.assert_called_once()
                                    mock_display_val.assert_not_called()

                                    assert isinstance(result, ValidationResults)

    @pytest.mark.asyncio
    async def test_run_validation_initialization_failure(self, runner_with_mocks: Any) -> None:
        """Test run_validation() when component initialization fails."""
        runner = runner_with_mocks

        with patch.object(runner, "_initialize_components", new_callable=AsyncMock) as mock_init:
            mock_init.side_effect = Exception("Initialization failed")
            with patch.object(
                runner, "_cleanup_components", new_callable=AsyncMock
            ) as mock_cleanup:
                result = await runner.run_validation()

                # Should still return results and cleanup
                assert isinstance(result, ValidationResults)
                mock_cleanup.assert_called_once()

                # Should record the failure
                failures = result.get_failures()
                assert len(failures) > 0
                assert any("Runner error" in failure.message for failure in failures)

    @pytest.mark.asyncio
    async def test_run_validation_component_validation_failure(
        self, runner_with_mocks: Any
    ) -> None:
        """Test run_validation() when individual component validation fails."""
        runner = runner_with_mocks

        with patch.object(runner, "_initialize_components", new_callable=AsyncMock):
            with patch.object(
                runner, "_validate_source_connectivity", new_callable=AsyncMock
            ) as mock_source_val:
                mock_source_val.side_effect = Exception("Source validation failed")
                with patch.object(runner, "_validate_cache_operations", new_callable=AsyncMock):
                    with patch.object(
                        runner, "_validate_display_functionality", new_callable=AsyncMock
                    ):
                        with patch.object(runner, "_cleanup_components", new_callable=AsyncMock):
                            result = await runner.run_validation()

                            # Should continue with other validations and return results
                            assert isinstance(result, ValidationResults)
                            assert result.end_time is not None

    @pytest.mark.asyncio
    async def test_run_validation_cleanup_always_called(self, runner_with_mocks: Any) -> None:
        """Test that cleanup is always called even when validation fails."""
        runner = runner_with_mocks

        with patch.object(runner, "_initialize_components", new_callable=AsyncMock):
            with patch.object(
                runner, "_validate_source_connectivity", new_callable=AsyncMock
            ) as mock_source_val:
                mock_source_val.side_effect = Exception("Validation error")
                with patch.object(
                    runner, "_cleanup_components", new_callable=AsyncMock
                ) as mock_cleanup:
                    result = await runner.run_validation()

                    # Cleanup should always be called
                    mock_cleanup.assert_called_once()
                    assert isinstance(result, ValidationResults)

    @pytest.mark.asyncio
    async def test_initialize_components_success(self, runner_with_mocks: Any) -> None:
        """Test _initialize_components() successful execution."""
        runner = runner_with_mocks

        # Mock the component imports using their actual module paths
        with patch("calendarbot.sources.SourceManager") as MockSourceManager:
            with patch("calendarbot.cache.CacheManager") as MockCacheManager:
                with patch("calendarbot.display.DisplayManager") as MockDisplayManager:
                    mock_source_instance = MagicMock()
                    mock_cache_instance = MagicMock()
                    mock_display_instance = MagicMock()

                    MockSourceManager.return_value = mock_source_instance
                    MockCacheManager.return_value = mock_cache_instance
                    MockDisplayManager.return_value = mock_display_instance

                    await runner._initialize_components()

                    # Verify components were created with settings
                    MockSourceManager.assert_called_once_with(runner.settings)
                    MockCacheManager.assert_called_once_with(runner.settings)
                    MockDisplayManager.assert_called_once_with(runner.settings)

                    # Verify components were assigned
                    assert runner.source_manager is mock_source_instance
                    assert runner.cache_manager is mock_cache_instance
                    assert runner.display_manager is mock_display_instance

                    # Verify success result was added
                    success_items = [
                        item
                        for item in runner.results.items
                        if item.status == ValidationStatus.SUCCESS
                    ]
                    assert len(success_items) == 1
                    assert success_items[0].test_name == "component_initialization"

    @pytest.mark.asyncio
    async def test_initialize_components_failure(self, runner_with_mocks: Any) -> None:
        """Test _initialize_components() when component creation fails."""
        runner = runner_with_mocks

        with patch("calendarbot.sources.SourceManager") as MockSourceManager:
            MockSourceManager.side_effect = Exception("Source manager creation failed")

            # Should raise the exception
            with pytest.raises(Exception, match="Source manager creation failed"):
                await runner._initialize_components()

            # Should record failure
            failures = runner.results.get_failures()
            assert len(failures) == 1
            assert "Failed to initialize components" in failures[0].message

    @pytest.mark.asyncio
    async def test_validate_source_connectivity_success(
        self, runner_with_mocks: Any, mock_components: Any
    ) -> None:
        """Test _validate_source_connectivity() successful execution."""
        runner = runner_with_mocks
        mock_source, _, _ = mock_components
        runner.source_manager = mock_source

        # Mock the individual test methods
        with patch.object(runner, "_test_source_manager_init", new_callable=AsyncMock) as mock_init:
            with patch.object(
                runner, "_test_source_health_checks", new_callable=AsyncMock
            ) as mock_health:
                with patch.object(runner, "_test_ics_fetch", new_callable=AsyncMock) as mock_fetch:
                    await runner._validate_source_connectivity()

                    # All source tests should be called
                    mock_init.assert_called_once()
                    mock_health.assert_called_once()
                    mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_source_connectivity_failure(self, runner_with_mocks: Any) -> None:
        """Test _validate_source_connectivity() when source tests fail."""
        runner = runner_with_mocks

        with patch.object(runner, "_test_source_manager_init", new_callable=AsyncMock) as mock_init:
            mock_init.side_effect = Exception("Source init failed")

            await runner._validate_source_connectivity()

            # Should record the failure
            failures = runner.results.get_failures()
            assert len(failures) == 1
            assert "Source validation failed" in failures[0].message

    @pytest.mark.asyncio
    async def test_validate_cache_operations_success(
        self, runner_with_mocks: Any, mock_components: Any
    ) -> None:
        """Test _validate_cache_operations() successful execution."""
        runner = runner_with_mocks
        _, mock_cache, _ = mock_components
        runner.cache_manager = mock_cache

        # Mock the individual test methods
        with patch.object(runner, "_test_cache_init", new_callable=AsyncMock) as mock_init:
            with patch.object(runner, "_test_cache_operations", new_callable=AsyncMock) as mock_ops:
                with patch.object(
                    runner, "_test_cache_status", new_callable=AsyncMock
                ) as mock_status:
                    await runner._validate_cache_operations()

                    # All cache tests should be called
                    mock_init.assert_called_once()
                    mock_ops.assert_called_once()
                    mock_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_cache_operations_failure(self, runner_with_mocks: Any) -> None:
        """Test _validate_cache_operations() when cache tests fail."""
        runner = runner_with_mocks

        with patch.object(runner, "_test_cache_init", new_callable=AsyncMock) as mock_init:
            mock_init.side_effect = Exception("Cache init failed")

            await runner._validate_cache_operations()

            # Should record the failure
            failures = runner.results.get_failures()
            assert len(failures) == 1
            assert "Cache validation failed" in failures[0].message

    @pytest.mark.asyncio
    async def test_validate_display_functionality_success(
        self, runner_with_mocks: Any, mock_components: Any
    ) -> None:
        """Test _validate_display_functionality() successful execution."""
        runner = runner_with_mocks
        _, _, mock_display = mock_components
        runner.display_manager = mock_display

        # Mock the individual test methods
        with patch.object(runner, "_test_display_init", new_callable=AsyncMock) as mock_init:
            with patch.object(
                runner, "_test_display_rendering", new_callable=AsyncMock
            ) as mock_render:
                await runner._validate_display_functionality()

                # All display tests should be called
                mock_init.assert_called_once()
                mock_render.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_display_functionality_failure(self, runner_with_mocks: Any) -> None:
        """Test _validate_display_functionality() when display tests fail."""
        runner = runner_with_mocks

        with patch.object(runner, "_test_display_init", new_callable=AsyncMock) as mock_init:
            mock_init.side_effect = Exception("Display init failed")

            await runner._validate_display_functionality()

            # Should record the failure
            failures = runner.results.get_failures()
            assert len(failures) == 1
            assert "Display validation failed" in failures[0].message


class TestValidationRunnerAsyncComponentTests:
    """Test individual async component validation methods in detail."""

    @pytest.fixture
    def runner_with_mocks(self, test_settings: Any) -> Any:
        """Create ValidationRunner with mocked dependencies."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                return ValidationRunner()

    @pytest.mark.asyncio
    async def test_test_source_manager_init_success(self, runner_with_mocks: Any) -> None:
        """Test _test_source_manager_init() with successful source manager."""
        runner = runner_with_mocks

        # Create mock source manager
        mock_source_manager = MagicMock()
        mock_source_manager.sources = ["source1", "source2"]
        runner.source_manager = mock_source_manager
        runner.settings.ics_url = "http://example.com/calendar.ics"

        await runner._test_source_manager_init()

        # Should record success
        successes = [
            item for item in runner.results.items if item.status == ValidationStatus.SUCCESS
        ]
        assert len(successes) == 1
        assert successes[0].test_name == "source_manager_init"
        assert successes[0].details["source_count"] == 2
        assert successes[0].details["has_primary_source"] is True

    @pytest.mark.asyncio
    async def test_test_source_manager_init_no_manager(self, runner_with_mocks: Any) -> None:
        """Test _test_source_manager_init() with no source manager."""
        runner = runner_with_mocks
        runner.source_manager = None

        await runner._test_source_manager_init()

        # Should record failure
        failures = runner.results.get_failures()
        assert len(failures) == 1
        assert failures[0].test_name == "source_manager_init"
        assert "Source manager not initialized" in failures[0].message

    @pytest.mark.asyncio
    async def test_test_source_manager_init_exception(self, runner_with_mocks: Any) -> None:
        """Test _test_source_manager_init() when accessing manager raises exception."""
        runner = runner_with_mocks

        mock_source_manager = MagicMock()
        mock_source_manager.sources = property(lambda x: exec('raise Exception("Access error")'))
        runner.source_manager = mock_source_manager

        await runner._test_source_manager_init()

        # Should record failure
        failures = runner.results.get_failures()
        assert len(failures) == 1
        assert "Source manager init error" in failures[0].message

    @pytest.mark.asyncio
    async def test_test_source_health_checks_success(self, runner_with_mocks: Any) -> None:
        """Test _test_source_health_checks() with healthy sources."""
        runner = runner_with_mocks

        # Mock source manager with health status
        mock_source_manager = AsyncMock()
        mock_health_status = {
            "source1": MagicMock(is_healthy=True),
            "source2": MagicMock(is_healthy=True),
        }
        mock_source_manager.get_health_status.return_value = mock_health_status
        runner.source_manager = mock_source_manager

        await runner._test_source_health_checks()

        # Should record success
        successes = [
            item for item in runner.results.items if item.status == ValidationStatus.SUCCESS
        ]
        assert len(successes) == 1
        assert successes[0].test_name == "source_health_checks"
        assert successes[0].details["healthy_sources"] == 2
        assert successes[0].details["total_sources"] == 2

    @pytest.mark.asyncio
    async def test_test_source_health_checks_no_sources(self, runner_with_mocks: Any) -> None:
        """Test _test_source_health_checks() with no sources configured."""
        runner = runner_with_mocks

        mock_source_manager = AsyncMock()
        mock_source_manager.get_health_status.return_value = {}
        runner.source_manager = mock_source_manager

        await runner._test_source_health_checks()

        # Should record warning
        warnings = runner.results.get_warnings()
        assert len(warnings) == 1
        assert warnings[0].test_name == "source_health_checks"
        assert "No sources configured" in warnings[0].message

    @pytest.mark.asyncio
    async def test_test_source_health_checks_all_unhealthy(self, runner_with_mocks: Any) -> None:
        """Test _test_source_health_checks() with all sources unhealthy."""
        runner = runner_with_mocks

        mock_source_manager = AsyncMock()
        mock_health_status = {
            "source1": MagicMock(is_healthy=False),
            "source2": MagicMock(is_healthy=False),
        }
        mock_source_manager.get_health_status.return_value = mock_health_status
        runner.source_manager = mock_source_manager

        await runner._test_source_health_checks()

        # Should record failure
        failures = runner.results.get_failures()
        assert len(failures) == 1
        assert failures[0].test_name == "source_health_checks"
        assert "All sources unhealthy" in failures[0].message

    @pytest.mark.asyncio
    async def test_test_ics_fetch_success(self, runner_with_mocks: Any) -> None:
        """Test _test_ics_fetch() with successful event fetching."""
        runner = runner_with_mocks

        mock_source_manager = AsyncMock()
        mock_events = ["event1", "event2", "event3"]
        mock_source_manager.fetch_events.return_value = mock_events
        runner.source_manager = mock_source_manager

        await runner._test_ics_fetch()

        # Should record success
        successes = [
            item for item in runner.results.items if item.status == ValidationStatus.SUCCESS
        ]
        assert len(successes) == 1
        assert successes[0].test_name == "ics_fetch"
        assert successes[0].details["events_count"] == 3

    @pytest.mark.asyncio
    async def test_test_ics_fetch_no_manager(self, runner_with_mocks: Any) -> None:
        """Test _test_ics_fetch() with no source manager."""
        runner = runner_with_mocks
        runner.source_manager = None

        await runner._test_ics_fetch()

        # Should record failure
        failures = runner.results.get_failures()
        assert len(failures) == 1
        assert failures[0].test_name == "ics_fetch"
        assert "Source manager not initialized" in failures[0].message

    @pytest.mark.asyncio
    async def test_test_cache_init_success(self, runner_with_mocks: Any) -> None:
        """Test _test_cache_init() with successful cache initialization."""
        runner = runner_with_mocks

        mock_cache_manager = AsyncMock()
        mock_cache_manager.initialize.return_value = True
        runner.cache_manager = mock_cache_manager
        runner.settings.database_file = "/path/to/db.sqlite"

        await runner._test_cache_init()

        # Should record success
        successes = [
            item for item in runner.results.items if item.status == ValidationStatus.SUCCESS
        ]
        assert len(successes) == 1
        assert successes[0].test_name == "cache_initialization"
        assert successes[0].details["initialized"] is True
        assert successes[0].details["database_path"] == "/path/to/db.sqlite"

    @pytest.mark.asyncio
    async def test_test_cache_init_failure(self, runner_with_mocks: Any) -> None:
        """Test _test_cache_init() when cache initialization fails."""
        runner = runner_with_mocks

        mock_cache_manager = AsyncMock()
        mock_cache_manager.initialize.return_value = False
        runner.cache_manager = mock_cache_manager

        await runner._test_cache_init()

        # Should record failure
        failures = runner.results.get_failures()
        assert len(failures) == 1
        assert failures[0].test_name == "cache_initialization"
        assert "Cache initialization failed" in failures[0].message

    @pytest.mark.asyncio
    async def test_test_cache_operations_success(self, runner_with_mocks: Any) -> None:
        """Test _test_cache_operations() with successful cache operations."""
        runner = runner_with_mocks

        mock_cache_manager = AsyncMock()
        mock_cached_events = ["cached_event1", "cached_event2"]
        mock_cache_summary = {"total_events": 10, "cache_size": "5MB"}
        mock_cache_manager.get_todays_cached_events.return_value = mock_cached_events
        mock_cache_manager.get_cache_summary.return_value = mock_cache_summary
        runner.cache_manager = mock_cache_manager

        await runner._test_cache_operations()

        # Should record success
        successes = [
            item for item in runner.results.items if item.status == ValidationStatus.SUCCESS
        ]
        assert len(successes) == 1
        assert successes[0].test_name == "cache_operations"
        assert successes[0].details["cached_events_count"] == 2
        assert successes[0].details["cache_summary"] == mock_cache_summary

    @pytest.mark.asyncio
    async def test_test_cache_status_success(self, runner_with_mocks: Any) -> None:
        """Test _test_cache_status() with successful cache status check."""
        runner = runner_with_mocks

        mock_cache_manager = AsyncMock()
        mock_cache_status = MagicMock(status="active", size="10MB")
        mock_cache_manager.get_cache_status.return_value = mock_cache_status
        mock_cache_manager.is_cache_fresh.return_value = True
        runner.cache_manager = mock_cache_manager

        await runner._test_cache_status()

        # Should record success
        successes = [
            item for item in runner.results.items if item.status == ValidationStatus.SUCCESS
        ]
        assert len(successes) == 1
        assert successes[0].test_name == "cache_status"
        assert successes[0].details["is_fresh"] is True

    @pytest.mark.asyncio
    async def test_test_display_init_success(self, runner_with_mocks: Any) -> None:
        """Test _test_display_init() with successful display initialization."""
        runner = runner_with_mocks

        mock_display_manager = MagicMock()
        mock_settings = MagicMock(display_type="console", display_enabled=True)
        mock_display_manager.settings = mock_settings
        runner.display_manager = mock_display_manager

        await runner._test_display_init()

        # Should record success
        successes = [
            item for item in runner.results.items if item.status == ValidationStatus.SUCCESS
        ]
        assert len(successes) == 1
        assert successes[0].test_name == "display_initialization"
        assert successes[0].details["display_type"] == "console"
        assert successes[0].details["display_enabled"] is True

    @pytest.mark.asyncio
    async def test_test_display_rendering_success(self, runner_with_mocks: Any) -> None:
        """Test _test_display_rendering() with successful rendering."""
        runner = runner_with_mocks

        mock_display_manager = AsyncMock()
        mock_display_manager.display_events.return_value = True
        runner.display_manager = mock_display_manager

        await runner._test_display_rendering()

        # Should record success
        successes = [
            item for item in runner.results.items if item.status == ValidationStatus.SUCCESS
        ]
        assert len(successes) == 1
        assert successes[0].test_name == "display_rendering"
        assert successes[0].details["render_success"] is True

    @pytest.mark.asyncio
    async def test_test_display_rendering_failure(self, runner_with_mocks: Any) -> None:
        """Test _test_display_rendering() when rendering fails."""
        runner = runner_with_mocks

        mock_display_manager = AsyncMock()
        mock_display_manager.display_events.return_value = False
        runner.display_manager = mock_display_manager

        await runner._test_display_rendering()

        # Should record failure
        failures = runner.results.get_failures()
        assert len(failures) == 1
        assert failures[0].test_name == "display_rendering"
        assert "Display rendering failed" in failures[0].message


class TestValidationRunnerAsyncErrorHandling:
    """Test async error handling and edge cases in validation workflows."""

    @pytest.fixture
    def runner_with_mocks(self, test_settings: Any) -> Any:
        """Create ValidationRunner with mocked dependencies."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                return ValidationRunner()

    @pytest.mark.asyncio
    async def test_async_timeout_scenarios(self, runner_with_mocks: Any) -> None:
        """Test async operations with timeout simulation."""
        runner = runner_with_mocks

        # Mock a slow async operation
        mock_source_manager = AsyncMock()

        async def slow_fetch() -> None:
            await asyncio.sleep(0.1)  # Simulate slow operation

        mock_source_manager.fetch_events = slow_fetch
        runner.source_manager = mock_source_manager

        # Should complete without timeout in test environment
        await runner._test_ics_fetch()

        # Should still record result
        results = [
            item for item in runner.results.items if item.status == ValidationStatus.SUCCESS
        ] + runner.results.get_failures()
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_async_cancellation_scenarios(self, runner_with_mocks: Any) -> None:
        """Test async operation cancellation handling."""
        runner = runner_with_mocks

        # Mock cancelled async operation
        mock_cache_manager = AsyncMock()
        mock_cache_manager.initialize.side_effect = asyncio.CancelledError("Operation cancelled")
        runner.cache_manager = mock_cache_manager

        # Should handle cancellation gracefully
        with pytest.raises(asyncio.CancelledError):
            await runner._test_cache_init()

    @pytest.mark.asyncio
    async def test_async_exception_propagation(self, runner_with_mocks: Any) -> None:
        """Test that async exceptions are properly captured and recorded."""
        runner = runner_with_mocks

        # Test with various exception types
        exceptions_to_test = [
            ConnectionError("Network connection failed"),
            TimeoutError("Operation timed out"),
            ValueError("Invalid value provided"),
            RuntimeError("Runtime error occurred"),
        ]

        for exception in exceptions_to_test:
            # Reset results for each test
            runner.results = ValidationResults()

            mock_source_manager = AsyncMock()
            mock_source_manager.get_health_status.side_effect = exception
            runner.source_manager = mock_source_manager

            await runner._test_source_health_checks()

            # Should record the failure
            failures = runner.results.get_failures()
            assert len(failures) == 1
            assert str(exception) in failures[0].message

    @pytest.mark.asyncio
    async def test_async_resource_cleanup_on_error(self, runner_with_mocks: Any) -> None:
        """Test that resources are cleaned up even when async operations fail."""
        runner = runner_with_mocks

        # Mock cache manager that fails during operation but needs cleanup
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get_cache_status.side_effect = Exception("Cache error")
        mock_cache_manager.cleanup_old_events = AsyncMock()  # Should still be called
        runner.cache_manager = mock_cache_manager

        # Test cache status (will fail)
        await runner._test_cache_status()

        # Test cleanup (should succeed despite previous failure)
        await runner._cleanup_components()

        # Cleanup should have been called
        mock_cache_manager.cleanup_old_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_async_operations(self, runner_with_mocks: Any) -> None:
        """Test handling of concurrent async operations."""
        runner = runner_with_mocks

        # Setup multiple mock managers
        mock_source = AsyncMock()
        mock_cache = AsyncMock()
        mock_display = AsyncMock()

        mock_source.fetch_events.return_value = []
        mock_cache.get_cache_summary.return_value = {}
        mock_display.display_events.return_value = True

        runner.source_manager = mock_source
        runner.cache_manager = mock_cache
        runner.display_manager = mock_display

        # Run operations concurrently
        tasks = [
            runner._test_ics_fetch(),
            runner._test_cache_operations(),
            runner._test_display_rendering(),
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should have recorded results
        all_results = (
            [item for item in runner.results.items if item.status == ValidationStatus.SUCCESS]
            + runner.results.get_failures()
            + runner.results.get_warnings()
        )
        assert len(all_results) >= 3

    @pytest.mark.asyncio
    async def test_async_memory_management(self, runner_with_mocks: Any) -> None:
        """Test memory management during async operations."""
        runner = runner_with_mocks

        # Mock manager that returns large data sets
        mock_source_manager = AsyncMock()
        large_event_list = [f"event_{i}" for i in range(1000)]
        mock_source_manager.fetch_events.return_value = large_event_list
        runner.source_manager = mock_source_manager

        await runner._test_ics_fetch()

        # Should handle large data gracefully
        successes = [
            item for item in runner.results.items if item.status == ValidationStatus.SUCCESS
        ]
        assert len(successes) == 1
        assert successes[0].details["events_count"] == 1000

        # Clean up references
        del large_event_list
        del mock_source_manager


class TestValidationRunnerAsyncIntegration:
    """Test integration between async workflows and ValidationResults."""

    @pytest.fixture
    def runner_with_mocks(self, test_settings: Any) -> Any:
        """Create ValidationRunner with mocked dependencies."""
        with patch("calendarbot.validation.runner.get_validation_logger"):
            with patch("calendarbot.validation.runner.settings", test_settings):
                return ValidationRunner()

    @pytest.mark.asyncio
    async def test_results_aggregation_across_async_operations(
        self, runner_with_mocks: Any
    ) -> None:
        """Test that results are properly aggregated across multiple async operations."""
        runner = runner_with_mocks

        # Setup mocks for successful operations
        mock_source = AsyncMock()
        mock_cache = AsyncMock()
        mock_display = AsyncMock()

        mock_source.sources = ["source1"]
        mock_source.get_health_status.return_value = {"source1": MagicMock(is_healthy=True)}
        mock_source.fetch_events.return_value = ["event1", "event2"]

        mock_cache.initialize.return_value = True
        mock_cache.get_todays_cached_events.return_value = ["cached1"]
        mock_cache.get_cache_summary.return_value = {"total": 1}
        mock_cache.get_cache_status.return_value = MagicMock()
        mock_cache.is_cache_fresh.return_value = True

        mock_display.settings = MagicMock(display_type="console", display_enabled=True)
        mock_display.display_events.return_value = True

        runner.source_manager = mock_source
        runner.cache_manager = mock_cache
        runner.display_manager = mock_display
        runner.settings.ics_url = "http://example.com/cal.ics"
        runner.settings.database_file = "/test/db.sqlite"

        # Run all individual test methods
        await runner._test_source_manager_init()
        await runner._test_source_health_checks()
        await runner._test_ics_fetch()
        await runner._test_cache_init()
        await runner._test_cache_operations()
        await runner._test_cache_status()
        await runner._test_display_init()
        await runner._test_display_rendering()

        # Verify comprehensive results aggregation
        successes = [
            item for item in runner.results.items if item.status == ValidationStatus.SUCCESS
        ]
        assert len(successes) == 8  # All tests should succeed

        # Verify all components were tested
        components_tested = runner.results.components_tested
        assert "sources" in components_tested
        assert "cache" in components_tested
        assert "display" in components_tested

        # Verify different test types
        test_names = [success.test_name for success in successes]
        expected_tests = [
            "source_manager_init",
            "source_health_checks",
            "ics_fetch",
            "cache_initialization",
            "cache_operations",
            "cache_status",
            "display_initialization",
            "display_rendering",
        ]
        for expected_test in expected_tests:
            assert expected_test in test_names

    @pytest.mark.asyncio
    async def test_results_timing_across_async_operations(self, runner_with_mocks: Any) -> None:
        """Test that timing information is captured across async operations."""
        runner = runner_with_mocks

        # Setup mock with delay
        mock_source = AsyncMock()

        async def delayed_fetch() -> list[Any]:
            await asyncio.sleep(0.01)  # Small delay
            return []  # Return empty list for successful fetch

        mock_source.fetch_events = delayed_fetch
        runner.source_manager = mock_source

        time.time()
        await runner._test_ics_fetch()
        time.time()

        # Verify timing was captured
        successes = [
            item for item in runner.results.items if item.status == ValidationStatus.SUCCESS
        ]
        assert len(successes) == 1
        assert successes[0].duration_ms is not None
        assert successes[0].duration_ms > 0

        # Duration should be reasonable (at least 10ms due to sleep)
        assert successes[0].duration_ms >= 10

    @pytest.mark.asyncio
    async def test_results_error_context_preservation(self, runner_with_mocks: Any) -> None:
        """Test that error context is preserved across async operations."""
        runner = runner_with_mocks

        # Test different types of failures
        test_scenarios = [
            {
                "component": "sources",
                "manager_attr": "source_manager",
                "test_method": "_test_ics_fetch",
                "mock_method": "fetch_events",
                "exception": ConnectionError("Network unreachable"),
            },
            {
                "component": "cache",
                "manager_attr": "cache_manager",
                "test_method": "_test_cache_init",
                "mock_method": "initialize",
                "exception": PermissionError("Database access denied"),
            },
        ]

        for scenario in test_scenarios:
            # Reset results for each scenario
            runner.results = ValidationResults()

            # Setup mock manager
            mock_manager = AsyncMock()
            getattr(mock_manager, scenario["mock_method"]).side_effect = scenario["exception"]  # type: ignore
            setattr(runner, scenario["manager_attr"], mock_manager)  # type: ignore

            # Execute test method
            await getattr(runner, scenario["test_method"])()  # type: ignore

            # Verify error context is preserved
            failures = runner.results.get_failures()
            assert len(failures) == 1
            failure = failures[0]
            assert failure.component == scenario["component"]
            assert str(scenario["exception"]) in failure.message
            assert failure.duration_ms is not None
