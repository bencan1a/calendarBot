#!/usr/bin/env python3
"""
Comprehensive dead code analysis script for CalendarBot.

This script combines multiple static analysis tools to identify:
- Unused functions, classes, and variables
- Unused imports
- Print statements that should be logging
- Debug statements for production review
- TODO/FIXME comments (technical debt)
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from calendarbot.optimization.production import DebugStatementAnalyzer
except ImportError:
    print("Error: Unable to import DebugStatementAnalyzer")
    sys.exit(1)


def run_vulture_analysis(min_confidence: int = 80) -> list[str]:
    """Run vulture dead code detection."""
    print(f"🔍 Running Vulture analysis (confidence >= {min_confidence}%)...")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "vulture", "calendarbot", f"--min-confidence={min_confidence}"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        if result.stdout:
            return result.stdout.strip().split("\n")
        return []
    except Exception as e:
        print(f"Warning: Vulture analysis failed: {e}")
        return []


def run_unimport_analysis() -> list[str]:
    """Run unimport to find unused imports."""
    print("📦 Running unimport analysis...")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "unimport", "--check", "calendarbot"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        if result.stdout:
            return result.stdout.strip().split("\n")
        return []
    except Exception as e:
        print(f"Warning: Unimport analysis failed: {e}")
        return []


def run_debug_analyzer() -> dict[str, Any]:
    """Run the built-in debug statement analyzer."""
    print("🐛 Running debug statement analysis...")

    analyzer = DebugStatementAnalyzer()
    return analyzer.analyze_codebase("calendarbot")


def run_ruff_unused_analysis() -> list[str]:
    """Run Ruff to find unused variables and imports."""
    print("🦀 Running Ruff analysis for unused code...")

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "calendarbot",
                "--select",
                "F401,F841,ARG001,ARG002,ERA001",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        if result.stdout:
            return result.stdout.strip().split("\n")
        return []
    except Exception as e:
        print(f"Warning: Ruff analysis failed: {e}")
        return []


def generate_report(
    vulture_results: list[str],
    unimport_results: list[str],
    debug_results: dict[str, Any],
    ruff_results: list[str],
) -> None:
    """Generate a comprehensive dead code report."""

    print("\n" + "=" * 80)
    print("📊 DEAD CODE ANALYSIS REPORT")
    print("=" * 80)

    # Summary
    vulture_count = len([r for r in vulture_results if r.strip()])
    unimport_count = len([r for r in unimport_results if r.strip() and "at " in r])
    ruff_count = len([r for r in ruff_results if r.strip()])

    print("\n📈 SUMMARY:")
    print(f"   • Vulture findings: {vulture_count}")
    print(f"   • Unused imports (unimport): {unimport_count}")
    print(f"   • Ruff findings: {ruff_count}")
    print(f"   • Print statements: {len(debug_results.get('print_statements', []))}")
    print(f"   • Debug logs: {len(debug_results.get('debug_logs', []))}")
    print(f"   • TODO comments: {len(debug_results.get('todo_comments', []))}")

    # Detailed findings
    if vulture_count > 0:
        print(f"\n🔍 VULTURE FINDINGS ({vulture_count} items):")
        for item in vulture_results[:10]:  # Show first 10
            if item.strip():
                print(f"   • {item}")
        if vulture_count > 10:
            print(f"   ... and {vulture_count - 10} more items")

    if unimport_count > 0:
        print(f"\n📦 UNUSED IMPORTS ({unimport_count} items):")
        for item in unimport_results[:10]:
            if item.strip() and "at " in item:
                print(f"   • {item}")
        if unimport_count > 10:
            print(f"   ... and {unimport_count - 10} more items")

    if ruff_count > 0:
        print(f"\n🦀 RUFF FINDINGS ({ruff_count} items):")
        for item in ruff_results[:10]:
            if item.strip():
                print(f"   • {item}")
        if ruff_count > 10:
            print(f"   ... and {ruff_count - 10} more items")

    # Debug analysis
    print_statements = debug_results.get("print_statements", [])
    if print_statements:
        print(f"\n🖨️  PRINT STATEMENTS TO REVIEW ({len(print_statements)} items):")
        for stmt in print_statements[:5]:
            print(f"   • {stmt['file']}:{stmt['line']}")
        if len(print_statements) > 5:
            print(f"   ... and {len(print_statements) - 5} more files")

    # Optimization suggestions
    suggestions = debug_results.get("optimization_suggestions", [])
    if suggestions:
        print("\n💡 OPTIMIZATION SUGGESTIONS:")
        for suggestion in suggestions:
            priority = suggestion.get("priority", "unknown").upper()
            print(f"   • [{priority}] {suggestion['suggestion']}")

    # Action items
    print("\n🎯 RECOMMENDED ACTIONS:")
    print(f"   1. Review and remove {vulture_count} unused code items found by Vulture")
    print(f"   2. Clean up {unimport_count} unused imports")
    print(f"   3. Replace {len(print_statements)} print statements with proper logging")
    print(
        f"   4. Review {len(debug_results.get('debug_logs', []))} debug statements for production"
    )
    print(f"   5. Address {len(debug_results.get('todo_comments', []))} TODO/FIXME comments")

    print("\n🛠️  NEXT STEPS:")
    print("   • Run: vulture calendarbot --min-confidence=60 > dead_code_report.txt")
    print("   • Run: unimport --remove-all calendarbot (with backup!)")
    print("   • Run: ruff check calendarbot --select=F401,F841 --fix")
    print("   • Consider using autoflake for automated cleanup")

    print("\n" + "=" * 80)


def main():
    """Main execution function."""
    print("🚀 Starting comprehensive dead code analysis for CalendarBot...")
    print("This may take a few minutes...\n")

    # Run all analyses
    vulture_results = run_vulture_analysis(min_confidence=70)
    unimport_results = run_unimport_analysis()
    debug_results = run_debug_analyzer()
    ruff_results = run_ruff_unused_analysis()

    # Generate report
    generate_report(vulture_results, unimport_results, debug_results, ruff_results)

    # Save detailed results
    report_data = {
        "vulture_findings": vulture_results,
        "unimport_findings": unimport_results,
        "debug_analysis": debug_results,
        "ruff_findings": ruff_results,
    }

    report_file = Path("dead_code_analysis_detailed.json")
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2, default=str)

    print(f"\n💾 Detailed report saved to: {report_file}")


if __name__ == "__main__":
    main()
