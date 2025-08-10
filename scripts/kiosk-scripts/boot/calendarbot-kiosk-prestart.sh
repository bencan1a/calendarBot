#!/bin/bash
# CalendarBot Kiosk Pre-Start Script
# Ensures system is ready for kiosk operation

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
if [ -z "$TARGET_USER" ]; then
    log "ERROR: Cannot determine target user"
    exit 1
fi

TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)

# Logging
LOG_FILE="/var/log/calendarbot/kiosk-prestart.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting CalendarBot kiosk pre-start checks (user: $TARGET_USER)"

# 1. Verify X11 display is available
if ! xdpyinfo -display :0 >/dev/null 2>&1; then
    log "ERROR: X11 display :0 not available"
    exit 1
fi
log "X11 display :0 verified"

# 2. Check available memory
AVAILABLE_MEM=$(free -m | awk '/^Mem:/{print $7}')
REQUIRED_MEM=300

if [ "$AVAILABLE_MEM" -lt "$REQUIRED_MEM" ]; then
    log "WARNING: Low memory available: ${AVAILABLE_MEM}MB < ${REQUIRED_MEM}MB"
    # Attempt to free memory
    sync
    echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
    log "Memory cleanup attempted"
fi

# 3. Verify network connectivity
if ! /usr/local/bin/calendarbot-wait-for-network.sh --quick; then
    log "WARNING: Network connectivity check failed"
fi

# 4. Check calendar configuration
CALENDAR_CONFIG="$TARGET_HOME/.config/calendarbot/config.yaml"
if [ ! -f "$CALENDAR_CONFIG" ]; then
    log "WARNING: Calendar configuration not found at $CALENDAR_CONFIG"
    log "Will use default configuration or environment variables"
fi

# 5. Verify browser is available
if ! command -v chromium-browser >/dev/null 2>&1; then
    log "ERROR: Chromium browser not installed"
    exit 1
fi

# 6. Setup display for kiosk mode
log "Configuring display for kiosk mode"

# Disable screen blanking
xset -display :0 s off 2>/dev/null || true
xset -display :0 -dpms 2>/dev/null || true
xset -display :0 s noblank 2>/dev/null || true

# Hide cursor
unclutter -display :0 -idle 0.1 -root &

# Set display orientation for 480x800 portrait
xrandr --output HDMI-1 --rotate left 2>/dev/null || true

log "Pre-start checks completed successfully"