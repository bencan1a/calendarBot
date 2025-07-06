# Development Guide

**Document Version:** 1.0
**Last Updated:** January 7, 2025
**System Version:** Calendar Bot v1.0.0 with Automated Development Setup

This guide covers setting up and working with Calendar Bot's development environment using the new automated setup system.

## 🚀 Quick Start: Automated Development Setup

Calendar Bot features a **complete automated development environment setup** that handles all dependencies, tools, and configurations:

### One-Command Development Setup

```bash
# Clone the repository
git clone <repository-url> calendarbot
cd calendarbot

# Run the automated development setup
python scripts/dev_setup.py
```

**That's it!** The automated development setup handles:
- ✅ Virtual environment creation and activation
- ✅ Development dependencies installation (`pip install -e .[dev]`)
- ✅ Code quality tools configuration (black, flake8, mypy, pytest)
- ✅ Pre-commit hooks setup
- ✅ IDE configuration files
- ✅ Development database initialization
- ✅ Environment validation and testing

## Table of Contents

- [Quick Start: Automated Development Setup](#-quick-start-automated-development-setup)
- [Development Environment Features](#development-environment-features)
- [Code Quality Tools](#code-quality-tools)
- [Testing Framework](#testing-framework)
- [Packaging Development](#packaging-development)
- [Contributing Guidelines](#contributing-guidelines)
- [Development Workflows](#development-workflows)
- [Troubleshooting](#troubleshooting)

## Development Environment Features

### Automated Setup Script (`scripts/dev_setup.py`)

The development setup script provides:

```python
# Key features of the automated development setup:
- Virtual environment management
- Editable package installation
- Development dependency resolution
- Code quality tool configuration
- Testing framework setup
- Documentation generation tools
- Development server configuration
```

### What Gets Installed

The automated setup installs all development tools:

```bash
# Core development dependencies
pip install -e .[dev]  # Installs the package in editable mode with dev extras

# Development tools included:
- pytest>=7.0.0          # Testing framework
- pytest-asyncio>=0.21.0 # Async testing support
- pytest-cov>=4.0.0      # Coverage reporting
- black>=23.0.0          # Code formatting
- flake8>=6.0.0          # Linting
- mypy>=1.0.0            # Type checking
- pre-commit>=3.0.0      # Git hooks
- sphinx>=6.0.0          # Documentation generation
- build>=0.10.0          # Package building
- twine>=4.0.0           # Package publishing
```

### Directory Structure

After running the automated setup:

```
calendarbot/
├── .venv/                    # Virtual environment (auto-created)
├── .git/hooks/               # Pre-commit hooks (auto-configured)
├── .pytest_cache/            # Test cache (auto-created)
├── .mypy_cache/              # Type checking cache (auto-created)
├── calendarbot/              # Main package
├── tests/                    # Test suite
├── scripts/
│   ├── dev_setup.py         # Automated development setup
│   └── deploy.py            # Deployment automation
├── docs/                     # Documentation
├── setup.py                 # Enhanced packaging with automation
├── pyproject.toml           # Modern Python packaging configuration
└── requirements-dev.txt     # Development dependencies
```

## Code Quality Tools

### Automated Code Formatting

**Black** is configured for consistent code formatting:

```bash
# Format all code (runs automatically in pre-commit)
black calendarbot/ tests/ scripts/

# Check formatting without making changes
black --check calendarbot/
```

Configuration in [`pyproject.toml`](pyproject.toml):
```toml
[tool.black]
line-length = 88
target-version = ['py38']
include = '\.pyi?$'
```

### Linting with Flake8

**Flake8** provides code quality checking:

```bash
# Run linting
flake8 calendarbot/ tests/ scripts/

# Configuration in setup.cfg or pyproject.toml
```

### Type Checking with MyPy

**MyPy** ensures type safety:

```bash
# Run type checking
mypy calendarbot/

# Check specific module
mypy calendarbot/setup_wizard.py
```

Configuration in [`pyproject.toml`](pyproject.toml):
```toml
[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### Pre-commit Hooks

Automated code quality checks run on every commit:

```yaml
# .pre-commit-config.yaml (auto-configured)
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
```

## Testing Framework

### Automated Test Setup

The development environment includes comprehensive testing:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=calendarbot

# Run specific test file
pytest tests/test_setup_wizard.py

# Run in verbose mode
pytest -v
```

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Test configuration and fixtures
├── test_setup_wizard.py     # Setup wizard tests
├── test_packaging.py        # Packaging system tests
├── test_ics_client.py       # ICS client tests
├── test_config.py           # Configuration tests
└── integration/             # Integration tests
    ├── test_full_setup.py   # End-to-end setup testing
    └── test_cli_commands.py # CLI command testing
```

### Test Configuration

Configured in [`pyproject.toml`](pyproject.toml):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=calendarbot",
    "--cov-report=term-missing"
]
```

## Packaging Development

### Testing the Packaging System

The automated development setup includes packaging validation:

```bash
# Test package building
python -m build

# Test installation in clean environment
python scripts/test_packaging.py

# Test the setup wizard
python -m calendarbot --setup --test-mode

# Validate package metadata
python setup.py check --metadata --strict
```

### Package Structure Validation

Key packaging components that are automatically tested:

- **Entry Points**: [`console_scripts`](setup.py) configuration
- **Setup Wizard**: [`calendarbot/setup_wizard.py`](calendarbot/setup_wizard.py) functionality
- **Post-install Hooks**: [`setup.py`](setup.py) automation
- **Dependencies**: [`pyproject.toml`](pyproject.toml) resolution
- **Module Loading**: [`calendarbot/__main__.py`](calendarbot/__main__.py) execution

### Development Installation

The automated setup installs the package in editable mode:

```bash
# Editable installation (done automatically by dev_setup.py)
pip install -e .[dev]

# Verify installation
calendarbot --version
calendarbot --help

# Test setup wizard
calendarbot --setup --dry-run
```

## Contributing Guidelines

### Development Workflow

1. **Start with Automated Setup**:
   ```bash
   git clone <repository-url> calendarbot
   cd calendarbot
   python scripts/dev_setup.py
   ```

2. **Create Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Develop with Quality Checks**:
   ```bash
   # Code changes are automatically checked by pre-commit hooks
   # Manual quality checks:
   black calendarbot/
   flake8 calendarbot/
   mypy calendarbot/
   pytest
   ```

4. **Test Packaging Changes**:
   ```bash
   # If you modify packaging components
   python scripts/test_packaging.py
   python -m build
   ```

5. **Submit Pull Request**:
   - All automated checks pass
   - Tests included for new features
   - Documentation updated

### Code Style Guidelines

- **Formatting**: Use Black with 88-character line length
- **Type Hints**: Required for all public APIs
- **Docstrings**: Google-style docstrings for all public functions
- **Testing**: Minimum 80% code coverage for new code
- **Documentation**: Update relevant `.md` files for user-facing changes

### Packaging System Contributions

When modifying the automated setup system:

1. **Test Setup Wizard Changes**:
   ```bash
   python -c "from calendarbot.setup_wizard import SetupWizard; SetupWizard().run_test_mode()"
   ```

2. **Validate Packaging Configuration**:
   ```bash
   python setup.py check --metadata --strict
   pip-compile pyproject.toml  # If you have pip-tools
   ```

3. **Test Cross-platform Compatibility**:
   - Test on Linux, macOS, Windows (if possible)
   - Verify console entry points work correctly
   - Check path handling and permissions

## Development Workflows

### Daily Development

```bash
# Start development session
cd calendarbot
source .venv/bin/activate  # Or activate virtual environment

# Run development server with auto-reload
calendarbot --web --dev-mode

# Run tests continuously
pytest --watch

# Format and check code before committing
black calendarbot/ && flake8 calendarbot/ && mypy calendarbot/
```

### Feature Development

```bash
# Create feature branch
git checkout -b feature/new-calendar-service

# Develop feature with automated validation
# (Pre-commit hooks ensure code quality)

# Test feature thoroughly
pytest tests/test_new_feature.py
python -m calendarbot --setup --dry-run  # Test setup wizard integration

# Validate packaging if setup.py or dependencies changed
python scripts/test_packaging.py
```

### Release Preparation

```bash
# Update version in setup.py and calendarbot/__init__.py
# Update documentation dates

# Run full test suite
pytest --cov=calendarbot --cov-report=html

# Test packaging
python -m build
python scripts/test_packaging.py

# Test installation in clean environment
python -m venv test_env
test_env/bin/pip install dist/calendarbot-*.whl
test_env/bin/calendarbot --setup --dry-run
```

## Troubleshooting

### Development Setup Issues

**Problem**: `scripts/dev_setup.py` fails
```bash
# Check Python version (3.8+ required)
python --version

# Ensure pip is up to date
python -m pip install --upgrade pip

# Check virtual environment creation
python -m venv test_venv
```

**Problem**: Pre-commit hooks failing
```bash
# Reinstall pre-commit hooks
pre-commit uninstall
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### Testing Issues

**Problem**: Tests failing after packaging changes
```bash
# Reinstall in editable mode
pip install -e .[dev]

# Clear pytest cache
rm -rf .pytest_cache/

# Run specific test with verbose output
pytest -v tests/test_setup_wizard.py::test_service_templates
```

### IDE Configuration

**VS Code** recommended settings (auto-created by dev setup):
```json
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true
}
```

**PyCharm** configuration:
- Set interpreter to `.venv/bin/python`
- Enable Black formatting
- Configure Flake8 and MyPy inspections

### Performance Development

**Memory Usage Monitoring**:
```bash
# Profile memory usage during development
python -m memory_profiler main.py

# Monitor during setup wizard
python -c "from calendarbot.setup_wizard import SetupWizard; import tracemalloc; tracemalloc.start(); w = SetupWizard(); w.run_test_mode(); print(tracemalloc.get_traced_memory())"
```

---

## Next Steps

After setting up your development environment:

1. **Explore the Setup Wizard**: Run [`calendarbot --setup --dry-run`] to understand the user experience
2. **Review Packaging Code**: Study [`setup.py`](setup.py) and [`calendarbot/setup_wizard.py`](calendarbot/setup_wizard.py)
3. **Run the Test Suite**: Execute `pytest` to understand test coverage
4. **Check Documentation**: Review [`SETUP.md`](SETUP.md) and [`INSTALL.md`](INSTALL.md) for user perspectives
5. **Try Different Scenarios**: Test with various calendar services and configurations

---

**🛠️ Development Environment Ready!** You now have a fully automated development setup for Calendar Bot.

**📖 Need Help?** Check the [main documentation](README.md) or [create an issue](https://github.com/your-repo/calendarBot/issues) for development questions.

---

*Development Guide v1.0 - Last updated January 7, 2025*
*Built with automated setup system - From 20+ manual steps to 1 command*