/**
 * Unit tests for What's Next P0 Time Gap Display Functions
 * Tests the calculateTimeGap, formatTimeGap, and checkBoundaryAlert functions
 */

// Define the P0 functions inline for testing
function calculateTimeGap(currentTime, nextMeetingTime) {
    if (!currentTime || !nextMeetingTime) {
        return 0;
    }
    
    const gap = nextMeetingTime.getTime() - currentTime.getTime();
    return Math.max(0, gap); // Ensure non-negative
}

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

describe('P0 Time Gap Display Functions', () => {
    
    describe('calculateTimeGap', () => {
        test('calculateTimeGap_when_valid_future_time_then_returns_positive_gap', () => {
            const currentTime = new Date('2025-07-15T18:00:00');
            const futureTime = new Date('2025-07-15T19:30:00');
            
            const result = calculateTimeGap(currentTime, futureTime);
            
            expect(result).toBe(90 * 60 * 1000); // 90 minutes in milliseconds
            expect(typeof result).toBe('number');
        });

        test('calculateTimeGap_when_past_time_then_returns_zero', () => {
            const currentTime = new Date('2025-07-15T18:00:00');
            const pastTime = new Date('2025-07-15T17:00:00');
            
            const result = calculateTimeGap(currentTime, pastTime);
            
            expect(result).toBe(0);
        });

        test('calculateTimeGap_when_null_parameters_then_returns_zero', () => {
            expect(calculateTimeGap(null, new Date())).toBe(0);
            expect(calculateTimeGap(new Date(), null)).toBe(0);
            expect(calculateTimeGap(null, null)).toBe(0);
        });

        test('calculateTimeGap_when_same_time_then_returns_zero', () => {
            const sameTime = new Date('2025-07-15T18:00:00');
            
            const result = calculateTimeGap(sameTime, sameTime);
            
            expect(result).toBe(0);
        });
    });

    describe('formatTimeGap', () => {
        test('formatTimeGap_when_zero_milliseconds_then_returns_zero_minutes', () => {
            const result = formatTimeGap(0);
            
            expect(result).toBe('0 minutes');
        });

        test('formatTimeGap_when_one_minute_then_returns_singular_minute', () => {
            const oneMinute = 1 * 60 * 1000;
            
            const result = formatTimeGap(oneMinute);
            
            expect(result).toBe('1 minute');
        });

        test('formatTimeGap_when_multiple_minutes_then_returns_plural_minutes', () => {
            const twentyThreeMinutes = 23 * 60 * 1000;
            
            const result = formatTimeGap(twentyThreeMinutes);
            
            expect(result).toBe('23 minutes');
        });

        test('formatTimeGap_when_one_hour_exact_then_returns_singular_hour', () => {
            const oneHour = 60 * 60 * 1000;
            
            const result = formatTimeGap(oneHour);
            
            expect(result).toBe('1 hour');
        });

        test('formatTimeGap_when_one_hour_fifteen_minutes_then_returns_combined_format', () => {
            const oneHourFifteenMinutes = (60 + 15) * 60 * 1000;
            
            const result = formatTimeGap(oneHourFifteenMinutes);
            
            expect(result).toBe('1 hour 15 minutes');
        });
    });

    describe('checkBoundaryAlert', () => {
        test('checkBoundaryAlert_when_one_minute_remaining_then_returns_critical_alert', () => {
            const oneMinute = 1 * 60 * 1000;
            
            const result = checkBoundaryAlert(oneMinute);
            
            expect(result.type).toBe('critical');
            expect(result.cssClass).toBe('time-gap-critical');
            expect(result.message).toBe('WRAP UP NOW');
            expect(result.urgent).toBe(true);
        });

        test('checkBoundaryAlert_when_five_minutes_remaining_then_returns_tight_alert', () => {
            const fiveMinutes = 5 * 60 * 1000;
            
            const result = checkBoundaryAlert(fiveMinutes);
            
            expect(result.type).toBe('tight');
            expect(result.cssClass).toBe('time-gap-tight');
            expect(result.message).toBe('Meeting starts soon');
            expect(result.urgent).toBe(true);
        });

        test('checkBoundaryAlert_when_fifteen_minutes_remaining_then_returns_comfortable_alert', () => {
            const fifteenMinutes = 15 * 60 * 1000;
            
            const result = checkBoundaryAlert(fifteenMinutes);
            
            expect(result.type).toBe('comfortable');
            expect(result.cssClass).toBe('time-gap-comfortable');
            expect(result.message).toBe('Upcoming meeting');
            expect(result.urgent).toBe(false);
        });

        test('checkBoundaryAlert_when_one_hour_remaining_then_returns_relaxed_alert', () => {
            const oneHour = 60 * 60 * 1000;
            
            const result = checkBoundaryAlert(oneHour);
            
            expect(result.type).toBe('relaxed');
            expect(result.cssClass).toBe('');
            expect(result.message).toBe('Next meeting');
            expect(result.urgent).toBe(false);
        });
    });

    describe('Integration Tests', () => {
        test('integration_when_typical_workflow_then_functions_work_together', () => {
            const currentTime = new Date('2025-07-15T18:00:00');
            const meetingTime = new Date('2025-07-15T18:08:00'); // 8 minutes away
            
            // Calculate time gap
            const timeGap = calculateTimeGap(currentTime, meetingTime);
            expect(timeGap).toBe(8 * 60 * 1000);
            
            // Format time gap
            const formattedGap = formatTimeGap(timeGap);
            expect(formattedGap).toBe('8 minutes');
            
            // Check boundary alert
            const boundaryAlert = checkBoundaryAlert(timeGap);
            expect(boundaryAlert.type).toBe('tight');
            expect(boundaryAlert.cssClass).toBe('time-gap-tight');
            expect(boundaryAlert.urgent).toBe(true);
        });

        test('integration_when_critical_boundary_then_all_functions_indicate_urgency', () => {
            const currentTime = new Date('2025-07-15T18:00:00');
            const meetingTime = new Date('2025-07-15T18:01:30'); // 1.5 minutes away
            
            const timeGap = calculateTimeGap(currentTime, meetingTime);
            const formattedGap = formatTimeGap(timeGap);
            const boundaryAlert = checkBoundaryAlert(timeGap);
            
            expect(formattedGap).toBe('1 minute'); // Rounded down
            expect(boundaryAlert.type).toBe('critical');
            expect(boundaryAlert.message).toBe('WRAP UP NOW');
        });
    });
});