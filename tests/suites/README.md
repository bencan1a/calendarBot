# CalendarBot Test Suite Organization

This directory contains the test suite organization and management system for CalendarBot, providing optimized test execution strategies for different scenarios.

## 🎯 Test Suite Overview

### Critical Path Test Suite (`critical_path.py`)
**Target**: <5 minutes execution time
**Purpose**: Fast feedback for CI/CD pipelines
**Coverage**: Essential functionality only

- **Core Unit Tests**: Basic functionality for all main components
- **Security Essentials**: SSRF protection and input validation
- **API Endpoints**: Core web server functionality
- **Basic Integration**: Key workflow validation
- **Web Interface Smoke**: Basic page functionality

### Full Regression Test Suite (`full_regression.py`)
**Target**: 20-30 minutes execution time
**Purpose**: Comprehensive validation for releases
**Coverage**: Complete application testing

- **All Unit Tests**: Complete unit test coverage
- **Integration Tests**: Full component interaction testing
- **End-to-End Workflows**: Complete application scenarios
- **Browser Automation**: All browser-based testing
- **Visual Regression**: Screenshot comparison testing
- **Performance Validation**: Load and stress testing
- **Security Comprehensive**: Complete security testing

### Test Suite Manager (`suite_manager.py`)
**Purpose**: Intelligent test execution coordination
**Features**: Smart selection, performance analysis, optimization

- **Smart Test Selection**: Based on code changes
- **Performance Tracking**: Historical execution analysis
- **Optimization Recommendations**: Suite improvement suggestions
- **Execution Reporting**: Comprehensive result analysis

## 🚀 Quick Start

### Running Test Suites

```bash
# Critical path suite (fast feedback)
python tests/run_tests.py --critical-path

# Full regression suite (comprehensive)
python tests/run_tests.py --full-regression

# Smart test selection (based on changes)
python tests/run_tests.py --smart-selection

# Analyze suite performance
python tests/run_tests.py --suite-analysis

# Optimize suite organization
python tests/run_tests.py --optimize-suites
```

### Direct Suite Usage

```bash
# Critical path configuration
python tests/suites/critical_path.py --plan
python tests/suites/critical_path.py --args

# Full regression configuration
python tests/suites/full_regression.py --plan
python tests/suites/full_regression.py --phases

# Suite management
python tests/suites/suite_manager.py smart
python tests/suites/suite_manager.py analyze --days 7
```

## 📊 Test Categories and Markers

### Critical Path Markers
- `critical_path`: Essential tests for CI/CD
- `smoke`: Basic functionality verification
- `fast`: Quick-executing tests (<30 seconds)

### Comprehensive Testing Markers
- `regression`: Full regression testing
- `slow`: Tests that take significant time
- `performance`: Performance and stress tests
- `visual_regression`: Screenshot comparison tests

### Test Type Markers
- `unit`: Individual component tests
- `integration`: Component interaction tests
- `e2e`: End-to-end workflow tests
- `browser`: Browser automation tests
- `security`: Security-focused tests

## ⚡ Performance Optimization

### Critical Path Optimization
- **Parallel Execution**: Uses pytest-xdist for speed
- **Fast Failure**: Stops after 3 failures
- **Lightweight Coverage**: Basic reporting only
- **Timeout Protection**: 30-second per-test limit
- **Priority Ordering**: High-priority tests first

### Full Regression Optimization
- **Phased Execution**: Early failure detection
- **Smart Parallelization**: Where appropriate
- **Resource Monitoring**: Memory and CPU tracking
- **Visual Baseline Management**: Efficient image comparison

## 🧠 Smart Test Selection

The suite manager can intelligently select tests based on code changes:

### Selection Strategies
1. **No Changes**: Run critical path suite
2. **Few Changes**: Run targeted tests for changed files
3. **Core Changes**: Run full regression suite
4. **Many Changes**: Run critical path for safety

### File-to-Test Mapping
- `calendarbot/cache/` → `tests/unit/test_cache_manager.py`
- `calendarbot/web/` → `tests/unit/test_web_server.py`, `tests/browser/`
- `calendarbot/main.py` → Full regression recommended
- Configuration files → Integration and e2e tests

## 📈 Performance Analysis

### Execution Tracking
```bash
# Analyze recent performance
python tests/suites/suite_manager.py analyze --days 7

# Show execution trends
python tests/suites/suite_manager.py changed
```

### Metrics Tracked
- **Execution Duration**: Target vs actual times
- **Success Rate**: Pass/fail ratios over time
- **Coverage Trends**: Line and branch coverage
- **Performance Regression**: Duration increase detection

### Optimization Recommendations
- Suite restructuring suggestions
- Slow test identification
- Coverage improvement areas
- Execution time optimization

## 🔧 Configuration

### Critical Path Configuration
Located in `critical_path.py`:
```python
# Maximum execution time (seconds)
MAX_EXECUTION_TIME = 300  # 5 minutes

# Test categories with priorities
TEST_CATEGORIES = [
    TestCategory(
        name="core_unit_tests",
        paths=[...],
        max_duration=60,
        priority=1
    ),
    # ...
]
```

### Full Regression Configuration
Located in `full_regression.py`:
```python
# Target execution time range
MIN_EXECUTION_TIME = 1200  # 20 minutes
MAX_EXECUTION_TIME = 1800  # 30 minutes

# Coverage targets
# TEMPORARY ADJUSTMENT: Reduced from 85% to 70% to unblock development
# Target date for restoration to 85%: January 22, 2025 (2 weeks from Jan 8, 2025)
COVERAGE_TARGETS = {
    "line_coverage": 70,  # TEMPORARY: Reduced from 85% - restore to 85% by Jan 22, 2025
    "branch_coverage": 75,
    "function_coverage": 70
}
```

## 🏗️ CI/CD Integration

### GitHub Actions
Template available in `tests/ci/github_actions.yml`:
- Critical path on PRs and pushes
- Full regression on schedules
- Smart selection on demand
- Security scanning
- Performance monitoring

### GitLab CI
Template available in `tests/ci/gitlab_ci.yml`:
- Multi-stage pipeline
- Parallel execution matrix
- Artifact management
- Coverage reporting

### Pipeline Triggers
- **Critical Path**: All PRs, pushes to main
- **Full Regression**: Nightly, releases, manual
- **Smart Selection**: Changed files, manual
- **Security Scans**: All branches, schedules

## 📝 Adding New Tests

### Marking Tests for Suites
```python
import pytest

@pytest.mark.critical_path
@pytest.mark.unit
@pytest.mark.fast
def test_essential_functionality():
    """Essential test for critical path."""
    pass

@pytest.mark.regression
@pytest.mark.integration
@pytest.mark.slow
def test_comprehensive_workflow():
    """Comprehensive test for full regression."""
    pass
```

### Test Selection Criteria

#### Critical Path Inclusion
- Core functionality tests
- Security essentials
- Basic API validation
- Smoke tests
- Fast execution (<30s each)

#### Critical Path Exclusion
- Visual regression tests
- Performance stress tests
- Cross-browser testing
- Large dataset tests
- Slow integration tests

## 🚨 Troubleshooting

### Common Issues

#### Critical Path Exceeds 5 Minutes
```bash
# Analyze slow tests
python tests/suites/critical_path.py --validate 350

# Check recommendations
python tests/run_tests.py --optimize-suites
```

#### Full Regression Takes Too Long
```bash
# Check phase execution
python tests/suites/full_regression.py --phases

# Analyze performance
python tests/suites/suite_manager.py analyze
```

#### Smart Selection Not Working
```bash
# Check changed files detection
python tests/suites/suite_manager.py changed

# Manual test selection
python tests/run_tests.py --specific tests/unit/test_cache_manager.py
```

### Performance Optimization Tips
1. **Use Parallel Execution**: Enable `-n auto` for pytest-xdist
2. **Optimize Fixtures**: Reuse expensive setup operations
3. **Mock External Dependencies**: Avoid network calls in unit tests
4. **Profile Slow Tests**: Use `--durations` to identify bottlenecks
5. **Split Large Tests**: Break down complex test scenarios

## 📚 Best Practices

### Test Organization
- Keep critical path tests under 30 seconds each
- Use appropriate markers for all tests
- Maintain clear test naming conventions
- Document complex test scenarios

### Performance Monitoring
- Review suite performance weekly
- Act on optimization recommendations
- Monitor coverage trends
- Track execution time increases

### CI/CD Optimization
- Use critical path for fast feedback
- Schedule full regression during off-peak hours
- Cache dependencies and virtual environments
- Parallelize where possible

## 🔍 Monitoring and Alerts

### Performance Alerts
- Critical path exceeding 5 minutes
- Full regression exceeding 30 minutes
- Coverage dropping below targets
- High test failure rates

### Quality Metrics
- Test execution time trends
- Coverage percentage changes
- Success rate monitoring
- Performance regression detection

This test suite organization provides comprehensive, optimized testing strategies that balance speed with thoroughness, ensuring both rapid development feedback and comprehensive quality validation.
