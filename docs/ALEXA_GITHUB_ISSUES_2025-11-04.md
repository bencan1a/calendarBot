# Alexa Integration GitHub Issues

**Generated:** 2025-11-04  
**Source:** Alexa Integration Code Review (docs/ALEXA_CODE_REVIEW_2025-11-04.md)  
**Total Issues:** 10 (3 High Priority, 4 Medium Priority, 3 Low Priority)  
**Estimated Effort:** 11 days

This document contains detailed GitHub issues for improvements identified in the Alexa integration code review. Issues are prioritized and ready for creation in the repository's issue tracker.

---

## High Priority Issues (Fix Immediately - 3 days)

### Issue #1: Fix Platform-Specific strftime Format (Windows Compatibility)

**Priority:** High  
**Effort:** 1 day  
**Labels:** bug, compatibility, alexa, high-priority

**Description:**

The codebase uses Unix-specific strftime format codes (`%-I`) that cause crashes on Windows systems. This prevents deployment and testing on Windows development environments.

**Problem Details:**

The `%-I` format code (hour without leading zero) is specific to Unix/Linux systems and is not supported on Windows. This causes runtime errors when the code is executed on Windows platforms.

**Affected Files:**
- `calendarbot_lite/alexa_handlers.py` (lines 863, 865)
- `calendarbot_lite/alexa_presentation.py` (lines 201, 203)

**Code Examples:**

```python
# Current problematic code:
time_str = end_local.strftime("%-I:%M %p").lower()
time_str = end_local.strftime("%-I:%M %p UTC").lower()
```

**Impact:**
- ❌ Application crashes on Windows systems
- ❌ Prevents local development on Windows
- ❌ Blocks Windows-based CI/CD pipelines
- ❌ Reduces developer accessibility

**Recommended Solution:**

Use cross-platform time formatting approaches:

```python
# Option 1: Use custom formatting function
def format_time_cross_platform(dt: datetime) -> str:
    """Format time without leading zeros, cross-platform compatible."""
    hour = dt.hour % 12 or 12  # Convert to 12-hour format
    return f"{hour}:{dt.minute:02d} {dt.strftime('%p').lower()}"

# Option 2: Strip leading zeros after formatting
time_str = end_local.strftime("%I:%M %p").lower().lstrip("0")

# Option 3: Use conditional formatting
import platform
if platform.system() == "Windows":
    time_str = end_local.strftime("%I:%M %p").lower().lstrip("0")
else:
    time_str = end_local.strftime("%-I:%M %p").lower()
```

**Testing Requirements:**
- [ ] Unit tests on Windows platform
- [ ] Unit tests on Linux platform
- [ ] Unit tests on macOS platform
- [ ] CI/CD validation on all platforms

**Acceptance Criteria:**
- Code runs successfully on Windows, Linux, and macOS
- Time formatting remains consistent across platforms
- All existing tests continue to pass
- New tests validate cross-platform compatibility

---

### Issue #2: Implement Rate Limiting for Alexa Endpoints

**Priority:** High  
**Effort:** 1 day  
**Labels:** security, enhancement, alexa, high-priority, DoS-protection

**Description:**

The Alexa integration endpoints currently lack rate limiting, making the application vulnerable to Denial of Service (DoS) attacks. An attacker could overwhelm the server with excessive requests.

**Problem Details:**

Without rate limiting, a malicious actor (or even misconfigured client) can:
- Exhaust server resources (CPU, memory, network)
- Cause service degradation for legitimate users
- Generate excessive cloud computing costs
- Trigger cascading failures in dependent services

**Affected Endpoints:**
- `POST /alexa` - Main Alexa skill webhook
- All handler methods in `calendarbot_lite/alexa_handlers.py`

**Current State:**
- ❌ No rate limiting middleware
- ❌ No per-IP request limits
- ❌ No per-token request limits
- ❌ No burst protection

**Recommended Solution:**

Implement aiohttp rate limiting middleware with multiple strategies:

```python
from aiohttp_ratelimit import rate_limit, RateLimitExceeded
from aiohttp import web

# Configuration
RATE_LIMITS = {
    "per_ip": 100,        # requests per minute per IP
    "per_token": 500,     # requests per minute per bearer token
    "burst": 20,          # max burst requests
}

# Middleware implementation
@rate_limit(
    max_requests=RATE_LIMITS["per_ip"],
    time_period=60,       # seconds
    storage_backend="memory"  # or Redis for distributed systems
)
async def alexa_handler(request: web.Request) -> web.Response:
    # Existing handler logic
    pass
```

**Implementation Steps:**
1. Add `aiohttp-ratelimit` dependency to requirements.txt
2. Create rate limiting middleware module
3. Configure per-IP and per-token limits
4. Add rate limit headers to responses (X-RateLimit-*)
5. Return 429 status with Retry-After header when exceeded
6. Add rate limit metrics to health endpoint
7. Document rate limits in API documentation

**Recommended Limits:**
- **Per IP:** 100 requests/minute (protects against IP-based attacks)
- **Per Bearer Token:** 500 requests/minute (protects against compromised tokens)
- **Burst Limit:** 20 requests/10 seconds (prevents burst attacks)

**Testing Requirements:**
- [ ] Unit tests for rate limiting logic
- [ ] Integration tests exceeding limits
- [ ] Load tests validating limits under stress
- [ ] Tests for 429 response format and headers

**Monitoring:**
- Add CloudWatch/Prometheus metrics for rate limit hits
- Alert on unusual rate limit patterns
- Track legitimate vs rejected requests ratio

**Acceptance Criteria:**
- Rate limiting middleware is active on all Alexa endpoints
- Proper HTTP 429 responses with Retry-After headers
- Rate limit metrics available in /api/health endpoint
- No performance degradation for normal traffic
- Documentation updated with rate limit policies

---

### Issue #3: Make Lambda Timezone Configurable (Hardcoded PST)

**Priority:** High  
**Effort:** 1 day  
**Labels:** bug, configuration, alexa, high-priority, internationalization

**Description:**

The AWS Lambda backend has a hardcoded Pacific timezone (`America/Los_Angeles`) in the morning summary handler, causing incorrect results for users in other timezones.

**Problem Details:**

The morning summary feature returns events based on PST/PDT regardless of the user's actual location, leading to:
- Wrong "morning" events for non-PST users
- Confusion about event timing
- Poor user experience for international users
- Violation of timezone handling best practices

**Affected Code:**

File: `calendarbot_lite/alexa_skill_backend.py` (line 268)

```python
# Current problematic code:
"timezone": "America/Los_Angeles",  # Default timezone, could be made configurable
```

**Impact:**
- ❌ Wrong results for users outside Pacific timezone
- ❌ Morning summary shows afternoon/evening events for other timezones
- ❌ Cannot deploy for international users
- ❌ Hardcoded values violate configuration management principles

**Recommended Solution:**

Make timezone configurable via environment variable with sensible fallback:

```python
import os
from zoneinfo import ZoneInfo

# In config_manager.py or environment setup
DEFAULT_TIMEZONE = os.getenv("CALENDARBOT_DEFAULT_TIMEZONE", "America/Los_Angeles")

# In alexa_skill_backend.py
def get_morning_summary_context(user_timezone: str | None = None) -> dict:
    """Get morning summary with user-specific or default timezone."""
    timezone = user_timezone or DEFAULT_TIMEZONE
    try:
        tz = ZoneInfo(timezone)
    except Exception:
        # Fall back to default if invalid timezone provided
        tz = ZoneInfo(DEFAULT_TIMEZONE)
    
    return {
        "timezone": timezone,
        # ... rest of context
    }
```

**Implementation Steps:**
1. Add `CALENDARBOT_DEFAULT_TIMEZONE` environment variable
2. Update config_manager.py to expose timezone setting
3. Modify alexa_skill_backend.py to use configurable timezone
4. Add timezone validation logic
5. Update .env.example with timezone documentation
6. Add timezone to request context (if available from Alexa API)
7. Update tests to validate timezone handling

**Environment Variable:**
```bash
# In .env or Lambda environment
CALENDARBOT_DEFAULT_TIMEZONE=America/Los_Angeles  # PST/PDT
# Other examples:
# CALENDARBOT_DEFAULT_TIMEZONE=America/New_York    # EST/EDT
# CALENDARBOT_DEFAULT_TIMEZONE=Europe/London       # GMT/BST
# CALENDARBOT_DEFAULT_TIMEZONE=Asia/Tokyo          # JST
```

**Advanced Consideration:**

Investigate if Alexa provides user timezone in request context:
```python
# Check if available in Alexa request
user_timezone = request.context.get("System", {}).get("device", {}).get("timeZone")
```

**Testing Requirements:**
- [ ] Unit tests with different timezone configurations
- [ ] Tests for invalid timezone handling
- [ ] Tests for missing timezone (fallback to default)
- [ ] Integration tests with morning summary across timezones
- [ ] Tests for daylight saving time transitions

**Documentation Updates:**
- Update .env.example with CALENDARBOT_DEFAULT_TIMEZONE
- Document supported timezone formats (IANA timezone database)
- Add troubleshooting guide for timezone issues
- Document how to determine user's Alexa device timezone

**Acceptance Criteria:**
- Timezone is configurable via environment variable
- Invalid timezones fall back gracefully to default
- Morning summary uses correct timezone
- All tests pass with different timezone configurations
- Documentation clearly explains timezone configuration

---

## Medium Priority Issues (Plan for Next Sprint - 5 days)

### Issue #4: Refactor Manual Timezone String Handling

**Priority:** Medium  
**Effort:** 2 days  
**Labels:** technical-debt, refactoring, alexa, medium-priority

**Description:**

The codebase has 4 instances of manual timezone string manipulation using `+ "Z"` suffix concatenation. This approach is fragile, error-prone, and bypasses proper datetime serialization utilities.

**Problem Details:**

Manual string concatenation for timezone suffixes:
- Bypasses timezone-aware datetime handling
- Is error-prone and hard to maintain
- Doesn't handle edge cases (leap seconds, DST transitions)
- Makes code less readable and intuitive
- Violates DRY principle (Don't Repeat Yourself)

**Affected Locations:**

1. `calendarbot_lite/alexa_handlers.py:780`
```python
"now_iso": self.iso_serializer(now) if self.iso_serializer else now.isoformat() + "Z",
```

2. `calendarbot_lite/alexa_utils.py:120`
```python
else (latest_start_utc.isoformat() + "Z" if latest_start_utc else None)
```

3. `calendarbot_lite/alexa_utils.py:125`
```python
else (latest_end_utc.isoformat() + "Z" if latest_end_utc else None)
```

4. Additional instances found in code review

**Problems with Current Approach:**

```python
# ❌ Manual concatenation - fragile
timestamp = datetime.utcnow().isoformat() + "Z"

# Issues:
# - Assumes datetime is already in UTC
# - No validation that datetime is timezone-aware
# - Inconsistent with datetime best practices
# - Hard to test and mock
```

**Recommended Solution:**

Create a centralized datetime serialization utility:

```python
# In calendarbot_lite/datetime_utils.py (new module)
from datetime import datetime, timezone
from typing import Optional

def serialize_datetime_utc(dt: datetime) -> str:
    """
    Serialize datetime to ISO 8601 UTC string with Z suffix.
    
    Args:
        dt: Datetime to serialize (timezone-aware or naive)
    
    Returns:
        ISO 8601 string with Z suffix (e.g., "2024-11-04T16:30:00Z")
    
    Raises:
        ValueError: If datetime is None
    """
    if dt is None:
        raise ValueError("Cannot serialize None datetime")
    
    # Convert to UTC if timezone-aware, assume UTC if naive
    if dt.tzinfo is not None:
        dt_utc = dt.astimezone(timezone.utc)
    else:
        dt_utc = dt.replace(tzinfo=timezone.utc)
    
    # Use proper ISO format with Z suffix
    return dt_utc.isoformat().replace("+00:00", "Z")


def serialize_datetime_optional(dt: Optional[datetime]) -> Optional[str]:
    """Serialize optional datetime, returning None if input is None."""
    return serialize_datetime_utc(dt) if dt is not None else None
```

**Refactored Usage:**

```python
# ✅ Proper serialization utility
from calendarbot_lite.datetime_utils import serialize_datetime_utc, serialize_datetime_optional

# In alexa_handlers.py
"now_iso": serialize_datetime_utc(now),

# In alexa_utils.py
serialize_datetime_optional(latest_start_utc),
serialize_datetime_optional(latest_end_utc),
```

**Benefits:**
- ✅ Centralized datetime handling logic
- ✅ Proper timezone awareness validation
- ✅ Consistent serialization across codebase
- ✅ Easier to test and mock
- ✅ Better error messages for debugging
- ✅ Follows DRY principle

**Implementation Steps:**
1. Create `calendarbot_lite/datetime_utils.py` module
2. Implement `serialize_datetime_utc()` and `serialize_datetime_optional()`
3. Add comprehensive unit tests (timezone-aware, naive, None, edge cases)
4. Replace all 4 manual concatenations with utility calls
5. Update existing tests to use new utilities
6. Add documentation and examples

**Testing Requirements:**
- [ ] Test with timezone-aware datetime
- [ ] Test with naive datetime (assumes UTC)
- [ ] Test with None (optional variant)
- [ ] Test timezone conversion (non-UTC to UTC)
- [ ] Test edge cases (midnight, leap seconds, DST)
- [ ] Validate ISO 8601 format compliance
- [ ] Performance tests (serialization overhead)

**Acceptance Criteria:**
- All manual `+ "Z"` concatenations replaced
- New datetime_utils module with full test coverage
- All existing tests continue to pass
- Code is more maintainable and readable
- Documentation includes usage examples

---

### Issue #5: Refine Exception Handling Specificity

**Priority:** Medium  
**Effort:** 2 days  
**Labels:** technical-debt, error-handling, alexa, medium-priority, debugging

**Description:**

The codebase has 31 instances of overly broad `except Exception` clauses that catch all exceptions indiscriminately. This makes debugging difficult, masks actual errors, and reduces observability.

**Problem Details:**

Broad exception handling has several issues:
- Catches unexpected errors (KeyboardInterrupt, SystemExit, etc.)
- Makes debugging harder (what error actually occurred?)
- Hides programming mistakes (typos, attribute errors)
- Reduces error tracking and alerting effectiveness
- Violates Python best practices (PEP 8)

**Current State:**
- 32 instances of `except Exception` in Alexa modules
- Minimal error context captured
- Generic error messages to users
- Difficult to trace root causes in production

**Example Problem Code:**

```python
# ❌ Too broad - catches everything
try:
    result = process_calendar_event(event)
    return format_response(result)
except Exception as e:
    logger.error(f"Error processing event: {e}")
    return error_response("Something went wrong")
```

**Issues with Above:**
- Catches `KeyboardInterrupt`, `SystemExit`, `MemoryError`
- No distinction between expected vs unexpected errors
- Generic error message doesn't help user or developer
- No error context (event details, stack trace)

**Recommended Solution:**

Use specific exception hierarchies and proper error handling:

```python
# ✅ Specific exception handling
from calendarbot_lite.alexa_exceptions import (
    AlexaRequestError,
    AlexaValidationError,
    AlexaAuthenticationError,
    CalendarFetchError,
)

try:
    result = process_calendar_event(event)
    return format_response(result)
except AlexaValidationError as e:
    logger.warning(f"Invalid event data: {e}", extra={"event_id": event.id})
    return error_response("I couldn't understand that event format")
except CalendarFetchError as e:
    logger.error(f"Calendar fetch failed: {e}", extra={"calendar_url": url})
    return error_response("I'm having trouble accessing your calendar")
except AlexaRequestError as e:
    logger.error(f"Request processing failed: {e}", exc_info=True)
    return error_response("I encountered an error processing your request")
except Exception as e:
    # Only catch truly unexpected errors
    logger.critical(f"Unexpected error: {e}", exc_info=True, extra={"event": event})
    # Re-raise or send to error tracking (Sentry, etc.)
    raise
```

**Implementation Strategy:**

1. **Phase 1: Identify Exception Categories (Day 1)**
   - Audit all 31 `except Exception` clauses
   - Categorize by error type:
     - Expected errors (validation, auth, not found)
     - Transient errors (network, timeout, rate limit)
     - Programming errors (attribute, type, key errors)
     - Critical errors (memory, system failures)

2. **Phase 2: Refactor High-Traffic Handlers (Day 1)**
   - Start with alexa_handlers.py (most critical)
   - Replace broad catches with specific exceptions
   - Add proper error context and logging
   - Test error paths thoroughly

3. **Phase 3: Refactor Supporting Modules (Day 2)**
   - Update alexa_presentation.py, alexa_precompute_stages.py
   - Ensure consistent error handling patterns
   - Add error recovery strategies where appropriate

**Exception Hierarchy Design:**

```python
# Expand existing alexa_exceptions.py
class AlexaError(Exception):
    """Base exception for all Alexa-related errors."""
    pass

class AlexaRequestError(AlexaError):
    """Request processing errors."""
    pass

class AlexaValidationError(AlexaRequestError):
    """Invalid request data."""
    pass

class AlexaAuthenticationError(AlexaRequestError):
    """Authentication/authorization failures."""
    pass

class AlexaResourceError(AlexaError):
    """Resource access errors."""
    pass

class CalendarFetchError(AlexaResourceError):
    """Calendar data fetch failures."""
    pass

class AlexaTimeoutError(AlexaResourceError):
    """Operation timeout."""
    pass
```

**Error Context Best Practices:**

```python
# Add structured context to errors
logger.error(
    "Calendar fetch failed",
    extra={
        "error_type": type(e).__name__,
        "calendar_url": url,
        "user_id": request.user_id,
        "request_id": request.request_id,
        "retry_count": retry_count,
    },
    exc_info=True,  # Include stack trace
)
```

**Testing Requirements:**
- [ ] Unit tests for each exception type
- [ ] Tests for error propagation
- [ ] Tests for error logging and context
- [ ] Integration tests for error scenarios
- [ ] Verify no regressions in error handling

**Monitoring Impact:**
- Better error categorization in logs
- Improved alerting (specific error types)
- Easier debugging with context
- Better error tracking in APM tools

**Acceptance Criteria:**
- Reduce `except Exception` instances from 31 to <10
- All remaining broad catches are justified with comments
- Specific exception types for all expected errors
- Comprehensive error context in logs
- All tests pass with refined error handling
- Documentation updated with error handling patterns

---

### Issue #6: Add Input Validation Limits (Resource Exhaustion Protection)

**Priority:** Medium  
**Effort:** 1 day  
**Labels:** security, validation, alexa, medium-priority

**Description:**

The Alexa integration lacks maximum length validation on user-provided input fields (meeting subjects, locations, descriptions), making it vulnerable to resource exhaustion attacks and storage abuse.

**Problem Details:**

Without input length limits:
- **Memory exhaustion**: Extremely long strings consume excessive RAM
- **Storage abuse**: Database/cache bloat from oversized data
- **Processing overhead**: String operations on huge inputs degrade performance
- **Response size issues**: Oversized responses may exceed Alexa limits
- **DoS vector**: Malicious actors can overwhelm system resources

**Current State:**
- ❌ No maximum length validation on event subjects
- ❌ No maximum length validation on event locations
- ❌ No maximum length validation on event descriptions
- ❌ No total request size limits

**Attack Scenario:**

```python
# Attacker sends event with massive subject line
{
    "event": {
        "subject": "A" * 1_000_000,  # 1MB subject line
        "location": "B" * 1_000_000,  # 1MB location
        "description": "C" * 1_000_000,  # 1MB description
    }
}

# System tries to process, format, and cache this massive event
# Results in:
# - High memory usage
# - Slow SSML generation
# - Cache bloat
# - Potential OOM (Out of Memory) crash
```

**Recommended Limits:**

Based on Alexa SSML constraints and reasonable usage:

```python
# Input validation limits
MAX_EVENT_SUBJECT_LENGTH = 200      # ~20 words
MAX_EVENT_LOCATION_LENGTH = 100     # ~10 words
MAX_EVENT_DESCRIPTION_LENGTH = 500  # ~50 words
MAX_EVENTS_PER_REQUEST = 100        # Pagination limit
MAX_REQUEST_SIZE = 1_000_000        # 1MB total request size
```

**Implementation Solution:**

```python
# In calendarbot_lite/alexa_models.py (Pydantic validation)
from pydantic import BaseModel, Field, validator

class EventData(BaseModel):
    """Event data with validation constraints."""
    
    subject: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Event subject/title"
    )
    
    location: Optional[str] = Field(
        None,
        max_length=100,
        description="Event location"
    )
    
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Event description"
    )
    
    @validator("subject", "location", "description")
    def strip_whitespace(cls, v):
        """Strip leading/trailing whitespace."""
        return v.strip() if v else v
    
    @validator("subject")
    def validate_subject_not_empty(cls, v):
        """Ensure subject is not empty after stripping."""
        if not v or not v.strip():
            raise ValueError("Event subject cannot be empty")
        return v


# Add request size middleware
async def request_size_limiter(request: web.Request, handler):
    """Reject requests exceeding size limit."""
    content_length = request.content_length
    if content_length and content_length > MAX_REQUEST_SIZE:
        return web.Response(
            status=413,  # Payload Too Large
            text=json.dumps({
                "error": "Request too large",
                "max_size": MAX_REQUEST_SIZE,
                "your_size": content_length,
            }),
        )
    return await handler(request)
```

**Error Response Format:**

```python
# When validation fails
{
    "error": "Validation failed",
    "details": {
        "field": "subject",
        "message": "Subject exceeds maximum length of 200 characters",
        "provided_length": 1500,
        "max_length": 200
    }
}
```

**User-Friendly Alexa Responses:**

```python
# Don't expose technical details to end users
if subject_too_long:
    return alexa_response(
        "That event title is too long. Please use a shorter title."
    )

if location_too_long:
    return alexa_response(
        "That location name is too long. Please use a shorter location."
    )
```

**Implementation Steps:**
1. Add length constants to configuration
2. Update Pydantic models with Field constraints
3. Add custom validators for edge cases
4. Implement request size middleware
5. Add validation error handling
6. Create user-friendly error messages for Alexa
7. Add comprehensive tests for limits
8. Document limits in API documentation

**Testing Requirements:**
- [ ] Test with inputs at exact limit (boundary test)
- [ ] Test with inputs exceeding limit by 1 character
- [ ] Test with empty strings
- [ ] Test with whitespace-only strings
- [ ] Test with Unicode characters (multi-byte)
- [ ] Test with emoji (can be 4+ bytes each)
- [ ] Test with very long request bodies
- [ ] Load test with maximum valid inputs

**Configuration:**

```python
# In .env or config_manager.py
CALENDARBOT_MAX_EVENT_SUBJECT_LENGTH=200
CALENDARBOT_MAX_EVENT_LOCATION_LENGTH=100
CALENDARBOT_MAX_EVENT_DESCRIPTION_LENGTH=500
CALENDARBOT_MAX_EVENTS_PER_REQUEST=100
CALENDARBOT_MAX_REQUEST_SIZE=1000000
```

**Monitoring:**
- Track validation failure rate
- Alert on unusual validation failure spikes
- Log attempted excessive sizes (potential attacks)
- Monitor average input sizes (baseline behavior)

**Acceptance Criteria:**
- All input fields have maximum length validation
- Pydantic models enforce constraints automatically
- Request size middleware rejects oversized requests
- User-friendly error messages for Alexa users
- Comprehensive test coverage for all limits
- Documentation updated with validation rules
- No performance degradation with valid inputs

---

### Issue #7: Add Request Correlation IDs (Observability Enhancement)

**Priority:** Medium  
**Effort:** Included in exception handling refactor (Issue #5)  
**Labels:** observability, enhancement, alexa, medium-priority, debugging

**Description:**

The Alexa integration lacks request correlation IDs, making it difficult to trace requests across distributed system components (Alexa -> API Gateway -> Lambda -> CalendarBot -> Calendar Service).

**Problem Details:**

Without correlation IDs:
- **Cannot trace request flow** across services
- **Debugging is difficult**: Logs from different services can't be correlated
- **Performance analysis is limited**: Can't track end-to-end latency
- **Error investigation is slow**: Finding related log entries is manual
- **Distributed tracing is impossible**: No way to construct request traces

**Current State:**
- ❌ No request ID in Alexa request handling
- ❌ No correlation ID in logs
- ❌ No trace context propagation
- ❌ Logs cannot be correlated across services

**Example Problem:**

```
# User reports: "Alexa said 'Something went wrong' at 2:34 PM"
# Developer tries to debug:

# Lambda logs:
[2024-11-04 14:34:12] ERROR: Calendar fetch failed

# CalendarBot logs:
[2024-11-04 14:34:11] INFO: Processing calendar request
[2024-11-04 14:34:12] ERROR: HTTP 503 from calendar service

# Calendar service logs:
[2024-11-04 14:34:12] ERROR: Database timeout

# Question: Are these logs related to the same request?
# Answer: Unknown! No correlation ID to link them.
```

**Recommended Solution:**

Implement request correlation ID tracking throughout the request lifecycle:

```python
# In calendarbot_lite/middleware/correlation_id.py (new module)
import uuid
from aiohttp import web
from contextvars import ContextVar

# Context variable for request correlation ID
request_id_var: ContextVar[str] = ContextVar("request_id", default=None)


@web.middleware
async def correlation_id_middleware(request: web.Request, handler):
    """
    Extract or generate correlation ID for request tracking.
    
    Priority:
    1. X-Amzn-Trace-Id from AWS ALB/API Gateway
    2. X-Request-ID from client
    3. Generate new UUID
    """
    # Try to get correlation ID from headers
    correlation_id = (
        request.headers.get("X-Amzn-Trace-Id") or
        request.headers.get("X-Request-ID") or
        request.headers.get("X-Correlation-ID") or
        str(uuid.uuid4())
    )
    
    # Store in context variable for access throughout request
    request_id_var.set(correlation_id)
    
    # Add to request for handler access
    request["correlation_id"] = correlation_id
    
    # Process request
    response = await handler(request)
    
    # Add correlation ID to response headers
    response.headers["X-Request-ID"] = correlation_id
    
    return response


def get_request_id() -> str:
    """Get current request correlation ID from context."""
    return request_id_var.get() or "no-request-id"
```

**Structured Logging Integration:**

```python
# In calendarbot_lite/logging_utils.py
import logging
import json
from datetime import datetime

class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to all log records."""
    
    def filter(self, record):
        record.request_id = get_request_id()
        return True


# Configure logging with correlation ID
def setup_logging():
    """Setup logging with correlation ID in all messages."""
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(request_id)s] %(levelname)s: %(message)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())
    
    logger = logging.getLogger("calendarbot_lite")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
```

**Structured JSON Logging (Production):**

```python
# JSON format for machine parsing (CloudWatch, ELK, etc.)
def log_json(level: str, message: str, **extra):
    """Log in JSON format with correlation ID."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "message": message,
        "request_id": get_request_id(),
        **extra,
    }
    print(json.dumps(log_entry))


# Usage in handlers
log_json(
    "INFO",
    "Processing Alexa request",
    intent=intent_name,
    user_id=user_id,
    event_count=len(events),
)
```

**Propagate to External Services:**

```python
# When calling calendar service or other APIs
async def fetch_calendar(url: str) -> bytes:
    """Fetch calendar with correlation ID in request."""
    headers = {
        "X-Request-ID": get_request_id(),
        "User-Agent": "CalendarBot/1.0",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            return await response.read()
```

**Alexa Request ID Integration:**

```python
# Alexa provides its own request ID - use it!
def extract_alexa_request_id(alexa_request: dict) -> str:
    """Extract Alexa's native request ID."""
    return alexa_request.get("request", {}).get("requestId", str(uuid.uuid4()))


# In Alexa handler
async def handle_alexa_request(request: web.Request) -> web.Response:
    """Handle Alexa request with correlation ID."""
    alexa_request = await request.json()
    
    # Use Alexa's request ID as correlation ID
    alexa_request_id = extract_alexa_request_id(alexa_request)
    request_id_var.set(alexa_request_id)
    
    logger.info(f"Processing Alexa request: {alexa_request_id}")
    # ... rest of handler
```

**Implementation Steps:**
1. Create correlation_id middleware module
2. Add ContextVar for request ID storage
3. Integrate with logging (add filter)
4. Update all loggers to include request ID
5. Add request ID to external service calls
6. Use Alexa requestId when available
7. Add request ID to error responses
8. Update monitoring dashboards to use request IDs

**Benefits:**
- ✅ **End-to-end request tracing** across all services
- ✅ **Faster debugging**: Find all logs for a specific request
- ✅ **Performance analysis**: Track request latency across components
- ✅ **Error investigation**: Correlate errors across services
- ✅ **Distributed tracing**: Build complete request traces
- ✅ **Production observability**: Essential for microservices

**Example Debug Workflow with Correlation IDs:**

```bash
# User reports error at specific time
# 1. Get correlation ID from Alexa logs
$ grep "2024-11-04 14:34:12" alexa_logs.txt | grep "requestId"
requestId: "abc123-def456-ghi789"

# 2. Find all related logs across all services
$ grep "abc123-def456-ghi789" all_logs.txt
[14:34:11] [abc123] INFO: Alexa request received: WhatsNextIntent
[14:34:11] [abc123] INFO: Fetching calendar from ICS_URL
[14:34:12] [abc123] ERROR: Calendar service returned 503
[14:34:12] [abc123] ERROR: Cannot process request: service unavailable
[14:34:12] [abc123] INFO: Returning error response to Alexa

# 3. Root cause identified: Calendar service was down
```

**Testing Requirements:**
- [ ] Test correlation ID generation
- [ ] Test correlation ID extraction from headers
- [ ] Test correlation ID in logs
- [ ] Test correlation ID in responses
- [ ] Test correlation ID propagation to external calls
- [ ] Test with Alexa requestId
- [ ] Integration test with full request flow

**Monitoring Integration:**
- CloudWatch: Filter logs by request ID
- X-Ray: Link traces by correlation ID
- APM tools: Track request by correlation ID
- Dashboards: Show request flow diagrams

**Acceptance Criteria:**
- Correlation ID middleware active on all routes
- All log messages include request ID
- Request ID returned in response headers
- Request ID propagated to external services
- Alexa requestId used when available
- Documentation includes debugging workflow
- Tests validate correlation ID functionality

---

## Low Priority Issues (Backlog - 3 days)

### Issue #8: Standardize Error Messages

**Priority:** Low  
**Effort:** 1 day  
**Labels:** enhancement, user-experience, alexa, low-priority

**Description:**

Error messages returned to Alexa users are inconsistent in tone, format, and helpfulness. Standardizing error messages improves user experience and makes the application feel more polished.

**Problem Details:**

Current issues with error messages:
- **Inconsistent tone**: Some formal, some casual
- **Varying detail levels**: Some too technical, some too vague
- **No actionable guidance**: Don't tell user how to fix issues
- **Brand inconsistency**: Don't match Alexa's conversational style
- **Localization gaps**: No i18n support for error messages

**Example Inconsistencies:**

```python
# Various error messages in current code:
"Sorry, something went wrong"
"I couldn't process that request"
"An error occurred while fetching your calendar"
"Unable to retrieve calendar events at this time"
"There was a problem accessing your calendar"
"Calendar service is unavailable"
```

**Recommended Solution:**

Create standardized error message patterns:

```python
# In calendarbot_lite/alexa_error_messages.py (new module)
from enum import Enum

class ErrorMessage(Enum):
    """Standardized error messages for Alexa responses."""
    
    # Calendar fetch errors
    CALENDAR_UNAVAILABLE = (
        "I'm having trouble accessing your calendar right now. "
        "Please try again in a few moments."
    )
    
    CALENDAR_INVALID_URL = (
        "I can't access your calendar. "
        "Please check that your calendar URL is configured correctly."
    )
    
    CALENDAR_TIMEOUT = (
        "Your calendar is taking too long to respond. "
        "Please try again in a moment."
    )
    
    # Validation errors
    NO_EVENTS_FOUND = (
        "I don't see any events on your calendar right now."
    )
    
    INVALID_TIME_RANGE = (
        "I didn't understand that time range. "
        "Try asking about today, tomorrow, or a specific day."
    )
    
    # Authentication errors
    AUTH_FAILED = (
        "I couldn't verify your request. "
        "Please check your Alexa app settings for CalendarBot."
    )
    
    # System errors
    INTERNAL_ERROR = (
        "I'm sorry, something unexpected happened. "
        "I've reported this issue and it should be fixed soon."
    )
    
    SERVICE_DEGRADED = (
        "CalendarBot is experiencing issues right now. "
        "Please try again in a few minutes."
    )


# Error message guidelines
ERROR_MESSAGE_GUIDELINES = {
    "tone": "Friendly, apologetic, helpful",
    "length": "1-2 sentences maximum",
    "technical_details": "Never expose to end users",
    "actionable": "Tell user what to do next when possible",
    "brand_voice": "Match Alexa's conversational style",
}
```

**Implementation Pattern:**

```python
# In handlers, use standardized messages
from calendarbot_lite.alexa_error_messages import ErrorMessage

try:
    events = await fetch_calendar()
except CalendarTimeoutError:
    return alexa_error_response(ErrorMessage.CALENDAR_TIMEOUT.value)
except CalendarInvalidURLError:
    return alexa_error_response(ErrorMessage.CALENDAR_INVALID_URL.value)
except Exception as e:
    logger.critical(f"Unexpected error: {e}", exc_info=True)
    return alexa_error_response(ErrorMessage.INTERNAL_ERROR.value)
```

**Categorized Error Messages:**

1. **Transient Errors** (user should retry):
   - Calendar unavailable
   - Service timeout
   - Rate limit exceeded

2. **Configuration Errors** (user needs to fix setup):
   - Invalid calendar URL
   - Missing bearer token
   - Incorrect timezone

3. **User Input Errors** (user needs to rephrase):
   - Invalid time range
   - Unrecognized intent
   - Missing required information

4. **System Errors** (internal issues):
   - Internal server error
   - Service degraded
   - Unexpected exception

**Testing Requirements:**
- [ ] Catalog all existing error messages
- [ ] Map errors to standardized messages
- [ ] Test each error scenario
- [ ] Verify tone consistency
- [ ] User testing for clarity
- [ ] Accessibility review (screen readers)

**Internationalization Support:**

```python
# Future: i18n support for error messages
from babel import Locale

ERROR_MESSAGES_i18n = {
    "en_US": ErrorMessage,
    "es_ES": ErrorMessageES,  # Spanish translations
    "fr_FR": ErrorMessageFR,  # French translations
}

def get_error_message(error_type: str, locale: str = "en_US") -> str:
    """Get localized error message."""
    messages = ERROR_MESSAGES_i18n.get(locale, ErrorMessage)
    return getattr(messages, error_type).value
```

**Acceptance Criteria:**
- All error messages use standardized patterns
- Consistent tone across all errors
- Clear, actionable guidance for users
- No technical details exposed to end users
- Documentation for error message guidelines
- Tests validate all error scenarios

---

### Issue #9: Add Cache Performance Metrics

**Priority:** Low  
**Effort:** 1 day  
**Labels:** enhancement, monitoring, alexa, low-priority, observability

**Description:**

The response cache (alexa_response_cache.py) lacks performance metrics, making it difficult to assess cache effectiveness, optimize hit rates, and diagnose performance issues.

**Problem Details:**

Without cache metrics:
- **Cannot assess cache effectiveness**: Don't know hit/miss rates
- **Cannot optimize cache strategy**: No data on what to cache
- **Cannot diagnose performance**: No visibility into cache overhead
- **Cannot capacity plan**: No data on cache memory usage
- **Cannot track trends**: No historical cache performance data

**Current State:**
- ❌ No cache hit/miss counters
- ❌ No cache size tracking
- ❌ No eviction statistics
- ❌ No performance timing data
- ❌ No cache metrics in /api/health endpoint

**Recommended Metrics:**

```python
# Key cache metrics to track
CACHE_METRICS = {
    "hits": "Number of cache hits",
    "misses": "Number of cache misses",
    "hit_rate": "Percentage of requests served from cache",
    "evictions": "Number of entries evicted (LRU)",
    "size": "Current number of cached entries",
    "memory_bytes": "Approximate memory usage",
    "avg_hit_time_ms": "Average time for cache hit",
    "avg_miss_time_ms": "Average time for cache miss",
    "oldest_entry_age_seconds": "Age of oldest cache entry",
}
```

**Implementation Solution:**

```python
# Enhanced cache with metrics tracking
from dataclasses import dataclass
from time import time
from typing import Dict, Any

@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    total_hit_time_ms: float = 0
    total_miss_time_ms: float = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    @property
    def avg_hit_time_ms(self) -> float:
        """Calculate average hit time."""
        return (self.total_hit_time_ms / self.hits) if self.hits > 0 else 0.0
    
    @property
    def avg_miss_time_ms(self) -> float:
        """Calculate average miss time."""
        return (self.total_miss_time_ms / self.misses) if self.misses > 0 else 0.0


class ResponseCacheWithMetrics:
    """Response cache with performance metrics tracking."""
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.metrics = CacheMetrics()
    
    async def get(self, key: str) -> Any | None:
        """Get from cache with metrics tracking."""
        start_time = time()
        
        if key in self.cache:
            # Cache hit
            self.metrics.hits += 1
            elapsed_ms = (time() - start_time) * 1000
            self.metrics.total_hit_time_ms += elapsed_ms
            return self.cache[key]
        else:
            # Cache miss
            self.metrics.misses += 1
            elapsed_ms = (time() - start_time) * 1000
            self.metrics.total_miss_time_ms += elapsed_ms
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        """Set cache entry with metrics tracking."""
        if len(self.cache) >= MAX_CACHE_SIZE:
            # Track eviction
            self.metrics.evictions += 1
            # Evict oldest entry (LRU)
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key]
        
        self.cache[key] = {
            "value": value,
            "timestamp": time(),
            "ttl": ttl,
        }
        self.metrics.size = len(self.cache)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current cache metrics."""
        return {
            "hits": self.metrics.hits,
            "misses": self.metrics.misses,
            "hit_rate": f"{self.metrics.hit_rate:.1f}%",
            "evictions": self.metrics.evictions,
            "size": self.metrics.size,
            "avg_hit_time_ms": f"{self.metrics.avg_hit_time_ms:.2f}",
            "avg_miss_time_ms": f"{self.metrics.avg_miss_time_ms:.2f}",
        }
```

**Health Endpoint Integration:**

```python
# Add cache metrics to /api/health endpoint
@routes.get("/api/health")
async def health_check(request: web.Request) -> web.Response:
    """Health check with cache metrics."""
    cache = request.app["response_cache"]
    
    return web.json_response({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "cache": cache.get_metrics(),
        "version": "1.0.0",
    })
```

**Monitoring Dashboard:**

```python
# Prometheus metrics export (optional)
from prometheus_client import Counter, Gauge, Histogram

cache_hits = Counter("cache_hits_total", "Total cache hits")
cache_misses = Counter("cache_misses_total", "Total cache misses")
cache_size = Gauge("cache_size_entries", "Current cache size")
cache_hit_time = Histogram("cache_hit_time_ms", "Cache hit latency")

# Update metrics in cache operations
cache_hits.inc()
cache_hit_time.observe(elapsed_ms)
```

**Testing Requirements:**
- [ ] Test metric collection for hits
- [ ] Test metric collection for misses
- [ ] Test eviction tracking
- [ ] Test timing accuracy
- [ ] Test metrics endpoint response
- [ ] Load test with metrics enabled
- [ ] Validate metric accuracy

**Alerting Rules:**

```yaml
# Example CloudWatch or Prometheus alerts
alerts:
  - name: LowCacheHitRate
    condition: cache_hit_rate < 50%
    duration: 5m
    action: notify_team
    
  - name: HighEvictionRate
    condition: cache_evictions > 100/min
    duration: 5m
    action: investigate_cache_size
```

**Acceptance Criteria:**
- Cache metrics tracked in real-time
- Metrics available in /api/health endpoint
- Low overhead (<1ms per operation)
- Historical metrics logged periodically
- Dashboard shows cache performance
- Alerts configured for anomalies
- Documentation explains metrics

---

### Issue #10: Implement Circuit Breaker for Calendar Service

**Priority:** Low  
**Effort:** 1 day  
**Labels:** enhancement, reliability, alexa, low-priority, resilience

**Description:**

The application lacks a circuit breaker pattern for the external calendar service dependency. When the calendar service is down or slow, the application continues making failing requests, wasting resources and degrading user experience.

**Problem Details:**

Without a circuit breaker:
- **Cascading failures**: Slow calendar service degrades entire application
- **Resource waste**: Continued requests to failing service
- **Poor user experience**: Long timeouts before showing errors
- **No fail-fast**: Users wait for timeout rather than quick failure
- **No automatic recovery**: Manual intervention required

**Circuit Breaker Pattern Benefits:**
- **Fail fast**: Return error immediately when service is down
- **Resource protection**: Stop making requests to failing service
- **Automatic recovery**: Periodically test if service is back
- **Graceful degradation**: Can serve cached data during outages
- **Better user experience**: Quick error responses vs long timeouts

**Recommended Solution:**

Implement circuit breaker using `aiobreaker` library:

```python
# Add to requirements.txt
aiobreaker==2.0.0

# In calendarbot_lite/circuit_breaker.py (new module)
from aiobreaker import CircuitBreaker, CircuitBreakerError
import logging

logger = logging.getLogger(__name__)

# Circuit breaker configuration
calendar_breaker = CircuitBreaker(
    fail_max=5,              # Open after 5 failures
    timeout_duration=60,     # Stay open for 60 seconds
    exclude=[],              # Exceptions that don't trigger breaker
    listeners=[],            # Event listeners
    name="calendar_service"
)

@calendar_breaker
async def fetch_calendar_with_breaker(url: str, http_client) -> bytes:
    """
    Fetch calendar with circuit breaker protection.
    
    Circuit states:
    - CLOSED: Normal operation, requests go through
    - OPEN: Service is down, fail fast without making requests
    - HALF_OPEN: Testing if service recovered, limited requests
    """
    logger.debug(f"Fetching calendar (breaker state: {calendar_breaker.state})")
    
    try:
        response = await http_client.get(url, timeout=30)
        response.raise_for_status()
        return await response.read()
    except Exception as e:
        logger.error(f"Calendar fetch failed: {e}")
        raise  # Will trigger circuit breaker


# Usage in handlers
async def get_calendar_events(request: web.Request):
    """Get calendar events with circuit breaker."""
    try:
        calendar_data = await fetch_calendar_with_breaker(
            url=ICS_URL,
            http_client=request.app["http_client"]
        )
        events = parse_calendar(calendar_data)
        return web.json_response({"events": events})
        
    except CircuitBreakerError:
        # Circuit is open - service is known to be down
        logger.warning("Circuit breaker OPEN - calendar service unavailable")
        
        # Option 1: Return cached data if available
        if cached_events := request.app["cache"].get("last_known_events"):
            return web.json_response({
                "events": cached_events,
                "warning": "Using cached data - calendar service unavailable"
            })
        
        # Option 2: Return friendly error
        return web.json_response({
            "error": "Calendar service is temporarily unavailable"
        }, status=503)
```

**Circuit Breaker States:**

```
CLOSED (Normal Operation)
  ↓ (5 failures)
OPEN (Fail Fast)
  ↓ (60 seconds timeout)
HALF_OPEN (Test Recovery)
  ↓ (success)         ↓ (failure)
CLOSED                OPEN
```

**Event Listeners for Monitoring:**

```python
# Track circuit breaker events
def on_circuit_open(breaker):
    """Called when circuit opens (service down)."""
    logger.error(f"Circuit breaker OPENED: {breaker.name}")
    # Send alert to monitoring
    send_alert("Calendar service circuit breaker opened")

def on_circuit_close(breaker):
    """Called when circuit closes (service recovered)."""
    logger.info(f"Circuit breaker CLOSED: {breaker.name}")
    # Send recovery notification
    send_alert("Calendar service circuit breaker closed - service recovered")

def on_circuit_half_open(breaker):
    """Called when testing service recovery."""
    logger.info(f"Circuit breaker HALF_OPEN: {breaker.name}")

# Register listeners
calendar_breaker.add_listener(on_circuit_open, breaker_open=True)
calendar_breaker.add_listener(on_circuit_close, breaker_closed=True)
calendar_breaker.add_listener(on_circuit_half_open, breaker_half_open=True)
```

**Configuration:**

```python
# Make circuit breaker configurable
CIRCUIT_BREAKER_CONFIG = {
    "fail_max": int(os.getenv("CALENDAR_BREAKER_FAIL_MAX", "5")),
    "timeout_duration": int(os.getenv("CALENDAR_BREAKER_TIMEOUT", "60")),
    "expected_exception": CalendarFetchError,
}

calendar_breaker = CircuitBreaker(**CIRCUIT_BREAKER_CONFIG)
```

**Graceful Degradation Strategy:**

```python
# Serve stale cached data during outages
async def get_calendar_with_fallback(request: web.Request):
    """Get calendar with fallback to cached data."""
    cache = request.app["cache"]
    
    try:
        # Try to get fresh data
        data = await fetch_calendar_with_breaker(ICS_URL)
        events = parse_calendar(data)
        
        # Update cache with fresh data
        cache.set("last_known_events", events, ttl=3600)
        
        return events
        
    except CircuitBreakerError:
        # Circuit open - use cached data if available
        if cached := cache.get("last_known_events"):
            logger.info("Serving cached events (circuit breaker open)")
            return cached
        else:
            raise CalendarUnavailableError("No cached data available")
```

**Metrics and Monitoring:**

```python
# Add circuit breaker metrics to health endpoint
@routes.get("/api/health")
async def health_check(request: web.Request) -> web.Response:
    """Health check with circuit breaker status."""
    return web.json_response({
        "status": "healthy",
        "circuit_breakers": {
            "calendar_service": {
                "state": calendar_breaker.state.name,  # CLOSED, OPEN, HALF_OPEN
                "failure_count": calendar_breaker.fail_counter,
                "last_failure": calendar_breaker.last_failure_time,
            }
        }
    })
```

**Testing Requirements:**
- [ ] Test circuit opens after threshold failures
- [ ] Test circuit stays open for timeout duration
- [ ] Test circuit transitions to half-open
- [ ] Test circuit closes on successful recovery
- [ ] Test fallback to cached data
- [ ] Test event listeners are called
- [ ] Integration test with failing service
- [ ] Load test with circuit breaker active

**Implementation Steps:**
1. Add aiobreaker dependency
2. Create circuit_breaker.py module
3. Wrap calendar fetch with circuit breaker
4. Add event listeners for monitoring
5. Implement graceful degradation with cache
6. Add circuit breaker metrics to health endpoint
7. Configure alerts for circuit breaker events
8. Add comprehensive tests
9. Document circuit breaker behavior

**Acceptance Criteria:**
- Circuit breaker protects calendar service calls
- Fail-fast when service is down (no long timeouts)
- Graceful degradation with cached data
- Automatic recovery testing
- Metrics available in health endpoint
- Alerts configured for circuit state changes
- Documentation explains circuit breaker behavior
- All tests pass with circuit breaker active

---

## Summary Statistics

**Total Issues:** 10  
**Estimated Effort:** 11 days

**Priority Breakdown:**
- **High Priority:** 3 issues (3 days) - Critical for production
- **Medium Priority:** 4 issues (5 days) - Important for robustness
- **Low Priority:** 3 issues (3 days) - Nice-to-have enhancements

**Category Breakdown:**
- **Security:** 2 issues (Rate limiting, Input validation)
- **Compatibility:** 1 issue (Windows strftime)
- **Configuration:** 1 issue (Hardcoded timezone)
- **Technical Debt:** 2 issues (Exception handling, Timezone strings)
- **Observability:** 2 issues (Correlation IDs, Cache metrics)
- **User Experience:** 1 issue (Error messages)
- **Reliability:** 1 issue (Circuit breaker)

**Impact Assessment:**
- **Critical (blocking deployment):** Issues #1, #3
- **High (security/reliability):** Issues #2, #6
- **Medium (maintainability):** Issues #4, #5, #7
- **Low (enhancements):** Issues #8, #9, #10

---

## Recommended Implementation Order

### Sprint 1: Critical Fixes (3 days)
1. Issue #1: Fix platform-specific strftime (Day 1)
2. Issue #2: Implement rate limiting (Day 2)
3. Issue #3: Make Lambda timezone configurable (Day 3)

### Sprint 2: Security & Robustness (3 days)
4. Issue #6: Add input validation limits (Day 1)
5. Issue #5: Refine exception handling (Days 2-3)

### Sprint 3: Observability & Quality (2 days)
6. Issue #4: Refactor timezone string handling (Day 1)
7. Issue #7: Add request correlation IDs (included in #5)
8. Issue #8: Standardize error messages (Day 2)

### Backlog: Enhancements (3 days)
9. Issue #9: Add cache performance metrics (Day 1)
10. Issue #10: Implement circuit breaker (Day 2)
11. Final review and documentation (Day 3)

---

## Issue Creation Checklist

When creating these issues in GitHub:

- [ ] Use issue title from heading (e.g., "Fix Platform-Specific strftime Format")
- [ ] Set priority label (high-priority, medium-priority, low-priority)
- [ ] Add component labels (alexa, security, compatibility, etc.)
- [ ] Add effort estimate in description
- [ ] Link to code review document (docs/ALEXA_CODE_REVIEW_2025-11-04.md)
- [ ] Set milestone based on recommended sprint
- [ ] Assign to appropriate team member(s)
- [ ] Add to project board
- [ ] Reference in commit messages when fixing

---

## Notes for Issue Creation

**GitHub Issue Templates:**

Use these labels consistently:
- Priority: `high-priority`, `medium-priority`, `low-priority`
- Type: `bug`, `enhancement`, `technical-debt`, `security`
- Component: `alexa`, `compatibility`, `configuration`, `observability`
- Effort: `1-day`, `2-days`, `3-days`

**Issue Numbering:**

These issues should be created as individual GitHub issues and referenced by number in subsequent PRs and commits.

**Cross-References:**

Each issue should reference:
- Parent review document: `docs/ALEXA_CODE_REVIEW_2025-11-04.md`
- Related issues (dependencies)
- Affected files and line numbers
- Test files that need updates

---

**Document Created:** 2025-11-04  
**Created By:** AI Principal Software Engineer  
**Source Review:** docs/ALEXA_CODE_REVIEW_2025-11-04.md  
**Status:** Ready for GitHub issue creation  
**Next Action:** Create individual GitHub issues from this document
