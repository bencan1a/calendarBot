#!/usr/bin/env python3
"""
Unit tests for the coverage analysis tool.

This module tests the CoverageAnalyzer class and its methods
to ensure proper functionality of coverage tracking and reporting.
"""

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.coverage_analysis import CoverageAnalyzer


class TestCoverageAnalyzer(unittest.TestCase):
    """Test cases for CoverageAnalyzer class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.analyzer = CoverageAnalyzer(data_dir=self.temp_dir)

        # Sample coverage data for testing
        self.sample_coverage_data = {
            "meta": {
                "version": "7.3.0",
                "timestamp": "2024-01-01T00:00:00",
                "branch_coverage": True,
                "show_contexts": False,
            },
            "files": {
                "calendarbot/main.py": {
                    "executed_lines": [1, 2, 3, 5, 8, 10],
                    "summary": {
                        "covered_lines": 6,
                        "num_statements": 10,
                        "percent_covered": 60.0,
                        "percent_covered_display": "60",
                    },
                    "missing_lines": [4, 6, 7, 9],
                    "excluded_lines": [],
                },
                "calendarbot/utils/helpers.py": {
                    "executed_lines": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                    "summary": {
                        "covered_lines": 10,
                        "num_statements": 10,
                        "percent_covered": 100.0,
                        "percent_covered_display": "100",
                    },
                    "missing_lines": [],
                    "excluded_lines": [],
                },
                "calendarbot/web/server.py": {
                    "executed_lines": [1, 2, 3, 4],
                    "summary": {
                        "covered_lines": 4,
                        "num_statements": 8,
                        "percent_covered": 50.0,
                        "percent_covered_display": "50",
                    },
                    "missing_lines": [5, 6, 7, 8],
                    "excluded_lines": [],
                },
            },
            "totals": {
                "covered_lines": 20,
                "num_statements": 28,
                "percent_covered": 71.43,
                "percent_covered_display": "71",
                "covered_branches": 0,
                "num_branches": 0,
                "missing_lines": 8,
            },
        }

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_database(self):
        """Test database initialization."""
        # Check if database file exists
        self.assertTrue(self.analyzer.db_path.exists())

        # Check if tables are created
        conn = sqlite3.connect(self.analyzer.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        self.assertIn("coverage_runs", tables)
        self.assertIn("file_coverage", tables)

        conn.close()

    def test_analyze_coverage_data(self):
        """Test coverage data analysis."""
        # Create temporary coverage file
        coverage_file = Path(self.temp_dir) / "test_coverage.json"
        with open(coverage_file, "w") as f:
            json.dump(self.sample_coverage_data, f)

        # Analyze the data
        analysis = self.analyzer.analyze_coverage_data(str(coverage_file))

        # Verify analysis structure
        self.assertIn("summary", analysis)
        self.assertIn("files", analysis)
        self.assertIn("hotspots", analysis)
        self.assertIn("missing_coverage", analysis)
        self.assertIn("critical_files", analysis)

        # Verify summary data
        self.assertEqual(analysis["summary"]["percent_covered"], 71.43)

        # Verify file analysis
        self.assertEqual(len(analysis["files"]), 3)
        self.assertIn("calendarbot/main.py", analysis["files"])

        # Verify hotspots
        self.assertTrue(len(analysis["hotspots"]["highest"]) > 0)
        self.assertTrue(len(analysis["hotspots"]["lowest"]) > 0)

    def test_identify_missing_coverage(self):
        """Test missing coverage identification."""
        # Create temporary coverage file
        coverage_file = Path(self.temp_dir) / "test_coverage.json"
        with open(coverage_file, "w") as f:
            json.dump(self.sample_coverage_data, f)

        analysis = self.analyzer.analyze_coverage_data(str(coverage_file))
        missing = self.analyzer.identify_missing_coverage(analysis, threshold=70.0)

        # Should identify files below 70% coverage
        self.assertTrue(len(missing) > 0)

        # Check that files below threshold are identified
        missing_files = [item["file"] for item in missing]
        self.assertIn("calendarbot/main.py", missing_files)  # 60% coverage
        self.assertIn("calendarbot/web/server.py", missing_files)  # 50% coverage

        # Check priority assignment
        for item in missing:
            if item["coverage"] < 60:
                self.assertEqual(item["priority"], "high")
            else:
                self.assertEqual(item["priority"], "medium")

    def test_store_coverage_run(self):
        """Test storing coverage runs in database."""
        # Create temporary coverage file
        coverage_file = Path(self.temp_dir) / "test_coverage.json"
        with open(coverage_file, "w") as f:
            json.dump(self.sample_coverage_data, f)

        analysis = self.analyzer.analyze_coverage_data(str(coverage_file))
        run_id = self.analyzer.store_coverage_run(analysis, "unit", "Test run")

        # Verify run was stored
        self.assertIsInstance(run_id, int)
        self.assertGreater(run_id, 0)

        # Verify data in database
        conn = sqlite3.connect(self.analyzer.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM coverage_runs WHERE id = ?", (run_id,))
        run_data = cursor.fetchone()
        self.assertIsNotNone(run_data)

        cursor.execute("SELECT * FROM file_coverage WHERE run_id = ?", (run_id,))
        file_data = cursor.fetchall()
        self.assertEqual(len(file_data), 3)  # Three files in sample data

        conn.close()

    @patch("subprocess.run")
    def test_get_git_commit(self, mock_subprocess):
        """Test git commit hash retrieval."""
        # Mock successful git command
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc123def456\n"
        mock_subprocess.return_value = mock_result

        commit = self.analyzer._get_git_commit()
        self.assertEqual(commit, "abc123def456")

        # Mock failed git command
        mock_result.returncode = 1
        commit = self.analyzer._get_git_commit()
        self.assertIsNone(commit)

    def test_generate_trend_report_no_data(self):
        """Test trend report generation with no data."""
        trends = self.analyzer.generate_trend_report(days=7)
        self.assertIn("error", trends)

    def test_generate_trend_report_with_data(self):
        """Test trend report generation with sample data."""
        # Create temporary coverage file and store some runs
        coverage_file = Path(self.temp_dir) / "test_coverage.json"
        with open(coverage_file, "w") as f:
            json.dump(self.sample_coverage_data, f)

        analysis = self.analyzer.analyze_coverage_data(str(coverage_file))

        # Store multiple runs
        for i in range(5):
            self.analyzer.store_coverage_run(analysis, f"test_{i}", f"Test run {i}")

        trends = self.analyzer.generate_trend_report(days=7)

        # Verify trend report structure
        self.assertIn("period_days", trends)
        self.assertIn("total_runs", trends)
        self.assertIn("trend_data", trends)
        self.assertIn("trend_direction", trends)
        self.assertIn("current_coverage", trends)

        self.assertEqual(trends["total_runs"], 5)
        self.assertEqual(len(trends["trend_data"]), 5)

    def test_generate_coverage_report_text(self):
        """Test text coverage report generation."""
        # Create temporary coverage file
        coverage_file = Path(self.temp_dir) / "test_coverage.json"
        with open(coverage_file, "w") as f:
            json.dump(self.sample_coverage_data, f)

        # Create properly analyzed data structure that generate_coverage_report expects
        analyzed_data = {
            "summary": self.sample_coverage_data["totals"],
            "files": {},
            "hotspots": {"highest": [], "lowest": []},
            "missing_coverage": [],
            "critical_files": [],
        }

        # Mock the coverage file path
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(self.analyzer, "analyze_coverage_data", return_value=analyzed_data):
                report = self.analyzer.generate_coverage_report("text")

        # Verify report contains expected sections
        self.assertIn("CALENDARBOT COVERAGE ANALYSIS REPORT", report)
        self.assertIn("COVERAGE SUMMARY", report)
        self.assertIn("COVERAGE HOTSPOTS", report)
        self.assertIn("RECOMMENDATIONS", report)

    def test_generate_coverage_report_json(self):
        """Test JSON coverage report generation."""
        # Create temporary coverage file
        coverage_file = Path(self.temp_dir) / "test_coverage.json"
        with open(coverage_file, "w") as f:
            json.dump(self.sample_coverage_data, f)

        # Mock the coverage file path
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                self.analyzer, "analyze_coverage_data", return_value=self.sample_coverage_data
            ):
                report = self.analyzer.generate_coverage_report("json")

        # Verify JSON format
        try:
            json.loads(report)
            json_valid = True
        except json.JSONDecodeError:
            json_valid = False

        self.assertTrue(json_valid)

    def test_generate_coverage_report_no_data(self):
        """Test coverage report generation with no coverage data."""
        with patch("pathlib.Path.exists", return_value=False):
            report = self.analyzer.generate_coverage_report("text")
            self.assertIn("Error: No coverage data found", report)


class TestCoverageAnalysisMain(unittest.TestCase):
    """Test cases for the main function and CLI interface."""

    @patch("sys.argv", ["coverage_analysis.py", "--analyze"])
    @patch("pathlib.Path.exists", return_value=True)
    def test_main_analyze(self, mock_exists):
        """Test main function with analyze argument."""
        with patch("tests.coverage_analysis.CoverageAnalyzer") as mock_analyzer:
            mock_instance = MagicMock()
            mock_analyzer.return_value = mock_instance
            mock_instance.generate_coverage_report.return_value = "Test report"

            from tests.coverage_analysis import main

            with patch("builtins.print") as mock_print:
                result = main()
                mock_print.assert_called_with("Test report")
                self.assertEqual(result, 0)

    @patch("sys.argv", ["coverage_analysis.py", "--missing", "--threshold", "75"])
    @patch("pathlib.Path.exists", return_value=True)
    def test_main_missing(self, mock_exists):
        """Test main function with missing coverage argument."""
        sample_analysis = {"files": {"test.py": {"coverage": 60}}}

        with patch("tests.coverage_analysis.CoverageAnalyzer") as mock_analyzer:
            mock_instance = MagicMock()
            mock_analyzer.return_value = mock_instance
            mock_instance.analyze_coverage_data.return_value = sample_analysis
            mock_instance.identify_missing_coverage.return_value = [
                {"file": "test.py", "coverage": 60, "priority": "medium"}
            ]

            from tests.coverage_analysis import main

            with patch("builtins.print") as mock_print:
                result = main()
                self.assertEqual(result, 0)
                # Verify that missing coverage info was printed
                mock_print.assert_any_call("Files below 75.0% coverage:")

    @patch("sys.argv", ["coverage_analysis.py", "--store", "--type", "unit"])
    @patch("pathlib.Path.exists", return_value=True)
    def test_main_store(self, mock_exists):
        """Test main function with store argument."""
        sample_analysis = {"summary": {"percent_covered": 85}}

        with patch("tests.coverage_analysis.CoverageAnalyzer") as mock_analyzer:
            mock_instance = MagicMock()
            mock_analyzer.return_value = mock_instance
            mock_instance.analyze_coverage_data.return_value = sample_analysis
            mock_instance.store_coverage_run.return_value = 123

            from tests.coverage_analysis import main

            with patch("builtins.print") as mock_print:
                result = main()
                self.assertEqual(result, 0)
                mock_print.assert_called_with("Coverage run stored with ID: 123")


if __name__ == "__main__":
    unittest.main()
