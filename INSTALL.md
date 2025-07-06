# Installation Guide

**Document Version:** 3.0
**Last Updated:** January 7, 2025
**System Version:** Calendar Bot v1.0.0 with Automated Setup
**Migration:** For users upgrading from Graph API v1.0, see [MIGRATION.md](MIGRATION.md)

This guide provides both the **new automated installation process** and detailed manual instructions for installing Calendar Bot.

## 🚀 Quick Start: Automated Installation (Recommended)

Calendar Bot now features a **complete automated setup system** that transforms the installation experience from 20+ manual steps to just 2 simple commands:

### The New Way - 2 Commands Only

```bash
# Step 1: Install Calendar Bot with automated setup
pip install calendarbot

# Step 2: Run the interactive configuration wizard
calendarbot --setup
```

**That's it!** The automated system handles:
- ✅ Directory creation and permissions
- ✅ Service-specific configuration templates
- ✅ Real-time URL validation and connection testing
- ✅ Authentication setup with guided prompts
- ✅ Complete YAML configuration generation
- ✅ First-run validation and testing

### What You Get

The automated installation provides:

- **Interactive Setup Wizard** with templates for Outlook, Google Calendar, iCloud, and CalDAV
- **Real-time Validation** that tests your calendar connection before saving
- **Professional CLI Experience** with clear guidance and error handling
- **Cross-platform Support** (Linux, macOS, Windows)
- **Intelligent First-run Detection** with automatic guidance
- **Built-in Backup/Restore** for configuration management

### Ready to Use Immediately

After the 2-command setup, Calendar Bot is immediately ready:

```bash
# Test your setup
calendarbot --test-mode

# Start interactive mode
calendarbot --interactive

# Launch web interface
calendarbot --web

# Raspberry Pi e-ink mode
calendarbot --rpi --web
```

**📖 For the complete automated setup experience, see [SETUP.md](SETUP.md)**

---

## 📋 Manual Installation (Alternative)

If you prefer manual installation or need custom configuration, the following sections provide detailed step-by-step instructions.

## Table of Contents

- [Quick Start: Automated Installation](#-quick-start-automated-installation-recommended)
- [Manual Installation](#-manual-installation-alternative)
- [Prerequisites](#prerequisites)
- [Raspberry Pi OS Setup](#raspberry-pi-os-setup)
- [Python Environment Setup](#python-environment-setup)
- [ICS Calendar Setup](#ics-calendar-setup)
- [Application Installation](#application-installation)
- [Initial Configuration](#initial-configuration)
- [First Run and Validation](#first-run-and-validation)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Hardware Requirements

- **Raspberry Pi Zero 2 W** or newer (recommended for optimal performance)
- **MicroSD card** (16GB minimum, Class 10 recommended)
- **Power supply** (5V 2.5A USB-C for Pi 4, micro-USB for older models)
- **Network connectivity** (WiFi or Ethernet)
- **Optional**: E-ink display HAT (for future phases)

### Software Requirements

- **Raspberry Pi OS Lite** (latest version)
- **Python 3.8+** (included in recent Raspberry Pi OS)
- **pip package manager** (included with Python)
- **Git** (for cloning the repository)

### Calendar Requirements

- **ICS calendar feed URL** from any calendar service:
  - Microsoft Outlook/Office 365
  - Google Calendar
  - Apple iCloud Calendar
  - CalDAV servers
  - Any calendar that exports ICS format

## Raspberry Pi OS Setup

### 1. Flash Raspberry Pi OS

1. **Download Raspberry Pi Imager** from [rpi.org](https://www.raspberrypi.org/software/)

2. **Flash the OS**:
   - Insert microSD card into your computer
   - Open Raspberry Pi Imager
   - Choose **Raspberry Pi OS Lite (64-bit)** for headless operation
   - Select your microSD card
   - Click the gear icon for advanced options

3. **Configure advanced options**:
   ```
   ✓ Enable SSH
   ✓ Set username and password
   ✓ Configure WiFi (SSID and password)
   ✓ Set locale settings (timezone, keyboard layout)
   ```

4. **Flash the image** and wait for completion

### 2. First Boot Setup

1. **Insert SD card** into Raspberry Pi and power on

2. **Find Pi IP address**:
   ```bash
   # On your computer, scan for the Pi
   nmap -sn 192.168.1.0/24
   # Or check your router's admin panel
   ```

3. **SSH into the Pi**:
   ```bash
   ssh pi@<raspberry-pi-ip>
   # Enter the password you set during imaging
   ```

### 3. System Updates

```bash
# Update package lists
sudo apt update

# Upgrade all packages
sudo apt upgrade -y

# Install essential packages
sudo apt install -y git curl wget vim htop

# Reboot to ensure all updates are applied
sudo reboot
```

### 4. Configure System Settings

```bash
# Run Raspberry Pi configuration tool
sudo raspi-config
```

**Recommended settings**:
- **Interface Options** → **SPI**: Enable (for future e-ink display)
- **Advanced Options** → **Memory Split**: Set to 16MB (minimal GPU memory)
- **Advanced Options** → **Expand Filesystem**: Ensure full SD card usage

```bash
# Reboot after configuration changes
sudo reboot
```

## Python Environment Setup

### 1. Verify Python Installation

```bash
# Check Python version (should be 3.8 or higher)
python3 --version

# Check pip version
pip3 --version

# If pip is missing, install it
sudo apt install -y python3-pip
```

### 2. Install Python Development Tools

```bash
# Install development packages
sudo apt install -y python3-dev python3-venv python3-setuptools

# Install system dependencies for Python packages
sudo apt install -y build-essential libssl-dev libffi-dev
```

### 3. Create Virtual Environment (Recommended)

```bash
# Create project directory
mkdir -p ~/projects
cd ~/projects

# Create virtual environment
python3 -m venv calendarbot-env

# Activate virtual environment
source calendarbot-env/bin/activate

# Upgrade pip in virtual environment
pip install --upgrade pip
```

## ICS Calendar Setup

### 1. Microsoft Outlook/Office 365

1. **Go to Outlook on the web** (outlook.live.com or outlook.office365.com)
2. **Navigate to Calendar**
3. **Click Settings** (gear icon) → **View all Outlook settings**
4. **Go to Calendar** → **Shared calendars**
5. **Under "Publish a calendar"**:
   - Select your calendar
   - Set permissions to "Can view when I'm busy" (minimal access)
   - Click **Publish**
6. **Copy the ICS link** (ends with `.ics`)

### 2. Google Calendar

1. **Open Google Calendar** (calendar.google.com)
2. **Click on the three dots** next to your calendar name
3. **Select "Settings and sharing"**
4. **Scroll to "Access permissions and export"**
5. **Copy the "Secret address in iCal format"** (ends with `.ics`)

### 3. Apple iCloud Calendar

1. **Go to iCloud.com** and sign in
2. **Open Calendar**
3. **Click the share icon** next to your calendar
4. **Enable "Public Calendar"**
5. **Copy the calendar URL** (ends with `.ics`)

### 4. CalDAV Servers

For CalDAV servers (Nextcloud, Radicale, etc.):
```
https://your-server.com/remote.php/dav/calendars/username/calendar-name/?export
```

### 5. Authentication Requirements

**Public Feeds**: Most personal calendar exports are public and require no authentication.

**Protected Feeds**: Some organizational calendars may require authentication:
- **Basic Auth**: Username and password
- **Bearer Token**: API token or app password
- **Custom Headers**: Additional authentication headers

## Application Installation

### 1. Clone the Repository

```bash
# Ensure you're in the project directory
cd ~/projects

# Clone the repository
git clone <repository-url> calendarBot
cd calendarBot

# If using virtual environment, activate it
source ../calendarbot-env/bin/activate
```

### 2. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Verify installation
pip list | grep -E "(icalendar|httpx|pydantic|aiosqlite)"
```

Expected packages:
- `icalendar>=5.0.0` - ICS parsing
- `httpx>=0.25.0` - HTTP client
- `aiosqlite>=0.19.0` - SQLite async support
- `pydantic>=2.0.0` - Data validation
- `PyYAML>=6.0` - Configuration files

### 3. Verify Installation

```bash
# Check project structure
ls -la

# Verify main module can be imported
python3 -c "import calendarbot; print('Installation successful')"
```

## Initial Configuration

### 1. Copy Example Configuration

```bash
# Copy example configuration file
cp config/config.yaml.example config/config.yaml
```

### 2. Edit Configuration File

```bash
# Edit configuration with your ICS URL
nano config/config.yaml
```

**Required configuration**:
```yaml
# ICS Calendar Configuration
ics:
  url: "your-ics-calendar-url"  # Replace with your ICS URL
  auth_type: "none"  # Change to "basic" or "bearer" if authentication required
  
  # For Basic Authentication (uncomment if needed)
  # username: "your-username"
  # password: "your-password"
  
  # For Bearer Token Authentication (uncomment if needed)
  # token: "your-bearer-token"
  
  # SSL Settings
  verify_ssl: true

# Application Settings (defaults are usually fine)
refresh_interval: 300  # 5 minutes
cache_ttl: 3600       # 1 hour
log_level: "INFO"

# Display Settings
display_enabled: true
display_type: "console"

# Network Settings
request_timeout: 30
max_retries: 3
retry_backoff_factor: 1.5
```

### 3. Alternative: Environment Variables

Instead of editing the config file, you can set environment variables:

```bash
# Add to ~/.bashrc for persistence
echo 'export CALENDARBOT_ICS_URL="your-ics-calendar-url"' >> ~/.bashrc
echo 'export CALENDARBOT_ICS_AUTH_TYPE="none"' >> ~/.bashrc
echo 'export CALENDARBOT_LOG_LEVEL="INFO"' >> ~/.bashrc

# For authentication (if required)
echo 'export CALENDARBOT_ICS_USERNAME="username"' >> ~/.bashrc
echo 'export CALENDARBOT_ICS_PASSWORD="password"' >> ~/.bashrc

# Reload bash configuration
source ~/.bashrc

# Verify environment variables
echo $CALENDARBOT_ICS_URL
```

### 4. Test Configuration

```bash
# Test configuration syntax
python3 -c "from config.settings import settings; print('Config valid')"

# Test ICS URL accessibility
python test_ics.py --url "$CALENDARBOT_ICS_URL"
```

## First Run and Validation

### 1. Test ICS Feed Access

```bash
# Test your ICS URL
python test_ics.py --url "your-ics-url"
```

Expected output:
```
✅ ICS Feed Validation Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📡 Connection Test
   ✅ Successfully connected to ICS feed
   ✅ Received 200 OK response
   ✅ Content-Type: text/calendar

📄 ICS Content Validation
   ✅ Valid ICS format detected
   ✅ Found 5 calendar events
   ✅ Date range: 2024-01-15 to 2024-01-22

📅 Calendar Information
   - Calendar Name: My Calendar
   - Product ID: Microsoft Exchange Server 2010
   - Version: 2.0
```

### 2. Test with Authentication (if required)

```bash
# For Basic Authentication
python test_ics.py --url "your-ics-url" --auth-type basic --username "user" --password "pass"

# For Bearer Token
python test_ics.py --url "your-ics-url" --auth-type bearer --token "your-token"
```

### 3. Run the Application

```bash
# Start the application
python main.py
```

### 4. Successful First Run

You should see:
```
Calendar Bot initialized
Starting Calendar Bot...
Initializing Calendar Bot components...
Calendar Bot initialization completed successfully
Starting refresh scheduler (interval: 300s)
Successfully fetched and cached 3 events from ICS source
```

Followed by your calendar display:
```
============================================================
📅 ICS CALENDAR - Monday, January 15
============================================================
Updated: 10:05 | 🌐 Live Data

📋 NEXT UP

• Team Standup
  10:00 - 10:30 | 📍 Conference Room A

• Project Review
  11:00 - 12:00 | 💻 Online

============================================================
```

## Verification

### 1. Check Application Output

The application should display your calendar events in a clean format with:
- Current date in the header
- Live data indicator (🌐)
- Events with times and locations
- Automatic refresh every 5 minutes

### 2. Verify File Structure

Check that configuration and cache files were created:

```bash
# Configuration directory
ls -la ~/.config/calendarbot/
# Should show: No files (configuration is in project directory)

# Data directory
ls -la ~/.local/share/calendarbot/
# Should show: calendar_cache.db

# Cache directory
ls -la ~/.cache/calendarbot/
# Should show: ics_cache.json (if HTTP caching enabled)
```

### 3. Test Stop and Restart

```bash
# Stop the application with Ctrl+C
^C

# Restart the application
python main.py
```

The application should start quickly and show cached data immediately, then refresh with live data.

### 4. Test Interactive Mode

```bash
# Try interactive navigation
python main.py --interactive
```

Use arrow keys to navigate between dates, Space to return to today, ESC to exit.

### 5. Check Logs

```bash
# If you enabled file logging, check log file
tail -f calendarbot.log

# Or check recent output
python main.py --test-mode --verbose
```

## Troubleshooting

### ICS Feed Issues

**Problem**: "Cannot connect to ICS feed"
```bash
# Test URL manually
curl -I "your-ics-url"

# Check if authentication is required
python test_ics.py --url "your-ics-url" --verbose
```

**Problem**: "Invalid ICS format" error
```bash
# Download and examine ICS content
curl "your-ics-url" | head -20

# Should start with: BEGIN:VCALENDAR
# Should contain: VERSION:2.0
# Should have: BEGIN:VEVENT entries
```

**Problem**: HTTP 401/403 errors
```bash
# Test with authentication
python test_ics.py --url "your-url" --auth-type basic --username "user" --password "pass"

# Check if URL requires special headers
curl -H "User-Agent: CalendarBot/1.0" "your-ics-url"
```

### Authentication Issues

**Problem**: Basic auth not working
```bash
# Verify credentials
echo -n "username:password" | base64
# Compare with Authorization header expected by server
```

**Problem**: Bearer token rejected
```bash
# Test token format
curl -H "Authorization: Bearer your-token" "your-ics-url"
```

### Network Issues

**Problem**: DNS resolution failures
```bash
# Test DNS resolution
nslookup your-calendar-server.com

# Check network connectivity
ping -c 4 8.8.8.8
```

**Problem**: SSL certificate errors
```yaml
# Temporarily disable SSL verification in config.yaml
ics:
  verify_ssl: false
```

**Problem**: Firewall blocking connections
```bash
# Test HTTPS connectivity
curl -I https://your-calendar-server.com

# Check if specific ports are blocked
telnet your-calendar-server.com 443
```

### Python/Dependencies Issues

**Problem**: Module import errors
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Check Python path
python3 -c "import sys; print(sys.path)"

# Verify virtual environment activation
which python
which pip
```

**Problem**: Cryptography compilation errors
```bash
# Install additional build dependencies
sudo apt install -y libssl-dev libffi-dev python3-dev rust

# Upgrade pip and setuptools
pip install --upgrade pip setuptools wheel

# Reinstall cryptography
pip install --force-reinstall cryptography
```

### Performance Issues

**Problem**: High CPU or memory usage
```bash
# Monitor resource usage
htop

# Check for multiple instances
ps aux | grep python

# Adjust refresh interval if needed
# Edit config.yaml: refresh_interval: 600  # 10 minutes
```

**Problem**: Slow startup or updates
```bash
# Test ICS feed response time
time curl -s "your-ics-url" > /dev/null

# Check database performance
ls -la ~/.local/share/calendarbot/
# If calendar_cache.db is very large, clear it:
# rm ~/.local/share/calendarbot/calendar_cache.db
```

### Configuration Issues

**Problem**: "ICS URL configuration is required" error
```bash
# Verify configuration
grep -A 5 "ics:" config/config.yaml

# Or check environment variable
echo $CALENDARBOT_ICS_URL
```

**Problem**: YAML syntax errors
```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('config/config.yaml'))"
```

### Getting Help

If you encounter issues not covered here:

1. **Run test mode**: `python main.py --test-mode --verbose`
2. **Check ICS feed directly**: `python test_ics.py --url "your-url" --verbose`
3. **Enable debug logging**: Set `log_level: "DEBUG"` in config
4. **Verify prerequisites**: Ensure all system requirements are met
5. **Test minimal configuration**: Try with just URL and no authentication
6. **Check GitHub issues**: Search for similar problems
7. **Create detailed issue**: Include logs, ICS URL (redacted), and exact error messages

### Next Steps

After successful installation:

#### Immediate Actions
1. **Verify operation**: Leave the application running for 10-15 minutes to ensure stable operation
2. **Check your calendar**: Compare displayed events with your calendar application
3. **Test interactive mode**: Try `python main.py --interactive` for navigation
4. **Monitor performance**: Check CPU and memory usage with `htop`

#### Documentation to Review
- **[USAGE.md](USAGE.md)**: Day-to-day operation and troubleshooting
- **[INTERACTIVE_NAVIGATION.md](INTERACTIVE_NAVIGATION.md)**: Interactive mode features
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Technical details and system design
- **[MIGRATION.md](MIGRATION.md)**: If you upgraded from Graph API v1.x

#### Optional Enhancements
- **Systemd service**: Set up automatic startup (see deployment guides)
- **Log rotation**: Configure log management for long-term operation
- **Backup automation**: Schedule configuration and cache backups
- **Multiple calendars**: Plan for additional ICS feeds (future feature)

### Installation Verification Checklist

- [ ] **System requirements met**: Raspberry Pi with Python 3.8+
- [ ] **ICS URL obtained**: Calendar feed URL copied and tested
- [ ] **Dependencies installed**: All Python packages installed successfully
- [ ] **Configuration created**: `config/config.yaml` file created and edited
- [ ] **ICS connectivity tested**: `python test_ics.py` completed successfully
- [ ] **Application started**: `python main.py` runs without errors
- [ ] **Events displayed**: Calendar events showing correctly
- [ ] **Status indicators correct**: Shows "🌐 Live Data" with recent timestamps
- [ ] **Interactive mode works**: Navigation with arrow keys functions
- [ ] **Graceful shutdown**: Ctrl+C stops application cleanly

### Performance Baseline

After installation, your system should achieve:

| Metric | Expected Value | How to Check |
|--------|----------------|--------------|
| **Memory Usage** | < 100MB RAM | `htop` or `ps aux \| grep python` |
| **CPU Usage** | < 5% average, < 20% during refresh | `htop` during operation |
| **Startup Time** | < 10 seconds to first display | Time from start to calendar output |
| **Refresh Time** | < 5 seconds per cycle | Watch console output during updates |
| **Cache Size** | < 5MB typical | `ls -lh ~/.local/share/calendarbot/` |

### Common Post-Installation Tasks

#### Enable Automatic Startup
```bash
# Create systemd service (optional)
sudo nano /etc/systemd/system/calendarbot.service

# Add service configuration:
[Unit]
Description=ICS Calendar Display Bot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/projects/calendarBot
ExecStart=/home/pi/projects/calendarbot-env/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable and start service
sudo systemctl enable calendarbot.service
sudo systemctl start calendarbot.service
```

#### Set Up Log Rotation
```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/calendarbot

# Add rotation rules:
/home/pi/projects/calendarBot/calendarbot.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 644 pi pi
}
```

#### Create Backup Script
```bash
# Simple backup script
cat > ~/backup-calendarbot.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf ~/calendarbot-backup-$DATE.tar.gz \
    ~/projects/calendarBot/config/config.yaml \
    ~/.local/share/calendarbot/
echo "Backup created: calendarbot-backup-$DATE.tar.gz"
EOF

chmod +x ~/backup-calendarbot.sh
```

---

**🎉 Installation Complete!** Your ICS Calendar Display Bot is now ready for production use.

**📖 What's Next?** Read the **[User Guide](USAGE.md)** to learn about daily operation and advanced features.

---

*Installation Guide v2.0 - Last updated January 5, 2025*
*For technical support, see [GitHub Issues](https://github.com/your-repo/calendarBot/issues)*