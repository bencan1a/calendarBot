/**
 * Jest setup file for CalendarBot frontend tests
 * Simplified configuration focusing on essential mocks and cleanup
 */

// Essential polyfills for Node.js environment
global.TextEncoder = require('util').TextEncoder;
global.TextDecoder = require('util').TextDecoder;

// Essential global mocks
global.fetch = jest.fn();

// Basic window properties for layout calculations
window.innerWidth = 1024;
window.innerHeight = 768;

// Simplified DOMParser mock for XML/HTML parsing
global.DOMParser = jest.fn(() => ({
  parseFromString: jest.fn((str, type) => {
    const mockDocument = {
      querySelector: jest.fn(),
      querySelectorAll: jest.fn(() => []),
      getElementById: jest.fn(),
      getElementsByClassName: jest.fn(() => []),
      createElement: jest.fn(() => ({
        textContent: '',
        innerHTML: '',
        setAttribute: jest.fn(),
        getAttribute: jest.fn(),
        classList: {
          add: jest.fn(),
          remove: jest.fn(),
          contains: jest.fn(() => false)
        }
      })),
      title: 'Test Document'
    };
    return mockDocument;
  })
}));

// Modern timer implementation
jest.useFakeTimers('modern');

// Essential test utilities (minimal set)
global.testUtils = {
  // Setup mock DOM structure for testing
  setupMockDOM: (html = '') => {
    document.body.innerHTML = html;
    
    // Mock common DOM methods
    document.querySelector = jest.fn((selector) => {
      return document.body.querySelector(selector);
    });
    
    document.querySelectorAll = jest.fn((selector) => {
      return document.body.querySelectorAll(selector);
    });
    
    document.getElementById = jest.fn((id) => {
      return document.body.querySelector(`#${id}`);
    });
    
    return {
      body: document.body,
      querySelector: document.querySelector,
      querySelectorAll: document.querySelectorAll,
      getElementById: document.getElementById
    };
  },

  // Create a mock DOM element with specified properties
  createMockElement: (tagName = 'div', props = {}) => {
    const element = document.createElement(tagName);
    Object.assign(element, props);
    
    // Mock common methods
    element.querySelector = jest.fn();
    element.querySelectorAll = jest.fn(() => []);
    element.getAttribute = jest.fn();
    element.setAttribute = jest.fn();
    element.appendChild = jest.fn();
    element.remove = jest.fn();
    element.click = jest.fn();
    element.focus = jest.fn();
    element.addEventListener = jest.fn();
    element.removeEventListener = jest.fn();
    element.dispatchEvent = jest.fn();
    
    return element;
  },

  // Create basic mock fetch response
  createMockFetchResponse: (data, status = 200, ok = true) => {
    return Promise.resolve({
      ok,
      status,
      statusText: ok ? 'OK' : 'Error',
      json: () => Promise.resolve(data),
      text: () => Promise.resolve(JSON.stringify(data))
    });
  },

  // Create mock localStorage implementation
  createMockLocalStorage: () => {
    const storage = {};
    return {
      getItem: jest.fn((key) => storage[key] || null),
      setItem: jest.fn((key, value) => {
        storage[key] = String(value);
      }),
      removeItem: jest.fn((key) => {
        delete storage[key];
      }),
      clear: jest.fn(() => {
        Object.keys(storage).forEach(key => delete storage[key]);
      }),
      key: jest.fn((index) => Object.keys(storage)[index] || null),
      get length() {
        return Object.keys(storage).length;
      },
      _getStorage: () => ({ ...storage })
    };
  },

  // Create mock meeting data
  createMockMeeting: (overrides = {}) => {
    const now = new Date();
    const startTime = new Date(now.getTime() + 30 * 60 * 1000);
    const endTime = new Date(startTime.getTime() + 60 * 60 * 1000);
    
    return {
      id: 'test-meeting-123',
      title: 'Test Meeting',
      start_time: startTime.toISOString(),
      end_time: endTime.toISOString(),
      location: 'Conference Room A',
      description: 'Test meeting description',
      ...overrides
    };
  },

  // Create mock settings data
  createMockSettings: (overrides = {}) => {
    return {
      event_filters: {
        hide_all_day_events: false,
        title_patterns: [{
          pattern: 'Daily Standup',
          is_regex: false,
          is_active: true,
          case_sensitive: false,
          match_count: 5,
          description: null
        }]
      },
      display: {
        default_layout: '3x4',
        display_density: 'normal'
      },
      metadata: {
        version: '1.0.0',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      },
      ...overrides
    };
  },

  // Create comprehensive test data suite for integration tests
  createTestDataSuite: () => {
    return {
      settings: global.testUtils.createMockSettings(),
      meetings: [global.testUtils.createMockMeeting()],
      events: [global.testUtils.createMockMeeting()],
      localStorage: global.testUtils.createMockLocalStorage(),
      
      // Mock timers with timer management
      timers: {
        activeTimers: new Map(),
        timerIdCounter: 1,
        
        createCountdown: jest.fn(function(endTime, callback) {
          const timerId = this.timerIdCounter++;
          const timer = {
            id: timerId,
            endTime,
            callback,
            isActive: true
          };
          this.activeTimers.set(timerId, timer);
          return timerId;
        }),
        
        stopCountdown: jest.fn(function(timerId) {
          if (this.activeTimers.has(timerId)) {
            const timer = this.activeTimers.get(timerId);
            timer.isActive = false;
            this.activeTimers.delete(timerId);
          }
        }),
        
        stopAllTimers: jest.fn(function() {
          this.activeTimers.clear();
        }),
        
        getActiveTimerCount: jest.fn(function() {
          return this.activeTimers.size;
        })
      },
      
      // Mock API client
      apiClient: {
        getSettings: jest.fn().mockResolvedValue({
          success: true,
          data: global.testUtils.createMockSettings()
        }),
        
        updateSettings: jest.fn().mockResolvedValue({
          success: true,
          data: { message: 'Settings updated successfully' }
        })
      },
      
      // Mock navigation
      navigation: {
        currentView: 'main',
        history: ['main'],
        
        navigate: jest.fn(function(target) {
          if (target && typeof target === 'string') {
            this.history.push(this.currentView);
            this.currentView = target;
            return true;
          }
          return false;
        })
      },
      
      // Mock theme manager
      themeManager: {
        currentTheme: 'light',
        availableThemes: ['light', 'dark'],
        
        setTheme: jest.fn(function(theme) {
          if (this.availableThemes.includes(theme)) {
            this.currentTheme = theme;
            return true;
          }
          return false;
        }),
        
        toggleTheme: jest.fn(function() {
          const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
          this.setTheme(newTheme);
          return newTheme;
        })
      }
    };
  }
};

// Essential cleanup after each test
afterEach(() => {
  // Clear all mocks
  jest.clearAllMocks();
  
  // Clear timers
  jest.clearAllTimers();
  
  // Reset DOM
  document.body.innerHTML = '';
  document.head.innerHTML = '';
  
  // Clear global test state (preserve testUtils)
  Object.keys(global).forEach(key => {
    if (key.startsWith('test') && key !== 'testUtils') {
      delete global[key];
    }
  });
});

// Global error handler for unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

console.log('Jest setup complete - Simplified test environment ready');