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



class ICSParseError(ICSError):
    """Exception raised when ICS content cannot be parsed."""



class ICSAuthError(ICSError):
    """Exception raised when ICS authentication fails."""



class ICSNetworkError(ICSError):
    """Exception raised for network-related ICS errors."""



class ICSTimeoutError(ICSError):
    """Exception raised when ICS request times out."""



class ICSContentError(ICSError):
    """Exception raised when ICS content is invalid or corrupted."""

