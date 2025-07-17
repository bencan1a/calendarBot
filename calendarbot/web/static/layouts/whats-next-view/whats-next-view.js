/* CalendarBot Whats-Next-View Layout JavaScript */

// Global state
let currentTheme = 'eink';
let autoRefreshInterval = null;
let autoRefreshEnabled = true;
let countdownInterval = null;
let currentMeeting = null;
let upcomingMeetings = [];
let lastDataUpdate = null;

// Debug mode state
let debugModeEnabled = false;
let debugData = {
    customTimeEnabled: false,
    customDate: '',
    customTime: '',
    customAmPm: 'AM'
};
let debugPanelVisible = false;

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
            case 'd':
            case 'D':
                toggleDebugMode();
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

        // Prepare request body with custom time if debug mode is enabled
        const requestBody = {};
        if (debugModeEnabled && debugData.customTimeEnabled) {
            const customTime = getCurrentTime();
            requestBody.debug_time = customTime.toISOString();
            console.log('DEBUG API: Sending custom time to backend:', requestBody.debug_time);
        }

        const response = await fetch('/api/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody),
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
        console.log('DIAGNOSTIC PARSE: parseMeetingDataFromHTML() called');
        console.log('DIAGNOSTIC PARSE: Input HTML length:', html.length);
        console.log('DIAGNOSTIC PARSE: Input HTML preview:', html.substring(0, 500) + '...');
        
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        console.log('DIAGNOSTIC PARSE: DOM parsed successfully');
        
        // Extract current and upcoming events from the HTML
        // This integrates with CalendarBot's existing event structure
        const currentEvents = doc.querySelectorAll('.current-event');
        const upcomingEvents = doc.querySelectorAll('.upcoming-event');
        
        console.log('DIAGNOSTIC PARSE: Current events found:', currentEvents.length);
        console.log('DIAGNOSTIC PARSE: Upcoming events found:', upcomingEvents.length);
        
        // DIAGNOSTIC: Check what CSS classes actually exist in the HTML
        const allElements = doc.querySelectorAll('*');
        const classNames = new Set();
        allElements.forEach(el => {
            if (el.className && typeof el.className === 'string') {
                el.className.split(' ').forEach(cls => cls.trim() && classNames.add(cls));
            }
        });
        console.log('DIAGNOSTIC PARSE: All CSS classes found in HTML:', Array.from(classNames).sort());
        
        // DIAGNOSTIC: Look for any event-related content
        const eventTitles = doc.querySelectorAll('.event-title');
        const eventTimes = doc.querySelectorAll('.event-time');
        const eventLocations = doc.querySelectorAll('.event-location');
        console.log('DIAGNOSTIC PARSE: Event titles found:', eventTitles.length);
        console.log('DIAGNOSTIC PARSE: Event times found:', eventTimes.length);
        console.log('DIAGNOSTIC PARSE: Event locations found:', eventLocations.length);
        
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
        
        // WHATS-NEXT-VIEW FIX: Also look for WhatsNextRenderer's section-based structure
        const currentSections = doc.querySelectorAll('section.current-events');
        const upcomingSections = doc.querySelectorAll('section.upcoming-events');
        
        console.log('DIAGNOSTIC PARSE: Found current sections:', currentSections.length);
        console.log('DIAGNOSTIC PARSE: Found upcoming sections:', upcomingSections.length);
        
        // Process events within current sections
        currentSections.forEach(section => {
            // Look for event elements within the section
            const sectionEvents = section.querySelectorAll('.current-event, .event-item');
            console.log('DIAGNOSTIC PARSE: Events in current section:', sectionEvents.length);
            sectionEvents.forEach(event => {
                const meeting = extractMeetingFromElement(event);
                if (meeting) {
                    upcomingMeetings.push(meeting);
                    console.log('DIAGNOSTIC PARSE: Added meeting from current section:', meeting.title);
                }
            });
        });
        
        // Process events within upcoming sections
        upcomingSections.forEach(section => {
            // Look for event elements within the section
            const sectionEvents = section.querySelectorAll('.upcoming-event, .event-item');
            console.log('DIAGNOSTIC PARSE: Events in upcoming section:', sectionEvents.length);
            sectionEvents.forEach(event => {
                const meeting = extractMeetingFromElement(event);
                if (meeting) {
                    upcomingMeetings.push(meeting);
                    console.log('DIAGNOSTIC PARSE: Added meeting from upcoming section:', meeting.title);
                }
            });
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
        // Handle both .event-time (current events) and .event-details (upcoming events)
        const timeElement = element.querySelector('.event-time') || element.querySelector('.event-details');
        const locationElement = element.querySelector('.event-location');
        
        if (!titleElement || !timeElement) {
            console.log('DIAGNOSTIC PARSE: Missing title or time element in:', element.outerHTML.substring(0, 200));
            return null;
        }
        
        const title = titleElement.textContent.trim();
        const timeText = timeElement.textContent.trim();
        
        console.log('DIAGNOSTIC PARSE: Extracted title:', title);
        console.log('DIAGNOSTIC PARSE: Extracted timeText:', timeText);
        
        // Parse time text to extract start and end times
        const timeMatch = timeText.match(/(\d{1,2}:\d{2}\s*(?:AM|PM)?)\s*-\s*(\d{1,2}:\d{2}\s*(?:AM|PM)?)/i);
        if (!timeMatch) {
            return null;
        }
        
        // Backend now handles debug time correctly, so we use the current time consistently
        // whether in debug mode or not - getCurrentTime() returns debug time when active
        const baseDate = getCurrentTime();
        const startTime = parseTimeString(timeMatch[1], baseDate);
        const endTime = parseTimeString(timeMatch[2], baseDate);
        
        console.log(`DEBUG MEETING PARSE: Title: ${title}, Time text: ${timeText}, Base date: ${baseDate.toISOString()}`);
        console.log(`DEBUG MEETING PARSE: Parsed start: ${startTime.toISOString()}, end: ${endTime.toISOString()}`);
        
        // No adjustment needed - backend provides correct meeting times for debug time
        let adjustedStartTime = startTime;
        let adjustedEndTime = endTime;
        
        return {
            id: `meeting-${Date.now()}-${Math.random()}`,
            title: title,
            start_time: adjustedStartTime.toISOString(),
            end_time: adjustedEndTime.toISOString(),
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
        
        // Handle day boundary: if parsed time is before current time, assume it's for tomorrow
        // BUT: only do this if we're not in debug mode with a custom time override
        const now = getCurrentTime();
        const realNow = new Date(); // Always use real time for this comparison
        
        // Only adjust date for "tomorrow" logic if we're using real time or the custom time is close to real time
        if (!debugModeEnabled || !debugData.customTimeEnabled) {
            // Normal operation: if time is in the past, assume it's for tomorrow
            if (date < now) {
                date.setDate(date.getDate() + 1);
            }
        } else {
            // Debug mode: be more careful about date adjustments
            // Only adjust if the meeting time is more than 12 hours in the past relative to custom time
            const timeDiff = now.getTime() - date.getTime();
            if (timeDiff > 12 * 60 * 60 * 1000) { // More than 12 hours in the past
                date.setDate(date.getDate() + 1);
            }
        }
    }
    
    return date;
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
    
    console.log('Whats-Next-View: Current meeting detected:', currentMeeting ? currentMeeting.title : 'None');
    updateMeetingDisplay();
}

// ===========================================
// P0 TIME GAP DISPLAY FUNCTIONS
// ===========================================

/**
 * Calculate time gap between current time and next meeting
 * @param {Date} currentTime - Current time
 * @param {Date} nextMeetingTime - Next meeting start time
 * @returns {number} Time gap in milliseconds
 */
function calculateTimeGap(currentTime, nextMeetingTime) {
    if (!currentTime || !nextMeetingTime) {
        return 0;
    }
    
    const gap = nextMeetingTime.getTime() - currentTime.getTime();
    return Math.max(0, gap); // Ensure non-negative
}

/**
 * Format time gap for human-readable display
 * @param {number} timeGapMs - Time gap in milliseconds
 * @returns {string} Formatted time string ("23 minutes", "1 hour 15 minutes")
 */
function formatTimeGap(timeGapMs) {
    if (timeGapMs <= 0) {
        return "0 minutes";
    }
    
    const totalMinutes = Math.floor(timeGapMs / (1000 * 60));
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    
    if (hours === 0) {
        return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`;
    } else if (minutes === 0) {
        return `${hours} ${hours === 1 ? 'hour' : 'hours'}`;
    } else {
        return `${hours} ${hours === 1 ? 'hour' : 'hours'} ${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`;
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
 */
function updateCountdown() {
    const countdownElement = document.querySelector('.countdown-time');
    const countdownLabel = document.querySelector('.countdown-label');
    const countdownUnits = document.querySelector('.countdown-units');
    const countdownContainer = document.querySelector('.countdown-container');
    
    if (!countdownElement || !currentMeeting) {
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
    
    // P0 Feature: Calculate time gap using new functions
    const timeGap = calculateTimeGap(now, meetingStart);
    const boundaryAlert = checkBoundaryAlert(timeGap);
    
    // P0 Feature: Apply boundary alert styling
    if (countdownContainer) {
        // Remove existing time gap classes
        countdownContainer.classList.remove('time-gap-critical', 'time-gap-tight', 'time-gap-comfortable');
        
        // Add appropriate boundary alert class
        if (boundaryAlert.cssClass) {
            countdownContainer.classList.add(boundaryAlert.cssClass);
        }
        
        // Add/remove urgent class
        if (boundaryAlert.urgent) {
            countdownContainer.classList.add('urgent');
        } else {
            countdownContainer.classList.remove('urgent');
        }
    }
    
    // P0 Feature: Display formatted time gap for upcoming meetings
    let displayText;
    let unitsText;
    
    if (now < meetingStart) {
        // Upcoming meeting - use P0 formatTimeGap function
        const formattedGap = formatTimeGap(timeGap);
        displayText = formattedGap.split(' ')[0]; // Get the number part
        unitsText = formattedGap.substring(formattedGap.indexOf(' ') + 1); // Get the units part
        
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
    
    // Update DOM
    countdownElement.textContent = displayText;
    if (countdownLabel) countdownLabel.textContent = labelText;
    if (countdownUnits) countdownUnits.textContent = unitsText;
    
    // Add urgent class if less than 15 minutes (legacy support)
    if (timeRemaining < 15 * 60 * 1000) {
        countdownElement.classList.add('urgent');
    } else {
        countdownElement.classList.remove('urgent');
    }
    
    // P0 Feature: Enhanced boundary alert announcements
    const totalMinutes = Math.floor(timeGap / (1000 * 60));
    if (totalMinutes === 10 || totalMinutes === 5 || totalMinutes === 2 || totalMinutes === 1) {
        const announcement = boundaryAlert.type === 'critical'
            ? `WRAP UP NOW - ${totalMinutes} ${totalMinutes === 1 ? 'minute' : 'minutes'} until ${currentMeeting.title}`
            : `${totalMinutes} ${totalMinutes === 1 ? 'minute' : 'minutes'} until ${currentMeeting.title}`;
        announceToScreenReader(announcement);
    }
}

/**
 * Update meeting display in the UI with P1 4-zone layout structure
 */
function updateMeetingDisplay() {
    console.log('DEBUG MODE: updateMeetingDisplay() called');
    
    const content = document.querySelector('.calendar-content');
    console.log('DEBUG MODE: Container check in updateMeetingDisplay:', {
        contentExists: !!content,
        contentHTML: content ? content.innerHTML.substring(0, 100) + '...' : 'CONTAINER NOT FOUND',
        documentReady: document.readyState,
        bodyExists: !!document.body
    });
    
    if (!content) {
        console.error('DEBUG MODE: CRITICAL ERROR - .calendar-content container not found in updateMeetingDisplay()');
        console.error('DEBUG MODE: This is the root cause - updateMeetingDisplay() returns early without creating DOM elements');
        console.error('DEBUG MODE: Check if the HTML layout includes the .calendar-content container');
        return;
    }
    
    if (!currentMeeting) {
        showEmptyState();
        return;
    }
    
    const now = getCurrentTime();
    const meetingStart = new Date(currentMeeting.start_time);
    const meetingEnd = new Date(currentMeeting.end_time);
    
    // Determine meeting status
    const isCurrentMeeting = now >= meetingStart && now <= meetingEnd;
    const statusText = isCurrentMeeting ? 'In Progress' : 'Upcoming';
    
    // P1 Feature: Organize content into 3-zone layout structure
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
            <div class="meeting-card current">
                <div class="meeting-title text-primary">${escapeHtml(currentMeeting.title)}</div>
                <div class="meeting-time text-secondary">${formatMeetingTime(currentMeeting.start_time, currentMeeting.end_time)}</div>
                ${currentMeeting.location ? `<div class="meeting-location text-supporting">${escapeHtml(currentMeeting.location)}</div>` : ''}
                ${currentMeeting.description ? `<div class="meeting-description text-small">${escapeHtml(currentMeeting.description)}</div>` : ''}
            </div>
        </div>
        
        <!-- Zone 4 (60px): Additional context -->
        <div class="layout-zone-4">
            <div class="context-info text-center">
                <div class="context-message text-caption">${getContextMessage(isCurrentMeeting)}</div>
            </div>
        </div>
    `;
    
    content.innerHTML = html;
    setupAccessibility(); // Re-setup accessibility after DOM update
}

/**
 * Format last update time for display
 * @returns {string} Formatted last update time
 */
function formatLastUpdate() {
    if (!lastDataUpdate) {
        return 'Never';
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
 * Show empty state when no meetings using 3-zone layout
 */
function showEmptyState() {
    const content = document.querySelector('.calendar-content');
    if (!content) return;
    
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
                <div class="last-update text-caption">Updated: ${formatLastUpdate()}</div>
            </div>
        </div>
        
        <!-- Zone 4 (60px): Context -->
        <div class="layout-zone-4">
            <div class="context-info text-center">
                <div class="context-message text-caption">No meetings scheduled</div>
            </div>
        </div>
    `;
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
        // Prepare request body with custom time if debug mode is enabled
        const requestBody = {};
        if (debugModeEnabled && debugData.customTimeEnabled) {
            const customTime = getCurrentTime();
            requestBody.debug_time = customTime.toISOString();
            console.log('DEBUG API: Sending custom time to backend (silent refresh):', requestBody.debug_time);
        }

        const response = await fetch('/api/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody),
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
    console.log('=== DIAGNOSTIC: updatePageContent() START ===');
    console.log('DIAGNOSTIC: newHTML length:', newHTML.length);
    console.log('DIAGNOSTIC: newHTML contains .calendar-content:', newHTML.includes('calendar-content'));
    console.log('DIAGNOSTIC: Function called at:', new Date().toISOString());
    
    const parser = new DOMParser();
    const newDoc = parser.parseFromString(newHTML, 'text/html');

    // Check what's in the new HTML
    const newCalendarContent = newDoc.querySelector('.calendar-content');
    console.log('DEBUG DIAGNOSIS: New HTML has .calendar-content:', !!newCalendarContent);
    if (newCalendarContent) {
        console.log('DEBUG DIAGNOSIS: New .calendar-content innerHTML length:', newCalendarContent.innerHTML.length);
    }

    // Check what's in current DOM
    const currentCalendarContent = document.querySelector('.calendar-content');
    console.log('DEBUG DIAGNOSIS: Current DOM has .calendar-content:', !!currentCalendarContent);

    // Update header elements
    const sectionsToUpdate = [
        '.header-title',
        '.whats-next-header'
    ];

    console.log('DEBUG DIAGNOSIS: Sections being updated:', sectionsToUpdate);

    sectionsToUpdate.forEach(selector => {
        const oldElement = document.querySelector(selector);
        const newElement = newDoc.querySelector(selector);

        console.log(`DEBUG DIAGNOSIS: Updating ${selector} - old exists: ${!!oldElement}, new exists: ${!!newElement}`);

        if (oldElement && newElement) {
            oldElement.innerHTML = newElement.innerHTML;
        }
    });

    // FIX: Also update .calendar-content from the API response
    // DIAGNOSTIC: Variables already declared above - reusing them to fix redeclaration bug
    console.log('DIAGNOSTIC: About to update .calendar-content container');
    console.log('DIAGNOSTIC: currentCalendarContent exists:', !!currentCalendarContent);
    console.log('DIAGNOSTIC: newCalendarContent exists:', !!newCalendarContent);
    
    if (newCalendarContent) {
        console.log('DIAGNOSTIC: newCalendarContent found, attempting update...');
        if (currentCalendarContent) {
            // Update existing .calendar-content
            currentCalendarContent.innerHTML = newCalendarContent.innerHTML;
            console.log('DIAGNOSTIC: ✓ Successfully updated existing .calendar-content with new content');
            console.log('DIAGNOSTIC: ✓ CRITICAL FIX APPLIED - DOM now contains calendar content');
        } else {
            // Create .calendar-content if it doesn't exist
            console.log('DIAGNOSTIC: Creating new .calendar-content container...');
            const main = document.createElement('main');
            main.className = 'calendar-content';
            main.innerHTML = newCalendarContent.innerHTML;
            
            // Insert after header or at beginning of body
            const header = document.querySelector('header');
            if (header && header.nextSibling) {
                document.body.insertBefore(main, header.nextSibling);
            } else {
                document.body.appendChild(main);
            }
            console.log('DIAGNOSTIC: ✓ Created new .calendar-content container with content');
            console.log('DIAGNOSTIC: ✓ CRITICAL FIX APPLIED - DOM now has calendar container');
        }
    } else {
        console.log('DIAGNOSTIC: ✗ No .calendar-content found in API response - this indicates backend issue');
    }

    // Verify the fix worked
    const verifyCalendarContent = document.querySelector('.calendar-content');
    console.log('DEBUG DIAGNOSIS: After update - .calendar-content exists in DOM:', !!verifyCalendarContent);
    if (verifyCalendarContent) {
        console.log('DEBUG DIAGNOSIS: .calendar-content innerHTML length:', verifyCalendarContent.innerHTML.length);
    }

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

// P1 Phase 2 function exports
window.formatLastUpdate = formatLastUpdate;
window.getContextMessage = getContextMessage;

// Accessibility function exports
window.setupAccessibility = setupAccessibility;
window.announceToScreenReader = announceToScreenReader;
window.getMeetingAriaLabel = getMeetingAriaLabel;

// ===========================================
// TIME OVERRIDE FUNCTIONALITY
// ===========================================

/**
 * Get current time - either real time or custom debug time
 * @returns {Date} Current time (real or debug override)
 */
function getCurrentTime() {
    if (debugModeEnabled && debugData.customTimeEnabled) {
        if (debugData.customDate && debugData.customTime) {
            try {
                // Parse custom date and time
                const dateStr = debugData.customDate;
                const timeStr = debugData.customTime;
                const ampm = debugData.customAmPm;
                
                // Parse time first
                const timeParts = timeStr.split(':');
                if (timeParts.length === 2) {
                    let hours = parseInt(timeParts[0]);
                    const minutes = parseInt(timeParts[1]);
                    
                    // Convert to 24-hour format
                    if (ampm === 'PM' && hours !== 12) {
                        hours += 12;
                    } else if (ampm === 'AM' && hours === 12) {
                        hours = 0;
                    }
                    
                    // Create date object with explicit local time (avoiding UTC conversion)
                    const dateParts = dateStr.split('-');
                    const customDate = new Date(
                        parseInt(dateParts[0]), // year
                        parseInt(dateParts[1]) - 1, // month (0-indexed)
                        parseInt(dateParts[2]), // day
                        hours, // hours
                        minutes, // minutes
                        0, // seconds
                        0 // milliseconds
                    );
                    
                    console.log(`DEBUG TIME: Using custom time: ${customDate.toISOString()}`);
                    console.log(`DEBUG TIME: Custom date input: ${dateStr} ${timeStr} ${ampm}`);
                    console.log(`DEBUG TIME: Parsed as local time: ${customDate.toString()}`);
                    console.log(`DEBUG TIME DIAGNOSTIC: Local hours: ${customDate.getHours()}, UTC hours: ${customDate.getUTCHours()}`);
                    console.log(`DEBUG TIME DIAGNOSTIC: Timezone offset minutes: ${customDate.getTimezoneOffset()}`);
                    console.log(`DEBUG TIME DIAGNOSTIC: Time values - Local: ${customDate.getHours()}:${customDate.getMinutes()}, UTC: ${customDate.getUTCHours()}:${customDate.getUTCMinutes()}`);
                    return customDate;
                }
            } catch (error) {
                console.error('DEBUG TIME: Error parsing custom time, falling back to real time:', error);
            }
        }
    }
    
    // Return real time
    return new Date();
}

// ===========================================
// DATE/TIME PICKER FUNCTIONALITY
// ===========================================

/**
 * Toggle time override on/off
 */
function toggleTimeOverride() {
    debugData.customTimeEnabled = !debugData.customTimeEnabled;
    
    const section = document.getElementById('time-override-section');
    const preview = document.getElementById('time-preview');
    
    if (section) {
        if (debugData.customTimeEnabled) {
            section.classList.remove('disabled');
        } else {
            section.classList.add('disabled');
        }
    }
    
    if (preview) {
        if (debugData.customTimeEnabled) {
            preview.classList.remove('disabled');
        } else {
            preview.classList.add('disabled');
        }
    }
    
    updateTimePreview();
    console.log('DEBUG TIME: Time override toggled:', debugData.customTimeEnabled);
}

/**
 * Update time preview display
 */
function updateTimePreview() {
    const previewText = document.getElementById('time-preview-text');
    if (!previewText) return;
    
    if (!debugData.customTimeEnabled) {
        previewText.textContent = '--:-- -- ----/--/--';
        return;
    }
    
    try {
        const dateInput = document.getElementById('debug-custom-date');
        const hourInput = document.getElementById('debug-custom-hour');
        const minuteInput = document.getElementById('debug-custom-minute');
        const ampmSelect = document.getElementById('debug-custom-ampm');
        
        if (!dateInput || !hourInput || !minuteInput || !ampmSelect) {
            previewText.textContent = 'Error: Missing inputs';
            return;
        }
        
        const date = dateInput.value;
        const hour = parseInt(hourInput.value) || 12;
        const minute = parseInt(minuteInput.value) || 0;
        const ampm = ampmSelect.value;
        
        // Update debugData
        debugData.customDate = date;
        debugData.customTime = `${hour}:${minute.toString().padStart(2, '0')}`;
        debugData.customAmPm = ampm;
        
        // Format preview
        const formattedTime = `${hour}:${minute.toString().padStart(2, '0')} ${ampm}`;
        const formattedDate = date ? new Date(date).toLocaleDateString() : 'Invalid Date';
        
        previewText.textContent = `${formattedTime} ${formattedDate}`;
        
    } catch (error) {
        console.error('DEBUG TIME: Error updating preview:', error);
        previewText.textContent = 'Error updating preview';
    }
}

/**
 * Reset time override to current time
 */
function resetTimeOverride() {
    const now = new Date(); // Use real time for reset, not getCurrentTime()
    const currentDate = now.toISOString().split('T')[0];
    const currentAmPm = now.getHours() >= 12 ? 'PM' : 'AM';
    const displayHours = now.getHours() % 12 || 12;
    const displayMinutes = now.getMinutes();
    
    // Update input fields
    const dateInput = document.getElementById('debug-custom-date');
    const hourInput = document.getElementById('debug-custom-hour');
    const minuteInput = document.getElementById('debug-custom-minute');
    const ampmSelect = document.getElementById('debug-custom-ampm');
    
    if (dateInput) dateInput.value = currentDate;
    if (hourInput) hourInput.value = displayHours;
    if (minuteInput) minuteInput.value = displayMinutes;
    if (ampmSelect) ampmSelect.value = currentAmPm;
    
    // Update debugData
    debugData.customDate = currentDate;
    debugData.customTime = `${displayHours}:${displayMinutes.toString().padStart(2, '0')}`;
    debugData.customAmPm = currentAmPm;
    
    updateTimePreview();
    
    console.log('DEBUG TIME: Time override reset to current time');
    showSuccessMessage('Time reset to current time');
}

// ===========================================
// DEBUG MODE FUNCTIONALITY
// ===========================================

/**
 * Toggle debug mode on/off
 */
function toggleDebugMode() {
    debugModeEnabled = !debugModeEnabled;
    
    if (debugModeEnabled) {
        console.log('==== DEBUG MODE ACTIVATION ====');
        console.log('DEBUG MODE: Activating debug mode for What\'s Next View');
        console.log('DEBUG MODE: Current state before activation:', {
            debugModeEnabled: false,
            debugPanelVisible: debugPanelVisible,
            currentMeeting: currentMeeting ? currentMeeting.title : 'None',
            upcomingMeetingsCount: upcomingMeetings.length
        });
        
        createDebugPanel();
        showDebugPanel();
        // addDebugModeIndicator(); // Removed per user request - no blue indicator box
        
        console.log('DEBUG MODE: Successfully enabled - Press D to toggle off');
        console.log('DEBUG MODE: Debug panel created and indicator added');
        console.log('DEBUG MODE: Use the debug panel to set test meeting data');
        console.log('====================================');
        
        announceToScreenReader('Debug mode enabled - Debug panel is now available');
        showSuccessMessage('Debug mode activated - Use panel to set test data');
    } else {
        console.log('==== DEBUG MODE DEACTIVATION ====');
        console.log('DEBUG MODE: Deactivating debug mode');
        console.log('DEBUG MODE: Current debug state:', getDebugState());
        
        hideDebugPanel();
        // removeDebugModeIndicator(); // Removed per user request - no blue indicator box
        clearDebugValues(); // Clear any active debug data
        
        console.log('DEBUG MODE: Successfully disabled');
        console.log('DEBUG MODE: Debug panel hidden and indicator removed');
        console.log('DEBUG MODE: Normal meeting data restored');
        console.log('======================================');
        
        announceToScreenReader('Debug mode disabled - Normal operation restored');
        showSuccessMessage('Debug mode deactivated - Normal data restored');
    }
}

/**
 * Create debug panel HTML structure
 */
function createDebugPanel() {
    console.log('DEBUG PANEL: Creating debug panel...');
    
    let debugPanel = document.getElementById('debug-panel');
    
    if (!debugPanel) {
        debugPanel = document.createElement('div');
        debugPanel.id = 'debug-panel';
        debugPanel.className = 'debug-panel hidden';
        
        // Get current date for default value
        const today = new Date();
        const currentDate = today.toISOString().split('T')[0];
        const currentTime = today.toTimeString().slice(0, 5);
        const currentAmPm = today.getHours() >= 12 ? 'PM' : 'AM';
        const displayHours = today.getHours() % 12 || 12;
        const displayMinutes = today.getMinutes().toString().padStart(2, '0');
        
        console.log('DEBUG PANEL: Function availability check:', {
            toggleTimeOverride: typeof window.toggleTimeOverride,
            updateTimePreview: typeof window.updateTimePreview,
            applyDebugValues: typeof window.applyDebugValues,
            clearDebugValues: typeof window.clearDebugValues,
            resetTimeOverride: typeof window.resetTimeOverride
        });
        
        debugPanel.innerHTML = `
            <div class="debug-panel-header">
                <h3>Debug Mode - What's Next View</h3>
                <button class="debug-close-btn" onclick="toggleDebugMode()">×</button>
            </div>
            <div class="debug-panel-content">
                <div class="debug-controls">
                    <!-- Time Override Section -->
                    <div class="time-override-section ${debugData.customTimeEnabled ? '' : 'disabled'}" id="time-override-section">
                        <div class="checkbox-field">
                            <input type="checkbox" id="debug-time-enabled" ${debugData.customTimeEnabled ? 'checked' : ''}>
                            <label for="debug-time-enabled">Enable Current Time Override</label>
                        </div>
                        
                        <div class="debug-field">
                            <label for="debug-custom-date">Date:</label>
                            <input type="date" id="debug-custom-date" value="${debugData.customDate || currentDate}">
                        </div>
                        
                        <div class="debug-field">
                            <label>Time:</label>
                            <div class="time-picker-container">
                                <input type="number" id="debug-custom-hour" placeholder="HH" value="${debugData.customTime ? debugData.customTime.split(':')[0] : displayHours}" min="1" max="12">
                                <label>:</label>
                                <input type="number" id="debug-custom-minute" placeholder="MM" value="${debugData.customTime ? debugData.customTime.split(':')[1] : displayMinutes}" min="0" max="59">
                                <select id="debug-custom-ampm">
                                    <option value="AM" ${debugData.customAmPm === 'AM' ? 'selected' : ''}>AM</option>
                                    <option value="PM" ${debugData.customAmPm === 'PM' ? 'selected' : ''}>PM</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="time-preview ${debugData.customTimeEnabled ? '' : 'disabled'}" id="time-preview">
                            Custom Time: <span id="time-preview-text">--:-- -- ----/--/--</span>
                        </div>
                    </div>
                    
                    <div class="debug-actions">
                        <button class="debug-apply-btn" id="debug-apply-btn">Apply Time Override</button>
                        <button class="debug-clear-btn" id="debug-clear-btn">Clear Debug</button>
                        <button class="debug-reset-btn" id="debug-reset-btn">Reset Time</button>
                    </div>
                </div>
                <div class="debug-status">
                    <div class="debug-status-indicator">
                        Debug mode: <span class="debug-active">ACTIVE</span>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(debugPanel);
        console.log('DEBUG PANEL: HTML structure added to DOM');
        
        // Manually attach event listeners instead of using inline handlers
        setupDebugPanelEventListeners();
        
        // Initialize time preview
        updateTimePreview();
        console.log('DEBUG PANEL: Event listeners attached and time preview initialized');
    }
}

/**
 * Setup event listeners for debug panel controls
 */
function setupDebugPanelEventListeners() {
    console.log('DEBUG PANEL: Setting up event listeners...');
    
    // Time override checkbox
    const timeEnabledCheckbox = document.getElementById('debug-time-enabled');
    if (timeEnabledCheckbox) {
        timeEnabledCheckbox.addEventListener('change', function() {
            console.log('DEBUG PANEL: Time override checkbox clicked');
            toggleTimeOverride();
        });
        console.log('DEBUG PANEL: Time override checkbox listener attached');
    } else {
        console.error('DEBUG PANEL: Time override checkbox not found!');
    }
    
    // Date input
    const dateInput = document.getElementById('debug-custom-date');
    if (dateInput) {
        dateInput.addEventListener('change', function() {
            console.log('DEBUG PANEL: Date input changed');
            updateTimePreview();
        });
        console.log('DEBUG PANEL: Date input listener attached');
    }
    
    // Hour input
    const hourInput = document.getElementById('debug-custom-hour');
    if (hourInput) {
        hourInput.addEventListener('change', function() {
            console.log('DEBUG PANEL: Hour input changed');
            updateTimePreview();
        });
        console.log('DEBUG PANEL: Hour input listener attached');
    }
    
    // Minute input
    const minuteInput = document.getElementById('debug-custom-minute');
    if (minuteInput) {
        minuteInput.addEventListener('change', function() {
            console.log('DEBUG PANEL: Minute input changed');
            updateTimePreview();
        });
        console.log('DEBUG PANEL: Minute input listener attached');
    }
    
    // AM/PM select
    const ampmSelect = document.getElementById('debug-custom-ampm');
    if (ampmSelect) {
        ampmSelect.addEventListener('change', function() {
            console.log('DEBUG PANEL: AM/PM select changed');
            updateTimePreview();
        });
        console.log('DEBUG PANEL: AM/PM select listener attached');
    }
    
    // Apply button
    const applyBtn = document.getElementById('debug-apply-btn');
    if (applyBtn) {
        applyBtn.addEventListener('click', function() {
            console.log('DEBUG PANEL: Apply button clicked');
            applyDebugValues();
        });
        console.log('DEBUG PANEL: Apply button listener attached');
    }
    
    // Clear button
    const clearBtn = document.getElementById('debug-clear-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            console.log('DEBUG PANEL: Clear button clicked');
            clearDebugValues();
        });
        console.log('DEBUG PANEL: Clear button listener attached');
    }
    
    // Reset button
    const resetBtn = document.getElementById('debug-reset-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            console.log('DEBUG PANEL: Reset button clicked');
            resetTimeOverride();
        });
        console.log('DEBUG PANEL: Reset button listener attached');
    }
    
    console.log('DEBUG PANEL: All event listeners setup complete');
}

/**
 * Show debug panel
 */
function showDebugPanel() {
    const debugPanel = document.getElementById('debug-panel');
    if (debugPanel) {
        debugPanel.classList.remove('hidden');
        debugPanelVisible = true;
        
        // Focus on the time override checkbox
        setTimeout(() => {
            const firstInput = debugPanel.querySelector('#debug-time-enabled');
            if (firstInput) {
                firstInput.focus();
            }
        }, 100);
    }
}

/**
 * Hide debug panel
 */
function hideDebugPanel() {
    const debugPanel = document.getElementById('debug-panel');
    if (debugPanel) {
        debugPanel.classList.add('hidden');
        debugPanelVisible = false;
    }
}

/**
 * Apply debug values and refresh display
 */
function applyDebugValues() {
    console.log('==== TIME OVERRIDE APPLICATION ====');
    console.log('DEBUG MODE: Starting time override application process');
    
    // Validate time override settings if enabled
    if (debugData.customTimeEnabled) {
        if (!debugData.customDate || !debugData.customTime) {
            console.warn('DEBUG MODE: Validation failed - Custom date and time are required when time override is enabled');
            showErrorMessage('Custom date and time are required');
            return;
        }
        
        console.log('DEBUG MODE: Time override validated:', {
            customDate: debugData.customDate,
            customTime: debugData.customTime,
            customAmPm: debugData.customAmPm
        });
    }
    
    // Refresh real calendar data with the custom time simulation
    console.log('DEBUG MODE: Loading real meeting data with time override...');
    loadMeetingData().then(() => {
        console.log('DEBUG MODE: Real meeting data loaded successfully with custom time');
        console.log('DEBUG MODE: All meeting calculations will now use custom time via getCurrentTime()');
        
        const currentTime = getCurrentTime();
        console.log('DEBUG MODE: Current effective time:', currentTime.toISOString());
        
        showSuccessMessage('Time override applied - Using real calendar data');
        announceToScreenReader('Time override applied, displaying real meetings with custom time');
    }).catch((error) => {
        console.error('DEBUG MODE: Error loading meeting data:', error);
        showErrorMessage('Failed to load meeting data');
    });
    
    console.log('DEBUG MODE: Time override application completed');
    console.log('==========================================');
}

/**
 * Clear debug values and restore normal operation
 */
function clearDebugValues() {
    console.log('==== DEBUG VALUES CLEARING ====');
    console.log('DEBUG MODE: Starting debug values clearing process');
    
    // Store previous state for logging
    const previousState = {
        debugData: { ...debugData },
        currentMeeting: currentMeeting ? currentMeeting.title : 'None',
        upcomingMeetingsCount: upcomingMeetings.length,
        debugModeEnabled: debugModeEnabled
    };
    
    console.log('DEBUG MODE: Previous state before clearing:', previousState);
    
    // Reset time override to disabled
    debugData.customTimeEnabled = false;
    debugData.customDate = '';
    debugData.customTime = '';
    debugData.customAmPm = 'AM';
    
    console.log('DEBUG MODE: Reset time override settings to default values');
    
    // Update time override UI if it exists
    const timeEnabledCheckbox = document.getElementById('debug-time-enabled');
    const timeSection = document.getElementById('time-override-section');
    const timePreview = document.getElementById('time-preview');
    
    if (timeEnabledCheckbox) {
        timeEnabledCheckbox.checked = false;
        console.log('DEBUG MODE: Unchecked time override checkbox');
    }
    
    if (timeSection) {
        timeSection.classList.add('disabled');
        console.log('DEBUG MODE: Disabled time override section');
    }
    
    if (timePreview) {
        timePreview.classList.add('disabled');
        console.log('DEBUG MODE: Disabled time preview section');
    }
    
    // Update time preview display
    updateTimePreview();
    
    // Reload real meeting data with normal time
    console.log('DEBUG MODE: Initiating real meeting data reload with normal time...');
    loadMeetingData().then(() => {
        console.log('DEBUG MODE: Real meeting data reload completed');
        console.log('DEBUG MODE: New meeting state after reload:', {
            currentMeeting: currentMeeting ? currentMeeting.title : 'None',
            upcomingMeetingsCount: upcomingMeetings.length
        });
    }).catch((error) => {
        console.error('DEBUG MODE: Error during meeting data reload:', error);
    });
    
    // Log state changes
    console.log('DEBUG MODE: State change summary:', {
        before: previousState,
        after: {
            debugData: debugData,
            currentMeeting: 'Pending reload',
            upcomingMeetingsCount: 'Pending reload',
            debugModeEnabled: debugModeEnabled
        }
    });
    
    console.log('DEBUG MODE: Successfully cleared debug values and initiated normal operation restore');
    console.log('DEBUG MODE: UX will be updated when real meeting data loads');
    console.log('=====================================');
    
    showSuccessMessage('Debug cleared, restored normal time and data');
    announceToScreenReader('Debug mode cleared, normal time and meeting data restored');
}

/**
 * Set debug values via API (for programmatic testing)
 * @param {Object} values - Debug values object
 * @param {boolean} values.customTimeEnabled - Whether time override is enabled
 * @param {string} values.customDate - Custom date (YYYY-MM-DD format)
 * @param {string} values.customTime - Custom time (HH:MM format)
 * @param {string} values.customAmPm - AM or PM
 */
function setDebugValues(values) {
    if (typeof values !== 'object' || !values) {
        console.error('Debug values must be an object');
        return false;
    }
    
    if (typeof values.customTimeEnabled === 'boolean') {
        debugData.customTimeEnabled = values.customTimeEnabled;
    }
    
    if (typeof values.customDate === 'string') {
        debugData.customDate = values.customDate;
    }
    
    if (typeof values.customTime === 'string') {
        debugData.customTime = values.customTime;
    }
    
    if (typeof values.customAmPm === 'string' && ['AM', 'PM'].includes(values.customAmPm)) {
        debugData.customAmPm = values.customAmPm;
    }
    
    // Update inputs if debug panel is visible
    const timeEnabledCheckbox = document.getElementById('debug-time-enabled');
    const dateInput = document.getElementById('debug-custom-date');
    const hourInput = document.getElementById('debug-custom-hour');
    const minuteInput = document.getElementById('debug-custom-minute');
    const ampmSelect = document.getElementById('debug-custom-ampm');
    
    if (timeEnabledCheckbox) timeEnabledCheckbox.checked = debugData.customTimeEnabled;
    if (dateInput) dateInput.value = debugData.customDate;
    if (hourInput && debugData.customTime) hourInput.value = debugData.customTime.split(':')[0];
    if (minuteInput && debugData.customTime) minuteInput.value = debugData.customTime.split(':')[1];
    if (ampmSelect) ampmSelect.value = debugData.customAmPm;
    
    // Update time override UI state
    toggleTimeOverride();
    updateTimePreview();
    
    console.log('Debug values set via API:', debugData);
    return true;
}

/**
 * Get current debug state
 * @returns {Object} Debug state information
 */
function getDebugState() {
    return {
        enabled: debugModeEnabled,
        panelVisible: debugPanelVisible,
        data: { ...debugData }
    };
}

/**
 * Add visual indicator that debug mode is active
 */
function addDebugModeIndicator() {
    console.log('DEBUG MODE: Adding visual debug mode indicator');
    
    let indicator = document.getElementById('debug-mode-indicator');
    
    console.log('DEBUG MODE: Checking for existing indicator:', {
        indicatorExists: !!indicator,
        indicatorId: indicator ? indicator.id : 'None'
    });
    
    if (!indicator) {
        console.log('DEBUG MODE: Creating new debug mode indicator element');
        
        indicator = document.createElement('div');
        indicator.id = 'debug-mode-indicator';
        indicator.innerHTML = 'DEBUG MODE ACTIVE';
        indicator.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: #ff4444;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            z-index: 1500;
            letter-spacing: 0.5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            animation: pulse 2s infinite;
        `;
        
        // Add some CSS animation for visibility
        if (!document.getElementById('debug-indicator-styles')) {
            const style = document.createElement('style');
            style.id = 'debug-indicator-styles';
            style.textContent = `
                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0.7; }
                    100% { opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }
        
        console.log('DEBUG MODE: Appending indicator to document body');
        document.body.appendChild(indicator);
        
        console.log('DEBUG MODE: Indicator element created and appended:', {
            elementId: indicator.id,
            innerHTML: indicator.innerHTML,
            parentElement: indicator.parentElement ? indicator.parentElement.tagName : 'None'
        });
    } else {
        console.log('DEBUG MODE: Debug mode indicator already exists, ensuring visibility');
        indicator.style.display = 'block';
    }
    
    console.log('DEBUG MODE: Adding debug-mode-active class to body');
    document.body.classList.add('debug-mode-active');
    
    // Verify the indicator is visible
    setTimeout(() => {
        const finalIndicator = document.getElementById('debug-mode-indicator');
        console.log('DEBUG MODE: Indicator visibility verification:', {
            indicatorExists: !!finalIndicator,
            isVisible: finalIndicator ? getComputedStyle(finalIndicator).display !== 'none' : false,
            hasActiveClass: document.body.classList.contains('debug-mode-active'),
            indicatorRect: finalIndicator ? finalIndicator.getBoundingClientRect() : null
        });
    }, 100);
    
    console.log('DEBUG MODE: Debug mode indicator setup completed');
}

/**
 * Remove debug mode indicator
 */
function removeDebugModeIndicator() {
    console.log('DEBUG MODE: Removing visual debug mode indicator');
    
    const indicator = document.getElementById('debug-mode-indicator');
    
    console.log('DEBUG MODE: Indicator removal status:', {
        indicatorExists: !!indicator,
        bodyHasActiveClass: document.body.classList.contains('debug-mode-active')
    });
    
    if (indicator) {
        console.log('DEBUG MODE: Removing indicator element from DOM');
        indicator.remove();
        console.log('DEBUG MODE: Indicator element successfully removed');
    } else {
        console.log('DEBUG MODE: No indicator element found to remove');
    }
    
    console.log('DEBUG MODE: Removing debug-mode-active class from body');
    document.body.classList.remove('debug-mode-active');
    
    // Also remove the debug styles if they exist
    const debugStyles = document.getElementById('debug-indicator-styles');
    if (debugStyles) {
        console.log('DEBUG MODE: Removing debug indicator styles');
        debugStyles.remove();
    }
    
    // Verify cleanup
    setTimeout(() => {
        const verifyIndicator = document.getElementById('debug-mode-indicator');
        console.log('DEBUG MODE: Indicator cleanup verification:', {
            indicatorStillExists: !!verifyIndicator,
            bodyStillHasActiveClass: document.body.classList.contains('debug-mode-active'),
            stylesStillExist: !!document.getElementById('debug-indicator-styles')
        });
    }, 100);
    
    console.log('DEBUG MODE: Debug mode indicator removal completed');
}

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
    },
    // Debug mode exports
    toggleDebugMode: toggleDebugMode,
    setDebugValues: setDebugValues,
    getDebugState: getDebugState,
    applyDebugValues: applyDebugValues,
    clearDebugValues: clearDebugValues
};

console.log('Whats-Next-View JavaScript loaded and ready');