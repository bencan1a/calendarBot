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
sudo chown bencan:bencan /var/log/calendarbot-watchdog /var/local/calendarbot-watchdog
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
bencan ALL=NOPASSWD: /sbin/reboot
bencan ALL=NOPASSWD: /bin/systemctl restart calendarbot-kiosk@bencan.service
EOF
```

### 4. Enable and Start Watchdog
```bash
# Enable watchdog service for user 'bencan'
sudo systemctl enable calendarbot-kiosk-watchdog@bencan.service

# Start watchdog service
sudo systemctl start calendarbot-kiosk-watchdog@bencan.service

# Check status
sudo systemctl status calendarbot-kiosk-watchdog@bencan.service
```

## Configuration

### Monitor Configuration (`/etc/calendarbot-monitor/monitor.yaml`)
Key settings:
- `health_check.interval_s`: Health check frequency (default: 30s)
- `health_check.browser_heartbeat_check_interval_s`: How often to check browser heartbeat (default: 60s)
- `health_check.browser_heartbeat_timeout_s`: Consider heartbeat stale after this time (default: 120s)
- `thresholds.browser_heartbeat_fail_count`: Consecutive heartbeat failures before restart (default: 2)
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
sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service -f

# Local log files
sudo tail -f /var/log/calendarbot-watchdog/watchdog.log

# Browser launch logs
tail -f /home/bencan/kiosk/browser-launch.log
```

### Check Status
```bash
# Service status
systemctl status calendarbot-kiosk-watchdog@bencan.service

# Health endpoint
curl http://127.0.0.1:8080/api/health

# Process check
ps aux | grep calendarbot
```

## Troubleshooting

### Common Issues
1. **Watchdog not starting**: Check PyYAML is installed and config file exists
2. **Permission errors**: Verify log directories are writable by bencan user
3. **No recovery actions**: Check rate limits in state file `/var/local/calendarbot-watchdog/state.json`
4. **High resource usage**: Enable degraded mode or adjust thresholds
5. **Browser heartbeat not detected**:
   - Verify server has browser-heartbeat endpoint: `curl -X POST http://localhost:8080/api/browser-heartbeat`
   - Check JavaScript is sending heartbeats in browser console logs
   - Verify `display_probe` data in health endpoint: `curl http://localhost:8080/api/health | jq '.display_probe'`
6. **False heartbeat failures**:
   - Increase `browser_heartbeat_timeout_s` in monitor.yaml (currently 120s)
   - Check system clock is synchronized (NTP)

### Debug Mode
```bash
# Enable debug logging
sudo systemctl stop calendarbot-kiosk-watchdog@bencan.service
sudo CALENDARBOT_WATCHDOG_DEBUG=true systemctl start calendarbot-kiosk-watchdog@bencan.service
```

### Manual Testing
```bash
# Test health endpoint
curl -v http://127.0.0.1:8080/api/health

# Test render marker
curl -s http://127.0.0.1:8080/ | grep 'calendarbot-ready'

# Test browser heartbeat
curl -X POST http://127.0.0.1:8080/api/browser-heartbeat
curl -s http://127.0.0.1:8080/api/health | jq '.display_probe'

# Test port cleanup
./kiosk/scripts/cleanup-port.sh 8080

# Test browser launcher
./kiosk/scripts/launch-browser.sh
```

## Integration with Existing Kiosk Setup

The watchdog integrates with existing kiosk components:
- Uses health endpoint from [`calendarbot_lite/server.py`](../calendarbot_lite/server.py)
- Detects render marker from [`calendarbot_lite/whatsnext.html`](../calendarbot_lite/whatsnext.html)
- **Browser heartbeat monitoring**: JavaScript in the page sends heartbeats every 30 seconds to `/api/browser-heartbeat`
- Watchdog checks `display_probe` data in health endpoint to detect stuck/frozen browsers
- Works with existing [`kiosk/service/calendarbot-kiosk.service`](service/calendarbot-kiosk.service)
- Compatible with [`kiosk/scripts/.xinitrc`](scripts/.xinitrc) browser launch patterns

### Browser Heartbeat System

The browser heartbeat system provides robust detection of stuck or frozen browsers:

1. **JavaScript Heartbeat** ([`whatsnext.js`](../calendarbot_lite/whatsnext.js)): Sends POST request to `/api/browser-heartbeat` every 30 seconds
2. **Server Tracking** ([`routes/api_routes.py`](../calendarbot_lite/routes/api_routes.py)): Records heartbeat timestamps in health tracker
3. **Watchdog Verification**: Checks `display_probe.last_render_probe_iso` in `/api/health` response
4. **Stale Detection**: If last heartbeat > 2 minutes old, browser is considered stuck and will be restarted

This solves the problem of browsers showing blank pages while the server remains healthy.

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