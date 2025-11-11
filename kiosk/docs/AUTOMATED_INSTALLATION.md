# CalendarBot Kiosk - Automated Installation Guide

This guide explains how to use the automated installation script to deploy CalendarBot Kiosk with minimal manual intervention.

---

## Overview

The automated installer ([install-kiosk.sh](../install-kiosk.sh)) provides:

✅ **Idempotent operation** - Safe to run multiple times
✅ **Modular installation** - Install only what you need
✅ **Dry-run mode** - Preview changes before applying
✅ **Automatic backups** - Original configs preserved
✅ **Progress tracking** - Clear feedback at each step
✅ **Verification checks** - Confirms successful installation

### What's Automated

| Section | Component | Automation Level |
|---------|-----------|------------------|
| **1. Base** | System packages, repo, venv, .env, service | ✅ Fully automated |
| **1. Base** | Auto-login configuration | ✅ Fully automated |
| **2. Kiosk** | X server, browser, .xinitrc, .bash_profile | ✅ Fully automated |
| **2. Kiosk** | Watchdog daemon, config, sudoers | ✅ Fully automated |
| **3. Alexa** | Caddy, bearer token, Caddyfile, firewall | ✅ Fully automated |
| **3. Alexa** | DNS, router, AWS Lambda, Alexa skill | ⚠️ Manual (see [MANUAL_STEPS.md](MANUAL_STEPS.md)) |
| **4. Monitoring** | Logrotate, scripts, cron jobs | ✅ Fully automated |
| **4. Monitoring** | rsyslog, log shipping service | 🔧 Partially automated |

---

## Prerequisites

### Hardware
- Raspberry Pi Zero 2 W / Pi 3 / Pi 4 / Pi 5
- MicroSD card: 16GB minimum, 32GB recommended
- HDMI display (for kiosk mode)
- Network connectivity

### Software
- Fresh Raspbian/Debian 11+ installation
- SSH enabled
- User account created (e.g., `bencan`)
- Internet connection

### Required Information
- **ICS Calendar URL** (from Outlook, Google Calendar, etc.)
- **Domain name** (only for Alexa integration)
- **AWS Account** (only for Alexa integration)
- **Amazon Developer Account** (only for Alexa integration)

---

## Quick Start

### 1. Clone Repository

SSH into your Raspberry Pi:

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/calendarbot.git
cd calendarbot/kiosk
```

### 2. Create Configuration File

```bash
cp install-config.example.yaml install-config.yaml
nano install-config.yaml
```

**Minimum required changes:**
```yaml
system:
  username: bencan  # Change to your username

calendarbot:
  ics_url: "https://outlook.office365.com/owa/calendar/YOUR_CALENDAR_ID/calendar.ics"
```

Save and exit (Ctrl+X, Y, Enter)

### 3. Run Installer (Dry-Run First)

**Always run a dry-run first** to preview changes:

```bash
sudo ./install-kiosk.sh --config install-config.yaml --dry-run
```

Review the output. If everything looks correct:

```bash
sudo ./install-kiosk.sh --config install-config.yaml
```

### 4. Reboot (for kiosk mode)

```bash
sudo reboot
```

After reboot, the kiosk should auto-start and display your calendar.

---

## Installation Paths

The installer supports three pre-configured deployment paths:

### Minimal (Sections 1+2) - ~30 minutes

Local kiosk display only, no internet-facing services.

**Configuration:**
```yaml
deployment_path: minimal
```

**What's included:**
- CalendarBot server (port 8080, localhost only)
- Auto-login and X session
- Chromium kiosk mode
- Watchdog with progressive recovery
- Browser heartbeat monitoring

**Use case:** Private calendar display, no remote access

---

### Full (Sections 1+2+3) - ~60 minutes + manual steps

Local kiosk + Alexa voice interface.

**Configuration:**
```yaml
deployment_path: full
```

**What's included:**
- Everything from Minimal, plus:
- Caddy reverse proxy with HTTPS
- Bearer token authentication
- UFW firewall
- Manual: DNS, router config, AWS Lambda, Alexa skill

**Use case:** Home/office kiosk with Alexa integration

---

### Production (All sections) - ~90 minutes + manual steps

Everything, plus comprehensive monitoring and logging.

**Configuration:**
```yaml
deployment_path: production
```

**What's included:**
- Everything from Full, plus:
- Logrotate for log management
- Automated daily/weekly reports
- Monitoring status dashboard
- Optional: rsyslog structured logging
- Optional: Remote log shipping

**Use case:** Production deployment with observability

---

## Configuration Reference

### Essential Settings

```yaml
# User running CalendarBot
system:
  username: bencan

# Your calendar feed URL (REQUIRED)
calendarbot:
  ics_url: "https://outlook.office365.com/owa/calendar/.../calendar.ics"
  web_port: 8080  # Default, change if needed
  refresh_interval: 300  # Calendar refresh in seconds (5 min)

# Kiosk display URL
kiosk:
  browser_url: "http://localhost:8080/whatsnext.html"

# Alexa integration (Section 3 only)
alexa:
  domain: "your-domain.com"  # Your domain name
  bearer_token: ""  # Leave empty to auto-generate
```

### Advanced Settings

```yaml
# Watchdog tuning (adjust recovery thresholds)
kiosk:
  watchdog:
    health_check_interval: 30  # Seconds between checks
    browser_heartbeat_timeout: 120  # Browser stuck after 2 min
    thresholds:
      max_browser_restarts_per_hour: 4  # Rate limiting
      max_service_restarts_per_hour: 2
      max_reboots_per_day: 1

# Monitoring configuration
monitoring:
  reports:
    daily_report_time: "01:00"  # HH:MM format
    weekly_report_time: "02:00"
  status_updates:
    interval_minutes: 5  # How often to update status

# Installation behavior
installation:
  backup_enabled: true  # Backup existing configs
  auto_reboot: false  # Auto-reboot after install (use with caution)
  run_verification: true  # Run verification checks
```

See [install-config.example.yaml](../install-config.example.yaml) for complete reference with comments.

---

## Usage Examples

### Initial Installation (Minimal Path)

```bash
# 1. Configure
cp install-config.example.yaml install-config.yaml
nano install-config.yaml
# Set: deployment_path: minimal, username, ics_url

# 2. Preview changes
sudo ./install-kiosk.sh --config install-config.yaml --dry-run

# 3. Install
sudo ./install-kiosk.sh --config install-config.yaml

# 4. Reboot
sudo reboot
```

---

### Update Existing Installation

When you need to update configurations or pull latest code:

```bash
# 1. Update configuration file if needed
nano install-config.yaml

# 2. Run in update mode
sudo ./install-kiosk.sh --config install-config.yaml --update

# 3. Restart services (automatic in update mode)
```

**Update mode:**
- Backs up existing configs before replacing
- Restarts services to apply changes
- Preserves state files (watchdog state, etc.)
- Safe to run on existing installations

---

### Install Specific Section Only

Install only one section (useful for modular deployment):

```bash
# Install only Section 2 (assuming Section 1 already installed)
sudo ./install-kiosk.sh --config install-config.yaml --section 2

# Install only Section 3 (Alexa)
sudo ./install-kiosk.sh --config install-config.yaml --section 3
```

**Valid sections:** 1 (base), 2 (kiosk), 3 (alexa), 4 (monitoring)

---

### Verbose Mode

Get detailed output for troubleshooting:

```bash
sudo ./install-kiosk.sh --config install-config.yaml --verbose
```

Shows:
- Every package checked/installed
- Every file backed up
- Every configuration value set
- All systemd operations

---

### Dry-Run Mode (Recommended First Step)

**Always dry-run before making changes:**

```bash
sudo ./install-kiosk.sh --config install-config.yaml --dry-run
```

Dry-run shows:
- What packages would be installed
- What files would be created/modified
- What services would be enabled/started
- What configurations would change

**No changes are made to the system.**

---

## Installation Flow

### Step-by-Step Process

1. **Configuration Loading**
   - Parses YAML configuration
   - Validates required settings
   - Exports configuration to environment

2. **State Detection**
   - Checks if repository exists
   - Checks if services are installed
   - Checks if packages are already present
   - Determines what needs to be done

3. **Package Installation**
   - Updates apt package lists
   - Installs only missing packages
   - Skips already-installed packages (idempotent)

4. **Section Installation** (for each enabled section):
   - Backs up existing configurations
   - Deploys new configurations
   - Creates/updates systemd services
   - Enables and starts services
   - Runs verification checks

5. **Summary**
   - Lists all backup files created
   - Shows any manual steps required
   - Provides next steps

### Time Estimates

| Path | Time (Automated) | Time (Manual) | Total |
|------|------------------|---------------|-------|
| Minimal | ~30 min | 0 | ~30 min |
| Full | ~30 min | 30-60 min | ~90 min |
| Production | ~45 min | 30-60 min | ~2 hrs |

*Times vary based on Pi model and internet speed*

---

## Verification

### Automated Verification

The installer automatically verifies each section (unless disabled):

**Section 1 (Base):**
- ✅ CalendarBot service is running
- ✅ API health check responds
- ✅ .env file configured correctly

**Section 2 (Kiosk):**
- ✅ Watchdog service is running
- ✅ Watchdog binary is executable
- ✅ State file exists

**Section 3 (Alexa):**
- ✅ Caddy service is running
- ✅ Caddyfile exists
- ✅ Bearer token is set

**Section 4 (Monitoring):**
- ✅ Logrotate config exists
- ✅ Monitoring scripts deployed
- ✅ Cron jobs configured

### Manual Verification

After installation, verify end-to-end:

```bash
# Check all CalendarBot services
sudo systemctl status calendarbot-lite@bencan.service
sudo systemctl status calendarbot-kiosk-watchdog@bencan.service

# Check API
curl -s http://localhost:8080/health | jq

# Check calendar data
curl -s http://localhost:8080/api/whats-next | jq

# Check logs
sudo journalctl -u calendarbot-* -n 50

# For Alexa (after manual steps complete):
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-domain.com/api/alexa/next-meeting | jq
```

---

## Backups

### Automatic Backups

The installer automatically backs up files before modifying:

- **Location:** `/var/backups/calendarbot/`
- **Format:** `filename.TIMESTAMP.bak`
- **When:** Before any file modification

**Files backed up:**
- `.env`
- `.xinitrc`
- `.bash_profile`
- `/etc/caddy/Caddyfile`
- `/etc/calendarbot-monitor/monitor.yaml`
- Systemd service files (if updating)
- Sudoers files
- Any other existing configuration

### Disable Backups

If you don't want backups (not recommended):

```yaml
installation:
  backup_enabled: false
```

### Restore from Backup

```bash
# List backups
ls -lh /var/backups/calendarbot/

# Restore a file
sudo cp /var/backups/calendarbot/Caddyfile.20251103_140530.bak \
  /etc/caddy/Caddyfile

# Reload service
sudo systemctl reload caddy
```

---

## Idempotency

The installer is **idempotent** - safe to run multiple times without causing issues.

### What Happens on Re-Run

**Packages:**
- Checks if already installed
- Skips if present
- Only installs missing packages

**Files:**
- Backs up existing file
- Replaces with new version
- Preserves ownership and permissions

**Services:**
- Checks if already enabled
- Skips `systemctl enable` if already enabled
- Restarts if in update mode

**State Files:**
- **Never overwrites** existing state
- Preserves watchdog recovery history
- Only creates if missing

### Safe Operations

✅ Run installer multiple times
✅ Re-run after config changes
✅ Run in update mode on existing installations
✅ Run specific sections independently
✅ Run dry-run as many times as needed

### Caution

⚠️ **Bearer token regeneration**: Only regenerate if intentional (must update AWS Lambda)
⚠️ **Auto-reboot**: Only enable if you're sure (set `installation.auto_reboot: true`)
⚠️ **Git auto-pull**: May pull unwanted changes (set `advanced.git.auto_pull: true`)

---

## Troubleshooting

### Configuration Errors

**Error: "Missing required config: calendarbot.ics_url"**

Solution: Edit `install-config.yaml` and set your ICS URL:
```yaml
calendarbot:
  ics_url: "https://outlook.office365.com/owa/calendar/YOUR_ID/calendar.ics"
```

**Error: "User USERNAME does not exist"**

Solution: Create the user first:
```bash
sudo adduser bencan
```

Or update config to use existing user:
```yaml
system:
  username: pi  # Use existing user
```

---

### Installation Failures

**Error: "Failed to clone repository"**

Causes:
- Network connectivity issue
- Git not installed
- Repository URL incorrect

Solution:
```bash
# Test network
ping -c 3 github.com

# Install git
sudo apt-get install -y git

# Update repository URL in script if needed
```

**Error: "Package installation failed"**

Solution:
```bash
# Update package lists manually
sudo apt-get update

# Try installing problem package manually
sudo apt-get install -y PACKAGE_NAME

# Re-run installer
```

---

### Service Issues

**CalendarBot service fails to start**

Check logs:
```bash
sudo journalctl -u calendarbot-lite@bencan.service -n 50
```

Common causes:
- Invalid ICS URL in .env
- Python dependency missing
- Port 8080 already in use

Solution:
```bash
# Verify .env
cat ~/calendarbot/.env

# Test manually
cd ~/calendarbot
source venv/bin/activate
python -m calendarbot_lite
```

**Watchdog service fails to start**

Check logs:
```bash
sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service -n 50
```

Common causes:
- PyYAML not installed
- monitor.yaml syntax error
- CalendarBot service not running

Solution:
```bash
# Install PyYAML
cd ~/calendarbot
source venv/bin/activate
pip install PyYAML

# Verify config syntax
python3 -c "import yaml; yaml.safe_load(open('/etc/calendarbot-monitor/monitor.yaml'))"

# Restart dependencies
sudo systemctl restart calendarbot-lite@bencan.service
sudo systemctl restart calendarbot-kiosk-watchdog@bencan.service
```

---

### Kiosk Mode Issues

**Kiosk doesn't auto-start after reboot**

Check auto-login:
```bash
cat /etc/systemd/system/getty@tty1.service.d/autologin.conf
```

Should contain:
```
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin bencan --noclear %I $TERM
```

Fix:
```bash
# Re-run Section 1 to reconfigure auto-login
sudo ./install-kiosk.sh --config install-config.yaml --section 1
sudo reboot
```

**X server fails to start**

Check logs:
```bash
cat ~/.xsession-errors
```

Common causes:
- Display not connected
- X server packages not installed
- .xinitrc syntax error

Solution:
```bash
# Test X server manually
startx
```

**Browser doesn't open**

Check if Chromium is installed:
```bash
which chromium-browser
```

Check .xinitrc:
```bash
cat ~/.xinitrc
```

---

### Alexa Integration Issues

See [MANUAL_STEPS.md](MANUAL_STEPS.md#troubleshooting-alexa-skill-issues) for comprehensive Alexa troubleshooting.

**Quick checks:**
```bash
# Verify bearer token in .env
grep CALENDARBOT_ALEXA_BEARER_TOKEN ~/calendarbot/.env

# Verify Caddy is running
sudo systemctl status caddy

# Test HTTPS endpoint (from external network)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-domain.com/api/alexa/next-meeting
```

---

## Maintenance

### Updating CalendarBot Code

```bash
cd ~/calendarbot
git pull

# Re-run installer in update mode
cd kiosk
sudo ./install-kiosk.sh --config install-config.yaml --update
```

### Updating Configuration

```bash
# Edit configuration
nano ~/calendarbot/kiosk/install-config.yaml

# Apply changes
sudo ./install-kiosk.sh --config install-config.yaml --update
```

### Rotating Bearer Token

```bash
# 1. Generate new token
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. Update config
nano ~/calendarbot/kiosk/install-config.yaml
# Set: alexa.bearer_token: "NEW_TOKEN"

# 3. Apply
sudo ./install-kiosk.sh --config install-config.yaml --update

# 4. Update AWS Lambda environment variables (manual)
# AWS Console → Lambda → Configuration → Environment variables
```

### Viewing Logs

```bash
# CalendarBot server
sudo journalctl -u calendarbot-lite@bencan.service -f

# Watchdog
sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service -f

# Caddy
sudo journalctl -u caddy -f

# All CalendarBot services
sudo journalctl -u calendarbot-* -f

# Last 100 lines
sudo journalctl -u calendarbot-* -n 100
```

---

## Advanced Usage

### Custom Repository Location

```yaml
system:
  repo_dir: /opt/calendarbot
  venv_dir: /opt/calendarbot/venv
```

The installer will use these paths instead of defaults.

### Custom Service Names

The installer creates services named:
- `calendarbot-lite@USERNAME.service`
- `calendarbot-kiosk-watchdog@USERNAME.service`

USERNAME is taken from `system.username` config.

### Skip Package Updates

```yaml
advanced:
  apt_update: false  # Don't run apt-get update
  apt_upgrade: false  # Don't run apt-get upgrade
```

Useful for offline installations or when package lists are current.

### Git Integration

```yaml
advanced:
  git:
    auto_pull: true  # Pull latest changes if repo exists
    branch: main     # Specify branch
```

Automatically updates code from git during installation.

---

## Next Steps

After installation:

1. **Verify kiosk display** - Should show calendar after reboot

2. **Complete manual steps** (if using Alexa):
   - See [MANUAL_STEPS.md](MANUAL_STEPS.md)
   - Configure DNS, router, AWS Lambda, Alexa skill

3. **Test recovery mechanisms**:
   ```bash
   # Kill browser (watchdog should restart it)
   pkill chromium

   # Watch recovery logs
   sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service -f
   ```

4. **Monitor health**:
   ```bash
   # Check API health
   curl -s http://localhost:8080/api/health | jq

   # Check watchdog state
   cat /var/local/calendarbot-watchdog/state.json | jq
   ```

5. **Set up monitoring** (if using Section 4):
   - Wait for first daily report (runs at 01:00)
   - Check: `/var/local/calendarbot-watchdog/reports/`

---

## FAQ

**Q: Can I run the installer without sudo?**

A: No, the installer requires root privileges to install packages, create systemd services, and modify system files.

**Q: What happens if the installer fails mid-way?**

A: The installer is idempotent. Fix the issue and re-run. Already-completed steps will be skipped.

**Q: Can I install on Ubuntu instead of Raspbian?**

A: Yes, the installer works on Debian-based distributions including Ubuntu. Tested on Debian 11+, Ubuntu 20.04+, Raspbian Bullseye+.

**Q: How do I uninstall CalendarBot?**

A: Currently no automated uninstaller. Manual removal:
```bash
# Stop and disable services
sudo systemctl stop calendarbot-*
sudo systemctl disable calendarbot-*

# Remove files
sudo rm /etc/systemd/system/calendarbot-*
sudo rm -rf ~/calendarbot
sudo rm /usr/local/bin/calendarbot-watchdog
sudo rm -rf /var/log/calendarbot-watchdog
sudo rm -rf /var/local/calendarbot-watchdog

# Reload systemd
sudo systemctl daemon-reload
```

**Q: Can I install on multiple Raspberry Pi devices?**

A: Yes! Use the same `install-config.yaml` on each Pi. Only change `alexa.bearer_token` if you want separate authentication per device.

**Q: Does the installer support Pi 5?**

A: Yes, tested on Pi Zero 2 W, Pi 3, Pi 4, and Pi 5.

---

## Support

### Documentation

- **Installation Overview**: [INSTALLATION_OVERVIEW.md](INSTALLATION_OVERVIEW.md)
- **Manual Steps**: [MANUAL_STEPS.md](MANUAL_STEPS.md)
- **Base Installation**: [1_BASE_INSTALL.md](1_BASE_INSTALL.md)
- **Kiosk & Watchdog**: [2_KIOSK_WATCHDOG.md](2_KIOSK_WATCHDOG.md)
- **Alexa Integration**: [3_ALEXA_INTEGRATION.md](3_ALEXA_INTEGRATION.md)
- **Log Management**: [4_LOG_MANAGEMENT.md](4_LOG_MANAGEMENT.md)

### Getting Help

1. Check logs: `sudo journalctl -u calendarbot-* -n 100`
2. Run dry-run mode to see what would change
3. Review verification checks after installation
4. Consult troubleshooting sections above
5. Check existing documentation in `kiosk/docs/`

---

**Last Updated**: 2025-11-03
**Installer Version**: 1.0.0
**Compatible with**: Debian 11+, Ubuntu 20.04+, Raspbian Bullseye+
