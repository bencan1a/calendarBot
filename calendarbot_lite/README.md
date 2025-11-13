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

**Rate Limiting (Security):**
- `CALENDARBOT_RATE_LIMIT_PER_IP` - Requests per minute per IP (default: 100)
- `CALENDARBOT_RATE_LIMIT_PER_TOKEN` - Requests per minute per bearer token (default: 500)
- `CALENDARBOT_RATE_LIMIT_BURST` - Max requests in burst window (default: 20)
- `CALENDARBOT_RATE_LIMIT_BURST_WINDOW` - Burst window in seconds (default: 10)

**Advanced/Testing:**
- `CALENDARBOT_NONINTERACTIVE` - Disable interactive prompts (true/false)
- `CALENDARBOT_TEST_TIME` - Override current time for testing (ISO format)
- `CALENDARBOT_PRODUCTION` - Enable production mode optimizations (true/false)

See `.env.example` for a complete reference with full CalendarBot vs calendarbot_lite variables.

Rate Limiting
-------------
CalendarBot Lite includes lightweight rate limiting to protect Alexa endpoints from DoS attacks. Rate limiting is automatically enabled for all Alexa API routes.

**Features:**
- **Per-IP Rate Limiting:** Limits requests per minute from each IP address
- **Per-Token Rate Limiting:** Limits requests per minute for each bearer token
- **Burst Protection:** Prevents rapid-fire attacks with short-window burst limits
- **Sliding Window Algorithm:** Accurate tracking without clock-related edge cases
- **In-Memory Storage:** No external dependencies (Redis, etc.) - suitable for Pi Zero 2W
- **Automatic Cleanup:** Background task removes expired tracking entries

**Default Limits:**
- Per IP: 100 requests/minute
- Per Token: 500 requests/minute
- Burst: 20 requests in 10 seconds

**HTTP Response Headers:**
Rate-limited responses include standard headers:
- `X-RateLimit-Limit-IP`: Maximum requests allowed per minute
- `X-RateLimit-Remaining-IP`: Remaining requests in current window
- `X-RateLimit-Reset`: Seconds until rate limit resets
- `Retry-After`: Seconds to wait before retrying (429 responses only)

**Monitoring:**
Rate limiter statistics are exposed in the `/api/health` endpoint:
```json
{
  "rate_limiting": {
    "total_requests": 1234,
    "rejected_requests": 5,
    "rejection_rate": 0.004,
    "tracked_ips": 3,
    "tracked_tokens": 1,
    "config": {
      "per_ip_limit": 100,
      "per_token_limit": 500,
      "burst_limit": 20,
      "burst_window_seconds": 10
    }
  }
}
```

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