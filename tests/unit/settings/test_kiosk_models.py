"""Unit tests for kiosk settings data models."""

import pytest
from pydantic import ValidationError

from calendarbot.settings.exceptions import SettingsValidationError

# Try importing kiosk models
try:
    from calendarbot.settings.kiosk_models import (
        KioskBrowserSettings,
        KioskDisplaySettings,
        KioskMonitoringSettings,
        KioskPiOptimizationSettings,
        KioskSecuritySettings,
        KioskSettings,
        KioskSystemSettings,
    )

    KIOSK_MODELS_AVAILABLE = True
except ImportError:
    KIOSK_MODELS_AVAILABLE = False


@pytest.mark.skipif(not KIOSK_MODELS_AVAILABLE, reason="Kiosk models not available")
class TestKioskDisplaySettings:
    """Test KioskDisplaySettings model validation and functionality."""

    def test_kiosk_display_settings_when_valid_data_then_creates_successfully(
        self, sample_kiosk_display_settings: "KioskDisplaySettings"
    ) -> None:
        """Test KioskDisplaySettings creation with valid data."""
        display = sample_kiosk_display_settings

        assert display.width == 480
        assert display.height == 800
        assert display.orientation == "portrait"
        assert display.scale_factor == 1.0
        assert display.touch_enabled is True
        assert display.brightness == 80
        assert display.hide_cursor is True
        assert display.fullscreen_mode is True

    def test_kiosk_display_settings_when_invalid_orientation_then_raises_validation_error(
        self,
    ) -> None:
        """Test KioskDisplaySettings validation fails with invalid orientation."""
        with pytest.raises(SettingsValidationError) as exc_info:
            KioskDisplaySettings(orientation="invalid")

        assert "Invalid display orientation" in str(exc_info.value)

    def test_kiosk_display_settings_when_invalid_dimensions_then_raises_validation_error(
        self,
    ) -> None:
        """Test KioskDisplaySettings validation fails with invalid dimensions."""
        with pytest.raises(ValidationError):
            KioskDisplaySettings(width=100)  # Below minimum

        with pytest.raises(ValidationError):
            KioskDisplaySettings(height=100)  # Below minimum

    def test_kiosk_display_settings_when_invalid_touch_calibration_then_raises_validation_error(
        self,
    ) -> None:
        """Test KioskDisplaySettings validation fails with invalid touch calibration."""
        with pytest.raises(SettingsValidationError) as exc_info:
            KioskDisplaySettings(
                touch_calibration={"offset_x": 0, "offset_y": 0}  # Missing required keys
            )

        assert "Touch calibration missing required keys" in str(exc_info.value)

        with pytest.raises(SettingsValidationError):
            KioskDisplaySettings(
                touch_calibration={
                    "offset_x": 0,
                    "offset_y": 0,
                    "scale_x": -1.0,
                    "scale_y": 1.0,  # Negative scale
                }
            )

    def test_kiosk_display_settings_when_valid_touch_calibration_then_creates_successfully(
        self,
    ) -> None:
        """Test KioskDisplaySettings creation with valid touch calibration."""
        display = KioskDisplaySettings(
            touch_calibration={"offset_x": 10.0, "offset_y": 20.0, "scale_x": 1.1, "scale_y": 0.9}
        )

        assert display.touch_calibration is not None
        assert display.touch_calibration["scale_x"] == 1.1


@pytest.mark.skipif(not KIOSK_MODELS_AVAILABLE, reason="Kiosk models not available")
class TestKioskBrowserSettings:
    """Test KioskBrowserSettings model validation and functionality."""

    def test_kiosk_browser_settings_when_valid_data_then_creates_successfully(
        self, sample_kiosk_browser_settings: "KioskBrowserSettings"
    ) -> None:
        """Test KioskBrowserSettings creation with valid data."""
        browser = sample_kiosk_browser_settings

        assert browser.executable_path == "chromium-browser"
        assert browser.startup_delay == 5
        assert browser.memory_limit_mb == 80
        assert browser.max_restart_attempts == 3
        assert browser.cache_clear_on_restart is True

    def test_kiosk_browser_settings_when_timeout_inconsistency_then_raises_validation_error(
        self,
    ) -> None:
        """Test KioskBrowserSettings validation fails with inconsistent timeouts."""
        with pytest.raises(SettingsValidationError) as exc_info:
            KioskBrowserSettings(startup_delay=30, startup_timeout=20)  # timeout < delay

        assert "startup timeout must be greater than startup delay" in str(exc_info.value)

    def test_kiosk_browser_settings_when_memory_threshold_inconsistency_then_raises_validation_error(
        self,
    ) -> None:
        """Test KioskBrowserSettings validation fails with inconsistent memory thresholds."""
        with pytest.raises(SettingsValidationError) as exc_info:
            KioskBrowserSettings(
                memory_warning_threshold=0.95,
                memory_critical_threshold=0.85,  # critical < warning
            )

        assert "Memory warning threshold must be less than critical threshold" in str(
            exc_info.value
        )

    def test_kiosk_browser_settings_when_too_many_custom_flags_then_raises_validation_error(
        self,
    ) -> None:
        """Test KioskBrowserSettings validation fails with too many custom flags."""
        with pytest.raises(SettingsValidationError) as exc_info:
            KioskBrowserSettings(custom_flags=[f"--flag{i}" for i in range(51)])  # > 50 flags

        assert "Too many custom flags" in str(exc_info.value)

    def test_kiosk_browser_settings_when_valid_custom_flags_then_creates_successfully(self) -> None:
        """Test KioskBrowserSettings creation with valid custom flags."""
        browser = KioskBrowserSettings(
            custom_flags=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
        )

        assert len(browser.custom_flags) == 3
        assert "--disable-gpu" in browser.custom_flags


@pytest.mark.skipif(not KIOSK_MODELS_AVAILABLE, reason="Kiosk models not available")
class TestKioskSystemSettings:
    """Test KioskSystemSettings model validation and functionality."""

    def test_kiosk_system_settings_when_valid_data_then_creates_successfully(
        self, sample_kiosk_system_settings: "KioskSystemSettings"
    ) -> None:
        """Test KioskSystemSettings creation with valid data."""
        system = sample_kiosk_system_settings

        assert system.systemd_service_name == "calendarbot-kiosk"
        assert system.service_user == "pi"
        assert system.boot_delay == 30
        assert system.enable_watchdog is True
        assert system.ssh_enabled is True

    def test_kiosk_system_settings_when_invalid_update_schedule_then_raises_validation_error(
        self,
    ) -> None:
        """Test KioskSystemSettings validation fails with invalid update schedule."""
        with pytest.raises(SettingsValidationError) as exc_info:
            KioskSystemSettings(update_schedule="invalid")

        assert "Invalid update schedule" in str(exc_info.value)

    def test_kiosk_system_settings_when_invalid_x11_display_then_raises_validation_error(
        self,
    ) -> None:
        """Test KioskSystemSettings validation fails with invalid X11 display."""
        with pytest.raises(SettingsValidationError) as exc_info:
            KioskSystemSettings(x11_display="invalid")

        assert "X11 display must start with ':'" in str(exc_info.value)

    def test_kiosk_system_settings_when_valid_update_schedules_then_creates_successfully(
        self,
    ) -> None:
        """Test KioskSystemSettings creation with valid update schedules."""
        for schedule in ["daily", "weekly", "monthly"]:
            system = KioskSystemSettings(update_schedule=schedule)
            assert system.update_schedule == schedule


@pytest.mark.skipif(not KIOSK_MODELS_AVAILABLE, reason="Kiosk models not available")
class TestKioskSecuritySettings:
    """Test KioskSecuritySettings model validation and functionality."""

    def test_kiosk_security_settings_when_valid_data_then_creates_successfully(
        self, sample_kiosk_security_settings: "KioskSecuritySettings"
    ) -> None:
        """Test KioskSecuritySettings creation with valid data."""
        security = sample_kiosk_security_settings

        assert security.enable_security_logging is True
        assert security.failed_auth_lockout is True
        assert security.max_failed_attempts == 3
        assert security.lockout_duration == 300
        assert security.audit_enabled is True

    def test_kiosk_security_settings_when_invalid_domains_then_raises_validation_error(
        self,
    ) -> None:
        """Test KioskSecuritySettings validation fails with invalid domains."""
        with pytest.raises(SettingsValidationError) as exc_info:
            KioskSecuritySettings(allowed_domains=["invalid..domain", "valid.com"])

        assert "Invalid domain format" in str(exc_info.value)

    def test_kiosk_security_settings_when_valid_domains_then_creates_successfully(self) -> None:
        """Test KioskSecuritySettings creation with valid domains."""
        security = KioskSecuritySettings(
            allowed_domains=["example.com", "subdomain.example.org", "localhost"]
        )

        assert len(security.allowed_domains) == 3
        assert "example.com" in security.allowed_domains


@pytest.mark.skipif(not KIOSK_MODELS_AVAILABLE, reason="Kiosk models not available")
class TestKioskMonitoringSettings:
    """Test KioskMonitoringSettings model validation and functionality."""

    def test_kiosk_monitoring_settings_when_valid_data_then_creates_successfully(
        self, sample_kiosk_monitoring_settings: "KioskMonitoringSettings"
    ) -> None:
        """Test KioskMonitoringSettings creation with valid data."""
        monitoring = sample_kiosk_monitoring_settings

        assert monitoring.enabled is True
        assert monitoring.health_check_interval == 30
        assert monitoring.memory_threshold_mb == 400
        assert monitoring.cpu_threshold_percent == 80.0
        assert monitoring.remote_monitoring_enabled is False

    def test_kiosk_monitoring_settings_when_invalid_alert_methods_then_raises_validation_error(
        self,
    ) -> None:
        """Test KioskMonitoringSettings validation fails with invalid alert methods."""
        with pytest.raises(SettingsValidationError) as exc_info:
            KioskMonitoringSettings(alert_methods=["log", "invalid", "email"])

        assert "Invalid alert method" in str(exc_info.value)

    def test_kiosk_monitoring_settings_when_valid_alert_methods_then_creates_successfully(
        self,
    ) -> None:
        """Test KioskMonitoringSettings creation with valid alert methods."""
        monitoring = KioskMonitoringSettings(alert_methods=["log", "email", "webhook", "mqtt"])

        assert len(monitoring.alert_methods) == 4
        assert "webhook" in monitoring.alert_methods


@pytest.mark.skipif(not KIOSK_MODELS_AVAILABLE, reason="Kiosk models not available")
class TestKioskPiOptimizationSettings:
    """Test KioskPiOptimizationSettings model validation and functionality."""

    def test_kiosk_pi_optimization_settings_when_valid_data_then_creates_successfully(
        self, sample_kiosk_pi_optimization_settings: "KioskPiOptimizationSettings"
    ) -> None:
        """Test KioskPiOptimizationSettings creation with valid data."""
        pi_opts = sample_kiosk_pi_optimization_settings

        assert pi_opts.enable_memory_optimization is True
        assert pi_opts.swap_size_mb == 256
        assert pi_opts.memory_split_mb == 64
        assert pi_opts.cpu_governor == "performance"
        assert pi_opts.enable_tmpfs_logs is True

    def test_kiosk_pi_optimization_settings_when_invalid_cpu_governor_then_raises_validation_error(
        self,
    ) -> None:
        """Test KioskPiOptimizationSettings validation fails with invalid CPU governor."""
        with pytest.raises(SettingsValidationError) as exc_info:
            KioskPiOptimizationSettings(cpu_governor="invalid")

        assert "Invalid CPU governor" in str(exc_info.value)

    def test_kiosk_pi_optimization_settings_when_thermal_limit_inconsistency_then_raises_validation_error(
        self,
    ) -> None:
        """Test KioskPiOptimizationSettings validation fails with inconsistent thermal limits."""
        with pytest.raises(SettingsValidationError) as exc_info:
            KioskPiOptimizationSettings(
                thermal_soft_limit=80.0,
                thermal_hard_limit=70.0,  # hard < soft
            )

        assert "Thermal soft limit must be less than hard limit" in str(exc_info.value)

    def test_kiosk_pi_optimization_settings_when_valid_cpu_governors_then_creates_successfully(
        self,
    ) -> None:
        """Test KioskPiOptimizationSettings creation with valid CPU governors."""
        for governor in ["performance", "powersave", "ondemand", "conservative", "userspace"]:
            pi_opts = KioskPiOptimizationSettings(cpu_governor=governor)
            assert pi_opts.cpu_governor == governor


@pytest.mark.skipif(not KIOSK_MODELS_AVAILABLE, reason="Kiosk models not available")
class TestKioskSettings:
    """Test KioskSettings main container model validation and functionality."""

    def test_kiosk_settings_when_valid_data_then_creates_successfully(
        self, sample_kiosk_settings: "KioskSettings"
    ) -> None:
        """Test KioskSettings creation with valid data."""
        kiosk = sample_kiosk_settings

        assert kiosk.enabled is True
        assert kiosk.auto_start is True
        assert kiosk.target_layout == "whats-next-view"
        assert kiosk.debug_mode is False
        assert kiosk.config_version == "1.0"

        # Check nested settings
        assert isinstance(kiosk.browser, KioskBrowserSettings)
        assert isinstance(kiosk.display, KioskDisplaySettings)
        assert isinstance(kiosk.monitoring, KioskMonitoringSettings)
        assert isinstance(kiosk.pi_optimization, KioskPiOptimizationSettings)
        assert isinstance(kiosk.system, KioskSystemSettings)
        assert isinstance(kiosk.security, KioskSecuritySettings)

    def test_kiosk_settings_when_disabled_then_skips_validation(self) -> None:
        """Test KioskSettings skips Pi Zero 2W validation when disabled."""
        # This should not raise validation errors even with high memory (within Pydantic limits)
        kiosk = KioskSettings(
            enabled=False,
            browser=KioskBrowserSettings(memory_limit_mb=200),  # High but within Pydantic limits
        )

        assert kiosk.enabled is False
        assert kiosk.browser.memory_limit_mb == 200

    def test_kiosk_settings_when_pi_memory_exceeded_then_raises_validation_error(self) -> None:
        """Test KioskSettings validation fails when Pi Zero 2W memory limits exceeded."""
        with pytest.raises(SettingsValidationError) as exc_info:
            KioskSettings(
                enabled=True,
                browser=KioskBrowserSettings(memory_limit_mb=200),  # Within individual limits
                pi_optimization=KioskPiOptimizationSettings(
                    tmpfs_size_mb=80
                ),  # But combined exceeds Pi Zero 2W
            )

        assert "exceeds Pi Zero 2W safe limits" in str(exc_info.value)

    def test_kiosk_settings_when_excessive_display_resolution_then_raises_validation_error(
        self,
    ) -> None:
        """Test KioskSettings validation succeeds with high resolution (no specific resolution limits)."""
        # High resolution displays are allowed but may impact performance
        kiosk = KioskSettings(
            enabled=True,
            display=KioskDisplaySettings(width=1920, height=1080),  # High resolution
        )

        assert kiosk.display.width == 1920
        assert kiosk.display.height == 1080

    def test_kiosk_settings_when_excessive_gpu_memory_then_raises_validation_error(self) -> None:
        """Test KioskSettings validation fails with excessive GPU memory split."""
        with pytest.raises(ValidationError) as exc_info:
            KioskSettings(
                enabled=True,
                pi_optimization=KioskPiOptimizationSettings(
                    memory_split_mb=200
                ),  # Exceeds Pydantic limit of 128MB
            )

        assert "memory_split_mb" in str(exc_info.value).lower()

    def test_kiosk_settings_when_empty_target_layout_then_raises_validation_error(self) -> None:
        """Test KioskSettings validation fails with empty target layout."""
        with pytest.raises(SettingsValidationError) as exc_info:
            KioskSettings(target_layout="   ")  # Empty/whitespace

        assert "Target layout cannot be empty" in str(exc_info.value)

    def test_kiosk_settings_memory_usage_methods_when_called_then_returns_correct_values(
        self, sample_kiosk_settings: "KioskSettings"
    ) -> None:
        """Test KioskSettings memory usage utility methods."""
        kiosk = sample_kiosk_settings

        # Test total memory calculation
        total_memory = kiosk.get_total_memory_usage_mb()
        assert total_memory > 0
        assert isinstance(total_memory, int)

        # Test memory safety check
        is_safe = kiosk.is_memory_usage_safe()
        assert isinstance(is_safe, bool)

        # Test memory breakdown
        breakdown = kiosk.get_memory_usage_breakdown()
        assert isinstance(breakdown, dict)
        assert "browser" in breakdown
        assert "calendarbot" in breakdown
        assert "system" in breakdown
        assert "tmpfs" in breakdown
        assert "total" in breakdown
        assert breakdown["total"] == sum(v for k, v in breakdown.items() if k != "total")

    def test_kiosk_settings_when_optimized_for_pi_zero_2w_then_memory_usage_safe(self) -> None:
        """Test KioskSettings with Pi Zero 2W optimized configuration."""
        # Create a configuration optimized for Pi Zero 2W
        kiosk = KioskSettings(
            enabled=True,
            browser=KioskBrowserSettings(memory_limit_mb=100),  # Conservative
            pi_optimization=KioskPiOptimizationSettings(
                swap_size_mb=256,  # Smaller swap
                memory_split_mb=64,  # Standard GPU split
                enable_tmpfs_logs=True,
                tmpfs_size_mb=32,  # Smaller tmpfs
            ),
            display=KioskDisplaySettings(width=480, height=800),  # Standard kiosk resolution
        )

        assert kiosk.is_memory_usage_safe()
        assert kiosk.get_total_memory_usage_mb() <= 450

    def test_kiosk_settings_when_defaults_then_creates_valid_configuration(self) -> None:
        """Test KioskSettings default configuration is valid for Pi Zero 2W."""
        kiosk = KioskSettings(enabled=True)  # Use defaults

        # Should not raise validation errors
        assert kiosk.enabled is True
        assert kiosk.is_memory_usage_safe()  # Defaults should be safe
        assert kiosk.get_total_memory_usage_mb() <= 450


@pytest.mark.skipif(not KIOSK_MODELS_AVAILABLE, reason="Kiosk models not available")
class TestKioskSettingsIntegration:
    """Test KioskSettings integration scenarios."""

    def test_kiosk_settings_when_serialized_and_deserialized_then_maintains_consistency(
        self, sample_kiosk_settings: "KioskSettings"
    ) -> None:
        """Test KioskSettings serialization and deserialization consistency."""
        kiosk = sample_kiosk_settings

        # Serialize to dict
        kiosk_dict = kiosk.dict()
        assert isinstance(kiosk_dict, dict)
        assert "enabled" in kiosk_dict
        assert "browser" in kiosk_dict
        assert "display" in kiosk_dict

        # Deserialize from dict
        kiosk_restored = KioskSettings(**kiosk_dict)

        # Check consistency
        assert kiosk_restored.enabled == kiosk.enabled
        assert kiosk_restored.target_layout == kiosk.target_layout
        assert kiosk_restored.browser.memory_limit_mb == kiosk.browser.memory_limit_mb
        assert kiosk_restored.display.width == kiosk.display.width

    def test_kiosk_settings_when_partial_updates_then_validates_correctly(self) -> None:
        """Test KioskSettings partial updates maintain validation."""
        # Start with defaults
        kiosk = KioskSettings(enabled=True)

        # Update browser settings
        kiosk.browser.memory_limit_mb = 90
        assert kiosk.is_memory_usage_safe()

        # Update that would exceed limits
        kiosk.browser.memory_limit_mb = 300
        assert not kiosk.is_memory_usage_safe()

    def test_kiosk_settings_when_production_configuration_then_validates_successfully(self) -> None:
        """Test realistic production configuration for Pi Zero 2W kiosk."""
        production_kiosk = KioskSettings(
            enabled=True,
            auto_start=True,
            target_layout="whats-next-view",
            browser=KioskBrowserSettings(
                executable_path="chromium-browser",
                startup_delay=10,  # Allow system to stabilize
                memory_limit_mb=90,  # Conservative for Pi Zero 2W
                max_restart_attempts=3,
                cache_clear_on_restart=True,
                disable_extensions=True,
                disable_plugins=True,
            ),
            display=KioskDisplaySettings(
                width=480,
                height=800,
                orientation="portrait",
                brightness=70,  # Save power
                hide_cursor=True,
                fullscreen_mode=True,
            ),
            monitoring=KioskMonitoringSettings(
                enabled=True,
                health_check_interval=60,  # Less frequent on Pi Zero 2W
                memory_threshold_mb=350,  # Conservative threshold
                remote_monitoring_enabled=True,
                alert_methods=["log", "webhook"],
            ),
            pi_optimization=KioskPiOptimizationSettings(
                enable_memory_optimization=True,
                swap_size_mb=256,  # Balanced for SD card wear
                memory_split_mb=64,
                cpu_governor="ondemand",  # Balance performance and power
                enable_tmpfs_logs=True,
                tmpfs_size_mb=32,
                enable_thermal_throttling=True,
            ),
            system=KioskSystemSettings(
                systemd_service_name="calendarbot-kiosk",
                service_user="pi",
                boot_delay=45,  # Extra time for Pi Zero 2W
                wait_for_network=True,
                enable_watchdog=True,
                ssh_enabled=True,
            ),
            security=KioskSecuritySettings(
                enable_security_logging=True,
                failed_auth_lockout=True,
                max_failed_attempts=3,
                audit_enabled=True,
            ),
        )

        # Should validate successfully
        assert production_kiosk.enabled is True
        assert production_kiosk.is_memory_usage_safe()
        assert production_kiosk.get_total_memory_usage_mb() <= 450

        # Check all components are properly configured
        assert production_kiosk.browser.memory_limit_mb == 90
        assert production_kiosk.display.width == 480
        assert production_kiosk.monitoring.enabled is True
        assert production_kiosk.pi_optimization.cpu_governor == "ondemand"
        assert production_kiosk.system.enable_watchdog is True
        assert production_kiosk.security.audit_enabled is True
