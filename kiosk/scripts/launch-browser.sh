#!/bin/bash
# CalendarBot Kiosk Browser Launcher
# Compatible launcher script for both Chromium and Epiphany browsers
# Used by watchdog for browser restart recovery

set -euo pipefail

# Configuration
USER_HOME="${HOME:-/home/$(whoami)}"
DISPLAY="${DISPLAY:-:0}"
CALENDARBOT_URL="${CALENDARBOT_URL:-http://$(hostname -I | awk '{print $1}'):8080}"
BROWSER_TYPE="${BROWSER_TYPE:-auto}"  # auto, chromium, epiphany
LOG_FILE="${USER_HOME}/kiosk/browser-launch.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Check if URL is reachable
check_server() {
    local max_attempts=10
    local attempt=1
    
    log "Checking if CalendarBot server is available at $CALENDARBOT_URL..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl --silent --fail --max-time 5 "$CALENDARBOT_URL" >/dev/null 2>&1; then
            log "Server is reachable (attempt $attempt/$max_attempts)"
            return 0
        fi
        
        log "Server not ready, waiting... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    log "WARNING: Server not reachable after $max_attempts attempts, launching browser anyway"
    return 1
}

# Detect available browser
detect_browser() {
    if [ "$BROWSER_TYPE" != "auto" ]; then
        echo "$BROWSER_TYPE"
        return
    fi
    
    if command -v chromium >/dev/null 2>&1; then
        echo "chromium"
    elif command -v chromium-browser >/dev/null 2>&1; then
        echo "chromium-browser"
    elif command -v epiphany-browser >/dev/null 2>&1; then
        echo "epiphany"
    elif command -v epiphany >/dev/null 2>&1; then
        echo "epiphany"
    else
        log "ERROR: No supported browser found (chromium, epiphany)"
        exit 1
    fi
}

# Launch Chromium browser with kiosk optimizations
launch_chromium() {
    local browser_cmd="$1"
    
    log "Launching Chromium browser in kiosk mode..."
    
    # Set environment for low-end device optimization
    export LIBGL_ALWAYS_SOFTWARE=1
    export GSK_RENDERER=cairo
    export WEBKIT_DISABLE_COMPOSITING_MODE=1
    export WEBKIT_DISABLE_WEBGL=1
    export JSC_useJIT=0
    export GTK_A11Y=none
    export WEBKIT_DISABLE_MEDIACODECS=1
    
    # Chromium flags optimized for Pi Zero 2
    exec "$browser_cmd" \
        --no-memcheck \
        --kiosk \
        --enable-low-end-device-mode \
        --noerrdialogs \
        --no-first-run \
        --no-default-browser-check \
        --disable-session-crashed-bubble \
        --overscroll-history-navigation=0 \
        --disable-vulkan \
        --disable-gpu-compositing \
        --disable-background-networking \
        --disable-component-update \
        --disable-sync \
        --no-pings \
        --disable-features=NetworkService,OnDeviceModel,PushMessaging,UseGCMNetworkManager,NetworkServiceSandbox,OptimizationHints,Translate,HeavyAdIntervention,SubresourceWebBundles,PrivacySandboxAdsAPIs,InterestFeed,FeedV2 \
        --disable-extensions \
        --disable-plugins \
        --disable-dev-shm-usage \
        --disable-software-rasterizer \
        --disable-background-timer-throttling \
        --disable-renderer-backgrounding \
        --disable-backgrounding-occluded-windows \
        --window-position=0,0 \
        --window-size=800,480 \
        "$CALENDARBOT_URL" \
        >>"$LOG_FILE" 2>&1
}

# Launch Epiphany browser
launch_epiphany() {
    local browser_cmd="$1"
    
    log "Launching Epiphany browser in kiosk mode..."
    
    # Set environment for WebKit optimization
    export WEBKIT_DISABLE_COMPOSITING_MODE=1
    export WEBKIT_DISABLE_WEBGL=1
    export JSC_useJIT=0
    export GTK_A11Y=none
    export WEBKIT_DISABLE_MEDIACODECS=1
    
    exec "$browser_cmd" \
        --application-mode \
        --profile=/tmp/epiphany-kiosk-profile \
        "$CALENDARBOT_URL" \
        >>"$LOG_FILE" 2>&1
}

# Setup display and window manager check
setup_display() {
    export DISPLAY="$DISPLAY"
    
    # Verify X server is running
    if ! xdpyinfo >/dev/null 2>&1; then
        log "ERROR: X server not available on display $DISPLAY"
        return 1
    fi
    
    # Check if window manager is running, start if needed
    if ! pgrep -x "matchbox-window-manager\|openbox\|mutter\|metacity" >/dev/null; then
        log "Starting minimal window manager..."
        
        if command -v matchbox-window-manager >/dev/null 2>&1; then
            matchbox-window-manager -use_cursor no &
        elif command -v openbox >/dev/null 2>&1; then
            openbox &
        else
            log "WARNING: No window manager found, browser may not display correctly"
        fi
        
        # Give window manager time to start
        sleep 2
    fi
    
    # Configure display settings
    xset s off -dpms 2>/dev/null || true
    xset s noblank 2>/dev/null || true
    
    return 0
}

# Kill existing browser processes
cleanup_existing_browsers() {
    log "Cleaning up any existing browser processes..."
    
    # Kill chromium processes
    pkill -f "chromium.*--kiosk" 2>/dev/null || true
    pkill -f "chromium-browser.*--kiosk" 2>/dev/null || true
    
    # Kill epiphany processes  
    pkill -f "epiphany.*--application-mode" 2>/dev/null || true
    pkill -f "epiphany-browser.*--application-mode" 2>/dev/null || true
    
    # Give processes time to exit
    sleep 3
    
    # Force kill if still running
    pkill -9 -f "chromium.*--kiosk" 2>/dev/null || true
    pkill -9 -f "epiphany.*--application-mode" 2>/dev/null || true
    
    log "Browser cleanup completed"
}

# Main execution
main() {
    log "=== CalendarBot Browser Launcher Started ==="
    log "User: $(whoami), Display: $DISPLAY, URL: $CALENDARBOT_URL"
    
    # Ensure log directory exists
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Setup display environment
    if ! setup_display; then
        log "ERROR: Failed to setup display environment"
        exit 1
    fi
    
    # Cleanup any existing browsers
    cleanup_existing_browsers
    
    # Check server availability (non-blocking)
    check_server || true
    
    # Detect and launch browser
    local browser_type
    browser_type=$(detect_browser)
    
    log "Detected browser type: $browser_type"
    
    case "$browser_type" in
        chromium|chromium-browser)
            launch_chromium "$browser_type"
            ;;
        epiphany)
            launch_epiphany "epiphany-browser"
            ;;
        *)
            log "ERROR: Unsupported browser type: $browser_type"
            exit 1
            ;;
    esac
}

# Signal handlers for graceful shutdown
trap 'log "Received SIGTERM, shutting down..."; cleanup_existing_browsers; exit 0' TERM
trap 'log "Received SIGINT, shutting down..."; cleanup_existing_browsers; exit 0' INT

# Execute main function
main "$@"