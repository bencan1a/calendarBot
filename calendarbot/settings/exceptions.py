"""
Settings-specific exceptions for CalendarBot settings management.

This module defines custom exception classes for handling various error conditions
that can occur during settings operations, including validation errors, persistence
failures, and general settings management issues.
"""

from typing import Any, Optional


class SettingsError(Exception):
    """Base exception for all settings-related errors.

    This serves as the parent class for all settings-specific exceptions,
    allowing for broad exception handling when needed.

    Args:
        message: Human-readable error description
        details: Optional dictionary containing additional error context

    Example:
        >>> raise SettingsError("Configuration failed", {"component": "persistence"})
    """

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class SettingsValidationError(SettingsError):
    """Exception raised when settings validation fails.

    This exception is raised when user-provided settings data fails validation,
    such as invalid regex patterns, out-of-range values, or malformed data structures.

    Args:
        message: Human-readable validation error description
        field_name: Name of the field that failed validation
        field_value: The invalid value that caused the error
        validation_errors: List of specific validation error messages
        details: Additional context about the validation failure

    Example:
        >>> raise SettingsValidationError(
        ...     "Invalid regex pattern",
        ...     field_name="pattern",
        ...     field_value="[unclosed",
        ...     validation_errors=["Missing closing bracket"]
        ... )
    """

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        validation_errors: Optional[list[str]] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.field_name = field_name
        self.field_value = field_value
        self.validation_errors = validation_errors or []

        # Build comprehensive details
        error_details = details or {}
        if field_name:
            error_details["field_name"] = field_name
        if field_value is not None:
            error_details["field_value"] = str(field_value)
        if self.validation_errors:
            error_details["validation_errors"] = self.validation_errors

        super().__init__(message, error_details)


class SettingsPersistenceError(SettingsError):
    """Exception raised when settings persistence operations fail.

    This exception is raised when there are issues reading from or writing to
    the settings storage backend, such as file system permissions, disk space,
    or data corruption issues.

    Args:
        message: Human-readable persistence error description
        operation: The operation that failed (load, save, backup, etc.)
        file_path: Path to the file involved in the operation
        original_error: The underlying exception that caused the failure
        details: Additional context about the persistence failure

    Example:
        >>> raise SettingsPersistenceError(
        ...     "Failed to save settings",
        ...     operation="save",
        ...     file_path="/home/user/.config/calendarbot/settings.json",
        ...     original_error=PermissionError("Permission denied")
        ... )
    """

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        file_path: Optional[str] = None,
        original_error: Optional[Exception] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.operation = operation
        self.file_path = file_path
        self.original_error = original_error

        # Build comprehensive details
        error_details = details or {}
        if operation:
            error_details["operation"] = operation
        if file_path:
            error_details["file_path"] = file_path
        if original_error:
            error_details["original_error"] = str(original_error)
            error_details["error_type"] = type(original_error).__name__

        super().__init__(message, error_details)


class SettingsSchemaError(SettingsError):
    """Exception raised when settings schema migration or compatibility issues occur.

    This exception is raised when there are problems with settings data format
    compatibility, schema migration failures, or version mismatches.

    Args:
        message: Human-readable schema error description
        current_version: The current schema version
        expected_version: The expected schema version
        migration_path: Available migration path, if any
        details: Additional context about the schema issue

    Example:
        >>> raise SettingsSchemaError(
        ...     "Schema version mismatch",
        ...     current_version="0.9.0",
        ...     expected_version="1.0.0",
        ...     migration_path="automatic"
        ... )
    """

    def __init__(
        self,
        message: str,
        current_version: Optional[str] = None,
        expected_version: Optional[str] = None,
        migration_path: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.current_version = current_version
        self.expected_version = expected_version
        self.migration_path = migration_path

        # Build comprehensive details
        error_details = details or {}
        if current_version:
            error_details["current_version"] = current_version
        if expected_version:
            error_details["expected_version"] = expected_version
        if migration_path:
            error_details["migration_path"] = migration_path

        super().__init__(message, error_details)
