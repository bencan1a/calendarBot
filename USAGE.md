# Usage Guide

This guide covers daily operation and all operational modes of Calendar Bot.

## Table of Contents

- [Operational Modes](#operational-modes)
- [Command Line Options](#command-line-options)
- [Understanding the Display](#understanding-the-display)
- [Network Connectivity](#network-connectivity)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

## Operational Modes

Calendar Bot provides multiple operational modes for different use cases.

### Interactive Mode (Default)

**Command**: `python main.py` or `python main.py --interactive`

**Purpose**: Real-time calendar navigation with keyboard controls

**Features**:
- Live calendar display with automatic updates
- Keyboard navigation between dates
- Real-time background data fetching
- Split display with calendar and log output

**Keyboard Controls**:
- **Arrow Keys**: Navigate between dates (← Previous day, → Next day)
- **Space**: Jump to today's date
- **ESC**: Exit interactive mode
- **Enter**: Refresh current view

### Web Interface Mode

**Command**: `python main.py --web`

**Purpose**: Browser-based calendar viewing

**Features**:
- Web interface on `http://localhost:8080`
- Mobile-friendly responsive design
- Real-time auto-refresh
- Navigation controls in browser

**Options**:
```bash
python main.py --web --port 3000        # Custom port
python main.py --web --auto-open        # Auto-open browser
python main.py --web --host 0.0.0.0     # Bind to all interfaces
```

### Test Mode

**Command**: `python main.py --test-mode`

**Purpose**: System validation and diagnostics

**Features**:
- Configuration validation
- ICS feed connectivity testing
- Authentication verification
- Cache system testing

**Options**:
```bash
python main.py --test-mode --verbose     # Detailed output
python main.py --test-mode --date 2024-01-15  # Specific date
python main.py --test-mode --components auth,api,cache  # Specific components
```

### Setup Mode

**Command**: `python main.py --setup`

**Purpose**: Configuration wizard for setup

**Features**:
- Interactive configuration wizard
- Service templates for popular calendars
- Real-time connection testing
- Authentication setup guidance

## Command Line Options

### Setup and Configuration
```bash
--setup                    # Run configuration wizard
--backup                   # Backup current configuration
--restore FILE             # Restore from backup
--list-backups            # List available backups
```

### Operational Modes
```bash
--interactive, -i         # Interactive navigation mode
--web, -w                 # Web server mode
--test-mode              # Validation and testing mode
```

### Web Server Options
```bash
--port PORT              # Web server port (default: 8080)
--host HOST              # Web server host (default: 0.0.0.0)
--auto-open              # Auto-open browser
```

### Testing Options
```bash
--verbose, -v            # Enable verbose output
--date DATE              # Test specific date (YYYY-MM-DD)
--components LIST        # Test specific components
--output-format FORMAT   # Output format: console or json
```

## Understanding the Display

### Display Layout

```
============================================================
📅 ICS CALENDAR - Monday, January 15
============================================================
Updated: 10:05 | 🌐 Live Data

▶ CURRENT EVENT

  Team Standup
  10:00 - 10:30
  📍 Conference Room A
  ⏱️  25 minutes remaining

📋 NEXT UP

• Project Review
  11:00 - 12:00 | 📍 Online

============================================================
```

### Status Indicators

| Indicator | Meaning |
|-----------|---------|
| 🌐 Live Data | Fresh data from ICS feed |
| 📱 Cached Data | Using offline cache |
| 📍 Location | Physical meeting location |
| 💻 Online | Online/virtual meeting |
| ▶ Current | Meeting happening now |
| • Next | Upcoming meetings |
| ⏱️ Time | Time remaining |

## Network Connectivity

### Online Operation
- ICS feed fetched every 5 minutes
- Events cached in SQLite database
- Status shows "🌐 Live Data"
- HTTP caching headers respected

### Offline Operation
- Cached data displayed from local database
- Status shows "📱 Cached Data"
- Automatic retry attempts in background
- Graceful degradation without restart

## Troubleshooting

### Common Issues

#### Events Not Displaying
```bash
# Test ICS feed
python test_ics.py --url "$CALENDARBOT_ICS_URL" --verbose

# Check event filtering
python main.py --test-mode --verbose
```

#### Connection Issues
```bash
# Test URL accessibility
curl -I "$CALENDARBOT_ICS_URL"

# Test with authentication
python test_ics.py --url "url" --auth-type basic --username "user" --password "pass"
```

#### Authentication Problems
```bash
# Verify credentials
curl -u "username:password" "$CALENDARBOT_ICS_URL"

# Check configuration
grep -A 5 "ics:" config/config.yaml
```

### Debug Mode

Enable detailed logging:
```bash
export CALENDARBOT_LOG_LEVEL="DEBUG"
python main.py --verbose
```

## Maintenance

### Regular Tasks

**Daily**:
- Monitor console output for errors
- Verify events display correctly
- Check update timestamps are recent

**Weekly**:
- Review logs for recurring issues
- Test ICS feed accessibility
- Verify system time accuracy

### Health Monitoring

**Healthy Operation**:
- ✅ "🌐 Live Data" indicator
- ✅ Recent update timestamps
- ✅ Events match calendar app
- ✅ No error messages

**Warning Signs**:
- ⚠️ Persistent "📱 Cached Data"
- ⚠️ Old update timestamps
- ⚠️ Authentication errors
- ⚠️ Missing events

### Backup and Recovery

```bash
# Backup configuration
python main.py --backup

# Clear cache if needed
rm ~/.local/share/calendarbot/calendar_cache.db

# Reset configuration
python main.py --setup
```

---

**Need Help?**

1. Run diagnostics: `python main.py --test-mode --verbose`
2. Test ICS feed: `python test_ics.py --url "your-url" --verbose`
3. Check [INSTALL.md](INSTALL.md) for setup issues
4. See [SETUP.md](SETUP.md) for configuration help

Calendar Bot is designed for reliable, low-maintenance operation with comprehensive error recovery.
