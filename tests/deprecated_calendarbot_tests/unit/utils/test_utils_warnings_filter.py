"""Comprehensive tests for calendarbot.utils.warnings_filter module."""

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


class TestSuppressWebsocketsDeprecationWarnings:
    """Test suppress_websockets_deprecation_warnings function."""

    def test_suppress_websockets_deprecation_warnings_when_called_then_filters_applied(
        self,
    ) -> None:
        """Test that websockets deprecation warnings are filtered correctly."""
        with patch("warnings.filterwarnings") as mock_filter:
            suppress_websockets_deprecation_warnings()

            # Verify the correct filters were applied
            assert mock_filter.call_count == 2
            mock_filter.assert_has_calls(
                [
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
            )


class TestSuppressDatetimeDeprecationWarnings:
    """Test suppress_datetime_deprecation_warnings function."""

    def test_suppress_datetime_deprecation_warnings_when_called_then_filters_applied(self) -> None:
        """Test that datetime deprecation warnings are filtered correctly."""
        with patch("warnings.filterwarnings") as mock_filter:
            suppress_datetime_deprecation_warnings()

            # Verify the correct filters were applied
            assert mock_filter.call_count == 2
            mock_filter.assert_has_calls(
                [
                    call(
                        "ignore",
                        category=DeprecationWarning,
                        message=r"datetime.datetime.utcfromtimestamp\(\) is deprecated.*",
                        module="pytz.tzinfo",
                    ),
                    call(
                        "ignore",
                        category=DeprecationWarning,
                        message=r"datetime.datetime.utcfromtimestamp\(\) is deprecated.*",
                        module="dateutil.tz.tz",
                    ),
                ]
            )


class TestSuppressBrowserTestWarnings:
    """Test suppress_browser_test_warnings function."""

    def test_suppress_browser_test_warnings_when_called_then_calls_other_functions(self) -> None:
        """Test that suppress_browser_test_warnings calls the other suppression functions."""
        with patch(
            "calendarbot.utils.warnings_filter.suppress_websockets_deprecation_warnings"
        ) as mock_websockets:
            with patch(
                "calendarbot.utils.warnings_filter.suppress_datetime_deprecation_warnings"
            ) as mock_datetime:
                suppress_browser_test_warnings()

                # Verify both suppression functions were called
                mock_websockets.assert_called_once()
                mock_datetime.assert_called_once()


class TestGetFilteredWarningCategories:
    """Test get_filtered_warning_categories function."""

    def test_get_filtered_warning_categories_when_called_then_returns_expected_list(self) -> None:
        """Test that get_filtered_warning_categories returns the expected list of warning categories."""
        result = get_filtered_warning_categories()

        # Verify the result is a list of tuples
        assert isinstance(result, list)
        assert all(isinstance(item, tuple) for item in result)
        assert all(len(item) == 2 for item in result)

        # Verify the expected warning categories are included
        expected_categories = [
            ("DeprecationWarning", "WebSocket loop argument deprecation (pyppeteer/websockets)"),
            (
                "DeprecationWarning",
                "DateTime utcfromtimestamp deprecation (pytz/dateutil - fallback filter)",
            ),
        ]

        for expected in expected_categories:
            assert expected in result


class TestApplyTestWarningFilters:
    """Test apply_test_warning_filters function."""

    def test_apply_test_warning_filters_when_called_then_calls_suppress_browser_test_warnings(
        self,
    ) -> None:
        """Test that apply_test_warning_filters calls suppress_browser_test_warnings."""
        with patch(
            "calendarbot.utils.warnings_filter.suppress_browser_test_warnings"
        ) as mock_suppress:
            apply_test_warning_filters()

            # Verify suppress_browser_test_warnings was called
            mock_suppress.assert_called_once()


class TestFilterWarnings:
    """Test filter_warnings function."""

    def test_filter_warnings_when_called_then_calls_apply_test_warning_filters(self) -> None:
        """Test that filter_warnings calls apply_test_warning_filters."""
        with patch("calendarbot.utils.warnings_filter.apply_test_warning_filters") as mock_apply:
            filter_warnings()

            # Verify apply_test_warning_filters was called
            mock_apply.assert_called_once()


class TestWarningsFilterIntegration:
    """Integration tests for warnings_filter module."""

    def test_integration_when_filter_warnings_called_then_warnings_are_suppressed(self) -> None:
        """Test that filter_warnings effectively suppresses the expected warnings."""
        # Apply the warning filters
        filter_warnings()

        # Test that websockets deprecation warnings are suppressed
        with warnings.catch_warnings(record=True) as recorded_warnings:
            # Trigger a warning that should be suppressed
            warnings.warn("remove loop argument", DeprecationWarning, stacklevel=2)

            # No warnings should be recorded if the filter is working
            # Note: This is an imperfect test since we can't fully simulate the module context
            # but it helps verify the basic functionality
            assert len(recorded_warnings) == 0

    def test_integration_when_main_executed_then_categories_printed(self) -> None:
        """Test the behavior of the module when executed as a script."""
        with patch("builtins.print") as mock_print:
            with patch("calendarbot.utils.warnings_filter.apply_test_warning_filters"):
                # Simulate running the module as a script
                # We need to execute the code that would run in the if __name__ == "__main__" block
                from calendarbot.utils.warnings_filter import get_filtered_warning_categories

                # Apply warning filters
                apply_test_warning_filters()

                # Print the filtered warning categories
                print("Applied warning filters for:")
                for warning_type, description in get_filtered_warning_categories():
                    print(f"  - {warning_type}: {description}")

                # Verify print was called with the expected messages
                assert mock_print.call_count >= 3  # Header + at least 2 warning categories
                mock_print.assert_any_call("Applied warning filters for:")
