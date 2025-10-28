"""Unit tests for settings API endpoints in web server."""

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
from calendarbot.settings.service import SettingsService
from calendarbot.web.server import WebRequestHandler


# Shared fixtures for all test classes
@pytest.fixture
def mock_handler():
    """Create a mock WebRequestHandler."""
    handler = WebRequestHandler()
    handler.web_server = Mock()
    handler.web_server.settings_service = Mock(spec=SettingsService)
    handler._send_json_response = Mock()
    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()
    handler.wfile = Mock()
    return handler


@pytest.fixture
def sample_settings_data():
    """Create sample settings data."""
    return SettingsData(
        event_filters=EventFilterSettings(),
        display=DisplaySettings(),
        conflict_resolution=ConflictResolutionSettings(),
    )


@pytest.fixture
def sample_filter_pattern():
    """Create sample filter pattern."""
    return FilterPattern(
        pattern="Test Pattern", is_regex=True, case_sensitive=False, description="Test description"
    )


class TestSettingsAPIRouting:
    """Test settings API endpoint routing and method validation."""

    def test_handle_settings_api_when_settings_service_unavailable_then_returns_503(
        self, mock_handler
    ) -> None:
        """Test settings API returns 503 when settings service is unavailable."""
        mock_handler.web_server.settings_service = None

        mock_handler._handle_settings_api("/api/settings", {})

        mock_handler._send_json_response.assert_called_once_with(
            503,
            {
                "error": "Settings service not available",
                "message": "Settings functionality is currently unavailable",
            },
        )

    @pytest.mark.parametrize(
        ("path", "method", "should_allow"),
        [
            # Core settings endpoints
            ("/api/settings", "GET", True),
            ("/api/settings", "PUT", True),
            ("/api/settings", "POST", False),
            # Sub-endpoints with standard patterns
            ("/api/settings/filters", "GET", True),
            ("/api/settings/filters", "PUT", True),
            ("/api/settings/display", "GET", True),
            ("/api/settings/display", "PUT", True),
            ("/api/settings/conflicts", "GET", True),
            ("/api/settings/conflicts", "PUT", True),
            # Action endpoints
            ("/api/settings/validate", "POST", True),
            ("/api/settings/validate", "GET", False),
            ("/api/settings/export", "GET", True),
            ("/api/settings/import", "POST", True),
            ("/api/settings/reset", "POST", True),
            ("/api/settings/info", "GET", True),
            # Pattern management
            ("/api/settings/filters/patterns", "POST", True),
            ("/api/settings/filters/patterns", "DELETE", True),
            ("/api/settings/filters/patterns", "GET", False),
        ],
    )
    def test_api_method_validation(
        self, mock_handler, path: str, method: str, should_allow: bool
    ) -> None:
        """Test settings API method validation for all endpoints."""
        mock_handler.command = method

        # Mock all handler methods to avoid execution
        handler_methods = [
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
        ]
        for handler_method in handler_methods:
            setattr(mock_handler, handler_method, Mock())

        mock_handler._handle_settings_api(path, {})

        if should_allow:
            # Should not get method not allowed error
            method_not_allowed_calls = [
                call
                for call in mock_handler._send_json_response.call_args_list
                if call[0][0] == 405
            ]
            assert len(method_not_allowed_calls) == 0, (
                f"Method {method} should be allowed for {path}"
            )
        else:
            # Should get method not allowed error
            mock_handler._send_json_response.assert_called_with(
                405, {"error": "Method not allowed"}
            )

    @pytest.mark.parametrize(
        ("endpoint", "expected_error"),
        [
            ("/api/settings/unknown", "Settings API endpoint not found"),
            ("/api/settings/invalid/path", "Settings API endpoint not found"),
        ],
    )
    def test_unknown_endpoints(self, mock_handler, endpoint: str, expected_error: str) -> None:
        """Test unknown endpoint handling."""
        mock_handler.command = "GET"
        mock_handler._handle_settings_api(endpoint, {})
        mock_handler._send_json_response.assert_called_once_with(404, {"error": expected_error})

    def test_exception_handling(self, mock_handler) -> None:
        """Test exception handling in API routing."""
        mock_handler.command = "GET"
        mock_handler._handle_get_settings = Mock(side_effect=Exception("Test error"))
        mock_handler._handle_settings_api("/api/settings", {})
        mock_handler._send_json_response.assert_called_once_with(500, {"error": "Test error"})


class TestSettingsEndpoints:
    """Test settings API endpoints with consolidated logic."""

    @pytest.mark.parametrize(
        ("handler_method", "service_method", "expected_data_key"),
        [
            ("_handle_get_settings", "get_settings", "data"),
            ("_handle_get_filter_settings", "get_filter_settings", "data"),
            ("_handle_get_display_settings", "get_display_settings", "data"),
            ("_handle_get_conflict_settings", "get_conflict_settings", "data"),
            ("_handle_get_settings_info", "get_settings_info", "data"),
        ],
    )
    def test_get_endpoints_success(
        self, mock_handler, sample_settings_data, handler_method, service_method, expected_data_key
    ):
        """Test successful GET endpoint responses."""
        getattr(
            mock_handler.web_server.settings_service, service_method
        ).return_value = sample_settings_data

        handler_func = getattr(mock_handler, handler_method)
        handler_func(mock_handler.web_server.settings_service)

        mock_handler._send_json_response.assert_called_once()
        args = mock_handler._send_json_response.call_args[0]
        assert args[0] == 200
        assert args[1]["success"] is True
        assert expected_data_key in args[1]

    @pytest.mark.parametrize(
        ("handler_method", "service_method", "error_message"),
        [
            ("_handle_get_settings", "get_settings", "Failed to get settings"),
            ("_handle_get_filter_settings", "get_filter_settings", "Failed to get filter settings"),
            (
                "_handle_get_display_settings",
                "get_display_settings",
                "Failed to get display settings",
            ),
            (
                "_handle_get_conflict_settings",
                "get_conflict_settings",
                "Failed to get conflict settings",
            ),
            ("_handle_get_settings_info", "get_settings_info", "Failed to get settings info"),
        ],
    )
    def test_get_endpoints_service_error(
        self, mock_handler, handler_method, service_method, error_message
    ):
        """Test GET endpoint error handling."""
        getattr(
            mock_handler.web_server.settings_service, service_method
        ).side_effect = SettingsError("Service failed")

        handler_func = getattr(mock_handler, handler_method)
        handler_func(mock_handler.web_server.settings_service)

        mock_handler._send_json_response.assert_called_once_with(
            500, {"error": error_message, "message": "Service failed"}
        )

    @pytest.mark.parametrize(
        ("handler_method", "service_method", "success_message"),
        [
            ("_handle_update_settings", "update_settings", "Settings updated successfully"),
            (
                "_handle_update_filter_settings",
                "update_filter_settings",
                "Filter settings updated successfully",
            ),
            (
                "_handle_update_display_settings",
                "update_display_settings",
                "Display settings updated successfully",
            ),
            (
                "_handle_update_conflict_settings",
                "update_conflict_settings",
                "Conflict settings updated successfully",
            ),
            ("_handle_import_settings", "update_settings", "Settings imported successfully"),
        ],
    )
    def test_update_endpoints_success(
        self, mock_handler, sample_settings_data, handler_method, service_method, success_message
    ):
        """Test successful update endpoint responses."""
        getattr(
            mock_handler.web_server.settings_service, service_method
        ).return_value = sample_settings_data

        params = {"test": "data"}
        with patch("calendarbot.settings.models.SettingsData", return_value=sample_settings_data):
            handler_func = getattr(mock_handler, handler_method)
            handler_func(mock_handler.web_server.settings_service, params)

        mock_handler._send_json_response.assert_called_once()
        args = mock_handler._send_json_response.call_args[0]
        assert args[0] == 200
        assert args[1]["success"] is True
        assert args[1]["message"] == success_message

    @pytest.mark.parametrize(
        ("handler_method", "invalid_data"),
        [
            ("_handle_update_settings", "invalid_string"),
            ("_handle_update_filter_settings", None),
            ("_handle_update_display_settings", []),
            ("_handle_validate_settings", None),
            ("_handle_import_settings", "invalid"),
        ],
    )
    def test_update_endpoints_invalid_data(self, mock_handler, handler_method, invalid_data):
        """Test update endpoints with invalid data."""
        handler_func = getattr(mock_handler, handler_method)
        handler_func(mock_handler.web_server.settings_service, invalid_data)

        mock_handler._send_json_response.assert_called_once_with(
            400, {"error": "Invalid request data"}
        )

    def test_validation_endpoint_success(self, mock_handler, sample_settings_data):
        """Test settings validation endpoint."""
        mock_handler.web_server.settings_service.validate_settings.return_value = []

        params = sample_settings_data.dict()
        with patch("calendarbot.settings.models.SettingsData", return_value=sample_settings_data):
            mock_handler._handle_validate_settings(mock_handler.web_server.settings_service, params)

        mock_handler._send_json_response.assert_called_once_with(
            200, {"success": True, "valid": True, "validation_errors": []}
        )

    def test_export_endpoint_success(self, mock_handler, sample_settings_data):
        """Test settings export endpoint."""
        mock_handler.web_server.settings_service.get_settings.return_value = sample_settings_data

        mock_handler._handle_export_settings(mock_handler.web_server.settings_service)

        mock_handler.send_response.assert_called_once_with(200)
        mock_handler.send_header.assert_any_call("Content-Type", "application/json")
        mock_handler.send_header.assert_any_call(
            "Content-Disposition", "attachment; filename=calendarbot_settings.json"
        )

    def test_reset_endpoint_success(self, mock_handler, sample_settings_data):
        """Test settings reset endpoint."""
        mock_handler.web_server.settings_service.reset_to_defaults.return_value = (
            sample_settings_data
        )

        mock_handler._handle_reset_settings(mock_handler.web_server.settings_service)

        mock_handler._send_json_response.assert_called_once()
        args = mock_handler._send_json_response.call_args[0]
        assert args[0] == 200
        assert args[1]["success"] is True
        assert args[1]["message"] == "Settings reset to defaults successfully"


class TestFilterPatternEndpoints:
    """Test filter pattern management endpoints."""

    def test_add_filter_pattern_success(self, mock_handler, sample_filter_pattern):
        """Test successful filter pattern addition."""
        mock_handler.web_server.settings_service.add_filter_pattern.return_value = (
            sample_filter_pattern
        )

        params = {
            "pattern": "Test Pattern",
            "is_regex": True,
            "case_sensitive": False,
            "description": "Test description",
        }

        mock_handler._handle_add_filter_pattern(mock_handler.web_server.settings_service, params)

        mock_handler.web_server.settings_service.add_filter_pattern.assert_called_once_with(
            "Test Pattern", True, False, "Test description"
        )
        mock_handler._send_json_response.assert_called_once()
        args = mock_handler._send_json_response.call_args[0]
        assert args[0] == 200
        assert args[1]["success"] is True

    @pytest.mark.parametrize(
        ("params", "expected_error"),
        [
            ({"is_regex": False}, "Pattern is required"),
            ("invalid_data", "Invalid request data"),
            (None, "Invalid request data"),
        ],
    )
    def test_add_filter_pattern_errors(self, mock_handler, params, expected_error):
        """Test filter pattern addition error cases."""
        mock_handler._handle_add_filter_pattern(mock_handler.web_server.settings_service, params)
        mock_handler._send_json_response.assert_called_once_with(400, {"error": expected_error})

    @pytest.mark.parametrize(
        ("params", "service_result", "expected_status", "expected_message"),
        [
            (
                {"pattern": ["Test"], "is_regex": ["false"]},
                True,
                200,
                "Filter pattern removed successfully",
            ),
            (
                {"pattern": ["Missing"], "is_regex": ["false"]},
                False,
                404,
                "Filter pattern not found",
            ),
            ({"is_regex": ["false"]}, None, 400, "Pattern parameter is required"),
        ],
    )
    def test_remove_filter_pattern_scenarios(
        self, mock_handler, params, service_result, expected_status, expected_message
    ):
        """Test filter pattern removal scenarios."""
        if service_result is not None:
            mock_handler.web_server.settings_service.remove_filter_pattern.return_value = (
                service_result
            )

        mock_handler._handle_remove_filter_pattern(mock_handler.web_server.settings_service, params)

        mock_handler._send_json_response.assert_called_once()
        args = mock_handler._send_json_response.call_args[0]
        assert args[0] == expected_status
        if expected_status == 200:
            assert args[1]["message"] == expected_message
        else:
            assert expected_message in args[1]["error"]


class TestSettingsAPIIntegration:
    """Test settings API integration and error handling scenarios."""

    def test_complete_workflow(self, mock_handler, sample_settings_data, sample_filter_pattern):
        """Test complete settings API workflow."""
        mock_service = mock_handler.web_server.settings_service
        mock_service.get_settings.return_value = sample_settings_data
        mock_service.update_settings.return_value = sample_settings_data
        mock_service.add_filter_pattern.return_value = sample_filter_pattern

        # 1. Get settings
        mock_handler._handle_get_settings(mock_service)
        assert mock_handler._send_json_response.call_count == 1

        # 2. Add pattern
        mock_handler._send_json_response.reset_mock()
        pattern_params = {
            "pattern": "Test",
            "is_regex": False,
            "case_sensitive": False,
            "description": "Test",
        }
        mock_handler._handle_add_filter_pattern(mock_service, pattern_params)
        assert mock_handler._send_json_response.call_count == 1

        # 3. Export settings
        mock_handler._send_json_response.reset_mock()
        mock_handler._handle_export_settings(mock_service)
        assert mock_handler.send_response.called

    @pytest.mark.parametrize(
        ("error_type", "expected_status"),
        [
            (SettingsValidationError("Validation failed", validation_errors=["Error 1"]), 400),
            (SettingsError("Service error"), 500),
        ],
    )
    def test_error_propagation(self, mock_handler, error_type, expected_status):
        """Test error propagation in settings API."""
        mock_handler.web_server.settings_service.update_settings.side_effect = error_type
        mock_handler._handle_update_settings(
            mock_handler.web_server.settings_service, {"test": "data"}
        )

        args = mock_handler._send_json_response.call_args[0]
        assert args[0] == expected_status
