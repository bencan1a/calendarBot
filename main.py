#!/usr/bin/env python3
"""Entry point for Calendar Bot application with test mode support."""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_configuration() -> tuple[bool, Optional[Path]]:
    """Check if Calendar Bot is configured and return config file path.
    
    Returns:
        Tuple of (is_configured, config_file_path)
    """
    from config.settings import CalendarBotSettings
    
    # Check for config file in project directory first
    project_config = Path(__file__).parent / "config" / "config.yaml"
    if project_config.exists():
        return True, project_config
    
    # Check user config directory
    user_config_dir = Path.home() / ".config" / "calendarbot"
    user_config = user_config_dir / "config.yaml"
    if user_config.exists():
        return True, user_config
    
    # Check if essential settings are available via environment variables
    settings = CalendarBotSettings()
    if settings.ics_url:
        return True, None  # Configured via environment variables
    
    return False, None


def show_setup_guidance():
    """Display setup guidance for first-time users."""
    print("\n" + "="*70)
    print("🚀 Welcome to Calendar Bot!")
    print("="*70)
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
    print("- Full setup instructions: See INSTALL.md")
    print("- Usage examples: Run 'calendarbot --help'")
    print("\n🔧 Required Configuration:")
    print("- ICS calendar URL (your Outlook/Google/iCloud calendar link)")
    print("- Optional: Authentication credentials for private calendars")
    print("="*70)


def backup_configuration() -> int:
    """Backup current configuration to timestamped file.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        import shutil
        from datetime import datetime
        
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
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_backup = target_config.parent / "backups" / f"config_before_restore_{timestamp}.yaml"
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


def run_setup_wizard() -> int:
    """Run the configuration setup wizard.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Import the comprehensive setup wizard
        from calendarbot.setup_wizard import run_setup_wizard as run_async_wizard, run_simple_wizard
        
        # Check if user wants full wizard or simple wizard
        print("\n" + "="*60)
        print("📅 Calendar Bot Configuration Wizard")
        print("="*60)
        print("Choose setup mode:")
        print("1. Full wizard (recommended) - Interactive setup with testing and templates")
        print("2. Quick setup - Basic configuration")
        print()
        
        choice = input("Enter choice (1 or 2) [1]: ").strip()
        
        if choice == "2":
            # Run simple wizard
            print("Running quick setup...")
            success = run_simple_wizard()
            return 0 if success else 1
        else:
            # Run full async wizard
            print("Running full interactive wizard...")
            success = asyncio.run(run_async_wizard())
            return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return 1


def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format.
    
    Args:
        date_str: Date string to parse
        
    Returns:
        Parsed datetime object
        
    Raises:
        argparse.ArgumentTypeError: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def parse_components(components_str: str) -> List[str]:
    """Parse comma-separated components string.
    
    Args:
        components_str: Comma-separated component names
        
    Returns:
        List of component names
        
    Raises:
        argparse.ArgumentTypeError: If invalid component specified
    """
    valid_components = {'auth', 'api', 'cache', 'display'}
    components = [c.strip().lower() for c in components_str.split(',')]
    
    invalid = set(components) - valid_components
    if invalid:
        raise argparse.ArgumentTypeError(
            f"Invalid components: {', '.join(invalid)}. "
            f"Valid options: {', '.join(sorted(valid_components))}"
        )
    
    return components


def apply_rpi_overrides(settings, args):
    """Apply RPI-specific command-line overrides to settings.
    
    Args:
        settings: Current settings object
        args: Parsed command line arguments
        
    Returns:
        Updated settings object
    """
    print(f"DEBUG: apply_rpi_overrides called with args.rpi={getattr(args, 'rpi', False)}")
    
    if hasattr(args, 'rpi') and args.rpi:
        print(f"DEBUG: RPI mode enabled, settings.rpi_auto_theme={settings.rpi_auto_theme}")
        
        # Enable RPI mode
        settings.rpi_enabled = True
        settings.display_type = "rpi"
        print(f"DEBUG: Set display_type = {settings.display_type}")
        
        # Apply RPI-specific settings
        if hasattr(args, 'rpi_width') and args.rpi_width:
            settings.rpi_display_width = args.rpi_width
        if hasattr(args, 'rpi_height') and args.rpi_height:
            settings.rpi_display_height = args.rpi_height
        if hasattr(args, 'rpi_refresh_mode') and args.rpi_refresh_mode:
            settings.rpi_refresh_mode = args.rpi_refresh_mode
        
        # Auto-optimize web theme for RPI
        print(f"DEBUG: Before theme override - web_theme={getattr(settings, 'web_theme', 'NOT_SET')}")
        if settings.rpi_auto_theme:
            settings.web_theme = "eink-rpi"
            print(f"DEBUG: Applied RPI theme override - web_theme={settings.web_theme}")
        else:
            print(f"DEBUG: RPI auto theme disabled, keeping web_theme={getattr(settings, 'web_theme', 'NOT_SET')}")
    else:
        print(f"DEBUG: RPI mode not enabled, keeping original theme")
    
    return settings


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Calendar Bot - ICS calendar display with interactive navigation and web interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run in interactive mode (default)
  %(prog)s --setup                   # Run first-time configuration wizard
  %(prog)s --backup                  # Backup current configuration
  %(prog)s --list-backups            # List available configuration backups
  %(prog)s --restore backup_file.yaml # Restore configuration from backup
  %(prog)s --test-mode               # Run validation tests
  %(prog)s --test-mode --verbose     # Run tests with verbose output
  %(prog)s --test-mode --date 2024-01-15 --components auth,api
  %(prog)s --test-mode --output-format json > results.json
  %(prog)s --interactive             # Run interactive console mode (explicit)
  %(prog)s --web                     # Run web server mode on localhost:8080
  %(prog)s --web --port 3000 --auto-open  # Run web server on port 3000 and open browser
  %(prog)s --rpi --web               # Run in RPI e-ink mode with web interface
        """
    )
    
    # Setup and configuration arguments
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run first-time configuration wizard (creates config.yaml)"
    )
    
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Backup current configuration to timestamped file"
    )
    
    parser.add_argument(
        "--restore",
        metavar="BACKUP_FILE",
        help="Restore configuration from backup file"
    )
    
    parser.add_argument(
        "--list-backups",
        action="store_true",
        help="List available configuration backups"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s 1.0.0",
        help="Show version information"
    )
    
    # Test mode arguments
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run validation tests instead of daemon mode"
    )
    
    parser.add_argument(
        "--date",
        type=parse_date,
        default=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
        help="Date for testing in YYYY-MM-DD format (default: today)"
    )
    
    parser.add_argument(
        "--end-date",
        type=parse_date,
        help="End date for range testing in YYYY-MM-DD format (default: same as --date)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging and detailed output"
    )
    
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Skip using cached data in tests"
    )
    
    parser.add_argument(
        "--components",
        type=parse_components,
        default=['auth', 'api', 'cache', 'display'],
        help="Comma-separated components to test: auth,api,cache,display (default: all)"
    )
    
    parser.add_argument(
        "--output-format",
        choices=['console', 'json'],
        default='console',
        help="Output format for test results (default: console)"
    )
    
    # Interactive mode arguments
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive navigation mode with arrow key controls"
    )
    
    # Web mode arguments
    parser.add_argument(
        "--web", "-w",
        action="store_true",
        help="Run in web server mode for browser-based calendar viewing"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for web server (default: 8080, web mode only)"
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for web server (default: 0.0.0.0, web mode only)"
    )
    
    parser.add_argument(
        "--auto-open",
        action="store_true",
        help="Automatically open browser when starting web mode"
    )
    
    # Raspberry Pi e-ink display arguments
    rpi_group = parser.add_argument_group('rpi', 'Raspberry Pi e-ink display options')
    
    rpi_group.add_argument(
        "--rpi", "--rpi-mode",
        action="store_true",
        help="Enable Raspberry Pi e-ink display mode (800x480px optimized)"
    )
    
    rpi_group.add_argument(
        "--rpi-width",
        type=int,
        default=800,
        help="RPI display width in pixels (default: 800)"
    )
    
    rpi_group.add_argument(
        "--rpi-height",
        type=int,
        default=480,
        help="RPI display height in pixels (default: 480)"
    )
    
    rpi_group.add_argument(
        "--rpi-refresh-mode",
        choices=['partial', 'full'],
        default='partial',
        help="E-ink refresh mode (default: partial)"
    )
    
    # Comprehensive logging arguments
    logging_group = parser.add_argument_group('logging', 'Comprehensive logging configuration options')
    
    # Log level options
    logging_group.add_argument(
        "--log-level",
        choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help="Set both console and file log levels"
    )
    
    logging_group.add_argument(
        "--console-level",
        choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help="Set console log level specifically"
    )
    
    logging_group.add_argument(
        "--file-level",
        choices=['DEBUG', 'VERBOSE', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help="Set file log level specifically"
    )
    
    # Quick options
    logging_group.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only show errors on console (sets console level to ERROR)"
    )
    
    # File logging options
    logging_group.add_argument(
        "--log-dir",
        type=Path,
        help="Custom directory for log files"
    )
    
    logging_group.add_argument(
        "--no-file-logging",
        action="store_true",
        help="Disable file logging completely"
    )
    
    logging_group.add_argument(
        "--max-log-files",
        type=int,
        help="Maximum number of log files to keep (default: 5)"
    )
    
    # Console options
    logging_group.add_argument(
        "--no-console-logging",
        action="store_true",
        help="Disable console logging completely"
    )
    
    logging_group.add_argument(
        "--no-log-colors",
        action="store_true",
        help="Disable colored console output"
    )
    
    # Interactive mode options
    logging_group.add_argument(
        "--no-split-display",
        action="store_true",
        help="Disable split display in interactive mode"
    )
    
    logging_group.add_argument(
        "--log-lines",
        type=int,
        help="Number of log lines to show in interactive mode (default: 5)"
    )
    
    return parser


async def run_test_mode(args) -> int:
    """Run Calendar Bot in test/validation mode.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Import validation and logging components
        from calendarbot.validation import ValidationRunner, setup_validation_logging
        from calendarbot.utils.logging import apply_command_line_overrides, setup_enhanced_logging
        from config.settings import settings
        
        # Apply command-line logging overrides with priority system
        updated_settings = apply_command_line_overrides(settings, args)
        
        # Apply RPI-specific overrides
        updated_settings = apply_rpi_overrides(updated_settings, args)
        
        # Set up enhanced logging for validation
        logger = setup_enhanced_logging(updated_settings, interactive_mode=False)
        logger.info("Enhanced logging initialized for test mode")
        
        # Create validation runner
        runner = ValidationRunner(
            test_date=args.date,
            end_date=args.end_date,
            components=args.components,
            use_cache=not args.no_cache,
            output_format=args.output_format
        )
        
        # Run validation
        results = await runner.run_validation()
        
        # Print results
        runner.print_results(verbose=args.verbose)
        
        # Return appropriate exit code
        if results.has_failures():
            return 1
        elif results.has_warnings():
            return 0  # Warnings don't cause failure
        else:
            return 0
            
    except KeyboardInterrupt:
        print("\nValidation interrupted by user")
        return 1
    except Exception as e:
        print(f"Validation error: {e}")
        return 1


async def run_daemon_mode(args) -> int:
    """Run Calendar Bot in daemon mode.
    
    Args:
        args: Parsed command line arguments
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    from calendarbot.main import main
    from calendarbot.utils.logging import apply_command_line_overrides, setup_enhanced_logging
    from config.settings import settings
    
    # Apply command-line logging overrides with priority system
    updated_settings = apply_command_line_overrides(settings, args)
    
    # Apply RPI-specific overrides
    updated_settings = apply_rpi_overrides(updated_settings, args)
    
    # Set up enhanced logging for daemon mode
    logger = setup_enhanced_logging(updated_settings, interactive_mode=False)
    logger.info("Enhanced logging initialized for daemon mode")
    
    return await main()


async def run_interactive_mode(args) -> int:
    """Run Calendar Bot in interactive navigation mode.
    
    Args:
        args: Parsed command line arguments
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        from calendarbot.main import CalendarBot
        from calendarbot.ui import InteractiveController
        from calendarbot.utils.logging import apply_command_line_overrides, setup_enhanced_logging
        from config.settings import settings
        
        # Apply command-line logging overrides with priority system
        updated_settings = apply_command_line_overrides(settings, args)
        
        # Apply RPI-specific overrides
        updated_settings = apply_rpi_overrides(updated_settings, args)
        
        # Create Calendar Bot instance
        app = CalendarBot()
        
        # Initialize components
        if not await app.initialize():
            print("Failed to initialize Calendar Bot")
            return 1
        
        # Set up enhanced logging for interactive mode with split display
        logger = setup_enhanced_logging(
            updated_settings,
            interactive_mode=True,
            display_manager=app.display_manager
        )
        logger.info("Enhanced logging initialized for interactive mode")
        
        # Create interactive controller
        interactive = InteractiveController(app.cache_manager, app.display_manager)
        
        # Start background data fetching
        fetch_task = asyncio.create_task(app.run_background_fetch())
        
        try:
            print("Starting interactive calendar navigation...")
            print("Use arrow keys to navigate, Space for today, ESC to exit")
            
            # Start interactive mode
            await interactive.start()
            
        finally:
            # Stop background fetching
            fetch_task.cancel()
            try:
                await fetch_task
            except asyncio.CancelledError:
                pass
            
            # Cleanup
            await app.cleanup()
        
        return 0
        
    except KeyboardInterrupt:
        print("\nInteractive mode interrupted")
        return 0
    except Exception as e:
        print(f"Interactive mode error: {e}")
        return 1


async def run_web_mode(args) -> int:
    """Run Calendar Bot in web server mode.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    import signal
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\nReceived signal {signum}, initiating graceful shutdown...")
        shutdown_event.set()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        import webbrowser
        from calendarbot.main import CalendarBot
        from calendarbot.web.server import WebServer
        from calendarbot.web.navigation import WebNavigationHandler
        from calendarbot.utils.logging import apply_command_line_overrides, setup_enhanced_logging
        from config.settings import settings
        
        # Apply command-line logging overrides with priority system
        updated_settings = apply_command_line_overrides(settings, args)
        print(f"DEBUG: After command line overrides - web_theme={getattr(updated_settings, 'web_theme', 'NOT_SET')}")
        
        # Apply RPI-specific overrides
        updated_settings = apply_rpi_overrides(updated_settings, args)
        print(f"DEBUG: After RPI overrides - web_theme={getattr(updated_settings, 'web_theme', 'NOT_SET')}")
        
        # Apply web mode overrides - ensure HTML renderer and eink-rpi theme for web mode
        if not hasattr(args, 'rpi') or not args.rpi:
            # DIAGNOSTIC: This is the source of the problem!
            print(f"DEBUG: PROBLEM IDENTIFIED - Setting display_type='html' instead of 'rpi'")
            print(f"DEBUG: This causes wrong HTML template structure to be generated")
            # FIXED: Use RPI renderer for proper layout structure
            updated_settings.display_type = "rpi"
            updated_settings.web_theme = "eink-rpi"  # Default to RPI-optimized theme for web mode
            print(f"DEBUG: FIXED - Set display_type = 'rpi' and web_theme = 'eink-rpi' for web mode")
        
        # Set up enhanced logging for web mode
        logger = setup_enhanced_logging(updated_settings, interactive_mode=False)
        logger.info("Enhanced logging initialized for web mode")
        
        logger.info("Starting Calendar Bot web mode initialization...")
        
        # Create Calendar Bot instance
        app = CalendarBot()
        logger.debug("Created CalendarBot instance")
        
        # Initialize components
        logger.info("Initializing Calendar Bot components...")
        if not await app.initialize():
            logger.error("Failed to initialize Calendar Bot")
            print("Failed to initialize Calendar Bot")
            return 1
        logger.info("Calendar Bot components initialized successfully")
        
        # Override web settings from command line
        logger.debug(f"Original settings - host: {updated_settings.web_host}, port: {updated_settings.web_port}")
        updated_settings.web_host = args.host
        updated_settings.web_port = args.port
        logger.info(f"Updated web settings - host: {updated_settings.web_host}, port: {updated_settings.web_port}")
        
        # CRITICAL: Check settings object mismatch
        print(f"DEBUG: SETTINGS MISMATCH CHECK:")
        print(f"  updated_settings.web_theme = {getattr(updated_settings, 'web_theme', 'NOT_SET')}")
        print(f"  original settings.web_theme = {getattr(settings, 'web_theme', 'NOT_SET')}")
        
        # Create web navigation handler
        logger.debug("Creating web navigation handler...")
        navigation_handler = WebNavigationHandler()
        logger.debug("Web navigation handler created successfully")
        
        # Create web server with navigation state enabled
        logger.debug("Creating WebServer with navigation state enabled...")
        try:
            web_server = WebServer(
                settings=updated_settings,
                display_manager=app.display_manager,
                cache_manager=app.cache_manager,
                navigation_state=navigation_handler.navigation_state  # Navigation enabled
            )
            logger.info("WebServer created successfully with navigation enabled")
        except Exception as e:
            logger.error(f"Failed to create WebServer: {e}")
            logger.debug(f"WebServer parameters attempted: settings={settings}, display_manager={app.display_manager}, cache_manager={app.cache_manager}, navigation_state={navigation_handler.navigation_state}")
            raise
        
        # Start background data fetching
        logger.debug("Starting background data fetching task...")
        fetch_task = asyncio.create_task(app.run_background_fetch())
        logger.debug("Background data fetching task started")
        
        try:
            print(f"Starting Calendar Bot web server on http://{args.host}:{args.port}")
            print("Press Ctrl+C to stop the server")
            logger.info(f"Web server configured for http://{args.host}:{args.port}")
            
            # Optionally open browser
            if args.auto_open:
                url = f"http://{args.host}:{args.port}"
                print(f"Opening browser to {url}")
                logger.info(f"Auto-opening browser to {url}")
                try:
                    webbrowser.open(url)
                except Exception as e:
                    logger.warning(f"Failed to auto-open browser: {e}")
            
            # Start web server (NOT async - fixed sync/async mismatch)
            logger.debug("Starting web server...")
            web_server.start()
            logger.info("Web server started successfully")
            
            # Keep the server running
            print("Web server is running. Press Ctrl+C to stop.")
            logger.debug("DEBUG: Entering main server loop with graceful shutdown")
            
            # Wait for shutdown signal using polling to keep event loop responsive
            logger.info("Web server started, waiting for shutdown signal...")
            
            # Poll the shutdown event instead of blocking on await
            while not shutdown_event.is_set():
                await asyncio.sleep(0.1)  # Check every 100ms
            
            logger.info("Shutdown signal received, beginning graceful shutdown...")
            
        finally:
            logger.debug("Entering cleanup phase...")
            
            # Stop web server
            try:
                logger.debug("Stopping web server...")
                web_server.stop()
                logger.info("Web server stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping web server: {e}")
            
            # Stop background fetching
            logger.debug("Cancelling background fetch task...")
            fetch_task.cancel()
            try:
                await fetch_task
            except asyncio.CancelledError:
                logger.debug("Background fetch task cancelled successfully")
            except Exception as e:
                logger.error(f"Error cancelling background fetch task: {e}")
            
            # Cleanup
            try:
                logger.debug("Running application cleanup...")
                await app.cleanup()
                logger.info("Application cleanup completed")
            except Exception as e:
                logger.error(f"Error during application cleanup: {e}")
        
        logger.info("Web mode completed successfully")
        return 0
        
    except Exception as e:
        # Use print instead of logger since logger might not be initialized yet
        print(f"Web server error: {e}")
        import traceback
        traceback.print_exc()
        return 1


async def main_entry() -> int:
    """Main entry point with argument parsing and first-run detection.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle setup wizard
    if hasattr(args, 'setup') and args.setup:
        return run_setup_wizard()
    
    # Handle backup operations
    if hasattr(args, 'backup') and args.backup:
        return backup_configuration()
    
    if hasattr(args, 'restore') and args.restore:
        return restore_configuration(args.restore)
    
    if hasattr(args, 'list_backups') and args.list_backups:
        return list_backups()
    
    # Check if configuration exists
    is_configured, config_path = check_configuration()
    
    # If not configured and not running setup, show guidance
    if not is_configured and not (hasattr(args, 'test_mode') and args.test_mode):
        show_setup_guidance()
        print(f"\n💡 Tip: Run 'calendarbot --setup' to get started quickly!\n")
        return 1
    
    # Validate mutually exclusive modes
    mode_count = sum([
        getattr(args, 'test_mode', False),
        getattr(args, 'interactive', False),
        getattr(args, 'web', False)
    ])
    if mode_count > 1:
        parser.error("Only one mode can be specified: --test-mode, --interactive, or --web")
    
    # Run in specified mode
    if hasattr(args, 'test_mode') and args.test_mode:
        return await run_test_mode(args)
    elif hasattr(args, 'web') and args.web:
        return await run_web_mode(args)
    else:
        # Default to interactive mode when no other mode is specified
        return await run_interactive_mode(args)


if __name__ == "__main__":
    # Run the Calendar Bot application
    exit_code = asyncio.run(main_entry())
    sys.exit(exit_code)