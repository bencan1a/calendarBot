# GitHub Workflows Documentation

This directory contains documentation for GitHub Actions workflows used in the CalendarBot project.

## Available Documentation

### [Python Setup Composite Action](reusable-setup.md)
Comprehensive guide for the Python setup composite action that standardizes Python environment configuration across all workflows.

**Key Features:**
- Configurable Python version
- Intelligent venv caching
- Optional dev dependencies
- Cache key differentiation
- Can be used as a step in any job

**Quick Start:**
```yaml
steps:
  - uses: actions/checkout@v4
  - uses: ./.github/actions/setup-python
  - run: pytest tests/
```

### [Refactoring Examples](refactoring-example.md)
Before/after examples showing how to refactor existing workflows to use the Python setup composite action.

**Benefits:**
- Drastically reduces duplication
- Single source of truth
- Easier maintenance
- Consistent setup
- Simple to use as a step

## Composite Actions

Composite actions are located in `.github/actions/`:

- **setup-python/** - Python setup with caching composite action

## Workflow Files

The actual workflow files are located in `.github/workflows/`:

- **test-reusable-setup.yml** - Test workflow for the Python setup action
- **ci.yml** - Main CI/CD pipeline
- **nightly-full-suite.yml** - Nightly full test suite
- **e2e-kiosk.yml** - End-to-end kiosk installation tests

## Related Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Composite Actions](https://docs.github.com/en/actions/creating-actions/creating-a-composite-action)
- [actions/setup-python](https://github.com/actions/setup-python)
- [actions/cache](https://github.com/actions/cache)
