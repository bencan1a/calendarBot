"""Data models for the CalendarBot benchmarking system."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class BenchmarkStatus(Enum):
    """Status of a benchmark execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BenchmarkMetadata:
    """Metadata for a benchmark definition."""

    benchmark_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: str = ""
    expected_duration_seconds: Optional[float] = None
    min_iterations: int = 1
    max_iterations: int = 10
    warmup_iterations: int = 1
    timeout_seconds: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for storage."""
        return {
            "benchmark_id": self.benchmark_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "expected_duration_seconds": self.expected_duration_seconds,
            "min_iterations": self.min_iterations,
            "max_iterations": self.max_iterations,
            "warmup_iterations": self.warmup_iterations,
            "timeout_seconds": self.timeout_seconds,
            "tags": self.tags,
            "prerequisites": self.prerequisites,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class BenchmarkResult:
    """Results from executing a single benchmark."""

    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str = ""
    benchmark_id: str = ""
    benchmark_name: str = ""
    category: str = ""
    status: BenchmarkStatus = BenchmarkStatus.PENDING

    # Timing results
    execution_time: float = 0.0
    iterations: int = 0
    min_value: float = 0.0
    max_value: float = 0.0
    mean_value: float = 0.0
    median_value: float = 0.0
    std_deviation: float = 0.0

    # Execution context
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    app_version: str = ""
    environment: str = ""
    correlation_id: Optional[str] = None

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    # Performance overhead tracking
    overhead_percentage: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for storage."""
        return {
            "result_id": self.result_id,
            "run_id": self.run_id,
            "benchmark_id": self.benchmark_id,
            "benchmark_name": self.benchmark_name,
            "category": self.category,
            "status": self.status.value,
            "execution_time": self.execution_time,
            "iterations": self.iterations,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "mean_value": self.mean_value,
            "median_value": self.median_value,
            "std_deviation": self.std_deviation,
            "timestamp": self.timestamp.isoformat(),
            "app_version": self.app_version,
            "environment": self.environment,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
            "error_message": self.error_message,
            "overhead_percentage": self.overhead_percentage,
        }

    @property
    def success(self) -> bool:
        """Whether the benchmark completed successfully."""
        return self.status == BenchmarkStatus.COMPLETED

    @property
    def duration_ms(self) -> float:
        """Execution time in milliseconds."""
        return self.execution_time * 1000

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the result."""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value with optional default."""
        return self.metadata.get(key, default)


@dataclass
class BenchmarkSuite:
    """Collection of related benchmarks."""

    suite_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0.0"

    # Suite configuration
    benchmark_ids: List[str] = field(default_factory=list)
    parallel_execution: bool = False
    stop_on_failure: bool = False
    max_execution_time_seconds: Optional[float] = None

    # Suite metadata
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""

    # Execution tracking
    last_run_id: Optional[str] = None
    last_run_timestamp: Optional[datetime] = None
    last_run_status: BenchmarkStatus = BenchmarkStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        """Convert suite to dictionary for storage."""
        return {
            "suite_id": self.suite_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "benchmark_ids": self.benchmark_ids,
            "parallel_execution": self.parallel_execution,
            "stop_on_failure": self.stop_on_failure,
            "max_execution_time_seconds": self.max_execution_time_seconds,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "last_run_id": self.last_run_id,
            "last_run_timestamp": self.last_run_timestamp.isoformat()
            if self.last_run_timestamp
            else None,
            "last_run_status": self.last_run_status.value,
        }

    def add_benchmark(self, benchmark_id: str) -> None:
        """Add a benchmark to this suite."""
        if benchmark_id not in self.benchmark_ids:
            self.benchmark_ids.append(benchmark_id)

    def remove_benchmark(self, benchmark_id: str) -> None:
        """Remove a benchmark from this suite."""
        if benchmark_id in self.benchmark_ids:
            self.benchmark_ids.remove(benchmark_id)

    @property
    def benchmark_count(self) -> int:
        """Number of benchmarks in this suite."""
        return len(self.benchmark_ids)


@dataclass
class BenchmarkRun:
    """Represents a complete benchmark execution session."""

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

    # Run configuration
    suite_id: Optional[str] = None
    benchmark_ids: List[str] = field(default_factory=list)
    environment: str = "development"
    app_version: str = ""

    # Execution tracking
    status: BenchmarkStatus = BenchmarkStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results aggregation
    total_benchmarks: int = 0
    completed_benchmarks: int = 0
    failed_benchmarks: int = 0
    skipped_benchmarks: int = 0

    # Performance summary
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    total_overhead_percentage: Optional[float] = None

    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert run to dictionary for storage."""
        return {
            "run_id": self.run_id,
            "name": self.name,
            "description": self.description,
            "suite_id": self.suite_id,
            "benchmark_ids": self.benchmark_ids,
            "environment": self.environment,
            "app_version": self.app_version,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_benchmarks": self.total_benchmarks,
            "completed_benchmarks": self.completed_benchmarks,
            "failed_benchmarks": self.failed_benchmarks,
            "skipped_benchmarks": self.skipped_benchmarks,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": self.average_execution_time,
            "total_overhead_percentage": self.total_overhead_percentage,
            "metadata": self.metadata,
            "error_message": self.error_message,
        }

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_benchmarks == 0:
            return 0.0
        return (self.completed_benchmarks / self.total_benchmarks) * 100

    @property
    def duration_seconds(self) -> float:
        """Total duration of the run in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    @property
    def is_complete(self) -> bool:
        """Whether the run has completed (successfully or with failures)."""
        return self.status in [BenchmarkStatus.COMPLETED, BenchmarkStatus.FAILED]

    def start(self) -> None:
        """Mark the run as started."""
        self.status = BenchmarkStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def complete(self, success: bool = True) -> None:
        """Mark the run as completed."""
        self.status = BenchmarkStatus.COMPLETED if success else BenchmarkStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)

    def update_statistics(self, results: List[BenchmarkResult]) -> None:
        """Update run statistics based on benchmark results."""
        self.total_benchmarks = len(results)
        self.completed_benchmarks = sum(1 for r in results if r.status == BenchmarkStatus.COMPLETED)
        self.failed_benchmarks = sum(1 for r in results if r.status == BenchmarkStatus.FAILED)
        self.skipped_benchmarks = sum(1 for r in results if r.status == BenchmarkStatus.SKIPPED)

        completed_results = [r for r in results if r.status == BenchmarkStatus.COMPLETED]
        if completed_results:
            self.total_execution_time = sum(r.execution_time for r in completed_results)
            self.average_execution_time = self.total_execution_time / len(completed_results)

            # Calculate average overhead
            overhead_values = [
                r.overhead_percentage
                for r in completed_results
                if r.overhead_percentage is not None
            ]
            if overhead_values:
                self.total_overhead_percentage = sum(overhead_values) / len(overhead_values)
