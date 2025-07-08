# Quick Start Guide

This guide provides minimal steps to install, configure, and launch Calendar Bot quickly.

## Prerequisites
- **Python 3.8+** (with pip installed)
- **Git** for repository cloning
- **Internet access** for calendar feeds

## Installation
Clone the repository:
```bash
git clone https://github.com/yourusername/CalendarBot.git
cd CalendarBot
. venv/bin/activate  # Activate virtual environment
pip install -r requirements.txt  # Install dependencies
```

**OR** Download ZIP file (see [INSTALL.md](INSTALL.md) for details)

## Quick Setup
Run the configuration wizard's Quick Setup:
```bash
python main.py --setup
```
In the wizard, choose Quick Setup and enter your ICS URL:
```
https://example.com/calendar.ics
```

**OR** Set environment variables:
```bash
export CALENDARBOT_ICS_URL="https://example.com/calendar.ics"
export CALENDARBOT_ICS_AUTH_TYPE="none"  # Or "basic"/"bearer" if needed
```

## Launch Calendar Bot
Run the interactive calendar display:
```bash
. venv/bin/activate  # Activate if not already active
python main.py  # Launch interactive mode
```

**Next Steps**: See [INSTALL.md](INSTALL.md) and [SETUP.md](SETUP.md) for full details, then explore usage options in [USAGE.md](USAGE.md).
