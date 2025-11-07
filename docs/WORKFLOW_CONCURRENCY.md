# GitHub Actions Workflow Concurrency

## Overview

This document explains the concurrency controls added to prevent duplicate workflow runs in GitHub Actions.

## Problem

When autopilot agents (like GitHub Copilot) create pull requests, the CI/CD workflow could run multiple times for the same commit:

1. **PR opened event**: When the PR is first created
2. **Synchronize event**: When commits are pushed to the PR branch

Without concurrency controls, both events trigger separate workflow runs, causing:
- Duplicate CI checks appearing in the GitHub UI
- Wasted CI resources and runner minutes
- Confusion during PR approval (seeing "two" of the same action)

## Solution

We've added **concurrency groups** to workflows that can be triggered by PR events. A concurrency group ensures that:

1. Only one instance of the workflow runs at a time for a given context (PR number, branch, etc.)
2. In-progress runs are automatically cancelled when a new run is triggered
3. Resources are used efficiently without duplicate work

## Implementation

### CI/CD Pipeline (ci.yml)

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event_name }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

**How it works:**
- **Group**: Combines workflow name + event type + (PR number OR branch ref)
  - For PRs: Groups by PR number (e.g., `CI/CD-pull_request-123`)
  - For pushes to main/develop: Groups by branch (e.g., `CI/CD-push-refs/heads/main`)
  - For manual triggers: Groups by ref
- **Cancel in-progress**: Only for `pull_request` events
  - When a new commit is pushed to a PR, cancels the old run
  - Allows concurrent runs for main/develop branches (for parallel merges)
  - Allows multiple manual workflow_dispatch runs

**Example scenario:**
1. Autopilot creates PR #123 → Workflow starts (group: `CI/CD-pull_request-123`)
2. Autopilot pushes new commit to PR #123 → Old workflow cancelled, new workflow starts (same group)
3. Result: Only one workflow runs at a time for PR #123

### Copilot Setup (copilot-setup-steps.yml)

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

**How it works:**
- **Group**: Combines workflow name + branch ref
- **Cancel in-progress**: Always true
  - This workflow only runs on `workflow_dispatch` and file changes
  - Cancelling old runs is always safe since it's for environment setup

## Workflows Not Modified

### nightly-full-suite.yml
- **Triggers**: `schedule` (cron) and `workflow_dispatch`
- **Why no concurrency control**:
  - Scheduled jobs run once per day (no risk of overlap)
  - Manual triggers are rare and intentional
  - No PR events, so no duplicate run risk

### e2e-kiosk.yml
- **Triggers**: `workflow_dispatch` only
- **Why no concurrency control**:
  - Manual trigger only
  - Intentional test runs should complete independently
  - No PR events

## Benefits

1. **Eliminates duplicate runs**: Only one workflow per PR at a time
2. **Saves CI resources**: Cancelled runs stop immediately, freeing runners
3. **Clearer PR status**: One status check per workflow, not multiple
4. **Faster feedback**: Latest changes tested immediately without waiting for old runs

## Testing

To verify the fix works:

1. Create a test PR
2. Push multiple commits in quick succession
3. Verify in GitHub Actions UI:
   - Only one workflow run is active at a time
   - Previous runs show as "Cancelled" when new commits are pushed
   - Final run completes successfully

## References

- [GitHub Actions: Workflow concurrency](https://docs.github.com/en/actions/using-jobs/using-concurrency)
- [GitHub Actions: Workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#concurrency)
