"""
Unit tests for automatic cache invalidation in SettingsService.
"""

import time
from pathlib import Path
from unittest.mock import patch

from calendarbot.settings.service import SettingsService


class TestAutomaticCacheInvalidation:
    """Test automatic cache invalidation when settings file is modified externally."""

    def test_cache_invalidation_when_file_modified_externally_then_reloads_automatically(
        self, temp_config_dir: Path
    ) -> None:
        """Test that cache automatically reloads when settings file is modified externally."""
        # Create first service instance (simulates web server)
        service1 = SettingsService(config_dir=temp_config_dir)

        # Load initial settings to establish cache
        initial_settings = service1.get_filter_settings()
        initial_count = len(initial_settings.hidden_events)

        # Add some hidden events
        initial_settings.hidden_events.update({"event-1", "event-2"})
        service1.update_filter_settings(initial_settings)

        # Verify service1 sees the events (from cache)
        cached_settings = service1.get_filter_settings()
        assert len(cached_settings.hidden_events) == 2

        # Create second service instance (simulates external script)
        service2 = SettingsService(config_dir=temp_config_dir)

        # Modify settings via second service (external change)
        external_settings = service2.get_filter_settings()
        external_settings.hidden_events.clear()
        service2.update_filter_settings(external_settings)

        # Small delay to ensure different modification times
        time.sleep(0.01)

        # First service should automatically detect the change
        updated_settings = service1.get_filter_settings()
        assert len(updated_settings.hidden_events) == 0

    def test_normal_caching_when_no_external_changes_then_uses_cache(
        self, temp_config_dir: Path
    ) -> None:
        """Test that normal caching still works when there are no external changes."""
        service = SettingsService(config_dir=temp_config_dir)

        # Load settings to establish cache
        settings = service.get_filter_settings()
        settings.hidden_events.add("test-event")
        service.update_filter_settings(settings)

        # Mock the persistence layer to track calls
        with patch.object(
            service.persistence, "load_settings", wraps=service.persistence.load_settings
        ) as mock_load:
            # Multiple get_settings calls should use cache (not reload)
            for _ in range(3):
                cached_settings = service.get_filter_settings()
                assert len(cached_settings.hidden_events) == 1

            # Should only have called load_settings once during the loop (not on each get)
            assert mock_load.call_count == 0  # Should use cache, not reload

    def test_cache_tracks_modification_time_correctly(self, temp_config_dir: Path) -> None:
        """Test that modification time tracking works correctly."""
        service = SettingsService(config_dir=temp_config_dir)

        # Initial state - no modification time tracked
        assert service._settings_file_mtime is None

        # Create and save settings - should establish modification time
        settings = service.get_settings()
        service.update_settings(settings)  # This ensures file is created and mtime is tracked

        # File should now exist and mtime should be tracked
        assert service.persistence.settings_file.exists()
        assert service._settings_file_mtime is not None
        initial_mtime = service._settings_file_mtime

        # Small delay to ensure different modification times
        time.sleep(0.01)

        # Update settings again - should update modification time
        settings.event_filters.hide_all_day_events = True
        service.update_settings(settings)
        assert service._settings_file_mtime > initial_mtime

    def test_file_modification_detection_when_file_missing_then_returns_false(
        self, temp_config_dir: Path
    ) -> None:
        """Test that missing settings file is handled gracefully."""
        service = SettingsService(config_dir=temp_config_dir)

        # Remove settings file
        if service.persistence.settings_file.exists():
            service.persistence.settings_file.unlink()

        # Should return False for missing file
        assert service._is_settings_file_modified() is False

    def test_file_modification_detection_when_first_check_then_returns_false(
        self, temp_config_dir: Path
    ) -> None:
        """Test that first modification check returns False."""
        service = SettingsService(config_dir=temp_config_dir)

        # Create settings file
        settings = service.get_settings()
        service.update_settings(settings)

        # Reset tracking
        service._settings_file_mtime = None

        # First check should return False
        assert service._is_settings_file_modified() is False

    def test_multiple_external_changes_detected_correctly(self, temp_config_dir: Path) -> None:
        """Test that multiple external changes are detected correctly."""
        service1 = SettingsService(config_dir=temp_config_dir)
        service2 = SettingsService(config_dir=temp_config_dir)

        # Establish initial cache
        settings = service1.get_filter_settings()
        settings.hidden_events.add("initial-event")
        service1.update_filter_settings(settings)

        # First external change
        ext_settings = service2.get_filter_settings()
        ext_settings.hidden_events.add("external-event-1")
        service2.update_filter_settings(ext_settings)

        time.sleep(0.01)

        # Service1 should detect first change
        updated1 = service1.get_filter_settings()
        assert "external-event-1" in updated1.hidden_events

        # Second external change
        ext_settings = service2.get_filter_settings()
        ext_settings.hidden_events.add("external-event-2")
        service2.update_filter_settings(ext_settings)

        time.sleep(0.01)

        # Service1 should detect second change
        updated2 = service1.get_filter_settings()
        assert "external-event-2" in updated2.hidden_events
        assert len(updated2.hidden_events) == 3  # initial + external-1 + external-2
