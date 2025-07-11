# Testing Strategy

## Overview

The prevention-first development approach includes a comprehensive testing strategy that integrates with the overall quality assurance workflow. Testing is automated, efficient, and provides immediate feedback to maintain high code quality.

## Testing Philosophy

### Comprehensive Coverage
- **Unit Tests**: Every function has corresponding tests
- **Integration Tests**: Component interactions are validated
- **Type Safety**: MyPy ensures compile-time correctness
- **Security Testing**: Automated vulnerability scanning

### Smart Test Execution
- **File Change Detection**: Only run relevant tests for modified code
- **Parallel Execution**: Utilize multiple CPU cores for speed
- **Incremental Testing**: Build on previous test results
- **Fast Feedback Loops**: Quick validation for development flow

## Test Organization

### Directory Structure

```
tests/
├── unit/                           # Unit tests for individual components
│   ├── test_auth.py               # Authentication module tests
│   ├── test_calendar_integration.py
│   ├── test_config.py
│   ├── test_meeting_context.py    # Feature-specific tests
│   └── test_setup_wizard.py
├── integration/                    # Integration and workflow tests
│   ├── test_api_integration.py
│   ├── test_calendar_workflow.py
│   └── test_end_to_end.py
├── fixtures/                       # Test data and utilities
│   ├── sample_calendar_data.json
│   ├── test_configs.py
│   └── mock_responses.py
├── conftest.py                     # Shared test configuration
└── pytest.ini                     # Test runner configuration
```

### Naming Conventions

```python
# Test file naming: test_{module_name}.py
# Test function naming: test_{function_name}_when_{condition}_then_{expected}

def test_process_calendar_events_when_valid_data_then_returns_processed_list():
    """Test calendar event processing with valid input data."""
    pass

def test_process_calendar_events_when_empty_list_then_returns_empty_list():
    """Test calendar event processing with empty input."""
    pass

def test_process_calendar_events_when_invalid_data_then_raises_value_error():
    """Test calendar event processing with invalid input data."""
    pass
```

## Testing Patterns

### Unit Test Template

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any
from calendarbot.features.meeting_context import MeetingContextAnalyzer

class TestMeetingContextAnalyzer:
    """Comprehensive test suite for MeetingContextAnalyzer."""
    
    @pytest.fixture
    def calendar_data(self) -> Dict[str, Any]:
        """Provide test calendar data."""
        return {
            "calendar_id": "test_cal_123",
            "timezone": "UTC",
            "default_duration": 30
        }
    
    @pytest.fixture
    def analyzer(self, calendar_data: Dict[str, Any]) -> MeetingContextAnalyzer:
        """Create analyzer instance for testing."""
        return MeetingContextAnalyzer(calendar_data)
    
    def test_init_when_valid_calendar_data_then_creates_instance(self, calendar_data: Dict[str, Any]):
        """Test successful initialization with valid calendar data."""
        analyzer = MeetingContextAnalyzer(calendar_data)
        
        assert analyzer.calendar_data == calendar_data
        assert isinstance(analyzer, MeetingContextAnalyzer)
    
    def test_init_when_invalid_calendar_data_then_raises_value_error(self):
        """Test initialization failure with invalid calendar data."""
        with pytest.raises(ValueError, match="Calendar data must be a dictionary"):
            MeetingContextAnalyzer("invalid_data")
    
    def test_analyze_meeting_context_when_valid_meeting_then_returns_success(self, analyzer):
        """Test meeting analysis with valid meeting data."""
        meeting_data = {
            "title": "Team Standup",
            "start_time": "2024-01-01T09:00:00Z",
            "duration": 30
        }
        
        success, error = analyzer.analyze_meeting_context(meeting_data)
        
        assert success is True
        assert error is None
        assert isinstance(success, bool)
        assert error is None or isinstance(error, str)
    
    def test_analyze_meeting_context_when_missing_title_then_returns_error(self, analyzer):
        """Test meeting analysis failure when title is missing."""
        meeting_data = {
            "start_time": "2024-01-01T09:00:00Z",
            "duration": 30
        }
        
        success, error = analyzer.analyze_meeting_context(meeting_data)
        
        assert success is False
        assert error is not None
        assert "title" in error.lower()
    
    @patch('calendarbot.features.meeting_context.logger')
    def test_analyze_meeting_context_when_exception_then_logs_and_returns_error(
        self, mock_logger, analyzer
    ):
        """Test error handling and logging when analysis fails."""
        # Force an exception by passing None
        success, error = analyzer.analyze_meeting_context(None)
        
        assert success is False
        assert error is not None
        mock_logger.error.assert_called_once()
```

### Async Function Testing

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestAsyncCalendarOperations:
    """Test suite for async calendar operations."""
    
    @pytest.mark.asyncio
    async def test_fetch_calendar_events_when_valid_range_then_returns_events(self):
        """Test async calendar event fetching."""
        from datetime import datetime, timedelta
        
        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)
        
        # Mock async calendar API
        with patch('calendarbot.calendar.api_client') as mock_client:
            mock_client.get_events = AsyncMock(return_value=[
                {"id": "1", "title": "Meeting 1"},
                {"id": "2", "title": "Meeting 2"}
            ])
            
            from calendarbot.calendar import fetch_calendar_events
            events = await fetch_calendar_events("cal123", start_date, end_date)
            
            assert isinstance(events, list)
            assert len(events) == 2
            assert all("title" in event for event in events)
            mock_client.get_events.assert_called_once_with("cal123", start_date, end_date)
    
    @pytest.mark.asyncio
    async def test_fetch_calendar_events_when_api_error_then_raises_exception(self):
        """Test async function error handling."""
        from calendarbot.calendar import fetch_calendar_events, CalendarAPIError
        from datetime import datetime
        
        with patch('calendarbot.calendar.api_client') as mock_client:
            mock_client.get_events = AsyncMock(side_effect=CalendarAPIError("API Error"))
            
            with pytest.raises(CalendarAPIError):
                await fetch_calendar_events("cal123", datetime.now(), datetime.now())
```

### Integration Testing

```python
class TestCalendarWorkflowIntegration:
    """Integration tests for complete calendar workflows."""
    
    @pytest.fixture
    def mock_config(self):
        """Provide test configuration."""
        return {
            "calendar": {
                "api_key": "test_key",
                "timeout": 30
            },
            "database": {
                "url": "sqlite:///:memory:"
            }
        }
    
    def test_complete_event_processing_workflow(self, mock_config):
        """Test end-to-end event processing workflow."""
        from calendarbot.workflows import process_calendar_events
        
        # Mock all external dependencies
        with patch('calendarbot.calendar.api_client') as mock_api, \
             patch('calendarbot.database.session') as mock_db:
            
            # Setup mocks
            mock_api.get_events.return_value = [
                {"id": "1", "title": "Test Meeting", "start": "2024-01-01T09:00:00Z"}
            ]
            mock_db.save_events.return_value = True
            
            # Execute workflow
            result = process_calendar_events(mock_config, "cal123")
            
            # Verify workflow execution
            assert result["success"] is True
            assert result["events_processed"] == 1
            mock_api.get_events.assert_called_once()
            mock_db.save_events.assert_called_once()
```

## Smart Test Selection

### File Change Detection

The testing strategy includes intelligent test selection based on file changes:

```python
# .pre-commit-config.yaml excerpt
- id: smart-tests
  name: "🧪 Smart Test Selection"
  entry: python scripts/smart_test_runner.py
  language: system
  pass_filenames: true
  files: \.py$
```

Smart test selection logic:
```python
# scripts/smart_test_runner.py
import sys
from pathlib import Path
from typing import List, Set

def get_related_tests(changed_files: List[str]) -> Set[str]:
    """
    Determine which tests to run based on changed files.
    
    Args:
        changed_files: List of modified file paths
        
    Returns:
        Set of test file paths to execute
    """
    test_files = set()
    
    for file_path in changed_files:
        path = Path(file_path)
        
        # Direct test file mapping
        if path.parts[0] == "calendarbot":
            # calendarbot/auth.py -> tests/unit/test_auth.py
            test_path = f"tests/unit/test_{path.stem}.py"
            if Path(test_path).exists():
                test_files.add(test_path)
        
        # Feature-specific mappings
        if "features" in path.parts:
            # calendarbot/features/meeting_context.py -> tests/unit/test_meeting_context.py
            test_files.add(f"tests/unit/test_{path.stem}.py")
            # Also run integration tests for features
            test_files.add("tests/integration/test_feature_integration.py")
        
        # Configuration changes trigger config tests
        if path.name in ["config.py", "settings.py", "pyproject.toml"]:
            test_files.add("tests/unit/test_config.py")
            test_files.add("tests/integration/test_configuration.py")
    
    return test_files

if __name__ == "__main__":
    changed_files = sys.argv[1:]
    test_files = get_related_tests(changed_files)
    
    if test_files:
        import subprocess
        subprocess.run(["pytest"] + list(test_files) + ["-v"])
    else:
        print("No tests needed for changed files")
```

## Test Execution Modes

### Development Mode (Fast Feedback)

```bash
# Run tests for currently changed files only
pytest tests/unit/test_meeting_context.py -v

# Quick smoke test (fastest critical tests only)
pytest -m "smoke" --maxfail=3

# Parallel execution for speed
pytest -n auto tests/unit/ -v
```

### Pre-commit Mode (Smart Selection)

```bash
# Automatic smart test selection (integrated in pre-commit)
git add calendarbot/features/meeting_context.py
git commit -m "feat: improve meeting context analysis"
# Automatically runs: tests/unit/test_meeting_context.py
#                    tests/integration/test_feature_integration.py
```

### Comprehensive Mode (Full Validation)

```bash
# Complete test suite
pytest tests/ -v --cov=calendarbot

# With coverage report
pytest tests/ --cov=calendarbot --cov-report=html --cov-report=term

# All tests with performance timing
pytest tests/ -v --durations=10
```

## Coverage Requirements

### Target Metrics

- **Unit Test Coverage**: >95% for new code
- **Integration Coverage**: >80% for workflows
- **Type Coverage**: 100% (enforced by MyPy)
- **Security Coverage**: 100% (enforced by Bandit)

### Coverage Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["calendarbot"]
omit = [
    "tests/*",
    "*/migrations/*",
    "*/venv/*",
    "setup.py"
]

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false

[tool.coverage.html]
directory = "htmlcov"
```

### Coverage Enforcement

```python
# In pre-commit hooks
- id: coverage-check
  name: "📊 Coverage Check"
  entry: sh -c '. venv/bin/activate && python -m coverage run -m pytest tests/unit/ && python -m coverage report --fail-under=95'
  language: system
  pass_filenames: false
  files: \.py$
  stages: [pre-push]  # Only on push, not every commit
```

## Test Data Management

### Fixtures and Test Data

```python
# tests/fixtures/test_configs.py
from typing import Dict, Any

def minimal_config() -> Dict[str, Any]:
    """Minimal valid configuration for testing."""
    return {
        "calendar": {"api_key": "test_key"},
        "database": {"url": "sqlite:///:memory:"}
    }

def complete_config() -> Dict[str, Any]:
    """Complete configuration with all options."""
    return {
        "calendar": {
            "api_key": "test_key",
            "timeout": 30,
            "retry_attempts": 3
        },
        "database": {
            "url": "sqlite:///:memory:",
            "pool_size": 5
        },
        "features": {
            "meeting_context": True,
            "smart_scheduling": True
        }
    }

# tests/fixtures/sample_calendar_data.json
{
  "events": [
    {
      "id": "event_1",
      "title": "Team Standup",
      "start": "2024-01-01T09:00:00Z",
      "end": "2024-01-01T09:30:00Z",
      "attendees": ["user1@example.com", "user2@example.com"]
    },
    {
      "id": "event_2",
      "title": "Project Review",
      "start": "2024-01-01T14:00:00Z",
      "end": "2024-01-01T15:00:00Z",
      "attendees": ["user1@example.com", "manager@example.com"]
    }
  ]
}
```

### Mock Patterns

```python
# tests/conftest.py - Shared mocks and fixtures
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_calendar_api():
    """Mock calendar API client."""
    mock = Mock()
    mock.get_events = AsyncMock(return_value=[])
    mock.create_event = AsyncMock(return_value={"id": "new_event"})
    mock.update_event = AsyncMock(return_value=True)
    mock.delete_event = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def mock_database():
    """Mock database session."""
    mock = Mock()
    mock.save_events = Mock(return_value=True)
    mock.get_events = Mock(return_value=[])
    mock.update_event = Mock(return_value=True)
    return mock
```

## Performance Testing

### Test Execution Performance

```python
# Performance benchmarks for critical functions
import pytest
import time
from calendarbot.processors import EventProcessor

class TestEventProcessorPerformance:
    """Performance tests for event processing."""
    
    @pytest.mark.performance
    def test_process_large_event_list_performance(self):
        """Test processing performance with large event lists."""
        # Generate test data
        events = [
            {"id": f"event_{i}", "title": f"Meeting {i}"}
            for i in range(1000)
        ]
        
        processor = EventProcessor({"max_events": 1000})
        
        start_time = time.time()
        result = processor.process_events(events)
        execution_time = time.time() - start_time
        
        # Performance assertions
        assert execution_time < 1.0  # Should complete in under 1 second
        assert len(result) == 1000
        
    @pytest.mark.performance
    def test_concurrent_processing_performance(self):
        """Test concurrent event processing performance."""
        import concurrent.futures
        
        processor = EventProcessor({"max_events": 100})
        event_batches = [
            [{"id": f"batch_{batch}_event_{i}", "title": f"Meeting {i}"}
             for i in range(100)]
            for batch in range(10)
        ]
        
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(processor.process_events, batch)
                for batch in event_batches
            ]
            results = [future.result() for future in futures]
        execution_time = time.time() - start_time
        
        assert execution_time < 2.0  # Concurrent should be faster
        assert len(results) == 10
```

## Continuous Integration

### GitHub Actions Integration

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -e .
    
    - name: Run pre-commit hooks
      run: |
        pre-commit run --all-files
    
    - name: Run tests with coverage
      run: |
        pytest tests/ --cov=calendarbot --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## Test Maintenance

### Regular Maintenance Tasks

```bash
# Weekly test maintenance routine
# 1. Update test dependencies
pip install --upgrade pytest pytest-cov pytest-mock

# 2. Check for unused fixtures
pytest --collect-only --quiet | grep "unused"

# 3. Review test performance
pytest --durations=20 tests/

# 4. Clean up test artifacts
rm -rf .pytest_cache/ htmlcov/ .coverage
```

### Test Quality Metrics

```bash
# Test coverage trending
coverage run -m pytest tests/
coverage report --show-missing

# Test reliability (flaky test detection)
pytest --count=10 tests/unit/  # Run tests multiple times

# Test documentation coverage
pytest --doctest-modules calendarbot/
```

## Integration with Prevention-First Workflow

The testing strategy seamlessly integrates with the prevention-first development approach:

1. **Real-time Feedback**: Tests run automatically on file changes
2. **Smart Selection**: Only relevant tests execute for quick feedback
3. **Comprehensive Validation**: Full test suite runs before important commits
4. **Type Safety**: MyPy ensures tests match function signatures
5. **Quality Gates**: Coverage and performance thresholds prevent quality regression

This testing strategy ensures high code quality while maintaining development velocity and providing immediate feedback for the prevention-first development workflow.