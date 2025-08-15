"""Phase 2A performance monitoring for connection pooling and request pipeline optimization."""

import time
from dataclasses import dataclass
from typing import Any, Optional

from ..config.optimization import OptimizationConfig, get_optimization_config
from ..utils.logging import get_logger
from .performance import MetricType, PerformanceMetric, get_performance_logger


@dataclass
class ConnectionPoolMetrics:
    """Metrics for connection pool monitoring."""

    active_connections: int = 0
    idle_connections: int = 0
    total_connections: int = 0
    max_connections: int = 0
    pool_utilization: float = 0.0
    connection_acquisitions: int = 0
    connection_releases: int = 0
    acquisition_wait_time: float = 0.0
    failed_acquisitions: int = 0

    @property
    def utilization_percentage(self) -> float:
        """Calculate connection pool utilization as percentage."""
        if self.max_connections == 0:
            return 0.0
        return (self.total_connections / self.max_connections) * 100.0


@dataclass
class RequestPipelineMetrics:
    """Metrics for request pipeline monitoring."""

    cache_hits: int = 0
    cache_misses: int = 0
    total_requests: int = 0
    cached_request_duration: float = 0.0
    uncached_request_duration: float = 0.0
    batch_requests: int = 0
    single_requests: int = 0
    average_batch_size: float = 0.0
    ttl_expirations: int = 0

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate as ratio."""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests

    @property
    def cache_miss_rate(self) -> float:
        """Calculate cache miss rate as ratio."""
        return 1.0 - self.cache_hit_rate

    @property
    def batch_efficiency(self) -> float:
        """Calculate batching efficiency ratio."""
        if self.total_requests == 0:
            return 0.0
        return self.batch_requests / self.total_requests


class Phase2AMonitor:
    """Specialized monitoring for Phase 2A connection pooling and request pipeline optimizations."""

    def __init__(self, optimization_config: Optional[OptimizationConfig] = None):
        """Initialize Phase 2A monitor.

        Args:
            optimization_config: Optional optimization configuration
        """
        self.config = optimization_config or get_optimization_config()
        self.perf_logger = get_performance_logger()
        self.logger = get_logger("phase_2a_monitor")

        # Metrics tracking
        self.connection_pool_metrics = ConnectionPoolMetrics()
        self.request_pipeline_metrics = RequestPipelineMetrics()

        # Timing state
        self._request_timers: dict[str, float] = {}
        self._monitoring_start_time = time.time()

        # Warning/error thresholds from config
        self.memory_warning_threshold = self.config.memory_warning_threshold_mb
        self.latency_warning_threshold = (
            self.config.latency_warning_threshold_ms / 1000.0
        )  # Convert to seconds
        self.cache_hit_rate_warning = self.config.cache_hit_rate_warning

    def log_connection_pool_status(
        self,
        active: int,
        idle: int,
        max_connections: int,
        component: str = "connection_pool",
        correlation_id: Optional[str] = None,
    ) -> None:
        """Log current connection pool status.

        Args:
            active: Number of active connections
            idle: Number of idle connections
            max_connections: Maximum allowed connections
            component: Component name for logging
            correlation_id: Optional correlation ID
        """
        # Update metrics
        self.connection_pool_metrics.active_connections = active
        self.connection_pool_metrics.idle_connections = idle
        self.connection_pool_metrics.total_connections = active + idle
        self.connection_pool_metrics.max_connections = max_connections
        self.connection_pool_metrics.pool_utilization = (
            self.connection_pool_metrics.utilization_percentage
        )

        # Log individual metrics
        metrics_to_log = [
            ("connection_pool_active", active, "count"),
            ("connection_pool_idle", idle, "count"),
            ("connection_pool_total", active + idle, "count"),
            (
                "connection_pool_utilization",
                self.connection_pool_metrics.utilization_percentage,
                "percent",
            ),
        ]

        for name, value, unit in metrics_to_log:
            metric = PerformanceMetric(
                name=name,
                metric_type=MetricType.GAUGE,
                value=value,
                unit=unit,
                component=component,
                operation="pool_status",
                correlation_id=correlation_id,
                metadata={
                    "max_connections": max_connections,
                    "active": active,
                    "idle": idle,
                },
            )
            self.perf_logger.log_metric(metric)

        # Check thresholds
        if self.connection_pool_metrics.utilization_percentage > 90.0:
            self.logger.error(
                f"Connection pool utilization critical: {self.connection_pool_metrics.utilization_percentage:.1f}%"
            )
        elif self.connection_pool_metrics.utilization_percentage > 75.0:
            self.logger.warning(
                f"Connection pool utilization high: {self.connection_pool_metrics.utilization_percentage:.1f}%"
            )

    def log_connection_acquisition(
        self,
        wait_time: float,
        success: bool = True,
        component: str = "connection_pool",
        correlation_id: Optional[str] = None,
    ) -> None:
        """Log connection acquisition event.

        Args:
            wait_time: Time waited to acquire connection in seconds
            success: Whether acquisition was successful
            component: Component name for logging
            correlation_id: Optional correlation ID
        """
        if success:
            self.connection_pool_metrics.connection_acquisitions += 1
            self.connection_pool_metrics.acquisition_wait_time += wait_time
        else:
            self.connection_pool_metrics.failed_acquisitions += 1

        metric = PerformanceMetric(
            name="connection_acquisition",
            metric_type=MetricType.TIMER,
            value=wait_time,
            unit="seconds",
            component=component,
            operation="acquire_connection",
            correlation_id=correlation_id,
            metadata={
                "success": success,
                "total_acquisitions": self.connection_pool_metrics.connection_acquisitions,
                "failed_acquisitions": self.connection_pool_metrics.failed_acquisitions,
            },
        )
        self.perf_logger.log_metric(metric)

        # Check acquisition time threshold
        if wait_time > 1.0:
            self.logger.warning(f"Connection acquisition slow: {wait_time:.2f}s")

    def log_connection_release(
        self, component: str = "connection_pool", correlation_id: Optional[str] = None
    ) -> None:
        """Log connection release event.

        Args:
            component: Component name for logging
            correlation_id: Optional correlation ID
        """
        self.connection_pool_metrics.connection_releases += 1

        metric = PerformanceMetric(
            name="connection_release",
            metric_type=MetricType.COUNTER,
            value=1,
            unit="count",
            component=component,
            operation="release_connection",
            correlation_id=correlation_id,
            metadata={
                "total_releases": self.connection_pool_metrics.connection_releases,
            },
        )
        self.perf_logger.log_metric(metric)

    def start_request_timer(self, request_id: str, is_cached: bool = False) -> None:
        """Start timing a request.

        Args:
            request_id: Unique identifier for the request
            is_cached: Whether this request will use cache
        """
        self._request_timers[request_id] = time.perf_counter()

    def log_request_completion(
        self,
        request_id: str,
        cache_hit: bool = False,
        was_batched: bool = False,
        batch_size: int = 1,
        component: str = "request_pipeline",
        correlation_id: Optional[str] = None,
    ) -> float:
        """Log completion of a request with caching and batching info.

        Args:
            request_id: Unique identifier for the request
            cache_hit: Whether this was a cache hit
            was_batched: Whether this request was part of a batch
            batch_size: Size of the batch (1 for single requests)
            component: Component name for logging
            correlation_id: Optional correlation ID

        Returns:
            Request duration in seconds
        """
        start_time = self._request_timers.pop(request_id, None)
        if start_time is None:
            self.logger.warning(f"Request timer not found for {request_id}")
            return 0.0

        duration = time.perf_counter() - start_time

        # Update metrics
        self.request_pipeline_metrics.total_requests += 1

        if cache_hit:
            self.request_pipeline_metrics.cache_hits += 1
            self.request_pipeline_metrics.cached_request_duration += duration
        else:
            self.request_pipeline_metrics.cache_misses += 1
            self.request_pipeline_metrics.uncached_request_duration += duration

        if was_batched:
            self.request_pipeline_metrics.batch_requests += 1
            # Update average batch size incrementally
            old_avg = self.request_pipeline_metrics.average_batch_size
            batch_count = self.request_pipeline_metrics.batch_requests
            self.request_pipeline_metrics.average_batch_size = (
                (old_avg * (batch_count - 1)) + batch_size
            ) / batch_count
        else:
            self.request_pipeline_metrics.single_requests += 1

        # Log request metric
        metric = PerformanceMetric(
            name="request_pipeline_duration",
            metric_type=MetricType.REQUEST,
            value=duration,
            unit="seconds",
            component=component,
            operation="process_request",
            correlation_id=correlation_id,
            metadata={
                "cache_hit": cache_hit,
                "was_batched": was_batched,
                "batch_size": batch_size,
                "request_id": request_id,
            },
        )
        self.perf_logger.log_metric(metric)

        # Check latency threshold
        if duration > self.latency_warning_threshold:
            self.logger.warning(f"Request latency high: {duration:.2f}s (cache_hit={cache_hit})")

        return duration

    def log_cache_performance(
        self, component: str = "request_pipeline", correlation_id: Optional[str] = None
    ) -> None:
        """Log current cache performance metrics.

        Args:
            component: Component name for logging
            correlation_id: Optional correlation ID
        """
        if self.request_pipeline_metrics.total_requests == 0:
            return

        hit_rate = self.request_pipeline_metrics.cache_hit_rate
        miss_rate = self.request_pipeline_metrics.cache_miss_rate

        metrics_to_log = [
            ("cache_hit_rate", hit_rate, "ratio"),
            ("cache_miss_rate", miss_rate, "ratio"),
            ("cache_hits", self.request_pipeline_metrics.cache_hits, "count"),
            ("cache_misses", self.request_pipeline_metrics.cache_misses, "count"),
        ]

        for name, value, unit in metrics_to_log:
            metric = PerformanceMetric(
                name=name,
                metric_type=MetricType.CACHE,
                value=value,
                unit=unit,
                component=component,
                operation="cache_performance",
                correlation_id=correlation_id,
                metadata={
                    "total_requests": self.request_pipeline_metrics.total_requests,
                    "hit_rate": hit_rate,
                    "miss_rate": miss_rate,
                },
            )
            self.perf_logger.log_metric(metric)

        # Check cache hit rate threshold
        if hit_rate < self.cache_hit_rate_warning:
            self.logger.warning(
                f"Cache hit rate low: {hit_rate:.1%} (target: {self.cache_hit_rate_warning:.1%})"
            )

    def log_ttl_expiration(
        self,
        expired_items: int = 1,
        component: str = "request_pipeline",
        correlation_id: Optional[str] = None,
    ) -> None:
        """Log TTL cache expiration events.

        Args:
            expired_items: Number of items that expired
            component: Component name for logging
            correlation_id: Optional correlation ID
        """
        self.request_pipeline_metrics.ttl_expirations += expired_items

        metric = PerformanceMetric(
            name="ttl_expiration",
            metric_type=MetricType.COUNTER,
            value=expired_items,
            unit="count",
            component=component,
            operation="cache_expiration",
            correlation_id=correlation_id,
            metadata={
                "total_expirations": self.request_pipeline_metrics.ttl_expirations,
            },
        )
        self.perf_logger.log_metric(metric)

    def get_phase_2a_summary(self) -> dict[str, Any]:
        """Get comprehensive Phase 2A performance summary.

        Returns:
            Dictionary containing all Phase 2A metrics and derived statistics
        """
        uptime = time.time() - self._monitoring_start_time

        # Calculate average request times
        avg_cached_time = 0.0
        avg_uncached_time = 0.0

        if self.request_pipeline_metrics.cache_hits > 0:
            avg_cached_time = (
                self.request_pipeline_metrics.cached_request_duration
                / self.request_pipeline_metrics.cache_hits
            )

        if self.request_pipeline_metrics.cache_misses > 0:
            avg_uncached_time = (
                self.request_pipeline_metrics.uncached_request_duration
                / self.request_pipeline_metrics.cache_misses
            )

        return {
            "monitoring_uptime_seconds": uptime,
            "connection_pool": {
                "active_connections": self.connection_pool_metrics.active_connections,
                "idle_connections": self.connection_pool_metrics.idle_connections,
                "total_connections": self.connection_pool_metrics.total_connections,
                "max_connections": self.connection_pool_metrics.max_connections,
                "utilization_percentage": self.connection_pool_metrics.utilization_percentage,
                "total_acquisitions": self.connection_pool_metrics.connection_acquisitions,
                "failed_acquisitions": self.connection_pool_metrics.failed_acquisitions,
                "total_releases": self.connection_pool_metrics.connection_releases,
                "avg_acquisition_wait_time": (
                    self.connection_pool_metrics.acquisition_wait_time
                    / max(1, self.connection_pool_metrics.connection_acquisitions)
                ),
            },
            "request_pipeline": {
                "total_requests": self.request_pipeline_metrics.total_requests,
                "cache_hits": self.request_pipeline_metrics.cache_hits,
                "cache_misses": self.request_pipeline_metrics.cache_misses,
                "cache_hit_rate": self.request_pipeline_metrics.cache_hit_rate,
                "cache_miss_rate": self.request_pipeline_metrics.cache_miss_rate,
                "batch_requests": self.request_pipeline_metrics.batch_requests,
                "single_requests": self.request_pipeline_metrics.single_requests,
                "batch_efficiency": self.request_pipeline_metrics.batch_efficiency,
                "average_batch_size": self.request_pipeline_metrics.average_batch_size,
                "ttl_expirations": self.request_pipeline_metrics.ttl_expirations,
                "avg_cached_request_time": avg_cached_time,
                "avg_uncached_request_time": avg_uncached_time,
                "cache_speedup_factor": (
                    avg_uncached_time / max(0.001, avg_cached_time) if avg_cached_time > 0 else 1.0
                ),
            },
            "performance_assessment": {
                "connection_pool_healthy": self.connection_pool_metrics.utilization_percentage
                < 75.0,
                "cache_performance_good": self.request_pipeline_metrics.cache_hit_rate
                >= self.cache_hit_rate_warning,
                "latency_acceptable": avg_uncached_time < self.latency_warning_threshold,
                "optimization_effective": (
                    self.request_pipeline_metrics.cache_hit_rate >= 0.3
                    and self.connection_pool_metrics.utilization_percentage < 90.0
                ),
            },
        }


# Global Phase 2A monitor instance
_phase_2a_monitor: Optional[Phase2AMonitor] = None


def get_phase_2a_monitor(
    optimization_config: Optional[OptimizationConfig] = None,
) -> Phase2AMonitor:
    """Get or create global Phase 2A monitor instance.

    Args:
        optimization_config: Optional optimization configuration

    Returns:
        Phase2AMonitor instance
    """
    global _phase_2a_monitor  # noqa: PLW0603
    if _phase_2a_monitor is None:
        _phase_2a_monitor = Phase2AMonitor(optimization_config)
    return _phase_2a_monitor


def reset_phase_2a_monitor() -> None:
    """Reset the global Phase 2A monitor (for testing)."""
    global _phase_2a_monitor  # noqa: PLW0603
    _phase_2a_monitor = None
