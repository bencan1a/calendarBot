"""Helper functions for constructing and validating test data in calendarbot_lite tests."""

from datetime import datetime
from typing import Any, Optional


def build_ics_event(
    summary: str,
    dtstart: str,
    dtend: str,
    rrule: Optional[str] = None,
    exdate: Optional[str] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """
    Build an ICS event string programmatically.

    Generates an RFC 5545 compliant iCalendar string with a single event.
    Useful for dynamically creating test fixtures with specific properties.

    Args:
        summary: Event title/summary
        dtstart: Start datetime in ISO format (YYYY-MM-DDTHH:MM:SS) or
                 iCal format (YYYYMMDDTHHMMSSZ)
        dtend: End datetime in ISO format (YYYY-MM-DDTHH:MM:SS) or
               iCal format (YYYYMMDDTHHMMSSZ)
        rrule: Optional RRULE string (e.g., "FREQ=DAILY;COUNT=5")
        exdate: Optional EXDATE string in iCal format (YYYYMMDDTHHMMSSZ)
        location: Optional location string
        description: Optional description string
        **kwargs: Additional iCalendar properties as key=value pairs
                  (e.g., uid="custom-uid", status="CONFIRMED")

    Returns:
        Complete ICS calendar string with the event

    Example:
        >>> ics = build_ics_event(
        ...     summary="Team Meeting",
        ...     dtstart="20240115T100000Z",
        ...     dtend="20240115T110000Z",
        ...     location="Room 101",
        ...     rrule="FREQ=WEEKLY;COUNT=3"
        ... )
    """
    # Normalize datetime formats to iCal format (YYYYMMDDTHHMMSSZ)
    dtstart_normalized = _normalize_datetime(dtstart)
    dtend_normalized = _normalize_datetime(dtend)

    # Generate default UID if not provided
    uid = kwargs.pop("uid", f"test-event-{hash(summary)}@calendarbot.test")

    # Generate DTSTAMP (current time in iCal format)
    dtstamp = kwargs.pop("dtstamp", _get_current_dtstamp())

    # Build event lines
    event_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//CalendarBot Test//EN",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTART:{dtstart_normalized}",
        f"DTEND:{dtend_normalized}",
        f"SUMMARY:{summary}",
    ]

    # Add optional fields
    if location:
        event_lines.append(f"LOCATION:{location}")

    if description:
        # Escape special characters in description
        escaped_desc = description.replace("\\", "\\\\").replace(",", "\\,")
        event_lines.append(f"DESCRIPTION:{escaped_desc}")

    if rrule:
        event_lines.append(f"RRULE:{rrule}")

    if exdate:
        exdate_normalized = _normalize_datetime(exdate)
        event_lines.append(f"EXDATE:{exdate_normalized}")

    # Add any additional custom properties
    for key, value in kwargs.items():
        # Convert key to uppercase iCal format
        key_upper = key.upper().replace("_", "-")
        event_lines.append(f"{key_upper}:{value}")

    # Add DTSTAMP and close event
    event_lines.extend([f"DTSTAMP:{dtstamp}", "END:VEVENT", "END:VCALENDAR"])

    return "\n".join(event_lines)


def assert_event_matches(
    actual: dict,
    expected: dict,
    fields: Optional[list[str]] = None,
) -> None:
    """
    Assert that an event dict matches expected values.

    Performs deep comparison of event dictionaries with helpful error messages
    that show which field failed and what the difference was.

    Args:
        actual: Parsed event dict from calendarbot_lite (the result to test)
        expected: Expected event values (ground truth)
        fields: Optional list of fields to check. If None, checks all fields
                present in the expected dict. Common fields include:
                - summary, location, description
                - start, end (datetime strings or objects)
                - uid, dtstart, dtend
                - rrule, exdate

    Raises:
        AssertionError: If events don't match, with detailed message about
                        which field(s) failed and the expected vs actual values

    Example:
        >>> actual_event = parse_ics_event(ics_string)
        >>> expected = {
        ...     "summary": "Team Meeting",
        ...     "location": "Room 101",
        ...     "start": "2024-01-15T10:00:00Z"
        ... }
        >>> assert_event_matches(actual_event, expected)
    """
    # Determine which fields to check
    fields_to_check = fields if fields is not None else list(expected.keys())

    errors = []

    for field in fields_to_check:
        if field not in expected:
            continue

        expected_value = expected[field]

        if field not in actual:
            errors.append(f"Field '{field}' missing from actual event")
            continue

        actual_value = actual[field]

        # Compare values with type-aware comparison
        if not _values_match(actual_value, expected_value):
            errors.append(
                f"Field '{field}' mismatch:\n"
                f"  Expected: {expected_value!r} (type: {type(expected_value).__name__})\n"
                f"  Actual:   {actual_value!r} (type: {type(actual_value).__name__})"
            )

    if errors:
        error_message = "Event matching failed:\n" + "\n".join(errors)
        raise AssertionError(error_message)


# ==================== Private Helper Functions ====================


def _normalize_datetime(dt_string: str) -> str:
    """
    Normalize datetime string to iCal format (YYYYMMDDTHHMMSSZ).

    Args:
        dt_string: Datetime in ISO format (2024-01-15T10:00:00Z) or
                   iCal format (20240115T100000Z)

    Returns:
        Datetime in iCal format (20240115T100000Z)
    """
    # If already in iCal format, return as-is
    if "T" in dt_string and "-" not in dt_string:
        return dt_string

    # Parse ISO format and convert to iCal
    try:
        # Handle various ISO formats
        dt_string_clean = dt_string.replace("Z", "+00:00")
        dt = datetime.fromisoformat(dt_string_clean)
        return dt.strftime("%Y%m%dT%H%M%SZ")
    except ValueError as e:
        raise ValueError(
            f"Invalid datetime format: {dt_string}. "
            f"Expected ISO (YYYY-MM-DDTHH:MM:SSZ) or iCal (YYYYMMDDTHHMMSSZ) format."
        ) from e


def _get_current_dtstamp() -> str:
    """
    Get current timestamp in iCal DTSTAMP format.

    Returns:
        Current UTC time in YYYYMMDDTHHMMSSZ format
    """
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _values_match(actual: Any, expected: Any) -> bool:
    """
    Compare two values with type-aware logic.

    Handles comparison of:
    - Datetime objects and datetime strings
    - Nested dicts and lists
    - Primitive types

    Args:
        actual: Actual value from parsed event
        expected: Expected value from test

    Returns:
        True if values match, False otherwise
    """
    # Handle datetime comparisons
    if isinstance(expected, datetime) and isinstance(actual, str):
        try:
            actual_dt = datetime.fromisoformat(actual.replace("Z", "+00:00"))
            return actual_dt == expected
        except (ValueError, AttributeError):
            return False

    if isinstance(actual, datetime) and isinstance(expected, str):
        try:
            expected_dt = datetime.fromisoformat(expected.replace("Z", "+00:00"))
            return actual == expected_dt
        except (ValueError, AttributeError):
            return False

    # Handle dict comparisons
    if isinstance(expected, dict) and isinstance(actual, dict):
        if set(expected.keys()) != set(actual.keys()):
            return False
        return all(_values_match(actual[k], expected[k]) for k in expected.keys())

    # Handle list comparisons
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return False
        return all(_values_match(a, e) for a, e in zip(actual, expected))

    # Direct comparison for primitives
    return bool(actual == expected)
