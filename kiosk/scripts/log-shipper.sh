#!/bin/bash

# CalendarBot Remote Log Shipper
# Pi Zero 2 optimized script for shipping critical monitoring events to remote endpoints
# Integrates with journald and implements rate limiting, retry logic, and authentication

set -euo pipefail

# Script metadata
readonly SCRIPT_NAME="calendarbot-log-shipper"
readonly VERSION="1.0.0"
readonly STATE_DIR="/var/local/calendarbot-watchdog"
readonly RATE_LIMIT_FILE="$STATE_DIR/log-shipper-state.json"
readonly TEMP_DIR="/tmp/calendarbot-log-shipper"
readonly MAX_RETRIES=3
readonly RETRY_DELAY=5
readonly RATE_LIMIT_MINUTES=30
readonly MAX_PAYLOAD_SIZE=8192  # 8KB max payload for Pi Zero 2

# Default configuration
WEBHOOK_URL="${CALENDARBOT_WEBHOOK_URL:-}"
WEBHOOK_TOKEN="${CALENDARBOT_WEBHOOK_TOKEN:-}"
WEBHOOK_TIMEOUT="${CALENDARBOT_WEBHOOK_TIMEOUT:-10}"
DEBUG_MODE="${CALENDARBOT_LOG_SHIPPER_DEBUG:-false}"
ENABLED="${CALENDARBOT_LOG_SHIPPER_ENABLED:-false}"

# Logging functions
log_info() {
    echo "$(date -Iseconds) [INFO] $*" >&2
    if command -v logger >/dev/null 2>&1; then
        logger -t "$SCRIPT_NAME" -p daemon.info "$*" 2>/dev/null || true
    fi
}

log_warn() {
    echo "$(date -Iseconds) [WARN] $*" >&2
    if command -v logger >/dev/null 2>&1; then
        logger -t "$SCRIPT_NAME" -p daemon.warning "$*" 2>/dev/null || true
    fi
}

log_error() {
    echo "$(date -Iseconds) [ERROR] $*" >&2
    if command -v logger >/dev/null 2>&1; then
        logger -t "$SCRIPT_NAME" -p daemon.error "$*" 2>/dev/null || true
    fi
}

log_debug() {
    if [[ "$DEBUG_MODE" == "true" ]]; then
        echo "$(date -Iseconds) [DEBUG] $*" >&2
        if command -v logger >/dev/null 2>&1; then
            logger -t "$SCRIPT_NAME" -p daemon.debug "$*" 2>/dev/null || true
        fi
    fi
}

# Initialize state directory and temp directory
init_directories() {
    mkdir -p "$STATE_DIR" "$TEMP_DIR"
    chmod 700 "$STATE_DIR" "$TEMP_DIR"
}

# Load rate limiting state
load_state() {
    if [[ -f "$RATE_LIMIT_FILE" ]]; then
        cat "$RATE_LIMIT_FILE" 2>/dev/null || echo '{"last_ship_time": 0, "ship_count": 0}'
    else
        echo '{"last_ship_time": 0, "ship_count": 0}'
    fi
}

# Save rate limiting state
save_state() {
    local state="$1"
    echo "$state" > "$RATE_LIMIT_FILE.tmp"
    mv "$RATE_LIMIT_FILE.tmp" "$RATE_LIMIT_FILE"
    chmod 600 "$RATE_LIMIT_FILE"
}

# Check if shipping is rate limited
is_rate_limited() {
    local current_time
    current_time=$(date +%s)

    local state
    state=$(load_state)

    local last_ship_time
    last_ship_time=$(echo "$state" | jq -r '.last_ship_time // 0')

    local time_diff=$((current_time - last_ship_time))
    local limit_seconds=$((RATE_LIMIT_MINUTES * 60))

    if [[ $time_diff -lt $limit_seconds ]]; then
        log_debug "Rate limited: $time_diff seconds since last ship (limit: $limit_seconds)"
        return 0  # Rate limited
    fi

    return 1  # Not rate limited
}

# Update rate limiting state after shipping
update_rate_state() {
    local current_time
    current_time=$(date +%s)

    local state
    state=$(load_state)

    local ship_count
    ship_count=$(echo "$state" | jq -r '.ship_count // 0')
    ship_count=$((ship_count + 1))

    local new_state
    new_state=$(jq -n \
        --argjson time "$current_time" \
        --argjson count "$ship_count" \
        '{last_ship_time: $time, ship_count: $count}')

    save_state "$new_state"
    log_debug "Updated rate state: shipped $ship_count times, last at $current_time"
}

# Validate webhook configuration
validate_config() {
    if [[ "$ENABLED" != "true" ]]; then
        log_debug "Log shipping disabled"
        return 1
    fi

    if [[ -z "$WEBHOOK_URL" ]]; then
        log_error "CALENDARBOT_WEBHOOK_URL not configured"
        return 1
    fi

    if ! command -v curl >/dev/null 2>&1; then
        log_error "curl not available"
        return 1
    fi

    if ! command -v jq >/dev/null 2>&1; then
        log_error "jq not available"
        return 1
    fi

    return 0
}

# Filter critical events from journald JSON
filter_critical_events() {
    local input="$1"

    # Parse JSON and check for critical events
    local component level event recovery_level
    component=$(echo "$input" | jq -r '.component // ""')
    level=$(echo "$input" | jq -r '.level // ""')
    event=$(echo "$input" | jq -r '.event // ""')
    recovery_level=$(echo "$input" | jq -r '.recovery_level // 0')

    # Critical event criteria:
    # 1. CRITICAL or ERROR level
    # 2. Recovery events with level > 0
    # 3. Specific critical event patterns
    if [[ "$level" == "CRITICAL" ]] ||
       [[ "$level" == "ERROR" && "$recovery_level" -gt 0 ]] ||
       [[ "$event" == *"reboot"* ]] ||
       [[ "$event" == *"service.restart"* ]] ||
       [[ "$event" == *"watchdog.escalate"* ]]; then
        return 0  # Is critical
    fi

    return 1  # Not critical
}

# Prepare webhook payload
prepare_payload() {
    local event_data="$1"
    local hostname
    hostname=$(hostname)

    local timestamp
    timestamp=$(date -Iseconds)

    # Get system context
    local system_info
    system_info=$(cat <<EOF
{
    "hostname": "$hostname",
    "timestamp": "$timestamp",
    "uptime": "$(uptime -p 2>/dev/null || echo 'unknown')",
    "load": "$(uptime | awk -F'load average:' '{print $2}' | xargs || echo 'unknown')",
    "memory": "$(free -h 2>/dev/null | awk 'NR==2{print $3"/"$2}' || echo 'unknown')",
    "disk": "$(df -h / 2>/dev/null | awk 'NR==2{print $5}' || echo 'unknown')"
}
EOF
    )

    # Combine event data with system context
    local payload
    payload=$(echo "$event_data" | jq \
        --argjson system "$system_info" \
        '. + {system_context: $system, shipper_version: "'"$VERSION"'"}')

    echo "$payload"
}

# Ship event to webhook with retry logic
ship_event() {
    local payload="$1"
    local attempt=1

    # Check payload size
    local payload_size
    payload_size=$(echo "$payload" | wc -c)
    if [[ $payload_size -gt $MAX_PAYLOAD_SIZE ]]; then
        log_warn "Payload too large ($payload_size bytes), truncating"
        payload=$(echo "$payload" | jq -c . | head -c $MAX_PAYLOAD_SIZE)
    fi

    log_debug "Shipping payload (${payload_size} bytes) to $WEBHOOK_URL"

    while [[ $attempt -le $MAX_RETRIES ]]; do
        local curl_args=(
            --silent
            --show-error
            --fail
            --max-time "$WEBHOOK_TIMEOUT"
            --header "Content-Type: application/json"
            --header "User-Agent: CalendarBot-LogShipper/$VERSION"
            --data "$payload"
        )

        # Add authentication if token provided
        if [[ -n "$WEBHOOK_TOKEN" ]]; then
            curl_args+=(--header "Authorization: Bearer $WEBHOOK_TOKEN")
        fi

        # SSL verification (enabled by default)
        if [[ "${CALENDARBOT_WEBHOOK_INSECURE:-false}" != "true" ]]; then
            curl_args+=(--cacert /etc/ssl/certs/ca-certificates.crt)
        else
            curl_args+=(--insecure)
            log_warn "SSL verification disabled"
        fi

        curl_args+=("$WEBHOOK_URL")

        log_debug "Attempt $attempt/$MAX_RETRIES"

        if curl "${curl_args[@]}" >/dev/null 2>&1; then
            log_info "Successfully shipped critical event (attempt $attempt)"
            update_rate_state
            return 0
        else
            local exit_code=$?
            log_warn "Ship attempt $attempt failed (exit code: $exit_code)"

            if [[ $attempt -lt $MAX_RETRIES ]]; then
                log_debug "Retrying in $RETRY_DELAY seconds"
                sleep $RETRY_DELAY
            fi
        fi

        ((attempt++))
    done

    log_error "Failed to ship event after $MAX_RETRIES attempts"
    return 1
}

# Process a single log entry
process_log_entry() {
    local log_entry="$1"

    log_debug "Processing log entry: $(echo "$log_entry" | jq -c . 2>/dev/null || echo "invalid JSON")"

    # Validate JSON
    if ! echo "$log_entry" | jq . >/dev/null 2>&1; then
        log_debug "Skipping invalid JSON"
        return 0
    fi

    # Filter for critical events
    if ! filter_critical_events "$log_entry"; then
        log_debug "Event not critical, skipping"
        return 0
    fi

    # Check rate limiting
    if is_rate_limited; then
        log_debug "Rate limited, skipping event"
        return 0
    fi

    log_info "Processing critical event for shipping"

    # Prepare and ship payload
    local payload
    payload=$(prepare_payload "$log_entry")

    if ship_event "$payload"; then
        log_info "Critical event shipped successfully"
    else
        log_error "Failed to ship critical event"
        return 1
    fi
}

# Main processing function for streaming mode
stream_process() {
    log_info "Starting log shipper in stream mode"

    while IFS= read -r line; do
        # Skip empty lines
        [[ -n "$line" ]] || continue

        # Process the log entry
        process_log_entry "$line" || true
    done
}

# Process historical logs from journald
process_historical() {
    local since="${1:-1 hour ago}"
    log_info "Processing historical logs since: $since"

    # Query journald for CalendarBot logs
    journalctl \
        --since="$since" \
        --unit="calendarbot-*" \
        --output=json \
        --no-pager \
        --quiet \
    | while IFS= read -r line; do
        # Extract MESSAGE field which contains our JSON
        local message
        message=$(echo "$line" | jq -r '.MESSAGE // empty' 2>/dev/null)

        # Skip if not JSON message
        if [[ -z "$message" ]] || ! echo "$message" | jq . >/dev/null 2>&1; then
            continue
        fi

        process_log_entry "$message" || true
    done
}

# Show usage information
show_usage() {
    cat <<EOF
CalendarBot Remote Log Shipper v$VERSION

USAGE:
    $0 [OPTIONS] [COMMAND]

COMMANDS:
    stream          Process logs from stdin (default)
    historical      Process historical logs from journald
    test            Test webhook configuration
    status          Show current shipping status

OPTIONS:
    -h, --help      Show this help message
    -v, --version   Show version information
    -d, --debug     Enable debug logging

ENVIRONMENT VARIABLES:
    CALENDARBOT_WEBHOOK_URL              Webhook endpoint URL (required)
    CALENDARBOT_WEBHOOK_TOKEN            Bearer token for authentication
    CALENDARBOT_WEBHOOK_TIMEOUT          Request timeout in seconds (default: 10)
    CALENDARBOT_WEBHOOK_INSECURE         Disable SSL verification (default: false)
    CALENDARBOT_LOG_SHIPPER_ENABLED      Enable log shipping (default: false)
    CALENDARBOT_LOG_SHIPPER_DEBUG        Enable debug mode (default: false)

EXAMPLES:
    # Enable and test configuration
    export CALENDARBOT_LOG_SHIPPER_ENABLED=true
    export CALENDARBOT_WEBHOOK_URL="https://example.com/webhook"
    $0 test

    # Process recent logs
    $0 historical

    # Stream processing (for use with journald)
    journalctl -f -u calendarbot-* --output=json | $0 stream

EOF
}

# Test webhook configuration
test_webhook() {
    log_info "Testing webhook configuration"

    if ! validate_config; then
        log_error "Configuration validation failed"
        return 1
    fi

    # Create test payload
    local test_payload
    test_payload=$(cat <<EOF
{
    "timestamp": "$(date -Iseconds)",
    "component": "log-shipper",
    "level": "INFO",
    "event": "webhook.test",
    "message": "Log shipper webhook test",
    "details": {
        "test": true,
        "version": "$VERSION"
    },
    "system_context": {
        "hostname": "$(hostname)",
        "test_mode": true
    }
}
EOF
    )

    log_info "Sending test payload to webhook"

    if ship_event "$test_payload"; then
        log_info "Webhook test successful"
        return 0
    else
        log_error "Webhook test failed"
        return 1
    fi
}

# Show current shipping status
show_status() {
    log_info "Log shipper status:"

    echo "Configuration:"
    echo "  Enabled: $ENABLED"
    echo "  Webhook URL: ${WEBHOOK_URL:-'not configured'}"
    echo "  Authentication: ${WEBHOOK_TOKEN:+'configured'}"
    echo "  Timeout: ${WEBHOOK_TIMEOUT}s"
    echo "  Debug Mode: $DEBUG_MODE"
    echo

    if [[ -f "$RATE_LIMIT_FILE" ]]; then
        local state
        state=$(load_state)

        local last_ship_time ship_count
        last_ship_time=$(echo "$state" | jq -r '.last_ship_time // 0')
        ship_count=$(echo "$state" | jq -r '.ship_count // 0')

        echo "Rate Limiting:"
        echo "  Total shipped: $ship_count"
        if [[ $last_ship_time -gt 0 ]]; then
            echo "  Last shipped: $(date -d @$last_ship_time 2>/dev/null || echo 'unknown')"

            local current_time time_diff
            current_time=$(date +%s)
            time_diff=$((current_time - last_ship_time))

            if [[ $time_diff -lt $((RATE_LIMIT_MINUTES * 60)) ]]; then
                local remaining=$(( (RATE_LIMIT_MINUTES * 60) - time_diff ))
                echo "  Rate limited for: ${remaining}s"
            else
                echo "  Rate limited: no"
            fi
        else
            echo "  Last shipped: never"
        fi
    else
        echo "Rate Limiting: no state file"
    fi

    echo
    echo "System Status:"
    echo "  Uptime: $(uptime -p 2>/dev/null || echo 'unknown')"
    echo "  Load: $(uptime | awk -F'load average:' '{print $2}' | xargs || echo 'unknown')"
    echo "  Memory: $(free -h 2>/dev/null | awk 'NR==2{print $3"/"$2}' || echo 'unknown')"
    echo "  Disk: $(df -h / 2>/dev/null | awk 'NR==2{print $5" used"}' || echo 'unknown')"
}

# Main function
main() {
    local command="stream"

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -v|--version)
                echo "$SCRIPT_NAME v$VERSION"
                exit 0
                ;;
            -d|--debug)
                DEBUG_MODE="true"
                shift
                ;;
            stream|historical|test|status)
                command="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Initialize directories
    init_directories

    # Validate prerequisites
    if [[ "$command" != "status" ]] && ! validate_config; then
        log_error "Configuration validation failed"
        exit 1
    fi

    log_debug "Starting $SCRIPT_NAME v$VERSION in $command mode"

    # Execute command
    case $command in
        stream)
            stream_process
            ;;
        historical)
            # Default to last hour if no argument provided
            process_historical "${2:-1 hour ago}"
            ;;
        test)
            if test_webhook; then
                log_info "Webhook test passed"
                exit 0
            else
                log_error "Webhook test failed"
                exit 1
            fi
            ;;
        status)
            show_status
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Cleanup function for signal handling
cleanup() {
    log_info "Received shutdown signal, cleaning up"
    rm -rf "$TEMP_DIR"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Run main function with all arguments
main "$@"