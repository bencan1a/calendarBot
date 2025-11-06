#!/bin/bash
# CalendarBot Port Cleanup Script
# Non-interactive port conflict resolution for systemd/kiosk deployment

set -euo pipefail

# Configuration
PORT="${1:-8080}"
HOST="${2:-127.0.0.1}"
FORCE="${3:-false}"
LOG_PRIORITY="info"

# Logging function with journald integration
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Log to stderr for systemd capture
    echo "[$timestamp] [$level] port-cleanup: $message" >&2

    # Also log to journald if available
    if command -v logger >/dev/null 2>&1; then
        logger -t "calendarbot-port-cleanup" -p "daemon.$level" "$message"
    fi
}

# Check if port is in use
check_port_usage() {
    local port="$1"
    local host="$2"

    # Try multiple methods to detect port usage
    if command -v ss >/dev/null 2>&1; then
        ss -ltn "sport = :$port" | grep -q ":$port" 2>/dev/null
    elif command -v netstat >/dev/null 2>&1; then
        netstat -ln | grep -q ":$port " 2>/dev/null
    elif command -v lsof >/dev/null 2>&1; then
        lsof -i ":$port" >/dev/null 2>&1
    else
        log "error" "No network tools available (ss, netstat, lsof)"
        return 2
    fi
}

# Find process using port
find_port_process() {
    local port="$1"
    local result=""

    # Try ss first (most reliable)
    if command -v ss >/dev/null 2>&1; then
        result=$(ss -ltnp "sport = :$port" 2>/dev/null | grep ":$port" | head -1)
        if [ -n "$result" ]; then
            # Extract PID from ss output (format: users:(("process",pid=1234,fd=5)))
            echo "$result" | sed -n 's/.*pid=\([0-9]*\).*/\1/p'
            return 0
        fi
    fi

    # Try lsof as fallback
    if command -v lsof >/dev/null 2>&1; then
        result=$(lsof -ti ":$port" 2>/dev/null | head -1)
        if [ -n "$result" ]; then
            echo "$result"
            return 0
        fi
    fi

    # Try netstat + ps combination
    if command -v netstat >/dev/null 2>&1 && command -v ps >/dev/null 2>&1; then
        local inode
        inode=$(netstat -ln --protocol=inet | awk "\$4 ~ /:$port\$/ {print \$NF}" | head -1)
        if [ -n "$inode" ] && [ "$inode" != "-" ]; then
            # Find process by socket inode
            local pid
            pid=$(find /proc/*/fd -type l 2>/dev/null | xargs -r ls -l 2>/dev/null | \
                  awk -v inode="$inode" '$NF ~ "socket:\\[" inode "\\]" {split($9, a, "/"); print a[3]}' | head -1)
            if [ -n "$pid" ]; then
                echo "$pid"
                return 0
            fi
        fi
    fi

    return 1
}

# Get process information
get_process_info() {
    local pid="$1"

    if [ ! -d "/proc/$pid" ]; then
        echo "Process $pid no longer exists"
        return 1
    fi

    local cmdline
    cmdline=$(cat "/proc/$pid/cmdline" 2>/dev/null | tr '\0' ' ' | sed 's/ *$//')

    local exe
    exe=$(readlink "/proc/$pid/exe" 2>/dev/null || echo "unknown")

    local user
    user=$(stat -c %U "/proc/$pid" 2>/dev/null || echo "unknown")

    echo "PID: $pid, User: $user, Exe: $exe, Cmd: $cmdline"
}

# Check if process is safe to terminate
is_safe_to_terminate() {
    local pid="$1"
    local cmdline="$2"
    local exe="$3"
    local user="$4"

    # Never terminate system processes (PID < 100)
    if [ "$pid" -lt 100 ]; then
        log "warn" "Refusing to terminate system process $pid"
        return 1
    fi

    # Never terminate root processes unless they're clearly CalendarBot-related
    if [ "$user" = "root" ]; then
        case "$cmdline" in
            *calendarbot*|*python*calendarbot*)
                log "info" "Root process appears to be CalendarBot-related: $cmdline"
                ;;
            *)
                log "warn" "Refusing to terminate root process: $cmdline"
                return 1
                ;;
        esac
    fi

    # Check for critical system processes
    case "$(basename "$exe")" in
        systemd|init|kernel*|kthread*|ssh*|dbus*|NetworkManager|systemd-*)
            log "warn" "Refusing to terminate critical system process: $exe"
            return 1
            ;;
    esac

    # Identify likely CalendarBot processes
    case "$cmdline" in
        *calendarbot*|*python*calendarbot*|*"python -m calendarbot"*)
            log "info" "Process appears to be CalendarBot: $cmdline"
            return 0
            ;;
        *python*|*uvicorn*|*gunicorn*|*aiohttp*)
            log "info" "Process appears to be a Python web server: $cmdline"
            return 0
            ;;
    esac

    # For other processes, be cautious in non-force mode
    if [ "$FORCE" != "true" ]; then
        log "warn" "Refusing to terminate unknown process without --force: $cmdline"
        return 1
    fi

    log "warn" "Force mode enabled, will attempt to terminate: $cmdline"
    return 0
}

# Terminate process gracefully
terminate_process() {
    local pid="$1"
    local process_info="$2"

    log "info" "Attempting graceful termination of process: $process_info"

    # Send TERM signal
    if ! kill -TERM "$pid" 2>/dev/null; then
        log "error" "Failed to send TERM signal to process $pid"
        return 1
    fi

    # Wait up to 10 seconds for graceful shutdown
    local wait_count=0
    while [ $wait_count -lt 10 ]; do
        if ! kill -0 "$pid" 2>/dev/null; then
            log "info" "Process $pid terminated gracefully"
            return 0
        fi
        sleep 1
        ((wait_count++))
    done

    # If still running, send KILL signal
    log "warn" "Process $pid did not exit gracefully, sending KILL signal"
    if kill -KILL "$pid" 2>/dev/null; then
        # Wait a bit more for KILL to take effect
        sleep 2
        if ! kill -0 "$pid" 2>/dev/null; then
            log "info" "Process $pid terminated forcefully"
            return 0
        fi
    fi

    log "error" "Failed to terminate process $pid"
    return 1
}

# Main cleanup function
cleanup_port() {
    local port="$1"
    local host="$2"

    log "info" "Checking port $port usage on $host"

    # Check if port is actually in use
    if ! check_port_usage "$port" "$host"; then
        log "info" "Port $port is not in use"
        return 0
    fi

    log "warn" "Port $port is in use, attempting to identify the process"

    # Find the process using the port
    local pid
    pid=$(find_port_process "$port")

    if [ -z "$pid" ]; then
        log "error" "Could not identify process using port $port"
        return 1
    fi

    # Get process information
    local process_info
    process_info=$(get_process_info "$pid")

    if [ $? -ne 0 ]; then
        log "error" "Could not get information for process $pid"
        return 1
    fi

    log "info" "Found process using port $port: $process_info"

    # Extract process details for safety check
    local user exe cmdline
    user=$(echo "$process_info" | sed -n 's/.*User: \([^,]*\).*/\1/p')
    exe=$(echo "$process_info" | sed -n 's/.*Exe: \([^,]*\).*/\1/p')
    cmdline=$(echo "$process_info" | sed -n 's/.*Cmd: \(.*\)/\1/p')

    # Check if safe to terminate
    if ! is_safe_to_terminate "$pid" "$cmdline" "$exe" "$user"; then
        log "error" "Process $pid is not safe to terminate automatically"
        return 1
    fi

    # Attempt termination
    if terminate_process "$pid" "$process_info"; then
        # Verify port is now free
        sleep 2
        if ! check_port_usage "$port" "$host"; then
            log "info" "Port $port cleanup successful"
            return 0
        else
            log "warn" "Port $port still appears to be in use after process termination"
            return 1
        fi
    else
        log "error" "Failed to terminate process using port $port"
        return 1
    fi
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [PORT] [HOST] [FORCE]

Non-interactive port cleanup script for CalendarBot kiosk deployment.

Arguments:
  PORT    Port number to clean up (default: 8080)
  HOST    Host address (default: 127.0.0.1)
  FORCE   Set to 'true' to force cleanup of unknown processes (default: false)

Examples:
  $0                    # Clean up port 8080 on localhost
  $0 3000               # Clean up port 3000 on localhost
  $0 8080 0.0.0.0       # Clean up port 8080 on all interfaces
  $0 8080 127.0.0.1 true # Force cleanup of port 8080

Exit codes:
  0 - Success (port is now free)
  1 - Error (port cleanup failed)
  2 - No tools available for port detection

Environment variables:
  CALENDARBOT_NONINTERACTIVE - Set to disable interactive prompts (auto-set in systemd)

EOF
}

# Main execution
main() {
    # Handle help requests
    case "${1:-}" in
        -h|--help|help)
            usage
            exit 0
            ;;
    esac

    # Set non-interactive mode automatically in systemd environment
    if [ -n "${JOURNAL_STREAM:-}" ] || [ -n "${SYSTEMD_EXEC_PID:-}" ]; then
        export CALENDARBOT_NONINTERACTIVE=true
    fi

    log "info" "Starting port cleanup for port $PORT on $HOST (force=$FORCE)"

    # Perform cleanup
    if cleanup_port "$PORT" "$HOST"; then
        log "info" "Port cleanup completed successfully"
        exit 0
    else
        log "error" "Port cleanup failed"
        exit 1
    fi
}

# Handle script interruption
trap 'log "warn" "Port cleanup interrupted"; exit 130' INT TERM

# Execute main function
main "$@"