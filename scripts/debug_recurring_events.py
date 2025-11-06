#!/usr/bin/env python3
"""
Debug helper: fetch ICS from workspace .env-configured source, parse, expand RRULEs,
and write a structured JSON trace to --output.

Usage:
  python scripts/debug_recurring_events.py --env .env --output /tmp/expansion_debug.json --limit 50 --compare-dateutil

This script is conservative (safe defaults) and intended for diagnostic runs under the
project virtualenv.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from calendarbot_lite.core.debug_helpers import (
    collect_rrule_candidates,
    event_summary,
    expand_candidates_to_trace,
    fetch_ics_stream,
    parse_stream_via_parser,
    read_env,
)

logger = logging.getLogger("debug_recurring_events")


def setup_logging(debug: bool = False) -> None:
    """Configure logging for debug script."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def create_mock_settings(
    expansion_days: int = 365,
    max_occurrences: int = 250,
    limit_per_rule: Optional[int] = None,
) -> Any:
    """Create a minimal settings object for RRULE expansion."""
    settings = SimpleNamespace()
    settings.rrule_worker_concurrency = 1
    settings.max_occurrences_per_rule = limit_per_rule or max_occurrences
    settings.expansion_days_window = expansion_days
    settings.expansion_time_budget_ms_per_rule = 500  # More generous for debug
    settings.expansion_yield_frequency = 50
    return settings


async def fetch_and_parse_phase(ics_source: str) -> Dict[str, Any]:
    """Fetch ICS content and parse it, returning structured results."""
    phase_result = {
        "success": False,
        "fetch_metadata": {},
        "parse_metadata": {},
        "events": [],
        "warnings": [],
        "error": None,
    }

    try:
        logger.info("Starting fetch phase for source: %s", ics_source[:100])

        # Handle file vs URL
        if ics_source.startswith(("http://", "https://")):
            # HTTP(S) fetch
            try:
                fetch_start = datetime.now(timezone.utc)
                byte_stream = fetch_ics_stream(ics_source, timeout=30)

                # Parse the stream
                parse_result = await parse_stream_via_parser(byte_stream, source_url=ics_source)
                fetch_end = datetime.now(timezone.utc)

                phase_result["fetch_metadata"] = {
                    "source_type": "http",
                    "url": ics_source,
                    "fetch_duration_ms": (fetch_end - fetch_start).total_seconds() * 1000,
                    "status": "success",
                }
            except Exception as e:
                logger.exception("HTTP fetch failed: %s", e)
                phase_result["error"] = f"HTTP fetch failed: {e}"
                return phase_result
        else:
            # File fetch
            try:
                file_path = Path(ics_source)
                if not file_path.exists():
                    phase_result["error"] = f"File not found: {ics_source}"
                    return phase_result

                content = file_path.read_text(encoding="utf-8")
                logger.info("Read %d characters from file", len(content))

                # Convert to async byte stream for consistency
                async def content_to_bytes():
                    for chunk in [content[i:i+8192] for i in range(0, len(content), 8192)]:
                        yield chunk.encode("utf-8")

                parse_result = await parse_stream_via_parser(content_to_bytes(), source_url=f"file://{file_path}")

                phase_result["fetch_metadata"] = {
                    "source_type": "file",
                    "path": str(file_path),
                    "size_bytes": len(content),
                    "status": "success",
                }
            except Exception as e:
                logger.exception("File read failed: %s", e)
                phase_result["error"] = f"File read failed: {e}"
                return phase_result

        # Process parse results
        if hasattr(parse_result, "success") and parse_result.success:
            events = getattr(parse_result, "events", [])
            warnings = getattr(parse_result, "warnings", [])

            phase_result["parse_metadata"] = {
                "total_components": getattr(parse_result, "total_components", 0),
                "event_count": getattr(parse_result, "event_count", len(events)),
                "recurring_event_count": getattr(parse_result, "recurring_event_count", 0),
                "calendar_name": getattr(parse_result, "calendar_name", None),
                "timezone": getattr(parse_result, "timezone", None),
                "prodid": getattr(parse_result, "prodid", None),
            }

            # Convert events to summaries for JSON serialization
            phase_result["events"] = [event_summary(ev) for ev in events]
            phase_result["warnings"] = list(warnings)
            phase_result["success"] = True

            logger.info("Parse successful: %d events, %d warnings", len(events), len(warnings))
        else:
            error_msg = getattr(parse_result, "error_message", "Unknown parse error")
            phase_result["error"] = f"Parse failed: {error_msg}"
            logger.error("Parse failed: %s", error_msg)

    except Exception as e:
        logger.exception("Fetch and parse phase failed: %s", e)
        phase_result["error"] = f"Unexpected error: {e}"

    return phase_result


async def expansion_phase(
    parsed_events: List[Any],
    settings: Any,
    compare_dateutil: bool = False,
) -> Dict[str, Any]:
    """Expand RRULE patterns and return structured results."""
    phase_result = {
        "success": False,
        "rrule_candidates": [],
        "expansion_traces": {},
        "expansion_metadata": {},
        "dateutil_comparison": None,
        "warnings": [],
        "error": None,
    }

    try:
        # Collect RRULE candidates
        candidates = collect_rrule_candidates(parsed_events)
        logger.info("Found %d RRULE candidates for expansion", len(candidates))

        phase_result["rrule_candidates"] = [
            {
                "event_id": getattr(event, "id", "unknown"),
                "subject": getattr(event, "subject", ""),
                "rrule_string": rrule_str,
                "exdates_count": len(exdates) if exdates else 0,
            }
            for event, rrule_str, exdates in candidates
        ]

        if not candidates:
            phase_result["success"] = True
            phase_result["expansion_metadata"] = {"total_candidates": 0, "total_expansions": 0}
            return phase_result

        # Expand candidates
        expansion_start = datetime.now(timezone.utc)
        expansion_traces = await expand_candidates_to_trace(
            candidates,
            settings,
            limit_per_rule=getattr(settings, "max_occurrences_per_rule", 250)
        )
        expansion_end = datetime.now(timezone.utc)

        phase_result["expansion_traces"] = expansion_traces
        phase_result["expansion_metadata"] = {
            "total_candidates": len(candidates),
            "total_expansions": sum(len(instances) for instances in expansion_traces.values()),
            "expansion_duration_ms": (expansion_end - expansion_start).total_seconds() * 1000,
            "expansion_window_days": getattr(settings, "expansion_days_window", 365),
            "max_occurrences_per_rule": getattr(settings, "max_occurrences_per_rule", 250),
        }

        # Optional dateutil comparison
        if compare_dateutil:
            try:
                comparison_result = await compare_with_dateutil(candidates, settings)
                phase_result["dateutil_comparison"] = comparison_result
            except Exception as e:
                logger.warning("Dateutil comparison failed: %s", e)
                phase_result["warnings"].append(f"Dateutil comparison failed: {e}")

        phase_result["success"] = True
        logger.info("Expansion successful: %d traces generated", len(expansion_traces))

    except Exception as e:
        logger.exception("Expansion phase failed: %s", e)
        phase_result["error"] = f"Expansion failed: {e}"

    return phase_result


async def compare_with_dateutil(candidates: List[Any], settings: Any) -> Dict[str, Any]:
    """Compare lite expansion with python-dateutil for validation."""
    try:
        from dateutil.rrule import rrulestr
        from datetime import timedelta
    except ImportError:
        return {"error": "python-dateutil not available"}

    comparison = {"comparisons": [], "summary": {"matches": 0, "mismatches": 0, "errors": 0}}

    for event, rrule_str, exdates in candidates:
        try:
            # Get our expansion results (already computed)
            event_id = getattr(event, "id", "unknown")
            start_dt = getattr(event.start, "date_time", None) if hasattr(event, "start") else None

            if not start_dt:
                continue

            # Try dateutil expansion
            try:
                rule = rrulestr(rrule_str, dtstart=start_dt)
                expansion_days = getattr(settings, "expansion_days_window", 365)
                end_window = start_dt + timedelta(days=expansion_days)

                dateutil_occurrences = list(rule.between(start_dt, end_window, inc=True))
                dateutil_count = len(dateutil_occurrences)

                comparison["comparisons"].append({
                    "event_id": event_id,
                    "rrule_string": rrule_str,
                    "dateutil_count": dateutil_count,
                    "status": "success",
                })
                comparison["summary"]["matches"] += 1

            except Exception as e:
                comparison["comparisons"].append({
                    "event_id": event_id,
                    "rrule_string": rrule_str,
                    "dateutil_error": str(e),
                    "status": "error",
                })
                comparison["summary"]["errors"] += 1

        except Exception as e:
            logger.warning("Comparison failed for event %s: %s", getattr(event, "id", "unknown"), e)
            comparison["summary"]["errors"] += 1

    return comparison


async def main_async(args: argparse.Namespace) -> None:
    """Main async function for the debug script."""
    setup_logging(debug=bool(args.debug))

    # Read environment (prefer CALENDARBOT_ICS_URL, fall back to ICS_SOURCE in .env)
    env_data = read_env(args.env)
    ics_source = os.environ.get("CALENDARBOT_ICS_URL") or env_data.get("CALENDARBOT_ICS_URL") or env_data.get("ICS_SOURCE")
    if not ics_source:
        logger.error("No CALENDARBOT_ICS_URL or ICS_SOURCE found in %s", args.env)
        sys.exit(1)

    # Apply datetime override if specified
    if env_data.get("DATETIME_OVERRIDE"):
        logger.info("DATETIME_OVERRIDE found: %s", env_data["DATETIME_OVERRIDE"])

    # Enable debug logging if requested in env
    if env_data.get("CALENDARBOT_DEBUG") == "true":
        setup_logging(debug=True)

    # Create settings
    settings = create_mock_settings(
        expansion_days=args.expansion_days,
        max_occurrences=args.max_occurrences,
        limit_per_rule=args.limit,
    )

    # Main processing pipeline
    result = {
        "metadata": {
            "script_version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": ics_source,
            "args": {
                "env": args.env,
                "limit": args.limit,
                "expansion_days": args.expansion_days,
                "max_occurrences": args.max_occurrences,
                "compare_dateutil": args.compare_dateutil,
            },
            "env_overrides": {k: v for k, v in env_data.items() if v is not None},
        },
        "fetch_parse_phase": {},
        "expansion_phase": {},
    }

    try:
        # Phase 1: Fetch and Parse
        logger.info("=== Phase 1: Fetch and Parse ===")
        fetch_parse_result = await fetch_and_parse_phase(ics_source)
        result["fetch_parse_phase"] = fetch_parse_result

        if not fetch_parse_result["success"]:
            logger.error("Fetch/parse failed, stopping: %s", fetch_parse_result["error"])
        else:
            # Phase 2: RRULE Expansion
            logger.info("=== Phase 2: RRULE Expansion ===")
            # Convert event summaries back to mock objects for expansion
            mock_events = []
            for event_data in fetch_parse_result["events"]:
                if event_data.get("is_recurring") and event_data.get("rrule"):
                    mock_event = SimpleNamespace(**event_data)
                    # Add nested start/end objects
                    if event_data.get("start"):
                        mock_event.start = SimpleNamespace(date_time=datetime.fromisoformat(event_data["start"]))
                    if event_data.get("end"):
                        mock_event.end = SimpleNamespace(date_time=datetime.fromisoformat(event_data["end"]))
                    mock_events.append(mock_event)

            expansion_result = await expansion_phase(mock_events, settings, args.compare_dateutil)
            result["expansion_phase"] = expansion_result

    except Exception as e:
        logger.exception("Main processing failed: %s", e)
        result["error"] = str(e)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    logger.info("Results written to: %s", output_path)

    # Summary
    if result["fetch_parse_phase"].get("success"):
        event_count = len(result["fetch_parse_phase"]["events"])
        logger.info("Summary: %d events parsed", event_count)

        if result["expansion_phase"].get("success"):
            expansion_count = result["expansion_phase"]["expansion_metadata"]["total_expansions"]
            logger.info("Summary: %d total expanded instances", expansion_count)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Debug recurring events in CalendarBot Lite")
    parser.add_argument("--env", default=".env", help="Path to .env file (default: .env)")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--limit", type=int, help="Limit expansions per RRULE (optional)")
    parser.add_argument("--expansion-days", type=int, default=365, help="Days to expand forward (default: 365)")
    parser.add_argument("--max-occurrences", type=int, default=250, help="Max occurrences per rule (default: 250)")
    parser.add_argument("--compare-dateutil", action="store_true", help="Compare with python-dateutil")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

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