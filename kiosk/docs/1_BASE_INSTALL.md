# Section 1: Base CalendarBot_Lite Installation

Install the core CalendarBot_Lite server with systemd service management.

**Estimated Time**: 30-45 minutes
**Prerequisites**: Fresh Raspbian/Debian installation with SSH access

---

## What You'll Install

By the end of this section, you'll have:

- ✅ Python 3 virtual environment
- ✅ CalendarBot_Lite server running on port 8080
- ✅ systemd service for automatic startup on boot
- ✅ Environment configuration for calendar sync
- ✅ Basic API functionality verified

**Services Added**: 1 (`calendarbot-lite@bencan.service`)

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Raspberry Pi Zero 2 W / Pi 3 / Pi 4 with Raspbian/Debian 11+
- [ ] SSH access configured
- [ ] User account created (examples use `bencan`)
- [ ] Internet connectivity active
- [ ] ICS calendar URL available (Office 365, Google Calendar, etc.)
- [ ] At least 2GB free disk space

---

## Step 1: Install System Dependencies

Update system and install required packages:

```bash
# Update package lists
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3 and development tools
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential

# Install Git for repository cloning
sudo apt-get install -y git

# Install utilities
sudo apt-get install -y \
    curl \
    jq \
    htop
```

**Verify Python version:**
```bash
python3 --version
# Should show: Python 3.9.x or later
```

**Why these packages?**
- `python3-venv` - Create isolated Python environments
- `python3-dev`, `build-essential` - Compile Python packages with C extensions
- `git` - Clone the CalendarBot repository
- `curl`, `jq` - HTTP testing and JSON processing

---

## Step 2: Clone CalendarBot Repository

Clone the repository to your user's home directory:

```bash
# Navigate to home directory
cd ~

# Clone repository
git clone https://github.com/YOUR_USERNAME/calendarBot.git

# Navigate to repository
cd calendarBot
```

**Alternative: Clone specific branch**
```bash
# Clone a specific branch or tag
git clone -b <branch-name> https://github.com/YOUR_USERNAME/calendarBot.git
```

**Verify clone:**
```bash
ls -la ~/calendarBot
# Should show: calendarbot_lite/, kiosk/, docs/, etc.
```

---

## Step 3: Create Python Virtual Environment

Create an isolated Python environment for CalendarBot:

```bash
# From ~/calendarBot directory
cd ~/calendarBot

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify activation (prompt should show "(venv)")
which python
# Should show: /home/bencan/calendarBot/venv/bin/python

# Upgrade pip to latest version
pip install --upgrade pip
```

**Important**: Always activate the virtual environment before running CalendarBot commands:
```bash
source ~/calendarBot/venv/bin/activate
```

**Add to .bashrc for convenience (optional):**
```bash
echo 'alias cbenv="source ~/calendarBot/venv/bin/activate"' >> ~/.bashrc
source ~/.bashrc

# Now you can use: cbenv
```

---

## Step 4: Install Python Dependencies

Install all required Python packages:

```bash
# Ensure virtual environment is activated
source ~/calendarBot/venv/bin/activate

# Install from requirements.txt
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed aiohttp-3.x httpx-0.x icalendar-5.x python-dateutil-2.x ...
```

**Key dependencies installed:**
- `aiohttp` - Async HTTP web server
- `httpx` - HTTP client with connection pooling
- `icalendar` - ICS calendar parsing
- `python-dateutil` - Date/time utilities
- `PyYAML` - Configuration parsing (for watchdog in Section 2)

**Verify installation:**
```bash
pip list | grep -E "aiohttp|httpx|icalendar"
```

**Troubleshooting: Installation Fails**

If you see compilation errors:
```bash
# Install missing development packages
sudo apt-get install -y python3-dev libffi-dev libssl-dev

# Retry installation
pip install -r requirements.txt
```

---

## Step 5: Configure Environment (.env file)

Create configuration file from template:

```bash
# Copy example environment file
cd ~/calendarBot
cp .env.example .env

# Edit configuration
nano .env
```

### Required Configuration

**Minimum required settings:**

```bash
# === REQUIRED ===
# Your ICS calendar feed URL
CALENDARBOT_ICS_URL=https://outlook.office365.com/owa/calendar/XXXXXXXX@yourdomain.com/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX/calendar.ics

# === SERVER SETTINGS (defaults shown) ===
# Bind to all network interfaces (0.0.0.0) or localhost (127.0.0.1)
CALENDARBOT_WEB_HOST=0.0.0.0

# Server port
CALENDARBOT_WEB_PORT=8080

# === REFRESH SETTINGS ===
# How often to refresh calendar (seconds)
# 300 = 5 minutes (recommended for production)
# 60 = 1 minute (useful for testing)
CALENDARBOT_REFRESH_INTERVAL=300

# === LOGGING ===
# Enable debug logging (set to false for production)
CALENDARBOT_DEBUG=false

# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
CALENDARBOT_LOG_LEVEL=INFO

# === SYSTEMD DEPLOYMENT ===
# Automatically cleanup port conflicts without prompting
# (set to true for systemd service)
CALENDARBOT_NONINTERACTIVE=true
```

### Optional Configuration

**Alexa Integration** (configure in Section 3):
```bash
# Bearer token for Alexa skill authentication
# Generate in Section 3: python -c "import secrets; print(secrets.token_urlsafe(32))"
CALENDARBOT_ALEXA_BEARER_TOKEN=
```

### Getting Your ICS Calendar URL

**Office 365 / Outlook.com:**
1. Open Outlook Web App (https://outlook.office365.com)
2. Click Settings (gear icon) → View all Outlook settings
3. Calendar → Shared calendars → Publish a calendar
4. Select your calendar → ICS → Copy the ICS URL

**Google Calendar:**
1. Open Google Calendar (https://calendar.google.com)
2. Click Settings → Settings for my calendars
3. Select your calendar → Integrate calendar
4. Copy "Secret address in iCal format"

**Verify ICS URL works:**
```bash
# Test URL (replace with your URL)
curl -s "YOUR_ICS_URL" | head -n 20
# Should show: BEGIN:VCALENDAR
```

---

## Step 6: Test Server Manually

Before creating a service, test the server runs correctly:

```bash
# Activate virtual environment
source ~/calendarBot/venv/bin/activate

# Run server in foreground
python -m calendarbot_lite
```

**Expected output:**
```
INFO:calendarbot:Loading configuration from environment...
INFO:calendarbot:Server starting on http://0.0.0.0:8080
INFO:calendarbot:Performing initial calendar refresh...
INFO:calendarbot:Loaded 25 events from calendar sources
INFO:calendarbot:Background tasks started
INFO:calendarbot:Server ready and listening
```

**If you see errors:**
- Check `.env` file has valid `CALENDARBOT_ICS_URL`
- Verify ICS URL is accessible: `curl -I YOUR_ICS_URL`
- Check port 8080 is not in use: `sudo ss -tlnp | grep 8080`

**Test from another terminal (or another machine on your network):**

```bash
# From Pi (localhost)
curl http://localhost:8080/api/whats-next

# From another machine (replace <PI_IP> with your Pi's IP address)
curl http://<PI_IP>:8080/api/whats-next
```

**Expected response:**
```json
{
  "status": "ok",
  "event": {
    "summary": "Team Meeting",
    "start_time": "2025-11-03T14:00:00-05:00",
    "end_time": "2025-11-03T15:00:00-05:00",
    "location": "Conference Room A",
    "is_all_day": false
  },
  "time_until_seconds": 3600,
  "time_until_human": "in 1 hour"
}
```

**Test other endpoints:**

```bash
# Health check
curl http://localhost:8080/health

# Web interface (open in browser)
# http://<PI_IP>:8080/whatsnext.html
```

**Stop the server**: Press `Ctrl+C`

---

## Step 7: Create systemd Service

Deploy the CalendarBot systemd service for automatic startup and management:

```bash
# Copy the service file from the repository
sudo cp ~/calendarBot/kiosk/service/calendarbot-kiosk.service \
  /etc/systemd/system/calendarbot-lite@.service
```

**What this service file does:**
- `%i` placeholder is replaced with username (e.g., `bencan`)
- Runs as the specified user (not root)
- Auto-restarts on failure with 5-second delay
- Limits memory to 300MB max (protects Pi Zero 2)
- Logs to systemd journal

**Note**: The service is installed as `calendarbot-lite@.service` (template service with @) which allows running it for specific users like `calendarbot-lite@bencan.service`.

---

## Step 8: Enable and Start Service

Deploy and start the systemd service:

```bash
# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service (start on boot) for user 'bencan'
sudo systemctl enable calendarbot-lite@bencan.service

# Start service now
sudo systemctl start calendarbot-lite@bencan.service

# Check status
sudo systemctl status calendarbot-lite@bencan.service
```

**Expected status output:**
```
● calendarbot-lite@bencan.service - CalendarBot Lite Calendar Display Server for bencan
     Loaded: loaded (/etc/systemd/system/calendarbot-lite@.service; enabled)
     Active: active (running) since Mon 2025-11-03 10:00:00 EST; 5s ago
   Main PID: 12345 (python)
      Tasks: 3 (limit: 512)
     Memory: 45.2M
     CGroup: /system.slice/system-calendarbot\x2dlite.slice/calendarbot-lite@bencan.service
             └─12345 /home/bencan/calendarBot/venv/bin/python -m calendarbot_lite
```

**Key indicators of success:**
- `Active: active (running)` (not "failed" or "inactive")
- Memory usage reasonable (< 100MB initially)
- No error messages in the log excerpt

---

## Step 9: Verify Service Operation

Check that the service is working correctly:

### Check Service Status

```bash
# Full status
sudo systemctl status calendarbot-lite@bencan.service

# Is service running?
sudo systemctl is-active calendarbot-lite@bencan.service
# Should output: active
```

### View Logs

```bash
# View recent logs
sudo journalctl -u calendarbot-lite@bencan.service -n 50

# Follow logs in real-time
sudo journalctl -u calendarbot-lite@bencan.service -f

# Filter for errors only
sudo journalctl -u calendarbot-lite@bencan.service | grep -i error
```

**Healthy logs should show:**
```
INFO:calendarbot:Server starting on http://0.0.0.0:8080
INFO:calendarbot:Loaded 25 events from calendar sources
INFO:calendarbot:Background tasks started
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8080/health

# Next meeting
curl http://localhost:8080/api/whats-next

# Browser heartbeat (for Section 2)
curl -X POST http://localhost:8080/api/browser-heartbeat
```

### Test from Web Browser

Open in a web browser on your network:
```
http://<PI_IP>:8080/whatsnext.html
```

You should see the calendar display page with your next meeting.

---

## Step 10: Configure Service Management

Learn how to manage the service:

### Start/Stop/Restart

```bash
# Stop service
sudo systemctl stop calendarbot-lite@bencan.service

# Start service
sudo systemctl start calendarbot-lite@bencan.service

# Restart service (after config changes)
sudo systemctl restart calendarbot-lite@bencan.service

# Reload service (graceful reload)
sudo systemctl reload-or-restart calendarbot-lite@bencan.service
```

### Enable/Disable Auto-Start

```bash
# Enable (start on boot)
sudo systemctl enable calendarbot-lite@bencan.service

# Disable (don't start on boot)
sudo systemctl disable calendarbot-lite@bencan.service

# Check if enabled
sudo systemctl is-enabled calendarbot-lite@bencan.service
```

### After Updating Code

```bash
# Pull latest changes
cd ~/calendarBot
git pull

# Activate virtual environment
source venv/bin/activate

# Update dependencies (if requirements.txt changed)
pip install -r requirements.txt

# Restart service
sudo systemctl restart calendarbot-lite@bencan.service

# Check status
sudo systemctl status calendarbot-lite@bencan.service
```

### After Changing .env Configuration

```bash
# Edit .env file
nano ~/calendarBot/.env

# Restart service to reload configuration
sudo systemctl restart calendarbot-lite@bencan.service

# Verify changes took effect
sudo journalctl -u calendarbot-lite@bencan.service -n 20
```

---

## Step 11: Configure Auto-Login (Optional - For Kiosk Mode)

If you plan to use kiosk mode (Section 2), configure the Pi to automatically log in as your user on boot. This allows the `.bash_profile` to automatically start the X session.

**Note**: Skip this step if you only need the server (no kiosk display).

```bash
# Configure auto-login using raspi-config
sudo raspi-config
```

**In raspi-config:**
1. Navigate to: **System Options** → **Boot / Auto Login**
2. Select: **Console Autologin** (text console, automatically logged in as your user)
3. Select **Finish**
4. Reboot when prompted (or reboot later)

**Alternative method (manual configuration)**:

```bash
# Create autologin service override
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d

# Create override configuration
sudo tee /etc/systemd/system/getty@tty1.service.d/autologin.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin bencan --noclear %I \$TERM
EOF

# Reload systemd
sudo systemctl daemon-reload
```

**Verification:**
```bash
# Check auto-login is configured
systemctl cat getty@tty1.service | grep -A2 ExecStart

# Should show: --autologin bencan
```

**Security Note**: Auto-login reduces security as anyone with physical access can access the system. Only use on dedicated kiosk devices in secure locations.

---

## Verification Checklist

Before proceeding to Section 2, verify all items:

**Installation:**
- [ ] System packages installed (python3, git, etc.)
- [ ] Repository cloned to `~/calendarBot`
- [ ] Virtual environment created at `~/calendarBot/venv`
- [ ] Python dependencies installed without errors
- [ ] `.env` file exists with valid ICS URL

**Service:**
- [ ] systemd service file created at `/etc/systemd/system/calendarbot-lite@.service`
- [ ] Service enabled: `sudo systemctl is-enabled calendarbot-lite@bencan.service` returns `enabled`
- [ ] Service active: `sudo systemctl is-active calendarbot-lite@bencan.service` returns `active`
- [ ] No errors in logs: `sudo journalctl -u calendarbot-lite@bencan.service | grep -i error`

**Functionality:**
- [ ] API endpoint responds: `curl http://localhost:8080/api/whats-next` returns JSON
- [ ] Health endpoint healthy: `curl http://localhost:8080/health` returns `{"status":"ok",...}`
- [ ] Web interface loads: `http://<PI_IP>:8080/whatsnext.html` shows calendar
- [ ] Calendar data refreshing: Logs show periodic "Loaded X events" messages

**Network:**
- [ ] Server accessible from other machines on your network
- [ ] Firewall rules don't block port 8080 (if applicable)

---

## Files Deployed

Summary of files created or modified in this section:

| File Path | Purpose | User Editable |
|-----------|---------|---------------|
| `~/calendarBot/` | Repository clone | No (via git) |
| `~/calendarBot/venv/` | Python virtual environment | No |
| `~/calendarBot/.env` | Environment configuration | **Yes** |
| `/etc/systemd/system/calendarbot-lite@.service` | systemd service | Rarely |

---

## Troubleshooting

### Issue: Service fails to start

**Check logs:**
```bash
sudo journalctl -u calendarbot-lite@bencan.service -n 50
```

**Common causes:**

1. **Missing or invalid .env file**
   ```bash
   # Check file exists
   ls -la ~/calendarBot/.env

   # Verify ICS URL is set
   grep CALENDARBOT_ICS_URL ~/calendarBot/.env
   ```

2. **Port 8080 already in use**
   ```bash
   # Check what's using port 8080
   sudo ss -tlnp | grep 8080

   # Kill process if needed
   sudo fuser -k 8080/tcp

   # Restart service
   sudo systemctl restart calendarbot-lite@bencan.service
   ```

3. **Virtual environment missing or broken**
   ```bash
   # Recreate virtual environment
   cd ~/calendarBot
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   # Restart service
   sudo systemctl restart calendarbot-lite@bencan.service
   ```

4. **Python dependency errors**
   ```bash
   # Check for missing packages
   source ~/calendarBot/venv/bin/activate
   python -c "import aiohttp, httpx, icalendar"

   # Reinstall if errors
   pip install -r requirements.txt --force-reinstall
   ```

### Issue: Can't access server from other machines

**Check server is listening:**
```bash
sudo ss -tlnp | grep 8080
# Should show: 0.0.0.0:8080 (not 127.0.0.1:8080)
```

**If showing 127.0.0.1:8080:**
```bash
# Edit .env to bind to all interfaces
nano ~/calendarBot/.env
# Set: CALENDARBOT_WEB_HOST=0.0.0.0

# Restart service
sudo systemctl restart calendarbot-lite@bencan.service
```

**Check firewall (if using ufw):**
```bash
sudo ufw status
# If active, allow port 8080:
sudo ufw allow 8080/tcp
```

### Issue: Calendar not refreshing

**Check logs for refresh errors:**
```bash
sudo journalctl -u calendarbot-lite@bencan.service | grep -i refresh
```

**Test ICS URL manually:**
```bash
curl -I "YOUR_ICS_URL"
# Should return: HTTP/1.1 200 OK
```

**Common causes:**
- ICS URL expired or revoked
- Network connectivity issues
- Calendar service authentication changed

**Force refresh by restarting:**
```bash
sudo systemctl restart calendarbot-lite@bencan.service
```

### Issue: High memory usage

**Check current memory:**
```bash
# Service memory
systemctl status calendarbot-lite@bencan.service | grep Memory

# System memory
free -h
```

**If memory high (>200MB):**
```bash
# Increase refresh interval to reduce load
nano ~/calendarBot/.env
# Set: CALENDARBOT_REFRESH_INTERVAL=600  # 10 minutes

# Restart service
sudo systemctl restart calendarbot-lite@bencan.service
```

### Issue: Service won't restart after reboot

**Check if enabled:**
```bash
sudo systemctl is-enabled calendarbot-lite@bencan.service
# Should return: enabled
```

**If disabled:**
```bash
sudo systemctl enable calendarbot-lite@bencan.service
```

**Check for dependency issues:**
```bash
# View service dependencies
systemctl list-dependencies calendarbot-lite@bencan.service

# Ensure network is available before service starts
# (Service file should have After=network-online.target)
```

---

## Performance Notes (Pi Zero 2)

Expected resource usage on Raspberry Pi Zero 2 W:

- **Memory**: 50-100MB RSS (depends on calendar size)
- **CPU**: 2-5% average (spikes during refresh)
- **Disk I/O**: Minimal (no database writes)
- **Network**: Periodic bursts during calendar refresh

**Optimization tips:**
- Increase `CALENDARBOT_REFRESH_INTERVAL` to reduce CPU/network load
- Use `CALENDARBOT_DEBUG=false` in production (reduces log volume)
- Limit calendar to events within reasonable window (reduce parsing load)

---

## Next Steps

**Section 1 Complete!** ✅

You now have a working CalendarBot_Lite server with:
- API endpoints accessible at `http://<PI_IP>:8080`
- Automatic startup on boot
- systemd management and monitoring
- Calendar sync from your ICS feed

**Choose your next section:**

- **[Section 2: Kiosk Mode & Watchdog →](2_KIOSK_WATCHDOG.md)** - Add automatic browser display and recovery
- **[Section 3: Alexa Integration →](3_ALEXA_INTEGRATION.md)** - Add HTTPS and Alexa access (requires Section 1 only)
- **[Section 4: Log Management →](4_LOG_MANAGEMENT.md)** - Add log rotation and monitoring (requires Section 1 only)

**Or return to**: [Installation Overview](INSTALLATION_OVERVIEW.md)
