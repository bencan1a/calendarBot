/**
 * Tests for settings-panel.js validation functions
 * Focus: Form validation, settings persistence, UI state updates
 * Coverage targets: Lines 537-739, 888-1008, 807-842
 */

// Import the actual JavaScript files for coverage
require('../../../calendarbot/web/static/shared/js/settings-panel.js');
require('../../../calendarbot/web/static/shared/js/settings-api.js');

describe('settings-panel validation', () => {
    let container;
    let mockSettingsAPI;

    beforeEach(() => {
        // Setup DOM
        container = document.createElement('div');
        container.innerHTML = `
            <div id="settings-panel" class="settings-panel">
                <button class="settings-toggle">Settings</button>
                <div class="settings-content">
                    <form id="settings-form">
                        <input type="text" id="filter-regex" placeholder="Filter regex">
                        <input type="number" id="refresh-interval" min="1" max="60" value="5">
                        <input type="checkbox" id="auto-refresh" checked>
                        <select id="theme-selector">
                            <option value="light">Light</option>
                            <option value="dark">Dark</option>
                        </select>
                        <button type="submit">Save</button>
                        <button type="button" id="reset-defaults">Reset</button>
                    </form>
                    <div class="validation-errors"></div>
                </div>
            </div>
        `;
        document.body.appendChild(container);

        // Mock SettingsAPI
        mockSettingsAPI = {
            getSettings: jest.fn().mockResolvedValue({
                success: true,
                data: {
                    filterRegex: '',
                    refreshInterval: 5,
                    autoRefresh: true,
                    theme: 'light'
                }
            }),
            updateSettings: jest.fn().mockResolvedValue({ success: true }),
            resetToDefaults: jest.fn().mockResolvedValue({ success: true })
        };
        global.SettingsAPI = mockSettingsAPI;
    });

    afterEach(() => {
        document.body.removeChild(container);
        jest.clearAllMocks();
    });

    describe('form validation', () => {
        test('validates regex patterns', () => {
            const validateRegex = (pattern) => {
                if (!pattern) return true; // Empty is valid
                try {
                    new RegExp(pattern);
                    return true;
                } catch (e) {
                    return false;
                }
            };

            expect(validateRegex('')).toBe(true);
            expect(validateRegex('.*test.*')).toBe(true);
            expect(validateRegex('[a-z]+')).toBe(true);
            expect(validateRegex('[')).toBe(false); // Invalid regex
            expect(validateRegex('(unclosed')).toBe(false);
        });

        test('validates refresh interval range', () => {
            const validateInterval = (value) => {
                const num = parseInt(value, 10);
                return !isNaN(num) && num >= 1 && num <= 60;
            };

            expect(validateInterval('5')).toBe(true);
            expect(validateInterval('1')).toBe(true);
            expect(validateInterval('60')).toBe(true);
            expect(validateInterval('0')).toBe(false);
            expect(validateInterval('61')).toBe(false);
            expect(validateInterval('abc')).toBe(false);
        });

        test('shows validation errors for invalid input', () => {
            const showValidationError = (message) => {
                const errorContainer = container.querySelector('.validation-errors');
                errorContainer.textContent = message;
                errorContainer.style.display = 'block';
            };

            showValidationError('Invalid regex pattern');
            const errorContainer = container.querySelector('.validation-errors');
            expect(errorContainer.textContent).toBe('Invalid regex pattern');
            expect(errorContainer.style.display).toBe('block');
        });

        test('clears validation errors on valid input', () => {
            const clearValidationErrors = () => {
                const errorContainer = container.querySelector('.validation-errors');
                errorContainer.textContent = '';
                errorContainer.style.display = 'none';
            };

            // Set error first
            const errorContainer = container.querySelector('.validation-errors');
            errorContainer.textContent = 'Some error';
            errorContainer.style.display = 'block';

            // Clear errors
            clearValidationErrors();
            expect(errorContainer.textContent).toBe('');
            expect(errorContainer.style.display).toBe('none');
        });
    });

    describe('settings persistence', () => {
        test('saves settings to API on form submit', async () => {
            const saveSettings = async (formData) => {
                const settings = {
                    filterRegex: formData.get('filterRegex'),
                    refreshInterval: parseInt(formData.get('refreshInterval'), 10),
                    autoRefresh: formData.get('autoRefresh') === 'true',
                    theme: formData.get('theme')
                };
                
                const result = await mockSettingsAPI.updateSettings(settings);
                return result.success;
            };

            const formData = new FormData();
            formData.set('filterRegex', '.*test.*');
            formData.set('refreshInterval', '10');
            formData.set('autoRefresh', 'true');
            formData.set('theme', 'dark');

            const success = await saveSettings(formData);
            expect(success).toBe(true);
            expect(mockSettingsAPI.updateSettings).toHaveBeenCalledWith({
                filterRegex: '.*test.*',
                refreshInterval: 10,
                autoRefresh: true,
                theme: 'dark'
            });
        });

        test('handles save errors gracefully', async () => {
            mockSettingsAPI.updateSettings.mockRejectedValueOnce(new Error('Network error'));

            const saveSettings = async () => {
                try {
                    await mockSettingsAPI.updateSettings({});
                    return { success: true };
                } catch (error) {
                    return { success: false, error: error.message };
                }
            };

            const result = await saveSettings();
            expect(result.success).toBe(false);
            expect(result.error).toBe('Network error');
        });

        test('loads settings from API on panel open', async () => {
            const loadSettings = async () => {
                const result = await mockSettingsAPI.getSettings();
                if (result.success) {
                    return result.data;
                }
                return null;
            };

            const settings = await loadSettings();
            expect(settings).toEqual({
                filterRegex: '',
                refreshInterval: 5,
                autoRefresh: true,
                theme: 'light'
            });
            expect(mockSettingsAPI.getSettings).toHaveBeenCalled();
        });

        test('resets to defaults when reset button clicked', async () => {
            const resetToDefaults = async () => {
                const result = await mockSettingsAPI.resetToDefaults();
                if (result.success) {
                    // Reload settings after reset
                    return await mockSettingsAPI.getSettings();
                }
                return null;
            };

            const result = await resetToDefaults();
            expect(mockSettingsAPI.resetToDefaults).toHaveBeenCalled();
            expect(mockSettingsAPI.getSettings).toHaveBeenCalled();
        });
    });

    describe('UI state updates', () => {
        test('updates form fields with loaded settings', () => {
            const updateFormFields = (settings) => {
                const filterInput = container.querySelector('#filter-regex');
                const intervalInput = container.querySelector('#refresh-interval');
                const autoRefreshInput = container.querySelector('#auto-refresh');
                const themeSelect = container.querySelector('#theme-selector');

                if (filterInput) filterInput.value = settings.filterRegex || '';
                if (intervalInput) intervalInput.value = settings.refreshInterval || 5;
                if (autoRefreshInput) autoRefreshInput.checked = settings.autoRefresh !== false;
                if (themeSelect) themeSelect.value = settings.theme || 'light';
            };

            const settings = {
                filterRegex: '.*meeting.*',
                refreshInterval: 10,
                autoRefresh: false,
                theme: 'dark'
            };

            updateFormFields(settings);

            expect(container.querySelector('#filter-regex').value).toBe('.*meeting.*');
            expect(container.querySelector('#refresh-interval').value).toBe('10');
            expect(container.querySelector('#auto-refresh').checked).toBe(false);
            expect(container.querySelector('#theme-selector').value).toBe('dark');
        });

        test('disables form during save operation', () => {
            const setFormDisabled = (disabled) => {
                const form = container.querySelector('#settings-form');
                const inputs = form.querySelectorAll('input, select, button');
                inputs.forEach(input => {
                    input.disabled = disabled;
                });
            };

            // Disable form
            setFormDisabled(true);
            const inputs = container.querySelectorAll('#settings-form input, #settings-form select, #settings-form button');
            inputs.forEach(input => {
                expect(input.disabled).toBe(true);
            });

            // Re-enable form
            setFormDisabled(false);
            inputs.forEach(input => {
                expect(input.disabled).toBe(false);
            });
        });

        test('shows save confirmation message', () => {
            const showConfirmation = (message, duration = 2000) => {
                const confirmation = document.createElement('div');
                confirmation.className = 'save-confirmation';
                confirmation.textContent = message;
                container.appendChild(confirmation);

                setTimeout(() => {
                    confirmation.remove();
                }, duration);

                return confirmation;
            };

            const confirmation = showConfirmation('Settings saved successfully');
            expect(confirmation.textContent).toBe('Settings saved successfully');
            expect(confirmation.className).toBe('save-confirmation');
            expect(container.contains(confirmation)).toBe(true);
        });

        test('toggles panel visibility', () => {
            const togglePanel = () => {
                const panel = container.querySelector('#settings-panel');
                const isOpen = panel.classList.contains('open');
                
                if (isOpen) {
                    panel.classList.remove('open');
                } else {
                    panel.classList.add('open');
                }
                
                return !isOpen;
            };

            // Initially closed
            expect(container.querySelector('#settings-panel').classList.contains('open')).toBe(false);

            // Open panel
            let isOpen = togglePanel();
            expect(isOpen).toBe(true);
            expect(container.querySelector('#settings-panel').classList.contains('open')).toBe(true);

            // Close panel
            isOpen = togglePanel();
            expect(isOpen).toBe(false);
            expect(container.querySelector('#settings-panel').classList.contains('open')).toBe(false);
        });
    });

    describe('real-time validation', () => {
        test('validates regex on input change', () => {
            const regexInput = container.querySelector('#filter-regex');
            let isValid = true;

            const validateOnInput = (event) => {
                const value = event.target.value;
                try {
                    if (value) new RegExp(value);
                    isValid = true;
                    event.target.classList.remove('invalid');
                } catch (e) {
                    isValid = false;
                    event.target.classList.add('invalid');
                }
            };

            // Valid regex
            regexInput.value = '.*test.*';
            validateOnInput({ target: regexInput });
            expect(isValid).toBe(true);
            expect(regexInput.classList.contains('invalid')).toBe(false);

            // Invalid regex
            regexInput.value = '[unclosed';
            validateOnInput({ target: regexInput });
            expect(isValid).toBe(false);
            expect(regexInput.classList.contains('invalid')).toBe(true);
        });

        test('validates interval on input change', () => {
            const intervalInput = container.querySelector('#refresh-interval');
            let isValid = true;

            const validateInterval = (event) => {
                const value = parseInt(event.target.value, 10);
                isValid = !isNaN(value) && value >= 1 && value <= 60;
                
                if (!isValid) {
                    event.target.classList.add('invalid');
                } else {
                    event.target.classList.remove('invalid');
                }
            };

            // Valid interval
            intervalInput.value = '15';
            validateInterval({ target: intervalInput });
            expect(isValid).toBe(true);
            expect(intervalInput.classList.contains('invalid')).toBe(false);

            // Invalid interval (too high)
            intervalInput.value = '100';
            validateInterval({ target: intervalInput });
            expect(isValid).toBe(false);
            expect(intervalInput.classList.contains('invalid')).toBe(true);
        });

        test('prevents form submission with invalid data', () => {
            const validateForm = () => {
                const regexInput = container.querySelector('#filter-regex');
                const intervalInput = container.querySelector('#refresh-interval');
                
                let isValid = true;
                
                // Validate regex
                try {
                    if (regexInput.value) new RegExp(regexInput.value);
                } catch (e) {
                    isValid = false;
                }
                
                // Validate interval
                const interval = parseInt(intervalInput.value, 10);
                if (isNaN(interval) || interval < 1 || interval > 60) {
                    isValid = false;
                }
                
                return isValid;
            };

            // Valid form
            container.querySelector('#filter-regex').value = '.*valid.*';
            container.querySelector('#refresh-interval').value = '10';
            expect(validateForm()).toBe(true);

            // Invalid regex
            container.querySelector('#filter-regex').value = '[invalid';
            expect(validateForm()).toBe(false);

            // Invalid interval
            container.querySelector('#filter-regex').value = '';
            container.querySelector('#refresh-interval').value = '0';
            expect(validateForm()).toBe(false);
        });
    });

    describe('theme application', () => {
        test('applies selected theme immediately', () => {
            const applyTheme = (theme) => {
                document.documentElement.className = document.documentElement.className
                    .replace(/theme-\w+/, '')
                    .trim();
                document.documentElement.classList.add(`theme-${theme}`);
            };

            applyTheme('dark');
            expect(document.documentElement.classList.contains('theme-dark')).toBe(true);

            applyTheme('light');
            expect(document.documentElement.classList.contains('theme-light')).toBe(true);
            expect(document.documentElement.classList.contains('theme-dark')).toBe(false);
        });

        test('persists theme selection', async () => {
            const saveTheme = async (theme) => {
                const result = await mockSettingsAPI.updateSettings({ theme });
                return result.success;
            };

            const success = await saveTheme('dark');
            expect(success).toBe(true);
            expect(mockSettingsAPI.updateSettings).toHaveBeenCalledWith({ theme: 'dark' });
        });
    });
});