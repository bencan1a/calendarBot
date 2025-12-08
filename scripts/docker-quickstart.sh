#!/bin/bash
# Quick Start Script for CalendarBot Docker Deployment
# This script sets up and starts CalendarBot in Docker

set -e  # Exit on error

echo "=================================================="
echo "CalendarBot Container Quick Start"
echo "=================================================="
echo ""

# Detect container runtime (Docker or Podman)
CONTAINER_RUNTIME=""
RUNTIME_NAME=""

# Check if Docker daemon is running (real Docker, not Podman wrapper)
if command -v docker &> /dev/null && systemctl is-active docker &> /dev/null 2>&1; then
    CONTAINER_RUNTIME="docker"
    RUNTIME_NAME="Docker"
elif command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
    # Docker command works, but check if it's real Docker or Podman wrapper
    if docker info 2>&1 | grep -qi "buildahVersion\|podman"; then
        # This is Podman masquerading as Docker
        CONTAINER_RUNTIME="podman"
        RUNTIME_NAME="Podman"
    else
        # Real Docker daemon is running
        CONTAINER_RUNTIME="docker"
        RUNTIME_NAME="Docker"
    fi
elif command -v podman &> /dev/null; then
    # Podman is available
    CONTAINER_RUNTIME="podman"
    RUNTIME_NAME="Podman"
else
    echo "❌ Error: Neither Docker nor Podman is installed or running"
    echo "Please install one of:"
    echo "  - Docker: https://docs.docker.com/get-docker/"
    echo "  - Podman: https://podman.io/getting-started/installation"
    exit 1
fi

echo "✓ Using $RUNTIME_NAME"

# Check if appropriate Compose tool is available
if [ "$CONTAINER_RUNTIME" = "docker" ]; then
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        echo "❌ Error: Docker Compose is not installed"
        echo "Please install Docker Compose from: https://docs.docker.com/compose/install/"
        exit 1
    fi
elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
    if ! command -v podman-compose &> /dev/null; then
        echo "❌ Error: podman-compose is not installed"
        echo "Please install it with: sudo apt install podman-compose"
        exit 1
    fi
fi

echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    if [ -f .env.docker ]; then
        cp .env.docker .env
        echo "✓ Created .env from .env.docker template"
        echo ""
        echo "⚠️  IMPORTANT: You must edit .env and set your calendar URL!"
        echo ""
        echo "Edit .env now? (y/n)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env
        else
            echo ""
            echo "Please edit .env manually before continuing:"
            echo "  nano .env"
            echo ""
            echo "At minimum, set:"
            echo "  CALENDARBOT_ICS_URL=your-calendar-url"
            echo ""
            exit 0
        fi
    else
        echo "❌ Error: .env.docker template not found"
        exit 1
    fi
else
    echo "✓ Found .env file"
fi

# Validate .env has required settings
if ! grep -q "^CALENDARBOT_ICS_URL=http" .env; then
    echo ""
    echo "⚠️  WARNING: CALENDARBOT_ICS_URL not set or invalid in .env"
    echo ""
    echo "Your .env file must contain a valid calendar URL:"
    echo "  CALENDARBOT_ICS_URL=https://outlook.office365.com/owa/calendar/..."
    echo ""
    echo "Edit .env now? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env
    else
        echo ""
        echo "Please edit .env and set your calendar URL, then run this script again."
        exit 1
    fi
fi

echo ""
echo "=================================================="
echo "Starting CalendarBot Container"
echo "=================================================="
echo ""

# Select appropriate compose command based on runtime
if [ "$CONTAINER_RUNTIME" = "docker" ]; then
    # Use docker compose or docker-compose depending on what's available
    if docker compose version &> /dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
    COMPOSE_CMD="podman-compose"
fi

# Build and start the container
echo "Building container image (this may take a few minutes)..."
$COMPOSE_CMD build

echo ""
echo "Starting container..."
$COMPOSE_CMD up -d

echo ""
echo "Waiting for container to be healthy..."
sleep 5

# Check if container is running
if ! $COMPOSE_CMD ps | grep -q "Up"; then
    echo ""
    echo "❌ Error: Container failed to start"
    echo ""
    echo "Check logs with:"
    echo "  $COMPOSE_CMD logs"
    exit 1
fi

echo ""
echo "=================================================="
echo "✓ CalendarBot is running!"
echo "=================================================="
echo ""

# Setup auto-start on boot
echo "=================================================="
echo "Setting up auto-start on boot"
echo "=================================================="
echo ""

if [ "$CONTAINER_RUNTIME" = "docker" ]; then
    # Enable Docker daemon to start on boot
    if ! systemctl is-enabled docker &> /dev/null; then
        echo "Enabling Docker daemon to start on boot..."
        sudo systemctl enable docker
        echo "✓ Docker daemon will start on boot"
    else
        echo "✓ Docker daemon already enabled for auto-start"
    fi
    echo "  (Container will auto-restart due to 'restart: unless-stopped' policy)"

elif [ "$CONTAINER_RUNTIME" = "podman" ]; then
    # Setup Podman systemd service
    SERVICE_NAME="calendarbot-lite"
    SERVICE_FILE="$HOME/.config/systemd/user/${SERVICE_NAME}.service"

    echo "Creating systemd service for Podman container..."

    # Create systemd user directory if it doesn't exist
    mkdir -p "$HOME/.config/systemd/user"

    # Generate systemd service file
    cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=CalendarBot Lite Container
Wants=network-online.target
After=network-online.target
RequiresMountsFor=%t/containers

[Service]
Environment=PODMAN_SYSTEMD_UNIT=%n
Restart=on-failure
TimeoutStopSec=70
ExecStartPre=/bin/rm -f %t/%n.ctr-id
ExecStart=/usr/bin/podman run \\
    --cidfile=%t/%n.ctr-id \\
    --cgroups=no-conmon \\
    --rm \\
    --sdnotify=conmon \\
    --replace \\
    --name ${SERVICE_NAME} \\
    --publish 0.0.0.0:8080:8080 \\
    --env-file $(pwd)/.env \\
    --env CALENDARBOT_WEB_HOST=0.0.0.0 \\
    --env CALENDARBOT_WEB_PORT=8080 \\
    localhost/calendarbot_calendarbot:latest
ExecStop=/usr/bin/podman stop --ignore --cidfile=%t/%n.ctr-id
ExecStopPost=/usr/bin/podman rm -f --ignore --cidfile=%t/%n.ctr-id
Type=notify
NotifyAccess=all

[Install]
WantedBy=default.target
EOF

    echo "✓ Created systemd service file: $SERVICE_FILE"

    # Reload systemd
    systemctl --user daemon-reload

    # Enable the service
    systemctl --user enable ${SERVICE_NAME}.service
    echo "✓ Enabled ${SERVICE_NAME}.service"

    # Enable lingering so service starts on boot even when not logged in
    loginctl enable-linger $USER
    echo "✓ Enabled user lingering (service will start on boot)"

    echo ""
    echo "Systemd service commands:"
    echo "  Status:   systemctl --user status ${SERVICE_NAME}"
    echo "  Start:    systemctl --user start ${SERVICE_NAME}"
    echo "  Stop:     systemctl --user stop ${SERVICE_NAME}"
    echo "  Restart:  systemctl --user restart ${SERVICE_NAME}"
    echo "  Logs:     journalctl --user -u ${SERVICE_NAME} -f"
fi

echo ""
echo "=================================================="
echo "Network Access Configuration"
echo "=================================================="
echo ""

# Get host IP addresses
HOST_IPS=$(hostname -I 2>/dev/null || ip addr show | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1)

echo "Your CalendarBot is accessible at:"
echo ""
echo "  Local access:"
echo "    http://localhost:8080"
echo ""

if [ -n "$HOST_IPS" ]; then
    echo "  Network access:"
    for ip in $HOST_IPS; do
        echo "    http://${ip}:8080"
    done
    echo ""
    echo "✓ Container is bound to 0.0.0.0 (accessible from network)"
else
    echo "  (Could not detect network IP addresses)"
fi

echo ""
echo "Endpoints:"
echo "  Kiosk Display:  /kiosk"
echo "  Health Check:   /api/health"
echo "  Next Events:    /api/whats-next"
echo ""

echo "=================================================="
echo "Useful Commands"
echo "=================================================="
echo ""
if [ "$CONTAINER_RUNTIME" = "podman" ]; then
    echo "Container management:"
    echo "  View logs:      $COMPOSE_CMD logs -f"
    echo "  Stop:           $COMPOSE_CMD down"
    echo "  Restart:        $COMPOSE_CMD restart"
    echo "  Status:         $COMPOSE_CMD ps"
    echo ""
    echo "Systemd service management:"
    echo "  Status:         systemctl --user status ${SERVICE_NAME}"
    echo "  Restart:        systemctl --user restart ${SERVICE_NAME}"
    echo "  Logs:           journalctl --user -u ${SERVICE_NAME} -f"
else
    echo "  View logs:      $COMPOSE_CMD logs -f"
    echo "  Stop:           $COMPOSE_CMD down"
    echo "  Restart:        $COMPOSE_CMD restart"
    echo "  Status:         $COMPOSE_CMD ps"
fi
echo ""
echo "For more information, see DOCKER.md"
echo "=================================================="
