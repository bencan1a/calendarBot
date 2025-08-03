# CalendarBot Operational Modes

**Version:** 1.0.0  
**Last Updated:** August 3, 2025  
**Related Modules:** 
- `calendarbot/cli/modes/`
- `calendarbot/setup_wizard.py`
**Status:** Implemented

## Overview

CalendarBot supports multiple operational modes to accommodate different use cases, environments, and user preferences. Each mode provides specialized functionality while sharing the core calendar processing capabilities. This modular approach allows CalendarBot to function effectively in various deployment scenarios, from headless servers to interactive terminals to Raspberry Pi e-paper displays.

## Available Modes

### 1. Setup Mode (`--setup`)

Setup mode provides an interactive configuration wizard to help users set up their calendar sources, authentication, and display preferences.

**Entry Point:** `calendarbot/setup_wizard.py`

**Key Features:**
- Interactive configuration wizard with service templates
- Automatic ICS feed validation and testing
- Authentication setup (basic auth, bearer tokens)
- Configuration file generation and management

**Usage:**
```bash
calendarbot --setup
```

**Example Workflow:**
1. User runs CalendarBot in setup mode
2. Wizard prompts for calendar service type (Google, Outlook, etc.)
3. User provides calendar URL and authentication details
4. System validates the calendar feed
5. Configuration is saved to `config.yaml`

### 2. Interactive Mode (`--interactive`)

Interactive mode provides a terminal-based user interface with keyboard navigation for viewing and interacting with calendar events.

**Entry Point:** `calendarbot/cli/modes/interactive.py`

**Key Features:**
- Keyboard-driven navigation (arrow keys, space, ESC)
- Real-time background data fetching
- Split-screen logging in development mode
- Cross-platform input handling

**Usage:**
```bash
calendarbot --interactive
```

**Example Workflow:**
1. User runs CalendarBot in interactive mode
2. Terminal displays current day's events
3. User navigates between days using arrow keys
4. Background processes fetch updated calendar data
5. User exits with ESC key

### 3. Web Mode (`--web`)

Web mode runs a local web server that provides a browser-based interface for viewing calendar events with rich formatting and layout options.

**Entry Point:** `calendarbot/cli/modes/web.py`

**Key Features:**
- Browser-based calendar interface
- Multiple layout support (4x8, 3x4, whats-next-view)
- Auto-refresh capabilities
- Mobile-responsive design

**Usage:**
```bash
calendarbot --web [--port PORT]
```

**Example Workflow:**
1. User runs CalendarBot in web mode
2. Web server starts on specified port (default: 8080)
3. User opens browser to http://localhost:8080
4. Browser displays calendar with selected layout
5. Page auto-refreshes to show updated events

### 4. E-Paper Mode (`--epaper`)

E-Paper mode is optimized for Raspberry Pi devices with e-ink displays, providing power-efficient rendering and specialized layouts.

**Entry Point:** `calendarbot/cli/modes/epaper.py`

**Key Features:**
- E-ink display optimized layouts (800x480px)
- High contrast, minimal refresh themes
- Power-efficient rendering strategies
- Web interface integration

**Usage:**
```bash
calendarbot --epaper
```

**Example Workflow:**
1. User runs CalendarBot in e-paper mode on Raspberry Pi
2. System detects connected e-ink display
3. Calendar is rendered with e-ink optimized layout
4. Display refreshes at configured intervals
5. Low power consumption for long-term operation

### 5. Test/Validation Mode (`--test-mode`)

Test mode runs comprehensive system validation to verify configuration, connectivity, and functionality.

**Entry Point:** `calendarbot/cli/modes/test.py`

**Key Features:**
- Comprehensive system validation
- Component-specific testing (ICS, cache, display)
- Performance benchmarking
- Configuration verification

**Usage:**
```bash
calendarbot --test-mode
```

**Example Workflow:**
1. User runs CalendarBot in test mode
2. System validates configuration files
3. Tests connectivity to calendar sources
4. Verifies cache functionality
5. Reports results with detailed diagnostics

### 6. Default Mode

When no specific mode is provided, CalendarBot defaults to web mode with standard settings.

**Entry Point:** `calendarbot/cli/__init__.py`

**Key Features:**
- Defaults to web mode when no other mode is specified
- Configuration validation and loading
- Graceful error handling and recovery
- Command-line argument processing

**Usage:**
```bash
calendarbot
```

**Example Workflow:**
1. User runs CalendarBot without mode flags
2. System loads configuration and validates
3. Web server starts with default settings
4. User accesses calendar via browser

## Mode Selection Logic

CalendarBot uses the following logic to determine which mode to run:

1. Command-line arguments are parsed first (`--setup`, `--interactive`, etc.)
2. If multiple mode flags are provided, precedence is:
   - Setup > Test > E-Paper > Interactive > Web
3. If no mode flag is provided, defaults to web mode
4. Configuration file settings can specify a default mode

## Configuration

Mode-specific configuration is managed through the settings system:

```yaml
# Mode-specific settings in config.yaml

# Interactive Mode Settings
interactive:
  enabled: true
  refresh_interval: 60  # seconds
  log_display: true
  log_lines: 5

# Web Mode Settings
web:
  enabled: true
  port: 8080
  host: "0.0.0.0"
  layout: "4x8"
  auto_refresh: 60  # seconds

# E-Paper Mode Settings
epaper:
  enabled: false
  display_type: "waveshare_v2"
  display_width: 800
  display_height: 480
  refresh_mode: "partial"
  refresh_interval: 300  # seconds
```

## API Reference

### Mode Entry Points

Each mode has a standardized entry point function:

```python
def run_mode(settings: CalendarBotSettings, args: argparse.Namespace) -> int:
    """
    Run the specific mode with provided settings and arguments.
    
    Args:
        settings: Application settings
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
```

### Common Mode Interfaces

All modes implement these common interfaces:

```python
def initialize(settings: CalendarBotSettings) -> bool:
    """Initialize mode-specific resources."""
    
def cleanup() -> None:
    """Clean up mode-specific resources."""
    
def handle_signal(sig: int, frame: Any) -> None:
    """Handle system signals (SIGINT, SIGTERM)."""
```

## Integration Points

The operational modes integrate with the following CalendarBot components:

- **Source Management**: All modes use the SourceManager to fetch calendar data
- **Cache System**: All modes leverage the cache for performance optimization
- **Display System**: Each mode uses appropriate renderers for its display needs
- **Layout System**: Web and E-Paper modes use the layout management system
- **Configuration**: All modes use the settings system for configuration

## Extending with Custom Modes

CalendarBot can be extended with custom operational modes:

1. Create a new module in `calendarbot/cli/modes/`
2. Implement the standard mode interfaces
3. Register the mode in `calendarbot/cli/__init__.py`
4. Add command-line argument handling

Example custom mode skeleton:

```python
# calendarbot/cli/modes/custom_mode.py
from calendarbot.config.settings import CalendarBotSettings

def run_custom_mode(settings: CalendarBotSettings, args: Any) -> int:
    """Run custom operational mode."""
    # Initialize resources
    # Main mode logic
    # Cleanup resources
    return 0

def initialize(settings: CalendarBotSettings) -> bool:
    """Initialize custom mode resources."""
    return True

def cleanup() -> None:
    """Clean up custom mode resources."""
    pass
```

## Limitations

- Only one mode can be active at a time
- Some modes require specific hardware (e-paper mode)
- No remote control or API for switching modes at runtime
- Limited customization of mode-specific behaviors
- No support for custom renderers in interactive mode