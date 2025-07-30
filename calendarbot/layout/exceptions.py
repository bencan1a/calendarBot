"""Layout system exceptions."""


class LayoutError(Exception):
    """Base exception for layout system errors."""



class LayoutNotFoundError(LayoutError):
    """Raised when requested layout cannot be found."""



class LayoutValidationError(LayoutError):
    """Raised when layout configuration is invalid."""



class ResourceLoadingError(LayoutError):
    """Raised when layout resources fail to load."""

