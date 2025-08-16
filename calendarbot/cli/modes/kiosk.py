"""Kiosk mode handler for Calendar Bot CLI.

This module provides kiosk mode functionality for Calendar Bot,
including kiosk start, status checking, stop, restart, and setup operations.
The kiosk mode orchestrates browser management, web server coordination,
and system health monitoring optimized for Raspberry Pi Zero 2W deployment.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from calendarbot.config.settings import settings
from calendarbot.kiosk.manager import KioskError, KioskManager, KioskStatus
from calendarbot.settings.kiosk_models import KioskSettings
from calendarbot.utils.logging import (
    apply_command_line_overrides,
    setup_enhanced_logging,
)

from ..config import apply_cli_overrides

logger = logging.getLogger(__name__)


class KioskCLIError(Exception):
    """Exception raised for kiosk CLI-related errors."""


def _configure_kiosk_settings(args: Any, base_settings: Any) -> tuple[Any, KioskSettings]:
    """Configure kiosk mode settings from command line arguments.

    Args:
        args: Parsed command line arguments
        base_settings: Base settings object to configure

    Returns:
        Tuple of (updated_settings, kiosk_settings)

    Raises:
        KioskCLIError: If kiosk configuration is invalid
    """
    try:
        # Apply command-line logging overrides with priority system
        updated_settings = apply_command_line_overrides(base_settings, args)

        # Apply CLI-specific overrides
        updated_settings = apply_cli_overrides(updated_settings, args)

        # Create kiosk settings from arguments
        kiosk_config = {
            "enabled": True,
            "browser": {
                "memory_limit_mb": getattr(args, "kiosk_memory_limit", 80),
                "startup_timeout": getattr(args, "kiosk_startup_timeout", 30),
                "health_check_interval": getattr(args, "kiosk_health_interval", 60),
                "max_restart_attempts": getattr(args, "kiosk_max_restarts", 3),
                "enable_gpu": getattr(args, "kiosk_enable_gpu", False),
                "disable_extensions": getattr(args, "kiosk_disable_extensions", True),
                "disable_plugins": getattr(args, "kiosk_disable_plugins", True),
            },
            "display": {
                "width": getattr(args, "kiosk_width", 480),
                "height": getattr(args, "kiosk_height", 800),
                "orientation": getattr(args, "kiosk_orientation", "portrait"),
                "scale_factor": getattr(args, "kiosk_scale", 1.0),
                "fullscreen_mode": getattr(args, "kiosk_fullscreen", True),
                "hide_cursor": getattr(args, "kiosk_hide_cursor", True),
                "prevent_zoom": getattr(args, "kiosk_prevent_zoom", True),
            },
            "target_layout": getattr(args, "display_type", "whats-next-view"),
            "auto_start": getattr(args, "kiosk_auto_start", False),
            "startup_delay": getattr(args, "kiosk_startup_delay", 5.0),
        }

        kiosk_settings = KioskSettings(**kiosk_config)
        return updated_settings, kiosk_settings

    except Exception as e:
        raise KioskCLIError(f"Failed to configure kiosk settings: {e}") from e


def _setup_kiosk_logging(updated_settings: Any, kiosk_mode: bool = True) -> logging.Logger:
    """Set up logging for kiosk mode operations.

    Args:
        updated_settings: Configured settings object
        kiosk_mode: Whether this is for kiosk mode (affects console logging)

    Returns:
        Logger instance configured for kiosk operations
    """
    if kiosk_mode and hasattr(updated_settings, "logging"):
        # Reduce console logging for kiosk mode but keep some output
        if not updated_settings.logging.console_level:
            updated_settings.logging.console_level = "WARNING"

        # Ensure file logging is enabled for kiosk mode
        updated_settings.logging.file_enabled = True
        if not updated_settings.logging.file_directory:
            log_dir = Path.home() / ".calendarbot" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            updated_settings.logging.file_directory = str(log_dir)

        # Set kiosk-specific prefix
        updated_settings.logging.file_prefix = "kiosk"

    # Set up enhanced logging
    logger_instance = setup_enhanced_logging(updated_settings, interactive_mode=False)
    if kiosk_mode:
        logger_instance.info("Kiosk mode logging initialized")
    return logger_instance


def _format_kiosk_status(status: KioskStatus, color_output: bool = True) -> str:
    """Format kiosk status for console display with optional color coding.

    Args:
        status: KioskStatus object to format
        color_output: Whether to include ANSI color codes

    Returns:
        Formatted status string
    """
    if not color_output:
        # Plain text formatting
        lines = [
            f"Kiosk Status: {'Running' if status.is_running else 'Stopped'}",
            f"Started: {status.start_time.strftime('%Y-%m-%d %H:%M:%S') if status.start_time else 'N/A'}",
            f"Uptime: {str(status.uptime).split('.')[0] if status.uptime else 'N/A'}",
            f"Browser State: {status.browser_status.state.value if status.browser_status else 'N/A'}",
            f"System Memory: {status.memory_usage_mb}MB",
            f"System CPU: {status.cpu_usage_percent:.1f}%",
            f"Restart Count: {status.restart_count}",
        ]

        if status.browser_status:
            lines.extend(
                [
                    f"Browser PID: {status.browser_status.pid or 'N/A'}",
                    f"Browser Memory: {status.browser_status.memory_usage_mb or 0}MB",
                    f"Browser CPU: {status.browser_status.cpu_usage_percent or 0:.1f}%",
                ]
            )

        if status.last_error:
            lines.append(f"Last Error: {status.last_error}")
            if status.error_time:
                lines.append(f"Error Time: {status.error_time.strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(lines)

    # Color-coded formatting
    def colorize(text: str, color: str) -> str:
        colors = {
            "green": "\033[92m",
            "red": "\033[91m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "bold": "\033[1m",
            "reset": "\033[0m",
        }
        return f"{colors.get(color, '')}{text}{colors['reset']}"

    # Status indicator with color
    status_color = "green" if status.is_running else "red"
    status_text = (
        colorize("●", status_color)
        + f" Kiosk Status: {colorize('Running' if status.is_running else 'Stopped', status_color)}"
    )

    lines = [
        colorize("CalendarBot Kiosk Status", "bold"),
        "=" * 30,
        status_text,
        f"Started: {status.start_time.strftime('%Y-%m-%d %H:%M:%S') if status.start_time else 'N/A'}",
        f"Uptime: {str(status.uptime).split('.')[0] if status.uptime else 'N/A'}",
        f"System Memory: {status.memory_usage_mb}MB",
        f"System CPU: {status.cpu_usage_percent:.1f}%",
        f"Restart Count: {status.restart_count}",
    ]

    # Browser status with color coding
    if status.browser_status:
        browser_color = "green" if status.browser_status.state.value == "RUNNING" else "red"
        lines.extend(
            [
                f"Browser State: {colorize(status.browser_status.state.value, browser_color)}",
                f"Browser PID: {status.browser_status.pid or 'N/A'}",
                f"Browser Memory: {status.browser_status.memory_usage_mb or 0}MB",
                f"Browser CPU: {status.browser_status.cpu_usage_percent or 0:.1f}%",
            ]
        )
    else:
        lines.append(f"Browser State: {colorize('N/A', 'yellow')}")

    # Daemon status (as proxy for web server)
    daemon_color = "green" if status.daemon_status else "red"
    lines.append(
        f"Web Server: {colorize('Running' if status.daemon_status else 'Stopped', daemon_color)}"
    )

    # Error message
    if status.last_error:
        lines.extend(["", colorize("Last Error:", "red"), colorize(status.last_error, "red")])
        if status.error_time:
            lines.append(f"Error Time: {status.error_time.strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)


async def _start_kiosk_process(args: Any) -> int:
    """Start CalendarBot in kiosk mode.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Configure settings
        updated_settings, kiosk_settings = _configure_kiosk_settings(args, settings)

        # Set up logging
        logger_instance = _setup_kiosk_logging(updated_settings, kiosk_mode=True)

        # Create kiosk manager
        kiosk_manager = KioskManager(updated_settings, kiosk_settings)

        # Check if kiosk is already running
        status = kiosk_manager.get_kiosk_status()
        if status.is_running:
            print("CalendarBot kiosk is already running")
            print("Use 'calendarbot --kiosk-status' to check status")
            print("Use 'calendarbot --kiosk-stop' to stop kiosk mode")
            return 1

        logger_instance.info("Starting CalendarBot kiosk mode")
        logger_instance.info(
            f"Display: {kiosk_settings.display.width}x{kiosk_settings.display.height}"
        )
        logger_instance.info(f"Layout: {kiosk_settings.target_layout}")
        logger_instance.info(f"Port: {args.port}")

        print("Starting CalendarBot kiosk mode...")
        print(f"Display: {kiosk_settings.display.width}x{kiosk_settings.display.height}")
        print(f"Layout: {kiosk_settings.target_layout}")
        print(f"Browser memory limit: {kiosk_settings.browser.memory_limit_mb}MB")

        # Start kiosk mode
        success = await kiosk_manager.start_kiosk()

        if success:
            print("✓ CalendarBot kiosk started successfully")
            logger_instance.info("CalendarBot kiosk started successfully")

            # Show status
            status = kiosk_manager.get_kiosk_status()
            print(
                "\n"
                + _format_kiosk_status(
                    status, color_output=not getattr(args, "no_log_colors", False)
                )
            )

            return 0
        print("✗ Failed to start CalendarBot kiosk")
        logger_instance.error("Failed to start CalendarBot kiosk")
        return 1

    except KioskCLIError as e:
        print(f"Configuration error: {e}")
        logger.exception("Kiosk configuration error")
        return 1
    except KioskError as e:
        print(f"Kiosk error: {e}")
        logger.exception("Kiosk operation error")
        return 1
    except Exception as e:
        print(f"Unexpected error starting kiosk: {e}")
        logger.exception("Unexpected error starting kiosk mode")
        return 1


def _check_kiosk_status(args: Any) -> int:
    """Check and display kiosk status.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Configure minimal settings for status check
        updated_settings, kiosk_settings = _configure_kiosk_settings(args, settings)

        # Create kiosk manager
        kiosk_manager = KioskManager(updated_settings, kiosk_settings)

        # Get status
        status = kiosk_manager.get_kiosk_status()

        if not status.is_running:
            print("CalendarBot kiosk is not running")
            return 1

        # Display formatted status
        color_output = not getattr(args, "no_log_colors", False)
        print(_format_kiosk_status(status, color_output=color_output))
        return 0

    except Exception as e:
        print(f"Error checking kiosk status: {e}")
        logger.exception("Error checking kiosk status")
        return 1


async def _stop_kiosk_process(args: Any) -> int:
    """Stop running kiosk process.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Configure minimal settings for stop operation
        updated_settings, kiosk_settings = _configure_kiosk_settings(args, settings)

        # Set up logging for stop operation
        logger_instance = _setup_kiosk_logging(updated_settings, kiosk_mode=False)

        # Create kiosk manager
        kiosk_manager = KioskManager(updated_settings, kiosk_settings)

        # Check if kiosk is running
        status = kiosk_manager.get_kiosk_status()
        if not status.is_running:
            print("CalendarBot kiosk is not running")
            return 1

        print("Stopping CalendarBot kiosk...")
        logger_instance.info("Stopping CalendarBot kiosk mode")

        # Stop kiosk mode
        success = await kiosk_manager.stop_kiosk()

        if success:
            print("✓ CalendarBot kiosk stopped successfully")
            logger_instance.info("CalendarBot kiosk stopped successfully")
            return 0
        print("✗ Failed to stop CalendarBot kiosk")
        logger_instance.error("Failed to stop CalendarBot kiosk")
        return 1

    except Exception as e:
        print(f"Error stopping kiosk: {e}")
        logger.exception("Error stopping kiosk mode")
        return 1


async def _restart_kiosk_process(args: Any) -> int:
    """Restart kiosk process with recovery.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        print("Restarting CalendarBot kiosk...")

        # First, stop the kiosk if running
        await _stop_kiosk_process(args)

        # Wait a moment for cleanup
        await asyncio.sleep(2)

        # Start the kiosk again
        start_result = await _start_kiosk_process(args)

        if start_result == 0:
            print("✓ CalendarBot kiosk restarted successfully")
            return 0
        print("✗ Failed to restart CalendarBot kiosk")
        return 1

    except Exception as e:
        print(f"Error restarting kiosk: {e}")
        logger.exception("Error restarting kiosk mode")
        return 1


async def _run_kiosk_setup_wizard(args: Any) -> int:  # noqa: PLR0915
    """Run interactive kiosk setup wizard for Pi Zero 2W deployment.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        print("CalendarBot Kiosk Setup Wizard")
        print("=" * 35)
        print()
        print("This wizard will help you configure CalendarBot for kiosk mode")
        print("optimized for Raspberry Pi Zero 2W deployment.")
        print()

        # Gather configuration
        config = {}

        # Display settings
        print("Display Configuration:")
        print("---------------------")

        width = input("Display width in pixels [480]: ").strip() or "480"
        height = input("Display height in pixels [800]: ").strip() or "800"
        orientation = (
            input("Display orientation (portrait/landscape) [portrait]: ").strip() or "portrait"
        )

        try:
            config["display"] = {
                "width": int(width),
                "height": int(height),
                "orientation": orientation.lower(),
                "fullscreen_mode": True,
                "hide_cursor": True,
                "prevent_zoom": True,
            }
        except ValueError:
            print("Invalid display dimensions. Using defaults.")
            config["display"] = {
                "width": 480,
                "height": 800,
                "orientation": "portrait",
                "fullscreen_mode": True,
                "hide_cursor": True,
                "prevent_zoom": True,
            }

        print()

        # Browser settings
        print("Browser Configuration:")
        print("----------------------")

        memory_limit = input("Browser memory limit in MB [80]: ").strip() or "80"
        enable_gpu = input("Enable GPU acceleration (y/n) [n]: ").strip().lower() in ["y", "yes"]

        try:
            config["browser"] = {
                "memory_limit_mb": int(memory_limit),
                "startup_timeout": 30,
                "health_check_interval": 60,
                "max_restart_attempts": 3,
                "enable_gpu": enable_gpu,
                "disable_extensions": True,
                "disable_plugins": True,
            }
        except ValueError:
            print("Invalid memory limit. Using default (80MB).")
            config["browser"] = {
                "memory_limit_mb": 80,
                "startup_timeout": 30,
                "health_check_interval": 60,
                "max_restart_attempts": 3,
                "enable_gpu": False,
                "disable_extensions": True,
                "disable_plugins": True,
            }

        print()

        # Layout and network settings
        print("Application Configuration:")
        print("-------------------------")

        layout = (
            input("Calendar layout (whats-next-view/4x8/3x4) [whats-next-view]: ").strip()
            or "whats-next-view"
        )
        port = input("Web server port [8080]: ").strip() or "8080"
        auto_start = input("Auto-start on boot (y/n) [y]: ").strip().lower() in ["y", "yes", ""]

        try:
            config["layout"] = layout
            config["port"] = int(port)
            config["auto_start"] = auto_start
            config["startup_delay"] = 5.0
        except ValueError:
            print("Invalid port. Using default (8080).")
            config["layout"] = layout
            config["port"] = 8080
            config["auto_start"] = auto_start
            config["startup_delay"] = 5.0

        print()

        # Configuration summary
        print("Configuration Summary:")
        print("======================")
        print(
            f"Display: {config['display']['width']}x{config['display']['height']} ({config['display']['orientation']})"
        )
        print(f"Browser Memory: {config['browser']['memory_limit_mb']}MB")
        print(f"GPU Acceleration: {'Enabled' if config['browser']['enable_gpu'] else 'Disabled'}")
        print(f"Layout: {config['layout']}")
        print(f"Port: {config['port']}")
        print(f"Auto-start: {'Enabled' if config['auto_start'] else 'Disabled'}")
        print()

        # Confirmation
        confirm = input("Save this configuration and start kiosk mode? (y/n) [y]: ").strip().lower()
        if confirm not in ["y", "yes", ""]:
            print("Setup cancelled.")
            return 1

        # Save configuration to file
        config_dir = Path.home() / ".calendarbot"
        config_dir.mkdir(exist_ok=True)

        config_file = config_dir / "kiosk_config.yaml"

        # Simple YAML-like format for configuration
        config_content = f"""# CalendarBot Kiosk Configuration
# Generated by setup wizard

kiosk:
  enabled: true
  layout: {config["layout"]}
  auto_start: {str(config["auto_start"]).lower()}
  startup_delay: {config["startup_delay"]}

  display:
    width: {config["display"]["width"]}
    height: {config["display"]["height"]}
    orientation: {config["display"]["orientation"]}
    fullscreen_mode: true
    hide_cursor: true
    prevent_zoom: true

  browser:
    memory_limit_mb: {config["browser"]["memory_limit_mb"]}
    startup_timeout: {config["browser"]["startup_timeout"]}
    health_check_interval: {config["browser"]["health_check_interval"]}
    max_restart_attempts: {config["browser"]["max_restart_attempts"]}
    enable_gpu: {str(config["browser"]["enable_gpu"]).lower()}
    disable_extensions: true
    disable_plugins: true

web:
  port: {config["port"]}
"""

        try:
            with Path(config_file).open("w") as f:
                f.write(config_content)
            print(f"✓ Configuration saved to {config_file}")
        except Exception as e:
            print(f"Warning: Could not save configuration file: {e}")

        print()
        print("Setup complete! Starting CalendarBot kiosk mode...")

        # Update args with configuration
        args.port = config["port"]
        args.display_type = config["layout"]
        args.kiosk_width = config["display"]["width"]
        args.kiosk_height = config["display"]["height"]
        args.kiosk_orientation = config["display"]["orientation"]
        args.kiosk_memory_limit = config["browser"]["memory_limit_mb"]
        args.kiosk_enable_gpu = config["browser"]["enable_gpu"]
        args.kiosk_fullscreen = config["display"]["fullscreen_mode"]
        args.kiosk_hide_cursor = config["display"]["hide_cursor"]
        args.kiosk_prevent_zoom = config["display"]["prevent_zoom"]

        # Start kiosk mode
        return await _start_kiosk_process(args)

    except KeyboardInterrupt:
        print("\nSetup cancelled by user.")
        return 1
    except Exception as e:
        print(f"Setup error: {e}")
        logger.exception("Error during kiosk setup wizard")
        return 1


async def run_kiosk_mode(args: Any) -> int:
    """Run Calendar Bot in kiosk mode based on CLI arguments.

    This function handles the kiosk operations:
    - args.kiosk: Start kiosk mode
    - args.kiosk_status: Check kiosk status
    - args.kiosk_stop: Stop running kiosk
    - args.kiosk_restart: Restart kiosk with recovery
    - args.kiosk_setup: Run interactive setup wizard

    Args:
        args: Parsed command line arguments with kiosk flags

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Validate arguments
    kiosk_operations = [
        getattr(args, "kiosk", False),
        getattr(args, "kiosk_status", False),
        getattr(args, "kiosk_stop", False),
        getattr(args, "kiosk_restart", False),
        getattr(args, "kiosk_setup", False),
    ]

    if not any(kiosk_operations):
        print("Error: No valid kiosk operation specified")
        return 1

    # Handle kiosk operations
    if getattr(args, "kiosk_setup", False):
        # Setup wizard operation
        return await _run_kiosk_setup_wizard(args)

    if getattr(args, "kiosk", False):
        # Start kiosk operation
        return await _start_kiosk_process(args)

    if getattr(args, "kiosk_status", False):
        # Status check operation (synchronous)
        return _check_kiosk_status(args)

    if getattr(args, "kiosk_stop", False):
        # Stop kiosk operation
        return await _stop_kiosk_process(args)

    if getattr(args, "kiosk_restart", False):
        # Restart kiosk operation
        return await _restart_kiosk_process(args)

    print("Error: No valid kiosk operation specified")
    return 1


__all__ = [
    "KioskCLIError",
    "run_kiosk_mode",
]
