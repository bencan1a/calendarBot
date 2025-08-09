# CalendarBot Daemon Mode Usage Guide

**Version:** 1.0.0  
**Last Updated:** August 8, 2025  
**Related Modules:** 
- `calendarbot/cli/modes/daemon.py`
- `calendarbot/utils/daemon.py`
**Status:** Implemented

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
- [Command Reference](#command-reference)
- [Basic Workflows](#basic-workflows)
- [Advanced Usage](#advanced-usage)
- [System Integration](#system-integration)
- [Troubleshooting](#troubleshooting)
- [Technical Details](#technical-details)
- [See Also](#see-also)

## Overview

CalendarBot's daemon mode provides Docker Compose-like functionality for running CalendarBot as a background service. It allows you to start, monitor, and stop CalendarBot without keeping a terminal session open, making it ideal for server deployments, headless systems, and long-running calendar displays.

**Key Features:**
- Background service operation with process detachment
- Docker Compose-style command interface
- Comprehensive status monitoring and health checks
- Graceful shutdown with signal handling
- File-based logging for daemon operations
- PID file management following Unix conventions

**When to Use Daemon Mode:**
- Server deployments where CalendarBot should run continuously
- Headless systems without interactive terminal access
- Production environments requiring service-like operation
- E-paper displays that need 24/7 operation
- Integration with system startup processes (systemd, init scripts)

## Getting Started

### Prerequisites

- CalendarBot properly installed and configured
- Virtual environment activated
- Calendar sources configured via `calendarbot --setup`
- Sufficient permissions to create files in `~/.calendarbot/`

### Quick Start

The most basic daemon workflow:

```bash
# Activate virtual environment
. venv/bin/activate

# Start CalendarBot as background service
calendarbot --daemon

# Check if daemon is running
calendarbot --daemon-status

# Stop the daemon service
calendarbot --daemon-stop
```

## Command Reference

### Start Daemon (`--daemon`)

**Command:** `calendarbot --daemon [options]`

Starts CalendarBot as a background daemon process, detaching from the terminal and running the web server in background mode.

**Features:**
- Process detachment using Unix double-fork method
- PID file creation at `~/.calendarbot/daemon.pid`
- File-only logging to `~/.calendarbot/logs/daemon.log`
- Signal handlers for graceful shutdown
- Web server operation on specified port

**Basic Usage:**
```bash
# Start daemon on default port (8080)
calendarbot --daemon

# Start daemon on custom port
calendarbot --daemon --port 3000

# Start daemon with specific host binding
calendarbot --daemon --host 0.0.0.0 --port 8080
```

**Advanced Options:**
```bash
# Start with custom layout
calendarbot --daemon --web_layout whats-next-view

# Start with specific display type
calendarbot --daemon --display_type 3x4

# Start with verbose logging
calendarbot --daemon --verbose
```

**Output Example:**
```
Starting CalendarBot daemon...
CalendarBot daemon started successfully with PID 12345
Web server is starting on port 8080
Access your calendar at: http://<host-ip>:8080
```

### Check Status (`--daemon-status`)

**Command:** `calendarbot --daemon-status`

Displays comprehensive status information about the running daemon, including health monitoring and operational details.

**Features:**
- Process health verification
- Uptime calculation
- Port and PID information
- Log file location
- Resource usage (when psutil is available)

**Usage:**
```bash
calendarbot --daemon-status
```

**Example Output:**
```
CalendarBot Daemon Status:
  PID: 12345
  Port: 8080
  Uptime: 2:15:30
  Health: healthy
  Log file: /home/user/.calendarbot/logs/daemon.log
```

**Status When Not Running:**
```
CalendarBot daemon is not running
```

### Stop Daemon (`--daemon-stop`)

**Command:** `calendarbot --daemon-stop [--daemon-timeout SECONDS]`

Gracefully stops the running daemon process with configurable timeout and force-kill fallback.

**Features:**
- Graceful shutdown via SIGTERM signal
- Configurable timeout for shutdown wait
- Force kill (SIGKILL) fallback if graceful shutdown fails
- Automatic PID file cleanup
- Process verification

**Basic Usage:**
```bash
# Stop daemon with default 30-second timeout
calendarbot --daemon-stop

# Stop daemon with custom timeout
calendarbot --daemon-stop --daemon-timeout 60
```

**Example Output:**
```
Stopping CalendarBot daemon (PID 12345)...
CalendarBot daemon stopped successfully
```

## Basic Workflows

### Daily Operation Workflow

**Start Service:**
```bash
. venv/bin/activate
calendarbot --daemon --port 8080
```

**Monitor Service:**
```bash
# Check status periodically
calendarbot --daemon-status

# Monitor logs
tail -f ~/.calendarbot/logs/daemon.log
```

**Stop Service:**
```bash
calendarbot --daemon-stop
```

### Development and Testing Workflow

**Start for Testing:**
```bash
# Start on different port to avoid conflicts
calendarbot --daemon --port 3000 --verbose

# Verify it's running
calendarbot --daemon-status

# Test web interface
curl http://localhost:3000/calendar
```

**Stop and Restart:**
```bash
# Stop current instance
calendarbot --daemon-stop

# Start with new configuration
calendarbot --daemon --port 8080 --web_layout whats-next-view
```

### Production Deployment Workflow

**Initial Setup:**
```bash
# Configure calendar sources
calendarbot --setup

# Test configuration
calendarbot --test-mode

# Start daemon
calendarbot --daemon --host 0.0.0.0 --port 8080
```

**Monitoring:**
```bash
# Health check script (can be automated)
#!/bin/sh
if calendarbot --daemon-status > /dev/null 2>&1; then
    echo "CalendarBot daemon is healthy"
    exit 0
else
    echo "CalendarBot daemon is not running"
    exit 1
fi
```

## Advanced Usage

### Custom Port Configuration

```bash
# Standard web port
calendarbot --daemon --port 80

# Custom application port
calendarbot --daemon --port 9090

# Development port
calendarbot --daemon --port 3000
```

### Layout and Display Options

```bash
# E-paper optimized layout
calendarbot --daemon --web_layout whats-next-view --display_type 3x4

# Large display layout
calendarbot --daemon --display_type 4x8

# Compact layout for small screens
calendarbot --daemon --display_type 3x4
```

### Logging Configuration

```bash
# Verbose logging for debugging
calendarbot --daemon --verbose

# Specific log level
CALENDARBOT_LOG_LEVEL=DEBUG calendarbot --daemon
```

### Host Binding Options

```bash
# Bind to all interfaces (server deployment)
calendarbot --daemon --host 0.0.0.0

# Bind to specific interface
calendarbot --daemon --host 192.168.1.100

# Localhost only (default)
calendarbot --daemon --host 127.0.0.1
```

## System Integration

### Systemd Service Integration

Create a systemd service file for automatic startup:

**File:** `/etc/systemd/system/calendarbot.service`
```ini
[Unit]
Description=CalendarBot Calendar Display Service
After=network.target

[Service]
Type=forking
User=calendarbot
WorkingDirectory=/home/calendarbot/calendarbot
ExecStartPre=/bin/sh -c '. venv/bin/activate'
ExecStart=/home/calendarbot/calendarbot/venv/bin/python -m calendarbot --daemon --port 8080
ExecStop=/home/calendarbot/calendarbot/venv/bin/python -m calendarbot --daemon-stop
PIDFile=/home/calendarbot/.calendarbot/daemon.pid
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Enable and Start Service:**
```bash
sudo systemctl enable calendarbot
sudo systemctl start calendarbot
sudo systemctl status calendarbot
```

### Cron Job Integration

For systems without systemd, use cron for basic monitoring:

```bash
# Add to crontab: Check every 5 minutes, restart if not running
*/5 * * * * /home/user/check_calendarbot.sh

# check_calendarbot.sh script:
#!/bin/sh
cd /home/user/calendarbot
. venv/bin/activate
if ! calendarbot --daemon-status > /dev/null 2>&1; then
    calendarbot --daemon --port 8080
fi
```

### Docker Integration

While daemon mode is designed for direct system deployment, it can also be used within containers:

```dockerfile
# Dockerfile example
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install -e .
EXPOSE 8080
CMD ["python", "-m", "calendarbot", "--daemon", "--port", "8080", "--host", "0.0.0.0"]
```

## Troubleshooting

### Common Issues and Solutions

#### "Daemon already running" Error

**Problem:** Attempting to start daemon when one is already running.

**Solution:**
```bash
# Check current status
calendarbot --daemon-status

# Stop existing daemon
calendarbot --daemon-stop

# Start new daemon
calendarbot --daemon
```

#### Stale PID File

**Problem:** PID file exists but process is not running.

**Symptoms:**
```
CalendarBot daemon is not running
# but PID file exists at ~/.calendarbot/daemon.pid
```

**Solution:**
```bash
# Remove stale PID file
rm ~/.calendarbot/daemon.pid

# Start daemon normally
calendarbot --daemon
```

#### Permission Denied Errors

**Problem:** Cannot create PID file or log files.

**Solution:**
```bash
# Create CalendarBot directory with proper permissions
mkdir -p ~/.calendarbot/logs
chmod 755 ~/.calendarbot
chmod 755 ~/.calendarbot/logs

# Try starting daemon again
calendarbot --daemon
```

#### Port Already in Use

**Problem:** Cannot bind to specified port.

**Symptoms:**
```bash
calendarbot --daemon --port 8080
# Error: [Errno 98] Address already in use
```

**Solution:**
```bash
# Check what's using the port
lsof -i :8080
# or
netstat -tulpn | grep :8080

# Use different port
calendarbot --daemon --port 8081

# Or stop conflicting service
sudo systemctl stop apache2  # if Apache is using port 8080
```

#### Daemon Won't Stop

**Problem:** `calendarbot --daemon-stop` doesn't work.

**Solution:**
```bash
# Check daemon status
calendarbot --daemon-status

# Force stop with longer timeout
calendarbot --daemon-stop --daemon-timeout 60

# Manual cleanup if needed
pkill -f "calendarbot.*daemon"
rm ~/.calendarbot/daemon.pid
```

#### No Web Response

**Problem:** Daemon is running but web interface is not accessible.

**Diagnosis:**
```bash
# Check daemon status
calendarbot --daemon-status

# Check if port is listening
netstat -tulpn | grep :8080

# Check logs
tail -f ~/.calendarbot/logs/daemon.log

# Test local connection
curl http://localhost:8080/calendar
```

**Solutions:**
- Verify firewall settings
- Check host binding (use `--host 0.0.0.0` for external access)
- Ensure no proxy/load balancer conflicts
- Verify calendar configuration is valid

### Log File Analysis

**Default Log Location:** `~/.calendarbot/logs/daemon.log`

**Useful Log Patterns:**
```bash
# Check daemon startup
grep "Daemon started" ~/.calendarbot/logs/daemon.log

# Check for errors
grep "ERROR" ~/.calendarbot/logs/daemon.log

# Monitor in real-time
tail -f ~/.calendarbot/logs/daemon.log

# Check web server status
grep "Web server" ~/.calendarbot/logs/daemon.log
```

### Health Check Commands

**Quick Health Check:**
```bash
# Simple status check
calendarbot --daemon-status && echo "Healthy" || echo "Not running"

# Full health verification
#!/bin/sh
STATUS=$(calendarbot --daemon-status)
if [ $? -eq 0 ]; then
    echo "Daemon Status: OK"
    echo "$STATUS"
    
    # Test web interface
    curl -s http://localhost:8080/calendar > /dev/null
    if [ $? -eq 0 ]; then
        echo "Web Interface: OK"
    else
        echo "Web Interface: ERROR"
    fi
else
    echo "Daemon Status: NOT RUNNING"
fi
```

## Technical Details

### PID File Management

**Location:** `~/.calendarbot/daemon.pid`

The daemon uses a PID file to track the running process:
- Created when daemon starts
- Contains the process ID (PID) of the daemon
- Automatically cleaned up on graceful shutdown
- Stale files are detected and removed

### Process Detachment

CalendarBot daemon uses the Unix double-fork method for proper process detachment:

1. **First fork:** Creates child process, parent exits
2. **Session leader:** Child becomes session leader with `setsid()`
3. **Second fork:** Prevents TTY reacquisition
4. **File descriptor redirection:** stdout/stderr/stdin → /dev/null
5. **Working directory:** Changed to `/` to avoid filesystem locks

### Signal Handling

The daemon handles these signals gracefully:
- **SIGTERM:** Graceful shutdown (preferred)
- **SIGINT:** Interrupt signal (Ctrl+C equivalent)
- **SIGKILL:** Force termination (used as fallback)

### Logging Configuration

**Daemon-specific logging settings:**
- Console logging: Disabled (daemon runs in background)
- File logging: Enabled to `~/.calendarbot/logs/daemon.log`
- Log rotation: Handled by system log rotation tools
- Verbosity: Configurable via `--verbose` flag

### Resource Management

**Memory Usage:**
- Base CalendarBot process memory
- Web server overhead (minimal with async framework)
- Calendar data caching

**CPU Usage:**
- Event-driven architecture for minimal CPU usage
- Periodic calendar refresh (configurable interval)
- Web request handling

**Disk Usage:**
- Log files in `~/.calendarbot/logs/`
- Cache data in `~/.calendarbot/cache/`
- Configuration in `~/.calendarbot/config.yaml`

### Dependencies

**Required:**
- Python 3.8+
- CalendarBot core dependencies
- Unix-like operating system (Linux, macOS)

**Optional:**
- `psutil`: Enhanced process monitoring and resource usage
- `systemd`: For system service integration
- Log rotation tools: `logrotate`, `rotatelogs`

### Port and Network Configuration

**Default Port:** 8080  
**Supported Protocols:** HTTP (HTTPS can be added via reverse proxy)  
**Host Binding:** 
- `127.0.0.1` (localhost only, default)
- `0.0.0.0` (all interfaces)
- Specific IP addresses

**Firewall Considerations:**
```bash
# Allow CalendarBot port through firewall
sudo ufw allow 8080/tcp

# For specific interface only
sudo ufw allow from 192.168.1.0/24 to any port 8080
```

## See Also

- [General Usage Guide](USAGE.md) - Basic CalendarBot operation
- [Operational Modes](../features/OPERATIONAL_MODES.md) - All available modes
- [Setup Guide](SETUP.md) - Initial configuration
- [Web Mode Documentation](../features/WEB_MODE.md) - Web interface details
- [System Administration](../admin/SYSTEM_ADMIN.md) - Advanced deployment