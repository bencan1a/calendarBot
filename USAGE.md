# User Guide

**Document Version:** 2.0
**Last Updated:** January 5, 2025
**Application Version:** ICS Calendar Bot v2.0
**Compatible With:** All ICS-compliant calendar systems

This guide covers day-to-day operation of the ICS Calendar Display Bot, including understanding the display output, handling connectivity issues, and basic troubleshooting.

> **Note for Migrating Users**: If you're upgrading from the Microsoft Graph API version, please review the [Migration Guide](MIGRATION.md) for important changes and setup differences.

## Table of Contents

- [Daily Operation](#daily-operation)
- [Execution Modes](#execution-modes)
- [Understanding the Display](#understanding-the-display)
- [Network Connectivity](#network-connectivity)
- [Configuration Management](#configuration-management)
- [Error Recovery](#error-recovery)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

## Daily Operation

### What to Expect

The Calendar Bot runs continuously in the background, automatically:
- **Fetching** your ICS calendar feed every 5 minutes
- **Parsing** calendar events from ICS content
- **Displaying** current and upcoming meetings
- **Caching** events for offline access
- **Handling** network interruptions gracefully

### Normal Operation Indicators

When everything is working correctly, you'll see:
- **Live data indicator** (🌐 Live Data)
- **Recent update timestamp** (Updated: HH:MM)
- **Current events** highlighted with ▶ arrow
- **Upcoming events** listed with times and locations
- **Source status** showing successful ICS feed access

### Passive Monitoring

The system is designed to work without intervention. Simply:
- **Glance at the display** when you need schedule information
- **Trust the automatic updates** every 5 minutes
- **Ignore brief network interruptions** - cached data will be shown
- **Monitor the status indicators** for system health

## Execution Modes

### Daemon Mode (Default)

```bash
python main.py
```

**Purpose**: Continuous background operation
**Features**:
- Automatic refresh every 5 minutes
- Console output with real-time updates
- Signal handling for graceful shutdown
- Persistent operation until stopped

**Use Case**: Primary mode for always-on calendar display

### Interactive Mode

```bash
python main.py --interactive
```

**Purpose**: Manual calendar navigation
**Features**:
- Keyboard-driven date browsing
- Real-time background data updates
- Navigation between past and future dates
- Immediate response to user input

**Keyboard Controls**:
- **Arrow Keys**: Navigate between dates (← Previous day, → Next day)
- **Space**: Jump to today's date
- **ESC**: Exit interactive mode
- **Enter**: Refresh current view

**Use Case**: When you need to browse different dates or explore your schedule

### Test Mode

```bash
python main.py --test-mode
```

**Purpose**: System validation and diagnostics
**Features**:
- ICS feed connectivity testing
- Configuration validation
- Cache system verification
- Quick health check

**Verbose Testing**:
```bash
python main.py --test-mode --verbose
```

**Additional Test Options**:
```bash
# Test specific date range
python main.py --test-mode --date 2024-01-15 --end-date 2024-01-20

# Test specific components
python main.py --test-mode --components ics,cache,display

# Skip cache during testing
python main.py --test-mode --no-cache

# JSON output for automation
python main.py --test-mode --output-format json
```

**Use Case**: Troubleshooting, initial setup validation, automated testing

### Direct ICS Testing

```bash
python test_ics.py
```

**Purpose**: Dedicated ICS feed testing utility
**Features**:
- Direct ICS URL validation
- Authentication testing
- Content parsing verification
- Detailed diagnostic output

**Examples**:
```bash
# Test current configuration
python test_ics.py

# Test specific URL
python test_ics.py --url "https://example.com/calendar.ics"

# Test with authentication
python test_ics.py --url "url" --auth-type basic --username user --password pass

# Test with verbose output
python test_ics.py --url "url" --verbose

# Validate format only
python test_ics.py --url "url" --validate-only
```

## Understanding the Display

### Display Layout Structure

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

• Lunch Meeting
  12:30 - 13:30 | 📍 Restaurant

⏰ LATER TODAY

• Code Review
  14:00 - 15:00
• 1:1 with Manager
  15:30 - 16:00

============================================================
```

### Display Elements Explained

#### Header Section
- **📅 ICS Calendar**: Indicates ICS-based calendar system
- **Date**: Current date in readable format
- **Updated time**: When ICS feed was last fetched and parsed
- **Data source**: 🌐 Live Data or 📱 Cached Data

#### Current Event Section (▶)
- **Event title**: Meeting name from ICS SUMMARY field
- **Time range**: Start and end times with timezone conversion
- **Location**: 📍 Physical location or 💻 Online Meeting from ICS LOCATION
- **Time remaining**: ⏱️ Minutes left in current meeting

#### Next Up Section (📋)
- **Upcoming events**: Next 2-3 meetings chronologically
- **Time and location**: Combined display for space efficiency
- **Priority order**: Sorted by start time from ICS feed

#### Later Today Section (⏰)
- **Additional events**: Remaining meetings for the day
- **Simplified format**: Title and time only to conserve space
- **Event filtering**: Only busy/tentative events from ICS

### Status Indicators

| Indicator | Meaning |
|-----------|---------|
| 🌐 Live Data | Successfully fetched fresh data from ICS feed |
| 📱 Cached Data | Using offline cache due to ICS feed unavailability |
| 📍 Location | Physical meeting location from ICS LOCATION field |
| 💻 Online | Online meeting (detected from location keywords) |
| ▶ Current | Meeting happening right now |
| • Next | Upcoming meetings |
| ⏱️ Time | Time remaining in current meeting |
| 🔔 Alert | Meeting starting soon (within 5 minutes) |

### Event Filtering

The display shows events based on ICS `STATUS` and `TRANSP` fields:

**Displayed Events**:
- **BUSY** - Regular meetings (default if not specified)
- **TENTATIVE** - Meetings marked as tentative

**Filtered Out**:
- **FREE** - Availability blocks
- **TRANSPARENT** - Events marked as "free time"
- **CANCELLED** - Cancelled meetings

## Network Connectivity

### Online Operation

When connected to the internet and ICS feed is accessible:
- ICS feed fetched every 5 minutes
- Calendar events parsed from ICS content
- Status shows "🌐 Live Data"
- HTTP caching headers respected (ETags, Last-Modified)
- All features work normally

### Offline Operation

When internet is unavailable or ICS feed inaccessible:
- Cached calendar data displayed from SQLite database
- Status shows "📱 Cached Data"
- Last successful update time preserved
- System continues with stored information
- Automatic retry attempts continue in background

### Connectivity Recovery

When ICS feed access is restored:
- System automatically detects availability
- Fresh ICS content is fetched and parsed
- Cache updated with new event information
- Display returns to "🌐 Live Data" status
- Seamless transition without user intervention

### ICS Feed Issues Handling

**HTTP Response Codes**:
- **200 OK**: Successful ICS content retrieval
- **304 Not Modified**: Content unchanged (efficient caching)
- **401/403**: Authentication required or credentials invalid
- **404**: ICS feed URL not found
- **500+**: Server-side issues, automatic retry with backoff

**Content Issues**:
- **Invalid ICS Format**: Partial parsing with error reporting
- **Empty Content**: Clear error message and cache fallback
- **Malformed Events**: Skip problematic events, continue with valid ones
- **Timezone Problems**: Automatic timezone detection and conversion

## Configuration Management

### Configuration Hierarchy

Settings are applied in order of precedence:
1. **Command line arguments** (highest priority)
2. **Environment variables** (CALENDARBOT_* prefix)
3. **Configuration file** (config/config.yaml)
4. **Default values** (lowest priority)

### Primary Configuration File

Edit [`config/config.yaml`](config/config.yaml.example):

```yaml
# ICS Calendar Configuration
ics:
  url: "https://outlook.live.com/.../calendar.ics"
  auth_type: "none"  # Options: none, basic, bearer
  verify_ssl: true
  user_agent: "CalendarBot/1.0"
  
  # For Basic Authentication (uncomment if needed)
  # username: "your-username"
  # password: "your-password"
  
  # For Bearer Token (uncomment if needed)  
  # token: "your-bearer-token"

# Application Settings
refresh_interval: 300  # 5 minutes
cache_ttl: 3600       # 1 hour
log_level: "INFO"

# Display Settings
display_enabled: true
display_type: "console"

# Network Settings
request_timeout: 30
max_retries: 3
retry_backoff_factor: 1.5
```

### Environment Variables

Override any setting using environment variables:

```bash
# ICS Configuration
export CALENDARBOT_ICS_URL="https://example.com/calendar.ics"
export CALENDARBOT_ICS_AUTH_TYPE="basic"
export CALENDARBOT_ICS_USERNAME="username"
export CALENDARBOT_ICS_PASSWORD="password"

# Application Settings
export CALENDARBOT_REFRESH_INTERVAL=600  # 10 minutes
export CALENDARBOT_CACHE_TTL=7200        # 2 hours
export CALENDARBOT_LOG_LEVEL="DEBUG"

# Network Settings
export CALENDARBOT_REQUEST_TIMEOUT=60
export CALENDARBOT_MAX_RETRIES=5
```

### Common Configuration Adjustments

**Change refresh frequency**:
```yaml
refresh_interval: 600  # 10 minutes instead of 5
```

**Extend cache duration**:
```yaml
cache_ttl: 7200  # 2 hours instead of 1
```

**Enable debug logging**:
```yaml
log_level: "DEBUG"
log_file: "calendarbot.log"
```

**Disable SSL verification** (not recommended):
```yaml
ics:
  verify_ssl: false
```

**Increase timeout for slow servers**:
```yaml
request_timeout: 60  # 1 minute timeout
```

### Multiple Calendar Sources

Future support for multiple ICS feeds:

```yaml
# Multiple ICS Sources (planned feature)
sources:
  - name: "Work Calendar"
    url: "https://company.com/work-calendar.ics"
    auth_type: "basic"
    username: "work-user"
    password: "work-pass"
    
  - name: "Personal Calendar"
    url: "https://personal.com/calendar.ics"
    auth_type: "none"
```

## Error Recovery

### Automatic Recovery

The system includes automatic recovery for:
- **Network connectivity** - Exponential backoff retry logic
- **ICS feed errors** - Fallback to cached data
- **HTTP timeouts** - Configurable timeout with retry
- **Parsing errors** - Partial recovery and error reporting
- **Cache corruption** - Database recreation if needed

### Error Display Modes

When errors occur, the display adapts based on error type:

**Network Issues**:
```
============================================================
📅 ICS CALENDAR - Monday, January 15
============================================================

⚠️  CONNECTION ISSUE

   Cannot reach ICS feed - Using Cached Data

📱 SHOWING CACHED DATA
------------------------------------------------------------
• Team Standup
  10:00 - 10:30
  📍 Conference Room A

============================================================
```

**Authentication Problems**:
```
============================================================
📅 ICS CALENDAR - Monday, January 15
============================================================

🔒 AUTHENTICATION REQUIRED

   ICS feed requires credentials
   Check configuration for auth_type, username, password

============================================================
```

**ICS Parsing Issues**:
```
============================================================
📅 ICS CALENDAR - Monday, January 15
============================================================

📄 PARTIAL DATA

   ICS parsing completed with warnings
   Showing 3 of 5 events (2 events had errors)

• Team Standup
  10:00 - 10:30

============================================================
```

### Manual Recovery Actions

**Force refresh** (restart application):
```bash
# If running manually
Ctrl+C
python main.py

# If running as service
sudo systemctl restart calendarbot
```

**Clear cache** (for persistent data issues):
```bash
# Remove cached calendar data
rm ~/.local/share/calendarbot/calendar_cache.db
python main.py
```

**Test ICS feed directly**:
```bash
# Validate ICS feed
python test_ics.py --url "your-ics-url" --verbose

# Test authentication
python test_ics.py --url "url" --auth-type basic --username user --password pass
```

**Reset configuration**:
```bash
# Backup current config
cp config/config.yaml config/config.yaml.backup

# Reset to example
cp config/config.yaml.example config/config.yaml
# Edit with your settings
```

## Troubleshooting

### ICS Feed Issues

**Problem**: "Cannot connect to ICS feed"
```bash
# Test ICS URL directly
curl -I "your-ics-url"

# Test with authentication
curl -u "username:password" "your-ics-url"

# Use test utility
python test_ics.py --url "your-ics-url" --verbose
```

**Problem**: "Invalid ICS format" error
```bash
# Download and examine ICS content
curl "your-ics-url" | head -20

# Should start with: BEGIN:VCALENDAR
# Should contain: VERSION:2.0
# Should have: BEGIN:VEVENT entries

# Validate with test utility
python test_ics.py --url "your-ics-url" --validate-only
```

**Problem**: Events not showing up
- **Check event status**: Ensure events are marked as "BUSY" or "TENTATIVE"
- **Verify date range**: ICS events might be outside current date window
- **Check timezone**: Verify system timezone matches calendar timezone
- **Test parsing**: Use `python test_ics.py --verbose` to see parsed events

### Authentication Issues

**Problem**: HTTP 401/403 errors
```bash
# Test credentials
python test_ics.py --url "url" --auth-type basic --username "user" --password "pass"

# Check URL accessibility
curl -u "username:password" -I "your-ics-url"
```

**Problem**: Bearer token not working
```bash
# Test token format
curl -H "Authorization: Bearer your-token" "your-ics-url"

# Verify token in configuration
grep -A 5 "ics:" config/config.yaml
```

### Configuration Issues

**Problem**: "ICS URL configuration is required" error
```bash
# Check configuration
grep -A 10 "ics:" config/config.yaml

# Verify environment variable
echo $CALENDARBOT_ICS_URL

# Test configuration loading
python3 -c "from config.settings import settings; print(f'ICS URL: {settings.ics_url}')"
```

**Problem**: YAML syntax errors
```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('config/config.yaml'))"

# Check for common issues: indentation, quotes, special characters
```

### Network Issues

**Problem**: SSL certificate errors
```yaml
# Temporarily disable SSL verification (not recommended for production)
ics:
  verify_ssl: false
```

**Problem**: DNS resolution failures
```bash
# Test DNS resolution
nslookup your-calendar-server.com

# Test connectivity
ping your-calendar-server.com

# Check network configuration
cat /etc/resolv.conf
```

**Problem**: Timeout errors
```yaml
# Increase timeout in configuration
request_timeout: 60  # 1 minute

# Reduce retry attempts if server is slow
max_retries: 2
```

### Performance Issues

**Problem**: High memory usage
```bash
# Check cache database size
ls -lh ~/.local/share/calendarbot/calendar_cache.db

# Clear cache if too large
rm ~/.local/share/calendarbot/calendar_cache.db

# Reduce cache TTL
# In config.yaml: cache_ttl: 1800  # 30 minutes
```

**Problem**: Frequent network requests
```yaml
# Increase refresh interval
refresh_interval: 900  # 15 minutes

# Enable HTTP caching
ics:
  enable_cache: true
```

### Interactive Mode Issues

**Problem**: Keyboard input not working
```bash
# Test interactive mode
python test_interactive.py

# Check terminal compatibility
echo $TERM

# Try different terminal
# Interactive mode works best with standard terminals
```

**Problem**: Navigation not responding
- **Check terminal size**: Ensure terminal is large enough for display
- **Verify key bindings**: Arrow keys, Space, ESC should work
- **Test background updates**: Data should refresh automatically

## Maintenance

### Regular Tasks

**Daily**:
- Monitor console output for errors
- Verify current events are displaying correctly
- Check that timestamps are recent (within 5 minutes)

**Weekly**:
- Review application logs for recurring issues
- Verify ICS feed accessibility
- Check cache database size and performance
- Confirm system time accuracy

**Monthly**:
- Update Python dependencies if needed
- Review and rotate log files
- Check available storage space
- Validate configuration settings

### Health Monitoring

**Signs of healthy operation**:
- ✅ Regular "Successfully fetched and cached X events" messages
- ✅ "🌐 Live Data" indicator in display
- ✅ Recent update timestamps (within 5 minutes)
- ✅ No error messages in logs
- ✅ Events match what's in your calendar application

**Signs requiring attention**:
- ⚠️ Persistent "📱 Cached Data" indicator
- ⚠️ Old update timestamps (> 10 minutes)
- ⚠️ HTTP authentication errors
- ⚠️ ICS parsing warnings
- ⚠️ Missing events that should be visible

### Log Management

**View recent activity**:
```bash
# If using systemd service
sudo journalctl -u calendarbot.service -f

# If running manually with file logging
tail -f calendarbot.log

# Check for specific errors
grep -i error calendarbot.log
```

**Enable detailed logging**:
```yaml
# In config.yaml
log_level: "DEBUG"
log_file: "calendarbot.log"
```

**Log rotation** (prevent log files from growing too large):
```bash
# Manual log rotation
mv calendarbot.log calendarbot.log.old
# Application will create new log file

# Or use logrotate
sudo nano /etc/logrotate.d/calendarbot
```

### Backup and Recovery

**Configuration backup**:
```bash
# Backup configuration
cp config/config.yaml ~/calendarbot-config-backup.yaml

# Backup cache (optional)
cp ~/.local/share/calendarbot/calendar_cache.db ~/calendarbot-cache-backup.db
```

**Recovery procedures**:
```bash
# Restore configuration
cp ~/calendarbot-config-backup.yaml config/config.yaml

# Reset cache (will rebuild automatically)
rm ~/.local/share/calendarbot/calendar_cache.db

# Restart application
python main.py
```

### Getting Help

When troubleshooting issues:

1. **Check this guide** for common solutions
2. **Run test mode**: `python main.py --test-mode --verbose`
3. **Test ICS feed directly**: `python test_ics.py --url "your-url" --verbose`
4. **Review logs** for specific error messages
5. **Verify configuration** syntax and values
6. **Test with minimal settings** to isolate issues

For additional support:
- **Installation issues**: See [INSTALL.md](INSTALL.md)
- **Architecture questions**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Interactive mode help**: See [INTERACTIVE_NAVIGATION.md](INTERACTIVE_NAVIGATION.md)
- **Bug reports**: Create GitHub issue with logs and configuration (redact sensitive URLs)

---

## Summary

The ICS Calendar Display Bot provides a robust, low-maintenance calendar display solution with:

### Core Strengths
- **Universal Compatibility**: Works with any ICS-compliant calendar service
- **Automatic Recovery**: Built-in retry logic and graceful error handling
- **Offline Resilience**: Comprehensive caching for network outages
- **Resource Efficiency**: Optimized for Raspberry Pi and low-power operation
- **User-Friendly**: Clear status indicators and intuitive operation

### Maintenance Philosophy

The system is designed for **"set it and forget it"** operation:
- **Automatic Updates**: Calendar data refreshes every 5 minutes
- **Self-Healing**: Network issues and errors resolve automatically
- **Minimal Intervention**: Most problems are handled transparently
- **Clear Indicators**: Status displays show exactly what's happening

### When to Take Action

You should only need to intervene when:
- ❗ **Configuration Changes**: New calendar URL or authentication requirements
- ❗ **Persistent Offline Mode**: "📱 Cached Data" shown for > 30 minutes
- ❗ **Missing Events**: Calendar events not appearing as expected
- ❗ **Performance Issues**: High resource usage or slow response times

### Quick Health Check

The system is operating correctly when you see:
- ✅ **"🌐 Live Data"** status indicator
- ✅ **Recent timestamps** (within 5-10 minutes)
- ✅ **Current events** matching your calendar
- ✅ **Automatic updates** every 5 minutes
- ✅ **No error messages** in console output

---

**🔧 Need Help?** Check the troubleshooting sections above or see the [Installation Guide](INSTALL.md) for system-level issues.

**🏗️ Want Technical Details?** Review the [Architecture Guide](ARCHITECTURE.md) for system design information.

**📈 Upgrading?** See the [Migration Guide](MIGRATION.md) for Graph API to ICS transition steps.

---

*User Guide v2.0 - Last updated January 5, 2025*
*The ICS Calendar Display Bot is designed for reliable, low-maintenance operation with automatic error recovery.*