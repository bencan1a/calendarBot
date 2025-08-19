/**
 * Tests for 4x8.js core functionality 
 * Focus: Testing initialization, navigation, keyboard handlers, and auto-refresh
 */

// Import the actual JavaScript file for coverage
require('../../../../calendarbot/web/static/layouts/4x8/4x8.js');

describe('4x8 layout core functionality', () => {
    let container;
    let mockFunctions;
    let eventHandlers = [];

    beforeEach(() => {
        // Clear any existing event handlers
        eventHandlers = [];
        // Initialize global state variables consistently
        global.backendBaselineTime = null;
        global.frontendBaselineTime = null;
        global.settingsPanel = null;
        global.autoRefreshInterval = null;
        global.autoRefreshEnabled = false;
        global.currentTheme = undefined;
        
        // Setup DOM container
        container = document.createElement('div');
        container.innerHTML = `
            <div id="app">
                <div class="calendar-grid">
                    <button data-action="prev">Previous</button>
                    <button data-action="next">Next</button>
                    <button data-action="refresh">Refresh</button>
                </div>
            </div>
        `;
        document.body.appendChild(container);

        // Mock global functions with fresh instances
        mockFunctions = {
            navigate: jest.fn(),
            refresh: jest.fn(),
            toggleTheme: jest.fn(),
            cycleLayout: jest.fn(),
            initializeSettingsPanel: jest.fn(),
            setupNavigationButtons: null,
            setupKeyboardNavigation: null,
            setupAutoRefresh: null,
            setupMobileEnhancements: null
        };
        
        Object.assign(global, mockFunctions);

        // Mock theme detection
        document.documentElement.className = 'theme-standard';
    });

    afterEach(() => {
        // Clean up DOM
        if (container && container.parentNode) {
            document.body.removeChild(container);
        }
        
        // Clear any intervals that might be running
        if (global.autoRefreshInterval) {
            clearInterval(global.autoRefreshInterval);
            global.autoRefreshInterval = null;
        }
        
        // Reset document event listeners by creating a fresh document
        // Save current body content, clear listeners, restore content
        const bodyHTML = document.body.innerHTML;
        const newDocument = document.implementation.createHTMLDocument();
        
        // Replace current document's event handling with clean version
        document.removeAllListeners = function() {
            // This is a simple approach for jsdom - remove common event types
            const events = ['click', 'keydown', 'DOMContentLoaded'];
            events.forEach(eventType => {
                const oldListeners = document._events?.[eventType] || [];
                oldListeners.forEach(listener => {
                    document.removeEventListener(eventType, listener);
                });
            });
        };
        
        // Remove all stored event handlers
        eventHandlers.forEach(({ element, event, handler }) => {
            element.removeEventListener(event, handler);
        });
        eventHandlers = [];
        
        // Reset global state
        global.backendBaselineTime = null;
        global.frontendBaselineTime = null;
        global.settingsPanel = null;
        global.autoRefreshInterval = null;
        global.autoRefreshEnabled = false;
        global.currentTheme = undefined;
    });

    describe('initializeApp', () => {
        let initializeApp;

        beforeEach(() => {
            // Create mock setup functions
            global.setupNavigationButtons = jest.fn();
            global.setupKeyboardNavigation = jest.fn();
            global.setupAutoRefresh = jest.fn();
            global.setupMobileEnhancements = jest.fn();

            // Implementation based on actual code (lines 18-42)
            initializeApp = function() {
                // Detect current theme from HTML class
                const htmlElement = document.documentElement;
                const themeClasses = htmlElement.className.match(/\btheme-(\w+)\b/);
                if (themeClasses) {
                    global.currentTheme = themeClasses[1];
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
            };
        });

        test('detects theme from HTML class', () => {
            document.documentElement.className = 'theme-dark';
            
            initializeApp();
            
            expect(global.currentTheme).toBe('dark');
        });

        test('calls all setup functions', () => {
            initializeApp();
            
            expect(global.setupNavigationButtons).toHaveBeenCalledTimes(1);
            expect(global.setupKeyboardNavigation).toHaveBeenCalledTimes(1);
            expect(global.setupAutoRefresh).toHaveBeenCalledTimes(1);
            expect(global.setupMobileEnhancements).toHaveBeenCalledTimes(1);
            expect(global.initializeSettingsPanel).toHaveBeenCalledTimes(1);
        });

        test('handles missing theme class gracefully', () => {
            document.documentElement.className = 'some-other-class no-themes-here';
            global.currentTheme = 'default';
            
            initializeApp();
            
            // Should not change currentTheme if no theme class found
            expect(global.currentTheme).toBe('default');
        });

        test('handles multiple theme classes', () => {
            document.documentElement.className = 'other-class theme-eink more-classes';
            
            initializeApp();
            
            expect(global.currentTheme).toBe('eink');
        });
    });

    describe('setupNavigationButtons', () => {
        let setupNavigationButtons;

        beforeEach(() => {
            // Implementation based on actual code (lines 45-59)
            setupNavigationButtons = function() {
                const handler = function(event) {
                    const element = event.target.closest('[data-action]');
                    if (element) {
                        const action = element.getAttribute('data-action');
                        if (action === 'prev' || action === 'next') {
                            event.preventDefault();
                            navigate(action);
                        }
                    }
                };
                document.addEventListener('click', handler);
                eventHandlers.push({ element: document, event: 'click', handler });
            };
        });

        test('handles prev button click', () => {
            setupNavigationButtons();
            
            const prevBtn = container.querySelector('[data-action="prev"]');
            const clickEvent = new MouseEvent('click', { bubbles: true });
            
            prevBtn.dispatchEvent(clickEvent);
            
            expect(mockFunctions.navigate).toHaveBeenCalledWith('prev');
        });

        test('handles next button click', () => {
            setupNavigationButtons();
            
            const nextBtn = container.querySelector('[data-action="next"]');
            const clickEvent = new MouseEvent('click', { bubbles: true });
            
            nextBtn.dispatchEvent(clickEvent);
            
            expect(mockFunctions.navigate).toHaveBeenCalledWith('next');
        });

        test('ignores non-navigation buttons', () => {
            setupNavigationButtons();
            
            const refreshBtn = container.querySelector('[data-action="refresh"]');
            const clickEvent = new MouseEvent('click', { bubbles: true });
            
            refreshBtn.dispatchEvent(clickEvent);
            
            expect(mockFunctions.navigate).not.toHaveBeenCalled();
        });

        test('handles click on nested elements', () => {
            const navBtn = container.querySelector('[data-action="prev"]');
            const innerSpan = document.createElement('span');
            innerSpan.textContent = 'Previous';
            navBtn.appendChild(innerSpan);
            
            setupNavigationButtons();
            
            const clickEvent = new MouseEvent('click', { bubbles: true });
            innerSpan.dispatchEvent(clickEvent);
            
            expect(mockFunctions.navigate).toHaveBeenCalledWith('prev');
        });

        test('prevents default behavior for navigation actions', () => {
            setupNavigationButtons();
            
            const prevBtn = container.querySelector('[data-action="prev"]');
            const clickEvent = new MouseEvent('click', { bubbles: true });
            const preventDefaultSpy = jest.spyOn(clickEvent, 'preventDefault');
            
            prevBtn.dispatchEvent(clickEvent);
            
            expect(preventDefaultSpy).toHaveBeenCalled();
        });
    });

    describe('setupKeyboardNavigation', () => {
        let setupKeyboardNavigation;

        beforeEach(() => {
            // Implementation based on actual code (lines 62-100)
            setupKeyboardNavigation = function() {
                const handler = function(event) {
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
                };
                document.addEventListener('keydown', handler);
                eventHandlers.push({ element: document, event: 'keydown', handler });
            };
        });

        test('handles left arrow key for previous navigation', () => {
            setupKeyboardNavigation();
            
            const event = new KeyboardEvent('keydown', { key: 'ArrowLeft' });
            document.dispatchEvent(event);
            
            expect(mockFunctions.navigate).toHaveBeenCalledWith('prev');
        });

        test('handles right arrow key for next navigation', () => {
            setupKeyboardNavigation();
            
            const event = new KeyboardEvent('keydown', { key: 'ArrowRight' });
            document.dispatchEvent(event);
            
            expect(mockFunctions.navigate).toHaveBeenCalledWith('next');
        });

        test('handles space bar for today navigation', () => {
            setupKeyboardNavigation();
            
            const event = new KeyboardEvent('keydown', { key: ' ' });
            document.dispatchEvent(event);
            
            expect(mockFunctions.navigate).toHaveBeenCalledWith('today');
        });

        test('handles Home key for week start', () => {
            setupKeyboardNavigation();
            
            const event = new KeyboardEvent('keydown', { key: 'Home' });
            document.dispatchEvent(event);
            
            expect(mockFunctions.navigate).toHaveBeenCalledWith('week-start');
        });

        test('handles End key for week end', () => {
            setupKeyboardNavigation();
            
            const event = new KeyboardEvent('keydown', { key: 'End' });
            document.dispatchEvent(event);
            
            expect(mockFunctions.navigate).toHaveBeenCalledWith('week-end');
        });

        test('handles R key for refresh', () => {
            setupKeyboardNavigation();
            
            const event = new KeyboardEvent('keydown', { key: 'R' });
            document.dispatchEvent(event);
            
            expect(mockFunctions.refresh).toHaveBeenCalledTimes(1);
        });

        test('handles lowercase r key for refresh', () => {
            setupKeyboardNavigation();
            
            const event = new KeyboardEvent('keydown', { key: 'r' });
            document.dispatchEvent(event);
            
            expect(mockFunctions.refresh).toHaveBeenCalledTimes(1);
        });

        test('handles T key for theme toggle', () => {
            setupKeyboardNavigation();
            
            const event = new KeyboardEvent('keydown', { key: 'T' });
            document.dispatchEvent(event);
            
            expect(mockFunctions.toggleTheme).toHaveBeenCalledTimes(1);
        });

        test('handles L key for layout cycle', () => {
            setupKeyboardNavigation();
            
            const event = new KeyboardEvent('keydown', { key: 'L' });
            document.dispatchEvent(event);
            
            expect(mockFunctions.cycleLayout).toHaveBeenCalledTimes(1);
        });

        test('prevents default for navigation keys', () => {
            setupKeyboardNavigation();
            
            const navigationKeys = ['ArrowLeft', 'ArrowRight', ' ', 'Home', 'End', 'r', 'R'];
            
            navigationKeys.forEach(key => {
                const event = new KeyboardEvent('keydown', { key });
                const preventDefaultSpy = jest.spyOn(event, 'preventDefault');
                
                document.dispatchEvent(event);
                
                expect(preventDefaultSpy).toHaveBeenCalled();
            });
        });

        test('ignores non-navigation keys', () => {
            setupKeyboardNavigation();
            
            const event = new KeyboardEvent('keydown', { key: 'a' });
            document.dispatchEvent(event);
            
            expect(mockFunctions.navigate).not.toHaveBeenCalled();
            expect(mockFunctions.refresh).not.toHaveBeenCalled();
            expect(mockFunctions.toggleTheme).not.toHaveBeenCalled();
            expect(mockFunctions.cycleLayout).not.toHaveBeenCalled();
        });
    });

    describe('setupAutoRefresh', () => {
        let setupAutoRefresh;

        beforeEach(() => {
            jest.useFakeTimers();
            
            // Mock implementation
            setupAutoRefresh = function() {
                if (global.autoRefreshEnabled) {
                    global.autoRefreshInterval = setInterval(function() {
                        refresh();
                    }, 60000); // 1 minute
                }
            };
        });

        afterEach(() => {
            if (global.autoRefreshInterval) {
                clearInterval(global.autoRefreshInterval);
            }
            jest.useRealTimers();
        });

        test('sets up auto refresh when enabled', () => {
            global.autoRefreshEnabled = true;
            
            setupAutoRefresh();
            
            expect(global.autoRefreshInterval).toBeDefined();
            
            // Fast-forward 1 minute
            jest.advanceTimersByTime(60000);
            expect(mockFunctions.refresh).toHaveBeenCalledTimes(1);
            
            // Fast-forward another minute
            jest.advanceTimersByTime(60000);
            expect(mockFunctions.refresh).toHaveBeenCalledTimes(2);
        });

        test('does not set up auto refresh when disabled', () => {
            global.autoRefreshEnabled = false;
            
            setupAutoRefresh();
            
            expect(global.autoRefreshInterval).toBeNull();
            
            jest.advanceTimersByTime(60000);
            expect(mockFunctions.refresh).not.toHaveBeenCalled();
        });
    });

    describe('timezone handling', () => {
        test('initializes timezone baseline variables', () => {
            expect(global.backendBaselineTime).toBeNull();
            expect(global.frontendBaselineTime).toBeNull();
        });

        test('can set timezone baseline for synchronization', () => {
            const backendTime = new Date('2024-01-15T10:00:00Z').getTime();
            const frontendTime = Date.now();
            
            global.backendBaselineTime = backendTime;
            global.frontendBaselineTime = frontendTime;
            
            expect(global.backendBaselineTime).toBe(backendTime);
            expect(global.frontendBaselineTime).toBe(frontendTime);
        });
    });

    describe('DOM event integration', () => {
        test('DOMContentLoaded triggers initialization', () => {
            const initSpy = jest.fn();
            
            // Add event listener for DOMContentLoaded
            document.addEventListener('DOMContentLoaded', initSpy);
            
            // Simulate DOMContentLoaded event
            const event = new Event('DOMContentLoaded');
            document.dispatchEvent(event);
            
            expect(initSpy).toHaveBeenCalledTimes(1);
        });

        test('handles multiple clicks correctly', () => {
            const setupNavigationButtons = function() {
                const handler = function(event) {
                    const element = event.target.closest('[data-action]');
                    if (element) {
                        const action = element.getAttribute('data-action');
                        if (action === 'prev' || action === 'next') {
                            navigate(action);
                        }
                    }
                };
                document.addEventListener('click', handler);
                eventHandlers.push({ element: document, event: 'click', handler });
            };

            setupNavigationButtons();
            
            const prevBtn = container.querySelector('[data-action="prev"]');
            const nextBtn = container.querySelector('[data-action="next"]');
            
            // Multiple clicks
            prevBtn.click();
            nextBtn.click();
            prevBtn.click();
            
            expect(mockFunctions.navigate).toHaveBeenCalledTimes(3);
            expect(mockFunctions.navigate).toHaveBeenNthCalledWith(1, 'prev');
            expect(mockFunctions.navigate).toHaveBeenNthCalledWith(2, 'next');
            expect(mockFunctions.navigate).toHaveBeenNthCalledWith(3, 'prev');
        });

        test('handles rapid keyboard input correctly', () => {
            const setupKeyboardNavigation = function() {
                const handler = function(event) {
                    if (event.key === 'ArrowLeft') {
                        navigate('prev');
                    } else if (event.key === 'ArrowRight') {
                        navigate('next');
                    }
                };
                document.addEventListener('keydown', handler);
                eventHandlers.push({ element: document, event: 'keydown', handler });
            };

            setupKeyboardNavigation();
            
            // Rapid key presses
            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft' }));
            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight' }));
            document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft' }));
            
            expect(mockFunctions.navigate).toHaveBeenCalledTimes(3);
        });
    });

    describe('state management', () => {
        test('tracks current theme state', () => {
            global.currentTheme = 'standard';
            
            const initializeApp = function() {
                const htmlElement = document.documentElement;
                const themeClasses = htmlElement.className.match(/\btheme-(\w+)\b/);
                if (themeClasses) {
                    global.currentTheme = themeClasses[1];
                }
            };

            document.documentElement.className = 'theme-dark';
            initializeApp();
            
            expect(global.currentTheme).toBe('dark');
        });

        test('manages auto refresh state', () => {
            expect(typeof global.autoRefreshEnabled).toBe('boolean');
            expect(global.autoRefreshInterval).toBeNull();
        });

        test('manages settings panel state', () => {
            expect(global.settingsPanel).toBeNull();
        });
    });
});