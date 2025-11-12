# Implementation Roadmap: Python-Template Best Practices Migration

## Executive Summary

This document provides a phased implementation roadmap for adopting best practices from the python-template repository into CalendarBot. The migration is broken down into discrete tasks that can be delegated to agents for parallel execution.

## Key Discoveries from Python-Template

### 1. **Documentation Self-Healing System**
- **docs.yml workflow**: Auto-generates documentation from code/plans
- **build_context.py script**: Merges API docs, active plans, facts into CONTEXT.md
- **Automated changelog**: Tracks documentation regeneration
- **Auto-pruning**: Removes old agent-tmp files (>7 days)
- **Active plans summary**: Surfaces only recent/active work (<21 days)

### 2. **Centralized Agent Instructions (AGENTS.md)**
- Single source of truth for all agent guidance
- Includes environment setup, file organization, testing workflow
- Documents code quality requirements
- Provides common issues and solutions
- Referenced by all custom agent profiles

### 3. **DevContainer Configuration**
- Pre-configured VS Code development environment
- Auto-installs extensions (Copilot, Ruff, mypy, etc.)
- Auto-creates and activates venv
- Consistent settings across developers

### 4. **EditorConfig & GitAttributes**
- **EditorConfig**: Enforces consistent formatting (indentation, line endings, etc.)
- **GitAttributes**: Ensures proper line ending normalization across platforms
- Prevents formatting wars and merge conflicts

### 5. **UV Package Manager**
- Significantly faster than pip (10-100x for some operations)
- Used in CI workflows: `uv pip install --system -e '.[dev]'`
- Speeds up CI by reducing dependency installation time
- Drop-in replacement for pip commands

---

## Implementation Phases

### Phase 1: Foundation (Documentation & Development Environment)
**Priority**: High | **Estimated Effort**: 2-4 hours | **Dependencies**: None

#### Task 1.1: Add Core Documentation Files
**Agent**: Documentation Agent
**Deliverables**:
- [x] CONTRIBUTING.md (completed)
- [x] QUICK_REFERENCE.md (completed)
- [x] CHANGELOG.md (completed)

#### Task 1.2: Add EditorConfig & GitAttributes
**Agent**: Architecture Agent or manual
**Files to create**:
- `.editorconfig` - Consistent formatting across editors
- `.gitattributes` - Line ending normalization

**Benefits**:
- Prevents formatting inconsistencies
- Avoids merge conflicts from line ending differences
- Works with any editor/IDE

#### Task 1.3: Add DevContainer Configuration
**Agent**: Architecture Agent
**Files to create**:
- `.devcontainer/devcontainer.json` - VS Code dev container config

**Adaptations for CalendarBot**:
- Use Python 3.12 base image
- Include calendarbot_lite specific extensions
- Auto-install development dependencies
- Mount SSH keys for git operations

**Benefits**:
- Consistent development environment
- Faster onboarding for contributors
- Pre-configured with all tools

---

### Phase 2: Build Tools & Automation
**Priority**: High | **Estimated Effort**: 3-5 hours | **Dependencies**: Phase 1

#### Task 2.1: Create Makefile
**Agent**: Architecture Agent or manual
**Status**: ✅ **COMPLETED**
**File**: `Makefile`

#### Task 2.2: Add Documentation Self-Healing System
**Agent**: Documentation Agent + Architecture Agent
**Files to create**:
- `tools/build_context.py` - Documentation builder script
- `.github/workflows/docs.yml` - Auto-regeneration workflow
- `docs/CONTEXT.md` - Generated context file (initial)
- `docs/SUMMARY.md` - Documentation index
- `docs/facts.json` - Stable project facts

**Workflow**:
1. Script generates API docs from docstrings
2. Summarizes active plans from `agent-projects/`
3. Merges with `docs/facts.json`
4. Creates `docs/CONTEXT.md` (capped at 150KB)
5. Updates `docs/SUMMARY.md` and `docs/CHANGELOG.md`
6. Auto-commits changes

**Triggers**:
- Push to main (when docs/, src/, or schema files change)
- Nightly at 2 AM UTC
- Manual workflow dispatch

**Benefits**:
- Always up-to-date documentation
- AI agents have comprehensive context
- Reduces documentation drift
- Auto-prunes old temporary files

#### Task 2.3: Create Agent-Projects Structure
**Agent**: Manual or Architecture Agent
**Directories to create**:
- `agent-projects/` (if not exists)
- `agent-tmp/` (gitignored)

**Update .gitignore**:
```
# Agent temporary files
agent-tmp/

# Agent projects (committed)
# agent-projects/ is committed
```

**Create example plan**:
- `agent-projects/example-project/plan.md` with metadata template

---

### Phase 3: GitHub Workflows Enhancement
**Priority**: Medium | **Estimated Effort**: 4-6 hours | **Dependencies**: Phase 2

#### Task 3.1: Add Dependency Review Workflow
**Agent**: Security Agent
**File**: `.github/workflows/dependency-review.yml`

**Features**:
- Scans dependencies on PR for vulnerabilities
- Uses pip-audit + safety
- Comments on PR with findings
- Blocks merge on critical vulnerabilities

#### Task 3.2: Add Code Quality Workflow
**Agent**: Architecture Agent
**File**: `.github/workflows/code-quality.yml`

**Features**:
- Cyclomatic complexity analysis (radon)
- Maintainability index
- Dead code detection (vulture)
- Comments on PR with metrics

#### Task 3.3: Add Release Workflow
**Agent**: Architecture Agent
**File**: `.github/workflows/release.yml`

**Features**:
- Triggered on version tags (v*.*.*)
- Validates: tests, security, type checking
- Builds distributions (wheel + sdist)
- Creates GitHub release
- Optional: PyPI publishing (disabled by default for CalendarBot)

#### Task 3.4: Add Reusable Setup Workflow
**Agent**: Architecture Agent
**File**: `.github/workflows/reusable-setup.yml`

**Purpose**: DRY - common Python setup for other workflows
**Features**:
- Parameterized Python version
- Optional dev dependencies
- Advanced caching (pip, venv)
- Reusable across workflows

#### Task 3.5: Enhance Existing Workflows with UV
**Agent**: Performance Agent
**Files to update**:
- `.github/workflows/ci.yml`
- `.github/workflows/nightly-full-suite.yml`

**Changes**:
- Add uv installation step: `pip install uv`
- Replace `pip install` with `uv pip install --system`
- Measure CI time improvement (should be 20-40% faster)

**Example**:
```yaml
- name: Install uv
  run: pip install uv

- name: Install dependencies
  run: uv pip install --system -e '.[dev]'
```

#### Task 3.6: Add SARIF Security Reporting
**Agent**: Security Agent
**Files to update**:
- `.github/workflows/ci.yml` (enhance security job)

**Features**:
- Generate SARIF format from bandit
- Upload to GitHub Security tab
- Visible in repository security dashboard

---

### Phase 4: Enhanced Agent Profiles
**Priority**: Medium | **Estimated Effort**: 3-4 hours | **Dependencies**: Phase 1

#### Task 4.1: Create Additional Agent Profiles
**Agent**: Documentation Agent
**Files to create**:
- [x] `.github/agents/architecture.md` (completed)
- [ ] `.github/agents/test.md`
- [ ] `.github/agents/debug.md`
- [ ] `.github/agents/documentation.md`

**Each agent should**:
- Reference centralized AGENTS.md
- Include CalendarBot-specific context (Pi Zero 2W, resource constraints)
- Specify code quality requirements
- Document file organization expectations
- Include examples relevant to CalendarBot

#### Task 4.2: Update Agents README
**Agent**: Documentation Agent
**File**: `.github/agents/README.md`

**Enhancements**:
- Add new agent descriptions
- Document selection guide
- Explain file organization rubric
- Include CalendarBot-specific considerations
- Add quality gate requirements

---

### Phase 5: Testing & CI Scripts
**Priority**: Medium | **Estimated Effort**: 3-5 hours | **Dependencies**: Phase 2, 3

#### Task 5.1: Add Smart Test Selection Script
**Agent**: Test Agent
**File**: `.github/scripts/smart_test_selection.py`

**Features**:
- Analyzes changed files in PR
- Selects relevant tests to run
- Outputs test file list
- Integrates with CI workflow

**Note**: CalendarBot already has `scripts/smart_test_selector.py` - evaluate and potentially replace or enhance.

#### Task 5.2: Add Coverage Check Script
**Agent**: Test Agent
**File**: `.github/scripts/check_coverage.py`

**Features**:
- Validates coverage on changed files only
- Enforces coverage threshold (70%)
- Outputs detailed report
- Fails if coverage drops below threshold

---

### Phase 6: Documentation & Workflow Guides
**Priority**: Low | **Estimated Effort**: 2-3 hours | **Dependencies**: All previous phases

#### Task 6.1: Create Workflow Documentation
**Agent**: Documentation Agent
**File**: `docs/WORKFLOWS.md`

**Content**:
- Overview of all workflows
- What triggers each workflow
- How to use manual triggers
- Debugging failed workflows
- Artifact descriptions

#### Task 6.2: Create Migration Summary
**Agent**: Documentation Agent
**File**: `docs/MIGRATION_SUMMARY.md`

**Content**:
- What was added
- What was changed
- Breaking changes (if any)
- How to use new features
- Performance improvements

#### Task 6.3: Update Main Documentation
**Agent**: Documentation Agent
**Files to update**:
- `README.md` - Add badges, reference new docs
- `AGENTS.md` - Reference documentation self-healing
- `.github/copilot-instructions.md` - Update with new structure

---

## Task Assignment Matrix

### Immediate Tasks (Can Start Now)

| Task ID | Task | Agent | Priority | Effort | Dependencies |
|---------|------|-------|----------|--------|--------------|
| 1.2 | EditorConfig & GitAttributes | Architecture | High | 30min | None |
| 1.3 | DevContainer | Architecture | High | 1h | None |
| 2.2 | Doc Self-Healing | Docs + Arch | High | 2-3h | None |
| 2.3 | Agent-Projects Structure | Manual | High | 15min | None |

### Sequential Tasks (After Foundation)

| Task ID | Task | Agent | Priority | Effort | Dependencies |
|---------|------|-------|----------|--------|--------------|
| 3.1 | Dependency Review | Security | Medium | 1h | 2.3 |
| 3.2 | Code Quality Workflow | Architecture | Medium | 1h | 2.3 |
| 3.3 | Release Workflow | Architecture | Medium | 1.5h | 2.3 |
| 3.4 | Reusable Setup | Architecture | Medium | 1h | 2.3 |
| 3.5 | UV Integration | Performance | Medium | 1.5h | 2.2, 3.4 |
| 3.6 | SARIF Reporting | Security | Medium | 1h | 3.1 |

### Parallel Tasks (Agent Profiles)

| Task ID | Task | Agent | Priority | Effort | Dependencies |
|---------|------|-------|----------|--------|--------------|
| 4.1a | Test Agent | Documentation | Medium | 45min | 1.1 |
| 4.1b | Debug Agent | Documentation | Medium | 45min | 1.1 |
| 4.1c | Docs Agent | Documentation | Medium | 45min | 1.1 |
| 4.2 | Update Agents README | Documentation | Medium | 30min | 4.1a-c |

### Final Tasks

| Task ID | Task | Agent | Priority | Effort | Dependencies |
|---------|------|-------|----------|--------|--------------|
| 5.1 | Smart Test Selection | Test | Medium | 1.5h | 3.5 |
| 5.2 | Coverage Check | Test | 1h | 3.5 |
| 6.1 | Workflow Docs | Documentation | Low | 1.5h | All Phase 3 |
| 6.2 | Migration Summary | Documentation | Low | 1h | All previous |
| 6.3 | Update Main Docs | Documentation | Low | 1h | All previous |

---

## Detailed Task Breakdowns

### Task 1.2: EditorConfig & GitAttributes

**Create `.editorconfig`**:
```ini
# EditorConfig is awesome: https://EditorConfig.org
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_style = space
indent_size = 4
max_line_length = 100

[*.{yml,yaml}]
indent_style = space
indent_size = 2

[*.{json,toml}]
indent_style = space
indent_size = 2

[*.md]
trim_trailing_whitespace = false
max_line_length = off

[*.sh]
indent_style = space
indent_size = 2

[Makefile]
indent_style = tab
```

**Create `.gitattributes`**:
```
# Auto detect text files and perform LF normalization
* text=auto

# Source code
*.py text eol=lf
*.pyi text eol=lf

# Configuration files
*.json text eol=lf
*.toml text eol=lf
*.yaml text eol=lf
*.yml text eol=lf

# Scripts
*.sh text eol=lf
*.bash text eol=lf

# Documentation
*.md text eol=lf
*.txt text eol=lf

# Binary files
*.pyc binary
*.so binary
*.png binary
*.jpg binary
*.pdf binary
*.whl binary
*.egg binary
*.zip binary
*.tar binary
*.gz binary

# Export ignore
.gitattributes export-ignore
.gitignore export-ignore
.github/ export-ignore
.devcontainer/ export-ignore
tests/ export-ignore
```

### Task 1.3: DevContainer Configuration

**Create `.devcontainer/devcontainer.json`**:
```json
{
  "name": "CalendarBot Development",
  "image": "mcr.microsoft.com/devcontainers/python:1-3.12-bullseye",
  "features": {
    "ghcr.io/devcontainers/features/git:1": {},
    "ghcr.io/devcontainers/features/github-cli:1": {}
  },
  "customizations": {
    "vscode": {
      "settings": {
        "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
        "python.linting.enabled": true,
        "python.linting.pylintEnabled": false,
        "python.formatting.provider": "none",
        "python.analysis.typeCheckingMode": "basic",
        "python.terminal.activateEnvironment": true,
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
          "source.organizeImports": "explicit"
        },
        "[python]": {
          "editor.defaultFormatter": "charliermarsh.ruff",
          "editor.formatOnSave": true,
          "editor.codeActionsOnSave": {
            "source.fixAll": "explicit",
            "source.organizeImports": "explicit"
          }
        },
        "files.insertFinalNewline": true,
        "files.trimTrailingWhitespace": true
      },
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff",
        "ms-python.mypy-type-checker",
        "GitHub.copilot",
        "GitHub.copilot-chat",
        "tamasfe.even-better-toml",
        "redhat.vscode-yaml",
        "eamodio.gitlens"
      ]
    }
  },
  "postCreateCommand": "python3 -m venv venv && . venv/bin/activate && pip install --upgrade pip && pip install -e '.[dev]'",
  "remoteUser": "vscode",
  "updateContentCommand": ". venv/bin/activate && pip install -e '.[dev]'",
  "mounts": [
    "source=${localEnv:HOME}/.ssh,target=/home/vscode/.ssh,readonly,type=bind,consistency=cached"
  ]
}
```

### Task 2.2: Documentation Self-Healing System

**Components**:
1. `tools/build_context.py` - Main documentation builder
2. `.github/workflows/docs.yml` - Automation workflow
3. `docs/facts.json` - Stable project facts
4. `docs/CONTEXT.md` - Generated comprehensive context
5. `docs/SUMMARY.md` - Quick index

**Key Features**:
- Auto-generates API docs from Python docstrings
- Summarizes active plans (<21 days old, status=active)
- Merges everything into single CONTEXT.md
- Prunes old agent-tmp/ files (>7 days)
- Auto-commits changes
- Runs nightly and on relevant pushes

---

## Success Criteria

### Phase 1
- [ ] All documentation files created and reviewed
- [ ] EditorConfig working in editors
- [ ] GitAttributes preventing line ending issues
- [ ] DevContainer successfully builds and runs

### Phase 2
- [ ] Makefile targets all working
- [ ] Documentation self-healing workflow running successfully
- [ ] CONTEXT.md auto-generating correctly
- [ ] Agent-projects structure in place

### Phase 3
- [ ] All new workflows passing in CI
- [ ] Dependency review catching vulnerabilities
- [ ] Code quality metrics appearing on PRs
- [ ] UV speeding up CI (measure before/after)
- [ ] SARIF reports in Security tab

### Phase 4
- [ ] All agent profiles created
- [ ] Agents referencing centralized AGENTS.md
- [ ] CalendarBot-specific context included

### Phase 5
- [ ] Smart test selection working
- [ ] Coverage checks enforcing thresholds
- [ ] Scripts integrated with CI

### Phase 6
- [ ] Documentation complete and accurate
- [ ] Migration benefits documented
- [ ] README updated with new badges

---

## Risk Mitigation

### Potential Issues

1. **UV Compatibility**: UV might have edge cases
   - Mitigation: Test thoroughly, keep pip as fallback

2. **Documentation Size**: CONTEXT.md might exceed 150KB
   - Mitigation: Adjust truncation logic, prioritize recent content

3. **Workflow Complexity**: Too many workflows might confuse
   - Mitigation: Clear documentation, logical organization

4. **Breaking Changes**: New structure might break existing processes
   - Mitigation: Phase approach, test each phase

### Rollback Plan

Each phase can be rolled back independently:
- Phase 1: Remove files (low risk)
- Phase 2: Disable docs workflow, keep tools
- Phase 3: Disable individual workflows
- Phase 4: Agents are additive, no rollback needed
- Phase 5: Scripts are optional enhancements
- Phase 6: Documentation is additive

---

## Expected Benefits

### Immediate (Phase 1-2)
- ✅ Better developer onboarding (CONTRIBUTING, DevContainer)
- ✅ Consistent formatting (EditorConfig, GitAttributes)
- ✅ Quick command reference (QUICK_REFERENCE, Makefile)
- ✅ Always up-to-date docs (self-healing)

### Medium-term (Phase 3-4)
- ⚡ Faster CI (20-40% with UV)
- 🔒 Better security (dependency review, SARIF)
- 📊 Code quality visibility (complexity metrics)
- 🎯 Better agent guidance (enhanced profiles)

### Long-term (Phase 5-6)
- 🧪 Smarter testing (selective test execution)
- 📚 Comprehensive documentation
- 🚀 Easier releases (automated workflow)
- 🎓 Better contributor experience

---

## Next Steps

1. **Review this roadmap** with stakeholders
2. **Prioritize phases** based on immediate needs
3. **Assign tasks** to agents or execute manually
4. **Track progress** using GitHub Projects or issues
5. **Iterate** based on feedback and results

---

**Document Version**: 1.0
**Created**: 2024-11-12
**Last Updated**: 2024-11-12
