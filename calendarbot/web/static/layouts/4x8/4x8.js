/* Calendar Bot Web Interface JavaScript */

// Global state
let currentTheme = 'standard';
let autoRefreshInterval = null;
let autoRefreshEnabled = true;
let settingsPanel = null;

// Timezone-aware time calculation state
let backendBaselineTime = null; // Backend timezone-aware time at page load
let frontendBaselineTime = null; // Frontend Date.now() at page load

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Calendar Bot Web Interface loaded

    // Detect current theme from HTML class
    const htmlElement = document.documentElement;
    const themeClasses = htmlElement.className.match(/theme-(\w+)/);
    if (themeClasses) {
        currentTheme = themeClasses[1];
    }

    // Setup navigation button click handlers
    setupNavigationButtons();

    // Setup keyboard navigation
    setupKeyboardNavigation();

    // Setup auto-refresh
    setupAutoRefresh();

    // Setup touch/mobile enhancements
    setupMobileEnhancements();

    // Initialize settings panel
    initializeSettingsPanel();
}

// Navigation button click handlers
function setupNavigationButtons() {
    // Add click event listeners to arrow buttons using event delegation
    document.addEventListener('click', function(event) {
        const element = event.target.closest('[data-action]');
        if (element) {
            const action = element.getAttribute('data-action');
            if (action === 'prev' || action === 'next') {
                event.preventDefault();
                navigate(action);
            }
        }
    });

    // Navigation button handlers setup complete
}

// Keyboard navigation
function setupKeyboardNavigation() {
    document.addEventListener('keydown', function(event) {
        // Prevent default behavior for navigation keys
        const navigationKeys = ['ArrowLeft', 'ArrowRight', ' ', 'Home', 'End', 'r', 'R'];
        if (navigationKeys.includes(event.key)) {
            event.preventDefault();
        }

        switch(event.key) {
            case 'ArrowLeft':
                navigate('prev');
                break;
            case 'ArrowRight':
                navigate('next');
                break;
            case ' ': // Space bar
                navigate('today');
                break;
            case 'Home':
                navigate('week-start');
                break;
            case 'End':
                navigate('week-end');
                break;
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
        }
    });
}

// Auto-refresh functionality
function setupAutoRefresh() {
    // Get configurable auto-refresh interval (following whats-next-view pattern)
    const refreshInterval = getAutoRefreshInterval();

    if (autoRefreshEnabled) {
        autoRefreshInterval = setInterval(function() {
            refreshSilent();
        }, refreshInterval);

        // Silent by default - consistent with whats-next-view
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

    // Default to 5 minutes for performance optimization
    return 300000; // 5 minutes
}

function toggleAutoRefresh() {
    if (autoRefreshEnabled) {
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = null;
        }
        autoRefreshEnabled = false;
        // Silent by default - consistent with whats-next-view
    } else {
        setupAutoRefresh();
        autoRefreshEnabled = true;
        // Silent by default - consistent with whats-next-view
    }
}

// Mobile/touch enhancements
function setupMobileEnhancements() {
    // Add touch event listeners for swipe navigation
    let touchStartX = 0;
    let touchEndX = 0;

    document.addEventListener('touchstart', function(event) {
        if (event.changedTouches && event.changedTouches.length > 0) {
            touchStartX = event.changedTouches[0].screenX;
        }
    });

    document.addEventListener('touchend', function(event) {
        if (event.changedTouches && event.changedTouches.length > 0) {
            touchEndX = event.changedTouches[0].screenX;
            handleSwipe();
        }
    });

    function handleSwipe() {
        const swipeThreshold = 50; // Minimum distance for a swipe
        const swipeDistance = touchEndX - touchStartX;

        if (Math.abs(swipeDistance) > swipeThreshold) {
            if (swipeDistance < 0) {
                // Swipe left anywhere on screen - switch layout
                cycleLayout();
            } else if (swipeDistance > 0) {
                // Swipe right - go to previous day
                navigate('prev');
            }
        }
    }

    // Prevent zoom on double-tap for iOS
    let lastTouchEnd = 0;
    document.addEventListener('touchend', function(event) {
        const now = (new Date()).getTime();
        if (now - lastTouchEnd <= 300) {
            event.preventDefault();
        }
        lastTouchEnd = now;
    }, false);
}

// Navigation functions
async function navigate(action) {
    // Navigation action requested

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
            // Update the page content
            updatePageContent(data.html);
        } else {
            console.error('Navigation failed:', data.error);
            showErrorMessage('Navigation failed');
        }

    } catch (error) {
        console.error('Navigation error:', error);
        showErrorMessage('Navigation error: ' + error.message);
    } finally {
        hideLoadingIndicator();
    }
}

// Theme switching
async function toggleTheme() {
    // Toggling theme

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

            // Update HTML class
            document.documentElement.className = document.documentElement.className.replace(/theme-\w+/, `theme-${currentTheme}`);

            // Theme changed

            // Visual feedback
            flashThemeChange();
        } else {
            console.error('Theme toggle failed');
        }

    } catch (error) {
        console.error('Theme toggle error:', error);
    }
}

// Layout switching
async function cycleLayout() {
    console.log('DEBUG: cycleLayout() called - L key pressed');
    // Layout cycling requested

    try {
        showLoadingIndicator('Switching layout...');
        console.log('DEBUG: Sending layout change request to API');
        // Sending layout change request to API

        const response = await fetch('/api/layout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        });

        const data = await response.json();
        console.log('DEBUG: API response received:', data);
        // API response received

        if (data.success) {
            console.log('Layout changed to: ' + data.layout);
            // Layout changed successfully
            // Force page reload to switch to new layout
            window.location.reload();
        } else {
            console.error('Layout cycle failed:', data.error);
            showErrorMessage('Layout switch failed');
        }

    } catch (error) {
        console.error('Layout cycle error:', error);
        showErrorMessage('Layout switch error: ' + error.message);
    } finally {
        hideLoadingIndicator();
    }
}

async function setLayout(layout) {
    // Setting layout

    try {
        showLoadingIndicator('Switching layout...');

        const response = await fetch('/api/layout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ layout: layout })
        });

        const data = await response.json();

        if (data.success) {
            // Layout set successfully
            
            // Force full page reload to load new layout's CSS/JS
            window.location.reload();
        } else {
            console.error('Layout set failed:', data.error);
            showErrorMessage('Layout switch failed');
        }

    } catch (error) {
        console.error('Layout set error:', error);
        showErrorMessage('Layout switch error: ' + error.message);
    } finally {
        hideLoadingIndicator();
    }
}

// Data refresh
async function refresh() {
    // Manual refresh requested

    try {
        showLoadingIndicator('Refreshing...');

        const response = await fetch('/api/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();

        if (data.success && data.html) {
            updatePageContent(data.html);
            showSuccessMessage('Data refreshed');
        } else {
            showErrorMessage('Refresh failed');
        }

    } catch (error) {
        console.error('Refresh error:', error);
        showErrorMessage('Refresh error: ' + error.message);
    } finally {
        hideLoadingIndicator();
    }
}

// Silent refresh (for auto-refresh)
async function refreshSilent() {
    try {
        const response = await fetch('/api/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();

        if (data.success && data.html) {
            updatePageContent(data.html);
            console.log('Auto-refresh completed');
            // Auto-refresh completed
        }

    } catch (error) {
        console.error('Silent refresh error:', error);
    }
}

// UI update functions
function updatePageContent(newHTML) {
    // Parse the new HTML
    const parser = new DOMParser();
    const newDoc = parser.parseFromString(newHTML, 'text/html');

    // Initialize timezone baseline from backend HTML for hybrid time calculation
    initializeTimezoneBaseline(newDoc);

    // Update specific sections
    const sectionsToUpdate = [
        '.calendar-title',
        '.status-line',
        '.calendar-content',
        '.navigation-help',
        '.calendar-header',
        '.header-info',
        '.date-info',
        'header',
        '.header'
    ];

    sectionsToUpdate.forEach(selector => {
        const oldElement = document.querySelector(selector);
        const newElement = newDoc.querySelector(selector);

        if (oldElement && newElement) {
            oldElement.innerHTML = newElement.innerHTML;
        }
    });

    // Also update any elements with date-related text content
    // This ensures date displays in headers get updated
    const headerElements = document.querySelectorAll('h1, h2, h3, .title');
    const newHeaderElements = newDoc.querySelectorAll('h1, h2, h3, .title');

    headerElements.forEach((oldEl, index) => {
        if (newHeaderElements[index]) {
            oldEl.innerHTML = newHeaderElements[index].innerHTML;
        }
    });

    // Update page title
    if (newDoc.title) {
        document.title = newDoc.title;
    }

    // Ensure theme class is maintained
    document.documentElement.className = document.documentElement.className.replace(/theme-\w+/, `theme-${currentTheme}`);
}

// Visual feedback functions
function flashNavigationFeedback(action) {
    // Create feedback element
    const feedback = document.createElement('div');
    feedback.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        z-index: 1000;
        font-size: 16px;
        font-weight: bold;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.3s ease;
        text-align: center;
        white-space: nowrap;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    `;

    const icons = {
        'prev': '← Previous',
        'next': 'Next →',
        'today': '📅 Today',
        'week-start': '⏮ Week Start',
        'week-end': 'Week End ⏭'
    };

    feedback.textContent = icons[action] || action;
    document.body.appendChild(feedback);

    // Animate
    setTimeout(() => feedback.style.opacity = '1', 10);
    setTimeout(() => {
        feedback.style.opacity = '0';
        setTimeout(() => feedback.remove(), 300);
    }, 1000);
}

function flashThemeChange() {
    // Flash effect for theme change
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: ${currentTheme === 'eink' ? '#000' : '#fff'};
        opacity: 0;
        z-index: 9999;
        pointer-events: none;
        transition: opacity 0.2s ease;
    `;

    document.body.appendChild(overlay);

    setTimeout(() => overlay.style.opacity = '0.3', 10);
    setTimeout(() => {
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 200);
    }, 150);
}

// Loading indicator
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

function hideLoadingIndicator() {
    const indicator = document.getElementById('loading-indicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

// Message functions
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

// Timezone utility functions
/**
 * Initialize timezone baseline data from backend HTML for hybrid time calculation
 * @param {Document} doc - Parsed HTML document from backend
 * @returns {boolean} True if timezone baseline was successfully initialized
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
        console.error('Timezone baseline initialization failed:', error);
        backendBaselineTime = null;
        frontendBaselineTime = null;
        return false;
    }
}

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
            
            // Check for potential DST transition issues
            const dstIssue = detectDSTTransition(correctedTime);
            if (dstIssue.hasIssue) {
                console.warn('DST transition detected:', dstIssue.message);
                // For DST issues, fall back to browser time with warning
                return new Date();
            }
            
            return correctedTime;
        } catch (error) {
            console.error('Timezone calculation error:', error);
        }
    }

    // Fallback to browser time
    return new Date();
}

/**
 * Detect potential DST transition issues in timezone calculations
 * @param {Date} calculatedTime - The calculated timezone-aware time
 * @returns {Object} DST detection result with issue flag and message
 */
function detectDSTTransition(calculatedTime) {
    try {
        const browserTime = new Date();
        const timeDifference = Math.abs(calculatedTime.getTime() - browserTime.getTime());
        
        // Check if baseline is older than 2 hours (potential DST boundary)
        const baselineAge = Date.now() - frontendBaselineTime;
        const twoHours = 2 * 60 * 60 * 1000;
        
        // If baseline is old and there's a significant time difference, suspect DST transition
        if (baselineAge > twoHours && timeDifference > (30 * 60 * 1000)) { // 30 minute threshold
            return {
                hasIssue: true,
                message: `Potential DST transition: ${Math.round(timeDifference / 60000)} min difference, baseline age: ${Math.round(baselineAge / 60000)} min`,
                timeDifference,
                baselineAge
            };
        }
        
        // Check for unusual time offsets that might indicate DST boundary issues
        const offsetDifference = Math.abs(calculatedTime.getTimezoneOffset() - browserTime.getTimezoneOffset());
        if (offsetDifference > 0) {
            return {
                hasIssue: true,
                message: `Timezone offset mismatch: calculated=${calculatedTime.getTimezoneOffset()}, browser=${browserTime.getTimezoneOffset()}`,
                offsetDifference
            };
        }
        
        return { hasIssue: false, message: 'No DST issues detected' };
        
    } catch (error) {
        return {
            hasIssue: true,
            message: 'DST detection failed: ' + error.message,
            error: error.message
        };
    }
}

/**
 * Check if timezone baseline needs refresh due to potential DST transition
 * @returns {boolean} True if baseline should be refreshed
 */
function shouldRefreshTimezoneBaseline() {
    if (!backendBaselineTime || !frontendBaselineTime) {
        return false;
    }
    
    try {
        const currentTime = getCurrentTime();
        const calculatedTime = new Date(backendBaselineTime.getTime() + (Date.now() - frontendBaselineTime));
        
        // Check for DST transition indicators
        const dstIssue = detectDSTTransition(calculatedTime);
        if (dstIssue.hasIssue) {
            console.info('Timezone baseline refresh recommended due to DST transition');
            return true;
        }
        
        // Check baseline age - refresh after 4 hours to handle DST transitions
        const baselineAge = Date.now() - frontendBaselineTime;
        const fourHours = 4 * 60 * 60 * 1000;
        
        if (baselineAge > fourHours) {
            console.info('Timezone baseline refresh recommended due to age');
            return true;
        }
        
        return false;
        
    } catch (error) {
        console.error('Error checking baseline refresh need:', error);
        return true; // Err on side of caution
    }
}

/**
 * Handle DST transition by refreshing timezone baseline if needed
 * @returns {Promise<boolean>} True if refresh was triggered
 */
async function handleDSTTransition() {
    if (!shouldRefreshTimezoneBaseline()) {
        return false;
    }
    
    try {
        console.info('Triggering silent refresh for DST transition handling');
        await refreshSilent();
        return true;
    } catch (error) {
        console.error('DST transition handling failed:', error);
        return false;
    }
}

// Event ordering validation functions
/**
 * Validate chronological ordering of events in the current view
 * @param {Document} doc - Document containing event elements to validate
 * @returns {Object} Validation result with status and details
 */
function validateEventOrdering(doc = document) {
    try {
        const eventElements = doc.querySelectorAll('[data-event-time]');
        
        if (eventElements.length === 0) {
            return { isValid: true, message: 'No events to validate' };
        }

        const events = Array.from(eventElements).map(element => {
            const eventTimeIso = element.getAttribute('data-event-time');
            const eventTime = new Date(eventTimeIso);
            
            return {
                element,
                time: eventTime,
                timeIso: eventTimeIso,
                text: element.textContent.trim().substring(0, 50) + '...'
            };
        }).filter(event => !isNaN(event.time.getTime()));

        // Sort events by actual time
        events.sort((a, b) => a.time.getTime() - b.time.getTime());

        // Check if DOM order matches chronological order
        const domOrder = Array.from(eventElements).map(el => el.getAttribute('data-event-time'));
        const chronologicalOrder = events.map(event => event.timeIso);
        
        const isValid = JSON.stringify(domOrder) === JSON.stringify(chronologicalOrder);
        
        if (!isValid) {
            console.warn('Event ordering validation failed - events not in chronological order');
            return {
                isValid: false,
                message: `${events.length} events found but not in chronological order`,
                details: {
                    domOrder,
                    chronologicalOrder,
                    events: events.map(e => ({ time: e.timeIso, text: e.text }))
                }
            };
        }

        return {
            isValid: true,
            message: `${events.length} events validated in correct chronological order`
        };

    } catch (error) {
        console.error('Event ordering validation error:', error);
        return {
            isValid: false,
            message: 'Validation failed due to error',
            error: error.message
        };
    }
}

/**
 * Check if events are ordered relative to current timezone-aware time
 * @param {Document} doc - Document containing event elements
 * @returns {Object} Time-relative validation result
 */
function validateEventTimeRelativity(doc = document) {
    try {
        const currentTime = getCurrentTime();
        const eventElements = doc.querySelectorAll('[data-event-time]');
        
        if (eventElements.length === 0) {
            return { isValid: true, message: 'No events to validate' };
        }

        const pastEvents = [];
        const futureEvents = [];
        
        eventElements.forEach(element => {
            const eventTimeIso = element.getAttribute('data-event-time');
            const eventTime = new Date(eventTimeIso);
            
            if (!isNaN(eventTime.getTime())) {
                if (eventTime < currentTime) {
                    pastEvents.push({ time: eventTime, timeIso: eventTimeIso });
                } else {
                    futureEvents.push({ time: eventTime, timeIso: eventTimeIso });
                }
            }
        });

        return {
            isValid: true,
            message: `Events properly categorized: ${pastEvents.length} past, ${futureEvents.length} future`,
            details: {
                currentTime: currentTime.toISOString(),
                pastCount: pastEvents.length,
                futureCount: futureEvents.length,
                timezoneBased: backendBaselineTime !== null
            }
        };

    } catch (error) {
        console.error('Event time relativity validation error:', error);
        return {
            isValid: false,
            message: 'Time relativity validation failed',
            error: error.message
        };
    }
}

/**
 * Perform comprehensive event ordering validation
 * @param {Document} doc - Document to validate (defaults to current document)
 * @returns {Object} Complete validation results
 */
function performEventValidation(doc = document) {
    const orderingResult = validateEventOrdering(doc);
    const timeResult = validateEventTimeRelativity(doc);
    
    const isFullyValid = orderingResult.isValid && timeResult.isValid;
    
    if (!isFullyValid) {
        console.warn('Event validation issues detected:', {
            ordering: orderingResult,
            timeRelativity: timeResult
        });
    }
    
    return {
        isValid: isFullyValid,
        ordering: orderingResult,
        timeRelativity: timeResult,
        timestamp: getCurrentTime().toISOString()
    };
}

// Utility functions
function getCurrentTheme() {
    return currentTheme;
}

function isAutoRefreshEnabled() {
    return autoRefreshEnabled;
}

// Export functions for global access
window.navigate = navigate;
window.toggleTheme = toggleTheme;
window.cycleLayout = cycleLayout;
window.setLayout = setLayout;
window.refresh = refresh;
window.refreshSilent = refreshSilent;
window.toggleAutoRefresh = toggleAutoRefresh;
window.getCurrentTheme = getCurrentTheme;
window.isAutoRefreshEnabled = isAutoRefreshEnabled;

// UI feedback function exports
window.showLoadingIndicator = showLoadingIndicator;
window.hideLoadingIndicator = hideLoadingIndicator;
window.showErrorMessage = showErrorMessage;
window.showSuccessMessage = showSuccessMessage;
window.showMessage = showMessage;

// Content update function exports
window.updatePageContent = updatePageContent;

// Visual feedback function exports
window.flashNavigationFeedback = flashNavigationFeedback;
window.flashThemeChange = flashThemeChange;

// Timezone-aware function exports
window.getCurrentTime = getCurrentTime;
window.initializeTimezoneBaseline = initializeTimezoneBaseline;
window.validateEventOrdering = validateEventOrdering;
window.validateEventTimeRelativity = validateEventTimeRelativity;
window.performEventValidation = performEventValidation;
window.handleDSTTransition = handleDSTTransition;

// Debug helper
window.calendarBot = {
    navigate,
    toggleTheme,
    cycleLayout,
    setLayout,
    refresh,
    toggleAutoRefresh,
    getCurrentTheme,
    isAutoRefreshEnabled,
    currentTheme: () => currentTheme
};

// Settings panel integration
function initializeSettingsPanel() {
    try {
        // Check if SettingsPanel is available
        if (typeof window.SettingsPanel !== 'undefined') {
            settingsPanel = new window.SettingsPanel({
                layout: '4x8',
                gestureZoneHeight: 50,
                dragThreshold: 20,
                autoSave: true,
                autoSaveDelay: 2000
            });
            // Settings panel initialized for 4x8 layout
        } else {
            // Settings panel not available - shared components not loaded
        }
    } catch (error) {
        console.error('Settings panel initialization failed:', error);
    }
}

function getSettingsPanel() {
    return settingsPanel;
}

function hasSettingsPanel() {
    return settingsPanel !== null;
}

// Cleanup function for settings panel
function cleanup() {
    if (settingsPanel) {
        try {
            settingsPanel.destroy();
            settingsPanel = null;
            // Settings panel cleaned up
        } catch (error) {
            console.error('Settings panel cleanup failed:', error);
        }
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

// Calendar Bot JavaScript loaded and ready
