"""Unit tests for calendarbot.validation.logging_setup module."""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest

from calendarbot.validation.logging_setup import (
    ComponentFilter,
    ValidationFormatter,
    get_validation_logger,
    log_validation_result,
    log_validation_start,
    setup_validation_logging,
)


class TestValidationFormatter:
    """Test ValidationFormatter class functionality."""

    @pytest.fixture
    def formatter(self):
        """Create ValidationFormatter instance for testing."""
        return ValidationFormatter(
            "%(asctime)s.%(msecs_formatted)s [%(component)8s] %(levelname)7s: %(message)s",
            datefmt="%H:%M:%S",
        )

    def test_format_record_with_calendarbot_logger(self, formatter):
        """Test format method with calendarbot logger name."""
        record = logging.LogRecord(
            name="calendarbot.auth",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.msecs = 123.456

        formatted = formatter.format(record)

        assert hasattr(record, "msecs_formatted")
        assert record.msecs_formatted == "123"
        assert hasattr(record, "component")
        assert record.component == "auth"
        assert "Test message" in formatted

    def test_format_record_with_non_calendarbot_logger(self, formatter):
        """Test format method with non-calendarbot logger name."""
        record = logging.LogRecord(
            name="other.module",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.msecs = 456.789

        formatted = formatter.format(record)

        assert record.component == "system"
        assert record.msecs_formatted == "457"

    def test_format_record_with_single_part_logger(self, formatter):
        """Test format method with single-part logger name."""
        record = logging.LogRecord(
            name="root",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Warning message",
            args=(),
            exc_info=None,
        )
        record.msecs = 0.0

        formatted = formatter.format(record)

        assert record.component == "system"
        assert record.msecs_formatted == "000"

    def test_format_record_with_deep_logger_hierarchy(self, formatter):
        """Test format method with deep logger hierarchy."""
        record = logging.LogRecord(
            name="calendarbot.api.graph.client",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error message",
            args=(),
            exc_info=None,
        )
        record.msecs = 999.999

        formatted = formatter.format(record)

        assert record.component == "api"  # Should extract second part
        assert record.msecs_formatted == "1000"


class TestComponentFilter:
    """Test ComponentFilter class functionality."""

    def test_component_filter_initialization_with_allowed_components(self):
        """Test ComponentFilter initialization with allowed components."""
        allowed_components = ["auth", "api", "cache"]
        filter_instance = ComponentFilter(allowed_components)

        assert filter_instance.allowed_components == set(allowed_components)

    def test_component_filter_initialization_with_none(self):
        """Test ComponentFilter initialization with None (allow all)."""
        filter_instance = ComponentFilter(None)

        assert filter_instance.allowed_components is None

    def test_component_filter_initialization_with_empty_list(self):
        """Test ComponentFilter initialization with empty list."""
        filter_instance = ComponentFilter([])

        assert filter_instance.allowed_components == set()

    def test_filter_allows_all_when_no_components_specified(self):
        """Test filter allows all records when no components specified."""
        filter_instance = ComponentFilter(None)

        record = Mock()
        record.name = "any.logger.name"

        assert filter_instance.filter(record) == True

    def test_filter_allows_matching_calendarbot_component(self):
        """Test filter allows matching calendarbot component."""
        filter_instance = ComponentFilter(["auth", "api"])

        record = Mock()
        record.name = "calendarbot.auth.manager"

        assert filter_instance.filter(record) == True

    def test_filter_blocks_non_matching_calendarbot_component(self):
        """Test filter blocks non-matching calendarbot component."""
        filter_instance = ComponentFilter(["auth", "api"])

        record = Mock()
        record.name = "calendarbot.cache.manager"

        assert filter_instance.filter(record) == False

    def test_filter_allows_system_logs_when_system_in_allowed(self):
        """Test filter allows system logs when system is in allowed components."""
        filter_instance = ComponentFilter(["auth", "system"])

        record = Mock()
        record.name = "other.module"

        assert filter_instance.filter(record) == True

    def test_filter_blocks_system_logs_when_system_not_in_allowed(self):
        """Test filter blocks system logs when system not in allowed components."""
        filter_instance = ComponentFilter(["auth", "api"])

        record = Mock()
        record.name = "other.module"

        assert filter_instance.filter(record) == False

    def test_filter_handles_single_part_calendarbot_logger(self):
        """Test filter handles single-part calendarbot logger name."""
        filter_instance = ComponentFilter(["auth"])

        record = Mock()
        record.name = "calendarbot"

        # Should treat as system since no component part
        assert filter_instance.filter(record) == False

    def test_filter_handles_non_calendarbot_logger_with_system_allowed(self):
        """Test filter handles non-calendarbot logger with system allowed."""
        filter_instance = ComponentFilter(["system"])

        record = Mock()
        record.name = "urllib3.connectionpool"

        assert filter_instance.filter(record) == True


class TestSetupValidationLogging:
    """Test setup_validation_logging function."""

    @patch("calendarbot.validation.logging_setup.logging.getLogger")
    def test_setup_validation_logging_basic(self, mock_get_logger):
        """Test basic setup_validation_logging functionality."""
        mock_logger = Mock()
        mock_logger.handlers = []  # Fix: Ensure handlers is a list
        mock_get_logger.return_value = mock_logger

        with patch("calendarbot.validation.logging_setup.logging.StreamHandler") as mock_handler:
            with patch("calendarbot.validation.logging_setup.sys.stdout", new=Mock()):

                result = setup_validation_logging()

                assert isinstance(result, dict)
                assert "sources" in result  # Updated component name
                assert "cache" in result
                assert "display" in result
                assert "validation" in result
                assert "system" in result

    @patch("calendarbot.validation.logging_setup.logging.getLogger")
    def test_setup_validation_logging_verbose(self, mock_get_logger):
        """Test setup_validation_logging with verbose mode."""
        mock_logger = Mock()
        mock_logger.handlers = []  # Fix: Ensure handlers is a list
        mock_get_logger.return_value = mock_logger

        with patch(
            "calendarbot.validation.logging_setup.logging.StreamHandler"
        ) as mock_handler_class:
            mock_handler = Mock()
            mock_handler_class.return_value = mock_handler

            result = setup_validation_logging(verbose=True)

            # Should set DEBUG level when verbose
            mock_handler.setLevel.assert_called_with(logging.DEBUG)

    @patch("calendarbot.validation.logging_setup.logging.getLogger")
    def test_setup_validation_logging_with_components(self, mock_get_logger):
        """Test setup_validation_logging with specific components."""
        mock_logger = Mock()
        mock_logger.handlers = []  # Fix: Ensure handlers is a list
        mock_get_logger.return_value = mock_logger

        components = ["sources", "cache"]  # Updated component names

        with patch(
            "calendarbot.validation.logging_setup.logging.StreamHandler"
        ) as mock_handler_class:
            with patch("calendarbot.validation.logging_setup.ComponentFilter") as mock_filter_class:
                mock_handler = Mock()
                mock_filter = Mock()
                mock_handler_class.return_value = mock_handler
                mock_filter_class.return_value = mock_filter

                result = setup_validation_logging(components=components)

                # Should create component filter with system added
                mock_filter_class.assert_called_with(["sources", "cache", "system"])
                mock_handler.addFilter.assert_called_with(mock_filter)

    @patch("calendarbot.validation.logging_setup.logging.getLogger")
    @patch("calendarbot.validation.logging_setup.logging.handlers.RotatingFileHandler")
    def test_setup_validation_logging_with_log_file(self, mock_file_handler_class, mock_get_logger):
        """Test setup_validation_logging with log file."""
        mock_logger = Mock()
        mock_logger.handlers = []  # Fix: Ensure handlers is a list
        mock_get_logger.return_value = mock_logger
        mock_file_handler = Mock()
        mock_file_handler_class.return_value = mock_file_handler

        with patch("calendarbot.validation.logging_setup.Path") as mock_path_class:
            mock_path = Mock()
            mock_path_class.return_value = mock_path

            result = setup_validation_logging(log_file="/test/log/file.log")

            # Should create file handler
            mock_file_handler_class.assert_called_once()
            mock_file_handler.setLevel.assert_called_with(logging.DEBUG)
            mock_logger.addHandler.assert_called_with(mock_file_handler)

    @patch("calendarbot.validation.logging_setup.logging.getLogger")
    def test_setup_validation_logging_clears_existing_handlers(self, mock_get_logger):
        """Test that setup_validation_logging clears existing handlers."""
        mock_root_logger = Mock()
        mock_existing_handler = Mock()
        mock_root_logger.handlers = [mock_existing_handler]

        def mock_get_logger_side_effect(name=""):
            if name == "":
                return mock_root_logger
            return Mock()

        mock_get_logger.side_effect = mock_get_logger_side_effect

        with patch("calendarbot.validation.logging_setup.logging.StreamHandler"):
            result = setup_validation_logging()

            # Should remove existing handlers
            mock_root_logger.removeHandler.assert_called_with(mock_existing_handler)

    @patch("calendarbot.validation.logging_setup.logging.getLogger")
    def test_setup_validation_logging_configures_third_party_loggers(self, mock_get_logger):
        """Test that setup_validation_logging configures third-party logger levels."""
        mock_loggers = {}

        def mock_get_logger_side_effect(name=""):
            if name not in mock_loggers:
                mock_loggers[name] = Mock()
                # Fix: Ensure handlers is a list for root logger
                if name == "":
                    mock_loggers[name].handlers = []
            return mock_loggers[name]

        mock_get_logger.side_effect = mock_get_logger_side_effect

        with patch("calendarbot.validation.logging_setup.logging.StreamHandler"):
            result = setup_validation_logging()

            # Should configure third-party logger levels
            assert "aiohttp" in mock_loggers
            assert "urllib3" in mock_loggers
            assert "msal" in mock_loggers
            assert "asyncio" in mock_loggers

            # Check that WARNING level was set
            mock_loggers["aiohttp"].setLevel.assert_called_with(logging.WARNING)
            mock_loggers["urllib3"].setLevel.assert_called_with(logging.WARNING)
            mock_loggers["msal"].setLevel.assert_called_with(logging.WARNING)
            mock_loggers["asyncio"].setLevel.assert_called_with(logging.WARNING)


class TestGetValidationLogger:
    """Test get_validation_logger function."""

    @patch("calendarbot.validation.logging_setup.logging.getLogger")
    def test_get_validation_logger(self, mock_get_logger):
        """Test get_validation_logger function."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        result = get_validation_logger("auth")

        mock_get_logger.assert_called_once_with("calendarbot.auth")
        assert result == mock_logger

    @pytest.mark.parametrize(
        "component,expected_name",
        [
            ("auth", "calendarbot.auth"),
            ("api", "calendarbot.api"),
            ("cache", "calendarbot.cache"),
            ("display", "calendarbot.display"),
            ("validation", "calendarbot.validation"),
        ],
    )
    @patch("calendarbot.validation.logging_setup.logging.getLogger")
    def test_get_validation_logger_component_mapping(
        self, mock_get_logger, component, expected_name
    ):
        """Test get_validation_logger with different components."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        result = get_validation_logger(component)

        mock_get_logger.assert_called_once_with(expected_name)


class TestLogValidationStart:
    """Test log_validation_start function."""

    def test_log_validation_start_basic(self):
        """Test log_validation_start with basic parameters."""
        mock_logger = Mock()

        log_validation_start(mock_logger, "test_validation")

        mock_logger.info.assert_called_once_with("Starting validation: test_validation")

    def test_log_validation_start_with_details(self):
        """Test log_validation_start with details."""
        mock_logger = Mock()
        details = {"param1": "value1", "param2": "value2"}

        log_validation_start(mock_logger, "test_validation", details)

        # Should call info once for main message
        mock_logger.info.assert_called_once_with("Starting validation: test_validation")

        # Should call debug for each detail
        assert mock_logger.debug.call_count == 2
        debug_calls = [call.args[0] for call in mock_logger.debug.call_args_list]
        assert "  param1: value1" in debug_calls
        assert "  param2: value2" in debug_calls

    def test_log_validation_start_with_empty_details(self):
        """Test log_validation_start with empty details."""
        mock_logger = Mock()

        log_validation_start(mock_logger, "test_validation", {})

        mock_logger.info.assert_called_once_with("Starting validation: test_validation")
        mock_logger.debug.assert_not_called()

    def test_log_validation_start_with_none_details(self):
        """Test log_validation_start with None details."""
        mock_logger = Mock()

        log_validation_start(mock_logger, "test_validation", None)

        mock_logger.info.assert_called_once_with("Starting validation: test_validation")
        mock_logger.debug.assert_not_called()


class TestLogValidationResult:
    """Test log_validation_result function."""

    def test_log_validation_result_success(self):
        """Test log_validation_result with success."""
        mock_logger = Mock()

        log_validation_result(mock_logger, "test_validation", True, "Test passed")

        mock_logger.log.assert_called_once_with(
            logging.INFO, "Validation PASSED: test_validation - Test passed"
        )

    def test_log_validation_result_failure(self):
        """Test log_validation_result with failure."""
        mock_logger = Mock()

        log_validation_result(mock_logger, "test_validation", False, "Test failed")

        mock_logger.log.assert_called_once_with(
            logging.ERROR, "Validation FAILED: test_validation - Test failed"
        )

    def test_log_validation_result_with_duration(self):
        """Test log_validation_result with duration."""
        mock_logger = Mock()

        log_validation_result(mock_logger, "test_validation", True, "Test passed", 1500)

        mock_logger.log.assert_called_once_with(
            logging.INFO, "Validation PASSED: test_validation - Test passed (1500ms)"
        )

    def test_log_validation_result_without_duration(self):
        """Test log_validation_result without duration."""
        mock_logger = Mock()

        log_validation_result(mock_logger, "test_validation", False, "Test failed", None)

        mock_logger.log.assert_called_once_with(
            logging.ERROR, "Validation FAILED: test_validation - Test failed"
        )

    @pytest.mark.parametrize(
        "success,expected_level,expected_status",
        [
            (True, logging.INFO, "PASSED"),
            (False, logging.ERROR, "FAILED"),
        ],
    )
    def test_log_validation_result_level_and_status(self, success, expected_level, expected_status):
        """Test log_validation_result level and status mapping."""
        mock_logger = Mock()

        log_validation_result(mock_logger, "test_validation", success, "Test message")

        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == expected_level
        assert expected_status in call_args[0][1]


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    @patch("calendarbot.validation.logging_setup.logging.getLogger")
    def test_complete_logging_setup_flow(self, mock_get_logger):
        """Test complete logging setup and usage flow."""
        mock_loggers = {}

        def mock_get_logger_side_effect(name=""):
            if name not in mock_loggers:
                mock_loggers[name] = Mock()
                # Fix: Ensure handlers is a list for root logger
                if name == "":
                    mock_loggers[name].handlers = []
            return mock_loggers[name]

        mock_get_logger.side_effect = mock_get_logger_side_effect

        with patch("calendarbot.validation.logging_setup.logging.StreamHandler"):
            with patch("calendarbot.validation.logging_setup.Path") as mock_path_class:
                with patch(
                    "calendarbot.validation.logging_setup.logging.handlers.RotatingFileHandler"
                ):
                    # Mock the Path object properly
                    mock_path = Mock()
                    mock_path.parent = Mock()
                    mock_path_class.return_value = mock_path

                    # Setup logging
                    component_loggers = setup_validation_logging(
                        verbose=True,
                        components=["sources", "cache"],  # Updated component names
                        log_file="/test/validation.log",
                    )

                    # Get individual logger
                    sources_logger = get_validation_logger("sources")  # Updated component name

                    # Use logging functions
                    log_validation_start(sources_logger, "sources_test", {"detail": "value"})
                    log_validation_result(sources_logger, "sources_test", True, "Success", 250)

                    # Verify setup worked
                    assert "sources" in component_loggers  # Updated component name
                    assert sources_logger == mock_loggers["calendarbot.sources"]

    def test_formatter_with_real_log_record(self):
        """Test formatter with real LogRecord instance."""
        formatter = ValidationFormatter("%(asctime)s [%(component)s] %(levelname)s: %(message)s")

        # Create real log record
        logger = logging.getLogger("calendarbot.test")
        record = logger.makeRecord(
            "calendarbot.test", logging.INFO, __file__, 1, "Test message with %s", ("args",), None
        )
        record.msecs = 123.0

        formatted = formatter.format(record)

        assert "test" in formatted  # component
        assert "INFO" in formatted
        assert "Test message with args" in formatted

    def test_component_filter_with_real_log_record(self):
        """Test component filter with real LogRecord instance."""
        filter_instance = ComponentFilter(["auth", "system"])

        # Create real log records
        auth_logger = logging.getLogger("calendarbot.auth")
        auth_record = auth_logger.makeRecord(
            "calendarbot.auth", logging.INFO, __file__, 1, "Auth message", (), None
        )

        other_logger = logging.getLogger("other.module")
        other_record = other_logger.makeRecord(
            "other.module", logging.INFO, __file__, 1, "Other message", (), None
        )

        assert filter_instance.filter(auth_record) == True
        assert filter_instance.filter(other_record) == True  # system allowed

    @patch("calendarbot.validation.logging_setup.Path")
    def test_log_file_directory_creation(self, mock_path_class):
        """Test that log file directory is created."""
        mock_path = Mock()
        mock_path.parent = Mock()
        mock_path_class.return_value = mock_path

        with patch("calendarbot.validation.logging_setup.logging.getLogger"):
            with patch("calendarbot.validation.logging_setup.logging.handlers.RotatingFileHandler"):
                with patch("calendarbot.validation.logging_setup.logging.StreamHandler"):

                    setup_validation_logging(log_file="/test/dir/validation.log")

                    # Should create parent directory
                    mock_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_error_handling_in_formatter(self):
        """Test error handling in ValidationFormatter."""
        formatter = ValidationFormatter("%(message)s")

        # Create record with potential issue
        record = Mock()
        record.name = None  # This could cause issues
        record.msecs = "invalid"  # This could cause issues

        # Should handle gracefully - now our formatter handles None names
        with patch.object(logging.Formatter, "format", return_value="formatted"):
            result = formatter.format(record)
            assert result == "formatted"
            # Verify error handling worked - should have set component to 'system'
            assert record.component == "system"
            assert record.msecs_formatted == "000"  # Should handle invalid msecs

    def test_formatter_handles_none_msecs(self):
        """Test formatter handles None msecs value."""
        formatter = ValidationFormatter("%(message)s")

        record = Mock()
        record.name = "calendarbot.test"
        record.msecs = None  # This should trigger line 20

        with patch.object(logging.Formatter, "format", return_value="formatted"):
            result = formatter.format(record)

        assert hasattr(record, "msecs_formatted")
        assert record.msecs_formatted == "000"  # Should handle None msecs as 0
        assert record.component == "test"
        assert result == "formatted"

    def test_formatter_handles_attribute_error_in_component_extraction(self):
        """Test formatter handles AttributeError when extracting component."""
        formatter = ValidationFormatter("%(message)s")

        # Create a mock that causes AttributeError in the component extraction try block
        record = Mock()
        record.msecs = 123.0

        # Mock getattr to raise AttributeError to trigger line 33
        with patch("calendarbot.validation.logging_setup.getattr") as mock_getattr:

            def side_effect(obj, attr, default=None):
                if attr == "msecs":
                    return 123.0
                elif attr == "name":
                    raise AttributeError("name access failed")
                return default

            mock_getattr.side_effect = side_effect

            with patch.object(logging.Formatter, "format", return_value="formatted"):
                result = formatter.format(record)

                assert result == "formatted"
                assert record.component == "system"  # Should fallback to system
                assert record.msecs_formatted == "123"

    def test_formatter_handles_type_error_in_component_extraction(self):
        """Test formatter handles TypeError when extracting component."""
        formatter = ValidationFormatter("%(message)s")

        # Create a mock that causes TypeError in the component extraction try block
        record = Mock()
        record.msecs = 456.0

        # Mock getattr to raise TypeError to trigger line 34
        with patch("calendarbot.validation.logging_setup.getattr") as mock_getattr:

            def side_effect(obj, attr, default=None):
                if attr == "msecs":
                    return 456.0
                elif attr == "name":
                    raise TypeError("name type error")
                return default

            mock_getattr.side_effect = side_effect

            with patch.object(logging.Formatter, "format", return_value="formatted"):
                result = formatter.format(record)

                assert result == "formatted"
                assert record.component == "system"  # Should fallback to system
                assert record.msecs_formatted == "456"
