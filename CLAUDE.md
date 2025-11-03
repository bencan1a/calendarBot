# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**For comprehensive development guidance, see [AGENTS.md](AGENTS.md)** - the complete reference for working with this codebase.

---

## ⚠️ CRITICAL: Active vs Archived Code

- **ACTIVE PROJECT**: `calendarbot_lite/` - Alexa skill backend (USE THIS)
- **ARCHIVED PROJECT**: `calendarbot/` - Legacy app (DO NOT USE unless explicitly instructed)

**Default to working in `calendarbot_lite/` for all development tasks.**

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

### tests/
- `tests/lite/` - Main test directory
- `tests/lite_tests/` - Additional tests
- `calendarbot_lite/test_*.py` - Co-located unit tests

### Configuration
- `.env` - Environment variables (see `.env.example`)
- `pyproject.toml` - Build config, coverage, pytest, ruff
- `pytest-lite.ini` - Lite test configuration

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

- **[AGENTS.md](AGENTS.md)** - **Complete development guide** (start here)
- **[README.md](README.md)** - Project overview
- **[calendarbot_lite/README.md](calendarbot_lite/README.md)** - Module documentation
- **[docs/](docs/)** - Additional documentation

---

## ARCHIVED: Legacy CalendarBot

The `calendarbot/` directory contains an archived terminal/web calendar application. **Do not modify this code unless explicitly instructed.**

For legacy architecture details, see [AGENTS.md - ARCHIVED section](AGENTS.md#L404-L425).

---

**Last Updated**: 2025-11-03
**Active Project**: calendarbot_lite/
**For complete guidance**: See [AGENTS.md](AGENTS.md)
