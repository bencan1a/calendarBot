#!/bin/bash

# CalendarBot Critical Event Filter
# Pi Zero 2 optimized script for monitoring journald for critical CalendarBot events
# Filters, deduplicates, and forwards only actionable events for remote shipping

set -euo pipefail

# Script metadata
readonly SCRIPT_NAME="calendarbot-critical-event-filter"
readonly VERSION="1.0.0"
readonly STATE_DIR="/var/local/calendarbot-watchdog"
readonly FILTER_STATE_FILE="$STATE_DIR/critical-filter-state.json"
readonly TEMP_DIR="/tmp/calendarbot-critical-filter"
readonly DEDUP_WINDOW_MINUTES=60
readonly MAX_EVENTS_PER_HOUR=10

# Default configuration
DEBUG_MODE="${CALENDARBOT_FILTER_DEBUG:-false}"
DRY_RUN="${CALENDARBOT_FILTER_DRY_RUN:-false}"
FORWARD_ENABLED="${CALENDARBOT_FILTER_FORWARD:-true}"
LOG_SHIPPER_PATH="${CALENDARBOT_LOG_SHIPPER_PATH:-/opt/calendarbot/kiosk/scripts/log-shipper.sh}"

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

# Initialize directories and state
init_state() {
    mkdir -p "$STATE_DIR" "$TEMP_DIR"
    chmod 700 "$STATE_DIR" "$TEMP_DIR"

    # Initialize state file if it doesn't exist
    if [[ ! -f "$FILTER_STATE_FILE" ]]; then
        echo '{
            "event_hashes": {},
            "hourly_counts": {},
            "last_cleanup": 0,
            "total_filtered": 0,
            "total_forwarded": 0
        }' > "$FILTER_STATE_FILE"
        chmod 600 "$FILTER_STATE_FILE"
    fi
}

# Load filter state
load_state() {
    if [[ -f "$FILTER_STATE_FILE" ]]; then
        cat "$FILTER_STATE_FILE" 2>/dev/null || echo '{
            "event_hashes": {},
            "hourly_counts": {},
            "last_cleanup": 0,
            "total_filtered": 0,
            "total_forwarded": 0
        }'
    else
        echo '{
            "event_hashes": {},
            "hourly_counts": {},
            "last_cleanup": 0,
            "total_filtered": 0,
            "total_forwarded": 0
        }'
    fi
}

# Save filter state
save_state() {
    local state="$1"
    echo "$state" > "$FILTER_STATE_FILE.tmp"
    mv "$FILTER_STATE_FILE.tmp" "$FILTER_STATE_FILE"
    chmod 600 "$FILTER_STATE_FILE"
}

# Generate event hash for deduplication
generate_event_hash() {
    local event="$1"

    # Extract key fields for hashing
    local component level event_type message
    component=$(echo "$event" | jq -r '.component // ""')
    level=$(echo "$event" | jq -r '.level // ""')
    event_type=$(echo "$event" | jq -r '.event // ""')
    message=$(echo "$event" | jq -r '.message // ""')

    # Create normalized hash input (remove timestamps and variable data)
    local hash_input="${component}:${level}:${event_type}:${message}"

    # Generate hash using available tools
    if command -v sha256sum >/dev/null 2>&1; then
        echo "$hash_input" | sha256sum | cut -d' ' -f1
    elif command -v md5sum >/dev/null 2>&1; then
        echo "$hash_input" | md5sum | cut -d' ' -f1
    else
        # Fallback: use simple checksum
        echo "$hash_input" | cksum | cut -d' ' -f1
    fi
}

# Check if event is critical based on filtering rules
is_critical_event() {
    local event="$1"

    # Parse event fields
    local level component event_type recovery_level
    level=$(echo "$event" | jq -r '.level // ""')
    component=$(echo "$event" | jq -r '.component // ""')
    event_type=$(echo "$event" | jq -r '.event // ""')
    recovery_level=$(echo "$event" | jq -r '.recovery_level // 0')

    # Critical event criteria (stricter than log-shipper)
    if [[ "$level" == "CRITICAL" ]]; then
        log_debug "Critical level event detected: $event_type"
        return 0
    fi

    if [[ "$level" == "ERROR" && "$recovery_level" -gt 1 ]]; then
        log_debug "Error with recovery level $recovery_level: $event_type"
        return 0
    fi

    # Specific critical patterns
    case "$event_type" in
        *"reboot"*|*"service.restart"*|*"watchdog.escalate"*|*"health.critical"*)
            log_debug "Critical pattern detected: $event_type"
            return 0
            ;;
        *"browser.restart"*)
            # Only critical if frequent
            if [[ "$recovery_level" -gt 0 ]]; then
                log_debug "Browser restart with recovery: $event_type"
                return 0
            fi
            ;;
    esac

    return 1  # Not critical
}

# Check rate limiting
is_rate_limited() {
    local current_hour
    current_hour=$(date +%Y%m%d%H)

    local state
    state=$(load_state)

    local hour_count
    hour_count=$(echo "$state" | jq -r ".hourly_counts[\"$current_hour\"] // 0")

    if [[ $hour_count -ge $MAX_EVENTS_PER_HOUR ]]; then
        log_debug "Rate limited: $hour_count events in hour $current_hour"
        return 0  # Rate limited
    fi

    return 1  # Not rate limited
}

# Check for duplicate events
is_duplicate() {
    local event="$1"
    local event_hash
    event_hash=$(generate_event_hash "$event")

    local state
    state=$(load_state)

    local current_time
    current_time=$(date +%s)

    local last_seen
    last_seen=$(echo "$state" | jq -r ".event_hashes[\"$event_hash\"] // 0")

    local time_diff=$((current_time - last_seen))
    local dedup_seconds=$((DEDUP_WINDOW_MINUTES * 60))

    if [[ $last_seen -gt 0 && $time_diff -lt $dedup_seconds ]]; then
        log_debug "Duplicate event detected (hash: $event_hash, last seen: ${time_diff}s ago)"
        return 0  # Is duplicate
    fi

    return 1  # Not duplicate
}

# Update state after processing event
update_state() {
    local event="$1"
    local forwarded="$2"

    local event_hash
    event_hash=$(generate_event_hash "$event")

    local current_time current_hour
    current_time=$(date +%s)
    current_hour=$(date +%Y%m%d%H)

    local state
    state=$(load_state)

    # Update event hash timestamp
    state=$(echo "$state" | jq \
        --arg hash "$event_hash" \
        --argjson time "$current_time" \
        '.event_hashes[$hash] = $time')

    # Update hourly count
    state=$(echo "$state" | jq \
        --arg hour "$current_hour" \
        '.hourly_counts[$hour] = (.hourly_counts[$hour] // 0) + 1')

    # Update totals
    state=$(echo "$state" | jq '.total_filtered += 1')

    if [[ "$forwarded" == "true" ]]; then
        state=$(echo "$state" | jq '.total_forwarded += 1')
    fi

    save_state "$state"
}

# Cleanup old state data
cleanup_state() {
    local state
    state=$(load_state)

    local current_time
    current_time=$(date +%s)

    local last_cleanup
    last_cleanup=$(echo "$state" | jq -r '.last_cleanup // 0')

    # Cleanup every hour
    if [[ $((current_time - last_cleanup)) -lt 3600 ]]; then
        return 0
    fi

    log_debug "Cleaning up old state data"

    # Remove event hashes older than dedup window
    local cutoff_time=$((current_time - DEDUP_WINDOW_MINUTES * 60))
    state=$(echo "$state" | jq \
        --argjson cutoff "$cutoff_time" \
        '.event_hashes = (.event_hashes | to_entries | map(select(.value > $cutoff)) | from_entries)')

    # Remove hourly counts older than 24 hours
    local current_hour_num
    current_hour_num=$(date +%Y%m%d%H)
    local cutoff_hour_num=$((current_hour_num - 100))  # 24 hours ago (rough)

    state=$(echo "$state" | jq \
        --arg cutoff "$cutoff_hour_num" \
        '.hourly_counts = (.hourly_counts | to_entries | map(select(.key > $cutoff)) | from_entries)')

    # Update cleanup timestamp
    state=$(echo "$state" | jq \
        --argjson time "$current_time" \
        '.last_cleanup = $time')

    save_state "$state"
    log_debug "State cleanup completed"
}

# Format event for forwarding
format_for_forwarding() {
    local event="$1"

    # Add filter metadata
    local formatted
    formatted=$(echo "$event" | jq \
        --arg filter_version "$VERSION" \
        --arg filter_time "$(date -Iseconds)" \
        '. + {
            filter_metadata: {
                version: $filter_version,
                filtered_at: $filter_time,
                action: "forwarded_critical"
            }
        }')

    echo "$formatted"
}

# Forward event using log shipper
forward_event() {
    local event="$1"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would forward event: $(echo "$event" | jq -c .)"
        return 0
    fi

    if [[ "$FORWARD_ENABLED" != "true" ]]; then
        log_debug "Forwarding disabled, skipping"
        return 0
    fi

    # Check if log shipper exists
    if [[ ! -x "$LOG_SHIPPER_PATH" ]]; then
        log_warn "Log shipper not found at $LOG_SHIPPER_PATH"
        return 1
    fi

    local formatted_event
    formatted_event=$(format_for_forwarding "$event")

    log_debug "Forwarding event via log shipper"

    # Forward to log shipper via stdin
    if echo "$formatted_event" | "$LOG_SHIPPER_PATH" stream; then
        log_info "Event forwarded successfully"
        return 0
    else
        log_error "Failed to forward event"
        return 1
    fi
}

# Process a single event
process_event() {
    local event="$1"

    log_debug "Processing event: $(echo "$event" | jq -c . 2>/dev/null || echo "invalid JSON")"

    # Validate JSON
    if ! echo "$event" | jq . >/dev/null 2>&1; then
        log_debug "Skipping invalid JSON"
        return 0
    fi

    # Check if event is critical
    if ! is_critical_event "$event"; then
        log_debug "Event not critical, skipping"
        return 0
    fi

    # Check for duplicates
    if is_duplicate "$event"; then
        log_debug "Duplicate event, skipping"
        update_state "$event" "false"
        return 0
    fi

    # Check rate limiting
    if is_rate_limited; then
        log_warn "Rate limited, skipping critical event"
        update_state "$event" "false"
        return 0
    fi

    log_info "Processing critical event for forwarding"

    # Forward the event
    local forwarded="false"
    if forward_event "$event"; then
        forwarded="true"
        log_info "Critical event forwarded successfully"
    else
        log_error "Failed to forward critical event"
    fi

    # Update state
    update_state "$event" "$forwarded"

    # Periodic cleanup
    cleanup_state
}

# Stream processing mode
stream_mode() {
    log_info "Starting critical event filter in stream mode"

    while IFS= read -r line; do
        # Skip empty lines
        [[ -n "$line" ]] || continue

        # Process the event
        process_event "$line" || true
    done
}

# Monitor journald directly
monitor_mode() {
    log_info "Starting critical event filter in monitor mode"

    # Follow journald for CalendarBot events
    journalctl \
        --follow \
        --unit="calendarbot*" \
        --output=json \
        --no-pager \
        --since="now" \
    | while IFS= read -r line; do
        # Extract MESSAGE field
        local message
        message=$(echo "$line" | jq -r '.MESSAGE // empty' 2>/dev/null)

        # Skip if not JSON message
        if [[ -z "$message" ]] || ! echo "$message" | jq . >/dev/null 2>&1; then
            continue
        fi

        # Process the extracted event
        process_event "$message" || true
    done
}

# Show filter statistics
show_stats() {
    local state
    state=$(load_state)

    echo "Critical Event Filter Statistics:"
    echo "  Total events filtered: $(echo "$state" | jq -r '.total_filtered')"
    echo "  Total events forwarded: $(echo "$state" | jq -r '.total_forwarded')"
    echo "  Current dedup cache size: $(echo "$state" | jq -r '.event_hashes | length')"
    echo "  Hourly counts:"

    echo "$state" | jq -r '.hourly_counts | to_entries[] | "    " + .key + ": " + (.value | tostring)' | tail -24

    echo
    echo "Configuration:"
    echo "  Debug mode: $DEBUG_MODE"
    echo "  Dry run: $DRY_RUN"
    echo "  Forward enabled: $FORWARD_ENABLED"
    echo "  Log shipper path: $LOG_SHIPPER_PATH"
    echo "  Dedup window: ${DEDUP_WINDOW_MINUTES} minutes"
    echo "  Max events per hour: $MAX_EVENTS_PER_HOUR"
}

# Test the filter with a sample event
test_filter() {
    log_info "Testing critical event filter"

    # Create test event
    local test_event
    test_event=$(cat <<EOF
{
    "timestamp": "$(date -Iseconds)",
    "component": "test",
    "level": "CRITICAL",
    "event": "filter.test",
    "message": "Critical event filter test",
    "details": {
        "test": true,
        "version": "$VERSION"
    }
}
EOF
    )

    echo "Test event:"
    echo "$test_event" | jq .
    echo

    echo "Processing test event..."
    process_event "$test_event"

    echo
    echo "Test completed. Check logs for processing details."
}

# Show usage information
show_usage() {
    cat <<EOF
CalendarBot Critical Event Filter v$VERSION

USAGE:
    $0 [OPTIONS] [COMMAND]

COMMANDS:
    stream          Process events from stdin (default)
    monitor         Monitor journald directly for events
    stats           Show filter statistics
    test            Run filter test with sample event

OPTIONS:
    -h, --help      Show this help message
    -v, --version   Show version information
    -d, --debug     Enable debug logging
    -n, --dry-run   Dry run mode (don't forward events)
    --disable-forward   Disable event forwarding

ENVIRONMENT VARIABLES:
    CALENDARBOT_FILTER_DEBUG         Enable debug mode (default: false)
    CALENDARBOT_FILTER_DRY_RUN       Enable dry run mode (default: false)
    CALENDARBOT_FILTER_FORWARD       Enable forwarding (default: true)
    CALENDARBOT_LOG_SHIPPER_PATH     Path to log shipper script

EXAMPLES:
    # Monitor journald directly
    $0 monitor

    # Process events from log aggregator
    calendarbot-log-aggregator daily \$(date +%Y-%m-%d) | $0 stream

    # Test with debug output
    $0 --debug test

    # Dry run mode
    $0 --dry-run monitor

EOF
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
            -n|--dry-run)
                DRY_RUN="true"
                shift
                ;;
            --disable-forward)
                FORWARD_ENABLED="false"
                shift
                ;;
            stream|monitor|stats|test)
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

    # Validate prerequisites
    if ! command -v jq >/dev/null 2>&1; then
        log_error "jq is required but not installed"
        exit 1
    fi

    # Initialize
    init_state

    log_debug "Starting $SCRIPT_NAME v$VERSION with command: $command"

    # Execute command
    case $command in
        stream)
            stream_mode
            ;;
        monitor)
            monitor_mode
            ;;
        stats)
            show_stats
            ;;
        test)
            test_filter
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