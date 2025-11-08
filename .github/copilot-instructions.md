# GitHub Copilot Instructions for CalendarBot

**Optimized guidance for GitHub Copilot agents working on the CalendarBot repository.**

This file provides project-specific context, patterns, and workflows to maximize agent effectiveness. For comprehensive development guidance, see [AGENTS.md](../AGENTS.md).

---

## 🎯 Quick Context

**CalendarBot Lite** is a lightweight Alexa skill backend with ICS calendar processing, designed for:
- **Primary Use Case**: Raspberry Pi kiosk with 24/7 calendar display
- **Scale**: Personal project for 1-5 users on resource-constrained hardware
- **Philosophy**: Keep it simple, optimize for low resource usage, no enterprise patterns

**Active Codebase**: `calendarbot_lite/` - All development work happens here
**Kiosk System**: `kiosk/` - Production deployment system
**Archived Code**: `calendarbot/` - Legacy app, DO NOT modify

---

## 🚀 Essential Commands

### Development Setup
```bash
# Always activate venv first
. venv/bin/activate

# Run server
python -m calendarbot_lite

# Run tests
./run_lite_tests.sh
./run_lite_tests.sh --coverage

# Run specific tests
pytest tests/lite/ -v
pytest tests/lite/ -m "unit"
pytest tests/lite/ -m "not slow"
```

### Code Quality (REQUIRED before commit)
```bash
# Format code
ruff format calendarbot_lite

# Lint and auto-fix
ruff check calendarbot_lite --fix

# Type check
mypy calendarbot_lite

# Security scan
bandit -r calendarbot_lite
```

### Common Tasks
```bash
# Run pre-commit checks
pre-commit run --all-files
```

---

## 📁 Project Structure

### Active Development (`calendarbot_lite/`)

```
calendarbot_lite/
├── api/                      # HTTP server and routes
│   ├── server.py            # Main web server
│   ├── routes/              # Route handlers
│   │   ├── alexa_routes.py  # Alexa webhook endpoints
│   │   ├── api_routes.py    # REST API endpoints
│   │   └── static_routes.py # Kiosk interface
│   └── middleware/          # HTTP middleware
│       ├── correlation_id.py
│       └── rate_limiter.py
├── alexa/                   # Alexa integration
│   ├── alexa_handlers.py    # Intent processing (51KB core logic)
│   ├── alexa_registry.py    # Handler registration
│   ├── alexa_ssml.py        # Speech synthesis (30KB)
│   └── alexa_models.py      # Pydantic request/response models
├── calendar/                # Calendar processing
│   ├── lite_parser.py       # ICS parsing coordinator
│   ├── lite_rrule_expander.py  # Recurring event expansion
│   ├── lite_fetcher.py      # ICS URL fetching
│   └── lite_event_parser.py # Event extraction
├── domain/                  # Business logic
│   ├── event_filter.py      # Event filtering
│   ├── event_prioritizer.py # Event ranking
│   └── pipeline.py          # Processing orchestration
└── core/                    # Shared infrastructure
    ├── config_manager.py    # Configuration (5KB)
    ├── http_client.py       # HTTP with retry (12KB)
    ├── health_tracker.py    # Health monitoring (8KB)
    └── async_utils.py       # Async helpers (21KB)
```

### Kiosk Deployment (`kiosk/`)

```
kiosk/
├── install-kiosk.sh         # Automated installer (MAIN ENTRY POINT)
├── install-config.example.yaml  # Configuration template
├── docs/                    # Installation guides
│   ├── AUTOMATED_INSTALLATION.md
│   ├── INSTALLATION_OVERVIEW.md
│   └── DEPLOYMENT_CHECKLIST.md
├── config/                  # System configuration
│   ├── calendarbot-watchdog # Watchdog script
│   └── monitor.yaml         # Watchdog config
└── service/                 # systemd unit files
```

### Tests (`tests/`)

```
tests/
├── lite/                    # Main test directory
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── fixtures/           # Test data
├── lite_tests/             # Additional test modules
└── fixtures/               # Shared test fixtures
```

### File Organization Rules

- **Temporary Files**: Write to `tmp/` (gitignored)
- **Documentation**: Write to `docs/` for permanent docs
- **Configuration**: Root directory only (`.env`, `pyproject.toml`)
- **Project Plans**: Create markdown files in `project-plans/` directory at root

---

## 🎨 Code Style Standards

### Python Conventions

**Line Length**: 100 characters
**Target**: Python 3.12+
**Tools**: ruff (replaces black + flake8)

### Type Annotations
```python
# REQUIRED: All function parameters and return types
def process_events(
    events: list[Event],
    timezone: str = "UTC"
) -> list[Event]:
    """Process and filter events."""
    return filtered_events

# Exception: 'self' parameter doesn't need annotation
```

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
from calendarbot_lite.calendar.lite_parser import parse_ics
```

### Async Patterns
```python
# Prefer async/await for I/O
async def fetch_calendar(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
```

---

## 🧪 Testing Standards

### Test Quality Principles

**Core Rules**:
1. **Unconditional Assertions**: No `if` statements in test body
2. **Test One Outcome**: Verify ONE specific behavior per test
3. **Must Fail If Broken**: Tests verify implementation, not just types
4. **Strategic Mocking**: Mock I/O boundaries (HTTP, filesystem, time), NOT business logic

### Critical Anti-Patterns to Avoid

❌ **Conditional Assertions**
```python
# BAD - assertion might not execute
if len(result) > 0:
    assert result[0].status == "active"

# GOOD - always executes
assert len(result) == 1
assert result[0].status == "active"
```

❌ **Over-Mocking Business Logic**
```python
# BAD - mocks domain logic
mock_filter.return_value = [event1, event2]
result = process_events(events)

# GOOD - tests real filtering logic
result = process_events([busy_event, free_event])
assert result == [busy_event]
```

### Test Markers

```bash
# Fast tests only
pytest tests/lite/ -m "fast"

# Skip slow tests
pytest tests/lite/ -m "not slow"

# Unit tests
pytest tests/lite/ -m "unit"

# Integration tests
pytest tests/lite/ -m "integration"

# Smoke tests (includes Alexa API smoke suite)
pytest tests/lite/ -m "smoke"
```

### Async Testing

Tests use `asyncio_mode = auto` - no explicit `@pytest.mark.asyncio` decorators needed:

```python
async def test_async_function():
    """Test async functionality."""
    result = await some_async_function()
    assert result == expected
```

---

## 🔧 Configuration

### Environment Variables

**Required**:
- `CALENDARBOT_ICS_URL` - ICS calendar feed URL

**Server**:
- `CALENDARBOT_WEB_HOST` - Bind address (default: 0.0.0.0)
- `CALENDARBOT_WEB_PORT` - Port (default: 8080)
- `CALENDARBOT_REFRESH_INTERVAL` - Refresh seconds (default: 300)

**Development**:
- `CALENDARBOT_DEBUG` - Enable debug logging (true/false)
- `CALENDARBOT_LOG_LEVEL` - Override log level (DEBUG, INFO, WARNING, ERROR)
- `CALENDARBOT_NONINTERACTIVE` - Disable interactive prompts (true/false)
- `CALENDARBOT_TEST_TIME` - Override current time for testing (ISO format)

See [.env.example](../.env.example) for complete reference.

---

## 🏗️ Architecture Patterns

### Application Scale

**Key Context**: This is a **personal application** for 1-5 users on Raspberry Pi Zero 2W.

**Do**:
- ✅ Keep it simple - avoid enterprise patterns
- ✅ Optimize for low resource usage (<100MB RAM idle)
- ✅ Focus on single-instance reliability
- ✅ Prefer straightforward solutions

**Don't**:
- ❌ Add circuit breakers, distributed tracing, service mesh
- ❌ Implement staged rollouts or blue-green deployments
- ❌ Add complex caching layers or CDN integration
- ❌ Over-engineer for horizontal scaling

### Breaking Changes

**Breaking changes are acceptable** - this is a personal project with controlled deployment. No need for:
- API versioning
- Deprecation warnings
- Migration paths

Just update docs and deploy.

### Request Correlation IDs

All requests have correlation IDs for distributed tracing:

**Priority**:
1. `X-Amzn-Trace-Id` - AWS ALB/API Gateway
2. `X-Request-ID` - Client-provided
3. `X-Correlation-ID` - Alternative header
4. Auto-generated UUID

**Implementation**:
- Middleware: `calendarbot_lite/middleware/correlation_id.py`
- Context Storage: Python `contextvars` for async-safe tracking
- Log Integration: `CorrelationIdFilter` in `lite_logging.py`

---

## 🚢 Raspberry Pi Kiosk Deployment

### Overview

The **kiosk deployment is the PRIMARY production use case**. It provides:
- Automated installation with `install-kiosk.sh`
- Auto-login and X session management
- Watchdog monitoring with progressive recovery
- Browser heartbeat detection for frozen displays
- 24/7 calendar display operation

### Quick Start

```bash
# 1. Configure
cd ~/calendarBot/kiosk
cp install-config.example.yaml install-config.yaml
nano install-config.yaml  # Set username and ICS URL

# 2. Install
sudo ./install-kiosk.sh --config install-config.yaml

# 3. Reboot
sudo reboot
```

### Architecture

```
Boot → systemd
  ├─> calendarbot-lite@user.service (server on port 8080)
  ├─> Auto-login to tty1 → .bash_profile → startx → .xinitrc → Chromium
  └─> calendarbot-kiosk-watchdog@user.service (health monitoring)
```

### Progressive Recovery

When browser heartbeat fails, watchdog uses 3-level escalation:

1. **Level 0: Soft Reload** (~15s) - F5 key via xdotool
2. **Level 1: Browser Restart** (~30s) - Kill and relaunch
3. **Level 2: X Session Restart** (~60s) - Full X restart

Escalates after 2 consecutive failures, de-escalates when health resumes.

### Service Management

```bash
# Check status
systemctl status calendarbot-lite@bencan.service
systemctl status calendarbot-kiosk-watchdog@bencan.service

# View logs
journalctl -u calendarbot-kiosk-watchdog@bencan.service -f

# Test heartbeat
curl -X POST http://127.0.0.1:8080/api/browser-heartbeat
curl -s http://127.0.0.1:8080/api/health | jq '.display_probe'
```

---

## 🐛 Debugging

### Enable Debug Logging

```bash
# In .env
CALENDARBOT_DEBUG=true
CALENDARBOT_LOG_LEVEL=DEBUG
```

### Correlation ID Tracing

```bash
# Test with custom ID
curl -H "X-Request-ID: test-12345" http://localhost:8080/api/health

# Find all related logs
grep "test-12345" server.log
```

### Debug Recurring Events

```bash
python scripts/debug_recurring_events.py \
  --env .env \
  --output /tmp/rrule_debug.json \
  --limit 50 \
  --compare-dateutil
```

---

## 📋 Common Workflows

### Make Code Changes

1. **Activate venv**: `. venv/bin/activate`
2. **Make changes**: Edit files in `calendarbot_lite/`
3. **Run tests early**: `pytest tests/lite/ -v`
4. **Format code**: `ruff format calendarbot_lite`
5. **Check linting**: `ruff check calendarbot_lite --fix`
6. **Type check**: `mypy calendarbot_lite`
7. **Security scan**: `bandit -r calendarbot_lite`
8. **Run tests again**: `./run_lite_tests.sh --coverage`
9. **Commit**: Git will run pre-commit hooks

### Add New Test

1. Create test in `tests/lite/` matching structure
2. Use appropriate markers (`@pytest.mark.unit`, etc.)
3. Follow test quality standards (no conditional assertions)
4. Mock at I/O boundaries, not business logic
5. Run specific test: `pytest tests/lite/ -k "test_name"`
6. Run full suite: `./run_lite_tests.sh`

### Add New Alexa Intent

1. Create handler in `calendarbot_lite/alexa/alexa_handlers.py`
2. Register in `alexa_registry.py`
3. Add route in `calendarbot_lite/api/routes/alexa_routes.py`
4. Add test in `tests/lite/integration/test_alexa_runner.py`
5. Update SSML generation if needed in `alexa_ssml.py`

### Debug Kiosk Issue

1. Check service status: `systemctl status calendarbot-lite@user.service`
2. Check watchdog: `journalctl -u calendarbot-kiosk-watchdog@user.service -f`
3. Check browser heartbeat: `curl -X POST http://127.0.0.1:8080/api/browser-heartbeat`
4. Test soft reload: `DISPLAY=:0 xdotool search --class chromium windowactivate --sync key F5`
5. Restart X session: `sudo systemctl restart auto-login-x-session`

---

## 📚 Documentation Reference

### Core Documentation

- **[AGENTS.md](../AGENTS.md)** - **Comprehensive development guide (START HERE)**
- **[CLAUDE.md](../CLAUDE.md)** - Quick reference for Claude Code
- **[README.md](../README.md)** - Project overview
- **[.env.example](../.env.example)** - Environment variable reference

### Kiosk Documentation

- **[kiosk/README.md](../kiosk/README.md)** - Kiosk deployment overview
- **[kiosk/docs/AUTOMATED_INSTALLATION.md](../kiosk/docs/AUTOMATED_INSTALLATION.md)** - Installation guide
- **[kiosk/docs/INSTALLATION_OVERVIEW.md](../kiosk/docs/INSTALLATION_OVERVIEW.md)** - Architecture

### Component Documentation

- **[docs/lite/](../docs/lite/)** - Detailed component documentation
- **[docs/pytest-best-practices.md](../docs/pytest-best-practices.md)** - Testing guide with all 10 anti-patterns
- **[docs/ALEXA_DEPLOYMENT_GUIDE.md](../docs/ALEXA_DEPLOYMENT_GUIDE.md)** - Alexa skill setup

---

## ⚠️ Critical Patterns

### Always Activate Virtual Environment

**FIRST COMMAND**: `. venv/bin/activate`

Module import failures usually mean venv not activated. Dependencies are in venv, not globally.

### Remote Development

- Development often happens in remote containers/VMs
- Use host IP (e.g., 192.168.1.45:8080) not localhost for browser testing
- Server binds to 0.0.0.0 by default for remote access

### Time-Based Testing

Override current time for testing:
```bash
CALENDARBOT_TEST_TIME=2024-01-01T12:00:00 pytest tests/lite/
```

### Archived Code

**DO NOT modify `calendarbot/` directory** unless explicitly instructed. It's archived legacy code.

---

## 🎯 Success Criteria

Before committing, verify:

1. ✅ Virtual environment activated
2. ✅ Tests pass: `./run_lite_tests.sh`
3. ✅ Code formatted: `ruff format calendarbot_lite`
4. ✅ Linting clean: `ruff check calendarbot_lite`
5. ✅ Type checking clean: `mypy calendarbot_lite`
6. ✅ Security scan clean: `bandit -r calendarbot_lite`
7. ✅ Changes are minimal and surgical
8. ✅ Archived `calendarbot/` directory untouched

---

**Last Updated**: 2025-11-07
**Active Project**: `calendarbot_lite/`
**Primary Use Case**: Raspberry Pi kiosk deployment
**For Complete Guidance**: See [AGENTS.md](../AGENTS.md)
