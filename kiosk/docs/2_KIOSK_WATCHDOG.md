# Section 2: Kiosk Mode & Watchdog

Configure automatic browser display with X session management and progressive recovery monitoring.

**Estimated Time**: 45-60 minutes
**Prerequisites**: Section 1 completed (CalendarBot_Lite service running)

---

## What You'll Install

By the end of this section, you'll have:

- ✅ X server with minimal window manager
- ✅ Chromium browser in kiosk mode
- ✅ Automatic X session startup (via systemd or .bash_profile)
- ✅ Watchdog daemon with progressive recovery
- ✅ Browser heartbeat monitoring
- ✅ 3-level browser recovery (soft reload → restart → X restart)
- ✅ 4-level system escalation (browser → X → service → reboot)

**Services Added**: 2-3
- `calendarbot-kiosk-watchdog@bencan.service`
- `[removed - not used]` (optional, recommended)

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Section 1 completed (CalendarBot service running)
- [ ] CalendarBot accessible at `http://localhost:8080`
- [ ] Display connected via HDMI
- [ ] Keyboard access (for initial setup and testing)
- [ ] At least 1GB free disk space

---

## Architecture Overview

### Kiosk System Flow

```
Boot
  ↓
systemd starts services
  ↓
calendarbot-lite@bencan.service starts
  ↓
[removed - not used] starts (or .bash_profile triggers startx)
  ↓
X server starts → .xinitrc executes
  ↓
.xinitrc launches:
  - matchbox window manager
  - waits for CalendarBot server ready
  - launches Chromium browser in kiosk mode
  ↓
Browser loads http://localhost:8080/whatsnext.html
  ↓
JavaScript sends heartbeat every 30 seconds
  ↓
Watchdog monitors heartbeat, server health, processes
  ↓
If issues detected → Progressive recovery
```

### Progressive Recovery Levels

**Browser Heartbeat Recovery:**
```
Level 0: Soft Reload (F5 via xdotool)        ~15 sec
Level 1: Browser Restart (kill + relaunch)   ~30 sec
Level 2: X Session Restart (systemctl)       ~60 sec
```

**System Health Recovery:**
```
Level 1: Browser Restart
Level 2: X Session Restart
Level 3: CalendarBot Service Restart
Level 4: System Reboot
```

---

## Step 1: Install X Server and Browser

Install required packages for graphical display:

```bash
# Install X server and utilities
sudo apt-get install -y \
    xserver-xorg \
    xinit \
    x11-xserver-utils

# Install minimal window manager
sudo apt-get install -y matchbox-window-manager

# Alternative window manager (if matchbox not available)
# sudo apt-get install -y openbox

# Install Chromium browser (recommended)
sudo apt-get install -y chromium-browser


# Install xdotool for keyboard automation (soft reload)
sudo apt-get install -y xdotool

# Install D-Bus for session management
sudo apt-get install -y dbus-x11
```

**Verify installations:**
```bash
# Check Chromium
which chromium || which chromium-browser

# Check X server
which xinit

# Check xdotool
xdotool version
```

---

## Step 2: Install Python YAML Parser

The watchdog daemon requires PyYAML for configuration:

```bash
# Activate CalendarBot virtual environment
source ~/calendarbot/venv/bin/activate

# Install PyYAML
pip install PyYAML

# Verify installation
python -c "import yaml; print(yaml.__version__)"
```

---

## Step 3: Configure X Session (.xinitrc)

Create X session initialization script:

```bash
# Copy .xinitrc template from repository
cp ~/calendarbot/kiosk/config/.xinitrc ~/.xinitrc

# Make executable
chmod +x ~/.xinitrc

# Review configuration
cat ~/.xinitrc
```

**What .xinitrc does:**
1. Starts session D-Bus
2. Disables screen blanking and DPMS power management
3. Launches matchbox window manager
4. Waits for CalendarBot server to be ready (up to 60 seconds)
5. Additional 15-second delay for rendering readiness
6. Launches Chromium with kiosk flags and Pi Zero 2 optimizations

**Key environment variables you can customize:**

```bash
# Edit .xinitrc if needed
nano ~/.xinitrc

# Available configuration:
# CALENDARBOT_URL - Override server URL (default: auto-detect or localhost:8080)
# BROWSER_TYPE - Force browser (auto, chromium)
# DISPLAY - X display number (default: :0)
```

**Example customization:**
```bash
# Add at top of .xinitrc
export CALENDARBOT_URL="http://192.168.1.100:8080/whatsnext.html"
export BROWSER_TYPE="chromium"
```

---

## Step 4: Configure .bash_profile for X Session Auto-Start

Configure `.bash_profile` to automatically start the X session when logging in to the console.

**Prerequisites**: Ensure auto-login is configured (see Section 1, Step 11).

**Copy the template .bash_profile:**
```bash
# Copy .bash_profile from repository
cp ~/calendarbot/kiosk/config/.bash-profile ~/.bash_profile

# Review the configuration
cat ~/.bash_profile
```

**What this does:**
- When you log in to tty1 (the console), `.bash_profile` checks if X is already running
- If not running, it automatically executes `startx`
- `startx` reads `~/.xinitrc` (configured in Step 3) which launches the browser in kiosk mode

**Expected contents:**
```bash
#!/bin/bash
# ~/.bash_profile

if [[ -z "$DISPLAY" && "$(tty)" == "/dev/tty1" ]]; then
  startx
fi
```

**Boot sequence:**
1. Pi boots
2. Auto-login to tty1 as `bencan` (configured in Section 1)
3. `.bash_profile` runs
4. `startx` launches
5. `.xinitrc` runs
6. Chromium launches in kiosk mode

---

## Step 5: Deploy Watchdog

Deploy the watchdog monitoring daemon step-by-step:

### 5.1: Deploy Watchdog Executable

```bash
# Copy watchdog daemon
sudo cp ~/calendarbot/kiosk/config/calendarbot-watchdog /usr/local/bin/
sudo chmod +x /usr/local/bin/calendarbot-watchdog

# Verify
/usr/local/bin/calendarbot-watchdog --help
```

### 5.2: Deploy Watchdog Configuration

```bash
# Create configuration directory
sudo mkdir -p /etc/calendarbot-monitor

# Copy configuration
sudo cp ~/calendarbot/kiosk/config/monitor.yaml /etc/calendarbot-monitor/

# Review configuration
sudo cat /etc/calendarbot-monitor/monitor.yaml
```

### 5.3: Create Directories

```bash
# Create log directory
sudo mkdir -p /var/log/calendarbot-watchdog
sudo chown bencan:bencan /var/log/calendarbot-watchdog

# Create state/data directory
sudo mkdir -p /var/local/calendarbot-watchdog
sudo chown bencan:bencan /var/local/calendarbot-watchdog
```

### 5.4: Deploy systemd Service

```bash
# Copy service file
sudo cp ~/calendarbot/kiosk/service/calendarbot-kiosk-watchdog@.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload
```

### 5.5: Configure Sudoers Privileges

The watchdog needs sudo access for recovery actions:

```bash
# Create sudoers configuration
sudo tee /etc/sudoers.d/calendarbot-watchdog << 'EOF'
# CalendarBot watchdog privileges
bencan ALL=NOPASSWD: /sbin/reboot
bencan ALL=NOPASSWD: /bin/systemctl restart calendarbot-lite@*.service
bencan ALL=NOPASSWD: /bin/systemctl restart [removed - not used]
bencan ALL=NOPASSWD: /bin/systemctl status calendarbot-lite@*.service
bencan ALL=NOPASSWD: /bin/systemctl status [removed - not used]
EOF

# Set correct permissions
sudo chmod 440 /etc/sudoers.d/calendarbot-watchdog

# Verify sudoers file is valid
sudo visudo -c
```

**Test sudo permissions:**
```bash
# Should not prompt for password
sudo systemctl status calendarbot-lite@bencan.service
```

### 5.6: Initialize State File

```bash
# Create initial state file
cat > /var/local/calendarbot-watchdog/state.json << 'EOF'
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

# Set ownership
sudo chown bencan:bencan /var/local/calendarbot-watchdog/state.json
```

---

## Step 6: Enable Watchdog Service

Enable the watchdog service (but don't start yet):

```bash
# Enable watchdog service
sudo systemctl enable calendarbot-kiosk-watchdog@bencan.service

# Verify enabled
sudo systemctl is-enabled calendarbot-kiosk-watchdog@bencan.service
# Should output: enabled
```

---

## Step 7: Configure Watchdog

Review and customize watchdog configuration:

```bash
# Edit configuration
sudo nano /etc/calendarbot-monitor/monitor.yaml
```

### Key Configuration Sections

**Health Check Intervals:**
```yaml
health_check:
  interval_s: 30                          # Main health check every 30 seconds
  browser_heartbeat_check_interval_s: 60  # Check browser heartbeat every 60s
  browser_heartbeat_timeout_s: 120        # Browser stuck if heartbeat > 2 min old
  startup_grace_period_s: 300             # 5-minute grace period on boot
  base_url: "http://127.0.0.1:8080"       # CalendarBot server URL
  render_marker: 'name="calendarbot-ready"'  # HTML marker for render detection
```

**Failure Thresholds:**
```yaml
thresholds:
  browser_heartbeat_fail_count: 2         # Trigger recovery after 2 consecutive failures
  max_browser_restarts_per_hour: 4        # Rate limiting
  max_service_restarts_per_hour: 2
  max_reboots_per_day: 1
  recovery_cooldown_s: 60                 # Minimum time between recoveries
```

**Recovery Configuration:**
```yaml
recovery:
  # Level 0: Soft reload (F5 key)
  browser_soft_reload:
    reload_cmd: "DISPLAY=:0 xdotool search --class chromium windowactivate --sync key F5"
    reload_delay_s: 15                    # Wait 15 sec to verify

  # Level 1: Browser restart
  browser_restart:
    launch_script: "/home/bencan/calendarbot/kiosk/scripts/launch-browser.sh"
    verification_delay_s: 30              # Wait 30 sec to verify

  # Level 2: X session restart
  x_restart:
    restart_cmd: "sudo systemctl restart [removed - not used]"
    verification_delay_s: 60              # Wait 60 sec to verify
```

**Resource Limits:**
```yaml
resource_limits:
  min_free_mem_kb: 30000                  # 30MB minimum free memory
  max_load_1m: 2.0                        # Max load average
  auto_throttle: false                    # Automatic degraded mode
```

**Logging:**
```yaml
logging:
  log_level: "INFO"                       # DEBUG, INFO, WARNING, ERROR, CRITICAL
  json_logging: true                      # Structured JSON logs
  journal_logging: true                   # Log to systemd journal
```

### Environment Variable Overrides

```bash
# Enable debug logging
export CALENDARBOT_WATCHDOG_DEBUG=true

# Disable all recovery actions (monitoring only)
export CALENDARBOT_WATCHDOG_DISABLED=true

# Custom log level
export CALENDARBOT_WATCHDOG_LOG_LEVEL=DEBUG
```

---

## Step 8: Start Services

Now start everything:

```bash
# Start watchdog
sudo systemctl start calendarbot-kiosk-watchdog@bencan.service

# If using systemd X session (Option A):
sudo systemctl start [removed - not used]

# If using .bash_profile (Option B):
# Login to console (tty1) or reboot

# Check statuses
sudo systemctl status calendarbot-lite@bencan.service
sudo systemctl status calendarbot-kiosk-watchdog@bencan.service
sudo systemctl status [removed - not used]  # if using systemd
```

**Expected output:**
```
● calendarbot-kiosk-watchdog@bencan.service - CalendarBot Kiosk Watchdog
     Loaded: loaded
     Active: active (running)

● [removed - not used] - CalendarBot Kiosk X Session
     Loaded: loaded
     Active: active (running)
```

**Within 30-60 seconds**, you should see:
- X server starts
- Browser window opens in full-screen kiosk mode
- CalendarBot calendar display loads

---

## Step 9: Verify Kiosk Operation

### Check Services

```bash
# All services running?
sudo systemctl status calendarbot-* | grep Active

# View logs
sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service -f
```

### Check Processes

```bash
# X server running?
ps aux | grep Xorg

# Browser running?
ps aux | grep chromium

# Watchdog running?
ps aux | grep calendarbot-watchdog
```

### Test Browser Heartbeat

```bash
# Manually send heartbeat
curl -X POST http://localhost:8080/api/browser-heartbeat

# Check health endpoint
curl -s http://localhost:8080/api/health | jq '.display_probe'
```

**Expected response:**
```json
{
  "last_render_probe_iso": "2025-11-03T14:30:00.000Z",
  "last_probe_ok": true,
  "last_probe_notes": "browser-heartbeat"
}
```

### Check Watchdog State

```bash
# View current state
cat /var/local/calendarbot-watchdog/state.json | jq

# View logs
sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service -n 50
```

**Healthy watchdog logs:**
```
INFO: Health check passed: server healthy, browser heartbeat ok
INFO: System resources OK: memory=120MB free, load=0.45
```

---

## Step 10: Test Progressive Recovery

Test the recovery system to ensure it works:

### Test Level 0: Soft Reload

```bash
# Manually trigger soft reload
DISPLAY=:0 xdotool search --class chromium windowactivate --sync key F5

# Watch browser reload
# (Should see page refresh without browser restart)
```

### Test Level 1: Browser Restart

```bash
# Kill browser process
pkill chromium

# Watch watchdog logs
sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service -f

# Expected behavior:
# 1. Watchdog detects missing browser heartbeat
# 2. After 2 consecutive failures (~2 minutes), escalates to Level 0 (soft reload)
# 3. No browser running, so escalates to Level 1 (browser restart)
# 4. Browser relaunches
# 5. Heartbeat resumes
```

### Test Level 2: X Session Restart

```bash
# Kill X server (WARNING: will close all windows)
sudo pkill -TERM Xorg

# Watch watchdog logs
sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service -f

# Expected behavior:
# 1. Watchdog detects missing X server
# 2. Escalates through levels to X restart
# 3. If using systemd X session: systemctl restart automatically restarts X
# 4. Browser relaunches
# 5. Heartbeat resumes
```

### Reset Watchdog State (if needed)

After testing, you may want to reset the watchdog state:

```bash
# Stop watchdog
sudo systemctl stop calendarbot-kiosk-watchdog@bencan.service

# Reset state
cat > /var/local/calendarbot-watchdog/state.json << 'EOF'
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

# Restart watchdog
sudo systemctl start calendarbot-kiosk-watchdog@bencan.service
```

---

## Verification Checklist

Before proceeding to Section 3, verify all items:

**Installation:**
- [ ] X server and window manager installed
- [ ] Chromium browser installed
- [ ] xdotool installed
- [ ] PyYAML installed in virtual environment
- [ ] .xinitrc deployed to user home

**Watchdog:**
- [ ] Watchdog daemon at `/usr/local/bin/calendarbot-watchdog`
- [ ] Configuration at `/etc/calendarbot-monitor/monitor.yaml`
- [ ] Directories created: `/var/log/calendarbot-watchdog`, `/var/local/calendarbot-watchdog`
- [ ] Sudoers privileges configured and tested
- [ ] Watchdog service enabled and running
- [ ] State file exists with valid JSON

**X Session:**
- [ ] X session starts automatically (via systemd or .bash_profile)
- [ ] Browser launches in kiosk mode
- [ ] Display shows CalendarBot calendar

**Functionality:**
- [ ] Browser heartbeat working: `curl -X POST http://localhost:8080/api/browser-heartbeat`
- [ ] Watchdog logs show "Health check passed"
- [ ] Watchdog state shows `browser_escalation_level: 0`
- [ ] Soft reload works: `DISPLAY=:0 xdotool ... key F5` refreshes page
- [ ] Browser restart recovery works (tested by killing browser)

---

## Files Deployed

Summary of files created or modified in this section:

| File Path | Purpose | User Editable |
|-----------|---------|---------------|
| `~/.xinitrc` | X session initialization | Yes |
| `~/.bash_profile` | Auto-start X (if using Option B) | Yes |
| `/usr/local/bin/calendarbot-watchdog` | Watchdog daemon | No |
| `/etc/calendarbot-monitor/monitor.yaml` | Watchdog configuration | **Yes** |
| `/etc/systemd/system/calendarbot-kiosk-watchdog@.service` | Watchdog service | Rarely |
| `/etc/systemd/system/[removed - not used]` | X session service (Option A) | Rarely |
| `/etc/sudoers.d/calendarbot-watchdog` | Sudo privileges | No |
| `/var/local/calendarbot-watchdog/state.json` | Watchdog state | Auto-managed |
| `~/calendarbot/kiosk/scripts/launch-browser.sh` | Browser launcher | No |
| `~/kiosk/kiosk.log` | X session logs | Auto-generated |
| `~/kiosk/browser-launch.log` | Browser launch logs | Auto-generated |

---

## Troubleshooting

### Issue: X server won't start

**Check logs:**
```bash
# If using systemd X session:
sudo journalctl -u [removed - not used] -n 50

# If using .bash_profile:
cat ~/.xsession-errors
```

**Common causes:**

1. **.xinitrc missing or not executable**
   ```bash
   ls -la ~/.xinitrc
   chmod +x ~/.xinitrc
   ```

2. **Display already in use**
   ```bash
   # Kill existing X server
   sudo pkill Xorg

   # Restart
   sudo systemctl restart [removed - not used]
   ```

3. **Graphics driver issues**
   ```bash
   # Check for errors
   dmesg | grep -i drm

   # Try forcing software rendering
   nano ~/.xinitrc
   # Add at top: export LIBGL_ALWAYS_SOFTWARE=1
   ```

### Issue: Browser not launching

**Check browser installed:**
```bash
which chromium || which chromium-browser || which epiphany
```

**Check .xinitrc logs:**
```bash
tail -f ~/kiosk/kiosk.log
```

**Check browser launch logs:**
```bash
tail -f ~/kiosk/browser-launch.log
```

**Test manual browser launch:**
```bash
DISPLAY=:0 chromium --kiosk http://localhost:8080/whatsnext.html
```

### Issue: Browser heartbeat not detected

**Test heartbeat endpoint:**
```bash
curl -X POST http://localhost:8080/api/browser-heartbeat
curl -s http://localhost:8080/api/health | jq '.display_probe'
```

**If endpoint returns error:**
```bash
# Restart CalendarBot service
sudo systemctl restart calendarbot-lite@bencan.service

# Check JavaScript console in browser (if accessible)
# Should see: "Browser heartbeat sent successfully"
```

**Check system time:**
```bash
timedatectl
# Sync time if needed
sudo timedatectl set-ntp true
```

### Issue: Watchdog not taking recovery actions

**Check watchdog state:**
```bash
cat /var/local/calendarbot-watchdog/state.json | jq
```

**Rate limited?**
```bash
# Check browser_restarts array
# If >= 4 restarts in last hour, rate limited

# Reset state (stop watchdog first)
sudo systemctl stop calendarbot-kiosk-watchdog@bencan.service
# Use reset command from Step 12
sudo systemctl start calendarbot-kiosk-watchdog@bencan.service
```

**Check sudo permissions:**
```bash
sudo -u bencan sudo -l
# Should show: systemctl restart, reboot commands
```

**Enable debug logging:**
```bash
# Edit service environment
sudo systemctl edit calendarbot-kiosk-watchdog@bencan.service

# Add:
[Service]
Environment="CALENDARBOT_WATCHDOG_DEBUG=true"

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart calendarbot-kiosk-watchdog@bencan.service

# View debug logs
sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service -f
```

### Issue: xdotool soft reload not working

**Test xdotool manually:**
```bash
DISPLAY=:0 xdotool search --class chromium
# Should return window ID

DISPLAY=:0 xdotool search --class chromium windowactivate --sync key F5
# Should reload browser
```

**Check browser window class:**
```bash
DISPLAY=:0 xprop | grep WM_CLASS
# Click browser window
# Note the class name (chromium, Chromium, epiphany, etc.)
```

**Update monitor.yaml if needed:**
```bash
sudo nano /etc/calendarbot-monitor/monitor.yaml
# Update browser_soft_reload.reload_cmd with correct class name
```

### Issue: High memory usage / OOM

**Check memory:**
```bash
free -h
cat /proc/meminfo | grep -i available
```

**Enable swap:**
```bash
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

**Reduce browser memory:**
```bash
nano ~/.xinitrc
# Add to Chromium flags:
# --js-flags="--max-old-space-size=128"
```

**Enable watchdog degraded mode:**
```bash
sudo nano /etc/calendarbot-monitor/monitor.yaml
# Set: auto_throttle: true
# Restart watchdog
sudo systemctl restart calendarbot-kiosk-watchdog@bencan.service
```

---

## Progressive Recovery Details

### Browser Heartbeat System

**How it works:**

1. **JavaScript in page** (`whatsnext.js`):
   ```javascript
   setInterval(() => {
       fetch('/api/browser-heartbeat', {method: 'POST'});
   }, 30000);  // Every 30 seconds
   ```

2. **Server records timestamp** (`routes/api_routes.py`):
   ```python
   health_tracker.record_render_probe(ok=True, notes="browser-heartbeat")
   ```

3. **Watchdog checks** (`/usr/local/bin/calendarbot-watchdog`):
   ```python
   response = requests.get('http://localhost:8080/api/health')
   last_heartbeat = response.json()['display_probe']['last_render_probe_iso']
   if timestamp_age(last_heartbeat) > 120:  # 2 minutes
       trigger_recovery()
   ```

### Escalation Logic

**After 2 consecutive heartbeat failures:**

```
Start at Level 0 (soft reload)
  ↓
Execute: DISPLAY=:0 xdotool ... key F5
  ↓
Wait 15 seconds
  ↓
Check heartbeat
  ↓
├─ Heartbeat OK → Reset to level 0, done
│
└─ Heartbeat still stale → Escalate to Level 1
   ↓
   Execute: launch-browser.sh (kill + relaunch)
   ↓
   Wait 30 seconds
   ↓
   Check heartbeat
   ↓
   ├─ Heartbeat OK → Stay at level 1, done
   │
   └─ Heartbeat still stale → Escalate to Level 2
      ↓
      Execute: sudo systemctl restart [removed - not used]
      ↓
      Wait 60 seconds
      ↓
      Check heartbeat
      ↓
      ├─ Heartbeat OK → Stay at level 2, done
      │
      └─ Heartbeat still stale → System escalation (service restart)
```

**Rate limiting:**
- Max 4 browser restarts per hour
- Max 2 service restarts per hour
- Max 1 reboot per day
- Minimum 60 seconds between recoveries

---

## Performance Notes (Pi Zero 2)

Expected resource usage:

- **Chromium**: 100-200MB RAM, 10-20% CPU (idle)
- **X server**: 20-40MB RAM, 5% CPU
- **Watchdog**: 20-30MB RAM, <2% CPU

**Total kiosk overhead**: ~200-300MB RAM

**Optimization tips:**
- Use Chromium instead of Chromium if memory tight
- Disable JavaScript features in browser (already in .xinitrc)
- Increase watchdog intervals if CPU constrained

---

## Next Steps

**Section 2 Complete!** ✅

You now have a self-healing kiosk with:
- Automatic browser launch on boot
- Browser heartbeat monitoring
- Progressive 3-level recovery
- systemd service management

**Choose your next section:**

- **[Section 3: Alexa Integration →](3_ALEXA_INTEGRATION.md)** - Add HTTPS and Alexa access
- **[Section 4: Log Management →](4_LOG_MANAGEMENT.md)** - Add log rotation and monitoring

**Or return to**: [Installation Overview](INSTALLATION_OVERVIEW.md)
