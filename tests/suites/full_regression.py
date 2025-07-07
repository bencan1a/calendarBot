#!/usr/bin/env python3
"""
Full Regression Test Suite Configuration for CalendarBot.

This module defines the comprehensive regression test suite that includes
all test types for complete validation. Designed for nightly runs and
release validation with comprehensive coverage across all functionality.

Target: Complete coverage validation (20-30 minutes execution time)
Focus: All test types, comprehensive validation, edge cases
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
class TestSuite:
    """Configuration for a test suite category."""

    name: str
    paths: List[str]
    markers: List[str]
    estimated_duration: float  # seconds
    parallel: bool = True
    priority: int = 1  # 1=highest, 5=lowest
    requires_setup: List[str] = None  # Special setup requirements


class FullRegressionSuite:
    """
    Full Regression Test Suite Configuration.

    Includes all test types for comprehensive validation.
    Target execution time: 20-30 minutes
    """

    # Target execution time range (seconds)
    MIN_EXECUTION_TIME = 1200  # 20 minutes
    MAX_EXECUTION_TIME = 1800  # 30 minutes

    # Comprehensive test suites in execution order
    TEST_SUITES = [
        TestSuite(
            name="unit_tests_complete",
            paths=[
                "tests/unit/",
            ],
            markers=["unit"],
            estimated_duration=300,  # 5 minutes
            priority=1,
        ),
        TestSuite(
            name="integration_tests_complete",
            paths=[
                "tests/integration/",
            ],
            markers=["integration"],
            estimated_duration=360,  # 6 minutes
            priority=1,
        ),
        TestSuite(
            name="security_comprehensive",
            paths=[
                "tests/unit/test_ics_fetcher.py",
                "tests/unit/test_web_server.py",
                "tests/integration/test_web_api_integration.py",
            ],
            markers=["security"],
            estimated_duration=180,  # 3 minutes
            priority=1,
        ),
        TestSuite(
            name="e2e_workflows",
            paths=[
                "tests/e2e/",
            ],
            markers=["e2e"],
            estimated_duration=240,  # 4 minutes
            priority=2,
        ),
        TestSuite(
            name="browser_core",
            paths=[
                "tests/browser/test_web_interface.py",
                "tests/browser/test_api_integration.py",
            ],
            markers=["browser"],
            estimated_duration=300,  # 5 minutes
            priority=2,
            requires_setup=["browser_automation"],
        ),
        TestSuite(
            name="browser_responsive",
            paths=[
                "tests/browser/test_responsive_design.py",
            ],
            markers=["responsive", "browser"],
            estimated_duration=180,  # 3 minutes
            priority=3,
            requires_setup=["browser_automation"],
        ),
        TestSuite(
            name="stress_and_load",
            paths=[
                "tests/e2e/test_application_workflows.py",
            ],
            markers=["performance", "slow"],
            estimated_duration=240,  # 4 minutes
            priority=5,
        ),
    ]

    # Coverage targets for regression suite
    COVERAGE_TARGETS = {
        "line_coverage": 85,  # Higher target for regression
        "branch_coverage": 75,
        "function_coverage": 70,
    }

    # Additional pytest plugins for comprehensive testing
    REQUIRED_PLUGINS = [
        "pytest-xdist",  # Parallel execution
        "pytest-cov",  # Coverage tracking
        "pytest-html",  # HTML reports
        "pytest-json",  # JSON reports
        "pytest-timeout",  # Test timeouts
        "pytest-asyncio",  # Async support
        "pytest-mock",  # Mocking utilities
    ]

    @classmethod
    def get_pytest_args(
        cls,
        include_slow: bool = True,
        parallel: bool = True,
        verbose: bool = True,
        coverage_detailed: bool = True,
    ) -> List[str]:
        """
        Generate pytest arguments for full regression execution.

        Args:
            include_slow: Include slow and performance tests
            parallel: Enable parallel execution
            verbose: Enable verbose output
            coverage_detailed: Enable detailed coverage reporting

        Returns:
            List of pytest command arguments
        """
        args = [
            "python",
            "-m",
            "pytest",
            "tests/",  # Run all tests
            # Comprehensive coverage
            "--cov=calendarbot",
            "--cov-branch",
            "--cov-config=.coveragerc",
            f"--cov-fail-under={cls.COVERAGE_TARGETS['line_coverage']}",
        ]

        if coverage_detailed:
            args.extend(
                [
                    "--cov-report=html:htmlcov/regression",
                    "--cov-report=xml",
                    "--cov-report=json",
                    "--cov-report=term-missing",
                ]
            )
        else:
            args.extend(
                [
                    "--cov-report=term",
                    "--cov-report=xml",
                ]
            )

        # Test execution configuration
        args.extend(
            [
                "--tb=short",
                "--maxfail=10",  # Allow more failures for comprehensive view
                "--durations=20",  # Show 20 slowest tests
                "--timeout=120",  # 2 minutes per test max
            ]
        )

        # Include/exclude slow tests
        if include_slow:
            # Include all tests including slow ones
            pass  # No marker filtering
        else:
            args.extend(["-m", "not slow"])

        if parallel:
            args.extend(["-n", "auto"])

        if verbose:
            args.append("-v")
        else:
            args.append("-q")

        # HTML and JSON reporting
        args.extend(
            [
                "--html=htmlcov/regression_report.html",
                "--self-contained-html",
                "--json-report",
                "--json-report-file=htmlcov/regression_report.json",
            ]
        )

        return args

    @classmethod
    def get_execution_phases(cls) -> List[Dict[str, Any]]:
        """
        Get execution phases for staged test running.

        Returns:
            List of execution phases with test suites
        """
        phases = [
            {
                "name": "Core Validation",
                "description": "Essential unit and integration tests",
                "suites": [
                    "unit_tests_complete",
                    "integration_tests_complete",
                    "security_comprehensive",
                ],
                "estimated_duration": 840,  # 14 minutes
                "parallel": True,
                "required": True,
            },
            {
                "name": "Application Workflows",
                "description": "End-to-end workflow validation",
                "suites": ["e2e_workflows"],
                "estimated_duration": 240,  # 4 minutes
                "parallel": False,  # E2E tests often need sequential execution
                "required": True,
            },
            {
                "name": "Browser Automation Core",
                "description": "Core browser functionality tests",
                "suites": ["browser_core", "browser_responsive"],
                "estimated_duration": 480,  # 8 minutes
                "parallel": True,
                "required": True,
            },
            {
                "name": "Stress and Load",
                "description": "Stress and load testing",
                "suites": ["stress_and_load"],
                "estimated_duration": 240,  # 4 minutes
                "parallel": False,
                "required": False,
            },
        ]

        return phases

    @classmethod
    def get_execution_plan(cls, include_optional: bool = True) -> Dict[str, Any]:
        """
        Get detailed execution plan for the full regression suite.

        Args:
            include_optional: Include optional test phases

        Returns:
            Dictionary containing execution plan details
        """
        phases = cls.get_execution_phases()

        if not include_optional:
            phases = [p for p in phases if p["required"]]

        total_estimated_time = sum(phase["estimated_duration"] for phase in phases)

        return {
            "suite_name": "Full Regression",
            "target_duration_range": f"{cls.MIN_EXECUTION_TIME//60}-{cls.MAX_EXECUTION_TIME//60} minutes",
            "estimated_duration": total_estimated_time,
            "phases": phases,
            "coverage_targets": cls.COVERAGE_TARGETS,
            "required_plugins": cls.REQUIRED_PLUGINS,
            "optimization_features": [
                "Phased execution for early failure detection",
                "Parallel execution where appropriate",
                "Comprehensive coverage tracking",
                "HTML and JSON reporting",
                "Visual regression baseline management",
                "Performance monitoring and validation",
                "Cross-browser compatibility testing",
            ],
            "setup_requirements": {
                "browser_automation": "Playwright/Puppeteer setup required",
                "baseline_images": "Visual regression baselines needed",
                "multiple_browsers": "Chrome, Firefox, Safari availability",
            },
        }

    @classmethod
    def validate_execution_time(cls, actual_duration: float) -> Dict[str, Any]:
        """
        Validate that execution time meets regression suite expectations.

        Args:
            actual_duration: Actual execution time in seconds

        Returns:
            Validation results
        """
        within_range = cls.MIN_EXECUTION_TIME <= actual_duration <= cls.MAX_EXECUTION_TIME

        if actual_duration < cls.MIN_EXECUTION_TIME:
            status = "FAST"
            message = "Execution faster than expected. Verify all tests ran."
        elif actual_duration <= cls.MAX_EXECUTION_TIME:
            status = "OPTIMAL"
            message = "Execution time within expected range."
        else:
            overage = actual_duration - cls.MAX_EXECUTION_TIME
            status = "SLOW"
            message = f"Execution exceeded target by {overage//60:.0f}m {overage%60:.0f}s."

        return {
            "within_range": within_range,
            "actual_duration": actual_duration,
            "target_min": cls.MIN_EXECUTION_TIME,
            "target_max": cls.MAX_EXECUTION_TIME,
            "status": status,
            "message": message,
            "recommendation": cls._get_performance_recommendation(actual_duration),
        }

    @classmethod
    def _get_performance_recommendation(cls, actual_duration: float) -> str:
        """Get performance improvement recommendation."""
        if actual_duration < cls.MIN_EXECUTION_TIME:
            return "Consider adding more comprehensive test coverage or verify all test suites executed."
        elif actual_duration <= cls.MAX_EXECUTION_TIME:
            return "Regression suite execution time is optimal."
        else:
            overage_percent = (
                (actual_duration - cls.MAX_EXECUTION_TIME) / cls.MAX_EXECUTION_TIME
            ) * 100

            if overage_percent < 25:
                return "Slightly over target. Consider optimizing slowest tests or increasing parallelization."
            elif overage_percent < 50:
                return "Significantly over target. Review test efficiency and consider phase-based execution."
            else:
                return "Critically over target. Major optimization needed - consider splitting into multiple suites."

    @classmethod
    def get_coverage_validation_args(cls) -> List[str]:
        """Get arguments specifically for coverage validation."""
        return [
            "python",
            "-m",
            "pytest",
            "tests/",
            "--cov=calendarbot",
            "--cov-branch",
            "--cov-config=.coveragerc",
            f"--cov-fail-under={cls.COVERAGE_TARGETS['line_coverage']}",
            "--cov-report=term",
            "--cov-report=xml",
            "--cov-report=json",
            "-q",  # Quiet output for coverage focus
            "--tb=no",  # No traceback for coverage runs
        ]


def main():
    """CLI interface for full regression suite configuration."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Full Regression Test Suite Configuration")
    parser.add_argument("--plan", action="store_true", help="Show execution plan")
    parser.add_argument("--phases", action="store_true", help="Show execution phases")
    parser.add_argument("--args", action="store_true", help="Show pytest arguments")
    parser.add_argument(
        "--coverage-args", action="store_true", help="Show coverage validation arguments"
    )
    parser.add_argument("--validate", type=float, help="Validate execution time")
    parser.add_argument(
        "--no-optional", action="store_true", help="Exclude optional phases from plan"
    )

    args = parser.parse_args()

    if args.plan:
        plan = FullRegressionSuite.get_execution_plan(include_optional=not args.no_optional)
        print(json.dumps(plan, indent=2))
    elif args.phases:
        phases = FullRegressionSuite.get_execution_phases()
        for phase in phases:
            print(f"Phase: {phase['name']}")
            print(f"  Description: {phase['description']}")
            print(
                f"  Duration: {phase['estimated_duration']//60}m {phase['estimated_duration']%60}s"
            )
            print(f"  Required: {phase['required']}")
            print(f"  Suites: {', '.join(phase['suites'])}")
            print()
    elif args.args:
        pytest_args = FullRegressionSuite.get_pytest_args()
        print(" ".join(pytest_args))
    elif args.coverage_args:
        coverage_args = FullRegressionSuite.get_coverage_validation_args()
        print(" ".join(coverage_args))
    elif args.validate is not None:
        result = FullRegressionSuite.validate_execution_time(args.validate)
        print(f"Status: {result['status']}")
        print(f"Duration: {result['actual_duration']//60:.0f}m {result['actual_duration']%60:.0f}s")
        print(f"Target Range: {result['target_min']//60}-{result['target_max']//60} minutes")
        print(f"Within Range: {result['within_range']}")
        print(f"Message: {result['message']}")
        print(f"Recommendation: {result['recommendation']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
