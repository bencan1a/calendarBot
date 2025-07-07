#!/usr/bin/env python3
"""
Advanced coverage analysis tools for CalendarBot.

This script provides detailed coverage analysis, trend tracking,
and hotspot identification for the CalendarBot test suite.
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class CoverageAnalyzer:
    """Advanced coverage analysis and reporting."""

    def __init__(self, data_dir: str = "coverage_data"):
        """Initialize coverage analyzer."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.db_path = self.data_dir / "coverage_history.db"
        self.init_database()

    def init_database(self):
        """Initialize SQLite database for coverage history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS coverage_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                test_type TEXT NOT NULL,
                line_coverage REAL NOT NULL,
                branch_coverage REAL NOT NULL,
                function_coverage REAL NOT NULL,
                total_lines INTEGER NOT NULL,
                covered_lines INTEGER NOT NULL,
                total_branches INTEGER NOT NULL,
                covered_branches INTEGER NOT NULL,
                total_functions INTEGER NOT NULL,
                covered_functions INTEGER NOT NULL,
                git_commit TEXT,
                notes TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_coverage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                filename TEXT NOT NULL,
                line_coverage REAL NOT NULL,
                branch_coverage REAL NOT NULL,
                lines_covered INTEGER NOT NULL,
                lines_total INTEGER NOT NULL,
                branches_covered INTEGER NOT NULL,
                branches_total INTEGER NOT NULL,
                missing_lines TEXT,
                FOREIGN KEY (run_id) REFERENCES coverage_runs (id)
            )
        """
        )

        conn.commit()
        conn.close()

    def analyze_coverage_data(self, coverage_file: str = "coverage.json") -> Dict[str, Any]:
        """Analyze coverage data from JSON report."""
        if not Path(coverage_file).exists():
            raise FileNotFoundError(f"Coverage file not found: {coverage_file}")

        with open(coverage_file, "r") as f:
            data = json.load(f)

        analysis = {
            "summary": data["totals"],
            "files": {},
            "hotspots": {"highest": [], "lowest": []},
            "missing_coverage": [],
            "critical_files": [],
        }

        # Analyze per-file coverage
        for filename, file_data in data["files"].items():
            if filename.startswith("calendarbot/"):
                coverage_pct = file_data["summary"]["percent_covered"]
                missing_lines = file_data["missing_lines"]

                analysis["files"][filename] = {
                    "coverage": coverage_pct,
                    "lines_total": file_data["summary"]["num_statements"],
                    "lines_covered": file_data["summary"]["covered_lines"],
                    "missing_lines": missing_lines,
                    "excluded_lines": file_data["excluded_lines"],
                }

                # Identify hotspots
                if coverage_pct >= 90:
                    analysis["hotspots"]["highest"].append((filename, coverage_pct))
                elif coverage_pct < 70:
                    analysis["hotspots"]["lowest"].append((filename, coverage_pct))

                # Identify files with significant missing coverage
                if missing_lines and len(missing_lines) > 10:
                    analysis["missing_coverage"].append(
                        {"file": filename, "missing_lines": missing_lines, "coverage": coverage_pct}
                    )

                # Critical files (core functionality)
                if any(critical in filename for critical in ["main", "core", "manager", "server"]):
                    analysis["critical_files"].append(
                        {"file": filename, "coverage": coverage_pct, "critical": coverage_pct < 80}
                    )

        # Sort hotspots
        analysis["hotspots"]["highest"].sort(key=lambda x: x[1], reverse=True)
        analysis["hotspots"]["lowest"].sort(key=lambda x: x[1])

        return analysis

    def store_coverage_run(
        self, analysis: Dict[str, Any], test_type: str = "all", notes: str = ""
    ) -> int:
        """Store coverage run in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get git commit if available
        git_commit = self._get_git_commit()

        # Extract summary data
        summary = analysis["summary"]

        cursor.execute(
            """
            INSERT INTO coverage_runs
            (timestamp, test_type, line_coverage, branch_coverage, function_coverage,
             total_lines, covered_lines, total_branches, covered_branches,
             total_functions, covered_functions, git_commit, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                datetime.now().isoformat(),
                test_type,
                summary.get("percent_covered", 0),
                summary.get("percent_covered_display", 0),  # Branch coverage if available
                0,  # Function coverage - calculate from data
                summary.get("num_statements", 0),
                summary.get("covered_lines", 0),
                summary.get("num_branches", 0),
                summary.get("covered_branches", 0),
                0,  # Total functions
                0,  # Covered functions
                git_commit,
                notes,
            ),
        )

        run_id = cursor.lastrowid

        # Store per-file data
        for filename, file_data in analysis["files"].items():
            cursor.execute(
                """
                INSERT INTO file_coverage
                (run_id, filename, line_coverage, branch_coverage,
                 lines_covered, lines_total, branches_covered, branches_total,
                 missing_lines)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    run_id,
                    filename,
                    file_data["coverage"],
                    0,  # Branch coverage per file
                    file_data["lines_covered"],
                    file_data["lines_total"],
                    0,  # Branches covered
                    0,  # Branches total
                    json.dumps(file_data["missing_lines"]),
                ),
            )

        conn.commit()
        conn.close()
        return run_id

    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=project_root
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except:
            return None

    def generate_trend_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate coverage trend report."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=days)

        cursor.execute(
            """
            SELECT timestamp, test_type, line_coverage, branch_coverage,
                   function_coverage, git_commit
            FROM coverage_runs
            WHERE timestamp > ?
            ORDER BY timestamp
        """,
            (cutoff_date.isoformat(),),
        )

        runs = cursor.fetchall()
        conn.close()

        if not runs:
            return {"error": "No coverage data found for the specified period"}

        # Calculate trends
        trend_data = []
        for run in runs:
            trend_data.append(
                {
                    "timestamp": run[0],
                    "test_type": run[1],
                    "line_coverage": run[2],
                    "branch_coverage": run[3],
                    "function_coverage": run[4],
                    "git_commit": run[5],
                }
            )

        # Calculate trend direction
        recent_coverage = trend_data[-5:] if len(trend_data) >= 5 else trend_data
        avg_recent = sum(r["line_coverage"] for r in recent_coverage) / len(recent_coverage)

        older_coverage = trend_data[-10:-5] if len(trend_data) >= 10 else trend_data[:-5]
        avg_older = (
            sum(r["line_coverage"] for r in older_coverage) / len(older_coverage)
            if older_coverage
            else avg_recent
        )

        trend_direction = (
            "improving"
            if avg_recent > avg_older
            else "declining" if avg_recent < avg_older else "stable"
        )

        return {
            "period_days": days,
            "total_runs": len(runs),
            "trend_data": trend_data,
            "trend_direction": trend_direction,
            "coverage_change": avg_recent - avg_older,
            "current_coverage": trend_data[-1]["line_coverage"] if trend_data else 0,
            "best_coverage": max(r["line_coverage"] for r in trend_data),
            "worst_coverage": min(r["line_coverage"] for r in trend_data),
        }

    def identify_missing_coverage(
        self, analysis: Dict[str, Any], threshold: float = 80.0
    ) -> List[Dict[str, Any]]:
        """Identify files and areas with missing coverage."""
        missing_coverage = []

        for filename, file_data in analysis["files"].items():
            if file_data["coverage"] < threshold:
                missing_lines = file_data["missing_lines"]

                # Group consecutive missing lines
                line_groups = []
                if missing_lines:
                    current_group = [missing_lines[0]]
                    for line in missing_lines[1:]:
                        if line == current_group[-1] + 1:
                            current_group.append(line)
                        else:
                            line_groups.append(current_group)
                            current_group = [line]
                    line_groups.append(current_group)

                missing_coverage.append(
                    {
                        "file": filename,
                        "coverage": file_data["coverage"],
                        "lines_missing": len(missing_lines),
                        "lines_total": file_data["lines_total"],
                        "missing_line_groups": line_groups,
                        "priority": "high" if file_data["coverage"] < 60 else "medium",
                    }
                )

        # Sort by priority and coverage percentage
        missing_coverage.sort(key=lambda x: (x["priority"] == "high", -x["coverage"]))

        return missing_coverage

    def generate_coverage_report(self, output_format: str = "text") -> str:
        """Generate comprehensive coverage report."""
        if not Path("coverage.json").exists():
            return "Error: No coverage data found. Run tests with coverage first."

        analysis = self.analyze_coverage_data()

        if output_format == "json":
            return json.dumps(analysis, indent=2)

        # Text report
        report = []
        report.append("=" * 80)
        report.append("CALENDARBOT COVERAGE ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Summary
        summary = analysis["summary"]
        report.append("COVERAGE SUMMARY")
        report.append("-" * 40)
        report.append(f"Line Coverage:     {summary.get('percent_covered', 0):.2f}%")
        report.append(f"Total Lines:       {summary.get('num_statements', 0)}")
        report.append(f"Covered Lines:     {summary.get('covered_lines', 0)}")
        report.append(f"Missing Lines:     {summary.get('missing_lines', 0)}")
        report.append("")

        # Coverage hotspots
        report.append("COVERAGE HOTSPOTS")
        report.append("-" * 40)
        report.append("Highest Coverage:")
        for filename, coverage in analysis["hotspots"]["highest"][:5]:
            report.append(f"  {filename:<50} {coverage:>6.2f}%")

        report.append("\nLowest Coverage:")
        for filename, coverage in analysis["hotspots"]["lowest"][:5]:
            status = "❌" if coverage < 60 else "⚠️"
            report.append(f"  {status} {filename:<48} {coverage:>6.2f}%")
        report.append("")

        # Missing coverage details
        missing = self.identify_missing_coverage(analysis)
        if missing:
            report.append("FILES NEEDING ATTENTION")
            report.append("-" * 40)
            for item in missing[:10]:
                priority_icon = "🔴" if item["priority"] == "high" else "🟡"
                report.append(f"{priority_icon} {item['file']}")
                report.append(
                    f"    Coverage: {item['coverage']:.2f}% ({item['lines_missing']} lines missing)"
                )
                if item["missing_line_groups"]:
                    groups_str = ", ".join(
                        [
                            f"{g[0]}-{g[-1]}" if len(g) > 1 else str(g[0])
                            for g in item["missing_line_groups"][:3]
                        ]
                    )
                    report.append(f"    Missing lines: {groups_str}")
                report.append("")

        # Critical files
        critical_files = [f for f in analysis["critical_files"] if f["critical"]]
        if critical_files:
            report.append("CRITICAL FILES BELOW THRESHOLD")
            report.append("-" * 40)
            for item in critical_files:
                report.append(f"⚠️  {item['file']:<50} {item['coverage']:>6.2f}%")
            report.append("")

        # Recommendations
        report.append("RECOMMENDATIONS")
        report.append("-" * 40)
        if summary.get("percent_covered", 0) < 80:
            report.append("• Overall coverage is below 80% target")
        if analysis["hotspots"]["lowest"]:
            report.append("• Focus on files with coverage below 70%")
        if critical_files:
            report.append("• Prioritize testing critical files")
        if analysis["missing_coverage"]:
            report.append("• Add tests for identified missing coverage areas")

        return "\n".join(report)


def main():
    """Main entry point for coverage analysis."""
    parser = argparse.ArgumentParser(
        description="Advanced coverage analysis for CalendarBot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python coverage_analysis.py --analyze                    # Analyze current coverage
  python coverage_analysis.py --report --format json      # Generate JSON report
  python coverage_analysis.py --trends --days 14          # Show 14-day trends
  python coverage_analysis.py --missing --threshold 75    # Find files below 75%
  python coverage_analysis.py --store --type unit         # Store coverage run
        """,
    )

    parser.add_argument("--analyze", action="store_true", help="Analyze current coverage data")
    parser.add_argument(
        "--report", action="store_true", help="Generate comprehensive coverage report"
    )
    parser.add_argument("--trends", action="store_true", help="Show coverage trends")
    parser.add_argument("--missing", action="store_true", help="Identify missing coverage areas")
    parser.add_argument(
        "--store", action="store_true", help="Store current coverage run in database"
    )

    parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format for reports"
    )
    parser.add_argument("--days", type=int, default=30, help="Number of days for trend analysis")
    parser.add_argument(
        "--threshold", type=float, default=80.0, help="Coverage threshold for missing analysis"
    )
    parser.add_argument("--type", default="all", help="Test type for storing runs")
    parser.add_argument("--notes", default="", help="Notes for coverage run")

    args = parser.parse_args()

    analyzer = CoverageAnalyzer()

    try:
        if args.analyze or args.report:
            report = analyzer.generate_coverage_report(args.format)
            print(report)

        elif args.trends:
            trends = analyzer.generate_trend_report(args.days)
            if "error" in trends:
                print(f"Error: {trends['error']}")
            else:
                print(f"Coverage Trends ({args.days} days)")
                print(f"Trend: {trends['trend_direction']}")
                print(f"Current: {trends['current_coverage']:.2f}%")
                print(f"Change: {trends['coverage_change']:+.2f}%")
                print(f"Best: {trends['best_coverage']:.2f}%")
                print(f"Worst: {trends['worst_coverage']:.2f}%")

        elif args.missing:
            if not Path("coverage.json").exists():
                print("Error: No coverage data found. Run tests with coverage first.")
                return 1

            analysis = analyzer.analyze_coverage_data()
            missing = analyzer.identify_missing_coverage(analysis, args.threshold)

            print(f"Files below {args.threshold}% coverage:")
            for item in missing:
                priority_icon = "🔴" if item["priority"] == "high" else "🟡"
                print(f"{priority_icon} {item['file']:<50} {item['coverage']:>6.2f}%")

        elif args.store:
            if not Path("coverage.json").exists():
                print("Error: No coverage data found. Run tests with coverage first.")
                return 1

            analysis = analyzer.analyze_coverage_data()
            run_id = analyzer.store_coverage_run(analysis, args.type, args.notes)
            print(f"Coverage run stored with ID: {run_id}")

        else:
            parser.print_help()

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
