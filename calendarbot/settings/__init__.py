"""
CalendarBot Settings Management Module.

This module provides comprehensive settings management capabilities for CalendarBot,
including data models, persistence, and business logic for handling user preferences
and application configuration.

Public API:
    SettingsService: Main service class for settings operations
    FilterPattern: Individual filter pattern configuration
    EventFilterSettings: Event filtering configuration
    ConflictResolutionSettings: Meeting conflict resolution configuration
    DisplaySettings: Display and layout preferences
    SettingsData: Complete settings data structure
    SettingsError: Base exception for settings-related errors
    SettingsValidationError: Settings validation error
    SettingsPersistenceError: Settings persistence error
"""

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
from .service import SettingsService

__all__ = [
    "ConflictResolutionSettings",
    "DisplaySettings",
    "EventFilterSettings",
    "FilterPattern",
    "SettingsData",
    "SettingsError",
    "SettingsMetadata",
    "SettingsPersistence",
    "SettingsPersistenceError",
    "SettingsService",
    "SettingsValidationError",
]

__version__ = "1.0.0"
