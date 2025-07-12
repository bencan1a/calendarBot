# Usage Guide

This guide covers daily operation and all operational modes of Calendar Bot.

## Table of Contents

- [Operational Modes](#operational-modes)
- [Basic Workflows](#basic-workflows)
- [Intermediate Operations](#intermediate-operations)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)
- [Advanced Operations](#advanced-operations)
- [See Also](#see-also)

### Display Configuration

To configure CalendarBot for specific display resolutions:

**Supported Display Types**:
- **4x8 (Standard):** Optimized for typical desktop LCD screens
- **3x4 (Compact):** Designed for small embedded displays like e-ink panels

**Command Line Selection**:
```bash
# Console-only example
python main.py --display-type 4x8

# Web interface example
python main.py --web --display-type 3x4
```

**Tips**:
- Display type affects layout rendering but maintains data consistency across modes
- Combine with `--help` for full option details (e.g., `python main.py --web --help`)

## Operational Modes

### Interactive Mode (Default)

**Command**: `python main.py` or `python main.py --interactive`

**Features**:

- Real-time calendar display with automatic updates
- Keyboard navigation between dates with status indicators
- Quick jump to today and refreshing capabilities

**Keyboard Controls**:

- **Arrow Keys**: Navigate between dates (← Previous day, → Next day)
- **Space**: Jump to today's date
- **ESC**: Exit interactive mode
- **Enter**: Refresh current view

### Web Interface Mode

**Command**: `python main.py --web`

**Features**:

- Web interface on `http://localhost:8080` with mobile support
- Real-time auto-refresh and navigation controls

**Intermediate Options**:

```bash
python main.py --web --port 3000       # Custom port
python main.py --web --auto-open       # Auto-open browser
python main.py --web --host 0.0.0.0    # Bind to all interfaces
```

---

## Basic Workflows

### Daily Operation

1. **Interactive Navigation** (Default)
```bash
. venv/bin/activate
python main.py  # Launch interactive mode
```

2. **Web Interface Viewing**
```bash
. venv/bin/activate
python main.py --web  # Launch web interface
```

### Quick Event Refresh

Use Enter (interactive) or manual refresh (web mode) to update calendar view.

---

## Intermediate Operations

### Command Line Options

- **Setup**: `python main.py --setup`
- **Configuration**: `python main.py --config`
- **Help**: `python main.py --help`

**Example**:
```bash
. venv/bin/activate
python main.py --help  # View all command options
```

---

## Maintenance

**Daily Tasks:**

- Monitor console output for errors
- Verify events display correctly

**Weekly Review:**

- Review logs for issues
- Test ICS feed with `python test_ics.py --url "your-url"`

[⬆️ Back to Top](#table-of-contents)

---

## Troubleshooting

- **Events Not Displaying**:
```bash
python test_ics.py --url "$CALENDARBOT_ICS_URL" --verbose
```

- **Offline Mode**:
If offline, Calendar Bot serves cached data.

**Log Level Adjustment**:
```bash
export CALENDARBOT_LOG_LEVEL="DEBUG"
. venv/bin/activate
python main.py --verbose
```

## Advanced Operations

### Testing Modes

**Validation**:
```bash
. venv/bin/activate
python main.py --test-mode  # Validates system components
```

**Component Testing**:
```bash
python main.py --test-mode --components cache  # Tests cache only
```

### Debugging

**Detailed Logs**:
```bash
. venv/bin/activate
python main.py --debug  # Enables full debugging
```

## See Also

- [Setup Guide](SETUP.md)
- [Configuration Wizard](SETUP.md#wizard)
- [Installation Documentation](INSTALL.md)
