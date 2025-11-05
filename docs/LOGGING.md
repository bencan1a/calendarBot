# Logging Best Practices for CalendarBot Lite

This guide documents logging standards and best practices for the CalendarBot Lite codebase.

## Table of Contents

1. [Logging Infrastructure](#logging-infrastructure)
2. [Performance-Optimized Logging](#performance-optimized-logging)
3. [Log Level Guidelines](#log-level-guidelines)
4. [Correlation IDs and Request Tracing](#correlation-ids-and-request-tracing)
5. [Monitoring Logging](#monitoring-logging)
6. [Common Patterns](#common-patterns)
7. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)

---

## Logging Infrastructure

CalendarBot Lite uses Python's standard `logging` module with custom configuration optimized for Pi Zero 2W deployment.

### Configuration Files

- **[lite_logging.py](../calendarbot_lite/lite_logging.py)** - Central logging configuration
- **[monitoring_logging.py](../calendarbot_lite/monitoring_logging.py)** - Structured JSON logging for monitoring

### Environment Variables

- `CALENDARBOT_DEBUG` - Enable debug logging (values: `1`, `true`, `yes`)
- `CALENDARBOT_LOG_LEVEL` - Override root log level (values: `DEBUG`, `INFO`, `WARNING`, `ERROR`)

### Module Logger Setup

Every module should create a logger using `__name__`:

```python
import logging

logger = logging.getLogger(__name__)
```

This creates a hierarchical logger namespace (e.g., `calendarbot_lite.lite_parser`) that can be configured independently.

---

## Performance-Optimized Logging

**Critical Rule**: Always use %-formatting with lazy evaluation, never f-strings.

### ❌ BAD - F-string (Always Evaluated)

```python
logger.debug(f"Processing {len(events)} events")  # BAD: String evaluated even if DEBUG disabled
logger.info(f"User {user_id} logged in at {timestamp}")  # BAD: Wastes CPU
```

**Problem**: F-strings are evaluated **before** the logging call, wasting CPU cycles even when the log level is disabled.

### ✅ GOOD - %-formatting (Lazy Evaluation)

```python
logger.debug("Processing %d events", len(events))  # GOOD: Only evaluated if DEBUG enabled
logger.info("User %s logged in at %s", user_id, timestamp)  # GOOD: Efficient
```

**Benefit**: Arguments are only formatted if the log level is actually enabled, saving significant CPU on resource-constrained hardware like Pi Zero 2W.

### Performance Impact

On Pi Zero 2W with disabled DEBUG logs:
- **F-strings**: ~10-15% CPU overhead (always formats strings)
- **%-formatting**: ~0% overhead (skipped entirely when disabled)

---

## Log Level Guidelines

Use appropriate log levels to ensure effective monitoring and debugging.

### DEBUG

**When to use**: Detailed diagnostic information for troubleshooting development issues.

```python
logger.debug("Parsed event: %s", event.subject)
logger.debug("Cache hit for key: %s", cache_key)
logger.debug("RRULE expansion completed in %.2fs", elapsed_time)
```

**Do NOT log**: Sensitive data (passwords, tokens, private user data)

### INFO

**When to use**: General informational messages about normal system operation.

```python
logger.info("Server started on port %d", port)
logger.info("Generated morning summary in %.2fs", elapsed_time)
logger.info("Processed %d events successfully", event_count)
```

### WARNING

**When to use**: Recoverable issues that don't prevent operation but should be investigated.

```python
logger.warning("Failed to parse timezone %r, assuming UTC", timezone)
logger.warning("Cache miss for key %s", cache_key)
logger.warning("Rate limit approaching for IP %s", client_ip)
```

### ERROR

**When to use**: Errors that prevent a specific operation but don't crash the system.

```python
logger.error("Failed to fetch ICS from %s: %s", url, error_msg)
logger.error("Database connection failed: %s", error)
logger.error("Authentication failed for user %s", user_id)
```

### CRITICAL

**When to use**: Severe errors that may cause system shutdown.

```python
logger.critical("Database is unreachable, shutting down")
logger.critical("Out of memory, cannot continue")
```

### EXCEPTION

**When to use**: Log exceptions with full traceback (automatically sets level to ERROR).

```python
try:
    result = await risky_operation()
except Exception:
    logger.exception("Risky operation failed for input %s", input_data)
    raise
```

**Note**: Always use `logger.exception()` in exception handlers - it automatically captures the traceback.

---

## Correlation IDs and Request Tracing

CalendarBot Lite implements request correlation IDs for distributed tracing across async operations.

### Using Correlation IDs

```python
from calendarbot_lite.middleware import get_request_id

# Get current request ID
request_id = get_request_id()

# Log with correlation ID (automatically included in format)
logger.info("Processing request %s", request_id)
```

### Automatic Injection

The `CorrelationIdFilter` in [lite_logging.py](../calendarbot_lite/lite_logging.py) automatically adds `request_id` to all log records:

```python
# Log format includes %(request_id)s
"[%(asctime)s] [%(request_id)s] %(levelname)s - %(name)s - %(message)s"
```

### Request ID Propagation

Request IDs are:
- Generated at HTTP request entry points
- Propagated through async call chains using `contextvars`
- Included in HTTP client requests via `X-Request-ID` header

---

## Monitoring Logging

For structured monitoring and alerting, use the `MonitoringLogger` from [monitoring_logging.py](../calendarbot_lite/monitoring_logging.py).

### When to Use

Use `MonitoringLogger` for:
- Production health metrics
- System state changes
- Recovery actions
- Watchdog events

Use regular `logger` for:
- Development debugging
- General application flow
- Detailed diagnostic information

### Example Usage

```python
from calendarbot_lite.monitoring_logging import get_logger

monitoring_logger = get_logger("watchdog")

# Log structured event
monitoring_logger.info(
    "health.check.failed",
    "Health check failed after 3 attempts",
    details={
        "endpoint": "/health",
        "attempts": 3,
        "last_error": error_msg,
    },
    recovery_level=1,
)
```

### Structured Schema

Monitoring logs follow a consistent JSON schema:

```json
{
  "timestamp": "2025-01-04T12:00:00Z",
  "component": "watchdog",
  "level": "INFO",
  "event": "health.check.failed",
  "message": "Health check failed after 3 attempts",
  "details": {
    "endpoint": "/health",
    "attempts": 3
  },
  "request_id": "req-abc123",
  "recovery_level": 1
}
```

---

## Common Patterns

### Logging Exceptions

```python
try:
    result = await fetch_calendar()
except httpx.TimeoutException:
    logger.exception("Timeout fetching calendar from %s", url)
    # Handle timeout
except httpx.HTTPStatusError as e:
    logger.exception("HTTP error %d fetching calendar from %s", e.response.status_code, url)
    # Handle HTTP error
```

### Logging Performance Metrics

```python
import time

start_time = time.time()
result = await expensive_operation()
elapsed = time.time() - start_time

logger.info("Operation completed in %.2fs", elapsed)

if elapsed > threshold:
    logger.warning("Operation exceeded threshold: %.2fs > %ds", elapsed, threshold)
```

### Logging Data Structures

```python
# For small lists/dicts
logger.debug("Found %d events: %r", len(events), [e.subject for e in events[:5]])

# For large data structures (use summary)
logger.debug("Processing %d events, first: %s, last: %s",
             len(events), events[0].subject, events[-1].subject)
```

### Conditional Logging

```python
# Good: Check before expensive operations
if logger.isEnabledFor(logging.DEBUG):
    expensive_debug_data = compute_debug_info()
    logger.debug("Debug info: %s", expensive_debug_data)
```

---

## Anti-Patterns to Avoid

### ❌ Don't Use F-strings in Logging

```python
# BAD - Performance penalty
logger.debug(f"Processing {len(events)} events")
logger.info(f"User {user_id} at {timestamp}")

# GOOD - Lazy evaluation
logger.debug("Processing %d events", len(events))
logger.info("User %s at %s", user_id, timestamp)
```

### ❌ Don't Log Sensitive Data

```python
# BAD - Logs passwords/tokens
logger.debug("User credentials: %s", credentials)
logger.info("Bearer token: %s", token)

# GOOD - Redact sensitive data
logger.debug("User authenticated: %s", user_id)
logger.info("Token received (redacted)")
```

### ❌ Don't Use print() Statements

```python
# BAD - Bypasses logging infrastructure
print(f"Processing event: {event_id}")

# GOOD - Use proper logging
logger.info("Processing event: %s", event_id)
```

### ❌ Don't Create Loggers with Hardcoded Names

```python
# BAD - Breaks hierarchy
logger = logging.getLogger("my_logger")

# GOOD - Use __name__ for automatic hierarchy
logger = logging.getLogger(__name__)
```

### ❌ Don't Log Inside Tight Loops

```python
# BAD - Floods logs, kills performance
for event in events:
    logger.debug("Processing event %s", event.id)  # 1000+ log lines

# GOOD - Log summary
logger.debug("Processing %d events", len(events))
# Or log first/last
logger.debug("Processing events %s to %s", events[0].id, events[-1].id)
```

### ❌ Don't Swallow Exceptions Without Logging

```python
# BAD - Silent failure
try:
    result = risky_operation()
except Exception:
    pass  # Lost all error information!

# GOOD - Log then handle
try:
    result = risky_operation()
except Exception:
    logger.exception("Risky operation failed")
    raise  # Or handle appropriately
```

---

## Linting and Code Quality

A ruff rule prevents f-strings in logging calls:

```toml
[tool.ruff.lint.flake8-logging-format]
# Prevent f-strings in logging (G004 rule)
```

This rule catches patterns like:
```python
logger.debug(f"message {var}")  # ❌ Fails linting
logger.debug("message %s", var)  # ✅ Passes linting
```

---

## Summary

**Key Takeaways**:

1. ✅ **Always use %-formatting** with `logger` calls, never f-strings
2. ✅ Use `logger.exception()` in exception handlers for automatic tracebacks
3. ✅ Use appropriate log levels (DEBUG for diagnostics, INFO for operation, WARNING for issues, ERROR for failures)
4. ✅ Include correlation IDs for request tracing in distributed systems
5. ✅ Use `MonitoringLogger` for structured production metrics
6. ❌ Never log sensitive data (passwords, tokens, API keys)
7. ❌ Never use `print()` statements in production code
8. ❌ Avoid logging inside tight loops

**Performance**: On Pi Zero 2W, proper logging practices save 10-15% CPU by avoiding unnecessary string formatting.

---

**Last Updated**: 2025-01-04
**Related Documentation**:
- [lite_logging.py](../calendarbot_lite/lite_logging.py) - Logging configuration
- [monitoring_logging.py](../calendarbot_lite/monitoring_logging.py) - Structured monitoring
- [AGENTS.md](../AGENTS.md) - Development guidelines
