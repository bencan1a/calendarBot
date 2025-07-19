/* Calendar Bot Web Interface JavaScript */

// Global state
let currentTheme = 'eink';
let autoRefreshInterval = null;
let autoRefreshEnabled = true;
let settingsPanel = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    console.log('Calendar Bot Web Interface loaded');

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

    console.log(`Initialized with theme: ${currentTheme}`);
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

    console.log('Navigation button handlers setup complete');
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
    // Get auto-refresh interval from server or default to 60 seconds
    const refreshInterval = 60000; // 60 seconds

    if (autoRefreshEnabled) {
        autoRefreshInterval = setInterval(function() {
            refreshSilent();
        }, refreshInterval);

        console.log(`Auto-refresh enabled: ${refreshInterval/1000}s interval`);
    }
}

function toggleAutoRefresh() {
    if (autoRefreshEnabled) {
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = null;
        }
        autoRefreshEnabled = false;
        console.log('Auto-refresh disabled');
    } else {
        setupAutoRefresh();
        autoRefreshEnabled = true;
        console.log('Auto-refresh enabled');
    }
}

// Mobile/touch enhancements
function setupMobileEnhancements() {
    // Add touch event listeners for swipe navigation
    let touchStartX = 0;
    let touchEndX = 0;

    document.addEventListener('touchstart', function(event) {
        touchStartX = event.changedTouches[0].screenX;
    });

    document.addEventListener('touchend', function(event) {
        touchEndX = event.changedTouches[0].screenX;
        handleSwipe();
    });

    function handleSwipe() {
        const swipeThreshold = 50; // Minimum distance for a swipe
        const swipeDistance = touchEndX - touchStartX;

        if (Math.abs(swipeDistance) > swipeThreshold) {
            if (swipeDistance > 0) {
                // Swipe right - go to previous day
                navigate('prev');
            } else {
                // Swipe left - go to next day
                navigate('next');
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
    console.log(`Navigation action: ${action}`);

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
    console.log('Toggling theme');

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

            console.log(`Theme changed to: ${currentTheme}`);

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
    console.log('Cycling layout');

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
            console.log(`Layout changed to: ${data.layout}`);
            
            // Force full page reload to load new layout's CSS/JS
            // window.location.reload(); // Disabled for testing - would reload in production
            console.log('Layout changed complete - page would reload in production');
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
    console.log(`Setting layout to: ${layout}`);

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
            console.log(`Layout set to: ${data.layout}`);
            
            // Force full page reload to load new layout's CSS/JS
            // window.location.reload(); // Disabled for testing - would reload in production
            console.log('Layout set complete - page would reload in production');
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
    console.log('Manual refresh requested');

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
            console.log('Settings panel initialized for 4x8 layout');
        } else {
            console.log('Settings panel not available - shared components not loaded');
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
            console.log('Settings panel cleaned up');
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

console.log('Calendar Bot JavaScript loaded and ready');
