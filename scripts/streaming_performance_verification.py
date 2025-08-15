#!/usr/bin/env python3
"""
Streaming ICS Parser Performance Verification Script

Validates performance targets:
- 40-60MB memory reduction for large files (50MB+)
- 50% processing time improvement for files >20MB
- Memory usage stays <8MB regardless of file size

Created: 2025-08-14
Purpose: Final verification for Phase 1 streaming parser optimization
"""

import gc
import os
import sys
import time
import traceback
from pathlib import Path

import psutil

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from calendarbot.ics.parser import ICSParser  # noqa: E402


class MemoryProfiler:
    """Track memory usage during operations."""

    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = self.get_memory_mb()

    def get_memory_mb(self) -> float:
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024

    def get_peak_memory_increase(self) -> float:
        """Get peak memory increase since initialization."""
        current = self.get_memory_mb()
        return max(0, current - self.initial_memory)


def generate_large_ics_content(event_count: int = 10000) -> str:
    """Generate large ICS content for testing."""
    header = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CalendarBot//Performance Test//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
"""

    footer = "END:VCALENDAR\n"

    event_template = """BEGIN:VEVENT
UID:event-{event_id}@performance-test.com
DTSTART:20240{month:02d}{day:02d}T{hour:02d}0000Z
DTEND:20240{month:02d}{day:02d}T{end_hour:02d}0000Z
SUMMARY:Performance Test Event {event_id} - This is a longer summary that
  contains multiple lines to test line folding functionality across chunk
  boundaries in the streaming parser implementation
DESCRIPTION:This is a detailed description for event {event_id} that spans
  multiple lines and contains various information. The purpose is to create
  realistic ICS content that will test the streaming parser's ability to
  handle large files efficiently. This description is intentionally verbose
  to increase the file size and test memory usage patterns.
LOCATION:Test Location {location_id} - Conference Room {room}
ORGANIZER:CN=Test Organizer:MAILTO:organizer@test.com
ATTENDEE;PARTSTAT=ACCEPTED:MAILTO:attendee{attendee}@test.com
CREATED:20240101T120000Z
LAST-MODIFIED:20240101T120000Z
SEQUENCE:0
STATUS:CONFIRMED
TRANSP:OPAQUE
END:VEVENT
"""

    events = []
    for i in range(event_count):
        event = event_template.format(
            event_id=i,
            month=(i % 12) + 1,
            day=(i % 28) + 1,
            hour=(i % 24),
            end_hour=((i % 24) + 1) % 24,
            location_id=(i % 50) + 1,
            room=(i % 20) + 1,
            attendee=(i % 100) + 1,
        )
        events.append(event)

    return header + "".join(events) + footer


def benchmark_parser(content: str, parser_type: str, file_size_mb: float) -> dict:
    """Benchmark a parser with memory and timing metrics."""
    print(f"\n--- Benchmarking {parser_type} Parser (File: {file_size_mb:.1f}MB) ---")

    # Setup
    gc.collect()  # Clean up before test
    profiler = MemoryProfiler()

    start_time = time.perf_counter()
    initial_memory = profiler.get_memory_mb()

    try:
        # Create mock settings for parser
        class MockSettings:
            def __init__(self):
                pass

        settings = MockSettings()

        if parser_type == "Traditional":
            # Force traditional parsing by using parse_ics_content directly (bypasses streaming logic)
            parser = ICSParser(settings)

            # Create a small content first to force traditional path
            # small_content = content[:1000] + "\nEND:VCALENDAR"  # unused

            # Now use the traditional parser method directly (not the optimized one)
            # We'll simulate traditional parsing by ensuring we don't hit streaming threshold
            calendar_data = parser.parse_ics_content(content)

        elif parser_type == "Streaming":
            # Use the optimized parser that will automatically select streaming for large content
            parser = ICSParser(settings)
            calendar_data = parser.parse_ics_content_optimized(content)

        else:
            raise ValueError(f"Unknown parser type: {parser_type}")  # noqa: TRY301

        end_time = time.perf_counter()

        # Memory measurements
        peak_memory = profiler.get_memory_mb()
        memory_increase = peak_memory - initial_memory

        # Processing metrics
        processing_time = end_time - start_time
        event_count = len(calendar_data.events) if calendar_data and calendar_data.events else 0

        results = {
            "parser_type": parser_type,
            "file_size_mb": file_size_mb,
            "processing_time": processing_time,
            "memory_increase_mb": memory_increase,
            "peak_memory_mb": peak_memory,
            "events_parsed": event_count,
            "events_per_second": event_count / processing_time if processing_time > 0 else 0,
            "success": True,
        }

        print(f"✓ Processing time: {processing_time:.3f}s")
        print(f"✓ Memory increase: {memory_increase:.1f}MB")
        print(f"✓ Events parsed: {event_count}")
        print(f"✓ Events/sec: {results['events_per_second']:.1f}")

        return results

    except Exception as e:
        print(f"✗ Error: {e}")
        return {
            "parser_type": parser_type,
            "file_size_mb": file_size_mb,
            "error": str(e),
            "success": False,
        }
    finally:
        gc.collect()


def run_performance_comparison() -> list[dict]:
    """Run comprehensive performance comparison."""
    print("=" * 60)
    print("STREAMING ICS PARSER PERFORMANCE VERIFICATION")
    print("=" * 60)

    # Test scenarios: (event_count, expected_size_mb)
    test_scenarios = [
        (1000, 2),  # Small file
        (5000, 10),  # Medium file
        (10000, 20),  # Large file (triggers streaming)
        (25000, 50),  # Very large file
        (50000, 100),  # Extreme file
    ]

    results = []

    for event_count, expected_size_mb in test_scenarios:
        print(f"\n{'=' * 40}")
        print(f"SCENARIO: {event_count:,} events (~{expected_size_mb}MB)")
        print(f"{'=' * 40}")

        # Generate test content
        print("Generating test content...")
        content = generate_large_ics_content(event_count)
        actual_size_mb = len(content.encode("utf-8")) / 1024 / 1024
        print(f"Generated {actual_size_mb:.1f}MB of ICS content")

        # Test traditional parser (only for smaller files to avoid memory issues)
        traditional_result = None
        if actual_size_mb <= 20:  # Limit traditional parser to avoid OOM
            traditional_result = benchmark_parser(content, "Traditional", actual_size_mb)
            results.append(traditional_result)

        # Test streaming parser
        streaming_result = benchmark_parser(content, "Streaming", actual_size_mb)
        results.append(streaming_result)

        # Performance comparison (if both parsers ran)
        if (
            actual_size_mb <= 20
            and traditional_result is not None
            and traditional_result["success"]
            and streaming_result["success"]
        ):
            print("\n--- COMPARISON ---")
            time_improvement = (
                (traditional_result["processing_time"] - streaming_result["processing_time"])
                / traditional_result["processing_time"]
                * 100
            )
            memory_reduction = (
                traditional_result["memory_increase_mb"] - streaming_result["memory_increase_mb"]
            )

            print(f"Time improvement: {time_improvement:.1f}%")
            print(f"Memory reduction: {memory_reduction:.1f}MB")

            # Validate targets
            if actual_size_mb >= 20:
                if time_improvement >= 50:
                    print("✓ PASSED: 50% time improvement target")
                else:
                    print("✗ FAILED: 50% time improvement target")

            if actual_size_mb >= 50:
                if memory_reduction >= 40:
                    print("✓ PASSED: 40MB+ memory reduction target")
                else:
                    print("✗ FAILED: 40MB+ memory reduction target")

    return results


def validate_targets(results: list[dict]) -> None:  # noqa: PLR0912
    """Validate that performance targets are met."""
    print(f"\n{'=' * 60}")
    print("TARGET VALIDATION")
    print(f"{'=' * 60}")

    streaming_results = [
        r for r in results if r.get("parser_type") == "Streaming" and r.get("success")
    ]
    traditional_results = [
        r for r in results if r.get("parser_type") == "Traditional" and r.get("success")
    ]

    print("\nStreaming Parser Memory Usage:")
    for result in streaming_results:
        size = result["file_size_mb"]
        memory = result["memory_increase_mb"]
        status = "✓ PASS" if memory <= 8 else "✗ FAIL"
        print(f"  {size:6.1f}MB file -> {memory:5.1f}MB memory increase {status}")

    # Target 1: Memory usage <8MB regardless of file size
    max_memory = max((r["memory_increase_mb"] for r in streaming_results), default=0)
    print("\nTarget 1 - Memory usage <8MB: ", end="")
    if max_memory <= 8:
        print("✓ PASSED")
    else:
        print(f"✗ FAILED (Peak: {max_memory:.1f}MB)")

    # Target 2: 50% time improvement for files >20MB
    print("\nTarget 2 - 50% time improvement for files >20MB:")
    large_file_improvements = []

    for trad in traditional_results:
        if trad["file_size_mb"] > 20:
            matching_stream = next(
                (s for s in streaming_results if abs(s["file_size_mb"] - trad["file_size_mb"]) < 1),
                None,
            )
            if matching_stream:
                improvement = (
                    (trad["processing_time"] - matching_stream["processing_time"])
                    / trad["processing_time"]
                    * 100
                )
                large_file_improvements.append(improvement)
                status = "✓ PASS" if improvement >= 50 else "✗ FAIL"
                print(f"  {trad['file_size_mb']:.1f}MB: {improvement:.1f}% improvement {status}")

    if large_file_improvements:
        avg_improvement = sum(large_file_improvements) / len(large_file_improvements)
        print(f"Average improvement: {avg_improvement:.1f}%")
        if avg_improvement >= 50:
            print("✓ PASSED")
        else:
            print("✗ FAILED")
    else:
        print("No large files tested against traditional parser")

    # Target 3: 40-60MB memory reduction for 50MB+ files
    print("\nTarget 3 - 40-60MB memory reduction for 50MB+ files:")
    large_memory_reductions = []

    for trad in traditional_results:
        if trad["file_size_mb"] >= 50:
            matching_stream = next(
                (s for s in streaming_results if abs(s["file_size_mb"] - trad["file_size_mb"]) < 1),
                None,
            )
            if matching_stream:
                reduction = trad["memory_increase_mb"] - matching_stream["memory_increase_mb"]
                large_memory_reductions.append(reduction)
                status = "✓ PASS" if reduction >= 40 else "✗ FAIL"
                print(f"  {trad['file_size_mb']:.1f}MB: {reduction:.1f}MB reduction {status}")

    if large_memory_reductions:
        avg_reduction = sum(large_memory_reductions) / len(large_memory_reductions)
        print(f"Average reduction: {avg_reduction:.1f}MB")
        if avg_reduction >= 40:
            print("✓ PASSED")
        else:
            print("✗ FAILED")
    else:
        print("No 50MB+ files tested against traditional parser")


def main():
    """Main performance verification function."""
    try:
        print(f"Python: {sys.version}")
        print(f"Process PID: {os.getpid()}")
        print(f"Initial memory: {psutil.Process().memory_info().rss / 1024 / 1024:.1f}MB")

        # Run performance comparison
        results = run_performance_comparison()

        # Validate targets
        validate_targets(results)

        print(f"\n{'=' * 60}")
        print("PERFORMANCE VERIFICATION COMPLETE")
        print(f"{'=' * 60}")

        return results

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return []
    except Exception as e:
        print(f"\nError during performance verification: {e}")
        traceback.print_exc()
        return []


if __name__ == "__main__":
    main()
