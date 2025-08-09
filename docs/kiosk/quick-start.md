# CalendarBot Kiosk Mode - Quick Start Guide

**Get your Raspberry Pi Zero 2W calendar display running in under 10 minutes!**

## Prerequisites Checklist

### Hardware Requirements
- ✅ Raspberry Pi Zero 2W with 512MB RAM
- ✅ MicroSD card (16GB+ recommended)
- ✅ Display (tested with 480x800 portrait displays)
- ✅ Stable power supply (5V/2.5A recommended)
- ✅ Network connectivity (WiFi or Ethernet via USB adapter)

### Software Requirements
- ✅ Raspberry Pi OS Lite or Desktop (latest)
- ✅ SSH access configured (for headless setup)
- ✅ Internet connection for initial setup

## Single-Command Installation

### Step 1: Clone and Install
```bash
# Clone the CalendarBot repository
git clone https://github.com/your-org/calendarbot.git
cd calendarbot

# Run the automated installation script
sudo scripts/kiosk/install-calendarbot-kiosk.sh
```

### Step 2: Validate Installation
```bash
# Verify all components are properly installed
sudo scripts/kiosk/validate-kiosk-installation.sh
```

### Step 3: Configure Calendar Sources
```bash
# Configure your calendar URLs (interactive setup)
./venv/bin/python -m calendarbot --kiosk-setup
```

### Step 4: Reboot and Enjoy
```bash
sudo reboot
```

## What Just Happened?

The installation script automatically:

1. **📦 Installed System Packages**: Chromium, X11, systemd services
2. **⚙️ Configured Services**: Auto-start kiosk on boot with crash recovery
3. **🖥️ Set Up Display**: Optimized for 480x800 portrait displays
4. **🔧 Applied Pi Zero 2W Optimizations**: 80MB browser memory limit, GPU memory split
5. **🔐 Configured Security**: Hardened systemd service with resource limits
6. **📊 Enabled Monitoring**: Health checks and automatic restart on failures

## Verification Commands

### Check Kiosk Status
```bash
# Service status
systemctl status calendarbot-kiosk.service

# Real-time logs
journalctl -u calendarbot-kiosk.service -f

# System resource usage
htop
```

### Test Basic Functionality
```bash
# Manual kiosk start (for testing)
cd /home/pi/calendarbot
./venv/bin/python -m calendarbot --kiosk

# Check configuration
./venv/bin/python -m calendarbot --kiosk-status
```

## Common Post-Installation Tasks

### Add Calendar Sources
```bash
# Interactive calendar setup
./venv/bin/python -m calendarbot --kiosk-setup

# Or edit configuration directly
nano ~/.config/calendarbot/config.yaml
```

### Customize Display Settings
```bash
# Edit kiosk configuration
nano ~/.config/calendarbot/kiosk.yaml

# Available options:
# - Display resolution and orientation
# - Browser memory limits
# - Health check intervals
# - Restart behavior
```

### Monitor Performance
```bash
# Memory usage (should stay under 400MB total)
free -h

# Browser memory specifically
ps aux | grep chromium

# Service logs
journalctl -u calendarbot-kiosk.service --since "1 hour ago"
```

## Troubleshooting Quick Fixes

### ❌ Kiosk Won't Start
```bash
# Check service status
systemctl status calendarbot-kiosk.service

# Check for dependency issues
systemctl status calendarbot-kiosk-setup.service
systemctl status calendarbot-network-wait.service

# Manual diagnostic run
cd /home/pi/calendarbot
./venv/bin/python -m calendarbot --kiosk --debug
```

### ❌ Display Issues
```bash
# Check X11 session
echo $DISPLAY
xdpyinfo

# Verify display configuration
cat /boot/config.txt | grep -A 10 "CalendarBot"

# Test browser manually
chromium-browser --kiosk http://localhost:8080/whats-next-view
```

### ❌ Memory Issues
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -10

# Restart browser process
systemctl restart calendarbot-kiosk.service

# Reduce memory limits if needed
nano ~/.config/calendarbot/kiosk.yaml
```

### ❌ Network Connectivity
```bash
# Test internet connection
ping -c 3 google.com

# Check calendar URL accessibility
curl -I "your-calendar-url-here"

# Restart network service
sudo systemctl restart networking
```

## Management Commands

### Service Control
```bash
# Stop kiosk
sudo systemctl stop calendarbot-kiosk.service

# Start kiosk
sudo systemctl start calendarbot-kiosk.service

# Restart kiosk
sudo systemctl restart calendarbot-kiosk.service

# Disable auto-start
sudo systemctl disable calendarbot-kiosk.service
```

### System Maintenance
```bash
# Update CalendarBot
cd /home/pi/calendarbot
git pull
./venv/bin/pip install -e .
sudo systemctl restart calendarbot-kiosk.service

# Clean browser cache
sudo systemctl stop calendarbot-kiosk.service
rm -rf /home/pi/.cache/chromium
sudo systemctl start calendarbot-kiosk.service

# System cleanup
sudo apt autoremove
sudo journalctl --vacuum-time=7d
```

## Performance Optimization

### Memory Optimization (Pi Zero 2W)
- Browser memory limit: 80MB (configurable)
- Total system memory usage: <400MB
- Automatic cache clearing on restart
- GPU memory split: 64MB

### CPU Optimization
- CPU quota: 80% maximum
- Background process throttling
- Chromium flags optimized for ARM architecture

### Storage Optimization
- Logs rotated automatically
- Browser cache limited and cleaned regularly
- Temporary files cleaned on restart

## Next Steps

Once your kiosk is running:

1. **📅 Configure Calendar Sources**: Add your Google Calendar, Outlook, or ICS URLs
2. **🎨 Customize Layout**: Choose from available display layouts
3. **⏰ Set Refresh Intervals**: Configure how often calendar data updates
4. **🔧 Fine-tune Settings**: Adjust memory limits, timeouts, and display options
5. **📊 Monitor Performance**: Set up log monitoring and health checks

## Getting Help

- **📖 Full Documentation**: See [`docs/kiosk/`](.) for comprehensive guides
- **🐛 Issues**: Report problems at GitHub Issues
- **💬 Community**: Join our Discord/Slack for support
- **📧 Email**: Support contact information

## Uninstallation

If you need to remove kiosk mode:

```bash
# Complete removal
sudo /usr/local/bin/uninstall-calendarbot-kiosk.sh

# Reboot to complete removal
sudo reboot
```

---

**🎉 Congratulations!** Your CalendarBot kiosk should now be running. The display will automatically start on boot and recover from any crashes or network issues.

For advanced configuration and troubleshooting, see the [User Guide](user-guide.md) and [Deployment Guide](deployment-guide.md).