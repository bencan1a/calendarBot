"""Concurrency tests for calendarbot_lite.SkippedStore ensuring thread-safety."""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from calendarbot_lite.domain.skipped_store import SkippedStore

pytestmark = pytest.mark.integration


def _read_json_file(path: Path) -> dict[str, Any]:
    """Read JSON file at path and return parsed object."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _assert_file_well_formed(path: Path) -> None:
    """Assert JSON file contains mapping of str->iso datetime strings."""
    data = _read_json_file(path)
    assert isinstance(data, dict)
    for k, v in data.items():
        assert isinstance(k, str)
        assert isinstance(v, str)
        # should parse as ISO-8601
        datetime.fromisoformat(v)


def test_concurrent_adds_thread_safety(tmp_path: Path) -> None:
    """Multiple threads adding unique skips concurrently should be safe."""
    path = tmp_path / "skipped.json"
    store = SkippedStore(str(path))

    n_threads = 10
    barrier = threading.Barrier(n_threads + 1)
    exceptions: list[Exception] = []

    def worker(i: int) -> None:
        try:
            barrier.wait()
            mid = f"meeting-{i}"
            store.add_skip(mid)
        except Exception as exc:  # pragma: no cover - surface any thread errors
            exceptions.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()

    # Release all workers
    barrier.wait()
    for t in threads:
        t.join(timeout=5)

    assert not exceptions, f"Thread exceptions: {exceptions}"

    active = store.active_list()
    assert len(active) == n_threads
    # Ensure file is well formed and contains same keys
    _assert_file_well_formed(path)
    file_data = _read_json_file(path)
    assert set(file_data.keys()) == set(active.keys())


@pytest.mark.slow
def test_concurrent_adds_and_clears(tmp_path: Path) -> None:
    """Mixed add and clear operations concurrently should not corrupt file."""
    path = tmp_path / "skipped.json"
    store = SkippedStore(str(path))

    adders = 20
    clearers = 3
    total = adders + clearers
    barrier = threading.Barrier(total + 1)
    exceptions: list[Exception] = []

    def adder(i: int) -> None:
        try:
            barrier.wait()
            store.add_skip(f"a-{i}")
        except Exception as exc:
            exceptions.append(exc)

    def clearer(_i: int) -> None:
        try:
            barrier.wait()
            store.clear_all()
        except Exception as exc:
            exceptions.append(exc)

    threads = []
    for i in range(adders):
        threads.append(threading.Thread(target=adder, args=(i,)))
    for i in range(clearers):
        threads.append(threading.Thread(target=clearer, args=(i,)))

    for t in threads:
        t.start()
    barrier.wait()
    for t in threads:
        t.join(timeout=5)

    assert not exceptions, f"Thread exceptions during mixed ops: {exceptions}"

    # File should be a dict and well-formed JSON
    _assert_file_well_formed(path)

    # Re-load from disk into a fresh instance and ensure structure is valid
    fresh = SkippedStore(str(path))
    disk = fresh.active_list()
    assert isinstance(disk, dict)
    for k, v in disk.items():
        assert isinstance(k, str)
        assert isinstance(v, str)
        datetime.fromisoformat(v)


@pytest.mark.slow
@pytest.mark.xfail(reason="Known race on concurrent instance read/write without file locking; see TODO", strict=False)
def test_concurrent_multiple_instances_load_save(tmp_path: Path) -> None:
    """Concurrent initialization and saves from multiple SkippedStore instances."""
    path = tmp_path / "skipped.json"

    # Prepopulate file with a known entry to exercise concurrent load
    initial = {"pre": datetime.utcnow().isoformat()}  # type: ignore[arg-type]
    path.write_text(json.dumps(initial), encoding="utf-8")

    n_threads = 8
    barrier = threading.Barrier(n_threads + 1)
    exceptions: list[Exception] = []

    def inst_worker(i: int) -> None:
        try:
            barrier.wait()
            s = SkippedStore(str(path))
            s.add_skip(f"inst-{i}")
            # explicitly load to exercise concurrent reads
            s.load()
        except Exception as exc:
            exceptions.append(exc)

    threads = [threading.Thread(target=inst_worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    barrier.wait()
    for t in threads:
        t.join(timeout=5)

    assert not exceptions, f"Instance thread exceptions: {exceptions}"

    final = SkippedStore(str(path))
    keys = set(final.active_list().keys())
    # Expect all instance keys plus pre
    for i in range(n_threads):
        assert f"inst-{i}" in keys
    assert "pre" in keys


def test_high_contention_same_key(tmp_path: Path) -> None:
    """Many threads adding the same key should not create duplicates or corrupt state."""
    path = tmp_path / "skipped.json"
    store = SkippedStore(str(path))

    n_threads = 25
    barrier = threading.Barrier(n_threads + 1)
    exceptions: list[Exception] = []

    def worker() -> None:
        try:
            barrier.wait()
            store.add_skip("same-key")
        except Exception as exc:
            exceptions.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    barrier.wait()
    for t in threads:
        t.join(timeout=5)

    assert not exceptions, f"Contention exceptions: {exceptions}"
    active = store.active_list()
    assert len(active) == 1
    assert "same-key" in active
    # File contains single entry
    data = _read_json_file(path)
    assert isinstance(data, dict)
    assert len(data) == 1
    assert "same-key" in data
