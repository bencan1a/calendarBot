/* CalendarBot Whats-Next-View Layout JavaScript */

// Global state
let currentTheme = 'eink';
let autoRefreshInterval = null;
let autoRefreshEnabled = true;
let countdownInterval = null;
let currentMeeting = null;
let upcomingMeetings = [];
let lastDataUpdate = null;
let settingsPanel = null;

// Performance optimization state for countdown system
let lastCountdownValues = {
    displayText: null,
    unitsText: null,
    labelText: null,
    cssClass: null,
    urgent: null
};

// Performance optimization state for incremental DOM updates
let lastDOMState = {
    meetingTitle: null,
    meetingTime: null,
    meetingLocation: null,
    meetingDescription: null,
    contextMessage: null,
    statusText: null,
    lastUpdateText: null,
    layoutState: null // 'meeting', 'empty', 'error'
};

// Timezone-aware time calculation state
let backendBaselineTime = null; // Backend timezone-aware time at page load
let frontendBaselineTime = null; // Frontend Date.now() at page load

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    initializeWhatsNextView();
});

/**
 * Initialize the Whats-Next-View layout
 * Sets up all functionality and starts the countdown system
 */
function initializeWhatsNextView() {
    // Detect current theme from HTML class
    const htmlElement = document.documentElement;
    const themeClasses = htmlElement.className.match(/theme-(\w+)/);
    if (themeClasses) {
        currentTheme = themeClasses[1];
    }

    // Setup core functionality
    setupNavigationButtons();
    setupKeyboardNavigation();
    setupAutoRefresh();
    setupMobileEnhancements();

    // Setup whats-next-view specific functionality
    setupCountdownSystem();
    setupMeetingDetection();
    setupAccessibility();

    // Initialize viewport resolution display
    setupViewportResolutionDisplay();

    // Initialize settings panel
    initializeSettingsPanel();

    // Initialize state manager (Phase 2)
    initializeStateManager();

    // Initial data load
    loadMeetingData();
}

/**
 * Navigation button click handlers (following 3x4 pattern)
 */
function setupNavigationButtons() {
    document.addEventListener('click', function (event) {
        const element = event.target.closest('[data-action]');
        if (element) {
            const action = element.getAttribute('data-action');
            event.preventDefault();

            switch (action) {
                case 'refresh':
                    refresh();
                    break;
                case 'theme':
                    toggleTheme();
                    break;
                case 'layout':
                    cycleLayout();
                    break;
                default:
                    if (action === 'prev' || action === 'next') {
                        navigate(action);
                    }
            }
        }
    });
}

/**
 * Keyboard navigation (following 3x4 pattern)
 */
function setupKeyboardNavigation() {
    document.addEventListener('keydown', function (event) {
        const navigationKeys = ['r', 'R', 't', 'T', 'l', 'L', ' '];
        if (navigationKeys.includes(event.key)) {
            event.preventDefault();
        }

        switch (event.key) {
            case 'r':
            case 'R':
                refresh();
                break;
            case 't':
            case 'T':
                toggleTheme();
                break;
            case 'l':
            case 'L':
                cycleLayout();
                break;
            case ' ': // Space bar for manual refresh
                refresh();
                break;
        }
    });
}

/**
 * Auto-refresh functionality (following 3x4 pattern)
 * Optimized for reduced server load - 5 minute intervals instead of 1 minute
 */
function setupAutoRefresh() {
    // Performance optimization: Reduced from 60s to 300s (5 minutes)
    // This reduces server requests by 80% while maintaining reasonable data freshness
    const refreshInterval = getAutoRefreshInterval();

    if (autoRefreshEnabled) {
        autoRefreshInterval = setInterval(function () {
            refreshSilent();
        }, refreshInterval);

    }
}

/**
 * Get auto-refresh interval with configuration support
 * @returns {number} Refresh interval in milliseconds
 */
function getAutoRefreshInterval() {
    // Check for user configuration from settings system
    if (typeof window.settingsData !== 'undefined' &&
        window.settingsData.display &&
        window.settingsData.display.auto_refresh_interval) {
        const interval = parseInt(window.settingsData.display.auto_refresh_interval);
        if (interval && interval > 0) {
            return interval;
        }
    }

    // Fallback: Check for legacy configuration
    if (typeof window.whatsNextViewSettings !== 'undefined' &&
        window.whatsNextViewSettings.autoRefreshInterval) {
        return window.whatsNextViewSettings.autoRefreshInterval;
    }

    // Default to 5 minutes (300 seconds) for performance optimization
    return 300000; // 5 minutes
}

/**
 * Mobile/touch enhancements (following 3x4 pattern)
 */
function setupMobileEnhancements() {
    // Add touch event listeners for swipe navigation
    let touchStartX = 0;
    let touchEndX = 0;

    document.addEventListener('touchstart', function (event) {
        touchStartX = event.changedTouches[0].screenX;
    });

    document.addEventListener('touchend', function (event) {
        touchEndX = event.changedTouches[0].screenX;
        handleSwipe();
    });

    function handleSwipe() {
        const swipeThreshold = 50;
        const swipeDistance = touchEndX - touchStartX;
        const rightEdgeThreshold = 50; // Pixels from right edge to trigger layout switch
        const windowWidth = window.innerWidth;

        if (Math.abs(swipeDistance) > swipeThreshold) {
            // Check for swipe left from right edge for layout switching
            if (swipeDistance < 0 && touchStartX >= (windowWidth - rightEdgeThreshold)) {
                // Swipe left from right edge - switch layout
                cycleLayout();
            } else if (swipeDistance > 0) {
                // Swipe right - refresh
                refresh();
            } else {
                // Swipe left from non-edge - refresh
                refresh();
            }
        }
    }

    // Prevent zoom on double-tap for iOS
    let lastTouchEnd = 0;
    document.addEventListener('touchend', function (event) {
        const now = (new Date()).getTime();
        if (now - lastTouchEnd <= 300) {
            event.preventDefault();
        }
        lastTouchEnd = now;
    }, false);
}

/**
 * Setup countdown timer system (optimized)
 */
function setupCountdownSystem() {
    // Start countdown updates every second with efficiency optimizations
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }

    // Initialize DOM cache for countdown system
    DOMCache.init();

    countdownInterval = setInterval(function () {
        updateCountdown();
        checkMeetingTransitions();
    }, 1000);
}

/**
 * Setup meeting detection and filtering
 */
function setupMeetingDetection() {
    // This will be called after data loads to find the next meeting
}

/**
 * Setup accessibility features
 */
function setupAccessibility() {
    // Add ARIA live region for countdown announcements
    const liveRegion = document.createElement('div');
    liveRegion.id = 'whats-next-live-region';
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.className = 'sr-only';
    document.body.appendChild(liveRegion);

    // Add focus management for meeting cards
    const meetingCards = document.querySelectorAll('.meeting-card');
    meetingCards.forEach((card, index) => {
        card.setAttribute('tabindex', '0');
        card.setAttribute('role', 'button');
        card.setAttribute('aria-label', getMeetingAriaLabel(card));
    });

}

/**
 * Setup viewport resolution display at bottom right of window (optimized)
 */
function setupViewportResolutionDisplay() {
    // Create viewport resolution display element
    const viewportDisplay = document.createElement('div');
    viewportDisplay.id = 'viewport-resolution-display';
    viewportDisplay.style.cssText = `
        position: fixed;
        bottom: 10px;
        right: 10px;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 6px 10px;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
        font-size: 11px;
        z-index: 99999;
        pointer-events: none;
        user-select: none;
        backdrop-filter: blur(4px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        line-height: 1.3;
        white-space: pre-line;
        display: none;
    `;

    // Store in DOM cache for efficient access
    DOMCache.viewportDisplay = viewportDisplay;

    // Cache content area reference and add border styling
    if (!DOMCache.calendarContent) {
        DOMCache.calendarContent = document.querySelector('.calendar-content');
    }
    
    if (DOMCache.calendarContent) {
        DOMCache.calendarContent.style.border = '1px solid #bdbdbd';
        DOMCache.calendarContent.style.boxSizing = 'border-box';
    }

    // Optimized update function with caching
    let lastViewportWidth = 0;
    let lastViewportHeight = 0;
    let lastContentWidth = 0;
    let lastContentHeight = 0;

    function updateViewportDisplay() {
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        // Get content area dimensions using cached reference
        let contentWidth = 300;  // Default from CSS
        let contentHeight = 400; // Default from CSS
        
        if (DOMCache.calendarContent) {
            const rect = DOMCache.calendarContent.getBoundingClientRect();
            contentWidth = Math.round(rect.width);
            contentHeight = Math.round(rect.height);
        }
        
        // Only update if dimensions have actually changed
        if (viewportWidth !== lastViewportWidth ||
            viewportHeight !== lastViewportHeight ||
            contentWidth !== lastContentWidth ||
            contentHeight !== lastContentHeight) {
            
            DOMCache.viewportDisplay.textContent = `Viewport: ${viewportWidth} × ${viewportHeight}\nContent: ${contentWidth} × ${contentHeight}`;
            
            // Update cached values
            lastViewportWidth = viewportWidth;
            lastViewportHeight = viewportHeight;
            lastContentWidth = contentWidth;
            lastContentHeight = contentHeight;
        }
    }

    // Throttled resize handler to improve performance
    let resizeTimeout;
    function throttledUpdateViewport() {
        if (resizeTimeout) {
            clearTimeout(resizeTimeout);
        }
        resizeTimeout = setTimeout(updateViewportDisplay, 100); // 100ms throttle
    }

    // Initial display update
    updateViewportDisplay();

    // Add to document body
    document.body.appendChild(viewportDisplay);

    // Update on window resize with throttling
    window.addEventListener('resize', throttledUpdateViewport);
}

/**
 * Load meeting data from CalendarBot API (Phase 2: JSON consumption)
 * Uses WhatsNextStateManager instead of HTML parsing
 */
async function loadMeetingData() {
    try {
        showLoadingIndicator('Loading meetings...');

        if (!whatsNextStateManager) {
            throw new Error('WhatsNextStateManager not initialized');
        }

        // Use state manager to load data with automatic incremental DOM updates
        const data = await whatsNextStateManager.loadData();
        // DOM updates are now handled automatically by state manager's refreshView()
        
        // Update global variables for backward compatibility with existing functions
        if (data && data.events) {
            upcomingMeetings = data.events.map(event => ({
                graph_id: event.graph_id,
                title: event.title,
                start_time: event.start_time,
                end_time: event.end_time,
                location: event.location || '',
                description: event.description || '',
                is_hidden: event.is_hidden || false
            }));
            
            lastDataUpdate = new Date();

        } else {
            showErrorState('Failed to load meeting data');
        }

    } catch (error) {
        showErrorState('Network error occurred');
    } finally {
        hideLoadingIndicator();
    }
}





/**
 * Detect the current/next meeting
 */
function detectCurrentMeeting() {
    const now = getCurrentTime();
    currentMeeting = null;

    // Find the earliest remaining meeting
    for (const meeting of upcomingMeetings) {
        const meetingStart = new Date(meeting.start_time);
        const meetingEnd = new Date(meeting.end_time);

        // Check if meeting is currently happening
        if (now >= meetingStart && now <= meetingEnd) {
            currentMeeting = meeting;
            break;
        }

        // Check if meeting is upcoming
        if (meetingStart > now) {
            currentMeeting = meeting;
            break;
        }
    }

    updateMeetingDisplayOptimized();
}

// ===========================================
// P0 TIME GAP DISPLAY FUNCTIONS
// ===========================================

/**
 * Performance optimized version of calculateTimeGap with input validation
 * @param {Date} currentTime - Current time
 * @param {Date} nextMeetingTime - Next meeting start time
 * @returns {number} Time gap in milliseconds
 */
function calculateTimeGapOptimized(currentTime, nextMeetingTime) {
    // Fast path for null/undefined inputs
    if (!currentTime || !nextMeetingTime) {
        return 0;
    }

    // Direct millisecond calculation without repeated getTime() calls
    const gap = nextMeetingTime.getTime() - currentTime.getTime();
    return gap > 0 ? gap : 0; // Optimized Math.max replacement
}

/**
 * Performance optimized version of formatTimeGap with structured return
 * @param {number} timeGapMs - Time gap in milliseconds
 * @returns {Object} Object with number and units properties for efficient DOM updates
 */
function formatTimeGapOptimized(timeGapMs) {
    if (timeGapMs <= 0) {
        return { number: '0', units: 'minutes' };
    }

    // Use integer division for better performance
    const totalMinutes = Math.floor(timeGapMs / 60000); // Direct division by 60000ms
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    if (hours === 0) {
        return {
            number: minutes.toString(),
            units: minutes === 1 ? 'minute' : 'minutes'
        };
    } else if (minutes === 0) {
        return {
            number: hours.toString(),
            units: hours === 1 ? 'hour' : 'hours'
        };
    } else {
        return {
            number: hours.toString(),
            units: `${hours === 1 ? 'hour' : 'hours'} ${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`
        };
    }
}

/**
 * Check boundary alert conditions for visual warnings
 * @param {number} timeGapMs - Time gap in milliseconds
 * @returns {Object} Alert information with type and message
 */
function checkBoundaryAlert(timeGapMs) {
    const totalMinutes = Math.floor(timeGapMs / (1000 * 60));

    if (totalMinutes <= 2) {
        return {
            type: 'critical',
            cssClass: 'time-gap-critical',
            message: 'WRAP UP NOW',
            showCountdown: true,
            urgent: true
        };
    } else if (totalMinutes <= 10) {
        return {
            type: 'tight',
            cssClass: 'time-gap-tight',
            message: 'Meeting starts soon',
            showCountdown: true,
            urgent: true
        };
    } else if (totalMinutes <= 30) {
        return {
            type: 'comfortable',
            cssClass: 'time-gap-comfortable',
            message: 'Upcoming meeting',
            showCountdown: false,
            urgent: false
        };
    } else {
        return {
            type: 'relaxed',
            cssClass: '',
            message: 'Next meeting',
            showCountdown: false,
            urgent: false
        };
    }
}

/**
 * Update the countdown display with P0 time gap and boundary alerts
 * Performance optimized: Uses DOM cache and only updates when values change
 */
function updateCountdown() {
    // Use cached DOM elements for better performance
    if (!DOMCache.countdownTime) {
        DOMCache.countdownTime = document.querySelector('.countdown-time');
        DOMCache.countdownLabel = document.querySelector('.countdown-label');
        DOMCache.countdownUnits = document.querySelector('.countdown-units');
        DOMCache.countdownContainer = document.querySelector('.countdown-container');
    }

    if (!DOMCache.countdownTime || !currentMeeting) {
        return;
    }

    const now = getCurrentTime();
    const meetingStart = new Date(currentMeeting.start_time);
    const meetingEnd = new Date(currentMeeting.end_time);

    let timeRemaining;
    let labelText;

    // Determine if meeting is current or upcoming
    if (now >= meetingStart && now <= meetingEnd) {
        // Meeting is happening now - show time until end
        timeRemaining = meetingEnd - now;
        labelText = 'Time Remaining';
    } else if (meetingStart > now) {
        // Meeting is upcoming - show time until start
        timeRemaining = meetingStart - now;
        labelText = 'Starts In';
    } else {
        // Meeting has passed
        detectCurrentMeeting();
        return;
    }

    if (timeRemaining <= 0) {
        detectCurrentMeeting();
        return;
    }

    // Performance optimization: Calculate time gap efficiently
    const timeGap = calculateTimeGapOptimized(now, meetingStart);
    const boundaryAlert = checkBoundaryAlert(timeGap);

    // Performance optimization: Generate display values
    let displayText;
    let unitsText;

    if (now < meetingStart) {
        // Upcoming meeting - use optimized formatTimeGap function
        const formattedGap = formatTimeGapOptimized(timeGap);
        displayText = formattedGap.number;
        unitsText = formattedGap.units;

        // Special handling for critical alerts
        if (boundaryAlert.type === 'critical') {
            labelText = boundaryAlert.message;
            unitsText = 'REMAINING';
        } else if (boundaryAlert.type === 'tight') {
            labelText = boundaryAlert.message;
        }
    } else {
        // Meeting in progress - show time remaining in hours:minutes format
        const hours = Math.floor(timeRemaining / (1000 * 60 * 60));
        const minutes = Math.floor((timeRemaining % (1000 * 60 * 60)) / (1000 * 60));

        if (hours > 0) {
            displayText = `${hours}:${minutes.toString().padStart(2, '0')}`;
            unitsText = hours === 1 ? 'Hour' : 'Hours';
        } else {
            displayText = minutes.toString();
            unitsText = minutes === 1 ? 'Minute' : 'Minutes';
        }
    }

    // Performance optimization: Check if values have changed before updating DOM
    const currentCssClass = boundaryAlert.cssClass || '';
    const hasChanges = (
        lastCountdownValues.displayText !== displayText ||
        lastCountdownValues.unitsText !== unitsText ||
        lastCountdownValues.labelText !== labelText ||
        lastCountdownValues.cssClass !== currentCssClass ||
        lastCountdownValues.urgent !== boundaryAlert.urgent
    );

    if (!hasChanges) {
        // No visual changes needed, skip DOM updates
        return;
    }

    // Update DOM only when values have changed (using cached elements)
    if (lastCountdownValues.displayText !== displayText) {
        DOMCache.countdownTime.textContent = displayText;
        lastCountdownValues.displayText = displayText;
    }

    if (lastCountdownValues.labelText !== labelText && DOMCache.countdownLabel) {
        DOMCache.countdownLabel.textContent = labelText;
        lastCountdownValues.labelText = labelText;
    }

    if (lastCountdownValues.unitsText !== unitsText && DOMCache.countdownUnits) {
        DOMCache.countdownUnits.textContent = unitsText;
        lastCountdownValues.unitsText = unitsText;
    }

    // Update CSS classes only when they change (using cached container)
    if (DOMCache.countdownContainer && lastCountdownValues.cssClass !== currentCssClass) {
        // Remove existing time gap classes
        DOMCache.countdownContainer.classList.remove('time-gap-critical', 'time-gap-tight', 'time-gap-comfortable');

        // Add new boundary alert class
        if (boundaryAlert.cssClass) {
            DOMCache.countdownContainer.classList.add(boundaryAlert.cssClass);
        }
        lastCountdownValues.cssClass = currentCssClass;
    }

    // Update urgent class only when it changes (using cached elements)
    if (lastCountdownValues.urgent !== boundaryAlert.urgent) {
        if (DOMCache.countdownContainer) {
            if (boundaryAlert.urgent) {
                DOMCache.countdownContainer.classList.add('urgent');
            } else {
                DOMCache.countdownContainer.classList.remove('urgent');
            }
        }

        // Legacy urgent support for countdown element
        const isLegacyUrgent = timeRemaining < 15 * 60 * 1000;
        if (isLegacyUrgent) {
            DOMCache.countdownTime.classList.add('urgent');
        } else {
            DOMCache.countdownTime.classList.remove('urgent');
        }

        lastCountdownValues.urgent = boundaryAlert.urgent;
    }

    // P0 Feature: Enhanced boundary alert announcements (unchanged)
    const totalMinutes = Math.floor(timeGap / (1000 * 60));
    if (totalMinutes === 10 || totalMinutes === 5 || totalMinutes === 2 || totalMinutes === 1) {
        const announcement = boundaryAlert.type === 'critical'
            ? `WRAP UP NOW - ${totalMinutes} ${totalMinutes === 1 ? 'minute' : 'minutes'} until ${currentMeeting.title}`
            : `${totalMinutes} ${totalMinutes === 1 ? 'minute' : 'minutes'} until ${currentMeeting.title}`;
        announceToScreenReader(announcement);
    }
}

/**
 * Performance optimized version of updateMeetingDisplay with incremental DOM updates
 * Only updates elements that have actually changed to reduce DOM manipulation overhead
 */
function updateMeetingDisplayOptimized() {
    const content = document.querySelector('.calendar-content');

    if (!content) {
        return;
    }

    if (!currentMeeting) {
        updateEmptyStateOptimized();
        return;
    }

    const now = getCurrentTime();
    const meetingStart = new Date(currentMeeting.start_time);
    const meetingEnd = new Date(currentMeeting.end_time);

    // Determine meeting status
    const isCurrentMeeting = now >= meetingStart && now <= meetingEnd;
    const statusText = isCurrentMeeting ? 'In Progress' : 'Upcoming';

    // Generate new values for change detection (no HTML escaping needed for textContent)
    const newMeetingTitle = currentMeeting.title;
    const newMeetingTime = formatMeetingTime(currentMeeting.start_time, currentMeeting.end_time);
    const newMeetingLocation = currentMeeting.location || '';
    const newMeetingDescription = currentMeeting.description || '';
    const newContextMessage = getContextMessage(isCurrentMeeting);
    const newLayoutState = 'meeting';

    // Performance optimization: Check if we need to create the layout structure
    const needsFullRebuild = (
        lastDOMState.layoutState !== newLayoutState ||
        !content.querySelector('.layout-zone-1') ||
        !content.querySelector('.layout-zone-2') ||
        !content.querySelector('.layout-zone-4')
    );

    if (needsFullRebuild) {
        // Create full layout structure only when needed
        createMeetingLayoutStructure(content);
    }

    // Performance optimization: Update only changed elements
    updateMeetingTitleOptimized(newMeetingTitle);
    updateMeetingTimeOptimized(newMeetingTime);
    updateMeetingLocationOptimized(newMeetingLocation);
    updateMeetingDescriptionOptimized(newMeetingDescription);
    updateContextMessageOptimized(newContextMessage);

    // Update DOM state tracking
    lastDOMState.meetingTitle = newMeetingTitle;
    lastDOMState.meetingTime = newMeetingTime;
    lastDOMState.meetingLocation = newMeetingLocation;
    lastDOMState.meetingDescription = newMeetingDescription;
    lastDOMState.contextMessage = newContextMessage;
    lastDOMState.layoutState = newLayoutState;

    // Re-setup accessibility only when layout was rebuilt
    if (needsFullRebuild) {
        setupAccessibility();
    }
}

/**
 * Create the meeting layout structure in the content container
 * @param {Element} content - The calendar content container
 */
function createMeetingLayoutStructure(content) {
    const html = `
        <!-- Zone 1 (100px): Time gap display -->
        <div class="layout-zone-1">
            <div class="countdown-container">
                <div class="countdown-label text-small">Next Meeting</div>
                <div class="countdown-time text-primary">--</div>
                <div class="countdown-units text-caption">Minutes</div>
            </div>
        </div>
        
        <!-- Zone 2 (140px): Next meeting information -->
        <div class="layout-zone-2">
            <div class="meeting-card current" data-graph-id="${currentMeeting ? currentMeeting.id || currentMeeting.graph_id || '' : ''}">
                <div class="meeting-title text-primary"></div>
                <div class="meeting-time text-secondary"></div>
                <div class="meeting-location text-supporting" style="display: none;"></div>
                <div class="meeting-description text-small" style="display: none;"></div>
                <button class="meeting-close-box" aria-label="Hide event" tabindex="0"></button>
            </div>
        </div>
        
        <!-- Zone 4 (60px): Additional context -->
        <div class="layout-zone-4">
            <div class="context-info text-center">
                <div class="context-message text-caption"></div>
            </div>
        </div>
    `;

    content.innerHTML = html;
    
    // Set up event hiding functionality
    setupEventHiding();
}

/**
 * Update meeting title element only if it has changed
 * @param {string} newTitle - New meeting title
 */
function updateMeetingTitleOptimized(newTitle) {
    if (lastDOMState.meetingTitle === newTitle) {
        return; // No change needed
    }

    const titleElement = document.querySelector('.meeting-title');
    if (titleElement) {
        titleElement.textContent = newTitle;
    }
}

/**
 * Update meeting time element only if it has changed
 * @param {string} newTime - New meeting time
 */
function updateMeetingTimeOptimized(newTime) {
    if (lastDOMState.meetingTime === newTime) {
        return; // No change needed
    }

    const timeElement = document.querySelector('.meeting-time');
    if (timeElement) {
        timeElement.textContent = newTime;
    }
}

/**
 * Update meeting location element only if it has changed
 * @param {string} newLocation - New meeting location
 */
function updateMeetingLocationOptimized(newLocation) {
    if (lastDOMState.meetingLocation === newLocation) {
        return; // No change needed
    }

    const locationElement = document.querySelector('.meeting-location');
    if (locationElement) {
        if (newLocation) {
            locationElement.textContent = newLocation;
            locationElement.style.display = 'block';
        } else {
            locationElement.style.display = 'none';
        }
    }
}

/**
 * Update meeting description element only if it has changed
 * @param {string} newDescription - New meeting description
 */
function updateMeetingDescriptionOptimized(newDescription) {
    if (lastDOMState.meetingDescription === newDescription) {
        return; // No change needed
    }

    const descriptionElement = document.querySelector('.meeting-description');
    if (descriptionElement) {
        if (newDescription) {
            descriptionElement.textContent = newDescription;
            descriptionElement.style.display = 'block';
        } else {
            descriptionElement.style.display = 'none';
        }
    }
}

/**
 * Update context message element only if it has changed
 * @param {string} newMessage - New context message
 */
function updateContextMessageOptimized(newMessage) {
    if (lastDOMState.contextMessage === newMessage) {
        return; // No change needed
    }

    const messageElement = document.querySelector('.context-message');
    if (messageElement) {
        messageElement.textContent = newMessage;
    }
}

/**
 * Format last update time for display
 * @returns {string} Formatted last update time
 */
function formatLastUpdate() {
    // Handle case where lastDataUpdate is null
    if (!lastDataUpdate) {
        return 'Just now';
    }

    const now = new Date();
    const diffMs = now - lastDataUpdate;
    const diffMins = Math.floor(diffMs / (1000 * 60));

    if (diffMins < 1) {
        return 'Just now';
    } else if (diffMins === 1) {
        return '1 minute ago';
    } else if (diffMins < 60) {
        return `${diffMins} minutes ago`;
    } else {
        return lastDataUpdate.toLocaleTimeString([], {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
    }
}

/**
 * Get contextual message based on meeting status
 * @param {boolean} isCurrentMeeting - Whether meeting is currently in progress
 * @returns {string} Context message
 */
function getContextMessage(isCurrentMeeting) {
    if (isCurrentMeeting) {
        return 'Meeting in progress';
    }

    const now = getCurrentTime();
    const meetingStart = new Date(currentMeeting.start_time);
    const timeUntilMeeting = meetingStart - now;
    const minutesUntil = Math.floor(timeUntilMeeting / (1000 * 60));

    if (minutesUntil <= 5) {
        return 'Starting very soon';
    } else if (minutesUntil <= 15) {
        return 'Starting soon';
    } else if (minutesUntil <= 60) {
        return 'Starting within the hour';
    } else {
        return 'Plenty of time';
    }
}

/**
 * Check for meeting transitions
 */
function checkMeetingTransitions() {
    if (!currentMeeting) return;

    const now = getCurrentTime();
    const meetingEnd = new Date(currentMeeting.end_time);

    // Check if current meeting has ended
    if (now > meetingEnd) {
        detectCurrentMeeting();
        announceToScreenReader('Meeting ended. Updating to next meeting.');
    }
}

/**
 * Format meeting time for display
 * @param {string} startTime - ISO time string
 * @param {string} endTime - ISO time string
 * @returns {string} Formatted time string
 */
function formatMeetingTime(startTime, endTime, formattedTimeRange) {
    // Use the pre-formatted time range from backend if available (timezone-aware)
    if (formattedTimeRange) {
        return formattedTimeRange;
    }
    
    // Fallback to original formatting for backwards compatibility
    try {
        const start = new Date(startTime);
        const end = new Date(endTime);

        const options = {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        };

        const startStr = start.toLocaleTimeString([], options);
        const endStr = end.toLocaleTimeString([], options);

        return `${startStr} - ${endStr}`;
    } catch (error) {
        return '';
    }
}

/**
 * Performance optimized version of showEmptyState with incremental updates
 * Only updates elements that have changed to reduce DOM manipulation
 */
function updateEmptyStateOptimized() {
    const content = document.querySelector('.calendar-content');
    if (!content) return;

    const newLastUpdate = formatLastUpdate();
    const newLayoutState = 'empty';

    // Check if we need to rebuild the empty state structure
    const needsFullRebuild = (
        lastDOMState.layoutState !== newLayoutState ||
        !content.querySelector('.empty-state')
    );

    if (needsFullRebuild) {
        // Create full empty state structure
        content.innerHTML = `
            <!-- Zone 1 (100px): Empty time display -->
            <div class="layout-zone-1">
                <div class="countdown-container">
                    <div class="countdown-label text-small">Next Meeting</div>
                    <div class="countdown-time text-primary">--</div>
                    <div class="countdown-units text-caption">None</div>
                </div>
            </div>
            
            <!-- Zone 2 (140px): Empty message -->
            <div class="layout-zone-2">
                <div class="empty-state">
                    <div class="empty-state-icon">📅</div>
                    <div class="empty-state-title text-secondary">No Upcoming Meetings</div>
                    <div class="empty-state-message text-supporting">You're all caught up!</div>
                    <div class="last-update text-caption">Updated: ${newLastUpdate}</div>
                </div>
            </div>
            
            <!-- Zone 4 (60px): Context -->
            <div class="layout-zone-4">
                <div class="context-info text-center">
                    <div class="context-message text-caption">No meetings scheduled</div>
                </div>
            </div>
        `;

        // Update all state tracking since we rebuilt everything
        lastDOMState.lastUpdateText = newLastUpdate;
        lastDOMState.layoutState = newLayoutState;
        lastDOMState.meetingTitle = null;
        lastDOMState.meetingTime = null;
        lastDOMState.meetingLocation = null;
        lastDOMState.meetingDescription = null;
        lastDOMState.contextMessage = 'No meetings scheduled';
    } else {
        // Only update last update text if it changed
        updateLastUpdateOptimized(newLastUpdate);
    }
}

/**
 * Update last update text element only if it has changed
 * @param {string} newUpdateText - New last update text
 */
function updateLastUpdateOptimized(newUpdateText) {
    if (lastDOMState.lastUpdateText === newUpdateText) {
        return; // No change needed
    }

    const lastUpdateElement = document.querySelector('.last-update');
    if (lastUpdateElement) {
        lastUpdateElement.textContent = `Updated: ${newUpdateText}`;
        lastDOMState.lastUpdateText = newUpdateText;
    }
}

/**
 * Show error state
 * @param {string} message - Error message to display
 */
function showErrorState(message) {
    const content = document.querySelector('.calendar-content');
    if (!content) return;

    content.innerHTML = `
        <div class="error-state">
            <div class="error-icon">⚠️</div>
            <div class="error-title">Unable to Load Meetings</div>
            <div class="error-message">${escapeHtml(message)}</div>
        </div>
    `;
}

/**
 * Get ARIA label for meeting
 * @param {Element} element - Meeting element
 * @returns {string} ARIA label text
 */
function getMeetingAriaLabel(element) {
    const title = element.querySelector('.meeting-title')?.textContent || '';
    const time = element.querySelector('.meeting-time')?.textContent || '';
    return `Meeting: ${title}${time ? `, ${time}` : ''}`;
}

/**
 * Announce message to screen readers
 * @param {string} message - Message to announce
 */
function announceToScreenReader(message) {
    const liveRegion = document.getElementById('whats-next-live-region');
    if (liveRegion) {
        liveRegion.textContent = message;
    }
}

/**
 * Escape HTML to prevent XSS
 * @param {string} unsafe - Unsafe HTML string
 * @returns {string} Escaped HTML string
 */
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ===========================================
// CALENDARBOT INTEGRATION FUNCTIONS
// (Following 3x4 Layout Patterns)
// ===========================================

/**
 * Navigation function (following 3x4 pattern)
 */
async function navigate(action) {

    try {
        showLoadingIndicator();

        const response = await fetch('/api/navigate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ action: action })
        });

        const data = await response.json();

        if (data.success && data.html) {
            // Use WhatsNextStateManager instead of deprecated HTML parsing
            whatsNextStateManager.refreshView();
            detectCurrentMeeting();
        } else {
            showErrorMessage('Navigation failed');
        }

    } catch (error) {
        showErrorMessage('Navigation error: ' + error.message);
    } finally {
        hideLoadingIndicator();
    }
}

/**
 * Theme switching (following 3x4 pattern)
 */
async function toggleTheme() {

    try {
        const response = await fetch('/api/theme', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        });

        const data = await response.json();

        if (data.success) {
            currentTheme = data.theme;
            document.documentElement.className = document.documentElement.className.replace(/theme-\w+/, `theme-${currentTheme}`);
        } else {
        }

    } catch (error) {
    }
}

/**
 * Layout switching (following 3x4 pattern)
 */
async function cycleLayout() {

    try {
        showLoadingIndicator('Switching layout...');

        const response = await fetch('/api/layout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        });

        const data = await response.json();

        if (data.success) {
            window.location.reload(); // Re-enabled for production use
        } else {
            showErrorMessage('Layout switch failed');
        }

    } catch (error) {
        showErrorMessage('Layout switch error: ' + error.message);
    } finally {
        hideLoadingIndicator();
    }
}

/**
 * Data refresh (following 3x4 pattern) - Phase 2: Uses state manager with incremental DOM updates
 */
async function refresh() {
    
    try {
        if (!whatsNextStateManager) {
            showErrorMessage('State manager not available');
            return;
        }

        // Use state manager for refresh with incremental DOM updates
        await whatsNextStateManager.loadData();
        // DOM is automatically updated via state manager's refreshView()
        
        showSuccessMessage('Meetings refreshed');
        
    } catch (error) {
        showErrorMessage('Refresh failed: ' + error.message);
    }
}

/**
 * Silent refresh for auto-refresh (following 3x4 pattern) - Phase 2: Uses state manager with incremental DOM updates
 */
async function refreshSilent() {
    try {
        if (!whatsNextStateManager) {
            return;
        }

        // Use state manager for silent refresh with incremental DOM updates
        // This now enables full DOM updates while preserving countdown elements
        await whatsNextStateManager.loadData();
        // DOM is automatically updated via state manager's refreshView() which preserves countdown elements


    } catch (error) {
        showErrorMessage('Auto-refresh error - please try manual refresh');
    }
}


// ===========================================
// UI FEEDBACK FUNCTIONS
// (Following 3x4 Layout Patterns)
// ===========================================

/**
 * Show loading indicator
 */
function showLoadingIndicator(message = 'Loading...') {
    let indicator = document.getElementById('loading-indicator');

    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'loading-indicator';
        indicator.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px 15px;
            border-radius: 4px;
            z-index: 1000;
            font-size: 14px;
            display: none;
        `;
        document.body.appendChild(indicator);
    }

    indicator.textContent = message;
    indicator.style.display = 'block';
}

/**
 * Hide loading indicator
 */
function hideLoadingIndicator() {
    const indicator = document.getElementById('loading-indicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

/**
 * Show message to user
 */
function showMessage(message, type = 'info') {
    const messageEl = document.createElement('div');
    messageEl.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        padding: 10px 20px;
        border-radius: 4px;
        z-index: 1000;
        font-size: 14px;
        max-width: 300px;
        text-align: center;
        opacity: 0;
        transition: opacity 0.3s ease;
        ${type === 'error' ? 'background: #dc3545; color: white;' :
            type === 'success' ? 'background: #28a745; color: white;' :
                'background: #17a2b8; color: white;'}
    `;

    messageEl.textContent = message;
    document.body.appendChild(messageEl);

    setTimeout(() => messageEl.style.opacity = '1', 10);
    setTimeout(() => {
        messageEl.style.opacity = '0';
        setTimeout(() => messageEl.remove(), 300);
    }, 3000);
}

function showErrorMessage(message) {
    showMessage(message, 'error');
}

function showSuccessMessage(message) {
    showMessage(message, 'success');
}

// ===========================================
// GLOBAL EXPORTS AND DEBUG HELPERS
// (Following 3x4 Layout Patterns)
// ===========================================

// Cache frequently accessed DOM elements
const DOMCache = {
    calendarContent: null,
    countdownTime: null,
    countdownLabel: null,
    countdownUnits: null,
    countdownContainer: null,
    viewportDisplay: null,
    
    // Initialize cache with commonly accessed elements
    init() {
        this.calendarContent = document.querySelector('.calendar-content');
        this.countdownTime = document.querySelector('.countdown-time');
        this.countdownLabel = document.querySelector('.countdown-label');
        this.countdownUnits = document.querySelector('.countdown-units');
        this.countdownContainer = document.querySelector('.countdown-container');
        this.viewportDisplay = document.getElementById('viewport-resolution-display');
    },
    
    // Clear cache when DOM structure changes
    clear() {
        Object.keys(this).forEach(key => {
            if (key !== 'init' && key !== 'clear') {
                this[key] = null;
            }
        });
    }
};

/**
 * Initialize timezone baseline data from backend HTML for hybrid time calculation
 * @param {Document} doc - Parsed HTML document from backend
 */
function initializeTimezoneBaseline(doc) {
    try {
        // Look for elements with timezone data attributes
        const eventElements = doc.querySelectorAll('[data-current-time][data-event-time]');

        if (eventElements.length > 0) {
            const firstEvent = eventElements[0];
            const backendTimeIso = firstEvent.getAttribute('data-current-time');

            if (backendTimeIso) {
                // Set baseline times for hybrid calculation
                backendBaselineTime = new Date(backendTimeIso);
                frontendBaselineTime = Date.now();
                return true;
            }
        }

        return false;

    } catch (error) {
        backendBaselineTime = null;
        frontendBaselineTime = null;
        return false;
    }
}

// Essential exports for external integration
window.navigate = navigate;
window.toggleTheme = toggleTheme;
window.cycleLayout = cycleLayout;
window.refresh = refresh;
window.getCurrentTheme = () => currentTheme;
window.isAutoRefreshEnabled = () => autoRefreshEnabled;

// Core functionality exports (required for external access)
window.updateCountdown = updateCountdown;
window.detectCurrentMeeting = detectCurrentMeeting;
window.loadMeetingData = loadMeetingData;
window.getCurrentTime = getCurrentTime;

// UI feedback exports (needed for error handling)
window.showErrorMessage = showErrorMessage;
window.showSuccessMessage = showSuccessMessage;

// Essential utility exports
window.formatMeetingTime = formatMeetingTime;
window.escapeHtml = escapeHtml;

// Testing access exports
Object.defineProperty(window, 'currentMeeting', {
    get: function () { return currentMeeting; },
    set: function (value) { currentMeeting = value; }
});

// Settings panel exports
window.getSettingsPanel = getSettingsPanel;
window.hasSettingsPanel = hasSettingsPanel;

// Cleanup export
window.cleanup = cleanup;

// DOM Cache export for external access
window.DOMCache = DOMCache;


// ===========================================
// TIME OVERRIDE FUNCTIONALITY
// ===========================================

/**
 * Get current time - either real time or timezone-aware hybrid time
 * @returns {Date} Current time (real or timezone-corrected)
 */
function getCurrentTime() {

    if (backendBaselineTime && frontendBaselineTime) {
        try {
            const now = Date.now();
            const elapsedMs = now - frontendBaselineTime;
            const correctedTime = new Date(backendBaselineTime.getTime() + elapsedMs);
            return correctedTime;
        } catch (error) {

        }
    }

    // Fallback to browser time
    return new Date();
}


// ===========================================
// SETTINGS PANEL INTEGRATION
// ===========================================

/**
 * Initialize settings panel for whats-next-view layout with retry mechanism
 * Fixes timing race condition where settings-panel.js hasn't finished loading
 */
async function initializeSettingsPanel() {
    const maxRetries = 10;
    const retryDelay = 100; // 100ms between retries
    let retryCount = 0;


    const attemptInitialization = async () => {
        try {
            // Check if SettingsPanel is available
            if (typeof window.SettingsPanel !== 'undefined') {

                settingsPanel = new window.SettingsPanel({
                    layout: 'whats-next-view',
                    gestureZoneHeight: 50,
                    dragThreshold: 20,
                    autoSave: true,
                    autoSaveDelay: 2000
                });

                // CRITICAL FIX: Call initialize() to create DOM elements and gesture handler
                await settingsPanel.initialize();

                return true;
            } else {
                retryCount++;
                if (retryCount <= maxRetries) {
                    // Use setTimeout to retry after delay
                    return new Promise((resolve) => {
                        setTimeout(async () => {
                            const result = await attemptInitialization();
                            resolve(result);
                        }, retryDelay);
                    });
                } else {
                    return false;
                }
            }
        } catch (error) {
            retryCount++;
            if (retryCount <= maxRetries) {
                // Retry on error as well
                return new Promise((resolve) => {
                    setTimeout(async () => {
                        const result = await attemptInitialization();
                        resolve(result);
                    }, retryDelay);
                });
            } else {
                return false;
            }
        }
    };

    await attemptInitialization();
}

/**
 * Get settings panel instance
 * @returns {Object|null} Settings panel instance or null
 */
function getSettingsPanel() {
    return settingsPanel;
}

/**
 * Check if settings panel is available
 * @returns {boolean} Whether settings panel is available
 */
function hasSettingsPanel() {
    return settingsPanel !== null;
}

/**
 * Cleanup function for whats-next-view layout
 */
/**
 * Set up event hiding functionality
 * Adds click handlers to close boxes and manages animations
 */
function setupEventHiding() {
    // Find all close boxes
    const closeBoxes = document.querySelectorAll('.meeting-close-box');
    
    // Add click handlers to each close box
    closeBoxes.forEach(closeBox => {
        closeBox.addEventListener('click', function(event) {
            event.preventDefault();
            event.stopPropagation();
            
            // Get the meeting card and its data
            const meetingCard = this.closest('.meeting-card');
            if (!meetingCard) return;
            
            // Find the event ID from the meeting card
            const graphId = meetingCard.getAttribute('data-graph-id');
            const customId = meetingCard.getAttribute('data-event-id');
            const eventId = graphId || customId;
            
            if (!eventId) {
                return;
            }
            
            // Hide the event using state manager
            hideEvent(eventId);
        });
        
        // Add keyboard support
        closeBox.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                this.click();
            }
        });
    });

}

/**
 * Hide an event using the WhatsNextStateManager
 * @param {string} graphId - The graph_id of the event to hide
 */
async function hideEvent(graphId) {
    if (!graphId) {
        return;
    }
    
    if (!whatsNextStateManager) {
        return;
    }
    
    try {
        // Delegate to state manager which handles optimistic updates, API calls, and error handling
        const success = await whatsNextStateManager.hideEvent(graphId);
        
        if (success) {
        } else {
        }
        
        return success;
    } catch (error) {
        return false;
    }
}

// ===========================================
// WHATS-NEXT STATE MANAGER (Phase 2)
// ===========================================

/**
 * WhatsNextStateManager - Unified state management for the Whats-Next view
 *
 * This class provides a single source of truth for all view state and replaces
 * the multiple competing refresh mechanisms with a unified, event-driven approach.
 *
 * Key Features:
 * - Single source of truth for all frontend state
 * - Event-driven architecture for state changes
 * - JSON-based data loading (replacing HTML parsing)
 * - Optimistic updates for immediate UI feedback
 * - Error handling and recovery mechanisms
 */
class WhatsNextStateManager {
    constructor() {
        // Internal state
        this.state = {
            events: [],
            layoutName: 'whats-next-view',
            lastUpdated: null,
            layoutConfig: {
                showHiddenEvents: false,
                maxEvents: 10,
                timeFormat: '12h'
            },
            loading: false,
            error: null
        };

        // Event listeners for state changes
        this.listeners = {
            stateChanged: [],
            dataLoaded: [],
            eventHidden: [],
            eventUnhidden: [],
            error: []
        };

        // Internal optimistic update cache
        this.optimisticUpdates = new Map();

        // Performance tracking
        this.performanceMetrics = {
            lastLoadTime: null,
            loadDuration: null,
            apiCallCount: 0
        };

    }

    /**
     * Load data from the JSON API endpoint
     * @returns {Promise<Object>} The loaded data
     */
    async loadData() {
        try {
            this._setLoading(true);
            this._setError(null);

            const startTime = performance.now();        
            const requestBody = {};
            const response = await fetch('/api/whats-next/data', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody),
            });

            if (!response.ok) {
                throw new Error(`API request failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            
            // Update performance metrics
            const endTime = performance.now();
            this.performanceMetrics.lastLoadTime = new Date();
            this.performanceMetrics.loadDuration = endTime - startTime;
            this.performanceMetrics.apiCallCount++;

            // Update state with new data
            this.updateState(data);

            
            // Automatically refresh the view with incremental updates
            this.refreshView();
            
            // Emit data loaded event
            this._emitEvent('dataLoaded', { data, metrics: this.performanceMetrics });

            return data;

        } catch (error) {
            this._setError(error.message);
            this._emitEvent('error', { type: 'loadData', error: error.message });
            throw error;
        } finally {
            this._setLoading(false);
        }
    }

    /**
     * Update internal state with new data
     * @param {Object} newData - New data from API response
     */
    updateState(newData) {
        const previousState = { ...this.state };

        // Merge new data into state
        if (newData.events) {
            this.state.events = newData.events;
        }
        if (newData.layout_name) {
            this.state.layoutName = newData.layout_name;
        }
        if (newData.last_updated) {
            this.state.lastUpdated = new Date(newData.last_updated);
        }
        if (newData.layout_config) {
            this.state.layoutConfig = { ...this.state.layoutConfig, ...newData.layout_config };
        }

        // Apply any pending optimistic updates
        this._applyOptimisticUpdates();


        // Emit state change event
        this._emitEvent('stateChanged', {
            previousState,
            newState: { ...this.state },
            changeType: 'update'
        });
    }

    /**
     * Refresh the view by synchronizing DOM with current state using incremental updates
     * This method preserves JavaScript countdown elements by only updating changed content
     */
    refreshView() {
        try {
            // Update global variables for backward compatibility
            this._updateLegacyGlobalState();

            // Perform incremental DOM updates that preserve countdown elements
            this._performIncrementalDOMUpdates();


        } catch (error) {
            this._setError('View refresh failed');
            this._emitEvent('error', { type: 'refreshView', error: error.message });
        }
    }

    /**
     * Perform incremental DOM updates that preserve JavaScript countdown elements
     * Uses smart diffing to only update elements that have actually changed
     */
    _performIncrementalDOMUpdates() {
        if (!this.state.events || this.state.events.length === 0) {
            this._updateToEmptyState();
            return;
        }

        // Find current meeting from state - filter out hidden events
        const now = getCurrentTime();
        let currentMeeting = null;
        const visibleEvents = this.state.events.filter(event => !event.is_hidden);
        
        for (const event of visibleEvents) {
            const meetingStart = new Date(event.start_time);
            const meetingEnd = new Date(event.end_time);
            
            // Check if meeting is currently happening or upcoming
            if (now >= meetingStart && now <= meetingEnd) {
                currentMeeting = event;
                break;
            }
            if (meetingStart > now) {
                currentMeeting = event;
                break;
            }
        }

        if (!currentMeeting) {
            this._updateToEmptyState();
            return;
        }

        // Update current meeting display with incremental updates
        this._updateMeetingDisplayIncremental(currentMeeting);
        
        // Update countdown display (preserves countdown elements)
        this._updateCountdownIncremental(currentMeeting, now);
        
        // Update last update timestamp
        this._updateLastUpdateIncremental();
    }

    /**
     * Update meeting display using incremental DOM updates
     * @param {Object} meeting - The current meeting object
     */
    _updateMeetingDisplayIncremental(meeting) {
        const content = document.querySelector('.calendar-content');
        
        if (!content) {
            return;
        }

        // Ensure basic meeting layout structure exists
        this._ensureMeetingLayoutStructure(content);

        // Update individual components with change detection
        this._updateElementIfChanged('.meeting-title', meeting.title);
        this._updateElementIfChanged('.meeting-time', this._formatMeetingTime(meeting.start_time, meeting.end_time));
        this._updateElementIfChanged('.meeting-location', meeting.location || '');
        this._updateElementIfChanged('.meeting-description', meeting.description || '');
        
        // Update context message
        const isCurrentMeeting = this._isMeetingCurrent(meeting);
        const contextMessage = this._getContextMessage(isCurrentMeeting);
        this._updateElementIfChanged('.context-message', contextMessage);
    }

    /**
     * Update countdown display while preserving countdown JavaScript elements
     * @param {Object} meeting - The current meeting object
     * @param {Date} now - Current time
     */
    _updateCountdownIncremental(meeting, now) {
        const meetingStart = new Date(meeting.start_time);
        const meetingEnd = new Date(meeting.end_time);
        
        // Update global currentMeeting for backward compatibility with countdown system
        window.currentMeeting = {
            title: meeting.title,
            start_time: meeting.start_time,
            end_time: meeting.end_time,
            location: meeting.location || '',
            description: meeting.description || '',
            graph_id: meeting.graph_id
        };
        
        // Trigger existing countdown update function which preserves countdown elements
        updateCountdown();
    }

    /**
     * Update an element's text content only if it has changed
     * @param {string} selector - CSS selector for the element
     * @param {string} newContent - New content to set
     */
    _updateElementIfChanged(selector, newContent) {
        const element = document.querySelector(selector);
        if (!element) {
            return;
        }
        
        const currentContent = element.textContent.trim();
        const trimmedNewContent = (newContent || '').trim();
        
        if (currentContent !== trimmedNewContent) {
            element.textContent = trimmedNewContent;
        }
    }

    /**
     * Ensure basic meeting layout structure exists in the content container
     * @param {Element} content - The calendar content container
     */
    _ensureMeetingLayoutStructure(content) {
        // Check if meeting structure already exists
        let meetingContainer = content.querySelector('.meeting-container');
        
        if (!meetingContainer) {
            // Create basic meeting structure without destroying existing countdown elements
            const existingCountdown = content.querySelector('.countdown-container');
            
            meetingContainer = document.createElement('div');
            meetingContainer.className = 'meeting-container';
            
            // Create meeting info elements
            const meetingTitle = document.createElement('h2');
            meetingTitle.className = 'meeting-title';
            
            const meetingTime = document.createElement('div');
            meetingTime.className = 'meeting-time';
            
            const meetingLocation = document.createElement('div');
            meetingLocation.className = 'meeting-location';
            
            const meetingDescription = document.createElement('div');
            meetingDescription.className = 'meeting-description';
            
            const contextMessage = document.createElement('div');
            contextMessage.className = 'context-message';
            
            // Add elements to container
            meetingContainer.appendChild(meetingTitle);
            meetingContainer.appendChild(meetingTime);
            meetingContainer.appendChild(meetingLocation);
            meetingContainer.appendChild(meetingDescription);
            meetingContainer.appendChild(contextMessage);
            
            // Insert meeting container while preserving countdown
            if (existingCountdown && existingCountdown.parentNode === content) {
                content.insertBefore(meetingContainer, existingCountdown);
            } else {
                content.appendChild(meetingContainer);
            }
        }
    }

    /**
     * Update display to empty state when no meetings are available
     */
    _updateToEmptyState() {
        const content = document.querySelector('.calendar-content');
        if (!content) {
            return;
        }
        
        // Preserve countdown elements while updating meeting content
        const existingCountdown = content.querySelector('.countdown-container');
        
        // Update meeting container to show empty state
        let meetingContainer = content.querySelector('.meeting-container');
        if (meetingContainer) {
            meetingContainer.innerHTML = '<div class="no-meetings">No upcoming meetings</div>';
        } else {
            // Create empty state container
            meetingContainer = document.createElement('div');
            meetingContainer.className = 'meeting-container';
            meetingContainer.innerHTML = '<div class="no-meetings">No upcoming meetings</div>';
            
            if (existingCountdown) {
                content.insertBefore(meetingContainer, existingCountdown);
            } else {
                content.appendChild(meetingContainer);
            }
        }
        
        // Clear global currentMeeting
        window.currentMeeting = null;
    }

    /**
     * Update last update timestamp incrementally
     */
    _updateLastUpdateIncremental() {
        const lastUpdateElement = document.querySelector('.last-update');
        if (lastUpdateElement && this.state.lastUpdated) {
            const formattedTime = this.state.lastUpdated.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
            });
            this._updateElementIfChanged('.last-update', `Last updated: ${formattedTime}`);
        }
    }

    /**
     * Format meeting time for display
     * @param {string} startTime - ISO string of start time
     * @param {string} endTime - ISO string of end time
     * @returns {string} Formatted time string
     */
    _formatMeetingTime(startTime, endTime) {
        const start = new Date(startTime);
        const end = new Date(endTime);
        
        const options = {
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        };
        
        return `${start.toLocaleTimeString([], options)} - ${end.toLocaleTimeString([], options)}`;
    }

    /**
     * Check if a meeting is currently happening
     * @param {Object} meeting - Meeting object
     * @returns {boolean} True if meeting is current
     */
    _isMeetingCurrent(meeting) {
        const now = getCurrentTime();
        const meetingStart = new Date(meeting.start_time);
        const meetingEnd = new Date(meeting.end_time);
        
        return now >= meetingStart && now <= meetingEnd;
    }

    /**
     * Get context message for meeting
     * @param {boolean} isCurrentMeeting - Whether meeting is currently happening
     * @returns {string} Context message
     */
    _getContextMessage(isCurrentMeeting) {
        return isCurrentMeeting ? 'Meeting in progress' : 'Next meeting';
    }

    /**
     * Hide an event with optimistic UI updates
     * @param {string} graphId - The graph ID of the event to hide
     * @returns {Promise<boolean>} Success status
     */
    async hideEvent(graphId) {
        if (!graphId) {
            return false;
        }

        try {
            // Apply optimistic update immediately
            this._addOptimisticUpdate(graphId, { is_hidden: true });
            this._applyOptimisticUpdates();
            this.refreshView();


            // Make API call in background
            const response = await fetch('/api/events/hide', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ graph_id: graphId }),
            });

            if (!response.ok) {
                throw new Error(`Hide request failed: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();

            // Update state with server response if it includes updated data
            if (result.events) {
                this.updateState(result);
            }

            // Remove optimistic update since server confirmed
            this._removeOptimisticUpdate(graphId);


            // Emit event hidden notification
            this._emitEvent('eventHidden', { graphId, result });

            return true;

        } catch (error) {
            
            // Rollback optimistic update
            this._removeOptimisticUpdate(graphId);
            this._applyOptimisticUpdates();
            this.refreshView();

            this._setError(`Failed to hide event: ${error.message}`);
            this._emitEvent('error', { type: 'hideEvent', graphId, error: error.message });
            
            return false;
        }
    }

    /**
     * Unhide an event with optimistic UI updates
     * @param {string} graphId - The graph ID of the event to unhide
     * @returns {Promise<boolean>} Success status
     */
    async unhideEvent(graphId) {
        if (!graphId) {
            return false;
        }

        try {
            // Apply optimistic update immediately
            this._addOptimisticUpdate(graphId, { is_hidden: false });
            this._applyOptimisticUpdates();
            this.refreshView();


            // Make API call in background
            const response = await fetch('/api/events/unhide', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ graph_id: graphId }),
            });

            if (!response.ok) {
                throw new Error(`Unhide request failed: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();

            // Update state with server response if it includes updated data
            if (result.events) {
                this.updateState(result);
            }

            // Remove optimistic update since server confirmed
            this._removeOptimisticUpdate(graphId);


            // Emit event unhidden notification
            this._emitEvent('eventUnhidden', { graphId, result });

            return true;

        } catch (error) {
            
            // Rollback optimistic update
            this._removeOptimisticUpdate(graphId);
            this._applyOptimisticUpdates();
            this.refreshView();

            this._setError(`Failed to unhide event: ${error.message}`);
            this._emitEvent('error', { type: 'unhideEvent', graphId, error: error.message });
            
            return false;
        }
    }

    /**
     * Get current state
     * @returns {Object} Current state object
     */
    getState() {
        return { ...this.state };
    }

    /**
     * Get current events
     * @returns {Array} Current events array
     */
    getEvents() {
        return [...this.state.events];
    }

    /**
     * Get performance metrics
     * @returns {Object} Performance metrics
     */
    getPerformanceMetrics() {
        return { ...this.performanceMetrics };
    }

    /**
     * Add event listener for state changes
     * @param {string} eventType - Type of event to listen for
     * @param {Function} callback - Callback function
     */
    addEventListener(eventType, callback) {
        if (this.listeners[eventType]) {
            this.listeners[eventType].push(callback);
        } else {
        }
    }

    /**
     * Remove event listener
     * @param {string} eventType - Type of event
     * @param {Function} callback - Callback function to remove
     */
    removeEventListener(eventType, callback) {
        if (this.listeners[eventType]) {
            const index = this.listeners[eventType].indexOf(callback);
            if (index > -1) {
                this.listeners[eventType].splice(index, 1);
            }
        }
    }

    // Private methods

    /**
     * Set loading state
     * @private
     */
    _setLoading(loading) {
        this.state.loading = loading;
    }

    /**
     * Set error state
     * @private
     */
    _setError(error) {
        this.state.error = error;
    }

    /**
     * Emit event to all listeners
     * @private
     */
    _emitEvent(eventType, data) {
        if (this.listeners[eventType]) {
            this.listeners[eventType].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                }
            });
        }
    }

    /**
     * Add optimistic update for immediate UI feedback
     * @private
     */
    _addOptimisticUpdate(graphId, updates) {
        this.optimisticUpdates.set(graphId, updates);
    }

    /**
     * Remove optimistic update
     * @private
     */
    _removeOptimisticUpdate(graphId) {
        this.optimisticUpdates.delete(graphId);
    }

    /**
     * Apply pending optimistic updates to state
     * @private
     */
    _applyOptimisticUpdates() {
        this.state.events = this.state.events.map(event => {
            if (this.optimisticUpdates.has(event.graph_id)) {
                const updates = this.optimisticUpdates.get(event.graph_id);
                return { ...event, ...updates };
            }
            return event;
        });
    }

    /**
     * Update legacy global state variables for backward compatibility
     * @private
     */
    _updateLegacyGlobalState() {
        // Update global variables that existing code depends on - filter out hidden events
        upcomingMeetings = (this.state.events || []).filter(event => !event.is_hidden);
        lastDataUpdate = this.state.lastUpdated || new Date();

        // Find current meeting using existing logic
        const now = getCurrentTime();
        currentMeeting = null;

        for (const meeting of upcomingMeetings) {
            const meetingStart = new Date(meeting.start_time);
            const meetingEnd = new Date(meeting.end_time);

            // Check if meeting is currently happening
            if (now >= meetingStart && now <= meetingEnd) {
                currentMeeting = meeting;
                break;
            }

            // Check if meeting is upcoming
            if (meetingStart > now) {
                currentMeeting = meeting;
                break;
            }
        }
    }
}

// Global state manager instance (initialized after DOM loads)
let whatsNextStateManager = null;

/**
 * Initialize the WhatsNextStateManager
 * Called alongside existing initialization code
 */
function initializeStateManager() {
    try {
        if (!whatsNextStateManager) {
            whatsNextStateManager = new WhatsNextStateManager();

            // Set up error handling
            whatsNextStateManager.addEventListener('error', (data) => {
                showErrorMessage('State manager error: ' + data.error);
            });

            // Set up state change handling for debugging
            whatsNextStateManager.addEventListener('stateChanged', (data) => {
            });

            // Set up data loaded event handling (Phase 2 integration)
            whatsNextStateManager.addEventListener('dataLoaded', (data) => {
                
                // Update global variables for backward compatibility
                if (data.data && data.data.events) {
                    upcomingMeetings = data.data.events.map(event => ({
                        graph_id: event.graph_id,
                        title: event.title,
                        start_time: event.start_time,
                        end_time: event.end_time,
                        location: event.location || '',
                        description: event.description || '',
                        is_hidden: event.is_hidden || false
                    }));
                    
                    lastDataUpdate = new Date();
                    
                    // Trigger existing UI update functions
                    detectCurrentMeeting();
                    updateCountdown();
                }
            });

            // Set up event hidden/unhidden event handling
            whatsNextStateManager.addEventListener('eventHidden', (data) => {
                // Update UI to reflect hidden event
                detectCurrentMeeting();
                updateCountdown();
            });

            whatsNextStateManager.addEventListener('eventUnhidden', (data) => {
                // Update UI to reflect unhidden event
                detectCurrentMeeting();
                updateCountdown();
            });

        }
    } catch (error) {
    }
}

// ===========================================
// END WHATS-NEXT STATE MANAGER
// ===========================================

/**
 * Cleanup function for the Whats-Next-View
 */
function cleanup() {

    // Clean up settings panel
    if (settingsPanel) {
        try {
            settingsPanel.destroy();
            settingsPanel = null;
        } catch (error) {
        }
    }

    // Clean up countdown interval
    if (countdownInterval) {
        clearInterval(countdownInterval);
        countdownInterval = null;
    }

    // Clean up auto-refresh interval
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }

}

// Handle page unload
window.addEventListener('beforeunload', cleanup);

// Export settings panel functions
window.getSettingsPanel = getSettingsPanel;
window.hasSettingsPanel = hasSettingsPanel;
window.cleanup = cleanup;
