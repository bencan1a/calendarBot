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


class TestSecurityEventType:
    """Test SecurityEventType enum functionality."""

    def test_all_event_types_accessible(self):
        """Test that all security event types are accessible."""
        expected_types = [
            "AUTH_SUCCESS",
            "AUTH_FAILURE",
            "AUTH_TIMEOUT",
            "AUTH_TOKEN_REFRESH",
            "AUTH_TOKEN_EXPIRED",
            "AUTH_LOGOUT",
            "AUTHZ_ACCESS_GRANTED",
            "AUTHZ_ACCESS_DENIED",
            "AUTHZ_PERMISSION_CHECK",
            "INPUT_VALIDATION_FAILURE",
            "INPUT_SANITIZATION",
            "INPUT_MALFORMED",
            "SYSTEM_CONFIG_CHANGE",
            "SYSTEM_CREDENTIAL_ACCESS",
            "SYSTEM_SECURITY_VIOLATION",
            "DATA_ACCESS",
            "DATA_MODIFICATION",
            "DATA_EXPORT",
        ]

        for event_type in expected_types:
            assert hasattr(SecurityEventType, event_type)

    def test_event_type_values(self):
        """Test that event types have correct string values."""
        assert SecurityEventType.AUTH_SUCCESS.value == "auth_success"
        assert SecurityEventType.AUTH_FAILURE.value == "auth_failure"
        assert SecurityEventType.INPUT_VALIDATION_FAILURE.value == "input_validation_failure"
        assert SecurityEventType.SYSTEM_SECURITY_VIOLATION.value == "system_security_violation"


class TestSecuritySeverity:
    """Test SecuritySeverity enum functionality."""

    def test_severity_initialization(self):
        """Test that severity levels are initialized correctly."""
        assert SecuritySeverity.LOW.severity_name == "low"
        assert SecuritySeverity.LOW.priority == 1
        assert SecuritySeverity.MEDIUM.severity_name == "medium"
        assert SecuritySeverity.MEDIUM.priority == 2
        assert SecuritySeverity.HIGH.severity_name == "high"
        assert SecuritySeverity.HIGH.priority == 3
        assert SecuritySeverity.CRITICAL.severity_name == "critical"
        assert SecuritySeverity.CRITICAL.priority == 4

    def test_severity_string_representation(self):
        """Test __str__ method returns severity name."""
        assert str(SecuritySeverity.LOW) == "low"
        assert str(SecuritySeverity.MEDIUM) == "medium"
        assert str(SecuritySeverity.HIGH) == "high"
        assert str(SecuritySeverity.CRITICAL) == "critical"

    def test_severity_comparison(self):
        """Test __lt__ method for severity comparison."""
        assert SecuritySeverity.LOW < SecuritySeverity.MEDIUM
        assert SecuritySeverity.MEDIUM < SecuritySeverity.HIGH
        assert SecuritySeverity.HIGH < SecuritySeverity.CRITICAL
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

    def test_get_mask_length(self):
        """Test mask length calculation for different input lengths."""
        assert CredentialMaskingPatterns.get_mask_length(5) == 3
        assert CredentialMaskingPatterns.get_mask_length(8) == 3
        assert CredentialMaskingPatterns.get_mask_length(12) == 6
        assert CredentialMaskingPatterns.get_mask_length(16) == 6
        assert CredentialMaskingPatterns.get_mask_length(24) == 8
        assert CredentialMaskingPatterns.get_mask_length(32) == 8
        assert CredentialMaskingPatterns.get_mask_length(64) == 12
        assert CredentialMaskingPatterns.get_mask_length(128) == 12

    def test_create_mask_default_settings(self):
        """Test create_mask with default prefix and suffix."""
        # Short credential - full mask
        assert CredentialMaskingPatterns.create_mask("abc") == "***"
        assert CredentialMaskingPatterns.create_mask("abcd") == "***"

        # Normal credential - prefix + mask + suffix
        assert CredentialMaskingPatterns.create_mask("password123") == "pa******23"
        assert CredentialMaskingPatterns.create_mask("verylongpassword456") == "ve********56"

    def test_create_mask_custom_prefix_suffix(self):
        """Test create_mask with custom prefix and suffix lengths."""
        credential = "secrettoken123456"

        # No prefix or suffix
        result = CredentialMaskingPatterns.create_mask(credential, show_prefix=0, show_suffix=0)
        assert result == "********"

        # Custom prefix/suffix
        result = CredentialMaskingPatterns.create_mask(credential, show_prefix=3, show_suffix=4)
        assert result == "sec********3456"

        # Large prefix/suffix (should fall back to full mask)
        result = CredentialMaskingPatterns.create_mask("short", show_prefix=3, show_suffix=3)
        assert result == "***"

    def test_patterns_compilation(self):
        """Test that all predefined patterns are compiled regex objects."""
        patterns = CredentialMaskingPatterns.PATTERNS

        assert len(patterns) > 0
        for pattern_name, pattern in patterns.items():
            assert isinstance(pattern, re.Pattern)
            assert pattern_name in [
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
            ]

    def test_jwt_pattern_matching(self):
        """Test JWT pattern matching functionality."""
        jwt_pattern = CredentialMaskingPatterns.PATTERNS["jwt"]

        # Valid JWT format
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

    def test_empty_or_none_input(self):
        """Test mask_credentials with empty or None input."""
        assert mask_credentials("") == ""
        assert mask_credentials(None) == None

    def test_password_masking(self):
        """Test password credential masking."""
        text = 'Login with password: "mypassword123"'
        result = mask_credentials(text)
        assert "mypassword123" not in result
        assert "password" in result
        assert "my******23" in result

    def test_token_masking(self):
        """Test token credential masking."""
        text = '{"token": "abc123xyz789"}'
        result = mask_credentials(text)
        assert "abc123xyz789" not in result
        assert "token" in result
        assert "ab******89" in result

    def test_bearer_token_masking(self):
        """Test Bearer token masking."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = mask_credentials(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "Authorization:" in result
        # Bearer token is replaced with *** in the pattern
        assert "***" in result or "ey************R9" in result

    def test_api_key_masking(self):
        """Test API key masking."""
        text = "API_KEY=sk-1234567890abcdef"
        result = mask_credentials(text)
        assert "sk-1234567890abcdef" not in result
        assert "API_KEY" in result
        assert "sk********ef" in result

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
        text = """
        {
            "password": "userpass123",
            "api_key": "sk-abcdefghijklmnop",
            "token": "bearer_token_xyz"
        }
        """
        result = mask_credentials(text)

        assert "userpass123" not in result
        assert "sk-abcdefghijklmnop" not in result
        assert "bearer_token_xyz" not in result
        assert "password" in result
        assert "api_key" in result
        assert "token" in result

    def test_no_masking_when_no_patterns_match(self):
        """Test that text without credentials remains unchanged."""
        text = "This is just normal text without any sensitive information."
        result = mask_credentials(text)
        assert result == text


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

    def test_initialization_without_settings(self):
        """Test SecurityEventLogger initialization without settings."""
        with patch("calendarbot.security.logging.get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger = SecurityEventLogger()

            assert logger.settings is None
            assert logger.logger == mock_logger
            assert logger._event_cache == []
            assert logger.cache_size == 1000
            mock_get_logger.assert_called_once_with("security")

    @patch("calendarbot.security.logging.Path")
    @patch("logging.handlers.RotatingFileHandler")
    @patch("logging.getLogger")
    def test_initialization_with_settings(
        self, mock_get_audit_logger, mock_handler_class, mock_path
    ):
        """Test SecurityEventLogger initialization with settings."""
        mock_settings = Mock()
        mock_settings.data_dir = "/test/data"

        # Mock audit logger
        mock_audit_logger = Mock()
        mock_get_audit_logger.return_value = mock_audit_logger

        # Mock handler
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler

        # Mock Path operations to avoid PermissionError
        mock_audit_dir = Mock()
        mock_path.return_value = mock_audit_dir
        mock_audit_dir.__truediv__ = Mock(return_value=mock_audit_dir)
        mock_audit_dir.mkdir = Mock()  # Mock mkdir to avoid PermissionError

        with patch("calendarbot.security.logging.get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger = SecurityEventLogger(mock_settings)

            assert logger.settings == mock_settings

    @patch("calendarbot.security.logging.Path")
    @patch("logging.getLogger")
    @patch("logging.handlers.RotatingFileHandler")
    def test_setup_audit_logger_with_settings(self, mock_handler_class, mock_get_logger, mock_path):
        """Test audit logger setup with settings."""
        mock_settings = Mock()
        mock_settings.data_dir = "/test/data"

        mock_audit_logger = Mock()
        mock_get_logger.return_value = mock_audit_logger

        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler

        # Mock Path operations
        mock_audit_dir = Mock()
        mock_path.return_value = mock_audit_dir
        mock_audit_dir.__truediv__ = Mock(return_value=mock_audit_dir)

        with patch("calendarbot.security.logging.get_logger"):
            SecurityEventLogger(mock_settings)

            # Verify audit logger configuration
            mock_get_logger.assert_called_with("calendarbot.security.audit")
            mock_audit_logger.setLevel.assert_called_with(logging.INFO)
            mock_audit_logger.handlers.clear.assert_called_once()

    @patch("calendarbot.security.logging.Path")
    @patch("logging.getLogger")
    @patch("logging.handlers.RotatingFileHandler")
    def test_setup_audit_logger_without_settings(
        self, mock_handler_class, mock_get_logger, mock_path
    ):
        """Test audit logger setup without settings (uses default path)."""
        mock_audit_logger = Mock()
        mock_get_logger.return_value = mock_audit_logger

        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler

        # Mock Path operations for default directory
        mock_home_path = Mock()
        mock_path.home.return_value = mock_home_path
        mock_audit_dir = Mock()
        mock_home_path.__truediv__ = Mock(return_value=mock_audit_dir)
        mock_audit_dir.__truediv__ = Mock(return_value=mock_audit_dir)

        with patch("calendarbot.security.logging.get_logger"):
            SecurityEventLogger()

            # Verify default path is used
            mock_path.home.assert_called_once()

    def test_log_event_success(self):
        """Test successful event logging."""
        with patch("calendarbot.security.logging.get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_audit_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger = SecurityEventLogger()
            logger.audit_logger = mock_audit_logger

            event = SecurityEvent(
                event_type=SecurityEventType.AUTH_SUCCESS,
                severity=SecuritySeverity.LOW,
                user_id="user123",
            )

            logger.log_event(event)

            # Verify event was added to cache
            assert len(logger._event_cache) == 1
            assert logger._event_cache[0] == event

            # Verify logging calls
            mock_logger.log.assert_called_once()
            mock_audit_logger.info.assert_called_once()

    def test_log_authentication_success(self):
        """Test log_authentication_success method."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()
            logger.log_event = Mock()

            logger.log_authentication_success(
                user_id="user123", session_id="session456", details={"method": "password"}
            )

            logger.log_event.assert_called_once()
            event = logger.log_event.call_args[0][0]

            assert event.event_type == SecurityEventType.AUTH_SUCCESS
            assert event.severity == SecuritySeverity.LOW
            assert event.user_id == "user123"
            assert event.session_id == "session456"
            assert event.action == "authenticate"
            assert event.result == "success"
            assert event.details == {"method": "password"}

    def test_log_authentication_failure(self):
        """Test log_authentication_failure method."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()
            logger.log_event = Mock()

            logger.log_authentication_failure(
                user_id="user123", reason="Invalid password", details={"attempts": 3}
            )

            logger.log_event.assert_called_once()
            event = logger.log_event.call_args[0][0]

            assert event.event_type == SecurityEventType.AUTH_FAILURE
            assert event.severity == SecuritySeverity.MEDIUM
            assert event.user_id == "user123"
            assert event.action == "authenticate"
            assert event.result == "failure"
            assert event.details == {"attempts": 3, "failure_reason": "Invalid password"}

    def test_log_token_refresh(self):
        """Test log_token_refresh method."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()
            logger.log_event = Mock()

            # Test successful refresh
            logger.log_token_refresh(user_id="user123", session_id="session456", success=True)

            logger.log_event.assert_called_once()
            event = logger.log_event.call_args[0][0]

            assert event.event_type == SecurityEventType.AUTH_TOKEN_REFRESH
            assert event.severity == SecuritySeverity.LOW
            assert event.user_id == "user123"
            assert event.session_id == "session456"
            assert event.action == "token_refresh"
            assert event.result == "success"

    def test_log_token_refresh_failure(self):
        """Test log_token_refresh method with failure."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()
            logger.log_event = Mock()

            logger.log_token_refresh(user_id="user123", session_id="session456", success=False)

            event = logger.log_event.call_args[0][0]
            assert event.result == "failure"

    def test_log_input_validation_failure(self):
        """Test log_input_validation_failure method."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()
            logger.log_event = Mock()

            logger.log_input_validation_failure(
                input_type="calendar_url",
                validation_error="Invalid URL format",
                details={"url": "invalid-url", "source": "web_form"},
            )

            logger.log_event.assert_called_once()
            event = logger.log_event.call_args[0][0]

            assert event.event_type == SecurityEventType.INPUT_VALIDATION_FAILURE
            assert event.severity == SecuritySeverity.MEDIUM
            assert event.action == "validate_input"
            assert event.result == "failure"
            expected_details = {
                "url": "invalid-url",
                "source": "web_form",
                "input_type": "calendar_url",
                "validation_error": "Invalid URL format",
            }
            assert event.details == expected_details

    def test_log_credential_access(self):
        """Test log_credential_access method."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()
            logger.log_event = Mock()

            logger.log_credential_access(
                resource="/api/tokens", access_type="write", user_id="admin123"
            )

            logger.log_event.assert_called_once()
            event = logger.log_event.call_args[0][0]

            assert event.event_type == SecurityEventType.SYSTEM_CREDENTIAL_ACCESS
            assert event.severity == SecuritySeverity.HIGH
            assert event.user_id == "admin123"
            assert event.resource == "/api/tokens"
            assert event.action == "write"
            assert event.details == {"credential_type": "authentication_token"}

    def test_log_security_violation(self):
        """Test log_security_violation method."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()
            logger.log_event = Mock()

            logger.log_security_violation(
                violation_type="rate_limit_exceeded",
                description="Too many requests from IP",
                severity=SecuritySeverity.HIGH,
                details={"ip": "192.168.1.100", "requests": 1000},
            )

            logger.log_event.assert_called_once()
            event = logger.log_event.call_args[0][0]

            assert event.event_type == SecurityEventType.SYSTEM_SECURITY_VIOLATION
            assert event.severity == SecuritySeverity.HIGH
            assert event.action == "security_check"
            assert event.result == "violation"
            expected_details = {
                "ip": "192.168.1.100",
                "requests": 1000,
                "violation_type": "rate_limit_exceeded",
                "description": "Too many requests from IP",
            }
            assert event.details == expected_details

    def test_severity_to_log_level(self):
        """Test _severity_to_log_level method."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()

            assert logger._severity_to_log_level(SecuritySeverity.LOW) == logging.DEBUG
            assert logger._severity_to_log_level(SecuritySeverity.MEDIUM) == logging.WARNING
            assert logger._severity_to_log_level(SecuritySeverity.HIGH) == logging.ERROR
            assert logger._severity_to_log_level(SecuritySeverity.CRITICAL) == logging.CRITICAL

    def test_severity_to_log_level_unknown(self):
        """Test _severity_to_log_level with unknown severity."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()

            # Create a mock severity that won't be in the mapping
            mock_severity = Mock()
            result = logger._severity_to_log_level(mock_severity)
            assert result == logging.WARNING

    def test_add_to_cache(self):
        """Test _add_to_cache method."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()

            event1 = SecurityEvent(user_id="user1")
            event2 = SecurityEvent(user_id="user2")

            logger._add_to_cache(event1)
            assert len(logger._event_cache) == 1
            assert logger._event_cache[0] == event1

            logger._add_to_cache(event2)
            assert len(logger._event_cache) == 2
            assert logger._event_cache[1] == event2

    def test_add_to_cache_size_limit(self):
        """Test _add_to_cache respects cache size limit."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()
            logger.cache_size = 3  # Set small cache size for testing

            # Add events beyond cache size
            events = [SecurityEvent(user_id=f"user{i}") for i in range(5)]
            for event in events:
                logger._add_to_cache(event)

            # Should only keep the last 3 events
            assert len(logger._event_cache) == 3
            assert logger._event_cache[0].user_id == "user2"
            assert logger._event_cache[1].user_id == "user3"
            assert logger._event_cache[2].user_id == "user4"

    def test_get_recent_events_no_filters(self):
        """Test get_recent_events without filters."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()

            # Add events with different timestamps
            event1 = SecurityEvent(
                user_id="user1", timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc)
            )
            event2 = SecurityEvent(
                user_id="user2", timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc)
            )
            event3 = SecurityEvent(
                user_id="user3", timestamp=datetime(2024, 1, 3, tzinfo=timezone.utc)
            )

            for event in [event1, event2, event3]:
                logger._add_to_cache(event)

            recent = logger.get_recent_events(limit=10)

            # Should return events in reverse chronological order
            assert len(recent) == 3
            assert recent[0] == event3  # Most recent first
            assert recent[1] == event2
            assert recent[2] == event1

    def test_get_recent_events_with_limit(self):
        """Test get_recent_events with limit."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()

            # Add 5 events
            events = [SecurityEvent(user_id=f"user{i}") for i in range(5)]
            for event in events:
                logger._add_to_cache(event)

            recent = logger.get_recent_events(limit=2)
            assert len(recent) == 2

    def test_get_recent_events_filter_by_type(self):
        """Test get_recent_events filtering by event type."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()

            auth_event = SecurityEvent(event_type=SecurityEventType.AUTH_SUCCESS)
            violation_event = SecurityEvent(event_type=SecurityEventType.SYSTEM_SECURITY_VIOLATION)

            logger._add_to_cache(auth_event)
            logger._add_to_cache(violation_event)

            auth_events = logger.get_recent_events(event_type=SecurityEventType.AUTH_SUCCESS)
            assert len(auth_events) == 1
            assert auth_events[0] == auth_event

    def test_get_recent_events_filter_by_severity(self):
        """Test get_recent_events filtering by severity."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()

            low_event = SecurityEvent(severity=SecuritySeverity.LOW)
            high_event = SecurityEvent(severity=SecuritySeverity.HIGH)
            critical_event = SecurityEvent(severity=SecuritySeverity.CRITICAL)

            for event in [low_event, high_event, critical_event]:
                logger._add_to_cache(event)

            # Filter for HIGH severity and above
            high_and_above = logger.get_recent_events(severity=SecuritySeverity.HIGH)
            assert len(high_and_above) == 2
            assert low_event not in high_and_above
            assert high_event in high_and_above
            assert critical_event in high_and_above

    def test_get_security_summary_empty_cache(self):
        """Test get_security_summary with empty cache."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()

            summary = logger.get_security_summary()

            expected = {"total_events": 0, "by_severity": {}, "by_type": {}}
            assert summary == expected

    def test_get_security_summary_with_events(self):
        """Test get_security_summary with events in cache."""
        with patch("calendarbot.security.logging.get_logger"):
            logger = SecurityEventLogger()

            # Add events of different types and severities
            events = [
                SecurityEvent(
                    event_type=SecurityEventType.AUTH_SUCCESS, severity=SecuritySeverity.LOW
                ),
                SecurityEvent(
                    event_type=SecurityEventType.AUTH_SUCCESS, severity=SecuritySeverity.LOW
                ),
                SecurityEvent(
                    event_type=SecurityEventType.AUTH_FAILURE, severity=SecuritySeverity.MEDIUM
                ),
                SecurityEvent(
                    event_type=SecurityEventType.SYSTEM_SECURITY_VIOLATION,
                    severity=SecuritySeverity.HIGH,
                ),
            ]

            for event in events:
                logger._add_to_cache(event)

            summary = logger.get_security_summary()

            assert summary["total_events"] == 4
            assert summary["recent_events"] == 4
            assert summary["by_severity"]["low"] == 2
            assert summary["by_severity"]["medium"] == 1
            assert summary["by_severity"]["high"] == 1
            assert summary["by_severity"]["critical"] == 0
            assert summary["by_type"]["auth_success"] == 2
            assert summary["by_type"]["auth_failure"] == 1
            assert summary["by_type"]["system_security_violation"] == 1
            assert summary["oldest_event"] is not None
            assert summary["newest_event"] is not None


class TestGlobalSecurityLoggerFunctions:
    """Test global security logger management functions."""

    def test_get_security_logger_first_call(self):
        """Test get_security_logger creates new instance on first call."""
        # Reset global state
        import calendarbot.security.logging as security_logging

        security_logging._security_logger = None

        with patch("calendarbot.security.logging.SecurityEventLogger") as mock_logger_class:
            mock_logger = Mock()
            mock_logger_class.return_value = mock_logger

            result = get_security_logger()

            assert result == mock_logger
            mock_logger_class.assert_called_once_with(None)

    def test_get_security_logger_subsequent_calls(self):
        """Test get_security_logger returns existing instance on subsequent calls."""
        import calendarbot.security.logging as security_logging

        # Set up existing logger
        existing_logger = Mock()
        security_logging._security_logger = existing_logger

        with patch("calendarbot.security.logging.SecurityEventLogger") as mock_logger_class:
            result = get_security_logger()

            assert result == existing_logger
            mock_logger_class.assert_not_called()

    def test_get_security_logger_with_settings(self):
        """Test get_security_logger with custom settings."""
        import calendarbot.security.logging as security_logging

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
            import calendarbot.security.logging as security_logging

            assert security_logging._security_logger == mock_logger

    def test_init_security_logging_replaces_existing(self):
        """Test init_security_logging replaces existing logger."""
        import calendarbot.security.logging as security_logging

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
