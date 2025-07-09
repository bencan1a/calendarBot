#!/usr/bin/env python3
"""
Test Suite Management and Execution Coordinator for CalendarBot.

This module provides centralized management of test suite execution,
including dynamic test selection, timing analysis, optimization recommendations,
and execution reporting.
"""

import asyncio
import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.suites.critical_path import CriticalPathSuite
from tests.suites.full_regression import FullRegressionSuite


@dataclass
class TestExecution:
    """Record of a test suite execution."""

    suite_name: str
    start_time: datetime
    end_time: datetime
    duration: float
    status: str
    test_count: int
    passed: int
    failed: int
    skipped: int
    coverage_line: float
    coverage_branch: float
    git_commit: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class TestFile:
    """Information about a test file."""

    path: str
    size: int
    modified: datetime
    hash: str
    test_count: int


class TestSuiteManager:
    """
    Central manager for test suite execution and coordination.

    Provides dynamic test selection, execution timing, optimization analysis,
    and comprehensive reporting capabilities.
    """

    def __init__(self, workspace_dir: Optional[Path] = None):
        """
        Initialize the test suite manager.

        Args:
            workspace_dir: Root directory of the project workspace
        """
        self.workspace_dir = workspace_dir or project_root
        self.test_dir = self.workspace_dir / "tests"
        self.data_dir = self.test_dir / "suite_data"
        self.data_dir.mkdir(exist_ok=True)

        self.db_path = self.data_dir / "test_executions.db"
        self._init_database()

    def _init_database(self):
        """Initialize the execution tracking database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    suite_name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    duration REAL NOT NULL,
                    status TEXT NOT NULL,
                    test_count INTEGER NOT NULL,
                    passed INTEGER NOT NULL,
                    failed INTEGER NOT NULL,
                    skipped INTEGER NOT NULL,
                    coverage_line REAL,
                    coverage_branch REAL,
                    git_commit TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    modified TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    test_count INTEGER NOT NULL,
                    last_checked TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(path, hash)
                )
            """
            )

    def get_changed_files(self, since: Optional[datetime] = None) -> List[str]:
        """
        Get list of files changed since a specific time or last test run.

        Args:
            since: Check for changes since this time (default: last test execution)

        Returns:
            List of changed file paths
        """
        if since is None:
            # Get last execution time
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT MAX(end_time) FROM test_executions")
                result = cursor.fetchone()
                if result and result[0]:
                    since = datetime.fromisoformat(result[0])
                else:
                    since = datetime.now() - timedelta(days=1)

        changed_files = []

        # Check all Python files in the project
        for py_file in self.workspace_dir.rglob("*.py"):
            if ".git" in str(py_file) or "__pycache__" in str(py_file):
                continue

            try:
                stat = py_file.stat()
                modified = datetime.fromtimestamp(stat.st_mtime)

                if modified > since:
                    changed_files.append(str(py_file.relative_to(self.workspace_dir)))
            except OSError:
                continue

        return changed_files

    def get_related_tests(self, changed_files: List[str]) -> Set[str]:
        """
        Determine which tests should run based on changed files.

        Args:
            changed_files: List of changed file paths

        Returns:
            Set of test file paths to execute
        """
        related_tests = set()

        for file_path in changed_files:
            path_obj = Path(file_path)

            # Direct test file changes
            if path_obj.parts[0] == "tests" and path_obj.name.startswith("test_"):
                related_tests.add(file_path)
                continue

            # Map source files to test files
            if path_obj.parts[0] == "calendarbot":
                # Map calendarbot/module/file.py to tests/unit/test_file.py
                module_name = path_obj.stem
                potential_tests = [
                    f"tests/unit/test_{module_name}.py",
                    f"tests/integration/test_{module_name}_integration.py",
                    f"tests/e2e/test_{module_name}_workflows.py",
                ]

                for test_path in potential_tests:
                    if (self.workspace_dir / test_path).exists():
                        related_tests.add(test_path)

                # Also include integration tests for core modules
                if any(core in file_path for core in ["cache", "source", "web", "main"]):
                    related_tests.update(
                        [
                            "tests/integration/test_web_api_integration.py",
                            "tests/e2e/test_application_workflows.py",
                        ]
                    )

            # Configuration changes affect many tests
            elif any(config in file_path for config in ["config", "settings", "pyproject.toml"]):
                related_tests.update(
                    [
                        "tests/unit/test_calendar_bot.py",
                        "tests/integration/test_web_api_integration.py",
                    ]
                )

        # Filter to existing files
        existing_tests = set()
        for test_path in related_tests:
            if (self.workspace_dir / test_path).exists():
                existing_tests.add(test_path)

        return existing_tests

    def analyze_test_performance(self, days: int = 7) -> Dict[str, Any]:
        """
        Analyze test performance over time.

        Args:
            days: Number of days to analyze

        Returns:
            Performance analysis results
        """
        since = datetime.now() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT suite_name, duration, status, test_count,
                       coverage_line, coverage_branch, start_time
                FROM test_executions
                WHERE start_time >= ?
                ORDER BY start_time DESC
            """,
                (since.isoformat(),),
            )

            executions = cursor.fetchall()

        if not executions:
            return {"message": "No test executions found in the specified period"}

        # Group by suite
        suites: Dict[str, List[Dict[str, Any]]] = {}
        for exec_data in executions:
            suite_name = exec_data[0]
            if suite_name not in suites:
                suites[suite_name] = []
            suites[suite_name].append(
                {
                    "duration": exec_data[1],
                    "status": exec_data[2],
                    "test_count": exec_data[3],
                    "coverage_line": exec_data[4],
                    "coverage_branch": exec_data[5],
                    "timestamp": exec_data[6],
                }
            )

        analysis = {}
        for suite_name, suite_executions in suites.items():
            durations = [e["duration"] for e in suite_executions if e["status"] == "PASS"]

            if durations:
                analysis[suite_name] = {
                    "execution_count": len(suite_executions),
                    "success_rate": len([e for e in suite_executions if e["status"] == "PASS"])
                    / len(suite_executions)
                    * 100,
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "latest_coverage": {
                        "line": suite_executions[0]["coverage_line"],
                        "branch": suite_executions[0]["coverage_branch"],
                    },
                    "trend": self._calculate_trend(durations),
                }

        return {
            "analysis_period": f"{days} days",
            "total_executions": len(executions),
            "suites": analysis,
            "recommendations": self._generate_performance_recommendations(analysis),
        }

    def _calculate_trend(self, durations: List[float]) -> str:
        """Calculate performance trend from duration data."""
        if len(durations) < 2:
            return "insufficient_data"

        # Simple trend calculation: compare first half to second half
        mid = len(durations) // 2
        first_half_avg = sum(durations[:mid]) / mid
        second_half_avg = sum(durations[mid:]) / (len(durations) - mid)

        if second_half_avg < first_half_avg * 0.95:
            return "improving"
        elif second_half_avg > first_half_avg * 1.05:
            return "degrading"
        else:
            return "stable"

    def _generate_performance_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []

        for suite_name, metrics in analysis.items():
            if metrics["success_rate"] < 90:
                recommendations.append(
                    f"{suite_name}: Low success rate ({metrics['success_rate']:.1f}%) - investigate flaky tests"
                )

            if metrics["trend"] == "degrading":
                recommendations.append(
                    f"{suite_name}: Performance degrading - review recent changes and optimize slow tests"
                )

            if suite_name == "critical_path" and metrics["avg_duration"] > 300:
                recommendations.append(
                    f"{suite_name}: Exceeding 5-minute target ({metrics['avg_duration']:.1f}s) - remove slow tests"
                )

            if metrics.get("latest_coverage", {}).get("line", 0) < 80:
                recommendations.append(
                    f"{suite_name}: Coverage below target - add tests for uncovered code"
                )

        if not recommendations:
            recommendations.append("All suites performing within acceptable parameters")

        return recommendations

    def execute_suite(self, suite_name: str, **kwargs) -> TestExecution:
        """
        Execute a specific test suite with tracking.

        Args:
            suite_name: Name of the suite to execute ('critical_path' or 'full_regression')
            **kwargs: Additional arguments for suite execution

        Returns:
            TestExecution record
        """
        start_time = datetime.now()

        try:
            if suite_name == "critical_path":
                args = CriticalPathSuite.get_pytest_args(**kwargs)
            elif suite_name == "full_regression":
                args = FullRegressionSuite.get_pytest_args(**kwargs)
            else:
                raise ValueError(f"Unknown suite: {suite_name}")

            # Execute the test suite
            result = subprocess.run(args, cwd=self.workspace_dir, capture_output=True, text=True)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Parse results
            test_count, passed, failed, skipped = self._parse_pytest_output(result.stdout)
            coverage_line, coverage_branch = self._parse_coverage_output(result.stdout)
            coverage_failure = self._parse_coverage_failure(result.stdout)

            status = "PASS" if result.returncode == 0 else "FAIL"

            # Build detailed error notes for failures
            notes = None
            if result.returncode != 0:
                if coverage_failure:
                    notes = (
                        f"Coverage threshold failure: Required {coverage_failure['required']}%, "
                        f"actual {coverage_failure['actual']}%. Tests passed but coverage insufficient."
                    )
                elif failed > 0:
                    notes = f"Test failures: {failed} test(s) failed"
                else:
                    notes = "Unknown failure - check test output"

            # Get git commit if available
            git_commit = self._get_git_commit()

            execution = TestExecution(
                suite_name=suite_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                status=status,
                test_count=test_count,
                passed=passed,
                failed=failed,
                skipped=skipped,
                coverage_line=coverage_line,
                coverage_branch=coverage_branch,
                git_commit=git_commit,
                notes=notes,
            )

            # Store execution record
            self._store_execution(execution)

            return execution

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            execution = TestExecution(
                suite_name=suite_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                status="ERROR",
                test_count=0,
                passed=0,
                failed=0,
                skipped=0,
                coverage_line=0.0,
                coverage_branch=0.0,
                notes=str(e),
            )

            self._store_execution(execution)
            return execution

    def _parse_pytest_output(self, output: str) -> Tuple[int, int, int, int]:
        """Parse pytest output for test counts and detect coverage failures."""
        import re

        # Look for patterns like "5 passed, 2 failed, 1 skipped"
        pattern = r"(\d+) passed(?:, (\d+) failed)?(?:, (\d+) skipped)?"
        match = re.search(pattern, output)

        if match:
            passed = int(match.group(1) or 0)
            failed = int(match.group(2) or 0)
            skipped = int(match.group(3) or 0)
            total = passed + failed + skipped
            return total, passed, failed, skipped

        # Check for coverage failure when no test results are found
        coverage_fail_pattern = r"FAIL Required test coverage of (\d+(?:\.\d+)?)% not reached\. Total coverage: (\d+(?:\.\d+)?)%"
        coverage_match = re.search(coverage_fail_pattern, output)

        if coverage_match:
            # Coverage failure detected - this means tests passed but coverage failed
            # Look for any test counts that might still be in output
            test_pattern = r"(\d+) passed"
            test_match = re.search(test_pattern, output)
            if test_match:
                passed = int(test_match.group(1))
                return (
                    passed,
                    passed,
                    0,
                    0,
                )  # Return with 0 failed tests since coverage is the issue

        return 0, 0, 0, 0

    def _parse_coverage_output(self, output: str) -> Tuple[float, float]:
        """Parse coverage information from output."""
        import re

        # Look for coverage percentages
        line_pattern = r"TOTAL.*?(\d+)%"
        branch_pattern = r"TOTAL.*?\d+%.*?(\d+)%"

        line_match = re.search(line_pattern, output)
        line_coverage = float(line_match.group(1)) if line_match else 0.0

        branch_match = re.search(branch_pattern, output)
        branch_coverage = float(branch_match.group(1)) if branch_match else 0.0

        return line_coverage, branch_coverage

    def _parse_coverage_failure(self, output: str) -> Optional[Dict[str, float]]:
        """Parse coverage failure details from pytest output."""
        import re

        coverage_fail_pattern = r"FAIL Required test coverage of (\d+(?:\.\d+)?)% not reached\. Total coverage: (\d+(?:\.\d+)?)%"
        match = re.search(coverage_fail_pattern, output)

        if match:
            return {"required": float(match.group(1)), "actual": float(match.group(2))}

        return None

    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=self.workspace_dir, capture_output=True, text=True
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except:
            return None

    def _store_execution(self, execution: TestExecution):
        """Store execution record in database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO test_executions
                (suite_name, start_time, end_time, duration, status, test_count,
                 passed, failed, skipped, coverage_line, coverage_branch, git_commit, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    execution.suite_name,
                    execution.start_time.isoformat(),
                    execution.end_time.isoformat(),
                    execution.duration,
                    execution.status,
                    execution.test_count,
                    execution.passed,
                    execution.failed,
                    execution.skipped,
                    execution.coverage_line,
                    execution.coverage_branch,
                    execution.git_commit,
                    execution.notes,
                ),
            )

    def smart_test_selection(self, target_duration: Optional[float] = None) -> Dict[str, Any]:
        """
        Intelligently select tests based on recent changes and performance data.

        Args:
            target_duration: Target execution duration in seconds

        Returns:
            Test selection recommendation
        """
        changed_files = self.get_changed_files()
        related_tests = self.get_related_tests(changed_files)

        if not changed_files:
            recommendation: Dict[str, Any] = {
                "strategy": "critical_path",
                "reason": "No recent changes detected",
                "tests": None,
                "estimated_duration": 300,
            }
        elif len(related_tests) <= 5:
            recommendation = {
                "strategy": "targeted",
                "reason": f"Few changes detected ({len(changed_files)} files)",
                "tests": list(related_tests),
                "estimated_duration": len(related_tests) * 30,
            }
        elif any("calendarbot/main.py" in f or "setup.py" in f for f in changed_files):
            recommendation = {
                "strategy": "full_regression",
                "reason": "Core application files changed",
                "tests": None,
                "estimated_duration": 1800,
            }
        else:
            recommendation = {
                "strategy": "critical_path",
                "reason": f"Multiple changes detected ({len(changed_files)} files), using critical path",
                "tests": None,
                "estimated_duration": 300,
            }

        recommendation["changed_files"] = changed_files
        recommendation["related_tests"] = list(related_tests)

        return recommendation

    def generate_execution_report(self, execution: TestExecution) -> Dict[str, Any]:
        """
        Generate a comprehensive execution report.

        Args:
            execution: TestExecution record

        Returns:
            Detailed execution report
        """
        # Validate against suite targets
        if execution.suite_name == "critical_path":
            validation = CriticalPathSuite.validate_execution_time(execution.duration)
        elif execution.suite_name == "full_regression":
            validation = FullRegressionSuite.validate_execution_time(execution.duration)
        else:
            validation = {"status": "UNKNOWN", "recommendation": "Unknown suite type"}

        # Get historical context
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT AVG(duration), AVG(coverage_line), AVG(coverage_branch)
                FROM test_executions
                WHERE suite_name = ? AND status = 'PASS'
                AND start_time >= date('now', '-30 days')
            """,
                (execution.suite_name,),
            )

            historical = cursor.fetchone()

        historical_avg_duration = (
            historical[0] if historical and historical[0] else execution.duration
        )
        historical_avg_line = (
            historical[1] if historical and historical[1] else execution.coverage_line
        )
        historical_avg_branch = (
            historical[2] if historical and historical[2] else execution.coverage_branch
        )

        return {
            "execution": asdict(execution),
            "validation": validation,
            "performance_comparison": {
                "duration_vs_historical": {
                    "current": execution.duration,
                    "historical_avg": historical_avg_duration,
                    "improvement": (
                        (
                            (historical_avg_duration - execution.duration)
                            / historical_avg_duration
                            * 100
                        )
                        if historical_avg_duration > 0
                        else 0
                    ),
                },
                "coverage_vs_historical": {
                    "line": {
                        "current": execution.coverage_line,
                        "historical_avg": historical_avg_line,
                        "improvement": execution.coverage_line - historical_avg_line,
                    },
                    "branch": {
                        "current": execution.coverage_branch,
                        "historical_avg": historical_avg_branch,
                        "improvement": execution.coverage_branch - historical_avg_branch,
                    },
                },
            },
            "recommendations": self._generate_execution_recommendations(execution, validation),
        }

    def _generate_execution_recommendations(
        self, execution: TestExecution, validation: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on execution results."""
        recommendations = []

        if execution.status == "FAIL":
            # Check if this is a coverage failure vs test failure
            if execution.notes and "Coverage threshold failure" in execution.notes:
                recommendations.append(
                    "Coverage threshold not met - add tests to increase coverage"
                )
                recommendations.append(execution.notes)  # Include specific coverage details
            elif execution.failed > 0:
                recommendations.append("Address test failures before proceeding with deployment")
                recommendations.append(f"Investigate {execution.failed} failed test(s)")
            else:
                recommendations.append("Address test failures before proceeding with deployment")

        if execution.failed > 0:
            recommendations.append(f"Investigate {execution.failed} failed test(s)")

        if execution.coverage_line < 80:
            recommendations.append("Increase test coverage - below 80% target")

        if validation.get("status") == "FAIL":
            recommendations.append(validation.get("recommendation", "Optimize execution time"))

        if execution.skipped > execution.test_count * 0.1:  # More than 10% skipped
            recommendations.append("High number of skipped tests - verify test environment")

        if not recommendations:
            recommendations.append("Execution completed successfully within targets")

        return recommendations

    def execute_smart_strategy(self, verbose: bool = True) -> int:
        """
        Execute smart test selection strategy for pre-commit integration.

        Args:
            verbose: Enable verbose output

        Returns:
            Exit code (0 = success, 1 = failure)
        """
        try:
            # Get smart test selection recommendation
            recommendation = self.smart_test_selection()

            if verbose:
                print(f"🔍 Smart Test Selection Analysis:")
                print(f"   Strategy: {recommendation['strategy']}")
                print(f"   Reason: {recommendation['reason']}")
                print(f"   Estimated Duration: {recommendation['estimated_duration']}s")
                print(f"   Changed Files: {len(recommendation['changed_files'])}")
                print(f"   Related Tests: {len(recommendation['related_tests'])}")
                print()

            strategy = recommendation["strategy"]

            if strategy == "targeted":
                # Execute specific tests
                test_files = recommendation["tests"]
                if not test_files:
                    if verbose:
                        print("✅ No specific tests to run - validation passed")
                    return 0

                if verbose:
                    print(f"🎯 Running targeted tests ({len(test_files)} files)...")

                # Build pytest command for targeted tests
                args = [
                    "python",
                    "-m",
                    "pytest",
                    "--tb=short",
                    "--maxfail=3",
                    "--cov=calendarbot",
                    "--cov-report=term",
                    "--cov-fail-under=30",  # Lower threshold for targeted tests since they don't cover full codebase
                    "-q",
                ] + test_files

                result = subprocess.run(
                    args, cwd=self.workspace_dir, capture_output=True, text=True
                )

                if verbose:
                    if result.returncode == 0:
                        print("✅ Targeted tests passed")
                    else:
                        print("❌ Targeted tests failed")
                        print(result.stdout[-500:] if result.stdout else "")  # Show last 500 chars
                        print(result.stderr[-500:] if result.stderr else "")

                return result.returncode

            elif strategy == "critical_path":
                # Execute critical path suite
                if verbose:
                    print("🚀 Running critical path test suite...")

                execution = self.execute_suite("critical_path", parallel=True, verbose=False)

                if verbose:
                    if execution.status == "PASS":
                        print(
                            f"✅ Critical path tests passed ({execution.duration:.1f}s, {execution.passed}/{execution.test_count} tests)"
                        )
                    else:
                        print(f"❌ Critical path tests failed ({execution.failed} failures)")
                        if execution.notes:
                            print(f"   Error: {execution.notes}")

                return 0 if execution.status == "PASS" else 1

            elif strategy == "full_regression":
                # Execute full regression suite
                if verbose:
                    print("🏗️  Running full regression test suite...")
                    print("   Note: This may take 20-30 minutes")

                execution = self.execute_suite("full_regression", parallel=True, verbose=False)

                if verbose:
                    if execution.status == "PASS":
                        print(
                            f"✅ Full regression tests passed ({execution.duration//60:.0f}m {execution.duration%60:.0f}s)"
                        )
                    else:
                        print(f"❌ Full regression tests failed ({execution.failed} failures)")
                        if execution.notes:
                            print(f"   Error: {execution.notes}")

                return 0 if execution.status == "PASS" else 1

            else:
                if verbose:
                    print(f"❌ Unknown strategy: {strategy}")
                return 1

        except Exception as e:
            if verbose:
                print(f"❌ Smart test execution failed: {str(e)}")
            return 1

    def execute_targeted_tests(self, test_files: List[str], verbose: bool = True) -> int:
        """
        Execute specific test files with optimized settings.

        Args:
            test_files: List of test file paths to execute
            verbose: Enable verbose output

        Returns:
            Exit code (0 = success, 1 = failure)
        """
        if not test_files:
            if verbose:
                print("✅ No tests to execute")
            return 0

        try:
            args = [
                "python",
                "-m",
                "pytest",
                "--tb=short",
                "--maxfail=5",
                "--timeout=60",  # 60 second timeout per test
                "--cov=calendarbot",
                "--cov-report=term",
                "--cov-fail-under=30",  # Lower threshold for targeted tests since they don't cover full codebase
                "-v" if verbose else "-q",
            ] + test_files

            if verbose:
                print(f"🎯 Executing {len(test_files)} targeted test files...")

            result = subprocess.run(args, cwd=self.workspace_dir, capture_output=True, text=True)

            # Parse basic results
            test_count, passed, failed, skipped = self._parse_pytest_output(result.stdout)

            if verbose:
                if result.returncode == 0:
                    print(
                        f"✅ Targeted tests passed: {passed} passed, {failed} failed, {skipped} skipped"
                    )
                else:
                    print(
                        f"❌ Targeted tests failed: {passed} passed, {failed} failed, {skipped} skipped"
                    )
                    # Show relevant output
                    if result.stdout:
                        lines = result.stdout.split("\n")
                        # Show FAILURES section and summary
                        for i, line in enumerate(lines):
                            if "FAILURES" in line or "ERRORS" in line or "=====" in line:
                                print("\n".join(lines[i : i + 20]))  # Show next 20 lines
                                break

            return result.returncode

        except Exception as e:
            if verbose:
                print(f"❌ Error executing targeted tests: {str(e)}")
            return 1


def main():
    """CLI interface for test suite management."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Suite Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Execute command
    exec_parser = subparsers.add_parser("execute", help="Execute a test suite")
    exec_parser.add_argument("suite", choices=["critical_path", "full_regression"])
    exec_parser.add_argument("--parallel", action="store_true", default=True)
    exec_parser.add_argument("--verbose", action="store_true", default=True)

    # Smart selection command
    smart_parser = subparsers.add_parser("smart", help="Smart test selection")
    smart_parser.add_argument("--target-duration", type=float, help="Target duration in seconds")

    # Execute smart command (for pre-commit)
    execute_smart_parser = subparsers.add_parser(
        "execute-smart", help="Execute smart test strategy for pre-commit"
    )
    execute_smart_parser.add_argument(
        "--verbose", action="store_true", default=True, help="Enable verbose output"
    )
    execute_smart_parser.add_argument("--quiet", action="store_true", help="Disable verbose output")

    # Analysis command
    analysis_parser = subparsers.add_parser("analyze", help="Performance analysis")
    analysis_parser.add_argument("--days", type=int, default=7, help="Days to analyze")

    # Changed files command
    changed_parser = subparsers.add_parser("changed", help="Show changed files and related tests")

    args = parser.parse_args()

    manager = TestSuiteManager()

    if args.command == "execute":
        print(f"Executing {args.suite} test suite...")
        execution = manager.execute_suite(args.suite, parallel=args.parallel, verbose=args.verbose)

        report = manager.generate_execution_report(execution)
        print(json.dumps(report, indent=2, default=str))

    elif args.command == "smart":
        recommendation = manager.smart_test_selection(args.target_duration)
        print(json.dumps(recommendation, indent=2))

    elif args.command == "execute-smart":
        verbose = args.verbose and not args.quiet
        exit_code = manager.execute_smart_strategy(verbose=verbose)
        sys.exit(exit_code)

    elif args.command == "analyze":
        analysis = manager.analyze_test_performance(args.days)
        print(json.dumps(analysis, indent=2))

    elif args.command == "changed":
        changed_files = manager.get_changed_files()
        related_tests = manager.get_related_tests(changed_files)

        print(f"Changed files ({len(changed_files)}):")
        for file_path in changed_files:
            print(f"  {file_path}")

        print(f"\nRelated tests ({len(related_tests)}):")
        for test_path in related_tests:
            print(f"  {test_path}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
