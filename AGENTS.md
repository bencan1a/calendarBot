# AGENTS.md

**Agent guidance for working with the CalendarBot codebase.**

This file provides essential context, patterns, and commands for AI agents working on this project.

---

## ⚠️ CRITICAL: Project Structure

### Active vs Archived Codebases

- **ACTIVE PROJECT**: [`calendarbot_lite/`](calendarbot_lite/) - Alexa skill backend with ICS calendar processing
- **ARCHIVED PROJECT**: [`calendarbot/`](calendarbot/) - Legacy terminal/web UI application (deprecated, no longer maintained)

**DEFAULT BEHAVIOR**: Unless explicitly instructed otherwise, ALL development work should be in `calendarbot_lite/`.

**DO NOT** modify code in the `calendarbot/` directory without explicit user instruction.

---

## Project Overview

**calendarbot_lite** is a lightweight Alexa skill backend that:
- Fetches and parses ICS calendar feeds (RFC 5545 compliant)
- Expands recurring events using RRULE processing
- Provides natural language calendar responses via Alexa
- Serves a web API for calendar data and health monitoring
- Handles timezone conversions and event prioritization

**Key Technologies**: Python 3.9+, aiohttp, icalendar, python-dateutil, pydantic

---

## Quick Start

### Development Setup

```bash
# Activate virtual environment
. venv/bin/activate  # Linux/Mac
. venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment (copy and edit .env)
cp .env.example .env
# Edit .env with your ICS_URL and other settings

# Run the server
python -m calendarbot_lite

# Server runs on http://0.0.0.0:8080 by default
```

### Testing

```bash
# Run all calendarbot_lite tests
./run_lite_tests.sh

# Run with coverage report
./run_lite_tests.sh --coverage

# Run specific tests with pytest
pytest tests/lite/ -v
pytest calendarbot_lite/test_alexa_registry.py -v

# Run with markers
pytest tests/lite/ -m "unit"
pytest tests/lite/ -m "not slow"
```

---

## File Organization

**IMPORTANT: Follow these conventions when creating files:**

- **Production Code**: `calendarbot_lite/*.py` - Core application modules
- **Routes/Endpoints**: `calendarbot_lite/routes/*.py` - HTTP route handlers
- **Tests**: `tests/lite/` or `tests/lite_tests/` - Test modules
- **Temporary Files**: `tmp/` - Debug scripts, analysis reports (gitignored)
- **Documentation**: `docs/` - Permanent documentation and guides
- **Scripts**: `scripts/` - Utility scripts for development/debugging
- **Configuration**: Root directory - CLAUDE.md, AGENTS.md, README.md, .env

The `tmp/` directory is gitignored for temporary/analysis files that don't need version control.

---

## Configuration

### Environment Variables

Configuration is managed via environment variables in `.env` file:

**Required:**
- `CALENDARBOT_ICS_URL` - ICS calendar feed URL

**Server:**
- `CALENDARBOT_WEB_HOST` - Bind address (default: 0.0.0.0)
- `CALENDARBOT_WEB_PORT` - Port number (default: 8080)
- `CALENDARBOT_REFRESH_INTERVAL` - Refresh seconds (default: 300)

**Alexa Integration:**
- `CALENDARBOT_ALEXA_BEARER_TOKEN` - Bearer token for Alexa API authentication

**Logging:**
- `CALENDARBOT_DEBUG` - Enable debug logging (true/false)
- `CALENDARBOT_LOG_LEVEL` - Override log level (DEBUG, INFO, WARNING, ERROR)

**Testing/Advanced:**
- `CALENDARBOT_NONINTERACTIVE` - Disable interactive prompts (true/false)
- `CALENDARBOT_TEST_TIME` - Override current time for testing (ISO format)
- `CALENDARBOT_PRODUCTION` - Enable production optimizations (true/false)

See [.env.example](.env.example) for complete reference.

---

## Architecture Overview

### Core Modules (calendarbot_lite/)

**Server & HTTP:**
- `server.py` - aiohttp web server, background tasks, lifecycle management
- `routes/alexa_routes.py` - Alexa skill intent handlers
- `routes/api_routes.py` - REST API endpoints for calendar data
- `routes/static_routes.py` - Static file serving

**Alexa Integration:**
- `alexa_handlers.py` - Intent processing pipeline (51KB, core logic)
- `alexa_registry.py` - Handler registration and routing
- `alexa_precompute_stages.py` - Request preprocessing pipeline
- `alexa_response_cache.py` - Response caching layer
- `alexa_presentation.py` - Response formatting and presentation
- `alexa_ssml.py` - Speech synthesis markup generation (30KB)
- `alexa_models.py` - Pydantic models for Alexa requests/responses
- `alexa_types.py` - Type definitions and protocols
- `alexa_exceptions.py` - Custom exception hierarchy

**Calendar Processing:**
- `lite_event_parser.py` - ICS parsing and event extraction
- `lite_rrule_expander.py` - Recurring event expansion
- `event_filter.py` - Event filtering logic
- `event_prioritizer.py` - Event ranking and prioritization
- `timezone_utils.py` - Timezone conversion utilities

**Infrastructure:**
- `async_utils.py` - Async helpers and utilities (21KB)
- `http_client.py` - HTTP client with retry logic (12KB)
- `fetch_orchestrator.py` - Calendar fetch coordination (10KB)
- `health_tracker.py` - System health monitoring (8KB)
- `config_manager.py` - Configuration management (5KB)
- `dependencies.py` - Dependency injection helpers

**Debugging:**
- `debug_helpers.py` - Debugging utilities and diagnostics

### Test Structure

- `tests/lite/` - Main test directory for calendarbot_lite
- `tests/lite_tests/` - Additional test modules
- `calendarbot_lite/test_*.py` - Co-located unit tests for specific modules
- `tests/fixtures/` - Test fixtures and sample data
- `tests/deprecated_calendarbot_tests/` - Archived legacy tests (ignore)

---

## Development Workflows

### Common Tasks

**Run the development server:**
```bash
. venv/bin/activate
python -m calendarbot_lite
```

**Run tests with coverage:**
```bash
./run_lite_tests.sh --coverage
```

**Debug recurring event expansion:**
```bash
python scripts/debug_recurring_events.py --env .env --output /tmp/debug.json --limit 50
```

**Run performance benchmarks:**
```bash
python scripts/performance_benchmark.py --run all --output calendarbot_lite_perf_results.json
```

**Generate test fixtures:**
```bash
python scripts/write_test_fixtures.py
```

**Kill hanging processes:**
```bash
./scripts/kill_calendarbot.sh --force
```

### Code Quality

**Linting and formatting (using ruff):**
```bash
ruff check calendarbot_lite      # Check for issues
ruff format calendarbot_lite     # Format code
```

**Type checking:**
```bash
mypy calendarbot_lite
```

**Security scanning:**
```bash
bandit -r calendarbot_lite
```

---

## Testing Guidelines

### Test Markers

Configure test runs using pytest markers:

- `unit` - Fast unit tests for individual functions
- `integration` - Cross-component tests with external dependencies
- `smoke` - Quick startup validation tests
- `slow` - Tests that take >5 seconds
- `fast` - Quick tests (<1 second)
- `network` - Tests requiring network access

### Running Specific Test Categories

```bash
# Fast tests only
pytest tests/lite/ -m "fast"

# Skip slow tests
pytest tests/lite/ -m "not slow"

# Unit tests only
pytest tests/lite/ -m "unit"

# Integration tests
pytest tests/lite/ -m "integration"
```

### Coverage Configuration

Coverage is configured in [pyproject.toml](pyproject.toml#L390-L413):
- **Source**: `calendarbot_lite/` only
- **Excluded**: `calendarbot/*` (archived code)
- **Reports**: Terminal, HTML (htmlcov/), XML

---

## Critical Non-Obvious Patterns

### Environment Activation
**ALWAYS activate venv first**: `. venv/bin/activate`
- Module import failures usually mean venv not activated
- Dependencies are installed in venv, not globally

### Debug Mode
Set `CALENDARBOT_DEBUG=true` in `.env` to enable DEBUG logging without code changes.

### Remote Development
- Development often happens in remote containers/VMs
- Use host IP (e.g., 192.168.1.45:8080) not localhost for browser testing
- Localhost binding may fail in remote environments

### Async Testing
- Tests use `asyncio_mode = auto` (configured in pyproject.toml)
- No need for explicit `@pytest.mark.asyncio` decorators
- Use `pytest-asyncio` for async fixtures

### Time-Based Testing
Override current time for testing:
```bash
CALENDARBOT_TEST_TIME=2024-01-01T12:00:00 python -m pytest
```

---

## Code Style Standards

### Ruff Configuration
- **Line Length**: 100 characters
- **Target**: Python 3.9+
- **Replaces**: black (formatting) + flake8 (linting)
- **Import Style**: Combined imports, split on trailing comma
- **First-Party**: `calendarbot_lite` package

### Type Annotations
- **Required**: All function parameters and return types
- **Exception**: `self` parameter in class methods
- **Preference**: Explicit types over `Any`
- **Tools**: mypy for type checking

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

---

## API Endpoints

### Health & Status
- `GET /health` - Health check endpoint
- `GET /api/health` - Detailed health status
- `GET /api/status` - Server status information

### Calendar Data
- `GET /api/events` - Get calendar events
- `GET /api/whats-next` - Get next upcoming events
- `POST /api/refresh` - Force calendar refresh

### Alexa Integration
- `POST /alexa` - Alexa skill webhook endpoint

See [calendarbot_lite/routes/](calendarbot_lite/routes/) for full route definitions.

---

## Debugging Tips

### Enable Debug Logging
```bash
# In .env
CALENDARBOT_DEBUG=true
CALENDARBOT_LOG_LEVEL=DEBUG
```

### Check Logs
```bash
# Server logs to stdout by default
python -m calendarbot_lite 2>&1 | tee server.log
```

### Debug Recurring Events
```bash
# Generate detailed expansion trace
python scripts/debug_recurring_events.py \
  --env .env \
  --output /tmp/rrule_debug.json \
  --limit 50 \
  --compare-dateutil
```

### Profile Performance
```bash
# Run performance benchmarks
python scripts/performance_benchmark.py --run all
```

### Kill Stuck Processes
```bash
# Kill all calendarbot processes
./scripts/kill_calendarbot.sh --force
```

---

## Deployment Considerations

### Production Mode
Set `CALENDARBOT_PRODUCTION=true` to enable:
- Optimized logging
- Response caching
- Error suppression for user-facing responses

### Port Binding
Default port 8080 can be changed via:
```bash
CALENDARBOT_WEB_PORT=5000 python -m calendarbot_lite
```

### Health Monitoring
Monitor `/health` endpoint for uptime checks:
```bash
curl http://localhost:8080/health
```

---

## ARCHIVED: Legacy CalendarBot (calendarbot/)

**The following information is for the ARCHIVED `calendarbot/` directory only.**
**Do not use these commands unless specifically working with legacy code.**

### Legacy Entry Points (ARCHIVED)
```bash
# DO NOT USE - Archived application
calendarbot --web
calendarbot --setup
calendarbot --epaper
```

### Legacy Architecture (ARCHIVED)
The archived `calendarbot/` directory contains:
- Terminal UI with keyboard navigation
- Web interface with multiple layouts
- E-paper display support
- SQLite-based event caching
- Comprehensive settings management

For details on the archived architecture, see legacy sections in [CLAUDE.md](CLAUDE.md#L139-L252).

---

## Additional Resources

- **[README.md](README.md)** - Project overview and quick start
- **[calendarbot_lite/README.md](calendarbot_lite/README.md)** - Module documentation
- **[docs/](docs/)** - Additional documentation and guides
- **[.env.example](.env.example)** - Environment configuration reference
- **[pyproject.toml](pyproject.toml)** - Build configuration and dependencies
- **[pytest-lite.ini](pytest-lite.ini)** - Pytest configuration for lite tests

---

## Contributing Guidelines

### Before Committing
1. Run tests: `./run_lite_tests.sh`
2. Check formatting: `ruff format calendarbot_lite`
3. Run linter: `ruff check calendarbot_lite`
4. Verify types: `mypy calendarbot_lite`

### Git Workflow
- **Main branch**: `main` - Production-ready code
- **Feature branches**: Create from `main`, merge via PR
- **Commit messages**: Follow conventional commits format

### Code Review
- Ensure tests pass
- Verify coverage doesn't decrease
- Check for security issues
- Validate documentation updates

---

**Last Updated**: 2025-11-03
**Active Project**: calendarbot_lite/
**Archived Project**: calendarbot/ (deprecated)
