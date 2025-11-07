"""
Unit tests for calendarbot_lite.lite_fetcher.LiteICSFetcher

Covers:
- backoff calculation behavior
- conditional headers helper
- basic SSRF URL validation
- response creation handling of 304 and empty content
"""

import random
import types

import pytest

from calendarbot_lite.calendar.lite_fetcher import JITTER_MAX_FACTOR, MAX_BACKOFF_SECONDS, LiteICSFetcher

pytestmark = [pytest.mark.unit, pytest.mark.fast]


class DummySettings:
    max_retries = 3
    retry_backoff_factor = 2.0
    request_timeout = 5


@pytest.fixture(autouse=True)
def seeded_random(monkeypatch):
    """Seed random.uniform to deterministic value for jitter in tests."""
    monkeypatch.setattr(random, "uniform", lambda a, b: (a + b) / 2)


def test_calculate_backoff_when_attempts_increase_then_backoff_increases() -> None:
    """Test exponential backoff increases with retry attempts (2^attempt * factor + jitter)."""
    fetcher = LiteICSFetcher(DummySettings())
    b0 = fetcher._calculate_backoff(attempt=0, corruption_detected=False, max_retries=3, backoff_factor=2.0)
    b1 = fetcher._calculate_backoff(attempt=1, corruption_detected=False, max_retries=3, backoff_factor=2.0)
    b2 = fetcher._calculate_backoff(attempt=2, corruption_detected=False, max_retries=3, backoff_factor=2.0)
    assert b0 >= 1.0 * 0.1  # base 1.0 plus jitter (deterministic seeded)
    assert b1 > b0
    assert b2 > b1


def test_calculate_backoff_when_corruption_detected_then_capped_and_doubled() -> None:
    """Test corruption detection triggers immediate capped backoff (prevents retry storms on bad data)."""
    fetcher = LiteICSFetcher(DummySettings())
    # Use a large attempt so base_backoff would normally be big, but corruption should cap it
    backoff = fetcher._calculate_backoff(attempt=10, corruption_detected=True, max_retries=3, backoff_factor=2.0)
    # Should not exceed MAX_BACKOFF_SECONDS plus allowed jitter
    assert backoff <= MAX_BACKOFF_SECONDS * (1.0 + JITTER_MAX_FACTOR)


def test_get_conditional_headers_returns_expected_keys() -> None:
    """Test conditional headers generation (If-None-Match, If-Modified-Since) for HTTP caching."""
    fetcher = LiteICSFetcher(DummySettings())
    headers = fetcher.get_conditional_headers(etag='"abc"', last_modified="Mon, 01 Jan 2000 00:00:00 GMT")
    assert headers["If-None-Match"] == '"abc"'
    assert headers["If-Modified-Since"] == "Mon, 01 Jan 2000 00:00:00 GMT"

    headers2 = fetcher.get_conditional_headers()
    assert headers2 == {}


def test_validate_url_for_ssrf_blocks_non_http_and_missing_hostname() -> None:
    """Test SSRF protection blocks non-HTTP schemes and malformed URLs.

    Prevents Server-Side Request Forgery by ensuring only valid HTTP/HTTPS URLs with hostnames.
    """
    fetcher = LiteICSFetcher(DummySettings())
    # Non-HTTP scheme
    assert fetcher._validate_url_for_ssrf("ftp://example.com/resource") is False
    # Missing hostname
    assert fetcher._validate_url_for_ssrf("http:///no-host") is False
    # Valid URL should pass
    assert fetcher._validate_url_for_ssrf("https://example.com/calendar.ics") is True


def make_fake_response(status_code=200, headers=None, text="BEGIN:VCALENDAR\nEND:VCALENDAR\n"):
    if headers is None:
        headers = {}
    # Minimal fake response object with required attributes used by _create_response
    return types.SimpleNamespace(status_code=status_code, headers=headers, text=text, content=text.encode("utf-8"))


def test_create_response_handles_304_not_modified() -> None:
    """Test HTTP 304 Not Modified returns success with ETag/Last-Modified (uses cached data)."""
    fetcher = LiteICSFetcher(DummySettings())
    resp = make_fake_response(status_code=304, headers={"etag": "etag-val", "last-modified": "LM"})
    result = fetcher._create_response(resp)
    assert result.success is True
    assert result.status_code == 304
    assert result.etag == "etag-val"
    assert result.last_modified == "LM"


def test_create_response_handles_empty_content_as_error() -> None:
    """Test empty/whitespace-only response content returns error (prevents parsing failures)."""
    fetcher = LiteICSFetcher(DummySettings())
    resp = make_fake_response(status_code=200, headers={}, text="   ")
    result = fetcher._create_response(resp)
    assert result.success is False
    assert "Empty content" in (result.error_message or "")
