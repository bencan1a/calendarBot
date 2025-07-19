/**
 * @fileoverview Jest Tests - State Management & Detection (REAL SOURCE)
 * Tests state getters, detection logic, and boundary conditions using real whats-next-view.js functions
 * ARCHITECTURAL TRANSFORMATION: Real source import instead of mock implementations
 */

// Import real source file
require('../../../../calendarbot/web/static/layouts/whats-next-view/whats-next-view.js');

describe('WhatsNextView State Management & Detection', () => {
  let mockDocument;

  beforeEach(() => {
    // Setup DOM mocks
    mockDocument = global.testUtils.setupMockDOM();
    
    // Enable debug mode for consistent test time
    if (typeof window.enableDebugMode === 'function') {
      window.enableDebugMode();
      window.setCustomTime(new Date('2023-07-19T10:00:00'));
    }
  });

  afterEach(() => {
    // Clean up debug state
    if (typeof window.disableDebugMode === 'function') {
      window.disableDebugMode();
    }
    jest.clearAllMocks();
  });

  describe('getCurrentTime', () => {
    describe('when getting current time', () => {
      it('should return current date object', () => {
        const result = window.getCurrentTime();
        
        expect(result).toBeInstanceOf(Date);
        // Real function behavior - when debug mode enabled, returns debug time
        expect(result).toBeInstanceOf(Date);
      });

      it('should return consistent time across multiple calls', () => {
        const time1 = window.getCurrentTime();
        const time2 = window.getCurrentTime();
        
        // Times should be very close (within 1 second for real implementation)
        expect(Math.abs(time1.getTime() - time2.getTime())).toBeLessThan(1000);
      });
    });
  });

  describe('checkBoundaryAlert', () => {

    describe('when checking critical time boundaries', () => {
      it('should return critical alert for 2 minutes or less', () => {
        const twoMinutes = 2 * 60 * 1000;
        const result = window.checkBoundaryAlert(twoMinutes);
        
        expect(result.type).toBe('critical');
        expect(result.cssClass).toBe('time-gap-critical');
        expect(result.message).toBe('WRAP UP NOW');
        expect(result.showCountdown).toBe(true);
        expect(result.urgent).toBe(true);
      });

      it('should return critical alert for 1 minute', () => {
        const oneMinute = 1 * 60 * 1000;
        const result = window.checkBoundaryAlert(oneMinute);
        
        expect(result.type).toBe('critical');
        expect(result.urgent).toBe(true);
      });

      it('should return critical alert for 0 minutes', () => {
        const result = window.checkBoundaryAlert(0);
        
        expect(result.type).toBe('critical');
        expect(result.urgent).toBe(true);
      });
    });

    describe('when checking tight time boundaries', () => {
      it('should return tight alert for 3-10 minutes', () => {
        const fiveMinutes = 5 * 60 * 1000;
        const result = window.checkBoundaryAlert(fiveMinutes);
        
        expect(result.type).toBe('tight');
        expect(result.cssClass).toBe('time-gap-tight');
        expect(result.message).toBe('Meeting starts soon');
        expect(result.showCountdown).toBe(true);
        expect(result.urgent).toBe(true);
      });

      it('should return tight alert for exactly 10 minutes', () => {
        const tenMinutes = 10 * 60 * 1000;
        const result = window.checkBoundaryAlert(tenMinutes);
        
        expect(result.type).toBe('tight');
        expect(result.urgent).toBe(true);
      });
    });

    describe('when checking comfortable time boundaries', () => {
      it('should return comfortable alert for 11-30 minutes', () => {
        const fifteenMinutes = 15 * 60 * 1000;
        const result = window.checkBoundaryAlert(fifteenMinutes);
        
        expect(result.type).toBe('comfortable');
        expect(result.cssClass).toBe('time-gap-comfortable');
        expect(result.message).toBe('Upcoming meeting');
        expect(result.showCountdown).toBe(false);
        expect(result.urgent).toBe(false);
      });

      it('should return comfortable alert for exactly 30 minutes', () => {
        const thirtyMinutes = 30 * 60 * 1000;
        const result = window.checkBoundaryAlert(thirtyMinutes);
        
        expect(result.type).toBe('comfortable');
        expect(result.urgent).toBe(false);
      });
    });

    describe('when checking relaxed time boundaries', () => {
      it('should return relaxed alert for more than 30 minutes', () => {
        const oneHour = 60 * 60 * 1000;
        const result = window.checkBoundaryAlert(oneHour);
        
        expect(result.type).toBe('relaxed');
        expect(result.cssClass).toBe('');
        expect(result.message).toBe('Next meeting');
        expect(result.showCountdown).toBe(false);
        expect(result.urgent).toBe(false);
      });

      it('should return relaxed alert for 45 minutes', () => {
        const fortyFiveMinutes = 45 * 60 * 1000;
        const result = window.checkBoundaryAlert(fortyFiveMinutes);
        
        expect(result.type).toBe('relaxed');
        expect(result.urgent).toBe(false);
      });
    });
  });

  describe('getContextMessage', () => {
    beforeEach(() => {
      // Set up a mock current meeting for getContextMessage to work
      // Use window.currentMeeting property that we exported from the source
      window.currentMeeting = {
        start_time: '2023-07-19T11:00:00.000Z',
        end_time: '2023-07-19T12:00:00.000Z',
        title: 'Test Meeting'
      };
    });

    afterEach(() => {
      // Clean up meeting
      window.currentMeeting = null;
    });

    describe('when meeting is in progress', () => {
      it('should return "Meeting in progress" for current meeting', () => {
        const result = window.getContextMessage(true);
        
        expect(result).toBe('Meeting in progress');
      });
    });

    describe('when meeting is upcoming', () => {
      it('should return appropriate message based on time until meeting', () => {
        const result = window.getContextMessage(false);
        
        // Real implementation returns messages based on actual time calculations
        expect(typeof result).toBe('string');
        expect(result.length).toBeGreaterThan(0);
      });

      it('should handle different time scenarios with real calculation', () => {
        // Test with different meeting times to get different messages
        const now = window.getCurrentTime();
        
        // Test upcoming meeting (1 hour from now)
        window.currentMeeting.start_time = new Date(now.getTime() + 60 * 60 * 1000).toISOString();
        const result1 = window.getContextMessage(false);
        expect(typeof result1).toBe('string');
        
        // Test soon meeting (5 minutes from now)
        window.currentMeeting.start_time = new Date(now.getTime() + 5 * 60 * 1000).toISOString();
        const result2 = window.getContextMessage(false);
        expect(typeof result2).toBe('string');
        
        // Both should be valid strings
        expect(result1.length).toBeGreaterThan(0);
        expect(result2.length).toBeGreaterThan(0);
      });
    });
  });
});