#!/usr/bin/env python3
"""
ICS Test Mode - Validate and test ICS calendar configuration.

This script provides command-line testing capabilities for ICS calendar feeds,
allowing users to validate their configuration before running the main application.
"""

import asyncio
import argparse
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

# Add the project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from calendarbot.sources import SourceManager
from calendarbot.ics.exceptions import ICSError, ICSFetchError, ICSParseError
from calendarbot.utils import setup_logging


def setup_test_logging(verbose: bool = False):
    """Set up logging for test mode."""
    level = "DEBUG" if verbose else "INFO"
    return setup_logging(
        log_level=level,
        log_file=None  # Console only for test mode
    )


async def test_ics_configuration(url: Optional[str] = None, verbose: bool = False) -> bool:
    """Test ICS configuration and connectivity.
    
    Args:
        url: Optional ICS URL to test (overrides settings)
        verbose: Enable verbose output
        
    Returns:
        True if all tests pass, False otherwise
    """
    logger = setup_test_logging(verbose)
    
    print("=" * 60)
    print("ICS Calendar Configuration Test")
    print("=" * 60)
    
    try:
        # Override URL if provided
        if url:
            settings.ics_url = url
            print(f"Testing custom URL: {url}")
        else:
            print(f"Testing configured URL: {settings.ics_url}")
        
        print()
        
        # Initialize source manager
        print("1. Initializing Source Manager...")
        source_manager = SourceManager(settings)
        
        if not await source_manager.initialize():
            print("❌ Failed to initialize source manager")
            return False
        print("✅ Source manager initialized successfully")
        
        # Test source configuration
        print("\n2. Validating Source Configuration...")
        source_info = source_manager.get_source_info("primary")
        
        print(f"   - Source Type: ICS Calendar")
        print(f"   - URL: {source_info.config.url}")
        print(f"   - Authentication: {source_info.config.auth_type or 'None'}")
        print(f"   - Configured: {'✅ Yes' if source_info else '❌ No'}")
        
        if not source_info:
            print("❌ Source not properly configured")
            return False
        
        # Test connectivity and health
        print("\n3. Testing Connectivity...")
        health_results = await source_manager.test_all_sources()
        primary_health = health_results.get("primary", {})
        
        print(f"   - Health Status: {'✅ Healthy' if primary_health.get('healthy', False) else '❌ Unhealthy'}")
        print(f"   - Response Time: {primary_health.get('response_time_ms', 0):.0f}ms")
        print(f"   - Status Message: {primary_health.get('status', 'Unknown')}")
        
        if primary_health.get('error_message'):
            print(f"   - Error Details: {primary_health['error_message']}")
        
        if not primary_health.get('healthy', False):
            print("❌ Connectivity test failed")
            return False
        
        # Test event fetching
        print("\n4. Testing Event Fetching...")
        try:
            events = await source_manager.get_todays_events()
            print(f"✅ Successfully fetched {len(events)} events for today")
            
            if events and verbose:
                print("\n   Sample Events:")
                for i, event in enumerate(events[:3]):  # Show first 3 events
                    print(f"   {i+1}. {event.summary}")
                    print(f"      Time: {event.start.date_time} - {event.end.date_time}")
                    if event.location:
                        print(f"      Location: {event.location}")
                    if event.body_preview:
                        desc = event.body_preview[:50] + "..." if len(event.body_preview) > 50 else event.body_preview
                        print(f"      Description: {desc}")
                    print()
                
                if len(events) > 3:
                    print(f"   ... and {len(events) - 3} more events")
            
        except Exception as e:
            print(f"❌ Failed to fetch events: {e}")
            return False
        
        # Test date range fetching
        print("\n5. Testing Date Range Fetching...")
        try:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=7)
            range_events = await source_manager.get_events_for_date_range(start_date, end_date)
            print(f"✅ Successfully fetched {len(range_events)} events for next 7 days")
            
        except Exception as e:
            print(f"❌ Failed to fetch date range events: {e}")
            return False
        
        # Get summary status (replacing metrics since get_metrics doesn't exist)
        print("\n6. Source Status:")
        summary = source_manager.get_summary_status()
        print(f"   - Total Sources: {summary.get('total_sources', 0)}")
        print(f"   - Healthy Sources: {summary.get('healthy_sources', 0)}")
        print(f"   - Last Update: {summary.get('last_successful_update', 'Never')}")
        print(f"   - Consecutive Failures: {summary.get('consecutive_failures', 0)}")
        print(f"   - Overall Health: {'✅ Healthy' if summary.get('is_healthy', False) else '❌ Unhealthy'}")
        
        print("\n" + "=" * 60)
        print("✅ All ICS tests passed successfully!")
        print("Your ICS configuration is working correctly.")
        print("=" * 60)
        
        return True
        
    except ICSFetchError as e:
        print(f"\n❌ ICS Fetch Error: {e}")
        if verbose:
            logger.exception("Detailed fetch error")
        return False
        
    except ICSParseError as e:
        print(f"\n❌ ICS Parse Error: {e}")
        if verbose:
            logger.exception("Detailed parse error")
        return False
        
    except ICSError as e:
        print(f"\n❌ ICS Error: {e}")
        if verbose:
            logger.exception("Detailed ICS error")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        if verbose:
            logger.exception("Detailed error")
        return False


async def validate_ics_format(url: str, verbose: bool = False) -> bool:
    """Validate ICS format without full configuration.
    
    Args:
        url: ICS URL to validate
        verbose: Enable verbose output
        
    Returns:
        True if ICS format is valid, False otherwise
    """
    logger = setup_test_logging(verbose)
    
    print("=" * 60)
    print("ICS Format Validation")
    print("=" * 60)
    print(f"Validating: {url}")
    print()
    
    try:
        from calendarbot.ics.fetcher import ICSFetcher
        from calendarbot.ics.parser import ICSParser
        from calendarbot.ics.models import ICSSource
        
        # Create a temporary source configuration
        source = ICSSource(
            name="Test ICS Source",
            url=url,
            timeout=30
        )
        
        # Test fetching
        print("1. Testing ICS Download...")
        fetcher = ICSFetcher(settings)
        response = await fetcher.fetch_ics(source)
        
        if not response.success:
            print(f"❌ Failed to download ICS: {response.error_message}")
            return False
        
        print("✅ ICS downloaded successfully")
        print(f"   - Content Length: {len(response.content)} characters")
        print(f"   - Status Code: {response.status_code}")
        
        # Test parsing
        print("\n2. Testing ICS Parsing...")
        parser = ICSParser(settings)
        parse_result = parser.parse_ics_content(response.content)
        
        if not parse_result.success:
            print(f"❌ Failed to parse ICS: {parse_result.error_message}")
            return False
        
        print("✅ ICS parsed successfully")
        print(f"   - Total Events Found: {len(parse_result.events)}")
        print(f"   - Parsing Warnings: {len(parse_result.warnings)}")
        
        if parse_result.warnings and verbose:
            print("   - Warnings:")
            for warning in parse_result.warnings:
                print(f"     • {warning}")
        
        # Show calendar metadata
        print(f"   - Calendar Name: {parse_result.calendar_name or 'N/A'}")
        print(f"   - Calendar Version: {parse_result.ics_version or 'N/A'}")
        print(f"   - Product ID: {parse_result.prodid or 'N/A'}")
        
        # Show sample events
        if parse_result.events and verbose:
            print(f"\n3. Sample Events (showing first 3 of {len(parse_result.events)}):")
            for i, event in enumerate(parse_result.events[:3]):
                print(f"   Event {i+1}:")
                print(f"     - Title: {event.title}")
                print(f"     - Start: {event.start_time}")
                print(f"     - End: {event.end_time}")
                print(f"     - All Day: {event.is_all_day}")
                if event.location:
                    print(f"     - Location: {event.location}")
                print()
        
        print("=" * 60)
        print("✅ ICS format validation passed!")
        print("The ICS calendar format is valid and parseable.")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Validation Error: {e}")
        if verbose:
            logger.exception("Detailed validation error")
        return False


def main():
    """Main entry point for ICS test mode."""
    parser = argparse.ArgumentParser(
        description="Test and validate ICS calendar configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_ics.py                                    # Test current configuration
  python test_ics.py -v                                 # Test with verbose output
  python test_ics.py --url https://example.com/cal.ics  # Test specific URL
  python test_ics.py --validate-only --url URL          # Only validate format
        """
    )
    
    parser.add_argument(
        "--url",
        help="ICS URL to test (overrides configuration)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output with detailed information"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate ICS format without full configuration test"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.validate_only and not args.url:
        print("❌ Error: --validate-only requires --url")
        return 1
    
    if not args.url and not settings.ics_url:
        print("❌ Error: No ICS URL configured. Use --url or configure in settings.")
        return 1
    
    try:
        # Run the appropriate test
        if args.validate_only:
            success = asyncio.run(validate_ics_format(args.url, args.verbose))
        else:
            success = asyncio.run(test_ics_configuration(args.url, args.verbose))
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())