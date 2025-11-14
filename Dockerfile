# CalendarBot Lite - Docker Container for Kiosk Deployment
# Multi-stage build for optimized image size

# Stage 1: Build stage
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt pyproject.toml ./
COPY README.md ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.12-slim

# Set labels
LABEL maintainer="CalendarBot Team <support@calendarbot.local>"
LABEL description="CalendarBot Lite - ICS Calendar Display with Alexa Integration"
LABEL version="0.1.0"

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY calendarbot_lite/ ./calendarbot_lite/
COPY main.py ./

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CALENDARBOT_WEB_HOST=0.0.0.0 \
    CALENDARBOT_WEB_PORT=8080

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash calendarbot && \
    chown -R calendarbot:calendarbot /app
USER calendarbot

# Expose web server port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Run the application
CMD ["python", "-m", "calendarbot_lite"]
