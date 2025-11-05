# CalendarBot Lite Test Suite

This directory contains the comprehensive test suite for **calendarbot_lite**, the lightweight standalone calendar module. The test suite is organized into distinct categories with proper markers for efficient execution and CI integration.

## Test Suite Organization

### Test Files by Category

#### Core Infrastructure
- [`conftest.py`](./conftest.py) - Centralized fixtures for all lite tests
- [`test_server_helpers.py`](./test_server_helpers.py) - Unit tests for server helper functions

#### Validation Tests  
- [`test_lite_smoke_boot.py`](./test_lite_smoke_boot.py) - Smoke tests for startup validation
- [`test_calendarbot_lite_harness.py`](./test_calendarbot_lite_harness.py) - Integration test harness

#### Component Tests
- [`test_lite_rrule_expander_units.py`](./test_lite_rrule_expander_units.py) - Unit tests for RRule parsing (16 test cases)
- [`test_skipped_store_concurrency.py`](./test_skipped_store_concurrency.py) - Thread-safety tests

#### Legacy Tests
- `test_lite_fetcher.py` - HTTP client and ICS fetching tests
- `test_http_client.py` - Shared HTTP client and connection pool tests  
- `test_lite_parser_streaming.py` - ICS parser streaming tests
- `test_rrule_streaming_optimization.py` - RRule expansion and worker pool tests
- `test_lite_done_for_day.py` - Done-for-day functionality tests
- `test_lite_logging.py` - Lite logging functionality tests
- `test_config_and_skipped_store.py` - Configuration and skipped event store tests
- `test_alexa_launch_intent.py` - Alexa launch intent handler tests
- `test_alexa_integration.py` - Alexa skill integration tests
- `test_alexa_ssml.py` - SSML generation and formatting tests
- `test_concurrency_system.py` - Concurrency system and worker pool tests
- `test_server_port_conflict.py` - Server port conflict handling tests

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
**Purpose**: Fast, isolated tests of individual functions and classes  
**Runtime**: <1s each  
**Examples**: [`test_server_helpers.py`](./test_server_helpers.py), [`test_lite_rrule_expander_units.py`](./test_lite_rrule_expander_units.py)

Fast, deterministic tests that validate individual function behavior without external dependencies. Cover normal cases, edge cases, and error conditions.

### Smoke Tests (`@pytest.mark.smoke`)  
**Purpose**: Quick startup validation tests  
**Runtime**: ~1-10s total  
**Examples**: [`test_lite_smoke_boot.py`](./test_lite_smoke_boot.py)

Lightweight tests that verify the application can start successfully and respond to basic requests without ERROR-level logs. Essential for rapid feedback in CI pipelines.

### Integration Tests (`@pytest.mark.integration`)
**Purpose**: Cross-component validation with external dependencies  
**Runtime**: Variable, typically deterministic  
**Examples**: [`test_calendarbot_lite_harness.py`](./test_calendarbot_lite_harness.py)

Tests that validate interactions between components, often using local stub servers to avoid external network dependencies while exercising full request/response paths.

### Slow Tests (`@pytest.mark.slow`)
**Purpose**: Concurrency or complex scenarios that may take >5s  
**Runtime**: >5s, potentially >30s for stress tests  
**Examples**: [`test_skipped_store_concurrency.py`](./test_skipped_store_concurrency.py)

Tests involving concurrency, stress testing, or complex scenarios that require more time. Often disabled in fast CI runs.

## Shared Fixtures

### [`simple_settings`](./conftest.py#L8)
Lightweight settings object providing deterministic configuration:
- `request_timeout`: HTTP read timeout (30s)
- `max_retries`: Retry attempts (3)
- `retry_backoff_factor`: Backoff multiplier (1.5)
- `user_agent`: Test user agent string

### [`test_timezone`](./conftest.py#L27)  
Returns `"America/Los_Angeles"` for consistent timezone-dependent tests, avoiding host-local timezone differences.

### [`cleanup_shared_http_clients`](./conftest.py#L36)
Autouse async fixture that ensures [`close_all_clients()`](../../calendarbot_lite/http_client.py) is called after every test to prevent resource leaks from httpx clients.

## Running Tests

### Prerequisites
```bash
# Activate virtual environment (REQUIRED)
. venv/bin/activate
```

### Quick Commands

#### Run Only Smoke Tests
```bash
pytest tests/lite/ -m smoke
```

#### Run Fast Unit Tests (Exclude Slow Tests)
```bash
pytest tests/lite/ -m "not slow"
```

#### Run Full Lite Test Suite
```bash
pytest tests/lite/
```

#### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/lite/ -m unit

# Integration tests only  
pytest tests/lite/ -m integration

# Smoke and unit tests
pytest tests/lite/ -m "smoke or unit"
```

#### Run with Coverage
```bash
pytest tests/lite/ --cov=calendarbot_lite --cov-report=term-missing
```

#### Run Specific Files or Functions
```bash
# Single test file
pytest tests/lite/ tests/lite/test_server_helpers.py -v

# Specific test function
pytest tests/lite/ tests/lite/test_lite_smoke_boot.py::test_lite_smoke_boot_inprocess_no_errors -v
```

### Alternative Execution
```bash
# Use the project's lite test script
./run_lite_tests.sh

# Run without the lite-specific config (uses main pytest config)
pytest tests/lite/
```

## Performance Expectations

| Category | Target Runtime | Description |
|----------|---------------|-------------|
| **Unit** | <1s per test | Individual function validation |
| **Smoke** | <10s total | Startup validation suite |
| **Integration** | <30s per test | Cross-component validation |
| **Slow** | >5s per test | Concurrency and stress tests |
| **Full Suite** | <2 minutes | All lite tests combined |

## Configuration

### Test Configuration ([`pytest-lite.ini`](../../pytest-lite.ini))
- **Test Discovery**: `tests/lite/` directory only
- **Markers**: Properly defined for all test categories
- **Timeouts**: Reasonable defaults with `--maxfail=5`
- **Logging**: INFO level with structured format
- **Warnings**: Filtered to reduce noise

### Markers Defined
- `unit`: Fast unit tests for individual functions and classes
- `smoke`: Quick startup validation tests (~1-10s runtime)  
- `integration`: Cross-component validation tests with external dependencies
- `slow`: Tests that may take >5s (deselect with `-m "not slow"`)
- `fast`: Quick-executing tests (<1s each)
- `network`: Tests that require network access

## Relationship to Main Test Suite

The lite test suite is **isolated** from the main calendarbot test suite:

- **Separate Configuration**: Uses [`pytest-lite.ini`](../../pytest-lite.ini) instead of main [`pytest.ini`](../../pytest.ini)
- **Independent Execution**: Can run without main test dependencies
- **Focused Coverage**: Tests only `calendarbot_lite/` module code
- **Fast Feedback**: Designed for rapid development cycles

### Running Excluding Lite Tests
```bash
# Run main calendarbot tests, excluding lite
pytest tests/ --ignore=tests/lite/

# With coverage for main module only
pytest tests/ --ignore=tests/lite/ --cov=calendarbot --cov-report=term-missing
```

## Troubleshooting

### Common Issues

#### Module Import Errors
```
ModuleNotFoundError: No module named 'calendarbot_lite'
```
**Solution**: Activate the virtual environment first:
```bash
. venv/bin/activate
```

#### Hanging HTTP Clients
```
ResourceWarning: unclosed <ssl.SSLSocket>
```
**Solution**: The [`cleanup_shared_http_clients`](./conftest.py#L36) fixture should handle this automatically. If issues persist, manually call:
```python
await calendarbot_lite.http_client.close_all_clients()
```

#### Port Conflicts in Integration Tests
```
OSError: [Errno 48] Address already in use
```
**Solution**: Integration tests use [`find_free_port()`](./test_calendarbot_lite_harness.py#L38) to avoid conflicts. If issues persist, check for hanging processes:
```bash
ps aux | grep calendarbot_lite
pkill -f calendarbot_lite
```

#### Slow Test Timeouts
```
FAILED tests/lite/test_skipped_store_concurrency.py::test_concurrent_adds_and_clears - Failed: Timeout
```
**Solution**: Increase timeout or skip slow tests:
```bash
pytest tests/lite/ -m "not slow"
```

### Debug Mode
Enable debug logging for test issues:
```bash
CALENDARBOT_DEBUG=true pytest tests/lite/ -v -s
```

### Test Performance Profiling
```bash
# Show slowest 10 tests
pytest tests/lite/ --durations=10

# Profile specific test
pytest tests/lite/ tests/lite/test_server_helpers.py --durations=0
```

## CI Integration

The lite test suite supports multiple CI execution patterns:

### Fast CI Pipeline  
```bash
pytest tests/lite/ -m "smoke or unit" --maxfail=1
```

### Full Validation Pipeline
```bash
pytest tests/lite/ --cov=calendarbot_lite --cov-report=xml --junitxml=lite-results.xml
```

### Coverage Target
- **Current Target**: 70% (temporarily reduced from 85% until Jan 22, 2025)
- **Measured Against**: `calendarbot_lite/` module only

## Contributing

When adding new tests to the lite suite:

1. **Choose Appropriate Markers**: Use `@pytest.mark.unit`, `@pytest.mark.smoke`, `@pytest.mark.integration`, or `@pytest.mark.slow`
2. **Use Shared Fixtures**: Leverage [`simple_settings`](./conftest.py#L8) and [`test_timezone`](./conftest.py#L27) for consistency
3. **Follow Naming Convention**: `test_function_when_condition_then_expected`  
4. **Keep Tests Fast**: Unit tests should be <1s, smoke tests <10s total
5. **Document Slow Tests**: If a test needs `@pytest.mark.slow`, document why in a comment
6. **Clean Up Resources**: Async tests should not leak HTTP clients (fixture handles this automatically)

## Related Documentation

- [Main Testing Guide](../TESTING.md) - Broader project test architecture
- [CalendarBot Lite Module](../../calendarbot_lite/README.md) - Module documentation
- [Project Architecture](../../docs/ARCHITECTURE.md) - Overall system design
