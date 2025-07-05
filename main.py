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


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Calendar Bot - Microsoft 365 calendar display daemon with test mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run as daemon
  %(prog)s --test-mode               # Run validation tests
  %(prog)s --test-mode --verbose     # Run tests with verbose output
  %(prog)s --test-mode --date 2024-01-15 --components auth,api
  %(prog)s --test-mode --output-format json > results.json
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
    
    return parser


async def run_test_mode(args) -> int:
    """Run Calendar Bot in test/validation mode.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Import validation components
        from calendarbot.validation import ValidationRunner, setup_validation_logging
        
        # Set up enhanced logging for validation
        setup_validation_logging(
            verbose=args.verbose,
            components=args.components if args.verbose else None,
            log_file=None  # Could be made configurable later
        )
        
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


async def run_daemon_mode() -> int:
    """Run Calendar Bot in daemon mode.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    from calendarbot.main import main
    return await main()


async def run_interactive_mode() -> int:
    """Run Calendar Bot in interactive navigation mode.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        from calendarbot.main import CalendarBot
        from calendarbot.ui import InteractiveController
        
        # Create Calendar Bot instance
        app = CalendarBot()
        
        # Initialize components
        if not await app.initialize():
            print("Failed to initialize Calendar Bot")
            return 1
        
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


async def main_entry() -> int:
    """Main entry point with argument parsing.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = create_parser()
    args = parser.parse_args()
    
    if args.test_mode:
        return await run_test_mode(args)
    elif args.interactive:
        return await run_interactive_mode()
    else:
        return await run_daemon_mode()


if __name__ == "__main__":
    # Run the Calendar Bot application
    exit_code = asyncio.run(main_entry())
    sys.exit(exit_code)