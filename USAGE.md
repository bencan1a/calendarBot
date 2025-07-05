# User Guide

This guide covers day-to-day operation of the Microsoft 365 Calendar Display Bot, including understanding the display output, handling connectivity issues, and basic troubleshooting.

## Table of Contents

- [Daily Operation](#daily-operation)
- [Understanding the Display](#understanding-the-display)
- [Network Connectivity](#network-connectivity)
- [Authentication Management](#authentication-management)
- [Error Recovery](#error-recovery)
- [Configuration Adjustments](#configuration-adjustments)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

## Daily Operation

### What to Expect

The Calendar Bot runs continuously in the background, automatically:
- **Fetching** your calendar events every 5 minutes
- **Displaying** current and upcoming meetings
- **Caching** events for offline access
- **Refreshing** authentication tokens as needed

### Normal Operation Indicators

When everything is working correctly, you'll see:
- **Live data indicator** (🌐 Live Data)
- **Recent update timestamp** (Updated: HH:MM)
- **Current events** highlighted with ▶ arrow
- **Upcoming events** listed with times and locations

### Passive Monitoring

The system is designed to work without intervention. Simply:
- **Glance at the display** when you need schedule information
- **Trust the automatic updates** every 5 minutes
- **Ignore brief network interruptions** - cached data will be shown

## Understanding the Display

### Display Layout Structure

```
============================================================
📅 MICROSOFT 365 CALENDAR - Monday, January 15
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
- **📅 Date**: Current date in readable format
- **Updated time**: When calendar data was last refreshed
- **Data source**: 🌐 Live Data or 📱 Cached Data

#### Current Event Section (▶)
- **Event title**: Meeting name
- **Time range**: Start and end times
- **Location**: 📍 Physical location or 💻 Online Meeting
- **Time remaining**: ⏱️ Minutes left in current meeting

#### Next Up Section (📋)
- **Upcoming events**: Next 2-3 meetings
- **Time and location**: Combined on one line
- **Priority order**: Sorted by start time

#### Later Today Section (⏰)
- **Additional events**: Remaining meetings for the day
- **Simplified format**: Title and time only to save space

### Status Indicators

| Indicator | Meaning |
|-----------|---------|
| 🌐 Live Data | Connected to Microsoft 365, showing real-time data |
| 📱 Cached Data | Using offline cache due to connectivity issues |
| 📍 Location | Physical meeting location |
| 💻 Online | Microsoft Teams or other online meeting |
| ▶ Current | Meeting happening right now |
| • Next | Upcoming meetings |
| ⏱️ Time | Time remaining in current meeting |
| 🔔 Alert | Meeting starting soon (within 5 minutes) |

### Event Filtering

The display only shows events marked as:
- **Busy** - Regular meetings you should attend
- **Tentative** - Meetings you might attend

Events filtered out:
- **Free** - Availability blocks
- **Out of Office** - Time off periods
- **Working Elsewhere** - Location indicators

## Network Connectivity

### Online Operation

When connected to the internet:
- Calendar data refreshes every 5 minutes
- Authentication tokens refresh automatically
- Status shows "🌐 Live Data"
- All features work normally

### Offline Operation

When internet is unavailable:
- Cached calendar data is displayed
- Status shows "📱 Cached Data"
- Last successful update time is preserved
- System continues to function with stored information

### Connectivity Recovery

When connection is restored:
- System automatically detects connectivity
- Fresh calendar data is fetched
- Cache is updated with new information
- Display returns to "🌐 Live Data" status

### Network Issues Handling

The system handles common network problems:

**Temporary Outages**:
- Automatic retry with exponential backoff
- No user intervention required
- Cached data displayed during outages

**Rate Limiting**:
- Respects Microsoft Graph API limits
- Automatically adjusts polling frequency
- Prevents authentication token exhaustion

**DNS/Firewall Issues**:
- Clear error messages displayed
- Maintains functionality with cached data
- Logs detailed error information for diagnosis

## Authentication Management

### Token Lifecycle

Authentication tokens are managed automatically:
- **Initial Setup**: One-time device code flow authentication
- **Automatic Renewal**: Tokens refresh 5 minutes before expiration
- **Secure Storage**: AES-256 encrypted token storage
- **Error Recovery**: Automatic re-authentication when needed

### Re-authentication Triggers

You may need to re-authenticate if:
- Tokens are corrupted or manually deleted
- Microsoft 365 password is changed
- Account security policies require re-approval
- Application permissions are revoked

### Re-authentication Process

When re-authentication is required:

1. **Application prompts** with device code:
```
===============================================================
🔐 MICROSOFT 365 AUTHENTICATION REQUIRED
===============================================================

To access your calendar, please complete authentication:

1. Visit: https://microsoft.com/devicelogin
2. Enter code: A1B2C3D4

Waiting for authentication...
===============================================================
```

2. **Complete authentication**:
   - Open web browser on any device
   - Navigate to https://microsoft.com/devicelogin
   - Enter the displayed code
   - Sign in with your Microsoft 365 account
   - Grant calendar permissions

3. **Automatic continuation**:
   - Application detects successful authentication
   - Tokens are securely stored
   - Normal operation resumes

### Authentication Troubleshooting

**Problem**: Repeated authentication requests
- **Cause**: Token storage issues or permission changes
- **Solution**: Clear stored tokens and re-authenticate once

**Problem**: "Invalid client" errors
- **Cause**: Azure app registration configuration issues
- **Solution**: Verify client ID and app registration settings

## Error Recovery

### Automatic Recovery

The system includes automatic recovery for:
- **Network connectivity** - Retry with exponential backoff
- **API rate limiting** - Respect rate limits and wait
- **Token expiration** - Automatic token refresh
- **Temporary service outages** - Fallback to cached data

### Error Display

When errors occur, the display shows:

```
============================================================
📅 MICROSOFT 365 CALENDAR - Monday, January 15
============================================================

⚠️  CONNECTION ISSUE

   Network Issue - Using Cached Data

📱 SHOWING CACHED DATA
------------------------------------------------------------
• Team Standup
  10:00 - 10:30
  📍 Conference Room A

============================================================
```

### Manual Recovery Actions

**Force refresh** (if running manually):
```bash
# Stop and restart the application
Ctrl+C
python main.py
```

**Clear authentication** (for persistent auth issues):
```bash
# Remove stored tokens
rm ~/.config/calendarbot/tokens.enc
python main.py
# Follow re-authentication prompts
```

**Clear cache** (for stale data issues):
```bash
# Remove cached calendar data
rm ~/.local/share/calendarbot/calendar_cache.db
python main.py
```

## Configuration Adjustments

### Common Configuration Changes

Edit [`config/config.yaml`](config/config.yaml.example) for these adjustments:

**Refresh frequency**:
```yaml
refresh_interval: 600  # 10 minutes instead of 5
```

**Cache duration**:
```yaml
cache_ttl: 7200  # 2 hours instead of 1
```

**Logging level**:
```yaml
log_level: "DEBUG"  # More detailed logs
log_file: "calendarbot.log"  # Enable file logging
```

**Display settings**:
```yaml
display_enabled: false  # Disable display output
display_type: "console"  # Console output type
```

### Environment Variable Overrides

Override settings without editing files:

```bash
# Temporary changes
export CALENDARBOT_REFRESH_INTERVAL=600
export CALENDARBOT_LOG_LEVEL="DEBUG"
python main.py

# Permanent changes (add to ~/.bashrc)
echo 'export CALENDARBOT_REFRESH_INTERVAL=600' >> ~/.bashrc
source ~/.bashrc
```

### Configuration Validation

Test configuration changes:

```bash
# Validate configuration syntax
python3 -c "from config.settings import settings; print('Config valid')"

# Test with new settings
python main.py
# Ctrl+C to stop after verifying changes work
```

## Troubleshooting

### Display Issues

**Problem**: No calendar events shown
- **Check**: Verify you have events in your Microsoft 365 calendar
- **Check**: Ensure events are marked as "Busy" or "Tentative"
- **Action**: View calendar in Outlook to confirm events exist

**Problem**: Events not updating
- **Check**: Look for "🌐 Live Data" vs "📱 Cached Data" indicator
- **Check**: Verify network connectivity
- **Action**: Wait for next refresh cycle (up to 5 minutes)

**Problem**: Incorrect times displayed
- **Check**: System timezone settings (`timedatectl status`)
- **Check**: Calendar timezone in Microsoft 365
- **Action**: Synchronize system time (`sudo ntpdate -s time.nist.gov`)

### Authentication Issues

**Problem**: Constant re-authentication requests
- **Check**: Token file permissions (`ls -la ~/.config/calendarbot/`)
- **Check**: Available disk space (`df -h`)
- **Action**: Clear tokens and re-authenticate once

**Problem**: "Permissions insufficient" errors
- **Check**: Azure app registration has Calendar.Read permission
- **Check**: User has access to calendar being queried
- **Action**: Re-grant permissions through Azure portal

### Performance Issues

**Problem**: High CPU or memory usage
- **Check**: Multiple instances running (`ps aux | grep python`)
- **Check**: System resources (`htop` or `top`)
- **Action**: Increase refresh interval to reduce API calls

**Problem**: Slow response or timeouts
- **Check**: Network latency to Microsoft services
- **Check**: System load and available memory
- **Action**: Increase `request_timeout` in configuration

### Data Issues

**Problem**: Missing recent meetings
- **Check**: Meeting time zone vs system time zone
- **Check**: Meeting status (ensure not marked as "Free")
- **Action**: Verify events visible in Outlook web app

**Problem**: Duplicate events displayed
- **Check**: Cache corruption (`rm ~/.local/share/calendarbot/calendar_cache.db`)
- **Check**: Multiple calendar sources syncing
- **Action**: Restart application after clearing cache

## Maintenance

### Regular Tasks

**Weekly**:
- Check application logs for errors
- Verify system time accuracy
- Confirm calendar synchronization

**Monthly**:
- Review authentication token status
- Clean old log files if file logging enabled
- Check available storage space

**As Needed**:
- Update configuration for schedule changes
- Re-authenticate if password changed
- Restart application after system updates

### Log Monitoring

**View recent activity**:
```bash
# If using systemd service
sudo journalctl -u calendarbot.service -f

# If running manually with file logging
tail -f calendarbot.log
```

**Check for errors**:
```bash
# Search for error messages
sudo journalctl -u calendarbot.service | grep -i error

# Check last 24 hours of logs
sudo journalctl -u calendarbot.service --since="24 hours ago"
```

### Health Indicators

Signs of healthy operation:
- ✅ Regular "Successfully fetched and cached X events" messages
- ✅ Periodic "Token refreshed successfully" entries
- ✅ No error messages in recent logs
- ✅ Display shows current timestamp and live data

Signs requiring attention:
- ⚠️ Repeated authentication failures
- ⚠️ Network timeout errors
- ⚠️ High resource usage warnings
- ⚠️ Cache corruption errors

### Getting Help

When troubleshooting issues:

1. **Check this guide** for common solutions
2. **Review logs** for specific error messages
3. **Test basic connectivity** to Microsoft services
4. **Verify configuration** syntax and values
5. **Try minimal configuration** to isolate issues

For additional support:
- **Installation issues**: See [INSTALL.md](INSTALL.md)
- **Deployment problems**: See [DEPLOY.md](DEPLOY.md)
- **Development questions**: See [DEVELOPMENT.md](DEVELOPMENT.md)
- **Bug reports**: Create GitHub issue with logs and configuration

---

**Normal operation requires minimal user intervention.** The system is designed to work reliably in the background while providing useful calendar information at a glance.