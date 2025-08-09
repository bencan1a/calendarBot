#!/bin/sh
# Wait for network connectivity with configurable timeout

set -euo pipefail

# Default configuration
TIMEOUT=120
QUICK_MODE=false
TEST_HOSTS="8.8.8.8 1.1.1.1 google.com"

# Parse arguments
while [ $# -gt 0 ]; do
    case $1 in
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --quick)
            QUICK_MODE=true
            TIMEOUT=10
            shift
            ;;
        *)
            echo "Usage: $0 [--timeout SECONDS] [--quick]"
            exit 1
            ;;
    esac
done

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Waiting for network connectivity (timeout: ${TIMEOUT}s)"

# Wait for network interface to be up
i=0
while [ $i -lt $TIMEOUT ]; do
    if ip route | grep -q default; then
        log "Default route available"
        break
    fi
    
    if [ $i -eq $((TIMEOUT-1)) ]; then
        log "ERROR: No default route after ${TIMEOUT}s"
        exit 1
    fi
    
    sleep 1
    i=$((i+1))
done

# Test actual connectivity
i=0
while [ $i -lt $TIMEOUT ]; do
    for host in $TEST_HOSTS; do
        if ping -c 1 -W 2 "$host" >/dev/null 2>&1; then
            log "Network connectivity verified (reached $host)"
            exit 0
        fi
    done
    
    if [ "$QUICK_MODE" = "true" ] && [ $i -ge 5 ]; then
        log "Quick mode: giving up after 5 attempts"
        exit 1
    fi
    
    if [ $i -eq $((TIMEOUT-1)) ]; then
        log "ERROR: No network connectivity after ${TIMEOUT}s"
        exit 1
    fi
    
    sleep 1
    i=$((i+1))
done