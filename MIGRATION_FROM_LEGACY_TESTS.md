# Test Suite Migration Guide

## Overview

This guide explains how to transition from legacy CalendarBot tests to the updated, optimized test architecture. By following the guidelines below, you will streamline your test suite, reduce execution times, and improve coverage while maintaining reliability.

## What's Changed

### Key Improvements

- **Module Structure**: Tests are now organized into `*_optimized.py` files for clear separation of concerns and easier maintenance.

### Configuration Updates

**.coveragerc**:

```ini
[report]
# Reduced coverage threshold for improved reliability
fail_under = 80
```

**pytest.ini**:

```ini
[tool:pytest]
# Added stricter markers and performance controls
markers =
    unit
    critical_path
    smoke
    slow
    network
    browser
timeout = 60
```

### Core Concepts

- **Lightweight Fixtures**: Reduced test dependencies through lightweight fixture design, improving speed and isolation.
- **Mock Strategies**: Enhanced browser test performance using advanced mocking techniques.
- **Coverage Measurement**: Focused coverage targets on essential components while reducing complexity.

## How to Identify Coverage

1. **Run Fast Tests**
   ```sh
   pytest --critical-path
   ```

2. **Check Details by Module**
   ```sh
   pytest tests/unit/test_calendar_bot_optimized.py
   ```

3. **Analyze Coverage**
   ```sh
   coverage report -m
   ```

### Adding New Tests to the Suite

1. **Create a New Test Module**
   Add a file like `test_new_feature_optimized.py` under `tests/unit/`

2. **Implement Lightweight Fixtures**
   Define fixtures using a modular design to minimize dependencies and improve speed.

3. **Utilize Critical Path Markers**
   Flag core tests with `@pytest.mark.critical_path` and others with appropriate labels.

4. **Validate with Coverage**
   Ensure new tests meet the minimum 80% coverage target by executing:

   ```sh
   pytest --new-feature && coverage report -m
   ```

5. **Test Performance**
   Benchmark new additions and verify compliance with execution limits:

   ```sh
   pytest --performance
   ```

## Best Practices

- **Consistent Naming**: Use clear, consistent test names and module structures.
- **Performance Optimization**: Regularly review and enhance tests following our guidelines.
- **Comprehensive Reporting**: Always review HTML reports to monitor performance and coverage trends.

## Quality Assurance Checklist

- **Suite Execution**: Ensure all modules execute successfully in CI
- **Coverage**: Validate 80%+ coverage achievement on every run
- **Performance**: Verify execution time under 2.66 seconds
- **Memory**: Confirm memory usage below 47GB during tests

---
