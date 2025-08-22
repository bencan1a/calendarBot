# CalendarBot Project Brief

## Main Goal/Purpose

CalendarBot is an ICS-based calendar display application designed to provide a flexible, multi-mode calendar visualization system. It fetches calendar data from standard ICS feeds, processes and caches the events, and renders them through various display interfaces. The primary purpose is to offer a universal calendar compatibility layer with real-time updates and extensible deployment options, making calendar information easily accessible across different environments and display types.

## Key Features/Components

1. **Universal Calendar Support**
   - Compatible with Microsoft Outlook/Office 365, Google Calendar, Apple iCloud Calendar, and any RFC 5545 compliant calendar system
   - Supports various authentication methods (none, basic, bearer)

2. **Multiple Operational Modes**
   - Interactive Mode: Keyboard-driven navigation with real-time background data fetching
   - Web Mode: Browser-based calendar interface with multiple layout support
   - E-Paper Mode: E-ink display optimized layouts for power-efficient rendering
   - Setup Mode: Interactive configuration wizard for easy onboarding

3. **Layout Management System**
   - Dynamic layout discovery and validation
   - Multiple layout support (4x8, 3x4, whats-next-view)
   - Resource management for CSS/JS assets
   - Responsive design with fallback capabilities

4. **Core System Components**
   - Source Management: Coordinates multiple calendar sources with health monitoring
   - ICS Processing: Async HTTP client with RFC 5545 compliant parsing
   - Cache Management: Event storage with TTL management
   - Display Management: Coordinates rendering across different display types

5. **Meeting Context Features**
   - Intelligent analysis of calendar events
   - "What's Next" view with countdown timer
   - Meeting detection algorithms

## Target Audience/Users

CalendarBot is designed for:

1. **Individual Users**: Who need a flexible calendar display for personal use
2. **Office Environments**: For meeting room displays and shared calendars
3. **Embedded Device Users**: Particularly those using e-ink displays
4. **Developers**: Who want to extend or customize calendar visualization

## Architectural Style/Technologies

1. **Core Architecture**
   - Modular component-based design with clear separation of concerns
   - Manager→Handler→Protocol relationship pattern
   - Async/await patterns for efficient I/O operations

2. **Technology Stack**
   - **Language**: Python 3.8+ with modern async/await patterns
   - **Data Processing**: icalendar (RFC 5545 compliant parsing)
   - **HTTP Client**: httpx (async HTTP with authentication support)
   - **Data Validation**: pydantic v2.0+ (settings and data model validation)
   - **Database**: aiosqlite (async SQLite for event caching)
   - **Configuration**: PyYAML + pydantic-settings
   - **Web Server**: Python HTTPServer for lightweight web interface

3. **MCP Server Integration**
   - **Playwright MCP**: Used for browser automation, UI testing, and visual validation
   - **Context7 MCP**: Used for documentation and code examples

## Foundational Information

1. **Development Standards**
   - Comprehensive type annotations for all parameters/returns
   - Explicit error handling with specific exception types
   - Structured logging with context
   - Unit testing with pytest

2. **Configuration System**
   - Hierarchical configuration approach (defaults, YAML, environment variables, CLI)
   - Pydantic-based settings validation
   - Multiple configuration locations support (project dir, user home)

3. **Deployment Options**
   - Standard desktop/laptop deployment
   - E-ink display support with device integration
   - Web server mode for network access

4. **Performance Considerations**
   - Efficient caching strategy with TTL management
   - Async I/O for network and database operations
   - E-ink optimized rendering for power efficiency

This project brief reflects the current implementation state of CalendarBot as of August 2025.