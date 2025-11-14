# CalendarBot Docker Deployment Guide

This guide explains how to deploy CalendarBot Lite using Docker containers for an isolated, portable environment.

## Overview

The Docker deployment provides:

- 🐳 **Isolated Environment** - Self-contained application with all dependencies
- 🚀 **Easy Deployment** - One-command setup on any Docker-capable host
- 🔌 **Exposed Endpoints** - Web server and Alexa endpoints accessible from the host network
- 📦 **Portable** - Deploy on any machine with Docker (Linux, macOS, Windows with WSL2)
- 🔄 **Auto-restart** - Container automatically restarts on failure or system reboot
- 💾 **Persistent Data** - Optional volume for maintaining state across restarts

## Quick Start

### Prerequisites

- Docker 20.10+ installed ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose 1.29+ (usually included with Docker Desktop)
- ICS calendar feed URL (Office 365, Google Calendar, iCloud, etc.)

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/bencan1a/calendarbot.git
   cd calendarbot
   ```

2. **Configure environment:**
   ```bash
   cp .env.docker .env
   nano .env  # Edit with your calendar URL and settings
   ```

   At minimum, set your calendar URL:
   ```bash
   CALENDARBOT_ICS_URL=https://outlook.office365.com/owa/calendar/your-calendar-id/calendar.ics
   ```

3. **Start the container:**
   ```bash
   docker-compose up -d
   ```

4. **Verify it's running:**
   ```bash
   # Check container status
   docker-compose ps
   
   # View logs
   docker-compose logs -f
   
   # Test the API
   curl http://localhost:8080/api/health
   ```

5. **Access the application:**
   - **Kiosk Display:** http://localhost:8080
   - **Health Check:** http://localhost:8080/api/health
   - **Next Events API:** http://localhost:8080/api/whats-next
   - **Alexa Webhook:** http://your-host-ip:8080/api/alexa/*

## Configuration

### Environment Variables

All configuration is done via the `.env` file. See `.env.docker` for a complete example.

**Required:**
- `CALENDARBOT_ICS_URL` - Your ICS calendar feed URL

**Optional:**
- `CALENDARBOT_WEB_PORT` - Port to expose (default: 8080)
- `CALENDARBOT_REFRESH_INTERVAL` - Refresh interval in seconds (default: 300)
- `CALENDARBOT_ALEXA_BEARER_TOKEN` - Bearer token for Alexa authentication
- `CALENDARBOT_DEBUG` - Enable debug logging (true/false)
- `CALENDARBOT_DEFAULT_TIMEZONE` - Default timezone (e.g., America/Los_Angeles)

See `.env.docker` for all available options.

### Port Configuration

By default, CalendarBot exposes port 8080. To use a different port:

1. Update `.env`:
   ```bash
   CALENDARBOT_WEB_PORT=3000
   ```

2. Update `docker-compose.yml`:
   ```yaml
   ports:
     - "3000:3000"  # host:container
   ```

3. Restart the container:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Resource Limits

The default `docker-compose.yml` includes conservative resource limits:

- **CPU:** 0.25-1.0 cores
- **Memory:** 128-512 MB

Adjust these in `docker-compose.yml` based on your needs:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 256M
```

## Usage

### Container Management

```bash
# Start the container
docker-compose up -d

# Stop the container
docker-compose down

# Restart the container
docker-compose restart

# View logs
docker-compose logs -f

# View last 100 lines of logs
docker-compose logs --tail=100

# Check container status
docker-compose ps

# View resource usage
docker stats calendarbot-lite
```

### Accessing Services

From the **host machine:**
```bash
# Kiosk display
curl http://localhost:8080

# Health check
curl http://localhost:8080/api/health

# Next events
curl http://localhost:8080/api/whats-next
```

From **other machines** on your network:
```bash
# Replace YOUR_HOST_IP with the Docker host's IP
curl http://YOUR_HOST_IP:8080/api/health
```

### Updating the Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose up -d --build

# Or build without using cache
docker-compose build --no-cache
docker-compose up -d
```

## Advanced Usage

### Building the Image Manually

```bash
# Build the image
docker build -t calendarbot-lite:latest .

# Run without docker-compose
docker run -d \
  --name calendarbot-lite \
  -p 8080:8080 \
  --env-file .env \
  --restart unless-stopped \
  calendarbot-lite:latest
```

### Debugging

**View detailed logs:**
```bash
# All logs
docker-compose logs -f

# Logs from the last hour
docker-compose logs --since 1h

# Logs with timestamps
docker-compose logs -f -t
```

**Execute commands in the container:**
```bash
# Open a shell
docker-compose exec calendarbot bash

# Check Python version
docker-compose exec calendarbot python --version

# Test calendar fetch
docker-compose exec calendarbot python -c "import os; print(os.environ.get('CALENDARBOT_ICS_URL'))"
```

**Inspect container:**
```bash
# View container details
docker inspect calendarbot-lite

# View network settings
docker network inspect calendarbot_calendarbot-net
```

### Health Monitoring

The container includes a health check that runs every 30 seconds:

```bash
# Check health status
docker inspect --format='{{json .State.Health}}' calendarbot-lite | jq

# View health check logs
docker inspect calendarbot-lite | jq '.[0].State.Health'
```

Healthy status means:
- Container is running
- Port 8080 is accessible
- `/api/health` endpoint responds with 200 OK

## Deployment Scenarios

### Scenario 1: Local Development

```bash
# Start with live logs
docker-compose up

# Make changes to code
# Rebuild and restart
docker-compose up --build
```

### Scenario 2: Home Server / Raspberry Pi

```bash
# Configure for auto-start on boot
docker-compose up -d

# Access from any device on your network
# http://YOUR_SERVER_IP:8080
```

### Scenario 3: Cloud Deployment (AWS, Azure, GCP)

```bash
# Deploy to a cloud VM
ssh user@your-cloud-vm
git clone https://github.com/bencan1a/calendarbot.git
cd calendarbot
cp .env.docker .env
# Edit .env with your settings
docker-compose up -d

# Configure firewall to allow port 8080
# For AWS: Add security group rule for port 8080
# For Azure: Add inbound rule for port 8080
# For GCP: Add firewall rule for port 8080
```

### Scenario 4: Alexa Integration

1. **Deploy container with public access:**
   ```bash
   # Ensure port 8080 is accessible from the internet
   # Configure your router/firewall
   docker-compose up -d
   ```

2. **Configure Alexa skill:**
   - Set webhook URL to: `https://your-domain.com/api/alexa/whatsnext`
   - Add bearer token to `.env`:
     ```bash
     CALENDARBOT_ALEXA_BEARER_TOKEN=your-secure-token
     ```
   - Restart container:
     ```bash
     docker-compose restart
     ```

See [docs/ALEXA_DEPLOYMENT_GUIDE.md](docs/ALEXA_DEPLOYMENT_GUIDE.md) for detailed Alexa setup.

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker-compose logs
```

**Common issues:**
- Missing `.env` file → Copy from `.env.docker`
- Invalid `CALENDARBOT_ICS_URL` → Check the URL is accessible
- Port 8080 already in use → Change port in `.env` and `docker-compose.yml`

### Can't Access from Host

**Verify container is running:**
```bash
docker-compose ps
```

**Check port binding:**
```bash
docker port calendarbot-lite
```

**Test from inside container:**
```bash
docker-compose exec calendarbot curl http://localhost:8080/api/health
```

### High Memory Usage

**Check current usage:**
```bash
docker stats calendarbot-lite
```

**Adjust memory limits in `docker-compose.yml`:**
```yaml
deploy:
  resources:
    limits:
      memory: 256M  # Reduce from 512M
```

### Calendar Not Updating

**Check logs for fetch errors:**
```bash
docker-compose logs -f | grep -i "fetch\|calendar\|error"
```

**Verify ICS URL is accessible from container:**
```bash
docker-compose exec calendarbot curl -I "$CALENDARBOT_ICS_URL"
```

**Force refresh:**
```bash
# Clear cache and restart
docker-compose restart
```

## Security Considerations

1. **Environment Variables:**
   - Never commit `.env` to version control
   - Use strong bearer tokens for Alexa authentication
   - Rotate tokens periodically

2. **Network Security:**
   - Use HTTPS reverse proxy (nginx, Traefik) for production
   - Limit exposed ports to necessary ones only
   - Configure firewall rules appropriately

3. **Container Security:**
   - Runs as non-root user (UID 1000)
   - Minimal base image (python:3.12-slim)
   - No unnecessary tools installed

4. **Rate Limiting:**
   - Enable rate limiting for Alexa endpoints
   - Configure in `.env`:
     ```bash
     CALENDARBOT_RATE_LIMIT_PER_IP=100
     CALENDARBOT_RATE_LIMIT_PER_TOKEN=500
     ```

## Performance Tips

1. **Resource Allocation:**
   - Allocate at least 256MB RAM
   - Use 0.5-1.0 CPU cores for optimal performance

2. **Refresh Interval:**
   - Don't set below 60 seconds to avoid excessive API calls
   - Recommended: 300 seconds (5 minutes)

3. **Logging:**
   - Rotate logs to prevent disk fill:
     ```yaml
     logging:
       driver: "json-file"
       options:
         max-size: "10m"
         max-file: "3"
     ```

## Backup and Restore

### Backup Persistent Data

```bash
# Backup skipped meetings data
docker cp calendarbot-lite:/app/data/skipped.json ./backup/

# Backup entire data volume
docker run --rm \
  -v calendarbot_calendarbot-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/calendarbot-data.tar.gz -C /data .
```

### Restore Data

```bash
# Restore skipped meetings
docker cp ./backup/skipped.json calendarbot-lite:/app/data/

# Restore entire data volume
docker run --rm \
  -v calendarbot_calendarbot-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/calendarbot-data.tar.gz -C /data
```

## Uninstalling

```bash
# Stop and remove containers, networks, and volumes
docker-compose down -v

# Remove images
docker rmi calendarbot-lite:latest

# Remove cloned repository (optional)
cd ..
rm -rf calendarbot
```

## Support

- **Issues:** [GitHub Issues](https://github.com/bencan1a/calendarbot/issues)
- **Documentation:** See [README.md](README.md) and [docs/](docs/)
- **Kiosk Setup:** See [kiosk/README.md](kiosk/README.md)

## License

See [LICENSE](LICENSE) file.
