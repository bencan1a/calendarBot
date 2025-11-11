# CalendarBot Kiosk Deployment Checklist

Quick-reference checklists for verifying your installation.

**Last Updated**: 2025-11-03

---

## Pre-Deployment Checklist

Complete before starting any installation:

### Hardware & Network
- [ ] Raspberry Pi Zero 2 W / Pi 3 / Pi 4 with power supply
- [ ] MicroSD card (16GB minimum, 32GB recommended)
- [ ] Display connected (for kiosk mode)
- [ ] Network connectivity (WiFi or Ethernet configured)
- [ ] SSH access enabled and tested
- [ ] At least 2GB free disk space

### Credentials & Information
- [ ] ICS calendar URL obtained (Office 365, Google Calendar, etc.)
- [ ] Non-root user account created (e.g., `bencan`)
- [ ] (If Alexa) Domain name registered
- [ ] (If Alexa) DNS management access
- [ ] (If logs) Webhook endpoint URL (optional)

### System Preparation
- [ ] System updated: `sudo apt-get update && sudo apt-get upgrade -y`
- [ ] Git installed: `sudo apt-get install -y git`
- [ ] Python 3.7+ verified: `python3 --version`
- [ ] Locale configured: `sudo raspi-config` → Localisation Options

---

## Section 1: Base Installation Checklist

### Installation Steps

- [ ] System packages installed (python3, python3-venv, git, curl, jq)
- [ ] Repository cloned to `~/calendarbot`
- [ ] Virtual environment created: `~/calendarbot/venv/`
- [ ] Virtual environment activated: `source venv/bin/activate`
- [ ] Python dependencies installed: `pip install -r requirements.txt`
- [ ] `.env` file created from `.env.example`
- [ ] ICS calendar URL added to `.env`
- [ ] Other required settings configured in `.env`
- [ ] Auto-login configured (optional, required for kiosk mode in Section 2)

### Service Configuration

- [ ] systemd service file created: `/etc/systemd/system/calendarbot-lite@.service`
- [ ] Service enabled: `sudo systemctl enable calendarbot-lite@bencan.service`
- [ ] Service started: `sudo systemctl start calendarbot-lite@bencan.service`
- [ ] Service active: `sudo systemctl is-active calendarbot-lite@bencan.service` returns `active`

### Verification

- [ ] Server responds: `curl http://localhost:8080/api/whats-next` returns JSON
- [ ] Health endpoint OK: `curl http://localhost:8080/health` shows `"status":"ok"`
- [ ] Web interface loads: `http://<PI_IP>:8080/whatsnext.html` displays calendar
- [ ] Logs show no errors: `sudo journalctl -u calendarbot-lite@bencan.service | grep ERROR`
- [ ] Calendar data refreshing: Logs show "Loaded X events" messages
- [ ] Service survives reboot: `sudo reboot` → verify service auto-starts

---

## Section 2: Kiosk Mode & Watchdog Checklist

### Installation Steps

- [ ] X server packages installed (xserver-xorg, xinit, x11-xserver-utils)
- [ ] Window manager installed (matchbox-window-manager or openbox)
- [ ] Chromium browser installed
- [ ] xdotool installed
- [ ] PyYAML installed in virtual environment
- [ ] `.xinitrc` deployed to `~/.xinitrc` and made executable
- [ ] `.bash_profile` deployed to `~/.bash_profile` for auto-starting X
- [ ] Auto-login configured (from Section 1, Step 11)

### Watchdog Deployment

- [ ] Watchdog daemon copied to `/usr/local/bin/calendarbot-watchdog`
- [ ] Watchdog executable: `chmod +x /usr/local/bin/calendarbot-watchdog`
- [ ] Configuration deployed: `/etc/calendarbot-monitor/monitor.yaml`
- [ ] Log directory created: `/var/log/calendarbot-watchdog/`
- [ ] State directory created: `/var/local/calendarbot-watchdog/`
- [ ] Directories owned by bencan user
- [ ] Watchdog service deployed: `/etc/systemd/system/calendarbot-kiosk-watchdog@.service`
- [ ] Sudoers configuration created: `/etc/sudoers.d/calendarbot-watchdog`
- [ ] Sudoers permissions correct: `chmod 440 /etc/sudoers.d/calendarbot-watchdog`
- [ ] State file initialized: `/var/local/calendarbot-watchdog/state.json`

### Service Configuration

- [ ] Watchdog service enabled: `sudo systemctl enable calendarbot-kiosk-watchdog@bencan.service`
- [ ] Watchdog service started: `sudo systemctl start calendarbot-kiosk-watchdog@bencan.service`
- [ ] X session auto-starts via .bash_profile on console login

### Verification

- [ ] X server running: `ps aux | grep Xorg` shows process
- [ ] Chromium browser running: `ps aux | grep chromium` shows process
- [ ] Display shows calendar in full-screen kiosk mode
- [ ] Browser heartbeat working: `curl -X POST http://localhost:8080/api/browser-heartbeat` returns 200
- [ ] Health endpoint shows heartbeat: `curl http://localhost:8080/api/health | jq '.display_probe'` shows recent timestamp
- [ ] Watchdog service active: `sudo systemctl is-active calendarbot-kiosk-watchdog@bencan.service` returns `active`
- [ ] Watchdog logs healthy: `sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service | grep "Health check passed"`
- [ ] Watchdog state valid: `cat /var/local/calendarbot-watchdog/state.json | jq` shows valid JSON
- [ ] Sudo permissions work: `sudo systemctl status calendarbot-lite@bencan.service` (no password prompt)
- [ ] Soft reload works: `DISPLAY=:0 xdotool search --class chromium windowactivate --sync key F5` refreshes page
- [ ] Auto-login works: Reboot and verify X starts automatically on tty1

### Recovery Testing

- [ ] Browser recovery tested: Kill browser → watchdog restarts it
- [ ] Escalation tested: Browser heartbeat stops → watchdog escalates through levels
- [ ] System survives reboot: Auto-login → .bash_profile → X → browser auto-start

---

## Section 3: Alexa Integration Checklist

### Prerequisites

- [ ] Domain name registered and accessible
- [ ] Public IP address identified: `curl ifconfig.me`
- [ ] Router port forwarding configured (80 → Pi:80, 443 → Pi:443)
- [ ] DNS A record created pointing to public IP
- [ ] DNS propagation verified: `nslookup YOUR_DOMAIN` returns correct IP
- [ ] Amazon Developer Account created
- [ ] AWS Account created

### Installation Steps

- [ ] Caddy installed: `caddy version` works
- [ ] Bearer token generated: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Bearer token saved securely
- [ ] Bearer token added to `~/calendarbot/.env` as `CALENDARBOT_ALEXA_BEARER_TOKEN`
- [ ] CalendarBot service restarted: `sudo systemctl restart calendarbot-lite@bencan.service`
- [ ] Caddyfile deployed to `/etc/caddy/Caddyfile`
- [ ] Caddyfile edited with your domain name
- [ ] Caddy log directory created: `/var/log/caddy/`
- [ ] Firewall configured: UFW allows ports 22, 80, 443
- [ ] Caddy service enabled: `sudo systemctl enable caddy`
- [ ] Caddy service started: `sudo systemctl start caddy`

### Verification

- [ ] Caddy service active: `sudo systemctl is-active caddy` returns `active`
- [ ] HTTPS certificate obtained: Caddy logs show "certificate obtained successfully"
- [ ] HTTPS works: `curl -I https://YOUR_DOMAIN` returns 200 (test from external network)
- [ ] Local bearer token test passes: `curl -H "Authorization: Bearer TOKEN" http://localhost:8080/api/alexa/next-meeting` returns JSON
- [ ] Remote endpoint without token returns 401: `curl https://YOUR_DOMAIN/api/alexa/next-meeting` returns `{"error":"Unauthorized"}`
- [ ] Remote endpoint with token returns 200: `curl -H "Authorization: Bearer TOKEN" https://YOUR_DOMAIN/api/alexa/next-meeting` returns calendar data
- [ ] Debug endpoint shows header forwarding: `curl -H "Authorization: Bearer TEST" https://YOUR_DOMAIN/debug-headers` shows "Authorization: Bearer TEST"
- [ ] All Alexa endpoints tested: next-meeting, time-until-next, done-for-day

### AWS Lambda

- [ ] Lambda function created: `calendarbot-alexa-skill`
- [ ] Lambda code deployed from `alexa_skill_backend.py`
- [ ] Environment variables configured (CALENDARBOT_ENDPOINT, CALENDARBOT_BEARER_TOKEN, REQUEST_TIMEOUT)
- [ ] Lambda timeout set to 10 seconds
- [ ] Test events created for all intents (GetNextMeeting, GetTimeUntilNext, GetDoneForDay)
- [ ] All Lambda test events pass
- [ ] Lambda ARN copied for Alexa skill configuration

### Alexa Skill

- [ ] Skill created in Amazon Developer Console: "Calendar Bot"
- [ ] Interaction model JSON deployed
- [ ] Model built successfully
- [ ] Endpoint configured with Lambda ARN
- [ ] Skill enabled for testing (Development mode)
- [ ] Alexa simulator tests pass: "ask calendar bot what's my next meeting"
- [ ] Alexa simulator tests pass: "ask calendar bot how long until my next meeting"
- [ ] Alexa simulator tests pass: "ask calendar bot when am I done for the day"
- [ ] Physical Alexa device tests pass
- [ ] Voice commands return correct calendar data

### Security

- [ ] Bearer token NOT committed to git
- [ ] `.env` file in `.gitignore`
- [ ] Only required ports exposed (22, 80, 443)
- [ ] Port 8080 NOT accessible from internet (only localhost)

---

## Section 4: Monitoring & Log Management Checklist

### Installation Steps

- [ ] Logrotate configuration deployed: `/etc/logrotate.d/calendarbot-watchdog`
- [ ] Logrotate tested: `sudo logrotate -d /etc/logrotate.d/calendarbot-watchdog`
- [ ] (Optional) rsyslog with JSON parser installed
- [ ] (Optional) rsyslog configuration deployed: `/etc/rsyslog.d/50-calendarbot.conf`
- [ ] (Optional) rsyslog log directory created: `/var/log/calendarbot/`
- [ ] (Optional) rsyslog restarted: `sudo systemctl restart rsyslog`
- [ ] Log aggregator script deployed: `/usr/local/bin/log-aggregator.sh`
- [ ] Monitoring status script deployed: `/usr/local/bin/monitoring-status.sh`
- [ ] Scripts made executable: `chmod +x /usr/local/bin/*.sh`
- [ ] Report directory created: `/var/local/calendarbot-watchdog/reports/`
- [ ] Cache directory created: `/var/local/calendarbot-watchdog/cache/`

### Automation

- [ ] Cron jobs configured: `crontab -e`
- [ ] Daily report cron job added
- [ ] Weekly report cron job added
- [ ] Cleanup cron job added
- [ ] Monitoring status cron job added (optional)

### Remote Shipping (Optional)

- [ ] Log shipper script deployed: `/usr/local/bin/log-shipper.sh`
- [ ] Webhook URL and token obtained
- [ ] Environment variables configured: `/etc/environment`
- [ ] Webhook tested: `/usr/local/bin/log-shipper.sh test` succeeds
- [ ] Log shipper service created (if using systemd streaming)
- [ ] Log shipper service enabled and started

### Verification

- [ ] Logrotate test passes: `sudo logrotate -d /etc/logrotate.d/calendarbot-watchdog`
- [ ] rsyslog logs being written (if installed): `ls /var/log/calendarbot/`
- [ ] Daily report generates: `/usr/local/bin/log-aggregator.sh daily $(date +%Y-%m-%d)` succeeds
- [ ] Report file exists: `/var/local/calendarbot-watchdog/reports/daily_*.json`
- [ ] Report valid JSON: `cat /var/local/calendarbot-watchdog/reports/daily_*.json | jq`
- [ ] Monitoring status works: `/usr/local/bin/monitoring-status.sh health` returns status
- [ ] Cron jobs listed: `crontab -l` shows all jobs
- [ ] (Optional) Webhook shipping works: Check webhook endpoint received test event

---

## Installation Path Checklists

### Path A: Minimal (Kiosk Display Only)

Sections 1 + 2:

- [ ] All Section 1 items completed (including auto-login configuration)
- [ ] All Section 2 items completed
- [ ] Kiosk displays calendar on boot via auto-login + .bash_profile
- [ ] Watchdog monitors and recovers from failures
- [ ] No internet-facing services (port 8080 localhost only)

**Time**: ~90 minutes

---

### Path B: Full Deployment (Kiosk + Alexa)

Sections 1 + 2 + 3:

- [ ] All Section 1 items completed (including auto-login configuration)
- [ ] All Section 2 items completed
- [ ] All Section 3 items completed (HTTPS, Lambda, Alexa skill)
- [ ] Kiosk displays calendar on boot via auto-login
- [ ] Alexa skill works end-to-end: voice → AWS Lambda → HTTPS → CalendarBot
- [ ] Bearer token authentication working
- [ ] All 3 Alexa intents tested and working

**Time**: ~2.5-3 hours

---

### Path C: Production (Everything)

Sections 1 + 2 + 3 + 4:

- [ ] All Section 1 items completed
- [ ] All Section 2 items completed
- [ ] All Section 3 items completed
- [ ] All Section 4 items completed
- [ ] Kiosk displays calendar on boot via auto-login
- [ ] Alexa skill working end-to-end
- [ ] Monitoring and log rotation configured
- [ ] Health checks and reports working
- [ ] Monitoring dashboard available
- [ ] (Optional) Remote log shipping configured

**Time**: ~2.5 hours

---

## Post-Installation Verification

### System Health

```bash
# All services running
sudo systemctl status calendarbot-lite@bencan.service
sudo systemctl status calendarbot-kiosk-watchdog@bencan.service
sudo systemctl status caddy  # If Section 3
sudo systemctl status rsyslog  # If Section 4 with rsyslog

# No critical errors in logs (last hour)
sudo journalctl -u calendarbot-* --since "1 hour ago" | grep -i critical

# Disk space OK
df -h | grep -E "Filesystem|/var|/home"
# Should have > 1GB free

# Memory usage OK
free -h
# Should have > 100MB available
```

### Functional Tests

```bash
# CalendarBot API works
curl http://localhost:8080/api/whats-next

# Health endpoint healthy
curl http://localhost:8080/api/health | jq '.status'
# Should show: "ok"

# Browser heartbeat active
curl http://localhost:8080/api/health | jq '.display_probe.last_render_probe_iso'
# Should show recent timestamp (< 2 minutes old)

# (If Alexa) Remote endpoint works
curl -H "Authorization: Bearer YOUR_TOKEN" https://YOUR_DOMAIN/api/alexa/next-meeting

# (If logs) Monitoring status
/usr/local/bin/monitoring-status.sh health
```

### Auto-Start Tests

```bash
# Reboot and verify everything auto-starts
sudo reboot

# After reboot (wait 2-3 minutes), SSH back in and check:
sudo systemctl status calendarbot-*
ps aux | grep -E "Xorg|chromium"
curl http://localhost:8080/api/whats-next
```

---

## Maintenance Checklist

### Daily
- [ ] Check kiosk display shows current calendar
- [ ] Check no error messages on screen

### Weekly
- [ ] Review watchdog logs: `sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service --since "7 days ago" | grep ERROR`
- [ ] Check disk space: `df -h`
- [ ] Review monitoring status: `/usr/local/bin/monitoring-status.sh health`
- [ ] (If logs) Review weekly report: `cat /var/local/calendarbot-watchdog/reports/weekly_*.json | jq .summary`

### Monthly
- [ ] Update system packages: `sudo apt-get update && sudo apt-get upgrade -y`
- [ ] Rotate bearer token (if using Alexa)
- [ ] Review Caddy access logs for suspicious activity: `sudo grep "401" /var/log/caddy/access.log`
- [ ] Backup configuration files: `.env`, `monitor.yaml`, `Caddyfile`
- [ ] Check log rotation working: `ls -lh /var/log/calendarbot-watchdog/`

---

## Troubleshooting Quick Reference

### Service Won't Start
```bash
# Check logs
sudo journalctl -u <service-name> -n 50

# Check configuration
cat ~/calendarbot/.env
cat /etc/calendarbot-monitor/monitor.yaml

# Restart service
sudo systemctl restart <service-name>
```

### Kiosk Not Displaying
```bash
# Check X running
ps aux | grep Xorg

# Check browser running
ps aux | grep chromium

# Check .xinitrc logs
tail -f ~/kiosk/kiosk.log

# Check .bash_profile
cat ~/.bash_profile

# Check auto-login configuration
systemctl cat getty@tty1.service | grep autologin

# Restart by logging out and back in to tty1
# Or reboot
sudo reboot
```

### Watchdog Not Recovering
```bash
# Check watchdog state
cat /var/local/calendarbot-watchdog/state.json | jq

# Check sudo permissions
sudo -u bencan sudo -l

# Reset watchdog state
sudo systemctl stop calendarbot-kiosk-watchdog@bencan.service
# Reset state file (see Section 2)
sudo systemctl start calendarbot-kiosk-watchdog@bencan.service
```

### HTTPS Not Working
```bash
# Check DNS
nslookup YOUR_DOMAIN

# Check port forwarding
# Test from external network
curl -I http://YOUR_DOMAIN

# Check Caddy logs
sudo journalctl -u caddy -n 100

# Reload Caddy
sudo systemctl reload caddy
```

---

## Documentation Reference

- **[Installation Overview](INSTALLATION_OVERVIEW.md)** - Start here
- **[Section 1: Base Installation](1_BASE_INSTALL.md)** - Detailed instructions
- **[Section 2: Kiosk & Watchdog](2_KIOSK_WATCHDOG.md)** - Detailed instructions
- **[Section 3: Alexa Integration](3_ALEXA_INTEGRATION.md)** - Detailed instructions
- **[Section 4: Log Management](4_LOG_MANAGEMENT.md)** - Detailed instructions
- **[File Inventory](FILE_INVENTORY.md)** - Complete file reference

---

**Use this checklist alongside the detailed section guides for a successful deployment!**
