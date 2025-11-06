# Configuration & Dependencies Component

**Component:** 5 of 5 - Configuration Layer
**Purpose:** Environment-based configuration, dependency injection, type-safe settings management
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

The Configuration & Dependencies component manages application settings through environment variables and provides a dependency injection container for testability and maintainability. All configuration is loaded from `.env` files or environment variables following the 12-factor app methodology.

### Position in Architecture

This component is consumed by **all other components** in the application:

```
┌──────────────────────────────────────────────────┐
│      Configuration & Dependencies (foundation)    │
│   config_manager.py, dependencies.py              │
└────────────────┬─────────────────────────────────┘
                 │
                 │ Consumed by all components ↓
                 │
    ┌────────────┼────────────┬──────────────┐
    ▼            ▼            ▼              ▼
  Server    Alexa Integ   Calendar Proc   Infrastructure
```

**References:**
- Architecture context: [`tmp/component_analysis.md`](../../tmp/component_analysis.md#L300-L323)
- Full architecture: [`AGENTS.md`](../../AGENTS.md#L93-L139)

### Key Design Patterns

1. **Environment-Based Configuration** - All settings from environment variables (12-factor)
2. **Dependency Injection Container** - [`AppDependencies`](../../calendarbot_lite/dependencies.py#L9-L50) dataclass for testability
3. **Type-Safe Settings** - Pydantic models for validation and serialization
4. **Non-Overriding Defaults** - `.env` only sets values not in environment
5. **Singleton Pattern** - Shared HTTP client and configuration manager

---

## Core Modules

### Configuration Management

#### [`config_manager.py`](../../calendarbot_lite/config_manager.py) - Environment Configuration (5KB)

**Primary Classes:**
- [`ConfigManager`](../../calendarbot_lite/config_manager.py#L14-L140) - Manages `.env` file loading and config building
  - [`load_env_file()`](../../calendarbot_lite/config_manager.py#L25-L73) - Loads `.env` without overriding existing env vars
  - [`build_config_from_env()`](../../calendarbot_lite/config_manager.py#L75-L126) - Builds config dict from environment
  - [`load_full_config()`](../../calendarbot_lite/config_manager.py#L128-L140) - Main entry point

**Utility Functions:**
- [`get_config_value()`](../../calendarbot_lite/config_manager.py#L143-L156) - Supports both dict and object attribute access

**Key Features:**
- Reads `.env` file with KEY=VALUE format
- Skips comments and empty lines
- Only sets variables not already in environment
- Supports quoted values (strips quotes)
- Logs loaded keys for debugging

**Environment Variable Mapping:**
```python
# Input                              → Output
CALENDARBOT_ICS_URL                  → config["ics_sources"] (list)
CALENDARBOT_REFRESH_INTERVAL         → config["refresh_interval_seconds"] (int)
CALENDARBOT_WEB_HOST                 → config["server_bind"] (str)
CALENDARBOT_WEB_PORT                 → config["server_port"] (int)
CALENDARBOT_ALEXA_BEARER_TOKEN       → config["alexa_bearer_token"] (str)
```

### Dependency Injection

#### [`dependencies.py`](../../calendarbot_lite/dependencies.py) - Dependency Container

**Primary Classes:**
- [`AppDependencies`](../../calendarbot_lite/dependencies.py#L9-L50) - Dataclass container for all dependencies
  - Configuration: `config`, `config_manager`
  - State: `event_window_ref`, `window_lock`, `stop_event`, `skipped_store`
  - Infrastructure: `shared_http_client`, `health_tracker`
  - Business Logic: `event_filter`, `window_manager`, `fetch_orchestrator`
  - Utilities: `time_provider`, `get_config_value`, timezone functions, SSML renderers

- [`DependencyContainer`](../../calendarbot_lite/dependencies.py#L52-L146) - Factory for building dependencies
  - [`build_dependencies()`](../../calendarbot_lite/dependencies.py#L55-L146) - Constructs all application dependencies

**Key Features:**
- Single dataclass holds all shared dependencies
- Factory method initializes all components
- Enables easy mocking for tests
- Explicit dependency graph
- Async-safe shared resources

### Data Models & Type Definitions

#### [`lite_models.py`](../../calendarbot_lite/lite_models.py) - Core Data Models (326 lines)

**Configuration Models:**
- [`LiteICSSource`](../../calendarbot_lite/lite_models.py#L46-L65) - ICS source configuration
  - `name`, `url`, `auth` (LiteICSAuth)
  - `refresh_interval`, `timeout`, `custom_headers`
  - `validate_ssl` flag
- [`LiteICSAuth`](../../calendarbot_lite/lite_models.py#L21-L43) - Authentication configuration
  - [`get_headers()`](../../calendarbot_lite/lite_models.py#L29-L43) - Generate auth headers

**Response Models:**
- [`LiteICSResponse`](../../calendarbot_lite/lite_models.py#L68-L126) - ICS fetch response
  - Streaming support: `stream_handle`, `stream_mode`
  - HTTP caching: `etag`, `last_modified`, `cache_control`
  - [`get_content_or_stream()`](../../calendarbot_lite/lite_models.py#L118-L126) - Unified content access

**Event Models:**
- [`LiteCalendarEvent`](../../calendarbot_lite/lite_models.py#L265-L326) - Main event model
  - Core: `id`, `subject`, `body_preview`
  - Time: `start`, `end`, `is_all_day`
  - Status: `show_as`, `is_cancelled`, `is_organizer`
  - Recurrence: `is_recurring`, `recurrence_id`, `rrule_master_uid`
  - [`is_busy_status`](../../calendarbot_lite/lite_models.py#L311-L319) - Property for busy check

**Supporting Models:**
- [`LiteDateTimeInfo`](../../calendarbot_lite/lite_models.py#L234-L243) - DateTime with timezone
- [`LiteLocation`](../../calendarbot_lite/lite_models.py#L246-L251) - Location details
- [`LiteAttendee`](../../calendarbot_lite/lite_models.py#L254-L262) - Attendee information

**Enums:**
- [`LiteEventStatus`](../../calendarbot_lite/lite_models.py#L205-L212) - Event status values
- [`LiteAttendeeType`](../../calendarbot_lite/lite_models.py#L215-L220) - Attendee types
- [`LiteResponseStatus`](../../calendarbot_lite/lite_models.py#L223-L231) - Response statuses

---

## Key Interfaces & Data Structures

### Configuration Dictionary Structure

```python
# From config_manager.py
config: dict[str, Any] = {
    # Required
    "ics_sources": list[str],               # ICS feed URLs

    # Server settings
    "server_bind": str,                     # Host to bind (default: "0.0.0.0")
    "server_port": int,                     # Port (default: 8080)
    "refresh_interval_seconds": int,        # Refresh interval (default: 300)

    # Processing settings
    "rrule_expansion_days": int,            # RRULE expansion window
    "event_window_size": int,               # Max events to keep

    # Authentication
    "alexa_bearer_token": str | None,       # Alexa API auth token
}
```

### Environment Variable Naming Convention

**Pattern:** `CALENDARBOT_<COMPONENT>_<SETTING>`

**Examples:**
```bash
# Required
CALENDARBOT_ICS_URL=https://calendar.ics

# Server
CALENDARBOT_WEB_HOST=0.0.0.0
CALENDARBOT_WEB_PORT=8080
CALENDARBOT_REFRESH_INTERVAL=300

# Alexa
CALENDARBOT_ALEXA_BEARER_TOKEN=token123

# Logging
CALENDARBOT_DEBUG=true
CALENDARBOT_LOG_LEVEL=DEBUG

# Testing
CALENDARBOT_TEST_TIME=2024-01-01T12:00:00
CALENDARBOT_NONINTERACTIVE=true
CALENDARBOT_PRODUCTION=true
```

### Dependency Injection Container

```python
# From dependencies.py
@dataclass
class AppDependencies:
    # Configuration
    config: Any
    config_manager: Any

    # State management
    event_window_ref: list[tuple[dict[str, Any], ...]]
    window_lock: asyncio.Lock
    stop_event: asyncio.Event
    skipped_store: object | None

    # Infrastructure
    shared_http_client: aiohttp.ClientSession
    health_tracker: HealthTracker

    # Business logic
    event_filter: EventFilter
    window_manager: EventWindowManager
    fetch_orchestrator: FetchOrchestrator

    # Utility functions
    time_provider: Callable
    get_config_value: Callable
    get_server_timezone: Callable
    serialize_iso: Callable
    # ... more utilities
```

### Type Definitions for Configuration

**From [`lite_models.py`](../../calendarbot_lite/lite_models.py):**
- All models use Pydantic BaseModel for validation
- `ConfigDict(use_enum_values=True)` for enum serialization
- `@field_serializer` decorators for datetime formatting
- `@property` methods for computed values

---

## Integration Points

### How Components Access Configuration

**Server Layer ([`server.py`](../../calendarbot_lite/server.py)):**
```python
# Load configuration at startup
config_mgr = ConfigManager()
config = config_mgr.load_full_config()

# Apply CLI overrides
if args.port:
    config["server_port"] = args.port

# Pass to server
start_server(config, skipped_store)
```

**Route Handlers ([`routes/api_routes.py`](../../calendarbot_lite/routes/api_routes.py)):**
```python
# Configuration injected via route registration
def health_check(
    health_tracker: HealthTracker,
    get_system_diagnostics: Callable,
    config: dict[str, Any],
) -> web.Response:
    # Access config values
    refresh_interval = config.get("refresh_interval_seconds", 300)
```

**Alexa Handlers ([`alexa_handlers.py`](../../calendarbot_lite/alexa_handlers.py)):**
```python
# Configuration passed during handler instantiation
handler = NextMeetingHandler(
    bearer_token=config.get("alexa_bearer_token"),
    event_window_ref=event_window_ref,
    window_lock=window_lock,
)
```

### Dependency Injection Flow

```
Application Startup
  ↓
ConfigManager.load_full_config()
  ↓
DependencyContainer.build_dependencies(config, ...)
  ↓
AppDependencies dataclass (all dependencies)
  ↓
Route Registration (inject dependencies)
  ↓
Request Handlers (use injected dependencies)
```

### Environment Variable Flow

```
.env file
  ↓
ConfigManager.load_env_file()
  ↓
os.environ (only if not already set)
  ↓
ConfigManager.build_config_from_env()
  ↓
config: dict[str, Any]
  ↓
Application components
```

### Testing with Custom Configuration

**Unit Tests:**
```python
# Mock configuration
config = {
    "ics_sources": ["https://test.ics"],
    "refresh_interval_seconds": 60,
    "server_port": 9999,
}

# Mock dependencies
deps = AppDependencies(
    config=config,
    event_window_ref=[()],
    window_lock=asyncio.Lock(),
    # ... mock other dependencies
)
```

**Integration Tests:**
```python
# Override environment for testing
os.environ["CALENDARBOT_TEST_TIME"] = "2024-01-01T12:00:00"
os.environ["CALENDARBOT_ICS_URL"] = "https://test-calendar.ics"

# Load config with test values
config_mgr = ConfigManager()
config = config_mgr.load_full_config()
```

---

## Common Usage Patterns

### Accessing Configuration Values

**Using `get_config_value()` utility:**
```python
from calendarbot_lite.config_manager import get_config_value

# Works with both dicts and objects
refresh_interval = get_config_value(config, "refresh_interval_seconds", 300)
server_port = get_config_value(config, "server_port", 8080)
```

**Direct dict access with defaults:**
```python
# Standard dict.get() pattern
ics_sources = config.get("ics_sources", [])
bearer_token = config.get("alexa_bearer_token")
```

### Adding New Configuration Options

**1. Add to `.env.example`:**
```bash
# .env.example
CALENDARBOT_NEW_SETTING=default_value
```

**2. Update `ConfigManager.build_config_from_env()`:**
```python
# In config_manager.py
def build_config_from_env(self) -> dict[str, Any]:
    cfg: dict[str, Any] = {}

    # Add new setting
    new_setting = os.environ.get("CALENDARBOT_NEW_SETTING")
    if new_setting:
        cfg["new_setting"] = new_setting

    return cfg
```

**3. Document in [`AGENTS.md`](../../AGENTS.md#L93-L139):**
```markdown
**New Setting:**
- `CALENDARBOT_NEW_SETTING` - Description of setting
```

### Registering Dependencies

**Add to `AppDependencies` dataclass:**
```python
@dataclass
class AppDependencies:
    # ... existing fields

    # Add new dependency
    new_component: NewComponent
```

**Initialize in `DependencyContainer.build_dependencies()`:**
```python
def build_dependencies(...) -> AppDependencies:
    # ... existing initialization

    # Create new component
    new_component = NewComponent(config)

    return AppDependencies(
        # ... existing deps
        new_component=new_component,
    )
```

### Testing with Mock Configuration

**Pytest fixture for config:**
```python
import pytest

@pytest.fixture
def test_config():
    return {
        "ics_sources": ["https://test.ics"],
        "server_bind": "127.0.0.1",
        "server_port": 8888,
        "refresh_interval_seconds": 60,
        "alexa_bearer_token": "test-token",
    }

@pytest.fixture
def test_dependencies(test_config):
    return AppDependencies(
        config=test_config,
        event_window_ref=[()],
        window_lock=asyncio.Lock(),
        stop_event=asyncio.Event(),
        # ... mock other dependencies
    )
```

**Override environment in tests:**
```python
import os
from unittest.mock import patch

def test_config_loading():
    with patch.dict(os.environ, {
        "CALENDARBOT_ICS_URL": "https://test.ics",
        "CALENDARBOT_WEB_PORT": "9999",
    }):
        config_mgr = ConfigManager()
        config = config_mgr.load_full_config()

        assert config["ics_sources"] == ["https://test.ics"]
        assert config["server_port"] == 9999
```

### Environment Variable Validation

**Type conversion with error handling:**
```python
# From config_manager.py
try:
    cfg["server_port"] = int(port)
except Exception:
    logger.warning("Invalid CALENDARBOT_WEB_PORT=%r; ignoring", port)
```

**Boolean parsing:**
```python
# Parse "true"/"false" strings
debug_str = os.environ.get("CALENDARBOT_DEBUG", "").lower()
debug = debug_str in ("true", "1", "yes")
```

**List parsing:**
```python
# Parse comma-separated list
sources_str = os.environ.get("CALENDARBOT_ICS_URLS", "")
sources = [s.strip() for s in sources_str.split(",") if s.strip()]
```

---

## Code Examples

### Example 1: Loading Configuration at Startup

**From [`__main__.py`](../../calendarbot_lite/__main__.py):**
```python
def main() -> None:
    """Main entry point for calendarbot_lite server."""
    import argparse
    from .config_manager import ConfigManager

    parser = argparse.ArgumentParser(description="CalendarBot Lite Server")
    parser.add_argument("--port", type=int, help="Server port override")
    args = parser.parse_args()

    # Load configuration from .env and environment
    config_mgr = ConfigManager()
    config = config_mgr.load_full_config()

    # Apply CLI overrides
    if args.port:
        config["server_port"] = args.port

    # Start server with configuration
    from . import run_server
    run_server(config)
```

### Example 2: Building Dependencies

**From [`dependencies.py`](../../calendarbot_lite/dependencies.py#L55-L146):**
```python
@staticmethod
def build_dependencies(
    config: Any,
    skipped_store: object | None,
    shared_http_client: Any,
) -> AppDependencies:
    """Build all application dependencies."""
    import asyncio
    from .health_tracker import HealthTracker
    from .event_filter import EventFilter, EventWindowManager

    # Initialize components
    health_tracker = HealthTracker()
    event_window_ref: list[tuple[dict[str, Any], ...]] = [()]
    window_lock = asyncio.Lock()
    stop_event = asyncio.Event()

    # Build event filtering components
    event_filter = EventFilter(get_server_timezone, get_fallback_timezone)
    window_manager = EventWindowManager(event_filter, fallback_handler)

    # Return container
    return AppDependencies(
        config=config,
        event_window_ref=event_window_ref,
        window_lock=window_lock,
        # ... all other dependencies
    )
```

### Example 3: Accessing Configuration in Routes

**From [`routes/api_routes.py`](../../calendarbot_lite/routes/api_routes.py):**
```python
async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint with system diagnostics."""
    # Dependencies injected by route registration
    health_tracker = request.app["health_tracker"]
    config = request.app["config"]
    get_system_diagnostics = request.app["get_system_diagnostics"]

    # Access config values
    refresh_interval = config.get("refresh_interval_seconds", 300)

    # Build health response
    diagnostics = get_system_diagnostics()
    health_status = {
        "status": "healthy",
        "refresh_interval": refresh_interval,
        "last_refresh": health_tracker.last_refresh,
        "total_refreshes": health_tracker.total_refreshes,
        **diagnostics,
    }

    return web.json_response(health_status)
```

### Example 4: Testing with Custom Configuration

**Test example:**
```python
import pytest
import asyncio
from calendarbot_lite.dependencies import AppDependencies

@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        "ics_sources": ["https://test-calendar.ics"],
        "server_bind": "127.0.0.1",
        "server_port": 8888,
        "refresh_interval_seconds": 60,
        "rrule_expansion_days": 90,
        "event_window_size": 50,
    }

@pytest.fixture
def test_dependencies(test_config):
    """Provide test dependencies container."""
    return AppDependencies(
        config=test_config,
        event_window_ref=[()],
        window_lock=asyncio.Lock(),
        stop_event=asyncio.Event(),
        skipped_store=None,
        shared_http_client=None,  # Mock as needed
        health_tracker=None,      # Mock as needed
        # ... other dependencies
    )

async def test_event_filtering(test_dependencies):
    """Test event filtering with custom config."""
    config = test_dependencies.config
    event_filter = test_dependencies.event_filter

    # Test uses configuration
    assert config["event_window_size"] == 50
```

### Example 5: Environment Variable Override for Testing

**From test setup:**
```python
import os
import pytest
from unittest.mock import patch

@pytest.fixture
def override_test_time():
    """Override current time for testing."""
    with patch.dict(os.environ, {
        "CALENDARBOT_TEST_TIME": "2024-06-15T10:00:00",
    }):
        yield

def test_time_based_logic(override_test_time):
    """Test time-dependent logic with fixed time."""
    from calendarbot_lite.timezone_utils import now_utc

    # now_utc() returns mocked time
    current = now_utc()
    assert current.year == 2024
    assert current.month == 6
```

### Example 6: Adding New Configuration Option

**Step-by-step example:**

**1. Add to `.env.example`:**
```bash
# Cache Configuration
CALENDARBOT_CACHE_SIZE=100
```

**2. Update `config_manager.py`:**
```python
def build_config_from_env(self) -> dict[str, Any]:
    cfg: dict[str, Any] = {}

    # ... existing config loading

    # Cache size configuration
    cache_size = os.environ.get("CALENDARBOT_CACHE_SIZE")
    if cache_size:
        try:
            cfg["cache_size"] = int(cache_size)
        except Exception:
            logger.warning("Invalid CALENDARBOT_CACHE_SIZE=%r; ignoring", cache_size)

    return cfg
```

**3. Use in application:**
```python
from calendarbot_lite.config_manager import get_config_value

cache_size = get_config_value(config, "cache_size", 100)
response_cache = ResponseCache(max_size=cache_size)
```

---

## Related Documentation

### Component Documentation
- **[01-server-http-routing.md](01-server-http-routing.md)** - Server lifecycle and configuration usage
- **[02-alexa-integration.md](02-alexa-integration.md)** - Alexa handler configuration and bearer tokens
- **[03-calendar-processing.md](03-calendar-processing.md)** - ICS source configuration and processing settings
- **[04-infrastructure.md](04-infrastructure.md)** - Health tracking and HTTP client configuration

### Architecture & Setup
- **[`tmp/component_analysis.md`](../../tmp/component_analysis.md)** - Component analysis and architecture
- **[`AGENTS.md`](../../AGENTS.md)** - Complete environment variable reference
- **[`.env.example`](../../.env.example)** - Complete configuration template

### Configuration Reference
- **Environment Variables:** [`AGENTS.md` - Configuration](../../AGENTS.md#L93-L139)
- **Type Models:** [`lite_models.py`](../../calendarbot_lite/lite_models.py)
- **Dependency Injection:** [`dependencies.py`](../../calendarbot_lite/dependencies.py)

---

## Environment Variables Reference

**Complete list from [`.env.example`](../../.env.example):**

### Required
- `CALENDARBOT_ICS_URL` - ICS calendar feed URL

### Server Configuration
- `CALENDARBOT_WEB_HOST` - Bind address (default: `0.0.0.0`)
- `CALENDARBOT_WEB_PORT` - Port number (default: `8080`)
- `CALENDARBOT_REFRESH_INTERVAL` - Refresh interval in seconds (default: `300`)

### Alexa Integration
- `CALENDARBOT_ALEXA_BEARER_TOKEN` - Bearer token for Alexa API authentication

### Logging Configuration
- `CALENDARBOT_DEBUG` - Enable debug logging (`true`/`false`)
- `CALENDARBOT_LOG_LEVEL` - Override log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

### Advanced/Testing
- `CALENDARBOT_NONINTERACTIVE` - Disable interactive prompts (`true`/`false`)
- `CALENDARBOT_TEST_TIME` - Override current time for testing (ISO 8601 format)
- `CALENDARBOT_PRODUCTION` - Enable production optimizations (`true`/`false`)

---

**Last Updated:** 2025-11-03
**Maintained By:** CalendarBot Lite Project
**Related Components:** All components depend on this foundation layer