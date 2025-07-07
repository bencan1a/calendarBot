# Optimized Tests Quick Start Guide

## Running Tests

### Fast Critical Path Tests

To run the core functionality tests:

```sh
. venv/bin/activate
pytest --critical-path
```

### Detailed Unit Tests

For testing specific components:

```sh
pytest --unit
```

### Regression Tests

For comprehensive regression validation:

```sh
pytest --full-regression
```

### Smart Selection

For targeted testing based on recent changes:

```sh
pytest --smart-selection
```

### Performance Thresholds

- Execution Time: ≤ 2.66s
- Memory Usage: ≤ 47GB

### Covered Lines

- Total Expected Coverage: 80%+

## Coverage Validation

To validate coverage:

```sh
coverage report -m
```

## Troubleshooting

### Missing Coverage Data

```sh
# Run tests first to generate coverage data
pytest --unit && coverage report -m
```

### Common Issues

- **Coverage Data Not Found**: Ensure tests are executed first.
- **Timeouts Exceeded**: Optimize your tests following our performance patterns.

---
