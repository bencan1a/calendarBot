"""
Settings service layer providing business logic for settings management.

This module implements the core business logic for CalendarBot settings operations,
including CRUD operations, validation, integration with existing configuration,
and coordination between the models and persistence layers.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..config.settings import CalendarBotSettings
from .exceptions import SettingsError, SettingsPersistenceError, SettingsValidationError
from .models import (
    ConflictResolutionSettings,
    DisplaySettings,
    EventFilterSettings,
    FilterPattern,
    SettingsData,
    SettingsMetadata,
)
from .persistence import SettingsPersistence

logger = logging.getLogger(__name__)


class SettingsService:
    """Business logic service for CalendarBot settings management.

    Provides high-level operations for settings management including validation,
    persistence coordination, and integration with CalendarBot's existing
    configuration system. Acts as the main entry point for all settings operations.

    Attributes:
        persistence: Settings persistence manager
        calendarbot_settings: Integration with existing CalendarBot settings
        current_settings: Cached current settings data

    Example:
        >>> service = SettingsService()
        >>> settings = service.get_settings()
        >>> settings.event_filters.hide_all_day_events = True
        >>> service.update_settings(settings)
    """

    def __init__(
        self,
        calendarbot_settings: Optional[CalendarBotSettings] = None,
        config_dir: Optional[Path] = None,
    ) -> None:
        """Initialize settings service with CalendarBot integration.

        Args:
            calendarbot_settings: Existing CalendarBot settings for integration
            config_dir: Custom configuration directory (uses CalendarBot default if None)

        Raises:
            SettingsError: If initialization fails
        """
        try:
            # Use provided CalendarBot settings or import default
            if calendarbot_settings is not None:
                self.calendarbot_settings = calendarbot_settings
            else:
                from ..config.settings import settings as default_settings

                self.calendarbot_settings = default_settings

            # Determine configuration directory
            if config_dir is not None:
                self.config_dir = config_dir
            else:
                self.config_dir = self.calendarbot_settings.config_dir

            # Initialize persistence manager
            self.persistence = SettingsPersistence(self.config_dir)

            # Cache for current settings
            self._current_settings: Optional[SettingsData] = None

            logger.info(f"Settings service initialized with config directory: {self.config_dir}")

        except Exception as e:
            raise SettingsError(
                "Failed to initialize settings service",
                details={
                    "error": str(e),
                    "config_dir": str(config_dir) if config_dir else "default",
                },
            )

    def get_settings(self, force_reload: bool = False) -> SettingsData:
        """Get current settings data with caching support.

        Args:
            force_reload: Whether to force reload from persistence layer

        Returns:
            Current SettingsData object

        Raises:
            SettingsError: If settings cannot be loaded
        """
        try:
            if self._current_settings is None or force_reload:
                logger.debug("Loading settings from persistence layer")
                self._current_settings = self.persistence.load_settings()

                # Validate loaded settings
                self._validate_settings_consistency(self._current_settings)

                logger.debug("Settings loaded and validated successfully")

            return self._current_settings

        except Exception as e:
            raise SettingsError(
                "Failed to get settings", details={"force_reload": force_reload, "error": str(e)}
            )

    def update_settings(self, settings: SettingsData) -> SettingsData:
        """Update settings with validation and persistence.

        Args:
            settings: Updated SettingsData object to save

        Returns:
            The saved SettingsData object (with updated metadata)

        Raises:
            SettingsValidationError: If settings validation fails
            SettingsPersistenceError: If persistence operation fails
            SettingsError: If update operation fails
        """
        try:
            logger.debug("Updating settings")

            # Validate settings before saving
            validation_errors = self.validate_settings(settings)
            if validation_errors:
                raise SettingsValidationError(
                    "Settings validation failed", validation_errors=validation_errors
                )

            # Additional business logic validation
            self._validate_settings_consistency(settings)

            # Update metadata
            settings.metadata.last_modified_by = "settings_service"

            # Save to persistence layer
            success = self.persistence.save_settings(settings)
            if not success:
                raise SettingsPersistenceError(
                    "Settings save operation returned false", operation="save"
                )

            # Update cache
            self._current_settings = settings

            logger.info("Settings updated successfully")
            return settings

        except (SettingsValidationError, SettingsPersistenceError):
            # Re-raise validation and persistence errors as-is
            raise
        except Exception as e:
            raise SettingsError("Failed to update settings", details={"error": str(e)})

    def get_filter_settings(self) -> EventFilterSettings:
        """Get current event filter settings.

        Returns:
            EventFilterSettings object
        """
        return self.get_settings().event_filters

    def update_filter_settings(self, filter_settings: EventFilterSettings) -> EventFilterSettings:
        """Update only the event filter settings.

        Args:
            filter_settings: Updated EventFilterSettings object

        Returns:
            The updated EventFilterSettings object

        Raises:
            SettingsError: If update fails
        """
        try:
            current = self.get_settings()
            current.event_filters = filter_settings
            updated = self.update_settings(current)
            return updated.event_filters

        except Exception as e:
            raise SettingsError("Failed to update filter settings", details={"error": str(e)})

    def get_display_settings(self) -> DisplaySettings:
        """Get current display settings.

        Returns:
            DisplaySettings object
        """
        return self.get_settings().display

    def update_display_settings(self, display_settings: DisplaySettings) -> DisplaySettings:
        """Update only the display settings.

        Args:
            display_settings: Updated DisplaySettings object

        Returns:
            The updated DisplaySettings object

        Raises:
            SettingsError: If update fails
        """
        try:
            current = self.get_settings()
            current.display = display_settings
            updated = self.update_settings(current)
            return updated.display

        except Exception as e:
            raise SettingsError("Failed to update display settings", details={"error": str(e)})

    def get_conflict_settings(self) -> ConflictResolutionSettings:
        """Get current conflict resolution settings.

        Returns:
            ConflictResolutionSettings object
        """
        return self.get_settings().conflict_resolution

    def update_conflict_settings(
        self, conflict_settings: ConflictResolutionSettings
    ) -> ConflictResolutionSettings:
        """Update only the conflict resolution settings.

        Args:
            conflict_settings: Updated ConflictResolutionSettings object

        Returns:
            The updated ConflictResolutionSettings object

        Raises:
            SettingsError: If update fails
        """
        try:
            current = self.get_settings()
            current.conflict_resolution = conflict_settings
            updated = self.update_settings(current)
            return updated.conflict_resolution

        except Exception as e:
            raise SettingsError("Failed to update conflict settings", details={"error": str(e)})

    def add_filter_pattern(
        self,
        pattern: str,
        is_regex: bool = False,
        case_sensitive: bool = False,
        description: Optional[str] = None,
    ) -> FilterPattern:
        """Add a new filter pattern to event filters.

        Args:
            pattern: The filter pattern text
            is_regex: Whether the pattern is a regular expression
            case_sensitive: Whether matching should be case sensitive
            description: Optional description of the filter

        Returns:
            The created FilterPattern object

        Raises:
            SettingsValidationError: If pattern is invalid
            SettingsError: If addition fails
        """
        try:
            # Create and validate new filter pattern
            filter_pattern = FilterPattern(
                pattern=pattern,
                is_regex=is_regex,
                case_sensitive=case_sensitive,
                description=description,
            )

            # Add to current filter settings
            current = self.get_settings()
            current.event_filters.title_patterns.append(filter_pattern)

            # Save updated settings
            self.update_settings(current)

            logger.info(f"Added filter pattern: {pattern}")
            return filter_pattern

        except Exception as e:
            raise SettingsError(
                "Failed to add filter pattern", details={"pattern": pattern, "error": str(e)}
            )

    def remove_filter_pattern(self, pattern: str, is_regex: bool = False) -> bool:
        """Remove a filter pattern from event filters.

        Args:
            pattern: The pattern text to remove
            is_regex: Whether the pattern is a regular expression

        Returns:
            True if pattern was found and removed

        Raises:
            SettingsError: If removal fails
        """
        try:
            current = self.get_settings()
            patterns = current.event_filters.title_patterns

            # Find and remove matching pattern
            for i, filter_pattern in enumerate(patterns):
                if filter_pattern.pattern == pattern and filter_pattern.is_regex == is_regex:
                    patterns.pop(i)
                    self.update_settings(current)
                    logger.info(f"Removed filter pattern: {pattern}")
                    return True

            logger.warning(f"Filter pattern not found: {pattern}")
            return False

        except Exception as e:
            raise SettingsError(
                "Failed to remove filter pattern", details={"pattern": pattern, "error": str(e)}
            )

    def toggle_filter_pattern(self, pattern: str, is_regex: bool = False) -> Optional[bool]:
        """Toggle the active state of a filter pattern.

        Args:
            pattern: The pattern text to toggle
            is_regex: Whether the pattern is a regular expression

        Returns:
            New active state (True/False) or None if pattern not found

        Raises:
            SettingsError: If toggle operation fails
        """
        try:
            current = self.get_settings()
            patterns = current.event_filters.title_patterns

            # Find and toggle matching pattern
            for filter_pattern in patterns:
                if filter_pattern.pattern == pattern and filter_pattern.is_regex == is_regex:
                    filter_pattern.is_active = not filter_pattern.is_active
                    self.update_settings(current)
                    logger.info(f"Toggled filter pattern {pattern}: {filter_pattern.is_active}")
                    return filter_pattern.is_active

            logger.warning(f"Filter pattern not found for toggle: {pattern}")
            return None

        except Exception as e:
            raise SettingsError(
                "Failed to toggle filter pattern", details={"pattern": pattern, "error": str(e)}
            )

    def validate_settings(self, settings: SettingsData) -> List[str]:
        """Validate settings data and return list of validation errors.

        Args:
            settings: SettingsData object to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        try:
            # Pydantic validation is handled automatically during object creation
            # Additional business logic validation can be added here

            # Validate display layout against available layouts
            available_layouts = self._get_available_layouts()
            if (
                settings.display.default_layout
                and available_layouts
                and settings.display.default_layout not in available_layouts
            ):
                errors.append(
                    f"Invalid default layout '{settings.display.default_layout}'. "
                    f"Available layouts: {', '.join(available_layouts)}"
                )

            # Validate filter pattern limits
            active_patterns = sum(1 for p in settings.event_filters.title_patterns if p.is_active)
            if active_patterns > 25:  # Reasonable performance limit
                errors.append(
                    f"Too many active filter patterns ({active_patterns}). "
                    "Consider disabling some patterns for better performance."
                )

            # Additional validation rules can be added here

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return errors

    def reset_to_defaults(self) -> SettingsData:
        """Reset all settings to default values.

        Returns:
            New SettingsData object with default values

        Raises:
            SettingsError: If reset operation fails
        """
        try:
            logger.info("Resetting settings to defaults")

            # Create backup before reset
            self.persistence.create_backup("pre_reset")

            # Create new default settings
            default_settings = SettingsData()
            default_settings.metadata.last_modified_by = "reset_operation"

            # Save and return defaults
            return self.update_settings(default_settings)

        except Exception as e:
            raise SettingsError("Failed to reset settings to defaults", details={"error": str(e)})

    def export_settings(self, export_path: Path) -> bool:
        """Export current settings to a file.

        Args:
            export_path: Path where settings should be exported

        Returns:
            True if export succeeded

        Raises:
            SettingsError: If export fails
        """
        try:
            return self.persistence.export_settings(export_path)
        except Exception as e:
            raise SettingsError(
                "Failed to export settings",
                details={"export_path": str(export_path), "error": str(e)},
            )

    def import_settings(self, import_path: Path) -> SettingsData:
        """Import settings from a file.

        Args:
            import_path: Path to settings file to import

        Returns:
            Imported SettingsData object

        Raises:
            SettingsError: If import fails
        """
        try:
            settings = self.persistence.import_settings(import_path)
            # Update cache after import
            self._current_settings = settings
            return settings
        except Exception as e:
            raise SettingsError(
                "Failed to import settings",
                details={"import_path": str(import_path), "error": str(e)},
            )

    def get_settings_info(self) -> Dict[str, Any]:
        """Get comprehensive information about current settings.

        Returns:
            Dictionary containing settings information and statistics
        """
        try:
            settings = self.get_settings()
            persistence_info = self.persistence.get_settings_info()

            return {
                "settings_data": {
                    "active_filters": settings.get_active_filter_count(),
                    "total_match_count": settings.get_total_match_count(),
                    "default_layout": settings.display.default_layout,
                    "display_density": settings.display.display_density,
                    "hide_all_day_events": settings.event_filters.hide_all_day_events,
                    "conflict_display_mode": settings.conflict_resolution.conflict_display_mode,
                    "schema_version": settings.metadata.version,
                    "last_modified": settings.metadata.last_modified.isoformat(),
                },
                "persistence_info": persistence_info,
                "service_info": {
                    "config_directory": str(self.config_dir),
                    "calendarbot_integration": True,
                    "cache_status": "loaded" if self._current_settings else "not_loaded",
                },
            }

        except Exception as e:
            logger.error(f"Error getting settings info: {e}")
            return {
                "error": str(e),
                "service_info": {
                    "config_directory": str(self.config_dir),
                    "calendarbot_integration": True,
                    "cache_status": "error",
                },
            }

    def create_backup(self, backup_name: Optional[str] = None) -> Path:
        """Create a manual backup of current settings.

        Args:
            backup_name: Optional custom name for the backup

        Returns:
            Path to the created backup file

        Raises:
            SettingsError: If backup creation fails
        """
        try:
            return self.persistence.create_backup(backup_name)
        except Exception as e:
            raise SettingsError(
                "Failed to create settings backup",
                details={"backup_name": backup_name, "error": str(e)},
            )

    def list_backups(self) -> List[Tuple[Path, str]]:
        """List available settings backups.

        Returns:
            List of tuples containing (backup_path, formatted_timestamp)
        """
        try:
            backups = self.persistence.list_backups()
            return [(path, timestamp.strftime("%Y-%m-%d %H:%M:%S")) for path, timestamp in backups]
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []

    def _validate_settings_consistency(self, settings: SettingsData) -> None:
        """Validate internal consistency of settings data.

        Args:
            settings: SettingsData object to validate

        Raises:
            SettingsValidationError: If consistency checks fail
        """
        errors = []

        # Check for conflicting display settings
        if (
            settings.display.display_density == "compact"
            and settings.display.font_sizes.get("body") == "extra-large"
        ):
            errors.append("Compact display density conflicts with extra-large body font")

        # Check filter pattern consistency
        pattern_texts = [p.pattern for p in settings.event_filters.title_patterns]
        if len(pattern_texts) != len(set(pattern_texts)):
            errors.append("Duplicate filter patterns detected")

        if errors:
            raise SettingsValidationError(
                "Settings consistency validation failed", validation_errors=errors
            )

    def _get_available_layouts(self) -> List[str]:
        """Get list of available layouts from CalendarBot system.

        Returns:
            List of available layout names
        """
        try:
            # Try to import and use layout registry
            from ..layout.registry import LayoutRegistry

            registry = LayoutRegistry()
            return registry.get_available_layouts()
        except Exception as e:
            logger.warning(f"Could not get available layouts: {e}")
            # Return common default layouts as fallback
            return ["3x4", "4x8", "whats-next-view"]
