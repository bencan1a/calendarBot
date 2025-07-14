/* CalendarBot Whats-Next-View Layout JavaScript */

// Global state
let currentTheme = 'eink';
let autoRefreshInterval = null;
let autoRefreshEnabled = true;
let countdownInterval = null;
let currentMeeting = null;
let upcomingMeetings = [];
let lastDataUpdate = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeWhatsNextView();
});

/**
 * Initialize the Whats-Next-View layout
 * Sets up all functionality and starts the countdown system
 */
function initializeWhatsNextView() {
    console.log('Whats-Next-View: Initializing layout');

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
    
    // Initial data load
    loadMeetingData();

    console.log(`Whats-Next-View: Initialized with theme: ${currentTheme}`);
}

/**
 * Navigation button click handlers (following 3x4 pattern)
 */
function setupNavigationButtons() {
    document.addEventListener('click', function(event) {
        const element = event.target.closest('[data-action]');
        if (element) {
            const action = element.getAttribute('data-action');
            event.preventDefault();
            
            switch(action) {
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

    console.log('Whats-Next-View: Navigation handlers setup complete');
}

/**
 * Keyboard navigation (following 3x4 pattern)
 */
function setupKeyboardNavigation() {
    document.addEventListener('keydown', function(event) {
        const navigationKeys = ['r', 'R', 't', 'T', 'l', 'L', ' '];
        if (navigationKeys.includes(event.key)) {
            event.preventDefault();
        }

        switch(event.key) {
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
 */
function setupAutoRefresh() {
    const refreshInterval = 60000; // 60 seconds

    if (autoRefreshEnabled) {
        autoRefreshInterval = setInterval(function() {
            refreshSilent();
        }, refreshInterval);

        console.log(`Whats-Next-View: Auto-refresh enabled: ${refreshInterval/1000}s interval`);
    }
}

/**
 * Mobile/touch enhancements (following 3x4 pattern)
 */
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
        const swipeThreshold = 50;
        const swipeDistance = touchEndX - touchStartX;

        if (Math.abs(swipeDistance) > swipeThreshold) {
            if (swipeDistance > 0) {
                // Swipe right - refresh
                refresh();
            } else {
                // Swipe left - refresh
                refresh();
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

/**
 * Setup countdown timer system
 */
function setupCountdownSystem() {
    // Start countdown updates every second
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
    
    countdownInterval = setInterval(function() {
        updateCountdown();
        checkMeetingTransitions();
    }, 1000);

    console.log('Whats-Next-View: Countdown system initialized');
}

/**
 * Setup meeting detection and filtering
 */
function setupMeetingDetection() {
    // This will be called after data loads to find the next meeting
    console.log('Whats-Next-View: Meeting detection setup complete');
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

    console.log('Whats-Next-View: Accessibility features setup complete');
}

/**
 * Load meeting data from CalendarBot API
 */
async function loadMeetingData() {
    try {
        showLoadingIndicator('Loading meetings...');

        const response = await fetch('/api/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();

        if (data.success && data.html) {
            // Parse the HTML to extract meeting data
            parseMeetingDataFromHTML(data.html);
            updatePageContent(data.html);
            detectCurrentMeeting();
            updateCountdown();
            lastDataUpdate = new Date();
        } else {
            showErrorState('Failed to load meeting data');
        }

    } catch (error) {
        console.error('Whats-Next-View: Failed to load meeting data', error);
        showErrorState('Network error occurred');
    } finally {
        hideLoadingIndicator();
    }
}

/**
 * Parse meeting data from HTML response
 * @param {string} html - HTML content from server
 */
function parseMeetingDataFromHTML(html) {
    try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Extract current and upcoming events from the HTML
        // This integrates with CalendarBot's existing event structure
        const currentEvents = doc.querySelectorAll('.current-event');
        const upcomingEvents = doc.querySelectorAll('.upcoming-event');
        
        upcomingMeetings = [];
        
        // Process current events
        currentEvents.forEach(event => {
            const meeting = extractMeetingFromElement(event);
            if (meeting) {
                upcomingMeetings.push(meeting);
            }
        });
        
        // Process upcoming events
        upcomingEvents.forEach(event => {
            const meeting = extractMeetingFromElement(event);
            if (meeting) {
                upcomingMeetings.push(meeting);
            }
        });
        
        // Sort by start time
        upcomingMeetings.sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
        
        console.log(`Whats-Next-View: Parsed ${upcomingMeetings.length} meetings`);
        
    } catch (error) {
        console.error('Whats-Next-View: Failed to parse meeting data', error);
    }
}

/**
 * Extract meeting data from DOM element
 * @param {Element} element - DOM element containing meeting data
 * @returns {Object|null} Meeting object or null if parsing fails
 */
function extractMeetingFromElement(element) {
    try {
        const titleElement = element.querySelector('.event-title');
        const timeElement = element.querySelector('.event-time');
        const locationElement = element.querySelector('.event-location');
        
        if (!titleElement || !timeElement) {
            return null;
        }
        
        const title = titleElement.textContent.trim();
        const timeText = timeElement.textContent.trim();
        
        // Parse time text to extract start and end times
        const timeMatch = timeText.match(/(\d{1,2}:\d{2}\s*(?:AM|PM)?)\s*-\s*(\d{1,2}:\d{2}\s*(?:AM|PM)?)/i);
        if (!timeMatch) {
            return null;
        }
        
        const today = new Date();
        const startTime = parseTimeString(timeMatch[1], today);
        const endTime = parseTimeString(timeMatch[2], today);
        
        return {
            id: `meeting-${Date.now()}-${Math.random()}`,
            title: title,
            start_time: startTime.toISOString(),
            end_time: endTime.toISOString(),
            location: locationElement ? locationElement.textContent.trim() : '',
            description: ''
        };
        
    } catch (error) {
        console.error('Whats-Next-View: Failed to extract meeting from element', error);
        return null;
    }
}

/**
 * Parse time string into Date object
 * @param {string} timeStr - Time string (e.g., "2:30 PM")
 * @param {Date} baseDate - Base date to use
 * @returns {Date} Parsed date object
 */
function parseTimeString(timeStr, baseDate) {
    const cleanTime = timeStr.trim();
    const date = new Date(baseDate);
    
    // Handle 12-hour format
    const match = cleanTime.match(/(\d{1,2}):(\d{2})\s*(AM|PM)?/i);
    if (match) {
        let hours = parseInt(match[1]);
        const minutes = parseInt(match[2]);
        const ampm = match[3] ? match[3].toUpperCase() : '';
        
        if (ampm === 'PM' && hours !== 12) {
            hours += 12;
        } else if (ampm === 'AM' && hours === 12) {
            hours = 0;
        }
        
        date.setHours(hours, minutes, 0, 0);
    }
    
    return date;
}

/**
 * Detect the current/next meeting
 */
function detectCurrentMeeting() {
    const now = new Date();
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
    
    console.log('Whats-Next-View: Current meeting detected:', currentMeeting ? currentMeeting.title : 'None');
    updateMeetingDisplay();
}

/**
 * Update the countdown display
 */
function updateCountdown() {
    const countdownElement = document.querySelector('.countdown-time');
    const countdownLabel = document.querySelector('.countdown-label');
    const countdownUnits = document.querySelector('.countdown-units');
    
    if (!countdownElement || !currentMeeting) {
        return;
    }
    
    const now = new Date();
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
    
    // Calculate hours and minutes
    const hours = Math.floor(timeRemaining / (1000 * 60 * 60));
    const minutes = Math.floor((timeRemaining % (1000 * 60 * 60)) / (1000 * 60));
    
    // Format display
    let displayText;
    let unitsText;
    
    if (hours > 0) {
        displayText = `${hours}:${minutes.toString().padStart(2, '0')}`;
        unitsText = hours === 1 ? 'Hour' : 'Hours';
    } else {
        displayText = minutes.toString();
        unitsText = minutes === 1 ? 'Minute' : 'Minutes';
    }
    
    // Update DOM
    countdownElement.textContent = displayText;
    if (countdownLabel) countdownLabel.textContent = labelText;
    if (countdownUnits) countdownUnits.textContent = unitsText;
    
    // Add urgent class if less than 15 minutes
    if (timeRemaining < 15 * 60 * 1000) {
        countdownElement.classList.add('urgent');
    } else {
        countdownElement.classList.remove('urgent');
    }
    
    // Announce milestone times to screen readers
    if (minutes === 15 || minutes === 5 || minutes === 1) {
        announceToScreenReader(`${minutes} ${minutes === 1 ? 'minute' : 'minutes'} until ${currentMeeting.title}`);
    }
}

/**
 * Update meeting display in the UI
 */
function updateMeetingDisplay() {
    const content = document.querySelector('.whats-next-content');
    if (!content) return;
    
    if (!currentMeeting) {
        showEmptyState();
        return;
    }
    
    // Generate meeting display HTML
    const nextMeetings = upcomingMeetings.slice(1, 4); // Show next 3 meetings
    
    const html = `
        <div class="countdown-container">
            <div class="countdown-label">Next Meeting</div>
            <div class="countdown-time">--</div>
            <div class="countdown-units">Minutes</div>
        </div>
        
        <div class="meeting-card current">
            <div class="meeting-title">${escapeHtml(currentMeeting.title)}</div>
            <div class="meeting-time">${formatMeetingTime(currentMeeting.start_time, currentMeeting.end_time)}</div>
            ${currentMeeting.location ? `<div class="meeting-location">${escapeHtml(currentMeeting.location)}</div>` : ''}
            ${currentMeeting.description ? `<div class="meeting-description">${escapeHtml(currentMeeting.description)}</div>` : ''}
        </div>
        
        ${nextMeetings.length > 0 ? `
            <div class="next-meetings">
                <div class="next-meetings-title">Coming Up</div>
                ${nextMeetings.map(meeting => `
                    <div class="next-meeting-item">
                        <div class="next-meeting-info">
                            <div class="next-meeting-title">${escapeHtml(meeting.title)}</div>
                        </div>
                        <div class="next-meeting-time">${formatMeetingTime(meeting.start_time, meeting.end_time)}</div>
                    </div>
                `).join('')}
            </div>
        ` : ''}
    `;
    
    content.innerHTML = html;
    setupAccessibility(); // Re-setup accessibility after DOM update
}

/**
 * Check for meeting transitions
 */
function checkMeetingTransitions() {
    if (!currentMeeting) return;
    
    const now = new Date();
    const meetingEnd = new Date(currentMeeting.end_time);
    
    // Check if current meeting has ended
    if (now > meetingEnd) {
        console.log('Whats-Next-View: Meeting ended, transitioning to next');
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
function formatMeetingTime(startTime, endTime) {
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
 * Show empty state when no meetings
 */
function showEmptyState() {
    const content = document.querySelector('.whats-next-content');
    if (!content) return;
    
    content.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">📅</div>
            <div class="empty-state-title">No Upcoming Meetings</div>
            <div class="empty-state-message">You're all caught up! No meetings scheduled for now.</div>
        </div>
    `;
}

/**
 * Show error state
 * @param {string} message - Error message to display
 */
function showErrorState(message) {
    const content = document.querySelector('.whats-next-content');
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
    console.log(`Whats-Next-View: Navigation action: ${action}`);

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
            parseMeetingDataFromHTML(data.html);
            updatePageContent(data.html);
            detectCurrentMeeting();
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

/**
 * Theme switching (following 3x4 pattern)
 */
async function toggleTheme() {
    console.log('Whats-Next-View: Toggling theme');

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
            console.log(`Theme changed to: ${currentTheme}`);
        } else {
            console.error('Theme toggle failed');
        }

    } catch (error) {
        console.error('Theme toggle error:', error);
    }
}

/**
 * Layout switching (following 3x4 pattern)
 */
async function cycleLayout() {
    console.log('Whats-Next-View: Cycling layout');

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

/**
 * Data refresh (following 3x4 pattern)
 */
async function refresh() {
    console.log('Whats-Next-View: Manual refresh requested');
    await loadMeetingData();
    showSuccessMessage('Meetings refreshed');
}

/**
 * Silent refresh for auto-refresh (following 3x4 pattern)
 */
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
            parseMeetingDataFromHTML(data.html);
            updatePageContent(data.html);
            detectCurrentMeeting();
            console.log('Whats-Next-View: Auto-refresh completed');
        }

    } catch (error) {
        console.error('Silent refresh error:', error);
    }
}

/**
 * Update page content (following 3x4 pattern)
 */
function updatePageContent(newHTML) {
    const parser = new DOMParser();
    const newDoc = parser.parseFromString(newHTML, 'text/html');

    // Update header elements
    const sectionsToUpdate = [
        '.header-title',
        '.whats-next-header'
    ];

    sectionsToUpdate.forEach(selector => {
        const oldElement = document.querySelector(selector);
        const newElement = newDoc.querySelector(selector);

        if (oldElement && newElement) {
            oldElement.innerHTML = newElement.innerHTML;
        }
    });

    // Update page title
    if (newDoc.title) {
        document.title = newDoc.title;
    }

    // Ensure theme class is maintained
    document.documentElement.className = document.documentElement.className.replace(/theme-\w+/, `theme-${currentTheme}`);
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

// Export functions for global access
window.navigate = navigate;
window.toggleTheme = toggleTheme;
window.cycleLayout = cycleLayout;
window.refresh = refresh;
window.getCurrentTheme = () => currentTheme;
window.isAutoRefreshEnabled = () => autoRefreshEnabled;

// Whats-Next-View specific exports
window.updateCountdown = updateCountdown;
window.detectCurrentMeeting = detectCurrentMeeting;
window.loadMeetingData = loadMeetingData;

// UI feedback function exports
window.showLoadingIndicator = showLoadingIndicator;
window.hideLoadingIndicator = hideLoadingIndicator;
window.showErrorMessage = showErrorMessage;
window.showSuccessMessage = showSuccessMessage;
window.showMessage = showMessage;

// Meeting display function exports
window.updateMeetingDisplay = updateMeetingDisplay;
window.formatMeetingTime = formatMeetingTime;
window.escapeHtml = escapeHtml;

// Accessibility function exports
window.setupAccessibility = setupAccessibility;
window.announceToScreenReader = announceToScreenReader;
window.getMeetingAriaLabel = getMeetingAriaLabel;

// Debug helper
window.whatsNextView = {
    getCurrentMeeting: () => currentMeeting,
    getUpcomingMeetings: () => upcomingMeetings,
    getLastUpdate: () => lastDataUpdate,
    forceRefresh: refresh,
    toggleAutoRefresh: () => {
        autoRefreshEnabled = !autoRefreshEnabled;
        if (autoRefreshEnabled) {
            setupAutoRefresh();
        } else if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = null;
        }
        return autoRefreshEnabled;
    }
};

console.log('Whats-Next-View JavaScript loaded and ready');