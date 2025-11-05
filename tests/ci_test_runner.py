#!/usr/bin/env python3
"""
CI Test Runner for CalendarBot GitHub Actions workflows.

This script provides unified test execution interface for CI/CD pipelines.
Supports both the active calendarbot_lite and legacy calendarbot projects.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, description: str = "") -> int:
    """Run a shell command and return exit code."""
    print(f"{'=' * 60}")
    if description:
        print(f"Running: {description}")
    print(f"Command: {cmd}")
    print(f"{'=' * 60}")

    result = subprocess.run(cmd, check=False, shell=True)
    return result.returncode


def run_critical_path_tests() -> int:
    """Run fast, critical path tests for immediate feedback.

    Runs only smoke tests - essential functionality checks that complete in <2 minutes.
    These tests verify:
    - Server can start
    - Core parsing works
    - Basic API endpoints respond
    - Essential Alexa handlers function
    """
    print("Running critical path tests (smoke tests only)...")

    # Run ONLY smoke tests for critical path (<2 minutes target)
    # No coverage for fast feedback - use --coverage or --full-regression for coverage
    cmd = "pytest tests/lite/ -m 'smoke' -x --tb=short"
    return run_command(cmd, "Critical Path Tests (Smoke)")


def run_lint() -> int:
    """Run code linting."""
    print("Running linting...")

    # Focus on calendarbot_lite for active development
    cmd = "ruff check calendarbot_lite/"
    return run_command(cmd, "Linting with Ruff")


def run_type_check() -> int:
    """Run type checking."""
    print("Running type checking...")

    # Focus on calendarbot_lite only
    # Archived calendarbot/ directory is excluded via pyproject.toml configuration
    cmd = "mypy calendarbot_lite/ --no-error-summary"
    return run_command(cmd, "Type Checking with MyPy")


def run_security() -> int:
    """Run security analysis."""
    print("Running security analysis...")

    # Run on calendarbot_lite (active) instead of calendarbot (archived)
    cmd = "bandit -r calendarbot_lite/ --skip B101,B603"
    return run_command(cmd, "Security Analysis")


def run_full_regression() -> int:
    """Run complete test suite."""
    print("Running full regression tests...")

    # Clean old coverage data to prevent branch/statement mismatch errors
    subprocess.run("coverage erase", shell=True, check=False)

    # Run all calendarbot_lite tests
    cmd = "pytest tests/lite/ calendarbot_lite/ -v --cov=calendarbot_lite --cov-report=html:htmlcov --cov-report=xml:coverage.xml --cov-report=json:coverage.json --junitxml=pytest-results.xml"
    return run_command(cmd, "Full Test Suite")


def run_browser_tests() -> int:
    """Run browser-based tests."""
    print("Running browser tests...")

    # Run browser integration tests if they exist
    if os.path.exists("tests/browser"):
        cmd = "pytest tests/browser/ -v"
        return run_command(cmd, "Browser Tests")
    print("No browser tests found, skipping...")
    return 0


def run_coverage() -> int:
    """Generate coverage report."""
    print("Generating coverage report...")

    # Clean old coverage data to prevent branch/statement mismatch errors
    subprocess.run("coverage erase", shell=True, check=False)

    cmd = "pytest tests/lite/ calendarbot_lite/ --cov=calendarbot_lite --cov-report=xml:coverage.xml --cov-report=term-missing"
    return run_command(cmd, "Coverage Report")


def run_coverage_report() -> int:
    """Generate detailed coverage reports."""
    print("Generating detailed coverage reports...")

    # Clean old coverage data to prevent branch/statement mismatch errors
    subprocess.run("coverage erase", shell=True, check=False)

    cmd = "pytest tests/lite/ calendarbot_lite/ --cov=calendarbot_lite --cov-report=html:htmlcov --cov-report=xml:coverage.xml --cov-report=json:coverage.json"
    return run_command(cmd, "Detailed Coverage Reports")


def run_coverage_diff() -> int:
    """Analyze coverage differential."""
    print("Running coverage differential analysis...")

    # Clean old coverage data to prevent branch/statement mismatch errors
    subprocess.run("coverage erase", shell=True, check=False)

    # Basic coverage check - can be enhanced with coverage comparison logic
    cmd = "pytest tests/lite/ --cov=calendarbot_lite --cov-report=term --cov-fail-under=70"
    return run_command(cmd, "Coverage Differential")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="CalendarBot CI Test Runner")
    parser.add_argument("--critical-path", action="store_true", help="Run critical path tests")
    parser.add_argument("--lint", action="store_true", help="Run linting")
    parser.add_argument("--type-check", action="store_true", help="Run type checking")
    parser.add_argument("--security", action="store_true", help="Run security analysis")
    parser.add_argument("--full-regression", action="store_true", help="Run full test suite")
    parser.add_argument("--browser", action="store_true", help="Run browser tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument(
        "--coverage-report", action="store_true", help="Generate detailed coverage reports"
    )
    parser.add_argument(
        "--coverage-diff", action="store_true", help="Run coverage differential analysis"
    )
    parser.add_argument("--coverage-fail-under", type=int, help="Fail if coverage below threshold")

    args = parser.parse_args()

    # Ensure we're in the right directory
    os.chdir(Path(__file__).parent.parent)

    exit_code = 0

    # Process arguments
    if args.critical_path:
        exit_code = max(exit_code, run_critical_path_tests())

    if args.lint:
        exit_code = max(exit_code, run_lint())

    if args.type_check:
        exit_code = max(exit_code, run_type_check())

    if args.security:
        exit_code = max(exit_code, run_security())

    if args.full_regression:
        exit_code = max(exit_code, run_full_regression())

    if args.browser:
        exit_code = max(exit_code, run_browser_tests())

    if args.coverage:
        if args.coverage_fail_under:
            # Clean old coverage data to prevent branch/statement mismatch errors
            subprocess.run("coverage erase", shell=True, check=False)
            cmd = f"pytest tests/lite/ --cov=calendarbot_lite --cov-report=xml:coverage.xml --cov-fail-under={args.coverage_fail_under}"
            exit_code = max(exit_code, run_command(cmd, "Coverage with Threshold"))
        else:
            exit_code = max(exit_code, run_coverage())

    if args.coverage_report:
        exit_code = max(exit_code, run_coverage_report())

    if args.coverage_diff:
        exit_code = max(exit_code, run_coverage_diff())

    # If no specific action requested, run critical path by default
    if not any(vars(args).values()):
        print("No specific test requested, running critical path tests...")
        exit_code = run_critical_path_tests()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
