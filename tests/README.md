# CalendarBot Test Framework

This directory contains a comprehensive test suite for the CalendarBot application, implementing a multi-layered testing strategy with 70% unit tests, 20% integration tests, and 10% end-to-end tests.

## 📁 Test Structure

```
tests/
├── conftest.py                 # Test configuration and fixtures
├── pytest.ini                 # Pytest configuration
├── run_tests.py               # Test runner script
├── README.md                  # This file
│
├── lite/                      # CalendarBot Lite tests (251 tests)
│   ├── README.md              # Lite test documentation
│   ├── test_lite_fetcher.py   # HTTP client and ICS fetching
│   ├── test_http_client.py    # Shared HTTP client and connection pool
│   ├── test_lite_parser_streaming.py # ICS parser streaming
│   ├── test_rrule_streaming_optimization.py # RRule expansion and worker pool
│   ├── test_lite_done_for_day.py # Done-for-day functionality
│   ├── test_lite_logging.py   # Lite logging functionality
│   ├── test_alexa_launch_intent.py # Alexa launch intent handler
│   ├── test_alexa_integration.py # Alexa skill integration tests
│   ├── test_alexa_ssml.py     # SSML generation and formatting
│   ├── test_concurrency_system.py # Concurrency system and worker pool
│   ├── test_config_and_skipped_store.py # Config and skipped events
│   ├── test_calendarbot_lite_harness.py # Integration test harness
│   └── test_server_port_conflict.py # Server port conflict handling
│
├── fixtures/                  # Test fixtures and mock data
│   ├── mock_ics_data.py      # ICS calendar data factories
│   ├── test_databases.py     # Database testing utilities
│   └── mock_servers.py       # Mock HTTP servers
│
├── unit/                      # Unit tests (60% of tests)
│   ├── test_ics_fetcher.py   # ICS fetching and parsing
│   ├── test_cache_manager.py # Event caching and database operations
│   ├── test_source_manager.py # Source coordination and health checking
│   ├── test_web_server.py    # Web server and API endpoints
│   └── test_calendar_bot.py  # Main application logic
│
├── integration/               # Integration tests (15% of tests)
│   ├── test_source_cache_integration.py    # Source ↔ Cache integration
│   └── test_web_api_integration.py         # Web API ↔ Backend integration
│
├── browser/                   # Browser automation tests (20% of tests)
│   ├── conftest.py           # Browser test infrastructure and fixtures
│   ├── README.md             # Browser test documentation
│   ├── manage_baselines.py   # Visual regression baseline management
│   ├── test_web_interface.py # Core web interface functionality
│   ├── test_api_integration.py # Browser-based API testing
│   ├── test_responsive_design.py # Multi-viewport testing
│   ├── test_visual_regression.py # Screenshot comparison testing
│   ├── test_performance.py   # Performance and load testing
│   ├── test_accessibility.py # WCAG compliance testing
│   └── test_cross_browser.py # Cross-browser compatibility
│
└── e2e/                      # End-to-end tests (5% of tests)
    └── test_application_workflows.py       # Complete application workflows
```

## 🧪 Test Categories

### CalendarBot Lite Tests (`tests/lite/`)
Tests for the lightweight Alexa skill implementation (calendarbot_lite module).

- **`test_lite_fetcher.py`**: HTTP client, ICS fetching, SSRF protection
- **`test_http_client.py`**: Shared HTTP client and connection pool management
- **`test_lite_parser_streaming.py`**: Streaming ICS parser functionality
- **`test_rrule_streaming_optimization.py`**: RRule expansion and worker pool optimization
- **`test_lite_done_for_day.py`**: Done-for-day computation and SSML rendering
- **`test_alexa_launch_intent.py`**: Alexa launch intent handler
- **`test_alexa_integration.py`**: Alexa skill integration tests
- **`test_alexa_ssml.py`**: SSML generation, formatting, and urgency selection
- **`test_concurrency_system.py`**: Concurrency system and worker pool tests
- **`test_lite_logging.py`**: Lite logging functionality
- **`test_config_and_skipped_store.py`**: Configuration and skipped event storage
- **`test_calendarbot_lite_harness.py`**: Integration test harness
- **`test_server_port_conflict.py`**: Server port conflict handling

**Run lite tests only:**
```bash
pytest tests/lite/                          # All lite tests
pytest tests/lite/ --cov=calendarbot_lite   # With coverage
```

**Run main calendarbot tests (excluding lite):**
```bash
pytest tests/ --ignore=tests/lite/
```

### Unit Tests (`tests/unit/`)
Test individual components in isolation with mocked dependencies.

- **`test_ics_fetcher.py`**: HTTP fetching, ICS parsing, SSRF protection, authentication
- **`test_cache_manager.py`**: SQLite operations, TTL logic, event conversion, performance
- **`test_source_manager.py`**: Multi-source coordination, health checking, deduplication
- **`test_web_server.py`**: API endpoints, navigation, theme switching, security validation
- **`test_calendar_bot.py`**: Application lifecycle, error handling, background operations

### Integration Tests (`tests/integration/`)
Test component interactions and data flow between modules.

- **Source-Cache Integration**: Complete fetch → cache → retrieve pipeline
- **Web API Integration**: API endpoints working with real backend components
- **Error Handling**: Cross-component error propagation and recovery
- **Performance**: Large datasets and concurrent operations

### Browser Automation Tests (`tests/browser/`)
Test the web interface using Puppeteer browser automation for comprehensive end-to-end validation.

- **`test_web_interface.py`**: Core web interface functionality, navigation, theme switching
- **`test_api_integration.py`**: Browser-based API endpoint testing with real user interactions
- **`test_responsive_design.py`**: Multi-viewport testing across mobile, tablet, and desktop
- **`test_visual_regression.py`**: Screenshot comparison testing for UI consistency
- **`test_performance.py`**: Page load times, API response times, memory usage monitoring
- **`test_accessibility.py`**: WCAG compliance, keyboard navigation, screen reader support
- **`test_cross_browser.py`**: Cross-browser compatibility and feature support validation

### End-to-End Tests (`tests/e2e/`)
Test complete application workflows from start to finish.

- **Application Workflows**: Complete startup, refresh cycles, shutdown
- **Web Interface Workflows**: Navigation, theme switching, data display
- **Failure Recovery**: Network failures, cache corruption, graceful degradation
- **Performance**: Large datasets, high frequency operations, memory usage

## 🏗️ Test Infrastructure

### Fixtures (`tests/fixtures/`)

#### Mock Data Factory (`mock_ics_data.py`)
```python
# Create realistic test events
events = ICSTestData.create_mock_events(count=10, include_today=True)

# Generate ICS calendar content
ics_content = ICSTestData.create_mock_ics_content(events=events)

# Create specific event scenarios
event = ICSTestData.create_event_for_date(date.today(), "Test Event")
```

#### Database Utilities (`test_databases.py`)
```python
# Create test database scenarios
fresh_db = TestDatabaseFactory.create_fresh_cache_scenario()
stale_db = TestDatabaseFactory.create_stale_cache_scenario()
```

#### Mock Servers (`mock_servers.py`)
```python
# HTTP server for testing network operations
async with MockHTTPServer() as server:
    server.add_ics_endpoint("/calendar.ics", mock_events)
```

### Configuration (`conftest.py`)
Provides comprehensive fixtures for all test scenarios:

- **Database fixtures**: Fresh/stale/corrupted cache states
- **Component fixtures**: Mocked managers with realistic behavior
- **Performance fixtures**: Timing and resource usage tracking
- **Security fixtures**: Input validation and SSRF testing

## 🚀 Running Tests

### Quick Start
```bash
# Run all tests
python tests/run_tests.py --all

# NEW: Optimized Test Suites
python tests/run_tests.py --critical-path      # Fast feedback (<5 minutes)
python tests/run_tests.py --full-regression    # Comprehensive (20-30 minutes)
python tests/run_tests.py --smart-selection    # Based on code changes

# Run specific test types
python tests/run_tests.py --unit
python tests/run_tests.py --integration
python tests/run_tests.py --browser
python tests/run_tests.py --e2e
```

### 🎯 Optimized Test Suites

CalendarBot now includes **intelligent test suite organization** for optimal execution times:

#### Critical Path Suite (⚡ <5 minutes)
**Purpose**: Fast feedback for CI/CD pipelines
```bash
python tests/run_tests.py --critical-path
```
- Core unit tests for main components
- Essential security validation (SSRF protection)
- Basic API endpoint testing
- Key integration workflows
- Web interface smoke tests

#### Full Regression Suite (🔍 20-30 minutes)
**Purpose**: Comprehensive validation for releases
```bash
python tests/run_tests.py --full-regression
```
- Complete unit, integration, and e2e test coverage
- All browser automation tests (visual regression, accessibility, cross-browser)
- Performance and stress testing
- Comprehensive security testing
- Complete workflow validation

#### Smart Test Selection (🧠 Variable time)
**Purpose**: Intelligent test selection based on code changes
```bash
python tests/run_tests.py --smart-selection
```
- Analyzes changed files since last test run
- Maps source files to relevant test files
- Recommends critical path, targeted, or full regression
- Optimizes execution time based on change scope

#### Suite Analysis and Optimization
```bash
# Analyze suite performance over time
python tests/run_tests.py --suite-analysis

# Get optimization recommendations
python tests/run_tests.py --optimize-suites
```

### Advanced Usage
```bash
# Fast tests only (exclude slow operations)
python tests/run_tests.py --fast

# Security-focused tests
python tests/run_tests.py --security

# Performance tests
python tests/run_tests.py --performance

# Browser automation test categories
python tests/run_tests.py --accessibility
python tests/run_tests.py --visual-regression
python tests/run_tests.py --responsive
python tests/run_tests.py --cross-browser

# Run specific test file
python tests/run_tests.py --specific tests/unit/test_cache_manager.py
python tests/run_tests.py --specific tests/browser/test_web_interface.py

# Generate comprehensive report
python tests/run_tests.py --report
```

### Direct Pytest Usage
```bash
# Run with coverage
pytest --cov=calendarbot --cov-report=html

# Run specific markers
pytest -m "unit"
pytest -m "integration"
pytest -m "e2e"
pytest -m "security"
pytest -m "accessibility"
pytest -m "visual_regression"
pytest -m "responsive"
pytest -m "cross_browser"

# Run with verbose output
pytest -v -s tests/unit/test_ics_fetcher.py
pytest -v -s tests/browser/test_web_interface.py
```

## 📊 Coverage Tracking System

CalendarBot includes a comprehensive coverage tracking and reporting system with advanced analysis capabilities.

### Coverage Targets
- **Line Coverage**: 80% minimum with detailed reporting
- **Branch Coverage**: 70% minimum with decision path analysis
- **Function Coverage**: 60% minimum with API coverage validation

### Enhanced Coverage Features

#### Advanced Coverage Options
```bash
# Run tests with comprehensive coverage tracking
python tests/run_tests.py --coverage

# Generate detailed coverage reports
python tests/run_tests.py --coverage-report

# Generate HTML reports with enhanced styling
python tests/run_tests.py --coverage-html

# Generate XML reports for CI/CD integration
python tests/run_tests.py --coverage-xml

# Fail if coverage below custom threshold
python tests/run_tests.py --coverage --coverage-fail-under 85

# Generate coverage differential reports
python tests/run_tests.py --coverage-diff
```

#### Coverage Analysis Tool
```bash
# Comprehensive coverage analysis
python tests/coverage_analysis.py --analyze

# Identify missing coverage areas
python tests/coverage_analysis.py --missing --threshold 75

# Show coverage trends over time
python tests/coverage_analysis.py --trends --days 14

# Store coverage run for historical tracking
python tests/coverage_analysis.py --store --type unit --notes "After feature X"

# Generate JSON report for automation
python tests/coverage_analysis.py --report --format json
```

#### Coverage Badge Generation
```bash
# Generate SVG coverage badge
python scripts/generate_coverage_badge.py

# Generate markdown badge link
python scripts/generate_coverage_badge.py --format markdown

# Generate HTML badge tag
python scripts/generate_coverage_badge.py --format html

# Use XML coverage input
python scripts/generate_coverage_badge.py --xml --input coverage.xml
```

### Coverage Configuration

The system uses `.coveragerc` for centralized configuration:
- Branch coverage tracking enabled
- Comprehensive exclusion patterns for vendor code
- Multiple report formats (HTML, XML, JSON)
- Enhanced HTML styling with custom CSS
- Parallel execution support

### Coverage Reports and Analysis

#### 1. HTML Reports (`htmlcov/index.html`)
- Interactive file browser with line-by-line coverage
- Branch coverage indicators
- Custom styling with color-coded coverage levels
- Responsive design for mobile viewing
- Context-aware coverage display

#### 2. Advanced Analysis Reports
- **Coverage Hotspots**: Identify highest and lowest coverage files
- **Missing Coverage**: Detailed analysis of uncovered areas
- **Critical Files**: Focus on core application components
- **Trend Analysis**: Track coverage changes over time
- **Recommendations**: Actionable suggestions for improvement

#### 3. Historical Tracking
- SQLite database for coverage history
- Trend analysis and reporting
- Git commit correlation
- Performance impact tracking
- Coverage regression detection

### Component-Specific Targets
- **Core Logic**: 90%+ coverage (cache manager, source manager, main application)
- **Security Critical**: 95%+ coverage (SSRF protection, input validation)
- **API Endpoints**: 85%+ coverage (web server, navigation, themes)
- **Error Handling**: 80%+ coverage (all error paths tested)

### Documentation
- **Complete Guide**: See [`tests/COVERAGE.md`](COVERAGE.md) for comprehensive documentation
- **Configuration**: Coverage settings in `.coveragerc`
- **Troubleshooting**: Common issues and solutions
- **CI/CD Integration**: GitHub Actions and GitLab CI examples

## 🔒 Security Testing

### Input Validation Tests
- **Navigation Actions**: XSS, path traversal, SQL injection attempts
- **Theme Parameters**: Malicious theme names and values
- **ICS URLs**: SSRF protection testing with internal/localhost URLs
- **Error Messages**: No sensitive information leakage

### Authentication Tests
- **Basic Auth**: Username/password validation
- **Bearer Tokens**: Token format and validation
- **URL Parameters**: Auth parameter handling and security

### SSRF Protection Tests
```python
# Test internal network access prevention
ssrf_urls = [
    "http://localhost:3000/admin",
    "http://127.0.0.1:22/",
    "http://169.254.169.254/metadata",
    "file:///etc/passwd"
]
```

## ⚡ Performance Testing

### Load Testing Scenarios
- **Large Datasets**: 1000+ events processing
- **Concurrent Operations**: Multiple simultaneous requests
- **Memory Usage**: Long-running operation monitoring
- **Database Performance**: Cache operations under load

### Performance Assertions
```python
# Example performance tracking
performance_tracker.start_timer("cache_operation")
await cache_manager.cache_events(large_event_set)
performance_tracker.end_timer("cache_operation")
performance_tracker.assert_performance("cache_operation", max_seconds=2.0)
```

## 🐛 Debugging Tests

### Running with Debug Output
```bash
# Verbose output with print statements
pytest -v -s tests/unit/test_cache_manager.py::TestCacheManager::test_specific_method

# Show locals on failure
pytest --tb=long --showlocals

# Stop on first failure
pytest -x
```

### Common Debug Patterns
```python
# Debug async operations
@pytest.mark.asyncio
async def test_debug_async():
    async with AsyncDebugContext():
        result = await some_async_operation()
        print(f"Debug result: {result}")

# Debug mock calls
mock_method.assert_called_once_with(expected_arg)
print(f"Actual calls: {mock_method.call_args_list}")
```

## 🔧 Test Utilities

### Async Test Helpers
```python
# Wait for async operations
await asyncio.wait_for(operation(), timeout=5.0)

# Test concurrent operations
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Mock Helpers
```python
# Create realistic mock responses
mock_response = MockHTTPResponse(
    status_code=200,
    headers={"Content-Type": "text/calendar"},
    content=ics_content
)
```

### Database Helpers
```python
# Create isolated test database
async with TestDatabase() as db:
    # Test operations
    pass
# Database automatically cleaned up
```

## 📋 Test Maintenance

### Adding New Tests
1. **Unit Tests**: Add to appropriate `test_*.py` file in `tests/unit/`
2. **Integration Tests**: Add to relevant integration test file
3. **E2E Tests**: Add to `test_application_workflows.py`
4. **Fixtures**: Add reusable test data to `tests/fixtures/`

### Test Naming Conventions
```python
def test_component_action_condition():
    """Test that component performs action when condition is met."""
    pass

async def test_async_operation_success():
    """Test successful async operation."""
    pass
```

### Marker Usage
```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_unit_async_operation():
    pass

@pytest.mark.integration
@pytest.mark.slow
def test_integration_large_dataset():
    pass

@pytest.mark.e2e
@pytest.mark.performance
def test_end_to_end_performance():
    pass
```

## 🚨 CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run Tests
  run: |
    python tests/run_tests.py --all

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

### Coverage Enforcement
```bash
# Fail if coverage below threshold
pytest --cov=calendarbot --cov-fail-under=80
```

## 📚 Testing Best Practices

### 1. Test Independence
- Each test should be independent and isolated
- Use fixtures for setup/teardown
- Don't rely on test execution order

### 2. Realistic Test Data
- Use the `ICSTestData` factory for realistic events
- Test with various date ranges and timezones
- Include edge cases (empty calendars, malformed data)

### 3. Error Testing
- Test both success and failure paths
- Verify error messages and handling
- Test recovery scenarios

### 4. Performance Awareness
- Use `@pytest.mark.slow` for expensive tests
- Monitor memory usage in long-running tests
- Set reasonable timeouts

### 5. Security Focus
- Test all input validation paths
- Verify SSRF protection works
- Check for information leakage in errors

## 🔍 Test Analysis

### Coverage Analysis
```bash
# Find untested code
coverage report --show-missing

# Focus on specific modules
coverage report --include="calendarbot/cache/*"
```

### Performance Analysis
```bash
# Show slowest tests
pytest --durations=10

# Profile test execution
pytest --profile
```

### Failure Analysis
```bash
# Re-run only failed tests
pytest --lf

# Show detailed failure information
pytest --tb=long --showlocals
```

This comprehensive test framework ensures CalendarBot is reliable, secure, and performant across all use cases and deployment scenarios.
