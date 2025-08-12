"""
Settings persistence layer for JSON file-based storage.

This module provides robust settings persistence functionality with support for
atomic file operations, backup/restore, schema migration, and comprehensive
error handling. It integrates with CalendarBot's existing configuration system.
"""

import contextlib
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .exceptions import SettingsPersistenceError, SettingsSchemaError
from .models import SettingsData

logger = logging.getLogger(__name__)


class SettingsPersistence:
    """Handles persistent storage of settings data with backup and migration support.

    Provides atomic file operations, automatic backup creation, and schema migration
    capabilities for CalendarBot settings. Uses JSON format for human readability
    and cross-platform compatibility.

    Attributes:
        settings_file: Primary settings file path
        backup_dir: Directory for settings backups
        max_backups: Maximum number of backup files to retain
        backup_enabled: Whether backup functionality is available

    Example:
        >>> persistence = SettingsPersistence(Path("/home/user/.config/calendarbot"))
        >>> settings = SettingsData()
        >>> persistence.save_settings(settings)
        >>> loaded_settings = persistence.load_settings()
    """

    def __init__(
        self, config_dir: Path, settings_filename: str = "settings.json", max_backups: int = 5
    ) -> None:
        """Initialize settings persistence with configuration directory.

        Args:
            config_dir: Directory path for storing settings files
            settings_filename: Name of the primary settings file
            max_backups: Maximum number of backup files to keep

        Raises:
            SettingsPersistenceError: If main directory creation fails
        """
        self.config_dir = config_dir
        self.settings_file = config_dir / settings_filename
        self.backup_dir = config_dir / "settings_backups"
        self.max_backups = max_backups
        self.backup_enabled = False

        # Ensure main config directory exists
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Settings config directory: {self.config_dir}")
        except OSError as e:
            raise SettingsPersistenceError(
                f"Failed to create settings directory: {config_dir}",
                operation="initialize",
                file_path=str(config_dir),
                original_error=e,
            ) from e

        # Try to create backup directory, but don't fail if permissions are denied
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self.backup_enabled = True
            logger.debug(f"Settings backup directory: {self.backup_dir}")
        except PermissionError as e:
            logger.warning(
                f"Cannot create backup directory due to permissions: {self.backup_dir}. "
                f"Backup functionality will be disabled. Error: {e}"
            )
            self.backup_enabled = False
        except OSError as e:
            logger.warning(
                f"Cannot create backup directory: {self.backup_dir}. "
                f"Backup functionality will be disabled. Error: {e}"
            )
            self.backup_enabled = False

        logger.debug(
            f"Settings persistence initialized: {self.settings_file} (backup_enabled={self.backup_enabled})"
        )

    def load_settings(self) -> SettingsData:
        """Load settings from persistent storage.

        Attempts to load settings from the primary file, falling back to the most
        recent backup if the primary file is corrupted or missing.

        Returns:
            SettingsData object with loaded configuration

        Raises:
            SettingsPersistenceError: If loading fails completely
            SettingsSchemaError: If schema migration is required but fails
        """
        logger.debug(f"Loading settings from {self.settings_file}")

        # Try loading from primary file first
        try:
            if self.settings_file.exists():
                settings_data = self._load_from_file(self.settings_file)
                if settings_data:
                    logger.info("Settings loaded successfully from primary file")
                    return settings_data
        except Exception as e:
            logger.warning(f"Failed to load from primary settings file: {e}")

        # Try loading from most recent backup
        try:
            backup_file = self._get_most_recent_backup()
            if backup_file:
                logger.info(f"Attempting to load from backup: {backup_file}")
                settings_data = self._load_from_file(backup_file)
                if settings_data:
                    logger.info("Settings loaded successfully from backup")
                    # Save backup data to primary file
                    self.save_settings(settings_data)
                    return settings_data
        except Exception as e:
            logger.warning(f"Failed to load from backup: {e}")

        # Return default settings if all loading attempts fail
        logger.info("Creating new default settings (no existing settings found)")
        return SettingsData()

    def save_settings(self, settings: SettingsData) -> bool:
        """Save settings to persistent storage with atomic write operations.

        Performs atomic file writes to prevent corruption, creates automatic backups
        when available, and manages backup file retention.

        Args:
            settings: SettingsData object to save

        Returns:
            True if save operation succeeded

        Raises:
            SettingsPersistenceError: If save operation fails
        """
        logger.debug(f"Saving settings to {self.settings_file}")

        try:
            # Update metadata before saving
            settings.metadata.last_modified = datetime.now()

            # Create backup of existing settings before overwriting (if backup is enabled)
            if self.backup_enabled and self.settings_file.exists():
                try:
                    self._create_backup()
                except Exception as e:
                    logger.warning(f"Backup creation failed but continuing with save: {e}")
            elif not self.backup_enabled and self.settings_file.exists():
                logger.debug("Backup skipped (backup disabled due to permissions)")

            # Perform atomic write
            self._atomic_write(self.settings_file, settings)

            # Clean up old backups (if backup is enabled)
            if self.backup_enabled:
                try:
                    self._cleanup_old_backups()
                except Exception as e:
                    logger.warning(f"Backup cleanup failed but save succeeded: {e}")

            logger.info("Settings saved successfully")
            return True

        except Exception as e:
            raise SettingsPersistenceError(
                "Failed to save settings",
                operation="save",
                file_path=str(self.settings_file),
                original_error=e,
            ) from e

    def create_backup(self, backup_name: Optional[str] = None) -> Path:
        """Create a manual backup of current settings.

        Args:
            backup_name: Optional custom name for backup file

        Returns:
            Path to the created backup file

        Raises:
            SettingsPersistenceError: If backup creation fails or backups are disabled
        """
        if not self.backup_enabled:
            raise SettingsPersistenceError(
                "Cannot create backup: backup functionality is disabled due to permission restrictions",
                operation="backup",
                file_path=str(self.backup_dir),
            )

        def _validate_settings_file_exists() -> None:
            """Validate that settings file exists for backup."""
            if not self.settings_file.exists():
                raise SettingsPersistenceError(
                    "Cannot create backup: no settings file exists",
                    operation="backup",
                    file_path=str(self.settings_file),
                )

        try:
            _validate_settings_file_exists()

            backup_file = self._create_backup(backup_name)
            logger.info(f"Manual backup created: {backup_file}")
            return backup_file

        except Exception as e:
            raise SettingsPersistenceError(
                "Failed to create settings backup",
                operation="backup",
                file_path=str(self.settings_file),
                original_error=e,
            ) from e

    def restore_from_backup(self, backup_file: Optional[Path] = None) -> SettingsData:
        """Restore settings from a backup file.

        Args:
            backup_file: Specific backup file to restore from (uses most recent if None)

        Returns:
            Restored SettingsData object

        Raises:
            SettingsPersistenceError: If restore operation fails
        """

        def _validate_backup_file(backup_file: Optional[Path]) -> Path:
            """Validate backup file availability and existence."""
            if backup_file is None:
                backup_file = self._get_most_recent_backup()
                if backup_file is None:
                    raise SettingsPersistenceError(
                        "No backup files available for restore", operation="restore"
                    )

            if not backup_file.exists():
                raise SettingsPersistenceError(
                    f"Backup file does not exist: {backup_file}",
                    operation="restore",
                    file_path=str(backup_file),
                )
            return backup_file

        def _validate_backup_data(
            backup_file: Path, settings_data: Optional[SettingsData]
        ) -> SettingsData:
            """Validate that backup data was loaded successfully."""
            if settings_data is None:
                raise SettingsPersistenceError(
                    f"Failed to load data from backup file: {backup_file}",
                    operation="restore",
                    file_path=str(backup_file),
                )
            return settings_data

        try:
            backup_file = _validate_backup_file(backup_file)

            # Load settings from backup
            settings_data = self._load_from_file(backup_file)
            settings_data = _validate_backup_data(backup_file, settings_data)

            # Save restored settings as current
            self.save_settings(settings_data)

            logger.info(f"Settings restored from backup: {backup_file}")
            return settings_data

        except Exception as e:
            raise SettingsPersistenceError(
                "Failed to restore settings from backup",
                operation="restore",
                file_path=str(backup_file) if backup_file else "unknown",
                original_error=e,
            ) from e

    def export_settings(self, export_file: Path) -> bool:
        """Export current settings to a specified file.

        Args:
            export_file: Path where settings should be exported

        Returns:
            True if export succeeded

        Raises:
            SettingsPersistenceError: If export operation fails
        """
        try:
            settings = self.load_settings()

            # Ensure export directory exists
            export_file.parent.mkdir(parents=True, exist_ok=True)

            # Write settings to export file
            self._atomic_write(export_file, settings)

            logger.info(f"Settings exported to: {export_file}")
            return True

        except Exception as e:
            raise SettingsPersistenceError(
                "Failed to export settings",
                operation="export",
                file_path=str(export_file),
                original_error=e,
            ) from e

    def import_settings(self, import_file: Path) -> SettingsData:
        """Import settings from a specified file.

        Args:
            import_file: Path to settings file to import

        Returns:
            Imported SettingsData object

        Raises:
            SettingsPersistenceError: If import operation fails
            SettingsSchemaError: If imported settings have incompatible schema
        """

        def _validate_import_file(import_file: Path) -> None:
            """Validate that import file exists."""
            if not import_file.exists():
                raise SettingsPersistenceError(
                    f"Import file does not exist: {import_file}",
                    operation="import",
                    file_path=str(import_file),
                )

        def _validate_import_data(
            import_file: Path, settings_data: Optional[SettingsData]
        ) -> SettingsData:
            """Validate that import data was loaded successfully."""
            if settings_data is None:
                raise SettingsPersistenceError(
                    f"Failed to load data from import file: {import_file}",
                    operation="import",
                    file_path=str(import_file),
                )
            return settings_data

        try:
            _validate_import_file(import_file)

            # Load settings from import file
            settings_data = self._load_from_file(import_file)
            settings_data = _validate_import_data(import_file, settings_data)

            # Create backup before importing
            if self.settings_file.exists():
                self._create_backup("pre_import")

            # Save imported settings
            self.save_settings(settings_data)

            logger.info(f"Settings imported from: {import_file}")
            return settings_data

        except Exception as e:
            raise SettingsPersistenceError(
                "Failed to import settings",
                operation="import",
                file_path=str(import_file),
                original_error=e,
            ) from e

    def list_backups(self) -> list[tuple[Path, datetime]]:
        """List available backup files with their creation timestamps.

        Returns:
            List of tuples containing (backup_file_path, creation_time),
            empty list if backups are disabled
        """
        backups: list[tuple[Path, datetime]] = []

        if not self.backup_enabled:
            logger.debug("Backup listing skipped (backup disabled due to permissions)")
            return backups

        try:
            if not self.backup_dir.exists():
                return backups

            def _parse_backup_timestamp(backup_file: Path) -> Optional[tuple[Path, datetime]]:
                """Parse timestamp from backup filename."""
                try:
                    # Extract timestamp from filename
                    timestamp_str = backup_file.stem.replace("settings_backup_", "")
                    timestamp = datetime.fromisoformat(timestamp_str.replace("_", ":"))
                    return (backup_file, timestamp)
                except (ValueError, IndexError):
                    # Skip files with invalid timestamp format
                    logger.warning(f"Skipping backup file with invalid timestamp: {backup_file}")
                    return None

            for backup_file in self.backup_dir.glob("settings_backup_*.json"):
                result = _parse_backup_timestamp(backup_file)
                if result:
                    backups.append(result)

            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x[1], reverse=True)

        except Exception:
            logger.exception("Error listing backups")

        return backups

    def get_settings_info(self) -> dict[str, Any]:
        """Get information about current settings file and backups.

        Returns:
            Dictionary containing settings file information
        """
        info = {
            "settings_file": str(self.settings_file),
            "settings_exists": self.settings_file.exists(),
            "backup_directory": str(self.backup_dir),
            "backup_enabled": self.backup_enabled,
            "backup_count": 0,
            "settings_size": 0,
            "last_modified": None,
        }

        try:
            if self.settings_file.exists():
                stat = self.settings_file.stat()
                info["settings_size"] = stat.st_size
                info["last_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()

            if self.backup_enabled:
                backups = self.list_backups()
                info["backup_count"] = len(backups)
            else:
                info["backup_count"] = "N/A (backups disabled)"

        except Exception:
            logger.exception("Error getting settings info")

        return info

    def _load_from_file(self, file_path: Path) -> Optional[SettingsData]:
        """Load settings data from a specific file.

        Args:
            file_path: Path to settings file

        Returns:
            SettingsData object or None if loading fails

        Raises:
            SettingsSchemaError: If schema migration is required
        """
        try:
            with file_path.open(encoding="utf-8") as f:
                data = json.load(f)

            # Validate and potentially migrate schema
            data = self._migrate_schema(data)

            # Create SettingsData object from loaded data
            return SettingsData(**data)

        except json.JSONDecodeError:
            logger.exception(f"Invalid JSON in settings file {file_path}")
            return None
        except Exception:
            logger.exception(f"Error loading settings from {file_path}")
            return None

    def _atomic_write(self, file_path: Path, settings: SettingsData) -> None:
        """Perform atomic write operation to prevent file corruption.

        Args:
            file_path: Target file path
            settings: Settings data to write

        Raises:
            SettingsPersistenceError: If write operation fails
        """
        temp_file = file_path.with_suffix(".tmp")

        try:
            # Write to temporary file first
            with temp_file.open("w", encoding="utf-8") as f:
                json.dump(settings.dict(), f, indent=2, default=str, ensure_ascii=False)
                f.flush()  # Ensure data is written to disk

            # Atomic move to final location
            temp_file.replace(file_path)

        except Exception:
            # Clean up temporary file if it exists
            if temp_file.exists():
                with contextlib.suppress(Exception):
                    temp_file.unlink()
            raise

    def _create_backup(self, backup_name: Optional[str] = None) -> Path:
        """Create a backup of the current settings file.

        Args:
            backup_name: Optional custom backup name

        Returns:
            Path to created backup file
        """
        if backup_name:
            backup_file = self.backup_dir / f"settings_backup_{backup_name}.json"
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
            backup_file = self.backup_dir / f"settings_backup_{timestamp}.json"

        shutil.copy2(self.settings_file, backup_file)
        return backup_file

    def _get_most_recent_backup(self) -> Optional[Path]:
        """Get the path to the most recent backup file.

        Returns:
            Path to most recent backup or None if no backups exist
        """
        backups = self.list_backups()
        if backups:
            return backups[0][0]  # First item is most recent
        return None

    def _cleanup_old_backups(self) -> None:
        """Remove old backup files beyond the retention limit."""
        if not self.backup_enabled:
            logger.debug("Backup cleanup skipped (backup disabled due to permissions)")
            return

        try:
            backups = self.list_backups()

            def _remove_backup_file(backup_file: Path) -> None:
                """Remove a single backup file with error handling."""
                try:
                    backup_file.unlink()
                    logger.debug(f"Removed old backup: {backup_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove old backup {backup_file}: {e}")

            # Remove excess backups
            if len(backups) > self.max_backups:
                for backup_file, _ in backups[self.max_backups :]:
                    _remove_backup_file(backup_file)

        except Exception:
            logger.exception("Error cleaning up old backups")

    def _migrate_schema(self, data: dict[str, Any]) -> dict[str, Any]:
        """Migrate settings data to current schema version.

        Args:
            data: Raw settings data dictionary

        Returns:
            Migrated settings data

        Raises:
            SettingsSchemaError: If migration fails
        """
        # Initialize these variables so they are always defined, even if an exception occurs
        current_version = "0.0.0"
        expected_version = "1.0.0"
        try:
            # Get current version from metadata
            metadata = data.get("metadata", {})
            current_version = metadata.get("version", "0.0.0")

            # Define expected version (should match current SettingsData schema)
            expected_version = "1.0.0"

            if current_version == expected_version:
                return data  # No migration needed

            # Perform version-specific migrations
            if current_version == "0.0.0":
                data = self._migrate_from_v0_to_v1(data)
                logger.info("Migrated settings from version 0.0.0 to 1.0.0")

            # Update version in metadata
            if "metadata" not in data:
                data["metadata"] = {}
            data["metadata"]["version"] = expected_version

            return data

        except Exception as e:
            raise SettingsSchemaError(
                "Failed to migrate settings schema",
                current_version=current_version,
                expected_version=expected_version,
                details={"migration_error": str(e)},
            ) from e

    def _migrate_from_v0_to_v1(self, data: dict[str, Any]) -> dict[str, Any]:
        """Migrate settings from version 0.0.0 to 1.0.0.

        Args:
            data: Settings data in v0.0.0 format

        Returns:
            Settings data in v1.0.0 format
        """
        # This is a placeholder for actual migration logic
        # In a real scenario, this would handle schema changes between versions

        # Ensure all required top-level sections exist
        if "event_filters" not in data:
            data["event_filters"] = {}
        if "conflict_resolution" not in data:
            data["conflict_resolution"] = {}
        if "display" not in data:
            data["display"] = {}
        if "metadata" not in data:
            data["metadata"] = {}

        return data
