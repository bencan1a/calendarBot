# Section 4: Monitoring & Log Management

Configure comprehensive system monitoring, health checks, log management, and optional remote observability.

**Estimated Time**: 30-45 minutes
**Prerequisites**: Section 1 completed (CalendarBot service running)

---

## What You'll Install

By the end of this section, you'll have:

- ✅ **Health Monitoring** - Real-time status checks and dashboards
- ✅ **Log Management** - Automatic rotation, aggregation, and retention
- ✅ **Structured Logging** - JSON-formatted events with severity filtering (optional)
- ✅ **Monitoring Dashboard** - Prometheus metrics, status API
- ✅ **Remote Observability** - Webhook shipping, external integrations (optional)
- ✅ **Operational Tools** - Log analysis, event tracking, trend reports

**Services Added**: 0-1 (`calendarbot-log-shipper.service`, optional)

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Section 1 completed (CalendarBot service running)
- [ ] At least 500MB free disk space for logs
- [ ] (Optional) Webhook endpoint URL for remote shipping
- [ ] (Optional) Webhook authentication token

---

## Architecture Overview

### Log Flow

```
CalendarBot Services
  ↓
systemd journald
  ↓
┌─────────────────┬──────────────────┬──────────────────┐
│                 │                  │                  │
▼                 ▼                  ▼                  ▼
Local Files    rsyslog (optional)  Aggregator     Shipper (optional)
  ↓                 ↓                  ↓                  ↓
Logrotate      Filtered Logs       Reports         Remote Webhook
  ↓                 ↓                  ↓
Compressed     JSON Parsing       Daily/Weekly
Archives       Severity Filter    Prometheus Metrics
```

### Structured Log Events

All monitoring events use a consistent JSON schema for parsing and analysis:

```json
{
  "timestamp": "2025-11-03T10:30:00.123Z",
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

---

## Step 1: Deploy Logrotate Configuration

Configure automatic log rotation to prevent disk space issues.

```bash
# Deploy logrotate configuration
sudo cp ~/calendarbot/kiosk/config/logrotate-calendarbot-watchdog \
  /etc/logrotate.d/calendarbot-watchdog

# Review configuration
sudo cat /etc/logrotate.d/calendarbot-watchdog
```

### What Gets Rotated

**Watchdog Logs:**
- Path: `/var/log/calendarbot-watchdog/*.log`
- Rotation: Daily or when > 2MB
- Retention: 7 days
- Compression: Enabled (delayed by 1 day)

**State Files:**
- Path: `/var/local/calendarbot-watchdog/*.json`
- Rotation: Weekly or when > 1MB
- Retention: 4 weeks

**Browser Logs:**
- Path: `/home/*/kiosk/*.log`
- Rotation: Daily or when > 5MB
- Retention: 3 days

### Test Logrotate

```bash
# Test configuration (dry run)
sudo logrotate -d /etc/logrotate.d/calendarbot-watchdog

# Force rotation (for testing)
sudo logrotate -f /etc/logrotate.d/calendarbot-watchdog

# Check rotated files
ls -lh /var/log/calendarbot-watchdog/
```

**Expected output:**
```
watchdog.log
watchdog.log.1
watchdog.log.2.gz
```

---

## Step 2: Deploy rsyslog Configuration (Optional)

Install rsyslog for structured JSON logging with severity-based filtering.

### Install rsyslog with JSON Parser

```bash
# Install rsyslog and JSON parser module
sudo apt-get install -y rsyslog rsyslog-mmjsonparse

# Verify installation
rsyslogd -v
```

### Deploy Configuration

```bash
# Create log directory
sudo mkdir -p /var/log/calendarbot
sudo chown syslog:adm /var/log/calendarbot

# Deploy rsyslog configuration
sudo cp ~/calendarbot/kiosk/config/rsyslog-calendarbot.conf \
  /etc/rsyslog.d/50-calendarbot.conf

# Test configuration
sudo rsyslogd -N1

# Restart rsyslog
sudo systemctl restart rsyslog

# Check status
sudo systemctl status rsyslog
```

### Log Files Created

| File | Purpose | Filtering |
|------|---------|-----------|
| `/var/log/calendarbot/server.log` | CalendarBot server logs | All server events |
| `/var/log/calendarbot/watchdog.log` | Watchdog daemon logs | All watchdog events |
| `/var/log/calendarbot/log-shipper.log` | Log shipper logs | Shipping events |
| `/var/log/calendarbot/critical.log` | ERROR/CRITICAL only | Severity ≥ ERROR |
| `/var/log/calendarbot/monitoring-events.log` | Structured JSON events | JSON-formatted only |

### Key Event Codes

Monitoring events follow a structured naming convention:

| Event Code | Component | Description |
|------------|-----------|-------------|
| `health.endpoint.check` | health | Health endpoint validation |
| `health.endpoint.fail` | health | Health endpoint unreachable |
| `render.probe.check` | health | HTML render verification |
| `render.probe.fail` | health | Browser render failure |
| `browser.restart.start` | recovery | Browser restart initiated |
| `browser.restart.complete` | recovery | Browser restart completed |
| `x.restart.start` | recovery | X session restart initiated |
| `service.restart.start` | recovery | Service restart initiated |
| `service.restart.complete` | recovery | Service restart completed |
| `reboot.start` | recovery | System reboot initiated |
| `degraded.mode.active` | watchdog | System under resource pressure |
| `degraded.mode.clear` | watchdog | System resources recovered |

### Test rsyslog

```bash
# Send test log message
logger -t calendarbot-test "Test log entry"

# View in appropriate log file
tail /var/log/calendarbot/server.log

# View all CalendarBot logs
tail -f /var/log/calendarbot/*.log
```

---

## Step 3: Deploy Log Aggregation Scripts

Install scripts for generating daily/weekly reports and monitoring status.

```bash
# Copy scripts to system bin
sudo cp ~/calendarbot/kiosk/scripts/log-aggregator.sh /usr/local/bin/
sudo cp ~/calendarbot/kiosk/scripts/monitoring-status.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/log-aggregator.sh
sudo chmod +x /usr/local/bin/monitoring-status.sh

# Create report directory
sudo mkdir -p /var/local/calendarbot-watchdog/reports
sudo chown bencan:bencan /var/local/calendarbot-watchdog/reports

# Create cache directory (for monitoring status)
sudo mkdir -p /var/local/calendarbot-watchdog/cache
sudo chown bencan:bencan /var/local/calendarbot-watchdog/cache
```

### Test Log Aggregator

```bash
# Generate daily report for today
/usr/local/bin/log-aggregator.sh daily $(date +%Y-%m-%d)

# View report
cat /var/local/calendarbot-watchdog/reports/daily_$(date +%Y-%m-%d).json | jq

# Generate weekly report
/usr/local/bin/log-aggregator.sh weekly $(date -d 'last monday' +%Y-%m-%d)
```

**Report includes:**
- Event counts by component, level, type
- Recovery action statistics
- Error patterns and trends
- System resource metrics

### Test Monitoring Status

```bash
# Generate status file
/usr/local/bin/monitoring-status.sh status /tmp/calendarbot-status.json

# View status
cat /tmp/calendarbot-status.json | jq

# Quick health check (stdout)
/usr/local/bin/monitoring-status.sh health
```

**Example output:**
```json
{
  "timestamp": "2025-11-03T14:30:00Z",
  "status": "healthy",
  "system": {
    "cpu": {"load_1m": 0.42},
    "memory": {"usage_percent": 38, "available_kb": 298000},
    "disk": {"usage_percent": 27}
  },
  "services": {
    "server": {"status": "ok", "reachable": true}
  },
  "events_24h": {
    "total": 142,
    "errors": 1,
    "recovery_actions": 0
  }
}
```

---

## Step 4: Configure Automated Reporting

Set up cron jobs for automatic daily/weekly reports.

```bash
# Edit crontab for user bencan
crontab -e
```

**Add cron jobs:**
```cron
# Daily report at 1 AM
0 1 * * * /usr/local/bin/log-aggregator.sh daily $(date +\%Y-\%m-\%d) >> /var/log/calendarbot-watchdog/aggregator.log 2>&1

# Weekly report on Monday at 2 AM
0 2 * * 1 /usr/local/bin/log-aggregator.sh weekly $(date -d 'last monday' +\%Y-\%m-\%d) >> /var/log/calendarbot-watchdog/aggregator.log 2>&1

# Cleanup old reports daily at 3 AM (30-day retention)
0 3 * * * /usr/local/bin/log-aggregator.sh cleanup >> /var/log/calendarbot-watchdog/aggregator.log 2>&1

# Update monitoring status every 5 minutes
*/5 * * * * /usr/local/bin/monitoring-status.sh status /var/www/html/calendarbot-status.json 2>&1
```

**Save and exit**: `Ctrl+X`, `Y`, `Enter`

**Verify cron jobs:**
```bash
crontab -l
```

---

## Step 5: Configure Remote Log Shipping (Optional)

Set up webhook-based remote log shipping for critical events.

### Prerequisites

- Webhook endpoint URL (e.g., monitoring service, Slack, Discord)
- Authentication token (if required)

### Deploy Log Shipper

```bash
# Copy log shipper script
sudo cp ~/calendarbot/kiosk/scripts/log-shipper.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/log-shipper.sh
```

### Configure Environment Variables

```bash
# Edit system environment file
sudo nano /etc/environment
```

**Add configuration:**
```bash
# Log Shipping Configuration
CALENDARBOT_LOG_SHIPPER_ENABLED=true
CALENDARBOT_WEBHOOK_URL=https://your-monitoring-service.com/webhook
CALENDARBOT_WEBHOOK_TOKEN=your-webhook-bearer-token
CALENDARBOT_WEBHOOK_TIMEOUT=10
CALENDARBOT_WEBHOOK_INSECURE=false
```

**Apply environment:**
```bash
# Reload environment
source /etc/environment

# Verify
echo $CALENDARBOT_WEBHOOK_URL
```

### Test Log Shipper

```bash
# Test webhook connection
/usr/local/bin/log-shipper.sh test
```

**Expected output:**
```
Testing webhook configuration...
✓ Webhook URL configured
✓ Connection successful
✓ Webhook responded with status 200
```

### Create Log Shipper Service

For continuous log shipping from journald:

```bash
# Create systemd service
sudo nano /etc/systemd/system/calendarbot-log-shipper.service
```

**Service contents:**
```ini
[Unit]
Description=CalendarBot Critical Event Log Shipper
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=bencan
EnvironmentFile=/etc/environment
ExecStart=/bin/bash -c 'journalctl -f -u calendarbot-* --output=json | /usr/local/bin/log-shipper.sh stream'
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable calendarbot-log-shipper.service
sudo systemctl start calendarbot-log-shipper.service

# Check status
sudo systemctl status calendarbot-log-shipper.service
```

### What Gets Shipped

**Critical events only:**
- CRITICAL level logs
- ERROR logs with recovery actions
- System reboot events
- Service restart events
- Escalation to higher recovery levels

**Rate limiting:**
- Max 1 ship per 30 minutes per event type
- Prevents flooding webhook endpoint

---

## Step 6: Configure Monitoring Dashboard (Optional)

Expose monitoring status for external dashboards (Grafana, Prometheus, etc.).

### Option A: Web Server Hosting

```bash
# Install nginx (lightweight)
sudo apt-get install -y nginx

# Create status directory
sudo mkdir -p /var/www/html/monitoring

# Update cron to write status here
crontab -e
# Change path to: /var/www/html/monitoring/calendarbot-status.json

# Access via browser
# http://<PI_IP>/monitoring/calendarbot-status.json
```

### Option B: Prometheus Metrics Export

```bash
# Generate Prometheus metrics
/usr/local/bin/monitoring-status.sh metrics /var/lib/prometheus/calendarbot.prom

# Add to cron
crontab -e
# Add: */5 * * * * /usr/local/bin/monitoring-status.sh metrics /var/lib/prometheus/calendarbot.prom
```

**Example Prometheus metrics:**
```prometheus
# HELP calendarbot_up CalendarBot server status (1=up, 0=down)
# TYPE calendarbot_up gauge
calendarbot_up 1

# HELP calendarbot_events_total Total events in 24h window
# TYPE calendarbot_events_total counter
calendarbot_events_total 142

# HELP calendarbot_errors_total Total errors in 24h
# TYPE calendarbot_errors_total counter
calendarbot_errors_total 1

# HELP calendarbot_recovery_actions_24h Recovery actions in 24h
# TYPE calendarbot_recovery_actions_24h counter
calendarbot_recovery_actions_24h 0

# HELP calendarbot_memory_usage_percent Memory usage percentage
# TYPE calendarbot_memory_usage_percent gauge
calendarbot_memory_usage_percent 38.2

# HELP calendarbot_cpu_load_1m 1-minute CPU load average
# TYPE calendarbot_cpu_load_1m gauge
calendarbot_cpu_load_1m 0.42

# HELP calendarbot_disk_usage_percent Disk usage percentage
# TYPE calendarbot_disk_usage_percent gauge
calendarbot_disk_usage_percent 27.1
```

---

## Operational Procedures

### Health Monitoring

#### Real-time Health Status

```bash
# Quick health check
curl -s http://127.0.0.1:8080/api/health | jq '.'

# Generate comprehensive status
/usr/local/bin/monitoring-status.sh health

# Dashboard-compatible status
/usr/local/bin/monitoring-status.sh status /tmp/status.json
cat /tmp/status.json | jq '.'
```

#### Health Endpoint Response Format

The `/api/health` endpoint provides comprehensive system status:

```json
{
  "status": "ok",
  "timestamp": "2025-11-03T10:30:00Z",
  "server": {
    "status": "running",
    "uptime_seconds": 86400,
    "memory_usage": "28MB"
  },
  "last_refresh": {
    "timestamp": "2025-11-03T10:29:30Z",
    "success": true,
    "last_success_delta_s": 30,
    "refresh_interval_s": 300
  },
  "display_probe": {
    "last_render_probe_iso": "2025-11-03T10:29:45Z",
    "browser_heartbeat_active": true
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

### Log Analysis and Interpretation

#### Viewing Structured Logs

```bash
# View all CalendarBot logs
sudo journalctl -u calendarbot-* -f

# View only errors
sudo journalctl -u calendarbot-* | grep -E '(ERROR|CRITICAL)'

# View logs from last 24 hours
sudo journalctl -u calendarbot-* --since "24 hours ago"

# View logs with JSON parsing
sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service --output=json | jq
```

#### Analyzing Event Patterns

**Find critical events:**
```bash
# All critical events in last 24 hours
sudo journalctl -u calendarbot-* --since "24 hours ago" | \
  grep -E '(CRITICAL|recovery|reboot)'

# Parse JSON events for errors
cat /var/log/calendarbot-watchdog/watchdog.log | \
  jq 'select(.level == "ERROR" or .level == "CRITICAL") | {timestamp, event, message}'
```

**Recovery pattern analysis:**
```bash
# Generate recovery effectiveness report
/usr/local/bin/log-aggregator.sh daily $(date +%Y-%m-%d)
cat "/var/local/calendarbot-watchdog/reports/daily_$(date +%Y-%m-%d).json" | \
  jq '.patterns.recovery_effectiveness'
```

#### Event Frequency Analysis

```bash
# Count events by level
sudo journalctl -u calendarbot-* --since "24 hours ago" | \
  grep -oE '(DEBUG|INFO|WARN|ERROR|CRITICAL)' | sort | uniq -c

# Count recovery actions
sudo journalctl -u calendarbot-* --since "24 hours ago" | \
  grep -c "recovery"
```

### Log File Locations

```bash
# Structured monitoring logs
/var/log/calendarbot-watchdog/watchdog.log

# Component-specific logs (rsyslog)
/var/log/calendarbot/server.log
/var/log/calendarbot/watchdog.log
/var/log/calendarbot/critical.log

# System logs (journald)
sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service
sudo journalctl -u calendarbot-lite@bencan.service

# Browser logs (from .xinitrc)
/home/bencan/kiosk/kiosk.log
/home/bencan/kiosk/browser-launch.log

# Report files
/var/local/calendarbot-watchdog/reports/daily_*.json
/var/local/calendarbot-watchdog/reports/weekly_*.json
```

---

## Verification Checklist

After completing this section, verify all items:

**Logrotate:**
- [ ] Configuration deployed: `/etc/logrotate.d/calendarbot-watchdog`
- [ ] Test run successful: `sudo logrotate -d /etc/logrotate.d/calendarbot-watchdog`
- [ ] Log directories exist with correct permissions

**rsyslog (if installed):**
- [ ] rsyslog service running
- [ ] Log files created: `/var/log/calendarbot/*.log`
- [ ] Test message appears in logs

**Log Aggregation:**
- [ ] Scripts deployed: `/usr/local/bin/log-aggregator.sh`, `monitoring-status.sh`
- [ ] Scripts executable and working
- [ ] Report directory exists: `/var/local/calendarbot-watchdog/reports/`
- [ ] Daily report generated successfully
- [ ] Monitoring status working

**Automation:**
- [ ] Cron jobs configured: `crontab -l`
- [ ] Cron jobs include daily/weekly reports and cleanup

**Remote Shipping (if configured):**
- [ ] Environment variables set
- [ ] Test webhook successful
- [ ] Log shipper service enabled and running (if using systemd service)

---

## Files Deployed

Summary of files created or modified in this section:

| File Path | Purpose | User Editable |
|-----------|---------|---------------|
| `/etc/logrotate.d/calendarbot-watchdog` | Log rotation config | Rarely |
| `/etc/rsyslog.d/50-calendarbot.conf` | rsyslog config (optional) | Rarely |
| `/usr/local/bin/log-aggregator.sh` | Report generator | No |
| `/usr/local/bin/monitoring-status.sh` | Status dashboard | No |
| `/usr/local/bin/log-shipper.sh` | Remote shipping (optional) | No |
| `/etc/systemd/system/calendarbot-log-shipper.service` | Shipper service (optional) | Rarely |
| `/etc/environment` | Webhook config (optional) | **Yes** |
| Crontab | Automated tasks | **Yes** |

---

## Troubleshooting

### Issue: Logrotate not rotating logs

**Check logrotate status:**
```bash
cat /var/lib/logrotate/status | grep calendarbot
```

**Force rotation:**
```bash
sudo logrotate -f /etc/logrotate.d/calendarbot-watchdog
```

**Check permissions:**
```bash
ls -ld /var/log/calendarbot-watchdog
# Should be writable by bencan user
```

### Issue: rsyslog not writing logs

**Check rsyslog status:**
```bash
sudo systemctl status rsyslog
sudo journalctl -u rsyslog -n 50
```

**Test configuration:**
```bash
sudo rsyslogd -N1
# Should show no errors
```

**Check file permissions:**
```bash
ls -ld /var/log/calendarbot
# Should be owned by syslog:adm
```

**Monitor rsyslog processing:**
```bash
# Enable debug mode temporarily
sudo rsyslogd -d

# Or check for errors in journald
sudo journalctl -u rsyslog | grep -i error
```

### Issue: Log aggregator fails

**Run manually with debug:**
```bash
/usr/local/bin/log-aggregator.sh daily $(date +%Y-%m-%d)
# Check output for errors
```

**Check jq installed:**
```bash
which jq
# If not found: sudo apt-get install jq
```

**Check journalctl access:**
```bash
journalctl -u calendarbot-* --since "1 hour ago"
# Should show logs
```

**Check file permissions:**
```bash
ls -ld /var/local/calendarbot-watchdog/reports
# Should be owned by bencan user
```

### Issue: Webhook shipping fails

**Test webhook manually:**
```bash
export CALENDARBOT_WEBHOOK_URL="https://your-webhook.com"
export CALENDARBOT_WEBHOOK_TOKEN="your-token"
/usr/local/bin/log-shipper.sh test
```

**Check network connectivity:**
```bash
curl -v "$CALENDARBOT_WEBHOOK_URL"
```

**View shipper service logs:**
```bash
sudo journalctl -u calendarbot-log-shipper.service -f
```

**Test DNS resolution:**
```bash
nslookup $(echo "$CALENDARBOT_WEBHOOK_URL" | sed 's|https\?://||' | cut -d/ -f1)
```

### Issue: High disk usage

**Check current log usage:**
```bash
du -sh /var/log/calendarbot*
du -sh /var/local/calendarbot-watchdog
```

**Check for unrotated large files:**
```bash
find /var/log -type f -size +10M | grep calendarbot
```

**Manually clean up old compressed logs:**
```bash
find /var/log/calendarbot-watchdog -name "*.gz" -mtime +7 -delete
```

**Check logrotate status:**
```bash
cat /var/lib/logrotate/status | grep calendarbot
sudo logrotate -vf /etc/logrotate.d/calendarbot-watchdog
```

---

## Maintenance

### Regular Maintenance Tasks

**Weekly:**
```bash
# Review error logs
sudo journalctl -u calendarbot-* --since "7 days ago" | grep -i error

# Check disk space
df -h | grep -E "Filesystem|/var|/home"

# Review aggregated reports
ls -lh /var/local/calendarbot-watchdog/reports/
cat /var/local/calendarbot-watchdog/reports/weekly_*.json | jq '.summary' | head
```

**Monthly:**
```bash
# Check log rotation working
ls -lh /var/log/calendarbot-watchdog/

# Review monitoring trends
cat /var/local/calendarbot-watchdog/reports/weekly_*.json | jq '.summary'

# Clean up old compressed logs if needed
find /var/log/calendarbot-watchdog -name "*.gz" -mtime +30 -delete

# Review cron job execution
grep CRON /var/log/syslog | grep calendarbot
```

**Quarterly:**
```bash
# Review log aggregation configuration
/usr/local/bin/log-aggregator.sh --help

# Test monitoring status
/usr/local/bin/monitoring-status.sh health

# Review webhook shipping (if enabled)
sudo journalctl -u calendarbot-log-shipper.service --since "3 months ago" | grep -c "shipped"

# Update webhook token if rotating
sudo nano /etc/environment
# Update CALENDARBOT_WEBHOOK_TOKEN
```

### Manual Report Generation

```bash
# Daily report for specific date
/usr/local/bin/log-aggregator.sh daily 2025-11-01

# Weekly report for week starting specific date
/usr/local/bin/log-aggregator.sh weekly 2025-10-28

# Status snapshot
/usr/local/bin/monitoring-status.sh status /tmp/status-snapshot.json

# View with jq
cat /var/local/calendarbot-watchdog/reports/daily_2025-11-01.json | jq .summary
```

### Log Retention Management

```bash
# Manual cleanup of old reports
/usr/local/bin/log-aggregator.sh cleanup

# Check report disk usage
du -sh /var/local/calendarbot-watchdog/reports

# Archive old reports to external storage
tar -czf calendarbot-reports-$(date +%Y-%m).tar.gz \
  /var/local/calendarbot-watchdog/reports/*.json

# Copy to external storage or network location
# scp calendarbot-reports-*.tar.gz user@backup-server:/backups/
```

---

## Advanced Topics

### External Monitoring Integration

#### Grafana + Prometheus Setup

**1. Install Prometheus (for metrics collection):**
```bash
# Install Prometheus Node Exporter
sudo apt-get install -y prometheus-node-exporter
sudo systemctl enable prometheus-node-exporter
sudo systemctl start prometheus-node-exporter
```

**2. Configure CalendarBot metrics export:**
```bash
# Create Prometheus metrics directory
sudo mkdir -p /var/lib/prometheus
sudo chown bencan:bencan /var/lib/prometheus

# Add metrics generation to crontab
crontab -e
# Add: */5 * * * * /usr/local/bin/monitoring-status.sh metrics /var/lib/prometheus/calendarbot.prom
```

**3. Configure Prometheus scraper** (on monitoring server):
```yaml
# /etc/prometheus/prometheus.yml
scrape_configs:
  - job_name: 'calendarbot-kiosk'
    static_configs:
      - targets: ['<PI_IP>:9100']  # node_exporter

  - job_name: 'calendarbot-app'
    file_sd_configs:
      - files:
          - '/var/lib/prometheus/calendarbot.prom'
        refresh_interval: 60s
```

**4. Create Grafana dashboard:**
```json
{
  "dashboard": {
    "title": "CalendarBot Kiosk Monitoring",
    "panels": [
      {
        "title": "System Health",
        "type": "stat",
        "targets": [
          {"expr": "calendarbot_up"}
        ]
      },
      {
        "title": "Resource Usage",
        "type": "graph",
        "targets": [
          {"expr": "calendarbot_memory_usage_percent"},
          {"expr": "calendarbot_cpu_load_1m"}
        ]
      },
      {
        "title": "24h Error Rate",
        "type": "graph",
        "targets": [
          {"expr": "increase(calendarbot_errors_total[1h])"},
          {"expr": "increase(calendarbot_recovery_actions_24h[1h])"}
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
HEALTH_OUTPUT=$(/usr/local/bin/monitoring-status.sh health 2>/dev/null)
if [[ $? -eq 0 ]]; then
    echo "OK - CalendarBot is healthy: $HEALTH_OUTPUT"
    exit 0
else
    echo "CRITICAL - CalendarBot health check failed"
    exit 2
fi
EOF

sudo chmod +x /usr/local/lib/nagios/plugins/check_calendarbot

# Add to Nagios configuration
# define service {
#     use                 generic-service
#     host_name           calendarbot-kiosk
#     service_description CalendarBot Health
#     check_command       check_calendarbot
# }
```

### Webhook Integration Examples

#### Slack Notifications

```bash
# Configure Slack webhook
export CALENDARBOT_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

# Test message
curl -X POST "$CALENDARBOT_WEBHOOK_URL" \
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

#### Discord Integration

```bash
# Configure Discord webhook
export CALENDARBOT_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR/WEBHOOK"

# Test message
curl -X POST "$CALENDARBOT_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "embeds": [{
      "title": "CalendarBot Critical Event",
      "description": "System reboot initiated",
      "color": 15158332,
      "fields": [
        {"name": "Device", "value": "Pi Zero 2 Kiosk", "inline": true},
        {"name": "Recovery Level", "value": "4", "inline": true}
      ],
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S.000Z)'"
    }]
  }'
```

#### Custom Webhook Handler (Flask example)

```python
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route('/api/calendarbot/events', methods=['POST'])
def receive_calendarbot_event():
    # Verify authentication token
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if token != 'your-secure-token-here':
        return jsonify({'error': 'Unauthorized'}), 401

    event = request.json
    print(f"Received CalendarBot event: {json.dumps(event, indent=2)}")

    # Process critical events
    if event.get('level') == 'CRITICAL':
        send_alert(event)

    # Store in database, forward to monitoring system, etc.

    return jsonify({'status': 'received'}), 200

def send_alert(event):
    # Implement your alerting logic here
    # Email, SMS, PagerDuty, etc.
    pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

### Multi-Device Log Aggregation

For managing logs from multiple CalendarBot kiosks:

**1. Central log collection server setup:**
```bash
# Install rsyslog on central server
sudo apt-get install -y rsyslog

# Configure remote reception
sudo tee -a /etc/rsyslog.conf << 'EOF'
# Enable UDP syslog reception
module(load="imudp")
input(type="imudp" port="514")

# Enable TCP syslog reception
module(load="imtcp")
input(type="imtcp" port="514")

# Template for per-host logs
template(name="RemoteHost" type="string" string="/var/log/remote/%HOSTNAME%/%PROGRAMNAME%.log")
*.* ?RemoteHost
EOF

sudo systemctl restart rsyslog
```

**2. Configure kiosks to forward logs:**
```bash
# On each Pi kiosk
sudo tee -a /etc/rsyslog.conf << 'EOF'
# Forward all logs to central server
*.* @@central-log-server.example.com:514
EOF

sudo systemctl restart rsyslog
```

**3. Centralized monitoring dashboard:**
```bash
# Aggregate status from multiple devices
for device in kiosk-01 kiosk-02 kiosk-03; do
  echo "=== $device ==="
  ssh bencan@$device '/usr/local/bin/monitoring-status.sh health'
done
```

### Email Alerts (Alternative to Webhook)

```bash
# Install mailutils
sudo apt-get install -y mailutils

# Configure SMTP (edit /etc/postfix/main.cf or use msmtp)
# Example for Gmail SMTP:
sudo tee ~/.msmtprc << 'EOF'
defaults
auth on
tls on
logfile ~/.msmtp.log

account gmail
host smtp.gmail.com
port 587
from your-email@gmail.com
user your-email@gmail.com
password your-app-password
EOF

chmod 600 ~/.msmtprc

# Test email
echo "Test from CalendarBot" | mail -s "Test" your@email.com

# Add email alert to cron
crontab -e
# Add: 0 */6 * * * journalctl -u calendarbot-* --since "6 hours ago" | grep CRITICAL | mail -s "CalendarBot Critical Errors" your@email.com
```

### Custom Log Filtering

Create custom filters for specific events:

```bash
# Create critical event filter script
sudo tee /usr/local/bin/critical-event-filter.sh << 'EOF'
#!/bin/bash
# Filter and report only critical recovery events

SINCE="${1:-1 hour ago}"

journalctl -u calendarbot-* --since "$SINCE" | \
  grep -E '(CRITICAL|reboot|escalat)' | \
  while read -r line; do
    echo "$line"
  done | \
  jq -R -s 'split("\n") | map(select(length > 0))'
EOF

sudo chmod +x /usr/local/bin/critical-event-filter.sh

# Use the filter
/usr/local/bin/critical-event-filter.sh "24 hours ago"
```

---

## Performance Notes

**Disk usage (with default rotation):**
- Active logs: ~20-50MB
- Compressed archives: ~5-10MB/week
- Reports: ~1-2MB/month

**Total estimated**: ~100-200MB for 30 days of logs

**CPU usage:**
- Log aggregation: <5% CPU for 1-2 seconds daily
- Monitoring status: <2% CPU for <1 second per run
- Log rotation: <1% CPU for <1 second daily
- rsyslog: <1% CPU continuous

**Memory usage:**
- rsyslog: ~5-10MB
- Log aggregator (when running): ~20-30MB
- Monitoring status: ~10-15MB

**Optimization tips:**
- Reduce cron frequency if CPU constrained (e.g., status every 15 mins instead of 5)
- Decrease log retention if disk space limited
- Use local-only logging (skip rsyslog) for minimal overhead
- Batch webhook shipping to reduce network overhead

---

## Security Considerations

### Webhook Security

```bash
# Always use HTTPS for webhooks
export CALENDARBOT_WEBHOOK_URL="https://secure-endpoint.example.com"
export CALENDARBOT_WEBHOOK_INSECURE=false

# Use strong bearer tokens
WEBHOOK_TOKEN=$(openssl rand -hex 32)
export CALENDARBOT_WEBHOOK_TOKEN="$WEBHOOK_TOKEN"

# Store token securely
sudo mkdir -p /etc/calendarbot-monitor/secrets
sudo chmod 700 /etc/calendarbot-monitor/secrets
echo "$WEBHOOK_TOKEN" | sudo tee /etc/calendarbot-monitor/secrets/webhook_token
sudo chmod 600 /etc/calendarbot-monitor/secrets/webhook_token
```

### Log File Permissions

```bash
# Secure log directories
sudo chmod 750 /var/log/calendarbot-watchdog
sudo chmod 750 /var/log/calendarbot

# Secure state and reports
sudo chmod 700 /var/local/calendarbot-watchdog

# Review permissions
ls -ld /var/log/calendarbot*
ls -ld /var/local/calendarbot-watchdog
```

### Network Security

```bash
# Use firewall to restrict log shipper
sudo ufw allow out 443/tcp  # HTTPS webhooks only
sudo ufw deny out 514       # Block syslog unless needed

# Encrypt syslog forwarding (if using remote syslog)
export CALENDARBOT_REMOTE_SYSLOG_TLS=true
```

---

## Next Steps

**Section 4 Complete!** ✅

You now have:
- **Comprehensive monitoring** - Health checks, status dashboards, real-time metrics
- **Intelligent log management** - Automatic rotation, aggregation, retention
- **Structured observability** - JSON logging, severity filtering, event tracking
- **Trend analysis** - Daily/weekly reports for pattern detection
- **Remote integration** - Webhook shipping, external monitoring tools (optional)
- **Operational tooling** - Log analysis commands, troubleshooting procedures

**Complete your installation:**
- Review [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for verification
- Review [FILE_INVENTORY.md](FILE_INVENTORY.md) for complete file reference
- Return to [Installation Overview](INSTALLATION_OVERVIEW.md)

**Ongoing monitoring:**
```bash
# Quick health check
/usr/local/bin/monitoring-status.sh health

# View recent logs
sudo journalctl -u calendarbot-* --since "1 hour ago"

# Check disk space
df -h /var/log

# Review daily report
cat /var/local/calendarbot-watchdog/reports/daily_$(date +%Y-%m-%d).json | jq .summary
```

---

**Installation Complete!** 🎉
