"""
Unit tests for calendarbot_lite.fetch_orchestrator.FetchOrchestrator

Covers:
- empty sources handling
- successful aggregation of parsed events
- handling of source task exceptions
"""

import asyncio
from typing import Any

import pytest

from calendarbot_lite.fetch_orchestrator import FetchOrchestrator

pytestmark = [pytest.mark.unit, pytest.mark.fast]


class DummyHealthTracker:
    def __init__(self) -> None:
        self.attempts = 0
        self.successes = 0
        self.heartbeats = 0

    def record_refresh_attempt(self) -> None:
        self.attempts += 1

    def record_background_heartbeat(self) -> None:
        self.heartbeats += 1

    def record_refresh_success(self, count: int) -> None:
        self.successes += 1


class DummyWindowManager:
    async def update_window(self, *args: Any, **kwargs: Any) -> tuple[bool, int, str]:
        # Always update successfully with final_count set to number of parsed events passed
        event_window_ref = args[0]
        # For unit tests we don't exercise internals; return updated True
        return True, kwargs.get("window_size", 0), "ok"


class DummyMonitoringLogger:
    def __call__(self, *args: Any, **kwargs: Any) -> None:
        # No-op for tests
        return None


@pytest.mark.asyncio
async def test_fetch_all_sources_when_no_sources_then_returns_empty() -> None:
    """test_fetch_all_sources_when_no_sources_then_returns_empty"""
    orchestrator = FetchOrchestrator(fetch_and_parse_source=lambda *a, **k: None,
                                     window_manager=None,
                                     health_tracker=None,
                                     monitoring_logger=lambda *a, **k: None)
    result = await orchestrator.fetch_all_sources([], fetch_concurrency=2, rrule_days=7)
    assert result == []


@pytest.mark.asyncio
async def test_fetch_all_sources_when_tasks_return_events_then_combines(monkeypatch) -> None:
    """test_fetch_all_sources_when_tasks_return_events_then_combines"""
    # Fake fetch_and_parse_source that returns a list of events
    async def fake_fetch_and_parse(semaphore, src_cfg, rrule_days, shared_http_client):
        # Acquire semaphore to simulate concurrency gating
        async with semaphore:
            await asyncio.sleep(0)  # yield control
            return [{"source": src_cfg["name"], "id": 1}]

    # Create orchestrator instance under test
    orchestrator_obj = FetchOrchestrator(
        fetch_and_parse_source=fake_fetch_and_parse,
        window_manager=DummyWindowManager(),
        health_tracker=DummyHealthTracker(),
        monitoring_logger=DummyMonitoringLogger(),
    )

    # Provide a real-like orchestrator with gather_with_timeout implementation
    class FakeOrch:
        async def gather_with_timeout(self, *tasks, timeout: float, return_exceptions: bool):
            # Await underlying tasks via asyncio.gather to simulate orchestration behavior
            return await asyncio.gather(*tasks, return_exceptions=return_exceptions)

    # Patch async_utils.get_global_orchestrator used inside fetch_all_sources
    monkeypatch.setattr("calendarbot_lite.async_utils.get_global_orchestrator", lambda: FakeOrch())

    sources = [{"name": "a"}, {"name": "b"}]
    parsed = await orchestrator_obj.fetch_all_sources(sources, fetch_concurrency=2, rrule_days=5)
    # Should combine two lists (one per source)
    assert isinstance(parsed, list)
    assert len(parsed) == 2
    assert {e["source"] for e in parsed} == {"a", "b"}


@pytest.mark.asyncio
async def test_fetch_all_sources_when_task_raises_then_skips_and_continues(monkeypatch) -> None:
    """test_fetch_all_sources_when_task_raises_then_skips_and_continues"""
    async def ok_fetch(semaphore, src_cfg, rrule_days, shared_http_client):
        async with semaphore:
            await asyncio.sleep(0)
            return [{"source": src_cfg["name"], "id": 1}]

    async def bad_fetch(semaphore, src_cfg, rrule_days, shared_http_client):
        async with semaphore:
            await asyncio.sleep(0)
            raise RuntimeError("boom")

    # We'll route based on source name
    async def dispatch_fetch(semaphore, src_cfg, rrule_days, shared_http_client):
        if src_cfg.get("bad"):
            return await bad_fetch(semaphore, src_cfg, rrule_days, shared_http_client)
        return await ok_fetch(semaphore, src_cfg, rrule_days, shared_http_client)

    orchestrator_obj = FetchOrchestrator(
        fetch_and_parse_source=dispatch_fetch,
        window_manager=DummyWindowManager(),
        health_tracker=DummyHealthTracker(),
        monitoring_logger=DummyMonitoringLogger(),
    )

    class FakeOrch:
        async def gather_with_timeout(self, *tasks, timeout: float, return_exceptions: bool):
            return await asyncio.gather(*tasks, return_exceptions=return_exceptions)

    monkeypatch.setattr("calendarbot_lite.async_utils.get_global_orchestrator", lambda: FakeOrch())

    sources = [{"name": "ok"}, {"name": "fail", "bad": True}, {"name": "also_ok"}]
    parsed = await orchestrator_obj.fetch_all_sources(sources, fetch_concurrency=2, rrule_days=3)
    # One task raised, two succeeded => 2 events
    assert isinstance(parsed, list)
    assert len(parsed) == 2
    assert {e["source"] for e in parsed} == {"ok", "also_ok"}
