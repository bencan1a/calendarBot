"""Utility-specific exceptions."""


class UtilsError(Exception):
    """Base exception for all utils-related errors."""


class RetryError(UtilsError):
    """Exception raised when retry operations fail after all attempts."""

    def __init__(self, message: str, attempts: int, last_exception: Exception) -> None:
        """Initialize RetryError.

        Args:
            message: Error message
            attempts: Number of attempts made
            last_exception: The last exception that caused the retry to fail
        """
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception


class CircuitBreakerError(UtilsError):
    """Exception raised when circuit breaker is open and blocks execution."""

    def __init__(self, message: str = "Circuit breaker is OPEN") -> None:
        """Initialize CircuitBreakerError.

        Args:
            message: Error message describing the circuit breaker state
        """
        super().__init__(message)
