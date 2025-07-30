"""Production logging optimization and volume reduction for CalendarBot."""

from .production import (
    DebugStatementAnalyzer,
    LoggingOptimizer,
    LogVolumeAnalyzer,
    OptimizationRule,
    OptimizationType,
    ProductionLogFilter,
    analyze_log_volume,
    create_production_filter,
    optimize_logging_config,
)

__all__ = [
    "DebugStatementAnalyzer",
    "LogVolumeAnalyzer",
    "LoggingOptimizer",
    "OptimizationRule",
    "OptimizationType",
    "ProductionLogFilter",
    "analyze_log_volume",
    "create_production_filter",
    "optimize_logging_config",
]


# Convenience functions for quick access
def get_optimizer() -> LoggingOptimizer:
    """Get a logging optimizer instance."""
    return LoggingOptimizer()


def get_volume_analyzer() -> LogVolumeAnalyzer:
    """Get a log volume analyzer instance."""
    return LogVolumeAnalyzer()
