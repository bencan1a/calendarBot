"""Custom exception hierarchy for Alexa handler errors.

This module provides specific exception types to replace generic Exception
handling throughout the Alexa integration code, enabling better error
diagnosis, proper HTTP status codes, and improved observability.
"""


class AlexaHandlerError(Exception):
    """Base exception for all Alexa handler errors.

    All custom exceptions in the Alexa integration should inherit from this
    base class to enable centralized exception handling and consistent error
    responses.
    """


class AlexaAuthenticationError(AlexaHandlerError):
    """Authentication or authorization failed.

    Raised when:
    - Bearer token is missing or invalid
    - Authorization header is malformed
    - User doesn't have permission to access the resource

    Should result in HTTP 401 Unauthorized response.
    """


class AlexaValidationError(AlexaHandlerError):
    """Request validation failed.

    Raised when:
    - Query parameters are invalid or malformed
    - Required parameters are missing
    - Parameter values are out of valid range
    - Timezone string is not a valid IANA timezone

    Should result in HTTP 400 Bad Request response.
    """


class AlexaTimezoneError(AlexaHandlerError):
    """Timezone parsing or conversion failed.

    Raised when:
    - Timezone string cannot be parsed
    - ZoneInfo lookup fails
    - Timezone conversion produces invalid results

    This is a specialized validation error for timezone-specific issues.
    """


class AlexaEventProcessingError(AlexaHandlerError):
    """Event processing or filtering failed.

    Raised when:
    - Event data cannot be parsed or accessed
    - Event filtering logic encounters unexpected data
    - Pipeline stage processing fails

    Should result in HTTP 500 Internal Server Error response.
    """


class AlexaSSMLGenerationError(AlexaHandlerError):
    """SSML generation failed.

    Raised when:
    - SSML renderer raises an exception
    - SSML template is malformed
    - SSML data interpolation fails

    This is typically a non-fatal error - the handler should fall back
    to plain text response.
    """


class AlexaDataAccessError(AlexaHandlerError):
    """Data access or retrieval failed.

    Raised when:
    - Skipped events store access fails
    - Event window access encounters issues
    - External data source is unavailable

    Should result in HTTP 500 Internal Server Error response.
    """


class AlexaResponseGenerationError(AlexaHandlerError):
    """Response generation or serialization failed.

    Raised when:
    - Response data cannot be serialized to JSON
    - Response structure is invalid
    - Required response fields are missing

    Should result in HTTP 500 Internal Server Error response.
    """
