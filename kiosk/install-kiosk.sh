#!/bin/bash

################################################################################
# CalendarBot Kiosk - Automated Installation Script
################################################################################
# This script automates the installation and configuration of the CalendarBot
# kiosk system with full idempotency support.
#
# Usage:
#   sudo ./install-kiosk.sh --config install-config.yaml [options]
#
# Options:
#   --config FILE       Configuration file (required)
#   --dry-run          Show what would be done without making changes
#   --update           Update existing installation
#   --section N        Install only section N (1-4)
#   --verbose          Enable verbose output
#   --help             Show this help message
#
# Exit codes:
#   0 = Success
#   1 = General error
#   2 = Missing dependencies
#   3 = Configuration error
#   4 = Permission error
#
################################################################################

set -euo pipefail

# Script version
VERSION="1.0.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE=""
DRY_RUN=false
UPDATE_MODE=false
SPECIFIC_SECTION=""
VERBOSE=false
BACKUP_DIR=""
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Installation state tracking
declare -A INSTALLED_STATE
declare -A CHANGED_FILES

################################################################################
# Utility Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[VERBOSE]${NC} $*"
    fi
}

log_dry_run() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} $*"
    fi
}

die() {
    log_error "$1"
    exit "${2:-1}"
}

check_root() {
    # Allow tests to bypass root check
    if [[ "${TEST_MODE:-false}" == "true" ]]; then
        log_verbose "Running in TEST_MODE - bypassing root check"
        return 0
    fi

    if [[ $EUID -ne 0 ]]; then
        die "This script must be run as root (use sudo)" 4
    fi
}

show_help() {
    tail -n +3 "$0" | head -n 28 | grep "^#" | sed 's/^# \?//'
    exit 0
}

################################################################################
# YAML Parser (simple key=value extraction)
################################################################################

parse_yaml() {
    local yaml_file="$1"
    local prefix="${2:-}"

    if [[ ! -f "$yaml_file" ]]; then
        die "Configuration file not found: $yaml_file" 3
    fi

    # Simple YAML parser for our specific format
    # Handles: key: value, key: "value", and nested keys (converts to key_subkey)
    local s='[[:space:]]*'
    local w='[a-zA-Z0-9_]*'
    local fs=$(echo @|tr @ '\034')

    sed -ne "s|^\($s\):|\1|" \
        -e "s|^\($s\)\($w\)$s:$s[\"']\(.*\)[\"']$s\$|\1$fs\2$fs\3|p" \
        -e "s|^\($s\)\($w\)$s:$s\(.*\)$s\$|\1$fs\2$fs\3|p" "$yaml_file" |
    awk -F"$fs" '{
        indent = length($1)/2;
        vname[indent] = $2;
        for (i in vname) {if (i > indent) {delete vname[i]}}
        if (length($3) > 0) {
            vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])("_")}
            printf("%s%s%s=%s\n", "'"$prefix"'", vn, $2, $3);
        }
    }' | grep -v '^#' | grep -v '^[[:space:]]*$'
}

load_config() {
    log_info "Loading configuration from: $CONFIG_FILE"

    # Parse YAML and export as environment variables
    while IFS='=' read -r key value; do
        # Remove quotes from value
        value="${value%\"}"
        value="${value#\"}"
        value="${value%\'}"
        value="${value#\'}"

        # Export to environment
        export "CFG_${key}=${value}"
        log_verbose "Config: $key = $value"
    done < <(parse_yaml "$CONFIG_FILE" "")

    # Validate required configuration
    validate_config
}

validate_config() {
    log_info "Validating configuration..."

    local errors=0

    # Check required fields based on enabled sections
    if [[ "${CFG_sections_section_1_base:-true}" == "true" ]]; then
        if [[ -z "${CFG_system_username:-}" ]]; then
            log_error "Missing required config: system.username"
            errors=$((errors + 1))
        fi

        if [[ -z "${CFG_calendarbot_ics_url:-}" ]] || [[ "${CFG_calendarbot_ics_url}" == *"YOUR_CALENDAR"* ]]; then
            log_error "Missing or invalid config: calendarbot.ics_url"
            errors=$((errors + 1))
        fi
    fi

    if [[ "${CFG_sections_section_3_alexa:-false}" == "true" ]]; then
        if [[ -z "${CFG_alexa_domain:-}" ]] || [[ "${CFG_alexa_domain}" == *"ashwoodgrove"* ]]; then
            log_warning "Alexa domain not customized: ${CFG_alexa_domain:-none}"
        fi
    fi

    if [[ $errors -gt 0 ]]; then
        die "Configuration validation failed with $errors error(s)" 3
    fi

    log_success "Configuration validated"
}

################################################################################
# State Detection
################################################################################

detect_current_state() {
    log_info "Detecting current installation state..."

    # Check if repository exists
    if [[ -d "${CFG_system_repo_dir:-/home/${CFG_system_username}/calendarBot}" ]]; then
        INSTALLED_STATE[repo_exists]=true
        log_verbose "Repository: Found"
    else
        INSTALLED_STATE[repo_exists]=false
        log_verbose "Repository: Not found"
    fi

    # Check if virtual environment exists
    if [[ -d "${CFG_system_venv_dir:-${CFG_system_repo_dir:-/home/${CFG_system_username}/calendarBot}/venv}" ]]; then
        INSTALLED_STATE[venv_exists]=true
        log_verbose "Virtual environment: Found"
    else
        INSTALLED_STATE[venv_exists]=false
        log_verbose "Virtual environment: Not found"
    fi

    # Check if CalendarBot service exists
    if systemctl list-unit-files | grep -q "calendarbot-kiosk@"; then
        INSTALLED_STATE[service_base]=true
        log_verbose "CalendarBot service: Installed"
    else
        INSTALLED_STATE[service_base]=false
        log_verbose "CalendarBot service: Not installed"
    fi

    # Check if watchdog service exists
    if systemctl list-unit-files | grep -q "calendarbot-kiosk-watchdog@"; then
        INSTALLED_STATE[service_watchdog]=true
        log_verbose "Watchdog service: Installed"
    else
        INSTALLED_STATE[service_watchdog]=false
        log_verbose "Watchdog service: Not installed"
    fi

    # Check if Caddy is installed
    if command -v caddy &> /dev/null; then
        INSTALLED_STATE[caddy_installed]=true
        log_verbose "Caddy: Installed"
    else
        INSTALLED_STATE[caddy_installed]=false
        log_verbose "Caddy: Not installed"
    fi

    # Check if X server is installed
    if command -v startx &> /dev/null; then
        INSTALLED_STATE[xserver_installed]=true
        log_verbose "X server: Installed"
    else
        INSTALLED_STATE[xserver_installed]=false
        log_verbose "X server: Not installed"
    fi

    # Check if user exists
    if id "${CFG_system_username}" &>/dev/null; then
        INSTALLED_STATE[user_exists]=true
        log_verbose "User ${CFG_system_username}: Exists"
    else
        INSTALLED_STATE[user_exists]=false
        die "User ${CFG_system_username} does not exist. Please create it first." 3
    fi

    log_success "State detection complete"
}

################################################################################
# Backup Functions
################################################################################

backup_file() {
    local file="$1"
    local backup_dir="${CFG_installation_backup_dir:-/var/backups/calendarbot}"

    if [[ ! -f "$file" ]]; then
        log_verbose "No backup needed for $file (doesn't exist)"
        return 0
    fi

    if [[ "${CFG_installation_backup_enabled:-true}" != "true" ]]; then
        log_verbose "Backups disabled, skipping: $file"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would backup: $file"
        return 0
    fi

    mkdir -p "$backup_dir"
    local backup_name="$(basename "$file").$TIMESTAMP.bak"
    cp -a "$file" "$backup_dir/$backup_name"
    log_verbose "Backed up: $file -> $backup_dir/$backup_name"
    CHANGED_FILES["$file"]="$backup_dir/$backup_name"
}

################################################################################
# Package Installation
################################################################################

install_apt_packages() {
    local packages=("$@")
    local to_install=()

    # Check which packages are not installed
    for pkg in "${packages[@]}"; do
        if ! dpkg -l | grep -q "^ii  $pkg "; then
            to_install+=("$pkg")
        else
            log_verbose "Package already installed: $pkg"
        fi
    done

    if [[ ${#to_install[@]} -eq 0 ]]; then
        log_verbose "All packages already installed"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would install packages: ${to_install[*]}"
        return 0
    fi

    log_info "Installing packages: ${to_install[*]}"
    DEBIAN_FRONTEND=noninteractive apt-get install -y "${to_install[@]}"
}

update_apt() {
    if [[ "${CFG_advanced_apt_update:-true}" != "true" ]]; then
        log_verbose "APT update disabled in config"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would run: apt-get update"
        return 0
    fi

    log_info "Updating package lists..."
    apt-get update -qq
}

upgrade_apt() {
    if [[ "${CFG_advanced_apt_upgrade:-false}" != "true" ]]; then
        log_verbose "APT upgrade disabled in config"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would run: apt-get upgrade"
        return 0
    fi

    log_info "Upgrading system packages (this may take a while)..."
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
}

################################################################################
# SECTION 1: Base CalendarBot Installation
################################################################################

install_section_1_base() {
    log_info "===== SECTION 1: Base CalendarBot Installation ====="

    # Install system dependencies
    log_info "Installing base system dependencies..."
    install_apt_packages \
        python3 python3-pip python3-venv python3-dev \
        build-essential git curl jq htop

    # Set up repository
    local repo_dir="${CFG_system_repo_dir:-/home/${CFG_system_username}/calendarBot}"
    local repo_owner="${CFG_system_username}"

    if [[ "${INSTALLED_STATE[repo_exists]}" == "false" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would clone repository to: $repo_dir"
        else
            log_info "Cloning repository..."
            local parent_dir="$(dirname "$repo_dir")"
            sudo -u "$repo_owner" mkdir -p "$parent_dir"
            sudo -u "$repo_owner" git clone https://github.com/YOUR_USERNAME/calendarBot.git "$repo_dir" || \
                die "Failed to clone repository. Please check the URL." 1
        fi
    else
        log_info "Repository already exists: $repo_dir"
        if [[ "${CFG_advanced_git_auto_pull:-false}" == "true" ]]; then
            if [[ "$DRY_RUN" == "true" ]]; then
                log_dry_run "Would pull latest changes"
            else
                log_info "Pulling latest changes..."
                sudo -u "$repo_owner" git -C "$repo_dir" pull
            fi
        fi
    fi

    # Create virtual environment
    local venv_dir="${CFG_system_venv_dir:-$repo_dir/venv}"

    if [[ "${INSTALLED_STATE[venv_exists]}" == "false" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would create virtual environment: $venv_dir"
        else
            log_info "Creating virtual environment..."
            sudo -u "$repo_owner" python3 -m venv "$venv_dir"
        fi
    else
        log_info "Virtual environment already exists: $venv_dir"
    fi

    # Install Python packages
    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would install Python packages from requirements.txt"
    else
        log_info "Installing Python packages..."
        sudo -u "$repo_owner" bash -c "source '$venv_dir/bin/activate' && pip install --upgrade pip && pip install -r '$repo_dir/requirements.txt'"
    fi

    # Configure .env file
    local env_file="$repo_dir/.env"

    if [[ ! -f "$env_file" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would create .env file from template"
        else
            log_info "Creating .env file from template..."
            sudo -u "$repo_owner" cp "$repo_dir/.env.example" "$env_file"
        fi
    else
        log_info ".env file already exists"
        backup_file "$env_file"
    fi

    # Update .env with configuration
    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would update .env with configuration values"
    else
        log_info "Updating .env configuration..."
        update_env_file "$env_file"
    fi

    # Deploy systemd service
    local service_file="/etc/systemd/system/calendarbot-kiosk@.service"
    local source_service="$repo_dir/kiosk/service/calendarbot-kiosk.service"

    if [[ ! -f "$service_file" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would deploy systemd service: $service_file"
        else
            log_info "Deploying CalendarBot systemd service..."
            cp "$source_service" "$service_file"
            systemctl daemon-reload
        fi
    else
        log_info "CalendarBot service already deployed"
        if [[ "$UPDATE_MODE" == "true" ]]; then
            backup_file "$service_file"
            if [[ "$DRY_RUN" == "true" ]]; then
                log_dry_run "Would update service file"
            else
                log_info "Updating service file..."
                cp "$source_service" "$service_file"
                systemctl daemon-reload
            fi
        fi
    fi

    # Enable and start service
    local service_name="calendarbot-kiosk@${CFG_system_username}.service"

    if ! systemctl is-enabled "$service_name" &>/dev/null; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would enable service: $service_name"
        else
            log_info "Enabling CalendarBot service..."
            systemctl enable "$service_name"
        fi
    else
        log_info "Service already enabled: $service_name"
    fi

    if ! systemctl is-active "$service_name" &>/dev/null; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would start service: $service_name"
        else
            log_info "Starting CalendarBot service..."
            systemctl start "$service_name"
        fi
    else
        log_info "Service already running: $service_name"
        if [[ "$UPDATE_MODE" == "true" ]]; then
            if [[ "$DRY_RUN" == "true" ]]; then
                log_dry_run "Would restart service: $service_name"
            else
                log_info "Restarting service to apply updates..."
                systemctl restart "$service_name"
            fi
        fi
    fi

    # Configure auto-login
    configure_autologin

    # Verify installation
    if [[ "${CFG_installation_run_verification:-true}" == "true" ]] && [[ "$DRY_RUN" == "false" ]]; then
        verify_section_1
    fi

    log_success "Section 1 (Base CalendarBot) installation complete"
}

update_env_file() {
    local env_file="$1"

    # Update or add configuration values
    set_env_value "$env_file" "CALENDARBOT_ICS_URL" "${CFG_calendarbot_ics_url}"
    set_env_value "$env_file" "CALENDARBOT_WEB_HOST" "${CFG_calendarbot_web_host:-0.0.0.0}"
    set_env_value "$env_file" "CALENDARBOT_WEB_PORT" "${CFG_calendarbot_web_port:-8080}"
    set_env_value "$env_file" "CALENDARBOT_REFRESH_INTERVAL" "${CFG_calendarbot_refresh_interval:-300}"
    set_env_value "$env_file" "CALENDARBOT_DEBUG" "${CFG_calendarbot_debug:-false}"
    set_env_value "$env_file" "CALENDARBOT_LOG_LEVEL" "${CFG_calendarbot_log_level:-INFO}"
    set_env_value "$env_file" "CALENDARBOT_NONINTERACTIVE" "${CFG_calendarbot_noninteractive:-true}"

    # Set ownership
    chown "${CFG_system_username}:${CFG_system_username}" "$env_file"
}

set_env_value() {
    local file="$1"
    local key="$2"
    local value="$3"

    if grep -q "^${key}=" "$file"; then
        # Update existing value
        sed -i "s|^${key}=.*|${key}=${value}|" "$file"
        log_verbose "Updated .env: $key"
    else
        # Add new value
        echo "${key}=${value}" >> "$file"
        log_verbose "Added to .env: $key"
    fi
}

configure_autologin() {
    local autologin_dir="/etc/systemd/system/getty@tty1.service.d"
    local autologin_file="$autologin_dir/autologin.conf"

    if [[ -f "$autologin_file" ]]; then
        log_info "Auto-login already configured"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would configure auto-login for: ${CFG_system_username}"
        return 0
    fi

    log_info "Configuring auto-login for: ${CFG_system_username}"
    mkdir -p "$autologin_dir"

    cat > "$autologin_file" <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin ${CFG_system_username} --noclear %I \$TERM
EOF

    systemctl daemon-reload
}

verify_section_1() {
    log_info "Verifying Section 1 installation..."

    local errors=0

    # Check if service is running
    if ! systemctl is-active "calendarbot-kiosk@${CFG_system_username}.service" &>/dev/null; then
        log_error "CalendarBot service is not running"
        errors=$((errors + 1))
    fi

    # Check if API is responding
    sleep 2  # Give service a moment to start
    if ! curl -s http://localhost:${CFG_calendarbot_web_port:-8080}/health &>/dev/null; then
        log_warning "API health check failed (service may still be starting)"
    fi

    if [[ $errors -eq 0 ]]; then
        log_success "Section 1 verification passed"
    else
        log_warning "Section 1 verification completed with $errors error(s)"
    fi
}

################################################################################
# SECTION 2: Kiosk Mode & Watchdog
################################################################################

install_section_2_kiosk() {
    log_info "===== SECTION 2: Kiosk Mode & Watchdog ====="

    # Install X server and browser
    log_info "Installing X server and browser packages..."
    install_apt_packages \
        xserver-xorg xinit x11-xserver-utils \
        matchbox-window-manager chromium \
        xdotool dbus-x11

    # Install PyYAML
    local repo_dir="${CFG_system_repo_dir:-/home/${CFG_system_username}/calendarBot}"
    local venv_dir="${CFG_system_venv_dir:-$repo_dir/venv}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would install PyYAML in virtual environment"
    else
        log_info "Installing PyYAML..."
        sudo -u "${CFG_system_username}" bash -c "source '$venv_dir/bin/activate' && pip install PyYAML"
    fi

    # Deploy .xinitrc
    local xinitrc_file="/home/${CFG_system_username}/.xinitrc"
    local source_xinitrc="$repo_dir/kiosk/config/.xinitrc"

    backup_file "$xinitrc_file"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would deploy .xinitrc"
    else
        log_info "Deploying .xinitrc..."
        cp "$source_xinitrc" "$xinitrc_file"
        chmod +x "$xinitrc_file"
        chown "${CFG_system_username}:${CFG_system_username}" "$xinitrc_file"

        # Update browser URL if customized
        if [[ -n "${CFG_kiosk_browser_url:-}" ]]; then
            sed -i "s|http://localhost:8080/whatsnext.html|${CFG_kiosk_browser_url}|g" "$xinitrc_file"
        fi
    fi

    # Deploy .bash_profile
    local bash_profile_file="/home/${CFG_system_username}/.bash_profile"
    local source_bash_profile="$repo_dir/kiosk/config/.bash-profile"

    backup_file "$bash_profile_file"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would deploy .bash_profile"
    else
        log_info "Deploying .bash_profile..."
        cp "$source_bash_profile" "$bash_profile_file"
        chown "${CFG_system_username}:${CFG_system_username}" "$bash_profile_file"
    fi

    # Deploy watchdog daemon
    local watchdog_bin="/usr/local/bin/calendarbot-watchdog"
    local source_watchdog="$repo_dir/kiosk/config/calendarbot-watchdog"

    backup_file "$watchdog_bin"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would deploy watchdog daemon"
    else
        log_info "Deploying watchdog daemon..."
        cp "$source_watchdog" "$watchdog_bin"
        chmod +x "$watchdog_bin"
    fi

    # Deploy watchdog configuration
    local monitor_config_dir="/etc/calendarbot-monitor"
    local monitor_config_file="$monitor_config_dir/monitor.yaml"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would deploy watchdog configuration to $monitor_config_file"
    else
        log_info "Deploying watchdog configuration..."
        mkdir -p "$monitor_config_dir"
        backup_file "$monitor_config_file"
        create_monitor_config "$monitor_config_file"
    fi

    # Create watchdog directories
    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would create watchdog directories"
    else
        log_info "Creating watchdog directories..."
        mkdir -p /var/log/calendarbot-watchdog
        mkdir -p /var/local/calendarbot-watchdog
        chown -R "${CFG_system_username}:${CFG_system_username}" /var/log/calendarbot-watchdog
        chown -R "${CFG_system_username}:${CFG_system_username}" /var/local/calendarbot-watchdog
    fi

    # Initialize state file
    local state_file="/var/local/calendarbot-watchdog/state.json"

    if [[ ! -f "$state_file" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would initialize watchdog state file"
        else
            log_info "Initializing watchdog state file..."
            cat > "$state_file" <<'EOF'
{
  "browser_restarts": [],
  "service_restarts": [],
  "reboots": [],
  "last_recovery_time": null,
  "consecutive_failures": 0,
  "degraded_mode": false,
  "browser_escalation_level": 0,
  "browser_escalation_time": null
}
EOF
            chown "${CFG_system_username}:${CFG_system_username}" "$state_file"
        fi
    else
        log_info "Watchdog state file already exists (preserving)"
    fi

    # Deploy watchdog systemd service
    local watchdog_service="/etc/systemd/system/calendarbot-kiosk-watchdog@.service"
    local source_watchdog_service="$repo_dir/kiosk/service/calendarbot-kiosk-watchdog@.service"

    if [[ -f "$source_watchdog_service" ]]; then
        backup_file "$watchdog_service"

        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would deploy watchdog service"
        else
            log_info "Deploying watchdog service..."
            cp "$source_watchdog_service" "$watchdog_service"
            systemctl daemon-reload
        fi
    else
        log_warning "Watchdog service file not found in repo, creating basic service..."
        if [[ "$DRY_RUN" == "false" ]]; then
            create_watchdog_service "$watchdog_service"
            systemctl daemon-reload
        fi
    fi

    # Configure sudoers
    configure_sudoers

    # Enable and start watchdog service
    local watchdog_service_name="calendarbot-kiosk-watchdog@${CFG_system_username}.service"

    if ! systemctl is-enabled "$watchdog_service_name" &>/dev/null; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would enable watchdog service"
        else
            log_info "Enabling watchdog service..."
            systemctl enable "$watchdog_service_name"
        fi
    else
        log_info "Watchdog service already enabled"
    fi

    if ! systemctl is-active "$watchdog_service_name" &>/dev/null; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would start watchdog service"
        else
            log_info "Starting watchdog service..."
            systemctl start "$watchdog_service_name"
        fi
    else
        log_info "Watchdog service already running"
        if [[ "$UPDATE_MODE" == "true" ]]; then
            if [[ "$DRY_RUN" == "true" ]]; then
                log_dry_run "Would restart watchdog service"
            else
                log_info "Restarting watchdog service..."
                systemctl restart "$watchdog_service_name"
            fi
        fi
    fi

    # Verify installation
    if [[ "${CFG_installation_run_verification:-true}" == "true" ]] && [[ "$DRY_RUN" == "false" ]]; then
        verify_section_2
    fi

    log_success "Section 2 (Kiosk & Watchdog) installation complete"
    log_info "NOTE: Reboot required for kiosk mode to auto-start via auto-login"
}

create_monitor_config() {
    local config_file="$1"

    cat > "$config_file" <<EOF
health_check:
  interval_s: ${CFG_kiosk_watchdog_health_check_interval:-30}
  browser_heartbeat_timeout_s: ${CFG_kiosk_watchdog_browser_heartbeat_timeout:-120}
  startup_grace_period_s: ${CFG_kiosk_watchdog_startup_grace_period:-300}
  service_name: "calendarbot-kiosk@${CFG_system_username}.service"
  api_base_url: "http://localhost:${CFG_calendarbot_web_port:-8080}"

thresholds:
  browser_heartbeat_fail_count: ${CFG_kiosk_watchdog_thresholds_browser_heartbeat_fail_count:-2}
  max_browser_restarts_per_hour: ${CFG_kiosk_watchdog_thresholds_max_browser_restarts_per_hour:-4}
  max_service_restarts_per_hour: ${CFG_kiosk_watchdog_thresholds_max_service_restarts_per_hour:-2}
  max_reboots_per_day: ${CFG_kiosk_watchdog_thresholds_max_reboots_per_day:-1}
  recovery_cooldown_s: ${CFG_kiosk_watchdog_thresholds_recovery_cooldown_s:-60}

recovery:
  browser_soft_reload:
    reload_cmd: "DISPLAY=:0 xdotool search --class chromium windowactivate --sync key F5"
    reload_delay_s: ${CFG_kiosk_watchdog_recovery_reload_delay_s:-15}
  browser_restart:
    restart_cmd: "pkill -TERM chromium"
    verification_delay_s: ${CFG_kiosk_watchdog_recovery_browser_restart_delay_s:-30}
  x_restart:
    restart_cmd: "pkill -TERM Xorg"
    verification_delay_s: ${CFG_kiosk_watchdog_recovery_x_restart_delay_s:-60}
  service_restart:
    restart_cmd: "sudo systemctl restart calendarbot-kiosk@${CFG_system_username}.service"
    verification_delay_s: 30
  system_reboot:
    reboot_cmd: "sudo /sbin/reboot"

logging:
  log_dir: "/var/log/calendarbot-watchdog"
  log_level: "INFO"
  json_logging: true
  max_log_size_mb: 10

state:
  state_file: "/var/local/calendarbot-watchdog/state.json"
  backup_on_write: true
EOF
}

create_watchdog_service() {
    local service_file="$1"

    cat > "$service_file" <<EOF
[Unit]
Description=CalendarBot Kiosk Watchdog for %i
After=network.target calendarbot-kiosk@%i.service
Requires=calendarbot-kiosk@%i.service

[Service]
Type=simple
User=%i
WorkingDirectory=/home/%i/calendarBot
ExecStart=/usr/local/bin/calendarbot-watchdog --config /etc/calendarbot-monitor/monitor.yaml
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
}

configure_sudoers() {
    local sudoers_file="/etc/sudoers.d/calendarbot-watchdog"

    if [[ -f "$sudoers_file" ]]; then
        log_info "Sudoers configuration already exists"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would configure sudoers for watchdog"
        return 0
    fi

    log_info "Configuring sudoers for watchdog..."

    cat > "$sudoers_file" <<EOF
${CFG_system_username} ALL=NOPASSWD: /sbin/reboot
${CFG_system_username} ALL=NOPASSWD: /bin/systemctl restart calendarbot-kiosk@*.service
${CFG_system_username} ALL=NOPASSWD: /bin/systemctl status calendarbot-kiosk@*.service
EOF

    chmod 440 "$sudoers_file"

    # Verify syntax
    if ! visudo -c -f "$sudoers_file" &>/dev/null; then
        log_error "Sudoers syntax check failed!"
        rm -f "$sudoers_file"
        die "Failed to configure sudoers" 1
    fi
}

verify_section_2() {
    log_info "Verifying Section 2 installation..."

    local errors=0

    # Check if watchdog service is running
    if ! systemctl is-active "calendarbot-kiosk-watchdog@${CFG_system_username}.service" &>/dev/null; then
        log_error "Watchdog service is not running"
        errors=$((errors + 1))
    fi

    # Check if watchdog binary exists and is executable
    if [[ ! -x "/usr/local/bin/calendarbot-watchdog" ]]; then
        log_error "Watchdog binary not found or not executable"
        errors=$((errors + 1))
    fi

    # Check if state file exists
    if [[ ! -f "/var/local/calendarbot-watchdog/state.json" ]]; then
        log_error "Watchdog state file not found"
        errors=$((errors + 1))
    fi

    if [[ $errors -eq 0 ]]; then
        log_success "Section 2 verification passed"
    else
        log_warning "Section 2 verification completed with $errors error(s)"
    fi
}

################################################################################
# SECTION 3: Alexa Integration
################################################################################

install_section_3_alexa() {
    log_info "===== SECTION 3: Alexa Integration ====="

    # Install Caddy
    if [[ "${INSTALLED_STATE[caddy_installed]}" == "false" ]]; then
        log_info "Installing Caddy..."
        install_caddy
    else
        log_info "Caddy already installed"
    fi

    # Generate bearer token if not provided
    local bearer_token="${CFG_alexa_bearer_token:-}"

    if [[ -z "$bearer_token" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would generate bearer token"
            bearer_token="DRY_RUN_TOKEN_PLACEHOLDER"
        else
            log_info "Generating bearer token..."
            bearer_token=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
            log_success "Bearer token generated (save this for AWS Lambda configuration):"
            log_info "TOKEN: $bearer_token"
        fi
    else
        log_info "Using provided bearer token from configuration"
    fi

    # Update .env with bearer token
    local env_file="${CFG_system_repo_dir:-/home/${CFG_system_username}/calendarBot}/.env"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would add bearer token to .env"
    else
        log_info "Adding bearer token to .env..."
        set_env_value "$env_file" "CALENDARBOT_ALEXA_BEARER_TOKEN" "$bearer_token"

        # Restart CalendarBot service to apply token
        log_info "Restarting CalendarBot service to apply bearer token..."
        systemctl restart "calendarbot-kiosk@${CFG_system_username}.service"
    fi

    # Deploy Caddyfile
    deploy_caddyfile

    # Configure firewall
    if [[ "${CFG_alexa_firewall_enabled:-true}" == "true" ]]; then
        configure_firewall
    fi

    # Start Caddy
    if ! systemctl is-enabled caddy &>/dev/null; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would enable Caddy service"
        else
            log_info "Enabling Caddy service..."
            systemctl enable caddy
        fi
    fi

    if ! systemctl is-active caddy &>/dev/null; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would start Caddy service"
        else
            log_info "Starting Caddy service..."
            # Note: Caddy may fail to start if backend service isn't running yet
            # This is expected during installation - Caddy will start on next reboot
            if ! systemctl start caddy; then
                log_warning "Caddy service failed to start (backend may not be running yet)"
                log_warning "Caddy will be started automatically on next system boot"
            fi
        fi
    else
        if [[ "$DRY_RUN" == "true" ]]; then
            log_dry_run "Would reload Caddy service"
        else
            log_info "Reloading Caddy service..."
            systemctl reload caddy || log_warning "Caddy reload failed"
        fi
    fi

    # Display manual steps
    log_info "==== MANUAL STEPS REQUIRED ===="
    log_warning "The following steps cannot be automated and must be completed manually:"
    log_warning "1. Configure DNS A record: ${CFG_alexa_domain} -> Your public IP"
    log_warning "2. Configure router port forwarding: 80, 443 -> Pi"
    log_warning "3. Deploy AWS Lambda function (see kiosk/docs/MANUAL_STEPS.md)"
    log_warning "4. Create Alexa skill (see kiosk/docs/MANUAL_STEPS.md)"
    log_warning "5. Configure Lambda with bearer token: $bearer_token"
    log_info "==============================="

    # Verify installation
    if [[ "${CFG_installation_run_verification:-true}" == "true" ]] && [[ "$DRY_RUN" == "false" ]]; then
        verify_section_3
    fi

    log_success "Section 3 (Alexa Integration) installation complete"
}

install_caddy() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would install Caddy"
        return 0
    fi

    log_info "Adding Caddy repository..."
    apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl

    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
        gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg

    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
        tee /etc/apt/sources.list.d/caddy-stable.list

    apt-get update
    apt-get install -y caddy
}

deploy_caddyfile() {
    local caddyfile="/etc/caddy/Caddyfile"
    local repo_dir="${CFG_system_repo_dir:-/home/${CFG_system_username}/calendarBot}"
    local source_caddyfile="$repo_dir/kiosk/config/enhanced_caddyfile"

    backup_file "$caddyfile"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would deploy Caddyfile for domain: ${CFG_alexa_domain}"
        return 0
    fi

    log_info "Deploying Caddyfile for domain: ${CFG_alexa_domain}"

    # Create log directory
    mkdir -p /var/log/caddy
    chown caddy:caddy /var/log/caddy

    # Copy and customize Caddyfile
    if [[ -f "$source_caddyfile" ]]; then
        cp "$source_caddyfile" "$caddyfile"
        # Replace domain placeholder
        sed -i "s/ashwoodgrove\.net/${CFG_alexa_domain}/g" "$caddyfile"
    else
        # Create basic Caddyfile
        cat > "$caddyfile" <<EOF
${CFG_alexa_domain} {
    reverse_proxy localhost:${CFG_calendarbot_web_port:-8080} {
        header_up Authorization {header.Authorization}
        header_up Host {host}
        header_up X-Real-IP {remote}
        header_up X-Forwarded-For {remote}
        header_up X-Forwarded-Proto {scheme}
    }

    log {
        output file /var/log/caddy/access.log
        format json
    }
}

# Debug endpoint to verify header forwarding
${CFG_alexa_domain}/debug-headers {
    respond "Authorization: {header.Authorization}" 200
}
EOF
    fi
}

configure_firewall() {
    if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
        log_info "UFW already active"
        return 0
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would configure UFW firewall"
        return 0
    fi

    log_info "Configuring UFW firewall..."
    apt-get install -y ufw

    # Allow SSH first (important!)
    if [[ "${CFG_alexa_firewall_allow_ssh:-true}" == "true" ]]; then
        ufw allow 22/tcp
    fi

    # Allow HTTP/HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp

    # Enable firewall
    echo "y" | ufw enable

    log_success "UFW firewall configured and enabled"
}

verify_section_3() {
    log_info "Verifying Section 3 installation..."

    local errors=0

    # Check if Caddy is running
    if ! systemctl is-active caddy &>/dev/null; then
        log_warning "Caddy service is not running (will start on system boot)"
        errors=$((errors + 1))
    fi

    # Check if Caddyfile exists
    if [[ ! -f "/etc/caddy/Caddyfile" ]]; then
        log_error "Caddyfile not found"
        errors=$((errors + 1))
    fi

    # Check if bearer token is set in .env
    local env_file="${CFG_system_repo_dir:-/home/${CFG_system_username}/calendarBot}/.env"
    if ! grep -q "CALENDARBOT_ALEXA_BEARER_TOKEN" "$env_file"; then
        log_error "Bearer token not set in .env"
        errors=$((errors + 1))
    fi

    if [[ $errors -eq 0 ]]; then
        log_success "Section 3 verification passed"
    else
        log_warning "Section 3 verification completed with $errors error(s)"
    fi
}

################################################################################
# SECTION 4: Monitoring & Log Management
################################################################################

install_section_4_monitoring() {
    log_info "===== SECTION 4: Monitoring & Log Management ====="

    local repo_dir="${CFG_system_repo_dir:-/home/${CFG_system_username}/calendarBot}"

    # Deploy logrotate configuration
    if [[ "${CFG_monitoring_logrotate_enabled:-true}" == "true" ]]; then
        deploy_logrotate
    fi

    # Deploy rsyslog configuration (optional)
    if [[ "${CFG_monitoring_rsyslog_enabled:-false}" == "true" ]]; then
        deploy_rsyslog
    fi

    # Deploy monitoring scripts
    deploy_monitoring_scripts

    # Configure cron jobs
    if [[ "${CFG_monitoring_reports_enabled:-true}" == "true" ]]; then
        configure_monitoring_cron
    fi

    # Configure log shipping (optional)
    if [[ "${CFG_monitoring_log_shipping_enabled:-false}" == "true" ]]; then
        configure_log_shipping
    fi

    # Verify installation
    if [[ "${CFG_installation_run_verification:-true}" == "true" ]] && [[ "$DRY_RUN" == "false" ]]; then
        verify_section_4
    fi

    log_success "Section 4 (Monitoring & Log Management) installation complete"
}

deploy_logrotate() {
    local logrotate_file="/etc/logrotate.d/calendarbot-watchdog"
    local repo_dir="${CFG_system_repo_dir:-/home/${CFG_system_username}/calendarBot}"
    local source_logrotate="$repo_dir/kiosk/config/logrotate-calendarbot-watchdog"

    backup_file "$logrotate_file"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would deploy logrotate configuration"
        return 0
    fi

    log_info "Deploying logrotate configuration..."

    if [[ -f "$source_logrotate" ]]; then
        cp "$source_logrotate" "$logrotate_file"
    else
        create_logrotate_config "$logrotate_file"
    fi
}

create_logrotate_config() {
    local config_file="$1"

    cat > "$config_file" <<EOF
/var/log/calendarbot-watchdog/*.log {
    daily
    rotate ${CFG_monitoring_logrotate_watchdog_retention_days:-7}
    compress
    delaycompress
    missingok
    notifempty
    create 0640 ${CFG_system_username} ${CFG_system_username}
}

/var/local/calendarbot-watchdog/state.json {
    weekly
    rotate ${CFG_monitoring_logrotate_state_retention_weeks:-4}
    compress
    missingok
    notifempty
    create 0640 ${CFG_system_username} ${CFG_system_username}
}
EOF
}

deploy_rsyslog() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would deploy rsyslog configuration"
        return 0
    fi

    log_info "Installing rsyslog packages..."
    install_apt_packages rsyslog rsyslog-mmjsonparse

    local rsyslog_file="/etc/rsyslog.d/50-calendarbot.conf"
    backup_file "$rsyslog_file"

    log_info "Deploying rsyslog configuration..."

    mkdir -p /var/log/calendarbot
    chown syslog:adm /var/log/calendarbot

    cat > "$rsyslog_file" <<'EOF'
# CalendarBot structured logging

# Load JSON parsing module
module(load="mmjsonparse")

# Filter CalendarBot messages
if $programname == 'calendarbot' then {
    action(type="omfile" file="/var/log/calendarbot/server.log")
}

if $programname == 'calendarbot-watchdog' then {
    action(type="omfile" file="/var/log/calendarbot/watchdog.log")
}

# Critical events only
if $programname startswith 'calendarbot' and $syslogseverity <= 3 then {
    action(type="omfile" file="/var/log/calendarbot/critical.log")
}
EOF

    systemctl restart rsyslog
}

deploy_monitoring_scripts() {
    local repo_dir="${CFG_system_repo_dir:-/home/${CFG_system_username}/calendarBot}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would deploy monitoring scripts"
        return 0
    fi

    log_info "Deploying monitoring scripts..."

    # Create report directories
    mkdir -p /var/local/calendarbot-watchdog/reports
    mkdir -p /var/local/calendarbot-watchdog/cache
    chown -R "${CFG_system_username}:${CFG_system_username}" /var/local/calendarbot-watchdog

    # Copy scripts if they exist in repo
    for script in log-aggregator.sh monitoring-status.sh log-shipper.sh; do
        local source="$repo_dir/kiosk/scripts/$script"
        if [[ -f "$source" ]]; then
            cp "$source" "/usr/local/bin/$script"
            chmod +x "/usr/local/bin/$script"
            log_verbose "Deployed: $script"
        else
            log_warning "Script not found in repo: $script (skipping)"
        fi
    done
}

configure_monitoring_cron() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would configure monitoring cron jobs"
        return 0
    fi

    log_info "Configuring monitoring cron jobs..."

    local daily_time="${CFG_monitoring_reports_daily_report_time:-01:00}"
    local weekly_time="${CFG_monitoring_reports_weekly_report_time:-02:00}"
    local cleanup_time="${CFG_monitoring_reports_cleanup_time:-03:00}"
    local status_interval="${CFG_monitoring_status_updates_interval_minutes:-5}"
    local status_output="${CFG_monitoring_status_updates_output_file:-/var/www/html/calendarbot-status.json}"

    # Parse time into cron format (HH:MM -> MM HH)
    local daily_cron=$(echo "$daily_time" | awk -F: '{print $2" "$1}')
    local weekly_cron=$(echo "$weekly_time" | awk -F: '{print $2" "$1}')
    local cleanup_cron=$(echo "$cleanup_time" | awk -F: '{print $2" "$1}')

    # Get current crontab for user
    local temp_cron=$(mktemp)
    sudo -u "${CFG_system_username}" crontab -l 2>/dev/null > "$temp_cron" || true

    # Remove existing CalendarBot cron jobs
    sed -i '/calendarbot/d' "$temp_cron"

    # Add new cron jobs
    cat >> "$temp_cron" <<EOF
# CalendarBot monitoring jobs (managed by install-kiosk.sh)
$daily_cron * * * /usr/local/bin/log-aggregator.sh daily \$(date +\\%Y-\\%m-\\%d) >> /var/log/calendarbot-watchdog/aggregator.log 2>&1
$weekly_cron * * 1 /usr/local/bin/log-aggregator.sh weekly \$(date -d 'last monday' +\\%Y-\\%m-\\%d) >> /var/log/calendarbot-watchdog/aggregator.log 2>&1
$cleanup_cron * * * /usr/local/bin/log-aggregator.sh cleanup >> /var/log/calendarbot-watchdog/aggregator.log 2>&1
*/$status_interval * * * * /usr/local/bin/monitoring-status.sh status $status_output 2>&1
EOF

    # Install new crontab (pipe through stdin to avoid permission issues)
    cat "$temp_cron" | sudo -u "${CFG_system_username}" crontab -
    rm -f "$temp_cron"

    log_success "Monitoring cron jobs configured"
}

configure_log_shipping() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry_run "Would configure log shipping"
        return 0
    fi

    log_info "Configuring log shipping..."

    # Update /etc/environment with webhook config
    local env_file="/etc/environment"
    backup_file "$env_file"

    # Add webhook configuration
    cat >> "$env_file" <<EOF

# CalendarBot log shipping configuration
CALENDARBOT_LOG_SHIPPER_ENABLED=${CFG_monitoring_log_shipping_enabled:-true}
CALENDARBOT_WEBHOOK_URL=${CFG_monitoring_log_shipping_webhook_url:-}
CALENDARBOT_WEBHOOK_TOKEN=${CFG_monitoring_log_shipping_webhook_token:-}
CALENDARBOT_WEBHOOK_TIMEOUT=${CFG_monitoring_log_shipping_webhook_timeout:-10}
CALENDARBOT_WEBHOOK_INSECURE=${CFG_monitoring_log_shipping_webhook_insecure:-false}
EOF

    log_warning "Log shipping configured. Manual setup of shipper service may be required."
    log_warning "See kiosk/docs/4_LOG_MANAGEMENT.md for details."
}

verify_section_4() {
    log_info "Verifying Section 4 installation..."

    local errors=0

    # Check if logrotate config exists
    if [[ ! -f "/etc/logrotate.d/calendarbot-watchdog" ]]; then
        log_error "Logrotate configuration not found"
        errors=$((errors + 1))
    fi

    # Check if monitoring scripts exist
    if [[ ! -f "/usr/local/bin/log-aggregator.sh" ]]; then
        log_warning "log-aggregator.sh not found"
    fi

    # Check if cron jobs are configured
    if ! sudo -u "${CFG_system_username}" crontab -l 2>/dev/null | grep -q "calendarbot"; then
        log_warning "Monitoring cron jobs not configured"
    fi

    if [[ $errors -eq 0 ]]; then
        log_success "Section 4 verification passed"
    else
        log_warning "Section 4 verification completed with $errors error(s)"
    fi
}

################################################################################
# Main Installation Logic
################################################################################

main() {
    log_info "====================================================="
    log_info "CalendarBot Kiosk Automated Installation v$VERSION"
    log_info "====================================================="

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --update)
                UPDATE_MODE=true
                shift
                ;;
            --section)
                SPECIFIC_SECTION="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                show_help
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                ;;
        esac
    done

    # Validate arguments
    if [[ -z "$CONFIG_FILE" ]]; then
        die "Configuration file required. Use: --config <file>" 3
    fi

    if [[ ! -f "$CONFIG_FILE" ]]; then
        die "Configuration file not found: $CONFIG_FILE" 3
    fi

    # Check prerequisites
    check_root

    # Load and validate configuration
    load_config

    # Detect current state
    detect_current_state

    # Set update mode from config if not set via CLI
    if [[ "${CFG_installation_update_mode:-false}" == "true" ]] && [[ "$UPDATE_MODE" == "false" ]]; then
        UPDATE_MODE=true
        log_info "Update mode enabled from configuration"
    fi

    # Show dry-run notice
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "DRY-RUN MODE: No changes will be made to the system"
    fi

    # Update package lists
    update_apt
    upgrade_apt

    # Install sections based on configuration or specific section
    if [[ -n "$SPECIFIC_SECTION" ]]; then
        case $SPECIFIC_SECTION in
            1)
                install_section_1_base
                ;;
            2)
                install_section_2_kiosk
                ;;
            3)
                install_section_3_alexa
                ;;
            4)
                install_section_4_monitoring
                ;;
            *)
                die "Invalid section number: $SPECIFIC_SECTION (must be 1-4)" 3
                ;;
        esac
    else
        # Install based on configuration
        if [[ "${CFG_sections_section_1_base:-true}" == "true" ]]; then
            install_section_1_base
        fi

        if [[ "${CFG_sections_section_2_kiosk:-true}" == "true" ]]; then
            install_section_2_kiosk
        fi

        if [[ "${CFG_sections_section_3_alexa:-false}" == "true" ]]; then
            install_section_3_alexa
        fi

        if [[ "${CFG_sections_section_4_monitoring:-false}" == "true" ]]; then
            install_section_4_monitoring
        fi
    fi

    # Show summary
    log_info "====================================================="
    log_success "Installation complete!"
    log_info "====================================================="

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "This was a dry-run. No changes were made."
        log_info "Remove --dry-run flag to perform actual installation."
    else
        # Show backup information
        if [[ "${!CHANGED_FILES[@]}" ]]; then
            log_info "Backups created:"
            for file in "${!CHANGED_FILES[@]}"; do
                log_info "  $file -> ${CHANGED_FILES[$file]}"
            done
        fi

        # Reboot recommendation
        if [[ "${CFG_sections_section_2_kiosk:-false}" == "true" ]] || [[ "$SPECIFIC_SECTION" == "2" ]]; then
            log_warning "REBOOT RECOMMENDED: Kiosk mode requires reboot to auto-start"
            if [[ "${CFG_installation_auto_reboot:-false}" == "true" ]]; then
                log_warning "Auto-reboot enabled. System will reboot in 10 seconds..."
                log_warning "Press Ctrl+C to cancel"
                sleep 10
                /sbin/reboot
            else
                log_info "Run: sudo reboot"
            fi
        fi
    fi

    log_info "For manual steps (DNS, AWS, Alexa), see: kiosk/docs/MANUAL_STEPS.md"
    log_info "For usage guide, see: kiosk/docs/AUTOMATED_INSTALLATION.md"

    exit 0
}

# Run main function
main "$@"
