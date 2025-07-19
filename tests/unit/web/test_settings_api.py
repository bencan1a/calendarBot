"""Unit tests for settings API endpoints in web server."""

import json
from io import BytesIO
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest

from calendarbot.settings.exceptions import (
    SettingsError,
    SettingsPersistenceError,
    SettingsValidationError,
)
from calendarbot.settings.models import (
    ConflictResolutionSettings,
    DisplaySettings,
    EventFilterSettings,
    FilterPattern,
    SettingsData,
)
from calendarbot.settings.service import SettingsService
from calendarbot.web.server import WebRequestHandler


class TestSettingsAPIRouting:
    """Test settings API endpoint routing and method validation."""

    def test_handle_settings_api_when_settings_service_unavailable_then_returns_503(self) -> None:
        """Test settings API returns 503 when settings service is unavailable."""
        handler = WebRequestHandler()
        handler.web_server = Mock()
        handler.web_server.settings_service = None
        handler._send_json_response = Mock()

        handler._handle_settings_api("/api/settings", {})

        handler._send_json_response.assert_called_once_with(
            503,
            {
                "error": "Settings service not available",
                "message": "Settings functionality is currently unavailable",
            },
        )

    @pytest.mark.parametrize(
        "path,method,should_allow",
        [
            ("/api/settings", "GET", True),
            ("/api/settings", "PUT", True),
            ("/api/settings", "POST", False),
            ("/api/settings", "DELETE", False),
            ("/api/settings/filters", "GET", True),
            ("/api/settings/filters", "PUT", True),
            ("/api/settings/filters", "POST", False),
            ("/api/settings/display", "GET", True),
            ("/api/settings/display", "PUT", True),
            ("/api/settings/conflicts", "GET", True),
            ("/api/settings/conflicts", "PUT", True),
            ("/api/settings/validate", "POST", True),
            ("/api/settings/validate", "GET", False),
            ("/api/settings/export", "GET", True),
            ("/api/settings/export", "POST", False),
            ("/api/settings/import", "POST", True),
            ("/api/settings/import", "GET", False),
            ("/api/settings/reset", "POST", True),
            ("/api/settings/reset", "GET", False),
            ("/api/settings/info", "GET", True),
            ("/api/settings/info", "POST", False),
            ("/api/settings/filters/patterns", "POST", True),
            ("/api/settings/filters/patterns", "GET", False),
            ("/api/settings/filters/patterns", "DELETE", True),
        ],
    )
    def test_handle_settings_api_when_method_validation_then_responds_correctly(
        self, path: str, method: str, should_allow: bool
    ) -> None:
        """Test settings API method validation for all endpoints."""
        handler = WebRequestHandler()
        handler.command = method
        handler.web_server = Mock()
        handler.web_server.settings_service = Mock(spec=SettingsService)
        handler._send_json_response = Mock()

        # Mock individual handlers to avoid actual execution
        for handler_method in [
            "_handle_get_settings",
            "_handle_update_settings",
            "_handle_get_filter_settings",
            "_handle_update_filter_settings",
            "_handle_get_display_settings",
            "_handle_update_display_settings",
            "_handle_get_conflict_settings",
            "_handle_update_conflict_settings",
            "_handle_validate_settings",
            "_handle_export_settings",
            "_handle_import_settings",
            "_handle_reset_settings",
            "_handle_get_settings_info",
            "_handle_add_filter_pattern",
            "_handle_remove_filter_pattern",
        ]:
            setattr(handler, handler_method, Mock())

        handler._handle_settings_api(path, {})

        if should_allow:
            # Should not get method not allowed error
            calls = [
                call for call in handler._send_json_response.call_args_list if call[0][0] == 405
            ]
            assert len(calls) == 0, f"Method {method} should be allowed for {path}"
        else:
            # Should get method not allowed error
            handler._send_json_response.assert_called_with(405, {"error": "Method not allowed"})

    def test_handle_settings_api_when_unknown_endpoint_then_returns_404(self) -> None:
        """Test settings API returns 404 for unknown endpoints."""
        handler = WebRequestHandler()
        handler.command = "GET"
        handler.web_server = Mock()
        handler.web_server.settings_service = Mock(spec=SettingsService)
        handler._send_json_response = Mock()

        handler._handle_settings_api("/api/settings/unknown", {})

        handler._send_json_response.assert_called_once_with(
            404, {"error": "Settings API endpoint not found"}
        )

    def test_handle_settings_api_when_exception_occurs_then_returns_500(self) -> None:
        """Test settings API returns 500 when exception occurs."""
        handler = WebRequestHandler()
        handler.command = "GET"
        handler.web_server = Mock()
        handler.web_server.settings_service = Mock(spec=SettingsService)
        handler._send_json_response = Mock()

        # Mock handler to raise exception
        handler._handle_get_settings = Mock(side_effect=Exception("Test error"))

        handler._handle_settings_api("/api/settings", {})

        handler._send_json_response.assert_called_once_with(500, {"error": "Test error"})


class TestGetSettingsEndpoint:
    """Test GET /api/settings endpoint."""

    def test_handle_get_settings_when_successful_then_returns_settings(
        self, sample_settings_data: SettingsData
    ) -> None:
        """Test GET settings returns settings data successfully."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.get_settings.return_value = sample_settings_data

        handler._handle_get_settings(mock_service)

        mock_service.get_settings.assert_called_once()
        handler._send_json_response.assert_called_once_with(
            200, {"success": True, "data": sample_settings_data.to_api_dict()}
        )

    def test_handle_get_settings_when_service_error_then_returns_500(self) -> None:
        """Test GET settings returns 500 when service fails."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.get_settings.side_effect = SettingsError("Service failed")

        handler._handle_get_settings(mock_service)

        handler._send_json_response.assert_called_once_with(
            500, {"error": "Failed to get settings", "message": "Service failed"}
        )


class TestUpdateSettingsEndpoint:
    """Test PUT /api/settings endpoint."""

    def test_handle_update_settings_when_valid_data_then_updates_successfully(
        self, sample_settings_data: SettingsData
    ) -> None:
        """Test PUT settings updates with valid data successfully."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.update_settings.return_value = sample_settings_data

        params = sample_settings_data.dict()

        with patch(
            "calendarbot.settings.models.SettingsData", return_value=sample_settings_data
        ) as mock_settings_data:
            handler._handle_update_settings(mock_service, params)

            mock_settings_data.assert_called_once_with(**params)
            mock_service.update_settings.assert_called_once_with(sample_settings_data)
            handler._send_json_response.assert_called_once_with(
                200,
                {
                    "success": True,
                    "message": "Settings updated successfully",
                    "data": sample_settings_data.to_api_dict(),
                },
            )

    def test_handle_update_settings_when_invalid_data_then_returns_400(self) -> None:
        """Test PUT settings returns 400 with invalid request data."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)

        handler._handle_update_settings(mock_service, "invalid_data")

        handler._send_json_response.assert_called_once_with(400, {"error": "Invalid request data"})

    def test_handle_update_settings_when_validation_error_then_returns_400(self) -> None:
        """Test PUT settings returns 400 when validation fails."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        validation_error = SettingsValidationError(
            "Validation failed", validation_errors=["Error 1", "Error 2"]
        )
        mock_service.update_settings.side_effect = validation_error

        params = {"test": "data"}

        with patch("calendarbot.settings.models.SettingsData"):
            handler._handle_update_settings(mock_service, params)

            handler._send_json_response.assert_called_once_with(
                400,
                {
                    "error": "Settings validation failed",
                    "message": "Validation failed: {'validation_errors': ['Error 1', 'Error 2']}",
                    "validation_errors": ["Error 1", "Error 2"],
                },
            )

    def test_handle_update_settings_when_service_error_then_returns_500(self) -> None:
        """Test PUT settings returns 500 when service fails."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.update_settings.side_effect = SettingsError("Service failed")

        params = {"test": "data"}

        with patch("calendarbot.settings.models.SettingsData"):
            handler._handle_update_settings(mock_service, params)

            handler._send_json_response.assert_called_once_with(
                500, {"error": "Failed to update settings", "message": "Service failed"}
            )


class TestSpecificSettingsEndpoints:
    """Test specific settings endpoints (filters, display, conflicts)."""

    def test_handle_get_filter_settings_when_successful_then_returns_filters(
        self, sample_event_filter_settings: EventFilterSettings
    ) -> None:
        """Test GET filter settings returns filter data successfully."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.get_filter_settings.return_value = sample_event_filter_settings

        handler._handle_get_filter_settings(mock_service)

        handler._send_json_response.assert_called_once_with(
            200, {"success": True, "data": sample_event_filter_settings.dict()}
        )

    def test_handle_update_filter_settings_when_valid_data_then_updates_successfully(
        self, sample_event_filter_settings: EventFilterSettings
    ) -> None:
        """Test PUT filter settings updates successfully."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.update_filter_settings.return_value = sample_event_filter_settings

        params = sample_event_filter_settings.dict()

        with patch(
            "calendarbot.settings.models.EventFilterSettings",
            return_value=sample_event_filter_settings,
        ):
            handler._handle_update_filter_settings(mock_service, params)

            handler._send_json_response.assert_called_once_with(
                200,
                {
                    "success": True,
                    "message": "Filter settings updated successfully",
                    "data": sample_event_filter_settings.dict(),
                },
            )

    def test_handle_get_display_settings_when_successful_then_returns_display(
        self, sample_display_settings: DisplaySettings
    ) -> None:
        """Test GET display settings returns display data successfully."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.get_display_settings.return_value = sample_display_settings

        handler._handle_get_display_settings(mock_service)

        handler._send_json_response.assert_called_once_with(
            200, {"success": True, "data": sample_display_settings.dict()}
        )

    def test_handle_update_display_settings_when_valid_data_then_updates_successfully(
        self, sample_display_settings: DisplaySettings
    ) -> None:
        """Test PUT display settings updates successfully."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.update_display_settings.return_value = sample_display_settings

        params = sample_display_settings.dict()

        with patch(
            "calendarbot.settings.models.DisplaySettings", return_value=sample_display_settings
        ):
            handler._handle_update_display_settings(mock_service, params)

            handler._send_json_response.assert_called_once_with(
                200,
                {
                    "success": True,
                    "message": "Display settings updated successfully",
                    "data": sample_display_settings.dict(),
                },
            )

    def test_handle_get_conflict_settings_when_successful_then_returns_conflicts(
        self, sample_conflict_resolution_settings: ConflictResolutionSettings
    ) -> None:
        """Test GET conflict settings returns conflict data successfully."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.get_conflict_settings.return_value = sample_conflict_resolution_settings

        handler._handle_get_conflict_settings(mock_service)

        handler._send_json_response.assert_called_once_with(
            200, {"success": True, "data": sample_conflict_resolution_settings.dict()}
        )

    def test_handle_update_conflict_settings_when_valid_data_then_updates_successfully(
        self, sample_conflict_resolution_settings: ConflictResolutionSettings
    ) -> None:
        """Test PUT conflict settings updates successfully."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.update_conflict_settings.return_value = sample_conflict_resolution_settings

        params = sample_conflict_resolution_settings.dict()

        with patch(
            "calendarbot.settings.models.ConflictResolutionSettings",
            return_value=sample_conflict_resolution_settings,
        ):
            handler._handle_update_conflict_settings(mock_service, params)

            handler._send_json_response.assert_called_once_with(
                200,
                {
                    "success": True,
                    "message": "Conflict settings updated successfully",
                    "data": sample_conflict_resolution_settings.dict(),
                },
            )


class TestSettingsValidationEndpoint:
    """Test POST /api/settings/validate endpoint."""

    def test_handle_validate_settings_when_valid_data_then_returns_validation_result(
        self, sample_settings_data: SettingsData
    ) -> None:
        """Test POST validate settings returns validation result."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.validate_settings.return_value = []  # No errors

        params = sample_settings_data.dict()

        with patch("calendarbot.settings.models.SettingsData", return_value=sample_settings_data):
            handler._handle_validate_settings(mock_service, params)

            handler._send_json_response.assert_called_once_with(
                200, {"success": True, "valid": True, "validation_errors": []}
            )

    def test_handle_validate_settings_when_validation_errors_then_returns_errors(
        self, sample_settings_data: SettingsData
    ) -> None:
        """Test POST validate settings returns validation errors."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.validate_settings.return_value = ["Error 1", "Error 2"]

        params = sample_settings_data.dict()

        with patch("calendarbot.settings.models.SettingsData", return_value=sample_settings_data):
            handler._handle_validate_settings(mock_service, params)

            handler._send_json_response.assert_called_once_with(
                200, {"success": True, "valid": False, "validation_errors": ["Error 1", "Error 2"]}
            )

    def test_handle_validate_settings_when_invalid_data_then_returns_400(self) -> None:
        """Test POST validate settings returns 400 with invalid data."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)

        handler._handle_validate_settings(mock_service, "invalid_data")

        handler._send_json_response.assert_called_once_with(400, {"error": "Invalid request data"})

    def test_handle_validate_settings_when_exception_occurs_then_returns_400(self) -> None:
        """Test POST validate settings returns 400 when exception occurs."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)

        params = {"test": "data"}

        with patch(
            "calendarbot.settings.models.SettingsData", side_effect=Exception("Validation error")
        ):
            handler._handle_validate_settings(mock_service, params)

            handler._send_json_response.assert_called_once_with(
                400, {"error": "Settings validation failed", "message": "Validation error"}
            )


class TestSettingsExportEndpoint:
    """Test GET /api/settings/export endpoint."""

    def test_handle_export_settings_when_successful_then_returns_file(
        self, sample_settings_data: SettingsData
    ) -> None:
        """Test GET export settings returns file download."""
        handler = WebRequestHandler()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.get_settings.return_value = sample_settings_data

        handler._handle_export_settings(mock_service)

        # Verify file response headers
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_any_call("Content-Type", "application/json")
        handler.send_header.assert_any_call(
            "Content-Disposition", "attachment; filename=calendarbot_settings.json"
        )
        handler.end_headers.assert_called_once()

        # Verify JSON content was written
        written_content = handler.wfile.write.call_args[0][0]
        exported_data = json.loads(written_content.decode("utf-8"))
        assert "event_filters" in exported_data
        assert "display" in exported_data

    def test_handle_export_settings_when_service_error_then_returns_500(self) -> None:
        """Test GET export settings returns 500 when service fails."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.get_settings.side_effect = SettingsError("Export failed")

        handler._handle_export_settings(mock_service)

        handler._send_json_response.assert_called_once_with(
            500, {"error": "Failed to export settings", "message": "Export failed"}
        )


class TestSettingsImportEndpoint:
    """Test POST /api/settings/import endpoint."""

    def test_handle_import_settings_when_valid_data_then_imports_successfully(
        self, sample_settings_data: SettingsData
    ) -> None:
        """Test POST import settings imports data successfully."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.update_settings.return_value = sample_settings_data

        params = sample_settings_data.dict()

        with patch("calendarbot.settings.models.SettingsData", return_value=sample_settings_data):
            handler._handle_import_settings(mock_service, params)

            handler._send_json_response.assert_called_once_with(
                200,
                {
                    "success": True,
                    "message": "Settings imported successfully",
                    "data": sample_settings_data.to_api_dict(),
                },
            )

    def test_handle_import_settings_when_invalid_data_then_returns_400(self) -> None:
        """Test POST import settings returns 400 with invalid data."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)

        handler._handle_import_settings(mock_service, "invalid_data")

        handler._send_json_response.assert_called_once_with(400, {"error": "Invalid request data"})

    def test_handle_import_settings_when_validation_error_then_returns_400(self) -> None:
        """Test POST import settings returns 400 when validation fails."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        validation_error = SettingsValidationError("Import validation failed")
        mock_service.update_settings.side_effect = validation_error

        params = {"test": "data"}

        with patch("calendarbot.settings.models.SettingsData"):
            handler._handle_import_settings(mock_service, params)

            handler._send_json_response.assert_called_once_with(
                400,
                {
                    "error": "Settings import validation failed",
                    "message": "Import validation failed",
                },
            )


class TestSettingsResetEndpoint:
    """Test POST /api/settings/reset endpoint."""

    def test_handle_reset_settings_when_successful_then_resets_to_defaults(
        self, sample_settings_data: SettingsData
    ) -> None:
        """Test POST reset settings resets to defaults successfully."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.reset_to_defaults.return_value = sample_settings_data

        handler._handle_reset_settings(mock_service)

        mock_service.reset_to_defaults.assert_called_once()
        handler._send_json_response.assert_called_once_with(
            200,
            {
                "success": True,
                "message": "Settings reset to defaults successfully",
                "data": sample_settings_data.to_api_dict(),
            },
        )

    def test_handle_reset_settings_when_service_error_then_returns_500(self) -> None:
        """Test POST reset settings returns 500 when service fails."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.reset_to_defaults.side_effect = SettingsError("Reset failed")

        handler._handle_reset_settings(mock_service)

        handler._send_json_response.assert_called_once_with(
            500, {"error": "Failed to reset settings", "message": "Reset failed"}
        )


class TestSettingsInfoEndpoint:
    """Test GET /api/settings/info endpoint."""

    def test_handle_get_settings_info_when_successful_then_returns_info(self) -> None:
        """Test GET settings info returns settings information."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        info_data = {
            "settings_data": {"active_filters": 3},
            "persistence_info": {"backup_count": 5},
            "service_info": {"cache_status": "loaded"},
        }
        mock_service.get_settings_info.return_value = info_data

        handler._handle_get_settings_info(mock_service)

        handler._send_json_response.assert_called_once_with(
            200, {"success": True, "data": info_data}
        )

    def test_handle_get_settings_info_when_service_error_then_returns_500(self) -> None:
        """Test GET settings info returns 500 when service fails."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.get_settings_info.side_effect = SettingsError("Info failed")

        handler._handle_get_settings_info(mock_service)

        handler._send_json_response.assert_called_once_with(
            500, {"error": "Failed to get settings info", "message": "Info failed"}
        )


class TestFilterPatternEndpoints:
    """Test filter pattern management endpoints."""

    def test_handle_add_filter_pattern_when_valid_data_then_adds_successfully(
        self, sample_filter_pattern: FilterPattern
    ) -> None:
        """Test POST add filter pattern adds pattern successfully."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.add_filter_pattern.return_value = sample_filter_pattern

        params = {
            "pattern": "Test Pattern",
            "is_regex": True,
            "case_sensitive": False,
            "description": "Test description",
        }

        handler._handle_add_filter_pattern(mock_service, params)

        mock_service.add_filter_pattern.assert_called_once_with(
            "Test Pattern", True, False, "Test description"
        )
        handler._send_json_response.assert_called_once_with(
            200,
            {
                "success": True,
                "message": "Filter pattern added successfully",
                "data": sample_filter_pattern.dict(),
            },
        )

    def test_handle_add_filter_pattern_when_missing_pattern_then_returns_400(self) -> None:
        """Test POST add filter pattern returns 400 when pattern is missing."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)

        params = {"is_regex": False}  # Missing pattern

        handler._handle_add_filter_pattern(mock_service, params)

        handler._send_json_response.assert_called_once_with(400, {"error": "Pattern is required"})

    def test_handle_add_filter_pattern_when_invalid_data_then_returns_400(self) -> None:
        """Test POST add filter pattern returns 400 with invalid data."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)

        handler._handle_add_filter_pattern(mock_service, "invalid_data")

        handler._send_json_response.assert_called_once_with(400, {"error": "Invalid request data"})

    def test_handle_add_filter_pattern_when_validation_error_then_returns_400(self) -> None:
        """Test POST add filter pattern returns 400 when validation fails."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        validation_error = SettingsValidationError("Pattern validation failed")
        mock_service.add_filter_pattern.side_effect = validation_error

        params = {"pattern": "invalid_pattern"}

        handler._handle_add_filter_pattern(mock_service, params)

        handler._send_json_response.assert_called_once_with(
            400,
            {"error": "Filter pattern validation failed", "message": "Pattern validation failed"},
        )

    def test_handle_remove_filter_pattern_when_pattern_found_then_removes_successfully(
        self,
    ) -> None:
        """Test DELETE remove filter pattern removes pattern successfully."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.remove_filter_pattern.return_value = True

        params = {"pattern": ["Test Pattern"], "is_regex": ["false"]}

        handler._handle_remove_filter_pattern(mock_service, params)

        mock_service.remove_filter_pattern.assert_called_once_with("Test Pattern", False)
        handler._send_json_response.assert_called_once_with(
            200, {"success": True, "message": "Filter pattern removed successfully"}
        )

    def test_handle_remove_filter_pattern_when_pattern_not_found_then_returns_404(self) -> None:
        """Test DELETE remove filter pattern returns 404 when pattern not found."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.remove_filter_pattern.return_value = False

        params = {"pattern": ["Nonexistent"], "is_regex": ["false"]}

        handler._handle_remove_filter_pattern(mock_service, params)

        handler._send_json_response.assert_called_once_with(
            404, {"error": "Filter pattern not found"}
        )

    def test_handle_remove_filter_pattern_when_missing_pattern_then_returns_400(self) -> None:
        """Test DELETE remove filter pattern returns 400 when pattern parameter is missing."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)

        params = {"is_regex": ["false"]}  # Missing pattern

        handler._handle_remove_filter_pattern(mock_service, params)

        handler._send_json_response.assert_called_once_with(
            400, {"error": "Pattern parameter is required"}
        )

    def test_handle_remove_filter_pattern_when_service_error_then_returns_500(self) -> None:
        """Test DELETE remove filter pattern returns 500 when service fails."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.remove_filter_pattern.side_effect = SettingsError("Remove failed")

        params = {"pattern": ["Test Pattern"], "is_regex": ["false"]}

        handler._handle_remove_filter_pattern(mock_service, params)

        handler._send_json_response.assert_called_once_with(
            500, {"error": "Failed to remove filter pattern", "message": "Remove failed"}
        )


class TestSettingsAPIErrorHandling:
    """Test settings API error handling across all endpoints."""

    @pytest.mark.parametrize(
        "endpoint_handler,error_type,expected_status,expected_error",
        [
            ("_handle_get_settings", SettingsError("Get failed"), 500, "Failed to get settings"),
            (
                "_handle_get_filter_settings",
                SettingsError("Filter get failed"),
                500,
                "Failed to get filter settings",
            ),
            (
                "_handle_get_display_settings",
                SettingsError("Display get failed"),
                500,
                "Failed to get display settings",
            ),
            (
                "_handle_get_conflict_settings",
                SettingsError("Conflict get failed"),
                500,
                "Failed to get conflict settings",
            ),
            (
                "_handle_update_filter_settings",
                SettingsValidationError("Filter validation failed"),
                400,
                "Filter settings validation failed",
            ),
            (
                "_handle_update_display_settings",
                SettingsValidationError("Display validation failed"),
                400,
                "Display settings validation failed",
            ),
            (
                "_handle_update_conflict_settings",
                SettingsValidationError("Conflict validation failed"),
                400,
                "Conflict settings validation failed",
            ),
            (
                "_handle_update_filter_settings",
                SettingsError("Filter update failed"),
                500,
                "Failed to update filter settings",
            ),
            (
                "_handle_update_display_settings",
                SettingsError("Display update failed"),
                500,
                "Failed to update display settings",
            ),
            (
                "_handle_update_conflict_settings",
                SettingsError("Conflict update failed"),
                500,
                "Failed to update conflict settings",
            ),
        ],
    )
    def test_settings_handlers_when_errors_occur_then_return_appropriate_status(
        self,
        endpoint_handler: str,
        error_type: Exception,
        expected_status: int,
        expected_error: str,
    ) -> None:
        """Test settings handlers return appropriate status codes for different error types."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)

        # Set up the specific service method to raise the error
        service_method_map = {
            "_handle_get_settings": "get_settings",
            "_handle_get_filter_settings": "get_filter_settings",
            "_handle_get_display_settings": "get_display_settings",
            "_handle_get_conflict_settings": "get_conflict_settings",
            "_handle_update_filter_settings": "update_filter_settings",
            "_handle_update_display_settings": "update_display_settings",
            "_handle_update_conflict_settings": "update_conflict_settings",
        }

        service_method = service_method_map[endpoint_handler]
        getattr(mock_service, service_method).side_effect = error_type

        # Call the handler - no need to patch models since we're testing service error handling
        if endpoint_handler.startswith("_handle_update"):
            # Update handlers need params but don't need model patching for error testing
            getattr(handler, endpoint_handler)(mock_service, {"test": "data"})
        else:
            # Get handlers just need service
            getattr(handler, endpoint_handler)(mock_service)

        # Verify the response
        handler._send_json_response.assert_called_once()
        call_args = handler._send_json_response.call_args
        assert call_args[0][0] == expected_status
        assert expected_error in call_args[0][1]["error"]


class TestSettingsAPIDataValidation:
    """Test settings API request data validation."""

    @pytest.mark.parametrize(
        "handler_name,invalid_data",
        [
            ("_handle_update_settings", None),
            ("_handle_update_settings", []),
            ("_handle_update_settings", "string"),
            ("_handle_update_filter_settings", None),
            ("_handle_update_display_settings", None),
            ("_handle_update_conflict_settings", None),
            ("_handle_validate_settings", None),
            ("_handle_import_settings", None),
            ("_handle_add_filter_pattern", None),
            ("_handle_add_filter_pattern", []),
        ],
    )
    def test_update_handlers_when_invalid_data_types_then_return_400(
        self, handler_name: str, invalid_data: Any
    ) -> None:
        """Test update handlers return 400 for invalid data types."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)

        getattr(handler, handler_name)(mock_service, invalid_data)

        handler._send_json_response.assert_called_once_with(400, {"error": "Invalid request data"})

    def test_handle_remove_filter_pattern_when_pattern_parameter_formats_then_handles_correctly(
        self,
    ) -> None:
        """Test remove filter pattern handles different parameter formats correctly."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.remove_filter_pattern.return_value = True

        # Test with list format (query parameters)
        params_list = {"pattern": ["Test Pattern"], "is_regex": ["true"]}
        handler._handle_remove_filter_pattern(mock_service, params_list)

        mock_service.remove_filter_pattern.assert_called_with("Test Pattern", True)

        # Reset mock
        mock_service.reset_mock()
        handler._send_json_response.reset_mock()

        # Test with string format (JSON parameters)
        params_string = {"pattern": "Test Pattern", "is_regex": "false"}
        handler._handle_remove_filter_pattern(mock_service, params_string)

        mock_service.remove_filter_pattern.assert_called_with("Test Pattern", False)


class TestSettingsAPIIntegration:
    """Test settings API integration scenarios."""

    def test_complete_settings_api_workflow_when_normal_usage_then_works_correctly(
        self, sample_settings_data: SettingsData, sample_filter_pattern: FilterPattern
    ) -> None:
        """Test complete settings API workflow from get to update to export."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()

        mock_service = Mock(spec=SettingsService)
        mock_service.get_settings.return_value = sample_settings_data
        mock_service.update_settings.return_value = sample_settings_data
        mock_service.add_filter_pattern.return_value = sample_filter_pattern

        # 1. Get initial settings
        handler._handle_get_settings(mock_service)
        assert handler._send_json_response.call_count == 1

        # 2. Add a filter pattern
        handler._send_json_response.reset_mock()
        pattern_params = {
            "pattern": "Test Pattern",
            "is_regex": False,
            "case_sensitive": False,
            "description": "Test",
        }
        handler._handle_add_filter_pattern(mock_service, pattern_params)
        assert handler._send_json_response.call_count == 1

        # 3. Update settings - mock at service level instead
        handler._send_json_response.reset_mock()
        handler._handle_update_settings(mock_service, sample_settings_data.dict())
        assert handler._send_json_response.call_count == 1

        # 4. Export settings
        handler._send_json_response.reset_mock()
        handler._handle_export_settings(mock_service)
        # Export doesn't use _send_json_response, it writes directly
        assert handler.send_response.called
        assert handler.wfile.write.called

    def test_settings_api_error_propagation_when_service_errors_then_propagates_correctly(
        self,
    ) -> None:
        """Test settings API properly propagates different types of service errors."""
        handler = WebRequestHandler()
        handler._send_json_response = Mock()

        mock_service = Mock(spec=SettingsService)

        # Test SettingsValidationError propagation
        validation_error = SettingsValidationError(
            "Validation failed", validation_errors=["Error 1"]
        )
        mock_service.update_settings.side_effect = validation_error

        handler._handle_update_settings(mock_service, {"test": "data"})

        call_args = handler._send_json_response.call_args
        assert call_args[0][0] == 400
        assert "Settings validation failed" in call_args[0][1]["error"]
        assert call_args[0][1]["validation_errors"] == ["Error 1"]

        # Reset and test SettingsError propagation
        handler._send_json_response.reset_mock()
        settings_error = SettingsError("Service error")
        mock_service.get_settings.side_effect = settings_error

        handler._handle_get_settings(mock_service)

        call_args = handler._send_json_response.call_args
        assert call_args[0][0] == 500
        assert "Failed to get settings" in call_args[0][1]["error"]
        assert call_args[0][1]["message"] == "Service error"
