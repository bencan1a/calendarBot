# Deployment Guide

This guide covers production deployment of the Microsoft 365 Calendar Display Bot on Raspberry Pi, including systemd service setup, process monitoring, and maintenance procedures.

## Table of Contents

- [Production Deployment Overview](#production-deployment-overview)
- [Systemd Service Setup](#systemd-service-setup)
- [Auto-Start Configuration](#auto-start-configuration)
- [Process Monitoring](#process-monitoring)
- [Log Management](#log-management)
- [Backup and Recovery](#backup-and-recovery)
- [Maintenance Procedures](#maintenance-procedures)
- [Security Hardening](#security-hardening)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)

## Production Deployment Overview

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi System                      │
├─────────────────────────────────────────────────────────────┤
│  Systemd Service (calendarbot.service)                     │
│  ├── Auto-start on boot                                    │
│  ├── Process monitoring & restart                          │
│  ├── Resource limits                                       │
│  └── Logging configuration                                 │
├─────────────────────────────────────────────────────────────┤
│  CalendarBot Application                                    │
│  ├── Virtual environment isolation                         │
│  ├── Configuration management                              │
│  ├── Log rotation                                          │
│  └── Error recovery                                        │
├─────────────────────────────────────────────────────────────┤
│  Data Storage                                               │
│  ├── ~/.config/calendarbot/ (configs, tokens)             │
│  ├── ~/.local/share/calendarbot/ (database)               │
│  └── /var/log/calendarbot/ (system logs)                  │
└─────────────────────────────────────────────────────────────┘
```

### Prerequisites

Before proceeding with production deployment:
- ✅ Complete [INSTALL.md](INSTALL.md) setup
- ✅ Verify application runs correctly manually
- ✅ Confirm authentication is working
- ✅ Test calendar data retrieval

## Systemd Service Setup

### 1. Create Service User (Recommended)

For security, create a dedicated user for the service:

```bash
# Create system user for calendarbot
sudo useradd --system --shell /bin/false --home /opt/calendarbot --create-home calendarbot

# Create necessary directories
sudo mkdir -p /opt/calendarbot
sudo mkdir -p /var/log/calendarbot
sudo mkdir -p /etc/calendarbot

# Set ownership
sudo chown -R calendarbot:calendarbot /opt/calendarbot
sudo chown -R calendarbot:calendarbot /var/log/calendarbot
```

### 2. Install Application for Service User

```bash
# Switch to service user (or copy files as root)
sudo -u calendarbot -s

# Navigate to service user home
cd /opt/calendarbot

# Clone application (if not already done)
git clone <repository-url> app
cd app

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy configuration
cp config/config.yaml.example config/config.yaml
# Edit config/config.yaml with your settings
```

### 3. Create Systemd Service File

Create the service definition:

```bash
sudo nano /etc/systemd/system/calendarbot.service
```

**Service file content**:

```ini
[Unit]
Description=Microsoft 365 Calendar Display Bot
Documentation=https://github.com/your-repo/calendarBot
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=30
StartLimitBurst=3

[Service]
Type=simple
User=calendarbot
Group=calendarbot
WorkingDirectory=/opt/calendarbot/app
Environment=PATH=/opt/calendarbot/app/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/calendarbot/app/venv/bin/python /opt/calendarbot/app/main.py
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

# Restart configuration
Restart=always
RestartSec=10

# Resource limits
MemoryMax=200M
CPUQuota=50%

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/calendarbot /var/log/calendarbot
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=calendarbot

[Install]
WantedBy=multi-user.target
```

### 4. Configure Service Environment

Create environment file for service-specific settings:

```bash
sudo nano /etc/calendarbot/environment
```

**Environment file content**:

```bash
# CalendarBot Environment Configuration
CALENDARBOT_CLIENT_ID=your-azure-app-client-id
CALENDARBOT_TENANT_ID=common
CALENDARBOT_LOG_LEVEL=INFO
CALENDARBOT_LOG_FILE=/var/log/calendarbot/calendarbot.log
CALENDARBOT_CONFIG_DIR=/opt/calendarbot/.config/calendarbot
CALENDARBOT_DATA_DIR=/opt/calendarbot/.local/share/calendarbot
CALENDARBOT_CACHE_DIR=/opt/calendarbot/.cache/calendarbot
```

Update service file to use environment:

```bash
sudo nano /etc/systemd/system/calendarbot.service
```

Add to `[Service]` section:
```ini
EnvironmentFile=/etc/calendarbot/environment
```

### 5. Set Permissions

```bash
# Set proper permissions
sudo chmod 644 /etc/systemd/system/calendarbot.service
sudo chmod 600 /etc/calendarbot/environment
sudo chown root:root /etc/systemd/system/calendarbot.service
sudo chown root:calendarbot /etc/calendarbot/environment

# Create required directories for service user
sudo mkdir -p /opt/calendarbot/.config/calendarbot
sudo mkdir -p /opt/calendarbot/.local/share/calendarbot
sudo mkdir -p /opt/calendarbot/.cache/calendarbot
sudo chown -R calendarbot:calendarbot /opt/calendarbot/
```

## Auto-Start Configuration

### 1. Enable and Start Service

```bash
# Reload systemd to recognize new service
sudo systemctl daemon-reload

# Enable service for auto-start
sudo systemctl enable calendarbot.service

# Start the service
sudo systemctl start calendarbot.service

# Check service status
sudo systemctl status calendarbot.service
```

### 2. Verify Auto-Start

```bash
# Check if service is enabled
sudo systemctl is-enabled calendarbot.service
# Should output: enabled

# Test auto-start by rebooting
sudo reboot

# After reboot, check service status
sudo systemctl status calendarbot.service
```

### 3. Service Control Commands

```bash
# Start service
sudo systemctl start calendarbot.service

# Stop service
sudo systemctl stop calendarbot.service

# Restart service
sudo systemctl restart calendarbot.service

# Reload configuration (if supported)
sudo systemctl reload calendarbot.service

# Check service status
sudo systemctl status calendarbot.service

# View recent logs
sudo journalctl -u calendarbot.service -f

# View logs since last boot
sudo journalctl -u calendarbot.service -b
```

## Process Monitoring

### 1. Service Health Monitoring

Create health check script:

```bash
sudo nano /opt/calendarbot/health-check.sh
```

**Health check script**:

```bash
#!/bin/bash

# CalendarBot Health Check Script
SERVICE_NAME="calendarbot.service"
LOG_FILE="/var/log/calendarbot/health-check.log"
MAX_MEMORY_MB=200
MAX_CPU_PERCENT=50

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Check if service is running
if ! systemctl is-active --quiet "$SERVICE_NAME"; then
    log "ERROR: Service $SERVICE_NAME is not running"
    # Attempt to restart
    systemctl restart "$SERVICE_NAME"
    log "INFO: Attempted to restart $SERVICE_NAME"
    exit 1
fi

# Get service PID
PID=$(systemctl show --property MainPID --value "$SERVICE_NAME")

if [ "$PID" -eq 0 ]; then
    log "ERROR: Could not determine PID for $SERVICE_NAME"
    exit 1
fi

# Check memory usage
MEMORY_KB=$(ps -p "$PID" -o rss= 2>/dev/null)
if [ -n "$MEMORY_KB" ]; then
    MEMORY_MB=$((MEMORY_KB / 1024))
    if [ "$MEMORY_MB" -gt "$MAX_MEMORY_MB" ]; then
        log "WARNING: High memory usage: ${MEMORY_MB}MB (limit: ${MAX_MEMORY_MB}MB)"
    fi
fi

# Check CPU usage (5-second average)
CPU_PERCENT=$(ps -p "$PID" -o %cpu= 2>/dev/null | tr -d ' ')
if [ -n "$CPU_PERCENT" ]; then
    if (( $(echo "$CPU_PERCENT > $MAX_CPU_PERCENT" | bc -l) )); then
        log "WARNING: High CPU usage: ${CPU_PERCENT}% (limit: ${MAX_CPU_PERCENT}%)"
    fi
fi

# Check last log entry age
LAST_LOG_TIME=$(journalctl -u "$SERVICE_NAME" -n 1 --output=json | jq -r '.__REALTIME_TIMESTAMP')
if [ -n "$LAST_LOG_TIME" ]; then
    CURRENT_TIME=$(date +%s%6N)
    AGE_SECONDS=$(( (CURRENT_TIME - LAST_LOG_TIME) / 1000000 ))
    
    # Alert if no logs in last 10 minutes
    if [ "$AGE_SECONDS" -gt 600 ]; then
        log "WARNING: No logs from service in last $((AGE_SECONDS / 60)) minutes"
    fi
fi

log "INFO: Health check completed successfully"
```

Make script executable:

```bash
sudo chmod +x /opt/calendarbot/health-check.sh
sudo chown calendarbot:calendarbot /opt/calendarbot/health-check.sh
```

### 2. Automated Health Checks

Add cron job for regular health checks:

```bash
# Edit cron for calendarbot user
sudo -u calendarbot crontab -e
```

Add health check entry:

```bash
# Run health check every 5 minutes
*/5 * * * * /opt/calendarbot/health-check.sh
```

### 3. Watchdog Configuration

Add watchdog to systemd service:

```bash
sudo nano /etc/systemd/system/calendarbot.service
```

Add to `[Service]` section:

```ini
# Watchdog configuration
WatchdogSec=60
```

## Log Management

### 1. Application Log Configuration

Configure application logging in [`config/config.yaml`](config/config.yaml.example):

```yaml
# Logging Configuration
log_level: "INFO"
log_file: "/var/log/calendarbot/calendarbot.log"
```

### 2. Log Rotation Setup

Create logrotate configuration:

```bash
sudo nano /etc/logrotate.d/calendarbot
```

**Logrotate configuration**:

```
/var/log/calendarbot/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 calendarbot calendarbot
    postrotate
        systemctl reload calendarbot.service > /dev/null 2>&1 || true
    endscript
}
```

### 3. Systemd Journal Configuration

Configure journal retention:

```bash
sudo nano /etc/systemd/journald.conf
```

Add or modify:

```ini
[Journal]
SystemMaxUse=100M
SystemMaxFileSize=10M
SystemMaxFiles=10
MaxRetentionSec=30day
```

Restart journald:

```bash
sudo systemctl restart systemd-journald
```

### 4. Log Monitoring Commands

```bash
# View live application logs
sudo tail -f /var/log/calendarbot/calendarbot.log

# View systemd service logs
sudo journalctl -u calendarbot.service -f

# View logs from last hour
sudo journalctl -u calendarbot.service --since="1 hour ago"

# View logs with specific priority
sudo journalctl -u calendarbot.service -p err

# Export logs to file
sudo journalctl -u calendarbot.service --since="1 week ago" > /tmp/calendarbot-logs.txt
```

## Backup and Recovery

### 1. Backup Strategy

Create backup script:

```bash
sudo nano /opt/calendarbot/backup.sh
```

**Backup script**:

```bash
#!/bin/bash

# CalendarBot Backup Script
BACKUP_DIR="/opt/calendarbot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="calendarbot_backup_$DATE"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup archive
tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" \
    -C /opt/calendarbot \
    app/config/ \
    .config/calendarbot/ \
    .local/share/calendarbot/ \
    --exclude="*.pyc" \
    --exclude="__pycache__"

# Log backup
echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup created: $BACKUP_NAME.tar.gz" >> /var/log/calendarbot/backup.log

# Clean old backups (keep last 7 days)
find "$BACKUP_DIR" -name "calendarbot_backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
```

Make script executable:

```bash
sudo chmod +x /opt/calendarbot/backup.sh
sudo chown calendarbot:calendarbot /opt/calendarbot/backup.sh
```

### 2. Automated Backups

Add backup to cron:

```bash
sudo -u calendarbot crontab -e
```

Add backup entry:

```bash
# Daily backup at 2 AM
0 2 * * * /opt/calendarbot/backup.sh
```

### 3. Recovery Procedure

```bash
# Stop service
sudo systemctl stop calendarbot.service

# Extract backup
cd /opt/calendarbot
sudo -u calendarbot tar -xzf backups/calendarbot_backup_YYYYMMDD_HHMMSS.tar.gz

# Verify permissions
sudo chown -R calendarbot:calendarbot /opt/calendarbot/

# Start service
sudo systemctl start calendarbot.service

# Verify service status
sudo systemctl status calendarbot.service
```

## Maintenance Procedures

### 1. Regular Maintenance Tasks

**Weekly maintenance script**:

```bash
sudo nano /opt/calendarbot/maintenance.sh
```

```bash
#!/bin/bash

# CalendarBot Maintenance Script
LOG_FILE="/var/log/calendarbot/maintenance.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "Starting maintenance tasks"

# Update package lists
log "Updating package lists"
apt update >> "$LOG_FILE" 2>&1

# Check for system updates
UPDATES=$(apt list --upgradable 2>/dev/null | grep -c upgradable)
log "Available system updates: $UPDATES"

# Clean old logs
log "Cleaning old logs"
find /var/log/calendarbot/ -name "*.log*" -mtime +30 -delete

# Check disk usage
DISK_USAGE=$(df /opt/calendarbot | awk 'NR==2 {print $5}' | sed 's/%//')
log "Disk usage: ${DISK_USAGE}%"

if [ "$DISK_USAGE" -gt 80 ]; then
    log "WARNING: High disk usage detected"
fi

# Verify service health
if systemctl is-active --quiet calendarbot.service; then
    log "Service status: Active"
else
    log "ERROR: Service is not active"
fi

log "Maintenance tasks completed"
```

### 2. Update Procedures

**Application updates**:

```bash
# Stop service
sudo systemctl stop calendarbot.service

# Backup current version
sudo -u calendarbot /opt/calendarbot/backup.sh

# Update application
cd /opt/calendarbot/app
sudo -u calendarbot git pull origin main

# Update dependencies
sudo -u calendarbot source venv/bin/activate
sudo -u calendarbot pip install --upgrade -r requirements.txt

# Start service
sudo systemctl start calendarbot.service

# Verify update
sudo systemctl status calendarbot.service
```

### 3. System Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python packages in virtual environment
cd /opt/calendarbot/app
sudo -u calendarbot source venv/bin/activate
sudo -u calendarbot pip install --upgrade pip
sudo -u calendarbot pip list --outdated

# Reboot if kernel updated
if [ -f /var/run/reboot-required ]; then
    sudo reboot
fi
```

## Security Hardening

### 1. Service Security

The systemd service includes security features:
- `NoNewPrivileges=true` - Prevents privilege escalation
- `PrivateTmp=true` - Isolated /tmp directory
- `ProtectSystem=strict` - Read-only system directories
- `ProtectHome=true` - Restricts access to home directories

### 2. File Permissions

```bash
# Secure configuration files
sudo chmod 600 /etc/calendarbot/environment
sudo chmod 644 /etc/systemd/system/calendarbot.service

# Secure application files
sudo chmod 755 /opt/calendarbot/app/
sudo chmod 600 /opt/calendarbot/.config/calendarbot/tokens.enc
sudo chmod 644 /opt/calendarbot/.config/calendarbot/config.yaml
```

### 3. Network Security

```bash
# Configure firewall (if needed)
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh

# For future e-ink display web interface
# sudo ufw allow 8080/tcp
```

## Performance Optimization

### 1. System Optimization

```bash
# Optimize for minimal power consumption
echo 'powersave' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Disable unnecessary services
sudo systemctl disable bluetooth.service
sudo systemctl disable avahi-daemon.service
```

### 2. Application Optimization

Configure settings in [`config/config.yaml`](config/config.yaml.example):

```yaml
# Optimize refresh intervals
refresh_interval: 300  # 5 minutes (increase if needed)
cache_ttl: 3600       # 1 hour

# Network timeouts
request_timeout: 30
max_retries: 3
retry_backoff_factor: 1.5
```

## Troubleshooting

### Common Deployment Issues

**Service fails to start**:

```bash
# Check service status
sudo systemctl status calendarbot.service

# View detailed logs
sudo journalctl -u calendarbot.service -f

# Check configuration
sudo -u calendarbot /opt/calendarbot/app/venv/bin/python -c "from config.settings import settings; print('Config OK')"
```

**Permission errors**:

```bash
# Fix ownership
sudo chown -R calendarbot:calendarbot /opt/calendarbot/

# Check file permissions
ls -la /opt/calendarbot/.config/calendarbot/
```

**Memory issues**:

```bash
# Check memory usage
free -h
ps aux | grep calendarbot

# Adjust memory limits in service file
sudo nano /etc/systemd/system/calendarbot.service
# Modify: MemoryMax=200M
```

**Network connectivity**:

```bash
# Test Graph API connectivity
sudo -u calendarbot curl -I https://graph.microsoft.com/v1.0/

# Check DNS resolution
nslookup graph.microsoft.com
```

### Getting Help

For deployment issues:
1. Check systemd service logs: `sudo journalctl -u calendarbot.service`
2. Verify file permissions and ownership
3. Test manual application startup
4. Review security restrictions in service file
5. Check system resource availability

---

**Production deployment complete!** Your Calendar Bot is now running as a system service with automatic startup, monitoring, and maintenance procedures.

For day-to-day operation guidance, see [USAGE.md](USAGE.md).