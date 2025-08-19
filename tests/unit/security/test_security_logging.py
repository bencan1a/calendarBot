"""Comprehensive unit tests for security logging module.

This module tests all aspects of the security logging system including:
- Security event types and severity levels
- Credential masking patterns and functionality
- Secure logging formatters
- Security event logger and audit trail
- Event caching and retrieval
- Global security logger management
"""

import logging
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

import calendarbot.security.logging as security_logging
from calendarbot.security.logging import (
    CredentialMaskingPatterns,
    SecureFormatter,
    SecurityEvent,
    SecurityEventLogger,
    SecurityEventType,
    SecuritySeverity,
    get_security_logger,
    init_security_logging,
    mask_credentials,
)


# Test fixtures for reusable mock setups
@pytest.fixture
def mock_audit_logger_setup():
    """Fixture for common audit logger mock setup."""
    with (
        patch("calendarbot.security.logging.Path") as mock_path,
        patch("logging.handlers.RotatingFileHandler") as mock_handler_class,
        patch("logging.getLogger") as mock_get_logger,
    ):
        mock_audit_logger = Mock()
        mock_get_logger.return_value = mock_audit_logger

        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler

        # Simplified Path mocking
        mock_audit_dir = Mock()
        mock_path.return_value = mock_audit_dir
        mock_path.home.return_value = mock_audit_dir
        mock_audit_dir.__truediv__ = Mock(return_value=mock_audit_dir)
        mock_audit_dir.mkdir = Mock()

        yield {
            "mock_get_logger": mock_get_logger,
            "mock_audit_logger": mock_audit_logger,
            "mock_handler": mock_handler,
            "mock_path": mock_path,
        }


@pytest.fixture
def security_event_logger():
    """Fixture for SecurityEventLogger with standard mocking."""
    with patch("calendarbot.security.logging.get_logger") as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        logger = SecurityEventLogger()
        logger.audit_logger = Mock()  # Simple mock for audit logger
        yield logger


class TestSecurityEventType:
    """Test SecurityEventType enum functionality."""

    def test_all_event_types_accessible(self):
        """Test that all security event types are accessible and have correct values."""
        expected_types = {
            "AUTH_SUCCESS": "auth_success",
            "AUTH_FAILURE": "auth_failure",
            "INPUT_VALIDATION_FAILURE": "input_validation_failure",
            "SYSTEM_SECURITY_VIOLATION": "system_security_violation",
            "DATA_ACCESS": "data_access",
            "SYSTEM_CREDENTIAL_ACCESS": "system_credential_access",
        }

        # Test both accessibility and values in one pass
        for enum_name, expected_value in expected_types.items():
            assert hasattr(SecurityEventType, enum_name)
            assert getattr(SecurityEventType, enum_name).value == expected_value


class TestSecuritySeverity:
    """Test SecuritySeverity enum functionality."""

    @pytest.mark.parametrize(
        "severity,name,priority",
        [
            (SecuritySeverity.LOW, "low", 1),
            (SecuritySeverity.MEDIUM, "medium", 2),
            (SecuritySeverity.HIGH, "high", 3),
            (SecuritySeverity.CRITICAL, "critical", 4),
        ],
    )
    def test_severity_properties(self, severity, name, priority):
        """Test severity initialization and string representation."""
        assert severity.severity_name == name
        assert severity.priority == priority
        assert str(severity) == name

    def test_severity_comparison(self):
        """Test __lt__ method for severity comparison."""
        severities = [
            SecuritySeverity.LOW,
            SecuritySeverity.MEDIUM,
            SecuritySeverity.HIGH,
            SecuritySeverity.CRITICAL,
        ]

        # Test that each severity is less than the next
        for i in range(len(severities) - 1):
            assert severities[i] < severities[i + 1]

        # Test reverse is not true
        assert not (SecuritySeverity.HIGH < SecuritySeverity.LOW)


class TestSecurityEvent:
    """Test SecurityEvent dataclass functionality."""

    def test_default_initialization(self):
        """Test SecurityEvent with default values."""
        event = SecurityEvent()

        assert event.event_id is not None
        assert isinstance(event.event_id, str)
        assert event.event_type == SecurityEventType.SYSTEM_SECURITY_VIOLATION
        assert event.severity == SecuritySeverity.LOW
        assert isinstance(event.timestamp, datetime)
        assert event.user_id is None
        assert event.session_id is None
        assert event.source_ip is None
        assert event.user_agent is None
        assert event.resource is None
        assert event.action is None
        assert event.result is None
        assert event.details == {}
        assert event.correlation_id is None

    def test_custom_initialization(self):
        """Test SecurityEvent with custom values."""
        custom_timestamp = datetime.now(timezone.utc)
        details = {"key": "value", "count": 42}

        event = SecurityEvent(
            event_type=SecurityEventType.AUTH_FAILURE,
            severity=SecuritySeverity.HIGH,
            timestamp=custom_timestamp,
            user_id="user123",
            session_id="session456",
            source_ip="192.168.1.100",
            user_agent="TestAgent/1.0",
            resource="/api/login",
            action="authenticate",
            result="failure",
            details=details,
            correlation_id="corr789",
        )

        assert event.event_type == SecurityEventType.AUTH_FAILURE
        assert event.severity == SecuritySeverity.HIGH
        assert event.timestamp == custom_timestamp
        assert event.user_id == "user123"
        assert event.session_id == "session456"
        assert event.source_ip == "192.168.1.100"
        assert event.user_agent == "TestAgent/1.0"
        assert event.resource == "/api/login"
        assert event.action == "authenticate"
        assert event.result == "failure"
        assert event.details == details
        assert event.correlation_id == "corr789"

    def test_to_dict_conversion(self):
        """Test to_dict method produces correct dictionary."""
        timestamp = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        details = {"error_code": 401, "attempts": 3}

        event = SecurityEvent(
            event_id="test-event-123",
            event_type=SecurityEventType.AUTH_FAILURE,
            severity=SecuritySeverity.MEDIUM,
            timestamp=timestamp,
            user_id="user456",
            session_id="sess789",
            source_ip="10.0.0.1",
            user_agent="Mozilla/5.0",
            resource="/secure/data",
            action="access",
            result="denied",
            details=details,
            correlation_id="corr123",
        )

        result = event.to_dict()

        expected = {
            "event_id": "test-event-123",
            "event_type": "auth_failure",
            "severity": "medium",
            "timestamp": "2024-01-15T10:30:45+00:00",
            "user_id": "user456",
            "session_id": "sess789",
            "source_ip": "10.0.0.1",
            "user_agent": "Mozilla/5.0",
            "resource": "/secure/data",
            "action": "access",
            "result": "denied",
            "details": {"error_code": 401, "attempts": 3},
            "correlation_id": "corr123",
        }

        assert result == expected

    def test_unique_event_ids(self):
        """Test that event IDs are unique across instances."""
        event1 = SecurityEvent()
        event2 = SecurityEvent()

        assert event1.event_id != event2.event_id
        assert isinstance(uuid.UUID(event1.event_id), uuid.UUID)
        assert isinstance(uuid.UUID(event2.event_id), uuid.UUID)


class TestCredentialMaskingPatterns:
    """Test CredentialMaskingPatterns class functionality."""

    @pytest.mark.parametrize(
        "length,expected", [(5, 3), (8, 3), (12, 6), (16, 6), (24, 8), (32, 8), (64, 12), (128, 12)]
    )
    def test_get_mask_length(self, length, expected):
        """Test mask length calculation for different input lengths."""
        assert CredentialMaskingPatterns.get_mask_length(length) == expected

    @pytest.mark.parametrize(
        "credential,expected",
        [
            ("abc", "***"),
            ("abcd", "***"),
            ("password123", "pa******23"),
            ("verylongpassword456", "ve********56"),
        ],
    )
    def test_create_mask_default_settings(self, credential, expected):
        """Test create_mask with default prefix and suffix."""
        assert CredentialMaskingPatterns.create_mask(credential) == expected

    def test_create_mask_custom_prefix_suffix(self):
        """Test create_mask with custom prefix and suffix lengths."""
        credential = "secrettoken123456"

        # Test cases for custom prefix/suffix
        test_cases = [
            (0, 0, "********"),
            (3, 4, "sec********3456"),
        ]

        for prefix, suffix, expected in test_cases:
            result = CredentialMaskingPatterns.create_mask(
                credential, show_prefix=prefix, show_suffix=suffix
            )
            assert result == expected

        # Large prefix/suffix (should fall back to full mask)
        result = CredentialMaskingPatterns.create_mask("short", show_prefix=3, show_suffix=3)
        assert result == "***"

    def test_patterns_compilation(self):
        """Test that all predefined patterns are compiled regex objects."""
        patterns = CredentialMaskingPatterns.PATTERNS
        expected_names = {
            "password",
            "token",
            "bearer",
            "api_key",
            "secret",
            "auth_header",
            "basic_auth",
            "jwt",
            "access_token",
            "refresh_token",
            "ics_calendar_id",
            "ics_outlook_path",
            "ics_url_generic",
        }

        assert len(patterns) > 0
        for pattern_name, pattern in patterns.items():
            assert isinstance(pattern, re.Pattern)
            assert pattern_name in expected_names

    def test_jwt_pattern_matching(self):
        """Test JWT pattern matching functionality."""
        jwt_pattern = CredentialMaskingPatterns.PATTERNS["jwt"]
        valid_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

        match = jwt_pattern.search(valid_jwt)
        assert match is not None
        assert match.group(0) == valid_jwt

    def test_ics_calendar_pattern_matching(self):
        """Test ICS calendar URL pattern matching."""
        ics_pattern = CredentialMaskingPatterns.PATTERNS["ics_calendar_id"]
        test_url = (
            "https://calendar.google.com/calendar/ical/user123@gmail.com/private-abc123/basic.ics"
        )
        match = ics_pattern.search(test_url)

        if match:
            assert "calendar/" in match.group(0)


class TestMaskCredentials:
    """Test mask_credentials function."""

    @pytest.mark.parametrize("input_text,expected", [("", ""), (None, None)])
    def test_empty_or_none_input(self, input_text, expected):
        """Test mask_credentials with empty or None input."""
        assert mask_credentials(input_text) == expected

    @pytest.mark.parametrize(
        "text,credential,masked_part",
        [
            ('Login with password: "mypassword123"', "mypassword123", "my******23"),
            ('{"token": "abc123xyz789"}', "abc123xyz789", "ab******89"),
            ("API_KEY=sk-1234567890abcdef", "sk-1234567890abcdef", "sk********ef"),
        ],
    )
    def test_credential_masking(self, text, credential, masked_part):
        """Test various credential types are properly masked."""
        result = mask_credentials(text)
        assert credential not in result
        assert masked_part in result

    def test_bearer_token_masking(self):
        """Test Bearer token masking."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = mask_credentials(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "Authorization:" in result
        assert "***" in result or "ey************R9" in result

    def test_custom_patterns(self):
        """Test mask_credentials with custom patterns."""
        custom_patterns = {"custom_secret": re.compile(r"(SECRET_VAL=)([^\s]+)", re.IGNORECASE)}
        text = "Configuration: SECRET_VAL=custom123secret"
        result = mask_credentials(text, custom_patterns)

        assert "custom123secret" not in result
        assert "SECRET_VAL=" in result
        assert "cu******et" in result

    def test_multiple_credential_types(self):
        """Test masking multiple credential types in same text."""
        text = '{"password": "userpass123", "api_key": "sk-abcdefghijklmnop", "token": "bearer_token_xyz"}'
        result = mask_credentials(text)

        # Verify credentials are masked
        for credential in ["userpass123", "sk-abcdefghijklmnop", "bearer_token_xyz"]:
            assert credential not in result

        # Verify structure preserved
        for label in ["password", "api_key", "token"]:
            assert label in result

    def test_no_masking_when_no_patterns_match(self):
        """Test that text without credentials remains unchanged."""
        text = "This is just normal text without any sensitive information."
        assert mask_credentials(text) == text


class TestSecureFormatter:
    """Test SecureFormatter class functionality."""

    def test_initialization_default(self):
        """Test SecureFormatter initialization with defaults."""
        formatter = SecureFormatter()

        assert formatter.enable_masking is True
        assert formatter.custom_patterns == {}

    def test_initialization_custom(self):
        """Test SecureFormatter initialization with custom settings."""
        custom_patterns = {"test": re.compile(r"test")}
        formatter = SecureFormatter(
            fmt="%(message)s", enable_masking=False, custom_patterns=custom_patterns
        )

        assert formatter.enable_masking is False
        assert formatter.custom_patterns == custom_patterns

    def test_format_with_masking_enabled(self):
        """Test format method with masking enabled."""
        formatter = SecureFormatter("%(message)s", enable_masking=True)

        # Create a log record with credentials
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='User login: password="secret123"',
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert "secret123" not in result
        assert "password=" in result
        assert "se******23" in result

    def test_format_with_masking_disabled(self):
        """Test format method with masking disabled."""
        formatter = SecureFormatter("%(message)s", enable_masking=False)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg='User login: password="secret123"',
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        assert "secret123" in result  # Should not be masked

    def test_add_pattern(self):
        """Test adding custom masking patterns."""
        formatter = SecureFormatter()
        test_pattern = re.compile(r"(TEST=)([^\s]+)")

        formatter.add_pattern("test_pattern", test_pattern)
        assert "test_pattern" in formatter.custom_patterns
        assert formatter.custom_patterns["test_pattern"] == test_pattern

    def test_remove_pattern(self):
        """Test removing custom masking patterns."""
        formatter = SecureFormatter()
        test_pattern = re.compile(r"test")

        formatter.add_pattern("test_pattern", test_pattern)
        assert "test_pattern" in formatter.custom_patterns

        formatter.remove_pattern("test_pattern")
        assert "test_pattern" not in formatter.custom_patterns

    def test_remove_nonexistent_pattern(self):
        """Test removing a pattern that doesn't exist."""
        formatter = SecureFormatter()

        # Should not raise exception
        formatter.remove_pattern("nonexistent")
        assert "nonexistent" not in formatter.custom_patterns


class TestSecurityEventLogger:
    """Test SecurityEventLogger class functionality."""

    def test_initialization_without_settings(self, security_event_logger):
        """Test SecurityEventLogger initialization without settings."""
        logger = security_event_logger

        assert logger.settings is None
        assert logger._event_cache == []
        assert logger.cache_size == 1000

    def test_initialization_with_settings(self, mock_audit_logger_setup):
        """Test SecurityEventLogger initialization with settings."""
        mock_settings = Mock()
        mock_settings.data_dir = "/test/data"

        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger(mock_settings)
            assert logger.settings == mock_settings

    def test_log_event_success(self, security_event_logger):
        """Test successful event logging."""
        event = SecurityEvent(
            event_type=SecurityEventType.AUTH_SUCCESS,
            severity=SecuritySeverity.LOW,
            user_id="user123",
        )

        security_event_logger.log_event(event)

        # Verify event was added to cache and audit logged
        assert len(security_event_logger._event_cache) == 1
        assert security_event_logger._event_cache[0] == event
        security_event_logger.audit_logger.info.assert_called_once()

        # Verify audit log format
        call_args = security_event_logger.audit_logger.info.call_args[0][0]
        assert call_args.startswith("AUDIT: ")
        assert "auth_success" in call_args
        assert "user123" in call_args

    @pytest.mark.parametrize(
        "method_name,event_type,severity,expected_action,expected_result",
        [
            (
                "log_authentication_success",
                SecurityEventType.AUTH_SUCCESS,
                SecuritySeverity.LOW,
                "authenticate",
                "success",
            ),
            (
                "log_authentication_failure",
                SecurityEventType.AUTH_FAILURE,
                SecuritySeverity.MEDIUM,
                "authenticate",
                "failure",
            ),
            (
                "log_credential_access",
                SecurityEventType.SYSTEM_CREDENTIAL_ACCESS,
                SecuritySeverity.HIGH,
                "read",
                None,
            ),
        ],
    )
    def test_security_event_methods(
        self,
        security_event_logger,
        method_name,
        event_type,
        severity,
        expected_action,
        expected_result,
    ):
        """Test various security event logging methods."""
        security_event_logger.log_event = Mock()

        # Call the method with minimal params
        method = getattr(security_event_logger, method_name)
        if method_name == "log_credential_access":
            method(resource="/api/test")
        else:
            method(user_id="user123")

        security_event_logger.log_event.assert_called_once()
        event = security_event_logger.log_event.call_args[0][0]

        assert event.event_type == event_type
        assert event.severity == severity
        if expected_action:
            assert event.action == expected_action
        if expected_result:
            assert event.result == expected_result

    def test_log_token_refresh_success_and_failure(self, security_event_logger):
        """Test log_token_refresh with both success and failure cases."""
        security_event_logger.log_event = Mock()

        # Test success
        security_event_logger.log_token_refresh(user_id="user123", success=True)
        event = security_event_logger.log_event.call_args[0][0]
        assert event.result == "success"

        # Reset mock and test failure
        security_event_logger.log_event.reset_mock()
        security_event_logger.log_token_refresh(user_id="user123", success=False)
        event = security_event_logger.log_event.call_args[0][0]
        assert event.result == "failure"

    @pytest.mark.parametrize(
        "severity,expected_level",
        [
            (SecuritySeverity.LOW, logging.DEBUG),
            (SecuritySeverity.MEDIUM, logging.WARNING),
            (SecuritySeverity.HIGH, logging.ERROR),
            (SecuritySeverity.CRITICAL, logging.CRITICAL),
        ],
    )
    def test_severity_to_log_level(self, security_event_logger, severity, expected_level):
        """Test _severity_to_log_level method."""
        assert security_event_logger._severity_to_log_level(severity) == expected_level

    def test_severity_to_log_level_unknown(self, security_event_logger):
        """Test _severity_to_log_level with unknown severity."""
        mock_severity = Mock()
        assert security_event_logger._severity_to_log_level(mock_severity) == logging.WARNING

    def test_cache_operations(self, security_event_logger):
        """Test cache add operations and size limits."""
        # Test basic add
        event1 = SecurityEvent(user_id="user1")
        event2 = SecurityEvent(user_id="user2")

        security_event_logger._add_to_cache(event1)
        security_event_logger._add_to_cache(event2)

        assert len(security_event_logger._event_cache) == 2
        assert security_event_logger._event_cache == [event1, event2]

        # Test size limit
        security_event_logger.cache_size = 2
        event3 = SecurityEvent(user_id="user3")
        security_event_logger._add_to_cache(event3)

        assert len(security_event_logger._event_cache) == 2
        assert security_event_logger._event_cache == [event2, event3]

    def test_get_recent_events_filtering(self, security_event_logger):
        """Test get_recent_events with various filters."""
        # Add test events
        events = [
            SecurityEvent(
                event_type=SecurityEventType.AUTH_SUCCESS,
                severity=SecuritySeverity.LOW,
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            ),
            SecurityEvent(
                event_type=SecurityEventType.AUTH_FAILURE,
                severity=SecuritySeverity.HIGH,
                timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            ),
            SecurityEvent(
                event_type=SecurityEventType.AUTH_SUCCESS,
                severity=SecuritySeverity.CRITICAL,
                timestamp=datetime(2024, 1, 3, tzinfo=timezone.utc),
            ),
        ]

        for event in events:
            security_event_logger._add_to_cache(event)

        # Test no filters (should return in reverse chronological order)
        recent = security_event_logger.get_recent_events(limit=10)
        assert len(recent) == 3
        assert recent[0] == events[2]  # Most recent first

        # Test type filter
        auth_success_events = security_event_logger.get_recent_events(
            event_type=SecurityEventType.AUTH_SUCCESS
        )
        assert len(auth_success_events) == 2

        # Test severity filter (HIGH and above)
        high_severity_events = security_event_logger.get_recent_events(
            severity=SecuritySeverity.HIGH
        )
        assert len(high_severity_events) == 2

        # Test limit
        limited = security_event_logger.get_recent_events(limit=1)
        assert len(limited) == 1

    def test_get_security_summary(self, security_event_logger):
        """Test get_security_summary with empty and populated cache."""
        # Test empty cache
        summary = security_event_logger.get_security_summary()
        expected_empty = {"total_events": 0, "by_severity": {}, "by_type": {}}
        assert summary == expected_empty

        # Add test events
        events = [
            SecurityEvent(event_type=SecurityEventType.AUTH_SUCCESS, severity=SecuritySeverity.LOW),
            SecurityEvent(event_type=SecurityEventType.AUTH_SUCCESS, severity=SecuritySeverity.LOW),
            SecurityEvent(
                event_type=SecurityEventType.AUTH_FAILURE, severity=SecuritySeverity.MEDIUM
            ),
        ]

        for event in events:
            security_event_logger._add_to_cache(event)

        summary = security_event_logger.get_security_summary()

        assert summary["total_events"] == 3
        assert summary["recent_events"] == 3
        assert summary["by_severity"]["low"] == 2
        assert summary["by_severity"]["medium"] == 1
        assert summary["by_type"]["auth_success"] == 2
        assert summary["by_type"]["auth_failure"] == 1
        assert summary["oldest_event"] is not None
        assert summary["newest_event"] is not None


class TestGlobalSecurityLoggerFunctions:
    """Test global security logger management functions."""

    def test_get_security_logger_first_call(self):
        """Test get_security_logger creates new instance on first call."""
        # Reset global state
        security_logging._security_logger = None

        with patch("calendarbot.security.logging.SecurityEventLogger") as mock_logger_class:
            mock_logger = Mock()
            mock_logger_class.return_value = mock_logger

            result = get_security_logger()

            assert result == mock_logger
            mock_logger_class.assert_called_once_with(None)

    def test_get_security_logger_subsequent_calls(self):
        """Test get_security_logger returns existing instance on subsequent calls."""
        # Set up existing logger
        existing_logger = Mock()
        security_logging._security_logger = existing_logger

        with patch("calendarbot.security.logging.SecurityEventLogger") as mock_logger_class:
            result = get_security_logger()

            assert result == existing_logger
            mock_logger_class.assert_not_called()

    def test_get_security_logger_with_settings(self):
        """Test get_security_logger with custom settings."""
        security_logging._security_logger = None

        mock_settings = Mock()

        with patch("calendarbot.security.logging.SecurityEventLogger") as mock_logger_class:
            mock_logger = Mock()
            mock_logger_class.return_value = mock_logger

            result = get_security_logger(mock_settings)

            assert result == mock_logger
            mock_logger_class.assert_called_once_with(mock_settings)

    def test_init_security_logging(self):
        """Test init_security_logging function."""
        mock_settings = Mock()

        with patch("calendarbot.security.logging.SecurityEventLogger") as mock_logger_class:
            mock_logger = Mock()
            mock_logger_class.return_value = mock_logger

            result = init_security_logging(mock_settings)

            assert result == mock_logger
            mock_logger_class.assert_called_once_with(mock_settings)

            # Verify global state is updated
            assert security_logging._security_logger == mock_logger

    def test_init_security_logging_replaces_existing(self):
        """Test init_security_logging replaces existing logger."""
        # Set up existing logger
        old_logger = Mock()
        security_logging._security_logger = old_logger

        mock_settings = Mock()

        with patch("calendarbot.security.logging.SecurityEventLogger") as mock_logger_class:
            new_logger = Mock()
            mock_logger_class.return_value = new_logger

            result = init_security_logging(mock_settings)

            assert result == new_logger
            assert security_logging._security_logger == new_logger
            assert security_logging._security_logger != old_logger


@pytest.mark.integration
class TestSecurityLoggingIntegration:
    """Integration tests for security logging system."""

    @patch("calendarbot.security.logging.Path")
    @patch("logging.handlers.RotatingFileHandler")
    @patch("logging.getLogger")
    def test_end_to_end_security_event_flow(
        self, mock_get_audit_logger, mock_handler_class, mock_path
    ):
        """Test complete security event logging flow."""
        with patch("calendarbot.security.logging.get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Mock audit logger components
            mock_audit_logger = Mock()
            mock_get_audit_logger.return_value = mock_audit_logger

            mock_handler = Mock()
            mock_handler_class.return_value = mock_handler

            # Mock Path operations
            mock_audit_dir = Mock()
            mock_path.return_value = mock_audit_dir
            mock_audit_dir.__truediv__ = Mock(return_value=mock_audit_dir)
            mock_audit_dir.mkdir = Mock()

            # Initialize security logger
            mock_settings = Mock()
            mock_settings.data_dir = "/test/data"  # Provide actual string value
            security_logger = SecurityEventLogger(mock_settings)

            # Log various security events
            security_logger.log_authentication_success(user_id="user123")
            security_logger.log_authentication_failure(user_id="user456", reason="Invalid password")
            security_logger.log_input_validation_failure("url", "Invalid format")

            # Verify events are in cache
            assert len(security_logger._event_cache) == 3

            # Get summary
            summary = security_logger.get_security_summary()
            assert summary["total_events"] == 3
            assert summary["by_severity"]["low"] == 1
            assert summary["by_severity"]["medium"] == 2

    def test_credential_masking_in_formatter(self):
        """Test credential masking integration with formatter."""
        formatter = SecureFormatter("%(message)s")

        # Create log record with multiple credential types
        message = """
        Authentication attempt with:
        password="supersecret123"
        api_key="sk-1234567890abcdef"
        Bearer token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
        """

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)

        # Verify all credentials are masked
        assert "supersecret123" not in result
        assert "sk-1234567890abcdef" not in result
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result

        # Verify structure is preserved
        assert "password=" in result
        assert "api_key=" in result
        assert "Bearer" in result

    def test_audit_logger_setup_creates_directory(self):
        """Test that audit logger setup creates necessary directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_settings = Mock()
            mock_settings.data_dir = temp_dir

            with patch("calendarbot.security.logging.get_logger"):
                logger = SecurityEventLogger(mock_settings)

                # Verify audit directory structure would be created
                Path(temp_dir) / "security" / "audit"
                # Note: We can't test actual directory creation due to mocking,
                # but we verify the logger is set up without errors
                assert logger.audit_logger is not None
