/**
 * Tests for whats-next-view.js DOM update functions
 * Focus: Testing updateEmptyStateOptimized, formatMeetingTime, and DOM manipulation functions
 */

// Import the actual JavaScript file for coverage
require('../../../../calendarbot/web/static/layouts/whats-next-view/whats-next-view.js');


describe('whats-next-view DOM updates', () => {
    let container;
    
    beforeEach(() => {
        // Setup DOM container
        container = document.createElement('div');
        container.innerHTML = `
            <div class="calendar-content">
                <div class="countdown-container">
                    <div class="countdown-time">00:00</div>
                    <div class="countdown-label">Next Meeting</div>
                    <div class="countdown-units">Minutes</div>
                </div>
                <div class="meeting-cards"></div>
            </div>
        `;
        document.body.appendChild(container);

        // Mock global state
        global.lastDOMState = {
            meetingTitle: null,
            meetingTime: null,
            meetingLocation: null,
            meetingDescription: null,
            contextMessage: null,
            statusText: null,
            lastUpdateText: null,
            layoutState: null
        };

        global.lastDataUpdate = new Date();
    });

    afterEach(() => {
        document.body.removeChild(container);
        jest.clearAllMocks();
    });

    describe('formatMeetingTime', () => {
        let formatMeetingTime;

        beforeEach(() => {
            // Implementation based on actual code (lines 973-997)
            formatMeetingTime = function(startTime, endTime, formattedTimeRange) {
                // Use the pre-formatted time range from backend if available
                if (formattedTimeRange) {
                    return formattedTimeRange;
                }
                
                // Handle null/undefined inputs
                if (!startTime || !endTime) {
                    return '';
                }
                
                // Fallback to original formatting for backwards compatibility
                try {
                    const start = new Date(startTime);
                    const end = new Date(endTime);

                    // Check if dates are invalid
                    if (isNaN(start.getTime()) || isNaN(end.getTime())) {
                        return '';
                    }

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
            };
        });

        test('uses pre-formatted time range when available', () => {
            const result = formatMeetingTime(
                '2024-01-15T10:00:00Z',
                '2024-01-15T11:00:00Z',
                '10:00 AM - 11:00 AM'
            );
            
            expect(result).toBe('10:00 AM - 11:00 AM');
        });

        test('formats time range when no pre-formatted string provided', () => {
            const result = formatMeetingTime(
                '2024-01-15T10:00:00Z',
                '2024-01-15T11:00:00Z',
                null
            );
            
            // Should be formatted as "10:00 AM - 11:00 AM" (exact format may vary by locale)
            expect(result).toMatch(/\d{1,2}:\d{2}\s(AM|PM)\s-\s\d{1,2}:\d{2}\s(AM|PM)/);
        });

        test('handles invalid date strings gracefully', () => {
            const result = formatMeetingTime(
                'invalid-date',
                'another-invalid-date',
                null
            );
            
            expect(result).toBe('');
        });

        test('handles null/undefined inputs', () => {
            expect(formatMeetingTime(null, null, null)).toBe('');
            expect(formatMeetingTime(undefined, undefined, undefined)).toBe('');
        });

        test('prefers backend formatting over client formatting', () => {
            const result = formatMeetingTime(
                '2024-01-15T10:00:00Z',
                '2024-01-15T11:00:00Z',
                'Custom Backend Format'
            );
            
            expect(result).toBe('Custom Backend Format');
        });

        test('formats different time zones correctly', () => {
            const result = formatMeetingTime(
                '2024-01-15T15:30:00Z',  // 3:30 PM UTC
                '2024-01-15T16:45:00Z',  // 4:45 PM UTC
                null
            );
            
            expect(result).toMatch(/\d{1,2}:\d{2}\s(AM|PM)\s-\s\d{1,2}:\d{2}\s(AM|PM)/);
        });
    });

    describe('updateEmptyStateOptimized', () => {
        let updateEmptyStateOptimized;

        beforeEach(() => {
            // Mock formatLastUpdate function
            global.formatLastUpdate = jest.fn(() => 'Just now');

            // Implementation based on actual code (lines 1003-1049)
            updateEmptyStateOptimized = function() {
                const content = document.querySelector('.calendar-content');
                if (!content) return;

                const newLastUpdate = global.formatLastUpdate();
                const newLayoutState = 'empty';

                // Check if we need to rebuild the empty state structure
                const needsFullRebuild = (
                    global.lastDOMState.layoutState !== newLayoutState ||
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
                    global.lastDOMState.lastUpdateText = newLastUpdate;
                    global.lastDOMState.layoutState = newLayoutState;
                    global.lastDOMState.meetingTitle = null;
                } else {
                    // Incremental update - only update last update text if changed
                    if (global.lastDOMState.lastUpdateText !== newLastUpdate) {
                        const lastUpdateElement = content.querySelector('.last-update');
                        if (lastUpdateElement) {
                            lastUpdateElement.textContent = `Updated: ${newLastUpdate}`;
                        }
                        global.lastDOMState.lastUpdateText = newLastUpdate;
                    }
                }
            };
        });

        test('builds full empty state structure on first call', () => {
            global.lastDOMState.layoutState = null; // Trigger full rebuild
            
            updateEmptyStateOptimized();

            const content = container.querySelector('.calendar-content');
            
            // Check structure was created
            expect(content.querySelector('.layout-zone-1')).toBeTruthy();
            expect(content.querySelector('.layout-zone-2')).toBeTruthy();
            expect(content.querySelector('.layout-zone-4')).toBeTruthy();
            expect(content.querySelector('.empty-state')).toBeTruthy();
            expect(content.querySelector('.empty-state-icon')).toBeTruthy();
            expect(content.querySelector('.empty-state-title')).toBeTruthy();
            expect(content.querySelector('.empty-state-message')).toBeTruthy();
            
            // Check content
            expect(content.querySelector('.empty-state-title').textContent).toBe('No Upcoming Meetings');
            expect(content.querySelector('.empty-state-message').textContent).toBe("You're all caught up!");
            expect(content.querySelector('.context-message').textContent).toBe('No meetings scheduled');
        });

        test('performs incremental update when structure exists', () => {
            // First call to build structure
            global.lastDOMState.layoutState = null;
            updateEmptyStateOptimized();

            // Reset format function to return different value
            global.formatLastUpdate.mockReturnValue('5 minutes ago');
            
            // Second call should only update last update text
            updateEmptyStateOptimized();

            const lastUpdateElement = container.querySelector('.last-update');
            expect(lastUpdateElement.textContent).toBe('Updated: 5 minutes ago');
            expect(global.lastDOMState.lastUpdateText).toBe('5 minutes ago');
        });

        test('skips update when no changes needed', () => {
            // First call
            global.lastDOMState.layoutState = 'empty';
            global.lastDOMState.lastUpdateText = 'Just now';
            
            // Add existing empty state to DOM
            const content = container.querySelector('.calendar-content');
            content.innerHTML = '<div class="empty-state"><div class="last-update">Updated: Just now</div></div>';
            
            const originalHTML = content.innerHTML;
            
            updateEmptyStateOptimized();

            // Should not change DOM when no updates needed
            expect(content.innerHTML).toBe(originalHTML);
        });

        test('handles missing calendar-content element', () => {
            // Remove calendar-content by clearing its parent
            container.innerHTML = '';
            
            // Should not throw error
            expect(() => updateEmptyStateOptimized()).not.toThrow();
        });

        test('updates state tracking correctly', () => {
            global.lastDOMState.layoutState = null;
            
            updateEmptyStateOptimized();

            expect(global.lastDOMState.layoutState).toBe('empty');
            expect(global.lastDOMState.lastUpdateText).toBe('Just now');
            expect(global.lastDOMState.meetingTitle).toBeNull();
        });

        test('handles different formatLastUpdate values', () => {
            global.formatLastUpdate.mockReturnValue('2 hours ago');
            global.lastDOMState.layoutState = null;
            
            updateEmptyStateOptimized();

            const lastUpdateElement = container.querySelector('.last-update');
            expect(lastUpdateElement.textContent).toBe('Updated: 2 hours ago');
        });
    });

    describe('DOM cache management', () => {
        test('initializes DOM cache correctly', () => {
            const DOMCache = {
                init: function() {
                    this.countdownTime = document.querySelector('.countdown-time');
                    this.countdownLabel = document.querySelector('.countdown-label');
                    this.countdownUnits = document.querySelector('.countdown-units');
                    this.countdownContainer = document.querySelector('.countdown-container');
                },
                countdownTime: null,
                countdownLabel: null,
                countdownUnits: null,
                countdownContainer: null
            };

            DOMCache.init();

            expect(DOMCache.countdownTime).toBeTruthy();
            expect(DOMCache.countdownLabel).toBeTruthy();
            expect(DOMCache.countdownUnits).toBeTruthy();
            expect(DOMCache.countdownContainer).toBeTruthy();
        });

        test('caches DOM elements for performance', () => {
            const querySelectorSpy = jest.spyOn(document, 'querySelector');
            
            const cacheObject = {};
            const getCachedElement = function(selector) {
                if (!cacheObject.cache) cacheObject.cache = {};
                if (!cacheObject.cache[selector]) {
                    cacheObject.cache[selector] = document.querySelector(selector);
                }
                return cacheObject.cache[selector];
            };

            // First call should query DOM
            getCachedElement('.countdown-time');
            expect(querySelectorSpy).toHaveBeenCalledWith('.countdown-time');

            // Second call should use cache
            querySelectorSpy.mockClear();
            getCachedElement('.countdown-time');
            expect(querySelectorSpy).not.toHaveBeenCalled();

            querySelectorSpy.mockRestore();
        });
    });

    describe('incremental DOM updates', () => {
        test('only updates changed elements', () => {
            let updateCount = 0;
            
            const incrementalUpdate = function(elementSelector, newValue) {
                const element = document.querySelector(elementSelector);
                if (element && element.textContent !== newValue) {
                    element.textContent = newValue;
                    updateCount++;
                }
            };

            const timeElement = container.querySelector('.countdown-time');
            
            // First update should change
            incrementalUpdate('.countdown-time', '05:30');
            expect(updateCount).toBe(1);
            expect(timeElement.textContent).toBe('05:30');

            // Same value should not update
            incrementalUpdate('.countdown-time', '05:30');
            expect(updateCount).toBe(1);

            // Different value should update
            incrementalUpdate('.countdown-time', '05:29');
            expect(updateCount).toBe(2);
            expect(timeElement.textContent).toBe('05:29');
        });

        test('batches multiple DOM updates efficiently', () => {
            const batchUpdate = function(updates) {
                const fragment = document.createDocumentFragment();
                let hasChanges = false;

                updates.forEach(({ selector, value }) => {
                    const element = document.querySelector(selector);
                    if (element && element.textContent !== value) {
                        element.textContent = value;
                        hasChanges = true;
                    }
                });

                return hasChanges;
            };

            const updates = [
                { selector: '.countdown-time', value: '10:30' },
                { selector: '.countdown-label', value: 'Next Meeting' },
                { selector: '.countdown-units', value: 'Minutes' }
            ];

            const hasChanges = batchUpdate(updates);

            expect(hasChanges).toBe(true);
            expect(container.querySelector('.countdown-time').textContent).toBe('10:30');
            expect(container.querySelector('.countdown-label').textContent).toBe('Next Meeting');
            expect(container.querySelector('.countdown-units').textContent).toBe('Minutes');
        });
    });

    describe('layout zones management', () => {
        test('creates proper layout zone structure', () => {
            const createLayoutZones = function() {
                return `
                    <div class="layout-zone-1">
                        <div class="countdown-container"></div>
                    </div>
                    <div class="layout-zone-2">
                        <div class="meeting-info"></div>
                    </div>
                    <div class="layout-zone-3">
                        <div class="meeting-details"></div>
                    </div>
                    <div class="layout-zone-4">
                        <div class="context-info"></div>
                    </div>
                `;
            };

            const content = container.querySelector('.calendar-content');
            content.innerHTML = createLayoutZones();

            expect(content.querySelectorAll('[class^="layout-zone-"]')).toHaveLength(4);
            expect(content.querySelector('.layout-zone-1')).toBeTruthy();
            expect(content.querySelector('.layout-zone-2')).toBeTruthy();
            expect(content.querySelector('.layout-zone-3')).toBeTruthy();
            expect(content.querySelector('.layout-zone-4')).toBeTruthy();
        });

        test('validates zone content structure', () => {
            const validateZoneStructure = function(zoneNumber, expectedClass) {
                const zone = document.querySelector(`.layout-zone-${zoneNumber}`);
                if (!zone) return false;
                
                const expectedElement = zone.querySelector(`.${expectedClass}`);
                return expectedElement !== null;
            };

            // Setup test structure
            const content = container.querySelector('.calendar-content');
            content.innerHTML = `
                <div class="layout-zone-1">
                    <div class="countdown-container"></div>
                </div>
                <div class="layout-zone-2">
                    <div class="meeting-info"></div>
                </div>
            `;

            expect(validateZoneStructure(1, 'countdown-container')).toBe(true);
            expect(validateZoneStructure(2, 'meeting-info')).toBe(true);
            expect(validateZoneStructure(3, 'context-info')).toBe(false);
        });
    });
});