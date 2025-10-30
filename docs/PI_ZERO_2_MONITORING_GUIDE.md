# CalendarBot_Lite Pi Zero 2 Monitoring Solution - Implementation and Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites and Requirements](#prerequisites-and-requirements)
4. [Installation Instructions](#installation-instructions)
5. [Configuration Guide](#configuration-guide)
6. [Operational Procedures](#operational-procedures)
7. [Integration Examples](#integration-examples)
8. [Reference Documentation](#reference-documentation)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Advanced Topics](#advanced-topics)

---

## Overview

### Purpose and Benefits

The CalendarBot_Lite monitoring solution provides comprehensive health monitoring and automatic recovery for kiosk deployments on Raspberry Pi Zero 2. This system ensures maximum uptime and reliability through:

- **Multi-level Health Monitoring**: Continuous health checks for server, browser, and X session
- **Intelligent Recovery**: 4-level escalation strategy from browser restart to system reboot
- **Resource Optimization**: Designed specifically for Pi Zero 2 constraints with minimal overhead
- **Structured Logging**: JSON-based event logging with rate limiting and remote shipping
- **Dashboard Integration**: Real-time status exports for external monitoring systems

### Key Features

- **Health Endpoint**: Comprehensive [`/api/health`](../calendarbot_lite/server.py) endpoint with server status, refresh tracking, and system metrics
- **Watchdog Service**: [`calendarbot-kiosk-watchdog@.service`](../kiosk/service/calendarbot-kiosk-watchdog@.service) with automatic escalation
- **Log Management**: Structured logging with [`monitoring_logging.py`](../calendarbot_lite/monitoring_logging.py) and remote shipping
- **Event Processing**: Intelligent filtering and aggregation with rate limiting
- **Dashboard Support**: JSON/Prometheus metrics for Grafana, Nagios, and custom dashboards

### Benefits for Pi Zero 2 Kiosk Deployments

- **Reliability**: Automatic recovery from browser crashes, X session failures, and service issues
- **Resource Efficiency**: <30MB memory footprint, <2% CPU usage
- **Remote Monitoring**: Optional webhook and syslog integration for centralized monitoring
- **Maintenance Reduction**: Self-healing capabilities reduce manual intervention
- **Audit Trail**: Comprehensive logging of all recovery actions and system events

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CalendarBot_Lite Monitoring                     │
├─────────────────────────────────────────────────────────────────────┤
│  Health Endpoint    │  Watchdog Service   │    Log Management     │
│  (/api/health)      │  (4-level recovery) │   (JSON + shipping)   │
├─────────────────────────────────────────────────────────────────────┤
│  Event Processing   │  Status Dashboard   │   External Integr.    │
│  (filter/aggregate) │  (JSON/Prometheus)  │   (webhooks/syslog)   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Raspberry Pi Zero 2 System                     │
├─────────────────────────────────────────────────────────────────────┤
│    X Session       │     Browser         │     CalendarBot       │
│  (matchbox-wm)     │   (Chromium)        │   (Python server)     │
├─────────────────────────────────────────────────────────────────────┤
│   Systemd          │    Journald         │      Rsyslog          │
│ (service mgmt)     │  (log collection)   │   (log routing)       │
└─────────────────────────────────────────────────────────────────────┘
```

### Recovery Escalation Levels

1. **Level 0**: Transient retry with exponential backoff (10s, 20s, 40s)
2. **Level 1**: Browser restart via process termination and relaunch
3. **Level 2**: X session restart (window manager and display)
4. **Level 3**: Systemd service restart (full application restart)
5. **Level 4**: System reboot (last resort with rate limiting)

### Data Flow

1. **Health Monitoring**: Continuous checks of [`/api/health`](../calendarbot_lite/server.py), HTML rendering, and process status
2. **Event Generation**: Structured JSON events via [`monitoring_logging.py`](../calendarbot_lite/monitoring_logging.py)
3. **Log Routing**: Journald → Rsyslog → Local files + Remote endpoints
4. **Event Processing**: Filtering, deduplication, and aggregation
5. **Recovery Actions**: Automated responses based on escalation matrix
6. **Status Export**: Real-time status for dashboards and monitoring systems

### Pi Zero 2 Optimizations

- **Memory Management**: Streaming log processing, limited cache sizes
- **CPU Efficiency**: JSON parsing optimizations, rate limiting
- **Storage Optimization**: Log rotation, compression, retention policies
- **Network Conservation**: Batched remote shipping, compression
- **Graceful Degradation**: Reduced monitoring frequency under system load

---

## Prerequisites and Requirements

### Hardware Requirements

- **Raspberry Pi Zero 2 W** (minimum 512MB RAM)
- **MicroSD Card**: 16GB+ Class 10 (32GB+ recommended)
- **Network Connection**: WiFi or Ethernet for remote monitoring (optional)

### Software Requirements

#### Base System
- **OS**: Raspberry Pi OS Lite (Debian 11+ based)
- **Python**: 3.7+ with pip
- **systemd**: Service management (included in Pi OS)
- **X11**: For GUI kiosk mode

#### Required Packages
```bash
# Essential system packages
sudo apt update
sudo apt install -y python3-pip python3-venv curl jq rsyslog

# Python dependencies
pip3 install PyYAML

# Optional: for advanced monitoring
sudo apt install -y prometheus-node-exporter logrotate
```

#### Existing CalendarBot_Lite Setup
- Working CalendarBot_Lite installation
- Configured kiosk service from [`kiosk/service/calendarbot-kiosk.service`](../kiosk/service/calendarbot-kiosk.service)
- Browser setup via [`kiosk/scripts/.xinitrc`](../kiosk/scripts/.xinitrc)

### Network Requirements

#### Local (Required)
- **Health endpoint**: `http://127.0.0.1:8080/api/health`
- **Web interface**: `http://127.0.0.1:8080/`

#### Remote (Optional)
- **Webhook endpoint**: HTTPS recommended for log shipping
- **Syslog server**: TCP/UDP 514 or custom port
- **Monitoring dashboard**: HTTP/HTTPS access for status API

### Storage Requirements

| Component | Storage Usage | Location |
|-----------|---------------|----------|
| Watchdog script | <1MB | `/usr/local/bin/` |
| Configuration | <10KB | `/etc/calendarbot-monitor/` |
| Local logs | 2-50MB | `/var/log/calendarbot-watchdog/` |
| State files | <1MB | `/var/local/calendarbot-watchdog/` |
| Scripts | <1MB | `/opt/calendarbot/kiosk/scripts/` |

---

## Installation Instructions

### Step 1: Prepare Installation Environment

```bash
# Create installation directory
sudo mkdir -p /opt/calendarbot
cd /opt/calendarbot

# Clone or copy CalendarBot repository
# (Assuming files are already present in current directory)

# Activate Python virtual environment if using one
. venv/bin/activate  # If using project venv
```

### Step 2: Install Core Components

```bash
# Install watchdog script
sudo cp kiosk/scripts/calendarbot-watchdog /usr/local/bin/
sudo chmod +x /usr/local/bin/calendarbot-watchdog

# Install monitoring scripts
sudo mkdir -p /opt/calendarbot/kiosk/scripts
sudo cp kiosk/scripts/*.sh /opt/calendarbot/kiosk/scripts/
sudo chmod +x /opt/calendarbot/kiosk/scripts/*.sh

# Install systemd service
sudo cp kiosk/service/calendarbot-kiosk-watchdog@.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### Step 3: Configure Monitoring System

```bash
# Create configuration directory
sudo mkdir -p /etc/calendarbot-monitor

# Install base configuration
sudo cp kiosk/config/monitor.yaml /etc/calendarbot-monitor/
sudo cp kiosk/config/rsyslog-calendarbot.conf /etc/rsyslog.d/50-calendarbot.conf

# Install log rotation configuration
sudo cp kiosk/config/logrotate-calendarbot-watchdog /etc/logrotate.d/calendarbot-watchdog
```

### Step 4: Create Directories and Set Permissions

```bash
# Create log directories
sudo mkdir -p /var/log/calendarbot-watchdog
sudo mkdir -p /var/log/calendarbot
sudo mkdir -p /var/local/calendarbot-watchdog
sudo mkdir -p /var/local/calendarbot-watchdog/reports

# Set ownership for pi user
sudo chown -R pi:pi /var/log/calendarbot-watchdog
sudo chown -R pi:pi /var/local/calendarbot-watchdog

# Set permissions
sudo chmod 755 /var/log/calendarbot
sudo chmod 700 /var/local/calendarbot-watchdog
```

### Step 5: Configure System Permissions

```bash
# Create sudoers configuration for reboot privileges
sudo tee /etc/sudoers.d/calendarbot-watchdog << 'EOF'
# CalendarBot watchdog recovery privileges
pi ALL=NOPASSWD: /sbin/reboot
pi ALL=NOPASSWD: /bin/systemctl restart calendarbot-kiosk@pi.service
pi ALL=NOPASSWD: /bin/systemctl restart graphical-session.target
EOF

# Restart rsyslog to load new configuration
sudo systemctl restart rsyslog
```

### Step 6: Enable and Start Services

```bash
# Enable watchdog service for user 'pi'
sudo systemctl enable calendarbot-kiosk-watchdog@pi.service

# Start the watchdog service
sudo systemctl start calendarbot-kiosk-watchdog@pi.service

# Verify service status
sudo systemctl status calendarbot-kiosk-watchdog@pi.service

# Check service logs
sudo journalctl -u calendarbot-kiosk-watchdog@pi.service -f --lines=20
```

### Step 7: Verify Installation

```bash
# Test health endpoint
curl -v http://127.0.0.1:8080/api/health

# Check render marker
curl -s http://127.0.0.1:8080/ | grep 'calendarbot-ready'

# Verify log structure
sudo tail -f /var/log/calendarbot-watchdog/watchdog.log

# Test monitoring scripts
/opt/calendarbot/kiosk/scripts/monitoring-status.sh health
```

---

## Configuration Guide

### Monitor Configuration (`/etc/calendarbot-monitor/monitor.yaml`)

The main configuration file controls all monitoring behavior:

#### Health Check Settings

```yaml
monitor:
  health_check:
    # Primary health endpoint check interval (seconds)
    interval_s: 30
    # HTML render probe interval (seconds) - heavier check
    render_probe_interval_s: 60
    # X session responsiveness check interval (seconds)
    x_health_interval_s: 120
    # Maximum retries for transient failures before escalating
    max_retries: 3
    # Request timeout for health checks (seconds)
    request_timeout_s: 6
    # Base URL for health checks - will resolve to local IP
    base_url: "http://127.0.0.1:8080"
    # HTML marker to look for in render probe
    render_marker: 'name="calendarbot-ready"'
```

#### Failure Thresholds and Rate Limiting

```yaml
  thresholds:
    # Factor to multiply refresh interval for staleness detection
    refresh_miss_factor: 2
    # Number of consecutive render probe failures before escalation
    render_fail_count: 2
    # Maximum browser restarts per hour before escalating
    max_browser_restarts_per_hour: 4
    # Maximum service restarts per hour before escalating  
    max_service_restarts_per_hour: 2
    # Maximum reboots per 24 hours (last resort)
    max_reboots_per_day: 1
    # Minimum seconds between recovery actions of same level
    recovery_cooldown_s: 60
```

#### System Commands Configuration

```yaml
  commands:
    # Command to detect running browser process
    browser_detect_cmd: "pgrep -f 'chromium.*--kiosk' || pgrep -f 'epiphany.*--kiosk'"
    # Command to launch browser (will be executed via shell)
    browser_launch_cmd: |
      export DISPLAY=:0 && cd /home/{user} && 
      chromium --no-memcheck --kiosk --enable-low-end-device-mode --noerrdialogs \
        --no-first-run --no-default-browser-check \
        --disable-session-crashed-bubble \
        --overscroll-history-navigation=0 \
        --disable-vulkan --disable-gpu-compositing \
        --disable-background-networking --disable-component-update \
        --disable-sync --no-pings \
        http://$(hostname -I | awk '{print $1}'):8080 &
    # Command to gracefully stop browser
    browser_stop_cmd: "pkill -TERM -f 'chromium.*--kiosk'; sleep 8; pkill -KILL -f 'chromium.*--kiosk' 2>/dev/null || true"
    # Command to check X server availability  
    x_health_cmd: "DISPLAY=:0 xdpyinfo >/dev/null 2>&1"
    # Systemd unit name for kiosk service
    kiosk_systemd_unit: "calendarbot-kiosk@{user}.service"
```

#### Resource Limits and Graceful Degradation

```yaml
  resource_limits:
    # Minimum free memory (KB) before degrading monitoring frequency
    min_free_mem_kb: 60000
    # Maximum 1-minute load average before degrading monitoring
    max_load_1m: 1.5
    # Degradation factor for intervals when under resource pressure
    degradation_factor: 2.0
    # Enable automatic throttling under system load
    auto_throttle: true
```

#### Logging Configuration

```yaml
  logging:
    # Local log directory (will be created if needed)
    local_log_dir: "/var/log/calendarbot-watchdog"
    # Log level: DEBUG, INFO, WARN, ERROR
    log_level: "INFO"
    # Maximum log file size before rotation (MB)
    max_log_size_mb: 2
    # Number of rotated log files to keep
    log_files_to_keep: 7
    # Enable JSON structured logging
    json_logging: true
    # Log to systemd journal as well
    journal_logging: true
```

### Environment Variable Overrides

Environment variables provide runtime configuration overrides:

#### Debug and Development
```bash
# Enable debug logging
export CALENDARBOT_DEBUG=true
export CALENDARBOT_WATCHDOG_DEBUG=true
export CALENDARBOT_LOG_LEVEL=DEBUG

# Disable recovery actions for testing
export CALENDARBOT_WATCHDOG_DISABLED=true

# Force degraded mode
export CALENDARBOT_WATCHDOG_DEGRADED=true
```

#### Remote Monitoring Setup
```bash
# Log shipping configuration
export CALENDARBOT_LOG_SHIPPER_ENABLED=true
export CALENDARBOT_WEBHOOK_URL="https://your-monitoring.example.com/webhook"
export CALENDARBOT_WEBHOOK_TOKEN="your-bearer-token"
export CALENDARBOT_WEBHOOK_TIMEOUT=10

# Syslog forwarding
export CALENDARBOT_REMOTE_SYSLOG_SERVER="syslog.example.com"
export CALENDARBOT_REMOTE_SYSLOG_PORT=514
```

#### Monitoring Scripts Configuration
```bash
# Aggregation settings
export CALENDARBOT_AGGREGATOR_RETENTION_DAYS=30
export CALENDARBOT_AGGREGATOR_EXPORT_METRICS=true

# Status dashboard settings
export CALENDARBOT_STATUS_CACHE=true
export CALENDARBOT_STATUS_TRENDS=true
```

### Security Considerations

#### File Permissions
```bash
# Secure configuration files
sudo chmod 640 /etc/calendarbot-monitor/monitor.yaml
sudo chown root:pi /etc/calendarbot-monitor/monitor.yaml

# Secure log directories
sudo chmod 750 /var/log/calendarbot-watchdog
sudo chmod 700 /var/local/calendarbot-watchdog
```

#### Network Security
```bash
# Use HTTPS for webhooks
CALENDARBOT_WEBHOOK_URL="https://secure-endpoint.example.com/webhook"

# Enable SSL verification
export CALENDARBOT_WEBHOOK_INSECURE=false

# Use encrypted syslog
export CALENDARBOT_REMOTE_SYSLOG_TLS=true
```

#### Access Control

For webhook authentication, create a secure token:
```bash
# Generate secure webhook token
WEBHOOK_TOKEN=$(openssl rand -hex 32)
echo "export CALENDARBOT_WEBHOOK_TOKEN='$WEBHOOK_TOKEN'" >> /home/pi/.bashrc
```

---

## Operational Procedures

### Health Monitoring

#### Real-time Health Status

```bash
# Quick health check
curl -s http://127.0.0.1:8080/api/health | jq '.'

# Generate comprehensive status
/opt/calendarbot/kiosk/scripts/monitoring-status.sh health

# Dashboard-compatible status
/opt/calendarbot/kiosk/scripts/monitoring-status.sh status /tmp/status.json
cat /tmp/status.json | jq '.'
```

#### Health Endpoint Response Format

```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00Z",
  "server": {
    "status": "running",
    "uptime_seconds": 86400,
    "memory_usage": "28MB"
  },
  "last_refresh": {
    "timestamp": "2024-01-15T10:29:30Z",
    "success": true,
    "last_success_delta_s": 30,
    "refresh_interval_s": 300
  },
  "background_tasks": {
    "refresher_active": true,
    "last_refresh_error": null
  },
  "system_diagnostics": {
    "cpu_load": 0.8,
    "memory_free_mb": 128.5,
    "disk_free_mb": 2048.0,
    "uptime_seconds": 86400
  }
}
```

### Log Analysis and Monitoring Events

#### Structured Log Format

All monitoring events use this JSON schema:
```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "component": "server|watchdog|health|recovery",
  "level": "DEBUG|INFO|WARN|ERROR|CRITICAL",
  "event": "health.endpoint.check",
  "message": "Human readable description",
  "details": {
    "custom": "event-specific data"
  },
  "action_taken": "Description of any action taken",
  "recovery_level": 0,
  "system_state": {
    "cpu_load": 0.8,
    "memory_free_mb": 128.5,
    "disk_free_mb": 2048.0
  },
  "schema_version": "1.0"
}
```

#### Key Event Codes

| Event Code | Component | Description |
|------------|-----------|-------------|
| `health.endpoint.check` | health | Health endpoint validation |
| `health.endpoint.fail` | health | Health endpoint unreachable |
| `render.probe.check` | health | HTML render verification |
| `browser.restart.start` | recovery | Browser restart initiated |
| `service.restart.complete` | recovery | Service restart completed |
| `reboot.start` | recovery | System reboot initiated |
| `degraded.mode.active` | watchdog | System under resource pressure |

#### Log File Locations

```bash
# Structured monitoring logs
/var/log/calendarbot-watchdog/watchdog.log

# Component-specific logs (rsyslog)
/var/log/calendarbot/server.log
/var/log/calendarbot/watchdog.log
/var/log/calendarbot/critical.log

# System logs
sudo journalctl -u calendarbot-kiosk-watchdog@pi.service
sudo journalctl -u calendarbot-kiosk@pi.service
```

### Recovery Process Verification

#### Test Recovery Scenarios

```bash
# Test browser recovery
sudo pkill -f chromium
# Wait 2-3 minutes, verify browser restarts

# Test health endpoint failure
sudo systemctl stop calendarbot-kiosk@pi.service
# Wait for escalation, verify service restart

# Test X session recovery
sudo pkill -f matchbox-window-manager
# Wait for escalation, verify X restart
```

#### Monitor Recovery Actions

```bash
# Watch recovery events in real-time
sudo journalctl -u calendarbot-kiosk-watchdog@pi.service -f | grep -E '(recovery|escalate)'

# Check recovery state
cat /var/local/calendarbot-watchdog/state.json | jq '.'

# View recovery statistics
/opt/calendarbot/kiosk/scripts/critical-event-filter.sh stats
```

#### Verify Recovery Effectiveness

```bash
# Generate recovery report
/opt/calendarbot/kiosk/scripts/log-aggregator.sh daily $(date +%Y-%m-%d)

# Check recovery patterns
cat /var/local/calendarbot-watchdog/reports/daily_$(date +%Y-%m-%d).json | \
  jq '.patterns.recovery_effectiveness'
```

### Maintenance and Updates

#### Log Rotation and Cleanup

```bash
# Manual log rotation
sudo logrotate -f /etc/logrotate.d/calendarbot-watchdog

# Clean old reports
/opt/calendarbot/kiosk/scripts/log-aggregator.sh cleanup

# Clear state files (reset rate limiting)
sudo rm -f /var/local/calendarbot-watchdog/state.json
sudo systemctl restart calendarbot-kiosk-watchdog@pi.service
```

#### Configuration Updates

```bash
# Validate configuration changes
python3 -c "import yaml; yaml.safe_load(open('/etc/calendarbot-monitor/monitor.yaml'))"

# Reload configuration
sudo systemctl restart calendarbot-kiosk-watchdog@pi.service

# Test configuration
sudo /usr/local/bin/calendarbot-watchdog --config /etc/calendarbot-monitor/monitor.yaml --user pi --version
```

#### Service Updates

```bash
# Update monitoring scripts
sudo cp kiosk/scripts/*.sh /opt/calendarbot/kiosk/scripts/
sudo chmod +x /opt/calendarbot/kiosk/scripts/*.sh

# Update systemd service
sudo cp kiosk/service/calendarbot-kiosk-watchdog@.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart calendarbot-kiosk-watchdog@pi.service
```

---

## Integration Examples

### Dashboard Integration

#### Grafana Integration

1. **Install Prometheus Node Exporter**:
```bash
sudo apt install prometheus-node-exporter
sudo systemctl enable prometheus-node-exporter
```

2. **Generate Prometheus Metrics**:
```bash
# Create metrics endpoint
/opt/calendarbot/kiosk/scripts/monitoring-status.sh metrics /var/lib/prometheus/calendarbot.prom

# Add to crontab for regular updates
echo "*/5 * * * * /opt/calendarbot/kiosk/scripts/monitoring-status.sh metrics /var/lib/prometheus/calendarbot.prom" | crontab -
```

3. **Grafana Dashboard Configuration**:
```json
{
  "dashboard": {
    "title": "CalendarBot Kiosk Monitoring",
    "panels": [
      {
        "title": "System Health",
        "targets": [
          "calendarbot_up",
          "calendarbot_memory_usage_percent",
          "calendarbot_cpu_load_1m"
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          "calendarbot_errors_total_24h",
          "calendarbot_recovery_actions_24h"
        ]
      }
    ]
  }
}
```

#### Nagios Integration

```bash
# Create Nagios check script
sudo tee /usr/local/lib/nagios/plugins/check_calendarbot << 'EOF'
#!/bin/bash
HEALTH_OUTPUT=$(/opt/calendarbot/kiosk/scripts/monitoring-status.sh health 2>/dev/null)
if [[ $? -eq 0 ]]; then
    echo "OK - CalendarBot is healthy"
    exit 0
else
    echo "CRITICAL - CalendarBot health check failed"
    exit 2
fi
EOF

sudo chmod +x /usr/local/lib/nagios/plugins/check_calendarbot
```

### Remote Monitoring Setup

#### Webhook Integration

1. **Configure Webhook Endpoint**:
```bash
export CALENDARBOT_LOG_SHIPPER_ENABLED=true
export CALENDARBOT_WEBHOOK_URL="https://monitoring.example.com/api/calendarbot/events"
export CALENDARBOT_WEBHOOK_TOKEN="your-secure-token-here"
```

2. **Test Webhook Configuration**:
```bash
/opt/calendarbot/kiosk/scripts/log-shipper.sh test
```

3. **Example Webhook Handler** (Python Flask):
```python
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route('/api/calendarbot/events', methods=['POST'])
def receive_calendarbot_event():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token != 'your-secure-token-here':
        return jsonify({'error': 'Unauthorized'}), 401
    
    event = request.json
    print(f"Received CalendarBot event: {json.dumps(event, indent=2)}")
    
    # Process critical events
    if event.get('level') == 'CRITICAL':
        send_alert(event)
    
    return jsonify({'status': 'received'}), 200

def send_alert(event):
    # Implement your alerting logic here
    pass
```

#### Syslog Integration

1. **Configure Rsyslog Client**:
```bash
# Add to /etc/rsyslog.conf
echo "*.* @@syslog.example.com:514" | sudo tee -a /etc/rsyslog.conf
sudo systemctl restart rsyslog
```

2. **ELK Stack Integration**:
```bash
# Logstash configuration for CalendarBot events
input {
  syslog {
    port => 514
    type => "calendarbot"
  }
}

filter {
  if [type] == "calendarbot" {
    json {
      source => "message"
    }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "calendarbot-%{+YYYY.MM.dd}"
  }
}
```

### External System Integration

#### IFTTT/Zapier Integration

```bash
# Create webhook trigger for critical events
curl -X POST "https://maker.ifttt.com/trigger/calendarbot_critical/with/key/YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "value1": "CalendarBot Critical Event",
    "value2": "System reboot initiated",
    "value3": "Pi Zero 2 Kiosk"
  }'
```

#### Slack Integration

```bash
# Slack webhook for notifications
SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

curl -X POST "$SLACK_WEBHOOK" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "CalendarBot Alert",
    "attachments": [
      {
        "color": "danger",
        "fields": [
          {
            "title": "Event",
            "value": "Browser restart required",
            "short": true
          },
          {
            "title": "Device",
            "value": "Pi Zero 2 Kiosk",
            "short": true
          }
        ]
      }
    ]
  }'
```

---

## Reference Documentation

### Health API Reference

#### GET `/api/health`

**Description**: Comprehensive health status endpoint for monitoring and recovery systems.

**Request**:
```http
GET /api/health HTTP/1.1
Host: 127.0.0.1:8080
User-Agent: CalendarBot-Watchdog/1.0.0
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-cache

{
  "status": "ok|degraded|critical",
  "timestamp": "2024-01-15T10:30:00.123Z",
  "server": {
    "status": "running",
    "uptime_seconds": 86400,
    "memory_usage": "28MB",
    "active_connections": 1
  },
  "last_refresh": {
    "timestamp": "2024-01-15T10:29:30Z",
    "success": true,
    "last_success_delta_s": 30,
    "refresh_interval_s": 300,
    "error_count": 0
  },
  "background_tasks": {
    "refresher_active": true,
    "last_refresh_error": null,
    "task_count": 1
  },
  "system_diagnostics": {
    "cpu_load": 0.8,
    "memory_free_mb": 128.5,
    "disk_free_mb": 2048.0,
    "uptime_seconds": 86400,
    "temperature_celsius": 45
  }
}
```

**Status Codes**:
- `200 OK`: Health check successful
- `503 Service Unavailable`: Server in degraded state
- `500 Internal Server Error`: Critical server error

### Configuration Schema

#### Monitor Configuration (`monitor.yaml`)

```yaml
# Complete configuration schema with defaults
monitor:
  health_check:
    interval_s: 30                    # Health check frequency
    render_probe_interval_s: 60       # HTML render check frequency
    x_health_interval_s: 120          # X session check frequency
    max_retries: 3                    # Retries before escalation
    request_timeout_s: 6              # HTTP request timeout
    base_url: "http://127.0.0.1:8080" # Health endpoint URL
    render_marker: 'name="calendarbot-ready"' # HTML marker to find

  thresholds:
    refresh_miss_factor: 2            # Refresh staleness multiplier
    render_fail_count: 2              # Render failures before action
    max_browser_restarts_per_hour: 4  # Browser restart rate limit
    max_service_restarts_per_hour: 2  # Service restart rate limit
    max_reboots_per_day: 1           # Reboot rate limit
    recovery_cooldown_s: 60          # Minimum time between actions

  commands:
    browser_detect_cmd: "pgrep -f 'chromium.*--kiosk'"
    browser_launch_cmd: "export DISPLAY=:0 && chromium --kiosk ..."
    browser_stop_cmd: "pkill -TERM -f 'chromium.*--kiosk'"
    x_health_cmd: "DISPLAY=:0 xdpyinfo >/dev/null 2>&1"
    kiosk_systemd_unit: "calendarbot-kiosk@{user}.service"

  logging:
    local_log_dir: "/var/log/calendarbot-watchdog"
    log_level: "INFO"
    max_log_size_mb: 2
    log_files_to_keep: 7
    json_logging: true
    journal_logging: true

  resource_limits:
    min_free_mem_kb: 60000           # Memory threshold for degradation
    max_load_1m: 1.5                 # CPU load threshold
    degradation_factor: 2.0          # Interval multiplier under load
    auto_throttle: true              # Enable automatic throttling

  remote:
    webhook_enabled: false           # Enable webhook notifications
    webhook_url: ""                  # Webhook endpoint URL
    max_webhooks_per_hour: 2         # Webhook rate limit
    webhook_timeout_s: 10            # Webhook request timeout
    include_diagnostics: true        # Include system data in payload

  state:
    state_file: "/var/local/calendarbot-watchdog/state.json"
    lock_file: "/tmp/calendarbot-watchdog.lock"
    lock_timeout_s: 30

  recovery:
    retry_intervals: [10, 20, 40]    # Retry backoff intervals (seconds)
    browser_restart:
      term_grace_period_s: 8         # Grace period for TERM signal
      restart_verification_delay_s: 30
    x_restart:
      restart_cmd: "systemctl --user restart graphical-session.target"
      verification_delay_s: 45
    service_restart:
      verification_delay_s: 60
      max_wait_s: 120
    reboot:
      reboot_delay_s: 30             # Delay before reboot (for log shipping)
      reboot_cmd: "sudo /sbin/reboot"
```

### File Locations and Directory Structure

```
/etc/calendarbot-monitor/
├── monitor.yaml                     # Main configuration file
└── monitor.conf                     # Environment overrides (optional)

/usr/local/bin/
└── calendarbot-watchdog            # Main watchdog script

/opt/calendarbot/kiosk/
├── scripts/
│   ├── log-shipper.sh              # Remote log shipping
│   ├── log-aggregator.sh           # Daily/weekly reports
│   ├── critical-event-filter.sh    # Event filtering
│   ├── monitoring-status.sh        # Status dashboard
│   ├── launch-browser.sh           # Browser launcher
│   └── cleanup-port.sh             # Port cleanup utility
├── config/
│   ├── monitor.yaml                # Configuration template
│   ├── rsyslog-calendarbot.conf    # Rsyslog configuration
│   └── logrotate-calendarbot-watchdog # Log rotation
└── service/
    └── calendarbot-kiosk-watchdog@.service # Systemd service

/var/log/calendarbot-watchdog/
├── watchdog.log                    # Main watchdog log
├── watchdog.log.1                  # Rotated logs
└── ...

/var/log/calendarbot/
├── server.log                      # Server component logs
├── watchdog.log                    # Watchdog component logs
├── critical.log                    # Critical events only
└── monitoring-events.log           # Structured monitoring events

/var/local/calendarbot-watchdog/
├── state.json                      # Persistent state
├── reports/
│   ├── daily_YYYY-MM-DD.json      # Daily reports
│   ├── weekly_YYYY-MM-DD_to_YYYY-MM-DD.json # Weekly reports
│   └── current_status.json        # Latest status
└── cache/
    └── status-cache.json           # Status cache
```

### Systemd Service Dependencies

```ini
# Service dependency chain
calendarbot-kiosk-watchdog@pi.service
├── Requires: network-online.target
├── After: network-online.target
├── PartOf: calendarbot-kiosk@pi.service
└── Manages: calendarbot-kiosk@pi.service

calendarbot-kiosk@pi.service
├── Requires: graphical-session.target
├── After: graphical-session.target
└── Type: simple

# Service execution order:
# 1. network-online.target
# 2. graphical-session.target  
# 3. calendarbot-kiosk@pi.service
# 4. calendarbot-kiosk-watchdog@pi.service
```

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `CALENDARBOT_DEBUG` | `false` | Enable debug logging |
| `CALENDARBOT_LOG_LEVEL` | `INFO` | Override log level |
| `CALENDARBOT_WATCHDOG_DEBUG` | `false` | Watchdog debug mode |
| `CALENDARBOT_WATCHDOG_DISABLED` | `false` | Disable recovery actions |
| `CALENDARBOT_WATCHDOG_DEGRADED` | `false` | Force degraded mode |
| `CALENDARBOT_LOG_SHIPPER_ENABLED` | `false` | Enable log shipping |
| `CALENDARBOT_WEBHOOK_URL` | - | Webhook endpoint URL |
| `CALENDARBOT_WEBHOOK_TOKEN` | - | Bearer token for webhook |
| `CALENDARBOT_WEBHOOK_TIMEOUT` | `10` | Webhook timeout (seconds) |
| `CALENDARBOT_WEBHOOK_INSECURE` | `false` | Disable SSL verification |
| `CALENDARBOT_REMOTE_SYSLOG_SERVER` | - | Remote syslog server |
| `CALENDARBOT_REMOTE_SYSLOG_PORT` | `514` | Remote syslog port |
| `CALENDARBOT_AGGREGATOR_RETENTION_DAYS` | `30` | Report retention |
| `CALENDARBOT_STATUS_CACHE` | `true` | Enable status caching |

---

## Troubleshooting Guide

### Common Deployment Issues

#### 1. Watchdog Service Won't Start

**Symptoms**:
```bash
$ sudo systemctl status calendarbot-kiosk-watchdog@pi.service
● calendarbot-kiosk-watchdog@pi.service - CalendarBot Kiosk Watchdog for user pi
   Loaded: loaded (/etc/systemd/system/calendarbot-kiosk-watchdog@.service; enabled; vendor preset: enabled)
   Active: failed (Result: exit-code) since Mon 2024-01-15 10:30:00 GMT; 1min ago
  Process: 1234 ExecStart=/usr/bin/python3 /usr/local/bin/calendarbot-watchdog --config /etc/calendarbot-monitor/monitor.yaml --user pi (code=exited, status=1)
```

**Common Causes & Solutions**:

```bash
# Check Python dependencies
python3 -c "import yaml" 2>/dev/null || echo "PyYAML missing"
# Solution: pip3 install PyYAML

# Check configuration file
sudo python3 -c "import yaml; yaml.safe_load(open('/etc/calendarbot-monitor/monitor.yaml'))"
# Solution: Fix YAML syntax errors

# Check permissions
ls -la /etc/calendarbot-monitor/monitor.yaml
# Solution: sudo chmod 640 /etc/calendarbot-monitor/monitor.yaml

# Check log directories
ls -la /var/log/calendarbot-watchdog/
# Solution: sudo mkdir -p /var/log/calendarbot-watchdog && sudo chown pi:pi /var/log/calendarbot-watchdog
```

#### 2. Health Endpoint Not Reachable

**Symptoms**:
```bash
$ curl http://127.0.0.1:8080/api/health
curl: (7) Failed to connect to 127.0.0.1 port 8080: Connection refused
```

**Diagnosis**:
```bash
# Check if CalendarBot_Lite is running
ps aux | grep calendarbot
sudo systemctl status calendarbot-kiosk@pi.service

# Check port usage
sudo netstat -tlnp | grep 8080
sudo lsof -i :8080

# Check CalendarBot_Lite logs
sudo journalctl -u calendarbot-kiosk@pi.service -f --lines=50
```

**Solutions**:
```bash
# Start CalendarBot_Lite service
sudo systemctl start calendarbot-kiosk@pi.service

# Fix port conflicts
/opt/calendarbot/kiosk/scripts/cleanup-port.sh 8080

# Check Python virtual environment
cd /opt/calendarbot && . venv/bin/activate && python -m calendarbot_lite --port 8080
```

#### 3. Permission Errors

**Symptoms**:
```
PermissionError: [Errno 13] Permission denied: '/var/log/calendarbot-watchdog/watchdog.log'
```

**Solution**:
```bash
# Fix log directory permissions
sudo chown -R pi:pi /var/log/calendarbot-watchdog
sudo chmod -R 755 /var/log/calendarbot-watchdog

# Fix state directory permissions
sudo chown -R pi:pi /var/local/calendarbot-watchdog
sudo chmod -R 700 /var/local/calendarbot-watchdog

# Check sudoers configuration
sudo visudo /etc/sudoers.d/calendarbot-watchdog
```

#### 4. Recovery Actions Not Working

**Symptoms**:
- Browser crashes are not automatically restarted
- Rate limiting prevents recovery actions

**Diagnosis**:
```bash
# Check state file for rate limiting
cat /var/local/calendarbot-watchdog/state.json | jq '.'

# Check recent recovery attempts
sudo journalctl -u calendarbot-kiosk-watchdog@pi.service | grep -E '(recovery|restart|reboot)'

# Verify sudo permissions
sudo -u pi sudo /sbin/reboot --help >/dev/null 2>&1 && echo "Reboot permission OK" || echo "Reboot permission FAILED"
```

**Solutions**:
```bash
# Reset rate limiting
sudo rm -f /var/local/calendarbot-watchdog/state.json
sudo systemctl restart calendarbot-kiosk-watchdog@pi.service

# Test recovery manually
sudo -u pi /usr/local/bin/calendarbot-watchdog --config /etc/calendarbot-monitor/monitor.yaml --user pi

# Verify browser launch command
export DISPLAY=:0
cd /home/pi
# Run browser_launch_cmd from monitor.yaml manually
```

### Performance Problems and Optimization

#### 1. High Memory Usage

**Symptoms**:
```bash
$ free -h
               total        used        free      shared  buff/cache   available
Mem:           427M        380M         20M        12M        26M         15M
```

**Monitoring**:
```bash
# Monitor memory usage
watch -n 5 'free -h && ps aux --sort=-%mem | head -10'

# Check monitoring resource usage
ps aux | grep -E '(calendarbot|watchdog)'
```

**Optimization**:
```bash
# Enable degraded mode
export CALENDARBOT_WATCHDOG_DEGRADED=true

# Reduce monitoring frequency
# Edit /etc/calendarbot-monitor/monitor.yaml:
# health_check.interval_s: 60
# render_probe_interval_s: 120

# Reduce log retention
# logging.log_files_to_keep: 3
# logging.max_log_size_mb: 1
```

#### 2. High CPU Load

**Symptoms**:
```bash
$ uptime
 10:30:01 up 1 day,  2:34,  1 user,  load average: 2.45, 2.20, 1.95
```

**Diagnosis**:
```bash
# Identify CPU-intensive processes
top -o %CPU

# Monitor system load
iostat -x 1

# Check for CPU throttling
vcgencmd measure_temp
vcgencmd get_throttled
```

**Solutions**:
```bash
# Enable automatic throttling
# In monitor.yaml:
# resource_limits.auto_throttle: true
# resource_limits.max_load_1m: 1.5

# Reduce browser resource usage
# Verify browser launch with low-end optimizations in .xinitrc:
# --enable-low-end-device-mode
# --disable-gpu-compositing
# --disable-vulkan
```

### Network Connectivity Issues

#### 1. Webhook Shipping Failures

**Symptoms**:
```bash
$ /opt/calendarbot/kiosk/scripts/log-shipper.sh test
[ERROR] Failed to ship event after 3 attempts
```

**Diagnosis**:
```bash
# Test network connectivity
ping -c 3 google.com
curl -I https://httpbin.org/get

# Test webhook endpoint
curl -v -X POST "$CALENDARBOT_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CALENDARBOT_WEBHOOK_TOKEN" \
  -d '{"test": true}'

# Check DNS resolution
nslookup $(echo "$CALENDARBOT_WEBHOOK_URL" | sed 's|https\?://||' | cut -d/ -f1)
```

**Solutions**:
```bash
# Configure DNS
echo "nameserver 8.8.8.8" | sudo tee -a /etc/resolv.conf

# Use HTTP for testing (not recommended for production)
export CALENDARBOT_WEBHOOK_INSECURE=true

# Test with local webhook receiver
python3 -m http.server 8000 &
export CALENDARBOT_WEBHOOK_URL="http://127.0.0.1:8000/webhook"
```

#### 2. Syslog Forwarding Issues

**Diagnosis**:
```bash
# Test syslog forwarding
logger -p daemon.info "Test message from CalendarBot"

# Check rsyslog configuration
sudo rsyslog -N1 -f /etc/rsyslog.conf

# Monitor rsyslog errors
sudo journalctl -u rsyslog -f
```

**Solutions**:
```bash
# Restart rsyslog
sudo systemctl restart rsyslog

# Test with netcat
echo "test message" | nc -u syslog.example.com 514

# Check firewall
sudo ufw status
sudo iptables -L OUTPUT
```

### Log Analysis and Interpretation

#### 1. Understanding Event Patterns

**Critical Event Analysis**:
```bash
# Find all critical events in last 24 hours
sudo journalctl -u calendarbot-kiosk-watchdog@pi.service --since "24 hours ago" | \
  grep -E '(CRITICAL|recovery|reboot)'

# Analyze error patterns
cat /var/log/calendarbot-watchdog/watchdog.log | \
  jq 'select(.level == "ERROR" or .level == "CRITICAL") | {timestamp, event, message}'
```

**Recovery Pattern Analysis**:
```bash
# Generate recovery effectiveness report
/opt/calendarbot/kiosk/scripts/log-aggregator.sh daily $(date +%Y-%m-%d)
cat "/var/local/calendarbot-watchdog/reports/daily_$(date +%Y-%m-%d).json" | \
  jq '.patterns.recovery_effectiveness'
```

#### 2. Performance Trend Analysis

```bash
# Generate weekly trend report
/opt/calendarbot/kiosk/scripts/log-aggregator.sh weekly $(date -d 'last monday' +%Y-%m-%d)

# Extract system health trends
cat "/var/local/calendarbot-watchdog/reports/weekly_*.json" | \
  jq '.patterns.system_health_trends'

# Monitor resource usage trends
/opt/calendarbot/kiosk/scripts/monitoring-status.sh status /tmp/trends.json
cat /tmp/trends.json | jq '.trends'
```

### Recovery Process Debugging

#### 1. Debug Recovery Escalation

**Enable Debug Mode**:
```bash
# Stop service and run in debug mode
sudo systemctl stop calendarbot-kiosk-watchdog@pi.service
sudo CALENDARBOT_WATCHDOG_DEBUG=true \
  /usr/local/bin/calendarbot-watchdog \
  --config /etc/calendarbot-monitor/monitor.yaml \
  --user pi
```

**Monitor Recovery Steps**:
```bash
# Watch recovery in real-time
sudo journalctl -u calendarbot-kiosk-watchdog@pi.service -f | \
  grep -E '(recovery|escalate|restart|reboot)' --color=always

# Check state transitions
watch -n 2 'cat /var/local/calendarbot-watchdog/state.json | jq .'
```

#### 2. Test Recovery Components

**Test Individual Recovery Levels**:
```bash
# Level 1: Browser restart
sudo pkill -f chromium
/opt/calendarbot/kiosk/scripts/launch-browser.sh

# Level 2: X session restart
sudo systemctl --user restart graphical-session.target

# Level 3: Service restart
sudo systemctl restart calendarbot-kiosk@pi.service

# Level 4: System reboot (use with caution)
# sudo /sbin/reboot
```

**Verify Recovery Commands**:
```bash
# Test browser detection
eval "$(grep browser_detect_cmd /etc/calendarbot-monitor/monitor.yaml | cut -d: -f2-)"

# Test X server health
DISPLAY=:0 xdpyinfo >/dev/null 2>&1 && echo "X server OK" || echo "X server FAILED"

# Test service status
systemctl is-active calendarbot-kiosk@pi.service
```

---

## Advanced Topics

### Custom Recovery Strategies

#### Creating Custom Recovery Scripts

```bash
# Create custom recovery script
sudo tee /opt/calendarbot/kiosk/scripts/custom-recovery.sh << 'EOF'
#!/bin/bash
# Custom recovery script for specific hardware or environment

set -euo pipefail

RECOVERY_LEVEL="$1"
USER="$2"

case "$RECOVERY_LEVEL" in
    "browser")
        echo "Custom browser recovery for $USER"
        # Custom browser restart logic
        pkill -f chromium || true
        sleep 5
        sudo -u "$USER" DISPLAY=:0 chromium --kiosk --custom-flags &
        ;;
    "display")
        echo "Custom display recovery"
        # Reset display configuration
        sudo -u "$USER" DISPLAY=:0 xrandr --auto
        ;;
    *)
        echo "Unknown recovery level: $RECOVERY_LEVEL"
        exit 1
        ;;
esac
EOF

sudo chmod +x /opt/calendarbot/kiosk/scripts/custom-recovery.sh
```

#### Integration with Monitor Configuration

```yaml
# Add custom commands to monitor.yaml
monitor:
  commands:
    # Override browser restart with custom script
    browser_launch_cmd: "/opt/calendarbot/kiosk/scripts/custom-recovery.sh browser {user}"
    
    # Add custom display reset command
    display_reset_cmd: "/opt/calendarbot/kiosk/scripts/custom-recovery.sh display {user}"
```

### External Monitoring System Integration

#### Prometheus + Grafana Setup

1. **Install Prometheus**:
```bash
# Download and install Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-armv7.tar.gz
tar xzf prometheus-2.40.0.linux-armv7.tar.gz
sudo mv prometheus-2.40.0.linux-armv7 /opt/prometheus
sudo ln -s /opt/prometheus/prometheus /usr/local/bin/

# Create Prometheus configuration
sudo tee /etc/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'calendarbot'
    static_configs:
      - targets: ['localhost:9100']
    metrics_path: '/metrics'
    scrape_interval: 30s
    
  - job_name: 'calendarbot-file'
    file_sd_configs:
      - files:
          - '/var/lib/prometheus/calendarbot.prom'
        refresh_interval: 60s
EOF

# Create systemd service for Prometheus
sudo tee /etc/systemd/system/prometheus.service << 'EOF'
[Unit]
Description=Prometheus Server
After=network-online.target

[Service]
Type=simple
User=prometheus
Group=prometheus
ExecStart=/opt/prometheus/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/var/lib/prometheus \
  --web.console.templates=/opt/prometheus/consoles \
  --web.console.libraries=/opt/prometheus/console_libraries \
  --web.listen-address=0.0.0.0:9090

[Install]
WantedBy=multi-user.target
EOF

# Create prometheus user and directories
sudo useradd -r -s /bin/false prometheus
sudo mkdir -p /var/lib/prometheus
sudo chown prometheus:prometheus /var/lib/prometheus

# Enable and start Prometheus
sudo systemctl enable prometheus
sudo systemctl start prometheus
```

2. **Configure CalendarBot Metrics Export**:
```bash
# Add metrics generation to crontab
(crontab -l 2>/dev/null || true; echo "*/5 * * * * /opt/calendarbot/kiosk/scripts/monitoring-status.sh metrics /var/lib/prometheus/calendarbot.prom") | crontab -

# Test metrics generation
/opt/calendarbot/kiosk/scripts/monitoring-status.sh metrics /tmp/test-metrics.prom
cat /tmp/test-metrics.prom
```

3. **Install Grafana**:
```bash
# Add Grafana repository
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list

# Install Grafana
sudo apt update
sudo apt install grafana

# Enable and start Grafana
sudo systemctl enable grafana-server
sudo systemctl start grafana-server

# Access Grafana at http://pi-ip:3000 (admin/admin)
```

4. **Create CalendarBot Dashboard**:
```json
{
  "dashboard": {
    "id": null,
    "title": "CalendarBot Pi Zero 2 Monitoring",
    "tags": ["calendarbot", "raspberry-pi"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "System Health",
        "type": "stat",
        "targets": [
          {
            "expr": "calendarbot_up",
            "legendFormat": "Server Status"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                {"color": "red", "value": 0},
                {"color": "green", "value": 1}
              ]
            }
          }
        }
      },
      {
        "id": 2,
        "title": "Resource Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "calendarbot_memory_usage_percent",
            "legendFormat": "Memory %"
          },
          {
            "expr": "calendarbot_cpu_load_1m",
            "legendFormat": "CPU Load"
          }
        ]
      },
      {
        "id": 3,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "increase(calendarbot_errors_total_24h[1h])",
            "legendFormat": "Errors/hour"
          },
          {
            "expr": "increase(calendarbot_recovery_actions_24h[1h])",
            "legendFormat": "Recovery Actions/hour"
          }
        ]
      }
    ],
    "time": {
      "from": "now-24h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

#### Datadog Integration

```bash
# Install Datadog agent
DD_API_KEY=your_api_key bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script.sh)"

# Configure custom metrics
sudo tee /etc/datadog-agent/conf.d/calendarbot.yaml << 'EOF'
init_config:

instances:
  - name: calendarbot
    url: http://127.0.0.1:8080/api/health
    timeout: 5
    tags:
      - service:calendarbot
      - env:production
      - device:pi-zero-2
EOF

# Restart Datadog agent
sudo systemctl restart datadog-agent
```

#### New Relic Integration

```bash
# Install New Relic infrastructure agent
curl -Ls https://download.newrelic.com/install/newrelic-cli/scripts/install.sh | bash
sudo NEW_RELIC_API_KEY=your_api_key NEW_RELIC_ACCOUNT_ID=your_account_id /usr/local/bin/newrelic install

# Configure custom monitoring
sudo tee /etc/newrelic-infra/integrations.d/calendarbot.yml << 'EOF'
integrations:
  - name: nri-http
    config:
      urls:
        - name: calendarbot-health
          url: http://127.0.0.1:8080/api/health
          method: GET
    interval: 30s
EOF
```

### Scaling Considerations

#### Multi-Device Management

For managing multiple Pi Zero 2 kiosk deployments:

1. **Centralized Configuration Management**:
```bash
# Use Ansible for configuration management
# Create inventory file
cat > inventory.ini << 'EOF'
[calendarbot_kiosks]
kiosk-01 ansible_host=192.168.1.101
kiosk-02 ansible_host=192.168.1.102
kiosk-03 ansible_host=192.168.1.103

[calendarbot_kiosks:vars]
ansible_user=pi
ansible_ssh_private_key_file=~/.ssh/pi_key
EOF

# Create Ansible playbook
cat > deploy-monitoring.yml << 'EOF'
---
- hosts: calendarbot_kiosks
  become: yes
  tasks:
    - name: Copy monitoring configuration
      copy:
        src: kiosk/config/monitor.yaml
        dest: /etc/calendarbot-monitor/monitor.yaml
        owner: root
        group: pi
        mode: '0640'
      
    - name: Restart watchdog service
      systemd:
        name: calendarbot-kiosk-watchdog@pi.service
        state: restarted
        enabled: yes
EOF

# Deploy to all devices
ansible-playbook -i inventory.ini deploy-monitoring.yml
```

2. **Centralized Logging and Monitoring**:
```bash
# Configure all devices to ship logs to central server
export CALENDARBOT_WEBHOOK_URL="https://central-monitoring.example.com/api/events"
export CALENDARBOT_REMOTE_SYSLOG_SERVER="logs.example.com"

# Use environment file for consistency
sudo tee /etc/calendarbot-monitor/monitor.conf << 'EOF'
CALENDARBOT_WEBHOOK_URL=https://central-monitoring.example.com/api/events
CALENDARBOT_WEBHOOK_TOKEN=shared-secure-token
CALENDARBOT_REMOTE_SYSLOG_SERVER=logs.example.com
CALENDARBOT_LOG_SHIPPER_ENABLED=true
EOF
```

3. **Device Health Dashboard**:
```python
# Central monitoring dashboard (Flask example)
from flask import Flask, jsonify, render_template
import requests
import concurrent.futures

app = Flask(__name__)

DEVICES = [
    {'name': 'Kiosk-01', 'ip': '192.168.1.101'},
    {'name': 'Kiosk-02', 'ip': '192.168.1.102'},
    {'name': 'Kiosk-03', 'ip': '192.168.1.103'},
]

def check_device_health(device):
    try:
        response = requests.get(f"http://{device['ip']}:8080/api/health", timeout=5)
        return {
            'name': device['name'],
            'status': 'online',
            'health': response.json()
        }
    except:
        return {
            'name': device['name'],
            'status': 'offline',
            'health': None
        }

@app.route('/api/fleet-status')
def fleet_status():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(check_device_health, device) for device in DEVICES]
        results = [future.result() for future in futures]
    
    return jsonify({
        'devices': results,
        'summary': {
            'total': len(results),
            'online': len([r for r in results if r['status'] == 'online']),
            'offline': len([r for r in results if r['status'] == 'offline'])
        }
    })
```

#### Performance Optimization for Scale

1. **Reduce Monitoring Frequency**:
```yaml
# For deployments with 10+ devices
monitor:
  health_check:
    interval_s: 60                    # Increased from 30s
    render_probe_interval_s: 300      # Increased from 60s
    x_health_interval_s: 600          # Increased from 120s
```

2. **Optimize Log Shipping**:
```bash
# Batch log shipping to reduce network overhead
export CALENDARBOT_LOG_SHIPPER_BATCH_SIZE=10
export CALENDARBOT_LOG_SHIPPER_BATCH_TIMEOUT=300
```

3. **Resource Monitoring**:
```bash
# Monitor resource usage across fleet
for device in 192.168.1.{101..103}; do
  echo "=== $device ==="
  ssh pi@$device 'free -h && uptime && df -h / | tail -1'
done
```

### Security Hardening

#### Network Security

1. **Firewall Configuration**:
```bash
# Enable UFW firewall
sudo ufw enable

# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8080/tcp  # CalendarBot (local only)
sudo ufw deny 8080 from any to any port 8080  # Block external access
sudo ufw allow from 192.168.1.0/24 to any port 8080  # Allow local network only

# Allow outgoing for updates and monitoring
sudo ufw allow out 80/tcp   # HTTP
sudo ufw allow out 443/tcp  # HTTPS
sudo ufw allow out 53       # DNS

# Check firewall status
sudo ufw status verbose
```

2. **SSH Hardening**:
```bash
# Configure SSH security
sudo tee -a /etc/ssh/sshd_config << 'EOF'
# CalendarBot security hardening
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
X11Forwarding no
AllowUsers pi
Protocol 2
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

sudo systemctl restart sshd
```

3. **HTTPS for Webhooks**:
```bash
# Always use HTTPS for webhook endpoints
export CALENDARBOT_WEBHOOK_URL="https://secure-monitoring.example.com/webhook"
export CALENDARBOT_WEBHOOK_INSECURE=false

# Use certificate pinning for high security
export CALENDARBOT_WEBHOOK_CERT_PIN="sha256:base64-encoded-cert-hash"
```

#### Application Security

1. **File Permissions**:
```bash
# Secure configuration files
sudo chmod 640 /etc/calendarbot-monitor/monitor.yaml
sudo chown root:pi /etc/calendarbot-monitor/monitor.yaml

# Secure log directories
sudo chmod 750 /var/log/calendarbot-watchdog
sudo chmod 700 /var/local/calendarbot-watchdog

# Secure scripts
sudo chmod 755 /opt/calendarbot/kiosk/scripts/*.sh
sudo chown root:root /opt/calendarbot/kiosk/scripts/*.sh
```

2. **Sudo Restrictions**:
```bash
# Minimal sudo privileges
sudo tee /etc/sudoers.d/calendarbot-watchdog << 'EOF'
# CalendarBot watchdog - minimal required privileges
pi ALL=NOPASSWD: /sbin/reboot
pi ALL=NOPASSWD: /bin/systemctl restart calendarbot-kiosk@pi.service
pi ALL=NOPASSWD: /bin/systemctl restart graphical-session.target
pi ALL=NOPASSWD: /bin/systemctl status calendarbot-*

# Deny everything else
pi ALL=!/bin/su, !/usr/bin/sudo, !/bin/bash, !/bin/sh
EOF
```

3. **Process Isolation**:
```bash
# Run watchdog with restricted capabilities
# Add to systemd service:
sudo tee -a /etc/systemd/system/calendarbot-kiosk-watchdog@.service << 'EOF'

# Additional security restrictions
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictRealtime=yes
RestrictNamespaces=yes
LockPersonality=yes
MemoryDenyWriteExecute=yes
EOF

sudo systemctl daemon-reload
```

#### Data Protection

1. **Log Encryption**:
```bash
# Encrypt sensitive logs
sudo apt install gnupg

# Create encryption key
gpg --gen-key --batch << 'EOF'
Key-Type: RSA
Key-Length: 2048
Name-Real: CalendarBot Monitoring
Name-Email: monitoring@example.com
Expire-Date: 1y
%no-protection
%commit
EOF

# Encrypt critical logs
gpg --encrypt --recipient monitoring@example.com /var/log/calendarbot/critical.log
```

2. **Secure Token Storage**:
```bash
# Store webhook tokens securely
sudo mkdir -p /etc/calendarbot-monitor/secrets
sudo chmod 700 /etc/calendarbot-monitor/secrets

# Store token in protected file
echo "your-webhook-token" | sudo tee /etc/calendarbot-monitor/secrets/webhook_token
sudo chmod 600 /etc/calendarbot-monitor/secrets/webhook_token
sudo chown root:root /etc/calendarbot-monitor/secrets/webhook_token

# Reference in environment
export CALENDARBOT_WEBHOOK_TOKEN="$(sudo cat /etc/calendarbot-monitor/secrets/webhook_token)"
```

### Backup and Disaster Recovery

#### Configuration Backup

1. **Automated Configuration Backup**:
```bash
#!/bin/bash
# Create configuration backup script
sudo tee /opt/calendarbot/kiosk/scripts/backup-config.sh << 'EOF'
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/var/backups/calendarbot"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/calendarbot_config_$TIMESTAMP.tar.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create configuration backup
tar -czf "$BACKUP_FILE" \
    /etc/calendarbot-monitor/ \
    /etc/systemd/system/calendarbot-*.service \
    /etc/sudoers.d/calendarbot-watchdog \
    /etc/rsyslog.d/50-calendarbot.conf \
    /etc/logrotate.d/calendarbot-watchdog \
    /opt/calendarbot/kiosk/scripts/ \
    2>/dev/null || true

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "calendarbot_config_*.tar.gz" -mtime +7 -delete

echo "Configuration backup created: $BACKUP_FILE"
EOF

sudo chmod +x /opt/calendarbot/kiosk/scripts/backup-config.sh

# Add to crontab for daily backup
echo "0 2 * * * /opt/calendarbot/kiosk/scripts/backup-config.sh" | sudo crontab -
```

2. **State and Log Backup**:
```bash
#!/bin/bash
# Create state backup script
sudo tee /opt/calendarbot/kiosk/scripts/backup-state.sh << 'EOF'
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/var/backups/calendarbot"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
STATE_BACKUP="$BACKUP_DIR/calendarbot_state_$TIMESTAMP.tar.gz"

# Backup state and recent logs
tar -czf "$STATE_BACKUP" \
    /var/local/calendarbot-watchdog/ \
    /var/log/calendarbot-watchdog/ \
    --exclude='*.log.*' \
    2>/dev/null || true

# Keep only last 3 days of state backups
find "$BACKUP_DIR" -name "calendarbot_state_*.tar.gz" -mtime +3 -delete

echo "State backup created: $STATE_BACKUP"
EOF

sudo chmod +x /opt/calendarbot/kiosk/scripts/backup-state.sh

# Add to crontab for hourly state backup
echo "0 * * * * /opt/calendarbot/kiosk/scripts/backup-state.sh" | sudo crontab -
```

#### Disaster Recovery Procedures

1. **Quick Recovery Script**:
```bash
#!/bin/bash
# Emergency recovery script
sudo tee /opt/calendarbot/kiosk/scripts/emergency-recovery.sh << 'EOF'
#!/bin/bash
set -euo pipefail

echo "=== CalendarBot Emergency Recovery ==="

# Step 1: Stop all services
echo "Stopping services..."
sudo systemctl stop calendarbot-kiosk-watchdog@pi.service || true
sudo systemctl stop calendarbot-kiosk@pi.service || true

# Step 2: Clean up processes
echo "Cleaning up processes..."
sudo pkill -f chromium || true
sudo pkill -f calendarbot || true

# Step 3: Clear temporary state
echo "Clearing temporary state..."
sudo rm -f /var/local/calendarbot-watchdog/state.json
sudo rm -f /tmp/calendarbot-*

# Step 4: Reset X session
echo "Resetting X session..."
sudo pkill -f matchbox-window-manager || true
sudo systemctl --user restart graphical-session.target || true

# Step 5: Wait and restart services
echo "Restarting services..."
sleep 10
sudo systemctl start calendarbot-kiosk@pi.service
sleep 30
sudo systemctl start calendarbot-kiosk-watchdog@pi.service

# Step 6: Verify recovery
echo "Verifying recovery..."
sleep 30
if curl -s http://127.0.0.1:8080/api/health >/dev/null; then
    echo "✓ Recovery successful - health endpoint responsive"
else
    echo "✗ Recovery failed - health endpoint not responsive"
    exit 1
fi

echo "=== Recovery Complete ==="
EOF

sudo chmod +x /opt/calendarbot/kiosk/scripts/emergency-recovery.sh
```

2. **Configuration Restore**:
```bash
#!/bin/bash
# Configuration restore script
sudo tee /opt/calendarbot/kiosk/scripts/restore-config.sh << 'EOF'
#!/bin/bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    exit 1
fi

BACKUP_FILE="$1"

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Restoring configuration from: $BACKUP_FILE"

# Stop services
sudo systemctl stop calendarbot-kiosk-watchdog@pi.service || true
sudo systemctl stop calendarbot-kiosk@pi.service || true

# Restore configuration
cd /
sudo tar -xzf "$BACKUP_FILE"

# Reload systemd and restart services
sudo systemctl daemon-reload
sudo systemctl restart rsyslog

# Start services
sudo systemctl start calendarbot-kiosk@pi.service
sudo systemctl start calendarbot-kiosk-watchdog@pi.service

echo "Configuration restored successfully"
EOF

sudo chmod +x /opt/calendarbot/kiosk/scripts/restore-config.sh
```

3. **Complete System Rebuild**:
```bash
#!/bin/bash
# Complete system rebuild from backup
sudo tee /opt/calendarbot/kiosk/scripts/rebuild-system.sh << 'EOF'
#!/bin/bash
set -euo pipefail

echo "=== CalendarBot System Rebuild ==="
echo "WARNING: This will completely rebuild the monitoring system"
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Backup current state
echo "Creating emergency backup..."
/opt/calendarbot/kiosk/scripts/backup-config.sh
/opt/calendarbot/kiosk/scripts/backup-state.sh

# Stop and disable services
echo "Stopping services..."
sudo systemctl stop calendarbot-kiosk-watchdog@pi.service || true
sudo systemctl disable calendarbot-kiosk-watchdog@pi.service || true

# Remove all monitoring components
echo "Removing existing installation..."
sudo rm -rf /etc/calendarbot-monitor/
sudo rm -f /etc/systemd/system/calendarbot-kiosk-watchdog@.service
sudo rm -f /etc/sudoers.d/calendarbot-watchdog
sudo rm -f /etc/rsyslog.d/50-calendarbot.conf
sudo rm -f /etc/logrotate.d/calendarbot-watchdog
sudo rm -rf /opt/calendarbot/kiosk/scripts/
sudo rm -rf /var/log/calendarbot-watchdog/
sudo rm -rf /var/local/calendarbot-watchdog/

# Reinstall from repository
echo "Reinstalling monitoring system..."
cd /opt/calendarbot

# Copy installation files
sudo cp kiosk/scripts/calendarbot-watchdog /usr/local/bin/
sudo chmod +x /usr/local/bin/calendarbot-watchdog

sudo mkdir -p /opt/calendarbot/kiosk/scripts
sudo cp kiosk/scripts/*.sh /opt/calendarbot/kiosk/scripts/
sudo chmod +x /opt/calendarbot/kiosk/scripts/*.sh

sudo cp kiosk/service/calendarbot-kiosk-watchdog@.service /etc/systemd/system/
sudo systemctl daemon-reload

sudo mkdir -p /etc/calendarbot-monitor
sudo cp kiosk/config/monitor.yaml /etc/calendarbot-monitor/
sudo cp kiosk/config/rsyslog-calendarbot.conf /etc/rsyslog.d/50-calendarbot.conf
sudo cp kiosk/config/logrotate-calendarbot-watchdog /etc/logrotate.d/calendarbot-watchdog

# Create directories
sudo mkdir -p /var/log/calendarbot-watchdog
sudo mkdir -p /var/local/calendarbot-watchdog
sudo chown -R pi:pi /var/log/calendarbot-watchdog /var/local/calendarbot-watchdog

# Restore sudo privileges
sudo tee /etc/sudoers.d/calendarbot-watchdog << 'SUDOERS'
pi ALL=NOPASSWD: /sbin/reboot
pi ALL=NOPASSWD: /bin/systemctl restart calendarbot-kiosk@pi.service
pi ALL=NOPASSWD: /bin/systemctl restart graphical-session.target
SUDOERS

# Enable and start services
sudo systemctl enable calendarbot-kiosk-watchdog@pi.service
sudo systemctl restart rsyslog
sudo systemctl start calendarbot-kiosk-watchdog@pi.service

echo "=== System Rebuild Complete ==="
echo "Verifying installation..."

sleep 30
if sudo systemctl is-active calendarbot-kiosk-watchdog@pi.service >/dev/null; then
    echo "✓ Watchdog service is running"
else
    echo "✗ Watchdog service failed to start"
    sudo systemctl status calendarbot-kiosk-watchdog@pi.service
fi

if curl -s http://127.0.0.1:8080/api/health >/dev/null; then
    echo "✓ Health endpoint is responsive"
else
    echo "✗ Health endpoint is not responsive"
fi

echo "Rebuild complete. Check logs for any issues."
EOF

sudo chmod +x /opt/calendarbot/kiosk/scripts/rebuild-system.sh
```

#### Remote Backup Integration

```bash
# Configure remote backup to cloud storage
# Example: AWS S3 backup
sudo apt install awscli

# Configure AWS credentials
aws configure set aws_access_key_id YOUR_ACCESS_KEY
aws configure set aws_secret_access_key YOUR_SECRET_KEY
aws configure set default.region us-west-2

# Automated cloud backup script
sudo tee /opt/calendarbot/kiosk/scripts/cloud-backup.sh << 'EOF'
#!/bin/bash
set -euo pipefail

DEVICE_ID=$(hostname)
BACKUP_BUCKET="calendarbot-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create local backup
/opt/calendarbot/kiosk/scripts/backup-config.sh
CONFIG_BACKUP=$(ls -t /var/backups/calendarbot/calendarbot_config_*.tar.gz | head -1)

# Upload to S3
aws s3 cp "$CONFIG_BACKUP" "s3://$BACKUP_BUCKET/$DEVICE_ID/config/$(basename $CONFIG_BACKUP)"

# Create and upload state backup
/opt/calendarbot/kiosk/scripts/backup-state.sh
STATE_BACKUP=$(ls -t /var/backups/calendarbot/calendarbot_state_*.tar.gz | head -1)
aws s3 cp "$STATE_BACKUP" "s3://$BACKUP_BUCKET/$DEVICE_ID/state/$(basename $STATE_BACKUP)"

echo "Cloud backup completed for device: $DEVICE_ID"
EOF

sudo chmod +x /opt/calendarbot/kiosk/scripts/cloud-backup.sh

# Schedule daily cloud backup
echo "0 3 * * * /opt/calendarbot/kiosk/scripts/cloud-backup.sh" | sudo crontab -
```

---

## Conclusion

This comprehensive monitoring solution provides robust, automated health monitoring and recovery for CalendarBot_Lite deployments on Raspberry Pi Zero 2. The system offers:

- **Reliability**: Multi-level health monitoring with intelligent recovery escalation
- **Efficiency**: Optimized for Pi Zero 2 resource constraints with <30MB memory footprint
- **Observability**: Structured logging with dashboard integration and remote monitoring
- **Maintainability**: Comprehensive documentation, troubleshooting guides, and automated backup

The solution has been designed to minimize manual intervention while providing comprehensive visibility into system health and performance. For production deployments, follow the security hardening guidelines and implement appropriate backup strategies.

For support and updates, refer to the project repository and maintain regular backups of your configuration and state data.