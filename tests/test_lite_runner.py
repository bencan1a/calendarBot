"""Pytest integration tests for calendarbot_lite test runner.

Remember to activate the venv before running: `. venv/bin/activate`
"""

import pytest
from pathlib import Path
from typing import List

from tests.lite_tests.runner import LiteTestRunner, LiteTestResult, run_tests_from_specs_file


@pytest.fixture
def specs_file() -> Path:
    """Path to test specifications YAML file."""
    return Path(__file__).parent / "lite_tests" / "specs.yaml"


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to ICS fixtures directory."""
    return Path(__file__).parent / "fixtures" / "ics"


@pytest.fixture
def lite_runner(specs_file: Path, fixtures_dir: Path) -> LiteTestRunner:
    """Test runner instance configured with test specs and fixtures."""
    return LiteTestRunner(specs_file, fixtures_dir, timeout=90.0, lite_startup_timeout=45.0)


@pytest.mark.timeout(300)  # 5 minute overall timeout for integration tests
def test_lite_runner_initialization_when_valid_specs_then_loads_successfully(
    specs_file: Path, fixtures_dir: Path
) -> None:
    """Test that LiteTestRunner initializes correctly with valid specs."""
    runner = LiteTestRunner(specs_file, fixtures_dir)
    
    # Verify runner loads test specs
    assert len(runner.test_specs) > 0
    assert all(isinstance(spec, dict) for spec in runner.test_specs)
    
    # Verify required fields are present in each spec
    required_fields = ['test_id', 'description', 'category', 'ics_file', 'datetime_override', 'expected']
    for spec in runner.test_specs:
        for field in required_fields:
            assert field in spec, f"Missing required field '{field}' in test spec"


def test_lite_runner_initialization_when_missing_specs_then_raises_error() -> None:
    """Test that LiteTestRunner raises error when specs file is missing."""
    nonexistent_specs = Path("/does/not/exist/specs.yaml")
    fixtures_dir = Path(__file__).parent / "fixtures" / "ics"
    
    with pytest.raises(FileNotFoundError, match="Test specs file not found"):
        LiteTestRunner(nonexistent_specs, fixtures_dir)


def test_lite_runner_initialization_when_missing_fixtures_then_raises_error(specs_file: Path) -> None:
    """Test that LiteTestRunner raises error when fixtures directory is missing."""
    nonexistent_fixtures = Path("/does/not/exist/fixtures")
    
    with pytest.raises(FileNotFoundError, match="Fixtures directory not found"):
        LiteTestRunner(specs_file, nonexistent_fixtures)


@pytest.mark.timeout(60)
def test_lite_runner_convenience_function_when_called_then_returns_results(
    specs_file: Path, fixtures_dir: Path
) -> None:
    """Test convenience function for running tests from specs file."""
    # This test only verifies the function can be called and returns results
    # It doesn't validate that calendarbot_lite actually works since that 
    # requires the server implementation to be complete
    
    # Note: This will likely fail until calendarbot_lite server is implemented
    # but it validates the runner structure and API
    try:
        results = run_tests_from_specs_file(specs_file, fixtures_dir)
        
        # Verify we get back a list of results
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, LiteTestResult) for r in results)
        
        # Verify each result has required attributes
        for result in results:
            assert hasattr(result, 'test_id')
            assert hasattr(result, 'description')
            assert hasattr(result, 'category')
            assert hasattr(result, 'expected')
            assert hasattr(result, 'passed')
            assert isinstance(result.passed, bool)
            
    except NotImplementedError:
        # Expected when calendarbot_lite server is not yet implemented
        pytest.skip("Calendarbot_lite server not implemented yet")
    except Exception as e:
        # Log the error for debugging but don't fail the test structure validation
        pytest.fail(f"Unexpected error during test runner execution: {e}")


@pytest.mark.integration
@pytest.mark.timeout(300)  # 5 minute timeout for full integration test
def test_lite_runner_full_integration_when_all_specs_then_all_pass(lite_runner: LiteTestRunner) -> None:
    """Integration test that runs all test specs and expects them to pass.
    
    This test is marked with @pytest.mark.integration and can be skipped
    during development until calendarbot_lite server is fully implemented.
    """
    try:
        results = lite_runner.run_all_tests()
        
        # Verify all tests pass
        for result in results:
            assert result.passed, (
                f"Test {result.test_id} failed: {result.error_message}. "
                f"Diagnostics: {result.diagnostics}"
            )
        
        # Verify we ran the expected number of tests
        assert len(results) == len(lite_runner.test_specs)
        
    except NotImplementedError:
        pytest.skip("Calendarbot_lite server not implemented yet")


@pytest.mark.integration
@pytest.mark.timeout(120)
def test_lite_runner_json_report_generation_when_results_exist_then_generates_valid_json(
    lite_runner: LiteTestRunner
) -> None:
    """Test JSON report generation from test results."""
    # Create mock results for testing report generation
    mock_results = [
        LiteTestResult(
            test_id="test_1",
            description="Mock test 1",
            category="single_meeting",
            expected={"events": []},
            actual={"events": []},
            passed=True,
        ),
        LiteTestResult(
            test_id="test_2", 
            description="Mock test 2",
            category="recurring",
            expected={"events": []},
            actual=None,
            passed=False,
            error_message="Mock error",
        ),
    ]
    
    report = lite_runner.generate_json_report(mock_results)
    
    # Verify report structure
    assert 'summary' in report
    assert 'tests' in report
    
    # Verify summary
    summary = report['summary']
    assert summary['total_tests'] == 2
    assert summary['passed'] == 1
    assert summary['failed'] == 1
    assert summary['success_rate'] == 0.5
    
    # Verify test details
    tests = report['tests']
    assert len(tests) == 2
    
    test1, test2 = tests
    assert test1['test_id'] == "test_1"
    assert test1['passed'] is True
    assert test2['test_id'] == "test_2"
    assert test2['passed'] is False
    assert test2['error_message'] == "Mock error"


def test_lite_runner_summary_string_generation_when_results_exist_then_generates_readable_summary(
    lite_runner: LiteTestRunner
) -> None:
    """Test human-readable summary generation from test results."""
    # Create mock results
    mock_results = [
        LiteTestResult(
            test_id="test_1",
            description="Mock test 1",
            category="single_meeting",
            expected={"events": []},
            passed=True,
        ),
        LiteTestResult(
            test_id="test_2",
            description="Mock test 2", 
            category="recurring",
            expected={"events": []},
            passed=False,
            error_message="Mock error",
        ),
    ]
    
    summary = lite_runner.generate_summary_string(mock_results)
    
    # Verify summary contains expected information
    assert "CalendarBot Lite Test Results" in summary
    assert "Total tests: 2" in summary
    assert "Passed: 1" in summary
    assert "Failed: 1" in summary
    assert "Success rate: 50.0%" in summary
    assert "test_2: Mock error" in summary  # Failed test details
    assert "single_meeting: 1/1 passed" in summary  # Category breakdown
    assert "recurring: 0/1 passed" in summary