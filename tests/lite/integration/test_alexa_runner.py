"""Pytest integration tests for calendarbot_lite Alexa API test runner.

Tests the Alexa API endpoints (launch-summary, done-for-day, morning-summary)
with smoke and regression test suites.

Remember to activate the venv before running: `. venv/bin/activate`

Usage:
    # Run smoke suite (fast, 5-8 tests)
    pytest tests/lite/integration/test_alexa_runner.py -m smoke -v

    # Run regression suite (thorough, 25+ tests)
    pytest tests/lite/integration/test_alexa_runner.py -m regression -v

    # Run all Alexa tests
    pytest tests/lite/integration/test_alexa_runner.py -v

    # Run specific test by ID
    pytest tests/lite/integration/test_alexa_runner.py -k "smoke_launch_summary_with_meeting"
"""

from pathlib import Path

import pytest

from tests.lite_tests.alexa_runner import AlexaTestResult, AlexaTestRunner

pytestmark = pytest.mark.integration


@pytest.fixture
def alexa_specs_file() -> Path:
    """Path to Alexa test specifications YAML file."""
    return Path(__file__).parent.parent.parent / "lite_tests" / "alexa_specs.yaml"


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to ICS fixtures directory."""
    return Path(__file__).parent.parent.parent / "fixtures" / "ics"


@pytest.fixture
def alexa_runner_smoke(alexa_specs_file: Path, fixtures_dir: Path) -> AlexaTestRunner:
    """Alexa test runner instance configured for smoke suite."""
    return AlexaTestRunner(
        alexa_specs_file,
        fixtures_dir,
        timeout=90.0,
        lite_startup_timeout=45.0,
        suite_filter='smoke'
    )


@pytest.fixture
def alexa_runner_comprehensive(alexa_specs_file: Path, fixtures_dir: Path) -> AlexaTestRunner:
    """Alexa test runner instance configured for comprehensive suite."""
    return AlexaTestRunner(
        alexa_specs_file,
        fixtures_dir,
        timeout=90.0,
        lite_startup_timeout=45.0,
        suite_filter='comprehensive'
    )


@pytest.fixture
def alexa_runner_all(alexa_specs_file: Path, fixtures_dir: Path) -> AlexaTestRunner:
    """Alexa test runner instance configured for all tests."""
    return AlexaTestRunner(
        alexa_specs_file,
        fixtures_dir,
        timeout=90.0,
        lite_startup_timeout=45.0,
        suite_filter=None
    )


@pytest.mark.integration
@pytest.mark.timeout(300)
def test_alexa_runner_initialization_when_valid_specs_then_loads_successfully(
    alexa_specs_file: Path, fixtures_dir: Path
) -> None:
    """Test that AlexaTestRunner initializes correctly with valid specs."""
    runner = AlexaTestRunner(alexa_specs_file, fixtures_dir)

    # Verify runner loads test specs
    assert len(runner.test_specs) > 0
    assert all(isinstance(spec, dict) for spec in runner.test_specs)

    # Verify required fields are present in each spec
    required_fields = [
        'test_id', 'description', 'category', 'suite', 'endpoint',
        'ics_file', 'datetime_override', 'expected'
    ]
    for spec in runner.test_specs:
        for field in required_fields:
            assert field in spec, f"Missing required field '{field}' in test spec"


@pytest.mark.unit
def test_alexa_runner_initialization_when_missing_specs_then_raises_error() -> None:
    """Test that AlexaTestRunner raises error when specs file is missing."""
    nonexistent_specs = Path("/does/not/exist/alexa_specs.yaml")
    fixtures_dir = Path(__file__).parent / "fixtures" / "ics"

    with pytest.raises(FileNotFoundError, match="Test specs file not found"):
        AlexaTestRunner(nonexistent_specs, fixtures_dir)


@pytest.mark.unit
def test_alexa_runner_initialization_when_missing_fixtures_then_raises_error(
    alexa_specs_file: Path
) -> None:
    """Test that AlexaTestRunner raises error when fixtures directory is missing."""
    nonexistent_fixtures = Path("/does/not/exist/fixtures")

    with pytest.raises(FileNotFoundError, match="Fixtures directory not found"):
        AlexaTestRunner(alexa_specs_file, nonexistent_fixtures)


@pytest.mark.unit
def test_alexa_runner_suite_filtering_when_smoke_then_filters_correctly(
    alexa_specs_file: Path, fixtures_dir: Path
) -> None:
    """Test that suite filtering works for smoke tests."""
    runner = AlexaTestRunner(alexa_specs_file, fixtures_dir, suite_filter='smoke')

    # Verify all loaded specs are smoke tests
    assert len(runner.test_specs) > 0
    assert all(spec['suite'] == 'smoke' for spec in runner.test_specs)


@pytest.mark.unit
def test_alexa_runner_suite_filtering_when_comprehensive_then_filters_correctly(
    alexa_specs_file: Path, fixtures_dir: Path
) -> None:
    """Test that suite filtering works for comprehensive tests."""
    runner = AlexaTestRunner(alexa_specs_file, fixtures_dir, suite_filter='comprehensive')

    # Verify all loaded specs are comprehensive tests
    assert len(runner.test_specs) > 0
    assert all(spec['suite'] == 'comprehensive' for spec in runner.test_specs)


def pytest_generate_tests(metafunc):
    """Dynamically generate test parameters from Alexa test specs.

    This function is called by pytest to parametrize tests. It reads the
    Alexa test specifications from the YAML file and creates a separate test
    for each spec with appropriate markers (smoke or regression).
    """
    if "alexa_test_spec" in metafunc.fixturenames:
        # Load test specs
        specs_file = Path(__file__).parent.parent.parent / "lite_tests" / "alexa_specs.yaml"
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "ics"

        # Create runner to load specs (no suite filter - load all)
        runner = AlexaTestRunner(specs_file, fixtures_dir)

        # Create parametrized values with markers
        params = []
        ids = []
        for spec in runner.test_specs:
            # Determine marker based on suite
            suite = spec.get('suite', 'unknown')
            if suite == 'smoke':
                param = pytest.param(spec, marks=[pytest.mark.smoke])
            elif suite == 'comprehensive':
                param = pytest.param(spec, marks=[pytest.mark.regression])
            else:
                param = spec

            params.append(param)
            ids.append(spec['test_id'])

        # Parametrize with markers applied
        metafunc.parametrize(
            "alexa_test_spec",
            params,
            ids=ids
        )


@pytest.mark.integration
@pytest.mark.timeout(60)
def test_individual_alexa_spec_execution(
    alexa_runner_all: AlexaTestRunner, alexa_test_spec: dict
) -> None:
    """Run a single Alexa API test spec from the alexa_specs.yaml file.

    This test is parametrized to run once for each spec in the YAML file.
    Each spec becomes a separate pytest test with appropriate markers based
    on the suite (smoke or comprehensive).

    To add a new test:
    1. Add ICS file to tests/fixtures/ics/alexa/
    2. Add entry to tests/lite_tests/alexa_specs.yaml with suite: smoke or comprehensive
    3. Run pytest - new test is automatically discovered

    Markers are applied during parametrization:
    - suite: smoke -> pytest.mark.smoke
    - suite: comprehensive -> pytest.mark.regression
    """
    try:
        result = alexa_runner_all.run_single_test(alexa_test_spec)

        assert result.passed, (
            f"Alexa test {result.test_id} ({result.description}) failed\n"
            f"Suite: {result.suite}\n"
            f"Category: {result.category}\n"
            f"Endpoint: {result.endpoint}\n"
            f"Error: {result.error_message}\n"
            f"Expected: {result.expected}\n"
            f"Actual: {result.actual}\n"
            f"Diagnostics: {result.diagnostics}"
        )

    except NotImplementedError:
        pytest.skip("Calendarbot_lite Alexa API not implemented yet")


@pytest.mark.integration
@pytest.mark.timeout(120)
def test_alexa_runner_json_report_generation_when_results_exist_then_generates_valid_json(
    alexa_runner_smoke: AlexaTestRunner
) -> None:
    """Test JSON report generation from Alexa test results."""
    # Create mock results for testing report generation
    mock_results = [
        AlexaTestResult(
            test_id="test_1",
            description="Mock Alexa test 1",
            category="launch_summary",
            suite="smoke",
            endpoint="/api/alexa/launch-summary",
            expected={"has_meetings_today": True},
            actual={"has_meetings_today": True},
            passed=True,
        ),
        AlexaTestResult(
            test_id="test_2",
            description="Mock Alexa test 2",
            category="done_for_day",
            suite="comprehensive",
            endpoint="/api/alexa/done-for-day",
            expected={"has_meetings_today": False},
            actual=None,
            passed=False,
            error_message="Mock error",
        ),
    ]

    report = alexa_runner_smoke.generate_json_report(mock_results)

    # Verify report structure
    assert 'summary' in report
    assert 'tests' in report

    # Verify summary
    summary = report['summary']
    assert summary['total_tests'] == 2
    assert summary['passed'] == 1
    assert summary['failed'] == 1
    assert summary['success_rate'] == 0.5

    # Verify suite breakdown
    assert 'by_suite' in summary
    assert 'smoke' in summary['by_suite']
    assert 'comprehensive' in summary['by_suite']

    # Verify category breakdown
    assert 'by_category' in summary
    assert 'launch_summary' in summary['by_category']
    assert 'done_for_day' in summary['by_category']

    # Verify test details
    tests = report['tests']
    assert len(tests) == 2

    test1, test2 = tests
    assert test1['test_id'] == "test_1"
    assert test1['passed'] is True
    assert test1['suite'] == 'smoke'
    assert test1['endpoint'] == '/api/alexa/launch-summary'

    assert test2['test_id'] == "test_2"
    assert test2['passed'] is False
    assert test2['error_message'] == "Mock error"


@pytest.mark.unit
def test_alexa_runner_summary_string_generation_when_results_exist_then_generates_readable_summary(
    alexa_runner_smoke: AlexaTestRunner
) -> None:
    """Test human-readable summary generation from Alexa test results."""
    # Create mock results
    mock_results = [
        AlexaTestResult(
            test_id="test_1",
            description="Mock Alexa test 1",
            category="launch_summary",
            suite="smoke",
            endpoint="/api/alexa/launch-summary",
            expected={},
            passed=True,
        ),
        AlexaTestResult(
            test_id="test_2",
            description="Mock Alexa test 2",
            category="morning_summary",
            suite="comprehensive",
            endpoint="/api/alexa/morning-summary",
            expected={},
            passed=False,
            error_message="Mock error",
        ),
    ]

    summary = alexa_runner_smoke.generate_summary_string(mock_results)

    # Verify summary contains expected information
    assert "CalendarBot Lite - Alexa API Test Results" in summary
    assert "Total tests: 2" in summary
    assert "Passed: 1" in summary
    assert "Failed: 1" in summary
    assert "Success rate: 50.0%" in summary
    assert "test_2: Mock error" in summary  # Failed test details

    # Verify suite breakdown
    assert "Results by suite:" in summary
    assert "smoke:" in summary
    assert "comprehensive:" in summary

    # Verify category breakdown
    assert "Results by category:" in summary
    assert "launch_summary:" in summary
    assert "morning_summary:" in summary


@pytest.mark.unit
def test_alexa_runner_get_nested_field_when_path_exists_then_returns_value(
    alexa_runner_smoke: AlexaTestRunner
) -> None:
    """Test nested field retrieval from response objects."""
    test_obj = {
        'field1': 'value1',
        'nested': {
            'field2': 'value2',
            'deeper': {
                'field3': 'value3'
            }
        }
    }

    # Test simple field
    assert alexa_runner_smoke._get_nested_field(test_obj, 'field1') == 'value1'

    # Test nested field
    assert alexa_runner_smoke._get_nested_field(test_obj, 'nested.field2') == 'value2'

    # Test deeply nested field
    assert alexa_runner_smoke._get_nested_field(test_obj, 'nested.deeper.field3') == 'value3'

    # Test non-existent field
    assert alexa_runner_smoke._get_nested_field(test_obj, 'nonexistent') is None
    assert alexa_runner_smoke._get_nested_field(test_obj, 'nested.nonexistent') is None


@pytest.mark.unit
def test_alexa_runner_validate_ssml_when_valid_then_returns_no_errors(
    alexa_runner_smoke: AlexaTestRunner
) -> None:
    """Test SSML validation with valid SSML."""
    valid_ssml = '<speak>Hello <emphasis level="strong">world</emphasis>!</speak>'
    rules = {
        'max_chars': 100,
        'required_tags': ['emphasis']
    }

    errors = alexa_runner_smoke._validate_ssml(valid_ssml, rules)
    assert len(errors) == 0


@pytest.mark.unit
def test_alexa_runner_validate_ssml_when_exceeds_max_chars_then_returns_error(
    alexa_runner_smoke: AlexaTestRunner
) -> None:
    """Test SSML validation with character limit exceeded."""
    long_ssml = '<speak>' + 'a' * 200 + '</speak>'
    rules = {'max_chars': 100}

    errors = alexa_runner_smoke._validate_ssml(long_ssml, rules)
    assert len(errors) > 0
    assert any('max characters' in err for err in errors)


@pytest.mark.unit
def test_alexa_runner_validate_ssml_when_invalid_xml_then_returns_error(
    alexa_runner_smoke: AlexaTestRunner
) -> None:
    """Test SSML validation with invalid XML."""
    invalid_ssml = '<speak>Unclosed tag'
    rules = {}

    errors = alexa_runner_smoke._validate_ssml(invalid_ssml, rules)
    assert len(errors) > 0
    assert any('not valid XML' in err for err in errors)


@pytest.mark.unit
def test_alexa_runner_validate_ssml_when_missing_required_tag_then_returns_error(
    alexa_runner_smoke: AlexaTestRunner
) -> None:
    """Test SSML validation with missing required tag."""
    ssml = '<speak>Hello world</speak>'
    rules = {'required_tags': ['emphasis', 'prosody']}

    errors = alexa_runner_smoke._validate_ssml(ssml, rules)
    assert len(errors) > 0
    assert any('missing required tag' in err for err in errors)


@pytest.mark.unit
def test_alexa_runner_validate_ssml_when_wrong_root_tag_then_returns_error(
    alexa_runner_smoke: AlexaTestRunner
) -> None:
    """Test SSML validation with wrong root tag."""
    invalid_root_ssml = '<voice>Hello world</voice>'
    rules = {}

    errors = alexa_runner_smoke._validate_ssml(invalid_root_ssml, rules)
    assert len(errors) > 0
    assert any('root tag should be <speak>' in err for err in errors)
