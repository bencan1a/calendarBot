/**
 * @fileoverview Phase 2 Jest Tests - API Client Methods Integration
 * Tests API integration, network requests, and error handling with comprehensive mocking
 * Target: +20% Coverage focusing on API interactions and state management
 */

// Import the actual SettingsAPI class
const SettingsAPI = require('../../../calendarbot/web/static/shared/js/settings-api.js');

describe('SettingsAPI Integration Tests', () => {
  let settingsAPI;
  let mockDocument;

  beforeEach(() => {
    // Setup DOM mocks using Phase 1 infrastructure
    mockDocument = global.testUtils.setupMockDOM();
    
    // Use real SettingsAPI class
    settingsAPI = new SettingsAPI();
    
    // Mock the delay function to prevent real timeouts during tests
    settingsAPI.delay = jest.fn().mockImplementation(() => Promise.resolve());

    // Mock loadMeetingData function from whats-next-view.js
    global.loadMeetingData = async function() {
      try {
        const requestBody = {};
        const response = await fetch('/api/refresh', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
        });

        const data = await response.json();

        if (data.success && data.html) {
          return {
            success: true,
            data: data,
            error: null
          };
        } else {
          throw new Error('Failed to load meeting data');
        }

      } catch (error) {
        console.error('Failed to load meeting data', error);
        return {
          success: false,
          data: null,
          error: error.message
        };
      }
    };
  });

  afterEach(() => {
    // Clean up global functions and mocks
    delete global.loadMeetingData;
    jest.clearAllMocks();
    
    // Reset fetch mock for next test
    global.fetch.mockClear();
  });

  describe('getSettings API Integration', () => {
    describe('when retrieving settings successfully', () => {
      it('should return settings data on successful API call', async () => {
        const mockSettings = global.testUtils.createMockSettings();
        
        global.fetch.mockResolvedValueOnce(
          global.testUtils.createMockFetchResponse(mockSettings, 200, true)
        );

        const result = await settingsAPI.getSettings();

        expect(result.success).toBe(true);
        expect(result.data).toEqual(mockSettings);
        expect(result.error).toBeNull();
        expect(global.fetch).toHaveBeenCalledWith('/api/settings', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          }
        });
      });

      it('should handle response parsing correctly', async () => {
        const mockSettings = {
          event_filters: {
            hide_all_day_events: true,
            title_patterns: []
          },
          display: {
            default_layout: '3x4'
          }
        };
        
        global.fetch.mockResolvedValueOnce(
          global.testUtils.createMockFetchResponse(mockSettings, 200, true)
        );

        const result = await settingsAPI.getSettings();

        expect(result.success).toBe(true);
        expect(result.data.event_filters.hide_all_day_events).toBe(true);
        expect(result.data.display.default_layout).toBe('3x4');
      });
    });

    describe('when handling API errors', () => {
      it('should handle server error responses gracefully', async () => {
        const errorResponse = { error: 'Internal server error' };
        
        // Mock all 3 retry attempts with the same error response
        global.fetch
          .mockResolvedValueOnce(global.testUtils.createMockFetchResponse(errorResponse, 500, false))
          .mockResolvedValueOnce(global.testUtils.createMockFetchResponse(errorResponse, 500, false))
          .mockResolvedValueOnce(global.testUtils.createMockFetchResponse(errorResponse, 500, false));

        const result = await settingsAPI.getSettings();

        expect(result.success).toBe(false);
        expect(result.data).toBeNull();
        expect(result.error).toContain('HTTP 500');
      });

      it('should handle network errors correctly', async () => {
        // Mock all 3 retry attempts with the same network error
        global.fetch
          .mockRejectedValueOnce(new Error('Network error'))
          .mockRejectedValueOnce(new Error('Network error'))
          .mockRejectedValueOnce(new Error('Network error'));

        const result = await settingsAPI.getSettings();

        expect(result.success).toBe(false);
        expect(result.data).toBeNull();
        expect(result.error).toBe('Network error');
      });

      it('should handle malformed JSON response', async () => {
        const mockResponse = {
          ok: true,
          status: 200,
          json: jest.fn().mockRejectedValueOnce(new Error('Invalid JSON'))
        };
        
        global.fetch.mockResolvedValueOnce(mockResponse);

        const result = await settingsAPI.getSettings();

        expect(result.success).toBe(false);
        expect(result.error).toBe('Invalid JSON');
      });
    });
  });

  describe('updateSettings API Integration', () => {
    describe('when updating settings successfully', () => {
      it('should validate and update settings with valid data', async () => {
        const validSettings = global.testUtils.createMockSettings();
        const updateResponse = { success: true, message: 'Settings updated' };
        
        global.fetch.mockResolvedValueOnce(
          global.testUtils.createMockFetchResponse(updateResponse, 200, true)
        );

        const result = await settingsAPI.updateSettings(validSettings);

        expect(result.success).toBe(true);
        expect(result.data).toEqual(updateResponse);
        expect(global.fetch).toHaveBeenCalledWith('/api/settings', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(validSettings)
        });
      });

      it('should handle settings with complex pattern data', async () => {
        const complexSettings = {
          event_filters: {
            hide_all_day_events: false,
            title_patterns: [
              {
                pattern: 'Daily Standup',
                is_regex: false,
                is_active: true,
                case_sensitive: false,
                match_count: 5
              }
            ]
          },
          display: {
            default_layout: 'whats-next-view',
            display_density: 'compact'
          }
        };
        
        global.fetch.mockResolvedValueOnce(
          global.testUtils.createMockFetchResponse({ success: true }, 200, true)
        );

        const result = await settingsAPI.updateSettings(complexSettings);

        expect(result.success).toBe(true);
        expect(global.fetch).toHaveBeenCalledWith('/api/settings', 
          expect.objectContaining({
            method: 'PUT',
            body: JSON.stringify(complexSettings)
          })
        );
      });
    });

    describe('when handling validation errors', () => {
      it('should reject invalid settings object', async () => {
        const invalidSettings = null;

        const result = await settingsAPI.updateSettings(invalidSettings);

        expect(result.success).toBe(false);
        expect(result.error).toContain('Validation failed');
        expect(global.fetch).not.toHaveBeenCalled();
      });

      it('should reject settings with invalid event filters', async () => {
        const invalidSettings = {
          event_filters: {
            hide_all_day_events: 'not a boolean',
            title_patterns: 'not an array'
          }
        };

        const result = await settingsAPI.updateSettings(invalidSettings);

        expect(result.success).toBe(false);
        expect(result.error).toContain('hide_all_day_events must be a boolean');
        expect(result.error).toContain('title_patterns must be an array');
        expect(global.fetch).not.toHaveBeenCalled();
      });

      it('should reject invalid regex patterns', async () => {
        const invalidSettings = {
          event_filters: {
            hide_all_day_events: true,
            title_patterns: [
              {
                pattern: '[invalid regex',
                is_regex: true,
                is_active: true
              }
            ]
          }
        };

        const result = await settingsAPI.updateSettings(invalidSettings);

        expect(result.success).toBe(false);
        expect(result.error).toContain('not a valid regex');
        expect(global.fetch).not.toHaveBeenCalled();
      });
    });
  });

  describe('resetToDefaults API Integration', () => {
    describe('when resetting settings successfully', () => {
      it('should call reset endpoint and return default settings', async () => {
        const defaultSettings = global.testUtils.createMockSettings({
          event_filters: { hide_all_day_events: false, title_patterns: [] },
          display: { default_layout: '3x4', display_density: 'normal' }
        });
        
        global.fetch.mockResolvedValueOnce(
          global.testUtils.createMockFetchResponse(defaultSettings, 200, true)
        );

        const result = await settingsAPI.resetToDefaults();

        expect(result.success).toBe(true);
        expect(result.data).toEqual(defaultSettings);
        expect(global.fetch).toHaveBeenCalledWith('/api/settings/reset', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          }
        });
      });
    });

    describe('when handling reset errors', () => {
      it('should handle server errors during reset', async () => {
        // Mock all 3 retry attempts with the same error response
        global.fetch
          .mockResolvedValueOnce(global.testUtils.createMockFetchResponse({ error: 'Reset failed' }, 500, false))
          .mockResolvedValueOnce(global.testUtils.createMockFetchResponse({ error: 'Reset failed' }, 500, false))
          .mockResolvedValueOnce(global.testUtils.createMockFetchResponse({ error: 'Reset failed' }, 500, false));

        const result = await settingsAPI.resetToDefaults();

        expect(result.success).toBe(false);
        expect(result.error).toContain('HTTP 500');
      });

      it('should handle network errors during reset', async () => {
        // Mock all 3 retry attempts with the same network error
        global.fetch
          .mockRejectedValueOnce(new Error('Connection timeout'))
          .mockRejectedValueOnce(new Error('Connection timeout'))
          .mockRejectedValueOnce(new Error('Connection timeout'));

        const result = await settingsAPI.resetToDefaults();

        expect(result.success).toBe(false);
        expect(result.error).toBe('Connection timeout');
      });
    });
  });

  describe('exportSettings API Integration', () => {
    describe('when exporting settings successfully', () => {
      it('should retrieve settings for export', async () => {
        const exportData = {
          settings: global.testUtils.createMockSettings(),
          metadata: {
            exported_at: new Date().toISOString(),
            version: '1.0.0'
          }
        };
        
        global.fetch.mockResolvedValueOnce(
          global.testUtils.createMockFetchResponse(exportData, 200, true)
        );

        const result = await settingsAPI.exportSettings();

        expect(result.success).toBe(true);
        expect(result.data).toEqual(exportData);
        expect(global.fetch).toHaveBeenCalledWith('/api/settings/export', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          }
        });
      });

      it('should handle export data with complete settings structure', async () => {
        const fullExportData = {
          settings: {
            event_filters: {
              hide_all_day_events: true,
              title_patterns: [
                { pattern: 'Test', is_regex: false, is_active: true, match_count: 3 }
              ]
            },
            display: {
              default_layout: '4x8',
              display_density: 'spacious'
            },
            metadata: {
              version: '1.0.0',
              created_at: '2023-07-19T10:00:00Z'
            }
          },
          export_metadata: {
            exported_at: '2023-07-19T10:30:00Z',
            format_version: '1.0'
          }
        };
        
        global.fetch.mockResolvedValueOnce(
          global.testUtils.createMockFetchResponse(fullExportData, 200, true)
        );

        const result = await settingsAPI.exportSettings();

        expect(result.success).toBe(true);
        expect(result.data.settings.event_filters.title_patterns).toHaveLength(1);
        expect(result.data.export_metadata).toBeDefined();
      });
    });

    describe('when handling export errors', () => {
      it('should handle export failure gracefully', async () => {
        // Mock all 3 retry attempts with the same error response
        global.fetch
          .mockResolvedValueOnce(global.testUtils.createMockFetchResponse({ error: 'Export failed' }, 500, false))
          .mockResolvedValueOnce(global.testUtils.createMockFetchResponse({ error: 'Export failed' }, 500, false))
          .mockResolvedValueOnce(global.testUtils.createMockFetchResponse({ error: 'Export failed' }, 500, false));

        const result = await settingsAPI.exportSettings();

        expect(result.success).toBe(false);
        expect(result.error).toContain('HTTP 500');
      });
    });
  });

  describe('importSettings API Integration', () => {
    describe('when importing settings successfully', () => {
      it('should import valid settings data', async () => {
        const importData = {
          settings: global.testUtils.createMockSettings(),
          metadata: {
            imported_at: new Date().toISOString()
          }
        };
        const importResponse = { success: true, imported_settings: importData.settings };
        
        global.fetch.mockResolvedValueOnce(
          global.testUtils.createMockFetchResponse(importResponse, 200, true)
        );

        const result = await settingsAPI.importSettings(importData);

        expect(result.success).toBe(true);
        expect(result.data).toEqual(importResponse);
        expect(global.fetch).toHaveBeenCalledWith('/api/settings/import', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(importData)
        });
      });
    });

    describe('when handling import errors', () => {
      it('should handle malformed import data', async () => {
        global.fetch.mockResolvedValueOnce(
          global.testUtils.createMockFetchResponse(
            { error: 'Invalid import format' }, 
            400, 
            false
          )
        );

        const result = await settingsAPI.importSettings({ invalid: 'data' });

        expect(result.success).toBe(false);
        expect(result.error).toContain('Invalid import format');
      });

      it('should handle import processing errors', async () => {
        // Mock all 3 retry attempts with the same processing error
        global.fetch
          .mockRejectedValueOnce(new Error('Processing failed'))
          .mockRejectedValueOnce(new Error('Processing failed'))
          .mockRejectedValueOnce(new Error('Processing failed'));

        const result = await settingsAPI.importSettings({});

        expect(result.success).toBe(false);
        expect(result.error).toBe('Processing failed');
      });
    });
  });

  describe('previewFilterEffects API Integration', () => {
    describe('when previewing filter effects successfully', () => {
      it('should return filter preview data', async () => {
        const filterSettings = {
          hide_all_day_events: true,
          title_patterns: [
            { pattern: 'Meeting', is_regex: false, is_active: true }
          ]
        };
        const previewData = {
          total_events: 50,
          filtered_events: 15,
          remaining_events: 35,
          affected_patterns: [
            { pattern: 'Meeting', matches: 15 }
          ]
        };
        
        global.fetch.mockResolvedValueOnce(
          global.testUtils.createMockFetchResponse(previewData, 200, true)
        );

        const result = await settingsAPI.previewFilterEffects(filterSettings);

        expect(result.success).toBe(true);
        expect(result.data).toEqual(previewData);
        expect(global.fetch).toHaveBeenCalledWith('/api/settings/preview', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(filterSettings)
        });
      });
    });

    describe('when handling preview errors', () => {
      it('should handle preview calculation errors', async () => {
        // Mock all 3 retry attempts with the same error response
        global.fetch
          .mockResolvedValueOnce(global.testUtils.createMockFetchResponse({ error: 'Preview calculation failed' }, 500, false))
          .mockResolvedValueOnce(global.testUtils.createMockFetchResponse({ error: 'Preview calculation failed' }, 500, false))
          .mockResolvedValueOnce(global.testUtils.createMockFetchResponse({ error: 'Preview calculation failed' }, 500, false));

        const result = await settingsAPI.previewFilterEffects({});

        expect(result.success).toBe(false);
        expect(result.error).toContain('HTTP 500');
      });
    });
  });

  describe('loadMeetingData API Integration', () => {
    describe('when loading meeting data successfully', () => {
      it('should fetch and parse meeting data', async () => {
        const meetingData = {
          success: true,
          html: '<div class="current-event"><div class="event-title">Test Meeting</div></div>'
        };
        
        global.fetch.mockResolvedValueOnce(
          global.testUtils.createMockFetchResponse(meetingData, 200, true)
        );

        const result = await global.loadMeetingData();

        expect(result.success).toBe(true);
        expect(result.data).toEqual(meetingData);
        expect(global.fetch).toHaveBeenCalledWith('/api/refresh', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({})
        });
      });
    });

    describe('when handling meeting data errors', () => {
      it('should handle failed meeting data fetch', async () => {
        global.fetch.mockResolvedValueOnce(
          global.testUtils.createMockFetchResponse(
            { success: false, error: 'No meetings found' }, 
            404, 
            false
          )
        );

        const result = await global.loadMeetingData();

        expect(result.success).toBe(false);
        expect(result.error).toBe('Failed to load meeting data');
      });

      it('should handle network errors during meeting data fetch', async () => {
        global.fetch.mockRejectedValueOnce(new Error('Network timeout'));

        const result = await global.loadMeetingData();

        expect(result.success).toBe(false);
        expect(result.error).toBe('Network timeout');
      });
    });
  });

  describe('fetchWithRetry Error Handling', () => {
    describe('when implementing retry logic', () => {
      /**
       * Test retry logic with exponential backoff for server errors
       * This test verifies that the API client properly retries failed requests
       * and implements exponential backoff delay strategy
       */
      it('should retry server errors with exponential backoff', async () => {
        // Mock consecutive failures followed by success
        global.fetch
          .mockRejectedValueOnce(new Error('Server error'))
          .mockRejectedValueOnce(new Error('Server error'))
          .mockResolvedValueOnce(
            global.testUtils.createMockFetchResponse({ success: true }, 200, true)
          );

        // Mock delay function to avoid actual waiting in tests
        const originalDelay = settingsAPI.delay;
        settingsAPI.delay = jest.fn().mockImplementation(() => Promise.resolve());
        
        // Also ensure fetch is properly mocked to avoid hanging
        global.fetch.mockImplementation(() => Promise.reject(new Error('Server error')));

        const result = await settingsAPI.getSettings();

        expect(result.success).toBe(true);
        expect(global.fetch).toHaveBeenCalledTimes(3);
        expect(settingsAPI.delay).toHaveBeenCalledWith(1000); // First retry
        expect(settingsAPI.delay).toHaveBeenCalledWith(2000); // Second retry

        // Restore original delay function
        settingsAPI.delay = originalDelay;
      });

      it('should not retry client errors (4xx)', async () => {
        global.fetch.mockResolvedValueOnce(
          global.testUtils.createMockFetchResponse(
            { error: 'Bad request' }, 
            400, 
            false
          )
        );

        const result = await settingsAPI.getSettings();

        expect(result.success).toBe(false);
        expect(global.fetch).toHaveBeenCalledTimes(1); // No retries for client errors
      });

      it('should throw error after all retries exhausted', async () => {
        global.fetch.mockRejectedValue(new Error('Persistent error'));

        // Mock delay to avoid waiting
        settingsAPI.delay = jest.fn().mockResolvedValue();

        const result = await settingsAPI.getSettings();

        expect(result.success).toBe(false);
        expect(result.error).toBe('Persistent error');
        expect(global.fetch).toHaveBeenCalledTimes(3); // All retry attempts
      });
    });
  });
});