"""
Tests for calendarbot_lite config loader and skipped-store.

Imports:
- calendarbot_lite.config_loader as cfg
- calendarbot_lite.skipped_store as ss

Run with:
    pytest tests/lite/test_config_and_skipped_store.py -q
"""

import json
from datetime import datetime, timedelta, timezone

import calendarbot_lite.config_loader as cfg
import calendarbot_lite.skipped_store as ss


def test_from_dict_applies_defaults():
    """Config.from_dict applies defaults when only sources provided."""
    data = {"sources": ["https://example.com/cal.ics"]}
    conf = cfg.Config.from_dict(data)

    # Defaults asserted exactly as specified by the dataclass
    assert conf.refresh_interval_seconds == 300
    assert conf.rrule_expansion_days == 14
    assert conf.event_window_size == 5
    assert conf.server_bind == "0.0.0.0"
    assert conf.server_port == 8080


def test_load_config_reads_yaml_and_overrides(tmp_path):
    """load_config reads a file and uses values from it (overriding defaults)."""
    # Create a config file; JSON is acceptable input for the loader fallback
    cfg_path = tmp_path / "cfg.yaml"
    payload = {
        "sources": ["https://one.example/cal.ics", "https://two.example/cal.ics"],
        "refresh_interval_seconds": 120,
        "rrule_expansion_days": 7,
        "event_window_size": 10,
        "server_bind": "127.0.0.1",
        "server_port": 9090,
        "log_level": "debug",
    }
    cfg_path.write_text(json.dumps(payload), encoding="utf-8")

    conf = cfg.load_config(path=str(cfg_path))

    # Assert values exactly match those specified in file
    assert conf.sources == payload["sources"]
    assert conf.refresh_interval_seconds == 120
    assert conf.rrule_expansion_days == 7
    assert conf.event_window_size == 10
    assert conf.server_bind == "127.0.0.1"
    assert conf.server_port == 9090
    # log_level should be uppercased by loader
    assert conf.log_level == "DEBUG"


def test_add_is_skipped_and_active_list(tmp_path):
    """add_skip returns an ISO expiry ~24h from now and membership checks succeed."""
    store_path = tmp_path / "skipped.json"
    store = ss.SkippedStore(path=str(store_path))

    now = datetime.now(timezone.utc)
    iso = store.add_skip("test-id")

    # Parse returned ISO and verify it's between 23h and 25h from now
    expiry = datetime.fromisoformat(iso)
    lower = now + timedelta(hours=23)
    upper = now + timedelta(hours=25)
    assert lower <= expiry <= upper, "expiry not within expected 23h..25h window"

    # The store should report the id as skipped and present it in active_list
    assert store.is_skipped("test-id") is True
    active = store.active_list()
    assert "test-id" in active
    # active_list returns ISO strings; confirm they parse
    assert datetime.fromisoformat(active["test-id"])


def test_expiry_purged_on_load(tmp_path):
    """Expired entries on-disk are purged when loading the store."""
    store_path = tmp_path / "skipped.json"

    now = datetime.now(timezone.utc)
    old_iso = (now - timedelta(days=2)).isoformat()  # older than 24h, should be purged
    good_iso = (now + timedelta(hours=2)).isoformat()  # in future, should remain

    data = {"old-id": old_iso, "good-id": good_iso}
    store_path.write_text(json.dumps(data), encoding="utf-8")

    store = ss.SkippedStore(path=str(store_path))
    # load() is invoked in ctor, but call explicitly to be clear in test
    store.load()

    active = store.active_list()
    assert "good-id" in active
    assert "old-id" not in active


def test_clear_all_returns_count_and_persists(tmp_path):
    """clear_all removes all entries, returns the count, and writes empty JSON on disk."""
    store_path = tmp_path / "skipped.json"
    store = ss.SkippedStore(path=str(store_path))

    # Add multiple entries (N >= 2)
    ids = ["a", "b", "c"]
    for i in ids:
        store.add_skip(i)

    # clear_all should return number cleared
    cleared = store.clear_all()
    assert cleared == len(ids)

    # active_list must be empty in-memory
    assert store.active_list() == {}

    # On-disk JSON should be an empty object
    on_disk = json.loads(store_path.read_text(encoding="utf-8"))
    assert on_disk == {}
