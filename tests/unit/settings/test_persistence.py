"""Unit tests for settings persistence layer."""

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, call, mock_open, patch

import pytest

from calendarbot.settings.exceptions import SettingsPersistenceError, SettingsSchemaError
from calendarbot.settings.models import SettingsData
from calendarbot.settings.persistence import SettingsPersistence


class TestSettingsPersistenceInitialization:
    """Test SettingsPersistence initialization and setup."""

    def test_settings_persistence_when_valid_config_dir_then_initializes_successfully(
        self, temp_config_dir: Path
    ) -> None:
        """Test SettingsPersistence initialization with valid config directory."""
        persistence = SettingsPersistence(temp_config_dir)

        assert persistence.config_dir == temp_config_dir
        assert persistence.settings_file == temp_config_dir / "settings.json"
        assert persistence.backup_dir == temp_config_dir / "settings_backups"
        assert persistence.max_backups == 5
        assert isinstance(persistence, SettingsPersistence)

    def test_settings_persistence_when_custom_filename_then_sets_correctly(
        self, temp_config_dir: Path
    ) -> None:
        """Test SettingsPersistence initialization with custom filename."""
        persistence = SettingsPersistence(temp_config_dir, settings_filename="custom.json")

        assert persistence.settings_file == temp_config_dir / "custom.json"

    def test_settings_persistence_when_custom_max_backups_then_sets_correctly(
        self, temp_config_dir: Path
    ) -> None:
        """Test SettingsPersistence initialization with custom max backups."""
        persistence = SettingsPersistence(temp_config_dir, max_backups=10)

        assert persistence.max_backups == 10

    def test_settings_persistence_when_directories_created_then_exist(
        self, temp_config_dir: Path
    ) -> None:
        """Test SettingsPersistence creates required directories."""
        # Remove directory first to test creation
        shutil.rmtree(temp_config_dir)

        persistence = SettingsPersistence(temp_config_dir)

        assert temp_config_dir.exists()
        assert temp_config_dir.is_dir()
        assert persistence.backup_dir.exists()
        assert persistence.backup_dir.is_dir()

    @patch("pathlib.Path.mkdir")
    def test_settings_persistence_when_directory_creation_fails_then_raises_persistence_error(
        self, mock_mkdir: Mock, temp_config_dir: Path
    ) -> None:
        """Test SettingsPersistence raises error when directory creation fails."""
        mock_mkdir.side_effect = OSError("Permission denied")

        with pytest.raises(SettingsPersistenceError) as exc_info:
            SettingsPersistence(temp_config_dir)

        assert "Failed to create settings directory" in str(exc_info.value)
        assert exc_info.value.operation == "initialize"
        assert str(temp_config_dir) in str(exc_info.value)


class TestSettingsPersistenceLoadSettings:
    """Test SettingsPersistence load_settings functionality."""

    def test_load_settings_when_file_exists_then_loads_successfully(
        self, settings_persistence: SettingsPersistence, populated_settings_file: Path
    ) -> None:
        """Test load_settings loads existing settings file successfully."""
        settings = settings_persistence.load_settings()

        assert isinstance(settings, SettingsData)
        assert settings.event_filters.hide_all_day_events is True
        assert len(settings.event_filters.title_patterns) == 1
        assert settings.display.default_layout == "whats-next-view"

    def test_load_settings_when_file_missing_then_returns_defaults(
        self, settings_persistence: SettingsPersistence
    ) -> None:
        """Test load_settings returns default settings when file doesn't exist."""
        settings = settings_persistence.load_settings()

        assert isinstance(settings, SettingsData)
        # Should be default values
        assert settings.event_filters.hide_all_day_events is False
        assert len(settings.event_filters.title_patterns) == 0
        assert settings.display.default_layout == "4x8"

    def test_load_settings_when_file_corrupted_then_falls_back_to_backup(
        self, temp_config_dir: Path, sample_json_settings_data: str
    ) -> None:
        """Test load_settings falls back to backup when primary file is corrupted."""
        persistence = SettingsPersistence(temp_config_dir)

        # Create corrupted primary file
        settings_file = temp_config_dir / "settings.json"
        settings_file.write_text('{"invalid": json}', encoding="utf-8")

        # Create valid backup file
        backup_dir = temp_config_dir / "settings_backups"
        backup_dir.mkdir(exist_ok=True)
        backup_file = backup_dir / "settings_backup_2023-07-18_12_00_00.json"
        backup_file.write_text(sample_json_settings_data, encoding="utf-8")

        settings = persistence.load_settings()

        # Should load from backup
        assert isinstance(settings, SettingsData)
        assert settings.event_filters.hide_all_day_events is True

    def test_load_settings_when_no_files_available_then_returns_defaults(
        self, settings_persistence: SettingsPersistence
    ) -> None:
        """Test load_settings returns defaults when no files are available."""
        settings = settings_persistence.load_settings()

        assert isinstance(settings, SettingsData)
        # Should be fresh defaults
        assert settings.event_filters.hide_all_day_events is False

    def test_load_settings_when_backup_fallback_successful_then_saves_to_primary(
        self, temp_config_dir: Path, sample_json_settings_data: str
    ) -> None:
        """Test load_settings saves backup data to primary file after successful fallback."""
        persistence = SettingsPersistence(temp_config_dir)

        # Create backup file only
        backup_dir = temp_config_dir / "settings_backups"
        backup_dir.mkdir(exist_ok=True)
        backup_file = backup_dir / "settings_backup_2023-07-18_12_00_00.json"
        backup_file.write_text(sample_json_settings_data, encoding="utf-8")

        settings = persistence.load_settings()

        # Primary file should now exist with the backup data
        settings_file = temp_config_dir / "settings.json"
        assert settings_file.exists()

        # Verify content matches
        primary_data = json.loads(settings_file.read_text(encoding="utf-8"))
        backup_data = json.loads(sample_json_settings_data)
        assert (
            primary_data["event_filters"]["hide_all_day_events"]
            == backup_data["event_filters"]["hide_all_day_events"]
        )

    def test_load_settings_when_schema_migration_needed_then_migrates(
        self, settings_persistence: SettingsPersistence, temp_config_dir: Path
    ) -> None:
        """Test load_settings calls schema migration when needed."""
        # Create settings file with old schema version
        old_data = {
            "metadata": {"version": "0.0.0"},
            "event_filters": {},
            "conflict_resolution": {},
            "display": {},
        }

        settings_file = temp_config_dir / "settings.json"
        with open(settings_file, "w") as f:
            json.dump(old_data, f)

        # Mock the migration method to verify it's called
        with patch.object(
            settings_persistence, "_migrate_schema", wraps=settings_persistence._migrate_schema
        ) as mock_migrate:
            settings = settings_persistence.load_settings()

            assert settings is not None
            mock_migrate.assert_called_once()


class TestSettingsPersistenceSaveSettings:
    """Test SettingsPersistence save_settings functionality."""

    def test_save_settings_when_valid_data_then_saves_successfully(
        self, settings_persistence: SettingsPersistence, sample_settings_data: SettingsData
    ) -> None:
        """Test save_settings saves valid settings data successfully."""
        result = settings_persistence.save_settings(sample_settings_data)

        assert result is True
        assert settings_persistence.settings_file.exists()

        # Verify content was saved correctly
        saved_data = json.loads(settings_persistence.settings_file.read_text(encoding="utf-8"))
        assert saved_data["event_filters"]["hide_all_day_events"] is True

    def test_save_settings_when_existing_file_then_creates_backup(
        self,
        settings_persistence: SettingsPersistence,
        sample_settings_data: SettingsData,
        populated_settings_file: Path,
    ) -> None:
        """Test save_settings creates backup when overwriting existing file."""
        # File already exists from fixture
        result = settings_persistence.save_settings(sample_settings_data)

        assert result is True

        # Check backup was created
        backup_files = list(settings_persistence.backup_dir.glob("settings_backup_*.json"))
        assert len(backup_files) >= 1

    def test_save_settings_when_save_operation_then_updates_metadata_timestamp(
        self, settings_persistence: SettingsPersistence, sample_settings_data: SettingsData
    ) -> None:
        """Test save_settings updates last_modified timestamp in metadata."""
        original_timestamp = sample_settings_data.metadata.last_modified

        settings_persistence.save_settings(sample_settings_data)

        # Timestamp should be updated
        assert sample_settings_data.metadata.last_modified > original_timestamp

    @patch("calendarbot.settings.persistence.SettingsPersistence._atomic_write")
    def test_save_settings_when_atomic_write_fails_then_raises_persistence_error(
        self,
        mock_atomic_write: Mock,
        settings_persistence: SettingsPersistence,
        sample_settings_data: SettingsData,
    ) -> None:
        """Test save_settings raises error when atomic write fails."""
        mock_atomic_write.side_effect = OSError("Disk full")

        with pytest.raises(SettingsPersistenceError) as exc_info:
            settings_persistence.save_settings(sample_settings_data)

        assert "Failed to save settings" in str(exc_info.value)
        assert exc_info.value.operation == "save"

    def test_save_settings_when_successful_then_cleans_old_backups(
        self, settings_persistence: SettingsPersistence, sample_settings_data: SettingsData
    ) -> None:
        """Test save_settings cleans up old backups after successful save."""
        # Create many backup files beyond the limit
        for i in range(10):
            timestamp = f"2023-07-{18-i:02d}_12_00_00"
            backup_file = settings_persistence.backup_dir / f"settings_backup_{timestamp}.json"
            backup_file.parent.mkdir(exist_ok=True)
            backup_file.write_text('{"test": true}', encoding="utf-8")

        settings_persistence.save_settings(sample_settings_data)

        # Should only keep max_backups + new backup
        backup_files = list(settings_persistence.backup_dir.glob("settings_backup_*.json"))
        assert (
            len(backup_files) <= settings_persistence.max_backups + 1
        )  # +1 for new backup created


class TestSettingsPersistenceAtomicWrite:
    """Test SettingsPersistence atomic write operations."""

    def test_atomic_write_when_successful_then_creates_file(
        self, settings_persistence: SettingsPersistence, sample_settings_data: SettingsData
    ) -> None:
        """Test _atomic_write creates file successfully."""
        test_file = settings_persistence.config_dir / "test_atomic.json"

        settings_persistence._atomic_write(test_file, sample_settings_data)

        assert test_file.exists()
        data = json.loads(test_file.read_text(encoding="utf-8"))
        assert data["event_filters"]["hide_all_day_events"] is True

    @patch("pathlib.Path.replace")
    @patch("builtins.open", new_callable=mock_open)
    def test_atomic_write_when_replace_fails_then_cleans_temp_file(
        self,
        mock_file_open: Mock,
        mock_replace: Mock,
        settings_persistence: SettingsPersistence,
        sample_settings_data: SettingsData,
    ) -> None:
        """Test _atomic_write cleans up temporary file when replace fails."""
        mock_replace.side_effect = OSError("Replace failed")
        test_file = settings_persistence.config_dir / "test_atomic.json"

        with pytest.raises(OSError):
            settings_persistence._atomic_write(test_file, sample_settings_data)

        # Temporary file should be cleaned up (mocked, but method should be called)
        mock_replace.assert_called_once()


class TestSettingsPersistenceBackupOperations:
    """Test SettingsPersistence backup and restore operations."""

    def test_create_backup_when_settings_file_exists_then_creates_backup(
        self, settings_persistence: SettingsPersistence, populated_settings_file: Path
    ) -> None:
        """Test create_backup creates backup file successfully."""
        backup_path = settings_persistence.create_backup()

        assert backup_path.exists()
        assert backup_path.parent == settings_persistence.backup_dir
        assert backup_path.name.startswith("settings_backup_")
        assert backup_path.suffix == ".json"

    def test_create_backup_when_custom_name_then_uses_custom_name(
        self, settings_persistence: SettingsPersistence, populated_settings_file: Path
    ) -> None:
        """Test create_backup uses custom backup name when provided."""
        backup_path = settings_persistence.create_backup("manual_backup")

        assert backup_path.name == "settings_backup_manual_backup.json"

    def test_create_backup_when_no_settings_file_then_raises_persistence_error(
        self, settings_persistence: SettingsPersistence
    ) -> None:
        """Test create_backup raises error when no settings file exists."""
        with pytest.raises(SettingsPersistenceError) as exc_info:
            settings_persistence.create_backup()

        assert "Cannot create backup: no settings file exists" in str(exc_info.value)
        assert exc_info.value.operation == "backup"

    def test_restore_from_backup_when_backup_exists_then_restores_successfully(
        self, temp_config_dir: Path, sample_json_settings_data: str
    ) -> None:
        """Test restore_from_backup restores settings from backup file."""
        persistence = SettingsPersistence(temp_config_dir)

        # Create backup file
        backup_file = persistence.backup_dir / "settings_backup_2023-07-18_12_00_00.json"
        backup_file.parent.mkdir(exist_ok=True)
        backup_file.write_text(sample_json_settings_data, encoding="utf-8")

        restored_settings = persistence.restore_from_backup(backup_file)

        assert isinstance(restored_settings, SettingsData)
        assert restored_settings.event_filters.hide_all_day_events is True

        # Should also save restored settings as current
        assert persistence.settings_file.exists()

    def test_restore_from_backup_when_no_backup_specified_then_uses_most_recent(
        self, temp_config_dir: Path, sample_json_settings_data: str
    ) -> None:
        """Test restore_from_backup uses most recent backup when none specified."""
        persistence = SettingsPersistence(temp_config_dir)
        backup_dir = persistence.backup_dir
        backup_dir.mkdir(exist_ok=True)

        # Create multiple backup files
        old_backup = backup_dir / "settings_backup_2023-07-17_12_00_00.json"
        new_backup = backup_dir / "settings_backup_2023-07-18_12_00_00.json"

        old_backup.write_text('{"test": "old"}', encoding="utf-8")
        new_backup.write_text(sample_json_settings_data, encoding="utf-8")

        restored_settings = persistence.restore_from_backup()

        # Should restore from newer backup
        assert restored_settings.event_filters.hide_all_day_events is True

    def test_restore_from_backup_when_no_backups_available_then_raises_persistence_error(
        self, settings_persistence: SettingsPersistence
    ) -> None:
        """Test restore_from_backup raises error when no backups available."""
        with pytest.raises(SettingsPersistenceError) as exc_info:
            settings_persistence.restore_from_backup()

        assert "No backup files available for restore" in str(exc_info.value)
        assert exc_info.value.operation == "restore"

    def test_restore_from_backup_when_backup_file_missing_then_raises_persistence_error(
        self, settings_persistence: SettingsPersistence
    ) -> None:
        """Test restore_from_backup raises error when specified backup file doesn't exist."""
        nonexistent_backup = settings_persistence.backup_dir / "nonexistent_backup.json"

        with pytest.raises(SettingsPersistenceError) as exc_info:
            settings_persistence.restore_from_backup(nonexistent_backup)

        assert "Backup file does not exist" in str(exc_info.value)
        assert exc_info.value.operation == "restore"

    def test_list_backups_when_backups_exist_then_returns_sorted_list(
        self, settings_persistence: SettingsPersistence, sample_json_settings_data: str
    ) -> None:
        """Test list_backups returns sorted list of backup files."""
        backup_dir = settings_persistence.backup_dir
        backup_dir.mkdir(exist_ok=True)

        # Create backup files with different timestamps
        timestamps = ["2023-07-16_12_00_00", "2023-07-18_12_00_00", "2023-07-17_12_00_00"]
        for timestamp in timestamps:
            backup_file = backup_dir / f"settings_backup_{timestamp}.json"
            backup_file.write_text(sample_json_settings_data, encoding="utf-8")

        backups = settings_persistence.list_backups()

        assert len(backups) == 3
        # Should be sorted by timestamp, newest first
        assert backups[0][1] > backups[1][1] > backups[2][1]

    def test_list_backups_when_no_backups_then_returns_empty_list(
        self, settings_persistence: SettingsPersistence
    ) -> None:
        """Test list_backups returns empty list when no backups exist."""
        backups = settings_persistence.list_backups()
        assert backups == []

    def test_list_backups_when_invalid_backup_files_then_skips_them(
        self, settings_persistence: SettingsPersistence, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test list_backups skips backup files with invalid timestamp format."""
        backup_dir = settings_persistence.backup_dir
        backup_dir.mkdir(exist_ok=True)

        # Create files with invalid timestamp formats
        invalid_file = backup_dir / "settings_backup_invalid_timestamp.json"
        valid_file = backup_dir / "settings_backup_2023-07-18_12_00_00.json"

        invalid_file.write_text('{"test": true}', encoding="utf-8")
        valid_file.write_text('{"test": true}', encoding="utf-8")

        backups = settings_persistence.list_backups()

        assert len(backups) == 1  # Only valid file should be included
        assert "Skipping backup file with invalid timestamp" in caplog.text


class TestSettingsPersistenceImportExport:
    """Test SettingsPersistence import and export functionality."""

    def test_export_settings_when_settings_exist_then_exports_successfully(
        self, settings_persistence: SettingsPersistence, populated_settings_file: Path
    ) -> None:
        """Test export_settings exports current settings to specified file."""
        export_file = settings_persistence.config_dir / "exported_settings.json"

        result = settings_persistence.export_settings(export_file)

        assert result is True
        assert export_file.exists()

        # Verify exported content
        exported_data = json.loads(export_file.read_text(encoding="utf-8"))
        assert exported_data["event_filters"]["hide_all_day_events"] is True

    def test_export_settings_when_export_directory_missing_then_creates_directory(
        self, settings_persistence: SettingsPersistence, populated_settings_file: Path
    ) -> None:
        """Test export_settings creates export directory if it doesn't exist."""
        export_dir = settings_persistence.config_dir / "exports"
        export_file = export_dir / "settings.json"

        result = settings_persistence.export_settings(export_file)

        assert result is True
        assert export_file.exists()
        assert export_dir.exists()

    @patch("calendarbot.settings.persistence.SettingsPersistence.load_settings")
    def test_export_settings_when_load_fails_then_raises_persistence_error(
        self, mock_load: Mock, settings_persistence: SettingsPersistence
    ) -> None:
        """Test export_settings raises error when loading settings fails."""
        mock_load.side_effect = Exception("Load failed")
        export_file = settings_persistence.config_dir / "export.json"

        with pytest.raises(SettingsPersistenceError) as exc_info:
            settings_persistence.export_settings(export_file)

        assert "Failed to export settings" in str(exc_info.value)
        assert exc_info.value.operation == "export"

    def test_import_settings_when_valid_file_then_imports_successfully(
        self, settings_persistence: SettingsPersistence, sample_json_settings_data: str
    ) -> None:
        """Test import_settings imports settings from valid file."""
        import_file = settings_persistence.config_dir / "import_settings.json"
        import_file.write_text(sample_json_settings_data, encoding="utf-8")

        imported_settings = settings_persistence.import_settings(import_file)

        assert isinstance(imported_settings, SettingsData)
        assert imported_settings.event_filters.hide_all_day_events is True

        # Should also save imported settings as current
        assert settings_persistence.settings_file.exists()

    def test_import_settings_when_import_file_missing_then_raises_persistence_error(
        self, settings_persistence: SettingsPersistence
    ) -> None:
        """Test import_settings raises error when import file doesn't exist."""
        import_file = settings_persistence.config_dir / "nonexistent.json"

        with pytest.raises(SettingsPersistenceError) as exc_info:
            settings_persistence.import_settings(import_file)

        assert "Import file does not exist" in str(exc_info.value)
        assert exc_info.value.operation == "import"

    def test_import_settings_when_existing_settings_then_creates_backup(
        self,
        settings_persistence: SettingsPersistence,
        populated_settings_file: Path,
        sample_json_settings_data: str,
    ) -> None:
        """Test import_settings creates backup before importing when settings exist."""
        import_file = settings_persistence.config_dir / "import_settings.json"
        import_file.write_text(sample_json_settings_data, encoding="utf-8")

        settings_persistence.import_settings(import_file)

        # Check backup was created with pre_import name
        backup_files = list(settings_persistence.backup_dir.glob("settings_backup_pre_import.json"))
        assert len(backup_files) == 1


class TestSettingsPersistenceSchemaHandling:
    """Test SettingsPersistence schema migration and compatibility."""

    def test_migrate_schema_when_current_version_then_returns_unchanged(
        self, settings_persistence: SettingsPersistence
    ) -> None:
        """Test _migrate_schema returns data unchanged when version is current."""
        data = {
            "metadata": {"version": "1.0.0"},
            "event_filters": {},
            "display": {},
            "conflict_resolution": {},
        }

        result = settings_persistence._migrate_schema(data)

        assert result == data

    def test_migrate_schema_when_old_version_then_migrates_to_current(
        self, settings_persistence: SettingsPersistence
    ) -> None:
        """Test _migrate_schema migrates old version data to current schema."""
        data = {"metadata": {"version": "0.0.0"}}

        result = settings_persistence._migrate_schema(data)

        assert result["metadata"]["version"] == "1.0.0"
        assert "event_filters" in result
        assert "display" in result
        assert "conflict_resolution" in result

    @patch("calendarbot.settings.persistence.SettingsPersistence._migrate_from_v0_to_v1")
    def test_migrate_schema_when_migration_fails_then_raises_schema_error(
        self, mock_migrate_v0: Mock, settings_persistence: SettingsPersistence
    ) -> None:
        """Test _migrate_schema raises SchemaError when migration fails."""
        mock_migrate_v0.side_effect = Exception("Migration failed")
        data = {"metadata": {"version": "0.0.0"}}

        with pytest.raises(SettingsSchemaError) as exc_info:
            settings_persistence._migrate_schema(data)

        assert "Failed to migrate settings schema" in str(exc_info.value)
        assert exc_info.value.current_version == "0.0.0"
        assert exc_info.value.expected_version == "1.0.0"

    def test_migrate_from_v0_to_v1_when_missing_sections_then_adds_defaults(
        self, settings_persistence: SettingsPersistence
    ) -> None:
        """Test _migrate_from_v0_to_v1 adds missing top-level sections."""
        data = {"some_old_field": "value"}

        result = settings_persistence._migrate_from_v0_to_v1(data)

        assert "event_filters" in result
        assert "conflict_resolution" in result
        assert "display" in result
        assert "metadata" in result
        assert result["some_old_field"] == "value"  # Preserves existing data


class TestSettingsPersistenceUtilities:
    """Test SettingsPersistence utility methods."""

    def test_get_settings_info_when_settings_exist_then_returns_complete_info(
        self,
        settings_persistence: SettingsPersistence,
        populated_settings_file: Path,
        sample_json_settings_data: str,
    ) -> None:
        """Test get_settings_info returns complete information when settings exist."""
        # Create some backup files
        backup_dir = settings_persistence.backup_dir
        backup_dir.mkdir(exist_ok=True)
        backup_file = backup_dir / "settings_backup_2023-07-18_12_00_00.json"
        backup_file.write_text(sample_json_settings_data, encoding="utf-8")

        info = settings_persistence.get_settings_info()

        assert info["settings_file"] == str(settings_persistence.settings_file)
        assert info["settings_exists"] is True
        assert info["backup_directory"] == str(settings_persistence.backup_dir)
        assert info["backup_count"] == 1
        assert info["settings_size"] > 0
        assert "last_modified" in info
        assert isinstance(info, dict)

    def test_get_settings_info_when_no_settings_then_returns_basic_info(
        self, settings_persistence: SettingsPersistence
    ) -> None:
        """Test get_settings_info returns basic information when no settings exist."""
        info = settings_persistence.get_settings_info()

        assert info["settings_exists"] is False
        assert info["backup_count"] == 0
        assert info["settings_size"] == 0
        assert info["last_modified"] is None

    def test_get_settings_info_when_stat_fails_then_handles_gracefully(
        self, settings_persistence: SettingsPersistence, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test get_settings_info handles file stat errors gracefully."""
        with patch.object(
            settings_persistence, "list_backups", side_effect=OSError("Permission denied")
        ):
            info = settings_persistence.get_settings_info()

            assert isinstance(info, dict)
            assert "Error getting settings info" in caplog.text

    def test_load_from_file_when_valid_json_then_loads_successfully(
        self, settings_persistence: SettingsPersistence, populated_settings_file: Path
    ) -> None:
        """Test _load_from_file loads valid JSON file successfully."""
        settings = settings_persistence._load_from_file(populated_settings_file)

        assert isinstance(settings, SettingsData)
        assert settings.event_filters.hide_all_day_events is True

    def test_load_from_file_when_invalid_json_then_returns_none(
        self,
        settings_persistence: SettingsPersistence,
        temp_config_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test _load_from_file returns None for invalid JSON."""
        invalid_file = temp_config_dir / "invalid.json"
        invalid_file.write_text('{"invalid": json}', encoding="utf-8")

        result = settings_persistence._load_from_file(invalid_file)

        assert result is None
        assert "Invalid JSON in settings file" in caplog.text

    def test_load_from_file_when_file_error_then_returns_none(
        self, settings_persistence: SettingsPersistence, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test _load_from_file returns None when file cannot be read."""
        nonexistent_file = settings_persistence.config_dir / "nonexistent.json"

        result = settings_persistence._load_from_file(nonexistent_file)

        assert result is None
        assert "Error loading settings from" in caplog.text

    def test_cleanup_old_backups_when_exceeds_limit_then_removes_oldest(
        self, settings_persistence: SettingsPersistence, sample_json_settings_data: str
    ) -> None:
        """Test _cleanup_old_backups removes oldest backup files when limit exceeded."""
        backup_dir = settings_persistence.backup_dir
        backup_dir.mkdir(exist_ok=True)

        # Create more backup files than the limit
        timestamps = [f"2023-07-{i:02d}_12_00_00" for i in range(10, 20)]  # 10 files
        for timestamp in timestamps:
            backup_file = backup_dir / f"settings_backup_{timestamp}.json"
            backup_file.write_text(sample_json_settings_data, encoding="utf-8")

        # Set lower limit for testing
        settings_persistence.max_backups = 5

        settings_persistence._cleanup_old_backups()

        # Should only keep max_backups files
        remaining_backups = list(backup_dir.glob("settings_backup_*.json"))
        assert len(remaining_backups) == 5

        # Should keep the newest files
        remaining_timestamps = [f.stem.replace("settings_backup_", "") for f in remaining_backups]
        assert "2023-07-19_12_00_00" in remaining_timestamps  # Newest
        assert "2023-07-10_12_00_00" not in remaining_timestamps  # Oldest

    def test_cleanup_old_backups_when_cleanup_fails_then_logs_error(
        self, settings_persistence: SettingsPersistence, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test _cleanup_old_backups logs error when cleanup fails."""
        with patch.object(settings_persistence, "list_backups") as mock_list:
            mock_list.side_effect = Exception("List failed")

            settings_persistence._cleanup_old_backups()

            assert "Error cleaning up old backups" in caplog.text

    def test_get_most_recent_backup_when_backups_exist_then_returns_newest(
        self, settings_persistence: SettingsPersistence, sample_json_settings_data: str
    ) -> None:
        """Test _get_most_recent_backup returns the newest backup file."""
        backup_dir = settings_persistence.backup_dir
        backup_dir.mkdir(exist_ok=True)

        # Create backup files with different dates
        old_backup = backup_dir / "settings_backup_2023-07-17_12_00_00.json"
        new_backup = backup_dir / "settings_backup_2023-07-18_12_00_00.json"

        old_backup.write_text(sample_json_settings_data, encoding="utf-8")
        new_backup.write_text(sample_json_settings_data, encoding="utf-8")

        most_recent = settings_persistence._get_most_recent_backup()

        assert most_recent == new_backup

    def test_get_most_recent_backup_when_no_backups_then_returns_none(
        self, settings_persistence: SettingsPersistence
    ) -> None:
        """Test _get_most_recent_backup returns None when no backups exist."""
        most_recent = settings_persistence._get_most_recent_backup()
        assert most_recent is None

    def test_create_backup_helper_when_custom_name_then_uses_name(
        self, settings_persistence: SettingsPersistence, populated_settings_file: Path
    ) -> None:
        """Test _create_backup creates backup with custom name."""
        backup_path = settings_persistence._create_backup("test_backup")

        assert backup_path.name == "settings_backup_test_backup.json"
        assert backup_path.exists()

    def test_create_backup_helper_when_no_name_then_uses_timestamp(
        self, settings_persistence: SettingsPersistence, populated_settings_file: Path
    ) -> None:
        """Test _create_backup creates backup with timestamp when no name provided."""
        backup_path = settings_persistence._create_backup()

        assert backup_path.name.startswith("settings_backup_")
        assert backup_path.name.endswith(".json")
        # Should contain timestamp format
        assert (
            len(backup_path.name.replace("settings_backup_", "").replace(".json", "")) == 19
        )  # YYYY-MM-DD_HH_MM_SS
        assert backup_path.exists()
