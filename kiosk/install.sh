#!/bin/bash

# CalendarBot Kiosk Installation Script
# Automates the installation of CalendarBot as a kiosk service using systemd templates

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
KIOSK_SERVICE_DIR="$SCRIPT_DIR/service"
KIOSK_SCRIPTS_DIR="$SCRIPT_DIR/scripts"
LOG_FILE="/tmp/calendarbot-kiosk-install.log"
CURRENT_USER="$(whoami)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Print functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Error handling
error_exit() {
    print_error "$1"
    print_error "Installation failed. Check log file: $LOG_FILE"
    exit 1
}

# Confirmation prompt
confirm() {
    local prompt="$1"
    local default="${2:-n}"
    local response
    
    if [[ "$default" == "y" ]]; then
        prompt="$prompt [Y/n]: "
    else
        prompt="$prompt [y/N]: "
    fi
    
    read -r -p "$prompt" response
    
    if [[ -z "$response" ]]; then
        response="$default"
    fi
    
    [[ "$response" =~ ^[Yy]$ ]]
}

# Check if running as root
check_not_root() {
    if [[ $EUID -eq 0 ]]; then
        error_exit "This script should not be run as root. Run as the user who will use the kiosk."
    fi
}

# Check if running on supported system
check_supported_system() {
    print_info "Checking system compatibility..."
    
    if [[ "$(uname -s)" != "Linux" ]]; then
        error_exit "This script only supports Linux systems."
    fi
    
    if ! command -v systemctl >/dev/null 2>&1; then
        error_exit "systemctl not found. This script requires systemd."
    fi
    
    print_success "System is compatible (Linux with systemd)"
}

# Check if CalendarBot is installed and working
check_calendarbot() {
    print_info "Checking CalendarBot installation..."
    
    if ! command -v calendarbot >/dev/null 2>&1; then
        error_exit "CalendarBot command not found. Please install CalendarBot first."
    fi
    
    local version_output
    if ! version_output=$(calendarbot --version 2>&1); then
        error_exit "CalendarBot --version failed. CalendarBot may not be properly installed."
    fi
    
    print_success "CalendarBot is installed: $version_output"
}

# Check for required dependencies
check_dependencies() {
    print_info "Checking required dependencies..."
    
    local missing_deps=()
    local deps=("chromium-browser" "openbox" "xdpyinfo" "xset" "curl" "unclutter")
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            missing_deps+=("$dep")
        fi
    done
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        print_info "Install them with: sudo apt-get install ${missing_deps[*]}"
        error_exit "Please install missing dependencies and run this script again."
    fi
    
    print_success "All required dependencies are installed"
}

# Check if in correct CalendarBot directory
check_project_directory() {
    print_info "Verifying CalendarBot project directory..."
    
    if [[ ! -f "$PROJECT_DIR/calendarbot/__init__.py" ]]; then
        error_exit "Not in CalendarBot project directory. Please run this script from the CalendarBot project root."
    fi
    
    if [[ ! -d "$KIOSK_SERVICE_DIR" ]] || [[ ! -d "$KIOSK_SCRIPTS_DIR" ]]; then
        error_exit "Kiosk directories not found: $KIOSK_SERVICE_DIR or $KIOSK_SCRIPTS_DIR"
    fi
    
    local required_files=(
        "$KIOSK_SERVICE_DIR/calendarbot-kiosk.service"
        "$KIOSK_SCRIPTS_DIR/start-kiosk.sh"
        "$KIOSK_SCRIPTS_DIR/.xinitrc"
        "$KIOSK_SCRIPTS_DIR/.bash-profile"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            error_exit "Required kiosk file not found: $file"
        fi
    done
    
    print_success "Project directory structure is valid"
}

# Install systemd service
install_service() {
    print_info "Installing systemd service..."
    
    local service_src="$KIOSK_SERVICE_DIR/calendarbot-kiosk.service"
    local service_dest="/etc/systemd/system/calendarbot-kiosk@.service"
    
    # Copy service file (requires sudo)
    if ! sudo cp "$service_src" "$service_dest"; then
        error_exit "Failed to copy service file to $service_dest"
    fi
    
    # Set proper permissions
    sudo chmod 644 "$service_dest"
    
    # Reload systemd daemon
    if ! sudo systemctl daemon-reload; then
        error_exit "Failed to reload systemd daemon"
    fi
    
    # Enable service for current user
    local user_service="calendarbot-kiosk@$CURRENT_USER.service"
    if ! sudo systemctl enable "$user_service"; then
        error_exit "Failed to enable service: $user_service"
    fi
    
    print_success "Systemd service installed and enabled: $user_service"
}

# Install kiosk scripts
install_kiosk_scripts() {
    print_info "Installing kiosk scripts and configuration files..."
    
    # Create bin directory if it doesn't exist
    mkdir -p "$HOME/bin"
    
    # Copy start-kiosk.sh to ~/bin
    local start_script_dest="$HOME/bin/start-kiosk.sh"
    if ! cp "$KIOSK_SCRIPTS_DIR/start-kiosk.sh" "$start_script_dest"; then
        error_exit "Failed to copy start-kiosk.sh to $start_script_dest"
    fi
    chmod +x "$start_script_dest"
    print_success "Installed start-kiosk.sh to $start_script_dest"
    
    # Copy .xinitrc to home directory
    local xinitrc_dest="$HOME/.xinitrc"
    if ! cp "$KIOSK_SCRIPTS_DIR/.xinitrc" "$xinitrc_dest"; then
        error_exit "Failed to copy .xinitrc to $xinitrc_dest"
    fi
    chmod +x "$xinitrc_dest"
    print_success "Installed .xinitrc to $xinitrc_dest"
    
    # Handle .bash_profile (append or create)
    local bash_profile_src="$KIOSK_SCRIPTS_DIR/.bash-profile"
    local bash_profile_dest="$HOME/.bash_profile"
    
    if [[ -f "$bash_profile_dest" ]]; then
        # Check if our content is already there
        if ! grep -q "startx" "$bash_profile_dest"; then
            print_info "Appending kiosk configuration to existing .bash_profile"
            {
                echo ""
                echo "# CalendarBot Kiosk Configuration"
                cat "$bash_profile_src"
            } >> "$bash_profile_dest"
        else
            print_warning ".bash_profile already contains kiosk configuration"
        fi
    else
        print_info "Creating new .bash_profile"
        cp "$bash_profile_src" "$bash_profile_dest"
    fi
    print_success "Updated .bash_profile for kiosk auto-start"
}

# Create necessary directories and set permissions
setup_directories() {
    print_info "Setting up directories and permissions..."
    
    # Create kiosk log directory
    local kiosk_dir="$HOME/kiosk"
    mkdir -p "$kiosk_dir"
    print_success "Created directory: $kiosk_dir"
    
    # Ensure ~/bin is in PATH for current session
    if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
        export PATH="$HOME/bin:$PATH"
        print_info "Added ~/bin to PATH for current session"
    fi
}

# Validate service installation
validate_service() {
    print_info "Validating service installation..."
    
    local user_service="calendarbot-kiosk@$CURRENT_USER.service"
    
    # Check if service file exists
    if [[ ! -f "/etc/systemd/system/calendarbot-kiosk@.service" ]]; then
        error_exit "Service file not found in systemd directory"
    fi
    
    # Check service status (should be enabled but not running)
    if ! systemctl is-enabled "$user_service" >/dev/null 2>&1; then
        error_exit "Service is not enabled: $user_service"
    fi
    
    print_success "Service validation passed"
}

# Test CalendarBot functionality
test_calendarbot() {
    print_info "Testing CalendarBot functionality..."
    
    # Change to project directory for test
    cd "$PROJECT_DIR"
    
    print_info "Starting CalendarBot web server for 10 seconds..."
    local pid
    
    # Start CalendarBot in background
    if calendarbot --web --port 8080 >/dev/null 2>&1 & pid=$!; then
        sleep 3
        
        # Test if CalendarBot is responding
        local test_url="http://localhost:8080"
        if curl --silent --fail --max-time 5 "$test_url" >/dev/null 2>&1; then
            print_success "CalendarBot web server is responding"
        else
            print_warning "CalendarBot web server is not responding (this may be normal)"
        fi
        
        # Stop CalendarBot
        kill "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
    else
        print_warning "Could not start CalendarBot for testing (this may be normal)"
    fi
}

# Provide user guidance
show_usage_instructions() {
    print_header "Installation Complete!"
    
    echo ""
    echo -e "${GREEN}CalendarBot Kiosk has been successfully installed!${NC}"
    echo ""
    echo -e "${BLUE}Service Management:${NC}"
    echo -e "• Start kiosk service:  ${YELLOW}sudo systemctl start calendarbot-kiosk@$CURRENT_USER.service${NC}"
    echo -e "• Stop kiosk service:   ${YELLOW}sudo systemctl stop calendarbot-kiosk@$CURRENT_USER.service${NC}"
    echo -e "• Service status:       ${YELLOW}sudo systemctl status calendarbot-kiosk@$CURRENT_USER.service${NC}"
    echo -e "• View service logs:    ${YELLOW}sudo journalctl -u calendarbot-kiosk@$CURRENT_USER.service -f${NC}"
    echo ""
    echo -e "${BLUE}Auto-Start Configuration:${NC}"
    echo "• The service is enabled and will start automatically on boot"
    echo "• User $CURRENT_USER will auto-login to X11 kiosk mode when logging into tty1"
    echo ""
    echo -e "${BLUE}Manual Kiosk Mode:${NC}"
    echo -e "• Start X11 manually:   ${YELLOW}startx${NC}"
    echo -e "• Run kiosk script:     ${YELLOW}~/bin/start-kiosk.sh${NC}"
    echo ""
    echo -e "${BLUE}Troubleshooting:${NC}"
    echo -e "• Installation log:     ${YELLOW}$LOG_FILE${NC}"
    echo -e "• Kiosk logs:          ${YELLOW}~/kiosk/kiosk.log${NC}"
    echo -e "• Check dependencies:   ${YELLOW}chromium-browser --version && openbox --version${NC}"
    echo -e "• Test CalendarBot:     ${YELLOW}calendarbot --web --port 8080${NC}"
    echo ""
    echo -e "${BLUE}Important Notes:${NC}"
    echo -e "• Ensure CalendarBot project is in: ${YELLOW}$PROJECT_DIR${NC}"
    echo -e "• The kiosk will display CalendarBot at: ${YELLOW}http://\$(hostname -I | awk '{print \$1}'):8080${NC}"
    echo -e "• To uninstall, run this script with: ${YELLOW}$0 --uninstall${NC}"
    echo ""
}

# Uninstall function
uninstall_kiosk() {
    print_header "Uninstalling CalendarBot Kiosk"
    
    if ! confirm "Are you sure you want to uninstall CalendarBot Kiosk?"; then
        print_info "Uninstall cancelled."
        exit 0
    fi
    
    local user_service="calendarbot-kiosk@$CURRENT_USER.service"
    
    # Stop and disable service
    sudo systemctl stop "$user_service" 2>/dev/null || true
    sudo systemctl disable "$user_service" 2>/dev/null || true
    
    # Remove service file
    sudo rm -f "/etc/systemd/system/calendarbot-kiosk@.service"
    sudo systemctl daemon-reload
    
    # Remove installed files
    rm -f "$HOME/bin/start-kiosk.sh"
    rm -f "$HOME/.xinitrc"
    
    # Remove kiosk configuration from .bash_profile
    if [[ -f "$HOME/.bash_profile" ]]; then
        # Create backup
        cp "$HOME/.bash_profile" "$HOME/.bash_profile.backup"
        # Remove our additions (simple approach - remove lines after our marker)
        sed -i '/# CalendarBot Kiosk Configuration/,$d' "$HOME/.bash_profile"
    fi
    
    print_success "CalendarBot Kiosk has been uninstalled"
    print_info "Backup of .bash_profile saved as .bash_profile.backup"
}

# Main installation function
main() {
    print_header "CalendarBot Kiosk Installation"
    
    log "Starting CalendarBot Kiosk installation at $(date)"
    log "Running as user: $CURRENT_USER"
    log "Project directory: $PROJECT_DIR"
    
    # Handle uninstall option
    if [[ "${1:-}" == "--uninstall" ]]; then
        uninstall_kiosk
        exit 0
    fi
    
    # Show installation summary
    cat << EOF
This script will install CalendarBot as a kiosk service with the following features:
• Systemd service that starts CalendarBot automatically
• X11 kiosk mode with Chromium browser
• Auto-login configuration for tty1
• Service management commands
• Comprehensive logging and error handling

The installation will:
1. Check system requirements and dependencies
2. Install systemd service template
3. Copy kiosk scripts and configuration files
4. Set up directories and permissions
5. Validate the installation
6. Provide usage instructions

EOF
    
    if ! confirm "Do you want to proceed with the installation?" "y"; then
        print_info "Installation cancelled."
        exit 0
    fi
    
    # Pre-installation checks
    print_header "Pre-Installation Checks"
    check_not_root
    check_supported_system
    check_calendarbot
    check_dependencies
    check_project_directory
    
    # Installation steps
    print_header "Installing CalendarBot Kiosk Service"
    install_service
    install_kiosk_scripts
    setup_directories
    
    # Validation
    print_header "Validating Installation"
    validate_service
    test_calendarbot
    
    # Success
    show_usage_instructions
    
    log "Installation completed successfully at $(date)"
    print_success "Installation log saved to: $LOG_FILE"
}

# Handle script interruption
trap 'print_error "Installation interrupted"; exit 1' INT TERM

# Run main function
main "$@"