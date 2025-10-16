# Installation Guide

## Prerequisites

- **Python 3.9+** with pip
- **Git** for cloning the repository
- **Internet connection** for calendar feeds

## Quick Installation

```bash
# Clone and setup
git clone <repository-url>
cd calendarBot

# Create virtual environment
python -m venv venv
. venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Setup

Run the interactive setup wizard:

```bash
calendarbot --setup
```

Or set environment variables:

```bash
export CALENDARBOT_ICS_URL="https://example.com/calendar.ics"
export CALENDARBOT_ICS_AUTH_TYPE="none"
```

## Launch

```bash
# Activate environment
. venv/bin/activate

# Interactive mode
calendarbot

# Web interface
calendarbot --web

# E-paper display
calendarbot --epaper

# On resource-constrained devices (for example Pi Zero2 W) you can
# disable e-paper initialization and its heavy components with:
# export CALENDARBOT_DISABLE_EPAPER=1
#
# Alternatively, use the consolidated Pi-optimized mode which applies a
# recommended set of performance overrides for Pi Zero2 W (disables monitoring,
# reduces asset/prebuild usage and limits events processed):
#   python -m calendarbot.main --web --port 8080 --pi-optimized
# or using environment variable only:
#   export CALENDARBOT_PI_OPTIMIZED=1 && python -m calendarbot.main --web --port 8080
```
# Monitoring on resource-constrained devices
# On small devices (for example Raspberry Pi Zero2 W) monitoring and frequent sampling
# can increase CPU and disk I/O. Consider disabling heavy monitoring or enabling
# small-device optimizations in your configuration.
#
# Example (config.yaml):
# optimization:
#   small_device: true
# monitoring:
#   enabled: false
#   sampling_interval_seconds: 30
#
# Alternatively, set environment variable to disable monitoring:
# export CALENDARBOT_MONITORING=0

## Dependencies

Core Python packages:
- `icalendar>=5.0.0` - ICS calendar parsing
- `httpx>=0.25.0` - HTTP client
- `aiosqlite>=0.19.0` - Async SQLite database
- `pydantic>=2.0.0` - Data validation
- `PyYAML>=6.0` - Configuration

## Troubleshooting

**Python version error**:
```bash
python --version  # Check version
# Install newer Python from python.org if needed
```

**Install failures**:
```bash
pip install --upgrade pip
pip install -r requirements.txt