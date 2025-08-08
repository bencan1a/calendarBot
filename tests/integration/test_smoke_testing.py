"""Smoke tests for CalendarBot Phase 1 implementation.

This module contains smoke tests to validate:
- Application startup without errors
- Web server serves both old and new endpoints
- Existing HTML endpoints continue to work
- E-paper compatibility is maintained
- No regressions in core functionality

Smoke tests are designed to run quickly and catch major issues before detailed testing.
"""

import json
import logging
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

import pytest
import requests

logger = logging.getLogger(__name__)


class CalendarBotSmokeTest:
    """Smoke test suite for CalendarBot application."""

    def __init__(self, port: int = 0):
        """Initialize smoke test with a specific port or auto-select."""
        self.port = port or self._get_free_port()
        self.process: Optional[subprocess.Popen] = None
        self.base_url = f"http://localhost:{self.port}"

    def _get_free_port(self) -> int:
        """Get a free port for testing."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    def start_application(self, timeout: int = 30) -> bool:
        """Start CalendarBot application and wait for it to be ready.

        Args:
            timeout: Maximum time to wait for application startup

        Returns:
            True if application started successfully, False otherwise
        """
        try:
            # Activate venv and start calendarbot
            cmd = [
                "sh",
                "-c",
                f". venv/bin/activate && python -m calendarbot --web --port {self.port}",
            ]

            logger.info(f"Starting CalendarBot on port {self.port}")

            # Start the process
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=Path.cwd()
            )

            # Wait for application to be ready
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=1)
                    if response.status_code == 200:
                        logger.info(f"CalendarBot started successfully on port {self.port}")
                        return True
                except requests.RequestException:
                    pass

                # Check if process is still running
                if self.process.poll() is not None:
                    stdout, stderr = self.process.communicate()
                    logger.error("CalendarBot process exited early:")
                    logger.error(f"STDOUT: {stdout}")
                    logger.error(f"STDERR: {stderr}")
                    return False

                time.sleep(0.5)

            logger.error(f"CalendarBot failed to start within {timeout} seconds")
            return False

        except Exception as e:
            logger.error(f"Failed to start CalendarBot: {e}")
            return False

    def stop_application(self):
        """Stop the CalendarBot application."""
        if self.process:
            try:
                # Try graceful shutdown first
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    self.process.kill()
                    self.process.wait()
                logger.info("CalendarBot stopped")
            except Exception as e:
                logger.error(f"Error stopping CalendarBot: {e}")
            finally:
                self.process = None

    def test_application_startup(self) -> bool:
        """Test that the application starts without errors."""
        return self.start_application()

    def test_health_endpoint(self) -> bool:
        """Test that health endpoint responds correctly."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Health endpoint test failed: {e}")
            return False

    def test_existing_html_endpoints(self) -> Tuple[bool, str]:
        """Test that existing HTML endpoints continue to work.

        Returns:
            Tuple of (success, error_message)
        """
        endpoints_to_test = ["/", "/whats-next-view", "/status"]

        for endpoint in endpoints_to_test:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code not in [200, 301, 302]:
                    return False, f"Endpoint {endpoint} returned status {response.status_code}"

                # For HTML endpoints, verify we get HTML content
                if endpoint in ["/", "/whats-next-view"]:
                    content_type = response.headers.get("content-type", "")
                    if "text/html" not in content_type:
                        return (
                            False,
                            f"Endpoint {endpoint} did not return HTML content: {content_type}",
                        )

            except requests.RequestException as e:
                return False, f"Endpoint {endpoint} failed: {e}"

        return True, "All HTML endpoints working"

    def test_new_json_endpoints(self) -> Tuple[bool, str]:
        """Test that new JSON endpoints from Phase 1 work correctly.

        Returns:
            Tuple of (success, error_message)
        """
        json_endpoints = [
            ("/api/whats-next/data", "GET"),
            ("/api/events/hidden", "GET"),
            ("/api/status", "GET"),
        ]

        for endpoint, method in json_endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                else:
                    response = requests.post(f"{self.base_url}{endpoint}", json={}, timeout=10)

                if response.status_code not in [200, 400]:  # 400 is OK for some endpoints
                    return False, f"JSON endpoint {endpoint} returned status {response.status_code}"

                # Verify JSON response
                try:
                    response.json()
                except json.JSONDecodeError:
                    return False, f"Endpoint {endpoint} did not return valid JSON"

            except requests.RequestException as e:
                return False, f"JSON endpoint {endpoint} failed: {e}"

        return True, "All JSON endpoints working"

    def test_event_hiding_workflow(self) -> Tuple[bool, str]:
        """Test basic event hiding workflow works end-to-end.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get initial data
            response = requests.get(f"{self.base_url}/api/whats-next/data", timeout=10)
            if response.status_code != 200:
                return False, f"Failed to get initial data: {response.status_code}"

            # Try to hide a test event
            test_graph_id = "smoke-test-event"
            hide_response = requests.post(
                f"{self.base_url}/api/events/hide", json={"graph_id": test_graph_id}, timeout=10
            )

            if hide_response.status_code != 200:
                return False, f"Failed to hide event: {hide_response.status_code}"

            hide_data = hide_response.json()
            if not hide_data.get("success"):
                return False, f"Hide event returned success=False: {hide_data}"

            # Try to unhide the event
            unhide_response = requests.post(
                f"{self.base_url}/api/events/unhide", json={"graph_id": test_graph_id}, timeout=10
            )

            if unhide_response.status_code != 200:
                return False, f"Failed to unhide event: {unhide_response.status_code}"

            unhide_data = unhide_response.json()
            if not unhide_data.get("success"):
                return False, f"Unhide event returned success=False: {unhide_data}"

            return True, "Event hiding workflow working"

        except Exception as e:
            return False, f"Event hiding workflow failed: {e}"

    def test_static_file_serving(self) -> Tuple[bool, str]:
        """Test that static files are served correctly.

        Returns:
            Tuple of (success, error_message)
        """
        static_files = [
            "/static/layouts/whats-next-view/whats-next-view.js",
            "/static/layouts/whats-next-view/whats-next-view.css",
        ]

        for static_file in static_files:
            try:
                response = requests.get(f"{self.base_url}{static_file}", timeout=10)
                if response.status_code != 200:
                    return (
                        False,
                        f"Static file {static_file} returned status {response.status_code}",
                    )

                # Verify content type
                content_type = response.headers.get("content-type", "")
                if static_file.endswith(".js") and "javascript" not in content_type:
                    return False, f"JS file {static_file} has wrong content type: {content_type}"
                if static_file.endswith(".css") and "css" not in content_type:
                    return False, f"CSS file {static_file} has wrong content type: {content_type}"

            except requests.RequestException as e:
                return False, f"Static file {static_file} failed: {e}"

        return True, "Static file serving working"

    def run_all_smoke_tests(self) -> Tuple[bool, dict]:
        """Run all smoke tests and return results.

        Returns:
            Tuple of (overall_success, detailed_results)
        """
        results = {}
        overall_success = True

        # Test 1: Application startup
        logger.info("Running smoke test: Application startup")
        startup_success = self.test_application_startup()
        results["application_startup"] = {
            "success": startup_success,
            "message": "Application started successfully"
            if startup_success
            else "Application failed to start",
        }
        overall_success &= startup_success

        if not startup_success:
            return False, results

        try:
            # Test 2: Health endpoint
            logger.info("Running smoke test: Health endpoint")
            health_success = self.test_health_endpoint()
            results["health_endpoint"] = {
                "success": health_success,
                "message": "Health endpoint working"
                if health_success
                else "Health endpoint failed",
            }
            overall_success &= health_success

            # Test 3: Existing HTML endpoints
            logger.info("Running smoke test: HTML endpoints")
            html_success, html_message = self.test_existing_html_endpoints()
            results["html_endpoints"] = {"success": html_success, "message": html_message}
            overall_success &= html_success

            # Test 4: New JSON endpoints
            logger.info("Running smoke test: JSON endpoints")
            json_success, json_message = self.test_new_json_endpoints()
            results["json_endpoints"] = {"success": json_success, "message": json_message}
            overall_success &= json_success

            # Test 5: Event hiding workflow
            logger.info("Running smoke test: Event hiding workflow")
            workflow_success, workflow_message = self.test_event_hiding_workflow()
            results["event_hiding_workflow"] = {
                "success": workflow_success,
                "message": workflow_message,
            }
            overall_success &= workflow_success

            # Test 6: Static file serving
            logger.info("Running smoke test: Static file serving")
            static_success, static_message = self.test_static_file_serving()
            results["static_file_serving"] = {"success": static_success, "message": static_message}
            overall_success &= static_success

        finally:
            # Always stop the application
            self.stop_application()

        return overall_success, results


# Pytest integration
@pytest.fixture(scope="module")
def smoke_test_instance():
    """Create a smoke test instance for the test session."""
    return CalendarBotSmokeTest()


class TestCalendarBotSmoke:
    """Pytest test class for CalendarBot smoke tests."""

    def test_application_can_start(self, smoke_test_instance):
        """Test that CalendarBot application can start successfully."""
        success = smoke_test_instance.test_application_startup()
        assert success, "CalendarBot application failed to start"

        # Clean up
        smoke_test_instance.stop_application()

    def test_full_smoke_test_suite(self, smoke_test_instance):
        """Run the complete smoke test suite."""
        overall_success, results = smoke_test_instance.run_all_smoke_tests()

        # Log detailed results
        for test_name, result in results.items():
            status = "✓" if result["success"] else "✗"
            logger.info(f"{status} {test_name}: {result['message']}")

        # Assert overall success
        if not overall_success:
            failed_tests = [name for name, result in results.items() if not result["success"]]
            pytest.fail(f"Smoke tests failed: {failed_tests}")

    def test_phase_1_endpoints_available(self, smoke_test_instance):
        """Test that Phase 1 JSON endpoints are available and working."""
        # Start application
        assert smoke_test_instance.test_application_startup(), "Application failed to start"

        try:
            # Test JSON endpoints
            json_success, json_message = smoke_test_instance.test_new_json_endpoints()
            assert json_success, f"Phase 1 JSON endpoints failed: {json_message}"

            # Test event hiding workflow
            workflow_success, workflow_message = smoke_test_instance.test_event_hiding_workflow()
            assert workflow_success, f"Phase 1 event hiding workflow failed: {workflow_message}"

        finally:
            smoke_test_instance.stop_application()

    def test_no_regression_in_existing_functionality(self, smoke_test_instance):
        """Test that existing functionality has not regressed."""
        # Start application
        assert smoke_test_instance.test_application_startup(), "Application failed to start"

        try:
            # Test existing HTML endpoints
            html_success, html_message = smoke_test_instance.test_existing_html_endpoints()
            assert html_success, f"Existing HTML endpoints failed: {html_message}"

            # Test static file serving
            static_success, static_message = smoke_test_instance.test_static_file_serving()
            assert static_success, f"Static file serving failed: {static_message}"

        finally:
            smoke_test_instance.stop_application()


# Standalone smoke test runner
def run_smoke_tests() -> bool:
    """Run smoke tests as a standalone function.

    Returns:
        True if all smoke tests pass, False otherwise
    """
    smoke_test = CalendarBotSmokeTest()
    overall_success, results = smoke_test.run_all_smoke_tests()

    print("\n" + "=" * 60)
    print("CALENDARBOT SMOKE TEST RESULTS")
    print("=" * 60)

    for test_name, result in results.items():
        status = "✓ PASS" if result["success"] else "✗ FAIL"
        print(f"{status:<8} {test_name:<30} {result['message']}")

    print("=" * 60)
    overall_status = "ALL TESTS PASSED" if overall_success else "SOME TESTS FAILED"
    print(f"OVERALL: {overall_status}")
    print("=" * 60)

    return overall_success


if __name__ == "__main__":
    """Run smoke tests when executed directly."""
    import sys

    # Set up logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run smoke tests
    success = run_smoke_tests()
    sys.exit(0 if success else 1)
