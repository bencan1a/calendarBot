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
```

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