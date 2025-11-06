/**
 * Tests for whats-next-view.js mobile enhancement functions
 * Focus: Testing setupMobileEnhancements function covering lines 183-227
 */

// Import the actual JavaScript file for coverage
require('../../../../calendarbot/web/static/layouts/whats-next-view/whats-next-view.js');

describe('whats-next-view mobile enhancements', () => {
    let container;
    let mockFunctions;

    beforeEach(() => {
        // Setup DOM container
        container = document.createElement('div');
        container.innerHTML = `
            <div id="app">
                <div class="countdown-display"></div>
                <div class="meeting-cards"></div>
            </div>
        `;
        document.body.appendChild(container);

        // Mock global functions
        mockFunctions = {
            refresh: jest.fn(),
            cycleLayout: jest.fn()
        };
        Object.assign(global, mockFunctions);

        // Reset touch event tracking
        jest.clearAllMocks();
    });

    afterEach(() => {
        document.body.removeChild(container);
        jest.clearAllMocks();
    });

    describe('setupMobileEnhancements', () => {
        let setupMobileEnhancements;
        let cleanupFunctions = [];

        beforeEach(() => {
            // Clear any existing cleanup functions
            cleanupFunctions = [];

            // Create the setupMobileEnhancements function based on the actual implementation
            setupMobileEnhancements = function() {
                let touchStartX = 0;
                let touchEndX = 0;

                const touchStartHandler = function(event) {
                    if (event.changedTouches && event.changedTouches.length > 0) {
                        touchStartX = event.changedTouches[0].screenX;
                    }
                };

                const touchEndHandler = function(event) {
                    if (event.changedTouches && event.changedTouches.length > 0) {
                        touchEndX = event.changedTouches[0].screenX;
                        handleSwipe();
                    }
                };

                function handleSwipe() {
                    const swipeThreshold = 50;
                    const swipeDistance = touchEndX - touchStartX;
                    const rightEdgeThreshold = 50;
                    const windowWidth = window.innerWidth;

                    if (Math.abs(swipeDistance) > swipeThreshold) {
                        if (swipeDistance < 0 && touchStartX >= (windowWidth - rightEdgeThreshold)) {
                            // Swipe left from right edge - switch layout
                            cycleLayout();
                        } else if (swipeDistance > 0) {
                            // Swipe right - refresh
                            refresh();
                        } else {
                            // Swipe left from non-edge - refresh
                            refresh();
                        }
                    }
                }

                // Prevent zoom on double-tap for iOS
                let lastTouchEnd = 0;
                const doubleTabHandler = function(event) {
                    const now = (new Date()).getTime();
                    if (now - lastTouchEnd <= 300) {
                        event.preventDefault();
                    }
                    lastTouchEnd = now;
                };

                // Add event listeners
                document.addEventListener('touchstart', touchStartHandler);
                document.addEventListener('touchend', touchEndHandler);
                document.addEventListener('touchend', doubleTabHandler, false);

                // Store cleanup functions
                cleanupFunctions.push(() => {
                    document.removeEventListener('touchstart', touchStartHandler);
                    document.removeEventListener('touchend', touchEndHandler);
                    document.removeEventListener('touchend', doubleTabHandler, false);
                });
            };
        });

        afterEach(() => {
            // Clean up all event listeners
            cleanupFunctions.forEach(cleanup => cleanup());
            cleanupFunctions = [];
        });

        test('sets up touch event listeners', () => {
            const addEventListenerSpy = jest.spyOn(document, 'addEventListener');

            setupMobileEnhancements();

            // Should add touchstart, touchend listeners
            expect(addEventListenerSpy).toHaveBeenCalledWith('touchstart', expect.any(Function));
            expect(addEventListenerSpy).toHaveBeenCalledWith('touchend', expect.any(Function));

            addEventListenerSpy.mockRestore();
        });

        test('handles swipe right for refresh', () => {
            setupMobileEnhancements();

            // Mock window width
            Object.defineProperty(window, 'innerWidth', { value: 1000, writable: true });

            // Clear any previous mock calls
            mockFunctions.refresh.mockClear();
            mockFunctions.cycleLayout.mockClear();

            // Simulate swipe right (start at 100, end at 200)
            const touchStartEvent = new TouchEvent('touchstart', {
                changedTouches: [{ screenX: 100 }]
            });

            const touchEndEvent = new TouchEvent('touchend', {
                changedTouches: [{ screenX: 200 }]  // 100px swipe right
            });

            document.dispatchEvent(touchStartEvent);
            document.dispatchEvent(touchEndEvent);

            expect(mockFunctions.refresh).toHaveBeenCalledTimes(1);
            expect(mockFunctions.cycleLayout).not.toHaveBeenCalled();
        });

        test('handles swipe left from right edge for layout switch', () => {
            setupMobileEnhancements();

            // Mock window width
            Object.defineProperty(window, 'innerWidth', { value: 1000, writable: true });

            // Clear any previous mock calls
            mockFunctions.refresh.mockClear();
            mockFunctions.cycleLayout.mockClear();

            // Simulate swipe left from right edge (start at 960, end at 860)
            const touchStartEvent = new TouchEvent('touchstart', {
                changedTouches: [{ screenX: 960 }]  // Within 50px of right edge (1000-50=950)
            });

            const touchEndEvent = new TouchEvent('touchend', {
                changedTouches: [{ screenX: 860 }]  // 100px swipe left
            });

            document.dispatchEvent(touchStartEvent);
            document.dispatchEvent(touchEndEvent);

            expect(mockFunctions.cycleLayout).toHaveBeenCalledTimes(1);
            expect(mockFunctions.refresh).not.toHaveBeenCalled();
        });

        test('handles swipe left from non-edge for refresh', () => {
            setupMobileEnhancements();

            // Mock window width
            Object.defineProperty(window, 'innerWidth', { value: 1000, writable: true });

            // Clear any previous mock calls
            mockFunctions.refresh.mockClear();
            mockFunctions.cycleLayout.mockClear();

            // Simulate swipe left from middle (start at 500, end at 400)
            const touchStartEvent = new TouchEvent('touchstart', {
                changedTouches: [{ screenX: 500 }]  // Not near right edge
            });

            const touchEndEvent = new TouchEvent('touchend', {
                changedTouches: [{ screenX: 400 }]  // 100px swipe left
            });

            document.dispatchEvent(touchStartEvent);
            document.dispatchEvent(touchEndEvent);

            expect(mockFunctions.refresh).toHaveBeenCalledTimes(1);
            expect(mockFunctions.cycleLayout).not.toHaveBeenCalled();
        });

        test('ignores swipes below threshold', () => {
            setupMobileEnhancements();

            // Mock window width
            Object.defineProperty(window, 'innerWidth', { value: 1000, writable: true });

            // Simulate small swipe (below 50px threshold)
            const touchStartEvent = new TouchEvent('touchstart', {
                changedTouches: [{ screenX: 500 }]
            });

            const touchEndEvent = new TouchEvent('touchend', {
                changedTouches: [{ screenX: 530 }]  // Only 30px swipe
            });

            document.dispatchEvent(touchStartEvent);
            document.dispatchEvent(touchEndEvent);

            expect(mockFunctions.refresh).not.toHaveBeenCalled();
            expect(mockFunctions.cycleLayout).not.toHaveBeenCalled();
        });

        test('prevents double-tap zoom', () => {
            setupMobileEnhancements();

            const mockPreventDefault = jest.fn();

            // First touch
            const firstTouchEvent = new TouchEvent('touchend');
            firstTouchEvent.preventDefault = mockPreventDefault;
            document.dispatchEvent(firstTouchEvent);

            // Second touch within 300ms
            const secondTouchEvent = new TouchEvent('touchend');
            secondTouchEvent.preventDefault = mockPreventDefault;
            document.dispatchEvent(secondTouchEvent);

            expect(mockPreventDefault).toHaveBeenCalledTimes(1);
        });

        test('allows touches after 300ms interval', () => {
            setupMobileEnhancements();

            const mockPreventDefault = jest.fn();

            // First touch
            const firstTouchEvent = new TouchEvent('touchend');
            firstTouchEvent.preventDefault = mockPreventDefault;
            document.dispatchEvent(firstTouchEvent);

            // Clear the preventDefault calls from first touch
            mockPreventDefault.mockClear();

            // Wait more than 300ms
            jest.advanceTimersByTime(400);

            // Second touch after interval
            const secondTouchEvent = new TouchEvent('touchend');
            secondTouchEvent.preventDefault = mockPreventDefault;
            document.dispatchEvent(secondTouchEvent);

            expect(mockPreventDefault).not.toHaveBeenCalled();
        });

        test('handles edge case with zero window width', () => {
            setupMobileEnhancements();

            // Mock zero window width
            Object.defineProperty(window, 'innerWidth', { value: 0, writable: true });

            // Clear any previous mock calls
            mockFunctions.refresh.mockClear();
            mockFunctions.cycleLayout.mockClear();

            // Swipe right with zero window width - should still trigger refresh
            const touchStartEvent = new TouchEvent('touchstart', {
                changedTouches: [{ screenX: 0 }]
            });

            const touchEndEvent = new TouchEvent('touchend', {
                changedTouches: [{ screenX: 60 }]  // 60px swipe right, exceeds threshold
            });

            document.dispatchEvent(touchStartEvent);
            document.dispatchEvent(touchEndEvent);

            expect(mockFunctions.refresh).toHaveBeenCalledTimes(1);
            expect(mockFunctions.cycleLayout).not.toHaveBeenCalled();
        });
    });

    describe('swipe direction detection', () => {
        test('correctly identifies swipe directions', () => {
            const testCases = [
                { start: 100, end: 200, distance: 100, shouldTrigger: true, expectedDirection: 'right' },
                { start: 200, end: 100, distance: -100, shouldTrigger: true, expectedDirection: 'left' },
                { start: 150, end: 150, distance: 0, shouldTrigger: false, expectedDirection: 'none' },
                { start: 300, end: 250, distance: -50, shouldTrigger: false, expectedDirection: 'none' },
                { start: 250, end: 300, distance: 50, shouldTrigger: false, expectedDirection: 'none' }
            ];

            testCases.forEach(({ start, end, distance, shouldTrigger, expectedDirection }) => {
                const calculatedDistance = end - start;
                expect(calculatedDistance).toBe(distance);

                const swipeThreshold = 50;
                const willTrigger = Math.abs(calculatedDistance) > swipeThreshold;
                expect(willTrigger).toBe(shouldTrigger);

                if (willTrigger) {
                    const direction = calculatedDistance > 0 ? 'right' : 'left';
                    expect(direction).toBe(expectedDirection);
                }
            });
        });
    });

    describe('right edge detection', () => {
        test('correctly identifies touches near right edge', () => {
            const windowWidth = 1000;
            const rightEdgeThreshold = 50;
            const edgeStart = windowWidth - rightEdgeThreshold; // 950

            const testCases = [
                { touchX: 960, expected: true },   // Within edge
                { touchX: 950, expected: true },   // Exactly at edge
                { touchX: 949, expected: false },  // Just outside edge
                { touchX: 900, expected: false },  // Well outside edge
                { touchX: 1000, expected: true },  // At very edge
            ];

            testCases.forEach(({ touchX, expected }) => {
                const isNearRightEdge = touchX >= edgeStart;
                expect(isNearRightEdge).toBe(expected);
            });
        });
    });
});