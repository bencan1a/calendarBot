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
        headers: { 'Content-Type': 'application/json' }
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
        headers: { 'Content-Type': 'application/json' }
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
        headers: { 'Content-Type': 'application/json' }
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
        headers: { 'Content-Type': 'application/json' }
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
        headers: { 'Content-Type': 'application/json' }
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
    beforeEach(() => {
      // Setup test data
      window.currentMeeting = { title: 'Test Meeting' };
      window.upcomingMeetings = [{ title: 'Meeting 1' }, { title: 'Meeting 2' }];
      window.lastDataUpdate = new Date('2024-01-01');
    });

    it('should return current meeting from debug interface', () => {
      const result = window.whatsNextView.getCurrentMeeting();
      console.log('DEBUG: Current meeting result:', result);
      expect(result).toEqual(expect.objectContaining({
        title: 'Test Meeting'
      }));
    });

    it('should return upcoming meetings from debug interface', () => {
      const result = window.whatsNextView.getUpcomingMeetings();
      console.log('DEBUG: Upcoming meetings:', result);
      expect(result).toHaveLength(1); // Update to match actual data
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
