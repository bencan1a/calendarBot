# CalendarBot Kiosk Watchdog Installation Guide

## Overview
Automatic recovery system for CalendarBot_Lite on Raspberry Pi Zero 2. Provides 4-level escalation recovery: browser restart → X restart → systemd service restart → reboot.

## Prerequisites
- Raspberry Pi Zero 2 with Debian/Raspbian
- CalendarBot_Lite installed and working
- systemd for service management
- Python 3.7+ with PyYAML package

## Installation Steps

### 1. Install System Components
```bash
# Copy watchdog script
sudo cp kiosk/scripts/calendarbot-watchdog /usr/local/bin/
sudo chmod +x /usr/local/bin/calendarbot-watchdog

# Copy systemd service
sudo cp kiosk/service/calendarbot-kiosk-watchdog@.service /etc/systemd/system/
sudo systemctl daemon-reload

# Copy configuration
sudo mkdir -p /etc/calendarbot-monitor
sudo cp kiosk/config/monitor.yaml /etc/calendarbot-monitor/

# Setup log rotation
sudo cp kiosk/config/logrotate-calendarbot-watchdog /etc/logrotate.d/calendarbot-watchdog

# Create log directories
sudo mkdir -p /var/log/calendarbot-watchdog
sudo mkdir -p /var/local/calendarbot-watchdog
sudo chown pi:pi /var/log/calendarbot-watchdog /var/local/calendarbot-watchdog
```

### 2. Install Python Dependencies
```bash
# Install PyYAML for configuration loading
pip install PyYAML
```

### 3. Configure Sudo Privileges (if needed for reboot)
```bash
# Create sudoers file for reboot privileges
sudo tee /etc/sudoers.d/calendarbot-watchdog << EOF
# CalendarBot watchdog privileges
pi ALL=NOPASSWD: /sbin/reboot
pi ALL=NOPASSWD: /bin/systemctl restart calendarbot-kiosk@pi.service
EOF
```

### 4. Enable and Start Watchdog
```bash
# Enable watchdog service for user 'pi'
sudo systemctl enable calendarbot-kiosk-watchdog@pi.service

# Start watchdog service
sudo systemctl start calendarbot-kiosk-watchdog@pi.service

# Check status
sudo systemctl status calendarbot-kiosk-watchdog@pi.service
```

## Configuration

### Monitor Configuration (`/etc/calendarbot-monitor/monitor.yaml`)
Key settings:
- `health_check.interval_s`: Health check frequency (default: 30s)
- `thresholds.max_browser_restarts_per_hour`: Rate limiting (default: 4)
- `resource_limits.min_free_mem_kb`: Degradation threshold (default: 60MB)

### Environment Variables
- `CALENDARBOT_WATCHDOG_DEBUG=true`: Enable debug logging
- `CALENDARBOT_WATCHDOG_DISABLED=true`: Disable all recovery actions
- `CALENDARBOT_WATCHDOG_LOG_LEVEL=DEBUG`: Override log level

## Monitoring

### View Logs
```bash
# Watchdog service logs
sudo journalctl -u calendarbot-kiosk-watchdog@pi.service -f

# Local log files
sudo tail -f /var/log/calendarbot-watchdog/watchdog.log

# Browser launch logs
tail -f /home/pi/kiosk/browser-launch.log
```

### Check Status
```bash
# Service status
systemctl status calendarbot-kiosk-watchdog@pi.service

# Health endpoint
curl http://127.0.0.1:8080/api/health

# Process check
ps aux | grep calendarbot
```

## Troubleshooting

### Common Issues
1. **Watchdog not starting**: Check PyYAML is installed and config file exists
2. **Permission errors**: Verify log directories are writable by pi user
3. **No recovery actions**: Check rate limits in state file `/var/local/calendarbot-watchdog/state.json`
4. **High resource usage**: Enable degraded mode or adjust thresholds

### Debug Mode
```bash
# Enable debug logging
sudo systemctl stop calendarbot-kiosk-watchdog@pi.service
sudo CALENDARBOT_WATCHDOG_DEBUG=true systemctl start calendarbot-kiosk-watchdog@pi.service
```

### Manual Testing
```bash
# Test health endpoint
curl -v http://127.0.0.1:8080/api/health

# Test render marker
curl -s http://127.0.0.1:8080/ | grep 'calendarbot-ready'

# Test port cleanup
./kiosk/scripts/cleanup-port.sh 8080

# Test browser launcher
./kiosk/scripts/launch-browser.sh
```

## Integration with Existing Kiosk Setup

The watchdog integrates with existing kiosk components:
- Uses health endpoint from [`calendarbot_lite/server.py`](../calendarbot_lite/server.py)
- Detects render marker from [`calendarbot_lite/whatsnext.html`](../calendarbot_lite/whatsnext.html)
- Works with existing [`kiosk/service/calendarbot-kiosk.service`](service/calendarbot-kiosk.service)
- Compatible with [`kiosk/scripts/.xinitrc`](scripts/.xinitrc) browser launch patterns

## Performance

Resource usage on Pi Zero 2:
- **Memory**: <30MB RSS
- **CPU**: <2% average
- **Disk**: <10MB for logs with rotation
- **Network**: Localhost HTTP only (no external traffic)

## Security

- Minimal sudo privileges (reboot and service restart only)
- Localhost-only health monitoring
- Safe process termination with user/privilege checks
- Rate limiting prevents recovery loops