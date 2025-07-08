"""Configuration management for Calendar Bot CLI.

This module handles configuration file operations, validation,
backup and restore functionality, and integration with the setup wizard.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple


def check_configuration() -> Tuple[bool, Optional[Path]]:
    """Check if Calendar Bot is configured and return config file path.

    Returns:
        Tuple of (is_configured, config_file_path)
    """
    try:
        # Check for config file in project directory first
        project_config = Path(__file__).parent.parent.parent / "config" / "config.yaml"
        if project_config.exists():
            return True, project_config

        # Check user config directory
        user_config_dir = Path.home() / ".config" / "calendarbot"
        user_config = user_config_dir / "config.yaml"
        if user_config.exists():
            return True, user_config

        # Check if essential settings are available via environment variables
        try:
            from config.settings import CalendarBotSettings

            settings = CalendarBotSettings()
            if settings.ics_url:
                return True, None  # Configured via environment variables
        except ImportError:
            # Settings module not available, continue to return not configured
            pass

        return False, None

    except Exception:
        # Handle any general exceptions gracefully
        return False, None


def show_setup_guidance() -> None:
    """Display setup guidance for first-time users."""
    print("\n" + "=" * 70)
    print("🚀 Welcome to Calendar Bot!")
    print("=" * 70)
    print("It looks like this is your first time running Calendar Bot.")
    print("Let's get you set up!\n")

    print("📋 Quick Setup Options:")
    print("1. Run 'calendarbot --setup' for interactive configuration wizard")
    print("   ✨ NEW: Includes service templates, testing, and authentication setup")
    print("2. Copy config/config.yaml.example to config/config.yaml")
    print("3. Set environment variable: CALENDARBOT_ICS_URL=your-calendar-url")
    print("\n🔧 Interactive Wizard Features:")
    print("- Templates for Outlook, Google Calendar, iCloud, and CalDAV")
    print("- Automatic URL validation and connection testing")
    print("- Authentication setup (basic auth, bearer tokens)")
    print("- Advanced settings configuration")
    print("\n📖 Documentation:")
    print("- Configuration guide: See config/config.yaml.example")
    print("- Full setup instructions: See docs/INSTALL.md")
    print("- Usage examples: Run 'calendarbot --help'")
    print("\n🔧 Required Configuration:")
    print("- ICS calendar URL (your Outlook/Google/iCloud calendar link)")
    print("- Optional: Authentication credentials for private calendars")
    print("=" * 70)


def backup_configuration() -> int:
    """Backup current configuration to timestamped file.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        import shutil

        # Find current config file
        is_configured, config_path = check_configuration()
        if not is_configured or not config_path:
            print("❌ No configuration file found to backup")
            return 1

        # Create backup directory
        backup_dir = Path.home() / ".config" / "calendarbot" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"config_backup_{timestamp}.yaml"
        backup_path = backup_dir / backup_filename

        # Copy config file to backup
        shutil.copy2(config_path, backup_path)

        print(f"✅ Configuration backed up to: {backup_path}")
        return 0

    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return 1


def restore_configuration(backup_file: str) -> int:
    """Restore configuration from backup file.

    Args:
        backup_file: Path to backup file to restore

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        import shutil

        backup_path = Path(backup_file)
        if not backup_path.exists():
            print(f"❌ Backup file not found: {backup_file}")
            return 1

        # Determine target config location
        target_config = Path.home() / ".config" / "calendarbot" / "config.yaml"
        target_config.parent.mkdir(parents=True, exist_ok=True)

        # Backup current config if it exists
        if target_config.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_backup = (
                target_config.parent / "backups" / f"config_before_restore_{timestamp}.yaml"
            )
            current_backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target_config, current_backup)
            print(f"📦 Current config backed up to: {current_backup}")

        # Restore from backup
        shutil.copy2(backup_path, target_config)

        print(f"✅ Configuration restored from: {backup_file}")
        print(f"📁 Active config location: {target_config}")
        return 0

    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return 1


def list_backups() -> int:
    """List available configuration backups.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        backup_dir = Path.home() / ".config" / "calendarbot" / "backups"

        if not backup_dir.exists():
            print("📂 No backup directory found")
            return 0

        backup_files = list(backup_dir.glob("config_*.yaml"))

        if not backup_files:
            print("📂 No configuration backups found")
            return 0

        print(f"📂 Configuration backups in {backup_dir}:")
        print()

        # Sort by modification time (newest first)
        backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        for backup_file in backup_files:
            stat = backup_file.stat()
            size_kb = stat.st_size / 1024
            mtime = datetime.fromtimestamp(stat.st_mtime)

            print(f"  📄 {backup_file.name}")
            print(f"     Size: {size_kb:.1f} KB")
            print(f"     Date: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"     Path: {backup_file}")
            print()

        print(f"💡 To restore: calendarbot --restore {backup_files[0]}")
        return 0

    except Exception as e:
        print(f"❌ Failed to list backups: {e}")
        return 1


def apply_rpi_overrides(settings: Any, args: Any) -> Any:
    """Apply RPI-specific command-line overrides to settings.

    Args:
        settings: Current settings object
        args: Parsed command line arguments

    Returns:
        Updated settings object
    """
    logger = logging.getLogger("calendarbot.cli.config")

    logger.debug(f"Applying RPI overrides with args.rpi={getattr(args, 'rpi', False)}")

    if hasattr(args, "rpi") and args.rpi:
        logger.info(f"RPI mode enabled, auto_theme={settings.rpi_auto_theme}")

        # Enable RPI mode
        settings.rpi_enabled = True
        settings.display_type = "rpi"
        logger.debug(f"Set display_type={settings.display_type}")

        # Apply RPI-specific settings
        if hasattr(args, "rpi_width") and args.rpi_width:
            settings.rpi_display_width = args.rpi_width
        if hasattr(args, "rpi_height") and args.rpi_height:
            settings.rpi_display_height = args.rpi_height
        if hasattr(args, "rpi_refresh_mode") and args.rpi_refresh_mode:
            settings.rpi_refresh_mode = args.rpi_refresh_mode

        # Auto-optimize web theme for RPI
        current_theme = getattr(settings, "web_theme", "NOT_SET")
        if settings.rpi_auto_theme:
            settings.web_theme = "eink-rpi"
            logger.info(f"Applied RPI theme override: {current_theme} -> {settings.web_theme}")
        else:
            logger.debug(f"RPI auto theme disabled, keeping web_theme={current_theme}")
    else:
        logger.debug("RPI mode not enabled, keeping original theme")

    return settings


__all__ = [
    "check_configuration",
    "show_setup_guidance",
    "backup_configuration",
    "restore_configuration",
    "list_backups",
    "apply_rpi_overrides",
]
