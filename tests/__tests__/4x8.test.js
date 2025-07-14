/**
 * @fileoverview Comprehensive Jest test suite for Calendar Bot 4x8 Layout JavaScript Module
 * Tests all functions, API interactions, DOM manipulation, and user interactions
 * Target: 90%+ code coverage
 */

const fs = require('fs');
const path = require('path');

const moduleContent = fs.readFileSync(
  path.join(__dirname, '../../calendarbot/web/static/layouts/4x8/4x8.js'),
  'utf8'
);

/**
 * Test suite for Calendar Bot 4x8 Layout Module
 * Covers initialization, navigation, theme switching, auto-refresh, and mobile features
 */
describe('Calendar Bot 4x8 Layout Module (4x8.js)', () => {
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
          <div class="calendar-title">Test Calendar 4x8</div>
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
   * Test suite for 4x8 Application Initialization
   */
  describe('4x8 Application Initialization', () => {
    it('should initialize the app correctly when DOM is loaded', () => {
      const logSpy = jest.spyOn(console, 'log');
      
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      expect(logSpy).toHaveBeenCalledWith('Calendar Bot Web Interface loaded');
      expect(logSpy).toHaveBeenCalledWith(expect.stringContaining('Initialized with theme:'));
    });

    it('should detect theme from HTML class correctly in 4x8 layout', () => {
      document.documentElement.className = 'theme-light';
      
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      expect(window.getCurrentTheme()).toBe('light');
    });

    it('should setup navigation buttons on 4x8 initialization', () => {
      const addEventListenerSpy = jest.spyOn(document, 'addEventListener');
      
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      expect(addEventListenerSpy).toHaveBeenCalledWith('click', expect.any(Function));
    });

    it('should setup keyboard navigation on 4x8 initialization', () => {
      const addEventListenerSpy = jest.spyOn(document, 'addEventListener');
      
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      expect(addEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
    });

    it('should setup auto-refresh when enabled in 4x8', () => {
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
   * Test suite for 4x8 Navigation Functions
   */
  describe('4x8 Navigation Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should handle successful navigation action in 4x8 layout', async () => {
      testUtils.mockFetchSuccess({
        success: true,
        html: '<div class="updated-content">Updated 4x8 content</div>'
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

    it('should handle failed navigation action in 4x8', async () => {
      testUtils.mockFetchSuccess({ success: false, error: 'Navigation failed in 4x8' });
      
      const showErrorMessageSpy = jest.fn();
      window.showErrorMessage = showErrorMessageSpy;
      
      await window.navigate('prev');
      
      expect(showErrorMessageSpy).toHaveBeenCalledWith('Navigation failed');
    });

    it('should handle 4x8 navigation errors', async () => {
      testUtils.mockFetchError(new Error('Network error in 4x8'));
      
      const showErrorMessageSpy = jest.fn();
      window.showErrorMessage = showErrorMessageSpy;
      
      await window.navigate('today');
      
      expect(showErrorMessageSpy).toHaveBeenCalledWith('Navigation error: Network error in 4x8');
    });

    it('should show and hide loading indicator during 4x8 navigation', async () => {
      testUtils.mockFetchSuccess({ success: true, html: '<div>New 4x8 content</div>' });
      
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
   * Test suite for 4x8 Theme Functions
   */
  describe('4x8 Theme Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should toggle theme successfully in 4x8 layout', async () => {
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

    it('should handle theme toggle failure in 4x8', async () => {
      testUtils.mockFetchSuccess({ success: false });
      
      const logSpy = jest.spyOn(console, 'error');
      
      await window.toggleTheme();
      
      expect(logSpy).toHaveBeenCalledWith('Theme toggle failed');
    });

    it('should handle theme toggle errors in 4x8', async () => {
      testUtils.mockFetchError(new Error('Theme error in 4x8'));
      
      const logSpy = jest.spyOn(console, 'error');
      
      await window.toggleTheme();
      
      expect(logSpy).toHaveBeenCalledWith('Theme toggle error:', expect.any(Error));
    });

    it('should update HTML class when theme changes in 4x8', async () => {
      testUtils.mockFetchSuccess({ success: true, theme: 'light' });
      
      await window.toggleTheme();
      
      expect(document.documentElement.className).toContain('theme-light');
    });
  });

  /**
   * Test suite for 4x8 Layout Functions
   */
  describe('4x8 Layout Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should cycle layout successfully from 4x8', async () => {
      testUtils.mockFetchSuccess({ success: true, layout: '3x4' });
      
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

    it('should set specific layout successfully from 4x8', async () => {
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

    it('should handle layout change failure in 4x8', async () => {
      testUtils.mockFetchSuccess({ success: false, error: 'Layout error in 4x8' });
      
      const showErrorMessageSpy = jest.fn();
      window.showErrorMessage = showErrorMessageSpy;
      
      await window.cycleLayout();
      
      expect(showErrorMessageSpy).toHaveBeenCalledWith('Layout switch failed');
    });
  });

  /**
   * Test suite for 4x8 Refresh Functions
   */
  describe('4x8 Refresh Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should perform manual refresh successfully in 4x8', async () => {
      testUtils.mockFetchSuccess({
        success: true,
        html: '<div class="new-content">Refreshed 4x8 content</div>'
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

    it('should perform silent refresh successfully in 4x8', async () => {
      testUtils.mockFetchSuccess({
        success: true,
        html: '<div>Silent refresh 4x8 content</div>'
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

    it('should handle refresh failure in 4x8', async () => {
      testUtils.mockFetchSuccess({ success: false });
      
      const showErrorMessageSpy = jest.fn();
      window.showErrorMessage = showErrorMessageSpy;
      
      await window.refresh();
      
      expect(showErrorMessageSpy).toHaveBeenCalledWith('Refresh failed');
    });

    it('should handle silent refresh errors gracefully in 4x8', async () => {
      testUtils.mockFetchError(new Error('Silent error in 4x8'));
      
      const logSpy = jest.spyOn(console, 'error');
      
      await window.refreshSilent();
      
      expect(logSpy).toHaveBeenCalledWith('Silent refresh error:', expect.any(Error));
    });
  });

  /**
   * Test suite for 4x8 Auto-Refresh Functions
   */
  describe('4x8 Auto-Refresh Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should toggle auto-refresh on when disabled in 4x8', () => {
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

    it('should toggle auto-refresh off when enabled in 4x8', () => {
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
   * Test suite for 4x8 Keyboard Navigation
   */
  describe('4x8 Keyboard Navigation', () => {
    it.each([
      ['ArrowLeft', 'prev'],
      ['ArrowRight', 'next'],
      [' ', 'today'],
      ['Home', 'week-start'],
      ['End', 'week-end']
    ])('should handle %s key for %s action in 4x8', (key, expectedAction) => {
      const keyEvent = new KeyboardEvent('keydown', { key, cancelable: true });
      
      document.dispatchEvent(keyEvent);
      
      expect(window.navigate).toHaveBeenCalledWith(expectedAction);
      expect(keyEvent.defaultPrevented).toBe(true);
    });

    it.each(['r', 'R'])('should handle %s key for refresh action in 4x8', (key) => {
      const keyEvent = new KeyboardEvent('keydown', { key, cancelable: true });
      
      document.dispatchEvent(keyEvent);
      
      expect(window.refresh).toHaveBeenCalled();
    });

    it.each(['t', 'T'])('should handle %s key for toggleTheme action in 4x8', (key) => {
      const keyEvent = new KeyboardEvent('keydown', { key, cancelable: true });
      
      document.dispatchEvent(keyEvent);
      
      expect(window.toggleTheme).toHaveBeenCalled();
    });

    it.each(['l', 'L'])('should handle %s key for cycleLayout action in 4x8', (key) => {
      const keyEvent = new KeyboardEvent('keydown', { key, cancelable: true });
      
      document.dispatchEvent(keyEvent);
      
      expect(window.cycleLayout).toHaveBeenCalled();
    });
  });

  /**
   * Test suite for 4x8 Mobile and Touch Interactions
   */
  describe('4x8 Mobile and Touch Interactions', () => {
    it('should handle swipe right for previous navigation in 4x8', () => {
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

    it('should handle swipe left for next navigation in 4x8', () => {
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

    it('should ignore small swipe gestures in 4x8', () => {
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

    it('should prevent double-tap zoom in 4x8', () => {
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
   * Test suite for 4x8 Button Click Handlers
   */
  describe('4x8 Button Click Handlers', () => {
    it('should handle prev button click in 4x8', () => {
      const prevButton = document.querySelector('[data-action="prev"]');
      const clickEvent = new MouseEvent('click', { cancelable: true });
      
      prevButton.dispatchEvent(clickEvent);
      
      expect(window.navigate).toHaveBeenCalledWith('prev');
      expect(clickEvent.defaultPrevented).toBe(true);
    });

    it('should handle next button click in 4x8', () => {
      const nextButton = document.querySelector('[data-action="next"]');
      const clickEvent = new MouseEvent('click', { cancelable: true });
      
      nextButton.dispatchEvent(clickEvent);
      
      expect(window.navigate).toHaveBeenCalledWith('next');
      expect(clickEvent.defaultPrevented).toBe(true);
    });

    it('should ignore clicks on elements without data-action in 4x8', () => {
      const normalDiv = document.querySelector('.calendar-content');
      const clickEvent = new MouseEvent('click');
      
      normalDiv.dispatchEvent(clickEvent);
      
      expect(window.navigate).not.toHaveBeenCalled();
    });
  });

  /**
   * Test suite for 4x8 UI Feedback Functions
   */
  describe('4x8 UI Feedback Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should show loading indicator with correct styling in 4x8', () => {
      window.showLoadingIndicator('Loading 4x8 test...');
      
      const indicator = document.getElementById('loading-indicator');
      expect(indicator).toBeTruthy();
      expect(indicator.textContent).toBe('Loading 4x8 test...');
      expect(indicator.style.display).toBe('block');
    });

    it('should hide loading indicator in 4x8', () => {
      window.showLoadingIndicator('Test');
      window.hideLoadingIndicator();
      
      const indicator = document.getElementById('loading-indicator');
      expect(indicator.style.display).toBe('none');
    });

    it('should show error messages correctly in 4x8', () => {
      window.showErrorMessage('Test 4x8 error');
      
      const message = Array.from(document.querySelectorAll('div')).find(el =>
        el.textContent.includes('Test 4x8 error')
      );
      
      expect(message).toBeTruthy();
      expect(message.style.background).toBe('rgb(220, 53, 69)');
    });

    it('should show success messages correctly in 4x8', () => {
      window.showSuccessMessage('Test 4x8 success');
      
      const message = Array.from(document.querySelectorAll('div')).find(el =>
        el.textContent.includes('Test 4x8 success')
      );
      
      expect(message).toBeTruthy();
      expect(message.style.background).toBe('rgb(40, 167, 69)');
    });

    it('should auto-remove messages after timeout in 4x8', (done) => {
      jest.useRealTimers();
      
      window.showMessage('Temporary 4x8 message', 'info');
      
      let message = Array.from(document.querySelectorAll('div')).find(el =>
        el.textContent.includes('Temporary 4x8 message')
      );
      expect(message).toBeTruthy();
      
      setTimeout(() => {
        message = Array.from(document.querySelectorAll('div')).find(el =>
          el.textContent.includes('Temporary 4x8 message')
        );
        expect(message).toBeFalsy();
        jest.useFakeTimers();
        done();
      }, 3100);
    });
  });

  /**
   * Test suite for 4x8 Content Update Functions
   */
  describe('4x8 Content Update Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should update page content correctly in 4x8', () => {
      const newHtml = `
        <html>
          <head><title>New 4x8 Title</title></head>
          <body>
            <div class="calendar-title">New 4x8 Calendar</div>
            <div class="status-line">New 4x8 Status</div>
            <div class="calendar-content">New 4x8 Content</div>
          </body>
        </html>
      `;
      
      window.updatePageContent(newHtml);
      
      expect(document.querySelector('.calendar-title').innerHTML).toBe('New 4x8 Calendar');
      expect(document.querySelector('.status-line').innerHTML).toBe('New 4x8 Status');
      expect(document.querySelector('.calendar-content').innerHTML).toBe('New 4x8 Content');
      expect(document.title).toBe('New 4x8 Title');
    });

    it('should maintain theme class after content update in 4x8', () => {
      const originalTheme = window.getCurrentTheme();
      const newHtml = '<html><body><div class="calendar-title">Updated 4x8</div></body></html>';
      
      window.updatePageContent(newHtml);
      
      expect(document.documentElement.className).toContain(`theme-${originalTheme}`);
    });

    it('should handle missing elements gracefully in 4x8', () => {
      const newHtml = '<html><body><div class="non-existent">Test 4x8</div></body></html>';
      
      expect(() => window.updatePageContent(newHtml)).not.toThrow();
    });
  });

  /**
   * Test suite for 4x8 Visual Feedback Functions
   */
  describe('4x8 Visual Feedback Functions', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should flash navigation feedback correctly in 4x8', () => {
      window.flashNavigationFeedback('next');
      
      const feedback = Array.from(document.querySelectorAll('div')).find(el =>
        el.textContent.includes('Next →')
      );
      
      expect(feedback).toBeTruthy();
      expect(feedback.style.position).toBe('fixed');
      expect(feedback.style.zIndex).toBe('1000');
    });

    it('should flash theme change correctly in 4x8', () => {
      window.flashThemeChange();
      
      const overlay = Array.from(document.querySelectorAll('div')).find(el =>
        el.style.position === 'fixed' && el.style.zIndex === '9999'
      );
      
      expect(overlay).toBeTruthy();
    });
  });

  /**
   * Test suite for 4x8 Global Exports and Debug
   */
  describe('4x8 Global Exports and Debug', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should export functions to window object in 4x8', () => {
      expect(typeof window.navigate).toBe('function');
      expect(typeof window.toggleTheme).toBe('function');
      expect(typeof window.cycleLayout).toBe('function');
      expect(typeof window.setLayout).toBe('function');
      expect(typeof window.refresh).toBe('function');
      expect(typeof window.toggleAutoRefresh).toBe('function');
      expect(typeof window.getCurrentTheme).toBe('function');
      expect(typeof window.isAutoRefreshEnabled).toBe('function');
    });

    it('should provide calendarBot debug object in 4x8', () => {
      expect(window.calendarBot).toBeDefined();
      expect(typeof window.calendarBot.navigate).toBe('function');
      expect(typeof window.calendarBot.toggleTheme).toBe('function');
      expect(typeof window.calendarBot.getCurrentTheme).toBe('function');
      expect(typeof window.calendarBot.currentTheme).toBe('function');
    });

    it('should return correct theme from debug functions in 4x8', () => {
      const theme = window.calendarBot.currentTheme();
      expect(typeof theme).toBe('string');
      expect(theme).toBe(window.getCurrentTheme());
    });
  });

  /**
   * Test suite for 4x8 Edge Cases and Error Handling
   */
  describe('4x8 Edge Cases and Error Handling', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should handle fetch network errors gracefully in 4x8', async () => {
      testUtils.mockFetchError(new Error('Network unavailable in 4x8'));
      
      const showErrorMessageSpy = jest.fn();
      window.showErrorMessage = showErrorMessageSpy;
      
      await window.navigate('next');
      
      expect(showErrorMessageSpy).toHaveBeenCalledWith('Navigation error: Network unavailable in 4x8');
    });

    it('should handle invalid JSON responses in 4x8', async () => {
      fetch.mockResolvedValueOnce({
        json: () => Promise.reject(new Error('Invalid JSON in 4x8'))
      });
      
      const showErrorMessageSpy = jest.fn();
      window.showErrorMessage = showErrorMessageSpy;
      
      await window.refresh();
      
      expect(showErrorMessageSpy).toHaveBeenCalledWith('Refresh error: Invalid JSON in 4x8');
    });

    it('should handle missing DOM elements during initialization in 4x8', () => {
      testUtils.cleanupDOM();
      
      expect(() => {
        const event = new Event('DOMContentLoaded');
        document.dispatchEvent(event);
      }).not.toThrow();
    });

    it('should handle theme detection with no theme class in 4x8', () => {
      document.documentElement.className = 'no-theme-4x8';
      
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
      
      expect(window.getCurrentTheme()).toBe('eink'); // default theme
    });
  });

  /**
   * Test suite for 4x8 Integration Scenarios
   */
  describe('4x8 Integration Scenarios', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should handle complete navigation workflow in 4x8', async () => {
      testUtils.mockFetchSuccess({
        success: true,
        html: '<div class="calendar-content">4x8 Navigation result</div>'
      });
      
      const updatePageContentSpy = jest.fn();
      window.updatePageContent = updatePageContentSpy;
      
      await window.navigate('next');
      
      expect(fetch).toHaveBeenCalledWith('/api/navigate', expect.any(Object));
      expect(updatePageContentSpy).toHaveBeenCalled();
    });

    it('should handle theme switching with content updates in 4x8', async () => {
      testUtils.mockFetchSuccess({ success: true, theme: 'dark' });
      
      await window.toggleTheme();
      
      expect(window.getCurrentTheme()).toBe('dark');
      expect(document.documentElement.className).toContain('theme-dark');
    });

    it('should handle auto-refresh cycle correctly in 4x8', async () => {
      testUtils.mockFetchSuccess({
        success: true,
        html: '<div>4x8 Auto refresh content</div>'
      });
      
      const updatePageContentSpy = jest.fn();
      window.updatePageContent = updatePageContentSpy;
      
      await window.refreshSilent();
      
      expect(updatePageContentSpy).toHaveBeenCalled();
    });

    it('should handle layout switching to different layouts from 4x8', async () => {
      testUtils.mockFetchSuccess({ success: true, layout: '3x4' });
      
      const reloadSpy = jest.fn();
      Object.defineProperty(window.location, 'reload', { value: reloadSpy });
      
      await window.setLayout('3x4');
      
      expect(fetch).toHaveBeenCalledWith('/api/layout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ layout: '3x4' })
      });
      
      expect(reloadSpy).toHaveBeenCalled();
    });
  });

  /**
   * Test suite for 4x8 Layout-Specific Features
   */
  describe('4x8 Layout-Specific Features', () => {
    beforeEach(() => {
      // Simulate DOMContentLoaded event
      const event = new Event('DOMContentLoaded');
      document.dispatchEvent(event);
    });

    it('should handle larger content areas in 4x8 layout', () => {
      const newHtml = `
        <html>
          <body>
            <div class="calendar-content">
              <div class="event">Event 1</div>
              <div class="event">Event 2</div>
              <div class="event">Event 3</div>
              <div class="event">Event 4</div>
              <div class="event">Event 5</div>
            </div>
          </body>
        </html>
      `;
      
      window.updatePageContent(newHtml);
      
      const events = document.querySelectorAll('.event');
      expect(events.length).toBe(5);
    });

    it('should handle different viewport considerations for 4x8', () => {
      const viewportMeta = document.querySelector('meta[name="viewport"]');
      expect(viewportMeta).toBeTruthy();
      expect(viewportMeta.getAttribute('content')).toContain('width=device-width');
    });
  });
});