/**
 * @fileoverview Jest tests for CalendarBot Lite whatsnext.js
 * Focused test suite for the What's Next View JavaScript functionality
 */

describe('CalendarBot Lite - What\'s Next View', () => {
    let fetchMock;

    beforeEach(() => {
        // Clean up any previous instance
        if (window.calendarBotCleanup) {
            window.calendarBotCleanup();
            delete window.calendarBotCleanup;
        }

        // Set up DOM
        document.body.innerHTML = `
            <div class="countdown-container">
                <div class="countdown-time"></div>
                <div class="countdown-hours"></div>
                <div class="countdown-minutes"></div>
            </div>
            <div class="meeting-card">
                <button class="meeting-close-btn">×</button>
                <div class="meeting-title"></div>
                <div class="meeting-time"></div>
                <div class="meeting-location"></div>
            </div>
            <div class="next-meetings">
                <div class="next-meeting-time"></div>
                <div class="next-meeting-title"></div>
            </div>
        `;

        // Set document state
        Object.defineProperty(document, 'readyState', {
            writable: true,
            configurable: true,
            value: 'complete'
        });

        // Mock fetch with default empty response
        fetchMock = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ meeting: null })
            })
        );
        global.fetch = fetchMock;

        // Mock navigator
        Object.defineProperty(navigator, 'onLine', {
            writable: true,
            configurable: true,
            value: true
        });

        // Use fake timers
        jest.useFakeTimers();

        // (temporarily not suppressing console to aid debugging)
    });

    afterEach(() => {
        if (window.calendarBotCleanup) {
            window.calendarBotCleanup();
            delete window.calendarBotCleanup;
        }

        jest.clearAllTimers();
        jest.useRealTimers();

        if (console.log.mockRestore) console.log.mockRestore();
        if (console.error.mockRestore) console.error.mockRestore();

        document.body.innerHTML = '';
        jest.resetModules();
    });

    describe('Initialization', () => {
        test('should initialize and expose cleanup function', () => {
            require('../../calendarbot_lite/whatsnext.js');

            expect(typeof window.calendarBotCleanup).toBe('function');
        });

        test('should cache DOM elements on load', () => {
            const querySelectorSpy = jest.spyOn(document, 'querySelector');

            require('../../calendarbot_lite/whatsnext.js');

            expect(querySelectorSpy).toHaveBeenCalledWith('.countdown-time');
            expect(querySelectorSpy).toHaveBeenCalledWith('.meeting-title');

            querySelectorSpy.mockRestore();
        });

        test('should handle missing required elements', () => {
            document.querySelector('.countdown-time').remove();

            const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

            require('../../calendarbot_lite/whatsnext.js');

            expect(consoleErrorSpy.mock.calls.some(call =>
                call[0] && call[0].includes('Required element not found')
            )).toBe(true);

            consoleErrorSpy.mockRestore();
        });

        test('should start polling on initialization', () => {
            require('../../calendarbot_lite/whatsnext.js');

            jest.advanceTimersByTime(100);

            expect(fetchMock).toHaveBeenCalled();
        });
    });

    describe('API Calls', () => {
        test('should call /api/whats-next endpoint', async () => {
            require('../../calendarbot_lite/whatsnext.js');

            jest.advanceTimersByTime(100);
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();

            expect(fetchMock).toHaveBeenCalledWith(
                '/api/whats-next',
                expect.objectContaining({
                    method: 'GET'
                })
            );
        });

        test('should include correct headers in request', async () => {
            require('../../calendarbot_lite/whatsnext.js');

            jest.advanceTimersByTime(100);
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();

            expect(fetchMock).toHaveBeenCalledWith(
                expect.any(String),
                expect.objectContaining({
                    headers: expect.objectContaining({
                        'Accept': 'application/json',
                        'Cache-Control': 'no-cache'
                    })
                })
            );
        });

        test('should poll at 60-second intervals', async () => {
            require('../../calendarbot_lite/whatsnext.js');

            fetchMock.mockClear();

            jest.advanceTimersByTime(100);
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();
            const firstCount = fetchMock.mock.calls.filter(call => call[0] === '/api/whats-next').length;

            jest.advanceTimersByTime(60000);
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();
            const secondCount = fetchMock.mock.calls.filter(call => call[0] === '/api/whats-next').length;

            expect(secondCount).toBeGreaterThan(firstCount);
        });
    });

    describe('Display Updates - Meeting Data', () => {
        test('should update DOM with meeting title', async () => {
            fetchMock.mockImplementation(() =>
                Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        meeting: {
                            subject: 'Team Standup',
                            start_iso: new Date().toISOString(),
                            duration_seconds: 1800,
                            seconds_until_start: 900
                        }
                    })
                })
            );

            require('../../calendarbot_lite/whatsnext.js');
            jest.advanceTimersByTime(100);
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();

            const meetingTitle = document.querySelector('.meeting-title');
            expect(meetingTitle.textContent).toBe('Team Standup');
        });

        test('should display countdown in hours', async () => {
            fetchMock.mockImplementation(() =>
                Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        meeting: {
                            subject: 'Test',
                            start_iso: new Date().toISOString(),
                            duration_seconds: 3600,
                            seconds_until_start: 7200 // 2 hours
                        }
                    })
                })
            );

            require('../../calendarbot_lite/whatsnext.js');
            jest.advanceTimersByTime(100);
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();

            expect(document.querySelector('.countdown-time').textContent).toBe('2');
            expect(document.querySelector('.countdown-hours').textContent).toBe('HOURS');
        });

        test('should display countdown in minutes', async () => {
            fetchMock.mockImplementation(() =>
                Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        meeting: {
                            subject: 'Test',
                            start_iso: new Date().toISOString(),
                            duration_seconds: 3600,
                            seconds_until_start: 900 // 15 minutes
                        }
                    })
                })
            );

            require('../../calendarbot_lite/whatsnext.js');
            jest.advanceTimersByTime(100);
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();

            expect(document.querySelector('.countdown-time').textContent).toBe('15');
            expect(document.querySelector('.countdown-hours').textContent).toBe('MINUTES');
        });

        test('should apply critical CSS class when time < 5 minutes', async () => {
            fetchMock.mockImplementation(() =>
                Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        meeting: {
                            subject: 'Test',
                            start_iso: new Date().toISOString(),
                            duration_seconds: 3600,
                            seconds_until_start: 240 // 4 minutes
                        }
                    })
                })
            );

            require('../../calendarbot_lite/whatsnext.js');
            jest.advanceTimersByTime(100);
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();

            const container = document.querySelector('.countdown-container');
            expect(container.classList.contains('countdown-critical')).toBe(true);
        });

        test('should apply warning CSS class when time < 15 minutes', async () => {
            fetchMock.mockImplementation(() =>
                Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        meeting: {
                            subject: 'Test',
                            start_iso: new Date().toISOString(),
                            duration_seconds: 3600,
                            seconds_until_start: 600 // 10 minutes
                        }
                    })
                })
            );

            require('../../calendarbot_lite/whatsnext.js');
            jest.advanceTimersByTime(100);
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();

            const container = document.querySelector('.countdown-container');
            expect(container.classList.contains('countdown-warning')).toBe(true);
        });

        test('should show no meetings message when no data', async () => {
            fetchMock.mockImplementation(() =>
                Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({})
                })
            );

            require('../../calendarbot_lite/whatsnext.js');
            jest.advanceTimersByTime(100);
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();

            expect(document.querySelector('.meeting-title').textContent).toBe('No upcoming meetings');
            expect(document.querySelector('.countdown-time').textContent).toBe('0');
            expect(document.querySelector('.countdown-hours').textContent).toBe('MEETINGS');
        });
    });

    describe('Bottom Section Context Messages', () => {
        test('should show "Starting very soon" for meetings < 2 minutes', async () => {
            fetchMock.mockImplementation(() =>
                Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        meeting: {
                            subject: 'Test',
                            start_iso: new Date().toISOString(),
                            duration_seconds: 3600,
                            seconds_until_start: 90
                        }
                    })
                })
            );

            require('../../calendarbot_lite/whatsnext.js');
            jest.advanceTimersByTime(100);
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();

            expect(document.querySelector('.next-meeting-title').textContent).toBe('Starting very soon');
        });

        test('should show "Meeting in progress" for started meetings', async () => {
            fetchMock.mockImplementation(() =>
                Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        meeting: {
                            subject: 'Test',
                            start_iso: new Date().toISOString(),
                            duration_seconds: 3600,
                            seconds_until_start: -300 // Started 5min ago
                        }
                    })
                })
            );

            require('../../calendarbot_lite/whatsnext.js');
            jest.advanceTimersByTime(100);
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();

            expect(document.querySelector('.next-meeting-title').textContent).toBe('Meeting in progress');
        });

        test('should show "Plenty of time" for meetings > 60 minutes', async () => {
            fetchMock.mockImplementation(() =>
                Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        meeting: {
                            subject: 'Test',
                            start_iso: new Date().toISOString(),
                            duration_seconds: 3600,
                            seconds_until_start: 7200
                        }
                    })
                })
            );

            require('../../calendarbot_lite/whatsnext.js');
            jest.advanceTimersByTime(100);
            jest.runOnlyPendingTimers();
            // Flush microtasks more aggressively to ensure async display updates complete
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();

            expect(document.querySelector('.next-meeting-title').textContent).toBe('Plenty of time');
        });
    });

    describe('Polling Behavior', () => {
        test('should stop polling when page is hidden', async () => {
            require('../../calendarbot_lite/whatsnext.js');

            fetchMock.mockClear();

            Object.defineProperty(document, 'hidden', {
                writable: true,
                configurable: true,
                value: true
            });
            document.dispatchEvent(new Event('visibilitychange'));

            jest.advanceTimersByTime(100);
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();
            const callsAfterHidden = fetchMock.mock.calls.filter(call => call[0] === '/api/whats-next').length;

            jest.advanceTimersByTime(60000);
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();

            expect(fetchMock.mock.calls.filter(call => call[0] === '/api/whats-next').length).toBe(callsAfterHidden);
        });

        test('should resume polling when page becomes visible', async () => {
            require('../../calendarbot_lite/whatsnext.js');

            // Hide page
            Object.defineProperty(document, 'hidden', {
                writable: true,
                configurable: true,
                value: true
            });
            document.dispatchEvent(new Event('visibilitychange'));

            fetchMock.mockClear();

            // Show page
            Object.defineProperty(document, 'hidden', {
                writable: true,
                configurable: true,
                value: false
            });
            document.dispatchEvent(new Event('visibilitychange'));

            jest.advanceTimersByTime(100);
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();

            expect(fetchMock.mock.calls.filter(call => call[0] === '/api/whats-next').length).toBeGreaterThan(0);
        });
    });

    describe('Cleanup', () => {
        test('should cleanup on beforeunload', () => {
            require('../../calendarbot_lite/whatsnext.js');

            const clearIntervalSpy = jest.spyOn(global, 'clearInterval');

            window.dispatchEvent(new Event('beforeunload'));

            expect(clearIntervalSpy).toHaveBeenCalled();

            clearIntervalSpy.mockRestore();
        });

        test('cleanup function should stop polling', () => {
            require('../../calendarbot_lite/whatsnext.js');

            fetchMock.mockClear();

            window.calendarBotCleanup();

            jest.advanceTimersByTime(120000);

            expect(fetchMock.mock.calls.filter(call => call[0] === '/api/whats-next').length).toBe(0);
        });
    });

    describe('Error Handling', () => {
        test('should handle fetch errors with retry', async () => {
            fetchMock.mockImplementation(() =>
                Promise.reject(new Error('Network error'))
            );

            const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

            require('../../calendarbot_lite/whatsnext.js');

            jest.advanceTimersByTime(100);
            jest.runOnlyPendingTimers();
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();
            await Promise.resolve();

            expect(consoleErrorSpy.mock.calls.flat().join(' ')).toContain('API fetch failed');

            consoleErrorSpy.mockRestore();
        });

        test('should handle HTTP errors', async () => {
            fetchMock.mockImplementation(() =>
                Promise.resolve({
                    ok: false,
                    status: 500,
                    statusText: 'Internal Server Error'
                })
            );

            const consoleLogSpy = jest.spyOn(console, 'log').mockImplementation(() => {});

            require('../../calendarbot_lite/whatsnext.js');

            jest.advanceTimersByTime(100);
            jest.runOnlyPendingTimers();
            await Promise.resolve();
            await Promise.resolve();

            // Accept either an explicit API fetch failure log or the retry.log emitted on HTTP error
            expect(consoleLogSpy.mock.calls.flat().join(' ')).toMatch(/API fetch failed|Retrying in|HTTP 500|Internal Server Error/);

            consoleLogSpy.mockRestore();
        });
    });
});
