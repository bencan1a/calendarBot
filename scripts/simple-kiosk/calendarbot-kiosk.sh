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
        "http://localhost:$PORT"
        "http://127.0.0.1:$PORT" 
        "http://$(hostname -I | awk '{print $1}'):$PORT"
        "http://$(hostname).local:$PORT"
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

# Close any existing Chromium windows (optional)
pkill -f chromium-browser 2>/dev/null || true
sleep 1

# Launch Chromium in kiosk mode
log "Launching Chromium kiosk mode..."
exec chromium-browser \
    --kiosk \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --disable-background-timer-throttling \
    --disable-renderer-backgrounding \
    --disable-backgrounding-occluded-windows \
    "$CALENDARBOT_URL"