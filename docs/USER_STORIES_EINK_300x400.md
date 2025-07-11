# User Stories for CalendarBot 300x400 e-ink Display Mode

This document captures the user stories for implementing the new 300x400 pixel e-ink display mode for CalendarBot. 

## Background
CalendarBot now needs to support a smaller 300x400 e-ink screen variant used in portable devices with reduced display area. This mode must maintain core functionality while adapting to the 62.5% height reduction compared to the standard 480x800 display.

## Functional Area Breakdown

### Configuration

*   Users should be able to enable/disable this mode in settings
*   Need to define scaling parameters and resolution overrides

#### User Story #1
**Persona:** End User  
**Goal:** Enable 300x400 mode through setup wizard  
**Acceptance:** Display renders correctly at 300x400 resolution  
**Priority:** High/P1  
<TBD: Actual criteria details here>

### Information Display

*   Adjust font sizes for limited height
*   Re-prioritize information presentation for small displays
*   Collapse optional/secondary content areas

#### User Story #2
**Persona:** Early Adopter  
**Goal:** View full day+week schedule on small screen  
**Acceptance:** Primary events display vertically with scrolling  
**Priority:** High/P2  
<TBD: Adaptation details here>

### Navigation

*   Optimize navigation elements for reduced vertical space
*   Simplify menu structure for tactile interaction

#### User Story #3
**Persona:** Power User  
**Goal:** Quick navigation using minimal screen space  
**Acceptance:** Top/bottom menu buttons use 5% screen height  
**Priority:** Medium/P3  
<TBD: Tactical adaptations here>

## Implementation Guidance

*   Renderer Protocol must account for height-constrained layouts in [`calendarbot/display/renderer_protocol.py`](../calendarbot/display/renderer_protocol.py)
*   Consider vertical scrolling optimizations for performance impact
*   Adapt existing `CSS` in [`eink-compact-300x400.css`](../calendarbot/web/static/eink-compact-300x400.css) files

## Cross-references

*   Mode implementation details in [`daemon.py`](../calendarbot/cli/modes/daemon.py)
*   Performance optimization docs in [`PERFORMANCE.md`](./PERFORMANCE.md#rendering-optimizations)

<TBD: More detailed stories, sub-headings, and technical specs as finalized>