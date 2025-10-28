# CalendarBot

> **IMPORTANT**: This README describes the legacy `calendarbot/` application which is now **ARCHIVED**.
> For active development, see **[calendarbot_lite/](calendarbot_lite/)** - the lightweight, focused ICS calendar processor.

---

## Project Status

- **ACTIVE**: [calendarbot_lite/](calendarbot_lite/) - Lightweight ICS parser and calendar processor
- **ARCHIVED**: [calendarbot/](calendarbot/) - Legacy terminal/web-based calendar application (see [DEPRECATED.md](calendarbot/DEPRECATED.md))

The `calendarbot_lite` implementation provides focused ICS parsing, RRULE expansion, and Alexa integration without the complexity of the full web UI and e-paper display system.

---

## Legacy CalendarBot (ARCHIVED)

📅 A terminal and web-based calendar utility that integrates with ICS calendar feeds. Provides interactive calendar navigation, real-time updates, and cross-platform compatibility.

**Note: This implementation is no longer actively maintained. Use [calendarbot_lite/](calendarbot_lite/) for new projects.**

## Features

- 📋 Interactive terminal navigation with keyboard controls
- 🌐 Mobile-friendly web interface with multiple layouts
- 📱 E-paper display support with e-ink optimization
- ⚙️ Built-in setup wizard for quick configuration
- 🔄 Real-time data fetching from any ICS calendar feed
- 💾 Local caching with offline support

## Quick Start

### Installation

```bash
# Clone and setup
git clone <repository-url>
cd calendarBot

# Create virtual environment
python -m venv venv
. venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Setup

```bash
# Interactive setup wizard
calendarbot --setup
```

### Launch

```bash
# Interactive mode
calendarbot

# Web interface
calendarbot --web

# E-paper display
calendarbot --epaper
```

## Calendar Compatibility

Supports any RFC 5545 compliant calendar system:
- Microsoft Outlook/Office 365
- Google Calendar  
- Apple iCloud Calendar
- CalDAV servers (Nextcloud, Radicale, SOGo)
- Any direct ICS feed

## Documentation

- **[Installation Guide](docs/INSTALL.md)** - Complete setup instructions
- **[Usage Guide](docs/USAGE.md)** - Operation modes and configuration
- **[Architecture Overview](docs/ARCHITECTURE.md)** - System design and components
- **[Testing Guide](docs/TESTING.md)** - Development and testing workflow

## Development

### Requirements

- Python 3.9+
- Virtual environment recommended

### Quick Test

```bash
# Activate environment
. venv/bin/activate

# Run tests
pytest

# System validation
calendarbot --test-mode
```

## Configuration

### Environment Variables

```bash
export CALENDARBOT_ICS_URL="https://example.com/calendar.ics"
export CALENDARBOT_ICS_AUTH_TYPE="none"
```

### YAML Configuration

Create `config.yaml`:

```yaml
ics:
  url: "https://calendar.example.com/calendar.ics"
  auth_type: "none"

web:
  enabled: true
  port: 8080
  theme: "4x8"
```

## Web Interface Layouts

- **4x8**: Standard desktop layout (480x800px)
- **3x4**: Compact layout (300x400px)  
- **whats-next-view**: Meeting countdown display

## License

[Add your license here]

## Support

- **Issues**: Report bugs and feature requests via GitHub Issues
- **Documentation**: See `docs/` folder for detailed guides
- **Testing**: Use `calendarbot --test-mode` for system validation