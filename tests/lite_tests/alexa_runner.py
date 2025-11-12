"""Test runner for calendarbot_lite Alexa API integration tests.

Extends the core LiteTestRunner to support Alexa-specific validation including
SSML output, speech text patterns, and flexible response matching.

Remember to activate the venv before running: `. venv/bin/activate`
"""

import json
import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import urlopen

import yaml

from .utils import (
    cleanup_processes,
    find_free_port,
    start_calendarbot_lite,
    start_simple_http_server,
)

logger = logging.getLogger(__name__)


class AlexaTestResult:
    """Structured test result for a single Alexa API test case."""

    def __init__(
        self,
        test_id: str,
        description: str,
        category: str,
        suite: str,
        endpoint: str,
        expected: Dict[str, Any],
        actual: Optional[Dict[str, Any]] = None,
        passed: bool = False,
        error_message: Optional[str] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
    ):
        """Initialize Alexa test result.

        Args:
            test_id: Unique identifier for the test
            description: Human-readable test description
            category: Test category (launch_summary, done_for_day, morning_summary)
            suite: Test suite (smoke, comprehensive)
            endpoint: Alexa API endpoint tested
            expected: Expected API response structure
            actual: Actual API response (None if test failed before API call)
            passed: Whether the test passed
            error_message: Error message if test failed
            diagnostics: Additional diagnostic information
        """
        self.test_id = test_id
        self.description = description
        self.category = category
        self.suite = suite
        self.endpoint = endpoint
        self.expected = expected
        self.actual = actual
        self.passed = passed
        self.error_message = error_message
        self.diagnostics = diagnostics or {}


class AlexaTestRunner:
    """Test runner for Alexa API endpoints."""

    def __init__(
        self,
        specs_file: Path,
        fixtures_dir: Path,
        timeout: float = 60.0,
        lite_startup_timeout: float = 30.0,
        suite_filter: Optional[str] = None,
    ):
        """Initialize Alexa test runner.

        Args:
            specs_file: Path to YAML test specifications file
            fixtures_dir: Directory containing ICS fixture files
            timeout: Overall test timeout in seconds
            lite_startup_timeout: Timeout for calendarbot_lite startup
            suite_filter: Optional filter for test suite ('smoke', 'comprehensive', or None for all)

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
        self.suite_filter = suite_filter

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
                required_fields = [
                    'test_id', 'description', 'category', 'suite', 'endpoint',
                    'ics_file', 'datetime_override', 'expected'
                ]
                for field in required_fields:
                    if field not in test:
                        raise ValueError(f"Test {i} missing required field: {field}")

            # Apply suite filter if specified
            if self.suite_filter:
                tests = [t for t in tests if t.get('suite') == self.suite_filter]
                logger.info("Filtered to %d tests in suite '%s'", len(tests), self.suite_filter)

            logger.info("Loaded %d test specifications", len(tests))
            return tests

        except Exception as e:
            raise ValueError(f"Failed to load test specs from {self.specs_file}: {e}") from e

    def run_all_tests(self) -> List[AlexaTestResult]:
        """Run all tests defined in the specs file.

        Returns:
            List of test results
        """
        results = []

        logger.info("Starting Alexa API test run for %d tests", len(self.test_specs))

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

    def run_single_test(self, test_spec: Dict[str, Any]) -> AlexaTestResult:
        """Run a single Alexa API test case.

        Args:
            test_spec: Test specification dictionary

        Returns:
            Test result
        """
        test_id = test_spec['test_id']
        description = test_spec['description']
        category = test_spec['category']
        suite = test_spec['suite']
        endpoint = test_spec['endpoint']
        ics_file = test_spec['ics_file']
        datetime_override = test_spec['datetime_override']
        expected = test_spec['expected']
        query_params = test_spec.get('query_params', {})

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
                'CALENDARBOT_LOG_LEVEL': 'DEBUG',
                'CALENDARBOT_ALEXA_BEARER_TOKEN': '',  # Disable auth for tests
            }

            # Start calendarbot_lite
            lite_process = start_calendarbot_lite(lite_port, env_overrides)

            # Wait for calendarbot_lite to be ready and get API response
            try:
                actual_response = self._wait_for_alexa_endpoint(
                    lite_port,
                    endpoint,
                    query_params,
                    timeout=self.lite_startup_timeout,
                    retry_interval=1.0
                )

                # Validate response using Alexa-specific validation
                passed, validation_details = self._validate_alexa_response(
                    expected,
                    actual_response,
                    test_spec
                )

                # Gather diagnostics
                diagnostics = {
                    'http_port': http_port,
                    'lite_port': lite_port,
                    'ics_source_url': ics_source_url,
                    'datetime_override': datetime_override,
                    'endpoint': endpoint,
                    'query_params': query_params,
                    'validation_details': validation_details,
                }

                return AlexaTestResult(
                    test_id=test_id,
                    description=description,
                    category=category,
                    suite=suite,
                    endpoint=endpoint,
                    expected=expected,
                    actual=actual_response,
                    passed=passed,
                    error_message=None if passed else self._format_validation_errors(validation_details),
                    diagnostics=diagnostics,
                )

            except Exception as e:
                # API call or validation failed
                error_msg = f"Failed to get API response or validate results: {e}"
                logger.exception("Test %s failed during API interaction", test_id)

                return AlexaTestResult(
                    test_id=test_id,
                    description=description,
                    category=category,
                    suite=suite,
                    endpoint=endpoint,
                    expected=expected,
                    actual=None,
                    passed=False,
                    error_message=error_msg,
                    diagnostics={
                        'http_port': http_port,
                        'lite_port': lite_port,
                        'ics_source_url': ics_source_url,
                        'datetime_override': datetime_override,
                        'endpoint': endpoint,
                        'query_params': query_params,
                        'exception': str(e),
                    },
                )

        except Exception as e:
            # Setup failed
            error_msg = f"Test setup failed: {e}"
            logger.exception("Test %s failed during setup", test_id)

            return AlexaTestResult(
                test_id=test_id,
                description=description,
                category=category,
                suite=suite,
                endpoint=endpoint,
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

    def _wait_for_alexa_endpoint(
        self,
        port: int,
        endpoint: str,
        query_params: Dict[str, Any],
        timeout: float = 30.0,
        retry_interval: float = 1.0
    ) -> Dict[str, Any]:
        """Wait for Alexa endpoint to be ready and return response.

        Args:
            port: Port of the calendarbot_lite server
            endpoint: API endpoint path (e.g., '/api/alexa/launch-summary')
            query_params: Query parameters to include in request
            timeout: Maximum time to wait in seconds
            retry_interval: Time between retry attempts in seconds

        Returns:
            JSON response from endpoint

        Raises:
            TimeoutError: If endpoint doesn't become ready within timeout
            Exception: If endpoint returns error or invalid JSON
        """
        import time

        # Build URL with query parameters
        base_url = f"http://127.0.0.1:{port}{endpoint}"
        if query_params:
            url = f"{base_url}?{urlencode(query_params)}"
        else:
            url = base_url

        start_time = time.time()
        last_error = None

        while time.time() - start_time < timeout:
            try:
                with urlopen(url, timeout=10) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode())
                        logger.debug("Successfully got Alexa API response: %s keys", list(data.keys()))
                        return data
                    else:
                        last_error = f"HTTP {response.status}: {response.reason}"

            except Exception as e:
                last_error = str(e)
                logger.debug("Waiting for Alexa endpoint (attempt failed: %s)", last_error)

            time.sleep(retry_interval)

        raise TimeoutError(
            f"Alexa endpoint {endpoint} not ready after {timeout}s. Last error: {last_error}"
        )

    def _validate_alexa_response(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any],
        test_spec: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Validate Alexa API response with flexible matching rules.

        Args:
            expected: Expected response structure with validation rules
            actual: Actual API response
            test_spec: Full test specification for context

        Returns:
            Tuple of (passed, validation_details)
        """
        validation_details = {
            'field_validations': [],
            'speech_text_validations': [],
            'ssml_validations': [],
            'errors': [],
        }

        # 1. Validate required fields with exact matching
        if 'field_exact_match' in expected:
            for field_path, expected_value in expected['field_exact_match'].items():
                actual_value = self._get_nested_field(actual, field_path)
                if actual_value != expected_value:
                    validation_details['errors'].append(
                        f"Field '{field_path}': expected {expected_value!r}, got {actual_value!r}"
                    )
                else:
                    validation_details['field_validations'].append(
                        f"Field '{field_path}' matched: {expected_value!r}"
                    )

        # 2. Validate fields that should contain specific values
        if 'field_contains' in expected:
            for field_path, expected_items in expected['field_contains'].items():
                actual_value = self._get_nested_field(actual, field_path)
                if not isinstance(expected_items, list):
                    expected_items = [expected_items]

                for item in expected_items:
                    if isinstance(actual_value, str):
                        if item not in actual_value:
                            validation_details['errors'].append(
                                f"Field '{field_path}' should contain {item!r}, got {actual_value!r}"
                            )
                        else:
                            validation_details['field_validations'].append(
                                f"Field '{field_path}' contains {item!r}"
                            )
                    elif isinstance(actual_value, list):
                        if item not in actual_value:
                            validation_details['errors'].append(
                                f"Field '{field_path}' should contain item {item!r}, got {actual_value!r}"
                            )
                        else:
                            validation_details['field_validations'].append(
                                f"Field '{field_path}' contains item {item!r}"
                            )

        # 3. Validate speech_text patterns
        if 'speech_text_patterns' in expected:
            speech_text = actual.get('speech_text', '')
            for pattern in expected['speech_text_patterns']:
                if isinstance(pattern, str):
                    # Simple substring match
                    if pattern not in speech_text:
                        validation_details['errors'].append(
                            f"Speech text missing expected phrase: {pattern!r}"
                        )
                    else:
                        validation_details['speech_text_validations'].append(
                            f"Found phrase: {pattern!r}"
                        )
                elif isinstance(pattern, dict) and 'regex' in pattern:
                    # Regex match
                    if not re.search(pattern['regex'], speech_text):
                        validation_details['errors'].append(
                            f"Speech text doesn't match regex: {pattern['regex']!r}"
                        )
                    else:
                        validation_details['speech_text_validations'].append(
                            f"Matched regex: {pattern['regex']!r}"
                        )

        # 4. Validate SSML if present
        if 'ssml_validation' in expected:
            ssml_rules = expected['ssml_validation']
            ssml = actual.get('ssml')

            if ssml_rules.get('required', False) and not ssml:
                validation_details['errors'].append("SSML is required but not present")
            elif ssml:
                ssml_errors = self._validate_ssml(ssml, ssml_rules)
                if ssml_errors:
                    validation_details['errors'].extend(ssml_errors)
                    validation_details['ssml_validations'].append("SSML validation FAILED")
                else:
                    validation_details['ssml_validations'].append("SSML validation passed")

        # 5. Validate nested objects (next_meeting, done_for_day, etc.)
        if 'nested_objects' in expected:
            for obj_path, obj_rules in expected['nested_objects'].items():
                actual_obj = self._get_nested_field(actual, obj_path)

                if actual_obj is None and obj_rules.get('required', False):
                    validation_details['errors'].append(f"Required object '{obj_path}' is missing")
                elif actual_obj:
                    obj_errors = self._validate_nested_object(obj_path, obj_rules, actual_obj)
                    if obj_errors:
                        validation_details['errors'].extend(obj_errors)
                    else:
                        validation_details['field_validations'].append(
                            f"Nested object '{obj_path}' validated successfully"
                        )

        # Determine if test passed
        passed = len(validation_details['errors']) == 0

        return passed, validation_details

    def _get_nested_field(self, obj: Dict[str, Any], field_path: str) -> Any:
        """Get nested field from object using dot notation.

        Args:
            obj: Object to query
            field_path: Dot-separated field path (e.g., 'next_meeting.subject')

        Returns:
            Field value or None if not found
        """
        parts = field_path.split('.')
        current = obj

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def _validate_ssml(self, ssml: str, rules: Dict[str, Any]) -> List[str]:
        """Validate SSML structure and content.

        Args:
            ssml: SSML string to validate
            rules: Validation rules (max_chars, required_tags, etc.)

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Check character limit
        if 'max_chars' in rules:
            if len(ssml) > rules['max_chars']:
                errors.append(
                    f"SSML exceeds max characters: {len(ssml)} > {rules['max_chars']}"
                )

        # Validate XML structure
        try:
            # Add Amazon namespace declaration if not present to enable XML parsing
            # Alexa's SSML parser is lenient and doesn't require this, but Python's
            # XML parser is strict about namespace prefixes
            ssml_to_parse = ssml
            if 'amazon:' in ssml and 'xmlns:amazon=' not in ssml:
                # Add namespace declaration to <speak> tag
                ssml_to_parse = ssml.replace(
                    '<speak>',
                    '<speak xmlns:amazon="https://developer.amazon.com/alexa/ssml">',
                    1
                )

            root = ET.fromstring(ssml_to_parse)

            # Check root tag is <speak>
            if root.tag != 'speak':
                errors.append(f"SSML root tag should be <speak>, got <{root.tag}>")

            # Check for required tags
            if 'required_tags' in rules:
                for tag in rules['required_tags']:
                    # If the required tag is the root tag, it's present
                    if tag == root.tag:
                        continue
                    # Otherwise search for it in descendants
                    if root.find(f".//{tag}") is None:
                        errors.append(f"SSML missing required tag: <{tag}>")

        except ET.ParseError as e:
            errors.append(f"SSML is not valid XML: {e}")

        return errors

    def _validate_nested_object(
        self,
        obj_path: str,
        rules: Dict[str, Any],
        actual_obj: Dict[str, Any]
    ) -> List[str]:
        """Validate nested object against rules.

        Args:
            obj_path: Object path for error messages
            rules: Validation rules for object
            actual_obj: Actual object to validate

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Check required fields
        if 'required_fields' in rules:
            for field in rules['required_fields']:
                if field not in actual_obj or actual_obj[field] is None:
                    errors.append(f"Object '{obj_path}' missing required field: {field}")

        # Check field values
        if 'field_values' in rules:
            for field, expected_value in rules['field_values'].items():
                actual_value = actual_obj.get(field)
                if actual_value != expected_value:
                    errors.append(
                        f"Object '{obj_path}.{field}': expected {expected_value!r}, got {actual_value!r}"
                    )

        return errors

    def _format_validation_errors(self, validation_details: Dict[str, Any]) -> str:
        """Format validation errors into a readable message.

        Args:
            validation_details: Validation details dictionary

        Returns:
            Formatted error message
        """
        errors = validation_details.get('errors', [])
        if not errors:
            return "Validation passed"

        return f"{len(errors)} validation error(s): " + "; ".join(errors[:3])

    def generate_json_report(self, results: List[AlexaTestResult]) -> Dict[str, Any]:
        """Generate JSON report from test results.

        Args:
            results: List of test results

        Returns:
            JSON-serializable report dictionary
        """
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count

        # Group by suite and category
        by_suite = {}
        by_category = {}

        for result in results:
            # By suite
            if result.suite not in by_suite:
                by_suite[result.suite] = {'passed': 0, 'failed': 0, 'tests': []}
            if result.passed:
                by_suite[result.suite]['passed'] += 1
            else:
                by_suite[result.suite]['failed'] += 1
            by_suite[result.suite]['tests'].append(result.test_id)

            # By category
            if result.category not in by_category:
                by_category[result.category] = {'passed': 0, 'failed': 0, 'tests': []}
            if result.passed:
                by_category[result.category]['passed'] += 1
            else:
                by_category[result.category]['failed'] += 1
            by_category[result.category]['tests'].append(result.test_id)

        report = {
            'summary': {
                'total_tests': len(results),
                'passed': passed_count,
                'failed': failed_count,
                'success_rate': passed_count / len(results) if results else 0.0,
                'by_suite': by_suite,
                'by_category': by_category,
            },
            'tests': [
                {
                    'test_id': result.test_id,
                    'description': result.description,
                    'category': result.category,
                    'suite': result.suite,
                    'endpoint': result.endpoint,
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

    def generate_summary_string(self, results: List[AlexaTestResult]) -> str:
        """Generate human-friendly summary string.

        Args:
            results: List of test results

        Returns:
            Multi-line summary string
        """
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count

        lines = [
            f"CalendarBot Lite - Alexa API Test Results",
            f"=========================================",
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

        # Group by suite
        lines.append("Results by suite:")
        suites = {}
        for result in results:
            if result.suite not in suites:
                suites[result.suite] = {'passed': 0, 'failed': 0}
            if result.passed:
                suites[result.suite]['passed'] += 1
            else:
                suites[result.suite]['failed'] += 1

        for suite, counts in sorted(suites.items()):
            total = counts['passed'] + counts['failed']
            lines.append(f"  {suite}: {counts['passed']}/{total} passed")

        lines.append("")
        lines.append("Results by category:")
        categories = {}
        for result in results:
            if result.category not in categories:
                categories[result.category] = {'passed': 0, 'failed': 0}
            if result.passed:
                categories[result.category]['passed'] += 1
            else:
                categories[result.category]['failed'] += 1

        for category, counts in sorted(categories.items()):
            total = counts['passed'] + counts['failed']
            lines.append(f"  {category}: {counts['passed']}/{total} passed")

        return "\n".join(lines)


def run_alexa_tests_from_specs_file(
    specs_file: Path,
    fixtures_dir: Path,
    suite_filter: Optional[str] = None,
    output_json: Optional[Path] = None,
) -> List[AlexaTestResult]:
    """Convenience function to run Alexa tests from a specs file.

    Args:
        specs_file: Path to YAML test specifications
        fixtures_dir: Directory containing ICS fixture files
        suite_filter: Optional filter for test suite ('smoke', 'comprehensive', or None)
        output_json: Optional path to write JSON report

    Returns:
        List of test results
    """
    runner = AlexaTestRunner(specs_file, fixtures_dir, suite_filter=suite_filter)
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
    """CLI entry point for running Alexa tests directly."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run calendarbot_lite Alexa API integration tests")
    parser.add_argument(
        "--specs",
        type=Path,
        default=Path(__file__).parent / "alexa_specs.yaml",
        help="Path to Alexa test specifications YAML file"
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path(__file__).parent.parent / "fixtures" / "ics",
        help="Path to ICS fixtures directory"
    )
    parser.add_argument(
        "--suite",
        choices=['smoke', 'comprehensive'],
        help="Filter tests by suite (smoke or comprehensive)"
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
        results = run_alexa_tests_from_specs_file(
            specs_file=args.specs,
            fixtures_dir=args.fixtures,
            suite_filter=args.suite,
            output_json=args.output_json,
        )

        # Exit with failure code if any tests failed
        failed_count = sum(1 for r in results if not r.passed)
        sys.exit(failed_count)

    except Exception as e:
        logger.exception("Alexa test runner failed")
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
