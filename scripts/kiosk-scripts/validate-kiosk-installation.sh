#!/bin/bash
# CalendarBot Kiosk Installation Validation Script
# Verifies that all components are properly installed and configured

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validation results
PASSED=0
FAILED=0
WARNINGS=0

log_info() {
    echo "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo "${GREEN}[PASS]${NC} $*"
    PASSED=$((PASSED + 1))
}

log_error() {
    echo "${RED}[FAIL]${NC} $*"
    FAILED=$((FAILED + 1))
}

log_warning() {
    echo "${YELLOW}[WARN]${NC} $*"
    WARNINGS=$((WARNINGS + 1))
}

# Header
echo "==============================================="
echo "CalendarBot Kiosk Installation Validation"
echo "==============================================="
echo

# Check if running as root
if [ "$(id -u)" -eq 0 ]; then
    log_warning "Running as root - some checks may not reflect pi user environment"
fi

# 1. Check systemd service files
log_info "Checking systemd service files..."
for service in calendarbot-kiosk.service calendarbot-kiosk-setup.service calendarbot-network-wait.service; do
    if [ -f "/etc/systemd/system/$service" ]; then
        log_success "Service file exists: $service"
    else
        log_error "Missing service file: $service"
    fi
done

# 2. Check boot scripts
log_info "Checking boot scripts..."
for script in calendarbot-kiosk-prestart.sh calendarbot-kiosk-system-setup.sh calendarbot-wait-for-network.sh calendarbot-kiosk-cleanup.sh; do
    if [ -f "/usr/local/bin/$script" ] && [ -x "/usr/local/bin/$script" ]; then
        log_success "Boot script exists and executable: $script"
    else
        log_error "Missing or non-executable boot script: $script"
    fi
done

# 3. Check X11 session files
log_info "Checking X11 session configuration..."
if [ -f "/usr/share/xsessions/calendarbot-kiosk.desktop" ]; then
    log_success "Kiosk session definition exists"
else
    log_error "Missing kiosk session definition"
fi

if [ -f "/home/pi/.xsession" ] && [ -x "/home/pi/.xsession" ]; then
    log_success "X11 session script exists and executable"
else
    log_error "Missing or non-executable X11 session script"
fi

# 4. Check LightDM configuration
log_info "Checking auto-login configuration..."
if [ -f "/etc/lightdm/lightdm.conf" ]; then
    if grep -q "autologin-user=pi" /etc/lightdm/lightdm.conf; then
        log_success "Auto-login configured for pi user"
    else
        log_error "Auto-login not configured properly"
    fi
else
    log_error "LightDM configuration file missing"
fi

# 5. Check boot configuration
log_info "Checking boot configuration..."
if [ -f "/boot/config.txt" ]; then
    if grep -q "gpu_mem=64" /boot/config.txt; then
        log_success "GPU memory split configured"
    else
        log_warning "GPU memory split not configured"
    fi
    
    if grep -q "dtparam=watchdog=on" /boot/config.txt; then
        log_success "Hardware watchdog enabled"
    else
        log_warning "Hardware watchdog not enabled"
    fi
else
    log_error "Boot configuration file missing"
fi

# 6. Check required packages
log_info "Checking required system packages..."
REQUIRED_PACKAGES="chromium-browser unclutter xinput xserver-xorg openbox lightdm watchdog python3-venv python3-pip x11-xserver-utils"
for package in $REQUIRED_PACKAGES; do
    if dpkg -l | grep -q "^ii.*$package"; then
        log_success "Package installed: $package"
    else
        log_error "Package missing: $package"
    fi
done

# 7. Check CalendarBot installation
log_info "Checking CalendarBot installation..."
if [ -d "/home/pi/calendarbot" ]; then
    log_success "CalendarBot directory exists"
    
    if [ -d "/home/pi/calendarbot/venv" ]; then
        log_success "Python virtual environment exists"
        
        # Check if CalendarBot is installed in venv
        if /home/pi/calendarbot/venv/bin/python -c "import calendarbot" 2>/dev/null; then
            log_success "CalendarBot package installed in virtual environment"
        else
            log_error "CalendarBot package not installed in virtual environment"
        fi
    else
        log_error "Python virtual environment missing"
    fi
else
    log_error "CalendarBot directory missing"
fi

# 8. Check configuration directory
log_info "Checking configuration directory..."
if [ -d "/home/pi/.config/calendarbot" ]; then
    log_success "CalendarBot configuration directory exists"
    
    if [ -f "/home/pi/.config/calendarbot/config.yaml" ]; then
        log_success "Configuration file exists"
    else
        log_warning "Configuration file missing (will be created on first run)"
    fi
else
    log_error "CalendarBot configuration directory missing"
fi

# 9. Check log directory
log_info "Checking log directory..."
if [ -d "/var/log/calendarbot" ]; then
    log_success "Log directory exists"
    
    # Check permissions
    if [ "$(stat -c %U /var/log/calendarbot)" = "pi" ]; then
        log_success "Log directory has correct ownership"
    else
        log_error "Log directory has incorrect ownership"
    fi
else
    log_error "Log directory missing"
fi

# 10. Check service status (if systemd is running)
if systemctl is-system-running >/dev/null 2>&1; then
    log_info "Checking service status..."
    
    for service in calendarbot-kiosk-setup.service calendarbot-network-wait.service calendarbot-kiosk.service; do
        if systemctl is-enabled "$service" >/dev/null 2>&1; then
            log_success "Service enabled: $service"
        else
            log_error "Service not enabled: $service"
        fi
    done
    
    # Check if graphical target is default
    if systemctl get-default | grep -q "graphical.target"; then
        log_success "Graphical target is default"
    else
        log_error "Graphical target is not default"
    fi
else
    log_warning "Systemd not running - cannot check service status"
fi

# 11. Check display environment (if X11 is running)
if [ -n "${DISPLAY:-}" ]; then
    log_info "Checking display environment..."
    
    if command -v xdpyinfo >/dev/null 2>&1 && xdpyinfo >/dev/null 2>&1; then
        log_success "X11 display accessible"
    else
        log_warning "X11 display not accessible"
    fi
else
    log_warning "DISPLAY environment variable not set"
fi

# 12. Security and permissions check
log_info "Checking security configuration..."
for script in /usr/local/bin/calendarbot-*; do
    if [ -f "$script" ]; then
        PERMS=$(stat -c %a "$script")
        if [ "$PERMS" = "755" ]; then
            log_success "Correct permissions on $(basename "$script")"
        else
            log_warning "Unexpected permissions ($PERMS) on $(basename "$script")"
        fi
    fi
done

# Summary
echo
echo "==============================================="
echo "Validation Summary"
echo "==============================================="
echo "${GREEN}Passed: $PASSED${NC}"
echo "${YELLOW}Warnings: $WARNINGS${NC}"
echo "${RED}Failed: $FAILED${NC}"
echo

if [ $FAILED -eq 0 ]; then
    echo "${GREEN}✓ Installation validation completed successfully!${NC}"
    echo "The system appears ready for kiosk mode."
    echo
    echo "Next steps:"
    echo "1. Ensure CalendarBot configuration is set up"
    echo "2. Reboot to start kiosk mode: sudo reboot"
    exit 0
else
    echo "${RED}✗ Installation validation failed with $FAILED errors${NC}"
    echo "Please address the failed checks before proceeding."
    exit 1
fi