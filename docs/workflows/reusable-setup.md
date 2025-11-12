# Reusable Python Setup Workflow

## Overview

The `reusable-setup.yml` workflow provides a standardized way to set up Python with dependency caching across all GitHub Actions workflows. This promotes DRY (Don't Repeat Yourself) principles and ensures consistent Python environment setup.

## Location

`.github/workflows/reusable-setup.yml`

## Features

- ✅ Configurable Python version (default: 3.12)
- ✅ Intelligent venv caching (based on requirements.txt and pyproject.toml)
- ✅ Optional dev dependencies installation
- ✅ Optional cache key suffix for workflow-specific caching
- ✅ Outputs Python version and cache hit status
- ✅ Uses latest actions/setup-python@v5

## Inputs

| Input | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `python-version` | string | No | `'3.12'` | Python version to use |
| `install-dev` | boolean | No | `true` | Install with dev dependencies (`.[dev]`) |
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
  my-job:
    uses: ./.github/workflows/reusable-setup.yml
```

This will:
- Use Python 3.12
- Install with dev dependencies
- Cache the venv based on requirements.txt and pyproject.toml

### Custom Python Version

```yaml
jobs:
  my-job:
    uses: ./.github/workflows/reusable-setup.yml
    with:
      python-version: '3.11'
```

### Without Dev Dependencies

```yaml
jobs:
  my-job:
    uses: ./.github/workflows/reusable-setup.yml
    with:
      install-dev: false
```

This installs only production dependencies (no pytest, ruff, mypy, etc.).

### With Cache Key Suffix

```yaml
jobs:
  my-job:
    uses: ./.github/workflows/reusable-setup.yml
    with:
      cache-key-suffix: 'e2e-tests'
```

Useful when you need separate caches for different workflows (e.g., unit tests vs e2e tests with additional dependencies).

### Full Configuration

```yaml
jobs:
  my-job:
    uses: ./.github/workflows/reusable-setup.yml
    with:
      python-version: '3.12'
      install-dev: true
      cache-key-suffix: 'custom-suffix'
```

### Using Outputs

```yaml
jobs:
  setup:
    uses: ./.github/workflows/reusable-setup.yml
    with:
      python-version: '3.12'

  test:
    needs: setup
    runs-on: ubuntu-latest
    steps:
      - name: Check Python version
        run: |
          echo "Python version used: ${{ needs.setup.outputs.python-version }}"
          echo "Cache was hit: ${{ needs.setup.outputs.cache-hit }}"
```

## Cache Behavior

The workflow caches the entire `venv` directory with a key based on:

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
      - uses: actions/setup-python@v4
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
```

### After (Using Reusable Workflow)

```yaml
jobs:
  test:
    uses: ./.github/workflows/reusable-setup.yml
```

## Validation

To validate YAML syntax of all workflows:

```bash
make check-yaml
```

Or directly:

```bash
python3 scripts/validate_yaml.py
```

## Testing

A test workflow is available to verify the reusable setup works correctly:

```bash
# Trigger test workflow via GitHub UI or CLI
gh workflow run test-reusable-setup.yml
```

The test workflow validates:
- Default setup with dev dependencies
- Setup without dev dependencies
- Setup with custom cache key suffix
- Cache functionality
- Python version and dependency availability

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
2. The installation steps check `steps.venv-cache.outputs.cache-hit != 'true'`

### venv in PATH

The workflow sets two environment variables for subsequent steps:
- `GITHUB_PATH`: Adds `venv/bin` to PATH
- `VIRTUAL_ENV`: Points to the venv directory

This allows subsequent steps to use Python commands without explicitly activating the venv.

## Best Practices

1. **Use specific Python versions** - Avoid floating versions like `'3.x'`
2. **Match production Python version** - Use the same version as your deployment target
3. **Use cache-key-suffix sparingly** - Only when workflows truly need separate caches
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

## Future Improvements

Potential enhancements:
- Support for poetry/pipenv
- Conditional installation of optional dependency groups
- Pre-commit hook caching
- Tox environment caching
- Multiple Python version matrix support

## Related Files

- `.github/workflows/reusable-setup.yml` - The reusable workflow
- `.github/workflows/test-reusable-setup.yml` - Test workflow
- `scripts/validate_yaml.py` - YAML validation script
- `Makefile` - Contains `check-yaml` target
- `pyproject.toml` - Project dependencies definition

## References

- [GitHub Reusable Workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [actions/setup-python](https://github.com/actions/setup-python)
- [actions/cache](https://github.com/actions/cache)
