#!/bin/bash
# Install CalendarBot Simple Kiosk Desktop Shortcuts

set -euo pipefail

# Auto-detect paths
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
DESKTOP_DIR="$HOME/Desktop"

# Auto-detect username
USERNAME=$(whoami)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Installing CalendarBot Simple Kiosk desktop shortcuts..."
log "Project directory: $PROJECT_DIR"
log "Desktop directory: $DESKTOP_DIR"

# Make sure scripts are executable
chmod +x "$SCRIPT_DIR"/*.sh

# Create desktop directory if it doesn't exist
mkdir -p "$DESKTOP_DIR"

# Create CalendarBot Kiosk launcher shortcut
cat > "$DESKTOP_DIR/CalendarBot-Kiosk.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=CalendarBot Kiosk
Comment=Launch CalendarBot in fullscreen kiosk mode
Icon=calendar
Exec=$SCRIPT_DIR/calendarbot-kiosk.sh
Terminal=false
Categories=Utility;Office;Calendar;
EOF

# Create Stop CalendarBot Kiosk shortcut
cat > "$DESKTOP_DIR/Stop-CalendarBot-Kiosk.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Stop CalendarBot Kiosk
Comment=Exit CalendarBot kiosk mode and return to desktop
Icon=process-stop
Exec=$SCRIPT_DIR/stop-calendarbot-kiosk.sh
Terminal=false
Categories=Utility;Office;Calendar;
EOF

# Make desktop files executable
chmod +x "$DESKTOP_DIR/CalendarBot-Kiosk.desktop"
chmod +x "$DESKTOP_DIR/Stop-CalendarBot-Kiosk.desktop"

log "Desktop shortcuts installed successfully!"
log ""
log "Usage:"
log "  - Double-click 'CalendarBot-Kiosk' to enter kiosk mode"
log "  - Double-click 'Stop-CalendarBot-Kiosk' to exit kiosk mode"
log "  - Or press Alt+F4 while in kiosk mode to exit"
log ""
log "Scripts location: $SCRIPT_DIR"
log "Desktop shortcuts: $DESKTOP_DIR"