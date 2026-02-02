"""Pytest integration tests for calendarbot_lite test runner.

Remember to activate the venv before running: `. venv/bin/activate`
"""

from pathlib import Path

import pytest

from tests.spec_runners.runner import LiteTestResult, LiteTestRunner

pytestmark = pytest.mark.integration


@pytest.fixture
def specs_file() -> Path:
    """Path to test specifications YAML file."""
    return Path(__file__).parent.parent.parent / "spec_runners" / "specs.yaml"


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to ICS fixtures directory."""
    return Path(__file__).parent.parent.parent / "fixtures" / "ics"


@pytest.fixture
def lite_runner(specs_file: Path, fixtures_dir: Path) -> LiteTestRunner:
    """Test runner instance configured with test specs and fixtures."""
    return LiteTestRunner(specs_file, fixtures_dir, timeout=90.0, lite_startup_timeout=45.0)


@pytest.mark.integration
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


@pytest.mark.unit
def test_lite_runner_initialization_when_missing_specs_then_raises_error() -> None:
    """Test that LiteTestRunner raises error when specs file is missing."""
    nonexistent_specs = Path("/does/not/exist/specs.yaml")
    fixtures_dir = Path(__file__).parent / "fixtures" / "ics"

    with pytest.raises(FileNotFoundError, match="Test specs file not found"):
        LiteTestRunner(nonexistent_specs, fixtures_dir)


@pytest.mark.unit
def test_lite_runner_initialization_when_missing_fixtures_then_raises_error(specs_file: Path) -> None:
    """Test that LiteTestRunner raises error when fixtures directory is missing."""
    nonexistent_fixtures = Path("/does/not/exist/fixtures")

    with pytest.raises(FileNotFoundError, match="Fixtures directory not found"):
        LiteTestRunner(specs_file, nonexistent_fixtures)


def pytest_generate_tests(metafunc):
    """Dynamically generate test parameters from test specs.

    This function is called by pytest to parametrize tests. It reads the
    test specifications from the YAML file and creates a separate test
    for each spec, making it easy to add new tests by just updating the
    YAML file without changing Python code.
    """
    if "test_spec" in metafunc.fixturenames:
        # Load test specs
        specs_file = Path(__file__).parent.parent.parent / "spec_runners" / "specs.yaml"
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "ics"

        # Create runner to load specs
        runner = LiteTestRunner(specs_file, fixtures_dir)

        # Parametrize with test_id as the test identifier
        metafunc.parametrize(
            "test_spec",
            runner.test_specs,
            ids=[spec['test_id'] for spec in runner.test_specs]
        )


@pytest.mark.integration
@pytest.mark.slow  # Parametrized 31 times, 60s timeout each - not for critical path
@pytest.mark.timeout(60)
def test_individual_spec_execution(
    lite_runner: LiteTestRunner, test_spec: dict
) -> None:
    """Run a single test spec from the specs.yaml file.

    This test is parametrized to run once for each spec in the YAML file.
    Each spec becomes a separate pytest test, making it easy to:
    - See which specific test failed
    - Run individual tests with pytest -k "test_id"
    - Add new tests by just updating specs.yaml

    To add a new test:
    1. Add ICS file to tests/fixtures/ics/
    2. Add entry to tests/spec_runners/specs.yaml
    3. Run pytest - new test is automatically discovered
    """
    try:
        result = lite_runner.run_single_test(test_spec)

        assert result.passed, (
            f"Test {result.test_id} ({result.description}) failed\n"
            f"Category: {result.category}\n"
            f"Error: {result.error_message}\n"
            f"Expected: {result.expected}\n"
            f"Actual: {result.actual}\n"
            f"Diagnostics: {result.diagnostics}"
        )

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


@pytest.mark.unit
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
