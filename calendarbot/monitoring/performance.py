"""Comprehensive performance monitoring and metrics collection system."""

import json
import logging
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import psutil

from ..utils.logging import get_logger


class MetricType(Enum):
    """Types of performance metrics."""

    TIMER = "timer"
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    MEMORY = "memory"
    CACHE = "cache"
    REQUEST = "request"
    DATABASE = "database"
    SYSTEM = "system"


@dataclass
class PerformanceMetric:
    """Structured performance metric data."""

    metric_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    metric_type: MetricType = MetricType.GAUGE
    value: Union[float, int, str] = 0
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    component: str = ""
    operation: str = ""
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary for logging."""
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "component": self.component,
            "operation": self.operation,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }


class PerformanceLogger:
    """Centralized performance metrics logging and collection."""

    def __init__(self, settings: Optional[Any] = None):
        self.settings = settings
        self.logger = get_logger("performance")
        self.metrics_logger = self._setup_metrics_logger()
        self._metrics_cache: List[PerformanceMetric] = []
        self._operation_timers: Dict[str, float] = {}
        self.cache_size = 2000
        self._lock = threading.Lock()

        # Performance thresholds for alerting
        self.thresholds = {
            "request_duration_warning": 5.0,  # seconds
            "request_duration_error": 15.0,  # seconds
            "memory_usage_warning": 500,  # MB
            "memory_usage_error": 1000,  # MB
            "cache_miss_rate_warning": 0.3,  # 30%
            "cache_miss_rate_error": 0.6,  # 60%
        }

    def _setup_metrics_logger(self) -> logging.Logger:
        """Set up dedicated metrics logger."""
        metrics_logger = logging.getLogger("calendarbot.performance.metrics")
        metrics_logger.setLevel(logging.INFO)

        # Clear existing handlers
        metrics_logger.handlers.clear()

        # Create metrics log directory
        if self.settings and hasattr(self.settings, "data_dir"):
            metrics_dir = Path(self.settings.data_dir) / "performance" / "metrics"
        else:
            metrics_dir = (
                Path.home() / ".local" / "share" / "calendarbot" / "performance" / "metrics"
            )

        metrics_dir.mkdir(parents=True, exist_ok=True)

        # Set up file handler with rotation
        from logging.handlers import RotatingFileHandler

        metrics_file = metrics_dir / "performance_metrics.log"

        metrics_handler = RotatingFileHandler(
            metrics_file, maxBytes=100 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 100MB
        )

        # JSON formatter for metrics
        metrics_formatter = logging.Formatter(
            "%(asctime)s - PERFORMANCE - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        metrics_handler.setFormatter(metrics_formatter)
        metrics_logger.addHandler(metrics_handler)

        # Prevent propagation to avoid duplication
        metrics_logger.propagate = False

        return metrics_logger

    def log_metric(self, metric: PerformanceMetric):
        """
        Log a performance metric.

        Args:
            metric: PerformanceMetric to log
        """
        try:
            with self._lock:
                # Add to cache
                self._add_to_cache(metric)

                # Convert to structured log message
                metric_dict = metric.to_dict()
                metric_json = json.dumps(metric_dict, separators=(",", ":"))

                # Log to metrics logger
                self.metrics_logger.info(metric_json)

                # Check thresholds and alert if necessary
                self._check_thresholds(metric)

        except Exception as e:
            self.logger.error(f"Failed to log performance metric: {e}")

    def start_timer(
        self, operation: str, component: str = "", correlation_id: Optional[str] = None
    ) -> str:
        """
        Start a timer for an operation.

        Args:
            operation: Name of the operation being timed
            component: Component performing the operation
            correlation_id: Optional correlation ID for tracking

        Returns:
            Timer ID for stopping the timer
        """
        timer_id = f"{operation}_{uuid.uuid4().hex[:8]}"

        with self._lock:
            self._operation_timers[timer_id] = time.perf_counter()

        # Log timer start
        start_metric = PerformanceMetric(
            name=f"{operation}_start",
            metric_type=MetricType.TIMER,
            value=time.perf_counter(),
            unit="timestamp",
            component=component,
            operation=operation,
            correlation_id=correlation_id,
            metadata={"timer_id": timer_id, "action": "start"},
        )
        self.log_metric(start_metric)

        return timer_id

    def stop_timer(
        self,
        timer_id: str,
        component: str = "",
        operation: str = "",
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Stop a timer and log the duration.

        Args:
            timer_id: Timer ID from start_timer
            component: Component performing the operation
            operation: Operation name
            correlation_id: Optional correlation ID
            metadata: Additional metadata to include

        Returns:
            Duration in seconds
        """
        end_time = time.perf_counter()

        with self._lock:
            start_time = self._operation_timers.pop(timer_id, None)

        if start_time is None:
            self.logger.warning(f"Timer {timer_id} not found")
            return 0.0

        duration = end_time - start_time

        # Log timer completion
        timer_metric = PerformanceMetric(
            name=f"{operation}_duration" if operation else "operation_duration",
            metric_type=MetricType.TIMER,
            value=duration,
            unit="seconds",
            component=component,
            operation=operation,
            correlation_id=correlation_id,
            metadata={
                "timer_id": timer_id,
                "action": "complete",
                "start_time": start_time,
                "end_time": end_time,
                **(metadata or {}),
            },
        )
        self.log_metric(timer_metric)

        return duration

    def log_request_performance(
        self,
        method: str,
        url: str,
        duration: float,
        status_code: int,
        component: str = "http_client",
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log HTTP request performance metrics."""
        request_metric = PerformanceMetric(
            name="http_request_duration",
            metric_type=MetricType.REQUEST,
            value=duration,
            unit="seconds",
            component=component,
            operation=f"{method} {url}",
            correlation_id=correlation_id,
            metadata={
                "method": method,
                "url": url,
                "status_code": status_code,
                "success": 200 <= status_code < 300,
                **(metadata or {}),
            },
        )
        self.log_metric(request_metric)

    def log_memory_usage(
        self,
        component: str = "system",
        operation: str = "memory_check",
        correlation_id: Optional[str] = None,
    ):
        """Log current memory usage metrics."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            # Log RSS (Resident Set Size) memory
            rss_metric = PerformanceMetric(
                name="memory_rss",
                metric_type=MetricType.MEMORY,
                value=memory_info.rss / 1024 / 1024,  # Convert to MB
                unit="MB",
                component=component,
                operation=operation,
                correlation_id=correlation_id,
                metadata={
                    "memory_type": "rss",
                    "vms": memory_info.vms / 1024 / 1024,  # Virtual memory
                    "pid": process.pid,
                },
            )
            self.log_metric(rss_metric)

            # System memory usage
            system_memory = psutil.virtual_memory()
            system_metric = PerformanceMetric(
                name="system_memory_usage",
                metric_type=MetricType.SYSTEM,
                value=system_memory.percent,
                unit="percent",
                component=component,
                operation=operation,
                correlation_id=correlation_id,
                metadata={
                    "total_mb": system_memory.total / 1024 / 1024,
                    "available_mb": system_memory.available / 1024 / 1024,
                    "used_mb": system_memory.used / 1024 / 1024,
                },
            )
            self.log_metric(system_metric)

        except Exception as e:
            self.logger.error(f"Failed to log memory usage: {e}")

    def log_cache_performance(
        self,
        cache_name: str,
        hits: int,
        misses: int,
        total_requests: int,
        component: str = "cache",
        correlation_id: Optional[str] = None,
    ):
        """Log cache performance metrics."""
        hit_rate = hits / total_requests if total_requests > 0 else 0
        miss_rate = misses / total_requests if total_requests > 0 else 0

        cache_metric = PerformanceMetric(
            name=f"{cache_name}_hit_rate",
            metric_type=MetricType.CACHE,
            value=hit_rate,
            unit="ratio",
            component=component,
            operation="cache_performance",
            correlation_id=correlation_id,
            metadata={
                "cache_name": cache_name,
                "hits": hits,
                "misses": misses,
                "total_requests": total_requests,
                "miss_rate": miss_rate,
            },
        )
        self.log_metric(cache_metric)

    def log_database_performance(
        self,
        query_type: str,
        duration: float,
        rows_affected: int = 0,
        component: str = "database",
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log database operation performance."""
        db_metric = PerformanceMetric(
            name="database_query_duration",
            metric_type=MetricType.DATABASE,
            value=duration,
            unit="seconds",
            component=component,
            operation=query_type,
            correlation_id=correlation_id,
            metadata={"query_type": query_type, "rows_affected": rows_affected, **(metadata or {})},
        )
        self.log_metric(db_metric)

    def _check_thresholds(self, metric: PerformanceMetric):
        """Check if metric exceeds defined thresholds and log warnings/errors."""
        if metric.metric_type == MetricType.REQUEST and "duration" in metric.name:
            duration = float(metric.value)
            if duration > self.thresholds["request_duration_error"]:
                self.logger.error(
                    f"Request duration critical: {duration:.2f}s exceeds {self.thresholds['request_duration_error']}s threshold"
                )
            elif duration > self.thresholds["request_duration_warning"]:
                self.logger.warning(
                    f"Request duration high: {duration:.2f}s exceeds {self.thresholds['request_duration_warning']}s threshold"
                )

        elif metric.metric_type == MetricType.MEMORY and "rss" in metric.name:
            memory_mb = float(metric.value)
            if memory_mb > self.thresholds["memory_usage_error"]:
                self.logger.error(
                    f"Memory usage critical: {memory_mb:.1f}MB exceeds {self.thresholds['memory_usage_error']}MB threshold"
                )
            elif memory_mb > self.thresholds["memory_usage_warning"]:
                self.logger.warning(
                    f"Memory usage high: {memory_mb:.1f}MB exceeds {self.thresholds['memory_usage_warning']}MB threshold"
                )

        elif metric.metric_type == MetricType.CACHE and "hit_rate" in metric.name:
            miss_rate = metric.metadata.get("miss_rate", 0)
            if miss_rate > self.thresholds["cache_miss_rate_error"]:
                self.logger.error(
                    f"Cache miss rate critical: {miss_rate:.1%} exceeds {self.thresholds['cache_miss_rate_error']:.1%} threshold"
                )
            elif miss_rate > self.thresholds["cache_miss_rate_warning"]:
                self.logger.warning(
                    f"Cache miss rate high: {miss_rate:.1%} exceeds {self.thresholds['cache_miss_rate_warning']:.1%} threshold"
                )

    def _add_to_cache(self, metric: PerformanceMetric):
        """Add metric to in-memory cache."""
        self._metrics_cache.append(metric)

        # Maintain cache size limit
        if len(self._metrics_cache) > self.cache_size:
            self._metrics_cache = self._metrics_cache[-self.cache_size :]

    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance summary for the specified time period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_metrics = [m for m in self._metrics_cache if m.timestamp > cutoff_time]

        if not recent_metrics:
            return {"total_metrics": 0, "time_period_hours": hours}

        # Group metrics by type
        by_type = {}
        for metric_type in MetricType:
            type_metrics = [m for m in recent_metrics if m.metric_type == metric_type]
            if type_metrics:
                by_type[metric_type.value] = {
                    "count": len(type_metrics),
                    "avg_value": sum(
                        float(m.value) for m in type_metrics if isinstance(m.value, (int, float))
                    )
                    / len(type_metrics),
                }

        # Calculate average request duration
        request_metrics = [m for m in recent_metrics if m.metric_type == MetricType.REQUEST]
        avg_request_duration = 0
        if request_metrics:
            durations = [
                float(m.value) for m in request_metrics if isinstance(m.value, (int, float))
            ]
            avg_request_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total_metrics": len(recent_metrics),
            "time_period_hours": hours,
            "by_type": by_type,
            "avg_request_duration": avg_request_duration,
            "oldest_metric": min(m.timestamp for m in recent_metrics).isoformat(),
            "newest_metric": max(m.timestamp for m in recent_metrics).isoformat(),
        }


class PerformanceLoggerMixin:
    """Mixin class to add performance logging capabilities to any class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._perf_logger = get_performance_logger()

    def start_performance_timer(self, operation: str, correlation_id: Optional[str] = None) -> str:
        """Start a performance timer for this component."""
        component = self.__class__.__name__
        return self._perf_logger.start_timer(operation, component, correlation_id)

    def stop_performance_timer(
        self,
        timer_id: str,
        operation: str = "",
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Stop a performance timer for this component."""
        component = self.__class__.__name__
        return self._perf_logger.stop_timer(
            timer_id, component, operation, correlation_id, metadata
        )

    def log_performance_metric(
        self,
        name: str,
        value: Union[float, int],
        metric_type: MetricType = MetricType.GAUGE,
        unit: str = "",
        operation: str = "",
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log a performance metric for this component."""
        component = self.__class__.__name__
        metric = PerformanceMetric(
            name=name,
            metric_type=metric_type,
            value=value,
            unit=unit,
            component=component,
            operation=operation,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
        self._perf_logger.log_metric(metric)


@contextmanager
def performance_timer(
    operation: str,
    component: str = "",
    correlation_id: Optional[str] = None,
    logger: Optional[PerformanceLogger] = None,
):
    """
    Context manager for timing operations.

    Usage:
        with performance_timer("fetch_events", "source_manager"):
            # ... operation code ...
            pass
    """
    perf_logger = logger or get_performance_logger()
    timer_id = perf_logger.start_timer(operation, component, correlation_id)
    start_time = time.perf_counter()

    try:
        yield timer_id
    finally:
        duration = perf_logger.stop_timer(timer_id, component, operation, correlation_id)


def performance_monitor(
    operation: str = "",
    component: str = "",
    track_memory: bool = False,
    correlation_id: Optional[str] = None,
):
    """
    Decorator for automatic performance monitoring of functions.

    Args:
        operation: Operation name (defaults to function name)
        component: Component name (defaults to module name)
        track_memory: Whether to track memory usage before/after
        correlation_id: Optional correlation ID

    Usage:
        @performance_monitor(operation="fetch_events", track_memory=True)
        def fetch_calendar_events():
            # ... function code ...
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            perf_logger = get_performance_logger()
            op_name = operation or func.__name__
            comp_name = component or func.__module__.split(".")[-1]

            # Track memory before if requested
            if track_memory:
                perf_logger.log_memory_usage(comp_name, f"{op_name}_start", correlation_id)

            # Time the operation
            with performance_timer(op_name, comp_name, correlation_id):
                result = func(*args, **kwargs)

            # Track memory after if requested
            if track_memory:
                perf_logger.log_memory_usage(comp_name, f"{op_name}_end", correlation_id)

            return result

        return wrapper

    return decorator


@contextmanager
def memory_monitor(
    component: str = "system",
    operation: str = "memory_check",
    correlation_id: Optional[str] = None,
    logger: Optional[PerformanceLogger] = None,
):
    """
    Context manager for monitoring memory usage during operations.

    Usage:
        with memory_monitor("cache_manager", "load_events"):
            # ... operation that uses memory ...
            pass
    """
    perf_logger = logger or get_performance_logger()

    # Log memory before operation
    perf_logger.log_memory_usage(component, f"{operation}_start", correlation_id)

    try:
        yield
    finally:
        # Log memory after operation
        perf_logger.log_memory_usage(component, f"{operation}_end", correlation_id)


@contextmanager
def cache_monitor(
    cache_name: str,
    component: str = "cache",
    correlation_id: Optional[str] = None,
    logger: Optional[PerformanceLogger] = None,
):
    """
    Context manager for monitoring cache performance.

    Usage:
        with cache_monitor("events_cache") as monitor:
            # ... cache operations ...
            monitor.record_hit()  # or monitor.record_miss()
    """
    perf_logger = logger or get_performance_logger()

    class CacheMonitor:
        def __init__(self):
            self.hits = 0
            self.misses = 0

        def record_hit(self):
            self.hits += 1

        def record_miss(self):
            self.misses += 1

        @property
        def total_requests(self):
            return self.hits + self.misses

    monitor = CacheMonitor()

    try:
        yield monitor
    finally:
        if monitor.total_requests > 0:
            perf_logger.log_cache_performance(
                cache_name,
                monitor.hits,
                monitor.misses,
                monitor.total_requests,
                component,
                correlation_id,
            )


# Global performance logger instance
_performance_logger: Optional[PerformanceLogger] = None


def get_performance_logger(settings: Optional[Any] = None) -> PerformanceLogger:
    """Get or create global performance logger instance."""
    global _performance_logger
    if _performance_logger is None:
        _performance_logger = PerformanceLogger(settings)
    return _performance_logger


def init_performance_logging(settings: Any):
    """Initialize performance logging system with settings."""
    global _performance_logger
    _performance_logger = PerformanceLogger(settings)
    return _performance_logger
