#!/usr/bin/env python3
"""
Unit tests for coverage failure parsing in suite manager.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.suites.suite_manager import TestSuiteManager


class TestCoverageFailureParsing(unittest.TestCase):
    """Test coverage failure detection and parsing."""

    def setUp(self):
        """Set up test manager."""
        self.manager = TestSuiteManager()

    def test_parse_coverage_failure_message(self):
        """Test parsing of coverage failure message."""
        output = """
        ============== FAILURES ==============
        FAIL Required test coverage of 85% not reached. Total coverage: 58.67%
        """

        coverage_failure = self.manager._parse_coverage_failure(output)

        self.assertIsNotNone(coverage_failure)
        self.assertEqual(coverage_failure["required"], 85.0)
        self.assertEqual(coverage_failure["actual"], 58.67)

    def test_parse_coverage_failure_no_match(self):
        """Test parsing when no coverage failure message exists."""
        output = """
        ============== test session starts ==============
        5 passed, 2 failed, 1 skipped
        """

        coverage_failure = self.manager._parse_coverage_failure(output)

        self.assertIsNone(coverage_failure)

    def test_parse_pytest_output_with_coverage_failure(self):
        """Test pytest output parsing when coverage fails but tests pass."""
        output = """
        ============== test session starts ==============
        3 passed in 0.45s
        FAIL Required test coverage of 85% not reached. Total coverage: 58.67%
        """

        test_count, passed, failed, skipped = self.manager._parse_pytest_output(output)

        # Should detect that tests passed but coverage failed
        self.assertEqual(test_count, 3)
        self.assertEqual(passed, 3)
        self.assertEqual(failed, 0)  # No test failures, only coverage failure
        self.assertEqual(skipped, 0)

    def test_parse_pytest_output_normal_failures(self):
        """Test pytest output parsing with normal test failures."""
        output = """
        ============== test session starts ==============
        3 passed, 2 failed, 1 skipped
        """

        test_count, passed, failed, skipped = self.manager._parse_pytest_output(output)

        self.assertEqual(test_count, 6)
        self.assertEqual(passed, 3)
        self.assertEqual(failed, 2)
        self.assertEqual(skipped, 1)

    def test_parse_pytest_output_no_match(self):
        """Test pytest output parsing when no pattern matches."""
        output = """
        Some random output
        No test results here
        """

        test_count, passed, failed, skipped = self.manager._parse_pytest_output(output)

        self.assertEqual(test_count, 0)
        self.assertEqual(passed, 0)
        self.assertEqual(failed, 0)
        self.assertEqual(skipped, 0)


if __name__ == "__main__":
    unittest.main()
