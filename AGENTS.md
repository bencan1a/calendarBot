# AGENTS.md

**Agent guidance for working with the CalendarBot codebase.**

This file provides essential context, patterns, and commands for AI agents working on this project.

---

## ⚠️ CRITICAL: Project Structure

### Active vs Archived Codebases

- **ACTIVE PROJECT**: [`calendarbot_lite/`](calendarbot_lite/) - Alexa skill backend with ICS calendar processing
- **KIOSK DEPLOYMENT**: [`kiosk/`](kiosk/) - Production-ready Raspberry Pi kiosk system (PRIMARY use case)
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

**kiosk** provides a production-ready Raspberry Pi deployment system:
- Automated installation with `install-kiosk.sh`
- Auto-login and X session management
- Watchdog monitoring with progressive recovery
- Browser heartbeat detection for frozen displays
- 24/7 calendar display operation

**Key Technologies**: Python 3.12+, aiohttp, icalendar, python-dateutil, pydantic

---

## ⚠️ Application Context & Scale

**CalendarBot Lite is a personal application with a single developer.** This fundamentally shapes how we approach development:

### Scale & Performance Expectations

- **User Count**: Designed for a few users at most (typically 1-5)
- **Deployment Target**: Primarily Raspberry Pi Zero 2W (1GB RAM, quad-core ARM Cortex-A53)
- **Resource Constraints**: Optimize for low memory footprint and efficient CPU usage
- **Network Load**: Minimal concurrent requests (1-2 typical, 5-10 maximum)

### Development Philosophy

**Keep It Simple:**
- ❌ **Don't** add enterprise patterns (circuit breakers, distributed tracing, service mesh, etc.)
- ❌ **Don't** implement staged rollouts, blue-green deployments, or canary releases
- ❌ **Don't** add complex caching layers or CDN integration
- ❌ **Don't** over-engineer for horizontal scaling or high availability
- ✅ **Do** prioritize simplicity and maintainability
- ✅ **Do** focus on single-instance reliability
- ✅ **Do** optimize for resource efficiency on constrained hardware
- ✅ **Do** prefer straightforward solutions over clever abstractions

**Backward Compatibility:**
- **Breaking changes are acceptable** - this is a personal project with controlled deployment
- No need for API versioning, deprecation warnings, or migration paths
- Update docs and deploy - version bumps are fine

**Performance Considerations:**
- Optimize for **low resource usage** (memory, CPU) over raw throughput
- Target: Idle server uses <100MB RAM, handles 1-2 requests/sec comfortably
- Raspberry Pi Zero 2W constraints: 1GB RAM total, ~400MHz-1GHz CPU per core
- Avoid heavy dependencies that inflate memory footprint
- Prefer async I/O for efficiency, but don't over-complicate with parallelization

**Code Patterns:**
- Simple, direct implementations over abstraction layers
- Minimal dependencies - each new library costs memory and startup time
- Clear, readable code beats clever optimization (unless resource-critical)
- Built-in Python stdlib preferred over third-party when feasible

### When to Ignore This Guidance

You **should** still apply professional practices for:
- Error handling and graceful degradation
- Security best practices (input validation, authentication, etc.)
- Testing critical functionality
- Clear documentation
- Type safety and linting

But scale them appropriately - test what matters, document what's complex, secure what's exposed.

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
- **Kiosk Deployment**: `kiosk/` - Raspberry Pi kiosk deployment system and documentation
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

## Raspberry Pi Kiosk Deployment

### Overview

The **`kiosk/`** directory provides a production-ready Raspberry Pi kiosk deployment system designed for 24/7 calendar display operation. **This is a PRIMARY use case** for CalendarBot Lite.

### Quick Start

**Automated Installation (Recommended):**
```bash
# 1. Configure
cd ~/calendarBot/kiosk
cp install-config.example.yaml install-config.yaml
nano install-config.yaml  # Set username and ICS URL

# 2. Preview changes
sudo ./install-kiosk.sh --config install-config.yaml --dry-run

# 3. Install
sudo ./install-kiosk.sh --config install-config.yaml

# 4. Reboot to start kiosk
sudo reboot
```

### Architecture

```
Boot → systemd
  ├─> calendarbot-lite@user.service (server on port 8080)
  ├─> Auto-login to tty1 → .bash_profile → startx → .xinitrc → Chromium
  └─> calendarbot-kiosk-watchdog@user.service (health monitoring)
```

### Key Features

- **Automated Installation**: One-command idempotent deployment
- **Auto-Login & X Session**: Console auto-login triggers kiosk display on boot
- **Watchdog Monitoring**: Health checks with progressive recovery
- **Browser Heartbeat**: Detects stuck/frozen browsers via JavaScript
- **Progressive Recovery**: 3-level escalation (soft reload → browser restart → X restart)
- **Resource Monitoring**: Degraded mode under system load

### Service Management

```bash
# Check service status
systemctl status calendarbot-lite@bencan.service
systemctl status calendarbot-kiosk-watchdog@bencan.service

# View watchdog logs
journalctl -u calendarbot-kiosk-watchdog@bencan.service -f

# Restart X session (full kiosk restart)
sudo systemctl restart auto-login-x-session

# Test browser heartbeat
curl -X POST http://127.0.0.1:8080/api/browser-heartbeat
curl -s http://127.0.0.1:8080/api/health | jq '.display_probe'
```

### Kiosk Directory Structure

```
kiosk/
├── README.md                    # Kiosk deployment overview
├── install-kiosk.sh            # Automated installer (main entry point)
├── install-config.example.yaml # Configuration template
├── docs/                       # Comprehensive installation guides
│   ├── AUTOMATED_INSTALLATION.md
│   ├── INSTALLATION_OVERVIEW.md
│   ├── DEPLOYMENT_CHECKLIST.md
│   ├── MANUAL_STEPS.md
│   └── 1_BASE_INSTALL.md through 4_LOG_MANAGEMENT.md
├── config/                     # Configuration files
│   ├── calendarbot-watchdog    # Watchdog script
│   ├── monitor.yaml            # Watchdog config
│   └── *.service files
├── scripts/                    # Helper scripts
└── service/                    # systemd unit files
```

### Documentation

See **[kiosk/README.md](kiosk/README.md)** for complete kiosk documentation:
- **[Automated Installation Guide](kiosk/docs/AUTOMATED_INSTALLATION.md)** - Complete automation guide
- **[Installation Overview](kiosk/docs/INSTALLATION_OVERVIEW.md)** - Architecture & workflow
- **[Deployment Checklist](kiosk/docs/DEPLOYMENT_CHECKLIST.md)** - Verification checklists
- **[Manual Steps Guide](kiosk/docs/MANUAL_STEPS.md)** - DNS, AWS Lambda, Alexa setup

### Progressive Recovery System

When browser heartbeat fails, watchdog uses 3-level escalation:

1. **Level 0: Soft Reload** (~15s) - Send F5 key for page rendering issues
2. **Level 1: Browser Restart** (~30s) - Kill/relaunch for memory leaks
3. **Level 2: X Session Restart** (~60s) - Full X restart for display problems

Recovery escalates after **2 consecutive** heartbeat failures, de-escalates when health resumes.

### Troubleshooting

```bash
# Check service logs
journalctl -u calendarbot-kiosk-watchdog@bencan.service -n 50

# Check watchdog state
cat /var/local/calendarbot-watchdog/state.json | jq

# Reset watchdog state (stop watchdog first)
sudo systemctl stop calendarbot-kiosk-watchdog@bencan.service
# Edit /var/local/calendarbot-watchdog/state.json
sudo systemctl start calendarbot-kiosk-watchdog@bencan.service

# Test soft reload
DISPLAY=:0 xdotool search --class chromium windowactivate --sync key F5
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
- **Target**: Python 3.12+
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

### Core Documentation
- **[README.md](README.md)** - Project overview and quick start
- **[calendarbot_lite/README.md](calendarbot_lite/README.md)** - Module documentation
- **[docs/](docs/)** - Additional documentation and guides
- **[.env.example](.env.example)** - Environment configuration reference
- **[pyproject.toml](pyproject.toml)** - Build configuration and dependencies
- **[pytest-lite.ini](pytest-lite.ini)** - Pytest configuration for lite tests

### Kiosk Deployment Resources
- **[kiosk/README.md](kiosk/README.md)** - Kiosk deployment overview
- **[kiosk/docs/AUTOMATED_INSTALLATION.md](kiosk/docs/AUTOMATED_INSTALLATION.md)** - Automated installation
- **[kiosk/docs/INSTALLATION_OVERVIEW.md](kiosk/docs/INSTALLATION_OVERVIEW.md)** - Architecture & workflow
- **[kiosk/docs/DEPLOYMENT_CHECKLIST.md](kiosk/docs/DEPLOYMENT_CHECKLIST.md)** - Verification checklists

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

**Last Updated**: 2025-11-04
**Active Project**: calendarbot_lite/
**Kiosk Deployment**: kiosk/ (PRIMARY use case for production)
**Archived Project**: calendarbot/ (deprecated)
