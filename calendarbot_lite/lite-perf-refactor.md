Architectural plans for the three performance refactorings (target: Pi Zero 2W). All designs preserve API compatibility with the lite server path [`calendarbot_lite/server.py`](calendarbot_lite/server.py:1) and reference the forked modules such as [`calendarbot_lite/lite_fetcher.py`](calendarbot_lite/lite_fetcher.py:1), [`calendarbot_lite/lite_parser.py`](calendarbot_lite/lite_parser.py:1), [`calendarbot_lite/lite_rrule_expander.py`](calendarbot_lite/lite_rrule_expander.py:1), and [`calendarbot_lite/lite_models.py`](calendarbot_lite/lite_models.py:1).

Summary: Three refactors are designed to (1) make fetch decisions based on Content-Length and heuristics, (2) create a streaming pipeline from HTTP response into the streaming parser (no intermediate full-buffer strings), and (3) bound concurrency for fetching + move RRULE expansion to a worker queue with strict limits. Each design is pragmatic, low-dependency, and tuned for ~512MB RAM + single-core CPU.

===============================================================================
REFRACTOR 1 — Smart HTTP Streaming Based on Content-Length Headers
===============================================================================

1. High-level architecture diagram (text)
- Mermaid flow (text)
  ```mermaid
  flowchart LR
    A[Refresh job in server] --> B[LiteICSFetcher.fetch_ics(source)]
    B --> C{HEAD or GET?}
    C -->|Has Content-Length and <= threshold| D[GET buffer entire body]
    C -->|Has Content-Length and > threshold| E[GET stream into streaming parser]
    C -->|No Content-Length (chunked)| F[GET stream with heuristic fast-path]
    D --> G[lite_parser.parse_ics_content(whole string)]
    E --> H[lite_parser.parse_ics_stream(response.iter_bytes())]
    F --> H
    G --> I[LiteRRuleExpander or worker queue]
    H --> I
  ```

2. Key design decisions and rationale for Pi Zero 2W
- Primary decision point: use Content-Length header to choose buffering vs streaming.
  - If Content-Length present and small (< STREAM_THRESHOLD, e.g. 256KB–1MB), perform existing buffered flow to preserve current behavior and fast parse.
  - If Content-Length present and large (> STREAM_THRESHOLD), select streaming GET to feed parser directly to avoid allocating whole-body string.
  - If no Content-Length (chunked transfer), apply a conservative streaming heuristic: start streaming immediately but optionally buffer first N KB to detect ICS header patterns or encodings.
- Rationale: Pi Zero 2W memory is limited. Avoid copying large responses into memory. Content-Length is cheap and widely available; heuristics handle chunked responses.

3. API changes needed in the lite components
- [`calendarbot_lite/lite_fetcher.py`](calendarbot_lite/lite_fetcher.py:1)
  - Add new method/flag on LiteICSResponse: streamable: bool (indicates response contains streaming body handle).
  - Add optional response.stream (an async iterator or httpx.Response object) when streaming is used.
  - Add method fetch_ics(source, prefer_stream: Optional[bool] = None) -> LiteICSResponse. prefer_stream is default None; decision still controlled inside fetcher by Content-Length and config.
- Backwards compatibility:
  - Existing code paths expecting LiteICSResponse.content (string) continue for buffered responses.
  - When response.stream is populated, response.content remains None. Consumers (parser) must handle both variants. Provide utility function: get_content_or_stream(response) to preserve compatibility.
- Minor model change in [`calendarbot_lite/lite_models.py`](calendarbot_lite/lite_models.py:1): add fields:
  - stream_handle: Optional[object] = None
  - stream_mode: Optional[str] = None  # "bytes" or "lines"
  - Keep content property untouched.

4. Integration points with existing server
- [`calendarbot_lite/server.py`](calendarbot_lite/server.py:1) continues to call LiteICSFetcher.fetch_ics; if fetch returns a stream_handle, pass it to parser via new parse_ics_stream API in [`calendarbot_lite/lite_parser.py`](calendarbot_lite/lite_parser.py:1). No server API changes required; fetcher retains same method name and return type (LiteICSResponse), only additional optional fields added.

5. Memory and CPU optimization strategies
- Use Content-Length to avoid allocating full-body bytes for large responses.
- For streaming decisions, set STREAM_THRESHOLD default to small (e.g., 256KB) but configurable.
- Avoid double-decoding: stream bytes to parser, let parser decode incremental chunks.
- Use a small read buffer (e.g., 8KB–32KB) to limit peak memory usage.
- For chunked responses, limit initial buffered lookahead to e.g., 8KB to detect ICS header lines; avoid unlimited buffering.

6. Configuration options for resource tuning
- stream_threshold_bytes (default 262144, i.e., 256KB)
- min_stream_threshold_bytes (minimum allowed)
- prefer_stream: tri-state (auto|force|never) for debugging/profiling
- initial_buffer_bytes_for_chunked (default 8192)
- read_chunk_size_bytes (default 8192)

7. Implementation complexity assessment
- Medium. Required changes in fetcher return model and careful handling of stream objects. Must add tests confirming backward compatibility for buffered responses and new streaming flows.

8. Dependencies and potential risks
- Dependencies: httpx (already used), plus small adapter code to expose async iterators. No new package required.
- Risks:
  - Some servers omit Content-Length or misreport it.
  - Older code may assume response.content is always str — ensure defensive handling.
  - Need careful exception handling when streaming to avoid leaked sockets.

===============================================================================
REFRACTOR 2 — Streaming Pipeline from HTTP Response to Parser
===============================================================================

1. High-level architecture diagram (text)
- Mermaid flow (text)
  ```mermaid
  sequenceDiagram
    participant Server
    participant Fetcher
    participant Parser
    Server->>Fetcher: fetch_ics(source)
    Fetcher->>Parser: parse_ics_stream(async_byte_iter)
    Parser->>Parser: incremental assembly of folded lines, handle CRLF boundaries
    Parser->>RRuleWorker: emit events or event skeletons
    RRuleWorker-->>Server: completed expanded events
  ```

2. Key design decisions and rationale for Pi Zero 2W
- Build an async generator interface for streaming bytes/lines: parser accepts an AsyncIterator[bytes] or AsyncIterator[str].
- Parser must be able to:
  - Accept partial lines across chunk boundaries (line folding per RFC5545).
  - Decode bytes incrementally with incremental UTF-8 decoder to avoid encoding errors.
  - Maintain a minimal state machine for parsing VEVENT boundaries without full-file buffering.
- Rationale: streaming eliminates intermediate large string allocations and copying; incremental decoding reduces peak memory pressure.

3. API changes needed in the lite components
- [`calendarbot_lite/lite_fetcher.py`](calendarbot_lite/lite_fetcher.py:1)
  - Provide response.stream_handle as an AsyncIterator of bytes (or an httpx.Response capable of aiter_bytes()).
  - Helper: fetcher.stream_response(response) -> AsyncIterator[bytes]
- [`calendarbot_lite/lite_parser.py`](calendarbot_lite/lite_parser.py:1)
  - Add parse_ics_stream(stream: AsyncIterator[bytes], source_url: Optional[str] = None) -> LiteICSParseResult
  - Existing parse_ics_content(ics_content: str, ...) remains unchanged.
  - Internally reuse streaming lower-level parser: LiteStreamingICSParser.parse_from_bytes_iter()
- Maintain backward compatibility:
  - The public API parse_ics_content remains available.
  - When fetcher returns stream_handle, server will call parse_ics_stream; otherwise it calls parse_ics_content with response.content.

4. Integration points with existing server
- [`calendarbot_lite/server.py`](calendarbot_lite/server.py:1) logic:
  - When receiving LiteICSResponse:
    - If response.stream_handle present -> call parser.parse_ics_stream(response.stream_handle)
    - Else -> call parser.parse_ics_content(response.content)
  - These branches preserve server's original callsite shape while enabling streaming.

5. Memory and CPU optimization strategies
- Stream in small chunks (8KB default) and reuse a small parser buffer.
- Use incremental codecs (codecs.getincrementaldecoder("utf-8")) to decode bytes to strings only as needed.
- Avoid creating intermediate large strings; keep line buffers bounded (max_line_length config).
- Pre-allocate small object pools for event skeleton objects if necessary to avoid frequent allocations — but prefer simple approach first.
- Provide an option to stream parse to a temporary file on disk (rotating) for extremely large feeds as fallback (useful for debugging or when out-of-memory otherwise), but keep default in-memory stream parsing.

6. Configuration options for resource tuning
- read_chunk_size_bytes (default 8192)
- max_line_length_bytes (default 32_768)
- enable_tempfile_fallback: bool (default False)
- tempdir_for_streams (if enabled)
- stream_decode_errors: 'strict' | 'replace' (default 'replace')

7. Implementation complexity assessment
- High. Accurate streaming parser must correctly handle line folding, multi-byte UTF-8 boundaries, CRLF normalization, and long folded lines. Requires comprehensive unit tests and fuzzing with chunk boundaries.

8. Dependencies and potential risks
- Dependencies: no new runtime libs; use Python stdlib incremental decoder and existing httpx async streaming.
- Risks:
  - Subtle parsing bugs introduced by chunk boundaries (line folding errors).
  - Edge cases: mixed encodings or very long lines might trigger errors.
  - Need robust tests using chunked inputs that simulate real-world ICS servers.

===============================================================================
REFRACTOR 3 — Bounded Concurrency and Worker-Based RRULE Expansion
===============================================================================

1. High-level architecture diagram (text)
- Mermaid flow (text)
  ```mermaid
  flowchart LR
    A[Periodic Refresh Scheduler] --> B[Fetch worker pool (bounded concurrency N)]
    B --> C[LiteICSFetcher.fetch_ics]
    C --> D[Parser parse_ics_stream or parse_ics_content]
    D --> E{Event list with RRULEs}
    E -->|Has RRULEs| F[RRULE Expansion Worker Queue]
    F --> G[Worker thread or process or async task pool]
    G --> H[Persist expanded events to in-memory cache]
    H --> I[Server API serves cached events immediately]
  ```

2. Key design decisions and rationale for Pi Zero 2W
- Bounded fetch concurrency: default 2 concurrent fetches (configurable 1..3). Rationale: Pi Zero 2W single core means network IO benefits from concurrency but CPU-heavy tasks (parsing/expansion) must be limited.
- RRULE expansion must be offloaded to a background worker pool to avoid blocking the main refresh + web server thread. Worker options:
  - Preferred: asyncio.Task-based worker pool running in same process but ensuring expansions yield to event loop by chunked expansion.
  - Alternative (if expansions still block): spawn a single background ProcessPoolExecutor worker process for expansions to avoid GIL-bound CPU blocking (more complex).
- Expansion controls: max_expansion_occurrences and expansion_time_window to cap work and prevent runaway CPU/memory.

3. API changes needed in the lite components
- [`calendarbot_lite/lite_rrule_expander.py`](calendarbot_lite/lite_rrule_expander.py:1)
  - Add non-blocking API: expand_rrule_async(event, limits) -> AsyncIterator[partial_result] or returns a Future which resolves when expansion completes.
  - Add method expand_rrule_in_worker(event, limits) to offload to worker pool.
  - New return type: partial/streaming expansion results to allow incremental insertion into the event cache (keeps server responsive).
- [`calendarbot_lite/lite_fetcher.py`](calendarbot_lite/lite_fetcher.py:1) and parser remain largely unchanged, but parser should be able to emit "skeleton events" quickly and hand off heavy expansion to worker queue.
- Server-level addition in [`calendarbot_lite/server.py`](calendarbot_lite/server.py:1): a small background task manager (FetchPool + RRuleWorkerQueue). Expose status endpoints or metrics.

4. Integration points with existing server
- Replace existing sequential refresh loop with:
  - FetchPool: bounded semaphore or asyncio.Semaphore to restrict concurrent fetch tasks to FETCH_CONCURRENCY (default 2).
  - For each fetched source: parse (streaming) and produce parsed events.
  - For events with RRULEs: push to RRULE worker queue; server immediately updates cached non-expanded events so API returns stable data.
  - When expansions complete, merge expanded occurrences into cache and optionally emit a lightweight webhook/event for cache update.
- The web API continues to serve from the shared in-memory cache and remains responsive because expansions are asynchronous.

5. Memory and CPU optimization strategies
- Bound the maximum number of concurrent fetch tasks to limit peak memory usage and CPU contention.
- For RRULE expansion:
  - Default expansion limits: max_occurrences_per_rule (e.g., 250), max_days_window (configurable, e.g., now..+365), and per-rule time budget (e.g., 200ms).
  - Implement incremental expansion that yields control back to the event loop after processing each N occurrences (cooperative multitasking).
  - Optionally use ProcessPoolExecutor for heavy expansions if CPU time per expansion is consistently high; fallback to single-worker process recommended for Pi Zero 2W only if necessary.
- Cache results in compact structures; store only required fields (avoid saving large strings like full descriptions if not used by UI).

6. Configuration options for resource tuning
- fetch_concurrency (default 2)
- rrule_worker_concurrency (default 1)
- max_occurrences_per_rule (default 250)
- expansion_days_window (default 365)
- expansion_time_budget_ms_per_rule (default 200)
- expansion_yield_frequency (after N occurrences, yield to event loop, default 50)
- use_process_worker_for_expansion (bool, default False)
- worker_poll_interval_seconds (for background tasks)

7. Implementation complexity assessment
- Medium to High.
  - Implementing bounded fetch concurrency is straightforward (use asyncio.Semaphore).
  - Implementing non-blocking, incremental RRULE expansion and safe merge into cache is medium complexity.
  - If ProcessPoolExecutor is required, complexity increases due to serialization of event data and cross-process communication.

8. Dependencies and potential risks
- Dependencies: Python concurrent.futures (stdlib), asyncio (stdlib). No new external libs required.
- Risks:
  - Incorrect merging of partially-expanded data could create duplicates or missing occurrences — requires careful cache merge logic and tests.
  - Process-based expansion introduces IPC overhead and complexity (serialization, crash handling).
  - Too-strict expansion limits could make the UI show incomplete results; must expose config to tuning.

===============================================================================
COMMONS: Profiling, Measurement, Tests, and Rollout Plan
===============================================================================

1. Profiling and measurement plan
- Add lightweight metrics and logging:
  - Fetch time, bytes transferred, Content-Length header presence.
  - Peak memory during fetch and parse (measure using psutil or the existing scripts in [`calendarbot_lite/scripts/measure_memory_cpu.sh`](calendarbot_lite/scripts/measure_memory_cpu.sh:1)).
  - Expansion time per rule and occurrences produced.
  - Queue lengths and worker utilization.
- Use A/B profiling: run before/after traces on Pi Zero 2W using py-spy or existing measurement tools; capture CPU flamegraphs and memory snapshots.
- Add unit tests for streaming parser using chunked input tests (simulate arbitrary chunk boundaries).

2. Deployment and rollback guidance
- Implement feature flags and config toggles (prefer_stream=auto/never/force, enable_streaming_parser flag, use_rrule_worker flag).
- Deploy behind feature toggle; start with conservative defaults (stream_threshold 256KB, fetch_concurrency 1->2, worker_concurrency 1).
- Monitor memory and CPU; rollback by toggling features off.

3. Logging and observability
- Keep concise debug logging in [`calendarbot_lite/lite_logging.py`](calendarbot_lite/lite_logging.py:1) for streaming decisions and streaming parser progress (byte counts, events parsed).
- Add warnings when content-length mismatches actual bytes or when streaming had to fall back to full buffer.

===============================================================================
IMPLEMENTATION NOTES & TESTS (practical steps)
===============================================================================
- Unit tests for:
  - Smart streaming decision matrix: with/without Content-Length, different sizes, chunked responses.
  - Streaming parser correctness across random chunk boundaries and folded lines.
  - RRULE worker: limits honored (occurrence cap/time budget) and cache merge correctness.
- Integration tests:
  - Simulate multiple sources with large ICS payloads; ensure bounded concurrency and responsiveness of API.
  - End-to-end smoke test using the standard start command `calendarbot --web --port PORT` in a Pi emulated low-RAM environment.

===============================================================================
RISKS & MITIGATION SUMMARY
===============================================================================
- Risk: Parser bugs on chunk boundaries.
  - Mitigation: Comprehensive unit tests that simulate chunk boundaries and varied encodings; incremental rollout.
- Risk: APIs that assume string content break.
  - Mitigation: Keep buffered content path unchanged; add response.stream optional field and helper utilities; defensive checks in parser and server.
- Risk: RRULE expansion still consumes too much CPU.
  - Mitigation: Add strict per-rule limits and process-based worker fallback; expose config; monitor expansion duration and occurrences.

===============================================================================
ESTIMATED EFFORT & PRIORITY
===============================================================================
- Refactor 1 (Smart HTTP Streaming): Medium effort — priority: High (quick wins on memory).
- Refactor 2 (Streaming Pipeline): High effort — priority: High (necessary to realize memory savings).
- Refactor 3 (Bounded Concurrency + RRULE workers): Medium-High effort — priority: Medium-High (improves responsiveness and stability).

===============================================================================
CONFIGURATION DEFAULTS (recommended)
===============================================================================
- stream_threshold_bytes = 262144  # 256KB
- read_chunk_size_bytes = 8192
- fetch_concurrency = 2
- rrule_worker_concurrency = 1
- max_occurrences_per_rule = 250
- expansion_days_window = 365
- expansion_time_budget_ms_per_rule = 200
- enable_tempfile_fallback = False
- prefer_stream = auto

===============================================================================
FILES / ENTRY POINTS AFFECTED (references)
===============================================================================
- [`calendarbot_lite/lite_fetcher.py`](calendarbot_lite/lite_fetcher.py:1) — add streaming decision logic and optional stream_handle in responses.
- [`calendarbot_lite/lite_parser.py`](calendarbot_lite/lite_parser.py:1) — add parse_ics_stream and robust streaming parsing utilities.
- [`calendarbot_lite/lite_models.py`](calendarbot_lite/lite_models.py:1) — small model additions for stream metadata.
- [`calendarbot_lite/lite_rrule_expander.py`](calendarbot_lite/lite_rrule_expander.py:1) — non-blocking expansion API and worker-target functions.
- [`calendarbot_lite/server.py`](calendarbot_lite/server.py:1) — replace sequential refresh loop with bounded fetch pool + worker queue orchestration (no external API changes).

===============================================================================
NEXT STEPS (recommended)
===============================================================================
1. Implement small, isolated unit in fetcher to read Content-Length and return decision flag; add tests.
2. Implement a minimal streaming parser harness that accepts AsyncIterator[bytes] and parse a handful of VEVENTs; add chunk-boundary tests.
3. Add bounded fetch concurrency using asyncio.Semaphore in server refresh code.
4. Implement RRULE expansion queue with simple worker (async) and hard caps; verify responsiveness on Pi Zero 2W.
5. Full integration and profiling on Pi Zero 2W; tune config defaults.

This completes the architectural designs for all three refactorings requested. The designs include diagrams, API changes, integration points, resource strategies, configuration options, complexity assessments, and risks. Implementation-ready details are provided to guide incremental development and safe rollout on the Pi Zero 2W platform.