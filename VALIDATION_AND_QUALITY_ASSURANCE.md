# Validation Steps for CalendarBot Tests

To ensure the optimized test suite operates correctly, adheres to performance expectations, and meets quality standards, follow the comprehensive validation steps below:

---

## Steps to Validate Optimization Success

1. Run Fast Tests
    ```bash
    # Verify core functionality
    pytest --critical-path
    ```
    - Expected Outcome: **All tests pass within 2.66s** maximum

2. Verify Coverage
    ```bash
    coverage report -m
    # Minimum expected coverage of: **80%+**
    ```

3. Check Performance
    ```bash
    pytest --performance
    ```
    - Expected Outcome: **Tests complete under 2.66s execution time**.
    - Memory Usage: **Below 47GB**

4. Inspect Coverage Report
    ```bash
    open htmlcov/index.html
    ```
    - Expected Outcome: **Comprehensive coverage of core functionality and data handling**.

## Test Suite Quality Assurance Checklist

- [ ] Validated optimized test suite architecture following the new modular approach
- [ ] Verified test execution speeds (less than 2.66 seconds for unit tests)
- [ ] Confirmed reduced memory usage (under 47GB) in optimized tests
- [ ] Ensured 80%+ coverage on core components like calendar handling and data processing
- [ ] Checked proper test categorization with markers (smoke, critical_path)
- [ ] Reviewed test output readability and logging performance
- [ ] Cross-verified configuration changes (pytest.ini + coveragerc)
- [ ] Tested parallel execution mode functionality

## Troubleshooting Common Issues

- Coverage Not Updating
    - **Verification Command:**
        ```bash
        coverage report -m && coverage xml
        ```
        - **Expected Outcome:** **Coverage files (coverage.xml) updated** in the **tests** directory

- Test Failures Under Parallel Execution
    - **Commands:**
       ```bash
        pytest --tb=line # For short, focused tracebacks
        pytest -n=2      # Verify parallel execution mode
        ```
        - **Look For:** **Thread-safety issues or improper fixture usage**
