# calendarbot_lite — Performance Validation Report (Pi Zero 2W target)

This report documents the performance benchmark harness I added for the CalendarBot Lite fork, how to run it, what it measures, expected outcomes for Pi Zero 2W-like constraints, and recommended deployment tuning.

Files added / relevant
- Benchmark harness (self-contained): [`calendarbot_lite/scripts/performance_benchmark_lite.py:1`](calendarbot_lite/scripts/performance_benchmark_lite.py:1)
- Existing smoke sampler: [`calendarbot_lite/scripts/measure_memory_cpu.sh:1`](calendarbot_lite/scripts/measure_memory_cpu.sh:1)
- Unit tests to validate concurrency/worker behavior: [`tests/unit/test_concurrency_system.py:1`](tests/unit/test_concurrency_system.py:1)
- Streaming fetcher & parser implementations: [`calendarbot_lite/lite_fetcher.py:1`](calendarbot_lite/lite_fetcher.py:1), [`calendarbot_lite/lite_parser.py:1`](calendarbot_lite/lite_parser.py:1)
- RRULE worker implementation: [`calendarbot_lite/lite_rrule_expander.py:1`](calendarbot_lite/lite_rrule_expander.py:1)

Summary of what's implemented
- A repeatable, local benchmark harness that spins up an aiohttp test server serving generated ICS payloads (small/medium/large and multi-source).
  - Script: [`calendarbot_lite/scripts/performance_benchmark_lite.py:1`](calendarbot_lite/scripts/performance_benchmark_lite.py:1)
- Measurements recorded:
  - Peak RSS (best-effort via psutil or resource)
  - Wall-clock elapsed times for fetch / parse / expand phases
  - Heuristic network bytes (content-length or measured buffer)
  - Simple HTTP-root probing to measure responsiveness while background jobs run
- Scenarios:
  - small: ~50KB (buffered path expected)
  - medium: ~500KB (streaming path expected)
  - large: ~5MB+ (streaming path shows memory savings)
  - concurrent: 3 sources concurrently (mixed sizes + RRULEs)
- Output: JSON file (default `calendarbot_lite_perf_results.json`) with per-scenario measurements.

How to run (recommended)
1. Activate project venv (IMPORTANT per repo rules)
   - Example (bash):
     - source .venv/bin/activate  # or however your venv is named
2. Install optional profiling dependencies if not present:
   - pip install psutil py-spy
3. Run the harness locally:
   - python3 calendarbot_lite/scripts/performance_benchmark_lite.py --run all
   - Or run a specific scenario:
     - python3 calendarbot_lite/scripts/performance_benchmark_lite.py --run medium
4. Output:
   - Results are written to `calendarbot_lite_perf_results.json` (path printed by script).
   - Use `calendarbot_lite/scripts/measure_memory_cpu.sh:1` to do a quick smoke sampling of server process RSS/CPU.

Commands for deeper profiling (recommend to run on a development machine first; on Pi Zero use sampling tools like py-spy)
- Sample (low overhead) flamegraph with py-spy (sampling):
  - py-spy record -o profile.svg -- python3 calendarbot_lite/scripts/performance_benchmark_lite.py --run large
  - py-spy record -o profile.speedscope.json --format speedscope -- python3 calendarbot_lite/scripts/performance_benchmark_lite.py --run large
- Deterministic CPU profiling for focused test (use with caution — high overhead):
  - python -m cProfile -o out.prof calendarbot_lite/scripts/performance_benchmark_lite.py --run medium
  - python - <<'PY'
    import pstats
    p = pstats.Stats('out.prof')
    p.sort_stats('cumtime').print_stats(50)
    PY
- Memory allocation snapshots (tracemalloc)
  - Add tracemalloc.start() to a small test harness or use an instrumented script to take snapshots before/after parse.

Reproducible baseline vs optimized comparison
- To measure "before" (unoptimized baseline) you need to run the same scenario but force the unoptimized behaviors:
  - Force buffered path:
    - set `CALENDARBOT_DEBUG=true` and/or set `prefer_stream` = "never" on the settings object used by the fetcher (or temporarily modify `calendarbot_lite/lite_fetcher.py:1` in a branch to prefer buffering).
  - Enable verbose debug logging (to measure logging CPU/I/O costs):
    - configure with [`calendarbot_lite/lite_logging.py:1`](calendarbot_lite/lite_logging.py:1) by passing debug_mode=True or set env CALENDARBOT_DEBUG=1.
- Run the harness for both configurations (optimized vs baseline) and compare:
  - RSS peak (KB)
  - Phase elapsed times (fetch, parse, expand)
  - Wall-clock overall scenario time
  - HTTP responsiveness samples during background work

What the harness measures (mapping to your requested metrics)
- Memory usage: RSS before/after phases via psutil/resource in the harness. See `get_rss_kb()` in [`calendarbot_lite/scripts/performance_benchmark_lite.py:1`](calendarbot_lite/scripts/performance_benchmark_lite.py:1).
- CPU utilization: the harness measures elapsed time per phase. For CPU hotspots use py-spy / cProfile to collect stack-level CPU time breakdowns.
- I/O efficiency:
  - Network bytes: estimated from response content-length or content size measured by the harness.
  - Disk I/O for logging: measure separately by enabling production logging (INFO) vs debug and using system-level tools (iotop) or by measuring log file sizes after runs (not automated in this harness).
- Responsiveness: the harness includes a simple HTTP probe hitting server root periodically while background work runs; this demonstrates latency impact under background work.

Resource constraint simulation (Pi Zero 2W)
- The harness supports simulated memory pressure via `--simulate-memory-pressure-mb N`.
  - Example: `python3 calendarbot_lite/scripts/performance_benchmark_lite.py --run large --simulate-memory-pressure-mb 100`
  - This allocates N MB (best-effort) to reduce available memory and observe behavior/fallbacks.
- To simulate single-core CPU, run on actual Pi Zero 2W or use a CPU-limited VM; synthetic CPU throttling is not as accurate as running on the target device.

Key validation checks and expected outcomes (guidance)
- Streaming vs Buffering decision:
  - For payloads < STREAM_THRESHOLD (default 256KB), fetcher should choose buffered GET path and parser should use the traditional path. Test: small scenario.
  - For payloads >= STREAM_THRESHOLD, fetcher should return a StreamHandle and parser should use streaming parser path. Test: medium and large scenarios.
  - Validation: harness records whether response used `stream_handle` (see parse_phase logic).
- Memory optimization effectiveness:
  - Expectation: streaming parse should keep RSS lower than full-buffer parse for large ICS payloads (5MB+). On Pi Zero 2W you should see meaningful reductions in peak RSS (tens of MB saved).
  - Recommendation: streaming avoids storing full `content` in memory; ensure `raw_content` remains None for streaming path.
- Bounded concurrency behavior:
  - With `fetch_concurrency` set to 2 (default in server design) the harness's concurrent scenario should show limited parallelism (Semaphore usage).
  - For Pi Zero single-core, recommended fetch_concurrency is 1–2 (2 often optimal if network-bound but keep at 1 for very CPU-heavy parsing).
- RRULE worker behavior:
  - RRULE expansion must yield back to event loop and honor time/occurrence budgets.
  - Recommended defaults in code: worker concurrency=1, time_budget_ms_per_rule ~200ms, yield_frequency=50. These should preserve API responsiveness.
  - The harness measures expansion elapsed time; use py-spy to find hotspots in expansion code.

Quick expected thresholds (target Pi Zero 2W)
- Small ICS (~50KB):
  - RSS: under 50–80 MB (process), fetch+parse elapsed < 1s (network & CPU dependent)
- Medium ICS (~500KB) — streaming path:
  - RSS: under 80–150 MB
  - fetch+parse elapsed: 1–3s
- Large ICS (~5MB+) — streaming path:
  - RSS: significantly lower than buffered baseline; expect savings of at least the size of the file (i.e. ~5MB) plus parser working memory. On Pi Zero, aim for process peak <200–250MB.
  - fetch+parse elapsed: streaming may be similar or slightly slower than buffered (I/O-bound), but memory constrained systems benefit.
- Concurrent fetch of 3 mixed sources (fetch_concurrency=2):
  - Total elapsed should be less than serial by roughly (#sources / concurrency) factor, but watch CPU contention on single-core devices. If parse is CPU heavy, concurrency=1 may perform better overall.

Integration test to validate all optimizations together
- The harness (`calendarbot_lite/scripts/performance_benchmark_lite.py:1`) runs a concurrent scenario that exercises:
  - Smart HTTP streaming decision in `calendarbot_lite/lite_fetcher.py:1`
  - Streaming pipeline `calendarbot_lite/lite_parser.py:1` (parse_ics_stream)
  - Bounded concurrency logic (via Semaphore usage in server refresh logic tested in `tests/unit/test_concurrency_system.py:1`)
  - RRULE worker code in `calendarbot_lite/lite_rrule_expander.py:1` (expansion tradeoffs)
- Recommended test run:
  - On development machine:
    - python3 calendarbot_lite/scripts/performance_benchmark_lite.py --run concurrent --concurrency 2
  - On Pi Zero 2W:
    - Run same command and compare results.

How to produce "before vs after" numeric comparison
1. Baseline (unoptimized-ish)
   - Force buffered fetch and verbose logging:
     - Ensure configuration that sets `prefer_stream="never"` or temporarily edit settings to disable streaming decisions.
     - Set CALENDARBOT_DEBUG=true if you want to include logging CPU/I/O overhead in baseline.
   - Run:
     - python3 calendarbot_lite/scripts/performance_benchmark_lite.py --run large --output baseline.json
2. Optimized
   - Restore optimized settings (prefer_stream default "auto", logging production config).
   - Run:
     - python3 calendarbot_lite/scripts/performance_benchmark_lite.py --run large --output optimized.json
3. Compare the JSON outputs:
   - RSS deltas, phase elapsed deltas, events parsed, recurring instances.
   - For example, streaming should show lower RSS_kb_after in parse phases and lower raw_content storage.

Recommendations for Pi Zero 2W deployment (practical)
- Keep fetch_concurrency = 1–2 (start at 1, increase to 2 if network bound)
- rrule_worker_concurrency = 1 (single worker; avoid CPU oversubscription)
- expansion_time_budget_ms_per_rule = ~100–300 ms (short budgets prevent long-running expansions blocking responsiveness)
- stream_threshold_bytes = 256KB (current code default) — good tradeoff between overhead and streaming benefit
- Logging config: use `configure_lite_logging(debug_mode=False)` (production mode) — suppress noisy debug logs to reduce CPU and disk I/O
- Monitor regularly with the lightweight smoke script: [`calendarbot_lite/scripts/measure_memory_cpu.sh:1`](calendarbot_lite/scripts/measure_memory_cpu.sh:1)

Limitations and notes
- This harness is deterministic and self-contained but does not emulate full OS memory usage — best validation is running on actual Pi Zero 2W.
- For authoritative CPU flamegraphs / hotspot analysis, use py-spy on the target device if possible (py-spy supports Linux/ARM).
- Tracemalloc snapshots are useful for allocation site analysis but are not included by default due to overhead; add targeted scripts for that when necessary.

Next steps I can do for you (pick one)
- Run the harness locally (I can run commands here if you want me to execute them).
- Add a pytest integration test that runs one scenario and asserts basic resource bounds (example: parse completes and RSS < X MB).
- Add helper scripts that automatically run py-spy for a scenario and attach results to the JSON output.

End of report.