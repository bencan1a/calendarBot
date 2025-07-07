"""Unit tests for calendarbot.validation.results module."""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from calendarbot.validation.results import ValidationItem, ValidationResults, ValidationStatus


class TestValidationStatus:
    """Test ValidationStatus enum."""

    def test_validation_status_values(self):
        """Test that all expected validation statuses are defined."""
        expected_statuses = [
            ("SUCCESS", "success"),
            ("FAILURE", "failure"),
            ("WARNING", "warning"),
            ("SKIPPED", "skipped"),
        ]

        for status_name, status_value in expected_statuses:
            assert hasattr(ValidationStatus, status_name)
            assert getattr(ValidationStatus, status_name).value == status_value

    def test_validation_status_enum_members(self):
        """Test ValidationStatus enum members."""
        assert ValidationStatus.SUCCESS.value == "success"
        assert ValidationStatus.FAILURE.value == "failure"
        assert ValidationStatus.WARNING.value == "warning"
        assert ValidationStatus.SKIPPED.value == "skipped"


class TestValidationItem:
    """Test ValidationItem dataclass."""

    def test_validation_item_initialization_required_fields(self):
        """Test ValidationItem initialization with required fields only."""
        item = ValidationItem(
            component="auth",
            test_name="test_authentication",
            status=ValidationStatus.SUCCESS,
            message="Authentication successful",
        )

        assert item.component == "auth"
        assert item.test_name == "test_authentication"
        assert item.status == ValidationStatus.SUCCESS
        assert item.message == "Authentication successful"
        assert item.details is None
        assert isinstance(item.timestamp, datetime)
        assert item.duration_ms is None

    def test_validation_item_initialization_all_fields(self):
        """Test ValidationItem initialization with all fields."""
        test_timestamp = datetime(2023, 1, 15, 10, 30, 0)
        test_details = {"param1": "value1", "param2": 42}

        item = ValidationItem(
            component="cache",
            test_name="test_cache_operations",
            status=ValidationStatus.FAILURE,
            message="Cache operation failed",
            details=test_details,
            timestamp=test_timestamp,
            duration_ms=1500,
        )

        assert item.component == "cache"
        assert item.test_name == "test_cache_operations"
        assert item.status == ValidationStatus.FAILURE
        assert item.message == "Cache operation failed"
        assert item.details == test_details
        assert item.timestamp == test_timestamp
        assert item.duration_ms == 1500

    def test_validation_item_default_timestamp(self):
        """Test ValidationItem gets current timestamp by default."""
        before = datetime.now()

        item = ValidationItem(
            component="api",
            test_name="test_api",
            status=ValidationStatus.SUCCESS,
            message="API test passed",
        )

        after = datetime.now()

        assert before <= item.timestamp <= after

    @pytest.mark.parametrize(
        "status",
        [
            ValidationStatus.SUCCESS,
            ValidationStatus.FAILURE,
            ValidationStatus.WARNING,
            ValidationStatus.SKIPPED,
        ],
    )
    def test_validation_item_with_different_statuses(self, status):
        """Test ValidationItem with different validation statuses."""
        item = ValidationItem(
            component="display",
            test_name="test_display",
            status=status,
            message=f"Display test {status.value}",
        )

        assert item.status == status


class TestValidationResults:
    """Test ValidationResults class."""

    @pytest.fixture
    def validation_results(self):
        """Create ValidationResults instance for testing."""
        return ValidationResults()

    def test_validation_results_initialization(self, validation_results):
        """Test ValidationResults initialization."""
        assert validation_results.items == []
        assert isinstance(validation_results.start_time, datetime)
        assert validation_results.end_time is None
        assert validation_results.components_tested == set()

    def test_add_result_basic(self, validation_results):
        """Test add_result method with basic parameters."""
        validation_results.add_result(
            component="auth",
            test_name="test_token",
            status=ValidationStatus.SUCCESS,
            message="Token validation successful",
        )

        assert len(validation_results.items) == 1
        item = validation_results.items[0]
        assert item.component == "auth"
        assert item.test_name == "test_token"
        assert item.status == ValidationStatus.SUCCESS
        assert item.message == "Token validation successful"
        assert item.details == {}
        assert "auth" in validation_results.components_tested

    def test_add_result_with_details_and_duration(self, validation_results):
        """Test add_result method with details and duration."""
        details = {"token_length": 256, "expires_in": 3600}

        validation_results.add_result(
            component="auth",
            test_name="test_token",
            status=ValidationStatus.SUCCESS,
            message="Token validation successful",
            details=details,
            duration_ms=250,
        )

        item = validation_results.items[0]
        assert item.details == details
        assert item.duration_ms == 250

    def test_add_success(self, validation_results):
        """Test add_success convenience method."""
        details = {"connection": "established"}

        validation_results.add_success(
            component="api",
            test_name="test_connection",
            message="API connection successful",
            details=details,
            duration_ms=150,
        )

        assert len(validation_results.items) == 1
        item = validation_results.items[0]
        assert item.status == ValidationStatus.SUCCESS
        assert item.details == details
        assert item.duration_ms == 150

    def test_add_failure(self, validation_results):
        """Test add_failure convenience method."""
        details = {"error_code": 404}

        validation_results.add_failure(
            component="api",
            test_name="test_endpoint",
            message="Endpoint not found",
            details=details,
            duration_ms=200,
        )

        assert len(validation_results.items) == 1
        item = validation_results.items[0]
        assert item.status == ValidationStatus.FAILURE
        assert item.details == details

    def test_add_warning(self, validation_results):
        """Test add_warning convenience method."""
        validation_results.add_warning(
            component="cache",
            test_name="test_cache_age",
            message="Cache is older than recommended",
            details={"age_hours": 25},
            duration_ms=50,
        )

        assert len(validation_results.items) == 1
        item = validation_results.items[0]
        assert item.status == ValidationStatus.WARNING

    def test_add_skipped(self, validation_results):
        """Test add_skipped convenience method."""
        validation_results.add_skipped(
            component="auth",
            test_name="test_advanced_auth",
            message="Advanced auth not configured",
            details={"reason": "not_configured"},
        )

        assert len(validation_results.items) == 1
        item = validation_results.items[0]
        assert item.status == ValidationStatus.SKIPPED
        # Skipped items don't have duration
        assert item.duration_ms is None

    def test_finalize(self, validation_results):
        """Test finalize method."""
        assert validation_results.end_time is None

        validation_results.finalize()

        assert validation_results.end_time is not None
        assert isinstance(validation_results.end_time, datetime)

    def test_get_summary_basic(self, validation_results):
        """Test get_summary method with basic results."""
        # Add some test results
        validation_results.add_success("sources", "test1", "Success 1")
        validation_results.add_failure("cache", "test2", "Failure 1")
        validation_results.add_warning("cache", "test3", "Warning 1")
        validation_results.add_skipped("display", "test4", "Skipped 1")

        summary = validation_results.get_summary()

        assert "start_time" in summary
        assert "end_time" in summary
        assert "total_duration_seconds" in summary
        assert "total_tests" in summary
        assert "components_tested" in summary
        assert "status_counts" in summary
        assert "component_stats" in summary
        assert "success_rate" in summary

        assert summary["total_tests"] == 4
        assert summary["components_tested"] == ["cache", "display", "sources"]
        assert summary["status_counts"]["success"] == 1
        assert summary["status_counts"]["failure"] == 1
        assert summary["status_counts"]["warning"] == 1
        assert summary["status_counts"]["skipped"] == 1
        assert summary["success_rate"] == 0.25  # 1 success out of 4 total

    def test_get_summary_auto_finalize(self, validation_results):
        """Test get_summary automatically finalizes if not done."""
        validation_results.add_success("auth", "test", "Success")

        assert validation_results.end_time is None

        summary = validation_results.get_summary()

        # Should have auto-finalized
        assert validation_results.end_time is not None
        assert summary["end_time"] is not None

    def test_get_summary_component_stats(self, validation_results):
        """Test get_summary component statistics."""
        # Add multiple results for same component
        validation_results.add_success("auth", "test1", "Success 1")
        validation_results.add_success("auth", "test2", "Success 2")
        validation_results.add_failure("auth", "test3", "Failure 1")
        validation_results.add_warning("api", "test4", "Warning 1")

        summary = validation_results.get_summary()

        auth_stats = summary["component_stats"]["auth"]
        api_stats = summary["component_stats"]["api"]

        assert auth_stats["success"] == 2
        assert auth_stats["failure"] == 1
        assert auth_stats["warning"] == 0
        assert auth_stats["skipped"] == 0

        assert api_stats["success"] == 0
        assert api_stats["failure"] == 0
        assert api_stats["warning"] == 1
        assert api_stats["skipped"] == 0

    def test_has_failures_true(self, validation_results):
        """Test has_failures returns True when failures exist."""
        validation_results.add_success("auth", "test1", "Success")
        validation_results.add_failure("api", "test2", "Failure")

        assert validation_results.has_failures() == True

    def test_has_failures_false(self, validation_results):
        """Test has_failures returns False when no failures exist."""
        validation_results.add_success("auth", "test1", "Success")
        validation_results.add_warning("api", "test2", "Warning")

        assert validation_results.has_failures() == False

    def test_has_warnings_true(self, validation_results):
        """Test has_warnings returns True when warnings exist."""
        validation_results.add_success("auth", "test1", "Success")
        validation_results.add_warning("api", "test2", "Warning")

        assert validation_results.has_warnings() == True

    def test_has_warnings_false(self, validation_results):
        """Test has_warnings returns False when no warnings exist."""
        validation_results.add_success("auth", "test1", "Success")
        validation_results.add_failure("api", "test2", "Failure")

        assert validation_results.has_warnings() == False

    def test_get_failures(self, validation_results):
        """Test get_failures returns only failure items."""
        validation_results.add_success("auth", "test1", "Success")
        validation_results.add_failure("api", "test2", "Failure 1")
        validation_results.add_warning("cache", "test3", "Warning")
        validation_results.add_failure("display", "test4", "Failure 2")

        failures = validation_results.get_failures()

        assert len(failures) == 2
        assert all(item.status == ValidationStatus.FAILURE for item in failures)
        failure_messages = [item.message for item in failures]
        assert "Failure 1" in failure_messages
        assert "Failure 2" in failure_messages

    def test_get_warnings(self, validation_results):
        """Test get_warnings returns only warning items."""
        validation_results.add_success("auth", "test1", "Success")
        validation_results.add_failure("api", "test2", "Failure")
        validation_results.add_warning("cache", "test3", "Warning 1")
        validation_results.add_warning("display", "test4", "Warning 2")

        warnings = validation_results.get_warnings()

        assert len(warnings) == 2
        assert all(item.status == ValidationStatus.WARNING for item in warnings)
        warning_messages = [item.message for item in warnings]
        assert "Warning 1" in warning_messages
        assert "Warning 2" in warning_messages

    @patch("builtins.print")
    def test_print_console_report_basic(self, mock_print, validation_results):
        """Test print_console_report method."""
        validation_results.add_success("sources", "test1", "Success", duration_ms=100)
        validation_results.add_failure("cache", "test2", "Failure", duration_ms=200)

        validation_results.print_console_report()

        # Should have printed multiple lines
        assert mock_print.call_count > 5

        # Check some expected content in print calls
        all_prints = [
            str(call.args[0]) if call.args else str(call) for call in mock_print.call_args_list
        ]
        all_content = " ".join(all_prints)

        assert "CALENDAR BOT VALIDATION REPORT" in all_content
        assert "Total Tests: 2" in all_content
        assert "Success Rate:" in all_content

    @patch("builtins.print")
    def test_print_console_report_verbose(self, mock_print, validation_results):
        """Test print_console_report method in verbose mode."""
        details = {"key1": "value1", "key2": "value2"}
        validation_results.add_success("sources", "test1", "Success", details=details)

        validation_results.print_console_report(verbose=True)

        # Should print details when verbose
        all_prints = [
            str(call.args[0]) if call.args else str(call) for call in mock_print.call_args_list
        ]
        all_content = " ".join(all_prints)

        assert "key1: value1" in all_content
        assert "key2: value2" in all_content

    @patch("builtins.print")
    def test_print_console_report_with_failures_and_warnings(self, mock_print, validation_results):
        """Test print_console_report shows detailed results when there are failures/warnings."""
        validation_results.add_success("sources", "test1", "Success")
        validation_results.add_failure("cache", "test2", "Failure")
        validation_results.add_warning("cache", "test3", "Warning")

        validation_results.print_console_report(verbose=False)

        # Should show detailed results even without verbose when there are failures/warnings
        all_prints = [
            str(call.args[0]) if call.args else str(call) for call in mock_print.call_args_list
        ]
        all_content = " ".join(all_prints)

        assert "Detailed Results:" in all_content
        assert "✓" in all_content  # Success icon
        assert "✗" in all_content  # Failure icon
        assert "⚠" in all_content  # Warning icon

    def test_to_json_basic(self, validation_results):
        """Test to_json method with basic results."""
        validation_results.add_success("auth", "test1", "Success", duration_ms=100)
        validation_results.add_failure("api", "test2", "Failure", duration_ms=200)
        validation_results.finalize()

        json_str = validation_results.to_json()

        # Should be valid JSON
        data = json.loads(json_str)

        assert "summary" in data
        assert "items" in data
        assert len(data["items"]) == 2

        # Check summary structure
        summary = data["summary"]
        assert summary["total_tests"] == 2
        assert summary["status_counts"]["success"] == 1
        assert summary["status_counts"]["failure"] == 1

        # Check items structure
        items = data["items"]
        success_item = next(item for item in items if item["status"] == "success")
        failure_item = next(item for item in items if item["status"] == "failure")

        assert success_item["component"] == "auth"
        assert success_item["test_name"] == "test1"
        assert success_item["message"] == "Success"
        assert success_item["duration_ms"] == 100

        assert failure_item["component"] == "api"
        assert failure_item["test_name"] == "test2"
        assert failure_item["message"] == "Failure"
        assert failure_item["duration_ms"] == 200

    def test_to_json_with_details(self, validation_results):
        """Test to_json method includes details."""
        details = {"param1": "value1", "param2": 42}
        validation_results.add_success("auth", "test", "Success", details=details)

        json_str = validation_results.to_json()
        data = json.loads(json_str)

        item = data["items"][0]
        assert item["details"] == details

    def test_to_json_without_duration(self, validation_results):
        """Test to_json method handles items without duration."""
        validation_results.add_skipped("auth", "test", "Skipped")  # No duration for skipped

        json_str = validation_results.to_json()
        data = json.loads(json_str)

        item = data["items"][0]
        # Should not include duration_ms key when None
        assert "duration_ms" not in item

    @patch("builtins.print")
    def test_print_json_report(self, mock_print, validation_results):
        """Test print_json_report method."""
        validation_results.add_success("auth", "test", "Success")

        validation_results.print_json_report()

        # Should print JSON
        mock_print.assert_called_once()
        json_output = mock_print.call_args[0][0]

        # Should be valid JSON
        data = json.loads(json_output)
        assert "summary" in data
        assert "items" in data


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    def test_empty_validation_results(self):
        """Test ValidationResults with no items."""
        results = ValidationResults()

        summary = results.get_summary()

        assert summary["total_tests"] == 0
        assert summary["success_rate"] == 0.0
        assert not results.has_failures()
        assert not results.has_warnings()
        assert results.get_failures() == []
        assert results.get_warnings() == []

    def test_large_number_of_results(self):
        """Test ValidationResults with many items."""
        results = ValidationResults()

        # Add many results
        for i in range(100):
            if i % 4 == 0:
                results.add_success(f"component_{i % 5}", f"test_{i}", f"Success {i}")
            elif i % 4 == 1:
                results.add_failure(f"component_{i % 5}", f"test_{i}", f"Failure {i}")
            elif i % 4 == 2:
                results.add_warning(f"component_{i % 5}", f"test_{i}", f"Warning {i}")
            else:
                results.add_skipped(f"component_{i % 5}", f"test_{i}", f"Skipped {i}")

        summary = results.get_summary()

        assert summary["total_tests"] == 100
        assert summary["status_counts"]["success"] == 25
        assert summary["status_counts"]["failure"] == 25
        assert summary["status_counts"]["warning"] == 25
        assert summary["status_counts"]["skipped"] == 25
        assert summary["success_rate"] == 0.25

        # Test filtering methods
        assert len(results.get_failures()) == 25
        assert len(results.get_warnings()) == 25

    def test_validation_results_timing(self):
        """Test ValidationResults timing calculations."""
        results = ValidationResults()
        start_time = results.start_time

        # Add some delay before finalizing
        import time

        time.sleep(0.01)  # 10ms delay

        results.finalize()

        summary = results.get_summary()

        assert summary["total_duration_seconds"] > 0
        assert summary["total_duration_seconds"] < 1  # Should be very short

    def test_validation_item_timestamp_ordering(self):
        """Test that ValidationItems have proper timestamp ordering."""
        results = ValidationResults()

        # Add items with small delays
        import time

        results.add_success("auth", "test1", "First")
        time.sleep(0.001)
        results.add_success("auth", "test2", "Second")
        time.sleep(0.001)
        results.add_success("auth", "test3", "Third")

        # Timestamps should be in order
        assert (
            results.items[0].timestamp <= results.items[1].timestamp <= results.items[2].timestamp
        )

    def test_json_serialization_with_special_characters(self):
        """Test JSON serialization handles special characters."""
        results = ValidationResults()

        # Add result with special characters
        results.add_failure(
            "api",
            "test_unicode",
            "Error with unicode: 🚫 and quotes 'single' \"double\"",
            details={"unicode_key": "🔥", "newline": "line1\nline2"},
        )

        json_str = results.to_json()

        # Should be valid JSON
        data = json.loads(json_str)
        item = data["items"][0]

        assert "🚫" in item["message"]
        assert "🔥" in item["details"]["unicode_key"]
        assert "\n" in item["details"]["newline"]

    @patch("builtins.print")
    def test_console_report_icon_mapping(self, mock_print):
        """Test console report uses correct icons for each status."""
        results = ValidationResults()

        results.add_success("sources", "test1", "Success")
        results.add_failure("cache", "test2", "Failure")
        results.add_warning("cache", "test3", "Warning")
        results.add_skipped("display", "test4", "Skipped")

        results.print_console_report(verbose=True)

        all_prints = [
            str(call.args[0]) if call.args else str(call) for call in mock_print.call_args_list
        ]
        all_content = " ".join(all_prints)

        # Check for expected icons
        assert "✓" in all_content  # Success
        assert "✗" in all_content  # Failure
        assert "⚠" in all_content  # Warning
        assert "○" in all_content  # Skipped

    def test_component_tracking_across_operations(self):
        """Test that components_tested set is maintained correctly."""
        results = ValidationResults()

        assert len(results.components_tested) == 0

        results.add_success("auth", "test1", "Success")
        assert results.components_tested == {"auth"}

        results.add_failure("auth", "test2", "Failure")  # Same component
        assert results.components_tested == {"auth"}

        results.add_warning("api", "test3", "Warning")  # New component
        assert results.components_tested == {"auth", "api"}

        results.add_skipped("cache", "test4", "Skipped")  # Another new component
        assert results.components_tested == {"auth", "api", "cache"}

    def test_edge_case_zero_duration(self):
        """Test handling of zero duration."""
        results = ValidationResults()

        results.add_success("auth", "test", "Success", duration_ms=0)

        json_str = results.to_json()
        data = json.loads(json_str)

        item = data["items"][0]
        assert item["duration_ms"] == 0
