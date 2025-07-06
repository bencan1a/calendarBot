/* ===========================================
   E-INK RASPBERRY PI JAVASCRIPT MODULE
   Optimized for 800x480px e-ink displays
   =========================================== */

/**
 * E-ink Calendar Bot JavaScript Module
 * 
 * Optimized for Raspberry Pi e-ink displays with focus on:
 * - Minimal DOM manipulations to reduce e-ink refresh cycles
 * - Touch-optimized interactions for 44px minimum touch targets
 * - Battery-conscious event handling and reduced CPU usage
 * - Component-based interaction system
 * - Efficient content loading with partial e-ink refresh support
 */

// ===========================================
// GLOBAL STATE AND CONFIGURATION
// ===========================================

const EInkCalendar = {
    // Configuration
    config: {
        // E-ink display specifications
        displayWidth: 800,
        displayHeight: 480,
        
        // Performance settings optimized for e-ink
        refreshThrottle: 500, // Minimum time between API calls (ms)
        touchThrottle: 300,   // Minimum time between touch events (ms)
        swipeThreshold: 80,   // Increased threshold for more deliberate swipes
        
        // Battery conservation
        autoRefreshEnabled: false, // Disabled for e-ink to save battery
        animationsEnabled: false,  // Disabled for e-ink display
        transitionsEnabled: false, // Disabled for e-ink display
        
        // Touch targets (minimum 44px for accessibility)
        minTouchTarget: 44,
        
        // API endpoints
        endpoints: {
            navigate: '/api/navigate',
            refresh: '/api/refresh',
            theme: '/api/theme',
            status: '/api/status'
        }
    },
    
    // Runtime state
    state: {
        currentTheme: 'eink-rpi',
        isLoading: false,
        lastRefresh: null,
        lastNavigationAction: null,
        touchStartData: null,
        pendingUpdates: new Set(),
        initialized: false
    },
    
    // Event handlers storage
    handlers: new Map(),
    
    // Performance monitoring
    performance: {
        apiCallCount: 0,
        domUpdateCount: 0,
        lastApiCall: null
    }
};

// ===========================================
// INITIALIZATION AND LIFECYCLE
// ===========================================

/**
 * Initialize the e-ink calendar interface
 */
function initializeEInkCalendar() {
    if (EInkCalendar.state.initialized) {
        console.log('E-ink Calendar already initialized');
        return;
    }
    
    console.log('Initializing E-ink Calendar Bot for Raspberry Pi');
    
    // Detect and set theme
    detectAndSetTheme();
    
    // Setup optimized event handling
    setupEInkEventHandling();
    
    // Setup touch interactions
    setupTouchInteractions();
    
    // Setup keyboard navigation (accessibility)
    setupKeyboardNavigation();
    
    // Setup performance monitoring
    setupPerformanceMonitoring();
    
    // Disable problematic features for e-ink
    disableEInkProblematicFeatures();
    
    // Setup content update handlers
    setupContentUpdateHandling();
    
    // Mark as initialized
    EInkCalendar.state.initialized = true;
    
    console.log('E-ink Calendar initialization complete');
    logPerformanceMetrics();
}

/**
 * Detect current theme and configure accordingly
 */
function detectAndSetTheme() {
    const htmlElement = document.documentElement;
    const themeClasses = htmlElement.className.match(/theme-(\w+)/);
    
    if (themeClasses) {
        EInkCalendar.state.currentTheme = themeClasses[1];
    }
    
    // Ensure e-ink optimizations are applied
    if (EInkCalendar.state.currentTheme === 'eink-rpi') {
        applyEInkOptimizations();
    }
    
    console.log(`Theme detected: ${EInkCalendar.state.currentTheme}`);
}

/**
 * Apply e-ink specific optimizations to the DOM
 */
function applyEInkOptimizations() {
    // Disable all CSS transitions and animations
    const style = document.createElement('style');
    style.textContent = `
        .theme-eink-rpi * {
            transition: none !important;
            animation: none !important;
            animation-duration: 0s !important;
            animation-delay: 0s !important;
            transition-duration: 0s !important;
            transition-delay: 0s !important;
        }
    `;
    document.head.appendChild(style);
    
    // Set viewport meta for precise e-ink display
    const viewport = document.querySelector('meta[name="viewport"]');
    if (viewport) {
        viewport.setAttribute('content', 
            'width=800, height=480, initial-scale=1.0, user-scalable=no, ' +
            'minimal-ui, viewport-fit=cover'
        );
    }
    
    console.log('E-ink display optimizations applied');
}

/**
 * Disable features that are problematic for e-ink displays
 */
function disableEInkProblematicFeatures() {
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
    
    console.log('E-ink problematic features disabled');
}

// ===========================================
// EVENT HANDLING SYSTEM
// ===========================================

/**
 * Setup optimized event handling for e-ink displays
 */
function setupEInkEventHandling() {
    console.log('Setting up E-ink event handling...');
    
    // Navigation button handling with throttling
    const handleNavigation = throttle((action) => {
        console.log(`E-ink handleNavigation called with action: ${action}`);
        if (!EInkCalendar.state.isLoading) {
            navigate(action);
        } else {
            console.log('Navigation blocked - already loading');
        }
    }, EInkCalendar.config.refreshThrottle);
    
    // Add click listeners to specific navigation elements
    const setupNavigationListeners = () => {
        console.log('Setting up navigation listeners...');
        
        // Find all buttons with data-action attributes
        const actionButtons = document.querySelectorAll('button[data-action]');
        console.log(`Found ${actionButtons.length} action buttons`);
        
        actionButtons.forEach((button, index) => {
            const action = button.getAttribute('data-action');
            console.log(`Setting up button ${index + 1}: action="${action}", classes="${button.className}"`);
            
            // Remove any existing listeners to prevent duplicates
            button.removeEventListener('click', handleButtonClick);
            
            // Add new listener
            button.addEventListener('click', handleButtonClick, { passive: false });
        });
        
        // Also handle legacy buttons and class-based selection
        const legacyButtons = [
            { selector: '.nav-prev', action: 'prev' },
            { selector: '.nav-next', action: 'next' },
            { selector: '.nav-today', action: 'today' },
            { selector: '.theme-toggle', action: 'theme' }
        ];
        
        legacyButtons.forEach(({ selector, action }) => {
            const button = document.querySelector(selector);
            if (button && !button.hasAttribute('data-action')) {
                console.log(`Setting up legacy button: ${selector} -> ${action}`);
                button.setAttribute('data-action', action);
                button.removeEventListener('click', handleButtonClick);
                button.addEventListener('click', handleButtonClick, { passive: false });
            }
        });
    };
    
    // Unified button click handler
    const handleButtonClick = (event) => {
        console.log('Button clicked:', event.target);
        event.preventDefault();
        event.stopPropagation();
        
        const button = event.target.closest('button');
        const action = button?.getAttribute('data-action');
        
        console.log(`Button action: ${action}`);
        
        if (!action) {
            console.warn('No action found for button');
            return;
        }
        
        // Provide immediate visual feedback for e-ink
        showButtonFeedback(button, action);
        
        switch (action) {
            case 'prev':
                console.log('Executing prev navigation');
                handleNavigation('prev');
                break;
            case 'next':
                console.log('Executing next navigation');
                handleNavigation('next');
                break;
            case 'today':
                console.log('Executing today navigation');
                handleNavigation('today');
                break;
            case 'theme':
                console.log('Executing theme toggle');
                toggleTheme();
                break;
            default:
                console.warn(`Unknown action: ${action}`);
        }
    };
    
    // Show button press feedback optimized for e-ink
    const showButtonFeedback = (button, action) => {
        if (!button) return;
        
        // Store original styles
        const originalBorder = button.style.border;
        const originalBackground = button.style.background;
        
        // Apply feedback styling
        button.style.border = '3px solid #000';
        button.style.background = '#000';
        button.style.color = '#fff';
        
        // Show action feedback message
        const actionMessages = {
            'prev': '← Previous Day',
            'next': 'Next Day →',
            'today': '📅 Today',
            'theme': '🎨 Theme'
        };
        
        showEInkMessage(actionMessages[action] || action, 'info');
        
        // Restore original styling after feedback period
        setTimeout(() => {
            button.style.border = originalBorder;
            button.style.background = originalBackground;
            button.style.color = '';
        }, 200);
    };
    
    // Setup listeners immediately
    setupNavigationListeners();
    
    // Also setup listeners after DOM mutations (for dynamic content)
    const observer = new MutationObserver((mutations) => {
        let shouldSetupListeners = false;
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                for (let node of mutation.addedNodes) {
                    if (node.nodeType === 1 && // Element node
                        (node.querySelector &&
                         (node.querySelector('button[data-action]') ||
                          node.querySelector('button.nav-prev') ||
                          node.querySelector('button.nav-next') ||
                          node.querySelector('button.theme-toggle') ||
                          node.tagName === 'BUTTON'))) {
                        shouldSetupListeners = true;
                        break;
                    }
                }
            }
        });
        
        if (shouldSetupListeners) {
            console.log('DOM mutation detected, re-setting up navigation listeners');
            setTimeout(setupNavigationListeners, 100); // Small delay to ensure DOM is ready
        }
    });
    
    // Observe the entire document for navigation button changes
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Store handler for cleanup if needed
    EInkCalendar.handlers.set('navigation', handleNavigation);
    
    console.log('E-ink event handling setup complete');
}

/**
 * Setup touch interactions optimized for e-ink displays
 */
function setupTouchInteractions() {
    let touchData = {
        startX: 0,
        startY: 0,
        startTime: 0,
        isSwipe: false
    };
    
    // Touch start handler
    document.addEventListener('touchstart', (event) => {
        if (event.touches.length === 1) {
            const touch = event.touches[0];
            touchData = {
                startX: touch.clientX,
                startY: touch.clientY,
                startTime: Date.now(),
                isSwipe: false
            };
            EInkCalendar.state.touchStartData = touchData;
        }
    }, { passive: true });
    
    // Touch move handler - detect swipe intent
    document.addEventListener('touchmove', (event) => {
        if (event.touches.length === 1 && EInkCalendar.state.touchStartData) {
            const touch = event.touches[0];
            const deltaX = Math.abs(touch.clientX - touchData.startX);
            const deltaY = Math.abs(touch.clientY - touchData.startY);
            
            // Mark as swipe if horizontal movement is significant
            if (deltaX > 20 && deltaX > deltaY) {
                touchData.isSwipe = true;
            }
        }
    }, { passive: true });
    
    // Touch end handler with swipe detection
    const handleTouchEnd = throttle((event) => {
        if (!EInkCalendar.state.touchStartData) return;
        
        const touch = event.changedTouches[0];
        const deltaX = touch.clientX - touchData.startX;
        const deltaY = touch.clientY - touchData.startY;
        const deltaTime = Date.now() - touchData.startTime;
        
        // Swipe detection with stricter criteria for e-ink
        if (touchData.isSwipe && 
            Math.abs(deltaX) > EInkCalendar.config.swipeThreshold &&
            Math.abs(deltaX) > Math.abs(deltaY) * 2 && // More horizontal than vertical
            deltaTime < 1000) { // Within reasonable time
            
            if (deltaX > 0) {
                // Swipe right - go to previous day
                navigate('prev');
            } else {
                // Swipe left - go to next day  
                navigate('next');
            }
        }
        
        // Reset touch data
        EInkCalendar.state.touchStartData = null;
    }, EInkCalendar.config.touchThrottle);
    
    document.addEventListener('touchend', handleTouchEnd, { passive: true });
    
    // Prevent double-tap zoom on iOS
    let lastTouchEnd = 0;
    document.addEventListener('touchend', (event) => {
        const now = Date.now();
        if (now - lastTouchEnd <= 300) {
            event.preventDefault();
        }
        lastTouchEnd = now;
    }, { passive: false });
    
    console.log('Touch interactions setup complete');
}

/**
 * Setup keyboard navigation for accessibility
 */
function setupKeyboardNavigation() {
    document.addEventListener('keydown', (event) => {
        // Only handle navigation if not in an input
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            return;
        }
        
        const navigationKeys = ['ArrowLeft', 'ArrowRight', ' ', 'Home', 'End', 'r', 'R', 't', 'T'];
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
        }
    });
    
    console.log('Keyboard navigation setup complete');
}

// ===========================================
// NAVIGATION FUNCTIONS
// ===========================================

/**
 * Navigate to a different date/view
 * @param {string} action - Navigation action (prev, next, today, etc.)
 */
async function navigate(action) {
    console.log(`=== E-ink Navigation Started ===`);
    console.log(`Action: ${action}`);
    console.log(`Current loading state: ${EInkCalendar.state.isLoading}`);
    console.log(`API endpoint: ${EInkCalendar.config.endpoints.navigate}`);
    
    if (EInkCalendar.state.isLoading) {
        console.log('Navigation blocked - already loading');
        showEInkMessage('Please wait...', 'info');
        return;
    }
    
    console.log(`Setting loading state to true`);
    EInkCalendar.state.isLoading = true;
    EInkCalendar.state.lastNavigationAction = action;
    
    try {
        // Show minimal loading indicator
        console.log('Showing loading indicator');
        showEInkLoadingIndicator(`Navigating ${action}...`);
        
        // Track performance
        const startTime = performance.now();
        EInkCalendar.performance.apiCallCount++;
        EInkCalendar.performance.lastApiCall = Date.now();
        
        console.log('Making API request...');
        const requestBody = JSON.stringify({ action: action });
        console.log(`Request body: ${requestBody}`);
        
        const response = await fetch(EInkCalendar.config.endpoints.navigate, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: requestBody
        });
        
        console.log(`Response status: ${response.status}`);
        console.log(`Response ok: ${response.ok}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        console.log('Parsing response JSON...');
        const data = await response.json();
        console.log('Response data:', {
            success: data.success,
            hasHtml: !!data.html,
            error: data.error,
            htmlLength: data.html ? data.html.length : 0
        });
        
        if (data.success && data.html) {
            console.log('Updating content...');
            // Update content efficiently for e-ink
            await updateEInkContent(data.html);
            
            // Provide minimal feedback
            console.log('Showing navigation feedback');
            showEInkNavigationFeedback(action);
            
            // Log performance
            const duration = performance.now() - startTime;
            console.log(`Navigation completed successfully in ${duration.toFixed(2)}ms`);
            showEInkSuccessMessage(`${action} navigation complete`);
        } else {
            console.error('Navigation failed - server response:', data);
            showEInkErrorMessage(data.error || 'Navigation failed');
        }
        
    } catch (error) {
        console.error('Navigation error:', error);
        console.error('Error stack:', error.stack);
        showEInkErrorMessage(`Navigation error: ${error.message}`);
    } finally {
        console.log('Cleaning up navigation...');
        hideEInkLoadingIndicator();
        EInkCalendar.state.isLoading = false;
        console.log(`=== E-ink Navigation Completed ===`);
    }
}

/**
 * Refresh calendar data
 */
async function refresh() {
    if (EInkCalendar.state.isLoading) {
        console.log('Refresh blocked - already loading');
        return;
    }
    
    console.log('E-ink refresh requested');
    EInkCalendar.state.isLoading = true;
    
    try {
        showEInkLoadingIndicator('Refreshing...');
        
        // Track performance
        EInkCalendar.performance.apiCallCount++;
        EInkCalendar.performance.lastApiCall = Date.now();
        
        const response = await fetch(EInkCalendar.config.endpoints.refresh, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        const data = await response.json();
        
        if (data.success && data.html) {
            await updateEInkContent(data.html);
            EInkCalendar.state.lastRefresh = Date.now();
            showEInkSuccessMessage('Data refreshed');
        } else {
            showEInkErrorMessage('Refresh failed');
        }
        
    } catch (error) {
        console.error('Refresh error:', error);
        showEInkErrorMessage('Refresh error');
    } finally {
        hideEInkLoadingIndicator();
        EInkCalendar.state.isLoading = false;
    }
}

/**
 * Toggle theme (primarily for testing - e-ink prefers consistent theme)
 */
async function toggleTheme() {
    console.log('E-ink theme toggle requested');
    
    try {
        const response = await fetch(EInkCalendar.config.endpoints.theme, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        });
        
        const data = await response.json();
        
        if (data.success) {
            EInkCalendar.state.currentTheme = data.theme;
            
            // Update HTML class efficiently
            const htmlElement = document.documentElement;
            htmlElement.className = htmlElement.className.replace(/theme-\w+/, `theme-${data.theme}`);
            
            // Re-apply e-ink optimizations if needed
            if (data.theme === 'eink-rpi') {
                applyEInkOptimizations();
            }
            
            console.log(`Theme changed to: ${data.theme}`);
        }
        
    } catch (error) {
        console.error('Theme toggle error:', error);
    }
}

// ===========================================
// CONTENT UPDATE SYSTEM
// ===========================================

/**
 * Setup content update handling optimized for e-ink
 */
function setupContentUpdateHandling() {
    // Monitor for dynamic content changes
    const observer = new MutationObserver((mutations) => {
        let hasSignificantChanges = false;
        
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                hasSignificantChanges = true;
            }
        });
        
        if (hasSignificantChanges) {
            EInkCalendar.performance.domUpdateCount++;
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
    
    console.log('Content update monitoring initialized');
}

/**
 * Update page content efficiently for e-ink displays
 * @param {string} newHTML - New HTML content
 */
async function updateEInkContent(newHTML) {
    const startTime = performance.now();
    
    try {
        // Parse the new HTML
        const parser = new DOMParser();
        const newDoc = parser.parseFromString(newHTML, 'text/html');
        
        // Update only specific sections to minimize e-ink refreshes
        const sectionsToUpdate = [
            '.calendar-title',
            '.status-line',
            '.calendar-content',
            '.nav-date-display'
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
        
        // Track performance
        EInkCalendar.performance.domUpdateCount++;
        const duration = performance.now() - startTime;
        
        console.log(`Updated ${updatedSections} sections in ${duration.toFixed(2)}ms`);
        
    } catch (error) {
        console.error('Error updating e-ink content:', error);
        throw error;
    }
}

// ===========================================
// USER FEEDBACK SYSTEM (E-INK OPTIMIZED)
// ===========================================

/**
 * Show minimal loading indicator for e-ink
 * @param {string} message - Loading message
 */
function showEInkLoadingIndicator(message = 'Loading...') {
    let indicator = document.getElementById('eink-loading-indicator');
    
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'eink-loading-indicator';
        indicator.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: #000;
            color: #fff;
            padding: 8px 12px;
            font-size: 14px;
            font-family: monospace;
            z-index: 1000;
            border: 2px solid #000;
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
function hideEInkLoadingIndicator() {
    const indicator = document.getElementById('eink-loading-indicator');
    if (indicator) {
        indicator.style.display = 'none';
    }
}

/**
 * Show navigation feedback optimized for e-ink
 * @param {string} action - Navigation action performed
 */
function showEInkNavigationFeedback(action) {
    // For e-ink displays, we provide minimal, non-animated feedback
    const dateDisplay = document.querySelector('.nav-date-display');
    if (dateDisplay) {
        // Briefly highlight the date display to show something changed
        const originalBorder = dateDisplay.style.border;
        dateDisplay.style.border = '2px solid #000';
        
        setTimeout(() => {
            dateDisplay.style.border = originalBorder;
        }, 300);
    }
    
    console.log(`Navigation feedback: ${action}`);
}

/**
 * Show error message for e-ink displays
 * @param {string} message - Error message
 */
function showEInkErrorMessage(message) {
    showEInkMessage(message, 'error');
}

/**
 * Show success message for e-ink displays  
 * @param {string} message - Success message
 */
function showEInkSuccessMessage(message) {
    showEInkMessage(message, 'success');
}

/**
 * Show message optimized for e-ink displays
 * @param {string} message - Message to show
 * @param {string} type - Message type (error, success, info)
 */
function showEInkMessage(message, type = 'info') {
    const messageEl = document.createElement('div');
    messageEl.style.cssText = `
        position: fixed;
        bottom: 70px;
        left: 50%;
        transform: translateX(-50%);
        padding: 8px 16px;
        font-size: 14px;
        font-family: monospace;
        text-align: center;
        z-index: 1000;
        border: 2px solid #000;
        max-width: 300px;
        ${type === 'error' ? 'background: #000; color: #fff;' : 'background: #fff; color: #000;'}
    `;
    
    messageEl.textContent = message;
    document.body.appendChild(messageEl);
    
    // Remove after delay (no fade for e-ink)
    setTimeout(() => {
        if (messageEl.parentNode) {
            messageEl.parentNode.removeChild(messageEl);
        }
    }, 3000);
}

// ===========================================
// PERFORMANCE AND MONITORING
// ===========================================

/**
 * Setup performance monitoring for e-ink optimization
 */
function setupPerformanceMonitoring() {
    // Monitor frame rate and performance metrics
    let frameCount = 0;
    let lastFrameTime = performance.now();
    
    function checkPerformance() {
        frameCount++;
        const currentTime = performance.now();
        
        // Log performance metrics every minute
        if (currentTime - lastFrameTime > 60000) {
            logPerformanceMetrics();
            lastFrameTime = currentTime;
            frameCount = 0;
        }
        
        requestAnimationFrame(checkPerformance);
    }
    
    // Start monitoring only if needed (can be disabled for battery saving)
    if (console.debug) {
        requestAnimationFrame(checkPerformance);
    }
}

/**
 * Log performance metrics
 */
function logPerformanceMetrics() {
    const metrics = {
        apiCalls: EInkCalendar.performance.apiCallCount,
        domUpdates: EInkCalendar.performance.domUpdateCount,
        lastApiCall: EInkCalendar.performance.lastApiCall ? 
            new Date(EInkCalendar.performance.lastApiCall).toLocaleTimeString() : 'Never',
        memoryUsage: performance.memory ? 
            `${Math.round(performance.memory.usedJSHeapSize / 1024 / 1024)}MB` : 'Unknown'
    };
    
    console.log('E-ink Performance Metrics:', metrics);
}

/**
 * Throttle function to limit API calls and DOM updates
 * @param {Function} func - Function to throttle
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Throttled function
 */
function throttle(func, wait) {
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
// COMPONENT INTERACTION SYSTEM
// ===========================================

/**
 * Handle interactions on event cards with data attributes
 */
function setupEventCardInteractions() {
    const container = document.querySelector('.calendar-content');
    if (!container) return;
    
    // Event delegation for event cards
    container.addEventListener('click', (event) => {
        const eventCard = event.target.closest('[data-event-id]');
        if (eventCard) {
            const eventId = eventCard.getAttribute('data-event-id');
            handleEventCardClick(eventId, eventCard);
        }
    }, { passive: true });
    
    console.log('Event card interactions setup complete');
}

/**
 * Handle click on event card
 * @param {string} eventId - Event ID
 * @param {Element} cardElement - Card DOM element
 */
function handleEventCardClick(eventId, cardElement) {
    // For e-ink displays, provide minimal interaction
    console.log(`Event card clicked: ${eventId}`);
    
    // Could implement modal or detail view here
    // For now, just provide visual feedback
    const originalBorder = cardElement.style.border;
    cardElement.style.border = '3px solid #000';
    
    setTimeout(() => {
        cardElement.style.border = originalBorder;
    }, 300);
}

// ===========================================
// INITIALIZATION AND EXPORTS
// ===========================================

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeEInkCalendar);
} else {
    // DOM already loaded
    initializeEInkCalendar();
}

// Export functions for global access (maintaining compatibility)
// Override any existing functions from app.js
console.log('Exporting e-ink navigation functions globally...');

// Force override of global functions
window.navigate = navigate;
window.toggleTheme = toggleTheme;
window.refresh = refresh;
window.EInkCalendar = EInkCalendar;

// Override any existing calendarBot object
window.calendarBot = {
    navigate,
    toggleTheme,
    refresh,
    getCurrentTheme: () => EInkCalendar.state.currentTheme,
    isAutoRefreshEnabled: () => false, // Disabled for e-ink
    getMetrics: () => EInkCalendar.performance,
    getState: () => EInkCalendar.state,
    getConfig: () => EInkCalendar.config
};

// Comprehensive debug function
function debugNavigationSetup() {
    console.log('=== E-ink Navigation Debug Report ===');
    
    // Check for buttons
    const buttons = document.querySelectorAll('button');
    console.log(`Total buttons found: ${buttons.length}`);
    
    buttons.forEach((btn, i) => {
        console.log(`Button ${i + 1}:`, {
            classes: btn.className,
            dataAction: btn.getAttribute('data-action'),
            onclick: btn.onclick ? 'has onclick' : 'no onclick',
            text: btn.textContent.trim(),
            disabled: btn.disabled
        });
    });
    
    // Check navigation elements specifically
    const navElements = [
        { selector: '.nav-prev', expected: 'Previous button' },
        { selector: '.nav-next', expected: 'Next button' },
        { selector: '.nav-today', expected: 'Today button' },
        { selector: '.theme-toggle', expected: 'Theme button' },
        { selector: 'button[data-action="prev"]', expected: 'Data-action prev' },
        { selector: 'button[data-action="next"]', expected: 'Data-action next' },
        { selector: 'button[data-action="today"]', expected: 'Data-action today' },
        { selector: 'button[data-action="theme"]', expected: 'Data-action theme' }
    ];
    
    navElements.forEach(({ selector, expected }) => {
        const element = document.querySelector(selector);
        console.log(`${expected}: ${element ? 'FOUND' : 'MISSING'} (${selector})`);
    });
    
    // Check global functions
    console.log('Global functions:', {
        navigate: typeof window.navigate,
        toggleTheme: typeof window.toggleTheme,
        refresh: typeof window.refresh
    });
    
    // Check state
    console.log('E-ink state:', EInkCalendar.state);
    console.log('E-ink config:', EInkCalendar.config);
    
    console.log('=== End Debug Report ===');
}

// Global debug access
window.einkCalendarBot = {
    navigate,
    toggleTheme,
    refresh,
    getMetrics: () => EInkCalendar.performance,
    getState: () => EInkCalendar.state,
    getConfig: () => EInkCalendar.config,
    reinitialize: initializeEInkCalendar,
    setupEventHandling: setupEInkEventHandling,
    debug: debugNavigationSetup
};

console.log('E-ink Calendar Bot JavaScript module loaded and ready');
console.log('Global functions exported:', {
    navigate: typeof window.navigate,
    toggleTheme: typeof window.toggleTheme,
    refresh: typeof window.refresh
});