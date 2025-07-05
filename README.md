# ICS Calendar Display Bot

**Version:** 2.0 (ICS Implementation)
**Last Updated:** January 5, 2025
**Architecture:** ICS-based Universal Calendar System
**Migration Status:** Migrated from Microsoft Graph API v1.0

A lightweight ICS calendar display application optimized for Raspberry Pi with e-ink displays. This application provides persistent desktop calendar display showing today's meetings with offline caching and flexible authentication for ICS calendar feeds.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red.svg)
![Status](https://img.shields.io/badge/status-Production%20Ready-green.svg)

## Project Overview

Transform any Raspberry Pi into a dedicated calendar display that shows your daily schedule from any ICS calendar feed. Designed specifically for e-ink displays, this application provides an always-on calendar view perfect for your desk, office, or anywhere you need quick access to your schedule.

### Key Benefits

- **Universal ICS Support**: Works with any calendar that exports ICS feeds (Outlook, Google Calendar, CalDAV, etc.)
- **Always-On Display**: Low-power e-ink display shows your schedule 24/7
- **Secure & Private**: All calendar data processed locally with flexible authentication
- **Offline Resilient**: Works even when internet connectivity is intermittent
- **Zero Configuration**: Simple setup with minimal user intervention required
- **Raspberry Pi Optimized**: Designed for efficiency and minimal resource usage

## Features

### 🔗 Universal ICS Feed Support
- **Direct ICS URL integration** from any calendar service
- **Flexible HTTP authentication** (Basic, Bearer token, or public feeds)
- **Calendar auto-detection** with metadata parsing
- **Multiple feed support** for combined calendar views

### 📅 Smart Calendar Management
- **Real-time sync** with configurable polling intervals (default: 5 minutes)
- **Event filtering** to "Busy" and "Tentative" events only
- **Timezone handling** with automatic detection and conversion
- **Recurring event expansion** for accurate scheduling

### 💾 Robust Offline Functionality
- **SQLite caching** with configurable TTL for offline access
- **WAL mode enabled** for reduced SD card wear and improved performance
- **Graceful degradation** when feeds are unavailable
- **Network connectivity monitoring** with automatic reconnection

### 🖥️ Clean Display Interface
- **Console output** optimized for testing and development
- **Current meeting highlighting** with visual indicators (▶)
- **Next 2-3 meetings** displayed with time and location
- **Real-time status indicators** showing last update and connection status
- **Interactive navigation mode** with keyboard controls

### 🛡️ Enterprise-Grade Error Handling
- **Exponential backoff retry logic** for HTTP requests
- **Comprehensive exception handling** throughout the application
- **Circuit breaker pattern** for network failures
- **Detailed logging** with configurable levels and file rotation

### ⚡ Power & Performance Optimized
- **Minimal resource usage** (< 100MB RAM, < 10% CPU average)
- **Async/await architecture** for efficient I/O operations
- **SQLite WAL mode** to minimize SD card writes
- **Smart caching** to reduce HTTP requests and bandwidth usage

## Quick Start

### Prerequisites

- **Raspberry Pi** (Zero 2 W or newer recommended)
- **Python 3.8+** with pip package manager
- **ICS calendar feed URL** from your calendar service
- **Internet connectivity** for initial setup and ongoing sync

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd calendarBot
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Get your ICS calendar URL:**

**For Outlook/Office 365:**
- Go to Outlook on the web
- Navigate to Calendar → Settings → View all Outlook settings
- Go to Calendar → Shared calendars
- Under "Publish a calendar", select your calendar and click "Publish"
- Copy the ICS link

**For Google Calendar:**
- Open Google Calendar
- Click on the three dots next to your calendar
- Select "Settings and sharing"
- Scroll to "Access permissions and export"
- Copy the "Secret address in iCal format"

4. **Configure the application:**
```bash
# Copy example configuration
cp config/config.yaml.example config/config.yaml

# Edit configuration with your ICS URL
nano config/config.yaml
```

Or set environment variable:
```bash
export CALENDARBOT_ICS_URL="your-ics-calendar-url"
```

5. **Run the application:**
```bash
python main.py
```

### First Run

The application will:
- Validate your ICS feed URL
- Download and parse calendar events
- Cache events locally
- Display your current schedule

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

============================================================
```

## Execution Modes

### Daemon Mode (Default)
```bash
python main.py
```
Runs continuously, updating calendar data every 5 minutes.

### Interactive Mode
```bash
python main.py --interactive
```
Provides keyboard navigation:
- **Arrow keys**: Navigate between dates
- **Space**: Jump to today
- **ESC**: Exit

### Test Mode
```bash
python main.py --test-mode
```
Validates configuration and tests ICS feed connectivity.

```bash
python main.py --test-mode --verbose
```
Runs comprehensive validation with detailed output.

## Documentation

| Document | Description |
|----------|-------------|
| [INSTALL.md](INSTALL.md) | Detailed installation guide including Raspberry Pi setup |
| [USAGE.md](USAGE.md) | Day-to-day operation and troubleshooting guide |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical architecture and design decisions |
| [MIGRATION.md](MIGRATION.md) | **Migration guide from Microsoft Graph API to ICS system** |
| [CHANGELOG.md](CHANGELOG.md) | Version history and breaking changes documentation |
| [INTERACTIVE_NAVIGATION.md](INTERACTIVE_NAVIGATION.md) | Interactive mode usage guide |

## Configuration

### Environment Variables

All configuration can be set via environment variables with the `CALENDARBOT_` prefix:

```bash
export CALENDARBOT_ICS_URL="https://outlook.live.com/.../calendar.ics"
export CALENDARBOT_ICS_AUTH_TYPE="basic"  # or "bearer" or "none"
export CALENDARBOT_ICS_USERNAME="username"  # for basic auth
export CALENDARBOT_ICS_PASSWORD="password"  # for basic auth
export CALENDARBOT_LOG_LEVEL="INFO"
export CALENDARBOT_REFRESH_INTERVAL=300
export CALENDARBOT_CACHE_TTL=3600
export CALENDARBOT_DISPLAY_TYPE="console"
```

### Configuration File

Create [`config/config.yaml`](config/config.yaml.example) based on the example:

```yaml
# ICS Calendar Configuration
ics:
  url: "https://outlook.live.com/.../calendar.ics"
  auth_type: "none"  # "basic", "bearer", or "none"
  # username: "your-username"  # for basic auth
  # password: "your-password"  # for basic auth
  # token: "your-bearer-token"  # for bearer auth
  verify_ssl: true

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

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Source Manager  │    │   ICS Fetcher    │    │ Cache Manager   │
│                 │    │                  │    │                 │
│ • Multi-source  │───▶│ • HTTP Client    │───▶│ • SQLite WAL    │
│ • Health Check  │    │ • Auth Support   │    │ • TTL Caching   │
│ • Auto Config   │    │ • Retry Logic    │    │ • Offline Mode  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                         ┌─────────────────┐
                         │ Display Manager │
                         │                 │
                         │ • Console Out   │
                         │ • Status Info   │
                         │ • Error Display │
                         └─────────────────┘
```

## File Structure

```
calendarBot/
├── README.md                    # This file
├── INSTALL.md                   # Installation guide
├── USAGE.md                     # User guide
├── ARCHITECTURE.md              # Architecture documentation
├── requirements.txt             # Python dependencies
├── setup.py                     # Package installation
├── main.py                      # Application entry point
├── test_ics.py                  # ICS testing utility
├── test_interactive.py          # Interactive mode testing
├── config/
│   ├── settings.py              # Pydantic settings
│   ├── config.yaml.example      # Example configuration
│   └── ics_config.py            # ICS-specific configuration
├── calendarbot/
│   ├── main.py                  # Core application logic
│   ├── sources/                 # Calendar source management
│   │   ├── manager.py           # Source coordination
│   │   ├── ics_source.py        # ICS feed handling
│   │   ├── models.py            # Source data models
│   │   └── exceptions.py        # Source-specific exceptions
│   ├── ics/                     # ICS processing
│   │   ├── fetcher.py           # HTTP ICS fetching
│   │   ├── parser.py            # ICS content parsing
│   │   ├── models.py            # ICS data models
│   │   └── exceptions.py        # ICS-specific exceptions
│   ├── cache/                   # Local data caching
│   │   ├── manager.py           # Cache coordination
│   │   ├── database.py          # SQLite operations
│   │   └── models.py            # Cache data models
│   ├── display/                 # Display management
│   │   ├── manager.py           # Display coordination
│   │   └── console_renderer.py  # Console output renderer
│   ├── ui/                      # User interface
│   │   ├── interactive.py       # Interactive controller
│   │   ├── keyboard.py          # Keyboard input handling
│   │   └── navigation.py        # Navigation logic
│   ├── utils/                   # Utility functions
│   │   ├── logging.py           # Logging setup
│   │   └── helpers.py           # General utilities
│   └── validation/              # Testing and validation
│       ├── runner.py            # Validation framework
│       ├── results.py           # Result models
│       └── logging_setup.py     # Validation logging
```

## Usage Examples

### Basic Operation

The application runs continuously, updating every 5 minutes:

```bash
python main.py
```

### Testing Your Configuration

Validate your ICS feed setup with our dedicated testing utility:

```bash
# Test basic ICS feed access
python test_ics.py --url "your-ics-url"

# Test with verbose output showing detailed parsing
python test_ics.py --url "your-ics-url" --verbose

# Test with Basic Authentication
python test_ics.py --url "your-ics-url" --auth-type basic --username user --password pass

# Test with Bearer Token
python test_ics.py --url "your-ics-url" --auth-type bearer --token "your-token"

# Validate ICS format only (no event parsing)
python test_ics.py --url "your-ics-url" --validate-only
```

The testing utility leverages [`calendarbot.ics.fetcher.ICSFetcher`](calendarbot/ics/fetcher.py) and [`calendarbot.ics.parser.ICSParser`](calendarbot/ics/parser.py) to validate your complete setup.

### Interactive Navigation

Explore your calendar with keyboard controls:

```bash
python main.py --interactive
```

Use arrow keys to navigate, Space for today, ESC to exit.

## Troubleshooting

### ICS Feed Issues

**Problem**: Cannot fetch calendar data
```bash
# Test ICS URL directly
python test_ics.py --url "your-ics-url" --verbose

# Check for authentication requirements
curl -I "your-ics-url"
```

**Problem**: "Invalid ICS format" error
- Verify the URL returns valid ICS content
- Check if authentication is required
- Ensure the feed is publicly accessible or credentials are correct

### Authentication Issues

**Problem**: HTTP 401/403 errors
```bash
# Test with credentials
python test_ics.py --url "your-url" --auth-type basic --username "user" --password "pass"
```

**Problem**: SSL certificate errors
```yaml
# In config.yaml, disable SSL verification (not recommended for production)
ics:
  verify_ssl: false
```

### Network Issues

**Problem**: Connection timeouts
- Check internet connectivity
- Verify firewall settings allow HTTPS connections
- Increase `request_timeout` in configuration

### Cache Issues

**Problem**: Stale data displayed
```bash
# Clear cache database
rm -rf ~/.local/share/calendarbot/calendar_cache.db
```

### Logging and Debugging

Enable debug logging:
```bash
export CALENDARBOT_LOG_LEVEL="DEBUG"
python main.py
```

Or set in [`config/config.yaml`](config/config.yaml.example):
```yaml
log_level: "DEBUG"
log_file: "calendarbot.log"
```

## Security & Privacy

### Data Protection
- **Local Storage Only**: No cloud storage of calendar data
- **Minimal Data Collection**: Only calendar events are processed
- **Secure HTTP**: HTTPS for all calendar feed requests
- **Credential Protection**: Optional HTTP authentication support

### Network Security
- **HTTPS Only**: All feed communications use TLS by default
- **Certificate Validation**: Strict certificate checking (configurable)
- **No External Dependencies**: Minimal attack surface
- **Rate Limiting**: Respects server limits to prevent abuse

## Migration from Microsoft Graph

If you're currently using a Microsoft Graph API implementation, you can migrate to ICS feeds:

1. **Export your Outlook calendar as ICS** (see Quick Start section)
2. **Update configuration** to use ICS URL instead of client ID
3. **Remove Azure authentication** - no longer needed
4. **Test with the new configuration** using test mode

The ICS approach provides:
- ✅ Simpler setup (no Azure app registration)
- ✅ Universal compatibility (works with any calendar service)
- ✅ No API quotas or rate limiting concerns
- ✅ Privacy (direct calendar access without third-party APIs)

## Contributing

We welcome contributions to improve the ICS Calendar Display Bot! Please follow these guidelines:

### Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/your-username/calendarBot.git
   cd calendarBot
   ```

2. **Set up development environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run tests before making changes**:
   ```bash
   python main.py --test-mode --verbose
   python test_ics.py --url "your-test-ics-url"
   ```

### Contribution Process

1. **Create a feature branch**: `git checkout -b feature/amazing-feature`
2. **Follow coding standards**: Ensure code follows PEP 8 and includes type hints
3. **Test your changes**: Verify all functionality works with your modifications
4. **Update documentation**: Update relevant `.md` files if you change functionality
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to your fork**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**: Include description of changes and testing performed

### Code Style Guidelines

- **Python Code**: Follow PEP 8, use type hints, add docstrings for public functions
- **Documentation**: Follow the existing markdown style, use proper linking syntax
- **Configuration**: Maintain backward compatibility when possible
- **Testing**: Add test cases for new features using the existing validation framework

### Reporting Issues

When reporting bugs or requesting features:
- **Use the issue template** with clear description and steps to reproduce
- **Include system information**: OS, Python version, calendar service used
- **Provide logs**: Enable debug logging and include relevant output
- **Test with latest version**: Ensure issue exists in the current release

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for complete details.

### Copyright Notice

```
Copyright (c) 2025 ICS Calendar Display Bot Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

### Third-Party Licenses

This project includes dependencies with the following licenses:
- **icalendar**: BSD-2-Clause License
- **httpx**: BSD License
- **pydantic**: MIT License
- **aiosqlite**: MIT License
- **PyYAML**: MIT License

See individual package documentation for complete license terms.

## Support

### Documentation Resources

| Resource | Purpose | When to Use |
|----------|---------|-------------|
| [INSTALL.md](INSTALL.md) | Complete installation guide | Setting up for the first time |
| [USAGE.md](USAGE.md) | Day-to-day operation guide | Understanding daily operation |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical architecture details | Understanding system design |
| [MIGRATION.md](MIGRATION.md) | **Graph API to ICS migration** | **Upgrading from v1.x** |
| [CHANGELOG.md](CHANGELOG.md) | Version history and changes | Understanding what's new |

### Getting Help

1. **Check the documentation** - Most questions are answered in the guides above
2. **Run diagnostics**: `python main.py --test-mode --verbose`
3. **Test ICS feed directly**: `python test_ics.py --url "your-url" --verbose`
4. **Search existing issues** on GitHub for similar problems
5. **Create a new issue** with detailed information:
   - System information (OS, Python version)
   - Calendar service and ICS URL format (redacted)
   - Complete error messages and logs
   - Steps to reproduce the issue

### Community and Contributions

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and community support
- **Pull Requests**: Code contributions and improvements
- **Documentation**: Help improve guides and examples

## Acknowledgments

### Technical Foundation
- **RFC 5545** (Internet Calendaring and Scheduling Core Object Specification) for standardized calendar data format
- **Python icalendar library** for robust and compliant ICS parsing implementation
- **HTTPX library** for modern async HTTP client capabilities
- **Pydantic** for type-safe configuration and data validation

### Hardware and Platform
- **Raspberry Pi Foundation** for providing excellent ARM-based computing platform
- **E-ink display manufacturers** for low-power display technology
- **Python asyncio community** for async/await best practices and performance insights

### Open Source Community
- **Contributors and testers** who help improve the software
- **Calendar service providers** (Microsoft, Google, Apple) for ICS feed support
- **CalDAV specification authors** for standardized calendar protocols
- **Python packaging community** for excellent dependency management

### Previous Implementations
- **Microsoft Graph API developers** for the inspiration from the v1.x implementation
- **Azure authentication libraries** that informed the security design principles
- **REST API patterns** that influenced the ICS processing architecture

---

## Quick Reference

### Essential Commands

```bash
# Installation and setup
git clone <repository-url> && cd calendarBot
pip install -r requirements.txt
cp config/config.yaml.example config/config.yaml

# Testing and validation
python test_ics.py --url "your-ics-url" --verbose
python main.py --test-mode --verbose

# Normal operation
python main.py                    # Daemon mode
python main.py --interactive      # Interactive navigation
python main.py --test-mode       # System validation
```

### Configuration Quick Start

```yaml
# Minimal config.yaml
ics:
  url: "https://outlook.live.com/.../calendar.ics"
  auth_type: "none"
refresh_interval: 300
log_level: "INFO"
```

### System Requirements

- **Hardware**: Raspberry Pi Zero 2 W or newer
- **OS**: Raspberry Pi OS Lite (headless recommended)
- **Python**: 3.8+ with pip
- **Network**: Internet connectivity for ICS feeds
- **Storage**: 1GB available space (including dependencies)

---

**🚀 Ready to get started?** Follow the **[Installation Guide](INSTALL.md)** for detailed setup instructions.

**📚 Need help?** Check the **[Migration Guide](MIGRATION.md)** if upgrading from Microsoft Graph API v1.x.

---

*ICS Calendar Display Bot v2.0 - Documentation last updated January 5, 2025*
*Copyright (c) 2025 - Licensed under MIT License - [View Changelog](CHANGELOG.md)*