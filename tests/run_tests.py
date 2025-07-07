#!/usr/bin/env python3
"""
Test runner script for CalendarBot test suite.

This script provides convenient ways to run different types of tests
and generate comprehensive reports.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description or ' '.join(cmd)}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"✅ {description or 'Command'} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description or 'Command'} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        return False


def run_unit_tests():
    """Run unit tests only."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/unit/",
        "-m",
        "unit",
        "--cov=calendarbot",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/unit",
        "-v",
    ]
    return run_command(cmd, "Unit Tests")


def run_integration_tests():
    """Run integration tests only."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/integration/",
        "-m",
        "integration",
        "--cov=calendarbot",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/integration",
        "-v",
    ]
    return run_command(cmd, "Integration Tests")


def run_e2e_tests():
    """Run end-to-end tests only."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/e2e/",
        "-m",
        "e2e",
        "--cov=calendarbot",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/e2e",
        "-v",
    ]
    return run_command(cmd, "End-to-End Tests")


def run_security_tests():
    """Run security-focused tests only."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "-m",
        "security",
        "--cov=calendarbot",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/security",
        "-v",
    ]
    return run_command(cmd, "Security Tests")


def run_performance_tests():
    """Run performance tests only."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "-m",
        "performance",
        "--cov=calendarbot",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/performance",
        "-v",
    ]
    return run_command(cmd, "Performance Tests")


def run_all_tests():
    """Run all tests with comprehensive coverage."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/",
        "--cov=calendarbot",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/complete",
        "--cov-report=xml",
        "--cov-report=json",
        "--cov-fail-under=80",
        "--cov-config=.coveragerc",
        "--durations=10",
        "-v",
    ]
    return run_command(cmd, "Complete Test Suite")


def run_fast_tests():
    """Run fast tests only (exclude slow, e2e, and visual regression)."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/",
        "-m",
        "not slow and not e2e and not visual_regression",
        "--cov=calendarbot",
        "--cov-report=term-missing",
        "-v",
    ]
    return run_command(cmd, "Fast Tests (Critical Path)")


def run_critical_path_suite():
    """Run critical path test suite (5-minute target)."""
    try:
        # Import the critical path suite configuration
        sys.path.insert(0, str(Path(__file__).parent))
        from suites.critical_path import CriticalPathSuite

        args = CriticalPathSuite.get_pytest_args(parallel=True, verbose=True)
        return run_command(args, "Critical Path Test Suite (<5 minutes)")
    except ImportError:
        print("❌ Critical path suite configuration not found")
        return False


def run_full_regression_suite():
    """Run full regression test suite (20-30 minutes)."""
    try:
        # Import the full regression suite configuration
        sys.path.insert(0, str(Path(__file__).parent))
        from suites.full_regression import FullRegressionSuite

        args = FullRegressionSuite.get_pytest_args(
            include_slow=True, parallel=True, verbose=True, coverage_detailed=True
        )
        return run_command(args, "Full Regression Test Suite (20-30 minutes)")
    except ImportError:
        print("❌ Full regression suite configuration not found")
        return False


def run_smart_test_selection():
    """Run smart test selection based on changed files."""
    try:
        # Import the suite manager
        sys.path.insert(0, str(Path(__file__).parent))
        from suites.suite_manager import TestSuiteManager

        manager = TestSuiteManager()
        recommendation = manager.smart_test_selection()

        print(f"\n{'='*60}")
        print("SMART TEST SELECTION RECOMMENDATION")
        print(f"{'='*60}")
        print(f"Strategy: {recommendation['strategy']}")
        print(f"Reason: {recommendation['reason']}")
        print(
            f"Estimated Duration: {recommendation['estimated_duration']//60}m {recommendation['estimated_duration']%60}s"
        )
        print(f"Changed Files: {len(recommendation['changed_files'])}")
        print(f"Related Tests: {len(recommendation['related_tests'])}")

        if recommendation["strategy"] == "critical_path":
            return run_critical_path_suite()
        elif recommendation["strategy"] == "full_regression":
            return run_full_regression_suite()
        elif recommendation["strategy"] == "targeted" and recommendation["tests"]:
            # Run specific tests
            cmd = [
                "python",
                "-m",
                "pytest",
                *recommendation["tests"],
                "--cov=calendarbot",
                "--cov-report=term-missing",
                "-v",
            ]
            return run_command(cmd, "Smart Selected Tests")
        else:
            return run_fast_tests()

    except ImportError:
        print("❌ Suite manager not found, falling back to fast tests")
        return run_fast_tests()


def analyze_test_suites():
    """Analyze test suite performance and provide recommendations."""
    try:
        # Import the suite manager
        sys.path.insert(0, str(Path(__file__).parent))
        import json

        from suites.suite_manager import TestSuiteManager

        manager = TestSuiteManager()
        analysis = manager.analyze_test_performance(days=7)

        print(f"\n{'='*60}")
        print("TEST SUITE PERFORMANCE ANALYSIS")
        print(f"{'='*60}")
        print(json.dumps(analysis, indent=2, default=str))

        return True

    except ImportError:
        print("❌ Suite manager not found")
        return False


def optimize_test_suites():
    """Optimize test suite organization and execution."""
    try:
        # Import suite configurations
        sys.path.insert(0, str(Path(__file__).parent))
        from suites.critical_path import CriticalPathSuite
        from suites.full_regression import FullRegressionSuite

        print(f"\n{'='*60}")
        print("TEST SUITE OPTIMIZATION ANALYSIS")
        print(f"{'='*60}")

        # Show critical path plan
        print("\nCRITICAL PATH SUITE:")
        critical_plan = CriticalPathSuite.get_execution_plan()
        print(
            f"  Target Duration: {critical_plan['target_duration']}s ({critical_plan['target_duration']//60}m)"
        )
        print(
            f"  Estimated Duration: {critical_plan['estimated_duration']}s ({critical_plan['estimated_duration']//60}m)"
        )
        print(f"  Categories: {len(critical_plan['categories'])}")
        print(f"  Excluded Markers: {', '.join(critical_plan['excluded_markers'])}")

        # Show full regression plan
        print("\nFULL REGRESSION SUITE:")
        regression_plan = FullRegressionSuite.get_execution_plan()
        print(f"  Target Duration: {regression_plan['target_duration_range']}")
        print(f"  Estimated Duration: {regression_plan['estimated_duration']//60}m")
        print(f"  Phases: {len(regression_plan['phases'])}")
        print(
            f"  Coverage Targets: Line {regression_plan['coverage_targets']['line_coverage']}%, Branch {regression_plan['coverage_targets']['branch_coverage']}%"
        )

        return True

    except ImportError:
        print("❌ Suite configurations not found")
        return False


def run_specific_test(test_path):
    """Run a specific test file or test function."""
    cmd = [
        "python",
        "-m",
        "pytest",
        test_path,
        "--cov=calendarbot",
        "--cov-report=term-missing",
        "-v",
        "-s",
    ]
    return run_command(cmd, f"Specific Test: {test_path}")


def run_browser_tests():
    """Run all browser automation tests."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/browser/",
        "--cov=calendarbot",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/browser",
        "-v",
    ]
    return run_command(cmd, "Browser Tests")


def run_accessibility_tests():
    """Run accessibility tests only."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "-m",
        "accessibility",
        "--cov=calendarbot",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/accessibility",
        "-v",
    ]
    return run_command(cmd, "Accessibility Tests")


def run_visual_regression_tests():
    """Run visual regression tests only."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "-m",
        "visual_regression",
        "--cov=calendarbot",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/visual_regression",
        "-v",
    ]
    return run_command(cmd, "Visual Regression Tests")


def run_responsive_tests():
    """Run responsive design tests only."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "-m",
        "responsive",
        "--cov=calendarbot",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/responsive",
        "-v",
    ]
    return run_command(cmd, "Responsive Design Tests")


def run_cross_browser_tests():
    """Run cross-browser compatibility tests only."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "-m",
        "cross_browser",
        "--cov=calendarbot",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov/cross_browser",
        "-v",
    ]
    return run_command(cmd, "Cross-Browser Compatibility Tests")


def run_linting():
    """Run code linting and quality checks."""
    success = True

    # Flake8
    if run_command(["flake8", "calendarbot", "tests"], "Flake8 Linting"):
        print("✅ Flake8 checks passed")
    else:
        success = False

    # Black formatting check
    if run_command(["black", "--check", "calendarbot", "tests"], "Black Formatting Check"):
        print("✅ Black formatting checks passed")
    else:
        success = False

    # isort import sorting check
    if run_command(["isort", "--check-only", "calendarbot", "tests"], "isort Import Check"):
        print("✅ isort import checks passed")
    else:
        success = False

    return success


def run_type_checking():
    """Run type checking with mypy."""
    cmd = ["mypy", "calendarbot", "--ignore-missing-imports"]
    return run_command(cmd, "Type Checking (mypy)")


def generate_test_report():
    """Generate comprehensive test report."""
    print("\n" + "=" * 60)
    print("GENERATING COMPREHENSIVE TEST REPORT")
    print("=" * 60)

    # Run all tests with detailed output
    success = run_all_tests()

    if success:
        print("\n" + "=" * 60)
        print("TEST REPORT GENERATED")
        print("=" * 60)
        print("📊 Coverage report: htmlcov/complete/index.html")
        print("📄 XML coverage: coverage.xml")
        print("🎯 Coverage target: 80% line coverage")

        # Show coverage summary
        try:
            result = subprocess.run(
                ["python", "-m", "coverage", "report", "--show-missing"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print("\nCOVERAGE SUMMARY:")
                print(result.stdout)
        except:
            pass

    return success


def run_coverage_tests(coverage_type="all", fail_under=80, html=True, xml=True):
    """Run tests with specific coverage options."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/",
        "--cov=calendarbot",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-config=.coveragerc",
    ]

    if html:
        cmd.extend(["--cov-report=html:htmlcov/coverage"])
    if xml:
        cmd.extend(["--cov-report=xml", "--cov-report=json"])

    cmd.extend([f"--cov-fail-under={fail_under}", "-v"])

    return run_command(cmd, f"Coverage Tests ({coverage_type})")


def run_coverage_report():
    """Generate detailed coverage reports."""
    print("\n" + "=" * 60)
    print("GENERATING COVERAGE REPORTS")
    print("=" * 60)

    # Generate coverage analysis
    analysis_cmd = ["python", "tests/coverage_analysis.py", "--report"]
    success = run_command(analysis_cmd, "Coverage Analysis Report")

    if success:
        print("\n📊 Coverage reports available:")
        print("  • HTML Report: htmlcov/coverage/index.html")
        print("  • XML Report: coverage.xml")
        print("  • JSON Report: coverage.json")
        print("  • Analysis: Generated above")

    return success


def run_coverage_validation(threshold=80):
    """Validate coverage meets minimum thresholds."""
    print(f"\n" + "=" * 60)
    print(f"VALIDATING COVERAGE (≥{threshold}%)")
    print("=" * 60)

    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/",
        "--cov=calendarbot",
        "--cov-branch",
        "--cov-config=.coveragerc",
        f"--cov-fail-under={threshold}",
        "--cov-report=term",
        "-x",  # Stop on first failure
    ]

    return run_command(cmd, f"Coverage Validation (≥{threshold}%)")


def generate_coverage_diff():
    """Generate coverage differential report."""
    print("\n" + "=" * 60)
    print("GENERATING COVERAGE DIFFERENTIAL")
    print("=" * 60)

    # Store current coverage run
    store_cmd = ["python", "tests/coverage_analysis.py", "--store", "--type", "current"]
    if run_command(store_cmd, "Store Current Coverage"):
        # Generate trend analysis
        trends_cmd = ["python", "tests/coverage_analysis.py", "--trends", "--days", "7"]
        return run_command(trends_cmd, "Coverage Trends Analysis")

    return False


def clean_test_artifacts():
    """Clean test artifacts and cache."""
    artifacts = [
        ".pytest_cache",
        "__pycache__",
        "htmlcov",
        ".coverage",
        "coverage.xml",
        "coverage.json",
        ".coverage.*",
        "coverage_data",
        ".mypy_cache",
        "tests/browser/screenshots",
        "tests/browser/baselines",
        "tests/browser/reports",
    ]

    print("🧹 Cleaning test artifacts...")

    for artifact in artifacts:
        if os.path.exists(artifact):
            if os.path.isfile(artifact):
                os.remove(artifact)
                print(f"  Removed: {artifact}")
            else:
                subprocess.run(["rm", "-rf", artifact])
                print(f"  Removed: {artifact}/")

    print("✅ Test artifacts cleaned")


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(
        description="CalendarBot Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py --all                    # Run all tests
  python run_tests.py --unit                   # Run unit tests only
  python run_tests.py --integration            # Run integration tests only
  python run_tests.py --e2e                    # Run end-to-end tests only
  python run_tests.py --fast                   # Run fast tests only
  python run_tests.py --security               # Run security tests only
  python run_tests.py --performance            # Run performance tests only
  python run_tests.py --browser                # Run browser automation tests
  python run_tests.py --accessibility          # Run accessibility tests only
  python run_tests.py --visual-regression      # Run visual regression tests only
  python run_tests.py --responsive             # Run responsive design tests only
  python run_tests.py --cross-browser          # Run cross-browser compatibility tests only
  python run_tests.py --specific tests/unit/test_cache_manager.py
  python run_tests.py --lint                   # Run linting checks
  python run_tests.py --type-check             # Run type checking
  python run_tests.py --report                 # Generate comprehensive report
  python run_tests.py --clean                  # Clean test artifacts
  python run_tests.py --coverage               # Run tests with coverage tracking
  python run_tests.py --coverage-report        # Generate detailed coverage reports
  python run_tests.py --coverage-html          # Generate HTML coverage reports
  python run_tests.py --coverage-xml           # Generate XML coverage reports for CI
  python run_tests.py --coverage-fail-under 85 # Fail if coverage below 85%
  python run_tests.py --coverage-diff          # Generate coverage differential report
  python run_tests.py --critical-path          # Run critical path test suite (<5 minutes)
  python run_tests.py --full-regression        # Run full regression test suite (20-30 minutes)
  python run_tests.py --smart-selection        # Run tests based on code changes
  python run_tests.py --suite-analysis         # Analyze test suite performance and coverage
  python run_tests.py --optimize-suites        # Optimize test suite organization
        """,
    )

    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests only")
    parser.add_argument("--fast", action="store_true", help="Run fast tests only")
    parser.add_argument("--security", action="store_true", help="Run security tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--browser", action="store_true", help="Run browser automation tests")
    parser.add_argument("--accessibility", action="store_true", help="Run accessibility tests only")
    parser.add_argument(
        "--visual-regression", action="store_true", help="Run visual regression tests only"
    )
    parser.add_argument(
        "--responsive", action="store_true", help="Run responsive design tests only"
    )
    parser.add_argument(
        "--cross-browser", action="store_true", help="Run cross-browser compatibility tests only"
    )
    parser.add_argument("--specific", help="Run specific test file or function")
    parser.add_argument("--lint", action="store_true", help="Run linting checks")
    parser.add_argument("--type-check", action="store_true", help="Run type checking")
    parser.add_argument("--report", action="store_true", help="Generate comprehensive test report")
    parser.add_argument("--clean", action="store_true", help="Clean test artifacts")

    # New test suite options
    parser.add_argument(
        "--critical-path", action="store_true", help="Run critical path test suite (<5 minutes)"
    )
    parser.add_argument(
        "--full-regression",
        action="store_true",
        help="Run full regression test suite (20-30 minutes)",
    )
    parser.add_argument(
        "--smart-selection", action="store_true", help="Run tests based on code changes"
    )
    parser.add_argument(
        "--suite-analysis", action="store_true", help="Analyze test suite performance and coverage"
    )
    parser.add_argument(
        "--optimize-suites", action="store_true", help="Optimize test suite organization"
    )

    # Coverage-specific options
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage tracking")
    parser.add_argument(
        "--coverage-report", action="store_true", help="Generate detailed coverage reports"
    )
    parser.add_argument(
        "--coverage-html", action="store_true", help="Generate HTML coverage reports"
    )
    parser.add_argument(
        "--coverage-xml", action="store_true", help="Generate XML coverage reports for CI"
    )
    parser.add_argument(
        "--coverage-fail-under", type=int, default=80, help="Fail if coverage below threshold"
    )
    parser.add_argument(
        "--coverage-diff", action="store_true", help="Generate coverage differential report"
    )

    args = parser.parse_args()

    # Ensure we're in the right directory
    script_dir = Path(__file__).parent.parent
    os.chdir(script_dir)

    success = True

    if args.clean:
        clean_test_artifacts()
    elif args.coverage:
        success = run_coverage_tests(
            "all", args.coverage_fail_under, args.coverage_html, args.coverage_xml
        )
    elif args.coverage_report:
        success = run_coverage_report()
    elif args.coverage_diff:
        success = generate_coverage_diff()
    elif args.lint:
        success = run_linting()
    elif args.type_check:
        success = run_type_checking()
    elif args.report:
        success = generate_test_report()
    elif args.unit:
        success = run_unit_tests()
    elif args.integration:
        success = run_integration_tests()
    elif args.e2e:
        success = run_e2e_tests()
    elif args.security:
        success = run_security_tests()
    elif args.performance:
        success = run_performance_tests()
    elif args.browser:
        success = run_browser_tests()
    elif args.accessibility:
        success = run_accessibility_tests()
    elif args.visual_regression:
        success = run_visual_regression_tests()
    elif args.responsive:
        success = run_responsive_tests()
    elif args.cross_browser:
        success = run_cross_browser_tests()
    elif args.fast:
        success = run_fast_tests()
    elif args.critical_path:
        success = run_critical_path_suite()
    elif args.full_regression:
        success = run_full_regression_suite()
    elif args.smart_selection:
        success = run_smart_test_selection()
    elif args.suite_analysis:
        success = analyze_test_suites()
    elif args.optimize_suites:
        success = optimize_test_suites()
    elif args.specific:
        success = run_specific_test(args.specific)
    elif args.all:
        success = run_all_tests()
    else:
        # Default: run all tests
        success = run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
