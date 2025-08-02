"""
Settings data models using Pydantic for validation and type safety.

This module defines the complete data model structure for CalendarBot settings,
including validation logic, default values, and comprehensive documentation.
All models use Pydantic for automatic validation, serialization, and type checking.
"""

import builtins
import logging
import re
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .exceptions import SettingsValidationError

logger = logging.getLogger(__name__)


class FilterPattern(BaseModel):
    """Individual filter pattern configuration for event filtering.

    Represents a single filtering rule that can be applied to calendar events,
    supporting both literal text matching and regular expression patterns.

    Attributes:
        pattern: The filter pattern (text or regex)
        is_regex: Whether the pattern should be treated as a regular expression
        is_active: Whether this filter is currently enabled
        case_sensitive: Whether pattern matching is case sensitive
        match_count: Number of events this pattern has matched (for analytics)
        description: Optional user-provided description of the filter purpose

    Example:
        >>> filter_pat = FilterPattern(
        ...     pattern="Daily Standup",
        ...     description="Hide routine standup meetings"
        ... )
        >>> filter_pat.is_active
        True
    """

    pattern: str = Field(
        ..., min_length=1, max_length=500, description="Filter pattern (text or regex)"
    )
    is_regex: bool = Field(default=False, description="Whether pattern is regex")
    is_active: bool = Field(default=True, description="Whether filter is enabled")
    case_sensitive: bool = Field(default=False, description="Case sensitive matching")
    match_count: int = Field(default=0, ge=0, description="Number of events matched")
    description: Optional[str] = Field(default=None, max_length=200, description="User description")

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Validate pattern syntax.

        Args:
            v: The pattern string to validate

        Returns:
            The validated pattern string

        Raises:
            SettingsValidationError: If pattern is invalid
        """
        if not v.strip():
            raise SettingsValidationError(
                "Pattern cannot be empty or whitespace only", field_name="pattern", field_value=v
            )
        return v.strip()

    @model_validator(mode="after")
    def validate_regex_pattern(self) -> "FilterPattern":
        """Validate regex pattern syntax if is_regex is True.

        Returns:
            The validated FilterPattern instance

        Raises:
            SettingsValidationError: If regex pattern is invalid
        """
        if self.is_regex:
            try:
                re.compile(self.pattern)
            except re.error as e:
                raise SettingsValidationError(
                    f"Invalid regex pattern: {e}",
                    field_name="pattern",
                    field_value=self.pattern,
                    validation_errors=[str(e)],
                ) from e
        return self

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean description field.

        Args:
            v: The description string to validate

        Returns:
            The cleaned description or None
        """
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class EventFilterSettings(BaseModel):
    """Event filtering configuration for reducing calendar clutter.

    Contains all settings related to filtering calendar events, including
    title patterns, category filters, and special event type handling.

    Attributes:
        enabled: Whether event filtering is globally enabled
        hide_all_day_events: Whether to hide all-day calendar events
        title_patterns: List of title filter patterns to apply
        event_categories: Category-based filter settings
        recurring_filters: Recurring event filter settings
        attendee_count_filter: Filter events by attendee count range
        default_action: Default action for events not matching any pattern

    Example:
        >>> filters = EventFilterSettings(
        ...     enabled=True,
        ...     hide_all_day_events=True,
        ...     title_patterns=[FilterPattern(pattern="Lunch", description="Hide lunch blocks")]
        ... )
    """

    enabled: bool = Field(default=True, description="Whether event filtering is enabled")
    hide_all_day_events: bool = Field(default=False, description="Hide all-day events")
    title_patterns: list[FilterPattern] = Field(
        default_factory=list, description="Title filter patterns"
    )
    event_categories: dict[str, bool] = Field(
        default_factory=dict, description="Category filter settings"
    )
    recurring_filters: dict[str, bool] = Field(
        default_factory=dict, description="Recurring event filters"
    )
    attendee_count_filter: Optional[dict[str, int]] = Field(
        default=None, description="Filter by attendee count"
    )
    default_action: str = Field(default="include", description="Default action: include or exclude")

    @model_validator(mode="before")
    @classmethod
    def map_patterns_field(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Map 'patterns' field to 'title_patterns' for backward compatibility.

        Args:
            values: Input values dictionary

        Returns:
            Modified values with patterns mapped to title_patterns
        """
        # Handle backward compatibility: map 'patterns' to 'title_patterns'
        if "patterns" in values and "title_patterns" not in values:
            values["title_patterns"] = values["patterns"]

        return values

    @field_validator("title_patterns")
    @classmethod
    def validate_title_patterns(cls, v: list[FilterPattern]) -> list[FilterPattern]:
        """Validate title pattern list for duplicates and limits.

        Args:
            v: List of filter patterns to validate

        Returns:
            The validated list of patterns

        Raises:
            SettingsValidationError: If validation fails
        """
        if len(v) > 50:  # Reasonable limit to prevent performance issues
            raise SettingsValidationError(
                "Too many title patterns (maximum 50 allowed)",
                field_name="title_patterns",
                field_value=f"{len(v)} patterns",
            )

        # Check for duplicate patterns
        seen_patterns = set()
        for pattern in v:
            pattern_key = (pattern.pattern.lower(), pattern.is_regex, pattern.case_sensitive)
            if pattern_key in seen_patterns:
                raise SettingsValidationError(
                    f"Duplicate pattern detected: {pattern.pattern}",
                    field_name="title_patterns",
                    field_value=pattern.pattern,
                )
            seen_patterns.add(pattern_key)

        return v

    @field_validator("attendee_count_filter")
    @classmethod
    def validate_attendee_count_filter(
        cls, v: Optional[dict[str, int]]
    ) -> Optional[dict[str, int]]:
        """Validate attendee count filter settings.

        Args:
            v: Attendee count filter configuration

        Returns:
            The validated filter configuration

        Raises:
            SettingsValidationError: If filter configuration is invalid
        """
        if v is None:
            return v

        # Validate required keys and ranges
        if "min_count" in v and v["min_count"] < 0:
            raise SettingsValidationError(
                "Minimum attendee count cannot be negative",
                field_name="attendee_count_filter.min_count",
                field_value=v["min_count"],
            )

        if "max_count" in v and v["max_count"] < 0:
            raise SettingsValidationError(
                "Maximum attendee count cannot be negative",
                field_name="attendee_count_filter.max_count",
                field_value=v["max_count"],
            )

        if "min_count" in v and "max_count" in v and v["min_count"] > v["max_count"]:
            raise SettingsValidationError(
                "Minimum attendee count cannot be greater than maximum",
                field_name="attendee_count_filter",
                field_value=v,
            )

        return v

    @field_validator("default_action")
    @classmethod
    def validate_default_action(cls, v: str) -> str:
        """Validate default action setting.

        Args:
            v: The default action string to validate

        Returns:
            The validated default action

        Raises:
            SettingsValidationError: If default action is invalid
        """
        valid_actions = {"include", "exclude"}
        if v not in valid_actions:
            raise SettingsValidationError(
                f"Invalid default action: {v}",
                field_name="default_action",
                field_value=v,
                validation_errors=[f"Must be one of: {', '.join(valid_actions)}"],
            )
        return v

    def dict(self, **kwargs: Any) -> dict[str, Any]:
        """Override dict method to include backward compatibility for integration tests.

        Args:
            **kwargs: Additional arguments passed to parent dict method

        Returns:
            Dictionary representation with backward compatibility
        """
        result = super().dict(**kwargs)

        # Add backward compatibility for integration tests that expect 'patterns' key
        # while maintaining the correct 'title_patterns' key for frontend
        if "title_patterns" in result:
            result["patterns"] = result["title_patterns"]

        return result


class ConflictResolutionSettings(BaseModel):
    """Meeting conflict resolution configuration.

    Defines how overlapping meetings should be prioritized and displayed
    when multiple events occur at the same time.

    Attributes:
        priority_by_acceptance: Prioritize accepted meetings over tentative/unresponded
        priority_by_attendee_count: Prioritize meetings by number of attendees
        priority_by_organizer: Prioritize meetings based on organizer importance
        show_multiple_conflicts: Whether to show indicators for multiple conflicts
        conflict_display_mode: How to display conflicting meetings

    Example:
        >>> conflicts = ConflictResolutionSettings(
        ...     priority_by_acceptance=True,
        ...     conflict_display_mode="primary"
        ... )
    """

    priority_by_acceptance: bool = Field(default=True, description="Prioritize accepted meetings")
    priority_by_attendee_count: bool = Field(
        default=False, description="Prioritize by attendee count"
    )
    priority_by_organizer: bool = Field(default=False, description="Prioritize by organizer")
    show_multiple_conflicts: bool = Field(default=True, description="Show conflict indicators")
    conflict_display_mode: str = Field(default="primary", description="primary|all|indicator")

    @field_validator("conflict_display_mode")
    @classmethod
    def validate_conflict_display_mode(cls, v: str) -> str:
        """Validate conflict display mode setting.

        Args:
            v: The display mode string to validate

        Returns:
            The validated display mode

        Raises:
            SettingsValidationError: If display mode is invalid
        """
        valid_modes = {"primary", "all", "indicator"}
        if v not in valid_modes:
            raise SettingsValidationError(
                f"Invalid conflict display mode: {v}",
                field_name="conflict_display_mode",
                field_value=v,
                validation_errors=[f"Must be one of: {', '.join(valid_modes)}"],
            )
        return v


class EpaperSettings(BaseModel):
    """E-Paper display configuration settings.

    Comprehensive configuration for e-Paper display functionality including
    hardware detection, display properties, rendering options, and fallback settings.

    Attributes:
        enabled: Whether e-Paper functionality is enabled
        display_model: Specific e-Paper display model identifier
        width: Display width in pixels
        height: Display height in pixels
        rotation: Display rotation in degrees (0, 90, 180, 270)
        supports_partial_refresh: Whether partial refresh is supported
        supports_grayscale: Whether grayscale rendering is supported
        supports_red: Whether red color channel is supported
        refresh_interval: Full refresh interval in seconds
        partial_refresh_enabled: Whether to use partial refresh when available
        contrast_level: Display contrast level (0-100)
        dither_mode: Dithering algorithm for color reduction
        png_fallback_enabled: Whether to save PNG fallback images
        png_output_path: Path for PNG fallback output
        hardware_detection_enabled: Whether to auto-detect hardware
        error_fallback_mode: Fallback mode on hardware errors
        color_palette: Color palette configuration
        update_strategy: Display update strategy

    Example:
        >>> epaper = EpaperSettings(
        ...     enabled=True,
        ...     display_model="waveshare_4_2",
        ...     width=400,
        ...     height=300,
        ...     rotation=0,
        ...     refresh_interval=300
        ... )
    """

    # Core Configuration
    enabled: bool = Field(default=True, description="Enable e-Paper functionality")
    display_model: Optional[str] = Field(
        default=None, description="E-Paper display model (e.g., 'waveshare_4_2', 'waveshare_7_5')"
    )

    # Display Properties
    width: int = Field(default=400, ge=100, le=2000, description="Display width in pixels")
    height: int = Field(default=300, ge=100, le=2000, description="Display height in pixels")
    rotation: int = Field(default=0, description="Display rotation in degrees")

    # Display Capabilities
    supports_partial_refresh: bool = Field(default=True, description="Supports partial refresh")
    supports_grayscale: bool = Field(default=True, description="Supports grayscale rendering")
    supports_red: bool = Field(default=False, description="Supports red color channel")

    # Refresh Settings
    refresh_interval: int = Field(
        default=300, ge=30, le=3600, description="Full refresh interval in seconds"
    )
    partial_refresh_enabled: bool = Field(default=True, description="Enable partial refresh")

    # Rendering Options
    contrast_level: int = Field(
        default=100, ge=0, le=100, description="Display contrast level (0-100)"
    )
    dither_mode: str = Field(
        default="floyd_steinberg", description="Dithering mode: none, floyd_steinberg, ordered"
    )

    # Fallback Configuration
    png_fallback_enabled: bool = Field(default=True, description="Enable PNG fallback output")
    png_output_path: Optional[str] = Field(
        default=None, description="Custom path for PNG fallback files"
    )

    # Hardware Detection
    hardware_detection_enabled: bool = Field(
        default=True, description="Enable hardware auto-detection"
    )
    error_fallback_mode: str = Field(
        default="png", description="Fallback mode on errors: png, console, disable"
    )

    # Advanced Settings
    color_palette: dict[str, str] = Field(
        default_factory=lambda: {
            "background": "#FFFFFF",
            "foreground": "#000000",
            "accent": "#FF0000",
        },
        description="Color palette configuration",
    )
    update_strategy: str = Field(
        default="adaptive", description="Update strategy: full, partial, adaptive"
    )

    @field_validator("rotation")
    @classmethod
    def validate_rotation(cls, v: int) -> int:
        """Validate display rotation value.

        Args:
            v: Rotation value in degrees

        Returns:
            The validated rotation value

        Raises:
            SettingsValidationError: If rotation is invalid
        """
        valid_rotations = {0, 90, 180, 270}
        if v not in valid_rotations:
            raise SettingsValidationError(
                f"Invalid rotation: {v}",
                field_name="rotation",
                field_value=v,
                validation_errors=[f"Must be one of: {', '.join(map(str, valid_rotations))}"],
            )
        return v

    @field_validator("dither_mode")
    @classmethod
    def validate_dither_mode(cls, v: str) -> str:
        """Validate dithering mode.

        Args:
            v: Dithering mode string

        Returns:
            The validated dithering mode

        Raises:
            SettingsValidationError: If dither mode is invalid
        """
        valid_modes = {"none", "floyd_steinberg", "ordered"}
        if v not in valid_modes:
            raise SettingsValidationError(
                f"Invalid dither mode: {v}",
                field_name="dither_mode",
                field_value=v,
                validation_errors=[f"Must be one of: {', '.join(valid_modes)}"],
            )
        return v

    @field_validator("error_fallback_mode")
    @classmethod
    def validate_error_fallback_mode(cls, v: str) -> str:
        """Validate error fallback mode.

        Args:
            v: Error fallback mode string

        Returns:
            The validated fallback mode

        Raises:
            SettingsValidationError: If fallback mode is invalid
        """
        valid_modes = {"png", "console", "disable"}
        if v not in valid_modes:
            raise SettingsValidationError(
                f"Invalid error fallback mode: {v}",
                field_name="error_fallback_mode",
                field_value=v,
                validation_errors=[f"Must be one of: {', '.join(valid_modes)}"],
            )
        return v

    @field_validator("update_strategy")
    @classmethod
    def validate_update_strategy(cls, v: str) -> str:
        """Validate display update strategy.

        Args:
            v: Update strategy string

        Returns:
            The validated update strategy

        Raises:
            SettingsValidationError: If update strategy is invalid
        """
        valid_strategies = {"full", "partial", "adaptive"}
        if v not in valid_strategies:
            raise SettingsValidationError(
                f"Invalid update strategy: {v}",
                field_name="update_strategy",
                field_value=v,
                validation_errors=[f"Must be one of: {', '.join(valid_strategies)}"],
            )
        return v

    @field_validator("color_palette")
    @classmethod
    def validate_color_palette(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate color palette configuration.

        Args:
            v: Color palette dictionary

        Returns:
            The validated color palette

        Raises:
            SettingsValidationError: If color palette is invalid
        """
        required_colors = {"background", "foreground"}
        for color_name in required_colors:
            if color_name not in v:
                raise SettingsValidationError(
                    f"Missing required color in palette: {color_name}",
                    field_name="color_palette",
                    field_value=v,
                )

        # Validate hex color format for each color
        import re  # noqa: PLC0415

        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for color_name, color_value in v.items():
            if not hex_pattern.match(color_value):
                raise SettingsValidationError(
                    f"Invalid hex color format for {color_name}: {color_value}",
                    field_name=f"color_palette.{color_name}",
                    field_value=color_value,
                    validation_errors=["Color must be in format #RRGGBB"],
                )

        return v

    @model_validator(mode="before")
    @classmethod
    def set_png_output_default(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Set default PNG output path if not specified.

        Args:
            values: Input values dictionary

        Returns:
            Values with default PNG output path set
        """
        if values.get("png_fallback_enabled", True) and not values.get("png_output_path"):
            values["png_output_path"] = "epaper_output.png"
        return values


class DisplaySettings(BaseModel):
    """Display and layout preferences for CalendarBot interface.

    Controls the visual presentation of the calendar interface including
    layout selection, typography, spacing, and theme preferences.

    Attributes:
        default_layout: Default layout name to use on startup
        font_sizes: Font size overrides for different UI components
        display_density: Information density level
        color_theme: Color theme preference
        animation_enabled: Whether to enable UI animations
        timezone: User's preferred timezone for time calculations

    Example:
        >>> display = DisplaySettings(
        ...     default_layout="whats-next-view",
        ...     display_density="compact",
        ...     font_sizes={"headers": "large", "body": "medium"},
        ...     timezone="America/Los_Angeles"
        ... )
    """

    default_layout: str = Field(default="whats-next-view", description="Default layout name")
    font_sizes: dict[str, str] = Field(default_factory=dict, description="Font size overrides")
    display_density: str = Field(default="normal", description="compact|normal|spacious")
    color_theme: str = Field(default="default", description="Color theme preference")
    animation_enabled: bool = Field(default=True, description="Enable animations")
    timezone: str = Field(default="UTC", description="User's preferred timezone")

    @field_validator("default_layout")
    @classmethod
    def validate_default_layout(cls, v: str) -> str:
        """Validate default layout name.

        Args:
            v: Layout name to validate

        Returns:
            The validated layout name

        Raises:
            SettingsValidationError: If layout name is invalid
        """
        # Basic validation - more specific validation can be done at the service level
        # where available layouts are known
        if not v.strip():
            raise SettingsValidationError(
                "Default layout cannot be empty", field_name="default_layout", field_value=v
            )
        return v.strip()

    @field_validator("display_density")
    @classmethod
    def validate_display_density(cls, v: str) -> str:
        """Validate display density setting.

        Args:
            v: Display density to validate

        Returns:
            The validated density setting

        Raises:
            SettingsValidationError: If density is invalid
        """
        valid_densities = {"compact", "normal", "spacious"}
        if v not in valid_densities:
            raise SettingsValidationError(
                f"Invalid display density: {v}",
                field_name="display_density",
                field_value=v,
                validation_errors=[f"Must be one of: {', '.join(valid_densities)}"],
            )
        return v

    @field_validator("font_sizes")
    @classmethod
    def validate_font_sizes(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate font size configuration.

        Args:
            v: Font size configuration dictionary

        Returns:
            The validated font size configuration

        Raises:
            SettingsValidationError: If font sizes are invalid
        """
        valid_sizes = {"small", "medium", "large", "extra-large"}
        valid_components = {"headers", "body", "time_labels", "navigation"}

        for component, size in v.items():
            if component not in valid_components:
                logger.warning(f"Unknown font component: {component}")

            if size not in valid_sizes:
                raise SettingsValidationError(
                    f"Invalid font size '{size}' for component '{component}'",
                    field_name=f"font_sizes.{component}",
                    field_value=size,
                    validation_errors=[f"Must be one of: {', '.join(valid_sizes)}"],
                )

        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone string.

        Args:
            v: Timezone string to validate

        Returns:
            The validated timezone string

        Raises:
            SettingsValidationError: If timezone is invalid
        """
        if not v.strip():
            raise SettingsValidationError(
                "Timezone cannot be empty", field_name="timezone", field_value=v
            )

        try:
            import pytz  # noqa: PLC0415

            # Validate timezone exists
            pytz.timezone(v)
            return v.strip()
        except ImportError:
            # If pytz is not available, accept common timezone formats
            logger.warning("pytz not available for timezone validation")
            common_timezones = {
                "UTC",
                "GMT",
                "EST",
                "CST",
                "MST",
                "PST",
                "America/New_York",
                "America/Chicago",
                "America/Denver",
                "America/Los_Angeles",
                "Europe/London",
                "Europe/Paris",
                "Asia/Tokyo",
                "Australia/Sydney",
            }
            if v not in common_timezones:
                logger.warning(f"Could not validate timezone {v} - pytz not available")
            return v.strip()
        except Exception as e:
            # Handle pytz.exceptions.UnknownTimeZoneError and other pytz errors
            if "UnknownTimeZoneError" in str(type(e)) or "timezone" in str(e).lower():
                raise SettingsValidationError(
                    f"Invalid timezone: {v}",
                    field_name="timezone",
                    field_value=v,
                    validation_errors=[
                        "Must be a valid timezone (e.g., 'America/Los_Angeles', 'Europe/London', 'UTC')"
                    ],
                ) from e
            logger.warning(f"Timezone validation error: {e}")
            return v.strip()


class SettingsMetadata(BaseModel):
    """Settings metadata and versioning information.

    Tracks metadata about the settings data structure including version,
    modification history, and device identification for synchronization.

    Attributes:
        version: Settings schema version for compatibility tracking
        last_modified: Timestamp of last modification
        last_modified_by: Identifier of last modifier
        device_id: Optional device identifier for multi-device setups

    Example:
        >>> metadata = SettingsMetadata(
        ...     version="1.0.0",
        ...     last_modified_by="web_interface"
        ... )
    """

    version: str = Field(default="1.0.0", description="Settings schema version")
    last_modified: datetime = Field(
        default_factory=datetime.now, description="Last modification time"
    )
    last_modified_by: str = Field(default="user", description="Last modifier")
    device_id: Optional[str] = Field(default=None, description="Device identifier")

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version string format.

        Args:
            v: Version string to validate

        Returns:
            The validated version string

        Raises:
            SettingsValidationError: If version format is invalid
        """
        # Basic semantic version validation (x.y.z)
        version_pattern = r"^\d+\.\d+\.\d+$"
        if not re.match(version_pattern, v):
            raise SettingsValidationError(
                f"Invalid version format: {v}",
                field_name="version",
                field_value=v,
                validation_errors=["Version must be in format x.y.z (e.g., 1.0.0)"],
            )
        return v


class SettingsData(BaseModel):
    """Complete settings data structure containing all user preferences.

    This is the top-level settings container that encompasses all configuration
    categories and provides a unified interface for settings management.

    Attributes:
        event_filters: Event filtering configuration
        conflict_resolution: Meeting conflict resolution settings
        display: Display and layout preferences
        epaper: E-Paper display configuration (core feature)
        metadata: Settings metadata and versioning

    Example:
        >>> settings = SettingsData(
        ...     event_filters=EventFilterSettings(hide_all_day_events=True),
        ...     display=DisplaySettings(default_layout="whats-next-view"),
        ...     epaper=EpaperSettings(enabled=True, display_model="waveshare_4_2")
        ... )
    """

    event_filters: EventFilterSettings = Field(
        default_factory=EventFilterSettings, description="Event filtering configuration"
    )
    conflict_resolution: ConflictResolutionSettings = Field(
        default_factory=ConflictResolutionSettings,
        description="Meeting conflict resolution settings",
    )
    display: DisplaySettings = Field(
        default_factory=DisplaySettings, description="Display and layout preferences"
    )
    epaper: EpaperSettings = Field(
        default_factory=EpaperSettings, description="E-Paper display configuration (core feature)"
    )
    metadata: SettingsMetadata = Field(
        default_factory=SettingsMetadata, description="Settings metadata and versioning"
    )

    @model_validator(mode="after")
    def validate_settings_consistency(self) -> "SettingsData":
        """Validate cross-field consistency and update metadata.

        Returns:
            The validated SettingsData instance
        """
        # Update last_modified timestamp when settings are created/modified
        if self.metadata:
            self.metadata.last_modified = datetime.now()

        # Additional cross-validation can be added here
        # For example, ensuring display.default_layout is compatible with filters

        return self

    def dict(self, **kwargs: Any) -> dict[str, Any]:
        """Override dict method to ensure custom EventFilterSettings serialization.

        Args:
            **kwargs: Additional arguments passed to parent dict method

        Returns:
            Dictionary representation with proper field serialization
        """
        result = super().dict(**kwargs)

        # Ensure event_filters uses the custom dict method that includes 'patterns' key
        result["event_filters"] = self.event_filters.dict()

        return result

    def to_api_dict(self) -> builtins.dict[str, Any]:
        """Convert settings to API-friendly dictionary format.

        Returns:
            Dictionary representation suitable for API responses
        """
        # Get the standard dictionary representation
        event_filters_dict = self.event_filters.dict()

        # Add backward compatibility for integration tests that expect 'patterns' key
        # while maintaining the correct 'title_patterns' key for frontend
        if "title_patterns" in event_filters_dict:
            event_filters_dict["patterns"] = event_filters_dict["title_patterns"]

        return {
            "event_filters": event_filters_dict,
            "conflict_resolution": self.conflict_resolution.dict(),
            "display": self.display.dict(),
            "epaper": self.epaper.dict(),
            "metadata": {
                **self.metadata.dict(),
                "last_modified": self.metadata.last_modified.isoformat(),
            },
        }

    def get_active_filter_count(self) -> int:
        """Get count of active filter patterns.

        Returns:
            Number of currently active filter patterns
        """
        return sum(1 for pattern in self.event_filters.title_patterns if pattern.is_active)

    def get_total_match_count(self) -> int:
        """Get total number of events matched by all filters.

        Returns:
            Total match count across all filter patterns
        """
        return sum(pattern.match_count for pattern in self.event_filters.title_patterns)
