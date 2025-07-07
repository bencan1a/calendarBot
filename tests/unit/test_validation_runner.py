"""Unit tests for calendarbot.validation.runner module."""

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch

import pytest

from calendarbot.validation.results import ValidationResults, ValidationStatus
from calendarbot.validation.runner import ValidationRunner


class TestValidationRunner:
    """Test ValidationRunner class functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        settings = Mock()
        settings.database_file = "/tmp/test.db"
        settings.display_type = "console"
        settings.display_enabled = True
        settings.ics_url = "http://example.com/calendar.ics"
        return settings

    @pytest.fixture
    def validation_runner(self, mock_settings):
        """Create ValidationRunner instance for testing."""
        with patch("calendarbot.validation.runner.settings", mock_settings):
            runner = ValidationRunner()
            return runner

    def test_validation_runner_initialization_defaults(self, mock_settings):
        """Test ValidationRunner initialization with default parameters."""
        with patch("calendarbot.validation.runner.settings", mock_settings):
            runner = ValidationRunner()

            assert runner.test_date.hour == 0
            assert runner.test_date.minute == 0
            assert runner.test_date.second == 0
            assert runner.end_date == runner.test_date
            assert runner.components == ["sources", "cache", "display"]
            assert runner.use_cache == True
            assert runner.output_format == "console"
            assert runner.settings == mock_settings
            assert isinstance(runner.results, ValidationResults)

    def test_validation_runner_initialization_custom(self, mock_settings):
        """Test ValidationRunner initialization with custom parameters."""
        test_date = datetime(2023, 1, 15, 10, 30)
        end_date = datetime(2023, 1, 16, 10, 30)
        components = ["sources", "cache"]

        with patch("calendarbot.validation.runner.settings", mock_settings):
            runner = ValidationRunner(
                test_date=test_date,
                end_date=end_date,
                components=components,
                use_cache=False,
                output_format="json",
            )

            assert runner.test_date == test_date
            assert runner.end_date == end_date
            assert runner.components == components
            assert runner.use_cache == False
            assert runner.output_format == "json"

    @pytest.mark.asyncio
    async def test_run_validation_success(self, validation_runner):
        """Test successful validation run."""
        # Mock component initialization
        with patch.object(validation_runner, "_initialize_components") as mock_init:
            with patch.object(validation_runner, "_validate_source_connectivity") as mock_sources:
                with patch.object(validation_runner, "_validate_cache_operations") as mock_cache:
                    with patch.object(
                        validation_runner, "_validate_display_functionality"
                    ) as mock_display:
                        with patch.object(validation_runner, "_cleanup_components") as mock_cleanup:

                            result = await validation_runner.run_validation()

                            assert isinstance(result, ValidationResults)
                            mock_init.assert_called_once()
                            mock_sources.assert_called_once()
                            mock_cache.assert_called_once()
                            mock_display.assert_called_once()
                            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_validation_with_exception(self, validation_runner):
        """Test validation run with exception during initialization."""
        with patch.object(
            validation_runner, "_initialize_components", side_effect=Exception("Init error")
        ):
            with patch.object(validation_runner, "_cleanup_components") as mock_cleanup:

                result = await validation_runner.run_validation()

                assert isinstance(result, ValidationResults)
                assert result.has_failures()
                mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_validation_selective_components(self, mock_settings):
        """Test validation run with selective components."""
        with patch("calendarbot.validation.runner.settings", mock_settings):
            runner = ValidationRunner(components=["sources", "cache"])

            with patch.object(runner, "_initialize_components"):
                with patch.object(runner, "_validate_source_connectivity") as mock_sources:
                    with patch.object(runner, "_validate_cache_operations") as mock_cache:
                        with patch.object(
                            runner, "_validate_display_functionality"
                        ) as mock_display:
                            with patch.object(runner, "_cleanup_components"):

                                await runner.run_validation()

                                mock_sources.assert_called_once()
                                mock_cache.assert_called_once()
                                mock_display.assert_not_called()  # Not in components

    @pytest.mark.asyncio
    async def test_initialize_components_success(self, validation_runner):
        """Test successful component initialization."""
        mock_source_manager = Mock()
        mock_cache_manager = Mock()
        mock_display_manager = Mock()

        with patch("calendarbot.sources.SourceManager", return_value=mock_source_manager):
            with patch("calendarbot.cache.CacheManager", return_value=mock_cache_manager):
                with patch("calendarbot.display.DisplayManager", return_value=mock_display_manager):

                    await validation_runner._initialize_components()

                    assert validation_runner.source_manager == mock_source_manager
                    assert validation_runner.cache_manager == mock_cache_manager
                    assert validation_runner.display_manager == mock_display_manager

                    # Check that success was recorded
                    successes = [
                        item
                        for item in validation_runner.results.items
                        if item.status == ValidationStatus.SUCCESS
                        and item.test_name == "component_initialization"
                    ]
                    assert len(successes) == 1

    @pytest.mark.asyncio
    async def test_initialize_components_failure(self, validation_runner):
        """Test component initialization failure."""
        with patch(
            "calendarbot.sources.SourceManager", side_effect=Exception("Source init failed")
        ):

            with pytest.raises(Exception):
                await validation_runner._initialize_components()

            # Check that failure was recorded
            failures = [
                item
                for item in validation_runner.results.items
                if item.status == ValidationStatus.FAILURE
                and item.test_name == "component_initialization"
            ]
            assert len(failures) == 1

    @pytest.mark.asyncio
    async def test_cleanup_components_success(self, validation_runner):
        """Test successful component cleanup."""
        mock_cache_manager = AsyncMock()
        validation_runner.cache_manager = mock_cache_manager

        await validation_runner._cleanup_components()

        mock_cache_manager.cleanup_old_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_components_with_error(self, validation_runner):
        """Test component cleanup with error."""
        mock_cache_manager = AsyncMock()
        mock_cache_manager.cleanup_old_events.side_effect = Exception("Cleanup error")
        validation_runner.cache_manager = mock_cache_manager

        # Should not raise exception
        await validation_runner._cleanup_components()

    @pytest.mark.asyncio
    async def test_validate_source_connectivity(self, validation_runner):
        """Test source connectivity validation."""
        with patch.object(validation_runner, "_test_source_manager_init") as mock_manager_init:
            with patch.object(validation_runner, "_test_source_health_checks") as mock_health:
                with patch.object(validation_runner, "_test_ics_fetch") as mock_fetch:

                    await validation_runner._validate_source_connectivity()

                    mock_manager_init.assert_called_once()
                    mock_health.assert_called_once()
                    mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_source_manager_init_success(self, validation_runner):
        """Test source manager initialization success."""
        mock_source_manager = Mock()
        mock_source_manager.sources = ["source1", "source2"]
        validation_runner.source_manager = mock_source_manager

        await validation_runner._test_source_manager_init()

        # Check that success was recorded
        successes = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.SUCCESS and item.test_name == "source_manager_init"
        ]
        assert len(successes) == 1
        assert successes[0].details["source_count"] == 2

    @pytest.mark.asyncio
    async def test_test_source_health_checks_success(self, validation_runner):
        """Test source health checks success."""
        mock_health_status = {"source1": Mock(is_healthy=True), "source2": Mock(is_healthy=True)}

        mock_source_manager = AsyncMock()
        mock_source_manager.get_health_status.return_value = mock_health_status
        validation_runner.source_manager = mock_source_manager

        await validation_runner._test_source_health_checks()

        # Check that success was recorded
        successes = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.SUCCESS and item.test_name == "source_health_checks"
        ]
        assert len(successes) == 1
        assert successes[0].details["healthy_sources"] == 2

    @pytest.mark.asyncio
    async def test_test_source_health_checks_no_sources(self, validation_runner):
        """Test source health checks with no sources."""
        mock_source_manager = AsyncMock()
        mock_source_manager.get_health_status.return_value = {}
        validation_runner.source_manager = mock_source_manager

        await validation_runner._test_source_health_checks()

        # Check that warning was recorded
        warnings = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.WARNING and item.test_name == "source_health_checks"
        ]
        assert len(warnings) == 1

    @pytest.mark.asyncio
    async def test_test_ics_fetch_success(self, validation_runner):
        """Test ICS fetch success."""
        mock_events = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        mock_source_manager = AsyncMock()
        mock_source_manager.fetch_events.return_value = mock_events
        validation_runner.source_manager = mock_source_manager

        await validation_runner._test_ics_fetch()

        # Check that success was recorded
        successes = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.SUCCESS and item.test_name == "ics_fetch"
        ]
        assert len(successes) == 1
        assert successes[0].details["events_count"] == 3

    @pytest.mark.asyncio
    async def test_validate_cache_operations(self, validation_runner):
        """Test cache operations validation."""
        with patch.object(validation_runner, "_test_cache_init") as mock_init:
            with patch.object(validation_runner, "_test_cache_operations") as mock_ops:
                with patch.object(validation_runner, "_test_cache_status") as mock_status:

                    await validation_runner._validate_cache_operations()

                    mock_init.assert_called_once()
                    mock_ops.assert_called_once()
                    mock_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_cache_init_success(self, validation_runner):
        """Test cache initialization success."""
        mock_cache_manager = AsyncMock()
        mock_cache_manager.initialize.return_value = True
        validation_runner.cache_manager = mock_cache_manager

        await validation_runner._test_cache_init()

        # Check that success was recorded
        successes = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.SUCCESS and item.test_name == "cache_initialization"
        ]
        assert len(successes) == 1

    @pytest.mark.asyncio
    async def test_test_cache_init_failure(self, validation_runner):
        """Test cache initialization failure."""
        mock_cache_manager = AsyncMock()
        mock_cache_manager.initialize.return_value = False
        validation_runner.cache_manager = mock_cache_manager

        await validation_runner._test_cache_init()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "cache_initialization"
        ]
        assert len(failures) == 1

    @pytest.mark.asyncio
    async def test_test_cache_operations_success(self, validation_runner):
        """Test cache operations success."""
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get_todays_cached_events.return_value = [{"id": "1"}]
        mock_cache_manager.get_cache_summary.return_value = {"total": 1}
        validation_runner.cache_manager = mock_cache_manager

        await validation_runner._test_cache_operations()

        # Check that success was recorded
        successes = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.SUCCESS and item.test_name == "cache_operations"
        ]
        assert len(successes) == 1
        assert successes[0].details["cached_events_count"] == 1

    @pytest.mark.asyncio
    async def test_test_cache_status_success(self, validation_runner):
        """Test cache status check success."""
        mock_cache_status = Mock()
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get_cache_status.return_value = mock_cache_status
        mock_cache_manager.is_cache_fresh.return_value = True
        validation_runner.cache_manager = mock_cache_manager

        await validation_runner._test_cache_status()

        # Check that success was recorded
        successes = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.SUCCESS and item.test_name == "cache_status"
        ]
        assert len(successes) == 1
        assert successes[0].details["is_fresh"] == True

    @pytest.mark.asyncio
    async def test_validate_display_functionality(self, validation_runner):
        """Test display functionality validation."""
        with patch.object(validation_runner, "_test_display_init") as mock_init:
            with patch.object(validation_runner, "_test_display_rendering") as mock_render:

                await validation_runner._validate_display_functionality()

                mock_init.assert_called_once()
                mock_render.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_display_init_success(self, validation_runner):
        """Test display initialization success."""
        mock_display_manager = Mock()
        mock_display_manager.settings.display_type = "console"
        mock_display_manager.settings.display_enabled = True
        validation_runner.display_manager = mock_display_manager

        await validation_runner._test_display_init()

        # Check that success was recorded
        successes = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.SUCCESS
            and item.test_name == "display_initialization"
        ]
        assert len(successes) == 1
        assert successes[0].details["display_type"] == "console"

    @pytest.mark.asyncio
    async def test_test_display_rendering_success(self, validation_runner):
        """Test display rendering success."""
        mock_display_manager = AsyncMock()
        mock_display_manager.display_events.return_value = True
        validation_runner.display_manager = mock_display_manager

        await validation_runner._test_display_rendering()

        # Check that success was recorded
        successes = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.SUCCESS and item.test_name == "display_rendering"
        ]
        assert len(successes) == 1

    @pytest.mark.asyncio
    async def test_test_display_rendering_failure(self, validation_runner):
        """Test display rendering failure."""
        mock_display_manager = AsyncMock()
        mock_display_manager.display_events.return_value = False
        validation_runner.display_manager = mock_display_manager

        await validation_runner._test_display_rendering()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "display_rendering"
        ]
        assert len(failures) == 1

    def test_get_results(self, validation_runner):
        """Test get_results method."""
        result = validation_runner.get_results()
        assert isinstance(result, ValidationResults)
        assert result == validation_runner.results

    def test_print_results_console_format(self, validation_runner):
        """Test print_results method with console format."""
        validation_runner.output_format = "console"

        with patch.object(validation_runner.results, "print_console_report") as mock_console:
            validation_runner.print_results(verbose=True)
            mock_console.assert_called_once_with(True)

    def test_print_results_json_format(self, validation_runner):
        """Test print_results method with JSON format."""
        validation_runner.output_format = "json"

        with patch.object(validation_runner.results, "print_json_report") as mock_json:
            validation_runner.print_results()
            mock_json.assert_called_once()


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        settings = Mock()
        settings.database_file = "/tmp/test.db"
        settings.display_type = "console"
        settings.display_enabled = True
        settings.ics_url = "http://example.com/calendar.ics"
        return settings

    @pytest.fixture
    def validation_runner(self, mock_settings):
        """Create ValidationRunner instance for testing."""
        with patch("calendarbot.validation.runner.settings", mock_settings):
            runner = ValidationRunner()
            return runner

    @pytest.mark.asyncio
    async def test_source_manager_init_when_manager_is_none(self, validation_runner):
        """Test source manager init when source_manager is None."""
        # Ensure source_manager is None
        validation_runner.source_manager = None

        await validation_runner._test_source_manager_init()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "source_manager_init"
        ]
        assert len(failures) == 1
        assert "Source manager not initialized" in failures[0].message

    @pytest.mark.asyncio
    async def test_source_manager_init_with_exception(self, validation_runner):
        """Test source manager init with exception during evaluation."""
        # Create a mock that raises exception when accessing sources
        mock_source_manager = Mock()
        mock_source_manager.sources = Mock(side_effect=Exception("Source access error"))
        validation_runner.source_manager = mock_source_manager

        await validation_runner._test_source_manager_init()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "source_manager_init"
        ]
        assert len(failures) == 1
        assert "Source manager init error" in failures[0].message

    @pytest.mark.asyncio
    async def test_source_health_checks_when_manager_is_none(self, validation_runner):
        """Test source health checks when source_manager is None."""
        validation_runner.source_manager = None

        await validation_runner._test_source_health_checks()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "source_health_checks"
        ]
        assert len(failures) == 1
        assert "Source manager not initialized" in failures[0].message

    @pytest.mark.asyncio
    async def test_source_health_checks_with_exception(self, validation_runner):
        """Test source health checks with exception."""
        mock_source_manager = AsyncMock()
        mock_source_manager.get_health_status.side_effect = Exception("Health check error")
        validation_runner.source_manager = mock_source_manager

        await validation_runner._test_source_health_checks()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "source_health_checks"
        ]
        assert len(failures) == 1
        assert "Source health check error" in failures[0].message

    @pytest.mark.asyncio
    async def test_source_health_checks_all_unhealthy(self, validation_runner):
        """Test source health checks when all sources are unhealthy."""
        mock_health_status = {"source1": Mock(is_healthy=False), "source2": Mock(is_healthy=False)}

        mock_source_manager = AsyncMock()
        mock_source_manager.get_health_status.return_value = mock_health_status
        validation_runner.source_manager = mock_source_manager

        await validation_runner._test_source_health_checks()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "source_health_checks"
        ]
        assert len(failures) == 1
        assert "All sources unhealthy" in failures[0].message

    @pytest.mark.asyncio
    async def test_ics_fetch_when_manager_is_none(self, validation_runner):
        """Test ICS fetch when source_manager is None."""
        validation_runner.source_manager = None

        await validation_runner._test_ics_fetch()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "ics_fetch"
        ]
        assert len(failures) == 1
        assert "Source manager not initialized" in failures[0].message

    @pytest.mark.asyncio
    async def test_ics_fetch_with_exception(self, validation_runner):
        """Test ICS fetch with exception."""
        mock_source_manager = AsyncMock()
        mock_source_manager.fetch_events.side_effect = Exception("Fetch error")
        validation_runner.source_manager = mock_source_manager

        await validation_runner._test_ics_fetch()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "ics_fetch"
        ]
        assert len(failures) == 1
        assert "ICS fetch error" in failures[0].message

    @pytest.mark.asyncio
    async def test_cache_init_when_manager_is_none(self, validation_runner):
        """Test cache init when cache_manager is None."""
        validation_runner.cache_manager = None

        await validation_runner._test_cache_init()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "cache_initialization"
        ]
        assert len(failures) == 1
        assert "Cache manager not initialized" in failures[0].message

    @pytest.mark.asyncio
    async def test_cache_init_with_exception(self, validation_runner):
        """Test cache init with exception."""
        mock_cache_manager = AsyncMock()
        mock_cache_manager.initialize.side_effect = Exception("Cache init error")
        validation_runner.cache_manager = mock_cache_manager

        await validation_runner._test_cache_init()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "cache_initialization"
        ]
        assert len(failures) == 1
        assert "Cache init error" in failures[0].message

    @pytest.mark.asyncio
    async def test_cache_operations_when_manager_is_none(self, validation_runner):
        """Test cache operations when cache_manager is None."""
        validation_runner.cache_manager = None

        await validation_runner._test_cache_operations()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "cache_operations"
        ]
        assert len(failures) == 1
        assert "Cache manager not initialized" in failures[0].message

    @pytest.mark.asyncio
    async def test_cache_operations_with_exception(self, validation_runner):
        """Test cache operations with exception."""
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get_todays_cached_events.side_effect = Exception("Cache ops error")
        validation_runner.cache_manager = mock_cache_manager

        await validation_runner._test_cache_operations()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "cache_operations"
        ]
        assert len(failures) == 1
        assert "Cache operations error" in failures[0].message

    @pytest.mark.asyncio
    async def test_cache_status_when_manager_is_none(self, validation_runner):
        """Test cache status when cache_manager is None."""
        validation_runner.cache_manager = None

        await validation_runner._test_cache_status()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "cache_status"
        ]
        assert len(failures) == 1
        assert "Cache manager not initialized" in failures[0].message

    @pytest.mark.asyncio
    async def test_cache_status_with_exception(self, validation_runner):
        """Test cache status with exception."""
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get_cache_status.side_effect = Exception("Cache status error")
        validation_runner.cache_manager = mock_cache_manager

        await validation_runner._test_cache_status()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "cache_status"
        ]
        assert len(failures) == 1
        assert "Cache status error" in failures[0].message

    @pytest.mark.asyncio
    async def test_display_init_when_manager_is_none(self, validation_runner):
        """Test display init when display_manager is None."""
        validation_runner.display_manager = None

        await validation_runner._test_display_init()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE
            and item.test_name == "display_initialization"
        ]
        assert len(failures) == 1
        assert "Display manager not initialized" in failures[0].message

    @pytest.mark.asyncio
    async def test_display_init_with_exception(self, validation_runner):
        """Test display init with exception."""
        # Create a mock that raises exception when accessing settings.display_type
        mock_settings = Mock()
        type(mock_settings).display_type = PropertyMock(
            side_effect=Exception("Display access error")
        )

        mock_display_manager = Mock()
        mock_display_manager.settings = mock_settings
        validation_runner.display_manager = mock_display_manager

        await validation_runner._test_display_init()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE
            and item.test_name == "display_initialization"
        ]
        assert len(failures) == 1
        assert "Display init error" in failures[0].message

    @pytest.mark.asyncio
    async def test_display_rendering_when_manager_is_none(self, validation_runner):
        """Test display rendering when display_manager is None."""
        validation_runner.display_manager = None

        await validation_runner._test_display_rendering()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "display_rendering"
        ]
        assert len(failures) == 1
        assert "Display manager not initialized" in failures[0].message

    @pytest.mark.asyncio
    async def test_display_rendering_with_exception(self, validation_runner):
        """Test display rendering with exception."""
        mock_display_manager = AsyncMock()
        mock_display_manager.display_events.side_effect = Exception("Display render error")
        validation_runner.display_manager = mock_display_manager

        await validation_runner._test_display_rendering()

        # Check that failure was recorded
        failures = [
            item
            for item in validation_runner.results.items
            if item.status == ValidationStatus.FAILURE and item.test_name == "display_rendering"
        ]
        assert len(failures) == 1
        assert "Display rendering error" in failures[0].message

    @pytest.mark.asyncio
    async def test_cleanup_components_with_none_manager(self, validation_runner):
        """Test component cleanup when cache_manager is None."""
        validation_runner.cache_manager = None

        # Should not raise exception
        await validation_runner._cleanup_components()

    @pytest.mark.parametrize(
        "components",
        [
            ["sources"],
            ["cache"],
            ["display"],
            ["sources", "cache"],
            ["cache", "display"],
            ["sources", "display"],
        ],
    )
    @pytest.mark.asyncio
    async def test_run_validation_selective_component_combinations(self, mock_settings, components):
        """Test validation run with different component combinations."""
        with patch("calendarbot.validation.runner.settings", mock_settings):
            runner = ValidationRunner(components=components)

            with patch.object(runner, "_initialize_components"):
                with patch.object(runner, "_validate_source_connectivity") as mock_sources:
                    with patch.object(runner, "_validate_cache_operations") as mock_cache:
                        with patch.object(
                            runner, "_validate_display_functionality"
                        ) as mock_display:
                            with patch.object(runner, "_cleanup_components"):

                                await runner.run_validation()

                                # Check that only requested components were validated
                                if "sources" in components:
                                    mock_sources.assert_called_once()
                                else:
                                    mock_sources.assert_not_called()

                                if "cache" in components:
                                    mock_cache.assert_called_once()
                                else:
                                    mock_cache.assert_not_called()

                                if "display" in components:
                                    mock_display.assert_called_once()
                                else:
                                    mock_display.assert_not_called()


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        settings = Mock()
        settings.database_file = "/tmp/test.db"
        settings.display_type = "console"
        settings.display_enabled = True
        settings.ics_url = "http://example.com/calendar.ics"
        return settings

    @pytest.mark.asyncio
    async def test_complete_validation_flow_all_components(self, mock_settings):
        """Test complete validation flow with all components."""
        with patch("calendarbot.validation.runner.settings", mock_settings):
            runner = ValidationRunner(components=["sources", "cache", "display"])

            # Mock all dependencies
            with patch("calendarbot.sources.SourceManager"):
                with patch("calendarbot.cache.CacheManager"):
                    with patch("calendarbot.display.DisplayManager"):

                        results = await runner.run_validation()

                        assert isinstance(results, ValidationResults)
                        # Should have results for all component types
                        components_tested = {item.component for item in results.items}
                        assert "sources" in components_tested
                        assert "cache" in components_tested
                        assert "display" in components_tested

    @pytest.mark.asyncio
    async def test_partial_component_failure_continues_validation(self, mock_settings):
        """Test that validation continues even if individual components fail."""
        with patch("calendarbot.validation.runner.settings", mock_settings):
            runner = ValidationRunner(components=["sources", "cache"])

            # Mock components to initialize successfully
            with patch("calendarbot.sources.SourceManager"):
                with patch("calendarbot.cache.CacheManager"):
                    with patch("calendarbot.display.DisplayManager"):

                        # Mock the validation methods to control behavior
                        async def failing_sources_validation():
                            runner.results.add_failure("sources", "test_sources", "Sources failed")

                        async def successful_cache_validation():
                            runner.results.add_success("cache", "test_cache", "Cache success")

                        with patch.object(
                            runner,
                            "_validate_source_connectivity",
                            side_effect=failing_sources_validation,
                        ):
                            with patch.object(
                                runner,
                                "_validate_cache_operations",
                                side_effect=successful_cache_validation,
                            ):

                                results = await runner.run_validation()

                                # Should have both failure and success
                                assert results.has_failures()
                                failures = results.get_failures()
                                successes = [
                                    item
                                    for item in results.items
                                    if item.status == ValidationStatus.SUCCESS
                                ]

                                assert len(failures) > 0
                                assert len(successes) > 0

    @pytest.mark.asyncio
    async def test_initialization_failure_stops_validation(self, mock_settings):
        """Test that initialization failure stops the entire validation process."""
        with patch("calendarbot.validation.runner.settings", mock_settings):
            runner = ValidationRunner(components=["sources", "cache"])

            # Mock sources to fail during initialization
            with patch(
                "calendarbot.sources.SourceManager", side_effect=Exception("Sources failed")
            ):
                with patch("calendarbot.cache.CacheManager"):
                    with patch("calendarbot.display.DisplayManager"):

                        results = await runner.run_validation()

                        # Should have initialization failure but no component validation results
                        assert results.has_failures()
                        failures = results.get_failures()

                        # Should have component_initialization failure and validation_runner failure
                        failure_names = [f.test_name for f in failures]
                        assert "component_initialization" in failure_names
                        assert "validation_runner" in failure_names

    @pytest.mark.asyncio
    async def test_validation_with_date_range(self, mock_settings):
        """Test validation with date range."""
        test_date = datetime(2023, 1, 15)
        end_date = datetime(2023, 1, 17)

        with patch("calendarbot.validation.runner.settings", mock_settings):
            runner = ValidationRunner(test_date=test_date, end_date=end_date)

            assert runner.test_date == test_date
            assert runner.end_date == end_date

    def test_logger_configuration(self, mock_settings):
        """Test that logger is properly configured."""
        with patch("calendarbot.validation.runner.settings", mock_settings):
            with patch("calendarbot.validation.runner.get_validation_logger") as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                runner = ValidationRunner()

                mock_get_logger.assert_called_with("validation")
                assert runner.logger == mock_logger

    @pytest.mark.asyncio
    async def test_cache_status_with_object_dict_conversion(self, mock_settings):
        """Test cache status when cache_status has __dict__ attribute."""
        with patch("calendarbot.validation.runner.settings", mock_settings):
            runner = ValidationRunner()

            # Create a simple object with __dict__ attribute
            class MockCacheStatus:
                def __init__(self):
                    self.status = "ok"
                    self.count = 5

            mock_cache_status = MockCacheStatus()

            mock_cache_manager = AsyncMock()
            mock_cache_manager.get_cache_status.return_value = mock_cache_status
            mock_cache_manager.is_cache_fresh.return_value = True
            runner.cache_manager = mock_cache_manager

            await runner._test_cache_status()

            # Check that success was recorded with correct details
            successes = [
                item
                for item in runner.results.items
                if item.status == ValidationStatus.SUCCESS and item.test_name == "cache_status"
            ]
            assert len(successes) == 1
            assert successes[0].details["cache_status"] == {"status": "ok", "count": 5}

    @pytest.mark.asyncio
    async def test_cache_status_without_dict_attribute(self, mock_settings):
        """Test cache status when cache_status doesn't have __dict__ attribute."""
        with patch("calendarbot.validation.runner.settings", mock_settings):
            runner = ValidationRunner()

            # Create a mock object without __dict__
            mock_cache_status = "simple_status_string"

            mock_cache_manager = AsyncMock()
            mock_cache_manager.get_cache_status.return_value = mock_cache_status
            mock_cache_manager.is_cache_fresh.return_value = False
            runner.cache_manager = mock_cache_manager

            await runner._test_cache_status()

            # Check that success was recorded with string conversion
            successes = [
                item
                for item in runner.results.items
                if item.status == ValidationStatus.SUCCESS and item.test_name == "cache_status"
            ]
            assert len(successes) == 1
            assert successes[0].details["cache_status"] == "simple_status_string"

    def test_initialization_with_date_range_logging(self, mock_settings):
        """Test initialization logging when end_date differs from test_date."""
        test_date = datetime(2023, 1, 15)
        end_date = datetime(2023, 1, 17)

        with patch("calendarbot.validation.runner.settings", mock_settings):
            with patch("calendarbot.validation.runner.get_validation_logger") as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                runner = ValidationRunner(test_date=test_date, end_date=end_date)

                # Check that date range was logged
                info_calls = [call for call in mock_logger.info.call_args_list]
                assert len(info_calls) >= 3  # At least 3 info calls during initialization

                # Check that date range logging happened
                date_range_logged = any("Date range:" in str(call) for call in info_calls)
                assert date_range_logged

    def test_initialization_without_date_range_logging(self, mock_settings):
        """Test initialization logging when end_date equals test_date."""
        test_date = datetime(2023, 1, 15)

        with patch("calendarbot.validation.runner.settings", mock_settings):
            with patch("calendarbot.validation.runner.get_validation_logger") as mock_get_logger:
                mock_logger = Mock()
                mock_get_logger.return_value = mock_logger

                runner = ValidationRunner(test_date=test_date, end_date=test_date)

                # Check that date range was NOT logged (since dates are the same)
                info_calls = [call for call in mock_logger.info.call_args_list]
                date_range_logged = any("Date range:" in str(call) for call in info_calls)
                assert not date_range_logged
