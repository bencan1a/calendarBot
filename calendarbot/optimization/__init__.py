"""Production logging optimization and volume reduction for CalendarBot."""

from .production import (
    LoggingOptimizer,
    OptimizationRule,
    OptimizationType,
    LogVolumeAnalyzer,
    ProductionLogFilter,
    DebugStatementAnalyzer,
    optimize_logging_config,
    analyze_log_volume,
    create_production_filter
)

__all__ = [
    'LoggingOptimizer',
    'OptimizationRule',
    'OptimizationType', 
    'LogVolumeAnalyzer',
    'ProductionLogFilter',
    'DebugStatementAnalyzer',
    'optimize_logging_config',
    'analyze_log_volume',
    'create_production_filter'
]


# Convenience functions for quick access
def get_optimizer():
    """Get a logging optimizer instance."""
    return LoggingOptimizer()

def get_volume_analyzer():
    """Get a log volume analyzer instance."""
    return LogVolumeAnalyzer()