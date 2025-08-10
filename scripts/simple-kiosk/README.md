# CalendarBot Simple Kiosk Mode

A safe, simple way to run CalendarBot in fullscreen kiosk mode without risky system modifications.

## Features

- **On-demand kiosk mode** - Launch when you want it
- **No system modifications** - No boot configuration changes
- **Smart URL detection** - Works with localhost, IP, or hostname
- **Auto-startup** - Starts CalendarBot web server if not running
- **Easy exit** - Press Alt+F4 or click stop shortcut
- **Desktop shortcuts** - One-click launch from desktop

## Installation

1. **Install CalendarBot prerequisites:**
   ```bash
   sudo apt update
   sudo apt install -y python3-venv python3-pip chromium-browser unclutter
   ```

2. **Set up CalendarBot virtual environment:**
   ```bash
   cd /path/to/calendarBot
   python3 -m venv venv
   source venv/bin/activate
   pip install -e .
   ```

3. **Install desktop shortcuts:**
   ```bash
   ./scripts/simple-kiosk/install-desktop-shortcuts.sh
   ```

## Usage

### Desktop Shortcuts (Recommended)
- **Start:** Double-click "CalendarBot-Kiosk" on desktop
- **Stop:** Double-click "Stop-CalendarBot-Kiosk" or press Alt+F4

### Command Line
```bash
# Enter kiosk mode
./scripts/simple-kiosk/calendarbot-kiosk.sh

# Exit kiosk mode  
./scripts/simple-kiosk/stop-calendarbot-kiosk.sh

# Start just the web server
./scripts/simple-kiosk/start-calendarbot.sh
```

## How It Works

1. **start-calendarbot.sh** - Starts CalendarBot web server on port 8080
2. **calendarbot-kiosk.sh** - Launches Chromium in fullscreen kiosk mode
3. **stop-calendarbot-kiosk.sh** - Closes Chromium (keeps web server running)

## Service Setup (Optional)

To convert this to a proper systemd service later:

```bash
# Create user service
cat > ~/.config/systemd/user/calendarbot-web.service << EOF
[Unit]
Description=CalendarBot Web Server
After=graphical-session.target

[Service]
Type=simple
ExecStart=/path/to/calendarBot/scripts/simple-kiosk/start-calendarbot.sh
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

# Enable and start
systemctl --user daemon-reload
systemctl --user enable calendarbot-web.service
systemctl --user start calendarbot-web.service
```

## Troubleshooting

- **"Connection refused":** CalendarBot web server may still be starting, wait a few seconds
- **"Command not found":** Make sure scripts are executable: `chmod +x scripts/simple-kiosk/*.sh`
- **Desktop shortcuts don't work:** Run `./scripts/simple-kiosk/install-desktop-shortcuts.sh`

## Advantages over Full Kiosk Mode

- ✅ No system modifications required
- ✅ No boot configuration changes
- ✅ No risk of boot loops
- ✅ Easy to uninstall (just delete shortcuts)
- ✅ Works on any desktop Linux system
- ✅ Can be version controlled and deployed