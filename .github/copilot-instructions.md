# GitHub Copilot Instructions for CalendarBot

## Repository Overview

CalendarBot is a dual-project repository with both active and archived codebases:

- **ACTIVE PROJECT**: `calendarbot_lite/` - Lightweight Alexa skill backend with ICS calendar processing
- **ARCHIVED PROJECT**: `calendarbot/` - Legacy terminal/web UI application (deprecated, no longer maintained)

**⚠️ CRITICAL: Unless explicitly instructed otherwise, ALL development work should be in `calendarbot_lite/`.**

### Project Purpose

`calendarbot_lite` is a lightweight Alexa skill backend that:
- Fetches and parses ICS calendar feeds (RFC 5545 compliant)
- Expands recurring events using RRULE processing
- Provides natural language calendar responses via Alexa
- Serves a web API for calendar data and health monitoring
- Handles timezone conversions and event prioritization

### Key Technologies

- **Python 3.12+**: Primary language for backend services
- **JavaScript/Node.js**: Frontend and testing (Jest)
- **Core Libraries**: aiohttp, icalendar, python-dateutil, pydantic
- **Async Programming**: Heavy use of asyncio patterns

## Build Instructions

### Python Setup

```bash
# Activate virtual environment (ALWAYS do this first)
. venv/bin/activate  # Linux/Mac
. venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -e .[dev]
```

### JavaScript Setup

```bash
# Install Node.js dependencies
npm install
```

### Configuration

Create a `.env` file from the example:
```bash
cp .env.example .env
# Edit .env with your configuration
```

**Required Environment Variables:**
- `CALENDARBOT_ICS_URL` - ICS calendar feed URL

See `.env.example` for complete configuration options.

### Running the Application

```bash
# Activate virtual environment
. venv/bin/activate

# Run calendarbot_lite server
python -m calendarbot_lite

# Server runs on http://0.0.0.0:8080 by default
```

## Test Instructions

### Python Tests

```bash
# Activate virtual environment first
. venv/bin/activate

# Run all calendarbot_lite tests
./run_lite_tests.sh

# Run with coverage report
./run_lite_tests.sh --coverage

# Run specific test markers
pytest tests/lite/ -m "unit"
pytest tests/lite/ -m "fast"
pytest tests/lite/ -m "not slow"

# Run specific test files
pytest tests/lite/test_server.py -v
pytest calendarbot_lite/test_alexa_registry.py -v
```

### JavaScript Tests

```bash
# Run Jest tests
npm test

# Run with watch mode
npm run test:watch

# Run with coverage
npm run test:coverage
```

### Test Structure

- **`tests/lite/`** - Main test directory for calendarbot_lite
- **`tests/lite_tests/`** - Additional test modules
- **`calendarbot_lite/test_*.py`** - Co-located unit tests
- **`tests/fixtures/`** - Test fixtures and sample data
- **`tests/deprecated_calendarbot_tests/`** - Archived tests (IGNORE)

### Test Markers

- `unit` - Fast unit tests for individual functions
- `integration` - Cross-component tests with external dependencies
- `smoke` - Quick startup validation tests
- `slow` - Tests that take >5 seconds
- `fast` - Quick tests (<1 second)
- `network` - Tests requiring network access

## Linting and Formatting

### Python - Ruff (replaces black + flake8)

```bash
# Check for linting issues
ruff check calendarbot_lite

# Auto-fix issues
ruff check --fix calendarbot_lite

# Format code
ruff format calendarbot_lite

# Both check and format
ruff check --fix calendarbot_lite && ruff format calendarbot_lite
```

**Configuration:** `pyproject.toml` (line length: 100, target: Python 3.9+)

### Type Checking - mypy

```bash
# Run type checking
mypy calendarbot_lite
```

**Configuration:** `pyproject.toml` with strict type checking enabled

### Security Scanning - Bandit

```bash
# Run security scan
bandit -r calendarbot_lite -c pyproject.toml
```

**Configuration:** `pyproject.toml` (medium+ severity issues)

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run all hooks manually
pre-commit run --all-files

# Run specific hook
pre-commit run ruff-check --all-files
```

## Code Style and Standards

### Type Annotations

- **REQUIRED**: All function parameters and return types must be annotated
- **EXCEPTION**: `self` parameter in class methods
- **PREFERENCE**: Explicit types over `Any`

### Import Organization

```python
# Standard library
import asyncio
from datetime import datetime

# Third-party
import aiohttp
from icalendar import Calendar

# First-party
from calendarbot_lite.config_manager import ConfigManager
```

### Code Formatting

- **Line Length**: 100 characters
- **Quote Style**: Double quotes
- **Import Style**: Combined imports, split on trailing comma

### Async Patterns

- Use async/await consistently
- Configure async tests with `asyncio_mode = auto` in pytest
- No need for explicit `@pytest.mark.asyncio` decorators

## Contribution Guidelines

### Before Committing

1. **Activate virtual environment**: `. venv/bin/activate`
2. **Run tests**: `./run_lite_tests.sh`
3. **Format code**: `ruff format calendarbot_lite`
4. **Check linting**: `ruff check calendarbot_lite`
5. **Type check**: `mypy calendarbot_lite`

### File Organization

- **Production Code**: `calendarbot_lite/*.py` - Core application modules
- **Routes/Endpoints**: `calendarbot_lite/routes/*.py` - HTTP route handlers
- **Tests**: `tests/lite/` or `tests/lite_tests/` - Test modules
- **Temporary Files**: `tmp/` - Debug scripts, analysis (gitignored)
- **Documentation**: `docs/` - Permanent documentation
- **Scripts**: `scripts/` - Utility scripts

### Git Workflow

- **Main branch**: `main` - Production-ready code
- **Feature branches**: Create from `main`, merge via PR
- **Commit messages**: Follow conventional commits format

### Code Review Checklist

- [ ] Tests pass (`./run_lite_tests.sh`)
- [ ] Code formatted (`ruff format`)
- [ ] Linting clean (`ruff check`)
- [ ] Types valid (`mypy`)
- [ ] Security scan clean (`bandit`)
- [ ] Coverage maintained or improved
- [ ] Documentation updated if needed

## Common Development Tasks

### Debug Recurring Events

```bash
python scripts/debug_recurring_events.py --env .env --output /tmp/debug.json --limit 50
```

### Kill Stuck Processes

```bash
./scripts/kill_calendarbot.sh --force
```

### Generate Test Fixtures

```bash
python scripts/write_test_fixtures.py
```

## Important Patterns and Conventions

### Virtual Environment

**ALWAYS activate venv first**: `. venv/bin/activate`
- Module import failures usually mean venv not activated
- Dependencies are installed in venv, not globally

### Debug Mode

Set `CALENDARBOT_DEBUG=true` in `.env` to enable DEBUG logging without code changes.

### Remote Development

- Development often happens in remote containers/VMs
- Use host IP (e.g., 192.168.1.45:8080) not localhost for browser testing
- Localhost binding may fail in remote environments

### Time-Based Testing

Override current time for testing:
```bash
CALENDARBOT_TEST_TIME=2024-01-01T12:00:00 python -m pytest
```

### Coverage Configuration

Coverage is configured in `pyproject.toml`:
- **Source**: `calendarbot_lite/` only
- **Excluded**: `calendarbot/*` (archived code)
- **Reports**: Terminal, HTML (htmlcov/), XML

## Core Architecture

### Modules in calendarbot_lite/

**Server & HTTP:**
- `server.py` - aiohttp web server, background tasks, lifecycle
- `routes/alexa_routes.py` - Alexa skill intent handlers
- `routes/api_routes.py` - REST API endpoints
- `routes/static_routes.py` - Static file serving

**Alexa Integration:**
- `alexa_handlers.py` - Intent processing pipeline (51KB core logic)
- `alexa_registry.py` - Handler registration and routing
- `alexa_precompute_stages.py` - Request preprocessing
- `alexa_response_cache.py` - Response caching
- `alexa_presentation.py` - Response formatting
- `alexa_ssml.py` - Speech synthesis markup (30KB)
- `alexa_models.py` - Pydantic request/response models
- `alexa_types.py` - Type definitions
- `alexa_exceptions.py` - Exception hierarchy

**Calendar Processing:**
- `lite_event_parser.py` - ICS parsing and event extraction
- `lite_rrule_expander.py` - Recurring event expansion
- `event_filter.py` - Event filtering logic
- `event_prioritizer.py` - Event ranking
- `timezone_utils.py` - Timezone conversion

**Infrastructure:**
- `async_utils.py` - Async helpers (21KB)
- `http_client.py` - HTTP client with retry (12KB)
- `fetch_orchestrator.py` - Calendar fetch coordination (10KB)
- `health_tracker.py` - System health monitoring (8KB)
- `config_manager.py` - Configuration management (5KB)

## API Endpoints

### Health & Status
- `GET /health` - Health check
- `GET /api/health` - Detailed health status
- `GET /api/status` - Server status

### Calendar Data
- `GET /api/events` - Get calendar events
- `GET /api/whats-next` - Get next upcoming events
- `POST /api/refresh` - Force calendar refresh

### Alexa Integration
- `POST /alexa` - Alexa skill webhook

## Debugging Tips

### Enable Debug Logging

```bash
# In .env
CALENDARBOT_DEBUG=true
CALENDARBOT_LOG_LEVEL=DEBUG
```

### Check Logs

```bash
# Server logs to stdout
python -m calendarbot_lite 2>&1 | tee server.log
```

### Profile Performance

```bash
python scripts/performance_benchmark.py --run all
```

## Additional Resources

- **`AGENTS.md`** - Comprehensive agent guidance with detailed patterns
- **`README.md`** - Project overview and quick start
- **`calendarbot_lite/README.md`** - Module documentation
- **`.env.example`** - Environment configuration reference
- **`pyproject.toml`** - Build configuration and dependencies
- **`pytest-lite.ini`** - Pytest configuration

## DO NOT Modify

- **`calendarbot/`** - Archived legacy application (unless explicitly instructed)
- **`.github/agents/`** - Agent-specific instructions (not for Copilot)

---

**For detailed patterns, non-obvious conventions, and advanced workflows, refer to `AGENTS.md`.**
