# CalendarBot Testing Guide

This guide provides the **standard pytest approach** to resolve test suite reliability issues and achieve consistent coverage reporting.

## 🎯 Problems Solved

### Original Issues:
- **Test Collection vs Execution Discrepancy**: 1469 tests collected but only 850 executed
- **Coverage Context Loss**: Individual module coverage ~100% vs full suite coverage ~62%
- **Browser Test Hanging**: Tests hanging indefinitely causing timeouts
- **Configuration Conflicts**: Multiple pytest.ini files causing conflicts

### Solution Approach:
✅ **Standard pytest commands** with enhanced shell scripts for reliability
✅ **Optimized pytest configuration** to prevent hanging and conflicts
✅ **Browser test timeout protection** with process cleanup
✅ **Category-based execution** for better isolation and debugging

---

## 🚀 Standard Pytest Usage

### Basic Commands

```bash
# Activate virtual environment first
. venv/bin/activate

# Run all tests
pytest

# Run specific test categories
pytest tests/unit/                    # Unit tests only
pytest tests/integration/             # Integration tests only
pytest tests/browser/                 # Browser tests only
pytest tests/e2e/                     # End-to-end tests only

# Run tests by markers
pytest -m "unit"                      # Tests marked as unit
pytest -m "browser"                   # Tests marked as browser
pytest -m "fast"                      # Quick tests only
pytest -m "unit or integration"       # Multiple categories

# Run with coverage
pytest --cov=calendarbot              # Basic coverage
pytest --cov=calendarbot --cov-report=html    # HTML report
pytest --cov=calendarbot --cov-report=term-missing  # Terminal with missing lines
```

### Advanced Commands

```bash
# Limit execution for debugging
pytest --maxfail=5                    # Stop after 5 failures
pytest -x                             # Stop at first failure
pytest --tb=short                     # Shorter tracebacks
pytest -v                             # Verbose output

# Performance and debugging
pytest --durations=10                 # Show 10 slowest tests
pytest --collect-only                 # Show test discovery without running
pytest -k "test_name_pattern"         # Run tests matching pattern

# Specific file or function
pytest tests/unit/test_cache_manager.py                    # Single file
pytest tests/unit/test_cache_manager.py::test_initialize   # Single function
```

---

## 🔧 Enhanced Shell Scripts (Recommended)

For better reliability and timeout protection, use the enhanced shell scripts:

### Main Coverage Script

```bash
# Enhanced test execution with timeout protection and cleanup
./scripts/run_coverage.sh unit           # Unit tests (5min timeout)
./scripts/run_coverage.sh integration    # Integration tests (10min timeout)
./scripts/run_coverage.sh browser        # Browser tests (15min timeout with cleanup)
./scripts/run_coverage.sh full           # Complete suite (30min timeout)

# Diagnostic tools
./scripts/run_coverage.sh diagnose       # Analyze test suite health
./scripts/test_diagnostics.sh            # Comprehensive diagnostics
```

### Process Management

```bash
# Clean up hanging processes
./scripts/quick_kill.sh                  # Kill hanging test processes
./scripts/kill_calendarbot.sh            # Kill CalendarBot processes
```

---

## 📊 Coverage Analysis

### Consistent Coverage Reporting

The enhanced scripts ensure coverage context is preserved between individual and full suite runs:

```bash
# Individual module coverage (should match full suite)
./scripts/run_coverage.sh individual calendarbot.cache.manager
./scripts/run_coverage.sh module tests/unit/test_cache_manager.py

# Category-specific coverage with proper context
./scripts/run_coverage.sh unit           # Unit test coverage
./scripts/run_coverage.sh integration    # Integration coverage
./scripts/run_coverage.sh browser        # Browser/web coverage

# Full suite coverage (should now match individual totals)
./scripts/run_coverage.sh full
```

### Coverage Commands Explained

| Command | Purpose | Coverage Target | Timeout |
|---------|---------|----------------|---------|
| `unit` | Fast component tests | `calendarbot` | 5 min |
| `integration` | Component interaction tests | `calendarbot` | 10 min |
| `browser` | Web UI tests with cleanup | `calendarbot.web` | 15 min |
| `individual` | Specific module coverage | Custom module | 5 min |
| `full` | Complete test suite | `calendarbot` | 30 min |

---

## 🌐 Browser Test Management

### Browser Test Execution

Browser tests have been enhanced with aggressive timeout management and process cleanup:

```bash
# Standard pytest (may hang)
pytest tests/browser/

# Enhanced script (recommended - includes cleanup)
./scripts/run_coverage.sh browser
```

### Browser Test Features

- **Timeout Protection**: 15-minute hard timeout with graceful cleanup
- **Process Cleanup**: Automatic Chrome process termination
- **Memory Monitoring**: Track memory usage and warn on leaks
- **Error Recovery**: Simplified event handling to prevent deadlocks

### Manual Browser Cleanup

If browser tests hang or fail:

```bash
# Emergency cleanup
./scripts/quick_kill.sh

# Check for hanging processes
pgrep -af "chrome.*--test-type"
pgrep -af "pytest"

# Force kill specific processes
pkill -f "chrome.*--test-type"
pkill -f pytest
```

---

## 🔍 Debugging Test Issues

### Diagnostic Tools

```bash
# Comprehensive test suite analysis
./scripts/test_diagnostics.sh

# Quick diagnostic with pytest
./scripts/run_coverage.sh diagnose

# Manual investigation
pytest --collect-only -q              # Check test discovery
pytest --markers                      # Verify markers are configured
pytest tests/ --maxfail=1 -x -q       # Quick smoke test
```

### Common Issues and Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Collection ≠ Execution** | 1469 collected, 850 executed | Use category-specific execution |
| **Browser Tests Hang** | Tests timeout or never complete | Use `./scripts/run_coverage.sh browser` |
| **Coverage Mismatch** | Individual ≠ suite coverage | Use enhanced scripts for consistent context |
| **Configuration Conflicts** | Unexpected test behavior | Check `pytest.ini` for duplicates |

### Test Execution Analysis

```bash
# Compare individual vs suite execution
pytest tests/unit/test_cache_manager.py -v | grep -E "(PASSED|FAILED)" | wc -l
pytest tests/unit/ -q | grep -E "(PASSED|FAILED)" | wc -l

# Verify browser test health
pytest tests/browser/ --collect-only >/dev/null 2>&1 && echo "OK" || echo "FAILED"
```

---

## ⚙️ Configuration

### Pytest Configuration (`pytest.ini`)

Key settings optimized for reliability:

```ini
[pytest]
# Sequential execution only - prevents asyncio conflicts
timeout = 120                         # 2-minute default timeout
asyncio_mode = auto                   # Proper async support
collect_ignore = [                    # Ignore utility scripts
    "tests/run_tests.py",
    "tests/suite_manager.py"
]
```

### Browser Test Configuration (`tests/browser/conftest.py`)

Enhanced browser fixtures with:
- **Aggressive timeout management**: `asyncio.wait_for` protection
- **Process cleanup**: Chrome process termination
- **Memory monitoring**: Track and warn on memory usage
- **Simplified event handling**: Prevent deadlock scenarios

---

## 🎯 Best Practices

### Standard Workflow

1. **Start with diagnostics**:
   ```bash
   ./scripts/test_diagnostics.sh
   ```

2. **Run category-specific tests**:
   ```bash
   ./scripts/run_coverage.sh unit           # Start with fast tests
   ./scripts/run_coverage.sh integration    # Component interactions
   ./scripts/run_coverage.sh browser        # Web UI (with cleanup)
   ```

3. **Full suite execution**:
   ```bash
   ./scripts/run_coverage.sh full           # Complete coverage
   ```

### CI/CD Integration

For automated testing environments:

```bash
# Fast feedback loop
pytest tests/unit/ -m "unit or fast" --maxfail=10

# Comprehensive testing
./scripts/run_coverage.sh full

# Browser testing (with timeout protection)
./scripts/run_coverage.sh browser
```

### Development Workflow

```bash
# During development
pytest tests/unit/test_module.py -v      # Test specific module
pytest -k "test_function_name"          # Test specific function

# Before committing
./scripts/run_coverage.sh unit           # Quick verification
./scripts/run_coverage.sh diagnose       # Health check
```

---

## 📈 Expected Results

After implementing this approach:

### ✅ Test Execution Reliability
- Collection count matches execution count consistently
- No hanging browser tests with timeout protection
- Proper process cleanup and resource management

### ✅ Coverage Consistency
- Individual module coverage matches full suite coverage
- Category-specific coverage reporting with proper context
- Accurate overall coverage metrics

### ✅ Development Experience
- Standard pytest commands work reliably
- Clear diagnostic tools for troubleshooting
- Enhanced shell scripts for complex scenarios

---

## 🆘 Troubleshooting

### Emergency Cleanup

```bash
# Kill all hanging processes
./scripts/quick_kill.sh

# Clean up test artifacts
rm -f .coverage* coverage*.xml coverage*.json
rm -rf htmlcov*

# Reset test environment
./scripts/test_diagnostics.sh
```

### Contact and Support

- Use standard pytest commands first
- Refer to enhanced shell scripts for complex scenarios
- Run diagnostics for systematic troubleshooting
- Check this guide for common issues and solutions

The key principle: **Use standard pytest with enhanced reliability scripts** rather than custom test runners.
