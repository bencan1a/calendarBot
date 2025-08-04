#!/usr/bin/env python3
"""
Benchmark script for comparing PIL drawing vs HTML-to-PNG conversion for e-paper display.

This script benchmarks the performance and memory usage of the two rendering approaches:
1. Traditional PIL drawing operations
2. HTML-to-PNG conversion

It generates sample data and renders it using both approaches, then compares the results.

Usage:
    python scripts/benchmark_html_renderer.py [--iterations ITERATIONS] [--output OUTPUT_DIR]

Options:
    --iterations ITERATIONS  Number of iterations for benchmarking (default: 5)
    --output OUTPUT_DIR      Directory to save output files (default: current directory)
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
from typing import Dict, List, Optional, Tuple

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import memory_profiler for memory usage tracking
try:
    import memory_profiler
    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False
    logger.warning("memory_profiler not available. Install with: pip install memory_profiler")

# Try to import the required components
try:
    from calendarbot.cache.models import CachedEvent
    from calendarbot.display.epaper.integration.eink_whats_next_renderer import EInkWhatsNextRenderer
    from calendarbot.display.epaper.utils.html_to_png import is_html2image_available
    from calendarbot.display.whats_next_data_model import EventData, StatusInfo, WhatsNextViewModel
    from calendarbot.display.whats_next_logic import WhatsNextLogic
except ImportError as e:
    logger.error(f"Failed to import required components: {e}")
    sys.exit(1)


def create_mock_settings():
    """Create mock settings for testing."""
    class MockSettings:
        def __init__(self):
            self.web_layout = "whats-next-view"
            self.debug = False
    
    return MockSettings()


def create_sample_events() -> List[CachedEvent]:
    """Create sample events for testing."""
    now = datetime.now()
    
    # Current event (happening now)
    current_event = CachedEvent(
        id="1",
        subject="Team Meeting",
        start_dt=now - timedelta(minutes=30),
        end_dt=now + timedelta(minutes=30),
        location_display_name="Conference Room A",
        is_all_day=False,
    )
    
    # Upcoming events
    upcoming_events = [
        CachedEvent(
            id="2",
            subject="Project Review",
            start_dt=now + timedelta(hours=1),
            end_dt=now + timedelta(hours=2),
            location_display_name="Conference Room B",
            is_all_day=False,
        ),
        CachedEvent(
            id="3",
            subject="Client Meeting",
            start_dt=now + timedelta(hours=3),
            end_dt=now + timedelta(hours=4),
            location_display_name="Virtual",
            is_all_day=False,
        ),
        CachedEvent(
            id="4",
            subject="Team Lunch",
            start_dt=now + timedelta(hours=5),
            end_dt=now + timedelta(hours=6),
            location_display_name="Cafeteria",
            is_all_day=False,
        ),
    ]
    
    return [current_event] + upcoming_events


def create_sample_view_model() -> WhatsNextViewModel:
    """Create a sample view model for testing."""
    # Create sample events
    events = create_sample_events()
    
    # Create status info
    status_info = StatusInfo(
        last_update=datetime.now(),
        is_cached=False,
        connection_status="Connected",
        relative_description="Today",
        interactive_mode=False,
        selected_date="Monday, August 4, 2025",
    )
    
    # Create event data objects
    current_events = [
        EventData(
            subject=events[0].subject,
            location=events[0].location_display_name,
            start_time=events[0].start_dt.strftime("%I:%M %p"),
            end_time=events[0].end_dt.strftime("%I:%M %p"),
            formatted_time_range=f"{events[0].start_dt.strftime('%I:%M %p')} - {events[0].end_dt.strftime('%I:%M %p')}",
            duration_minutes=60,
            time_until_minutes=None,
        )
    ]
    
    next_events = [
        EventData(
            subject=events[1].subject,
            location=events[1].location_display_name,
            start_time=events[1].start_dt.strftime("%I:%M %p"),
            end_time=events[1].end_dt.strftime("%I:%M %p"),
            formatted_time_range=f"{events[1].start_dt.strftime('%I:%M %p')} - {events[1].end_dt.strftime('%I:%M %p')}",
            duration_minutes=60,
            time_until_minutes=60,
        )
    ]
    
    later_events = [
        EventData(
            subject=events[2].subject,
            location=events[2].location_display_name,
            start_time=events[2].start_dt.strftime("%I:%M %p"),
            end_time=events[2].end_dt.strftime("%I:%M %p"),
            formatted_time_range=f"{events[2].start_dt.strftime('%I:%M %p')} - {events[2].end_dt.strftime('%I:%M %p')}",
            duration_minutes=60,
            time_until_minutes=180,
        ),
        EventData(
            subject=events[3].subject,
            location=events[3].location_display_name,
            start_time=events[3].start_dt.strftime("%I:%M %p"),
            end_time=events[3].end_dt.strftime("%I:%M %p"),
            formatted_time_range=f"{events[3].start_dt.strftime('%I:%M %p')} - {events[3].end_dt.strftime('%I:%M %p')}",
            duration_minutes=60,
            time_until_minutes=300,
        ),
    ]
    
    # Create view model
    view_model = WhatsNextViewModel(
        current_events=current_events,
        next_events=next_events,
        later_events=later_events,
        status_info=status_info,
        current_time=datetime.now(),
        display_date="Monday, August 4, 2025",
    )
    
    # Add helper method for compatibility
    def get_next_event():
        return next_events[0] if next_events else None
    
    view_model.get_next_event = get_next_event
    
    return view_model


def benchmark_pil_rendering(renderer: EInkWhatsNextRenderer, view_model: WhatsNextViewModel) -> Dict:
    """
    Benchmark the PIL rendering approach.
    
    Args:
        renderer: EInkWhatsNextRenderer instance
        view_model: View model to render
        
    Returns:
        Dictionary with benchmark results
    """
    results = {
        'rendering_time_ms': 0,
        'memory_usage_mb': 0,
        'success': False,
    }
    
    # Disable HTML conversion for this test
    original_html_converter = renderer.html_converter
    renderer.html_converter = None
    
    try:
        # Measure rendering time
        start_time = time.time() * 1000
        
        # Measure memory usage if memory_profiler is available
        if MEMORY_PROFILER_AVAILABLE:
            memory_usage = memory_profiler.memory_usage((
                renderer._render_full_image,
                (view_model,),
                {}
            ))
            results['memory_usage_mb'] = max(memory_usage) - memory_usage[0]
            image = renderer._render_full_image(view_model)
        else:
            # If memory_profiler is not available, just render normally
            image = renderer._render_full_image(view_model)
        
        end_time = time.time() * 1000
        results['rendering_time_ms'] = end_time - start_time
        
        # Check if rendering was successful
        if image:
            results['success'] = True
        
        return results
    
    finally:
        # Restore HTML converter
        renderer.html_converter = original_html_converter


def benchmark_html_rendering(renderer: EInkWhatsNextRenderer, view_model: WhatsNextViewModel) -> Dict:
    """
    Benchmark the HTML-to-PNG rendering approach.
    
    Args:
        renderer: EInkWhatsNextRenderer instance
        view_model: View model to render
        
    Returns:
        Dictionary with benchmark results
    """
    results = {
        'rendering_time_ms': 0,
        'memory_usage_mb': 0,
        'success': False,
    }
    
    # Skip if HTML conversion is not available
    if not is_html2image_available() or renderer.html_converter is None:
        logger.warning("HTML-to-PNG conversion not available, skipping benchmark")
        return results
    
    try:
        # Clear HTML render cache to ensure fresh rendering
        renderer._html_render_cache.clear()
        
        # Measure rendering time
        start_time = time.time() * 1000
        
        # Measure memory usage if memory_profiler is available
        if MEMORY_PROFILER_AVAILABLE:
            memory_usage = memory_profiler.memory_usage((
                renderer._render_using_html_conversion,
                (view_model,),
                {}
            ))
            results['memory_usage_mb'] = max(memory_usage) - memory_usage[0]
            image = renderer._render_using_html_conversion(view_model)
        else:
            # If memory_profiler is not available, just render normally
            image = renderer._render_using_html_conversion(view_model)
        
        end_time = time.time() * 1000
        results['rendering_time_ms'] = end_time - start_time
        
        # Check if rendering was successful
        if image:
            results['success'] = True
        
        return results
    
    except Exception as e:
        logger.error(f"Error in HTML rendering benchmark: {e}")
        return results


def run_benchmarks(iterations: int, output_dir: Path) -> Tuple[List[Dict], List[Dict]]:
    """
    Run benchmarks for both rendering approaches.
    
    Args:
        iterations: Number of iterations for benchmarking
        output_dir: Directory to save output files
        
    Returns:
        Tuple of (pil_results, html_results)
    """
    # Create renderer
    settings = create_mock_settings()
    renderer = EInkWhatsNextRenderer(settings)
    
    # Create view model
    view_model = create_sample_view_model()
    
    # Run benchmarks
    pil_results = []
    html_results = []
    
    logger.info(f"Running {iterations} iterations of benchmarks...")
    
    for i in range(iterations):
        logger.info(f"Iteration {i+1}/{iterations}")
        
        # Benchmark PIL rendering
        logger.info("Benchmarking PIL rendering...")
        pil_result = benchmark_pil_rendering(renderer, view_model)
        pil_results.append(pil_result)
        logger.info(f"PIL rendering: {pil_result['rendering_time_ms']:.2f}ms, {pil_result['memory_usage_mb']:.2f}MB")
        
        # Benchmark HTML rendering
        logger.info("Benchmarking HTML-to-PNG rendering...")
        html_result = benchmark_html_rendering(renderer, view_model)
        html_results.append(html_result)
        logger.info(f"HTML rendering: {html_result['rendering_time_ms']:.2f}ms, {html_result['memory_usage_mb']:.2f}MB")
    
    # Save sample images
    try:
        # Save PIL rendering
        pil_image = renderer._render_full_image(view_model)
        pil_image.save(output_dir / "pil_rendering.png")
        logger.info(f"Saved PIL rendering to {output_dir / 'pil_rendering.png'}")
        
        # Save HTML rendering if available
        if renderer.html_converter is not None:
            html_image = renderer._render_using_html_conversion(view_model)
            html_image.save(output_dir / "html_rendering.png")
            logger.info(f"Saved HTML rendering to {output_dir / 'html_rendering.png'}")
    except Exception as e:
        logger.warning(f"Failed to save sample images: {e}")
    
    # Clean up
    if hasattr(renderer, 'cleanup'):
        renderer.cleanup()
    
    return pil_results, html_results


def calculate_statistics(results: List[Dict]) -> Dict:
    """
    Calculate statistics from benchmark results.
    
    Args:
        results: List of benchmark results
        
    Returns:
        Dictionary with statistics
    """
    if not results:
        return {
            'avg_time_ms': 0,
            'min_time_ms': 0,
            'max_time_ms': 0,
            'avg_memory_mb': 0,
            'min_memory_mb': 0,
            'max_memory_mb': 0,
            'success_rate': 0,
        }
    
    # Calculate statistics
    times = [r['rendering_time_ms'] for r in results]
    memories = [r['memory_usage_mb'] for r in results]
    successes = [r['success'] for r in results]
    
    return {
        'avg_time_ms': sum(times) / len(times),
        'min_time_ms': min(times),
        'max_time_ms': max(times),
        'avg_memory_mb': sum(memories) / len(memories),
        'min_memory_mb': min(memories),
        'max_memory_mb': max(memories),
        'success_rate': sum(successes) / len(successes),
    }


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Benchmark PIL drawing vs HTML-to-PNG conversion')
    parser.add_argument('--iterations', type=int, default=5, help='Number of iterations')
    parser.add_argument('--output', type=str, default='.', help='Output directory')
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    logger.info("Benchmarking PIL drawing vs HTML-to-PNG conversion")
    
    # Check if html2image is available
    if not is_html2image_available():
        logger.warning("html2image is not available. Only PIL rendering will be benchmarked.")
    
    # Run benchmarks
    pil_results, html_results = run_benchmarks(args.iterations, output_dir)
    
    # Calculate statistics
    pil_stats = calculate_statistics(pil_results)
    html_stats = calculate_statistics(html_results)
    
    # Print results
    logger.info("\nBenchmark Results:")
    logger.info("\nPIL Rendering:")
    logger.info(f"  Average Time: {pil_stats['avg_time_ms']:.2f}ms")
    logger.info(f"  Min/Max Time: {pil_stats['min_time_ms']:.2f}ms / {pil_stats['max_time_ms']:.2f}ms")
    logger.info(f"  Average Memory: {pil_stats['avg_memory_mb']:.2f}MB")
    logger.info(f"  Min/Max Memory: {pil_stats['min_memory_mb']:.2f}MB / {pil_stats['max_memory_mb']:.2f}MB")
    logger.info(f"  Success Rate: {pil_stats['success_rate'] * 100:.2f}%")
    
    logger.info("\nHTML-to-PNG Rendering:")
    logger.info(f"  Average Time: {html_stats['avg_time_ms']:.2f}ms")
    logger.info(f"  Min/Max Time: {html_stats['min_time_ms']:.2f}ms / {html_stats['max_time_ms']:.2f}ms")
    logger.info(f"  Average Memory: {html_stats['avg_memory_mb']:.2f}MB")
    logger.info(f"  Min/Max Memory: {html_stats['min_memory_mb']:.2f}MB / {html_stats['max_memory_mb']:.2f}MB")
    logger.info(f"  Success Rate: {html_stats['success_rate'] * 100:.2f}%")
    
    # Compare results
    if html_stats['avg_time_ms'] > 0:
        time_diff = (html_stats['avg_time_ms'] - pil_stats['avg_time_ms']) / pil_stats['avg_time_ms'] * 100
        memory_diff = (html_stats['avg_memory_mb'] - pil_stats['avg_memory_mb']) / pil_stats['avg_memory_mb'] * 100
        
        logger.info("\nComparison (HTML vs PIL):")
        logger.info(f"  Time Difference: {time_diff:.2f}% ({'slower' if time_diff > 0 else 'faster'})")
        logger.info(f"  Memory Difference: {memory_diff:.2f}% ({'more' if memory_diff > 0 else 'less'})")
    
    logger.info("\nBenchmark completed successfully")


if __name__ == "__main__":
    main()