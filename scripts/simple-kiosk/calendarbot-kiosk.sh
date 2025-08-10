#!/bin/bash
# CalendarBot Kiosk Mode Launcher

set -e

# Auto-detect script directory
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

# Configuration
PORT=8080
STARTUP_WAIT=5

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Function to find CalendarBot URL
find_calendarbot_url() {
    # Try common URLs in order of preference
    local urls=(
        "http://192.168.1.225:$PORT"
        # "http://127.0.0.1:$PORT" 
        # "http://$(hostname -I | awk '{print $1}'):$PORT"
        # "http://$(hostname).local:$PORT"
    )
    
    for url in "${urls[@]}"; do
        if curl -s --connect-timeout 2 "$url" > /dev/null 2>&1; then
            echo "$url"
            return 0
        fi
    done
    
    # Default fallback
    echo "http://localhost:$PORT"
    return 1
}

log "Starting CalendarBot Kiosk Mode..."

# Start CalendarBot web server if not running
if ! pgrep -f "calendarbot.*--web" > /dev/null; then
    log "CalendarBot not running, starting web server..."
    "$SCRIPT_DIR/start-calendarbot.sh" &
    
    log "Waiting $STARTUP_WAIT seconds for server to start..."
    sleep $STARTUP_WAIT
else
    log "CalendarBot web server already running"
fi

# Detect the correct URL
CALENDARBOT_URL=$(find_calendarbot_url)
log "Using CalendarBot URL: $CALENDARBOT_URL"

# Test connection
if ! curl -s --connect-timeout 5 "$CALENDARBOT_URL" > /dev/null; then
    log "WARNING: Could not connect to $CALENDARBOT_URL"
    log "CalendarBot may still be starting up..."
fi

# Configure display for kiosk mode
log "Configuring display for kiosk mode..."

# Disable screen blanking and power management (if X11 is available)
if command -v xset > /dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
    log "Disabling screen blanking and power management"
    xset -display "${DISPLAY:-:0}" s off 2>/dev/null || true
    xset -display "${DISPLAY:-:0}" -dpms 2>/dev/null || true
    xset -display "${DISPLAY:-:0}" s noblank 2>/dev/null || true
else
    log "X11 not available, skipping display configuration"
fi

# Hide cursor (if unclutter is available)
if command -v unclutter > /dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
    log "Starting cursor hiding utility"
    # Kill any existing unclutter processes
    pkill -f unclutter 2>/dev/null || true
    # Start unclutter to hide cursor after 1 second of inactivity
    unclutter -display "${DISPLAY:-:0}" -idle 1 -root &
else
    log "unclutter not available, cursor will remain visible"
fi

# Optional: Set display orientation (uncomment if needed)
# if command -v xrandr > /dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
#     log "Setting display orientation"
#     xrandr --output HDMI-1 --rotate left 2>/dev/null || true
# fi

# Close any existing Chromium windows
log "Closing existing Chromium windows..."
pkill -f chromium-browser 2>/dev/null || true
sleep 2

# Launch Chromium in comprehensive kiosk mode
log "Launching Chromium in comprehensive kiosk mode..."
exec chromium-browser \
    --kiosk \
    --start-fullscreen \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --disable-background-timer-throttling \
    --disable-renderer-backgrounding \
    --disable-backgrounding-occluded-windows \
    --disable-features=TranslateUI,BlinkGenPropertyTrees \
    --disable-ipc-flooding-protection \
    --disable-background-networking \
    --disable-sync \
    --disable-translate \
    --disable-extensions \
    --disable-plugins \
    --disable-default-apps \
    --disable-component-extensions-with-background-pages \
    --no-default-browser-check \
    --no-first-run \
    --noerrdialogs \
    --disable-logging \
    --disable-gpu-logging \
    --silent-debugger-extension-api \
    --overscroll-history-navigation=0 \
    --window-position=0,0 \
    --app="$CALENDARBOT_URL"