"""Configuration management for Calendar Bot CLI.

This module handles configuration file operations, validation,
backup and restore functionality, and integration with the setup wizard.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def check_configuration() -> "tuple[bool, Optional[Path]]":
    """Check if Calendar Bot is configured and return config file path.

    Returns:
        Tuple of (is_configured, config_file_path)
    """
    try:
        # Check for config file in project directory first
        project_config = Path(__file__).parent.parent / "config" / "config.yaml"
        if project_config.exists():
            return True, project_config

        # Check user config directory
        user_config_dir = Path.home() / ".config" / "calendarbot"
        user_config = user_config_dir / "config.yaml"
        if user_config.exists():
            return True, user_config

        # Check if essential settings are available via environment variables
        try:
            from calendarbot.config.settings import CalendarBotSettings  # noqa: PLC0415

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
    print("2. Copy calendarbot/config/config.yaml.example to calendarbot/config/config.yaml")
    print("3. Set environment variable: CALENDARBOT_ICS_URL=your-calendar-url")
    print("\n🔧 Interactive Wizard Features:")
    print("- Templates for Outlook, Google Calendar, iCloud, and CalDAV")
    print("- Automatic URL validation and connection testing")
    print("- Authentication setup (basic auth, bearer tokens)")
    print("- Advanced settings configuration")
    print("\n📖 Documentation:")
    print("- Configuration guide: See calendarbot/config/config.yaml.example")
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
        import shutil  # noqa: PLC0415

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
        import shutil  # noqa: PLC0415

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
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

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


def _apply_renderer_and_layout(settings: Any, args: Any, logger: logging.Logger) -> None:
    if getattr(args, "renderer", None):
        settings.display_type = args.renderer
        logger.debug(f"Set display_type={settings.display_type} from --renderer")
    if getattr(args, "layout", None):
        settings.web_layout = args.layout
        logger.debug(f"Set web_layout={settings.web_layout} from --layout")
    if getattr(args, "display_type", None):
        settings.web_layout = args.display_type
        logger.debug(
            f"Set web_layout={settings.web_layout} from --display-type (backward compatibility)"
        )


def _apply_rpi_mode(settings: Any, args: Any, logger: logging.Logger) -> None:
    if getattr(args, "rpi", False):
        logger.info(f"RPI mode enabled, auto_layout={getattr(settings, 'rpi_auto_layout', True)}")
        settings.rpi_enabled = True
        settings.display_type = "compact"
        logger.debug(f"Set display_type={settings.display_type} for RPI mode")
        if getattr(args, "rpi_width", None):
            settings.rpi_display_width = args.rpi_width
        if getattr(args, "rpi_height", None):
            settings.rpi_display_height = args.rpi_height
        if getattr(args, "rpi_refresh_mode", None):
            settings.rpi_refresh_mode = args.rpi_refresh_mode
        if getattr(settings, "rpi_auto_layout", True) and not getattr(args, "layout", None):
            current_layout = getattr(settings, "web_layout", "NOT_SET")
            settings.web_layout = "3x4"
            if hasattr(settings, "layout_name"):
                settings.layout_name = "3x4"
            logger.info(f"Applied RPI layout override: {current_layout} -> {settings.web_layout}")


def _apply_compact_mode(settings: Any, args: Any, logger: logging.Logger) -> None:
    if getattr(args, "compact", False):
        logger.info("Compact mode enabled")
        settings.display_type = "compact"
        logger.debug(f"Set display_type={settings.display_type} for compact mode")
        if getattr(args, "compact_width", None):
            settings.compact_display_width = args.compact_width
        if getattr(args, "compact_height", None):
            settings.compact_display_height = args.compact_height
        if not getattr(args, "layout", None):
            current_layout = getattr(settings, "web_layout", "NOT_SET")
            settings.web_layout = "3x4"
            logger.info(
                f"Applied compact layout override: {current_layout} -> {settings.web_layout}"
            )


def _apply_epaper_mode(settings: Any, args: Any, logger: logging.Logger) -> None:
    if getattr(args, "epaper", False):
        logger.info("E-Paper mode enabled")
        settings.epaper.enabled = True
    else:
        # Explicitly set epaper to disabled when not in epaper mode
        logger.info("E-Paper mode disabled")
        settings.epaper.enabled = False
        settings.display_type = "eink-whats-next"
        logger.debug(f"Set display_type={settings.display_type} for epaper mode")
        epaper_fields = [
            ("epaper_model", "display_model"),
            ("epaper_width", "width"),
            ("epaper_height", "height"),
            ("epaper_rotation", "rotation"),
            ("epaper_refresh_interval", "refresh_interval"),
            ("epaper_partial_refresh", "partial_refresh"),
            ("epaper_contrast", "contrast_level"),
            ("epaper_dither", "dither_mode"),
            ("epaper_png_fallback", "png_fallback_enabled"),
            ("epaper_png_output", "png_output_path"),
            ("epaper_force", "force_epaper"),
        ]
        for arg_name, attr_name in epaper_fields:
            value = getattr(args, arg_name, None)
            if value is not None:
                setattr(settings.epaper, attr_name, value)
        # Also set legacy fields for backward compatibility
        legacy_map = {
            "epaper_force": "force_epaper",
            "epaper_model": "epaper_display_model",
            "epaper_rotation": "epaper_rotation",
            "epaper_refresh_interval": "epaper_refresh_interval",
            "epaper_partial_refresh": "epaper_partial_refresh",
            "epaper_contrast": "epaper_contrast_level",
            "epaper_dither": "epaper_dither_mode",
        }
        for arg_name, legacy_attr in legacy_map.items():
            value = getattr(args, arg_name, None)
            if value is not None:
                setattr(settings, legacy_attr, value)
        logger.info(
            f"E-Paper configuration applied: model={getattr(settings.epaper, 'display_model', None)}, "
            f"dimensions={getattr(settings.epaper, 'width', None)}x{getattr(settings.epaper, 'height', None)}, "
            f"rotation={getattr(settings.epaper, 'rotation', None)}°"
        )


def apply_cli_overrides(settings: Any, args: Any) -> Any:
    """Apply command-line overrides to settings with proper layout/renderer separation.

    Args:
        settings: Current settings object
        args: Parsed command line arguments

    Returns:
        Updated settings object
    """
    logger = logging.getLogger("calendarbot.cli.config")
    _apply_renderer_and_layout(settings, args, logger)
    _apply_rpi_mode(settings, args, logger)
    _apply_compact_mode(settings, args, logger)
    _apply_epaper_mode(settings, args, logger)
    return settings


__all__ = [
    "apply_cli_overrides",
    "backup_configuration",
    "check_configuration",
    "list_backups",
    "restore_configuration",
    "show_setup_guidance",
]
