# UX Specifications - What's Next View UX Improvement

*Practical design specifications for 300x400px greyscale display optimized for 2-3 second scanning and meeting boundary decisions.*

## Design Principles

**Core User Need**: "Can I let this conversation continue or do I need to wrap up now?"

**Design Constraints**:
- 300x400px display (portrait orientation)
- Greyscale only (no color)
- 2-3 second scanning requirement
- Used during active meeting participation (split attention)

**Priority Hierarchy**:
1. Time gap until next meeting (most prominent)
2. Next meeting context (time, title)
3. Boundary alerts and status messages
4. Additional meeting details (least prominent)

---

## Layout Structure & Visual Hierarchy

### Primary Layout (300x400px)

```
┌─────────────────────────────┐ 300px wide
│         TIME GAP            │ 
│       ████████             │ Header: 80px
│      48min until            │ (Time gap display)
│                             │
├─────────────────────────────┤
│    NEXT MEETING             │ 
│   ■■■■■■■■■■■■■■            │ Primary: 140px  
│  2:30 PM - 3:30 PM          │ (Next meeting info)
│  Team Sprint Review         │
│  with Engineering Team      │
│                             │
├─────────────────────────────┤
│      STATUS AREA            │
│     ░░░░░░░░░░░░            │ Secondary: 100px
│   Current: Product Demo     │ (Current context)
│   Running since 1:30 PM     │
│                             │
├─────────────────────────────┤
│    ADDITIONAL INFO          │
│      ▒▒▒▒▒▒▒▒▒▒            │ Footer: 80px
│  Following: All-hands       │ (Future meetings)
│      at 4:00 PM             │
└─────────────────────────────┘ 400px total height
```

### Information Hierarchy Zones

**Zone 1 - Time Gap (Critical)**: 80px height
- Largest typography (36-48px)
- Maximum contrast
- Top placement for immediate visibility

**Zone 2 - Next Meeting (Primary)**: 140px height  
- Large typography (24-32px) for title
- Medium typography (18-20px) for details
- High contrast, clear grouping

**Zone 3 - Current Status (Secondary)**: 100px height
- Medium typography (16-18px)
- Moderate contrast
- Context without overwhelming

**Zone 4 - Additional Info (Tertiary)**: 80px height
- Small typography (14-16px) 
- Lower contrast
- Minimal space usage

---

## Typography Scale & Weights

### Greyscale-Optimized Font Hierarchy

**Level 1 - Critical Time Gap**:
- Size: 48px
- Weight: 900 (Black)
- Line Height: 1.2
- Usage: Time gap numbers and "min until"
- Contrast: White on Black background (#000/#FFF)

**Level 2 - Primary Meeting Info**:
- Size: 32px  
- Weight: 700 (Bold)
- Line Height: 1.3
- Usage: Next meeting time
- Contrast: Black on White (#000/#FFF)

**Level 3 - Secondary Meeting Info**:
- Size: 24px
- Weight: 600 (Semi-Bold) 
- Line Height: 1.4
- Usage: Meeting titles
- Contrast: Dark Grey on White (#333/#FFF)

**Level 4 - Supporting Text**:
- Size: 18px
- Weight: 400 (Regular)
- Line Height: 1.5  
- Usage: Attendee info, locations
- Contrast: Medium Grey on White (#666/#FFF)

**Level 5 - Minimal Text**:
- Size: 14px
- Weight: 400 (Regular)
- Line Height: 1.4
- Usage: Additional context
- Contrast: Light Grey on White (#999/#FFF)

### Font Selection
- **Primary**: System font stack for reliability
- **Fallback**: `"SF Pro Display", "Segoe UI", "Roboto", "Arial", sans-serif`
- **Optimization**: Fonts selected for greyscale clarity and small display rendering

---

## Screen States & Wireframes

### State 1: Comfortable Gap (>15 minutes)

```
┌─────────────────────────────┐
│        48min until          │ 48px white on black
│         NEXT MEETING        │ 
├─────────────────────────────┤
│       2:30 PM - 3:30 PM     │ 32px bold black
│     Team Sprint Review      │ 24px semi-bold  
│   with Engineering Team     │ 18px regular
│                             │
├─────────────────────────────┤
│   Current: Product Demo     │ 18px regular grey
│   Running since 1:30 PM     │ 14px regular
│                             │
├─────────────────────────────┤
│  Following: All-hands       │ 14px light grey
│      at 4:00 PM             │
└─────────────────────────────┘
```

### State 2: Tight Gap (5-15 minutes)

```
┌─────────────────────────────┐
│        8min until           │ 48px white on dark grey
│      ⚠ NEXT MEETING ⚠      │ Warning indicators
├─────────────────────────────┤
│       2:30 PM - 3:30 PM     │ 32px bold black
│     Team Sprint Review      │ 24px semi-bold
│   with Engineering Team     │ 18px regular
│                             │
├─────────────────────────────┤
│   Current: Product Demo     │ 18px regular grey
│   Consider wrapping up      │ 16px italic advice
│                             │
├─────────────────────────────┤
│     [Future meetings        │ 14px compressed
│      minimized]             │
└─────────────────────────────┘
```

### State 3: Critical Gap (<5 minutes)

```
┌─────────────────────────────┐
│       2min until            │ 48px white on black
│     🚨 WRAP UP NOW 🚨       │ Urgent messaging
├─────────────────────────────┤
│       2:30 PM - 3:30 PM     │ 32px bold black
│     Team Sprint Review      │ 24px semi-bold
│                             │
│     ⏰ STARTING SOON        │ 20px urgent indicator
│                             │
├─────────────────────────────┤
│   Current: Product Demo     │ 18px regular grey
│   End immediately           │ 16px bold advice
│                             │
├─────────────────────────────┤
│     [All other info         │ Minimal space
│      hidden for focus]      │
└─────────────────────────────┘
```

### State 4: No Next Meeting

```
┌─────────────────────────────┐
│    No more meetings         │ 36px regular
│        today                │ 
├─────────────────────────────┤
│   ✅ Schedule is clear      │ 24px with checkmark
│   after this meeting       │ 18px regular
│                             │
│   Take your time            │ 18px encouraging
│                             │
├─────────────────────────────┤
│   Current: Product Demo     │ 18px regular grey
│   Running since 1:30 PM     │ 14px regular
│                             │
├─────────────────────────────┤
│  Tomorrow: Daily Standup    │ 14px light grey
│      at 9:00 AM             │
└─────────────────────────────┘
```

---

## Spacing & Positioning Specifications

### Layout Grid (300x400px)

**Margins**:
- Left/Right: 16px
- Top/Bottom: 12px
- Content Width: 268px (300 - 32px margins)

**Vertical Spacing**:
- Zone separation: 8px borders
- Internal padding: 12px per zone
- Line spacing: 4px between related lines
- Section spacing: 8px between unrelated content

**Horizontal Spacing**:
- Text alignment: Left-aligned for scanning
- Time alignment: Right-aligned in time zone
- Icon spacing: 8px from text
- Bullet spacing: 12px indent

**Touch Targets** (if interactive):
- Minimum: 44x44px
- Preferred: 48x48px
- Spacing between targets: 8px minimum

---

## Component Specifications

### TimeGapDisplay Component

**Props**:
- `gapMinutes`: number
- `gapType`: 'comfortable' | 'tight' | 'critical' | 'none'
- `nextMeetingTitle`: string
- `nextMeetingTime`: string

**States**:
- Default: Normal display
- Warning: Tight gap styling  
- Critical: Urgent gap styling
- Empty: No next meeting

**Behavior**:
- Auto-updates every 15 seconds
- Transitions between states smoothly
- Shows countdown when <10 minutes

### MeetingInfo Component

**Props**:
- `title`: string
- `startTime`: string
- `endTime`: string
- `attendeeCount`: number
- `location`: string (optional)

**States**:
- Primary: Next meeting display
- Secondary: Current meeting display
- Minimized: Reduced detail view

**Text Overflow**:
- Title: Truncate at 2 lines with ellipsis
- Attendees: Show count instead of names if >3
- Location: Truncate at 1 line

### StatusMessage Component

**Props**:
- `message`: string
- `type`: 'info' | 'warning' | 'critical'
- `showTime`: boolean

**States**:
- Info: Standard grey text
- Warning: Emphasized text
- Critical: High contrast urgent text

---

## Interactive Behavior

### Auto-Refresh Logic
- Data refresh: Every 30 seconds
- Display update: Every 15 seconds
- Critical updates: Every 5 seconds when gap <10min

### State Transitions
- Smooth fade between gap states
- Progressive information hiding as urgency increases
- Emphasis changes without jarring movement

### Error States
- Network error: Show last known good data with timestamp
- Calendar sync error: Clear error message
- No data: Helpful empty state message

---

## Design Tokens

### Colors (Greyscale Values)

```css
:root {
  /* Critical/Primary */
  --color-critical-bg: #000000;      /* Pure black */
  --color-critical-text: #FFFFFF;    /* Pure white */
  
  /* Primary Content */
  --color-primary-text: #000000;     /* Black text */
  --color-primary-bg: #FFFFFF;       /* White background */
  
  /* Secondary Content */
  --color-secondary-text: #333333;   /* Dark grey */
  --color-secondary-bg: #F5F5F5;     /* Light grey bg */
  
  /* Supporting Content */
  --color-supporting-text: #666666;  /* Medium grey */
  --color-muted-text: #999999;       /* Light grey */
  
  /* Borders & Separators */
  --color-border: #E0E0E0;           /* Very light grey */
  --color-separator: #CCCCCC;        /* Light grey */
}
```

### Typography Tokens

```css
:root {
  /* Font Sizes */
  --font-size-critical: 48px;
  --font-size-primary: 32px;
  --font-size-secondary: 24px;
  --font-size-body: 18px;
  --font-size-small: 14px;
  
  /* Font Weights */
  --font-weight-black: 900;
  --font-weight-bold: 700;
  --font-weight-semi: 600;
  --font-weight-regular: 400;
  
  /* Line Heights */
  --line-height-tight: 1.2;
  --line-height-normal: 1.4;
  --line-height-relaxed: 1.5;
}
```

### Spacing Tokens

```css
:root {
  /* Layout Spacing */
  --space-page-margin: 16px;
  --space-zone-padding: 12px;
  --space-zone-separator: 8px;
  
  /* Content Spacing */
  --space-line-gap: 4px;
  --space-section-gap: 8px;
  --space-icon-gap: 8px;
  
  /* Component Spacing */
  --space-touch-target: 44px;
  --space-min-tap: 8px;
}
```

---

## UX Handoff Package

### Component Inventory

**1. TimeGapDisplay**
- Purpose: Primary time gap visualization
- Props: gapMinutes, gapType, nextMeetingTitle, nextMeetingTime
- States: comfortable, tight, critical, none
- Behavior: Auto-updating countdown, state-based styling

**2. MeetingInfoCard**
- Purpose: Meeting details display
- Props: title, startTime, endTime, attendeeCount, location
- States: primary, secondary, minimized
- Behavior: Text truncation, responsive detail levels

**3. StatusMessage**
- Purpose: Contextual status and advice
- Props: message, type, showTime
- States: info, warning, critical
- Behavior: Type-based styling, conditional display

**4. LayoutContainer**
- Purpose: Main layout structure
- Props: zones configuration
- States: normal, urgent (critical mode)
- Behavior: Zone height management, responsive spacing

### CSS Implementation Classes

```css
/* Layout Classes */
.whats-next-container { /* 300x400 container */ }
.zone-time-gap { /* Zone 1: 80px height */ }
.zone-next-meeting { /* Zone 2: 140px height */ }
.zone-current-status { /* Zone 3: 100px height */ }
.zone-additional { /* Zone 4: 80px height */ }

/* Typography Classes */
.text-critical { /* 48px, weight 900 */ }
.text-primary { /* 32px, weight 700 */ }
.text-secondary { /* 24px, weight 600 */ }
.text-body { /* 18px, weight 400 */ }
.text-small { /* 14px, weight 400 */ }

/* State Classes */
.gap-comfortable { /* Normal styling */ }
.gap-tight { /* Warning styling */ }
.gap-critical { /* Urgent styling */ }
.gap-none { /* Clear schedule styling */ }
```

### Interaction Patterns

**Time Gap State Changes**:
```
comfortable -> tight: Emphasize gap, add warning indicators
tight -> critical: High contrast, show urgent messaging, hide non-essential info
critical -> comfortable: Fade back to normal, restore full information
```

**Data Updates**:
```
on refresh: Smooth transition of time values, maintain visual stability
on error: Show last good data with "Updated X minutes ago"
on empty: Clear messaging about schedule status
```

### Implementation Notes

**Performance**:
- Optimize for 300x400px rendering
- Minimize reflows during updates
- Use CSS transforms for smooth transitions

**Responsiveness**:
- Fixed 300x400 layout (no scaling)
- Maintain proportional spacing
- Ensure touch targets if interactive

**Browser Support**:
- Support basic greyscale displays
- Fallback fonts for embedded systems
- Progressive enhancement for features

---

## Success Metrics

**Primary Goal**: Enable meeting boundary decisions in <3 seconds

**Measurable Outcomes**:
- Time to identify next meeting gap: <2 seconds
- Accuracy of gap time reading: 100% at glance
- User confidence in wrap-up decisions: High
- Cognitive load during active meetings: Minimal

**Implementation Validation**:
- Contrast ratios meet 7:1 minimum for greyscale
- Typography renders clearly at 300px width
- Information hierarchy tested with rapid scanning
- State transitions tested across all gap scenarios

---

*UX Specifications completed: July 15, 2025*  
*Optimized for 300x400px greyscale display and 2-3 second scanning requirement*