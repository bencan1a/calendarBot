# Infrastructure Layer - calendarbot_lite

**Component documentation for cross-cutting infrastructure concerns**

Part 4 of the calendarbot_lite component documentation series.

---

## Overview

The Infrastructure layer provides shared utilities, performance optimization, observability, and debugging capabilities used across all other components. This layer implements cross-cutting concerns including async patterns, HTTP client management, health monitoring, logging, configuration management, and dependency injection.

### Purpose and Responsibilities

- **Async Patterns**: Reusable async utilities (timeouts, retries, worker pools, task management)
- **HTTP Client**: Connection pooling, retry logic, rate limiting, error handling
- **Fetch Coordination**: Orchestrates calendar fetching with deduplication and scheduling
- **Health Monitoring**: System health tracking, metrics collection, status reporting
- **Logging**: Structured logging, debug modes, log configuration
- **Configuration**: Environment-based configuration management
- **Debugging**: Diagnostic tools, performance profiling, troubleshooting utilities
- **Dependency Injection**: Centralized dependency management and initialization

### Position in Architecture

The Infrastructure layer is **foundational** - it's used by all other layers:

```
┌─────────────────────────────────────────┐
│  Server & HTTP (01) / Alexa (02)        │
│  Calendar Processing (03)                │
└─────────────────┬───────────────────────┘
                  │ uses
                  ↓
┌─────────────────────────────────────────┐
│  INFRASTRUCTURE (04)                     │
│  - async_utils (async patterns)         │
│  - http_client (HTTP with pooling)      │
│  - fetch_orchestrator (coordination)    │
│  - health_tracker (monitoring)          │
│  - lite_logging (configuration)         │
│  - monitoring_logging (structured logs) │
│  - config_manager (environment)         │
│  - dependencies (DI container)          │
│  - debug_helpers (diagnostics)          │
└─────────────────────────────────────────┘
```

### Key Design Patterns

1. **Connection Pooling**: Single shared httpx.AsyncClient across application
2. **Async Orchestration**: Centralized async patterns with timeout/retry logic
3. **Health Tracking**: Centralized metrics collection with event-based updates
4. **Bounded Concurrency**: Semaphore-based resource management
5. **Dependency Injection**: Centralized initialization and lifecycle management
6. **Structured Logging**: Context-aware logging with rate limiting
7. **Environment Configuration**: .env file-based configuration with overrides

---

## Core Modules

### [`async_utils.py`](../calendarbot_lite/async_utils.py) - Async Helpers and Utilities (21KB)

**Purpose**: Provides centralized async orchestration patterns including ThreadPoolExecutor management, timeout handling, retry logic, and bounded concurrency.

**Key Classes**:
- [`AsyncOrchestrator`](../calendarbot_lite/async_utils.py) - Centralized async patterns and resource management

**Key Methods**:
- [`run_with_timeout()`](../calendarbot_lite/async_utils.py) - Execute coroutine with timeout enforcement
- [`run_in_executor()`](../calendarbot_lite/async_utils.py) - Run blocking function in ThreadPoolExecutor
- [`gather_with_timeout()`](../calendarbot_lite/async_utils.py) - Concurrent execution with global timeout
- [`retry_async()`](../calendarbot_lite/async_utils.py) - Retry async operation with exponential backoff
- [`get_global_orchestrator()`](../calendarbot_lite/async_utils.py) - Get shared orchestrator instance

**Responsibilities**:
- ThreadPoolExecutor lifecycle management (creation, reuse, cleanup)
- Event loop detection and safe execution
- Timeout enforcement with proper cancellation
- Retry logic with configurable backoff strategies
- Semaphore-based concurrency control
- Background task lifecycle management

**Design Goals**:
1. Eliminate scattered ThreadPoolExecutor usage across codebase
2. Provide safe event loop handling for mixed sync/async contexts
3. Centralize timeout and retry configuration
4. Enable consistent error handling and logging patterns
5. Simplify async code with reusable utilities

**Common Use Cases**:
- Running RRULE expansion in isolated event loop (CPU-intensive)
- HTTP requests with timeout enforcement
- Retrying calendar fetches on transient failures
- Parallel event processing with bounded concurrency

---

### [`http_client.py`](../calendarbot_lite/http_client.py) - HTTP Client with Connection Pooling (12KB)

**Purpose**: Manages shared HTTP client lifecycle with connection pooling, optimized for Pi Zero 2W performance. Eliminates per-request client creation overhead.

**Key Functions**:
- [`get_shared_client()`](../calendarbot_lite/http_client.py) - Get or create shared httpx.AsyncClient
- [`record_client_error()`](../calendarbot_lite/http_client.py) - Track client errors for health monitoring
- [`record_client_success()`](../calendarbot_lite/http_client.py) - Track successful requests
- [`_create_ipv4_transport()`](../calendarbot_lite/http_client.py) - Create IPv4-only transport

**Responsibilities**:
- Single shared `httpx.AsyncClient` for connection pooling
- Pi Zero 2W optimized limits (max_connections=4, keepalive=2)
- IPv4-only transport to avoid DNS resolution issues
- Browser-like headers for compatibility (e.g., Office365)
- Health tracking with automatic client recreation on errors
- Timeout configuration (connect=10s, read=30s, write=10s, pool=30s)

**Configuration Constants**:
- `_PI_ZERO_LIMITS`: Conservative connection limits for low-memory device
- `_PI_ZERO_TIMEOUT`: Timeout configuration for ICS fetching
- `DEFAULT_BROWSER_HEADERS`: Browser-like headers for compatibility
- `HEALTH_ERROR_THRESHOLD`: Recreate client after 3 consecutive errors
- `HEALTH_TIMEOUT_SECONDS`: Consider client unhealthy after 5 minutes

**Health Monitoring**:
Client health tracked globally with automatic recreation when:
- 3+ consecutive errors detected
- 5+ minutes since last successful request
- Client health degraded beyond threshold

---

### [`fetch_orchestrator.py`](../calendarbot_lite/fetch_orchestrator.py) - Calendar Fetch Coordination (10KB)

**Purpose**: Orchestrates fetching from multiple ICS sources with bounded concurrency, timeout management, and error handling.

**Key Classes**:
- [`FetchOrchestrator`](../calendarbot_lite/fetch_orchestrator.py) - Coordinates multi-source calendar fetching

**Key Methods**:
- [`fetch_all_sources()`](../calendarbot_lite/fetch_orchestrator.py) - Fetch and parse all sources concurrently
- [`refresh_once()`](../calendarbot_lite/fetch_orchestrator.py) - Single refresh cycle with pipeline processing

**Responsibilities**:
- **Bounded Concurrency**: Semaphore-controlled parallel fetching (fetch_concurrency limit)
- **Timeout Management**: 120s timeout for fetching all sources via AsyncOrchestrator
- **Error Recovery**: Continues with partial results if some sources fail
- **Health Integration**: Reports fetch metrics to health tracker
- **Pipeline Coordination**: Orchestrates multi-stage event processing pipeline

**Integration**:
Uses [`AsyncOrchestrator.gather_with_timeout()`](../calendarbot_lite/async_utils.py) for consistent async patterns and timeout enforcement.

---

### [`health_tracker.py`](../calendarbot_lite/health_tracker.py) - System Health Monitoring (8KB)

**Purpose**: Centralized health tracking, metrics collection, and status reporting for observability and monitoring.

**Key Classes**:
- [`HealthTracker`](../calendarbot_lite/health_tracker.py) - Thread-safe health metrics tracking
- [`HealthStatus`](../calendarbot_lite/health_tracker.py) - Health status dataclass
- [`SystemDiagnostics`](../calendarbot_lite/health_tracker.py) - System diagnostics dataclass

**Key Methods**:
- [`record_refresh_attempt()`](../calendarbot_lite/health_tracker.py) - Record refresh attempt
- [`record_refresh_success()`](../calendarbot_lite/health_tracker.py) - Record successful refresh
- [`record_background_heartbeat()`](../calendarbot_lite/health_tracker.py) - Record background task heartbeat
- [`record_render_probe()`](../calendarbot_lite/health_tracker.py) - Record render probe result
- [`update()`](../calendarbot_lite/health_tracker.py) - Batch update multiple metrics
- [`get_health_status()`](../calendarbot_lite/health_tracker.py) - Get current health status

**Tracked Metrics**:
- **Refresh Metrics**: Last attempt, last success, event count
- **Background Task**: Heartbeat timestamp (task alive indicator)
- **Render Probe**: Last probe time, success status, notes
- **Uptime**: Server start time, uptime duration
- **PID**: Process ID for monitoring

**Health Status Values**:
- `"ok"` - System healthy, recent successful refresh
- `"degraded"` - Stale data or intermittent failures
- `"critical"` - No successful refresh, persistent errors

---

### [`lite_logging.py`](../calendarbot_lite/lite_logging.py) - Logging Configuration

**Purpose**: Configures logging levels optimized for Pi Zero 2W performance by suppressing verbose debug logs from third-party libraries while maintaining diagnostic information.

**Key Functions**:
- [`configure_lite_logging()`](../calendarbot_lite/lite_logging.py) - Configure logging for calendarbot_lite

**Configuration**:
- **Debug Mode**: `CALENDARBOT_DEBUG=true` enables DEBUG level
- **Log Level Override**: `CALENDARBOT_LOG_LEVEL` environment variable
- **Default Level**: INFO for production, DEBUG for development
- **Format**: Preserves colorful formatters from `__init__.py`

**Third-Party Library Suppression** (WARNING level):
- `aiohttp.access`, `aiohttp.server`, `aiohttp.web_log` - HTTP server logs
- `httpx` - HTTP client debug logs
- `asyncio` - Event loop debug logs
- `urllib3.connectionpool` - Connection pool logs
- `charset_normalizer`, `multipart` - Noisy parsing libraries

**CalendarBot Modules** (DEBUG/INFO based on mode):
- `calendarbot_lite.*` - All calendarbot_lite modules
- Level controlled by `debug_mode` parameter or `CALENDARBOT_DEBUG` env var

---

### [`monitoring_logging.py`](../calendarbot_lite/monitoring_logging.py) - Structured Logging

**Purpose**: Enhanced monitoring with structured JSON logging, consistent field schema, rate limiting, and multi-destination output support.

**Key Classes**:
- [`LogEntry`](../calendarbot_lite/monitoring_logging.py) - Structured log entry with schema
- [`MonitoringLogger`](../calendarbot_lite/monitoring_logging.py) - Logger with rate limiting

**Key Features**:
- **Structured Schema**: Consistent JSON schema (component, level, event, message, details)
- **Rate Limiting**: Prevents log flooding from repeated events
- **Context Managers**: `@contextmanager` for operation tracking
- **Multi-Destination**: Stdout, file, and custom handlers
- **Recovery Levels**: Escalation levels 0-4 for error recovery tracking

**Schema Fields**:
- `timestamp` - ISO 8601 UTC timestamp
- `component` - Component name (server, watchdog, health, recovery)
- `level` - Log level (DEBUG, INFO, WARN, ERROR, CRITICAL)
- `event` - Short event code (e.g., "health.endpoint.check")
- `message` - Human-readable description
- `details` - Additional context data (dict)
- `action_taken` - Description of action taken (optional)
- `recovery_level` - Recovery escalation level 0-4 (optional)
- `system_state` - Current system metrics (optional)
- `schema_version` - Schema version ("1.0")

---

### [`config_manager.py`](../calendarbot_lite/config_manager.py) - Configuration Management (5KB)

**Purpose**: Manages application configuration from environment variables and .env files with backward compatibility.

**Key Classes**:
- [`ConfigManager`](../calendarbot_lite/config_manager.py) - Environment-based configuration

**Key Methods**:
- [`load_env_file()`](../calendarbot_lite/config_manager.py) - Load .env file into environment
- [`build_config_from_env()`](../calendarbot_lite/config_manager.py) - Build config dict from environment

**Recognized Environment Variables**:
- `CALENDARBOT_ICS_URL` → `ics_sources` (list with single URL)
- `CALENDARBOT_REFRESH_INTERVAL` → `refresh_interval_seconds` (int)
- `CALENDARBOT_WEB_HOST` / `CALENDARBOT_SERVER_BIND` → `server_bind`
- `CALENDARBOT_WEB_PORT` / `CALENDARBOT_SERVER_PORT` → `server_port` (int)
- `CALENDARBOT_ALEXA_BEARER_TOKEN` → `alexa_bearer_token`

**Behavior**:
- Only sets variables NOT already in environment (no overrides)
- Skips empty lines and comments in .env file
- Strips quotes from values
- Returns list of keys loaded from .env

---

### [`dependencies.py`](../calendarbot_lite/dependencies.py) - Dependency Injection

**Purpose**: Centralized dependency management, initialization, and lifecycle coordination.

**Key Classes**:
- [`AppDependencies`](../calendarbot_lite/dependencies.py) - Container dataclass for all dependencies
- [`DependencyContainer`](../calendarbot_lite/dependencies.py) - Factory for building dependencies

**Key Methods**:
- [`DependencyContainer.build_dependencies()`](../calendarbot_lite/dependencies.py) - Initialize all dependencies

**Managed Dependencies**:
- **Configuration**: config dict
- **State Management**: event_window_ref, window_lock, stop_event, skipped_store
- **Infrastructure**: shared_http_client, health_tracker
- **Business Logic**: config_manager, event_filter, window_manager, fetch_orchestrator
- **Utilities**: time_provider, get_config_value, timezone functions, serializers
- **SSML Renderers**: Optional Alexa SSML rendering functions

**Pattern**:
```python
# Build dependencies at server startup
deps = DependencyContainer.build_dependencies(config, skipped_store, http_client)

# Access dependencies throughout application
health = deps.health_tracker
orchestrator = deps.fetch_orchestrator
```

**Circular Dependency Resolution**:
Uses dynamic imports from [`server`](../calendarbot_lite/server.py) module to avoid circular imports.

---

### [`debug_helpers.py`](../calendarbot_lite/debug_helpers.py) - Debugging Utilities

**Purpose**: Lightweight debug helpers for calendar diagnostics with minimal dependencies.

**Key Functions**:
- [`read_env()`](../calendarbot_lite/debug_helpers.py) - Read minimal env keys from .env file
- [`fetch_ics_stream()`](../calendarbot_lite/debug_helpers.py) - Async generator yielding ICS bytes
- [`parse_stream_via_parser()`](../calendarbot_lite/debug_helpers.py) - Call lite_parser.parse_ics_stream
- [`event_summary()`](../calendarbot_lite/debug_helpers.py) - Serializable summary of LiteCalendarEvent
- [`collect_rrule_candidates()`](../calendarbot_lite/debug_helpers.py) - Extract RRULE events for expansion

**Design Goals**:
- **Minimal Dependencies**: Can be imported by debug scripts without core library changes
- **Backward Compatibility**: Supports legacy `ICS_SOURCE` and new `CALENDARBOT_ICS_URL`
- **Stream-Based**: Works with async streaming for large ICS files
- **Serializable Output**: JSON-compatible summaries for reporting

**Common Use Cases**:
- Debug scripts analyzing recurring event expansion
- ICS feed diagnostics and validation
- Performance profiling of parsing/expansion
- Test fixture generation

---

## Key Interfaces & Data Structures

### Async Orchestrator Interface

```python
class AsyncOrchestrator:
    def __init__(self, max_workers: int = 4):
        """Initialize with ThreadPoolExecutor pool."""
    
    async def run_with_timeout(
        self,
        coro: Coroutine,
        timeout: float,
        operation_name: str = "operation"
    ) -> Any:
        """Run coroutine with timeout enforcement."""
    
    async def run_in_executor(
        self,
        func: Callable,
        *args: Any
    ) -> Any:
        """Run blocking function in ThreadPoolExecutor."""
    
    async def gather_with_timeout(
        self,
        *coros: Coroutine,
        timeout: float,
        return_exceptions: bool = False
    ) -> list[Any]:
        """Gather multiple coroutines with global timeout."""
    
    async def retry_async(
        self,
        func: Callable,
        max_retries: int = 3,
        backoff: float = 1.0,
        **kwargs: Any
    ) -> Any:
        """Retry async function with exponential backoff."""
```

---

### HTTP Client Interface

```python
async def get_shared_client(
    client_id: str = "default",
    limits: httpx.Limits | None = None,
    timeout: httpx.Timeout | None = None
) -> httpx.AsyncClient:
    """Get or create shared HTTP client with connection pooling.
    
    Features:
    - Connection pooling (reuses TCP connections)
    - Pi Zero 2W optimized limits (max_connections=4)
    - IPv4-only transport (avoids DNS issues)
    - Browser-like headers for compatibility
    - Health tracking with automatic recreation
    """
```

---

### Health Status Structure

```python
@dataclass
class HealthStatus:
    status: str  # "ok", "degraded", or "critical"
    server_time_iso: str
    uptime_seconds: int
    pid: int
    event_count: int
    last_refresh_success_age_seconds: int | None
    background_tasks: list[dict[str, Any]]
```

**Used By**:
- [`/health`](../calendarbot_lite/routes/api_routes.py) endpoint
- [`/api/health`](../calendarbot_lite/routes/api_routes.py) detailed status
- Monitoring systems and health checks

---

### Log Entry Schema

```python
{
    "timestamp": "2025-01-01T12:00:00.000Z",  # ISO 8601 UTC
    "component": "server",  # server|watchdog|health|recovery
    "level": "INFO",  # DEBUG|INFO|WARN|ERROR|CRITICAL
    "event": "health.endpoint.check",  # Short event code
    "message": "Health check completed",  # Human-readable
    "details": {  # Additional context
        "event_count": 50,
        "duration_ms": 5
    },
    "action_taken": "Refreshed calendar",  # Optional
    "recovery_level": 0,  # Optional: 0-4
    "system_state": {},  # Optional: Current metrics
    "schema_version": "1.0"
}
```

---

### Configuration Dictionary

```python
config: dict[str, Any] = {
    "ics_sources": list[str],          # ICS feed URLs
    "server_bind": str,                 # Host to bind (default: "0.0.0.0")
    "server_port": int,                 # Port (default: 8080)
    "refresh_interval_seconds": int,    # Background refresh interval (default: 300)
    "rrule_expansion_days": int,        # RRULE window (default: 90)
    "event_window_size": int,           # Max events to keep (default: 50)
    "alexa_bearer_token": str | None,   # Alexa auth token
}
```

---

## Integration Points

### Dependency Injection Flow

```
Server Startup (server.py)
    ↓
ConfigManager.load_env_file()
    ↓
ConfigManager.build_config_from_env()
    ↓
get_shared_client() - Create HTTP client
    ↓
DependencyContainer.build_dependencies()
    ↓
├── Create HealthTracker
├── Create EventFilter, EventWindowManager
├── Create FetchOrchestrator
└── Wire dependencies together
    ↓
Server.run() - Use dependencies
    ↓
Server Shutdown
    ↓
Cleanup resources (HTTP client, orchestrator)
```

---

### Health Monitoring Integration

All components report to [`HealthTracker`](../calendarbot_lite/health_tracker.py):

```python
# Fetch orchestrator reports
health.record_refresh_attempt()
health.record_refresh_success(event_count=50)

# Background task reports
health.record_background_heartbeat()

# Render probe reports
health.record_render_probe(ok=True, notes="Rendered successfully")

# API routes expose
status = health.get_health_status()
is_ok = status.status == "ok"
```

---

### Logging Integration

All modules use [`configure_lite_logging()`](../calendarbot_lite/lite_logging.py) for consistent logging:

```python
from calendarbot_lite.lite_logging import configure_lite_logging
import logging

# Setup (called at startup)
configure_lite_logging(debug_mode=False)

# Use throughout application
logger = logging.getLogger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)
```

**Debug Mode**: `CALENDARBOT_DEBUG=true` enables DEBUG level globally.

---

### Async Orchestration Integration

All async operations use [`AsyncOrchestrator`](../calendarbot_lite/async_utils.py):

```python
from calendarbot_lite.async_utils import get_global_orchestrator

orchestrator = get_global_orchestrator()

# Timeout enforcement
result = await orchestrator.run_with_timeout(
    some_async_func(),
    timeout=30.0,
    operation_name="calendar_fetch"
)

# Concurrent execution with timeout
results = await orchestrator.gather_with_timeout(
    fetch_source1(),
    fetch_source2(),
    fetch_source3(),
    timeout=120.0
)

# Retry with backoff
result = await orchestrator.retry_async(
    flaky_async_func,
    max_retries=3,
    backoff=1.0
)
```

---

## Common Usage Patterns

### Using Shared HTTP Client

```python
from calendarbot_lite.http_client import get_shared_client

async def fetch_calendar():
    """Fetch calendar with shared HTTP client."""
    client = await get_shared_client()
    
    try:
        response = await client.get(
            "https://calendar.example.com/feed.ics",
            headers={"Authorization": "Bearer token"},
            timeout=30.0
        )
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        raise
    except asyncio.TimeoutError:
        logger.error("Request timed out")
        raise
```

**Benefits**:
- Connection pooling (reuses TCP connections)
- Automatic error tracking and health monitoring
- Browser-like headers for compatibility
- IPv4-only transport (avoids DNS issues on Pi Zero 2W)

---

### Implementing Background Fetch Coordination

```python
from calendarbot_lite.fetch_orchestrator import FetchOrchestrator

async def refresh_calendar(orchestrator: FetchOrchestrator):
    """Refresh calendar using fetch orchestrator."""
    sources_cfg = [
        {"url": "https://cal1.example.com/feed.ics", "name": "Calendar 1"},
        {"url": "https://cal2.example.com/feed.ics", "name": "Calendar 2"},
    ]
    
    # Fetch all sources with bounded concurrency
    events = await orchestrator.fetch_all_sources(
        sources_cfg=sources_cfg,
        fetch_concurrency=2,  # Max 2 concurrent fetches
        rrule_days=90,
        shared_http_client=await get_shared_client()
    )
    
    logger.info(f"Fetched {len(events)} events from {len(sources_cfg)} sources")
    return events
```

**Features**:
- Bounded concurrency (semaphore-controlled)
- Global timeout (120s for all sources)
- Continues with partial results if some sources fail
- Health tracking integration

---

### Adding Health Metrics

```python
from calendarbot_lite.health_tracker import HealthTracker

async def process_with_health_tracking(health: HealthTracker):
    """Process with health tracking."""
    # Record attempt
    health.record_refresh_attempt()
    
    try:
        result = await fetch_and_parse()
        
        # Record success
        health.record_refresh_success(event_count=len(result))
        
        return result
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise
```

**Metrics Tracked**:
- Refresh attempts and successes
- Event counts
- Background task heartbeats
- Render probe results

---

### Configuring Logging

**Environment-Based Configuration**:

```bash
# .env file
CALENDARBOT_DEBUG=true              # Enable DEBUG level
CALENDARBOT_LOG_LEVEL=DEBUG         # Override log level
```

**Code Usage**:

```python
from calendarbot_lite.lite_logging import configure_lite_logging
import logging

# Setup (called at startup)
configure_lite_logging(debug_mode=False)  # Overridden by env vars

# Use throughout application
logger = logging.getLogger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)
```

**Structured Logging with Monitoring**:

```python
from calendarbot_lite.monitoring_logging import LogEntry, MonitoringLogger

# Create logger
mon_logger = MonitoringLogger(component="server")

# Log structured event
entry = LogEntry(
    component="server",
    level="INFO",
    event="calendar.refresh",
    message="Calendar refreshed successfully",
    details={"event_count": 50, "duration_ms": 150},
    action_taken="Updated event window"
)
mon_logger.log(entry)
```

---

### Using Async Utilities

**Timeout Enforcement**:

```python
from calendarbot_lite.async_utils import get_global_orchestrator

async def fetch_with_timeout():
    """Fetch calendar with 30s timeout."""
    orchestrator = get_global_orchestrator()
    
    try:
        result = await orchestrator.run_with_timeout(
            fetch_calendar(),
            timeout=30.0,
            operation_name="calendar_fetch"
        )
        return result
    except asyncio.TimeoutError:
        logger.warning("Calendar fetch timed out after 30s")
        return None
```

**Retry with Backoff**:

```python
async def fetch_with_retry():
    """Fetch with automatic retry on failures."""
    orchestrator = get_global_orchestrator()
    
    result = await orchestrator.retry_async(
        fetch_calendar,
        max_retries=3,
        backoff=1.0
    )
    return result
```

**Concurrent Execution with Timeout**:

```python
async def fetch_all_with_timeout():
    """Fetch all sources concurrently with global timeout."""
    orchestrator = get_global_orchestrator()
    
    results = await orchestrator.gather_with_timeout(
        fetch_source1(),
        fetch_source2(),
        fetch_source3(),
        timeout=120.0,
        return_exceptions=True
    )
    
    # Filter out exceptions
    successful = [r for r in results if not isinstance(r, Exception)]
    return successful
```

---

### Testing Infrastructure Components

**Mocking HTTP Client**:

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_fetch_calendar():
    """Test calendar fetch with mocked HTTP client."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.text = "ICS content"
    mock_response.raise_for_status = AsyncMock()
    mock_client.get.return_value = mock_response
    
    with patch("calendarbot_lite.http_client.get_shared_client", return_value=mock_client):
        result = await fetch_calendar()
        assert result == "ICS content"
        mock_client.get.assert_called_once()
```

**Testing Health Tracker**:

```python
import pytest
from calendarbot_lite.health_tracker import HealthTracker

def test_health_status():
    """Test health status tracking."""
    health = HealthTracker()
    
    # Record success
    health.record_refresh_success(event_count=50)
    
    status = health.get_health_status()
    assert status.status == "ok"
    assert status.event_count == 50
    
    # Check uptime
    assert status.uptime_seconds >= 0
```

**Testing Async Orchestrator**:

```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_orchestrator_timeout():
    """Test async orchestrator timeout enforcement."""
    from calendarbot_lite.async_utils import AsyncOrchestrator
    
    orchestrator = AsyncOrchestrator(max_workers=2)
    
    async def slow_operation():
        await asyncio.sleep(10)
        return "result"
    
    with pytest.raises(asyncio.TimeoutError):
        await orchestrator.run_with_timeout(
            slow_operation(),
            timeout=1.0,
            operation_name="slow_op"
        )
```

---

## Code Examples

### Complete HTTP Client Usage

```python
from calendarbot_lite.http_client import get_shared_client, record_client_success, record_client_error
import httpx
import logging

logger = logging.getLogger(__name__)

async def fetch_ics_with_health_tracking(url: str, client_id: str = "default"):
    """Complete example of HTTP client usage with health tracking."""
    client = await get_shared_client(client_id=client_id)
    
    try:
        response = await client.get(
            url,
            headers={"User-Agent": "CalendarBot/1.0"},
            timeout=30.0
        )
        response.raise_for_status()
        
        # Record success
        record_client_success(client_id)
        
        logger.info(f"Fetched {len(response.text)} bytes from {url}")
        return response.text
        
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code}: {url}")
        record_client_error(client_id)
        raise
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching {url}")
        record_client_error(client_id)
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        record_client_error(client_id)
        raise
```

---

### Complete Fetch Orchestrator Integration

```python
from calendarbot_lite.fetch_orchestrator import FetchOrchestrator
from calendarbot_lite.health_tracker import HealthTracker
from calendarbot_lite.http_client import get_shared_client
from calendarbot_lite.event_filter import EventWindowManager
import logging

logger = logging.getLogger(__name__)

async def setup_and_run_orchestrator():
    """Complete example of fetch orchestrator setup and usage."""
    # Initialize dependencies
    health = HealthTracker()
    window_manager = EventWindowManager(event_filter, fallback_handler)
    http_client = await get_shared_client()
    
    # Create orchestrator
    orchestrator = FetchOrchestrator(
        fetch_and_parse_source=fetch_and_parse_source_func,
        window_manager=window_manager,
        health_tracker=health,
        monitoring_logger=log_monitoring_event
    )
    
    # Configure sources
    sources_cfg = [
        {"url": "https://cal1.example.com/feed.ics", "name": "Work"},
        {"url": "https://cal2.example.com/feed.ics", "name": "Personal"},
    ]
    
    # Fetch all sources
    try:
        events = await orchestrator.fetch_all_sources(
            sources_cfg=sources_cfg,
            fetch_concurrency=2,
            rrule_days=90,
            shared_http_client=http_client
        )
        
        logger.info(f"Fetched {len(events)} events from {len(sources_cfg)} sources")
        return events
        
    except Exception as e:
        logger.error(f"Orchestration failed: {e}", exc_info=True)
        raise
```

---

### Complete Health Tracking Example

```python
from calendarbot_lite.health_tracker import HealthTracker, HealthStatus
import logging
import time

logger = logging.getLogger(__name__)

async def calendar_refresh_with_health(health: HealthTracker):
    """Complete example of health tracking during refresh."""
    # Record attempt
    health.record_refresh_attempt()
    
    start = time.time()
    try:
        # Fetch and parse
        events = await fetch_and_parse_calendar()
        duration = time.time() - start
        
        # Record success
        health.record_refresh_success(event_count=len(events))
        
        logger.info(
            f"Refresh succeeded: {len(events)} events in {duration:.2f}s"
        )
        
        # Check overall health
        status = health.get_health_status()
        if status.status != "ok":
            logger.warning(f"System health degraded: {status.status}")
        
        return events
        
    except Exception as e:
        duration = time.time() - start
        logger.error(
            f"Refresh failed after {duration:.2f}s: {e}",
            exc_info=True
        )
        
        # Health automatically marked degraded due to failed refresh
        status = health.get_health_status()
        logger.error(f"Health status: {status.status}")
        
        raise
```

---

### Complete Async Orchestrator Examples

```python
from calendarbot_lite.async_utils import AsyncOrchestrator, get_global_orchestrator
import asyncio
import logging

logger = logging.getLogger(__name__)

async def comprehensive_async_patterns():
    """Complete examples of async orchestrator patterns."""
    orchestrator = get_global_orchestrator()
    
    # 1. Timeout enforcement
    try:
        result = await orchestrator.run_with_timeout(
            slow_async_operation(),
            timeout=10.0,
            operation_name="slow_operation"
        )
        logger.info(f"Operation completed: {result}")
    except asyncio.TimeoutError:
        logger.warning("Operation timed out after 10s")
    
    # 2. Retry with exponential backoff
    try:
        result = await orchestrator.retry_async(
            fetch_external_api,
            max_retries=3,
            backoff=1.0
        )
        logger.info(f"API call succeeded: {result}")
    except Exception as e:
        logger.error(f"API call failed after retries: {e}")
    
    # 3. Concurrent execution with timeout
    try:
        results = await orchestrator.gather_with_timeout(
            fetch_source1(),
            fetch_source2(),
            fetch_source3(),
            timeout=120.0,
            return_exceptions=True
        )
        
        # Filter successful results
        successful = [r for r in results if not isinstance(r, Exception)]
        logger.info(f"Completed {len(successful)}/{len(results)} operations")
        
    except asyncio.TimeoutError:
        logger.error("Concurrent operations timed out")
    
    # 4. Run blocking function in executor
    result = await orchestrator.run_in_executor(
        blocking_function,
        arg1,
        arg2
    )
    logger.info(f"Blocking function result: {result}")
    
    return results
```

---

## Related Documentation

- **[01-server-http-routing.md](01-server-http-routing.md)** - Server integration, lifecycle management, background tasks
- **[02-alexa-integration.md](02-alexa-integration.md)** - Alexa request handling, health endpoints
- **[03-calendar-processing.md](03-calendar-processing.md)** - Calendar fetching, parsing, event processing
- **[AGENTS.md](../../AGENTS.md)** - Development workflows, testing, deployment
- **[tmp/component_analysis.md](../../tmp/component_analysis.md)** - Architectural analysis and component boundaries

---

## Testing Infrastructure

### Test Locations

- **Unit Tests**: 
  - [`tests/lite/unit/test_async_utils.py`](../../tests/lite/unit/test_async_utils.py)
  - [`tests/lite/unit/test_http_client.py`](../../tests/lite/unit/test_http_client.py)
  - [`tests/lite/unit/test_health_tracker_module.py`](../../tests/lite/unit/test_health_tracker_module.py)
  - [`tests/lite/unit/test_fetch_orchestrator.py`](../../tests/lite/unit/test_fetch_orchestrator.py)
  - [`tests/lite/unit/test_config_manager_module.py`](../../tests/lite/unit/test_config_manager_module.py)
  - [`tests/lite/unit/test_dependencies.py`](../../tests/lite/unit/test_dependencies.py)
  - [`tests/lite/unit/test_debug_helpers.py`](../../tests/lite/unit/test_debug_helpers.py)

- **Integration Tests**: 
  - [`tests/lite/integration/test_concurrency_system.py`](../../tests/lite/integration/test_concurrency_system.py)
  - [`tests/lite/integration/test_health_check.py`](../../tests/lite/integration/test_health_check.py)

### Running Infrastructure Tests

```bash
# All infrastructure tests
pytest tests/lite/unit/test_async_utils.py \
       tests/lite/unit/test_http_client.py \
       tests/lite/unit/test_health_tracker_module.py \
       tests/lite/unit/test_fetch_orchestrator.py -v

# Fast unit tests only
pytest tests/lite/unit/ -m "fast"

# Integration tests with health monitoring
pytest tests/lite/integration/test_health_check.py -v
```

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-03  
**Part of**: calendarbot_lite component documentation series  
**Related Components**: Server & HTTP (01), Alexa Integration (02), Calendar Processing (03)