/**
 * @fileoverview Phase 1 Jest Tests - Settings Panel Functions
 * Tests form handling, data collection, pattern management utilities
 * Target: High coverage efficiency with minimal complexity - pure functions only
 */

// Import the actual SettingsPanel class for real testing
const SettingsPanel = require('../../../calendarbot/web/static/shared/js/settings-panel.js');

describe('SettingsPanel Functions', () => {
  let mockDocument;
  let settingsPanel;

  beforeEach(() => {
    // Setup DOM mocks
    mockDocument = global.testUtils.setupMockDOM();

    // Create SettingsPanel instance for testing
    // Mock the dependencies it needs
    global.SettingsAPI = class MockSettingsAPI {
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

    settingsPanel = new SettingsPanel();
    settingsPanel.localSettings = {
      event_filters: { title_patterns: [] },
      display: {},
      metadata: {}
    };
  });

  afterEach(() => {
    // Clean up
    delete global.SettingsAPI;
    delete global.GestureHandler;
    jest.clearAllMocks();
  });

  describe('collectFormData', () => {
    describe('when collecting form data into settings object', () => {
      it('should collect all-day events toggle', () => {
        const toggle = global.testUtils.createMockElement('input', {
          id: 'hide-all-day-events',
          type: 'checkbox',
          checked: true
        });

        document.getElementById = jest.fn().mockImplementation((id) => {
          if (id === 'hide-all-day-events') return toggle;
          return null;
        });

        settingsPanel.collectFormData();

        expect(settingsPanel.localSettings.event_filters.hide_all_day_events).toBe(true);
      });

      it('should collect selected layout', () => {
        const radio = global.testUtils.createMockElement('input', {
          type: 'radio',
          name: 'default-layout',
          value: '3x4',
          checked: true
        });

        document.querySelector = jest.fn().mockImplementation((selector) => {
          if (selector === 'input[name="default-layout"]:checked') return radio;
          return null;
        });

        settingsPanel.collectFormData();

        expect(settingsPanel.localSettings.display.default_layout).toBe('3x4');
      });

      it('should collect display density', () => {
        const select = global.testUtils.createMockElement('select', {
          id: 'display-density'
        });
        // Ensure value property works correctly
        Object.defineProperty(select, 'value', {
          value: 'compact',
          writable: true,
          configurable: true
        });

        document.getElementById = jest.fn().mockImplementation((id) => {
          if (id === 'display-density') return select;
          return null;
        });

        settingsPanel.collectFormData();

        expect(settingsPanel.localSettings.display.display_density).toBe('compact');
      });

      it('should handle missing form elements gracefully', () => {
        document.getElementById = jest.fn().mockReturnValue(null);
        document.querySelector = jest.fn().mockReturnValue(null);

        settingsPanel.collectFormData();

        expect(settingsPanel.localSettings).toHaveProperty('event_filters');
        expect(settingsPanel.localSettings).toHaveProperty('display');
        expect(settingsPanel.localSettings).toHaveProperty('metadata');
      });

      it('should return properly structured settings object', () => {
        settingsPanel.collectFormData();

        expect(settingsPanel.localSettings).toHaveProperty('event_filters.title_patterns');
        expect(Array.isArray(settingsPanel.localSettings.event_filters.title_patterns)).toBe(true);
        expect(settingsPanel.localSettings).toHaveProperty('display');
        expect(settingsPanel.localSettings).toHaveProperty('metadata');
      });
    });
  });

  describe('populateForm', () => {
    describe('when populating form with settings data', () => {
      it('should populate all-day events toggle', () => {
        const toggle = global.testUtils.createMockElement('input', {
          id: 'hide-all-day-events',
          type: 'checkbox',
          checked: false
        });

        document.getElementById = jest.fn().mockImplementation((id) => {
          if (id === 'hide-all-day-events') return toggle;
          return null;
        });

        const settings = {
          event_filters: {
            hide_all_day_events: true
          }
        };

        settingsPanel.populateForm(settings);

        expect(toggle.checked).toBe(true);
      });

      it('should populate default layout radio', () => {
        const radio = global.testUtils.createMockElement('input', {
          type: 'radio',
          name: 'default-layout',
          value: '4x8',
          checked: false
        });

        document.querySelector = jest.fn().mockImplementation((selector) => {
          if (selector === 'input[name="default-layout"][value="4x8"]') return radio;
          return null;
        });

        const settings = {
          display: {
            default_layout: '4x8'
          }
        };

        settingsPanel.populateForm(settings);

        expect(radio.checked).toBe(true);
      });

      it('should populate display density select', () => {
        const select = global.testUtils.createMockElement('select', {
          id: 'display-density'
        });
        // Create value property that can be set
        Object.defineProperty(select, 'value', {
          value: 'normal',
          writable: true,
          configurable: true
        });

        document.getElementById = jest.fn().mockImplementation((id) => {
          if (id === 'display-density') return select;
          return null;
        });

        const settings = {
          display: {
            display_density: 'spacious'
          }
        };

        settingsPanel.populateForm(settings);

        expect(select.value).toBe('spacious');
      });

      it('should handle null settings gracefully', () => {
        expect(() => {
          settingsPanel.populateForm(null);
        }).not.toThrow();
      });

      it('should handle missing form elements gracefully', () => {
        document.getElementById = jest.fn().mockReturnValue(null);
        document.querySelector = jest.fn().mockReturnValue(null);

        const settings = {
          event_filters: { hide_all_day_events: true },
          display: { default_layout: '3x4', display_density: 'compact' }
        };

        expect(() => {
          settingsPanel.populateForm(settings);
        }).not.toThrow();
      });
    });
  });

  describe('renderPatternList', () => {
    describe('when rendering filter pattern list', () => {
      it('should render patterns correctly', () => {
        const container = global.testUtils.createMockElement('div', {
          id: 'pattern-list',
          innerHTML: ''
        });

        document.getElementById = jest.fn().mockReturnValue(container);

        const patterns = [
          {
            pattern: 'Daily Standup',
            is_regex: false,
            is_active: true,
            match_count: 5
          },
          {
            pattern: '[Mm]eeting',
            is_regex: true,
            is_active: false,
            match_count: 3
          }
        ];

        settingsPanel.renderPatternList(patterns);

        expect(container.innerHTML).toContain('Daily Standup');
        expect(container.innerHTML).toContain('[Mm]eeting');
        expect(container.innerHTML).toContain('Regex');
        expect(container.innerHTML).toContain('5 events filtered');
      });

      it('should show empty state for no patterns', () => {
        const container = global.testUtils.createMockElement('div', {
          id: 'pattern-list',
          innerHTML: ''
        });

        document.getElementById = jest.fn().mockReturnValue(container);

        settingsPanel.renderPatternList([]);

        expect(container.innerHTML).toContain('No patterns configured');
      });

      it('should handle null patterns', () => {
        const container = global.testUtils.createMockElement('div', {
          id: 'pattern-list',
          innerHTML: ''
        });

        document.getElementById = jest.fn().mockReturnValue(container);

        settingsPanel.renderPatternList(null);

        expect(container.innerHTML).toContain('No patterns configured');
      });

      it('should handle missing container gracefully', () => {
        document.getElementById = jest.fn().mockReturnValue(null);

        expect(() => {
          settingsPanel.renderPatternList([{pattern: 'test', is_regex: false, is_active: true}]);
        }).not.toThrow();
      });

      it('should escape HTML in pattern text', () => {
        const container = global.testUtils.createMockElement('div', {
          id: 'pattern-list',
          innerHTML: ''
        });

        document.getElementById = jest.fn().mockReturnValue(container);

        const patterns = [
          {
            pattern: '<script>alert("xss")</script>',
            is_regex: false,
            is_active: true,
            match_count: 0
          }
        ];

        settingsPanel.renderPatternList(patterns);

        expect(container.innerHTML).toContain('&lt;script&gt;');
        expect(container.innerHTML).not.toContain('<script>');
      });
    });
  });

  describe('detectScreenSize', () => {
    describe('when detecting screen size category', () => {
      it('should detect compact screen size', () => {
        Object.defineProperty(window, 'innerWidth', { value: 320, writable: true });
        Object.defineProperty(window, 'innerHeight', { value: 420, writable: true });

        const result = settingsPanel.detectScreenSize();

        expect(result).toBe('compact');
      });

      it('should detect medium screen size', () => {
        Object.defineProperty(window, 'innerWidth', { value: 480, writable: true });
        Object.defineProperty(window, 'innerHeight', { value: 800, writable: true });

        const result = settingsPanel.detectScreenSize();

        expect(result).toBe('medium');
      });

      it('should detect large screen size', () => {
        Object.defineProperty(window, 'innerWidth', { value: 1024, writable: true });
        Object.defineProperty(window, 'innerHeight', { value: 768, writable: true });

        const result = settingsPanel.detectScreenSize();

        expect(result).toBe('large');
      });

      it('should default to medium for unmatched sizes', () => {
        Object.defineProperty(window, 'innerWidth', { value: 600, writable: true });
        Object.defineProperty(window, 'innerHeight', { value: 600, writable: true });

        const result = settingsPanel.detectScreenSize();

        expect(result).toBe('medium');
      });
    });
  });
});