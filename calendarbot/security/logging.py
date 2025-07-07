"""Comprehensive security logging and credential masking system."""

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern

# Lazy import moved to function level to avoid circular dependency


class SecurityEventType(Enum):
    """Security event types for classification."""

    # Authentication Events
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    AUTH_TIMEOUT = "auth_timeout"
    AUTH_TOKEN_REFRESH = "auth_token_refresh"
    AUTH_TOKEN_EXPIRED = "auth_token_expired"
    AUTH_LOGOUT = "auth_logout"

    # Authorization Events
    AUTHZ_ACCESS_GRANTED = "authz_access_granted"
    AUTHZ_ACCESS_DENIED = "authz_access_denied"
    AUTHZ_PERMISSION_CHECK = "authz_permission_check"

    # Input Validation Events
    INPUT_VALIDATION_FAILURE = "input_validation_failure"
    INPUT_SANITIZATION = "input_sanitization"
    INPUT_MALFORMED = "input_malformed"

    # System Security Events
    SYSTEM_CONFIG_CHANGE = "system_config_change"
    SYSTEM_CREDENTIAL_ACCESS = "system_credential_access"
    SYSTEM_SECURITY_VIOLATION = "system_security_violation"

    # Data Security Events
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_EXPORT = "data_export"


class SecuritySeverity(Enum):
    """Security event severity levels."""

    LOW = ("low", 1)
    MEDIUM = ("medium", 2)
    HIGH = ("high", 3)
    CRITICAL = ("critical", 4)

    def __init__(self, name: str, priority: int):
        self.severity_name = name
        self.priority = priority

    def __str__(self):
        return self.severity_name

    def __lt__(self, other):
        return self.priority < other.priority


@dataclass
class SecurityEvent:
    """Structured security event data."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: SecurityEventType = SecurityEventType.SYSTEM_SECURITY_VIOLATION
    severity: SecuritySeverity = SecuritySeverity.LOW
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert security event to dictionary for logging."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "severity": self.severity.severity_name,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "source_ip": self.source_ip,
            "user_agent": self.user_agent,
            "resource": self.resource,
            "action": self.action,
            "result": self.result,
            "details": self.details,
            "correlation_id": self.correlation_id,
        }


class CredentialMaskingPatterns:
    """Predefined patterns for credential detection and masking."""

    # Compiled regex patterns for various credential types
    PATTERNS: Dict[str, Pattern] = {
        "password": re.compile(r'(password["\s]*[:=]["\s]*)([^"\s,}]+)', re.IGNORECASE),
        "token": re.compile(r'(token["\s]*[:=]["\s]*)([^"\s,}]+)', re.IGNORECASE),
        "bearer": re.compile(r'(bearer["\s]+)([a-zA-Z0-9._-]+)', re.IGNORECASE),
        "api_key": re.compile(r'(api[_-]?key["\s]*[:=]["\s]*)([^"\s,}]+)', re.IGNORECASE),
        "secret": re.compile(r'(secret["\s]*[:=]["\s]*)([^"\s,}]+)', re.IGNORECASE),
        "auth_header": re.compile(
            r'(authorization["\s]*[:=]["\s]*["\']?)([^"\'}\s,]+)', re.IGNORECASE
        ),
        "basic_auth": re.compile(r'(basic["\s]+)([a-zA-Z0-9+/]+=*)', re.IGNORECASE),
        "jwt": re.compile(r"(eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)", re.IGNORECASE),
        "access_token": re.compile(r'(access[_-]?token["\s]*[:=]["\s]*)([^"\s,}]+)', re.IGNORECASE),
        "refresh_token": re.compile(
            r'(refresh[_-]?token["\s]*[:=]["\s]*)([^"\s,}]+)', re.IGNORECASE
        ),
        # ICS Calendar URL patterns - mask calendar IDs and sensitive path components
        "ics_calendar_id": re.compile(r"(calendar/)([a-fA-F0-9-]+@[^/]+)(/)", re.IGNORECASE),
        "ics_outlook_path": re.compile(
            r"(outlook\.office365\.com/owa/calendar/)([a-fA-F0-9-]+@[^/]+/[a-fA-F0-9/]+)(/calendar\.ics)",
            re.IGNORECASE,
        ),
        "ics_url_generic": re.compile(
            r'(ics[_-]?url["\s]*[:=]["\s]*["\']?https?://[^/]+/)([^"\'}\s,/]+)(/[^"\'}\s,]*)',
            re.IGNORECASE,
        ),
    }

    @classmethod
    def get_mask_length(cls, original_length: int) -> int:
        """Calculate appropriate mask length based on original credential length."""
        if original_length <= 8:
            return 3
        elif original_length <= 16:
            return 6
        elif original_length <= 32:
            return 8
        else:
            return 12

    @classmethod
    def create_mask(cls, credential: str, show_prefix: int = 2, show_suffix: int = 2) -> str:
        """Create a masked version of a credential showing only prefix and suffix."""
        if len(credential) <= (show_prefix + show_suffix + 2):
            return "*" * cls.get_mask_length(len(credential))

        mask_length = cls.get_mask_length(len(credential))
        prefix = credential[:show_prefix] if show_prefix > 0 else ""
        suffix = credential[-show_suffix:] if show_suffix > 0 else ""

        return f"{prefix}{'*' * mask_length}{suffix}"


def mask_credentials(text: str, custom_patterns: Optional[Dict[str, Pattern]] = None) -> str:
    """
    Mask credentials in text using predefined and custom patterns.

    Args:
        text: Input text that may contain credentials
        custom_patterns: Additional regex patterns to use for masking

    Returns:
        Text with credentials masked
    """
    if not text:
        return text

    masked_text = text
    patterns = CredentialMaskingPatterns.PATTERNS.copy()

    if custom_patterns:
        patterns.update(custom_patterns)

    for pattern_name, pattern in patterns.items():

        def mask_match(match):
            prefix = match.group(1) if match.lastindex >= 1 else ""
            credential = match.group(2) if match.lastindex >= 2 else match.group(0)

            # Create appropriate mask
            masked_credential = CredentialMaskingPatterns.create_mask(credential)

            return f"{prefix}{masked_credential}"

        masked_text = pattern.sub(mask_match, masked_text)

    return masked_text


class SecureFormatter(logging.Formatter):
    """Logging formatter with automatic credential masking."""

    def __init__(
        self,
        *args,
        enable_masking: bool = True,
        custom_patterns: Optional[Dict[str, Pattern]] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.enable_masking = enable_masking
        self.custom_patterns = custom_patterns or {}

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with credential masking applied."""
        # Format the record normally first
        formatted = super().format(record)

        if not self.enable_masking:
            return formatted

        # Apply credential masking
        return mask_credentials(formatted, self.custom_patterns)

    def add_pattern(self, name: str, pattern: Pattern):
        """Add a custom masking pattern."""
        self.custom_patterns[name] = pattern

    def remove_pattern(self, name: str):
        """Remove a custom masking pattern."""
        self.custom_patterns.pop(name, None)


class SecurityEventLogger:
    """Centralized security event logging system."""

    def __init__(self, settings: Optional[Any] = None):
        self.settings = settings
        # Lazy import to avoid circular dependency
        from ..utils.logging import get_logger

        self.logger = get_logger("security")
        self.audit_logger = self._setup_audit_logger()
        self._event_cache: List[SecurityEvent] = []
        self.cache_size = 1000

    def _setup_audit_logger(self) -> logging.Logger:
        """Set up dedicated audit trail logger with secure formatting."""
        audit_logger = logging.getLogger("calendarbot.security.audit")
        audit_logger.setLevel(logging.INFO)

        # Clear existing handlers
        audit_logger.handlers.clear()

        # Create audit log directory
        if self.settings and hasattr(self.settings, "data_dir"):
            audit_dir = Path(self.settings.data_dir) / "security" / "audit"
        else:
            audit_dir = Path.home() / ".local" / "share" / "calendarbot" / "security" / "audit"

        audit_dir.mkdir(parents=True, exist_ok=True)

        # Set up file handler with rotation
        from logging.handlers import RotatingFileHandler

        audit_file = audit_dir / "security_audit.log"

        audit_handler = RotatingFileHandler(
            audit_file, maxBytes=50 * 1024 * 1024, backupCount=10, encoding="utf-8"  # 50MB
        )

        # Use secure formatter for audit logs
        audit_formatter = SecureFormatter(
            "%(asctime)s - SECURITY - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            enable_masking=True,
        )
        audit_handler.setFormatter(audit_formatter)
        audit_logger.addHandler(audit_handler)

        # Ensure audit logs don't propagate to avoid duplication
        audit_logger.propagate = False

        return audit_logger

    def log_event(self, event: SecurityEvent):
        """
        Log a security event to both standard and audit logs.

        Args:
            event: SecurityEvent to log
        """
        try:
            # Add to cache for analysis
            self._add_to_cache(event)

            # Convert event to structured log message
            event_dict = event.to_dict()
            event_json = json.dumps(event_dict, separators=(",", ":"))

            # Log to main logger based on severity
            log_level = self._severity_to_log_level(event.severity)
            self.logger.log(log_level, f"Security Event: {event_json}")

            # Always log to audit trail
            self.audit_logger.info(f"AUDIT: {event_json}")

        except Exception as e:
            # Fallback logging - don't let security logging break the application
            self.logger.error(f"Failed to log security event: {e}")

    def log_authentication_success(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log successful authentication event."""
        event = SecurityEvent(
            event_type=SecurityEventType.AUTH_SUCCESS,
            severity=SecuritySeverity.LOW,
            user_id=user_id,
            session_id=session_id,
            action="authenticate",
            result="success",
            details=details or {},
        )
        self.log_event(event)

    def log_authentication_failure(
        self,
        user_id: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log failed authentication event."""
        event_details = details or {}
        if reason:
            event_details["failure_reason"] = reason

        event = SecurityEvent(
            event_type=SecurityEventType.AUTH_FAILURE,
            severity=SecuritySeverity.MEDIUM,
            user_id=user_id,
            action="authenticate",
            result="failure",
            details=event_details,
        )
        self.log_event(event)

    def log_token_refresh(
        self, user_id: Optional[str] = None, session_id: Optional[str] = None, success: bool = True
    ):
        """Log token refresh event."""
        event = SecurityEvent(
            event_type=SecurityEventType.AUTH_TOKEN_REFRESH,
            severity=SecuritySeverity.LOW,
            user_id=user_id,
            session_id=session_id,
            action="token_refresh",
            result="success" if success else "failure",
        )
        self.log_event(event)

    def log_input_validation_failure(
        self, input_type: str, validation_error: str, details: Optional[Dict[str, Any]] = None
    ):
        """Log input validation failure."""
        event_details = details or {}
        event_details.update({"input_type": input_type, "validation_error": validation_error})

        event = SecurityEvent(
            event_type=SecurityEventType.INPUT_VALIDATION_FAILURE,
            severity=SecuritySeverity.MEDIUM,
            action="validate_input",
            result="failure",
            details=event_details,
        )
        self.log_event(event)

    def log_credential_access(
        self, resource: str, access_type: str = "read", user_id: Optional[str] = None
    ):
        """Log credential access event."""
        event = SecurityEvent(
            event_type=SecurityEventType.SYSTEM_CREDENTIAL_ACCESS,
            severity=SecuritySeverity.HIGH,
            user_id=user_id,
            resource=resource,
            action=access_type,
            details={"credential_type": "authentication_token"},
        )
        self.log_event(event)

    def log_security_violation(
        self,
        violation_type: str,
        description: str,
        severity: SecuritySeverity = SecuritySeverity.HIGH,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log general security violation."""
        event_details = details or {}
        event_details.update({"violation_type": violation_type, "description": description})

        event = SecurityEvent(
            event_type=SecurityEventType.SYSTEM_SECURITY_VIOLATION,
            severity=severity,
            action="security_check",
            result="violation",
            details=event_details,
        )
        self.log_event(event)

    def _severity_to_log_level(self, severity: SecuritySeverity) -> int:
        """Convert security severity to logging level."""
        mapping = {
            SecuritySeverity.LOW: logging.INFO,
            SecuritySeverity.MEDIUM: logging.WARNING,
            SecuritySeverity.HIGH: logging.ERROR,
            SecuritySeverity.CRITICAL: logging.CRITICAL,
        }
        return mapping.get(severity, logging.WARNING)

    def _add_to_cache(self, event: SecurityEvent):
        """Add event to in-memory cache for analysis."""
        self._event_cache.append(event)

        # Maintain cache size limit
        if len(self._event_cache) > self.cache_size:
            self._event_cache = self._event_cache[-self.cache_size :]

    def get_recent_events(
        self,
        limit: int = 100,
        event_type: Optional[SecurityEventType] = None,
        severity: Optional[SecuritySeverity] = None,
    ) -> List[SecurityEvent]:
        """
        Get recent security events from cache.

        Args:
            limit: Maximum number of events to return
            event_type: Filter by specific event type
            severity: Filter by minimum severity level

        Returns:
            List of matching security events
        """
        events = self._event_cache

        # Apply filters
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if severity:
            events = [e for e in events if e.severity.priority >= severity.priority]

        # Return most recent events
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_security_summary(self) -> Dict[str, Any]:
        """Get summary of recent security events."""
        if not self._event_cache:
            return {"total_events": 0, "by_severity": {}, "by_type": {}}

        recent_events = self._event_cache[-100:]  # Last 100 events

        # Count by severity
        severity_counts = {}
        for severity in SecuritySeverity:
            severity_counts[severity.severity_name] = len(
                [e for e in recent_events if e.severity == severity]
            )

        # Count by type
        type_counts = {}
        for event_type in SecurityEventType:
            type_counts[event_type.value] = len(
                [e for e in recent_events if e.event_type == event_type]
            )

        return {
            "total_events": len(self._event_cache),
            "recent_events": len(recent_events),
            "by_severity": severity_counts,
            "by_type": type_counts,
            "oldest_event": (
                self._event_cache[0].timestamp.isoformat() if self._event_cache else None
            ),
            "newest_event": (
                self._event_cache[-1].timestamp.isoformat() if self._event_cache else None
            ),
        }


# Global security logger instance
_security_logger: Optional[SecurityEventLogger] = None


def get_security_logger(settings: Optional[Any] = None) -> SecurityEventLogger:
    """Get or create global security logger instance."""
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityEventLogger(settings)
    return _security_logger


def init_security_logging(settings: Any):
    """Initialize security logging system with settings."""
    global _security_logger
    _security_logger = SecurityEventLogger(settings)
    return _security_logger
