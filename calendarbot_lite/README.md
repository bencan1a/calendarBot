# calendarbot_lite

Lightweight, isolated skeleton for a minimal CalendarBot application intended for fast development
and experimentation without pulling in the full CalendarBot runtime.

Purpose
-------
calendarbot_lite will provide a small, self-contained server and tooling surface that reuses the
core ICS parsing code from the main CalendarBot project but keeps its runtime and configuration
surface intentionally small for easier iteration.

Isolation and reuse
-------------------
This package is isolated from the main project codebase. It intentionally does NOT copy or import
the full CalendarBot application at package import time. When appropriate, calendarbot_lite will
reuse the following existing parser modules from the main project:

- [`calendarbot/sources/ics_source.py`](calendarbot/sources/ics_source.py:1)

NOTE: Those modules will be imported only at runtime (inside server or workers) to avoid heavy
startup costs and ensure the package remains lightweight when inspected.

Configuration
-------------
calendarbot_lite uses environment variables for configuration. Create a `.env` file in the repository root or set environment variables directly:

**Core Settings:**
- `CALENDARBOT_ICS_URL` - ICS calendar feed URL (required)
- `CALENDARBOT_WEB_HOST` - Web server bind address (default: 0.0.0.0)
- `CALENDARBOT_WEB_PORT` - Web server port (default: 8080)
- `CALENDARBOT_REFRESH_INTERVAL` - Refresh interval in seconds (default: 300)

**Optional Settings:**
- `CALENDARBOT_ALEXA_BEARER_TOKEN` - Alexa API authentication token
- `CALENDARBOT_DEBUG` - Enable debug logging (true/false)
- `CALENDARBOT_LOG_LEVEL` - Log level override (DEBUG, INFO, WARNING, ERROR)

**Advanced/Testing:**
- `CALENDARBOT_NONINTERACTIVE` - Disable interactive prompts (true/false)
- `CALENDARBOT_TEST_TIME` - Override current time for testing (ISO format)
- `CALENDARBOT_PRODUCTION` - Enable production mode optimizations (true/false)

See `.env.example` for a complete reference with full CalendarBot vs calendarbot_lite variables.

Developer quickstart
--------------------
In development you can run the package with:

python -m calendarbot_lite

Where to add files
------------------
Add the runtime code under the package directory:

- `calendarbot_lite/server.py` - HTTP server and background tasks
- `calendarbot_lite/store.py` - lightweight skipped-store cache
- `tests/test_calendarbot_lite_server.py` - tests for server behavior

License & notes
---------------
This skeleton is intended to be a minimal first step. Keep imports inside functions to keep top-level
import cheap and fast for editor tooling and test discovery.