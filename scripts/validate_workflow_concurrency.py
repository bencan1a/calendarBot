#!/usr/bin/env python3
"""
Validate GitHub Actions workflow configurations for concurrency controls.

This script checks that workflows that can be triggered by PR events have
appropriate concurrency groups to prevent duplicate runs.
"""

import sys
from pathlib import Path
import yaml


def check_workflow_concurrency(workflow_path: Path) -> tuple[bool, list[str]]:
    """
    Check if a workflow has appropriate concurrency controls.
    
    Returns:
        (is_valid, messages) - bool indicating if valid, list of messages
    """
    messages = []
    
    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)
    
    workflow_name = workflow.get('name', workflow_path.name)
    messages.append(f"\n=== Checking: {workflow_name} ===")
    
    # Check if workflow has PR triggers
    # Note: 'on' is a reserved word in YAML and gets parsed as boolean True
    triggers = workflow.get('on', workflow.get(True, {}))
    
    # Handle different trigger formats
    if isinstance(triggers, str):
        triggers = {triggers: True}
    elif isinstance(triggers, list):
        triggers = {t: True for t in triggers}
    elif not isinstance(triggers, dict):
        triggers = {}
    
    has_pr_trigger = 'pull_request' in triggers or 'pull_request_target' in triggers
    has_push_trigger = 'push' in triggers
    
    trigger_names = list(triggers.keys()) if isinstance(triggers, dict) else []
    messages.append(f"  Triggers: {', '.join(trigger_names) if trigger_names else 'None detected'}")
    
    # Check for concurrency group
    has_concurrency = 'concurrency' in workflow
    messages.append(f"  Has concurrency: {has_concurrency}")
    
    if has_concurrency:
        concurrency = workflow['concurrency']
        messages.append(f"  Concurrency group: {concurrency.get('group', 'N/A')}")
        messages.append(f"  Cancel in-progress: {concurrency.get('cancel-in-progress', False)}")
    
    # Validate
    is_valid = True
    
    if has_pr_trigger:
        if not has_concurrency:
            messages.append("  ⚠️  WARNING: Workflow has pull_request trigger but no concurrency group")
            messages.append("     This may cause duplicate runs when PRs receive multiple commits")
            is_valid = False
        else:
            # Check that concurrency group includes PR number
            group = concurrency.get('group', '')
            if 'pull_request.number' not in group and has_pr_trigger:
                messages.append("  ⚠️  WARNING: Concurrency group doesn't include PR number")
                messages.append("     Consider: github.event.pull_request.number || github.ref")
                is_valid = False
            else:
                messages.append("  ✓ Concurrency group properly configured for PRs")
    else:
        messages.append("  ℹ️  No PR trigger - concurrency not critical")
        # Concurrency is still nice to have for other triggers, but not required
    
    return is_valid, messages


def main():
    """Check all workflows in .github/workflows/"""
    workflows_dir = Path(__file__).parent.parent / '.github' / 'workflows'
    
    if not workflows_dir.exists():
        print(f"ERROR: Workflows directory not found: {workflows_dir}")
        return 1
    
    print("GitHub Actions Workflow Concurrency Validation")
    print("=" * 60)
    
    all_valid = True
    all_messages = []
    
    for workflow_file in sorted(workflows_dir.glob('*.yml')):
        try:
            is_valid, messages = check_workflow_concurrency(workflow_file)
            all_valid = all_valid and is_valid
            all_messages.extend(messages)
        except Exception as e:
            all_messages.append(f"\n=== Error checking {workflow_file.name} ===")
            all_messages.append(f"  ❌ {e}")
            all_valid = False
    
    # Print all messages
    for msg in all_messages:
        print(msg)
    
    print("\n" + "=" * 60)
    if all_valid:
        print("✓ All workflows with PR triggers have concurrency controls")
        return 0
    else:
        print("⚠️  Some workflows may have concurrency issues")
        print("   Review warnings above and consider adding concurrency groups")
        return 0  # Return 0 since warnings are informational, not errors


if __name__ == '__main__':
    sys.exit(main())
