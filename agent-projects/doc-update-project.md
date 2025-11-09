# Documentation Update Strategy for CalendarBot

## Overview

This document defines the strategy and guidelines for maintaining and updating documentation in the CalendarBot repository. This strategy is designed to work with both human developers and AI coding agents (GitHub Copilot, Claude, etc.).

## Documentation Structure

### Core Documentation Locations

1. **Root Level Documentation**
   - `README.md` - Project overview, quick start, and feature summary
   - `AGENTS.md` - Comprehensive development guide for all contributors
   - `CLAUDE.md` - Quick reference for Claude Code interactions
   - `projectBrief.md` - High-level project context and architecture

2. **Technical Documentation** (`docs/`)
   - Component-specific guides (e.g., `ALEXA_DEPLOYMENT_GUIDE.md`)
   - Architecture and algorithm documentation (e.g., `ALGORITHMS.md`)
   - Security assessments and recommendations
   - Performance and monitoring guides
   - Deprecated system documentation in `docs/calendarbot (deprecated)/`

3. **Component Documentation** (`docs/lite/`)
   - Modular documentation for `calendarbot_lite` components
   - Server, API, calendar processing, infrastructure guides
   - Each numbered file covers a specific subsystem

4. **Kiosk Documentation** (`kiosk/docs/`)
   - Installation and deployment guides
   - Watchdog configuration and monitoring
   - Automated installation procedures

5. **Testing Documentation** (`tests/*/README.md`)
   - Test suite organization and conventions
   - Testing best practices and anti-patterns

6. **Agent Instructions** (`.github/`)
   - `copilot-instructions.md` - GitHub Copilot coding agent guidance
   - `agents/` - Specialized custom agent configurations

7. **Project Plans** (`project-plans/`)
   - Strategic planning documents
   - Feature design and task breakdowns

## Update Principles

### 1. Documentation-First Approach

**When implementing new features or fixing bugs:**
- Update documentation BEFORE or DURING implementation, not after
- Document design decisions and rationale
- Include examples and usage patterns
- Update related documentation (API docs, agent instructions, etc.)

### 2. Accuracy and Consistency

**All documentation must be:**
- **Accurate**: Reflect the current state of the code
- **Consistent**: Follow existing formatting and terminology
- **Complete**: Include all necessary context for understanding
- **Concise**: Avoid redundancy, link to existing docs when appropriate

### 3. Audience-Aware Documentation

**Different audiences need different documentation:**
- **Users**: Focus on what and how (README, deployment guides)
- **Developers**: Focus on why and how it works (AGENTS.md, component docs)
- **AI Agents**: Focus on patterns, conventions, and constraints (copilot-instructions.md, agent configs)
- **Contributors**: Focus on getting started and best practices (CONTRIBUTING if exists)

## Documentation Update Workflows

### For New Features

1. **Planning Phase**
   - Create or update design document in `project-plans/` if feature is substantial
   - Outline documentation requirements

2. **Implementation Phase**
   - Update relevant technical documentation in `docs/`
   - Add inline code documentation (docstrings, comments)
   - Update component-specific guides in `docs/lite/` if applicable

3. **Completion Phase**
   - Update root README.md if user-facing changes
   - Update AGENTS.md if development workflow changes
   - Update agent instructions if new patterns or constraints
   - Update deployment guides if configuration or setup changes

### For Bug Fixes

1. **Document the root cause** in commit messages
2. **Update troubleshooting sections** if bug was hard to diagnose
3. **Add to known issues** if workaround is temporary
4. **Update tests and test documentation** to prevent regression

### For Refactoring

1. **Update architecture documentation** if structure changes
2. **Update component guides** if interfaces or responsibilities change
3. **Update agent instructions** if coding patterns change
4. **Keep old patterns documented** in deprecation notes if needed for migration

### For Security Updates

1. **Update security documentation** (`docs/SECURITY_RECOMMENDATIONS.md`, etc.)
2. **Document security considerations** in relevant component docs
3. **Update deployment guides** if security configuration changes
4. **Update agent instructions** if new security patterns required

## Agent-Specific Guidelines

### When Agents Should Update Documentation

**ALWAYS update documentation when:**
- Adding new public APIs or endpoints
- Changing configuration options or environment variables
- Modifying deployment procedures
- Adding new dependencies or tools
- Implementing security features or fixes
- Changing data models or schemas
- Adding new testing infrastructure

**Consider updating documentation when:**
- Refactoring internal implementations (if it affects debugging or understanding)
- Optimizing performance (document the optimization and expected impact)
- Fixing non-obvious bugs (add to troubleshooting guides)
- Adding internal utilities that other developers might use

### Documentation Update Checklist for Agents

When making code changes, check:

- [ ] Does this change affect user-facing behavior? → Update README.md
- [ ] Does this change configuration? → Update .env.example and relevant guides
- [ ] Does this change deployment? → Update kiosk/docs/ or DEPLOYMENT guides
- [ ] Does this introduce new patterns? → Update AGENTS.md and copilot-instructions.md
- [ ] Does this add new dependencies? → Update requirements.txt and document why
- [ ] Does this change security posture? → Update security documentation
- [ ] Does this affect testing? → Update test documentation and pytest-best-practices.md
- [ ] Does this add new components? → Add component documentation to docs/lite/

### Documentation Quality Standards

**All documentation updates must:**

1. **Use clear, concise language**
   - Avoid jargon unless necessary and defined
   - Use active voice
   - Write in present tense

2. **Include examples**
   - Show actual code or command examples
   - Provide sample outputs
   - Demonstrate common use cases

3. **Maintain consistent formatting**
   - Use existing heading hierarchy
   - Follow markdown best practices
   - Keep line length reasonable (100-120 characters)
   - Use code fences with language specifiers

4. **Link to related documentation**
   - Cross-reference related topics
   - Use relative links for internal docs
   - Keep links up-to-date

5. **Include metadata**
   - Add "Last Updated" dates for time-sensitive docs
   - Include version information if applicable
   - Credit authors or reviewers if significant contribution

## Formatting Standards

### Markdown Conventions

- **Headers**: Use ATX-style headers (`#` prefix), not underlining
- **Lists**: Use `-` for unordered lists, `1.` for ordered lists
- **Code blocks**: Always specify language (```python, ```bash, etc.)
- **Links**: Use reference-style links for frequently referenced URLs
- **Emphasis**: Use `**bold**` for UI elements, `*italic*` for emphasis, `` `code` `` for code/commands
- **Line breaks**: Remove trailing whitespace, use blank lines between sections
- **Tables**: Align columns for readability in source

### Code Examples

```python
# Good: Complete, runnable example with context
from calendarbot_lite.config_manager import ConfigManager

# Initialize with environment variables
config = ConfigManager()
ics_url = config.get("CALENDARBOT_ICS_URL")

# Fetch calendar events
events = await fetch_calendar(ics_url)
print(f"Found {len(events)} events")
```

```python
# Bad: Incomplete, no context
events = fetch_calendar(url)
```

### Documentation File Naming

- Use `SCREAMING_SNAKE_CASE.md` for major guides (e.g., `DEPLOYMENT_GUIDE.md`)
- Use `kebab-case.md` for supplementary docs (e.g., `pytest-best-practices.md`)
- Use numbered prefixes for ordered series (e.g., `01-server-http-routing.md`)
- Use descriptive names that indicate content

## Deprecation and Archival

### Deprecating Documentation

When features or components are deprecated:

1. **Add deprecation notice** at the top of the document:
   ```markdown
   > **⚠️ DEPRECATED**: This component is deprecated as of [DATE]. 
   > Use [NEW_COMPONENT] instead. See [MIGRATION_GUIDE].
   ```

2. **Keep old documentation** for reference during transition period

3. **Move to archived location** after migration is complete:
   - Archived documentation goes in `docs/[component] (deprecated)/`
   - Update links in active documentation to point to new content

4. **Document migration path** in both old and new documentation

### Removing Documentation

**Only remove documentation when:**
- Feature has been completely removed from codebase
- All users have migrated (for public-facing features)
- Documented in changelog or release notes
- Archived copy kept for historical reference if significant

## Validation and Quality Assurance

### Pre-Commit Checks

- **Markdown linting**: Use markdownlint or similar
- **Link checking**: Verify internal links are valid
- **Spell checking**: Run spellcheck on new content
- **Formatting**: Ensure consistent formatting (remove trailing spaces, etc.)

### Review Checklist

Before committing documentation updates:

- [ ] All code examples are tested and work
- [ ] Links are valid and point to correct locations
- [ ] Formatting is consistent with existing docs
- [ ] Spelling and grammar are correct
- [ ] Changes are reflected in table of contents if applicable
- [ ] Cross-references are updated
- [ ] Examples include necessary context
- [ ] Sensitive information (credentials, private URLs) is removed

## Special Considerations

### Security Documentation

- **Never include sensitive data**: No actual credentials, API keys, private URLs
- **Use examples**: Show format with placeholder values
- **Document security implications**: Explain what could go wrong
- **Keep security docs up-to-date**: Security landscape changes rapidly

### Performance Documentation

- **Include actual measurements**: Don't just say "faster", show benchmarks
- **Document test conditions**: Hardware, data size, concurrency
- **Explain trade-offs**: What was sacrificed for performance gain
- **Update when performance characteristics change**

### API Documentation

- **Document all parameters**: Type, required/optional, default value, description
- **Show request/response examples**: Actual JSON/XML with all fields
- **Document error conditions**: What errors can occur and why
- **Include rate limits and constraints**: Help users avoid issues

## Continuous Improvement

### Documentation Debt

Track documentation debt just like technical debt:

- **Create issues** for missing or outdated documentation
- **Label issues** with `documentation` tag
- **Prioritize documentation** alongside feature work
- **Review documentation** during code reviews

### Feedback Loop

- **Monitor user questions**: What documentation is missing or unclear?
- **Update based on feedback**: Improve docs when confusion occurs
- **Track documentation metrics**: Views, search terms, feedback
- **Regular audits**: Quarterly review of documentation accuracy

## Implementation Notes

### For AI Coding Agents

When working on this repository:

1. **Read relevant documentation first** before making changes
2. **Update documentation as part of PR** - don't create separate documentation PRs
3. **Follow existing patterns** for documentation style and structure
4. **Ask for clarification** if documentation requirements are unclear
5. **Validate examples** by actually running them when possible
6. **Update this strategy** if you discover gaps or improvements

### For Human Developers

1. **Treat documentation as code** - same standards for quality and review
2. **Document as you code** - don't defer documentation to later
3. **Review documentation changes** as carefully as code changes
4. **Keep documentation DRY** - avoid duplication, use links
5. **Make documentation searchable** - use clear headings and keywords

## Success Metrics

Documentation quality can be measured by:

- **Coverage**: % of features/APIs documented
- **Accuracy**: % of documentation that matches current code
- **Freshness**: Average age of last update
- **Usability**: User feedback, questions that existing docs should answer
- **Discoverability**: Can users find what they need?

## Related Documents

- [AGENTS.md](../AGENTS.md) - Comprehensive development guide
- [CLAUDE.md](../CLAUDE.md) - Quick reference for Claude Code
- [.github/copilot-instructions.md](../.github/copilot-instructions.md) - GitHub Copilot agent guidance
- [docs/pytest-best-practices.md](../docs/pytest-best-practices.md) - Testing documentation standards

---

**Last Updated**: 2025-11-09  
**Version**: 1.0  
**Status**: Active

