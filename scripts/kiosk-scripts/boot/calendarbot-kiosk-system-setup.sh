#!/bin/bash
# CalendarBot Kiosk System Setup Script
# One-time system configuration for optimal kiosk operation

set -euo pipefail

# Auto-detect target user (same logic as installer script)
TARGET_USER=""

# Try SUDO_USER first (most reliable when run with sudo)
if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
    TARGET_USER="$SUDO_USER"
fi

# If no SUDO_USER, try to detect from CalendarBot project directory
if [ -z "$TARGET_USER" ] || [ "$TARGET_USER" = "root" ]; then
    # Find CalendarBot project directory
    SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
    PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
    
    if [ -d "$PROJECT_ROOT" ] && [ -f "$PROJECT_ROOT/calendarbot/__init__.py" ]; then
        TARGET_USER=$(stat -c '%U' "$PROJECT_ROOT" 2>/dev/null || true)
    fi
fi

# Fall back to first regular user with home directory
if [ -z "$TARGET_USER" ] || [ "$TARGET_USER" = "root" ]; then
    REGULAR_USERS=$(awk -F: '$3 >= 1000 && $3 != 65534 && $1 !~ /^snap/ {print $1}' /etc/passwd)
    for user in $REGULAR_USERS; do
        if [ "$user" != "nobody" ] && [ -d "/home/$user" ]; then
            TARGET_USER="$user"
            break
        fi
    done
fi

if [ -z "$TARGET_USER" ] || [ "$TARGET_USER" = "root" ]; then
    echo "ERROR: Cannot determine target user for CalendarBot."
    echo "Please ensure you're running this with sudo as a regular user."
    exit 1
fi

TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)
TARGET_UID=$(id -u "$TARGET_USER")
TARGET_GID=$(id -g "$TARGET_USER")

LOG_FILE="/var/log/calendarbot/system-setup.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting CalendarBot kiosk system setup for user: $TARGET_USER (UID: $TARGET_UID, Home: $TARGET_HOME)"

# System compatibility check
log "Checking system compatibility..."
IS_RASPBERRY_PI=0
PI_MODEL=""

if [ -f "/proc/device-tree/model" ]; then
    MODEL=$(tr -d '\0' < /proc/device-tree/model)
    if echo "$MODEL" | grep -q "Raspberry Pi"; then
        IS_RASPBERRY_PI=1
        PI_MODEL="$MODEL"
        log "Detected: $PI_MODEL"
    fi
fi

if [ $IS_RASPBERRY_PI -eq 0 ]; then
    log "WARNING: Not running on Raspberry Pi hardware"
    log "System: $(uname -a)"
    log "Some optimizations may not apply"
fi

# 1. Configure GPU memory split for Raspberry Pi
if [ $IS_RASPBERRY_PI -eq 1 ]; then
    log "Configuring GPU memory split"
    BOOT_CONFIG=""
    for location in /boot/firmware/config.txt /boot/config.txt; do
        if [ -f "$location" ]; then
            BOOT_CONFIG="$location"
            break
        fi
    done
    
    if [ -n "$BOOT_CONFIG" ]; then
        if ! grep -q "gpu_mem=64" "$BOOT_CONFIG"; then
            echo "gpu_mem=64" >> "$BOOT_CONFIG"
            log "GPU memory split set to 64MB in $BOOT_CONFIG"
        fi
    else
        log "WARNING: Boot config not found, skipping GPU memory configuration"
    fi
else
    log "Skipping GPU memory configuration (not Raspberry Pi)"
fi

# 2. Configure zram (compressed RAM swap) instead of swap file
log "Configuring memory management with zram"

# Check if zram-tools is installed
if ! command -v zramctl >/dev/null 2>&1; then
    log "WARNING: zram-tools not installed. Skipping zram configuration."
    log "Install with: apt-get install zram-tools"
else
    # Configure zram if not already configured
    if ! zramctl | grep -q zram0; then
        # Load zram module
        modprobe zram num_devices=1 2>/dev/null || true
        
        # Calculate zram size (50% of total RAM, max 512MB for Pi Zero 2)
        TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
        ZRAM_SIZE=$(( TOTAL_MEM / 2 ))
        if [ $ZRAM_SIZE -gt 512 ]; then
            ZRAM_SIZE=512
        fi
        
        # Set up zram device
        if [ -b /dev/zram0 ]; then
            echo "${ZRAM_SIZE}M" > /sys/block/zram0/disksize
            mkswap /dev/zram0
            swapon -p 100 /dev/zram0
            log "zram configured: ${ZRAM_SIZE}MB compressed swap"
        else
            log "WARNING: zram device not available"
        fi
    else
        log "zram already configured"
    fi
    
    # Create zram config for persistence
    cat > /etc/default/zramswap << EOF
# CalendarBot Kiosk zram configuration
ALGO=lz4
PERCENT=50
PRIORITY=100
EOF
    log "zram configuration saved to /etc/default/zramswap"
fi

# 3. Configure tmpfs for logs to reduce SD card wear
log "Configuring tmpfs for logs"
if ! grep -q "/var/log/calendarbot" /etc/fstab; then
    echo "tmpfs /var/log/calendarbot tmpfs defaults,size=64M,uid=$TARGET_UID,gid=$TARGET_GID 0 0" >> /etc/fstab
    log "tmpfs configured for CalendarBot logs (UID: $TARGET_UID, GID: $TARGET_GID)"
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
pidfile = $TARGET_HOME/.calendarbot/daemon.pid
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

# 8. Configure auto-login for target user
log "Configuring auto-login for user: $TARGET_USER"
systemctl set-default graphical.target

# Configure auto-login through systemd
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $TARGET_USER --noclear %I \$TERM
EOF

log "System setup completed successfully"
log "Configuration summary:"
log "  - Target user: $TARGET_USER"
log "  - Home directory: $TARGET_HOME"
log "  - System type: $([ $IS_RASPBERRY_PI -eq 1 ] && echo "$PI_MODEL" || echo "Non-Pi system")"
log "  - Memory management: zram (compressed swap)"
log "  - Auto-login: Configured for $TARGET_USER"