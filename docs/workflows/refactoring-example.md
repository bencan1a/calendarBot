# Example: Refactoring to Use Reusable Setup

This document demonstrates how to refactor an existing workflow to use the reusable Python setup workflow.

## Before: Traditional Approach

```yaml
name: Example Workflow

on:
  push:
    branches: [ main ]
  pull_request:

jobs:
  lint:
    name: Lint Code
    runs-on: ubuntu-latest
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python 3.12
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Cache virtual environment
      uses: actions/cache@v4
      id: venv-cache
      with:
        path: venv
        key: venv-${{ runner.os }}-py3.12-${{ hashFiles('requirements.txt', 'pyproject.toml') }}
        restore-keys: |
          venv-${{ runner.os }}-py3.12-

    - name: Create virtual environment
      if: steps.venv-cache.outputs.cache-hit != 'true'
      run: python -m venv venv

    - name: Set venv in PATH
      run: |
        echo "$PWD/venv/bin" >> $GITHUB_PATH
        echo "VIRTUAL_ENV=$PWD/venv" >> $GITHUB_ENV

    - name: Install dependencies
      if: steps.venv-cache.outputs.cache-hit != 'true'
      run: |
        pip install --upgrade pip setuptools wheel
        pip install --prefer-binary -e .[dev]

    - name: Run linting
      run: ruff check calendarbot_lite

  test:
    name: Run Tests
    runs-on: ubuntu-latest
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python 3.12
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Cache virtual environment
      uses: actions/cache@v4
      id: venv-cache
      with:
        path: venv
        key: venv-${{ runner.os }}-py3.12-${{ hashFiles('requirements.txt', 'pyproject.toml') }}
        restore-keys: |
          venv-${{ runner.os }}-py3.12-

    - name: Create virtual environment
      if: steps.venv-cache.outputs.cache-hit != 'true'
      run: python -m venv venv

    - name: Set venv in PATH
      run: |
        echo "$PWD/venv/bin" >> $GITHUB_PATH
        echo "VIRTUAL_ENV=$PWD/venv" >> $GITHUB_ENV

    - name: Install dependencies
      if: steps.venv-cache.outputs.cache-hit != 'true'
      run: |
        pip install --upgrade pip setuptools wheel
        pip install --prefer-binary -e .[dev]

    - name: Run tests
      run: pytest tests/lite/ -v
```

**Problems with this approach:**
- 🔴 Duplicated setup steps (12 steps × 2 jobs = 24 steps)
- 🔴 Hard to maintain (changes must be replicated)
- 🔴 Inconsistency risk (easy to forget updates)
- 🔴 Verbose and cluttered workflow file

## After: Using Reusable Workflow

```yaml
name: Example Workflow

on:
  push:
    branches: [ main ]
  pull_request:

jobs:
  # Setup Python once, share across jobs
  setup:
    name: Setup Python Environment
    uses: ./.github/workflows/reusable-setup.yml
    with:
      python-version: '3.12'
      install-dev: true

  lint:
    name: Lint Code
    needs: setup
    runs-on: ubuntu-latest
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python 3.12
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'

    - name: Cache virtual environment
      uses: actions/cache@v4
      with:
        path: venv
        key: venv-${{ runner.os }}-py3.12-${{ hashFiles('requirements.txt', 'pyproject.toml') }}
        restore-keys: |
          venv-${{ runner.os }}-py3.12-

    - name: Set venv in PATH
      run: |
        echo "$PWD/venv/bin" >> $GITHUB_PATH
        echo "VIRTUAL_ENV=$PWD/venv" >> $GITHUB_ENV

    - name: Run linting
      run: ruff check calendarbot_lite

  test:
    name: Run Tests
    needs: setup
    runs-on: ubuntu-latest
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python 3.12
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'

    - name: Cache virtual environment
      uses: actions/cache@v4
      with:
        path: venv
        key: venv-${{ runner.os }}-py3.12-${{ hashFiles('requirements.txt', 'pyproject.toml') }}
        restore-keys: |
          venv-${{ runner.os }}-py3.12-

    - name: Set venv in PATH
      run: |
        echo "$PWD/venv/bin" >> $GITHUB_PATH
        echo "VIRTUAL_ENV=$PWD/venv" >> $GITHUB_ENV

    - name: Run tests
      run: pytest tests/lite/ -v
```

**Benefits:**
- ✅ Single source of truth for Python setup
- ✅ Reduces duplication (setup job handles all setup logic)
- ✅ Easy to update (change once, affects all workflows)
- ✅ Consistent setup across all jobs
- ✅ Cleaner, more readable workflow files
- ✅ Cache is populated once and shared

**Note:** Each job still needs to restore the cache and set up PATH, but the
heavy lifting (venv creation and dependency installation) is done once.

## Even Better: Per-Job Setup

For truly independent jobs, use the reusable workflow directly in each job:

```yaml
name: Example Workflow

on:
  push:
    branches: [ main ]
  pull_request:

jobs:
  lint:
    name: Lint Code
    uses: ./.github/workflows/reusable-setup.yml
    with:
      python-version: '3.12'
      install-dev: true

  # Can run a custom job after setup
  lint-check:
    name: Run Linting
    needs: lint
    runs-on: ubuntu-latest
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'

    - name: Restore cache
      uses: actions/cache@v4
      with:
        path: venv
        key: venv-${{ runner.os }}-py3.12-${{ hashFiles('requirements.txt', 'pyproject.toml') }}

    - name: Set venv in PATH
      run: |
        echo "$PWD/venv/bin" >> $GITHUB_PATH
        echo "VIRTUAL_ENV=$PWD/venv" >> $GITHUB_ENV

    - name: Run linting
      run: ruff check calendarbot_lite
```

## Best Practice: Composite Setup

For even more reusability, you could also create a composite action for the
cache restoration steps. However, the reusable workflow is simpler for most cases.

## Migration Checklist

When refactoring an existing workflow:

- [ ] Identify all Python setup steps
- [ ] Replace with reusable workflow call
- [ ] Verify Python version matches
- [ ] Confirm dev dependencies requirement
- [ ] Test the refactored workflow
- [ ] Check cache behavior is correct
- [ ] Verify job dependencies are preserved
- [ ] Update any workflow-specific cache keys if needed

## Common Patterns

### Pattern 1: Different Python Versions

```yaml
jobs:
  test-py312:
    uses: ./.github/workflows/reusable-setup.yml
    with:
      python-version: '3.12'

  test-py311:
    uses: ./.github/workflows/reusable-setup.yml
    with:
      python-version: '3.11'
```

### Pattern 2: Production vs Dev

```yaml
jobs:
  build-production:
    uses: ./.github/workflows/reusable-setup.yml
    with:
      install-dev: false  # Production dependencies only

  run-tests:
    uses: ./.github/workflows/reusable-setup.yml
    with:
      install-dev: true   # Dev dependencies for testing
```

### Pattern 3: Separate Caches

```yaml
jobs:
  unit-tests:
    uses: ./.github/workflows/reusable-setup.yml
    with:
      cache-key-suffix: 'unit'

  e2e-tests:
    uses: ./.github/workflows/reusable-setup.yml
    with:
      cache-key-suffix: 'e2e'
      # E2E might install additional dependencies
```
