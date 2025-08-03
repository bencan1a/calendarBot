# Installation Guide

This guide provides complete instructions for installing and setting up Calendar Bot on your system.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Installation Steps](#quick-installation-steps)
- [Python Environment Setup](#python-environment-setup)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

## Prerequisites

### System Requirements

- **Python 3.8 or higher** with pip
- **Git** for cloning the repository
- **Internet connection** for accessing calendar feeds

### Python Verification

Check your Python version:

```bash
python --version
# or
python3 --version
```

If Python is not installed or version is too old, download from [python.org](https://python.org).

## Quick Installation Steps

### Method 1: Git Clone (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd calendarBot

# Create and activate virtual environment
python -m venv venv
. venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Method 2: Download ZIP

1. Download ZIP file from GitHub
2. Extract to your preferred location
3. Follow virtual environment setup from Method 1

## Python Environment Setup

### Virtual Environment (Recommended)

Using a virtual environment isolates Calendar Bot's dependencies:

```bash
# Create virtual environment
python -m venv venv

# Activate environment
. venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Verify installation (should show icalendar and dependencies)
pip list | grep -E "(icalendar|httpx|pydantic)"
```

### System-wide Installation

**Not recommended** due to dependency conflicts. If required:

```bash
pip install -r requirements.txt  # Installs globally
```

## Dependencies Overview

Calendar Bot requires these Python packages:

```bash
icalendar>=5.0.0      # ICS calendar parsing
httpx>=0.25.0         # HTTP client for fetching
aiosqlite>=0.19.0     # Async SQLite database
pydantic>=2.0.0       # Data validation
pydantic-settings>=2.0.0  # Settings management
PyYAML>=6.0           # YAML configuration
python-dateutil>=2.8.0    # Date parsing
pytz>=2023.3          # Timezone support
cryptography>=41.0.0  # Secure credentials
APScheduler>=3.10.0   # Task scheduling
```

## Troubleshooting

### Installation Issues

**Python version error**:
```bash
# Check Python version
python --version

# If too old, install newer Python from python.org
# Then retry installation
```

**Pip install failures**:
```bash
pip install --upgrade pip

sudo apt install python3-dev build-essential  # Linux
xcode-select --install  # macOS

pip install -r requirements.txt
```

## See Also

- 📋 [Quick Start Guide](QUICK_START.md)
- ⚙️ [Setup Guide](SETUP.md)
- 📘 [Full Usage Guide](USAGE.md)
