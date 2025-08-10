#!/bin/bash
# Stop CalendarBot Kiosk Mode

set -e

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Stopping CalendarBot Kiosk Mode..."

# Kill Chromium browser
if pgrep -f chromium-browser > /dev/null; then
    log "Closing Chromium browser..."
    pkill -f chromium-browser || true
fi

# Optional: Stop CalendarBot web server (comment out if you want to keep it running)
# if pgrep -f "calendarbot.*--web" > /dev/null; then
#     log "Stopping CalendarBot web server..."
#     pkill -f "calendarbot.*--web" || true
# fi

log "Kiosk mode stopped. CalendarBot web server may still be running."