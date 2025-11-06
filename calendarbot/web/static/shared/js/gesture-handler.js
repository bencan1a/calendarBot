/**
 * CalendarBot Gesture Handler
 *
 * Implements Kindle-style gesture interface for settings panel access.
 * Handles top-zone detection, drag tracking, and panel reveal/dismiss gestures.
 */

class GestureHandler {
    constructor(settingsPanel) {
        this.settingsPanel = settingsPanel;
        this.gestureZoneHeight = 50; // pixels
        this.dragThreshold = 20; // pixels
        this.isListening = false;
        this.isDragging = false;
        this.startY = 0;
        this.currentY = 0;
        this.dragIndicator = null;

        // Touch/mouse state tracking
        this.touchStartTime = 0;
        this.lastTouchEnd = 0;

        // Gesture state
        this.gestureActive = false;
        this.panelTransitioning = false;

        if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Initialized with gesture zone height:', this.gestureZoneHeight);
    }

    /**
     * Initialize gesture recognition system
     * Sets up event listeners and creates gesture zone
     */
    initialize() {
        this.createGestureZone();
        this.createDragIndicator();
        this.setupEventListeners();
        if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Gesture recognition system initialized');
    }

    /**
     * Create invisible gesture zone at top of content area
     */
    createGestureZone() {
        // Remove existing gesture zone if it exists
        const existingZone = document.getElementById('settings-gesture-zone');
        if (existingZone) {
            existingZone.remove();
        }

        const gestureZone = document.createElement('div');
        gestureZone.id = 'settings-gesture-zone';
        gestureZone.className = 'settings-gesture-zone';

        // CRITICAL FIX: Position relative to content area, not viewport
        const contentContainer = document.querySelector('.calendar-content');
        let topPosition = '0px';
        let leftPosition = '0px';
        let zoneWidth = '100%';

        if (contentContainer) {
            const rect = contentContainer.getBoundingClientRect();
            topPosition = `${rect.top}px`;
            leftPosition = `${rect.left}px`;
            zoneWidth = `${rect.width}px`;
            if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Positioning gesture zone over content area:', {
                top: topPosition,
                left: leftPosition,
                width: zoneWidth
            });
        } else {
            console.warn('GestureHandler: Content container not found, using viewport positioning');
        }

        gestureZone.style.cssText = `
            position: fixed;
            top: ${topPosition};
            left: ${leftPosition};
            width: ${zoneWidth};
            height: ${this.gestureZoneHeight}px;
            z-index: 100;
            background: transparent;
            cursor: pointer;
            touch-action: none;
            user-select: none;
        `;

        document.body.appendChild(gestureZone);
        if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Content-aware gesture zone created');
    }

    /**
     * Create drag indicator element
     */
    createDragIndicator() {
        if (this.dragIndicator) {
            this.dragIndicator.remove();
        }

        this.dragIndicator = document.createElement('div');
        this.dragIndicator.id = 'settings-drag-indicator';
        this.dragIndicator.className = 'settings-drag-indicator';

        // CRITICAL FIX: Position relative to content area, not viewport
        const contentContainer = document.querySelector('.calendar-content');
        let topPosition = `${this.gestureZoneHeight}px`;
        let leftPosition = '50%';

        if (contentContainer) {
            const rect = contentContainer.getBoundingClientRect();
            topPosition = `${rect.top + this.gestureZoneHeight}px`;
            leftPosition = `${rect.left + (rect.width / 2)}px`;
            if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Positioning drag indicator relative to content area:', {
                top: topPosition,
                left: leftPosition
            });
        } else {
            console.warn('GestureHandler: Content container not found for drag indicator, using viewport positioning');
        }

        this.dragIndicator.style.cssText = `
            position: fixed;
            top: ${topPosition};
            left: ${leftPosition};
            transform: translateX(-50%);
            width: 60px;
            height: 4px;
            background: var(--border-medium, #bdbdbd);
            border-radius: 2px;
            opacity: 0;
            transition: opacity 0.2s ease;
            z-index: 150;
            pointer-events: none;
        `;

        // Add downward arrow indicator
        const arrow = document.createElement('div');
        arrow.style.cssText = `
            position: absolute;
            top: 8px;
            left: 50%;
            transform: translateX(-50%);
            width: 0;
            height: 0;
            border-left: 6px solid transparent;
            border-right: 6px solid transparent;
            border-top: 8px solid var(--border-medium, #bdbdbd);
            opacity: 0.8;
        `;
        this.dragIndicator.appendChild(arrow);

        document.body.appendChild(this.dragIndicator);
        if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Content-aware drag indicator created');
    }

    /**
     * Setup event listeners for gesture recognition
     */
    setupEventListeners() {
        const gestureZone = document.getElementById('settings-gesture-zone');
        if (!gestureZone) {
            console.error('GestureHandler: Gesture zone not found during event setup');
            return;
        }

        // Mouse events
        gestureZone.addEventListener('mousedown', this.onPointerStart.bind(this));
        document.addEventListener('mousemove', this.onPointerMove.bind(this));
        document.addEventListener('mouseup', this.onPointerEnd.bind(this));

        // Touch events
        gestureZone.addEventListener('touchstart', this.onPointerStart.bind(this), { passive: false });
        document.addEventListener('touchmove', this.onPointerMove.bind(this), { passive: false });
        document.addEventListener('touchend', this.onPointerEnd.bind(this), { passive: false });

        // Click outside to dismiss
        document.addEventListener('click', this.onDocumentClick.bind(this));

        // Keyboard escape to dismiss
        document.addEventListener('keydown', this.onKeyDown.bind(this));

        // Prevent context menu in gesture zone
        gestureZone.addEventListener('contextmenu', (e) => e.preventDefault());

        if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Event listeners attached');
    }

    /**
     * Handle pointer start (mouse down or touch start)
     * @param {Event} event - Pointer event
     */
    onPointerStart(event) {
        // Prevent default behavior
        event.preventDefault();

        // Don't start new gesture if panel is transitioning
        if (this.panelTransitioning) {
            return;
        }

        // CRITICAL FIX: Check if click/touch is within the content-relative gesture zone
        const clientY = event.clientY || (event.touches && event.touches[0].clientY);

        // Get current gesture zone position for accurate coordinate checking
        const gestureZone = document.getElementById('settings-gesture-zone');
        if (gestureZone) {
            const zoneRect = gestureZone.getBoundingClientRect();
            const withinGestureZone = clientY >= zoneRect.top && clientY <= zoneRect.bottom;

            if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Touch at Y:', clientY, 'Zone:', zoneRect.top, '-', zoneRect.bottom, 'Within zone:', withinGestureZone);

            if (!withinGestureZone) {
                return;
            }
        } else {
            // Fallback to old logic if gesture zone not found
            console.warn('GestureHandler: Gesture zone not found, using fallback coordinate check');
            if (clientY > this.gestureZoneHeight) {
                return;
            }
        }

        // If panel is already open, don't start gesture
        if (this.settingsPanel && this.settingsPanel.isOpen) {
            return;
        }

        this.startY = clientY;
        this.currentY = clientY;
        this.isDragging = false;
        this.gestureActive = true;
        this.touchStartTime = Date.now();

        // Show drag indicator immediately
        this.showDragIndicator();

        if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Gesture started at Y:', this.startY);
    }

    /**
     * Handle pointer move (mouse move or touch move)
     * @param {Event} event - Pointer event
     */
    onPointerMove(event) {
        if (!this.gestureActive) {
            return;
        }

        event.preventDefault();

        const clientY = event.clientY || (event.touches && event.touches[0].clientY);
        this.currentY = clientY;
        const dragDistance = this.currentY - this.startY;

        // Only track downward movement
        if (dragDistance < 0) {
            return;
        }

        // Check if we've crossed the drag threshold
        if (!this.isDragging && dragDistance >= this.dragThreshold) {
            this.isDragging = true;
            this.startPanelReveal();
            if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Drag threshold reached, starting panel reveal');
        }

        // Update panel position if dragging
        if (this.isDragging && this.settingsPanel) {
            this.updatePanelPosition(dragDistance);
        }
    }

    /**
     * Handle pointer end (mouse up or touch end)
     * @param {Event} event - Pointer event
     */
    onPointerEnd(event) {
        if (!this.gestureActive) {
            return;
        }

        const touchDuration = Date.now() - this.touchStartTime;
        const dragDistance = this.currentY - this.startY;

        if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Gesture ended', {
            dragDistance,
            touchDuration,
            isDragging: this.isDragging
        });

        if (this.isDragging) {
            // Hide drag indicator when dragging completes
            this.hideDragIndicator();

            // Complete or cancel panel reveal based on drag distance
            if (dragDistance >= this.dragThreshold * 2) {
                this.completePanelReveal();
            } else {
                this.cancelPanelReveal();
            }
        } else {
            // CRITICAL FIX: For short taps, keep drag indicator visible and show hint
            // Don't hide indicator until user clicks outside or starts dragging
            if (touchDuration < 300 && dragDistance < 10) {
                this.showGestureHint();
                // Drag indicator stays visible - will be hidden by document click or next gesture
                if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Short tap detected, keeping drag indicator visible');
            } else {
                // Hide indicator for longer touches that didn't become drags
                this.hideDragIndicator();
            }
        }

        this.resetGestureState();
    }

    /**
     * Handle document clicks for dismissing panel
     * @param {Event} event - Click event
     */
    onDocumentClick(event) {
        // Don't dismiss if clicking inside the settings panel
        if (this.settingsPanel && this.settingsPanel.isOpen) {
            const settingsElement = document.querySelector('.settings-panel');
            if (settingsElement && settingsElement.contains(event.target)) {
                return;
            }

            // Don't dismiss if clicking the gesture zone
            const gestureZone = document.getElementById('settings-gesture-zone');
            if (gestureZone && gestureZone.contains(event.target)) {
                return;
            }

            // Dismiss panel
            this.settingsPanel.close();
        }
    }

    /**
     * Handle keyboard events
     * @param {Event} event - Keyboard event
     */
    onKeyDown(event) {
        if (event.key === 'Escape' && this.settingsPanel && this.settingsPanel.isOpen) {
            event.preventDefault();
            this.settingsPanel.close();
        }
    }

    /**
     * Show drag indicator
     */
    showDragIndicator() {
        if (this.dragIndicator) {
            this.dragIndicator.style.opacity = '0.6';
        }
    }

    /**
     * Hide drag indicator
     */
    hideDragIndicator() {
        if (this.dragIndicator) {
            this.dragIndicator.style.opacity = '0';
        }
    }

    /**
     * Start panel reveal animation
     */
    startPanelReveal() {
        if (this.settingsPanel) {
            this.panelTransitioning = true;
            this.settingsPanel.startReveal();
        }
    }

    /**
     * Update panel position during drag
     * @param {number} dragDistance - Distance dragged in pixels
     */
    updatePanelPosition(dragDistance) {
        if (this.settingsPanel) {
            // Calculate reveal percentage (0 to 1)
            const maxDrag = 200; // Maximum drag distance for full reveal
            const revealPercent = Math.min(dragDistance / maxDrag, 1);
            this.settingsPanel.updateReveal(revealPercent);
        }
    }

    /**
     * Complete panel reveal and open settings
     */
    completePanelReveal() {
        if (this.settingsPanel) {
            this.settingsPanel.open();
        }
        this.panelTransitioning = false;
    }

    /**
     * Cancel panel reveal and hide panel
     */
    cancelPanelReveal() {
        if (this.settingsPanel) {
            this.settingsPanel.cancelReveal();
        }
        this.panelTransitioning = false;
    }

    /**
     * Show brief gesture hint to user
     */
    showGestureHint() {
        const hint = document.createElement('div');
        hint.className = 'gesture-hint';
        hint.textContent = 'Drag down to open settings';

        // CRITICAL FIX: Position relative to content area, not viewport
        const contentContainer = document.querySelector('.calendar-content');
        let topPosition = `${this.gestureZoneHeight + 10}px`;
        let leftPosition = '50%';

        if (contentContainer) {
            const rect = contentContainer.getBoundingClientRect();
            topPosition = `${rect.top + this.gestureZoneHeight + 10}px`;
            leftPosition = `${rect.left + (rect.width / 2)}px`;
            if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Positioning hint relative to content area:', {
                top: topPosition,
                left: leftPosition
            });
        } else {
            console.warn('GestureHandler: Content container not found for hint, using viewport positioning');
        }

        hint.style.cssText = `
            position: fixed;
            top: ${topPosition};
            left: ${leftPosition};
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 14px;
            z-index: 200;
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
        `;

        document.body.appendChild(hint);

        // Animate in
        setTimeout(() => hint.style.opacity = '1', 10);

        // Remove after delay
        setTimeout(() => {
            hint.style.opacity = '0';
            setTimeout(() => hint.remove(), 300);
        }, 2000);
    }

    /**
     * Reset gesture state
     */
    resetGestureState() {
        this.gestureActive = false;
        this.isDragging = false;
        this.startY = 0;
        this.currentY = 0;
        this.touchStartTime = 0;
    }

    /**
     * Update gesture zone height (for responsive adjustments)
     * @param {number} height - New height in pixels
     */
    updateGestureZoneHeight(height) {
        this.gestureZoneHeight = height;

        const gestureZone = document.getElementById('settings-gesture-zone');
        if (gestureZone) {
            gestureZone.style.height = `${height}px`;
        }

        if (this.dragIndicator) {
            this.dragIndicator.style.top = `${height}px`;
        }

        if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Gesture zone height updated to:', height);
    }

    /**
     * Enable gesture recognition
     */
    enable() {
        this.isListening = true;
        const gestureZone = document.getElementById('settings-gesture-zone');
        if (gestureZone) {
            gestureZone.style.pointerEvents = 'auto';
        }
        if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Gesture recognition enabled');
    }

    /**
     * Disable gesture recognition
     */
    disable() {
        this.isListening = false;
        this.resetGestureState();
        this.hideDragIndicator();

        const gestureZone = document.getElementById('settings-gesture-zone');
        if (gestureZone) {
            gestureZone.style.pointerEvents = 'none';
        }
        if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Gesture recognition disabled');
    }

    /**
     * Cleanup gesture handler
     */
    destroy() {
        // Remove event listeners
        const gestureZone = document.getElementById('settings-gesture-zone');
        if (gestureZone) {
            gestureZone.remove();
        }

        if (this.dragIndicator) {
            this.dragIndicator.remove();
        }

        // Remove document event listeners
        document.removeEventListener('click', this.onDocumentClick.bind(this));
        document.removeEventListener('keydown', this.onKeyDown.bind(this));

        if (!window.CALENDARBOT_PRODUCTION) console.log('GestureHandler: Cleaned up and destroyed');
    }
}

// Export for module systems or global use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GestureHandler;
} else if (typeof window !== 'undefined') {
    window.GestureHandler = GestureHandler;
}