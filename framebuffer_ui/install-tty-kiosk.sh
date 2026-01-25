#!/bin/bash
# CalendarBot Framebuffer Kiosk - TTY Auto-Login Installer
#
# Usage:
#   sudo ./install-tty-kiosk.sh USERNAME
#
# Example:
#   sudo ./install-tty-kiosk.sh bencan

set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# Check username argument
if [ -z "$1" ]; then
    echo "ERROR: Username required"
    echo "Usage: sudo $0 USERNAME"
    exit 1
fi

USERNAME="$1"
USER_HOME=$(eval echo ~"$USERNAME")

# Verify user exists
if ! id "$USERNAME" &>/dev/null; then
    echo "ERROR: User '$USERNAME' does not exist"
    exit 1
fi

echo "==================================================="
echo "CalendarBot Framebuffer Kiosk - TTY Auto-Login"
echo "==================================================="
echo "User: $USERNAME"
echo "Home: $USER_HOME"
echo ""

# 1. Make startup script executable
echo "[1/5] Making startup script executable..."
chmod +x "$USER_HOME/calendarbot/framebuffer_ui/start-framebuffer-kiosk.sh"
chown "$USERNAME:$USERNAME" "$USER_HOME/calendarbot/framebuffer_ui/start-framebuffer-kiosk.sh"

# 2. Configure auto-login on TTY1
echo "[2/5] Configuring auto-login on TTY1..."
mkdir -p /etc/systemd/system/getty@tty1.service.d/
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $USERNAME --noclear %I \$TERM
EOF

# 3. Add kiosk startup to login script
echo "[3/5] Adding kiosk startup to .bash_profile..."

# Determine which profile file to use
if [ -f "$USER_HOME/.bash_profile" ]; then
    PROFILE_FILE="$USER_HOME/.bash_profile"
elif [ -f "$USER_HOME/.profile" ]; then
    PROFILE_FILE="$USER_HOME/.profile"
else
    # Create .bash_profile if neither exists
    PROFILE_FILE="$USER_HOME/.bash_profile"
    touch "$PROFILE_FILE"
    chown "$USERNAME:$USERNAME" "$PROFILE_FILE"
fi

# Check if already configured
if grep -q "CALENDARBOT_KIOSK_RUNNING" "$PROFILE_FILE"; then
    echo "   Already configured in $PROFILE_FILE, skipping..."
else
    cat >> "$PROFILE_FILE" <<'EOF'

# CalendarBot Framebuffer Kiosk
# Only run on tty1 and only if not already running
if [ "$(tty)" = "/dev/tty1" ] && [ -z "$CALENDARBOT_KIOSK_RUNNING" ]; then
    export CALENDARBOT_KIOSK_RUNNING=1
    exec ~/calendarbot/framebuffer_ui/start-framebuffer-kiosk.sh
fi
EOF
    chown "$USERNAME:$USERNAME" "$PROFILE_FILE"
    echo "   Added to $PROFILE_FILE"
fi

# 4. Disable systemd service if enabled
echo "[4/5] Disabling systemd services (if any)..."
systemctl stop "calendarbot-display@$USERNAME.service" 2>/dev/null || true
systemctl disable "calendarbot-display@$USERNAME.service" 2>/dev/null || true

# Also disable X11 kiosk if running
systemctl stop "calendarbot-kiosk-watchdog@$USERNAME.service" 2>/dev/null || true
systemctl disable "calendarbot-kiosk-watchdog@$USERNAME.service" 2>/dev/null || true

# 5. Reload systemd
echo "[5/5] Reloading systemd..."
systemctl daemon-reload

echo ""
echo "==================================================="
echo "Installation complete!"
echo "==================================================="
echo ""
echo "Next steps:"
echo "  1. Reboot the system:"
echo "     sudo reboot"
echo ""
echo "  2. After reboot, the kiosk will auto-start on TTY1"
echo ""
echo "  3. To access shell, either:"
echo "     - SSH from another machine"
echo "     - Press Ctrl+Alt+F2 for TTY2"
echo ""
echo "See framebuffer_ui/INSTALL_TTY_KIOSK.md for details"
echo "==================================================="
