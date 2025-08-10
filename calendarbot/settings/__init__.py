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

# Import kiosk models if available
try:
    from .kiosk_models import (
        KioskDisplaySettings,  # noqa: F401
        KioskMonitoringSettings,  # noqa: F401
        KioskPiOptimizationSettings,  # noqa: F401
        KioskSecuritySettings,  # noqa: F401
        KioskSettings,  # noqa: F401
        KioskSystemSettings,  # noqa: F401
    )

    _kiosk_exports = [
        "KioskDisplaySettings",
        "KioskMonitoringSettings",
        "KioskPiOptimizationSettings",
        "KioskSecuritySettings",
        "KioskSettings",
        "KioskSystemSettings",
    ]
except ImportError:
    _kiosk_exports = []

# Build __all__ list - must contain only strings for static analyzers
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

# Conditionally extend with kiosk exports
try:
    # Only add if kiosk imports succeeded
    if "KioskSettings" in globals():
        __all__.extend(
            [
                "KioskDisplaySettings",
                "KioskMonitoringSettings",
                "KioskPiOptimizationSettings",
                "KioskSecuritySettings",
                "KioskSettings",
                "KioskSystemSettings",
            ]
        )
except NameError:
    pass

__version__ = "1.0.0"
