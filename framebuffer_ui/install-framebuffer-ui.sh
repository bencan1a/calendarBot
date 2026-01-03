#!/bin/bash
# CalendarBot Framebuffer UI Installer
# Installs the lightweight pygame-based display for Raspberry Pi Zero 2W
#
# Usage:
#   sudo ./install-framebuffer-ui.sh USERNAME
#
# Example:
#   sudo ./install-framebuffer-ui.sh bencan

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

# Get username
USERNAME="$1"
if [ -z "$USERNAME" ]; then
    print_error "Usage: sudo $0 USERNAME"
    exit 1
fi

# Verify user exists
if ! id "$USERNAME" &>/dev/null; then
    print_error "User '$USERNAME' does not exist"
    exit 1
fi

USER_HOME=$(eval echo "~$USERNAME")
CALENDARBOT_DIR="$USER_HOME/calendarbot"

print_header "CalendarBot Framebuffer UI Installer"
echo "User: $USERNAME"
echo "Home: $USER_HOME"
echo "Install Dir: $CALENDARBOT_DIR"
echo ""

# Check if calendarbot directory exists
if [ ! -d "$CALENDARBOT_DIR" ]; then
    print_error "CalendarBot directory not found: $CALENDARBOT_DIR"
    print_info "Please install calendarbot_lite first"
    exit 1
fi

# Step 1: Install system dependencies
print_header "Step 1: Installing System Dependencies"

print_info "Installing SDL2 libraries..."
apt-get update -qq
apt-get install -y \
    libsdl2-2.0-0 \
    libsdl2-ttf-2.0-0 \
    libdrm2 \
    libgbm1

print_success "System dependencies installed"

# Step 2: Install Python dependencies
print_header "Step 2: Installing Python Dependencies"

print_info "Installing pygame in virtual environment..."
su - "$USERNAME" -c "cd $CALENDARBOT_DIR && source venv/bin/activate && pip install --quiet pygame>=2.5.0"

print_success "Python dependencies installed"

# Step 3: Add user to video group
print_header "Step 3: Configuring User Permissions"

print_info "Adding $USERNAME to 'video' group..."
usermod -a -G video "$USERNAME"

print_success "User added to video group"

# Step 4: Install systemd service
print_header "Step 4: Installing systemd Service"

SERVICE_FILE="$CALENDARBOT_DIR/framebuffer_ui/calendarbot-display@.service"
if [ ! -f "$SERVICE_FILE" ]; then
    print_error "Service file not found: $SERVICE_FILE"
    exit 1
fi

print_info "Copying service file..."
cp "$SERVICE_FILE" /etc/systemd/system/

print_info "Reloading systemd daemon..."
systemctl daemon-reload

print_success "systemd service installed"

# Step 5: Configuration
print_header "Step 5: Configuration"

ENV_FILE="$CALENDARBOT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    print_error ".env file not found: $ENV_FILE"
    print_info "Please create .env file with CALENDARBOT_BACKEND_URL"
    exit 1
fi

print_info "Checking .env configuration..."
if grep -q "CALENDARBOT_BACKEND_URL" "$ENV_FILE"; then
    BACKEND_URL=$(grep "CALENDARBOT_BACKEND_URL" "$ENV_FILE" | cut -d'=' -f2)
    print_success "Backend URL configured: $BACKEND_URL"
else
    print_error "CALENDARBOT_BACKEND_URL not found in .env"
    exit 1
fi

# Step 6: Enable and start service
print_header "Step 6: Enable and Start Service"

SERVICE_NAME="calendarbot-display@$USERNAME.service"

print_info "Enabling service: $SERVICE_NAME"
systemctl enable "$SERVICE_NAME"

print_info "Starting service: $SERVICE_NAME"
systemctl start "$SERVICE_NAME"

# Wait a moment for service to start
sleep 2

# Check service status
if systemctl is-active --quiet "$SERVICE_NAME"; then
    print_success "Service is running!"
else
    print_error "Service failed to start"
    print_info "View logs with: journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

# Final summary
print_header "Installation Complete!"

echo ""
echo "CalendarBot Framebuffer UI is now running!"
echo ""
echo "Service management:"
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
echo "  Start:   sudo systemctl start $SERVICE_NAME"
echo "  Restart: sudo systemctl restart $SERVICE_NAME"
echo "  Logs:    journalctl -u $SERVICE_NAME -f"
echo ""
echo "To disable the old X11 kiosk (if installed):"
echo "  sudo systemctl disable calendarbot-kiosk-watchdog@$USERNAME.service"
echo ""
echo "Expected memory usage: ~15-25MB (vs ~260MB for X11+Chromium)"
echo ""

print_success "Installation successful!"
