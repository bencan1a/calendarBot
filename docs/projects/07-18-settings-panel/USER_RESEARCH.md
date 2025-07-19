# CalendarBot Settings Panel User Research Report

## Executive Summary

This research explores user requirements for a web-based settings panel for CalendarBot, focusing on configuration options that are currently difficult to access or don't exist. The primary user need is democratizing configuration access for technical users who prefer web interfaces over CLI tools.

## User Profile

**Primary Persona:** Technical users who understand configuration concepts but prefer web interfaces over command-line tools.

**Current Behavior:** Uses CLI parameters during development but wants to provide easier access for end users without requiring CLI knowledge.

## Core Problem Statement

Users need intuitive web-based access to advanced configuration options that either don't exist today or require CLI expertise to modify. The current system relies heavily on YAML files, CLI parameters, and environment variables, creating barriers for users who prefer graphical interfaces.

## Key Findings

### 1. Configuration Pain Points

**Current State:**
- Configuration scattered across YAML files, CLI parameters, environment variables
- Advanced filtering options don't exist
- Meeting conflict handling is limited
- No web access to layout/display customization

**User Impact:**
- Visual clutter from routine meetings reduces calendar effectiveness
- Double-booking scenarios poorly handled in whats-next view
- Limited personalization options for different screen sizes/contexts

### 2. Desired Settings Categories

#### A. Advanced Event Filtering (PRIORITY 1)
**User Need:** "I want to filter out recurring personal/routine meetings that clutter the view like 'Daily Standup' or 'Lunch' and all-day events or blocked time that shouldn't show as meetings."

**Filtering Criteria:**
- Meeting title patterns/keywords
- All-day event exclusion
- Event type classification
- Recurring meeting patterns

**Business Value:** Directly improves core calendar readability and usefulness

#### B. Meeting Conflict Resolution
**User Need:** "When I'm double booked, I need to specify how that should be handled. The whats-next view only shows a single meeting currently."

**Configuration Options:**
- Prioritization by acceptance status (accepted vs tentative)
- Prioritization by attendee count
- Visual indicators for multiple overlapping meetings
- Custom priority rules

#### C. Layout & Display Customization
**User Need:** "I'd like to control the default layout and configure style settings for font sizes for different parts of the UX."

**Settings Required:**
- Default layout selection (3x4, 4x8, whats-next-view)
- Font sizing by UI component
- Display density options
- Screen-size-specific adaptations

### 3. Usage Patterns

**Change Frequency:** "Initial setup followed by occasional tweaks when workflow changes"

**Implications:**
- Interface should prioritize clarity and completeness over speed
- Users need confidence in settings without frequent testing
- Complex configurations acceptable if well-organized

### 4. Interface Requirements

**Access Method:** Kindle-style gesture interface
- Click at top of screen reveals drag indicator
- Drag down to reveal settings overlay
- Non-intrusive, discoverable interaction

**Responsive Design:** Must adapt to:
- 300w × 400h layout (compact e-ink)
- 480w × 800h layout (RPI e-ink)
- Various web browser sizes

**Cross-Layout Compatibility:** Settings panel must work consistently across all CalendarBot layout views (3x4, 4x8, whats-next-view)

## Use Cases

### UC1: Initial Calendar Setup
**Actor:** New CalendarBot user  
**Goal:** Configure filtering to show only relevant meetings  
**Flow:** User sets up filtering rules during first use to hide routine meetings and focus on important events  
**Success Criteria:** Calendar shows clean, actionable schedule without noise

### UC2: Workflow Change Adaptation  
**Actor:** Existing user with changing meeting patterns  
**Goal:** Adjust filtering rules when job role or meeting patterns change  
**Flow:** User accesses settings to modify filtering criteria and conflict resolution preferences  
**Success Criteria:** Calendar adapts to new work context without requiring CLI knowledge

### UC3: Multi-Device Optimization
**Actor:** User with multiple CalendarBot displays  
**Goal:** Optimize display settings for different screen sizes  
**Flow:** User adjusts font sizes and layout preferences for different devices (e-ink vs web)  
**Success Criteria:** Optimal readability across all devices

### UC4: Double-Booking Management
**Actor:** User with frequent scheduling conflicts  
**Goal:** Configure how conflicts are displayed and prioritized  
**Flow:** User sets rules for which meeting to show when double-booked  
**Success Criteria:** Whats-next view shows most relevant meeting or clear conflict indicator

## Priority Roadmap

### Phase 1 (Initial Release)
**Focus:** Advanced Event Filtering
- Meeting title/keyword filtering
- All-day event exclusion
- Basic UI framework with gesture access

**Rationale:** Directly addresses core value proposition (calendar clarity) with highest user impact

### Phase 2 (Follow-up)
**Focus:** Meeting Conflict Resolution
- Double-booking prioritization rules
- Visual conflict indicators
- Enhanced whats-next view logic

### Phase 3 (Enhancement)
**Focus:** Layout & Display Customization
- Default layout selection
- Font sizing controls
- Advanced display preferences

## Technical Considerations

### Integration Points
- Must integrate with existing CalendarBot configuration system
- Should extend current YAML/CLI configuration rather than replace
- Settings persistence across restarts required

### Cross-Layout Support
- Settings panel must render consistently across all layouts
- Responsive design for 300×400 and 480×800 constraints
- Touch-optimized for e-ink displays

### User Experience Requirements
- Non-intrusive access (gesture-based)
- Clear visual feedback for setting changes
- Immediate preview of filtering effects where possible

## Edge Cases & Failure Modes

### Configuration Conflicts
- User sets contradictory filtering rules
- All meetings filtered out accidentally
- Invalid regex patterns in title filters

### Technical Failures
- Settings panel fails to load/render
- Configuration changes don't persist
- Gesture recognition issues on different devices

### User Error Recovery
- Easy way to reset to defaults
- Clear indication when no meetings match filters
- Undo/rollback capabilities for recent changes

## Recommendations

1. **Start with filtering** - highest impact, clearest user need
2. **Implement gesture interface early** - core to the UX vision
3. **Design mobile-first** - e-ink constraints drive good responsive design
4. **Build configuration incrementally** - add setting categories as they're implemented
5. **Provide immediate feedback** - show filtering effects in real-time where possible

## Next Steps

This research provides foundation for:
1. User story creation and acceptance criteria definition
2. Technical architecture planning for settings persistence
3. UX design specifications for responsive overlay interface
4. Feature prioritization and sprint planning