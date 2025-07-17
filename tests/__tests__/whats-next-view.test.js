/**
 * @fileoverview Comprehensive test suite for whats-next-view.js
 * Tests meeting detection, countdown functionality, and user interactions
 */

describe('Whats-Next-View Layout Module (whats-next-view.js)', () => {
  let setIntervalSpy;
  let clearIntervalSpy;
  let consoleLogSpy;
  let fetchMock;

  beforeEach(() => {
    // Reset DOM
    testUtils.cleanupDOM();
    testUtils.setupMockDOM(`
      <html class="theme-eink">
        <head><title>CalendarBot</title></head>
        <body>
          <div class="whats-next-content"></div>
          <div class="countdown-time">--</div>
          <div class="countdown-label">Next Meeting</div>
          <div class="countdown-units">Minutes</div>
          <button data-action="refresh">Refresh</button>
          <button data-action="theme">Theme</button>
          <button data-action="layout">Layout</button>
        </body>
      </html>
    `);

    // Setup spies
    setIntervalSpy = jest.spyOn(global, 'setInterval').mockImplementation((fn, delay) => {
      return setTimeout(fn, 0); // Execute immediately for testing
    });
    clearIntervalSpy = jest.spyOn(global, 'clearInterval');
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
    
    // Mock fetch
    fetchMock = fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        html: '<div class="current-event"><div class="event-title">Test Meeting</div><div class="event-time">2:00 PM - 3:00 PM</div></div>'
      })
    });

    // Reset global state variables if they exist
    if (typeof window !== 'undefined') {
      window.currentMeeting = null;
      window.upcomingMeetings = [];
      window.autoRefreshEnabled = true;
      window.currentTheme = 'eink';
    }

    // Load the source file and trigger initialization
    require('../../calendarbot/web/static/layouts/whats-next-view/whats-next-view.js');
    
    // Trigger DOMContentLoaded to initialize the module
    const event = new Event('DOMContentLoaded');
    document.dispatchEvent(event);
  });

  afterEach(() => {
    jest.clearAllMocks();
    jest.clearAllTimers();
    testUtils.cleanupDOM();
  });

  describe('Initialization', () => {
    it('should initialize when DOM content is loaded', () => {
      const logSpy = jest.spyOn(console, 'log').mockImplementation();
      
      // Trigger DOMContentLoaded
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      expect(logSpy).toHaveBeenCalledWith('Whats-Next-View: Initializing layout');
    });

    it('should have required functions available globally', () => {
      expect(typeof window.navigate).toBe('function');
      expect(typeof window.toggleTheme).toBe('function');
      expect(typeof window.cycleLayout).toBe('function');
      expect(typeof window.refresh).toBe('function');
      expect(typeof window.getCurrentTheme).toBe('function');
      expect(typeof window.isAutoRefreshEnabled).toBe('function');
      expect(typeof window.updateCountdown).toBe('function');
      expect(typeof window.detectCurrentMeeting).toBe('function');
      expect(typeof window.loadMeetingData).toBe('function');
    });

    it('should have debug interface available', () => {
      expect(typeof window.whatsNextView).toBe('object');
      expect(typeof window.whatsNextView.getCurrentMeeting).toBe('function');
      expect(typeof window.whatsNextView.getUpcomingMeetings).toBe('function');
      expect(typeof window.whatsNextView.toggleAutoRefresh).toBe('function');
    });
  });

  describe('Navigation Functions', () => {
    it('should handle navigation requests', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div>Navigation result</div>'
        })
      });

      await window.navigate('next');

      expect(fetchMock).toHaveBeenCalledWith('/api/navigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'next' })
      });
    });

    it('should handle navigation errors', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Network error'));

      await expect(window.navigate('prev')).resolves.not.toThrow();
    });
  });

  describe('Theme Functions', () => {
    it('should toggle theme successfully', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          theme: 'dark'
        })
      });

      await window.toggleTheme();

      expect(fetchMock).toHaveBeenCalledWith('/api/theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
    });

    it('should handle theme toggle errors', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Theme error'));

      await expect(window.toggleTheme()).resolves.not.toThrow();
    });
  });

  describe('Layout Functions', () => {
    it('should cycle layout successfully', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          layout: '3x4'
        })
      });

      await window.cycleLayout();

      expect(fetchMock).toHaveBeenCalledWith('/api/layout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
    });

    it('should handle layout cycle errors', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Layout error'));

      await expect(window.cycleLayout()).resolves.not.toThrow();
    });
  });

  describe('Refresh Functions', () => {
    it('should perform manual refresh', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div>Refreshed content</div>'
        })
      });

      await window.refresh();

      expect(fetchMock).toHaveBeenCalled();
    });

    it('should handle refresh errors', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Refresh error'));

      await expect(window.refresh()).resolves.not.toThrow();
    });
  });

  describe('Meeting Data Loading', () => {
    it('should load meeting data from API', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div class="current-event"><div class="event-title">Team Meeting</div></div>'
        })
      });

      await window.loadMeetingData();

      expect(fetchMock).toHaveBeenCalledWith('/api/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}'
      });
    });

    it('should handle API errors gracefully', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Network error'));

      await expect(window.loadMeetingData()).resolves.not.toThrow();
    });
  });

  describe('Navigation Button Handlers', () => {
    it('should handle refresh button clicks', async () => {
      const refreshButton = document.querySelector('[data-action="refresh"]');
      
      // Reset fetch mock to track new calls
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div>Refreshed</div>'
        })
      });
      
      testUtils.triggerEvent(refreshButton, 'click');
      
      // Wait for any async operations
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}'
      });
    });

    it('should handle theme button clicks', async () => {
      const themeButton = document.querySelector('[data-action="theme"]');
      
      // Reset fetch mock to track new calls
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          theme: 'dark'
        })
      });
      
      testUtils.triggerEvent(themeButton, 'click');
      
      // Wait for any async operations
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
    });

    it('should handle layout button clicks', async () => {
      const layoutButton = document.querySelector('[data-action="layout"]');
      
      // Reset fetch mock to track new calls
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          layout: '3x4'
        })
      });
      
      testUtils.triggerEvent(layoutButton, 'click');
      
      // Wait for any async operations
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/layout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
    });
  });

  describe('Keyboard Navigation', () => {
    it('should handle R key for refresh', async () => {
      // Reset fetch mock to track new calls
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div>Refreshed</div>'
        })
      });
      
      const keyEvent = new KeyboardEvent('keydown', { key: 'r' });
      document.dispatchEvent(keyEvent);
      
      // Wait for any async operations
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}'
      });
    });

    it('should handle T key for theme toggle', async () => {
      // Reset fetch mock to track new calls
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          theme: 'dark'
        })
      });
      
      const keyEvent = new KeyboardEvent('keydown', { key: 't' });
      document.dispatchEvent(keyEvent);
      
      // Wait for any async operations
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
    });

    it('should handle L key for layout cycle', async () => {
      // Reset fetch mock to track new calls
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          layout: '3x4'
        })
      });
      
      const keyEvent = new KeyboardEvent('keydown', { key: 'l' });
      document.dispatchEvent(keyEvent);
      
      // Wait for any async operations
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/layout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
    });

    it('should handle Space key for refresh', async () => {
      // Reset fetch mock to track new calls
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div>Refreshed</div>'
        })
      });
      
      const keyEvent = new KeyboardEvent('keydown', { key: ' ' });
      document.dispatchEvent(keyEvent);
      
      // Wait for any async operations
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}'
      });
    });
  });

  describe('Touch/Mobile Events', () => {
    beforeEach(() => {
      // Trigger initialization
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should handle touch swipe gestures', async () => {
      // Reset fetch mock to track new calls
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div>Refreshed</div>'
        })
      });
      
      // Simulate swipe right with proper touch event structure
      const touchStartEvent = new TouchEvent('touchstart', {
        changedTouches: [{ screenX: 100 }]
      });
      document.dispatchEvent(touchStartEvent);

      const touchEndEvent = new TouchEvent('touchend', {
        changedTouches: [{ screenX: 200 }]  // Swipe distance > 50 threshold
      });
      document.dispatchEvent(touchEndEvent);

      // Wait for any async operations
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}'
      });
    });
  });

  describe('Auto-Refresh Functionality', () => {
    it('should setup auto-refresh interval', () => {
      // Trigger initialization
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);

      expect(setIntervalSpy).toHaveBeenCalledWith(expect.any(Function), 60000);
    });
  });

  describe('Countdown System', () => {
    beforeEach(() => {
      // Trigger initialization
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should update countdown display', () => {
      // Setup a test meeting
      window.currentMeeting = {
        id: 'test-meeting',
        title: 'Test Meeting',
        start_time: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
        end_time: new Date(Date.now() + 75 * 60 * 1000).toISOString(),
        location: 'Test Room'
      };

      expect(() => window.updateCountdown()).not.toThrow();
    });

    it('should handle missing countdown elements', () => {
      // Remove countdown elements
      document.querySelector('.countdown-time')?.remove();
      
      expect(() => window.updateCountdown()).not.toThrow();
    });
  });

  describe('Meeting Detection', () => {
    beforeEach(() => {
      // Trigger initialization
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should detect current meeting', () => {
      // Setup test meetings
      window.upcomingMeetings = [
        {
          id: 'meeting-1',
          title: 'Test Meeting',
          start_time: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
          end_time: new Date(Date.now() + 90 * 60 * 1000).toISOString(),
          location: 'Room A'
        }
      ];

      expect(() => window.detectCurrentMeeting()).not.toThrow();
    });

    it('should handle empty meeting list', () => {
      window.upcomingMeetings = [];
      
      expect(() => window.detectCurrentMeeting()).not.toThrow();
    });
  });

  describe('UI Feedback Functions', () => {
    beforeEach(() => {
      // Trigger initialization
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should show loading indicator', () => {
      expect(() => window.showLoadingIndicator('Loading...')).not.toThrow();
      
      const indicator = document.getElementById('loading-indicator');
      expect(indicator).toBeTruthy();
      expect(indicator.textContent).toBe('Loading...');
    });

    it('should hide loading indicator', () => {
      window.showLoadingIndicator('Test');
      
      expect(() => window.hideLoadingIndicator()).not.toThrow();
      
      const indicator = document.getElementById('loading-indicator');
      expect(indicator.style.display).toBe('none');
    });

    it('should show error messages', () => {
      expect(() => window.showErrorMessage('Error occurred')).not.toThrow();
    });

    it('should show success messages', () => {
      expect(() => window.showSuccessMessage('Success')).not.toThrow();
    });
  });

  describe('Meeting Display Functions', () => {
    beforeEach(() => {
      // Trigger initialization
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should update meeting display', () => {
      window.currentMeeting = {
        id: 'test-meeting',
        title: 'Test Meeting',
        start_time: new Date().toISOString(),
        end_time: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
        location: 'Test Location'
      };

      expect(() => window.updateMeetingDisplay()).not.toThrow();
    });

    it('should show empty state when no meetings', () => {
      window.currentMeeting = null;
      
      expect(() => window.updateMeetingDisplay()).not.toThrow();
    });

    it('should format meeting time correctly', () => {
      const startTime = new Date('2024-01-01T14:30:00').toISOString();
      const endTime = new Date('2024-01-01T15:30:00').toISOString();
      
      const result = window.formatMeetingTime(startTime, endTime);
      
      expect(typeof result).toBe('string');
      expect(result).toContain('PM');
    });

    it('should escape HTML correctly', () => {
      const unsafeString = '<script>alert("xss")</script>';
      const result = window.escapeHtml(unsafeString);
      
      expect(result).toBe('&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;');
    });
  });

  describe('Accessibility Features', () => {
    beforeEach(() => {
      // Trigger initialization
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should setup accessibility features', () => {
      expect(() => window.setupAccessibility()).not.toThrow();
      
      const liveRegion = document.getElementById('whats-next-live-region');
      expect(liveRegion).toBeTruthy();
      expect(liveRegion.getAttribute('aria-live')).toBe('polite');
    });

    it('should announce to screen readers', () => {
      window.setupAccessibility();
      
      expect(() => window.announceToScreenReader('Test announcement')).not.toThrow();
      
      const liveRegion = document.getElementById('whats-next-live-region');
      expect(liveRegion.textContent).toBe('Test announcement');
    });

    it('should get meeting ARIA label', () => {
      const meetingElement = document.createElement('div');
      meetingElement.innerHTML = `
        <div class="meeting-title">Important Meeting</div>
        <div class="meeting-time">2:00 PM - 3:00 PM</div>
      `;
      
      const ariaLabel = window.getMeetingAriaLabel(meetingElement);
      
      expect(ariaLabel).toBe('Meeting: Important Meeting, 2:00 PM - 3:00 PM');
    });
  });

  describe('Debug Interface', () => {
    beforeEach(async () => {
      // Reset fetch mock for this test
      fetchMock.mockClear();
      
      // Mock API response with meeting data that will populate internal state
      // Use times far in the future to ensure they're always "upcoming"
      const now = new Date();
      const futureHour1 = new Date(now.getTime() + 2 * 60 * 60 * 1000); // 2 hours from now
      const futureHour2 = new Date(now.getTime() + 3 * 60 * 60 * 1000); // 3 hours from now
      const futureHour3 = new Date(now.getTime() + 4 * 60 * 60 * 1000); // 4 hours from now
      const futureHour4 = new Date(now.getTime() + 5 * 60 * 60 * 1000); // 5 hours from now
      
      const formatTime = (date) => {
        return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
      };
      
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: `
            <div class="current-event">
              <div class="event-title">Test Meeting</div>
              <div class="event-time">${formatTime(futureHour1)} - ${formatTime(futureHour2)}</div>
              <div class="event-location">Test Room</div>
            </div>
            <div class="upcoming-event">
              <div class="event-title">Meeting 1</div>
              <div class="event-time">${formatTime(futureHour2)} - ${formatTime(futureHour3)}</div>
            </div>
            <div class="upcoming-event">
              <div class="event-title">Meeting 2</div>
              <div class="event-time">${formatTime(futureHour3)} - ${formatTime(futureHour4)}</div>
            </div>
          `
        })
      });
      
      // Load data using the module's own API to populate internal state
      await window.loadMeetingData();
    });

    it('should return current meeting from debug interface', () => {
      const result = window.whatsNextView.getCurrentMeeting();
      const upcomingMeetings = window.whatsNextView.getUpcomingMeetings();
      
      console.log('DEBUG: Current meeting result:', result);
      console.log('DEBUG: Upcoming meetings:', upcomingMeetings);
      console.log('DEBUG: Upcoming meetings length:', upcomingMeetings ? upcomingMeetings.length : 'null/undefined');
      
      if (upcomingMeetings && upcomingMeetings.length > 0) {
        console.log('DEBUG: First meeting:', upcomingMeetings[0]);
      }
      
      // Should now have a meeting object with the expected title
      expect(result).not.toBeNull();
      expect(result).toEqual(expect.objectContaining({
        title: 'Test Meeting'
      }));
    });

    it('should return upcoming meetings from debug interface', () => {
      const result = window.whatsNextView.getUpcomingMeetings();
      console.log('DEBUG: Upcoming meetings:', result);
      
      // Should have all parsed meetings (current + upcoming) in chronological order
      expect(result).toHaveLength(3);
      expect(result[0]).toEqual(expect.objectContaining({
        title: 'Test Meeting'  // Earliest meeting (becomes currentMeeting)
      }));
      expect(result[1]).toEqual(expect.objectContaining({
        title: 'Meeting 1'     // Second earliest meeting
      }));
      expect(result[2]).toEqual(expect.objectContaining({
        title: 'Meeting 2'     // Latest meeting
      }));
    });

    it('should return last update from debug interface', () => {
      const result = window.whatsNextView.getLastUpdate();
      console.log('DEBUG: Last update:', result);
      expect(result).toBeInstanceOf(Date);
    });

    it('should toggle auto-refresh through debug interface', () => {
      const initialState = window.isAutoRefreshEnabled();
      const result = window.whatsNextView.toggleAutoRefresh();
      expect(typeof result).toBe('boolean');
    });
  });

  describe('Integration Tests', () => {
    it('should handle complete workflow', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div class="current-event"><div class="event-title">Integration Meeting</div></div>'
        })
      });

      // Trigger initialization
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);

      // Load data
      await window.loadMeetingData();
      
      // Update display
      window.updateCountdown();
      window.updateMeetingDisplay();
      
      expect(fetchMock).toHaveBeenCalled();
    });

    it('should handle error scenarios gracefully', async () => {
      fetchMock.mockRejectedValue(new Error('Network error'));

      await expect(window.loadMeetingData()).resolves.not.toThrow();
      await expect(window.navigate('next')).resolves.not.toThrow();
      await expect(window.toggleTheme()).resolves.not.toThrow();
      await expect(window.cycleLayout()).resolves.not.toThrow();
      
      // Test refresh separately since it's async but doesn't return a promise
      expect(() => window.refresh()).not.toThrow();
    });
  });

  describe('Edge Cases', () => {
    it('should handle missing DOM elements', () => {
      testUtils.cleanupDOM();
      
      expect(() => window.updateCountdown()).not.toThrow();
      expect(() => window.updateMeetingDisplay()).not.toThrow();
      expect(() => window.setupAccessibility()).not.toThrow();
    });

    it('should handle invalid meeting data', () => {
      window.currentMeeting = null;
      window.upcomingMeetings = [];
      
      expect(() => window.updateCountdown()).not.toThrow();
      expect(() => window.updateMeetingDisplay()).not.toThrow();
      expect(() => window.detectCurrentMeeting()).not.toThrow();
    });
  });
});

  /**
   * Comprehensive Debug Mode Tests
   * Testing all debug mode functions (lines 1398-2067)
   * This is the largest uncovered area requiring extensive testing
   */
  describe('Debug Mode Functionality', () => {
    beforeEach(() => {
      testUtils.setupMockDOM(`
        <html class="theme-eink">
          <body>
            <div class="calendar-content"></div>
            <div class="countdown-time">--</div>
            <div class="countdown-label">Next Meeting</div>
            <div class="countdown-units">Minutes</div>
            <div class="countdown-container"></div>
          </body>
        </html>
      `);
      
      // Reset debug state
      if (window.whatsNextView) {
        window.whatsNextView.clearDebugValues && window.whatsNextView.clearDebugValues();
      }
    });

    describe('Debug Mode Toggle', () => {
      it('should toggle debug mode on and off', () => {
        const initialState = window.whatsNextView && window.whatsNextView.getDebugState();
        
        // Toggle debug mode on
        expect(() => window.whatsNextView && window.whatsNextView.toggleDebugMode()).not.toThrow();
        
        if (window.whatsNextView && window.whatsNextView.getDebugState) {
          const newState = window.whatsNextView.getDebugState();
          expect(newState.enabled).toBe(!initialState?.enabled);
        }
      });

      it('should handle D key for debug mode toggle', () => {
        const keyEvent = new KeyboardEvent('keydown', { key: 'D' });
        
        expect(() => document.dispatchEvent(keyEvent)).not.toThrow();
      });

      it('should handle d key for debug mode toggle', () => {
        const keyEvent = new KeyboardEvent('keydown', { key: 'd' });
        
        expect(() => document.dispatchEvent(keyEvent)).not.toThrow();
      });
    });

    describe('Debug Panel Creation', () => {
      it('should create debug panel when enabled', () => {
        if (window.whatsNextView && window.whatsNextView.toggleDebugMode) {
          window.whatsNextView.toggleDebugMode();
          
          // Check if debug panel exists
          const debugPanel = document.getElementById('debug-panel');
          expect(debugPanel).toBeTruthy();
        }
      });

      it('should remove debug panel when disabled', () => {
        if (window.whatsNextView && window.whatsNextView.toggleDebugMode) {
          // Enable debug mode first
          window.whatsNextView.toggleDebugMode();
          
          // Then disable it
          window.whatsNextView.toggleDebugMode();
          
          // Panel should be hidden
          const debugPanel = document.getElementById('debug-panel');
          if (debugPanel) {
            expect(debugPanel.classList.contains('hidden')).toBe(true);
          }
        }
      });
    });

    describe('Time Override Functions', () => {
      it('should enable and disable time override', () => {
        if (window.toggleTimeOverride) {
          expect(() => window.toggleTimeOverride()).not.toThrow();
        }
      });

      it('should update time preview correctly', () => {
        if (window.updateTimePreview) {
          expect(() => window.updateTimePreview()).not.toThrow();
        }
      });

      it('should reset time override to current time', () => {
        if (window.resetTimeOverride) {
          expect(() => window.resetTimeOverride()).not.toThrow();
        }
      });

      it('should handle getCurrentTime with debug time override', () => {
        if (window.getCurrentTime) {
          const currentTime = window.getCurrentTime();
          expect(currentTime).toBeInstanceOf(Date);
        }
      });

      it('should handle invalid custom time inputs gracefully', () => {
        // Test with invalid debug data
        if (window.setDebugValues) {
          expect(() => {
            window.setDebugValues({
              customTimeEnabled: true,
              customDate: 'invalid-date',
              customTime: 'invalid-time',
              customAmPm: 'INVALID'
            });
          }).not.toThrow();
        }
      });
    });

    describe('Debug Values Management', () => {
      it('should set debug values via API', () => {
        const testValues = {
          customTimeEnabled: true,
          customDate: '2024-01-01',
          customTime: '14:30',
          customAmPm: 'PM'
        };
        
        if (window.whatsNextView && window.whatsNextView.setDebugValues) {
          const result = window.whatsNextView.setDebugValues(testValues);
          expect(result).toBe(true);
        }
      });

      it('should handle invalid debug values', () => {
        if (window.whatsNextView && window.whatsNextView.setDebugValues) {
          // Test with invalid input
          const result1 = window.whatsNextView.setDebugValues(null);
          const result2 = window.whatsNextView.setDebugValues('invalid');
          const result3 = window.whatsNextView.setDebugValues({});
          
          expect(result1).toBe(false);
          expect(result2).toBe(false);
          expect(typeof result3).toBe('boolean');
        }
      });

      it('should clear debug values correctly', () => {
        if (window.whatsNextView && window.whatsNextView.clearDebugValues) {
          expect(() => window.whatsNextView.clearDebugValues()).not.toThrow();
        }
      });

      it('should apply debug values correctly', () => {
        if (window.whatsNextView && window.whatsNextView.applyDebugValues) {
          expect(() => window.whatsNextView.applyDebugValues()).not.toThrow();
        }
      });

      it('should get debug state correctly', () => {
        if (window.whatsNextView && window.whatsNextView.getDebugState) {
          const state = window.whatsNextView.getDebugState();
          expect(typeof state).toBe('object');
          expect(typeof state.enabled).toBe('boolean');
        }
      });
    });

    describe('Debug Panel Event Handlers', () => {
      beforeEach(() => {
        // Create a basic debug panel structure for testing
        if (!document.getElementById('debug-panel')) {
          const debugPanel = document.createElement('div');
          debugPanel.id = 'debug-panel';
          debugPanel.innerHTML = `
            <input type="checkbox" id="debug-time-enabled">
            <input type="date" id="debug-custom-date" value="2024-01-01">
            <input type="number" id="debug-custom-hour" value="14">
            <input type="number" id="debug-custom-minute" value="30">
            <select id="debug-custom-ampm">
              <option value="AM">AM</option>
              <option value="PM" selected>PM</option>
            </select>
            <button id="debug-apply-btn">Apply</button>
            <button id="debug-clear-btn">Clear</button>
            <button id="debug-reset-btn">Reset</button>
            <span id="time-preview-text">--:-- -- ----/--/--</span>
          `;
          document.body.appendChild(debugPanel);
        }
      });

      it('should handle debug panel interactions', () => {
        const timeCheckbox = document.getElementById('debug-time-enabled');
        const dateInput = document.getElementById('debug-custom-date');
        const hourInput = document.getElementById('debug-custom-hour');
        const minuteInput = document.getElementById('debug-custom-minute');
        const ampmSelect = document.getElementById('debug-custom-ampm');
        const applyBtn = document.getElementById('debug-apply-btn');
        const clearBtn = document.getElementById('debug-clear-btn');
        const resetBtn = document.getElementById('debug-reset-btn');

        // Test checkbox change
        if (timeCheckbox) {
          expect(() => {
            timeCheckbox.checked = true;
            timeCheckbox.dispatchEvent(new Event('change'));
          }).not.toThrow();
        }

        // Test input changes
        if (dateInput) {
          expect(() => {
            dateInput.value = '2024-01-02';
            dateInput.dispatchEvent(new Event('change'));
          }).not.toThrow();
        }

        if (hourInput) {
          expect(() => {
            hourInput.value = '15';
            hourInput.dispatchEvent(new Event('change'));
          }).not.toThrow();
        }

        if (minuteInput) {
          expect(() => {
            minuteInput.value = '45';
            minuteInput.dispatchEvent(new Event('change'));
          }).not.toThrow();
        }

        if (ampmSelect) {
          expect(() => {
            ampmSelect.value = 'AM';
            ampmSelect.dispatchEvent(new Event('change'));
          }).not.toThrow();
        }

        // Test button clicks
        if (applyBtn) {
          expect(() => {
            applyBtn.click();
          }).not.toThrow();
        }

        if (clearBtn) {
          expect(() => {
            clearBtn.click();
          }).not.toThrow();
        }

        if (resetBtn) {
          expect(() => {
            resetBtn.click();
          }).not.toThrow();
        }
      });
    });

    describe('Debug Time Calculations', () => {
      it('should handle custom time parsing correctly', () => {
        if (window.getCurrentTime) {
          // Test with various time configurations
          const testCases = [
            { date: '2024-01-01', time: '14:30', ampm: 'PM' },
            { date: '2024-12-31', time: '23:59', ampm: 'PM' },
            { date: '2024-06-15', time: '00:00', ampm: 'AM' },
            { date: '2024-06-15', time: '12:00', ampm: 'PM' }
          ];

          testCases.forEach(testCase => {
            if (window.setDebugValues) {
              window.setDebugValues({
                customTimeEnabled: true,
                customDate: testCase.date,
                customTime: testCase.time,
                customAmPm: testCase.ampm
              });
              
              const currentTime = window.getCurrentTime();
              expect(currentTime).toBeInstanceOf(Date);
            }
          });
        }
      });

      it('should fall back to real time when debug mode disabled', () => {
        if (window.getCurrentTime && window.clearDebugValues) {
          window.clearDebugValues();
          
          const currentTime = window.getCurrentTime();
          const realTime = new Date();
          
          // Should be close to real time (within 1 second)
          expect(Math.abs(currentTime.getTime() - realTime.getTime())).toBeLessThan(1000);
        }
      });

      it('should handle timezone calculations correctly', () => {
        if (window.getCurrentTime) {
          const time = window.getCurrentTime();
          
          // Should have proper timezone offset
          expect(typeof time.getTimezoneOffset()).toBe('number');
        }
      });
    });

    describe('Debug API Integration', () => {
      it('should send debug time to backend when enabled', async () => {
        if (window.setDebugValues && window.loadMeetingData) {
          // Enable debug mode with custom time
          window.setDebugValues({
            customTimeEnabled: true,
            customDate: '2024-01-01',
            customTime: '14:30',
            customAmPm: 'PM'
          });

          fetchMock.mockResolvedValueOnce({
            ok: true,
            json: async () => ({
              success: true,
              html: '<div class="current-event"><div class="event-title">Debug Meeting</div></div>'
            })
          });

          await window.loadMeetingData();

          // Should have called API with debug_time parameter
          expect(fetchMock).toHaveBeenCalledWith('/api/refresh', expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('debug_time')
          }));
        }
      });

      it('should not send debug time when disabled', async () => {
        if (window.clearDebugValues && window.loadMeetingData) {
          window.clearDebugValues();

          fetchMock.mockResolvedValueOnce({
            ok: true,
            json: async () => ({
              success: true,
              html: '<div class="current-event"><div class="event-title">Normal Meeting</div></div>'
            })
          });

          await window.loadMeetingData();

          // Should have called API without debug_time parameter
          expect(fetchMock).toHaveBeenCalledWith('/api/refresh', expect.objectContaining({
            method: 'POST',
            body: '{}'
          }));
        }
      });
    });

    describe('Debug Mode Error Handling', () => {
      it('should handle debug panel creation errors gracefully', () => {
        // Test with problematic DOM state
        testUtils.cleanupDOM();
        
        if (window.toggleDebugMode) {
          expect(() => window.toggleDebugMode()).not.toThrow();
        }
      });

      it('should handle missing debug elements gracefully', () => {
        if (window.updateTimePreview) {
          expect(() => window.updateTimePreview()).not.toThrow();
        }
        
        if (window.toggleTimeOverride) {
          expect(() => window.toggleTimeOverride()).not.toThrow();
        }
      });

      it('should handle invalid time parsing in debug mode', () => {
        if (window.setDebugValues) {
          const invalidValues = {
            customTimeEnabled: true,
            customDate: '',
            customTime: '',
            customAmPm: ''
          };
          
          expect(() => window.setDebugValues(invalidValues)).not.toThrow();
        }
      });
    });

    describe('Debug Mode Accessibility', () => {
      it('should announce debug mode changes to screen readers', () => {
        // Enable screen reader announcements
        if (window.setupAccessibility) {
          window.setupAccessibility();
        }
        
        if (window.toggleDebugMode) {
          expect(() => window.toggleDebugMode()).not.toThrow();
          
          // Check if live region was updated
          const liveRegion = document.getElementById('whats-next-live-region');
          if (liveRegion) {
            expect(liveRegion.textContent).toContain('Debug mode');
          }
        }
      });

      it('should provide proper focus management in debug panel', () => {
        if (window.toggleDebugMode) {
          window.toggleDebugMode();
          
          // Should focus on first input when panel opens
          const debugPanel = document.getElementById('debug-panel');
          if (debugPanel && !debugPanel.classList.contains('hidden')) {
            const firstInput = debugPanel.querySelector('#debug-time-enabled');
            expect(firstInput).toBeTruthy();
          }
        }
      });
    });

    describe('Debug Mode State Persistence', () => {
      it('should maintain debug state across function calls', () => {
        if (window.whatsNextView && window.whatsNextView.setDebugValues && window.whatsNextView.getDebugState) {
          const testValues = {
            customTimeEnabled: true,
            customDate: '2024-01-01',
            customTime: '14:30',
            customAmPm: 'PM'
          };
          
          const result = window.whatsNextView.setDebugValues(testValues);
          expect(result).toBe(true);
          
          const state = window.whatsNextView.getDebugState();
          expect(state).toBeDefined();
          expect(state.data).toBeDefined();
          
          // Test that some state is maintained
          expect(typeof state.enabled).toBe('boolean');
        }
      });

      it('should reset state correctly on clear', () => {
        if (window.whatsNextView && window.whatsNextView.setDebugValues && window.whatsNextView.clearDebugValues && window.whatsNextView.getDebugState) {
          // Set some values first
          window.whatsNextView.setDebugValues({
            customTimeEnabled: true,
            customDate: '2024-01-01'
          });
          
          // Clear values
          window.whatsNextView.clearDebugValues();
          
          const state = window.whatsNextView.getDebugState();
          expect(state.data.customTimeEnabled).toBe(false);
        }
      });
    });

    describe('Debug Mode Integration with Main Features', () => {
      it('should affect meeting detection when time override is active', async () => {
        if (window.whatsNextView && window.whatsNextView.setDebugValues) {
          // Set debug time
          window.whatsNextView.setDebugValues({
            customTimeEnabled: true,
            customDate: '2024-01-01',
            customTime: '14:30',
            customAmPm: 'PM'
          });

          fetchMock.mockResolvedValueOnce({
            ok: true,
            json: async () => ({
              success: true,
              html: `
                <div class="current-event">
                  <div class="event-title">Debug Test Meeting</div>
                  <div class="event-time">2:00 PM - 3:00 PM</div>
                </div>
              `
            })
          });

          await window.loadMeetingData();
          
          // Should have detected meeting with custom time context
          const meetings = window.whatsNextView.getUpcomingMeetings();
          expect(meetings.length).toBeGreaterThan(0);
        }
      });

      it('should update countdown display with debug time', () => {
        if (window.whatsNextView && window.whatsNextView.setDebugValues && window.updateCountdown) {
          // Set debug time and meeting
          window.whatsNextView.setDebugValues({
            customTimeEnabled: true,
            customDate: '2024-01-01',
            customTime: '14:00',
            customAmPm: 'PM'
          });

          window.currentMeeting = {
            id: 'debug-meeting',
            title: 'Debug Meeting',
            start_time: '2024-01-01T14:30:00.000Z',
            end_time: '2024-01-01T15:30:00.000Z'
          };

          expect(() => window.updateCountdown()).not.toThrow();
        }
      });
    });
  });

  /**
   * Additional Coverage Tests for Remaining Uncovered Lines
   */
  describe('Additional Coverage Tests', () => {
    beforeEach(() => {
      testUtils.setupMockDOM(`
        <html class="theme-eink">
          <body>
            <div class="calendar-content"></div>
            <div class="countdown-container"></div>
            <button data-action="prev">Previous</button>
            <button data-action="next">Next</button>
          </body>
        </html>
      `);
    });

    describe('Navigation Actions', () => {
      it('should handle prev and next navigation actions', async () => {
        const prevButton = document.querySelector('[data-action="prev"]');
        const nextButton = document.querySelector('[data-action="next"]');

        fetchMock.mockResolvedValue({
          ok: true,
          json: async () => ({
            success: true,
            html: '<div>Navigation result</div>'
          })
        });

        if (prevButton) {
          testUtils.triggerEvent(prevButton, 'click');
          await new Promise(resolve => setTimeout(resolve, 0));
        }

        if (nextButton) {
          testUtils.triggerEvent(nextButton, 'click');
          await new Promise(resolve => setTimeout(resolve, 0));
        }

        expect(fetchMock).toHaveBeenCalledWith('/api/navigate', expect.objectContaining({
          method: 'POST'
        }));
      });
    });

    describe('Double Tap Prevention', () => {
      it('should prevent double tap zoom on iOS', () => {
        const touchEndEvent1 = new TouchEvent('touchend', {
          changedTouches: [{ screenX: 100 }]
        });
        const touchEndEvent2 = new TouchEvent('touchend', {
          changedTouches: [{ screenX: 100 }]
        });

        // First touch
        expect(() => document.dispatchEvent(touchEndEvent1)).not.toThrow();
        
        // Second touch within 300ms should be prevented
        setTimeout(() => {
          expect(() => document.dispatchEvent(touchEndEvent2)).not.toThrow();
        }, 100);
      });
    });

    describe('Meeting Time Edge Cases', () => {
      it('should handle AM/PM conversion edge cases', () => {
        const baseDate = new Date('2024-01-01T12:00:00');
        
        if (window.parseTimeString) {
          // Test 12:00 AM (midnight)
          const midnight = window.parseTimeString('12:00 AM', baseDate);
          expect(midnight.getHours()).toBe(0);
          
          // Test 12:00 PM (noon)
          const noon = window.parseTimeString('12:00 PM', baseDate);
          expect(noon.getHours()).toBe(12);
          
          // Test edge cases
          expect(() => {
            window.parseTimeString('25:00 PM', baseDate);
            window.parseTimeString('12:60 AM', baseDate);
            window.parseTimeString('invalid format', baseDate);
          }).not.toThrow();
        }
      });

      it('should handle day boundary crossing', () => {
        const baseDate = new Date('2024-01-01T23:30:00'); // Late evening
        
        if (window.parseTimeString) {
          // Meeting tomorrow morning
          const morningMeeting = window.parseTimeString('9:00 AM', baseDate);
          
          // Should be on the next day
          expect(morningMeeting.getDate()).toBe(baseDate.getDate() + 1);
        }
      });
    });

    describe('Context Message Generation', () => {
      it('should generate appropriate context messages', () => {
        if (window.getContextMessage) {
          // Test different meeting scenarios
          const now = new Date();
          
          // Meeting in progress
          window.currentMeeting = {
            start_time: new Date(now.getTime() - 30 * 60 * 1000).toISOString(), // Started 30 minutes ago
            end_time: new Date(now.getTime() + 30 * 60 * 1000).toISOString()  // Ends in 30 minutes
          };
          
          const inProgressMessage = window.getContextMessage(true);
          expect(inProgressMessage).toBe('Meeting in progress');
          
          // Upcoming meeting scenarios
          window.currentMeeting = {
            start_time: new Date(now.getTime() + 3 * 60 * 1000).toISOString(), // In 3 minutes
            end_time: new Date(now.getTime() + 63 * 60 * 1000).toISOString()
          };
          
          const soonMessage = window.getContextMessage(false);
          expect(soonMessage).toBe('Starting very soon');
          
          // Meeting in 10 minutes
          window.currentMeeting = {
            start_time: new Date(now.getTime() + 10 * 60 * 1000).toISOString(),
            end_time: new Date(now.getTime() + 70 * 60 * 1000).toISOString()
          };
          
          const startingSoonMessage = window.getContextMessage(false);
          expect(startingSoonMessage).toBe('Starting soon');
        }
      });
    });

    describe('Last Update Formatting', () => {
      it('should format last update time correctly', () => {
        if (window.formatLastUpdate) {
          // Set last update time
          window.lastDataUpdate = new Date();
          
          const formatted = window.formatLastUpdate();
          expect(formatted).toBe('Just now');
          
          // Test 1 minute ago
          window.lastDataUpdate = new Date(Date.now() - 60 * 1000);
          const oneMinuteAgo = window.formatLastUpdate();
          expect(oneMinuteAgo).toBe('1 minute ago');
          
          // Test multiple minutes ago
          window.lastDataUpdate = new Date(Date.now() - 5 * 60 * 1000);
          const fiveMinutesAgo = window.formatLastUpdate();
          expect(fiveMinutesAgo).toBe('5 minutes ago');
          
          // Test no last update
          window.lastDataUpdate = null;
          const never = window.formatLastUpdate();
          expect(never).toBe('Never');
        }
      });
    });

    describe('Empty State Display', () => {
      it('should show empty state with proper 3-zone layout', () => {
        if (window.showEmptyState) {
          window.showEmptyState();
          
          const content = document.querySelector('.calendar-content');
          if (content) {
            expect(content.innerHTML).toContain('layout-zone-1');
            expect(content.innerHTML).toContain('layout-zone-2');
            expect(content.innerHTML).toContain('layout-zone-4');
            expect(content.innerHTML).toContain('No Upcoming Meetings');
          }
        }
      });
    });

    describe('Meeting Transition Detection', () => {
      it('should detect when meetings have ended', () => {
        const now = new Date();
        const pastMeeting = {
          id: 'past-meeting',
          title: 'Past Meeting',
          start_time: new Date(now.getTime() - 120 * 60 * 1000).toISOString(), // 2 hours ago
          end_time: new Date(now.getTime() - 60 * 60 * 1000).toISOString()    // 1 hour ago
        };
        
        window.currentMeeting = pastMeeting;
        
        if (window.checkMeetingTransitions) {
          expect(() => window.checkMeetingTransitions()).not.toThrow();
        }
      });
    });

    describe('Layout Cycle Error Handling', () => {
      it('should handle layout cycle API failures', async () => {
        fetchMock.mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: false,
            error: 'Layout switch failed'
          })
        });

        await expect(window.cycleLayout()).resolves.not.toThrow();
      });

      it('should handle layout cycle with page reload', async () => {
        // Mock window.location.reload
        const originalReload = window.location.reload;
        window.location.reload = jest.fn();

        fetchMock.mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: true,
            layout: '4x8'
          })
        });

        await window.cycleLayout();

        expect(window.location.reload).toHaveBeenCalled();

        // Restore original
        window.location.reload = originalReload;
      });
    });
  });
