/**
 * @fileoverview Comprehensive test suite for 4x8.js
 * Tests calendar navigation, theme switching, and user interactions
 */

describe('4x8 Layout Module (4x8.js)', () => {
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
          <div class="calendar-content">Calendar Content</div>
          <div class="calendar-title">Calendar Title</div>
          <div class="status-line">Status</div>
          <div class="navigation-help">Help</div>
          <div class="calendar-header">Header</div>
          <div class="header-info">Header Info</div>
          <div class="date-info">Date Info</div>
          <header>Main Header</header>
          <div class="header">Alt Header</div>
          <h1>Page Title</h1>
          <button data-action="prev">Previous</button>
          <button data-action="next">Next</button>
        </body>
      </html>
    `);

    // Setup spies
    setIntervalSpy = jest.spyOn(global, 'setInterval').mockImplementation((fn, delay) => {
      return setTimeout(fn, 0); // Execute immediately for testing
    });
    clearIntervalSpy = jest.spyOn(global, 'clearInterval');
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
    
    // JSDOM will naturally ignore location.reload() calls from the source code
    // Tests focus on API functionality rather than browser navigation behavior
    
    // Mock fetch
    fetchMock = fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        html: '<div class="calendar-content">Updated Content</div>'
      })
    });

    // Reset global state variables
    if (typeof window !== 'undefined') {
      window.currentTheme = 'eink';
      window.autoRefreshInterval = null;
      window.autoRefreshEnabled = true;
    }

    // Load the source file and trigger initialization
    require('../../calendarbot/web/static/layouts/4x8/4x8.js');
    
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
      
      expect(logSpy).toHaveBeenCalledWith('Calendar Bot Web Interface loaded');
      expect(logSpy).toHaveBeenCalledWith('Initialized with theme: eink');
    });

    it('should detect theme from HTML class', () => {
      document.documentElement.className = 'theme-dark';
      
      // Trigger DOMContentLoaded
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      expect(window.getCurrentTheme()).toBe('dark');
    });

    it('should have required functions available globally', () => {
      expect(typeof window.navigate).toBe('function');
      expect(typeof window.toggleTheme).toBe('function');
      expect(typeof window.cycleLayout).toBe('function');
      expect(typeof window.setLayout).toBe('function');
      expect(typeof window.refresh).toBe('function');
      expect(typeof window.refreshSilent).toBe('function');
      expect(typeof window.toggleAutoRefresh).toBe('function');
      expect(typeof window.getCurrentTheme).toBe('function');
      expect(typeof window.isAutoRefreshEnabled).toBe('function');
    });

    it('should have UI feedback functions available', () => {
      expect(typeof window.showLoadingIndicator).toBe('function');
      expect(typeof window.hideLoadingIndicator).toBe('function');
      expect(typeof window.showErrorMessage).toBe('function');
      expect(typeof window.showSuccessMessage).toBe('function');
      expect(typeof window.showMessage).toBe('function');
    });

    it('should have debug interface available', () => {
      expect(typeof window.calendarBot).toBe('object');
      expect(typeof window.calendarBot.navigate).toBe('function');
      expect(typeof window.calendarBot.toggleTheme).toBe('function');
      expect(typeof window.calendarBot.cycleLayout).toBe('function');
      expect(typeof window.calendarBot.getCurrentTheme).toBe('function');
    });
  });

  describe('Navigation Functions', () => {
    it('should handle navigation requests successfully', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div class="calendar-content">Next Day</div>'
        })
      });

      await window.navigate('next');

      expect(fetchMock).toHaveBeenCalledWith('/api/navigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'next' })
      });
    });

    it('should handle navigation API errors', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: false,
          error: 'Navigation failed'
        })
      });

      await expect(window.navigate('prev')).resolves.not.toThrow();
      expect(consoleLogSpy).toHaveBeenCalledWith('Navigation action: prev');
    });

    it('should handle navigation network errors', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Network error'));

      await expect(window.navigate('today')).resolves.not.toThrow();
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

    it('should update HTML class when theme changes', async () => {
      document.documentElement.className = 'theme-eink';
      
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          theme: 'dark'
        })
      });

      await window.toggleTheme();

      expect(document.documentElement.className).toBe('theme-dark');
      expect(window.getCurrentTheme()).toBe('dark');
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
          layout: 'whats-next-view'
        })
      });

      await window.cycleLayout();

      expect(fetchMock).toHaveBeenCalledWith('/api/layout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
    });

    it('should set specific layout', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          layout: '3x4'
        })
      });

      await window.setLayout('3x4');

      expect(fetchMock).toHaveBeenCalledWith('/api/layout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ layout: '3x4' })
      });
    });

    it('should handle layout cycle errors', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Layout error'));

      await expect(window.cycleLayout()).resolves.not.toThrow();
    });

    it('should handle layout set errors', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Layout error'));

      await expect(window.setLayout('invalid')).resolves.not.toThrow();
    });
  });

  describe('Refresh Functions', () => {
    it('should perform manual refresh', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div class="calendar-content">Refreshed content</div>'
        })
      });

      await window.refresh();

      expect(fetchMock).toHaveBeenCalledWith('/api/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
    });

    it('should perform silent refresh', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div class="calendar-content">Silently refreshed</div>'
        })
      });

      await window.refreshSilent();

      expect(fetchMock).toHaveBeenCalledWith('/api/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
    });

    it('should handle refresh errors', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Refresh error'));

      await expect(window.refresh()).resolves.not.toThrow();
    });

    it('should handle silent refresh errors', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Silent refresh error'));

      await expect(window.refreshSilent()).resolves.not.toThrow();
    });
  });

  describe('Auto-Refresh Functionality', () => {
    it('should setup auto-refresh interval', () => {
      // Trigger initialization
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);

      expect(setIntervalSpy).toHaveBeenCalledWith(expect.any(Function), 60000);
    });

    it('should toggle auto-refresh off', () => {
      window.autoRefreshEnabled = true;
      window.autoRefreshInterval = setInterval(() => {}, 1000);

      window.toggleAutoRefresh();

      expect(window.isAutoRefreshEnabled()).toBe(false);
      expect(clearIntervalSpy).toHaveBeenCalled();
    });

    it('should toggle auto-refresh on', () => {
      window.autoRefreshEnabled = false;
      window.autoRefreshInterval = null;

      window.toggleAutoRefresh();

      expect(window.isAutoRefreshEnabled()).toBe(true);
    });
  });

  describe('Navigation Button Handlers', () => {
    it('should handle prev button clicks', async () => {
      const prevButton = document.querySelector('[data-action="prev"]');
      
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div>Previous day</div>'
        })
      });
      
      testUtils.triggerEvent(prevButton, 'click');
      
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/navigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'prev' })
      });
    });

    it('should handle next button clicks', async () => {
      const nextButton = document.querySelector('[data-action="next"]');
      
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div>Next day</div>'
        })
      });
      
      testUtils.triggerEvent(nextButton, 'click');
      
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/navigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'next' })
      });
    });
  });

  describe('Keyboard Navigation', () => {
    it('should handle ArrowLeft key for previous', async () => {
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div>Previous</div>'
        })
      });
      
      const keyEvent = new KeyboardEvent('keydown', { key: 'ArrowLeft' });
      document.dispatchEvent(keyEvent);
      
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/navigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'prev' })
      });
    });

    it('should handle ArrowRight key for next', async () => {
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div>Next</div>'
        })
      });
      
      const keyEvent = new KeyboardEvent('keydown', { key: 'ArrowRight' });
      document.dispatchEvent(keyEvent);
      
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/navigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'next' })
      });
    });

    it('should handle Space key for today', async () => {
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div>Today</div>'
        })
      });
      
      const keyEvent = new KeyboardEvent('keydown', { key: ' ' });
      document.dispatchEvent(keyEvent);
      
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/navigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'today' })
      });
    });

    it('should handle R key for refresh', async () => {
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
      
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
    });

    it('should handle T key for theme toggle', async () => {
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
      
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
    });

    it('should handle L key for layout cycle', async () => {
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          layout: 'whats-next-view'
        })
      });
      
      const keyEvent = new KeyboardEvent('keydown', { key: 'l' });
      document.dispatchEvent(keyEvent);
      
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/layout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
    });

    it('should handle Home key for week start', async () => {
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div>Week Start</div>'
        })
      });
      
      const keyEvent = new KeyboardEvent('keydown', { key: 'Home' });
      document.dispatchEvent(keyEvent);
      
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/navigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'week-start' })
      });
    });

    it('should handle End key for week end', async () => {
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div>Week End</div>'
        })
      });
      
      const keyEvent = new KeyboardEvent('keydown', { key: 'End' });
      document.dispatchEvent(keyEvent);
      
      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/navigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'week-end' })
      });
    });
  });

  describe('Touch/Mobile Events', () => {
    it('should handle touch swipe right for previous', async () => {
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div>Previous</div>'
        })
      });
      
      // Simulate swipe right
      const touchStartEvent = new TouchEvent('touchstart', {
        changedTouches: [{ screenX: 100 }]
      });
      document.dispatchEvent(touchStartEvent);

      const touchEndEvent = new TouchEvent('touchend', {
        changedTouches: [{ screenX: 200 }]  // Swipe distance > 50 threshold
      });
      document.dispatchEvent(touchEndEvent);

      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/navigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'prev' })
      });
    });

    it('should handle touch swipe left for next', async () => {
      fetchMock.mockClear();
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div>Next</div>'
        })
      });
      
      // Simulate swipe left
      const touchStartEvent = new TouchEvent('touchstart', {
        changedTouches: [{ screenX: 200 }]
      });
      document.dispatchEvent(touchStartEvent);

      const touchEndEvent = new TouchEvent('touchend', {
        changedTouches: [{ screenX: 100 }]  // Swipe distance < -50 threshold
      });
      document.dispatchEvent(touchEndEvent);

      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).toHaveBeenCalledWith('/api/navigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'next' })
      });
    });

    it('should ignore small swipe gestures', async () => {
      // Clear any pending timers and fetch calls to avoid auto-refresh interference
      jest.clearAllTimers();
      fetchMock.mockClear();
      
      // Temporarily disable auto-refresh to prevent interference
      const originalAutoRefresh = window.isAutoRefreshEnabled();
      if (originalAutoRefresh) {
        window.toggleAutoRefresh(); // Disable
      }
      
      // Simulate small swipe (below threshold)
      const touchStartEvent = new TouchEvent('touchstart', {
        changedTouches: [{ screenX: 100 }]
      });
      document.dispatchEvent(touchStartEvent);

      const touchEndEvent = new TouchEvent('touchend', {
        changedTouches: [{ screenX: 120 }]  // Swipe distance < 50 threshold
      });
      document.dispatchEvent(touchEndEvent);

      await new Promise(resolve => setTimeout(resolve, 0));
      
      expect(fetchMock).not.toHaveBeenCalled();
      
      // Restore auto-refresh state
      if (originalAutoRefresh && !window.isAutoRefreshEnabled()) {
        window.toggleAutoRefresh(); // Re-enable
      }
    });

    it('should prevent double-tap zoom', () => {
      const preventDefault = jest.fn();
      
      // First touch
      const firstTouchEvent = new TouchEvent('touchend');
      firstTouchEvent.preventDefault = preventDefault;
      document.dispatchEvent(firstTouchEvent);

      // Second touch within 300ms
      const secondTouchEvent = new TouchEvent('touchend');
      secondTouchEvent.preventDefault = preventDefault;
      document.dispatchEvent(secondTouchEvent);

      expect(preventDefault).toHaveBeenCalled();
    });
  });

  describe('UI Feedback Functions', () => {
    it('should show loading indicator', () => {
      window.showLoadingIndicator('Loading test...');
      
      const indicator = document.getElementById('loading-indicator');
      expect(indicator).toBeTruthy();
      expect(indicator.textContent).toBe('Loading test...');
      expect(indicator.style.display).toBe('block');
    });

    it('should hide loading indicator', () => {
      window.showLoadingIndicator('Test');
      window.hideLoadingIndicator();
      
      const indicator = document.getElementById('loading-indicator');
      expect(indicator.style.display).toBe('none');
    });

    it('should show error messages', () => {
      expect(() => window.showErrorMessage('Error occurred')).not.toThrow();
    });

    it('should show success messages', () => {
      expect(() => window.showSuccessMessage('Success')).not.toThrow();
    });

    it('should show info messages', () => {
      expect(() => window.showMessage('Info message', 'info')).not.toThrow();
    });

    it('should flash navigation feedback', () => {
      expect(() => window.flashNavigationFeedback('next')).not.toThrow();
    });

    it('should flash theme change', () => {
      expect(() => window.flashThemeChange()).not.toThrow();
    });
  });

  describe('Content Update Functions', () => {
    it('should update page content', () => {
      const newHTML = `
        <html>
          <head><title>New Title</title></head>
          <body>
            <div class="calendar-content">New Content</div>
            <div class="calendar-title">New Title</div>
            <h1>New Header</h1>
          </body>
        </html>
      `;

      window.updatePageContent(newHTML);

      const calendarContent = document.querySelector('.calendar-content');
      const calendarTitle = document.querySelector('.calendar-title');
      const header = document.querySelector('h1');

      expect(calendarContent.textContent).toBe('New Content');
      expect(calendarTitle.textContent).toBe('New Title');
      expect(header.textContent).toBe('New Header');
      expect(document.title).toBe('New Title');
    });

    it('should maintain theme class during content update', () => {
      // Set theme class and initialize module properly
      document.documentElement.className = 'theme-dark';
      
      // Trigger DOMContentLoaded to initialize the module's internal currentTheme variable
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      // Verify theme is detected correctly
      expect(window.getCurrentTheme()).toBe('dark');
      
      const newHTML = `
        <html>
          <body>
            <div class="calendar-content">Updated</div>
          </body>
        </html>
      `;

      // The updatePageContent function should preserve existing theme
      window.updatePageContent(newHTML);

      // Theme class should be maintained after content update
      expect(document.documentElement.className).toBe('theme-dark');
    });
  });

  describe('Utility Functions', () => {
    it('should return current theme', () => {
      // Ensure DOM is set up with proper theme class
      document.documentElement.className = 'theme-eink';
      
      // Trigger initialization to detect theme
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      expect(window.getCurrentTheme()).toBe('eink');
    });

    it('should return auto-refresh status', () => {
      expect(window.isAutoRefreshEnabled()).toBe(true);
    });
  });

  describe('Integration Tests', () => {
    it('should handle complete navigation workflow', async () => {
      fetchMock.mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          html: '<div class="calendar-content">Integration test</div>'
        })
      });

      // Trigger initialization
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);

      // Navigate
      await window.navigate('next');
      
      expect(fetchMock).toHaveBeenCalled();
    });

    it('should handle error scenarios gracefully', async () => {
      fetchMock.mockRejectedValue(new Error('Network error'));

      await expect(window.navigate('next')).resolves.not.toThrow();
      await expect(window.toggleTheme()).resolves.not.toThrow();
      await expect(window.cycleLayout()).resolves.not.toThrow();
      await expect(window.setLayout('test')).resolves.not.toThrow();
      await expect(window.refresh()).resolves.not.toThrow();
      await expect(window.refreshSilent()).resolves.not.toThrow();
    });
  });

  describe('Edge Cases', () => {
    it('should handle missing DOM elements', () => {
      testUtils.cleanupDOM();
      
      expect(() => window.updatePageContent('<div>test</div>')).not.toThrow();
      expect(() => window.showLoadingIndicator()).not.toThrow();
      expect(() => window.hideLoadingIndicator()).not.toThrow();
    });

    it('should handle theme detection with no theme class', () => {
      document.documentElement.className = '';
      
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      // Should not throw and should handle gracefully
      expect(() => window.getCurrentTheme()).not.toThrow();
    });

    it('should handle auto-refresh when already disabled', () => {
      // First disable auto-refresh through the proper API
      if (window.isAutoRefreshEnabled()) {
        window.toggleAutoRefresh(); // This will disable it
      }
      
      // Verify it's disabled
      expect(window.isAutoRefreshEnabled()).toBe(false);
      
      // Now toggle it back on
      expect(() => window.toggleAutoRefresh()).not.toThrow();
      expect(window.isAutoRefreshEnabled()).toBe(true);
    });
  });
});