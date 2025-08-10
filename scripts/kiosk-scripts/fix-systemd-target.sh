#!/bin/bash
# Quick fix for systemd target issue
# Fixes graphical-session.target -> graphical.target

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

KIOSK_SERVICE="/etc/systemd/system/calendarbot-kiosk.service"

if [ ! -f "$KIOSK_SERVICE" ]; then
    echo "ERROR: Service file not found: $KIOSK_SERVICE"
    exit 1
fi

echo "Fixing systemd target reference in calendarbot-kiosk.service..."

# Backup the service file
cp "$KIOSK_SERVICE" "${KIOSK_SERVICE}.backup.target.$(date +%Y%m%d_%H%M%S)"

# Fix the target references
sed -i 's/graphical-session\.target/graphical.target/g' "$KIOSK_SERVICE"

echo "Fixed systemd target references:"
echo "  graphical-session.target -> graphical.target"

# Reload systemd daemon
systemctl daemon-reload

echo "Systemd configuration reloaded"
echo ""
echo "You can now restart the service:"
echo "  sudo systemctl restart calendarbot-kiosk.service"