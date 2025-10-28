# DEPRECATED - This Directory is Archived

**This `calendarbot/` directory is no longer actively maintained.**

## Important Notice

- **Status**: ARCHIVED / DEPRECATED
- **Active Project**: Use [`calendarbot_lite/`](../calendarbot_lite/) for all new development
- **Reason**: The calendarbot_lite implementation provides a more focused, lightweight solution for ICS calendar processing and Alexa integration

## What This Means

- No new features will be added to this codebase
- Bug fixes will not be applied unless critical
- Documentation may be outdated
- Tests may not be maintained
- Dependencies may become stale

## Migration Path

If you're currently using the legacy `calendarbot` application:

1. Review the [`calendarbot_lite/`](../calendarbot_lite/) implementation
2. Migrate to using `calendarbot_lite` for ICS parsing and calendar operations
3. The core ICS parsing logic has been refined and improved in the lite version

## For Developers and AI Agents

**DO NOT** modify or enhance code in this directory unless:
- You are explicitly maintaining legacy compatibility
- You are fixing a critical security issue
- You have been specifically instructed to work on archived code

**ALWAYS** default to working in `calendarbot_lite/` for:
- Calendar-related features
- ICS parsing improvements
- RRULE expansion enhancements
- Alexa integration work
- Bug fixes and optimizations

## Historical Context

This directory contains the original CalendarBot implementation with:
- Terminal UI with keyboard navigation
- Web interface with multiple layouts
- E-paper display support
- Complex caching system
- Full web server with settings UI

While feature-rich, this codebase became complex and difficult to maintain. The `calendarbot_lite` project provides a more maintainable, focused solution.

## Archives

For historical reference, this codebase is preserved in the repository but should be considered read-only unless explicitly required.

---

**Last Updated**: 2025-10-27
**Migration to**: [`calendarbot_lite/`](../calendarbot_lite/)
