# Contributing to CalendarBot

Welcome! This guide will help you get started contributing to CalendarBot.

---

## What is CalendarBot?

**CalendarBot Lite** is a lightweight Alexa skill backend and web API for ICS calendar processing. It fetches and parses RFC 5545-compliant calendar feeds, expands recurring events using RRULE processing, and provides natural language calendar responses via Alexa.

**Primary Use Cases:**
- 🖥️ **Raspberry Pi Kiosk Deployment** - Production-ready display system with auto-login and watchdog monitoring (PRIMARY production use case)
- 🗣️ **Alexa Integration** - Voice-activated calendar queries
- 📺 **Web API** - REST endpoints for calendar data and health monitoring

### Project Scale

CalendarBot is a **personal project designed for resource-constrained hardware**:
- **Users**: 1-5 users maximum
- **Target Hardware**: Raspberry Pi Zero 2W (1GB RAM, quad-core ARM processor)
- **Philosophy**: Keep it simple, optimize for efficiency, no over-engineering

See [AGENTS.md - Application Context & Scale](AGENTS.md#-application-context--scale) for complete development philosophy.

---

## Getting Started

### Prerequisites

- **Python 3.12+** - Required by the project
- **Git** - For version control
- **Virtual Environment Support** - Python venv (standard library)

### Initial Setup

```bash
# 1. Clone the repository
git clone https://github.com/bencan1a/calendarbot.git
cd calendarbot

# 2. Create and activate virtual environment
python3.12 -m venv venv
. venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# 3. Install development dependencies
pip install -e '.[dev]'

# 4. Configure environment
cp .env.example .env
# Edit .env with your ICS_URL and other settings
nano .env  # or your preferred editor
```

### Virtual Environment

**Always activate the virtual environment before running any Python commands:**

```bash
. venv/bin/activate  # Linux/macOS
source venv/bin/activate  # Alternative
venv\Scripts\activate  # Windows
```

You'll see `(venv)` in your shell prompt when active. To deactivate: `deactivate`

---

## Development Workflow

### Running the Server

```bash
# Start the CalendarBot Lite server
python -m calendarbot_lite

# Server runs on http://localhost:8080 by default
# Configure with CALENDARBOT_WEB_PORT in .env
```

### Code Quality Checks

We use several tools to maintain code quality:

```bash
# Format Python code with ruff (auto-fixes style issues)
make format

# Run linter (auto-fixes most issues)
make lint

# Check linting without auto-fixing
make lint-check

# Run type checker (mypy)
make typecheck

# Run security scanner (bandit)
make security

# Validate YAML files
make check-yaml

# Run ALL quality checks
make check
```

### Quick Test & Check

```bash
# Pre-commit checks (what we recommend before pushing)
# Runs: format, lint, typecheck, and fast tests
make precommit

# Full test suite with coverage
make test-coverage

# Fast tests only (exclude slow tests)
make test-fast
```

### Available Make Targets

```bash
make help  # Show all available targets
```

Key targets:
- `make install` - Install dependencies
- `make serve` - Run the server
- `make test` - Run all tests
- `make test-coverage` - Run tests with coverage report
- `make test-unit` - Run unit tests only
- `make test-fast` - Run fast tests (exclude slow)
- `make test-smoke` - Run smoke tests
- `make format` - Format code
- `make lint` - Lint and auto-fix
- `make typecheck` - Type checking
- `make security` - Security scan
- `make check` - All quality checks
- `make precommit` - Pre-commit checks
- `make clean` - Clean build artifacts
- `make pre-commit-install` - Install git hooks
- `make pre-commit-run` - Run hooks on all files

### Pre-commit Hooks (Optional)

Install git hooks to automatically run checks before commits:

```bash
make pre-commit-install

# Hooks will now run automatically when you commit
# To run manually on all files:
make pre-commit-run
```

---

## Testing

### Running Tests

Tests are in the `tests/lite/` directory and are organized by test type.

```bash
# Run all tests
./run_lite_tests.sh

# Run with coverage report
./run_lite_tests.sh --coverage

# Run specific test categories
./run_lite_tests.sh -m unit         # Unit tests only
./run_lite_tests.sh -m smoke        # Smoke tests only
./run_lite_tests.sh -m "not slow"   # Everything except slow tests

# Run specific test file
pytest tests/lite/test_event_parser.py -v

# Run with pytest directly
pytest tests/lite/ -v
```

### Test Markers

Tests are marked with categories to allow selective execution:

- `unit` - Fast unit tests (recommended for pre-commit)
- `integration` - Tests requiring external dependencies
- `smoke` - Basic functionality verification
- `slow` - Long-running tests (excluded from `make test-fast`)
- `e2e` - End-to-end tests

### Coverage Threshold

- **Minimum**: 70% coverage of `calendarbot_lite/` code
- **View Report**: `make test-coverage` generates an HTML report in `htmlcov/`

### Test Quality Standards

All tests in this project follow strict quality standards:

1. **Tests Must Fail When Implementation Breaks** - The golden rule: if you comment out the implementation, the test MUST fail
2. **Unconditional Assertions** - No `if` statements in test bodies; all assertions must execute
3. **One Outcome Per Test** - Each test verifies ONE specific behavior
4. **Mock External I/O** - Mock HTTP, filesystem, and time operations; don't mock business logic
5. **Descriptive Names** - Test names should describe what's being tested

See [docs/pytest-best-practices.md](docs/pytest-best-practices.md) for complete testing guidelines with examples.

---

## Code Style & Quality

### Formatting with Ruff

Ruff formats Python code to a consistent standard:

```bash
make format  # Auto-format calendarbot_lite/
```

Configuration: [pyproject.toml#L136-L237](pyproject.toml#L136)
- **Line length**: 100 characters
- **Target Python**: 3.12
- **Quote style**: Double quotes
- **Indentation**: 4 spaces

### Linting with Ruff

Ruff checks for code issues and enforces style rules:

```bash
make lint        # Run linter and auto-fix issues
make lint-check  # Check without fixing
```

Configuration: [pyproject.toml#L160-L211](pyproject.toml#L160)

Enabled checks include: pycodestyle, Pyflakes, pyupgrade, flake8-bugbear, flake8-simplify, isort, naming conventions, and more.

### Type Checking with MyPy

MyPy performs static type checking:

```bash
make typecheck
```

Configuration: [pyproject.toml#L253-L302](pyproject.toml#L253)
- **Python version**: 3.12
- **Strict mode**: Enabled
- **Source**: `calendarbot_lite/` only

### Security Scanning with Bandit

Bandit identifies security issues:

```bash
make security
```

Configuration: [pyproject.toml#L239-L251](pyproject.toml#L239)
- **Scope**: `calendarbot_lite/` only
- **Severity**: Medium and high issues flagged

### YAML Validation

Validates YAML syntax in configuration files:

```bash
make check-yaml
```

---

## Pull Request Process

### Before You Start

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes in `calendarbot_lite/` (the active codebase)

### Before Pushing

```bash
# Run pre-commit checks (recommended)
make precommit

# This runs: format → lint → typecheck → fast tests
# Fix any issues it reports, then commit
```

### Commit Messages

Write clear, descriptive commit messages:

```
Short (50 chars or less) summary of changes

Longer description explaining WHY the changes were made,
not WHAT they do (the diff shows that). Mention any
related issues: Fixes #123
```

### Creating the PR

1. Push your branch: `git push origin feature/your-feature-name`
2. Open a pull request on GitHub
3. Include a description of the changes and why they're needed
4. Link any related issues: "Fixes #123"
5. Wait for CI checks to pass

### After Submission

- CI will automatically run all quality checks
- Respond to any review feedback
- Keep commits clean and well-organized
- Don't force-push unless absolutely necessary

---

## File Organization

When creating new files, follow these conventions:

### Temporary/Debug Files

Place temporary or debug scripts in `tmp/` (gitignored):

```bash
# Debug script
tmp/debug_rrule_expansion.py

# Analysis output
tmp/performance_profile.txt

# Scratch work
tmp/test_calculations.py
```

### Project Documentation

Place permanent documentation in `docs/`:

```bash
# Feature documentation
docs/FEATURE_NAME.md

# Architecture decisions
docs/ARCHITECTURE.md

# Setup guides
docs/INSTALLATION.md
```

### Code Organization

- `calendarbot_lite/` - **ACTIVE** project code
  - `server.py` - Web server and background tasks
  - `routes/` - HTTP endpoints
  - `alexa_*.py` - Alexa integration
  - `lite_event_parser.py` - ICS parsing
  - `lite_rrule_expander.py` - Recurring event expansion

- `tests/lite/` - Test code for calendarbot_lite
  - Mirror structure of source code
  - Test files: `test_*.py`

- `kiosk/` - Raspberry Pi kiosk deployment
  - `install-kiosk.sh` - Automated installer
  - `docs/` - Kiosk documentation
  - `config/` - Configuration files
  - `service/` - systemd unit files

---

## Key Resources

### Essential Documentation

- **[AGENTS.md](AGENTS.md)** - Complete development guide with all commands and patterns
- **[CLAUDE.md](CLAUDE.md)** - Quick reference for AI agents
- **[README.md](README.md)** - Project overview and features
- **[Makefile](Makefile)** - All available commands

### Testing & Quality

- **[docs/pytest-best-practices.md](docs/pytest-best-practices.md)** - Detailed testing guidelines with examples
- **[pyproject.toml](pyproject.toml)** - Tool configurations (pytest, coverage, ruff, mypy, bandit)

### Deployment & Operations

- **[kiosk/README.md](kiosk/README.md)** - Kiosk system overview
- **[kiosk/docs/AUTOMATED_INSTALLATION.md](kiosk/docs/AUTOMATED_INSTALLATION.md)** - Kiosk installation
- **[docs/PI_ZERO_2_MONITORING_GUIDE.md](docs/PI_ZERO_2_MONITORING_GUIDE.md)** - Raspberry Pi monitoring

---

## Troubleshooting

### Virtual Environment Issues

```bash
# If commands don't work, make sure venv is activated
which python  # Should show path to venv/bin/python

# Recreate venv if corrupted
rm -rf venv
python3.12 -m venv venv
. venv/bin/activate
pip install -e '.[dev]'
```

### Dependency Issues

```bash
# Update pip
pip install --upgrade pip

# Reinstall dependencies
pip install -e '.[dev]' --force-reinstall

# Clear pip cache
pip cache purge
```

### Test Issues

```bash
# Clean pytest cache
make clean

# Run with verbose output
pytest tests/lite/ -vv

# Run with debug output
pytest tests/lite/ -vv -s
```

### Type Checking Issues

```bash
# Clear mypy cache
rm -rf .mypy_cache

# Run mypy with verbose output
mypy calendarbot_lite --show-traceback
```

---

## Questions?

- Check **[AGENTS.md](AGENTS.md)** for detailed development guidance
- Check **[README.md](README.md)** for project overview
- Review **[docs/](docs/)** for topic-specific documentation
- Open an issue on GitHub for questions or problems

---

## Code of Conduct

Be respectful, professional, and constructive. This is a personal project, and we want to maintain a friendly, inclusive environment for all contributors.

---

**Last Updated**: 2025-11-12
**Active Project**: calendarbot_lite/
**For Detailed Guidance**: See [AGENTS.md](AGENTS.md)
