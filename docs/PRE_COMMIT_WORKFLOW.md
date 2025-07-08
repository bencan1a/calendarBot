# Pre-Commit Workflow Documentation

## Overview

This document describes the optimized pre-commit configuration designed to provide fast, reliable validation while preventing cascade failures and ensuring comprehensive security and quality checks.

## Pipeline Architecture

### Staged Validation Approach

The pre-commit pipeline uses a **4-stage fail-fast strategy**:

```
Stage 1: Fast Validation (< 10 seconds)
   ↓ (if all pass)
Stage 2: Security & Type Checking (< 30 seconds)
   ↓ (if all pass)
Stage 3: Smart Test Execution (varies)
   ↓ (if all pass)
Stage 4: Format Validation (< 5 seconds)
```

### Stage Details

#### Stage 1: Fast Validation
**Purpose**: Catch basic syntax and structure issues quickly
**Duration**: < 10 seconds
**Hooks**:
- YAML Syntax Check
- JSON Syntax Check
- TOML Syntax Check
- Merge Conflict Check
- Large File Check
- Debug Statement Check
- Docstring Position Check

#### Stage 2: Security & Type Checking
**Purpose**: Comprehensive security and type validation
**Duration**: < 30 seconds
**Hooks**:
- **Bandit Security Scan** - Full security vulnerability detection
- **MyPy Type Checking** - Complete type safety validation

#### Stage 3: Smart Test Execution
**Purpose**: Intelligent test selection based on changes
**Duration**: 30 seconds to 30 minutes (depends on strategy)
**Smart Selection Logic**:

```python
if no_changes:
    strategy = "critical_path"  # ~5 minutes
elif few_changes (≤5 related tests):
    strategy = "targeted"       # ~30 seconds - 2 minutes
elif core_files_changed:
    strategy = "full_regression" # ~20-30 minutes
else:
    strategy = "critical_path"  # ~5 minutes
```

#### Stage 4: Format Validation
**Purpose**: Ensure code formatting without modifying files
**Duration**: < 5 seconds
**Hooks**:
- Black format check (check-only)
- isort import check (check-only)

## Key Features

### 1. Fail-Fast Strategy
- `fail_fast: true` stops execution at first failure
- Prevents expensive operations when basic issues exist
- Saves developer time and CI resources

### 2. Check-Only Formatting
- **Problem Solved**: No more cascade failures from auto-correcting hooks
- **Approach**: Format checks block commits without modifying files
- **Developer Action**: Run manual formatting when needed

### 3. Smart Test Selection
- **Targeted Tests**: Run only tests related to changed files
- **Critical Path**: Fast essential tests for small changes
- **Full Regression**: Comprehensive testing for core changes
- **Intelligence**: Leverages existing TestSuiteManager infrastructure

### 4. Restored Security & Type Checking
- **Bandit**: Full security scanning with medium/high severity
- **MyPy**: Complete type checking including tests
- **No Compromises**: All weakened rules restored

## Usage Guide

### Normal Development Workflow

1. **Make changes** to your code
2. **Attempt commit**: `git commit -m "Your message"`
3. **Pre-commit runs automatically**:
   - If **Stage 1 fails**: Fix syntax/structure issues
   - If **Stage 2 fails**: Fix security/type issues
   - If **Stage 3 fails**: Fix failing tests
   - If **Stage 4 fails**: Run formatting commands

### Manual Operations

#### Run Smart Test Strategy
```bash
python tests/suites/suite_manager.py execute-smart
```

#### Check What Tests Would Run
```bash
python tests/suites/suite_manager.py smart
```

#### Manual Formatting (when Stage 4 fails)
```bash
# Format code
black .
isort .

# Re-attempt commit
git add -u
git commit -m "Your message"
```

#### Skip Pre-commit (Emergency Only)
```bash
git commit --no-verify -m "Emergency commit"
```

### Test Selection Examples

#### Example 1: Small Change
```
Changed files: calendarbot/utils/helpers.py
Related tests: tests/unit/test_helpers.py
Strategy: targeted (30 seconds)
```

#### Example 2: Medium Changes
```
Changed files: 3 files in calendarbot/web/
Related tests: 8 test files
Strategy: critical_path (5 minutes)
```

#### Example 3: Core Changes
```
Changed files: calendarbot/main.py, setup.py
Strategy: full_regression (20-30 minutes)
```

## Troubleshooting

### Common Issues

#### Security Scan Failures
```bash
# Issue: B605 shell injection detected
# Fix: Replace os.system() with subprocess.run()

# Before (vulnerable):
os.system("clear")

# After (secure):
subprocess.run(["clear"], check=False)
```

#### Type Check Failures
```bash
# Issue: MyPy type errors
# Fix: Add proper type annotations

# Before:
def process_data(data):
    return data.process()

# After:
def process_data(data: Dict[str, Any]) -> ProcessResult:
    return data.process()
```

#### Format Check Failures
```bash
# Issue: Code not formatted properly
# Fix: Run formatting tools
black .
isort .
git add -u
git commit -m "Your message"
```

#### Test Failures
```bash
# Issue: Tests failing in smart execution
# Fix: Address test failures based on strategy

# Targeted: Fix specific failing tests
# Critical Path: Ensure core functionality works
# Full Regression: Comprehensive test fixes needed
```

### Performance Issues

#### Slow Commits
- **Cause**: Full regression triggered by core file changes
- **Solution**: Consider breaking large changes into smaller commits

#### Test Selection Not Optimal
- **Check selection logic**: `python tests/suites/suite_manager.py smart`
- **Manual override**: Skip pre-commit for large refactoring, run tests separately

## Configuration Files

### Key Configuration Locations

- **Pre-commit config**: `.pre-commit-config.yaml`
- **Security settings**: `pyproject.toml` `[tool.bandit]`
- **Type checking**: `pyproject.toml` `[tool.mypy]`
- **Test markers**: `pyproject.toml` `[tool.pytest.ini_options]`
- **Smart test logic**: `tests/suites/suite_manager.py`

### Customization

#### Adjust Test Selection Thresholds
```python
# In tests/suites/suite_manager.py
elif len(related_tests) <= 5:  # Adjust threshold
    strategy = "targeted"
```

#### Modify Security Rules
```toml
# In pyproject.toml [tool.bandit]
skips = [
    "B101",  # Add rules to skip (carefully!)
]
```

#### Change Format Check Behavior
```yaml
# In .pre-commit-config.yaml
- id: black-check
  args: [--check, --diff]  # Modify arguments
```

## Benefits Summary

### ✅ Problems Solved
- **Cascade Failures**: Eliminated through check-only formatting
- **Slow Commits**: Optimized through smart test selection
- **Security Gaps**: Restored comprehensive Bandit scanning
- **Type Safety**: Full MyPy validation restored
- **Failed Tests**: Clear stages with focused remediation

### ✅ Performance Improvements
- **Fast Feedback**: Basic issues caught in < 10 seconds
- **Intelligent Testing**: Only run tests related to changes
- **Fail-Fast**: Stop at first issue to save time
- **Staged Execution**: Expensive operations only when needed

### ✅ Developer Experience
- **Predictable**: No unexpected file modifications
- **Informative**: Clear failure reasons and remediation steps
- **Flexible**: Manual override options for edge cases
- **Comprehensive**: Full quality gates without compromise

## Monitoring & Analytics

The TestSuiteManager provides execution analytics:

```bash
# View recent performance
python tests/suites/suite_manager.py analyze --days 7

# Check what changed recently
python tests/suites/suite_manager.py changed
```

This data helps optimize test selection thresholds and identify performance trends.
