# CalendarBot Framebuffer UI

Lightweight pygame-based calendar display for Raspberry Pi Zero 2W, replacing the heavy X11 + Chromium stack with a minimal-memory framebuffer renderer.

## Overview

**Memory Usage:** ~15-25MB (vs ~260MB for X11+Chromium)
**Startup Time:** <5s (vs ~60s for X11+Chromium)
**Dependencies:** Python + pygame + SDL2
**Target Platform:** Raspberry Pi Zero 2W (512MB RAM)

### What is this?

The framebuffer UI provides a direct-to-hardware rendering solution that eliminates the need for X Windows and a web browser. It uses pygame with SDL2's DRM/KMS backend to render the calendar display directly to the framebuffer.

### Key Benefits

- **94% memory reduction** - From ~260MB to ~15MB
- **12x faster startup** - From ~60s to <5s
- **Simpler architecture** - One Python process instead of X11+Chromium stack
- **More reliable** - Fewer failure points, no browser crashes
- **Remote backend support** - Backend can run on different device

## Architecture

```
┌─────────────────────────────────────────────────┐
│ framebuffer_ui/                                 │
│                                                  │
│  main.py ──────► renderer.py ──────► Display   │
│     │               (pygame)                     │
│     ├─► api_client.py ──────► Backend API      │
│     │    (aiohttp)                               │
│     └─► layout_engine.py                        │
│          (data transformation)                   │
└─────────────────────────────────────────────────┘
```

### Dual-Loop Design

The framebuffer UI uses a **dual-loop architecture** that decouples data fetching from display rendering:

- **Data Refresh Loop** (slow - 60s default): Fetches fresh data from the backend API
- **Display Refresh Loop** (fast - 5s default): Renders the display using cached data

Between API calls, the countdown is calculated locally by adjusting `seconds_until_start` based on elapsed time. This keeps the display responsive (updating every 5 seconds) while minimizing backend API load.

**Benefits:**
- Countdown timers update every 5 seconds (vs 60 seconds with single loop)
- Status messages ("Starting soon", "Starting very soon") update at exact threshold crossings
- Minimal resource overhead (+0.5% CPU, +1MB RAM)
- Backend API calls remain at configured interval (default: 60s)

### Components

- **[main.py](main.py)** - Entry point and event loop coordinator
- **[renderer.py](renderer.py)** - Pygame framebuffer rendering (3-zone layout)
- **[api_client.py](api_client.py)** - Async HTTP client for `/api/whats-next`
- **[layout_engine.py](layout_engine.py)** - Data transformation and formatting
- **[config.py](config.py)** - Configuration from environment variables
- **[fonts/](fonts/)** - Bundled DejaVu Sans TTF fonts

## Installation

### Prerequisites

```bash
# System dependencies (SDL2, DRM)
sudo apt-get install -y libsdl2-2.0-0 libsdl2-ttf-2.0-0 libdrm2 libgbm1

# Python 3.12+ with virtual environment
python3 --version  # Should be 3.12 or higher
```

### Recommended: TTY Auto-Login Installation

**This is the recommended approach** - it runs the framebuffer UI from a TTY login, which gives pygame proper access to framebuffer drivers.

```bash
# Run installer as root
cd ~/calendarbot
sudo ./framebuffer_ui/install-tty-kiosk.sh USERNAME

# Example:
sudo ./framebuffer_ui/install-tty-kiosk.sh bencan

# Reboot to start kiosk
sudo reboot
```

The installer will:
1. Make startup script executable
2. Configure auto-login on TTY1
3. Add kiosk startup to .bash_profile
4. Disable systemd services (if any)

**See [INSTALL_TTY_KIOSK.md](INSTALL_TTY_KIOSK.md) for complete documentation.**

### Alternative: Systemd Service (May Not Work)

⚠️ **Note:** Systemd service may not work properly on Raspberry Pi because pygame's SDL2 framebuffer drivers require TTY context. Use TTY auto-login instead.

```bash
# Run installer as root
cd ~/calendarbot
sudo ./framebuffer_ui/install-framebuffer-ui.sh USERNAME

# Example:
sudo ./framebuffer_ui/install-framebuffer-ui.sh bencan
```

The installer will:
1. Install system dependencies
2. Install pygame in virtualenv
3. Add user to `video` group
4. Install systemd service
5. Enable and start the service

### Manual Installation

```bash
# 1. Install Python dependencies
cd ~/calendarbot
source venv/bin/activate
pip install pygame>=2.5.0

# 2. Add user to video group (for framebuffer access)
sudo usermod -a -G video $USER

# 3. Install systemd service
sudo cp framebuffer_ui/calendarbot-display@.service /etc/systemd/system/
sudo systemctl daemon-reload

# 4. Enable and start service
sudo systemctl enable calendarbot-display@$USER.service
sudo systemctl start calendarbot-display@$USER.service

# 5. Check status
sudo systemctl status calendarbot-display@$USER.service
```

## Configuration

All configuration is via environment variables in `.env` file:

```bash
# Backend API URL (required)
CALENDARBOT_BACKEND_URL=http://localhost:8080

# Display settings (optional)
CALENDARBOT_DISPLAY_WIDTH=480      # Default: 480
CALENDARBOT_DISPLAY_HEIGHT=800     # Default: 800
CALENDARBOT_DISPLAY_ROTATION=0     # 0, 90, 180, 270

# Refresh intervals (optional)
CALENDARBOT_REFRESH_INTERVAL=60             # API data refresh in seconds (default: 60)
CALENDARBOT_DISPLAY_REFRESH_INTERVAL=5      # Display render refresh in seconds (default: 5)

# Logging (optional)
CALENDARBOT_LOG_LEVEL=INFO         # DEBUG, INFO, WARNING, ERROR
```

### Remote Backend Support

The framebuffer UI can connect to a backend running on a different device:

```bash
# In .env on Raspberry Pi:
CALENDARBOT_BACKEND_URL=http://192.168.1.100:8080
```

This allows you to run the backend on a more powerful machine while keeping the lightweight display on the Pi.

## Usage

### Running Directly (Testing)

```bash
# Activate virtual environment
cd ~/calendarbot
source venv/bin/activate

# Run the UI (video driver auto-detected)
python -m framebuffer_ui

# Or override video driver if needed
export SDL_VIDEODRIVER=fbcon  # Force specific driver
python -m framebuffer_ui
```

**Note:** The UI automatically tries video drivers in order: `kmsdrm` → `fbcon` → `dummy`. You only need to set `SDL_VIDEODRIVER` manually if you want to force a specific driver.

### systemd Service (Production)

```bash
# Start service
sudo systemctl start calendarbot-display@USERNAME.service

# Stop service
sudo systemctl stop calendarbot-display@USERNAME.service

# Restart service
sudo systemctl restart calendarbot-display@USERNAME.service

# View logs
journalctl -u calendarbot-display@USERNAME.service -f

# Check status
sudo systemctl status calendarbot-display@USERNAME.service
```

## Testing

### Component Tests (No Display Required)

```bash
# Test API client and layout engine
python test_framebuffer_components.py
```

Output:
```
✓ Test 1 passed: Normal meeting (9h away)
✓ Test 2 passed: Critical meeting (3m away)
✓ Test 3 passed: No meetings
✅ Layout engine tests passed!
✅ API client test passed!
```

### Visual Tests (Requires Display)

```bash
# Test with mock data (requires X11 or framebuffer)
python test_framebuffer_ui.py --mock

# Test with live backend
python test_framebuffer_ui.py
```

### Testing on Windows/Mac (Development)

For development on non-Linux systems, pygame will fall back to windowed mode:

```bash
# Will open a 480x800 window
export SDL_VIDEODRIVER=x11  # or 'cocoa' on Mac
python -m framebuffer_ui
```

## Display Layout

The UI matches the HTML/CSS design with 3 zones:

```
┌─────────────────────────────┐
│ Zone 1: Countdown (300px)   │  ← Gray background, large number
│   "STARTS IN"               │
│   "9 HOURS"                 │
│   "58 MINUTES"              │
├─────────────────────────────┤
│ Zone 2: Meeting (400px)     │  ← White card with shadow
│   "Meeting Title..."        │
│   "07:00 AM - 08:00 AM"     │
│   "Location"                │
├─────────────────────────────┤
│ Zone 3: Status (100px)      │  ← Gray background, status text
│   "Starting soon"           │
└─────────────────────────────┘
480x800 pixels total
```

### Visual States

- **Normal** - Meeting >15 minutes away (gray background)
- **Warning** - Meeting 5-15 minutes away (light yellow)
- **Critical** - Meeting <5 minutes away (light red)

## Troubleshooting

### Service Won't Start

```bash
# View detailed logs
journalctl -u calendarbot-display@USERNAME.service -n 50

# Check if pygame can access framebuffer
sudo -u USERNAME /home/USERNAME/calendarbot/venv/bin/python -c "import pygame; pygame.init()"
```

### Permission Denied on /dev/dri/card0

```bash
# Add user to video group
sudo usermod -a -G video USERNAME

# Logout and login again (or reboot)
sudo reboot
```

### SDL Error: No available video device

The UI automatically tries multiple video drivers (kmsdrm → fbcon → dummy), but if all fail:

```bash
# Check if framebuffer/DRM devices exist
ls -la /dev/dri/  # DRM/KMS devices (for kmsdrm driver)
ls -la /dev/fb0   # Legacy framebuffer (for fbcon driver)

# Check permissions
groups  # Should include 'video' group

# View detailed error logs
journalctl -u calendarbot-display@USERNAME.service -n 50

# Force specific driver (for debugging)
export SDL_VIDEODRIVER=fbcon
python -m framebuffer_ui
```

**Common causes:**
- Missing `/dev/fb0` or `/dev/dri/card0` - Driver modules not loaded
- Permission denied - User not in `video` group
- Display already in use - Another process using the framebuffer

### Memory Usage Higher Than Expected

```bash
# Check actual memory usage
ps aux | grep framebuffer_ui

# Expected: ~15-25MB RSS
# If higher, check for memory leaks in logs
```

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Memory (RSS) | <25MB | ~15MB ✓ |
| Startup Time | <15s | <5s ✓ |
| CPU (idle) | <2% | <1% ✓ |
| API Latency | <1s | <100ms ✓ |

## Migration from X11 Kiosk

To switch from the old X11+Chromium kiosk to framebuffer UI:

```bash
# 1. Install framebuffer UI
sudo ./framebuffer_ui/install-framebuffer-ui.sh USERNAME

# 2. Disable old kiosk
sudo systemctl disable calendarbot-kiosk-watchdog@USERNAME.service
sudo systemctl stop calendarbot-kiosk-watchdog@USERNAME.service

# 3. Reboot to start framebuffer UI
sudo reboot
```

### Rollback to X11 Kiosk

If you need to revert:

```bash
# 1. Stop framebuffer UI
sudo systemctl disable calendarbot-display@USERNAME.service
sudo systemctl stop calendarbot-display@USERNAME.service

# 2. Re-enable X11 kiosk
sudo systemctl enable calendarbot-kiosk-watchdog@USERNAME.service
sudo systemctl start calendarbot-kiosk-watchdog@USERNAME.service

# 3. Reboot
sudo reboot
```

## Development

### Project Structure

```
framebuffer_ui/
├── __init__.py              # Package initialization
├── __main__.py              # Entry point for -m flag
├── main.py                  # Main application logic
├── renderer.py              # Pygame framebuffer rendering
├── api_client.py            # Async HTTP client
├── layout_engine.py         # Data transformation
├── config.py                # Configuration management
├── fonts/                   # Bundled TTF fonts
│   ├── DejaVuSans.ttf
│   ├── DejaVuSans-Bold.ttf
│   └── README.md
├── calendarbot-display@.service  # systemd unit file
├── install-framebuffer-ui.sh     # Installation script
└── README.md                     # This file
```

### Adding New Features

1. **Modify layout** - Edit [renderer.py](renderer.py) to change visual design
2. **Change data processing** - Edit [layout_engine.py](layout_engine.py)
3. **Adjust API polling** - Edit [api_client.py](api_client.py)
4. **Add configuration** - Edit [config.py](config.py)

### Running Tests

```bash
# Component tests (no display)
python test_framebuffer_components.py

# Visual tests (requires display)
python test_framebuffer_ui.py --mock

# Live backend test
python test_framebuffer_ui.py
```

## License

Same as CalendarBot project (see root LICENSE file).

## Credits

- **Architecture Design**: Based on approved lightweight UI plan
- **Fonts**: DejaVu Sans (Bitstream Vera license)
- **Rendering**: pygame 2.5+ with SDL2 backend

## See Also

- [Project Architecture Plan](../project-plans/lightweight-ui-architecture.md)
- [CalendarBot Lite Documentation](../calendarbot_lite/README.md)
- [Kiosk Installation](../kiosk/README.md)
