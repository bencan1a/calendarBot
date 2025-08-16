"""Runtime resource consumption tracking for application performance monitoring."""

import statistics
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import psutil

from ..benchmarking.models import BenchmarkResult, BenchmarkRun, BenchmarkStatus
from ..benchmarking.storage import BenchmarkResultStorage
from ..utils.logging import get_logger
from .performance import (
    MetricType,
    PerformanceLogger,
    PerformanceMetric,
    get_performance_logger,
)


@dataclass
class ResourceSample:
    """Single resource consumption sample."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cpu_percent: float = 0.0
    memory_rss_mb: float = 0.0
    memory_vms_mb: float = 0.0
    memory_percent: float = 0.0


@dataclass
class RuntimeResourceStats:
    """Aggregated runtime resource consumption statistics."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Sample counts
    total_samples: int = 0
    sampling_interval_seconds: float = 1.0

    # CPU statistics
    cpu_median: float = 0.0
    cpu_maximum: float = 0.0
    cpu_minimum: float = 0.0
    cpu_mean: float = 0.0
    cpu_std_deviation: float = 0.0

    # Memory statistics (RSS - Resident Set Size)
    memory_median_mb: float = 0.0
    memory_maximum_mb: float = 0.0
    memory_minimum_mb: float = 0.0
    memory_mean_mb: float = 0.0
    memory_std_deviation_mb: float = 0.0

    # Memory percent statistics
    memory_percent_median: float = 0.0
    memory_percent_maximum: float = 0.0
    memory_percent_minimum: float = 0.0
    memory_percent_mean: float = 0.0
    memory_percent_std_deviation: float = 0.0

    # Additional metadata
    process_pid: int = 0
    app_version: str = ""
    environment: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "total_samples": self.total_samples,
            "sampling_interval_seconds": self.sampling_interval_seconds,
            "cpu_median": self.cpu_median,
            "cpu_maximum": self.cpu_maximum,
            "cpu_minimum": self.cpu_minimum,
            "cpu_mean": self.cpu_mean,
            "cpu_std_deviation": self.cpu_std_deviation,
            "memory_median_mb": self.memory_median_mb,
            "memory_maximum_mb": self.memory_maximum_mb,
            "memory_minimum_mb": self.memory_minimum_mb,
            "memory_mean_mb": self.memory_mean_mb,
            "memory_std_deviation_mb": self.memory_std_deviation_mb,
            "memory_percent_median": self.memory_percent_median,
            "memory_percent_maximum": self.memory_percent_maximum,
            "memory_percent_minimum": self.memory_percent_minimum,
            "memory_percent_mean": self.memory_percent_mean,
            "memory_percent_std_deviation": self.memory_percent_std_deviation,
            "process_pid": self.process_pid,
            "app_version": self.app_version,
            "environment": self.environment,
            "metadata": self.metadata,
        }


class RuntimeResourceTracker:
    """
    Tracks CPU and memory usage during application runtime with minimal overhead.

    Provides background monitoring, statistical analysis, and integration with
    the existing performance monitoring infrastructure.
    """

    def __init__(
        self,
        settings: Optional[Any] = None,
        performance_logger: Optional[PerformanceLogger] = None,
        storage: Optional[BenchmarkResultStorage] = None,
        sampling_interval: float = 1.0,
        save_individual_samples: bool = False,
    ) -> None:
        """
        Initialize the runtime resource tracker.

        Args:
            settings: Application settings object.
            performance_logger: Optional custom performance logger.
            storage: Optional custom storage implementation.
            sampling_interval: Interval between samples in seconds.
            save_individual_samples: Whether to save individual samples to performance logger.
        """
        self.settings = settings
        self.logger = get_logger("monitoring.runtime_tracker")

        # Initialize dependencies
        self.perf_logger = performance_logger or get_performance_logger(settings)
        self.storage = storage or BenchmarkResultStorage(settings=settings)

        # Configuration
        self.sampling_interval = sampling_interval
        self.save_individual_samples = save_individual_samples

        # Tracking state
        self._tracking = False
        self._tracking_thread: Optional[threading.Thread] = None
        self._samples: list[ResourceSample] = []
        self._current_stats: Optional[RuntimeResourceStats] = None
        self._process: Optional[psutil.Process] = None
        self._lock = threading.Lock()

        # Performance thresholds
        self.max_overhead_percentage = 2.0  # Maximum allowed tracking overhead

    def start_tracking(
        self,
        session_name: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Start runtime resource tracking.

        Args:
            session_name: Optional name for this tracking session.
            correlation_id: Optional correlation ID for linking with other metrics.
            metadata: Additional metadata to include with results.

        Returns:
            Session ID for this tracking session.
        """
        if self._tracking:
            self.logger.warning("Runtime tracking already active, stopping previous session")
            self.stop_tracking()

        # Initialize process monitoring
        try:
            self._process = psutil.Process()
            # Establish CPU baseline - first call to cpu_percent() always returns 0.0
            self._process.cpu_percent()
            self.logger.debug("Established CPU monitoring baseline")
        except Exception:
            self.logger.exception("Failed to initialize process monitoring")
            raise

        # Create new tracking session
        self._current_stats = RuntimeResourceStats(
            sampling_interval_seconds=self.sampling_interval,
            process_pid=self._process.pid,
            app_version=self._get_app_version(),
            environment=self._get_environment(),
            metadata=metadata or {},
        )

        if session_name:
            self._current_stats.metadata["session_name"] = session_name
        if correlation_id:
            self._current_stats.metadata["correlation_id"] = correlation_id

        # Clear previous samples
        with self._lock:
            self._samples.clear()
            self._tracking = True

        # Start background monitoring thread
        self._tracking_thread = threading.Thread(
            target=self._monitoring_loop,
            name=f"RuntimeTracker-{self._current_stats.session_id[:8]}",
            daemon=True,
        )
        self._tracking_thread.start()

        self.logger.info(
            f"Started runtime resource tracking (session: {self._current_stats.session_id}, "
            f"interval: {self.sampling_interval}s)"
        )

        # Log tracking start metric
        self.perf_logger.log_metric(
            PerformanceMetric(
                name="runtime_tracking_start",
                metric_type=MetricType.SYSTEM,
                value=time.perf_counter(),
                unit="timestamp",
                component="runtime_tracker",
                operation="start_tracking",
                correlation_id=correlation_id,
                metadata={
                    "session_id": self._current_stats.session_id,
                    "sampling_interval": self.sampling_interval,
                    "session_name": session_name,
                },
            )
        )

        return self._current_stats.session_id

    def stop_tracking(self, save_results: bool = True) -> Optional[RuntimeResourceStats]:
        """
        Stop runtime resource tracking and return aggregated statistics.

        Args:
            save_results: Whether to save results to storage.

        Returns:
            RuntimeResourceStats with aggregated results, or None if no tracking was active.
        """
        if not self._tracking:
            self.logger.warning("No active runtime tracking session to stop")
            return None

        # Stop tracking
        with self._lock:
            self._tracking = False

        # Wait for monitoring thread to finish
        if self._tracking_thread and self._tracking_thread.is_alive():
            self._tracking_thread.join(timeout=5.0)
            if self._tracking_thread.is_alive():
                self.logger.warning("Monitoring thread did not stop gracefully")

        # Calculate final statistics
        stats = self._calculate_statistics()

        if stats and save_results:
            self._save_results(stats)

        # Clean up
        self._current_stats = None
        self._tracking_thread = None

        session_id = stats.session_id if stats else "unknown"
        self.logger.info(f"Stopped runtime resource tracking (session: {session_id})")

        return stats

    def get_current_sample(self) -> Optional[ResourceSample]:
        """
        Get current resource usage sample without affecting tracking.

        Returns:
            Current ResourceSample or None if unable to sample.
        """
        try:
            if not self._process:
                self._process = psutil.Process()

            # Get current CPU and memory usage
            cpu_percent = self._process.cpu_percent()
            memory_info = self._process.memory_info()
            memory_percent = self._process.memory_percent()

            return ResourceSample(
                cpu_percent=cpu_percent,
                memory_rss_mb=float(memory_info.rss) / 1024 / 1024,
                memory_vms_mb=float(memory_info.vms) / 1024 / 1024,
                memory_percent=memory_percent,
            )
        except Exception:
            self.logger.exception("Failed to get current resource sample")
            return None

    @contextmanager
    def track_execution(
        self,
        operation_name: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        save_results: bool = True,
    ):
        """
        Context manager for tracking resource consumption during a specific operation.

        Args:
            operation_name: Name of the operation being tracked.
            correlation_id: Optional correlation ID.
            metadata: Additional metadata.
            save_results: Whether to save results when done.

        Usage:
            with tracker.track_execution("data_processing"):
                # ... operation code ...
                pass
        """
        session_metadata = {"operation": operation_name}
        if metadata:
            session_metadata.update(metadata)

        session_id = self.start_tracking(
            session_name=operation_name,
            correlation_id=correlation_id,
            metadata=session_metadata,
        )

        try:
            yield session_id
        finally:
            self.stop_tracking(save_results=save_results)

    def _monitoring_loop(self) -> None:
        """Background monitoring loop that collects resource samples."""
        self.logger.debug("Starting resource monitoring loop")

        try:
            while self._tracking:
                # Measure overhead
                loop_start = time.perf_counter()

                # Take sample
                sample = self.get_current_sample()
                if sample:
                    with self._lock:
                        self._samples.append(sample)

                    # Optionally save individual samples
                    if self.save_individual_samples:
                        self._log_sample_metrics(sample)

                # Check overhead
                loop_duration = time.perf_counter() - loop_start
                if loop_duration > (self.sampling_interval * self.max_overhead_percentage / 100):
                    self.logger.warning(
                        f"Monitoring loop overhead too high: {loop_duration:.4f}s "
                        f"(>{self.max_overhead_percentage}% of {self.sampling_interval}s interval)"
                    )

                # Sleep until next sample
                sleep_time = max(0, self.sampling_interval - loop_duration)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception:
            self.logger.exception("Error in monitoring loop")
        finally:
            self.logger.debug("Resource monitoring loop finished")

    def _log_sample_metrics(self, sample: ResourceSample) -> None:
        """Log individual sample metrics to performance logger."""
        correlation_id = None
        if self._current_stats:
            correlation_id = self._current_stats.metadata.get("correlation_id")

        # Log CPU metric
        self.perf_logger.log_metric(
            PerformanceMetric(
                name="runtime_cpu_sample",
                metric_type=MetricType.SYSTEM,
                value=sample.cpu_percent,
                unit="percent",
                component="runtime_tracker",
                operation="resource_sampling",
                correlation_id=correlation_id,
                metadata={
                    "session_id": self._current_stats.session_id
                    if self._current_stats
                    else "unknown",
                    "sample_type": "cpu",
                },
            )
        )

        # Log memory metric
        self.perf_logger.log_metric(
            PerformanceMetric(
                name="runtime_memory_sample",
                metric_type=MetricType.MEMORY,
                value=sample.memory_rss_mb,
                unit="MB",
                component="runtime_tracker",
                operation="resource_sampling",
                correlation_id=correlation_id,
                metadata={
                    "session_id": self._current_stats.session_id
                    if self._current_stats
                    else "unknown",
                    "sample_type": "memory_rss",
                    "memory_percent": sample.memory_percent,
                },
            )
        )

    def _calculate_statistics(self) -> Optional[RuntimeResourceStats]:
        """Calculate aggregated statistics from collected samples."""
        if not self._current_stats:
            return None

        with self._lock:
            samples = self._samples.copy()

        if not samples:
            self.logger.warning("No samples collected for statistics calculation")
            return self._current_stats

        # Update timing
        self._current_stats.end_time = datetime.now(timezone.utc)
        self._current_stats.duration_seconds = (
            self._current_stats.end_time - self._current_stats.start_time
        ).total_seconds()
        self._current_stats.total_samples = len(samples)

        # Extract values for statistics
        cpu_values = [s.cpu_percent for s in samples]
        memory_values = [s.memory_rss_mb for s in samples]
        memory_percent_values = [s.memory_percent for s in samples]

        # Calculate CPU statistics
        if cpu_values:
            self._current_stats.cpu_median = statistics.median(cpu_values)
            self._current_stats.cpu_maximum = max(cpu_values)
            self._current_stats.cpu_minimum = min(cpu_values)
            self._current_stats.cpu_mean = statistics.mean(cpu_values)
            if len(cpu_values) > 1:
                self._current_stats.cpu_std_deviation = statistics.stdev(cpu_values)

        # Calculate memory statistics
        if memory_values:
            self._current_stats.memory_median_mb = statistics.median(memory_values)
            self._current_stats.memory_maximum_mb = max(memory_values)
            self._current_stats.memory_minimum_mb = min(memory_values)
            self._current_stats.memory_mean_mb = statistics.mean(memory_values)
            if len(memory_values) > 1:
                self._current_stats.memory_std_deviation_mb = statistics.stdev(memory_values)

        # Calculate memory percent statistics
        if memory_percent_values:
            self._current_stats.memory_percent_median = statistics.median(memory_percent_values)
            self._current_stats.memory_percent_maximum = max(memory_percent_values)
            self._current_stats.memory_percent_minimum = min(memory_percent_values)
            self._current_stats.memory_percent_mean = statistics.mean(memory_percent_values)
            if len(memory_percent_values) > 1:
                self._current_stats.memory_percent_std_deviation = statistics.stdev(
                    memory_percent_values
                )

        return self._current_stats

    def _save_results(self, stats: RuntimeResourceStats) -> None:
        """Save runtime tracking results to storage."""
        try:
            # Create a benchmark run for this runtime tracking session
            run = BenchmarkRun(
                name=f"Runtime Tracking: {stats.metadata.get('session_name', 'Application')}",
                description="Runtime resource consumption tracking session",
                environment=stats.environment,
                app_version=stats.app_version,
                total_benchmarks=2,  # CPU and Memory tracking
            )
            run.start()
            run.complete(success=True)
            run.total_execution_time = stats.duration_seconds
            run.metadata.update(
                {
                    "tracking_type": "runtime_resource_consumption",
                    "session_id": stats.session_id,
                    "sampling_interval": stats.sampling_interval_seconds,
                    "total_samples": stats.total_samples,
                }
            )
            run.metadata.update(stats.metadata)

            # Store the run
            self.storage.store_benchmark_run(run)

            # Prepare comprehensive resource stats for metadata
            resource_stats = {
                "session_id": stats.session_id,
                "duration_seconds": stats.duration_seconds,
                "sample_count": stats.total_samples,
                "sampling_interval": stats.sampling_interval_seconds,
                # CPU statistics
                "cpu_percent_median": stats.cpu_median,
                "cpu_percent_max": stats.cpu_maximum,
                "cpu_percent_min": stats.cpu_minimum,
                "cpu_percent_mean": stats.cpu_mean,
                "cpu_percent_std": stats.cpu_std_deviation,
                # Memory statistics (RSS)
                "memory_rss_mb_median": stats.memory_median_mb,
                "memory_rss_mb_max": stats.memory_maximum_mb,
                "memory_rss_mb_min": stats.memory_minimum_mb,
                "memory_rss_mb_mean": stats.memory_mean_mb,
                "memory_rss_mb_std": stats.memory_std_deviation_mb,
                # Memory percent statistics
                "memory_percent_median": stats.memory_percent_median,
                "memory_percent_max": stats.memory_percent_maximum,
                "memory_percent_min": stats.memory_percent_minimum,
                "memory_percent_mean": stats.memory_percent_mean,
                "memory_percent_std": stats.memory_percent_std_deviation,
                # Process information
                "process_pid": stats.process_pid,
                "app_version": stats.app_version,
                "environment": stats.environment,
            }

            # Create benchmark results for CPU and Memory tracking
            cpu_result = BenchmarkResult(
                run_id=run.run_id,
                benchmark_id="runtime_cpu_tracking",
                benchmark_name="Runtime CPU Usage",
                category="runtime_tracking",
                status=BenchmarkStatus.COMPLETED,
                execution_time=stats.duration_seconds,
                iterations=stats.total_samples,
                min_value=stats.cpu_minimum,
                max_value=stats.cpu_maximum,
                mean_value=stats.cpu_mean,
                median_value=stats.cpu_median,
                std_deviation=stats.cpu_std_deviation,
                app_version=stats.app_version,
                environment=stats.environment,
                correlation_id=stats.metadata.get("correlation_id"),
                metadata={
                    "metric_type": "cpu_percent",
                    "process_pid": stats.process_pid,
                    "resource_stats": resource_stats,
                    **stats.metadata,
                },
            )

            memory_result = BenchmarkResult(
                run_id=run.run_id,
                benchmark_id="runtime_memory_tracking",
                benchmark_name="Runtime Memory Usage",
                category="runtime_tracking",
                status=BenchmarkStatus.COMPLETED,
                execution_time=stats.duration_seconds,
                iterations=stats.total_samples,
                min_value=stats.memory_minimum_mb,
                max_value=stats.memory_maximum_mb,
                mean_value=stats.memory_mean_mb,
                median_value=stats.memory_median_mb,
                std_deviation=stats.memory_std_deviation_mb,
                app_version=stats.app_version,
                environment=stats.environment,
                correlation_id=stats.metadata.get("correlation_id"),
                metadata={
                    "metric_type": "memory_rss_mb",
                    "process_pid": stats.process_pid,
                    "memory_percent_median": stats.memory_percent_median,
                    "memory_percent_maximum": stats.memory_percent_maximum,
                    "resource_stats": resource_stats,
                    **stats.metadata,
                },
            )

            # Store results
            self.storage.store_benchmark_result(cpu_result)
            self.storage.store_benchmark_result(memory_result)

            # Log summary metric
            self.perf_logger.log_metric(
                PerformanceMetric(
                    name="runtime_tracking_complete",
                    metric_type=MetricType.SYSTEM,
                    value=stats.duration_seconds,
                    unit="seconds",
                    component="runtime_tracker",
                    operation="tracking_complete",
                    correlation_id=stats.metadata.get("correlation_id"),
                    metadata={
                        "session_id": stats.session_id,
                        "total_samples": stats.total_samples,
                        "cpu_median": stats.cpu_median,
                        "cpu_maximum": stats.cpu_maximum,
                        "memory_median_mb": stats.memory_median_mb,
                        "memory_maximum_mb": stats.memory_maximum_mb,
                        "run_id": run.run_id,
                    },
                )
            )

            self.logger.info(
                f"Saved runtime tracking results - CPU: {stats.cpu_median:.1f}%/{stats.cpu_maximum:.1f}% "
                f"(median/max), Memory: {stats.memory_median_mb:.1f}MB/{stats.memory_maximum_mb:.1f}MB "
                f"(median/max) over {stats.duration_seconds:.1f}s with {stats.total_samples} samples"
            )

        except Exception:
            self.logger.exception("Failed to save runtime tracking results")

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

    def get_tracking_status(self) -> dict[str, Any]:
        """
        Get current tracking status and statistics.

        Returns:
            Dictionary with current tracking information.
        """
        with self._lock:
            sample_count = len(self._samples)

        status = {
            "tracking_active": self._tracking,
            "session_id": self._current_stats.session_id if self._current_stats else None,
            "sample_count": sample_count,
            "sampling_interval": self.sampling_interval,
            "save_individual_samples": self.save_individual_samples,
        }

        if self._current_stats:
            status.update(
                {
                    "session_start": self._current_stats.start_time.isoformat(),
                    "duration_so_far": (
                        datetime.now(timezone.utc) - self._current_stats.start_time
                    ).total_seconds(),
                    "metadata": self._current_stats.metadata,
                }
            )

        return status


# Global runtime tracker instance
_runtime_tracker: Optional[RuntimeResourceTracker] = None


def get_runtime_tracker(settings: Optional[Any] = None) -> RuntimeResourceTracker:
    """Get or create global runtime tracker instance."""
    from . import NoOpRuntimeResourceTracker, _is_monitoring_enabled  # noqa: PLC0415

    # Access module-level variable without using 'global'
    # This pattern allows reading the variable without the global keyword
    # and modifies it through direct module reference
    if globals()["_runtime_tracker"] is None:
        if _is_monitoring_enabled():
            globals()["_runtime_tracker"] = RuntimeResourceTracker(settings)
        else:
            globals()["_runtime_tracker"] = NoOpRuntimeResourceTracker(settings)
    return globals()["_runtime_tracker"]


def init_runtime_tracking(settings: Any, **kwargs: Any) -> RuntimeResourceTracker:
    """Initialize runtime tracking system with settings."""
    from . import NoOpRuntimeResourceTracker, _is_monitoring_enabled  # noqa: PLC0415

    # Access module-level variable without using 'global'
    if _is_monitoring_enabled():
        globals()["_runtime_tracker"] = RuntimeResourceTracker(settings, **kwargs)
    else:
        globals()["_runtime_tracker"] = NoOpRuntimeResourceTracker(settings, **kwargs)
    return globals()["_runtime_tracker"]
