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
    sleep 1
fi

# Kill cursor hiding utility
if pgrep -f unclutter > /dev/null; then
    log "Stopping cursor hiding utility..."
    pkill -f unclutter || true
fi

# Restore display settings (if X11 is available)
if command -v xset > /dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
    log "Restoring display power management..."
    xset -display "${DISPLAY:-:0}" s default 2>/dev/null || true
    xset -display "${DISPLAY:-:0}" +dpms 2>/dev/null || true
else
    log "X11 not available, skipping display restoration"
fi

# Optional: Stop CalendarBot web server (comment out if you want to keep it running)
# if pgrep -f "calendarbot.*--web" > /dev/null; then
#     log "Stopping CalendarBot web server..."
#     pkill -f "calendarbot.*--web" || true
# fi

log "Kiosk mode stopped. CalendarBot web server may still be running."
log "Desktop display settings restored."