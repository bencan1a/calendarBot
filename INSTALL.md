# Installation Guide

This guide provides step-by-step instructions for installing the Microsoft 365 Calendar Display Bot on your Raspberry Pi.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Raspberry Pi OS Setup](#raspberry-pi-os-setup)
- [Python Environment Setup](#python-environment-setup)
- [Azure App Registration](#azure-app-registration)
- [Application Installation](#application-installation)
- [Initial Configuration](#initial-configuration)
- [First Run and Authentication](#first-run-and-authentication)
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

### Account Requirements

- **Microsoft 365 account** with calendar access
- **Azure subscription** (free tier sufficient for app registration)

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

## Azure App Registration

### 1. Access Azure Portal

1. Go to [Azure Portal](https://portal.azure.com/)
2. Sign in with your Microsoft account
3. Navigate to **Azure Active Directory** → **App registrations**

### 2. Create New App Registration

1. **Click "New registration"**

2. **Configure the application**:
   - **Name**: `CalendarBot` (or your preferred name)
   - **Supported account types**: 
     - Select "Accounts in any organizational directory and personal Microsoft accounts"
   - **Redirect URI**: Leave blank (not needed for device flow)

3. **Click "Register"**

### 3. Configure Application Settings

1. **Copy Application (client) ID**:
   - On the app overview page, copy the **Application (client) ID**
   - Save this value - you'll need it for configuration

2. **Configure Authentication**:
   - Go to **Authentication** in the left menu
   - Under **Advanced settings**, set:
     - **Allow public client flows**: Yes
   - Click **Save**

3. **Set API Permissions** (Optional verification):
   - Go to **API permissions** in the left menu
   - Verify **Microsoft Graph** → **Calendars.Read** permission exists
   - If not present, click **Add a permission** → **Microsoft Graph** → **Delegated permissions**
   - Search for and select **Calendars.Read**
   - Click **Add permissions**

### 4. Record Configuration Details

Save the following information for application configuration:
- **Application (client) ID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Directory (tenant) ID**: Use `common` for personal accounts

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
pip list | grep -E "(msal|aiohttp|pydantic|cryptography)"
```

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
# Edit configuration with your Azure client ID
nano config/config.yaml
```

**Required configuration**:
```yaml
# Microsoft Graph API Configuration
client_id: "your-azure-app-client-id"  # Replace with your client ID
tenant_id: "common"  # Use 'common' for personal Microsoft accounts

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
echo 'export CALENDARBOT_CLIENT_ID="your-azure-app-client-id"' >> ~/.bashrc
echo 'export CALENDARBOT_TENANT_ID="common"' >> ~/.bashrc
echo 'export CALENDARBOT_LOG_LEVEL="INFO"' >> ~/.bashrc

# Reload bash configuration
source ~/.bashrc

# Verify environment variables
echo $CALENDARBOT_CLIENT_ID
```

### 4. Create Required Directories

The application will create these automatically, but you can verify:

```bash
# Check that directories will be created in expected locations
ls -la ~/.config/
ls -la ~/.local/share/
ls -la ~/.cache/
```

## First Run and Authentication

### 1. Run the Application

```bash
# Start the application
python main.py
```

### 2. Complete Authentication

On first run, you'll see:
```
===============================================================
🔐 MICROSOFT 365 AUTHENTICATION REQUIRED
===============================================================

To access your calendar, please complete authentication:

1. Visit: https://microsoft.com/devicelogin
2. Enter code: A1B2C3D4

Waiting for authentication...

===============================================================
```

### 3. Authentication Steps

1. **Open web browser** on any device (computer, phone, tablet)
2. **Navigate to**: https://microsoft.com/devicelogin
3. **Enter the device code** displayed in the terminal
4. **Sign in** with your Microsoft 365 account
5. **Grant permissions** when prompted
6. **Return to terminal** - authentication should complete automatically

### 4. Successful Authentication

You should see:
```
Authentication successful!
Calendar Bot initialized
Starting Calendar Bot...
Initializing Calendar Bot components...
Token refreshed successfully
Calendar Bot initialization completed successfully
Starting refresh scheduler (interval: 300s)
Successfully fetched and cached 3 events
```

## Verification

### 1. Check Application Output

The application should display your calendar:

```
============================================================
📅 MICROSOFT 365 CALENDAR - Monday, January 15
============================================================
Updated: 10:05 | 🌐 Live Data

📋 NEXT UP

• Team Standup
  10:00 - 10:30 | 📍 Conference Room A

• Project Review
  11:00 - 12:00 | 💻 Online

============================================================
```

### 2. Verify File Structure

Check that configuration and cache files were created:

```bash
# Configuration directory
ls -la ~/.config/calendarbot/
# Should show: config.yaml, tokens.enc, device_key.bin

# Data directory
ls -la ~/.local/share/calendarbot/
# Should show: calendar_cache.db

# Cache directory (may be empty initially)
ls -la ~/.cache/calendarbot/
```

### 3. Test Stop and Restart

```bash
# Stop the application with Ctrl+C
^C

# Restart the application
python main.py
```

The application should start without requiring re-authentication.

### 4. Check Logs

```bash
# If you enabled file logging, check log file
tail -f ~/calendarbot.log

# Or check system logs
journalctl -f | grep calendarbot
```

## Troubleshooting

### Authentication Issues

**Problem**: "Invalid client" error
```bash
# Verify client ID is correct
grep client_id config/config.yaml

# Check Azure app registration settings
# - Ensure "Allow public client flows" is enabled
# - Verify application is not expired
```

**Problem**: Permission denied errors
```bash
# Check file permissions
ls -la ~/.config/calendarbot/
sudo chown -R $USER:$USER ~/.config/calendarbot/
chmod 600 ~/.config/calendarbot/tokens.enc
```

**Problem**: Token refresh failures
```bash
# Clear stored tokens and re-authenticate
rm ~/.config/calendarbot/tokens.enc
python main.py
```

### Network Issues

**Problem**: DNS resolution failures
```bash
# Test DNS resolution
nslookup graph.microsoft.com
nslookup login.microsoftonline.com

# Check network connectivity
ping -c 4 8.8.8.8
```

**Problem**: Firewall blocking connections
```bash
# Test HTTPS connectivity
curl -I https://graph.microsoft.com/v1.0/

# If blocked, configure firewall to allow HTTPS outbound
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
sudo apt install -y libssl-dev libffi-dev python3-dev

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

### Getting Help

If you encounter issues not covered here:

1. **Check logs**: Enable debug logging by setting `log_level: "DEBUG"` in config
2. **Verify prerequisites**: Ensure all system requirements are met
3. **Test minimal configuration**: Try with default settings first
4. **Check GitHub issues**: Search for similar problems
5. **Create detailed issue**: Include logs, system info, and exact error messages

### Next Steps

After successful installation:
- Read [USAGE.md](USAGE.md) for day-to-day operation guidance
- See [DEPLOY.md](DEPLOY.md) for production deployment with systemd
- Review [DEVELOPMENT.md](DEVELOPMENT.md) if you want to contribute

---

**Installation complete!** Your Microsoft 365 Calendar Display Bot is now ready for use.