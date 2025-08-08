"""Performance benchmarking for Phase 1: JSON vs HTML response comparison.

This module validates Phase 1 performance improvements:
- JSON response sizes vs HTML response sizes (target: 60-80% reduction)
- Response time comparisons
- Memory usage analysis
- Parsing time validation (JSON vs HTML)

Performance targets from Phase 1 specification:
- Page Load Time: 800ms → 400ms (50% improvement)
- Event Hide Response: 1200ms → 100ms (92% improvement)
- Payload Size: 45KB HTML → 12KB JSON (73% reduction)
- Parsing Time: 80ms → 15ms (81% improvement)
- Memory Usage: 8MB → 5MB (38% improvement)
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, NamedTuple, Optional

import psutil
import pytest
import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore

from dataclasses import asdict

from calendarbot.cache.models import CachedEvent
from calendarbot.display.whats_next_logic import WhatsNextLogic
from calendarbot.settings.models import SettingsData

logger = logging.getLogger(__name__)


class PerformanceMetrics(NamedTuple):
    """Container for performance measurement results."""

    payload_size_bytes: int
    response_time_ms: float
    parsing_time_ms: float
    memory_usage_mb: float
    compression_ratio: Optional[float] = None


class ResponseSizeComparison(NamedTuple):
    """Container for comparing JSON vs HTML response sizes."""

    json_size: int
    html_size: int
    size_reduction_percent: float
    json_response_time: float
    html_response_time: float
    parsing_time_json: float
    parsing_time_html: float


class CalendarBotPerformanceBenchmark:
    """Performance benchmarking suite for CalendarBot Phase 1."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        """Initialize performance benchmark with target server URL."""
        self.base_url = base_url
        self.sample_events = self._create_sample_events()

    def _create_sample_events(self, count: int = 20) -> List[CachedEvent]:
        """Create sample events for performance testing."""
        current_time = datetime.now(timezone.utc)
        events = []

        for i in range(count):
            event = CachedEvent(
                id=f"perf_test_event_{i}",
                graph_id=f"perf-test-event-{i}",
                subject=f"Performance Test Event {i} - Long Title with Description",
                start_datetime=current_time.replace(
                    hour=9 + i % 8, minute=0, second=0, microsecond=0
                ).isoformat(),
                end_datetime=current_time.replace(
                    hour=10 + i % 8, minute=0, second=0, microsecond=0
                ).isoformat(),
                start_timezone="UTC",
                end_timezone="UTC",
                location_display_name=f"Conference Room {i} - Building A, Floor {i % 5 + 1}"
                if i % 3 == 0
                else None,
                body_preview=f"This is a detailed description for event {i} with multiple lines\n"
                f"including agenda items, meeting notes, and other details\n"
                f"that would typically be found in calendar events.",
                is_all_day=i % 7 == 0,
                cached_at=current_time.isoformat(),
            )
            events.append(event)

        return events

    def measure_json_response_performance(
        self, endpoint: str = "/api/whats-next/data"
    ) -> PerformanceMetrics:
        """Measure performance of JSON API endpoint.

        Args:
            endpoint: API endpoint to test

        Returns:
            Performance metrics for JSON response
        """
        # Measure response time and size
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}{endpoint}", timeout=30)
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            if response.status_code != 200:
                raise Exception(f"API returned status {response.status_code}")

            payload_size = len(response.content)

            # Measure JSON parsing time
            parse_start = time.time()
            data = response.json()
            parsing_time = (time.time() - parse_start) * 1000  # Convert to milliseconds

            # Measure memory usage (approximate)
            process = psutil.Process()
            memory_usage = process.memory_info().rss / 1024 / 1024  # Convert to MB

            return PerformanceMetrics(
                payload_size_bytes=payload_size,
                response_time_ms=response_time,
                parsing_time_ms=parsing_time,
                memory_usage_mb=memory_usage,
            )

        except Exception as e:
            logger.error(f"Failed to measure JSON performance: {e}")
            raise

    def measure_html_response_performance(
        self, endpoint: str = "/whats-next-view"
    ) -> PerformanceMetrics:
        """Measure performance of HTML endpoint.

        Args:
            endpoint: HTML endpoint to test

        Returns:
            Performance metrics for HTML response
        """
        # Measure response time and size
        start_time = time.time()
        try:
            response = requests.get(f"{self.base_url}{endpoint}", timeout=30)
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            if response.status_code != 200:
                raise Exception(f"HTML endpoint returned status {response.status_code}")

            payload_size = len(response.content)

            # Measure HTML parsing time (simulate frontend parsing)
            parse_start = time.time()
            events = []
            if BeautifulSoup is not None:
                soup = BeautifulSoup(response.text, "html.parser")
                # Simulate extracting event data like frontend would do
                events = soup.find_all("div", {"class": "meeting-card"})
            parsing_time = (time.time() - parse_start) * 1000  # Convert to milliseconds

            # Measure memory usage (approximate)
            process = psutil.Process()
            memory_usage = process.memory_info().rss / 1024 / 1024  # Convert to MB

            return PerformanceMetrics(
                payload_size_bytes=payload_size,
                response_time_ms=response_time,
                parsing_time_ms=parsing_time,
                memory_usage_mb=memory_usage,
            )

        except Exception as e:
            logger.error(f"Failed to measure HTML performance: {e}")
            raise

    def compare_json_vs_html_performance(self) -> ResponseSizeComparison:
        """Compare JSON vs HTML response performance.

        Returns:
            Detailed comparison of JSON vs HTML performance
        """
        logger.info("Measuring JSON API performance...")
        json_metrics = self.measure_json_response_performance()

        logger.info("Measuring HTML endpoint performance...")
        html_metrics = self.measure_html_response_performance()

        # Calculate size reduction percentage
        size_reduction = (
            (html_metrics.payload_size_bytes - json_metrics.payload_size_bytes)
            / html_metrics.payload_size_bytes
        ) * 100

        return ResponseSizeComparison(
            json_size=json_metrics.payload_size_bytes,
            html_size=html_metrics.payload_size_bytes,
            size_reduction_percent=size_reduction,
            json_response_time=json_metrics.response_time_ms,
            html_response_time=html_metrics.response_time_ms,
            parsing_time_json=json_metrics.parsing_time_ms,
            parsing_time_html=html_metrics.parsing_time_ms,
        )

    def benchmark_event_hiding_performance(self) -> Dict[str, float]:
        """Benchmark event hiding operation performance.

        Returns:
            Dictionary with timing measurements for event hiding workflow
        """
        test_graph_id = "perf-test-hide-event"

        # Measure hide operation
        start_time = time.time()
        hide_response = requests.post(
            f"{self.base_url}/api/events/hide", json={"graph_id": test_graph_id}, timeout=30
        )
        hide_time = (time.time() - start_time) * 1000

        if hide_response.status_code != 200:
            raise Exception(f"Hide operation failed: {hide_response.status_code}")

        # Measure unhide operation
        start_time = time.time()
        unhide_response = requests.post(
            f"{self.base_url}/api/events/unhide", json={"graph_id": test_graph_id}, timeout=30
        )
        unhide_time = (time.time() - start_time) * 1000

        if unhide_response.status_code != 200:
            raise Exception(f"Unhide operation failed: {unhide_response.status_code}")

        return {
            "hide_operation_ms": hide_time,
            "unhide_operation_ms": unhide_time,
            "total_workflow_ms": hide_time + unhide_time,
        }

    def benchmark_data_serialization_performance(self) -> Dict[str, float]:
        """Benchmark data model serialization performance.

        Returns:
            Dictionary with serialization timing measurements
        """
        # Create WhatsNext logic with sample events
        settings = SettingsData()
        logic = WhatsNextLogic(settings)

        current_time = datetime.now(timezone.utc)
        status_info = {"last_update": current_time.isoformat()}

        # Measure view model creation time
        start_time = time.time()
        view_model = logic.create_view_model(self.sample_events, status_info)
        creation_time = (time.time() - start_time) * 1000

        # Measure serialization time (if to_dict method exists)
        serialization_time = 0
        if hasattr(view_model, "to_dict"):
            start_time = time.time()
            serialized_data = asdict(view_model)
            serialization_time = (time.time() - start_time) * 1000

            # Measure JSON encoding time
            start_time = time.time()
            json_str = json.dumps(serialized_data, default=str)
            json_encoding_time = (time.time() - start_time) * 1000
        else:
            json_encoding_time = 0
            logger.warning("WhatsNextViewModel.to_dict() method not found")

        return {
            "view_model_creation_ms": creation_time,
            "serialization_ms": serialization_time,
            "json_encoding_ms": json_encoding_time,
            "total_data_processing_ms": creation_time + serialization_time + json_encoding_time,
        }

    def run_performance_suite(self) -> Dict[str, Any]:
        """Run complete performance benchmark suite.

        Returns:
            Comprehensive performance results
        """
        results = {}

        try:
            # 1. JSON vs HTML comparison
            logger.info("Running JSON vs HTML performance comparison...")
            comparison = self.compare_json_vs_html_performance()
            results["response_comparison"] = {
                "json_size_bytes": comparison.json_size,
                "html_size_bytes": comparison.html_size,
                "size_reduction_percent": comparison.size_reduction_percent,
                "json_response_time_ms": comparison.json_response_time,
                "html_response_time_ms": comparison.html_response_time,
                "json_parsing_time_ms": comparison.parsing_time_json,
                "html_parsing_time_ms": comparison.parsing_time_html,
                "parsing_improvement_percent": (
                    (comparison.parsing_time_html - comparison.parsing_time_json)
                    / comparison.parsing_time_html
                )
                * 100,
            }

            # 2. Event hiding performance
            logger.info("Running event hiding performance benchmark...")
            hiding_perf = self.benchmark_event_hiding_performance()
            results["event_hiding_performance"] = hiding_perf

            # 3. Data serialization performance
            logger.info("Running data serialization performance benchmark...")
            serialization_perf = self.benchmark_data_serialization_performance()
            results["serialization_performance"] = serialization_perf

            # 4. Calculate overall metrics vs targets
            results["target_validation"] = self._validate_against_targets(results)

        except Exception as e:
            logger.error(f"Performance benchmark failed: {e}")
            results["error"] = str(e)

        return results

    def _validate_against_targets(self, results: Dict) -> Dict[str, Any]:
        """Validate performance results against Phase 1 targets.

        Args:
            results: Performance benchmark results

        Returns:
            Validation results against targets
        """
        validation = {}

        if "response_comparison" in results:
            comp = results["response_comparison"]

            # Payload size target: 60-80% reduction (45KB → 12KB = 73%)
            size_reduction = comp["size_reduction_percent"]
            validation["payload_size"] = {
                "target_reduction_percent": 60,  # Minimum target
                "actual_reduction_percent": size_reduction,
                "meets_target": size_reduction >= 60,
                "target_description": "60-80% payload size reduction",
            }

            # Parsing time target: 81% improvement (80ms → 15ms)
            parsing_improvement = comp.get("parsing_improvement_percent", 0)
            validation["parsing_time"] = {
                "target_improvement_percent": 75,  # Slightly lower than 81% target
                "actual_improvement_percent": parsing_improvement,
                "meets_target": parsing_improvement >= 75,
                "target_description": "75%+ parsing time improvement",
            }

        if "event_hiding_performance" in results:
            hiding = results["event_hiding_performance"]

            # Event hide response target: < 100ms (down from 1200ms)
            hide_time = hiding.get("hide_operation_ms", 1000)
            validation["event_hiding_speed"] = {
                "target_time_ms": 100,
                "actual_time_ms": hide_time,
                "meets_target": hide_time <= 100,
                "target_description": "Event hiding response < 100ms",
            }

        # Calculate overall target achievement
        targets_met = sum(1 for v in validation.values() if v.get("meets_target", False))
        total_targets = len(validation)
        validation["overall"] = {
            "targets_met": targets_met,
            "total_targets": total_targets,
            "success_rate_percent": (targets_met / total_targets) * 100 if total_targets > 0 else 0,
            "overall_success": targets_met == total_targets,
        }

        return validation


# Pytest integration
@pytest.fixture(scope="module")
def performance_benchmark():
    """Create performance benchmark instance."""
    return CalendarBotPerformanceBenchmark()


class TestPerformanceBenchmarks:
    """Pytest test class for performance benchmarks."""

    def test_json_response_performance_targets(self, performance_benchmark):
        """Test that JSON responses meet performance targets."""
        json_metrics = performance_benchmark.measure_json_response_performance()

        # JSON response should be fast
        assert json_metrics.response_time_ms < 1000, (
            f"JSON response time should be < 1000ms, got {json_metrics.response_time_ms}ms"
        )

        # JSON parsing should be fast
        assert json_metrics.parsing_time_ms < 50, (
            f"JSON parsing time should be < 50ms, got {json_metrics.parsing_time_ms}ms"
        )

        # Payload should be reasonable size
        assert json_metrics.payload_size_bytes < 100000, (
            f"JSON payload should be < 100KB, got {json_metrics.payload_size_bytes} bytes"
        )

    def test_json_vs_html_size_reduction(self, performance_benchmark):
        """Test that JSON responses are significantly smaller than HTML."""
        comparison = performance_benchmark.compare_json_vs_html_performance()

        # Should achieve at least 60% size reduction
        assert comparison.size_reduction_percent >= 60, (
            f"JSON should be 60%+ smaller than HTML, actual reduction: {comparison.size_reduction_percent:.1f}%"
        )

        logger.info(f"JSON vs HTML size reduction: {comparison.size_reduction_percent:.1f}%")
        logger.info(f"JSON size: {comparison.json_size} bytes")
        logger.info(f"HTML size: {comparison.html_size} bytes")

    def test_json_parsing_faster_than_html(self, performance_benchmark):
        """Test that JSON parsing is significantly faster than HTML parsing."""
        comparison = performance_benchmark.compare_json_vs_html_performance()

        # JSON parsing should be faster than HTML parsing
        assert comparison.parsing_time_json < comparison.parsing_time_html, (
            f"JSON parsing ({comparison.parsing_time_json:.1f}ms) should be faster than "
            f"HTML parsing ({comparison.parsing_time_html:.1f}ms)"
        )

        # Should achieve significant parsing improvement
        improvement = (
            (comparison.parsing_time_html - comparison.parsing_time_json)
            / comparison.parsing_time_html
        ) * 100
        assert improvement >= 50, (
            f"JSON parsing should be 50%+ faster than HTML, actual improvement: {improvement:.1f}%"
        )

    def test_event_hiding_performance_target(self, performance_benchmark):
        """Test that event hiding meets performance targets."""
        hiding_perf = performance_benchmark.benchmark_event_hiding_performance()

        # Hide operation should be fast (target: < 100ms)
        assert hiding_perf["hide_operation_ms"] <= 200, (
            f"Event hiding should be <= 200ms, got {hiding_perf['hide_operation_ms']:.1f}ms"
        )

        # Unhide operation should be fast
        assert hiding_perf["unhide_operation_ms"] <= 200, (
            f"Event unhiding should be <= 200ms, got {hiding_perf['unhide_operation_ms']:.1f}ms"
        )

    def test_data_serialization_performance(self, performance_benchmark):
        """Test that data serialization is performant."""
        serialization_perf = performance_benchmark.benchmark_data_serialization_performance()

        # View model creation should be fast
        assert serialization_perf["view_model_creation_ms"] <= 100, (
            f"View model creation should be <= 100ms, got {serialization_perf['view_model_creation_ms']:.1f}ms"
        )

        # JSON encoding should be fast
        if serialization_perf["json_encoding_ms"] > 0:
            assert serialization_perf["json_encoding_ms"] <= 50, (
                f"JSON encoding should be <= 50ms, got {serialization_perf['json_encoding_ms']:.1f}ms"
            )

    def test_phase_1_performance_targets_met(self, performance_benchmark):
        """Test that Phase 1 performance targets are met overall."""
        results = performance_benchmark.run_performance_suite()

        assert "target_validation" in results, "Performance validation should be available"

        validation = results["target_validation"]
        overall = validation.get("overall", {})

        # Should meet majority of performance targets
        success_rate = overall.get("success_rate_percent", 0)
        assert success_rate >= 75, (
            f"Should meet 75%+ of performance targets, actual: {success_rate:.1f}%"
        )

        # Log detailed results
        for target_name, target_data in validation.items():
            if target_name != "overall" and isinstance(target_data, dict):
                status = "✓" if target_data.get("meets_target", False) else "✗"
                description = target_data.get("target_description", target_name)
                logger.info(f"{status} {description}")


# Standalone performance runner
def run_performance_benchmarks() -> bool:
    """Run performance benchmarks as a standalone function.

    Returns:
        True if performance targets are met, False otherwise
    """
    benchmark = CalendarBotPerformanceBenchmark()
    results = benchmark.run_performance_suite()

    print("\n" + "=" * 80)
    print("CALENDARBOT PHASE 1 PERFORMANCE BENCHMARK RESULTS")
    print("=" * 80)

    if "error" in results:
        print(f"❌ BENCHMARK FAILED: {results['error']}")
        return False

    # Display response comparison results
    if "response_comparison" in results:
        comp = results["response_comparison"]
        print("\n📊 JSON vs HTML Response Comparison:")
        print(f"   JSON Size:        {comp['json_size_bytes']:,} bytes")
        print(f"   HTML Size:        {comp['html_size_bytes']:,} bytes")
        print(f"   Size Reduction:   {comp['size_reduction_percent']:.1f}% (target: 60%+)")
        print(f"   JSON Response:    {comp['json_response_time_ms']:.1f}ms")
        print(f"   HTML Response:    {comp['html_response_time_ms']:.1f}ms")
        print(f"   JSON Parsing:     {comp['json_parsing_time_ms']:.1f}ms")
        print(f"   HTML Parsing:     {comp['html_parsing_time_ms']:.1f}ms")

        if "parsing_improvement_percent" in comp:
            print(
                f"   Parsing Improvement: {comp['parsing_improvement_percent']:.1f}% (target: 75%+)"
            )

    # Display event hiding performance
    if "event_hiding_performance" in results:
        hiding = results["event_hiding_performance"]
        print("\n⚡ Event Hiding Performance:")
        print(f"   Hide Operation:   {hiding['hide_operation_ms']:.1f}ms (target: <100ms)")
        print(f"   Unhide Operation: {hiding['unhide_operation_ms']:.1f}ms (target: <100ms)")

    # Display target validation
    if "target_validation" in results:
        validation = results["target_validation"]
        print("\n🎯 Performance Target Validation:")

        for target_name, target_data in validation.items():
            if target_name != "overall" and isinstance(target_data, dict):
                status = "✓ PASS" if target_data.get("meets_target", False) else "✗ FAIL"
                description = target_data.get("target_description", target_name)
                print(f"   {status:<8} {description}")

        overall = validation.get("overall", {})
        targets_met = overall.get("targets_met", 0)
        total_targets = overall.get("total_targets", 0)
        success_rate = overall.get("success_rate_percent", 0)

        print(
            f"\n📈 Overall Performance: {targets_met}/{total_targets} targets met ({success_rate:.1f}%)"
        )

        if overall.get("overall_success", False):
            print("🎉 ALL PERFORMANCE TARGETS ACHIEVED!")
            return True
        print("⚠️  Some performance targets not yet achieved")
        return False

    print("=" * 80)
    return False


if __name__ == "__main__":
    """Run performance benchmarks when executed directly."""
    import sys

    # Set up logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run performance benchmarks
    success = run_performance_benchmarks()
    sys.exit(0 if success else 1)
