"""Performance monitoring and metrics collection for CalendarBot."""

from .performance import (
    PerformanceLogger,
    PerformanceMetric,
    MetricType,
    PerformanceLoggerMixin,
    performance_timer,
    performance_monitor,
    memory_monitor,
    cache_monitor,
    get_performance_logger,
    init_performance_logging
)

__all__ = [
    'PerformanceLogger',
    'PerformanceMetric',
    'MetricType',
    'PerformanceLoggerMixin',
    'performance_timer',
    'performance_monitor',
    'memory_monitor',
    'cache_monitor',
    'get_performance_logger',
    'init_performance_logging'
]


# Convenience function for quick access
def get_logger():
    """Get the global performance logger instance."""
    return get_performance_logger()