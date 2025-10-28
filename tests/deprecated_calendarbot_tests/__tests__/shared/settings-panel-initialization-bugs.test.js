/**
 * @fileoverview Initialization Bug Detection Tests
 * These tests are designed to FAIL against the current implementation
 * to expose the JavaScript errors that users are experiencing.
 * 
 * Tests cover:
 * - Object initialization state errors
 * - Race conditions between async initialization and form events
 * - Method calls with uninitialized state
 */

const SettingsPanel = require('../../../calendarbot/web/static/shared/js/settings-panel.js');

describe('SettingsPanel Initialization Bug Detection', () => {
  let settingsPanel;
  let mockDocument;

  beforeEach(() => {
    // Setup DOM mocks
    mockDocument = global.testUtils.setupMockDOM();
    
    // Mock dependencies
    global.SettingsAPI = class MockSettingsAPI {
      getSettings() {
        return Promise.resolve({
          success: true,
          data: {
            event_filters: { 
              hide_all_day_events: false,
              title_patterns: []
            },
            display: { default_layout: '3x4' },
            metadata: {}
          }
        });
      }
      
      isValidRegex(pattern) {
        try {
          new RegExp(pattern);
          return true;
        } catch {
          return false;
        }
      }
    };
    
    global.GestureHandler = class MockGestureHandler {
      initialize() {}
      destroy() {}
    };
    
    // Create SettingsPanel with REAL constructor initialization
    // DO NOT pre-populate localSettings - this is the critical bug
    settingsPanel = new SettingsPanel();
    // Verify that localSettings is actually null after constructor
    expect(settingsPanel.localSettings).toBeNull();
  });

  afterEach(() => {
    delete global.SettingsAPI;
    delete global.GestureHandler;
    jest.clearAllMocks();
  });

  describe('collectFormData with null localSettings', () => {
    it('should initialize localSettings and work correctly when localSettings is null', () => {
      // Setup form element
      const toggle = global.testUtils.createMockElement('input', {
        id: 'hide-all-day-events',
        type: 'checkbox',
        checked: true
      });
      
      document.getElementById = jest.fn().mockImplementation((id) => {
        if (id === 'hide-all-day-events') return toggle;
        return null;
      });
      
      // This should now work correctly - the bug is fixed
      expect(() => {
        settingsPanel.collectFormData();
      }).not.toThrow();
      
      // Verify proper initialization occurred
      expect(settingsPanel.localSettings).toBeDefined();
      expect(settingsPanel.localSettings.event_filters).toBeDefined();
      expect(settingsPanel.localSettings.event_filters.hide_all_day_events).toBe(true);
    });

    it('should handle incomplete fallback structure gracefully', () => {
      // Set up the incomplete fallback scenario that used to cause problems
      settingsPanel.localSettings = {
        event_filters: { title_patterns: [] }, // Missing hide_all_day_events!
        display: {},
        metadata: {}
      };
      
      const toggle = global.testUtils.createMockElement('input', {
        id: 'hide-all-day-events',
        type: 'checkbox',
        checked: true
      });
      
      document.getElementById = jest.fn().mockImplementation((id) => {
        if (id === 'hide-all-day-events') return toggle;
        return null;
      });
      
      // This should now work correctly - defensive programming added
      expect(() => {
        settingsPanel.collectFormData();
      }).not.toThrow();
      
      // Verify the property was set correctly
      expect(settingsPanel.localSettings.event_filters.hide_all_day_events).toBe(true);
    });
  });

  describe('addTitlePattern with uninitialized state', () => {
    it('should initialize localSettings and work correctly when localSettings is null', () => {
      // Verify localSettings is null (real constructor state)
      expect(settingsPanel.localSettings).toBeNull();
      
      // This should now work correctly - the bug is fixed
      expect(() => {
        settingsPanel.addTitlePattern('Daily Standup');
      }).not.toThrow();
      
      // Verify proper initialization occurred
      expect(settingsPanel.localSettings).toBeDefined();
      expect(settingsPanel.localSettings.event_filters).toBeDefined();
      expect(settingsPanel.localSettings.event_filters.title_patterns).toHaveLength(1);
      expect(settingsPanel.localSettings.event_filters.title_patterns[0].pattern).toBe('Daily Standup');
    });

    it('should initialize event_filters when missing', () => {
      // Set up scenario where localSettings exists but event_filters doesn't
      settingsPanel.localSettings = {
        display: {},
        metadata: {}
        // Missing event_filters!
      };
      
      // This should now work correctly - defensive programming added
      expect(() => {
        settingsPanel.addTitlePattern('Meeting');
      }).not.toThrow();
      
      // Verify event_filters was properly initialized
      expect(settingsPanel.localSettings.event_filters).toBeDefined();
      expect(settingsPanel.localSettings.event_filters.title_patterns).toHaveLength(1);
      expect(settingsPanel.localSettings.event_filters.title_patterns[0].pattern).toBe('Meeting');
    });

    it('should initialize title_patterns when missing', () => {
      // Set up scenario where event_filters exists but title_patterns doesn't
      settingsPanel.localSettings = {
        event_filters: {
          hide_all_day_events: false
          // Missing title_patterns!
        },
        display: {},
        metadata: {}
      };
      
      // This should now work correctly - defensive programming added
      expect(() => {
        settingsPanel.addTitlePattern('Scrum');
      }).not.toThrow();
      
      // Verify title_patterns was properly initialized
      expect(settingsPanel.localSettings.event_filters.title_patterns).toHaveLength(1);
      expect(settingsPanel.localSettings.event_filters.title_patterns[0].pattern).toBe('Scrum');
    });
  });

  describe('onSettingChange race condition', () => {
    it('should handle form changes gracefully even before initialization completes', () => {
      // Simulate the race condition where form events fire before loadSettings() completes
      // This is the real-world scenario that was causing the reported errors
      
      const toggle = global.testUtils.createMockElement('input', {
        id: 'hide-all-day-events',
        type: 'checkbox',
        checked: true
      });
      
      document.getElementById = jest.fn().mockImplementation((id) => {
        if (id === 'hide-all-day-events') return toggle;
        return null;
      });
      
      // localSettings is still null because initialization hasn't completed
      expect(settingsPanel.localSettings).toBeNull();
      
      // This should now work correctly - defensive programming added
      expect(() => {
        settingsPanel.onSettingChange(); // This calls collectFormData()
      }).not.toThrow();
      
      // Verify proper initialization occurred
      expect(settingsPanel.localSettings).toBeDefined();
      expect(settingsPanel.localSettings.event_filters.hide_all_day_events).toBe(true);
    });
  });

  describe('method calls during initialization window', () => {
    it('should handle methods correctly when called immediately after constructor', () => {
      // This tests the critical initialization window where:
      // 1. Constructor has run (localSettings = null)
      // 2. initialize() hasn't completed yet
      // 3. User interactions can trigger method calls
      
      // Verify we're in the initialization window
      expect(settingsPanel.localSettings).toBeNull();
      expect(settingsPanel.currentSettings).toBeNull();
      
      // These method calls should now work correctly - bugs fixed
      expect(() => {
        settingsPanel.addTitlePattern('Test Pattern');
      }).not.toThrow();
      
      const toggle = global.testUtils.createMockElement('input', {
        id: 'hide-all-day-events',
        type: 'checkbox',
        checked: true
      });
      
      document.getElementById = jest.fn().mockReturnValue(toggle);
      
      expect(() => {
        settingsPanel.collectFormData();
      }).not.toThrow();
      
      // Verify both methods properly initialized localSettings
      expect(settingsPanel.localSettings).toBeDefined();
      expect(settingsPanel.localSettings.event_filters).toBeDefined();
    });
  });

  describe('form interaction before loadSettings completes', () => {
    it('should handle user clicking add pattern button during initialization', async () => {
      // Simulate user clicking "Add Pattern" button while loadSettings is still pending
      // This is a common real-world scenario that should now work
      
      // Start async initialization but don't await it
      const initPromise = settingsPanel.initialize();
      
      // User tries to add pattern while initialization is still pending - should now work
      expect(() => {
        settingsPanel.addTitlePattern('Quick Pattern');
      }).not.toThrow();
      
      // Verify the pattern was added
      expect(settingsPanel.localSettings.event_filters.title_patterns).toHaveLength(1);
      expect(settingsPanel.localSettings.event_filters.title_patterns[0].pattern).toBe('Quick Pattern');
      
      // Clean up the pending promise
      await initPromise.catch(() => {}); // Ignore any errors from incomplete test setup
    });

    it('should handle user changing toggle during initialization', async () => {
      // Simulate user changing a toggle while loadSettings is still pending
      
      const toggle = global.testUtils.createMockElement('input', {
        id: 'hide-all-day-events',
        type: 'checkbox',
        checked: true
      });
      
      document.getElementById = jest.fn().mockReturnValue(toggle);
      
      // Start async initialization but don't await it
      const initPromise = settingsPanel.initialize();
      
      // User changes toggle while initialization is still pending - should now work
      expect(() => {
        settingsPanel.onSettingChange(); // This calls collectFormData()
      }).not.toThrow();
      
      // Verify the setting was captured
      expect(settingsPanel.localSettings.event_filters.hide_all_day_events).toBe(true);
      
      // Clean up the pending promise
      await initPromise.catch(() => {}); // Ignore any errors from incomplete test setup
    });
  });

  describe('defensive programming validation', () => {
    it('should handle collectFormData with proper null checks', () => {
      // Test that the implementation now has proper defensive programming
      
      const toggle = global.testUtils.createMockElement('input', {
        id: 'hide-all-day-events',
        type: 'checkbox',
        checked: true
      });
      
      document.getElementById = jest.fn().mockReturnValue(toggle);
      
      // Should now work correctly with defensive programming
      expect(() => {
        settingsPanel.collectFormData();
      }).not.toThrow();
      
      expect(settingsPanel.localSettings).toBeDefined();
      expect(settingsPanel.localSettings.event_filters.hide_all_day_events).toBe(true);
    });

    it('should handle addTitlePattern with proper null checks', () => {
      // Test that the implementation now has proper defensive programming
      
      // Should now work correctly with defensive programming
      expect(() => {
        settingsPanel.addTitlePattern('Test');
      }).not.toThrow();
      
      expect(settingsPanel.localSettings).toBeDefined();
      expect(settingsPanel.localSettings.event_filters.title_patterns).toHaveLength(1);
      expect(settingsPanel.localSettings.event_filters.title_patterns[0].pattern).toBe('Test');
    });
  });
});