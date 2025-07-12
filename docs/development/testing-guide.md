# CalendarBot Testing Guide

## Overview

This guide provides comprehensive documentation for the CalendarBot test suite, covering architecture, utilities, best practices, and strategies for achieving 80% test coverage.

**Current Coverage**: 65.92% (Target: 80%)

## Table of Contents

1. [Test Architecture](#test-architecture)
2. [Testing Infrastructure](#testing-infrastructure)
3. [Test Utilities and Helpers](#test-utilities-and-helpers)
4. [Coverage Analysis](#coverage-analysis)
5. [Writing Effective Tests](#writing-effective-tests)
6. [Suite Management](#suite-management)
7. [CI/CD Integration](#cicd-integration)
8. [Troubleshooting](#troubleshooting)

## Test Architecture

### Directory Structure

```
tests/
├── conftest.py                      # Core fixtures and pytest configuration
├── pytest.ini                      # Pytest configuration
├── .coveragerc                     # Coverage configuration
├── unit/                           # Fast unit tests (70% of test pyramid)
│   ├── test_calendar_bot.py       # Core application logic
│   ├── test_cache_manager.py      # Cache functionality
│   ├── test_source_manager.py     # Source management
│   └── test_web_server.py         # Web server unit tests
├── integration/                    # Integration tests (20% of test pyramid)
│   ├── test_web_api_integration.py # API integration
│   ├── test_cache_integration.py   # Cache with real backends
│   └── test_cli_integration.py     # CLI integration
├── e2e/                           # End-to-end tests (10% of test pyramid)
│   ├── test_application_workflows.py # Complete user workflows
│   └── test_integrated_browser_validation.py # Browser-based validation
├── browser/                       # Browser-specific tests
│   ├── conftest.py               # Browser fixtures with Pyppeteer
│   └── test_ui_interactions.py   # UI interaction tests
├── fixtures/                     # Test data and mock factories
│   ├── mock_ics_data.py         # ICS data generators
│   └── test_calendars.py        # Calendar test data
├── suites/                       # Test suite management
│   ├── suite_manager.py         # Centralized test execution
│   ├── critical_path.py         # Critical path suite definition
│   └── full_regression.py       # Full regression suite definition
└── utils/                        # Testing utilities
    ├── async_helpers.py         # Async test utilities
    ├── mock_helpers.py          # Mock configuration helpers
    └── validation_helpers.py    # Assertion and validation utilities
```

### Test Pyramid Distribution

- **Unit Tests (70%)**: Fast, isolated tests for individual functions and classes
- **Integration Tests (20%)**: Tests for component interaction and external dependencies
- **End-to-End Tests (10%)**: Complete workflow validation with real user scenarios

## Testing Infrastructure

### Core Configuration

#### [`pytest.ini`](pytest.ini:1)
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Fast unit tests
    integration: Integration tests requiring external dependencies
    e2e: End-to-end tests
    browser: Browser-based validation tests
    security: Security-focused tests
    critical_path: Core functionality tests
    smoke: Basic smoke tests

addopts = 
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --maxfail=10
    --durations=10

asyncio_mode = auto
```

#### [`.coveragerc`](.coveragerc:1)
```ini
[run]
source = calendarbot
branch = True
fail_under = 80

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    if __name__ == .__main__.:
    @(abc\.)?abstractmethod

show_missing = True
precision = 2
```

### Core Fixtures

#### [`tests/conftest.py`](tests/conftest.py:1)

**Key Fixtures:**

1. **`event_loop`**: Async test support with proper cleanup
2. **`temp_dir`**: Isolated temporary directories for file operations
3. **`mock_calendar_data`**: Standardized test calendar data
4. **`calendar_cache`**: In-memory cache for testing
5. **`web_server_config`**: Web server test configuration
6. **`cli_runner`**: Click CLI testing utilities

**Usage Example:**
```python
def test_cache_operations(calendar_cache, mock_calendar_data):
    """Test cache with standardized test data."""
    cache_key = "test_events"
    calendar_cache.set(cache_key, mock_calendar_data)
    
    retrieved = calendar_cache.get(cache_key)
    assert retrieved == mock_calendar_data
```

## Test Utilities and Helpers

### Mock Data Factories

#### [`tests/fixtures/mock_ics_data.py`](tests/fixtures/mock_ics_data.py:1)

**ICSTestData Factory:**
```python
from tests.fixtures.mock_ics_data import ICSTestData

# Create Microsoft Graph API-like events
events = ICSTestData.create_mock_events(count=5, include_today=True)

# Create specific event for date
event = ICSTestData.create_event_for_date(date.today(), "Team Meeting")
```

**ICSDataFactory for Calendar Content:**
```python
from tests.fixtures.mock_ics_data import ICSDataFactory

# Basic ICS calendar
ics_content = ICSDataFactory.create_basic_ics(event_count=3)

# All-day events
all_day_ics = ICSDataFactory.create_all_day_event_ics()

# Recurring events
recurring_ics = ICSDataFactory.create_recurring_event_ics()

# Malformed content for error testing
malformed_ics = ICSDataFactory.create_malformed_ics()

# Large calendars for performance testing
large_ics = ICSDataFactory.create_large_ics(event_count=100)
```

**MockHTTPResponses for Network Testing:**
```python
from tests.fixtures.mock_ics_data import MockHTTPResponses

# Success response
success_resp = MockHTTPResponses.success_response(ics_content)

# Error responses
auth_error = MockHTTPResponses.auth_error_response()
not_found = MockHTTPResponses.not_found_response()
server_error = MockHTTPResponses.server_error_response()
timeout = MockHTTPResponses.timeout_response()
```

### Browser Testing Infrastructure

#### [`tests/browser/conftest.py`](tests/browser/conftest.py:1)

**Enhanced Browser Fixtures with Timeout Protection:**

```python
@pytest_asyncio.fixture(scope="function")
async def browser():
    """Browser instance with aggressive timeout handling."""
    # Features:
    # - 30-second launch timeout
    # - Automatic cleanup of hanging processes
    # - Memory monitoring
    # - Force cleanup on test completion
```

**BrowserTestUtils Class:**
```python
from tests.browser.conftest import BrowserTestUtils

utils = BrowserTestUtils()

# Wait for elements with timeout protection
success = await utils.wait_for_element(page, "#calendar-view", timeout=5000)

# Check element visibility
is_visible = await utils.is_element_visible(page, ".event-item")

# Get element text safely
text = await utils.get_element_text(page, ".event-title")

# Navigate with timeout protection
success = await utils.navigate_with_timeout(page, "http://localhost:8998")
```

### Async Testing Utilities

#### [`tests/utils/async_helpers.py`](tests/utils/async_helpers.py:1)

**Async Test Decorators:**
```python
from tests.utils.async_helpers import async_test, timeout_after

@async_test
async def test_async_operation():
    """Simplified async test execution."""
    result = await some_async_function()
    assert result is not None

@timeout_after(5.0)
async def test_with_timeout():
    """Test with automatic timeout protection."""
    await potentially_slow_operation()
```

**Async Context Managers:**
```python
from tests.utils.async_helpers import AsyncContextManager

async with AsyncContextManager() as context:
    # Automatic setup and cleanup
    await context.execute_operation()
```

### Mock Configuration Helpers

#### [`tests/utils/mock_helpers.py`](tests/utils/mock_helpers.py:1)

**HTTP Mock Setup:**
```python
from tests.utils.mock_helpers import setup_http_mocks

@setup_http_mocks([
    ("GET", "https://calendar.example.com/feed.ics", "mock_ics_content"),
    ("GET", "https://api.example.com/events", {"events": []})
])
def test_http_integration():
    """Test with automatic HTTP mocking."""
    pass
```

**Database Mock Patterns:**
```python
from tests.utils.mock_helpers import mock_database

with mock_database() as db:
    # Database operations use mocked backend
    db.execute("INSERT INTO events ...")
    results = db.fetch("SELECT * FROM events")
```

## Coverage Analysis

### Current Coverage Status (65.92%)

**High Coverage Areas:**
- Core calendar parsing: 85%
- Web API endpoints: 78%
- Cache operations: 82%

**Coverage Gaps (Priority Areas):**

1. **CLI Functionality (45% covered)**
   - Interactive mode handling
   - Daemon process management
   - Configuration file parsing
   - Error handling in CLI flows

2. **Error Handling Paths (35% covered)**
   - Network timeout scenarios
   - Invalid ICS format handling
   - Authentication failures
   - Cache corruption recovery

3. **Edge Cases (25% covered)**
   - Large calendar file processing
   - Timezone conversion edge cases
   - Concurrent access patterns
   - Resource cleanup scenarios

### Strategies to Reach 80% Coverage

#### 1. CLI Testing Enhancement

**Target**: Increase CLI coverage from 45% to 75%

```python
# tests/unit/test_cli_enhanced.py
import pytest
from click.testing import CliRunner
from calendarbot.cli.main import cli

class TestCLIInteractiveMode:
    """Enhanced CLI testing for interactive mode."""
    
    def test_interactive_startup_flow(self, cli_runner):
        """Test complete interactive startup sequence."""
        result = cli_runner.invoke(cli, ['--interactive'], input='y\n')
        assert result.exit_code == 0
        assert "Interactive mode started" in result.output
    
    @pytest.mark.parametrize("config_file,expected", [
        ("valid_config.json", True),
        ("malformed_config.json", False),
        ("missing_config.json", False),
    ])
    def test_config_file_handling(self, cli_runner, temp_dir, config_file, expected):
        """Test configuration file validation."""
        # Test implementation details...
```

#### 2. Error Handling Coverage

**Target**: Increase error handling coverage from 35% to 70%

```python
# tests/unit/test_error_handling.py
import pytest
from unittest.mock import patch, Mock
import asyncio

class TestNetworkErrorHandling:
    """Comprehensive network error scenario testing."""
    
    @pytest.mark.parametrize("error_type,expected_behavior", [
        (asyncio.TimeoutError, "graceful_timeout"),
        (ConnectionError, "retry_logic"),
        (ValueError, "validation_error"),
    ])
    async def test_network_error_scenarios(self, error_type, expected_behavior):
        """Test various network error handling paths."""
        # Implementation with proper mocking...
```

#### 3. Edge Case Testing

**Target**: Increase edge case coverage from 25% to 65%

```python
# tests/integration/test_edge_cases.py
class TestLargeDatasetHandling:
    """Test handling of large datasets and edge cases."""
    
    async def test_large_calendar_processing(self):
        """Test processing of calendars with 1000+ events."""
        large_ics = ICSDataFactory.create_large_ics(event_count=1000)
        # Test memory usage, performance, and correctness...
    
    async def test_concurrent_access_patterns(self):
        """Test concurrent calendar access scenarios."""
        # Test race conditions, locking, and data consistency...
```

## Writing Effective Tests

### Test Naming Conventions

**Pattern**: `test_<function_being_tested>_<scenario>_<expected_outcome>`

```python
def test_cache_get_existing_key_returns_value():
    """Test cache retrieval with existing key returns correct value."""
    
def test_cache_get_missing_key_returns_none():
    """Test cache retrieval with missing key returns None."""
    
def test_ics_parser_malformed_input_raises_error():
    """Test ICS parser with malformed input raises appropriate error."""
```

### Test Structure Best Practices

#### AAA Pattern (Arrange, Act, Assert)

```python
def test_calendar_event_creation():
    """Test calendar event creation with valid data."""
    # Arrange
    event_data = {
        "title": "Test Meeting",
        "start": datetime.now(),
        "end": datetime.now() + timedelta(hours=1)
    }
    
    # Act
    event = CalendarEvent.from_data(event_data)
    
    # Assert
    assert event.title == "Test Meeting"
    assert event.duration.total_seconds() == 3600
```

#### Parameterized Testing for Input Coverage

```python
@pytest.mark.parametrize("input_date,expected_format", [
    ("2024-01-15", "2024-01-15T00:00:00"),
    ("2024-01-15T10:30:00", "2024-01-15T10:30:00"),
    ("2024-01-15T10:30:00Z", "2024-01-15T10:30:00+00:00"),
])
def test_date_parsing_formats(input_date, expected_format):
    """Test date parsing handles various input formats."""
    result = parse_date(input_date)
    assert result.isoformat() == expected_format
```

### Mocking Guidelines

#### External Dependencies

```python
@patch('calendarbot.sources.http_client.requests')
def test_calendar_fetch_network_error(mock_requests):
    """Test calendar fetch handles network errors gracefully."""
    mock_requests.get.side_effect = ConnectionError("Network unreachable")
    
    with pytest.raises(CalendarFetchError):
        calendar_source.fetch_calendar("http://example.com/calendar.ics")
```

#### Async Operations

```python
@pytest.mark.asyncio
async def test_async_calendar_processing():
    """Test asynchronous calendar processing."""
    with patch('calendarbot.processor.async_parse') as mock_parse:
        mock_parse.return_value = asyncio.coroutine(lambda: mock_events)()
        
        result = await process_calendar_async(ics_content)
        assert len(result.events) == 3
```

## Suite Management

### [`tests/suites/suite_manager.py`](tests/suites/suite_manager.py:1)

**Centralized Test Execution and Tracking**

#### Smart Test Selection

```bash
# Analyze changed files and select appropriate tests
python tests/suites/suite_manager.py smart

# Execute smart test strategy (for pre-commit hooks)
python tests/suites/suite_manager.py execute-smart
```

#### Suite Execution

```bash
# Execute critical path suite (target: <5 minutes)
python tests/suites/suite_manager.py execute critical_path

# Execute full regression suite (target: <30 minutes)
python tests/suites/suite_manager.py execute full_regression
```

#### Performance Analysis

```bash
# Analyze test performance over last 7 days
python tests/suites/suite_manager.py analyze --days 7

# View changed files and related tests
python tests/suites/suite_manager.py changed
```

### Suite Definitions

#### Critical Path Suite ([`tests/suites/critical_path.py`](tests/suites/critical_path.py:1))

**Target**: <5 minutes execution time
**Focus**: Core functionality that must always work

- Core calendar parsing
- Basic web server functionality
- Essential CLI operations
- Critical error handling paths

#### Full Regression Suite ([`tests/suites/full_regression.py`](tests/suites/full_regression.py:1))

**Target**: <30 minutes execution time
**Focus**: Comprehensive validation before releases

- All unit tests
- Integration tests with real backends
- Browser-based UI validation
- Performance and load testing
- Security vulnerability checks

## CI/CD Integration

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: smart-tests
        name: Smart Test Selection
        entry: python tests/suites/suite_manager.py execute-smart
        language: system
        pass_filenames: false
        always_run: true
```

### GitHub Actions Integration

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  critical-path:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run critical path tests
        run: python tests/suites/suite_manager.py execute critical_path
  
  full-regression:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Run full regression
        run: python tests/suites/suite_manager.py execute full_regression
```

### Coverage Reporting

```bash
# Generate coverage report
pytest --cov=calendarbot --cov-report=html --cov-report=term --cov-fail-under=80

# Coverage with branch analysis
pytest --cov=calendarbot --cov-branch --cov-report=html

# XML report for CI integration
pytest --cov=calendarbot --cov-report=xml
```

## Testing Commands Reference

### Basic Test Execution

```bash
# Activate virtual environment
. venv/bin/activate

# Run all tests
pytest

# Run specific test categories
pytest -m unit                    # Unit tests only
pytest -m integration            # Integration tests only
pytest -m "not browser"          # Exclude browser tests

# Run with coverage
pytest --cov=calendarbot --cov-report=term

# Run tests in parallel (if pytest-xdist installed)
pytest -n auto
```

### Advanced Execution Options

```bash
# Stop on first failure
pytest -x

# Show local variables in tracebacks
pytest -l

# Run only failed tests from last run
pytest --lf

# Run tests matching pattern
pytest -k "test_cache"

# Generate HTML coverage report
pytest --cov=calendarbot --cov-report=html
```

### Browser Testing

```bash
# Run browser tests with visible browser (for debugging)
HEADLESS=false pytest tests/browser/

# Run browser tests with timeout protection
pytest tests/browser/ --timeout=300

# Run specific browser test
pytest tests/browser/test_ui_interactions.py::test_calendar_navigation
```

## Troubleshooting

### Common Issues

#### 1. Browser Tests Hanging

**Symptoms**: Tests timeout or hang indefinitely
**Solutions**:
- Check Chrome process cleanup: `ps aux | grep chrome`
- Force cleanup: `pkill -f chrome`
- Verify headless mode: `HEADLESS=true pytest tests/browser/`

#### 2. Async Test Failures

**Symptoms**: `RuntimeError: There is no current event loop`
**Solutions**:
- Ensure `pytest-asyncio` is installed
- Verify `asyncio_mode = auto` in [`pytest.ini`](pytest.ini:33)
- Use `@pytest.mark.asyncio` for async tests

#### 3. Coverage Report Issues

**Symptoms**: Coverage reports missing or incomplete
**Solutions**:
- Check [`.coveragerc`](.coveragerc:1) configuration
- Verify source paths are correct
- Use `--cov-append` for parallel execution

#### 4. Mock Configuration Problems

**Symptoms**: Mocks not applying or side effects not working
**Solutions**:
- Verify patch target paths
- Check import order and timing
- Use `autospec=True` for better mock validation

### Debugging Test Failures

#### 1. Verbose Output

```bash
# Maximum verbosity
pytest -vvv

# Show all print statements
pytest -s

# Show coverage missing lines
pytest --cov=calendarbot --cov-report=term-missing
```

#### 2. Debug Mode

```python
# Add to test for debugging
import pdb; pdb.set_trace()

# Or use pytest breakpoint
pytest --pdb
```

#### 3. Log Analysis

```bash
# Enable debug logging in tests
pytest --log-cli-level=DEBUG

# Capture logs in tests
pytest --capture=no
```

## Next Steps for 80% Coverage

### Immediate Actions (Week 1-2)

1. **Implement Enhanced CLI Testing**
   - Add [`tests/unit/test_cli_enhanced.py`](tests/unit/test_cli_enhanced.py:1) with interactive mode coverage
   - Add [`tests/integration/test_cli_daemon_mode.py`](tests/integration/test_cli_daemon_mode.py:1) for daemon testing

2. **Add Error Handling Tests**
   - Create [`tests/unit/test_error_handling.py`](tests/unit/test_error_handling.py:1) for comprehensive error scenarios
   - Add timeout and recovery testing

3. **Implement Edge Case Testing**
   - Add [`tests/integration/test_edge_cases.py`](tests/integration/test_edge_cases.py:1) for large dataset handling
   - Add concurrent access pattern testing

### Medium Term Goals (Week 3-4)

1. **Performance Testing Integration**
   - Add memory usage monitoring
   - Implement load testing scenarios
   - Add performance regression detection

2. **Security Testing Enhancement**
   - Expand SSRF protection testing
   - Add input validation security tests
   - Implement authentication/authorization testing

3. **Documentation and Training**
   - Create developer testing workshops
   - Add test writing guidelines to documentation
   - Implement test review processes

### Long Term Improvements (Month 2+)

1. **Advanced Test Automation**
   - Implement mutation testing
   - Add property-based testing with Hypothesis
   - Enhance test data generation

2. **Test Infrastructure Evolution**
   - Add test environment management
   - Implement test data versioning
   - Add cross-platform testing support

## Resources and References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Pyppeteer Documentation](https://pyppeteer.github.io/pyppeteer/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

**Last Updated**: January 2025  
**Target Coverage**: 80%  
**Current Coverage**: 65.92%  
**Estimated Timeline**: 4-6 weeks to reach target coverage