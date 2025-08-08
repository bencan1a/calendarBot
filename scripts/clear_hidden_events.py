#!/usr/bin/env python3
"""
Script to remove hidden status from all events by clearing the hidden_events set.
"""

import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from calendarbot.settings.service import SettingsService


def clear_all_hidden_events() -> None:
    """Clear all hidden events from the settings."""
    try:
        # Initialize settings service
        settings_service = SettingsService()

        # Get current filter settings
        filter_settings = settings_service.get_filter_settings()

        # Count current hidden events
        hidden_count = len(filter_settings.hidden_events)

        if hidden_count == 0:
            print("No hidden events found.")
            return

        print(f"Found {hidden_count} hidden events:")
        for graph_id in filter_settings.hidden_events:
            print(f"  - {graph_id}")

        # Clear all hidden events
        filter_settings.hidden_events.clear()

        # Update settings
        settings_service.update_filter_settings(filter_settings)

        print(f"\nSuccessfully cleared {hidden_count} hidden events.")
        print("All events are now visible.")

    except Exception as e:
        logging.exception(f"Failed to clear hidden events: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    clear_all_hidden_events()
