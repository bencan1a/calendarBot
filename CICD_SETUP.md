# CI/CD and Pre-commit Setup Guide

This document explains the automated testing and CI/CD infrastructure for CalendarBot, including pre-commit hooks, GitHub Actions workflows, and coverage enforcement.

## Overview

The project now includes comprehensive automated testing infrastructure:

- **Pre-commit hooks**: Run tests and checks before commits
- **GitHub Actions CI/CD**: Multi-stage pipeline for different scenarios
- **Coverage enforcement**: Ensure minimum 80% line coverage
- **Security scanning**: Automated security analysis with bandit
- **Test suite optimization**: Fast critical path tests (<5 minutes)

## Pre-commit Hooks

### Installation

1. Install pre-commit (already in dev dependencies):
```bash
. venv/bin/activate
pip install -e ".[dev]"
```

2. Install the pre-commit hooks:
```bash
pre-commit install
```

### What Runs on Commit

The following checks run automatically before each commit:

1. **Code Formatting**:
   - Black code formatting
   - isort import sorting
   - Trailing whitespace removal
   - End-of-file fixes

2. **Security Analysis**:
   - Bandit security scanning
   - Configuration validation

3. **Type Checking**:
   - MyPy static type analysis

4. **Critical Path Tests** (< 5 minutes):
   - Core unit tests
   - Security essentials
   - Basic API endpoints
   - Essential integration tests

5. **Coverage Validation**:
   - Ensures ≥80% line coverage
   - Blocks commits if coverage drops

### Skipping Hooks (Emergency Use Only)

In rare emergencies, you can skip hooks:
```bash
git commit --no-verify -m "Emergency commit message"
```

**Note**: Use sparingly - CI will still enforce all checks.

## GitHub Actions Workflows

### Workflow Structure

The CI/CD pipeline includes multiple jobs that run based on trigger conditions:

#### 1. Critical Path Tests (Every Push)
- **Runtime**: < 5 minutes
- **Purpose**: Fast feedback on core functionality
- **Runs on**: Every push to any branch
- **Includes**: Core unit tests, security essentials, basic integration

#### 2. Code Quality (Every Push)
- **Purpose**: Ensure code quality standards
- **Includes**: Linting, type checking, security analysis
- **Tools**: flake8, mypy, bandit

#### 3. Full Test Suite (PRs and Main Branch)
- **Runtime**: 20-30 minutes
- **Purpose**: Comprehensive testing across Python versions
- **Matrix**: Python 3.8, 3.9, 3.10, 3.11
- **Includes**: All tests including browser automation

#### 4. Coverage Enforcement (PRs Only)
- **Purpose**: Block merges if coverage drops below 80%
- **Includes**: Coverage differential analysis
- **Blocks**: PR merges that reduce coverage

#### 5. Security Tests (Always)
- **Purpose**: Validate security-focused test cases
- **Includes**: SSRF protection, input validation, security headers

#### 6. Browser Tests (PRs to Main)
- **Purpose**: End-to-end browser automation testing
- **Includes**: Visual regression, accessibility, cross-browser
- **Tools**: Playwright with Chromium

#### 7. Deployment Check (Main Branch)
- **Purpose**: Validate deployment readiness
- **Includes**: Application startup validation, artifact generation

### Triggering Workflows

- **Push to any branch**: Critical path + quality checks
- **Pull request**: Full test suite + coverage enforcement
- **Pull request to main**: Additional browser testing
- **Push to main**: Deployment readiness check

## Coverage Enforcement

### Minimum Requirements

- **Line Coverage**: ≥80%
- **Branch Coverage**: Tracked and reported
- **Trend Analysis**: Coverage changes monitored

### Coverage Reports

Multiple coverage reports are generated:

1. **Terminal Output**: Immediate feedback with missing lines
2. **HTML Report**: Interactive coverage browser (`htmlcov/index.html`)
3. **XML Report**: For CI/CD integration (`coverage.xml`)
4. **JSON Report**: For programmatic analysis (`coverage.json`)

### Coverage Enforcement Script

The `scripts/coverage_enforcement.py` script provides detailed analysis:

```bash
# Basic coverage check
. venv/bin/activate
python scripts/coverage_enforcement.py --threshold 80

# Include trend analysis
python scripts/coverage_enforcement.py --threshold 80 --trend

# Strict mode (fail on any decrease)
python scripts/coverage_enforcement.py --threshold 80 --strict --trend

# Report only (no enforcement)
python scripts/coverage_enforcement.py --report-only
```

## Developer Workflow

### Daily Development

1. **Make changes** to code
2. **Run tests locally**:
   ```bash
   . venv/bin/activate
   python tests/run_tests.py --fast  # Quick feedback
   ```
3. **Commit changes** (pre-commit hooks run automatically)
4. **Push to branch** (critical path tests run in CI)

### Before Creating PR

1. **Run full test suite**:
   ```bash
   . venv/bin/activate
   python tests/run_tests.py --all
   ```
2. **Check coverage**:
   ```bash
   python tests/run_tests.py --coverage-report
   ```
3. **Run security tests**:
   ```bash
   python tests/run_tests.py --security
   ```

### PR Review Process

1. **Automated checks**: All CI workflows must pass
2. **Coverage validation**: Must maintain ≥80% coverage
3. **Security analysis**: No new security issues
4. **Code review**: Human review of changes

## Test Suite Organization

### Critical Path Suite (<5 minutes)

Optimized for fast feedback in CI/CD:
- Core unit tests for essential functionality
- Security validation tests
- Basic API endpoint tests
- Essential integration scenarios
- Smoke tests for web interface

### Full Regression Suite (20-30 minutes)

Comprehensive testing for release validation:
- All unit, integration, and e2e tests
- Browser automation testing
- Performance benchmarking
- Visual regression testing
- Cross-browser compatibility

### Test Selection Strategy

The system automatically selects appropriate test suites:

```bash
# Smart test selection based on code changes
python tests/run_tests.py --smart-selection

# Analyze test performance
python tests/run_tests.py --suite-analysis

# Optimize test organization
python tests/run_tests.py --optimize-suites
```

## Troubleshooting

### Pre-commit Hooks Failing

1. **Format issues**: Run formatters manually:
   ```bash
   black calendarbot tests
   isort calendarbot tests
   ```

2. **Type errors**: Fix MyPy issues:
   ```bash
   mypy calendarbot --ignore-missing-imports
   ```

3. **Test failures**: Debug with verbose output:
   ```bash
   python tests/run_tests.py --critical-path -v
   ```

### Coverage Issues

1. **Check specific files**:
   ```bash
   python -m pytest tests/ --cov=calendarbot --cov-report=html
   # Open htmlcov/index.html to see detailed coverage
   ```

2. **Identify missing coverage**:
   ```bash
   python scripts/coverage_enforcement.py --report-only
   ```

### CI/CD Issues

1. **Check workflow logs** in GitHub Actions
2. **Reproduce locally**:
   ```bash
   # Simulate CI environment
   python tests/run_tests.py --critical-path
   python tests/run_tests.py --lint
   python tests/run_tests.py --type-check
   ```

## Configuration Files

- **`.pre-commit-config.yaml`**: Pre-commit hook configuration
- **`.github/workflows/ci.yml`**: GitHub Actions workflow
- **`.coveragerc`**: Coverage analysis configuration
- **`pyproject.toml`**: Tool configurations (black, isort, mypy, bandit)
- **`scripts/coverage_enforcement.py`**: Coverage enforcement script

## Security Features

### Automated Security Scanning

- **Bandit**: Python security issue detection
- **Dependency scanning**: Via GitHub's dependency analysis
- **Secret detection**: Via pre-commit hooks
- **Security tests**: Dedicated test cases for security features

### Security Test Categories

- SSRF protection validation
- Input sanitization testing
- Authentication and authorization checks
- Security header validation
- Configuration security assessment

## Performance Optimization

### Test Execution Speed

- **Parallel execution**: pytest-xdist for multi-core testing
- **Smart test selection**: Run only relevant tests for changes
- **Layered testing**: Fast critical path for immediate feedback
- **Caching**: Dependency caching in CI/CD pipeline

### Resource Management

- **Timeout protection**: Prevent hanging tests
- **Memory optimization**: Efficient test fixtures
- **Cleanup automation**: Proper resource cleanup after tests
- **Artifact management**: Automated cleanup of test artifacts

This infrastructure ensures high code quality, security, and reliability while maintaining developer productivity through fast feedback loops.
