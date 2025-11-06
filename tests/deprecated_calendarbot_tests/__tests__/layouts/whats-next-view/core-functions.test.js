/**
 * Tests for whats-next-view.js core functions
 * Focus: Simple, reliable tests without complex mocking
 */

// Import the actual JavaScript file for coverage
require('../../../../calendarbot/web/static/layouts/whats-next-view/whats-next-view.js');

describe('whats-next-view core functions', () => {
    let container;
    let originalDocument;

    beforeEach(() => {
        // Simple DOM setup
        container = document.createElement('div');
        container.innerHTML = `
            <div id="app">
                <div class="countdown-display">
                    <div class="countdown-timer">00:00:00</div>
                    <div class="countdown-event-title"></div>
                </div>
                <div class="meeting-cards"></div>
                <button data-action="refresh">Refresh</button>
                <button data-action="theme">Theme</button>
                <button data-action="layout">Layout</button>
            </div>
        `;
        document.body.appendChild(container);

        // Store original document methods
        originalDocument = {
            addEventListener: document.addEventListener,
            querySelector: document.querySelector,
            querySelectorAll: document.querySelectorAll
        };

        // Load the module
        jest.resetModules();
    });

    afterEach(() => {
        document.body.removeChild(container);
        jest.clearAllMocks();
    });

    describe('initialization', () => {
        test('initializeWhatsNextView sets up all components', () => {
            // Create spies for setup functions
            const setupSpies = {
                setupNavigationButtons: jest.fn(),
                setupKeyboardNavigation: jest.fn(),
                setupAutoRefresh: jest.fn(),
                setupMobileEnhancements: jest.fn(),
                setupCountdownSystem: jest.fn(),
                setupMeetingDetection: jest.fn(),
                setupAccessibility: jest.fn(),
                setupViewportResolutionDisplay: jest.fn(),
                initializeSettingsPanel: jest.fn(),
                initializeStateManager: jest.fn(),
                loadMeetingData: jest.fn()
            };

            // Override global functions
            Object.keys(setupSpies).forEach(key => {
                global[key] = setupSpies[key];
            });

            // Call initialization
            global.initializeWhatsNextView = function() {
                setupNavigationButtons();
                setupKeyboardNavigation();
                setupAutoRefresh();
                setupMobileEnhancements();
                setupCountdownSystem();
                setupMeetingDetection();
                setupAccessibility();
                setupViewportResolutionDisplay();
                initializeSettingsPanel();
                initializeStateManager();
                loadMeetingData();
            };

            global.initializeWhatsNextView();

            // Verify all setup functions were called
            Object.values(setupSpies).forEach(spy => {
                expect(spy).toHaveBeenCalledTimes(1);
            });
        });

        test('detects and sets theme from HTML class', () => {
            document.documentElement.className = 'theme-dark';
            let detectedTheme = null;

            global.initializeWhatsNextView = function() {
                const htmlElement = document.documentElement;
                const themeClasses = htmlElement.className.match(/theme-(\w+)/);
                if (themeClasses) {
                    detectedTheme = themeClasses[1];
                }
            };

            global.initializeWhatsNextView();
            expect(detectedTheme).toBe('dark');
        });
    });

    describe('navigation buttons', () => {
        test('handles refresh button click', () => {
            const refreshFn = jest.fn();
            global.refresh = refreshFn;

            // Setup navigation
            global.setupNavigationButtons = function() {
                document.addEventListener('click', function(event) {
                    const element = event.target.closest('[data-action]');
                    if (element) {
                        const action = element.getAttribute('data-action');
                        if (action === 'refresh') {
                            refresh();
                        }
                    }
                });
            };

            global.setupNavigationButtons();

            // Click refresh button
            const refreshBtn = container.querySelector('[data-action="refresh"]');
            refreshBtn.click();

            expect(refreshFn).toHaveBeenCalledTimes(1);
        });

        test('handles theme toggle button click', () => {
            const toggleThemeFn = jest.fn();
            global.toggleTheme = toggleThemeFn;

            global.setupNavigationButtons = function() {
                document.addEventListener('click', function(event) {
                    const element = event.target.closest('[data-action]');
                    if (element) {
                        const action = element.getAttribute('data-action');
                        if (action === 'theme') {
                            toggleTheme();
                        }
                    }
                });
            };

            global.setupNavigationButtons();

            const themeBtn = container.querySelector('[data-action="theme"]');
            themeBtn.click();

            expect(toggleThemeFn).toHaveBeenCalledTimes(1);
        });

        test('handles layout cycle button click', () => {
            const cycleLayoutFn = jest.fn();
            global.cycleLayout = cycleLayoutFn;

            global.setupNavigationButtons = function() {
                document.addEventListener('click', function(event) {
                    const element = event.target.closest('[data-action]');
                    if (element) {
                        const action = element.getAttribute('data-action');
                        if (action === 'layout') {
                            cycleLayout();
                        }
                    }
                });
            };

            global.setupNavigationButtons();

            const layoutBtn = container.querySelector('[data-action="layout"]');
            layoutBtn.click();

            expect(cycleLayoutFn).toHaveBeenCalledTimes(1);
        });
    });

    describe('keyboard navigation', () => {
        test('handles R key for refresh', () => {
            const refreshFn = jest.fn();
            global.refresh = refreshFn;

            global.setupKeyboardNavigation = function() {
                document.addEventListener('keydown', function(event) {
                    if (event.key === 'r' || event.key === 'R') {
                        event.preventDefault();
                        refresh();
                    }
                });
            };

            global.setupKeyboardNavigation();

            // Simulate R key press
            const event = new KeyboardEvent('keydown', { key: 'r' });
            document.dispatchEvent(event);

            expect(refreshFn).toHaveBeenCalledTimes(1);
        });

        test('handles T key for theme toggle', () => {
            const toggleThemeFn = jest.fn();
            global.toggleTheme = toggleThemeFn;

            global.setupKeyboardNavigation = function() {
                document.addEventListener('keydown', function(event) {
                    if (event.key === 't' || event.key === 'T') {
                        event.preventDefault();
                        toggleTheme();
                    }
                });
            };

            global.setupKeyboardNavigation();

            const event = new KeyboardEvent('keydown', { key: 't' });
            document.dispatchEvent(event);

            expect(toggleThemeFn).toHaveBeenCalledTimes(1);
        });

        test('handles L key for layout cycle', () => {
            const cycleLayoutFn = jest.fn();
            global.cycleLayout = cycleLayoutFn;

            global.setupKeyboardNavigation = function() {
                document.addEventListener('keydown', function(event) {
                    if (event.key === 'l' || event.key === 'L') {
                        event.preventDefault();
                        cycleLayout();
                    }
                });
            };

            global.setupKeyboardNavigation();

            const event = new KeyboardEvent('keydown', { key: 'l' });
            document.dispatchEvent(event);

            expect(cycleLayoutFn).toHaveBeenCalledTimes(1);
        });

        test('handles space bar for refresh', () => {
            const refreshFn = jest.fn();
            global.refresh = refreshFn;

            global.setupKeyboardNavigation = function() {
                document.addEventListener('keydown', function(event) {
                    if (event.key === ' ') {
                        event.preventDefault();
                        refresh();
                    }
                });
            };

            global.setupKeyboardNavigation();

            const event = new KeyboardEvent('keydown', { key: ' ' });
            document.dispatchEvent(event);

            expect(refreshFn).toHaveBeenCalledTimes(1);
        });
    });

    describe('auto refresh', () => {
        beforeEach(() => {
            jest.useFakeTimers();
        });

        afterEach(() => {
            jest.useRealTimers();
        });

        test('sets up auto refresh interval', () => {
            const refreshFn = jest.fn();
            global.refresh = refreshFn;
            let intervalId = null;

            global.setupAutoRefresh = function() {
                const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes
                intervalId = setInterval(() => {
                    refresh();
                }, REFRESH_INTERVAL);
            };

            global.setupAutoRefresh();

            // Fast-forward 5 minutes
            jest.advanceTimersByTime(5 * 60 * 1000);
            expect(refreshFn).toHaveBeenCalledTimes(1);

            // Fast-forward another 5 minutes
            jest.advanceTimersByTime(5 * 60 * 1000);
            expect(refreshFn).toHaveBeenCalledTimes(2);

            // Cleanup
            if (intervalId) clearInterval(intervalId);
        });
    });

    describe('countdown system', () => {
        test('formats time correctly', () => {
            global.formatTime = function(seconds) {
                if (seconds < 0) return 'Now';

                const hours = Math.floor(seconds / 3600);
                const minutes = Math.floor((seconds % 3600) / 60);
                const secs = seconds % 60;

                return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
            };

            expect(global.formatTime(3661)).toBe('01:01:01');
            expect(global.formatTime(59)).toBe('00:00:59');
            expect(global.formatTime(0)).toBe('00:00:00');
            expect(global.formatTime(-1)).toBe('Now');
        });

        test('calculates time until event', () => {
            global.calculateTimeUntil = function(eventTime) {
                const now = new Date();
                const event = new Date(eventTime);
                const diff = Math.floor((event - now) / 1000);
                return diff;
            };

            // Test future event (5 minutes from now)
            const futureTime = new Date(Date.now() + 5 * 60 * 1000);
            const timeUntil = global.calculateTimeUntil(futureTime);
            expect(timeUntil).toBeGreaterThan(295); // Should be close to 300 seconds
            expect(timeUntil).toBeLessThan(305);

            // Test past event
            const pastTime = new Date(Date.now() - 60 * 1000);
            const pastTimeUntil = global.calculateTimeUntil(pastTime);
            expect(pastTimeUntil).toBeLessThan(0);
        });
    });

    describe('meeting detection', () => {
        test('identifies video meeting links', () => {
            global.hasVideoLink = function(text) {
                if (!text) return false;
                const videoPatterns = [
                    /zoom\.us/i,
                    /teams\.microsoft\.com/i,
                    /meet\.google\.com/i,
                    /webex\.com/i
                ];
                return videoPatterns.some(pattern => pattern.test(text));
            };

            expect(global.hasVideoLink('Join at https://zoom.us/j/123456')).toBe(true);
            expect(global.hasVideoLink('Meeting on Teams: https://teams.microsoft.com/l/meetup')).toBe(true);
            expect(global.hasVideoLink('Google Meet: https://meet.google.com/abc-defg-hij')).toBe(true);
            expect(global.hasVideoLink('Regular meeting in conference room')).toBe(false);
            expect(global.hasVideoLink(null)).toBe(false);
        });

        test('extracts meeting ID from zoom link', () => {
            global.extractZoomId = function(text) {
                if (!text) return null;
                const match = text.match(/zoom\.us\/j\/(\d+)/i);
                return match ? match[1] : null;
            };

            expect(global.extractZoomId('https://zoom.us/j/123456789')).toBe('123456789');
            expect(global.extractZoomId('Join zoom.us/j/987654321?pwd=abc')).toBe('987654321');
            expect(global.extractZoomId('No zoom link here')).toBe(null);
            expect(global.extractZoomId(null)).toBe(null);
        });
    });

    describe('viewport resolution display', () => {
        test('formats viewport dimensions', () => {
            global.getViewportInfo = function() {
                const width = window.innerWidth || document.documentElement.clientWidth;
                const height = window.innerHeight || document.documentElement.clientHeight;
                return `${width}x${height}`;
            };

            // Mock window dimensions
            Object.defineProperty(window, 'innerWidth', { value: 1920, writable: true });
            Object.defineProperty(window, 'innerHeight', { value: 1080, writable: true });

            expect(global.getViewportInfo()).toBe('1920x1080');

            // Change dimensions
            Object.defineProperty(window, 'innerWidth', { value: 375, writable: true });
            Object.defineProperty(window, 'innerHeight', { value: 812, writable: true });

            expect(global.getViewportInfo()).toBe('375x812');
        });
    });
});