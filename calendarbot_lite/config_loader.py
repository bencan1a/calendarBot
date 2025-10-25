"""calendarbot_lite.config_loader

Lightweight config loader for calendarbot_lite.

- Prefers YAML (PyYAML) if available, falls back to JSON.
- Minimal imports at module import time to keep startup light.
- Exposes a typed dataclass `Config` and a `load_config()` helper that accepts
  an optional path override.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Typed configuration for calendarbot_lite.

    Fields:
        sources: list of ICS source URLs or descriptors (0-3 items)
        refresh_interval_seconds: how often to refresh (60..1800)
        rrule_expansion_days: days to expand RRULEs
        event_window_size: number of upcoming events to keep
        server_bind: host to bind the HTTP server to
        server_port: port for the HTTP server
        log_level: logging level name
        alexa_bearer_token: optional bearer token for Alexa API authentication
    """

    sources: list[str]
    refresh_interval_seconds: int = 300
    rrule_expansion_days: int = 14
    event_window_size: int = 5
    server_bind: str = "0.0.0.0"  # nosec: B104 - intentional default for local/dev; can be overridden via config/env
    server_port: int = 8080
    log_level: str = "INFO"
    alexa_bearer_token: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Create Config from a plain mapping, applying defaults and validation.

        This method is conservative about types: it coerces numeric-like values to int,
        ensures sources is a list of strings (truncating to 3 items), and enforces bounds
        for refresh_interval_seconds (60..1800), logging warnings when coercions occur.
        """
        if data is None:
            data = {}

        # Sources: accept legacy key `ics_sources` as well
        sources_raw = data.get("sources") if "sources" in data else data.get("ics_sources", [])
        if sources_raw is None:
            sources_raw = []
        if not isinstance(sources_raw, (list, tuple)):
            logger.warning("Config `sources` is not a list; coercing to single-item list")
            sources_list: list[str] = [str(sources_raw)]
        else:
            sources_list = [str(s) for s in sources_raw]

        # Limit sources to 3 entries
        if len(sources_list) > 3:
            logger.warning("Config `sources` has %d items; truncating to 3", len(sources_list))
            sources_list = sources_list[:3]

        def _coerce_int(key: str, default: int) -> int:
            raw = data.get(key, default)
            try:
                return int(raw)
            except Exception:
                logger.warning("Config %s=%r is not an int; using default %d", key, raw, default)
                return default

        refresh = _coerce_int("refresh_interval_seconds", 300)
        # enforce allowed range 60..1800
        if refresh < 60:
            logger.warning("refresh_interval_seconds %d below minimum; coercing to 60", refresh)
            refresh = 60
        elif refresh > 1800:
            logger.warning("refresh_interval_seconds %d above maximum; coercing to 1800", refresh)
            refresh = 1800

        rrule_days = _coerce_int("rrule_expansion_days", 14)
        event_window = _coerce_int("event_window_size", 5)
        server_port = _coerce_int("server_port", 8080)

        server_bind = data.get("server_bind", "0.0.0.0")  # nosec: B104 - default used for local development; configurable via env/config
        server_bind = str(server_bind) if server_bind is not None else "0.0.0.0"  # nosec: B104 - fallback literal for empty/missing config

        log_level = data.get("log_level", "INFO")
        log_level = str(log_level).upper() if log_level is not None else "INFO"

        alexa_bearer_token = data.get("alexa_bearer_token")
        if alexa_bearer_token is not None:
            alexa_bearer_token = str(alexa_bearer_token)

        return cls(
            sources=sources_list,
            refresh_interval_seconds=refresh,
            rrule_expansion_days=rrule_days,
            event_window_size=event_window,
            server_bind=server_bind,
            server_port=server_port,
            log_level=log_level,
            alexa_bearer_token=alexa_bearer_token,
        )


def _load_yaml_or_json(path: Path) -> dict[str, Any]:
    """
    Load a mapping from a YAML or JSON file.

    Prefers PyYAML if available; falls back to JSON and raises a helpful error if neither works.
    Heavy import of `yaml` is performed lazily inside this function to avoid increasing
    package import cost on constrained devices.
    """
    text = path.read_text()
    try:
        import yaml  # type: ignore  # noqa: PLC0415
    except Exception:
        # Fall back to JSON parsing
        try:
            return json.loads(text)
        except Exception as exc:
            raise RuntimeError(
                "Unable to parse config: PyYAML not installed and file is not valid JSON. "
                "Install pyyaml (`pip install pyyaml`) or provide a JSON formatted config."
            ) from exc
    else:
        loaded = yaml.safe_load(text)
        # safe_load can return None for empty files; normalize to empty dict
        if loaded is None:
            return {}
        if not isinstance(loaded, dict):
            # Return the raw loaded value (caller will validate mapping)
            return loaded
        return loaded


def load_config(path: str | None = None) -> Config:
    """Load configuration from a YAML/JSON file and return a Config instance.

    Args:
        path: Optional path to the config file. If not provided the default is
              ./calendarbot_lite/config.yaml (relative to current working dir).

    Returns:
        Config dataclass instance with values from file (or defaults).

    Behavior:
    - If file is missing: returns Config(sources=[]) with defaults.
    - If file exists but top-level is not a mapping: raises ValueError.
    - If PyYAML is not installed and the file is not valid JSON: raises RuntimeError
      instructing the user to install pyyaml or provide JSON.
    """
    p = Path(path) if path else Path.cwd() / "calendarbot_lite" / "config.yaml"
    logger.debug("Attempting to load config from %s", p)
    if not p.exists():
        logger.info("Config file %s not found; using defaults", p)
        cfg = Config(sources=[])
        logger.debug("Default Config in use: %s", cfg)
        return cfg

    raw = _load_yaml_or_json(p)
    if not isinstance(raw, dict):
        logger.warning("Config file %s parsed but top-level is not a mapping: %r", p, raw)
        raise ValueError("Config file must contain a mapping at top level")  # noqa: TRY004
    cfg = Config.from_dict(raw)
    logger.info("Loaded configuration from %s", p)
    logger.debug("Configuration values: %s", cfg)
    return cfg
