"""Navigation state management for interactive date browsing."""

import logging
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class NavigationDirection(Enum):
    """Direction for navigation."""

    FORWARD = "forward"
    BACKWARD = "backward"


class NavigationState:
    """Manages the currently selected date and navigation state."""

    def __init__(self, initial_date: Optional[date] = None):
        """Initialize navigation state.

        Args:
            initial_date: Initial date to display, defaults to today
        """
        self._selected_date = initial_date or date.today()
        self._today = date.today()
        self._change_callbacks: List[Callable[[date], None]] = []

        logger.debug(f"Navigation state initialized with date: {self._selected_date}")

    @property
    def selected_date(self) -> date:
        """Get the currently selected date."""
        return self._selected_date

    @property
    def today(self) -> date:
        """Get today's date."""
        return self._today

    def update_today(self) -> None:
        """Update the internal reference to today's date."""
        self._today = date.today()

    def is_today(self) -> bool:
        """Check if the selected date is today."""
        return self._selected_date == self._today

    def is_past(self) -> bool:
        """Check if the selected date is in the past."""
        return self._selected_date < self._today

    def is_future(self) -> bool:
        """Check if the selected date is in the future."""
        return self._selected_date > self._today

    def days_from_today(self) -> int:
        """Get number of days from today (negative for past, positive for future)."""
        delta = self._selected_date - self._today
        return delta.days

    def get_relative_description(self) -> str:
        """Get a human-readable description of the selected date relative to today."""
        days_diff = self.days_from_today()

        if days_diff == 0:
            return "Today"
        elif days_diff == 1:
            return "Tomorrow"
        elif days_diff == -1:
            return "Yesterday"
        elif days_diff > 1:
            return f"In {days_diff} days"
        else:  # days_diff < -1
            return f"{abs(days_diff)} days ago"

    def navigate_forward(self, days: int = 1) -> date:
        """Navigate forward by specified number of days.

        Args:
            days: Number of days to move forward

        Returns:
            New selected date
        """
        old_date = self._selected_date
        self._selected_date = self._selected_date + timedelta(days=days)

        logger.debug(f"Navigated forward {days} days: {old_date} -> {self._selected_date}")
        self._notify_change()
        return self._selected_date

    def navigate_backward(self, days: int = 1) -> date:
        """Navigate backward by specified number of days.

        Args:
            days: Number of days to move backward

        Returns:
            New selected date
        """
        old_date = self._selected_date
        self._selected_date = self._selected_date - timedelta(days=days)

        logger.debug(f"Navigated backward {days} days: {old_date} -> {self._selected_date}")
        self._notify_change()
        return self._selected_date

    def jump_to_today(self) -> date:
        """Jump to today's date.

        Returns:
            Today's date
        """
        old_date = self._selected_date
        self._selected_date = self._today

        logger.debug(f"Jumped to today: {old_date} -> {self._selected_date}")
        self._notify_change()
        return self._selected_date

    def jump_to_date(self, target_date: date) -> date:
        """Jump to a specific date.

        Args:
            target_date: Date to jump to

        Returns:
            New selected date
        """
        old_date = self._selected_date
        self._selected_date = target_date

        logger.debug(f"Jumped to date: {old_date} -> {self._selected_date}")
        self._notify_change()
        return self._selected_date

    def jump_to_start_of_week(self) -> date:
        """Jump to the start of the current week (Monday).

        Returns:
            First day of the week
        """
        days_since_monday = self._selected_date.weekday()
        start_of_week = self._selected_date - timedelta(days=days_since_monday)
        return self.jump_to_date(start_of_week)

    def jump_to_end_of_week(self) -> date:
        """Jump to the end of the current week (Sunday).

        Returns:
            Last day of the week
        """
        days_until_sunday = 6 - self._selected_date.weekday()
        end_of_week = self._selected_date + timedelta(days=days_until_sunday)
        return self.jump_to_date(end_of_week)

    def get_formatted_date(self, format_string: str = "%A, %B %d, %Y") -> str:
        """Get formatted string representation of selected date.

        Args:
            format_string: strftime format string

        Returns:
            Formatted date string
        """
        return self._selected_date.strftime(format_string)

    def get_display_date(self) -> str:
        """Get display-friendly date string with relative information."""
        base_format = self._selected_date.strftime("%A, %B %d")

        if self.is_today():
            return f"TODAY - {base_format}"
        else:
            relative = self.get_relative_description()
            return f"{base_format} ({relative})"

    def add_change_callback(self, callback: Callable[[date], None]) -> None:
        """Add a callback to be called when the selected date changes.

        Args:
            callback: Function to call with new date when it changes
        """
        self._change_callbacks.append(callback)
        logger.debug("Added date change callback")

    def remove_change_callback(self, callback: Callable[[date], None]) -> None:
        """Remove a date change callback.

        Args:
            callback: Callback function to remove
        """
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
            logger.debug("Removed date change callback")

    def _notify_change(self) -> None:
        """Notify all registered callbacks of date change."""
        for callback in self._change_callbacks:
            try:
                callback(self._selected_date)
            except Exception as e:
                logger.error(f"Error in date change callback: {e}")

    def get_week_context(self) -> dict:
        """Get context about the selected date's week.

        Returns:
            Dictionary with week information
        """
        start_of_week = self._selected_date - timedelta(days=self._selected_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        return {
            "selected_date": self._selected_date,
            "start_of_week": start_of_week,
            "end_of_week": end_of_week,
            "day_of_week": self._selected_date.weekday(),
            "week_number": self._selected_date.isocalendar()[1],
        }

    def __str__(self) -> str:
        """String representation of navigation state."""
        return f"NavigationState(selected={self._selected_date}, today={self._today})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"NavigationState(selected_date={self._selected_date!r}, "
            f"today={self._today!r}, is_today={self.is_today()})"
        )
