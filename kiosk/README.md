# CalendarBot Kiosk Mode

## Overview

CalendarBot Kiosk Mode provides a robust, self-healing calendar display system for Raspberry Pi devices. The system uses **auto-login with .bash_profile** with progressive recovery monitoring to ensure 24/7 uptime.

## 🚀 Automated Installation (Recommended)

The **automated installer** (`install-kiosk.sh`) deploys and configures all kiosk components with idempotent, one-command installation:

```bash
# 1. Configure
cd ~/calendarbot/kiosk
cp install-config.example.yaml install-config.yaml
nano install-config.yaml  # Set your username and ICS URL

# 2. Preview changes
sudo ./install-kiosk.sh --config install-config.yaml --dry-run

# 3. Install
sudo ./install-kiosk.sh --config install-config.yaml

# 4. Reboot for kiosk mode
sudo reboot
```

**Features:**
- ✅ Idempotent (safe to re-run)
- ✅ Automatic backups
- ✅ Modular sections (base, kiosk, alexa, monitoring)
- ✅ Dry-run mode
- ✅ Update mode for existing installations

**See:** [**Automated Installation Guide**](docs/AUTOMATED_INSTALLATION.md) for complete usage instructions.

## Documentation

**📘 For complete deployment instructions**, see the comprehensive guides in [docs/](docs/):

### Installation Guides

**Automated Installation (Recommended):**
- **[Automated Installation Guide](docs/AUTOMATED_INSTALLATION.md)** - Complete automation guide
- **[Manual Steps Guide](docs/MANUAL_STEPS.md)** - DNS, AWS Lambda, Alexa skill setup

**Manual Installation (Step-by-Step):**
- **[Installation Overview](docs/INSTALLATION_OVERVIEW.md)** - Architecture & workflow
- **[Section 1: Base Installation](docs/1_BASE_INSTALL.md)** - CalendarBot server setup
- **[Section 2: Kiosk & Watchdog](docs/2_KIOSK_WATCHDOG.md)** - Automatic display & recovery
- **[Section 3: Alexa Integration](docs/3_ALEXA_INTEGRATION.md)** - HTTPS reverse proxy
- **[Section 4: Log Management](docs/4_LOG_MANAGEMENT.md)** - Rotation, aggregation, monitoring

### Quick Reference

- **[Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md)** - Verification checklists
- **[File Inventory](docs/FILE_INVENTORY.md)** - Complete file reference

## Quick Start

**For first-time setup**, use the [**Automated Installation**](docs/AUTOMATED_INSTALLATION.md):

```bash
cd ~/calendarbot/kiosk
sudo ./install-kiosk.sh --config install-config.yaml --dry-run  # Preview
sudo ./install-kiosk.sh --config install-config.yaml            # Install
sudo reboot                                                       # Start kiosk
```

**For manual step-by-step setup**, see [Section 2: Kiosk & Watchdog](docs/2_KIOSK_WATCHDOG.md).

## Architecture

```
Boot → systemd
  ├─> calendarbot-lite@bencan.service (CalendarBot server)
  ├─> Auto-login to tty1 → .bash_profile → startx → .xinitrc → Chromium
  └─> calendarbot-kiosk-watchdog@bencan.service (monitoring)
```

### Key Features

✅ **Auto-Login X Session Management** - Console auto-login triggers `.bash_profile` which starts X via `.xinitrc`
✅ **Progressive Recovery** - 3-level escalation (soft reload → browser restart → X restart)
✅ **Browser Heartbeat Monitoring** - Detects stuck/frozen browsers via JavaScript heartbeats
✅ **Startup Grace Period** - No false failures during server boot
✅ **Watchdog Monitoring** - Health checks with automatic recovery actions
✅ **Resource Monitoring** - Degraded mode under system load

## Components

### Services

- **calendarbot-lite@.service** - CalendarBot_Lite server (port 8080)
- **calendarbot-kiosk-watchdog@.service** - Health monitoring and recovery
- **Auto-login + .bash_profile** - Triggers X session startup on console login

### Scripts

- **calendarbot-watchdog** - Watchdog monitoring daemon
- **deploy-progressive-recovery.sh.OLD_BACKUP** - Deprecated (old .bash_profile approach)

### Configuration

- **config/monitor.yaml** - Watchdog configuration (thresholds, intervals, commands)
- **service/*.service** - systemd unit files

## Progressive Recovery

When browser heartbeat fails, the watchdog uses 3-level escalation:

### Level 0: Soft Reload
- **Action**: Send F5 key to browser via xdotool
- **Duration**: ~15 seconds
- **Use Case**: Page rendering issues, JavaScript freezes

### Level 1: Browser Restart
- **Action**: Kill and relaunch browser
- **Duration**: ~30 seconds
- **Use Case**: Browser memory leaks, crashed tabs

### Level 2: X Session Restart
- **Action**: `systemctl restart auto-login + .bash_profile + X session`
- **Duration**: ~60 seconds
- **Use Case**: X server issues, display problems

### Escalation Logic

- After **2 consecutive** heartbeat failures → trigger recovery
- Action **succeeds** → stay at current level, wait for next check
- Heartbeat **fails again within 2 minutes** → escalate to next level
- Action **fails to execute** → immediately escalate
- Heartbeat **resumes** → reset escalation to level 0

## Service Management

### Status Checks

```bash
# Check all services
systemctl status calendarbot-lite@bencan.service
systemctl status auto-login + .bash_profile + X session
systemctl status calendarbot-kiosk-watchdog@bencan.service

# View logs
journalctl -u calendarbot-kiosk-watchdog@bencan.service -f
```

### Manual Control

```bash
# Restart X session
sudo systemctl restart auto-login + .bash_profile + X session

# Restart watchdog
sudo systemctl restart calendarbot-kiosk-watchdog@bencan.service

# Stop all services
sudo systemctl stop calendarbot-kiosk-watchdog@bencan.service
sudo systemctl stop auto-login + .bash_profile + X session
sudo systemctl stop calendarbot-lite@bencan.service
```

### Enable/Disable Auto-Start

```bash
# Enable (start on boot)
sudo systemctl enable calendarbot-lite@bencan.service
sudo systemctl enable auto-login + .bash_profile + X session
sudo systemctl enable calendarbot-kiosk-watchdog@bencan.service

# Disable
sudo systemctl disable calendarbot-kiosk-watchdog@bencan.service
```

## Browser Heartbeat System

The browser heartbeat system provides robust detection of stuck/frozen browsers:

1. **JavaScript** (in page): Sends POST to `/api/browser-heartbeat` every 30s
2. **Server**: Records timestamp in health tracker
3. **Watchdog**: Checks `display_probe.last_render_probe_iso` in `/api/health`
4. **Detection**: If last heartbeat > 2 minutes old → browser is stuck

## Configuration

### Watchdog Configuration

Edit `/etc/calendarbot-monitor/monitor.yaml`:

```yaml
health_check:
  interval_s: 30                          # Health check frequency
  browser_heartbeat_check_interval_s: 60  # Heartbeat check frequency
  browser_heartbeat_timeout_s: 120        # Stale threshold
  startup_grace_period_s: 300             # Boot grace period

thresholds:
  browser_heartbeat_fail_count: 2         # Failures before recovery
  max_browser_restarts_per_hour: 4        # Rate limiting

recovery:
  browser_soft_reload:
    reload_cmd: "DISPLAY=:0 xdotool search --class chromium windowactivate --sync key F5"
    reload_delay_s: 15

  x_restart:
    restart_cmd: "sudo systemctl restart calendarbot-kiosk-x@{user}.service"
    verification_delay_s: 60
```

### Sudoers Configuration

The watchdog requires sudo privileges for service management.

Location: `/etc/sudoers.d/calendarbot-watchdog`

```
bencan ALL=NOPASSWD: /bin/systemctl restart calendarbot-lite@*.service
bencan ALL=NOPASSWD: /bin/systemctl restart [removed - not used]
bencan ALL=NOPASSWD: /bin/systemctl status calendarbot-lite@*.service
bencan ALL=NOPASSWD: /bin/systemctl status [removed - not used]
bencan ALL=NOPASSWD: /sbin/reboot
```

## Testing

### Test Soft Reload

```bash
DISPLAY=:0 xdotool search --class chromium windowactivate --sync key F5
```

### Test Browser Restart

```bash
# Kill browser
pkill chromium

# Watch logs - should see progressive recovery
sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service -f
```

### Test X Session Restart

```bash
# Restart X
sudo systemctl restart auto-login + .bash_profile + X session

# Verify processes after 10 seconds
sleep 10
ps aux | grep Xorg
ps aux | grep chromium
```

### Check Browser Heartbeat

```bash
# Test endpoint
curl -X POST http://127.0.0.1:8080/api/browser-heartbeat

# Check display_probe data
curl -s http://127.0.0.1:8080/api/health | jq '.display_probe'
```

## Troubleshooting

### X Session Won't Start

```bash
# Check service status
systemctl status auto-login + .bash_profile + X session

# View logs
journalctl -u auto-login + .bash_profile + X session -n 50

# Check .xinitrc
ls -la /home/bencan/.xinitrc
cat /home/bencan/.xinitrc
```

### Watchdog Not Taking Recovery Actions

```bash
# Check rate limits
cat /var/local/calendarbot-watchdog/state.json | jq

# Reset state (stop watchdog first!)
sudo systemctl stop calendarbot-kiosk-watchdog@bencan.service
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

### Heartbeat Not Working

```bash
# Check if endpoint exists
curl -X POST http://127.0.0.1:8080/api/browser-heartbeat

# Restart server if endpoint missing
sudo systemctl restart calendarbot-lite@bencan.service
```

## Migration from Old Approach

If upgrading from the .bash_profile auto-login approach:

2. Disable auto-login (remove startx from .bash_profile)
3. Reboot system
4. Verify services started correctly

See [Section 2: Kiosk & Watchdog](docs/2_KIOSK_WATCHDOG.md) for detailed setup instructions.

## Additional Documentation

- **[Installation Overview](docs/INSTALLATION_OVERVIEW.md)** - Complete deployment guide (start here)
- **[Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md)** - Verification checklists
- **[File Inventory](docs/FILE_INVENTORY.md)** - Complete file reference
- **[Watchdog Installation](WATCHDOG_INSTALLATION.md)** - Legacy watchdog reference
- **[AGENTS.md](../AGENTS.md)** - Development guide
- **[docs/ALEXA_DEPLOYMENT_GUIDE.md](../docs/ALEXA_DEPLOYMENT_GUIDE.md)** - Alexa skill setup

## Performance

Resource usage on Raspberry Pi Zero 2:

- **Memory**: <30MB RSS (watchdog)
- **CPU**: <2% average (watchdog)
- **Disk**: <10MB for logs with rotation
- **Network**: Localhost HTTP only

## Security

- Minimal sudo privileges (service restart and reboot only)
- Localhost-only health monitoring
- Safe process termination with user/privilege checks
- Rate limiting prevents recovery loops
- No auto-login required (improved security posture)

## Support

For issues or questions:
- Check service logs: `journalctl -u <service-name> -f`
- Review troubleshooting sections in documentation
- Examine watchdog state: `cat /var/local/calendarbot-watchdog/state.json`
