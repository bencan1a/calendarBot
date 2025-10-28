"""Unit tests for settings service layer."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from calendarbot.settings.exceptions import (
    SettingsError,
    SettingsPersistenceError,
    SettingsValidationError,
)
from calendarbot.settings.models import (
    ConflictResolutionSettings,
    DisplaySettings,
    EventFilterSettings,
    FilterPattern,
    SettingsData,
)
from calendarbot.settings.persistence import SettingsPersistence
from calendarbot.settings.service import SettingsService


class TestSettingsServiceInitialization:
    """Test SettingsService initialization and setup."""

    def test_settings_service_when_valid_config_then_initializes_successfully(
        self, temp_config_dir: Path, mock_calendarbot_settings: Mock
    ) -> None:
        """Test SettingsService initialization with valid configuration."""
        service = SettingsService(
            calendarbot_settings=mock_calendarbot_settings, config_dir=temp_config_dir
        )

        assert service.calendarbot_settings == mock_calendarbot_settings
        assert service.config_dir == temp_config_dir
        assert isinstance(service.persistence, SettingsPersistence)
        assert service._current_settings is None
        assert isinstance(service, SettingsService)

    def test_settings_service_when_no_calendarbot_settings_then_imports_default(
        self, temp_config_dir: Path
    ) -> None:
        """Test SettingsService imports default CalendarBot settings when none provided."""
        with patch("calendarbot.config.settings.settings") as mock_default_settings:
            mock_default_settings.config_dir = temp_config_dir

            service = SettingsService(config_dir=temp_config_dir)

            assert service.calendarbot_settings == mock_default_settings

    def test_settings_service_when_no_config_dir_then_uses_calendarbot_config_dir(
        self, mock_calendarbot_settings: Mock
    ) -> None:
        """Test SettingsService uses CalendarBot config directory when none provided."""
        service = SettingsService(calendarbot_settings=mock_calendarbot_settings)

        assert service.config_dir == mock_calendarbot_settings.config_dir

    @patch("calendarbot.settings.service.SettingsPersistence")
    def test_settings_service_when_persistence_creation_fails_then_raises_settings_error(
        self, mock_persistence_class: Mock, mock_calendarbot_settings: Mock
    ) -> None:
        """Test SettingsService raises error when persistence creation fails."""
        mock_persistence_class.side_effect = Exception("Persistence failed")

        with pytest.raises(SettingsError) as exc_info:
            SettingsService(calendarbot_settings=mock_calendarbot_settings)

        assert "Failed to initialize settings service" in str(exc_info.value)
        assert "Persistence failed" in exc_info.value.details["error"]


class TestSettingsServiceGetSettings:
    """Test SettingsService get_settings functionality."""

    def test_get_settings_when_first_call_then_loads_from_persistence(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test get_settings loads from persistence on first call."""
        with patch.object(
            settings_service.persistence, "load_settings", return_value=sample_settings_data
        ) as mock_load:
            settings = settings_service.get_settings()

            mock_load.assert_called_once()
            assert settings == sample_settings_data
            assert settings_service._current_settings == sample_settings_data

    def test_get_settings_when_cached_then_returns_cache(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test get_settings returns cached settings on subsequent calls."""
        settings_service._current_settings = sample_settings_data

        with patch.object(settings_service.persistence, "load_settings") as mock_load:
            settings = settings_service.get_settings()

            mock_load.assert_not_called()
            assert settings == sample_settings_data

    def test_get_settings_when_force_reload_then_loads_from_persistence(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test get_settings loads from persistence when force_reload is True."""
        settings_service._current_settings = sample_settings_data

        new_settings = SettingsData()
        with patch.object(
            settings_service.persistence, "load_settings", return_value=new_settings
        ) as mock_load:
            settings = settings_service.get_settings(force_reload=True)

            mock_load.assert_called_once()
            assert settings == new_settings

    @patch("calendarbot.settings.service.SettingsService._validate_settings_consistency")
    def test_get_settings_when_loaded_then_validates_consistency(
        self,
        mock_validate: Mock,
        settings_service: SettingsService,
        sample_settings_data: SettingsData,
    ) -> None:
        """Test get_settings validates settings consistency after loading."""
        with patch.object(
            settings_service.persistence, "load_settings", return_value=sample_settings_data
        ):
            settings_service.get_settings()

            mock_validate.assert_called_once_with(sample_settings_data)

    def test_get_settings_when_persistence_fails_then_raises_settings_error(
        self, settings_service: SettingsService
    ) -> None:
        """Test get_settings raises SettingsError when persistence fails."""
        with patch.object(
            settings_service.persistence, "load_settings", side_effect=Exception("Load failed")
        ):
            with pytest.raises(SettingsError) as exc_info:
                settings_service.get_settings()

            assert "Failed to get settings" in str(exc_info.value)
            assert "Load failed" in exc_info.value.details["error"]

    def test_get_settings_when_validation_fails_then_raises_settings_error(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test get_settings raises SettingsError when validation fails."""
        with (
            patch.object(
                settings_service.persistence, "load_settings", return_value=sample_settings_data
            ),
            patch.object(
                settings_service,
                "_validate_settings_consistency",
                side_effect=SettingsValidationError("Invalid"),
            ),
        ):
            with pytest.raises(SettingsError) as exc_info:
                settings_service.get_settings()

            assert "Failed to get settings" in str(exc_info.value)


class TestSettingsServiceUpdateSettings:
    """Test SettingsService update_settings functionality."""

    def test_update_settings_when_valid_data_then_updates_successfully(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test update_settings saves valid settings successfully."""
        with (
            patch.object(settings_service, "validate_settings", return_value=[]),
            patch.object(settings_service, "_validate_settings_consistency"),
            patch.object(settings_service.persistence, "save_settings", return_value=True),
        ):
            result = settings_service.update_settings(sample_settings_data)

            assert result == sample_settings_data
            assert result.metadata.last_modified_by == "settings_service"
            assert settings_service._current_settings == sample_settings_data

    def test_update_settings_when_validation_errors_then_raises_validation_error(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test update_settings raises ValidationError when validation fails."""
        with patch.object(
            settings_service, "validate_settings", return_value=["Error 1", "Error 2"]
        ):
            with pytest.raises(SettingsValidationError) as exc_info:
                settings_service.update_settings(sample_settings_data)

            assert "Settings validation failed" in str(exc_info.value)
            assert exc_info.value.validation_errors == ["Error 1", "Error 2"]

    def test_update_settings_when_persistence_save_fails_then_raises_persistence_error(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test update_settings raises PersistenceError when save returns False."""
        with (
            patch.object(settings_service, "validate_settings", return_value=[]),
            patch.object(settings_service, "_validate_settings_consistency"),
            patch.object(settings_service.persistence, "save_settings", return_value=False),
        ):
            with pytest.raises(SettingsPersistenceError) as exc_info:
                settings_service.update_settings(sample_settings_data)

            assert "Settings save operation returned false" in str(exc_info.value)
            assert exc_info.value.operation == "save"

    def test_update_settings_when_consistency_validation_fails_then_re_raises_validation_error(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test update_settings re-raises consistency validation errors."""
        validation_error = SettingsValidationError("Consistency error")

        with (
            patch.object(settings_service, "validate_settings", return_value=[]),
            patch.object(
                settings_service, "_validate_settings_consistency", side_effect=validation_error
            ),
        ):
            with pytest.raises(SettingsValidationError) as exc_info:
                settings_service.update_settings(sample_settings_data)

            assert exc_info.value == validation_error

    def test_update_settings_when_general_error_then_raises_settings_error(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test update_settings raises SettingsError for general exceptions."""
        with patch.object(
            settings_service, "validate_settings", side_effect=Exception("General error")
        ):
            with pytest.raises(SettingsError) as exc_info:
                settings_service.update_settings(sample_settings_data)

            assert "Failed to update settings" in str(exc_info.value)
            assert "General error" in exc_info.value.details["error"]


class TestSettingsServiceSpecificSettingsGetters:
    """Test SettingsService specific settings getter methods."""

    def test_get_filter_settings_when_called_then_returns_filter_settings(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test get_filter_settings returns event filter settings."""
        with patch.object(settings_service, "get_settings", return_value=sample_settings_data):
            filters = settings_service.get_filter_settings()

            assert filters == sample_settings_data.event_filters
            assert isinstance(filters, EventFilterSettings)

    def test_get_display_settings_when_called_then_returns_display_settings(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test get_display_settings returns display settings."""
        with patch.object(settings_service, "get_settings", return_value=sample_settings_data):
            display = settings_service.get_display_settings()

            assert display == sample_settings_data.display
            assert isinstance(display, DisplaySettings)

    def test_get_conflict_settings_when_called_then_returns_conflict_settings(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test get_conflict_settings returns conflict resolution settings."""
        with patch.object(settings_service, "get_settings", return_value=sample_settings_data):
            conflicts = settings_service.get_conflict_settings()

            assert conflicts == sample_settings_data.conflict_resolution
            assert isinstance(conflicts, ConflictResolutionSettings)


class TestSettingsServiceSpecificSettingsUpdaters:
    """Test SettingsService specific settings updater methods."""

    def test_update_filter_settings_when_called_then_updates_filter_settings(
        self,
        settings_service: SettingsService,
        sample_settings_data: SettingsData,
        sample_event_filter_settings: EventFilterSettings,
    ) -> None:
        """Test update_filter_settings updates only filter settings."""
        new_filters = EventFilterSettings(hide_all_day_events=False)

        with (
            patch.object(settings_service, "get_settings", return_value=sample_settings_data),
            patch.object(settings_service, "update_settings") as mock_update,
        ):
            mock_update.return_value = sample_settings_data

            result = settings_service.update_filter_settings(new_filters)

            mock_update.assert_called_once()
            updated_settings = mock_update.call_args[0][0]
            assert updated_settings.event_filters == new_filters
            assert result == sample_settings_data.event_filters

    def test_update_display_settings_when_called_then_updates_display_settings(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test update_display_settings updates only display settings."""
        new_display = DisplaySettings(default_layout="4x8")

        with (
            patch.object(settings_service, "get_settings", return_value=sample_settings_data),
            patch.object(settings_service, "update_settings") as mock_update,
        ):
            mock_update.return_value = sample_settings_data

            result = settings_service.update_display_settings(new_display)

            mock_update.assert_called_once()
            updated_settings = mock_update.call_args[0][0]
            assert updated_settings.display == new_display
            assert result == sample_settings_data.display

    def test_update_conflict_settings_when_called_then_updates_conflict_settings(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test update_conflict_settings updates only conflict resolution settings."""
        new_conflicts = ConflictResolutionSettings(conflict_display_mode="all")

        with (
            patch.object(settings_service, "get_settings", return_value=sample_settings_data),
            patch.object(settings_service, "update_settings") as mock_update,
        ):
            mock_update.return_value = sample_settings_data

            result = settings_service.update_conflict_settings(new_conflicts)

            mock_update.assert_called_once()
            updated_settings = mock_update.call_args[0][0]
            assert updated_settings.conflict_resolution == new_conflicts
            assert result == sample_settings_data.conflict_resolution

    def test_update_filter_settings_when_update_fails_then_raises_settings_error(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test update_filter_settings raises SettingsError when update fails."""
        new_filters = EventFilterSettings()

        with (
            patch.object(settings_service, "get_settings", return_value=sample_settings_data),
            patch.object(
                settings_service, "update_settings", side_effect=Exception("Update failed")
            ),
        ):
            with pytest.raises(SettingsError) as exc_info:
                settings_service.update_filter_settings(new_filters)

            assert "Failed to update filter settings" in str(exc_info.value)
            assert "Update failed" in exc_info.value.details["error"]


class TestSettingsServiceFilterPatternManagement:
    """Test SettingsService filter pattern management methods."""

    def test_add_filter_pattern_when_valid_pattern_then_adds_successfully(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test add_filter_pattern adds new filter pattern successfully."""
        with (
            patch.object(settings_service, "get_settings", return_value=sample_settings_data),
            patch.object(settings_service, "update_settings") as mock_update,
        ):
            pattern = settings_service.add_filter_pattern(
                pattern="New Pattern",
                is_regex=True,
                case_sensitive=True,
                description="Test pattern",
            )

            assert pattern.pattern == "New Pattern"
            assert pattern.is_regex is True
            assert pattern.case_sensitive is True
            assert pattern.description == "Test pattern"

            mock_update.assert_called_once()
            updated_settings = mock_update.call_args[0][0]
            assert pattern in updated_settings.event_filters.title_patterns

    def test_add_filter_pattern_when_invalid_pattern_then_raises_settings_error(
        self, settings_service: SettingsService
    ) -> None:
        """Test add_filter_pattern raises SettingsError when pattern creation fails."""
        with patch(
            "calendarbot.settings.service.FilterPattern",
            side_effect=SettingsValidationError("Invalid pattern"),
        ):
            with pytest.raises(SettingsError) as exc_info:
                settings_service.add_filter_pattern("invalid")

            assert "Failed to add filter pattern" in str(exc_info.value)
            assert "invalid" in exc_info.value.details["pattern"]

    def test_remove_filter_pattern_when_pattern_exists_then_removes_successfully(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test remove_filter_pattern removes existing pattern successfully."""
        # Add a pattern to remove
        target_pattern = FilterPattern(pattern="To Remove", is_regex=False)
        sample_settings_data.event_filters.title_patterns.append(target_pattern)

        with (
            patch.object(settings_service, "get_settings", return_value=sample_settings_data),
            patch.object(settings_service, "update_settings") as mock_update,
        ):
            result = settings_service.remove_filter_pattern("To Remove", is_regex=False)

            assert result is True
            mock_update.assert_called_once()

    def test_remove_filter_pattern_when_pattern_not_found_then_returns_false(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test remove_filter_pattern returns False when pattern not found."""
        with patch.object(settings_service, "get_settings", return_value=sample_settings_data):
            result = settings_service.remove_filter_pattern("Nonexistent", is_regex=False)

            assert result is False

    def test_toggle_filter_pattern_when_pattern_exists_then_toggles_active_state(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test toggle_filter_pattern toggles pattern active state."""
        # Add a pattern to toggle
        target_pattern = FilterPattern(pattern="To Toggle", is_regex=False, is_active=True)
        sample_settings_data.event_filters.title_patterns.append(target_pattern)

        with (
            patch.object(settings_service, "get_settings", return_value=sample_settings_data),
            patch.object(settings_service, "update_settings") as mock_update,
        ):
            result = settings_service.toggle_filter_pattern("To Toggle", is_regex=False)

            assert result is False  # Should be toggled to False
            mock_update.assert_called_once()

    def test_toggle_filter_pattern_when_pattern_not_found_then_returns_none(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test toggle_filter_pattern returns None when pattern not found."""
        with patch.object(settings_service, "get_settings", return_value=sample_settings_data):
            result = settings_service.toggle_filter_pattern("Nonexistent", is_regex=False)

            assert result is None


class TestSettingsServiceValidation:
    """Test SettingsService validation functionality."""

    @patch("calendarbot.settings.service.SettingsService._get_available_layouts")
    def test_validate_settings_when_valid_settings_then_returns_empty_errors(
        self,
        mock_get_layouts: Mock,
        settings_service: SettingsService,
        sample_settings_data: SettingsData,
    ) -> None:
        """Test validate_settings returns empty list for valid settings."""
        mock_get_layouts.return_value = ["whats-next-view", "4x8", "4x8"]

        errors = settings_service.validate_settings(sample_settings_data)

        assert errors == []

    @patch("calendarbot.settings.service.SettingsService._get_available_layouts")
    def test_validate_settings_when_invalid_layout_then_returns_layout_error(
        self,
        mock_get_layouts: Mock,
        settings_service: SettingsService,
        sample_settings_data: SettingsData,
    ) -> None:
        """Test validate_settings returns error for invalid layout."""
        mock_get_layouts.return_value = ["4x8"]  # whats-next-view not available

        errors = settings_service.validate_settings(sample_settings_data)

        assert len(errors) == 1
        assert "Invalid default layout 'whats-next-view'" in errors[0]
        assert "Available layouts: 4x8" in errors[0]

    def test_validate_settings_when_too_many_active_patterns_then_returns_performance_warning(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test validate_settings warns about too many active patterns."""
        # Create many active patterns
        active_patterns = [FilterPattern(pattern=f"pattern_{i}", is_active=True) for i in range(30)]
        sample_settings_data.event_filters.title_patterns = active_patterns

        errors = settings_service.validate_settings(sample_settings_data)

        assert len(errors) == 1
        assert "Too many active filter patterns (30)" in errors[0]
        assert "Consider disabling some patterns" in errors[0]

    def test_validate_settings_when_validation_exception_then_includes_error(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test validate_settings includes exception messages in error list."""
        with patch.object(
            settings_service, "_get_available_layouts", side_effect=Exception("Layout check failed")
        ):
            errors = settings_service.validate_settings(sample_settings_data)

            assert len(errors) == 1
            assert "Validation error: Layout check failed" in errors[0]

    def test_validate_settings_consistency_when_conflicting_settings_then_raises_validation_error(
        self, settings_service: SettingsService
    ) -> None:
        """Test _validate_settings_consistency raises error for conflicting settings."""
        settings = SettingsData()
        settings.display.display_density = "compact"
        settings.display.font_sizes = {"body": "extra-large"}

        with pytest.raises(SettingsValidationError) as exc_info:
            settings_service._validate_settings_consistency(settings)

        assert "Settings consistency validation failed" in str(exc_info.value)
        assert (
            "Compact display density conflicts with extra-large body font"
            in exc_info.value.validation_errors
        )

    def test_validate_settings_consistency_when_duplicate_patterns_then_raises_validation_error(
        self, settings_service: SettingsService
    ) -> None:
        """Test _validate_settings_consistency raises error for duplicate patterns."""
        settings = SettingsData()
        pattern1 = FilterPattern(pattern="duplicate")
        pattern2 = FilterPattern(pattern="duplicate")
        settings.event_filters.title_patterns = [pattern1, pattern2]

        with pytest.raises(SettingsValidationError) as exc_info:
            settings_service._validate_settings_consistency(settings)

        assert "Duplicate filter patterns detected" in exc_info.value.validation_errors

    def test_get_available_layouts_when_registry_available_then_returns_layouts(
        self, settings_service: SettingsService
    ) -> None:
        """Test _get_available_layouts returns layouts from registry."""
        with patch("calendarbot.layout.registry.LayoutRegistry") as mock_registry_class:
            mock_registry = Mock()
            mock_registry.get_available_layouts.return_value = ["4x8", "4x8", "whats-next-view"]
            mock_registry_class.return_value = mock_registry

            layouts = settings_service._get_available_layouts()

            assert layouts == ["4x8", "4x8", "whats-next-view"]

    def test_get_available_layouts_when_registry_fails_then_returns_fallback(
        self, settings_service: SettingsService, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test _get_available_layouts returns fallback when registry fails."""
        with patch(
            "calendarbot.layout.registry.LayoutRegistry", side_effect=Exception("Registry failed")
        ):
            layouts = settings_service._get_available_layouts()

            assert layouts == ["4x8", "whats-next-view"]
            assert "Could not get available layouts" in caplog.text


class TestSettingsServiceUtilityMethods:
    """Test SettingsService utility and helper methods."""

    def test_reset_to_defaults_when_called_then_creates_backup_and_resets(
        self, settings_service: SettingsService
    ) -> None:
        """Test reset_to_defaults creates backup and resets to default settings."""
        with (
            patch.object(settings_service.persistence, "create_backup") as mock_backup,
            patch.object(settings_service, "update_settings") as mock_update,
        ):
            default_settings = SettingsData()
            mock_update.return_value = default_settings

            result = settings_service.reset_to_defaults()

            mock_backup.assert_called_once_with("pre_reset")
            mock_update.assert_called_once()

            # Check that defaults were passed to update_settings
            updated_settings = mock_update.call_args[0][0]
            assert updated_settings.metadata.last_modified_by == "reset_operation"
            assert result == default_settings

    def test_reset_to_defaults_when_operation_fails_then_raises_settings_error(
        self, settings_service: SettingsService
    ) -> None:
        """Test reset_to_defaults raises SettingsError when operation fails."""
        with patch.object(
            settings_service.persistence, "create_backup", side_effect=Exception("Backup failed")
        ):
            with pytest.raises(SettingsError) as exc_info:
                settings_service.reset_to_defaults()

            assert "Failed to reset settings to defaults" in str(exc_info.value)
            assert "Backup failed" in exc_info.value.details["error"]

    def test_export_settings_when_called_then_delegates_to_persistence(
        self, settings_service: SettingsService, tmp_path
    ) -> None:
        """Test export_settings delegates to persistence layer."""
        export_path = tmp_path / "export.json"

        with patch.object(
            settings_service.persistence, "export_settings", return_value=True
        ) as mock_export:
            result = settings_service.export_settings(export_path)

            mock_export.assert_called_once_with(export_path)
            assert result is True

    def test_export_settings_when_persistence_fails_then_raises_settings_error(
        self, settings_service: SettingsService, tmp_path
    ) -> None:
        """Test export_settings raises SettingsError when persistence fails."""
        export_path = tmp_path / "export.json"

        with patch.object(
            settings_service.persistence, "export_settings", side_effect=Exception("Export failed")
        ):
            with pytest.raises(SettingsError) as exc_info:
                settings_service.export_settings(export_path)

            assert "Failed to export settings" in str(exc_info.value)
            assert str(export_path) in exc_info.value.details["export_path"]

    def test_import_settings_when_called_then_delegates_to_persistence_and_updates_cache(
        self, settings_service: SettingsService, sample_settings_data: SettingsData, tmp_path
    ) -> None:
        """Test import_settings delegates to persistence and updates cache."""
        import_path = tmp_path / "import.json"

        with patch.object(
            settings_service.persistence, "import_settings", return_value=sample_settings_data
        ) as mock_import:
            result = settings_service.import_settings(import_path)

            mock_import.assert_called_once_with(import_path)
            assert result == sample_settings_data
            assert settings_service._current_settings == sample_settings_data

    def test_import_settings_when_persistence_fails_then_raises_settings_error(
        self, settings_service: SettingsService, tmp_path
    ) -> None:
        """Test import_settings raises SettingsError when persistence fails."""
        import_path = tmp_path / "import.json"

        with patch.object(
            settings_service.persistence, "import_settings", side_effect=Exception("Import failed")
        ):
            with pytest.raises(SettingsError) as exc_info:
                settings_service.import_settings(import_path)

            assert "Failed to import settings" in str(exc_info.value)
            assert str(import_path) in exc_info.value.details["import_path"]

    def test_get_settings_info_when_called_then_returns_comprehensive_info(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test get_settings_info returns comprehensive settings information."""
        persistence_info = {"backup_count": 3, "settings_size": 1024}

        # Set cache to simulate loaded settings
        settings_service._current_settings = sample_settings_data

        with (
            patch.object(settings_service, "get_settings", return_value=sample_settings_data),
            patch.object(
                settings_service.persistence, "get_settings_info", return_value=persistence_info
            ),
        ):
            info = settings_service.get_settings_info()

            assert "settings_data" in info
            assert "persistence_info" in info
            assert "service_info" in info

            # Check settings data info
            settings_info = info["settings_data"]
            assert "active_filters" in settings_info
            assert "default_layout" in settings_info
            assert "schema_version" in settings_info

            # Check service info
            service_info = info["service_info"]
            assert service_info["calendarbot_integration"] is True
            assert service_info["cache_status"] == "loaded"

    def test_get_settings_info_when_error_occurs_then_returns_error_info(
        self, settings_service: SettingsService, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test get_settings_info returns error information when operation fails."""
        with patch.object(
            settings_service, "get_settings", side_effect=Exception("Settings failed")
        ):
            info = settings_service.get_settings_info()

            assert "error" in info
            assert "service_info" in info
            assert info["service_info"]["cache_status"] == "error"
            assert "Error getting settings info" in caplog.text

    def test_create_backup_when_called_then_delegates_to_persistence(
        self, settings_service: SettingsService
    ) -> None:
        """Test create_backup delegates to persistence layer."""
        backup_path = Path("/tmp/backup.json")

        with patch.object(
            settings_service.persistence, "create_backup", return_value=backup_path
        ) as mock_backup:
            result = settings_service.create_backup("test_backup")

            mock_backup.assert_called_once_with("test_backup")
            assert result == backup_path

    def test_create_backup_when_persistence_fails_then_raises_settings_error(
        self, settings_service: SettingsService
    ) -> None:
        """Test create_backup raises SettingsError when persistence fails."""
        with patch.object(
            settings_service.persistence, "create_backup", side_effect=Exception("Backup failed")
        ):
            with pytest.raises(SettingsError) as exc_info:
                settings_service.create_backup("test_backup")

            assert "Failed to create settings backup" in str(exc_info.value)
            assert "test_backup" in exc_info.value.details["backup_name"]

    def test_list_backups_when_called_then_returns_formatted_backup_list(
        self, settings_service: SettingsService
    ) -> None:
        """Test list_backups returns formatted list of backups."""
        backup_data = [
            (Path("/tmp/backup1.json"), datetime(2023, 7, 18, 12, 0, 0)),
            (Path("/tmp/backup2.json"), datetime(2023, 7, 17, 12, 0, 0)),
        ]

        with patch.object(
            settings_service.persistence, "list_backups", return_value=backup_data
        ) as mock_list:
            backups = settings_service.list_backups()

            mock_list.assert_called_once()
            assert len(backups) == 2
            assert backups[0] == (Path("/tmp/backup1.json"), "2023-07-18 12:00:00")
            assert backups[1] == (Path("/tmp/backup2.json"), "2023-07-17 12:00:00")

    def test_list_backups_when_persistence_fails_then_returns_empty_list(
        self, settings_service: SettingsService, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test list_backups returns empty list when persistence fails."""
        with patch.object(
            settings_service.persistence, "list_backups", side_effect=Exception("List failed")
        ):
            backups = settings_service.list_backups()

            assert backups == []
            assert "Error listing backups" in caplog.text


class TestSettingsServiceCachingBehavior:
    """Test SettingsService caching behavior and cache management."""

    def test_get_settings_when_multiple_calls_then_uses_cache(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test get_settings uses cache for multiple calls."""
        with patch.object(
            settings_service.persistence, "load_settings", return_value=sample_settings_data
        ) as mock_load:
            # First call loads from persistence
            settings1 = settings_service.get_settings()
            # Second call uses cache
            settings2 = settings_service.get_settings()

            mock_load.assert_called_once()  # Only called once
            assert settings1 == settings2
            assert settings1 is settings2  # Same object reference

    def test_update_settings_when_successful_then_updates_cache(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test update_settings updates the cache after successful save."""
        with (
            patch.object(settings_service, "validate_settings", return_value=[]),
            patch.object(settings_service, "_validate_settings_consistency"),
            patch.object(settings_service.persistence, "save_settings", return_value=True),
        ):
            settings_service.update_settings(sample_settings_data)

            # Cache should be updated
            assert settings_service._current_settings == sample_settings_data

    def test_import_settings_when_successful_then_updates_cache(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test import_settings updates cache after successful import."""
        import_path = Path("/tmp/import.json")

        with patch.object(
            settings_service.persistence, "import_settings", return_value=sample_settings_data
        ):
            settings_service.import_settings(import_path)

            # Cache should be updated
            assert settings_service._current_settings == sample_settings_data


class TestSettingsServiceErrorHandling:
    """Test SettingsService error handling and exception propagation."""

    def test_service_when_persistence_operations_fail_then_propagates_persistence_errors(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test service propagates PersistenceError from persistence layer."""
        persistence_error = SettingsPersistenceError("Persistence failed", operation="save")

        with (
            patch.object(settings_service, "validate_settings", return_value=[]),
            patch.object(settings_service, "_validate_settings_consistency"),
            patch.object(
                settings_service.persistence, "save_settings", side_effect=persistence_error
            ),
        ):
            with pytest.raises(SettingsPersistenceError) as exc_info:
                settings_service.update_settings(sample_settings_data)

            assert exc_info.value == persistence_error

    def test_service_when_validation_errors_occur_then_propagates_validation_errors(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test service propagates ValidationError from validation layer."""
        validation_error = SettingsValidationError("Validation failed")

        with patch.object(
            settings_service, "_validate_settings_consistency", side_effect=validation_error
        ):
            with pytest.raises(SettingsValidationError) as exc_info:
                settings_service.update_settings(sample_settings_data)

            assert exc_info.value == validation_error

    def test_service_when_unexpected_errors_occur_then_wraps_in_settings_error(
        self, settings_service: SettingsService, sample_settings_data: SettingsData
    ) -> None:
        """Test service wraps unexpected errors in SettingsError."""
        with patch.object(
            settings_service, "validate_settings", side_effect=RuntimeError("Unexpected error")
        ):
            with pytest.raises(SettingsError) as exc_info:
                settings_service.update_settings(sample_settings_data)

            assert "Failed to update settings" in str(exc_info.value)
            assert "Unexpected error" in exc_info.value.details["error"]


class TestSettingsServiceIntegrationScenarios:
    """Test SettingsService integration scenarios and workflows."""

    def test_complete_settings_workflow_when_normal_usage_then_works_correctly(
        self, settings_service: SettingsService, temp_config_dir: Path
    ) -> None:
        """Test complete settings workflow from load to update."""
        # Create a real persistence instance for integration testing
        settings_service.persistence = SettingsPersistence(temp_config_dir)

        # Get initial settings (should be defaults)
        initial_settings = settings_service.get_settings()
        assert initial_settings.event_filters.hide_all_day_events is False

        # Add a filter pattern
        pattern = settings_service.add_filter_pattern("Test Pattern", description="Test")
        assert pattern.pattern == "Test Pattern"

        # Verify the pattern was added
        updated_settings = settings_service.get_settings()
        assert len(updated_settings.event_filters.title_patterns) == 1
        assert updated_settings.event_filters.title_patterns[0].pattern == "Test Pattern"

        # Update display settings
        new_display = DisplaySettings(default_layout="4x8", display_density="compact")
        settings_service.update_display_settings(new_display)

        # Verify display settings were updated
        final_settings = settings_service.get_settings()
        assert final_settings.display.default_layout == "4x8"
        assert final_settings.display.display_density == "compact"

        # Verify pattern is still there
        assert len(final_settings.event_filters.title_patterns) == 1
