# CalendarBot Kiosk Installation Overview

Complete deployment guide for setting up a CalendarBot_Lite kiosk on Raspberry Pi with monitoring, auto-recovery, and remote access.

**Last Updated**: 2025-11-03
**Target Platform**: Raspberry Pi Zero 2 W (also compatible with Pi 3/4)
**OS**: Raspbian/Debian 11+ (Bullseye or later)

---

## Documentation Structure

This deployment is organized into 4 modular sections that can be completed independently:

### **[1. Base CalendarBot_Lite Installation](1_BASE_INSTALL.md)**
Install the core CalendarBot_Lite server with systemd service management.

**What You'll Deploy:**
- Python virtual environment
- CalendarBot_Lite server
- systemd service for automatic startup
- Basic calendar functionality

**Time Required**: 30-45 minutes
**Prerequisites**: Fresh Raspbian installation with SSH access

---

### **[2. Kiosk Mode & Watchdog](2_KIOSK_WATCHDOG.md)**
Configure automatic browser launch with progressive recovery monitoring.

**What You'll Deploy:**
- X server and window manager
- Chromium browser in kiosk mode
- Watchdog daemon with 3-level browser recovery
- Auto-login and X session management

**Time Required**: 45-60 minutes
**Prerequisites**: Section 1 completed

---

### **[3. Alexa Integration](3_ALEXA_INTEGRATION.md)**
Set up HTTPS reverse proxy for remote Alexa skill access.

**What You'll Deploy:**
- Caddy web server with automatic HTTPS
- DNS configuration
- Bearer token authentication
- Firewall rules

**Time Required**: 30-45 minutes
**Prerequisites**: Section 1 completed, domain name registered

---

### **[4. Monitoring & Log Management](4_LOG_MANAGEMENT.md)**
Configure log rotation, aggregation, monitoring, and optional remote shipping.

**What You'll Deploy:**
- Logrotate configuration
- Log aggregation scripts
- Monitoring dashboard and health checks
- Optional remote webhook shipping

**Time Required**: 30 minutes
**Prerequisites**: Section 1 completed

---

## Quick Reference

**Need a checklist?** → [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
**Need file details?** → [FILE_INVENTORY.md](FILE_INVENTORY.md)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────┐
│  Raspberry Pi (Raspbian/Debian)                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  systemd Services                                │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  • calendarbot-lite@bencan.service              │   │
│  │    └─> CalendarBot server (port 8080)           │   │
│  │                                                  │   │
│  │  • calendarbot-kiosk-watchdog@bencan.service    │   │
│  │    └─> Health monitoring & recovery             │   │
│  │                                                  │   │
│  │  • caddy.service (optional)                     │   │
│  │    └─> HTTPS reverse proxy                      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Auto-Login Boot Sequence (Kiosk Mode)           │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  getty@tty1 → auto-login → .bash_profile        │   │
│  │    └─> startx → .xinitrc → Chromium kiosk       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Network Services                                │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  localhost:8080  → CalendarBot API               │   │
│  │  :80, :443       → Caddy HTTPS (optional)        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
         ▲                                        ▲
         │                                        │
    ICS Calendar                            Alexa Skill
    (Office 365, Google)                    (via HTTPS)
```

### Data Flow

```
┌──────────────┐     ┌───────────────────┐     ┌──────────────┐
│ ICS Calendar │────>│ CalendarBot Server│<────│ Alexa Skill  │
│  (Remote)    │     │   (localhost:8080)│     │ (via Caddy)  │
└──────────────┘     └─────────┬─────────┘     └──────────────┘
                               │
                     ┌─────────┴─────────┐
                     │                   │
                     ▼                   ▼
              ┌─────────────┐    ┌─────────────┐
              │  Chromium   │    │  Watchdog   │
              │  (Display)  │───>│  Monitor    │
              └─────────────┘    └─────────────┘
                     │                   │
                     └─────────┬─────────┘
                               ▼
                     Browser Heartbeat
                     (POST /api/browser-heartbeat)
```

### Progressive Recovery System

The watchdog implements multi-level escalation for different failure scenarios:

**Browser Heartbeat Recovery** (3 levels):
```
Heartbeat Stale (>2 min)
    ↓
Level 0: Soft Reload (F5 key via xdotool)
    ↓ (if still stale)
Level 1: Browser Restart (kill chromium + relaunch)
    ↓ (if still stale)
Level 2: X Session Restart (kill X + auto-restart via watchdog)
    ↓ (if still stale)
System escalation (service restart → reboot)
```

**System Health Recovery** (4 levels):
```
Server Unhealthy (HTTP 503/timeout)
    ↓
Level 1: Browser Restart (kill + relaunch)
    ↓ (if still unhealthy)
Level 2: X Session Restart (kill X, auto-restart via .bash_profile)
    ↓ (if still unhealthy)
Level 3: CalendarBot Service Restart (systemctl restart)
    ↓ (if still unhealthy)
Level 4: System Reboot (last resort)
```

---

## Prerequisites

### Hardware Requirements
- **Raspberry Pi Zero 2 W** / Pi 3 / Pi 4
- **MicroSD card**: 16GB minimum, 32GB recommended
- **Power supply**: Official Raspberry Pi power supply recommended
- **Display**: HDMI monitor (for kiosk mode)
- **Network**: WiFi or Ethernet connectivity

### Software Requirements
- **OS**: Fresh Raspbian/Debian installation (Bullseye or later)
- **SSH**: Enabled for remote access
- **User account**: Non-root user created (examples use `bencan`)
- **Internet**: Active network connectivity

### Required Credentials & Information

**For All Deployments:**
- [ ] ICS calendar URL (Office 365, Google Calendar, etc.)
- [ ] SSH access credentials
- [ ] Static IP address (recommended)

**For Alexa Integration (Section 3):**
- [ ] Domain name (e.g., `ashwoodgrove.net`)
- [ ] DNS management access
- [ ] Public IP address or dynamic DNS
- [ ] Amazon Developer Account (for Alexa Skill)
- [ ] AWS Account (for Lambda function)

**For Remote Log Shipping (Section 4, optional):**
- [ ] Webhook endpoint URL
- [ ] Webhook authentication token

### Network Configuration

**Recommended Setup:**
- Static IP address assignment
- Firewall configuration (UFW)

**Required Ports:**
- `22` - SSH access
- `8080` - CalendarBot server (localhost only)
- `80` - HTTP (optional, for Caddy/Alexa)
- `443` - HTTPS (optional, for Caddy/Alexa)

---

## Installation Paths

Choose your installation path based on your requirements:

### **Path A: Minimal (Kiosk Display Only)**
Complete sections 1 and 2 only.

**Use Case**: Local calendar display with automatic recovery, no remote access needed.

**Services Running**: 2
- CalendarBot server
- Watchdog daemon

**Time Required**: ~90 minutes

---

### **Path B: Full Deployment (Kiosk + Alexa)**
Complete sections 1, 2, and 3.

**Use Case**: Local kiosk display plus remote Alexa skill access via AWS Lambda.

**Services Running**: 3
- CalendarBot server
- Watchdog daemon
- Caddy reverse proxy

**Time Required**: ~2.5-3 hours (includes AWS Lambda + Alexa skill setup)

---

### **Path C: Production (Everything)**
Complete all sections 1-4.

**Use Case**: Production deployment with comprehensive logging, monitoring, and Alexa integration.

**Services Running**: 3-4
- CalendarBot server
- Watchdog daemon
- Caddy reverse proxy
- Log shipper (optional)

**Time Required**: ~3-3.5 hours

---

## Getting Started

### Step 1: Prepare Your System

```bash
# Update system packages
sudo apt-get update
sudo apt-get upgrade -y

# Install basic tools
sudo apt-get install -y git curl jq

# Verify Python 3.7+
python3 --version
```

### Step 2: Choose Your Path

Review the installation paths above and decide which sections you need.

### Step 3: Follow Section Guides

Start with **[Section 1: Base Installation](1_BASE_INSTALL.md)** and proceed sequentially through your chosen sections.

Each section is self-contained with:
- Prerequisites checklist
- Step-by-step instructions
- Verification procedures
- Troubleshooting guidance

### Step 4: Use Supporting Documents

- **During Installation**: Reference [FILE_INVENTORY.md](FILE_INVENTORY.md) for file details
- **For Quick Reference**: Use [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- **For Troubleshooting**: Each section has a dedicated troubleshooting section

---

## Post-Installation

### Verification

After completing your chosen sections:

```bash
# Check all services
sudo systemctl status calendarbot-lite@bencan.service
sudo systemctl status calendarbot-kiosk-watchdog@bencan.service

# Test API endpoint
curl http://localhost:8080/api/whats-next

# View logs
sudo journalctl -u calendarbot-* -f
```

### Ongoing Maintenance

**Daily:**
- Monitor system via watchdog logs

**Weekly:**
- Check monitoring status: `/usr/local/bin/monitoring-status.sh health`
- Review error logs: `sudo journalctl -u calendarbot-* --since "7 days ago" | grep ERROR`

**Monthly:**
- Update system packages: `sudo apt-get update && sudo apt-get upgrade -y`
- Review disk space: `df -h`
- Backup configuration files

### Backup Recommended Files

```bash
# Create backup directory
mkdir -p ~/calendarbot-backup

# Backup configurations
cp ~/calendarbot/.env ~/calendarbot-backup/
cp /etc/calendarbot-monitor/monitor.yaml ~/calendarbot-backup/
cp /etc/caddy/Caddyfile ~/calendarbot-backup/  # if using Alexa

# Create tarball
tar -czf ~/calendarbot-backup-$(date +%Y%m%d).tar.gz ~/calendarbot-backup/
```

---

## Getting Help

### Documentation Resources

- **Section Guides**: Detailed step-by-step instructions with troubleshooting
  - [1. Base Installation](1_BASE_INSTALL.md)
  - [2. Kiosk & Watchdog](2_KIOSK_WATCHDOG.md)
  - [3. Alexa Integration](3_ALEXA_INTEGRATION.md) (includes AWS Lambda + Alexa skill setup)
  - [4. Monitoring & Log Management](4_LOG_MANAGEMENT.md)
- **[FILE_INVENTORY.md](FILE_INVENTORY.md)**: Complete file reference
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)**: Quick verification checklists
- **[../../AGENTS.md](../../AGENTS.md)**: Development guide

### Common Issues

**Service won't start:**
```bash
# Check logs for errors
sudo journalctl -u calendarbot-lite@bencan.service -n 50

# Verify configuration
cat ~/calendarbot/.env | grep CALENDARBOT_ICS_URL
```

**Browser not launching:**
```bash
# Check X server running
ps aux | grep Xorg

# Check .xinitrc exists
ls -la ~/.xinitrc

# View kiosk logs
tail -f ~/kiosk/kiosk.log
```

**Watchdog not recovering:**
```bash
# Check watchdog state
cat /var/local/calendarbot-watchdog/state.json | jq

# View watchdog logs
sudo journalctl -u calendarbot-kiosk-watchdog@bencan.service -f
```

### Collecting Diagnostic Information

```bash
# System info
uname -a
free -h
df -h

# Service statuses
sudo systemctl status calendarbot-*

# Recent logs
sudo journalctl -u calendarbot-* --since "1 hour ago"
```

---

## Next Steps

1. **[Start with Section 1: Base Installation →](1_BASE_INSTALL.md)**

2. Review the [Deployment Checklist](DEPLOYMENT_CHECKLIST.md) for your chosen path

3. Bookmark the [File Inventory](FILE_INVENTORY.md) for reference during installation

---

**Ready to begin? Start with [Section 1: Base Installation](1_BASE_INSTALL.md)**
