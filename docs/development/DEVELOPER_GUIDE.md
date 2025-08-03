# CalendarBot Developer

This guide serves as a comprehensive reference for CalendarBot's architectural design, development practices, and extension mechanisms.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Code Organization Principles](#code-organization-principles)
- [Development Practices](#development-practices)
- [Key Design Patterns](#key-design-patterns)
- [Developer Workflows](#developer-workflows)
- [Extension Points](#extension-points)
- [Conclusion](#conclusion)

## Architecture Overview

### High-Level Component Diagram

```mermaid
graph TD
    A[Main Application] --> B[Source Manager]
    A --> C[Cache Manager]
    A --> D[Display Manager]
    B --> E[ICS Processing]
    D --> F[UI Controller]
    D --> G[Web Interface]
    G --> H[Static Assets]
```

### Module Organization

- **Source Management:** [`calendarbot/sources/`](calendarbot/sources/)
- **ICS Processing:** [`calendarbot/ics/`](calendarbot/ics/)
- **Cache Management:** [`calendarbot/cache/`](calendarbot/cache/)
- **Display Management:** [`calendarbot/display/`](calendarbot/display/)
- **User Interface:** [`calendarbot/ui/`](calendarbot/ui/)
- **Web Interface:** [`calendarbot/web/`](calendarbot/web/)
- **Utilities:** [`calendarbot/utils/`](calendarbot/utils/)
- **Validation Framework:** [`calendarbot/validation/`](calendarbot/validation/)
- **Configuration System:** [`config/`](config/)

### Data Flow Patterns

- **Event Processing:** Asynchronous pipeline from source fetchers through parsers and cache
- **Configuration Loading:** Multi-layer approach with Pydantic validation

## Code Organization Principles

### Separation of Concerns

- **Modular Design:** Each module handles a specific responsibility
- **Async Patterns:** Use of async/await for non-blocking operations
- **Configuration-Driven:** System behavior controlled externally through YAML and environment variables

### Dependency Injection

- **Pydantic Models:** For configuration settings
- **Abstract Base Classes:** For display and source extensions

### Configuration Management

- **Inheritance Model:** Defaults, YAML, environment variables, CLI overrides

## Development Practices

### Coding Standards

- **PEP8 Compliance:** Enforced by Black formatting
- **Static Typing:** Types hints required for public APIs
- **Error Handling:** Comprehensive logging and graceful degradation

### Testing Strategies

- **Unit Tests:** For isolated components (e.g., [`test_cache_manager.py`](tests/unit/test_cache_manager.py))
- **Integration Tests:** Full pipeline validation (e.g., [`test_full_pipeline.py`](tests/integration/test_full_pipeline.py))
- **UI Tests:** Browser-based testing for visual validation and interaction testing
- **End-to-End Tests:** User flow scenarios (planned in v2.0)

### Error Handling Patterns

- **Exponential Backoff:** For network retries [`ics_source.py`](calendarbot/ics/ics_source.py)
- **Fallback Strategies:** Cache usage on network failures

### Logging Conventions

- **Cross-Context Logging:** Same logger instance throughout modules
- **Colorized Output:** For development/interactive modes

### Performance Considerations

- **Async HTTP Client:** [`httpx`](https://pypi.org/project/httpx/) with caching
- **Efficient Data Structures:** SQLite for fast access patterns

## Key Design Patterns

### Renderer Protocol Pattern

- **Protocol Definition:** [`renderer_protocol.py`](calendarbot/display/renderer_protocol.py)
- **Renderer Implementations:** HTML, console, RPI-HTML

### Source Manager Pattern

- **Multi-Source Coordination:** [`source_manager.py`](calendarbot/sources/manager.py)
- **Per-Source Configuration:** Unique settings per feed type

### Configuration Wizard Pattern

- **Interactive Setup:** [`setup_wizard.py`](calendarbot/setup_wizard.py)
- **Environment Checking:** Automatic configuration file generation

### Web Interface Architecture

- **Server Framework:** [`server.py`](calendarbot/web/server.py)
- **Route Management:** REST API endpoints with async handlers


## Developer Workflows

### Setting Up Environment

```bash
git clone https://example.com/calendarbot.git
cd calendarbot
python scripts/dev_setup.py
```

### Adding New Features

1. Fork repository and clone to local
2. Create branch: `git checkout -b feature/new-feature`
3. Implement feature following coding standards
4. Add tests covering new functionality
5. Update documentation in `DEVELOPER_GUIDE.md`
6. Submit PR with clear explanations


### Extending Display Renderers

To create a new display renderer, implement the `RendererProtocol` interface:

```python
from calendarbot.display.renderer_protocol import RendererProtocol
from ..cache.models import CachedEvent
from typing import List, Optional, Dict, Any

class CustomRenderer(RendererProtocol):
    async def render_events(self, events: List[CachedEvent], status_info: Optional[Dict[str, Any]] = None) -> str:
        """Render events in a custom format."""
        return self.custom_render_logic(events, status_info)

    def render_error(self, error_message: str, cached_events: Optional[List[CachedEvent]] = None) -> str:
        """Render an error message."""
        return f"Error: {error_message}"

    def render_authentication_prompt(self, verification_uri: str, user_code: str) -> str:
        """Render authentication prompt."""
        return f"Authenticate at: {verification_uri}, Code: {user_code}"

    def custom_render_logic(self, events: List[CachedEvent], status_info: Optional[Dict[str, Any]]) -> str:
        """Custom rendering logic."""
        rendered_events = [f"\nEvent: {event.summary}" for event in events]
        return "".join(rendered_events)
```

### Adding a New Calendar Source

To add support for a new calendar source, extend the `ICSSourceHandler`:

```python
from calendarbot.sources.ics_source import ICSSourceHandler
from calendarbot.sources.models import SourceConfig
from typing import Optional

class GoogleCalendarSourceHandler(ICSSourceHandler):
    def __init__(
        self,
        config: SourceConfig,
        settings: Any,
        additional_param: Optional[str] = None,
    ):
        super().__init__(config, settings)
        self.additional_param = additional_param

    async def fetch_events(self, use_cache: bool = True) -> list[Event]:
        """Fetch events from Google Calendar source."""
        if not self.config.enabled:
            raise ValueError(f"Source {self.config.name} is disabled")

        return await super().fetch_events(use_cache)
```


## Extension Points

### Example: Adding a New CLI Command

To add a new CLI command, extend the `Command` class:

```python
from typing import List, Optional, Literal, Union
from .base_cli_command import BaseCLICommand

class MyNewCommand(BaseCLICommand):
    help: str = "Run a custom command"
    args: List[str] = ["--example-arg"]
    action: Literal["store", "store_true"] = "store"
    dest: str = "example_flag"
    default: Union[str, bool, None] = None
    required: bool = True

    def execute(self, argv: List[str]) -> None:
        """Execute the command."""
        print("Hello from MyNewCommand!")
```

### Example: Extending the Web Interface

To extend the web interface, add new routes to the existing `WebServer`:

```python
from calendarbot.web.server import WebServer

class MyExtendedWebServer(WebServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_custom_routes()

    def add_custom_routes(self):
        @self.app.route("/custom-route", methods=["GET", "POST"])
        def custom_handler():
            """Custom API endpoint."""
            return {"data": "Hello from custom endpoint"}
```


### Case Study: whats-next-view Layout Development

The **whats-next-view** layout serves as a comprehensive example of creating a specialized layout that demonstrates CalendarBot's architectural patterns and extension capabilities.

#### Development Overview

**Purpose**: Create a countdown timer layout that displays time remaining until the next meeting, optimized for e-ink displays and accessibility.

**Key Requirements**:
- Real-time countdown functionality
- Meeting detection algorithm
- E-ink display optimization
- Accessibility compliance
- Performance efficiency

#### Implementation Architecture

**1. Layout Configuration Design**

The layout follows CalendarBot's standardized configuration pattern:

```json
{
  "name": "whats-next-view",
  "display_name": "What's Next Countdown",
  "description": "Countdown timer layout for next meeting with smart detection",
  "capabilities": {
    "real_time_updates": true,
    "countdown_timer": true,
    "meeting_detection": true,
    "display_modes": ["countdown", "eink", "standard"]
  },
  "specialized_features": {
    "countdown_precision": "seconds",
    "meeting_detection_algorithm": "next_event_priority",
    "auto_refresh_interval": 1000,
    "timezone_aware": true
  }
}
```

**2. JavaScript Implementation Patterns**

```javascript
// whats-next-view.js - Demonstrates real-time update patterns
class WhatsNextView {
    constructor() {
        this.countdownInterval = null;
        this.nextMeeting = null;
        this.updateFrequency = 1000; // 1 second
    }

    async initialize() {
        await this.detectNextMeeting();
        this.startCountdown();
        this.setupAccessibilityFeatures();
    }

    async detectNextMeeting() {
        // Integration with CalendarBot's event API
        const events = await this.fetchEvents();
        this.nextMeeting = this.findNextMeeting(events);
    }

    startCountdown() {
        // Real-time countdown implementation
        this.countdownInterval = setInterval(() => {
            this.updateCountdownDisplay();
        }, this.updateFrequency);
    }
}
```

**3. CSS Design Patterns**

```css
/* whats-next-view.css - E-ink optimization patterns */
.whats-next-container {
    /* High contrast for e-ink displays */
    background: #ffffff;
    color: #000000;
    font-family: 'DejaVu Sans Mono', monospace;
    
    /* Remove animations for e-ink efficiency */
    * {
        transition: none !important;
        animation: none !important;
    }
}

.countdown-display {
    /* Large, readable text for accessibility */
    font-size: 4rem;
    font-weight: bold;
    text-align: center;
    
    /* High contrast borders */
    border: 3px solid #000000;
    padding: 2rem;
}
```

#### Design Patterns Demonstrated

**1. Modular Resource Management**
- Separate CSS and JavaScript files for maintainability
- Resource loading through CalendarBot's ResourceManager
- Fallback resource handling

**2. Configuration-Driven Behavior**
- Layout capabilities defined in configuration
- Runtime feature detection
- Flexible deployment options

**3. Integration Points**
- Web server layout switching
- Display manager coordination
- Cache system integration for event data

**4. Performance Optimization**
- Efficient DOM updates for countdown
- Memory-conscious event handling
- E-ink display refresh minimization

#### Testing Strategy

**Unit Tests**: [`tests/__tests__/whats-next-view.test.js`](tests/__tests__/whats-next-view.test.js)

```javascript
describe('WhatsNextView', () => {
    test('detectNextMeeting filters all-day events', async () => {
        const mockEvents = [
            { isAllDay: true, start: '2025-01-15' },
            { isAllDay: false, start: '2025-01-15T14:00:00Z' }
        ];
        
        const view = new WhatsNextView();
        const nextMeeting = view.findNextMeeting(mockEvents);
        
        expect(nextMeeting.isAllDay).toBe(false);
    });

    test('countdown updates every second', () => {
        const view = new WhatsNextView();
        const spy = jest.spyOn(view, 'updateCountdownDisplay');
        
        view.startCountdown();
        
        setTimeout(() => {
            expect(spy).toHaveBeenCalled();
        }, 1100);
    });
});
```

**Integration Testing**:
- Layout registration through LayoutRegistry
- Resource loading validation
- API endpoint integration
- Cross-browser compatibility

#### Development Workflow Applied

**1. Requirements Analysis**
- Identified need for countdown functionality
- Analyzed e-ink display constraints
- Defined accessibility requirements

**2. Architecture Design**
- Leveraged existing layout system
- Designed for extensibility
- Planned integration points

**3. Implementation**
- Followed CalendarBot coding standards
- Used async/await patterns
- Implemented comprehensive error handling

**4. Testing & Validation**
- Unit tests for JavaScript logic
- Layout validation through system
- Performance testing on target hardware

**5. Documentation**
- Configuration examples
- API integration guide
- Deployment instructions

#### Extension Lessons Learned

**1. Layout System Flexibility**
- Configuration-driven approach enables rapid prototyping
- Resource management system simplifies asset handling
- Integration points provide clean extension mechanisms

**2. Performance Considerations**
- E-ink displays require specialized optimization
- Real-time updates need careful resource management
- Accessibility features must be designed from the start

**3. Testing Strategies**
- JavaScript unit tests essential for client-side logic
- Integration testing validates system-wide functionality
- Performance testing crucial for specialized hardware

This case study demonstrates how CalendarBot's architectural patterns enable developers to create sophisticated, specialized layouts while maintaining system consistency and performance standards.

### Documentation Update Examples

When a new CLI command is added, follow these steps to document it:

```markdown
#### `mynewcommand` Command

This command runs a custom command.

**Usage**:

```sh
calendarbot mynewcommand --example-arg <example_arg>
```

**Options**:

- `--example-arg`: (required) A required example argument.
```

**Documentation**:
```

When a CLI command supports a flag without an argument, follow these steps to document it:

```markdown
#### `myflagcommand` Command

This command runs a custom command with a flag.

**Usage**:

```sh
calendarbot myflagcommand --example-flag
```

**Options**:

- `--example-flag`: (optional) A boolean flag indicating a particular behavior.
```

**Documentation**:
```

## Conclusion

This guide provides a comprehensive overview of CalendarBot's architectural foundations, development conventions, and extension mechanisms. For up-to-date information, refer to the official documentation repository and contribute to improvements by following the outlined workflows.
