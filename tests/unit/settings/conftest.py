"""Shared test fixtures for settings tests."""

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from unittest.mock import Mock, patch

import pytest

from calendarbot.settings.models import (
    ConflictResolutionSettings,
    DisplaySettings,
    EventFilterSettings,
    FilterPattern,
    SettingsData,
    SettingsMetadata,
)
from calendarbot.settings.persistence import SettingsPersistence
from calendarbot.settings.service import SettingsService

# Try importing kiosk models for fixtures
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


@pytest.fixture
def temp_config_dir() -> Path:
    """Create a temporary configuration directory for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_filter_pattern() -> FilterPattern:
    """Create a sample filter pattern for testing."""
    return FilterPattern(
        pattern="Daily Standup",
        is_regex=False,
        is_active=True,
        case_sensitive=False,
        match_count=5,
        description="Hide standup meetings",
    )


@pytest.fixture
def sample_regex_filter_pattern() -> FilterPattern:
    """Create a sample regex filter pattern for testing."""
    return FilterPattern(
        pattern=r"Meeting \d+",
        is_regex=True,
        is_active=True,
        case_sensitive=False,
        match_count=3,
        description="Hide numbered meetings",
    )


@pytest.fixture
def sample_event_filter_settings(sample_filter_pattern: FilterPattern) -> EventFilterSettings:
    """Create sample event filter settings for testing."""
    return EventFilterSettings(
        hide_all_day_events=True,
        title_patterns=[sample_filter_pattern],
        event_categories={"personal": True, "work": False},
        recurring_filters={"daily": True, "weekly": False},
        attendee_count_filter={"min_count": 2, "max_count": 10},
    )


@pytest.fixture
def sample_conflict_resolution_settings() -> ConflictResolutionSettings:
    """Create sample conflict resolution settings for testing."""
    return ConflictResolutionSettings(
        priority_by_acceptance=True,
        priority_by_attendee_count=False,
        priority_by_organizer=True,
        show_multiple_conflicts=True,
        conflict_display_mode="primary",
    )


@pytest.fixture
def sample_display_settings() -> DisplaySettings:
    """Create sample display settings for testing."""
    return DisplaySettings(
        default_layout="whats-next-view",
        font_sizes={"headers": "large", "body": "medium"},
        display_density="normal",
        color_theme="default",
        animation_enabled=True,
    )


@pytest.fixture
def sample_settings_metadata() -> SettingsMetadata:
    """Create sample settings metadata for testing."""
    return SettingsMetadata(
        version="1.0.0",
        last_modified=datetime(2023, 7, 18, 12, 0, 0),
        last_modified_by="test_user",
        device_id="test_device",
    )


@pytest.fixture
def sample_settings_data(
    sample_event_filter_settings: EventFilterSettings,
    sample_conflict_resolution_settings: ConflictResolutionSettings,
    sample_display_settings: DisplaySettings,
    sample_settings_metadata: SettingsMetadata,
) -> SettingsData:
    """Create complete sample settings data for testing."""
    return SettingsData(
        event_filters=sample_event_filter_settings,
        conflict_resolution=sample_conflict_resolution_settings,
        display=sample_display_settings,
        metadata=sample_settings_metadata,
    )


@pytest.fixture
def mock_settings_persistence(temp_config_dir: Path) -> Mock:
    """Create a mock settings persistence instance."""
    mock = Mock(spec=SettingsPersistence)
    mock.config_dir = temp_config_dir
    mock.settings_file = temp_config_dir / "settings.json"
    mock.backup_dir = temp_config_dir / "settings_backups"
    mock.max_backups = 5
    return mock


@pytest.fixture
def mock_calendarbot_settings() -> Mock:
    """Create a mock CalendarBot settings object."""
    mock = Mock()
    mock.config_dir = Path("/tmp/test_config")
    return mock


@pytest.fixture
def settings_persistence(temp_config_dir: Path) -> SettingsPersistence:
    """Create a real settings persistence instance for testing."""
    return SettingsPersistence(temp_config_dir)


@pytest.fixture
def settings_service(temp_config_dir: Path, mock_calendarbot_settings: Mock) -> SettingsService:
    """Create a settings service instance for testing."""
    return SettingsService(
        calendarbot_settings=mock_calendarbot_settings, config_dir=temp_config_dir
    )


@pytest.fixture
def mock_settings_service() -> Mock:
    """Create a mock settings service for API testing."""
    mock = Mock(spec=SettingsService)
    return mock


@pytest.fixture
def invalid_regex_pattern_data() -> dict[str, Any]:
    """Create invalid regex pattern data for testing validation."""
    return {"pattern": "[unclosed", "is_regex": True, "is_active": True, "case_sensitive": False}


@pytest.fixture
def invalid_attendee_filter_data() -> dict[str, Any]:
    """Create invalid attendee filter data for testing validation."""
    return {"min_count": 10, "max_count": 5}  # max < min should fail validation


@pytest.fixture
def sample_json_settings_data() -> str:
    """Create JSON representation of settings for file operations testing."""
    return json.dumps(
        {
            "event_filters": {
                "hide_all_day_events": True,
                "title_patterns": [
                    {
                        "pattern": "Daily Standup",
                        "is_regex": False,
                        "is_active": True,
                        "case_sensitive": False,
                        "match_count": 5,
                        "description": "Hide standup meetings",
                    }
                ],
                "event_categories": {"personal": True, "work": False},
                "recurring_filters": {"daily": True, "weekly": False},
                "attendee_count_filter": {"min_count": 2, "max_count": 10},
            },
            "conflict_resolution": {
                "priority_by_acceptance": True,
                "priority_by_attendee_count": False,
                "priority_by_organizer": True,
                "show_multiple_conflicts": True,
                "conflict_display_mode": "primary",
            },
            "display": {
                "default_layout": "whats-next-view",
                "font_sizes": {"headers": "large", "body": "medium"},
                "display_density": "normal",
                "color_theme": "default",
                "animation_enabled": True,
            },
            "metadata": {
                "version": "1.0.0",
                "last_modified": "2023-07-18T12:00:00",
                "last_modified_by": "test_user",
                "device_id": "test_device",
            },
        },
        indent=2,
    )


@pytest.fixture
def corrupted_json_data() -> str:
    """Create corrupted JSON data for error testing."""
    return '{"event_filters": {"hide_all_day_events": true, "invalid": }'


@pytest.fixture
def empty_settings_file(temp_config_dir: Path) -> Path:
    """Create an empty settings file for testing."""
    settings_file = temp_config_dir / "settings.json"
    settings_file.touch()
    return settings_file


@pytest.fixture
def populated_settings_file(temp_config_dir: Path, sample_json_settings_data: str) -> Path:
    """Create a populated settings file for testing."""
    settings_file = temp_config_dir / "settings.json"
    settings_file.write_text(sample_json_settings_data, encoding="utf-8")
    return settings_file


@pytest.fixture
def mock_web_request_handler() -> Mock:
    """Create a mock web request handler for API testing."""
    mock = Mock()
    mock.command = "GET"
    mock.client_address = ("127.0.0.1", 12345)
    mock._send_json_response = Mock()
    mock.send_response = Mock()
    mock.send_header = Mock()
    mock.end_headers = Mock()
    mock.wfile = Mock()
    return mock


@pytest.fixture
def api_test_data() -> dict[str, Any]:
    """Create test data for API endpoint testing."""
    return {
        "event_filters": {
            "hide_all_day_events": False,
            "title_patterns": [
                {
                    "pattern": "Test Meeting",
                    "is_regex": False,
                    "is_active": True,
                    "case_sensitive": False,
                    "description": "Test pattern",
                }
            ],
        },
        "display": {"default_layout": "4x8", "display_density": "compact"},
    }


@pytest.fixture
def mock_path_operations():
    """Mock pathlib Path operations for testing file system failures."""
    with (
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("pathlib.Path.exists") as mock_exists,
        patch("pathlib.Path.is_file") as mock_is_file,
        patch("pathlib.Path.unlink") as mock_unlink,
    ):
        mock_exists.return_value = False
        mock_is_file.return_value = False

        yield {
            "mkdir": mock_mkdir,
            "exists": mock_exists,
            "is_file": mock_is_file,
            "unlink": mock_unlink,
        }


class MockCalendarBotSettings:
    """Mock CalendarBot settings class for testing."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self.config_dir = config_dir or Path("/tmp/test_config")
        self.web_host = "localhost"
        self.web_port = 8080
        self.web_layout = "4x8"
        self.auto_kill_existing = False


@pytest.fixture
def test_layout_registry() -> Mock:
    """Create a mock layout registry for testing."""
    mock = Mock()
    mock.get_available_layouts.return_value = ["3x4", "4x8", "whats-next-view"]
    mock.validate_layout.return_value = True
    return mock


# Test assertion helpers
def assert_settings_equal(actual: SettingsData, expected: SettingsData) -> None:
    """Assert that two SettingsData objects are equal, ignoring timestamps."""
    assert actual.event_filters.dict() == expected.event_filters.dict()
    assert actual.conflict_resolution.dict() == expected.conflict_resolution.dict()
    assert actual.display.dict() == expected.display.dict()
    # Only check metadata fields that should remain constant
    assert actual.metadata.version == expected.metadata.version
    assert actual.metadata.last_modified_by == expected.metadata.last_modified_by
    assert actual.metadata.device_id == expected.metadata.device_id


def assert_filter_pattern_equal(actual: FilterPattern, expected: FilterPattern) -> None:
    """Assert that two FilterPattern objects are equal."""
    assert actual.pattern == expected.pattern
    assert actual.is_regex == expected.is_regex
    assert actual.is_active == expected.is_active
    assert actual.case_sensitive == expected.case_sensitive
    assert actual.description == expected.description
    # Don't check match_count as it may change during operations


def create_test_backup_file(backup_dir: Path, timestamp: str, content: str) -> Path:
    """Create a test backup file with specified timestamp and content."""
    backup_file = backup_dir / f"settings_backup_{timestamp}.json"
    backup_file.write_text(content, encoding="utf-8")
    return backup_file


# Kiosk settings test fixtures
if KIOSK_MODELS_AVAILABLE:

    @pytest.fixture
    def sample_kiosk_display_settings() -> "KioskDisplaySettings":
        """Create sample kiosk display settings for testing."""
        return KioskDisplaySettings(
            width=480,
            height=800,
            orientation="portrait",
            scale_factor=1.0,
            touch_enabled=True,
            brightness=80,
            hide_cursor=True,
            fullscreen_mode=True,
        )

    @pytest.fixture
    def sample_kiosk_browser_settings() -> "KioskBrowserSettings":
        """Create sample kiosk browser settings for testing."""
        return KioskBrowserSettings(
            executable_path="chromium-browser",
            startup_delay=5,
            startup_timeout=30,
            memory_limit_mb=80,
            max_restart_attempts=3,
            cache_clear_on_restart=True,
            health_check_interval=30,
            disable_extensions=True,
            disable_plugins=True,
        )

    @pytest.fixture
    def sample_kiosk_monitoring_settings() -> "KioskMonitoringSettings":
        """Create sample kiosk monitoring settings for testing."""
        return KioskMonitoringSettings(
            enabled=True,
            health_check_interval=30,
            memory_threshold_mb=400,
            cpu_threshold_percent=80.0,
            remote_monitoring_enabled=False,
            alert_methods=["log"],
        )

    @pytest.fixture
    def sample_kiosk_pi_optimization_settings() -> "KioskPiOptimizationSettings":
        """Create sample kiosk Pi optimization settings for testing."""
        return KioskPiOptimizationSettings(
            enable_memory_optimization=True,
            swap_size_mb=256,
            memory_split_mb=64,
            cpu_governor="performance",
            enable_tmpfs_logs=True,
            tmpfs_size_mb=32,
        )

    @pytest.fixture
    def sample_kiosk_system_settings() -> "KioskSystemSettings":
        """Create sample kiosk system settings for testing."""
        return KioskSystemSettings(
            systemd_service_name="calendarbot-kiosk",
            service_user="pi",
            service_group="pi",
            boot_delay=30,
            enable_watchdog=True,
            ssh_enabled=True,
        )

    @pytest.fixture
    def sample_kiosk_security_settings() -> "KioskSecuritySettings":
        """Create sample kiosk security settings for testing."""
        return KioskSecuritySettings(
            enable_security_logging=True,
            failed_auth_lockout=True,
            max_failed_attempts=3,
            lockout_duration=300,
            audit_enabled=True,
        )

    @pytest.fixture
    def sample_kiosk_settings(
        sample_kiosk_display_settings: "KioskDisplaySettings",
        sample_kiosk_browser_settings: "KioskBrowserSettings",
        sample_kiosk_monitoring_settings: "KioskMonitoringSettings",
        sample_kiosk_pi_optimization_settings: "KioskPiOptimizationSettings",
        sample_kiosk_system_settings: "KioskSystemSettings",
        sample_kiosk_security_settings: "KioskSecuritySettings",
    ) -> "KioskSettings":
        """Create complete sample kiosk settings for testing."""
        return KioskSettings(
            enabled=True,
            auto_start=True,
            target_layout="whats-next-view",
            debug_mode=False,
            config_version="1.0",
            browser=sample_kiosk_browser_settings,
            display=sample_kiosk_display_settings,
            monitoring=sample_kiosk_monitoring_settings,
            pi_optimization=sample_kiosk_pi_optimization_settings,
            system=sample_kiosk_system_settings,
            security=sample_kiosk_security_settings,
        )

else:
    # Create placeholder fixtures when kiosk models aren't available
    @pytest.fixture
    def sample_kiosk_display_settings():
        pytest.skip("Kiosk models not available")

    @pytest.fixture
    def sample_kiosk_browser_settings():
        pytest.skip("Kiosk models not available")

    @pytest.fixture
    def sample_kiosk_monitoring_settings():
        pytest.skip("Kiosk models not available")

    @pytest.fixture
    def sample_kiosk_pi_optimization_settings():
        pytest.skip("Kiosk models not available")

    @pytest.fixture
    def sample_kiosk_system_settings():
        pytest.skip("Kiosk models not available")

    @pytest.fixture
    def sample_kiosk_security_settings():
        pytest.skip("Kiosk models not available")

    @pytest.fixture
    def sample_kiosk_settings():
        pytest.skip("Kiosk models not available")
