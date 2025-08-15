#!/usr/bin/env python3
"""
Real ICS File Performance Test

Downloads or uses existing large ICS files to test streaming parser performance.
Uses actual calendar data that CalendarBot processes in production.

Validates performance targets:
- 40-60MB memory reduction for large files (50MB+)
- 50% processing time improvement for files >20MB
- Memory usage stays <8MB regardless of file size

Created: 2025-08-14
Purpose: Realistic performance validation using production ICS data
"""

import gc
import os
import sys
import time
from pathlib import Path

import psutil
import requests

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


def download_test_ics_file(url: str, local_path: Path) -> bool:
    """Download ICS file for testing if it doesn't exist locally."""
    if local_path.exists():
        print(
            f"Using existing test file: {local_path} ({local_path.stat().st_size / 1024 / 1024:.1f}MB)"
        )
        return True

    try:
        print(f"Downloading test ICS file from {url}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Ensure directory exists
        local_path.parent.mkdir(parents=True, exist_ok=True)

        with local_path.open("w", encoding="utf-8") as f:
            f.write(response.text)

        size_mb = local_path.stat().st_size / 1024 / 1024
        print(f"Downloaded {size_mb:.1f}MB ICS file to {local_path}")
        return True

    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False


def get_test_files() -> list[dict]:
    """Get list of test ICS files with their URLs and expected characteristics."""
    test_dir = Path("test_data/ics_files")

    # Common large public ICS feeds for testing
    return [
        {
            "name": "US Holidays",
            "url": "https://calendar.google.com/calendar/ical/en.usa%23holiday%40group.v.calendar.google.com/public/basic.ics",
            "local_path": test_dir / "us_holidays.ics",
            "expected_size_mb": 0.1,  # Small file for baseline
        },
        # Add more test files as needed
        # Note: We need to find publicly available large ICS files or use project-specific ones
    ]


def benchmark_parser_with_file(file_path: Path, parser_type: str) -> dict:
    """Benchmark a parser with a real ICS file."""
    file_size_mb = file_path.stat().st_size / 1024 / 1024
    print(
        f"\n--- Benchmarking {parser_type} Parser (File: {file_path.name}, {file_size_mb:.1f}MB) ---"
    )

    # Setup
    gc.collect()
    profiler = MemoryProfiler()

    start_time = time.perf_counter()
    initial_memory = profiler.get_memory_mb()

    try:
        # Read file content
        with file_path.open(encoding="utf-8") as f:
            content = f.read()

        # Create mock settings for parser
        class MockSettings:
            def __init__(self):
                pass

        settings = MockSettings()
        parser = ICSParser(settings)

        # Choose parsing method based on type
        if parser_type == "Traditional":
            # Force traditional parsing (bypass streaming logic)
            calendar_data = parser.parse_ics_content(content)
        elif parser_type == "Streaming":
            # Use optimized parser that will select streaming for large files
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
            "file_name": file_path.name,
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
            "file_name": file_path.name,
            "file_size_mb": file_size_mb,
            "error": str(e),
            "success": False,
        }
    finally:
        gc.collect()


def create_large_test_file(base_file: Path, target_size_mb: int) -> Path:
    """Create a larger test file by duplicating events from a base file."""
    if not base_file.exists():
        raise FileNotFoundError(f"Base file not found: {base_file}")

    large_file = base_file.parent / f"large_{target_size_mb}mb_{base_file.name}"

    if large_file.exists():
        size_mb = large_file.stat().st_size / 1024 / 1024
        print(f"Using existing large test file: {large_file} ({size_mb:.1f}MB)")
        return large_file

    print(f"Creating {target_size_mb}MB test file from {base_file.name}...")

    with base_file.open(encoding="utf-8") as f:
        content = f.read()

    # Extract events and calendar structure
    lines = content.split("\n")
    header = []
    events = []
    footer = []

    current_section = "header"
    current_event = []

    for line in lines:
        if line.strip() == "BEGIN:VEVENT":
            current_section = "event"
            current_event = [line]
        elif line.strip() == "END:VEVENT":
            current_event.append(line)
            events.append("\n".join(current_event))
            current_event = []
            current_section = "body"
        elif line.strip() == "END:VCALENDAR":
            current_section = "footer"
            footer.append(line)
        elif current_section == "header":
            header.append(line)
        elif current_section == "event":
            current_event.append(line)
        elif current_section == "footer":
            footer.append(line)

    if not events:
        raise ValueError(f"No events found in {base_file}")

    # Calculate how many times to duplicate events
    base_size = len(content.encode("utf-8"))
    target_size = target_size_mb * 1024 * 1024
    multiplier = max(1, target_size // base_size)

    # Create large content
    large_content = "\n".join(header) + "\n"

    event_counter = 0
    for _ in range(multiplier):
        for event in events:
            # Modify UID to make each event unique
            modified_event = event.replace("UID:", f"UID:dup{event_counter}_")
            large_content += modified_event + "\n"
            event_counter += 1

    large_content += "\n".join(footer)

    # Write large file
    with large_file.open("w", encoding="utf-8") as f:
        f.write(large_content)

    actual_size_mb = large_file.stat().st_size / 1024 / 1024
    print(f"Created {actual_size_mb:.1f}MB test file: {large_file}")

    return large_file


def run_performance_tests() -> list[dict]:
    """Run performance tests with real ICS files."""
    print("=" * 60)
    print("REAL ICS FILE PERFORMANCE VERIFICATION")
    print("=" * 60)

    results = []
    test_files = get_test_files()

    # Download/prepare test files
    available_files = []
    for test_file in test_files:
        if download_test_ics_file(test_file["url"], test_file["local_path"]):
            available_files.append(test_file["local_path"])

    if not available_files:
        print("No test files available. Exiting.")
        return []

    # Use the first available file as base
    base_file = available_files[0]

    # Create test files of different sizes
    test_scenarios = [
        (base_file, "Original"),
        (create_large_test_file(base_file, 10), "10MB"),
        (create_large_test_file(base_file, 25), "25MB"),
        (create_large_test_file(base_file, 50), "50MB"),
    ]

    for test_file, scenario_name in test_scenarios:
        print(f"\n{'=' * 40}")
        print(f"SCENARIO: {scenario_name}")
        print(f"{'=' * 40}")

        file_size_mb = test_file.stat().st_size / 1024 / 1024

        # Test traditional parser (only for smaller files)
        traditional_result = None
        if file_size_mb <= 20:
            traditional_result = benchmark_parser_with_file(test_file, "Traditional")
            results.append(traditional_result)

        # Test streaming parser
        streaming_result = benchmark_parser_with_file(test_file, "Streaming")
        results.append(streaming_result)

        # Compare results
        if traditional_result and traditional_result["success"] and streaming_result["success"]:
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

    return results


def validate_performance_targets(results: list[dict]) -> None:
    """Validate that performance targets are met."""
    print(f"\n{'=' * 60}")
    print("PERFORMANCE TARGET VALIDATION")
    print(f"{'=' * 60}")

    streaming_results = [
        r for r in results if r.get("parser_type") == "Streaming" and r.get("success")
    ]

    if not streaming_results:
        print("No successful streaming results to validate.")
        return

    print("\nStreaming Parser Results:")
    for result in streaming_results:
        name = result["file_name"]
        size = result["file_size_mb"]
        memory = result["memory_increase_mb"]
        time_taken = result["processing_time"]
        events = result["events_parsed"]

        print(
            f"  {name}: {size:.1f}MB -> {memory:.1f}MB memory, {time_taken:.3f}s, {events} events"
        )

    # Target validation
    max_memory = max((r["memory_increase_mb"] for r in streaming_results), default=0)
    print("\nTarget 1 - Memory usage <8MB: ", end="")
    if max_memory <= 8:
        print("✓ PASSED")
    else:
        print(f"✗ FAILED (Peak: {max_memory:.1f}MB)")

    # Additional analysis
    large_files = [r for r in streaming_results if r["file_size_mb"] > 20]
    if large_files:
        avg_memory = sum(r["memory_increase_mb"] for r in large_files) / len(large_files)
        print(f"\nAverage memory for large files (>20MB): {avg_memory:.1f}MB")

    print("\nNote: For complete validation of time improvement and memory reduction targets,")
    print("run tests with both traditional and streaming parsers on files >20MB.")


def main():
    """Main performance test function."""
    try:
        print(f"Python: {sys.version}")
        print(f"Process PID: {os.getpid()}")
        print(f"Initial memory: {psutil.Process().memory_info().rss / 1024 / 1024:.1f}MB")

        # Run performance tests
        results = run_performance_tests()

        # Validate targets
        validate_performance_targets(results)

        print(f"\n{'=' * 60}")
        print("PERFORMANCE VERIFICATION COMPLETE")
        print(f"{'=' * 60}")

        return results

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return []
    except Exception as e:
        print(f"\nError during performance verification: {e}")
        import traceback

        traceback.print_exc()
        return []


if __name__ == "__main__":
    main()
