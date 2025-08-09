"""Tests for ValidationResults class and related components."""

import json
from datetime import datetime
from unittest.mock import patch

from calendarbot.validation.results import ValidationItem, ValidationResults, ValidationStatus


class TestValidationStatus:
    """Test suite for ValidationStatus enum."""

    def test_validation_status_has_expected_values(self) -> None:
        """Test ValidationStatus enum has expected values."""
        # Assert
        assert ValidationStatus.SUCCESS.value == "success"
        assert ValidationStatus.FAILURE.value == "failure"
        assert ValidationStatus.WARNING.value == "warning"
        assert ValidationStatus.SKIPPED.value == "skipped"


class TestValidationItem:
    """Test suite for ValidationItem class."""

    def test_init_when_required_fields_then_creates_instance(self) -> None:
        """Test initialization with required fields."""
        # Arrange & Act
        item = ValidationItem(
            component="test_component",
            test_name="test_name",
            status=ValidationStatus.SUCCESS,
            message="Test message",
        )

        # Assert
        assert item.component == "test_component"
        assert item.test_name == "test_name"
        assert item.status == ValidationStatus.SUCCESS
        assert item.message == "Test message"
        assert item.details is None  # Default is None, not empty dict
        assert isinstance(item.timestamp, datetime)
        assert item.duration_ms is None

    def test_init_when_all_fields_then_creates_instance(self) -> None:
        """Test initialization with all fields."""
        # Arrange
        details = {"key": "value"}
        timestamp = datetime.now()
        duration_ms = 100

        # Act
        item = ValidationItem(
            component="test_component",
            test_name="test_name",
            status=ValidationStatus.SUCCESS,
            message="Test message",
            details=details,
            timestamp=timestamp,
            duration_ms=duration_ms,
        )

        # Assert
        assert item.component == "test_component"
        assert item.test_name == "test_name"
        assert item.status == ValidationStatus.SUCCESS
        assert item.message == "Test message"
        assert item.details == details
        assert item.timestamp == timestamp
        assert item.duration_ms == duration_ms


class TestValidationResults:
    """Test suite for ValidationResults class."""

    def test_init_when_called_then_initializes_empty_results(self) -> None:
        """Test initialization creates empty results."""
        # Act
        results = ValidationResults()

        # Assert
        assert len(results.items) == 0
        assert isinstance(results.start_time, datetime)
        assert results.end_time is None
        assert len(results.components_tested) == 0

    def test_add_result_when_called_then_adds_item(self) -> None:
        """Test add_result adds a validation item."""
        # Arrange
        results = ValidationResults()
        component = "test_component"
        test_name = "test_name"
        status = ValidationStatus.SUCCESS
        message = "Test message"
        details = {"key": "value"}
        duration_ms = 100

        # Act
        results.add_result(component, test_name, status, message, details, duration_ms)

        # Assert
        assert len(results.items) == 1
        assert results.items[0].component == component
        assert results.items[0].test_name == test_name
        assert results.items[0].status == status
        assert results.items[0].message == message
        assert results.items[0].details == details
        assert results.items[0].duration_ms == duration_ms
        assert component in results.components_tested

    def test_add_result_when_no_details_then_uses_empty_dict(self) -> None:
        """Test add_result uses empty dict when no details provided."""
        # Arrange
        results = ValidationResults()

        # Act
        results.add_result("component", "test", ValidationStatus.SUCCESS, "message")

        # Assert
        assert results.items[0].details == {}

    def test_add_success_when_called_then_adds_success_result(self) -> None:
        """Test add_success adds a success result."""
        # Arrange
        results = ValidationResults()
        component = "test_component"
        test_name = "test_name"
        message = "Test message"
        details = {"key": "value"}
        duration_ms = 100

        # Act
        results.add_success(component, test_name, message, details, duration_ms)

        # Assert
        assert len(results.items) == 1
        assert results.items[0].component == component
        assert results.items[0].test_name == test_name
        assert results.items[0].status == ValidationStatus.SUCCESS
        assert results.items[0].message == message
        assert results.items[0].details == details
        assert results.items[0].duration_ms == duration_ms

    def test_add_failure_when_called_then_adds_failure_result(self) -> None:
        """Test add_failure adds a failure result."""
        # Arrange
        results = ValidationResults()
        component = "test_component"
        test_name = "test_name"
        message = "Test message"
        details = {"key": "value"}
        duration_ms = 100

        # Act
        results.add_failure(component, test_name, message, details, duration_ms)

        # Assert
        assert len(results.items) == 1
        assert results.items[0].component == component
        assert results.items[0].test_name == test_name
        assert results.items[0].status == ValidationStatus.FAILURE
        assert results.items[0].message == message
        assert results.items[0].details == details
        assert results.items[0].duration_ms == duration_ms

    def test_add_warning_when_called_then_adds_warning_result(self) -> None:
        """Test add_warning adds a warning result."""
        # Arrange
        results = ValidationResults()
        component = "test_component"
        test_name = "test_name"
        message = "Test message"
        details = {"key": "value"}
        duration_ms = 100

        # Act
        results.add_warning(component, test_name, message, details, duration_ms)

        # Assert
        assert len(results.items) == 1
        assert results.items[0].component == component
        assert results.items[0].test_name == test_name
        assert results.items[0].status == ValidationStatus.WARNING
        assert results.items[0].message == message
        assert results.items[0].details == details
        assert results.items[0].duration_ms == duration_ms

    def test_add_skipped_when_called_then_adds_skipped_result(self) -> None:
        """Test add_skipped adds a skipped result."""
        # Arrange
        results = ValidationResults()
        component = "test_component"
        test_name = "test_name"
        message = "Test message"
        details = {"key": "value"}

        # Act
        results.add_skipped(component, test_name, message, details)

        # Assert
        assert len(results.items) == 1
        assert results.items[0].component == component
        assert results.items[0].test_name == test_name
        assert results.items[0].status == ValidationStatus.SKIPPED
        assert results.items[0].message == message
        assert results.items[0].details == details
        assert results.items[0].duration_ms is None

    def test_finalize_when_called_then_sets_end_time(self) -> None:
        """Test finalize sets end_time."""
        # Arrange
        results = ValidationResults()
        assert results.end_time is None

        # Act
        results.finalize()

        # Assert
        assert results.end_time is not None
        assert isinstance(results.end_time, datetime)

    def test_get_summary_when_not_finalized_then_auto_finalizes(self) -> None:
        """Test get_summary auto-finalizes if not already finalized."""
        # Arrange
        results = ValidationResults()
        assert results.end_time is None

        # Act
        summary = results.get_summary()

        # Assert
        assert results.end_time is not None
        assert summary["end_time"] is not None

    def test_get_summary_when_no_items_then_returns_zero_success_rate(self) -> None:
        """Test get_summary returns zero success rate when no items."""
        # Arrange
        results = ValidationResults()

        # Act
        summary = results.get_summary()

        # Assert
        assert summary["success_rate"] == 0.0
        assert summary["total_tests"] == 0

    def test_get_summary_when_items_exist_then_calculates_statistics(self) -> None:
        """Test get_summary calculates statistics correctly."""
        # Arrange
        results = ValidationResults()

        # Add various results
        results.add_success("comp1", "test1", "Success 1")
        results.add_success("comp1", "test2", "Success 2")
        results.add_failure("comp1", "test3", "Failure 1")
        results.add_warning("comp2", "test1", "Warning 1")
        results.add_skipped("comp2", "test2", "Skipped 1")

        # Act
        summary = results.get_summary()

        # Assert
        assert summary["total_tests"] == 5
        assert len(summary["components_tested"]) == 2
        assert "comp1" in summary["components_tested"]
        assert "comp2" in summary["components_tested"]

        # Check status counts
        assert summary["status_counts"]["success"] == 2
        assert summary["status_counts"]["failure"] == 1
        assert summary["status_counts"]["warning"] == 1
        assert summary["status_counts"]["skipped"] == 1

        # Check component stats
        assert summary["component_stats"]["comp1"]["success"] == 2
        assert summary["component_stats"]["comp1"]["failure"] == 1
        assert summary["component_stats"]["comp2"]["warning"] == 1
        assert summary["component_stats"]["comp2"]["skipped"] == 1

        # Check success rate
        assert summary["success_rate"] == 2 / 5

    def test_has_failures_when_no_failures_then_returns_false(self) -> None:
        """Test has_failures returns False when no failures."""
        # Arrange
        results = ValidationResults()
        results.add_success("comp", "test", "Success")
        results.add_warning("comp", "test", "Warning")
        results.add_skipped("comp", "test", "Skipped")

        # Act
        has_failures = results.has_failures()

        # Assert
        assert has_failures is False

    def test_has_failures_when_failures_exist_then_returns_true(self) -> None:
        """Test has_failures returns True when failures exist."""
        # Arrange
        results = ValidationResults()
        results.add_success("comp", "test", "Success")
        results.add_failure("comp", "test", "Failure")

        # Act
        has_failures = results.has_failures()

        # Assert
        assert has_failures is True

    def test_has_warnings_when_no_warnings_then_returns_false(self) -> None:
        """Test has_warnings returns False when no warnings."""
        # Arrange
        results = ValidationResults()
        results.add_success("comp", "test", "Success")
        results.add_failure("comp", "test", "Failure")
        results.add_skipped("comp", "test", "Skipped")

        # Act
        has_warnings = results.has_warnings()

        # Assert
        assert has_warnings is False

    def test_has_warnings_when_warnings_exist_then_returns_true(self) -> None:
        """Test has_warnings returns True when warnings exist."""
        # Arrange
        results = ValidationResults()
        results.add_success("comp", "test", "Success")
        results.add_warning("comp", "test", "Warning")

        # Act
        has_warnings = results.has_warnings()

        # Assert
        assert has_warnings is True

    def test_get_failures_when_no_failures_then_returns_empty_list(self) -> None:
        """Test get_failures returns empty list when no failures."""
        # Arrange
        results = ValidationResults()
        results.add_success("comp", "test", "Success")

        # Act
        failures = results.get_failures()

        # Assert
        assert len(failures) == 0

    def test_get_failures_when_failures_exist_then_returns_failures(self) -> None:
        """Test get_failures returns list of failures when failures exist."""
        # Arrange
        results = ValidationResults()
        results.add_success("comp", "test1", "Success")
        results.add_failure("comp", "test2", "Failure 1")
        results.add_failure("comp", "test3", "Failure 2")

        # Act
        failures = results.get_failures()

        # Assert
        assert len(failures) == 2
        assert all(item.status == ValidationStatus.FAILURE for item in failures)
        assert "Failure 1" in [item.message for item in failures]
        assert "Failure 2" in [item.message for item in failures]

    def test_get_warnings_when_no_warnings_then_returns_empty_list(self) -> None:
        """Test get_warnings returns empty list when no warnings."""
        # Arrange
        results = ValidationResults()
        results.add_success("comp", "test", "Success")

        # Act
        warnings = results.get_warnings()

        # Assert
        assert len(warnings) == 0

    def test_get_warnings_when_warnings_exist_then_returns_warnings(self) -> None:
        """Test get_warnings returns list of warnings when warnings exist."""
        # Arrange
        results = ValidationResults()
        results.add_success("comp", "test1", "Success")
        results.add_warning("comp", "test2", "Warning 1")
        results.add_warning("comp", "test3", "Warning 2")

        # Act
        warnings = results.get_warnings()

        # Assert
        assert len(warnings) == 2
        assert all(item.status == ValidationStatus.WARNING for item in warnings)
        assert "Warning 1" in [item.message for item in warnings]
        assert "Warning 2" in [item.message for item in warnings]

    def test_print_console_report_when_called_then_prints_report(self) -> None:
        """Test print_console_report prints report to console."""
        # Arrange
        results = ValidationResults()
        results.add_success("comp1", "test1", "Success 1")
        results.add_failure("comp1", "test2", "Failure 1")

        # Act & Assert
        with patch("builtins.print") as mock_print:
            results.print_console_report()
            # Verify print was called multiple times
            assert mock_print.call_count > 5

    def test_print_console_report_when_verbose_then_prints_details(self) -> None:
        """Test print_console_report with verbose prints details."""
        # Arrange
        results = ValidationResults()
        results.add_success("comp1", "test1", "Success 1", {"detail_key": "detail_value"})

        # Act & Assert
        with patch("builtins.print") as mock_print:
            results.print_console_report(verbose=True)

            # Check that detail printing was called
            detail_printed = False
            for call_args in mock_print.call_args_list:
                args = call_args[0][0] if call_args[0] else ""
                if isinstance(args, str) and "detail_key: detail_value" in args:
                    detail_printed = True
                    break

            assert detail_printed

    def test_to_json_when_called_then_returns_json_string(self) -> None:
        """Test to_json returns valid JSON string."""
        # Arrange
        results = ValidationResults()
        results.add_success("comp1", "test1", "Success 1")
        results.add_failure("comp1", "test2", "Failure 1", {"error": "test error"})

        # Act
        json_str = results.to_json()

        # Assert
        # Verify it's a valid JSON string
        json_data = json.loads(json_str)
        assert "summary" in json_data
        assert "items" in json_data
        assert len(json_data["items"]) == 2

        # Check item serialization
        assert json_data["items"][0]["component"] == "comp1"
        assert json_data["items"][0]["test_name"] == "test1"
        assert json_data["items"][0]["status"] == "success"

        assert json_data["items"][1]["component"] == "comp1"
        assert json_data["items"][1]["test_name"] == "test2"
        assert json_data["items"][1]["status"] == "failure"
        assert json_data["items"][1]["details"]["error"] == "test error"

    def test_print_json_report_when_called_then_prints_json(self) -> None:
        """Test print_json_report prints JSON report."""
        # Arrange
        results = ValidationResults()
        results.add_success("comp1", "test1", "Success 1")

        # Act & Assert
        with patch("builtins.print") as mock_print:
            with patch.object(results, "to_json", return_value='{"test": "json"}') as mock_to_json:
                results.print_json_report()
                mock_to_json.assert_called_once()
                mock_print.assert_called_once_with('{"test": "json"}')
