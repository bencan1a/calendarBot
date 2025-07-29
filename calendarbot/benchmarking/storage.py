"""Storage layer for benchmark results using SQLite database."""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..utils.logging import get_logger
from .models import (
    BenchmarkMetadata,
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkStatus,
    BenchmarkSuite,
)


class BenchmarkResultStorage:
    """Handles persistence of benchmark results and metadata to SQLite database."""

    def __init__(
        self, database_path: Optional[Union[str, Path]] = None, settings: Optional[Any] = None
    ) -> None:
        """
        Initialize the benchmark result storage.

        Args:
            database_path: Path to SQLite database file. If None, uses default location.
            settings: Application settings object for configuration.
        """
        self.settings = settings
        self.logger = get_logger("benchmarking.storage")

        # Set up database path
        if database_path:
            self.database_path = Path(database_path)
        else:
            if self.settings and hasattr(self.settings, "data_dir"):
                data_dir = Path(self.settings.data_dir) / "benchmarking"
            else:
                data_dir = Path.home() / ".local" / "share" / "calendarbot" / "benchmarking"

            data_dir.mkdir(parents=True, exist_ok=True)
            self.database_path = data_dir / "benchmark_results.db"

        self._lock = threading.Lock()
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize the database schema."""
        try:
            with self._get_connection() as conn:
                self._create_tables(conn)
                self._create_indexes(conn)
                self.logger.info(f"Initialized benchmark database at {self.database_path}")
        except Exception as e:
            self.logger.error(f"Failed to initialize benchmark database: {e}")
            raise

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper configuration."""
        conn = sqlite3.connect(self.database_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create all required database tables."""
        # Benchmark runs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_runs (
                run_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                suite_id TEXT,
                environment TEXT NOT NULL,
                app_version TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                total_benchmarks INTEGER DEFAULT 0,
                completed_benchmarks INTEGER DEFAULT 0,
                failed_benchmarks INTEGER DEFAULT 0,
                skipped_benchmarks INTEGER DEFAULT 0,
                total_execution_time REAL DEFAULT 0.0,
                average_execution_time REAL DEFAULT 0.0,
                total_overhead_percentage REAL,
                metadata TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Benchmark metadata table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_metadata (
                benchmark_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                expected_duration_seconds REAL,
                min_iterations INTEGER DEFAULT 1,
                max_iterations INTEGER DEFAULT 10,
                warmup_iterations INTEGER DEFAULT 1,
                timeout_seconds REAL,
                tags TEXT,
                prerequisites TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Benchmark results table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_results (
                result_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                benchmark_id TEXT NOT NULL,
                benchmark_name TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT NOT NULL,
                execution_time REAL NOT NULL,
                iterations INTEGER NOT NULL,
                min_value REAL NOT NULL,
                max_value REAL NOT NULL,
                mean_value REAL NOT NULL,
                median_value REAL NOT NULL,
                std_deviation REAL NOT NULL,
                timestamp TEXT NOT NULL,
                app_version TEXT NOT NULL,
                environment TEXT NOT NULL,
                correlation_id TEXT,
                metadata TEXT,
                error_message TEXT,
                overhead_percentage REAL,
                FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id) ON DELETE CASCADE
            )
        """)

        # Benchmark suites table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_suites (
                suite_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                version TEXT NOT NULL DEFAULT '1.0.0',
                benchmark_ids TEXT,
                parallel_execution INTEGER DEFAULT 0,
                stop_on_failure INTEGER DEFAULT 0,
                max_execution_time_seconds REAL,
                tags TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                last_run_id TEXT,
                last_run_timestamp TEXT,
                last_run_status TEXT DEFAULT 'pending'
            )
        """)

        # Benchmark baselines table (for regression detection)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_baselines (
                baseline_id TEXT PRIMARY KEY,
                benchmark_id TEXT NOT NULL,
                benchmark_name TEXT NOT NULL,
                category TEXT NOT NULL,
                baseline_value REAL NOT NULL,
                tolerance_percent REAL NOT NULL DEFAULT 10.0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                FOREIGN KEY (benchmark_id) REFERENCES benchmark_metadata(benchmark_id) ON DELETE CASCADE
            )
        """)

    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """Create database indexes for performance optimization."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_benchmark_results_run_id ON benchmark_results(run_id)",
            "CREATE INDEX IF NOT EXISTS idx_benchmark_results_benchmark_id ON benchmark_results(benchmark_id)",
            "CREATE INDEX IF NOT EXISTS idx_benchmark_results_category ON benchmark_results(category)",
            "CREATE INDEX IF NOT EXISTS idx_benchmark_results_status ON benchmark_results(status)",
            "CREATE INDEX IF NOT EXISTS idx_benchmark_results_timestamp ON benchmark_results(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_benchmark_runs_status ON benchmark_runs(status)",
            "CREATE INDEX IF NOT EXISTS idx_benchmark_runs_environment ON benchmark_runs(environment)",
            "CREATE INDEX IF NOT EXISTS idx_benchmark_baselines_benchmark_id ON benchmark_baselines(benchmark_id)",
            "CREATE INDEX IF NOT EXISTS idx_benchmark_metadata_category ON benchmark_metadata(category)",
        ]

        for index_sql in indexes:
            conn.execute(index_sql)

    def store_benchmark_run(self, run: BenchmarkRun) -> bool:
        """
        Store a benchmark run record.

        Args:
            run: BenchmarkRun object to store.

        Returns:
            True if successful, False otherwise.
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO benchmark_runs (
                            run_id, name, description, suite_id, environment, app_version,
                            status, started_at, completed_at, total_benchmarks,
                            completed_benchmarks, failed_benchmarks, skipped_benchmarks,
                            total_execution_time, average_execution_time, total_overhead_percentage,
                            metadata, error_message
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            run.run_id,
                            run.name,
                            run.description,
                            run.suite_id,
                            run.environment,
                            run.app_version,
                            run.status.value,
                            run.started_at.isoformat() if run.started_at else None,
                            run.completed_at.isoformat() if run.completed_at else None,
                            run.total_benchmarks,
                            run.completed_benchmarks,
                            run.failed_benchmarks,
                            run.skipped_benchmarks,
                            run.total_execution_time,
                            run.average_execution_time,
                            run.total_overhead_percentage,
                            json.dumps(run.metadata),
                            run.error_message,
                        ),
                    )
                    conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to store benchmark run {run.run_id}: {e}")
            return False

    def store_benchmark_result(self, result: BenchmarkResult) -> bool:
        """
        Store a benchmark result.

        Args:
            result: BenchmarkResult object to store.

        Returns:
            True if successful, False otherwise.
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO benchmark_results (
                            result_id, run_id, benchmark_id, benchmark_name, category, status,
                            execution_time, iterations, min_value, max_value, mean_value,
                            median_value, std_deviation, timestamp, app_version, environment,
                            correlation_id, metadata, error_message, overhead_percentage
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            result.result_id,
                            result.run_id,
                            result.benchmark_id,
                            result.benchmark_name,
                            result.category,
                            result.status.value,
                            result.execution_time,
                            result.iterations,
                            result.min_value,
                            result.max_value,
                            result.mean_value,
                            result.median_value,
                            result.std_deviation,
                            result.timestamp.isoformat(),
                            result.app_version,
                            result.environment,
                            result.correlation_id,
                            json.dumps(result.metadata),
                            result.error_message,
                            result.overhead_percentage,
                        ),
                    )
                    conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to store benchmark result {result.result_id}: {e}")
            return False

    def store_benchmark_metadata(self, metadata: BenchmarkMetadata) -> bool:
        """
        Store benchmark metadata.

        Args:
            metadata: BenchmarkMetadata object to store.

        Returns:
            True if successful, False otherwise.
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO benchmark_metadata (
                            benchmark_id, name, description, category, expected_duration_seconds,
                            min_iterations, max_iterations, warmup_iterations, timeout_seconds,
                            tags, prerequisites, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            metadata.benchmark_id,
                            metadata.name,
                            metadata.description,
                            metadata.category,
                            metadata.expected_duration_seconds,
                            metadata.min_iterations,
                            metadata.max_iterations,
                            metadata.warmup_iterations,
                            metadata.timeout_seconds,
                            json.dumps(metadata.tags),
                            json.dumps(metadata.prerequisites),
                            metadata.created_at.isoformat(),
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to store benchmark metadata {metadata.benchmark_id}: {e}")
            return False

    def store_benchmark_suite(self, suite: BenchmarkSuite) -> bool:
        """
        Store a benchmark suite.

        Args:
            suite: BenchmarkSuite object to store.

        Returns:
            True if successful, False otherwise.
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO benchmark_suites (
                            suite_id, name, description, version, benchmark_ids,
                            parallel_execution, stop_on_failure, max_execution_time_seconds,
                            tags, created_at, created_by, last_run_id, last_run_timestamp, last_run_status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            suite.suite_id,
                            suite.name,
                            suite.description,
                            suite.version,
                            json.dumps(suite.benchmark_ids),
                            int(suite.parallel_execution),
                            int(suite.stop_on_failure),
                            suite.max_execution_time_seconds,
                            json.dumps(suite.tags),
                            suite.created_at.isoformat(),
                            suite.created_by,
                            suite.last_run_id,
                            suite.last_run_timestamp.isoformat()
                            if suite.last_run_timestamp
                            else None,
                            suite.last_run_status.value,
                        ),
                    )
                    conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to store benchmark suite {suite.suite_id}: {e}")
            return False

    def get_benchmark_results(
        self,
        run_id: Optional[str] = None,
        benchmark_id: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[BenchmarkStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[BenchmarkResult]:
        """
        Retrieve benchmark results with optional filtering.

        Args:
            run_id: Filter by run ID.
            benchmark_id: Filter by benchmark ID.
            category: Filter by category.
            status: Filter by status.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of BenchmarkResult objects.
        """
        try:
            conditions = []
            params = []

            if run_id:
                conditions.append("run_id = ?")
                params.append(run_id)
            if benchmark_id:
                conditions.append("benchmark_id = ?")
                params.append(benchmark_id)
            if category:
                conditions.append("category = ?")
                params.append(category)
            if status:
                conditions.append("status = ?")
                params.append(status.value)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            query = f"""
                SELECT * FROM benchmark_results
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

            results = []
            for row in rows:
                result = BenchmarkResult(
                    result_id=row["result_id"],
                    run_id=row["run_id"],
                    benchmark_id=row["benchmark_id"],
                    benchmark_name=row["benchmark_name"],
                    category=row["category"],
                    status=BenchmarkStatus(row["status"]),
                    execution_time=row["execution_time"],
                    iterations=row["iterations"],
                    min_value=row["min_value"],
                    max_value=row["max_value"],
                    mean_value=row["mean_value"],
                    median_value=row["median_value"],
                    std_deviation=row["std_deviation"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    app_version=row["app_version"],
                    environment=row["environment"],
                    correlation_id=row["correlation_id"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    error_message=row["error_message"],
                    overhead_percentage=row["overhead_percentage"],
                )
                results.append(result)

            return results

        except Exception as e:
            self.logger.error(f"Failed to retrieve benchmark results: {e}")
            return []

    def get_benchmark_runs(
        self,
        status: Optional[BenchmarkStatus] = None,
        environment: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BenchmarkRun]:
        """
        Retrieve benchmark runs with optional filtering.

        Args:
            status: Filter by status.
            environment: Filter by environment.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of BenchmarkRun objects.
        """
        try:
            conditions = []
            params = []

            if status:
                conditions.append("status = ?")
                params.append(status.value)
            if environment:
                conditions.append("environment = ?")
                params.append(environment)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            query = f"""
                SELECT * FROM benchmark_runs
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

            runs = []
            for row in rows:
                run = BenchmarkRun(
                    run_id=row["run_id"],
                    name=row["name"],
                    description=row["description"],
                    suite_id=row["suite_id"],
                    environment=row["environment"],
                    app_version=row["app_version"],
                    status=BenchmarkStatus(row["status"]),
                    started_at=datetime.fromisoformat(row["started_at"])
                    if row["started_at"]
                    else None,
                    completed_at=datetime.fromisoformat(row["completed_at"])
                    if row["completed_at"]
                    else None,
                    total_benchmarks=row["total_benchmarks"],
                    completed_benchmarks=row["completed_benchmarks"],
                    failed_benchmarks=row["failed_benchmarks"],
                    skipped_benchmarks=row["skipped_benchmarks"],
                    total_execution_time=row["total_execution_time"],
                    average_execution_time=row["average_execution_time"],
                    total_overhead_percentage=row["total_overhead_percentage"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    error_message=row["error_message"],
                )
                runs.append(run)

            return runs

        except Exception as e:
            self.logger.error(f"Failed to retrieve benchmark runs: {e}")
            return []

    def get_performance_trends(self, benchmark_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get performance trends for a benchmark over time.

        Args:
            benchmark_id: The benchmark to analyze.
            days: Number of days to look back.

        Returns:
            List of trend data points.
        """
        try:
            cutoff_date = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)

            query = """
                SELECT 
                    DATE(timestamp) as date,
                    AVG(mean_value) as avg_performance,
                    MIN(min_value) as min_performance,
                    MAX(max_value) as max_performance,
                    COUNT(*) as run_count
                FROM benchmark_results
                WHERE benchmark_id = ? 
                AND status = 'completed'
                AND timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date
            """

            with self._get_connection() as conn:
                cursor = conn.execute(query, [benchmark_id, cutoff_date.isoformat()])
                rows = cursor.fetchall()

            trends = []
            for row in rows:
                trends.append(
                    {
                        "date": row["date"],
                        "avg_performance": row["avg_performance"],
                        "min_performance": row["min_performance"],
                        "max_performance": row["max_performance"],
                        "run_count": row["run_count"],
                    }
                )

            return trends

        except Exception as e:
            self.logger.error(f"Failed to get performance trends for {benchmark_id}: {e}")
            return []

    def cleanup_old_results(self, days_to_keep: int = 90) -> int:
        """
        Clean up old benchmark results.

        Args:
            days_to_keep: Number of days of results to keep.

        Returns:
            Number of records deleted.
        """
        try:
            cutoff_date = datetime.now(timezone.utc)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_to_keep)

            with self._lock:
                with self._get_connection() as conn:
                    # Delete old results
                    cursor = conn.execute(
                        "DELETE FROM benchmark_results WHERE timestamp < ?",
                        [cutoff_date.isoformat()],
                    )
                    deleted_results = cursor.rowcount

                    # Delete old runs that have no results
                    cursor = conn.execute(
                        """
                        DELETE FROM benchmark_runs 
                        WHERE run_id NOT IN (SELECT DISTINCT run_id FROM benchmark_results)
                        AND created_at < ?
                    """,
                        [cutoff_date.isoformat()],
                    )
                    deleted_runs = cursor.rowcount

                    conn.commit()

            total_deleted = deleted_results + deleted_runs
            self.logger.info(f"Cleaned up {total_deleted} old benchmark records")
            return total_deleted

        except Exception as e:
            self.logger.error(f"Failed to cleanup old results: {e}")
            return 0

    def close(self) -> None:
        """Close the storage connection."""
        # SQLite connections are automatically closed when connection objects are garbage collected
        # This method is provided for interface consistency
        pass
