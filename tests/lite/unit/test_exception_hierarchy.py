"""Test cases for exception handling refactoring."""
import pytest
from calendarbot_lite.alexa_exceptions import (
    AlexaHandlerError,
    AlexaAuthenticationError,
    AlexaValidationError,
    AlexaEventProcessingError,
    AlexaSSMLGenerationError,
    AlexaDataAccessError,
    AlexaResponseGenerationError,
)


class TestExceptionHierarchy:
    """Test the exception hierarchy is properly structured."""
    
    def test_all_exceptions_inherit_from_base(self):
        """All custom exceptions should inherit from AlexaHandlerError."""
        exceptions = [
            AlexaAuthenticationError,
            AlexaValidationError,
            AlexaEventProcessingError,
            AlexaSSMLGenerationError,
            AlexaDataAccessError,
            AlexaResponseGenerationError,
        ]
        
        for exc_class in exceptions:
            assert issubclass(exc_class, AlexaHandlerError)
            assert issubclass(exc_class, Exception)
    
    def test_exceptions_are_distinguishable(self):
        """Each exception type should be distinguishable."""
        exceptions = [
            AlexaAuthenticationError("auth"),
            AlexaValidationError("validation"),
            AlexaEventProcessingError("processing"),
            AlexaSSMLGenerationError("ssml"),
            AlexaDataAccessError("data"),
            AlexaResponseGenerationError("response"),
        ]
        
        # Each should have different types
        types = [type(e) for e in exceptions]
        assert len(set(types)) == len(types)
    
    def test_exception_messages_are_preserved(self):
        """Exception messages should be preserved."""
        msg = "Test error message"
        exc = AlexaValidationError(msg)
        assert str(exc) == msg
    
    def test_exceptions_can_be_raised_and_caught(self):
        """Exceptions can be raised and caught properly."""
        with pytest.raises(AlexaHandlerError):
            raise AlexaValidationError("test")
        
        with pytest.raises(AlexaValidationError):
            raise AlexaValidationError("test")


class TestExceptionContextPreservation:
    """Test that exception context and tracebacks are preserved."""
    
    def test_exception_chaining_preserves_cause(self):
        """Exception chaining should preserve the original cause."""
        original = ValueError("Original error")
        
        try:
            raise AlexaValidationError("Wrapped error") from original
        except AlexaValidationError as e:
            assert e.__cause__ is original
            assert str(e.__cause__) == "Original error"
    
    def test_exception_can_be_reraised(self):
        """Exceptions can be caught and re-raised."""
        with pytest.raises(AlexaDataAccessError):
            try:
                raise AlexaDataAccessError("Original")
            except AlexaDataAccessError:
                # Do some logging
                raise  # Re-raise
