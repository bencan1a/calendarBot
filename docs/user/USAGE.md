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

### Layout Configuration

CalendarBot features a dynamic layout system with automatic discovery and validation:

**Built-in Layouts**:
- **4x8 (Standard):** Optimized for typical desktop LCD screens (480x800px)
- **3x4 (Compact):** Designed for small embedded displays and e-ink panels (300x400px)
- **whats-next-view:** Specialized countdown layout for 300x400px displays, focusing on next meeting with real-time timer
- **Custom Layouts:** Create your own layouts with automatic discovery

**Command Line Selection**:
```bash
# Web interface with specific layout
calendarbot --web --display_type 4x8

# Web interface with specific layout
calendarbot --web --display_type 3x4

# Specialized countdown layout for small displays
calendarbot --web --web_layout whats-next-view

# Custom layout
calendarbot --web --display_type my-custom-layout
```

**Dynamic Layout Switching**:
```bash
# Runtime layout switching via URL parameters
# http://<host-ip>:8080/calendar?layout=4x8
# http://<host-ip>:8080/calendar?layout=3x4&date=2025-01-15
```

**Layout Features**:
- Automatic layout discovery and validation
- Fallback chain for missing or invalid layouts
- Multiple renderer support (html, rpi, compact)
- Responsive design for different screen sizes
- Dynamic CSS/JS resource loading

**Tips**:
- Layout affects visual rendering while maintaining data consistency
- Use URL parameters for dynamic layout switching
- Create custom layouts following the [Layout Development Guide](../development/LAYOUT_DEVELOPMENT_GUIDE.md)
- Combine with `--help` for full option details (e.g., `calendarbot --web --help`)

### What's Next View Layout

The **whats-next-view** layout is a specialized interface designed for small displays and meeting countdown scenarios:

**Target Use Cases**:
- Small 300×400px displays (3×4 inch screens)
- E-ink displays requiring minimal updates
- Meeting countdown displays
- Office door displays
- Personal meeting reminder screens

**Key Features**:
- **Real-time Countdown**: Displays countdown timer to next meeting start or current meeting end
- **Meeting Focus**: Shows only the most relevant upcoming meeting with full details
- **Automatic Transitions**: Seamlessly transitions from one meeting to the next
- **Urgent Highlighting**: Visual and accessible alerts when meetings are less than 15 minutes away
- **Accessibility Support**: Full WCAG 2.1 AA compliance with screen reader support

**Keyboard Navigation**:
- **R**: Manual refresh of meeting data
- **T**: Toggle between renderers
- **L**: Switch to different layout
- **Space**: Quick refresh (same as R key)

**Touch/Mobile Support**:
- **Swipe Left/Right**: Trigger refresh
- **Tap Controls**: Touch-friendly interface elements
- **Double-tap Prevention**: Prevents accidental zoom on mobile devices

**Renderers Available**:
- **html**: Clean interface with subtle shadows and animations
- **rpi**: High-contrast, static design optimized for e-ink displays with no animations
- **compact**: Simplified design for very small displays

**Display Information**:
- **Current/Next Meeting**: Title, time, location, and description (truncated if needed)
- **Countdown Timer**: Large, prominent countdown showing time until meeting starts/ends
- **Coming Up**: Preview of next 3 upcoming meetings
- **Empty State**: Clear messaging when no meetings are scheduled

**Example Usage**:
```bash
# Launch whats-next-view (recommended for small displays)
calendarbot --web --web_layout whats-next-view --renderer rpi

# Standard renderer with animations
calendarbot --web --web_layout whats-next-view --renderer html

# URL parameter switching
# http://<host-ip>:8080/calendar?layout=whats-next-view
```

**Performance Characteristics**:
- **Update Frequency**: 1-second countdown updates, 60-second auto-refresh
- **Bundle Size**: ~15KB CSS, ~20KB JavaScript
- **Memory Usage**: Low resource consumption
- **Display Compatibility**: Optimized for eink, LCD, and OLED displays

## Operational Modes

### Interactive Mode

**Command**: `calendarbot` or `calendarbot --interactive`

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

**Command**: `calendarbot --web`

**Features**:

- Web interface on `http://<host-ip>:8080` with mobile support
- Real-time auto-refresh and navigation controls

**Intermediate Options**:

```bash
calendarbot --web --port 3000       # Custom port
calendarbot --web --auto-open       # Auto-open browser
calendarbot --web --host 0.0.0.0    # Bind to all interfaces
```

### E-Paper Display Mode

**Command**: `calendarbot --epaper`

**Features**:

- Optimized for e-paper displays with hardware auto-detection
- PNG fallback when hardware is not available
- Power-efficient rendering with minimal refreshes

**Options**:

```bash
calendarbot --epaper                # Auto-detect hardware
calendarbot --epaper --rpi-width 480 --rpi-height 800  # Custom dimensions
```

---

## Basic Workflows

### Daily Operation

1. **Interactive Navigation** (Default)
```bash
. venv/bin/activate
calendarbot  # Launch interactive mode
```

2. **Web Interface Viewing**
```bash
. venv/bin/activate
calendarbot --web  # Launch web interface
```

3. **E-Paper Display**
```bash
. venv/bin/activate
calendarbot --epaper  # Launch e-paper mode
```

### Quick Event Refresh

Use Enter (interactive) or manual refresh (web mode) to update calendar view.

---

## Intermediate Operations

### Command Line Options

- **Setup**: `calendarbot --setup`
- **Help**: `calendarbot --help`

**Example**:
```bash
. venv/bin/activate
calendarbot --help  # View all command options
```

---

## Maintenance

**Daily Tasks:**

- Monitor console output for errors
- Verify events display correctly

**Weekly Review:**

- Review logs for issues
- Verify ICS feed connectivity

[⬆️ Back to Top](#table-of-contents)

---

## Troubleshooting

- **Events Not Displaying**:
Verify your ICS URL is correct and accessible.

- **Offline Mode**:
If offline, Calendar Bot serves cached data.

**Log Level Adjustment**:
```bash
export CALENDARBOT_LOG_LEVEL="DEBUG"
. venv/bin/activate
calendarbot --verbose
```

## Advanced Operations

### Testing Modes

**Validation**:
```bash
. venv/bin/activate
calendarbot --test-mode  # Validates system components
```

**Component Testing**:
```bash
calendarbot --test-mode --components cache  # Tests cache only
```

### Performance Monitoring

**Runtime Tracking**:
```bash
. venv/bin/activate
calendarbot --track-runtime  # Enable resource tracking
```

## See Also

- [Setup Guide](SETUP.md)
- [Configuration Wizard](SETUP.md#wizard)
- [Installation Documentation](INSTALL.md)
