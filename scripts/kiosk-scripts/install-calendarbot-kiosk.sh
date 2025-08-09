#!/bin/sh
# CalendarBot Kiosk Installation Script
# Complete automated installation and configuration for Raspberry Pi kiosk mode

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Installing CalendarBot Kiosk Mode..."

# Define source and target paths
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Verify we're in the right location
if [ ! -f "$PROJECT_ROOT/calendarbot/__init__.py" ]; then
    echo "ERROR: Cannot find CalendarBot project in expected location: $PROJECT_ROOT"
    exit 1
fi

echo "Project root: $PROJECT_ROOT"

# 1. Install required packages
echo "Installing system packages..."
apt-get update
apt-get install -y \
    chromium-browser \
    unclutter \
    xinput \
    xserver-xorg \
    openbox \
    lightdm \
    watchdog \
    python3-venv \
    python3-pip \
    x11-xserver-utils

# 2. Copy systemd service files
echo "Installing systemd services..."
cp "$SCRIPT_DIR/systemd/calendarbot-kiosk.service" /etc/systemd/system/
cp "$SCRIPT_DIR/systemd/calendarbot-kiosk-setup.service" /etc/systemd/system/
cp "$SCRIPT_DIR/systemd/calendarbot-network-wait.service" /etc/systemd/system/

# 3. Copy boot scripts
echo "Installing boot scripts..."
cp "$SCRIPT_DIR/boot/calendarbot-kiosk-prestart.sh" /usr/local/bin/
cp "$SCRIPT_DIR/boot/calendarbot-kiosk-system-setup.sh" /usr/local/bin/
cp "$SCRIPT_DIR/boot/calendarbot-wait-for-network.sh" /usr/local/bin/
cp "$SCRIPT_DIR/boot/calendarbot-kiosk-cleanup.sh" /usr/local/bin/

# 4. Make scripts executable
echo "Setting script permissions..."
chmod +x /usr/local/bin/calendarbot-*

# 5. Create log directory
echo "Creating log directory..."
mkdir -p /var/log/calendarbot
chown pi:pi /var/log/calendarbot

# 6. Set up X11 session
echo "Configuring X11 session..."
cp "$SCRIPT_DIR/x11/calendarbot-kiosk.desktop" /usr/share/xsessions/
cp "$SCRIPT_DIR/x11/.xsession" /home/pi/
chown pi:pi /home/pi/.xsession
chmod +x /home/pi/.xsession

# 7. Configure auto-login
echo "Configuring auto-login..."
cat > /etc/lightdm/lightdm.conf << EOF
[Seat:*]
autologin-user=pi
autologin-user-timeout=0
user-session=calendarbot-kiosk
autologin-session=calendarbot-kiosk
greeter-session=lightdm-greeter
EOF

# 8. Add boot configuration for Pi Zero 2W
echo "Configuring boot settings..."
BOOT_CONFIG="/boot/config.txt"

# Backup original config
cp "$BOOT_CONFIG" "${BOOT_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"

# Add CalendarBot kiosk configurations if not already present
if ! grep -q "# CalendarBot Kiosk Display Configuration" "$BOOT_CONFIG"; then
    cat >> "$BOOT_CONFIG" << EOF

# CalendarBot Kiosk Display Configuration

# GPU memory split for 512MB Pi Zero 2W
gpu_mem=64

# HDMI configuration for 480x800 display
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt=480 800 60 6 0 0 0

# Disable unnecessary hardware to save power/memory
dtparam=audio=off
dtoverlay=disable-bt

# Hardware watchdog
dtparam=watchdog=on

# Performance settings
arm_freq=1000
core_freq=500
over_voltage=2
force_turbo=1
EOF
    echo "Boot configuration updated"
fi

# 9. Create CalendarBot configuration directory if it doesn't exist
echo "Setting up CalendarBot configuration..."
mkdir -p /home/pi/.config/calendarbot
chown -R pi:pi /home/pi/.config/calendarbot

# 10. Set up Python virtual environment if it doesn't exist
if [ ! -d "/home/pi/calendarbot/venv" ]; then
    echo "Creating Python virtual environment..."
    cd /home/pi
    if [ ! -d "calendarbot" ]; then
        # Create symlink to project if not already there
        ln -sf "$PROJECT_ROOT" calendarbot
    fi
    cd calendarbot
    sudo -u pi python3 -m venv venv
    sudo -u pi ./venv/bin/pip install -e .
    echo "Virtual environment created and CalendarBot installed"
fi

# 11. Enable services
echo "Enabling systemd services..."
systemctl daemon-reload
systemctl enable calendarbot-kiosk-setup.service
systemctl enable calendarbot-network-wait.service
systemctl enable calendarbot-kiosk.service
systemctl enable lightdm.service
systemctl set-default graphical.target

# 12. Run initial system setup
echo "Running initial system setup..."
/usr/local/bin/calendarbot-kiosk-system-setup.sh

# 13. Create uninstall script
echo "Creating uninstall script..."
cat > /usr/local/bin/uninstall-calendarbot-kiosk.sh << 'EOF'
#!/bin/sh
# CalendarBot Kiosk Uninstall Script

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Uninstalling CalendarBot Kiosk Mode..."

# Stop and disable services
systemctl stop calendarbot-kiosk.service 2>/dev/null || true
systemctl disable calendarbot-kiosk.service 2>/dev/null || true
systemctl disable calendarbot-kiosk-setup.service 2>/dev/null || true
systemctl disable calendarbot-network-wait.service 2>/dev/null || true

# Remove service files
rm -f /etc/systemd/system/calendarbot-*.service

# Remove scripts
rm -f /usr/local/bin/calendarbot-*

# Remove X11 session
rm -f /usr/share/xsessions/calendarbot-kiosk.desktop
rm -f /home/pi/.xsession

# Restore lightdm default config
cat > /etc/lightdm/lightdm.conf << 'LIGHTDM_EOF'
[Seat:*]
#autologin-user=
#autologin-user-timeout=0
#user-session=default
#autologin-session=
LIGHTDM_EOF

# Restore boot config (manual step required)
echo "NOTE: Boot configuration in /boot/config.txt was modified."
echo "Backup available at /boot/config.txt.backup.*"
echo "Manual restoration may be required."

systemctl daemon-reload
systemctl set-default graphical.target

echo "CalendarBot Kiosk mode uninstalled."
echo "Reboot recommended to complete removal."
EOF

chmod +x /usr/local/bin/uninstall-calendarbot-kiosk.sh

# 14. Display installation summary
cat << EOF

===============================================
CalendarBot Kiosk Installation Completed!
===============================================

Installation Summary:
- System packages installed
- Systemd services configured and enabled
- Boot scripts installed in /usr/local/bin/
- X11 session configured for kiosk mode
- Auto-login configured for pi user
- Boot configuration updated for Pi Zero 2W
- CalendarBot installed in virtual environment

Services Enabled:
- calendarbot-kiosk-setup.service (system setup)
- calendarbot-network-wait.service (network connectivity)
- calendarbot-kiosk.service (main kiosk service)

Management Commands:
- Check status: systemctl status calendarbot-kiosk.service
- View logs: journalctl -u calendarbot-kiosk.service -f
- Stop kiosk: systemctl stop calendarbot-kiosk.service
- Start kiosk: systemctl start calendarbot-kiosk.service
- Uninstall: sudo /usr/local/bin/uninstall-calendarbot-kiosk.sh

Configuration:
- Kiosk config: /home/pi/.config/calendarbot/
- Logs: /var/log/calendarbot/
- Service files: /etc/systemd/system/calendarbot-*.service

IMPORTANT: Reboot the system to start kiosk mode
Command: sudo reboot

===============================================
EOF