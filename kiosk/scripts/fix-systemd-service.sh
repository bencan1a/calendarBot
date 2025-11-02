#!/bin/bash
# Fix systemd X service configuration and disable auto-login

set -e

USER="${1:-bencan}"

echo "========================================="
echo "Fixing X Session Service Configuration"
echo "========================================="
echo ""

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run with sudo"
    exit 1
fi

echo "[1/4] Updating X session service file..."
# Copy fixed service file
cp kiosk/service/calendarbot-kiosk-x@.service /etc/systemd/system/
chmod 644 /etc/systemd/system/calendarbot-kiosk-x@.service

# Reload systemd
systemctl daemon-reload

echo "  ✓ Service file updated"

echo ""
echo "[2/4] Checking auto-login configuration..."

# Check if .bash_profile has startx
if sudo -u $USER grep -q "startx" /home/$USER/.bash_profile 2>/dev/null; then
    echo "  Found startx in .bash_profile - commenting it out..."
    sudo -u $USER sed -i 's/^\([^#]*startx\)/# DISABLED FOR SYSTEMD: \1/' /home/$USER/.bash_profile
    echo "  ✓ Commented out startx in .bash_profile"
else
    echo "  ✓ No startx found in .bash_profile"
fi

echo ""
echo "[3/4] Checking getty auto-login..."

# Check if getty auto-login is configured
if systemctl cat getty@tty1.service 2>/dev/null | grep -q "autologin"; then
    echo "  Found getty auto-login configuration..."

    # Check for override file
    if [ -f /etc/systemd/system/getty@tty1.service.d/override.conf ]; then
        echo "  Removing getty override file..."
        rm -f /etc/systemd/system/getty@tty1.service.d/override.conf
        rmdir /etc/systemd/system/getty@tty1.service.d 2>/dev/null || true
        systemctl daemon-reload
        echo "  ✓ Removed getty auto-login"
    fi

    # Check for autologin in getty@tty1.service itself
    if systemctl cat getty@tty1.service | grep -q "ExecStart.*autologin"; then
        echo "  WARNING: getty@tty1.service has auto-login in main config"
        echo "  You may need to manually edit /lib/systemd/system/getty@.service"
    fi
else
    echo "  ✓ No getty auto-login configured"
fi

echo ""
echo "[4/4] Restarting X session service..."
systemctl restart calendarbot-kiosk-x@$USER.service

echo ""
echo "========================================="
echo "Fix Complete!"
echo "========================================="
echo ""
echo "Checking service status..."
systemctl status calendarbot-kiosk-x@$USER.service --no-pager -l | head -20

echo ""
echo "Recent logs:"
journalctl -u calendarbot-kiosk-x@$USER.service -n 10 --no-pager

echo ""
echo "========================================="
echo "Next Steps:"
echo "========================================="
echo ""
echo "1. Verify X service is running without errors:"
echo "   systemctl status calendarbot-kiosk-x@$USER.service"
echo ""
echo "2. If auto-login is still happening, check getty config:"
echo "   systemctl cat getty@tty1.service | grep -i autologin"
echo ""
echo "3. To completely disable auto-login, you may need to:"
echo "   sudo systemctl disable getty@tty1.service"
echo "   sudo systemctl mask getty@tty1.service"
echo ""
echo "4. Check if X and browser are running:"
echo "   ps aux | grep Xorg"
echo "   ps aux | grep chromium"
echo ""
