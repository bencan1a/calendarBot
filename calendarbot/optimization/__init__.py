"""Performance optimization modules for CalendarBot."""

from typing import Any

from .static_asset_cache import StaticAssetCache


# Placeholder classes for logging system compatibility
class LoggingOptimizer:
    """Placeholder logging optimizer for compatibility."""

    def __init__(self, settings: Any) -> None:
        """Initialize with empty rules."""
        self.rules: list[Any] = []


class ProductionLogFilter:
    """Placeholder log filter for compatibility."""

    def __init__(self, rules: Any, settings: Any) -> None:
        """Initialize filter."""
        self.rules = rules
        self.settings = settings

    def filter(self, record: Any) -> bool:
        """Allow all log records through."""
        return True


__all__ = ["LoggingOptimizer", "ProductionLogFilter", "StaticAssetCache"]
