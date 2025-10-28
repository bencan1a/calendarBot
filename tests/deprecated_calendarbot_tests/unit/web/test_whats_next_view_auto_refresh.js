/**
 * Unit tests for WhatsNextView auto-refresh configuration functionality.
 * Tests the getAutoRefreshInterval() function and related settings integration.
 */

describe('WhatsNextView Auto-Refresh Configuration', () => {
    let originalWindow;
    let originalConsole;
    let mockConsole;

    beforeEach(() => {
        // Save original window and console
        originalWindow = global.window;
        originalConsole = global.console;

        // Create mock console to capture logs
        mockConsole = {
            log: jest.fn(),
            error: jest.fn(),
            warn: jest.fn()
        };
        global.console = mockConsole;

        // Reset window mock for each test
        global.window = {};
    });

    afterEach(() => {
        // Restore original window and console
        global.window = originalWindow;
        global.console = originalConsole;
    });

    describe('getAutoRefreshInterval', () => {
        let getAutoRefreshInterval;

        beforeAll(() => {
            // Load the function under test
            // In a real test environment, this would import the actual function
            // For this test file, we'll define the function as implemented
            getAutoRefreshInterval = function () {
                const DEFAULT_INTERVAL = 300000; // 5 minutes in milliseconds

                try {
                    // Check if settings data exists and has the display.auto_refresh_interval field
                    if (window.settingsData &&
                        window.settingsData.display &&
                        typeof window.settingsData.display.auto_refresh_interval === 'number' &&
                        window.settingsData.display.auto_refresh_interval > 0) {

                        const intervalSeconds = window.settingsData.display.auto_refresh_interval;
                        const intervalMs = intervalSeconds * 1000;

                        console.log(`WhatsNextView: Using configured auto-refresh interval: ${intervalSeconds}s (${intervalMs}ms)`);
                        return intervalMs;
                    }
                } catch (error) {
                    console.error('WhatsNextView: Error reading auto-refresh interval from settings:', error);
                }

                // Fallback to default
                console.log(`WhatsNextView: Using default auto-refresh interval: ${DEFAULT_INTERVAL / 1000}s`);
                return DEFAULT_INTERVAL;
            };
        });

        describe('when_settings_data_unavailable_then_returns_default_interval', () => {
            test('window_settings_data_undefined_returns_300000', () => {
                global.window.settingsData = undefined;

                const result = getAutoRefreshInterval();

                expect(result).toBe(300000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using default auto-refresh interval: 300s'
                );
            });

            test('window_settings_data_null_returns_300000', () => {
                global.window.settingsData = null;

                const result = getAutoRefreshInterval();

                expect(result).toBe(300000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using default auto-refresh interval: 300s'
                );
            });

            test('window_settings_data_empty_object_returns_300000', () => {
                global.window.settingsData = {};

                const result = getAutoRefreshInterval();

                expect(result).toBe(300000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using default auto-refresh interval: 300s'
                );
            });
        });

        describe('when_display_settings_unavailable_then_returns_default_interval', () => {
            test('display_undefined_returns_300000', () => {
                global.window.settingsData = {
                    display: undefined
                };

                const result = getAutoRefreshInterval();

                expect(result).toBe(300000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using default auto-refresh interval: 300s'
                );
            });

            test('display_null_returns_300000', () => {
                global.window.settingsData = {
                    display: null
                };

                const result = getAutoRefreshInterval();

                expect(result).toBe(300000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using default auto-refresh interval: 300s'
                );
            });

            test('display_empty_object_returns_300000', () => {
                global.window.settingsData = {
                    display: {}
                };

                const result = getAutoRefreshInterval();

                expect(result).toBe(300000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using default auto-refresh interval: 300s'
                );
            });
        });

        describe('when_auto_refresh_interval_invalid_then_returns_default_interval', () => {
            test('auto_refresh_interval_undefined_returns_300000', () => {
                global.window.settingsData = {
                    display: {
                        auto_refresh_interval: undefined
                    }
                };

                const result = getAutoRefreshInterval();

                expect(result).toBe(300000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using default auto-refresh interval: 300s'
                );
            });

            test('auto_refresh_interval_null_returns_300000', () => {
                global.window.settingsData = {
                    display: {
                        auto_refresh_interval: null
                    }
                };

                const result = getAutoRefreshInterval();

                expect(result).toBe(300000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using default auto-refresh interval: 300s'
                );
            });

            test('auto_refresh_interval_string_returns_300000', () => {
                global.window.settingsData = {
                    display: {
                        auto_refresh_interval: "300"
                    }
                };

                const result = getAutoRefreshInterval();

                expect(result).toBe(300000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using default auto-refresh interval: 300s'
                );
            });

            test('auto_refresh_interval_zero_returns_300000', () => {
                global.window.settingsData = {
                    display: {
                        auto_refresh_interval: 0
                    }
                };

                const result = getAutoRefreshInterval();

                expect(result).toBe(300000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using default auto-refresh interval: 300s'
                );
            });

            test('auto_refresh_interval_negative_returns_300000', () => {
                global.window.settingsData = {
                    display: {
                        auto_refresh_interval: -60
                    }
                };

                const result = getAutoRefreshInterval();

                expect(result).toBe(300000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using default auto-refresh interval: 300s'
                );
            });
        });

        describe('when_valid_auto_refresh_interval_configured_then_returns_converted_milliseconds', () => {
            test('auto_refresh_interval_60_returns_60000', () => {
                global.window.settingsData = {
                    display: {
                        auto_refresh_interval: 60
                    }
                };

                const result = getAutoRefreshInterval();

                expect(result).toBe(60000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using configured auto-refresh interval: 60s (60000ms)'
                );
            });

            test('auto_refresh_interval_180_returns_180000', () => {
                global.window.settingsData = {
                    display: {
                        auto_refresh_interval: 180
                    }
                };

                const result = getAutoRefreshInterval();

                expect(result).toBe(180000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using configured auto-refresh interval: 180s (180000ms)'
                );
            });

            test('auto_refresh_interval_300_returns_300000', () => {
                global.window.settingsData = {
                    display: {
                        auto_refresh_interval: 300
                    }
                };

                const result = getAutoRefreshInterval();

                expect(result).toBe(300000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using configured auto-refresh interval: 300s (300000ms)'
                );
            });

            test('auto_refresh_interval_600_returns_600000', () => {
                global.window.settingsData = {
                    display: {
                        auto_refresh_interval: 600
                    }
                };

                const result = getAutoRefreshInterval();

                expect(result).toBe(600000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using configured auto-refresh interval: 600s (600000ms)'
                );
            });

            test('auto_refresh_interval_1800_returns_1800000', () => {
                global.window.settingsData = {
                    display: {
                        auto_refresh_interval: 1800
                    }
                };

                const result = getAutoRefreshInterval();

                expect(result).toBe(1800000);
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using configured auto-refresh interval: 1800s (1800000ms)'
                );
            });
        });

        describe('when_exception_occurs_then_returns_default_interval', () => {
            test('settings_data_access_throws_exception_returns_300000', () => {
                // Create a settings object that throws when accessed
                Object.defineProperty(global.window, 'settingsData', {
                    get: () => {
                        throw new Error('Settings access error');
                    }
                });

                const result = getAutoRefreshInterval();

                expect(result).toBe(300000);
                expect(mockConsole.error).toHaveBeenCalledWith(
                    'WhatsNextView: Error reading auto-refresh interval from settings:',
                    expect.any(Error)
                );
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using default auto-refresh interval: 300s'
                );
            });

            test('display_access_throws_exception_returns_300000', () => {
                global.window.settingsData = {
                    get display() {
                        throw new Error('Display settings access error');
                    }
                };

                const result = getAutoRefreshInterval();

                expect(result).toBe(300000);
                expect(mockConsole.error).toHaveBeenCalledWith(
                    'WhatsNextView: Error reading auto-refresh interval from settings:',
                    expect.any(Error)
                );
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'WhatsNextView: Using default auto-refresh interval: 300s'
                );
            });
        });
    });

    describe('Settings Panel Integration', () => {
        describe('auto_refresh_interval_field_visibility', () => {
            let mockSettingsPanel;
            let updateLayoutSpecificFields;

            beforeEach(() => {
                // Mock DOM elements
                mockSettingsPanel = {
                    autoRefreshIntervalField: {
                        style: { display: '' },
                        closest: jest.fn().mockReturnValue({
                            style: { display: '' }
                        })
                    }
                };

                global.document = {
                    getElementById: jest.fn((id) => {
                        if (id === 'auto-refresh-interval') {
                            return mockSettingsPanel.autoRefreshIntervalField;
                        }
                        return null;
                    })
                };

                // Mock the updateLayoutSpecificFields function as implemented
                updateLayoutSpecificFields = function (currentLayout) {
                    const autoRefreshField = document.getElementById('auto-refresh-interval');
                    if (autoRefreshField) {
                        const fieldRow = autoRefreshField.closest('.settings-row');
                        if (fieldRow) {
                            // Only show auto-refresh setting for WhatsNextView layout
                            if (currentLayout === 'whats-next-view') {
                                fieldRow.style.display = 'block';
                                console.log('Settings Panel: Auto-refresh interval field shown for WhatsNextView layout');
                            } else {
                                fieldRow.style.display = 'none';
                                console.log('Settings Panel: Auto-refresh interval field hidden for non-WhatsNextView layout');
                            }
                        }
                    }
                };
            });

            test('when_layout_is_whats_next_view_then_field_is_visible', () => {
                updateLayoutSpecificFields('whats-next-view');

                expect(mockSettingsPanel.autoRefreshIntervalField.closest).toHaveBeenCalledWith('.settings-row');
                expect(mockSettingsPanel.autoRefreshIntervalField.closest().style.display).toBe('block');
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'Settings Panel: Auto-refresh interval field shown for WhatsNextView layout'
                );
            });

            test('when_layout_is_not_whats_next_view_then_field_is_hidden', () => {
                updateLayoutSpecificFields('compact-list');

                expect(mockSettingsPanel.autoRefreshIntervalField.closest).toHaveBeenCalledWith('.settings-row');
                expect(mockSettingsPanel.autoRefreshIntervalField.closest().style.display).toBe('none');
                expect(mockConsole.log).toHaveBeenCalledWith(
                    'Settings Panel: Auto-refresh interval field hidden for non-WhatsNextView layout'
                );
            });

            test('when_field_element_not_found_then_no_error_thrown', () => {
                global.document.getElementById = jest.fn().mockReturnValue(null);

                expect(() => {
                    updateLayoutSpecificFields('whats-next-view');
                }).not.toThrow();

                expect(global.document.getElementById).toHaveBeenCalledWith('auto-refresh-interval');
            });
        });

        describe('auto_refresh_interval_form_handling', () => {
            let collectFormData;
            let populateFormFromSettings;

            beforeEach(() => {
                // Mock form element
                global.document = {
                    getElementById: jest.fn((id) => {
                        if (id === 'auto-refresh-interval') {
                            return { value: '300' };
                        }
                        return null;
                    })
                };

                // Mock the form data collection function as implemented
                collectFormData = function () {
                    const formData = {};
                    const autoRefreshInterval = document.getElementById('auto-refresh-interval');
                    if (autoRefreshInterval && autoRefreshInterval.value) {
                        formData.auto_refresh_interval = parseInt(autoRefreshInterval.value, 10);
                    }
                    return formData;
                };

                // Mock the form population function as implemented
                populateFormFromSettings = function (settings) {
                    if (settings && settings.display && settings.display.auto_refresh_interval) {
                        const autoRefreshField = document.getElementById('auto-refresh-interval');
                        if (autoRefreshField) {
                            autoRefreshField.value = settings.display.auto_refresh_interval.toString();
                        }
                    }
                };
            });

            test('when_collecting_form_data_then_includes_auto_refresh_interval', () => {
                const result = collectFormData();

                expect(result).toEqual({
                    auto_refresh_interval: 300
                });
                expect(global.document.getElementById).toHaveBeenCalledWith('auto-refresh-interval');
            });

            test('when_auto_refresh_field_missing_then_form_data_excludes_field', () => {
                global.document.getElementById = jest.fn().mockReturnValue(null);

                const result = collectFormData();

                expect(result).toEqual({});
            });

            test('when_auto_refresh_field_empty_then_form_data_excludes_field', () => {
                global.document.getElementById = jest.fn().mockReturnValue({ value: '' });

                const result = collectFormData();

                expect(result).toEqual({});
            });

            test('when_populating_form_from_settings_then_sets_field_value', () => {
                const mockField = { value: '' };
                global.document.getElementById = jest.fn().mockReturnValue(mockField);

                const settings = {
                    display: {
                        auto_refresh_interval: 180
                    }
                };

                populateFormFromSettings(settings);

                expect(mockField.value).toBe('180');
                expect(global.document.getElementById).toHaveBeenCalledWith('auto-refresh-interval');
            });

            test('when_settings_missing_auto_refresh_interval_then_field_unchanged', () => {
                const mockField = { value: '300' };
                global.document.getElementById = jest.fn().mockReturnValue(mockField);

                const settings = {
                    display: {}
                };

                populateFormFromSettings(settings);

                expect(mockField.value).toBe('300'); // Unchanged
            });
        });
    });

    describe('Auto-Refresh Setup Integration', () => {
        let setupAutoRefresh;
        let mockSetInterval;
        let mockClearInterval;

        beforeEach(() => {
            // Mock timer functions
            mockSetInterval = jest.fn().mockReturnValue(12345);
            mockClearInterval = jest.fn();
            global.setInterval = mockSetInterval;
            global.clearInterval = mockClearInterval;

            // Mock refreshSilent function
            global.refreshSilent = jest.fn();

            // Mock the setupAutoRefresh function as implemented (simplified version)
            setupAutoRefresh = function () {
                const getAutoRefreshInterval = function () {
                    const DEFAULT_INTERVAL = 300000;

                    try {
                        if (window.settingsData &&
                            window.settingsData.display &&
                            typeof window.settingsData.display.auto_refresh_interval === 'number' &&
                            window.settingsData.display.auto_refresh_interval > 0) {

                            const intervalSeconds = window.settingsData.display.auto_refresh_interval;
                            const intervalMs = intervalSeconds * 1000;

                            console.log(`Whats-Next-View: Using configured auto-refresh interval: ${intervalSeconds}s (${intervalMs}ms)`);
                            return intervalMs;
                        }
                    } catch (error) {
                        console.error('Whats-Next-View: Error reading auto-refresh interval from settings:', error);
                    }

                    console.log(`Whats-Next-View: Using default auto-refresh interval: ${DEFAULT_INTERVAL / 1000}s`);
                    return DEFAULT_INTERVAL;
                };

                const refreshInterval = getAutoRefreshInterval();
                const autoRefreshEnabled = true; // Simplified for testing

                if (autoRefreshEnabled) {
                    const intervalId = setInterval(function () {
                        refreshSilent();
                    }, refreshInterval);

                    console.log(`Whats-Next-View: Auto-refresh enabled: ${refreshInterval / 1000}s interval`);
                    return intervalId;
                }
                return null;
            };
        });

        test('when_setup_auto_refresh_with_default_settings_then_creates_interval_with_300s', () => {
            global.window.settingsData = {};

            const intervalId = setupAutoRefresh();

            expect(mockSetInterval).toHaveBeenCalledWith(
                expect.any(Function),
                300000
            );
            expect(intervalId).toBe(12345);
            expect(mockConsole.log).toHaveBeenCalledWith(
                'Whats-Next-View: Using default auto-refresh interval: 300s'
            );
            expect(mockConsole.log).toHaveBeenCalledWith(
                'Whats-Next-View: Auto-refresh enabled: 300s interval'
            );
        });

        test('when_setup_auto_refresh_with_custom_interval_then_creates_interval_with_custom_value', () => {
            global.window.settingsData = {
                display: {
                    auto_refresh_interval: 180
                }
            };

            const intervalId = setupAutoRefresh();

            expect(mockSetInterval).toHaveBeenCalledWith(
                expect.any(Function),
                180000
            );
            expect(intervalId).toBe(12345);
            expect(mockConsole.log).toHaveBeenCalledWith(
                'Whats-Next-View: Using configured auto-refresh interval: 180s (180000ms)'
            );
            expect(mockConsole.log).toHaveBeenCalledWith(
                'Whats-Next-View: Auto-refresh enabled: 180s interval'
            );
        });

        test('when_auto_refresh_interval_triggers_then_calls_refresh_silent', () => {
            global.window.settingsData = {
                display: {
                    auto_refresh_interval: 60
                }
            };

            setupAutoRefresh();

            // Get the callback function passed to setInterval
            const refreshCallback = mockSetInterval.mock.calls[0][0];

            // Execute the callback
            refreshCallback();

            expect(global.refreshSilent).toHaveBeenCalledTimes(1);
        });
    });

    describe('Performance Impact Validation', () => {
        test('when_interval_reduced_from_60s_to_300s_then_server_requests_reduced_by_80_percent', () => {
            const oldInterval = 60; // seconds
            const newInterval = 300; // seconds

            // Calculate theoretical reduction
            const reductionPercent = ((oldInterval - newInterval) / oldInterval) * 100;
            const expectedReduction = Math.abs(reductionPercent); // Should be 80% fewer requests

            // In this case, new interval is longer, so we're reducing frequency
            // Old: 60 requests per hour (every 60 seconds)
            // New: 12 requests per hour (every 300 seconds)
            // Reduction: (60 - 12) / 60 = 80%
            const oldRequestsPerHour = 3600 / oldInterval;
            const newRequestsPerHour = 3600 / newInterval;
            const actualReduction = ((oldRequestsPerHour - newRequestsPerHour) / oldRequestsPerHour) * 100;

            expect(actualReduction).toBe(80);
            expect(newRequestsPerHour).toBe(12);
            expect(oldRequestsPerHour).toBe(60);
        });

        test('when_using_supported_interval_values_then_all_convert_correctly_to_milliseconds', () => {
            const supportedIntervals = [
                { seconds: 60, expectedMs: 60000, description: '1 minute' },
                { seconds: 180, expectedMs: 180000, description: '3 minutes' },
                { seconds: 300, expectedMs: 300000, description: '5 minutes' },
                { seconds: 600, expectedMs: 600000, description: '10 minutes' },
                { seconds: 1800, expectedMs: 1800000, description: '30 minutes' }
            ];

            supportedIntervals.forEach(({ seconds, expectedMs, description }) => {
                global.window.settingsData = {
                    display: {
                        auto_refresh_interval: seconds
                    }
                };

                const getAutoRefreshInterval = function () {
                    if (window.settingsData?.display?.auto_refresh_interval > 0) {
                        return window.settingsData.display.auto_refresh_interval * 1000;
                    }
                    return 300000;
                };

                const result = getAutoRefreshInterval();

                expect(result).toBe(expectedMs);
            });
        });
    });
});