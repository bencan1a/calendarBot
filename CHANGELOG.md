# Changelog

All notable changes to the ICS Calendar Display Bot project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-01-05

### 🚨 BREAKING CHANGES

This major version completely replaces the Microsoft Graph API implementation with an ICS-based calendar system. **This is not a backward-compatible upgrade.**

#### Configuration Changes (BREAKING)
- **Removed**: All Microsoft Graph API configuration options
  - `client_id` (Azure Application ID)
  - `tenant_id` (Azure Tenant ID)  
  - `client_secret` (Azure Application Secret)
  - `calendar_id` (Graph API Calendar ID)
- **Added**: ICS calendar configuration
  - `ics.url` (ICS calendar feed URL)
  - `ics.auth_type` (Authentication method)
  - `ics.username/password` (Basic auth credentials)
  - `ics.token` (Bearer token authentication)

#### Authentication Changes (BREAKING)
- **Removed**: OAuth2 Azure authentication flow
- **Added**: HTTP authentication for ICS feeds (Basic, Bearer, or None)
- **Migration Required**: Users must obtain ICS calendar URLs from their calendar providers

#### API Changes (BREAKING)
- **Removed**: Microsoft Graph REST API client
- **Added**: HTTP-based ICS feed fetcher with [`calendarbot/ics/fetcher.py`](calendarbot/ics/fetcher.py)
- **Changed**: Event data models now based on ICS format in [`calendarbot/ics/models.py`](calendarbot/ics/models.py)

#### Cache Format Changes (BREAKING)
- **Changed**: Cache database schema updated for ICS events
- **Automatic**: Old cache data automatically migrated or recreated
- **Location**: Cache remains in `~/.local/share/calendarbot/calendar_cache.db`

### ✨ New Features

#### Universal Calendar Support
- **Added**: Support for any ICS-compatible calendar service
  - Microsoft Outlook/Office 365 (published calendars)
  - Google Calendar (secret iCal URLs)
  - Apple iCloud Calendar (public calendars)
  - CalDAV servers (Nextcloud, Radicale, etc.)
  - Any RFC 5545 compliant calendar system

#### Enhanced ICS Processing
- **Added**: RFC 5545 compliant ICS parsing with [`calendarbot/ics/parser.py`](calendarbot/ics/parser.py)
- **Added**: Comprehensive timezone handling and conversion
- **Added**: Recurring event expansion (RRULE support)
- **Added**: Event filtering by status (BUSY/TENTATIVE vs FREE/TRANSPARENT)

#### Improved Authentication
- **Added**: Flexible HTTP authentication methods
  - Public feeds (no authentication)
  - Basic Authentication (username/password)
  - Bearer Token authentication
  - Custom HTTP headers support

#### Enhanced Testing Framework
- **Added**: Dedicated ICS testing utility [`test_ics.py`](test_ics.py)
- **Added**: Comprehensive validation framework in [`calendarbot/validation/`](calendarbot/validation/)
- **Added**: Interactive mode testing with [`test_interactive.py`](test_interactive.py)

### 🔧 Improvements

#### Performance Optimizations
- **Improved**: Async/await architecture throughout
- **Improved**: SQLite WAL mode for better concurrency
- **Improved**: HTTP connection pooling and keep-alive
- **Improved**: Intelligent caching with ETags and Last-Modified headers

#### Error Handling
- **Enhanced**: Circuit breaker pattern for network failures
- **Enhanced**: Exponential backoff retry logic
- **Enhanced**: Graceful degradation during network outages
- **Enhanced**: Detailed error reporting and diagnostics

#### User Experience
- **Improved**: Cleaner console output with status indicators
- **Improved**: Interactive mode with keyboard navigation
- **Improved**: Real-time status updates (Live Data vs Cached Data)
- **Improved**: Better offline mode operation

#### Documentation
- **Added**: Comprehensive [Migration Guide](MIGRATION.md)
- **Updated**: Complete [Installation Guide](INSTALL.md) with ICS setup
- **Updated**: [Architecture Documentation](ARCHITECTURE.md) for ICS system
- **Updated**: [User Guide](USAGE.md) with new features and troubleshooting

### 🐛 Bug Fixes

#### Timezone Handling
- **Fixed**: Proper timezone conversion for all-day events
- **Fixed**: Daylight saving time transitions
- **Fixed**: Multiple timezone support in single calendar

#### Event Processing
- **Fixed**: Recurring event edge cases
- **Fixed**: Event overlap detection and display
- **Fixed**: Location parsing from various calendar formats

#### Cache Management
- **Fixed**: Cache corruption recovery
- **Fixed**: TTL expiration edge cases
- **Fixed**: Database locking issues

### 📦 Dependencies

#### Removed Dependencies
- `msal` (Microsoft Authentication Library)
- `microsoft-graph-core` (Graph API client)
- `microsoft-graph-auth` (Graph authentication)

#### Added Dependencies
- `icalendar>=5.0.0` (ICS parsing library)
- `httpx>=0.25.0` (Modern HTTP client with async support)
- Enhanced `aiosqlite>=0.19.0` usage for cache management

#### Updated Dependencies
- `pydantic>=2.0.0` (Settings and data validation)
- `PyYAML>=6.0` (Configuration file parsing)

### 🗂️ File Structure Changes

#### New Files
- [`MIGRATION.md`](MIGRATION.md) - Complete migration guide
- [`CHANGELOG.md`](CHANGELOG.md) - This changelog
- [`calendarbot/ics/`](calendarbot/ics/) - ICS processing module
  - [`fetcher.py`](calendarbot/ics/fetcher.py) - HTTP ICS fetching
  - [`parser.py`](calendarbot/ics/parser.py) - ICS content parsing
  - [`models.py`](calendarbot/ics/models.py) - ICS data models
  - [`exceptions.py`](calendarbot/ics/exceptions.py) - ICS-specific exceptions
- [`test_ics.py`](test_ics.py) - ICS testing utility
- [`test_interactive.py`](test_interactive.py) - Interactive mode testing

#### Updated Files
- [`README.md`](README.md) - Complete rewrite for ICS system
- [`INSTALL.md`](INSTALL.md) - Updated installation procedures
- [`ARCHITECTURE.md`](ARCHITECTURE.md) - New ICS-based architecture
- [`USAGE.md`](USAGE.md) - Updated usage guide
- [`config/config.yaml.example`](config/config.yaml.example) - ICS configuration examples

#### Removed Files
- `graph_auth.py` (Microsoft Graph authentication)
- `graph_client.py` (Graph API client)
- `token_cache.json` (OAuth token storage)

### 🔒 Security Improvements

#### Authentication Security
- **Enhanced**: HTTPS-only communication for ICS feeds
- **Enhanced**: SSL certificate validation (configurable)
- **Enhanced**: Secure credential storage in configuration files

#### Privacy Enhancements
- **Improved**: Local-only data processing (no cloud intermediaries)
- **Improved**: Direct calendar access without third-party APIs
- **Improved**: User-controlled data retention policies
- **Removed**: OAuth token management and storage

### 📊 Performance Metrics

#### Resource Usage Improvements
- **Memory**: Reduced from ~150MB to <100MB average usage
- **CPU**: Reduced OAuth overhead, more efficient HTTP handling
- **Network**: Direct ICS fetching vs REST API calls
- **Storage**: Simplified cache format, reduced database size

#### Response Time Improvements
- **Startup**: Faster initialization (no OAuth token validation)
- **Updates**: Direct ICS parsing vs multiple API calls
- **Offline**: Improved cache hit rates and faster fallback

### 🎯 Migration Path

For users upgrading from v1.x (Microsoft Graph API):

1. **Read** the [Migration Guide](MIGRATION.md)
2. **Backup** your current configuration
3. **Obtain** ICS calendar URLs from your calendar provider
4. **Update** configuration file with ICS settings
5. **Test** with `python test_ics.py --url "your-ics-url"`
6. **Restart** the application

### 🔮 Future Roadmap

#### Planned for v2.1
- Multiple ICS source support
- Enhanced e-ink display integration
- CalDAV two-way synchronization
- Advanced event filtering and categorization

#### Under Consideration
- Web dashboard interface
- Mobile companion app
- Advanced recurring event handling
- Integration with smart home systems

---

## [1.2.0] - 2024-12-15 (Legacy - Microsoft Graph API)

### Added
- Interactive navigation mode
- Enhanced error handling
- Improved display formatting

### Fixed
- Token refresh edge cases
- Cache corruption issues
- Timezone conversion bugs

### Changed
- Updated Microsoft Graph SDK dependencies
- Improved logging and diagnostics

---

## [1.1.0] - 2024-11-20 (Legacy - Microsoft Graph API)

### Added
- Offline mode with cache fallback
- Configurable refresh intervals
- Basic error recovery

### Fixed
- Authentication token expiration
- Network connectivity issues

---

## [1.0.0] - 2024-10-15 (Legacy - Microsoft Graph API)

### Added
- Initial release with Microsoft Graph API integration
- Basic calendar display functionality
- Azure authentication support
- Console output for events

---

## Version Support Policy

| Version | Status | Support Level | End of Life |
|---------|--------|---------------|-------------|
| 2.0.x | **Current** | Full support | TBD |
| 1.x | **Legacy** | Security fixes only | March 2025 |

### Migration Support Timeline

- **January 2025**: v2.0 released with migration guide
- **February 2025**: Migration support and documentation updates
- **March 2025**: End of support for v1.x (Graph API version)

### Getting Help

- **Migration Issues**: See [MIGRATION.md](MIGRATION.md)
- **Installation Problems**: See [INSTALL.md](INSTALL.md)
- **Bug Reports**: Create GitHub issue with version information
- **Feature Requests**: Discuss in GitHub Discussions

---

*For the complete version history and detailed technical changes, see the [Git commit history](https://github.com/your-repo/calendarBot/commits/main).*