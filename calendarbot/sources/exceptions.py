"""Source-specific exceptions."""


class SourceError(Exception):
    """Base exception for source-related errors."""
    
    def __init__(self, message: str, source_name: str = None):
        super().__init__(message)
        self.message = message
        self.source_name = source_name


class SourceConnectionError(SourceError):
    """Exception raised when source connection fails."""
    pass


class SourceConfigError(SourceError):
    """Exception raised when source configuration is invalid."""
    pass


class SourceAuthError(SourceError):
    """Exception raised when source authentication fails."""
    pass


class SourceDataError(SourceError):
    """Exception raised when source data is invalid or corrupted."""
    pass


class SourceTimeoutError(SourceError):
    """Exception raised when source operation times out."""
    pass