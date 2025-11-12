# Example: Refactoring to Use Python Setup Action

This document demonstrates how to refactor an existing workflow to use the Python setup composite action.

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

## After: Using Composite Action

The composite action can be used as a single step in any job, replacing all the setup boilerplate:

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
    - uses: actions/checkout@v4
    - uses: ./.github/actions/setup-python
    - run: ruff check calendarbot_lite

  test:
    name: Run Tests
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: ./.github/actions/setup-python
    - run: pytest tests/lite/ -v
```

**Benefits:**
- ✅ Single source of truth for Python setup
- ✅ Drastically reduces duplication (6 steps total vs 24)
- ✅ Easy to update (change once, affects all workflows)
- ✅ Consistent setup across all jobs
- ✅ Cleaner, more readable workflow files
- ✅ Each job independently benefits from intelligent caching
- ✅ Can be combined with other steps in the same job

## Advanced Usage

### Different Python Versions

```yaml
jobs:
  test-py312:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup-python
        with:
          python-version: '3.12'
      - run: pytest tests/

  test-py311:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup-python
        with:
          python-version: '3.11'
      - run: pytest tests/
```

### Production vs Dev Dependencies

```yaml
jobs:
  build-production:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup-python
        with:
          install-dev: 'false'  # Production dependencies only
      - run: python -m build

  run-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup-python
        with:
          install-dev: 'true'   # Dev dependencies for testing
      - run: pytest tests/
```

### Separate Caches for Different Jobs

```yaml
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup-python
        with:
          cache-key-suffix: 'unit'
      - run: pytest tests/unit/

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup-python
        with:
          cache-key-suffix: 'e2e'
      - run: pip install selenium  # Additional E2E dependencies
      - run: pytest tests/e2e/
```

## Migration Checklist

When refactoring an existing workflow:

- [ ] Identify all Python setup steps in your workflow
- [ ] Replace setup steps with `uses: ./.github/actions/setup-python`
- [ ] Verify Python version matches your requirements
- [ ] Confirm dev dependencies requirement (default is true)
- [ ] Test the refactored workflow
- [ ] Check cache behavior is working correctly
- [ ] Verify all dependent jobs still work

## Why Composite Actions?

Composite actions offer several advantages for this use case:

- **Flexibility**: Can be used as a step within any job
- **Simplicity**: Just add one line to use complete setup
- **Composability**: Easily combine with other actions and steps
- **No job overhead**: Runs in the same job, no separate runner needed
- **Direct outputs**: Access outputs immediately in the same job

Compared to reusable workflows (which must be entire jobs), composite actions are better suited for setup tasks that are part of a larger workflow.
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
