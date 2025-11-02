#!/bin/bash
# Setup auto-login for kiosk mode
# This enables automatic X session restart when X crashes

set -e

USER="${1:-bencan}"

echo "========================================="
echo "Setting Up Auto-Login for Kiosk"
echo "========================================="
echo ""
echo "User: $USER"
echo ""

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run with sudo"
    exit 1
fi

echo "[1/4] Configuring getty auto-login..."

# Create getty override directory
mkdir -p /etc/systemd/system/getty@tty1.service.d/

# Create autologin override
cat > /etc/systemd/system/getty@tty1.service.d/override.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $USER --noclear %I \$TERM
EOF

echo "  ✓ Getty auto-login configured"

echo ""
echo "[2/4] Setting up .bash_profile to launch X..."

# Backup existing .bash_profile
if [ -f /home/$USER/.bash_profile ]; then
    cp /home/$USER/.bash_profile /home/$USER/.bash_profile.backup.$(date +%Y%m%d_%H%M%S)
fi

# Create or update .bash_profile
cat >> /home/$USER/.bash_profile << 'EOF'

# Auto-start X session on tty1
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    exec startx
fi
EOF

chown $USER:$USER /home/$USER/.bash_profile

echo "  ✓ .bash_profile configured"

echo ""
echo "[3/4] Ensuring .xinitrc is executable..."

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
echo "[4/4] Updating watchdog configuration for auto-login mode..."

# Update monitor.yaml to use simple X restart (kill X, auto-login restarts it)
if [ -f /etc/calendarbot-monitor/monitor.yaml ]; then
    # Backup config
    cp /etc/calendarbot-monitor/monitor.yaml /etc/calendarbot-monitor/monitor.yaml.backup.$(date +%Y%m%d_%H%M%S)

    # Update x_restart command to simply kill X (auto-login will restart it)
    sed -i 's|restart_cmd: "sudo systemctl restart calendarbot-kiosk-x@{user}.service"|restart_cmd: "pkill -TERM Xorg"|' /etc/calendarbot-monitor/monitor.yaml

    echo "  ✓ Watchdog configured to kill X (auto-login will restart it)"
else
    echo "  ! Warning: /etc/calendarbot-monitor/monitor.yaml not found"
fi

echo ""
echo "[5/5] Disabling X systemd service (if enabled)..."

# Disable the X systemd service since we're using auto-login instead
if systemctl is-enabled calendarbot-kiosk-x@$USER.service 2>/dev/null; then
    systemctl disable calendarbot-kiosk-x@$USER.service
    systemctl stop calendarbot-kiosk-x@$USER.service
    echo "  ✓ Disabled X systemd service"
else
    echo "  ✓ X systemd service not enabled"
fi

echo ""
echo "========================================="
echo "Auto-Login Setup Complete!"
echo "========================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. Reboot to activate auto-login:"
echo "   sudo reboot"
echo ""
echo "2. After reboot, verify X is running:"
echo "   ps aux | grep Xorg"
echo "   ps aux | grep chromium"
echo ""
echo "3. Check watchdog logs:"
echo "   sudo journalctl -u calendarbot-kiosk-watchdog@$USER.service -f"
echo ""
echo "How it works:"
echo "- getty@tty1 automatically logs in as $USER"
echo "- .bash_profile runs startx on tty1"
echo "- .xinitrc launches browser"
echo "- If X crashes, getty auto-logins again and restarts X"
echo "- Watchdog can restart X by killing it (pkill -TERM Xorg)"
echo ""
