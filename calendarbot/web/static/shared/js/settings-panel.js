/**
 * CalendarBot Settings Panel Controller
 * 
 * Main controller for the settings panel that coordinates between
 * gesture handler, API client, and form management with auto-save.
 */

class SettingsPanel {
    constructor(options = {}) {
        this.isOpen = false;
        this.isInitialized = false;
        this.isTransitioning = false;

        // Component instances
        this.api = new SettingsAPI();
        this.gestureHandler = null;

        // Settings data
        this.currentSettings = null;
        this.localSettings = null;
        this.hasUnsavedChanges = false;

        // Auto-save configuration
        this.autoSaveDelay = 2000; // 2 seconds
        this.autoSaveTimeout = null;
        this.lastSaveTime = null;

        // Form validation
        this.validationErrors = {};

        // UI state
        this.currentLayout = this.detectLayout();
        this.screenSize = this.detectScreenSize();

        // Event listeners cleanup
        this.boundEventListeners = [];

        if (!window.CALENDARBOT_PRODUCTION) if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Initialized with layout:', this.currentLayout, 'screen size:', this.screenSize);
    }

    /**
     * Initialize the settings panel system
     * Creates DOM elements, sets up event listeners, and initializes components
     */
    async initialize() {
        if (this.isInitialized) {
            if (!window.CALENDARBOT_PRODUCTION) console.warn('SettingsPanel: Already initialized');
            return;
        }

        try {
            // Create panel DOM structure
            this.createPanelHTML();

            // CRITICAL: Apply content-based sizing after panel is created
            this.updateContentContainerDimensions();

            // Initialize gesture handler
            this.gestureHandler = new GestureHandler(this);
            this.gestureHandler.initialize();

            // Load initial settings
            await this.loadSettings();

            // Setup form event listeners
            this.setupFormEventListeners();

            // Setup responsive handlers
            this.setupResponsiveHandlers();

            // Setup keyboard shortcuts
            this.setupKeyboardShortcuts();

            this.isInitialized = true;
            if (!window.CALENDARBOT_PRODUCTION) if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Initialization complete');

        } catch (error) {
            if (!window.CALENDARBOT_PRODUCTION) console.error('SettingsPanel: Initialization failed:', error);
            this.showError('Failed to initialize settings panel: ' + error.message);
        }
    }

    /**
     * Create the settings panel HTML structure
     */
    createPanelHTML() {
        // Remove existing panel if it exists
        const existingPanel = document.getElementById('settings-panel');
        if (existingPanel) {
            existingPanel.remove();
        }

        if (!window.CALENDARBOT_PRODUCTION) if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Creating panel HTML, isOpen should be false:', this.isOpen);

        const panelHTML = `
            <div id="settings-panel" class="settings-panel" role="dialog" aria-labelledby="settings-title" aria-hidden="true" style="display: none !important; visibility: hidden !important; opacity: 0 !important;">
                <div class="settings-header">
                    <h2 id="settings-title" class="settings-title">Settings</h2>
                    <button class="settings-close" aria-label="Close settings" type="button">×</button>
                </div>
                
                <div class="settings-content">
                    <!-- Status Messages -->
                    <div id="settings-status" class="settings-status settings-hidden" role="alert"></div>
                    
                    <!-- Event Filtering Section -->
                    <section class="settings-section">
                        <h3 class="settings-section-title">Event Filtering</h3>
                        
                        <!-- All-day Events Toggle -->
                        <div class="settings-field">
                            <label class="settings-toggle">
                                <input type="checkbox" id="hide-all-day-events" />
                                <span class="settings-toggle-switch"></span>
                                <span class="settings-toggle-label">Hide all-day events</span>
                            </label>
                            <div class="settings-description">
                                Hide calendar blocks, vacation days, and other all-day events from view
                            </div>
                        </div>
                        
                        <!-- Title Pattern Filters -->
                        <div class="settings-field">
                            <label class="settings-label" for="pattern-input">Meeting Title Filters</label>
                            <div class="settings-description settings-mb-md">
                                Filter out meetings by title patterns. Use exact text or regular expressions.
                            </div>
                            
                            <!-- Quick Add Patterns -->
                            <div class="quick-add-patterns">
                                <button type="button" class="quick-add-button" data-pattern="Daily Standup">+ Daily Standup</button>
                                <button type="button" class="quick-add-button" data-pattern="Lunch">+ Lunch</button>
                                <button type="button" class="quick-add-button" data-pattern="Break">+ Break</button>
                                <button type="button" class="quick-add-button" data-pattern="Review">+ Review</button>
                            </div>
                            
                            <!-- Custom Pattern Input -->
                            <div class="settings-field settings-mt-md">
                                <div style="display: flex; gap: 8px;">
                                    <input type="text" id="pattern-input" class="settings-input" placeholder="Enter meeting title or pattern..." style="flex: 1;" />
                                    <label class="settings-toggle" style="flex-shrink: 0;">
                                        <input type="checkbox" id="pattern-regex" />
                                        <span class="settings-toggle-switch"></span>
                                        <span class="settings-toggle-label">Regex</span>
                                    </label>
                                    <button type="button" id="add-pattern-btn" class="settings-button">Add</button>
                                </div>
                                <div id="pattern-validation" class="settings-description" style="color: var(--settings-error); margin-top: 4px; display: none;"></div>
                            </div>
                            
                            <!-- Pattern List -->
                            <div id="pattern-list" class="filter-pattern-list settings-mt-md"></div>
                        </div>
                    </section>
                    
                    <!-- Display Settings Section -->
                    <section class="settings-section">
                        <h3 class="settings-section-title">Display Preferences</h3>
                        
                        <!-- Default Layout -->
                        <div class="settings-field">
                            <label class="settings-label">Default Layout</label>
                            <div class="settings-radio-group">
                                <label class="settings-radio">
                                    <input type="radio" name="default-layout" value="3x4" />
                                    <span class="settings-radio-label">3×4 Compact</span>
                                </label>
                                <label class="settings-radio">
                                    <input type="radio" name="default-layout" value="4x8" />
                                    <span class="settings-radio-label">4×8 Standard</span>
                                </label>
                                <label class="settings-radio">
                                    <input type="radio" name="default-layout" value="whats-next-view" />
                                    <span class="settings-radio-label">What's Next</span>
                                </label>
                            </div>
                        </div>
                        
                        <!-- Display Density -->
                        <div class="settings-field">
                            <label class="settings-label" for="display-density">Information Density</label>
                            <select id="display-density" class="settings-select">
                                <option value="compact">Compact - Maximum information</option>
                                <option value="normal">Normal - Balanced layout</option>
                                <option value="spacious">Spacious - Easy reading</option>
                            </select>
                            <div class="settings-description">
                                Controls how much detail is shown and spacing between elements
                            </div>
                        </div>
                        
                        <!-- Auto-refresh Interval (WhatsNextView only) -->
                        <div class="settings-field" id="auto-refresh-field" style="display: none;">
                            <label class="settings-label" for="auto-refresh-interval">Auto-refresh Frequency</label>
                            <select id="auto-refresh-interval" class="settings-select">
                                <option value="60000">Every 1 minute</option>
                                <option value="180000">Every 3 minutes</option>
                                <option value="300000">Every 5 minutes (Recommended)</option>
                                <option value="600000">Every 10 minutes</option>
                                <option value="1800000">Every 30 minutes</option>
                            </select>
                            <div class="settings-description">
                                How often to automatically refresh calendar data. Longer intervals reduce server load and improve performance.
                            </div>
                        </div>
                    </section>
                    
                    <!-- Actions -->
                    <section class="settings-section">
                        <div style="display: flex; gap: 12px; justify-content: space-between; flex-wrap: wrap;">
                            <div style="display: flex; gap: 8px;">
                                <button type="button" id="apply-settings-btn" class="settings-button primary">Apply Changes</button>
                                <button type="button" id="reset-settings-btn" class="settings-button">Reset to Defaults</button>
                            </div>
                            <div style="display: flex; gap: 8px;">
                                <button type="button" id="export-settings-btn" class="settings-button">Export</button>
                                <button type="button" id="import-settings-btn" class="settings-button">Import</button>
                            </div>
                        </div>
                    </section>
                    
                    <!-- Save Status -->
                    <div id="save-status" class="settings-text-center settings-mt-md" style="font-size: var(--text-sm); color: var(--settings-text-secondary);">
                        <span id="save-status-text">Changes saved automatically</span>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', panelHTML);
        if (!window.CALENDARBOT_PRODUCTION) if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Panel HTML created');
    }

    /**
     * Setup form event listeners
     */
    setupFormEventListeners() {
        const panel = document.getElementById('settings-panel');
        if (!panel) {
            if (!window.CALENDARBOT_PRODUCTION) console.error('SettingsPanel: Panel element not found during event setup');
            return;
        }

        // Close button
        const closeBtn = panel.querySelector('.settings-close');
        if (closeBtn) {
            this.addEventListenerWithCleanup(closeBtn, 'click', () => this.close());
        }

        // All-day events toggle
        const allDayToggle = panel.querySelector('#hide-all-day-events');
        if (allDayToggle) {
            this.addEventListenerWithCleanup(allDayToggle, 'change', () => this.onSettingChange());
        }

        // Quick add pattern buttons
        const quickAddButtons = panel.querySelectorAll('.quick-add-button');
        quickAddButtons.forEach(button => {
            this.addEventListenerWithCleanup(button, 'click', (e) => {
                const pattern = e.target.getAttribute('data-pattern');
                if (pattern) {
                    this.addTitlePattern(pattern, false);
                }
            });
        });

        // Custom pattern input
        const patternInput = panel.querySelector('#pattern-input');
        const addPatternBtn = panel.querySelector('#add-pattern-btn');
        const patternRegexToggle = panel.querySelector('#pattern-regex');

        if (patternInput) {
            this.addEventListenerWithCleanup(patternInput, 'input', () => this.validatePatternInput());
            this.addEventListenerWithCleanup(patternInput, 'keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.addPatternFromInput();
                }
            });
        }

        if (patternRegexToggle) {
            this.addEventListenerWithCleanup(patternRegexToggle, 'change', () => this.validatePatternInput());
        }

        if (addPatternBtn) {
            this.addEventListenerWithCleanup(addPatternBtn, 'click', () => this.addPatternFromInput());
        }

        // Layout radio buttons
        const layoutRadios = panel.querySelectorAll('input[name="default-layout"]');
        layoutRadios.forEach(radio => {
            this.addEventListenerWithCleanup(radio, 'change', () => this.onSettingChange());
        });

        // Display density select
        const densitySelect = panel.querySelector('#display-density');
        if (densitySelect) {
            this.addEventListenerWithCleanup(densitySelect, 'change', () => this.onSettingChange());
        }

        // Auto-refresh interval select
        const autoRefreshSelect = panel.querySelector('#auto-refresh-interval');
        if (autoRefreshSelect) {
            this.addEventListenerWithCleanup(autoRefreshSelect, 'change', () => this.onSettingChange());
        }

        // Action buttons
        const applyBtn = panel.querySelector('#apply-settings-btn');
        const resetBtn = panel.querySelector('#reset-settings-btn');
        const exportBtn = panel.querySelector('#export-settings-btn');
        const importBtn = panel.querySelector('#import-settings-btn');

        if (applyBtn) {
            this.addEventListenerWithCleanup(applyBtn, 'click', () => this.saveSettings());
        }

        if (resetBtn) {
            this.addEventListenerWithCleanup(resetBtn, 'click', () => this.resetToDefaults());
        }

        if (exportBtn) {
            this.addEventListenerWithCleanup(exportBtn, 'click', () => this.exportSettings());
        }

        if (importBtn) {
            this.addEventListenerWithCleanup(importBtn, 'click', () => this.importSettings());
        }

        if (!window.CALENDARBOT_PRODUCTION) if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Form event listeners setup complete');
    }

    /**
     * Add event listener with cleanup tracking
     */
    addEventListenerWithCleanup(element, event, handler) {
        element.addEventListener(event, handler);
        this.boundEventListeners.push({ element, event, handler });
    }

    /**
     * Setup responsive handlers for screen size changes
     */
    setupResponsiveHandlers() {
        const resizeHandler = () => {
            const newScreenSize = this.detectScreenSize();
            if (newScreenSize !== this.screenSize) {
                this.screenSize = newScreenSize;
                this.updateResponsiveLayout();
            }

            // Update content container dimensions on resize/orientation change
            this.updateContentContainerDimensions();
        };

        this.addEventListenerWithCleanup(window, 'resize', resizeHandler);
        this.addEventListenerWithCleanup(window, 'orientationchange', resizeHandler);
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        const keyHandler = (e) => {
            // Only handle shortcuts when panel is open
            if (!this.isOpen) return;

            switch (e.key) {
                case 'Escape':
                    e.preventDefault();
                    this.close();
                    break;
                case 's':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.saveSettings();
                    }
                    break;
            }
        };

        this.addEventListenerWithCleanup(document, 'keydown', keyHandler);
    }

    /**
     * Load settings from API and populate form
     */
    async loadSettings() {
        try {
            this.showStatus('Loading settings...', 'info');

            const result = await this.api.getSettings();

            if (result.success) {
                // Handle potential double-wrapped API response
                let settingsData = result.data;

                // Check if the data is double-wrapped (API returns {success: true, data: {success: true, data: {...}}})
                if (settingsData && settingsData.success && settingsData.data) {
                    settingsData = settingsData.data;
                }

                this.currentSettings = settingsData;
                this.localSettings = JSON.parse(JSON.stringify(settingsData)); // Deep copy
                this.populateForm(this.localSettings);
                this.hideStatus();
                if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Settings loaded successfully');
            } else {
                throw new Error(result.error || 'Failed to load settings');
            }

        } catch (error) {
            console.error('SettingsPanel: Failed to load settings:', error);
            this.showError('Failed to load settings: ' + error.message);
        }
    }

    /**
     * Populate form with settings data
     */
    populateForm(settings) {
        if (!settings) return;

        // All-day events toggle
        const allDayToggle = document.getElementById('hide-all-day-events');
        if (allDayToggle && settings.event_filters) {
            allDayToggle.checked = settings.event_filters.hide_all_day_events || false;
        }

        // Title patterns
        if (settings.event_filters && settings.event_filters.title_patterns) {
            this.renderPatternList(settings.event_filters.title_patterns);
        }

        // Default layout
        if (settings.display && settings.display.default_layout) {
            const layoutRadio = document.querySelector(`input[name="default-layout"][value="${settings.display.default_layout}"]`);
            if (layoutRadio) {
                layoutRadio.checked = true;
            }
        }

        // Display density
        const densitySelect = document.getElementById('display-density');
        if (densitySelect && settings.display && settings.display.display_density) {
            densitySelect.value = settings.display.display_density;
        }

        // Auto-refresh interval (WhatsNextView only)
        const autoRefreshSelect = document.getElementById('auto-refresh-interval');
        if (autoRefreshSelect && settings.display && settings.display.auto_refresh_interval) {
            autoRefreshSelect.value = settings.display.auto_refresh_interval.toString();
        }

        // Show/hide auto-refresh field based on current layout
        this.updateLayoutSpecificFields();

        if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Form populated with settings');
    }

    /**
     * Handle setting change with auto-save
     */
    onSettingChange() {
        this.collectFormData();
        this.hasUnsavedChanges = true;
        this.updateSaveStatus('pending');
        this.scheduleAutoSave();
    }

    /**
     * Collect current form data into local settings
     */
    collectFormData() {
        if (!this.localSettings) {
            this.localSettings = {
                event_filters: {
                    title_patterns: [],
                    hide_all_day_events: false
                },
                display: {},
                metadata: {}
            };
        }

        // Ensure event_filters structure exists
        if (!this.localSettings.event_filters) {
            this.localSettings.event_filters = {
                title_patterns: [],
                hide_all_day_events: false
            };
        }

        // Ensure display structure exists before using it
        if (!this.localSettings.display) {
            this.localSettings.display = {};
        }

        // All-day events
        const allDayToggle = document.getElementById('hide-all-day-events');
        if (allDayToggle) {
            this.localSettings.event_filters.hide_all_day_events = allDayToggle.checked;
        }

        // Default layout
        const selectedLayout = document.querySelector('input[name="default-layout"]:checked');
        if (selectedLayout) {
            this.localSettings.display.default_layout = selectedLayout.value;
        }

        // Display density
        const densitySelect = document.getElementById('display-density');
        if (densitySelect) {
            this.localSettings.display.display_density = densitySelect.value;
        }

        // Auto-refresh interval (WhatsNextView only)
        const autoRefreshSelect = document.getElementById('auto-refresh-interval');
        if (autoRefreshSelect) {
            this.localSettings.display.auto_refresh_interval = parseInt(autoRefreshSelect.value);
        }

        // Title patterns are managed separately in renderPatternList()
    }

    /**
     * Schedule auto-save with debouncing
     */
    scheduleAutoSave() {
        // Clear existing timeout
        if (this.autoSaveTimeout) {
            clearTimeout(this.autoSaveTimeout);
        }

        // Schedule new save
        this.autoSaveTimeout = setTimeout(() => {
            this.saveSettings(true); // Silent save
        }, this.autoSaveDelay);
    }

    /**
     * Save settings to server
     */
    async saveSettings(silent = false) {
        try {
            if (!silent) {
                this.showStatus('Saving settings...', 'info');
            }

            this.collectFormData();

            const result = await this.api.updateSettings(this.localSettings);

            if (result.success) {
                this.currentSettings = JSON.parse(JSON.stringify(this.localSettings));
                this.hasUnsavedChanges = false;
                this.lastSaveTime = new Date();

                if (!silent) {
                    this.showStatus('Settings saved successfully', 'success');
                    setTimeout(() => this.hideStatus(), 2000);
                }

                this.updateSaveStatus('saved');
                if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Settings saved successfully');

            } else {
                throw new Error(result.error || 'Failed to save settings');
            }

        } catch (error) {
            console.error('SettingsPanel: Failed to save settings:', error);
            this.showError('Failed to save settings: ' + error.message);
            this.updateSaveStatus('error');
        }
    }

    /**
     * Open settings panel with animation
     */
    async open() {
        if (this.isOpen || this.isTransitioning) {
            return;
        }

        try {
            this.isTransitioning = true;

            const panel = document.getElementById('settings-panel');
            if (!panel) {
                throw new Error('Settings panel element not found');
            }

            // Update content dimensions before showing panel
            this.updateContentContainerDimensions();

            // Load fresh settings
            await this.loadSettings();

            // Show panel
            panel.classList.add('open');
            panel.setAttribute('aria-hidden', 'false');

            // CRITICAL FIX: Remove inline !important styles that prevent CSS .open rules from working
            panel.style.display = '';
            panel.style.visibility = '';
            panel.style.opacity = '';

            // Focus management
            const firstFocusable = panel.querySelector('button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (firstFocusable) {
                setTimeout(() => firstFocusable.focus(), 100);
            }

            this.isOpen = true;
            this.isTransitioning = false;

            if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Panel opened successfully');

        } catch (error) {
            console.error('SettingsPanel: Failed to open panel:', error);
            this.isTransitioning = false;
            this.showError('Failed to open settings panel');
        }
    }

    /**
     * Close settings panel with animation and proper focus management
     */
    close() {
        if (!this.isOpen || this.isTransitioning) {
            if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Close called but panel not open or transitioning');
            return;
        }

        this.isTransitioning = true;

        const panel = document.getElementById('settings-panel');
        if (panel) {
            if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Starting close sequence');

            // ACCESSIBILITY FIX: Enhanced focus management before setting aria-hidden
            const focusedElement = document.activeElement;
            const panelContainsFocus = panel.contains(focusedElement);

            if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Focus management - focused element:', focusedElement?.tagName, focusedElement?.id);
            if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Panel contains focus:', panelContainsFocus);

            // Always handle focus management properly to prevent accessibility violations
            if (panelContainsFocus && focusedElement) {
                if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Removing focus from panel element:', focusedElement.id || focusedElement.tagName);

                // Force blur and clear any active state
                focusedElement.blur();

                // Ensure focus moves to a safe, focusable element outside the panel
                // Use document.body as the safest fallback
                document.body.focus();

                // Double-check that focus has actually moved
                const newFocused = document.activeElement;
                if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Focus moved to:', newFocused?.tagName, newFocused?.id);

                // Use a longer timeout to ensure focus change is fully processed
                setTimeout(() => {
                    // Verify focus is no longer inside panel before setting aria-hidden
                    const currentFocus = document.activeElement;
                    const stillInPanel = panel.contains(currentFocus);

                    if (!stillInPanel) {
                        panel.setAttribute('aria-hidden', 'true');
                        if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: aria-hidden set after successful focus management');
                    } else {
                        console.warn('SettingsPanel: Focus still inside panel, deferring aria-hidden');
                        // Force focus out one more time
                        document.body.focus();
                        setTimeout(() => {
                            panel.setAttribute('aria-hidden', 'true');
                            if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: aria-hidden set after forced focus removal');
                        }, 50);
                    }
                }, 10);
            } else {
                // No focus inside panel, safe to set aria-hidden immediately
                panel.setAttribute('aria-hidden', 'true');
                if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: aria-hidden set (no focus inside panel)');
            }

            // CRITICAL FIX: Remove all visibility-related classes
            // Do NOT reset transform to empty string as this interferes with hiding
            panel.classList.remove('open', 'revealing');

            // CRITICAL FIX: Allow CSS to handle the hiding via transform: translateY(-100%)
            // The transform will be managed by CSS when .open and .revealing classes are removed
        }

        // Clear any pending auto-save
        if (this.autoSaveTimeout) {
            clearTimeout(this.autoSaveTimeout);
            this.autoSaveTimeout = null;
        }

        // Save any unsaved changes
        if (this.hasUnsavedChanges) {
            this.saveSettings(true); // Silent save
        }

        this.isOpen = false;
        this.isTransitioning = false;

        if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Panel closed successfully');
    }

    /**
     * Methods called by gesture handler
     */
    startReveal() {
        const panel = document.getElementById('settings-panel');
        if (panel) {
            panel.classList.add('revealing');
            // Panel is now visible due to CSS .revealing { display: flex; }
        }
    }

    updateReveal(percent) {
        const panel = document.getElementById('settings-panel');
        if (panel) {
            // During drag, interpolate between hidden (-100%) and visible (0%)
            panel.style.transform = `translateY(${-100 + (percent * 100)}%)`;
        }
    }

    cancelReveal() {
        const panel = document.getElementById('settings-panel');
        if (panel) {
            panel.classList.remove('revealing');
            // Panel becomes hidden again due to CSS default { display: none; }
            // Reset transform to let CSS handle positioning
            panel.style.transform = '';
        }
    }

    /**
     * Add title pattern filter
     */
    addTitlePattern(pattern, isRegex = false) {
        if (!pattern.trim()) return;

        // Ensure localSettings is initialized
        if (!this.localSettings) {
            this.localSettings = {
                event_filters: {
                    title_patterns: [],
                    hide_all_day_events: false
                },
                display: {},
                metadata: {}
            };
        }

        // Ensure event_filters structure exists
        if (!this.localSettings.event_filters) {
            this.localSettings.event_filters = {
                title_patterns: [],
                hide_all_day_events: false
            };
        }

        // Ensure title_patterns array exists
        if (!this.localSettings.event_filters.title_patterns) {
            this.localSettings.event_filters.title_patterns = [];
        }

        // Validate regex if needed
        if (isRegex && !this.api.isValidRegex(pattern)) {
            this.showError('Invalid regular expression pattern');
            return;
        }

        // Check for duplicates
        if (this.localSettings.event_filters.title_patterns.some(p => p.pattern === pattern)) {
            this.showError('Pattern already exists');
            return;
        }

        // Add pattern
        const newPattern = {
            pattern: pattern,
            is_regex: isRegex,
            is_active: true,
            case_sensitive: false,
            match_count: 0,
            description: null
        };

        this.localSettings.event_filters.title_patterns.push(newPattern);
        this.renderPatternList(this.localSettings.event_filters.title_patterns);
        this.onSettingChange();

        if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Added title pattern:', pattern);
    }

    /**
     * Add pattern from input field
     */
    addPatternFromInput() {
        const patternInput = document.getElementById('pattern-input');
        const regexToggle = document.getElementById('pattern-regex');

        if (!patternInput) return;

        const pattern = patternInput.value.trim();
        const isRegex = regexToggle ? regexToggle.checked : false;

        if (pattern) {
            this.addTitlePattern(pattern, isRegex);
            patternInput.value = '';
            if (regexToggle) regexToggle.checked = false;
            this.validatePatternInput();
        }
    }

    /**
     * Validate pattern input
     */
    validatePatternInput() {
        const patternInput = document.getElementById('pattern-input');
        const regexToggle = document.getElementById('pattern-regex');
        const validationEl = document.getElementById('pattern-validation');

        if (!patternInput || !validationEl) return;

        const pattern = patternInput.value.trim();
        const isRegex = regexToggle ? regexToggle.checked : false;

        if (pattern && isRegex && !this.api.isValidRegex(pattern)) {
            validationEl.textContent = 'Invalid regular expression';
            validationEl.style.display = 'block';
            return false;
        } else {
            validationEl.style.display = 'none';
            return true;
        }
    }

    /**
     * Render pattern list
     */
    renderPatternList(patterns) {
        const container = document.getElementById('pattern-list');
        if (!container) return;

        if (!patterns || patterns.length === 0) {
            container.innerHTML = '<div class="settings-description">No patterns configured</div>';
            return;
        }

        const html = patterns.map((pattern, index) => `
            <div class="filter-pattern-item">
                <div class="filter-pattern-icon">${pattern.is_active ? '⚡' : '○'}</div>
                <div class="filter-pattern-content">
                    <div class="filter-pattern-text">${this.escapeHtml(pattern.pattern)}</div>
                    <div class="filter-pattern-meta">
                        ${pattern.is_regex ? 'Regex • ' : ''}${pattern.match_count || 0} events filtered
                    </div>
                </div>
                <div class="filter-pattern-actions">
                    <button type="button" class="filter-pattern-toggle" data-index="${index}" title="Toggle filter">
                        ${pattern.is_active ? '⏸️' : '▶️'}
                    </button>
                    <button type="button" class="filter-pattern-remove" data-index="${index}" title="Remove filter">×</button>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;

        // Add event listeners for pattern actions
        container.querySelectorAll('.filter-pattern-toggle').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.target.getAttribute('data-index'));
                this.togglePattern(index);
            });
        });

        container.querySelectorAll('.filter-pattern-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.target.getAttribute('data-index'));
                this.removePattern(index);
            });
        });
    }

    /**
     * Toggle pattern active state
     */
    togglePattern(index) {
        if (this.localSettings.event_filters.title_patterns[index]) {
            this.localSettings.event_filters.title_patterns[index].is_active =
                !this.localSettings.event_filters.title_patterns[index].is_active;
            this.renderPatternList(this.localSettings.event_filters.title_patterns);
            this.onSettingChange();
        }
    }

    /**
     * Remove pattern
     */
    removePattern(index) {
        if (this.localSettings.event_filters.title_patterns[index]) {
            this.localSettings.event_filters.title_patterns.splice(index, 1);
            this.renderPatternList(this.localSettings.event_filters.title_patterns);
            this.onSettingChange();
        }
    }

    /**
     * Reset settings to defaults
     */
    async resetToDefaults() {
        if (!confirm('Reset all settings to defaults? This cannot be undone.')) {
            return;
        }

        try {
            this.showStatus('Resetting settings...', 'info');

            const result = await this.api.resetToDefaults();

            if (result.success) {
                this.currentSettings = result.data;
                this.localSettings = JSON.parse(JSON.stringify(result.data));
                this.populateForm(this.localSettings);
                this.showStatus('Settings reset to defaults', 'success');
                setTimeout(() => this.hideStatus(), 2000);
            } else {
                throw new Error(result.error || 'Failed to reset settings');
            }

        } catch (error) {
            console.error('SettingsPanel: Failed to reset settings:', error);
            this.showError('Failed to reset settings: ' + error.message);
        }
    }

    /**
     * Export settings
     */
    async exportSettings() {
        try {
            const result = await this.api.exportSettings();

            if (result.success) {
                const dataStr = JSON.stringify(result.data, null, 2);
                const dataBlob = new Blob([dataStr], { type: 'application/json' });

                const link = document.createElement('a');
                link.href = URL.createObjectURL(dataBlob);
                link.download = `calendarbot-settings-${new Date().toISOString().split('T')[0]}.json`;
                link.click();

                this.showStatus('Settings exported successfully', 'success');
                setTimeout(() => this.hideStatus(), 2000);
            } else {
                throw new Error(result.error || 'Failed to export settings');
            }

        } catch (error) {
            console.error('SettingsPanel: Failed to export settings:', error);
            this.showError('Failed to export settings: ' + error.message);
        }
    }

    /**
     * Import settings
     */
    importSettings() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';

        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            try {
                const text = await file.text();
                const data = JSON.parse(text);

                const result = await this.api.importSettings(data);

                if (result.success) {
                    this.currentSettings = result.data;
                    this.localSettings = JSON.parse(JSON.stringify(result.data));
                    this.populateForm(this.localSettings);
                    this.showStatus('Settings imported successfully', 'success');
                    setTimeout(() => this.hideStatus(), 2000);
                } else {
                    throw new Error(result.error || 'Failed to import settings');
                }

            } catch (error) {
                console.error('SettingsPanel: Failed to import settings:', error);
                this.showError('Failed to import settings: ' + error.message);
            }
        };

        input.click();
    }

    /**
     * Detect current layout from DOM or URL
     */
    detectLayout() {
        // Look for layout indicators in DOM or URL
        const html = document.documentElement;
        const body = document.body;
        let layout = 'unknown';

        // Check HTML element class first (more reliable)
        if (html && html.classList.contains('layout-whats-next-view')) layout = 'whats-next-view';
        else if (html && html.classList.contains('layout-3x4')) layout = '3x4';
        else if (html && html.classList.contains('layout-4x8')) layout = '4x8';
        // Fallback to body classes
        else if (body && body.classList.contains('layout-whats-next-view')) layout = 'whats-next-view';
        else if (body && body.classList.contains('layout-3x4')) layout = '3x4';
        else if (body && body.classList.contains('layout-4x8')) layout = '4x8';
        else {
            // Check URL path as final fallback
            const path = window.location.pathname;
            if (path.includes('whats-next-view')) layout = 'whats-next-view';
            else if (path.includes('3x4')) layout = '3x4';
            else if (path.includes('4x8')) layout = '4x8';
        }

        if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Layout detected:', layout, 'from HTML class:', html?.className);
        return layout;
    }

    /**
     * Update content container dimensions and set dynamic CSS properties
     */
    updateContentContainerDimensions() {
        try {
            const contentContainer = document.querySelector('.calendar-content');
            const settingsPanel = document.getElementById('settings-panel');

            if (contentContainer && settingsPanel) {
                const rect = contentContainer.getBoundingClientRect();
                const computedStyle = window.getComputedStyle(contentContainer);

                // Get the actual content dimensions including padding
                const width = rect.width;
                const height = rect.height;

                // Store dimensions for later use
                this.contentContainerDimensions = {
                    width: Math.round(width),
                    height: Math.round(height),
                    left: Math.round(rect.left),
                    top: Math.round(rect.top)
                };

                // Apply content-aware CSS custom properties
                this.applyContentBasedSizing(this.contentContainerDimensions);

            } else if (!contentContainer) {
                this.contentContainerDimensions = null;
                this.clearContentBasedSizing();
            } else if (!settingsPanel) {
                this.contentContainerDimensions = null;
            }
        } catch (error) {
            console.warn('SettingsPanel: Failed to detect content container dimensions:', error);
            this.contentContainerDimensions = null;
        }
    }

    /**
     * Apply content-based sizing CSS custom properties
     */
    applyContentBasedSizing(dimensions) {
        if (!dimensions) return;

        const root = document.documentElement;
        const panel = document.getElementById('settings-panel');

        // Calculate panel height (capped at 400px as per CSS)
        const panelHeight = Math.min(dimensions.height, 400);

        // Calculate transform value to completely hide panel above viewport
        // For complete hiding: effective top + panel height ≤ 0
        // effective top = CSS top + translateY
        // So: dimensions.top + translateY + panelHeight ≤ 0
        // translateY ≤ -dimensions.top - panelHeight

        // Calculate transform to hide panel - handle constrained layouts
        let hideTransform;
        const bodyHeight = document.body.offsetHeight;
        const bodyWidth = document.body.offsetWidth;
        const isConstrainedLayout = bodyHeight <= 500 || bodyWidth <= 400;

        if (isConstrainedLayout) {
            // For constrained layouts: hide just above the content container
            hideTransform = -panelHeight;
        } else {
            // For normal layouts: hide above viewport as before
            hideTransform = -(dimensions.top + panelHeight);
        }

        // Set content-aware dimensions that override viewport-based ones
        root.style.setProperty('--settings-panel-content-width', `${dimensions.width}px`);
        root.style.setProperty('--settings-panel-content-height', `${panelHeight}px`);
        root.style.setProperty('--settings-panel-content-left', `${dimensions.left}px`);
        root.style.setProperty('--settings-panel-content-top', `${dimensions.top}px`);
        root.style.setProperty('--settings-panel-hide-transform', `${hideTransform}px`);

        // Flag that content-based sizing is active
        root.style.setProperty('--settings-panel-content-mode', '1');

        // CRITICAL FIX: Set data attribute to ensure CSS selectors work reliably
        if (panel) {
            panel.setAttribute('data-content-aware', 'true');
        }

        if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Applied content-based sizing for', isConstrainedLayout ? 'constrained' : 'normal', 'layout');
    }

    /**
     * Clear content-based sizing and restore viewport-based fallback
     */
    clearContentBasedSizing() {
        const root = document.documentElement;

        root.style.removeProperty('--settings-panel-content-width');
        root.style.removeProperty('--settings-panel-content-height');
        root.style.removeProperty('--settings-panel-content-left');
        root.style.removeProperty('--settings-panel-content-top');
        root.style.removeProperty('--settings-panel-content-mode');
    }

    /**
     * Detect screen size category
     */
    detectScreenSize() {
        const width = window.innerWidth;
        const height = window.innerHeight;

        if (width <= 320 && height <= 420) return 'compact';
        if (width <= 480 && height <= 800) return 'medium';
        if (width >= 768) return 'large';
        return 'medium';
    }

    /**
     * Update responsive layout
     */
    updateResponsiveLayout() {
        if (this.gestureHandler) {
            // Adjust gesture zone height based on screen size
            const zoneHeight = this.screenSize === 'compact' ? 40 : 50;
            this.gestureHandler.updateGestureZoneHeight(zoneHeight);
        }

        if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Updated responsive layout for screen size:', this.screenSize);
    }

    /**
     * Update layout-specific fields visibility
     */
    updateLayoutSpecificFields() {
        const autoRefreshField = document.getElementById('auto-refresh-field');
        if (autoRefreshField) {
            // Show auto-refresh setting only for WhatsNextView
            if (this.currentLayout === 'whats-next-view') {
                autoRefreshField.style.display = 'block';
            } else {
                autoRefreshField.style.display = 'none';
            }
        }
    }

    /**
     * Show status message
     */
    showStatus(message, type = 'info') {
        const statusEl = document.getElementById('settings-status');
        if (statusEl) {
            statusEl.textContent = message;
            statusEl.className = `settings-status ${type}`;
            statusEl.classList.remove('settings-hidden');
        }
    }

    /**
     * Hide status message
     */
    hideStatus() {
        const statusEl = document.getElementById('settings-status');
        if (statusEl) {
            statusEl.classList.add('settings-hidden');
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        this.showStatus(message, 'error');
        console.error('SettingsPanel Error:', message);
    }

    /**
     * Update save status indicator
     */
    updateSaveStatus(status) {
        const statusEl = document.getElementById('save-status-text');
        if (!statusEl) return;

        switch (status) {
            case 'pending':
                statusEl.textContent = 'Saving changes...';
                statusEl.style.color = 'var(--settings-warning)';
                break;
            case 'saved':
                statusEl.textContent = `Last saved: ${new Date().toLocaleTimeString()}`;
                statusEl.style.color = 'var(--settings-success)';
                break;
            case 'error':
                statusEl.textContent = 'Save failed - please try again';
                statusEl.style.color = 'var(--settings-error)';
                break;
            default:
                statusEl.textContent = 'Changes saved automatically';
                statusEl.style.color = 'var(--settings-text-secondary)';
        }
    }

    /**
     * Escape HTML for safe rendering
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Cleanup and destroy the settings panel
     */
    destroy() {
        // Clear auto-save timeout
        if (this.autoSaveTimeout) {
            clearTimeout(this.autoSaveTimeout);
        }

        // Clear content-based sizing properties
        this.clearContentBasedSizing();

        // Remove event listeners
        this.boundEventListeners.forEach(({ element, event, handler }) => {
            element.removeEventListener(event, handler);
        });
        this.boundEventListeners = [];

        // Destroy gesture handler
        if (this.gestureHandler) {
            this.gestureHandler.destroy();
        }

        // Remove panel from DOM
        const panel = document.getElementById('settings-panel');
        if (panel) {
            panel.remove();
        }

        this.isInitialized = false;
        if (!window.CALENDARBOT_PRODUCTION) console.log('SettingsPanel: Cleanup completed');
    }
}

// Export for module systems or global use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SettingsPanel;
} else if (typeof window !== 'undefined') {
    window.SettingsPanel = SettingsPanel;
}