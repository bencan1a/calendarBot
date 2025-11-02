#!/bin/bash
# Final Auto-Login Setup (No X systemd service)
# This is the simple, reliable approach that works on Raspberry Pi OS

set -e

USER="${1:-bencan}"

echo "========================================="
echo "Auto-Login Kiosk Setup (Final)"
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

# Create autologin override
cat > /etc/systemd/system/getty@tty1.service.d/override.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $USER --noclear %I \$TERM
EOF

systemctl daemon-reload

echo "  ✓ Getty auto-login configured"

echo ""
echo "[2/5] Setting up .bash_profile to launch X..."

# Backup existing .bash_profile
if [ -f /home/$USER/.bash_profile ]; then
    cp /home/$USER/.bash_profile /home/$USER/.bash_profile.backup.$(date +%Y%m%d_%H%M%S)
fi

# Ensure .bash_profile has startx
if ! grep -q "startx" /home/$USER/.bash_profile 2>/dev/null; then
    cat >> /home/$USER/.bash_profile << 'EOF'

# Auto-start X session on tty1
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    exec startx
fi
EOF
    chown $USER:$USER /home/$USER/.bash_profile
    echo "  ✓ Added startx to .bash_profile"
else
    echo "  ✓ .bash_profile already has startx"
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
echo "[4/5] Disabling X systemd service (if enabled)..."

# Disable and stop the X systemd service
if systemctl is-enabled calendarbot-kiosk-x@$USER.service 2>/dev/null; then
    systemctl disable calendarbot-kiosk-x@$USER.service
    systemctl stop calendarbot-kiosk-x@$USER.service 2>/dev/null || true
    echo "  ✓ Disabled X systemd service"
else
    echo "  ✓ X systemd service not enabled"
fi

echo ""
echo "[5/5] Updating watchdog configuration..."

# Update monitor.yaml to use pkill
if [ -f /etc/calendarbot-monitor/monitor.yaml ]; then
    # Backup config
    cp /etc/calendarbot-monitor/monitor.yaml /etc/calendarbot-monitor/monitor.yaml.backup.$(date +%Y%m%d_%H%M%S)

    # Update x_restart to use pkill
    sed -i 's|restart_cmd: "sudo systemctl restart calendarbot-kiosk-x@{user}.service"|restart_cmd: "pkill -TERM Xorg"|' /etc/calendarbot-monitor/monitor.yaml

    echo "  ✓ Watchdog configured to kill X (auto-login restarts it)"
else
    echo "  ! Warning: /etc/calendarbot-monitor/monitor.yaml not found"
fi

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Configuration:"
echo "- Getty: Auto-login as $USER on tty1"
echo "- .bash_profile: Runs startx on tty1"
echo "- .xinitrc: Launches browser"
echo "- Watchdog: Kills X with 'pkill -TERM Xorg'"
echo "- Recovery: Getty auto-logins again → .bash_profile → startx → browser"
echo ""
echo "Next Steps:"
echo ""
echo "1. Reboot to activate:"
echo "   sudo reboot"
echo ""
echo "2. After reboot, verify X is running:"
echo "   ps aux | grep Xorg"
echo "   ps aux | grep chromium"
echo ""
echo "3. Check watchdog logs:"
echo "   sudo journalctl -u calendarbot-kiosk-watchdog@$USER.service -f"
echo ""
echo "4. Test X restart recovery:"
echo "   sudo pkill -TERM Xorg"
echo "   # Wait 10 seconds, X should restart automatically"
echo "   sleep 10"
echo "   ps aux | grep Xorg"
echo ""
echo "How it works:"
echo "- Boot → Getty auto-logs in as $USER on tty1"
echo "- .bash_profile detects tty1 and runs 'exec startx'"
echo "- startx launches X server and runs .xinitrc"
echo "- .xinitrc launches browser"
echo "- If X crashes or watchdog kills it:"
echo "  → Getty auto-logins again"
echo "  → .bash_profile runs startx again"
echo "  → System fully recovers"
echo ""
