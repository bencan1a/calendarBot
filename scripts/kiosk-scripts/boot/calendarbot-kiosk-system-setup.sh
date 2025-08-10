#!/bin/bash
# CalendarBot Kiosk System Setup Script
# One-time system configuration for optimal kiosk operation

set -euo pipefail

LOG_FILE="/var/log/calendarbot/system-setup.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting CalendarBot kiosk system setup"

# 1. Configure GPU memory split for Pi Zero 2W
log "Configuring GPU memory split"
if ! grep -q "gpu_mem=64" /boot/config.txt; then
    echo "gpu_mem=64" >> /boot/config.txt
    log "GPU memory split set to 64MB"
fi

# 2. Configure swap for memory management
log "Configuring swap"
SWAP_SIZE=512
SWAP_FILE="/swapfile"

if [ ! -f "$SWAP_FILE" ]; then
    fallocate -l ${SWAP_SIZE}M "$SWAP_FILE"
    chmod 600 "$SWAP_FILE"
    mkswap "$SWAP_FILE"
    echo "$SWAP_FILE none swap sw 0 0" >> /etc/fstab
    log "Swap file created: ${SWAP_SIZE}MB"
fi

# Enable swap
swapon "$SWAP_FILE" 2>/dev/null || true

# 3. Configure tmpfs for logs to reduce SD card wear
log "Configuring tmpfs for logs"
if ! grep -q "/var/log/calendarbot" /etc/fstab; then
    echo "tmpfs /var/log/calendarbot tmpfs defaults,size=64M,uid=1000,gid=1000 0 0" >> /etc/fstab
    log "tmpfs configured for CalendarBot logs"
fi

# 4. Set CPU governor for consistent performance
log "Setting CPU governor to performance"
echo "performance" > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || true

# 5. Configure network optimizations
log "Applying network optimizations"
cat > /etc/sysctl.d/99-calendarbot-kiosk.conf << EOF
# CalendarBot Kiosk Network Optimizations
net.core.rmem_default = 65536
net.core.rmem_max = 131072
net.core.wmem_default = 65536
net.core.wmem_max = 131072
net.ipv4.tcp_rmem = 4096 65536 131072
net.ipv4.tcp_wmem = 4096 65536 131072
EOF

# 6. Configure hardware watchdog
log "Configuring hardware watchdog"
if [ -c /dev/watchdog ]; then
    modprobe bcm2835_wdt 2>/dev/null || true
    
    cat > /etc/watchdog.conf << EOF
# CalendarBot Kiosk Watchdog Configuration
watchdog-device = /dev/watchdog
watchdog-timeout = 60
interval = 10
logtick = 1

# Monitor system resources
max-load-1 = 8
max-load-5 = 6
max-load-15 = 4
min-memory = 32768

# Monitor kiosk process
pidfile = /home/pi/.calendarbot/daemon.pid
EOF

    systemctl enable watchdog
    log "Hardware watchdog configured"
fi

# 7. Disable unnecessary services to save memory
log "Disabling unnecessary services"
SERVICES_TO_DISABLE="
    bluetooth.service
    hciuart.service
    triggerhappy.service
    avahi-daemon.service
    cups.service
    cups-browsed.service
"

for service in $SERVICES_TO_DISABLE; do
    if systemctl is-enabled "$service" >/dev/null 2>&1; then
        systemctl disable "$service"
        log "Disabled service: $service"
    fi
done

# 8. Configure auto-login for pi user
log "Configuring auto-login"
systemctl set-default graphical.target

# Configure auto-login through systemd
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin pi --noclear %I \$TERM
EOF

log "System setup completed successfully"