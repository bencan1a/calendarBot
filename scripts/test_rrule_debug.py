#!/usr/bin/env python3
"""
RRULE comparison test script: compare lite_rrule_expander output to python-dateutil.

Usage:
  python scripts/test_rrule_debug.py --env .env
  python scripts/test_rrule_debug.py --env .env --verbose --max-diff 5

This script fetches ICS data, extracts RRULE patterns, and compares expansion results
between CalendarBot Lite's implementation and python-dateutil as the reference.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Set, Tuple

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from calendarbot_lite.debug_helpers import (
    collect_rrule_candidates,
    fetch_ics_stream,
    parse_stream_via_parser,
    read_env,
)
from calendarbot_lite.lite_rrule_expander import expand_events_async

logger = logging.getLogger("test_rrule_debug")


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the test script."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def create_test_settings(expansion_days: int = 90) -> Any:
    """Create minimal settings for RRULE expansion testing."""
    settings = SimpleNamespace()
    settings.rrule_worker_concurrency = 1
    settings.max_occurrences_per_rule = 100  # Smaller for testing
    settings.expansion_days_window = expansion_days
    settings.expansion_time_budget_ms_per_rule = 1000  # Generous for testing
    settings.expansion_yield_frequency = 25
    return settings


def normalize_datetime_for_comparison(dt: datetime) -> datetime:
    """Normalize datetime to UTC for consistent comparison."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class RRuleComparison:
    """Compare RRULE expansion between lite implementation and dateutil."""

    def __init__(self, max_diff_to_show: int = 3):
        self.max_diff_to_show = max_diff_to_show
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.error_tests = 0
        self.results: List[Dict[str, Any]] = []

    async def compare_event_expansion(
        self,
        event: Any,
        rrule_string: str,
        exdates: Optional[List[str]],
        settings: Any,
    ) -> Dict[str, Any]:
        """Compare expansion of a single event between implementations."""
        result = {
            "event_id": getattr(event, "id", "unknown"),
            "subject": getattr(event, "subject", ""),
            "rrule_string": rrule_string,
            "exdates_count": len(exdates) if exdates else 0,
            "status": "unknown",
            "lite_count": 0,
            "dateutil_count": 0,
            "differences": [],
            "error": None,
        }

        try:
            # Get start datetime for the event
            start_dt = None
            if hasattr(event, "start") and hasattr(event.start, "date_time"):
                start_dt = event.start.date_time
            elif hasattr(event, "start"):
                start_dt = getattr(event, "start", None)
            
            if not start_dt:
                result["error"] = "No start datetime found"
                result["status"] = "error"
                return result

            # Normalize start datetime
            start_dt = normalize_datetime_for_comparison(start_dt)

            # Calculate expansion window
            expansion_days = getattr(settings, "expansion_days_window", 90)
            end_window = start_dt + timedelta(days=expansion_days)

            # Get lite implementation results
            try:
                lite_events = await expand_events_async([(event, rrule_string, exdates)], settings)
                lite_occurrences = set()
                for expanded_event in lite_events:
                    if hasattr(expanded_event, "start") and hasattr(expanded_event.start, "date_time"):
                        dt = normalize_datetime_for_comparison(expanded_event.start.date_time)
                        lite_occurrences.add(dt)
                result["lite_count"] = len(lite_occurrences)
            except Exception as e:
                result["error"] = f"Lite expansion failed: {e}"
                result["status"] = "error"
                return result

            # Get dateutil reference results
            try:
                from dateutil.rrule import rrulestr
                
                rule = rrulestr(rrule_string, dtstart=start_dt)
                dateutil_raw = list(rule.between(start_dt, end_window, inc=True))
                dateutil_occurrences = {normalize_datetime_for_comparison(dt) for dt in dateutil_raw}
                
                # Apply EXDATE filtering if present
                if exdates:
                    exdate_set = set()
                    for exdate_str in exdates:
                        try:
                            # Parse EXDATE (simplified parsing for testing)
                            if exdate_str.startswith("TZID="):
                                _, dt_part = exdate_str.split(":", 1)
                                dt_part = dt_part.rstrip("Z")
                            else:
                                dt_part = exdate_str.rstrip("Z")
                            
                            # Try common formats
                            for fmt in ["%Y%m%dT%H%M%S", "%Y-%m-%dT%H:%M:%S", "%Y%m%d"]:
                                try:
                                    exdt = datetime.strptime(dt_part, fmt)
                                    if exdate_str.endswith("Z"):
                                        exdt = exdt.replace(tzinfo=timezone.utc)
                                    exdate_set.add(normalize_datetime_for_comparison(exdt))
                                    break
                                except ValueError:
                                    continue
                        except Exception as e:
                            logger.debug("Failed to parse EXDATE '%s': %s", exdate_str, e)
                    
                    # Remove EXDATEs
                    dateutil_occurrences -= exdate_set
                
                result["dateutil_count"] = len(dateutil_occurrences)
            except ImportError:
                result["error"] = "python-dateutil not available"
                result["status"] = "error"
                return result
            except Exception as e:
                result["error"] = f"Dateutil expansion failed: {e}"
                result["status"] = "error"
                return result

            # Compare results
            lite_only = lite_occurrences - dateutil_occurrences
            dateutil_only = dateutil_occurrences - lite_occurrences
            
            if not lite_only and not dateutil_only:
                result["status"] = "match"
            else:
                result["status"] = "mismatch"
                
                # Record differences (limited to avoid huge output)
                differences = []
                for dt in sorted(list(lite_only)[:self.max_diff_to_show]):
                    differences.append(f"lite_only: {dt.isoformat()}")
                for dt in sorted(list(dateutil_only)[:self.max_diff_to_show]):
                    differences.append(f"dateutil_only: {dt.isoformat()}")
                
                if len(lite_only) > self.max_diff_to_show:
                    differences.append(f"... and {len(lite_only) - self.max_diff_to_show} more lite_only")
                if len(dateutil_only) > self.max_diff_to_show:
                    differences.append(f"... and {len(dateutil_only) - self.max_diff_to_show} more dateutil_only")
                
                result["differences"] = differences

        except Exception as e:
            logger.exception("Comparison failed for event %s: %s", result["event_id"], e)
            result["error"] = f"Comparison failed: {e}"
            result["status"] = "error"

        return result

    async def run_comparison_suite(
        self,
        candidates: List[Tuple[Any, str, Optional[List[str]]]],
        settings: Any,
    ) -> None:
        """Run comparison tests on all RRULE candidates."""
        logger.info("Running comparison suite on %d RRULE candidates", len(candidates))

        for i, (event, rrule_str, exdates) in enumerate(candidates):
            logger.debug("Testing candidate %d/%d: %s", i + 1, len(candidates), rrule_str[:50])
            
            comparison_result = await self.compare_event_expansion(event, rrule_str, exdates, settings)
            self.results.append(comparison_result)
            
            # Update counters
            self.total_tests += 1
            if comparison_result["status"] == "match":
                self.passed_tests += 1
            elif comparison_result["status"] == "mismatch":
                self.failed_tests += 1
            elif comparison_result["status"] == "error":
                self.error_tests += 1

    def print_summary(self) -> None:
        """Print test summary and detailed results."""
        print(f"\n{'='*60}")
        print("RRULE COMPARISON SUMMARY")
        print(f"{'='*60}")
        print(f"Total tests:    {self.total_tests}")
        print(f"Passed (match): {self.passed_tests}")
        print(f"Failed (diff):  {self.failed_tests}")
        print(f"Errors:         {self.error_tests}")
        
        if self.total_tests > 0:
            success_rate = (self.passed_tests / self.total_tests) * 100
            print(f"Success rate:   {success_rate:.1f}%")

        # Show failed tests
        if self.failed_tests > 0:
            print(f"\n{'='*60}")
            print("FAILED TESTS (MISMATCHES)")
            print(f"{'='*60}")
            
            for result in self.results:
                if result["status"] == "mismatch":
                    print(f"\nEvent: {result['event_id']} - {result['subject']}")
                    print(f"RRULE: {result['rrule_string']}")
                    print(f"Lite count: {result['lite_count']}, Dateutil count: {result['dateutil_count']}")
                    if result["differences"]:
                        print("Differences:")
                        for diff in result["differences"]:
                            print(f"  - {diff}")

        # Show error tests
        if self.error_tests > 0:
            print(f"\n{'='*60}")
            print("ERROR TESTS")
            print(f"{'='*60}")
            
            for result in self.results:
                if result["status"] == "error":
                    print(f"\nEvent: {result['event_id']} - {result['subject']}")
                    print(f"RRULE: {result['rrule_string']}")
                    print(f"Error: {result['error']}")

        print(f"\n{'='*60}")


async def main_async(args: argparse.Namespace) -> None:
    """Main async function for the test script."""
    setup_logging(verbose=args.verbose)
    
    # Read environment
    env_data = read_env(args.env)
    ics_source = env_data.get("ICS_SOURCE")
    if not ics_source:
        logger.error("No ICS_SOURCE found in %s", args.env)
        sys.exit(1)

    logger.info("Testing RRULE implementation against python-dateutil")
    logger.info("ICS source: %s", ics_source[:100])

    # Create settings
    settings = create_test_settings(expansion_days=args.expansion_days)

    try:
        # Fetch and parse ICS
        logger.info("Fetching and parsing ICS data...")
        
        if ics_source.startswith(("http://", "https://")):
            byte_stream = fetch_ics_stream(ics_source, timeout=30)
            parse_result = await parse_stream_via_parser(byte_stream, source_url=ics_source)
        else:
            # File source
            file_path = Path(ics_source)
            if not file_path.exists():
                logger.error("File not found: %s", ics_source)
                sys.exit(1)
            
            content = file_path.read_text(encoding="utf-8")
            async def content_to_bytes():
                for chunk in [content[i:i+8192] for i in range(0, len(content), 8192)]:
                    yield chunk.encode("utf-8")
            
            parse_result = await parse_stream_via_parser(content_to_bytes(), source_url=f"file://{file_path}")

        if not (hasattr(parse_result, "success") and parse_result.success):
            error_msg = getattr(parse_result, "error_message", "Unknown parse error")
            logger.error("Parse failed: %s", error_msg)
            sys.exit(1)

        events = getattr(parse_result, "events", [])
        logger.info("Parsed %d events", len(events))

        # Collect RRULE candidates
        candidates = collect_rrule_candidates(events)
        logger.info("Found %d RRULE candidates", len(candidates))

        if not candidates:
            logger.warning("No RRULE patterns found - nothing to test")
            return

        # Limit candidates if requested
        if args.limit and len(candidates) > args.limit:
            logger.info("Limiting to first %d candidates", args.limit)
            candidates = candidates[:args.limit]

        # Run comparison tests
        comparison = RRuleComparison(max_diff_to_show=args.max_diff)
        await comparison.run_comparison_suite(candidates, settings)
        
        # Print results
        comparison.print_summary()

        # Exit with appropriate code
        if comparison.error_tests > 0:
            logger.error("Some tests had errors")
            sys.exit(2)
        elif comparison.failed_tests > 0:
            logger.error("Some tests failed (mismatches found)")
            sys.exit(1)
        else:
            logger.info("All tests passed!")

    except Exception as e:
        logger.exception("Test script failed: %s", e)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test RRULE implementation against python-dateutil")
    parser.add_argument("--env", default=".env", help="Path to .env file (default: .env)")
    parser.add_argument("--limit", type=int, help="Limit number of RRULE patterns to test")
    parser.add_argument("--expansion-days", type=int, default=90, help="Days to expand forward (default: 90)")
    parser.add_argument("--max-diff", type=int, default=3, help="Max differences to show per test (default: 3)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception("Script failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()