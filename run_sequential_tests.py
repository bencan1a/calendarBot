#!/usr/bin/env python3
"""
Sequential Test Execution Script
Runs tests in controlled batches to prevent hanging issues and ensure reliability.
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


class SequentialTestRunner:
    """Manages sequential test execution with batching and logging."""

    def __init__(self, config_path: str = "test_suite_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.setup_logging()
        self.results = []

    def _load_config(self) -> Dict:
        """Load test suite configuration."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def setup_logging(self):
        """Configure logging for test execution."""
        log_config = self.config.get("logging", {})
        level = getattr(logging, log_config.get("level", "INFO"))
        format_str = log_config.get("format", "%(asctime)s [%(levelname)8s] %(name)s: %(message)s")
        date_format = log_config.get("date_format", "%Y-%m-%d %H:%M:%S")

        logging.basicConfig(
            level=level,
            format=format_str,
            datefmt=date_format,
            handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("test_execution.log")],
        )
        self.logger = logging.getLogger("SequentialTestRunner")

    def activate_venv(self) -> bool:
        """Ensure virtual environment is activated."""
        try:
            # Check if we're in a virtual environment
            if hasattr(sys, "real_prefix") or (
                hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
            ):
                self.logger.info("Virtual environment already activated")
                return True

            # Try to activate venv
            venv_path = Path("venv/bin/activate")
            if venv_path.exists():
                self.logger.info("Activating virtual environment")
                # Note: In practice, the script should be run with venv already activated
                # This is more of a verification step
                return True
            else:
                self.logger.warning("Virtual environment not found at venv/bin/activate")
                return False

        except Exception as e:
            self.logger.error(f"Error activating virtual environment: {e}")
            return False

    def run_batch(self, batch_name: str, batch_config: Dict) -> Tuple[bool, str]:
        """Run a single test batch."""
        self.logger.info(f"Starting batch: {batch_name}")
        self.logger.info(f"Description: {batch_config.get('description', 'No description')}")

        start_time = time.time()

        # Build pytest command
        cmd = self._build_pytest_command(batch_config)

        try:
            self.logger.info(f"Executing: {' '.join(cmd)}")

            # Set environment variables if specified
            env = os.environ.copy()
            if "environment" in batch_config:
                for env_var in batch_config["environment"]:
                    key, value = env_var.split("=", 1)
                    env[key] = value

            # Run the test batch
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=batch_config.get("timeout", 300),
                env=env,
            )

            duration = time.time() - start_time

            # Log results
            if result.returncode == 0:
                self.logger.info(f"Batch {batch_name} PASSED in {duration:.2f}s")
                status = "PASSED"
            else:
                self.logger.error(f"Batch {batch_name} FAILED in {duration:.2f}s")
                self.logger.error(f"STDOUT: {result.stdout}")
                self.logger.error(f"STDERR: {result.stderr}")
                status = "FAILED"

            # Store results
            self.results.append(
                {
                    "batch": batch_name,
                    "status": status,
                    "duration": duration,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )

            return result.returncode == 0, result.stdout + result.stderr

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.logger.error(f"Batch {batch_name} TIMEOUT after {duration:.2f}s")
            self.results.append(
                {
                    "batch": batch_name,
                    "status": "TIMEOUT",
                    "duration": duration,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": "Test batch timed out",
                }
            )
            return False, "Test batch timed out"

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Batch {batch_name} ERROR: {e}")
            self.results.append(
                {
                    "batch": batch_name,
                    "status": "ERROR",
                    "duration": duration,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": str(e),
                }
            )
            return False, str(e)

    def _build_pytest_command(self, batch_config: Dict) -> List[str]:
        """Build pytest command for a batch."""
        cmd = ["python", "-m", "pytest"]

        # Add paths or expressions
        if "paths" in batch_config:
            # When paths are specified, run those files directly
            # Markers are redundant since we're targeting specific files
            cmd.extend(batch_config["paths"])
        elif "expressions" in batch_config:
            # For expression-based selection, combine all expressions into single -k argument
            expressions = batch_config["expressions"]
            if expressions:
                # Convert wildcard patterns to pytest-compatible expressions
                pytest_expressions = []
                for expr in expressions:
                    # Convert shell wildcards to pytest substring matching
                    # test_*_critical -> critical
                    # test_*_smoke -> smoke
                    # test_basic_* -> test_basic
                    if expr.startswith("test_") and "_*" in expr:
                        # Extract the meaningful part for substring matching
                        if expr == "test_*_critical":
                            pytest_expressions.append("critical")
                        elif expr == "test_*_smoke":
                            pytest_expressions.append("smoke")
                        elif expr == "test_basic_*":
                            pytest_expressions.append("test_basic")
                        else:
                            # Generic wildcard removal
                            pytest_expressions.append(
                                expr.replace("*", "").replace("__", "_").strip("_")
                            )
                    else:
                        # No wildcard, use as-is
                        pytest_expressions.append(expr)

                # Combine expressions with 'or' logic
                combined_expr = " or ".join(pytest_expressions)
                cmd.extend(["-k", combined_expr])

            # Add markers for expression-based selection
            if "markers" in batch_config:
                for marker in batch_config["markers"]:
                    cmd.extend(["-m", marker])
        else:
            # Fallback: use markers only if no paths or expressions
            if "markers" in batch_config:
                for marker in batch_config["markers"]:
                    cmd.extend(["-m", marker])

        # Minimal command line options - let pytest.ini handle the rest
        # This prevents conflicts with different pytest.ini files
        cmd.extend(["--tb=short", "--verbose"])

        return cmd

    def run_all_batches(self, selected_batches: Optional[List[str]] = None) -> bool:
        """Run all configured test batches sequentially."""
        if not self.activate_venv():
            self.logger.error("Failed to activate virtual environment")
            return False

        batches = self.config.get("batches", {})

        if selected_batches:
            batches = {k: v for k, v in batches.items() if k in selected_batches}

        self.logger.info(f"Running {len(batches)} test batches sequentially")

        overall_success = True
        total_start_time = time.time()

        for batch_name, batch_config in batches.items():
            success, output = self.run_batch(batch_name, batch_config)

            if not success:
                overall_success = False
                if self.config.get("execution", {}).get("fail_fast", False):
                    self.logger.error("Fail-fast enabled, stopping execution")
                    break

            # Brief pause between batches to prevent resource conflicts
            time.sleep(1)

        total_duration = time.time() - total_start_time
        self.logger.info(f"All batches completed in {total_duration:.2f}s")

        self._generate_summary_report()

        return overall_success

    def _generate_summary_report(self):
        """Generate a summary report of test execution."""
        self.logger.info("=" * 60)
        self.logger.info("TEST EXECUTION SUMMARY")
        self.logger.info("=" * 60)

        total_batches = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASSED")
        failed = sum(1 for r in self.results if r["status"] == "FAILED")
        timeouts = sum(1 for r in self.results if r["status"] == "TIMEOUT")
        errors = sum(1 for r in self.results if r["status"] == "ERROR")

        self.logger.info(f"Total Batches: {total_batches}")
        self.logger.info(f"Passed: {passed}")
        self.logger.info(f"Failed: {failed}")
        self.logger.info(f"Timeouts: {timeouts}")
        self.logger.info(f"Errors: {errors}")

        self.logger.info("\nBatch Details:")
        for result in self.results:
            status_icon = "✓" if result["status"] == "PASSED" else "✗"
            self.logger.info(
                f"  {status_icon} {result['batch']}: {result['status']} ({result['duration']:.2f}s)"
            )

        # Write detailed report to file
        with open("test_execution_report.txt", "w") as f:
            f.write("CalendarBot Sequential Test Execution Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Total Batches: {total_batches}\n")
            f.write(f"Passed: {passed}\n")
            f.write(f"Failed: {failed}\n")
            f.write(f"Timeouts: {timeouts}\n")
            f.write(f"Errors: {errors}\n\n")

            for result in self.results:
                f.write(f"\nBatch: {result['batch']}\n")
                f.write(f"Status: {result['status']}\n")
                f.write(f"Duration: {result['duration']:.2f}s\n")
                f.write(f"Return Code: {result['returncode']}\n")
                if result["stdout"]:
                    f.write(f"STDOUT:\n{result['stdout']}\n")
                if result["stderr"]:
                    f.write(f"STDERR:\n{result['stderr']}\n")
                f.write("-" * 40 + "\n")


def main():
    """Main entry point for sequential test runner."""
    parser = argparse.ArgumentParser(description="Run CalendarBot tests sequentially")
    parser.add_argument(
        "--config", default="test_suite_config.yaml", help="Path to test suite configuration file"
    )
    parser.add_argument("--batches", nargs="+", help="Specific batches to run (default: all)")
    parser.add_argument("--list-batches", action="store_true", help="List available test batches")

    args = parser.parse_args()

    try:
        runner = SequentialTestRunner(args.config)

        if args.list_batches:
            print("Available test batches:")
            for batch_name, batch_config in runner.config.get("batches", {}).items():
                print(f"  {batch_name}: {batch_config.get('description', 'No description')}")
            return 0

        success = runner.run_all_batches(args.batches)
        return 0 if success else 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
