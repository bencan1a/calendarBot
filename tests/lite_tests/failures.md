# CalendarBot Lite — Test Failures Diagnostic Report

Summary
-------
- Total specs run: 7
- Passed: 0
- Failed: 7
- Primary observed symptom: the test runner expected a top-level "events" array but the actual whats-next response contained a different structure (e.g., "meeting") or otherwise did not include "events". See JSON report at [`tests/lite_tests/report.json`](tests/lite_tests/report.json:1).

Failing tests
-------------
- single_meeting_20251105
- daily_recurring_202511
- recurring_with_exdate_202511
- timezone_event_202511
- all_day_event_202511
- dst_transition_timezone_202511
- dst_transition_overlapping_202511

Top prioritized failure reasons (with likelihood)
------------------------------------------------
1. Implementation bug in calendarbot_lite (high)
   - Reason: Runner logs and the generated report show "actual" responses that do not contain the expected top-level "events" key. Example: for `single_meeting_20251105` the captured actual top-level was `{"meeting": null}` instead of `{"events": [...]}` (see [`tests/lite_tests/report.json`](tests/lite_tests/report.json:1)).
   - Evidence: pytest captured assertion (excerpt) shows comparison diff where expected included 'events' and actual had 'meeting' (detailed under Evidence below).
2. Test-definition issue (low)
   - Reason: Specs appear consistent and generated from fixtures in [`tests/lite_tests/specs.yaml`](tests/lite_tests/specs.yaml:1), so less likely. Kept as a fallback if calendarbot_lite intentionally changed API format.
3. Environment/infra issue (low)
   - Reason: venv activation was required and the test run executed (pytest ran), so environment was not the primary blocker. However, direct runner invocation (`python tests/lite_tests/runner.py`) failed when executed as plain script due to relative imports — recommended to run via pytest or via module execution (`python -m tests.lite_tests.runner`) if needed.
4. Non-deterministic timing (very low)
   - Reason: The runner uses DATETIME_OVERRIDE and waits for whats-next; timeouts/logs show the runner reached the comparison step and produced diffs, so timing is unlikely.

Evidence (selected logs / diffs)
--------------------------------
- Pytest summary (relevant lines):
  - "Running test 1/7: single_meeting_20251105 ... Test single_meeting_20251105 FAILED: Comparison failed: 2 differences"
  - "Test run complete: 0/7 passed, 7 failed"
  (Full pytest stdout captured during the run; head+tail stored in the automation logs.)

- Detailed assertion excerpt (from pytest captured error for `single_meeting_20251105`):
  - Comparison diff included in test diagnostics:
    {
      "expected": {"events": [{"start_datetime": "2025-11-05T16:00:00Z", "end_datetime": "2025-11-05T17:00:00Z", "summary": "Team Standup", "uid": "single-meeting-20251105-001@example.com"}]},
      "actual": {"meeting": null},
      "differences": [
        "Event count mismatch: expected 1, got 0",
        "Missing event at index 0: {...}"
      ],
      "missing_fields": ["events"],
      "extra_fields": ["meeting"]
    }
  - This is recorded in the machine report at [`tests/lite_tests/report.json`](tests/lite_tests/report.json:1) for the single meeting test.

- Direct runner invocation note:
  - Running `python tests/lite_tests/runner.py --specs ...` failed with:
    ImportError: attempted relative import with no known parent package
  - Recommended invocation for direct runs (if not using pytest): `python -m tests.lite_tests.runner ...` or run via pytest as the integration test does.

Classification per failing test
--------------------------------
- single_meeting_20251105
  - Classification: Implementation bug in calendarbot_lite
  - Short reason: Actual response top-level contains `meeting` (or no `events`) instead of `events` array; events missing.
  - Evidence: diff in [`tests/lite_tests/report.json`](tests/lite_tests/report.json:1) and pytest assertion.

- daily_recurring_202511
  - Classification: Implementation bug in calendarbot_lite (likely same root cause)
  - Short reason: Runner logged "Comparison failed: 2 differences" and actual lacked expected events array.
  - Evidence: Runner logs and report JSON.

- recurring_with_exdate_202511
  - Classification: Implementation bug in calendarbot_lite
  - Short reason: 3 differences reported; expected events not matched, consistent with top-level mismatch or rrule expansion problem.
  - Evidence: Runner logs and report JSON.

- timezone_event_202511
  - Classification: Implementation bug in calendarbot_lite (timezone handling is a candidate)
  - Short reason: Expected timezone-normalized UTC event missing; actual did not provide expected events key.
  - Evidence: Runner logs and report JSON.

- all_day_event_202511
  - Classification: Implementation bug in calendarbot_lite or parsing of DATE-valued events
  - Short reason: All-day events use DATE values; if calendarbot_lite changed response schema it would cause missing events in the runner comparison.
  - Evidence: Runner logs and report JSON.

- dst_transition_timezone_202511
  - Classification: Implementation bug in calendarbot_lite (ambiguous-time handling possible)
  - Short reason: Expected ambiguous-time mapping to first occurrence not present; actual response did not include expected event.
  - Evidence: Runner logs and report JSON.

- dst_transition_overlapping_202511
  - Classification: Implementation bug in calendarbot_lite
  - Short reason: Two overlapping expected events missing or mismatched; likely related to event expansion logic or response format.
  - Evidence: Runner logs and report JSON.

Suggested next steps for implementer
-----------------------------------
1. Inspect the whats-next API response produced by calendarbot_lite for one failing test (start with `single_meeting_20251105`) and confirm the top-level JSON schema:
   - Verify whether the server returns `events: [...]` or a different key like `meeting`.
   - Endpoint to curl: `http://127.0.0.1:<lite_port>/api/whats-next` where <lite_port> is shown in the test diagnostics; e.g., see the runner diagnostics for `single_meeting_20251105` in [`tests/lite_tests/report.json`](tests/lite_tests/report.json:1).

2. If the top-level key was intentionally renamed (e.g., `meeting`), update calendarbot_lite to produce `events` for backwards compatibility OR update the test runner to accept the new schema (temporary). Prefer fixing calendarbot_lite if public API change is unintended.

3. For timezone, DST and all-day cases:
   - Once response schema mismatch is resolved, re-run the failing specs. If differences persist, investigate:
     - rrule expansion implementation in [`calendarbot_lite/lite_rrule_expander.py`](calendarbot_lite/lite_rrule_expander.py:1).
     - date vs datetime parsing in [`calendarbot_lite/lite_event_parser.py`](calendarbot_lite/lite_event_parser.py:1) and timezone normalization in [`calendarbot_lite/lite_datetime_utils.py`](calendarbot_lite/lite_datetime_utils.py:1).

4. Reproduce locally with a single failing spec using the runner:
   - Preferred: `pytest tests/test_lite_runner.py::test_lite_runner_full_integration_when_all_specs_then_all_pass -q -rA`
   - Or run a single spec by temporarily instrumenting the runner to run only one test or using the convenience function in [`tests/lite_tests/runner.py`](tests/lite_tests/runner.py:1).

5. If direct invocation is required (not via pytest), run module-style to avoid relative import failure:
   - `python -m tests.lite_tests.runner --specs tests/lite_tests/specs.yaml --fixtures tests/fixtures/ics --output-json tests/lite_tests/report.json`

Notes about environment and execution
-------------------------------------
- venv activation: tests were run with `. venv/bin/activate` as required by project docs. Pytest executed successfully (6 tests passed, 1 failed overall run exit code was 1). See captured pytest output for details.
- Direct runner invocation (`python tests/lite_tests/runner.py ...`) fails because the file uses relative imports; run it via pytest or as module if direct invocation is necessary.
- Timeout handling: Runner timeouts did not trigger — runner reached comparison step and emitted diffs, so hanging/timeouts were not the cause.

Files to inspect first
----------------------
- Test runner and utils:
  - [`tests/lite_tests/runner.py`](tests/lite_tests/runner.py:1)
  - [`tests/lite_tests/utils.py`](tests/lite_tests/utils.py:1)
- Specification fixtures:
  - [`tests/lite_tests/specs.yaml`](tests/lite_tests/specs.yaml:1)
  - ICS fixtures directory: [`tests/fixtures/ics/`](tests/fixtures/ics/:1)
- CalendarBot Lite implementation points to check:
  - [`calendarbot_lite/server.py`](calendarbot_lite/server.py:1)
  - [`calendarbot_lite/lite_event_parser.py`](calendarbot_lite/lite_event_parser.py:1)
  - [`calendarbot_lite/lite_rrule_expander.py`](calendarbot_lite/lite_rrule_expander.py:1)
  - [`calendarbot_lite/lite_datetime_utils.py`](calendarbot_lite/lite_datetime_utils.py:1)

Appendix — quick reproduction commands
-------------------------------------
- Run full pytest integration:
  - `. venv/bin/activate && pytest tests/test_lite_runner.py -q -rA`
- Run runner directly via module form:
  - `. venv/bin/activate && python -m tests.lite_tests.runner --specs tests/lite_tests/specs.yaml --fixtures tests/fixtures/ics --output-json tests/lite_tests/report.json`
