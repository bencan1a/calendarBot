# HTTP Server & Routing Component

**Component:** 1 of 5 - Server Layer
**Purpose:** Application entry point, web server lifecycle, HTTP endpoint routing, background tasks
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

The HTTP Server & Routing component serves as the application's entry point and manages the complete web server lifecycle. It coordinates background calendar refresh tasks, maintains an in-memory event window, and routes HTTP requests to appropriate handlers.

### Position in Architecture

This component sits at the top of the application stack, orchestrating all other components:

```
┌──────────────────────────────────────────────────┐
│     HTTP Server & Routing (this component)       │
│  Entry Point → Server Lifecycle → Routes         │
└───────────────┬──────────────────────────────────┘
                │
                ├──────────────────┬──────────────────┐
                ▼                  ▼                  ▼
         Alexa Integration   Calendar Processing   Infrastructure
```

**References:**
- Architecture context: [`tmp/component_analysis.md`](../../tmp/component_analysis.md#L28-L115)
- Full architecture: [`AGENTS.md`](../../AGENTS.md#L93-L139)

### Key Design Patterns

1. **Async-First Architecture** - All I/O operations use asyncio and aiohttp
2. **Dependency Injection** - Routes receive all dependencies via function parameters
3. **Atomic State Updates** - Event window stored as single-element list for atomic replacement
4. **Background Task Management** - Refresh loop runs concurrently with web server
5. **Signal-Based Shutdown** - Graceful shutdown via SIGINT/SIGTERM handlers

---

## Core Modules

### Entry Points

#### [`__main__.py`](../../calendarbot_lite/__main__.py)

CLI entry point for the application.

**Key Functions:**
- [`main()`](../../calendarbot_lite/__main__.py:45-69) - Parse command-line arguments and delegate to [`run_server()`](../../calendarbot_lite/__init__.py:77-186)
- [`_create_parser()`](../../calendarbot_lite/__main__.py:18-42) - Configure argument parser

**Responsibilities:**
- Command-line argument parsing (`--port` flag)
- User-friendly error handling for development
- Exit code management

**Usage:**
```bash
python -m calendarbot_lite              # Default port 8080
python -m calendarbot_lite --port 3000  # Custom port
```

#### [`__init__.py`](../../calendarbot_lite/__init__.py)

Package initialization and logging setup.

**Key Functions:**
- [`run_server(args)`](../../calendarbot_lite/__init__.py:77-186) - Main entry point, imports and delegates to [`server.start_server()`](../../calendarbot_lite/server.py:1422-1480)
- [`_init_logging(level_name)`](../../calendarbot_lite/__init__.py:12-74) - Configure root logging with colorlog support

**Responsibilities:**
- Early logging initialization (before heavy imports)
- Environment variable inspection (`CALENDARBOT_DEBUG`, `CALENDARBOT_LOG_LEVEL`)
- Import error reporting
- Configuration loading and command-line override application

**Key Features:**
- Honors `CALENDARBOT_DEBUG` env var to force DEBUG logging
- Lazy imports to keep package load time fast
- Colorized console output when colorlog available

#### [`server.py`](../../calendarbot_lite/server.py) (1480 lines)

Core server implementation - the heart of the application.

**Key Functions:**
- [`start_server(config, skipped_store)`](../../calendarbot_lite/server.py:1422-1480) - Public entry point, configures logging and runs asyncio event loop
- [`_serve(config, skipped_store)`](../../calendarbot_lite/server.py:1256-1420) - Async server lifecycle manager
- [`_make_app(...)`](../../calendarbot_lite/server.py:1169-1253) - Create aiohttp application and register routes
- [`_refresh_loop(...)`](../../calendarbot_lite/server.py:1090-1127) - Background task for periodic calendar refresh
- [`_refresh_once(...)`](../../calendarbot_lite/server.py:795-1088) - Single refresh cycle with pipeline processing

**Responsibilities:**
- aiohttp web server initialization and lifecycle
- Background refresh task coordination
- Signal handling (SIGINT, SIGTERM)
- Shared HTTP client initialization
- Response cache initialization
- Port conflict detection and resolution
- Health tracking integration
- Graceful shutdown sequence

**Data Flow:**
```
start_server()
  └─> asyncio.run(_serve())
        ├─> _make_app() - Create web app with routes
        ├─> _refresh_loop() - Start background task
        │     └─> _refresh_once() - Fetch → Parse → Filter → Update window
        └─> wait for stop_event (signal)
              └─> Cleanup: cancel tasks, close clients
```

---

### Route Registration

#### [`routes/__init__.py`](../../calendarbot_lite/routes/__init__.py)

Route module exports.

**Exported Functions:**
- `register_alexa_routes()` - Alexa skill endpoints
- `register_api_routes()` - REST API endpoints
- `register_static_routes()` - Static file serving

#### [`routes/api_routes.py`](../../calendarbot_lite/routes/api_routes.py) (369 lines)

REST API endpoints for calendar data and health monitoring.

**Key Function:**
- [`register_api_routes(app, config, ...)`](../../calendarbot_lite/routes/api_routes.py:12-369) - Register all API routes with dependency injection

**Registered Endpoints:**

| Route | Method | Handler | Purpose |
|-------|--------|---------|---------|
| `/api/health` | GET | [`health_check()`](../../calendarbot_lite/routes/api_routes.py:48-90) | System health status with diagnostics |
| `/api/whats-next` | GET | [`whats_next()`](../../calendarbot_lite/routes/api_routes.py:92-117) | Next upcoming event with prioritization |
| `/api/skip` | POST | [`post_skip()`](../../calendarbot_lite/routes/api_routes.py:119-151) | Skip a meeting by ID |
| `/api/skip` | DELETE | [`delete_skip()`](../../calendarbot_lite/routes/api_routes.py:153-171) | Clear all skipped meetings |
| `/api/clear_skips` | GET | [`clear_skips()`](../../calendarbot_lite/routes/api_routes.py:173-209) | Clear skips and force refresh |
| `/api/browser-heartbeat` | POST | [`browser_heartbeat()`](../../calendarbot_lite/routes/api_routes.py:211-223) | Browser liveness probe |
| `/api/done-for-day` | GET | [`done_for_day()`](../../calendarbot_lite/routes/api_routes.py:225-250) | Last meeting end time |
| `/api/morning-summary` | POST | [`morning_summary()`](../../calendarbot_lite/routes/api_routes.py:252-357) | Morning briefing data |

**Responsibilities:**
- Health monitoring and diagnostics
- Event window access with thread-safe locking
- Event prioritization using [`EventPrioritizer`](../../calendarbot_lite/event_prioritizer.py)
- Skip management via skipped_store
- Browser heartbeat tracking for watchdog monitoring
- Morning summary generation

**Example Response (`/api/health`):**
```json
{
  "status": "ok",
  "server_time_iso": "2025-11-03T11:30:00Z",
  "server_status": {"uptime_s": 3600, "pid": 12345},
  "data_status": {
    "event_count": 25,
    "last_refresh_success_age_s": 120
  },
  "background_tasks": {"refresh_loop": "running"},
  "display_probe": {
    "last_render_probe_iso": "2025-11-03T11:29:00Z",
    "last_probe_ok": true,
    "last_probe_notes": "browser-heartbeat"
  },
  "system_diagnostics": {
    "platform": "Linux",
    "python_version": "3.12.3",
    "event_loop_running": true
  }
}
```

#### [`routes/alexa_routes.py`](../../calendarbot_lite/routes/alexa_routes.py) (163 lines)

Alexa skill webhook endpoints.

**Key Function:**
- [`register_alexa_routes(app, bearer_token, ...)`](../../calendarbot_lite/routes/alexa_routes.py:14-163) - Register Alexa handler routes with presenters

**Registered Endpoints:**

| Route | Handler Class | Intent |
|-------|--------------|--------|
| `/api/alexa/next-meeting` | `NextMeetingHandler` | "What's my next meeting?" |
| `/api/alexa/time-until-next` | `TimeUntilHandler` | "How long until my next meeting?" |
| `/api/alexa/done-for-day` | `DoneForDayHandler` | "Am I done for the day?" |
| `/api/alexa/launch-summary` | `LaunchSummaryHandler` | Launch intent summary |
| `/api/alexa/morning-summary` | `MorningSummaryHandler` | Morning briefing |

**Responsibilities:**
- Handler instantiation with dependency injection
- SSML presenter configuration per handler
- Bearer token authentication setup
- Response cache integration
- Precomputed response access
- Route handler closure creation with proper binding

**Pattern:**
```python
# Handler instantiation with presenter
presenter = SSMLPresenter({"meeting": ssml_renderers.get("meeting")})
handler = NextMeetingHandler(
    bearer_token=bearer_token,
    presenter=presenter,
    # ... other dependencies
)

# Route registration with closure
def create_route_handler(handler_instance):
    async def route_handler(request):
        return await handler_instance.handle(request, event_window_ref, window_lock)
    return route_handler

app.router.add_get("/api/alexa/next-meeting", create_route_handler(handler))
```

#### [`routes/static_routes.py`](../../calendarbot_lite/routes/static_routes.py) (53 lines)

Static file serving for What's Next kiosk interface.

**Key Function:**
- [`register_static_routes(app, package_dir)`](../../calendarbot_lite/routes/static_routes.py:12-53) - Register static file routes

**Registered Endpoints:**

| Route | Handler | File |
|-------|---------|------|
| `/` | [`serve_static_html()`](../../calendarbot_lite/routes/static_routes.py:21-28) | `whatsnext.html` |
| `/whatsnext.css` | [`serve_static_css()`](../../calendarbot_lite/routes/static_routes.py:30-37) | `whatsnext.css` |
| `/whatsnext.js` | [`serve_static_js()`](../../calendarbot_lite/routes/static_routes.py:39-46) | `whatsnext.js` |

**Responsibilities:**
- Serve What's Next kiosk display interface (HTML, CSS, JS)
- File existence validation
- 404 error handling
- Content-type headers via aiohttp's FileResponse

**Kiosk Interface:**

The What's Next interface provides a dedicated kiosk display for viewing upcoming calendar events. This is the primary user interface for calendar display on kiosk devices.

**Files:**
- [`whatsnext.html`](../../calendarbot_lite/whatsnext.html) - Kiosk display HTML structure
- [`whatsnext.css`](../../calendarbot_lite/whatsnext.css) - Kiosk display styling
- [`whatsnext.js`](../../calendarbot_lite/whatsnext.js) - Client-side logic and API integration

**API Integration:**
- Fetches data from `/api/whats-next` endpoint
- Auto-refreshes to display current calendar state
- Displays event title, time, and meeting details

---

## Key Interfaces & Data Structures

### Server Configuration

Configuration passed to [`start_server()`](../../calendarbot_lite/server.py:1422-1480):

```python
config: dict[str, Any] = {
    # ICS Sources
    "ics_sources": list[str],          # ICS feed URLs

    # Server Configuration
    "server_bind": str,                 # Host to bind (default: "0.0.0.0")
    "server_port": int,                 # Port (default: 8080)
    "refresh_interval_seconds": int,    # Background refresh interval (default: 300)

    # Event Processing
    "rrule_expansion_days": int,        # RRULE expansion window (default: 365)
    "event_window_size": int,           # Max events to keep in memory

    # Authentication
    "alexa_bearer_token": str | None,   # Alexa API authentication

    # Logging
    "debug_logging": bool,              # Enable debug mode (default: False)

    # Bounded Concurrency (Pi Zero 2W optimized)
    "fetch_concurrency": int,           # Concurrent fetches (default: 2, range: 1-3)
    "rrule_worker_concurrency": int,    # RRULE worker pool size (default: 1)

    # RRULE Worker Limits
    "max_occurrences_per_rule": int,    # Max events per RRULE (default: 250)
    "expansion_days_window": int,       # Expansion window in days (default: 365)
    "expansion_time_budget_ms_per_rule": int,  # Time budget per RRULE (default: 200)
    "expansion_yield_frequency": int,   # Yield frequency (default: 50)

    # HTTP Fetcher Configuration
    "request_timeout": int,             # HTTP timeout in seconds (default: 30)
    "max_retries": int,                 # Maximum HTTP retries (default: 3)
    "retry_backoff_factor": float,      # Retry backoff multiplier (default: 1.5)
}
```

### Event Window State

Thread-safe event storage pattern used in [`_serve()`](../../calendarbot_lite/server.py:1256-1420):

```python
# Single-element list for atomic replacement semantics
event_window_ref: list[tuple[LiteCalendarEvent, ...]] = [()]
window_lock: asyncio.Lock = asyncio.Lock()

# Read access (all routes)
async with window_lock:
    window = tuple(event_window_ref[0])

# Write access (refresh loop only)
async with window_lock:
    event_window_ref[0] = new_window_tuple
```

**Why this pattern?**
- Single-element list allows atomic replacement of entire window
- asyncio.Lock ensures thread-safe access
- Tuple immutability prevents accidental mutation
- Simple, race-free concurrent access

### Background Task Management

Background refresh loop started in [`_serve()`](../../calendarbot_lite/server.py:1370-1377):

```python
# Create background task
refresher = asyncio.create_task(
    _refresh_loop(
        config, skipped_store, event_window_ref,
        window_lock, stop_event, shared_http_client, response_cache
    )
)

# Graceful cancellation on shutdown
refresher.cancel()
try:
    await refresher
except asyncio.CancelledError:
    pass
```

### Route Registration Pattern

All route modules follow this pattern:

```python
def register_*_routes(
    app: Any,                           # aiohttp web.Application
    # ... component-specific dependencies
) -> None:
    """Register routes with dependency injection."""

    # Define route handlers with closure over dependencies
    async def route_handler(request: Any) -> Any:
        # Access injected dependencies
        # Process request
        # Return response

    # Register routes
    app.router.add_get("/path", route_handler)
    app.router.add_post("/path", route_handler)
```

---

## Integration Points

### Outbound Dependencies

The HTTP Server & Routing component depends on:

1. **Calendar Processing**
   - [`FetchOrchestrator`](../../calendarbot_lite/fetch_orchestrator.py) - Multi-source calendar fetching
   - [`EventProcessingPipeline`](../../calendarbot_lite/pipeline.py) - Event processing pipeline
   - [`EventPrioritizer`](../../calendarbot_lite/event_prioritizer.py) - Event ranking logic

2. **Alexa Integration**
   - [`AlexaHandlerRegistry`](../../calendarbot_lite/alexa_registry.py) - Handler routing
   - Alexa handler classes (NextMeetingHandler, etc.)
   - [`SSMLPresenter`](../../calendarbot_lite/alexa_presentation.py) - Response formatting
   - [`ResponseCache`](../../calendarbot_lite/alexa_response_cache.py) - Response caching

3. **Infrastructure**
   - [`HealthTracker`](../../calendarbot_lite/health_tracker.py) - System health monitoring
   - [`get_shared_client()`](../../calendarbot_lite/http_client.py) - HTTP client pooling
   - [`ConfigManager`](../../calendarbot_lite/config_manager.py) - Configuration management

### Inbound Interfaces

The component receives:

1. **HTTP Requests** - Via aiohttp web server
2. **Environment Variables** - Via [`config_manager`](../../calendarbot_lite/config_manager.py) module
3. **System Signals** - SIGINT, SIGTERM for graceful shutdown
4. **Command-Line Arguments** - Parsed in [`__main__.py`](../../calendarbot_lite/__main__.py)

### Dependency Injection Pattern

Routes receive all dependencies as function parameters:

```python
# In server.py _make_app()
register_api_routes(
    app=app,
    config=_config,
    skipped_store=skipped_store,
    event_window_ref=event_window_ref,
    window_lock=window_lock,
    shared_http_client=shared_http_client,
    health_tracker=_health_tracker,
    time_provider=_now_utc,
    event_to_api_model=_event_to_api_model,
    # ... more helper functions
)
```

This pattern enables:
- Easy testing with mock dependencies
- Clear dependency visibility
- No global state access in routes
- Flexible composition

---

## Common Usage Patterns

### Starting the Server

**From command line:**
```bash
# Activate virtual environment first
. venv/bin/activate

# Run with defaults (port 8080)
python -m calendarbot_lite

# Run with custom port
python -m calendarbot_lite --port 3000
```

**Programmatically:**
```python
from calendarbot_lite import run_server
import argparse

# Create arguments namespace
args = argparse.Namespace(port=3000)

# Start server (blocks until shutdown)
run_server(args)
```

### Adding New API Endpoints

1. **Add handler function in appropriate route module:**

```python
# In routes/api_routes.py
async def my_new_endpoint(request: Any) -> Any:
    """Handle my new endpoint."""
    # Access injected dependencies
    now = time_provider()

    # Read event window safely
    async with window_lock:
        window = tuple(event_window_ref[0])

    # Process and return response
    return web.json_response({"result": "data"}, status=200)
```

2. **Register route in registration function:**

```python
# In register_api_routes()
app.router.add_get("/api/my-endpoint", my_new_endpoint)
```

3. **Access injected dependencies as needed** - All dependencies are in closure scope

### Background Task Pattern

**Creating a background task:**

```python
# In _serve()
background_task = asyncio.create_task(
    my_background_function(config, shared_resources)
)

# On shutdown
background_task.cancel()
try:
    await background_task
except asyncio.CancelledError:
    pass
```

**Background task implementation:**

```python
async def my_background_function(config, resources):
    """Run background task until cancelled."""
    interval = config.get("interval_seconds", 60)

    while True:
        try:
            # Do work
            await do_work(resources)

            # Sleep with cancellation awareness
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Background task cancelled")
            raise
        except Exception:
            logger.exception("Background task error")
            await asyncio.sleep(interval)
```

### Health Monitoring Integration

**Record health events:**

```python
from .health_tracker import HealthTracker

health_tracker = HealthTracker()

# Record successful refresh
health_tracker.record_refresh_success(event_count=50)

# Record browser heartbeat
health_tracker.record_render_probe(ok=True, notes="browser-heartbeat")

# Get health status
status = health_tracker.get_health_status(now_iso="2025-11-03T11:30:00Z")
```

**Access health data in routes:**

```python
async def health_check(request):
    now = time_provider()
    status = health_tracker.get_health_status(now.isoformat() + "Z")
    return web.json_response({
        "status": status.status,
        "uptime": status.uptime_seconds,
        # ... more fields
    })
```

---

## Code Examples

### Complete Route Handler with Dependencies

```python
async def my_endpoint(_request: Any) -> Any:
    """Example endpoint showing all common patterns."""
    from aiohttp import web

    # Get current time from injected provider
    now = time_provider()

    # Read event window with thread-safe lock
    async with window_lock:
        window = tuple(event_window_ref[0])

    # Filter events (example: only future events)
    future_events = [
        event for event in window
        if event.start_dt_utc and event.start_dt_utc > now
    ]

    # Check skip status if needed
    if skipped_store:
        # Filter out skipped events
        unfiltered_events = []
        for event in future_events:
            is_skipped = getattr(skipped_store, "is_skipped", lambda x: False)
            if not is_skipped(event.meeting_id):
                unfiltered_events.append(event)
        future_events = unfiltered_events

    # Convert to API model
    event_models = [event_to_api_model(event) for event in future_events[:10]]

    # Return JSON response
    return web.json_response({
        "count": len(event_models),
        "events": event_models,
        "timestamp": serialize_iso(now)
    }, status=200)
```

### Adding Alexa Handler Route

```python
# In routes/alexa_routes.py

# 1. Create presenter with SSML renderer
my_presenter = SSMLPresenter({
    "my_renderer": ssml_renderers.get("my_renderer")
})

# 2. Instantiate handler with dependencies
my_handler = MyAlexaHandler(
    bearer_token=bearer_token,
    time_provider=time_provider,
    skipped_store=skipped_store,
    response_cache=response_cache,
    presenter=my_presenter,
)

# 3. Create route handler closure
def create_route_handler(handler_instance: Any) -> Any:
    async def route_handler(request: Any) -> Any:
        return await handler_instance.handle(request, event_window_ref, window_lock)
    return route_handler

# 4. Register route
app.router.add_get("/api/alexa/my-intent", create_route_handler(my_handler))
```

### Custom Background Task

```python
async def custom_background_task(config, stop_event):
    """Example background task with proper lifecycle."""
    interval = config.get("custom_interval", 300)
    logger.info("Custom background task started")

    try:
        while not stop_event.is_set():
            try:
                # Do periodic work
                await do_custom_work()

                # Wait with cancellation check
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=interval
                )
            except asyncio.TimeoutError:
                # Timeout is expected, continue loop
                pass
            except Exception:
                logger.exception("Custom task error")
                await asyncio.sleep(10)  # Brief pause on error
    except asyncio.CancelledError:
        logger.info("Custom background task cancelled")
        raise
    finally:
        logger.info("Custom background task cleanup")

# In _serve(), start the task
custom_task = asyncio.create_task(
    custom_background_task(config, stop_event)
)

# On shutdown, cancel it
custom_task.cancel()
try:
    await custom_task
except asyncio.CancelledError:
    pass
```

### Port Conflict Handling

```python
# Server automatically handles port conflicts in _serve()
# If port is occupied, it attempts to clean up and retry

# You can also check manually:
from .server import _handle_port_conflict

host = "0.0.0.0"
port = 8080

if not _handle_port_conflict(host, port):
    logger.error("Port %d is occupied and cannot be freed", port)
    # Handle error
```

---

## Related Documentation

### Component Documentation
- [Component Analysis](../../tmp/component_analysis.md) - Architectural overview and component boundaries
- [AGENTS.md](../../AGENTS.md) - Developer guide with common patterns and commands

### Related Components
- **Alexa Integration** (Component 2) - Handler framework and SSML generation
- **Calendar Processing** (Component 3) - ICS parsing and event pipelines
- **Infrastructure** (Component 4) - HTTP client, health tracking, async utilities

### Module-Level Documentation
- [`server.py`](../../calendarbot_lite/server.py) - Full server implementation with docstrings
- [`routes/api_routes.py`](../../calendarbot_lite/routes/api_routes.py) - API endpoint implementations
- [`routes/alexa_routes.py`](../../calendarbot_lite/routes/alexa_routes.py) - Alexa route registration
- [`routes/static_routes.py`](../../calendarbot_lite/routes/static_routes.py) - Static file serving

### Configuration
- [`.env.example`](../../.env.example) - Environment variable reference
- [`config_manager.py`](../../calendarbot_lite/config_manager.py) - Configuration loading

### Testing
- [`tests/lite/smoke/test_lite_smoke_boot.py`](../../tests/lite/smoke/test_lite_smoke_boot.py) - Server startup tests
- [`tests/lite/unit/test_dependencies.py`](../../tests/lite/unit/test_dependencies.py) - Dependency injection tests

---

## Quick Reference

### Key Entry Points
- **CLI:** `python -m calendarbot_lite` → [`__main__.main()`](../../calendarbot_lite/__main__.py:45)
- **Programmatic:** [`run_server(args)`](../../calendarbot_lite/__init__.py:77) → [`start_server(config, skipped_store)`](../../calendarbot_lite/server.py:1422)
- **Async Core:** [`_serve(config, skipped_store)`](../../calendarbot_lite/server.py:1256) - Main async lifecycle

### Key Patterns
- **Event Window:** `event_window_ref: list[tuple[LiteCalendarEvent, ...]]` with `asyncio.Lock`
- **Route Registration:** Dependency injection via function parameters
- **Background Tasks:** Created with `asyncio.create_task()`, cancelled on shutdown
- **Health Tracking:** [`HealthTracker`](../../calendarbot_lite/health_tracker.py) instance available in all routes

### Environment Variables
- `CALENDARBOT_WEB_HOST` - Bind address (default: 0.0.0.0)
- `CALENDARBOT_WEB_PORT` - Server port (default: 8080)
- `CALENDARBOT_DEBUG` - Enable debug logging
- `CALENDARBOT_ALEXA_BEARER_TOKEN` - Alexa authentication

---

**End of HTTP Server & Routing Documentation**