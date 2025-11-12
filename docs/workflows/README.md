# GitHub Workflows Documentation

This directory contains documentation for GitHub Actions workflows used in the CalendarBot project.

## Available Documentation

### [Reusable Python Setup](reusable-setup.md)
Comprehensive guide for the reusable Python setup workflow that standardizes Python environment configuration across all workflows.

**Key Features:**
- Configurable Python version
- Intelligent venv caching
- Optional dev dependencies
- Cache key differentiation

**Quick Start:**
```yaml
jobs:
  my-job:
    uses: ./.github/workflows/reusable-setup.yml
```

### [Refactoring Examples](refactoring-example.md)
Before/after examples showing how to refactor existing workflows to use the reusable Python setup workflow.

**Benefits:**
- Reduces duplication
- Single source of truth
- Easier maintenance
- Consistent setup

## Workflow Files

The actual workflow files are located in `.github/workflows/`:

- **reusable-setup.yml** - Reusable Python setup workflow
- **test-reusable-setup.yml** - Test workflow for the reusable setup
- **ci.yml** - Main CI/CD pipeline
- **nightly-full-suite.yml** - Nightly full test suite
- **e2e-kiosk.yml** - End-to-end kiosk installation tests

## Validation

To validate all YAML workflow files:

```bash
make check-yaml
```

This runs `scripts/validate_yaml.py` which checks syntax of all workflows.

## Related Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Reusable Workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows)
- [actions/setup-python](https://github.com/actions/setup-python)
- [actions/cache](https://github.com/actions/cache)
