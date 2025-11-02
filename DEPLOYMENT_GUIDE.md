# CalendarBot Kiosk Deployment Guide - Systemd Approach

## Overview

This guide covers deploying CalendarBot Kiosk with **systemd-managed X session**, which provides:

- **No auto-login required** - X runs as a systemd service
- **Automatic recovery** - systemd's `Restart=always` handles crashes
- **Progressive escalation** - 3-level browser recovery (soft reload → browser restart → X restart)
- **Startup grace period** - HTTP 503 during boot treated as healthy
- **Robust monitoring** - watchdog with browser heartbeat detection

## What Changed from Previous Versions

### 1. X Session Management: Systemd Service (NEW)
- **OLD**: X started via .bash_profile on auto-login
- **NEW**: X runs as systemd service `calendarbot-kiosk-x@bencan.service`
- **Benefit**: No auto-login needed, proper process management

### 2. Progressive Browser Recovery (3-level escalation)
- **Level 0**: Soft reload (F5 via xdotool) - least disruptive
- **Level 1**: Browser restart (kill and relaunch) - moderate
- **Level 2**: X session restart (systemctl restart) - full recovery

### 3. X Restart Fix
- **OLD**: Only killed Xorg, left system at command prompt
- **NEW**: Properly restarts X via `systemctl restart calendarbot-kiosk-x@bencan.service`

### 4. Startup Grace Period
- **OLD**: Treated HTTP 503 during server startup as failures
- **NEW**: 5-minute grace period treats HTTP 503 as healthy during server startup

### 5. Escalation Logic Fix
- **OLD**: Escalated even when recovery actions succeeded
- **NEW**: Only escalates when action fails OR problem persists on next check

## Quick Start Deployment

### Prerequisites

- Raspberry Pi (tested on Pi Zero 2) with Raspberry Pi OS
- User account created (e.g., `bencan`)
- CalendarBot repository cloned to `/home/bencan/calendarBot`
- Basic X server and browser installed (Xorg, chromium)

### One-Command Deployment

```bash
cd /home/bencan/calendarBot
sudo ./kiosk/scripts/deploy-systemd-x-session.sh bencan
```

This automated script will:
1. Install xdotool (for soft reload)
2. Deploy X session systemd service
3. Deploy updated watchdog code
4. Deploy updated monitor.yaml config
5. Configure sudoers for passwordless service restarts
6. Reset rate limit state
7. Enable services and optionally restart them

**Follow the prompts** to restart services immediately or defer restart.

## Manual Deployment Steps

If you prefer step-by-step manual deployment:

### Step 1: Install Required Packages

```bash
sudo apt-get update
sudo apt-get install -y xdotool
```

### Step 2: Deploy X Session Systemd Service

```bash
# Copy service file
sudo cp kiosk/service/calendarbot-kiosk-x@.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/calendarbot-kiosk-x@.service

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable calendarbot-kiosk-x@bencan.service
```

### Step 3: Deploy Watchdog Script

```bash
# Backup existing script (if any)
if [ -f /usr/local/bin/calendarbot-watchdog ]; then
    sudo cp /usr/local/bin/calendarbot-watchdog \
           /usr/local/bin/calendarbot-watchdog.backup.$(date +%Y%m%d_%H%M%S)
fi

# Deploy updated watchdog
sudo cp kiosk/scripts/calendarbot-watchdog /usr/local/bin/
sudo chmod +x /usr/local/bin/calendarbot-watchdog
```

### Step 4: Deploy Configuration

```bash
# Create config directory
sudo mkdir -p /etc/calendarbot-monitor

# Backup existing config (if any)
if [ -f /etc/calendarbot-monitor/monitor.yaml ]; then
    sudo cp /etc/calendarbot-monitor/monitor.yaml \
           /etc/calendarbot-monitor/monitor.yaml.backup.$(date +%Y%m%d_%H%M%S)
fi

# Deploy updated config
sudo cp kiosk/config/monitor.yaml /etc/calendarbot-monitor/
```

### Step 5: Configure Sudoers

The watchdog needs passwordless sudo access to restart services:

```bash
sudo tee /etc/sudoers.d/calendarbot-watchdog << EOF
bencan ALL=(ALL) NOPASSWD: /bin/systemctl restart calendarbot-kiosk@*.service
bencan ALL=(ALL) NOPASSWD: /bin/systemctl restart calendarbot-kiosk-x@*.service
bencan ALL=(ALL) NOPASSWD: /bin/systemctl status calendarbot-kiosk@*.service
bencan ALL=(ALL) NOPASSWD: /bin/systemctl status calendarbot-kiosk-x@*.service
bencan ALL=(ALL) NOPASSWD: /sbin/reboot
EOF

sudo chmod 440 /etc/sudoers.d/calendarbot-watchdog
```

### Step 6: Set Up State Directory

```bash
# Create state directory
sudo mkdir -p /var/local/calendarbot-watchdog
sudo chown bencan:bencan /var/local/calendarbot-watchdog

# Initialize state file
cat > /tmp/watchdog-state.json << EOF
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

sudo mv /tmp/watchdog-state.json /var/local/calendarbot-watchdog/state.json
sudo chown bencan:bencan /var/local/calendarbot-watchdog/state.json
```

### Step 7: Start Services

```bash
# Start X session service
sudo systemctl start calendarbot-kiosk-x@bencan.service

# Start watchdog service
sudo systemctl start calendarbot-kiosk-watchdog@bencan.service

# Check status
systemctl status calendarbot-kiosk-x@bencan.service
systemctl status calendarbot-kiosk-watchdog@bencan.service
```

## Post-Deployment Configuration

### Disable Auto-Login (If Previously Configured)

**IMPORTANT**: With systemd managing X, auto-login is NO LONGER NEEDED.

#### Remove .bash_profile startx Command

If you have startx in `.bash_profile`, comment it out:

```bash
nano /home/bencan/.bash_profile

# Comment out or remove:
# if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
#     startx
# fi
```

#### Disable Getty Auto-Login

If you configured getty for auto-login:

```bash
# Check current getty configuration
systemctl cat getty@tty1.service | grep ExecStart

# If auto-login is configured, disable it:
sudo rm -f /etc/systemd/system/getty@tty1.service.d/override.conf
sudo systemctl daemon-reload
```

### Configure .xinitrc

Ensure `/home/bencan/.xinitrc` launches your browser in kiosk mode:

```bash
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
```

Make it executable:
```bash
chmod +x /home/bencan/.xinitrc
```

## Verification

### Check Service Status

```bash
# X session service
systemctl status calendarbot-kiosk-x@bencan.service

# Watchdog service
systemctl status calendarbot-kiosk-watchdog@bencan.service

# CalendarBot service
systemctl status calendarbot-kiosk@bencan.service
```

All services should show **active (running)** status.

### Check Browser Heartbeat Endpoint

```bash
# Test the browser-heartbeat endpoint
curl -X POST http://127.0.0.1:8080/api/browser-heartbeat

# Check health endpoint for display_probe
curl -s http://127.0.0.1:8080/api/health | jq '.display_probe'
```

Expected output should show `last_render_probe_iso` with a recent timestamp.

### View Logs

```bash
# Watch watchdog logs for progressive recovery
sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service -f

# Watch X session logs
journalctl -u calendarbot-kiosk-x@bencan.service -f

# Watch calendarbot service logs
journalctl -u calendarbot-kiosk@bencan.service -f
```

### Expected Log Events

After deployment, you should see logs like:

#### Startup Grace Period
```json
{"component": "healthcheck", "event": "health.endpoint.starting_up",
 "details": {"status_code": 503, "grace_period_remaining_s": 280}}
```

#### Browser Heartbeat Monitoring
```json
{"component": "healthcheck", "event": "browser.heartbeat.check",
 "details": {"age_s": 45, "timeout_s": 120, "ok": true}}
```

#### Progressive Recovery (when triggered)
```json
{"component": "recovery", "event": "browser.progressive_recovery.start",
 "details": {"current_level": 0}}
{"component": "recovery", "event": "browser.soft_reload.start", "action_taken": true}
{"component": "recovery", "event": "browser.soft_reload.complete"}
```

## Testing Recovery

### Test Soft Reload (Level 0)

Manually test xdotool soft reload:

```bash
DISPLAY=:0 xdotool search --class chromium windowactivate --sync key F5
```

Browser should refresh the page.

### Test Browser Restart (Level 1)

```bash
# Kill browser
pkill chromium

# Watchdog should detect heartbeat failure and restart browser within ~2 minutes
```

Watch logs: `sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service -f`

### Test X Session Restart (Level 2)

```bash
# Restart X session via systemd
sudo systemctl restart calendarbot-kiosk-x@bencan.service

# Wait 10 seconds
sleep 10

# Verify X and browser are running
ps aux | grep Xorg
ps aux | grep chromium
```

Both processes should be running.

## Expected Behavior

### During Boot
1. Server starts and begins loading calendar data (may return HTTP 503)
2. Watchdog starts and enters 5-minute grace period
3. HTTP 503 treated as healthy during grace period
4. X session service starts → startx → .xinitrc → browser
5. Browser loads and begins sending heartbeats

### During Normal Operation
1. Watchdog checks health endpoint every 30 seconds
2. Watchdog checks browser heartbeat every 60 seconds
3. Browser sends heartbeat POST every 30 seconds
4. All checks pass → no recovery actions

### When Browser Heartbeat Fails
1. **First failure**: Watchdog logs warning, increments failure counter
2. **Second consecutive failure**: Triggers progressive recovery at Level 0
3. **Level 0**: Soft reload via xdotool F5
4. **If heartbeat resumes**: Reset escalation level to 0, success!
5. **If heartbeat still stale after 2 min**: Escalate to Level 1 (browser restart)
6. **If still failing**: Escalate to Level 2 (X session restart via systemctl)

### Escalation Logic
- Action **succeeds**: Stay at current level, wait for next check
- Heartbeat **resumes**: Reset escalation to level 0
- Action **fails to execute**: Immediately escalate to next level
- Action **succeeded but problem persists** (within 2 min): Escalate to next level

## Troubleshooting

### X Session Won't Start

```bash
# Check service status and logs
systemctl status calendarbot-kiosk-x@bencan.service
journalctl -u calendarbot-kiosk-x@bencan.service -n 50

# Check if .xinitrc exists and is executable
ls -la /home/bencan/.xinitrc

# Test startx manually as the user
sudo -u bencan startx
```

### Browser Not Launching

```bash
# Check .xinitrc for errors
cat /home/bencan/.xinitrc

# Check X session logs
journalctl -u calendarbot-kiosk-x@bencan.service -n 50

# Verify browser is installed
which chromium-browser chromium
```

### Watchdog Can't Restart Services

```bash
# Check sudoers configuration
sudo cat /etc/sudoers.d/calendarbot-watchdog

# Test restart manually as the user
sudo -u bencan sudo systemctl restart calendarbot-kiosk-x@bencan.service
```

### Heartbeat Not Working

```bash
# Check if endpoint exists
curl -X POST http://127.0.0.1:8080/api/browser-heartbeat

# Check if JavaScript is sending heartbeats (browser console)
# Open browser console (F12) and look for heartbeat logs

# Restart calendarbot service if endpoint missing
sudo systemctl restart calendarbot-kiosk@bencan.service
```

### Soft Reload Not Working

```bash
# Test xdotool manually
DISPLAY=:0 xdotool search --class chromium windowactivate --sync key F5

# Check if xdotool is installed
which xdotool

# Install if missing
sudo apt-get install -y xdotool
```

### Rate Limiting Issues

If watchdog is rate-limited and not taking recovery actions:

```bash
# Check current state
cat /var/local/calendarbot-watchdog/state.json | jq

# Clear rate limits (stop watchdog first!)
sudo systemctl stop calendarbot-kiosk-watchdog@bencan.service

# Reset state
sudo bash -c 'cat > /var/local/calendarbot-watchdog/state.json << EOF
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
EOF'

sudo chown bencan:bencan /var/local/calendarbot-watchdog/state.json
sudo systemctl start calendarbot-kiosk-watchdog@bencan.service
```

## Service Management

### Start/Stop Services

```bash
# Stop all services
sudo systemctl stop calendarbot-kiosk-watchdog@bencan.service
sudo systemctl stop calendarbot-kiosk-x@bencan.service
sudo systemctl stop calendarbot-kiosk@bencan.service

# Start all services
sudo systemctl start calendarbot-kiosk@bencan.service
sudo systemctl start calendarbot-kiosk-x@bencan.service
sudo systemctl start calendarbot-kiosk-watchdog@bencan.service

# Restart individual services
sudo systemctl restart calendarbot-kiosk-x@bencan.service
sudo systemctl restart calendarbot-kiosk-watchdog@bencan.service
```

### Enable/Disable Auto-Start on Boot

```bash
# Enable (start on boot)
sudo systemctl enable calendarbot-kiosk@bencan.service
sudo systemctl enable calendarbot-kiosk-x@bencan.service
sudo systemctl enable calendarbot-kiosk-watchdog@bencan.service

# Disable (don't start on boot)
sudo systemctl disable calendarbot-kiosk@bencan.service
sudo systemctl disable calendarbot-kiosk-x@bencan.service
sudo systemctl disable calendarbot-kiosk-watchdog@bencan.service
```

### View Real-Time Logs

```bash
# All services in one terminal (requires multitail)
sudo multitail \
  -l 'journalctl -u calendarbot-kiosk@bencan.service -f' \
  -l 'journalctl -u calendarbot-kiosk-x@bencan.service -f' \
  -l 'journalctl -u calendarbot-kiosk-watchdog@bencan.service -f'

# Or view individually in separate terminals
sudo journalctl -u calendarbot-kiosk@bencan.service -f
sudo journalctl -u calendarbot-kiosk-x@bencan.service -f
sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service -f
```

## Migration from Old Approach

If you're upgrading from the .bash_profile auto-login approach:

1. **Backup current setup**:
   ```bash
   sudo cp /usr/local/bin/calendarbot-watchdog /usr/local/bin/calendarbot-watchdog.old
   sudo cp /etc/calendarbot-monitor/monitor.yaml /etc/calendarbot-monitor/monitor.yaml.old
   ```

2. **Run deployment script**:
   ```bash
   sudo ./kiosk/scripts/deploy-systemd-x-session.sh bencan
   ```

3. **Disable auto-login** (see "Post-Deployment Configuration" above)

4. **Reboot** for clean state:
   ```bash
   sudo reboot
   ```

5. **Verify** services started correctly:
   ```bash
   systemctl status calendarbot-kiosk-x@bencan.service
   systemctl status calendarbot-kiosk-watchdog@bencan.service
   ```

## Architecture Diagram

```
Boot
 └─> systemd
      ├─> calendarbot-kiosk@bencan.service
      │    └─> python -m calendarbot_lite (port 8080)
      │
      ├─> calendarbot-kiosk-x@bencan.service
      │    └─> startx
      │         └─> .xinitrc
      │              └─> chromium --kiosk http://localhost:8080
      │                   └─> JavaScript sends heartbeat POST every 30s
      │
      └─> calendarbot-kiosk-watchdog@bencan.service
           └─> Monitor loop:
                ├─> Check /api/health every 30s
                ├─> Check browser heartbeat every 60s
                └─> Progressive recovery on failure:
                     ├─> Level 0: Soft reload (xdotool F5)
                     ├─> Level 1: Browser restart (pkill + relaunch)
                     └─> Level 2: X restart (systemctl restart)
```

## Summary

The systemd approach provides a **robust, production-ready** kiosk deployment:

✅ **No auto-login required** - X runs as systemd service
✅ **Automatic recovery** - Progressive 3-level escalation
✅ **Startup grace period** - No false failures during boot
✅ **Proper process management** - systemd handles lifecycle
✅ **Clean logging** - All logs in systemd journal
✅ **Easy maintenance** - Standard systemctl commands

For issues or questions, check:
- **X_RESTART_FIX.md** - Detailed technical documentation
- **kiosk/WATCHDOG_INSTALLATION.md** - Installation reference
- Service logs via `journalctl`
