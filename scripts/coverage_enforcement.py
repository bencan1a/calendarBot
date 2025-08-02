#!/usr/bin/env python3
"""
Coverage enforcement script for CalendarBot CI/CD pipeline.

This script enforces coverage thresholds and provides detailed reporting
for failed coverage checks, helping developers understand what needs testing.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def load_coverage_data() -> Optional[dict]:
    """Load coverage data from coverage.json."""
    coverage_file = Path("coverage.json")
    if not coverage_file.exists():
        print("❌ Coverage data not found. Run tests with coverage first.")
        return None

    try:
        with open(coverage_file) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"❌ Error loading coverage data: {e}")
        return None


def analyze_coverage(coverage_data: dict, threshold: float) -> tuple[bool, dict]:
    """
    Analyze coverage data against threshold.

    Returns:
        (passes_threshold, analysis_details)
    """
    totals = coverage_data.get("totals", {})
    line_coverage = totals.get("percent_covered", 0.0)
    branch_coverage = totals.get("percent_covered_display", line_coverage)

    # Extract detailed file coverage
    files = coverage_data.get("files", {})
    low_coverage_files = []

    for filepath, file_data in files.items():
        file_coverage = file_data.get("summary", {}).get("percent_covered", 0.0)
        if file_coverage < threshold:
            missing_lines = file_data.get("missing_lines", [])
            low_coverage_files.append(
                {
                    "file": filepath,
                    "coverage": file_coverage,
                    "missing_lines": missing_lines,
                    "total_lines": file_data.get("summary", {}).get("num_statements", 0),
                }
            )

    analysis = {
        "line_coverage": line_coverage,
        "branch_coverage": branch_coverage,
        "threshold": threshold,
        "passes_threshold": line_coverage >= threshold,
        "low_coverage_files": sorted(low_coverage_files, key=lambda x: x["coverage"]),
        "total_files": len(files),
        "files_below_threshold": len(low_coverage_files),
    }

    return analysis["passes_threshold"], analysis


def generate_coverage_report(analysis: dict) -> str:
    """Generate detailed coverage report."""
    report_lines = []

    # Header
    report_lines.append("=" * 60)
    report_lines.append("COVERAGE ENFORCEMENT REPORT")
    report_lines.append("=" * 60)

    # Overall results
    status = "✅ PASS" if analysis["passes_threshold"] else "❌ FAIL"
    report_lines.append(f"\nStatus: {status}")
    report_lines.append(f"Line Coverage: {analysis['line_coverage']:.2f}%")
    report_lines.append(f"Threshold: {analysis['threshold']:.1f}%")
    report_lines.append(f"Files Analyzed: {analysis['total_files']}")
    report_lines.append(f"Files Below Threshold: {analysis['files_below_threshold']}")

    # Detailed file analysis
    if analysis["low_coverage_files"]:
        report_lines.append(f"\n{'-' * 40}")
        report_lines.append("FILES REQUIRING ATTENTION")
        report_lines.append(f"{'-' * 40}")

        for file_info in analysis["low_coverage_files"][:10]:  # Show top 10
            report_lines.append(f"\n📄 {file_info['file']}")
            report_lines.append(f"   Coverage: {file_info['coverage']:.1f}%")
            report_lines.append(f"   Total Lines: {file_info['total_lines']}")

            if file_info["missing_lines"]:
                missing_str = ", ".join(map(str, file_info["missing_lines"][:10]))
                if len(file_info["missing_lines"]) > 10:
                    missing_str += f" ... (+{len(file_info['missing_lines']) - 10} more)"
                report_lines.append(f"   Missing Lines: {missing_str}")

    # Recommendations
    report_lines.append(f"\n{'-' * 40}")
    report_lines.append("RECOMMENDATIONS")
    report_lines.append(f"{'-' * 40}")

    if analysis["passes_threshold"]:
        report_lines.append("✅ Coverage threshold met. Great job!")
        if analysis["files_below_threshold"] > 0:
            report_lines.append(
                f"💡 Consider improving coverage for {analysis['files_below_threshold']} files"
            )
    else:
        coverage_gap = analysis["threshold"] - analysis["line_coverage"]
        report_lines.append(f"❌ Coverage is {coverage_gap:.1f}% below threshold")
        report_lines.append("🎯 Focus on testing the files listed above")
        report_lines.append("📝 Prioritize files with the lowest coverage percentages")
        report_lines.append("🔍 Review missing lines to identify untested code paths")

    return "\n".join(report_lines)


def check_coverage_trend(current_coverage: float) -> dict:
    """Check coverage trend against previous runs."""
    trend_file = Path("coverage_trend.json")

    if not trend_file.exists():
        # First run, create baseline
        trend_data = {"history": [current_coverage]}
        with open(trend_file, "w") as f:
            json.dump(trend_data, f)
        return {"trend": "baseline", "change": 0.0}

    try:
        with open(trend_file) as f:
            trend_data = json.load(f)

        history = trend_data.get("history", [])
        if history:
            previous_coverage = history[-1]
            change = current_coverage - previous_coverage

            # Update history (keep last 10 runs)
            history.append(current_coverage)
            trend_data["history"] = history[-10:]

            with open(trend_file, "w") as f:
                json.dump(trend_data, f)

            if change > 1.0:
                trend = "improving"
            elif change < -1.0:
                trend = "declining"
            else:
                trend = "stable"

            return {"trend": trend, "change": change, "previous": previous_coverage}

    except (OSError, json.JSONDecodeError):
        pass

    return {"trend": "unknown", "change": 0.0}


def main():
    """Main coverage enforcement entry point."""
    parser = argparse.ArgumentParser(description="Coverage Enforcement for CalendarBot")
    parser.add_argument(
        "--threshold", type=float, default=80.0, help="Coverage threshold percentage (default: 80)"
    )
    parser.add_argument(
        "--strict", action="store_true", help="Strict mode: fail on any coverage decrease"
    )
    parser.add_argument(
        "--report-only", action="store_true", help="Generate report without enforcing threshold"
    )
    parser.add_argument("--trend", action="store_true", help="Include coverage trend analysis")

    args = parser.parse_args()

    # Load and analyze coverage data
    coverage_data = load_coverage_data()
    if not coverage_data:
        sys.exit(1)

    passes_threshold, analysis = analyze_coverage(coverage_data, args.threshold)

    # Generate and display report
    report = generate_coverage_report(analysis)
    print(report)

    # Check trend if requested
    if args.trend:
        trend_info = check_coverage_trend(analysis["line_coverage"])
        print(f"\n{'-' * 40}")
        print("COVERAGE TREND")
        print(f"{'-' * 40}")
        print(f"Trend: {trend_info['trend']}")
        if "change" in trend_info:
            print(f"Change: {trend_info['change']:+.2f}%")
        if "previous" in trend_info:
            print(f"Previous: {trend_info['previous']:.2f}%")

    # Determine exit code
    if args.report_only:
        sys.exit(0)

    if args.strict and args.trend:
        trend_info = check_coverage_trend(analysis["line_coverage"])
        if trend_info.get("change", 0) < 0:
            print("\n❌ STRICT MODE: Coverage decreased from previous run")
            sys.exit(1)

    sys.exit(0 if passes_threshold else 1)


if __name__ == "__main__":
    main()
