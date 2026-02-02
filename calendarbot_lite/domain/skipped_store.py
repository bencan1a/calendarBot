"""JSON-backed skipped-store for calendarbot_lite with 24-hour expiry and atomic writes."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def is_event_skipped(event_id: str, store: object | None) -> bool:
    """Check if an event is skipped using a skipped store.

    This is a shared utility function that safely handles:
    - None stores (returns False)
    - Stores without is_skipped method (returns False)
    - Exceptions from is_skipped (logs warning, returns False)

    Args:
        event_id: The event/meeting ID to check
        store: Optional object with is_skipped(event_id) method

    Returns:
        True if event is skipped, False otherwise
    """
    if store is None:
        return False

    is_skipped_fn = getattr(store, "is_skipped", None)
    if not callable(is_skipped_fn):
        return False

    try:
        result = is_skipped_fn(event_id)
        return bool(result)
    except Exception as e:
        logger.warning("skipped_store.is_skipped raised: %s", e)
        return False


def _now_utc() -> datetime:
    """Return current UTC time as an aware datetime.

    Uses centralized datetime override from timezone_utils that supports CALENDARBOT_TEST_TIME.
    """
    from calendarbot_lite.core.timezone_utils import now_utc

    return now_utc()


def _parse_iso(s: str) -> datetime:
    """Parse ISO-8601 string into an aware UTC datetime.

    Accepts strings with 'Z' or an offset.
    """
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


class SkippedStore:
    """Persistent skipped-store for meeting IDs with 24-hour expiry.

    The on-disk format is a JSON object mapping meeting_id -> expiry_iso.
    All times are stored as ISO-8601 strings with timezone information.
    """

    def __init__(self, path: str | None = None) -> None:
        """Create a SkippedStore.

        Args:
            path: Optional path to JSON file. Defaults to package-local
                'calendarbot_lite/skipped.json'.
        """
        if path:
            self._path = Path(path)
        else:
            self._path = Path(__file__).resolve().parent.joinpath("skipped.json")

        self._lock = threading.Lock()
        # in-memory mapping meeting_id -> expiry datetime (aware UTC)
        self._store: dict[str, datetime] = {}

        # Ensure parent directory exists
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Best-effort: do not fail imports if filesystem permissions restrict creation.
            logger.debug("Could not ensure directory for skipped store: %s", self._path.parent)

        # Load existing data if present
        try:
            self.load()
        except Exception as exc:
            logger.warning("Failed to load skipped store %s: %s", self._path, exc)

    def load(self) -> None:
        """Load JSON from disk (if exists), purge expired entries, and populate memory.

        This method is idempotent and safe to call multiple times.
        """
        with self._lock:
            if not self._path.exists():
                logger.debug("Skipped store file not found; starting empty: %s", self._path)
                self._store = {}
                return

            try:
                with self._path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if not isinstance(data, dict):
                    raise ValueError("skipped store JSON root must be an object")  # noqa: TRY004
            except Exception as exc:
                logger.warning("Failed to read skipped store %s: %s", self._path, exc)
                self._store = {}
                return

            now = _now_utc()
            store: dict[str, datetime] = {}
            for k, v in data.items():
                try:
                    if not k or not isinstance(k, str):
                        continue
                    if not isinstance(v, str):
                        continue
                    expiry = _parse_iso(v)
                    if expiry <= now:
                        # expired, skip
                        continue
                    store[k] = expiry
                except Exception:
                    # skip malformed entries
                    continue  # nosec B112 - skip malformed entries in persisted store

            self._store = store
            logger.debug(
                "Loaded skipped store %s (%d active entries)", self._path, len(self._store)
            )

    def _persist(self) -> None:
        """Persist current in-memory store to disk atomically.

        Writes to a temporary file in the same directory then os.replace() into place.
        """
        # Prepare serializable mapping
        data: dict[str, str] = {k: v.isoformat() for k, v in self._store.items()}

        dirpath = self._path.parent
        # Use NamedTemporaryFile in same dir to ensure atomic replace on same filesystem.
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", dir=dirpath, delete=False, encoding="utf-8"
            ) as tf:
                tmp_path = Path(tf.name)
                json.dump(data, tf, ensure_ascii=False)
                tf.flush()
                with contextlib.suppress(Exception):
                    os.fsync(tf.fileno())

            # Replace into place
            try:
                # prefer Path.replace for atomic semantics
                tmp_path.replace(self._path)
            except Exception:
                # fallback to Path.replace variation for older platforms/edge cases
                Path(str(tmp_path)).replace(self._path)
        except Exception as exc:
            logger.warning("Failed to persist skipped store to %s: %s", self._path, exc)
            # Cleanup temp file if present
            try:
                if tmp_path and tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass  # nosec B110 - best effort cleanup of temp file

    def add_skip(self, meeting_id: str) -> str:
        """Add meeting_id with expiry 24 hours from now and persist.

        Args:
            meeting_id: Non-empty meeting identifier string.

        Returns:
            ISO-8601 UTC expiry timestamp string.

        Raises:
            ValueError: if meeting_id is invalid.
        """
        if not meeting_id or not isinstance(meeting_id, str):
            raise ValueError("meeting_id must be a non-empty string")

        with self._lock:
            # Purge expired entries before adding
            self._purge_expired_locked()

            expiry = _now_utc() + timedelta(hours=24)
            self._store[meeting_id] = expiry

            try:
                self._persist()
            except Exception as exc:
                # If persistence fails, remove the in-memory entry to avoid inconsistency.
                with contextlib.suppress(Exception):
                    del self._store[meeting_id]
                logger.warning("Failed to persist new skip for %s: %s", meeting_id, exc)
                raise

            iso = expiry.isoformat()
            logger.info("Added skip for %s until %s", meeting_id, iso)
            return iso

    def is_skipped(self, meeting_id: str) -> bool:
        """Return True if meeting_id is currently skipped (not expired).

        Args:
            meeting_id: Meeting identifier to check.

        Returns:
            True if skip exists and is not expired; False otherwise.
        """
        if not meeting_id or not isinstance(meeting_id, str):
            return False

        with self._lock:
            expiry = self._store.get(meeting_id)
            if expiry is None:
                return False
            if expiry <= _now_utc():
                # expired; remove from in-memory but do not persist per spec
                with contextlib.suppress(KeyError):
                    del self._store[meeting_id]
                return False
            return True

    def clear_all(self) -> int:
        """Remove all skip entries, persist, and return count cleared.

        Returns:
            Number of entries removed.
        """
        with self._lock:
            count = len(self._store)
            self._store = {}
            try:
                self._persist()
            except Exception as exc:
                logger.warning("Failed to persist cleared skipped store: %s", exc)
                raise

            logger.info("Cleared all skipped entries (%d)", count)
            return count

    def active_list(self) -> dict[str, str]:
        """Return mapping meeting_id -> expiry_iso for active (non-expired) entries.

        Expired entries are not included.
        """
        with self._lock:
            now = _now_utc()
            result: dict[str, str] = {}
            # Do not persist purged entries here per spec; keep in-memory accurate.
            to_delete = []
            for k, v in self._store.items():
                if v <= now:
                    to_delete.append(k)
                else:
                    result[k] = v.isoformat()

            for k in to_delete:
                with contextlib.suppress(KeyError):
                    del self._store[k]

            return result

    def _purge_expired_locked(self) -> None:
        """Purge expired entries from in-memory store. Called with lock held."""
        now = _now_utc()
        keys = [k for k, v in self._store.items() if v <= now]
        for k in keys:
            with contextlib.suppress(KeyError):
                del self._store[k]
