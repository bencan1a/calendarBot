# Agent Prompts: Python-Template Migration

This document provides ready-to-use prompts for agents to execute each task in the migration. Tasks are marked as **PARALLEL** (can run simultaneously) or **SERIAL** (must wait for dependencies).

---

## Phase 1: Foundation ✅ COMPLETED

All Phase 1 tasks have been completed.

---

## Phase 2: Build Tools & Automation

### Task 2.1: Makefile ✅ COMPLETED

### Task 2.2: Documentation Self-Healing System
**Execution**: **SERIAL** (requires completion first, then others can reference)
**Agent**: Documentation Agent + Architecture Agent
**Estimated Time**: 2-3 hours

**Prompt for Agent:**
```
Create a documentation self-healing system for CalendarBot based on the python-template approach.

CONTEXT:
- CalendarBot is a Python project with calendarbot_lite/ as the main source
- Documentation in docs/ directory
- Agent projects tracked in agent-projects/
- Temporary files in agent-tmp/ (gitignored)

DELIVERABLES:
1. Create tools/build_context.py script that:
   - Generates API documentation from Python docstrings in calendarbot_lite/
   - Scans agent-projects/ for active plans (status=active, <21 days old)
   - Merges with stable facts from docs/facts.json
   - Creates docs/CONTEXT.md (capped at 150KB)
   - Updates docs/SUMMARY.md with component index
   - Appends to docs/CHANGELOG.md with timestamp
   - Prunes agent-tmp/ files older than 7 days

2. Create .github/workflows/docs.yml that:
   - Triggers on: push to main (when docs/, calendarbot_lite/, or schema files change)
   - Triggers on: nightly at 2 AM UTC
   - Triggers on: manual workflow dispatch with force rebuild option
   - Runs tools/build_context.py
   - Auto-commits changes if docs/CONTEXT.md or docs/SUMMARY.md changed
   - Uploads documentation artifacts

3. Create docs/facts.json with stable project facts:
   - Project name, description, purpose
   - Primary use case (Pi Zero 2W kiosk)
   - Scale (1-5 users, personal project)
   - Resource constraints (memory, CPU, startup time)
   - Active codebase (calendarbot_lite/)
   - Archived code (calendarbot/ - DO NOT modify)

4. Create initial docs/CONTEXT.md structure
5. Create docs/SUMMARY.md index

REFERENCE:
- See /tmp/python-template/tools/build_context.py for implementation example
- Adapt for CalendarBot's structure (calendarbot_lite vs src/)
- Include CalendarBot-specific context (Pi Zero 2W, Alexa, Kiosk)

QUALITY REQUIREMENTS:
- Script must handle missing files gracefully
- Must respect 150KB limit for CONTEXT.md
- Must not fail if no active plans exist
- Must validate JSON structure of docs/facts.json
- Workflow must only commit if files actually changed

VALIDATION:
1. Run tools/build_context.py manually
2. Verify docs/CONTEXT.md generated correctly
3. Verify docs/SUMMARY.md updated
4. Verify docs/CHANGELOG.md has new entry
5. Test workflow with manual trigger
6. Verify auto-pruning of old agent-tmp files
```

### Task 2.3: Agent-Projects Structure ✅ COMPLETED

---

## Phase 3: GitHub Workflows Enhancement

**Note**: Tasks 3.1-3.4 can run in PARALLEL. Task 3.5 is SERIAL (depends on 3.4). Task 3.6 is SERIAL (depends on 3.1).

### Task 3.1: Dependency Review Workflow
**Execution**: **PARALLEL** (can run with 3.2, 3.3, 3.4)
**Agent**: Security Agent
**Estimated Time**: 1 hour

**Prompt for Agent:**
```
Create a dependency review workflow for CalendarBot to scan for security vulnerabilities.

CONTEXT:
- CalendarBot uses pyproject.toml for dependencies
- Must check dependencies on PR changes
- Should comment on PRs with findings
- Must block merge on critical vulnerabilities

DELIVERABLE:
Create .github/workflows/dependency-review.yml that:
1. Triggers on: pull_request when pyproject.toml or requirements*.txt changes
2. Uses actions/dependency-review-action@v4
3. Runs pip-audit and safety checks
4. Fails on severity: moderate or higher
5. Comments on PR with vulnerability summary
6. Uploads detailed audit reports as artifacts (30-day retention)

REFERENCE:
- See /tmp/python-template/.github/workflows/dependency-review.yml
- Adapt paths for CalendarBot (calendarbot_lite vs src)

VALIDATION:
1. Test workflow with manual trigger
2. Verify pip-audit runs correctly
3. Verify safety check runs
4. Check artifact upload works
5. Validate YAML syntax: make check-yaml
```

### Task 3.2: Code Quality Workflow
**Execution**: **PARALLEL** (can run with 3.1, 3.3, 3.4)
**Agent**: Architecture Agent
**Estimated Time**: 1 hour

**Prompt for Agent:**
```
Create a code quality workflow for CalendarBot to analyze complexity metrics.

CONTEXT:
- CalendarBot source is in calendarbot_lite/
- Should analyze on PRs to provide feedback
- Must not block merges, only provide insights

DELIVERABLE:
Create .github/workflows/code-quality.yml that:
1. Triggers on: pull_request
2. Installs radon for cyclomatic complexity analysis
3. Installs vulture for dead code detection
4. Analyzes calendarbot_lite/ directory
5. Comments on PR with:
   - Cyclomatic complexity by function (flag functions with CC > 10)
   - Maintainability index
   - Dead code detection results
6. Uploads analysis reports as artifacts (30-day retention)
7. Does NOT fail the build (informational only)

TOOLS TO USE:
- radon cc -s -a calendarbot_lite/
- radon mi calendarbot_lite/
- vulture calendarbot_lite/ --min-confidence 80

VALIDATION:
1. Run radon and vulture locally on calendarbot_lite/
2. Test workflow with manual trigger
3. Verify PR comment generation
4. Validate YAML syntax: make check-yaml
```

### Task 3.3: Release Workflow
**Execution**: **PARALLEL** (can run with 3.1, 3.2, 3.4)
**Agent**: Architecture Agent
**Estimated Time**: 1.5 hours

**Prompt for Agent:**
```
Create an automated release workflow for CalendarBot.

CONTEXT:
- CalendarBot is a personal project, not published to PyPI
- Releases are for kiosk deployment tracking
- Should validate before creating release

DELIVERABLE:
Create .github/workflows/release.yml that:
1. Triggers on: tags matching v*.*.* (e.g., v1.0.0)
2. Pre-release validation:
   - Run full test suite
   - Run security scan (bandit)
   - Run type checking (mypy)
3. Build distributions (wheel + sdist) using python -m build
4. Extract changelog entry for this version from CHANGELOG.md
5. Create GitHub release with:
   - Tag name and version
   - Changelog excerpt
   - Built distributions as assets
6. DO NOT publish to PyPI (this is a personal project)

REFERENCE:
- See /tmp/python-template/.github/workflows/release.yml
- Remove PyPI publishing steps
- Keep validation and GitHub release creation

VALIDATION:
1. Test workflow with manual trigger and sample tag
2. Verify build artifacts created
3. Verify changelog extraction works
4. Validate YAML syntax: make check-yaml
```

### Task 3.4: Reusable Setup Workflow
**Execution**: **PARALLEL** (can run with 3.1, 3.2, 3.3)
**Agent**: Architecture Agent
**Estimated Time**: 1 hour

**Prompt for Agent:**
```
Create a reusable workflow for common Python setup to promote DRY principles.

CONTEXT:
- Multiple workflows need Python setup with caching
- Should support different Python versions
- Should support optional dev dependencies

DELIVERABLE:
Create .github/workflows/reusable-setup.yml that:
1. Is a reusable workflow (workflow_call)
2. Accepts inputs:
   - python-version (default: '3.12')
   - install-dev (boolean, default: true)
   - cache-key-suffix (string, optional)
3. Sets up Python with actions/setup-python@v5
4. Configures pip caching
5. Optionally installs with dev dependencies
6. Outputs Python version used

CAN BE USED BY:
- Future workflows to reduce duplication
- Consistent setup across all workflows

REFERENCE:
- See /tmp/python-template/.github/workflows/reusable-setup.yml

VALIDATION:
1. Validate YAML syntax: make check-yaml
2. Create a test workflow that calls this reusable workflow
3. Verify caching works correctly
```

### Task 3.5: UV Integration in Existing Workflows
**Execution**: **SERIAL** (depends on Task 3.4 completion)
**Agent**: Performance Agent
**Estimated Time**: 1.5 hours

**Prompt for Agent:**
```
Integrate UV package manager into CalendarBot CI workflows for faster dependency installation.

CONTEXT:
- UV is 10-100x faster than pip
- CalendarBot uses ci.yml and nightly-full-suite.yml
- Must maintain compatibility with existing setup

DELIVERABLES:
1. Update .github/workflows/ci.yml:
   - Add uv installation: pip install uv
   - Replace pip install with: uv pip install --system -e '.[dev]'
   - Measure time improvement in workflow runs

2. Update .github/workflows/nightly-full-suite.yml:
   - Add uv installation
   - Replace pip install commands
   - Ensure all dependency installations use uv

3. Optional: Update reusable-setup.yml (Task 3.4) to support UV

IMPORTANT:
- Keep --system flag for uv pip install (required in CI environments)
- Do NOT change local development docs (keep pip for developers)
- Test thoroughly - UV should be drop-in compatible

VALIDATION:
1. Run CI workflow and compare times before/after
2. Verify all dependencies install correctly
3. Ensure tests still pass
4. Document time savings in commit message
5. Validate YAML syntax: make check-yaml

EXPECTED RESULT:
- 20-40% faster CI runs
- No functional changes to tests or builds
```

### Task 3.6: SARIF Security Reporting
**Execution**: **SERIAL** (depends on Task 3.1 completion)
**Agent**: Security Agent
**Estimated Time**: 1 hour

**Prompt for Agent:**
```
Add SARIF format security reporting to make vulnerabilities visible in GitHub Security tab.

CONTEXT:
- CalendarBot already runs bandit for security scanning
- SARIF format uploads to GitHub Security tab
- Makes security issues more visible and trackable

DELIVERABLE:
Update .github/workflows/ci.yml security job to:
1. Generate SARIF output from bandit:
   - bandit -r calendarbot_lite -f sarif -o bandit.sarif
2. Upload SARIF to GitHub Security:
   - uses: github/codeql-action/upload-sarif@v3
   - with sarif_file: bandit.sarif
3. Ensure proper permissions:
   - security-events: write
4. Continue to upload JSON report as artifact

REFERENCE:
- GitHub SARIF documentation
- CodeQL upload-sarif action

VALIDATION:
1. Run workflow and verify SARIF generation
2. Check GitHub Security tab for uploaded results
3. Verify existing bandit functionality unchanged
4. Validate YAML syntax: make check-yaml
```

---

## Phase 4: Enhanced Agent Profiles

**Note**: Tasks 4.1a, 4.1b, 4.1c can run in PARALLEL. Task 4.2 is SERIAL (depends on 4.1a-c).

### Task 4.1a: Test Agent Profile
**Execution**: **PARALLEL** (can run with 4.1b, 4.1c)
**Agent**: Documentation Agent
**Estimated Time**: 45 minutes

**Prompt for Agent:**
```
Create a test agent profile for CalendarBot specialized in testing strategies.

CONTEXT:
- CalendarBot has comprehensive testing in tests/lite/
- Uses pytest with markers (unit, integration, smoke, slow)
- Has specific testing anti-patterns to avoid (see docs/pytest-best-practices.md)
- Must reference centralized AGENTS.md

DELIVERABLE:
Create .github/agents/test.md that includes:
1. Agent metadata (name, description, tools)
2. Primary responsibilities for testing
3. CalendarBot testing context:
   - Test directory: tests/lite/
   - Test markers and their usage
   - Coverage threshold: 70%
   - Critical anti-patterns from pytest-best-practices.md
4. Testing guidelines specific to CalendarBot:
   - Mock at I/O boundaries (HTTP, filesystem, time)
   - No conditional assertions in tests
   - Test one behavior per test
   - Strategic mocking, not business logic
5. Reference to AGENTS.md for environment setup
6. File organization (agent-tmp/, agent-projects/, docs/)
7. Code quality requirements

REFERENCE:
- /tmp/python-template/.github/agents/test.md
- /home/runner/work/calendarBot/calendarBot/docs/pytest-best-practices.md
- .github/agents/architecture.md (for structure)

VALIDATION:
1. Verify markdown formatting
2. Check all CalendarBot-specific context included
3. Ensure references to AGENTS.md are correct
```

### Task 4.1b: Debug Agent Profile
**Execution**: **PARALLEL** (can run with 4.1a, 4.1c)
**Agent**: Documentation Agent
**Estimated Time**: 45 minutes

**Prompt for Agent:**
```
Create a debug agent profile for CalendarBot specialized in debugging and troubleshooting.

CONTEXT:
- CalendarBot runs on Raspberry Pi Zero 2W (resource-constrained)
- Has specific logging and debugging tools
- Common issues: memory leaks, performance, timezone bugs

DELIVERABLE:
Create .github/agents/debug.md that includes:
1. Agent metadata (name, description, tools)
2. Primary responsibilities for debugging
3. CalendarBot debugging context:
   - Resource constraints (Pi Zero 2W: <100MB RAM, single-core)
   - Common issues: ICS parsing, RRULE expansion, timezone handling
   - Debugging tools: pytest, ipdb, memory_profiler
   - Log locations and formats
4. Debugging guidelines:
   - Performance profiling for Pi Zero 2W
   - Memory leak detection
   - Timezone debugging strategies
   - Kiosk watchdog system troubleshooting
5. Reference to AGENTS.md for environment setup
6. File organization for debug artifacts
7. Code quality requirements

REFERENCE:
- /tmp/python-template/.github/agents/debug.md
- .github/agents/architecture.md (for structure)

VALIDATION:
1. Verify markdown formatting
2. Check all CalendarBot-specific context included
3. Include Pi Zero 2W specific debugging guidance
```

### Task 4.1c: Documentation Agent Profile
**Execution**: **PARALLEL** (can run with 4.1a, 4.1b)
**Agent**: Documentation Agent
**Estimated Time**: 45 minutes

**Prompt for Agent:**
```
Create a documentation agent profile for CalendarBot specialized in technical writing.

CONTEXT:
- CalendarBot has extensive documentation in docs/
- Uses Google-style docstrings
- Documentation includes guides, ADRs, and API docs

DELIVERABLE:
Create .github/agents/documentation.md that includes:
1. Agent metadata (name, description, tools)
2. Primary responsibilities for documentation
3. CalendarBot documentation context:
   - Documentation locations: docs/, README.md, AGENTS.md
   - Docstring format: Google-style
   - Target audience: developers and AI agents
   - Documentation types: guides, API docs, architecture docs
4. Documentation guidelines:
   - When to write to docs/ vs agent-projects/
   - How to structure guides
   - Referencing CalendarBot-specific features (Pi Zero 2W, Alexa, Kiosk)
   - Keeping docs synchronized with code
5. Reference to AGENTS.md for environment setup
6. File organization (permanent vs ephemeral docs)
7. Code quality requirements

REFERENCE:
- /tmp/python-template/.github/agents/documentation.md
- .github/agents/architecture.md (for structure)

VALIDATION:
1. Verify markdown formatting
2. Check all CalendarBot-specific context included
3. Include documentation self-healing context (once Task 2.2 complete)
```

### Task 4.2: Update Agents README
**Execution**: **SERIAL** (depends on Tasks 4.1a, 4.1b, 4.1c)
**Agent**: Documentation Agent
**Estimated Time**: 30 minutes

**Prompt for Agent:**
```
Update .github/agents/README.md to include new agent profiles and enhanced guidance.

CONTEXT:
- CalendarBot now has 7 agent profiles total
- Need to organize and document all agents
- Should include selection guide and usage examples

DELIVERABLE:
Update .github/agents/README.md to:
1. Add descriptions for new agents:
   - Test Agent (test.md)
   - Debug Agent (debug.md)
   - Documentation Agent (documentation.md)
2. Update agent selection guide table
3. Add usage examples for each agent
4. Document file organization rubric
5. Include code quality requirements
6. Add CalendarBot-specific considerations:
   - Pi Zero 2W resource constraints
   - Project scale (personal, 1-5 users)
   - Active vs archived codebase

CURRENT AGENTS:
- architecture.md (new)
- test.md (new)
- debug.md (new)
- documentation.md (new)
- security-agent.md (existing)
- performance-agent.md (existing)
- ics-calendar-agent.md (existing)
- my-agent.md (existing)

VALIDATION:
1. Verify all agents listed and described
2. Check agent selection guide is accurate
3. Ensure examples are CalendarBot-specific
4. Verify markdown formatting
```

---

## Phase 5: Testing & CI Scripts

**Note**: Tasks 5.1 and 5.2 can run in PARALLEL.

### Task 5.1: Smart Test Selection Script
**Execution**: **PARALLEL** (can run with 5.2)
**Agent**: Test Agent
**Estimated Time**: 1.5 hours

**Prompt for Agent:**
```
Evaluate and potentially enhance CalendarBot's smart test selection capabilities.

CONTEXT:
- CalendarBot already has scripts/smart_test_selector.py
- Python-template has .github/scripts/smart_test_selection.py
- Need to compare approaches and adopt best features

DELIVERABLE:
1. Review both implementations:
   - CalendarBot: scripts/smart_test_selector.py
   - Template: /tmp/python-template/.github/scripts/smart_test_selection.py

2. Evaluate which is better or if they should be merged:
   - Feature comparison
   - Performance comparison
   - Accuracy of test selection

3. Take one of these actions:
   a. Keep CalendarBot's version (if superior)
   b. Replace with template's version (if superior)
   c. Enhance CalendarBot's version with template features
   d. Create new hybrid approach

4. If changes made:
   - Update .github/workflows/ci.yml to use the script
   - Add comprehensive docstrings
   - Add usage examples in comments

5. Ensure script:
   - Analyzes git diff to find changed files
   - Maps changed files to relevant test files
   - Outputs test file list in format pytest can consume
   - Handles edge cases (no changes, all files changed)

VALIDATION:
1. Run script against sample PRs
2. Verify test selection accuracy
3. Test integration with CI workflow
4. Document decision in commit message
```

### Task 5.2: Coverage Check Script
**Execution**: **PARALLEL** (can run with 5.1)
**Agent**: Test Agent
**Estimated Time**: 1 hour

**Prompt for Agent:**
```
Create a coverage check script that validates coverage on changed files only.

CONTEXT:
- CalendarBot requires 70% coverage threshold
- Should check coverage on changed files in PRs
- Should integrate with CI workflow

DELIVERABLE:
Create .github/scripts/check_coverage.py that:
1. Takes inputs:
   - --coverage-file (path to coverage.json)
   - --changed-files (list of changed Python files)
   - --threshold (default: 70.0)
   - --base-ref (git ref to compare against)
2. Extracts coverage data for changed files only
3. Calculates aggregate coverage for changed files
4. Outputs:
   - Per-file coverage report
   - Aggregate coverage percentage
   - Pass/fail status
5. Exits with code 1 if coverage below threshold
6. Provides clear error messages

INTEGRATION:
- Update .github/workflows/ci.yml to call this script
- Run after coverage.json is generated
- Only check changed files, not entire codebase

REFERENCE:
- /tmp/python-template/.github/scripts/check_coverage.py

VALIDATION:
1. Test with sample coverage.json
2. Test with various changed file lists
3. Verify threshold enforcement
4. Test integration in CI workflow
```

---

## Phase 6: Documentation & Workflow Guides

**Note**: Tasks 6.1, 6.2, 6.3 can run in PARALLEL after all previous phases complete.

### Task 6.1: Workflow Documentation
**Execution**: **PARALLEL** (can run with 6.2, 6.3 after Phase 3 complete)
**Agent**: Documentation Agent
**Estimated Time**: 1.5 hours

**Prompt for Agent:**
```
Create comprehensive documentation for all GitHub Actions workflows in CalendarBot.

CONTEXT:
- CalendarBot will have 7+ workflows after migration
- Need clear documentation for using and debugging workflows
- Target audience: developers and contributors

DELIVERABLE:
Create docs/WORKFLOWS.md that documents:
1. Overview of all workflows:
   - ci.yml - CI/CD pipeline
   - nightly-full-suite.yml - Nightly regression
   - e2e-kiosk.yml - End-to-end kiosk tests
   - dependency-review.yml - Security scanning
   - code-quality.yml - Complexity metrics
   - release.yml - Automated releases
   - docs.yml - Documentation self-healing
   - reusable-setup.yml - Reusable setup

2. For each workflow:
   - Purpose and description
   - Trigger conditions
   - What it does (steps overview)
   - How to trigger manually
   - Expected artifacts
   - Common failure scenarios

3. Debugging guide:
   - How to read workflow logs
   - How to download artifacts
   - How to re-run failed workflows
   - Common issues and solutions

4. Best practices:
   - When to use manual triggers
   - How to test workflow changes
   - Artifact retention policies

VALIDATION:
1. Verify all workflows documented
2. Test manual trigger instructions
3. Ensure debugging guide is clear
4. Check markdown formatting
```

### Task 6.2: Migration Summary
**Execution**: **PARALLEL** (can run with 6.1, 6.3 after all phases complete)
**Agent**: Documentation Agent
**Estimated Time**: 1 hour

**Prompt for Agent:**
```
Create a summary document of the python-template migration.

CONTEXT:
- This migration added significant infrastructure
- Need to document what changed and how to use it
- Target audience: project maintainers and contributors

DELIVERABLE:
Create docs/MIGRATION_SUMMARY.md that includes:
1. Executive summary:
   - What was migrated
   - Why it was done
   - Key benefits

2. What was added:
   - Documentation (CONTRIBUTING, QUICK_REFERENCE, etc.)
   - Development tools (Makefile, EditorConfig, DevContainer)
   - Workflows (dependency-review, code-quality, release)
   - Agent profiles (test, debug, documentation)
   - Scripts (smart selection, coverage check)

3. What changed:
   - CI workflow enhancements (UV integration)
   - Documentation structure (agent-projects/)
   - Security reporting (SARIF)

4. Breaking changes:
   - None expected, but document any

5. How to use new features:
   - Quick start with new tools
   - How to use new workflows
   - How to work with agent profiles

6. Performance improvements:
   - CI speed improvements (UV)
   - Workflow optimizations

7. Next steps and recommendations

VALIDATION:
1. Verify accuracy of all information
2. Test instructions for new features
3. Check markdown formatting
```

### Task 6.3: Update Main Documentation
**Execution**: **PARALLEL** (can run with 6.1, 6.2 after all phases complete)
**Agent**: Documentation Agent
**Estimated Time**: 1 hour

**Prompt for Agent:**
```
Update main documentation files to reference new features and structure.

DELIVERABLES:
1. Update README.md:
   - Add badges for new workflows
   - Update quick start to reference new tools
   - Add links to new documentation
   - Update project structure section

2. Update AGENTS.md:
   - Reference documentation self-healing system
   - Update file organization section
   - Link to new agent profiles
   - Update code quality requirements

3. Update .github/copilot-instructions.md:
   - Reference new agent profiles
   - Update file organization guidance
   - Add new workflow information
   - Reference IMPLEMENTATION_ROADMAP location

4. Update CHANGELOG.md:
   - Add entry for migration completion
   - List all new features
   - Document performance improvements

VALIDATION:
1. Verify all links work
2. Check markdown formatting
3. Ensure consistency across documents
4. Test that badges display correctly
```

---

## Execution Strategy

### Parallel Execution Groups

**Group A - Phase 3 Workflows (Can Run in Parallel)**
- Task 3.1: Dependency Review Workflow
- Task 3.2: Code Quality Workflow
- Task 3.3: Release Workflow
- Task 3.4: Reusable Setup Workflow

**Group B - Phase 4 Agent Profiles (Can Run in Parallel)**
- Task 4.1a: Test Agent Profile
- Task 4.1b: Debug Agent Profile
- Task 4.1c: Documentation Agent Profile

**Group C - Phase 5 Scripts (Can Run in Parallel)**
- Task 5.1: Smart Test Selection Script
- Task 5.2: Coverage Check Script

**Group D - Phase 6 Documentation (Can Run in Parallel, after all previous phases)**
- Task 6.1: Workflow Documentation
- Task 6.2: Migration Summary
- Task 6.3: Update Main Documentation

### Serial Dependencies

1. **Task 2.2** (Documentation Self-Healing) → Must complete before Phase 3 starts
2. **Task 3.4** (Reusable Setup) → Must complete before Task 3.5 (UV Integration)
3. **Task 3.1** (Dependency Review) → Must complete before Task 3.6 (SARIF)
4. **Tasks 4.1a, 4.1b, 4.1c** → Must complete before Task 4.2 (Agents README)
5. **All Phase 3-5 tasks** → Must complete before Phase 6 tasks

### Recommended Execution Order

**Week 1:**
- Task 2.2: Documentation Self-Healing (2-3 hours) - SERIAL, highest priority

**Week 2:**
- Run Group A in parallel (4 hours total, ~1 hour per task)
- Task 3.5: UV Integration (1.5 hours) - after 3.4 completes
- Task 3.6: SARIF Reporting (1 hour) - after 3.1 completes

**Week 3:**
- Run Group B in parallel (2.5 hours total, ~45 min per task)
- Task 4.2: Update Agents README (30 min) - after Group B completes
- Run Group C in parallel (2.5 hours total, ~1-1.5 hours per task)

**Week 4:**
- Run Group D in parallel (3.5 hours total, ~1-1.5 hours per task)
- Final review and validation

**Total Estimated Time**: 15-20 hours of agent work
**Calendar Time with Parallelization**: 3-4 weeks

---

## Using These Prompts

1. **Copy the entire prompt** for the task you want to execute
2. **Send to the designated agent** (or use a general-purpose agent)
3. **Include any necessary context files** as attachments
4. **Review agent output** before committing
5. **Run validation steps** listed in each prompt
6. **Mark task as complete** in IMPLEMENTATION_ROADMAP.md

## Notes

- All prompts include validation steps
- All prompts reference CalendarBot-specific context
- Serial dependencies are clearly marked
- Parallel tasks can be distributed to multiple agents
- Each prompt is self-contained and actionable
