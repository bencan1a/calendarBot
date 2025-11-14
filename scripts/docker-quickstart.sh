#!/bin/bash
# Quick Start Script for CalendarBot Docker Deployment
# This script sets up and starts CalendarBot in Docker

set -e  # Exit on error

echo "=================================================="
echo "CalendarBot Docker Quick Start"
echo "=================================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo "❌ Error: Docker Compose is not installed"
    echo "Please install Docker Compose from: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✓ Docker is installed"
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
echo "Starting CalendarBot Docker Container"
echo "=================================================="
echo ""

# Use docker compose or docker-compose depending on what's available
if docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Build and start the container
echo "Building Docker image (this may take a few minutes)..."
$DOCKER_COMPOSE build

echo ""
echo "Starting container..."
$DOCKER_COMPOSE up -d

echo ""
echo "Waiting for container to be healthy..."
sleep 5

# Check if container is running
if $DOCKER_COMPOSE ps | grep -q "Up"; then
    echo ""
    echo "=================================================="
    echo "✓ CalendarBot is running!"
    echo "=================================================="
    echo ""
    echo "Access your calendar:"
    echo "  Kiosk Display:  http://localhost:8080"
    echo "  Health Check:   http://localhost:8080/api/health"
    echo "  Next Events:    http://localhost:8080/api/whats-next"
    echo ""
    echo "Useful commands:"
    echo "  View logs:      $DOCKER_COMPOSE logs -f"
    echo "  Stop:           $DOCKER_COMPOSE down"
    echo "  Restart:        $DOCKER_COMPOSE restart"
    echo "  Status:         $DOCKER_COMPOSE ps"
    echo ""
    echo "For more information, see DOCKER.md"
    echo "=================================================="
else
    echo ""
    echo "❌ Error: Container failed to start"
    echo ""
    echo "Check logs with:"
    echo "  $DOCKER_COMPOSE logs"
    exit 1
fi
