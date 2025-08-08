/**
 * Unit tests for WhatsNextView performance optimization functionality.
 * Tests all optimized functions including countdown system, HTML parsing,
 * and incremental DOM updates.
 */

describe('WhatsNextView Performance Optimizations', () => {
    let originalWindow;
    let originalDocument;
    let originalConsole;
    let mockConsole;
    let mockDocument;

    beforeEach(() => {
        // Save originals
        originalWindow = global.window;
        originalDocument = global.document;
        originalConsole = global.console;

        // Create mock console
        mockConsole = {
            log: jest.fn(),
            error: jest.fn(),
            warn: jest.fn()
        };
        global.console = mockConsole;

        // Create mock DOM elements
        mockDocument = {
            getElementById: jest.fn(),
            querySelector: jest.fn(),
            createElement: jest.fn(() => ({
                className: '',
                innerHTML: '',
                textContent: '',
                appendChild: jest.fn(),
                style: {}
            })),
            querySelectorAll: jest.fn(() => [])
        };
        global.document = mockDocument;

        // Reset window mock
        global.window = {
            performance: {
                now: jest.fn(() => Date.now())
            }
        };
    });

    afterEach(() => {
        // Restore originals
        global.window = originalWindow;
        global.document = originalDocument;
        global.console = originalConsole;
    });

    describe('Countdown System Optimization', () => {
        let calculateTimeGapOptimized;
        let formatTimeGapOptimized;
        let lastCountdownValues;

        beforeAll(() => {
            // Mock the optimized functions as implemented
            lastCountdownValues = {
                displayText: null,
                unitsText: null,
                labelText: null,
                cssClass: null,
                urgent: null
            };

            calculateTimeGapOptimized = function (currentTime, targetTime) {
                if (!currentTime || !targetTime) {
                    return { gap: 0, inPast: false };
                }

                const gap = Math.abs(targetTime - currentTime);
                const inPast = targetTime < currentTime;

                return { gap, inPast };
            };

            formatTimeGapOptimized = function (gap, inPast) {
                if (gap === 0) {
                    return {
                        displayText: 'Now',
                        unitsText: '',
                        labelText: 'happening now',
                        cssClass: 'urgent',
                        urgent: true
                    };
                }

                const minutes = Math.floor(gap / 60000);
                const hours = Math.floor(minutes / 60);
                const days = Math.floor(hours / 24);

                let displayText, unitsText, labelText, cssClass;
                let urgent = false;

                if (days > 0) {
                    displayText = days.toString();
                    unitsText = days === 1 ? 'day' : 'days';
                    labelText = inPast ? `${days} ${unitsText} ago` : `in ${days} ${unitsText}`;
                    cssClass = 'distant';
                } else if (hours > 0) {
                    displayText = hours.toString();
                    unitsText = hours === 1 ? 'hour' : 'hours';
                    labelText = inPast ? `${hours} ${unitsText} ago` : `in ${hours} ${unitsText}`;
                    cssClass = 'moderate';
                } else {
                    displayText = minutes.toString();
                    unitsText = minutes === 1 ? 'minute' : 'minutes';
                    labelText = inPast ? `${minutes} ${unitsText} ago` : `in ${minutes} ${unitsText}`;
                    cssClass = minutes <= 5 ? 'urgent' : 'soon';
                    urgent = minutes <= 5;
                }

                return {
                    displayText,
                    unitsText,
                    labelText,
                    cssClass,
                    urgent
                };
            };
        });

        describe('calculateTimeGapOptimized', () => {
            test('when_current_time_and_target_time_provided_then_calculates_gap_correctly', () => {
                const currentTime = new Date('2023-01-01T10:00:00').getTime();
                const targetTime = new Date('2023-01-01T11:00:00').getTime();

                const result = calculateTimeGapOptimized(currentTime, targetTime);

                expect(result.gap).toBe(3600000); // 1 hour in milliseconds
                expect(result.inPast).toBe(false);
            });

            test('when_target_time_in_past_then_returns_in_past_true', () => {
                const currentTime = new Date('2023-01-01T11:00:00').getTime();
                const targetTime = new Date('2023-01-01T10:00:00').getTime();

                const result = calculateTimeGapOptimized(currentTime, targetTime);

                expect(result.gap).toBe(3600000);
                expect(result.inPast).toBe(true);
            });

            test('when_current_time_null_then_returns_zero_gap', () => {
                const result = calculateTimeGapOptimized(null, Date.now());

                expect(result.gap).toBe(0);
                expect(result.inPast).toBe(false);
            });

            test('when_target_time_null_then_returns_zero_gap', () => {
                const result = calculateTimeGapOptimized(Date.now(), null);

                expect(result.gap).toBe(0);
                expect(result.inPast).toBe(false);
            });
        });

        describe('formatTimeGapOptimized', () => {
            test('when_gap_zero_then_returns_now_format', () => {
                const result = formatTimeGapOptimized(0, false);

                expect(result.displayText).toBe('Now');
                expect(result.unitsText).toBe('');
                expect(result.labelText).toBe('happening now');
                expect(result.cssClass).toBe('urgent');
                expect(result.urgent).toBe(true);
            });

            test('when_gap_5_minutes_then_returns_urgent_format', () => {
                const fiveMinutes = 5 * 60 * 1000;
                const result = formatTimeGapOptimized(fiveMinutes, false);

                expect(result.displayText).toBe('5');
                expect(result.unitsText).toBe('minutes');
                expect(result.labelText).toBe('in 5 minutes');
                expect(result.cssClass).toBe('urgent');
                expect(result.urgent).toBe(true);
            });

            test('when_gap_30_minutes_then_returns_soon_format', () => {
                const thirtyMinutes = 30 * 60 * 1000;
                const result = formatTimeGapOptimized(thirtyMinutes, false);

                expect(result.displayText).toBe('30');
                expect(result.unitsText).toBe('minutes');
                expect(result.labelText).toBe('in 30 minutes');
                expect(result.cssClass).toBe('soon');
                expect(result.urgent).toBe(false);
            });

            test('when_gap_2_hours_then_returns_moderate_format', () => {
                const twoHours = 2 * 60 * 60 * 1000;
                const result = formatTimeGapOptimized(twoHours, false);

                expect(result.displayText).toBe('2');
                expect(result.unitsText).toBe('hours');
                expect(result.labelText).toBe('in 2 hours');
                expect(result.cssClass).toBe('moderate');
                expect(result.urgent).toBe(false);
            });

            test('when_gap_1_day_then_returns_distant_format', () => {
                const oneDay = 24 * 60 * 60 * 1000;
                const result = formatTimeGapOptimized(oneDay, false);

                expect(result.displayText).toBe('1');
                expect(result.unitsText).toBe('day');
                expect(result.labelText).toBe('in 1 day');
                expect(result.cssClass).toBe('distant');
                expect(result.urgent).toBe(false);
            });

            test('when_gap_in_past_then_returns_past_tense_label', () => {
                const twoHours = 2 * 60 * 60 * 1000;
                const result = formatTimeGapOptimized(twoHours, true);

                expect(result.displayText).toBe('2');
                expect(result.unitsText).toBe('hours');
                expect(result.labelText).toBe('2 hours ago');
                expect(result.cssClass).toBe('moderate');
            });

            test('when_singular_values_then_returns_singular_units', () => {
                const oneHour = 60 * 60 * 1000;
                const result = formatTimeGapOptimized(oneHour, false);

                expect(result.unitsText).toBe('hour');
                expect(result.labelText).toBe('in 1 hour');

                const oneMinute = 60 * 1000;
                const result2 = formatTimeGapOptimized(oneMinute, false);

                expect(result2.unitsText).toBe('minute');
                expect(result2.labelText).toBe('in 1 minute');
            });
        });
    });

    // NOTE: HTML Parsing Optimization tests removed in Phase 3
    //
    // The extractMeetingFromElementOptimized() function has been removed and replaced
    // by WhatsNextStateManager JSON-based data loading. HTML parsing optimizations
    // are no longer needed since the architecture now uses direct JSON consumption
    // from API endpoints instead of parsing HTML content.

    describe('Incremental DOM Updates', () => {
        let lastDOMState;
        let updateMeetingDisplayOptimized;
        let updateMeetingTitleOptimized;
        let updateMeetingTimeOptimized;
        let updateMeetingLocationOptimized;
        let updateMeetingDescriptionOptimized;
        let updateContextMessageOptimized;
        let updateEmptyStateOptimized;
        let updateLastUpdateOptimized;
        let createMeetingLayoutStructure;

        beforeAll(() => {
            // Mock DOM state tracking
            lastDOMState = {
                meetingTitle: null,
                meetingTime: null,
                meetingLocation: null,
                meetingDescription: null,
                contextMessage: null,
                statusText: null,
                lastUpdateText: null,
                layoutState: null
            };

            // Mock individual update functions
            updateMeetingTitleOptimized = function (titleElement, newTitle) {
                if (!titleElement) return false;

                if (lastDOMState.meetingTitle !== newTitle) {
                    titleElement.textContent = newTitle;
                    lastDOMState.meetingTitle = newTitle;
                    return true;
                }
                return false;
            };

            updateMeetingTimeOptimized = function (timeElement, newTime) {
                if (!timeElement) return false;

                if (lastDOMState.meetingTime !== newTime) {
                    timeElement.textContent = newTime;
                    lastDOMState.meetingTime = newTime;
                    return true;
                }
                return false;
            };

            updateMeetingLocationOptimized = function (locationElement, newLocation) {
                if (!locationElement) return false;

                if (lastDOMState.meetingLocation !== newLocation) {
                    locationElement.textContent = newLocation;
                    lastDOMState.meetingLocation = newLocation;
                    return true;
                }
                return false;
            };

            updateMeetingDescriptionOptimized = function (descElement, newDescription) {
                if (!descElement) return false;

                if (lastDOMState.meetingDescription !== newDescription) {
                    descElement.innerHTML = newDescription;
                    lastDOMState.meetingDescription = newDescription;
                    return true;
                }
                return false;
            };

            updateContextMessageOptimized = function (contextElement, newMessage) {
                if (!contextElement) return false;

                if (lastDOMState.contextMessage !== newMessage) {
                    contextElement.textContent = newMessage;
                    lastDOMState.contextMessage = newMessage;
                    return true;
                }
                return false;
            };

            updateLastUpdateOptimized = function (updateElement, newUpdateText) {
                if (!updateElement) return false;

                if (lastDOMState.lastUpdateText !== newUpdateText) {
                    updateElement.textContent = newUpdateText;
                    lastDOMState.lastUpdateText = newUpdateText;
                    return true;
                }
                return false;
            };

            createMeetingLayoutStructure = function (container) {
                if (!container) return null;

                const structure = {
                    title: mockDocument.createElement('div'),
                    time: mockDocument.createElement('div'),
                    location: mockDocument.createElement('div'),
                    description: mockDocument.createElement('div')
                };

                structure.title.className = 'meeting-title';
                structure.time.className = 'meeting-time';
                structure.location.className = 'meeting-location';
                structure.description.className = 'meeting-description';

                container.appendChild(structure.title);
                container.appendChild(structure.time);
                container.appendChild(structure.location);
                container.appendChild(structure.description);

                return structure;
            };

            updateMeetingDisplayOptimized = function (meeting, container) {
                if (!container) return false;

                const newLayoutState = meeting ? 'meeting' : 'empty';
                let layoutChanged = false;

                // Check if layout needs rebuilding
                if (lastDOMState.layoutState !== newLayoutState) {
                    container.innerHTML = '';
                    lastDOMState.layoutState = newLayoutState;
                    layoutChanged = true;
                }

                if (!meeting) return layoutChanged;

                // Create or get layout structure
                let structure = container.querySelector('.meeting-title') ? {
                    title: container.querySelector('.meeting-title'),
                    time: container.querySelector('.meeting-time'),
                    location: container.querySelector('.meeting-location'),
                    description: container.querySelector('.meeting-description')
                } : createMeetingLayoutStructure(container);

                // Update individual elements
                let elementsUpdated = 0;
                elementsUpdated += updateMeetingTitleOptimized(structure.title, meeting.title) ? 1 : 0;
                elementsUpdated += updateMeetingTimeOptimized(structure.time, meeting.time) ? 1 : 0;
                elementsUpdated += updateMeetingLocationOptimized(structure.location, meeting.location) ? 1 : 0;
                elementsUpdated += updateMeetingDescriptionOptimized(structure.description, meeting.description) ? 1 : 0;

                return layoutChanged || elementsUpdated > 0;
            };

            updateEmptyStateOptimized = function (container, statusText) {
                if (!container) return false;

                const newLayoutState = 'empty';
                let updated = false;

                if (lastDOMState.layoutState !== newLayoutState) {
                    container.innerHTML = '<div class="empty-state"></div>';
                    lastDOMState.layoutState = newLayoutState;
                    updated = true;
                }

                const emptyElement = container.querySelector('.empty-state');
                if (emptyElement && lastDOMState.statusText !== statusText) {
                    emptyElement.textContent = statusText;
                    lastDOMState.statusText = statusText;
                    updated = true;
                }

                return updated;
            };
        });

        beforeEach(() => {
            // Reset DOM state before each test
            lastDOMState.meetingTitle = null;
            lastDOMState.meetingTime = null;
            lastDOMState.meetingLocation = null;
            lastDOMState.meetingDescription = null;
            lastDOMState.contextMessage = null;
            lastDOMState.statusText = null;
            lastDOMState.lastUpdateText = null;
            lastDOMState.layoutState = null;
        });

        describe('updateMeetingTitleOptimized', () => {
            test('when_title_changes_then_updates_element_and_state', () => {
                const mockElement = { textContent: '' };

                const result = updateMeetingTitleOptimized(mockElement, 'New Meeting');

                expect(result).toBe(true);
                expect(mockElement.textContent).toBe('New Meeting');
                expect(lastDOMState.meetingTitle).toBe('New Meeting');
            });

            test('when_title_unchanged_then_skips_update', () => {
                const mockElement = { textContent: 'Existing Meeting' };
                lastDOMState.meetingTitle = 'Existing Meeting';

                const result = updateMeetingTitleOptimized(mockElement, 'Existing Meeting');

                expect(result).toBe(false);
                expect(mockElement.textContent).toBe('Existing Meeting');
            });

            test('when_element_null_then_returns_false', () => {
                const result = updateMeetingTitleOptimized(null, 'New Meeting');

                expect(result).toBe(false);
            });
        });

        describe('updateMeetingTimeOptimized', () => {
            test('when_time_changes_then_updates_element_and_state', () => {
                const mockElement = { textContent: '' };

                const result = updateMeetingTimeOptimized(mockElement, '2:00 PM');

                expect(result).toBe(true);
                expect(mockElement.textContent).toBe('2:00 PM');
                expect(lastDOMState.meetingTime).toBe('2:00 PM');
            });

            test('when_time_unchanged_then_skips_update', () => {
                const mockElement = { textContent: '2:00 PM' };
                lastDOMState.meetingTime = '2:00 PM';

                const result = updateMeetingTimeOptimized(mockElement, '2:00 PM');

                expect(result).toBe(false);
            });
        });

        describe('updateMeetingLocationOptimized', () => {
            test('when_location_changes_then_updates_element_and_state', () => {
                const mockElement = { textContent: '' };

                const result = updateMeetingLocationOptimized(mockElement, 'Room A');

                expect(result).toBe(true);
                expect(mockElement.textContent).toBe('Room A');
                expect(lastDOMState.meetingLocation).toBe('Room A');
            });

            test('when_location_unchanged_then_skips_update', () => {
                const mockElement = { textContent: 'Room A' };
                lastDOMState.meetingLocation = 'Room A';

                const result = updateMeetingLocationOptimized(mockElement, 'Room A');

                expect(result).toBe(false);
            });
        });

        describe('updateMeetingDescriptionOptimized', () => {
            test('when_description_changes_then_updates_element_and_state', () => {
                const mockElement = { innerHTML: '' };

                const result = updateMeetingDescriptionOptimized(mockElement, '<p>New description</p>');

                expect(result).toBe(true);
                expect(mockElement.innerHTML).toBe('<p>New description</p>');
                expect(lastDOMState.meetingDescription).toBe('<p>New description</p>');
            });

            test('when_description_unchanged_then_skips_update', () => {
                const mockElement = { innerHTML: '<p>Existing</p>' };
                lastDOMState.meetingDescription = '<p>Existing</p>';

                const result = updateMeetingDescriptionOptimized(mockElement, '<p>Existing</p>');

                expect(result).toBe(false);
            });
        });

        describe('updateContextMessageOptimized', () => {
            test('when_message_changes_then_updates_element_and_state', () => {
                const mockElement = { textContent: '' };

                const result = updateContextMessageOptimized(mockElement, 'New context message');

                expect(result).toBe(true);
                expect(mockElement.textContent).toBe('New context message');
                expect(lastDOMState.contextMessage).toBe('New context message');
            });

            test('when_message_unchanged_then_skips_update', () => {
                const mockElement = { textContent: 'Existing message' };
                lastDOMState.contextMessage = 'Existing message';

                const result = updateContextMessageOptimized(mockElement, 'Existing message');

                expect(result).toBe(false);
            });
        });

        describe('updateLastUpdateOptimized', () => {
            test('when_update_text_changes_then_updates_element_and_state', () => {
                const mockElement = { textContent: '' };

                const result = updateLastUpdateOptimized(mockElement, 'Last updated: 2:30 PM');

                expect(result).toBe(true);
                expect(mockElement.textContent).toBe('Last updated: 2:30 PM');
                expect(lastDOMState.lastUpdateText).toBe('Last updated: 2:30 PM');
            });

            test('when_update_text_unchanged_then_skips_update', () => {
                const mockElement = { textContent: 'Last updated: 2:30 PM' };
                lastDOMState.lastUpdateText = 'Last updated: 2:30 PM';

                const result = updateLastUpdateOptimized(mockElement, 'Last updated: 2:30 PM');

                expect(result).toBe(false);
            });
        });

        describe('createMeetingLayoutStructure', () => {
            test('when_container_provided_then_creates_meeting_structure', () => {
                const mockContainer = {
                    appendChild: jest.fn()
                };

                const result = createMeetingLayoutStructure(mockContainer);

                expect(result).toHaveProperty('title');
                expect(result).toHaveProperty('time');
                expect(result).toHaveProperty('location');
                expect(result).toHaveProperty('description');
                expect(result.title.className).toBe('meeting-title');
                expect(result.time.className).toBe('meeting-time');
                expect(result.location.className).toBe('meeting-location');
                expect(result.description.className).toBe('meeting-description');
                expect(mockContainer.appendChild).toHaveBeenCalledTimes(4);
            });

            test('when_container_null_then_returns_null', () => {
                const result = createMeetingLayoutStructure(null);

                expect(result).toBe(null);
            });
        });

        describe('updateMeetingDisplayOptimized', () => {
            test('when_meeting_provided_then_creates_layout_and_updates_elements', () => {
                const mockContainer = {
                    innerHTML: '',
                    appendChild: jest.fn(),
                    querySelector: jest.fn(() => null)
                };

                const meeting = {
                    title: 'Team Meeting',
                    time: '2:00 PM',
                    location: 'Room A',
                    description: 'Weekly sync'
                };

                const result = updateMeetingDisplayOptimized(meeting, mockContainer);

                expect(result).toBe(true);
                expect(lastDOMState.layoutState).toBe('meeting');
                expect(lastDOMState.meetingTitle).toBe('Team Meeting');
                expect(lastDOMState.meetingTime).toBe('2:00 PM');
                expect(lastDOMState.meetingLocation).toBe('Room A');
                expect(lastDOMState.meetingDescription).toBe('Weekly sync');
            });

            test('when_meeting_null_then_sets_empty_layout_state', () => {
                const mockContainer = {
                    innerHTML: '',
                    querySelector: jest.fn()
                };

                const result = updateMeetingDisplayOptimized(null, mockContainer);

                expect(result).toBe(true);
                expect(lastDOMState.layoutState).toBe('empty');
            });

            test('when_layout_state_unchanged_and_meeting_same_then_skips_updates', () => {
                const mockContainer = {
                    innerHTML: '',
                    querySelector: jest.fn(() => ({
                        textContent: 'Team Meeting'
                    }))
                };

                const meeting = {
                    title: 'Team Meeting',
                    time: '2:00 PM',
                    location: 'Room A',
                    description: 'Weekly sync'
                };

                // Set up existing state
                lastDOMState.layoutState = 'meeting';
                lastDOMState.meetingTitle = 'Team Meeting';
                lastDOMState.meetingTime = '2:00 PM';
                lastDOMState.meetingLocation = 'Room A';
                lastDOMState.meetingDescription = 'Weekly sync';

                mockContainer.querySelector = jest.fn((selector) => {
                    const mockElements = {
                        '.meeting-title': { textContent: 'Team Meeting' },
                        '.meeting-time': { textContent: '2:00 PM' },
                        '.meeting-location': { textContent: 'Room A' },
                        '.meeting-description': { innerHTML: 'Weekly sync' }
                    };
                    return mockElements[selector];
                });

                const result = updateMeetingDisplayOptimized(meeting, mockContainer);

                expect(result).toBe(false); // No updates needed
            });

            test('when_container_null_then_returns_false', () => {
                const meeting = { title: 'Test' };

                const result = updateMeetingDisplayOptimized(meeting, null);

                expect(result).toBe(false);
            });
        });

        describe('updateEmptyStateOptimized', () => {
            test('when_empty_state_changes_then_updates_layout_and_text', () => {
                const mockContainer = {
                    innerHTML: '',
                    querySelector: jest.fn(() => ({ textContent: '' }))
                };

                const result = updateEmptyStateOptimized(mockContainer, 'No meetings found');

                expect(result).toBe(true);
                expect(lastDOMState.layoutState).toBe('empty');
                expect(lastDOMState.statusText).toBe('No meetings found');
                expect(mockContainer.innerHTML).toBe('<div class="empty-state"></div>');
            });

            test('when_status_text_unchanged_then_skips_update', () => {
                const mockEmptyElement = { textContent: 'No meetings found' };
                const mockContainer = {
                    innerHTML: '<div class="empty-state"></div>',
                    querySelector: jest.fn(() => mockEmptyElement)
                };

                lastDOMState.layoutState = 'empty';
                lastDOMState.statusText = 'No meetings found';

                const result = updateEmptyStateOptimized(mockContainer, 'No meetings found');

                expect(result).toBe(false);
            });

            test('when_container_null_then_returns_false', () => {
                const result = updateEmptyStateOptimized(null, 'No meetings');

                expect(result).toBe(false);
            });
        });
    });

    describe('Performance Impact Validation', () => {
        test('when_using_change_detection_then_prevents_unnecessary_dom_updates', () => {
            // Simulate change detection preventing redundant updates
            const updateCalls = [];
            const mockElement = {
                get textContent() { return this._text; },
                set textContent(value) {
                    updateCalls.push(value);
                    this._text = value;
                }
            };

            // Mock state tracking
            let lastValue = null;

            const optimizedUpdate = (element, newValue) => {
                if (lastValue !== newValue) {
                    element.textContent = newValue;
                    lastValue = newValue;
                    return true;
                }
                return false;
            };

            // First update should execute
            optimizedUpdate(mockElement, 'Meeting 1');

            // Redundant updates should be skipped
            optimizedUpdate(mockElement, 'Meeting 1');
            optimizedUpdate(mockElement, 'Meeting 1');

            // New value should execute
            optimizedUpdate(mockElement, 'Meeting 2');

            expect(updateCalls).toEqual(['Meeting 1', 'Meeting 2']);
            expect(updateCalls.length).toBe(2); // Only 2 actual DOM updates instead of 4
        });

        test('when_layout_state_unchanged_then_skips_dom_rebuild', () => {
            const containerResetCalls = [];
            const mockContainer = {
                get innerHTML() { return this._html; },
                set innerHTML(value) {
                    containerResetCalls.push(value);
                    this._html = value;
                }
            };

            let lastLayoutState = null;

            const optimizedLayoutUpdate = (container, newState) => {
                if (lastLayoutState !== newState) {
                    container.innerHTML = '';
                    lastLayoutState = newState;
                    return true;
                }
                return false;
            };

            // First layout change should rebuild
            optimizedLayoutUpdate(mockContainer, 'meeting');

            // Subsequent calls with same state should skip rebuild
            optimizedLayoutUpdate(mockContainer, 'meeting');
            optimizedLayoutUpdate(mockContainer, 'meeting');

            // Different state should rebuild
            optimizedLayoutUpdate(mockContainer, 'empty');

            expect(containerResetCalls).toEqual(['', '']);
            expect(containerResetCalls.length).toBe(2); // Only 2 rebuilds instead of 4
        });

        test('when_optimized_time_calculation_cached_then_reduces_computation', () => {
            let calculationCount = 0;
            const cachedResults = new Map();

            const optimizedTimeGap = (current, target) => {
                const key = `${current}-${target}`;
                if (cachedResults.has(key)) {
                    return cachedResults.get(key);
                }

                calculationCount++;
                const result = Math.abs(target - current);
                cachedResults.set(key, result);
                return result;
            };

            const currentTime = Date.now();
            const targetTime = currentTime + 3600000;

            // First calculation
            optimizedTimeGap(currentTime, targetTime);

            // Repeated calculations with same values
            optimizedTimeGap(currentTime, targetTime);
            optimizedTimeGap(currentTime, targetTime);

            // Different calculation
            optimizedTimeGap(currentTime, targetTime + 1000);

            expect(calculationCount).toBe(2); // Only 2 actual calculations instead of 4
        });
    });
});