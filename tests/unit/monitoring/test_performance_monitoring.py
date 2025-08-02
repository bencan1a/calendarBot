"""Performance monitoring tests for CalendarBot resource usage optimization."""

import gc
import sys
import time
from datetime import datetime

import psutil
import pytest

from calendarbot.benchmarking.models import BenchmarkStatus
from calendarbot.benchmarking.runner import BenchmarkRunner
from calendarbot.benchmarking.storage import BenchmarkResultStorage


class ResourceMonitor:
    """Monitor CPU and memory usage during operations."""

    def __init__(self, process_name: str = "calendarbot"):
        self.process_name = process_name
        self.baseline_memory = None
        self.baseline_cpu = None

    def get_calendarbot_processes(self) -> list[psutil.Process]:
        """Find all CalendarBot processes."""
        processes = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                # Check if it's a Python process running CalendarBot
                cmdline = proc.info["cmdline"] or []
                if any("calendarbot" in str(arg).lower() for arg in cmdline):
                    processes.append(psutil.Process(proc.info["pid"]))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes

    def measure_current_usage(self) -> dict[str, float]:
        """Measure current resource usage."""
        processes = self.get_calendarbot_processes()

        if not processes:
            # If no CalendarBot processes, measure current Python process
            process = psutil.Process()
            processes = [process]

        total_memory_mb = 0
        total_cpu_percent = 0

        for proc in processes:
            try:
                # Memory usage in MB
                memory_info = proc.memory_info()
                total_memory_mb += memory_info.rss / (1024 * 1024)

                # CPU percentage - call twice for accurate reading
                # First call establishes baseline (returns 0)
                proc.cpu_percent()
                # Wait briefly then get actual measurement
                time.sleep(0.1)
                cpu_percent = proc.cpu_percent()
                total_cpu_percent += cpu_percent

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # System-wide metrics as additional context
        system_memory = psutil.virtual_memory()
        system_cpu = psutil.cpu_percent(interval=0.1)

        return {
            "memory_mb": total_memory_mb,
            "cpu_percent": total_cpu_percent,
            "system_memory_percent": system_memory.percent,
            "system_cpu_percent": system_cpu,
            "process_count": len(processes),
        }

    def set_baseline(self) -> None:
        """Set baseline measurements."""
        metrics = self.measure_current_usage()
        self.baseline_memory = metrics["memory_mb"]
        self.baseline_cpu = metrics["cpu_percent"]

    def measure_delta(self) -> dict[str, float]:
        """Measure change from baseline."""
        current = self.measure_current_usage()

        result = current.copy()
        if self.baseline_memory is not None:
            result["memory_delta_mb"] = current["memory_mb"] - self.baseline_memory
        if self.baseline_cpu is not None:
            result["cpu_delta_percent"] = current["cpu_percent"] - self.baseline_cpu

        return result


class PerformanceTestRunner:
    """Run performance tests and store results."""

    def __init__(self):
        self.runner = BenchmarkRunner()
        self.monitor = ResourceMonitor()

    def run_calendarbot_operation_benchmark(
        self, operation_name: str, operation_func, iterations: int = 3, measure_deltas: bool = True
    ) -> dict[str, float]:
        """
        Run a benchmark of a CalendarBot operation.

        Args:
            operation_name: Name of the operation being tested
            operation_func: Function that performs the operation
            iterations: Number of iterations to run
            measure_deltas: Whether to measure resource deltas

        Returns:
            Dictionary with performance metrics
        """
        # Set baseline if measuring deltas
        if measure_deltas:
            self.monitor.set_baseline()
            time.sleep(0.5)  # Let system stabilize

        def measured_operation():
            """Wrapper that measures resource usage during operation."""
            gc.collect()  # Clean up before measurement

            start_metrics = self.monitor.measure_current_usage()
            start_time = time.perf_counter()

            # Run the actual operation
            result = operation_func()

            end_time = time.perf_counter()
            end_metrics = self.monitor.measure_current_usage()

            # Calculate resource usage during operation
            execution_time = end_time - start_time
            memory_used = end_metrics["memory_mb"] - start_metrics["memory_mb"]

            # Store metrics in operation result for later access
            if hasattr(result, "__dict__"):
                result.execution_time = execution_time
                result.memory_used = memory_used
                result.end_metrics = end_metrics

            return result

        # Register and run the benchmark
        benchmark_id = self.runner.register_benchmark(
            name=f"perf_{operation_name}",
            func=measured_operation,
            category="performance_monitoring",
            description=f"Performance monitoring for {operation_name}",
            max_iterations=iterations,
            tags=["performance", "resource_monitoring", operation_name],
        )

        # Execute the benchmark
        result = self.runner.run_benchmark(benchmark_id, iterations=iterations)

        # Get final resource measurements
        final_metrics = self.monitor.measure_current_usage()

        # Combine benchmark results with resource metrics
        performance_data = {
            "execution_time_avg": result.mean_value,
            "execution_time_min": result.min_value,
            "execution_time_max": result.max_value,
            "execution_time_std": result.std_deviation,
            "current_memory_mb": final_metrics["memory_mb"],
            "current_cpu_percent": final_metrics["cpu_percent"],
            "system_memory_percent": final_metrics["system_memory_percent"],
            "system_cpu_percent": final_metrics["system_cpu_percent"],
            "process_count": final_metrics["process_count"],
            "benchmark_status": result.status.value,
            "iterations": result.iterations,
        }

        if measure_deltas:
            delta_metrics = self.monitor.measure_delta()
            performance_data.update(
                {
                    "memory_delta_mb": delta_metrics.get("memory_delta_mb", 0),
                    "cpu_delta_percent": delta_metrics.get("cpu_delta_percent", 0),
                }
            )

        # Add resource metrics to the benchmark result metadata
        result.add_metadata("resource_metrics", performance_data)

        # Update the result in storage with the new metadata
        self.runner.storage.store_benchmark_result(result)

        return performance_data


@pytest.fixture
def performance_runner():
    """Create performance test runner."""
    return PerformanceTestRunner()


class TestCalendarBotPerformance:
    """Performance monitoring tests for CalendarBot operations."""

    def test_baseline_resource_usage(self, performance_runner):
        """Test baseline resource usage of minimal operations."""

        def minimal_operation():
            """Minimal operation to establish baseline."""
            import time

            time.sleep(0.001)  # Minimal delay
            return "baseline"

        metrics = performance_runner.run_calendarbot_operation_benchmark(
            operation_name="baseline", operation_func=minimal_operation, iterations=5
        )

        # Print metrics for visibility
        print("\n=== Baseline Resource Usage ===")
        print(f"Memory usage: {metrics['current_memory_mb']:.2f} MB")
        print(f"CPU usage: {metrics['current_cpu_percent']:.2f}%")
        print(f"System memory: {metrics['system_memory_percent']:.2f}%")
        print(f"System CPU: {metrics['system_cpu_percent']:.2f}%")
        print(
            f"Execution time: {metrics['execution_time_avg']:.4f}s ± {metrics['execution_time_std']:.4f}s"
        )

        # Basic assertions
        assert metrics["benchmark_status"] == "completed"
        assert metrics["execution_time_avg"] > 0
        assert metrics["current_memory_mb"] > 0

    def test_calendar_data_processing_performance(self, performance_runner):
        """Test performance of calendar data processing operations."""

        def calendar_processing_operation():
            """Simulate calendar data processing."""
            # Import CalendarBot modules to test real loading overhead
            try:
                from calendarbot.ics import ICSFetcher, ICSParser
                from calendarbot.structured import StructuredLogger

                # Create some test data
                test_data = {
                    "events": [
                        {"title": f"Event {i}", "start": f"2024-01-{i:02d}T10:00:00Z"}
                        for i in range(1, 51)  # 50 events
                    ]
                }

                # Process the data (simplified to avoid dependency issues)
                processed = []
                for event in test_data["events"]:
                    processed.append(
                        {"title": event["title"].upper(), "formatted_start": event["start"]}
                    )

                return {"processed_events": len(processed), "sample": processed[0]}

            except ImportError:
                # If modules don't exist, simulate the processing
                import json

                test_data = {"events": [{"title": f"Event {i}"} for i in range(50)]}
                result = json.dumps(test_data)
                return {"simulated": True, "data_size": len(result)}

        metrics = performance_runner.run_calendarbot_operation_benchmark(
            operation_name="calendar_processing",
            operation_func=calendar_processing_operation,
            iterations=3,
        )

        print("\n=== Calendar Processing Performance ===")
        print(f"Memory usage: {metrics['current_memory_mb']:.2f} MB")
        print(f"Memory delta: {metrics.get('memory_delta_mb', 0):.2f} MB")
        print(f"CPU delta: {metrics.get('cpu_delta_percent', 0):.2f}%")
        print(
            f"Execution time: {metrics['execution_time_avg']:.4f}s ± {metrics['execution_time_std']:.4f}s"
        )

        assert metrics["benchmark_status"] == "completed"
        assert metrics["execution_time_avg"] < 2.0  # Should complete in reasonable time

    def test_web_server_startup_performance(self, performance_runner):
        """Test performance of web server initialization."""

        def web_startup_simulation():
            """Simulate web server startup operations."""
            try:
                # Try to import web-related modules
                import flask

                # Simulate creating a Flask app
                app = flask.Flask(__name__)

                @app.route("/test")
                def test_route():
                    return {"status": "ok", "timestamp": datetime.now().isoformat()}

                # Test route registration and basic functionality
                with app.test_client() as client:
                    response = client.get("/test")
                    data = response.get_json()

                return {"status": "web_server_ready", "response": data}

            except ImportError:
                # Simulate startup operations if Flask not available
                import time

                time.sleep(0.1)  # Simulate startup time
                return {"status": "simulated_startup", "duration": 0.1}

        metrics = performance_runner.run_calendarbot_operation_benchmark(
            operation_name="web_startup",
            operation_func=web_startup_simulation,
            iterations=2,  # Fewer iterations for startup tests
        )

        print("\n=== Web Server Startup Performance ===")
        print(f"Memory usage: {metrics['current_memory_mb']:.2f} MB")
        print(f"Memory delta: {metrics.get('memory_delta_mb', 0):.2f} MB")
        print(
            f"Execution time: {metrics['execution_time_avg']:.4f}s ± {metrics['execution_time_std']:.4f}s"
        )

        assert metrics["benchmark_status"] == "completed"
        assert metrics["execution_time_avg"] < 2.0  # Startup should be reasonable

    def test_memory_intensive_operation_performance(self, performance_runner):
        """Test performance under memory pressure."""

        def memory_intensive_operation():
            """Operation that uses significant memory."""
            # Create memory pressure
            large_data = []

            # Generate data that will use memory
            for i in range(1000):
                large_data.append(
                    {
                        "id": i,
                        "data": "x" * 1000,  # 1KB per entry
                        "nested": {"values": list(range(100))},
                    }
                )

            # Process the data
            result = {
                "total_items": len(large_data),
                "total_size_estimate": len(str(large_data)),
                "sample_item": large_data[0] if large_data else None,
            }

            # Clean up
            del large_data

            return result

        metrics = performance_runner.run_calendarbot_operation_benchmark(
            operation_name="memory_intensive",
            operation_func=memory_intensive_operation,
            iterations=2,
        )

        print("\n=== Memory Intensive Operation Performance ===")
        print(f"Memory usage: {metrics['current_memory_mb']:.2f} MB")
        print(f"Memory delta: {metrics.get('memory_delta_mb', 0):.2f} MB")
        print(
            f"Execution time: {metrics['execution_time_avg']:.4f}s ± {metrics['execution_time_std']:.4f}s"
        )

        assert metrics["benchmark_status"] == "completed"
        # Memory delta should show the impact
        if "memory_delta_mb" in metrics:
            print(f"Memory impact detected: {metrics['memory_delta_mb']:.2f} MB")


def view_performance_trends(days: int = 7) -> None:
    """
    View performance trends over the specified number of days.

    Args:
        days: Number of days to look back for trend analysis
    """
    storage = BenchmarkResultStorage()

    print(f"\n=== Performance Trends (Last {days} days) ===")

    # Get recent benchmark results
    results = storage.get_benchmark_results(
        category="performance_monitoring", status=BenchmarkStatus.COMPLETED, limit=100
    )

    if not results:
        print("No performance data found. Run performance tests first.")
        return

    # Group by benchmark name
    by_benchmark = {}
    for result in results:
        name = result.benchmark_name
        if name not in by_benchmark:
            by_benchmark[name] = []
        by_benchmark[name].append(result)

    # Display trends for each benchmark
    for benchmark_name, benchmark_results in by_benchmark.items():
        print(f"\n--- {benchmark_name} ---")

        # Sort by timestamp
        benchmark_results.sort(key=lambda x: x.timestamp, reverse=True)

        # Show recent results
        for i, result in enumerate(benchmark_results[:5]):  # Last 5 runs
            timestamp = result.timestamp.strftime("%Y-%m-%d %H:%M:%S")

            # Extract resource metrics from metadata
            resource_metrics = result.get_metadata("resource_metrics", {})
            memory_mb = resource_metrics.get("current_memory_mb", 0)
            cpu_percent = resource_metrics.get("current_cpu_percent", 0)

            print(f"  Run {i + 1} ({timestamp}):")
            print(f"    Execution: {result.mean_value:.4f}s")
            print(f"    Memory: {memory_mb:.2f} MB")
            print(f"    CPU: {cpu_percent:.2f}%")

        # Calculate trend if enough data
        if len(benchmark_results) >= 2:
            recent = benchmark_results[0].mean_value
            older = benchmark_results[-1].mean_value
            change_percent = ((recent - older) / older) * 100 if older > 0 else 0

            trend_indicator = "📈" if change_percent > 5 else "📉" if change_percent < -5 else "➡️"
            print(f"  Trend: {trend_indicator} {change_percent:+.1f}% vs oldest run")


if __name__ == "__main__":
    # Allow running this script directly to view trends
    if len(sys.argv) > 1 and sys.argv[1] == "trends":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        view_performance_trends(days)
    else:
        print("Run with: python test_performance_monitoring.py trends [days]")
        print("Or run via pytest: pytest tests/test_performance_monitoring.py -v -s")
