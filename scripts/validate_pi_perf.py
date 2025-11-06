#!/usr/bin/env python3
"""
Pi Zero 2W Performance Threshold Validator

Validates performance benchmark results against Pi Zero 2W constraints.
Designed to be used as a CI gate to prevent performance regressions.

Usage:
    python scripts/validate_pi_perf.py results.json --fail-under 200ms
    python scripts/validate_pi_perf.py results.json --max-memory 100MB --max-parse-time 200ms
"""
import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PerformanceThresholds:
    """Performance thresholds for Pi Zero 2W deployment."""

    max_parse_time_ms: float = 200.0  # Maximum parse time for 50 events
    max_memory_delta_mb: float = 50.0  # Maximum memory increase during parse
    max_total_memory_mb: float = 150.0  # Maximum total RSS after parse
    max_overall_time_ms: float = 250.0  # Maximum overall scenario time


@dataclass
class ValidationResult:
    """Result of performance validation."""

    passed: bool
    scenario: str
    parse_time_ms: float
    memory_delta_mb: float
    total_memory_mb: float
    overall_time_ms: float
    failures: list[str]


def parse_size_arg(size_str: str) -> float:
    """Parse size argument (e.g., '200ms', '100MB') to numeric value."""
    size_str = size_str.strip().upper()

    if size_str.endswith("MS"):
        return float(size_str[:-2])
    elif size_str.endswith("MB"):
        return float(size_str[:-2])
    elif size_str.endswith("KB"):
        return float(size_str[:-2]) / 1024
    elif size_str.endswith("S"):
        return float(size_str[:-1]) * 1000  # Convert seconds to ms
    else:
        # Try to parse as raw number
        return float(size_str)


def kb_to_mb(kb: Optional[int]) -> float:
    """Convert KB to MB."""
    return kb / 1024 if kb is not None else 0.0


def validate_scenario(
    scenario_data: dict, thresholds: PerformanceThresholds
) -> ValidationResult:
    """Validate a single scenario against thresholds."""
    scenario = scenario_data.get("scenario", "unknown")
    failures = []

    # Extract metrics
    overall_elapsed_s = scenario_data.get("overall_elapsed_s", 0.0)
    overall_time_ms = overall_elapsed_s * 1000

    # Get parse phase metrics
    phases = scenario_data.get("phases", [])
    if not phases:
        return ValidationResult(
            passed=False,
            scenario=scenario,
            parse_time_ms=0.0,
            memory_delta_mb=0.0,
            total_memory_mb=0.0,
            overall_time_ms=overall_time_ms,
            failures=["No phases found in scenario data"],
        )

    # Assume first phase is the parse phase
    parse_phase = phases[0]
    parse_elapsed_s = parse_phase.get("elapsed_s", 0.0)
    parse_time_ms = parse_elapsed_s * 1000

    rss_before_kb = parse_phase.get("rss_kb_before")
    rss_after_kb = parse_phase.get("rss_kb_after")

    memory_delta_mb = 0.0
    total_memory_mb = 0.0

    if rss_before_kb is not None and rss_after_kb is not None:
        memory_delta_mb = kb_to_mb(rss_after_kb - rss_before_kb)
        total_memory_mb = kb_to_mb(rss_after_kb)
    elif rss_after_kb is not None:
        total_memory_mb = kb_to_mb(rss_after_kb)

    # Check thresholds
    if parse_time_ms > thresholds.max_parse_time_ms:
        failures.append(
            f"Parse time {parse_time_ms:.1f}ms exceeds threshold {thresholds.max_parse_time_ms:.1f}ms"
        )

    if memory_delta_mb > thresholds.max_memory_delta_mb:
        failures.append(
            f"Memory delta {memory_delta_mb:.1f}MB exceeds threshold {thresholds.max_memory_delta_mb:.1f}MB"
        )

    if total_memory_mb > thresholds.max_total_memory_mb:
        failures.append(
            f"Total memory {total_memory_mb:.1f}MB exceeds threshold {thresholds.max_total_memory_mb:.1f}MB"
        )

    if overall_time_ms > thresholds.max_overall_time_ms:
        failures.append(
            f"Overall time {overall_time_ms:.1f}ms exceeds threshold {thresholds.max_overall_time_ms:.1f}ms"
        )

    return ValidationResult(
        passed=len(failures) == 0,
        scenario=scenario,
        parse_time_ms=parse_time_ms,
        memory_delta_mb=memory_delta_mb,
        total_memory_mb=total_memory_mb,
        overall_time_ms=overall_time_ms,
        failures=failures,
    )


def print_validation_report(results: list[ValidationResult]) -> None:
    """Print formatted validation report."""
    print("=" * 80)
    print("Pi Zero 2W Performance Validation Report")
    print("=" * 80)
    print()

    all_passed = all(r.passed for r in results)

    for result in results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"{status} - Scenario: {result.scenario}")
        print(f"  Parse Time:    {result.parse_time_ms:6.1f}ms")
        print(f"  Memory Delta:  {result.memory_delta_mb:6.1f}MB")
        print(f"  Total Memory:  {result.total_memory_mb:6.1f}MB")
        print(f"  Overall Time:  {result.overall_time_ms:6.1f}ms")

        if result.failures:
            print(f"  Failures:")
            for failure in result.failures:
                print(f"    • {failure}")
        print()

    print("=" * 80)
    if all_passed:
        print("✅ All scenarios passed - Performance meets Pi Zero 2W requirements")
    else:
        print("❌ Performance validation FAILED - Code does not meet Pi Zero 2W requirements")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Validate performance benchmark results for Pi Zero 2W deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default thresholds
  python scripts/validate_pi_perf.py results.json

  # Custom parse time threshold
  python scripts/validate_pi_perf.py results.json --fail-under 200ms

  # Custom memory threshold
  python scripts/validate_pi_perf.py results.json --max-memory 100MB

  # Multiple custom thresholds
  python scripts/validate_pi_perf.py results.json --max-parse-time 150ms --max-memory 80MB
        """,
    )
    parser.add_argument("results_file", type=Path, help="Path to benchmark results JSON file")
    parser.add_argument(
        "--fail-under",
        type=str,
        help="Alias for --max-parse-time (e.g., '200ms')",
    )
    parser.add_argument(
        "--max-parse-time",
        type=str,
        help="Maximum parse time threshold (e.g., '200ms', '0.2s')",
    )
    parser.add_argument(
        "--max-memory",
        type=str,
        help="Alias for --max-total-memory (e.g., '100MB')",
    )
    parser.add_argument(
        "--max-total-memory",
        type=str,
        help="Maximum total memory threshold (e.g., '150MB')",
    )
    parser.add_argument(
        "--max-memory-delta",
        type=str,
        help="Maximum memory delta threshold (e.g., '50MB')",
    )
    parser.add_argument(
        "--max-overall-time",
        type=str,
        help="Maximum overall scenario time (e.g., '250ms')",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Load results file
    if not args.results_file.exists():
        print(f"❌ ERROR: Results file not found: {args.results_file}", file=sys.stderr)
        sys.exit(1)

    try:
        with args.results_file.open("r") as f:
            results_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in results file: {e}", file=sys.stderr)
        sys.exit(1)

    # Build thresholds from arguments
    thresholds = PerformanceThresholds()

    if args.fail_under:
        thresholds.max_parse_time_ms = parse_size_arg(args.fail_under)
    if args.max_parse_time:
        thresholds.max_parse_time_ms = parse_size_arg(args.max_parse_time)
    if args.max_memory:
        thresholds.max_total_memory_mb = parse_size_arg(args.max_memory)
    if args.max_total_memory:
        thresholds.max_total_memory_mb = parse_size_arg(args.max_total_memory)
    if args.max_memory_delta:
        thresholds.max_memory_delta_mb = parse_size_arg(args.max_memory_delta)
    if args.max_overall_time:
        thresholds.max_overall_time_ms = parse_size_arg(args.max_overall_time)

    if args.verbose:
        print("Performance Thresholds:")
        print(f"  Max Parse Time:    {thresholds.max_parse_time_ms:.1f}ms")
        print(f"  Max Memory Delta:  {thresholds.max_memory_delta_mb:.1f}MB")
        print(f"  Max Total Memory:  {thresholds.max_total_memory_mb:.1f}MB")
        print(f"  Max Overall Time:  {thresholds.max_overall_time_ms:.1f}ms")
        print()

    # Validate each scenario
    validation_results = []
    for scenario_name, scenario_data in results_data.items():
        result = validate_scenario(scenario_data, thresholds)
        validation_results.append(result)

    # Print report
    print_validation_report(validation_results)

    # Exit with appropriate code
    all_passed = all(r.passed for r in validation_results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
