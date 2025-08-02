"""Benchmark execution engine with PerformanceLogger integration."""

import gc
import inspect
import statistics
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

from ..monitoring.performance import (
    MetricType,
    PerformanceLogger,
    PerformanceMetric,
    get_performance_logger,
)
from ..utils.logging import get_logger
from .models import (
    BenchmarkMetadata,
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkStatus,
    BenchmarkSuite,
)
from .storage import BenchmarkResultStorage


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark registration."""

    category: str = "general"
    description: str = ""
    expected_duration_seconds: Optional[float] = None
    min_iterations: int = 1
    max_iterations: int = 10
    warmup_iterations: Optional[int] = None
    timeout_seconds: Optional[float] = None
    tags: Optional[list[str]] = None
    prerequisites: Optional[list[str]] = None


class BenchmarkRunner:
    """
    Central benchmark execution engine that integrates with PerformanceLogger.

    Handles benchmark execution, measurement, and result storage while maintaining
    minimal performance overhead.
    """

    def __init__(
        self,
        settings: Optional[Any] = None,
        storage: Optional[BenchmarkResultStorage] = None,
        performance_logger: Optional[PerformanceLogger] = None,
    ) -> None:
        """
        Initialize the benchmark runner.

        Args:
            settings: Application settings object.
            storage: Optional custom storage implementation.
            performance_logger: Optional custom performance logger.
        """
        self.settings = settings
        self.logger = get_logger("benchmarking.runner")

        # Initialize storage and performance logger
        self.storage = storage or BenchmarkResultStorage(settings=settings)
        self.perf_logger = performance_logger or get_performance_logger(settings)

        # Benchmark registry
        self._benchmark_registry: dict[str, Callable[..., Any]] = {}
        self._benchmark_metadata: dict[str, BenchmarkMetadata] = {}

        # Execution state
        self._current_run: Optional[BenchmarkRun] = None
        self._overhead_tracking = True

        # Performance thresholds
        self.max_overhead_percentage = 5.0  # Maximum allowed overhead
        self.warmup_iterations = 1
        self.default_iterations = 5

    def register_benchmark(
        self,
        name: str,
        func: Callable[..., Any],
        category_or_config: Union[str, BenchmarkConfig, None] = None,
        description: str = "",
        expected_duration_seconds: Optional[float] = None,
        min_iterations: int = 1,
        max_iterations: int = 10,
        warmup_iterations: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        tags: Optional[list[str]] = None,
        prerequisites: Optional[list[str]] = None,
        *,
        category: Optional[str] = None,
    ) -> str:
        """
        Register a benchmark function.

        Args:
            name: Benchmark name.
            func: Function to benchmark.
            category_or_config: Either category string (old API) or BenchmarkConfig object (new API).
            description: Benchmark description (backward compatibility).
            expected_duration_seconds: Expected duration (backward compatibility).
            min_iterations: Minimum iterations (backward compatibility).
            max_iterations: Maximum iterations (backward compatibility).
            warmup_iterations: Warmup iterations (backward compatibility).
            timeout_seconds: Timeout in seconds (backward compatibility).
            tags: Optional tags (backward compatibility).
            prerequisites: Prerequisites (backward compatibility).
            category: Category for backward compatibility (keyword-only).

        Returns:
            Benchmark ID for reference.
        """
        # Handle backward compatibility for category keyword argument
        if category is not None and category_or_config is not None:
            # If both are provided, prefer category_or_config but warn
            self.logger.warning(
                "Both 'category' and 'category_or_config' provided. Using 'category_or_config'."
            )
        elif category is not None and category_or_config is None:
            # Use category keyword argument (old API)
            category_or_config = category

        # Handle backward compatibility
        if isinstance(category_or_config, BenchmarkConfig):
            config = category_or_config
        elif isinstance(category_or_config, str):
            # Old API: third parameter is category
            config = BenchmarkConfig(
                category=category_or_config,
                description=description,
                expected_duration_seconds=expected_duration_seconds,
                min_iterations=min_iterations,
                max_iterations=max_iterations,
                warmup_iterations=warmup_iterations,
                timeout_seconds=timeout_seconds,
                tags=tags,
                prerequisites=prerequisites,
            )
        else:
            # Default case (None)
            config = BenchmarkConfig(
                category="general",
                description=description,
                expected_duration_seconds=expected_duration_seconds,
                min_iterations=min_iterations,
                max_iterations=max_iterations,
                warmup_iterations=warmup_iterations,
                timeout_seconds=timeout_seconds,
                tags=tags,
                prerequisites=prerequisites,
            )

        benchmark_id = str(uuid.uuid4())

        # Create metadata
        metadata = BenchmarkMetadata(
            benchmark_id=benchmark_id,
            name=name,
            description=config.description or f"Benchmark for {func.__name__}",
            category=config.category,
            expected_duration_seconds=config.expected_duration_seconds,
            min_iterations=config.min_iterations,
            max_iterations=config.max_iterations,
            warmup_iterations=config.warmup_iterations or self.warmup_iterations,
            timeout_seconds=config.timeout_seconds,
            tags=config.tags or [],
            prerequisites=config.prerequisites or [],
        )

        # Store in registry
        self._benchmark_registry[benchmark_id] = func
        self._benchmark_metadata[benchmark_id] = metadata

        # Store metadata persistently
        self.storage.store_benchmark_metadata(metadata)

        self.logger.info(f"Registered benchmark '{name}' with ID {benchmark_id}")
        return benchmark_id

    def benchmark(
        self,
        name: Optional[str] = None,
        category: str = "general",
        description: str = "",
        iterations: Optional[int] = None,
        warmup_iterations: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        tags: Optional[list[str]] = None,
    ) -> Callable[..., Any]:
        """
        Decorator for registering benchmark functions.

        Args:
            name: Benchmark name (defaults to function name).
            category: Benchmark category.
            description: Benchmark description.
            iterations: Number of iterations to run.
            warmup_iterations: Number of warmup iterations.
            timeout_seconds: Timeout for benchmark execution.
            tags: Optional tags for categorization.

        Returns:
            Decorated function.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            benchmark_name = name or func.__name__
            config = BenchmarkConfig(
                category=category,
                description=description or f"Benchmark for {func.__name__}",
                max_iterations=iterations or self.default_iterations,
                warmup_iterations=warmup_iterations,
                timeout_seconds=timeout_seconds,
                tags=tags,
            )
            self.register_benchmark(
                name=benchmark_name,
                func=func,
                category_or_config=config,
            )
            return func

        return decorator

    def run_benchmark(  # noqa: PLR0915
        self,
        benchmark_id: str,
        iterations: Optional[int] = None,
        warmup_iterations: Optional[int] = None,
        correlation_id: Optional[str] = None,
        **kwargs: Any,
    ) -> BenchmarkResult:
        """
        Run a single benchmark.

        Args:
            benchmark_id: ID of the benchmark to run.
            iterations: Number of iterations (overrides metadata).
            warmup_iterations: Number of warmup iterations (overrides metadata).
            correlation_id: Optional correlation ID for tracking.
            **kwargs: Additional arguments to pass to benchmark function.

        Returns:
            BenchmarkResult with timing and statistics.

        Raises:
            ValueError: If benchmark ID not found.
            TimeoutError: If benchmark exceeds timeout.
        """
        # Validate benchmark exists
        if benchmark_id not in self._benchmark_registry:
            raise ValueError(f"Benchmark {benchmark_id} not found in registry")

        func = self._benchmark_registry[benchmark_id]
        metadata = self._benchmark_metadata[benchmark_id]

        # Determine iterations
        actual_iterations = iterations or metadata.max_iterations
        actual_warmup = warmup_iterations or metadata.warmup_iterations

        # Ensure we have a benchmark run for storing results
        if not self._current_run:
            # Create a temporary run for this standalone benchmark
            temp_run = BenchmarkRun(
                name=f"Standalone: {metadata.name}",
                description=f"Individual benchmark run for {metadata.name}",
                environment=self._get_environment(),
                app_version=self._get_app_version(),
                total_benchmarks=1,
            )
            temp_run.start()

            # Store the run so we can reference it
            self.storage.store_benchmark_run(temp_run)
            run_id = temp_run.run_id
        else:
            run_id = self._current_run.run_id

        # Create result object
        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            benchmark_name=metadata.name,
            category=metadata.category,
            run_id=run_id,
            iterations=actual_iterations,
            app_version=self._get_app_version(),
            environment=self._get_environment(),
            correlation_id=correlation_id,
        )

        correlation_id = correlation_id or result.result_id

        try:
            result.status = BenchmarkStatus.RUNNING

            # Log benchmark start
            self.perf_logger.log_metric(
                PerformanceMetric(
                    name="benchmark_start",
                    metric_type=MetricType.TIMER,
                    value=time.perf_counter(),
                    unit="timestamp",
                    component="benchmark_runner",
                    operation=metadata.name,
                    correlation_id=correlation_id,
                    metadata={"benchmark_id": benchmark_id, "iterations": actual_iterations},
                )
            )

            # Run warmup iterations
            if actual_warmup > 0:
                self.logger.debug(f"Running {actual_warmup} warmup iterations for {metadata.name}")
                for _ in range(actual_warmup):
                    self._execute_function_safely(func, metadata.timeout_seconds, **kwargs)

            # Measure overhead if enabled
            overhead_start_time = None
            overhead_end_time = None
            if self._overhead_tracking:
                overhead_start_time = time.perf_counter()

            # Run actual benchmark iterations
            self.logger.info(
                f"Running benchmark '{metadata.name}' for {actual_iterations} iterations"
            )
            execution_times = []

            for iteration in range(actual_iterations):
                # Force garbage collection before timing
                gc.collect()

                # Time the execution
                start_time = time.perf_counter()

                try:
                    with self._performance_context(metadata.name, correlation_id):
                        self._execute_function_safely(func, metadata.timeout_seconds, **kwargs)
                except Exception as e:
                    self.logger.exception(f"Benchmark iteration {iteration} failed")
                    result.status = BenchmarkStatus.FAILED
                    result.error_message = str(e)
                    return result

                end_time = time.perf_counter()
                execution_time = end_time - start_time
                execution_times.append(execution_time)

            # Calculate overhead
            if self._overhead_tracking and overhead_start_time:
                overhead_end_time = time.perf_counter()
                total_benchmark_time = sum(execution_times)
                total_elapsed_time = overhead_end_time - overhead_start_time

                if total_elapsed_time > 0:
                    overhead_percentage = (
                        (total_elapsed_time - total_benchmark_time) / total_elapsed_time
                    ) * 100
                    result.overhead_percentage = overhead_percentage

                    # Log warning if overhead is too high
                    if overhead_percentage > self.max_overhead_percentage:
                        self.logger.warning(
                            f"Benchmark overhead ({overhead_percentage:.2f}%) exceeds threshold "
                            f"({self.max_overhead_percentage}%)"
                        )

            # Calculate statistics
            result.execution_time = sum(execution_times)
            result.min_value = min(execution_times)
            result.max_value = max(execution_times)
            result.mean_value = statistics.mean(execution_times)
            result.median_value = statistics.median(execution_times)
            result.std_deviation = (
                statistics.stdev(execution_times) if len(execution_times) > 1 else 0.0
            )
            result.status = BenchmarkStatus.COMPLETED

            # Log completion
            self.perf_logger.log_metric(
                PerformanceMetric(
                    name="benchmark_complete",
                    metric_type=MetricType.TIMER,
                    value=result.execution_time,
                    unit="seconds",
                    component="benchmark_runner",
                    operation=metadata.name,
                    correlation_id=correlation_id,
                    metadata={
                        "benchmark_id": benchmark_id,
                        "iterations": actual_iterations,
                        "mean_time": result.mean_value,
                        "std_deviation": result.std_deviation,
                        "overhead_percentage": result.overhead_percentage,
                    },
                )
            )

            # Store result
            self.storage.store_benchmark_result(result)

            self.logger.info(
                f"Benchmark '{metadata.name}' completed: {result.mean_value:.4f}s avg "
                f"({result.min_value:.4f}s-{result.max_value:.4f}s)"
            )

        except Exception as e:
            self.logger.exception(f"Benchmark '{metadata.name}' failed")
            result.status = BenchmarkStatus.FAILED
            result.error_message = str(e)
            self.storage.store_benchmark_result(result)

        return result

    def run_benchmark_suite(
        self, suite: Union[BenchmarkSuite, str], correlation_id: Optional[str] = None
    ) -> BenchmarkRun:
        """
        Run a complete benchmark suite.

        Args:
            suite: BenchmarkSuite object or suite ID.
            correlation_id: Optional correlation ID for tracking.

        Returns:
            BenchmarkRun with aggregated results.
        """
        # Resolve suite
        if isinstance(suite, str):
            # In a full implementation, this would load from storage
            raise NotImplementedError("Loading suites by ID not yet implemented")

        suite_obj = suite
        correlation_id = correlation_id or str(uuid.uuid4())

        # Create run object
        run = BenchmarkRun(
            name=f"Suite: {suite_obj.name}",
            description=suite_obj.description,
            suite_id=suite_obj.suite_id,
            benchmark_ids=suite_obj.benchmark_ids.copy(),
            environment=self._get_environment(),
            app_version=self._get_app_version(),
        )

        # Set current run context
        self._current_run = run
        run.start()

        try:
            self.logger.info(
                f"Starting benchmark suite '{suite_obj.name}' with {len(suite_obj.benchmark_ids)} benchmarks"
            )

            results = []

            for benchmark_id in suite_obj.benchmark_ids:
                if benchmark_id not in self._benchmark_registry:
                    self.logger.warning(f"Benchmark {benchmark_id} not found in registry, skipping")
                    continue

                try:
                    result = self.run_benchmark(benchmark_id, correlation_id=correlation_id)
                    results.append(result)

                    # Check if we should stop on failure
                    if suite_obj.stop_on_failure and result.status == BenchmarkStatus.FAILED:
                        self.logger.warning(
                            f"Stopping suite execution due to failure in {benchmark_id}"
                        )
                        break

                except Exception:
                    self.logger.exception(f"Failed to run benchmark {benchmark_id}")
                    if suite_obj.stop_on_failure:
                        break

            # Update run statistics
            run.update_statistics(results)
            run.complete(success=run.failed_benchmarks == 0)

            # Update suite last run info
            suite_obj.last_run_id = run.run_id
            suite_obj.last_run_timestamp = run.completed_at
            suite_obj.last_run_status = run.status
            self.storage.store_benchmark_suite(suite_obj)

            self.logger.info(
                f"Completed benchmark suite '{suite_obj.name}': "
                f"{run.completed_benchmarks}/{run.total_benchmarks} successful "
                f"(Success rate: {run.success_rate:.1f}%)"
            )

        except Exception as e:
            self.logger.exception(f"Suite '{suite_obj.name}' failed")
            run.complete(success=False)
            run.error_message = str(e)
        finally:
            # Store run results
            self.storage.store_benchmark_run(run)
            self._current_run = None

        return run

    def _execute_function_safely(
        self, func: Callable[..., Any], timeout_seconds: Optional[float], **kwargs: Any
    ) -> Any:
        """
        Execute a function with optional timeout.

        Args:
            func: Function to execute.
            timeout_seconds: Optional timeout.
            **kwargs: Arguments to pass to function.

        Returns:
            Function result.

        Raises:
            TimeoutError: If function exceeds timeout.
        """
        # Simple timeout implementation
        start_time = time.perf_counter()

        # Get function signature to determine if it accepts arguments
        sig = inspect.signature(func)
        result = func(**kwargs) if sig.parameters else func()

        # Check timeout
        if timeout_seconds and (time.perf_counter() - start_time) > timeout_seconds:
            raise TimeoutError(f"Function exceeded timeout of {timeout_seconds} seconds")

        return result

    @contextmanager
    def _performance_context(self, operation: str, correlation_id: str):
        """Context manager for performance monitoring during benchmark execution."""
        timer_id = self.perf_logger.start_timer(
            operation=operation, component="benchmark_execution", correlation_id=correlation_id
        )

        try:
            yield timer_id
        finally:
            self.perf_logger.stop_timer(
                timer_id=timer_id,
                component="benchmark_execution",
                operation=operation,
                correlation_id=correlation_id,
            )

    def _get_app_version(self) -> str:
        """Get application version from settings or default."""
        if self.settings and hasattr(self.settings, "version"):
            return self.settings.version
        return "unknown"

    def _get_environment(self) -> str:
        """Get environment from settings or default."""
        if self.settings and hasattr(self.settings, "environment"):
            return self.settings.environment
        return "development"

    def get_benchmark_metadata(self, benchmark_id: str) -> Optional[BenchmarkMetadata]:
        """
        Get metadata for a registered benchmark.

        Args:
            benchmark_id: Benchmark ID.

        Returns:
            BenchmarkMetadata if found, None otherwise.
        """
        return self._benchmark_metadata.get(benchmark_id)

    def list_benchmarks(self, category: Optional[str] = None) -> list[BenchmarkMetadata]:
        """
        List all registered benchmarks.

        Args:
            category: Optional category filter.

        Returns:
            List of BenchmarkMetadata objects.
        """
        benchmarks = list(self._benchmark_metadata.values())

        if category:
            benchmarks = [b for b in benchmarks if b.category == category]

        return benchmarks

    def create_suite(
        self,
        name: str,
        benchmark_ids: list[str],
        description: str = "",
        parallel_execution: bool = False,
        stop_on_failure: bool = False,
        max_execution_time_seconds: Optional[float] = None,
        tags: Optional[list[str]] = None,
    ) -> BenchmarkSuite:
        """
        Create a new benchmark suite.

        Args:
            name: Suite name.
            benchmark_ids: List of benchmark IDs to include.
            description: Suite description.
            parallel_execution: Whether to run benchmarks in parallel.
            stop_on_failure: Whether to stop on first failure.
            max_execution_time_seconds: Maximum total execution time.
            tags: Optional tags for categorization.

        Returns:
            BenchmarkSuite object.
        """
        # Validate benchmark IDs
        invalid_ids = [bid for bid in benchmark_ids if bid not in self._benchmark_registry]
        if invalid_ids:
            raise ValueError(f"Invalid benchmark IDs: {invalid_ids}")

        suite = BenchmarkSuite(
            name=name,
            description=description,
            benchmark_ids=benchmark_ids,
            parallel_execution=parallel_execution,
            stop_on_failure=stop_on_failure,
            max_execution_time_seconds=max_execution_time_seconds,
            tags=tags or [],
            created_by="benchmark_runner",
        )

        # Store suite
        self.storage.store_benchmark_suite(suite)

        self.logger.info(f"Created benchmark suite '{name}' with {len(benchmark_ids)} benchmarks")
        return suite

    def get_performance_summary(self, hours: int = 24) -> dict[str, Any]:
        """
        Get performance summary from the performance logger.

        Args:
            hours: Number of hours to look back.

        Returns:
            Performance summary dictionary.
        """
        return self.perf_logger.get_performance_summary(hours)

    def cleanup_old_results(self, days_to_keep: int = 90) -> int:
        """
        Clean up old benchmark results.

        Args:
            days_to_keep: Number of days of results to keep.

        Returns:
            Number of records deleted.
        """
        return self.storage.cleanup_old_results(days_to_keep)
