# CalendarBot Context
*Generated: 2025-11-13 23:20:51 UTC*

---

## Project Overview
**Project**: CalendarBot Lite
**Description**: A lightweight Alexa skill backend with ICS calendar processing for Raspberry Pi kiosk deployment

**Purpose**: Provide voice-based calendar queries via Alexa and 24/7 visual calendar display on a kiosk screen

### Primary Use Case
Raspberry Pi Zero 2W kiosk with 24/7 calendar display. The primary production deployment is a kiosk system showing calendar events on a dedicated screen, with Alexa voice integration as a secondary interface.

### Project Scale
- **Users**: 1-5 users (personal/family project)
- **Deployment**: Single instance on Raspberry Pi Zero 2W
- **Project Type**: Personal project - not enterprise scale

### Resource Constraints
- **Memory**: <100MB RAM idle, <150MB under load (Pi Zero 2W has 512MB total)
- **Cpu**: ARM Cortex-A53 quad-core 1GHz (single-threaded performance critical)
- **Startup Time**: <10 seconds for application startup
- **Disk**: SD card storage - minimize writes for longevity

### Codebase Structure
- **Active Development**: `calendarbot_lite/`
- **Archived (DO NOT MODIFY)**: `calendarbot/`

---

## API Documentation

*Extracted from Python docstrings in calendarbot_lite/*

### Package: `alexa`

#### `alexa/alexa_exceptions.py`

Custom exception hierarchy for Alexa handler errors.

This module provides specific exception types to replace generic Exception
handling throughout the Alexa integration code, enabling better error
diagnosis, proper HTTP status codes, and improved observability.

**Classes**:

- **AlexaHandlerError**
  Base exception for all Alexa handler errors.

All custom exceptions in the Alexa integration should inherit from this
base class to enable centralized exception handling and consistent error
responses...

- **AlexaAuthenticationError**
  Authentication or authorization failed.

Raised when:
- Bearer token is missing or invalid
- Authorization header is malformed
- User doesn't have permission to access the resource

Should result in H...

- **AlexaValidationError**
  Request validation failed.

Raised when:
- Query parameters are invalid or malformed
- Required parameters are missing
- Parameter values are out of valid range
- Timezone string is not a valid IANA t...

- **AlexaTimezoneError**
  Timezone parsing or conversion failed.

Raised when:
- Timezone string cannot be parsed
- ZoneInfo lookup fails
- Timezone conversion produces invalid results

This is a specialized validation error f...

- **AlexaEventProcessingError**
  Event processing or filtering failed.

Raised when:
- Event data cannot be parsed or accessed
- Event filtering logic encounters unexpected data
- Pipeline stage processing fails

Should result in HTT...

- **AlexaSSMLGenerationError**
  SSML generation failed.

Raised when:
- SSML renderer raises an exception
- SSML template is malformed
- SSML data interpolation fails

This is typically a non-fatal error - the handler should fall ba...

- **AlexaDataAccessError**
  Data access or retrieval failed.

Raised when:
- Skipped events store access fails
- Event window access encounters issues
- External data source is unavailable

Should result in HTTP 500 Internal Ser...

- **AlexaResponseGenerationError**
  Response generation or serialization failed.

Raised when:
- Response data cannot be serialized to JSON
- Response structure is invalid
- Required response fields are missing

Should result in HTTP 50...

#### `alexa/alexa_handlers.py`

Consolidated Alexa endpoint handlers with shared logic.

**Classes**:

- **AlexaEndpointBase**
  Base class for Alexa endpoints with common authentication and meeting search logic.

- **NextMeetingHandler**
  Handler for /api/alexa/next-meeting endpoint.

- **TimeUntilHandler**
  Handler for /api/alexa/time-until-next endpoint.

- **DoneForDayHandler**
  Handler for /api/alexa/done-for-day endpoint.

- **LaunchSummaryHandler**
  Handler for /api/alexa/launch-summary endpoint.

- **MorningSummaryHandler**
  Handler for /api/alexa/morning-summary endpoint.

**Functions**:

- **validate_params()**
  Validate request query parameters using the handler's param model.

Args:
    request: aiohttp request object

Returns:
    Validated parameters as a ...

- **check_auth()**
  Check if request has valid bearer token.

Args:
    request: aiohttp request object

Raises:
    AlexaAuthenticationError: If authentication fails

- **find_next_meeting()**
  Find the next upcoming non-skipped meeting.

Args:
    window: Tuple of LiteCalendarEvent objects
    now: Current UTC time
    skip_focus_time: Wheth...

#### `alexa/alexa_models.py`

Pydantic models for Alexa request validation.

**Classes**:

- **AlexaRequestParams**
  Base request parameters for all Alexa handlers.

Attributes:
    tz: Optional IANA timezone identifier (e.g., "America/Los_Angeles")

- **NextMeetingRequestParams**
  Request parameters for NextMeetingHandler.

Inherits all parameters from AlexaRequestParams.

- **TimeUntilRequestParams**
  Request parameters for TimeUntilHandler.

Inherits all parameters from AlexaRequestParams.

- **DoneForDayRequestParams**
  Request parameters for DoneForDayHandler.

Inherits all parameters from AlexaRequestParams.

- **LaunchSummaryRequestParams**
  Request parameters for LaunchSummaryHandler.

Inherits all parameters from AlexaRequestParams.

- **MorningSummaryRequestParams**
  Request parameters for MorningSummaryHandler.

Attributes:
    date: Optional ISO date string (YYYY-MM-DD) for which day to summarize
    timezone: IANA timezone identifier (defaults to server timezon...

- **Config**
  Pydantic model configuration.

**Functions**:

- **validate_timezone()**
  Validate timezone is a valid IANA timezone.

Args:
    v: Timezone string to validate

Returns:
    The validated timezone string

Raises:
    ValueEr...

- **validate_timezone()**
  Validate timezone is a valid IANA timezone.

Args:
    v: Timezone string to validate

Returns:
    The validated timezone string

Raises:
    ValueEr...

- **validate_date()**
  Validate date is a valid ISO date string.

Args:
    v: Date string to validate

Returns:
    The validated date string

Raises:
    ValueError: If da...

- **parse_prefer_ssml()**
  Parse prefer_ssml from string to boolean if needed.

Args:
    data: Raw data dictionary

Returns:
    Processed data dictionary

- **parse_max_events()**
  Parse max_events from string to int if needed.

Args:
    data: Raw data dictionary

Returns:
    Processed data dictionary

Raises:
    ValueError: I...

#### `alexa/alexa_precompute_stages.py`

Precomputation stages for Alexa responses.

This module provides pipeline stages that precompute Alexa responses during
event window refresh, allowing handlers to serve precomputed responses
for common queries without reprocessing events.

The precomputed responses are stored in context.extra["precomputed_responses"]
and can be accessed by handlers to provide <10ms response times.

**Classes**:

- **NextMeetingPrecomputeStage**
  Precompute next meeting response for default timezone.

This stage finds the next upcoming meeting and generates a response
compatible with the NextMeetingHandler, caching it for quick retrieval.

- **TimeUntilPrecomputeStage**
  Precompute time until next meeting for default timezone.

This stage computes when the next meeting starts, optimized
for the TimeUntilHandler endpoint.

- **DoneForDayPrecomputeStage**
  Precompute done-for-day response for default timezone.

This stage determines when the user will be done with meetings today
and generates a response compatible with the DoneForDayHandler.

**Functions**:

- **create_alexa_precompute_pipeline()**
  Create pipeline for precomputing Alexa responses.

Args:
    skipped_store: Optional store for skipped events
    default_tz: Default timezone for pre...

- **name()**
  Name of this processing stage.

- **name()**
  Name of this processing stage.

- **name()**
  Name of this processing stage.

#### `alexa/alexa_presentation.py`

Presentation layer for Alexa responses - separates business logic from SSML formatting.

This module provides a clean separation between business logic (data gathering) and
presentation logic (formatting responses for Alexa). The Protocol-based interface
allows for easy testing and addition of new output formats.

**Classes**:

- **AlexaPresenter**
  Protocol defining the interface for Alexa response presenters.

Presenters are responsible for formatting data into speech-ready responses,
either as plain text or SSML. This separation allows busines...

- **PlainTextPresenter**
  Plain text presenter that generates speech without SSML.

This presenter is useful for testing, debugging, and scenarios where
SSML is not required or supported.

- **SSMLPresenter**
  SSML presenter that generates enhanced speech with SSML markup.

This presenter wraps existing SSML renderers and provides a unified
interface for SSML generation across all Alexa handlers.

**Functions**:

- **format_next_meeting()**
  Format next meeting data into speech and optional SSML.

Args:
    meeting_data: Dictionary with meeting info (subject, seconds_until_start, etc.)
   ...

- **format_time_until()**
  Format time until next meeting into speech and optional SSML.

Args:
    seconds_until: Seconds until next meeting (0 if no meeting)
    meeting_data:...

- **format_done_for_day()**
  Format done-for-day response into speech and optional SSML.

Args:
    has_meetings_today: Whether user has meetings today
    speech_text: Pre-genera...

- **format_launch_summary()**
  Format launch summary into speech and optional SSML.

Args:
    done_info: Done-for-day information
    primary_meeting: Primary meeting to highlight ...

- **format_morning_summary()**
  Format morning summary into speech and optional SSML.

Args:
    summary_result: MorningSummaryResult object

Returns:
    Tuple of (speech_text, opti...

- **format_next_meeting()**
  Format next meeting as plain text.

- **format_time_until()**
  Format time until as plain text.

- **format_done_for_day()**
  Format done-for-day as plain text.

- **format_launch_summary()**
  Format launch summary as plain text with full speech generation.

This method generates the complete speech text including done-for-day information.

...

- **format_morning_summary()**
  Format morning summary as plain text.

#### `alexa/alexa_protocols.py`

Protocol definitions for Alexa handler dependencies.

This module defines Protocol types for better type safety in Alexa handlers,
replacing generic 'Any' type hints with explicit interface contracts.

**Classes**:

- **TimeProvider**
  Protocol for time provider callables.

- **SkippedStore**
  Protocol for skipped events storage.

- **DurationFormatter**
  Protocol for duration formatting callables.

- **ISOSerializer**
  Protocol for datetime ISO serialization.

- **TimezoneGetter**
  Protocol for getting server timezone.

- **PrecomputeGetter**
  Protocol for getting precomputed responses.

- **AlexaPresenter**
  Protocol for Alexa response presenters.

Presenters format data for Alexa responses, separating
business logic from presentation concerns.

**Functions**:

- **is_skipped()**
  Check if an event is marked as skipped.

Args:
    event_id: Event identifier

Returns:
    True if event is skipped, False otherwise

- **format_next_meeting()**
  Format next meeting data for speech.

Args:
    meeting_data: Meeting data dict with subject, time, etc. (None if no meetings)

Returns:
    Tuple of ...

- **format_time_until()**
  Format time until meeting for speech.

Args:
    seconds_until: Seconds until next meeting (0 if none)
    meeting_data: Optional meeting data dict

R...

- **format_done_for_day()**
  Format done-for-day information for speech.

Args:
    has_meetings_today: Whether user has meetings today
    speech_text: Pre-generated speech text
...

- **format_launch_summary()**
  Format launch summary into speech and optional SSML.

Args:
    done_info: Done-for-day information
    primary_meeting: Next upcoming meeting (or Non...

- **format_morning_summary()**
  Format morning summary into speech and optional SSML.

Args:
    summary_result: MorningSummaryResult object

Returns:
    Tuple of (speech_text, opti...

#### `alexa/alexa_registry.py`

Registry pattern for Alexa intent handlers.

This module provides a decorator-based registry system for registering Alexa intent handlers.
New intents can be added by simply decorating the handler class.

**Classes**:

- **HandlerInfo**
  Metadata about a registered Alexa handler.

Attributes:
    intent: The Alexa intent name (e.g., "GetNextMeetingIntent")
    route: The HTTP route path (e.g., "/api/alexa/next-meeting")
    handler_cl...

- **AlexaHandlerRegistry**
  Registry for Alexa intent handlers.

Provides a decorator-based system for registering handlers and
automatically generating routes.

Example:
    @AlexaHandlerRegistry.register(
        intent="GetNe...

**Functions**:

- **get_handler_info_summary()**
  Get a summary of all registered handlers.

Returns:
    Formatted string with handler information

Example:
    >>> print(get_handler_info_summary())
...

- **register()**
  Decorator to register an Alexa handler.

Args:
    intent: Alexa intent name (e.g., "GetNextMeetingIntent")
    route: HTTP route path (e.g., "/api/al...

- **get_handlers()**
  Get all registered handlers.

Returns:
    Dictionary mapping intent names to HandlerInfo objects

- **get_handler()**
  Get a specific handler by intent name.

Args:
    intent: Alexa intent name

Returns:
    HandlerInfo object or None if not found

- **get_routes()**
  Get all registered routes.

Returns:
    Dictionary mapping route paths to HandlerInfo objects

- **clear()**
  Clear all registered handlers.

Note: This is primarily useful for testing.

- **list_intents()**
  List all registered intent names.

Returns:
    List of intent names

- **list_routes()**
  List all registered route paths.

Returns:
    List of route paths

- **decorator()**
  Register the handler class and return it unchanged.

#### `alexa/alexa_response_cache.py`

Response caching for Alexa handlers tied to event window version.

This module provides a cache for Alexa responses that automatically invalidates
when the event window is refreshed. Cache keys are based on handler name and
request parameters, ensuring consistent responses within a window version.

**Classes**:

- **ResponseCache**
  Cache for Alexa responses tied to event window version.

The cache automatically invalidates all entries when the event window
is refreshed, ensuring responses stay synchronized with current events.
E...

**Functions**:

- **generate_key()**
  Generate cache key from handler and params.

The key incorporates:
- Handler name (ensures different handlers don't collide)
- Window version (auto-in...

- **get()**
  Get cached response if valid.

Args:
    key: Cache key from generate_key()

Returns:
    Cached response dict or None if not found/invalid

- **set()**
  Cache response for current window version.

Args:
    key: Cache key from generate_key()
    response: Response dict to cache

- **invalidate_all()**
  Invalidate all cached responses (call on window refresh).

This increments the window version, which causes all existing
cache entries to be considere...

- **get_stats()**
  Get cache statistics.

Returns:
    Dict with cache statistics including:
    - hits: Number of cache hits
    - misses: Number of cache misses
    - ...

- **clear_stats()**
  Clear cache statistics (useful for testing).

#### `alexa/alexa_skill_backend.py`

Amazon Alexa Skill Backend for CalendarBot Lite Integration

This module provides an AWS Lambda handler that integrates with calendarbot_lite
to answer calendar queries via Alexa voice interface.

Usage:
- Deploy as AWS Lambda function
- Configure CALENDARBOT_ENDPOINT and CALENDARBOT_BEARER_TOKEN environment variables
- Register as Alexa Custom Skill endpoint

Supported Intents:
- GetNextMeetingIntent: "What's my next meeting?"
- GetTimeUntilNextMeetingIntent: "How long until my next meeting?"

**Classes**:

- **AlexaResponse**
  Helper class to build Alexa response format with SSML support.

**Functions**:

- **get_default_timezone()**
  Get default timezone from environment with validation.

Returns:
    Valid IANA timezone string (defaults to America/Los_Angeles)

Note:
    This func...

- **call_calendarbot_api()**
  Call calendarbot_lite API endpoint with authentication.

Args:
    endpoint_path: API path (e.g., "/api/alexa/next-meeting")

Returns:
    JSON respon...

- **handle_get_next_meeting_intent()**
  Handle GetNextMeetingIntent - returns next meeting info with SSML support.

- **handle_get_time_until_next_meeting_intent()**
  Handle GetTimeUntilNextMeetingIntent - returns time until next meeting with SSML support.

- **handle_get_done_for_day_intent()**
  Handle GetDoneForDayIntent - returns done for the day summary with SSML support.

- **handle_launch_intent()**
  Handle LaunchRequest with intelligent context switching.

During the day (when there are still meetings left today):
- Use existing behavior: call /ap...

- **handle_help_intent()**
  Handle AMAZON.HelpIntent.

- **handle_stop_intent()**
  Handle AMAZON.StopIntent and AMAZON.CancelIntent.

- **lambda_handler()**
  AWS Lambda handler for Alexa skill requests.

Args:
    event: Alexa request event
    context: Lambda context (unused)

Returns:
    Alexa response d...

#### `alexa/alexa_ssml.py`

Enhanced SSML speech response generation for calendarbot_lite Alexa integration.

This module provides lightweight, string-based SSML generation optimized for Pi Zero 2W
performance constraints. Generates urgency-aware speech responses with proper SSML
validation and fallback handling.

Performance targets:
- Generation time: <100ms (target <50ms for urgent)
- Memory overhead: <1MB
- SSML length: <500 characters default

**Functions**:

- **render_meeting_ssml()**
  Render full SSML for next-meeting intent with urgency-based pacing.

Args:
    meeting: Meeting data dict with subject, seconds_until_start, duration_...

- **render_time_until_ssml()**
  Render concise SSML for time-until-next intent (time-first approach).

Args:
    seconds_until: Seconds until next meeting
    meeting: Optional meeti...

- **render_done_for_day_ssml()**
  Render SSML for done-for-day intent with appropriate emphasis and pacing.

Args:
    has_meetings_today: Whether there were meetings today
    speech_...

- **render_morning_summary_ssml()**
  Render SSML for morning summary with natural evening/night context.

Args:
    summary_result: MorningSummaryResult object with speech text and analys...

- **validate_ssml()**
  Fast, linear SSML validation for server-side safety.

Args:
    ssml: SSML string to validate
    max_chars: Maximum allowed character length
    allo...

#### `alexa/alexa_types.py`

TypedDict definitions for Alexa response structures.

This module provides type-safe dictionary structures for Alexa endpoint responses,
replacing generic dicts and eliminating the need for # type: ignore comments.

**Classes**:

- **AlexaMeetingInfo**
  Information about a single meeting for Alexa responses.

Attributes:
    subject: Meeting title/subject
    start_iso: ISO 8601 formatted start time
    seconds_until_start: Seconds from now until mee...

- **AlexaNextMeetingResponse**
  Response structure for /api/alexa/next-meeting endpoint.

Attributes:
    meeting: Meeting information (None if no upcoming meetings)
    speech_text: Plain text response for Alexa
    ssml: Optional ...

- **AlexaTimeUntilResponse**
  Response structure for /api/alexa/time-until-next endpoint.

Attributes:
    seconds_until_start: Seconds until next meeting (None if no meetings)
    duration_spoken: Human-readable duration
    spee...

- **_AlexaDoneForDayInfoRequired**
  Required fields for AlexaDoneForDayInfo.

- **AlexaDoneForDayInfo**
  Done-for-day calculation results.

Attributes:
    has_meetings_today: Whether user has any meetings today
    last_meeting_start_iso: ISO time of last meeting start (None if no meetings)
    last_mee...

- **AlexaDoneForDayResponse**
  Response structure for /api/alexa/done-for-day endpoint.

Attributes:
    now_iso: Current time in ISO format
    tz: Timezone used for calculations
    has_meetings_today: Whether user has meetings t...

- **AlexaLaunchSummaryResponse**
  Response structure for /api/alexa/launch-summary endpoint.

Attributes:
    speech_text: Plain text response
    has_meetings_today: Whether user has meetings today
    next_meeting: Information about...

- **AlexaMorningSummaryMetadata**
  Metadata for morning summary response.

Attributes:
    preview_for: What the summary is for (e.g., "tomorrow_morning")
    total_meetings_equivalent: Total equivalent meeting time
    early_start_fla...

- **AlexaMorningSummaryResponse**
  Response structure for /api/alexa/morning-summary endpoint.

Attributes:
    speech_text: Plain text summary
    summary: Summary metadata
    ssml: Optional SSML markup
    error: Optional error mess...

#### `alexa/alexa_utils.py`

Shared utilities for Alexa handlers.

This module provides shared computation functions that can be used across multiple
Alexa handlers, eliminating the need for handlers to instantiate other handlers
just to access their computation logic.

**Functions**:

- **format_done_for_day_result()**
  Format done-for-day computation result for Alexa response.

Args:
    computation_result: Result from compute_done_for_day_info()
    iso_serializer: ...

### Package: `api`

#### `api/middleware/__init__.py`

Middleware components for request processing.

This module provides middleware for cross-cutting concerns like request
correlation ID tracking for distributed tracing.

#### `api/middleware/correlation_id.py`

Request correlation ID middleware for distributed tracing.

This module provides middleware to extract or generate correlation IDs
for request tracking across distributed system components (Alexa -> API
Gateway -> Lambda -> CalendarBot -> Calendar Service).

Correlation IDs enable:
- End-to-end request tracing across services
- Faster debugging by correlating logs
- Performance analysis tracking request latency
- Error investigation across service boundaries

**Functions**:

- **get_request_id()**
  Get current request correlation ID from context.

Returns:
    Current request correlation ID, or "no-request-id" if not set

Example:
    >>> from ca...

#### `api/middleware/rate_limit_middleware.py`

Rate limiting middleware for aiohttp route handlers.

This module provides decorator and middleware functions to apply rate limiting
to Alexa endpoint handlers with minimal code changes.

**Functions**:

- **create_rate_limited_handler()**
  Wrap a handler function with rate limiting.

Args:
    handler: Async handler function to wrap
    rate_limiter: RateLimiter instance

Returns:
    Wr...

- **rate_limit()**
  Decorator to apply rate limiting to a handler function.

Usage:
    @rate_limit(my_rate_limiter)
    async def my_handler(request):
        return web...

- **add_rate_limit_headers()**
  Add X-RateLimit-* headers to response.

#### `api/middleware/rate_limiter.py`

Lightweight rate limiting middleware for Alexa endpoints.

This module provides simple, memory-efficient rate limiting suitable for
single-instance personal deployments on resource-constrained hardware like
Raspberry Pi Zero 2W.

Design Philosophy:
- In-memory storage (no Redis/database dependency)
- Sliding window algorithm for accurate tracking
- Minimal memory footprint (~1KB per tracked IP/token)
- Automatic cleanup of expired entries
- Thread-safe for asyncio event loop

**Classes**:

- **RateLimitConfig**
  Configuration for rate limiting.

- **RateLimitEntry**
  Tracking entry for rate limiting with sliding window.

- **RateLimiter**
  Lightweight in-memory rate limiter with sliding window algorithm.

This implementation uses a sliding window to track requests, providing
accurate rate limiting without the overhead of external storag...

**Functions**:

- **get_client_ip()**
  Extract client IP address from request.

Handles X-Forwarded-For header for proxy scenarios.

Args:
    request: aiohttp request object

Returns:
    ...

- **get_bearer_token()**
  Extract bearer token from Authorization header.

Args:
    request: aiohttp request object

Returns:
    Bearer token string or None if not present

- **get_stats()**
  Get rate limiter statistics.

Returns:
    Dictionary with rate limiter stats

#### `api/routes/__init__.py`

Route modules for calendarbot_lite server.

#### `api/routes/alexa_routes.py`

Alexa-specific API routes using consolidated handlers.

**Functions**:

- **register_alexa_routes()**
  Register Alexa-specific API routes using consolidated handlers.

Args:
    app: aiohttp web application
    bearer_token: Bearer token for Alexa endpo...

- **create_route_handler()**
  Create route handler closure with proper handler binding.

#### `api/routes/api_routes.py`

Main API routes for calendarbot_lite.

**Functions**:

- **register_api_routes()**
  Register main API routes.

Args:
    app: aiohttp web application
    config: Application configuration
    skipped_store: Optional skipped events sto...

#### `api/routes/static_routes.py`

Static file serving routes for calendarbot_lite.

**Functions**:

- **register_static_routes()**
  Register static file serving routes.

Args:
    app: aiohttp web application
    package_dir: Path to calendarbot_lite package directory

#### `api/server.py`

calendarbot_lite.server — minimal asyncio HTTP server for Pi Zero 2W.

This module provides a small server core that:
- runs an asyncio event loop and aiohttp web server (lazy-imported)
- runs a background refresher that fetches ICS sources, parses events and expands recurrences
- keeps a small in-memory window of upcoming events
- exposes a tiny JSON API: GET /api/whats-next, POST /api/skip, DELETE /api/skip

The implementation imports calendarbot parsing/fetching modules lazily so
the module can be imported even if the full application modules aren't present.
aiohttp is required to run the server (imported at startup).

**Classes**:

- **PortConflictError**
  Raised when a port conflict cannot be resolved.

**Functions**:

- **log_monitoring_event()**
  Log monitoring event with fallback to standard logging.

- **start_server()**
  Start the asyncio event loop and HTTP server.

Args:
    config: dict or dataclass-like object with keys:
        - server_bind: host to bind (str)
  ...

### Package: `calendar`

#### `calendar/lite_attendee_parser.py`

Attendee parsing utilities for ICS calendar processing - CalendarBot Lite.

This module provides parsing of ATTENDEE properties from iCalendar components.
Extracted from lite_parser.py to improve modularity and testability.

**Classes**:

- **LiteAttendeeParser**
  Parser for iCalendar ATTENDEE properties.

**Functions**:

- **parse_attendee()**
  Parse attendee from iCalendar property.

Args:
    attendee_prop: iCalendar ATTENDEE property

Returns:
    Parsed LiteAttendee or None

- **parse_attendees()**
  Parse all attendees from an iCalendar component.

Args:
    component: iCalendar component (e.g., VEVENT)

Returns:
    List of parsed LiteAttendee ob...

#### `calendar/lite_datetime_utils.py`

DateTime parsing utilities for ICS calendar processing - CalendarBot Lite.

This module provides timezone-aware datetime parsing for iCalendar properties.
Extracted from lite_parser.py to improve modularity and testability.

**Classes**:

- **TimezoneParser**
  Parse datetime strings with timezone handling.

Handles TZID formats like: TZID=Pacific Standard Time:20251031T090000
Supports Windows timezone names with automatic conversion to IANA format.

- **LiteDateTimeParser**
  Parser for iCalendar datetime properties with timezone handling.

**Functions**:

- **ensure_timezone_aware()**
  Ensure datetime is timezone-aware (lightweight version for calendarbot_lite).

Args:
    dt: Datetime to make timezone-aware

Returns:
    Timezone-aw...

- **serialize_datetime_utc()**
  Serialize datetime to ISO 8601 UTC string with Z suffix.

This function replaces manual string concatenation (dt.isoformat() + "Z")
with proper dateti...

- **serialize_datetime_optional()**
  Serialize optional datetime to ISO 8601 UTC string, returning None if input is None.

This is a convenience wrapper around serialize_datetime_utc() fo...

- **format_time_cross_platform()**
  Format time in 12-hour format without leading zeros (cross-platform).

This function provides cross-platform compatible time formatting that works
on ...

- **format_time_for_speech()**
  Format a datetime for natural speech output.

Converts the datetime to the target timezone and formats it for speech.
Can return either plain text (fo...

- **parse_datetime_with_tzid()**
  Parse datetime string with TZID prefix.

Args:
    datetime_str: String in format "TZID=<timezone>:<datetime>"
                 Example: "TZID=Pacific...

- **parse_datetime()**
  Parse datetime string in various formats.

Handles:
- TZID format: TZID=Pacific Standard Time:20251031T090000
- ISO format: 2025-06-23T08:30:00Z
- RRU...

- **parse_datetime()**
  Parse iCalendar datetime property.

Args:
    dt_prop: iCalendar datetime property
    default_timezone: Default timezone if none specified (overrides...

- **parse_datetime_optional()**
  Parse optional datetime property.

Args:
    dt_prop: iCalendar datetime property or None

Returns:
    Parsed datetime or None

#### `calendar/lite_event_merger.py`

Event merging and deduplication for ICS calendar processing - CalendarBot Lite.

This module handles merging expanded recurring events with original events,
RECURRENCE-ID override processing, and event deduplication.
Extracted from lite_parser.py to improve modularity and testability.

**Classes**:

- **LiteEventMerger**
  Handles merging, deduplication, and RECURRENCE-ID override logic for calendar events.

**Functions**:

- **merge_expanded_events()**
  Merge expanded events with original events.

This method handles the complex logic of:
1. Identifying RECURRENCE-ID overrides (moved/modified recurrin...

- **deduplicate_events()**
  Remove duplicate events based on UID and start time.

Events are considered duplicates if they have the same:
- UID (event.id)
- Subject
- Start time ...

#### `calendar/lite_event_parser.py`

Event component parsing for ICS calendar processing - CalendarBot Lite.

This module provides parsing of VEVENT components from iCalendar files.
Extracted from lite_parser.py to improve modularity and testability.

**Classes**:

- **LiteEventComponentParser**
  Parser for iCalendar VEVENT components into LiteCalendarEvent objects.

**Functions**:

- **parse_event_component()**
  Parse a single VEVENT component into LiteCalendarEvent.

Args:
    component: iCalendar VEVENT component
    default_timezone: Default timezone for th...

#### `calendar/lite_fetcher.py`

HTTP client for downloading ICS calendar files - CalendarBot Lite version.

**Classes**:

- **LiteICSFetchError**
  Base exception for ICS fetch errors.

- **LiteICSAuthError**
  Authentication error during ICS fetch.

- **LiteICSNetworkError**
  Network error during ICS fetch.

- **LiteICSTimeoutError**
  Timeout error during ICS fetch.

- **LiteSecurityEventLogger**
  Lightweight security event logger for CalendarBot Lite.

- **LiteICSFetcher**
  Async HTTP client for downloading ICS calendar files - CalendarBot Lite version.

**Functions**:

- **log_event()**
  Log security event with minimal overhead.

Args:
    event_data: Security event data to log

- **get_conditional_headers()**
  Get conditional request headers for caching.

Args:
    etag: ETag value from previous response
    last_modified: Last-Modified value from previous r...

#### `calendar/lite_logging.py`

Central logging configuration for calendarbot_lite.

Provides optimized logging configuration for Pi Zero 2W deployment by suppressing
verbose debug logs from third-party libraries while maintaining important diagnostic
information.

**Classes**:

- **CorrelationIdFilter**
  Add correlation ID to all log records for distributed tracing.

**Functions**:

- **configure_lite_logging()**
  Configure logging levels for calendarbot_lite optimized for Pi Zero 2W performance.

This function suppresses verbose DEBUG logs from noisy third-part...

- **reset_logging_to_debug()**
  Reset all loggers to DEBUG level for troubleshooting.

This is a utility function to temporarily enable verbose logging
for all modules when diagnosin...

- **get_logging_status()**
  Get current logging configuration status.

Returns:
    Dictionary mapping logger names to their current levels

- **filter()**
  Add correlation ID to log record.

Args:
    record: Log record to enhance

Returns:
    True to allow record to be logged

#### `calendar/lite_models.py`

Data models for ICS calendar processing - CalendarBot Lite version.

**Classes**:

- **LiteAuthType**
  Supported authentication types for ICS sources.

- **LiteICSAuth**
  Authentication configuration for ICS sources.

- **LiteICSSource**
  Configuration for an ICS calendar source.

- **LiteICSResponse**
  Response from ICS fetch operation.

Notes:
    - New fields `stream_handle` and `stream_mode` support streaming responses.
    - Backwards compatibility is preserved: consumers may continue to use
   ...

- **LiteICSParseResult**
  Result of ICS parsing operation.

- **LiteICSValidationResult**
  Result of ICS source validation.

- **LiteEventStatus**
  Event status/show-as values.

- **LiteAttendeeType**
  Attendee type enum.

- **LiteResponseStatus**
  Response status enum.

- **LiteDateTimeInfo**
  Date and time information for calendar events.

- **LiteLocation**
  Location information for calendar events.

- **LiteAttendee**
  Calendar event attendee.

- **LiteCalendarEvent**
  Calendar event model for ICS-based events.

**Functions**:

- **get_headers()**
  Get HTTP headers for authentication.

- **is_not_modified()**
  Check if response indicates content not modified (304).

- **content_length()**
  Get content length if available for buffered responses or from headers.

- **get_content_or_stream()**
  Utility to obtain either buffered content or a stream handle.

Returns:
    (content, stream_handle)
    - For buffered responses, `content` will be p...

- **is_valid()**
  Check if validation passed all checks.

- **add_error()**
  Add an error message.

- **add_warning()**
  Add a warning message.

- **serialize_datetime()**
  Serialize datetime to ISO format.

- **strip_and_validate_display_name()**
  Strip whitespace and validate display name is not empty.

Args:
    v: Raw display name value

Returns:
    Stripped display name

Raises:
    ValueEr...

- **strip_and_validate_subject()**
  Strip whitespace and validate subject is not empty.

Args:
    v: Raw subject value

Returns:
    Stripped subject

Raises:
    ValueError: If subject...

#### `calendar/lite_parser.py`

iCalendar parser with Microsoft Outlook compatibility - CalendarBot Lite version.

**Classes**:

- **_SimpleEvent**
  Lightweight event representation for RRULE expansion.

Used as a fallback when a full parsed event is not available.
Contains minimal attributes needed for recurring event expansion.

- **_DateTimeWrapper**
  Wrapper for datetime objects used in event expansion.

Provides a consistent interface for date_time and time_zone attributes
expected by the RRULE expander.

- **LiteICSParser**
  iCalendar parser with Microsoft Outlook compatibility - CalendarBot Lite version.

**Functions**:

- **parse_ics_content_optimized()**
  Parse ICS content using optimal method based on size.

Automatically chooses between streaming (for large files) and
traditional parsing (for small fi...

- **parse_ics_content()**
  Parse ICS content into structured calendar events.

Automatically chooses optimal parsing method based on content size.
For large files (>10MB), uses ...

- **filter_busy_events()**
  Filter to only show busy/tentative events.

Args:
    events: List of calendar events

Returns:
    Filtered list of events

- **validate_ics_content()**
  Validate that content is valid ICS format.

Args:
    ics_content: ICS content to validate

Returns:
    True if valid ICS format, False otherwise

#### `calendar/lite_parser_telemetry.py`

Parser telemetry and circuit breaker for ICS calendar processing - CalendarBot Lite.

This module handles progress tracking, duplicate detection, and circuit breaker
logic to prevent infinite loops from corrupted/malformed ICS feeds.
Extracted from lite_parser.py to improve modularity and testability.

**Classes**:

- **ParserTelemetry**
  Tracks parsing progress, detects duplicates, and triggers circuit breaker.

This class monitors ICS parsing to detect network corruption or malformed
feeds that could cause infinite loops or excessive...

**Functions**:

- **record_item()**
  Record that an item was processed.

- **record_event()**
  Record an event and check for duplicates.

Args:
    event_uid: Event UID
    recurrence_id: Optional RECURRENCE-ID for modified instances

Returns:
 ...

- **record_warning()**
  Record a warning.

- **should_break()**
  Check if circuit breaker should activate.

Circuit breaker triggers when:
- Warning count exceeds threshold AND
- Duplicate ratio exceeds threshold

T...

- **get_duplicate_ratio()**
  Calculate duplicate ratio as percentage.

Returns:
    Duplicate percentage (0-100)

- **get_duplicate_count()**
  Get number of duplicate items detected.

Returns:
    Duplicate count

- **get_unique_event_count()**
  Get number of unique events.

Returns:
    Unique event count

- **get_content_size_estimate()**
  Estimate content size in bytes.

Returns:
    Rough estimate of content size (total_items * 100 bytes)

- **log_event_limit_reached()**
  Log when event limit is reached.

Args:
    max_events: Maximum events allowed
    events_collected: Number of events collected so far

- **log_completion()**
  Log completion with comprehensive telemetry.

Args:
    final_events: Number of events in final result
    warning_count: Total warnings encountered

#### `calendar/lite_rrule_expander.py`

RRULE expansion logic for CalendarBot Lite ICS parser.

**Classes**:

- **RRuleExpanderConfig**
  Configuration for RRULE expansion.

Consolidates all RRULE-related settings with explicit defaults.

- **RRuleWorkerPool**
  Async worker pool for RRULE expansion to maintain responsive Pi Zero 2W performance.

Implements bounded concurrency and cooperative multitasking for CPU-intensive RRULE expansion.

- **LiteRRuleExpander**
  RRULE expander with both async and sync interfaces.

Provides:
- Async streaming expansion (from RRuleWorkerPool)
- Legacy sync methods for backward compatibility
- Helper methods for parsing and even...

- **LiteRRuleExpansionError**
  Base exception for RRULE expansion errors.

- **LiteRRuleParseError**
  Error parsing RRULE string.

- **RRuleOrchestrator**
  Centralized RRULE expansion orchestration.

Consolidates all RRULE-related logic including:
- Building UID mappings between components and events
- Collecting expansion candidates with RRULE patterns
...

**Functions**:

- **get_worker_pool()**
  Get or create the global RRULE worker pool.

Args:
    settings: Configuration settings

Returns:
    RRuleWorkerPool instance

- **from_settings()**
  Extract RRULE configuration from settings object.

Args:
    settings: Configuration object with RRULE settings

Returns:
    RRuleExpanderConfig with...

- **expand_event()**
  Legacy synchronous-style wrapper returning a list of expanded events.

Delegates to expand_event_to_list via asyncio.run for callers that expect a blo...

- **expand_rrule()**
  Alias for expand_event to support older callers that used expand_rrule.

- **parse_rrule_string()**
  Parse RRULE string into components.

Args:
    rrule_string: RRULE string (e.g. "FREQ=WEEKLY;INTERVAL=1;BYDAY=MO")

Returns:
    Dictionary with parse...

- **apply_exdates()**
  Remove excluded dates from occurrence list.

Args:
    occurrences: List of datetime occurrences
    exdates: List of excluded dates in ISO format

Re...

- **generate_event_instances()**
  Generate LiteCalendarEvent instances for each occurrence.

Args:
    master_event: Master recurring event template
    occurrences: List of datetime o...

- **expand_recurring_events()**
  Expand recurring events using RRULE patterns.

This is the main entry point for RRULE expansion. It:
1. Builds mappings of UIDs to components and even...

- **check_not_in_event_loop()**
  Ensure we're not already in an event loop.

#### `calendar/lite_streaming_parser.py`

Memory-efficient streaming ICS parser for large calendar files - CalendarBot Lite.

This module handles streaming parsing of ICS files to minimize memory usage,
processing events incrementally as they are read from the source.
Extracted from lite_parser.py to improve modularity and testability.

**Classes**:

- **LiteICSContentTooLargeError**
  Raised when ICS content exceeds size limits.

- **LiteStreamingICSParser**
  Memory-efficient streaming ICS parser for large files.

Processes ICS files in chunks to minimize memory usage, handling
event boundaries and line folding across chunk boundaries.

**Functions**:

- **parse_stream()**
  Parse ICS content from file stream, yielding events as they are found.

Args:
    file_source: File path, file object, or ICS content string

Yields:
...

### Package: `core`

#### `core/async_utils.py`

Centralized async orchestration utilities for CalendarBot Lite.

This module provides consistent patterns for async operations including:
- ThreadPoolExecutor management with proper lifecycle
- Event loop detection and safe execution
- Timeout management with backoff strategies
- Error handling with retry logic
- Semaphore-based concurrency control
- Async context manager utilities

Design Goals:
1. Eliminate scattered ThreadPoolExecutor usage across codebase
2. Provide safe event loop handling for mixed sync/async contexts
3. Centralize timeout and retry configuration
4. Enable consistent error handling and logging patterns
5. Simplify async code with reusable utilities

Usage Example:
    ```python
    from calendarbot_lite.core.async_utils import AsyncOrchestrator

    orchestrator = AsyncOrchestrator(max_workers=4)

    # Run async function with timeout
    result = await orchestrator.run_with_timeout(
        some_async_func(),
        timeout=30.0
    )

    # Run sync function in executor
    result = await orchestrator.run_in_executor(
        some_blocking_func,
        arg1,
        arg2
    )

    # Gather multiple coroutines with timeout
    results = await orchestrator.gather_with_timeout(
        coro1(), coro2(), coro3(),
        timeout=60.0
    )

    # Retry with exponential backoff
    result = await orchestrator.retry_async(
        flaky_async_func,
        max_retries=3,
        backoff=1.0
    )
    ```

Async Patterns Audit (conducted 2025-11-01):

## ThreadPoolExecutor Usage:
1. lite_rrule_expander.py (lines 1018-1031): Creates ThreadPoolExecutor to run
   async code in new event loop when existing loop detected
2. lite_parser.py (lines 390-403): Similar pattern for RRULE expansion

## Async/Await Patterns:
- asyncio.gather() for concurrent operations (fetch_orchestrator.py:67)
- Semaphores for bounded concurrency (RRuleWorkerPool, FetchOrchestrator)
- AsyncIterator for streaming (lite_rrule_expander.py:101)
- Async context managers for locks and semaphores

## Timeout Strategies:
- http_client.py: httpx.Timeout with separate connect/read/write/pool timeouts
  - connect=10.0s, read=30.0s, write=10.0s, pool=30.0s
- RRuleWorkerPool: time budget per RRULE (200ms default)
- No centralized timeout management - handled ad-hoc per operation

## Error Handling:
- http_client.py: Health tracking with error counts and client recreation
- Try/except with logging throughout
- No centralized retry logic - implemented per operation
- Error recording: record_client_error(), record_client_success()

## Concurrency Control:
- asyncio.Semaphore for bounded concurrency
- RRuleWorkerPool: max_concurrency=1 (Pi Zero 2W optimization)
- FetchOrchestrator: fetch_concurrency=2-3 (bounded 1-3)
- No centralized semaphore management

## Common Patterns to Consolidate:
1. Event loop detection with fallback to ThreadPoolExecutor
2. Semaphore-based concurrency limiting
3. Health tracking with error thresholds
4. Timeout management with configurable durations
5. Async streaming with cooperative yields

**Classes**:

- **AsyncOrchestratorError**
  Base exception for AsyncOrchestrator errors.

- **AsyncTimeoutError**
  Raised when async operation exceeds timeout.

- **AsyncRetryExhaustedError**
  Raised when retry attempts are exhausted.

- **AsyncOrchestrator**
  Centralized async operation orchestration with consistent patterns.

Provides unified interface for:
- ThreadPoolExecutor lifecycle management
- Safe event loop detection and execution
- Timeout manag...

**Functions**:

- **get_global_orchestrator()**
  Get or create the global AsyncOrchestrator instance.

Args:
    max_workers: Maximum thread pool workers
    default_timeout: Default timeout for oper...

- **run_coroutine_from_sync()**
  Run async coroutine from synchronous context.

This is a SYNCHRONOUS method that safely executes async code whether
or not there's already a running e...

- **get_health_stats()**
  Get health statistics for monitoring.

Returns:
    Dictionary with health metrics

- **run_in_new_loop()**
  Run coroutine in a new event loop in separate thread.

- **run_in_new_loop()**
  Run coroutine in a new event loop in separate thread.

#### `core/config_manager.py`

Configuration management for calendarbot_lite server.

**Classes**:

- **ConfigManager**
  Manages application configuration from environment variables and .env files.

**Functions**:

- **get_default_timezone()**
  Get default timezone from environment with validation.

Args:
    fallback: Fallback timezone if not configured or invalid (default: America/Los_Angel...

- **get_config_value()**
  Get configuration value supporting both dict and dataclass-like objects.

Args:
    config: Configuration object (dict or object with attributes)
    ...

- **load_env_file()**
  Load .env file and set environment variables.

Only sets variables that are not already in the environment to avoid
surprising overrides of user's env...

- **build_config_from_env()**
  Build configuration dictionary from environment variables.

Recognizes:
- CALENDARBOT_ICS_URL -> 'ics_sources' (list with single URL)
- CALENDARBOT_RE...

- **load_full_config()**
  Load .env file and build configuration from environment.

This is the main entry point for loading configuration.

Returns:
    Configuration dictiona...

#### `core/debug_helpers.py`

Lightweight debug helpers for calendar diagnostics (CalendarBot Lite).

Provides:
- .read_env to read minimal env keys from a .env file
- .fetch_ics_stream to yield bytes from an ICS HTTP(S) source
- .parse_stream_via_parser to call lite_parser.parse_ics_stream and return the parse result
- .event_summary to produce a small serializable summary of LiteCalendarEvent objects
- .collect_rrule_candidates to extract (event, rrule_string, exdates) tuples for expansion

These helpers are intentionally small and dependency-light so debug scripts can import them
without requiring changes to core library behavior.

**Functions**:

- **read_env()**
  Read a minimal .env-style file and return selected keys.

Supported keys (preferred):
  - CALENDARBOT_ICS_URL (url or file path)
  - DATETIME_OVERRIDE...

- **event_summary()**
  Return a small serializable summary of a LiteCalendarEvent.

- **collect_rrule_candidates()**
  From parsed events, build a list of (event, rrule_string, exdates) tuples.

The parsed events may be LiteCalendarEvent instances or dict-like objects ...

#### `core/dependencies.py`

Dependency injection container for calendarbot_lite server.

**Classes**:

- **AppDependencies**
  Container for all application dependencies.

This dataclass holds all the shared dependencies needed by various
parts of the application, making it easier to test and maintain.

- **DependencyContainer**
  Factory for building application dependencies.

**Functions**:

- **build_dependencies()**
  Build all application dependencies.

Args:
    config: Application configuration
    skipped_store: Optional skipped events store
    shared_http_clie...

#### `core/health_tracker.py`

Health tracking and monitoring for calendarbot_lite server.

**Classes**:

- **HealthStatus**
  Health status information for the server.

- **SystemDiagnostics**
  System diagnostics information.

- **HealthTracker**
  Thread-safe health tracking for server monitoring.

**Functions**:

- **get_system_diagnostics()**
  Get system diagnostics information.

Returns:
    SystemDiagnostics with platform and runtime information

- **record_refresh_attempt()**
  Record that a refresh attempt was made.

- **record_refresh_success()**
  Record a successful refresh with event count.

Args:
    event_count: Number of events in the window after refresh

- **record_background_heartbeat()**
  Record that background task is alive.

- **record_render_probe()**
  Record render probe result.

Args:
    ok: Whether render probe succeeded
    notes: Optional notes about the probe

- **update()**
  Update multiple health tracking values atomically.

This is the main update method that can set multiple values at once.

Args:
    refresh_attempt: M...

- **get_uptime_seconds()**
  Get server uptime in seconds.

Returns:
    Uptime in seconds since tracker initialization

- **get_last_refresh_age_seconds()**
  Get age of last successful refresh in seconds.

Returns:
    Seconds since last successful refresh, or None if never refreshed

- **get_background_task_status()**
  Get background task status.

Returns:
    Dictionary with task status information

- **determine_overall_status()**
  Determine overall health status.

Returns:
    "ok", "degraded", or "critical"

#### `core/http_client.py`

Shared HTTP client manager optimized for Pi Zero 2W performance.

This module provides a connection pool manager that eliminates per-fetch
httpx.AsyncClient creation and reduces network overhead through connection reuse.
Configured with Pi Zero 2W-specific limits to balance performance and resource usage.

**Classes**:

- **StreamingHTTPResponse**
  Wrapper for streaming HTTP response with peek capability.

This class provides a way to peek at the initial bytes of an HTTP response
to make buffering vs streaming decisions, while preserving the abi...

**Functions**:

- **headers()**
  Get response headers.

- **status_code()**
  Get response status code.

- **raise_for_status()**
  Raise an exception if response indicates an error.

#### `core/monitoring_logging.py`

Enhanced monitoring logging module for CalendarBot_Lite.

Provides centralized structured JSON logging with consistent field schema,
rate limiting, context managers, and multi-destination output support.
Optimized for Pi Zero 2W with minimal resource usage.

**Classes**:

- **LogEntry**
  Structured log entry with consistent schema.

- **RateLimiter**
  Rate limiting for repeated error messages.

- **SystemMetricsCollector**
  Lightweight system metrics collection for Pi Zero 2W.

- **MonitoringLogger**
  Enhanced monitoring logger with structured JSON output.

IMPORTANT - Exception Handling:
    This logger does NOT have an exception() method. When logging errors
    within exception handlers, use the...

**Functions**:

- **configure_monitoring_logging()**
  Configure monitoring logging for a component.

Args:
    component: Component name (server|watchdog|health|recovery)
    level: Log level override fro...

- **get_logger()**
  Get or create a monitoring logger for a component.

Args:
    component: Component name

Returns:
    MonitoringLogger instance

- **log_server_event()**
  Log a server component event.

- **log_watchdog_event()**
  Log a watchdog component event.

- **log_health_event()**
  Log a health check component event.

- **log_recovery_event()**
  Log a recovery component event.

- **to_dict()**
  Convert to dictionary following the standard schema.

- **to_json()**
  Convert to JSON string.

- **should_log()**
  Check if event should be logged based on rate limits.

Args:
    event_key: Unique key for the event type
    max_per_minute: Maximum events per minut...

- **get_rate_limited_count()**
  Get count of rate limited events for the key.

#### `core/timezone_utils.py`

Timezone detection and conversion utilities for calendarbot_lite.

**Classes**:

- **TimezoneDetector**
  Detects server timezone using multiple fallback strategies.

- **TimeProvider**
  Provides current time with test time override support.

**Functions**:

- **get_server_timezone()**
  Get the server's local timezone (convenience function).

Returns:
    IANA timezone string

- **get_fallback_timezone()**
  Get the fallback timezone (convenience function).

Returns:
    Default fallback timezone string

- **now_utc()**
  Get current UTC time (convenience function).

Returns:
    Current time in UTC

- **windows_tz_to_iana()**
  Convert Windows timezone name to IANA timezone identifier.

Args:
    windows_tz: Windows timezone name (e.g., "Mountain Standard Time")

Returns:
   ...

- **resolve_timezone_alias()**
  Resolve timezone alias to canonical IANA timezone identifier.

Handles obsolete timezone names (e.g., US/Pacific -> America/Los_Angeles)
and common al...

- **normalize_timezone_name()**
  Normalize timezone string to canonical IANA timezone identifier.

This function provides comprehensive timezone name resolution:
1. Checks if it's a W...

- **convert_to_server_tz()**
  Convert a datetime to the server's local timezone.

This is a convenience function for the common pattern of converting
UTC or other timezone datetime...

- **convert_to_timezone()**
  Convert a datetime to a specific timezone.

Args:
    dt: Datetime to convert (should be timezone-aware)
    tz_str: IANA timezone identifier (e.g., "...

- **parse_request_timezone()**
  Parse timezone string from request, with fallback to UTC.

This utility consolidates the common pattern in Alexa handlers where a timezone
string is p...

- **get_server_timezone()**
  Get the server's local timezone as an IANA timezone identifier.

This function provides centralized timezone detection for calendarbot_lite.
It NEVER ...

### Package: `domain`

#### `domain/event_filter.py`

Event filtering and window management for calendarbot_lite server.

**Classes**:

- **SmartFallbackHandler**
  Handles smart fallback logic when source fetching fails or returns suspicious results.

- **EventFilter**
  Filters events based on time, timezone, and skip status.

- **EventWindowManager**
  Manages the in-memory event window with atomic updates.

**Functions**:

- **should_preserve_existing_window()**
  Determine if existing window should be preserved based on fetch results.

Args:
    parsed_events: Events parsed from sources
    existing_count: Numb...

- **filter_upcoming_events()**
  Filter events to include only those in the future.

Handles both timezone-aware and timezone-naive datetime objects safely.

Args:
    events: List of...

- **filter_skipped_events()**
  Filter out events that have been skipped by the user.

Args:
    events: List of event dictionaries
    skipped_store: Optional skipped store object w...

- **sort_and_limit_events()**
  Sort events by start time and limit to window size.

When multiple events have the same start time, they are sorted
alphabetically by event ID to ensu...

#### `domain/event_prioritizer.py`

Event prioritization logic for whats-next endpoint.

**Classes**:

- **EventCategory**
  Categories for event prioritization.

- **EventPrioritizer**
  Prioritizes events for the whats-next endpoint with business logic.

**Functions**:

- **find_next_event()**
  Find the next event to show, applying prioritization logic.

Business rules:
1. Skip events in the past
2. Skip focus time events
3. Skip user-skipped...

#### `domain/fetch_orchestrator.py`

Fetch orchestration and refresh loop management for calendarbot_lite.

**Classes**:

- **FetchOrchestrator**
  Orchestrates fetching from multiple sources with bounded concurrency.

#### `domain/morning_summary.py`

Morning summary logic service for CalendarBot's Alexa integration.

This module implements the core morning summary functionality for CalendarBot Lite,
providing analysis of tomorrow morning's calendar events (6 AM to 12 PM) with
natural language speech generation for Alexa delivery.

All user stories from the Morning Summary Feature specification are implemented:
- Basic Morning Summary Generation (Story 1)
- Early Start Detection and Wake-up Recommendations (Story 2)
- Free Time Block Analysis (Story 3)
- Morning Schedule Density Classification (Story 4)
- Natural Language Response Generation (Story 5)
- All-Day Event Handling (Story 6)
- No Meetings Scenario (Story 7)
- Performance and Reliability (Story 8)

**Classes**:

- **DensityLevel**
  Morning schedule density classification (Story 4).

- **MorningSummaryRequest**
  Request for morning summary generation.

- **FreeBlock**
  Free time block information (Story 3).

- **MeetingInsight**
  Meeting insight information.

- **MorningSummaryResult**
  Result of morning summary analysis.

- **MorningSummaryService**
  Core morning summary generation service.

Implements all user stories for morning summary functionality with
performance optimization and caching (Story 8).

**Functions**:

- **get_morning_summary_service()**
  Get the global morning summary service instance.

- **clamp_max_events()**
  Clamp max_events to performance limit (Story 8).

- **is_significant()**
  Check if this is a significant free block (45+ minutes).

- **get_spoken_duration()**
  Get conversational duration text (Story 5).

- **get_spoken_start_time()**
  Get conversational start time (Story 5).

Args:
    timezone_str: IANA timezone identifier for conversion (defaults to server timezone)

- **get_short_subject()**
  Get shortened subject for speech (Story 5).

- **get_spoken_start_time()**
  Get conversational start time (Story 5).

Args:
    timezone_str: IANA timezone identifier for conversion (defaults to server timezone)

- **wake_up_recommendation_time()**
  Get recommended wake-up time (Story 2).

- **longest_free_block()**
  Get longest continuous free time block (Story 3).

#### `domain/pipeline.py`

Event processing pipeline architecture for calendarbot_lite.

This module provides a flexible, extensible pipeline for processing calendar events
through multiple stages. The pipeline pattern enables:
- Clear separation of concerns
- Easy testing of individual stages
- Extensibility for new processing stages
- Explicit error handling and logging

Usage:
    pipeline = EventProcessingPipeline()
    pipeline.add_stage(FetchStage(...))
    pipeline.add_stage(ParseStage(...))
    pipeline.add_stage(ExpansionStage(...))

    context = ProcessingContext(...)
    result = await pipeline.process(context)

**Classes**:

- **ProcessingContext**
  Context passed between pipeline stages.

Contains all data and configuration needed for event processing.
Stages can read from and write to this context.

- **ProcessingResult**
  Result from a pipeline stage or complete pipeline execution.

Contains processed events plus error/warning information for observability.

- **EventProcessor**
  Protocol for a single stage in the event processing pipeline.

Each stage:
- Receives a ProcessingContext
- Performs its processing task
- Returns a ProcessingResult with events and any errors/warning...

- **EventProcessingPipeline**
  Orchestrates event processing through multiple stages.

The pipeline executes stages in sequence, passing the processing context
between stages. Each stage can:
- Transform events
- Filter events
- Ad...

**Functions**:

- **add_warning()**
  Add a warning message.

- **add_error()**
  Add an error message and mark as failed.

- **name()**
  Name of this processing stage for logging.

- **add_stage()**
  Add a processing stage to the pipeline (builder pattern).

Args:
    stage: Event processor to add

Returns:
    Self for method chaining

- **clear_stages()**
  Remove all stages from the pipeline.

#### `domain/pipeline_stages.py`

Concrete implementations of pipeline stages for event processing.

This module provides stage implementations that wrap existing calendarbot_lite
functionality into the EventProcessor protocol. These stages can be composed
into an EventProcessingPipeline for flexible event processing.

**Classes**:

- **DeduplicationStage**
  Remove duplicate events based on UID.

Uses hash-based dictionary lookups for O(n) complexity.
Wraps the existing deduplication logic from lite_parser.

Performance:
    - O(n) time complexity using d...

- **SkippedEventsFilterStage**
  Filter out events that the user has marked as skipped.

Wraps the existing event filtering logic.

- **TimeWindowStage**
  Filter events to a specific time window.

Keeps only events within the specified time range.

- **EventLimitStage**
  Limit the number of events to a maximum count.

Keeps the earliest N events (useful for UI display limits).

- **ParseStage**
  Parse ICS content into LiteCalendarEvent objects.

Wraps LiteICSParser to parse raw ICS content and populate context.events.

- **ExpansionStage**
  Expand recurring events using RRULE patterns.

Wraps the _expand_recurring_events logic from LiteICSParser.

- **SortStage**
  Sort events by start time.

Wraps the sorting logic from _finalize_parsing.

**Functions**:

- **create_basic_pipeline()**
  Create a basic post-processing pipeline for already-parsed events.

This pipeline handles deduplication, filtering, windowing, and limiting
for events...

- **create_complete_pipeline()**
  Create a complete event processing pipeline.

This pipeline handles the full event processing flow:
1. Parse ICS content → LiteCalendarEvent objects
2...

- **name()**
  Stage name for logging.

- **name()**
  Stage name for logging.

- **name()**
  Stage name for logging.

- **name()**
  Stage name for logging.

- **name()**
  Stage name for logging.

- **name()**
  Stage name for logging.

- **name()**
  Stage name for logging.

#### `domain/skipped_store.py`

JSON-backed skipped-store for calendarbot_lite with 24-hour expiry and atomic writes.

**Classes**:

- **SkippedStore**
  Persistent skipped-store for meeting IDs with 24-hour expiry.

The on-disk format is a JSON object mapping meeting_id -> expiry_iso.
All times are stored as ISO-8601 strings with timezone information.

**Functions**:

- **load()**
  Load JSON from disk (if exists), purge expired entries, and populate memory.

This method is idempotent and safe to call multiple times.

- **add_skip()**
  Add meeting_id with expiry 24 hours from now and persist.

Args:
    meeting_id: Non-empty meeting identifier string.

Returns:
    ISO-8601 UTC expir...

- **is_skipped()**
  Return True if meeting_id is currently skipped (not expired).

Args:
    meeting_id: Meeting identifier to check.

Returns:
    True if skip exists an...

- **clear_all()**
  Remove all skip entries, persist, and return count cleared.

Returns:
    Number of entries removed.

- **active_list()**
  Return mapping meeting_id -> expiry_iso for active (non-expired) entries.

Expired entries are not included.

### Package: `root`

#### `__init__.py`

calendarbot_lite - lightweight isolated app skeleton for CalendarBot.

This package provides a minimal entrypoint and stubs. It intentionally keeps imports
light so the package can be inspected without pulling in heavy runtime dependencies.

**Functions**:

- **run_server()**
  Start the calendarbot_lite server.

This function attempts to import the runtime server implementation using
importlib so we can capture and report im...

#### `__main__.py`

Command-line entry for calendarbot_lite.

This module provides a tiny, import-light CLI that invokes the package's
run_server() entrypoint. Since the server is not implemented in this step,
calling the module will print a friendly message explaining next steps.

**Functions**:

- **main()**
  Run the calendarbot_lite CLI.

This calls run_server() and catches NotImplementedError so that developers
running the package during early development...

### Package: `scripts`

#### `scripts/performance_benchmark_lite.py`

performance_benchmark_lite.py

Comprehensive performance benchmark and validation harness for calendarbot_lite
targeting Pi Zero 2W-like constraints.

What this script provides:
- Scenario drivers for small/medium/large ICS feeds and multi-source concurrent fetches.
- Local aiohttp test server that serves generated ICS payloads (so tests are self-contained).
- Measurements:
    - Peak RSS (psutil or resource)
    - Wall-clock timings for fetch / parse / expand phases
    - Simple network bytes transferred (content-length or measured)
    - Basic responsiveness: simple HTTP API probe while background work runs
- Optional memory-pressure simulation to validate behavior under constrained RAM.
- Outputs JSON summary to "./calendarbot_lite_perf_results.json"
- Usage examples and pointers to run py-spy / tracemalloc externally for deeper profiling.

Note: Activate the project venv before running to ensure dependencies (aiohttp, psutil, httpx, dateutil, icalendar) are available.

**Functions**:

- **get_rss_kb()**
  Return current process RSS in KB (best-effort).

- **find_free_port()**
  Find a free TCP port on localhost.

- **generate_expected_event_data()**
  Generate expected event data based on scenario parameters.

Args:
    scenario: Scenario name (small, medium, large, concurrent)
    include_rrule: Wh...

- **make_ics_with_sizes()**
  Generate a simple ICS calendar string approximately total_bytes long.

This creates repeated VEVENT blocks until the approximate size is reached.
If i...
