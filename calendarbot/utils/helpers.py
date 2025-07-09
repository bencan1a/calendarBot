"""General utility functions and helpers."""

import asyncio
import functools
import logging
import os
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Optional, Tuple, Type, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    max_retries: int = 3,
    backoff_factor: float = 1.5,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    *args: Any,
    **kwargs: Any,
) -> T:
    """Retry an async function with exponential backoff.

    This utility function provides robust retry logic with exponential backoff
    for handling transient failures in async operations.

    Args:
        func (Callable[..., Awaitable[T]]): Async function to retry
        max_retries (int, optional): Maximum number of retry attempts. Defaults to 3.
        backoff_factor (float, optional): Exponential backoff multiplier. Defaults to 1.5.
        initial_delay (float, optional): Initial delay in seconds. Defaults to 1.0.
        max_delay (float, optional): Maximum delay in seconds. Defaults to 60.0.
        exceptions (Tuple[Type[Exception], ...], optional): Tuple of exceptions that trigger retries. Defaults to (Exception,).
        *args (Any): Arguments to pass to function
        **kwargs (Any): Keyword arguments to pass to function

    Returns:
        T: Result of the function call

    Raises:
        Exception: The last exception if all retries fail

    Example:
        >>> async def fetch_data():
        ...     # Some operation that might fail
        ...     pass
        >>>
        >>> result = await retry_with_backoff(
        ...     fetch_data,
        ...     max_retries=5,
        ...     initial_delay=2.0,
        ...     exceptions=(ConnectionError, TimeoutError)
        ... )
    """
    last_exception = None
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except exceptions as e:
            last_exception = e

            if attempt == max_retries:
                logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                break

            logger.warning(
                f"Function {func.__name__} failed (attempt {attempt + 1}), "
                f"retrying in {delay:.1f}s: {e}"
            )

            await asyncio.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)

    # Re-raise the last exception
    if last_exception is not None:
        raise last_exception
    # This should never happen given the logic above, but satisfy mypy
    raise Exception("Function failed with no recorded exception")


async def safe_async_call(
    func: Callable[..., Awaitable[T]],
    default: Optional[T] = None,
    log_errors: bool = True,
    *args: Any,
    **kwargs: Any,
) -> Optional[T]:
    """Safely call an async function with error handling.

    Args:
        func: Async function to call
        default: Default value to return on error
        log_errors: Whether to log errors
        *args: Arguments to pass to function
        **kwargs: Keyword arguments to pass to function

    Returns:
        Function result or default value on error
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"Error in {func.__name__}: {e}")
        return default


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds == 0:
            return f"{minutes}m"
        else:
            return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        if remaining_minutes == 0:
            return f"{hours}h"
        else:
            return f"{hours}h {remaining_minutes}m"


def format_time_ago(dt: datetime) -> str:
    """Format datetime as time ago string.

    Args:
        dt: Datetime to format

    Returns:
        Formatted time ago string
    """
    now = datetime.now()
    if dt.tzinfo and now.tzinfo is None:
        now = now.replace(tzinfo=dt.tzinfo)
    elif dt.tzinfo is None and now.tzinfo:
        dt = dt.replace(tzinfo=now.tzinfo)

    delta = now - dt

    if delta.total_seconds() < 60:
        return "just now"
    elif delta.total_seconds() < 3600:
        minutes = int(delta.total_seconds() // 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif delta.total_seconds() < 86400:
        hours = int(delta.total_seconds() // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = delta.days
        return f"{days} day{'s' if days != 1 else ''} ago"


def ensure_timezone_aware(dt: datetime, default_tz: Optional[str] = None) -> datetime:
    """Ensure datetime is timezone-aware.

    Args:
        dt: Datetime to check
        default_tz: Default timezone to use if none specified

    Returns:
        Timezone-aware datetime
    """
    if dt.tzinfo is None:
        # If no timezone info, assume local time or use default
        if default_tz:
            import pytz

            tz = pytz.timezone(default_tz)
            return tz.localize(dt)
        else:
            # Assume local timezone
            return dt.replace(tzinfo=datetime.now().astimezone().tzinfo)

    return dt


def get_timezone_aware_now() -> datetime:
    """Get current datetime with timezone awareness.

    Returns:
        Current datetime with system timezone
    """
    return datetime.now().astimezone()


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def validate_email(email: str) -> bool:
    """Basic email validation.

    Args:
        email: Email address to validate

    Returns:
        True if email appears valid, False otherwise
    """
    import re

    # More strict pattern that doesn't allow consecutive dots
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def parse_iso_datetime(dt_string: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string with error handling.

    Args:
        dt_string: ISO datetime string

    Returns:
        Parsed datetime or None if parsing fails
    """
    if dt_string is None:
        logger.debug("Failed to parse datetime 'None': Input is None")
        return None

    try:
        # Handle various ISO formats
        if dt_string.endswith("Z"):
            dt_string = dt_string.replace("Z", "+00:00")

        return datetime.fromisoformat(dt_string)
    except (ValueError, TypeError) as e:
        logger.debug(f"Failed to parse datetime '{dt_string}': {e}")
        return None


def rate_limit(
    calls_per_second: float,
) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Decorator to rate limit function calls.

    Args:
        calls_per_second: Maximum calls per second allowed

    Returns:
        Decorator function
    """
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            elapsed = asyncio.get_event_loop().time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                await asyncio.sleep(left_to_wait)

            try:
                return await func(*args, **kwargs)
            finally:
                last_called[0] = asyncio.get_event_loop().time()

        return wrapper

    return decorator


class CircuitBreaker:
    """Simple circuit breaker pattern implementation.

    The CircuitBreaker pattern prevents cascading failures by monitoring
    service calls and stopping requests when failure rate exceeds threshold.

    States:
        - CLOSED: Normal operation, calls pass through
        - OPEN: Circuit is open, calls fail immediately
        - HALF_OPEN: Testing if service has recovered

    Example:
        >>> # Initialize circuit breaker
        >>> circuit = CircuitBreaker(
        ...     failure_threshold=3,
        ...     recovery_timeout=30,
        ...     expected_exception=ConnectionError
        ... )
        >>>
        >>> # Use with async function
        >>> async def unreliable_service():
        ...     # Some operation that might fail
        ...     pass
        >>>
        >>> try:
        ...     result = await circuit.call(unreliable_service)
        ... except Exception as e:
        ...     print(f"Circuit breaker prevented call: {e}")
        >>>
        >>> # Check circuit state
        >>> print(f"Circuit state: {circuit.state}")
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold (int, optional): Number of failures before opening circuit. Defaults to 5.
            recovery_timeout (int, optional): Seconds to wait before trying again. Defaults to 60.
            expected_exception (Type[Exception], optional): Exception type that triggers circuit breaker. Defaults to Exception.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """Call function through circuit breaker.

        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "OPEN":
            if (
                self.last_failure_time is not None
                and (datetime.now().timestamp() - self.last_failure_time) < self.recovery_timeout
            ):
                raise Exception("Circuit breaker is OPEN")
            else:
                self.state = "HALF_OPEN"

        try:
            result = await func(*args, **kwargs)
            self.on_success()
            return result
        except self.expected_exception as e:
            self.on_failure()
            raise

    def on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0
        self.state = "CLOSED"

    def on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now().timestamp()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


def secure_clear_screen() -> bool:
    """Securely clear the console screen using subprocess.

    This function replaces os.system() calls to prevent shell injection vulnerabilities.
    Uses subprocess.run() with shell=False for security.

    Returns:
        True if screen was cleared successfully, False otherwise
    """
    try:
        if os.name == "posix":
            # Unix/Linux/macOS systems
            subprocess.run(["clear"], check=True, timeout=5)
        else:
            # Windows systems - use cmd.exe /c cls to avoid shell=True
            subprocess.run(["cmd.exe", "/c", "cls"], check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning(f"Failed to clear screen: {e}")
        # Fallback: print enough newlines to simulate screen clearing
        print("\n" * 50)
        return False
    except Exception as e:
        logger.error(f"Unexpected error clearing screen: {e}")
        # Fallback: print enough newlines to simulate screen clearing
        print("\n" * 50)
        return False
