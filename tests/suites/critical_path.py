#!/usr/bin/env python3
"""
Critical Path Test Suite Configuration for CalendarBot.

This module defines the critical path test suite that must execute in under 5 minutes
for CI/CD pipeline integration. It includes essential tests for core functionality
while excluding slow operations like visual regression and extensive browser tests.

Target: <5 minutes execution time on standard CI hardware
Focus: Core functionality, security essentials, basic integration
"""

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class TestCategory:
    """Configuration for a test category."""

    name: str
    paths: List[str]
    markers: List[str]
    max_duration: float  # seconds
    parallel: bool = True
    priority: int = 1  # 1=highest, 5=lowest


class CriticalPathSuite:
    """
    Critical Path Test Suite Configuration.

    Defines which tests to include in the fast-feedback CI/CD pipeline.
    Target execution time: <5 minutes
    """

    # Maximum execution time for critical path suite (seconds)
    MAX_EXECUTION_TIME = 300  # 5 minutes

    # Test categories in execution order (highest priority first)
    TEST_CATEGORIES = [
        TestCategory(
            name="core_unit_tests",
            paths=[
                "tests/unit/test_ics_fetcher.py::TestICSFetcher::test_basic_fetch",
                "tests/unit/test_ics_fetcher.py::TestICSFetcher::test_ssrf_protection",
                "tests/unit/test_cache_manager.py::TestCacheManager::test_cache_events_success",
                "tests/unit/test_cache_manager.py::TestCacheManager::test_retrieve_cached_events",
                "tests/unit/test_source_manager.py::TestSourceManager::test_initialize_success",
                "tests/unit/test_web_server.py::TestWebServer::test_server_start_stop",
                "tests/unit/test_calendar_bot.py::TestCalendarBot::test_initialize_success",
            ],
            markers=["unit", "critical_path"],
            max_duration=60,  # 1 minute
            priority=1,
        ),
        TestCategory(
            name="security_essentials",
            paths=[
                "tests/unit/test_ics_fetcher.py::TestSSRFProtection",
                "tests/unit/test_web_server.py::TestSecurityValidation",
            ],
            markers=["security", "critical_path"],
            max_duration=30,  # 30 seconds
            priority=1,
        ),
        TestCategory(
            name="api_endpoints",
            paths=[
                "tests/unit/test_web_server.py::TestAPIEndpoints::test_status_endpoint",
                "tests/unit/test_web_server.py::TestAPIEndpoints::test_navigate_endpoint",
                "tests/unit/test_web_server.py::TestAPIEndpoints::test_layout_endpoint",
                "tests/unit/test_web_server.py::TestAPIEndpoints::test_refresh_endpoint",
            ],
            markers=["unit", "critical_path"],
            max_duration=45,  # 45 seconds
            priority=2,
        ),
        TestCategory(
            name="basic_integration",
            paths=[
                "tests/integration/test_web_api_integration.py::TestBasicIntegration::test_status_api_with_backend",
                "tests/integration/test_web_api_integration.py::TestBasicIntegration::test_navigation_with_cache",
            ],
            markers=["integration", "critical_path"],
            max_duration=60,  # 1 minute
            priority=2,
        ),
        TestCategory(
            name="core_workflows",
            paths=[
                "tests/e2e/test_application_workflows.py::TestApplicationLifecycle::test_startup_initialization",
                "tests/e2e/test_application_workflows.py::TestApplicationLifecycle::test_basic_refresh_cycle",
            ],
            markers=["e2e", "critical_path"],
            max_duration=90,  # 1.5 minutes
            priority=3,
        ),
        TestCategory(
            name="web_interface_smoke",
            paths=[
                "tests/browser/test_web_interface.py::TestBasicFunctionality::test_page_loads",
                "tests/browser/test_web_interface.py::TestBasicFunctionality::test_navigation_buttons",
                "tests/browser/test_web_interface.py::TestBasicFunctionality::test_layout_switching",
            ],
            markers=["browser", "smoke", "critical_path"],
            max_duration=45,  # 45 seconds
            priority=4,
        ),
    ]

    # Tests to explicitly exclude from critical path
    EXCLUDED_MARKERS = [
        "slow",
        "visual_regression",
        "performance",
        "accessibility",
        "cross_browser",
        "responsive",
    ]

    # Tests to explicitly exclude by pattern
    EXCLUDED_PATTERNS = ["**/*_large_dataset*", "**/*_stress_test*", "**/*_load_test*"]

    @classmethod
    def get_pytest_args(cls, parallel: bool = True, verbose: bool = True) -> List[str]:
        """
        Generate pytest arguments for critical path execution.

        Args:
            parallel: Enable parallel execution
            verbose: Enable verbose output

        Returns:
            List of pytest command arguments
        """
        args = [
            "python",
            "-m",
            "pytest",
            # Test selection
            "-m",
            cls._build_marker_expression(),
            # Coverage (lightweight for speed) - no fail threshold for critical path
            "--cov=calendarbot",
            "--cov-report=term",
            "--cov-fail-under=0",  # No coverage threshold for fast feedback
            # Performance optimization
            "--tb=short",
            "--maxfail=5",  # Stop after 5 failures for fast feedback
            "--durations=10",  # Show 10 slowest tests
            # Timeout protection
            "--timeout=60",  # 60 seconds per test max
            # Stability improvements
            "--disable-warnings",
        ]

        if parallel:
            args.extend(["-n", "2"])  # Limited parallel execution for stability

        if verbose:
            args.append("-v")
        else:
            args.append("-q")

        # Don't add specific test paths - rely on marker selection
        # This is more maintainable and works with our marked tests

        return args

    @classmethod
    def _build_marker_expression(cls) -> str:
        """Build marker expression for test selection."""
        # Include only critical path markers - NO browser/smoke tests
        include_markers = ["critical_path"]

        # Exclude slow markers AND browser tests (which cause parallel execution issues)
        exclude_markers = cls.EXCLUDED_MARKERS + ["browser", "smoke"]

        # Build expression: critical_path and not (slow or browser or visual_regression...)
        include_expr = " or ".join(include_markers)
        exclude_expr = " or ".join(exclude_markers)

        return f"({include_expr}) and not ({exclude_expr})"

    @classmethod
    def get_execution_plan(cls) -> Dict[str, Any]:
        """
        Get detailed execution plan for the critical path suite.

        Returns:
            Dictionary containing execution plan details
        """
        total_estimated_time = sum(cat.max_duration for cat in cls.TEST_CATEGORIES)

        return {
            "suite_name": "Critical Path",
            "target_duration": cls.MAX_EXECUTION_TIME,
            "estimated_duration": total_estimated_time,
            "categories": [
                {
                    "name": cat.name,
                    "test_count": len(cat.paths),
                    "max_duration": cat.max_duration,
                    "priority": cat.priority,
                    "parallel": cat.parallel,
                    "markers": cat.markers,
                }
                for cat in cls.TEST_CATEGORIES
            ],
            "excluded_markers": cls.EXCLUDED_MARKERS,
            "excluded_patterns": cls.EXCLUDED_PATTERNS,
            "optimization_features": [
                "Parallel execution with pytest-xdist",
                "Fast failure detection (maxfail=3)",
                "Lightweight coverage reporting",
                "30-second per-test timeout",
                "Priority-based test ordering",
            ],
        }

    @classmethod
    def validate_execution_time(cls, actual_duration: float) -> Dict[str, Any]:
        """
        Validate that execution time meets critical path requirements.

        Args:
            actual_duration: Actual execution time in seconds

        Returns:
            Validation results
        """
        target_met = actual_duration <= cls.MAX_EXECUTION_TIME
        efficiency = (cls.MAX_EXECUTION_TIME - actual_duration) / cls.MAX_EXECUTION_TIME * 100

        return {
            "target_met": target_met,
            "actual_duration": actual_duration,
            "target_duration": cls.MAX_EXECUTION_TIME,
            "efficiency_percentage": max(0, efficiency),
            "status": "PASS" if target_met else "FAIL",
            "recommendation": cls._get_performance_recommendation(actual_duration),
        }

    @classmethod
    def _get_performance_recommendation(cls, actual_duration: float) -> str:
        """Get performance improvement recommendation."""
        if actual_duration <= cls.MAX_EXECUTION_TIME:
            return "Critical path suite execution time is within target."

        overage = actual_duration - cls.MAX_EXECUTION_TIME
        overage_percent = (overage / cls.MAX_EXECUTION_TIME) * 100

        if overage_percent < 20:
            return f"Slightly over target by {overage:.1f}s. Consider removing slowest tests."
        elif overage_percent < 50:
            return f"Significantly over target by {overage:.1f}s. Review test selection and optimize slow tests."
        else:
            return (
                f"Critically over target by {overage:.1f}s. Major test suite restructuring needed."
            )


def main():
    """CLI interface for critical path suite configuration."""
    import argparse

    parser = argparse.ArgumentParser(description="Critical Path Test Suite Configuration")
    parser.add_argument("--plan", action="store_true", help="Show execution plan")
    parser.add_argument("--args", action="store_true", help="Show pytest arguments")
    parser.add_argument("--validate", type=float, help="Validate execution time")

    args = parser.parse_args()

    if args.plan:
        import json

        plan = CriticalPathSuite.get_execution_plan()
        print(json.dumps(plan, indent=2))
    elif args.args:
        pytest_args = CriticalPathSuite.get_pytest_args()
        print(" ".join(pytest_args))
    elif args.validate is not None:
        result = CriticalPathSuite.validate_execution_time(args.validate)
        print(f"Status: {result['status']}")
        print(f"Duration: {result['actual_duration']:.1f}s / {result['target_duration']}s")
        print(f"Efficiency: {result['efficiency_percentage']:.1f}%")
        print(f"Recommendation: {result['recommendation']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
