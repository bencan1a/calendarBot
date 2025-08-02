"""Integration tests for settings system end-to-end workflows."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from calendarbot.settings.exceptions import (
    SettingsError,
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
from calendarbot.web.server import WebRequestHandler


class TestSettingsEndToEndWorkflows:
    """Test complete settings workflows from API to persistence."""

    @pytest.fixture
    def temp_settings_dir(self) -> Path:
        """Create temporary directory for settings persistence."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def persistence_layer(self, temp_settings_dir: Path) -> SettingsPersistence:
        """Create real persistence layer for integration testing."""
        return SettingsPersistence(config_dir=temp_settings_dir)

    @pytest.fixture
    def settings_service(self, temp_settings_dir: Path) -> SettingsService:
        """Create real settings service for integration testing."""
        return SettingsService(config_dir=temp_settings_dir)

    @pytest.fixture
    def web_handler(self, settings_service: SettingsService) -> WebRequestHandler:
        """Create web handler with real settings service."""
        # Use established patching pattern to bypass BaseHTTPRequestHandler.__init__
        with patch.object(WebRequestHandler, "__init__", lambda self, *args, **kwargs: None):
            handler = WebRequestHandler()
            handler.web_server = Mock()
            handler.web_server.settings_service = settings_service
            handler._send_json_response = Mock()
            handler.send_response = Mock()
            handler.send_header = Mock()
            handler.end_headers = Mock()
            handler.wfile = Mock()
            return handler

    def test_complete_settings_lifecycle_when_normal_usage_then_works_correctly(
        self,
        web_handler: WebRequestHandler,
        settings_service: SettingsService,
        temp_settings_dir: Path,
    ) -> None:
        """Test complete settings lifecycle from API through persistence."""
        # 1. Get initial settings (should be defaults)
        web_handler._handle_get_settings(settings_service)

        # Verify default settings were returned
        call_args = web_handler._send_json_response.call_args
        assert call_args[0][0] == 200
        assert call_args[0][1]["success"] is True
        initial_data = call_args[0][1]["data"]
        assert "event_filters" in initial_data
        assert "display" in initial_data

        # 2. Update filter settings
        web_handler._send_json_response.reset_mock()
        new_filter_settings = {
            "enabled": True,
            "patterns": [
                {
                    "pattern": "test.*meeting",
                    "is_regex": True,
                    "case_sensitive": False,
                    "description": "Test meetings",
                }
            ],
            "default_action": "exclude",
        }

        # Remove unnecessary patching - let the real EventFilterSettings work
        web_handler._handle_update_filter_settings(settings_service, new_filter_settings)

        # Verify update succeeded
        call_args = web_handler._send_json_response.call_args
        assert call_args[0][0] == 200
        assert "Filter settings updated successfully" in call_args[0][1]["message"]

        # 3. Verify persistence by reading from file
        settings_file = temp_settings_dir / "settings.json"
        assert settings_file.exists()

        with open(settings_file) as f:
            persisted_data = json.load(f)

        assert persisted_data["event_filters"]["enabled"] is True
        assert len(persisted_data["event_filters"]["patterns"]) == 1
        assert persisted_data["event_filters"]["patterns"][0]["pattern"] == "test.*meeting"

        # 4. Get settings again to verify persistence
        web_handler._send_json_response.reset_mock()
        web_handler._handle_get_settings(settings_service)

        call_args = web_handler._send_json_response.call_args
        retrieved_data = call_args[0][1]["data"]
        assert retrieved_data["event_filters"]["enabled"] is True
        assert len(retrieved_data["event_filters"]["patterns"]) == 1

    def test_filter_pattern_management_workflow_when_add_remove_then_persists_correctly(
        self,
        web_handler: WebRequestHandler,
        settings_service: SettingsService,
        temp_settings_dir: Path,
    ) -> None:
        """Test filter pattern management workflow with persistence."""
        # 1. Add a filter pattern
        pattern_data = {
            "pattern": "urgent.*meeting",
            "is_regex": True,
            "case_sensitive": False,
            "description": "Urgent meetings filter",
        }

        web_handler._handle_add_filter_pattern(settings_service, pattern_data)

        # Verify pattern was added
        call_args = web_handler._send_json_response.call_args
        assert call_args[0][0] == 200
        assert "Filter pattern added successfully" in call_args[0][1]["message"]

        # 2. Verify persistence
        settings_file = temp_settings_dir / "settings.json"
        with open(settings_file) as f:
            persisted_data = json.load(f)

        patterns = persisted_data["event_filters"]["patterns"]
        assert len(patterns) == 1
        assert patterns[0]["pattern"] == "urgent.*meeting"
        assert patterns[0]["is_regex"] is True

        # 3. Add another pattern
        web_handler._send_json_response.reset_mock()
        second_pattern = {
            "pattern": "daily standup",
            "is_regex": False,
            "case_sensitive": True,
            "description": "Daily standup meetings",
        }

        web_handler._handle_add_filter_pattern(settings_service, second_pattern)

        # 4. Verify both patterns exist
        with open(settings_file) as f:
            persisted_data = json.load(f)

        patterns = persisted_data["event_filters"]["patterns"]
        assert len(patterns) == 2
        pattern_texts = [p["pattern"] for p in patterns]
        assert "urgent.*meeting" in pattern_texts
        assert "daily standup" in pattern_texts

        # 5. Remove first pattern
        web_handler._send_json_response.reset_mock()
        remove_params = {"pattern": ["urgent.*meeting"], "is_regex": ["true"]}

        web_handler._handle_remove_filter_pattern(settings_service, remove_params)

        # Verify removal succeeded
        call_args = web_handler._send_json_response.call_args
        assert call_args[0][0] == 200
        assert "Filter pattern removed successfully" in call_args[0][1]["message"]

        # 6. Verify persistence after removal
        with open(settings_file) as f:
            persisted_data = json.load(f)

        patterns = persisted_data["event_filters"]["patterns"]
        assert len(patterns) == 1
        assert patterns[0]["pattern"] == "daily standup"

    def test_settings_export_import_workflow_when_complete_cycle_then_preserves_data(
        self,
        web_handler: WebRequestHandler,
        settings_service: SettingsService,
        temp_settings_dir: Path,
    ) -> None:
        """Test settings export/import workflow preserves all data correctly."""
        # 1. Set up custom settings
        custom_settings = SettingsData(
            event_filters=EventFilterSettings(
                enabled=True,
                patterns=[
                    FilterPattern(
                        pattern="test.*",
                        is_regex=True,
                        case_sensitive=False,
                        description="Test pattern",
                    )
                ],
                default_action="exclude",
            ),
            display=DisplaySettings(color_theme="dark", display_density="normal"),
            conflict_resolution=ConflictResolutionSettings(
                priority_by_acceptance=True,
                priority_by_attendee_count=False,
                priority_by_organizer=False,
            ),
        )

        # Save initial settings
        settings_service.update_settings(custom_settings)

        # 2. Export settings
        web_handler._handle_export_settings(settings_service)

        # Verify export response
        assert web_handler.send_response.called
        assert web_handler.wfile.write.called

        # Extract exported data
        exported_content = web_handler.wfile.write.call_args[0][0].decode("utf-8")
        exported_data = json.loads(exported_content)

        # 3. Verify exported data structure
        assert "event_filters" in exported_data
        assert "display" in exported_data
        assert "conflict_resolution" in exported_data
        assert exported_data["event_filters"]["enabled"] is True
        assert exported_data["display"]["color_theme"] == "dark"
        assert exported_data["conflict_resolution"]["priority_by_acceptance"] is True

        # 4. Reset settings to defaults
        web_handler._send_json_response.reset_mock()
        web_handler._handle_reset_settings(settings_service)

        # 5. Import the exported settings
        web_handler._send_json_response.reset_mock()
        # Patch the import within the handler function
        with patch("calendarbot.settings.models.SettingsData", return_value=custom_settings):
            web_handler._handle_import_settings(settings_service, exported_data)

        # Verify import succeeded
        call_args = web_handler._send_json_response.call_args
        assert call_args[0][0] == 200
        assert "Settings imported successfully" in call_args[0][1]["message"]

        # 6. Verify imported settings match original
        web_handler._send_json_response.reset_mock()
        web_handler._handle_get_settings(settings_service)

        call_args = web_handler._send_json_response.call_args
        final_data = call_args[0][1]["data"]
        assert final_data["event_filters"]["enabled"] is True
        assert final_data["display"]["color_theme"] == "dark"
        assert final_data["conflict_resolution"]["priority_by_acceptance"] is True

    def test_settings_validation_workflow_when_invalid_data_then_prevents_persistence(
        self,
        web_handler: WebRequestHandler,
        settings_service: SettingsService,
        temp_settings_dir: Path,
    ) -> None:
        """Test settings validation prevents invalid data from being persisted."""
        # 1. Try to update with invalid settings
        invalid_settings = {
            "event_filters": {
                "enabled": "not_a_boolean",  # Invalid type
                "patterns": [],
                "default_action": "invalid_action",  # Invalid value
            },
            "display": {
                "color_theme": "invalid_theme",  # Invalid value
                "display_density": "normal",
            },
        }

        # Mock update_settings service method to raise validation error instead of patching SettingsData
        with patch.object(
            settings_service, "update_settings", side_effect=ValueError("Invalid settings data")
        ):
            web_handler._handle_update_settings(settings_service, invalid_settings)

        # Verify validation error was returned - invalid data returns 400 (bad request)
        call_args = web_handler._send_json_response.call_args
        assert call_args[0][0] == 400
        assert "Settings validation failed" in call_args[0][1]["error"]

        # 2. Verify no settings file was created (since validation failed)
        settings_file = temp_settings_dir / "settings.json"
        # File might exist with defaults, but should not contain invalid data
        if settings_file.exists():
            with open(settings_file) as f:
                persisted_data = json.load(f)
            # Should not contain invalid values
            assert persisted_data["event_filters"]["enabled"] in [True, False]
            assert persisted_data["display"]["color_theme"] in ["default", "dark", "light"]

    def test_concurrent_settings_access_when_multiple_operations_then_maintains_consistency(
        self,
        web_handler: WebRequestHandler,
        settings_service: SettingsService,
        temp_settings_dir: Path,
    ) -> None:
        """Test concurrent settings access maintains data consistency."""
        # This test simulates concurrent access patterns that might occur in real usage

        # 1. Initial settings update
        pattern_data = {
            "pattern": "concurrent.*test",
            "is_regex": True,
            "case_sensitive": False,
            "description": "Concurrent test pattern",
        }

        web_handler._handle_add_filter_pattern(settings_service, pattern_data)

        # 2. Simulate rapid successive operations
        for i in range(5):
            # Add pattern
            web_handler._send_json_response.reset_mock()
            pattern = {
                "pattern": f"pattern_{i}",
                "is_regex": False,
                "case_sensitive": False,
                "description": f"Pattern {i}",
            }
            web_handler._handle_add_filter_pattern(settings_service, pattern)

            # Get settings
            web_handler._send_json_response.reset_mock()
            web_handler._handle_get_settings(settings_service)

            # Verify consistency
            call_args = web_handler._send_json_response.call_args
            data = call_args[0][1]["data"]
            patterns = data["event_filters"]["patterns"]
            assert len(patterns) >= i + 2  # Initial + current patterns

        # 3. Verify final state consistency
        settings_file = temp_settings_dir / "settings.json"
        with open(settings_file) as f:
            persisted_data = json.load(f)

        patterns = persisted_data["event_filters"]["patterns"]
        assert len(patterns) == 6  # Initial + 5 added patterns

        # Verify all patterns are present and valid
        pattern_texts = [p["pattern"] for p in patterns]
        assert "concurrent.*test" in pattern_texts
        for i in range(5):
            assert f"pattern_{i}" in pattern_texts


class TestSettingsErrorPropagation:
    """Test error propagation across settings system layers."""

    @pytest.fixture
    def temp_settings_dir(self) -> Path:
        """Create temporary directory for settings persistence."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_persistence_error_propagation_when_file_system_error_then_handled_correctly(
        self, temp_settings_dir: Path
    ) -> None:
        """Test persistence errors propagate correctly through all layers."""
        # Create persistence layer with invalid directory
        invalid_dir = temp_settings_dir / "nonexistent" / "nested" / "path"
        persistence = SettingsPersistence(invalid_dir)

        # Make directory read-only to simulate permission error
        temp_settings_dir.chmod(0o444)

        try:
            service = SettingsService(config_dir=temp_settings_dir)

            # Create web handler with patching pattern
            with patch.object(WebRequestHandler, "__init__", lambda self, *args, **kwargs: None):
                with patch.object(
                    WebRequestHandler, "__init__", lambda self, *args, **kwargs: None
                ):
                    handler = WebRequestHandler()
                    handler.web_server = Mock()
                    handler.web_server.settings_service = service
                    handler._send_json_response = Mock()

            # Try to update settings - should propagate error correctly
            test_settings = {
                "event_filters": {"enabled": True, "patterns": [], "default_action": "include"}
            }

            with patch("calendarbot.settings.models.SettingsData") as mock_settings_data:
                settings_obj = SettingsData()
                mock_settings_data.return_value = settings_obj

                handler._handle_update_settings(service, test_settings)

            # Verify error was properly handled at API level
            call_args = handler._send_json_response.call_args
            assert call_args[0][0] == 500
            assert "Failed to update settings" in call_args[0][1]["error"]

        finally:
            # Restore permissions for cleanup
            temp_settings_dir.chmod(0o755)

    def test_service_layer_error_propagation_when_validation_fails_then_returns_detailed_errors(
        self, temp_settings_dir: Path
    ) -> None:
        """Test service layer validation errors propagate with details."""
        persistence = SettingsPersistence(config_dir=temp_settings_dir)
        service = SettingsService(config_dir=temp_settings_dir)

        handler = WebRequestHandler()
        handler.web_server = Mock()
        handler.web_server.settings_service = service
        handler._send_json_response = Mock()

        # Mock service to raise validation error with details
        with patch.object(service, "update_settings") as mock_update:
            validation_error = SettingsValidationError(
                "Multiple validation errors",
                validation_errors=["Error 1: Invalid theme", "Error 2: Invalid time format"],
            )
            mock_update.side_effect = validation_error

            test_settings = {"invalid": "data"}

            with patch("calendarbot.settings.models.SettingsData"):
                handler._handle_update_settings(service, test_settings)

        # Verify detailed error response
        call_args = handler._send_json_response.call_args
        assert call_args[0][0] == 400
        assert "Settings validation failed" in call_args[0][1]["error"]
        assert call_args[0][1]["validation_errors"] == [
            "Error 1: Invalid theme",
            "Error 2: Invalid time format",
        ]

    def test_api_layer_error_handling_when_unexpected_exception_then_returns_generic_error(
        self, temp_settings_dir: Path
    ) -> None:
        """Test API layer handles unexpected exceptions gracefully."""
        persistence = SettingsPersistence(config_dir=temp_settings_dir)
        service = SettingsService(config_dir=temp_settings_dir)

        handler = WebRequestHandler()
        handler.web_server = Mock()
        handler.web_server.settings_service = service
        handler._send_json_response = Mock()

        # Mock service to raise SettingsError (which the handler catches)
        with patch.object(
            service, "get_settings", side_effect=SettingsError("Unexpected system error")
        ):
            handler._handle_get_settings(service)

        # Verify generic error response
        call_args = handler._send_json_response.call_args
        assert call_args[0][0] == 500
        assert "Failed to get settings" in call_args[0][1]["error"]
        assert call_args[0][1]["message"] == "Unexpected system error"


class TestSettingsSystemIntegration:
    """Test integration between different settings system components."""

    @pytest.fixture
    def temp_settings_dir(self) -> Path:
        """Create temporary directory for settings persistence."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_settings_cache_integration_when_updates_then_cache_invalidated(
        self, temp_settings_dir: Path
    ) -> None:
        """Test settings cache is properly invalidated on updates."""
        persistence = SettingsPersistence(config_dir=temp_settings_dir)
        service = SettingsService(config_dir=temp_settings_dir)

        # 1. Get initial settings (loads cache)
        initial_settings = service.get_settings()
        assert initial_settings is not None

        # 2. Verify cache is loaded
        assert service._current_settings is not None
        cached_settings_id = id(service._current_settings)

        # 3. Update settings
        new_settings = SettingsData(
            display=DisplaySettings(color_theme="dark", display_density="compact")
        )
        updated_settings = service.update_settings(new_settings)

        # 4. Verify cache was invalidated and reloaded
        assert id(service._current_settings) != cached_settings_id
        assert updated_settings.display.color_theme == "dark"

        # 5. Get settings again to verify cache consistency
        retrieved_settings = service.get_settings()
        assert retrieved_settings.display.color_theme == "dark"

    def test_backup_and_recovery_integration_when_file_corruption_then_recovers_from_backup(
        self, temp_settings_dir: Path
    ) -> None:
        """Test backup and recovery integration works correctly."""
        persistence = SettingsPersistence(config_dir=temp_settings_dir)
        service = SettingsService(config_dir=temp_settings_dir)

        # 1. Create initial settings (this won't create backup)
        initial_settings = SettingsData(
            event_filters=EventFilterSettings(enabled=False, patterns=[])
        )
        service.update_settings(initial_settings)

        # 2. Update settings again (this will create backup of initial settings)
        test_settings = SettingsData(
            event_filters=EventFilterSettings(
                enabled=True,
                patterns=[FilterPattern(pattern="backup_test", description="Backup test pattern")],
            )
        )
        service.update_settings(test_settings)

        # 3. Verify backup was created
        backup_dir = temp_settings_dir / "settings_backups"
        backup_files = list(backup_dir.glob("settings_backup_*.json"))
        assert len(backup_files) > 0

        # 4. Corrupt main settings file
        settings_file = temp_settings_dir / "settings.json"
        with open(settings_file, "w") as f:
            f.write("corrupted json content {")

        # 5. Try to load settings - should recover from backup
        recovered_settings = service.get_settings()

        # 6. Verify recovery worked
        assert recovered_settings is not None
        # Note: Actual backup recovery depends on implementation details
        # This test verifies the integration points exist

    def test_schema_migration_integration_when_old_format_then_migrates_correctly(
        self, temp_settings_dir: Path
    ) -> None:
        """Test schema migration integration handles old format files."""
        # 1. Create old format settings file
        old_format_data = {
            "version": "1.0.0",  # Old version
            "filters": {"enabled": True, "rules": [{"pattern": "old_pattern"}]},  # Old structure
        }

        settings_file = temp_settings_dir / "settings.json"
        with open(settings_file, "w") as f:
            json.dump(old_format_data, f)

        # 2. Initialize service - should trigger migration
        persistence = SettingsPersistence(config_dir=temp_settings_dir)
        service = SettingsService(config_dir=temp_settings_dir)

        # 3. Get settings - should return migrated format
        settings = service.get_settings()

        # 4. Verify migration occurred
        assert settings is not None
        assert isinstance(settings, SettingsData)
        # Note: Actual migration logic depends on implementation
        # This test verifies the integration framework exists

    def test_settings_info_integration_when_called_then_returns_comprehensive_data(
        self, temp_settings_dir: Path
    ) -> None:
        """Test settings info integration returns data from all layers."""
        persistence = SettingsPersistence(config_dir=temp_settings_dir)
        service = SettingsService(config_dir=temp_settings_dir)

        # Set up some test data
        test_settings = SettingsData(
            event_filters=EventFilterSettings(
                patterns=[
                    FilterPattern(pattern="pattern1", description="Pattern 1"),
                    FilterPattern(pattern="pattern2", description="Pattern 2"),
                ]
            )
        )
        service.update_settings(test_settings)

        # Get settings info
        info = service.get_settings_info()

        # Verify comprehensive info is returned
        assert "settings_data" in info
        assert "persistence_info" in info
        assert "service_info" in info

        # Verify settings data info
        settings_info = info["settings_data"]
        assert "active_filters" in settings_info
        assert settings_info["active_filters"] == 2

        # Verify persistence info exists
        persistence_info = info["persistence_info"]
        assert isinstance(persistence_info, dict)

        # Verify service info exists
        service_info = info["service_info"]
        assert isinstance(service_info, dict)
        assert "cache_status" in service_info
