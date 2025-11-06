# CalendarBot Lite Documentation Index

**Complete reference documentation for the calendarbot_lite Alexa skill backend.**

This documentation set is designed for LLM agent consumption, providing comprehensive component references, architecture patterns, and implementation details.

---

## 📚 Documentation Structure

This documentation is organized into five component-focused documents:

| Document | Focus | Lines | When to Use |
|----------|-------|-------|-------------|
| [01-server-http-routing.md](01-server-http-routing.md) | Server & HTTP Layer | 651 | Server lifecycle, HTTP routes, background tasks |
| [02-alexa-integration.md](02-alexa-integration.md) | Alexa Integration | 1111 | Alexa intents, handlers, SSML, caching |
| [03-calendar-processing.md](03-calendar-processing.md) | Calendar Processing | 891 | ICS parsing, RRULE expansion, event filtering |
| [04-infrastructure.md](04-infrastructure.md) | Infrastructure | 918 | Async patterns, HTTP client, health monitoring |
| [05-configuration-dependencies.md](05-configuration-dependencies.md) | Configuration & DI | - | Environment config, dependency injection |

**Total Coverage**: 3571+ lines of component documentation

---

## 🚀 Quick Start Guide

### For New Developers

**Recommended reading order:**

1. **Start Here**: [Configuration & Dependencies](05-configuration-dependencies.md) - Understand environment setup and DI patterns
2. **Server Basics**: [Server & HTTP Routing](01-server-http-routing.md) - Learn server lifecycle and HTTP endpoints
3. **Core Business Logic**: [Alexa Integration](02-alexa-integration.md) - Master intent handling and response generation
4. **Data Processing**: [Calendar Processing](03-calendar-processing.md) - Understand ICS parsing and recurring events
5. **Supporting Systems**: [Infrastructure](04-infrastructure.md) - Learn async patterns and system utilities

### For Specific Tasks

| Task | Consult |
|------|---------|
| Adding Alexa intent | [02-alexa-integration.md](02-alexa-integration.md) §2 Handler Registration |
| Fixing RRULE issues | [03-calendar-processing.md](03-calendar-processing.md) §2 RRULE Expansion |
| Server performance | [01-server-http-routing.md](01-server-http-routing.md) §4 Background Tasks |
| HTTP endpoint issues | [01-server-http-routing.md](01-server-http-routing.md) §2-3 Routes |
| Async patterns | [04-infrastructure.md](04-infrastructure.md) §1 Async Utilities |
| Configuration changes | [05-configuration-dependencies.md](05-configuration-dependencies.md) §1 Config Manager |
| Health monitoring | [04-infrastructure.md](04-infrastructure.md) §4 Health Tracking |
| Timezone issues | [03-calendar-processing.md](03-calendar-processing.md) §5 Timezone Utilities |

---

## 🏗️ Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CALENDARBOT LITE                          │
│                  Alexa Skill Backend                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ SERVER & HTTP LAYER (01-server-http-routing.md)             │
├─────────────────────────────────────────────────────────────┤
│ • aiohttp Web Server (server.py)                            │
│ • HTTP Route Handlers (routes/*.py)                         │
│ • What's Next Kiosk Interface (whatsnext.html/css/js)       │
│ • Background Task Management                                │
│ • Lifecycle Management (startup/shutdown)                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ ALEXA INTEGRATION LAYER (02-alexa-integration.md)           │
├─────────────────────────────────────────────────────────────┤
│ • Intent Handler Pipeline (alexa_handlers.py)               │
│ • Request Preprocessing (alexa_precompute_stages.py)        │
│ • Response Caching (alexa_response_cache.py)                │
│ • SSML Generation (alexa_ssml.py)                           │
│ • Handler Registry (alexa_registry.py)                      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ CALENDAR PROCESSING LAYER (03-calendar-processing.md)       │
├─────────────────────────────────────────────────────────────┤
│ • ICS Parsing (lite_event_parser.py)                        │
│ • RRULE Expansion (lite_rrule_expander.py)                  │
│ • Event Filtering (event_filter.py)                         │
│ • Event Prioritization (event_prioritizer.py)               │
│ • Timezone Handling (timezone_utils.py)                     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE LAYER (04-infrastructure.md)                 │
├─────────────────────────────────────────────────────────────┤
│ • Async Utilities (async_utils.py)                          │
│ • HTTP Client (http_client.py)                              │
│ • Fetch Orchestration (fetch_orchestrator.py)               │
│ • Health Tracking (health_tracker.py)                       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ CONFIGURATION & DI (05-configuration-dependencies.md)       │
├─────────────────────────────────────────────────────────────┤
│ • Environment Config (config_manager.py)                    │
│ • Dependency Injection (dependencies.py)                    │
│ • Service Lifecycle Management                              │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow Overview

**Alexa Voice Flow:**
```
User Voice → Alexa Device → Alexa Service → POST /alexa
                                               │
                                               ▼
                                    Request Preprocessing
                                    (Context Enrichment)
                                               │
                                               ▼
                                    Intent Handler Lookup
                                    (Registry Pattern)
                                               │
                                               ▼
                                    Calendar Data Fetch
                                    (Background Refresh)
                                               │
                                               ▼
                                    Event Processing
                                    (Filter, Prioritize)
                                               │
                                               ▼
                                    Response Generation
                                    (SSML + Caching)
                                               │
                                               ▼
                                    JSON Response → Alexa
```

**Kiosk Display Flow:**
```
Browser/Kiosk → GET / → whatsnext.html
                          │
                          ▼
                    JavaScript loads whatsnext.js
                          │
                          ▼
                    GET /api/whats-next
                          │
                          ▼
                    Calendar Data Fetch
                    (Background Refresh)
                          │
                          ▼
                    Event Processing
                    (Filter, Prioritize)
                          │
                          ▼
                    JSON Response → Browser
                          │
                          ▼
                    Render Calendar Display
```

### Component Dependencies

```
server.py
  ├─> routes/alexa_routes.py ──> alexa_handlers.py
  │                                  ├─> alexa_registry.py
  │                                  ├─> alexa_precompute_stages.py
  │                                  ├─> alexa_response_cache.py
  │                                  ├─> alexa_presentation.py
  │                                  └─> alexa_ssml.py
  │
  ├─> routes/api_routes.py ──> event_filter.py
  │                        └─> event_prioritizer.py
  │
  └─> Background Tasks ──> fetch_orchestrator.py
                             ├─> http_client.py
                             ├─> lite_event_parser.py
                             └─> lite_rrule_expander.py

config_manager.py ──> (Used by all modules)
dependencies.py ──> (Provides DI container)
health_tracker.py ──> (Monitors all components)
```

---

## 🔍 Component Quick Reference

### 1. Server & HTTP Layer

**Key Modules:**
- [`server.py`](01-server-http-routing.md#1-serverpy) - Web server and lifecycle
- [`routes/alexa_routes.py`](01-server-http-routing.md#2-routesalexa_routespy) - Alexa webhook
- [`routes/api_routes.py`](01-server-http-routing.md#3-routesapi_routespy) - REST API
- [`routes/static_routes.py`](01-server-http-routing.md#4-routesstatic_routespy) - What's Next kiosk interface

**Kiosk Interface:**
- [`whatsnext.html`](../../calendarbot_lite/whatsnext.html) - Kiosk display structure
- [`whatsnext.css`](../../calendarbot_lite/whatsnext.css) - Kiosk display styling
- [`whatsnext.js`](../../calendarbot_lite/whatsnext.js) - Client-side logic and API integration

**Key Patterns:**
- Graceful startup/shutdown with `start_background_tasks()` / `cleanup_background_tasks()`
- Background refresh using `run_forever_async()`
- Health check endpoints at `/health` and `/api/health`

**See**: [01-server-http-routing.md](01-server-http-routing.md)

### 2. Alexa Integration

**Key Modules:**
- [`alexa_handlers.py`](02-alexa-integration.md#1-alexa_handlerspy) - Intent processing (51KB)
- [`alexa_registry.py`](02-alexa-integration.md#2-alexa_registrypy) - Handler registration
- [`alexa_precompute_stages.py`](02-alexa-integration.md#3-alexa_precompute_stagespy) - Request preprocessing
- [`alexa_response_cache.py`](02-alexa-integration.md#4-alexa_response_cachepy) - Response caching
- [`alexa_ssml.py`](02-alexa-integration.md#5-alexa_ssmlpy) - Speech synthesis (30KB)

**Key Patterns:**
- Registry pattern for handler registration with `@registry.register()`
- Multi-stage preprocessing pipeline (context enrichment)
- TTL-based response caching for performance
- SSML templates with pause/emphasis/prosody

**See**: [02-alexa-integration.md](02-alexa-integration.md)

### 3. Calendar Processing

**Key Modules:**
- [`lite_event_parser.py`](03-calendar-processing.md#1-lite_event_parserpy) - ICS parsing
- [`lite_rrule_expander.py`](03-calendar-processing.md#2-lite_rrule_expanderpy) - Recurring expansion
- [`event_filter.py`](03-calendar-processing.md#3-event_filterpy) - Event filtering
- [`event_prioritizer.py`](03-calendar-processing.md#4-event_prioritizerpy) - Event ranking
- [`timezone_utils.py`](03-calendar-processing.md#5-timezone_utilspy) - Timezone conversion

**Key Patterns:**
- RFC 5545 compliant ICS parsing with icalendar library
- Bounded RRULE expansion with duration limits
- Multi-field event filtering (time ranges, keywords, attendees)
- Priority scoring with configurable weights

**See**: [03-calendar-processing.md](03-calendar-processing.md)

### 4. Infrastructure

**Key Modules:**
- [`async_utils.py`](04-infrastructure.md#1-async_utilspy) - Async helpers (21KB)
- [`http_client.py`](04-infrastructure.md#2-http_clientpy) - HTTP client (12KB)
- [`fetch_orchestrator.py`](04-infrastructure.md#3-fetch_orchestratorpy) - Fetch coordination (10KB)
- [`health_tracker.py`](04-infrastructure.md#4-health_trackerpy) - Health monitoring (8KB)

**Key Patterns:**
- `run_forever_async()` for background task loops
- Exponential backoff retry with jitter
- Fetch orchestration with error handling
- Health metrics with success/failure tracking

**See**: [04-infrastructure.md](04-infrastructure.md)

### 5. Configuration & Dependencies

**Key Modules:**
- [`config_manager.py`](05-configuration-dependencies.md#1-config_managerpy) - Environment config (5KB)
- [`dependencies.py`](05-configuration-dependencies.md#2-dependenciespy) - Dependency injection

**Key Patterns:**
- Environment-based configuration with validation
- Dependency injection container pattern
- Service lifecycle management
- Testable configuration with overrides

**See**: [05-configuration-dependencies.md](05-configuration-dependencies.md)

---

## 🧪 Testing Strategy

### Test Organization

```
tests/lite/
├── unit/              # Fast unit tests (< 1s each)
│   ├── test_alexa_handlers.py
│   ├── test_lite_event_parser.py
│   ├── test_lite_rrule_expander.py
│   └── ...
├── integration/       # Cross-component tests
│   ├── test_integration_comprehensive.py
│   ├── test_recurring_scenarios.py
│   └── ...
├── smoke/            # Quick startup validation
│   └── test_lite_smoke_boot.py
└── performance/      # Performance benchmarks
    └── test_rrule_streaming_optimization.py
```

### Test Markers

| Marker | Purpose | Usage |
|--------|---------|-------|
| `unit` | Fast unit tests | `pytest -m "unit"` |
| `integration` | Cross-component tests | `pytest -m "integration"` |
| `smoke` | Quick startup checks | `pytest -m "smoke"` |
| `slow` | Tests > 5 seconds | `pytest -m "not slow"` |
| `fast` | Tests < 1 second | `pytest -m "fast"` |
| `network` | Requires network | `pytest -m "not network"` |

### Running Tests

```bash
# All tests with coverage
./run_lite_tests.sh --coverage

# Fast tests only
pytest tests/lite/ -m "fast"

# Skip slow tests
pytest tests/lite/ -m "not slow"

# Specific component
pytest tests/lite/unit/test_alexa_handlers.py -v
```

**See**: Each component document has a dedicated testing section

---

## ⚙️ Configuration Quick Reference

### Required Environment Variables

```bash
# ICS Calendar Feed (REQUIRED)
CALENDARBOT_ICS_URL=https://example.com/calendar.ics

# Server Configuration
CALENDARBOT_WEB_HOST=0.0.0.0       # Default: 0.0.0.0
CALENDARBOT_WEB_PORT=8080          # Default: 8080
CALENDARBOT_REFRESH_INTERVAL=300   # Default: 300 seconds

# Alexa Integration
CALENDARBOT_ALEXA_BEARER_TOKEN=your_token_here

# Logging
CALENDARBOT_DEBUG=true             # Enable debug logging
CALENDARBOT_LOG_LEVEL=DEBUG        # Override log level
```

**See**: [05-configuration-dependencies.md](05-configuration-dependencies.md) for complete reference

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | What's Next kiosk display interface |
| `/whatsnext.css` | GET | Kiosk interface stylesheet |
| `/whatsnext.js` | GET | Kiosk interface JavaScript |
| `/health` | GET | Basic health check |
| `/api/health` | GET | Detailed health status |
| `/api/status` | GET | Server status |
| `/api/events` | GET | Calendar events |
| `/api/whats-next` | GET | Next upcoming events (used by kiosk) |
| `/api/refresh` | POST | Force calendar refresh |
| `/alexa` | POST | Alexa skill webhook |

**See**: [01-server-http-routing.md](01-server-http-routing.md) for endpoint details

---

## 🔗 Cross-Reference Index

### Key Interfaces & Types

| Interface | Defined In | Used In |
|-----------|-----------|---------|
| `AlexaRequest` | [alexa_types.py](02-alexa-integration.md#7-alexa_typespy) | All Alexa handlers |
| `AlexaResponse` | [alexa_types.py](02-alexa-integration.md#7-alexa_typespy) | All Alexa handlers |
| `EventFilterCriteria` | [event_filter.py](03-calendar-processing.md#3-event_filterpy) | Event filtering |
| `PriorityWeights` | [event_prioritizer.py](03-calendar-processing.md#4-event_prioritizerpy) | Event ranking |
| `HealthMetrics` | [health_tracker.py](04-infrastructure.md#4-health_trackerpy) | Health monitoring |
| `ConfigManager` | [config_manager.py](05-configuration-dependencies.md#1-config_managerpy) | All modules |

### Integration Points

| Integration | Components | Documentation |
|------------|-----------|---------------|
| Alexa → Calendar | `alexa_handlers.py` ↔ `lite_event_parser.py` | [02](02-alexa-integration.md) + [03](03-calendar-processing.md) |
| Server → Alexa | `routes/alexa_routes.py` ↔ `alexa_handlers.py` | [01](01-server-http-routing.md) + [02](02-alexa-integration.md) |
| Background Tasks → Fetch | `server.py` ↔ `fetch_orchestrator.py` | [01](01-server-http-routing.md) + [04](04-infrastructure.md) |
| Config → All | `config_manager.py` → Everything | [05](05-configuration-dependencies.md) |

### Common Patterns

| Pattern | Example Module | Documentation |
|---------|----------------|---------------|
| Registry Pattern | `alexa_registry.py` | [02-alexa-integration.md](02-alexa-integration.md#2-alexa_registrypy) |
| Dependency Injection | `dependencies.py` | [05-configuration-dependencies.md](05-configuration-dependencies.md#2-dependenciespy) |
| Async Context Managers | `async_utils.py` | [04-infrastructure.md](04-infrastructure.md#1-async_utilspy) |
| Exponential Backoff | `http_client.py` | [04-infrastructure.md](04-infrastructure.md#2-http_clientpy) |
| TTL Caching | `alexa_response_cache.py` | [02-alexa-integration.md](02-alexa-integration.md#4-alexa_response_cachepy) |

---

## 📖 Usage Examples

### Adding a New Alexa Intent

1. **Define Handler**: See [02-alexa-integration.md §2](02-alexa-integration.md#2-alexa_registrypy)
2. **Register Intent**: Use `@registry.register()`
3. **Generate SSML**: See [02-alexa-integration.md §5](02-alexa-integration.md#5-alexa_ssmlpy)
4. **Test Handler**: See [02-alexa-integration.md §9](02-alexa-integration.md#9-testing-strategy)

### Implementing Custom Event Filter

1. **Filter Criteria**: See [03-calendar-processing.md §3](03-calendar-processing.md#3-event_filterpy)
2. **Apply Filter**: Use `EventFilter.filter_events()`
3. **Test Filter**: Unit tests with mock events

### Adding Background Task

1. **Task Definition**: See [01-server-http-routing.md §4](01-server-http-routing.md#4-background-tasks)
2. **Use `run_forever_async()`**: See [04-infrastructure.md §1](04-infrastructure.md#1-async_utilspy)
3. **Register Task**: Add to `start_background_tasks()`
4. **Cleanup**: Add to `cleanup_background_tasks()`

---

## 🎯 Key Concepts

### Async-First Architecture
- All I/O operations are async (aiohttp, aiosqlite)
- Background tasks use `run_forever_async()` pattern
- Tests configured with `asyncio_mode = auto`

**See**: [04-infrastructure.md §1](04-infrastructure.md#1-async_utilspy)

### Event Expansion & Filtering
- RFC 5545 compliant RRULE expansion
- Bounded expansion with duration limits
- Multi-stage filtering (time, keywords, attendees)

**See**: [03-calendar-processing.md](03-calendar-processing.md)

### Response Caching & SSML
- TTL-based caching for performance
- Context-aware cache invalidation
- SSML templates with prosody control

**See**: [02-alexa-integration.md §4-5](02-alexa-integration.md#4-alexa_response_cachepy)

### Health Monitoring
- Success/failure rate tracking
- Last fetch timestamp monitoring
- Degraded state detection

**See**: [04-infrastructure.md §4](04-infrastructure.md#4-health_trackerpy)

---

## 🚨 Common Issues & Solutions

| Issue | Where to Look | Documentation |
|-------|---------------|---------------|
| Alexa not responding | Handler registration | [02-alexa-integration.md §2](02-alexa-integration.md#2-alexa_registrypy) |
| Missing recurring events | RRULE expansion | [03-calendar-processing.md §2](03-calendar-processing.md#2-lite_rrule_expanderpy) |
| Server won't start | Environment config | [05-configuration-dependencies.md §1](05-configuration-dependencies.md#1-config_managerpy) |
| High memory usage | Background task leaks | [01-server-http-routing.md §4](01-server-http-routing.md#4-background-tasks) |
| Timezone wrong | Timezone conversion | [03-calendar-processing.md §5](03-calendar-processing.md#5-timezone_utilspy) |
| API timeout | HTTP client retry | [04-infrastructure.md §2](04-infrastructure.md#2-http_clientpy) |

---

## 📝 Documentation Maintenance

### When to Update

- **Adding New Module**: Add section to appropriate component doc
- **Changing API**: Update interface definitions and examples
- **New Pattern**: Document in relevant component + this index
- **Breaking Change**: Update cross-references and examples

### Documentation Standards

- **Target Audience**: LLM agents + developers
- **Language**: Technical, direct, minimal jargon
- **Structure**: Scannable (tables, lists, headers)
- **Code Examples**: Complete, runnable snippets
- **Links**: Use relative markdown links

---

## 🔄 Related Documentation

### Project-Wide Documentation

- **[AGENTS.md](../../AGENTS.md)** - Complete agent development guide
- **[CLAUDE.md](../../CLAUDE.md)** - Quick reference for Claude agents
- **[README.md](../../README.md)** - Project overview
- **[.env.example](../../.env.example)** - Environment configuration template

### Deployment & Operations

- **[docs/ALEXA_DEPLOYMENT_GUIDE.md](../ALEXA_DEPLOYMENT_GUIDE.md)** - Alexa skill deployment
- **[docs/DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md)** - Server deployment
- **[docs/PI_ZERO_2_MONITORING_GUIDE.md](../PI_ZERO_2_MONITORING_GUIDE.md)** - Hardware monitoring

### Architecture & Design

- **[docs/ARCHITECTURE.md](../ARCHITECTURE.md)** - High-level architecture
- **[02-alexa-integration.md](02-alexa-integration.md)** - Alexa deployment, security, and authentication
- **[03-calendar-processing.md](03-calendar-processing.md)** - Pipeline architecture and custom stages
- **[tmp/component_analysis.md](../../tmp/component_analysis.md)** - Component analysis

---

## 📊 Documentation Statistics

- **Total Documents**: 5 component docs + 1 index
- **Total Lines**: 3571+ lines (excluding this index)
- **Components Covered**: 25+ modules
- **Code Examples**: 100+ snippets
- **Cross-References**: 200+ links

---

## 🏁 Quick Navigation Summary

| Need | Go To |
|------|-------|
| **Getting Started** | [Configuration & Dependencies](05-configuration-dependencies.md) |
| **Server Issues** | [Server & HTTP Routing](01-server-http-routing.md) |
| **Alexa Problems** | [Alexa Integration](02-alexa-integration.md) |
| **Calendar Bugs** | [Calendar Processing](03-calendar-processing.md) |
| **Infrastructure** | [Infrastructure](04-infrastructure.md) |
| **Quick Reference** | This document (you are here) |

---

**Last Updated**: 2025-11-03
**Documentation Version**: 1.0
**Target**: calendarbot_lite/ (active project)

**For additional help**: See [AGENTS.md](../../AGENTS.md) or project README files