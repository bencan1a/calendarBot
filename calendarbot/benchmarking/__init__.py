"""CalendarBot Performance Benchmarking System.

This module provides comprehensive benchmarking capabilities for CalendarBot,
including benchmark execution, result storage, and performance analysis.
"""

from .models import (
    BenchmarkMetadata,
    BenchmarkResult,
    BenchmarkStatus,
    BenchmarkSuite,
)
from .runner import BenchmarkRunner
from .storage import BenchmarkResultStorage

__all__ = [
    "BenchmarkMetadata",
    "BenchmarkResult",
    "BenchmarkResultStorage",
    "BenchmarkRunner",
    "BenchmarkStatus",
    "BenchmarkSuite",
]

__version__ = "1.0.0"
