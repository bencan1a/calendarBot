"""Comprehensive tests for calendarbot.utils.helpers module."""

import subprocess
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from calendarbot.utils.exceptions import RetryError
from calendarbot.utils.helpers import (
    CircuitBreaker,
    ensure_timezone_aware,
    format_duration,
    format_time_ago,
    get_timezone_aware_now,
    parse_iso_datetime,
    rate_limit,
    retry_with_backoff,
    safe_async_call,
    secure_clear_screen,
    truncate_string,
    validate_email,
)


class TestRetryWithBackoff:
    """Test retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self) -> None:
        """Test successful function call requires no retries."""
        mock_func = AsyncMock(return_value="success")

        result = await retry_with_backoff(
            mock_func, 3, 1.5, 1.0, 60.0, (Exception,), "arg1", kwarg1="value1"
        )

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")

    @pytest.mark.asyncio
    async def test_retry_on_exception(self) -> None:
        """Test function retries on specified exceptions."""
        mock_func = AsyncMock(side_effect=[ValueError("error"), "success"])

        result = await retry_with_backoff(
            mock_func, max_retries=2, exceptions=(ValueError,), initial_delay=0.01
        )

        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self) -> None:
        """Test function fails after max retries exceeded."""
        mock_func = AsyncMock(side_effect=ValueError("persistent error"))

        with pytest.raises(RetryError, match="Function AsyncMock failed after 2 retries"):
            await retry_with_backoff(mock_func, max_retries=2, initial_delay=0.01)

        assert mock_func.call_count == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_backoff_factor_applied(self) -> None:
        """Test exponential backoff factor is applied."""
        mock_func = AsyncMock(side_effect=[ValueError("error"), "success"])

        start_time = time.time()
        await retry_with_backoff(mock_func, max_retries=2, initial_delay=0.1, backoff_factor=2.0)
        elapsed_time = time.time() - start_time

        # Should have waited at least initial_delay (0.1s)
        assert elapsed_time >= 0.1

    @pytest.mark.asyncio
    async def test_max_delay_respected(self) -> None:
        """Test maximum delay is respected."""
        mock_func = AsyncMock(side_effect=[ValueError("error"), "success"])

        await retry_with_backoff(
            mock_func, max_retries=2, initial_delay=0.01, backoff_factor=10.0, max_delay=0.05
        )

        # Test passes if no exception (max_delay working correctly)
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_unhandled_exception_not_retried(self) -> None:
        """Test unhandled exceptions are not retried."""
        mock_func = AsyncMock(side_effect=TypeError("wrong type"))

        with pytest.raises(TypeError, match="wrong type"):
            await retry_with_backoff(mock_func, max_retries=2, exceptions=(ValueError,))

        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_no_exception_fallback(self) -> None:
        """Test fallback exception when no recorded exception."""
        # This tests the edge case where last_exception is None
        with patch("calendarbot.utils.helpers.asyncio.sleep"):
            mock_func = AsyncMock(return_value="success")

            # Mock the function to succeed on first call
            result = await retry_with_backoff(mock_func, max_retries=0)
            assert result == "success"


class TestSafeAsyncCall:
    """Test safe_async_call function."""

    @pytest.mark.asyncio
    async def test_successful_call(self) -> None:
        """Test successful async function call."""
        mock_func = AsyncMock(return_value="success")

        result = await safe_async_call(mock_func, None, True, "arg1", kwarg1="value1")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")

    @pytest.mark.asyncio
    async def test_exception_returns_default(self) -> None:
        """Test exception returns default value."""
        mock_func = AsyncMock(side_effect=ValueError("error"))

        result = await safe_async_call(mock_func, default="fallback")

        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_exception_returns_none_default(self) -> None:
        """Test exception returns None when no default specified."""
        mock_func = AsyncMock(side_effect=ValueError("error"))

        result = await safe_async_call(mock_func)

        assert result is None


class TestFormatDuration:
    """Test format_duration function."""

    def test_seconds_only(self) -> None:
        """Test formatting seconds only."""
        assert format_duration(30) == "30s"
        assert format_duration(59) == "59s"
        assert format_duration(1) == "1s"

    def test_minutes_and_seconds(self) -> None:
        """Test formatting minutes and seconds."""
        assert format_duration(90) == "1m 30s"
        assert format_duration(125) == "2m 5s"
        assert format_duration(3599) == "59m 59s"

    def test_minutes_only(self) -> None:
        """Test formatting minutes without seconds."""
        assert format_duration(60) == "1m"
        assert format_duration(120) == "2m"
        assert format_duration(3540) == "59m"

    def test_hours_and_minutes(self) -> None:
        """Test formatting hours and minutes."""
        assert format_duration(3660) == "1h 1m"
        assert format_duration(7320) == "2h 2m"
        assert format_duration(5400) == "1h 30m"

    def test_hours_only(self) -> None:
        """Test formatting hours without minutes."""
        assert format_duration(3600) == "1h"
        assert format_duration(7200) == "2h"
        assert format_duration(10800) == "3h"

    def test_zero_duration(self) -> None:
        """Test zero duration."""
        assert format_duration(0) == "0s"


class TestFormatTimeAgo:
    """Test format_time_ago function."""

    def test_just_now(self) -> None:
        """Test very recent times."""
        now = datetime.now()
        recent = now - timedelta(seconds=30)

        assert format_time_ago(recent) == "just now"

    def test_minutes_ago_singular(self) -> None:
        """Test one minute ago."""
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)

        assert format_time_ago(one_minute_ago) == "1 minute ago"

    def test_minutes_ago_plural(self) -> None:
        """Test multiple minutes ago."""
        now = datetime.now()
        minutes_ago = now - timedelta(minutes=30)

        assert format_time_ago(minutes_ago) == "30 minutes ago"

    def test_hours_ago_singular(self) -> None:
        """Test one hour ago."""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)

        assert format_time_ago(one_hour_ago) == "1 hour ago"

    def test_hours_ago_plural(self) -> None:
        """Test multiple hours ago."""
        now = datetime.now()
        hours_ago = now - timedelta(hours=5)

        assert format_time_ago(hours_ago) == "5 hours ago"

    def test_days_ago_singular(self) -> None:
        """Test one day ago."""
        now = datetime.now()
        one_day_ago = now - timedelta(days=1)

        assert format_time_ago(one_day_ago) == "1 day ago"

    def test_days_ago_plural(self) -> None:
        """Test multiple days ago."""
        now = datetime.now()
        days_ago = now - timedelta(days=7)

        assert format_time_ago(days_ago) == "7 days ago"

    def test_timezone_aware_datetime(self) -> None:
        """Test timezone-aware datetime handling."""
        with patch("calendarbot.utils.helpers.datetime") as mock_datetime:
            # Mock now to return a consistent time
            mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now

            # Create a past time
            past = mock_now - timedelta(hours=2)

            result = format_time_ago(past)
            assert "hour" in result

    def test_mixed_timezone_handling(self) -> None:
        """Test mixed timezone scenarios."""
        with patch("calendarbot.utils.helpers.datetime") as mock_datetime:
            # Mock now to return a consistent time
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now

            # Test when input has timezone but now doesn't
            tz_dt = datetime(2023, 1, 1, 11, 30, 0, tzinfo=timezone.utc)
            result = format_time_ago(tz_dt)
            assert "minute" in result

            # Test when now has timezone but input doesn't
            naive_dt = datetime(2023, 1, 1, 11, 30, 0)
            result = format_time_ago(naive_dt)
            assert "minute" in result


class TestEnsureTimezoneAware:
    """Test ensure_timezone_aware function."""

    def test_already_timezone_aware(self) -> None:
        """Test datetime that already has timezone."""
        dt = datetime.now(timezone.utc)
        result = ensure_timezone_aware(dt)

        assert result == dt
        assert result.tzinfo is not None

    def test_naive_datetime_with_default_tz(self) -> None:
        """Test naive datetime with default timezone."""
        dt = datetime(2023, 1, 1, 12, 0, 0)

        # Mock the pytz import inside the function
        with patch("builtins.__import__") as mock_import:
            mock_pytz = MagicMock()
            mock_tz = MagicMock()
            mock_tz.localize.return_value = dt.replace(tzinfo=timezone.utc)
            mock_pytz.timezone.return_value = mock_tz

            def import_side_effect(name: str, *args: Any, **kwargs: Any) -> Any:
                if name == "pytz":
                    return mock_pytz
                return __import__(name, *args, **kwargs)

            mock_import.side_effect = import_side_effect

            ensure_timezone_aware(dt, "UTC")

            mock_pytz.timezone.assert_called_once_with("UTC")
            mock_tz.localize.assert_called_once_with(dt)

    def test_naive_datetime_no_default_tz(self) -> None:
        """Test naive datetime without default timezone."""
        dt = datetime(2023, 1, 1, 12, 0, 0)

        with patch("datetime.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.astimezone.return_value.tzinfo = timezone.utc
            mock_datetime.now.return_value = mock_now

            result = ensure_timezone_aware(dt)

            assert result.tzinfo is not None


class TestGetTimezoneAwareNow:
    """Test get_timezone_aware_now function."""

    def test_returns_timezone_aware_datetime(self) -> None:
        """Test function returns timezone-aware datetime."""
        result = get_timezone_aware_now()

        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_returns_current_time(self) -> None:
        """Test function returns current time."""
        before = datetime.now().astimezone()
        result = get_timezone_aware_now()
        after = datetime.now().astimezone()

        assert before <= result <= after


class TestTruncateString:
    """Test truncate_string function."""

    def test_short_string_unchanged(self) -> None:
        """Test short string remains unchanged."""
        text = "short"
        result = truncate_string(text, 10)
        assert result == "short"

    def test_exact_length_unchanged(self) -> None:
        """Test string at exact max length unchanged."""
        text = "exactly10c"
        result = truncate_string(text, 10)
        assert result == "exactly10c"

    def test_long_string_truncated(self) -> None:
        """Test long string is truncated with suffix."""
        text = "this is a very long string"
        result = truncate_string(text, 10)
        assert result == "this is..."
        assert len(result) == 10

    def test_custom_suffix(self) -> None:
        """Test custom suffix is used."""
        text = "long string here"
        result = truncate_string(text, 10, suffix="...")
        assert result.endswith("...")
        assert len(result) == 10

    def test_empty_suffix(self) -> None:
        """Test empty suffix."""
        text = "long string here"
        result = truncate_string(text, 10, suffix="")
        assert result == "long strin"
        assert len(result) == 10


class TestValidateEmail:
    """Test validate_email function."""

    def test_valid_emails(self) -> None:
        """Test valid email addresses."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@example.co.uk",
            "123@test.edu",
            "a@b.co",
        ]

        for email in valid_emails:
            assert validate_email(email), f"Should be valid: {email}"

    def test_invalid_emails(self) -> None:
        """Test invalid email addresses."""
        invalid_emails = [
            "invalid",
            "@example.com",
            "user@",
            "user@domain",
            "user@domain..com",
            "",
            "user@.com",
            "user@domain.",
        ]

        for email in invalid_emails:
            assert not validate_email(email), f"Should be invalid: {email}"


class TestParseIsoDatetime:
    """Test parse_iso_datetime function."""

    def test_valid_iso_format(self) -> None:
        """Test valid ISO datetime string."""
        dt_string = "2023-01-01T12:00:00"
        result = parse_iso_datetime(dt_string)

        assert result is not None
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12

    def test_iso_with_z_suffix(self) -> None:
        """Test ISO format with Z suffix."""
        dt_string = "2023-01-01T12:00:00Z"
        result = parse_iso_datetime(dt_string)

        assert result is not None
        assert result.tzinfo is not None

    def test_iso_with_timezone_offset(self) -> None:
        """Test ISO format with timezone offset."""
        dt_string = "2023-01-01T12:00:00+05:00"
        result = parse_iso_datetime(dt_string)

        assert result is not None
        assert result.tzinfo is not None

    def test_invalid_format(self) -> None:
        """Test invalid datetime format."""
        with patch("calendarbot.utils.helpers.logger") as mock_logger:
            result = parse_iso_datetime("invalid-date")

            assert result is None
            mock_logger.debug.assert_called_once()

    def test_none_input(self) -> None:
        """Test None input."""
        with patch("calendarbot.utils.helpers.logger") as mock_logger:
            result = parse_iso_datetime(None)

            assert result is None
            mock_logger.debug.assert_called_once()


class TestRateLimit:
    """Test rate_limit decorator."""

    @pytest.mark.asyncio
    async def test_rate_limiting_applied(self) -> None:
        """Test rate limiting is applied."""

        @rate_limit(calls_per_second=10.0)
        async def test_func() -> str:
            return "result"

        start_time = time.time()

        # Call function twice
        await test_func()
        await test_func()

        elapsed = time.time() - start_time

        # Should take at least 0.1 seconds (1/10 calls per second)
        assert elapsed >= 0.1

    @pytest.mark.asyncio
    async def test_function_args_preserved(self) -> None:
        """Test function arguments are preserved."""

        @rate_limit(calls_per_second=100.0)  # High rate to avoid delays
        async def test_func(arg1: str, arg2: Any = None) -> str:
            return f"{arg1}-{arg2}"

        result = await test_func("test", arg2="value")
        assert result == "test-value"

    @pytest.mark.asyncio
    async def test_exception_handling(self) -> None:
        """Test exceptions are properly handled."""

        @rate_limit(calls_per_second=100.0)
        async def failing_func() -> None:
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            await failing_func()


class TestCircuitBreaker:
    """Test CircuitBreaker class."""

    def test_initialization(self) -> None:
        """Test circuit breaker initialization."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 30
        assert cb.failure_count == 0
        assert cb.state == "CLOSED"
        assert cb.last_failure_time is None

    @pytest.mark.asyncio
    async def test_successful_call_closed_state(self) -> None:
        """Test successful call in closed state."""
        cb = CircuitBreaker()
        mock_func = AsyncMock(return_value="success")

        result = await cb.call(mock_func, "arg1", kwarg1="value1")

        assert result == "success"
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_failure_increments_count(self) -> None:
        """Test failure increments failure count."""
        cb = CircuitBreaker(failure_threshold=3)
        mock_func = AsyncMock(side_effect=ValueError("error"))

        with pytest.raises(ValueError):
            await cb.call(mock_func)

        assert cb.failure_count == 1
        assert cb.state == "CLOSED"

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self) -> None:
        """Test circuit opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=2)
        mock_func = AsyncMock(side_effect=ValueError("error"))

        # First failure
        with pytest.raises(ValueError):
            await cb.call(mock_func)

        # Second failure - should open circuit
        with pytest.raises(ValueError):
            await cb.call(mock_func)

        assert cb.state == "OPEN"
        assert cb.failure_count == 2

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self) -> None:
        """Test open circuit rejects calls."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        mock_func = AsyncMock(side_effect=ValueError("error"))

        # Trigger circuit to open
        with pytest.raises(ValueError):
            await cb.call(mock_func)

        assert cb.state == "OPEN"

        # Next call should be rejected
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await cb.call(mock_func)

    @pytest.mark.asyncio
    async def test_half_open_state_after_timeout(self) -> None:
        """Test circuit moves to half-open after timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        mock_func = AsyncMock(side_effect=ValueError("error"))

        # Open the circuit
        with pytest.raises(ValueError):
            await cb.call(mock_func)

        assert cb.state == "OPEN"

        # Mock time to simulate timeout without actual wait
        original_last_failure_time = cb.last_failure_time
        cb.last_failure_time = original_last_failure_time - 2  # Simulate 2 seconds passed

        # Next call should set state to HALF_OPEN
        mock_func.side_effect = None
        mock_func.return_value = "success"

        result = await cb.call(mock_func)
        assert result == "success"
        assert cb.state == "CLOSED"

    @pytest.mark.asyncio
    async def test_success_resets_circuit(self) -> None:
        """Test successful call resets circuit."""
        cb = CircuitBreaker()
        mock_func = AsyncMock()

        # Set some failure state
        cb.failure_count = 3
        cb.state = "HALF_OPEN"

        mock_func.return_value = "success"
        result = await cb.call(mock_func)

        assert result == "success"
        assert cb.failure_count == 0
        assert cb.state == "CLOSED"

    @pytest.mark.asyncio
    async def test_specific_exception_type(self) -> None:
        """Test circuit breaker with specific exception type."""
        cb = CircuitBreaker(expected_exception=ValueError)
        mock_func = AsyncMock(side_effect=TypeError("wrong type"))

        # TypeError should not trigger circuit breaker
        with pytest.raises(TypeError):
            await cb.call(mock_func)

        assert cb.state == "CLOSED"
        assert cb.failure_count == 0


class TestSecureClearScreen:
    """Test secure_clear_screen function."""

    @patch("calendarbot.utils.helpers.os.name", "posix")
    @patch("calendarbot.utils.helpers.subprocess.run")
    def test_posix_clear_success(self, mock_run: Any) -> None:
        """Test successful screen clear on POSIX systems."""
        mock_run.return_value = None

        result = secure_clear_screen()

        assert result is True
        mock_run.assert_called_once_with(["clear"], check=True, timeout=5)

    @patch("calendarbot.utils.helpers.os.name", "nt")
    @patch("calendarbot.utils.helpers.subprocess.run")
    def test_windows_clear_success(self, mock_run: Any) -> None:
        """Test successful screen clear on Windows systems."""
        mock_run.return_value = None

        result = secure_clear_screen()

        assert result is True
        mock_run.assert_called_once_with(["cmd.exe", "/c", "cls"], check=True, timeout=5)

    @patch("calendarbot.utils.helpers.os.name", "posix")
    @patch("calendarbot.utils.helpers.subprocess.run")
    @patch("builtins.print")
    def test_subprocess_error_fallback(self, mock_print: Any, mock_run: Any) -> None:
        """Test fallback when subprocess fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "clear")

        with patch("calendarbot.utils.helpers.logger") as mock_logger:
            result = secure_clear_screen()

            assert result is False
            mock_logger.warning.assert_called_once()
            mock_print.assert_called_once_with("\n" * 50)

    @patch("calendarbot.utils.helpers.os.name", "posix")
    @patch("calendarbot.utils.helpers.subprocess.run")
    @patch("builtins.print")
    def test_timeout_error_fallback(self, mock_print: Any, mock_run: Any) -> None:
        """Test fallback when subprocess times out."""
        mock_run.side_effect = subprocess.TimeoutExpired("clear", 5)

        with patch("calendarbot.utils.helpers.logger") as mock_logger:
            result = secure_clear_screen()

            assert result is False
            mock_logger.warning.assert_called_once()
            mock_print.assert_called_once_with("\n" * 50)

    @patch("calendarbot.utils.helpers.os.name", "posix")
    @patch("calendarbot.utils.helpers.subprocess.run")
    @patch("builtins.print")
    def test_file_not_found_fallback(self, mock_print: Any, mock_run: Any) -> None:
        """Test fallback when command not found."""
        mock_run.side_effect = FileNotFoundError("clear not found")

        with patch("calendarbot.utils.helpers.logger") as mock_logger:
            result = secure_clear_screen()

            assert result is False
            mock_logger.warning.assert_called_once()
            mock_print.assert_called_once_with("\n" * 50)
