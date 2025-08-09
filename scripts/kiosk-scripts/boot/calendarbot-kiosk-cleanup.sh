#!/bin/sh
# CalendarBot Kiosk Cleanup Script
# Cleanup tasks when kiosk service stops

set -euo pipefail

LOG_FILE="/var/log/calendarbot/kiosk-cleanup.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting CalendarBot kiosk cleanup"

# 1. Kill any remaining Chromium processes
pkill -f chromium-browser 2>/dev/null || true
pkill -f chrome 2>/dev/null || true
log "Browser processes terminated"

# 2. Kill cursor hiding utility
pkill -f unclutter 2>/dev/null || true

# 3. Clean up temporary files
rm -rf /tmp/calendarbot-kiosk-* 2>/dev/null || true
rm -rf /home/pi/.cache/chromium/Default/GPUCache/* 2>/dev/null || true

# 4. Reset display settings
xset -display :0 s default 2>/dev/null || true
xset -display :0 +dpms 2>/dev/null || true

# 5. Sync filesystem to ensure writes are flushed
sync

log "Cleanup completed"