# Agent Projects

This directory contains active project documentation and planning materials for ongoing work.

## Purpose

- **Ephemeral Plans**: Short-lived planning documents for specific refactors, experiments, or migrations
- **Work-in-Progress**: Active development documentation
- **Project Tracking**: Status and progress tracking for agent-driven tasks

## Structure

Each project should have its own subdirectory:

```
agent-projects/
├── feature-name/
│   ├── plan.md          # Required: Project plan with metadata
│   ├── progress.md      # Optional: Detailed progress tracking
│   └── findings.md      # Optional: Research findings
└── investigation-xyz/
    └── plan.md
```

## Plan Metadata Format

Each `plan.md` should include metadata at the top:

```yaml
status: active|paused|done
owner: <agent-name or developer-name>
created: YYYY-MM-DD
summary:
  - Short description of the project
  - Key objectives or outcomes
  - Expected completion timeline
```

## Lifecycle

- **Active**: Currently being worked on (status=active, <21 days old)
- **Paused**: Temporarily on hold
- **Done**: Completed, kept for reference
- **Archived**: Old projects remain in git history but are ignored by automation

## Documentation Self-Healing

The `tools/build_context.py` script (when implemented) will:
- Scan this directory for active plans
- Summarize plans with status=active and created within 21 days
- Include summaries in generated `docs/CONTEXT.md`
- Provide context to AI agents about ongoing work

## Best Practices

1. **Create a folder per project** with descriptive name
2. **Use prefixes**: `feature-`, `refactor-`, `investigation-`, `fix-`
3. **Include plan.md** with required metadata
4. **Update status** as work progresses
5. **Mark as done** when complete (don't delete - it's part of history)
6. **Clean descriptions** - assume others will read this

## Examples

### Feature Development
```
agent-projects/feature-calendar-caching/
├── plan.md
├── architecture.md
└── implementation-notes.md
```

### Investigation
```
agent-projects/investigation-memory-leak/
├── plan.md
├── profiling-results.md
└── findings.md
```

### Refactoring
```
agent-projects/refactor-alexa-handlers/
├── plan.md
└── migration-checklist.md
```

## See Also

- [../../AGENTS.md](../../AGENTS.md) - Agent guidance and workflow
- [../../project-plans/python-template-migration/IMPLEMENTATION_ROADMAP.md](../../project-plans/python-template-migration/IMPLEMENTATION_ROADMAP.md) - Migration roadmap
- [../../project-plans/python-template-migration/AGENT_PROMPTS.md](../../project-plans/python-template-migration/AGENT_PROMPTS.md) - Ready-to-use agent prompts
- `../docs/` - Permanent documentation
- `../agent-tmp/` - Temporary files (gitignored)
