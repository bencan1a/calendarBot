# CI/CD Patterns for CalendarBot Test Optimizations

## Automated Test Pipelines

### GitLab CI Example

```yaml
full-regression-tests:
  stage: test-comprehensive
  parallel:
    matrix:
      - PYTHON_VERSION: ["3.8", "3.9", "3.10", "3.11"]
  script:
    - python tests/run_tests.py --full-regression
  artifacts:
    paths:
      - htmlcov/
      - coverage.xml
      - coverage.json
  rules:
    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
    - if: '$CI_PIPELINE_SOURCE == "schedule"'
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

### GitHub Actions Example

```yaml
performance-monitoring:
  runs-on: ubuntu-latest
  timeout_minutes: 10
  steps:
    - uses: actions/checkout@v4
    - run: pip install -r requirements.txt pytest-benchmark
    - run: pytest --performance --timeout=2.66
```

## Coverage Reporting

- HTML & XML Reports: Integrated with Codecov
- Minimum Coverage Threshold: 80%

```yaml
coverage report -m
coverage xml -o coverage.xml
```

### Coverage Formats

- **Cobertua**: For GitLab
- **XML**: For Codecov Integration

## Performance Monitoring

- Execution Time Threshold: 2.66s maximum
- Memory Usage: ≤ 47GB

### Commands

- Fast Path: `pytest --critical-path`
- Full Regression: `pytest --full-regression`
- Performance Test: `pytest --performance`


## Fast vs. Comprehensive Execution

- `pytest --smart-selection`: For targeted, efficient testing
- `pytest --full-regression`: For complete validation

---
