/**
 * @fileoverview Comprehensive Jest test suite for Calendar Bot 3x4 Layout JavaScript Module
 * Tests all functions, API interactions, DOM manipulation, and user interactions
 * Target: 90%+ code coverage
 */

const fs = require('fs');
const path = require('path');

const moduleContent = fs.readFileSync(
  path.join(__dirname, '../../calendarbot/web/static/layouts/3x4/3x4.js'),
  'utf8'
);

/**
 * Test suite for Calendar Bot 3x4 Layout Module
 * Covers initialization, navigation, theme switching, auto-refresh, and mobile features
 */
describe('Calendar Bot 3x4 Layout Module (3x4.js)', () => {
  beforeEach(() => {
    // Reset DOM environment
    testUtils.cleanupDOM();
    
    // Setup basic HTML structure
    testUtils.setupMockDOM(`
      <html class="theme-eink">
        <head>
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>
          <div class="calendar-title">Test Calendar</div>
          <div class="status-line">Status: Ready</div>
          <div class="calendar-content">
            <div class="event">Test Event</div>
          </div>
          <div class="navigation-help">Navigation Help</div>
          <button data-action="prev">Previous</button>
          <button data-action="next">Next</button>
          <div class="calendar-header">
            <h1>Calendar Header</h1>
          </div>
        </body>
      </html>
    `);

    // Reset timers
    jest.clearAllTimers();
    jest.useFakeTimers();

    // Setup function spies BEFORE module loading to ensure event listeners bind to spies
    window.navigate = jest.fn();
    window.refresh = jest.fn();
    window.toggleTheme = jest.fn();
    window.cycleLayout = jest.fn();

    // Execute the module code
    eval(moduleContent);
    
    // Trigger DOMContentLoaded to initialize the module
    const event = new Event('DOMContentLoaded');
    document.dispatchEvent(event);
  });

  afterEach(() => {
    jest.clearAllTimers();
    jest.useRealTimers();
    fetch.mockClear();
  });

  /**
   * Test suite for Application Initialization
   */
  describe('Application Initialization', () => {
    it('should initialize the app correctly when DOM is loaded', () => {
      const logSpy = jest.spyOn(console, 'log');
      
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      expect(logSpy).toHaveBeenCalledWith('Calendar Bot Web Interface loaded');
      expect(logSpy).toHaveBeenCalledWith(expect.stringContaining('Initialized with theme:'));
    });

    it('should detect theme from HTML class correctly', () => {
      document.documentElement.className = 'theme-dark';
      
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      expect(window.getCurrentTheme()).toBe('dark');
    });

    it('should setup navigation buttons on initialization', () => {
      const addEventListenerSpy = jest.spyOn(document, 'addEventListener');
      
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      expect(addEventListenerSpy).toHaveBeenCalledWith('click', expect.any(Function));
    });

    it('should setup keyboard navigation on initialization', () => {
      const addEventListenerSpy = jest.spyOn(document, 'addEventListener');
      
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      expect(addEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
    });

    it('should setup auto-refresh when enabled', () => {
      const setIntervalSpy = jest.spyOn(global, 'setInterval');
      
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      if (window.isAutoRefreshEnabled()) {
        expect(setIntervalSpy).toHaveBeenCalledWith(expect.any(Function), 60000);
      }
    });
  });

  /**
   * Test suite for Navigation Functions
   */
  describe('Navigation Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should handle successful navigation action', async () => {
      testUtils.mockFetchSuccess({
        success: true,
        html: '<div class="updated-content">Updated content</div>'
      });
      
      const updatePageContentSpy = jest.fn();
      window.updatePageContent = updatePageContentSpy;
      
      await window.navigate('next');
      
      expect(fetch).toHaveBeenCalledWith('/api/navigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'next' })
      });
    });

    it('should handle failed navigation action', async () => {
      testUtils.mockFetchSuccess({ success: false, error: 'Navigation failed' });
      
      const showErrorMessageSpy = jest.fn();
      window.showErrorMessage = showErrorMessageSpy;
      
      await window.navigate('prev');
      
      expect(showErrorMessageSpy).toHaveBeenCalledWith('Navigation failed');
    });

    it('should handle navigation errors', async () => {
      testUtils.mockFetchError(new Error('Network error'));
      
      const showErrorMessageSpy = jest.fn();
      window.showErrorMessage = showErrorMessageSpy;
      
      await window.navigate('today');
      
      expect(showErrorMessageSpy).toHaveBeenCalledWith('Navigation error: Network error');
    });

    it('should show and hide loading indicator during navigation', async () => {
      testUtils.mockFetchSuccess({ success: true, html: '<div>New content</div>' });
      
      const showLoadingSpy = jest.fn();
      const hideLoadingSpy = jest.fn();
      window.showLoadingIndicator = showLoadingSpy;
      window.hideLoadingIndicator = hideLoadingSpy;
      
      await window.navigate('next');
      
      expect(showLoadingSpy).toHaveBeenCalled();
      expect(hideLoadingSpy).toHaveBeenCalled();
    });
  });

  /**
   * Test suite for Theme Functions
   */
  describe('Theme Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should toggle theme successfully', async () => {
      testUtils.mockFetchSuccess({ success: true, theme: 'dark' });
      
      const flashThemeChangeSpy = jest.fn();
      window.flashThemeChange = flashThemeChangeSpy;
      
      await window.toggleTheme();
      
      expect(fetch).toHaveBeenCalledWith('/api/theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      
      expect(window.getCurrentTheme()).toBe('dark');
      expect(flashThemeChangeSpy).toHaveBeenCalled();
    });

    it('should handle theme toggle failure', async () => {
      testUtils.mockFetchSuccess({ success: false });
      
      const logSpy = jest.spyOn(console, 'error');
      
      await window.toggleTheme();
      
      expect(logSpy).toHaveBeenCalledWith('Theme toggle failed');
    });

    it('should handle theme toggle errors', async () => {
      testUtils.mockFetchError(new Error('Theme error'));
      
      const logSpy = jest.spyOn(console, 'error');
      
      await window.toggleTheme();
      
      expect(logSpy).toHaveBeenCalledWith('Theme toggle error:', expect.any(Error));
    });

    it('should update HTML class when theme changes', async () => {
      testUtils.mockFetchSuccess({ success: true, theme: 'light' });
      
      await window.toggleTheme();
      
      expect(document.documentElement.className).toContain('theme-light');
    });
  });

  /**
   * Test suite for Layout Functions
   */
  describe('Layout Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should cycle layout successfully', async () => {
      testUtils.mockFetchSuccess({ success: true, layout: '4x8' });
      
      const reloadSpy = jest.fn();
      Object.defineProperty(window.location, 'reload', { value: reloadSpy });
      
      await window.cycleLayout();
      
      expect(fetch).toHaveBeenCalledWith('/api/layout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      
      expect(reloadSpy).toHaveBeenCalled();
    });

    it('should set specific layout successfully', async () => {
      testUtils.mockFetchSuccess({ success: true, layout: 'whats-next-view' });
      
      const reloadSpy = jest.fn();
      Object.defineProperty(window.location, 'reload', { value: reloadSpy });
      
      await window.setLayout('whats-next-view');
      
      expect(fetch).toHaveBeenCalledWith('/api/layout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ layout: 'whats-next-view' })
      });
      
      expect(reloadSpy).toHaveBeenCalled();
    });

    it('should handle layout change failure', async () => {
      testUtils.mockFetchSuccess({ success: false, error: 'Layout error' });
      
      const showErrorMessageSpy = jest.fn();
      window.showErrorMessage = showErrorMessageSpy;
      
      await window.cycleLayout();
      
      expect(showErrorMessageSpy).toHaveBeenCalledWith('Layout switch failed');
    });
  });

  /**
   * Test suite for Refresh Functions
   */
  describe('Refresh Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should perform manual refresh successfully', async () => {
      testUtils.mockFetchSuccess({
        success: true,
        html: '<div class="new-content">Refreshed content</div>'
      });
      
      const updatePageContentSpy = jest.fn();
      const showSuccessMessageSpy = jest.fn();
      window.updatePageContent = updatePageContentSpy;
      window.showSuccessMessage = showSuccessMessageSpy;
      
      await window.refresh();
      
      expect(fetch).toHaveBeenCalledWith('/api/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      expect(updatePageContentSpy).toHaveBeenCalled();
      expect(showSuccessMessageSpy).toHaveBeenCalledWith('Data refreshed');
    });

    it('should perform silent refresh successfully', async () => {
      testUtils.mockFetchSuccess({
        success: true,
        html: '<div>Silent refresh content</div>'
      });
      
      const updatePageContentSpy = jest.fn();
      window.updatePageContent = updatePageContentSpy;
      
      await window.refreshSilent();
      
      expect(fetch).toHaveBeenCalledWith('/api/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      expect(updatePageContentSpy).toHaveBeenCalled();
    });

    it('should handle refresh failure', async () => {
      testUtils.mockFetchSuccess({ success: false });
      
      const showErrorMessageSpy = jest.fn();
      window.showErrorMessage = showErrorMessageSpy;
      
      await window.refresh();
      
      expect(showErrorMessageSpy).toHaveBeenCalledWith('Refresh failed');
    });

    it('should handle silent refresh errors gracefully', async () => {
      testUtils.mockFetchError(new Error('Silent error'));
      
      const logSpy = jest.spyOn(console, 'error');
      
      await window.refreshSilent();
      
      expect(logSpy).toHaveBeenCalledWith('Silent refresh error:', expect.any(Error));
    });
  });

  /**
   * Test suite for Auto-Refresh Functions
   */
  describe('Auto-Refresh Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should toggle auto-refresh on when disabled', () => {
      const setIntervalSpy = jest.spyOn(global, 'setInterval');
      const logSpy = jest.spyOn(console, 'log');
      
      // Disable first
      if (window.isAutoRefreshEnabled()) {
        window.toggleAutoRefresh();
      }
      
      // Then enable
      window.toggleAutoRefresh();
      
      expect(setIntervalSpy).toHaveBeenCalledWith(expect.any(Function), 60000);
      expect(logSpy).toHaveBeenCalledWith('Auto-refresh enabled');
    });

    it('should toggle auto-refresh off when enabled', () => {
      const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
      const logSpy = jest.spyOn(console, 'log');
      
      // Ensure enabled first
      if (!window.isAutoRefreshEnabled()) {
        window.toggleAutoRefresh();
      }
      
      // Then disable
      window.toggleAutoRefresh();
      
      expect(clearIntervalSpy).toHaveBeenCalled();
      expect(logSpy).toHaveBeenCalledWith('Auto-refresh disabled');
    });
  });

  /**
   * Test suite for Keyboard Navigation
   */
  describe('Keyboard Navigation', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      // Mock navigation functions
      window.navigate = jest.fn();
      window.refresh = jest.fn();
      window.toggleTheme = jest.fn();
      window.cycleLayout = jest.fn();
    });

    it.each([
      ['ArrowLeft', 'prev'],
      ['ArrowRight', 'next'],
      [' ', 'today'],
      ['Home', 'week-start'],
      ['End', 'week-end']
    ])('should handle %s key for %s action', (key, expectedAction) => {
      const keyEvent = new KeyboardEvent('keydown', { key, cancelable: true });
      
      document.dispatchEvent(keyEvent);
      
      expect(window.navigate).toHaveBeenCalledWith(expectedAction);
      expect(keyEvent.defaultPrevented).toBe(true);
    });

    it.each(['r', 'R'])('should handle %s key for refresh action', (key) => {
      const keyEvent = new KeyboardEvent('keydown', { key, cancelable: true });
      
      document.dispatchEvent(keyEvent);
      
      expect(window.refresh).toHaveBeenCalled();
    });

    it.each(['t', 'T'])('should handle %s key for toggleTheme action', (key) => {
      const keyEvent = new KeyboardEvent('keydown', { key, cancelable: true });
      
      document.dispatchEvent(keyEvent);
      
      expect(window.toggleTheme).toHaveBeenCalled();
    });

    it.each(['l', 'L'])('should handle %s key for cycleLayout action', (key) => {
      const keyEvent = new KeyboardEvent('keydown', { key, cancelable: true });
      
      document.dispatchEvent(keyEvent);
      
      expect(window.cycleLayout).toHaveBeenCalled();
    });
  });

  /**
   * Test suite for Mobile and Touch Interactions
   */
  describe('Mobile and Touch Interactions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      window.navigate = jest.fn();
    });

    it('should handle swipe right for previous navigation', () => {
      // Simulate swipe right
      const touchStart = new TouchEvent('touchstart', {
        changedTouches: [{ screenX: 100 }]
      });
      const touchEnd = new TouchEvent('touchend', {
        changedTouches: [{ screenX: 200 }]
      });
      
      document.dispatchEvent(touchStart);
      document.dispatchEvent(touchEnd);
      
      expect(window.navigate).toHaveBeenCalledWith('prev');
    });

    it('should handle swipe left for next navigation', () => {
      // Simulate swipe left
      const touchStart = new TouchEvent('touchstart', {
        changedTouches: [{ screenX: 200 }]
      });
      const touchEnd = new TouchEvent('touchend', {
        changedTouches: [{ screenX: 100 }]
      });
      
      document.dispatchEvent(touchStart);
      document.dispatchEvent(touchEnd);
      
      expect(window.navigate).toHaveBeenCalledWith('next');
    });

    it('should ignore small swipe gestures', () => {
      // Simulate small swipe (under threshold)
      const touchStart = new TouchEvent('touchstart', {
        changedTouches: [{ screenX: 100 }]
      });
      const touchEnd = new TouchEvent('touchend', {
        changedTouches: [{ screenX: 120 }]
      });
      
      document.dispatchEvent(touchStart);
      document.dispatchEvent(touchEnd);
      
      expect(window.navigate).not.toHaveBeenCalled();
    });

    it('should prevent double-tap zoom', () => {
      jest.useRealTimers();
      
      const touchEnd1 = new TouchEvent('touchend', { cancelable: true });
      const touchEnd2 = new TouchEvent('touchend', { cancelable: true });
      
      document.dispatchEvent(touchEnd1);
      
      // Dispatch second touch within 300ms
      setTimeout(() => {
        document.dispatchEvent(touchEnd2);
        expect(touchEnd2.defaultPrevented).toBe(true);
      }, 100);
      
      jest.useFakeTimers();
    });
  });

  /**
   * Test suite for Button Click Handlers
   */
  describe('Button Click Handlers', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      window.navigate = jest.fn();
    });

    it('should handle prev button click', () => {
      const prevButton = document.querySelector('[data-action="prev"]');
      const clickEvent = new MouseEvent('click', { cancelable: true });
      
      prevButton.dispatchEvent(clickEvent);
      
      expect(window.navigate).toHaveBeenCalledWith('prev');
      expect(clickEvent.defaultPrevented).toBe(true);
    });

    it('should handle next button click', () => {
      const nextButton = document.querySelector('[data-action="next"]');
      const clickEvent = new MouseEvent('click', { cancelable: true });
      
      nextButton.dispatchEvent(clickEvent);
      
      expect(window.navigate).toHaveBeenCalledWith('next');
      expect(clickEvent.defaultPrevented).toBe(true);
    });

    it('should ignore clicks on elements without data-action', () => {
      const normalDiv = document.querySelector('.calendar-content');
      const clickEvent = new MouseEvent('click');
      
      normalDiv.dispatchEvent(clickEvent);
      
      expect(window.navigate).not.toHaveBeenCalled();
    });
  });

  /**
   * Test suite for UI Feedback Functions
   */
  describe('UI Feedback Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should show loading indicator with correct styling', () => {
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

    it('should show error messages correctly', () => {
      window.showErrorMessage('Test error');
      
      const message = Array.from(document.querySelectorAll('div')).find(el =>
        el.textContent.includes('Test error')
      );
      
      expect(message).toBeTruthy();
      expect(message.style.background).toBe('rgb(220, 53, 69)');
    });

    it('should show success messages correctly', () => {
      window.showSuccessMessage('Test success');
      
      const message = Array.from(document.querySelectorAll('div')).find(el =>
        el.textContent.includes('Test success')
      );
      
      expect(message).toBeTruthy();
      expect(message.style.background).toBe('rgb(40, 167, 69)');
    });

    it('should auto-remove messages after timeout', (done) => {
      jest.useRealTimers();
      
      window.showMessage('Temporary message', 'info');
      
      let message = Array.from(document.querySelectorAll('div')).find(el =>
        el.textContent.includes('Temporary message')
      );
      expect(message).toBeTruthy();
      
      setTimeout(() => {
        message = Array.from(document.querySelectorAll('div')).find(el =>
          el.textContent.includes('Temporary message')
        );
        expect(message).toBeFalsy();
        jest.useFakeTimers();
        done();
      }, 3100);
    });
  });

  /**
   * Test suite for Content Update Functions
   */
  describe('Content Update Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should update page content correctly', () => {
      const newHtml = `
        <html>
          <head><title>New Title</title></head>
          <body>
            <div class="calendar-title">New Calendar</div>
            <div class="status-line">New Status</div>
            <div class="calendar-content">New Content</div>
          </body>
        </html>
      `;
      
      window.updatePageContent(newHtml);
      
      expect(document.querySelector('.calendar-title').innerHTML).toBe('New Calendar');
      expect(document.querySelector('.status-line').innerHTML).toBe('New Status');
      expect(document.querySelector('.calendar-content').innerHTML).toBe('New Content');
      expect(document.title).toBe('New Title');
    });

    it('should maintain theme class after content update', () => {
      const originalTheme = window.getCurrentTheme();
      const newHtml = '<html><body><div class="calendar-title">Updated</div></body></html>';
      
      window.updatePageContent(newHtml);
      
      expect(document.documentElement.className).toContain(`theme-${originalTheme}`);
    });

    it('should handle missing elements gracefully', () => {
      const newHtml = '<html><body><div class="non-existent">Test</div></body></html>';
      
      expect(() => window.updatePageContent(newHtml)).not.toThrow();
    });
  });

  /**
   * Test suite for Visual Feedback Functions
   */
  describe('Visual Feedback Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should flash navigation feedback correctly', () => {
      window.flashNavigationFeedback('next');
      
      const feedback = Array.from(document.querySelectorAll('div')).find(el =>
        el.textContent.includes('Next →')
      );
      
      expect(feedback).toBeTruthy();
      expect(feedback.style.position).toBe('fixed');
      expect(feedback.style.zIndex).toBe('1000');
    });

    it('should flash theme change correctly', () => {
      window.flashThemeChange();
      
      const overlay = Array.from(document.querySelectorAll('div')).find(el =>
        el.style.position === 'fixed' && el.style.zIndex === '9999'
      );
      
      expect(overlay).toBeTruthy();
    });
  });

  /**
   * Test suite for Global Exports and Debug
   */
  describe('Global Exports and Debug', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should export functions to window object', () => {
      expect(typeof window.navigate).toBe('function');
      expect(typeof window.toggleTheme).toBe('function');
      expect(typeof window.cycleLayout).toBe('function');
      expect(typeof window.setLayout).toBe('function');
      expect(typeof window.refresh).toBe('function');
      expect(typeof window.toggleAutoRefresh).toBe('function');
      expect(typeof window.getCurrentTheme).toBe('function');
      expect(typeof window.isAutoRefreshEnabled).toBe('function');
    });

    it('should provide calendarBot debug object', () => {
      expect(window.calendarBot).toBeDefined();
      expect(typeof window.calendarBot.navigate).toBe('function');
      expect(typeof window.calendarBot.toggleTheme).toBe('function');
      expect(typeof window.calendarBot.getCurrentTheme).toBe('function');
      expect(typeof window.calendarBot.currentTheme).toBe('function');
    });

    it('should return correct theme from debug functions', () => {
      const theme = window.calendarBot.currentTheme();
      expect(typeof theme).toBe('string');
      expect(theme).toBe(window.getCurrentTheme());
    });
  });

  /**
   * Test suite for Edge Cases and Error Handling
   */
  describe('Edge Cases and Error Handling', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should handle fetch network errors gracefully', async () => {
      testUtils.mockFetchError(new Error('Network unavailable'));
      
      const showErrorMessageSpy = jest.fn();
      window.showErrorMessage = showErrorMessageSpy;
      
      await window.navigate('next');
      
      expect(showErrorMessageSpy).toHaveBeenCalledWith('Navigation error: Network unavailable');
    });

    it('should handle invalid JSON responses', async () => {
      fetch.mockResolvedValueOnce({
        json: () => Promise.reject(new Error('Invalid JSON'))
      });
      
      const showErrorMessageSpy = jest.fn();
      window.showErrorMessage = showErrorMessageSpy;
      
      await window.refresh();
      
      expect(showErrorMessageSpy).toHaveBeenCalledWith('Refresh error: Invalid JSON');
    });

    it('should handle missing DOM elements during initialization', () => {
      testUtils.cleanupDOM();
      
      expect(() => {
        const event = new Event('DOMContentLoaded');
        document.dispatchEvent(event);
      }).not.toThrow();
    });

    it('should handle theme detection with no theme class', () => {
      document.documentElement.className = 'no-theme';
      
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      expect(window.getCurrentTheme()).toBe('eink'); // default theme
    });
  });

  /**
   * Test suite for Integration Scenarios
   */
  describe('Integration Scenarios', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should handle complete navigation workflow', async () => {
      testUtils.mockFetchSuccess({
        success: true,
        html: '<div class="calendar-content">Navigation result</div>'
      });
      
      const updatePageContentSpy = jest.fn();
      window.updatePageContent = updatePageContentSpy;
      
      await window.navigate('next');
      
      expect(fetch).toHaveBeenCalledWith('/api/navigate', expect.any(Object));
      expect(updatePageContentSpy).toHaveBeenCalled();
    });

    it('should handle theme switching with content updates', async () => {
      testUtils.mockFetchSuccess({ success: true, theme: 'dark' });
      
      await window.toggleTheme();
      
      expect(window.getCurrentTheme()).toBe('dark');
      expect(document.documentElement.className).toContain('theme-dark');
    });

    it('should handle auto-refresh cycle correctly', async () => {
      testUtils.mockFetchSuccess({
        success: true,
        html: '<div>Auto refresh content</div>'
      });
      
      const updatePageContentSpy = jest.fn();
      window.updatePageContent = updatePageContentSpy;
      
      await window.refreshSilent();
      
      expect(updatePageContentSpy).toHaveBeenCalled();
    });
  });
});