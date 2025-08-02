"""
Unit tests for NavigationState functionality.

This module tests the NavigationState class, focusing on date navigation,
display string generation, and the removal of relative date indicators.
"""

from datetime import date, timedelta
from unittest.mock import Mock

import pytest

from calendarbot.ui.navigation import NavigationState


class TestNavigationState:
    """Test NavigationState functionality."""

    def test_init_defaults_to_today(self):
        """Test that NavigationState initializes to today's date."""
        nav = NavigationState()
        assert nav.selected_date == date.today()

    def test_init_with_specific_date(self):
        """Test NavigationState initialization with specific date."""
        test_date = date(2024, 1, 15)
        nav = NavigationState(test_date)
        assert nav.selected_date == test_date

    def test_navigate_forward(self):
        """Test navigating forward by one day."""
        nav = NavigationState(date(2024, 1, 15))
        nav.navigate_forward()
        assert nav.selected_date == date(2024, 1, 16)

    def test_navigate_backward(self):
        """Test navigating backward by one day."""
        nav = NavigationState(date(2024, 1, 15))
        nav.navigate_backward()
        assert nav.selected_date == date(2024, 1, 14)

    def test_jump_to_today(self):
        """Test jumping to today."""
        nav = NavigationState(date(2024, 1, 15))
        nav.jump_to_today()
        assert nav.selected_date == date.today()

    def test_jump_to_specific_date(self):
        """Test jumping to a specific date."""
        nav = NavigationState(date(2024, 1, 15))
        target_date = date(2024, 2, 1)
        nav.jump_to_date(target_date)
        assert nav.selected_date == target_date


class TestNavigationStateDisplayDate:
    """Test NavigationState display date generation without 'In X Days' indicators."""

    def test_get_display_date_today(self):
        """Test display date for today - should show 'TODAY' prefix."""
        nav = NavigationState(date.today())
        result = nav.get_display_date()

        # Should contain TODAY prefix and formatted date
        assert "TODAY" in result
        assert date.today().strftime("%A") in result
        # Should not contain "(In X Days)" text
        assert "(In" not in result
        assert "Days)" not in result

    def test_get_display_date_tomorrow(self):
        """Test display date for tomorrow - should show only formatted date."""
        tomorrow = date.today() + timedelta(days=1)
        nav = NavigationState(tomorrow)
        result = nav.get_display_date()

        # Should contain the formatted date but no relative description
        assert tomorrow.strftime("%A") in result
        assert tomorrow.strftime("%B %d") in result
        # Should not contain relative descriptions or "(In X Days)" text
        assert "Tomorrow" not in result
        assert "(In 1 Days)" not in result
        assert "(In" not in result
        assert "Days)" not in result

    def test_get_display_date_future_date(self):
        """Test display date for future date - should not include '(In X Days)' text."""
        future_date = date.today() + timedelta(days=5)
        nav = NavigationState(future_date)
        result = nav.get_display_date()

        # Should contain the formatted date but no "(In X Days)" indicators
        assert future_date.strftime("%A") in result
        # get_relative_description() returns empty string for future dates > 1 day
        # so result should be like "Friday, July 15 ()"
        assert "(In 5 Days)" not in result
        assert "(In" not in result
        assert "Days)" not in result

    def test_get_display_date_yesterday(self):
        """Test display date for yesterday - should show only formatted date."""
        yesterday = date.today() - timedelta(days=1)
        nav = NavigationState(yesterday)
        result = nav.get_display_date()

        # Should contain the formatted date but no relative description
        assert yesterday.strftime("%A") in result
        assert yesterday.strftime("%B %d") in result
        # Should not contain relative descriptions or "(In X Days)" text
        assert "Yesterday" not in result
        assert "(In" not in result
        assert "Days)" not in result

    def test_get_display_date_past_date(self):
        """Test display date for past date - should show only formatted date."""
        past_date = date.today() - timedelta(days=10)
        nav = NavigationState(past_date)
        result = nav.get_display_date()

        # Should contain the formatted date but no relative description
        assert past_date.strftime("%A") in result
        assert past_date.strftime("%B %d") in result
        # Should not contain relative descriptions or "(In X Days)" text
        assert "days ago" not in result
        assert "(In" not in result
        assert "Days)" not in result

    def test_get_relative_description_future_empty(self):
        """Test that get_relative_description returns empty for future dates > 1 day."""
        future_date = date.today() + timedelta(days=3)
        nav = NavigationState(future_date)
        result = nav.get_relative_description()

        # Should return empty string for future dates beyond tomorrow
        assert result == ""

    def test_get_display_date_consistency(self):
        """Test that display date format is consistent across different dates."""
        dates_to_test = [
            date.today() - timedelta(days=7),
            date.today() - timedelta(days=1),
            date.today(),
            date.today() + timedelta(days=1),
            date.today() + timedelta(days=7),
        ]

        results = []
        for test_date in dates_to_test:
            nav = NavigationState(test_date)
            result = nav.get_display_date()
            results.append(result)

            # None should contain "(In X Days)" indicators
            assert "(In" not in result
            assert "Days)" not in result

        # All results should be non-empty strings
        assert all(isinstance(result, str) and len(result) > 0 for result in results)


class TestNavigationStateIntegration:
    """Test NavigationState integration with other components."""

    def test_navigation_state_with_mock_renderer(self):
        """Test NavigationState integration with mock renderer."""
        nav = NavigationState(date(2024, 1, 15))

        # Mock renderer that would use the display date
        mock_renderer = Mock()
        mock_renderer.render_header = Mock(return_value="<h1>Header</h1>")

        # Get display date and verify it doesn't contain "(In X Days)" indicators
        display_date = nav.get_display_date()
        mock_renderer.render_header(display_date)

        # Verify the mock was called and the display date is clean
        mock_renderer.render_header.assert_called_once_with(display_date)
        assert "(In" not in display_date
        assert "Days)" not in display_date

    def test_navigation_workflow_display_dates(self):
        """Test a complete navigation workflow and verify display dates."""
        nav = NavigationState(date.today())

        # Navigate through several days and check each display date
        for i in range(-3, 4):  # Test from 3 days ago to 3 days from now
            nav = NavigationState(date.today() + timedelta(days=i))
            display_date = nav.get_display_date()

            # Each display date should be clean of "(In X Days)" indicators
            assert "(In" not in display_date, f"Display date for day {i} contains '(In'"
            assert "Days)" not in display_date, f"Display date for day {i} contains 'Days)'"
            assert len(display_date) > 0, f"Display date for day {i} is empty"

    def test_navigation_methods_workflow(self):
        """Test navigation methods work together correctly."""
        nav = NavigationState(date(2024, 1, 15))

        # Test forward navigation
        nav.navigate_forward()
        assert nav.selected_date == date(2024, 1, 16)

        # Test backward navigation
        nav.navigate_backward(2)  # Should accept days parameter
        assert nav.selected_date == date(2024, 1, 14)

        # Test jump to today
        nav.jump_to_today()
        assert nav.selected_date == date.today()

        # Verify display date is clean throughout
        display_date = nav.get_display_date()
        assert "(In" not in display_date
        assert "Days)" not in display_date


if __name__ == "__main__":
    pytest.main([__file__])
