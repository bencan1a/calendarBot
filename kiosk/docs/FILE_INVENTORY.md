# CalendarBot Kiosk File Inventory

Complete reference of all files deployed across all installation sections.

**Last Updated**: 2025-11-03

---

## How to Use This Document

This inventory provides:
- **Source Path**: Location in repository
- **Deployment Destination**: Where file should be deployed
- **Section**: Which installation section deploys this file
- **Purpose**: What the file does
- **User Editable**: Whether you should customize this file
- **Deployment Command**: How to deploy the file

---

## Section 1: Base Installation Files

### Configuration Files

| Source Path | Destination | Purpose | Editable |
|-------------|-------------|---------|----------|
| `.env.example` | `~/calendarbot/.env` | Environment configuration | **YES** |

**Deployment:**
```bash
cp .env.example .env
nano .env  # Edit with your settings
```

---

### System Service Files

| Source Path | Destination | Purpose | Editable |
|-------------|-------------|---------|----------|
| N/A (created manually) | `/etc/systemd/system/calendarbot-lite@.service` | CalendarBot systemd service | Rarely |

**Deployment:**
```bash
sudo nano /etc/systemd/system/calendarbot-lite@.service
# Paste service configuration from Section 1
sudo systemctl daemon-reload
sudo systemctl enable calendarbot-lite@bencan.service
```

---

### Runtime Directories

| Path | Purpose | Owner | Permissions |
|------|---------|-------|-------------|
| `~/calendarbot/` | Repository clone | bencan:bencan | 755 |
| `~/calendarbot/venv/` | Python virtual environment | bencan:bencan | 755 |

**Creation:**
```bash
cd ~
git clone https://github.com/YOUR_USERNAME/calendarbot.git
cd calendarbot
python3 -m venv venv
```

---

## Section 2: Kiosk Mode & Watchdog Files

### X Session Configuration

| Source Path | Destination | Purpose | Editable |
|-------------|-------------|---------|----------|
| `kiosk/config/.xinitrc` | `~/.xinitrc` | X session initialization | YES |
| N/A (user creates) | `~/.bash_profile` | Auto-start X on console login | YES |

**Deployment:**
```bash
# .xinitrc
cp ~/calendarbot/kiosk/config/.xinitrc ~/.xinitrc
chmod +x ~/.xinitrc

# .bash_profile
nano ~/.bash_profile
# Add auto-startx code from Section 2, Step 11
```

---

### Watchdog Daemon

| Source Path | Destination | Purpose | Editable |
|-------------|-------------|---------|----------|
| `kiosk/config/calendarbot-watchdog` | `/usr/local/bin/calendarbot-watchdog` | Watchdog executable | NO |
| `kiosk/config/monitor.yaml` | `/etc/calendarbot-monitor/monitor.yaml` | Watchdog configuration | **YES** |

**Deployment:**
```bash
# Daemon
sudo cp kiosk/config/calendarbot-watchdog /usr/local/bin/
sudo chmod +x /usr/local/bin/calendarbot-watchdog

# Configuration
sudo mkdir -p /etc/calendarbot-monitor
sudo cp kiosk/config/monitor.yaml /etc/calendarbot-monitor/
```

---

### Watchdog Service Files

| Source Path | Destination | Purpose | Editable |
|-------------|-------------|---------|----------|
| `kiosk/service/calendarbot-kiosk-watchdog@.service` | `/etc/systemd/system/calendarbot-kiosk-watchdog@.service` | Watchdog systemd service | Rarely |
| N/A (created manually) | `/etc/sudoers.d/calendarbot-watchdog` | Sudo privileges | NO |

**Deployment:**
```bash
# Watchdog service
sudo cp kiosk/service/calendarbot-kiosk-watchdog@.service /etc/systemd/system/
sudo systemctl daemon-reload

# Sudoers
sudo tee /etc/sudoers.d/calendarbot-watchdog << 'EOF'
bencan ALL=NOPASSWD: /sbin/reboot
bencan ALL=NOPASSWD: /bin/systemctl restart calendarbot-lite@*.service
bencan ALL=NOPASSWD: /bin/systemctl status calendarbot-lite@*.service
EOF
sudo chmod 440 /etc/sudoers.d/calendarbot-watchdog
```

---

### Runtime Directories (Watchdog)

| Path | Purpose | Owner | Permissions |
|------|---------|-------|-------------|
| `/var/log/calendarbot-watchdog/` | Watchdog log files | bencan:bencan | 755 |
| `/var/local/calendarbot-watchdog/` | State and report files | bencan:bencan | 755 |
| `/var/local/calendarbot-watchdog/state.json` | Watchdog state | bencan:bencan | 644 |
| `/var/local/calendarbot-watchdog/reports/` | Aggregated reports | bencan:bencan | 755 |
| `/var/local/calendarbot-watchdog/cache/` | Status cache | bencan:bencan | 755 |
| `~/kiosk/` | Kiosk log directory | bencan:bencan | 755 |

**Creation:**
```bash
sudo mkdir -p /var/log/calendarbot-watchdog
sudo mkdir -p /var/local/calendarbot-watchdog/reports
sudo mkdir -p /var/local/calendarbot-watchdog/cache
sudo chown -R bencan:bencan /var/log/calendarbot-watchdog /var/local/calendarbot-watchdog
mkdir -p ~/kiosk
```

---

## Section 3: Alexa Integration Files

### Caddy Configuration

| Source Path | Destination | Purpose | Editable |
|-------------|-------------|---------|----------|
| `kiosk/config/enhanced_caddyfile` | `/etc/caddy/Caddyfile` | Caddy reverse proxy config | **YES** |

**Deployment:**
```bash
# Backup existing
sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.backup

# Deploy enhanced config
sudo cp kiosk/config/enhanced_caddyfile /etc/caddy/Caddyfile

# Edit with your domain
sudo nano /etc/caddy/Caddyfile

# Reload
sudo systemctl reload caddy
```

---

### Caddy Log Directory

| Path | Purpose | Owner | Permissions |
|------|---------|-------|-------------|
| `/var/log/caddy/` | Caddy access logs | caddy:caddy | 755 |

**Creation:**
```bash
sudo mkdir -p /var/log/caddy
sudo chown caddy:caddy /var/log/caddy
```

---

### Environment Configuration Update

| File | Changes | Purpose |
|------|---------|---------|
| `~/calendarbot/.env` | Add `CALENDARBOT_ALEXA_BEARER_TOKEN` | Bearer token for Alexa auth |

**Update:**
```bash
nano ~/calendarbot/.env
# Add: CALENDARBOT_ALEXA_BEARER_TOKEN=YOUR_TOKEN_HERE
sudo systemctl restart calendarbot-lite@bencan.service
```

---

### AWS Lambda Function

| Source Path | Destination | Purpose | Editable |
|-------------|-------------|---------|----------|
| `calendarbot_lite/alexa_skill_backend.py` | AWS Lambda: `calendarbot-alexa-skill` | Alexa intent handler | NO |

**Deployment:**
- Deploy via AWS Lambda console or AWS CLI
- See [Section 3: Alexa Integration](3_ALEXA_INTEGRATION.md) for detailed steps
- Configure environment variables: `CALENDARBOT_ENDPOINT`, `CALENDARBOT_BEARER_TOKEN`, `REQUEST_TIMEOUT`
- Set timeout to 10 seconds
- Copy Lambda ARN for Alexa skill configuration

---

### Alexa Skill Configuration

| Source Path | Destination | Purpose | Editable |
|-------------|-------------|---------|----------|
| `alexa/interaction_model.json` | Amazon Developer Console | Alexa skill interaction model | Rarely |

**Deployment:**
- Create skill in Amazon Developer Console: "Calendar Bot"
- Upload `interaction_model.json` to define intents and utterances
- Configure endpoint with Lambda ARN
- Enable for testing in Development mode
- See [Section 3: Alexa Integration](3_ALEXA_INTEGRATION.md) for detailed steps

**Skill Details:**
- Invocation Name: "calendar bot"
- Intents: GetNextMeetingIntent, GetTimeUntilNextMeetingIntent, GetDoneForDayIntent
- Backend: AWS Lambda function

---

## Section 4: Monitoring & Log Management Files

### Logrotate Configuration

| Source Path | Destination | Purpose | Editable |
|-------------|-------------|---------|----------|
| `kiosk/config/logrotate-calendarbot-watchdog` | `/etc/logrotate.d/calendarbot-watchdog` | Log rotation config | Rarely |

**Deployment:**
```bash
sudo cp kiosk/config/logrotate-calendarbot-watchdog /etc/logrotate.d/calendarbot-watchdog
```

---

### rsyslog Configuration (Optional)

| Source Path | Destination | Purpose | Editable |
|-------------|-------------|---------|----------|
| `kiosk/config/rsyslog-calendarbot.conf` | `/etc/rsyslog.d/50-calendarbot.conf` | Structured logging config | Rarely |

**Deployment:**
```bash
sudo mkdir -p /var/log/calendarbot
sudo chown syslog:adm /var/log/calendarbot
sudo cp kiosk/config/rsyslog-calendarbot.conf /etc/rsyslog.d/50-calendarbot.conf
sudo systemctl restart rsyslog
```

---

### Log Management Scripts

| Source Path | Destination | Purpose | Editable |
|-------------|-------------|---------|----------|
| `kiosk/scripts/log-aggregator.sh` | `/usr/local/bin/log-aggregator.sh` | Daily/weekly report generator | NO |
| `kiosk/scripts/monitoring-status.sh` | `/usr/local/bin/monitoring-status.sh` | Status dashboard generator | NO |
| `kiosk/scripts/log-shipper.sh` | `/usr/local/bin/log-shipper.sh` | Remote webhook shipping | NO |
| `kiosk/scripts/critical-event-filter.sh` | `/usr/local/bin/critical-event-filter.sh` | Event filtering (optional) | NO |

**Deployment:**
```bash
sudo cp kiosk/scripts/log-aggregator.sh /usr/local/bin/
sudo cp kiosk/scripts/monitoring-status.sh /usr/local/bin/
sudo cp kiosk/scripts/log-shipper.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/*.sh
```

---

### Log Shipper Service (Optional)

| Source Path | Destination | Purpose | Editable |
|-------------|-------------|---------|----------|
| N/A (created manually) | `/etc/systemd/system/calendarbot-log-shipper.service` | Log shipper systemd service | Rarely |
| N/A (system file) | `/etc/environment` | Webhook configuration | **YES** |

**Deployment:**
```bash
# Service
sudo nano /etc/systemd/system/calendarbot-log-shipper.service
# Paste service configuration from Section 4
sudo systemctl daemon-reload
sudo systemctl enable calendarbot-log-shipper.service

# Environment
sudo nano /etc/environment
# Add webhook configuration
```

---

### Log Directories

| Path | Purpose | Owner | Permissions |
|------|---------|-------|-------------|
| `/var/log/calendarbot/` | rsyslog structured logs | syslog:adm | 755 |
| `/var/log/calendarbot-watchdog/` | Watchdog daemon logs | bencan:bencan | 755 |
| `/var/local/calendarbot-watchdog/reports/` | Aggregated reports | bencan:bencan | 755 |
| `/var/local/calendarbot-watchdog/cache/` | Monitoring status cache | bencan:bencan | 755 |

**Creation:**
```bash
sudo mkdir -p /var/log/calendarbot /var/log/calendarbot-watchdog
sudo chown syslog:adm /var/log/calendarbot
sudo chown bencan:bencan /var/log/calendarbot-watchdog
sudo mkdir -p /var/local/calendarbot-watchdog/reports /var/local/calendarbot-watchdog/cache
sudo chown -R bencan:bencan /var/local/calendarbot-watchdog
```

---

## Additional Utility Scripts

### Port Cleanup

| Source Path | Destination | Purpose | Editable |
|-------------|-------------|---------|----------|
| `kiosk/scripts/cleanup-port.sh` | `~/calendarbot/kiosk/scripts/cleanup-port.sh` | Port conflict resolution | NO |

**Usage:**
```bash
~/calendarbot/kiosk/scripts/cleanup-port.sh 8080
```

---

## Auto-Generated Files

These files are created automatically by services during operation:

| Path | Created By | Purpose |
|------|------------|---------|
| `/var/local/calendarbot-watchdog/state.json` | Watchdog daemon | Recovery state tracking |
| `/var/log/calendarbot-watchdog/watchdog.log` | Watchdog daemon | Watchdog logs |
| `~/kiosk/kiosk.log` | .xinitrc | X session startup logs |
| `~/kiosk/browser-launch.log` | launch-browser.sh | Browser launch logs |
| `/var/log/caddy/access.log` | Caddy | HTTP access logs |
| `/var/local/calendarbot-watchdog/reports/daily_*.json` | log-aggregator.sh | Daily reports |
| `/var/local/calendarbot-watchdog/reports/weekly_*.json` | log-aggregator.sh | Weekly reports |

**Do not edit these files manually** - they are managed by the respective services.

---

## User Tasks (Crontab)

Add to user crontab via `crontab -e`:

```cron
# Daily report at 1 AM
0 1 * * * /usr/local/bin/log-aggregator.sh daily $(date +\%Y-\%m-\%d)

# Weekly report on Monday at 2 AM
0 2 * * 1 /usr/local/bin/log-aggregator.sh weekly $(date -d 'last monday' +\%Y-\%m-\%d)

# Cleanup old reports daily at 3 AM
0 3 * * * /usr/local/bin/log-aggregator.sh cleanup

# Update monitoring status every 5 minutes
*/5 * * * * /usr/local/bin/monitoring-status.sh status /var/www/html/calendarbot-status.json
```

---

## File Permissions Summary

### System Files (require sudo)

```bash
# Configuration files
sudo chmod 644 /etc/caddy/Caddyfile
sudo chmod 644 /etc/calendarbot-monitor/monitor.yaml
sudo chmod 644 /etc/logrotate.d/calendarbot-watchdog
sudo chmod 644 /etc/rsyslog.d/50-calendarbot.conf
sudo chmod 644 /etc/systemd/system/calendarbot-*.service
sudo chmod 440 /etc/sudoers.d/calendarbot-watchdog

# Executables
sudo chmod 755 /usr/local/bin/calendarbot-watchdog
sudo chmod 755 /usr/local/bin/*.sh
```

### User Files

```bash
# Configuration
chmod 600 ~/.env  # Contains secrets
chmod 755 ~/.xinitrc
chmod 644 ~/.bash_profile

# Scripts
chmod 755 ~/calendarbot/kiosk/scripts/*.sh

# Logs (auto-managed)
chmod 644 ~/kiosk/*.log
```

### Directory Permissions

```bash
# System directories
sudo chmod 755 /etc/calendarbot-monitor
sudo chmod 755 /var/log/calendarbot
sudo chmod 755 /var/log/calendarbot-watchdog
sudo chmod 755 /var/local/calendarbot-watchdog

# User directories
chmod 755 ~/calendarbot
chmod 755 ~/kiosk
```

---

## Quick Deployment Reference

### Section 1: Base Install
```bash
git clone https://github.com/YOUR_USERNAME/calendarbot.git ~/calendarbot
cd ~/calendarbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
# Create /etc/systemd/system/calendarbot-lite@.service
sudo systemctl enable --now calendarbot-lite@bencan.service
```

### Section 2: Kiosk & Watchdog
```bash
sudo apt-get install -y xserver-xorg xinit chromium-browser xdotool matchbox-window-manager
cp ~/calendarbot/kiosk/config/.xinitrc ~/.xinitrc
chmod +x ~/.xinitrc
# Configure auto-login and .bash_profile (see Section 2, Steps 10-11)
# Deploy watchdog manually (see Section 2, Steps 1-9)
sudo systemctl enable --now calendarbot-kiosk-watchdog@bencan.service
```

### Section 3: Alexa Integration
```bash
sudo apt install caddy
python3 -c "import secrets; print(secrets.token_urlsafe(32))"  # Generate token
nano ~/calendarbot/.env  # Add token
sudo cp ~/calendarbot/kiosk/config/enhanced_caddyfile /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile  # Edit domain
sudo systemctl reload caddy
```

### Section 4: Monitoring & Log Management
```bash
sudo cp ~/calendarbot/kiosk/config/logrotate-calendarbot-watchdog /etc/logrotate.d/
sudo cp ~/calendarbot/kiosk/scripts/*.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/*.sh
crontab -e  # Add cron jobs
```

---

## File Checklist by Section

### Section 1 Files
- [ ] `~/calendarbot/.env`
- [ ] `/etc/systemd/system/calendarbot-lite@.service`

### Section 2 Files
- [ ] `~/.xinitrc`
- [ ] `~/.bash_profile`
- [ ] `/usr/local/bin/calendarbot-watchdog`
- [ ] `/etc/calendarbot-monitor/monitor.yaml`
- [ ] `/etc/systemd/system/calendarbot-kiosk-watchdog@.service`
- [ ] `/etc/sudoers.d/calendarbot-watchdog`

### Section 3 Files
- [ ] `/etc/caddy/Caddyfile`
- [ ] `~/calendarbot/.env` (updated with bearer token)
- [ ] AWS Lambda function: `calendarbot-alexa-skill`
- [ ] Alexa skill: "Calendar Bot" (Amazon Developer Console)

### Section 4 Files
- [ ] `/etc/logrotate.d/calendarbot-watchdog`
- [ ] `/etc/rsyslog.d/50-calendarbot.conf` (optional)
- [ ] `/usr/local/bin/log-aggregator.sh`
- [ ] `/usr/local/bin/monitoring-status.sh`
- [ ] `/usr/local/bin/log-shipper.sh` (optional)
- [ ] `/etc/systemd/system/calendarbot-log-shipper.service` (optional)
- [ ] Crontab entries

---

**For deployment procedures, see the section guides:**
- [Section 1: Base Installation](1_BASE_INSTALL.md)
- [Section 2: Kiosk & Watchdog](2_KIOSK_WATCHDOG.md)
- [Section 3: Alexa Integration](3_ALEXA_INTEGRATION.md)
- [Section 4: Monitoring & Log Management](4_LOG_MANAGEMENT.md)

**Return to**: [Installation Overview](INSTALLATION_OVERVIEW.md)
