# CalendarBot Architecture

## Overview

CalendarBot is a Python-based calendar display application that fetches ICS calendar feeds and presents them through multiple interfaces (web, e-paper display).

## Core Components

### 1. ICS Processing (`calendarbot/ics/`)
- **ICSFetcher**: HTTP client for fetching calendar feeds
- **ICSParser**: RFC 5545 compliant ICS content parsing
- **Authentication**: Basic auth, bearer tokens, or public access

### 2. Cache Management (`calendarbot/cache/`)
- **SQLite Database**: Local event storage with WAL mode
- **TTL Management**: Configurable cache expiration (default: 1 hour)
- **Offline Support**: Serves cached data when network unavailable

### 3. Display System (`calendarbot/display/`)
- **HTML Renderer**: Web interface with multiple layouts
- **RPi Renderer**: E-ink optimized display for Raspberry Pi

### 4. Web Interface (`calendarbot/web/`)
- **Layout System**: Dynamic layout discovery (4x8, 3x4, whats-next-view)
- **Auto-refresh**: Real-time calendar updates
- **Mobile Support**: Responsive design

### 5. Configuration (`calendarbot/config/`)
- **Pydantic Settings**: Type-safe configuration with YAML support
- **Environment Variables**: `CALENDARBOT_*` prefix support
- **Setup Wizard**: Interactive configuration tool

## Architecture Patterns

### Async-First Design
- All I/O operations use `async/await`
- Non-blocking HTTP requests and database operations
- Concurrent source fetching for multiple calendars

### Manager→Handler→Protocol Pattern
```
SourceManager → ICSFetcher → ICSSourceProtocol
DisplayManager → HTMLRenderer → RendererProtocol
CacheManager → DatabaseHandler → CacheProtocol
```

### Configuration Hierarchy
1. Default values (built into Pydantic models)
2. YAML configuration files
3. Environment variables
4. Command line arguments

## Data Flow

1. **Scheduler** triggers refresh cycle
2. **SourceManager** fetches ICS content via **ICSFetcher**
3. **ICSParser** parses and validates events
4. **CacheManager** stores events in SQLite database
5. **DisplayManager** retrieves events and renders via chosen renderer
6. **WebServer** serves HTML to browser (web mode)

## Operational Modes

- **Web**: Browser-based interface with layout system
- **E-Paper**: E-ink optimized rendering for Raspberry Pi
- **Daemon**: Background service operation

## Calendar Compatibility

Supports any RFC 5545 compliant calendar system:
- Microsoft Outlook/Office 365
- Google Calendar
- Apple iCloud Calendar
- CalDAV servers (Nextcloud, Radicale, SOGo)

## Performance Characteristics

- **Memory**: <50MB typical usage
- **Storage**: <5MB cache database
- **Network**: Efficient HTTP caching with conditional requests
- **Async Benefits**: Non-blocking I/O, responsive UI, concurrent operations

## Security

- **Local-First**: All processing happens locally
- **HTTPS Required**: SSL/TLS for calendar feed access
- **Credential Protection**: Secure storage in configuration
- **No Cloud Dependencies**: Direct ICS feed access only

## Extension Points

### Custom Renderers
```python
class CustomRenderer(BaseRenderer):
    async def render_events(self, events: List[CalendarEvent]) -> str:
        # Custom rendering logic
        pass
```

### Custom Layouts
- Add layout configuration in `calendarbot/web/static/layouts/`
- Define `layout.json` with capabilities and resources
- Automatic discovery and fallback chain support

### Custom Calendar Sources
```python
class CustomSource(BaseSource):
    async def fetch_events(self) -> List[CalendarEvent]:
        # Custom source implementation
        pass
```

## Development

### Key Technologies
- **Python 3.9+** with modern async patterns
- **icalendar**: RFC 5545 compliant parsing
- **httpx**: Async HTTP client
- **aiosqlite**: Async SQLite with WAL mode
- **pydantic**: Type-safe configuration and validation

### Testing
- **Unit Tests**: Component-level testing with pytest
- **Integration Tests**: Cross-component interaction testing
- **Browser Tests**: Web interface validation
- **Validation Framework**: Comprehensive system health checks

### File Structure
```
calendarbot/
├── __main__.py          # Module execution
├── main.py              # Core application logic
├── setup_wizard.py      # Interactive setup
├── ics/                 # ICS processing
├── cache/               # Event caching
├── display/             # Rendering system
├── web/                 # Web interface
├── config/              # Configuration management
└── cli/                 # Command-line interface
```

This architecture provides a clean, modular design with clear separation of concerns and extensive customization options while maintaining simplicity for end users.