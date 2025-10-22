# calendarbot_lite

Lightweight, isolated skeleton for a minimal CalendarBot application intended for fast development
and experimentation without pulling in the full CalendarBot runtime.

Purpose
-------
calendarbot_lite will provide a small, self-contained server and tooling surface that reuses the
core ICS parsing code from the main CalendarBot project but keeps its runtime and configuration
surface intentionally small for easier iteration.

Isolation and reuse
-------------------
This package is isolated from the main project codebase. It intentionally does NOT copy or import
the full CalendarBot application at package import time. When appropriate, calendarbot_lite will
reuse the following existing parser modules from the main project:

- [`calendarbot/ics/parser.py`](calendarbot/ics/parser.py:1)
- [`calendarbot/ics/rrule_expander.py`](calendarbot/ics/rrule_expander.py:1)
- [`calendarbot/sources/ics_source.py`](calendarbot/sources/ics_source.py:1)

NOTE: Those modules will be imported only at runtime (inside server or workers) to avoid heavy
startup costs and ensure the package remains lightweight when inspected.

Next steps
----------
Planned immediate next tasks:

- Implement `calendarbot_lite/server.py` with a small HTTP API and background refresher.
- Add a `skipped-store` lightweight cache implementation tailored for the lite app.
- Implement a small config loader that overlays defaults for quick developer setup.
- Add unit tests for new modules under `tests/test_calendarbot_lite_*.py`.

Developer quickstart
--------------------
In development you can run the package with:

python -m calendarbot_lite

Since the server is not implemented yet, this will print a friendly message explaining how to proceed.

Where to add files
------------------
Add the runtime code under the package directory:

- `calendarbot_lite/server.py` - HTTP server and background tasks
- `calendarbot_lite/config.py` - configuration loader & defaults
- `calendarbot_lite/store.py` - lightweight skipped-store cache
- `tests/test_calendarbot_lite_server.py` - tests for server behavior

License & notes
---------------
This skeleton is intended to be a minimal first step. Keep imports inside functions to keep top-level
import cheap and fast for editor tooling and test discovery.