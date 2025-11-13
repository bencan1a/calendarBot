#!/bin/bash

# CalendarBot Log Aggregation and Reporting Script
# Pi Zero 2 optimized script for collecting and summarizing monitoring events
# Generates reports from journald and exports metrics for monitoring systems

set -euo pipefail

# Script metadata
readonly SCRIPT_NAME="calendarbot-log-aggregator"
readonly VERSION="1.0.0"
readonly DATA_DIR="/var/local/calendarbot-watchdog"
readonly REPORTS_DIR="$DATA_DIR/reports"
readonly TEMP_DIR="/tmp/calendarbot-log-aggregator"
readonly MAX_REPORT_SIZE=10485760  # 10MB max report size

# Default configuration
RETENTION_DAYS="${CALENDARBOT_AGGREGATOR_RETENTION_DAYS:-30}"
DEBUG_MODE="${CALENDARBOT_AGGREGATOR_DEBUG:-false}"
OUTPUT_FORMAT="${CALENDARBOT_AGGREGATOR_FORMAT:-json}"
EXPORT_METRICS="${CALENDARBOT_AGGREGATOR_EXPORT_METRICS:-false}"

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

# Initialize directories
init_directories() {
    mkdir -p "$DATA_DIR" "$REPORTS_DIR" "$TEMP_DIR"
    chmod 700 "$DATA_DIR" "$TEMP_DIR"
    chmod 755 "$REPORTS_DIR"
}

# Validate prerequisites
validate_prerequisites() {
    local missing_tools=()

    if ! command -v jq >/dev/null 2>&1; then
        missing_tools+=("jq")
    fi

    if ! command -v journalctl >/dev/null 2>&1; then
        missing_tools+=("journalctl")
    fi

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        return 1
    fi

    return 0
}

# Query journald for CalendarBot events
query_calendarbot_events() {
    local since="$1"
    local until="${2:-now}"

    log_debug "Querying events from $since to $until"

    # Query journald for CalendarBot-related logs
    journalctl \
        --since="$since" \
        --until="$until" \
        --unit="calendarbot*" \
        --output=json \
        --no-pager \
        --quiet \
    | while IFS= read -r line; do
        # Extract MESSAGE field and validate JSON
        local message
        message=$(echo "$line" | jq -r '.MESSAGE // empty' 2>/dev/null)

        if [[ -n "$message" ]] && echo "$message" | jq . >/dev/null 2>&1; then
            echo "$message"
        fi
    done
}

# Aggregate events by component and level
aggregate_events() {
    local temp_file="$1"

    log_debug "Aggregating events from $temp_file"

    # Create aggregation summary
    local aggregation
    aggregation=$(jq -s '
        {
            total_events: length,
            by_component: group_by(.component) | map({
                component: .[0].component,
                count: length,
                by_level: group_by(.level) | map({
                    level: .[0].level,
                    count: length
                })
            }),
            by_level: group_by(.level) | map({
                level: .[0].level,
                count: length
            }),
            by_event_type: group_by(.event) | map({
                event: .[0].event,
                count: length,
                latest: max_by(.timestamp).timestamp
            }),
            recovery_actions: map(select(.recovery_level and (.recovery_level | tonumber) > 0)) | {
                total: length,
                by_level: group_by(.recovery_level) | map({
                    level: .[0].recovery_level,
                    count: length,
                    events: map(.event)
                })
            }
        }
    ' "$temp_file")

    echo "$aggregation"
}

# Generate event patterns analysis
analyze_patterns() {
    local temp_file="$1"

    log_debug "Analyzing patterns from $temp_file"

    # Pattern analysis
    local patterns
    patterns=$(jq -s '
        {
            error_patterns: map(select(.level == "ERROR" or .level == "CRITICAL")) |
                group_by(.event) |
                map({
                    pattern: .[0].event,
                    occurrences: length,
                    first_seen: min_by(.timestamp).timestamp,
                    last_seen: max_by(.timestamp).timestamp,
                    frequency_per_hour: (length / (
                        (max_by(.timestamp).timestamp | fromdateiso8601) -
                        (min_by(.timestamp).timestamp | fromdateiso8601)
                    ) * 3600)
                }),
            recovery_effectiveness: map(select(.action_taken)) |
                group_by(.action_taken) |
                map({
                    action: .[0].action_taken,
                    usage_count: length,
                    success_indicators: map(select(.level == "INFO" and (.event | contains("complete"))))
                }),
            system_health_trends: map(select(.system_state)) |
                [{
                    avg_cpu_load: (map(.system_state.cpu_load | select(. != null)) | add / length),
                    avg_memory_free: (map(.system_state.memory_free_mb | select(. != null)) | add / length),
                    min_disk_space: (map(.system_state.disk_free_mb | select(. != null)) | min)
                }] | .[0]
        }
    ' "$temp_file")

    echo "$patterns"
}

# Generate metrics for external monitoring
generate_metrics() {
    local aggregation="$1"
    local output_file="$2"

    log_debug "Generating metrics to $output_file"

    # Generate Prometheus-style metrics
    cat > "$output_file" <<EOF
# HELP calendarbot_events_total Total number of CalendarBot events
# TYPE calendarbot_events_total counter
calendarbot_events_total $(echo "$aggregation" | jq -r '.total_events')

# HELP calendarbot_errors_total Total number of error events
# TYPE calendarbot_errors_total counter
calendarbot_errors_total $(echo "$aggregation" | jq -r '
    .by_level[] | select(.level == "ERROR" or .level == "CRITICAL") | .count' |
    awk '{sum += $1} END {print sum+0}')

# HELP calendarbot_recovery_actions_total Total number of recovery actions
# TYPE calendarbot_recovery_actions_total counter
calendarbot_recovery_actions_total $(echo "$aggregation" | jq -r '.recovery_actions.total')

# HELP calendarbot_component_events Events by component
# TYPE calendarbot_component_events counter
EOF

    # Add component-specific metrics
    echo "$aggregation" | jq -r '
        .by_component[] |
        "calendarbot_component_events{component=\"" + .component + "\"} " + (.count | tostring)
    ' >> "$output_file"

    # Add level-specific metrics
    echo "" >> "$output_file"
    echo "# HELP calendarbot_level_events Events by log level" >> "$output_file"
    echo "# TYPE calendarbot_level_events counter" >> "$output_file"

    echo "$aggregation" | jq -r '
        .by_level[] |
        "calendarbot_level_events{level=\"" + .level + "\"} " + (.count | tostring)
    ' >> "$output_file"
}

# Create daily report
generate_daily_report() {
    local date_str="$1"
    local since="${date_str} 00:00:00"
    local until="${date_str} 23:59:59"

    log_info "Generating daily report for $date_str"

    local temp_events="$TEMP_DIR/events_${date_str}.json"
    local report_file="$REPORTS_DIR/daily_${date_str}.json"

    # Collect events for the day
    query_calendarbot_events "$since" "$until" > "$temp_events"

    local event_count
    event_count=$(wc -l < "$temp_events")

    if [[ $event_count -eq 0 ]]; then
        log_info "No events found for $date_str"
        echo '{"date": "'"$date_str"'", "events": [], "summary": {"total_events": 0}}' > "$report_file"
        rm -f "$temp_events"
        return 0
    fi

    log_debug "Found $event_count events for $date_str"

    # Generate aggregation and patterns
    local aggregation patterns
    aggregation=$(aggregate_events "$temp_events")
    patterns=$(analyze_patterns "$temp_events")

    # Create complete report
    local report
    report=$(jq -n \
        --arg date "$date_str" \
        --argjson aggregation "$aggregation" \
        --argjson patterns "$patterns" \
        '{
            date: $date,
            generated_at: now | todateiso8601,
            summary: $aggregation,
            patterns: $patterns,
            report_version: "'"$VERSION"'"
        }')

    # Write report
    echo "$report" > "$report_file"

    # Generate metrics if enabled
    if [[ "$EXPORT_METRICS" == "true" ]]; then
        local metrics_file="$REPORTS_DIR/metrics_${date_str}.prom"
        generate_metrics "$aggregation" "$metrics_file"
        log_debug "Metrics exported to $metrics_file"
    fi

    # Cleanup temp file
    rm -f "$temp_events"

    log_info "Daily report generated: $report_file"
}

# Create weekly summary
generate_weekly_report() {
    local week_start="$1"  # YYYY-MM-DD format

    log_info "Generating weekly report starting $week_start"

    local week_end
    week_end=$(date -d "$week_start + 6 days" +%Y-%m-%d)

    local report_file="$REPORTS_DIR/weekly_${week_start}_to_${week_end}.json"
    local temp_events="$TEMP_DIR/events_week_${week_start}.json"

    # Collect all events for the week
    query_calendarbot_events "${week_start} 00:00:00" "${week_end} 23:59:59" > "$temp_events"

    local event_count
    event_count=$(wc -l < "$temp_events")

    if [[ $event_count -eq 0 ]]; then
        log_info "No events found for week $week_start to $week_end"
        echo '{
            "week_start": "'"$week_start"'",
            "week_end": "'"$week_end"'",
            "events": [],
            "summary": {"total_events": 0}
        }' > "$report_file"
        rm -f "$temp_events"
        return 0
    fi

    log_debug "Found $event_count events for week $week_start to $week_end"

    # Generate weekly aggregation
    local aggregation patterns
    aggregation=$(aggregate_events "$temp_events")
    patterns=$(analyze_patterns "$temp_events")

    # Add daily breakdown
    local daily_breakdown
    daily_breakdown=$(jq -s '
        group_by(.timestamp | split("T")[0]) |
        map({
            date: .[0].timestamp | split("T")[0],
            count: length,
            error_count: map(select(.level == "ERROR" or .level == "CRITICAL")) | length,
            recovery_count: map(select(.recovery_level and (.recovery_level | tonumber) > 0)) | length
        })
    ' "$temp_events")

    # Create weekly report
    local report
    report=$(jq -n \
        --arg week_start "$week_start" \
        --arg week_end "$week_end" \
        --argjson aggregation "$aggregation" \
        --argjson patterns "$patterns" \
        --argjson daily "$daily_breakdown" \
        '{
            week_start: $week_start,
            week_end: $week_end,
            generated_at: now | todateiso8601,
            summary: $aggregation,
            patterns: $patterns,
            daily_breakdown: $daily,
            report_version: "'"$VERSION"'"
        }')

    echo "$report" > "$report_file"
    rm -f "$temp_events"

    log_info "Weekly report generated: $report_file"
}

# Clean up old reports
cleanup_old_reports() {
    log_info "Cleaning up reports older than $RETENTION_DAYS days"

    # Clean daily reports
    find "$REPORTS_DIR" -name "daily_*.json" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

    # Clean weekly reports
    find "$REPORTS_DIR" -name "weekly_*.json" -mtime +$((RETENTION_DAYS * 2)) -delete 2>/dev/null || true

    # Clean metrics files
    find "$REPORTS_DIR" -name "metrics_*.prom" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

    log_debug "Cleanup completed"
}

# Export monitoring status for external systems
export_status() {
    local output_file="$1"

    log_info "Exporting monitoring status to $output_file"

    # Get latest daily report
    local latest_report
    latest_report=$(find "$REPORTS_DIR" -name "daily_*.json" -type f | sort | tail -1)

    if [[ -z "$latest_report" ]]; then
        log_warn "No daily reports found for status export"
        echo '{"status": "no_data", "message": "No daily reports available"}' > "$output_file"
        return 0
    fi

    local report_data
    report_data=$(cat "$latest_report")

    # Create status summary
    local status
    status=$(echo "$report_data" | jq '{
        last_report_date: .date,
        total_events: .summary.total_events,
        error_count: (.summary.by_level[] | select(.level == "ERROR" or .level == "CRITICAL") | .count) // 0,
        recovery_actions: .summary.recovery_actions.total,
        critical_patterns: .patterns.error_patterns | length,
        system_health: .patterns.system_health_trends,
        status: (if (.summary.total_events > 0 and
                     ((.summary.by_level[] | select(.level == "CRITICAL") | .count) // 0) == 0)
                 then "healthy"
                 elif ((.summary.by_level[] | select(.level == "CRITICAL") | .count) // 0) > 0
                 then "critical"
                 else "degraded" end),
        generated_at: now | todateiso8601
    }')

    echo "$status" > "$output_file"
    log_info "Status exported successfully"
}

# Show usage information
show_usage() {
    cat <<EOF
CalendarBot Log Aggregator v$VERSION

USAGE:
    $0 [OPTIONS] COMMAND [ARGS]

COMMANDS:
    daily DATE              Generate daily report for DATE (YYYY-MM-DD)
    weekly DATE             Generate weekly report starting from DATE
    status OUTPUT_FILE      Export monitoring status to file
    cleanup                 Clean up old reports
    auto                    Run automatic daily/weekly reports

OPTIONS:
    -h, --help              Show this help message
    -v, --version           Show version information
    -d, --debug             Enable debug logging
    -f, --format FORMAT     Output format: json, text (default: json)
    -m, --metrics           Export metrics in Prometheus format

ENVIRONMENT VARIABLES:
    CALENDARBOT_AGGREGATOR_RETENTION_DAYS    Report retention in days (default: 30)
    CALENDARBOT_AGGREGATOR_DEBUG             Enable debug mode (default: false)
    CALENDARBOT_AGGREGATOR_FORMAT            Output format (default: json)
    CALENDARBOT_AGGREGATOR_EXPORT_METRICS    Export metrics (default: false)

EXAMPLES:
    # Generate daily report for today
    $0 daily \$(date +%Y-%m-%d)

    # Generate weekly report for current week
    $0 weekly \$(date -d 'last monday' +%Y-%m-%d)

    # Export current status
    $0 status /tmp/calendarbot-status.json

    # Automatic mode with metrics export
    export CALENDARBOT_AGGREGATOR_EXPORT_METRICS=true
    $0 auto

EOF
}

# Automatic report generation
run_automatic() {
    log_info "Running automatic report generation"

    # Generate daily report for yesterday
    local yesterday
    yesterday=$(date -d 'yesterday' +%Y-%m-%d)
    generate_daily_report "$yesterday"

    # Generate weekly report if it's Monday
    if [[ $(date +%u) -eq 1 ]]; then
        local last_monday
        last_monday=$(date -d 'last monday' +%Y-%m-%d)
        generate_weekly_report "$last_monday"
    fi

    # Clean up old reports
    cleanup_old_reports

    # Export current status
    export_status "$REPORTS_DIR/current_status.json"

    log_info "Automatic report generation completed"
}

# Main function
main() {
    local command=""

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
            -f|--format)
                OUTPUT_FORMAT="$2"
                shift 2
                ;;
            -m|--metrics)
                EXPORT_METRICS="true"
                shift
                ;;
            daily|weekly|status|cleanup|auto)
                command="$1"
                shift
                break
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    if [[ -z "$command" ]]; then
        log_error "No command specified"
        show_usage
        exit 1
    fi

    # Initialize
    init_directories

    if ! validate_prerequisites; then
        exit 1
    fi

    log_debug "Starting $SCRIPT_NAME v$VERSION with command: $command"

    # Execute command
    case $command in
        daily)
            if [[ $# -lt 1 ]]; then
                log_error "Daily command requires date argument (YYYY-MM-DD)"
                exit 1
            fi
            generate_daily_report "$1"
            ;;
        weekly)
            if [[ $# -lt 1 ]]; then
                log_error "Weekly command requires start date argument (YYYY-MM-DD)"
                exit 1
            fi
            generate_weekly_report "$1"
            ;;
        status)
            if [[ $# -lt 1 ]]; then
                log_error "Status command requires output file argument"
                exit 1
            fi
            export_status "$1"
            ;;
        cleanup)
            cleanup_old_reports
            ;;
        auto)
            run_automatic
            ;;
        *)
            log_error "Unknown command: $command"
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