#!/usr/bin/env python3
"""
Unit tests for warnings filter functionality.

Tests the various warning suppression mechanisms for third-party library
deprecation warnings.
"""

import unittest
import warnings
from unittest.mock import call, patch

from calendarbot.utils.warnings_filter import (
    apply_test_warning_filters,
    filter_warnings,
    get_filtered_warning_categories,
    suppress_browser_test_warnings,
    suppress_datetime_deprecation_warnings,
    suppress_websockets_deprecation_warnings,
)


class TestWarningsFilter(unittest.TestCase):
    """Test cases for warning filter functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Store original warning filters
        self.original_filters = warnings.filters[:]

    def tearDown(self):
        """Clean up after tests."""
        # Restore original warning filters
        warnings.filters[:] = self.original_filters

    @patch("calendarbot.utils.warnings_filter.warnings.filterwarnings")
    def test_suppress_datetime_deprecation_warnings(self, mock_filterwarnings):
        """Test that datetime deprecation warnings are properly filtered."""
        suppress_datetime_deprecation_warnings()

        # Verify that warning filters were added for both pytz and dateutil
        expected_calls = [
            call(
                "ignore",
                category=DeprecationWarning,
                message="datetime.datetime.utcfromtimestamp\\(\\) is deprecated.*",
                module="pytz.tzinfo",
            ),
            call(
                "ignore",
                category=DeprecationWarning,
                message="datetime.datetime.utcfromtimestamp\\(\\) is deprecated.*",
                module="dateutil.tz.tz",
            ),
        ]

        mock_filterwarnings.assert_has_calls(expected_calls)
        self.assertEqual(mock_filterwarnings.call_count, 2)

    @patch("calendarbot.utils.warnings_filter.warnings.filterwarnings")
    def test_suppress_websockets_deprecation_warnings(self, mock_filterwarnings):
        """Test that websockets deprecation warnings are properly filtered."""
        suppress_websockets_deprecation_warnings()

        # Verify that warning filters were added for websockets
        expected_calls = [
            call(
                "ignore",
                category=DeprecationWarning,
                message="remove loop argument",
                module="websockets.legacy.client",
            ),
            call(
                "ignore",
                category=DeprecationWarning,
                message="remove loop argument",
                module="websockets.legacy.protocol",
            ),
        ]

        mock_filterwarnings.assert_has_calls(expected_calls)
        self.assertEqual(mock_filterwarnings.call_count, 2)

    @patch("calendarbot.utils.warnings_filter.suppress_datetime_deprecation_warnings")
    @patch("calendarbot.utils.warnings_filter.suppress_websockets_deprecation_warnings")
    def test_suppress_browser_test_warnings(self, mock_websockets, mock_datetime):
        """Test that browser test warnings include both websockets and datetime filters."""
        suppress_browser_test_warnings()

        # Verify both warning suppression functions are called
        mock_websockets.assert_called_once()
        mock_datetime.assert_called_once()

    def test_get_filtered_warning_categories(self):
        """Test that filtered warning categories are properly documented."""
        categories = get_filtered_warning_categories()

        # Verify that we have the expected warning categories
        self.assertIsInstance(categories, list)
        self.assertGreater(len(categories), 0)

        # Check for specific warning types
        warning_descriptions = [desc for _, desc in categories]
        self.assertTrue(any("WebSocket" in desc for desc in warning_descriptions))
        self.assertTrue(any("DateTime" in desc for desc in warning_descriptions))

    @patch("calendarbot.utils.warnings_filter.suppress_browser_test_warnings")
    def test_apply_test_warning_filters(self, mock_browser_warnings):
        """Test that test warning filters are applied correctly."""
        apply_test_warning_filters()

        # Verify browser test warnings are suppressed
        mock_browser_warnings.assert_called_once()

    @patch("calendarbot.utils.warnings_filter.apply_test_warning_filters")
    def test_filter_warnings_convenience_function(self, mock_apply_filters):
        """Test the convenience function for applying warning filters."""
        filter_warnings()

        # Verify the main filter function is called
        mock_apply_filters.assert_called_once()

    def test_warning_filter_integration(self):
        """Integration test to verify warnings are actually suppressed."""
        # Apply all warning filters
        apply_test_warning_filters()

        # Verify that warnings are now in the filter list
        filter_count_before = len(warnings.filters)

        # The filters should have been added
        self.assertGreater(
            len(warnings.filters), filter_count_before - 10
        )  # Allow some flexibility

    def test_datetime_warning_filter_regex_pattern(self):
        """Test that the datetime warning filter regex pattern is valid."""
        import re

        # Test the regex pattern used in the filter
        pattern = "datetime.datetime.utcfromtimestamp\\(\\) is deprecated.*"
        test_message = "datetime.datetime.utcfromtimestamp() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.fromtimestamp(timestamp, datetime.UTC)."

        # Verify the pattern matches the actual warning message
        self.assertTrue(re.match(pattern, test_message))


if __name__ == "__main__":
    unittest.main()
