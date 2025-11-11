/**
 * CalendarBot Lite - What's Next JavaScript
 * Optimized for Pi Zero 2W performance
 *
 * Handles API calls to backend for meeting data and updates DOM
 * without countdown logic - backend provides all time calculations
 */

(function() {
    'use strict';

    // === CONFIGURATION ===
    const CONFIG = {
        API_ENDPOINT: '/api/whats-next',
        REFRESH_INTERVAL: 60000, // 60 seconds
        REQUEST_TIMEOUT: 10000,  // 10 seconds
        MAX_RETRY_ATTEMPTS: 3,
        RETRY_DELAY: 5000        // 5 seconds
    };

    // === CACHED DOM ELEMENTS (Performance optimization) ===
    let domElements = null;

    /**
     * Cache DOM elements on first access to avoid repeated queries
     * Critical for Pi Zero 2W performance
     */
    function getDOMElements() {
        if (!domElements) {
            domElements = {
                countdownTime: document.querySelector('.countdown-time'),
                countdownHours: document.querySelector('.countdown-hours'),
                countdownMinutes: document.querySelector('.countdown-minutes'),
                meetingTitle: document.querySelector('.meeting-title'),
                meetingTime: document.querySelector('.meeting-time'),
                meetingLocation: document.querySelector('.meeting-location'),
                nextMeetingTime: document.querySelector('.next-meeting-time'),
                nextMeetingTitle: document.querySelector('.next-meeting-title'),
                nextMeetings: document.querySelector('.next-meetings'),
                countdownContainer: document.querySelector('.countdown-container'),
                meetingCloseBtn: document.querySelector('.meeting-close-btn'),
                meetingCard: document.querySelector('.meeting-card')
            };
        }
        return domElements;
    }

    // === STATE MANAGEMENT ===
    let state = {
        intervalId: null,
        heartbeatIntervalId: null,
        retryCount: 0,
        lastSuccessfulUpdate: null,
        isOnline: navigator.onLine,
        currentMeeting: null
    };

    /**
     * Makes API call to get next meeting data
     * @returns {Promise<Object>} API response data
     */
    async function fetchMeetingData() {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT);

        try {
            const response = await fetch(CONFIG.API_ENDPOINT, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Cache-Control': 'no-cache'
                },
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            // Reset retry count on successful response
            state.retryCount = 0;
            state.lastSuccessfulUpdate = Date.now();

            return data;

        } catch (error) {
            clearTimeout(timeoutId);

            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }

            throw error;
        }
    }

    /**
     * Updates DOM elements with meeting data
     * Optimized for minimal DOM manipulation
     * @param {Object} data - API response data
     */
    function updateDisplay(data) {
        const elements = getDOMElements();

        try {
            // Check if we have a meeting from the server
            if (data.meeting) {
                const meeting = data.meeting;

                // Store current meeting data for skip functionality
                state.currentMeeting = meeting;

                // Update meeting title
                if (elements.meetingTitle) {
                    elements.meetingTitle.textContent = meeting.subject || 'No meeting';
                }

                // Update meeting time (format the start time)
                if (elements.meetingTime && meeting.start_iso) {
                    const startTime = new Date(meeting.start_iso);
                    const endTime = new Date(startTime.getTime() + (meeting.duration_seconds || 0) * 1000);
                    const timeFormat = { hour: '2-digit', minute: '2-digit', hour12: true };
                    elements.meetingTime.textContent = `${startTime.toLocaleTimeString('en-US', timeFormat)} - ${endTime.toLocaleTimeString('en-US', timeFormat)}`;
                }

                // Update meeting location
                if (elements.meetingLocation) {
                    elements.meetingLocation.textContent = meeting.location || '';
                }

                // Update countdown display based on seconds_until_start
                if (meeting.seconds_until_start !== undefined) {
                    const secondsUntil = meeting.seconds_until_start;
                    const hours = Math.floor(secondsUntil / 3600);
                    const minutes = Math.floor((secondsUntil % 3600) / 60);

                    // Main countdown number (show hours if > 0, otherwise minutes)
                    if (elements.countdownTime) {
                        elements.countdownTime.textContent = hours > 0 ? hours : Math.max(0, minutes);
                    }

                    // Time units
                    if (elements.countdownHours) {
                        elements.countdownHours.textContent = hours > 0 ? 'HOURS' : 'MINUTES';
                    }

                    if (elements.countdownMinutes) {
                        if (hours > 0) {
                            elements.countdownMinutes.textContent = `${minutes} MINUTES`;
                        } else {
                            elements.countdownMinutes.textContent = '';
                        }
                    }

                    // Apply visual state classes based on time remaining
                    if (elements.countdownContainer) {
                        let state = 'normal';
                        if (secondsUntil < 300) state = 'critical'; // Less than 5 minutes
                        else if (secondsUntil < 900) state = 'warning'; // Less than 15 minutes
                        updateCountdownState(elements.countdownContainer, state);
                    }
                }

                // Update bottom section display based on meeting timing
                updateBottomSectionDisplay(meeting, elements);

            } else {
                // No meeting data - show fallback
                if (elements.meetingTitle) {
                    elements.meetingTitle.textContent = 'No upcoming meetings';
                }

                if (elements.meetingTime) {
                    elements.meetingTime.textContent = '';
                }

                if (elements.meetingLocation) {
                    elements.meetingLocation.textContent = '';
                }

                if (elements.countdownTime) {
                    elements.countdownTime.textContent = '0';
                }

                if (elements.countdownHours) {
                    elements.countdownHours.textContent = 'MEETINGS';
                }

                if (elements.countdownMinutes) {
                    elements.countdownMinutes.textContent = '';
                }

                updateBottomSectionDisplay(null, elements);
            }

            console.log('Display updated successfully');

        } catch (error) {
            console.error('Error updating display:', error);
            handleDisplayError();
        }
    }

    /**
     * Update bottom section display based on current meeting timing
     * @param {Object} meeting - Current meeting data from server
     * @param {Object} elements - Cached DOM elements
     */
    function updateBottomSectionDisplay(meeting, elements) {
        if (!elements.nextMeetingTime) {
            return;
        }

        if (meeting && meeting.seconds_until_start !== undefined) {
            const secondsUntil = meeting.seconds_until_start;
            const minutesUntil = Math.floor(secondsUntil / 60);

            let contextText = 'Next meeting';
            let timeText = '';
            let isUrgent = false;
            let isCritical = false;

            if (secondsUntil <= 0) {
                // Meeting is happening now or has started
                const durationSeconds = meeting.duration_seconds || 0;
                const secondsSinceStart = Math.abs(secondsUntil);

                if (secondsSinceStart < durationSeconds) {
                    contextText = 'Meeting in progress';
                    const remainingSeconds = durationSeconds - secondsSinceStart;
                    const remainingMinutes = Math.floor(remainingSeconds / 60);
                    if (remainingMinutes > 0) {
                        timeText = `${remainingMinutes}m remaining`;
                    } else {
                        timeText = 'ending soon';
                    }
                    isUrgent = true;
                } else {
                    contextText = 'Meeting ended';
                    timeText = '';
                }
            } else if (minutesUntil <= 2) {
                contextText = 'Starting very soon';
                timeText = `${minutesUntil}m`;
                isCritical = true;
                isUrgent = true;
            } else if (minutesUntil <= 15) {
                contextText = 'Starting soon';
                timeText = `${minutesUntil}m`;
                isUrgent = true;
            } else if (minutesUntil <= 60) {
                contextText = 'Starting within the hour';
                timeText = `${minutesUntil}m`;
            } else {
                const hours = Math.floor(minutesUntil / 60);
                const minutes = minutesUntil % 60;
                if (hours < 24) {
                    contextText = 'Plenty of time';
                    if (minutes === 0) {
                        timeText = `${hours}h`;
                    } else {
                        timeText = `${hours}h ${minutes}m`;
                    }
                } else {
                    contextText = 'Next meeting';
                    const days = Math.floor(hours / 24);
                    timeText = `${days}d`;
                }
            }

            // Update content - only show context message, no time display
            elements.nextMeetingTime.textContent = '';
            if (elements.nextMeetingTitle) {
                elements.nextMeetingTitle.textContent = contextText;
            }

            // Apply lightweight visual styling based on urgency
            applyBottomSectionStyling(elements, isUrgent, isCritical);
        } else {
            // No meeting data - clear everything
            elements.nextMeetingTime.textContent = '';
            if (elements.nextMeetingTitle) {
                elements.nextMeetingTitle.textContent = 'No meetings scheduled';
            }

            // Clear any styling
            applyBottomSectionStyling(elements, false, false);
        }
    }

    /**
     * Apply lightweight styling to bottom section based on urgency
     * @param {Object} elements - Cached DOM elements
     * @param {boolean} isUrgent - Whether situation is urgent
     * @param {boolean} isCritical - Whether situation is critical
     */
    function applyBottomSectionStyling(elements, isUrgent, isCritical) {
        // Clear existing urgency classes
        if (elements.nextMeetingTitle) {
            elements.nextMeetingTitle.classList.remove('urgent');
        }
        if (elements.nextMeetingTime) {
            elements.nextMeetingTime.classList.remove('urgent');
        }
        if (elements.nextMeetings) {
            elements.nextMeetings.classList.remove('critical');
        }

        // Apply new classes based on state
        if (isUrgent) {
            if (elements.nextMeetingTitle) {
                elements.nextMeetingTitle.classList.add('urgent');
            }
            if (elements.nextMeetingTime) {
                elements.nextMeetingTime.classList.add('urgent');
            }
        }

        if (isCritical && elements.nextMeetings) {
            elements.nextMeetings.classList.add('critical');
        }
    }

    /**
     * Updates countdown container visual state
     * @param {HTMLElement} container - Countdown container element
     * @param {string} state - State from API (normal|warning|critical)
     */
    function updateCountdownState(container, state) {
        // Remove existing state classes
        container.classList.remove('countdown-normal', 'countdown-warning', 'countdown-critical');

        // Add new state class
        if (state && ['normal', 'warning', 'critical'].includes(state)) {
            container.classList.add(`countdown-${state}`);
        }
    }

    /**
     * Handles API fetch errors with exponential backoff retry
     * @param {Error} error - The error that occurred
     */
    function handleFetchError(error) {
        state.retryCount++;

        console.error(`API fetch failed (attempt ${state.retryCount}):`, error.message);

        if (state.retryCount < CONFIG.MAX_RETRY_ATTEMPTS) {
            const delay = CONFIG.RETRY_DELAY * Math.pow(2, state.retryCount - 1);
            console.log(`Retrying in ${delay / 1000} seconds...`);

            setTimeout(() => {
                updateMeetingData();
            }, delay);
        } else {
            console.error('Max retry attempts reached. Will retry on next interval.');
            handleDisplayError();
        }
    }

    /**
     * Handles display update errors
     */
    function handleDisplayError() {
        const elements = getDOMElements();

        // Show fallback content without breaking the interface
        if (elements.meetingTitle) {
            elements.meetingTitle.textContent = 'Connection Error';
        }

        if (elements.meetingTime) {
            elements.meetingTime.textContent = 'Reconnecting...';
        }
    }

    /**
     * Main function to fetch and update meeting data
     */
    async function updateMeetingData() {
        if (!state.isOnline) {
            console.log('Offline mode - skipping API call');
            return;
        }

        try {
            const data = await fetchMeetingData();

            // Validate response structure
            if (!data || typeof data !== 'object') {
                throw new Error('Invalid API response format');
            }

            updateDisplay(data);

        } catch (error) {
            handleFetchError(error);
        }
    }

    /**
     * Starts the periodic API polling
     */
    function startPolling() {
        // Clear any existing interval
        if (state.intervalId) {
            clearInterval(state.intervalId);
        }

        // Immediate first call
        updateMeetingData();

        // Set up recurring calls
        state.intervalId = setInterval(updateMeetingData, CONFIG.REFRESH_INTERVAL);

        console.log(`Polling started - updating every ${CONFIG.REFRESH_INTERVAL / 1000} seconds`);
    }

    /**
     * Stops the periodic API polling
     */
    function stopPolling() {
        if (state.intervalId) {
            clearInterval(state.intervalId);
            state.intervalId = null;
            console.log('Polling stopped');
        }
    }

    /**
     * Handles online/offline status changes
     */
    function handleConnectionChange() {
        state.isOnline = navigator.onLine;

        if (state.isOnline) {
            console.log('Connection restored - resuming polling');
            startPolling();
        } else {
            console.log('Connection lost - pausing polling');
            stopPolling();
        }
    }

    /**
     * Handles page visibility changes to optimize performance
     */
    function handleVisibilityChange() {
        if (document.hidden) {
            console.log('Page hidden - pausing polling');
            stopPolling();
        } else {
            console.log('Page visible - resuming polling');
            startPolling();
        }
    }

    /**
     * Sends browser heartbeat to server for watchdog monitoring
     * This helps detect stuck/frozen browsers showing blank pages
     */
    async function sendBrowserHeartbeat() {
        try {
            const response = await fetch('/api/browser-heartbeat', {
                method: 'POST',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (response.ok) {
                console.log('Browser heartbeat sent successfully');
            } else {
                console.warn('Browser heartbeat failed:', response.status);
            }
        } catch (error) {
            console.error('Error sending browser heartbeat:', error);
        }
    }

    /**
     * Starts the browser heartbeat monitoring
     * Sends heartbeats every 30 seconds to prove the browser is alive
     */
    function startBrowserHeartbeat() {
        // Clear any existing heartbeat interval
        if (state.heartbeatIntervalId) {
            clearInterval(state.heartbeatIntervalId);
        }

        // Send immediate heartbeat
        sendBrowserHeartbeat();

        // Set up recurring heartbeats every 30 seconds
        state.heartbeatIntervalId = setInterval(sendBrowserHeartbeat, 30000);

        console.log('Browser heartbeat started - sending every 30 seconds');
    }

    /**
     * Stops the browser heartbeat monitoring
     */
    function stopBrowserHeartbeat() {
        if (state.heartbeatIntervalId) {
            clearInterval(state.heartbeatIntervalId);
            state.heartbeatIntervalId = null;
            console.log('Browser heartbeat stopped');
        }
    }

    /**
     * Calls the skip API to mark a meeting as skipped
     * @param {string} meetingId - The meeting ID to skip
     * @returns {Promise<boolean>} - True if successful, false otherwise
     */
    async function skipMeeting(meetingId) {
        try {
            const response = await fetch('/api/skip', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ meeting_id: meetingId })
            });

            if (response.ok) {
                console.log('Meeting skipped successfully:', meetingId);
                return true;
            } else {
                console.error('Failed to skip meeting:', response.status, response.statusText);
                return false;
            }
        } catch (error) {
            console.error('Error skipping meeting:', error);
            return false;
        }
    }

    /**
     * Handles close button click to skip the current meeting
     */
    async function handleMeetingClose() {
        // Check if we have a current meeting
        if (!state.currentMeeting) {
            console.warn('No current meeting to skip');
            return;
        }

        // Get meeting ID - try different possible ID fields
        const meetingId = state.currentMeeting.id ||
                         state.currentMeeting.graph_id ||
                         state.currentMeeting.meeting_id ||
                         state.currentMeeting.uid;

        if (!meetingId) {
            console.error('Unable to determine meeting ID for skipping');
            return;
        }

        console.log('Attempting to skip meeting:', meetingId);

        // Disable the close button to prevent double-clicks
        const elements = getDOMElements();
        if (elements.meetingCloseBtn) {
            elements.meetingCloseBtn.disabled = true;
            elements.meetingCloseBtn.style.opacity = '0.5';
        }

        // Call the skip API
        const success = await skipMeeting(meetingId);

        if (success) {
            // Refresh the page to show the next meeting
            window.location.reload();
        } else {
            // Re-enable the button if skipping failed
            if (elements.meetingCloseBtn) {
                elements.meetingCloseBtn.disabled = false;
                elements.meetingCloseBtn.style.opacity = '1';
            }

            // Show error message to user
            alert('Failed to skip meeting. Please try again.');
        }
    }

    /**
     * Sets up event listeners for the close button
     */
    function setupCloseButtonListener() {
        const elements = getDOMElements();

        if (elements.meetingCloseBtn) {
            // Remove any existing listeners to prevent duplicates
            elements.meetingCloseBtn.removeEventListener('click', handleMeetingClose);
            elements.meetingCloseBtn.removeEventListener('touchstart', handleMeetingClose);

            // Add click and touch event listeners
            elements.meetingCloseBtn.addEventListener('click', handleMeetingClose, { passive: true });
            elements.meetingCloseBtn.addEventListener('touchstart', handleMeetingClose, { passive: true });

            console.log('Close button event listeners set up');
        }
    }

    /**
     * Cleanup function for proper resource management
     */
    function cleanup() {
        stopPolling();
        stopBrowserHeartbeat();

        // Remove close button listeners
        const elements = getDOMElements();
        if (elements.meetingCloseBtn) {
            elements.meetingCloseBtn.removeEventListener('click', handleMeetingClose);
            elements.meetingCloseBtn.removeEventListener('touchstart', handleMeetingClose);
        }

        domElements = null;

        // Remove event listeners
        window.removeEventListener('online', handleConnectionChange);
        window.removeEventListener('offline', handleConnectionChange);
        document.removeEventListener('visibilitychange', handleVisibilityChange);
        window.removeEventListener('beforeunload', cleanup);
    }

    /**
     * Initialize the application
     */
    function init() {
        console.log('CalendarBot Lite - What\'s Next View initialized');

        // Verify required DOM elements exist
        const elements = getDOMElements();
        const requiredElements = ['countdownTime', 'meetingTitle', 'meetingTime'];

        for (const elementName of requiredElements) {
            if (!elements[elementName]) {
                console.error(`Required element not found: .${elementName.replace(/([A-Z])/g, '-$1').toLowerCase()}`);
                return;
            }
        }

        // Set up event listeners for connection and visibility changes
        window.addEventListener('online', handleConnectionChange, { passive: true });
        window.addEventListener('offline', handleConnectionChange, { passive: true });
        document.addEventListener('visibilitychange', handleVisibilityChange, { passive: true });
        window.addEventListener('beforeunload', cleanup, { passive: true });

        // Set up close button event listener
        setupCloseButtonListener();

        // Start the polling
        startPolling();

        // Start browser heartbeat for watchdog monitoring
        startBrowserHeartbeat();
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }

    // Expose cleanup function globally for manual cleanup if needed
    window.calendarbotCleanup = cleanup;

})();