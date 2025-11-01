"""Test runner for calendarbot_lite integration tests.

Remember to activate the venv before running: `. venv/bin/activate`
"""

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .utils import (
    cleanup_processes,
    compare_expected_actual,
    find_free_port,
    start_calendarbot_lite,
    start_simple_http_server,
    wait_for_whats_next,
)

logger = logging.getLogger(__name__)


class LiteTestResult:
    """Structured test result for a single test case."""
    
    def __init__(
        self,
        test_id: str,
        description: str,
        category: str,
        expected: Dict[str, Any],
        actual: Optional[Dict[str, Any]] = None,
        passed: bool = False,
        error_message: Optional[str] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
    ):
        """Initialize test result.
        
        Args:
            test_id: Unique identifier for the test
            description: Human-readable test description
            category: Test category (e.g., "single_meeting", "recurring")
            expected: Expected API response structure
            actual: Actual API response (None if test failed before API call)
            passed: Whether the test passed
            error_message: Error message if test failed
            diagnostics: Additional diagnostic information
        """
        self.test_id = test_id
        self.description = description
        self.category = category
        self.expected = expected
        self.actual = actual
        self.passed = passed
        self.error_message = error_message
        self.diagnostics = diagnostics or {}


class LiteTestRunner:
    """Main test runner for calendarbot_lite."""
    
    def __init__(
        self,
        specs_file: Path,
        fixtures_dir: Path,
        timeout: float = 60.0,
        lite_startup_timeout: float = 30.0,
    ):
        """Initialize test runner.
        
        Args:
            specs_file: Path to YAML test specifications file
            fixtures_dir: Directory containing ICS fixture files
            timeout: Overall test timeout in seconds
            lite_startup_timeout: Timeout for calendarbot_lite startup
            
        Raises:
            FileNotFoundError: If specs file or fixtures dir doesn't exist
        """
        if not specs_file.exists():
            raise FileNotFoundError(f"Test specs file not found: {specs_file}")
        if not fixtures_dir.exists():
            raise FileNotFoundError(f"Fixtures directory not found: {fixtures_dir}")
            
        self.specs_file = specs_file
        self.fixtures_dir = fixtures_dir
        self.timeout = timeout
        self.lite_startup_timeout = lite_startup_timeout
        
        # Load test specifications
        self.test_specs = self._load_test_specs()
        
    def _load_test_specs(self) -> List[Dict[str, Any]]:
        """Load test specifications from YAML file.
        
        Returns:
            List of test specification dictionaries
            
        Raises:
            ValueError: If specs file is invalid or malformed
        """
        try:
            with open(self.specs_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            if not isinstance(data, dict) or 'tests' not in data:
                raise ValueError("Specs file must contain 'tests' key at root level")
                
            tests = data['tests']
            if not isinstance(tests, list):
                raise ValueError("'tests' must be a list")
                
            # Validate each test spec has required fields
            for i, test in enumerate(tests):
                required_fields = ['test_id', 'description', 'category', 'ics_file', 'datetime_override', 'expected']
                for field in required_fields:
                    if field not in test:
                        raise ValueError(f"Test {i} missing required field: {field}")
                        
            logger.info("Loaded %d test specifications", len(tests))
            return tests
            
        except Exception as e:
            raise ValueError(f"Failed to load test specs from {self.specs_file}: {e}") from e
    
    def run_all_tests(self) -> List[LiteTestResult]:
        """Run all tests defined in the specs file.
        
        Returns:
            List of test results
        """
        results = []
        
        logger.info("Starting test run for %d tests", len(self.test_specs))
        
        for i, test_spec in enumerate(self.test_specs):
            logger.info(
                "Running test %d/%d: %s (%s)", 
                i + 1, len(self.test_specs), 
                test_spec['test_id'], test_spec['description']
            )
            
            result = self.run_single_test(test_spec)
            results.append(result)
            
            if result.passed:
                logger.info("Test %s PASSED", result.test_id)
            else:
                logger.warning("Test %s FAILED: %s", result.test_id, result.error_message)
        
        # Summary
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count
        
        logger.info(
            "Test run complete: %d/%d passed, %d failed", 
            passed_count, len(results), failed_count
        )
        
        return results
    
    def run_single_test(self, test_spec: Dict[str, Any]) -> LiteTestResult:
        """Run a single test case.
        
        Args:
            test_spec: Test specification dictionary
            
        Returns:
            Test result
        """
        test_id = test_spec['test_id']
        description = test_spec['description']
        category = test_spec['category']
        ics_file = test_spec['ics_file']
        datetime_override = test_spec['datetime_override']
        expected = test_spec['expected']
        
        http_server_process = None
        lite_process = None
        
        try:
            # Find free ports
            http_port = find_free_port()
            lite_port = find_free_port()
            
            logger.debug("Using HTTP port %d, lite port %d for test %s", http_port, lite_port, test_id)
            
            # Start HTTP server for ICS fixtures
            http_server_process = start_simple_http_server(self.fixtures_dir, http_port)
            
            # Prepare environment for calendarbot_lite
            ics_source_url = f"http://127.0.0.1:{http_port}/{ics_file}"
            env_overrides = {
                'CALENDARBOT_ICS_URL': ics_source_url,
                'CALENDARBOT_TEST_TIME': datetime_override,
                'CALENDARBOT_LOG_LEVEL': 'DEBUG',  # Enable debug logging for diagnostics
            }
            
            # Start calendarbot_lite
            lite_process = start_calendarbot_lite(lite_port, env_overrides)
            
            # Wait for calendarbot_lite to be ready and get API response
            try:
                actual_response = wait_for_whats_next(
                    lite_port, 
                    timeout=self.lite_startup_timeout,
                    retry_interval=1.0
                )
                
                # Compare expected vs actual
                passed, diff_struct = compare_expected_actual(expected, actual_response)
                
                # Gather diagnostics
                diagnostics = {
                    'http_port': http_port,
                    'lite_port': lite_port,
                    'ics_source_url': ics_source_url,
                    'datetime_override': datetime_override,
                    'comparison_diff': diff_struct,
                }
                
                return LiteTestResult(
                    test_id=test_id,
                    description=description,
                    category=category,
                    expected=expected,
                    actual=actual_response,
                    passed=passed,
                    error_message=None if passed else f"Comparison failed: {len(diff_struct['differences'])} differences",
                    diagnostics=diagnostics,
                )
                
            except Exception as e:
                # API call or comparison failed
                error_msg = f"Failed to get API response or compare results: {e}"
                logger.exception("Test %s failed during API interaction", test_id)
                
                return LiteTestResult(
                    test_id=test_id,
                    description=description,
                    category=category,
                    expected=expected,
                    actual=None,
                    passed=False,
                    error_message=error_msg,
                    diagnostics={
                        'http_port': http_port,
                        'lite_port': lite_port,
                        'ics_source_url': ics_source_url,
                        'datetime_override': datetime_override,
                        'exception': str(e),
                    },
                )
            
        except Exception as e:
            # Setup failed
            error_msg = f"Test setup failed: {e}"
            logger.exception("Test %s failed during setup", test_id)
            
            return LiteTestResult(
                test_id=test_id,
                description=description,
                category=category,
                expected=expected,
                actual=None,
                passed=False,
                error_message=error_msg,
                diagnostics={
                    'exception': str(e),
                },
            )
        
        finally:
            # Always clean up processes
            if http_server_process:
                cleanup_processes(http_server_process)
            if lite_process:
                cleanup_processes(lite_process)
    
    def generate_json_report(self, results: List[LiteTestResult]) -> Dict[str, Any]:
        """Generate JSON report from test results.
        
        Args:
            results: List of test results
            
        Returns:
            JSON-serializable report dictionary
        """
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count
        
        report = {
            'summary': {
                'total_tests': len(results),
                'passed': passed_count,
                'failed': failed_count,
                'success_rate': passed_count / len(results) if results else 0.0,
            },
            'tests': [
                {
                    'test_id': result.test_id,
                    'description': result.description,
                    'category': result.category,
                    'passed': result.passed,
                    'error_message': result.error_message,
                    'expected': result.expected,
                    'actual': result.actual,
                    'diagnostics': result.diagnostics,
                }
                for result in results
            ]
        }
        
        return report
    
    def generate_summary_string(self, results: List[LiteTestResult]) -> str:
        """Generate human-friendly summary string.
        
        Args:
            results: List of test results
            
        Returns:
            Multi-line summary string
        """
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count
        
        lines = [
            f"CalendarBot Lite Test Results",
            f"=============================",
            f"Total tests: {len(results)}",
            f"Passed: {passed_count}",
            f"Failed: {failed_count}",
            f"Success rate: {passed_count / len(results) * 100:.1f}%" if results else "No tests",
            f"",
        ]
        
        if failed_count > 0:
            lines.append("Failed tests:")
            for result in results:
                if not result.passed:
                    lines.append(f"  - {result.test_id}: {result.error_message}")
            lines.append("")
        
        lines.append("Test details by category:")
        categories = {}
        for result in results:
            if result.category not in categories:
                categories[result.category] = {'passed': 0, 'failed': 0}
            if result.passed:
                categories[result.category]['passed'] += 1
            else:
                categories[result.category]['failed'] += 1
        
        for category, counts in categories.items():
            total = counts['passed'] + counts['failed']
            lines.append(f"  {category}: {counts['passed']}/{total} passed")
        
        return "\n".join(lines)


def run_tests_from_specs_file(
    specs_file: Path,
    fixtures_dir: Path,
    output_json: Optional[Path] = None,
) -> List[LiteTestResult]:
    """Convenience function to run tests from a specs file.
    
    Args:
        specs_file: Path to YAML test specifications
        fixtures_dir: Directory containing ICS fixture files
        output_json: Optional path to write JSON report
        
    Returns:
        List of test results
    """
    runner = LiteTestRunner(specs_file, fixtures_dir)
    results = runner.run_all_tests()
    
    # Generate and log summary
    summary = runner.generate_summary_string(results)
    print(summary)
    
    # Write JSON report if requested
    if output_json:
        report = runner.generate_json_report(results)
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info("JSON report written to %s", output_json)
    
    return results


if __name__ == "__main__":
    """CLI entry point for running tests directly."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Run calendarbot_lite integration tests")
    parser.add_argument(
        "--specs", 
        type=Path, 
        default=Path(__file__).parent / "specs.yaml",
        help="Path to test specifications YAML file"
    )
    parser.add_argument(
        "--fixtures", 
        type=Path, 
        default=Path(__file__).parent.parent / "fixtures" / "ics",
        help="Path to ICS fixtures directory"
    )
    parser.add_argument(
        "--output-json", 
        type=Path,
        help="Path to write JSON test report"
    )
    parser.add_argument(
        "--log-level", 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s %(levelname)-7s %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    try:
        results = run_tests_from_specs_file(
            specs_file=args.specs,
            fixtures_dir=args.fixtures,
            output_json=args.output_json,
        )
        
        # Exit with failure code if any tests failed
        failed_count = sum(1 for r in results if not r.passed)
        sys.exit(failed_count)
        
    except Exception as e:
        logger.exception("Test runner failed")
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)