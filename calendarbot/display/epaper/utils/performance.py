"""
Performance monitoring utilities for e-paper display operations.

This module provides tools for tracking performance metrics of e-paper rendering
and display operations, optimized for resource-constrained environments like
the Raspberry Pi Zero 2W.
"""

import time
from typing import Optional


class PerformanceMetrics:
    """
    Track performance metrics for e-paper operations.

    Provides lightweight timing and memory usage tracking for performance-critical
    operations in the e-paper rendering pipeline, with minimal overhead suitable
    for resource-constrained environments.
    """

    def __init__(self) -> None:
        """Initialize performance metrics tracking."""
        self._operation_timers: dict[str, float] = {}
        self._operation_results: dict[str, float] = {}

    def start_operation(self, operation_name: str) -> None:
        """
        Start timing an operation.

        Args:
            operation_name: Name of the operation to time
        """
        self._operation_timers[operation_name] = time.time() * 1000  # Store in milliseconds

    def end_operation(self, operation_name: str) -> float:
        """
        End timing an operation and record the result.

        Args:
            operation_name: Name of the operation to end timing

        Returns:
            Duration of the operation in milliseconds

        Raises:
            KeyError: If operation_name was not started
        """
        if operation_name not in self._operation_timers:
            raise KeyError(f"Operation '{operation_name}' was not started")

        end_time = time.time() * 1000
        start_time = self._operation_timers.pop(operation_name)
        duration = end_time - start_time

        # Store the result
        self._operation_results[operation_name] = duration
        return duration

    def get_operation_time(self, operation_name: str) -> Optional[float]:
        """
        Get the duration of a completed operation.

        Args:
            operation_name: Name of the operation

        Returns:
            Duration in milliseconds or None if not found
        """
        return self._operation_results.get(operation_name)

    def reset(self) -> None:
        """Reset all performance metrics."""
        self._operation_timers.clear()
        self._operation_results.clear()

    def get_summary(self) -> dict[str, float]:
        """
        Get a summary of all completed operations.

        Returns:
            Dictionary of operation names and durations
        """
        return self._operation_results.copy()
