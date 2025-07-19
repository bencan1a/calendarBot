# CalendarBot Settings Panel - UX Specifications

## Executive Summary

This document defines the complete user experience design for CalendarBot's web-based settings panel, implementing a Kindle-style gesture interface optimized for e-ink displays and responsive web environments. The design prioritizes accessibility, visual clarity, and efficient configuration workflows.

## Design Foundations

### Visual System Analysis

Based on existing CalendarBot layouts, the design system follows these principles:

**Color System:**
- **Standard Theme**: Modern web aesthetic with grayscale palette and subtle shadows
- **E-ink Theme**: High contrast black/white with monospace typography
- **Accessibility**: WCAG 2.2 AA compliance with minimum 4.5:1 contrast ratios

**Typography Scale:**
- **System Fonts**: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
- **E-ink Override**: 'DejaVu Sans Mono', 'Courier New', monospace
- **Scale**: 48px (critical), 32px (primary), 24px (secondary), 18px (supporting), 14px (caption)

**Layout Constraints:**
- **Primary**: 300×400px (3x4 layout) 
- **Secondary**: 480×800px (4x8 layout)
- **Responsive**: Scales for web browsers with consistent gesture zones

## Interaction Design

### Gesture-Based Access Pattern

#### Activation Zone
```
┌─────────────────────────────────┐
│    ← GESTURE ACTIVATION →       │ ← Top 50px
├─────────────────────────────────┤
│                                 │
│        Calendar Content         │
│                                 │
│                                 │
│                                 │
└─────────────────────────────────┘
```

**Gesture Sequence:**
1. **Click Detection**: User clicks anywhere in top 50px zone
2. **Visual Feedback**: Drag indicator appears (subtle downward arrow)
3. **Drag Threshold**: 20px vertical movement required
4. **Panel Reveal**: Settings overlay slides down with finger/mouse tracking
5. **Dismissal**: Drag up or click outside to hide

#### State Transitions

```
[Normal View] 
     ↓ (click top 50px)
[Drag Indicator Visible]
     ↓ (drag down 20px+)
[Settings Panel Sliding]
     ↓ (animation complete)
[Settings Panel Open]
     ↓ (drag up OR click outside)
[Settings Panel Closing]
     ↓ (animation complete)
[Normal View]
```

## Layout Design

### 300×400px Layout (Primary E-ink Target)

```
┌─────────────────────────┐  300px
│  ⚙️ Settings            │ ← Header (40px)
├─────────────────────────┤
│ ┌─ FILTER SETTINGS ──┐  │
│ │ □ All-day events    │  │
│ │ ⚡ Title patterns   │  │ ← Primary Section (180px)
│ │ + Daily Standup     │  │
│ │ + Lunch            │  │
│ └────────────────────┘  │
├─────────────────────────┤
│ ┌─ LAYOUT ───────────┐  │
│ │ ○ 3x4  ● 4x8       │  │ ← Secondary Section (100px)
│ │ Font: M            │  │
│ └────────────────────┘  │
├─────────────────────────┤
│ [Apply] [Reset]        │ ← Actions (30px)
├─────────────────────────┤
│ 📊 2 filters active    │ ← Status (30px)
└─────────────────────────┘
      400px
```

### 480×800px Layout (Secondary E-ink Target)

```
┌───────────────────────────────────┐  480px
│  ⚙️ Settings                      │ ← Header (50px)
├───────────────────────────────────┤
│ ┌─ ADVANCED EVENT FILTERING ────┐ │
│ │                               │ │
│ │ All-day Events                │ │
│ │ □ Hide all-day events         │ │
│ │                               │ │
│ │ Title Pattern Filters         │ │ ← Primary Section (400px)
│ │ ⚡ Daily Standup              │ │
│ │ ⚡ Lunch                      │ │
│ │ ⚡ Break                      │ │
│ │ [+ Add Pattern]               │ │
│ │                               │ │
│ │ Event Type Classification     │ │
│ │ □ 1:1 meetings               │ │
│ │ □ Social events              │ │
│ └───────────────────────────────┘ │
├───────────────────────────────────┤
│ ┌─ LAYOUT & DISPLAY ────────────┐ │
│ │                               │ │
│ │ Default Layout                │ │ ← Secondary Section (200px)
│ │ ○ 3x4  ● 4x8  ○ whats-next   │ │
│ │                               │ │
│ │ Typography                    │ │
│ │ Headers: [M ▼]  Body: [M ▼]  │ │
│ │                               │ │
│ │ Display Density               │ │
│ │ ○ Compact ● Normal ○ Spacious │ │
│ └───────────────────────────────┘ │
├───────────────────────────────────┤
│ [Apply Changes] [Reset to Defaults] │ ← Actions (50px)
├───────────────────────────────────┤
│ 📊 3 filters active • Last saved: 2m │ ← Status (40px)
└───────────────────────────────────┘
        800px
```

## Information Architecture

### Settings Organization Hierarchy

```
Settings Panel
├── Event Filtering (Priority 1)
│   ├── All-day Event Toggle
│   ├── Title Pattern Filters
│   │   ├── Quick Add Buttons
│   │   ├── Custom Pattern Input
│   │   └── Pattern List Management
│   ├── Event Type Classification
│   └── Recurring Meeting Controls
├── Layout & Display (Priority 2)
│   ├── Default Layout Selection
│   ├── Typography Controls
│   └── Display Density Options
├── Meeting Conflicts (Priority 3)
│   ├── Prioritization Rules
│   └── Visual Indicators
└── System Actions
    ├── Apply Changes
    ├── Reset to Defaults
    └── Export/Import Settings
```

### Content Priority by Screen Size

**300×400px (Essential Only):**
- All-day event toggle
- Top 3 title pattern filters
- Layout selection (3x4/4x8)
- Apply/Reset actions

**480×800px (Full Feature Set):**
- Complete event filtering suite
- Full layout customization
- Typography and density controls
- Advanced management features

## Component Specifications

### Settings Panel Container

**300×400px:**
```css
.settings-panel {
  position: fixed;
  top: 0;
  left: 0;
  width: 300px;
  height: 400px;
  background: var(--background-primary);
  border: 2px solid var(--border-strong);
  z-index: 200;
  overflow-y: auto;
  transform: translateY(-100%);
  transition: transform 0.3s ease;
}

.settings-panel.open {
  transform: translateY(0);
}
```

**480×800px:**
```css
.settings-panel {
  width: 480px;
  height: 800px;
  /* Other properties same as 300×400px */
}
```

### Drag Indicator

```css
.drag-indicator {
  position: absolute;
  top: 50px;
  left: 50%;
  transform: translateX(-50%);
  width: 60px;
  height: 4px;
  background: var(--border-medium);
  border-radius: 2px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.drag-indicator.visible {
  opacity: 0.6;
}
```

### Filter Toggle Component

```
┌─────────────────────────────┐
│ □ All-day events            │ ← 44px min height
│   Hide calendar blocks and  │
│   vacation days             │
└─────────────────────────────┘
```

**Specifications:**
- **Touch Target**: 44×44px minimum (WCAG compliance)
- **Typography**: 18px supporting text, 14px caption description
- **States**: default, hover, active, disabled
- **Animation**: Checkbox fade transition 0.2s

### Pattern Filter Item

```
┌─────────────────────────────┐
│ ⚡ Daily Standup        [×] │ ← 44px min height
│   3 events hidden          │
└─────────────────────────────┘
```

**Specifications:**
- **Icon**: ⚡ for active patterns, ○ for inactive
- **Remove Button**: 24×24px touch target in top-right
- **Count Display**: Shows filtered events in caption text
- **States**: active, inactive, hover, removing

### Quick Add Buttons

```
┌─── Common Patterns ─────────┐
│ [+ Daily Standup] [+ Lunch] │ ← 32px height
│ [+ Break] [+ Review]        │
│ [+ Custom Pattern...]       │
└─────────────────────────────┘
```

**Specifications:**
- **Button Height**: 32px for dense layout
- **Spacing**: 8px gap between buttons
- **Custom Input**: Expands to full-width text field
- **Validation**: Real-time regex pattern checking

### Layout Selection

```
┌─── Default Layout ──────────┐
│ ○ 3x4    ● 4x8    ○ whats-next │ ← Radio group
│ [Preview thumbnails if space]  │
└─────────────────────────────┘
```

**Specifications:**
- **Radio Buttons**: 20×20px with 24×24px touch target
- **Labels**: 14px caption text
- **Preview**: 40×64px thumbnails on 480×800px layout

## Visual Design System

### Design Tokens

#### Colors (Extended from existing system)
```css
:root {
  /* Existing CalendarBot tokens */
  --gray-1: #ffffff;
  --gray-2: #f5f5f5;
  --gray-3: #e0e0e0;
  --gray-4: #bdbdbd;
  --gray-5: #757575;
  --gray-6: #424242;
  --gray-7: #212121;
  --gray-8: #000000;
  
  /* Settings panel specific tokens */
  --settings-overlay: rgba(0, 0, 0, 0.1);
  --settings-success: #28a745;
  --settings-warning: #ffc107;
  --settings-error: #dc3545;
  --settings-info: #17a2b8;
}
```

#### Typography Scale
```css
.text-critical {
  font-size: 48px;
  font-weight: 900;
  line-height: 1.0;
}

.text-primary {
  font-size: 32px;
  font-weight: 700;
  line-height: 1.2;
}

.text-secondary {
  font-size: 24px;
  font-weight: 600;
  line-height: 1.3;
}

.text-supporting {
  font-size: 18px;
  font-weight: 400;
  line-height: 1.4;
}

.text-caption {
  font-size: 14px;
  font-weight: 400;
  line-height: 1.4;
}
```

#### Spacing Scale
```css
--space-xs: 4px;   /* Internal component spacing */
--space-sm: 8px;   /* Related element spacing */
--space-md: 16px;  /* Section spacing */
--space-lg: 24px;  /* Major section spacing */
--space-xl: 32px;  /* Panel-level spacing */
```

## State Management

### Panel States

#### Closed State
- **Visual**: Panel hidden above viewport
- **Gesture Zone**: Active (top 50px)
- **Performance**: Minimal DOM impact
- **Accessibility**: Settings panel excluded from tab order

#### Opening State
- **Visual**: Panel sliding down with drag tracking
- **Gesture Zone**: Active throughout animation
- **Performance**: Hardware-accelerated transform
- **Accessibility**: Announce "Settings panel opening"

#### Open State
- **Visual**: Panel fully visible
- **Gesture Zone**: Dismissal gestures active
- **Performance**: Full component rendering
- **Accessibility**: Focus trapped within panel

#### Closing State
- **Visual**: Panel sliding up
- **Gesture Zone**: Disabled during animation
- **Performance**: Hardware-accelerated transform
- **Accessibility**: Focus returned to trigger element

### Form States

#### Default State
- **Visual**: Clean, scannable layout
- **Interaction**: All controls enabled
- **Data**: Current settings displayed
- **Validation**: No errors present

#### Modified State
- **Visual**: Apply button highlighted
- **Interaction**: Unsaved changes warning
- **Data**: Local state differs from saved
- **Validation**: Real-time validation active

#### Saving State
- **Visual**: Loading indicators on form
- **Interaction**: Controls disabled during save
- **Data**: Optimistic UI updates
- **Validation**: Final server-side validation

#### Error State
- **Visual**: Error messages and field highlighting
- **Interaction**: Focus directed to first error
- **Data**: Local state preserved
- **Validation**: Specific error guidance provided

## Accessibility Implementation

### WCAG 2.2 AA Compliance

#### Keyboard Navigation
```
Tab Order:
1. Close Button (×)
2. Filter Section Toggle
3. All-day Events Checkbox
4. Pattern Filter List (arrow keys within)
5. Add Pattern Button
6. Layout Radio Group (arrow keys within)
7. Typography Controls
8. Apply Button
9. Reset Button
```

#### Screen Reader Support
```html
<div role="dialog" 
     aria-labelledby="settings-title"
     aria-describedby="settings-description"
     aria-modal="true">
  
  <h2 id="settings-title">Calendar Settings</h2>
  <p id="settings-description">
    Configure event filtering and display preferences
  </p>
  
  <section aria-labelledby="filtering-title">
    <h3 id="filtering-title">Event Filtering</h3>
    <!-- Filter controls -->
  </section>
</div>
```

#### Touch Target Requirements
- **Minimum Size**: 44×44px for all interactive elements
- **Spacing**: 8px minimum between adjacent targets
- **Visual**: Clear boundaries and hover states
- **Feedback**: Immediate visual and haptic responses

#### Color Contrast
- **Text on Background**: 21:1 (gray-8 on gray-1)
- **Interactive Elements**: 7:1 minimum (gray-6 on gray-1)
- **Disabled State**: 3:1 minimum (gray-5 on gray-1)
- **Focus Indicators**: 3:1 minimum contrast with background

### E-ink Optimizations

#### High Contrast Mode
```css
.theme-eink .settings-panel {
  background: #ffffff;
  border: 3px solid #000000;
  box-shadow: none;
}

.theme-eink .settings-toggle {
  border: 2px solid #000000;
  background: #ffffff;
}

.theme-eink .settings-toggle:checked {
  background: #000000;
  color: #ffffff;
}
```

#### Motion Reduction
```css
.theme-eink .settings-panel {
  transition: none;
  animation: none;
}

@media (prefers-reduced-motion: reduce) {
  .settings-panel {
    transition: none;
  }
}
```

## Interaction Patterns

### Form Behavior

#### Inline Validation
```javascript
// Pattern validation example
onPatternInput(value) {
  if (value.length === 0) {
    showStatus('neutral', 'Enter a meeting title pattern');
  } else if (isValidRegex(value)) {
    showStatus('success', `Will filter ${getMatchCount(value)} events`);
  } else {
    showStatus('error', 'Invalid pattern format');
  }
}
```

#### Auto-save Behavior
- **Trigger**: 2-second delay after last interaction
- **Visual**: Subtle "Saving..." indicator
- **Error Handling**: Retry with exponential backoff
- **Rollback**: Restore previous state on failure

#### Bulk Operations
- **Select All**: Checkbox in section headers
- **Clear Filters**: Single action to reset filtering
- **Import/Export**: JSON format for settings backup

### Error Recovery

#### Validation Errors
```
┌─────────────────────────────┐
│ ⚠️ Invalid Pattern          │
│ "Meeting[" is not valid     │
│ regex. Try "Meeting*"       │
│ [Fix Pattern] [Remove]      │
└─────────────────────────────┘
```

#### Network Errors
```
┌─────────────────────────────┐
│ 🔄 Connection Failed        │
│ Your changes are saved      │
│ locally. Will retry when    │
│ connection returns.         │
│ [Try Again] [Work Offline]  │
└─────────────────────────────┘
```

#### Data Conflicts
```
┌─────────────────────────────┐
│ ⚠️ Settings Changed         │
│ Another device updated      │
│ your settings. Keep yours   │
│ or use the latest version?  │
│ [Keep Mine] [Use Latest]    │
└─────────────────────────────┘
```

## UX Handoff Documentation

### Component Inventory

#### SettingsPanel
**Props:**
- `isOpen: boolean` - Panel visibility state
- `onClose: () => void` - Close handler
- `initialSettings: SettingsData` - Current configuration

**States:**
- `closed` - Hidden above viewport
- `opening` - Sliding down animation
- `open` - Fully visible and interactive
- `closing` - Sliding up animation

#### FilterToggle
**Props:**
- `id: string` - Unique identifier
- `label: string` - Toggle label text
- `description?: string` - Optional description
- `checked: boolean` - Toggle state
- `onChange: (checked: boolean) => void` - Change handler

**States:**
- `default` - Normal appearance
- `hover` - Mouse over state
- `focus` - Keyboard focus
- `disabled` - Non-interactive state

#### PatternFilter
**Props:**
- `pattern: string` - Filter pattern
- `matchCount: number` - Events affected
- `isActive: boolean` - Filter enabled state
- `onToggle: () => void` - Enable/disable handler
- `onRemove: () => void` - Delete handler

**States:**
- `active` - Filter enabled (⚡ icon)
- `inactive` - Filter disabled (○ icon)
- `removing` - Deletion in progress

#### QuickAddButton
**Props:**
- `label: string` - Button text
- `pattern: string` - Pattern to add
- `onAdd: (pattern: string) => void` - Add handler

**States:**
- `default` - Available to add
- `adding` - Creation in progress
- `disabled` - Pattern already exists

### Style Token Table

| Token | Value | Usage |
|-------|--------|--------|
| `--settings-panel-width-sm` | `300px` | Small display width |
| `--settings-panel-width-lg` | `480px` | Large display width |
| `--settings-panel-height-sm` | `400px` | Small display height |
| `--settings-panel-height-lg` | `800px` | Large display height |
| `--gesture-zone-height` | `50px` | Top activation area |
| `--drag-threshold` | `20px` | Minimum drag distance |
| `--touch-target-min` | `44px` | Minimum touch size |
| `--animation-duration` | `300ms` | Panel open/close timing |
| `--animation-easing` | `ease` | Panel movement curve |

### Interaction Snippets

#### Gesture Recognition
```javascript
// Top zone click detection
onTopZoneClick(event) {
  if (event.clientY <= GESTURE_ZONE_HEIGHT) {
    showDragIndicator();
    startDragListening();
  }
}

// Drag threshold validation
onDragMove(event) {
  const dragDistance = event.clientY - startY;
  if (dragDistance >= DRAG_THRESHOLD) {
    openSettingsPanel();
  }
}
```

#### Form Validation
```javascript
// Pattern validation with preview
validatePattern(pattern) {
  try {
    new RegExp(pattern);
    const matchCount = countMatches(pattern);
    return {
      isValid: true,
      message: `Will filter ${matchCount} events`,
      type: 'success'
    };
  } catch (error) {
    return {
      isValid: false,
      message: 'Invalid pattern format',
      type: 'error'
    };
  }
}
```

#### Auto-save Mechanism
```javascript
// Debounced save with optimistic updates
const autoSave = debounce(async (settings) => {
  try {
    setStatus('saving');
    await saveSettings(settings);
    setStatus('saved');
  } catch (error) {
    setStatus('error');
    revertToLastSaved();
  }
}, 2000);
```

#### Error Recovery
```javascript
// Retry with exponential backoff
const retryWithBackoff = async (operation, maxRetries = 3) => {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      if (attempt === maxRetries) throw error;
      await delay(Math.pow(2, attempt) * 1000);
    }
  }
};
```

## Implementation Notes

### Technical Requirements

#### Browser Support
- **Chrome 90+**: Full feature support
- **Firefox 88+**: Full feature support  
- **Safari 14+**: Full feature support
- **Touch Events**: Required for gesture interface
- **CSS Grid**: Required for responsive layouts

#### Performance Targets
- **Panel Open Time**: <200ms
- **Form Response Time**: <100ms immediate, <500ms validation
- **Memory Usage**: <5MB additional footprint
- **Bundle Size**: <50KB compressed JavaScript + CSS

#### Integration Points
- **Settings API**: RESTful endpoints for CRUD operations
- **WebSocket**: Real-time settings sync across devices
- **Local Storage**: Offline capability and optimistic updates
- **Analytics**: User interaction tracking for UX improvements

### Development Phases

#### Phase 1: Foundation (Sprint 1-2)
- Basic gesture recognition system
- Panel container and animation
- Core toggle and button components
- 300×400px layout implementation

#### Phase 2: Core Features (Sprint 3-4)
- Event filtering components
- Pattern management system
- Layout selection interface
- Auto-save functionality

#### Phase 3: Polish (Sprint 5-6)
- 480×800px layout optimization
- Error handling and recovery
- Accessibility enhancements
- Performance optimizations

### Success Metrics

#### Usability Metrics
- **Discovery Rate**: 90% of users find gesture interface within 30 seconds
- **Configuration Success**: 85% complete initial setup without assistance
- **Error Recovery**: 95% recover from validation errors within 60 seconds

#### Performance Metrics
- **Gesture Response**: 95% of gestures recognized within 100ms
- **Panel Animation**: 60fps during open/close transitions
- **Form Validation**: Real-time feedback within 200ms

#### Accessibility Metrics
- **Keyboard Navigation**: 100% functionality accessible via keyboard
- **Screen Reader**: Compatible with NVDA, JAWS, VoiceOver
- **Touch Targets**: 100% compliance with 44px minimum size

This comprehensive UX specification provides implementation-ready designs that align with CalendarBot's existing visual system while introducing powerful configuration capabilities through an intuitive gesture-based interface optimized for e-ink displays and responsive web environments.