# Migration Guide: Microsoft Graph API to ICS Calendar System

**Document Version:** 1.0  
**Last Updated:** January 5, 2025  
**Migration Path:** Graph API v1.0 → ICS Calendar v2.0

## Overview

This guide provides step-by-step instructions for migrating from the previous Microsoft Graph API implementation to the new ICS-based calendar system. The ICS approach provides universal calendar compatibility, simplified setup, and enhanced privacy.

## Migration Benefits

### Why Migrate to ICS?

- ✅ **Universal Compatibility**: Works with any calendar service (Outlook, Google, Apple, CalDAV)
- ✅ **Simplified Setup**: No Azure app registration or complex authentication
- ✅ **No API Quotas**: Unlimited access to your calendar data
- ✅ **Enhanced Privacy**: Direct calendar access without third-party APIs
- ✅ **Better Reliability**: No dependency on Microsoft Graph API availability
- ✅ **Easier Maintenance**: Standard ICS format with broad support

### Breaking Changes from Graph API Version

| Feature | Graph API (Old) | ICS System (New) | Impact |
|---------|-----------------|------------------|---------|
| Authentication | Azure Client ID/Secret | ICS URL (usually public) | 🔴 **Breaking**: Remove Azure config |
| Calendar Access | REST API calls | Direct ICS feed | 🟢 **Improved**: Simpler access |
| Event Filtering | Graph API filters | ICS TRANSP/STATUS parsing | 🟡 **Different**: New filtering logic |
| Rate Limiting | Microsoft quotas | HTTP politeness | 🟢 **Improved**: No hard limits |
| Offline Support | API cache only | Full ICS cache | 🟢 **Improved**: Better offline mode |

## Pre-Migration Checklist

### 1. Backup Current Configuration
```bash
# Backup your current configuration
cp config/config.yaml config/config.yaml.graph-backup
cp -r ~/.local/share/calendarbot ~/.local/share/calendarbot-graph-backup
```

### 2. Document Current Settings
Record your current Microsoft Graph configuration:
- Azure Tenant ID
- Application (Client) ID  
- Calendar ID or email address
- Refresh intervals and display settings

### 3. Obtain ICS Calendar URL

#### For Microsoft Outlook/Office 365:
1. Go to Outlook on the web (outlook.live.com or outlook.office365.com)
2. Navigate to Calendar → Settings (gear icon) → View all Outlook settings
3. Go to Calendar → Shared calendars
4. Under "Publish a calendar":
   - Select your calendar
   - Set permissions to "Can view when I'm busy"
   - Click **Publish**
5. Copy the ICS link (ends with `.ics`)

#### For Google Calendar:
1. Open Google Calendar (calendar.google.com)
2. Click three dots next to your calendar → "Settings and sharing"
3. Scroll to "Access permissions and export"
4. Copy the "Secret address in iCal format"

#### For Other Services:
- **Apple iCloud**: Calendar → Share → Public Calendar → Copy URL
- **CalDAV Servers**: Usually `https://server.com/path/calendar.ics?export`

## Step-by-Step Migration Process

### Step 1: Stop Current Application

```bash
# If running as systemd service
sudo systemctl stop calendarbot

# If running manually
# Press Ctrl+C to stop the application
```

### Step 2: Update Configuration File

Replace your Graph API configuration with ICS settings:

```yaml
# REMOVE these Graph API settings:
# client_id: "your-azure-client-id"
# tenant_id: "your-azure-tenant-id"  
# client_secret: "your-azure-client-secret"
# calendar_id: "your-calendar-id"

# ADD these ICS settings:
ics:
  url: "https://outlook.live.com/.../calendar.ics"  # Your ICS URL
  auth_type: "none"  # Most personal calendars are public
  verify_ssl: true

# Keep these existing settings:
refresh_interval: 300
cache_ttl: 3600
log_level: "INFO"
display_enabled: true
display_type: "console"
```

### Step 3: Clear Old Cache Data

```bash
# Remove Graph API cache (if it exists)
rm -rf ~/.local/share/calendarbot/graph_cache.db
rm -rf ~/.local/share/calendarbot/token_cache.json

# The new ICS cache will be created automatically
```

### Step 4: Test ICS Feed Access

```bash
# Test your ICS URL before running the full application
python test_ics.py --url "your-ics-calendar-url"
```

Expected output:
```
✅ ICS Feed Validation Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📡 Connection Test
   ✅ Successfully connected to ICS feed
   ✅ Received 200 OK response
   ✅ Content-Type: text/calendar

📄 ICS Content Validation
   ✅ Valid ICS format detected
   ✅ Found 5 calendar events
   ✅ Date range: 2025-01-05 to 2025-01-12
```

### Step 5: Run Migration Test

```bash
# Run comprehensive migration test
python main.py --test-mode --verbose
```

This validates:
- ICS feed connectivity
- Event parsing accuracy  
- Cache system functionality
- Display output format

### Step 6: Start New ICS System

```bash
# Start the application
python main.py
```

You should see:
```
Calendar Bot initialized
Starting Calendar Bot...
Initializing Calendar Bot components...
Calendar Bot initialization completed successfully
Starting refresh scheduler (interval: 300s)
Successfully fetched and cached 5 events from ICS source
```

### Step 7: Verify Migration Success

Check that the display shows your calendar events:

```
============================================================
📅 ICS CALENDAR - Sunday, January 5
============================================================
Updated: 07:30 | 🌐 Live Data

📋 NEXT UP

• Team Meeting
  09:00 - 10:00 | 📍 Conference Room A

• Project Review  
  14:00 - 15:00 | 💻 Online

============================================================
```

## Authentication Migration

### Public Calendars (Most Common)
Most personal calendar exports are public URLs requiring no authentication:

```yaml
ics:
  url: "https://outlook.live.com/.../calendar.ics"
  auth_type: "none"
```

### Protected Calendars (Corporate/Enterprise)

If your organization requires authentication:

#### Basic Authentication:
```yaml
ics:
  url: "https://company.com/calendar.ics"
  auth_type: "basic"
  username: "your-username"
  password: "your-password"
```

#### Bearer Token:
```yaml
ics:
  url: "https://api.company.com/calendar.ics"
  auth_type: "bearer"
  token: "your-bearer-token"
```

## Troubleshooting Migration Issues

### Issue: "Cannot connect to ICS feed"

**Diagnosis:**
```bash
# Test URL accessibility
curl -I "your-ics-url"

# Should return: HTTP/1.1 200 OK
# Content-Type: text/calendar
```

**Solutions:**
1. Verify the ICS URL is correct and accessible
2. Check if authentication is required
3. Ensure firewall allows HTTPS connections

### Issue: "Invalid ICS format" error

**Diagnosis:**
```bash
# Download and examine ICS content
curl "your-ics-url" | head -20

# Should start with:
# BEGIN:VCALENDAR
# VERSION:2.0
# PRODID:...
```

**Solutions:**
1. Verify URL returns actual ICS content (not HTML login page)
2. Check if URL requires authentication
3. Confirm calendar is published/shared correctly

### Issue: "No events showing" despite successful connection

**Diagnosis:**
```bash
# Test event parsing
python test_ics.py --url "your-ics-url" --verbose
```

**Common Causes:**
1. **Event Status**: Events marked as `FREE` or `TRANSPARENT` are filtered out
2. **Date Range**: Events might be outside current date window
3. **Timezone Issues**: Check system timezone vs calendar timezone
4. **All-Day Events**: May appear in wrong date due to timezone conversion

**Solutions:**
```yaml
# Disable busy-only filtering to see all events
ics:
  filter_busy_only: false
```

### Issue: Performance differences from Graph API

**Expected Differences:**
- **Startup**: ICS may be slightly slower due to full calendar parsing
- **Updates**: Should be similar or faster (no OAuth token management)
- **Offline**: Better offline support with full event caching

**Optimization:**
```yaml
# Reduce refresh frequency if ICS server is slow
refresh_interval: 600  # 10 minutes

# Increase cache duration
cache_ttl: 7200  # 2 hours
```

## Post-Migration Validation

### 1. Feature Parity Check

Verify all previous functionality works:

- ✅ **Current event highlighting**: Events happening now show with ▶
- ✅ **Upcoming events**: Next meetings displayed chronologically  
- ✅ **Location information**: Meeting locations preserved from calendar
- ✅ **Time formatting**: Correct timezone conversion and 24/12-hour format
- ✅ **Offline operation**: Cached events shown when network unavailable
- ✅ **Automatic refresh**: Updates every 5 minutes (or configured interval)

### 2. Data Accuracy Verification

Compare ICS system output with your calendar application:

```bash
# Generate detailed event list for verification
python test_ics.py --url "your-ics-url" --verbose --show-all-events
```

### 3. Performance Monitoring

Monitor resource usage after migration:

```bash
# Check memory and CPU usage
htop

# Monitor network requests
sudo tcpdump -i any host your-calendar-server.com
```

Expected improvements:
- **Lower CPU**: No OAuth token management overhead
- **Simpler Network**: Direct HTTPS requests instead of REST API calls
- **Better Caching**: Full ICS content cached vs individual API responses

## Rollback Procedure (If Needed)

If you need to revert to the Graph API system:

### 1. Stop ICS System
```bash
sudo systemctl stop calendarbot
```

### 2. Restore Graph Configuration
```bash
# Restore backup configuration
cp config/config.yaml.graph-backup config/config.yaml

# Restore backup cache
rm -rf ~/.local/share/calendarbot
mv ~/.local/share/calendarbot-graph-backup ~/.local/share/calendarbot
```

### 3. Reinstall Graph Dependencies
```bash
# If Graph API dependencies were removed
pip install microsoft-graph-auth microsoft-graph-core
```

### 4. Restart with Graph System
```bash
# Start with previous Graph implementation
python main.py
```

## Migration Support

### Getting Help

If you encounter issues during migration:

1. **Review this guide** for common solutions
2. **Test ICS feed directly**: `python test_ics.py --url "your-url" --verbose`
3. **Check migration logs**: Enable debug logging during migration
4. **Verify calendar setup**: Ensure calendar is properly published/shared
5. **Compare with working examples**: See [config.yaml.example](config/config.yaml.example)

### Advanced Migration Scenarios

#### Multiple Calendar Sources
```yaml
# Future feature: Multiple ICS sources
sources:
  - name: "Work Calendar"  
    url: "https://company.com/work.ics"
    auth_type: "basic"
    username: "work-user"
    password: "work-pass"
    
  - name: "Personal Calendar"
    url: "https://personal.com/calendar.ics" 
    auth_type: "none"
```

#### Custom ICS Processing
```yaml
# Advanced ICS configuration
ics:
  url: "your-url"
  # Custom event filtering
  filter_busy_only: false
  include_tentative: true
  # Timezone handling
  force_timezone: "America/New_York"
  # Custom parsing
  strict_parsing: false
```

## Migration Checklist

- [ ] **Pre-migration backup completed**
- [ ] **ICS calendar URL obtained and tested**
- [ ] **Old Graph API configuration documented**
- [ ] **Configuration file updated with ICS settings**
- [ ] **Old cache data cleared**
- [ ] **ICS feed connectivity tested successfully**
- [ ] **Migration test run with verbose output**
- [ ] **Application started and events displaying correctly**
- [ ] **Feature parity verified against previous system**
- [ ] **Performance monitoring baseline established**
- [ ] **Documentation updated with new ICS URLs**

## Summary

The migration from Microsoft Graph API to ICS calendar system provides:

- **Simplified Architecture**: Direct calendar access without API intermediaries
- **Universal Compatibility**: Works with any calendar service that exports ICS
- **Enhanced Privacy**: No third-party API access to your calendar data
- **Better Reliability**: No dependency on Microsoft Graph API quotas or availability
- **Easier Maintenance**: Standard ICS format with broad ecosystem support

The ICS-based system maintains all the functionality of the previous Graph API implementation while providing these additional benefits and removing the complexity of Azure app registration and OAuth authentication flows.

---

**Migration Complete!** Your calendar display bot now uses the robust, privacy-focused ICS calendar system.