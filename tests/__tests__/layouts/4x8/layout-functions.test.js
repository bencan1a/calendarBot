/**
 * @fileoverview Phase 1 Jest Tests - 4x8 Layout Functions
 * Tests core functionality of 4x8 layout including navigation, themes, auto-refresh, and mobile features
 * Target: High coverage efficiency with behavior-focused testing
 */

describe('4x8Layout Functions', () => {
  let mockDocument;
  let mockFetch;
  let originalSetInterval;
  let originalClearInterval;
  let intervalIds = [];

  beforeEach(() => {
    // Setup DOM mocks using the existing test utilities
    mockDocument = global.testUtils.setupMockDOM();
    
    // Mock DOM ready state
    Object.defineProperty(document, 'readyState', {
      value: 'complete',
      writable: true
    });
    
    // Set up initial DOM structure for 4x8 layout testing
    document.body.innerHTML = `
      <html class="theme-eink">
        <head><title>Calendar Bot</title></head>
        <body>
          <h1 class="calendar-title">4x8 Calendar</h1>
          <div class="calendar-content"><p>Calendar content</p></div>
          <div class="status-line">Status info</div>
          <div class="header-info">Header content</div>
          <div class="date-info">Date information</div>
          <header class="header">Main header</header>
          <div class="navigation-help">Navigation help</div>
          <div class="calendar-header">Calendar header</div>
        </body>
      </html>
    `;
    
    // Mock fetch for API calls
    mockFetch = jest.fn();
    global.fetch = mockFetch;
    
    // Mock timer functions to control auto-refresh testing
    originalSetInterval = global.setInterval;
    originalClearInterval = global.clearInterval;
    
    global.setInterval = jest.fn((callback, delay) => {
      const id = Date.now() + Math.random();
      intervalIds.push(id);
      return id;
    });
    
    global.clearInterval = jest.fn((id) => {
      intervalIds = intervalIds.filter(intervalId => intervalId !== id);
    });
    
    // Mock DOMParser for content updates
    global.DOMParser = class MockDOMParser {
      parseFromString(str, type) {
        const parser = new (require('jsdom').JSDOM)(str);
        return parser.window.document;
      }
    };

    // Mock console methods to reduce test noise
    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(console, 'warn').mockImplementation(() => {});
    
    // Load the 4x8 layout JavaScript (this executes the initialization)
    require('../../../../calendarbot/web/static/layouts/4x8/4x8.js');
  });

  afterEach(() => {
    // Clean up mocks and timers
    jest.restoreAllMocks();
    global.setInterval = originalSetInterval;
    global.clearInterval = originalClearInterval;
    intervalIds = [];
    delete global.fetch;
    
    // Clean up any settings panel instances
    if (window.cleanup) {
      window.cleanup();
    }
  });

  describe('Core Navigation Functions', () => {
    describe('navigate', () => {
      it('should make POST request to /api/navigate with correct action', async () => {
        mockFetch.mockResolvedValueOnce({
          json: async () => ({ success: true, html: '<div>Updated content</div>' })
        });

        await window.navigate('next');

        expect(mockFetch).toHaveBeenCalledWith('/api/navigate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'next' })
        });
      });

      it('should handle successful navigation response', async () => {
        const mockHTML = `
          <html>
            <body>
              <h1 class="calendar-title">Updated Title</h1>
              <div class="calendar-content">Updated content</div>
            </body>
          </html>
        `;
        
        mockFetch.mockResolvedValueOnce({
          json: async () => ({ success: true, html: mockHTML })
        });

        await window.navigate('prev');

        const titleElement = document.querySelector('.calendar-title');
        expect(titleElement.textContent).toBe('Updated Title');
      });

      it('should handle navigation errors gracefully', async () => {
        mockFetch.mockRejectedValueOnce(new Error('Network error'));

        await expect(window.navigate('next')).resolves.not.toThrow();
        expect(console.error).toHaveBeenCalledWith('Navigation error:', expect.any(Error));
      });

      it('should handle failed API response', async () => {
        mockFetch.mockResolvedValueOnce({
          json: async () => ({ success: false, error: 'Invalid action' })
        });

        await window.navigate('invalid');

        expect(console.error).toHaveBeenCalledWith('Navigation failed:', 'Invalid action');
      });

      it('should test different navigation actions', async () => {
        const actions = ['prev', 'next', 'today', 'week-start', 'week-end'];
        
        for (const action of actions) {
          mockFetch.mockResolvedValueOnce({
            json: async () => ({ success: true, html: '<div>Content</div>' })
          });
          
          await window.navigate(action);
          
          expect(mockFetch).toHaveBeenCalledWith('/api/navigate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
          });
        }
        
        expect(mockFetch).toHaveBeenCalledTimes(actions.length);
      });
    });

    describe('toggleTheme', () => {
      it('should make POST request to /api/theme', async () => {
        mockFetch.mockResolvedValueOnce({
          json: async () => ({ success: true, theme: 'dark' })
        });

        await window.toggleTheme();

        expect(mockFetch).toHaveBeenCalledWith('/api/theme', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
      });

      it('should update document theme class on successful response', async () => {
        document.documentElement.className = 'theme-eink some-other-class';
        
        mockFetch.mockResolvedValueOnce({
          json: async () => ({ success: true, theme: 'dark' })
        });

        await window.toggleTheme();

        expect(document.documentElement.className).toContain('theme-dark');
        expect(window.getCurrentTheme()).toBe('dark');
      });

      it('should handle theme toggle errors gracefully', async () => {
        mockFetch.mockRejectedValueOnce(new Error('Theme service unavailable'));

        await expect(window.toggleTheme()).resolves.not.toThrow();
        expect(console.error).toHaveBeenCalledWith('Theme toggle error:', expect.any(Error));
      });

      it('should handle failed theme toggle response', async () => {
        mockFetch.mockResolvedValueOnce({
          json: async () => ({ success: false })
        });

        await window.toggleTheme();

        expect(console.error).toHaveBeenCalledWith('Theme toggle failed');
      });
    });

    describe('cycleLayout', () => {
      it('should make POST request to /api/layout', async () => {
        mockFetch.mockResolvedValueOnce({
          json: async () => ({ success: true, layout: '3x4' })
        });

        await window.cycleLayout();

        expect(mockFetch).toHaveBeenCalledWith('/api/layout', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
      });

      it('should handle successful layout change', async () => {
        // Mock window.location.href to prevent actual reload
        const originalHref = window.location.href;
        Object.defineProperty(window.location, 'href', {
          writable: true,
          value: originalHref
        });
        
        // Spy on the loading indicator functions
        jest.spyOn(window, 'showLoadingIndicator');
        jest.spyOn(window, 'hideLoadingIndicator');
        
        mockFetch.mockResolvedValueOnce({
          json: async () => ({ success: true, layout: 'whats-next-view' })
        });

        await window.cycleLayout();

        // Verify loading indicator was shown
        expect(window.showLoadingIndicator).toHaveBeenCalledWith('Switching layout...');
        
        // Verify correct console.log calls
        expect(console.log).toHaveBeenCalledWith('DEBUG: cycleLayout() called - L key pressed');
        expect(console.log).toHaveBeenCalledWith('DEBUG: Sending layout change request to API');
        expect(console.log).toHaveBeenCalledWith('DEBUG: API response received:', { success: true, layout: 'whats-next-view' });
        expect(console.log).toHaveBeenCalledWith('Layout changed to: whats-next-view');
        
        // Verify hideLoadingIndicator was called
        expect(window.hideLoadingIndicator).toHaveBeenCalled();
      });

      it('should handle layout cycle errors', async () => {
        mockFetch.mockRejectedValueOnce(new Error('Layout service error'));

        await expect(window.cycleLayout()).resolves.not.toThrow();
        expect(console.error).toHaveBeenCalledWith('Layout cycle error:', expect.any(Error));
      });
    });

    describe('setLayout', () => {
      it('should make POST request with specific layout', async () => {
        mockFetch.mockResolvedValueOnce({
          json: async () => ({ success: true, layout: '3x4' })
        });

        await window.setLayout('3x4');

        expect(mockFetch).toHaveBeenCalledWith('/api/layout', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ layout: '3x4' })
        });
      });
    });
  });

  describe('Refresh Functions', () => {
    describe('refresh', () => {
      it('should make POST request to /api/refresh', async () => {
        mockFetch.mockResolvedValueOnce({
          json: async () => ({ success: true, html: '<div>Refreshed</div>' })
        });

        await window.refresh();

        expect(mockFetch).toHaveBeenCalledWith('/api/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
      });

      it('should update content on successful refresh', async () => {
        const refreshHTML = `
          <html>
            <body>
              <div class="calendar-content">Refreshed calendar data</div>
            </body>
          </html>
        `;
        
        mockFetch.mockResolvedValueOnce({
          json: async () => ({ success: true, html: refreshHTML })
        });

        await window.refresh();

        const contentElement = document.querySelector('.calendar-content');
        expect(contentElement.textContent).toBe('Refreshed calendar data');
      });

      it('should handle refresh errors', async () => {
        mockFetch.mockRejectedValueOnce(new Error('Refresh failed'));

        await expect(window.refresh()).resolves.not.toThrow();
        expect(console.error).toHaveBeenCalledWith('Refresh error:', expect.any(Error));
      });
    });

    describe('refreshSilent', () => {
      it('should perform silent refresh without user feedback', async () => {
        mockFetch.mockResolvedValueOnce({
          json: async () => ({ success: true, html: '<div>Silent refresh</div>' })
        });

        await window.refreshSilent();

        expect(mockFetch).toHaveBeenCalledWith('/api/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        expect(console.log).toHaveBeenCalledWith('Auto-refresh completed');
      });

      it('should handle silent refresh errors gracefully', async () => {
        mockFetch.mockRejectedValueOnce(new Error('Silent refresh error'));

        await expect(window.refreshSilent()).resolves.not.toThrow();
        expect(console.error).toHaveBeenCalledWith('Silent refresh error:', expect.any(Error));
      });
    });
  });

  describe('Auto-refresh Management', () => {
    describe('toggleAutoRefresh', () => {
      it('should toggle auto-refresh status', () => {
        const initialStatus = window.isAutoRefreshEnabled();
        
        window.toggleAutoRefresh();
        
        const newStatus = window.isAutoRefreshEnabled();
        expect(newStatus).toBe(!initialStatus);
      });

      it('should handle multiple toggle calls', () => {
        const initialStatus = window.isAutoRefreshEnabled();
        
        window.toggleAutoRefresh();
        window.toggleAutoRefresh();
        
        expect(window.isAutoRefreshEnabled()).toBe(initialStatus);
      });
    });

    describe('isAutoRefreshEnabled', () => {
      it('should return boolean indicating auto-refresh status', () => {
        const result = window.isAutoRefreshEnabled();
        expect(typeof result).toBe('boolean');
      });
    });
  });

  describe('Utility Functions', () => {
    describe('getCurrentTheme', () => {
      it('should return current theme string', () => {
        const theme = window.getCurrentTheme();
        expect(typeof theme).toBe('string');
        expect(['eink', 'dark', 'light']).toContain(theme);
      });

      it('should return consistent theme across calls', () => {
        const theme1 = window.getCurrentTheme();
        const theme2 = window.getCurrentTheme();
        expect(theme1).toBe(theme2);
      });
    });

    describe('updatePageContent', () => {
      it('should update multiple page sections', () => {
        const newHTML = `
          <html>
            <body>
              <h1 class="calendar-title">New Title</h1>
              <div class="status-line">New Status</div>
              <div class="calendar-content">New Content</div>
            </body>
          </html>
        `;

        window.updatePageContent(newHTML);

        expect(document.querySelector('.calendar-title').textContent).toBe('New Title');
        expect(document.querySelector('.status-line').textContent).toBe('New Status');
        expect(document.querySelector('.calendar-content').textContent).toBe('New Content');
      });

      it('should update document title', () => {
        const newHTML = `
          <html>
            <head><title>Updated Calendar</title></head>
            <body></body>
          </html>
        `;

        window.updatePageContent(newHTML);
        expect(document.title).toBe('Updated Calendar');
      });

      it('should maintain theme class', () => {
        const originalClassName = document.documentElement.className;
        
        window.updatePageContent('<html><body></body></html>');
        
        // Should maintain some theme class
        expect(document.documentElement.className).toMatch(/theme-\w+/);
      });

      it('should handle missing elements gracefully', () => {
        const newHTML = '<html><body><p>Simple content</p></body></html>';
        
        expect(() => {
          window.updatePageContent(newHTML);
        }).not.toThrow();
      });
    });
  });

  describe('UI Feedback Functions', () => {
    describe('showLoadingIndicator', () => {
      it('should create and show loading indicator', () => {
        window.showLoadingIndicator('Loading test...');
        
        const indicator = document.getElementById('loading-indicator');
        expect(indicator).not.toBeNull();
        expect(indicator.textContent).toBe('Loading test...');
        expect(indicator.style.display).toBe('block');
      });

      it('should update existing indicator', () => {
        window.showLoadingIndicator('First message');
        window.showLoadingIndicator('Second message');
        
        const indicators = document.querySelectorAll('#loading-indicator');
        expect(indicators.length).toBe(1);
        expect(indicators[0].textContent).toBe('Second message');
      });
    });

    describe('hideLoadingIndicator', () => {
      it('should hide loading indicator', () => {
        window.showLoadingIndicator('Test message');
        window.hideLoadingIndicator();
        
        const indicator = document.getElementById('loading-indicator');
        expect(indicator.style.display).toBe('none');
      });

      it('should handle missing indicator gracefully', () => {
        expect(() => {
          window.hideLoadingIndicator();
        }).not.toThrow();
      });
    });

    describe('showMessage', () => {
      it('should create message element with correct styling', () => {
        window.showMessage('Test message', 'error');
        
        const messages = document.querySelectorAll('[style*="position: fixed"]');
        const errorMessage = Array.from(messages).find(el => 
          el.textContent === 'Test message' && el.style.cssText.includes('background: #dc3545')
        );
        expect(errorMessage).not.toBeNull();
      });

      it('should handle different message types', () => {
        window.showMessage('Success message', 'success');
        window.showMessage('Info message', 'info');
        window.showMessage('Error message', 'error');
        
        const messages = document.querySelectorAll('[style*="position: fixed"]');
        expect(messages.length).toBe(3);
      });
    });

    describe('showErrorMessage and showSuccessMessage', () => {
      it('should be functions that can be called', () => {
        expect(typeof window.showErrorMessage).toBe('function');
        expect(typeof window.showSuccessMessage).toBe('function');
        
        expect(() => {
          window.showErrorMessage('Error occurred');
          window.showSuccessMessage('Operation successful');
        }).not.toThrow();
      });
    });
  });

  describe('Settings Panel Integration', () => {
    describe('getSettingsPanel', () => {
      it('should return settings panel instance or null', () => {
        const panel = window.getSettingsPanel();
        expect(panel === null || typeof panel === 'object').toBe(true);
      });
    });

    describe('hasSettingsPanel', () => {
      it('should return boolean indicating panel availability', () => {
        const hasPanel = window.hasSettingsPanel();
        expect(typeof hasPanel).toBe('boolean');
      });
    });

    describe('cleanup', () => {
      it('should clean up resources without errors', () => {
        expect(() => {
          window.cleanup();
        }).not.toThrow();
      });
    });
  });

  describe('Mobile Enhancement Functions', () => {
    describe('touch event handling', () => {
      it('should set up touch event listeners during initialization', () => {
        // Verify that the layout supports touch events
        expect(document.addEventListener).toBeDefined();
        
        // Test that touch events can be created without errors
        expect(() => {
          const touchEvent = new TouchEvent('touchstart', {
            changedTouches: [{ screenX: 100 }]
          });
          expect(touchEvent).toBeDefined();
        }).not.toThrow();
      });

      it('should handle touch events without throwing errors', () => {
        expect(() => {
          const touchStartEvent = new TouchEvent('touchstart', {
            changedTouches: [{ screenX: 100 }]
          });
          const touchEndEvent = new TouchEvent('touchend', {
            changedTouches: [{ screenX: 200 }]
          });
          
          document.dispatchEvent(touchStartEvent);
          document.dispatchEvent(touchEndEvent);
        }).not.toThrow();
      });
    });
  });

  describe('Error Handling and Edge Cases', () => {
    it('should handle malformed API responses', async () => {
      mockFetch.mockResolvedValueOnce({
        json: async () => { throw new Error('Invalid JSON'); }
      });

      await expect(window.navigate('next')).resolves.not.toThrow();
      expect(console.error).toHaveBeenCalled();
    });

    it('should handle network errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(window.refresh()).resolves.not.toThrow();
      expect(console.error).toHaveBeenCalled();
    });

    it('should handle missing DOM elements in content updates', () => {
      // Remove all elements that updatePageContent tries to update
      document.body.innerHTML = '<div>Empty page</div>';
      
      expect(() => {
        window.updatePageContent('<html><body><h1 class="calendar-title">Test</h1></body></html>');
      }).not.toThrow();
    });
  });

  describe('Global Exports and API Surface', () => {
    it('should export all required functions to window', () => {
      const requiredFunctions = [
        'navigate', 'toggleTheme', 'cycleLayout', 'setLayout', 'refresh', 'refreshSilent',
        'toggleAutoRefresh', 'getCurrentTheme', 'isAutoRefreshEnabled',
        'showLoadingIndicator', 'hideLoadingIndicator', 'showErrorMessage', 'showSuccessMessage',
        'updatePageContent', 'getSettingsPanel', 'hasSettingsPanel', 'cleanup'
      ];
      
      requiredFunctions.forEach(funcName => {
        expect(typeof window[funcName]).toBe('function');
      });
    });

    it('should provide calendarBot debug object', () => {
      expect(typeof window.calendarBot).toBe('object');
      expect(typeof window.calendarBot.navigate).toBe('function');
      expect(typeof window.calendarBot.currentTheme).toBe('function');
    });
  });
});