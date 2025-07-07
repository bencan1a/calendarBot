# Installation Guide

This guide provides complete instructions for installing and setting up Calendar Bot on your system.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
- [Python Environment Setup](#python-environment-setup)
- [Getting Your Calendar URL](#getting-your-calendar-url)
- [Configuration](#configuration)
- [First Run](#first-run)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Python 3.8 or higher** with pip
- **Git** for cloning the repository
- **Internet connection** for accessing calendar feeds
- **50MB disk space** for application and dependencies

### Supported Platforms

- Linux (all distributions)
- macOS (10.14+)
- Windows (10+)

### Python Verification

Check your Python version:

```bash
python --version
# or
python3 --version
```

If Python is not installed or version is too old, download from [python.org](https://python.org).

## Installation Methods

### Method 1: Git Clone (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd calendarBot

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Method 2: Download ZIP

1. Download ZIP file from GitHub
2. Extract to your preferred location
3. Follow virtual environment setup from Method 1

## Python Environment Setup

### Virtual Environment (Recommended)

Using a virtual environment isolates Calendar Bot's dependencies:

```bash
# Create virtual environment
python -m venv venv

# Activate environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Verify activation (should show venv path)
which python

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep -E "(icalendar|httpx|pydantic)"
```

### System-wide Installation

If you prefer system-wide installation:

```bash
# Install dependencies globally
pip install -r requirements.txt

# Note: This may conflict with other Python projects
```

### Dependencies Overview

Calendar Bot requires these Python packages:

```
icalendar>=5.0.0      # ICS calendar parsing
httpx>=0.25.0         # HTTP client for fetching
aiosqlite>=0.19.0     # Async SQLite database
pydantic>=2.0.0       # Data validation
pydantic-settings>=2.0.0  # Settings management
PyYAML>=6.0           # YAML configuration
python-dateutil>=2.8.0    # Date parsing
pytz>=2023.3          # Timezone support
cryptography>=41.0.0  # Secure credentials
APScheduler>=3.10.0   # Task scheduling
```

## Getting Your Calendar URL

Calendar Bot works with ICS (iCalendar) feeds from any calendar service. Here's how to get your URL:

### Microsoft Outlook/Office 365

1. **Go to Outlook web** (outlook.live.com or outlook.office365.com)
2. **Click Calendar** in the left sidebar
3. **Open Settings** (gear icon) → "View all Outlook settings"
4. **Navigate to Calendar** → "Shared calendars"
5. **Under "Publish a calendar"**:
   - Select your calendar
   - Set permissions to "Can view when I'm busy"
   - Click **Publish**
6. **Copy the ICS URL** (ends with `.ics`)

**Example URL**: `https://outlook.live.com/owa/calendar/00000000-0000-0000-0000-000000000000/11111111-1111-1111-1111-111111111111/cid-2222222222222222/calendar.ics`

### Google Calendar

1. **Open Google Calendar** (calendar.google.com)
2. **Click the three dots** next to your calendar name
3. **Select "Settings and sharing"**
4. **Scroll to "Access permissions and export"**
5. **Copy "Secret address in iCal format"** (ends with `.ics`)

**Example URL**: `https://calendar.google.com/calendar/ical/your-email%40gmail.com/private-1234567890abcdef/basic.ics`

### Apple iCloud Calendar

1. **Go to iCloud.com** and sign in
2. **Open Calendar app**
3. **Click the share icon** next to your calendar
4. **Enable "Public Calendar"**
5. **Copy the calendar URL**

**Example URL**: `https://p01-caldav.icloud.com/published/2/MTIzNDU2Nzg5MDEyMzQ1Ng`

### CalDAV Servers (Nextcloud, ownCloud)

For CalDAV servers, the URL pattern is typically:

```
https://your-server.com/remote.php/dav/calendars/username/calendar-name/?export
```

**Authentication**: CalDAV usually requires username/password authentication.

### Other Calendar Services

Most calendar services offer ICS export:
- Look for "Export", "Subscribe", "iCal", or "Webcal" options
- Copy the URL that ends with `.ics`
- If prompted for authentication, note your credentials

## Configuration

### Automated Setup (Recommended)

Use the interactive setup wizard:

```bash
python main.py --setup
```

The wizard will:
1. **Guide you through service selection**
2. **Provide service-specific instructions**
3. **Validate your URL format**
4. **Test the connection**
5. **Generate configuration file**

### Manual Configuration

If you prefer manual setup:

1. **Copy example configuration**:
   ```bash
   cp config/config.yaml.example config/config.yaml
   ```

2. **Edit configuration**:
   ```bash
   nano config/config.yaml  # or your preferred editor
   ```

3. **Add your ICS URL**:
   ```yaml
   ics:
     url: "your-ics-calendar-url"
     auth_type: "none"  # Change if authentication needed
     verify_ssl: true
   ```

### Authentication Configuration

If your calendar requires authentication:

**Basic Authentication** (username/password):
```yaml
ics:
  url: "your-ics-url"
  auth_type: "basic"
  username: "your-username"
  password: "your-password"
```

**Bearer Token Authentication**:
```yaml
ics:
  url: "your-ics-url"
  auth_type: "bearer"
  token: "your-bearer-token"
```

### Environment Variables

Alternatively, use environment variables:

```bash
# Linux/macOS
export CALENDARBOT_ICS_URL="your-calendar-url"
export CALENDARBOT_ICS_AUTH_TYPE="none"

# Windows
set CALENDARBOT_ICS_URL=your-calendar-url
set CALENDARBOT_ICS_AUTH_TYPE=none
```

## First Run

### Test Configuration

Validate your setup before running:

```bash
# Test configuration
python main.py --test-mode --verbose
```

This will:
- ✅ Validate configuration file
- ✅ Test ICS URL connectivity
- ✅ Verify authentication
- ✅ Parse sample calendar data
- ✅ Check cache functionality

### Direct ICS Testing

Test your ICS URL directly:

```bash
# Test public calendar
python test_ics.py --url "your-ics-url"

# Test with authentication
python test_ics.py --url "your-ics-url" --auth-type basic --username "user" --password "pass"

# Verbose output
python test_ics.py --url "your-ics-url" --verbose
```

### Start Calendar Bot

Run Calendar Bot in default mode:

```bash
python main.py
```

**Expected output**:
```
Calendar Bot initialized
Starting Calendar Bot...
Initializing Calendar Bot components...
Calendar Bot initialization completed successfully
Starting refresh scheduler (interval: 300s)
Successfully fetched and cached 5 events from ICS source

============================================================
📅 ICS CALENDAR - Monday, January 15
============================================================
Updated: 10:05 | 🌐 Live Data

📋 NEXT UP

• Team Standup
  10:00 - 10:30 | 📍 Conference Room A

• Project Review
  11:00 - 12:00 | 💻 Online

============================================================
```

## Verification

### Check Installation

Verify all components are working:

```bash
# 1. Test Python imports
python -c "import calendarbot; print('✅ Import successful')"

# 2. Test configuration loading
python -c "from config.settings import settings; print(f'✅ Config loaded: {bool(settings.ics_url)}')"

# 3. Test ICS functionality
python test_ics.py --url "$CALENDARBOT_ICS_URL"

# 4. Run full validation
python main.py --test-mode --components auth,api,cache,display
```

### Verify File Structure

Check that necessary files were created:

```bash
# Configuration
ls -la config/config.yaml

# Cache database (created after first run)
ls -la ~/.local/share/calendarbot/calendar_cache.db

# Log directory (if file logging enabled)
ls -la ~/.local/share/calendarbot/logs/
```

### Test Different Modes

Try all operational modes:

```bash
# Interactive mode
python main.py --interactive

# Web interface
python main.py --web

# Test mode
python main.py --test-mode --verbose
```

## Troubleshooting

### Installation Issues

**Python version error**:
```bash
# Check Python version
python --version

# If too old, install newer Python from python.org
# Then retry installation
```

**Pip install failures**:
```bash
# Upgrade pip
pip install --upgrade pip

# Install build tools (Linux)
sudo apt install python3-dev build-essential

# Install build tools (macOS)
xcode-select --install

# Retry installation
pip install -r requirements.txt
```

**Virtual environment issues**:
```bash
# Remove corrupted venv
rm -rf venv

# Recreate virtual environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration Issues

**"ICS URL configuration is required"**:
```bash
# Check if config file exists
ls -la config/config.yaml

# Verify URL is set
grep "url:" config/config.yaml

# Or set environment variable
export CALENDARBOT_ICS_URL="your-url"
```

**"Cannot connect to ICS feed"**:
```bash
# Test URL manually
curl -I "your-ics-url"

# Test with Calendar Bot
python test_ics.py --url "your-ics-url" --verbose

# Check firewall/proxy settings
```

**YAML syntax errors**:
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"

# Common issues:
# - Wrong indentation (use 2 spaces)
# - Missing quotes around URLs
# - Special characters in passwords
```

### Authentication Issues

**HTTP 401/403 errors**:
```bash
# Test credentials
python test_ics.py --url "url" --auth-type basic --username "user" --password "pass"

# Check if URL requires authentication
curl -I "your-ics-url"

# Verify credentials are correct
```

**SSL certificate errors**:
```yaml
# Temporarily disable SSL verification (not recommended)
ics:
  verify_ssl: false
```

### Network Issues

**Connection timeouts**:
```yaml
# Increase timeout in config
ics:
  timeout: 60

# Check network connectivity
ping google.com
```

**DNS resolution failures**:
```bash
# Check DNS resolution
nslookup your-calendar-server.com

# Try different DNS servers
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
```

### Performance Issues

**Slow startup**:
```bash
# Clear cache if corrupted
rm -rf ~/.local/share/calendarbot/calendar_cache.db

# Check disk space
df -h

# Monitor performance
python main.py --test-mode --verbose
```

**High memory usage**:
```yaml
# Reduce cache TTL
cache_ttl: 1800  # 30 minutes instead of 1 hour

# Increase refresh interval
refresh_interval: 600  # 10 minutes instead of 5
```

### Getting Help

If you encounter issues not covered here:

1. **Run diagnostics**: `python main.py --test-mode --verbose`
2. **Test ICS feed**: `python test_ics.py --url "your-url" --verbose`
3. **Check logs**: Enable debug logging in config
4. **Search issues**: Check GitHub issues for similar problems
5. **Create issue**: Include system info, logs, and exact error messages

### Recovery Procedures

**Reset to clean state**:
```bash
# Backup current config
cp config/config.yaml config/config.yaml.backup

# Clear cache
rm -rf ~/.local/share/calendarbot/

# Reset configuration
cp config/config.yaml.example config/config.yaml

# Reconfigure
python main.py --setup
```

**Restore from backup**:
```bash
# Using built-in backup system
python main.py --list-backups
python main.py --restore backup_file.yaml

# Manual restore
cp config/config.yaml.backup config/config.yaml
```

---

**Next Steps**: After successful installation, see [SETUP.md](SETUP.md) for configuration details and [USAGE.md](USAGE.md) for daily operation guidance.
