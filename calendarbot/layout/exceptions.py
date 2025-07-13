"""Layout system exceptions."""


class LayoutError(Exception):
    """Base exception for layout system errors."""

    pass


class LayoutNotFoundError(LayoutError):
    """Raised when requested layout cannot be found."""

    pass


class LayoutValidationError(LayoutError):
    """Raised when layout configuration is invalid."""

    pass


class ResourceLoadingError(LayoutError):
    """Raised when layout resources fail to load."""

    pass
