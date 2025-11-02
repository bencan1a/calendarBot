"""Unit tests for calendarbot_lite test runner.

Fast, isolated tests that don't require external components.
Remember to activate the venv before running: `. venv/bin/activate`
"""

import pytest
from pathlib import Path

from tests.lite_tests.runner import LiteTestRunner, LiteTestResult

pytestmark = pytest.mark.unit


@pytest.mark.unit
def test_lite_runner_initialization_when_missing_specs_then_raises_error() -> None:
    """Test that LiteTestRunner raises error when specs file is missing."""
    nonexistent_specs = Path("/does/not/exist/specs.yaml")
    fixtures_dir = Path(__file__).parent.parent.parent / "fixtures" / "ics"
    
    with pytest.raises(FileNotFoundError, match="Test specs file not found"):
        LiteTestRunner(nonexistent_specs, fixtures_dir)


@pytest.mark.unit
def test_lite_runner_initialization_when_missing_fixtures_then_raises_error() -> None:
    """Test that LiteTestRunner raises error when fixtures directory is missing."""
    specs_file = Path(__file__).parent.parent.parent / "lite_tests" / "specs.yaml"
    nonexistent_fixtures = Path("/does/not/exist/fixtures")
    
    with pytest.raises(FileNotFoundError, match="Fixtures directory not found"):
        LiteTestRunner(specs_file, nonexistent_fixtures)

