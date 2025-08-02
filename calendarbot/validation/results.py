"""Validation results tracking and reporting for test mode."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ValidationStatus(Enum):
    """Status of a validation operation."""

    SUCCESS = "success"
    FAILURE = "failure"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ValidationItem:
    """Individual validation result item."""

    component: str
    test_name: str
    status: ValidationStatus
    message: str
    details: Optional[dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: Optional[int] = None


class ValidationResults:
    """Tracks and reports validation results for test mode."""

    def __init__(self) -> None:
        """Initialize validation results tracking."""
        self.items: list[ValidationItem] = []
        self.start_time: datetime = datetime.now()
        self.end_time: Optional[datetime] = None
        self.components_tested: set[str] = set()

    def add_result(
        self,
        component: str,
        test_name: str,
        status: ValidationStatus,
        message: str,
        details: Optional[dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Add a validation result.

        Args:
            component: Component being tested (sources, cache, display)
            test_name: Name of the specific test
            status: Validation status
            message: Human-readable message
            details: Optional additional details
            duration_ms: Optional test duration in milliseconds
        """
        item = ValidationItem(
            component=component,
            test_name=test_name,
            status=status,
            message=message,
            details=details or {},
            duration_ms=duration_ms,
        )
        self.items.append(item)
        self.components_tested.add(component)

    def add_success(
        self,
        component: str,
        test_name: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Add a successful validation result."""
        self.add_result(
            component, test_name, ValidationStatus.SUCCESS, message, details, duration_ms
        )

    def add_failure(
        self,
        component: str,
        test_name: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Add a failed validation result."""
        self.add_result(
            component, test_name, ValidationStatus.FAILURE, message, details, duration_ms
        )

    def add_warning(
        self,
        component: str,
        test_name: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Add a warning validation result."""
        self.add_result(
            component, test_name, ValidationStatus.WARNING, message, details, duration_ms
        )

    def add_skipped(
        self, component: str, test_name: str, message: str, details: Optional[dict[str, Any]] = None
    ) -> None:
        """Add a skipped validation result."""
        self.add_result(component, test_name, ValidationStatus.SKIPPED, message, details)

    def finalize(self) -> None:
        """Mark validation as complete."""
        self.end_time = datetime.now()

    def get_summary(self) -> dict[str, Any]:
        """Get validation summary statistics.

        Returns:
            Dictionary with summary statistics
        """
        if not self.end_time:
            self.finalize()

        # After finalize(), end_time should not be None
        assert self.end_time is not None
        total_duration = (self.end_time - self.start_time).total_seconds()

        # Count by status
        status_counts = {status.value: 0 for status in ValidationStatus}
        component_stats = {}

        for item in self.items:
            status_counts[item.status.value] += 1

            if item.component not in component_stats:
                component_stats[item.component] = {status.value: 0 for status in ValidationStatus}
            component_stats[item.component][item.status.value] += 1

        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_seconds": total_duration,
            "total_tests": len(self.items),
            "components_tested": sorted(self.components_tested),
            "status_counts": status_counts,
            "component_stats": component_stats,
            "success_rate": status_counts["success"] / len(self.items) if self.items else 0.0,
        }

    def has_failures(self) -> bool:
        """Check if any validation failed.

        Returns:
            True if any validation failed, False otherwise
        """
        return any(item.status == ValidationStatus.FAILURE for item in self.items)

    def has_warnings(self) -> bool:
        """Check if any validation had warnings.

        Returns:
            True if any validation had warnings, False otherwise
        """
        return any(item.status == ValidationStatus.WARNING for item in self.items)

    def get_failures(self) -> list[ValidationItem]:
        """Get all failed validation items.

        Returns:
            List of failed validation items
        """
        return [item for item in self.items if item.status == ValidationStatus.FAILURE]

    def get_warnings(self) -> list[ValidationItem]:
        """Get all warning validation items.

        Returns:
            List of warning validation items
        """
        return [item for item in self.items if item.status == ValidationStatus.WARNING]

    def print_console_report(self, verbose: bool = False) -> None:
        """Print validation report to console.

        Args:
            verbose: If True, show detailed information for each test
        """
        summary = self.get_summary()

        print("\n" + "=" * 60)
        print("CALENDAR BOT VALIDATION REPORT")
        print("=" * 60)

        # Summary section
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Duration: {summary['total_duration_seconds']:.2f}s")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        print()

        # Status counts
        print("Results Summary:")
        for status, count in summary["status_counts"].items():
            if count > 0:
                status_icon = {"success": "✓", "failure": "✗", "warning": "⚠", "skipped": "○"}.get(
                    status, "?"
                )
                print(f"  {status_icon} {status.title()}: {count}")
        print()

        # Component breakdown
        if summary["component_stats"]:
            print("Component Results:")
            for component, stats in summary["component_stats"].items():
                total_component = sum(stats.values())
                successes = stats["success"]
                print(f"  {component}: {successes}/{total_component} passed")
        print()

        # Detailed results
        if verbose or self.has_failures() or self.has_warnings():
            print("Detailed Results:")
            for item in self.items:
                status_icon = {
                    ValidationStatus.SUCCESS: "✓",
                    ValidationStatus.FAILURE: "✗",
                    ValidationStatus.WARNING: "⚠",
                    ValidationStatus.SKIPPED: "○",
                }.get(item.status, "?")

                duration_str = f" ({item.duration_ms}ms)" if item.duration_ms else ""
                print(
                    f"  {status_icon} {item.component}.{item.test_name}: {item.message}{duration_str}"
                )

                if verbose and item.details:
                    for key, value in item.details.items():
                        print(f"    {key}: {value}")

        print("=" * 60)

    def to_json(self) -> str:
        """Export validation results as JSON.

        Returns:
            JSON string representation of results
        """
        summary = self.get_summary()

        # Convert items to dictionaries
        items_data: list[dict[str, Any]] = []
        for item in self.items:
            item_data: dict[str, Any] = {
                "component": item.component,
                "test_name": item.test_name,
                "status": item.status.value,
                "message": item.message,
                "timestamp": item.timestamp.isoformat(),
                "details": item.details or {},
            }
            if item.duration_ms is not None:
                item_data["duration_ms"] = item.duration_ms
            items_data.append(item_data)

        data = {"summary": summary, "items": items_data}

        return json.dumps(data, indent=2)

    def print_json_report(self) -> None:
        """Print validation results as JSON."""
        print(self.to_json())
