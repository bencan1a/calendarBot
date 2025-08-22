# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CalendarBot is a Python-based calendar application that fetches and displays ICS calendar feeds. It features multiple display modes including terminal UI, web interface, and e-paper display support.

## Key Commands

### Development Setup
```bash
# Activate virtual environment
. venv/bin/activate  # Linux/Mac
. venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -e ".[dev]"
```

### Running the Application
```bash
# Interactive terminal mode
calendarbot

# Web interface (port 8080)
calendarbot --web

# Setup wizard for initial configuration
calendarbot --setup

# E-paper display mode
calendarbot --epaper
```

### Testing Commands

#### Python Tests (pytest)
```bash
# Run full test suite with coverage
pytest --cov=calendarbot --cov-report=term-missing --cov-report=html

# Run specific test categories
pytest tests/unit/ -m "unit or fast"       # Unit tests only
pytest tests/integration/ -m "integration"  # Integration tests
pytest tests/browser/ -m "browser"         # Browser tests

# Use the coverage script for managed test execution with timeouts
./scripts/run_coverage.sh full        # Complete test suite (30min timeout)
./scripts/run_coverage.sh unit        # Unit tests only (5min timeout)
./scripts/run_coverage.sh browser     # Browser tests with cleanup (15min timeout)
./scripts/run_coverage.sh diagnose    # Test suite health check

# Run specific module tests
./scripts/run_coverage.sh individual calendarbot.setup_wizard
./scripts/run_coverage.sh module tests/unit/test_setup_wizard.py
```

#### JavaScript Tests (Jest)
```bash
# Run JavaScript tests for web UI components
npm test                    # Run all tests
npm run test:watch         # Watch mode
npm run test:coverage      # With coverage report
```

### Code Quality
```bash
# Linting and formatting (using ruff)
ruff check calendarbot      # Check for issues
ruff format calendarbot     # Format code

# Type checking
mypy calendarbot

# Security scanning
bandit -r calendarbot

# Find dead code
python scripts/find_dead_code.py
```

### Performance & Benchmarking
```bash
# Run performance benchmarks
python scripts/performance_benchmark.py

# Test bootup performance
python scripts/test_bootup_performance.py

# View performance trends
python scripts/view_performance_trends.py
```

## High-Level Architecture

### Core Components

1. **Cache System** (`calendarbot/cache/`)
   - `DatabaseManager`: SQLite-based event storage with async operations
   - `CacheManager`: Coordinates between API fetches and local storage
   - Supports offline mode with TTL-based expiration
   - Raw event storage for original ICS data preservation

2. **Display Subsystem** (`calendarbot/display/`)
   - **Renderer Protocol**: Unified interface for all display modes
   - **Console Renderer**: Terminal UI with keyboard navigation
   - **HTML Renderer**: Web interface generation
   - **E-Paper Integration**: Waveshare display support with color optimization
   - **What's Next Logic**: Business logic for event prioritization and grouping

3. **Web Server** (`calendarbot/web/`)
   - HTTP server with static file caching
   - RESTful API endpoints for event data and settings
   - Layout registry system for dynamic UI components
   - Settings panel for runtime configuration

4. **Layout System** (`calendarbot/layout/`)
   - `LayoutRegistry`: Dynamic layout discovery and loading
   - `LazyLayoutRegistry`: Deferred loading for performance
   - `ResourceManager`: Static asset bundling and optimization
   - Supports custom layouts in `web/static/layouts/`

5. **ICS Processing** (`calendarbot/ics/`)
   - `ICSFetcher`: Async HTTP client for calendar feeds
   - `ICSParser`: Streaming parser for large calendar files
   - `RRuleExpander`: Recurring event expansion with timezone support
   - Handles both ICS feeds and Microsoft Graph API

6. **Configuration** (`calendarbot/config/`)
   - YAML-based configuration with environment variable overrides
   - Build-time optimization settings
   - Runtime settings management via web UI

7. **Monitoring & Optimization** (`calendarbot/monitoring/`, `calendarbot/optimization/`)
   - Connection pool monitoring
   - Performance tracking and metrics
   - Static asset caching
   - Memory usage optimization

### Key Design Patterns

- **Async-First**: Core operations use asyncio for concurrent processing
- **Protocol-Based Interfaces**: Display renderers follow unified protocol
- **Lazy Loading**: Deferred resource loading for faster startup
- **Event-Driven Updates**: Real-time calendar updates via polling
- **Modular Layouts**: Pluggable UI components with self-contained assets

### Database Schema

- **cached_events**: Processed calendar events with display metadata
- **raw_events**: Original ICS content for data integrity
- **cache_metadata**: Feed metadata and sync timestamps
- **hidden_events**: User-hidden events management

### Testing Strategy

- **Unit Tests**: Fast, isolated component testing
- **Integration Tests**: Cross-component interaction validation  
- **Browser Tests**: Playwright-based UI testing
- **Coverage Target**: Minimum 60% for critical paths
- **Test Markers**: `unit`, `integration`, `browser`, `e2e`, `slow`

## Important Development Notes

- Always activate the virtual environment before running commands
- The project uses both Python (backend) and JavaScript (frontend) testing
- Browser tests can hang - use `./scripts/run_coverage.sh browser` for automatic cleanup
- E-paper functionality requires compatible e-ink display hardware
- Web server runs on port 8080 by default
- Settings changes via web UI are persisted to `config/config.yaml`
- Use correlation IDs for debugging async operations
- Check `calendarbot.log` for detailed runtime information

## Common Development Tasks

### Adding a New Layout
1. Create directory in `calendarbot/web/static/layouts/[name]/`
2. Add `[name].js`, `[name].css`, and `layout.json`
3. Layout will be auto-discovered by the registry

### Debugging Event Processing
1. Enable debug logging: `export LOG_LEVEL=DEBUG`
2. Check correlation IDs in logs for request tracking
3. Use `--test` mode to validate configuration

### Performance Optimization
1. Run benchmarks: `python scripts/performance_benchmark.py`
2. Check static asset caching in production mode
3. Monitor connection pool usage in logs

## Testing Individual Components

```bash
# Test specific functionality
pytest tests/unit/display/test_whats_next_logic.py -v
pytest tests/integration/test_web_api_integration.py -v

# Test with specific markers
pytest -m "not slow"  # Skip slow tests
pytest -m "critical"  # Only critical path tests
```

## Environment Variables

- `LOG_LEVEL`: Set logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `CONFIG_FILE`: Override default config location
- `DATABASE_FILE`: Override SQLite database location
- `PRODUCTION_MODE`: Enable production optimizations