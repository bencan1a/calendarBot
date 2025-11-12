#!/usr/bin/env python3
"""Documentation self-healing system for CalendarBot.

This script generates comprehensive documentation by:
1. Extracting API docs from Python docstrings in calendarbot_lite/
2. Scanning agent-projects/ for active plans (status=active, <21 days old)
3. Merging with stable facts from docs/facts.json
4. Creating docs/CONTEXT.md (capped at 150KB)
5. Updating docs/SUMMARY.md with component index
6. Appending to docs/CHANGELOG.md with timestamp
7. Pruning agent-tmp/ files older than 7 days
"""

import argparse
import ast
import json
import os
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

MAX_CONTEXT_SIZE = 150 * 1024  # 150KB limit


def parse_docstrings(source_dir: Path) -> dict[str, Any]:
    """Extract docstrings from Python files.

    Args:
        source_dir: Path to source directory to scan

    Returns:
        Dictionary mapping module paths to their documentation
    """
    docs = {}

    for py_file in source_dir.rglob("*.py"):
        if "__pycache__" in str(py_file) or "test" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            module_doc = ast.get_docstring(tree)

            # Get relative path from source_dir
            rel_path = py_file.relative_to(source_dir)

            if module_doc:
                docs[str(rel_path)] = {
                    "module": str(rel_path),
                    "docstring": module_doc.strip(),
                    "functions": [],
                    "classes": [],
                }

                # Extract function and class docstrings
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_doc = ast.get_docstring(node)
                        if func_doc and not node.name.startswith("_"):
                            docs[str(rel_path)]["functions"].append(
                                {"name": node.name, "doc": func_doc.strip()}
                            )
                    elif isinstance(node, ast.ClassDef):
                        class_doc = ast.get_docstring(node)
                        if class_doc:
                            docs[str(rel_path)]["classes"].append(
                                {"name": node.name, "doc": class_doc.strip()}
                            )

        except (SyntaxError, UnicodeDecodeError):
            # Skip files that can't be parsed
            continue

    return docs


def scan_agent_projects(projects_dir: Path) -> list[dict[str, Any]]:
    """Scan agent-projects/ for active plans.

    Args:
        projects_dir: Path to agent-projects directory

    Returns:
        List of active project summaries
    """
    active_plans = []
    cutoff_date = datetime.now() - timedelta(days=21)

    if not projects_dir.exists():
        return []

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir() or project_dir.name.startswith("."):
            continue

        plan_file = project_dir / "plan.md"
        if not plan_file.exists():
            continue

        try:
            with open(plan_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract metadata from YAML frontmatter or markdown
            status_match = re.search(r"^status:\s*(\w+)", content, re.MULTILINE)
            created_match = re.search(r"^created:\s*(\d{4}-\d{2}-\d{2})", content, re.MULTILINE)

            if not status_match or not created_match:
                continue

            status = status_match.group(1).strip()
            created_str = created_match.group(1).strip()
            created_date = datetime.strptime(created_str, "%Y-%m-%d")

            # Only include active plans less than 21 days old
            if status.lower() == "active" and created_date >= cutoff_date:
                # Extract summary
                summary_match = re.search(
                    r"^summary:\s*\n((?:^  - .*\n?)+)", content, re.MULTILINE
                )
                summary = []
                if summary_match:
                    summary_text = summary_match.group(1)
                    summary = [
                        line.strip("- ").strip()
                        for line in summary_text.split("\n")
                        if line.strip().startswith("-")
                    ]

                active_plans.append(
                    {
                        "project": project_dir.name,
                        "status": status,
                        "created": created_str,
                        "summary": summary,
                        "path": str(project_dir.relative_to(projects_dir.parent)),
                    }
                )

        except (ValueError, UnicodeDecodeError):
            # Skip invalid files
            continue

    return active_plans


def load_facts(facts_file: Path) -> dict[str, Any]:
    """Load stable project facts from JSON file.

    Args:
        facts_file: Path to facts.json

    Returns:
        Dictionary of project facts
    """
    if not facts_file.exists():
        return {}

    try:
        with open(facts_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def generate_context(
    api_docs: dict[str, Any], active_plans: list[dict[str, Any]], facts: dict[str, Any]
) -> str:
    """Generate comprehensive context document.

    Args:
        api_docs: API documentation from docstrings
        active_plans: List of active project plans
        facts: Stable project facts

    Returns:
        Generated context as markdown string
    """
    sections = []

    # Header
    sections.append("# CalendarBot Context\n")
    sections.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*\n")
    sections.append("\n---\n")

    # Project Facts
    if facts:
        sections.append("\n## Project Overview\n")
        if "name" in facts:
            sections.append(f"**Project**: {facts['name']}\n")
        if "description" in facts:
            sections.append(f"**Description**: {facts['description']}\n")
        if "purpose" in facts:
            sections.append(f"\n**Purpose**: {facts['purpose']}\n")

        if "primary_use_case" in facts:
            sections.append("\n### Primary Use Case\n")
            sections.append(f"{facts['primary_use_case']}\n")

        if "scale" in facts:
            sections.append("\n### Project Scale\n")
            for key, value in facts["scale"].items():
                sections.append(f"- **{key.replace('_', ' ').title()}**: {value}\n")

        if "resource_constraints" in facts:
            sections.append("\n### Resource Constraints\n")
            for key, value in facts["resource_constraints"].items():
                sections.append(f"- **{key.replace('_', ' ').title()}**: {value}\n")

        if "codebase" in facts:
            sections.append("\n### Codebase Structure\n")
            codebase = facts["codebase"]
            if "active" in codebase:
                sections.append(f"- **Active Development**: `{codebase['active']}/`\n")
            if "archived" in codebase:
                sections.append(f"- **Archived (DO NOT MODIFY)**: `{codebase['archived']}/`\n")

        sections.append("\n---\n")

    # Active Plans
    if active_plans:
        sections.append("\n## Active Projects\n")
        sections.append(
            "\n*Recent projects (status=active, created within 21 days)*\n"
        )

        for plan in active_plans:
            sections.append(f"\n### {plan['project']}\n")
            sections.append(f"**Status**: {plan['status']}  \n")
            sections.append(f"**Created**: {plan['created']}  \n")
            sections.append(f"**Path**: `{plan['path']}`\n")

            if plan["summary"]:
                sections.append("\n**Summary**:\n")
                for item in plan["summary"]:
                    sections.append(f"- {item}\n")

        sections.append("\n---\n")

    # API Documentation
    if api_docs:
        sections.append("\n## API Documentation\n")
        sections.append("\n*Extracted from Python docstrings in calendarbot_lite/*\n")

        # Group by directory
        by_package = {}
        for module_path, doc_info in sorted(api_docs.items()):
            package = str(Path(module_path).parts[0]) if "/" in module_path else "root"
            if package not in by_package:
                by_package[package] = []
            by_package[package].append((module_path, doc_info))

        for package, modules in sorted(by_package.items()):
            sections.append(f"\n### Package: `{package}`\n")

            for module_path, doc_info in modules:
                sections.append(f"\n#### `{module_path}`\n")
                sections.append(f"\n{doc_info['docstring']}\n")

                if doc_info["classes"]:
                    sections.append("\n**Classes**:\n")
                    for cls in doc_info["classes"]:
                        sections.append(f"\n- **{cls['name']}**\n")
                        # Truncate long class docs
                        cls_doc = cls["doc"]
                        if len(cls_doc) > 200:
                            cls_doc = cls_doc[:200] + "..."
                        sections.append(f"  {cls_doc}\n")

                if doc_info["functions"]:
                    sections.append("\n**Functions**:\n")
                    for func in doc_info["functions"][:10]:  # Limit to 10 functions
                        sections.append(f"\n- **{func['name']}()**\n")
                        # Truncate long function docs
                        func_doc = func["doc"]
                        if len(func_doc) > 150:
                            func_doc = func_doc[:150] + "..."
                        sections.append(f"  {func_doc}\n")

    # Join all sections and check size
    context = "".join(sections)

    # Truncate if needed
    if len(context.encode("utf-8")) > MAX_CONTEXT_SIZE:
        # Remove API docs section to fit within limit
        truncated_sections = [s for s in sections if "## API Documentation" not in s]
        context = "".join(truncated_sections)

        # Add note about truncation
        if len(context.encode("utf-8")) > MAX_CONTEXT_SIZE:
            context = context[: MAX_CONTEXT_SIZE - 200]
            context += "\n\n*[Document truncated to fit 150KB limit]*\n"

    return context


def generate_summary(api_docs: dict[str, Any]) -> str:
    """Generate component index summary.

    Args:
        api_docs: API documentation from docstrings

    Returns:
        Generated summary as markdown string
    """
    sections = []

    sections.append("# CalendarBot Component Summary\n")
    sections.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*\n")
    sections.append("\n## Component Index\n")

    # Group by package
    by_package = {}
    for module_path in sorted(api_docs.keys()):
        package = str(Path(module_path).parts[0]) if "/" in module_path else "root"
        if package not in by_package:
            by_package[package] = []
        by_package[package].append(module_path)

    for package, modules in sorted(by_package.items()):
        sections.append(f"\n### `{package}/`\n")
        for module in sorted(modules):
            sections.append(f"- `{module}`\n")

    sections.append("\n## Quick Links\n")
    sections.append("- [Full Context](CONTEXT.md)\n")
    sections.append("- [Changelog](CHANGELOG.md)\n")
    sections.append("- [Project Facts](facts.json)\n")

    return "".join(sections)


def append_changelog(changelog_file: Path) -> None:
    """Append entry to changelog.

    Args:
        changelog_file: Path to CHANGELOG.md
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = f"\n## {timestamp}\n\n- Documentation regenerated by build_context.py\n"

    if changelog_file.exists():
        with open(changelog_file, "a", encoding="utf-8") as f:
            f.write(entry)
    else:
        with open(changelog_file, "w", encoding="utf-8") as f:
            f.write("# Documentation Changelog\n")
            f.write(entry)


def prune_old_files(tmp_dir: Path, days: int = 7) -> int:
    """Prune files older than specified days from agent-tmp/.

    Args:
        tmp_dir: Path to agent-tmp directory
        days: Age threshold in days (default: 7)

    Returns:
        Number of files removed
    """
    if not tmp_dir.exists():
        return 0

    cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
    removed_count = 0

    for item in tmp_dir.rglob("*"):
        if item.is_file():
            try:
                if item.stat().st_mtime < cutoff_time:
                    item.unlink()
                    removed_count += 1
            except (OSError, PermissionError):
                # Skip files that can't be removed
                continue

    # Remove empty directories
    for item in sorted(tmp_dir.rglob("*"), reverse=True):
        if item.is_dir() and not any(item.iterdir()):
            try:
                item.rmdir()
            except OSError:
                continue

    return removed_count


def main() -> None:
    """Main entry point for documentation builder."""
    parser = argparse.ArgumentParser(description="Build CalendarBot documentation context")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root directory (default: current directory)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild even if source files haven't changed",
    )
    args = parser.parse_args()

    root_dir = args.root.resolve()
    source_dir = root_dir / "calendarbot_lite"
    projects_dir = root_dir / "agent-projects"
    docs_dir = root_dir / "docs"
    tmp_dir = root_dir / "agent-tmp"

    # Ensure directories exist
    docs_dir.mkdir(exist_ok=True)

    print("CalendarBot Documentation Builder")
    print("=" * 50)

    # Step 1: Extract API documentation
    print("\n1. Extracting API documentation from calendarbot_lite/...")
    api_docs = parse_docstrings(source_dir) if source_dir.exists() else {}
    print(f"   Found {len(api_docs)} documented modules")

    # Step 2: Scan active projects
    print("\n2. Scanning agent-projects/ for active plans...")
    active_plans = scan_agent_projects(projects_dir)
    print(f"   Found {len(active_plans)} active plans")

    # Step 3: Load stable facts
    print("\n3. Loading stable facts from docs/facts.json...")
    facts_file = docs_dir / "facts.json"
    facts = load_facts(facts_file)
    print(f"   Loaded {'facts' if facts else 'no facts (file missing)'}")

    # Step 4: Generate CONTEXT.md
    print("\n4. Generating docs/CONTEXT.md...")
    context = generate_context(api_docs, active_plans, facts)
    context_file = docs_dir / "CONTEXT.md"
    with open(context_file, "w", encoding="utf-8") as f:
        f.write(context)
    size_kb = len(context.encode("utf-8")) / 1024
    print(f"   Written {size_kb:.1f}KB (limit: 150KB)")

    # Step 5: Generate SUMMARY.md
    print("\n5. Generating docs/SUMMARY.md...")
    summary = generate_summary(api_docs)
    summary_file = docs_dir / "SUMMARY.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"   Written summary with {len(api_docs)} components")

    # Step 6: Append to CHANGELOG.md
    print("\n6. Updating docs/CHANGELOG.md...")
    changelog_file = docs_dir / "CHANGELOG.md"
    append_changelog(changelog_file)
    print("   Changelog updated")

    # Step 7: Prune old agent-tmp files
    print("\n7. Pruning old files from agent-tmp/...")
    removed = prune_old_files(tmp_dir, days=7)
    print(f"   Removed {removed} files older than 7 days")

    print("\n" + "=" * 50)
    print("Documentation build complete!")


if __name__ == "__main__":
    main()
