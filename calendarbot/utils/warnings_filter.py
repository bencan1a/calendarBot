#!/usr/bin/env python3
"""
Warning filters for suppressing known deprecation warnings from dependencies.

This module provides utilities to suppress specific deprecation warnings that come
from third-party libraries while preserving warnings for application code.
"""

import warnings
from typing import List, Tuple


def suppress_websockets_deprecation_warnings() -> None:
    """
    Suppress WebSocket deprecation warnings from pyppeteer/websockets.

    These warnings occur because pyppeteer 2.0.0 uses deprecated websockets API
    with explicit loop arguments. The warnings are:
    - "remove loop argument" from websockets.legacy.client
    - "remove loop argument" from websockets.legacy.protocol

    This is a temporary fix until pyppeteer is updated or replaced.
    """
    # Suppress specific websockets deprecation warnings
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message="remove loop argument",
        module="websockets.legacy.client",
    )

    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message="remove loop argument",
        module="websockets.legacy.protocol",
    )


def suppress_datetime_deprecation_warnings() -> None:
    """
    Suppress datetime.utcfromtimestamp deprecation warnings from third-party libraries.

    These warnings occur in older versions of pytz and dateutil libraries that use
    the deprecated datetime.datetime.utcfromtimestamp() function. These warnings are:
    - "datetime.datetime.utcfromtimestamp() is deprecated" from pytz.tzinfo
    - "datetime.datetime.utcfromtimestamp() is deprecated" from dateutil.tz.tz

    NOTE: This filter is a fallback for older library versions. The preferred
    solution is to use updated library versions (pytz>=2025.2, python-dateutil>=2.9.0)
    which have fixed these deprecation warnings.
    """
    # Suppress pytz datetime deprecation warnings
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message="datetime.datetime.utcfromtimestamp\\(\\) is deprecated.*",
        module="pytz.tzinfo",
    )

    # Suppress dateutil datetime deprecation warnings
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message="datetime.datetime.utcfromtimestamp\\(\\) is deprecated.*",
        module="dateutil.tz.tz",
    )


def suppress_browser_test_warnings() -> None:
    """
    Suppress all known deprecation warnings that occur during browser testing.

    This includes:
    - WebSocket loop argument warnings from pyppeteer
    - DateTime deprecation warnings from third-party libraries (fallback)
    - Any other known browser automation warnings
    """
    suppress_websockets_deprecation_warnings()
    suppress_datetime_deprecation_warnings()

    # Add any other browser-related warning filters here
    # Example for other potential warnings:
    # warnings.filterwarnings(
    #     "ignore",
    #     category=DeprecationWarning,
    #     message="some other deprecated feature",
    #     module="some.module"
    # )


def get_filtered_warning_categories() -> List[Tuple[str, str]]:
    """
    Get a list of all warning categories being filtered.

    Returns:
        List of tuples containing (warning_type, description)
    """
    return [
        ("DeprecationWarning", "WebSocket loop argument deprecation (pyppeteer/websockets)"),
        (
            "DeprecationWarning",
            "DateTime utcfromtimestamp deprecation (pytz/dateutil - fallback filter)",
        ),
        # Add other filtered warnings here for documentation
    ]


def apply_test_warning_filters() -> None:
    """
    Apply all warning filters appropriate for test environments.

    This should be called at the beginning of test suites to suppress
    known third-party deprecation warnings while preserving warnings
    for application code.
    """
    suppress_browser_test_warnings()


# Convenience function for one-liner import and application
def filter_warnings() -> None:
    """Convenience function to apply all warning filters."""
    apply_test_warning_filters()


if __name__ == "__main__":
    # Demonstrate the warning filters
    apply_test_warning_filters()

    print("Applied warning filters for:")
    for warning_type, description in get_filtered_warning_categories():
        print(f"  - {warning_type}: {description}")
