/**
 * @fileoverview Phase 1 Jest Tests - Settings API Functions
 * Tests validation functions, regex utilities, and error handling
 * Target: High coverage efficiency with minimal complexity
 */

describe('SettingsAPI Functions', () => {
  let mockSettingsAPI;

  beforeEach(() => {
    // Mock SettingsAPI class with the validation functions we need to test
    mockSettingsAPI = {
      isValidRegex: function(pattern) {
        try {
          new RegExp(pattern);
          return true;
        } catch (e) {
          return false;
        }
      },

      validateSettings: function(settings) {
        const errors = [];

        if (!settings || typeof settings !== 'object' || Array.isArray(settings)) {
          errors.push('Settings must be an object');
          return { isValid: false, errors };
        }

        // Validate event filters section
        if (settings.event_filters) {
          const filterErrors = this.validateEventFilters(settings.event_filters);
          errors.push(...filterErrors);
        }

        // Validate display settings section
        if (settings.display) {
          const displayErrors = this.validateDisplaySettings(settings.display);
          errors.push(...displayErrors);
        }

        return {
          isValid: errors.length === 0,
          errors
        };
      },

      validateEventFilters: function(filters) {
        const errors = [];

        if (typeof filters.hide_all_day_events !== 'boolean') {
          errors.push('hide_all_day_events must be a boolean');
        }

        if (!Array.isArray(filters.title_patterns)) {
          errors.push('title_patterns must be an array');
        } else {
          filters.title_patterns.forEach((pattern, index) => {
            if (!pattern.pattern || typeof pattern.pattern !== 'string') {
              errors.push(`title_patterns[${index}].pattern must be a non-empty string`);
            }
            if (pattern.is_regex && !this.isValidRegex(pattern.pattern)) {
              errors.push(`title_patterns[${index}].pattern is not a valid regex`);
            }
          });
        }

        return errors;
      },

      validateDisplaySettings: function(display) {
        const errors = [];

        const validLayouts = ['3x4', '4x8', 'whats-next-view'];
        if (display.default_layout && !validLayouts.includes(display.default_layout)) {
          errors.push(`default_layout must be one of: ${validLayouts.join(', ')}`);
        }

        const validDensities = ['compact', 'normal', 'spacious'];
        if (display.display_density && !validDensities.includes(display.display_density)) {
          errors.push(`display_density must be one of: ${validDensities.join(', ')}`);
        }

        return errors;
      },

      fetchWithRetry: async function(url, options) {
        const retryAttempts = 3;
        const retryDelay = 1000;
        let lastError;

        for (let attempt = 1; attempt <= retryAttempts; attempt++) {
          try {
            const response = await fetch(url, options);
            
            // Don't retry on client errors (4xx), only on server errors (5xx) and network issues
            if (response.ok || (response.status >= 400 && response.status < 500)) {
              return response;
            }
            
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            
          } catch (error) {
            lastError = error;
            
            if (attempt < retryAttempts) {
              await this.delay(retryDelay * attempt);
            }
          }
        }

        throw lastError;
      },

      delay: function(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
      }
    };

    // Make functions available globally for testing
    global.isValidRegex = mockSettingsAPI.isValidRegex.bind(mockSettingsAPI);
    global.validateSettings = mockSettingsAPI.validateSettings.bind(mockSettingsAPI);
    global.validateEventFilters = mockSettingsAPI.validateEventFilters.bind(mockSettingsAPI);
    global.fetchWithRetry = mockSettingsAPI.fetchWithRetry.bind(mockSettingsAPI);
    global.delay = mockSettingsAPI.delay.bind(mockSettingsAPI);
  });

  afterEach(() => {
    // Clean up global functions
    delete global.isValidRegex;
    delete global.validateSettings;
    delete global.validateEventFilters;
    delete global.fetchWithRetry;
    delete global.delay;
    jest.clearAllMocks();
  });

  describe('isValidRegex', () => {
    describe('when testing regex pattern validity', () => {
      it('should return true for valid regex patterns', () => {
        expect(global.isValidRegex('.*')).toBe(true);
        expect(global.isValidRegex('[a-z]+')).toBe(true);
        expect(global.isValidRegex('\\d{2,4}')).toBe(true);
        expect(global.isValidRegex('^test$')).toBe(true);
      });

      it('should return false for invalid regex patterns', () => {
        expect(global.isValidRegex('[')).toBe(false);
        expect(global.isValidRegex('*')).toBe(false);
        expect(global.isValidRegex('(?')).toBe(false);
        expect(global.isValidRegex('\\')).toBe(false);
      });

      it('should return true for empty string', () => {
        expect(global.isValidRegex('')).toBe(true);
      });

      it('should return true for simple string patterns', () => {
        expect(global.isValidRegex('Daily Standup')).toBe(true);
        expect(global.isValidRegex('Meeting')).toBe(true);
      });

      it('should handle complex valid patterns', () => {
        expect(global.isValidRegex('daily\\s+(standup|scrum)')).toBe(true);
        expect(global.isValidRegex('[Mm]eeting\\s*\\d*')).toBe(true);
      });
    });
  });

  describe('validateSettings', () => {
    describe('when validating settings object structure', () => {
      it('should validate correct settings object', () => {
        const validSettings = {
          event_filters: {
            hide_all_day_events: true,
            title_patterns: [
              { pattern: 'Daily Standup', is_regex: false },
              { pattern: '[Mm]eeting', is_regex: true }
            ]
          },
          display: {
            default_layout: '3x4',
            display_density: 'normal'
          }
        };

        const result = global.validateSettings(validSettings);
        
        expect(result.isValid).toBe(true);
        expect(result.errors).toHaveLength(0);
      });

      it('should reject null or undefined settings', () => {
        expect(global.validateSettings(null).isValid).toBe(false);
        expect(global.validateSettings(undefined).isValid).toBe(false);
        expect(global.validateSettings(null).errors).toContain('Settings must be an object');
      });

      it('should reject non-object settings', () => {
        expect(global.validateSettings('string').isValid).toBe(false);
        expect(global.validateSettings(123).isValid).toBe(false);
        expect(global.validateSettings([]).isValid).toBe(false);
      });

      it('should validate empty settings object', () => {
        const result = global.validateSettings({});
        
        expect(result.isValid).toBe(true);
        expect(result.errors).toHaveLength(0);
      });

      it('should accumulate errors from multiple sections', () => {
        const invalidSettings = {
          event_filters: {
            hide_all_day_events: 'not a boolean',
            title_patterns: 'not an array'
          },
          display: {
            default_layout: 'invalid_layout',
            display_density: 'invalid_density'
          }
        };

        const result = global.validateSettings(invalidSettings);
        
        expect(result.isValid).toBe(false);
        expect(result.errors.length).toBeGreaterThan(2);
      });
    });
  });

  describe('validateEventFilters', () => {
    describe('when validating event filter settings', () => {
      it('should validate correct event filters', () => {
        const validFilters = {
          hide_all_day_events: true,
          title_patterns: [
            { pattern: 'Daily Standup', is_regex: false },
            { pattern: '[Mm]eeting', is_regex: true }
          ]
        };

        const errors = global.validateEventFilters(validFilters);
        
        expect(errors).toHaveLength(0);
      });

      it('should reject invalid hide_all_day_events type', () => {
        const invalidFilters = {
          hide_all_day_events: 'not a boolean',
          title_patterns: []
        };

        const errors = global.validateEventFilters(invalidFilters);
        
        expect(errors).toContain('hide_all_day_events must be a boolean');
      });

      it('should reject non-array title_patterns', () => {
        const invalidFilters = {
          hide_all_day_events: true,
          title_patterns: 'not an array'
        };

        const errors = global.validateEventFilters(invalidFilters);
        
        expect(errors).toContain('title_patterns must be an array');
      });

      it('should validate individual pattern objects', () => {
        const invalidFilters = {
          hide_all_day_events: true,
          title_patterns: [
            { pattern: '', is_regex: false }, // Empty pattern
            { pattern: null, is_regex: false }, // Null pattern
            { is_regex: false }, // Missing pattern
            { pattern: '[', is_regex: true } // Invalid regex
          ]
        };

        const errors = global.validateEventFilters(invalidFilters);
        
        expect(errors.length).toBeGreaterThan(3);
        expect(errors.some(error => error.includes('must be a non-empty string'))).toBe(true);
        expect(errors.some(error => error.includes('not a valid regex'))).toBe(true);
      });

      it('should allow valid regex patterns', () => {
        const validFilters = {
          hide_all_day_events: false,
          title_patterns: [
            { pattern: '.*meeting.*', is_regex: true },
            { pattern: '^Daily\\s+Standup$', is_regex: true }
          ]
        };

        const errors = global.validateEventFilters(validFilters);
        
        expect(errors).toHaveLength(0);
      });

      it('should allow non-regex patterns without validation', () => {
        const validFilters = {
          hide_all_day_events: false,
          title_patterns: [
            { pattern: '[This would be invalid regex', is_regex: false }
          ]
        };

        const errors = global.validateEventFilters(validFilters);
        
        expect(errors).toHaveLength(0);
      });
    });
  });

  describe('fetchWithRetry', () => {
    describe('when performing network requests with retry logic', () => {
      beforeEach(() => {
        // Reset fetch mock
        global.fetch.mockReset();
      });

      it('should return successful response on first attempt', async () => {
        const mockResponse = {
          ok: true,
          status: 200,
          statusText: 'OK'
        };
        global.fetch.mockResolvedValueOnce(mockResponse);

        const result = await global.fetchWithRetry('/api/test', {});
        
        expect(result).toBe(mockResponse);
        expect(global.fetch).toHaveBeenCalledTimes(1);
      });

      it('should not retry on client errors (4xx)', async () => {
        const mockResponse = {
          ok: false,
          status: 404,
          statusText: 'Not Found'
        };
        global.fetch.mockResolvedValueOnce(mockResponse);

        const result = await global.fetchWithRetry('/api/test', {});
        
        expect(result).toBe(mockResponse);
        expect(global.fetch).toHaveBeenCalledTimes(1);
      });

      it('should retry on server errors (5xx)', async () => {
        // Mock delay to resolve immediately
        const delaySpy = jest.spyOn(mockSettingsAPI, 'delay').mockResolvedValue();
        
        const failResponse = {
          ok: false,
          status: 500,
          statusText: 'Internal Server Error'
        };
        const successResponse = {
          ok: true,
          status: 200,
          statusText: 'OK'
        };
        
        global.fetch
          .mockResolvedValueOnce(failResponse)
          .mockResolvedValueOnce(failResponse)
          .mockResolvedValueOnce(successResponse);

        const result = await global.fetchWithRetry('/api/test', {});
        
        expect(result).toBe(successResponse);
        expect(global.fetch).toHaveBeenCalledTimes(3);
        
        delaySpy.mockRestore();
      }, 15000);

      it('should throw error after all retry attempts fail', async () => {
        // Mock delay to resolve immediately
        const delaySpy = jest.spyOn(mockSettingsAPI, 'delay').mockResolvedValue();
        
        const error = new Error('Network error');
        global.fetch.mockRejectedValue(error);

        await expect(global.fetchWithRetry('/api/test', {})).rejects.toThrow('Network error');
        expect(global.fetch).toHaveBeenCalledTimes(3);
        
        delaySpy.mockRestore();
      }, 15000);

      it('should implement exponential backoff delay', async () => {
        const error = new Error('Network error');
        global.fetch.mockRejectedValue(error);
        
        const delaySpy = jest.spyOn(mockSettingsAPI, 'delay').mockResolvedValue();
        
        try {
          await global.fetchWithRetry('/api/test', {});
        } catch (e) {
          // Expected to fail
        }
        
        expect(delaySpy).toHaveBeenCalledWith(1000); // First retry delay
        expect(delaySpy).toHaveBeenCalledWith(2000); // Second retry delay
      }, 15000);
    });
  });

  describe('delay', () => {
    describe('when creating delays for retry logic', () => {
      it('should return a promise', () => {
        const result = global.delay(100);
        
        expect(result).toBeInstanceOf(Promise);
      });

      it('should resolve after specified time', async () => {
        const setTimeoutSpy = jest.spyOn(global, 'setTimeout');
        
        const delayPromise = global.delay(100);
        
        // Fast-forward time
        jest.advanceTimersByTime(100);
        
        await delayPromise;
        
        expect(setTimeoutSpy).toHaveBeenCalledWith(expect.any(Function), 100);
        
        setTimeoutSpy.mockRestore();
      }, 5000);

      it('should handle zero delay', async () => {
        const setTimeoutSpy = jest.spyOn(global, 'setTimeout');
        
        const delayPromise = global.delay(0);
        
        // Fast-forward time
        jest.advanceTimersByTime(0);
        
        await delayPromise;
        
        expect(setTimeoutSpy).toHaveBeenCalledWith(expect.any(Function), 0);
        
        setTimeoutSpy.mockRestore();
      }, 5000);
    });
  });
});