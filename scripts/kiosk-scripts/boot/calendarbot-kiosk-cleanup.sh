#!/bin/bash
# CalendarBot Kiosk Cleanup Script
# Cleanup tasks when kiosk service stops

set -euo pipefail

# Auto-detect target user (same logic as system-setup script)
TARGET_USER=""

# Try SUDO_USER first (most reliable when run with sudo)
if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
    TARGET_USER="$SUDO_USER"
fi

# Fall back to first regular user with home directory
if [ -z "$TARGET_USER" ] || [ "$TARGET_USER" = "root" ]; then
    REGULAR_USERS=$(awk -F: '$3 >= 1000 && $3 != 65534 && $1 !~ /^snap/ {print $1}' /etc/passwd)
    for user in $REGULAR_USERS; do
        if [ "$user" != "nobody" ] && [ -d "/home/$user" ]; then
            TARGET_USER="$user"
            break
        fi
    done
fi

# Get user home directory
TARGET_HOME="/home/$TARGET_USER"
if [ -n "$TARGET_USER" ]; then
    TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)
fi

LOG_FILE="/var/log/calendarbot/kiosk-cleanup.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting CalendarBot kiosk cleanup (user: ${TARGET_USER:-unknown})"

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