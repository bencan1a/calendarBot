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
