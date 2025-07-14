/**
 * @fileoverview Basic test to verify Jest setup and mocking capabilities
 */

// Mock console methods globally
console.log = jest.fn();
console.warn = jest.fn();
console.error = jest.fn();
console.info = jest.fn();

// Mock fetch globally for all tests
global.fetch = jest.fn();

// Note: window.location.reload mocking handled individually in tests that need it

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock TouchEvent for JSDOM
global.TouchEvent = class TouchEvent extends Event {
  constructor(type, options = {}) {
    super(type, options);
    
    // Always ensure changedTouches is properly structured
    if (options.changedTouches && Array.isArray(options.changedTouches)) {
      this.changedTouches = options.changedTouches;
    } else {
      // Create default touch object with all required properties
      this.changedTouches = [{
        screenX: options.screenX || 0,
        screenY: options.screenY || 0,
        clientX: options.clientX || 0,
        clientY: options.clientY || 0,
        pageX: options.pageX || 0,
        pageY: options.pageY || 0,
        identifier: 0,
        target: options.target || document.body
      }];
    }
    
    this.touches = options.touches || this.changedTouches;
    this.targetTouches = options.targetTouches || this.changedTouches;
  }
};

// Mock touch event properties
global.Touch = class Touch {
  constructor(options = {}) {
    this.identifier = options.identifier || 0;
    this.target = options.target || null;
    this.screenX = options.screenX || 0;
    this.screenY = options.screenY || 0;
    this.clientX = options.clientX || 0;
    this.clientY = options.clientY || 0;
    this.pageX = options.pageX || 0;
    this.pageY = options.pageY || 0;
  }
};

// Create test utilities as a global
global.testUtils = {
  setupMockDOM: (html) => {
    document.body.innerHTML = html;
  },

  cleanupDOM: () => {
    document.body.innerHTML = '';
    document.head.innerHTML = '';
    document.documentElement.className = '';
    // Clear all timers
    jest.clearAllTimers();
    // Clear all mocks
    jest.clearAllMocks();
  },

  createMockElement: (tagName, attributes = {}) => {
    const element = document.createElement(tagName);
    Object.entries(attributes).forEach(([key, value]) => {
      if (key === 'textContent') {
        element.textContent = value;
      } else {
        element.setAttribute(key, value);
      }
    });
    return element;
  },

  triggerEvent: (element, eventType, eventOptions = {}) => {
    const event = new Event(eventType, {
      bubbles: true,
      cancelable: true,
      ...eventOptions
    });
    
    // Add touch-specific properties for touch events
    if (eventType.startsWith('touch')) {
      const touch = new Touch({
        identifier: 0,
        target: element,
        clientX: eventOptions.clientX || 0,
        clientY: eventOptions.clientY || 0,
        screenX: eventOptions.screenX || 0,
        screenY: eventOptions.screenY || 0,
        pageX: eventOptions.pageX || 0,
        pageY: eventOptions.pageY || 0
      });
      
      Object.defineProperty(event, 'touches', {
        value: [touch],
        writable: false
      });
      Object.defineProperty(event, 'targetTouches', {
        value: [touch],
        writable: false
      });
      Object.defineProperty(event, 'changedTouches', {
        value: [touch],
        writable: false
      });
    }
    
    element.dispatchEvent(event);
    return event;
  },

  mockFetchSuccess: (data) => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => data,
      text: async () => JSON.stringify(data),
      status: 200,
      statusText: 'OK'
    });
  },

  mockFetchError: (error) => {
    fetch.mockRejectedValueOnce(error);
  },

  createMockTouch: (options = {}) => {
    return new Touch({
      identifier: options.identifier || 0,
      target: options.target || document.body,
      clientX: options.clientX || 0,
      clientY: options.clientY || 0,
      screenX: options.screenX || 0,
      screenY: options.screenY || 0,
      pageX: options.pageX || 0,
      pageY: options.pageY || 0
    });
  },

  dispatchTouchEvent: (element, type, touches = []) => {
    const touchEvent = new TouchEvent(type, {
      bubbles: true,
      cancelable: true,
      touches: touches,
      targetTouches: touches,
      changedTouches: touches
    });
    
    element.dispatchEvent(touchEvent);
    return touchEvent;
  }
};

describe('Jest Setup and Test Utilities', () => {
  it('should have testUtils available globally', () => {
    expect(testUtils).toBeDefined();
    expect(typeof testUtils.setupMockDOM).toBe('function');
    expect(typeof testUtils.cleanupDOM).toBe('function');
    expect(typeof testUtils.mockFetchSuccess).toBe('function');
    expect(typeof testUtils.mockFetchError).toBe('function');
  });

  it('should have fetch mock available', () => {
    expect(fetch).toBeDefined();
    expect(typeof fetch.mockClear).toBe('function');
  });

  it('should be able to create mock DOM elements', () => {
    testUtils.setupMockDOM('<div id="test">Test content</div>');
    
    const element = document.getElementById('test');
    expect(element).toBeTruthy();
    expect(element.textContent).toBe('Test content');
    
    testUtils.cleanupDOM();
  });

  it('should be able to mock fetch responses', () => {
    testUtils.mockFetchSuccess({ success: true, data: 'test' });
    
    expect(fetch).toHaveBeenCalledTimes(0); // Not called yet
    
    fetch.mockClear();
  });
});