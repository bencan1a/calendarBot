#!/bin/bash

# CalendarBot Monitoring Status Dashboard Script
# Pi Zero 2 optimized script for generating monitoring status JSON for external dashboards
# Aggregates health, recovery actions, system metrics with trend data and historical summaries

set -euo pipefail

# Script metadata
readonly SCRIPT_NAME="calendarbot-monitoring-status"
readonly VERSION="1.0.0"
readonly DATA_DIR="/var/local/calendarbot-watchdog"
readonly REPORTS_DIR="$DATA_DIR/reports"
readonly CACHE_DIR="$DATA_DIR/cache"
readonly TEMP_DIR="/tmp/calendarbot-monitoring-status"
readonly STATUS_CACHE_TTL=300  # 5 minutes cache TTL

# Default configuration
DEBUG_MODE="${CALENDARBOT_STATUS_DEBUG:-false}"
OUTPUT_FORMAT="${CALENDARBOT_STATUS_FORMAT:-json}"
CACHE_ENABLED="${CALENDARBOT_STATUS_CACHE:-true}"
INCLUDE_TRENDS="${CALENDARBOT_STATUS_TRENDS:-true}"

# Logging functions
log_info() {
    echo "$(date -Iseconds) [INFO] $*" >&2
    logger -t "$SCRIPT_NAME" -p daemon.info "$*"
}

log_warn() {
    echo "$(date -Iseconds) [WARN] $*" >&2
    logger -t "$SCRIPT_NAME" -p daemon.warning "$*"
}

log_error() {
    echo "$(date -Iseconds) [ERROR] $*" >&2
    logger -t "$SCRIPT_NAME" -p daemon.error "$*"
}

log_debug() {
    if [[ "$DEBUG_MODE" == "true" ]]; then
        echo "$(date -Iseconds) [DEBUG] $*" >&2
        logger -t "$SCRIPT_NAME" -p daemon.debug "$*"
    fi
}

# Initialize directories
init_directories() {
    mkdir -p "$DATA_DIR" "$REPORTS_DIR" "$CACHE_DIR" "$TEMP_DIR"
    chmod 700 "$DATA_DIR" "$TEMP_DIR"
    chmod 755 "$REPORTS_DIR" "$CACHE_DIR"
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
    
    if ! command -v curl >/dev/null 2>&1; then
        missing_tools+=("curl")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        return 1
    fi
    
    return 0
}

# Get current system metrics
get_system_metrics() {
    log_debug "Collecting system metrics"
    
    local metrics='{}'
    
    # CPU metrics
    if [[ -f /proc/loadavg ]]; then
        local load_avg
        load_avg=$(cat /proc/loadavg | cut -d' ' -f1-3)
        metrics=$(echo "$metrics" | jq --arg load "$load_avg" '.cpu.load_average = $load')
        
        local load_1m
        load_1m=$(echo "$load_avg" | cut -d' ' -f1)
        metrics=$(echo "$metrics" | jq --argjson load "$load_1m" '.cpu.load_1m = $load')
    fi
    
    # Memory metrics
    if [[ -f /proc/meminfo ]]; then
        local mem_total mem_available mem_free
        mem_total=$(awk '/MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo "0")
        mem_available=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo 2>/dev/null || echo "0")
        mem_free=$(awk '/MemFree:/ {print $2}' /proc/meminfo 2>/dev/null || echo "0")
        
        local mem_used=$((mem_total - mem_available))
        local mem_usage_pct
        if [[ $mem_total -gt 0 ]]; then
            mem_usage_pct=$((mem_used * 100 / mem_total))
        else
            mem_usage_pct=0
        fi
        
        metrics=$(echo "$metrics" | jq \
            --argjson total "$mem_total" \
            --argjson available "$mem_available" \
            --argjson free "$mem_free" \
            --argjson used "$mem_used" \
            --argjson usage_pct "$mem_usage_pct" \
            '.memory = {
                total_kb: $total,
                available_kb: $available,
                free_kb: $free,
                used_kb: $used,
                usage_percent: $usage_pct
            }')
    fi
    
    # Disk metrics
    if command -v df >/dev/null 2>&1; then
        local disk_info
        disk_info=$(df / 2>/dev/null | tail -1)
        if [[ -n "$disk_info" ]]; then
            local disk_total disk_used disk_available disk_usage_pct
            disk_total=$(echo "$disk_info" | awk '{print $2}')
            disk_used=$(echo "$disk_info" | awk '{print $3}')
            disk_available=$(echo "$disk_info" | awk '{print $4}')
            disk_usage_pct=$(echo "$disk_info" | awk '{print $5}' | sed 's/%//')
            
            metrics=$(echo "$metrics" | jq \
                --argjson total "$disk_total" \
                --argjson used "$disk_used" \
                --argjson available "$disk_available" \
                --argjson usage_pct "$disk_usage_pct" \
                '.disk = {
                    total_kb: $total,
                    used_kb: $used,
                    available_kb: $available,
                    usage_percent: $usage_pct
                }')
        fi
    fi
    
    # Uptime
    if [[ -f /proc/uptime ]]; then
        local uptime_seconds
        uptime_seconds=$(cut -d' ' -f1 /proc/uptime | cut -d'.' -f1)
        metrics=$(echo "$metrics" | jq --argjson uptime "$uptime_seconds" '.uptime_seconds = $uptime')
    fi
    
    # Temperature (if available)
    if [[ -f /sys/class/thermal/thermal_zone0/temp ]]; then
        local temp_raw temp_celsius
        temp_raw=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo "0")
        temp_celsius=$((temp_raw / 1000))
        metrics=$(echo "$metrics" | jq --argjson temp "$temp_celsius" '.temperature_celsius = $temp')
    fi
    
    echo "$metrics"
}

# Get CalendarBot service status
get_service_status() {
    log_debug "Checking service status"
    
    local status='{}'
    
    # Check server health endpoint
    local health_response health_status
    if curl -s --max-time 5 http://127.0.0.1:8080/api/health >/dev/null 2>&1; then
        health_response=$(curl -s --max-time 5 http://127.0.0.1:8080/api/health 2>/dev/null || echo '{}')
        health_status=$(echo "$health_response" | jq -r '.status // "unknown"')
        
        status=$(echo "$status" | jq \
            --arg status "$health_status" \
            --argjson health "$health_response" \
            '.server = {
                status: $status,
                reachable: true,
                health_data: $health
            }')
    else
        status=$(echo "$status" | jq '.server = {
            status: "unreachable",
            reachable: false,
            health_data: null
        }')
    fi
    
    # Check systemd services
    local services=("calendarbot-kiosk@bencan" "calendarbot-kiosk-watchdog@bencan")
    local service_states='[]'
    
    for service in "${services[@]}"; do
        if command -v systemctl >/dev/null 2>&1; then
            local service_status service_active service_enabled
            service_active=$(systemctl is-active "$service" 2>/dev/null || echo "unknown")
            service_enabled=$(systemctl is-enabled "$service" 2>/dev/null || echo "unknown")
            
            local service_info
            service_info=$(jq -n \
                --arg name "$service" \
                --arg active "$service_active" \
                --arg enabled "$service_enabled" \
                '{
                    name: $name,
                    active: $active,
                    enabled: $enabled,
                    healthy: ($active == "active")
                }')
            
            service_states=$(echo "$service_states" | jq ". + [$service_info]")
        fi
    done
    
    status=$(echo "$status" | jq --argjson services "$service_states" '.services = $services')
    
    echo "$status"
}

# Get recent monitoring events
get_recent_events() {
    local hours_back="${1:-24}"
    
    log_debug "Collecting events from last $hours_back hours"
    
    local since
    since=$(date -d "$hours_back hours ago" -Iseconds)
    
    # Query journald for recent CalendarBot events
    local events='[]'
    
    if command -v journalctl >/dev/null 2>&1; then
        local raw_events
        raw_events=$(journalctl \
            --since="$since" \
            --unit="calendarbot*" \
            --output=json \
            --no-pager \
            --quiet \
            2>/dev/null | head -1000)  # Limit to prevent memory issues
        
        # Process and filter events
        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                local message
                message=$(echo "$line" | jq -r '.MESSAGE // empty' 2>/dev/null)
                
                if [[ -n "$message" ]] && echo "$message" | jq . >/dev/null 2>&1; then
                    events=$(echo "$events" | jq ". + [$message]")
                fi
            fi
        done <<< "$raw_events"
    fi
    
    echo "$events"
}

# Calculate event statistics
calculate_event_stats() {
    local events="$1"
    
    log_debug "Calculating event statistics"
    
    local stats
    stats=$(echo "$events" | jq '{
        total_events: length,
        by_level: group_by(.level) | map({
            level: .[0].level,
            count: length
        }),
        by_component: group_by(.component) | map({
            component: .[0].component,
            count: length
        }),
        error_count: map(select(.level == "ERROR" or .level == "CRITICAL")) | length,
        recovery_actions: map(select(.recovery_level and (.recovery_level | tonumber) > 0)) | length,
        critical_events: map(select(.level == "CRITICAL")) | length,
        recent_errors: map(select(.level == "ERROR" or .level == "CRITICAL")) | 
                      sort_by(.timestamp) | reverse | .[0:5]
    }')
    
    echo "$stats"
}

# Get trend data from historical reports
get_trend_data() {
    local days_back="${1:-7}"
    
    log_debug "Collecting trend data for $days_back days"
    
    local trends='[]'
    
    # Look for daily reports
    for ((i=0; i<days_back; i++)); do
        local date_str
        date_str=$(date -d "$i days ago" +%Y-%m-%d)
        
        local report_file="$REPORTS_DIR/daily_${date_str}.json"
        
        if [[ -f "$report_file" ]]; then
            local report_data
            report_data=$(cat "$report_file" 2>/dev/null || echo '{}')
            
            if [[ -n "$report_data" ]] && echo "$report_data" | jq . >/dev/null 2>&1; then
                local trend_point
                trend_point=$(echo "$report_data" | jq \
                    --arg date "$date_str" \
                    '{
                        date: $date,
                        total_events: .summary.total_events // 0,
                        error_count: (.summary.by_level[] | select(.level == "ERROR" or .level == "CRITICAL") | .count) // 0,
                        recovery_actions: .summary.recovery_actions.total // 0,
                        critical_count: (.summary.by_level[] | select(.level == "CRITICAL") | .count) // 0
                    }')
                
                trends=$(echo "$trends" | jq ". + [$trend_point]")
            fi
        fi
    done
    
    # Sort by date
    trends=$(echo "$trends" | jq 'sort_by(.date)')
    
    echo "$trends"
}

# Generate dashboard-compatible status
generate_dashboard_status() {
    local output_file="$1"
    local real_time="${2:-true}"
    
    log_info "Generating dashboard status (real-time: $real_time)"
    
    local timestamp
    timestamp=$(date -Iseconds)
    
    # Collect all data
    local system_metrics service_status
    system_metrics=$(get_system_metrics)
    service_status=$(get_service_status)
    
    # Get recent events
    local recent_events event_stats
    recent_events=$(get_recent_events 24)
    event_stats=$(calculate_event_stats "$recent_events")
    
    # Determine overall health status
    local overall_status="healthy"
    local server_status
    server_status=$(echo "$service_status" | jq -r '.server.status')
    
    if [[ "$server_status" == "critical" ]] || [[ "$server_status" == "unreachable" ]]; then
        overall_status="critical"
    elif [[ "$server_status" == "degraded" ]]; then
        overall_status="degraded"
    fi
    
    # Check for recent critical events
    local critical_count
    critical_count=$(echo "$event_stats" | jq -r '.critical_events')
    if [[ $critical_count -gt 0 ]]; then
        overall_status="critical"
    fi
    
    # Build base status
    local status
    status=$(jq -n \
        --arg timestamp "$timestamp" \
        --arg status "$overall_status" \
        --arg version "$VERSION" \
        --argjson system "$system_metrics" \
        --argjson services "$service_status" \
        --argjson events "$event_stats" \
        '{
            timestamp: $timestamp,
            version: $version,
            status: $status,
            system: $system,
            services: $services,
            events: $events,
            uptime_hours: (($system.uptime_seconds // 0) / 3600 | floor)
        }')
    
    # Add trend data if enabled and not real-time only
    if [[ "$INCLUDE_TRENDS" == "true" && "$real_time" != "true" ]]; then
        local trends
        trends=$(get_trend_data 7)
        status=$(echo "$status" | jq --argjson trends "$trends" '.trends = $trends')
    fi
    
    # Add health indicators for dashboard compatibility
    local indicators
    indicators=$(jq -n '{
        server_reachable: ($services.server.reachable // false),
        memory_usage_ok: (($system.memory.usage_percent // 100) < 90),
        disk_usage_ok: (($system.disk.usage_percent // 100) < 85),
        load_ok: (($system.cpu.load_1m // 2.0) < 1.5),
        recent_errors_low: (($events.error_count // 100) < 10),
        no_critical_events: (($events.critical_events // 1) == 0)
    }' \
        --argjson services "$service_status" \
        --argjson system "$system_metrics" \
        --argjson events "$event_stats")
    
    status=$(echo "$status" | jq --argjson indicators "$indicators" '.health_indicators = $indicators')
    
    # Add Grafana-compatible metrics
    local grafana_metrics
    grafana_metrics=$(echo "$status" | jq '{
        calendarbot_up: (if .services.server.reachable then 1 else 0 end),
        calendarbot_memory_usage_percent: (.system.memory.usage_percent // 0),
        calendarbot_disk_usage_percent: (.system.disk.usage_percent // 0),
        calendarbot_cpu_load: (.system.cpu.load_1m // 0),
        calendarbot_events_total_24h: (.events.total_events // 0),
        calendarbot_errors_total_24h: (.events.error_count // 0),
        calendarbot_recovery_actions_24h: (.events.recovery_actions // 0),
        calendarbot_critical_events_24h: (.events.critical_events // 0),
        calendarbot_uptime_hours: .uptime_hours
    }')
    
    status=$(echo "$status" | jq --argjson metrics "$grafana_metrics" '.metrics = $metrics')
    
    # Write output
    echo "$status" > "$output_file"
    
    log_info "Dashboard status generated: $output_file"
}

# Generate Prometheus metrics format
generate_prometheus_metrics() {
    local output_file="$1"
    
    log_info "Generating Prometheus metrics"
    
    local status_file="$TEMP_DIR/status.json"
    generate_dashboard_status "$status_file" "true"
    
    local status
    status=$(cat "$status_file")
    
    # Generate Prometheus format
    cat > "$output_file" <<EOF
# HELP calendarbot_up CalendarBot server is reachable
# TYPE calendarbot_up gauge
calendarbot_up $(echo "$status" | jq -r '.metrics.calendarbot_up')

# HELP calendarbot_memory_usage_percent Memory usage percentage
# TYPE calendarbot_memory_usage_percent gauge
calendarbot_memory_usage_percent $(echo "$status" | jq -r '.metrics.calendarbot_memory_usage_percent')

# HELP calendarbot_disk_usage_percent Disk usage percentage
# TYPE calendarbot_disk_usage_percent gauge
calendarbot_disk_usage_percent $(echo "$status" | jq -r '.metrics.calendarbot_disk_usage_percent')

# HELP calendarbot_cpu_load_1m CPU load average 1 minute
# TYPE calendarbot_cpu_load_1m gauge
calendarbot_cpu_load_1m $(echo "$status" | jq -r '.metrics.calendarbot_cpu_load')

# HELP calendarbot_events_total_24h Total events in last 24 hours
# TYPE calendarbot_events_total_24h counter
calendarbot_events_total_24h $(echo "$status" | jq -r '.metrics.calendarbot_events_total_24h')

# HELP calendarbot_errors_total_24h Total errors in last 24 hours
# TYPE calendarbot_errors_total_24h counter
calendarbot_errors_total_24h $(echo "$status" | jq -r '.metrics.calendarbot_errors_total_24h')

# HELP calendarbot_recovery_actions_24h Recovery actions in last 24 hours
# TYPE calendarbot_recovery_actions_24h counter
calendarbot_recovery_actions_24h $(echo "$status" | jq -r '.metrics.calendarbot_recovery_actions_24h')

# HELP calendarbot_uptime_hours System uptime in hours
# TYPE calendarbot_uptime_hours gauge
calendarbot_uptime_hours $(echo "$status" | jq -r '.metrics.calendarbot_uptime_hours')
EOF
    
    log_info "Prometheus metrics generated: $output_file"
}

# Check cache validity
is_cache_valid() {
    local cache_file="$1"
    
    if [[ ! -f "$cache_file" ]]; then
        return 1
    fi
    
    local cache_age
    cache_age=$(( $(date +%s) - $(stat -c %Y "$cache_file" 2>/dev/null || echo 0) ))
    
    if [[ $cache_age -gt $STATUS_CACHE_TTL ]]; then
        return 1
    fi
    
    return 0
}

# Show usage information
show_usage() {
    cat <<EOF
CalendarBot Monitoring Status Dashboard v$VERSION

USAGE:
    $0 [OPTIONS] COMMAND [OUTPUT_FILE]

COMMANDS:
    status OUTPUT_FILE      Generate complete dashboard status JSON
    metrics OUTPUT_FILE     Generate Prometheus metrics format
    realtime OUTPUT_FILE    Generate real-time status (no trends)
    health                  Quick health check (stdout)

OPTIONS:
    -h, --help              Show this help message
    -v, --version           Show version information
    -d, --debug             Enable debug logging
    -f, --format FORMAT     Output format: json, prometheus (default: json)
    --no-cache              Disable caching
    --no-trends             Disable trend data collection

ENVIRONMENT VARIABLES:
    CALENDARBOT_STATUS_DEBUG         Enable debug mode (default: false)
    CALENDARBOT_STATUS_FORMAT        Output format (default: json)
    CALENDARBOT_STATUS_CACHE         Enable caching (default: true)
    CALENDARBOT_STATUS_TRENDS        Include trend data (default: true)

EXAMPLES:
    # Generate full dashboard status
    $0 status /var/www/monitoring/calendarbot-status.json

    # Generate Prometheus metrics
    $0 metrics /var/lib/prometheus/calendarbot.prom

    # Quick health check
    $0 health

    # Real-time status without trends
    $0 realtime /tmp/status.json

    # Generate for Grafana with debug
    $0 --debug status /var/lib/grafana/calendarbot.json

EOF
}

# Main function
main() {
    local command=""
    local output_file=""
    
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
            --no-cache)
                CACHE_ENABLED="false"
                shift
                ;;
            --no-trends)
                INCLUDE_TRENDS="false"
                shift
                ;;
            status|metrics|realtime|health)
                command="$1"
                shift
                if [[ $# -gt 0 && "$command" != "health" ]]; then
                    output_file="$1"
                    shift
                fi
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
    
    # Validate output file for most commands
    if [[ "$command" != "health" && -z "$output_file" ]]; then
        log_error "$command command requires output file argument"
        exit 1
    fi
    
    # Initialize
    init_directories
    
    if ! validate_prerequisites; then
        exit 1
    fi
    
    log_debug "Starting $SCRIPT_NAME v$VERSION with command: $command"
    
    # Check cache for status commands
    local cache_file="$CACHE_DIR/status-cache.json"
    if [[ "$CACHE_ENABLED" == "true" && "$command" == "status" && -n "$output_file" ]]; then
        if is_cache_valid "$cache_file"; then
            log_debug "Using cached status"
            cp "$cache_file" "$output_file"
            exit 0
        fi
    fi
    
    # Execute command
    case $command in
        status)
            generate_dashboard_status "$output_file" "false"
            if [[ "$CACHE_ENABLED" == "true" ]]; then
                cp "$output_file" "$cache_file"
            fi
            ;;
        metrics)
            generate_prometheus_metrics "$output_file"
            ;;
        realtime)
            generate_dashboard_status "$output_file" "true"
            ;;
        health)
            local health_file="$TEMP_DIR/health.json"
            generate_dashboard_status "$health_file" "true"
            
            local status overall_server
            status=$(cat "$health_file")
            overall_server=$(echo "$status" | jq -r '.status')
            
            echo "CalendarBot Health Status: $overall_server"
            echo "Server reachable: $(echo "$status" | jq -r '.services.server.reachable')"
            echo "Memory usage: $(echo "$status" | jq -r '.system.memory.usage_percent')%"
            echo "Disk usage: $(echo "$status" | jq -r '.system.disk.usage_percent')%"
            echo "Recent errors: $(echo "$status" | jq -r '.events.error_count')"
            
            # Exit with error code if not healthy
            if [[ "$overall_server" != "healthy" ]]; then
                exit 1
            fi
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