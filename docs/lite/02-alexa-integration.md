# Alexa Integration Component

**Component:** 2 of 5 - Alexa Voice Interface  
**Purpose:** Voice interface handlers, request validation, response generation, SSML rendering, caching  
**Last Updated:** 2025-11-03

---

## Table of Contents

1. [Overview](#overview)
2. [Core Modules](#core-modules)
3. [Key Interfaces & Data Structures](#key-interfaces--data-structures)
4. [Integration Points](#integration-points)
5. [Common Usage Patterns](#common-usage-patterns)
6. [Code Examples](#code-examples)
7. [Related Documentation](#related-documentation)

---

## Overview

### Purpose

The Alexa Integration component provides a voice interface for calendar queries, handling intent routing, request validation, response generation, and speech synthesis markup (SSML) formatting. It transforms calendar data into natural language responses optimized for voice interaction.

### Position in Architecture

This component bridges the HTTP Server layer and Calendar Processing layer, consuming calendar data and providing voice-optimized responses:

```
┌──────────────────────────────────────────────────┐
│     HTTP Server & Routing (Component 1)          │
│  /api/alexa/* routes → Alexa handlers             │
└───────────────┬──────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────┐
│     Alexa Integration (this component)            │
│  Handlers → Validation → Processing → SSML        │
└───────────────┬──────────────────────────────────┘
                │
                ├──────────────────┬──────────────────┐
                ▼                  ▼                  ▼
         Calendar Data       Infrastructure    Data Models
```

**References:**
- Architecture context: [`tmp/component_analysis.md`](../../tmp/component_analysis.md#L118-L203)
- HTTP entry points: [`docs/lite/01-server-http-routing.md`](01-server-http-routing.md#L195-L238)
- Full architecture: [`AGENTS.md`](../../AGENTS.md#L93-L139)

### Key Design Patterns

1. **Handler Registry Pattern** - Decorator-based registration for intent handlers
2. **Precomputation Pipeline** - Responses precomputed during refresh for <10ms latency
3. **Response Caching** - Version-aware cache invalidated on window updates
4. **SSML Generation** - Urgency-aware speech synthesis with fallback
5. **Protocol-Based Presentation** - Separation of business logic from formatting
6. **Exception Hierarchy** - Specific exception types for better error handling

---

## Core Modules

### Handler Framework

#### [`alexa_handlers.py`](../../calendarbot_lite/alexa_handlers.py) (51KB, ~1275 lines)

Core intent handler implementations with shared base class.

**Key Classes:**
- [`AlexaEndpointBase`](../../calendarbot_lite/alexa_handlers.py:50) - Base class with auth and validation
  - [`validate_params()`](../../calendarbot_lite/alexa_handlers.py:79) - Pydantic-based parameter validation
  - [`check_auth()`](../../calendarbot_lite/alexa_handlers.py:97) - Bearer token authentication
  - `handle()` - Abstract method for request processing
  
**Handler Implementations:**
- `NextMeetingHandler` - "What's my next meeting?" intent
- `TimeUntilHandler` - "How long until my next meeting?" intent
- `DoneForDayHandler` - "Am I done for the day?" intent
- `LaunchSummaryHandler` - Launch intent with day summary
- `MorningSummaryHandler` - Morning briefing with event list

**Responsibilities:**
- Request authentication via bearer token
- Query parameter validation using Pydantic models
- Event window access with thread-safe locking
- Meeting search and filtering (skip logic, time-based)
- Response generation (plain text + SSML)
- Cache integration for performance

**Key Features:**
- Shared meeting search logic across handlers
- Timezone-aware time formatting
- Integration with skipped events store
- Precomputed response support
- Error handling with specific exception types

#### [`alexa_registry.py`](../../calendarbot_lite/alexa_registry.py) (196 lines)

Decorator-based handler registration and routing system.

**Key Classes:**
- [`HandlerInfo`](../../calendarbot_lite/alexa_registry.py:16) - Handler metadata dataclass
  - `intent`: Alexa intent name (e.g., "GetNextMeetingIntent")
  - `route`: HTTP route path (e.g., "/api/alexa/next-meeting")
  - `handler_class`: Handler class to instantiate
  - `ssml_enabled`, `cache_enabled`, `precompute_enabled`: Feature flags

- [`AlexaHandlerRegistry`](../../calendarbot_lite/alexa_registry.py:39) - Central handler registry
  - [`register()`](../../calendarbot_lite/alexa_registry.py:58) - Decorator for handler registration
  - [`get_handlers()`](../../calendarbot_lite/alexa_registry.py:107) - Get all registered handlers
  - [`get_routes()`](../../calendarbot_lite/alexa_registry.py:128) - Get route → handler mapping

**Responsibilities:**
- Handler registration via decorators
- Intent → route → handler class mapping
- Handler metadata management
- Route generation for registration

**Usage Pattern:**
```python
@AlexaHandlerRegistry.register(
    intent="GetNextMeetingIntent",
    route="/api/alexa/next-meeting",
    description="Returns next upcoming meeting",
    ssml_enabled=True,
    cache_enabled=True,
    precompute_enabled=True
)
class NextMeetingHandler(AlexaEndpointBase):
    ...
```

#### [`alexa_precompute_stages.py`](../../calendarbot_lite/alexa_precompute_stages.py)

Pipeline stages for precomputing Alexa responses during event window refresh.

**Key Classes:**
- [`NextMeetingPrecomputeStage`](../../calendarbot_lite/alexa_precompute_stages.py:31) - Precompute next meeting response
  - `process()` - Find next meeting and generate cached response
  - Integrates with skip logic and timezone handling
  - Stores response in `context.extra["precomputed_responses"]`

**Responsibilities:**
- Precompute common queries during background refresh
- Generate responses for default timezone
- Store precomputed data for handler retrieval
- Reduce handler latency from ~100ms to <10ms

**Benefits:**
- Alexa handlers serve precomputed responses instantly
- Reduces CPU load during voice interactions
- Consistent responses within window version

---

### Response Generation

#### [`alexa_presentation.py`](../../calendarbot_lite/alexa_presentation.py)

Presentation layer separating business logic from response formatting.

**Key Protocols:**
- [`AlexaPresenter`](../../calendarbot_lite/alexa_presentation.py:20) - Protocol for response formatters
  - `format_next_meeting()` - Format meeting data to speech + SSML
  - `format_time_until()` - Format duration to speech + SSML
  - `format_done_for_day()` - Format end-of-day response
  - `format_launch_summary()` - Format launch summary
  - `format_morning_summary()` - Format morning briefing

**Implementation:**
- `SSMLPresenter` - Default presenter using SSML renderers
  - Takes dictionary of SSML renderer functions
  - Generates plain text + optional SSML for each response type
  - Handles renderer failures gracefully (falls back to plain text)

**Responsibilities:**
- Separate data gathering from presentation
- Generate speech-optimized text responses
- Invoke SSML renderers when available
- Provide consistent response format across handlers

**Design Benefits:**
- Business logic handlers don't know about SSML details
- Easy to add new output formats (e.g., cards, visual displays)
- Testable presentation logic separate from handler logic

#### [`alexa_ssml.py`](../../calendarbot_lite/alexa_ssml.py) (30KB, ~750 lines)

Speech Synthesis Markup Language (SSML) generation with urgency-aware formatting.

**Key Functions:**
- [`render_meeting_ssml()`](../../calendarbot_lite/alexa_ssml.py:42) - Full SSML for meeting announcement
  - Urgency-based pacing (fast for imminent, normal for distant)
  - Emphasis on meeting subject
  - Location and online meeting indicators
  
- `render_time_until_ssml()` - Time-until SSML with duration emphasis
- `render_done_for_day_ssml()` - End-of-day SSML
- `render_launch_summary_ssml()` - Launch summary SSML
- `render_morning_summary_ssml()` - Morning briefing SSML

**Urgency Thresholds:**
- Fast: <5 minutes (300s) - Higher speaking rate
- Standard: 5min - 1hr - Normal pacing
- Relaxed: >1 hour - Lower emphasis

**Configuration:**
```python
DEFAULT_CONFIG = {
    "enable_ssml": True,
    "ssml_max_chars": 500,
    "allowed_tags": {"speak", "prosody", "emphasis", "break"},
    "duration_threshold_long": 3600,   # Include if >60min
    "duration_threshold_short": 900,   # Include if <15min
    "title_max_chars": 50,
}
```

**Responsibilities:**
- Generate valid SSML markup
- Apply urgency-based speech parameters
- Escape special characters for XML safety
- Validate SSML length and structure
- Fallback to plain text on error

#### [`alexa_response_cache.py`](../../calendarbot_lite/alexa_response_cache.py)

Response caching tied to event window version for performance.

**Key Class:**
- [`ResponseCache`](../../calendarbot_lite/alexa_response_cache.py:18) - Version-aware response cache
  - [`generate_key()`](../../calendarbot_lite/alexa_response_cache.py:60) - Cache key from handler + params
  - [`get()`](../../calendarbot_lite/alexa_response_cache.py:88) - Retrieve cached response
  - [`set()`](../../calendarbot_lite/alexa_response_cache.py:100) - Store response in cache
  - [`invalidate_all()`](../../calendarbot_lite/alexa_response_cache.py:120) - Clear cache on window refresh

**Cache Key Format:**
```
{handler_name}:{window_version}:{param_hash}
Example: "NextMeetingHandler:0:5d41402abc4b2a76b9719d911017c592"
```

**Responsibilities:**
- Cache handler responses within window version
- Automatic invalidation on event window updates
- LRU eviction when max size reached
- Cache statistics tracking (hits, misses, evictions)

**Performance:**
- Max size: 100 entries (configurable)
- Key generation: <1ms (MD5 hash for speed, not security)
- Hit rate typically >80% for common queries

---

### Type Safety

#### [`alexa_models.py`](../../calendarbot_lite/alexa_models.py) (188 lines)

Pydantic models for request validation.

**Key Models:**
- [`AlexaRequestParams`](../../calendarbot_lite/alexa_models.py:12) - Base request parameters
  - `tz`: Optional IANA timezone identifier (validated)
  - [`validate_timezone()`](../../calendarbot_lite/alexa_models.py:21) - Timezone validation with ZoneInfo

- `NextMeetingRequestParams`, `TimeUntilRequestParams`, `DoneForDayRequestParams`, `LaunchSummaryRequestParams` - Handler-specific params (inherit from base)

- [`MorningSummaryRequestParams`](../../calendarbot_lite/alexa_models.py:75) - Complex params
  - `date`: Optional ISO date (YYYY-MM-DD)
  - `timezone`: IANA timezone (default: UTC)
  - `detail_level`: "brief" | "normal" | "detailed"
  - `prefer_ssml`: Boolean flag
  - `max_events`: 1-100 event limit

**Responsibilities:**
- Query parameter validation
- Timezone validation and parsing
- Type coercion and error messages
- Default value handling

**Benefits:**
- Catch invalid requests early
- Clear validation error messages
- Type hints for editor support
- Automatic documentation generation

#### [`alexa_types.py`](../../calendarbot_lite/alexa_types.py) (173 lines)

TypedDict definitions for response structures.

**Key Types:**
- [`AlexaMeetingInfo`](../../calendarbot_lite/alexa_types.py:11) - Meeting information dict
  - `subject`, `start_iso`, `seconds_until_start`
  - `duration_spoken`, `location`, `is_online_meeting`
  - `speech_text`, `ssml` (optional)

- [`AlexaNextMeetingResponse`](../../calendarbot_lite/alexa_types.py:37) - Next meeting response
- [`AlexaTimeUntilResponse`](../../calendarbot_lite/alexa_types.py:53) - Time-until response
- [`AlexaDoneForDayInfo`](../../calendarbot_lite/alexa_types.py:77) - Done-for-day data
- [`AlexaDoneForDayResponse`](../../calendarbot_lite/alexa_types.py:90) - Done-for-day response
- [`AlexaMorningSummaryResponse`](../../calendarbot_lite/alexa_types.py:160) - Morning summary response

**Responsibilities:**
- Type-safe response dictionaries
- IDE autocomplete for response fields
- Clear API contracts
- Eliminate need for `# type: ignore` comments

#### [`alexa_exceptions.py`](../../calendarbot_lite/alexa_exceptions.py) (101 lines)

Custom exception hierarchy for error handling.

**Exception Classes:**
- [`AlexaHandlerError`](../../calendarbot_lite/alexa_exceptions.py:9) - Base exception
- [`AlexaAuthenticationError`](../../calendarbot_lite/alexa_exceptions.py:18) - Auth failures (HTTP 401)
- [`AlexaValidationError`](../../calendarbot_lite/alexa_exceptions.py:30) - Invalid params (HTTP 400)
- [`AlexaTimezoneError`](../../calendarbot_lite/alexa_exceptions.py:43) - Timezone issues
- [`AlexaEventProcessingError`](../../calendarbot_lite/alexa_exceptions.py:55) - Event processing failures (HTTP 500)
- [`AlexaSSMLGenerationError`](../../calendarbot_lite/alexa_exceptions.py:67) - SSML generation failures (non-fatal)
- [`AlexaDataAccessError`](../../calendarbot_lite/alexa_exceptions.py:80) - Data access failures (HTTP 500)
- [`AlexaResponseGenerationError`](../../calendarbot_lite/alexa_exceptions.py:92) - Response serialization failures (HTTP 500)

**Responsibilities:**
- Specific exception types for different failure modes
- Clear error messages and context
- HTTP status code mapping
- Centralized exception handling in routes

---

## Key Interfaces & Data Structures

### Handler Protocol

Base class pattern used by all Alexa handlers:

```python
class AlexaEndpointBase(ABC):
    """Base class for Alexa endpoints with common logic."""
    
    # Subclass must specify parameter model
    param_model: type[BaseModel] = AlexaRequestParams
    
    def __init__(
        self,
        bearer_token: Optional[str],
        time_provider: Any,
        skipped_store: object | None,
        response_cache: Optional[Any] = None,
        precompute_getter: Optional[Any] = None,
    ):
        """Initialize with dependencies."""
        ...
    
    def validate_params(self, request: Any) -> BaseModel:
        """Validate query params using param_model."""
        ...
    
    def check_auth(self, request: Any) -> None:
        """Check bearer token authentication."""
        ...
    
    @abstractmethod
    async def handle(
        self,
        request: Any,
        event_window_ref: list[tuple[LiteCalendarEvent, ...]],
        window_lock: Any
    ) -> dict[str, Any]:
        """Process request and return response."""
        ...
```

### Response Structure

All Alexa responses follow this pattern:

```python
{
    # Core response data (handler-specific)
    "meeting": {...},           # NextMeeting
    "seconds_until_start": 300, # TimeUntil
    "has_meetings_today": True, # DoneForDay
    
    # Voice output (always present)
    "speech_text": "Your next meeting is Team Standup in 5 minutes",
    
    # Enhanced speech (optional, if SSML generated)
    "ssml": "<speak><prosody rate=\"fast\">...</prosody></speak>",
    
    # Visual display (optional)
    "card": {
        "title": "Next Meeting",
        "content": "Team Standup at 10:00 AM"
    }
}
```

### Precomputed Response Storage

Precomputed responses stored in pipeline context:

```python
# During refresh cycle (in precompute stage)
context.extra["precomputed_responses"] = {
    "next_meeting": {
        "meeting": {...},
        "speech_text": "...",
        "ssml": "...",
    },
    "time_until": {
        "seconds_until_start": 300,
        "duration_spoken": "5 minutes",
        "speech_text": "...",
    }
}

# Handler retrieval
if precompute_getter:
    precomputed = precompute_getter("next_meeting")
    if precomputed:
        return precomputed  # <10ms response time
```

### Cache Key Generation

Cache keys incorporate handler, window version, and parameters:

```python
# Generate cache key
cache = ResponseCache(max_size=100)
key = cache.generate_key(
    handler_name="NextMeetingHandler",
    params={"tz": "America/Los_Angeles"}
)
# Result: "NextMeetingHandler:0:5d41402abc4b2a76b9719d911017c592"

# Check cache
cached_response = cache.get(key)
if cached_response:
    return cached_response

# Process and cache
response = process_request()
cache.set(key, response)
```

---

## Integration Points

### Inbound Dependencies

The Alexa Integration component receives:

1. **HTTP Requests** - Via [`routes/alexa_routes.py`](../../calendarbot_lite/routes/alexa_routes.py)
   - Query parameters (timezone, date, detail level)
   - Bearer token in Authorization header
   - Request method and path

2. **Event Window** - From refresh loop via dependency injection
   - `event_window_ref`: Single-element list with event tuple
   - `window_lock`: asyncio.Lock for thread-safe access
   - Read-only access (handlers never modify window)

3. **Precomputed Responses** - From precompute pipeline
   - Stored in global dict during refresh cycle
   - Accessed via `precompute_getter` function
   - Keyed by handler name (e.g., "next_meeting")

4. **Configuration** - Via dependency injection
   - Bearer token for authentication
   - Time provider function
   - Skipped events store
   - Response cache instance

### Outbound Dependencies

The component depends on:

1. **Calendar Data** - Via event window
   - [`LiteCalendarEvent`](../../calendarbot_lite/lite_models.py:265) models
   - Event filtering and prioritization
   - Timezone-aware datetime handling

2. **Infrastructure** - Utility modules
   - [`timezone_utils`](../../calendarbot_lite/timezone_utils.py) - Timezone parsing and conversion
   - Time provider function for "now"
   - ISO serialization and duration formatting

3. **HTTP Server** - Response delivery
   - Returns JSON response dict
   - HTTP status codes (200, 400, 401, 500)
   - Error handling via exception types

### Data Flow

```
Alexa Request (POST /api/alexa/next-meeting?tz=America/Los_Angeles)
  ↓
Route Handler (alexa_routes.py)
  ↓
Handler Instance (NextMeetingHandler)
  ├─ validate_params() → Pydantic validation
  ├─ check_auth() → Bearer token check
  ├─ Check precomputed responses
  ├─ Check response cache
  ├─ Read event_window_ref (with lock)
  ├─ Filter events (skip logic, future only)
  ├─ Find next meeting
  ├─ Generate response data
  └─ Format with presenter (text + SSML)
  ↓
JSON Response
  {
    "meeting": {...},
    "speech_text": "...",
    "ssml": "..."
  }
```

---

## Common Usage Patterns

### Adding New Intent Handler

1. **Create handler class:**

```python
# In alexa_handlers.py
from .alexa_models import AlexaRequestParams
from .alexa_types import AlexaCustomResponse
from .alexa_registry import AlexaHandlerRegistry

@AlexaHandlerRegistry.register(
    intent="GetCustomIntent",
    route="/api/alexa/custom",
    description="Custom intent handler",
    ssml_enabled=True,
    cache_enabled=True,
    precompute_enabled=False
)
class CustomHandler(AlexaEndpointBase):
    """Handler for custom intent."""
    
    param_model = AlexaRequestParams  # Or custom params class
    
    def __init__(self, bearer_token, time_provider, skipped_store, **kwargs):
        super().__init__(bearer_token, time_provider, skipped_store, **kwargs)
        # Custom initialization
    
    async def handle(self, request, event_window_ref, window_lock):
        """Process custom intent."""
        # Validate params
        params = self.validate_params(request)
        
        # Check auth
        self.check_auth(request)
        
        # Read event window
        async with window_lock:
            window = tuple(event_window_ref[0])
        
        # Process events
        result = process_custom_logic(window, params)
        
        # Return response
        return {
            "custom_data": result,
            "speech_text": f"Your custom result is {result}",
            "ssml": None  # Or generate SSML
        }
```

2. **Register route (automatic via registry):**

Routes are automatically discovered from `AlexaHandlerRegistry.get_routes()` in [`routes/alexa_routes.py`](../../calendarbot_lite/routes/alexa_routes.py).

3. **Test handler:**

```python
# In tests/lite/unit/test_alexa_handlers.py
async def test_custom_handler_when_valid_request_then_returns_response():
    handler = CustomHandler(
        bearer_token="test_token",
        time_provider=lambda: datetime.now(timezone.utc),
        skipped_store=None
    )
    
    request = MockRequest(
        query={"tz": "UTC"},
        headers={"Authorization": "Bearer test_token"}
    )
    
    event_window_ref = [(test_event1, test_event2)]
    window_lock = asyncio.Lock()
    
    response = await handler.handle(request, event_window_ref, window_lock)
    
    assert response["speech_text"] == "Expected text"
    assert "custom_data" in response
```

### Working with Precomputed Responses

**Adding precomputation stage:**

```python
# In alexa_precompute_stages.py
class CustomPrecomputeStage:
    """Precompute custom handler responses."""
    
    def __init__(self, time_provider, skipped_store):
        self.time_provider = time_provider
        self.skipped_store = skipped_store
        self._name = "CustomPrecompute"
    
    @property
    def name(self) -> str:
        return self._name
    
    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Precompute custom response."""
        result = ProcessingResult(
            stage_name=self.name,
            events_in=len(context.events),
            events_out=len(context.events),
        )
        
        # Process events
        custom_data = compute_custom_data(context.events)
        
        # Store in extra
        if "precomputed_responses" not in context.extra:
            context.extra["precomputed_responses"] = {}
        
        context.extra["precomputed_responses"]["custom"] = {
            "custom_data": custom_data,
            "speech_text": f"Custom result: {custom_data}"
        }
        
        return result
```

**Using precomputed responses in handler:**

```python
async def handle(self, request, event_window_ref, window_lock):
    """Use precomputed response if available."""
    # Check precomputed
    if self.precompute_getter:
        precomputed = self.precompute_getter("custom")
        if precomputed:
            logger.info("Using precomputed custom response")
            return precomputed
    
    # Fallback to real-time processing
    return await self._process_realtime(request, event_window_ref, window_lock)
```

### Implementing SSML Renderer

**Create SSML renderer function:**

```python
# In alexa_ssml.py
def render_custom_ssml(
    data: dict[str, Any],
    config: Optional[dict[str, Any]] = None
) -> Optional[str]:
    """Render custom SSML markup.
    
    Args:
        data: Custom data dictionary
        config: Optional configuration overrides
    
    Returns:
        SSML string or None on error
    """
    try:
        cfg = {**DEFAULT_CONFIG, **(config or {})}
        
        if not cfg.get("enable_ssml", True):
            return None
        
        # Build SSML content
        parts = ['<speak>']
        
        if data.get("is_urgent"):
            parts.append('<prosody rate="fast">')
        
        parts.append('<emphasis level="strong">')
        parts.append(_escape_text_for_ssml(data.get("title", "")))
        parts.append('</emphasis>')
        
        if data.get("is_urgent"):
            parts.append('</prosody>')
        
        parts.append('</speak>')
        
        ssml = "".join(parts)
        
        # Validate
        if not _validate_ssml(ssml, cfg):
            return None
        
        return ssml
        
    except Exception:
        logger.exception("Custom SSML generation failed")
        return None
```

**Register renderer:**

```python
# In server.py or alexa_routes.py
ssml_renderers = {
    "meeting": render_meeting_ssml,
    "time_until": render_time_until_ssml,
    "custom": render_custom_ssml,  # Add new renderer
}

# Pass to handler via presenter
presenter = SSMLPresenter({"custom": ssml_renderers.get("custom")})
handler = CustomHandler(presenter=presenter, ...)
```

### Testing Alexa Handlers

**Unit test pattern:**

```python
import pytest
from unittest.mock import Mock
import asyncio
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_next_meeting_handler_when_has_meeting_then_returns_meeting():
    """Test NextMeetingHandler with valid meeting."""
    
    # Setup
    handler = NextMeetingHandler(
        bearer_token="test_token",
        time_provider=lambda: datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
        skipped_store=None,
        response_cache=None,
        precompute_getter=None,
    )
    
    # Mock request
    request = Mock()
    request.query = {"tz": "UTC"}
    request.headers = {"Authorization": "Bearer test_token"}
    
    # Mock event window
    event = LiteCalendarEvent(
        id="test-id",
        subject="Test Meeting",
        start_dt_utc=datetime(2025, 1, 1, 10, 30, tzinfo=timezone.utc),
        # ... other fields
    )
    event_window_ref = [(event,)]
    window_lock = asyncio.Lock()
    
    # Execute
    response = await handler.handle(request, event_window_ref, window_lock)
    
    # Assert
    assert response["meeting"] is not None
    assert response["meeting"]["subject"] == "Test Meeting"
    assert response["speech_text"] == "Your next meeting is Test Meeting in 30 minutes"
```

---

## Code Examples

### Complete Handler Implementation

```python
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

from .alexa_exceptions import AlexaValidationError
from .alexa_handlers import AlexaEndpointBase
from .alexa_registry import AlexaHandlerRegistry
from .alexa_types import AlexaMeetingInfo
from .lite_models import LiteCalendarEvent


class EventCountRequestParams(BaseModel):
    """Parameters for event count handler."""
    tz: Optional[str] = Field(None, description="IANA timezone")
    hours_ahead: int = Field(24, ge=1, le=168, description="Hours to look ahead")


@AlexaHandlerRegistry.register(
    intent="GetEventCountIntent",
    route="/api/alexa/event-count",
    description="Get count of events in next N hours",
    ssml_enabled=False,  # No SSML for this handler
    cache_enabled=True,
    precompute_enabled=False
)
class EventCountHandler(AlexaEndpointBase):
    """Handler for event count queries."""
    
    param_model = EventCountRequestParams
    
    async def handle(
        self,
        request: Any,
        event_window_ref: list[tuple[LiteCalendarEvent, ...]],
        window_lock: Any
    ) -> dict[str, Any]:
        """Get count of events in next N hours."""
        # Validate params
        params = self.validate_params(request)
        
        # Check auth
        self.check_auth(request)
        
        # Get current time
        now = self.time_provider()
        
        # Calculate time range
        cutoff = now + timedelta(hours=params.hours_ahead)
        
        # Read event window
        async with window_lock:
            window = tuple(event_window_ref[0])
        
        # Count events in range
        count = 0
        for event in window:
            if not isinstance(event.start.date_time, datetime):
                continue
            
            start_dt = event.start.date_time
            if start_dt >= now and start_dt < cutoff:
                # Check skip status
                if self.skipped_store and self.skipped_store.is_skipped(event.id):
                    continue
                count += 1
        
        # Generate response
        hours_text = f"{params.hours_ahead} hours" if params.hours_ahead != 1 else "1 hour"
        speech_text = f"You have {count} meetings in the next {hours_text}"
        
        if count == 0:
            speech_text = f"You have no meetings in the next {hours_text}"
        elif count == 1:
            speech_text = f"You have 1 meeting in the next {hours_text}"
        
        return {
            "event_count": count,
            "hours_ahead": params.hours_ahead,
            "speech_text": speech_text,
            "ssml": None
        }
```

### SSML Generation with Urgency

```python
def render_custom_announcement_ssml(
    event: dict[str, Any],
    config: Optional[dict[str, Any]] = None
) -> Optional[str]:
    """Render SSML for event announcement with urgency awareness."""
    try:
        cfg = {**DEFAULT_CONFIG, **(config or {})}
        
        if not cfg.get("enable_ssml", True):
            return None
        
        seconds_until = event.get("seconds_until_start", 3600)
        subject = event.get("subject", "Meeting")
        
        # Determine urgency
        if seconds_until < 300:  # <5 minutes
            rate = "fast"
            emphasis = "strong"
        elif seconds_until < 3600:  # <1 hour
            rate = "medium"
            emphasis = "moderate"
        else:
            rate = "medium"
            emphasis = "reduced"
        
        # Build SSML
        parts = ['<speak>']
        
        # Urgent meetings get faster pacing
        if rate != "medium":
            parts.append(f'<prosody rate="{rate}">')
        
        # Add emphasis on subject
        parts.append(f'<emphasis level="{emphasis}">')
        parts.append(_escape_text_for_ssml(subject))
        parts.append('</emphasis>')
        
        # Add timing
        if seconds_until < 300:
            parts.append(' <break time="0.3s"/> ')
            parts.append('<emphasis level="strong">starting soon</emphasis>')
        else:
            duration = event.get("duration_spoken", "")
            if duration:
                parts.append(f' {_escape_text_for_ssml(duration)}')
        
        if rate != "medium":
            parts.append('</prosody>')
        
        parts.append('</speak>')
        
        ssml = "".join(parts)
        
        # Validate length
        if len(ssml) > cfg.get("ssml_max_chars", 500):
            logger.warning("SSML too long, truncating")
            return None
        
        return ssml
        
    except Exception:
        logger.exception("SSML generation failed")
        return None
```

### Response Caching Pattern

```python
async def handle(self, request, event_window_ref, window_lock):
    """Handle request with caching."""
    # Validate and auth
    params = self.validate_params(request)
    self.check_auth(request)
    
    # Check cache
    if self.response_cache:
        cache_key = self.response_cache.generate_key(
            handler_name=self.__class__.__name__,
            params={"tz": params.tz or "UTC"}
        )
        
        cached = self.response_cache.get(cache_key)
        if cached:
            logger.debug("Cache hit for %s", cache_key)
            return cached
    
    # Process request
    response = await self._process_request(
        params, event_window_ref, window_lock
    )
    
    # Cache response
    if self.response_cache:
        self.response_cache.set(cache_key, response)
        logger.debug("Cached response for %s", cache_key)
    
    return response
```

---

## Related Documentation

### Component Documentation
- [Server & HTTP Routing](01-server-http-routing.md) - HTTP entry points and route registration
- [Component Analysis](../../tmp/component_analysis.md) - Architectural overview
- [AGENTS.md](../../AGENTS.md) - Developer guide and common patterns

### Related Components
- **Calendar Processing** (Component 3) - Event data consumed by Alexa handlers
- **Infrastructure** (Component 4) - Timezone utilities, async patterns, HTTP clients

### Module-Level Documentation
- [`alexa_handlers.py`](../../calendarbot_lite/alexa_handlers.py) - Handler implementations
- [`alexa_registry.py`](../../calendarbot_lite/alexa_registry.py) - Handler registration system
- [`alexa_ssml.py`](../../calendarbot_lite/alexa_ssml.py) - SSML generation
- [`routes/alexa_routes.py`](../../calendarbot_lite/routes/alexa_routes.py) - Route registration

### Testing
- [`tests/lite/unit/test_alexa_handlers.py`](../../tests/lite/unit/test_alexa_handlers.py) - Handler tests
- [`tests/lite/unit/test_alexa_registry.py`](../../tests/lite/unit/test_alexa_registry.py) - Registry tests
- [`tests/lite/unit/test_alexa_ssml.py`](../../tests/lite/unit/test_alexa_ssml.py) - SSML tests
- [`tests/lite/unit/test_alexa_integration.py`](../../tests/lite/unit/test_alexa_integration.py) - Integration tests

---

## Deployment & Security

### Authentication

**Bearer Token Approach:**
- Static bearer token stored in `CALENDARBOT_ALEXA_BEARER_TOKEN` environment variable
- Token transmitted over HTTPS in Authorization header
- No OAuth complexity - suitable for single-user home deployment

**Security Best Practices:**
- Token transmitted over HTTPS only (never HTTP)
- Token never exposed in URL parameters
- Rotate token periodically
- Use strong random token generation (32+ characters)

### Privacy Controls

**Data Minimization:**
- Only exposes next meeting information
- No historical or bulk calendar access
- Skipped meetings respected (privacy feature)
- No persistent storage - session-based access only

**Information Exposure:**
- Subject and start time only by default
- No attendee information shared with Alexa
- No meeting content or notes exposed
- Location data optional

**Local Processing:**
- Calendar data stays on user device
- No cloud storage of calendar data
- Logs retention configurable on device

### Network Security

**HTTPS Requirements:**
- All communication over HTTPS (TLS 1.2+)
- Valid TLS certificate required for production
- Self-signed certificates rejected by Alexa service

**Additional Security:**
- Rate limiting recommended (not implemented by default)
- IP allowlisting possible at reverse proxy level
- Firewall rules for port exposure

### Deployment Options

#### Option A: Local Network with Port Forwarding

**Setup:**
1. Run CalendarBot Lite on local device (Pi, NUC, server)
2. Configure router port forwarding (external port → device:8080)
3. Set up dynamic DNS (e.g., DuckDNS, No-IP) for stable hostname
4. Use Caddy or nginx for automatic HTTPS/LetsEncrypt
5. Deploy Alexa skill backend to AWS Lambda

**Configuration Example (Caddy):**
```
your-domain.duckdns.org {
    reverse_proxy localhost:8080
}
```

**Pros:**
- Simple setup, no monthly costs
- Full control over data and deployment
- No external dependencies beyond router

**Cons:**
- Requires router configuration access
- Security responsibility on user
- May not work with carrier-grade NAT

#### Option B: Secure Tunnel (Development)

**Setup:**
1. Run CalendarBot Lite locally
2. Use ngrok, localhost.run, or similar for HTTPS tunnel
3. Deploy Alexa skill backend with tunnel URL
4. Temporary/testing solution only

**Example:**
```bash
# Start CalendarBot Lite
python -m calendarbot_lite

# In another terminal, start tunnel
ngrok http 8080
```

**Pros:**
- No router configuration needed
- Quick setup for testing
- Works from any network

**Cons:**
- Tunnel dependency (service outage = downtime)
- Not recommended for production
- Free tier may have limitations

#### Option C: Cloud Proxy (Advanced)

**Setup:**
1. Deploy lightweight proxy on cloud VM (AWS EC2, DigitalOcean)
2. Proxy forwards requests to home device via VPN/WireGuard tunnel
3. CalendarBot Lite stays local for privacy
4. TLS termination at cloud proxy

**Architecture:**
```
Alexa → Cloud Proxy (HTTPS) → VPN Tunnel → Home Device (CalendarBot)
```

**Pros:**
- Professional setup with high availability
- Good security with VPN tunnel
- Static IP and reliable DNS

**Cons:**
- More complex setup and maintenance
- Ongoing cloud costs ($5-10/month)
- Requires VPN management

### Troubleshooting

**Common Issues:**

**"Unauthorized" responses:**
- Check `CALENDARBOT_ALEXA_BEARER_TOKEN` matches Lambda config
- Verify no extra spaces or newlines in token
- Ensure Authorization header format: `Bearer <token>`

**"Calendar access trouble" responses:**
- Verify CalendarBot Lite server is running
- Check HTTPS endpoint reachable from internet
- Test with curl from external network
- Check AWS CloudWatch logs for Lambda errors

**Alexa doesn't respond:**
- Verify skill is enabled in Alexa app
- Check interaction model is saved and built
- Test with Alexa Developer Console simulator first
- Check Lambda function has correct endpoint URL

**Network connectivity:**
- Test HTTPS endpoint: `curl https://your-domain.com/health`
- Verify TLS certificate is valid (no expired/self-signed)
- Check firewall/router port forwarding rules
- Ensure DNS resolves to correct IP

### Testing

**Manual Testing:**
```bash
# Test next meeting endpoint
curl -H "Authorization: Bearer your-token" \
     https://your-domain.com/api/alexa/next-meeting

# Test time-until endpoint
curl -H "Authorization: Bearer your-token" \
     https://your-domain.com/api/alexa/time-until-next
```

**Alexa Skill Testing:**
1. Use Alexa Developer Console simulator
2. Test on actual Alexa device
3. Check AWS CloudWatch logs for errors
4. Monitor CalendarBot Lite logs for requests

**Unit Tests:**
```bash
# Test authentication and handler logic
pytest tests/lite/unit/test_alexa_integration.py -v
pytest tests/lite/unit/test_alexa_handlers.py -v
```

### Error Responses

**HTTP Status Codes:**
- `200` - Success (meeting found or no meetings)
- `401` - Unauthorized (invalid/missing bearer token)
- `400` - Bad Request (invalid parameters)
- `500` - Internal server error

**Alexa Voice Responses:**
- Network errors: "Sorry, I'm having trouble accessing your calendar right now."
- No meetings: "You have no upcoming meetings."
- Auth errors: Logged but not exposed to user

---

## Quick Reference

### Key Entry Points
- **Route Registration:** [`register_alexa_routes()`](../../calendarbot_lite/routes/alexa_routes.py:14)
- **Handler Base:** [`AlexaEndpointBase`](../../calendarbot_lite/alexa_handlers.py:50)
- **Registry:** [`AlexaHandlerRegistry`](../../calendarbot_lite/alexa_registry.py:39)

### Common Handlers
- **Next Meeting:** `/api/alexa/next-meeting` → `NextMeetingHandler`
- **Time Until:** `/api/alexa/time-until-next` → `TimeUntilHandler`
- **Done For Day:** `/api/alexa/done-for-day` → `DoneForDayHandler`
- **Launch Summary:** `/api/alexa/launch-summary` → `LaunchSummaryHandler`
- **Morning Summary:** `/api/alexa/morning-summary` → `MorningSummaryHandler`

### Key Patterns
- **Handler Registration:** `@AlexaHandlerRegistry.register(...)` decorator
- **Request Validation:** Pydantic models with `validate_params()`
- **Authentication:** Bearer token check via `check_auth()`
- **Event Access:** Thread-safe lock with `async with window_lock`
- **Response Format:** `{"speech_text": str, "ssml": Optional[str], ...}`

### Performance Targets
- **Precomputed Responses:** <10ms response time
- **Cached Responses:** <50ms response time
- **Real-time Processing:** <200ms response time
- **SSML Generation:** <100ms per response

### Environment Variables
- `CALENDARBOT_ALEXA_BEARER_TOKEN` - Authentication token for Alexa endpoints
- `CALENDARBOT_PRODUCTION` - Enable response caching and optimizations

---

**End of Alexa Integration Documentation**