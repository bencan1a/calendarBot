# Setup and Configuration Guide

This guide covers the configuration system and setup wizard for Calendar Bot.

## Table of Contents

- [Configuration Wizard](#configuration-wizard)
- [Manual Configuration](#manual-configuration)
- [Authentication Setup](#authentication-setup)
- [Advanced Settings](#advanced-settings)
- [Configuration Management](#configuration-management)
- [Troubleshooting Setup](#troubleshooting-setup)

## Configuration Wizard

Calendar Bot includes an interactive setup wizard that guides you through the complete configuration process.

### Running the Wizard

```bash
python main.py --setup
```

### Wizard Features

The setup wizard provides:

- **Service Templates**: Pre-configured setups for popular calendar services
- **URL Validation**: Real-time verification of ICS URL format
- **Connection Testing**: Live testing of calendar feed accessibility
- **Authentication Setup**: Guided configuration of credentials
- **Configuration Generation**: Automatic creation of config.yaml file

### Wizard Modes

#### Full Wizard (Recommended)

```bash
python main.py --setup
# Choose: 1. Full wizard (recommended)
```

The full wizard includes:
- Service-specific templates and instructions
- Step-by-step authentication setup
- Real-time connection testing
- Advanced settings configuration
- Comprehensive validation

**Example interaction**:
```
📅 Calendar Bot Configuration Wizard
============================================================
Choose setup mode:
1. Full wizard (recommended) - Interactive setup with testing and templates
2. Quick setup - Basic configuration

Enter choice (1 or 2) [1]: 1

🔧 Calendar Service Selection
----------------------------------------
Select your calendar service for quick setup:
  1. Microsoft Outlook - Outlook.com or Office 365 calendar
  2. Google Calendar - Google Calendar with secret iCal URL
  3. Apple iCloud - iCloud calendar (public sharing required)
  4. CalDAV Server - Generic CalDAV server (Nextcloud, ownCloud, etc.)
  5. Custom/Other - Custom ICS URL or other calendar service

Choose your calendar service:
Enter choice (1-5): 1
```

#### Quick Setup

```bash
python main.py --setup
# Choose: 2. Quick setup
```

The quick setup provides:
- Basic URL entry
- Minimal configuration
- Fast setup for simple use cases
- Good for users familiar with ICS URLs

### Service Templates

The wizard includes templates for popular calendar services:

#### Microsoft Outlook
- **Instructions**: Step-by-step URL extraction from Outlook.com
- **URL Pattern**: `https://outlook.live.com/owa/calendar/.../calendar.ics`
- **Authentication**: Usually none for public calendar URLs
- **Validation**: Checks URL format against Outlook patterns

#### Google Calendar
- **Instructions**: How to get secret iCal URL from Google Calendar
- **URL Pattern**: `https://calendar.google.com/calendar/ical/.../basic.ics`
- **Authentication**: None for secret URLs
- **Validation**: Verifies Google Calendar URL format

#### Apple iCloud
- **Instructions**: Setting up public calendar sharing in iCloud
- **URL Pattern**: `https://p01-caldav.icloud.com/published/...`
- **Authentication**: None for public calendars
- **Validation**: Checks iCloud URL structure

#### CalDAV Server
- **Instructions**: Generic CalDAV export setup
- **URL Pattern**: `https://server.com/remote.php/dav/calendars/user/calendar/?export`
- **Authentication**: Basic auth (username/password)
- **Validation**: Flexible pattern matching for CalDAV servers

#### Custom/Other
- **Instructions**: General guidance for any ICS source
- **URL Pattern**: Flexible matching for `.ics` URLs
- **Authentication**: Configurable based on service requirements
- **Validation**: Basic URL format checking

## Manual Configuration

If you prefer manual configuration, edit the `calendarbot/config/config.yaml` file directly.

### Basic Configuration

Create or edit `calendarbot/config/config.yaml`:

```yaml
# ICS Calendar Configuration
ics:
  url: "your-ics-calendar-url"
  auth_type: "none"
  verify_ssl: true
  timeout: 30

# Application Settings
app_name: "CalendarBot"
refresh_interval: 300       # 5 minutes
cache_ttl: 3600            # 1 hour

# Logging Configuration
log_level: "WARNING"
log_file: null

# Display Settings
display_enabled: true
display_type: "console"
```

### Configuration File Locations

Calendar Bot searches for configuration in this order:

1. **Project directory**: `calendarbot/config/config.yaml` (relative to project root)
2. **User home directory**: `~/.config/calendarbot/config.yaml`
3. **Environment variables**: `CALENDARBOT_*` prefixed variables

### Environment Variable Configuration

All settings can be configured via environment variables:

```bash
# ICS Configuration
export CALENDARBOT_ICS_URL="https://example.com/calendar.ics"
export CALENDARBOT_ICS_AUTH_TYPE="none"

# Application Settings
export CALENDARBOT_REFRESH_INTERVAL="300"
export CALENDARBOT_CACHE_TTL="3600"
export CALENDARBOT_LOG_LEVEL="INFO"

# Display Settings
export CALENDARBOT_DISPLAY_TYPE="console"
```

### Configuration Validation

Test your configuration:

```bash
# Validate configuration syntax
python -c "from config.settings import settings; print('✅ Config valid')"

# Test complete setup
python main.py --test-mode --verbose
```

## Authentication Setup

Calendar Bot supports multiple authentication methods for protected ICS feeds.

### No Authentication (Default)

For public calendar feeds:

```yaml
ics:
  auth_type: "none"
  url: "https://example.com/public-calendar.ics"
```

### Basic Authentication

For calendars requiring username/password:

```yaml
ics:
  auth_type: "basic"
  url: "https://example.com/protected-calendar.ics"
  username: "your-username"
  password: "your-password"
```

**Environment variables**:
```bash
export CALENDARBOT_ICS_AUTH_TYPE="basic"
export CALENDARBOT_ICS_USERNAME="your-username"
export CALENDARBOT_ICS_PASSWORD="your-password"
```

### Bearer Token Authentication

For API token-based authentication:

```yaml
ics:
  auth_type: "bearer"
  url: "https://example.com/api-calendar.ics"
  token: "your-bearer-token"
```

**Environment variables**:
```bash
export CALENDARBOT_ICS_AUTH_TYPE="bearer"
export CALENDARBOT_ICS_BEARER_TOKEN="your-bearer-token"
```

### Testing Authentication

Verify authentication setup:

```bash
# Test public feed
python test_ics.py --url "your-url"

# Test with basic auth
python test_ics.py --url "your-url" --auth-type basic --username "user" --password "pass"

# Test with bearer token
python test_ics.py --url "your-url" --auth-type bearer --token "your-token"
```

## Advanced Settings

### Application Settings

```yaml
# Application behavior
app_name: "CalendarBot"
refresh_interval: 300       # Fetch interval in seconds
cache_ttl: 3600            # Cache time-to-live in seconds

# Network settings
request_timeout: 30         # HTTP timeout in seconds
max_retries: 3             # Maximum retry attempts
retry_backoff_factor: 1.5  # Exponential backoff multiplier
```

### ICS Processing Settings

```yaml
ics:
  url: "your-calendar-url"
  auth_type: "none"

  # HTTP settings
  verify_ssl: true          # Validate SSL certificates
  timeout: 30              # Request timeout
  user_agent: "CalendarBot/1.0"

  # Processing settings
  filter_busy_only: true   # Only show busy/tentative events
  enable_caching: true     # Enable HTTP caching (ETags)
```

### Logging Configuration

#### Basic Logging

```yaml
# Simple logging configuration
log_level: "INFO"           # DEBUG, INFO, WARNING, ERROR, CRITICAL
log_file: "calendarbot.log" # File path or null for no file logging
```

#### Advanced Logging

```yaml
logging:
  # Console logging
  console_enabled: true
  console_level: "WARNING"
  console_colors: true

  # File logging
  file_enabled: true
  file_level: "DEBUG"
  file_directory: null      # Uses default log directory
  file_prefix: "calendarbot"
  max_log_files: 5
  include_function_names: true

  # Interactive mode
  interactive_split_display: true
  interactive_log_lines: 5

  # Third-party libraries
  third_party_level: "WARNING"
```

### Web Interface Settings

```yaml
web:
  enabled: false            # Enable web interface
  port: 8080               # Web server port
  host: "0.0.0.0"          # Bind address
  theme: "4x8"             # Available layouts: 4x8, 3x4, whats-next-view
  auto_refresh: 60         # Auto-refresh interval in seconds
```

#### Available Layout Options

CalendarBot includes several built-in layouts optimized for different use cases:

- **`4x8`** - Standard landscape layout for 4×8 inch displays (default)
- **`3x4`** - Compact layout for smaller screens or portrait orientation
- **`whats-next-view`** - Countdown timer layout showing time until next meeting

##### whats-next-view Layout

The **whats-next-view** layout provides a specialized countdown display perfect for:
- **E-ink displays** - Optimized for high contrast and minimal refresh
- **Meeting rooms** - Large, readable countdown to next scheduled meeting
- **Accessibility** - High contrast mode with large text support

**Configuration example**:
```yaml
web:
  enabled: true
  theme: "whats-next-view"
  auto_refresh: 5          # Faster refresh for countdown accuracy
```

**Key features**:
- Real-time countdown timer with second precision
- Automatic detection of next upcoming meeting
- Filters out all-day events for accurate countdown
- Fallback to next day's first event when no meetings today
- Power-efficient rendering for e-ink displays

### Display Settings

```yaml
# Display configuration
display_enabled: true
display_type: "console"     # console, html, rpi

# Raspberry Pi specific (for future e-ink displays)
rpi:
  enabled: false
  display_width: 800
  display_height: 480
  refresh_mode: "partial"
  auto_theme: true
```

## Configuration Management

### Backup and Restore

Calendar Bot includes built-in configuration management:

```bash
# Backup current configuration
python main.py --backup

# List available backups
python main.py --list-backups

# Restore from backup
python main.py --restore backup_file.yaml
```

**Example backup output**:
```
✅ Configuration backed up to: /home/user/.config/calendarbot/backups/config_backup_20250107_143012.yaml
```

### Configuration Templates

Use the example configuration as a starting point:

```bash
# Copy example configuration
cp calendarbot/config/config.yaml.example calendarbot/config/config.yaml

# Edit with your settings
nano calendarbot/config/config.yaml
```

### Validation and Testing

Always validate configuration after changes:

```bash
# Test configuration syntax
python -c "from config.settings import settings; print('✅ Config loaded successfully')"

# Test ICS connectivity
python test_ics.py

# Run full validation
python main.py --test-mode --verbose
```

## Troubleshooting Setup

### Common Setup Issues

#### Configuration Not Found

**Error**: "ICS URL configuration is required"

**Solution**:
```bash
# Check if config file exists
ls -la calendarbot/config/config.yaml

# Run setup wizard
python main.py --setup

# Or set environment variable
export CALENDARBOT_ICS_URL="your-url"
```

#### Invalid YAML Syntax

**Error**: YAML parsing errors

**Solution**:
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('calendarbot/config/config.yaml'))"

# Common issues:
# - Wrong indentation (use 2 spaces)
# - Missing quotes around URLs with special characters
# - Incorrect nesting
```

#### URL Format Issues

**Error**: URL validation failures

**Solution**:
```bash
# Test URL format
python test_ics.py --url "your-url" --validate-only

# Check URL accessibility
curl -I "your-url"

# Verify URL starts with http:// or https://
```

#### Authentication Problems

**Error**: HTTP 401/403 errors

**Solution**:
```bash
# Test authentication
python test_ics.py --url "url" --auth-type basic --username "user" --password "pass"

# Check credentials
# Verify username/password are correct
# Ensure URL requires authentication

# For CalDAV, URL should end with /?export
```

### Setup Wizard Issues

#### Wizard Fails to Start

**Problem**: Setup wizard won't run

**Solution**:
```bash
# Check Python environment
python --version
source venv/bin/activate  # If using virtual environment

# Verify imports
python -c "import calendarbot.setup_wizard; print('✅ Import successful')"

# Run with debug
python main.py --setup --verbose
```

#### Connection Testing Fails

**Problem**: Wizard can't test ICS connection

**Solution**:
```bash
# Test URL manually
curl -I "your-ics-url"

# Check network connectivity
ping google.com

# Test with verbose output
python test_ics.py --url "your-url" --verbose

# Check firewall/proxy settings
```

#### Configuration Not Saved

**Problem**: Wizard completes but config not saved

**Solution**:
```bash
# Check file permissions
ls -la config/
touch config/test.txt  # Test write permissions

# Verify directory exists
mkdir -p ~/.config/calendarbot

# Run wizard with debug output
python main.py --setup --verbose
```

### Recovery Procedures

#### Reset Configuration

```bash
# Backup current config
python main.py --backup

# Remove current config
rm calendarbot/config/config.yaml

# Run setup wizard again
python main.py --setup
```

#### Factory Reset

```bash
# Remove all configuration and cache
rm -rf ~/.config/calendarbot/
rm -rf ~/.local/share/calendarbot/
rm -rf ~/.cache/calendarbot/

# Remove project config
rm -f calendarbot/config/config.yaml

# Start fresh setup
python main.py --setup
```

### Getting Help

If setup issues persist:

1. **Run diagnostics**: `python main.py --test-mode --verbose`
2. **Test ICS URL**: `python test_ics.py --url "your-url" --verbose`
3. **Check logs**: Enable debug logging for detailed output
4. **Verify requirements**: Ensure all dependencies are installed
5. **Check examples**: Review `calendarbot/config/config.yaml.example`
6. **Create issue**: Include setup logs and exact error messages

---

**Next Steps**: After successful setup, see [USAGE.md](USAGE.md) for daily operation guidance and available operational modes.
