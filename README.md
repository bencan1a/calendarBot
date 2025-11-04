# CalendarBot Lite

📅 **A lightweight Alexa skill backend and web API for ICS calendar processing with Raspberry Pi kiosk deployment**

CalendarBot Lite provides focused ICS calendar parsing, RRULE expansion, and natural language calendar responses via Alexa, with a production-ready Raspberry Pi kiosk deployment system featuring auto-login, watchdog monitoring, and a real-time "What's Next" display interface.

---

## Features

- 🖥️ **Raspberry Pi Kiosk Deployment** - Production-ready kiosk system with auto-login, watchdog monitoring, and automated installation
- 📺 **Kiosk Display** - Real-time "What's Next" meeting countdown interface with browser heartbeat monitoring
- 🗣️ **Alexa Integration** - Natural language calendar queries via Alexa voice commands
- 📅 **ICS Calendar Processing** - RFC 5545 compliant parsing with RRULE expansion
- 🌐 **Web API** - REST endpoints for calendar data and health monitoring
- 🔄 **Background Refresh** - Automatic calendar updates with configurable intervals
- ⏰ **Timezone Support** - Intelligent timezone conversion and handling
- 🎯 **Event Prioritization** - Smart ranking and filtering of calendar events

---

## Quick Start

### Prerequisites

- Python 3.12+
- ICS calendar feed URL (Office 365, Google Calendar, iCloud, etc.)

### Installation

```bash
# Clone repository
git clone https://github.com/bencan1a/calendarBot.git
cd calendarBot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your ICS_URL and other settings
```

### Configuration

Create a `.env` file with your calendar feed URL:

```bash
# Required: ICS calendar feed URL
CALENDARBOT_ICS_URL=https://outlook.office365.com/owa/calendar/your-calendar/calendar.ics

# Optional: Server configuration
CALENDARBOT_WEB_HOST=0.0.0.0
CALENDARBOT_WEB_PORT=8080
CALENDARBOT_REFRESH_INTERVAL=300

# Optional: Alexa integration
CALENDARBOT_ALEXA_BEARER_TOKEN=your-bearer-token

# Optional: Debug logging
CALENDARBOT_DEBUG=true
```

See [`.env.example`](.env.example) for complete configuration options.

### Run the Server

```bash
python -m calendarbot_lite
```

The server will start on `http://0.0.0.0:8080` by default.

---

## Raspberry Pi Kiosk Deployment

### Overview

The `kiosk/` directory provides a **production-ready Raspberry Pi kiosk deployment system** designed for 24/7 calendar display operation. This is a **primary use case** for CalendarBot Lite.

**Key Features:**
- 🚀 **Automated Installation** - One-command deployment with `install-kiosk.sh`
- 🔄 **Auto-Login & X Session** - Console auto-login triggers kiosk display on boot
- 🩺 **Watchdog Monitoring** - Health checks with progressive recovery (soft reload → browser restart → X restart)
- 💓 **Browser Heartbeat** - Detects stuck/frozen browsers via JavaScript heartbeats
- 📊 **Resource Monitoring** - Degraded mode under system load
- 🔧 **Idempotent Configuration** - Safe to re-run installation without side effects

### Quick Start: Automated Kiosk Installation

```bash
# 1. Configure
cd ~/calendarBot/kiosk
cp install-config.example.yaml install-config.yaml
nano install-config.yaml  # Set your username and ICS URL

# 2. Preview changes (dry-run)
sudo ./install-kiosk.sh --config install-config.yaml --dry-run

# 3. Install
sudo ./install-kiosk.sh --config install-config.yaml

# 4. Reboot to start kiosk mode
sudo reboot
```

**After reboot**, the system will:
- Auto-login to console
- Launch X session via `.bash_profile` → `.xinitrc`
- Start Chromium in kiosk mode displaying the calendar
- Begin watchdog monitoring with progressive recovery

### Kiosk Architecture

```
Boot → systemd
  ├─> calendarbot-lite@user.service (CalendarBot server on port 8080)
  ├─> Auto-login to tty1 → .bash_profile → startx → .xinitrc → Chromium
  └─> calendarbot-kiosk-watchdog@user.service (health monitoring & recovery)
```

### Progressive Recovery System

The watchdog monitors browser health via JavaScript heartbeats and uses 3-level escalation:

1. **Level 0: Soft Reload** (~15s) - Send F5 key via xdotool for page rendering issues
2. **Level 1: Browser Restart** (~30s) - Kill and relaunch browser for memory leaks
3. **Level 2: X Session Restart** (~60s) - Full X restart for display problems

Recovery escalates after **2 consecutive** heartbeat failures, with automatic de-escalation when health resumes.

### Kiosk Documentation

See the **[kiosk/README.md](kiosk/README.md)** for complete documentation:

- **[Automated Installation Guide](kiosk/docs/AUTOMATED_INSTALLATION.md)** - Complete automation guide
- **[Manual Steps Guide](kiosk/docs/MANUAL_STEPS.md)** - DNS, AWS Lambda, Alexa skill setup
- **[Installation Overview](kiosk/docs/INSTALLATION_OVERVIEW.md)** - Architecture & workflow
- **[Deployment Checklist](kiosk/docs/DEPLOYMENT_CHECKLIST.md)** - Verification checklists
- **[File Inventory](kiosk/docs/FILE_INVENTORY.md)** - Complete file reference

### Kiosk Service Management

```bash
# Check service status
systemctl status calendarbot-lite@bencan.service
systemctl status calendarbot-kiosk-watchdog@bencan.service

# View watchdog logs
journalctl -u calendarbot-kiosk-watchdog@bencan.service -f

# Restart X session (triggers full kiosk restart)
sudo systemctl restart auto-login-x-session

# Test browser heartbeat
curl -X POST http://127.0.0.1:8080/api/browser-heartbeat
curl -s http://127.0.0.1:8080/api/health | jq '.display_probe'
```

---

## Usage

### Kiosk Display (Primary Use Case)

For production Raspberry Pi deployment with auto-login and watchdog monitoring, see the **[Raspberry Pi Kiosk Deployment](#raspberry-pi-kiosk-deployment)** section above.

For development/testing, open your browser to `http://localhost:8080` to view the "What's Next" kiosk interface showing upcoming meetings with countdown timers.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | What's Next kiosk display interface |
| `/whatsnext.css` | GET | Kiosk display stylesheet |
| `/whatsnext.js` | GET | Kiosk display JavaScript |
| `/api/health` | GET | Detailed health status with metrics |
| `/api/whats-next` | GET | Get next upcoming events |
| `/api/done-for-day` | GET | Last meeting end time |
| `/api/morning-summary` | POST | Morning briefing data |
| `/api/skip` | POST | Skip a meeting by ID |
| `/api/clear_skips` | GET | Clear skipped meetings and force refresh |
| `/api/alexa/*` | GET/POST | Alexa skill webhook endpoints |

### Example API Calls

```bash
# Check server health
curl http://localhost:8080/api/health

# Get upcoming events
curl http://localhost:8080/api/whats-next

# Check if done for the day
curl http://localhost:8080/api/done-for-day

# Clear skipped meetings
curl http://localhost:8080/api/clear_skips
```

### Alexa Integration

Configure your Alexa skill to point to `https://your-server.com/api/alexa/*`. The skill supports intents for:
- Next meeting information
- Time until next meeting
- Morning briefings
- Daily summaries

See [docs/ALEXA_DEPLOYMENT_GUIDE.md](docs/ALEXA_DEPLOYMENT_GUIDE.md) for complete Alexa setup instructions.

---

## Calendar Compatibility

Supports any RFC 5545 compliant ICS calendar feed:
- ✅ Microsoft Outlook / Office 365
- ✅ Google Calendar
- ✅ Apple iCloud Calendar
- ✅ CalDAV servers (Nextcloud, Radicale, SOGo)
- ✅ Any standard ICS feed

---

## Development

### Running Tests

```bash
# Run all calendarbot_lite tests
./run_lite_tests.sh

# Run with coverage report
./run_lite_tests.sh --coverage

# Run specific tests
pytest tests/lite/ -v

# Run fast tests only
pytest tests/lite/ -m "fast"

# Skip slow tests
pytest tests/lite/ -m "not slow"
```

### Project Structure

```
calendarbot_lite/
├── server.py              # Main web server
├── routes/                # HTTP route handlers
│   ├── alexa_routes.py    # Alexa webhook
│   ├── api_routes.py      # REST API
│   └── static_routes.py   # Kiosk interface
├── alexa_handlers.py      # Alexa intent processing
├── lite_event_parser.py   # ICS parsing
├── lite_rrule_expander.py # Recurring event expansion
└── whatsnext.html/css/js  # Kiosk display interface
```

### Code Quality

```bash
# Format code
ruff format calendarbot_lite

# Lint code
ruff check calendarbot_lite

# Type check
mypy calendarbot_lite
```

---

## Documentation

### Core Documentation

- **[calendarbot_lite/README.md](calendarbot_lite/README.md)** - Module overview
- **[docs/lite/README.md](docs/lite/README.md)** - Complete component documentation
- **[docs/ALEXA_DEPLOYMENT_GUIDE.md](docs/ALEXA_DEPLOYMENT_GUIDE.md)** - Alexa skill deployment
- **[AGENTS.md](AGENTS.md)** - Developer guide for AI agents

### Kiosk Deployment Documentation

- **[kiosk/README.md](kiosk/README.md)** - **Kiosk deployment overview**
- **[kiosk/docs/AUTOMATED_INSTALLATION.md](kiosk/docs/AUTOMATED_INSTALLATION.md)** - Automated kiosk installation
- **[kiosk/docs/INSTALLATION_OVERVIEW.md](kiosk/docs/INSTALLATION_OVERVIEW.md)** - Architecture & workflow
- **[kiosk/docs/DEPLOYMENT_CHECKLIST.md](kiosk/docs/DEPLOYMENT_CHECKLIST.md)** - Verification checklists
- **[kiosk/docs/MANUAL_STEPS.md](kiosk/docs/MANUAL_STEPS.md)** - DNS, AWS Lambda, Alexa setup

### Component Documentation

- [Server & HTTP Routing](docs/lite/01-server-http-routing.md)
- [Alexa Integration](docs/lite/02-alexa-integration.md)
- [Calendar Processing](docs/lite/03-calendar-processing.md)
- [Infrastructure](docs/lite/04-infrastructure.md)
- [Configuration & Dependencies](docs/lite/05-configuration-dependencies.md)

---

## Deployment

### Raspberry Pi Kiosk (Recommended for Production)

For production deployment on Raspberry Pi with auto-login, watchdog monitoring, and kiosk display:

```bash
cd ~/calendarBot/kiosk
sudo ./install-kiosk.sh --config install-config.yaml
```

See the **[Raspberry Pi Kiosk Deployment](#raspberry-pi-kiosk-deployment)** section and **[kiosk/README.md](kiosk/README.md)** for complete instructions.

### Production Mode (Development/Testing)

Enable production optimizations for non-kiosk deployments:

```bash
CALENDARBOT_PRODUCTION=true python -m calendarbot_lite
```

### Docker (Coming Soon)

```bash
# Build and run with docker-compose
docker-compose up -d
```

### Systemd Service

See [docs/ALEXA_DEPLOYMENT_GUIDE.md](docs/ALEXA_DEPLOYMENT_GUIDE.md) for systemd service configuration.

---

## Architecture

CalendarBot Lite uses an async-first architecture with:

- **aiohttp** - Async web server
- **icalendar** - RFC 5545 compliant ICS parsing
- **python-dateutil** - RRULE expansion and timezone handling
- **pydantic** - Data validation and settings management

Key patterns:
- Registry pattern for Alexa intent handlers
- Background tasks for calendar refresh
- TTL-based response caching
- Health monitoring and metrics

---

## Archived Legacy Project

> **Note**: The original `calendarbot/` terminal and web UI application is now **ARCHIVED** and no longer maintained.
>
> See [calendarbot/DEPRECATED.md](calendarbot/DEPRECATED.md) for migration information.

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `./run_lite_tests.sh`
5. Format code: `ruff format calendarbot_lite`
6. Submit a pull request

---

## License

[Add your license here]

---

## Support

- **Issues**: [GitHub Issues](https://github.com/bencan1a/calendarBot/issues)
- **Documentation**: See [docs/lite/](docs/lite/) for detailed guides
- **Questions**: Open a discussion on GitHub