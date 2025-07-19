/**
 * CalendarBot Settings API Client
 * 
 * Handles all API communication for settings management, including
 * CRUD operations, validation, and error handling with retry logic.
 */

class SettingsAPI {
    constructor() {
        this.baseUrl = '/api/settings';
        this.retryAttempts = 3;
        this.retryDelay = 1000; // 1 second base delay
    }

    /**
     * Get current settings from server
     * @returns {Promise<Object>} Settings data object
     */
    async getSettings() {
        try {
            const response = await this.fetchWithRetry(`${this.baseUrl}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return {
                success: true,
                data: data,
                error: null
            };

        } catch (error) {
            console.error('SettingsAPI: Failed to get settings:', error);
            return {
                success: false,
                data: null,
                error: error.message
            };
        }
    }

    /**
     * Update complete settings data
     * @param {Object} settings - Complete settings object
     * @returns {Promise<Object>} Update result with success status
     */
    async updateSettings(settings) {
        try {
            // Client-side validation
            const validation = this.validateSettings(settings);
            if (!validation.isValid) {
                throw new Error(`Validation failed: ${validation.errors.join(', ')}`);
            }

            const response = await this.fetchWithRetry(`${this.baseUrl}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings)
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return {
                success: true,
                data: data,
                error: null
            };

        } catch (error) {
            console.error('SettingsAPI: Failed to update settings:', error);
            return {
                success: false,
                data: null,
                error: error.message
            };
        }
    }

    /**
     * Get event filter settings
     * @returns {Promise<Object>} Filter settings data
     */
    async getFilterSettings() {
        try {
            const response = await this.fetchWithRetry(`${this.baseUrl}/filters`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return {
                success: true,
                data: data,
                error: null
            };

        } catch (error) {
            console.error('SettingsAPI: Failed to get filter settings:', error);
            return {
                success: false,
                data: null,
                error: error.message
            };
        }
    }

    /**
     * Update event filter settings
     * @param {Object} filterSettings - Filter settings object
     * @returns {Promise<Object>} Update result
     */
    async updateFilterSettings(filterSettings) {
        try {
            const response = await this.fetchWithRetry(`${this.baseUrl}/filters`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(filterSettings)
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return {
                success: true,
                data: data,
                error: null
            };

        } catch (error) {
            console.error('SettingsAPI: Failed to update filter settings:', error);
            return {
                success: false,
                data: null,
                error: error.message
            };
        }
    }

    /**
     * Get display settings
     * @returns {Promise<Object>} Display settings data
     */
    async getDisplaySettings() {
        try {
            const response = await this.fetchWithRetry(`${this.baseUrl}/display`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return {
                success: true,
                data: data,
                error: null
            };

        } catch (error) {
            console.error('SettingsAPI: Failed to get display settings:', error);
            return {
                success: false,
                data: null,
                error: error.message
            };
        }
    }

    /**
     * Update display settings
     * @param {Object} displaySettings - Display settings object
     * @returns {Promise<Object>} Update result
     */
    async updateDisplaySettings(displaySettings) {
        try {
            const response = await this.fetchWithRetry(`${this.baseUrl}/display`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(displaySettings)
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return {
                success: true,
                data: data,
                error: null
            };

        } catch (error) {
            console.error('SettingsAPI: Failed to update display settings:', error);
            return {
                success: false,
                data: null,
                error: error.message
            };
        }
    }

    /**
     * Preview filter effects on current events
     * @param {Object} filterSettings - Filter settings to preview
     * @returns {Promise<Object>} Preview result with event counts
     */
    async previewFilterEffects(filterSettings) {
        try {
            const response = await this.fetchWithRetry(`${this.baseUrl}/preview`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(filterSettings)
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return {
                success: true,
                data: data,
                error: null
            };

        } catch (error) {
            console.error('SettingsAPI: Failed to preview filter effects:', error);
            return {
                success: false,
                data: null,
                error: error.message
            };
        }
    }

    /**
     * Validate settings object structure and content
     * @param {Object} settings - Settings object to validate
     * @returns {Object} Validation result with isValid boolean and errors array
     */
    validateSettings(settings) {
        const errors = [];

        if (!settings || typeof settings !== 'object') {
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
    }

    /**
     * Validate event filter settings
     * @param {Object} filters - Event filter settings
     * @returns {Array} Array of validation error messages
     */
    validateEventFilters(filters) {
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
    }

    /**
     * Validate display settings
     * @param {Object} display - Display settings
     * @returns {Array} Array of validation error messages
     */
    validateDisplaySettings(display) {
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
    }

    /**
     * Test if a string is a valid regular expression
     * @param {string} pattern - Pattern to test
     * @returns {boolean} True if valid regex, false otherwise
     */
    isValidRegex(pattern) {
        try {
            new RegExp(pattern);
            return true;
        } catch (e) {
            return false;
        }
    }

    /**
     * Fetch with retry logic for improved reliability
     * @param {string} url - URL to fetch
     * @param {Object} options - Fetch options
     * @returns {Promise<Response>} Fetch response
     */
    async fetchWithRetry(url, options) {
        let lastError;

        for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
            try {
                const response = await fetch(url, options);
                
                // Don't retry on client errors (4xx), only on server errors (5xx) and network issues
                if (response.ok || (response.status >= 400 && response.status < 500)) {
                    return response;
                }
                
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                
            } catch (error) {
                lastError = error;
                
                if (attempt < this.retryAttempts) {
                    console.warn(`SettingsAPI: Attempt ${attempt} failed, retrying in ${this.retryDelay}ms:`, error.message);
                    await this.delay(this.retryDelay * attempt); // Exponential backoff
                } else {
                    console.error(`SettingsAPI: All ${this.retryAttempts} attempts failed:`, error.message);
                }
            }
        }

        throw lastError;
    }

    /**
     * Utility function to create a delay
     * @param {number} ms - Milliseconds to delay
     * @returns {Promise} Promise that resolves after delay
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Reset settings to defaults
     * @returns {Promise<Object>} Reset result
     */
    async resetToDefaults() {
        try {
            const response = await this.fetchWithRetry(`${this.baseUrl}/reset`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return {
                success: true,
                data: data,
                error: null
            };

        } catch (error) {
            console.error('SettingsAPI: Failed to reset settings:', error);
            return {
                success: false,
                data: null,
                error: error.message
            };
        }
    }

    /**
     * Export settings for backup
     * @returns {Promise<Object>} Export result with settings data
     */
    async exportSettings() {
        try {
            const response = await this.fetchWithRetry(`${this.baseUrl}/export`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return {
                success: true,
                data: data,
                error: null
            };

        } catch (error) {
            console.error('SettingsAPI: Failed to export settings:', error);
            return {
                success: false,
                data: null,
                error: error.message
            };
        }
    }

    /**
     * Import settings from backup
     * @param {Object} settingsData - Settings data to import
     * @returns {Promise<Object>} Import result
     */
    async importSettings(settingsData) {
        try {
            const response = await this.fetchWithRetry(`${this.baseUrl}/import`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settingsData)
            });

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return {
                success: true,
                data: data,
                error: null
            };

        } catch (error) {
            console.error('SettingsAPI: Failed to import settings:', error);
            return {
                success: false,
                data: null,
                error: error.message
            };
        }
    }
}

// Export for module systems or global use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SettingsAPI;
} else if (typeof window !== 'undefined') {
    window.SettingsAPI = SettingsAPI;
}