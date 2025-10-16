"""Performance monitoring and metrics collection for CalendarBot."""

import os
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any, Optional, Union

from .performance import (
    MetricType,
    PerformanceLogger as _PerformanceLogger,
    PerformanceLoggerMixin as _PerformanceLoggerMixin,
    PerformanceMetric,
    cache_monitor as _cache_monitor,
    get_performance_logger as _get_performance_logger,
    init_performance_logging as _init_performance_logging,
    memory_monitor as _memory_monitor,
    performance_monitor as _performance_monitor,
    performance_timer as _performance_timer,
    set_monitoring_enabled as _set_monitoring_enabled,
)


def _is_monitoring_enabled() -> bool:
    """Determine whether monitoring should be enabled.

    Priority:
      1. Environment variable CALENDARBOT_MONITORING (if set)
      2. settings.monitoring.enabled (if available)
      3. If optimization.small_device is True, prefer to disable monitoring by default
      4. Fallback to True
    """
    env = os.getenv("CALENDARBOT_MONITORING")
    if env is not None:
        return env.lower() in ("true", "1", "yes", "on")
    try:
        from calendarbot.config.settings import get_settings  # noqa: PLC0415

        settings = get_settings()
        mon = getattr(settings, "monitoring", None)
        if mon is not None:
            return bool(getattr(mon, "enabled", True))
        if getattr(settings, "optimization", None) and getattr(
            settings.optimization, "small_device", False
        ):
            return False
    except Exception:
        pass
    return True


class NoOpPerformanceLogger:
    """No-operation performance logger that does nothing when monitoring is disabled."""

    def __init__(self, settings: Optional[Any] = None) -> None:
        pass

    def log_metric(self, metric: PerformanceMetric) -> None:
        pass

    def start_timer(
        self, operation: str, component: str = "", correlation_id: Optional[str] = None
    ) -> str:
        return "noop-timer"

    def stop_timer(
        self,
        timer_id: str,
        component: str = "",
        operation: str = "",
        correlation_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> float:
        return 0.0

    def log_request_performance(
        self,
        method: str,
        url: str,
        duration: float,
        status_code: int,
        component: str = "http_client",
        correlation_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        pass

    def log_memory_usage(
        self,
        component: str = "system",
        operation: str = "memory_check",
        correlation_id: Optional[str] = None,
    ) -> None:
        pass

    def log_cache_performance(
        self,
        cache_name: str,
        hits: int,
        misses: int,
        total_requests: int,
        component: str = "cache",
        correlation_id: Optional[str] = None,
    ) -> None:
        pass

    def log_database_performance(
        self,
        query_type: str,
        duration: float,
        rows_affected: int = 0,
        component: str = "database",
        correlation_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        pass

    def get_performance_summary(self, hours: int = 1) -> dict[str, Any]:
        return {"total_metrics": 0, "time_period_hours": hours, "monitoring_disabled": True}


class NoOpRuntimeResourceTracker:
    """No-operation runtime resource tracker when monitoring is disabled."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def start_tracking(
        self,
        session_name: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        return "noop-session"

    def stop_tracking(self, save_results: bool = True) -> Optional[Any]:
        return None

    def get_current_sample(self) -> Optional[Any]:
        return None

    def track_execution(
        self,
        operation_name: str,
        correlation_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        save_results: bool = True,
    ) -> Any:
        from contextlib import nullcontext  # noqa: PLC0415

        return nullcontext("noop-session")

    def get_tracking_status(self) -> dict[str, Any]:
        return {"tracking_active": False, "session_id": None, "sample_count": 0}


class NoOpPerformanceLoggerMixin:
    """No-operation mixin that provides no monitoring when disabled."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._perf_logger = NoOpPerformanceLogger()

    def start_performance_timer(self, operation: str, correlation_id: Optional[str] = None) -> str:
        return "noop-timer"

    def stop_performance_timer(
        self,
        timer_id: str,
        operation: str = "",
        correlation_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> float:
        return 0.0

    def log_performance_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        unit: str = "",
        operation: str = "",
        correlation_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        pass


@contextmanager
def noop_context_manager(*_args: Any, **_kwargs: Any) -> Any:
    """No-operation context manager that yields a no-op object."""

    class NoOpMonitor:
        def record_hit(self) -> None:
            pass

        def record_miss(self) -> None:
            pass

        @property
        def total_requests(self) -> int:
            return 0

    yield NoOpMonitor()


def noop_decorator(*args: Any, **kwargs: Any) -> Callable[..., Any]:  # noqa: ARG001
    """No-operation decorator that returns the original function unchanged."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    return decorator


# Conditional exports based on environment variable
if _is_monitoring_enabled():
    PerformanceLogger = _PerformanceLogger
    PerformanceLoggerMixin = _PerformanceLoggerMixin
    cache_monitor = _cache_monitor
    get_performance_logger = _get_performance_logger
    init_performance_logging = _init_performance_logging
    memory_monitor = _memory_monitor
    performance_monitor = _performance_monitor
    performance_timer = _performance_timer
    set_monitoring_enabled = _set_monitoring_enabled
else:
    PerformanceLogger = NoOpPerformanceLogger  # type: ignore[misc, assignment]
    PerformanceLoggerMixin = NoOpPerformanceLoggerMixin  # type: ignore[misc, assignment]
    cache_monitor = noop_context_manager
    get_performance_logger = lambda settings=None: NoOpPerformanceLogger(settings)  # type: ignore[assignment, return-value] # noqa: E731
    init_performance_logging = lambda settings: NoOpPerformanceLogger(settings)  # type: ignore[assignment, return-value] # noqa: E731
    memory_monitor = noop_context_manager
    performance_monitor = noop_decorator
    performance_timer = noop_context_manager

    # Provide a runtime setter that replaces the global logger with a noop when monitoring is disabled.
    def set_monitoring_enabled(enabled: bool, settings: Optional[Any] = None) -> None:
        """Runtime setter (noop) used when monitoring is disabled.

        Signature intentionally matches the exported implementation from the performance
        module (enabled: bool, settings: Optional[Any] = None) so static type
        checkers and callers can assign/replace this symbol without parameter-name
        mismatches.
        """
        # Explicitly acknowledge unused parameters to satisfy linters.
        del enabled, settings


__all__ = [
    "MetricType",
    "PerformanceLogger",
    "PerformanceLoggerMixin",
    "PerformanceMetric",
    "cache_monitor",
    "get_performance_logger",
    "init_performance_logging",
    "memory_monitor",
    "performance_monitor",
    "performance_timer",
]


# Convenience function for quick access
def get_logger() -> Union[_PerformanceLogger, NoOpPerformanceLogger]:
    """Get the global performance logger instance."""
    return get_performance_logger()
