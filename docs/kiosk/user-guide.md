# CalendarBot Kiosk Mode - User Guide

**Complete end-user documentation for CalendarBot kiosk mode on Raspberry Pi Zero 2W**

## Table of Contents

- [Overview](#overview)
- [What is Kiosk Mode?](#what-is-kiosk-mode)
- [Hardware Requirements](#hardware-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Daily Operations](#daily-operations)
- [CLI Command Reference](#cli-command-reference)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)
- [Performance Optimization](#performance-optimization)
- [Security Considerations](#security-considerations)

## Overview

CalendarBot Kiosk Mode transforms your Raspberry Pi Zero 2W into a dedicated calendar display kiosk. The system automatically starts on boot, displays your calendar information in full-screen mode, and provides robust error recovery and monitoring.

### Key Features

- **🔄 Auto-Start**: Boots directly into calendar display
- **💾 Memory Optimized**: Designed for Pi Zero 2W's 512MB RAM constraint
- **🔧 Self-Healing**: Automatic crash recovery and restart
- **🌐 Network Resilient**: Handles connectivity issues gracefully
- **⚙️ Easy Configuration**: Interactive setup and CLI tools
- **📊 Health Monitoring**: Built-in system monitoring and logging
- **🛡️ Secure**: Hardened systemd services with resource limits

### Supported Hardware

- **Primary**: Raspberry Pi Zero 2W (512MB RAM)
- **Display**: 480x800 portrait displays (tested)
- **Network**: WiFi or Ethernet via USB adapter
- **Storage**: 16GB+ microSD card recommended

## What is Kiosk Mode?

Kiosk mode creates a locked-down, dedicated calendar display that:

1. **Boots automatically** into calendar view without user interaction
2. **Runs full-screen** without desktop environment distractions
3. **Recovers automatically** from crashes, network issues, or power cycles
4. **Optimizes resources** specifically for Pi Zero 2W constraints
5. **Provides monitoring** and logging for reliability

### How It Works

```
Boot → Network Wait → CalendarBot Web Server → Browser Launch → Calendar Display
  ↓                    ↓                        ↓                ↓
Systemd              Health Check             Process Monitor   Full Screen
Services             & Recovery               & Restart         Chromium
```

## Hardware Requirements

### Raspberry Pi Zero 2W Specifications

| Component | Requirement | Notes |
|-----------|-------------|-------|
| **CPU** | ARM Cortex-A53 quad-core 1GHz | Built-in to Pi Zero 2W |
| **RAM** | 512MB | Must be Pi Zero 2W (original Pi Zero has only 512MB) |
| **Storage** | 16GB+ microSD | Class 10 or better recommended |
| **Display** | HDMI or GPIO-connected | 480x800 portrait tested and optimized |
| **Power** | 5V/2.5A | Stable power supply critical for reliability |
| **Network** | WiFi or USB Ethernet | Required for calendar data updates |

### Recommended Displays

| Display Type | Resolution | Notes |
|--------------|------------|-------|
| **Small Touchscreen** | 480x800 portrait | Optimal size for calendar view |
| **HDMI Monitor** | 1920x1080 | Works but may be oversized |
| **GPIO LCD** | 320x240 - 800x480 | Compatible with modifications |

### Power Considerations

- **Stable Supply**: Use quality 5V/2.5A power adapter
- **Backup Power**: Consider UPS for mission-critical displays
- **Power Management**: System automatically handles power state transitions

## Installation

### Prerequisites

Before starting installation:

1. **Fresh Raspberry Pi OS**: Latest Raspberry Pi OS Lite or Desktop
2. **SSH Access**: For headless installation (recommended)
3. **Internet Connection**: Required for downloading dependencies
4. **Basic Linux Knowledge**: Helpful for troubleshooting

### Step-by-Step Installation

#### 1. System Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install git if not present
sudo apt install git -y

# Create dedicated user (optional but recommended)
sudo useradd -m -s /bin/bash calendarbot
sudo usermod -aG sudo calendarbot
```

#### 2. Download CalendarBot

```bash
# Clone repository
git clone https://github.com/your-org/calendarbot.git
cd calendarbot

# Verify installation script
ls -la scripts/kiosk/install-calendarbot-kiosk.sh
```

#### 3. Run Automated Installation

```bash
# Execute installation (will prompt for configuration)
sudo scripts/kiosk/install-calendarbot-kiosk.sh

# The script will:
# - Install system dependencies (Chromium, X11, etc.)
# - Create Python virtual environment
# - Install CalendarBot package
# - Configure systemd services
# - Set up boot configuration
# - Apply Pi Zero 2W optimizations
```

#### 4. Validate Installation

```bash
# Run comprehensive validation
sudo scripts/kiosk/validate-kiosk-installation.sh

# Check for any installation issues
journalctl -u calendarbot-kiosk.service --since "10 minutes ago"
```

#### 5. Initial Configuration

```bash
# Interactive setup wizard
./venv/bin/python -m calendarbot --kiosk-setup

# Configure calendar sources, display settings, etc.
```

#### 6. First Boot Test

```bash
# Reboot to test auto-start
sudo reboot

# After reboot, verify kiosk is running
systemctl status calendarbot-kiosk.service
```

### Installation Troubleshooting

#### Common Installation Issues

**❌ Permission Denied**
```bash
# Fix script permissions
chmod +x scripts/kiosk/install-calendarbot-kiosk.sh
sudo chmod +x scripts/kiosk/install-calendarbot-kiosk.sh
```

**❌ Package Installation Failed**
```bash
# Update package lists
sudo apt update

# Fix broken packages
sudo apt --fix-broken install

# Retry installation
sudo scripts/kiosk/install-calendarbot-kiosk.sh
```

**❌ Display Configuration Issues**
```bash
# Check display connection
tvservice -s

# Verify HDMI config
cat /boot/config.txt | grep hdmi

# Force HDMI output (add to /boot/config.txt)
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=82
```

## Configuration

### Configuration Files

CalendarBot kiosk uses several configuration files:

| File | Purpose | Location |
|------|---------|----------|
| **Main Config** | Calendar sources, general settings | `~/.config/calendarbot/config.yaml` |
| **Kiosk Config** | Display and browser settings | `~/.config/calendarbot/kiosk.yaml` |
| **System Config** | Boot and hardware settings | `/boot/config.txt` |

### Interactive Configuration

```bash
# Launch interactive setup wizard
./venv/bin/python -m calendarbot --kiosk-setup

# Guided configuration includes:
# - Calendar source URLs (Google Calendar, Outlook, ICS)
# - Display resolution and orientation
# - Refresh intervals
# - Memory and performance settings
# - Network and security options
```

### Manual Configuration

#### Calendar Sources (`~/.config/calendarbot/config.yaml`)

```yaml
calendars:
  - name: "Work Calendar"
    url: "https://calendar.google.com/calendar/ical/work@company.com/private-.../basic.ics"
    color: "#1f77b4"
    enabled: true
    
  - name: "Personal Calendar"  
    url: "https://outlook.live.com/owa/calendar/.../calendar.ics"
    color: "#ff7f0e"
    enabled: true

general:
  refresh_interval: 900  # 15 minutes
  timezone: "America/Los_Angeles"
  date_format: "%Y-%m-%d"
  time_format: "%H:%M"
```

#### Kiosk Display Settings (`~/.config/calendarbot/kiosk.yaml`)

```yaml
display:
  resolution: "800x480"
  orientation: "portrait"  # portrait, landscape
  fullscreen: true
  hide_cursor: true
  
browser:
  memory_limit_mb: 80      # Critical for Pi Zero 2W
  cache_size_mb: 20
  disable_web_security: false
  user_agent: "CalendarBot-Kiosk/1.0"
  
performance:
  cpu_quota: 80            # Percentage
  restart_on_memory_limit: true
  health_check_interval: 30  # seconds
  max_restart_attempts: 5
  
network:
  timeout: 30              # seconds
  retry_attempts: 3
  offline_mode: false
```

#### Hardware Optimization (`/boot/config.txt`)

```ini
# CalendarBot Kiosk Optimizations
# GPU Memory Split (added by installer)
gpu_mem=64

# HDMI Configuration
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=82             # 1920x1080 @ 60Hz

# Display rotation (if needed)
display_rotate=1         # 0=normal, 1=90°, 2=180°, 3=270°

# Overclock settings (optional, use with caution)
# arm_freq=1000
# gpu_freq=500
```

### Calendar Source Configuration

#### Google Calendar Setup

1. **Get ICS URL**:
   - Open Google Calendar → Settings → Calendar settings
   - Select your calendar → "Integrate calendar" 
   - Copy "Public URL in iCal format" (if sharing publicly)
   - Or use "Secret URL in iCal format" for private calendars

2. **Add to Configuration**:
```yaml
calendars:
  - name: "Google Work"
    url: "https://calendar.google.com/calendar/ical/your-email@gmail.com/private-.../basic.ics"
    color: "#4285f4"
    enabled: true
```

#### Outlook/Office 365 Setup

1. **Get ICS URL**:
   - Open Outlook → Calendar → Share → "Publish this calendar"
   - Choose permission level → Copy ICS link

2. **Add to Configuration**:
```yaml
calendars:
  - name: "Outlook Work"
    url: "https://outlook.live.com/owa/calendar/.../calendar.ics"
    color: "#0078d4"
    enabled: true
```

#### Other Calendar Services

Most calendar services provide ICS export URLs:

- **Apple iCloud**: Calendar → Public Calendar → Copy Link
- **CalDAV**: Use CalDAV URL with authentication
- **ICS Files**: Direct file URLs or local file paths

### Display Layouts

CalendarBot supports multiple display layouts optimized for different screen sizes:

#### Available Layouts

| Layout | Best For | Screen Size | Description |
|--------|----------|-------------|-------------|
| **whats-next-view** | Small displays | 480x800 | Simplified upcoming events |
| **daily-agenda** | Medium displays | 800x1280 | Full day schedule |
| **weekly-overview** | Large displays | 1920x1080 | Week-at-a-glance |
| **minimal** | Any size | Any | Clean, minimal interface |

#### Layout Configuration

```bash
# Set layout via CLI
./venv/bin/python -m calendarbot --kiosk-layout daily-agenda

# Or edit configuration directly
nano ~/.config/calendarbot/config.yaml
```

```yaml
display:
  layout: "whats-next-view"
  theme: "light"           # light, dark, auto
  show_weather: true       # if weather integration enabled
  show_time: true
  show_date: true
```

## Daily Operations

### System Status Monitoring

#### Check Kiosk Status

```bash
# Service status
systemctl status calendarbot-kiosk.service

# Quick health check
./venv/bin/python -m calendarbot --kiosk-status

# Detailed system info
./venv/bin/python -m calendarbot --kiosk-info
```

#### Monitor System Resources

```bash
# Memory usage (should stay under 400MB total)
free -h

# CPU usage
top -p $(pgrep -f calendarbot)

# Browser memory specifically  
ps aux | grep chromium | awk '{print $6}' | sort -n
```

#### View Logs

```bash
# Real-time logs
journalctl -u calendarbot-kiosk.service -f

# Recent logs (last hour)
journalctl -u calendarbot-kiosk.service --since "1 hour ago"

# Error logs only
journalctl -u calendarbot-kiosk.service -p err

# Logs since last boot
journalctl -u calendarbot-kiosk.service -b
```

### Regular Maintenance Tasks

#### Daily Checks (Automated)

The kiosk performs these checks automatically:

- **Health Monitoring**: Browser responsiveness every 30 seconds
- **Memory Monitoring**: Restart browser if memory limit exceeded
- **Network Monitoring**: Retry calendar updates on network issues
- **Crash Recovery**: Automatic restart with exponential backoff

#### Weekly Maintenance

```bash
# Update calendar data manually
./venv/bin/python -m calendarbot --refresh-calendars

# Clear browser cache
sudo systemctl stop calendarbot-kiosk.service
rm -rf /home/pi/.cache/chromium/*
sudo systemctl start calendarbot-kiosk.service

# Check log file sizes
du -h /var/log/journal/
sudo journalctl --vacuum-time=7d
```

#### Monthly Maintenance  

```bash
# System updates
sudo apt update && sudo apt upgrade -y

# CalendarBot updates
cd /home/pi/calendarbot
git pull
./venv/bin/pip install -e .
sudo systemctl restart calendarbot-kiosk.service

# Configuration backup
cp ~/.config/calendarbot/*.yaml /home/pi/backup/

# System cleanup
sudo apt autoremove
sudo apt autoclean
```

### Calendar Updates

#### Manual Refresh

```bash
# Force immediate calendar refresh
./venv/bin/python -m calendarbot --refresh-now

# Restart browser to reload display
sudo systemctl restart calendarbot-kiosk.service
```

#### Automatic Updates

Calendar data refreshes automatically based on configuration:

- **Default Interval**: Every 15 minutes
- **Configurable**: 5 minutes to 24 hours
- **Network Aware**: Retries on network issues
- **Efficient**: Only downloads changed data

#### Troubleshooting Calendar Updates

```bash
# Test calendar URL manually
curl -I "your-calendar-url-here"

# Check calendar parsing
./venv/bin/python -m calendarbot --test-calendar "calendar-url"

# View calendar update logs
journalctl -u calendarbot-kiosk.service | grep -i calendar
```

## CLI Command Reference

### Basic Commands

#### Service Management

```bash
# Start kiosk mode
./venv/bin/python -m calendarbot --kiosk

# Stop kiosk (run from SSH)
sudo systemctl stop calendarbot-kiosk.service

# Restart kiosk
sudo systemctl restart calendarbot-kiosk.service

# Check status
./venv/bin/python -m calendarbot --kiosk-status
```

#### Configuration Management

```bash
# Interactive setup wizard
./venv/bin/python -m calendarbot --kiosk-setup

# Show current configuration
./venv/bin/python -m calendarbot --show-config

# Validate configuration
./venv/bin/python -m calendarbot --validate-config

# Reset to defaults (with confirmation)
./venv/bin/python -m calendarbot --reset-config
```

#### Calendar Management

```bash
# List configured calendars
./venv/bin/python -m calendarbot --list-calendars

# Add new calendar
./venv/bin/python -m calendarbot --add-calendar \
  --name "New Calendar" \
  --url "https://example.com/calendar.ics" \
  --color "#ff0000"

# Remove calendar
./venv/bin/python -m calendarbot --remove-calendar "Calendar Name"

# Test calendar URL
./venv/bin/python -m calendarbot --test-calendar "https://example.com/calendar.ics"
```

### Advanced Commands

#### Debugging and Diagnostics

```bash
# Run in debug mode (detailed logging)
./venv/bin/python -m calendarbot --kiosk --debug

# System diagnostics
./venv/bin/python -m calendarbot --diagnose

# Performance profiling (development)
./venv/bin/python -m calendarbot --kiosk --profile

# Memory usage analysis
./venv/bin/python -m calendarbot --memory-report
```

#### Display and Layout

```bash
# Change display layout
./venv/bin/python -m calendarbot --kiosk-layout "daily-agenda"

# Test layout without kiosk mode
./venv/bin/python -m calendarbot --web --layout "whats-next-view"

# Screen resolution detection
./venv/bin/python -m calendarbot --detect-display

# Display calibration mode
./venv/bin/python -m calendarbot --calibrate-display
```

#### Network and Updates

```bash
# Force calendar refresh
./venv/bin/python -m calendarbot --refresh-calendars

# Network connectivity test
./venv/bin/python -m calendarbot --test-network

# Update check
./venv/bin/python -m calendarbot --check-updates

# Manual update (development)
./venv/bin/python -m calendarbot --update
```

### Command Line Options Reference

#### Global Options

| Option | Description | Example |
|--------|-------------|---------|
| `--config` | Custom config file path | `--config /custom/path/config.yaml` |
| `--verbose` | Verbose output | `--verbose` |
| `--quiet` | Minimal output | `--quiet` |
| `--debug` | Debug mode with detailed logging | `--debug` |
| `--dry-run` | Show what would be done without executing | `--dry-run` |

#### Kiosk Mode Options

| Option | Description | Example |
|--------|-------------|---------|
| `--kiosk` | Start in kiosk mode | `--kiosk` |
| `--kiosk-setup` | Interactive configuration | `--kiosk-setup` |
| `--kiosk-status` | Show kiosk status | `--kiosk-status` |
| `--kiosk-layout` | Set display layout | `--kiosk-layout "daily-agenda"` |
| `--kiosk-info` | System information | `--kiosk-info` |

#### Web Server Options

| Option | Description | Example |
|--------|-------------|---------|
| `--web` | Start web server (non-kiosk) | `--web` |
| `--port` | Web server port | `--port 8080` |
| `--host` | Web server host | `--host 0.0.0.0` |
| `--layout` | Web layout | `--layout "weekly-overview"` |

## Troubleshooting

### Common Issues and Solutions

#### ❌ Kiosk Won't Start on Boot

**Symptoms**: Black screen, no calendar display after boot

**Diagnostic Steps**:
```bash
# Check service status
systemctl status calendarbot-kiosk.service

# Check service logs
journalctl -u calendarbot-kiosk.service --since "10 minutes ago"

# Check dependency services
systemctl status calendarbot-kiosk-setup.service
systemctl status calendarbot-network-wait.service
```

**Solutions**:
```bash
# Restart service manually
sudo systemctl restart calendarbot-kiosk.service

# Check network connectivity
ping -c 3 google.com

# Verify X11 session
echo $DISPLAY
xdpyinfo

# Reinstall if needed
sudo scripts/kiosk/install-calendarbot-kiosk.sh
```

#### ❌ Browser Crashes or Memory Issues  

**Symptoms**: Blank screen, "Out of Memory" errors, frequent restarts

**Diagnostic Steps**:
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -10

# Check browser memory specifically
ps aux | grep chromium

# Check crash logs
journalctl -u calendarbot-kiosk.service | grep -i "crash\|memory\|killed"
```

**Solutions**:
```bash
# Reduce browser memory limit
nano ~/.config/calendarbot/kiosk.yaml
# Set browser.memory_limit_mb to 60 or lower

# Restart browser process
sudo systemctl restart calendarbot-kiosk.service

# Clear browser cache
sudo systemctl stop calendarbot-kiosk.service
rm -rf /home/pi/.cache/chromium/*
sudo systemctl start calendarbot-kiosk.service

# Check for memory leaks (development)
./venv/bin/python -m calendarbot --memory-report
```

#### ❌ Calendar Data Not Loading

**Symptoms**: Empty calendar, "No events" message, old data

**Diagnostic Steps**:
```bash
# Test calendar URLs manually
curl -I "your-calendar-url-here"

# Check calendar parsing
./venv/bin/python -m calendarbot --test-calendar "calendar-url"

# Check network connectivity
./venv/bin/python -m calendarbot --test-network

# View calendar update logs
journalctl -u calendarbot-kiosk.service | grep -i calendar
```

**Solutions**:
```bash
# Force calendar refresh
./venv/bin/python -m calendarbot --refresh-calendars

# Verify calendar configuration
./venv/bin/python -m calendarbot --show-config

# Re-add calendar with fresh URL
./venv/bin/python -m calendarbot --remove-calendar "Calendar Name"
./venv/bin/python -m calendarbot --add-calendar --name "Calendar" --url "new-url"

# Check for authentication issues
# Some calendar services require re-authentication periodically
```

#### ❌ Display Issues

**Symptoms**: Wrong resolution, rotated display, no display output

**Diagnostic Steps**:
```bash
# Check display connection
tvservice -s

# Verify HDMI configuration
cat /boot/config.txt | grep hdmi

# Check X11 configuration
cat /var/log/Xorg.0.log | grep -i error

# Test display manually
DISPLAY=:0 chromium-browser --version
```

**Solutions**:
```bash
# Force HDMI output (add to /boot/config.txt)
sudo nano /boot/config.txt
# Add: hdmi_force_hotplug=1

# Fix display rotation
sudo nano /boot/config.txt  
# Add: display_rotate=1  # (0=normal, 1=90°, 2=180°, 3=270°)

# Reset display configuration
sudo cp /boot/config.txt.backup /boot/config.txt
sudo reboot

# Reconfigure display
./venv/bin/python -m calendarbot --calibrate-display
```

#### ❌ Network Connectivity Issues

**Symptoms**: "Network unreachable", calendar updates failing

**Diagnostic Steps**:
```bash
# Test basic connectivity
ping -c 3 google.com

# Test DNS resolution
nslookup google.com

# Check WiFi connection
iwconfig
sudo iwlist scan | grep -i "your-network-name"

# Check network services
systemctl status networking
systemctl status wpa_supplicant
```

**Solutions**:
```bash
# Restart networking
sudo systemctl restart networking

# Reconfigure WiFi
sudo raspi-config  # Network Options → WiFi

# Check network configuration
cat /etc/wpa_supplicant/wpa_supplicant.conf

# Use ethernet if available
# Connect USB-to-Ethernet adapter

# Configure static IP if needed
sudo nano /etc/dhcpcd.conf
```

### Diagnostic Tools

#### Built-in Diagnostics

```bash
# Comprehensive system check
./venv/bin/python -m calendarbot --diagnose

# Output includes:
# - Hardware information
# - Service status
# - Memory usage
# - Network connectivity
# - Configuration validation
# - Calendar accessibility
# - Display configuration
```

#### Log Analysis

```bash
# Service logs with context
journalctl -u calendarbot-kiosk.service -f --output=short-iso

# Error logs only
journalctl -u calendarbot-kiosk.service -p err --since "1 day ago"

# Boot logs
journalctl -b | grep -i calendarbot

# System logs
dmesg | grep -i error
```

#### Performance Monitoring

```bash
# Real-time resource monitoring
htop

# Process tree
pstree -p $(pgrep -f calendarbot)

# Network connections
netstat -tulpn | grep python

# Disk usage
df -h
du -sh ~/.cache/chromium/
```

### Recovery Procedures

#### Service Recovery

```bash
# Restart individual services
sudo systemctl restart calendarbot-kiosk.service
sudo systemctl restart calendarbot-kiosk-setup.service

# Full service reset
sudo systemctl stop calendarbot-kiosk.service
sudo systemctl disable calendarbot-kiosk.service
sudo systemctl enable calendarbot-kiosk.service
sudo systemctl start calendarbot-kiosk.service
```

#### Configuration Recovery

```bash
# Backup current configuration
cp ~/.config/calendarbot/*.yaml ~/backup/

# Reset to defaults
./venv/bin/python -m calendarbot --reset-config

# Restore from backup
cp ~/backup/*.yaml ~/.config/calendarbot/

# Validate restored configuration
./venv/bin/python -m calendarbot --validate-config
```

#### System Recovery

```bash
# Complete kiosk reinstallation
sudo scripts/kiosk/uninstall-calendarbot-kiosk.sh
sudo scripts/kiosk/install-calendarbot-kiosk.sh

# Factory reset (preserves user data)
sudo apt install --reinstall raspberrypi-bootloader
sudo rpi-update

# Nuclear option - full OS reinstall
# Flash fresh Raspberry Pi OS and start over
```

## Maintenance

### Preventive Maintenance

#### Daily Automated Tasks

The system automatically performs:

- **Health checks** every 30 seconds
- **Memory monitoring** with automatic restart if needed
- **Network connectivity** tests before calendar updates
- **Process monitoring** with crash recovery
- **Log rotation** to prevent disk space issues

#### Weekly Manual Tasks

```bash
# 1. Check system status
systemctl status calendarbot-kiosk.service

# 2. Review logs for issues
journalctl -u calendarbot-kiosk.service --since "1 week ago" | grep -i error

# 3. Monitor memory usage trends
free -h
ps aux | grep chromium

# 4. Clear browser cache
sudo systemctl stop calendarbot-kiosk.service
rm -rf /home/pi/.cache/chromium/*
sudo systemctl start calendarbot-kiosk.service

# 5. Test calendar connectivity
./venv/bin/python -m calendarbot --test-network
./venv/bin/python -m calendarbot --refresh-calendars
```

#### Monthly System Updates

```bash
# 1. Update system packages
sudo apt update && sudo apt upgrade -y

# 2. Update CalendarBot
cd /home/pi/calendarbot
git pull
./venv/bin/pip install -e .

# 3. Restart services with new version
sudo systemctl restart calendarbot-kiosk.service

# 4. Verify operation
./venv/bin/python -m calendarbot --kiosk-status

# 5. Clean up old packages
sudo apt autoremove
sudo apt autoclean

# 6. Backup configuration
cp ~/.config/calendarbot/*.yaml ~/backup/$(date +%Y%m%d)/
```

### System Monitoring

#### Performance Metrics

Monitor these key metrics for optimal operation:

| Metric | Healthy Range | Action Required |
|--------|---------------|-----------------|
| **Total Memory** | < 400MB | Restart if > 450MB |
| **Browser Memory** | < 80MB | Reduce limit if consistently high |
| **CPU Usage** | < 80% | Check for background processes |
| **Disk Usage** | < 80% | Clean logs and cache |
| **Temperature** | < 65°C | Check cooling and ventilation |

#### Monitoring Commands

```bash
# Memory usage
free -h | awk 'NR==2{printf "Memory Usage: %s/%s (%.2f%%)\n", $3,$2,$3*100/$2}'

# CPU temperature  
vcgencmd measure_temp

# Disk usage
df -h | awk '$NF=="/"{printf "Disk Usage: %d/%dGB (%s)\n", $3,$2,$5}'

# Service uptime
systemctl show -p ActiveEnterTimestamp calendarbot-kiosk.service

# Network connectivity
ping -c 1 google.com > /dev/null && echo "Network: OK" || echo "Network: FAILED"
```

#### Alert Thresholds

Configure monitoring alerts for:

- **High Memory Usage**: > 90% of 512MB RAM
- **Service Failures**: > 3 restarts per hour
- **Network Issues**: > 5 consecutive failures
- **High Temperature**: > 70°C sustained
- **Disk Space**: > 90% full

### Backup and Recovery

#### Configuration Backup

```bash
# Create backup directory
mkdir -p ~/backup/calendarbot/$(date +%Y%m%d)

# Backup configuration files
cp ~/.config/calendarbot/*.yaml ~/backup/calendarbot/$(date +%Y%m%d)/

# Backup system configuration
sudo cp /boot/config.txt ~/backup/calendarbot/$(date +%Y%m%d)/boot_config.txt

# Create automated backup script
cat > ~/backup_calendarbot.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=~/backup/calendarbot/$(date +%Y%m%d)
mkdir -p "$BACKUP_DIR"
cp ~/.config/calendarbot/*.yaml "$BACKUP_DIR/"
sudo cp /boot/config.txt "$BACKUP_DIR/boot_config.txt"
echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x ~/backup_calendarbot.sh
```

#### Automated Backups

```bash
# Add to crontab for weekly backups
crontab -e

# Add this line for weekly Sunday backups at 2 AM:
0 2 * * 0 /home/pi/backup_calendarbot.sh

# Verify crontab
crontab -l
```

#### Recovery from Backup

```bash
# List available backups
ls -la ~/backup/calendarbot/

# Restore configuration
BACKUP_DATE="20240109"  # Replace with actual date
cp ~/backup/calendarbot/$BACKUP_DATE/*.yaml ~/.config/calendarbot/

# Restore boot configuration (if needed)
sudo cp ~/backup/calendarbot/$BACKUP_DATE/boot_config.txt /boot/config.txt

# Restart services
sudo systemctl restart calendarbot-kiosk.service
sudo reboot  # If boot config was restored
```

## Performance Optimization

### Pi Zero 2W Specific Optimizations

#### Memory Management

The Pi Zero 2W's 512MB RAM requires careful memory management:

```yaml
# ~/.config/calendarbot/kiosk.yaml
browser:
  memory_limit_mb: 80          # Browser process limit
  cache_size_mb: 20           # Browser cache limit
  max_tabs: 1                 # Single tab only
  disable_extensions: true    # No browser extensions
  disable_plugins: true       # No Flash, Java, etc.

performance:
  cpu_quota: 80               # 80% CPU limit
  restart_on_memory_limit: true
  memory_check_interval: 30   # Check every 30 seconds
```

#### System Optimizations

```bash
# GPU memory split (in /boot/config.txt)
gpu_mem=64                    # 64MB for GPU, 448MB for system

# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable cups
sudo systemctl disable avahi-daemon

# Optimize swappiness
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
```

#### Browser Optimizations

Chromium flags optimized for Pi Zero 2W:

```python
# Applied automatically by CalendarBot
CHROMIUM_FLAGS = [
    '--memory-pressure-off',
    '--max_old_space_size=64',     # 64MB V8 heap
    '--optimize-for-size',
    '--enable-low-end-device-mode',
    '--disable-background-timer-throttling',
    '--disable-dev-shm-usage',     # Use /tmp instead of /dev/shm
    '--no-sandbox',                # Required for embedded systems
    '--disable-gpu',               # Software rendering only
    '--disable-software-rasterizer',
    '--disable-background-networking',
    '--disable-default-apps',
    '--disable-sync',
    '--disable-translate',
    '--disable-extensions',
    '--disable-plugins',
    '--disable-java',
    '--disable-background-media',
    '--autoplay-policy=no-user-gesture-required'
]
```

### Network Optimization

#### Connection Management

```yaml
# ~/.config/calendarbot/config.yaml
network:
  timeout: 30                 # Connection timeout
  retry_attempts: 3           # Retry failed requests
  retry_delay: 5              # Seconds between retries
  connection_pool_size: 2     # Limit concurrent connections
  
calendars:
  refresh_interval: 900       # 15 minutes (balance freshness vs. load)
  cache_duration: 3600        # 1 hour cache
  parallel_updates: false     # Sequential updates only
```

#### Bandwidth Optimization

```bash
# Limit bandwidth usage (if needed)
sudo apt install wondershaper

# Limit to 1 Mbps up/down (adjust as needed)
sudo wondershaper wlan0 1024 1024

# Remove limits
sudo wondershaper clear wlan0
```

### Display Performance

#### Resolution Optimization

For optimal performance, choose appropriate display resolution:

| Display Type | Recommended Resolution | Performance Impact |
|--------------|----------------------|-------------------|
| **Small LCD** | 480x320 | Minimal |
| **Medium LCD** | 800x480 | Low |
| **Large Display** | 1920x1080 | High (may cause lag) |

#### Rendering Optimization

```yaml
# ~/.config/calendarbot/kiosk.yaml
display:
  hardware_acceleration: false    # Software rendering only
  vsync: false                   # Disable vertical sync
  frame_rate_limit: 30           # Limit to 30 FPS
  
browser:
  disable_animations: true       # Disable CSS animations
  disable_transitions: true      # Disable CSS transitions
  force_color_profile: 'srgb'    # Standard color profile
```

### Storage Optimization

#### Cache Management

```bash
# Limit browser cache size
du -sh ~/.cache/chromium/

# Clear cache regularly (automated)
cat > /usr/local/bin/clear-calendarbot-cache.sh << 'EOF'
#!/bin/bash
if systemctl is-active --quiet calendarbot-kiosk.service; then
    sudo systemctl stop calendarbot-kiosk.service
    rm -rf /home/pi/.cache/chromium/*
    sudo systemctl start calendarbot-kiosk.service
    logger "CalendarBot cache cleared"
fi
EOF

chmod +x /usr/local/bin/clear-calendarbot-cache.sh

# Add to crontab for daily cache clearing
echo "0 3 * * * /usr/local/bin/clear-calendarbot-cache.sh" | crontab -
```

#### Log Management

```bash
# Configure log rotation
sudo nano /etc/systemd/journald.conf

# Set limits:
SystemMaxUse=100M
SystemMaxFileSize=10M
SystemMaxFiles=10
```

## Security Considerations

### System Security

#### Service Hardening

The kiosk systemd service includes security hardening:

```ini
# /etc/systemd/system/calendarbot-kiosk.service
[Service]
# Security hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/home/pi/.config /home/pi/.cache /tmp
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictRealtime=yes
RestrictSUIDSGID=yes

# Resource limits
MemoryMax=400M
CPUQuota=80%
TasksMax=50
```

#### Network Security

```bash
# Firewall configuration (optional)
sudo ufw enable
sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw allow out 80        # HTTP for calendar updates
sudo ufw allow out 443       # HTTPS for calendar updates
sudo ufw allow out 53        # DNS

# Disable unnecessary network services
sudo systemctl disable cups
sudo systemctl disable avahi-daemon
sudo systemctl disable bluetooth
```

#### User Security

```bash
# Create dedicated user (if not already done)
sudo useradd -m -s /bin/bash calendarbot

# Limit sudo access
echo "calendarbot ALL=(ALL) NOPASSWD: /bin/systemctl restart calendarbot-kiosk.service" | sudo tee /etc/sudoers.d/calendarbot

# Secure file permissions
chmod 600 ~/.config/calendarbot/*.yaml
chown -R calendarbot:calendarbot ~/.config/calendarbot/
```

### Calendar Security

#### Authentication

For private calendars, ensure secure authentication:

```yaml
# ~/.config/calendarbot/config.yaml
calendars:
  - name: "Secure Calendar"
    url: "https://calendar.example.com/secure/calendar.ics"
    auth:
      type: "basic"             # basic, oauth, token
      username: "username"
      password: "password"      # Store securely
    ssl_verify: true            # Always verify SSL certificates
```

#### Credential Storage

```bash
# Use environment variables for sensitive data
export CALENDAR_PASSWORD="your-password"

# Or use dedicated secrets file
echo "CALENDAR_PASSWORD=your-password" > ~/.calendar_secrets
chmod 600 ~/.calendar_secrets

# Source in service file
# Environment=CALENDAR_PASSWORD_FILE=/home/pi/.calendar_secrets
```

#### URL Security

- **Use HTTPS**: Always use HTTPS URLs for calendar sources
- **Private URLs**: Use calendar service's private/secret URLs when available
- **Rotate URLs**: Regenerate calendar URLs periodically
- **Monitor Access**: Check calendar service access logs for unauthorized access

### Physical Security

#### Kiosk Protection

```bash
# Disable local login
sudo systemctl disable getty@tty1

# Hide boot messages
sudo nano /boot/cmdline.txt
# Add: quiet splash

# Disable keyboard shortcuts in browser
# (handled automatically by kiosk mode)

# Lock down configuration files
sudo chattr +i /boot/config.txt    # Make immutable
```

#### Remote Access

```bash
# Secure SSH configuration
sudo nano /etc/ssh/sshd_config

# Recommended settings:
PermitRootLogin no
PasswordAuthentication no      # Use key-based auth only
AllowUsers calendarbot         # Limit to specific users
ClientAliveInterval 300        # Disconnect idle sessions
```

### Privacy Considerations

#### Data Handling

- **Local Processing**: Calendar data processed locally, not sent to external services
- **Cache Security**: Browser cache contains calendar data - secure appropriately
- **Log Privacy**: Logs may contain calendar event titles - rotate regularly
- **Network Traffic**: Calendar updates occur over encrypted connections

#### Compliance

For organizations with specific compliance requirements:

- **GDPR**: Ensure calendar data handling complies with data protection regulations
- **HIPAA**: Additional security measures may be required for healthcare environments
- **Corporate**: Follow organizational IT security policies and procedures

---

This completes the comprehensive User Guide for CalendarBot Kiosk Mode. The guide covers all aspects of installation, configuration, operation, and maintenance for end-users deploying the system on Raspberry Pi Zero 2W devices.