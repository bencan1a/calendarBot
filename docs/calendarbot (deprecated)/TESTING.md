# Testing Guide

## Quick Testing

### Run All Tests

```bash
# Activate environment
. venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=calendarbot
```

### Test Categories

```bash
# Unit tests (fast)
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Browser tests (slower)
pytest tests/browser/

# End-to-end tests
pytest tests/e2e/
```

### Specific Tests

```bash
# Single file
pytest tests/unit/test_cache_manager.py

# Single function
pytest tests/unit/test_cache_manager.py::test_initialize

# Pattern matching
pytest -k "test_cache"
```

## Development Testing

### Before Committing

```bash
# Quick validation
pytest tests/unit/ -x --maxfail=5

# Full test suite
pytest --cov=calendarbot --cov-report=term-missing
```

### Debug Options

```bash
# Stop on first failure
pytest -x

# Verbose output
pytest -v

# Show slowest tests
pytest --durations=10

# Test discovery only
pytest --collect-only
```

## Application Testing

### System Validation

```bash
# Built-in validation
calendarbot --test-mode

# Test specific components
calendarbot --test-mode --components ics,cache

# Verbose testing
calendarbot --test-mode --verbose
```

### Manual Testing

```bash
# Test web interface
calendarbot --web --port 8080

# Test setup wizard
calendarbot --setup
```

## Troubleshooting

### Common Issues

**Tests hanging:**
```bash
# Kill hanging processes
pkill -f pytest
pkill -f chrome
```

**Coverage issues:**
```bash
# Clean coverage data
rm -f .coverage*
pytest --cov=calendarbot --cov-report=html
```

**Browser test problems:**
```bash
# Run with timeout
timeout 300 pytest tests/browser/
```

### Test Configuration

Key pytest settings in `pytest.ini`:
- 2-minute default timeout
- Sequential execution (no parallel)
- Async support enabled

## CI/CD Testing

```bash
# Fast feedback
pytest tests/unit/ -m "unit or fast" --maxfail=10

# Full validation
pytest --cov=calendarbot --cov-report=xml

# Browser testing with timeout
timeout 900 pytest tests/browser/
```

## Test Structure

```
tests/
├── unit/           # Component tests
├── integration/    # Component interaction tests
├── browser/        # Web UI tests
├── e2e/           # End-to-end scenarios
└── fixtures/      # Test data and helpers
```

Use standard pytest commands for reliable testing. Enhanced shell scripts in `/scripts/` provide additional timeout protection and cleanup for complex scenarios.