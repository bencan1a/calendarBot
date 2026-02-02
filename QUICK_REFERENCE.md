# CalendarBot Quick Reference

Fast lookup for common commands and workflows. See [AGENTS.md](AGENTS.md) for complete development guide.

---

## Quick Setup

```bash
# Activate virtual environment
. venv/bin/activate

# Install dependencies
pip install -e '.[dev]'

# Configure environment
cp .env.example .env
# Edit .env with your settings (ICS_URL required)
```

---

## Essential Commands

| Task | Command | Notes |
|------|---------|-------|
| Run server | `python -m calendarbot_lite` or `make serve` | Binds to 0.0.0.0:8080 by default |
| Run all tests | `./run_lite_tests.sh` or `make test` | Tests in tests/lite/ |
| Tests with coverage | `./run_lite_tests.sh --coverage` or `make test-coverage` | HTML report: htmlcov-lite/ |
| Format code | `make format` | Uses ruff formatter |
| Check linting | `make lint-check` | Ruff linter (read-only) |
| Auto-fix linting | `make lint` | Ruff with auto-fix |
| Type check | `make typecheck` | MyPy type checking |
| Security scan | `make security` | Bandit vulnerability scan |
| Full quality check | `make check` | YAML + lint + type + security |
| Pre-commit checks | `make precommit` | Format + lint + type + fast tests |

---

## Testing Commands

Run specific test suites with markers:

```bash
# Run all tests
./run_lite_tests.sh

# Run with coverage report
./run_lite_tests.sh --coverage

# Run unit tests only
./run_lite_tests.sh -m unit
# Shortcut: make test-unit

# Run fast tests (exclude slow)
./run_lite_tests.sh -m "not slow"
# Shortcut: make test-fast

# Run smoke tests
./run_lite_tests.sh -m smoke
# Shortcut: make test-smoke

# Run with verbose output
./run_lite_tests.sh -v

# Combine options
./run_lite_tests.sh -m unit -v --coverage
```

---

## Makefile Targets Reference

### Code Quality

| Target | Description |
|--------|-------------|
| `format` | Format Python code with ruff |
| `lint` | Run ruff linter with auto-fix |
| `lint-check` | Check linting without auto-fix |
| `typecheck` | Run MyPy type checker |
| `security` | Run Bandit security scanner |
| `check-yaml` | Validate YAML syntax in all files |

### Testing

| Target | Description |
|--------|-------------|
| `test` | Run all tests |
| `test-coverage` | Run tests with coverage report |
| `test-unit` | Run unit tests only |
| `test-fast` | Run fast tests (exclude slow) |
| `test-smoke` | Run smoke tests |

### Combined Commands

| Target | Description |
|--------|-------------|
| `check` | All quality checks (YAML, lint, type, security) |
| `precommit` | Pre-commit checks (format, lint, type, fast tests) |

### Setup & Management

| Target | Description |
|--------|-------------|
| `install` | Install full dev dependencies |
| `install-test` | Install test dependencies only |
| `serve` | Run CalendarBot Lite server |
| `clean` | Clean build artifacts and cache files |
| `pre-commit-install` | Install pre-commit hooks |
| `pre-commit-run` | Run pre-commit hooks on all files |
| `help` | Show help message |

---

## Code Quality Workflow

```bash
# Format and lint (fixes auto-fixable issues)
make format lint

# Type check and security scan
make typecheck security

# Run all checks together
make check

# Pre-commit workflow
make precommit
```

---

## Debugging

### Run with Debug Logging

```bash
# Set environment variable
export CALENDARBOT_DEBUG=true
python -m calendarbot_lite
```

### Test Specific File

```bash
# Run tests for a specific file
pytest tests/lite/test_file.py -v

# Run specific test function
pytest tests/lite/test_file.py::test_function_name -v
```

### Coverage Report

```bash
# Generate coverage report
./run_lite_tests.sh --coverage

# View HTML report
open htmlcov-lite/index.html  # macOS
xdg-open htmlcov-lite/index.html  # Linux
```

### View Test Output

```bash
# Verbose output
./run_lite_tests.sh -v

# Show print statements
./run_lite_tests.sh -v -s
```

---

## Environment Configuration

Create `.env` from `.env.example` and configure:

### Required Variables

- `CALENDARBOT_ICS_URL` - ICS calendar feed URL (required)

### Common Configuration

- `CALENDARBOT_WEB_HOST` - Server host (default: 0.0.0.0)
- `CALENDARBOT_WEB_PORT` - Server port (default: 8080)
- `CALENDARBOT_REFRESH_INTERVAL` - Refresh interval in seconds (default: 300)
- `CALENDARBOT_DEFAULT_TIMEZONE` - Timezone (default: America/Los_Angeles)

### Optional Features

- `CALENDARBOT_ALEXA_BEARER_TOKEN` - Alexa integration token
- `CALENDARBOT_DEBUG` - Enable debug logging
- `CALENDARBOT_LOG_LEVEL` - Logging level (INFO, DEBUG, etc.)

See `.env.example` for complete configuration options.

---

## Project Structure

```
calendarbot_lite/          # ACTIVE - Main application
├── server.py              # Web server and background tasks
├── routes/                # HTTP endpoints (Alexa, API, static)
├── alexa_*.py            # Alexa integration modules
├── lite_event_parser.py   # ICS parsing
└── lite_rrule_expander.py # Recurring event expansion

kiosk/                      # PRIMARY PRODUCTION - Raspberry Pi deployment
├── install-kiosk.sh       # Automated installer
├── README.md              # Kiosk documentation
└── docs/                  # Installation guides

tests/
├── lite/                  # Main test directory (pytest)
└── spec_runners/          # YAML-based API validators

docs/                       # Documentation
scripts/                    # Development scripts
tmp/                        # Temporary files (gitignored)
```

---

## CI/CD & Pre-commit

### Run Local CI Simulation

```bash
# Full pre-commit check (before pushing)
make precommit

# Full quality check (more comprehensive)
make check

# Full test with coverage
make test-coverage
```

### Install Pre-commit Hooks

```bash
make pre-commit-install

# Hooks run automatically on git commit
# To run manually on all files:
make pre-commit-run
```

---

## Common Workflows

### Before Committing

```bash
# 1. Format and lint
make format lint

# 2. Type check
make typecheck

# 3. Run fast tests
make test-fast

# Or combine into one command
make precommit
```

### Full Quality Assurance

```bash
# Run everything before pushing
make check && make test-coverage
```

### During Development

```bash
# Run server
make serve

# In another terminal, run tests in watch mode
./run_lite_tests.sh -v
```

### After Making Changes

```bash
# Quick check
make lint-check typecheck test-unit

# Full check
make precommit
```

---

## Useful Development Commands

```bash
# Clean all build artifacts
make clean

# List all available targets
make help

# Install dependencies
make install

# Install test dependencies only
make install-test

# Check YAML syntax
make check-yaml
```

---

## Active vs Archived Code

- **ACTIVE**: `calendarbot_lite/` - Use this for development
- **PRODUCTION**: `kiosk/` - Raspberry Pi kiosk deployment
- **ARCHIVED**: `calendarbot/` - Legacy app (do not modify)

---

## Resources

| Resource | Purpose |
|----------|---------|
| [AGENTS.md](AGENTS.md) | Complete development reference and architecture guide |
| [README.md](README.md) | Project overview and background |
| [CLAUDE.md](CLAUDE.md) | Claude AI guidance for this codebase |
| [docs/](docs/) | Additional documentation |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [kiosk/README.md](kiosk/README.md) | Raspberry Pi kiosk deployment guide |

---

## Quick Tips

- **Virtual environment required**: Always activate with `. venv/bin/activate` before running Python commands
- **Async-first**: All I/O operations are async (aiohttp, aiosqlite)
- **No hardcoded config**: All configuration via `.env` file
- **Remote development**: Use host IP, not localhost for browser testing
- **Resource-constrained**: Optimized for <100MB RAM idle on Raspberry Pi

---

**Last Updated**: 2025-11-12
**Default Branch**: main
**Active Project**: calendarbot_lite/
