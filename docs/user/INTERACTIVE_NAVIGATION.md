# Interactive Date Navigation for CalendarBot

## Overview

This document describes the interactive date navigation feature implemented for CalendarBot, allowing users to navigate through dates with arrow keys and view events for any selected day.

## Features

### Navigation Controls
- **← (Left Arrow)**: Navigate to previous day
- **→ (Right Arrow)**: Navigate to next day
- **Space**: Jump to today
- **Home**: Jump to start of current week (Monday)
- **End**: Jump to end of current week (Sunday)
- **ESC**: Exit interactive mode

### Visual Indicators
- **TODAY** prefix when viewing current date
- **Relative descriptions**: Tomorrow, Yesterday, 3 days ago, etc.
- **Navigation status bar** with current controls
- **Date selection highlight** in header

### Background Operations
- **Independent data fetching**: ICS calendar data continues to refresh in background
- **Cache integration**: Events displayed from local SQLite cache
- **Real-time updates**: Display refreshes when new data becomes available

## Architecture

### Components

#### 1. Navigation State Management (`calendarbot/ui/navigation.py`)
```python
class NavigationState:
    def __init__(self):
        self.selected_date = date.today()

    def navigate_forward(self, days: int = 1)
    def navigate_backward(self, days: int = 1)
    def jump_to_today(self)
    def jump_to_start_of_week(self)
    def jump_to_end_of_week(self)
    def get_display_date(self) -> str
    def is_today(self) -> bool
```

#### 2. Keyboard Input Handling (`calendarbot/ui/keyboard.py`)
```python
class KeyboardHandler:
    def register_key_handler(self, key_code: KeyCode, callback)
    def start_listening(self) -> None
    def stop_listening(self) -> None
    def get_help_text(self) -> str
```

**Cross-platform support**:
- Unix systems: Uses `termios` for raw keyboard input
- Windows systems: Uses `msvcrt` for keyboard capture

#### 3. Interactive Controller (`calendarbot/ui/interactive.py`)
```python
class InteractiveController:
    async def run(self) -> None
    async def _background_update_loop(self) -> None
    def _setup_keyboard_handlers(self) -> None
    def _refresh_display(self) -> None
```

#### 4. Enhanced Display (`calendarbot/display/console_renderer.py`)
- Interactive mode detection
- Selected date display in header
- Navigation help status bar
- Visual differentiation for "TODAY" vs other dates

## Usage

### Starting Interactive Mode
```bash
calendarbot --interactive
```

### Navigation Examples
1. **View tomorrow's events**: Press → (right arrow)
2. **Go back to yesterday**: Press ← (left arrow)
3. **Jump to today**: Press Space
4. **See start of week**: Press Home
5. **Exit navigation**: Press ESC

### Display Format
```
============================================================
📅 ICS CALENDAR DISPLAY - TODAY - Saturday, July 05
============================================================
Updated: 06:12 | 🌐 Live Data | 📶 Online
------------------------------------------------------------
← → Navigate | Space: Today | ESC: Exit
------------------------------------------------------------

▶ CURRENT EVENT

• Team Meeting
  09:00 - 10:00 (60min)
  📍 Conference Room A
  ⏱️  45 minutes remaining

📋 NEXT UP

• Project Review
  14:00 - 15:00 | 💻 Online
  ⏰ In 7 hours
```

## Implementation Details

### Date Navigation Logic
- **Relative descriptions**: Automatically generated based on date difference
- **Week boundaries**: Monday = start, Sunday = end
- **Date arithmetic**: Handles month/year boundaries correctly

### Background Data Fetching
- **Decoupled operation**: Data fetching runs independently of UI navigation
- **Cache integration**: Events retrieved from SQLite database by date range
- **Live updates**: Display refreshes when cache is updated

### Keyboard Input Processing
- **Raw input mode**: Captures keys without Enter requirement
- **Signal handling**: Graceful cleanup on Ctrl+C
- **Platform detection**: Automatic selection of appropriate input method

### Memory Management
- **Async tasks**: Proper cleanup of background tasks
- **Resource cleanup**: Terminal settings restored on exit
- **Exception handling**: Graceful degradation on errors

## Testing

### Component Tests
Run the test suite to verify all components:
```bash
pytest tests/unit/ui/
```

### Manual Testing
1. **Start interactive mode**: `calendarbot --interactive`
2. **Test navigation**: Use arrow keys to move between dates
3. **Test today jump**: Press Space to return to current date
4. **Test week navigation**: Use Home/End keys
5. **Test exit**: Press ESC to return to normal mode

### Expected Behavior
- ✅ Arrow keys change displayed date immediately
- ✅ Space key always returns to current date
- ✅ Date header updates with relative descriptions
- ✅ Navigation help shows available controls
- ✅ Background data fetching continues independently
- ✅ ESC key exits cleanly back to normal operation

## Error Handling

### Common Issues
1. **Terminal compatibility**: Falls back to basic input if advanced features unavailable
2. **Authentication required**: Prompts for ICS authentication if configured
3. **Network issues**: Continues with cached data, shows connection status
4. **Keyboard interrupt**: Graceful cleanup and exit

### Debugging
- Enable debug logging: Set `CALENDARBOT_LOG_LEVEL=DEBUG` in environment
- Check cache status: Events loaded from SQLite database
- Verify authentication: Ensure ICS authentication credentials are valid

## Architecture Benefits

### Separation of Concerns
- **Navigation logic**: Independent of data fetching
- **Display rendering**: Decoupled from keyboard input
- **Cache management**: Isolated from UI components

### Scalability
- **Plugin architecture**: Easy to add new navigation controls
- **Event handling**: Extensible keyboard command system
- **Display modes**: Support for different output formats

### Maintainability
- **Clear interfaces**: Well-defined component boundaries
- **Error isolation**: Failures in one component don't break others
- **Testing support**: Each component can be tested independently

## Future Enhancements

### Potential Features
- **Date picker overlay**: Calendar widget for date selection
- **Time range navigation**: Jump by weeks/months
- **Filter controls**: Show only specific event types
- **Export functionality**: Save displayed events to file
- **Multi-calendar support**: Navigate between different calendars

### Performance Improvements
- **Lazy loading**: Load events only for displayed date
- **Cache optimization**: Pre-fetch adjacent dates
- **Display caching**: Avoid re-rendering unchanged content

## Conclusion

The interactive date navigation implementation provides a complete solution for browsing calendar events across different dates while maintaining background data synchronization. The architecture ensures clean separation between navigation, data fetching, and display components, making the system maintainable and extensible.
