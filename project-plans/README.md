# Project Plans

This directory contains architecture plans, design documents, and implementation roadmaps for CalendarBot features and improvements.

---

## Current Plans

### Lightweight UI Architecture (2025-12-29)

**Status:** ✅ **Approved - Implementation Starting**

**Problem:** Current kiosk runs X11 + Chromium (~260MB RAM) on Pi Zero 2W, which is resource-intensive and complex.

**Proposal:** Replace with lightweight Python framebuffer UI using pygame (~15MB RAM).

**Key Decisions:**
- ✅ Pygame approved for framebuffer rendering
- ✅ Remote backend support enabled
- ✅ Use existing .env configuration
- ✅ Bundle TTF fonts
- ✅ Keep X11 kiosk as fallback
- ✅ Resilient error handling (15min threshold)
- ✅ Separate installer based on install-kiosk.sh

**Documents:**

1. **[lightweight-ui-summary.md](./lightweight-ui-summary.md)** - Executive Summary (8KB)
   - Quick overview for decision makers
   - Key metrics and benefits
   - 10 questions for review
   - **Start here** for high-level understanding

2. **[lightweight-ui-architecture.md](./lightweight-ui-architecture.md)** - Full Technical Architecture (28KB)
   - Complete design specification
   - 5 technology options evaluated
   - Implementation phases (5 phases, 3-4 weeks)
   - Dependencies, deployment, testing strategy
   - **Read this** for implementation details

3. **[architecture-comparison.md](./architecture-comparison.md)** - Visual Comparisons (16KB)
   - Side-by-side architecture diagrams
   - Memory usage breakdowns
   - Performance metrics
   - Reliability analysis
   - **Review this** for visual understanding

**Key Metrics:**
- Memory: 84-94% reduction (260MB → 15-45MB)
- Startup: 12x faster (60s → 5s)
- Complexity: 6 processes → 1-2 processes
- Reliability: Fewer failure points, simpler recovery

**Next Steps:**
- ✅ Architecture approved by user
- 🚀 Begin Phase 1: Core Rendering implementation
- 📦 Set up framebuffer_ui package
- 🎨 Implement pygame renderer with bundled fonts

---

## Document Navigation

### For Decision Makers
👉 Read **[lightweight-ui-summary.md](./lightweight-ui-summary.md)** first  
⏱️ 5-10 minute read

### For Architects
👉 Read **[lightweight-ui-architecture.md](./lightweight-ui-architecture.md)**  
⏱️ 20-30 minute read

### For Visual Learners
👉 Read **[architecture-comparison.md](./architecture-comparison.md)**  
⏱️ 10-15 minute read

---

## Document History

| Date | Document | Status | Author |
|------|----------|--------|--------|
| 2025-12-29 | Lightweight UI Architecture | ✅ Approved | Principal Engineer |

---

## Contributing

To add a new project plan:

1. Create a new markdown file in this directory
2. Follow the naming convention: `feature-name-type.md`
3. Update this README with a link to your document
4. Include: problem statement, proposed solution, implementation plan, risks
5. Mark status: 🟡 Planning, 🟢 Approved, 🔵 In Progress, ✅ Complete, ❌ Rejected

---

## References

- [AGENTS.md](../AGENTS.md) - Development guide
- [CLAUDE.md](../CLAUDE.md) - Quick reference for AI agents
- [README.md](../README.md) - Project overview
- [kiosk/README.md](../kiosk/README.md) - Kiosk deployment documentation

