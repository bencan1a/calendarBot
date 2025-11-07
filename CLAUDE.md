# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**For comprehensive development guidance, see [AGENTS.md](AGENTS.md)** - the complete reference for working with this codebase.

---

## ⚠️ CRITICAL: Active vs Archived Code

- **ACTIVE PROJECT**: `calendarbot_lite/` - Alexa skill backend (USE THIS)
- **KIOSK DEPLOYMENT**: `kiosk/` - Raspberry Pi kiosk system (PRIMARY production use case)
- **ARCHIVED PROJECT**: `calendarbot/` - Legacy app (DO NOT USE unless explicitly instructed)

**Default to working in `calendarbot_lite/` for all development tasks.**

---

## ⚠️ Application Context

**This is a personal project for a single developer** deployed on resource-constrained hardware (Raspberry Pi Zero 2W).

**Key Principles:**
- **Keep it simple** - No enterprise patterns, no over-engineering
- **Resource efficient** - Optimize for low memory/CPU usage (<100MB RAM idle)
- **Breaking changes OK** - No backward compatibility burden
- **Few users** - Designed for 1-5 users maximum
- **Single instance** - No horizontal scaling needed

See **[AGENTS.md - Application Context & Scale](AGENTS.md#-application-context--scale)** for complete guidance.

---

## Quick Reference

### Development Setup
```bash
# Activate virtual environment
. venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run server
python -m calendarbot_lite
```

### Testing
```bash
# Run all tests
./run_lite_tests.sh

# Run with coverage
./run_lite_tests.sh --coverage

# Run specific tests
pytest tests/lite/ -v
pytest tests/lite/ -m "unit"
```

**Test Quality Standards:**
- All assertions must be unconditional (no `if` statements in test body)
- Test ONE specific outcome, not multiple possibilities
- Mock external I/O (HTTP, filesystem, time) NOT business logic
- Tests must fail if production code breaks
- See [docs/pytest-best-practices.md](docs/pytest-best-practices.md) for complete guide

### Code Quality
```bash
# Format code
ruff format calendarbot_lite

# Check linting
ruff check calendarbot_lite

# Type check
mypy calendarbot_lite
```

---

## File Organization

**IMPORTANT: Follow these conventions when creating files:**

- **Temporary/Debug Scripts**: Write to `tmp/` directory (gitignored)
- **Project Reports/Analysis**: Write to `tmp/` directory (gitignored)
- **Permanent Documentation**: Write to `docs/` directory
- **Configuration Files**: Root directory only (CLAUDE.md, AGENTS.md, README.md)

The `tmp/` directory is gitignored and should contain all temporary files that don't need version control.

---

## Project Structure

### calendarbot_lite/ (ACTIVE)
Alexa skill backend with ICS calendar processing:
- `server.py` - Web server and background tasks
- `routes/` - HTTP endpoints (Alexa, API, static)
- `alexa_*.py` - Alexa integration modules
- `lite_event_parser.py` - ICS parsing
- `lite_rrule_expander.py` - Recurring event expansion

### kiosk/ (PRIMARY PRODUCTION USE CASE)
Production-ready Raspberry Pi kiosk deployment system:
- `install-kiosk.sh` - Automated installer
- `docs/` - Comprehensive installation guides
- `config/` - Configuration files and watchdog script
- `service/` - systemd unit files
- See [kiosk/README.md](kiosk/README.md) for complete documentation

### tests/
- `tests/lite/` - Main test directory
- `tests/lite_tests/` - Additional tests
- `calendarbot_lite/test_*.py` - Co-located unit tests

### Configuration
- `.env` - Environment variables (see `.env.example`)
- `pyproject.toml` - Build config, coverage, pytest, ruff, mypy

---

## Key Commands

See [AGENTS.md](AGENTS.md) for complete command reference.

### Common Tasks
- **Run server**: `python -m calendarbot_lite`
- **Run tests**: `./run_lite_tests.sh --coverage`
- **Debug RRULE**: `python scripts/debug_recurring_events.py --env .env`
- **Format code**: `ruff format calendarbot_lite`

### Environment Variables
- `CALENDARBOT_ICS_URL` - ICS feed URL (required)
- `CALENDARBOT_WEB_PORT` - Server port (default: 8080)
- `CALENDARBOT_DEBUG` - Enable debug logging
- `CALENDARBOT_ALEXA_BEARER_TOKEN` - Alexa auth token

---

## Raspberry Pi Kiosk Deployment

The **`kiosk/`** directory provides a production-ready Raspberry Pi kiosk deployment system. **This is the PRIMARY production use case** for CalendarBot Lite.

### Quick Start

```bash
# 1. Configure
cd ~/calendarBot/kiosk
cp install-config.example.yaml install-config.yaml
nano install-config.yaml  # Set username and ICS URL

# 2. Install
sudo ./install-kiosk.sh --config install-config.yaml

# 3. Reboot to start kiosk
sudo reboot
```

### Key Features

- **Automated Installation**: One-command idempotent deployment
- **Auto-Login & X Session**: Console auto-login triggers kiosk display on boot
- **Watchdog Monitoring**: Progressive recovery (soft reload → browser restart → X restart)
- **Browser Heartbeat**: Detects stuck/frozen browsers via JavaScript

### Service Management

```bash
# Check service status
systemctl status calendarbot-lite@bencan.service
systemctl status calendarbot-kiosk-watchdog@bencan.service

# View watchdog logs
journalctl -u calendarbot-kiosk-watchdog@bencan.service -f

# Test browser heartbeat
curl -X POST http://127.0.0.1:8080/api/browser-heartbeat
```

See **[kiosk/README.md](kiosk/README.md)** and **[AGENTS.md - Raspberry Pi Kiosk Deployment](AGENTS.md#raspberry-pi-kiosk-deployment)** for complete documentation.

---

## Coverage Configuration

Code coverage is configured to **exclude the archived `calendarbot/` directory**:

- **Source**: `calendarbot_lite/` only
- **Excluded**: `calendarbot/*` (archived code)
- **Configuration**: [pyproject.toml](pyproject.toml#L390-L413)

Run coverage with: `./run_lite_tests.sh --coverage`

---

## Critical Patterns

### 1. Always Activate Virtual Environment
```bash
. venv/bin/activate  # Required before running any Python commands
```

### 2. Environment-Based Configuration
All config via `.env` file - no hardcoded values.

### 3. Async-First Architecture
- All I/O operations are async (aiohttp, aiosqlite)
- Tests use `asyncio_mode = auto`

### 4. Remote Development
- Use host IP, not localhost for browser testing
- Server binds to 0.0.0.0 by default

---

## Additional Resources

### Core Documentation
- **[AGENTS.md](AGENTS.md)** - **Complete development guide** (start here)
- **[README.md](README.md)** - Project overview
- **[calendarbot_lite/README.md](calendarbot_lite/README.md)** - Module documentation
- **[docs/](docs/)** - Additional documentation

### Kiosk Deployment
- **[kiosk/README.md](kiosk/README.md)** - Kiosk deployment overview
- **[kiosk/docs/AUTOMATED_INSTALLATION.md](kiosk/docs/AUTOMATED_INSTALLATION.md)** - Automated installation
- **[kiosk/docs/INSTALLATION_OVERVIEW.md](kiosk/docs/INSTALLATION_OVERVIEW.md)** - Architecture & workflow

---

## ARCHIVED: Legacy CalendarBot

The `calendarbot/` directory contains an archived terminal/web calendar application. **Do not modify this code unless explicitly instructed.**

For legacy architecture details, see [AGENTS.md - ARCHIVED section](AGENTS.md#L404-L425).

---

**Last Updated**: 2025-11-04
**Active Project**: calendarbot_lite/
**Kiosk Deployment**: kiosk/ (PRIMARY production use case)
**For complete guidance**: See [AGENTS.md](AGENTS.md)
