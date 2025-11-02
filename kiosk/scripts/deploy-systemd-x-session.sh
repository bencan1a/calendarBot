#!/bin/bash
# Deploy CalendarBot Kiosk with Systemd X Session Management
# This script deploys the systemd service approach for managing the X session,
# which eliminates the need for auto-login and provides better process management.

set -e

USER="${1:-bencan}"

echo "========================================="
echo "CalendarBot Kiosk X Session Deployment"
echo "========================================="
echo ""
echo "Deploying for user: $USER"
echo ""

# Check if running as root or with sudo access
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run with sudo"
    exit 1
fi

echo "Step 1: Installing required packages..."
apt-get update -qq
apt-get install -y xdotool

echo ""
echo "Step 2: Deploying X session systemd service..."
# Install the X session service
cp kiosk/service/calendarbot-kiosk-x@.service /etc/systemd/system/
chmod 644 /etc/systemd/system/calendarbot-kiosk-x@.service

echo ""
echo "Step 3: Deploying updated watchdog script..."
# Backup existing script if it exists
if [ -f /usr/local/bin/calendarbot-watchdog ]; then
    cp /usr/local/bin/calendarbot-watchdog /usr/local/bin/calendarbot-watchdog.backup.$(date +%Y%m%d_%H%M%S)
fi

# Deploy updated watchdog
cp kiosk/scripts/calendarbot-watchdog /usr/local/bin/
chmod +x /usr/local/bin/calendarbot-watchdog

echo ""
echo "Step 4: Deploying updated configuration..."
# Ensure config directory exists
mkdir -p /etc/calendarbot-monitor

# Backup existing config if it exists
if [ -f /etc/calendarbot-monitor/monitor.yaml ]; then
    cp /etc/calendarbot-monitor/monitor.yaml /etc/calendarbot-monitor/monitor.yaml.backup.$(date +%Y%m%d_%H%M%S)
fi

# Deploy updated config
cp kiosk/config/monitor.yaml /etc/calendarbot-monitor/

echo ""
echo "Step 5: Configuring sudoers for watchdog..."
# Add sudoers rule if not already present
SUDOERS_FILE="/etc/sudoers.d/calendarbot-watchdog"
if [ ! -f "$SUDOERS_FILE" ]; then
    cat > "$SUDOERS_FILE" << EOF
# Allow calendarbot watchdog to restart services without password
$USER ALL=(ALL) NOPASSWD: /bin/systemctl restart calendarbot-kiosk@*.service
$USER ALL=(ALL) NOPASSWD: /bin/systemctl restart calendarbot-kiosk-x@*.service
$USER ALL=(ALL) NOPASSWD: /bin/systemctl status calendarbot-kiosk@*.service
$USER ALL=(ALL) NOPASSWD: /bin/systemctl status calendarbot-kiosk-x@*.service
$USER ALL=(ALL) NOPASSWD: /sbin/reboot
EOF
    chmod 440 "$SUDOERS_FILE"
    echo "Created sudoers configuration: $SUDOERS_FILE"
else
    echo "Sudoers configuration already exists: $SUDOERS_FILE"
fi

echo ""
echo "Step 6: Setting up state directory..."
mkdir -p /var/local/calendarbot-watchdog
chown $USER:$USER /var/local/calendarbot-watchdog

# Reset state file to clear any rate limits
cat > /var/local/calendarbot-watchdog/state.json << EOF
{
  "browser_restarts": [],
  "service_restarts": [],
  "reboots": [],
  "last_recovery_time": null,
  "consecutive_failures": 0,
  "degraded_mode": false,
  "browser_escalation_level": 0,
  "browser_escalation_time": null
}
EOF
chown $USER:$USER /var/local/calendarbot-watchdog/state.json

echo ""
echo "Step 7: Reloading systemd..."
systemctl daemon-reload

echo ""
echo "Step 8: Enabling X session service..."
systemctl enable calendarbot-kiosk-x@$USER.service

echo ""
echo "Step 9: Checking if services should be restarted..."
read -p "Restart services now? This will restart X session and watchdog. (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Stopping watchdog..."
    systemctl stop calendarbot-kiosk-watchdog@$USER.service || true

    echo "Restarting X session service..."
    systemctl restart calendarbot-kiosk-x@$USER.service

    echo "Starting watchdog..."
    systemctl start calendarbot-kiosk-watchdog@$USER.service

    echo ""
    echo "Services restarted!"
else
    echo ""
    echo "Skipping service restart. To restart manually:"
    echo "  sudo systemctl restart calendarbot-kiosk-x@$USER.service"
    echo "  sudo systemctl restart calendarbot-kiosk-watchdog@$USER.service"
fi

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Service Status:"
systemctl status calendarbot-kiosk-x@$USER.service --no-pager -l | head -20

echo ""
echo "========================================="
echo "Important Notes:"
echo "========================================="
echo ""
echo "1. X Session Management:"
echo "   - X is now managed by systemd service: calendarbot-kiosk-x@$USER.service"
echo "   - Auto-login is NO LONGER NEEDED"
echo "   - X starts automatically on boot via systemd"
echo ""
echo "2. Disabling Auto-Login:"
echo "   If you have auto-login configured, you can disable it:"
echo "   - Remove any .bash_profile startx commands"
echo "   - Disable getty auto-login in systemd"
echo ""
echo "3. Service Control:"
echo "   - Check X status: systemctl status calendarbot-kiosk-x@$USER.service"
echo "   - Restart X: sudo systemctl restart calendarbot-kiosk-x@$USER.service"
echo "   - View logs: journalctl -u calendarbot-kiosk-x@$USER.service -f"
echo ""
echo "4. Watchdog Monitoring:"
echo "   - View logs: sudo journalctl -u calendarbot-kiosk-watchdog@$USER.service -f"
echo "   - Check state: cat /var/local/calendarbot-watchdog/state.json"
echo ""
echo "5. Progressive Recovery:"
echo "   When browser heartbeat fails, watchdog will:"
echo "   - Level 1: Soft reload (F5 via xdotool)"
echo "   - Level 2: Browser restart"
echo "   - Level 3: X session restart (via systemctl restart)"
echo ""
echo "========================================="
echo "Next Steps:"
echo "========================================="
echo ""
echo "1. Verify browser heartbeat endpoint:"
echo "   curl -X POST http://127.0.0.1:8080/api/browser-heartbeat"
echo ""
echo "2. Check health endpoint:"
echo "   curl -s http://127.0.0.1:8080/api/health | jq '.display_probe'"
echo ""
echo "3. Test X restart (optional):"
echo "   sudo systemctl restart calendarbot-kiosk-x@$USER.service"
echo "   # Wait 10 seconds, then check:"
echo "   ps aux | grep Xorg"
echo "   ps aux | grep chromium"
echo ""
echo "4. Monitor watchdog for progressive recovery:"
echo "   sudo journalctl -u calendarbot-kiosk-watchdog@$USER.service -f"
echo ""
