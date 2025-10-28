#!/usr/bin/env bash
set -euo pipefail

# Creates .github/workflows/perf_smoke.yml from the repository root.
# Run locally (from repository root) to write the workflow file:
#   bash scripts/create_perf_smoke_workflow.sh

mkdir -p .github/workflows
cat > .github/workflows/perf_smoke.yml <<'YML'
name: "Perf Smoke - Morning Summary"
on:
  workflow_dispatch:
  schedule:
    - cron: '0 3 * * 0' # weekly UTC

jobs:
  perf_smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install deps
        run: |
          python -m venv .venv
          . .venv/bin/activate
          pip install -r requirements.txt
      - name: Run perf harness (50 events)
        run: |
          . .venv/bin/activate
          python3 scripts/performance_benchmark_rewrite.py --run fifty --output calendarbot_lite_perf_results.json
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: perf-results
          path: calendarbot_lite_perf_results.json
YML

echo "Wrote .github/workflows/perf_smoke.yml (run this script locally to create the workflow file)."