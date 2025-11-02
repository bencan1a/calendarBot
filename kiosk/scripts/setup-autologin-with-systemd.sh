#!/bin/bash
# Setup auto-login + systemd X service
# Auto-login provides console user (for X permissions)
# Systemd service manages X lifecycle

set -e

USER="${1:-bencan}"

echo "========================================="
echo "Auto-Login + Systemd X Service Setup"
echo "========================================="
echo ""
echo "User: $USER"
echo ""

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run with sudo"
    exit 1
fi

echo "[1/5] Configuring getty auto-login..."

# Create getty override directory
mkdir -p /etc/systemd/system/getty@tty1.service.d/

# Create autologin override (provides console user for X)
cat > /etc/systemd/system/getty@tty1.service.d/override.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $USER --noclear %I \$TERM
EOF

echo "  ✓ Getty auto-login configured (provides console user)"

echo ""
echo "[2/5] Cleaning up .bash_profile (no startx needed)..."

# Remove any startx from .bash_profile
if [ -f /home/$USER/.bash_profile ]; then
    # Backup
    cp /home/$USER/.bash_profile /home/$USER/.bash_profile.backup.$(date +%Y%m%d_%H%M%S)

    # Remove startx lines
    sed -i '/startx/d' /home/$USER/.bash_profile
    sed -i '/DISPLAY/d' /home/$USER/.bash_profile

    echo "  ✓ Removed startx from .bash_profile"
else
    echo "  ✓ No .bash_profile found"
fi

echo ""
echo "[3/5] Ensuring .xinitrc is executable..."

if [ ! -f /home/$USER/.xinitrc ]; then
    echo "  Creating .xinitrc..."
    cat > /home/$USER/.xinitrc << 'XINITRC_EOF'
#!/bin/bash

# Wait for X to be ready
sleep 2

# Launch browser in kiosk mode
exec chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --no-first-run \
    --no-default-browser-check \
    --disable-session-crashed-bubble \
    --overscroll-history-navigation=0 \
    --disable-vulkan \
    --disable-gpu-compositing \
    http://$(hostname -I | awk '{print $1}'):8080
XINITRC_EOF
    chown $USER:$USER /home/$USER/.xinitrc
fi

chmod +x /home/$USER/.xinitrc
echo "  ✓ .xinitrc is executable"

echo ""
echo "[4/5] Deploying X systemd service..."

# Copy service file
cp kiosk/service/calendarbot-kiosk-x@.service /etc/systemd/system/
chmod 644 /etc/systemd/system/calendarbot-kiosk-x@.service

# Reload systemd
systemctl daemon-reload

# Enable service
systemctl enable calendarbot-kiosk-x@$USER.service

echo "  ✓ X systemd service deployed and enabled"

echo ""
echo "[5/5] Updating watchdog configuration..."

# Update monitor.yaml to use systemctl restart
if [ -f /etc/calendarbot-monitor/monitor.yaml ]; then
    # Backup config
    cp /etc/calendarbot-monitor/monitor.yaml /etc/calendarbot-monitor/monitor.yaml.backup.$(date +%Y%m%d_%H%M%S)

    # Ensure x_restart uses systemctl
    sed -i 's|restart_cmd: "pkill -TERM Xorg"|restart_cmd: "sudo systemctl restart calendarbot-kiosk-x@{user}.service"|' /etc/calendarbot-monitor/monitor.yaml

    echo "  ✓ Watchdog configured to use systemctl restart"
else
    echo "  ! Warning: /etc/calendarbot-monitor/monitor.yaml not found"
fi

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Configuration:"
echo "- Auto-login: Provides console user (satisfies X permissions)"
echo "- Systemd service: Manages X lifecycle (Restart=always)"
echo "- Watchdog: Uses 'systemctl restart' for clean restarts"
echo ""
echo "Next Steps:"
echo ""
echo "1. Reboot to activate:"
echo "   sudo reboot"
echo ""
echo "2. After reboot, verify services:"
echo "   systemctl status calendarbot-kiosk-x@$USER.service"
echo "   ps aux | grep Xorg"
echo "   ps aux | grep chromium"
echo ""
echo "3. Check watchdog logs:"
echo "   sudo journalctl -u calendarbot-kiosk-watchdog@$USER.service -f"
echo ""
echo "How it works:"
echo "- Getty auto-logs in as $USER (provides console session)"
echo "- Systemd X service starts as that console user"
echo "- X has permissions because user is logged into console"
echo "- Watchdog restarts X via 'systemctl restart' (clean!)"
echo "- If X crashes, systemd restarts it (Restart=always)"
echo ""
