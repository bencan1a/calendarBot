# Installation Guide

## Prerequisites

- **Python 3.9+** with pip
- **Git** for cloning the repository
- **Internet connection** for calendar feeds

## Quick Installation

```bash
# Clone and setup
git clone <repository-url>
cd calendarBot

# Create virtual environment
python -m venv venv
. venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Setup

Run the interactive setup wizard:

```bash
calendarbot --setup
```

Or set environment variables:

```bash
export CALENDARBOT_ICS_URL="https://example.com/calendar.ics"
export CALENDARBOT_ICS_AUTH_TYPE="none"
```

## Launch

```bash
# Activate environment
. venv/bin/activate

# Interactive mode
calendarbot

# Web interface
calendarbot --web

# E-paper display
calendarbot --epaper
```

## Dependencies

Core Python packages:
- `icalendar>=5.0.0` - ICS calendar parsing
- `httpx>=0.25.0` - HTTP client
- `aiosqlite>=0.19.0` - Async SQLite database
- `pydantic>=2.0.0` - Data validation
- `PyYAML>=6.0` - Configuration

## Kiosk Installation (Dedicated Display)

CalendarBot can be installed as a dedicated kiosk display for always-on calendar viewing. This setup is ideal for wall-mounted displays, reception areas, or dedicated calendar stations.

### Hardware Requirements

**Recommended Setup:**
- **Raspberry Pi Zero 2W** - Single board computer
- **Waveshare 4" 480x800 LCD Module** - Vertical orientation display
- **3D Printed Case** - STL files available in the `STL/` directory
- **MicroSD Card** (16GB+) - For Raspberry Pi OS
- **Power Supply** - 5V micro-USB for Pi Zero 2W

### Kiosk System Dependencies

The kiosk mode requires additional Linux packages:

```bash
sudo apt-get update
sudo apt-get install chromium-browser openbox xdpyinfo xset curl unclutter
```

### Kiosk Installation

1. **Install CalendarBot** (follow Quick Installation steps above)

2. **Run the kiosk installer:**
```bash
cd calendarBot
./kiosk/install.sh
```

The installer will:
- Install systemd service for auto-start
- Configure X11 kiosk environment with Openbox
- Set up auto-login to graphical interface
- Install kiosk management scripts
- Validate the installation

3. **Start the kiosk service:**
```bash
sudo systemctl start calendarbot-kiosk@$(whoami).service
```

### Kiosk Management

**Service Control:**
```bash
# Start kiosk
sudo systemctl start calendarbot-kiosk@$(whoami).service

# Stop kiosk
sudo systemctl stop calendarbot-kiosk@$(whoami).service

# Check status
sudo systemctl status calendarbot-kiosk@$(whoami).service

# View logs
sudo journalctl -u calendarbot-kiosk@$(whoami).service -f
```

**Manual Kiosk Mode:**
```bash
# Start X11 session manually
startx

# Run kiosk script directly
~/bin/start-kiosk.sh
```

### Kiosk Features

- **Auto-start:** Service starts automatically on boot
- **Auto-login:** User automatically logs into graphical interface on tty1
- **Full-screen display:** Chromium runs in kiosk mode
- **Screen management:** Disables screensaver and power management
- **Mouse hiding:** Cursor hidden during inactivity
- **Network resilience:** Waits for CalendarBot service and retries on failure

### Kiosk Configuration Files

The kiosk installation creates several configuration files:

- `~/.xinitrc` - X11 startup configuration
- `~/.bash_profile` - Auto-start X11 on tty1 login
- `~/bin/start-kiosk.sh` - Kiosk startup script
- `/etc/systemd/system/calendarbot-kiosk@.service` - Systemd service template

### Kiosk Troubleshooting

**Service not starting:**
```bash
# Check service status
sudo systemctl status calendarbot-kiosk@$(whoami).service

# Check CalendarBot is working
calendarbot --web --port 8080

# Verify dependencies
chromium-browser --version && openbox --version
```

**Display issues:**
```bash
# Check X11 display
echo $DISPLAY
xdpyinfo

# Check kiosk logs
cat ~/kiosk/kiosk.log

# Test manual start
~/bin/start-kiosk.sh
```

**Network connectivity:**
```bash
# Check CalendarBot web interface
curl http://$(hostname -I | awk '{print $1}'):8080

# Verify network interface
hostname -I
```

**Uninstall kiosk:**
```bash
./kiosk/install.sh --uninstall
```

## Troubleshooting

**Python version error**:
```bash
python --version  # Check version
# Install newer Python from python.org if needed
```

**Install failures**:
```bash
pip install --upgrade pip
pip install -r requirements.txt