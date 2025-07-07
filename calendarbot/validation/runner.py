"""Validation runner for coordinating component testing in test mode."""

import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import settings

from .logging_setup import get_validation_logger, log_validation_result, log_validation_start
from .results import ValidationResults, ValidationStatus


class ValidationRunner:
    """Coordinates validation testing of Calendar Bot components."""

    def __init__(
        self,
        test_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        components: Optional[List[str]] = None,
        use_cache: bool = True,
        output_format: str = "console",
    ):
        """Initialize validation runner.

        Args:
            test_date: Date to test (default: today)
            end_date: End date for range testing (default: same as test_date)
            components: List of components to test (default: all)
            use_cache: Whether to use cached data when available
            output_format: Output format ('console' or 'json')
        """
        self.test_date = test_date or datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        self.end_date = end_date or self.test_date
        self.components = components or ["sources", "cache", "display"]
        self.use_cache = use_cache
        self.output_format = output_format
        self.settings = settings

        # Initialize results tracking
        self.results = ValidationResults()

        # Get logger
        self.logger = get_validation_logger("validation")

        # Component instances (to be initialized during run)
        self.source_manager = None
        self.cache_manager = None
        self.display_manager = None

        self.logger.info(f"ValidationRunner initialized for {self.test_date.date()}")
        if self.end_date != self.test_date:
            self.logger.info(f"Date range: {self.test_date.date()} to {self.end_date.date()}")
        self.logger.info(f"Components to test: {', '.join(self.components)}")

    async def run_validation(self) -> ValidationResults:
        """Run complete validation suite.

        Returns:
            ValidationResults with all test outcomes
        """
        try:
            self.logger.info("Starting Calendar Bot validation")

            # Initialize components
            await self._initialize_components()

            # Run validations for each requested component
            if "sources" in self.components:
                await self._validate_source_connectivity()

            if "cache" in self.components:
                await self._validate_cache_operations()

            if "display" in self.components:
                await self._validate_display_functionality()

            # Finalize results
            self.results.finalize()
            self.logger.info("Validation completed")

            return self.results

        except Exception as e:
            self.logger.error(f"Validation runner error: {e}")
            self.results.add_failure("system", "validation_runner", f"Runner error: {str(e)}")
            self.results.finalize()
            return self.results
        finally:
            await self._cleanup_components()

    async def _initialize_components(self) -> None:
        """Initialize Calendar Bot components for testing."""
        try:
            log_validation_start(self.logger, "component_initialization")
            start_time = time.time()

            # Import components
            from calendarbot.cache import CacheManager
            from calendarbot.display import DisplayManager
            from calendarbot.sources import SourceManager

            # Initialize components
            self.source_manager = SourceManager(self.settings)
            self.cache_manager = CacheManager(self.settings)
            self.display_manager = DisplayManager(self.settings)

            duration_ms = int((time.time() - start_time) * 1000)

            self.results.add_success(
                "system",
                "component_initialization",
                "Components initialized successfully",
                {
                    "sources": bool(self.source_manager),
                    "cache": bool(self.cache_manager),
                    "display": bool(self.display_manager),
                },
                duration_ms,
            )

            log_validation_result(
                self.logger, "component_initialization", True, "Components initialized", duration_ms
            )

        except Exception as e:
            self.results.add_failure(
                "system", "component_initialization", f"Failed to initialize components: {str(e)}"
            )
            log_validation_result(self.logger, "component_initialization", False, str(e))
            raise

    async def _cleanup_components(self) -> None:
        """Clean up component resources."""
        try:
            if self.cache_manager:
                await self.cache_manager.cleanup_old_events()
            self.logger.debug("Component cleanup completed")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")

    async def _validate_source_connectivity(self) -> None:
        """Validate source connectivity functionality."""
        self.logger.info("Validating source connectivity")

        # Test source manager initialization
        await self._test_source_manager_init()

        # Test source health checks
        await self._test_source_health_checks()

        # Test ICS fetching
        await self._test_ics_fetch()

    async def _test_source_manager_init(self) -> None:
        """Test source manager initialization."""
        test_name = "source_manager_init"
        log_validation_start(self.logger, test_name)
        start_time = time.time()

        try:
            # Test source manager properties
            source_count = len(self.source_manager.sources)
            has_primary_source = bool(getattr(self.settings, "ics_url", None))

            duration_ms = int((time.time() - start_time) * 1000)

            self.results.add_success(
                "sources",
                test_name,
                "Source manager initialized successfully",
                {
                    "source_count": source_count,
                    "has_primary_source": has_primary_source,
                    "ics_url_configured": bool(getattr(self.settings, "ics_url", None)),
                },
                duration_ms,
            )

            log_validation_result(
                self.logger, test_name, True, f"Sources: {source_count}", duration_ms
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure(
                "sources",
                test_name,
                f"Source manager init error: {str(e)}",
                duration_ms=duration_ms,
            )
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)

    async def _test_source_health_checks(self) -> None:
        """Test source health checks."""
        test_name = "source_health_checks"
        log_validation_start(self.logger, test_name)
        start_time = time.time()

        try:
            # Perform health checks on all sources
            health_status = await self.source_manager.get_health_status()
            duration_ms = int((time.time() - start_time) * 1000)

            healthy_sources = sum(1 for source in health_status if health_status[source].is_healthy)
            total_sources = len(health_status)

            if total_sources == 0:
                self.results.add_warning(
                    "sources", test_name, "No sources configured", {"total_sources": 0}, duration_ms
                )
                log_validation_result(
                    self.logger, test_name, True, "No sources configured", duration_ms
                )
            elif healthy_sources > 0:
                self.results.add_success(
                    "sources",
                    test_name,
                    f"Source health checks completed - {healthy_sources}/{total_sources} healthy",
                    {
                        "healthy_sources": healthy_sources,
                        "total_sources": total_sources,
                        "health_status": {
                            name: status.is_healthy for name, status in health_status.items()
                        },
                    },
                    duration_ms,
                )
                log_validation_result(
                    self.logger,
                    test_name,
                    True,
                    f"{healthy_sources}/{total_sources} healthy",
                    duration_ms,
                )
            else:
                self.results.add_failure(
                    "sources",
                    test_name,
                    f"All sources unhealthy - {healthy_sources}/{total_sources} healthy",
                    duration_ms=duration_ms,
                )
                log_validation_result(
                    self.logger, test_name, False, "All sources unhealthy", duration_ms
                )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure(
                "sources",
                test_name,
                f"Source health check error: {str(e)}",
                duration_ms=duration_ms,
            )
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)

    async def _test_ics_fetch(self) -> None:
        """Test ICS calendar fetching."""
        test_name = "ics_fetch"
        log_validation_start(self.logger, test_name)
        start_time = time.time()

        try:
            # Try to fetch events from sources
            events = await self.source_manager.fetch_events()
            duration_ms = int((time.time() - start_time) * 1000)

            self.results.add_success(
                "sources",
                test_name,
                f"ICS fetch successful - {len(events)} events retrieved",
                {"events_count": len(events), "test_date": self.test_date.date().isoformat()},
                duration_ms,
            )

            log_validation_result(
                self.logger, test_name, True, f"{len(events)} events retrieved", duration_ms
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure(
                "sources", test_name, f"ICS fetch error: {str(e)}", duration_ms=duration_ms
            )
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)

    async def _validate_cache_operations(self) -> None:
        """Validate cache functionality."""
        self.logger.info("Validating cache operations")

        # Test cache initialization
        await self._test_cache_init()

        # Test cache operations
        await self._test_cache_operations()

        # Test cache status
        await self._test_cache_status()

    async def _test_cache_init(self) -> None:
        """Test cache initialization."""
        test_name = "cache_initialization"
        log_validation_start(self.logger, test_name)
        start_time = time.time()

        try:
            init_success = await self.cache_manager.initialize()
            duration_ms = int((time.time() - start_time) * 1000)

            if init_success:
                self.results.add_success(
                    "cache",
                    test_name,
                    "Cache initialized successfully",
                    {
                        "initialized": init_success,
                        "database_path": str(self.settings.database_file),
                    },
                    duration_ms,
                )
                log_validation_result(
                    self.logger, test_name, True, "Cache initialized", duration_ms
                )
            else:
                self.results.add_failure(
                    "cache", test_name, "Cache initialization failed", duration_ms=duration_ms
                )
                log_validation_result(
                    self.logger, test_name, False, "Cache init failed", duration_ms
                )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure(
                "cache", test_name, f"Cache init error: {str(e)}", duration_ms=duration_ms
            )
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)

    async def _test_cache_operations(self) -> None:
        """Test basic cache operations."""
        test_name = "cache_operations"
        log_validation_start(self.logger, test_name)
        start_time = time.time()

        try:
            # Test getting cached events
            cached_events = await self.cache_manager.get_todays_cached_events()

            # Test cache summary
            cache_summary = await self.cache_manager.get_cache_summary()

            duration_ms = int((time.time() - start_time) * 1000)

            self.results.add_success(
                "cache",
                test_name,
                f"Cache operations successful - {len(cached_events)} cached events",
                {"cached_events_count": len(cached_events), "cache_summary": cache_summary},
                duration_ms,
            )

            log_validation_result(
                self.logger, test_name, True, f"{len(cached_events)} cached events", duration_ms
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure(
                "cache", test_name, f"Cache operations error: {str(e)}", duration_ms=duration_ms
            )
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)

    async def _test_cache_status(self) -> None:
        """Test cache status reporting."""
        test_name = "cache_status"
        log_validation_start(self.logger, test_name)
        start_time = time.time()

        try:
            cache_status = await self.cache_manager.get_cache_status()
            is_fresh = await self.cache_manager.is_cache_fresh()

            duration_ms = int((time.time() - start_time) * 1000)

            self.results.add_success(
                "cache",
                test_name,
                f"Cache status check successful - fresh: {is_fresh}",
                {
                    "is_fresh": is_fresh,
                    "cache_status": (
                        cache_status.__dict__
                        if hasattr(cache_status, "__dict__")
                        else str(cache_status)
                    ),
                },
                duration_ms,
            )

            log_validation_result(
                self.logger, test_name, True, f"Cache fresh: {is_fresh}", duration_ms
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure(
                "cache", test_name, f"Cache status error: {str(e)}", duration_ms=duration_ms
            )
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)

    async def _validate_display_functionality(self) -> None:
        """Validate display functionality."""
        self.logger.info("Validating display functionality")

        # Test display initialization
        await self._test_display_init()

        # Test display rendering (with mock data)
        await self._test_display_rendering()

    async def _test_display_init(self) -> None:
        """Test display manager initialization."""
        test_name = "display_initialization"
        log_validation_start(self.logger, test_name)
        start_time = time.time()

        try:
            # Test display manager properties
            display_type = self.display_manager.settings.display_type
            display_enabled = self.display_manager.settings.display_enabled

            duration_ms = int((time.time() - start_time) * 1000)

            self.results.add_success(
                "display",
                test_name,
                "Display manager initialized",
                {"display_type": display_type, "display_enabled": display_enabled},
                duration_ms,
            )

            log_validation_result(
                self.logger, test_name, True, f"Display type: {display_type}", duration_ms
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure(
                "display", test_name, f"Display init error: {str(e)}", duration_ms=duration_ms
            )
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)

    async def _test_display_rendering(self) -> None:
        """Test display rendering with mock data."""
        test_name = "display_rendering"
        log_validation_start(self.logger, test_name)
        start_time = time.time()

        try:
            # Create mock status info
            status_info = {
                "last_update": datetime.now(),
                "is_cached": False,
                "connection_status": "Online",
                "total_events": 0,
                "consecutive_failures": 0,
            }

            # Test display with empty events (validation mode)
            display_success = await self.display_manager.display_events([], status_info)

            duration_ms = int((time.time() - start_time) * 1000)

            if display_success:
                self.results.add_success(
                    "display",
                    test_name,
                    "Display rendering successful",
                    {"render_success": display_success, "status_info": status_info},
                    duration_ms,
                )
                log_validation_result(
                    self.logger, test_name, True, "Display rendering OK", duration_ms
                )
            else:
                self.results.add_failure(
                    "display", test_name, "Display rendering failed", duration_ms=duration_ms
                )
                log_validation_result(
                    self.logger, test_name, False, "Display rendering failed", duration_ms
                )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.results.add_failure(
                "display", test_name, f"Display rendering error: {str(e)}", duration_ms=duration_ms
            )
            log_validation_result(self.logger, test_name, False, str(e), duration_ms)

    def get_results(self) -> ValidationResults:
        """Get validation results.

        Returns:
            ValidationResults instance
        """
        return self.results

    def print_results(self, verbose: bool = False) -> None:
        """Print validation results in requested format.

        Args:
            verbose: Whether to show verbose output
        """
        if self.output_format == "json":
            self.results.print_json_report()
        else:
            self.results.print_console_report(verbose)
