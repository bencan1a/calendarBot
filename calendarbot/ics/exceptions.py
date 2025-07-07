"""ICS-specific exceptions for error handling."""

from typing import Optional


class ICSError(Exception):
    """Base exception for ICS-related errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ICSFetchError(ICSError):
    """Exception raised when ICS file cannot be fetched."""

    pass


class ICSParseError(ICSError):
    """Exception raised when ICS content cannot be parsed."""

    pass


class ICSAuthError(ICSError):
    """Exception raised when ICS authentication fails."""

    pass


class ICSNetworkError(ICSError):
    """Exception raised for network-related ICS errors."""

    pass


class ICSTimeoutError(ICSError):
    """Exception raised when ICS request times out."""

    pass


class ICSContentError(ICSError):
    """Exception raised when ICS content is invalid or corrupted."""

    pass
