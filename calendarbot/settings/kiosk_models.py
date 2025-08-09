"""
Kiosk mode settings models using Pydantic for validation and type safety.

This module defines comprehensive Pydantic models for kiosk mode configuration,
optimized for Raspberry Pi Zero 2W deployment with 512MB memory constraints.
All models follow CalendarBot patterns for validation, serialization, and type checking.
"""

import logging
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .exceptions import SettingsValidationError

logger = logging.getLogger(__name__)


class KioskDisplaySettings(BaseModel):
    """Display configuration for kiosk mode optimized for 480x800 portrait display.

    Defines display properties, touch interface settings, and UI customization
    options for kiosk deployment scenarios.

    Attributes:
        width: Display width in pixels
        height: Display height in pixels
        orientation: Display orientation (portrait, landscape, etc.)
        scale_factor: Display scaling factor for UI elements
        touch_enabled: Enable touch input handling
        touch_calibration: Touch calibration parameters if needed
        screen_saver_timeout: Screen saver timeout in seconds (0 = disabled)
        brightness: Display brightness percentage
        auto_brightness: Automatically adjust brightness based on ambient light
        hide_cursor: Hide mouse cursor in kiosk mode
        fullscreen_mode: Force fullscreen browser display
        prevent_zoom: Prevent user zoom gestures

    Example:
        >>> display = KioskDisplaySettings(
        ...     width=480,
        ...     height=800,
        ...     orientation="portrait",
        ...     brightness=80
        ... )
    """

    # Physical display properties
    width: int = Field(default=480, ge=320, le=1920, description="Display width in pixels")

    height: int = Field(default=800, ge=240, le=1080, description="Display height in pixels")

    orientation: str = Field(
        default="portrait",
        description="Display orientation: portrait, landscape, portrait-flipped, landscape-flipped",
    )

    scale_factor: float = Field(
        default=1.0, ge=0.5, le=3.0, description="Display scaling factor for UI elements"
    )

    # Touch interface
    touch_enabled: bool = Field(default=True, description="Enable touch input handling")

    touch_calibration: Optional[dict[str, float]] = Field(
        default=None, description="Touch calibration parameters if needed"
    )

    # Kiosk display behavior
    screen_saver_timeout: int = Field(
        default=0, ge=0, le=3600, description="Screen saver timeout in seconds (0 = disabled)"
    )

    brightness: int = Field(default=100, ge=10, le=100, description="Display brightness percentage")

    auto_brightness: bool = Field(
        default=False, description="Automatically adjust brightness based on ambient light"
    )

    # UI customization
    hide_cursor: bool = Field(default=True, description="Hide mouse cursor in kiosk mode")

    fullscreen_mode: bool = Field(default=True, description="Force fullscreen browser display")

    prevent_zoom: bool = Field(default=True, description="Prevent user zoom gestures")

    @field_validator("orientation")
    @classmethod
    def validate_orientation(cls, v: str) -> str:
        """Validate display orientation setting.

        Args:
            v: The orientation string to validate

        Returns:
            The validated orientation string

        Raises:
            SettingsValidationError: If orientation is invalid
        """
        valid_orientations = {"portrait", "landscape", "portrait-flipped", "landscape-flipped"}
        if v not in valid_orientations:
            raise SettingsValidationError(
                f"Invalid display orientation: {v}",
                field_name="orientation",
                field_value=v,
                validation_errors=[f"Must be one of: {', '.join(valid_orientations)}"],
            )
        return v

    @field_validator("touch_calibration")
    @classmethod
    def validate_touch_calibration(
        cls, v: Optional[dict[str, float]]
    ) -> Optional[dict[str, float]]:
        """Validate touch calibration parameters.

        Args:
            v: Touch calibration dictionary

        Returns:
            The validated calibration parameters

        Raises:
            SettingsValidationError: If calibration parameters are invalid
        """
        if v is None:
            return v

        required_keys = {"offset_x", "offset_y", "scale_x", "scale_y"}
        if not all(key in v for key in required_keys):
            raise SettingsValidationError(
                f"Touch calibration missing required keys: {required_keys - set(v.keys())}",
                field_name="touch_calibration",
                field_value=v,
            )

        # Validate scale values are positive
        for key in ["scale_x", "scale_y"]:
            if v[key] <= 0:
                raise SettingsValidationError(
                    f"Touch calibration {key} must be positive",
                    field_name=f"touch_calibration.{key}",
                    field_value=v[key],
                )

        return v


class KioskBrowserSettings(BaseModel):
    """Chromium browser configuration optimized for Pi Zero 2W memory constraints.

    Provides comprehensive browser process management, memory optimization,
    crash recovery, and Pi Zero 2W specific performance tuning.

    Attributes:
        executable_path: Path to Chromium executable
        startup_delay: Delay before starting browser after web server ready
        startup_timeout: Maximum seconds to wait for browser startup
        shutdown_timeout: Maximum seconds to wait for graceful shutdown
        crash_restart_delay: Initial delay before restarting crashed browser
        max_restart_attempts: Maximum restart attempts per hour
        restart_backoff_factor: Exponential backoff factor for restart delays
        reset_attempts_after: Reset restart attempt counter after this time
        memory_limit_mb: Maximum memory usage before restart
        memory_warning_threshold: Memory usage percentage to trigger warning
        memory_critical_threshold: Memory usage percentage to trigger restart
        cache_clear_on_restart: Clear browser cache when restarting
        health_check_interval: Health check interval in seconds
        response_timeout: Timeout for health check responses
        custom_flags: Additional Chromium command line flags
        disable_extensions: Disable all Chromium extensions
        disable_plugins: Disable browser plugins

    Example:
        >>> browser = KioskBrowserSettings(
        ...     memory_limit_mb=128,
        ...     startup_delay=5,
        ...     max_restart_attempts=3
        ... )
    """

    # Process management
    executable_path: str = Field(
        default="chromium-browser", description="Path to Chromium executable"
    )

    startup_delay: int = Field(
        default=5,
        ge=0,
        le=60,
        description="Delay in seconds before starting browser after web server ready",
    )

    startup_timeout: int = Field(
        default=30, ge=10, le=120, description="Maximum seconds to wait for browser startup"
    )

    shutdown_timeout: int = Field(
        default=10, ge=1, le=30, description="Maximum seconds to wait for graceful browser shutdown"
    )

    # Restart and recovery
    crash_restart_delay: int = Field(
        default=3,
        ge=1,
        le=30,
        description="Initial delay in seconds before restarting crashed browser",
    )

    max_restart_attempts: int = Field(
        default=5, ge=1, le=20, description="Maximum restart attempts per hour"
    )

    restart_backoff_factor: float = Field(
        default=1.5, ge=1.0, le=3.0, description="Exponential backoff factor for restart delays"
    )

    reset_attempts_after: int = Field(
        default=3600,
        ge=300,
        le=86400,
        description="Reset restart attempt counter after this many seconds",
    )

    # Memory management
    memory_limit_mb: int = Field(
        default=80, ge=64, le=256, description="Maximum memory usage in MB before restart"
    )

    memory_warning_threshold: float = Field(
        default=0.85, ge=0.5, le=0.95, description="Memory usage percentage to trigger warning"
    )

    memory_critical_threshold: float = Field(
        default=0.95, ge=0.8, le=1.0, description="Memory usage percentage to trigger restart"
    )

    cache_clear_on_restart: bool = Field(
        default=True, description="Clear browser cache when restarting"
    )

    # Health monitoring
    health_check_interval: int = Field(
        default=30, ge=5, le=300, description="Health check interval in seconds"
    )

    response_timeout: int = Field(
        default=5, ge=1, le=30, description="Timeout for health check responses in seconds"
    )

    # Chromium optimization flags
    custom_flags: list[str] = Field(
        default_factory=list, description="Additional Chromium command line flags"
    )

    disable_extensions: bool = Field(default=True, description="Disable all Chromium extensions")

    disable_plugins: bool = Field(default=True, description="Disable browser plugins")

    @model_validator(mode="after")
    def validate_timeout_consistency(self) -> "KioskBrowserSettings":
        """Validate timeout consistency and memory threshold ordering.

        Returns:
            The validated KioskBrowserSettings instance

        Raises:
            SettingsValidationError: If timeouts or thresholds are inconsistent
        """
        # Validate startup timeout > startup delay
        if self.startup_timeout <= self.startup_delay:
            raise SettingsValidationError(
                "Browser startup timeout must be greater than startup delay",
                field_name="startup_timeout",
                field_value=self.startup_timeout,
                validation_errors=[
                    f"startup_timeout ({self.startup_timeout}) <= startup_delay ({self.startup_delay})"
                ],
            )

        # Validate memory threshold ordering
        if self.memory_warning_threshold >= self.memory_critical_threshold:
            raise SettingsValidationError(
                "Memory warning threshold must be less than critical threshold",
                field_name="memory_warning_threshold",
                field_value=self.memory_warning_threshold,
                validation_errors=[
                    f"warning ({self.memory_warning_threshold}) >= critical ({self.memory_critical_threshold})"
                ],
            )

        return self

    @field_validator("custom_flags")
    @classmethod
    def validate_custom_flags(cls, v: list[str]) -> list[str]:
        """Validate custom Chromium flags.

        Args:
            v: List of custom flags

        Returns:
            The validated list of flags

        Raises:
            SettingsValidationError: If flags are invalid
        """
        if len(v) > 50:  # Reasonable limit
            raise SettingsValidationError(
                "Too many custom flags (maximum 50 allowed)",
                field_name="custom_flags",
                field_value=f"{len(v)} flags",
            )

        # Validate flag format (should start with --)
        for flag in v:
            if not flag.startswith("--"):
                logger.warning(f"Custom flag should start with '--': {flag}")

        return v


class KioskSystemSettings(BaseModel):
    """System integration and service configuration for kiosk deployment.

    Manages systemd service configuration, boot behavior, X11 setup,
    watchdog configuration, and remote access settings.

    Attributes:
        systemd_service_name: Name for systemd service
        service_user: User to run kiosk service as
        service_group: Group to run kiosk service as
        boot_delay: Delay after boot before starting kiosk
        wait_for_network: Wait for network connectivity before starting
        network_timeout: Maximum time to wait for network
        x11_display: X11 display to use
        auto_login: Enable automatic login for kiosk user
        disable_screen_blanking: Disable screen blanking/power saving
        enable_watchdog: Enable hardware watchdog for automatic recovery
        watchdog_timeout: Watchdog timeout in seconds
        auto_update: Enable automatic system updates
        update_schedule: Update schedule frequency
        backup_config: Automatically backup configuration files
        ssh_enabled: Enable SSH access for remote maintenance
        ssh_port: SSH port number
        vnc_enabled: Enable VNC for remote desktop access

    Example:
        >>> system = KioskSystemSettings(
        ...     systemd_service_name="calendarbot-kiosk",
        ...     service_user="pi",
        ...     enable_watchdog=True
        ... )
    """

    # Service management
    systemd_service_name: str = Field(
        default="calendarbot-kiosk", description="Name for systemd service"
    )

    service_user: str = Field(default="pi", description="User to run kiosk service as")

    service_group: str = Field(default="pi", description="Group to run kiosk service as")

    # Boot configuration
    boot_delay: int = Field(
        default=30, ge=0, le=120, description="Delay after boot before starting kiosk (seconds)"
    )

    wait_for_network: bool = Field(
        default=True, description="Wait for network connectivity before starting"
    )

    network_timeout: int = Field(
        default=120, ge=30, le=300, description="Maximum time to wait for network (seconds)"
    )

    # X11 configuration
    x11_display: str = Field(default=":0", description="X11 display to use")

    auto_login: bool = Field(default=True, description="Enable automatic login for kiosk user")

    disable_screen_blanking: bool = Field(
        default=True, description="Disable screen blanking/power saving"
    )

    # Watchdog configuration
    enable_watchdog: bool = Field(
        default=True, description="Enable hardware watchdog for automatic recovery"
    )

    watchdog_timeout: int = Field(
        default=60, ge=30, le=300, description="Watchdog timeout in seconds"
    )

    # Maintenance
    auto_update: bool = Field(default=False, description="Enable automatic system updates")

    update_schedule: str = Field(
        default="daily", description="Update schedule: daily, weekly, monthly"
    )

    backup_config: bool = Field(
        default=True, description="Automatically backup configuration files"
    )

    # Remote access
    ssh_enabled: bool = Field(default=True, description="Enable SSH access for remote maintenance")

    ssh_port: int = Field(default=22, ge=1, le=65535, description="SSH port number")

    vnc_enabled: bool = Field(default=False, description="Enable VNC for remote desktop access")

    @field_validator("update_schedule")
    @classmethod
    def validate_update_schedule(cls, v: str) -> str:
        """Validate update schedule setting.

        Args:
            v: The update schedule string to validate

        Returns:
            The validated schedule string

        Raises:
            SettingsValidationError: If schedule is invalid
        """
        valid_schedules = {"daily", "weekly", "monthly"}
        if v not in valid_schedules:
            raise SettingsValidationError(
                f"Invalid update schedule: {v}",
                field_name="update_schedule",
                field_value=v,
                validation_errors=[f"Must be one of: {', '.join(valid_schedules)}"],
            )
        return v

    @field_validator("x11_display")
    @classmethod
    def validate_x11_display(cls, v: str) -> str:
        """Validate X11 display format.

        Args:
            v: The X11 display string to validate

        Returns:
            The validated display string

        Raises:
            SettingsValidationError: If display format is invalid
        """
        if not v.startswith(":"):
            raise SettingsValidationError(
                f"X11 display must start with ':': {v}",
                field_name="x11_display",
                field_value=v,
                validation_errors=["Display format should be ':0', ':1', etc."],
            )
        return v


class KioskSecuritySettings(BaseModel):
    """Security and access control configuration for kiosk deployment.

    Defines security policies, access restrictions, and monitoring
    settings to ensure secure kiosk operation.

    Attributes:
        enable_security_logging: Enable security event logging
        failed_auth_lockout: Enable lockout after failed authentication
        max_failed_attempts: Maximum failed authentication attempts
        lockout_duration: Duration of lockout in seconds
        allowed_domains: List of allowed domains for web browsing
        block_external_access: Block access to external websites
        enable_content_filtering: Enable content filtering
        admin_password_hash: Hashed admin password for configuration access
        session_timeout: Session timeout for admin access
        audit_enabled: Enable security audit logging

    Example:
        >>> security = KioskSecuritySettings(
        ...     enable_security_logging=True,
        ...     max_failed_attempts=3,
        ...     block_external_access=True
        ... )
    """

    # Security logging
    enable_security_logging: bool = Field(default=True, description="Enable security event logging")

    # Authentication and access control
    failed_auth_lockout: bool = Field(
        default=True, description="Enable lockout after failed authentication"
    )

    max_failed_attempts: int = Field(
        default=5, ge=1, le=20, description="Maximum failed authentication attempts"
    )

    lockout_duration: int = Field(
        default=300, ge=60, le=3600, description="Duration of lockout in seconds"
    )

    # Web browsing restrictions
    allowed_domains: list[str] = Field(
        default_factory=list, description="List of allowed domains for web browsing"
    )

    block_external_access: bool = Field(
        default=False, description="Block access to external websites"
    )

    enable_content_filtering: bool = Field(default=False, description="Enable content filtering")

    # Admin access
    admin_password_hash: Optional[str] = Field(
        default=None, description="Hashed admin password for configuration access"
    )

    session_timeout: int = Field(
        default=1800, ge=300, le=7200, description="Session timeout for admin access"
    )

    # Audit and monitoring
    audit_enabled: bool = Field(default=True, description="Enable security audit logging")

    @field_validator("allowed_domains")
    @classmethod
    def validate_allowed_domains(cls, v: list[str]) -> list[str]:
        """Validate allowed domains list.

        Args:
            v: List of domain strings

        Returns:
            The validated list of domains

        Raises:
            SettingsValidationError: If domains are invalid
        """
        import re  # noqa: PLC0415

        domain_pattern = re.compile(
            r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
        )

        for domain in v:
            if not domain_pattern.match(domain):
                raise SettingsValidationError(
                    f"Invalid domain format: {domain}",
                    field_name="allowed_domains",
                    field_value=domain,
                    validation_errors=["Domain must be in valid format (e.g., example.com)"],
                )

        return v


class KioskMonitoringSettings(BaseModel):
    """Health monitoring and alerting configuration for kiosk deployment.

    Provides comprehensive system health monitoring, resource tracking,
    error detection, and alerting capabilities for remote kiosk management.

    Attributes:
        enabled: Enable health monitoring
        health_check_interval: Overall health check interval in seconds
        memory_check_interval: Memory usage check interval in seconds
        memory_threshold_mb: System memory usage threshold for warnings
        cpu_threshold_percent: CPU usage threshold for warnings
        disk_threshold_percent: Disk usage threshold for warnings
        temperature_threshold_celsius: CPU temperature threshold for warnings
        max_error_history: Maximum number of errors to keep in history
        error_rate_threshold: Error rate threshold for alerts
        remote_monitoring_enabled: Enable remote monitoring API
        remote_monitoring_port: Port for remote monitoring API
        remote_monitoring_auth: Authentication token for remote monitoring
        alert_methods: Alert methods list
        webhook_url: Webhook URL for alerts
        email_config: Email configuration for alerts

    Example:
        >>> monitoring = KioskMonitoringSettings(
        ...     enabled=True,
        ...     memory_threshold_mb=400,
        ...     remote_monitoring_enabled=True
        ... )
    """

    # Health monitoring
    enabled: bool = Field(default=True, description="Enable health monitoring")

    health_check_interval: int = Field(
        default=30, ge=5, le=300, description="Overall health check interval in seconds"
    )

    memory_check_interval: int = Field(
        default=60, ge=10, le=600, description="Memory usage check interval in seconds"
    )

    # System resource monitoring
    memory_threshold_mb: int = Field(
        default=400, ge=200, le=500, description="System memory usage threshold for warnings (MB)"
    )

    cpu_threshold_percent: float = Field(
        default=80.0, ge=50.0, le=95.0, description="CPU usage threshold for warnings (%)"
    )

    disk_threshold_percent: float = Field(
        default=85.0, ge=50.0, le=95.0, description="Disk usage threshold for warnings (%)"
    )

    temperature_threshold_celsius: float = Field(
        default=75.0, ge=60.0, le=85.0, description="CPU temperature threshold for warnings (°C)"
    )

    # Error tracking
    max_error_history: int = Field(
        default=100, ge=10, le=1000, description="Maximum number of errors to keep in history"
    )

    error_rate_threshold: float = Field(
        default=0.1,
        ge=0.01,
        le=1.0,
        description="Error rate threshold for alerts (errors per minute)",
    )

    # Remote monitoring
    remote_monitoring_enabled: bool = Field(
        default=False, description="Enable remote monitoring API"
    )

    remote_monitoring_port: int = Field(
        default=8081, ge=1024, le=65535, description="Port for remote monitoring API"
    )

    remote_monitoring_auth: Optional[str] = Field(
        default=None, description="Authentication token for remote monitoring"
    )

    # Alerting
    alert_methods: list[str] = Field(
        default_factory=lambda: ["log"], description="Alert methods: log, email, webhook, mqtt"
    )

    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for alerts")

    email_config: Optional[dict[str, str]] = Field(
        default=None, description="Email configuration for alerts"
    )

    @field_validator("alert_methods")
    @classmethod
    def validate_alert_methods(cls, v: list[str]) -> list[str]:
        """Validate alert methods list.

        Args:
            v: List of alert method strings

        Returns:
            The validated list of alert methods

        Raises:
            SettingsValidationError: If alert methods are invalid
        """
        valid_methods = {"log", "email", "webhook", "mqtt"}
        for method in v:
            if method not in valid_methods:
                raise SettingsValidationError(
                    f"Invalid alert method: {method}",
                    field_name="alert_methods",
                    field_value=method,
                    validation_errors=[f"Must be one of: {', '.join(valid_methods)}"],
                )
        return v


class KioskPiOptimizationSettings(BaseModel):
    """Raspberry Pi Zero 2W specific optimizations for kiosk deployment.

    Provides memory management, CPU optimization, thermal management,
    storage optimization, and network tuning specifically for Pi Zero 2W.

    Attributes:
        enable_memory_optimization: Enable Pi-specific memory optimizations
        swap_size_mb: Swap file size in MB (0 = disabled)
        memory_split_mb: GPU memory split in MB
        cpu_governor: CPU frequency governor
        cpu_max_freq_mhz: Maximum CPU frequency in MHz
        enable_thermal_throttling: Enable CPU thermal throttling
        thermal_soft_limit: Temperature for soft throttling
        thermal_hard_limit: Temperature for hard throttling
        enable_tmpfs_logs: Use tmpfs for log files to reduce SD card wear
        tmpfs_size_mb: Size of tmpfs for logs in MB
        log_rotation_size_mb: Log file size before rotation in MB
        enable_network_optimization: Enable network stack optimizations
        tcp_window_size_kb: TCP window size in KB

    Example:
        >>> pi_opts = KioskPiOptimizationSettings(
        ...     enable_memory_optimization=True,
        ...     swap_size_mb=256,
        ...     cpu_governor="performance"
        ... )
    """

    # Memory management
    enable_memory_optimization: bool = Field(
        default=True, description="Enable Pi-specific memory optimizations"
    )

    swap_size_mb: int = Field(
        default=512, ge=0, le=2048, description="Swap file size in MB (0 = disabled)"
    )

    memory_split_mb: int = Field(default=64, ge=16, le=128, description="GPU memory split in MB")

    # CPU optimization
    cpu_governor: str = Field(
        default="performance",
        description="CPU frequency governor: performance, powersave, ondemand",
    )

    cpu_max_freq_mhz: Optional[int] = Field(
        default=None, ge=600, le=1400, description="Maximum CPU frequency in MHz (None = default)"
    )

    # Thermal management
    enable_thermal_throttling: bool = Field(
        default=True, description="Enable CPU thermal throttling"
    )

    thermal_soft_limit: float = Field(
        default=70.0, ge=60.0, le=80.0, description="Temperature for soft throttling (°C)"
    )

    thermal_hard_limit: float = Field(
        default=80.0, ge=70.0, le=85.0, description="Temperature for hard throttling (°C)"
    )

    # Storage optimization
    enable_tmpfs_logs: bool = Field(
        default=True, description="Use tmpfs for log files to reduce SD card wear"
    )

    tmpfs_size_mb: int = Field(
        default=32, ge=16, le=256, description="Size of tmpfs for logs in MB"
    )

    log_rotation_size_mb: int = Field(
        default=10, ge=1, le=100, description="Log file size before rotation in MB"
    )

    # Network optimization
    enable_network_optimization: bool = Field(
        default=True, description="Enable network stack optimizations"
    )

    tcp_window_size_kb: int = Field(default=64, ge=32, le=256, description="TCP window size in KB")

    @field_validator("cpu_governor")
    @classmethod
    def validate_cpu_governor(cls, v: str) -> str:
        """Validate CPU governor setting.

        Args:
            v: The CPU governor string to validate

        Returns:
            The validated governor string

        Raises:
            SettingsValidationError: If governor is invalid
        """
        valid_governors = {"performance", "powersave", "ondemand", "conservative", "userspace"}
        if v not in valid_governors:
            raise SettingsValidationError(
                f"Invalid CPU governor: {v}",
                field_name="cpu_governor",
                field_value=v,
                validation_errors=[f"Must be one of: {', '.join(valid_governors)}"],
            )
        return v

    @model_validator(mode="after")
    def validate_thermal_limits(self) -> "KioskPiOptimizationSettings":
        """Validate thermal limit consistency.

        Returns:
            The validated KioskPiOptimizationSettings instance

        Raises:
            SettingsValidationError: If thermal limits are inconsistent
        """
        if self.thermal_soft_limit >= self.thermal_hard_limit:
            raise SettingsValidationError(
                "Thermal soft limit must be less than hard limit",
                field_name="thermal_soft_limit",
                field_value=self.thermal_soft_limit,
                validation_errors=[
                    f"soft ({self.thermal_soft_limit}) >= hard ({self.thermal_hard_limit})"
                ],
            )

        return self


class KioskSettings(BaseModel):
    """Main kiosk mode configuration container optimized for Pi Zero 2W deployment.

    Provides comprehensive configuration for Pi Zero 2W kiosk deployment
    including browser management, display optimization, monitoring, and
    system integration with Pi Zero 2W specific constraints.

    Attributes:
        enabled: Enable kiosk mode functionality
        auto_start: Automatically start kiosk mode on system boot
        target_layout: CalendarBot layout to display in kiosk mode
        browser: Browser process management configuration
        display: Display and UI configuration for 480x800 screen
        monitoring: Health monitoring and alerting configuration
        pi_optimization: Raspberry Pi Zero 2W specific optimizations
        system: System integration and service configuration
        security: Security and access control configuration
        debug_mode: Enable debug logging and development features
        config_version: Configuration schema version for migration support

    Example:
        >>> kiosk = KioskSettings(
        ...     enabled=True,
        ...     target_layout="whats-next-view",
        ...     browser=KioskBrowserSettings(memory_limit_mb=128),
        ...     display=KioskDisplaySettings(width=480, height=800)
        ... )
    """

    # Core kiosk settings
    enabled: bool = Field(default=False, description="Enable kiosk mode functionality")

    auto_start: bool = Field(
        default=True, description="Automatically start kiosk mode on system boot"
    )

    target_layout: str = Field(
        default="whats-next-view", description="CalendarBot layout to display in kiosk mode"
    )

    # Component configurations
    browser: KioskBrowserSettings = Field(
        default_factory=KioskBrowserSettings, description="Browser process management configuration"
    )

    display: KioskDisplaySettings = Field(
        default_factory=KioskDisplaySettings,
        description="Display and UI configuration for 480x800 screen",
    )

    monitoring: KioskMonitoringSettings = Field(
        default_factory=KioskMonitoringSettings,
        description="Health monitoring and alerting configuration",
    )

    pi_optimization: KioskPiOptimizationSettings = Field(
        default_factory=KioskPiOptimizationSettings,
        description="Raspberry Pi Zero 2W specific optimizations",
    )

    system: KioskSystemSettings = Field(
        default_factory=KioskSystemSettings,
        description="System integration and service configuration",
    )

    security: KioskSecuritySettings = Field(
        default_factory=KioskSecuritySettings,
        description="Security and access control configuration",
    )

    # Advanced settings
    debug_mode: bool = Field(
        default=False, description="Enable debug logging and development features"
    )

    config_version: str = Field(
        default="1.0", description="Configuration schema version for migration support"
    )

    @model_validator(mode="after")
    def validate_pi_zero_2w_constraints(self) -> "KioskSettings":
        """Validate Pi Zero 2W memory and resource constraints.

        Returns:
            The validated KioskSettings instance

        Raises:
            SettingsValidationError: If configuration exceeds Pi Zero 2W limits
        """
        if not self.enabled:
            return self

        # Validate total memory allocation doesn't exceed Pi Zero 2W limits (512MB)
        total_memory = (
            self.browser.memory_limit_mb
            + 100  # Estimated CalendarBot memory
            + 200  # System memory reserve
        )

        # Add Pi optimization memory usage
        if self.pi_optimization.enable_tmpfs_logs:
            total_memory += self.pi_optimization.tmpfs_size_mb

        if total_memory > 450:  # Conservative limit for 512MB Pi
            raise SettingsValidationError(
                f"Total memory allocation ({total_memory}MB) exceeds Pi Zero 2W safe limits (450MB)",
                field_name="memory_allocation",
                field_value=total_memory,
                validation_errors=[
                    f"Browser: {self.browser.memory_limit_mb}MB",
                    "CalendarBot: ~100MB",
                    "System: ~200MB",
                    f"tmpfs: {self.pi_optimization.tmpfs_size_mb if self.pi_optimization.enable_tmpfs_logs else 0}MB",
                ],
            )

        # Validate display dimensions are reasonable for Pi Zero 2W
        display_pixels = self.display.width * self.display.height
        if display_pixels > 1920 * 1080:  # Full HD limit
            raise SettingsValidationError(
                f"Display resolution ({self.display.width}x{self.display.height}) may be too high for Pi Zero 2W",
                field_name="display_resolution",
                field_value=f"{self.display.width}x{self.display.height}",
                validation_errors=["Consider using 480x800 or similar resolution"],
            )

        # Validate GPU memory split is reasonable for Pi Zero 2W
        if self.pi_optimization.memory_split_mb > 128:
            raise SettingsValidationError(
                f"GPU memory split ({self.pi_optimization.memory_split_mb}MB) too large for Pi Zero 2W",
                field_name="pi_optimization.memory_split_mb",
                field_value=self.pi_optimization.memory_split_mb,
                validation_errors=["Pi Zero 2W should use 64MB or less for GPU"],
            )

        return self

    @field_validator("target_layout")
    @classmethod
    def validate_target_layout(cls, v: str) -> str:
        """Validate target layout name.

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
                "Target layout cannot be empty", field_name="target_layout", field_value=v
            )
        return v.strip()

    def get_total_memory_usage_mb(self) -> int:
        """Calculate total estimated memory usage in MB.

        Returns:
            Total estimated memory usage in MB
        """
        total = self.browser.memory_limit_mb + 100 + 200  # Browser + CalendarBot + System

        if self.pi_optimization.enable_tmpfs_logs:
            total += self.pi_optimization.tmpfs_size_mb

        return total

    def is_memory_usage_safe(self) -> bool:
        """Check if memory usage is within safe Pi Zero 2W limits.

        Returns:
            True if memory usage is safe, False otherwise
        """
        return self.get_total_memory_usage_mb() <= 450

    def get_memory_usage_breakdown(self) -> dict[str, int]:
        """Get detailed memory usage breakdown.

        Returns:
            Dictionary with memory usage breakdown by component
        """
        breakdown = {
            "browser": self.browser.memory_limit_mb,
            "calendarbot": 100,
            "system": 200,
            "tmpfs": self.pi_optimization.tmpfs_size_mb
            if self.pi_optimization.enable_tmpfs_logs
            else 0,
        }
        breakdown["total"] = sum(breakdown.values())
        return breakdown
