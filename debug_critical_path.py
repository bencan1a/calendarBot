#!/usr/bin/env python3
"""
Diagnostic script to identify critical path test suite issues.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.suites.critical_path import CriticalPathSuite


def analyze_critical_path_issues():
    """Analyze critical path test suite for configuration issues."""

    print("🔍 CRITICAL PATH TEST SUITE DIAGNOSTIC")
    print("=" * 60)

    # Get pytest arguments
    args = CriticalPathSuite.get_pytest_args(parallel=True, verbose=True)
    print(f"Generated pytest args: {' '.join(args)}")

    # Check marker expression
    marker_expr = CriticalPathSuite._build_marker_expression()
    print(f"Marker expression: {marker_expr}")

    # Check for conflicting configurations
    print("\n🚨 POTENTIAL ISSUES IDENTIFIED:")

    # Issue 1: Parallel execution with browser tests
    if "-n" in args and "smoke" in marker_expr:
        print("❌ PARALLEL + BROWSER CONFLICT:")
        print("   - Critical path enables parallel execution (-n 2)")
        print("   - Includes 'smoke' marker which includes browser tests")
        print("   - Browser tests cannot run in parallel (port conflicts, asyncio issues)")

    # Issue 2: Browser tests in critical path
    if "smoke" in marker_expr:
        print("❌ BROWSER TESTS IN CRITICAL PATH:")
        print("   - Browser tests are marked as 'smoke'")
        print("   - Browser tests are slow and hang-prone")
        print("   - Should not be in <5 minute critical path suite")

    # Issue 3: Timeout conflicts
    if "--timeout=60" in args:
        print("❌ TIMEOUT MISMATCH:")
        print("   - Critical path sets 60s timeout per test")
        print("   - Browser tests often need 8+ seconds just for page load")
        print("   - Plus browser setup/teardown time")

    # Get execution plan
    plan = CriticalPathSuite.get_execution_plan()
    print(f"\n📊 EXECUTION PLAN:")
    print(f"   Target duration: {plan['target_duration']}s")
    print(f"   Estimated duration: {plan['estimated_duration']}s")
    print(f"   Categories: {len(plan['categories'])}")

    print(f"\n🔧 RECOMMENDED FIXES:")
    print("1. Remove browser tests from critical path suite")
    print("2. Create separate 'critical_path_no_browser' marker")
    print("3. Disable parallel execution for tests with browser marker")
    print("4. Move browser tests to full regression suite only")


if __name__ == "__main__":
    analyze_critical_path_issues()
