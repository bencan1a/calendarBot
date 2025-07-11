# Development Guide

**Document Version:** 2.0
**Last Updated:** January 7, 2025
**System Version:** CalendarBot v1.0.0
**Target Audience:** Contributors, Developers, Maintainers

This guide covers development environment setup, contribution workflows, and technical guidelines for CalendarBot development.

## 🚀 Quick Start: Development Environment Setup

CalendarBot uses modern Python development practices with automated environment setup:

### One-Command Setup

```bash
# Clone the repository
git clone <repository-url> calendarbot
cd calendarbot

# Run automated development setup
python scripts/dev_setup.py
```

**The automated setup handles**:
- ✅ Virtual environment creation and activation
- ✅ Development dependencies installation (`pip install -e .[dev]`)
- ✅ Code quality tools (black, mypy, pytest)
- ✅ Pre-commit hooks configuration
- ✅ Development database initialization
- ✅ Environment validation

## Table of Contents

- [Development Environment](#development-environment)
- [Project Structure](#project-structure)
- [Code Quality Standards](#code-quality-standards)
- [Testing Framework](#testing-framework)
- [Configuration Development](#configuration-development)
- [Module Development Guidelines](#module-development-guidelines)
- [Web Interface Development](#web-interface-development)
- [Contributing Workflow](#contributing-workflow)
- [Troubleshooting](#troubleshooting)

## Development Environment

### Prerequisites

- **Python 3.8+** (3.10+ recommended)
- **Git** for version control
- **Modern terminal** with ANSI color support

### Automated Development Setup

The [`scripts/dev_setup.py`](scripts/dev_setup.py) script provides comprehensive environment setup:

```python
# Features included in automated setup:
- Virtual environment management
- Editable package installation
- Development dependency resolution
- Code quality tool configuration
- Testing framework initialization
- IDE configuration templates
```

### Manual Setup (Alternative)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Verify installation
calendarbot --version
calendarbot --test-mode
```

## Project Structure

### Module Organization

```
calendarbot/
├── __init__.py              # Package metadata and version
├── __main__.py              # Module execution support (python -m calendarbot)
├── main.py                  # Core application logic (CalendarBot class)
├── setup_wizard.py          # Interactive configuration wizard
│
├── cache/                   # Event caching and storage
│   ├── __init__.py
│   ├── manager.py           # Cache coordination and TTL management
│   ├── database.py          # Async SQLite operations
│   └── models.py            # Cache data models
│
├── display/                 # Output rendering and presentation
│   ├── __init__.py
│   ├── manager.py           # Display mode coordination
│   ├── console_renderer.py  # Console output formatting
│   ├── html_renderer.py     # Web-compatible HTML rendering
│   └── rpi_html_renderer.py # E-ink optimized layouts
│
├── ics/                     # ICS calendar processing
│   ├── __init__.py
│   ├── fetcher.py           # Async HTTP client with auth
│   ├── parser.py            # RFC 5545 ICS parsing
│   ├── models.py            # ICS data models
│   └── exceptions.py        # ICS-specific errors
│
├── sources/                 # Calendar source management
│   ├── __init__.py
│   ├── manager.py           # Multi-source coordination
│   ├── ics_source.py        # ICS source implementation
│   ├── models.py            # Source configuration models
│   └── exceptions.py        # Source-specific errors
│
├── ui/                      # Interactive user interface
│   ├── __init__.py
│   ├── interactive.py       # Interactive navigation controller
│   ├── keyboard.py          # Cross-platform input handling
│   └── navigation.py        # Date navigation logic
│
├── utils/                   # Common utilities
│   ├── __init__.py
│   ├── logging.py           # Enhanced logging with interactive support
│   └── helpers.py           # Utility functions
│
├── validation/              # Testing and validation framework
│   ├── __init__.py
│   ├── runner.py            # Comprehensive system validation
│   ├── results.py           # Test result models
│   └── logging_setup.py     # Validation-specific logging
│
└── web/                     # Web interface
    ├── __init__.py
    ├── server.py            # Web server implementation
    ├── navigation.py        # Web navigation handling
    └── static/              # CSS, JavaScript, themes
        ├── style.css        # Standard web theme
        ├── eink-compact-300x400.css  # E-ink compact theme
        ├── eink-compact-300x400.js   # E-ink compact JavaScript
        └── app.js           # Main web application logic
```

### Configuration Structure

```
config/
├── __init__.py
├── settings.py              # Pydantic settings models
├── config.yaml.example      # Configuration template
└── ics_config.py            # ICS-specific configuration helpers
```

### Entry Points

```
main.py                      # Primary entry point (direct execution)
pyproject.toml              # Package configuration and console scripts
setup.py                    # Legacy packaging support
```

## Code Quality Standards

### Code Formatting with Black

```bash
# Format all code
black calendarbot/ tests/ scripts/

# Check formatting without changes
black --check calendarbot/

# Configuration in pyproject.toml
[tool.black]
line-length = 100
target-version = ['py38']
```

### Type Checking with MyPy

```bash
# Run type checking
mypy calendarbot/

# Check specific module
mypy calendarbot/main.py

# Configuration in pyproject.toml
[tool.mypy]
python_version = "3.8"
disallow_untyped_defs = true
warn_return_any = true
```

### Import Sorting with isort

```bash
# Sort imports
isort calendarbot/ tests/

# Configuration in pyproject.toml
[tool.isort]
profile = "black"
line_length = 100
```

### Pre-commit Hooks

Automatically enforces code quality on every commit:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
```

## Testing Framework

### Test Organization

```
tests/
├── __init__.py
├── conftest.py              # Pytest configuration and fixtures
├── unit/                    # Unit tests
│   ├── test_cache_manager.py
│   ├── test_ics_parser.py
│   ├── test_settings.py
│   └── test_setup_wizard.py
├── integration/             # Integration tests
│   ├── test_full_pipeline.py
│   ├── test_web_server.py
│   └── test_validation.py
└── fixtures/                # Test data and fixtures
    ├── sample_calendars.ics
    └── config_examples/
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=calendarbot --cov-report=html

# Run specific test categories
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only

# Run tests with markers
pytest -m "not slow"        # Skip slow tests
pytest -m integration       # Only integration tests

# Verbose output with test details
pytest -v --tb=short
```

### Test Configuration

```toml
# pyproject.toml pytest configuration
[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --strict-markers"
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

### Writing Tests

```python
# Example unit test
import pytest
from calendarbot.cache.manager import CacheManager
from config.settings import CalendarBotSettings

@pytest.mark.asyncio
async def test_cache_manager_initialization():
    """Test cache manager initialization."""
    settings = CalendarBotSettings()
    cache_manager = CacheManager(settings)

    assert await cache_manager.initialize()
    assert cache_manager.is_initialized

# Example integration test
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_ics_pipeline():
    """Test complete ICS processing pipeline."""
    # Test implementation here
    pass
```

## Configuration Development

### Settings Architecture

The configuration system in [`config/settings.py`](config/settings.py) uses Pydantic for validation:

```python
# Example settings model
class CalendarBotSettings(BaseSettings):
    """Application settings with environment variable support."""

    # ICS Configuration
    ics_url: Optional[str] = Field(None, description="ICS calendar URL")
    ics_auth_type: Optional[str] = Field(None, regex="^(none|basic|bearer)$")

    # Automatic environment variable mapping
    class Config:
        env_prefix = "CALENDARBOT_"
        env_file = ".env"
```

### Adding New Configuration Options

1. **Define in Settings Model**:
```python
# Add to CalendarBotSettings class
new_feature_enabled: bool = Field(default=False, description="Enable new feature")
new_feature_timeout: int = Field(default=30, description="New feature timeout")
```

2. **Update YAML Schema**:
```yaml
# Add to config.yaml.example
new_feature:
  enabled: false
  timeout: 30
```

3. **Handle in Settings Loading**:
```python
# Add to _load_yaml_config method
if 'new_feature' in config_data:
    feature_config = config_data['new_feature']
    if 'enabled' in feature_config:
        self.new_feature_enabled = feature_config['enabled']
```

## Module Development Guidelines

### Adding New Modules

1. **Create Module Directory**:
```bash
mkdir calendarbot/new_module
touch calendarbot/new_module/__init__.py
```

2. **Implement Core Components**:
```python
# calendarbot/new_module/manager.py
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class NewModuleManager:
    """Manager for new module functionality."""

    def __init__(self, settings):
        self.settings = settings
        self.initialized = False

    async def initialize(self) -> bool:
        """Initialize the module."""
        try:
            # Initialization logic
            self.initialized = True
            logger.info("New module initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize new module: {e}")
            return False
```

3. **Add Data Models**:
```python
# calendarbot/new_module/models.py
from pydantic import BaseModel, Field
from typing import Optional

class NewModuleConfig(BaseModel):
    """Configuration model for new module."""

    enabled: bool = Field(default=False, description="Enable new module")
    timeout: int = Field(default=30, description="Operation timeout")
```

4. **Implement Exception Handling**:
```python
# calendarbot/new_module/exceptions.py
class NewModuleError(Exception):
    """Base exception for new module."""
    pass

class NewModuleConnectionError(NewModuleError):
    """Connection-related errors."""
    pass
```

### Integration with Main Application

```python
# Update calendarbot/main.py
from .new_module import NewModuleManager

class CalendarBot:
    def __init__(self):
        # Add to initialization
        self.new_module_manager = NewModuleManager(self.settings)

    async def initialize(self) -> bool:
        # Add to initialization sequence
        if not await self.new_module_manager.initialize():
            logger.error("Failed to initialize new module")
            return False
```

## Web Interface Development

### Theme Development

Create new themes in [`calendarbot/web/static/`](calendarbot/web/static/):

```css
/* custom-theme.css */
.custom-theme {
    /* Base theme variables */
    --bg-color: #ffffff;
    --text-color: #000000;
    --border-color: #cccccc;
    --accent-color: #007bff;
}

.custom-theme .calendar-container {
    background-color: var(--bg-color);
    color: var(--text-color);
    border: 1px solid var(--border-color);
}
```

### JavaScript Enhancement

```javascript
// custom-features.js
class CustomCalendarFeatures {
    constructor() {
        this.init();
    }

    init() {
        // Custom initialization
        this.setupEventHandlers();
    }

    setupEventHandlers() {
        // Custom event handling
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new CustomCalendarFeatures();
});
```

### Web Server Extension

```python
# Extend web server functionality
from calendarbot.web.server import WebServer

class ExtendedWebServer(WebServer):
    """Extended web server with custom features."""

    def add_custom_routes(self):
        """Add custom routes to the web server."""

        @self.app.route('/api/custom-endpoint')
        async def custom_endpoint():
            """Custom API endpoint."""
            return {"status": "success", "data": "custom data"}
```

## Contributing Workflow

### Development Process

1. **Fork and Clone**:
```bash
git clone https://github.com/your-username/calendarbot.git
cd calendarbot
```

2. **Set Up Development Environment**:
```bash
python scripts/dev_setup.py
```

3. **Create Feature Branch**:
```bash
git checkout -b feature/your-feature-name
```

4. **Develop with Quality Checks**:
```bash
# Code changes automatically checked by pre-commit hooks
# Manual quality verification:
black calendarbot/
mypy calendarbot/
pytest --cov=calendarbot
```

5. **Test Your Changes**:
```bash
# Test packaging
python -m build

# Test installation
pip install -e .[dev]

# Test functionality
calendarbot --test-mode --verbose
calendarbot --setup --dry-run
```

6. **Submit Pull Request**:
- Ensure all automated checks pass
- Include tests for new functionality
- Update documentation as needed
- Provide clear description of changes

### Code Style Guidelines

- **Type Hints**: Required for all public APIs and recommended for internal functions
- **Docstrings**: Google-style docstrings for all public classes and functions
- **Error Handling**: Comprehensive exception handling with logging
- **Async/Await**: Use async patterns for I/O operations
- **Configuration**: Make behavior configurable through settings when appropriate

### Documentation Standards

- **Module Documentation**: Each module should have clear docstrings
- **API Documentation**: Public APIs need comprehensive documentation
- **Configuration**: New settings must be documented in config.yaml.example
- **Architecture**: Significant changes should update ARCHITECTURE.md

## Troubleshooting

### Common Development Issues

**Issue**: Pre-commit hooks failing
```bash
# Solution: Reinstall hooks
pre-commit uninstall
pre-commit install
pre-commit run --all-files
```

**Issue**: Type checking errors
```bash
# Solution: Check mypy configuration
mypy --config-file pyproject.toml calendarbot/
# Update type hints as needed
```

**Issue**: Import errors during development
```bash
# Solution: Reinstall in development mode
pip install -e .[dev]
# Verify package structure
python -c "import calendarbot; print(calendarbot.__file__)"
```

**Issue**: Tests failing after changes
```bash
# Solution: Run specific test with verbose output
pytest -v tests/test_specific_module.py::test_function
# Check test fixtures and dependencies
```

### Development Environment Issues

**Python Version Compatibility**:
```bash
# Check Python version
python --version  # Should be 3.8+

# Update dependencies if needed
pip install --upgrade pip setuptools wheel
```

**Virtual Environment Problems**:
```bash
# Recreate virtual environment
rm -rf venv/
python -m venv venv
source venv/bin/activate
pip install -e .[dev]
```

### Performance Profiling

```bash
# Profile memory usage
python -m memory_profiler main.py --test-mode

# Profile execution time
python -m cProfile -o profile.out main.py --test-mode
python -c "import pstats; pstats.Stats('profile.out').sort_stats('time').print_stats(10)"

# Monitor resource usage
htop  # While running calendarbot
```

### Database Development

```bash
# Reset development database
rm -f ~/.local/share/calendarbot/calendar_cache.db

# Inspect database during development
sqlite3 ~/.local/share/calendarbot/calendar_cache.db ".schema"
sqlite3 ~/.local/share/calendarbot/calendar_cache.db "SELECT * FROM cached_events LIMIT 5;"
```

---

## Next Steps

After setting up your development environment:

1. **Explore the Codebase**: Start with [`calendarbot/main.py`](calendarbot/main.py) and [`config/settings.py`](config/settings.py)
2. **Run Tests**: Execute `pytest --cov=calendarbot` to understand test coverage
3. **Try Different Modes**: Test `--setup`, `--interactive`, `--web`, and `--test-mode`
4. **Read Architecture**: Review [`ARCHITECTURE.md`](ARCHITECTURE.md) for system design
5. **Check Issues**: Look for "good first issue" labels in the repository

---

**Development Guide v2.0** - Updated for current CalendarBot architecture with comprehensive development workflows and module-specific guidelines.
