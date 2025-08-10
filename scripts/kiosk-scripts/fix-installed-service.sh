#!/bin/bash
# Quick fix for already-installed CalendarBot kiosk service
# Fixes deprecated MemoryLimit and hardcoded user references

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Fixing CalendarBot kiosk service configuration..."

# Auto-detect target user
TARGET_USER=""

# Try SUDO_USER first
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

if [ -z "$TARGET_USER" ] || [ "$TARGET_USER" = "root" ]; then
    echo "ERROR: Cannot determine target user"
    exit 1
fi

TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)
TARGET_UID=$(id -u "$TARGET_USER")

echo "Detected user: $TARGET_USER (UID: $TARGET_UID, Home: $TARGET_HOME)"

KIOSK_SERVICE="/etc/systemd/system/calendarbot-kiosk.service"
NETWORK_SERVICE="/etc/systemd/system/calendarbot-network-wait.service"

if [ ! -f "$KIOSK_SERVICE" ] && [ ! -f "$NETWORK_SERVICE" ]; then
    echo "ERROR: No CalendarBot services found in /etc/systemd/system/"
    echo "CalendarBot services don't appear to be installed"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup existing service files
if [ -f "$KIOSK_SERVICE" ]; then
    cp "$KIOSK_SERVICE" "${KIOSK_SERVICE}.backup.${TIMESTAMP}"
    echo "Backed up kiosk service file"
fi

if [ -f "$NETWORK_SERVICE" ]; then
    cp "$NETWORK_SERVICE" "${NETWORK_SERVICE}.backup.${TIMESTAMP}"
    echo "Backed up network service file"
fi

# Fix the kiosk service file
if [ -f "$KIOSK_SERVICE" ]; then
    echo "Fixing kiosk service file..."
    cat > "$KIOSK_SERVICE" << EOF
[Unit]
Description=CalendarBot Kiosk Mode Display
Documentation=https://github.com/your-org/calendarbot
After=graphical.target network-online.target calendarbot-kiosk-setup.service
Wants=network-online.target
Requires=graphical.target calendarbot-kiosk-setup.service

# Conflict with other display managers to prevent conflicts
Conflicts=gdm.service lightdm.service sddm.service

[Service]
Type=simple
User=$TARGET_USER
Group=$TARGET_USER

# Environment setup
Environment=DISPLAY=:0
Environment=HOME=$TARGET_HOME
Environment=XDG_RUNTIME_DIR=/run/user/$TARGET_UID
Environment=XDG_SESSION_TYPE=x11
Environment=QT_QPA_PLATFORM=xcb
Environment=XAUTHORITY=$TARGET_HOME/.Xauthority

# Working directory
WorkingDirectory=$TARGET_HOME/calendarbot

# Startup delay to ensure system readiness
ExecStartPre=/bin/sleep 30
ExecStartPre=/usr/local/bin/calendarbot-kiosk-prestart.sh

# Main kiosk process
ExecStart=$TARGET_HOME/calendarbot/venv/bin/python -m calendarbot --kiosk
ExecStop=/bin/kill -TERM \$MAINPID
ExecStopPost=/usr/local/bin/calendarbot-kiosk-cleanup.sh

# Process management
KillMode=mixed
KillSignal=SIGTERM
TimeoutStartSec=120
TimeoutStopSec=30

# Restart configuration for reliability
Restart=always
RestartSec=15
StartLimitInterval=300
StartLimitBurst=5

# Resource limits for Pi Zero 2W (512MB RAM)
MemoryMax=400M
CPUQuota=80%
IOSchedulingClass=2
IOSchedulingPriority=4

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$TARGET_HOME/.config/calendarbot /tmp /var/log/calendarbot

# Additional security
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
RestrictRealtime=true

[Install]
WantedBy=graphical.target
EOF

    echo "Kiosk service file updated successfully"
fi

# Fix the network wait service file
if [ -f "$NETWORK_SERVICE" ]; then
    echo "Fixing network wait service file..."
    cat > "$NETWORK_SERVICE" << EOF
[Unit]
Description=Wait for network connectivity before starting kiosk
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=true
ExecStart=/usr/local/bin/calendarbot-wait-for-network.sh
TimeoutStartSec=180
User=$TARGET_USER

[Install]
WantedBy=network-online.target
EOF
    echo "Network wait service file updated successfully"
fi

# Reload systemd
systemctl daemon-reload

echo "Systemd configuration reloaded"
echo ""
echo "Fixed issues:"
if [ -f "$KIOSK_SERVICE" ]; then
    echo "  Kiosk service:"
    echo "    - Changed deprecated MemoryLimit= to MemoryMax="
    echo "    - Updated User/Group to: $TARGET_USER"
    echo "    - Updated all paths for: $TARGET_HOME"
    echo "    - Updated runtime directory for UID: $TARGET_UID"
fi
if [ -f "$NETWORK_SERVICE" ]; then
    echo "  Network wait service:"
    echo "    - Updated User to: $TARGET_USER (was hardcoded 'pi')"
fi
echo ""
echo "You can now restart the services:"
if [ -f "$KIOSK_SERVICE" ]; then
    echo "  sudo systemctl restart calendarbot-kiosk.service"
fi
if [ -f "$NETWORK_SERVICE" ]; then
    echo "  sudo systemctl restart calendarbot-network-wait.service"
fi
echo ""
echo "Check status:"
if [ -f "$KIOSK_SERVICE" ]; then
    echo "  sudo systemctl status calendarbot-kiosk.service"
fi
if [ -f "$NETWORK_SERVICE" ]; then
    echo "  sudo systemctl status calendarbot-network-wait.service"
fi