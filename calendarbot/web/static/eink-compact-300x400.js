/* ===========================================
   E-INK COMPACT 300x400 JAVASCRIPT MODULE
   Optimized for 300x400px e-ink displays (portrait)
   =========================================== */

/**
 * E-ink Compact Calendar Bot JavaScript Module
 *
 * Optimized for small e-ink displays with focus on:
 * - Ultra-minimal DOM manipulations for small e-ink refresh cycles
 * - Content truncation logic for limited screen space
 * - Performance optimizations for resource-constrained devices
 * - Touch-optimized interactions for 35px minimum touch targets
 * - Battery-conscious event handling and reduced CPU usage
 */

// ===========================================
// GLOBAL STATE AND CONFIGURATION
// ===========================================

const EInkCompactCalendar = {
    // Configuration for 300x400 display
    config: {
        // E-ink display specifications (compact portrait mode)
        displayWidth: 300,
        displayHeight: 400,

        // Performance settings optimized for compact e-ink
        refreshThrottle: 1000, // Longer throttle for small displays
        touchThrottle: 400,   // Longer delay for more deliberate touches
        swipeThreshold: 50,   // Reduced threshold for smaller display

        // Battery conservation - more aggressive for compact devices
        autoRefreshEnabled: false,
        animationsEnabled: false,
        transitionsEnabled: false,

        // Touch targets (minimum 35px for compact accessibility)
        minTouchTarget: 35,

        // Content truncation limits for compact display
        truncation: {
            currentEventTitle: 25,    // Max 25 characters for current event titles
            upcomingEventTitle: 20,   // Max 20 characters for upcoming events
            laterEventTitle: 15,      // Max 15 characters for later events
            location: 18,             // Max 18 characters for locations
            timeDisplay: 12           // Max 12 characters for time displays
        },

        // API endpoints
        endpoints: {
            refresh: '/api/refresh',
            theme: '/api/theme',
            status: '/api/status'
        }
    },

    // Runtime state
    state: {
        currentTheme: 'eink-compact-300x400',
        isLoading: false,
        lastRefresh: null,
        pendingUpdates: new Set(),
        initialized: false,
        contentTruncated: false
    },

    // Event handlers storage
    handlers: new Map(),

    // Performance monitoring
    performance: {
        apiCallCount: 0,
        domUpdateCount: 0,
        lastApiCall: null,
        truncationCount: 0
    }
};

// ===========================================
// INITIALIZATION AND LIFECYCLE
// ===========================================

/**
 * Initialize the compact e-ink calendar interface
 */
function initializeCompactEInkCalendar() {
    if (EInkCompactCalendar.state.initialized) {
        console.log('Compact E-ink Calendar already initialized');
        return;
    }

    console.log('Initializing Compact E-ink Calendar Bot for 300x400px display');

    // Detect and set theme
    detectAndSetCompactTheme();

    // Setup optimized event handling for compact display
    setupCompactEInkEventHandling();

    // Setup performance monitoring
    setupCompactPerformanceMonitoring();

    // Disable problematic features for e-ink
    disableCompactEInkProblematicFeatures();

    // Setup content update handlers with truncation
    setupCompactContentUpdateHandling();

    // Apply content truncation to existing content
    applyContentTruncation();

    // Mark as initialized
    EInkCompactCalendar.state.initialized = true;

    console.log('Compact E-ink Calendar initialization complete');
    logCompactPerformanceMetrics();
}

/**
 * Detect current theme and configure for compact display
 */
function detectAndSetCompactTheme() {
    const htmlElement = document.documentElement;
    const themeClasses = htmlElement.className.match(/theme-(\w+)/);

    if (themeClasses) {
        EInkCompactCalendar.state.currentTheme = themeClasses[1];
    }

    // Ensure compact e-ink optimizations are applied
    if (EInkCompactCalendar.state.currentTheme === 'eink-compact-300x400') {
        applyCompactEInkOptimizations();
    }

    console.log(`Compact theme detected: ${EInkCompactCalendar.state.currentTheme}`);
}

/**
 * Apply compact e-ink specific optimizations to the DOM
 */
function applyCompactEInkOptimizations() {
    // Disable all CSS transitions and animations
    const style = document.createElement('style');
    style.textContent = `
        .theme-eink-compact-300x400 * {
            transition: none !important;
            animation: none !important;
            animation-duration: 0s !important;
            animation-delay: 0s !important;
            transition-duration: 0s !important;
            transition-delay: 0s !important;
        }
    `;
    document.head.appendChild(style);

    // Set viewport meta for precise compact e-ink display
    const viewport = document.querySelector('meta[name="viewport"]');
    if (viewport) {
        viewport.setAttribute('content',
            'width=300, height=400, initial-scale=1.0, user-scalable=no, ' +
            'minimal-ui, viewport-fit=cover'
        );
    }

    console.log('Compact E-ink display optimizations applied');
}

/**
 * Disable features that are problematic for compact e-ink displays
 */
function disableCompactEInkProblematicFeatures() {
    // Disable text selection to prevent refresh issues
    document.body.style.userSelect = 'none';
    document.body.style.webkitUserSelect = 'none';

    // Disable context menu on long press
    document.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        return false;
    }, { passive: false });

    // Disable drag operations
    document.addEventListener('dragstart', (e) => {
        e.preventDefault();
        return false;
    }, { passive: false });

    // Prevent zoom gestures
    document.addEventListener('wheel', (e) => {
        if (e.ctrlKey) {
            e.preventDefault();
            return false;
        }
    }, { passive: false });

    console.log('Compact E-ink problematic features disabled');
}

// ===========================================
// CONTENT TRUNCATION SYSTEM
// ===========================================

/**
 * Apply content truncation to existing content for compact display
 */
function applyContentTruncation() {
    const truncationRules = [
        { selector: '.current-event .event-title', maxLength: EInkCompactCalendar.config.truncation.currentEventTitle, className: 'truncate-25' },
        { selector: '.upcoming-event .event-title', maxLength: EInkCompactCalendar.config.truncation.upcomingEventTitle, className: 'truncate-20' },
        { selector: '.later-event .event-title', maxLength: EInkCompactCalendar.config.truncation.laterEventTitle, className: 'truncate-15' },
        { selector: '.event-location', maxLength: EInkCompactCalendar.config.truncation.location, className: 'truncate-location' },
        { selector: '.event-time', maxLength: EInkCompactCalendar.config.truncation.timeDisplay, className: 'truncate-time' }
    ];

    let truncatedCount = 0;

    truncationRules.forEach(rule => {
        const elements = document.querySelectorAll(rule.selector);
        elements.forEach(element => {
            if (element.textContent.length > rule.maxLength) {
                element.classList.add(rule.className);
                truncatedCount++;
            }
        });
    });

    EInkCompactCalendar.performance.truncationCount = truncatedCount;
    EInkCompactCalendar.state.contentTruncated = truncatedCount > 0;

    if (truncatedCount > 0) {
        console.log(`Applied truncation to ${truncatedCount} elements for compact display`);
    }
}

/**
 * Truncate text content for compact display
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum character length
 * @returns {string} Truncated text
 */
function truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) {
        return text;
    }
    return text.substring(0, maxLength - 3) + '...';
}

/**
 * Smart truncation that preserves important words
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum character length
 * @returns {string} Intelligently truncated text
 */
function smartTruncateText(text, maxLength) {
    if (!text || text.length <= maxLength) {
        return text;
    }

    // Try to break at word boundaries
    const words = text.split(' ');
    let result = '';
    
    for (const word of words) {
        if ((result + ' ' + word).length <= maxLength - 3) {
            result += (result ? ' ' : '') + word;
        } else {
            break;
        }
    }

    return result ? result + '...' : text.substring(0, maxLength - 3) + '...';
}

// ===========================================
// EVENT HANDLING SYSTEM
// ===========================================

/**
 * Setup optimized event handling for compact e-ink displays
 */
function setupCompactEInkEventHandling() {
    console.log('Setting up Compact E-ink event handling...');

    // Only handle theme toggle button if present
    const setupCompactThemeListener = () => {
        const themeButton = document.querySelector('.theme-toggle, button[data-action="theme"]');
        if (themeButton) {
            console.log('Setting up compact theme toggle button');
            themeButton.addEventListener('click', (event) => {
                event.preventDefault();
                event.stopPropagation();
                console.log('Compact theme toggle clicked');
                toggleCompactTheme();
            }, { passive: false });
        }
    };

    // Setup theme listener immediately
    setupCompactThemeListener();

    // Monitor for theme button changes
    const observer = new MutationObserver((mutations) => {
        let shouldSetupListeners = false;
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                for (let node of mutation.addedNodes) {
                    if (node.nodeType === 1 && 
                        (node.querySelector &&
                         (node.querySelector('.theme-toggle') ||
                          node.querySelector('button[data-action="theme"]')))) {
                        shouldSetupListeners = true;
                        break;
                    }
                }
            }
        });

        if (shouldSetupListeners) {
            console.log('DOM mutation detected, re-setting up compact theme listener');
            setTimeout(setupCompactThemeListener, 100);
        }
    });

    // Observe the entire document for theme button changes
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    console.log('Compact E-ink event handling setup complete');
}

// ===========================================
// API FUNCTIONS
// ===========================================

/**
 * Refresh calendar data for compact display
 */
async function refreshCompact() {
    if (EInkCompactCalendar.state.isLoading) {
        console.log('Compact refresh blocked - already loading');
        return;
    }

    console.log('Compact E-ink refresh requested');
    EInkCompactCalendar.state.isLoading = true;

    try {
        showCompactLoadingIndicator('Refreshing...');

        // Track performance
        EInkCompactCalendar.performance.apiCallCount++;
        EInkCompactCalendar.performance.lastApiCall = Date.now();

        const response = await fetch(EInkCompactCalendar.config.endpoints.refresh, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();

        if (data.success && data.html) {
            await updateCompactEInkContent(data.html);
            EInkCompactCalendar.state.lastRefresh = Date.now();
            showCompactSuccessMessage('Updated');
        } else {
            showCompactErrorMessage('Refresh failed');
        }

    } catch (error) {
        console.error('Compact refresh error:', error);
        showCompactErrorMessage('Error');
    } finally {
        hideCompactLoadingIndicator();
        EInkCompactCalendar.state.isLoading = false;
    }
}

/**
 * Toggle theme for compact display
 */
async function toggleCompactTheme() {
    console.log('Compact E-ink theme toggle requested');

    try {
        const response = await fetch(EInkCompactCalendar.config.endpoints.theme, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        });

        const data = await response.json();

        if (data.success) {
            EInkCompactCalendar.state.currentTheme = data.theme;

            // Update HTML class efficiently
            const htmlElement = document.documentElement;
            htmlElement.className = htmlElement.className.replace(/theme-\w+/, `theme-${data.theme}`);

            // Re-apply compact optimizations if needed
            if (data.theme === 'eink-compact-300x400') {
                applyCompactEInkOptimizations();
                applyContentTruncation();
            }

            console.log(`Compact theme changed to: ${data.theme}`);
        }

    } catch (error) {
        console.error('Compact theme toggle error:', error);
    }
}

// ===========================================
// CONTENT UPDATE SYSTEM
// ===========================================

/**
 * Setup content update handling optimized for compact e-ink
 */
function setupCompactContentUpdateHandling() {
    // Monitor for dynamic content changes
    const observer = new MutationObserver((mutations) => {
        let hasSignificantChanges = false;

        mutations.forEach((mutation) => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                hasSignificantChanges = true;
            }
        });

        if (hasSignificantChanges) {
            EInkCompactCalendar.performance.domUpdateCount++;
            // Reapply truncation to new content
            setTimeout(applyContentTruncation, 50);
        }
    });

    // Observe main content area
    const contentArea = document.querySelector('.calendar-content');
    if (contentArea) {
        observer.observe(contentArea, {
            childList: true,
            subtree: true
        });
    }

    console.log('Compact content update monitoring initialized');
}

/**
 * Update page content efficiently for compact e-ink displays
 * @param {string} newHTML - New HTML content
 */
async function updateCompactEInkContent(newHTML) {
    const startTime = performance.now();

    try {
        // Parse the new HTML
        const parser = new DOMParser();
        const newDoc = parser.parseFromString(newHTML, 'text/html');

        // Update only specific sections to minimize e-ink refreshes
        const sectionsToUpdate = [
            '.calendar-title',
            '.calendar-status',
            '.calendar-content'
        ];

        let updatedSections = 0;

        for (const selector of sectionsToUpdate) {
            const oldElement = document.querySelector(selector);
            const newElement = newDoc.querySelector(selector);

            if (oldElement && newElement) {
                // Check if content actually changed to avoid unnecessary updates
                if (oldElement.innerHTML !== newElement.innerHTML) {
                    oldElement.innerHTML = newElement.innerHTML;
                    updatedSections++;
                }
            }
        }

        // Update page title if changed
        if (newDoc.title && newDoc.title !== document.title) {
            document.title = newDoc.title;
        }

        // Ensure theme class is maintained
        const newThemeClass = newDoc.documentElement.className.match(/theme-\w+/);
        if (newThemeClass) {
            document.documentElement.className = document.documentElement.className.replace(/theme-\w+/, newThemeClass[0]);
        }

        // Apply content truncation to updated content
        applyContentTruncation();

        // Track performance
        EInkCompactCalendar.performance.domUpdateCount++;
        const duration = performance.now() - startTime;

        console.log(`Compact: Updated ${updatedSections} sections in ${duration.toFixed(2)}ms`);

    } catch (error) {
        console.error('Error updating compact e-ink content:', error);
        throw error;
    }
}

// ===========================================
// USER FEEDBACK SYSTEM (COMPACT E-INK)
// ===========================================

/**
 * Show minimal loading indicator for compact e-ink
 * @param {string} message - Loading message
 */
function showCompactLoadingIndicator(message = 'Loading...') {
    let indicator = document.getElementById('compact-loading-indicator');

    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'compact-loading-indicator';
        indicator.style.cssText = `
            position: fixed;
            top: 5px;
            right: 5px;
            background: #000;
            color: #fff;
            padding: 4px 6px;
            font-size: 10px;
            font-family: monospace;
            z-index: 1000;
            border: 1px solid #000;
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
function hideCompactLoadingIndicator() {
    const indicator = document.getElementById('compact-loading-indicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

/**
 * Show error message for compact e-ink displays
 * @param {string} message - Error message
 */
function showCompactErrorMessage(message) {
    showCompactMessage(message, 'error');
}

/**
 * Show success message for compact e-ink displays
 * @param {string} message - Success message
 */
function showCompactSuccessMessage(message) {
    showCompactMessage(message, 'success');
}

/**
 * Show message optimized for compact e-ink displays
 * @param {string} message - Message to show
 * @param {string} type - Message type (error, success, info)
 */
function showCompactMessage(message, type = 'info') {
    const messageEl = document.createElement('div');
    messageEl.style.cssText = `
        position: fixed;
        bottom: 45px;
        left: 50%;
        transform: translateX(-50%);
        padding: 4px 8px;
        font-size: 10px;
        font-family: monospace;
        text-align: center;
        z-index: 1000;
        border: 1px solid #000;
        max-width: 200px;
        ${type === 'error' ? 'background: #000; color: #fff;' : 'background: #fff; color: #000;'}
    `;

    messageEl.textContent = truncateText(message, 20);
    document.body.appendChild(messageEl);

    // Remove after delay (no fade for e-ink)
    setTimeout(() => {
        if (messageEl.parentNode) {
            messageEl.parentNode.removeChild(messageEl);
        }
    }, 2000);
}

// ===========================================
// PERFORMANCE AND MONITORING
// ===========================================

/**
 * Setup performance monitoring for compact e-ink optimization
 */
function setupCompactPerformanceMonitoring() {
    // Monitor frame rate and performance metrics
    let frameCount = 0;
    let lastFrameTime = performance.now();

    function checkCompactPerformance() {
        frameCount++;
        const currentTime = performance.now();

        // Log performance metrics every 2 minutes (longer for compact)
        if (currentTime - lastFrameTime > 120000) {
            logCompactPerformanceMetrics();
            lastFrameTime = currentTime;
            frameCount = 0;
        }

        requestAnimationFrame(checkCompactPerformance);
    }

    // Start monitoring only if needed (can be disabled for battery saving)
    if (console.debug) {
        requestAnimationFrame(checkCompactPerformance);
    }
}

/**
 * Log performance metrics for compact display
 */
function logCompactPerformanceMetrics() {
    const metrics = {
        apiCalls: EInkCompactCalendar.performance.apiCallCount,
        domUpdates: EInkCompactCalendar.performance.domUpdateCount,
        truncations: EInkCompactCalendar.performance.truncationCount,
        contentTruncated: EInkCompactCalendar.state.contentTruncated,
        lastApiCall: EInkCompactCalendar.performance.lastApiCall ?
            new Date(EInkCompactCalendar.performance.lastApiCall).toLocaleTimeString() : 'Never',
        memoryUsage: performance.memory ?
            `${Math.round(performance.memory.usedJSHeapSize / 1024 / 1024)}MB` : 'Unknown'
    };

    console.log('Compact E-ink Performance Metrics:', metrics);
}

/**
 * Throttle function optimized for compact display
 * @param {Function} func - Function to throttle
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Throttled function
 */
function throttleCompact(func, wait) {
    let timeout;
    let previous = 0;

    return function() {
        const now = Date.now();
        const remaining = wait - (now - previous);
        const context = this;
        const args = arguments;

        if (remaining <= 0 || remaining > wait) {
            if (timeout) {
                clearTimeout(timeout);
                timeout = null;
            }
            previous = now;
            func.apply(context, args);
        } else if (!timeout) {
            timeout = setTimeout(() => {
                previous = Date.now();
                timeout = null;
                func.apply(context, args);
            }, remaining);
        }
    };
}

// ===========================================
// INITIALIZATION AND EXPORTS
// ===========================================

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeCompactEInkCalendar);
} else {
    // DOM already loaded
    initializeCompactEInkCalendar();
}

// Export functions for global access
console.log('Exporting compact e-ink functions globally...');

// Export compact-specific functions for global access
window.toggleTheme = toggleCompactTheme;
window.refresh = refreshCompact;
window.EInkCompactCalendar = EInkCompactCalendar;

// Override any existing calendarBot object
window.calendarBot = {
    toggleTheme: toggleCompactTheme,
    refresh: refreshCompact,
    getCurrentTheme: () => EInkCompactCalendar.state.currentTheme,
    isAutoRefreshEnabled: () => false, // Disabled for compact e-ink
    getMetrics: () => EInkCompactCalendar.performance,
    getState: () => EInkCompactCalendar.state,
    getConfig: () => EInkCompactCalendar.config,
    getTruncationInfo: () => ({
        enabled: EInkCompactCalendar.state.contentTruncated,
        count: EInkCompactCalendar.performance.truncationCount,
        rules: EInkCompactCalendar.config.truncation
    })
};

// Global debug access
window.compactEinkCalendarBot = {
    toggleTheme: toggleCompactTheme,
    refresh: refreshCompact,
    getMetrics: () => EInkCompactCalendar.performance,
    getState: () => EInkCompactCalendar.state,
    getConfig: () => EInkCompactCalendar.config,
    reinitialize: initializeCompactEInkCalendar,
    setupEventHandling: setupCompactEInkEventHandling,
    applyTruncation: applyContentTruncation,
    truncateText: truncateText,
    smartTruncateText: smartTruncateText,
    debug: () => {
        console.log('=== Compact E-ink Debug Report ===');
        console.log('State:', EInkCompactCalendar.state);
        console.log('Config:', EInkCompactCalendar.config);
        console.log('Performance:', EInkCompactCalendar.performance);
        console.log('=== End Debug Report ===');
    }
};

console.log('Compact E-ink Calendar Bot JavaScript module loaded and ready');
console.log('Compact functions exported:', {
    toggleTheme: typeof window.toggleTheme,
    refresh: typeof window.refresh,
    truncationEnabled: EInkCompactCalendar.state.contentTruncated
});