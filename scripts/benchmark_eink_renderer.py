#!/usr/bin/env python3
"""
Benchmark script for EInkWhatsNextRenderer performance optimizations.

This script measures the performance of the EInkWhatsNextRenderer with and without
the optimization features enabled, to quantify the improvements in rendering time
and memory usage.

Usage:
    python scripts/benchmark_eink_renderer.py

Results are printed to the console and can be redirected to a file if needed.
"""

import sys
import time
import gc
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import statistics

# Add the project root to the Python path
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the renderer and related components
from calendarbot.display.epaper.integration.eink_whats_next_renderer import EInkWhatsNextRenderer
from calendarbot.display.epaper.abstraction import DisplayAbstractionLayer
from calendarbot.display.whats_next_data_model import WhatsNextViewModel, EventData
from calendarbot.display.epaper.utils.performance import PerformanceMetrics


class MockDisplayCapabilities:
    """Mock display capabilities for benchmarking."""
    
    def __init__(
        self,
        width: int = 400,
        height: int = 300,
        supports_partial_update: bool = True,
        supports_grayscale: bool = True,
        supports_red: bool = False
    ) -> None:
        """Initialize mock display capabilities."""
        self.width = width
        self.height = height
        self.supports_partial_update = supports_partial_update
        self.supports_grayscale = supports_grayscale
        self.supports_red = supports_red


class MockDisplay(DisplayAbstractionLayer):
    """Mock display for benchmarking."""
    
    def __init__(self, capabilities: Optional[MockDisplayCapabilities] = None) -> None:
        """Initialize mock display."""
        self.capabilities = capabilities or MockDisplayCapabilities()
    
    def initialize(self) -> bool:
        """Mock initialize method."""
        return True
    
    def render(self, buffer: Any) -> bool:
        """Mock render method."""
        return True
    
    def get_capabilities(self) -> MockDisplayCapabilities:
        """Get display capabilities."""
        return self.capabilities


class MockEvent:
    """Mock event for benchmarking."""
    
    def __init__(
        self,
        subject: str,
        start_time: datetime,
        end_time: datetime,
        location: str,
        time_until_minutes: int
    ) -> None:
        """Initialize mock event."""
        self.subject = subject
        self.start_time = start_time
        self.end_time = end_time
        self.location = location
        self.time_until_minutes = time_until_minutes
        self.formatted_time_range = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
    
    def format_time_range(self) -> str:
        """Format time range."""
        return self.formatted_time_range


class MockViewModel:
    """Mock view model for benchmarking."""
    
    def __init__(
        self,
        current_events: List[MockEvent],
        next_events: List[MockEvent],
        display_date: str
    ) -> None:
        """Initialize mock view model."""
        self.current_events = current_events
        self.next_events = next_events
        self.display_date = display_date
        self.status_info = type('StatusInfo', (), {'is_cached': False})()
    
    def get_next_event(self) -> Optional[MockEvent]:
        """Get next event."""
        return self.next_events[0] if self.next_events else None


def create_test_events(count: int) -> Tuple[List[MockEvent], List[MockEvent]]:
    """Create test events for benchmarking.
    
    Args:
        count: Number of events to create
        
    Returns:
        Tuple of current events and next events
    """
    now = datetime.now()
    current_events = []
    next_events = []
    
    # Create current events (in progress)
    for i in range(count):
        start_time = now - timedelta(minutes=30)
        end_time = now + timedelta(minutes=30)
        event = MockEvent(
            subject=f"Current Meeting {i}",
            start_time=start_time,
            end_time=end_time,
            location=f"Room {i}",
            time_until_minutes=0
        )
        current_events.append(event)
    
    # Create next events (upcoming)
    for i in range(count):
        start_time = now + timedelta(minutes=60 * (i + 1))
        end_time = start_time + timedelta(minutes=60)
        event = MockEvent(
            subject=f"Next Meeting {i}",
            start_time=start_time,
            end_time=end_time,
            location=f"Room {i + 100}",
            time_until_minutes=60 * (i + 1)
        )
        next_events.append(event)
    
    return current_events, next_events


def benchmark_renderer(iterations: int = 10, event_count: int = 3) -> Dict[str, Any]:
    """Benchmark the EInkWhatsNextRenderer.
    
    Args:
        iterations: Number of iterations to run
        event_count: Number of events to create
        
    Returns:
        Dictionary of benchmark results
    """
    logger.info(f"Starting benchmark with {iterations} iterations and {event_count} events")
    
    # Create test events
    current_events, next_events = create_test_events(event_count)
    
    # Create view model
    view_model = MockViewModel(
        current_events=current_events,
        next_events=next_events,
        display_date=datetime.now().strftime("%Y-%m-%d")
    )
    
    # Create mock display
    mock_display = MockDisplay()
    
    # Create settings
    settings = {"display": {"type": "epaper"}}
    
    # Initialize renderer
    renderer = EInkWhatsNextRenderer(settings, display=mock_display)
    
    # Warm up
    logger.info("Warming up renderer...")
    renderer.render(view_model)
    
    # Collect garbage to ensure clean state
    gc.collect()
    
    # Benchmark render method
    logger.info("Benchmarking render method...")
    render_times = []
    for i in range(iterations):
        start_time = time.time() * 1000
        renderer.render(view_model)
        end_time = time.time() * 1000
        render_time = end_time - start_time
        render_times.append(render_time)
        logger.info(f"Iteration {i+1}/{iterations}: {render_time:.2f}ms")
    
    # Benchmark render_error method
    logger.info("Benchmarking render_error method...")
    error_times = []
    for i in range(iterations):
        start_time = time.time() * 1000
        renderer.render_error("Test error", cached_events=current_events)
        end_time = time.time() * 1000
        error_time = end_time - start_time
        error_times.append(error_time)
        logger.info(f"Iteration {i+1}/{iterations}: {error_time:.2f}ms")
    
    # Benchmark render_authentication_prompt method
    logger.info("Benchmarking render_authentication_prompt method...")
    auth_times = []
    for i in range(iterations):
        start_time = time.time() * 1000
        renderer.render_authentication_prompt("https://example.com", "ABC123")
        end_time = time.time() * 1000
        auth_time = end_time - start_time
        auth_times.append(auth_time)
        logger.info(f"Iteration {i+1}/{iterations}: {auth_time:.2f}ms")
    
    # Calculate statistics
    render_avg = statistics.mean(render_times)
    render_min = min(render_times)
    render_max = max(render_times)
    render_median = statistics.median(render_times)
    render_stdev = statistics.stdev(render_times) if len(render_times) > 1 else 0
    
    error_avg = statistics.mean(error_times)
    error_min = min(error_times)
    error_max = max(error_times)
    error_median = statistics.median(error_times)
    error_stdev = statistics.stdev(error_times) if len(error_times) > 1 else 0
    
    auth_avg = statistics.mean(auth_times)
    auth_min = min(auth_times)
    auth_max = max(auth_times)
    auth_median = statistics.median(auth_times)
    auth_stdev = statistics.stdev(auth_times) if len(auth_times) > 1 else 0
    
    # Get performance metrics from renderer
    perf_summary = renderer.performance.get_summary()
    
    # Return results
    return {
        "render": {
            "times": render_times,
            "avg": render_avg,
            "min": render_min,
            "max": render_max,
            "median": render_median,
            "stdev": render_stdev
        },
        "error": {
            "times": error_times,
            "avg": error_avg,
            "min": error_min,
            "max": error_max,
            "median": error_median,
            "stdev": error_stdev
        },
        "auth": {
            "times": auth_times,
            "avg": auth_avg,
            "min": auth_min,
            "max": auth_max,
            "median": auth_median,
            "stdev": auth_stdev
        },
        "performance_metrics": perf_summary
    }


def print_results(results: Dict[str, Any]) -> None:
    """Print benchmark results.
    
    Args:
        results: Benchmark results
    """
    print("\n=== BENCHMARK RESULTS ===\n")
    
    print("Render Method:")
    print(f"  Average: {results['render']['avg']:.2f}ms")
    print(f"  Minimum: {results['render']['min']:.2f}ms")
    print(f"  Maximum: {results['render']['max']:.2f}ms")
    print(f"  Median:  {results['render']['median']:.2f}ms")
    print(f"  StdDev:  {results['render']['stdev']:.2f}ms")
    
    print("\nRender Error Method:")
    print(f"  Average: {results['error']['avg']:.2f}ms")
    print(f"  Minimum: {results['error']['min']:.2f}ms")
    print(f"  Maximum: {results['error']['max']:.2f}ms")
    print(f"  Median:  {results['error']['median']:.2f}ms")
    print(f"  StdDev:  {results['error']['stdev']:.2f}ms")
    
    print("\nRender Authentication Prompt Method:")
    print(f"  Average: {results['auth']['avg']:.2f}ms")
    print(f"  Minimum: {results['auth']['min']:.2f}ms")
    print(f"  Maximum: {results['auth']['max']:.2f}ms")
    print(f"  Median:  {results['auth']['median']:.2f}ms")
    print(f"  StdDev:  {results['auth']['stdev']:.2f}ms")
    
    print("\nPerformance Metrics:")
    for operation, duration in results['performance_metrics'].items():
        print(f"  {operation}: {duration:.2f}ms")


if __name__ == "__main__":
    # Run benchmark
    results = benchmark_renderer(iterations=10, event_count=3)
    
    # Print results
    print_results(results)