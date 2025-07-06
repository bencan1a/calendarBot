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
        description="Calendar Bot - Microsoft 365 calendar display with interactive navigation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run in interactive mode (default)
  %(prog)s --test-mode               # Run validation tests
  %(prog)s --test-mode --verbose     # Run tests with verbose output
  %(prog)s --test-mode --date 2024-01-15 --components auth,api
  %(prog)s --test-mode --output-format json > results.json
  %(prog)s --interactive             # Run interactive console mode (explicit)
  %(prog)s --web                     # Run web server mode on localhost:8080
  %(prog)s --web --port 3000 --auto-open  # Run web server on port 3000 and open browser
        """
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
            # Only override if not in RPI mode
            updated_settings.display_type = "html"
            updated_settings.web_theme = "eink-rpi"  # Default to RPI-optimized theme for web mode
            print(f"DEBUG: Set display_type = 'html' and web_theme = 'eink-rpi' for web mode")
        
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
        
        # Create web server with correct parameters
        logger.debug("Creating WebServer with corrected parameters...")
        try:
            web_server = WebServer(
                settings=updated_settings,                        # FIXED: Use RPI-overridden settings
                display_manager=app.display_manager,              # Required second parameter
                cache_manager=app.cache_manager,                  # Required third parameter
                navigation_state=navigation_handler.navigation_state  # Correct parameter name
            )
            logger.info("WebServer created successfully")
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
    """Main entry point with argument parsing.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = create_parser()
    args = parser.parse_args()
    
    # Validate mutually exclusive modes
    mode_count = sum([args.test_mode, args.interactive, args.web])
    if mode_count > 1:
        parser.error("Only one mode can be specified: --test-mode, --interactive, or --web")
    
    if args.test_mode:
        return await run_test_mode(args)
    elif args.web:
        return await run_web_mode(args)
    else:
        # Default to interactive mode when no other mode is specified
        return await run_interactive_mode(args)


if __name__ == "__main__":
    # Run the Calendar Bot application
    exit_code = asyncio.run(main_entry())
    sys.exit(exit_code)