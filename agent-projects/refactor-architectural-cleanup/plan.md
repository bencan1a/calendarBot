# CalendarBot Architectural Cleanup Project

```yaml
status: active
owner: claude-opus-4-5
created: 2026-02-01
summary:
  - Comprehensive architectural cleanup of calendarbot_lite and framebuffer_ui
  - Remove ~2,800 lines of dead/unused code
  - Consolidate ~1,200 lines of duplicated code
  - Expected 25-30% codebase reduction
```

---

## Executive Summary

The CalendarBot codebase exhibits significant **agent-written over-engineering** that conflicts with the project's stated goal of being a simple personal project. Analysis identified:

- **~2,800 lines of dead or unused code** (deletable with no functional impact)
- **~1,200 lines of duplicated code** across modules
- **Enterprise patterns** inappropriate for 1-5 users
- **Architectural violations** (domain layer importing from API layer)

---

## Implementation Phases

| Phase | Description | Effort | Risk |
|-------|-------------|--------|------|
| 1 | Safe Deletions | 2-3 hrs | None |
| 2 | Alexa Layer Simplification | 3-4 hrs | Low |
| 3 | Core Infrastructure Cleanup | 3-4 hrs | Low |
| 4 | Calendar Processing Consolidation | 4-6 hrs | Medium |
| 5 | API/Server Simplification | 4-6 hrs | Medium |
| 6 | Domain Logic Cleanup | 2-3 hrs | Low |

---

## Files to DELETE (Phase 1)

| File | Lines | Reason |
|------|-------|--------|
| `core/dependencies.py` | 155 | Zero production usage |
| `alexa/alexa_protocols.py` | 182 | Protocols for single implementations |
| `alexa/alexa_registry.py` | 201 | Registry not used dynamically |
| `alexa/alexa_response_cache.py` | 198 | No benefit for 1-5 users |
| `alexa/alexa_precompute_stages.py` | 519 | Duplicates handlers |
| **Total** | **1,255** | |

---

## Reference: Full Plan

See [/Users/bencan/.claude/plans/snappy-giggling-honey.md](/Users/bencan/.claude/plans/snappy-giggling-honey.md) for the complete detailed plan with all phases, tasks, and verification steps.
