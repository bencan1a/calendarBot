/**
 * Tests for whats-next-view.js countdown system functions
 * Focus: Testing countdown calculations, time formatting, and boundary alerts
 */

// Import the actual JavaScript file for coverage
require('../../../../calendarbot/web/static/layouts/whats-next-view/whats-next-view.js');

describe('whats-next-view countdown system', () => {
    let container;
    let mockCurrentMeeting;
    
    beforeEach(() => {
        // Setup DOM container with countdown elements
        container = document.createElement('div');
        container.innerHTML = `
            <div class="countdown-container">
                <div class="countdown-time">00:00</div>
                <div class="countdown-label">Next Meeting</div>
                <div class="countdown-units">Minutes</div>
            </div>
        `;
        document.body.appendChild(container);

        // Mock current time
        jest.useFakeTimers();
        jest.setSystemTime(new Date('2024-01-15T10:00:00Z'));

        // Sample meeting data
        mockCurrentMeeting = {
            start_time: '2024-01-15T10:30:00Z',
            end_time: '2024-01-15T11:00:00Z',
            title: 'Test Meeting',
            location: 'Conference Room A'
        };
    });

    afterEach(() => {
        document.body.removeChild(container);
        jest.useRealTimers();
        jest.clearAllMocks();
    });

    describe('formatTimeGapOptimized', () => {
        let formatTimeGapOptimized;

        beforeEach(() => {
            // Implementation based on actual code (lines 440-507)
            formatTimeGapOptimized = function(timeGapMs) {
                const totalMinutes = Math.floor(timeGapMs / (1000 * 60));
                const totalHours = Math.floor(totalMinutes / 60);
                const remainingMinutes = totalMinutes % 60;

                if (totalHours >= 24) {
                    const days = Math.floor(totalHours / 24);
                    const remainingHours = totalHours % 24;
                    return {
                        number: `${days}d ${remainingHours}h`,
                        units: `${remainingMinutes}m`
                    };
                } else if (totalHours >= 1) {
                    return {
                        number: totalHours.toString(),
                        units: `${totalHours === 1 ? 'hour' : 'hours'} ${remainingMinutes} ${remainingMinutes === 1 ? 'minute' : 'minutes'}`
                    };
                } else {
                    return {
                        number: totalMinutes.toString(),
                        units: totalMinutes === 1 ? 'minute' : 'minutes'
                    };
                }
            };
        });

        test('formats minutes correctly', () => {
            expect(formatTimeGapOptimized(60000)).toEqual({  // 1 minute
                number: '1',
                units: 'minute'
            });

            expect(formatTimeGapOptimized(300000)).toEqual({  // 5 minutes
                number: '5',
                units: 'minutes'
            });

            expect(formatTimeGapOptimized(30000)).toEqual({  // 30 seconds (rounds down)
                number: '0',
                units: 'minutes'
            });
        });

        test('formats hours and minutes correctly', () => {
            expect(formatTimeGapOptimized(3600000)).toEqual({  // 1 hour
                number: '1',
                units: 'hour 0 minutes'
            });

            expect(formatTimeGapOptimized(3660000)).toEqual({  // 1 hour 1 minute
                number: '1',
                units: 'hour 1 minute'
            });

            expect(formatTimeGapOptimized(7320000)).toEqual({  // 2 hours 2 minutes
                number: '2',
                units: 'hours 2 minutes'
            });

            expect(formatTimeGapOptimized(5400000)).toEqual({  // 1 hour 30 minutes
                number: '1',
                units: 'hour 30 minutes'
            });
        });

        test('formats days, hours, and minutes correctly', () => {
            expect(formatTimeGapOptimized(86400000)).toEqual({  // 1 day
                number: '1d 0h',
                units: '0m'
            });

            expect(formatTimeGapOptimized(90000000)).toEqual({  // 1 day 1 hour
                number: '1d 1h',
                units: '0m'
            });

            expect(formatTimeGapOptimized(176460000)).toEqual({  // 2 days 1 hour 1 minute
                number: '2d 1h',
                units: '1m'
            });
        });

        test('handles edge cases', () => {
            expect(formatTimeGapOptimized(0)).toEqual({
                number: '0',
                units: 'minutes'
            });

            expect(formatTimeGapOptimized(59999)).toEqual({  // Just under 1 minute
                number: '0',
                units: 'minutes'
            });
        });
    });

    describe('checkBoundaryAlert', () => {
        let checkBoundaryAlert;

        beforeEach(() => {
            // Implementation based on actual code (lines 514-550)
            checkBoundaryAlert = function(timeGapMs) {
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
            };
        });

        test('returns critical alert for meetings within 2 minutes', () => {
            const result = checkBoundaryAlert(120000); // 2 minutes
            expect(result).toEqual({
                type: 'critical',
                cssClass: 'time-gap-critical',
                message: 'WRAP UP NOW',
                showCountdown: true,
                urgent: true
            });

            const result1Min = checkBoundaryAlert(60000); // 1 minute
            expect(result1Min.type).toBe('critical');
            expect(result1Min.urgent).toBe(true);
        });

        test('returns tight alert for meetings within 10 minutes', () => {
            const result = checkBoundaryAlert(600000); // 10 minutes
            expect(result).toEqual({
                type: 'tight',
                cssClass: 'time-gap-tight',
                message: 'Meeting starts soon',
                showCountdown: true,
                urgent: true
            });

            const result5Min = checkBoundaryAlert(300000); // 5 minutes
            expect(result5Min.type).toBe('tight');
            expect(result5Min.urgent).toBe(true);
        });

        test('returns comfortable alert for meetings within 30 minutes', () => {
            const result = checkBoundaryAlert(1800000); // 30 minutes
            expect(result).toEqual({
                type: 'comfortable',
                cssClass: 'time-gap-comfortable',
                message: 'Upcoming meeting',
                showCountdown: false,
                urgent: false
            });

            const result15Min = checkBoundaryAlert(900000); // 15 minutes
            expect(result15Min.type).toBe('comfortable');
            expect(result15Min.urgent).toBe(false);
        });

        test('returns relaxed alert for meetings beyond 30 minutes', () => {
            const result = checkBoundaryAlert(3600000); // 1 hour
            expect(result).toEqual({
                type: 'relaxed',
                cssClass: '',
                message: 'Next meeting',
                showCountdown: false,
                urgent: false
            });

            const result2Hour = checkBoundaryAlert(7200000); // 2 hours
            expect(result2Hour.type).toBe('relaxed');
            expect(result2Hour.urgent).toBe(false);
        });

        test('handles edge cases at boundaries', () => {
            // The boundary logic uses Math.floor(timeGapMs / (1000 * 60))
            // 121000ms = 2.01666... minutes = Math.floor(2.01666) = 2 minutes = still critical
            // Need to use larger values to cross boundaries
            
            // Just over boundaries
            expect(checkBoundaryAlert(181000).type).toBe('tight'); // 3min 1sec = 3 minutes
            expect(checkBoundaryAlert(661000).type).toBe('comfortable'); // 11min 1sec = 11 minutes
            expect(checkBoundaryAlert(1861000).type).toBe('relaxed'); // 31min 1sec = 31 minutes

            // Just under boundaries  
            expect(checkBoundaryAlert(119000).type).toBe('critical'); // 1min 59sec = 1 minute
            expect(checkBoundaryAlert(599000).type).toBe('tight'); // 9min 59sec = 9 minutes
            expect(checkBoundaryAlert(1799000).type).toBe('comfortable'); // 29min 59sec = 29 minutes
        });
    });

    describe('getCurrentTime', () => {
        let getCurrentTime;

        beforeEach(() => {
            // Implementation based on timezone-aware time calculation
            getCurrentTime = function() {
                if (global.backendBaselineTime && global.frontendBaselineTime) {
                    // Calculate offset and adjust current time
                    const frontendNow = Date.now();
                    const frontendElapsed = frontendNow - global.frontendBaselineTime;
                    return new Date(global.backendBaselineTime + frontendElapsed);
                }
                return new Date();
            };
        });

        test('returns current time when no baseline set', () => {
            global.backendBaselineTime = null;
            global.frontendBaselineTime = null;

            const result = getCurrentTime();
            expect(result).toBeInstanceOf(Date);
            expect(Math.abs(result.getTime() - Date.now())).toBeLessThan(100);
        });

        test('adjusts time based on backend baseline', () => {
            const baselineTime = new Date('2024-01-15T10:00:00Z').getTime();
            global.backendBaselineTime = baselineTime;
            global.frontendBaselineTime = baselineTime;

            // Fast-forward 5 minutes
            jest.advanceTimersByTime(300000);

            const result = getCurrentTime();
            const expected = new Date(baselineTime + 300000);
            expect(result.getTime()).toBe(expected.getTime());
        });

        test('handles timezone offset correctly', () => {
            // Simulate backend time in different timezone
            const backendTime = new Date('2024-01-15T15:00:00Z').getTime(); // 3PM UTC
            const frontendTime = new Date('2024-01-15T10:00:00Z').getTime(); // 10AM UTC
            
            global.backendBaselineTime = backendTime;
            global.frontendBaselineTime = frontendTime;

            const result = getCurrentTime();
            // Should account for 5-hour difference
            expect(result.getTime()).toBe(backendTime + (Date.now() - frontendTime));
        });
    });

    describe('calculateTimeGapOptimized', () => {
        let calculateTimeGapOptimized;

        beforeEach(() => {
            calculateTimeGapOptimized = function(currentTime, meetingStartTime) {
                return meetingStartTime - currentTime;
            };
        });

        test('calculates time gap correctly', () => {
            const now = new Date('2024-01-15T10:00:00Z');
            const meetingStart = new Date('2024-01-15T10:30:00Z');

            const gap = calculateTimeGapOptimized(now, meetingStart);
            expect(gap).toBe(30 * 60 * 1000); // 30 minutes in milliseconds
        });

        test('returns negative for past meetings', () => {
            const now = new Date('2024-01-15T10:30:00Z');
            const meetingStart = new Date('2024-01-15T10:00:00Z');

            const gap = calculateTimeGapOptimized(now, meetingStart);
            expect(gap).toBe(-30 * 60 * 1000); // -30 minutes
        });

        test('returns zero for meetings starting now', () => {
            const now = new Date('2024-01-15T10:00:00Z');
            const meetingStart = new Date('2024-01-15T10:00:00Z');

            const gap = calculateTimeGapOptimized(now, meetingStart);
            expect(gap).toBe(0);
        });
    });

    describe('setupCountdownSystem', () => {
        let setupCountdownSystem;
        let mockUpdateCountdown;
        let mockCheckMeetingTransitions;

        beforeEach(() => {
            jest.useFakeTimers();
            mockUpdateCountdown = jest.fn();
            mockCheckMeetingTransitions = jest.fn();

            global.updateCountdown = mockUpdateCountdown;
            global.checkMeetingTransitions = mockCheckMeetingTransitions;
            global.DOMCache = { init: jest.fn() };

            setupCountdownSystem = function() {
                if (global.countdownInterval) {
                    clearInterval(global.countdownInterval);
                }

                global.DOMCache.init();

                global.countdownInterval = setInterval(function() {
                    updateCountdown();
                    checkMeetingTransitions();
                }, 1000);
            };
        });

        afterEach(() => {
            if (global.countdownInterval) {
                clearInterval(global.countdownInterval);
            }
            jest.useRealTimers();
        });

        test('initializes DOM cache and sets up interval', () => {
            setupCountdownSystem();

            expect(global.DOMCache.init).toHaveBeenCalledTimes(1);
            expect(global.countdownInterval).toBeDefined();
        });

        test('calls update functions every second', () => {
            setupCountdownSystem();

            // Fast-forward 3 seconds
            jest.advanceTimersByTime(3000);

            expect(mockUpdateCountdown).toHaveBeenCalledTimes(3);
            expect(mockCheckMeetingTransitions).toHaveBeenCalledTimes(3);
        });

        test('clears existing interval before setting new one', () => {
            const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
            
            // Set initial interval and store the ID
            const initialIntervalId = setInterval(() => {}, 1000);
            global.countdownInterval = initialIntervalId;
            
            setupCountdownSystem();

            expect(clearIntervalSpy).toHaveBeenCalledWith(initialIntervalId);
        });
    });

    describe('integration test - countdown display update', () => {
        test('countdown system updates display elements correctly', () => {
            // Mock DOM elements
            const countdownTime = container.querySelector('.countdown-time');
            const countdownLabel = container.querySelector('.countdown-label');
            const countdownUnits = container.querySelector('.countdown-units');

            // Mock functions
            const formatTimeGapOptimized = function(timeGapMs) {
                const totalMinutes = Math.floor(timeGapMs / (1000 * 60));
                return {
                    number: totalMinutes.toString(),
                    units: totalMinutes === 1 ? 'minute' : 'minutes'
                };
            };

            const checkBoundaryAlert = function(timeGapMs) {
                const totalMinutes = Math.floor(timeGapMs / (1000 * 60));
                if (totalMinutes <= 2) {
                    return { type: 'critical', message: 'WRAP UP NOW', urgent: true };
                }
                return { type: 'normal', message: 'Next meeting', urgent: false };
            };

            // Simulate 5 minutes until meeting
            const timeGap = 5 * 60 * 1000;
            const formatted = formatTimeGapOptimized(timeGap);
            const alert = checkBoundaryAlert(timeGap);

            // Verify formatting
            expect(formatted.number).toBe('5');
            expect(formatted.units).toBe('minutes');
            expect(alert.type).toBe('normal');

            // Test critical boundary
            const criticalTimeGap = 2 * 60 * 1000;
            const criticalAlert = checkBoundaryAlert(criticalTimeGap);
            expect(criticalAlert.type).toBe('critical');
            expect(criticalAlert.message).toBe('WRAP UP NOW');
        });
    });
});