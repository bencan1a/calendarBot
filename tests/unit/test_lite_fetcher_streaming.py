from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from calendarbot_lite.lite_fetcher import STREAM_THRESHOLD, LiteICSFetcher, StreamHandle
from calendarbot_lite.lite_models import LiteICSSource


@pytest.mark.asyncio
async def test_buffered_when_content_length_small():
    settings = SimpleNamespace(request_timeout=5, max_retries=0)
    fetcher = LiteICSFetcher(settings)

    client = MagicMock()
    client.is_closed = False

    head_resp = SimpleNamespace(status_code=200, headers={"content-length": "1000"})
    client.head = AsyncMock(return_value=head_resp)

    get_resp = SimpleNamespace(
        status_code=200,
        headers={"content-type": "text/calendar"},
        text="BEGIN:VCALENDAR\nEND:VCALENDAR",
    )
    get_resp.raise_for_status = lambda: None
    client.get = AsyncMock(return_value=get_resp)

    fetcher.client = client

    source = LiteICSSource(name="test", url="https://example.com/cal.ics")
    resp = await fetcher.fetch_ics(source)

    assert resp.success is True
    assert resp.content is not None
    assert resp.stream_handle is None


@pytest.mark.asyncio
async def test_streaming_when_content_length_large():
    settings = SimpleNamespace(request_timeout=5, max_retries=0)
    fetcher = LiteICSFetcher(settings)

    client = MagicMock()
    client.is_closed = False

    cl = str(STREAM_THRESHOLD + 1)
    head_resp = SimpleNamespace(status_code=200, headers={"content-length": cl})
    client.head = AsyncMock(return_value=head_resp)

    client.get = AsyncMock(
        side_effect=Exception("GET should not be called when streaming selected")
    )

    fetcher.client = client

    source = LiteICSSource(name="test-large", url="https://example.com/large.ics")
    resp = await fetcher.fetch_ics(source)

    assert resp.success is True
    assert resp.content is None
    assert resp.stream_handle is not None
    assert isinstance(resp.stream_handle, StreamHandle)


@pytest.mark.asyncio
async def test_streaming_when_no_content_length():
    settings = SimpleNamespace(request_timeout=5, max_retries=0)
    fetcher = LiteICSFetcher(settings)

    client = MagicMock()
    client.is_closed = False

    client.head = AsyncMock(side_effect=Exception("HEAD not supported"))
    client.get = AsyncMock(side_effect=Exception("GET not expected"))

    fetcher.client = client

    source = LiteICSSource(name="test-chunked", url="https://example.com/chunked.ics")
    resp = await fetcher.fetch_ics(source)

    assert resp.success is True
    assert resp.stream_handle is not None
