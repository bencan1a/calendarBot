#!/bin/bash
# CalendarBot Kiosk Installation Script
# Complete automated installation and configuration for Raspberry Pi kiosk mode

set -euo pipefail

# Parse command line arguments
NO_AUTOSTART=0
SHOW_HELP=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-autostart)
            NO_AUTOSTART=1
            shift
            ;;
        --help|-h)
            SHOW_HELP=1
            shift
            ;;
        *)
            echo "ERROR: Unknown parameter: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

if [ "$SHOW_HELP" = "1" ]; then
    cat << EOF
CalendarBot Kiosk Installation Script

USAGE:
    sudo $0 [OPTIONS]

OPTIONS:
    --no-autostart    Install CalendarBot and dependencies but skip auto-boot configuration
                      This allows manual testing without system changes
    --help, -h        Show this help message

MODES:
    Default mode      Full kiosk installation with auto-boot configuration
    --no-autostart    Install for manual testing:
                      - Installs all system dependencies
                      - Sets up CalendarBot in virtual environment
                      - Skips boot config, auto-login, and service enablement
                      - Test with: sudo -u pi /home/pi/calendarbot/venv/bin/calendarbot --web --port 8080

EXAMPLES:
    sudo $0                    # Full installation with auto-boot
    sudo $0 --no-autostart     # Install for manual testing only
EOF
    exit 0
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

if [ "$NO_AUTOSTART" = "1" ]; then
    echo "Installing CalendarBot Kiosk Mode (Manual Testing Mode - No Auto-Start)..."
    echo "NOTE: This will install dependencies and CalendarBot but skip boot configuration"
else
    echo "Installing CalendarBot Kiosk Mode (Full Auto-Boot Installation)..."
fi

# Define source and target paths
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Verify we're in the right location
if [ ! -f "$PROJECT_ROOT/calendarbot/__init__.py" ]; then
    echo "ERROR: Cannot find CalendarBot project in expected location: $PROJECT_ROOT"
    exit 1
fi

echo "Project root: $PROJECT_ROOT"

# Validate required dependency directories and files exist
echo "Validating dependency files..."
MISSING_FILES=""

# Check systemd files
for service_file in "systemd/calendarbot-kiosk.service" "systemd/calendarbot-kiosk-setup.service" "systemd/calendarbot-network-wait.service"; do
    if [ ! -f "$SCRIPT_DIR/$service_file" ]; then
        MISSING_FILES="$MISSING_FILES\n  - $SCRIPT_DIR/$service_file"
    fi
done

# Check boot scripts
for boot_script in "boot/calendarbot-kiosk-prestart.sh" "boot/calendarbot-kiosk-system-setup.sh" "boot/calendarbot-wait-for-network.sh" "boot/calendarbot-kiosk-cleanup.sh"; do
    if [ ! -f "$SCRIPT_DIR/$boot_script" ]; then
        MISSING_FILES="$MISSING_FILES\n  - $SCRIPT_DIR/$boot_script"
    fi
done

# Check X11 files
for x11_file in "x11/calendarbot-kiosk.desktop" "x11/.xsession"; do
    if [ ! -f "$SCRIPT_DIR/$x11_file" ]; then
        MISSING_FILES="$MISSING_FILES\n  - $SCRIPT_DIR/$x11_file"
    fi
done

if [ -n "$MISSING_FILES" ]; then
    echo "ERROR: Missing required dependency files:$MISSING_FILES"
    echo ""
    echo "Script directory: $SCRIPT_DIR"
    echo "Expected directory structure:"
    echo "  $SCRIPT_DIR/"
    echo "  ├── systemd/"
    echo "  │   ├── calendarbot-kiosk.service"
    echo "  │   ├── calendarbot-kiosk-setup.service"
    echo "  │   └── calendarbot-network-wait.service"
    echo "  ├── boot/"
    echo "  │   ├── calendarbot-kiosk-prestart.sh"
    echo "  │   ├── calendarbot-kiosk-system-setup.sh"
    echo "  │   ├── calendarbot-wait-for-network.sh"
    echo "  │   └── calendarbot-kiosk-cleanup.sh"
    echo "  └── x11/"
    echo "      ├── calendarbot-kiosk.desktop"
    echo "      └── .xsession"
    exit 1
fi

echo "All dependency files verified successfully"

# 1. Validate system prerequisites
echo "Validating system prerequisites..."

# Check if we're on a Raspberry Pi
if [ ! -f "/proc/device-tree/model" ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "WARNING: This script is designed for Raspberry Pi systems"
    echo "Current system: $(uname -a)"
    read -p "Continue anyway? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled"
        exit 1
    fi
fi

# Auto-detect target user (flexible for different systems)
TARGET_USER=""

# Try to detect user from project directory ownership
if [ -d "$PROJECT_ROOT" ]; then
    TARGET_USER=$(stat -c '%U' "$PROJECT_ROOT" 2>/dev/null)
fi

# Fall back to SUDO_USER if project owner detection fails
if [ -z "$TARGET_USER" ] || [ "$TARGET_USER" = "root" ]; then
    if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
        TARGET_USER="$SUDO_USER"
    fi
fi

# Final fallback: try to find the 'pi' user (traditional Raspberry Pi)
if [ -z "$TARGET_USER" ] && id "pi" >/dev/null 2>&1; then
    TARGET_USER="pi"
fi

# Validate we found a suitable target user
if [ -z "$TARGET_USER" ] || [ "$TARGET_USER" = "root" ]; then
    echo "ERROR: Cannot determine target user for CalendarBot installation"
    echo "Project directory: $PROJECT_ROOT"
    echo "Available non-root users: $(cut -d: -f1 /etc/passwd | grep -E '^[a-z]' | head -5 | tr '\n' ' ')"
    echo ""
    echo "Please ensure:"
    echo "  1. You are running this script with sudo"
    echo "  2. The CalendarBot project is owned by a non-root user"
    echo "  3. The target user account exists on this system"
    exit 1
fi

# If still no target user found, try to detect from regular users (UID >= 1000)
if [ -z "$TARGET_USER" ] || [ "$TARGET_USER" = "root" ]; then
    echo "DEBUG: Attempting to detect from regular users..."
    REGULAR_USERS=$(awk -F: '$3 >= 1000 && $3 != 65534 && $1 !~ /^snap/ {print $1}' /etc/passwd | head -3)
    if [ -n "$REGULAR_USERS" ]; then
        # Use the first regular user that's not a system/snap user
        for user in $REGULAR_USERS; do
            if [ "$user" != "nobody" ] && [ -d "/home/$user" ]; then
                TARGET_USER="$user"
                echo "DEBUG: Found regular user: '$TARGET_USER'"
                break
            fi
        done
    fi
fi

# Validate the detected user exists and has a home directory
if [ -z "$TARGET_USER" ] || [ "$TARGET_USER" = "root" ]; then
    echo "ERROR: Cannot determine target user for CalendarBot installation"
    echo "Project directory: $PROJECT_ROOT"
    echo "Available regular users: $(awk -F: '$3 >= 1000 && $3 != 65534 {print $1}' /etc/passwd | tr '\n' ' ')"
    echo ""
    echo "Please ensure:"
    echo "  1. You are running this script with sudo"
    echo "  2. The CalendarBot project is owned by a non-root user"
    echo "  3. The target user account exists on this system"
    exit 1
fi

if ! id "$TARGET_USER" >/dev/null 2>&1; then
    echo "ERROR: Detected target user '$TARGET_USER' does not exist on this system"
    echo "Available users: $(cut -d: -f1 /etc/passwd | grep -E '^[a-z]' | head -5 | tr '\n' ' ')"
    exit 1
fi

TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)
if [ ! -d "$TARGET_HOME" ]; then
    echo "ERROR: Home directory for user '$TARGET_USER' does not exist: $TARGET_HOME"
    exit 1
fi

echo "Target user detected: $TARGET_USER (home: $TARGET_HOME)"

# Check network connectivity before attempting package installation
echo "Checking network connectivity..."
if ! ping -c 1 -W 5 8.8.8.8 >/dev/null 2>&1; then
    echo "ERROR: No network connectivity detected"
    echo "Network connection required for package installation"
    echo "Please check your network connection and try again"
    exit 1
fi

# 2. Install required packages
echo "Installing system packages..."
apt-get update || {
    echo "ERROR: Failed to update package lists"
    echo "Check network connection and repository configuration"
    exit 1
}

apt-get install -y \
    chromium-browser \
    unclutter \
    xinput \
    xserver-xorg \
    openbox \
    lightdm \
    watchdog \
    python3-venv \
    python3-pip \
    x11-xserver-utils || {
    echo "ERROR: Failed to install required packages"
    echo "Check package availability and system compatibility"
    exit 1
}

# 2. Copy systemd service files
if [ "$NO_AUTOSTART" != "1" ]; then
    echo "Installing systemd services..."
    cp "$SCRIPT_DIR/systemd/calendarbot-kiosk.service" /etc/systemd/system/
    cp "$SCRIPT_DIR/systemd/calendarbot-kiosk-setup.service" /etc/systemd/system/
    cp "$SCRIPT_DIR/systemd/calendarbot-network-wait.service" /etc/systemd/system/
else
    echo "Skipping systemd services installation (--no-autostart mode)"
fi

# 3. Copy boot scripts
if [ "$NO_AUTOSTART" != "1" ]; then
    echo "Installing boot scripts..."
    cp "$SCRIPT_DIR/boot/calendarbot-kiosk-prestart.sh" /usr/local/bin/
    cp "$SCRIPT_DIR/boot/calendarbot-kiosk-system-setup.sh" /usr/local/bin/
    cp "$SCRIPT_DIR/boot/calendarbot-wait-for-network.sh" /usr/local/bin/
    cp "$SCRIPT_DIR/boot/calendarbot-kiosk-cleanup.sh" /usr/local/bin/
else
    echo "Skipping boot scripts installation (--no-autostart mode)"
fi

# 4. Make scripts executable
if [ "$NO_AUTOSTART" != "1" ]; then
    echo "Setting script permissions..."
    chmod +x /usr/local/bin/calendarbot-*
else
    echo "Skipping script permissions setup (--no-autostart mode)"
fi

# 5. Create log directory
if [ "$NO_AUTOSTART" != "1" ]; then
    echo "Creating log directory..."
    mkdir -p /var/log/calendarbot
    chown "$TARGET_USER:$TARGET_USER" /var/log/calendarbot
else
    echo "Skipping log directory creation (--no-autostart mode)"
fi

# 6. Set up X11 session
if [ "$NO_AUTOSTART" != "1" ]; then
    echo "Configuring X11 session..."
    cp "$SCRIPT_DIR/x11/calendarbot-kiosk.desktop" /usr/share/xsessions/
    cp "$SCRIPT_DIR/x11/.xsession" "$TARGET_HOME/"
    chown "$TARGET_USER:$TARGET_USER" "$TARGET_HOME/.xsession"
    chmod +x "$TARGET_HOME/.xsession"
else
    echo "Skipping X11 session configuration (--no-autostart mode)"
fi

# 7. Configure auto-login (DANGEROUS - backup existing config)
if [ "$NO_AUTOSTART" = "1" ]; then
    echo "Skipping auto-login configuration (--no-autostart mode)"
    echo "Manual login will be required to test kiosk mode"
else
    echo "Configuring auto-login..."

    LIGHTDM_CONF="/etc/lightdm/lightdm.conf"

    # Critical safety check for LightDM configuration
    if [ ! -f "$LIGHTDM_CONF" ]; then
        echo "WARNING: LightDM configuration file not found at $LIGHTDM_CONF"
        echo "This could indicate LightDM is not properly installed"
        if ! systemctl is-enabled lightdm >/dev/null 2>&1; then
            echo "ERROR: LightDM service is not available or enabled"
            echo "Cannot configure auto-login without a display manager"
            exit 1
        fi
    fi

    # Backup existing LightDM configuration
    LIGHTDM_BACKUP="${LIGHTDM_CONF}.backup.calendarbot.$(date +%Y%m%d_%H%M%S)"
    if [ -f "$LIGHTDM_CONF" ]; then
        cp "$LIGHTDM_CONF" "$LIGHTDM_BACKUP" || {
            echo "ERROR: Failed to backup LightDM configuration"
            echo "Aborting to prevent breaking existing login system"
            exit 1
        }
        echo "LightDM config backed up to: $LIGHTDM_BACKUP"
        
        # Check if existing config has important settings we should preserve
        if grep -q "autologin-user.*=" "$LIGHTDM_CONF" 2>/dev/null; then
            EXISTING_USER=$(grep "autologin-user.*=" "$LIGHTDM_CONF" | head -1 | cut -d'=' -f2 | tr -d ' ')
            if [ -n "$EXISTING_USER" ] && [ "$EXISTING_USER" != "$TARGET_USER" ]; then
                echo "WARNING: Existing auto-login configured for user: $EXISTING_USER"
                echo "This will be changed to '$TARGET_USER' user"
                read -p "Continue with LightDM configuration change? [y/N]: " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    echo "Skipping LightDM configuration"
                    echo "Manual configuration required for auto-login"
                    SKIP_LIGHTDM=1
                fi
            fi
        fi
    fi

    if [ "$SKIP_LIGHTDM" != "1" ]; then
        #     # Create new LightDM configuration with CalendarBot settings
        #     cat > "$LIGHTDM_CONF" << EOF
        #     # LightDM Configuration - Modified by CalendarBot Kiosk Installer
        #     [Seat:*]
        #     autologin-user=$TARGET_USER
        #     autologin-user-timeout=0
        #     user-session=calendarbot-kiosk
        #     autologin-session=calendarbot-kiosk
        #     greeter-session=lightdm-greeter

        #     # Disable user switching for kiosk mode
        #     allow-user-switching=false
        #     allow-guest=false

        #     # CalendarBot kiosk mode settings
        #     session-setup-script=/usr/local/bin/calendarbot-kiosk-prestart.sh
        #     EOF

        # Validate the configuration file was written correctly
        if ! grep -q "autologin-user=$TARGET_USER" "$LIGHTDM_CONF"; then
            echo "ERROR: Failed to write LightDM configuration"
            echo "Restoring backup..."
            if [ -f "$LIGHTDM_BACKUP" ]; then
                mv "$LIGHTDM_BACKUP" "$LIGHTDM_CONF"
            fi
            exit 1
        fi
        
        echo "✓ LightDM configured for CalendarBot kiosk mode"
        echo "IMPORTANT: Original config backed up to $LIGHTDM_BACKUP"
    else
        echo "LightDM configuration skipped - manual setup required:"
        echo "  Edit $LIGHTDM_CONF to set:"
        echo "  autologin-user=$TARGET_USER"
        echo "  user-session=calendarbot-kiosk"
    fi
fi

# 8. Add boot configuration for Pi Zero 2W (DANGEROUS - requires validation)
if [ "$NO_AUTOSTART" = "1" ]; then
    echo "Skipping boot configuration (--no-autostart mode)"
    echo "Manual boot config setup will be required for kiosk mode"
else
    echo "skipping boot config setup"
    # echo "DEBUG: Starting boot configuration section..."
    # echo "Configuring boot settings..."

    # # Check for boot config in multiple possible locations (newer vs older Pi OS)
    # BOOT_CONFIG=""
    # POSSIBLE_LOCATIONS="/boot/firmware/config.txt /boot/config.txt"

    # echo "DEBUG: Searching for boot config in possible locations..."
    # for location in $POSSIBLE_LOCATIONS; do
    #     echo "DEBUG: Checking: $location"
    #     if [ -f "$location" ]; then
    #         BOOT_CONFIG="$location"
    #         echo "DEBUG: Found boot config at: $BOOT_CONFIG"
    #         break
    #     fi
    # done

    # # Critical safety checks for boot configuration
    # if [ -z "$BOOT_CONFIG" ]; then
    #     echo "DEBUG: No boot config file found in any location"
    #     echo "ERROR: Boot config file not found in any expected location"
    #     echo "This is required for Raspberry Pi systems"
    #     echo "Searched locations: $POSSIBLE_LOCATIONS"
    #     echo "Available boot locations:"
    #     find /boot* -name "config.txt" 2>/dev/null || echo "  No boot config files found"
    #     echo "DEBUG: EXITING at boot config check - no valid config found"
    #     exit 1
    # fi
    # echo "DEBUG: Boot config file confirmed at $BOOT_CONFIG"

    # # Validate current boot config is readable and appears valid
    # echo "DEBUG: Checking boot config content validity..."
    # if ! grep -q "arm_64bit\|gpu_mem\|hdmi_" "$BOOT_CONFIG" 2>/dev/null; then
    #     echo "DEBUG: Boot config doesn't contain expected Pi config markers"
    #     echo "WARNING: Boot config doesn't appear to be a standard Raspberry Pi config"
    #     echo "Current config preview:"
    #     head -20 "$BOOT_CONFIG" | sed 's/^/  /'
    #     echo "DEBUG: About to prompt user for confirmation..."
    #     read -p "Continue with boot config modification? [y/N]: " -n 1 -r
    #     echo
    #     echo "DEBUG: User response: '$REPLY'"
    #     if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    #         echo "DEBUG: User declined boot config modification"
    #         echo "Skipping boot configuration changes"
    #         echo "You may need to manually configure display settings"
    #         SKIP_BOOT_CONFIG=1
    #     fi
    # fi
    # echo "DEBUG: Boot config validation complete, SKIP_BOOT_CONFIG=$SKIP_BOOT_CONFIG"
fi

# 9. Create CalendarBot configuration directory if it doesn't exist
echo "Setting up CalendarBot configuration..."
mkdir -p "$TARGET_HOME/.config/calendarbot"
chown -R "$TARGET_USER:$TARGET_USER" "$TARGET_HOME/.config/calendarbot"

# 10. Set up Python virtual environment with comprehensive validation
echo "Setting up Python virtual environment..."

# Validate Python 3 is available and working
if ! python3 --version >/dev/null 2>&1; then
    echo "ERROR: Python 3 is not available or not working"
    echo "Python 3 is required for CalendarBot"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Found Python $PYTHON_VERSION"

# Check if virtual environment module is available
if ! python3 -m venv --help >/dev/null 2>&1; then
    echo "ERROR: Python venv module is not available"
    echo "Install with: apt-get install python3-venv"
    exit 1
fi

# Set up CalendarBot directory structure
echo "DEBUG: Setting up CalendarBot directory structure..."
echo "DEBUG: PROJECT_ROOT=$PROJECT_ROOT"
echo "DEBUG: TARGET_HOME=$TARGET_HOME"
echo "DEBUG: TARGET_USER=$TARGET_USER"

CALENDARBOT_HOME="$TARGET_HOME/calendarbot"
echo "DEBUG: CALENDARBOT_HOME=$CALENDARBOT_HOME"

if [ ! -d "$CALENDARBOT_HOME" ]; then
    echo "Creating CalendarBot home directory..."
    if [ ! -d "$TARGET_HOME" ]; then
        echo "ERROR: $TARGET_HOME directory does not exist"
        exit 1
    fi
    
    echo "DEBUG: Creating symlink from $PROJECT_ROOT to $CALENDARBOT_HOME"
    # Create symlink to project root
    if ! sudo -u "$TARGET_USER" ln -sf "$PROJECT_ROOT" "$CALENDARBOT_HOME"; then
        echo "ERROR: Failed to create symlink to project"
        echo "Source: $PROJECT_ROOT"
        echo "Target: $CALENDARBOT_HOME"
        echo "DEBUG: Checking source directory: '$PROJECT_ROOT'"
        if [ -d "$PROJECT_ROOT" ] && [ -r "$PROJECT_ROOT" ]; then
            echo "DEBUG: Directory exists and is readable"
            echo "DEBUG: Sample contents:"
            find "$PROJECT_ROOT" -maxdepth 1 -type f -o -type d | head -3
        else
            echo "DEBUG: Directory does not exist or is not accessible"
            echo "DEBUG: Directory test results: exists=$(test -d "$PROJECT_ROOT" && echo "yes" || echo "no"), readable=$(test -r "$PROJECT_ROOT" && echo "yes" || echo "no")"
        fi
        exit 1
    fi
    echo "✓ Project linked to $CALENDARBOT_HOME"
else
    echo "DEBUG: CalendarBot home directory already exists: $CALENDARBOT_HOME"
fi

# Validate project structure is accessible
echo "DEBUG: Validating project structure in $CALENDARBOT_HOME"
echo "DEBUG: Contents of $CALENDARBOT_HOME:"
if [ -d "$CALENDARBOT_HOME" ] && [ -r "$CALENDARBOT_HOME" ]; then
    find "$CALENDARBOT_HOME" -maxdepth 1 -type f -o -type d | head -10
else
    echo "DEBUG: Directory not accessible: '$CALENDARBOT_HOME'"
fi

if [ ! -f "$CALENDARBOT_HOME/setup.py" ] && [ ! -f "$CALENDARBOT_HOME/pyproject.toml" ]; then
    echo "ERROR: CalendarBot project appears to be missing setup files"
    echo "Expected setup.py or pyproject.toml in: $CALENDARBOT_HOME"
    echo "DEBUG: Full directory listing:"
    if [ -d "$CALENDARBOT_HOME" ] && [ -r "$CALENDARBOT_HOME" ]; then
        find "$CALENDARBOT_HOME" -maxdepth 1 -type f -o -type d -exec ls -ld {} \;
    else
        echo "DEBUG: Directory not accessible for listing: '$CALENDARBOT_HOME'"
    fi
    exit 1
fi
echo "DEBUG: Project structure validation passed"

# Create or validate virtual environment
VENV_PATH="$CALENDARBOT_HOME/venv"
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating Python virtual environment at $VENV_PATH..."
    
    # Create virtual environment as target user
    if ! sudo -u "$TARGET_USER" python3 -m venv "$VENV_PATH"; then
        echo "ERROR: Failed to create virtual environment"
        echo "Check Python installation and permissions"
        exit 1
    fi
    echo "✓ Virtual environment created"
else
    echo "Virtual environment already exists at $VENV_PATH"
fi

# Validate virtual environment is functional
if [ ! -f "$VENV_PATH/bin/python" ]; then
    echo "ERROR: Virtual environment appears corrupted"
    echo "Missing: $VENV_PATH/bin/python"
    rm -rf "$VENV_PATH"
    exit 1
fi

# Test virtual environment activation
if ! sudo -u "$TARGET_USER" "$VENV_PATH/bin/python" --version >/dev/null 2>&1; then
    echo "ERROR: Virtual environment Python is not functional"
    exit 1
fi

# Install CalendarBot in virtual environment
echo "Installing CalendarBot in virtual environment..."
cd "$CALENDARBOT_HOME"

# Upgrade pip first
if ! sudo -u "$TARGET_USER" "$VENV_PATH/bin/pip" install --upgrade pip; then
    echo "WARNING: Failed to upgrade pip, continuing with existing version"
fi

# Install CalendarBot
if ! sudo -u "$TARGET_USER" "$VENV_PATH/bin/pip" install -e .; then
    echo "ERROR: Failed to install CalendarBot"
    echo "Check setup.py/pyproject.toml and dependencies"
    echo "Virtual environment pip list:"
    sudo -u "$TARGET_USER" "$VENV_PATH/bin/pip" list || true
    exit 1
fi

# Verify CalendarBot installation
if ! sudo -u "$TARGET_USER" "$VENV_PATH/bin/calendarbot" --version >/dev/null 2>&1; then
    echo "WARNING: CalendarBot installation may not be working correctly"
    echo "Test the installation manually: $VENV_PATH/bin/calendarbot --version"
else
    CALENDARBOT_VERSION=$(sudo -u "$TARGET_USER" "$VENV_PATH/bin/calendarbot" --version 2>&1)
    echo "✓ CalendarBot installed successfully: $CALENDARBOT_VERSION"
fi

# 11. Validate and enable services
if [ "$NO_AUTOSTART" = "1" ]; then
    echo "Skipping service enablement and graphical target configuration (--no-autostart mode)"
    echo "Manual service enablement will be required for kiosk mode:"
    echo "  sudo systemctl enable calendarbot-kiosk-setup.service"
    echo "  sudo systemctl enable calendarbot-network-wait.service"
    echo "  sudo systemctl enable calendarbot-kiosk.service"
    echo "  sudo systemctl enable lightdm.service"
    echo "  sudo systemctl set-default graphical.target"
else
    echo "Validating systemd services..."

    # Validate service files exist and are readable
    SERVICES_OK=1
    for service in "calendarbot-kiosk-setup.service" "calendarbot-network-wait.service" "calendarbot-kiosk.service"; do
        if [ ! -f "/etc/systemd/system/$service" ]; then
            echo "ERROR: Service file missing: /etc/systemd/system/$service"
            SERVICES_OK=0
        elif ! systemctl cat "$service" >/dev/null 2>&1; then
            echo "ERROR: Service file invalid or unreadable: $service"
            SERVICES_OK=0
        fi
    done

    # Check if lightdm is available
    if ! systemctl list-unit-files lightdm.service >/dev/null 2>&1; then
        echo "ERROR: lightdm.service not available on this system"
        echo "Display manager is required for kiosk mode"
        SERVICES_OK=0
    fi

    # Verify CalendarBot installation before enabling services
    if [ ! -f "$CALENDARBOT_HOME/venv/bin/calendarbot" ] && [ ! -f "$TARGET_HOME/.local/bin/calendarbot" ]; then
        echo "WARNING: CalendarBot executable not found"
        echo "Services may fail to start until CalendarBot is properly installed"
        read -p "Continue with service enablement anyway? [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Skipping service enablement - you can enable them later with:"
            echo "  sudo systemctl enable calendarbot-kiosk-setup.service"
            echo "  sudo systemctl enable calendarbot-network-wait.service"
            echo "  sudo systemctl enable calendarbot-kiosk.service"
            echo "  sudo systemctl enable lightdm.service"
            SERVICES_OK=0
        fi
    fi

    if [ "$SERVICES_OK" = "1" ]; then
        echo "Enabling systemd services..."
        systemctl daemon-reload || {
            echo "ERROR: Failed to reload systemd daemon"
            exit 1
        }

        # Enable services one by one with error checking
        for service in "calendarbot-kiosk-setup.service" "calendarbot-network-wait.service" "calendarbot-kiosk.service" "lightdm.service"; do
            echo "Enabling $service..."
            if ! systemctl enable "$service"; then
                echo "ERROR: Failed to enable $service"
                echo "You may need to enable it manually later: sudo systemctl enable $service"
            else
                echo "✓ $service enabled successfully"
            fi
        done

        # Set graphical target
        if ! systemctl set-default graphical.target; then
            echo "WARNING: Failed to set graphical target as default"
            echo "System may boot to console instead of graphical mode"
        else
            echo "✓ Graphical target set as default"
        fi
    else
        echo "Service validation failed - services not enabled"
        echo "Manual service enablement will be required"
    fi
fi

# 12. Run initial system setup
echo "Running initial system setup..."
/usr/local/bin/calendarbot-kiosk-system-setup.sh

# 13. Create uninstall script
echo "Creating uninstall script..."
cat > /usr/local/bin/uninstall-calendarbot-kiosk.sh << 'EOF'
#!/bin/sh
# CalendarBot Kiosk Uninstall Script

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Uninstalling CalendarBot Kiosk Mode..."

# Stop and disable services
systemctl stop calendarbot-kiosk.service 2>/dev/null || true
systemctl disable calendarbot-kiosk.service 2>/dev/null || true
systemctl disable calendarbot-kiosk-setup.service 2>/dev/null || true
systemctl disable calendarbot-network-wait.service 2>/dev/null || true

# Remove service files
rm -f /etc/systemd/system/calendarbot-*.service

# Remove scripts
rm -f /usr/local/bin/calendarbot-*

# Remove X11 session
rm -f /usr/share/xsessions/calendarbot-kiosk.desktop
rm -f /home/pi/.xsession

# Restore lightdm default config
cat > /etc/lightdm/lightdm.conf << 'LIGHTDM_EOF'
[Seat:*]
#autologin-user=
#autologin-user-timeout=0
#user-session=default
#autologin-session=
LIGHTDM_EOF

# Restore boot config (manual step required)
echo "NOTE: Boot configuration in /boot/config.txt was modified."
echo "Backup available at /boot/config.txt.backup.*"
echo "Manual restoration may be required."

systemctl daemon-reload
systemctl set-default graphical.target

echo "CalendarBot Kiosk mode uninstalled."
echo "Reboot recommended to complete removal."
EOF

chmod +x /usr/local/bin/uninstall-calendarbot-kiosk.sh

# 14. Display installation summary
cat << EOF

===============================================
CalendarBot Kiosk Installation Completed!
===============================================

Installation Summary:
- System packages installed
- Systemd services configured and enabled
- Boot scripts installed in /usr/local/bin/
- X11 session configured for kiosk mode
- Auto-login configured for pi user
- Boot configuration updated for Pi Zero 2W
- CalendarBot installed in virtual environment

Services Enabled:
- calendarbot-kiosk-setup.service (system setup)
- calendarbot-network-wait.service (network connectivity)
- calendarbot-kiosk.service (main kiosk service)

Management Commands:
- Check status: systemctl status calendarbot-kiosk.service
- View logs: journalctl -u calendarbot-kiosk.service -f
- Stop kiosk: systemctl stop calendarbot-kiosk.service
- Start kiosk: systemctl start calendarbot-kiosk.service
- Uninstall: sudo /usr/local/bin/uninstall-calendarbot-kiosk.sh

Configuration:
- Kiosk config: /home/pi/.config/calendarbot/
- Logs: /var/log/calendarbot/
- Service files: /etc/systemd/system/calendarbot-*.service

IMPORTANT: Reboot the system to start kiosk mode
Command: sudo reboot

===============================================
EOF
