# Calendar Bot

📅 **Calendar Bot** is a terminal-based calendar utility that integrates with ICS calendar feeds. Provides interactive calendar navigation, real-time updates, and cross-platform compatibility.

## Features
- 📋 Interactive navigation with keyboard controls
- Real-time data fetching from ICS feeds
- Mobile-friendly web interface
- Custom configuration via YAML or environment variables
- Built-in setup wizard for quick configuration
- Comprehensive logging system for troubleshooting
- 🔧 **Auto-staging for code formatting** - Automatically stages files modified by black/isort during commits

## Installation
1. Clone the repository and install dependencies:
```bash
git clone https://github.com/yourusername/CalendarBot.git
cd CalendarBot
. venv/bin/activate  # Use ". venv\bin\activate" on Windows
pip install -r requirements.txt
```
2. **See [Install Guide](docs/INSTALL.md)** for detailed steps.

## Quick Setup
1. Run the interactive setup wizard:
```bash
calendarbot --setup
```
2. Follow on-screen prompts to configure your ICS feed.

**See [Quick Start Guide](quick_start.md)** for common configurations.

## Usage

Daily operation modes:
```bash
# Interactive navigation with terminal UI
calendarbot  # Launches interactive mode

# Start web interface on port 8080
calendarbot --web
```

<!-- Improved maintainability and consistency with CLI structure. -->

_For advanced features, see [Usage Guide](docs/USAGE.md)_

## Developer Features

### Auto-Staging for Code Formatting
Automatically stages files modified by black and isort during commits, eliminating manual intervention.

#### Quick Setup
```bash
# Install auto-staging (one-time setup)
python scripts/install_auto_staging.py

# Verify installation
python scripts/validate_auto_staging.py
```

#### How It Works
- Detects files modified by black/isort using SHA-256 checksums
- Automatically stages only formatter-modified files
- Preserves existing staged/unstaged changes
- Includes comprehensive error handling and rollback mechanisms

#### Documentation
- 📋 **[Auto-Staging User Guide](docs/AUTO_STAGING_USER_GUIDE.md)** - Complete usage and configuration guide
- 📋 **[Auto-Staging Troubleshooting](docs/AUTO_STAGING_TROUBLESHOOTING.md)** - Common issues and solutions
- 📋 **[Auto-Staging Technical Specification](docs/AUTO_STAGING_TECHNICAL_SPECIFICATION.md)** - Architecture and implementation details

## Additional Resources
📋 **[Full Installation Guide](docs/FULL_INSTALL.md)** (includes backup/restore)
📋 **[Architecture Overview](docs/ARCHITECTURE.md)** (system design, components)
📋 **[Community Contributions](CONTRIBUTING.md)** (developer guidelines)
---
### Get Support
- 🗺️ **GitHub Issues**: Post bugs/bugs at [GitHub Issues](https://github.com/yourusername/CalendarBot/issues/new)
- 📢 **Discussion Forum**: Join community discussions at [Forum](link.to/community)
