# Python Setup Composite Action

## Overview

The `setup-python` composite action provides a standardized way to set up Python with dependency caching that can be used as a step in any GitHub Actions job. This promotes DRY (Don't Repeat Yourself) principles and ensures consistent Python environment setup.

## Location

`.github/actions/setup-python/action.yml`

## Features

- ✅ Configurable Python version (default: 3.12)
- ✅ Intelligent venv caching (based on requirements.txt and pyproject.toml)
- ✅ Optional dev dependencies installation
- ✅ Optional cache key suffix for job-specific caching
- ✅ Outputs Python version and cache hit status
- ✅ Uses latest actions/setup-python@v5
- ✅ Can be used as a step within any job

## Inputs

| Input | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `python-version` | string | No | `'3.12'` | Python version to use |
| `install-dev` | string | No | `'true'` | Install with dev dependencies (`.[dev]`) |
| `cache-key-suffix` | string | No | `''` | Optional suffix for cache key differentiation |

## Outputs

| Output | Description |
|--------|-------------|
| `python-version` | The Python version that was set up |
| `cache-hit` | Whether venv was restored from cache (`'true'` or `'false'`) |

## Usage Examples

### Basic Usage (Default Settings)

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: ./.github/actions/setup-python
      
      - name: Run tests
        run: pytest tests/
```

This will:
- Use Python 3.12
- Install with dev dependencies
- Cache the venv based on requirements.txt and pyproject.toml

### Custom Python Version

```yaml
steps:
  - uses: actions/checkout@v4
  
  - name: Setup Python 3.11
    uses: ./.github/actions/setup-python
    with:
      python-version: '3.11'
```

### Without Dev Dependencies

```yaml
steps:
  - uses: actions/checkout@v4
  
  - name: Setup Python (production only)
    uses: ./.github/actions/setup-python
    with:
      install-dev: 'false'
```

This installs only production dependencies (no pytest, ruff, mypy, etc.).

### With Cache Key Suffix

```yaml
steps:
  - uses: actions/checkout@v4
  
  - name: Setup Python for E2E tests
    uses: ./.github/actions/setup-python
    with:
      cache-key-suffix: 'e2e-tests'
```

Useful when you need separate caches for different jobs (e.g., unit tests vs e2e tests with additional dependencies).

### Using Outputs

```yaml
steps:
  - uses: actions/checkout@v4
  
  - name: Setup Python
    id: setup
    uses: ./.github/actions/setup-python
  
  - name: Check setup results
    run: |
      echo "Python version: ${{ steps.setup.outputs.python-version }}"
      echo "Cache was hit: ${{ steps.setup.outputs.cache-hit }}"
```

## Cache Behavior

The action caches the entire `venv` directory with a key based on:

1. Operating system (`runner.os`)
2. Python version (`inputs.python-version`)
3. Content hash of `requirements.txt` and `pyproject.toml`
4. Optional cache key suffix (`inputs.cache-key-suffix`)

**Cache Key Format:**
```
venv-{runner.os}-py{python-version}-{hash(requirements.txt, pyproject.toml)}[-{cache-key-suffix}]
```

**Example:**
```
venv-Linux-py3.12-a1b2c3d4e5f6-e2e-tests
```

The cache is automatically invalidated when dependencies change.

## Migration Guide

### Before (Repetitive Setup)

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - uses: actions/cache@v4
        with:
          path: venv
          key: venv-${{ runner.os }}-py3.12-${{ hashFiles('requirements.txt', 'pyproject.toml') }}
      - run: python -m venv venv
        if: steps.cache.outputs.cache-hit != 'true'
      - run: |
          echo "$PWD/venv/bin" >> $GITHUB_PATH
          echo "VIRTUAL_ENV=$PWD/venv" >> $GITHUB_ENV
      - run: |
          pip install --upgrade pip setuptools wheel
          pip install --prefer-binary -e .[dev]
        if: steps.cache.outputs.cache-hit != 'true'
      - run: pytest tests/
```

### After (Using Composite Action)

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup-python
      - run: pytest tests/
```

## Implementation Details

### What Gets Cached

- The entire `venv` directory including:
  - Python interpreter symlinks
  - Installed packages in `site-packages/`
  - pip metadata
  - setuptools entry points

### When Dependencies Are Installed

Dependencies are only installed when:
1. Cache miss occurs (first run or dependencies changed)
2. The installation steps check cache-hit status

### venv in PATH

The action sets two environment variables for subsequent steps:
- `GITHUB_PATH`: Adds `venv/bin` to PATH
- `VIRTUAL_ENV`: Points to the venv directory

This allows subsequent steps to use Python commands without explicitly activating the venv.

## Best Practices

1. **Use specific Python versions** - Avoid floating versions like `'3.x'`
2. **Match production Python version** - Use the same version as your deployment target
3. **Use cache-key-suffix sparingly** - Only when jobs truly need separate caches
4. **Monitor cache usage** - GitHub has 10GB cache limit per repository
5. **Keep dependencies pinned** - Use `requirements.txt` or lock files for reproducibility

## Troubleshooting

### Cache Not Being Used

Check that:
- Dependencies haven't changed (hash mismatch)
- Python version matches previous runs
- Cache hasn't expired (7 days unused)

### Installation Failures

If pip install fails:
- Check network connectivity
- Verify pyproject.toml syntax
- Check for version conflicts in dependencies
- Try clearing cache and re-running

### Wrong Python Version

Ensure:
- `python-version` input is set correctly
- No later steps override the Python setup

## Advantages Over Reusable Workflows

Unlike reusable workflows (which must be entire jobs), composite actions:
- ✅ Can be used as steps within a job
- ✅ Allow combining setup with other actions in the same job
- ✅ Simpler to use - just add as a step
- ✅ Better suited for setup tasks that are part of a larger job

## Related Files

- `.github/actions/setup-python/action.yml` - The composite action
- `.github/workflows/test-reusable-setup.yml` - Test workflow
- `docs/workflows/refactoring-example.md` - Before/after examples
- `pyproject.toml` - Project dependencies definition

## References

- [GitHub Composite Actions](https://docs.github.com/en/actions/creating-actions/creating-a-composite-action)
- [actions/setup-python](https://github.com/actions/setup-python)
- [actions/cache](https://github.com/actions/cache)
